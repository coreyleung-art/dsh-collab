/**
 * lib/gate.js — ⑩ 约束前置 · 不可绕过（Lean4 逻辑门）
 *
 * 本工具「不该发生的路径」（每一条都是 2026-10-01 实测踩过的）：
 *   P1 把「套件崩溃」判成「变异被捕获」或「变异存活」—— 崩溃不是结论
 *   P2 把「变异体自身无效（语法错/绑定数错）」判成「存活」—— 无效变异体不构成证据
 *   P3 对**根本没执行**的断言报 PASS
 *   P4 修改被测源文件本身（审计器必须只读被测源）
 *   P5 向被测目录或任意路径写入（污染被审对象）
 *   P6 用宽杀 / 任意命令执行达成目的
 *
 * 四道结构封堵：
 *   ① 入口门：判定值只能是 VERDICT 闭集成员；**闭集里没有「PASS」这类可被崩溃冒充的值**
 *   ② 类型锁：出站命令是冻结白名单 [python3, node]，且以 shell:false + 数组实参调用
 *   ③ 唯一写入点：全仓库仅一处 fs 写入，且必须先过 assertTmpContained()
 *   ④ 失败即停：门不通过 → 抛 GateError → cli 返回 1，不降级为警告
 */

import path from 'node:path';

export class GateError extends Error {
  constructor(code, message) {
    super(`[${code}] ${message}`);
    this.name = 'GateError';
    this.code = code;
  }
}

/** ★ 判定闭集：故意【不含】PASS/OK/SUCCESS —— 崩溃无处可去，只能落到 INCONCLUSIVE */
export const VERDICT = Object.freeze({
  CAUGHT: 'CAUGHT',
  SURVIVED: 'SURVIVED',
  INCONCLUSIVE: 'INCONCLUSIVE',
});
export const VERDICT_VALUES = Object.freeze(Object.keys(VERDICT));

/** 出站命令白名单（冻结）
 *  · python3 / node —— 执行被测套件（assert-audit 模式）
 *  · ps / launchctl  —— 只读盘点（scope 模式：进程与服务清单）
 * ※ 严禁在本工具内调用任何**可变**子命令。launchctl 的可变子命令在下方 DENIED_SUBCOMMANDS 冻结，
 *   并由 G 项（源码扫描）断言其不出现——2026-10-01 我本人在会话里手跑过 `launchctl bootstrap`，
 *   那是一次**用户可见的显式动作**，不该被工具默默获得。 */
export const ALLOWED_COMMANDS = Object.freeze(['python3', 'node', 'ps', 'launchctl']);

/** 冻结的禁用子命令：这些一旦出现在源码里即判红（门不通过） */
export const DENIED_SUBCOMMANDS = Object.freeze([
  'bootstrap', 'bootout', 'enable', 'disable', 'kickstart',
  'load', 'unload', 'submit', 'remove', 'start', 'stop', 'restart',
]);

/** 危险原语（扫描前必须 stripLiterals） */
const BROAD_KILL_CALLS = Object.freeze([
  'killall', 'pkill', 'kill -9', 'process.kill(', 'taskkill',
]);
const SHELL_TRUE = Object.freeze(['shell: true', 'shell:true', '{ shell: true }']);

/** 唯一的写入原语名（全仓库只允许出现在这一处） */
const WRITE_PRIMITIVES = Object.freeze([
  'writeFileSync(', 'writeFile(', 'appendFileSync(', 'createWriteStream(',
  'rmSync(', 'unlinkSync(', 'mkdirSync(',
]);

/**
 * 剥掉注释 / 字符串 / 正则字面量（坑 #2：不剥就会把自己的检测正则当靶子 = 假阳性）。
 * 只用于「扫危险原语」；定位调用点后必须回原文读实参（坑 #3）。
 */
