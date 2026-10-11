/**
 * replace.js — K3 表面替换的**纯装配层**：把「计量 + 事件流 + 配对判据」装成一份替换计划
 * =============================================================================
 * 本文件零 dsh import、零 I/O、零时钟 —— 它只做**装配与判定**，**不调用** `session.append`。
 * 真正的写入留在 `lib/index.js`（那里才有 session），且必须再过一道宿主尺复核（见下 ★）。
 *
 * ★ 本文件存在的理由（顺序冲突）：
 *   `planCheckpoint` 先按 token 选出被遮区间，而配对判据只许在**配对安全切口**上切 ——
 *   若事后把区间"收缩"到合法切口，被遮 token 就变少而检查点**不会随之重算** ⇒
 *   节省量可能掉到要求以下，而报告仍是 ok。**两套数 = 假绿**。
 *   ⇒ 本文件把合法切口**先算出来喂进扫描**（`legalEndIdx`），使"扫出来的"就是"能用的"，只存在一套数。
 *
 * ★ 与官方的关系（R030：源码已读）：
 *   · 计量来源 ← `dsh-compaction-basic/lib/index.js:544`
 *     `selectedNodes.reduce((total, node) => total + node.tokens, 0)` —— **每个表面节点自带 `.tokens`**；
 *     节点列表 ← `dependencies.meter.measure(session).nodes`（`:537`）。
 *   · 替换调用的形状 ← 同文件 `:605–616`（`surfaceOp:{op:"replace",start,end}` + `sourceEventSeqs`）。
 *   · 边界合法性 ← 同文件 `:525–526`（`toolPairingBalancedBefore/After`，非法即 throw）。
 *
 * ★ **宿主尺复核是硬要求，不是可选项**：官方在下界判据上用的是
 *   `meter.estimateMessage(checkpointMessage)`（`:555`）而不是字符估算（`:556` 的
 *   `framedSummaryTokenCount >= shadowedTokenCount` 就是 P26 机制二本体，**相等即拒**）。
 *   本文件给出的 `checkpointTokens` 是**本核口径**的估算；**调用方在 append 之前必须**用宿主 meter
 *   再量一次成帧后的消息，不足则**放弃本次替换**（`requiresHostMeterCheck: true` 就是这条契约的机器可读形式）。
 */

import { planCheckpoint, PLAN, CP_DEFAULTS } from './checkpoint.js';
import { buildCutBalance } from './pairing.js';

/**
 * 默认取文：把事件里可读的文本抽出来。**尽力而为**，取不到就返回空串。
 * ★ 空串是**安全**的：该条仍会以 `[seq N kind]` 前缀 + 省略账出现在检查点里（指针不丢），
 *   只是没有逐字节选。宁可少引用，**绝不编造**（R030 / 立项书 §6 风险 4）。
 * ★ 形状未经全量核实：`tool/result` 的正文位置我没有实测样本 ⇒ 走兜底分支返回空串。
 */
export function defaultEntryText(event) {
  if (event === null || typeof event !== 'object') return '';
  const d = event.data;
  if (d !== null && typeof d === 'object') {
    const msg = d.message;
    if (msg !== null && typeof msg === 'object' && Array.isArray(msg.content)) {
      return msg.content
        .filter((b) => b && typeof b.text === 'string')
        .map((b) => b.text)
        .join('\n');
    }
    if (typeof d.text === 'string') return d.text;
  }
  return '';
}

/** 由事件类型定 kind（供阶梯分档：`tool/result` 在 L2 优先被丢）。取不到就报 unknown。 */
export function defaultEntryKind(event) {
  return event !== null && typeof event === 'object' && typeof event.type === 'string' ? event.type : 'unknown';
}

/**
 * ★ 主装配：给定表面节点 + 事件流 + 交接字段，产出一份**可执行且已配对安全**的替换计划。
 * @param {{nodes:Array<{seq:number,tokens:number}>, events:Array|Map, handoffFields:object,
 *          retainTokens?:number, neededSavingsTokens?:number, minSavingsTokens?:number,
 *          recallHint?:string, entryText?:Function, entryKind?:Function}} input
 * @returns 冻结的替换计划（`ok:false` 时带 reason，调用方应记 skipped 且**不动会话**）
 */
