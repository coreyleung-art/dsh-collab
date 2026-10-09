/**
 * gate.js — R006#10 结构门：约束前置 · 不可绕过（reflect-harvest 版）
 * =============================================================================
 * 本工具唯一的「不该发生路径」是：
 *
 *   ★ 把**无证据的条目**当成有效条目混进汇总（harvested-<date>.json 的 valid 集合）
 *
 * 为什么它是死线：下游 synthesize → 用户裁定 → 入册（RULES.md / 哲学库）
 * 全部建立在「cluster 里的每一条都有证据」之上。一旦无证据条目混进 valid：
 *   - 复现计数（recurrence）被虚高 → 排序失真 → 飞轮按噪音加速；
 *   - 用户按提案入册，而入册依据根本不存在 → 污染规则库/哲学库；
 *   - 且**事后无法察觉**——输出里看不出哪条是编的。
 *
 * 因此约束不是「检查后放行」，而是**让那条路径在语法上不存在**：
 *
 *   1) **没有那个入口**：条目进入 valid 集合的唯一通道是 `mintAdmitted()`，
 *      它内部调用 `adjudicate()`；判定不通过即返回 `null`。
 *      `buildValidSet()` 只接受**带品牌（Symbol）的**条目，裸对象一律抛 `GateError`。
 *      本模块**不导出**任何 `admitUnchecked` / `skipEvidence` / `force` / `lenient`；
 *      CLI 与工具 schema 同样**没有**这些旗标（--lean4-check 的 B 项会扫描源码证明）。
 *   2) **没有那个能力**：本模块（及整个包）**不执行任何外部命令**（无 exec/spawn/eval），
 *      也不写任何治理库（RULES.md / governance-philosophy.json）。
 *   3) **有那个证明**：`--lean4-check` 跑 A–F 六项，其中：
 *      - B 用去重后的负例矩阵实测「无证据/缺 ts/缺 cmd+output/证据非对象」全部被拒；
 *      - F 证明命令集为空**且**扫描器本身有正控（喂一条含 execFile 的合成源码，
 *        扫描器必须命中——否则是「空洞通过」，见 R006 §6 坑#3）。
 *   4) **失败即停**：`adjudicate` 不通过 → 条目进 `rejected`（带原因），
 *      `mintAdmitted` 返回 null → 永远进不了 valid；没有任何「警告后继续」的分支。
 *
 * 依 据：R006 v3.0 §2 ⑩ + §4（四种门型 / 六项自证）+ §6（7 条坑）
 * 对应哲学：phi-constraint-frontloaded（约束前置·不可绕过）、phi-truth（无验证的成功=未成功）
 */

/** 结构门拒绝时抛出的错误（带稳定 code，供 CLI 与 --lean4-check 判定） */
export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/* ========================================================================== *
 * 冻结白名单（门型：类型锁 + Schema 门）
 * ========================================================================== */

/** suggestion.type 只允许四选一（其余一律 invalid_type） */
export const SUGGESTION_TYPES = Object.freeze(['新增', '修订', '转规范', '无需动作']);

/** 条目级拒收原因闭集（防止下游拿到不可枚举的 reason 字符串） */
export const ITEM_REJECT_REASONS = Object.freeze([
  'invalid_evidence', // ★ 质量门：无证据
  'incomplete',       // 必填字段缺失
  'invalid_type'      // suggestion.type 非法
]);

/** 文件级拒收原因闭集 */
export const FILE_REJECT_REASONS = Object.freeze([
  'invalid_decline',  // declined:true 但未给理由
  'invalid_shape'     // 根本不是一份回填（非对象 / items 非数组）
]);

/** 全部拒收原因（摘要统计用；冻结） */
export const ALL_REJECT_REASONS = Object.freeze([
  ...ITEM_REJECT_REASONS,
  ...FILE_REJECT_REASONS
]);

/** 合法 flags（不拒收，只在 valid 条目上打标） */
export const ITEM_FLAGS = Object.freeze([
  'unknown_rule',              // related_rule 指向不存在的条目
  'cluster_duplicate',         // 与其它条目同簇
  'evidence_no_collected_at'   // ★ evidence.ts 是"对象时刻"，但缺"采集时刻"（collected_at）——只标注，不拒收
]);