export function stripLiterals(src) {
  return String(src)
    .replace(/\/\*[\s\S]*?\*\//g, ' ')      // 块注释
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1 ')  // 行注释（避开 http://）
    .replace(/`(?:\\.|[^`\\])*`/g, '``')     // 模板串
    .replace(/'(?:\\.|[^'\\])*'/g, "''")     // 单引串
    .replace(/"(?:\\.|[^"\\])*"/g, '""');    // 双引串
}

/** A 项支撑：源码无危险原语 */
export function scanDangerous({ sources }) {
  const hits = [];
  for (const [name, raw] of Object.entries(sources)) {
    const scan = stripLiterals(raw);
    for (const tok of [...BROAD_KILL_CALLS, ...SHELL_TRUE]) {
      if (scan.includes(tok)) hits.push({ file: name, token: tok });
    }
  }
  return hits;
}

/**
 * ③ 唯一写入点：统计写入原语出现处。
 * 返回 {sites:[{file,line,primitive}], count}
 */
export function scanWriteSites({ sources }) {
  const sites = [];
  for (const [name, raw] of Object.entries(sources)) {
    const lines = raw.split('\n');
    lines.forEach((ln, i) => {
      const scan = stripLiterals(ln);
      for (const p of WRITE_PRIMITIVES) {
        if (scan.includes(p)) sites.push({ file: name, line: i + 1, primitive: p });
      }
    });
  }
  return { sites, count: sites.length };
}

/**
 * F 项支撑：枚举出站调用点并**回原文读实参**。
 * ★ 坑 #3「空洞通过」的封堵：剥字面量后若读不到实参，**不得**当作「0 ⊆ 允许」通过，
 *   必须标为 UNRESOLVED 并在 F 项判红。三种解析结果分开报：
 *     literal           —— 首参是字面量，直接比白名单
 *     variable-guarded  —— 首参是变量，但同一行或前 3 行内出现过 assertCommand(...)
 *     UNRESOLVED        —— 读不到且找不到门 ⇒ 判红
 */
export function scanExecSites({ sources }) {
  const out = [];
  for (const [name, raw] of Object.entries(sources)) {
    const lines = raw.split('\n');
    lines.forEach((ln, i) => {
      const scan = stripLiterals(ln);
      if (!/(execFileSync|spawnSync|execFile|spawn)\s*\(/.test(scan)) return;
      const original = lines[i];
      const lit = original.match(/\(\s*(['"`])([^'"`]+)\1/);
      let command = null; let resolved = 'UNRESOLVED';
      if (lit) {
        command = lit[2];
        resolved = 'literal';
      } else {
        const window = lines.slice(Math.max(0, i - 3), i + 1).join('\n');
        if (/assertCommand\s*\(/.test(stripLiterals(window))) resolved = 'variable-guarded';
      }
      out.push({ file: name, line: i + 1, command, resolved, argsRaw: original.trim().slice(0, 160) });
    });
  }
  return out;
}

/**
 * ③ 唯一受控入口：只有它允许写。任何越出 os.tmpdir() 的目标直接拒绝。
 * ★ 2026-10-01 修正：初版用字符串 startsWith 判定，**被 /tmp/../etc/hosts 穿过**
 *   （以 /tmp/ 开头 ⇒ 假通过）。现改为 path.resolve 后比较，穿越在解析期即被消解。
 * @param {string} p 目标绝对路径
 * @param {string} tmpRoot os.tmpdir()
 */
export function assertTmpContained(p, tmpRoot) {
  if (typeof p !== 'string' || p.length === 0) {
    throw new GateError('WRITE_OUTSIDE_TMP', `写入目标非法（须为非空字符串）：${JSON.stringify(p)}`);
  }
  const root = path.resolve(tmpRoot) + path.sep;
  const abs = path.resolve(p);                 // ★ 先消解 . 与 ..
  if (abs !== path.resolve(tmpRoot) && !abs.startsWith(root)) {
    throw new GateError('WRITE_OUTSIDE_TMP',
      `写入目标不在临时目录内，拒绝：${p}（解析后 ${abs}；允许前缀 ${root}）`);
  }
  return true;
}

/** 判定值必须是闭集成员（防「凭空造一个 PASS」） */
export function assertVerdict(v) {
  if (!VERDICT_VALUES.includes(v)) {
    throw new GateError('BAD_VERDICT', `判定值不在冻结闭集内：${JSON.stringify(v)}`);
  }
  return v;
}

