/**
 * feedback.js — 飞轮闭环点：**把新规则推给所有设备上的相关智能体**（跨设备层 v1.1）
 * =============================================================================
 * 规则入册后如果躺着不动，**没有任何智能体会知道**。所以入册成功后必须：
 *   ① 生成反馈卡：本机 data/reflect/feedback-<date>.md
 *   ② 写黑板「规则变更通知」data/registry/reflect-feedback-<date>（全设备可检索；含"约束什么 + 哪些设备的哪些智能体该注意"）
 *   ③ 全卡上**中央黑板** data/reflect/feedback/<date>（跨设备汇聚点，设计文档 §10.2）
 *   ④ --notify 时给相关智能体发**短消息**（≤50 字，先落黑板再发「看黑板 <key>」）；
 *      本机智能体走本机黑板；**其他设备走中央黑板的待投递队列 notes/<device>/**（离线也能收到，§10.4）
 *   ⑤ "相关智能体" = `<device>:<agent>`：提案显式声明 → 资源归属（资源在哪台设备）→ 设备发现表；判不出如实说，不猜
 *
 * ★ 跨设备安全（继承 + 新增）：
 *   · 反馈卡落盘 / 上黑板前先跑**凭据扫描 + 脱敏**，脱敏后再**断言一次**（fail-closed：残留即拒写）
 *   · **只写自己命名空间**：正文只落 data/reflect/ · data/registry/；notes/ 仅限 ≤50 字短指引
 *   · 黑板 key 首段必须纯小写字母 [a-z]+（否则黑板 400 bad key）
 *   · 每次 PUT 之后**必须回读校验**（返回 200 ≠ 落地）
 * ★ 本文件是全包**唯一**的对外 HTTP 调用点（bbRequest），出站主机必须先过 assertBbHost 白名单。
 *   包内零 shell 出站：不 import child_process，无 exec/spawn 调用点（--lean4-check F 项证明）。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import {
  GateError, assertBbHost, assertWriteKey, redactCredentials, redactDeep, redactDeepCounted, assertNoCredentials,
  classifyBbReadback, MAX_POINTER_CHARS
} from './gate.js';
import { resolveRoot, inRoot, REL, readText, sha256 } from './enroll.js';
import { VERSION } from './version.js';
import { log } from './log.js';

/** 本机黑板（总线宿主）默认地址。 */
export const LOCAL_BB_DEFAULT = 'http://127.0.0.1:8792';
/** 中央黑板（跨设备汇聚点，设计文档 §10.2 实测可读写）。 */
export const CENTRAL_BB_DEFAULT = 'http://106.53.214.108:8792';
export const MAX_NOTIFY_CHARS = MAX_POINTER_CHARS;

/** 全卡 key：data/reflect/feedback/<date>（首段 data 纯小写 ✅） */
export const fullCardKey = (date) => `data/reflect/feedback/${date}`;
/** 规则变更通知卡 key（全设备可检索） */
export const noticeKey = (date) => `data/registry/reflect-feedback-${date}`;
/** 短指引待投递队列 key（该设备上线后自取） */
export const pointerKey = (device, date) => `notes/${device}/reflect-feedback-${date}`;

/**
 * 设备名别名表（冻结）：node-id / 表内设备名 → **总线域短名**。
 * 依据（可核）：`devices/device-registry.md`（node-macmini↔mac-mini / node-pci9↔PC-i9 / node-mbp↔MacBook Pro）
 * 与总线域实测（黑板 notes/ 第二段：mac-mini 859 键 · mbp 555 键 · i9 1243 键）。
 * 可用 <root>/data/registry/device-aliases.json 覆盖。
 */
export const DEVICE_ALIASES = Object.freeze({
  macmini: 'mac-mini', 'mac-mini': 'mac-mini', nodemacmini: 'mac-mini',
  mbp: 'mbp', macbookpro: 'mbp', nodembp: 'mbp', 'mbp-agent': 'mbp',
  i9: 'i9', pci9: 'i9', nodepci9: 'i9', 'pc-i9': 'i9'
});

const norm = (s) => String(s).toLowerCase().replace(/[^a-z0-9]/g, '');
const dedupeHidden = (list) => [...new Map(list.map((h) => [`${h.kind}|${h.sample}`, h])).values()];