/**
 * ★ 同步盘污染判定规则（冻结；跨设备层专用）。
 * 判据（两条都满足才判）：
 *   ① `lesson` **逐字相同**（trim 后严格相等）
 *   ② 跨 ≥2 设备，且 `evidence.ts` 时点接近（|Δt| ≤ windowMs）
 * 为什么只认"逐字相同"：**不同设备上的智能体独立反思，不可能写出逐字一样的句子**；
 * 逐字一样 = 同一份文件被同步盘复制（或人肉复制粘贴），**不是独立复现**。
 * 命中者仍然可见（`sync_duplicate_members`），但**不重复计入 recurrence** ——
 * 否则跨设备信号会被"同一份文件的两份副本"伪造。
 */
export const SYNC_DUP_RULE = Object.freeze({
  windowMs: 24 * 60 * 60 * 1000,
  requireByteIdenticalLesson: true,
  requireCrossDevice: true,
  note: '逐字相同 + 跨设备 + 时点接近(<24h) → 判 possible_sync_duplicate，不重复计入 recurrence'
});

/** 证据的硬性构成：必须 ts（非空字符串）+（cmd 或 output 至少一个非空） */
export const EVIDENCE_RULE = Object.freeze({
  ts: Object.freeze({ type: 'string', required: true, desc: '证据采集时点（Φ13：断言必须带时点）' }),
  atLeastOne: Object.freeze(['cmd', 'output']),
  desc: 'evidence 必须含 ts + (cmd 或 output)；缺任一项 → invalid_evidence（结构上无法进入 valid）'
});

/** related_rule 的「无」写法（视为无引用，不做 unknown_rule 判定） */
export const NONE_REFS = Object.freeze(['', '无', 'none', 'n/a', 'na', '-', '—', 'null', 'undefined']);

/**
 * 允许被本工具执行的外部命令（白名单）。
 * harvest 是**纯文件读写工具**：它不需要、也不得执行任何外部命令。
 * 空集是有意为之，并由 --lean4-check 的 F 项（含扫描器正控）证明「是真空集，不是瞎了」。
 */
export const ALLOWED_COMMANDS = Object.freeze([]);

/** 允许发生写副作用的文件（语义名，非路径；实际路径由 lib/out.js 解析并过 guardWritePath） */
export const ALLOWED_WRITE_TARGETS = Object.freeze(['harvested-json', 'unified-log', 'selfcheck-state']);

/** 绝不允许被本工具写入的路径（治理库 —— 写入权在用户/reflect-enroll，不在 harvest） */
export const FORBIDDEN_WRITE_TOKENS = Object.freeze([
  'RULES.md',
  'governance-philosophy.json',
  'rules.json',
  'gallery',
  'philosophy'
]);

/* ========================================================================== *
 * 证据完整性判定（纯函数，无副作用）
 * ========================================================================== */

const isNonEmptyString = (v) => typeof v === 'string' && v.trim() !== '';

/**
 * 证据完整性：evidence 必须是对象，且含非空 ts +（非空 cmd 或 非空 output）。
 * @returns {{ok:boolean, missing:string[], got:object|null}}
 */
export function evidenceCompleteness(ev) {
  const missing = [];
  if (ev === undefined || ev === null) return { ok: false, missing: ['evidence'], got: null };
  if (typeof ev !== 'object' || Array.isArray(ev)) return { ok: false, missing: ['evidence(必须是对象)'], got: null };
  if (!isNonEmptyString(ev.ts)) missing.push('evidence.ts');
  const oneOf = EVIDENCE_RULE.atLeastOne.some((k) => isNonEmptyString(ev[k]));
  if (!oneOf) missing.push('evidence.cmd|evidence.output');
  return { ok: missing.length === 0, missing, got: ev };
}

