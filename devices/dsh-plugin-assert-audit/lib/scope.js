/**
 * lib/scope.js — 范围审查：枚举「agent 会话 / 跨设备沟通」工具链的全部组件，
 *                并判定每个组件的**审计覆盖状态**，输出盲区清单。
 *
 * 动因（2026-10-01）：我审了自己新写的代码，却漏审了 node-bridge —— 那个已造成
 * 三次生产事故的组件。偏差是：**倾向审「我新写的」和「我刚碰过的」，漏掉「有事故史但不热」的**。
 * 「已被兜住」≠「已被审计」，而兜底最容易替代审计。本工具把这件事从靠记性变成靠枚举。
 *
 * ★ 三条防「空集通过」纪律（都是实测踩过的）：
 *   1. **多源发现**：进程 / launchd / profile 依赖 / 文件系统 —— 任一源失败必须显式报出，
 *      不得静默当成「该源无组件」。
 *   2. **覆盖判定三态**：COVERED / HAS_TESTS_NO_AUDIT / NO_TESTS / **UNKNOWN（不可判）**。
 *      UNKNOWN 不得折算为 COVERED 或 NO_TESTS。
 *   3. **自述盲区**：工具必须报出「我这一类看不见什么」（如二进制无源码、外部设备上的组件）。
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { assertCommand, DENIED_SUBCOMMANDS } from './gate.js';

/* ── ⑩ 类型锁：范围判定的模式表**冻结**（不靠启发式猜名字） ── */
export const SCOPE_PATTERNS = Object.freeze([
  'agent-bus', 'agentbus', 'agent-way', 'central-inbox', 'inbox-watch', 'central-wake',
  'comm-sync', 'comm-server', 'comm-device', 'device-daemon', 'bus-bridge', 'node-bridge',
  'blackboard', 'bb-sub', 'bb-gate', 'hb-forward', 'mailbox', 'agent-mailbox',
  'comm_domains', 'comm-hub', 'coordinator', 'session-fa1f9150',
]);

/** ★ 负向排除面（冻结）。首版没有它，结果把 nsurlsessiond / liveactivitiesd /
 *  nesessionmanager 都收进来了 —— 因为它们含子串 'session'（R006 坑 #1「门太宽」）。
 *  排除面须**先判**：命中排除面即出局，不再看范围模式。 */
export const EXCLUDE_PATTERNS = Object.freeze([
  // 系统/无关守护（含 session 子串但与本工具链无关）
  'nsurlsession', 'liveactivities', 'nesessionmanager', 'com.apple.', 'sysmond',
  'sharedfilelistd', 'cfprefsd', 'distnoted', 'runningboardd', 'launchd',
  // 非源码载体（日志/备份/归档/索引）
  '.log', '.err', '.out', '.bak', '.gz', '.tar', '.json', '.db', '.sqlite', '.tmp',
  // 目录条目
  '_raw-notes', 'node_modules', '.git',
]);

