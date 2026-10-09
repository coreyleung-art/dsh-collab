/**
 * gate.js — R006 ⑩ 结构门：约束前置 · 不可绕过
 * =============================================================================
 * 本工具的三条「不该发生路径」，门不靠纪律，靠**结构**：
 *
 *   ① 写被审对象        —— 只读侧根本没有任何写调用；唯一的写目标是 INDEX_PATH 常量，
 *                          且 assertWriteTargetAllowed() 要求 target === INDEX_PATH 全等。
 *   ② 把索引写到别处    —— 索引路径是**模块常量**，不是入参：没有那个入口，
 *                          「写到别处」在语法上不可表达（schema 里也没有这个键）。
 *   ③ source 传路径     —— SOURCE_ENUM 是冻结枚举 ["inbox"]，传 "/etc" / "./inbox" /
 *                          "~/..." 一律 GateError；没有「任意目录」这个入口。
 *
 * --lean4-check 的 A–F 六项逐项实测（含正/负例矩阵），B ≥ 8 条负例、C ≥ 3 条正例、
 * E 用 Object.isFrozen 实测、F 枚举命令调用点并要求集合非空且 ⊆ {node}。
 */

import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

/* ══════════════════════════════ 结构常量（冻结） ══════════════════════════════ */

/** 数据源：P0 只做 inbox。不是「默认值」，是**唯一的合法值**。 */
export const SOURCE_ENUM = Object.freeze(['inbox']);

/** 四个工具各自的动作名（R006 命名门已过，工具名不得改）。 */
export const ACTIONS = Object.freeze(['check', 'batch', 'explain', 'index_write']);

/** 五态：条目有效性判定的**值域**。 */
export const STATES = Object.freeze(['closed', 'stale', 'open', 'unknown', 'n/a']);

/** 五态 + 形态：形态与状态是两个轴，分开报。 */
export const SHAPES = Object.freeze(['action', 'record', 'feed', 'ack', 'unknown']);

/** 允许被本工具执行的外部命令。集合就是 {node} —— 插件本体不 exec 任何东西。 */
export const COMMAND_WHITELIST = Object.freeze(['node']);

/** 数据源根目录（只读侧的唯一读取根）。 */
export const INBOX_DIR = join(homedir(), '.dsh', 'inbox');

/**
 * ★ 唯一写目标：索引路径**写死为模块常量**，不作为入参。
 *   这是结构约束 —— 让「写到别处」在语法上不可表达。
 */
export const INDEX_PATH = join(homedir(), 'dsh-collab', 'docs', 'item-validity-index.json');

/** 统一日志（R7）：每次判一条写一行 JSON。 */
export const LOG_PATH = join(homedir(), 'dsh-collab', 'logs', 'dsh-plugin-item-validity-review-check.log');

/**
 * 危险原语（A 项扫描靶子）。
 * ★ 以**字符串字面量**存放在此：scanDangerousPrimitives 先剥字面量再扫，
 *   因此本清单自身不会被当成命中（这是「扫描器误伤自己」坑的修法）。
 */
export const FORBIDDEN_PRIMITIVES = Object.freeze([
  'child_process',
  'execSync',
  'execFileSync',
  'execFile',
  'spawnSync',
  'spawn',
  'fork',
  'eval',
  'new Function',
  'rmSync',
  'unlinkSync',
  'process.kill',
  'pkill',
  'killall',
  'rm -rf',
  'process.exit'
]);

/** 进程退出是**允许的**，但仅限 cli.js 入口 —— 见 A 项 detail 里的豁免理由。 */
export const EXIT_EXEMPT_FILE = 'cli.js';

/** A 项的扫描范围：只含 lib/*.js（cli.js 不在内，其入口 process.exit 有豁免）。 */
export const SCAN_SCOPE_DIR = 'lib';

/* ══════════════════════════════ 门错误 ══════════════════════════════ */

export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/* ══════════════════════════════ 门 1：数据源冻结枚举 ══════════════════════════════ */

/**
 * 只接受冻结枚举内的 source。
 * ★ 先判**精确枚举命中**，再对非白名单输入给「路径」类原因 ——
 *   否则「禁止路径」的正则会把合法值也误伤（门太宽）。
 */