/** 已知设备（真实来源：设备发现表 → 设备登记表 → 别名表 → 冻结兜底）。 */
export function knownDevices(root) {
  const r = resolveRoot(root);
  const out = new Set();
  const disc = path.join(r, 'data', 'discovery', 'agents');
  if (fs.existsSync(disc)) for (const f of fs.readdirSync(disc)) if (f.endsWith('.json')) out.add(f.replace(/\.json$/, ''));
  const reg = path.join(r, 'devices', 'device-registry.md');
  if (fs.existsSync(reg)) {
    for (const m of readText(reg).matchAll(/^\|\s*(node-[A-Za-z0-9-]+)\s*\|\s*([^|]+?)\s*\|/gm)) {
      for (const raw of [m[1], m[2]]) {
        const v = String(raw).trim().toLowerCase().replace(/\s+/g, '-');
        out.add(v);
        const alias = DEVICE_ALIASES[norm(v)];
        if (alias) out.add(alias);
      }
    }
  }
  const aliasFile = path.join(r, 'data', 'registry', 'device-aliases.json');
  if (fs.existsSync(aliasFile)) {
    try { for (const [k, v] of Object.entries(JSON.parse(readText(aliasFile)))) { out.add(String(v)); out.add(String(k)); } }
    catch (e) { log('feedback.aliases-unreadable', { result: { error: e.message } }); }
  }
  for (const d of ['mac-mini', 'mbp', 'i9']) out.add(d);
  return [...out].sort();
}

/** 本机设备名（--device > DSH_NODE_ID > 主机名匹配登记表 > 主机名派生）。 */
export function resolveDeviceName(root, explicit) {
  if (explicit) {
    const d = String(explicit).trim();
    if (!/^[a-z][a-z0-9-]*$/.test(d)) throw new GateError('BAD_DEVICE', `拒绝：设备名 '${d}' 非法（需 ^[a-z][a-z0-9-]*$，纯小写，可含连字符数字）`);
    return { device: d, source: 'explicit' };
  }
  if (process.env.DSH_NODE_ID) {
    const d = String(process.env.DSH_NODE_ID).trim().toLowerCase();
    if (/^[a-z][a-z0-9-]*$/.test(d)) return { device: d, source: 'env:DSH_NODE_ID' };
  }
  const host = os.hostname().split('.')[0];
  const h = norm(host);
  for (const k of knownDevices(root)) {
    const nk = norm(k);
    if (nk && h.includes(nk)) return { device: DEVICE_ALIASES[nk] || k, source: `hostname:${host}→${k}`, matched: k };
  }
  const derived = host.toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-|-$/g, '') || 'unknown-device';
  return {
    device: derived, source: `hostname:${host}(派生)`,
    note: `未能与设备登记表匹配，已用主机名派生名 '${derived}' —— 跨设备投递请显式 --device 指定（否则可能投错域）`
  };
}

/* ══════════════════════════ 相关智能体（跨设备） ══════════════════════════ */

/** 把 token 规范成 {device, agent}：`mbp:review` / `mbp`（整设备）/ `review`（本机 agent）。 */
export function normalizeAgentToken(token, { localDevice, known }) {
  const t = String(token).trim();
  if (!t) return null;
  if (t.includes(':')) {
    const [d, ...rest] = t.split(':');
    return { device: String(d).trim(), agent: rest.join(':').trim() || null };
  }
  if (known.includes(t)) return { device: t, agent: null };
  return { device: localDevice, agent: t };
}

function dedupeAgents(list) {
  const seen = new Set();
  const out = [];
  for (const a of list) {
    if (!a || !a.device) continue;
    const k = `${a.device}:${a.agent || '*'}`;
    if (seen.has(k)) continue;
    seen.add(k); out.push({ ...a, key: k });
  }
  return out;
}

function groupByDevice(agents) {
  const map = new Map();
  for (const a of agents) {
    if (!map.has(a.device)) map.set(a.device, []);
    if (a.agent) map.get(a.device).push(a.agent);
  }
  return [...map.entries()].map(([device, inner]) => ({ device, agents: inner }));
}

/**
 * 判定"相关智能体"（**跨设备**：`<device>:<agent>`）。四级依据（可信度降序），并如实回报用了哪一级：
 *   1) 提案显式声明 related_agents（支持 `device:agent`）
 *   2) 资源归属：提案 resources → data/registry/resource-owners.json（**资源在哪台设备**）+ `device:<name>` 自述
 *   3) 设备发现表 data/discovery/agents/*（含 sessions[].role → `device:role`）
 *   4) 判不出 → 空列表 + 如实说明，绝不猜
 */
