/**
 * harvest.js — 收牌内核（④ reflect-harvest）· ★ 跨设备版
 * =============================================================================
 * 流水线位置：
 *   ① reflect-collect → ② reflect-dispatch → ③ 各智能体回填 → ④ **本工具** → ⑤ synthesize
 *
 * 三件事同时成立，才是这台工具的全部价值：
 *
 *  【1】★ 质量门（不是简单合并）：无证据的条目**在结构上进不了 valid 集合**。
 *       下游的复现排序、用户裁定、入册全部建立在"每条都有证据"之上，漏一条就无声污染。
 *       `mintAdmitted()` 是唯一入口（不过返回 null），`buildValidSet()` 是唯一 push 点（裸对象抛错）。
 *       全包没有 skip-evidence / force / lenient 这类旗标。
 *
 *  【2】★ 复现广度 = 独立 **<设备>:<智能体>** 数（不是条目数、也不是会话数）。
 *       跨设备复现是**更强的信号**：不同设备跑不同任务、看不同上下文，
 *       独立踩同一个坑说明"这不是某条工作流的偶然，而是系统性的"（design §10.7）。
 *       ⇒ 集群带 `cross_device: true/false`，synthesize 按 (cross_device, recurrence) 排序。
 *
 *  【3】★ 跨设备污染与同步盘污染都要挡住：
 *       - `(device, agent)` 去重（黑板 > 本地）——否则同一台设备的本地落盘 + 黑板推送会被算两遍；
 *       - `device_mismatch`——key 说 A 设备、内容自称 B 设备 → 拒绝该条；
 *       - `possible_sync_duplicate`——**逐字相同**的 lesson 出现在 ≥2 设备且时点接近
 *         （同步盘/复制粘贴的典型形态）→ 标出来，但**不重复计入 recurrence**
 *         （否则跨设备信号会被"同一份文件的两份副本"伪造）。
 */
import os from 'node:os';
import path from 'node:path';
import { ANSWERS_DIR, LOG_FILE, log } from './out.js';
import {
  adjudicate, mintAdmitted, buildValidSet, GateError,
  ALL_REJECT_REASONS, ITEM_FLAGS, SYNC_DUP_RULE
} from './gate.js';
import { clusterLessons, similarityReport, SIM_RULE } from './lesson.js';
import { loadCatalog } from './catalog.js';
import { collectAnswerSources } from './source.js';
import { resolveDevices, DEFAULT_DEVICES } from './devices.js';
import { DEFAULT_CENTRAL } from './http.js';

/** IO / 用法类错误（CLI 映射 exit 2），与「门失效」exit 1 区分开 */
export class HarvestIOError extends Error {
  constructor(code, message) { super(message); this.name = 'HarvestIOError'; this.code = code; }
}

export const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** 默认本地根（跨设备布局：<root>/answers/<device>/<date>/ 与 <root>/cards/<device>/<date>.md） */
export const DEFAULT_LOCAL_ROOT = path.join(os.homedir(), 'dsh-collab', 'data', 'reflect');

export function answersDirOf(date, localRoot) {
  return path.join(localRoot || DEFAULT_LOCAL_ROOT, 'answers', date);
}

/* -------------------------------------------------------------------------- *
 * 主流程
 * -------------------------------------------------------------------------- */

/**
 * @param {string} date YYYY-MM-DD
 * @param {object} opts
 *   dryRun, devices[], localDevice, localRoot, central, localOnly, allowLate, timeoutMs, registryPath
 */