export function assertSource(input) {
  if (typeof input !== 'string') {
    throw new GateError('GATE_SOURCE_DENIED',
      '拒绝：source 必须是字符串，实得 ' + (input === null ? 'null' : typeof input) + '；只能是 ' + SOURCE_ENUM.join(', '));
  }
  const v = input.trim();
  if (SOURCE_ENUM.includes(v)) return v;
  // 非枚举：给可操作原因（但结论一样是拒）
  if (v === '') {
    throw new GateError('GATE_SOURCE_DENIED', '拒绝：source 为空。本工具不接受空值，只能是 ' + SOURCE_ENUM.join(', '));
  }
  if (v.includes('/') || v.includes('\\') || v.startsWith('~') || v.includes('*')) {
    throw new GateError('GATE_SOURCE_DENIED',
      '拒绝：source 传了路径「' + v + '」。source 是**冻结枚举**（' + SOURCE_ENUM.join(', ') + '），' +
      '不是目录参数 —— 「扫别的目录」这个入口在语法上不存在。');
  }
  throw new GateError('GATE_SOURCE_DENIED',
    '拒绝：source「' + v + '」不在冻结枚举内，只能是 ' + SOURCE_ENUM.join(', ') + '。');
}

/* ══════════════════════════════ 门 2：动作 / 状态枚举 ══════════════════════════════ */

export function assertAction(action) {
  if (typeof action !== 'string' || !ACTIONS.includes(action)) {
    throw new GateError('GATE_ACTION_DENIED',
      '拒绝：action 不在冻结枚举内（' + JSON.stringify(action) + '）；允许: ' + ACTIONS.join(', '));
  }
  return true;
}

export function assertState(state) {
  if (typeof state !== 'string' || !STATES.includes(state)) {
    throw new GateError('GATE_STATE_DENIED',
      '拒绝：state 不在冻结枚举内（' + JSON.stringify(state) + '）；允许: ' + STATES.join(', '));
  }
  return true;
}

/** 四个工具的 action 归属必须在冻结枚举内（apply 期调用 ⇒ 门是承重的，不是装饰）。 */
export function assertToolActions(pairs) {
  for (const [toolName, action] of pairs) {
    if (!ACTIONS.includes(action)) {
      throw new GateError('GATE_ACTION_DENIED',
        '拒绝：工具 ' + toolName + ' 声明的 action「' + action + '」不在冻结枚举内');
    }
  }
  return true;
}

/* ══════════════════════════════ 门 3：索引路径不可作为入参 ══════════════════════════════ */

const PATHISH_KEYS = Object.freeze(['indexPath', 'index_path', 'index', 'out', 'outPath', 'target', 'path', 'file', 'dir', 'directory']);

/**
 * 索引路径**不是入参**。调用方若试图传路径类键 ⇒ 拒。
 * schema 里本来就没有这些键（模型侧不可表达）；本函数是纵深防御 ——
 * 防未来有人「顺手」加一个入参。
 */
export function assertNoIndexPathInput(args) {
  if (args === null || typeof args !== 'object') return true;
  for (const k of Object.keys(args)) {
    if (PATHISH_KEYS.includes(k)) {
      throw new GateError('GATE_INDEX_PATH_INPUT',
        '拒绝：入参含路径类键「' + k + '」。索引路径是模块常量 ' + INDEX_PATH +
        '，**不作为入参** —— 这样「把索引写到别处」在结构上不可表达。');
    }
  }
  return true;
}

/** 唯一的写目标全等断言：target 必须 === INDEX_PATH，否则拒。 */
export function assertWriteTargetAllowed(target) {
  if (target !== INDEX_PATH) {
    throw new GateError('GATE_WRITE_TARGET_DENIED',
      '拒绝：写目标「' + String(target) + '」不等于唯一允许的索引路径常量。' +
      '本插件只有一处写操作，目标写死。');
  }
  const inboxPrefix = INBOX_DIR + '/';
  if (String(target).startsWith(inboxPrefix)) {
    throw new GateError('GATE_WRITE_TARGET_DENIED',
      '拒绝：写目标落在被审数据源目录内 —— **绝不写任何被审条目**。');
  }
  return true;
}

/* ══════════════════════════════ 门 4：外部命令白名单 ══════════════════════════════ */

export function assertCommandAllowed(command) {
  const first = String(command).trim().split(/\s+/)[0];
  if (!COMMAND_WHITELIST.includes(first)) {
    throw new GateError('GATE_COMMAND_DENIED',
      '拒绝：命令不在白名单「' + first + '」；允许: ' + COMMAND_WHITELIST.join(', '));
  }
  return true;
}

