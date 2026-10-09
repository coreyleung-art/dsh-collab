/**
 * enroll.js — 业务内核（R006 ③：只用 node 内置模块；⑩：无危险原语）
 * =============================================================================
 * 这是「每日反思」流水线的**唯一写库环节**，也是数据飞轮的闭环点。
 *
 * 写库流程（每个目标文件都走同一套，无例外）：
 *   ① 读原文件（含 sha256 快照）→ ② 前置查重（幂等 / 编号唯一 / 目标不存在）
 *   → ③ 备份为 <file>.bak-<stamp> 并**回读验证备份可解析**
 *   → ④ 计算新内容（只追加，条目数严格 +N）→ ⑤ 写 <file>.tmp-<stamp>
 *   → ⑥ 校验 tmp 可解析 → ⑦ rename 覆盖（原子）
 *   → ⑧ **回读校验**（可解析 / 条目数 / 编号存在 / 字段齐全 / 不含删除）
 *   → ⑨ 任一环失败：从备份**回滚**全部已写文件并逐个回读验证
 *
 * ★ 本模块**没有**任何删除/覆盖既有条目的代码路径：唯一的文本变换是"原文本 + 新增片段"，
 *   并且在回读阶段断言 `条目数 === 写入前 + N`（少于即回滚）。删除只能由人手动做。
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {
  GateError, assertDecision, assertTarget, assertSlug, assertInsideRoot, assertIdUnique, assertNotEnrolled,
  PHILOSOPHY_REQUIRED_FIELDS, RULE_REQUIRED_FIELDS, PHILOSOPHY_STATUS, RULE_STATUS,
  PHILOSOPHY_ID_RE, RULE_ID_RE, LIBRARY_TARGETS, DECISIONS, TARGETS, assertVersionMonotonic
} from './gate.js';
import { VERSION } from './version.js';
import { log } from './log.js';

/** root 内的相对落点（全部写操作只落这些路径）。 */
export const REL = Object.freeze({
  philosophy: 'data/blueprint/gallery/governance-philosophy.json',
  philosophyChangelog: 'data/blueprint/gallery/governance-philosophy-changelog.md',
  rulesMd: 'rules-registry/RULES.md',
  rulesJson: 'rules-registry/rules.json',
  ledger: 'data/reflect/enrolled.json',
  reflectDir: 'data/reflect',
  archiveDir: 'data/reflect/archive',
  sopsDir: 'docs/sops'
});

/* ══════════════════════════ 路径 / 时间 / 哈希 ══════════════════════════ */

export function resolveRoot(root) {
  const r = root || process.env.DSH_COLLAB_ROOT || path.join(os.homedir(), 'dsh-collab');
  return path.resolve(String(r).replace(/^~(?=\/|$)/, os.homedir()));
}

export function inRoot(root, rel) { return assertInsideRoot(resolveRoot(root), path.join(resolveRoot(root), rel)); }