export async function harvest(date, opts = {}) {
  if (!DATE_RE.test(String(date))) throw new HarvestIOError('BAD_DATE', `日期格式必须是 YYYY-MM-DD，收到 '${date}'`);
  const dryRun = opts.dryRun === true;
  const localRoot = opts.localRoot || DEFAULT_LOCAL_ROOT;
  const central = opts.central || DEFAULT_CENTRAL;
  const allowLate = opts.allowLate === true;
  const localOnly = opts.localOnly === true;

  const dev = resolveDevices({ devices: opts.devices, localDevice: opts.localDevice, registryPath: opts.registryPath });
  const notes = [...dev.notes];

  // ── 源收集（本地全部设备 + 中央黑板全部设备）
  const src = await collectAnswerSources({
    date, devices: dev.devices, localDevice: dev.localDevice,
    localRoot, central, localOnly, allowLate, timeoutMs: opts.timeoutMs
  });
  notes.push(...src.notes);

  if (src.records.length === 0) {
    throw new HarvestIOError('NO_ANSWERS',
      `没有任何回填被找到（日期 ${date}）。\n` +
      `  设备表: [${dev.devices.join(', ')}]（来源 ${dev.source}）\n` +
      `  本机设备: ${dev.localDevice}（来源 ${dev.localSource}）\n` +
      `  本地: ${localRoot}/answers/<device>/${date}/（老布局 ${localRoot}/answers/${date}/ 亦支持）\n` +
      `  中央黑板: ${central}/data/reflect/answers/<device>/${date}\n` +
      `（上游 ② reflect-dispatch 应先派卡；本工具不代建目录、不猜。离线设备表现为 pending 而不是缺数据。）`);
  }

  // ── 参照库（读不到时跳过 unknown_rule 判定，宁可漏标不可误标）
  const catalog = loadCatalog();
  notes.push(...catalog.notes);
  const catalogsForJudge = {
    rules: catalog.available.rules ? catalog.rules : null,
    phis: catalog.available.phis ? catalog.phis : null
  };

  const rejected = [];
  const entries = [];
  const perDeviceAgg = {};
  for (const d of dev.devices) {
    const rec = src.perDevice[d] || { local: 0, blackboard: 0, late_accepted: 0, out_of_window: 0, device_mismatch: 0, errors: [], card: { dispatched: null, via: null } };
    perDeviceAgg[d] = {
      device: d, status: 'unknown',
      agents_total: 0, agents_answered: 0, agents_declined: 0, files_rejected: 0,
      items_total: 0, items_valid: 0, items_rejected: 0,
      rejection_distribution: {}, flags_distribution: {},
      plugin_version: null, plugin_versions: [],
      late_accepted: rec.late_accepted, out_of_window: rec.out_of_window, device_mismatch: rec.device_mismatch,
      card_dispatched: rec.card.dispatched, card_via: rec.card.via,
      sources: { local: rec.local, blackboard: rec.blackboard },
      errors: (rec.errors || []).slice(0, 12)
    };
  }

  const answersMeta = [];
  for (const r of src.records) {
    const agg = perDeviceAgg[r.device];
    if (!agg) { notes.push(`★ 回填来自设备表之外的设备 '${r.device}'（${r.origin.kind}:${r.origin.ref}）→ 已忽略；如属正常请用 --devices 或 devices.json 登记`); continue; }
    agg.agents_total++;

    if (r.payload === null || r.payload === undefined) {
      agg.files_rejected++;
      rejected.push({ device: r.device, agent: r.agent, item_id: null, scope: 'file', reason: 'invalid_shape', reasons: ['invalid_shape'], issues: [r.parseError || '载荷为空'], origin: r.origin.kind, ref: r.origin.ref });
      continue;
    }
    if (r.payload.declined === true) {
      const reason = [r.payload.declined_reason, r.payload.reason, r.payload.decline_reason].find((v) => typeof v === 'string' && v.trim() !== '');
      if (!reason) {
        agg.files_rejected++;
        rejected.push({ device: r.device, agent: r.agent, item_id: null, scope: 'file', reason: 'invalid_decline', reasons: ['invalid_decline'], issues: ['declined:true 但未给理由（declined_reason / reason 均为空）——「弃权」也是一种断言，必须有依据（phi-facts）'], origin: r.origin.kind, ref: r.origin.ref });
        continue;
      }
      agg.agents_declined++;
      answersMeta.push({ device: r.device, agent: r.agent, declined: true, declined_reason: reason, items: 0, origin: r.origin.kind, submitted_at: r.submitted_at ?? null });
      continue;
    }
    if (!Array.isArray(r.payload.items)) {
      agg.files_rejected++;
      rejected.push({ device: r.device, agent: r.agent, item_id: null, scope: 'file', reason: 'invalid_shape', reasons: ['invalid_shape'], issues: ['items 缺失或不是数组（且 declined 非 true）'], origin: r.origin.kind, ref: r.origin.ref });
      continue;
    }
    agg.agents_answered++;
    const pv = r.plugin_version;
    if (pv) { const s = String(pv); if (!agg.plugin_versions.includes(s)) agg.plugin_versions.push(s); agg.plugin_version = s; }
    answersMeta.push({
      device: r.device, agent: r.agent, declined: false, items: r.payload.items.length,
      origin: r.origin.kind, ref: r.origin.ref, legacy_layout: r.origin.legacy === true,
      submitted_at: r.submitted_at ?? null, plugin_version: pv ? String(pv) : null,
      late_by_key: r.late_by_key === true, late_key_offset: r.late_key_offset || 0
    });

    r.payload.items.forEach((item, idx) => {
      const itemId = (item && typeof item === 'object' && item.id != null && String(item.id).trim() !== '') ? String(item.id) : `#${idx + 1}`;
      entries.push({ device: r.device, agent: r.agent, item_id: itemId, item, origin: r.origin, submitted_at: r.submitted_at ?? null, plugin_version: pv ? String(pv) : null, catalogs: catalogsForJudge });
    });
  }

  // ── 裁定 + ★ 品牌化（唯一入口）
  const admitted = [];
  for (const e of entries) {
    const agg = perDeviceAgg[e.device];
    agg.items_total++;
    const verdict = adjudicate(e);
    if (!verdict.ok) {
      agg.items_rejected++;
      agg.rejection_distribution[verdict.reason] = (agg.rejection_distribution[verdict.reason] || 0) + 1;
      rejected.push({
        device: e.device, agent: e.agent, item_id: e.item_id, scope: 'item',
        reason: verdict.reason, reasons: verdict.reasons, issues: verdict.issues,
        event_ref: (e.item && e.item.event_ref) || null,
        lesson_preview: String((e.item && e.item.lesson) || '').slice(0, 40)
      });
      continue;
    }
    const a = mintAdmitted(e);
    if (!a) {
      agg.items_rejected++;
      agg.rejection_distribution.invalid_evidence = (agg.rejection_distribution.invalid_evidence || 0) + 1;
      rejected.push({ device: e.device, agent: e.agent, item_id: e.item_id, scope: 'item', reason: 'invalid_evidence', reasons: ['invalid_evidence'], issues: ['mintAdmitted 返回 null（品牌工厂拒绝）'], event_ref: (e.item && e.item.event_ref) || null });
      continue;
    }
    admitted.push(a);
  }

  // ── ★ 唯一 push 点校验：裸对象在此**抛错**（不是过滤、不是警告）
  const validSet = buildValidSet(admitted);
  for (const v of validSet) {
    const agg = perDeviceAgg[v.device];
    agg.items_valid++;
    for (const f of v.flags) agg.flags_distribution[f] = (agg.flags_distribution[f] || 0) + 1;
  }

  // ── 聚类（键 = <device>:<agent>#<item_id>，完全确定）
  const clusterInput = validSet.map((v) => ({
    key: `${v.device}:${v.agent}#${v.item_id}`,
    device: v.device, agent: v.agent, item_id: v.item_id,
    lesson: String(v.item.lesson), item: v.item, flags: v.flags,
    submitted_at: v.submitted_at ?? null, plugin_version: v.plugin_version ?? null
  })).sort((a, b) => a.key.localeCompare(b.key));

  const groups = clusterLessons(clusterInput, SIM_RULE);
  const clusters = groups.map((g) => buildCluster(g.members, g.representative));

  // ★ 复现广度排序：**跨设备优先**，再按 recurrence（design §10.7）
  clusters.sort((a, b) =>
    Number(b.cross_device) - Number(a.cross_device) ||
    b.recurrence - a.recurrence ||
    b.item_count - a.item_count ||
    b.lesson.length - a.lesson.length ||
    a.lesson.localeCompare(b.lesson) ||
    a.items.join(',').localeCompare(b.items.join(',')));
  clusters.forEach((c, i) => { c.cluster_id = `C${i + 1}`; });

  // ── 统计
  const rejectionDistribution = {};
  for (const r of rejected) rejectionDistribution[r.reason] = (rejectionDistribution[r.reason] || 0) + 1;
  const flagDistribution = {};
  for (const v of validSet) for (const f of v.flags) flagDistribution[f] = (flagDistribution[f] || 0) + 1;

  // ── 设备状态 / 版本漂移
  const allVersions = new Set();
  for (const d of dev.devices) {
    const agg = perDeviceAgg[d];
    if (agg.items_total === 0 && agg.agents_declined === 0) {
      agg.status = agg.card_dispatched === true ? 'pending' : (agg.card_dispatched === false ? 'not_dispatched' : 'unknown');
    } else { agg.status = 'submitted'; }
    for (const v of agg.plugin_versions) allVersions.add(v);
  }
  const versionDrift = {
    versions_by_device: Object.fromEntries(dev.devices.map((d) => [d, perDeviceAgg[d].plugin_version])),
    distinct: [...allVersions].sort(),
    drifted: allVersions.size > 1,
    note: '回填未带 plugin_version 的设备无法比对 —— 那是"未知"，不是"一致"'
  };
  if (versionDrift.drifted) notes.push(`★ 设备间插件版本漂移：${versionDrift.distinct.join(' vs ')} —— 不同版本行为可能不同，裁定前先确认口径`);

  const totalItems = Object.values(perDeviceAgg).reduce((n, a) => n + a.items_total, 0);
  const payload = {
    schema: 'reflect-harvest/v2',
    date,
    generated_at: new Date().toISOString(),
    device_layer: {
      devices: dev.devices, device_source: dev.source,
      local_device: dev.localDevice, local_source: dev.localSource,
      central, local_only: localOnly, allow_late: allowLate, local_root: localRoot
    },
    agents_total: src.records.length,
    agents_answered: answersMeta.filter((a) => !a.declined).length,
    agents_declined: answersMeta.filter((a) => a.declined).length,
    files_rejected: rejected.filter((r) => r.scope === 'file').length,
    items_total: totalItems,
    items_valid: validSet.length,
    items_rejected: rejected.filter((r) => r.scope === 'item').length,
    devices_total: dev.devices.length,
    devices_submitted: dev.devices.filter((d) => perDeviceAgg[d].status === 'submitted').length,
    devices_pending: dev.devices.filter((d) => perDeviceAgg[d].status === 'pending').length,
    pending_devices: dev.devices.filter((d) => perDeviceAgg[d].status === 'pending'),
    per_device: perDeviceAgg,
    version_drift: versionDrift,
    rejected,
    rejection_distribution: rejectionDistribution,
    flags_distribution: flagDistribution,
    clusters,
    answers_meta: answersMeta,
    dedupe: { dropped_duplicate_sources: src.duplicates },
    similarity: similarityReport(clusterInput, SIM_RULE),
    similarity_rule: SIM_RULE,
    sync_duplicate_rule: SYNC_DUP_RULE,
    valid_items: validSet.map((v) => ({
      device: v.device, agent: v.agent, item_id: v.item_id, flags: v.flags,
      event_ref: v.item.event_ref ?? null, pit: v.item.pit, lesson: v.item.lesson,
      related_rule: v.item.related_rule ?? '无', suggestion: v.item.suggestion, evidence: v.item.evidence,
      submitted_at: v.submitted_at ?? null, plugin_version: v.plugin_version ?? null
    })),
    catalog: { rules_available: catalog.available.rules, rules_count: catalog.rules.size, phis_available: catalog.available.phis, phis_count: catalog.phis.size },
    notes
  };

  log(`harvest ${dryRun ? '[dry-run] ' : ''}date=${date} devices=${dev.devices.join(',')} src=${dev.source}`, {
    agents: `${payload.agents_answered}/${payload.agents_total} 已回填`,
    devices: `${payload.devices_submitted}/${payload.devices_total} submitted · ${payload.devices_pending} pending`,
    // 口径必须分开写：把条目级与文件级混成一个 "rejected" 会让日志与 payload 的 items_rejected 对不上
    items: `${validSet.length} valid / ${rejected.filter((r) => r.scope === 'item').length} item-rejected / ${rejected.filter((r) => r.scope === 'file').length} file-rejected`,
    clusters: clusters.length,
    cross_device_clusters: clusters.filter((c) => c.cross_device).length,
    rejection_distribution: rejectionDistribution
  }, { dryRun });

  return payload;
}