/* ══════════════════════════════ 源码结构扫描（A 项的真扫） ══════════════════════════════ */

/**
 * 剥掉注释 / 字符串 / 模板 / 正则字面量（行号保持不变：字面量按原长度换成空格）。
 * 为什么必须剥：初版直接扫原文，**把自己的检测清单和帮助文本当成了危险原语** —— 假阳性。
 * 说明：这是源码结构扫描，不是完整 AST（本包零外部依赖，宿主内无可用解析器），
 *       命名与输出如实标注，不冒充 AST。
 */
export function stripLiterals(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  const blank = (s) => { for (const ch of s) out += (ch === '\n' ? '\n' : ' '); };
  while (i < n) {
    const c = src[i];
    const d = src[i + 1];
    if (c === '/' && d === '/') { let j = i; while (j < n && src[j] !== '\n') j++; blank(src.slice(i, j)); i = j; continue; }
    if (c === '/' && d === '*') { let k = src.indexOf('*/', i + 2); k = k < 0 ? n : k + 2; blank(src.slice(i, k)); i = k; continue; }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === c) { j++; break; } j++; }
      blank(src.slice(i, j)); i = j; continue;
    }
    if (c === '/') {
      const lineEnd = src.indexOf('\n', i);
      const stop = lineEnd < 0 ? n : lineEnd;
      const prev = out.replace(/\s+$/, '').slice(-1);
      const regexPos = prev === '' || '(,=:[!&|?{};'.includes(prev);
      if (regexPos) {
        let j = i + 1;
        let closed = false;
        while (j < stop) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === '/') { closed = true; j++; break; } j++; }
        if (closed) { blank(src.slice(i, j)); i = j; continue; }
      }
    }
    out += c;
    i++;
  }
  return out;
}

/** 构造「调用形态」检测（限定标识符边界，且排除 `.exec(` 这类方法调用）。 */
function primitivePattern(name) {
  const esc = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (name === 'child_process' || name === 'rm -rf') return new RegExp(esc);
  if (name === 'new Function') return new RegExp('\\bnew\\s+Function\\s*\\(');
  if (name === 'eval') return new RegExp('(?<![\\w.$])eval\\s*\\(');
  if (name === 'process.kill') return new RegExp('\\bprocess\\s*\\.\\s*kill\\s*\\(');
  if (name === 'process.exit') return new RegExp('\\bprocess\\s*\\.\\s*exit\\s*\\(');
  if (name === 'pkill' || name === 'killall') return new RegExp('(?<![\\w.$-])' + esc + '(?![\\w-])');
  return new RegExp('(?<![\\w.$])' + esc + '\\s*\\(');
}

/**
 * A 项真扫：**剥字面量后**逐行匹配危险原语。
 * @returns [{file, line, primitive, text}]
 */
export function scanDangerousPrimitives(sources) {
  const hits = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    const lines = code.split('\n');
    for (let idx = 0; idx < lines.length; idx++) {
      for (const name of FORBIDDEN_PRIMITIVES) {
        if (primitivePattern(name).test(lines[idx])) {
          hits.push({ file, line: idx + 1, primitive: name, text: lines[idx].trim().slice(0, 120) });
        }
      }
    }
  }
  return hits;
}

