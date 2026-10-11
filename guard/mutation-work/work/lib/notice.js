/**
 * notice.js — 「压不动就说话」：不可缩小时的**通知产出**（纯函数，零 dsh import / 零 I/O）
 * =============================================================================
 * ★ 立项书 §2.4 **I1**：「走到阶梯末端仍缩小不了 ⇒ **不再静默** —— 写一条 `compaction/notice` 到会话
 *   + 打 `WARN`，判据与告警**同时落事件流**（R030：不隐藏"压不动"）。」
 * ★ 立项书 §5 **负控 3**：「阶梯走到尽头时，事件流**必须出现** `WARN` + notice（**不能只有"没动作"**）」。
 *
 * ★ 为什么把这条单列成模块而不是一行日志：
 *   **"没动作"与"压不动"若不落成不同形态，事后无法区分** —— 而这两者的处置完全相反
 *   （前者正常，后者意味着本后端在最需要它的那一点上失效了）。
 *   这与本插件记的「两种成因同痕」是同一族：**沉默是最危险的输出**，因为它与"一切正常"长得一样。
 *
 * ★ 本文件只**构造**通知（纯），**投递**留给 lib/index.js（那里才有 session）。
 *   ⇒ 本文件可离线全覆盖测试；「事件流里真的出现了吗」那一半需真跑（执行 apply()）。
 */

/** 通知的事件类型（逐字取自立项书 §2.4 I1）。 */
export const NOTICE_KIND = 'compaction/notice';

/** 通知级别（「打 WARN」）。 */
export const NOTICE_LEVEL = Object.freeze({ WARN: 'WARN' });

/** 不可缩小的成因码（闭集；**不得**用自由文本代替，否则又变成不可核）。 */
export const CANNOT_SHRINK_REASON = Object.freeze({
  NOTHING_TO_SHADOW: 'nothing_to_shadow',      // 可遮区为空（保活窗口吃满）
  NO_LEGAL_CUT: 'no_legal_cut',                // 可遮区内切口全不合法（配对安全切点不存在）
  LADDER_EXHAUSTED: 'ladder_exhausted',        // 阶梯走到底仍达不到要求节省量
  PLAN_FAILED: 'plan_failed'                   // 其它（带 plan.reason）
});

export class NoticeError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'NoticeError';
    this.code = code;
  }
}

/**
 * 由 `planCheckpoint` / `buildReplacement` 的结论构造一条不可缩小通知。
 *
 * ★ 契约：返回对象**必须**同时携带
 *   ① 可机器读的**实测数字**（shadowed / checkpoint / required / savings）
 *   ② 可机器读的**成因码**（闭集）
 *   ③ 一行人类可读文本
 *   ⇒ 任何一项缺失都抛错 —— 因为"只有一句人话、没有数字"的通知，事后仍然不可核（R030）。
 *
 * @param {object} result `planCheckpoint` 或 `buildReplacement` 的返回（`ok !== true`）
 * @param {{sessionSeq?:number, at?:string, phase?:string}} [ctx] 可选上下文（**不注入时钟**：at 由调用方给，保持本函数纯）
 * @returns 冻结的通知载荷
 */