/**
 * 组装一个集群：★ agents 升级为 `<device>:<agent>`，并做同步盘污染剔除。
 * `possible_sync_duplicate` 的判定（两条都要满足）：
 *   ① `lesson` **逐字相同**（trim 后严格相等）
 *   ② 跨 ≥2 设备 **且** `evidence.ts` 时点接近（|Δt| ≤ SYNC_DUP_RULE.windowMs）
 * 命中后：只保留字典序最小的那一条计入 recurrence，其余进 `sync_duplicate_members`
 * （它们**仍然可见**，只是不伪造跨设备信号）。
 */
function buildCluster(members, representative) {
  const keyOf = (m) => `${m.device}:${m.agent}#${m.item_id}`;
  const tsOf = (m) => {
    const v = m.item && m.item.evidence ? m.item.evidence.ts : null;
    const t = v ? Date.parse(v) : NaN;
    return Number.isFinite(t) ? t : null;
  };

  const byLesson = new Map();
  for (const m of members) {
    const k = String(m.lesson).trim();
    if (!byLesson.has(k)) byLesson.set(k, []);
    byLesson.get(k).push(m);
  }

  const syncDupKeys = new Set();
  const syncDupGroups = [];
  for (const [, group] of byLesson) {
    if (group.length < 2) continue;
    const devicesIn = [...new Set(group.map((m) => m.device))].sort();
    if (devicesIn.length < 2) continue;                        // 同设备内重复不算同步盘污染
    const times = group.map(tsOf).filter((t) => t !== null);
    const near = times.length < 2 ? true : (Math.max(...times) - Math.min(...times)) <= SYNC_DUP_RULE.windowMs;
    if (!near) continue;                                       // 时点差太远 → 不像同一份文件的副本
    const sorted = group.slice().sort((a, b) => a.key.localeCompare(b.key));
    const dropped = sorted.slice(1);
    dropped.forEach((m) => syncDupKeys.add(keyOf(m)));
    syncDupGroups.push({ devices: devicesIn, kept: keyOf(sorted[0]), dropped: dropped.map(keyOf), reason: 'lesson 逐字相同且跨设备、时点接近 → 疑似同步盘/复制粘贴产物，不重复计入 recurrence' });
  }

  const counted = members.filter((m) => !syncDupKeys.has(keyOf(m)));
  const agents = [...new Set(counted.map((m) => `${m.device}:${m.agent}`))].sort();
  const allAgents = [...new Set(members.map((m) => `${m.device}:${m.agent}`))].sort();
  const devices = [...new Set(counted.map((m) => m.device))].sort();
  const refs = [...new Set(members.flatMap((m) => {
    const rr = String(m.item.related_rule ?? '').trim();
    return rr === '' ? [] : rr.split(/[\/,、;；\s]+/).map((s) => s.trim()).filter(Boolean);
  }))].sort();
  const flags = new Set(members.flatMap((m) => m.flags));
  if (syncDupKeys.size) flags.add('possible_sync_duplicate');
  if (devices.length >= 2) flags.add('cross_device');

  return {
    cluster_id: null,
    lesson: representative,
    agents,
    all_agents: allAgents,
    devices,
    cross_device: devices.length >= 2,
    // ★ 复现广度必须按 **<设备>:<智能体>** 复合键去重。
    //   血泪（本工具开发中实测）：初版复用了 lesson.js 的 recurrenceOf()，而它按 `m.agent`（**只有智能体名**）去重
    //   → 两台设备上恰好同名的 agent-echo 被合并成 1 → recurrence 少算 1，
    //   而同一行的 `lab-mbp×1 + mac-mini×3 + mbp×1` 明细加起来是 5 —— **明细与计数自相矛盾**。
    //   现在 D 项的「产出不变量」会当场抓住这类自相矛盾（recurrence === agents.length）。
    recurrence: new Set(counted.map((m) => `${m.device}:${m.agent}`)).size,
    recurrence_raw: new Set(members.map((m) => `${m.device}:${m.agent}`)).size,
    item_count: members.length,
    refs,
    flags: [...flags].sort(),
    items: members.map(keyOf).sort(),
    sync_duplicate_members: [...syncDupKeys].sort(),
    sync_duplicate_groups: syncDupGroups,
    members: members.map((m) => ({
      device: m.device, agent: m.agent, item_id: m.item_id,
      event_ref: m.item.event_ref ?? null, pit: m.item.pit, lesson: m.item.lesson,
      related_rule: m.item.related_rule ?? '无', suggestion: m.item.suggestion, evidence: m.item.evidence,
      submitted_at: m.submitted_at, plugin_version: m.plugin_version,
      sync_duplicate: syncDupKeys.has(keyOf(m))
    }))
  };
}

