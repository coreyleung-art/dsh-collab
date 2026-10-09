/**
 * gate.js — R006#10 结构门：约束前置 · 不可绕过（reflect-synthesize 版）
 * =============================================================================
 * 本工具唯一的「不该发生路径」是：
 *
 *   ★ 替用户改**哲学库 / 规则库**（RULES.md / governance-philosophy.json）
 *
 * 为什么这是死线：整条流水线的所有权归属是「AI 提议、**用户裁定**」——
 * 依 据 phi-user-sovereignty（决策权在用户：AI 可提议/分析/预警，执行需人类确认）与
 *       phi-027（能力与权限分离：能不能做 ≠ 该不该做）。
 * synthesize 的位置在 ⑤，是**提案生成器**；入册（⑦ reflect-enroll）才可能碰库，且那是用户在 ⑥ 裁定之后的事。
 * 一旦提炼环节能直接写库，规则库/哲学库就会被"当日反思的热度"自动改写 —— 且无人复核、无留痕。
 *
 * 约束不是「检查后放行」，而是**让那条路径在语法上不存在**：
 *
 *   1) **没有那个入口**：写目标来自**冻结**的 WRITE_SPEC（只有三个语义名：
 *      proposal-md / unified-log / selfcheck-state）。没有 `--out`、没有 `--apply`、
 *      没有 `--write-rules`、没有 `--enroll`（旗标来自冻结的 lib/options.js，
 *      B 项用**集合运算**证明这些名字一个都不存在）。
 *   2) **没有那个能力**：全包写调用**只**出现在 lib/out.js，且每个写调用先过 `guardWritePath()`：
 *      - 解析后的绝对路径不得含禁用词（RULES.md / governance-philosophy.json / rules.json /
 *        rules-registry / gallery / blueprint）；
 *      - 必须落在该 kind 的基目录内、不得多一级子目录、文件名必须匹配模板。
 *      `rules-registry/` 与 `data/blueprint/gallery/` **根本不在任何基目录之下**。
 *      全包**零 exec/spawn**：没有外部命令这条路（命令白名单 = 空集）。
 *   3) **有那个证明**：`--lean4-check` A–F（B 项写门负例含"写 RULES.md"、"写哲学库"、
 *      "../ 穿越到 rules-registry"、"伪造 kind registry"，F 项含扫描器正控 + 写出口收口）。
 *   4) **失败即停**：`guardWritePath` 抛 `GateError`；调用方拿不到路径，也就写不出去。
 *
 * 纵深防御（二级，非 ⑩ 主体）：输入侧同样**只认带证据的条目** ——
 *   harvested-<date>.json 是磁盘上的文件，可能被手改。
 *   `vetClusterMember()` 对每个 cluster member 重跑证据判定，缺证据者**丢弃并计数**，不进提案。
 *   依据同 harvest 的死线：无证据的条目不能被摆到用户面前让他据此裁定。
 */

/** 结构门拒绝时抛出的错误 */
export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/* ========================================================================== *
 * 冻结白名单
 * ========================================================================== */

/** 写目标语义名闭集（**唯一入口集合**；没有"自定义 kind"这个入口） */
export const ALLOWED_WRITE_TARGETS = Object.freeze(['proposal-md', 'unified-log', 'selfcheck-state']);

/** 绝不允许被本工具写入的路径/目录名（治理库；写入权在用户裁定后的 ⑦ reflect-enroll） */
export const FORBIDDEN_WRITE_TOKENS = Object.freeze([
  'RULES.md',
  'governance-philosophy.json',
  'rules.json',
  'rules-registry',
  'gallery',
  'blueprint'
]);

/**
 * 允许被本工具执行的外部命令（白名单）。
 * synthesize 是**纯文件读写工具**：不需要、也不得执行任何外部命令。
 * 空集是有意为之，并由 F 项（含扫描器正控）证明「是真空集，不是瞎了」。
 */
export const ALLOWED_COMMANDS = Object.freeze([]);