const pad = (n) => String(n).padStart(2, '0');
export function stampNow(d = new Date()) {
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}
export function todayDate(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
export function sha256(text) { return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex'); }

/* ══════════════════════════ 基础 IO（原子 + 备份 + 回滚） ══════════════════════════ */

export function readText(abs) { return fs.readFileSync(abs, 'utf8'); }
export function readJson(abs) {
  const raw = readText(abs);
  try { return { raw, obj: JSON.parse(raw) }; }
  catch (e) { throw new GateError('TARGET_UNPARSEABLE', `目标文件不可解析（拒绝在坏文件上写入）: ${abs} — ${e.message}`); }
}

/**
 * 探测原文件的 JSON 排版风格（缩进 / 行尾），写入时**原样复现**。
 * 目的：让"新增一条"的 diff 只包含新增内容，不夹带整体重排 —— 这是"不写坏"的一部分。
 */
export function detectJsonStyle(raw, obj) {
  for (const indent of [1, 2, 0, '\t']) {
    for (const nl of [false, true]) {
      const s = JSON.stringify(obj, null, indent) + (nl ? '\n' : '');
      if (s === raw) return { indent, trailingNewline: nl, exact: true };
    }
  }
  return { indent: 1, trailingNewline: false, exact: false };
}

export function renderJsonLike(style, obj) {
  return JSON.stringify(obj, null, style.indent) + (style.trailingNewline ? '\n' : '');
}

/** 备份 + **回读验证**（字节一致；JSON 目标还要求可解析）。失败即中止，绝不带着坏备份往下写。 */
export function backupFile(abs, stamp, { mustParseJson = false } = {}) {
  if (!fs.existsSync(abs)) return null;
  const dest = `${abs}.bak-${stamp}`;
  fs.copyFileSync(abs, dest);
  const a = readText(abs);
  const b = readText(dest);
  if (a !== b) throw new GateError('BACKUP_UNVERIFIED', `备份回读不一致，拒绝继续写入: ${dest}`);
  if (mustParseJson) {
    try { JSON.parse(b); }
    catch (e) { throw new GateError('BACKUP_UNPARSEABLE', `备份不可解析，拒绝继续写入: ${dest} — ${e.message}`); }
  }
  return { path: dest, bytes: Buffer.byteLength(b, 'utf8'), sha256: sha256(b), verified: true };
}

/** 原子写：tmp → 校验 → rename。validate 抛错则 tmp 不会被激活（目标文件保持原样）。 */
export function writeAtomic(abs, content, { validate } = {}) {
  const tmp = `${abs}.tmp-${process.pid}`;
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(tmp, content, 'utf8');
  if (typeof validate === 'function') validate(readText(tmp));
  fs.renameSync(tmp, abs);
  return { path: abs, bytes: Buffer.byteLength(content, 'utf8'), sha256: sha256(content) };
}

/** 回滚：把备份内容**写回**目标（用写入而非删除——本工具无删除能力）。 */
export function restoreFromBackup(bak) {
  const content = readText(bak.path);
  writeAtomic(bak.path.replace(/\.bak-[\d-]+$/, ''), content);
  const now = readText(bak.path.replace(/\.bak-[\d-]+$/, ''));
  if (sha256(now) !== sha256(content)) throw new GateError('ROLLBACK_FAILED', `回滚后回读不一致: ${bak.path}`);
  return { restored: true, sha256: sha256(now) };
}

/* ══════════════════════════ R001 红绿灯：写前持锁检查（只读） ══════════════════════════ */

/**
 * 读总线锁状态（**只读**，不取锁、不发请求、零 shell）。
 * ★ 本工具**不自己取锁**：取锁需要 agent-bus 的会话身份（token），而"工具替调用方保管锁"
 *   会制造第二套锁机制（比不加锁更危险）。所以分工是：
 *     · 取锁/释放锁 = **调用方（人或会话）** 的动作（agent_lock / agent_unlock）
 *     · 本工具 = **别人持锁时拒绝写**（红灯不硬写）+ 计划后文件被改动即拒写（乐观并发）
 * 锁状态来源：$DSH_AGENT_BUS_STATE 或 ~/.dsh/agent-bus.json 的 locks[]（只读解析）。
 */
export function busStateFile() {
  return process.env.DSH_AGENT_BUS_STATE || path.join(os.homedir(), '.dsh', 'agent-bus.json');
}

export function checkBusLock(abs) {
  const f = busStateFile();
  const out = { checked: false, held: false, holders: [], resource: null, state: f, note: null };
  if (!fs.existsSync(f)) { out.note = '无总线状态文件（非总线环境）→ 跳过持锁检查'; return out; }
  let st;
  try { st = JSON.parse(readText(f)); }
  catch (e) { out.note = `总线状态不可解析，跳过持锁检查: ${e.message}`; return out; }
  out.checked = true;
  const target = path.resolve(abs);
  const now = Date.now();
  for (const lk of st.locks || []) {
    if (!lk || typeof lk.resource !== 'string') continue;
    if (!lk.resource.startsWith('file:')) continue;
    const res = lk.resource.slice(5);
    const resAbs = path.resolve(res);
    // 精确命中该文件，或其父目录被锁（含 dsh-collab 根）
    const covers = resAbs === target || target.startsWith(resAbs.endsWith(path.sep) ? resAbs : resAbs + path.sep);
    if (!covers) continue;
    const holders = (lk.holders || []).filter((id) => {
      const exp = lk.expiresAt && lk.expiresAt[id];
      return !exp || exp > now;                    // 过期锁视为已释放
    });
    if (holders.length) { out.held = true; out.holders = holders; out.resource = lk.resource; out.mode = lk.mode || 'exclusive'; return out; }
  }
  return out;
}

/** 门：目标文件正被他人持锁 → 拒绝写（R001：红灯不硬写；失败即停）。 */
export function assertNotLocked(abs) {
  const c = checkBusLock(abs);
  if (c.held) {
    throw new GateError('LOCKED_BY_OTHER',
      `拒绝：目标文件正被他人独占（R001 红绿灯）：${c.resource}，持锁者 ${c.holders.join(', ')}（mode=${c.mode}）。` +
      `本工具**不替你抢锁**——请等持锁方释放（agent_unlock），或由你取锁后再重跑。`);
  }
  return c;
}

/* ══════════════════════════ 台账（幂等门的依据） ══════════════════════════ */

export function loadLedger(root) {
  const abs = inRoot(root, REL.ledger);
  if (!fs.existsSync(abs)) return { abs, exists: false, raw: null, obj: { version: 1, updated: null, entries: [] }, style: { indent: 1, trailingNewline: true } };
  const { raw, obj } = readJson(abs);
  return { abs, exists: true, raw, obj, style: detectJsonStyle(raw, obj) };
}

/* ══════════════════════════ 输入装载 ══════════════════════════ */

/** 裁定文件（格式 A）：{"date":..,"rulings":[{proposal_id,decision,target,modifications,reason}]} */
export function loadRulings(root, { file, date } = {}) {
  const d = date || todayDate();
  const abs = file ? path.resolve(String(file).replace(/^~(?=\/|$)/, os.homedir()))
    : inRoot(root, path.join(REL.reflectDir, `ruling-${d}.json`));
  if (!fs.existsSync(abs)) {
    // ★ 刻意**不**自动挑一份旧裁定顶替：裁定是权威人工输入，替人选=越权（R006 ⑩）。
    //   只把"有哪些候选"报出来，让人显式指定（fail-closed + 可操作）。
    const dir = inRoot(root, REL.reflectDir);
    const cands = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => /^ruling-\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort().slice(-3) : [];
    throw new GateError('RULING_FILE_MISSING',
      `裁定文件不存在: ${abs}（本工具不接受"没有裁定"的入册请求）。` +
      (cands.length ? `同目录已有候选：${cands.join(' · ')} —— 请显式 --ruling 指定（工具**不替你挑**是哪份裁定）。` : ''));
  }
  const { obj } = readJson(abs);
  if (!Array.isArray(obj.rulings) || !obj.rulings.length) {
    throw new GateError('RULING_EMPTY', `裁定文件 ${abs} 里没有 rulings[]（空裁定不允许入册）`);
  }
  return { abs, date: obj.date || d, rulings: obj.rulings };
}

/**
 * 提案库（入册内容的正本；工具绝不自己编内容）。
 * 查找顺序：显式 --proposal → proposals-<date>.json → proposals.json → 最近的 proposals-YYYY-MM-DD.json（≤3 份，新→旧）。
 * 回退时会如实回报用了哪份、为什么（每日流水线常在跨零点后跑，硬绑"今天"会让整条链在午夜后空转）。
 */
export function loadProposals(root, { file, date } = {}) {
  const d = date || todayDate();
  const dir = inRoot(root, REL.reflectDir);
  const tried = [];
  let candidates;
  if (file) {
    candidates = [path.resolve(String(file).replace(/^~(?=\/|$)/, os.homedir()))];
  } else {
    const recent = fs.existsSync(dir)
      ? fs.readdirSync(dir).filter((f) => /^proposals-\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort().reverse().slice(0, 3)
      : [];
    candidates = [inRoot(root, path.join(REL.reflectDir, `proposals-${d}.json`)), inRoot(root, path.join(REL.reflectDir, 'proposals.json')), ...recent.map((f) => inRoot(root, path.join(REL.reflectDir, f)))];
  }
  for (const abs of [...new Set(candidates)]) {
    tried.push(abs);
    if (!fs.existsSync(abs)) continue;
    const { obj } = readJson(abs);
    const list = Array.isArray(obj) ? obj : (obj.proposals || []);
    const map = new Map();
    for (const p of list) if (p && p.id) map.set(String(p.id), p);
    const expected = inRoot(root, path.join(REL.reflectDir, `proposals-${d}.json`));
    const note = (!file && abs !== expected) ? `提案库回退：今日 ${path.basename(expected)} 不存在，改用 ${path.basename(abs)}` : null;
    return { abs, map, note, tried };
  }
  return { abs: null, map: new Map(), note: null, tried };
}

/**
 * CLI 单条形态：--rule P1=approve:philosophy。
 * ★ 语法与**冻结枚举**都在解析期校验 → CLI 这条入口的非法值属于**用法错误**（exit 2），
 *   而不是等到门里才拒（那样会把"参数写错"误报成"门拒绝"，让人查错方向）。
 *   （裁定文件里的非法值是外部数据，仍走门 → exit 1；两类语义刻意不同。）
 */
export function parseRuleSpec(spec) {
  const m = /^([A-Za-z0-9_-]+)=([a-zA-Z-]+):([a-zA-Z-]+)$/.exec(String(spec || '').trim());
  if (!m) {
    throw new UsageError(`--rule 格式应为 <提案id>=<${DECISIONS.join('|')}>:<${TARGETS.join('|')}>，收到 '${spec}'`);
  }
  if (!DECISIONS.includes(m[2])) throw new UsageError(`--rule 的 decision '${m[2]}' 非法（只接受 ${DECISIONS.join(' / ')}）—— CLI 参数写错属用法错误`);
  if (!TARGETS.includes(m[3])) throw new UsageError(`--rule 的 target '${m[3]}' 非法（只接受 ${TARGETS.join(' / ')}）—— CLI 参数写错属用法错误`);
  return { proposal_id: m[1], decision: m[2], target: m[3] };
}

export class UsageError extends Error {
  constructor(message) { super(message); this.name = 'UsageError'; this.code = 'USAGE'; }
}

/* ══════════════════════════ 内容构造（纯函数） ══════════════════════════ */

export function bumpMinor(v) {
  const m = /^(\d+)\.(\d+)(?:\.(\d+))?$/.exec(String(v || '0.0'));
  if (!m) return '0.1';
  // 保持原文件的段数（governance-philosophy.json 用两段 "2.4"，rules.json 用三段 "2.14.0"）
  return m[3] === undefined ? `${m[1]}.${Number(m[2]) + 1}` : `${m[1]}.${Number(m[2]) + 1}.0`;
}
export function bumpPatch(v) {
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(String(v || '0.0.0'));
  if (!m) return '0.0.1';
  return `${m[1]}.${m[2]}.${Number(m[3]) + 1}`;
}

function nonEmpty(v) { return typeof v === 'string' ? v.trim().length > 0 : (v !== undefined && v !== null); }

/** 校验提案内容是否足以构造一条合法哲学（缺字段即拒——工具不替人补内容）。 */
export function buildPhilosophyEntry(proposal, ruling, date) {
  const id = proposal.id_new || proposal.philosophy_id || (proposal.slug ? `phi-${proposal.slug}` : null);
  if (!nonEmpty(id) || !PHILOSOPHY_ID_RE.test(String(id))) {
    throw new GateError('BAD_PHILOSOPHY_ID', `提案 '${proposal.id}' 缺合法哲学编号：需提供 id_new / philosophy_id 或 slug（形如 phi-xxx，^phi-[a-z0-9-]+$）。工具不替提案编编号。`);
  }
  const status = proposal.status || 'active';
  if (!PHILOSOPHY_STATUS.includes(status)) throw new GateError('BAD_PHILOSOPHY_STATUS', `status '${status}' 不在 ${PHILOSOPHY_STATUS.join('/')}`);
  const entry = {
    id: String(id),
    name: proposal.name,
    core: proposal.core,
    origin: proposal.origin || `每日反思入册 ${date} · 提案 ${proposal.id}（用户裁定 ${ruling.decision}）`,
    doc: proposal.doc,
    order: undefined, // 由容器按 max+1 计算
    status
  };
  if (nonEmpty(proposal.order)) entry.order = Number(proposal.order);
  if (proposal.children) entry.children = proposal.children;
  if (proposal.derives) entry.derives = proposal.derives;
  entry.detail = proposal.detail || proposal.core;
  entry.principles = Array.isArray(proposal.principles) ? proposal.principles : [];
  entry.examples = Array.isArray(proposal.examples) ? proposal.examples : [];
  if (proposal.relDocs) entry.relDocs = proposal.relDocs;
  for (const f of PHILOSOPHY_REQUIRED_FIELDS) {
    if (f === 'order') continue;
    if (!nonEmpty(entry[f])) throw new GateError('PHILOSOPHY_FIELD_MISSING', `提案 '${proposal.id}' 缺必填字段 '${f}'（哲学条目必填 ${PHILOSOPHY_REQUIRED_FIELDS.join('/')}）。工具不替人编内容。`);
  }
  return entry;
}

/** 校验提案内容是否足以构造一条合法规则。 */
export function buildRuleEntry(proposal, ruling, date) {
  const id = proposal.rule_id || proposal.id_new || null;
  if (!nonEmpty(id) || !RULE_ID_RE.test(String(id))) {
    throw new GateError('BAD_RULE_ID', `提案 '${proposal.id}' 缺合法规则号：需提供 rule_id（形如 R036 / R-ERR5 / J46）。工具不替提案编号。`);
  }
  const status = proposal.status || 'enforced';
  if (!RULE_STATUS.includes(status)) throw new GateError('BAD_RULE_STATUS', `status '${status}' 不在 ${RULE_STATUS.join('/')}`);
  const entry = {
    id: String(id),
    name: proposal.name,
    category: proposal.category,
    scope: proposal.scope || 'all-bus-devices',
    status,
    version: proposal.version || '1.0',
    summary: proposal.summary,
    detail: proposal.detail,
    enforcedBy: proposal.enforcedBy || 'tool+manual',
    added: date,
    approvedBy: `user(${date} 裁定 ${ruling.decision}${ruling.reason ? '：' + String(ruling.reason).slice(0, 60) : ''})`
  };
  for (const f of RULE_REQUIRED_FIELDS) {
    if (!nonEmpty(entry[f])) throw new GateError('RULE_FIELD_MISSING', `提案 '${proposal.id}' 缺必填字段 '${f}'（规则必填 ${RULE_REQUIRED_FIELDS.join('/')}）。工具不替人编内容。`);
  }
  if (proposal.source) entry.source = proposal.source;
  entry.updated = date;
  return entry;
}

/** RULES.md 规则块（与既有块格式一致）。 */
export function renderRuleBlock(entry, { proposal, ruling, date }) {
  const lines = [
    `## ${entry.id} ✅ ${entry.name}`,
    `- 分类: ${entry.category} | 范围: ${entry.scope} | 状态: ${entry.status}`,
    `- 摘要: ${entry.summary}`,
    `- 详情: ${entry.detail}`,
    `- 来源: 每日反思入册 ${date}（用户裁定 ${ruling.decision}${ruling.reason ? '：' + String(ruling.reason).slice(0, 80) : ''}）· 提案 ${proposal.id}`,
    ''
  ];
  if (proposal.related) lines.splice(5, 0, `- 关联: ${proposal.related}`);
  if (proposal.versionNote) lines.splice(5, 0, `- 版本: ${proposal.versionNote}`);
  return lines.join('\n');
}

/** 把规则块插到「规则区」末尾（治理哲学段之前），保持规则块连续；找不到锚点则纯追加。 */
export function insertRuleBlock(md, block) {
  const anchor = '\n## 治理哲学（Φ 系列';
  const i = md.indexOf(anchor);
  if (i >= 0) return md.slice(0, i) + '\n' + block + md.slice(i);
  return (md.endsWith('\n') ? md : md + '\n') + '\n' + block;
}

/** 更新 RULES.md 头行版本与条数（找不到头行不失败，只记 note）。 */
export function bumpRulesHeader(md, { version, count }) {
  const re = /^> v(\d+\.\d+\.\d+) \| (\d+) 条 \| (.*)$/m;
  if (!re.test(md)) return { md, updated: false, note: 'RULES.md 头行未匹配 ^> vX.Y.Z | N 条 | …，已跳过版本/条数更新' };
  const out = md.replace(re, `> v${version} | ${count} 条 | $3`);
  return { md: out, updated: true, from: md.match(re)[0], to: out.match(re)[0] };
}

/** 哲学 changelog 段（插在「## 版本历史」之后，与"最新在前"的既有排法一致）。 */
export function insertPhilosophyChangelogSection(md, section) {
  const anchor = '## 版本历史\n';
  const i = md.indexOf(anchor);
  if (i >= 0) return md.slice(0, i + anchor.length) + '\n' + section + md.slice(i + anchor.length);
  return (md.endsWith('\n') ? md : md + '\n') + '\n' + section;
}

export function renderPhilosophyChangelogSection(entry, { proposal, ruling, date, newVersion }) {
  const phiNo = entry.order;
  return [
    `### v${newVersion}（${date} · 新增 1 条 → ${entry.order} 条）`,
    '',
    `- **变更**：新增哲学 **Φ${phiNo} ${entry.name}**（用户裁定 \`${ruling.decision}\` · 提案 ${proposal.id}）`,
    `- **核心**：${entry.core}`,
    `- **来源**：${entry.origin}`,
    `- **裁定理由**：${ruling.reason || '（未填写）'}`,
    ruling.modifications ? `- **用户修改**：${ruling.modifications}` : null,
    `- **落链**：\`governance-philosophy.json\` v${newVersion} · \`RULES.md\` Φ 系列段 · 本档案`,
    ''
  ].filter((l) => l !== null).join('\n');
}

/* ══════════════════════════ 计划（纯读，零写） ══════════════════════════ */

/**
 * 生成入册计划：**只读**，不写任何字节（--dry-run 到此为止）。
 * 计划里带每个目标文件的 sha256 快照 —— apply 阶段会复核，别人改过库就拒绝盲写。
 */
export function planOne({ root, ruling, proposal, date, ledgerEntries }) {
  const r = resolveRoot(root);
  const proposalId = String(ruling.proposal_id || '').trim();
  if (!proposalId) throw new GateError('NO_PROPOSAL_ID', '裁定缺少 proposal_id');
  const decision = assertDecision(ruling.decision);
  const target = assertTarget(ruling.target);

  // ★ 幂等门 + ★ "绝不自动决定"门
  assertNotEnrolled(ledgerEntries, proposalId);
  if (decision === 'modify' && !nonEmpty(ruling.modifications)) {
    throw new GateError('MODIFY_WITHOUT_TEXT',
      `拒绝：裁定为 modify 但没给 modifications 文本。工具**不猜**用户想怎么改——请把修改说明写进裁定。`);
  }

  const plan = {
    proposal_id: proposalId, decision, target, date, root: r,
    outcome: decision === 'defer' ? 'deferred' : (decision === 'reject' ? 'rejected' : 'enrolled'),
    reason: ruling.reason || null, modifications: ruling.modifications || null,
    proposal: proposal ? { id: proposal.id, name: proposal.name || null, related_agents: proposal.related_agents || null, resources: proposal.resources || null } : null,
    writes: [], notes: [], ref: null, summary: null
  };

  if (plan.outcome === 'deferred') {
    plan.notes.push('decision=defer：本工具**不写任何字节**（不入册、不写台账）——延期提案可在用户后续裁定后再次提交');
    return plan;
  }

  if (plan.outcome === 'rejected') {
    const rel = path.join(REL.archiveDir, `${date}.md`);
    const abs = inRoot(r, rel);
    const before = fs.existsSync(abs) ? readText(abs) : '';
    const block = [
      `## 驳回 · ${proposalId}（${date}）`,
      '',
      `- 目标: ${target}`,
      `- 提案名: ${proposal ? (proposal.name || proposal.summary || '(无名)') : '(裁定文件未附提案内容)'}`,
      `- 用户理由: ${ruling.reason || '（未填写）'}`,
      `- 裁定: reject（未写治理库；仅归档为案例，可再审）`,
      ''
    ].join('\n');
    const after = before ? `${before}${before.endsWith('\n') ? '' : '\n'}\n${block}` : `# 反思入册·驳回归档 ${date}\n\n${block}`;
    plan.ref = `${proposalId}@rejected`;
    plan.summary = `驳回归档（未入册）`;
    plan.writes.push({ rel, abs, exists: before !== '', before, after, sha256Before: before ? sha256(before) : null, expect: { kind: 'append-marker', marker: `## 驳回 · ${proposalId}` } });
    plan.ledgerEntry = { proposal_id: proposalId, date, decision, target, outcome: 'rejected', ts: new Date().toISOString(), ref: plan.ref, reason: ruling.reason || null };
    return plan;
  }

  /* ---- outcome=enrolled：必须有提案正本 ---- */
  if (!proposal) {
    throw new GateError('NO_PROPOSAL',
      `拒绝：提案 '${proposalId}' 的内容找不到（提案库 data/reflect/proposals-<date>.json 或 --proposal 未提供）。` +
      `本工具**绝不自行编造入册内容**——入册内容只能来自用户裁定所指向的提案正本。`);
  }

  if (target === 'philosophy') return planPhilosophy(plan, { r, proposal, ruling, date });
  if (target === 'rule') return planRule(plan, { r, proposal, ruling, date });
  if (target === 'spec') return planSpec(plan, { r, proposal, ruling, date });
  // archive
  const rel = path.join(REL.archiveDir, `${date}.md`);
  const abs = inRoot(r, rel);
  const before = fs.existsSync(abs) ? readText(abs) : '';
  const block = [
    `## 案例 · ${proposalId} ${proposal.name || ''}（${date}）`,
    '',
    `- 裁定: archive（用户裁定 approve 但目标=仅归档，**不入治理库**）`,
    `- 摘要: ${proposal.summary || proposal.core || '(无)'}`,
    `- 用户理由: ${ruling.reason || '（未填写）'}`,
    ''
  ].join('\n');
  const after = before ? `${before}${before.endsWith('\n') ? '' : '\n'}\n${block}` : `# 反思入册·案例归档 ${date}\n\n${block}`;
  plan.ref = `${proposalId}@archive`;
  plan.summary = '归档为案例（未入册治理库）';
  plan.writes.push({ rel, abs, exists: before !== '', before, after, sha256Before: before ? sha256(before) : null, expect: { kind: 'append-marker', marker: `## 案例 · ${proposalId}` } });
  plan.ledgerEntry = { proposal_id: proposalId, date, decision, target, outcome: 'enrolled', ts: new Date().toISOString(), ref: plan.ref, reason: ruling.reason || null };
  return plan;
}

function planPhilosophy(plan, { r, proposal, ruling, date }) {
  const abs = inRoot(r, REL.philosophy);
  const { raw, obj } = readJson(abs);
  if (!Array.isArray(obj.philosophies)) throw new GateError('TARGET_SHAPE', `${REL.philosophy} 缺 philosophies[]`);
  const style = detectJsonStyle(raw, obj);
  const monotonic = assertVersionMonotonic(obj, { relFile: REL.philosophy, source: 'philosophy' });   // ★ 版本单调性门
  const ids = obj.philosophies.map((p) => p.id);

  const entry = buildPhilosophyEntry(proposal, ruling, date);
  assertIdUnique(ids, entry.id);                                   // ★ 编号唯一
  const orders = obj.philosophies.map((p) => Number(p.order) || 0);
  const nextOrder = Math.max(0, ...orders) + 1;
  if (entry.order === undefined) entry.order = nextOrder;
  else if (orders.includes(entry.order)) {
    throw new GateError('ORDER_CONFLICT', `拒绝：哲学 order=${entry.order} 已被占用（现有 order 最大 ${Math.max(0, ...orders)}）。`);
  }
  if (!nonEmpty(entry.order)) throw new GateError('PHILOSOPHY_FIELD_MISSING', '哲学条目缺 order');

  const newVersion = bumpMinor(obj.version);
  const clEntry = {
    ts: date,
    what: `+Φ${entry.order} ${entry.name}（提案 ${proposal.id}）`,
    by: `reflect-enroll v${VERSION}（用户裁定 ${ruling.decision}）`,
    user: `用户裁定 ${date}`,
    ref: REL.philosophy
  };
  const releasedAtBefore = obj.releasedAt || null;
  const releasedAtAfter = new Date().toISOString();
  // ★ Φ13（HR 2026-09-11 指出）：不静默改写 releasedAt —— 原值必须留在文件里可查，
  //   否则「修复/写入时点」会顶掉「事件时点」，且旧值只能在 .bak 里找。
  const releasedAtHistory = [...(obj.releasedAtHistory || []), {
    from: releasedAtBefore, to: releasedAtAfter, at: releasedAtAfter,
    cause: `version ${obj.version} → ${newVersion} 入册 ${entry.id}`,
    by: `reflect-enroll v${VERSION}`, kind: 'enrollment'
  }];
  const next = {
    ...obj,
    philosophies: [...obj.philosophies, entry],
    version: newVersion,
    releasedAt: releasedAtAfter,
    releasedAtHistory,
    changelog: [...(obj.changelog || []), clEntry]
  };
  const after = renderJsonLike(style, next);
  const mdAbs = inRoot(r, REL.philosophyChangelog);
  const mdBefore = fs.existsSync(mdAbs) ? readText(mdAbs) : '';
  const mdAfter = insertPhilosophyChangelogSection(mdBefore, renderPhilosophyChangelogSection(entry, { proposal, ruling, date, newVersion }));

  plan.ref = entry.id;
  plan.entry = entry;
  plan.summary = `新增哲学 Φ${entry.order} ${entry.name}（${entry.id}）`;
  plan.notes.push(`json 排版风格: indent=${JSON.stringify(style.indent)} trailingNewline=${style.trailingNewline} exact=${style.exact}`);
  plan.notes.push(`版本单调性: 当前 ${monotonic.current}${monotonic.maxSeen ? ' ≥ 文件内最高记录 ' + monotonic.maxSeen : '（文件内无旁证版本）'} · 来源 [${monotonic.sources.join(',') || '-'}]`);
  plan.writes.push({
    rel: REL.philosophy, abs, exists: true, before: raw, after, sha256Before: sha256(raw),
    expect: { kind: 'philosophy', id: entry.id, entriesBefore: obj.philosophies.length, changelogBefore: (obj.changelog || []).length, versionBefore: obj.version, versionAfter: newVersion, releasedAtBefore, historyBefore: (obj.releasedAtHistory || []).length }
  });
  plan.writes.push({
    rel: REL.philosophyChangelog, abs: mdAbs, exists: mdBefore !== '', before: mdBefore, after: mdAfter,
    sha256Before: mdBefore ? sha256(mdBefore) : null, expect: { kind: 'append-marker', marker: `### v${newVersion}（` }
  });
  plan.ledgerEntry = { proposal_id: plan.proposal_id, date, decision: plan.decision, target: plan.target, outcome: 'enrolled', ts: new Date().toISOString(), ref: entry.id, philosophy_version: newVersion, reason: ruling.reason || null, proposal_name: entry.name };
  return plan;
}

function planRule(plan, { r, proposal, ruling, date }) {
  const mdAbs = inRoot(r, REL.rulesMd);
  const jsonAbs = inRoot(r, REL.rulesJson);
  const mdBefore = readText(mdAbs);
  const { raw: jsonRaw, obj: jsonObj } = readJson(jsonAbs);
  if (!Array.isArray(jsonObj.rules)) throw new GateError('TARGET_SHAPE', `${REL.rulesJson} 缺 rules[]`);
  const style = detectJsonStyle(jsonRaw, jsonObj);
  const monotonicR = assertVersionMonotonic(jsonObj, { relFile: REL.rulesJson, source: 'rule' });      // ★ 版本单调性门
  const ids = jsonObj.rules.map((x) => x.id);
  // 台账与 RULES.md 双重查重（防两处写入漂移）
  const mdIds = [...mdBefore.matchAll(/^## (\S+) ✅/gm)].map((m) => m[1]);

  const entry = buildRuleEntry(proposal, ruling, date);
  assertIdUnique(ids, entry.id);      // ★ 编号唯一（rules.json）
  assertIdUnique(mdIds, entry.id);    // ★ 编号唯一（RULES.md）

  const block = renderRuleBlock(entry, { proposal, ruling, date });
  const mdAfter = insertRuleBlock(mdBefore, block);
  const header = bumpRulesHeader(mdAfter, { version: bumpMinor(jsonObj.version), count: jsonObj.rules.length + 1 });
  if (!header.updated) plan.notes.push(header.note);

  const next = {
    ...jsonObj,
    version: bumpMinor(jsonObj.version),
    lastUpdated: date,
    audit: {
      ...(jsonObj.audit || {}),
      ruleCount: jsonObj.rules.length + 1,
      enforced: jsonObj.rules.filter((x) => x.status === 'enforced').length + (entry.status === 'enforced' ? 1 : 0),
      updated: `+${entry.id} ${entry.name}（reflect-enroll v${VERSION}，用户裁定 ${date}）`
    },
    rules: [...jsonObj.rules, entry]
  };
  const jsonAfter = renderJsonLike(style, next);

  plan.ref = entry.id;
  plan.entry = entry;
  plan.summary = `新增规则 ${entry.id} ${entry.name}`;
  plan.notes.push(`RULES.md 头行: ${header.updated ? header.from + ' → ' + header.to : '未更新'}`);
  plan.notes.push(`版本单调性: 当前 ${monotonicR.current}${monotonicR.maxSeen ? ' ≥ 文件内最高记录 ' + monotonicR.maxSeen : '（无旁证）'}`);
  plan.writes.push({
    rel: REL.rulesMd, abs: mdAbs, exists: true, before: mdBefore, after: header.md, sha256Before: sha256(mdBefore),
    expect: { kind: 'rule-block', id: entry.id, ruleCountAfter: mdIds.length + 1, allowedRewrite: header.updated ? { from: header.from, to: header.to } : null }
  });
  plan.writes.push({
    rel: REL.rulesJson, abs: jsonAbs, exists: true, before: jsonRaw, after: jsonAfter, sha256Before: sha256(jsonRaw),
    expect: { kind: 'rule-json', id: entry.id, entriesBefore: jsonObj.rules.length, versionAfter: next.version }
  });
  plan.ledgerEntry = { proposal_id: plan.proposal_id, date, decision: plan.decision, target: plan.target, outcome: 'enrolled', ts: new Date().toISOString(), ref: entry.id, rules_version: next.version, reason: ruling.reason || null, proposal_name: entry.name };
  return plan;
}

function planSpec(plan, { r, proposal, ruling, date }) {
  const slug = assertSlug(proposal.slug || plan.proposal_id.toLowerCase().replace(/[^a-z0-9-]/g, '-'), 'SOP slug');
  const rel = path.join(REL.sopsDir, `${slug}.md`);
  const abs = inRoot(r, rel);
  if (fs.existsSync(abs)) {
    throw new GateError('SOP_EXISTS', `拒绝：SOP '${slug}' 已存在（${rel}）。本工具**不覆盖、不删除**已有 SOP——请人手动处理或换 slug。`);
  }
  const body = [
    `# SOP · ${proposal.name || slug}`,
    '',
    `> 由每日反思入册（reflect-enroll v${VERSION}）于 ${date} 生成 · 用户裁定 \`${ruling.decision}\` · 提案 ${plan.proposal_id}`,
    `> 目标=spec：**不改治理哲学库/规则库**，只落一份可执行 SOP。`,
    '',
    `## 背景 / 为什么需要`,
    '',
    proposal.why || proposal.summary || proposal.core || '（提案未填写）',
    '',
    `## 步骤`,
    '',
    typeof proposal.steps === 'string' ? proposal.steps : (Array.isArray(proposal.steps) ? proposal.steps.map((s, i) => `${i + 1}. ${s}`).join('\n') : '（提案未填写）'),
    '',
    `## 依据`,
    '',
    proposal.detail || proposal.core || '（提案未填写）',
    '',
    `## 裁定记录`,
    '',
    `- 用户裁定: ${ruling.decision}`,
    `- 理由: ${ruling.reason || '（未填写）'}`,
    ruling.modifications ? `- 用户修改: ${ruling.modifications}` : null,
    ''
  ].filter((x) => x !== null).join('\n');

  plan.ref = slug;
  plan.summary = `转规范 SOP docs/sops/${slug}.md（未改治理库）`;
  plan.writes.push({ rel, abs, exists: false, before: '', after: body, sha256Before: null, expect: { kind: 'spec', slug } });
  plan.ledgerEntry = { proposal_id: plan.proposal_id, date, decision: plan.decision, target: plan.target, outcome: 'enrolled', ts: new Date().toISOString(), ref: slug, reason: ruling.reason || null, proposal_name: proposal.name || slug };
  return plan;
}

/* ══════════════════════════ 执行（写盘 + 回读 + 回滚） ══════════════════════════ */

/** 原文的非空行必须在写入后的文本里**按序**全部出现（用于"只增不删"不变式）。
 *  allowedRewrite：**唯一**允许被改写的行（RULES.md 头行版本/条数），且必须核对 from→to 真的发生。 */
export function linesLost(before, after, allowedRewrite = null) {
  const needles = String(before).split('\n').map((l) => l.trimEnd()).filter((l) => l.length > 0);
  const hay = String(after).split('\n').map((l) => l.trimEnd());
  const lost = [];
  let i = 0;
  for (const n of needles) {
    if (allowedRewrite && n === allowedRewrite.from) {
      if (!hay.includes(allowedRewrite.to)) lost.push(`[允许改写但未见新头行] ${allowedRewrite.to}`);
      continue;                          // 计划内的改写：跳过"必须原样在"的要求
    }
    let found = -1;
    for (let j = i; j < hay.length; j++) { if (hay[j] === n) { found = j; break; } }
    if (found < 0) lost.push(n.slice(0, 80));
    else i = found + 1;
  }
  return lost;
}

function verifyWrite(w) {
  const text = readText(w.abs);
  const checks = [{ name: '回读非空', ok: text.length > 0, detail: `${text.length} 字节` }];
  const e = w.expect || {};
  if (e.kind === 'philosophy') {
    let obj = null, parseErr = null;
    try { obj = JSON.parse(text); } catch (err) { parseErr = err.message; }
    checks.push({ name: 'JSON 可解析', ok: !!obj, detail: parseErr || 'ok' });
    if (obj) {
      const ids = obj.philosophies.map((p) => p.id);
      checks.push({ name: `条目数 = 前+1 (=${e.entriesBefore + 1})`, ok: obj.philosophies.length === e.entriesBefore + 1, detail: `实际 ${obj.philosophies.length}` });
      checks.push({ name: `已入册条目数未减少（前 ${e.entriesBefore}）`, ok: obj.philosophies.length >= e.entriesBefore, detail: `实际 ${obj.philosophies.length}` });
      checks.push({ name: `编号 '${e.id}' 在位`, ok: ids.includes(e.id), detail: `末条=${ids[ids.length - 1]}` });
      const last = obj.philosophies[obj.philosophies.length - 1];
      const missing = PHILOSOPHY_REQUIRED_FIELDS.filter((f) => f === 'order' ? !(last.order > 0) : !nonEmpty(last[f]));
      checks.push({ name: '新条目字段齐全', ok: missing.length === 0, detail: missing.length ? `缺 ${missing.join(',')}` : PHILOSOPHY_REQUIRED_FIELDS.join('/') });
      checks.push({ name: `changelog +1 (=${e.changelogBefore + 1})`, ok: (obj.changelog || []).length === e.changelogBefore + 1, detail: `实际 ${(obj.changelog || []).length}` });
      checks.push({ name: `version ${e.versionBefore} → ${e.versionAfter}`, ok: obj.version === e.versionAfter, detail: `实际 ${obj.version}` });
      // ★ releasedAt 保真（Φ13）：原值必须有记录，不许静默顶掉
      const hist = obj.releasedAtHistory || [];
      const lastHist = hist[hist.length - 1] || null;
      checks.push({ name: `releasedAtHistory +1（前 ${e.historyBefore}）`, ok: hist.length === e.historyBefore + 1, detail: `实际 ${hist.length}` });
      checks.push({ name: '改写前的 releasedAt 原值已留档', ok: !!lastHist && lastHist.from === e.releasedAtBefore, detail: `from=${lastHist ? lastHist.from : '(缺失)'} / 写前=${e.releasedAtBefore}` });
      checks.push({ name: 'releasedAt 事件时点与写入时点分列', ok: !!lastHist && lastHist.to === obj.releasedAt && !!lastHist.at && !!lastHist.cause, detail: `to=${lastHist ? lastHist.to : '-'} cause=${lastHist ? String(lastHist.cause).slice(0, 40) : '-'}` });
      checks.push({ name: '既有条目原文未改（前 N 条逐字节一致）', ok: JSON.stringify(obj.philosophies.slice(0, e.entriesBefore)) === JSON.stringify(JSON.parse(w.before).philosophies), detail: 'prefix-compare' });
    }
  } else if (e.kind === 'rule-block') {
    checks.push({ name: `规则块 '## ${e.id} ✅' 存在`, ok: text.includes(`## ${e.id} ✅`), detail: 'heading 命中' });
    checks.push({ name: `规则块数 = 前+1 (=${e.ruleCountAfter})`, ok: [...text.matchAll(/^## (\S+) ✅/gm)].length === e.ruleCountAfter, detail: `实际 ${[...text.matchAll(/^## (\S+) ✅/gm)].length}` });
    checks.push({ name: `既有规则块全在`, ok: [...w.before.matchAll(/^## (\S+) ✅/gm)].every((m) => text.includes(`## ${m[1]} ✅`)), detail: 'all-before-headings-present' });
    // ★ 只增不删的不变式（RULES.md 是**插在中间**的，且头行版本/条数按计划改写 —— 初版写"必须是前缀"，假失败）
    const lost = linesLost(w.before, text, e.allowedRewrite || null);
    checks.push({
      name: '原文所有行按序仍在（只增不删；仅头行版本/条数按计划改写）',
      ok: lost.length === 0,
      detail: lost.length ? `丢失 ${lost.length} 行，例如: ${JSON.stringify(lost.slice(0, 3))}`
        : (e.allowedRewrite ? `头行改写已核对: ${e.allowedRewrite.from} → ${e.allowedRewrite.to}；其余原行全在` : `原 ${w.before.split('\n').filter(Boolean).length} 行全在`)
    });
    checks.push({ name: '写入后比原文更长（确实新增）', ok: text.length > w.before.length, detail: `${w.before.length} → ${text.length} 字节` });
  } else if (e.kind === 'rule-json') {
    let obj = null, parseErr = null;
    try { obj = JSON.parse(text); } catch (err) { parseErr = err.message; }
    checks.push({ name: 'JSON 可解析', ok: !!obj, detail: parseErr || 'ok' });
    if (obj) {
      checks.push({ name: `条目数 = 前+1 (=${e.entriesBefore + 1})`, ok: obj.rules.length === e.entriesBefore + 1, detail: `实际 ${obj.rules.length}` });
      checks.push({ name: `编号 '${e.id}' 在位`, ok: obj.rules.some((x) => x.id === e.id), detail: `末条=${obj.rules[obj.rules.length - 1].id}` });
      const last = obj.rules[obj.rules.length - 1];
      const missing = RULE_REQUIRED_FIELDS.filter((f) => !nonEmpty(last[f]));
      checks.push({ name: '新条目字段齐全', ok: missing.length === 0, detail: missing.length ? `缺 ${missing.join(',')}` : RULE_REQUIRED_FIELDS.join('/') });
      checks.push({ name: `version → ${e.versionAfter}`, ok: obj.version === e.versionAfter, detail: `实际 ${obj.version}` });
      checks.push({ name: '既有规则原文未改', ok: JSON.stringify(obj.rules.slice(0, e.entriesBefore)) === JSON.stringify(JSON.parse(w.before).rules), detail: 'prefix-compare' });
    }
  } else if (e.kind === 'append-marker') {
    checks.push({ name: `追加标记 '${e.marker}' 存在`, ok: text.includes(e.marker), detail: 'marker' });
    // ★ 只增不删的真实不变式：原文**每一行非空行**都要在写入后按序仍在。
    //   （初版这里写的是"原文本必须是前缀"，但哲学 changelog 是**插在中间**的（新条目在「版本历史」下），
    //    于是 correct 的写入被判成失败 → 触发回滚 —— 一个会撒谎的检查。R006 坑#4 同类。）
    const lost = linesLost(w.before, text);
    checks.push({
      name: '原文所有行按序仍在（只增不删）',
      ok: lost.length === 0,
      detail: lost.length ? `丢失 ${lost.length} 行，例如: ${JSON.stringify(lost.slice(0, 3))}` : `原 ${w.before.split('\n').filter(Boolean).length} 行全在，新增 ${text.length - w.before.length} 字节`
    });
    checks.push({ name: '写入后比原文更长（确实新增）', ok: text.length > w.before.length, detail: `${w.before.length} → ${text.length} 字节` });
  } else if (e.kind === 'spec') {
    checks.push({ name: `SOP 内容与预期一致`, ok: text === w.after, detail: `${text.length} 字节` });
  }
  return { ok: checks.every((c) => c.ok), checks };
}

/** 执行一个计划：写盘 → 回读校验 → 失败自动回滚（含台账）。dryRun 时**在写任何字节之前返回**。 */
export function applyOne(plan, { dryRun = false, stamp } = {}) {
  const st = stamp || stampNow();
  if (dryRun) {
    log('apply.skipped-dry-run', { proposal_id: plan.proposal_id, outcome: plan.outcome, target: plan.target, writes: plan.writes.map((w) => w.rel) });
    return { ...plan, dryRun: true, applied: false, wrote: [], backups: [], verified: null, rolledBack: [] };
  }
  const wrote = [];
  const backups = [];
  const verifications = [];
  try {
    // 0) 并发写保护：别人改过库 → 拒绝盲写（防丢更新）
    for (const w of plan.writes) {
      const now = fs.existsSync(w.abs) ? sha256(readText(w.abs)) : null;
      if (now !== w.sha256Before) {
        throw new GateError('CONCURRENT_MODIFY',
          `拒绝：目标文件自计划生成后被改动（${w.rel}：${String(w.sha256Before).slice(0, 8)} → ${String(now).slice(0, 8)}）。` +
          `本工具不覆盖别人的写入——请重新生成计划。`);
      }
    }
    // 0.5) R001 红绿灯：别人持锁时不硬写（失败即停）
    for (const w of plan.writes) assertNotLocked(w.abs);
    // 1) 备份前置（全部先备份，且回读验证）
    for (const w of plan.writes) {
      const b = backupFile(w.abs, st, { mustParseJson: w.rel.endsWith('.json') });
      if (b) backups.push({ rel: w.rel, abs: w.abs, ...b });
    }
    // 2) 逐个原子写 + 立即回读校验
    for (const w of plan.writes) {
      const r = writeAtomic(w.abs, w.after, {
        validate: (t) => { if (w.rel.endsWith('.json')) JSON.parse(t); if (t.length === 0) throw new GateError('EMPTY_WRITE', `拒绝写入空内容: ${w.rel}`); }
      });
      wrote.push({ rel: w.rel, ...r });
      const v = verifyWrite(w);
      verifications.push({ rel: w.rel, ...v });
      if (!v.ok) {
        throw new GateError('VERIFY_FAILED',
          `回读校验失败（${w.rel}）: ${v.checks.filter((c) => !c.ok).map((c) => c.name).join('; ')}`);
      }
    }
    // 3) 台账（最后写；失败同样触发回滚——库与台账必须一致）
    if (plan.ledgerEntry) {
      const led = loadLedger(plan.root);
      const next = {
        version: led.obj.version || 1,
        updated: new Date().toISOString(),
        tool: `dsh-plugin-reflect-enroll v${VERSION}`,
        entries: [...(led.obj.entries || []), { ...plan.ledgerEntry, files: wrote.map((x) => x.rel), backup_stamp: st }]
      };
      const b = backupFile(led.abs, st, { mustParseJson: true });
      if (b) backups.push({ rel: REL.ledger, abs: led.abs, ...b });
      writeAtomic(led.abs, renderJsonLike(led.style, next), { validate: (t) => JSON.parse(t) });
      const back = JSON.parse(readText(led.abs));
      const okLedger = back.entries.some((e) => e.proposal_id === plan.proposal_id && e.outcome === plan.outcome);
      verifications.push({ rel: REL.ledger, ok: okLedger, checks: [{ name: '台账已记录本次入册（幂等门依据）', ok: okLedger, detail: `${back.entries.length} 条` }] });
      if (!okLedger) throw new GateError('VERIFY_FAILED', '台账回读未见本次入册记录');
      wrote.push({ rel: REL.ledger, path: led.abs });
    }
    log('apply.ok', {
      input: { proposal_id: plan.proposal_id, decision: plan.decision, target: plan.target },
      judge: { outcome: plan.outcome, ref: plan.ref },
      result: { ok: true, wrote: wrote.map((w) => w.rel), backups: backups.map((b) => b.path) },
      diag: { stamp: st, dryRun: false }
    });
    return { ...plan, applied: true, wrote: wrote.map((w) => w.rel), backups: backups.map((b) => b.path), verified: verifications, rolledBack: [] };
  } catch (e) {
    // ★ 失败即回滚：把本次已写的文件逐个还原（用备份内容写回），并回读验证
    const rolled = [];
    const rollbackErrors = [];
    for (const w of wrote.slice().reverse()) {
      const b = backups.find((x) => x.abs === w.path || x.rel === w.rel);
      try {
        if (b) {
          const r = restoreFromBackup(b);
          const nowSha = sha256(readText(b.abs));
          if (nowSha !== b.sha256) throw new Error(`回滚后 sha256 不一致（${nowSha.slice(0, 12)} ≠ ${String(b.sha256).slice(0, 12)}）`);
          rolled.push({ rel: w.rel, restored: true, restored_sha256: r.sha256, expected_sha256: b.sha256, matched: true });
        } else {
          // 本次新建的文件：无备份可还原 —— 记录并如实上报（本工具无删除能力，空壳留给人处置）
          rolled.push({ rel: w.rel, restored: false, note: '本次新建文件，无备份（工具无删除能力，已如实上报）' });
        }
      } catch (err) { rollbackErrors.push({ rel: w.rel, err: err.message }); }
    }
    log('apply.failed', {
      input: { proposal_id: plan.proposal_id, decision: plan.decision, target: plan.target },
      judge: { code: e.code || 'ERROR' },
      result: { ok: false, error: e.message, wrote: wrote.map((w) => w.rel), rolledBack: rolled, rollbackErrors },
      diag: { stamp: st, backups: backups.map((b) => b.path) }
    });
    const err = new GateError(e.code || 'ENROLL_FAILED', `${e.message}\n  ↳ 已回滚: ${rolled.map((r) => r.restored_sha256 ? `${r.rel}(sha256=${String(r.restored_sha256).slice(0, 12)})` : `${r.rel}(本次新建,无备份可还原)`).join(' · ') || '（无需回滚）'}`);
    err.rolledBack = rolled;
    err.rollbackErrors = rollbackErrors;
    err.backups = backups.map((b) => b.path);
    throw err;
  }
}

/** 批量：逐条计划 → 逐条执行；**第一条被拒即停**（失败即停，不继续放行后续入册）。 */
export function enrollAll({ root, rulings, proposals, dryRun = false, date, stamp }) {
  const r = resolveRoot(root);
  const d = date || todayDate();
  const st = stamp || stampNow();
  const led = loadLedger(r);
  const results = [];
  const seen = new Map(); // 本次运行内也做幂等（同批重复 proposal_id 即拒）

  for (const ruling of rulings) {
    const proposalId = String(ruling.proposal_id || '');
    if (seen.has(proposalId)) {
      const e = new GateError('DUPLICATE_IN_BATCH', `拒绝：提案 '${proposalId}' 在本批裁定中出现了 ${seen.get(proposalId) + 1} 次——同批重复入册即拒。`);
      log('plan.rejected', { input: { proposal_id: proposalId }, judge: { code: e.code }, result: { ok: false, error: e.message } });
      throw e;
    }
    seen.set(proposalId, 1);

    let plan;
    try {
      plan = planOne({
        root: r, ruling, date: d,
        proposal: proposals ? proposals.get(proposalId) : undefined,
        ledgerEntries: [...(led.obj.entries || []), ...results.filter((x) => x.ledgerEntry).map((x) => x.ledgerEntry)]
      });
    } catch (e) {
      log('plan.rejected', {
        input: { proposal_id: proposalId, decision: ruling.decision, target: ruling.target },
        judge: { code: e.code || 'ERROR' },
        result: { ok: false, error: e.message },
        diag: { date: d, dryRun }
      });
      throw e;
    }
    const res = applyOne(plan, { dryRun, stamp: st });
    results.push(res);
    if (res.applied && res.ledgerEntry) led.obj.entries.push(res.ledgerEntry);
  }
  return { root: r, date: d, stamp: st, dryRun, results, ledger: inRoot(r, REL.ledger) };
}

export const ENROLL_TARGETS = LIBRARY_TARGETS;