/* -------------------------------------------------------------------------- *
 * 人类可读摘要（--summary）
 * -------------------------------------------------------------------------- */

const REASON_EXPLAIN = {
  invalid_evidence: '证据不完整（缺 ts 或缺 cmd/output）—— 质量门死线，结构上进不了 valid',
  incomplete: '必填字段缺失（pit / lesson / suggestion.type）',
  invalid_type: 'suggestion.type 不在四选一',
  invalid_decline: 'declined:true 但未给理由（文件级）',
  invalid_shape: '不是一份合法回填（文件级）'
};

export function formatSummary(p) {
  const L = [];
  const push = (s = '') => L.push(s);
  const dl = p.device_layer;
  push(`每日反思 · 收牌摘要 · ${p.date}`);
  push(`  设备表: [${dl.devices.join(', ')}]（来源 ${dl.device_source}） · 本机=${dl.local_device}（${dl.local_source}）`);
  push(`  源: 本地 ${dl.local_root} · 中央黑板 ${dl.central}${dl.local_only ? ' · ★--local-only（未触网）' : ''}${dl.allow_late ? ' · --allow-late（收补填）' : ''}`);
  push(`  设备: ${p.devices_submitted}/${p.devices_total} 已回填 · ${p.devices_pending} 待回填(pending)${p.pending_devices.length ? ' → ' + p.pending_devices.join(', ') : ''}`);
  push(`  条目: ${p.items_valid} 条有效 / ${p.items_rejected} 条条目级拒收（共 ${p.items_total} 条）· 文件级拒收 ${p.files_rejected}`);
  push('');

  push('★ 按设备分组统计:');
  for (const d of dl.devices) {
    const a = p.per_device[d];
    if (!a) continue;
    const statusMark = { submitted: '✅ 已回填', pending: '⏳ pending（卡已派、人未填——可能离线）', not_dispatched: '· 未派卡', unknown: '? 状态未知' }[a.status] || a.status;
    push(`  [${d}] ${statusMark}`);
    push(`      来源: 本地 ${a.sources.local} · 黑板 ${a.sources.blackboard}` +
      `${a.late_accepted ? ` · 补填 ${a.late_accepted}` : ''}${a.out_of_window ? ` · 窗口外跳过 ${a.out_of_window}` : ''}${a.device_mismatch ? ` · ★设备不符拒绝 ${a.device_mismatch}` : ''}`);
    push(`      条目: ${a.items_valid} 有效 / ${a.items_rejected} 拒收 · 智能体 ${a.agents_answered} 已填 / ${a.agents_declined} 弃权 · 文件级拒收 ${a.files_rejected}`);
    const rd = Object.entries(a.rejection_distribution || {});
    if (rd.length) push(`      拒收: ${rd.map(([k, v]) => `${k}×${v}`).join(' · ')}`);
    const fd = Object.entries(a.flags_distribution || {});
    if (fd.length) push(`      标记: ${fd.map(([k, v]) => `${k}×${v}`).join(' · ')}`);
    if (a.card_dispatched !== null) push(`      卡: ${a.card_dispatched ? '已派出' : '未派出'}（${a.card_via}）`);
    push(`      插件版本: ${a.plugin_version || '（未标）'}`);
    if (a.errors && a.errors.length) push(`      ⚠ ${a.errors.slice(0, 3).join(' | ')}${a.errors.length > 3 ? ` …(+${a.errors.length - 3})` : ''}`);
  }
  if (p.version_drift.drifted) { push(''); push(`  ★ 设备间版本漂移: ${p.version_drift.distinct.join(' vs ')}`); }
  push('');

  push('★ 全量拒收原因分布:');
  const dist = Object.entries(p.rejection_distribution).sort((a, b) => b[1] - a[1]);
  if (!dist.length) push('  （无拒收）');
  for (const [k, v] of dist) push(`  ${String(v).padStart(2)} × ${k} — ${REASON_EXPLAIN[k] || ''}`);
  push('');

  push('★ 跨设备复现（★ 跨设备优先，再按广度降序 —— 飞轮指标，不是提交顺序）:');
  if (!p.clusters.length) push('  （无有效条目）');
  for (const c of p.clusters) {
    const perDev = {};
    for (const a of c.agents) { const d = a.split(':')[0]; perDev[d] = (perDev[d] || 0) + 1; }
    const breakdown = Object.entries(perDev).map(([d, n]) => `${d}×${n}`).join(' + ');
    push(`  [${c.cluster_id}] ${c.cross_device ? '★跨设备 ' : ''}recurrence=${c.recurrence}（${breakdown}）· 条目 ${c.item_count}`);
    push(`       ${c.lesson}`);
    if (c.sync_duplicate_members.length) push(`       ⚠ possible_sync_duplicate（逐字相同、不重复计入 recurrence）: ${c.sync_duplicate_members.join(', ')}`);
    if (c.refs.length) push(`       引用: ${c.refs.join(' / ')}${c.flags.includes('unknown_rule') ? '  ⚠️ unknown_rule' : ''}`);
  }
  if (Object.keys(p.flags_distribution).length) {
    push('');
    push(`标记（不拒收，仅提示）: ${Object.entries(p.flags_distribution).map(([k, v]) => `${k}×${v}`).join(' · ')}`);
  }
  if (p.dedupe.dropped_duplicate_sources.length) {
    push('');
    push(`源去重（同设备同 agent 多来源，按"黑板 > 本地"保留一份）: ${p.dedupe.dropped_duplicate_sources.length} 条`);
    p.dedupe.dropped_duplicate_sources.slice(0, 5).forEach((d) => push(`  · ${d.key}：保留 ${d.kept}，丢弃 ${d.dropped}`));
  }
  if (p.notes.length) { push(''); push('说明:'); p.notes.forEach((n) => push(`  · ${n}`)); }
  push('');
  push(`参照库: 规则 ${p.catalog.rules_count} 条（${p.catalog.rules_available ? 'ok' : '不可用'}） · 哲学 ${p.catalog.phis_count} 条（${p.catalog.phis_available ? 'ok' : '不可用'}）`);
  push(`日志: ${LOG_FILE}`);
  return L.join('\n');
}

