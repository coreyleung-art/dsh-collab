/**
 * guard.js — 压力观察器：把宿主对象**读**成一条可记录的压力读数（**零修改**）
 * =============================================================================
 * K2 的范围：**只测量，不替换**。本文件不碰 `agent.session` 的任何可变字段、
 * 不调用任何 replace/mutate、不注册任何 effect —— 它只做「读」并返回一条记录。
 *
 * ★ 为什么服务用 `ctx.get()` 而不是写进 `inject`：
 *   inject 是**强依赖**——声明了却拿不到 ⇒ 该条永久 pending ⇒ assertEntriesActivated
 *   失败 ⇒ **整棵插件树加载失败、CLD 起不来**（2026-10-09 excalidraw 事故的形态）。
 *   本插件的**功能性**依赖只有 tools；`tokenMeter` / `llm` 是"有则更好、无则如实报告"。
 *   官方自己在取可选服务时用的就是 `this.ctx.get("toolResultPruner")`
 *   （dsh-compaction-basic/lib/index.js:867）——本文件照抄这一姿势。
 *   好处：**K1 的 inject=['tools'] 与结构门 D 项判据完全不必动**，事故面保持为零。
 *
 * ★ 读数来源逐条对齐官方（R030：不猜）
 *   - `ctx.tokenMeter.measure(session).totalTokens`   ← 官方 compactIfNeeded 同源（:859）
 *   - `session.requestHeader()?.config.{provider,model}` ← 官方 routedTarget（:696）
 *   - `agent.options.{provider,model}`                ← 官方 conversationTarget 兜底（:705）
 *   - `(await ctx.llm.resolveModelInfo(p, m, signal)).context.contextWindow` ← 官方（:877）
 *   - `session.surface.replaceGeneration`             ← 官方**溢出重试的新鲜度判据**（:810/:816/:824）
 *   ★ 并发护栏**不是** replaceGeneration，而是 `assertNoActiveCompaction(session, stage)`
 *     （:513，在 :878 调用）—— 它读 `session.events` 的 `unmatchedCompactionStart`
 *     （"有 compaction/start 没配上 end"）。K3 接 `hasOpenCompaction` 时要接的是**这个**。
 *   - 官方**触发比率** `DEFAULT_THRESHOLD_RATIO = .8`（:13）→ 本插件阈值必须早于它；
 *     实现见 budget.js 的 `preemptCeil` / `preemptRatio`（F1，用户 2026-10-10 裁决「抢先」）。
 */
import {
  BUDGET_DEFAULTS, GUARD_REASON, pctFromRatio,
  resolveBudget, pickTarget, decide, describeBudget
} from './budget.js';

const msgOf = (e) => (e instanceof Error ? e.message : String(e));

/**
 * 从插件 config 取预算参数（比率→整数百分点；非法值交给 resolveBudget/pctFromRatio 抛错）。
 * ★ `preemptRatio` 是**抢先上限**：必须 < 0.8（官方 `dsh-compaction-basic:13` 的触发比率），
 *   否则守卫晚于官方触发（F1）。`resolveBudget` 会拒绝 ≥0.8 的值（BAD_PREEMPT）——
 *   这里只做换算，不自己 clamp，免得把非法值悄悄抹平。
 */
export function budgetConfigFrom(config = {}) {
  const out = {};
  out.bufferTokens = config.bufferTokens === undefined ? BUDGET_DEFAULTS.bufferTokens : config.bufferTokens;
  if (config.usableRatio !== undefined) out.usablePct = pctFromRatio(config.usableRatio);
  if (config.limitRatio !== undefined) out.limitPct = pctFromRatio(config.limitRatio);
  if (config.preemptRatio !== undefined) out.preemptPct = pctFromRatio(config.preemptRatio);
  if (config.maxTokens !== undefined) out.configCap = config.maxTokens;
  return out;
}

