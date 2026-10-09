/**
 * gate.js — R006#10 结构门：约束前置 · 不可绕过
 * =============================================================================
 * 本插件只做一件事：在会话内**非摘要**地压低活跃窗口。它的"不该发生路径"有三条：
 *
 *   1) **执行外部命令**（读任意文件、起进程、调 shell）——本插件**不做任何 I/O 之外的执行**：
 *      唯一的入口是会话事件流（host 平面的内存对象）。故命令白名单是**冻结的空集**，
 *      而 `--lean4-check` 的 F 项会证明源码里**执行点个数为 0**（不是"没找到危险命令"，
 *      而是"根本没能力执行命令"）。
 *   2) **召回任意东西**（召回工具变成任意文件读取 / 任意命令执行的口子）——`csx_recall`
 *      的目标在 **schema 层枚举**为 {seq, range, checkpoint}，id 只能是有界数字/数字区间；
 *      没有路径、没有命令、没有 URL 的入口。见 resolveRecallTarget()。
 *   3) **宿主端 inject 一个不存在的服务**——宿主端只能 inject host 平面存在的服务；
 *      inject `slots`（客户端专属）或不存在的服务 ⇒ 该条永久 pending ⇒ assertEntriesActivated
 *      失败 ⇒ **整棵插件树加载失败、CLD 起不来**（2026-10-09 excalidraw 事故）。
 *      同理**绝不** inject `compaction` / `toolResultPruner`——那是官方 realm 的地盘，
 *      本插件走 seam（b）并存，不接管（否则独占会拿掉官方压缩这层安全网）。
 *      scanInject() + ALLOWED_INJECT 把这条钉成结构判据。
 *
 * 门不是"检查后放行"，而是让那三条路径**在语法上不存在**。
 */
import fs from 'node:fs';
import path from 'node:path';

export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/** 冻结白名单：召回目标的种类。这是唯一的目标入口集合。 */
export const RECALL_KINDS = Object.freeze(['seq', 'range', 'checkpoint']);

/** 单个 id：纯数字，有界（会话内 seq / 检查点序号的形态；不接受任何其它字符）。 */
const ID_RE = /^[0-9]{1,7}$/;
/** 区间 id：`a-b`，两段都是纯数字。 */
const RANGE_RE = /^[0-9]{1,7}-[0-9]{1,7}$/;

/**
 * 本插件允许执行的外部命令（白名单）。
 * **空集**是设计结果，不是遗漏：本插件不 spawn/exec 任何东西。
 * `--lean4-check` F 项据此断言源码里**没有任何执行点**。
 */
export const ALLOWED_COMMANDS = Object.freeze([]);

/**
 * 宿主端 inject 白名单。
 * 只有 host 平面真实存在的服务可写；客户端专属（slots 等）与官方 realm 的地盘
 * （compaction / toolResultPruner）**一律禁止**。
 */
export const ALLOWED_INJECT = Object.freeze(['tools']);

/** 明令禁止出现在宿主端 inject 里的服务（客户端专属 + 官方 realm 独占）。 */
export const FORBIDDEN_INJECT = Object.freeze(['slots', 'compaction', 'toolResultPruner']);

/**
 * 解析召回目标。只接受 {kind ∈ RECALL_KINDS, id 为有界数字/数字区间}；
 * 一切其它输入（路径、命令、URL、注入串、空值）→ 抛 GateError。
 * 说明：**这里不拼接任何路径、不调用任何执行器**，返回值只用于在会话事件流里定位。
 */
export function resolveRecallTarget(input) {
  const kind = input && typeof input === 'object' ? String(input.kind ?? '').trim() : '';
  const rawId = input && typeof input === 'object' ? input.id : undefined;

  if (kind === '') {
    throw new GateError('EMPTY_KIND', '召回目标种类为空：只接受 ' + RECALL_KINDS.join(' / '));
  }
  if (!RECALL_KINDS.includes(kind)) {
    throw new GateError('UNKNOWN_KIND',
      `拒绝：目标种类 '${kind}' 不在枚举内。可用：${RECALL_KINDS.join(' / ')}` +
      '（枚举是冻结常量，无法通过参数扩展）。');
  }
  if (rawId === undefined || rawId === null) {
    throw new GateError('EMPTY_ID', `拒绝：kind='${kind}' 但 id 为空。`);
  }
  const id = String(rawId).trim();

  if (kind === 'range') {
    if (!RANGE_RE.test(id)) {
      throw new GateError('BAD_RANGE', `拒绝：range 的 id '${id}' 不是 <数字>-<数字>（有界）。`);
    }
    const [a, b] = id.split('-').map(Number);
    if (a > b) throw new GateError('BAD_RANGE', `拒绝：range 区间倒置 ${a}-${b}。`);
    return { kind, id, start: a, end: b };
  }

  if (!ID_RE.test(id)) {
    // 这里给出**可操作原因**：路径 / 命令 / 注入串都会被这一条拦下。
    throw new GateError('BAD_ID',
      `拒绝：${kind} 的 id '${id}' 不是 1-7 位纯数字。` +
      '本工具按会话内序号召回，**不接受路径、命令、URL 或任何其它字符串**。');
  }
  return { kind, id, index: Number(id) };
}