/** 对照现有库的判定闭集（R006 §2 ⑩「枚举」式约束：判定只能取这几个值） */
export const JUDGMENTS = Object.freeze([
  'already-application', // 已有规则/哲学**覆盖**了它，这条只是它的应用
  'extends-existing',    // 是已有条目的**延伸/补维**（如 Φ13 之于 phi-facts）
  'new-dimension',       // 现有条目**未覆盖**的新维度
  'conflicts',           // 与现有条目**冲突**（仅在显式冲突信号下机械判定）
  'unclear'              // ★ 规则判不了 → 必须显式标出，交人工/LLM 复核（不许强行归类）
]);

/** 分类归档闭集 */
export const CATEGORIES = Object.freeze([
  '拟新增哲学',
  '拟新增规则',
  '并入/补维',
  '转规范',
  '归档为案例',
  '需裁决冲突',
  '需人工复核'
]);

/** 证据硬性构成（与 harvest 同一条死线；此处用于输入侧纵深防御） */
export const EVIDENCE_RULE = Object.freeze({
  ts: 'non-empty-string',
  atLeastOne: Object.freeze(['cmd', 'output']),
  desc: 'evidence 必须含 ts + (cmd 或 output)'
});

/** 判定阈值（冻结；改它会改变判定结果分布，属版本级改动） */
export const JUDGE_RULE = Object.freeze({
  // ★ minMatch 是"这算一次真实的主题命中"的下限（共享字符 bigram 数）。
  //   为什么是 5：中文短句之间**总会有** 1-3 个偶然共享的 bigram（"的条"、"条目"、"必须"…）。
  //   实测（2026-09-10 fixtures）：两条完全无关的 lesson（一条讲"移动设备休眠"、一条讲"红绿灯互斥"）
  //   共享 2 个 bigram —— 若把 2 当"弱命中"，就会把噪音当成"已有条目覆盖"，进而阻塞真正的新维度。
  minMatch: 5,
  // decisive：最佳匹配要**明显领先**第二名，否则是多条目并列（→ unclear，交人定）
  decisiveFactor: 2,
  decisiveMin: 4,
  // already-application 还要求"该 lesson 大部分内容已被该条目覆盖"
  coverageMin: 0.6,
  noveltyMin: 4,      // 相对该条目的新增 bigram ≥4 → 确实带了新东西（补维而非重复）
  explicitConflict: '仅当 lesson/pit/detail 中出现「与 <已知条目 id> 冲突/矛盾/相悖/不一致/推翻/废止」这类**显式**信号才判 conflicts；工具不猜语义冲突'
});

/* ========================================================================== *
 * 输入侧纵深防御：只认带证据的条目
 * ========================================================================== */

const isNonEmptyString = (v) => typeof v === 'string' && v.trim() !== '';

/** 证据完整性（纯函数） */
export function evidenceCompleteness(ev) {
  const missing = [];
  if (ev === undefined || ev === null) return { ok: false, missing: ['evidence'], got: null };
  if (typeof ev !== 'object' || Array.isArray(ev)) return { ok: false, missing: ['evidence(必须是对象)'], got: null };
  if (!isNonEmptyString(ev.ts)) missing.push('evidence.ts');
  if (!EVIDENCE_RULE.atLeastOne.some((k) => isNonEmptyString(ev[k]))) missing.push('evidence.cmd|evidence.output');
  return { ok: missing.length === 0, missing, got: ev };
}

/**
 * 提案准入判定（纵深防御）：一个 cluster member 能不能被摆到用户面前。
 * 不通过 → 丢弃（并计数），**不进提案**。
 */
export function vetClusterMember(m) {
  if (!m || typeof m !== 'object') return { ok: false, reason: 'member 不是对象' };
  if (!isNonEmptyString(m.lesson)) return { ok: false, reason: 'lesson 缺失' };
  const evc = evidenceCompleteness(m.evidence);
  if (!evc.ok) return { ok: false, reason: `无证据（缺 ${evc.missing.join(' + ')}）` };
  return { ok: true };
}

/* ------------------- 输入侧证据门 负例 / 正例（供 --lean4-check 实测） ------------------- */