/** 仅证据门（供 lean4-check / 单测直接调用） */
export function admitEvidence(ev) {
  const c = evidenceCompleteness(ev);
  return c.ok ? { ok: true, evidence: c.got } : { ok: false, reason: 'invalid_evidence', missing: c.missing };
}

/* ========================================================================== *
 * 条目裁定（唯一分类器）
 * ========================================================================== */

/**
 * 裁定单个条目。
 *
 * 判定**优先级**（同时收集全部 issues；主 reason 取优先级最高者）：
 *   incomplete > invalid_type > invalid_evidence
 * 理由：结构缺失（连字段都没有）比内容非法更前置；而只要证据不通过，无论其它字段多完整，
 * 都**不可能**进入 valid —— 这是质量门的死线。
 *
 * @param {{agent:string, item:object, catalogs?:{rules?:Set<string>, phis?:Set<string>}}} entry
 * @returns {{ok:boolean, reason:string|null, reasons:string[], flags:string[], issues:string[]}}
 */
export function adjudicate(entry = {}) {
  const item = entry.item;
  const reasons = [];
  const issues = [];
  const flags = [];

  if (item === null || typeof item !== 'object' || Array.isArray(item)) {
    return { ok: false, reason: 'incomplete', reasons: ['incomplete'], flags, issues: ['item 不是对象'] };
  }

  // ── 1) 必填字段缺失 → incomplete
  const pitOk = isNonEmptyString(item.pit);
  const lessonOk = isNonEmptyString(item.lesson);
  const sugg = item.suggestion;
  const suggOk = sugg !== null && typeof sugg === 'object' && !Array.isArray(sugg);
  if (!pitOk) issues.push('pit 缺失或为空');
  if (!lessonOk) issues.push('lesson 缺失或为空');
  if (!suggOk) issues.push('suggestion 缺失或不是对象');
  else if (!isNonEmptyString(sugg.type)) issues.push('suggestion.type 缺失或为空');
  if (issues.length) reasons.push('incomplete');
  // 字段都缺时无法继续判 type/evidence，直接返回（但类型/证据判定也不会因此放行）
  const fieldIssues = issues.slice();

  // ── 2) suggestion.type 合法性 → invalid_type
  if (suggOk && isNonEmptyString(sugg.type) && !SUGGESTION_TYPES.includes(sugg.type)) {
    issues.push(`suggestion.type='${sugg.type}' 不在四选一 [${SUGGESTION_TYPES.join('/')}]`);
    reasons.push('invalid_type');
  }

  // ── 3) ★ 证据完整性 → invalid_evidence（死线）
  const evc = evidenceCompleteness(item.evidence);
  if (!evc.ok) {
    issues.push(`证据不完整，缺: ${evc.missing.join(' + ')}`);
    reasons.push('invalid_evidence');
  }

  // ── 4) flags（不拒收）
  // ★ 证据时点：Φ13 要求"断言带时点"。evidence.ts 通常是**对象/事件时刻**；
  //   采集时刻应是独立字段 collected_at。只有对象时刻而无采集时刻 → 标注（不拒收）。
  //   为什么只标注不拒收：现有回填格式里没有这个字段，拒收会让全流水线当天停摆；
  //   标注则把"该补的字段"变成可见的分布（各设备补齐后标记自然消失）。
  if (evc.ok && evc.got && !isNonEmptyString(evc.got.collected_at)) {
    flags.push('evidence_no_collected_at');
    issues.push('evidence 缺 collected_at（只有对象时刻 ts，没有采集时刻）—— 依 Φ13 建议补齐；各设备时钟不同步时尤其重要');
  }
  if (entry.catalogs && isNonEmptyString(item.related_rule)) {
    const refs = String(item.related_rule).split(/[\/,、;；\s]+/).map((s) => s.trim()).filter(Boolean);
    for (const ref of refs) {
      if (NONE_REFS.includes(ref.toLowerCase()) || NONE_REFS.includes(ref)) continue;
      const known = (entry.catalogs.rules && entry.catalogs.rules.has(ref)) ||
                    (entry.catalogs.phis && entry.catalogs.phis.has(ref));
      if (!known) { flags.push('unknown_rule'); issues.push(`related_rule '${ref}' 在 RULES.md / governance-philosophy.json 中不存在`); break; }
    }
  }

  // 主 reason 按优先级取（incomplete > invalid_type > invalid_evidence）
  const order = ['incomplete', 'invalid_type', 'invalid_evidence'];
  const primary = order.find((r) => reasons.includes(r)) || null;
  const uniqReasons = [...new Set(reasons)];
  const uniqFlags = [...new Set(flags)];

  return {
    ok: primary === null,
    reason: primary,
    reasons: uniqReasons,
    flags: uniqFlags,
    issues: [...new Set(issues)],
    fieldIssues
  };
}

