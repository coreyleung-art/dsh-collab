/**
 * budget.js — 守卫的**纯决策核**（零 import · 零 I/O · 逐位确定）
 * =============================================================================
 * 为什么单独一个文件：守卫的每一条判断都必须**可离线复算**，否则 K5 的负控与
 * K6 挂载后的事后归因都无从谈起。本文件不 import 任何 dsh / cordis / node 模块——
 * 输入是数字与普通对象，输出是冻结的普通对象；同一个输入永远得到同一个输出。
 *
 * 三条判据的来源（R030：不猜，逐条对齐官方源码）：
 *
 *   1) **预算公式**（照 ctxwin 形态 + 一处**刻意加项**）
 *        usable      = floor(cw × usablePct / 100)
 *        limit       = min(configCap, floor(cw × limitPct / 100))
 *        preemptCeil = floor(cw × preemptPct / 100)          ← 抢先上限（本插件加的，ctxwin 没有）
 *        threshold   = min(limit + bufferTokens, usable, preemptCeil)
 *      `threshold ≤ usable` 由构造保证（外层 min），即**请求前预算永不超过可用窗口**。
 *
 *      ★ preemptCeil 为什么存在（F1；2026-10-10 用户裁决走「抢先」）：
 *        并存的官方 `dsh-compaction-basic` 在 `floor(cw × DEFAULT_THRESHOLD_RATIO)` 触发
 *        （:13，`DEFAULT_THRESHOLD_RATIO = .8`）；而**照抄 ctxwin** 得到的
 *        `min(0.9cw + 8000, 0.95cw)` ≈ 0.91cw ⇒ **守卫晚于官方触发**，「在机制二发生之前介入」
 *        的立论落空（健康会话里官方先成功，本守卫永不触发，K5 也无数据可标定）。
 *        ⇒ 加一项**比率式**上限：默认 preemptPct = 70 < 官方 80，
 *        `floor(cw×70/100) < floor(cw×80/100)` 对所有 cw ≥ 10 成立 ⇒ 抢先**结构上**成立。
 *        加性 buffer 做不到这件事：cw=8192 时 `0.9cw+8000` 被 usable 夹到 7782，仍高于官方 6553。
 *        `preemptPct ≥ OFFICIAL_THRESHOLD_PCT` 直接抛 BAD_PREEMPT——不留"配置可改却静默失效"的口子。
 *
 *   2) **触发判据**（与官方 compaction-basic 逐字一致）
 *        `measurement.totalTokens < threshold ⇒ 不压`；**相等即压**。
 *      官方对照：dsh-compaction-basic/lib/index.js:882
 *        `if (measurement.totalTokens < spec.thresholdTokens) return null;`
 *      （官方还有一层并发护栏 `assertNoActiveCompaction`（:513，在 :878 调用）：它读
 *       `session.events` 里的 `unmatchedCompactionStart`，即"有 compaction/start 没配上 end"。
 *       本核以 hasOpenCompaction 入参对齐。
 *       ★ 它不是 `surface.replaceGeneration`（:810/:816/:824）——后者是**溢出重试的新鲜度判据**
 *       （"异步压缩期间表面是否已被别人换过"），与并发护栏是两回事。K2 曾把两者混为一谈，已正。）
 *
 *   3) **下界判据**（P26 机制二，本插件存在的理由）
 *        检查点必须**严格小于**被遮内容，且留出最小节省量。
 *      官方对照：`frameSummary` 输出须 < shadowedTokenCount（同文件 :556）——
 *      官方**没有**这个余量判据（无配置可改），于是摘要开销 ≥ 被遮内容时会话硬死锁。
 *      本插件把该判据**前置成纯函数**（canShrink），K3 只需把实际数字喂进来。
 *
 * ★ 为什么用**整数百分比**而不是浮点比率：
 *     `Math.floor(cw × 0.95)` 里的 0.95 不是二进制精确值，边界上会与手算差 1；
 *     本核只收整数百分比，`floor(cw × pct / 100)` 在 cw < 2^53/100 内**精确**。
 *     配置侧若给比率，由 pctFromRatio() 显式换算（四舍五入到整数百分点）。
 */