export function resolveRelatedAgents({ root, results, proposals, localDevice }) {
  const r = resolveRoot(root);
  const known = knownDevices(r);
  const ctx = { localDevice, known };
  const explicit = [];
  const resources = [];
  for (const res of results) {
    const p = proposals && res.proposal_id ? proposals.get(res.proposal_id) : null;
    if (p && Array.isArray(p.related_agents)) explicit.push(...p.related_agents);
    if (p && Array.isArray(p.resources)) resources.push(...p.resources);
  }
  const pack = (source, agents, extra = {}) => {
    const list = dedupeAgents(agents);
    return { source, agents: list, devices: groupByDevice(list), local_device: localDevice, known_devices: known, ...extra };
  };

  if (explicit.length) return pack('explicit:related_agents', explicit.map((t) => normalizeAgentToken(t, ctx)));

  if (resources.length) {
    const ownerFile = path.join(r, 'data', 'registry', 'resource-owners.json');
    const owners = [];
    if (fs.existsSync(ownerFile)) {
      try {
        const map = JSON.parse(readText(ownerFile));
        for (const res of resources) {
          for (const [resKey, owner] of Object.entries(map)) {
            if (!String(res).includes(resKey)) continue;
            if (typeof owner === 'string') owners.push({ device: owner, agent: null });
            else {
              const dev = owner.device || owner.owner || null;
              if (dev) owners.push({ device: dev, agent: null });
              for (const a of owner.agents || []) owners.push({ device: dev || localDevice, agent: a });
            }
          }
        }
      } catch (e) { log('feedback.owners-unreadable', { result: { error: e.message } }); }
    }
    for (const res of resources) {
      const m = /^([a-z][a-z0-9-]*):(.+)$/i.exec(String(res));
      if (m && (known.includes(m[1]) || m[1] === 'device')) owners.push(normalizeAgentToken(m[1] === 'device' ? m[2] : String(res), ctx));
    }
    if (owners.length) return pack('resources:resource-owners+自述设备', owners);
  }

  const disc = path.join(r, 'data', 'discovery', 'agents');
  if (fs.existsSync(disc)) {
    const agents = [];
    for (const f of fs.readdirSync(disc)) {
      if (!f.endsWith('.json')) continue;
      const dev = f.replace(/\.json$/, '');
      let added = false;
      try {
        const o = JSON.parse(readText(path.join(disc, f)));
        for (const s of o.sessions || []) if (s && s.role) { agents.push({ device: dev, agent: String(s.role) }); added = true; }
      } catch (e) { log('feedback.discovery-unreadable', { input: { file: f }, result: { error: e.message } }); }
      if (!added) agents.push({ device: dev, agent: null });
    }
    if (agents.length) return pack('discovery:data/discovery/agents', agents);
  }

  return pack('none', [], {
    note: '无法判定相关智能体：提案未给 related_agents，且资源归属表 / 设备发现表都不存在 —— 已如实上报，不猜（反馈卡与黑板登记仍会写）'
  });
}

/* ══════════════════════════ 反馈卡 ══════════════════════════ */