export function buildCannotShrinkNotice(result, ctx = {}) {
  if (result === null || typeof result !== 'object') {
    throw new NoticeError('BAD_RESULT', 'buildCannotShrinkNotice 需要一个判定结果对象');
  }
  if (result.ok === true) {
    throw new NoticeError('NOT_A_FAILURE', '该判定是 ok=true → **不该**产通知（否则通知会退化成噪声，进而被忽略）');
  }

  // 成因码：闭集，按优先级判定（顺序即语义）
  const verdict = result.verdict;
  const reasonText = typeof result.reason === 'string' ? result.reason : '';
  let code;
  if (verdict === 'plan_nothing_to_shadow' || /可遮区为空|无处可压/.test(reasonText)) {
    code = CANNOT_SHRINK_REASON.NOTHING_TO_SHADOW;
  } else if (/切口全部不合法|配对安全切点/.test(reasonText)) {
    code = CANNOT_SHRINK_REASON.NO_LEGAL_CUT;
  } else if (verdict === 'plan_impossible' || /末档|阶梯|缩不动/.test(reasonText)) {
    code = CANNOT_SHRINK_REASON.LADDER_EXHAUSTED;
  } else {
    code = CANNOT_SHRINK_REASON.PLAN_FAILED;
  }

  // 实测数字：**必须**全部是有限数（缺一项即抛 —— 不许用"未知"占位）
  const num = (v, name) => {
    if (!Number.isFinite(v)) throw new NoticeError('MISSING_METRIC', `通知缺少可核的实测数字 ${name}（收到 ${v}）—— 「只有人话没有数字」的通知事后仍不可核`);
    return v;
  };
  const metrics = Object.freeze({
    shadowedTokens: num(result.shadowedTokens, 'shadowedTokens'),
    checkpointTokens: num(result.checkpointTokens, 'checkpointTokens'),
    requiredSavings: num(result.requiredSavings, 'requiredSavings'),
    savings: num(result.savings, 'savings')
  });

  const text = `[${NOTICE_LEVEL.WARN}] 上下文存活守卫：**压不动**（${code}）—— `
    + `被遮 ${metrics.shadowedTokens} token · 检查点 ${metrics.checkpointTokens} token · `
    + `省 ${metrics.savings} · 要求 ${metrics.requiredSavings}`
    + (reasonText ? `；判定说明：${reasonText}` : '');

  return Object.freeze({
    kind: NOTICE_KIND,
    level: NOTICE_LEVEL.WARN,
    code,
    text,
    metrics,
    detail: reasonText,
    // 可选上下文**原样带上**（不补默认值、不注时钟 —— 本函数保持纯）
    sessionSeq: ctx.sessionSeq === undefined ? null : ctx.sessionSeq,
    at: typeof ctx.at === 'string' ? ctx.at : null,
    phase: typeof ctx.phase === 'string' ? ctx.phase : null,
    // ★ 契约标记：让"这是压不动通知"在事件流里**可判**，而不是靠人读文本
    surface: 'cannot_shrink'
  });
}

/**
 * ★ 供测试与调用方：把通知压成一行摘要（日志用）。
 * 与 `buildCannotShrinkNotice` 分开，是为了让"通知内容"与"日志呈现"各自可测。
 */
export function describeNotice(n) {
  if (n === null || typeof n !== 'object') return 'notice=null';
  return `notice=${n.level} code=${n.code} shadowed=${n.metrics.shadowedTokens}`
    + ` cp=${n.metrics.checkpointTokens} savings=${n.metrics.savings} required=${n.metrics.requiredSavings}`;
}

/**
 * ★★ 判据：**通知必须与"什么都没发生"可区分**。
 * 返回两个布尔，供调用方/CALLER 断言：
 *   · isSilent(payload) —— 载荷是否是"沉默"（null / 空文本 / 无 kind）
 *   · distinguishable(payload) —— 是否满足"非沉默且带可核数字"
 * ★ 为什么做成函数而不是写进注释：**"不能只有'没动作'"这条判据必须可跑**，否则它自己就是一句人话。
 */
export function isSilent(payload) {
  if (payload === null || payload === undefined) return true;
  if (typeof payload !== 'object') return true;
  if (typeof payload.kind !== 'string' || payload.kind.length === 0) return true;
  if (typeof payload.text !== 'string' || payload.text.length === 0) return true;
  return false;
}

export function distinguishable(payload) {
  if (isSilent(payload)) return false;
  const m = payload.metrics;
  if (m === null || typeof m !== 'object') return false;
  return ['shadowedTokens', 'checkpointTokens', 'requiredSavings', 'savings'].every((k) => Number.isFinite(m[k]));
}