/** 规范名：把 launchd label / 文件名 / 进程名归一成同一组件名，用于去重 */
export function canonicalName(raw) {
  let n = String(raw).trim();
  // ★ 2026-10-01 修正贪婪正则：原 [a-z0-9._-]* 会吃到**最后一个点**
  //   （com.dsh.node-bridge.mac-mini → 'mini'），导致源码映射全部挂不上、组件掉成 UNKNOWN。
  n = n.replace(/^com\.[a-z0-9-]+\./i, '');          // com.dsh.node-bridge.mac-mini → node-bridge.mac-mini
  n = n.replace(/^dsh-plugin-/, '');                 // dsh-plugin-agent-way → agent-way
  n = n.replace(/^dsh-/, '');
  n = n.replace(/\.(py|js|mjs|sh|rs|plist)$/i, '');   // 去扩展名
  n = n.replace(/\.(bak|p0|pre|good)[-._a-z0-9]*$/i, '');  // 去备份后缀
  n = n.replace(/[._]v?\d+(\.\d+)*$/, '');          // 去尾版本号
  n = n.split(/[\s(]/)[0];                            // 去参数/括号
  n = n.replace(/^.*\//, '');                         // 去路径
  return n.toLowerCase();
}

/** 角色分类（冻结）：判定该组件在通信链上处于哪一段 */
export const ROLE_RULES = Object.freeze([
  { role: 'store', patterns: ['blackboard', 'mailbox', 'bus-bridge', 'node-bridge'] },
  { role: 'transport', patterns: ['comm-sync', 'device-daemon', 'bus-bridge', 'node-bridge', 'hb-forward'] },
  { role: 'injector', patterns: ['inbox-watch', 'central-inbox', 'central-wake', 'agent-way'] },
  { role: 'producer/consumer', patterns: ['agent-bus', 'agent-way', 'bb-sub', 'session'] },
  { role: 'guard', patterns: ['log-guard', 'bb-gate', 'guard'] },
]);

/** ★ 源码映射表（冻结，人工维护）。
 *  为什么需要显式表：进程名（node-bridge-macos-arm64-v1.4.0）与 launchd label
 *  （com.dsh.node-bridge.mac-mini）都不等于源码目录名。首版按【精确键】匹配 ⇒ 挂不上，
 *  本该 HAS_TESTS_NO_AUDIT 的组件掉成 UNKNOWN（自查发现）。
 *  ★ 未登记者一律判 UNKNOWN 并**报出原因**，不猜——「不可判」不折算为任一侧。
 *  判据：key 出现在组件规范名里即命中；多 key 命中取**最长 key**（防 blackboard 吃掉 bb-sub）。 */
export const SOURCE_MAP = Object.freeze({
  'node-bridge': join(homedir(), 'dsh-collab', 'rust-bridge'),
  'rust-blackboard': join(homedir(), 'dsh-collab', 'rust-blackboard'),
  'inbox-watch': join(homedir(), 'dsh-collab', 'scripts'),
  'central-wake': join(homedir(), 'dsh-collab', 'scripts'),
  'hb-forward': join(homedir(), 'dsh-collab', 'scripts'),
  'bb-sub': join(homedir(), 'dsh-collab', 'scripts'),
  'bb-gate': join(homedir(), 'dsh-collab', 'scripts'),
  'device-daemon': join(homedir(), 'dsh-collab', 'comm-server'),
  'sync-from-central': join(homedir(), 'dsh-collab', 'comm-server'),
  'sync-to-central': join(homedir(), 'dsh-collab', 'comm-server'),
  'agent-mailbox': join(homedir(), 'dsh-collab', 'comm-server'),
  'agent-way': join(homedir(), 'dsh-plugin-agent-bus'),
  'central-inbox': join(homedir(), 'dsh-plugin-central-inbox'),
  'bus-bridge': join(homedir(), 'dsh-collab', 'devices', 'bus-bridge'),
  'comm-sync': join(homedir(), 'dsh-collab', 'comm-server'),
});

/** 按【最长 key】命中，避免 'blackboard' 吃掉 'bb-sub' 这类更具体的组件 */
export function sourcePathFor(canonical) {
  const low = String(canonical).toLowerCase();
  let best = null; let bestLen = -1;
  for (const [k, v] of Object.entries(SOURCE_MAP)) {
    if (low.includes(k) && k.length > bestLen && existsSync(v)) { best = v; bestLen = k.length; }
  }
  return best;
}

/** 已知事故史（人工登记，冻结）：用于盲区排序的「爆炸半径」 */
export const INCIDENT_HISTORY = Object.freeze({
  'node-bridge': '三次磁盘事故（21GB / 127.41GB / 156.35GB）',
  'mac-mini-inbox-watch': '5s 全量拉 20.76MB；累积器 1,944 平铺文件',
  'central-inbox': '单槽 lastInjected（非去重）',
});

const VERDICT = Object.freeze({
  COVERED: 'COVERED',
  HAS_TESTS_NO_AUDIT: 'HAS_TESTS_NO_AUDIT',
  NO_TESTS: 'NO_TESTS',
  UNKNOWN: 'UNKNOWN',
});

function run(cmd, args) {
  assertCommand(cmd);
  try {
    return { ok: true, out: execFileSync(cmd, args, { encoding: 'utf8', timeout: 30000, shell: false }) };
  } catch (e) {
    return { ok: false, err: String(e.stderr || e.message || e).slice(0, 200), out: String(e.stdout || '') };
  }
}

/* ── 1. 多源发现 ── */
export function discover() {
  const sources = {};
  const gaps = [];

  // 源 A：运行中的进程
  const ps = run('ps', ['-eo', 'pid=,rss=,command=']);
  if (!ps.ok) { sources.processes = []; gaps.push(`进程源不可用：${ps.err}`); }
  else {
    sources.processes = ps.out.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
      const [pid, rss, ...rest] = l.split(/\s+/);
      const command = rest.join(' ');
      return { pid: Number(pid), rssMB: Math.round(Number(rss) / 1024), command };
    }).filter((p) => p.command && !p.command.startsWith('ps '));
  }

  // 源 B：launchd 服务
  const lc = run('launchctl', ['list']);
  if (!lc.ok) { sources.launchd = []; gaps.push(`launchd 源不可用：${lc.err}`); }
  else {
    sources.launchd = lc.out.split('\n').slice(1).map((l) => l.trim()).filter(Boolean).map((l) => {
      const [pid, status, label] = l.split('\t');
      return { label, pid: pid === '-' ? null : Number(pid), lastExit: Number(status) };
    }).filter((s) => s.label);
  }

  // 源 C：profile 插件依赖
  const profilePkg = join(homedir(), '.dsh', 'profiles', 'web', 'package.json');
  sources.plugins = [];
  if (!existsSync(profilePkg)) gaps.push(`profile package.json 不存在：${profilePkg}`);
  else {
    try {
      const deps = Object.keys(JSON.parse(readFileSync(profilePkg, 'utf8')).dependencies || {});
      sources.plugins = deps.map((name) => ({ name }));
    } catch (e) { gaps.push(`profile package.json 解析失败：${String(e.message).slice(0, 80)}`); }
  }

  // 源 D：文件系统（脚本 / Rust 工程 / comm-server / devices）
  const roots = [
    join(homedir(), 'dsh-collab', 'scripts'),
    join(homedir(), 'dsh-collab', 'comm-server'),
    join(homedir(), 'dsh-collab', 'rust-bridge'),
    join(homedir(), 'dsh-collab', 'rust-blackboard'),
    join(homedir(), 'dsh-collab', 'rust-tools'),
    join(homedir(), 'dsh-collab', 'devices'),
    join(homedir(), 'dsh-plugin-agent-bus'),
    join(homedir(), 'dsh-plugin-central-inbox'),
  ];
  sources.paths = [];
  for (const r of roots) {
    if (!existsSync(r)) { gaps.push(`路径源不存在：${r}`); continue; }
    try { for (const f of readdirSync(r)) sources.paths.push({ root: r, entry: f }); }
    catch (e) { gaps.push(`路径不可读 ${r}：${String(e.message).slice(0, 60)}`); }
  }

  // 自述盲区（工具看不见什么）
  gaps.push('外部设备（MBP / i9 / 服务器）上的组件不在本机枚举范围');
  gaps.push('二进制产物若无配套源码目录，只能判 UNKNOWN');
  gaps.push('范围模式表是冻结白名单 —— 名字不含任何模式的新组件会被漏（需人工补模式）');
  return { sources, gaps };
}