/** B 项：负例全部被拒 */
export function gateNegativeCases() {
  const attempts = [
    ['assertTmpContained', '/etc/passwd', '绝对路径越界'],
    ['assertTmpContained', '/Users/coreyleung/.dsh/agent-bus.json', '写被测域'],
    ['assertTmpContained', '/tmp/../etc/hosts', '路径穿越'],
    ['assertTmpContained', '', '空值'],
    ['assertTmpContained', null, '非字符串'],
    ['assertTmpContained', undefined, '未定义'],
    ['assertVerdict', 'PASS', '闭集外的判定值（PASS 不允许存在）'],
    ['assertVerdict', 'OK', '闭集外的判定值'],
    ['assertVerdict', '', '空判定'],
    ['assertVerdict', null, '空判定'],
    ['assertCommand', 'bash', '白名单外命令'],
    ['assertCommand', 'sh', '白名单外命令'],
    ['assertCommand', 'rm', '白名单外命令'],
    ['assertCommand', '/bin/rm', '带路径的白名单外命令'],
    ['assertCommand', '', '空命令'],
    ['assertCommand', 'python3; rm -rf /', '命令拼接'],
    ['assertCommand', 'python3 && curl x', '命令串联'],
    ['assertCommand', null, '非字符串'],
  ];
  const results = [];
  for (const [fn, arg, why] of attempts) {
    let rejected = false; let code = null;
    try {
      if (fn === 'assertTmpContained') assertTmpContained(arg, '/tmp/');
      else if (fn === 'assertVerdict') assertVerdict(arg);
      else assertCommand(arg);
    } catch (e) {
      rejected = e instanceof GateError; code = e.code;
    }
    results.push({ fn, arg: String(arg), why, rejected, code });
  }
  return results;
}

/** C 项：正例必须可用（防「门太宽把自己人也拦了」） */
export function gatePositiveCases() {
  const cases = [];
  try { assertTmpContained('/tmp/assert-audit-x/mutant.py', '/tmp/'); cases.push({ case: 'tmp 内写入', ok: true }); }
  catch (e) { cases.push({ case: 'tmp 内写入', ok: false, err: String(e) }); }
  try { assertVerdict(VERDICT.CAUGHT); cases.push({ case: 'CAUGHT 合法', ok: true }); }
  catch (e) { cases.push({ case: 'CAUGHT 合法', ok: false, err: String(e) }); }
  try { assertVerdict(VERDICT.INCONCLUSIVE); cases.push({ case: 'INCONCLUSIVE 合法', ok: true }); }
  catch (e) { cases.push({ case: 'INCONCLUSIVE 合法', ok: false, err: String(e) }); }
  try { assertCommand('python3'); cases.push({ case: 'python3 合法', ok: true }); }
  catch (e) { cases.push({ case: 'python3 合法', ok: false, err: String(e) }); }
  try { assertCommand('node'); cases.push({ case: 'node 合法', ok: true }); }
  catch (e) { cases.push({ case: 'node 合法', ok: false, err: String(e) }); }
  return cases;
}

/** 出站命令门：必须是白名单冻结集的精确成员（不做前缀匹配，防 /bin/rm 类绕过） */
export function assertCommand(cmd) {
  if (typeof cmd !== 'string' || !ALLOWED_COMMANDS.includes(cmd)) {
    throw new GateError('COMMAND_NOT_ALLOWED',
      `命令不在白名单内：${JSON.stringify(cmd)}（允许：${ALLOWED_COMMANDS.join(', ')}）`);
  }
  return cmd;
}

export const GATE_META = Object.freeze({
  version: '1.0.0',
  gateTypes: Object.freeze(['入口门', '类型锁', '唯一写入点', '失败即停']),
  forbiddenPaths: Object.freeze([
    'P1 崩溃被当作结论',
    'P2 无效变异体被当作存活',
    'P3 未执行的断言报 PASS',
    'P4 修改被测源',
    'P5 越出 tmpdir 写入',
    'P6 宽杀 / 任意命令执行',
  ]),
});