/* ========================================================================== *
 * ★ 品牌机制：无证据条目在「类型层」进不了 valid 集合
 * ========================================================================== */

/** 品牌符号：**不导出**。外部无法伪造带品牌的条目。 */
const ADMITTED = Symbol('reflect.harvest.admitted');

/** 唯一把条目变成「可入 valid 集合」的工厂；判定不通过 → 返回 null（不是抛错后继续） */
export function mintAdmitted(entry) {
  const v = adjudicate(entry);
  if (!v.ok) return null;
  return Object.freeze({
    device: entry.device ?? null,
    agent: entry.agent,
    item_id: entry.item_id,
    file: entry.file ?? null,
    item: entry.item,
    submitted_at: entry.submitted_at ?? null,
    plugin_version: entry.plugin_version ?? null,
    flags: Object.freeze(v.flags.slice()),
    [ADMITTED]: true
  });
}

/** 品牌校验 */
export function isAdmitted(x) {
  return !!x && typeof x === 'object' && x[ADMITTED] === true;
}

/**
 * 构建 valid 集合：**唯一的 push 点**。
 * 未带品牌的条目（含任何"绕过 mintAdmitted 直接拼出来的"对象）→ 抛 GateError。
 * 没有任何参数/开关可以跳过这一判定。
 */
export function buildValidSet(entries) {
  const out = [];
  for (const e of entries) {
    if (!isAdmitted(e)) {
      throw new GateError('UNBRANDED_ENTRY',
        '拒绝：试图把未经 mintAdmitted() 品牌化的条目放进 valid 集合。' +
        '本工具**没有**跳过证据门的入口——凡是没走证据门的东西，在类型层就进不来。');
    }
    out.push(e);
  }
  return Object.freeze(out);
}

/* ========================================================================== *
 * 源码结构扫描（去字面量 + 回原文读实参）
 * ========================================================================== */

/**
 * 去注释 / 字符串 / 模板 / 正则字面量（**保持等长**，行号与偏移可对齐原文）。
 * 为什么必须去掉：R006 §6 坑#2 —— 直接扫原文会把检查器自己的检测正则与帮助文本当靶子（假阳性）。
 */
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