/* ── 2. 归入范围 ── */
export function inScope(name) {
  const low = String(name).toLowerCase();
  if (EXCLUDE_PATTERNS.some((p) => low.includes(p))) return false;   // ★ 排除面先判
  return SCOPE_PATTERNS.some((p) => low.includes(p));
}

export function roleOf(name) {
  const low = String(name).toLowerCase();
  for (const r of ROLE_RULES) if (r.patterns.some((p) => low.includes(p))) return r.role;
  return 'unknown-role';
}

/* ── 3. 覆盖判定（三态 + 不可判） ── */
function countAssertions(dir) {
  // 递归找源文件并统计断言
  const found = { files: [], count: 0, langs: new Set() };
  const walk = (d, depth = 0) => {
    if (depth > 3) return;
    let ents;
    try { ents = readdirSync(d); } catch { return; }
    for (const e of ents) {
      if (e === 'node_modules' || e === 'target' || e === 'dist' || e === '.git') continue;
      const p = join(d, e);
      let st;
      try { st = statSync(p); } catch { continue; }
      if (st.isDirectory()) { walk(p, depth + 1); continue; }
      let src = '';
      try { src = readFileSync(p, 'utf8'); } catch { continue; }
      let n = 0; let lang = null;
      if (p.endsWith('.rs')) { n = (src.match(/#\[test\]/g) || []).length; lang = 'rust'; }
      else if (p.endsWith('.py')) { n = (src.match(/\bcheck\(\s*["']/g) || []).length + (src.match(/^\s*assert /gm) || []).length; lang = 'python'; }
      else if (p.endsWith('.js') || p.endsWith('.mjs')) { n = (src.match(/\bassert\s*\(/g) || []).length; lang = 'js'; }
      if (n > 0) { found.files.push(p); found.count += n; if (lang) found.langs.add(lang); }
    }
  };
  walk(dir);
  return { ...found, langs: [...found.langs] };
}

function hasAuditRecord(name, auditDir) {
  let ents = [];
  try { ents = readdirSync(auditDir); } catch { return { found: false, reason: `审计记录目录不可读：${auditDir}` }; }
  const low = name.toLowerCase();
  const hits = ents.filter((e) => {
    const el = e.toLowerCase();
    return el.includes(low) && (el.includes('audit') || el.includes('审查'));
  });
  return { found: hits.length > 0, hits, reason: hits.length ? null : '未找到含该组件名且含 audit/审查 的记录文件' };
}

export function coverageOf(component, { auditDir }) {
  const p = component.sourcePath;
  if (!p || !existsSync(p)) {
    return { verdict: VERDICT.UNKNOWN, reason: component.noSourceReason || '无源码目录 ⇒ 不可判（既不能判已覆盖也不能判未覆盖）' };
  }
  const a = countAssertions(p);
  const rec = hasAuditRecord(component.name, auditDir);
  if (a.count === 0) return { verdict: VERDICT.NO_TESTS, assertions: 0, reason: '未发现任何断言/测试' };
  if (!rec.found) return { verdict: VERDICT.HAS_TESTS_NO_AUDIT, assertions: a.count, langs: a.langs, reason: rec.reason };
  return { verdict: VERDICT.COVERED, assertions: a.count, langs: a.langs, auditRecord: rec.hits };
}

/* ── 4. 汇总 ── */
export function scopeAudit({ auditDir = join(homedir(), 'dsh-collab', 'logs') } = {}) {
  const { sources, gaps } = discover();

  // 把多源合并成「组件」候选
  const cand = new Map();
  const add = (name, extra) => {
    if (!name) return;
    if (!inScope(name)) return;
    const key = canonicalName(name);                 // ★ 规范名去重（同一组件的进程/服务/文件只算一个）
    if (!cand.has(key)) cand.set(key, { name, canonical: key, aliases: [], evidence: [], rssMB: 0, pids: [] });
    const c = cand.get(key);
    if (!c.aliases.includes(name)) c.aliases.push(name);
    Object.assign(c, extra);
    if (!c.evidence.includes(extra.kind)) c.evidence.push(extra.kind);
  };

  for (const p of sources.processes) {
    const base = p.command.split('/').pop().split(/\s+/)[0];
    if (inScope(base) || inScope(p.command)) add(base, { kind: 'process', rssMB: p.rssMB, pids: [p.pid], command: p.command });
  }
  for (const s of sources.launchd) if (inScope(s.label)) add(s.label, { kind: 'launchd', pid: s.pid });
  for (const pl of sources.plugins) if (inScope(pl.name)) add(pl.name, { kind: 'plugin' });
  for (const e of sources.paths) if (inScope(e.entry)) add(`${e.entry}`, { kind: 'path', sourcePath: join(e.root, e.entry) });

  // 为每个候选挂源码路径（显式表 + 最长 key 命中；未登记 ⇒ 保持 UNKNOWN 并给原因）
  for (const c of cand.values()) {
    if (c.sourcePath) continue;
    const p = sourcePathFor(c.canonical || canonicalName(c.name));
    if (p) c.sourcePath = p;
    else c.noSourceReason = '未登记于 SOURCE_MAP（需人工补映射，不猜）';
  }

  const items = [];
  for (const c of cand.values()) {
    const cov = coverageOf(c, { auditDir });
    const incident = Object.entries(INCIDENT_HISTORY)
      .find(([k]) => c.name.toLowerCase().includes(k))?.[1] || null;
    // 爆炸半径：有事故史 > 常驻内存 > 其余
    const blast = (incident ? 1000 : 0) + (c.rssMB || 0);
    items.push({ name: c.name, role: roleOf(c.name), kind: c.evidence.join('+'),
      rssMB: c.rssMB || 0, incident, coverage: cov, blast });
  }
  items.sort((a, b) => b.blast - a.blast);

  const blind = items.filter((i) => i.coverage.verdict !== VERDICT.COVERED);
  const tally = {
    total: items.length,
    COVERED: items.filter((i) => i.coverage.verdict === VERDICT.COVERED).length,
    HAS_TESTS_NO_AUDIT: items.filter((i) => i.coverage.verdict === VERDICT.HAS_TESTS_NO_AUDIT).length,
    NO_TESTS: items.filter((i) => i.coverage.verdict === VERDICT.NO_TESTS).length,
    UNKNOWN: items.filter((i) => i.coverage.verdict === VERDICT.UNKNOWN).length,
  };
  return { items, blind, tally, gaps, sources: Object.fromEntries(
    Object.entries(sources).map(([k, v]) => [k, v.length])) };
}

export { VERDICT as SCOPE_VERDICT, DENIED_SUBCOMMANDS };