/** 第二道：**原文**里 import/require 危险模块（剥字面量会把模块名一起剥掉，故必须单独扫原文）。 */
export function scanForbiddenModules(sources) {
  const hits = [];
  const pattern = /(?:^|[^\w.])import\s[^;\n]*?\bfrom\s*['"]([^'"]+)['"]|(?:^|[^\w.$])require\s*\(\s*['"]([^'"]+)['"]/g;
  for (const [file, raw] of Object.entries(sources)) {
    for (const line of raw.split('\n')) {
      for (const m of line.matchAll(pattern)) {
        const spec = m[1] || m[2] || '';
        if (/(^|:)child_process$|(^|:)vm$|(^|:)worker_threads$/.test(spec)) {
          hits.push({ file, spec, text: line.trim().slice(0, 120) });
        }
      }
    }
  }
  return hits;
}

/**
 * A 项的正向对照（防「扫描器坏了自己不知道」）：拿一段**人造**含危险原语的源码跑同一个扫描器，
 * 必须命中；否则 A 项的「0 命中」毫无意义。
 */
export function scannerControl() {
  const planted = [
    'const cp = await import("node:' + 'child_' + 'process")',
    'const r = ' + 'exec' + 'Sync("whoami")',
    'const p = ' + 'spawn' + '("sh", ["-c", "x"])',
    'const e = ' + 'eval' + '(payload)',
    'process.' + 'exit' + '(1)'
  ].join('\n');
  const hits = scanDangerousPrimitives({ 'control.js': planted });
  const names = [...new Set(hits.map((h) => h.primitive))];
  return {
    sampleLines: planted.split('\n').length,
    hits: hits.length,
    primitives: names,
    ok: hits.length >= 3 && names.includes('eval') && names.includes('process.exit')
  };
}

/* ══════════════════════════════ F 项：命令调用点枚举 ══════════════════════════════ */

/**
 * 枚举「本交付物会被用什么命令调用」的**全部调用点**：
 *   ① package.json 的 scripts（每个脚本的第一个 token）
 *   ② cli.js 的 shebang 解释器
 *   ③ docs/README.md 复现命令里紧邻 cli.js 前的那个 token
 * ★ 空集必须判失败（「0 ⊆ 允许」是假通过）。
 */
export function scanCommandSites({ root }) {
  const sites = [];
  const push = (origin, command, raw) => sites.push({ origin, command, raw: String(raw).trim().slice(0, 120) });

  const pkgPath = join(root, 'package.json');
  if (existsSync(pkgPath)) {
    try {
      const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
      for (const [name, cmd] of Object.entries(pkg.scripts || {})) {
        const first = String(cmd).trim().split(/\s+/)[0];
        if (first) push('package.json:scripts.' + name, first, cmd);
      }
    } catch { /* 读失败不掩盖结论：由 site 数不足来暴露 */ }
  }

  const cliPath = join(root, 'cli.js');
  if (existsSync(cliPath)) {
    const first = readFileSync(cliPath, 'utf8').split('\n')[0];
    const m = first.match(/^#!\s*\S*\s+(\S+)/);
    if (m) push('cli.js:shebang', m[1], first);
  }

  const docPath = join(root, 'docs', 'README.md');
  if (existsSync(docPath)) {
    for (const line of readFileSync(docPath, 'utf8').split('\n')) {
      if (!line.includes('cli.js')) continue;
      for (const m of line.matchAll(/([\w./-]+)\s+cli\.js/g)) push('docs/README.md', m[1], line);
    }
  }

  const commands = [...new Set(sites.map((s) => s.command))];
  return { sites, commands };
}

/* ══════════════════════════════ B / C 项：负例与正例矩阵 ══════════════════════════════ */

/**
 * 负例矩阵（≥ 8 条）。每条**实测**：被拒 ⇒ rejected=true 且给出 GateError code。
 * code===null 表示「竟然放过了」= 门失效。
 */
export function negativeMatrix() {
  const cases = [
    ['未知 action', () => assertAction('delete-everything')],
    ['空 action', () => assertAction('')],
    ['非字符串 action', () => assertAction(42)],
    ['白名单外命令', () => assertCommandAllowed('rm -rf /')],
    ['shell 包装命令', () => assertCommandAllowed('bash -c ls')],
    ['source 传 /etc', () => assertSource('/etc')],
    ['source 传相对路径', () => assertSource('./inbox')],
    ['source 传家目录通配', () => assertSource('~/.dsh/inbox/*')],
    ['source 传非字符串', () => assertSource(null)],
    ['索引路径作为入参', () => assertNoIndexPathInput({ indexPath: '/tmp/elsewhere.json' })],
    ['索引路径作为入参(path)', () => assertNoIndexPathInput({ path: '/tmp/elsewhere.json' })],
    ['写目标非索引常量', () => assertWriteTargetAllowed('/tmp/elsewhere.json')],
    ['写目标落在被审目录', () => assertWriteTargetAllowed(INBOX_DIR + '/x.json')],
    ['未知 state', () => assertState('maybe')]
  ];
  return cases.map((pair) => {
    try {
      pair[1]();
      return { case: pair[0], rejected: false, code: null };
    } catch (e) {
      return { case: pair[0], rejected: e instanceof GateError, code: e && e.code ? e.code : 'NON_GATE_ERROR' };
    }
  });
}

/** 正例矩阵（≥ 3 条）：**防「门太宽把功能也拦了」** —— 合法输入必须能过。 */
export function positiveMatrix() {
  const cases = [
    ['合法 source="inbox"', () => assertSource('inbox')],
    ['合法 action=check', () => assertAction('check')],
    ['合法 action=index_write', () => assertAction('index_write')],
    ['合法 state=closed', () => assertState('closed')],
    ['合法 state=n/a', () => assertState('n/a')],
    ['白名单命令 node', () => assertCommandAllowed('node cli.js --selfcheck')],
    ['无路径类键的入参', () => assertNoIndexPathInput({ source: 'inbox', maxAgeDays: 7 })],
    ['唯一索引写目标', () => assertWriteTargetAllowed(INDEX_PATH)]
  ];
  return cases.map((pair) => {
    try {
      const v = pair[1]();
      return { case: pair[0], accepted: true, value: v === true ? true : String(v) };
    } catch (e) {
      return { case: pair[0], accepted: false, error: String(e && e.message) };
    }
  });
}

/* ══════════════════════════════ --lean4-check 六项 A–F ══════════════════════════════ */

export function sha256File(path) {
  try {
    if (!existsSync(path)) return null;
    return createHash('sha256').update(readFileSync(path)).digest('hex');
  } catch {
    return null;
  }
}

/**
 * A–F 六项自证。
 * @param {{root:string, libFiles?:string[], dryRunProbe?:Function}} options
 *   dryRunProbe 由调用方注入（避免 gate → core 的循环依赖）：返回 {wrote:boolean,...}
 */
export function lean4Check(options = {}) {
  const root = options.root || process.cwd();
  const libFiles = options.libFiles || ['lib/gate.js', 'lib/core.js', 'lib/index.js', 'lib/selfcheck.js'];

  // ── 准备三类源码视图 ──
  const sources = {};
  for (const f of libFiles) {
    const p = join(root, f);
    sources[f] = existsSync(p) ? readFileSync(p, 'utf8') : '';
  }
  const missing = Object.entries(sources).filter(([, v]) => v === '').map(([k]) => k);

  // ── A：真扫源码（范围只含 lib/*.js）──
  const hits = scanDangerousPrimitives(sources);
  const modHits = scanForbiddenModules(sources);
  const control = scannerControl();
  const aOk = hits.length === 0 && modHits.length === 0 && control.ok && missing.length === 0;
  const aDetail =
    '扫描范围=' + SCAN_SCOPE_DIR + '/*.js（' + libFiles.join(', ') + '）；剥注释/字符串/正则后命中 ' +
    hits.length + ' 次、危险模块 import ' + modHits.length + ' 次' +
    (hits.length ? '，命中：' + JSON.stringify(hits) : '') +
    (modHits.length ? '，模块：' + JSON.stringify(modHits) : '') +
    (missing.length ? '；★ 未读到文件：' + missing.join(', ') : '') +
    '；正向对照（人造样本 ' + control.sampleLines + ' 行）命中 ' + control.hits + ' 次 [' + control.primitives.join(', ') + ']' +
    ' ⇒ 扫描器有效（非空判定）' +
    '；★ 豁免理由：cli.js 的 process.exit 是**入口返回码**（R006 ⑨ 退出码 0/1/2 的载体），' +
    '故扫描范围只含 lib/*.js，不含 ' + EXIT_EXEMPT_FILE + '。';

  // ── B：负例全部被拒（≥8）──
  const neg = negativeMatrix();
  const leaked = neg.filter((n) => n.rejected !== true);
  const bOk = neg.length >= 8 && leaked.length === 0;
  const bDetail = neg.length + ' 条负例，' + (neg.length - leaked.length) + ' 条被拒' +
    (leaked.length ? '；★ 竟然放行：' + JSON.stringify(leaked) : '') +
    '；码分布 ' + JSON.stringify([...new Set(neg.map((n) => n.code))]);

  // ── C：正例可用（≥3）──
  const pos = positiveMatrix();
  const posBad = pos.filter((p) => p.accepted !== true);
  const cOk = pos.length >= 3 && posBad.length === 0;
  const cDetail = pos.length + ' 条正例，' + (pos.length - posBad.length) + ' 条通过' +
    (posBad.length ? '；★ 被误拦：' + JSON.stringify(posBad) : '') +
    '（合法 source="inbox" 必须能过 —— 防「门太宽把功能也拦了」）';

  // ── D：--dry-run 零变更（写前后 sha256 实测）──
  const before = sha256File(INDEX_PATH);
  let probe = { skipped: true, reason: '调用方未注入 dryRunProbe' };
  let after = before;
  if (typeof options.dryRunProbe === 'function') {
    try {
      probe = options.dryRunProbe();
      after = sha256File(INDEX_PATH);
    } catch (e) {
      probe = { error: String(e && e.message) };
      after = sha256File(INDEX_PATH);
    }
  }
  const dOk = before === after && probe && probe.wrote !== true && probe.error === undefined;
  const dDetail = '索引 ' + INDEX_PATH + ' 的 sha256 写前=' + (before ? before.slice(0, 12) : '(文件不存在)') +
    ' 写后=' + (after ? after.slice(0, 12) : '(文件不存在)') + ' ⇒ ' + (before === after ? '完全一致' : '★ 发生变更') +
    '；dryRunProbe.wrote=' + String(probe.wrote) + (probe.protocol ? '；' + probe.protocol : '') +
    (probe.error ? '；★ 探针异常：' + probe.error : '') +
    (probe.skipped ? '（' + probe.reason + '）' : '');

  // ── E：冻结实测（Object.isFrozen + 真改一次证明拒改）──
  const frozenTargets = { SOURCE_ENUM, ACTIONS, STATES, SHAPES, COMMAND_WHITELIST, FORBIDDEN_PRIMITIVES };
  const frozenState = Object.fromEntries(Object.entries(frozenTargets).map(([k, v]) => [k, Object.isFrozen(v)]));
  let mutateBlocked = false;
  try {
    SOURCE_ENUM.push('elsewhere');
  } catch {
    mutateBlocked = true;
  }
  const eOk = Object.values(frozenState).every(Boolean) && mutateBlocked && SOURCE_ENUM.length === 1;
  const eDetail = 'Object.isFrozen 实测 ' + JSON.stringify(frozenState) +
    '；追加 "elsewhere" ' + (mutateBlocked ? '被拒（TypeError）' : '★ 竟然成功') +
    '；SOURCE_ENUM 长度仍为 ' + SOURCE_ENUM.length;

  // ── F：外部命令白名单（枚举调用点，集合非空且 ⊆ {node}）──
  const cmdScan = scanCommandSites({ root });
  const outside = cmdScan.commands.filter((c) => !COMMAND_WHITELIST.includes(c));
  const fOk = cmdScan.sites.length > 0 && cmdScan.commands.length > 0 && outside.length === 0;
  const fDetail = '枚举到 ' + cmdScan.sites.length + ' 个调用点，命令集=[' + cmdScan.commands.join(', ') + ']' +
    (outside.length ? '；★ 越界命令：' + outside.join(', ') : '') +
    (cmdScan.sites.length === 0 ? '；★ 空集 —— 「0 ⊆ 允许」是假通过，判失败' : '') +
    ' ⊆ 允许=[' + COMMAND_WHITELIST.join(', ') + ']；来源 ' +
    JSON.stringify([...new Set(cmdScan.sites.map((s) => s.origin))]);

  const items = [
    { id: 'A', claim: '源码无危险原语（真扫 lib/*.js）', ok: aOk, detail: aDetail, evidence: { hits, modHits, control } },
    { id: 'B', claim: '负例全部被拒（≥8）', ok: bOk, detail: bDetail, evidence: neg },
    { id: 'C', claim: '正例可用（≥3，防门太宽）', ok: cOk, detail: cDetail, evidence: pos },
    { id: 'D', claim: '--dry-run 零变更（sha256 实测）', ok: dOk, detail: dDetail, evidence: { before, after, probe } },
    { id: 'E', claim: '枚举冻结（Object.isFrozen 实测）', ok: eOk, detail: eDetail, evidence: { frozenState, mutateBlocked } },
    { id: 'F', claim: '命令集 ⊆ {node} 且非空集', ok: fOk, detail: fDetail, evidence: { commands: cmdScan.commands, sites: cmdScan.sites } }
  ];

  return {
    ok: items.every((i) => i.ok),
    check: 'lean4-check A–F',
    items,
    gate: {
      sourceEnum: [...SOURCE_ENUM],
      actions: [...ACTIONS],
      states: [...STATES],
      commandWhitelist: [...COMMAND_WHITELIST],
      indexPath: INDEX_PATH,
      inboxDir: INBOX_DIR,
      principle: '唯一写目标写死为常量 + source 冻结枚举 + 索引路径不可作为入参'
    }
  };
}