/**
 * 官方压缩器的触发比率，以整数百分点表示（80 = 0.8）。
 * 来源：`dsh-compaction-basic/lib/index.js:13 DEFAULT_THRESHOLD_RATIO = .8`，
 * 且 `settings.yaml:56` 亲口写「压缩压力阈值 = floor(1,000,000 × 0.8) = 800,000」。
 * ★ 本插件的抢先上限必须**严格低于**它；见 BUDGET_DEFAULTS.preemptPct 与 resolveBudget()。
 */
export const OFFICIAL_THRESHOLD_PCT = 80;

/** 默认值。可被 config 覆盖；这里只是"没有配置时的形状"。 */
export const BUDGET_DEFAULTS = Object.freeze({
  usablePct: 95,
  limitPct: 90,
  preemptPct: 70,
  bufferTokens: 8000,
  retainTokens: 5120,
  minSavingsTokens: 32
});

/** decide() 的取值集合（闭集：只有未超阈与已超阈两种情况会请求压缩）。 */
export const DECISION = Object.freeze({
  COMPRESS: 'compress',
  SKIP_BELOW_THRESHOLD: 'skip_below_threshold',
  SKIP_COMPACTION_IN_PROGRESS: 'skip_compaction_in_progress'
});

/** 守卫**环境不满足**时的原因码（不是 decide 的判定，是"测都测不成"）。 */
export const GUARD_REASON = Object.freeze({
  NO_TOKEN_METER: 'no_token_meter',
  NO_SESSION: 'no_session',
  NO_TARGET: 'no_target',
  NO_LLM: 'no_llm',
  NO_CONTEXT_WINDOW: 'no_context_window'
});

/** canShrink 的三态。 */
export const SHRINK = Object.freeze({
  OK: 'shrink_ok',
  IMPOSSIBLE: 'shrink_impossible',
  NOTHING_TO_SHADOW: 'shrink_nothing_to_shadow'
});

/**
 * ★ token-meter 低估的**告知**（不是修正）：dsh-token-meter/lib/index.js:15
 * `CHARS_PER_TOKEN = 4` 是固定启发式 ⇒ 中文重会话约 4× 低估 ⇒ 账面余量是虚的。
 * 本函数只做乘法与标注，**默认 factor=1（不改变任何行为）**；要启用必须显式给因子。
 * 之所以不默认开：真实倍率未标定（K5 待测），默认修正 = 编造数字（R030）。
 */
export function advisoryTokens(measuredTokens, factor = 1) {
  if (!Number.isFinite(measuredTokens) || measuredTokens < 0) throw new BudgetError('BAD_MEASURED', `measuredTokens 必须是非负有限数，收到 ${measuredTokens}`);
  if (!Number.isFinite(factor) || factor < 1) throw new BudgetError('BAD_FACTOR', `factor 必须是 ≥1 的有限数（1 = 不修正），收到 ${factor}`);
  return {
    measuredTokens,
    effectiveTokens: Math.floor(measuredTokens * factor),
    factor,
    applied: factor !== 1,
    note: 'token-meter 用 CHARS_PER_TOKEN=4 的固定启发式，中文重会话约 4× 低估'
  };
}

export class BudgetError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'BudgetError';
    this.code = code;
  }
}

/** 比率 → 整数百分点。0.95 → 95。非法值抛错（不静默 clamp）。 */
export function pctFromRatio(ratio) {
  if (typeof ratio !== 'number' || !Number.isFinite(ratio) || ratio <= 0 || ratio > 1) {
    throw new BudgetError('BAD_RATIO', `比率必须在 (0, 1] 内，收到 ${ratio}`);
  }
  return Math.round(ratio * 100);
}

function reqPct(v, name) {
  if (!Number.isInteger(v) || v <= 0 || v > 100) throw new BudgetError('BAD_PCT', `${name} 必须是 1..100 的整数，收到 ${v}`);
  return v;
}
function reqUint(v, name, code) {
  if (!Number.isInteger(v) || v < 0) throw new BudgetError(code, `${name} 必须是 ≥0 的整数，收到 ${v}`);
  return v;
}
/**
 * 抢先上限必须是 1..(官方比率 - 1) 的整数百分点。
 * ★ 把「必须早于官方触发」做成**门**而不是注释：否则又是一个「配置可改却不生效」的静默 no-op
 *   （正是本插件立论要消灭的形态）。配成 80 及以上 = 放弃抢先，本核拒绝，而不是默默接受。
 */