/** 负例：**必须全部被 vetClusterMember 拒绝**（无证据/缺 ts/缺 cmd+output/无 lesson/非对象） */
export function vetNegativeCases() {
  const base = { device: 'd', agent: 'a', item_id: 'R1', lesson: 'L' };
  const attempts = [
    { name: 'evidence 整个缺失', m: { ...base } },
    { name: 'evidence=null', m: { ...base, evidence: null } },
    { name: 'evidence=字符串', m: { ...base, evidence: 'ts=…' } },
    { name: 'evidence=数组', m: { ...base, evidence: ['t'] } },
    { name: 'evidence={} 空对象', m: { ...base, evidence: {} } },
    { name: '只有 ts，无 cmd/output', m: { ...base, evidence: { ts: '2026-09-10' } } },
    { name: '只有 cmd，无 ts', m: { ...base, evidence: { cmd: 'ls' } } },
    { name: 'ts 是空白串', m: { ...base, evidence: { ts: '  ', cmd: 'ls' } } },
    { name: 'lesson 缺失', m: { device: 'd', agent: 'a', item_id: 'R1', evidence: { ts: 't', cmd: 'c' } } },
    { name: 'member 不是对象', m: 'x' },
    { name: 'member=null', m: null }
  ];
  return attempts.map(({ name, m }) => {
    const v = vetClusterMember(m);
    return { input: name, code: v.ok ? null : 'NO_EVIDENCE' };
  });
}

/** 正例：合法 member 必须能进提案（防「门太宽把正常输入也砍了」） */
export function vetPositiveCases() {
  const base = { device: 'mac-mini', agent: 'a', item_id: 'R1', lesson: 'L' };
  const cases = [
    { name: 'ts + cmd', m: { ...base, evidence: { ts: '2026-09-10T00:00:00Z', cmd: 'ls' } } },
    { name: 'ts + output', m: { ...base, evidence: { ts: '2026-09-10T00:00:00Z', output: 'ok' } } },
    { name: 'ts + collected_at + cmd', m: { ...base, evidence: { ts: 't', collected_at: 'c', cmd: 'ls' } } }
  ];
  return cases.map(({ name, m }) => {
    const v = vetClusterMember(m);
    return { input: name, ok: v.ok, reason: v.reason || null };
  });
}

/* ========================================================================== *
 * 源码结构扫描（去字面量 + 回原文读实参）—— 与 harvest 同源实现
 * ========================================================================== */

/** 去注释 / 字符串 / 模板 / 正则字面量（**保持等长**，偏移可对齐原文） */
export function stripLiterals(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  const pushBlank = (s) => { for (const ch of s) out += (ch === '\n' ? '\n' : ' '); };
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (c === '/' && d === '/') { let j = i; while (j < n && src[j] !== '\n') j++; pushBlank(src.slice(i, j)); i = j; continue; }
    if (c === '/' && d === '*') { let j = src.indexOf('*/', i + 2); j = j < 0 ? n : j + 2; pushBlank(src.slice(i, j)); i = j; continue; }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === c) { j++; break; } j++; }
      pushBlank(src.slice(i, j)); i = j; continue;
    }
    if (c === '/') {
      const lineEnd = src.indexOf('\n', i); const stop = lineEnd < 0 ? n : lineEnd;
      const prev = out.replace(/\s+$/, '').slice(-1);
      const regexPos = prev === '' || '(,=:[!&|?{};'.includes(prev);
      if (regexPos) {
        let j = i + 1, closed = false;
        while (j < stop) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === '/') { closed = true; j++; break; } j++; }
        if (closed) { pushBlank(src.slice(i, j)); i = j; continue; }
      }
    }
    out += c; i++;
  }
  return out;
}

/**
 * 负向后顾只排除 `[\w$]`（**不排除 `.`**）。
 * 血泪（harvest 开发中实测，R006 §6 坑#3）：写成 `(?<![\w.$])` 时，
 * `fs.writeFileSync(` 因前缀是 `.` 而被**全部漏掉** → 枚举 0 个 → 「0 个越界写」空洞通过。
 */