export function buildFeedbackCard({ date, results, related, ts, device }) {
  const enrolled = results.filter((x) => x.applied);
  const lines = [
    `# 反思入册 · 反馈卡 ${date}`,
    '',
    `> 生成: ${ts} · 采集者设备(origin_device): ${device} · dsh-plugin-reflect-enroll v${VERSION}`,
    `> 依据 phi-user-sovereignty（执行经用户确认）· 跨设备层设计: docs/daily-reflection-pipeline-design-v1.md §10`,
    '> **本卡是数据飞轮的闭环点**：入册完成 ≠ 生效；新规则必须被相关智能体（含其他设备上的）看到才算生效。',
    '',
    `## 本次入册（${enrolled.length} 条）`,
    ''
  ];
  enrolled.forEach((res, i) => {
    lines.push(`### ${i + 1}. [${res.target}] ${res.ref} — ${res.summary || ''}`, '');
    lines.push(`- **落点**: ${res.wrote.join(' · ')}`);
    lines.push(`- **裁定**: ${res.decision}${res.reason ? '（用户理由：' + res.reason + '）' : ''}`);
    if (res.notes && res.notes.length) lines.push(`- **写入细节**: ${res.notes.join('；')}`);
    const what = res.entry ? (res.entry.core || res.entry.summary || res.entry.detail) : null;
    if (what) {
      lines.push(`- **它约束什么**: ${String(what).slice(0, 500)}${String(what).length > 500 ? '…' : ''}`);
      lines.push(`- **相关智能体该注意什么**: 下次做 ${res.target === 'philosophy' ? '涉及该哲学覆盖范围的决策' : '触及该规则所辖资源/流程的动作'} 时，先按此约束自检；`);
      lines.push('  本工具不替你改变行为 —— 约束生效靠你把它读进去（有异议走提案流程，需新裁定）。');
    }
    lines.push('');
  });
  lines.push('## 相关智能体（本卡应被谁看到 · 跨设备）', '');
  lines.push(`- 判定依据: \`${related.source}\`${related.note ? ' — ' + related.note : ''}`);
  lines.push(`- 本机设备: \`${related.local_device}\``);
  lines.push('');
  lines.push('| 设备 | 智能体 | 依据 |');
  lines.push('|---|---|---|');
  for (const d of related.devices) {
    lines.push(`| ${d.device} | ${d.agents.length ? d.agents.map((a) => '`' + a + '`').join(' · ') : '（该设备全体）'} | ${related.source} |`);
  }
  if (!related.devices.length) lines.push('| — | （未判定出） | 无依据可用 |');
  lines.push('');
  lines.push('## 你现在该做什么', '');
  lines.push('1. 若你是相关智能体：把上面「它约束什么」纳入下次决策，不要等别人提醒。');
  lines.push(`2. 检索本卡：本机 \`curl ${LOCAL_BB_DEFAULT}/${noticeKey(date)}\` · 中央 \`curl ${CENTRAL_BB_DEFAULT}/${noticeKey(date)}\``);
  lines.push(`3. 全卡：本机落盘 \`data/reflect/feedback-${date}.md\` · 中央黑板 \`${fullCardKey(date)}\``);
  lines.push('4. 反对意见：走「每日反思」提案流程提出新提案——**本工具不会自行改动已入册内容**（改动需新的用户裁定）。');
  lines.push('');
  return lines.join('\n');
}

/** 落盘反馈卡（原子：tmp → rename → 回读）。落盘前**先脱敏 + 复检**（凭据不出本机、也不上黑板）。 */
export function writeFeedbackCard(root, date, card) {
  const r = resolveRoot(root);
  const { text: safe, hits } = redactCredentials(card);
  assertNoCredentials(safe, { where: `反馈卡 data/reflect/feedback-${date}.md` });
  const abs = inRoot(r, path.join(REL.reflectDir, `feedback-${date}.md`));
  const tmp = `${abs}.tmp-${process.pid}`;
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(tmp, safe, 'utf8');
  fs.renameSync(tmp, abs);
  const back = readText(abs);
  if (!back.includes(`反思入册 · 反馈卡 ${date}`)) throw new GateError('FEEDBACK_VERIFY_FAILED', `反馈卡回读校验失败: ${abs}`);
  return { rel: path.relative(r, abs), abs, bytes: Buffer.byteLength(safe, 'utf8'), sha256: sha256(safe), redactions: hits };
}

/* ══════════════════════════ 黑板（本包唯一 HTTP 调用点） ══════════════════════════ */

/**
 * bbRequest — 全包**唯一**的对外 HTTP 调用点（--lean4-check F 项断言：出站点恰好 1 个、
 * 就在本函数内、且本函数第一件事是 assertBbHost 白名单校验）。
 * PUT 用 JSON body（node:http 自带精确 Content-Length，符合 R003/R-ERR1 精神）。
 */
export function bbRequest(bbBase, key, method, value, { timeoutMs = 3000 } = {}) {
  assertBbHost(bbBase);
  if (!/^[a-z]+(\/[^\s]*)?$/.test(key)) {
    return Promise.resolve({ ok: false, status: 0, key, error: `key 非法（首段必须纯小写字母 [a-z]+）: ${key}` });
  }
  // ★ 纵深防御（2026-09-11 实测）：尾斜杠/空段 key 是黑板的**命名空间列举端点**——
  //   实测 GET /data/reflect/ → **200 但 body 是 {list,total} 全库列举**，
  //   而"全库列举里必然含有你刚写的键字符串" → 任何"回读含标记即落地"的判据都会被**必然骗过**。
  if (/\/$/.test(key) || key.includes('//')) {
    return Promise.resolve({ ok: false, status: 0, key, error: 'key 指向命名空间列举端点（尾斜杠/空段）：实测返回 {list,total} 而非 value，本工具拒绝把它当键使用' });
  }
  const body = value === undefined ? null : Buffer.from(JSON.stringify(value), 'utf8');
  const u = new URL(bbBase);
  return new Promise((resolve) => {
    const req = http.request({
      host: u.hostname, port: u.port || 80, path: '/' + key, method,
      headers: body ? { 'Content-Type': 'application/json', 'Content-Length': body.length } : {}
    }, (res) => {
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (c) => { data += c; });
      res.on('end', () => resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, key, body: data.slice(0, 20000) }));
    });
    req.setTimeout(timeoutMs, () => { req.destroy(new Error('timeout')); });
    req.on('error', (e) => resolve({ ok: false, status: 0, key, error: e.message }));
    if (body) req.write(body);
    req.end();
  });
}