function reqPreemptPct(v) {
  if (!Number.isInteger(v) || v < 1 || v >= OFFICIAL_THRESHOLD_PCT) {
    throw new BudgetError('BAD_PREEMPT',
      `preemptPct 必须是 1..${OFFICIAL_THRESHOLD_PCT - 1} 的整数百分点，收到 ${v}（必须 < 官方触发比率 ${OFFICIAL_THRESHOLD_PCT}%，否则守卫晚于官方 compaction-basic 触发）`);
  }
  return v;
}

/**
 * 解析预算。返回冻结对象（含每处推导值的来源，便于日志与事后复算）。
 * `thresholdSource` 记录**三项 min 里哪一项生效**——K5 标定时要看的就是它：
 * 大量步是 'preempt' 说明抢先上限在起作用，'usable' 说明窗口小到 buffer 塞不下。
 * @param {{contextWindow:number, configCap?:number, usablePct?:number, limitPct?:number,
 *          preemptPct?:number, bufferTokens?:number}} input
 */
export function resolveBudget(input = {}) {
  const contextWindow = input.contextWindow;
  if (!Number.isInteger(contextWindow) || contextWindow <= 0) {
    throw new BudgetError('BAD_CONTEXT_WINDOW', `contextWindow 必须是 ≥1 的整数，收到 ${contextWindow}`);
  }
  const usablePct = input.usablePct === undefined ? BUDGET_DEFAULTS.usablePct : reqPct(input.usablePct, 'usablePct');
  const limitPct = input.limitPct === undefined ? BUDGET_DEFAULTS.limitPct : reqPct(input.limitPct, 'limitPct');
  const preemptPct = input.preemptPct === undefined ? BUDGET_DEFAULTS.preemptPct : reqPreemptPct(input.preemptPct);
  const bufferTokens = input.bufferTokens === undefined ? BUDGET_DEFAULTS.bufferTokens : reqUint(input.bufferTokens, 'bufferTokens', 'BAD_BUFFER');
  const configCap = input.configCap === undefined || input.configCap === null ? null : reqUint(input.configCap, 'configCap', 'BAD_CAP');

  const usable = Math.floor((contextWindow * usablePct) / 100);
  const limitBase = Math.floor((contextWindow * limitPct) / 100);
  const limit = configCap === null ? limitBase : Math.min(configCap, limitBase);
  const preemptCeil = Math.floor((contextWindow * preemptPct) / 100);

  // 三选一，严格 < 才换来源（相等时保留前一项），故 thresholdSource 是确定且可复算的。
  let threshold = limit + bufferTokens;
  let thresholdSource = 'limit+buffer';
  if (usable < threshold) { threshold = usable; thresholdSource = 'usable'; }
  if (preemptCeil < threshold) { threshold = preemptCeil; thresholdSource = 'preempt'; }

  // 官方阈值与"是否真的抢先"：随预算一起给出，供日志/标定直接读，不必再去别处算一遍。
  const officialThreshold = Math.floor((contextWindow * OFFICIAL_THRESHOLD_PCT) / 100);
  const preemptsOfficial = threshold < officialThreshold;

  return Object.freeze({
    contextWindow, configCap, usablePct, limitPct, preemptPct, bufferTokens,
    usable, limitBase, limit, preemptCeil, threshold, thresholdSource,
    officialThreshold, preemptsOfficial
  });
}

/**
 * 从宿主对象里取出**本次请求真正的路由目标**（不抛错，取不到返回 null）。
 * 与官方同源：dsh-compaction-basic/lib/index.js:696 routedTarget / :705 conversationTarget。
 *   session.requestHeader()?.config.{provider,model}   ← 首选（最近一次真实路由）
 *   agent.options.{provider,model}                     ← 兜底（显式配置）
 */
export function pickTarget(headerConfig, agentOptions) {
  const ok = (o) => o !== null && typeof o === 'object'
    && typeof o.provider === 'string' && o.provider.length > 0
    && typeof o.model === 'string' && o.model.length > 0;
  if (ok(headerConfig)) return { provider: headerConfig.provider, model: headerConfig.model, source: 'request-header' };
  if (ok(agentOptions)) return { provider: agentOptions.provider, model: agentOptions.model, source: 'agent-options' };
  return null;
}

/**
 * 压力判定。**唯一决定"要不要压"的纯函数**。
 * 顺序即语义（并发护栏先于阈值，与官方 assertNoActiveCompaction 的位置一致）。
 * @returns {{action:string, reason:string, measuredTokens:number, threshold:number,
 *            headroom:number, overBy:number, pressure:number|null}}
 */
