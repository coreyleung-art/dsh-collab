/**
 * synthesize.js — 提炼内核（⑤ reflect-synthesize）
 * =============================================================================
 * 输入 harvested-<date>.json → 输出 proposal-<date>.md（**待用户裁定**）。
 *
 * 四步（每步都在输出里体现）：
 *   1) 对照现有库   —— judgeCluster()：already-application / extends-existing / new-dimension / conflicts / unclear
 *   2) 分类归档     —— classify()：拟新增哲学 / 拟新增规则 / 并入·补维 / 转规范 / 归档为案例 / 需裁决冲突 / 需人工复核
 *   3) ★ 复现广度排序 —— **(cross_device, recurrence) 二元组**：跨设备优先，同设备内再按广度
 *   4) 生成提案     —— buildProposal()：看一眼就能裁
 *
 * ★ 唯一"需要判断"的环节，所以纪律是：**规则能定的用规则；规则定不了的显式标 unclear 交人工/LLM**。
 *
 * ★ 输入侧纵深防御：harvested 是磁盘上的文件，可能被手改。
 *   任何 cluster member 若**没有证据**，一律丢弃并计数，不进提案 ——
 *   无证据的条目不能被摆到用户面前让他据此裁定（同 harvest 的质量门死线）。
 */
import fs from 'node:fs';
import path from 'node:path';
import { DATA_DIR, LOG_FILE, log, writeProposal } from './out.js';
import { GateError, vetClusterMember, JUDGMENTS, JUDGE_RULE } from './gate.js';
import { loadCatalog } from './catalog.js';
import { judgeCluster, classify, sortKey, ANALYZE_META } from './analyze.js';
import { buildProposal } from './proposal.js';

export class SynthesizeIOError extends Error {
  constructor(code, message) { super(message); this.name = 'SynthesizeIOError'; this.code = code; }
}

export const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function harvestedPathOf(date, dir) {
  return path.join(dir || DATA_DIR, `harvested-${date}.json`);
}

/**
 * @param {string} date
 * @param {{dryRun?:boolean, harvestedDir?:string, proposalDir?:string}} opts
 */