/** bbPut — 写黑板（PUT JSON body）。调用前必须已过 assertWriteKey 命名空间门。 */
export function bbPut(bbBase, key, value, opts) { return bbRequest(bbBase, key, 'PUT', value, opts); }

/** bbGet — 回读黑板键（R030：写入后必须回读，不能把"返回 200"当成落地）。 */
export function bbGet(bbBase, key, opts) { return bbRequest(bbBase, key, 'GET', undefined, opts); }

/** 写 + 回读校验（所有黑板写入都必须走它：命名空间门 → 脱敏 → 复检 → PUT → GET）。 */
export async function bbPutVerified(bbBase, key, value, { kind = 'card', text = null, marker = key } = {}) {
  assertWriteKey(key, { kind, text });
  const { value: clean, hits } = redactDeepCounted(value);
  assertNoCredentials(JSON.stringify(clean), { where: `黑板 value(${key})` });
  const put = await bbPut(bbBase, key, clean);
  if (!put.ok) {
    // 写都没成（含 400 键错）—— 直接按响应语义定性，不去回读
    const cls = classifyBbReadback({ status: put.status, body: put.body, marker, transportError: put.error });
    return { key, kind, board: bbBase, put_status: put.status, readback_status: null, landed: false, redactions: hits, verdict: cls.kind, semantics: cls.semantics, error: `PUT 未成功：${cls.semantics}` };
  }
  const readback = await bbGet(bbBase, key);
  // ★ R003 补充：只认「回读 200 + value 非空 + 内容命中标记」才算落地（空壳键不算）
  const cls = classifyBbReadback({ status: readback.status, body: readback.body, marker, expected: value, transportError: readback.error });
  return {
    key, kind, board: bbBase, put_status: put.status, readback_status: readback.status,
    landed: cls.landed, verdict: cls.kind, semantics: cls.semantics, redactions: hits,
    error: cls.landed ? null : `PUT=${put.status} 回读=${readback.status}：${cls.semantics}`
  };
}

/* ══════════════════════════ 反馈总编排 ══════════════════════════ */

/** 规则变更通知卡（要求 3）：新规则摘要 + 它约束什么 + 哪些设备的哪些智能体该注意 */
export function buildNoticeValue({ date, results, related, ts, device, cardRel, redactions }) {
  const enrolled = (results || []).filter((x) => x.applied);
  return {
    key: noticeKey(date),
    origin_device: device,
    plugin_version: VERSION,
    ts,
    ts_local: new Date().toString(),
    date,
    topic: `规则变更通知 ${date}（入册 ${enrolled.length} 条）`,
    rules: enrolled.map((x) => ({
      proposal_id: x.proposal_id, target: x.target, ref: x.ref,
      name: (x.entry && x.entry.name) || x.summary || null,
      summary: (x.entry && (x.entry.summary || x.entry.core)) || x.summary || null,
      constrains: (x.entry && (x.entry.core || x.entry.detail || x.entry.summary)) || x.summary || null,
      files: x.wrote || [], decision: x.decision, reason: x.reason || null
    })),
    devices: related.devices,
    related_source: related.source,
    card_key: fullCardKey(date),
    card_file: cardRel,
    redactions: (redactions || []).length
  };
}