/**
 * 去注释 / 字符串 / 模板 / 正则字面量（行号保持不变）。
 * 为什么必须去掉：初版直接扫原文，会**把自己的检测正则和帮助文本当成执行点**——假阳性。
 * 去掉字面量后，"代码里真的调用了什么"才是被检查的对象。
 * 说明：这是源码结构扫描，不是完整 AST（本包零外部依赖，宿主内无可用解析器）；
 * 命名与输出如实标注，不冒充 AST。
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

/**
 * 正向证明：枚举全部外部命令执行点（exec/execFile/spawn 家族）的第一个实参。
 * 本插件 ALLOWED_COMMANDS 为空集 ⇒ 任何执行点都是越界，`--lean4-check` F 项据此判红。
 */
export function scanExecSites({ sources }) {
  const sites = [];
  const callRe = /(?<![\w.$])(pExecFile|execFileSync|execFile|execSync|exec|spawnSync|spawn|fork)\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw); // 与原文等长（字面量被空格替换，换行保留）→ 索引可对齐
    let m;
    while ((m = callRe.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: m[1], cmd: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/**
 * 读取宿主入口的 `export const inject = [...]` 字面量数组。
 * 宿主端 inject 一个不存在的服务 ⇒ 整棵插件树加载失败（fail-fast，且统计全部失败项）。
 * 解析失败时返回 null（如实说"没读到"，由调用方判红，绝不假装通过）。
 */
export function extractInject(src) {
  const m = String(src).match(/export\s+const\s+inject\s*=\s*\[([^\]]*)\]/);
  if (!m) return null;
  return m[1]
    .split(',')
    .map((s) => s.trim().replace(/^['"`]|['"`]$/g, ''))
    .filter((s) => s.length > 0);
}

/** 宿主入口 inject 合规性：非空读到 ∧ ⊆ ALLOWED_INJECT ∧ ∩ FORBIDDEN_INJECT = ∅ */
export function checkInject(src, { allowed = ALLOWED_INJECT, forbidden = FORBIDDEN_INJECT } = {}) {
  const inject = extractInject(src);
  if (inject === null) return { ok: false, inject: null, reason: '未读到 export const inject = [...]（宿主入口必须显式声明）' };
  const forbiddenHits = inject.filter((s) => forbidden.includes(s));
  const notAllowed = inject.filter((s) => !allowed.includes(s));
  const ok = forbiddenHits.length === 0 && notAllowed.length === 0;
  return {
    ok, inject, forbiddenHits, notAllowed,
    reason: ok ? null : (forbiddenHits.length
      ? `禁止的 inject：${forbiddenHits.join(', ')}（客户端专属或官方 realm 独占 ⇒ 该条永久 pending ⇒ 整棵插件树加载失败）`
      : `inject 不在白名单内：${notAllowed.join(', ')}（宿主端只允许 ${allowed.join(', ')}）`)
  };
}

/**
 * 负例矩阵：`--lean4-check` 逐条实测，全部被拒才算门生效。
 * 返回 [{input, code}]，code===null 表示"竟然放过了"（门失效）。
 */
export function gateNegativeCases() {
  const attempts = [
    { kind: '', id: '1' },
    { kind: 'seq' },
    { kind: 'file', id: '/etc/passwd' },
    { kind: 'seq', id: '../../secret' },
    { kind: 'seq', id: '$(whoami)' },
    { kind: 'seq', id: '1; rm -rf /' },
    { kind: 'command', id: 'launchctl' },
    { kind: 'url', id: 'http://169.254.169.254/' },
    { kind: 'range', id: '9-3' },
    { kind: 'range', id: '1;2-3' },
    { kind: 'checkpoint', id: 'abc' },
    { kind: 'seq', id: '12345678' } // 8 位越界
  ];
  return attempts.map((input) => {
    try { resolveRecallTarget(input); return { input, code: null }; }
    catch (e) { return { input, code: e.code || 'ERROR' }; }
  });
}

/** 正例：枚举内的目标必须全部可解析（否则工具不可用）。 */
export function gatePositiveCases() {
  const attempts = [
    { kind: 'seq', id: '3' },
    { kind: 'checkpoint', id: '1024' },
    { kind: 'range', id: '5-17' }
  ];
  return attempts.map((input) => {
    try { return { input, ok: resolveRecallTarget(input) }; }
    catch (e) { return { input, ok: null, err: e.message }; }
  });
}

/** 冻结检查：白名单真的不可变（防止未来有人 push 扩展）。 */
export function gateFreezeProof() {
  return {
    RECALL_KINDS: Object.isFrozen(RECALL_KINDS),
    ALLOWED_COMMANDS: Object.isFrozen(ALLOWED_COMMANDS),
    ALLOWED_INJECT: Object.isFrozen(ALLOWED_INJECT),
    FORBIDDEN_INJECT: Object.isFrozen(FORBIDDEN_INJECT),
    commandsAreEmpty: ALLOWED_COMMANDS.length === 0
  };
}

/** 读取本包源码（供 lean4-check 扫描）。文件缺失如实抛错，不静默跳过。 */
export function readSources(baseDir, files) {
  const out = {};
  for (const f of files) out[f] = fs.readFileSync(path.join(baseDir, f), 'utf8');
  return out;
}

export const GATE_META = Object.freeze({
  recallKinds: RECALL_KINDS,
  allowedCommands: ALLOWED_COMMANDS,
  allowedInject: ALLOWED_INJECT,
  forbiddenInject: FORBIDDEN_INJECT,
  principle: 'R006#10：让不该发生的路径在语法上不存在（无入口 + 有证明）'
});