export function synthesize(date, opts = {}) {
  if (!DATE_RE.test(String(date))) throw new SynthesizeIOError('BAD_DATE', `日期格式必须是 YYYY-MM-DD，收到 '${date}'`);
  const dryRun = opts.dryRun === true;
  const srcPath = harvestedPathOf(date, opts.harvestedDir);

  let harvested;
  try { harvested = JSON.parse(fs.readFileSync(srcPath, 'utf8')); }
  catch (e) {
    if (e.code === 'ENOENT') {
      throw new SynthesizeIOError('NO_HARVESTED',
        `收牌产物不存在：${srcPath}\n（上游 ④ reflect-harvest 应先跑；本工具不代跑、不猜。命令：node ../dsh-plugin-reflect-harvest/cli.js --date ${date}）`);
    }
    throw new SynthesizeIOError('BAD_HARVESTED', `收牌产物不可解析：${srcPath}（${e.message}）`);
  }
  if (!harvested || typeof harvested !== 'object' || !Array.isArray(harvested.clusters)) {
    throw new SynthesizeIOError('BAD_SHAPE', `收牌产物结构不对（缺 clusters 数组）：${srcPath}`);
  }

  const catalog = loadCatalog();
  const notes = [...(harvested.notes || []), ...catalog.notes];
  const catalogUsable = catalog.available.rules || catalog.available.phis;
  if (!catalogUsable) {
    notes.push('★ 参照库不可读 → 本批 cluster **全部标 unclear**（读不到库 ≠ 库里没有；混为一谈会把"读失败"误判成"新维度提案"）');
  }

  // ── 输入侧纵深防御：无证据的 member 丢弃
  const droppedNoEvidence = [];
  const clusters = [];
  for (const c of harvested.clusters) {
    const kept = [];
    for (const m of (c.members || [])) {
      const v = vetClusterMember(m);
      if (v.ok) kept.push(m);
      else droppedNoEvidence.push({ cluster_id: c.cluster_id, device: m.device, agent: m.agent, item_id: m.item_id, reason: v.reason });
    }
    if (!kept.length) { notes.push(`簇 ${c.cluster_id} 的成员全部无证据 → 整簇丢弃，不进提案`); continue; }
    if (kept.length !== (c.members || []).length) notes.push(`簇 ${c.cluster_id}：${(c.members || []).length - kept.length} 条成员无证据，已丢弃（不进提案）`);
    clusters.push({ ...c, members: kept, item_count: kept.length });
  }
  if (droppedNoEvidence.length) notes.push(`★ 输入侧证据门：丢弃 ${droppedNoEvidence.length} 条无证据成员（harvested 文件可能被手改；无证据的条目不能摆到用户面前让他据此裁定）`);

  // ── 四步：对照 → 分类 → 排序 → 生成
  const items = clusters.map((c) => {
    const judge = catalogUsable
      ? judgeCluster(c, catalog)
      : { judgment: 'unclear', judgment_reason: '参照库不可读 → 无法对照（不猜）', confidence: 'low', refs: [], matched: [], best_match: null, novelty_vs_best: null, declared_types: [], explicit_conflict: null, cross_device: (c.devices || []).length >= 2, device_count: (c.devices || []).length, needs_human: true };
    const cls = classify(c, judge);
    return { cluster: c, judge, cls };
  });

  // ★ 第 3 步 · 排序：(cross_device, recurrence) 二元组降序（跨设备优先）
  items.sort((a, b) => {
    const ka = sortKey(a.cluster, a.judge), kb = sortKey(b.cluster, b.judge);
    return kb.cross_device - ka.cross_device ||
      kb.recurrence - ka.recurrence ||
      kb.devices - ka.devices ||
      kb.item_count - ka.item_count ||
      ka.lesson.localeCompare(kb.lesson);
  });
  items.forEach((it, i) => { it.rank = i + 1; });

  // ── 统计
  const judgmentDistribution = {};
  const categoryDistribution = {};
  for (const it of items) {
    judgmentDistribution[it.judge.judgment] = (judgmentDistribution[it.judge.judgment] || 0) + 1;
    categoryDistribution[it.cls.category] = (categoryDistribution[it.cls.category] || 0) + 1;
  }
  const stats = {
    devices: (harvested.device_layer && harvested.device_layer.devices) || [],
    device_source: (harvested.device_layer && harvested.device_layer.device_source) || 'unknown',
    devices_total: harvested.devices_total ?? null,
    devices_submitted: harvested.devices_submitted ?? null,
    devices_pending: harvested.devices_pending ?? null,
    pending_devices: harvested.pending_devices || [],
    items_valid: harvested.items_valid ?? null,
    items_rejected: harvested.items_rejected ?? null,
    files_rejected: harvested.files_rejected ?? null,
    rejection_distribution: harvested.rejection_distribution || {},
    flags_distribution: harvested.flags_distribution || {},
    version_drift: harvested.version_drift || null,
    judgment_distribution: judgmentDistribution,
    category_distribution: categoryDistribution,
    dropped_no_evidence: droppedNoEvidence
  };

  const markdown = buildProposal({
    date, version: opts.version || '0.0.0-unknown', items, stats, notes,
    sourceFile: srcPath
  });

  const version = opts.version || '0.0.0-unknown';
  const result = {
    schema: 'reflect-proposal/v1',
    date,
    generated_at: new Date().toISOString(),
    source_file: srcPath,
    output_file: null,
    version,
    counts: {
      clusters: items.length,
      need_ruling: items.filter((i) => i.cls.category !== '归档为案例').length,
      archived: items.filter((i) => i.cls.category === '归档为案例').length,
      need_human: items.filter((i) => i.cls.needs_human).length,
      cross_device: items.filter((i) => (i.cluster.devices || []).length >= 2).length,
      dropped_no_evidence: droppedNoEvidence.length
    },
    judgment_distribution: judgmentDistribution,
    category_distribution: categoryDistribution,
    items: items.map((it) => ({
      rank: it.rank,
      cluster_id: it.cluster.cluster_id,
      lesson: it.cluster.lesson,
      recurrence: it.cluster.recurrence,
      cross_device: (it.cluster.devices || []).length >= 2,
      devices: it.cluster.devices || [],
      agents: it.cluster.agents || [],
      recurrence_breakdown: (it.cluster.agents || []).reduce((acc, a) => { const d = String(a).split(':')[0]; acc[d] = (acc[d] || 0) + 1; return acc; }, {}),
      sync_duplicate_members: it.cluster.sync_duplicate_members || [],
      flags: it.cluster.flags || [],
      judgment: it.judge.judgment,
      confidence: it.judge.confidence,
      best_match: it.judge.best_match ? { kind: it.judge.best_match.kind, id: it.judge.best_match.id, overlap: it.judge.best_match.overlap, novelty: it.judge.best_match.novelty } : null,
      category: it.cls.category,
      target: it.cls.target,
      needs_human: it.cls.needs_human,
      ruling_options: it.cls.category
    })),
    dropped_no_evidence: droppedNoEvidence,
    stats,
    notes
  };

  if (!dryRun) {
    const w = writeProposal(date, markdown, {});
    result.output_file = w.target;
    result.output_sha256 = w.sha256;
    result.output_bytes = w.bytes;
  } else {
    const w = writeProposal(date, markdown, { dryRun: true });
    result.output_file = null;
    result.planned_file = w.target;
    result.planned_bytes = w.bytes;
  }

  log(`synthesize ${dryRun ? '[dry-run] ' : ''}date=${date}`, {
    src: srcPath, clusters: items.length,
    cross_device: result.counts.cross_device,
    need_ruling: result.counts.need_ruling,
    judgments: judgmentDistribution,
    categories: categoryDistribution
  }, { dryRun });

  return { result, markdown };
}