/**
 * 读一条压力读数。**任何一步不满足都如实返回 ok:false + 原因码**，绝不猜测、绝不抛出到调用方
 * （调用方仍会兜一层 try，双保险：守卫绝不能因为自身缺陷影响会话）。
 * @param {{get?:Function, logger?:object}} ctx 宿主 ctx（只用到 get）
 * @param {{agent?:object, signal?:object}} payload agent/pre-step 的载荷
 * @param {object} config 插件 config
 * @param {{hasOpenCompaction?:boolean}} opts K3 接并发护栏前恒为 false
 * @returns {Promise<object>} 冻结的读数记录
 */
export async function observePressure(ctx, payload, config = {}, opts = {}) {
  const get = typeof ctx?.get === 'function' ? (n) => ctx.get(n) : () => undefined;
  const agent = payload?.agent;
  const signal = payload?.signal;

  const meter = get('tokenMeter');
  if (meter === undefined || typeof meter.measure !== 'function') {
    return Object.freeze({ ok: false, reason: GUARD_REASON.NO_TOKEN_METER });
  }
  const session = agent?.session;
  if (session === undefined) return Object.freeze({ ok: false, reason: GUARD_REASON.NO_SESSION });

  let measurement;
  try { measurement = meter.measure(session); }
  catch (e) { return Object.freeze({ ok: false, reason: 'measure_failed', detail: msgOf(e) }); }
  const measuredTokens = measurement?.totalTokens;
  if (!Number.isFinite(measuredTokens)) {
    return Object.freeze({ ok: false, reason: 'measure_no_total', detail: `measure() 未给出 totalTokens：${JSON.stringify(measurement)?.slice(0, 200)}` });
  }

  // requestHeader() 本身也可能抛（会话已销毁等）⇒ 必须包住：取不到就回退 agent.options，
  // 全都取不到才报 NO_TARGET。观察器的契约是"绝不抛出到调用方"（K2-6 用例钉住这条）。
  let header;
  try { header = typeof session.requestHeader === 'function' ? session.requestHeader() : undefined; }
  catch { header = undefined; }
  const target = pickTarget(header?.config, agent?.options);
  if (target === null) return Object.freeze({ ok: false, reason: GUARD_REASON.NO_TARGET, measuredTokens });

  const llm = get('llm');
  if (llm === undefined || typeof llm.resolveModelInfo !== 'function') {
    return Object.freeze({ ok: false, reason: GUARD_REASON.NO_LLM, measuredTokens, target });
  }
  let info;
  try { info = await llm.resolveModelInfo(target.provider, target.model, signal); }
  catch (e) { return Object.freeze({ ok: false, reason: 'resolve_model_failed', detail: msgOf(e), measuredTokens, target }); }

  const contextWindow = info?.context?.contextWindow;
  if (!Number.isInteger(contextWindow) || contextWindow <= 0) {
    return Object.freeze({
      ok: false, reason: GUARD_REASON.NO_CONTEXT_WINDOW, measuredTokens, target,
      detail: `适配器未给出 contextWindow（官方对此会抛 TargetPressureConfigError；本插件如实跳过并告警）`
    });
  }

  const budget = resolveBudget({ contextWindow, ...budgetConfigFrom(config) });
  const decision = decide({ measuredTokens, budget, hasOpenCompaction: opts.hasOpenCompaction === true });
  const replaceGeneration = Number.isFinite(session?.surface?.replaceGeneration) ? session.surface.replaceGeneration : null;

  return Object.freeze({
    ok: true,
    target, measuredTokens, budget, decision, replaceGeneration,
    summary: describeBudget(budget)
  });
}

/** 一条读数 → 一行日志文本（纯函数，便于单测钉住格式）。 */
export function formatReading(reading) {
  if (!reading || reading.ok !== true) {
    return `breath=skip reason=${reading?.reason ?? 'unknown'}${reading?.detail ? ` detail=${reading.detail}` : ''}`;
  }
  const d = reading.decision;
  return `breath=${d.action} measured=${d.measuredTokens} threshold=${d.threshold}`
    + ` headroom=${d.headroom} overBy=${d.overBy} pressure=${d.pressure}`
    + ` route=${reading.target.provider}/${reading.target.model}(${reading.target.source})`
    + ` gen=${reading.replaceGeneration}`
    + ` [${reading.summary}]`
    + ` NOTE:measure-only(K2) 未做任何修改`;
}