export function buildReplacement(input = {}) {
  const nodes = input.nodes;
  if (!Array.isArray(nodes)) {
    return Object.freeze({ ok: false, reason: `nodes 必须是数组（收到 ${typeof nodes}）⇒ 本步不动` });
  }
  if (nodes.length === 0) {
    return Object.freeze({ ok: false, reason: '表面为空 ⇒ 无可替换区间' });
  }
  const events = input.events;
  const getText = typeof input.entryText === 'function' ? input.entryText : defaultEntryText;
  const getKind = typeof input.entryKind === 'function' ? input.entryKind : defaultEntryKind;
  const retainTokens = input.retainTokens === undefined ? undefined : input.retainTokens;

  // 1) 配对平衡：算出**合法切口**集合
  let cache;
  try {
    cache = buildCutBalance(nodes.map((n) => n.seq), events);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return Object.freeze({ ok: false, reason: `表面配对状态不可读（${msg}）⇒ 本步不动` });
  }
  // 第 k 条之后的那个切口 = cutBalanced[k]（cutBalanced[0] 是空前缀，恒真）
  const legalEndIdx = new Set();
  for (let k = 1; k <= nodes.length; k++) if (cache.cutBalanced[k] === true) legalEndIdx.add(k);

  // 2) 条目（表面顺序 = 由旧到新）
  const entries = nodes.map((n) => {
    const ev = events instanceof Map ? events.get(n.seq) : events[n.seq];
    return {
      seq: n.seq,
      kind: getKind(ev),
      tokens: n.tokens,
      text: getText(ev)
    };
  });

  // 3) 计划（把合法切口喂进扫描 ⇒ 扫出来的就是能用的）
  const plan = planCheckpoint({
    entries,
    retainTokens,
    neededSavingsTokens: input.neededSavingsTokens,
    minSavingsTokens: input.minSavingsTokens,
    recallHint: input.recallHint,
    legalEndIdx,
    ...(input.handoffFields || {})
  });

  if (plan.ok !== true) {
    return Object.freeze({
      ok: false, verdict: plan.verdict, rung: plan.rung,
      shadowedTokens: plan.shadowedTokens, checkpointTokens: plan.checkpointTokens,
      savings: plan.savings, requiredSavings: plan.requiredSavings,
      legalCutCount: legalEndIdx.size,
      reason: `本核判不可压（${plan.reason}）⇒ 本步不动，如实记 skipped`
    });
  }

  const start = plan.range.startSeq;
  const end = plan.range.endSeq;
  const shadowedSeqs = entries
    .filter((e) => e.seq >= start && e.seq <= end)
    .map((e) => e.seq);

  return Object.freeze({
    ok: true,
    rung: plan.rung, rungLabel: plan.rungLabel,
    // ---- 直接喂 session.append("user/message", msg, { surfaceOp, sourceEventSeqs }) 的三件 ----
    surfaceOp: Object.freeze({ op: 'replace', start, end }),
    shadowedSeqs: Object.freeze(shadowedSeqs),
    handoffText: plan.handoffText,
    // ---- 报数（本核口径）----
    shadowedTokens: plan.shadowedTokens,
    checkpointTokens: plan.checkpointTokens,
    savings: plan.savings, savingsPct: plan.savingsPct,
    requiredSavings: plan.requiredSavings,
    legalCutCount: legalEndIdx.size,
    // ★ 契约：调用方 append 前必须用**宿主 meter** 再量一次成帧消息，不足则放弃
    requiresHostMeterCheck: true,
    reason: `档位 ${plan.rung} · 替换 seq ${start}-${end}（${shadowedSeqs.length} 条 ${plan.shadowedTokens} token）⇒ 检查点 ${plan.checkpointTokens} token，省 ${plan.savings}（要求 ${plan.requiredSavings}）`
  });
}

/** 一行摘要（日志与 csx_status 用）。 */
export function describeReplacement(r) {
  if (!r || r.ok !== true) return `replace=none reason=${r ? r.reason : 'null'}`;
  return `replace=ok rung=${r.rung} seqs=${r.surfaceOp.start}-${r.surfaceOp.end}`
    + ` n=${r.shadowedSeqs.length} shadowed=${r.shadowedTokens} cp=${r.checkpointTokens}`
    + ` savings=${r.savings}(${r.savingsPct}%) legalCuts=${r.legalCutCount}`;
}

/** 供测试与调用方复用：本核口径的默认估算参数。 */
export const REPLACE_DEFAULTS = Object.freeze({ charsPerToken: CP_DEFAULTS.charsPerToken });
export { PLAN };