export function decide(input = {}) {
  const budget = input.budget;
  if (budget === null || typeof budget !== 'object' || !Number.isFinite(budget.threshold)) {
    throw new BudgetError('BAD_BUDGET', 'decide 需要一个由 resolveBudget 产出的预算对象');
  }
  const measuredTokens = input.measuredTokens;
  if (!Number.isFinite(measuredTokens) || measuredTokens < 0) {
    throw new BudgetError('BAD_MEASURED', `measuredTokens 必须是非负有限数，收到 ${measuredTokens}`);
  }
  const threshold = budget.threshold;
  const headroom = threshold - measuredTokens;     // >0 = 还有多少才触发
  const overBy = measuredTokens - threshold;       // ≥0 = 已超阈多少
  const pressure = Number((measuredTokens / budget.contextWindow).toFixed(6));

  const src = budget.thresholdSource ?? 'unknown';
  if (input.hasOpenCompaction === true) {
    return Object.freeze({ action: DECISION.SKIP_COMPACTION_IN_PROGRESS, reason: '已有压缩在途，不叠加（并发护栏）', measuredTokens, threshold, thresholdSource: src, headroom, overBy, pressure });
  }
  if (measuredTokens < threshold) {
    return Object.freeze({ action: DECISION.SKIP_BELOW_THRESHOLD, reason: `未达阈值（${measuredTokens} < ${threshold}，来源 ${src}）`, measuredTokens, threshold, thresholdSource: src, headroom, overBy, pressure });
  }
  return Object.freeze({ action: DECISION.COMPRESS, reason: `已达阈值（${measuredTokens} ≥ ${threshold}，来源 ${src}），触发压缩`, measuredTokens, threshold, thresholdSource: src, headroom, overBy, pressure });
}

/**
 * ★ P26 机制二的判据本体：检查点必须**严格小于**被遮内容，且省下 ≥ minSavingsTokens。
 * 官方正是在这里无解——它的"检查点"是模型生成的摘要，开销下不去，于是
 * `3435/3450 ≥ 2466`（见 docs/compaction-lowerbound-crash-20261009.md）会话硬死锁。
 * 本插件的检查点是**原文片段 + 指针**（非摘要），故这个判据可以被保证，而不是被指望。
 * @returns {{ok:boolean, verdict:string, savings:number, savingsPct:number, minSavingsTokens:number}}
 */
export function canShrink(input = {}) {
  const shadowedTokens = input.shadowedTokens;
  if (!Number.isFinite(shadowedTokens) || shadowedTokens < 0) throw new BudgetError('BAD_SHADOWED', `shadowedTokens 必须是非负有限数，收到 ${shadowedTokens}`);
  const checkpointTokens = input.checkpointTokens;
  if (!Number.isFinite(checkpointTokens) || checkpointTokens < 0) throw new BudgetError('BAD_CHECKPOINT', `checkpointTokens 必须是非负有限数，收到 ${checkpointTokens}`);
  const minSavingsTokens = input.minSavingsTokens === undefined ? BUDGET_DEFAULTS.minSavingsTokens : reqUint(input.minSavingsTokens, 'minSavingsTokens', 'BAD_MIN_SAVINGS');

  if (shadowedTokens === 0) {
    return Object.freeze({ ok: false, verdict: SHRINK.NOTHING_TO_SHADOW, savings: 0, savingsPct: 0, minSavingsTokens });
  }
  const savings = shadowedTokens - checkpointTokens;
  const savingsPct = Math.floor((savings * 100) / shadowedTokens);
  const ok = savings >= minSavingsTokens;
  return Object.freeze({
    ok,
    verdict: ok ? SHRINK.OK : SHRINK.IMPOSSIBLE,
    savings, savingsPct, minSavingsTokens
  });
}

/** 一行摘要，供日志与 CLI 打印（不含浮点拼接，整数出整数）。 */
export function describeBudget(b) {
  return `cw=${b.contextWindow} usable=${b.usable} limit=${b.limit} threshold=${b.threshold}`
    + ` src=${b.thresholdSource} ceil=${b.preemptCeil} official=${b.officialThreshold} preempts=${b.preemptsOfficial}`
    + ` (usablePct=${b.usablePct}% limitPct=${b.limitPct}% preemptPct=${b.preemptPct}% buffer=${b.bufferTokens}${b.configCap === null ? '' : ` cap=${b.configCap}`})`;
}