const EXEC_CALL_RE = /(?<![\w$])(pExecFile|execFileSync|execFile|execSync|exec|spawnSync|spawn|fork)\s*\(/g;
const WRITE_CALL_RE = /(?<![\w$])(writeFileSync|appendFileSync|writeFile|createWriteStream|copyFileSync|copyFile|renameSync|rename|unlinkSync|unlink|rmSync|rm|rmdirSync|rmdir)\s*\(/g;

/**
 * ★ 已知良性接收者（显式枚举 + **结果照样上报**，不静默丢弃）。
 * 扫描器会把**自己的检测代码** `re.exec(code)` 当成外部命令执行点（R006 §6 坑#2）。
 * 两种错修都要避免：收紧正则（会顺手关掉 `cp.exec` 这个真漏洞）／静默 filter（变成看不见的豁免）。
 * 本实现：照常枚举，识别接收者，标 `benign:true` 并计数上报。
 */
export const BENIGN_EXEC_RECEIVERS = Object.freeze(['re', 'regex', 'regexp', 'matcher', 'reg']);

/** 枚举外部命令执行点（去字面量定位 → 回原文读第一个实参 + 识别接收者） */
export function scanExecSites({ sources }) {
  const sites = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    const re = new RegExp(EXEC_CALL_RE.source, 'g');
    while ((m = re.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      const recv = code.slice(0, m.index).match(/([\w$]+)\s*\.\s*$/);
      const receiver = recv ? recv[1] : null;
      const benign = receiver !== null && BENIGN_EXEC_RECEIVERS.includes(receiver.toLowerCase());
      sites.push({ file, line, callee: m[1], receiver, benign, cmd: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/** 枚举写副作用调用点（同上：去字面量定位 → 回原文读实参 + 整行原文） */
export function scanWriteSites({ sources }) {
  const sites = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    const rawLines = raw.split('\n');
    let m;
    const re = new RegExp(WRITE_CALL_RE.source, 'g');
    while ((m = re.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: m[1], arg: lit ? lit[1] : null, literal: !!lit, sourceLine: (rawLines[line - 1] || '').trim() });
    }
  }
  return sites;
}

/**
 * ★ 扫描器正控（防 R006 §6 坑#3「空洞通过」）。
 * 喂一条**明知含危险调用**的合成源码，扫描器必须命中；命中 0 = 扫描器瞎了 → 门失效。
 * 同时断言「良性接收者被正确识别」**且**「真调用仍被枚举到」——防"把真漏洞一起关掉"。
 */
export function scannerSelfTest() {
  const probe = [
    "import { execFile } from 'node:child_process';",
    "const pExecFile = promisify(execFile);",
    "await pExecFile('rm', ['-rf', '/tmp/x']);",
    "const cp = require('node:child_process');",
    "cp.exec('curl http://evil');",
    "const m = re.exec(code);            // 良性：接收者是 RegExp",
    "fs.writeFileSync('/tmp/RULES.md', 'x');"
  ].join('\n');
  const src = { '__probe__.js': probe };
  const exec = scanExecSites({ sources: src });
  const write = scanWriteSites({ sources: src });
  const real = exec.filter((s) => !s.benign);
  const benign = exec.filter((s) => s.benign);
  const execOk = real.length === 2 && real.some((s) => s.cmd === 'rm') && real.some((s) => s.cmd === 'curl http://evil') &&
                 benign.length === 1 && benign[0].receiver === 're';
  const writeOk = write.length === 1 && write[0].literal === true && String(write[0].arg).includes('RULES.md');
  return {
    ok: execOk && writeOk,
    exec, write,
    detail: `正控: 真 exec 调用点 ${real.length}（期望 2：pExecFile('rm') + cp.exec('curl …')）· 良性接收者 ${benign.length}（期望 1：re.exec）· write ${write.length}（期望 1，arg=${write[0] ? write[0].arg : 'null'}）`
  };
}

export const GATE_META = Object.freeze({
  allowedWriteTargets: ALLOWED_WRITE_TARGETS,
  forbiddenWriteTokens: FORBIDDEN_WRITE_TOKENS,
  allowedCommands: ALLOWED_COMMANDS,
  judgments: JUDGMENTS,
  categories: CATEGORIES,
  judgeRule: JUDGE_RULE,
  principle: '本工具**没有**写 RULES.md / governance-philosophy.json 的能力（源码扫描证明无该路径）',
  philosophy: 'phi-user-sovereignty + phi-027（能力权限分离 · 人类开关锁）'
});