/** 人类可读摘要（--summary / 终端） */
export function formatSummary(r) {
  const L = [];
  const P = (s = '') => L.push(s);
  P(`每日反思 · 提炼摘要 · ${r.date}`);
  P(`  源: ${r.source_file}`);
  P(`  设备: ${(r.stats.devices || []).join('、')}（${r.stats.device_source}）· 已回填 ${r.stats.devices_submitted}/${r.stats.devices_total} · pending ${r.stats.devices_pending}`);
  P(`  簇 ${r.counts.clusters} 个（★跨设备 ${r.counts.cross_device}）· 需裁定 ${r.counts.need_ruling} · 归档 ${r.counts.archived} · 需人工复核 ${r.counts.need_human}`);
  P('');
  P('★ 按（跨设备, 复现广度）排序 —— 跨设备优先:');
  for (const it of r.items) {
    const devs = it.devices.join('+') || '?';
    const bd = Object.entries(it.recurrence_breakdown).map(([d, n]) => `${d}×${n}`).join('+');
    P(`  P${String(it.rank).padStart(2)} ${it.cross_device ? '★跨设备' : '  单设备'} rec=${it.recurrence}（${bd}） [${
      (it.judgment === 'unclear' ? '⚠️unclear' : it.judgment).padEnd(19)}] → ${it.category}`);
    P(`      ${it.lesson}`);
  }
  P('');
  P(`★ 判定分布: ${Object.entries(r.judgment_distribution).map(([k, v]) => `${k}×${v}`).join(' · ')}`);
  P(`★ 处置分布: ${Object.entries(r.category_distribution).map(([k, v]) => `${k}×${v}`).join(' · ')}`);
  if (r.dropped_no_evidence.length) P(`★ 输入侧丢弃（无证据）: ${r.dropped_no_evidence.length} 条`);
  P('');
  P(r.output_file ? `已写入 ${r.output_file}（${r.output_bytes}B · sha256 ${r.output_sha256}）` : `[dry-run] 未写入；计划产物 ${r.planned_file}（${r.planned_bytes}B）`);
  P(`日志: ${LOG_FILE}`);
  return L.join('\n');
}

export { GateError, JUDGMENTS, JUDGE_RULE, ANALYZE_META, DATA_DIR };