export async function publishFeedback({
  root, date, card, related, results, localBb, centralBb, notify = false, dryRun = false, ts, device
}) {
  const r = resolveRoot(root);
  const local = assertBbHost(localBb || LOCAL_BB_DEFAULT).origin;
  const central = assertBbHost(centralBb || CENTRAL_BB_DEFAULT).origin;
  const out = {
    cardKey: noticeKey(date), fullCardKey: fullCardKey(date), local_bb: local, central_bb: central,
    card: null, boards: { local: [], central: [] }, notify: [], skipped: false, redactions: [],
    notifyMaxChars: MAX_NOTIFY_CHARS, related_devices: related.devices,
    landed: false, landed_local: false, landed_central: false, notify_ok: null
  };
  if (dryRun) {
    out.skipped = true;
    out.reason = 'dry-run：反馈卡不落盘、黑板不写（本机+中央都不写）、消息不发（零变更）';
    log('feedback.skipped-dry-run', { input: { date, device }, result: { ok: true, cardKey: out.cardKey, local, central } });
    return out;
  }

  // ① 本机落盘（先脱敏 + 复检）
  out.card = writeFeedbackCard(r, date, card);
  out.redactions = out.card.redactions;
  if (out.redactions.length) {
    log('feedback.credentials-redacted', {
      input: { file: out.card.rel }, judge: { kinds: out.redactions.map((x) => x.kind) },
      result: { ok: true, redacted: out.redactions.length }
    });
  }

  // ②③ 两个黑板：全卡（本机+中央）+ 规则变更通知卡（全设备可检索）
  const fullValue = redactDeepCounted({
    key: fullCardKey(date), kind: 'reflect-feedback-card',
    origin_device: device, plugin_version: VERSION, ts, ts_local: new Date().toString(), date,
    topic: `每日反思入册·反馈卡 ${date}`,
    text: readText(out.card.abs),
    card_file: out.card.rel, related_devices: related.devices, related_source: related.source,
    redactions: out.redactions.length
  });
  const noticeValue = redactDeepCounted(buildNoticeValue({ date, results, related, ts, device, cardRel: out.card.rel, redactions: out.redactions }));
  for (const [boardName, base] of [['local', local], ['central', central]]) {
    const a = await bbPutVerified(base, fullCardKey(date), fullValue.value, { kind: 'card', marker: `每日反思入册·反馈卡 ${date}` });
    const b = await bbPutVerified(base, noticeKey(date), noticeValue.value, { kind: 'card', marker: noticeKey(date) });
    out.boards[boardName] = [a, b];
    out.redactions.push(...fullValue.hits, ...noticeValue.hits);
  }

  // ④ 短指引：本机智能体走本机黑板；其他设备走**中央黑板待投递队列**（离线也能收到）
  if (notify) {
    for (const a of related.agents) {
      const dev = String(a.device || '');
      if (!/^[a-z][a-z0-9-]*$/.test(dev)) {
        out.notify.push({ agent: a.key, ok: false, skipped: true, reason: `设备段 '${dev}' 不是合法黑板域（^[a-z][a-z0-9-]*$）——未发短消息` });
        continue;
      }
      const isLocal = dev === device;
      const base = isLocal ? local : central;
      const key = pointerKey(dev, date);
      const text = `看黑板 ${noticeKey(date)}`;
      try { assertWriteKey(key, { kind: 'pointer', text }); }
      catch (e) { out.notify.push({ agent: a.key, ok: false, skipped: true, key, reason: e.message }); continue; }
      const payload = redactDeepCounted({
        key, from: 'reflect-enroll', origin_device: device, plugin_version: VERSION, ts,
        text, ref: noticeKey(date), agent: a.agent, topic: `入册反馈指引 ${date}`,
        queue: isLocal ? 'local' : 'central-pending'
      });
      const res = await bbPutVerified(base, key, payload.value, { kind: 'pointer', text, marker: text });
      out.redactions.push(...payload.hits);
      out.notify.push({ ...res, ok: res.landed, agent: a.key, device: dev, chars: text.length, route: isLocal ? '本机黑板' : '中央黑板待投递队列(离线可达)' });
    }
  }

  out.redactions = dedupeHidden(out.redactions);
  if (out.redactions.length) {
    log('feedback.credentials-redacted', {
      input: { date, device },
      judge: { kinds: [...new Set(out.redactions.map((x) => x.kind))] },
      result: { ok: true, count: out.redactions.length, scope: '反馈卡 + 本机/中央黑板 value + 短指引' }
    });
  }
  out.landed_local = out.boards.local.every((x) => x.landed);
  out.landed_central = out.boards.central.every((x) => x.landed);
  out.landed = out.landed_local && out.landed_central;
  out.notify_ok = out.notify.length ? out.notify.every((x) => x.ok) : null;

  log('feedback.published', {
    input: { date, device, notify, related_source: related.source, devices: related.devices.map((d) => d.device) },
    judge: { cardKey: out.cardKey, fullCardKey: out.fullCardKey },
    result: {
      ok: out.landed, card: out.card.rel, redactions: out.redactions.length,
      local: out.boards.local, central: out.boards.central, notify: out.notify
    },
    diag: { local_bb: local, central_bb: central }
  });
  return out;
}
