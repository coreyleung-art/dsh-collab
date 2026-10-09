/**
 * gate.js — R006#10 结构门：约束前置 · 不可绕过
 * =============================================================================
 * 本工具唯一的"不该发生路径"是：**为了重启语音后端而杀死整个框架进程**
 * （CLD / Electron / dsh-runtime），或对任意进程做宽杀（killall / pkill -f / kill -9 -1）。
 *
 * 门不是"检查后放行"，而是**让那条路径在语法上不存在**：
 *   1) 服务表是冻结常量（ALLOWED），入参只能是从表中取到的 **键**；
 *      没有 `--label <任意字符串>` 这种入口，因此"重启别的服务"无处可传。
 *   2) 框架/宽杀关键词在第二层再拦一次（纵深防御，防未来有人加参数）。
 *   3) 本模块**不导出**任何接收 PID 列表 / 进程名执行 kill 的函数；
 *      唯一的下杀调用形如 launchctl kill SIGTERM <白名单 label>。
 *   4) `--lean4-check` 用 AST 扫描证明源码内不存在宽杀调用，并跑 4 条**负例**实测。
 *
 * 因此"能否绕过"不是靠纪律，而是靠：**没有那个入口 + 有那个证明**。
 */

export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/** 冻结白名单：键 → 服务描述。这是唯一的服务入口集合。 */
export const ALLOWED = Object.freeze({
  'cld-voice': Object.freeze({
    key: 'cld-voice',
    label: 'com.dsh.cld-voice',
    ports: Object.freeze([8902, 8903]),
    health: 'http://127.0.0.1:8902/api/health',
    desc: 'cld-voice (asr_server 8902 + 8903 流式桥)',
    backendFiles: Object.freeze(['asr_server.py', 'stream_bridge.py', 'duplex_bridge.py'])
  }),
  'voice-service': Object.freeze({
    key: 'voice-service',
    label: 'com.dsh.voice-service',
    ports: Object.freeze([8905, 8906]),
    health: 'http://127.0.0.1:8906/v1/health',
    desc: 'voice-service (WS 8905 + HTTP 8906)',
    backendFiles: Object.freeze(['voice_service.py', 'duplex_bridge.py'])
  })
});

export const ALLOWED_KEYS = Object.freeze(Object.keys(ALLOWED));

/**
 * 框架 / 宽杀关键词（第二层）。
 * 说明：连"表达"都不允许——本工具在任何情况下都不重启框架，
 * 该原则见 RULES.md R035「能热重启的，就不要直接杀死整个框架」。
 */
const FRAMEWORK_TOKENS = Object.freeze([
  'cld', 'electron', 'dsh-runtime', 'dsh-runtime/', 'auto-relaunch', 'cld-auto',
  'com.dsh.comm', 'com.dsh.bus', 'bus-bridge', 'agent-bus', 'blackboard',
  'all', '*', 'everything', 'killall', 'pkill'
]);

/** 宽杀调用形态（源码结构扫描用；命中即 lean4-check 失败） */
const BROAD_KILL_CALLS = Object.freeze([
  'killall', 'pkill', 'killAll', 'taskkill'
]);

/** 允许被本工具执行的外部命令（白名单）。除此之外不得出现任何 exec/spawn 目标。 */
export const ALLOWED_COMMANDS = Object.freeze(['launchctl', 'ps']);

/**
 * 去注释 / 字符串 / 模板 / 正则字面量（行号保持不变）。
 * 为什么必须去掉：初版直接扫原文，结果**把自己的检测正则和帮助文本当成了宽杀调用**——
 * 假阳性。去掉字面量后，"代码里真的调用了什么"才是被检查的对象。
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
    // 行注释
    if (c === '/' && d === '/') { let j = i; while (j < n && src[j] !== '\n') j++; pushBlank(src.slice(i, j)); i = j; continue; }
    // 块注释
    if (c === '/' && d === '*') { let j = src.indexOf('*/', i + 2); j = j < 0 ? n : j + 2; pushBlank(src.slice(i, j)); i = j; continue; }
    // 字符串 / 模板
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === c) { j++; break; } j++; }
      pushBlank(src.slice(i, j)); i = j; continue;
    }
    // 正则字面量（粗判：/ 出现在不被视作除法的位置，且本行内可闭合）
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