/** --help / selfcheck 复用的能力边界段落 */
export function capabilityLines() {
  return [
    `能做: 全设备收牌 —— 本机 <localRoot>/answers/<device>/<date>/ + 中央黑板 data/reflect/answers/<device>/<date>`,
    `      → 五类校验（★证据完整性 / 必填字段 / type 合法性 / related_rule 存在性 / declined 合法性）`,
    `      → (device,agent) 去重（黑板>本地）→ 跨设备聚类 → 复现广度（<设备>:<智能体>）+ cross_device 标注`,
    `      → 按设备分组统计 + 版本漂移检查 + pending/not_dispatched 区分 → 写 harvested-<date>.json`,
    `不能做: 写黑板（只 GET，绝不 PUT/POST —— 谁回填谁写，汇集方不得代笔）`,
    `        写 RULES.md / governance-philosophy.json / rules.json（写出口白名单里没有这些目录）`,
    `        修改任何回填写入文件、删除回填、代上游建目录；执行任何外部命令（命令白名单=空集）`,
    `没有那个入口: 无 --skip-evidence/--force/--lenient；mintAdmitted() 是条目入 valid 的唯一入口；lib/http.js 无 method 参数`
  ];
}

export { GateError, ALL_REJECT_REASONS, ITEM_FLAGS, DEFAULT_DEVICES, DEFAULT_CENTRAL };