const EXEC_CALL_RE = /(?<![\w$])(pExecFile|execFileSync|execFile|execSync|exec|spawnSync|spawn|fork)\s*\(/g;

/**
 * ★ 已知良性接收者（**显式枚举 + 结果照样上报**，不静默丢弃）。
 *
 * 开发中实测（本工具的 F 项第一次跑就红）：扫描器把**自己的检测代码** `re.exec(code)` 当成了外部命令执行点
 * —— 这正是 R006 §6 坑#2「扫描器误伤自己」。两种错修都要避免：
 *   ✗ 把正则收紧成 `(?<![\w$.])exec` → `cp.exec('ls')` 也一起漏掉（真漏洞被顺手关掉了）；
 *   ✗ 直接 filter 掉不报告 → 又变成"看不见的豁免"。
 * 本实现：照常枚举出 `obj.exec(`，把接收者识别出来，标 `benign:true` 并**在图示里计数**，
 * 只有非良性的调用点才需要满足命令白名单。谁被豁免、豁免了几次，--lean4-check 的输出里看得见。
 */
export const BENIGN_EXEC_RECEIVERS = Object.freeze(['re', 'regex', 'regexp', 'matcher', 'reg']);

/**
 * 枚举外部命令执行点（去字面量定位 → 回原文读第一个实参 + 识别接收者）。
 * R006 §6 坑#3：只去字面量会导致读不到实参 → 枚举 0 个 → "0 ⊆ 允许" 空洞通过。
 * 本实现按**同一偏移**回原文读实参，因此 `literal:false` 会被显式暴露而不是静默消失。
 */
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
      // 接收者：紧邻调用点之前的 `<ident>.`（如 `re.exec(` 的 `re`）
      const recv = code.slice(0, m.index).match(/([\w$]+)\s*\.\s*$/);
      const receiver = recv ? recv[1] : null;
      const benign = receiver !== null && BENIGN_EXEC_RECEIVERS.includes(receiver.toLowerCase());
      sites.push({ file, line, callee: m[1], receiver, benign, cmd: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

const WRITE_CALL_RE = /(?<![\w$])(writeFileSync|appendFileSync|writeFile|createWriteStream|copyFileSync|copyFile|renameSync|rename|unlinkSync|unlink|rmSync|rm|rmdirSync|rmdir)\s*\(/g;

/** 枚举写副作用调用点（同上方法：去字面量定位 → 回原文读实参 + 整行原文） */
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
 * 血泪（本工具开发中实测）：初版正则写成 `(?<![\w.$])`（把 `.` 也排除），
 * 结果 `fs.writeFileSync(` 因为前缀是 `.` 而**全部漏掉** → 写调用点枚举为 0 →
 * 「0 个越界写」空洞通过。正控当场抓到：喂进去的 `fs.writeFileSync('/tmp/RULES.md')` 命中 0。
 * 修法：负向后顾只排除标识符字符 `[\w$]`（`pExecFile` 里的 `execFile` 仍不会误匹配，
 * 因为前缀 `p` 是 `\w`），从而 `fs.writeFileSync(` / `cp.exec(` 这类方法调用**必定被枚举到**。
 * 喂一条**明知含危险调用**的合成源码，扫描器必须命中。
 * 命中 0 条 = 扫描器瞎了（或去字面量剥过头）→ 后续「空集通过」毫无意义 → 门失效。
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
  // 正控要同时证明三件事：真调用被枚举到（2 条）、良性接收者被正确识别（1 条 re.exec）、写点实参读得到
  const execOk = real.length === 2 && real.some((s) => s.cmd === 'rm') && real.some((s) => s.cmd === 'curl http://evil') &&
                 benign.length === 1 && benign[0].receiver === 're';
  const writeOk = write.length === 1 && write[0].literal === true && String(write[0].arg).includes('RULES.md');
  return {
    ok: execOk && writeOk,
    exec, write,
    detail: `正控: 真 exec 调用点 ${real.length}（期望 2：pExecFile('rm') + cp.exec('curl …')）· 良性接收者 ${benign.length}（期望 1：re.exec）· write ${write.length}（期望 1，arg=${write[0] ? write[0].arg : 'null'}）`
  };
}

/* ========================================================================== *
 * 负例 / 正例矩阵（供 --lean4-check 实测）
 * ========================================================================== */

/**
 * 证据门负例：**每一条都必须被拒**。
 * code===null 表示「竟然放过了」= 门失效。
 */
export function evidenceNegativeCases() {
  const base = { pit: 'P', lesson: 'L', suggestion: { type: '新增', detail: 'd', reason: 'r' } };
  const attempts = [
    { name: 'evidence 字段整个缺失', item: { ...base } },
    { name: 'evidence=null', item: { ...base, evidence: null } },
    { name: 'evidence=字符串', item: { ...base, evidence: 'ts=2026-09-10 cmd=ls' } },
    { name: 'evidence=数组', item: { ...base, evidence: ['2026-09-10'] } },
    { name: 'evidence={} 空对象', item: { ...base, evidence: {} } },
    { name: '只有 cmd 没有 ts', item: { ...base, evidence: { cmd: 'ls -la' } } },
    { name: '只有 output 没有 ts', item: { ...base, evidence: { output: 'stdout...' } } },
    { name: '有 ts 但 cmd/output 全空', item: { ...base, evidence: { ts: '2026-09-10T00:00:00Z', cmd: '   ', output: '' } } },
    { name: 'ts 是空白串', item: { ...base, evidence: { ts: '  ', cmd: 'ls' } } },
    { name: 'ts 非字符串(数字)', item: { ...base, evidence: { ts: 20260910, cmd: 'ls' } } }
  ];
  return attempts.map(({ name, item }) => {
    const v = adjudicate({ agent: 'neg', item });
    return { input: name, code: v.ok ? null : v.reason };
  });
}

/** 必填字段/类型负例 */
export function shapeNegativeCases() {
  const ev = { ts: '2026-09-10T00:00:00Z', cmd: 'ls' };
  const attempts = [
    { name: 'pit 缺失', item: { lesson: 'L', suggestion: { type: '新增' }, evidence: ev } },
    { name: 'lesson 为空串', item: { pit: 'P', lesson: '  ', suggestion: { type: '新增' }, evidence: ev } },
    { name: 'suggestion 缺失', item: { pit: 'P', lesson: 'L', evidence: ev } },
    { name: 'suggestion.type 缺失', item: { pit: 'P', lesson: 'L', suggestion: {}, evidence: ev } },
    { name: "suggestion.type='新增规则'（非法）", item: { pit: 'P', lesson: 'L', suggestion: { type: '新增规则' }, evidence: ev } },
    { name: "suggestion.type=''（空）", item: { pit: 'P', lesson: 'L', suggestion: { type: '' }, evidence: ev } },
    { name: 'item 是字符串', item: 'P/L/新增' },
    { name: 'item 是数组', item: [1, 2] }
  ];
  return attempts.map(({ name, item }) => {
    const v = adjudicate({ agent: 'neg', item });
    return { input: name, code: v.ok ? null : v.reason };
  });
}

/** 正例：合法证据形态必须**能通过**（防「门太宽把人自己砍了」） */
export function evidencePositiveCases() {
  const base = { pit: 'P', lesson: 'L', suggestion: { type: '新增' } };
  const cases = [
    { name: 'ts + cmd', item: { ...base, evidence: { ts: '2026-09-10T00:00:00Z', cmd: 'ls -la' } } },
    { name: 'ts + output', item: { ...base, evidence: { ts: '2026-09-10T00:00:00Z', output: 'ok' } } },
    { name: 'ts + cmd + output', item: { ...base, evidence: { ts: '2026-09-10', cmd: 'ls', output: 'ok' } } },
    { name: '四种 type 全可过', item: { ...base, suggestion: { type: '无需动作' }, evidence: { ts: 't', output: 'o' } } }
  ];
  return cases.map(({ name, item }) => {
    const v = adjudicate({ agent: 'pos', item });
    return { input: name, ok: v.ok, reason: v.reason };
  });
}

/** 品牌机制负例：绕过 mintAdmitted 的裸对象必须被 buildValidSet 拒绝 */
export function brandNegativeCases() {
  const forged = { agent: 'x', item: { pit: 'P', lesson: 'L', suggestion: { type: '新增' }, evidence: { ts: 't', cmd: 'c' } }, flags: [] };
  const cases = [forged, null, undefined, 42, 'entry', { agent: 'x', item: {} }];
  return cases.map((v, i) => {
    try { buildValidSet([v]); return { input: `forged#${i}`, code: null }; }
    catch (e) { return { input: `forged#${i}`, code: e.code || 'ERROR' }; }
  });
}

export const GATE_META = Object.freeze({
  suggestionTypes: SUGGESTION_TYPES,
  rejectReasons: ALL_REJECT_REASONS,
  evidenceRule: EVIDENCE_RULE,
  allowedCommands: ALLOWED_COMMANDS,
  allowedWriteTargets: ALLOWED_WRITE_TARGETS,
  principle: '无证据的条目在结构上进不了 valid 集合（质量门死线）；harvest 不写任何治理库',
  philosophy: 'phi-constraint-frontloaded + phi-truth'
});