/** 源码结构扫描（去字面量）：返回命中的 {file, line, callee} 列表 */
export function scanBroadKill({ sources }) {
  const hits = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    code.split('\n').forEach((line, idx) => {
      for (const name of BROAD_KILL_CALLS) {
        if (new RegExp(`(^|[^\\w.$])${name}\\s*\\(`).test(line)) hits.push({ file, line: idx + 1, callee: name });
      }
      if (/process\s*\.\s*kill\s*\(\s*-/.test(line)) hits.push({ file, line: idx + 1, callee: 'process.kill(-N)' });
    });
  }
  return hits;
}

/**
 * 正向证明：枚举全部外部命令执行点（exec/execFile/spawn/spawnSync）的第一个实参，
 * 断言其只能是 ALLOWED_COMMANDS 里的字面量。
 * 这比"没找到宽杀"更强：**本工具能执行的外部命令集合是可枚举且受限的**。
 */
export function scanExecSites({ sources }) {
  const sites = [];
  // 步骤 1：在**去字面量**的代码上定位调用点（避免把字符串/注释里的字样当成调用）
  const callRe = /(?<![\w.$])(pExecFile|execFileSync|execFile|execSync|exec|spawnSync|spawn)\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw); // 与原文等长（字面量被空格替换，换行保留）→ 索引可对齐
    let m;
    while ((m = callRe.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      // 步骤 2：回到**原文**同一偏移处读第一个实参（剥空白后是否字面量）
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: m[1], cmd: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/**
 * 解析服务键 → 服务描述。
 * 只接受白名单里的键；一切其它输入（含框架名、"all"、通配、空值）→ 抛 GateError。
 */
export function resolveService(input) {
  if (input === undefined || input === null || input === '') {
    throw new GateError('EMPTY', '服务键为空：本工具不接受空键，请显式指定白名单键之一：' + ALLOWED_KEYS.join(', '));
  }
  const key = String(input).trim();
  const low = key.toLowerCase();

  // 第一步：**精确**白名单命中（必须最先判，否则框架词会误伤合法键，例如 'cld' 命中 'cld-voice'）
  const svc = ALLOWED[key];
  if (svc) return svc;

  // 第二步：非白名单输入再判框架/宽杀关键词（给出可操作原因，而不是笼统报错）
  for (const tok of FRAMEWORK_TOKENS) {
    const hit = tok === '*' ? key.includes('*') : low.includes(tok);
    if (hit) {
      throw new GateError('FRAMEWORK_FORBIDDEN',
        `拒绝：'${key}' 命中框架/宽杀关键词「${tok}」。本工具**不重启框架进程**，` +
        `只重启白名单内的语音后端服务（${ALLOWED_KEYS.join(', ')}）。` +
        `依据 RULES.md R035：能热重启的，就不要直接杀死整个框架。`);
    }
  }

  // 第三步：其余一律拒绝
  throw new GateError('UNKNOWN_SERVICE',
    `拒绝：'${key}' 不在白名单内。可用键：${ALLOWED_KEYS.join(', ')}` +
    `（白名单是冻结常量，无法通过参数扩展）。`);
}

/**
 * 负例矩阵：--lean4-check 会逐条实测，全部被拒才算门生效。
 * 返回 [{input, code}]，code===null 表示"竟然放过了"（门失效）。
 */
export function gateNegativeCases() {
  const attempts = ['', '   ', 'CLD', 'electron', 'dsh-runtime', 'com.dsh.cld-auto-relaunch',
    'all', '*', 'everything', 'killall node', 'com.dsh.bus-bridge', 'nginx', '../cld-voice'];
  return attempts.map((input) => {
    try {
      resolveService(input);
      return { input, code: null };
    } catch (e) {
      return { input, code: e.code || 'ERROR' };
    }
  });
}

/** 正例：白名单键必须全部可解析（否则工具不可用） */
export function gatePositiveCases() {
  return ALLOWED_KEYS.map((k) => {
    try { return { key: k, ok: resolveService(k).label }; }
    catch (e) { return { key: k, ok: null, err: e.message }; }
  });
}

/* 旧的文本层 scanBroadKill 已删除：它扫原文、会把自己的检测正则与帮助文本当成宽杀调用（假阳性）。
   现行实现见上方 stripLiterals + scanBroadKill（去字面量后扫描）+ scanExecSites（枚举命令白名单）。 */

export const GATE_META = Object.freeze({
  allowed: ALLOWED_KEYS,
  frameworkTokens: FRAMEWORK_TOKENS,
  broadKill: BROAD_KILL_CALLS,
  principle: 'R035 能热重启的，就不要直接杀死整个框架'
});
