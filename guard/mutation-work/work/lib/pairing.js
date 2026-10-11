/**
 * pairing.js — K3 工具配对平衡：**切口合法性判定**（纯函数，零 dsh import）
 * =============================================================================
 * 本文件零 I/O、零时钟、零随机 —— 输入只是两个数组，故可离线跑、可逐位复算。
 *
 * ★ 为什么需要它：表面替换会改动 surface 位置，**切口若落在一次工具调用与它的结果之间**，
 *   就会把一个 step 劈成两半 —— 官方对此是硬拒绝（`validateSurfaceRegion` :525-526 直接 throw）。
 *   官方措辞：「would split a step's tool-call/result pair」/「would split a step, or the step is still open」。
 *
 * ★ 本文件**逐字复刻官方**（R030：源码已读，非推断）：
 *   来源 `@deepseek-ai/dsh-compaction/lib/types/tool-pairing.js`
 *     · `eventDelta(event)`          :9–18    ← 一条表面事件对"在途工具调用计数"的增量
 *     · `eventForSeq(events, seq)`   :20–26   ← ★ `events[seq]`（**按 seq 直接索引的数组**）
 *     · `extendCache(...)`           :28–47   ← fold 本体（逐个减去/累加，负值即"孤立 tool/result"⇒抛错）
 *     · `balanceCache(...)`          :49–69   ← 增量缓存（本文件**不做缓存**：纯函数每次重算，见下）
 *     · `cutBalance(cache, seq, off)` :70–78  ← 取切口
 *     · `toolPairingBalancedBefore`  :87–89   ← offset 0
 *     · `toolPairingBalancedAfter`   :98–100  ← offset 1
 *
 *   官方 fold 语义（半开区间约定）：
 *     cutBalanced[0]      = true            ← 空前缀切口，平凡平衡
 *     cutBalanced[i + 1]  = 处理完 nodes[i] 后是否 inProgressToolCalls === 0
 *     BalancedBefore(seq@i) = cutBalanced[i]     （节点**之前**那个切口）
 *     BalancedAfter(seq@i)  = cutBalanced[i + 1] （节点**之后**那个切口）
 *
 * ★ 与官方的**两处刻意分歧**（写下来免得日后当抄漏）：
 *   ① 官方为性能做了 WeakMap 增量缓存（:7/:49-69），键是 session + `surface.replaceGeneration`。
 *      本文件**不做缓存** —— 本插件每次决策只调用一次，缓存只会引入"陈旧 generation"这一整类缺陷，
 *      而 K2 的 F2 教训正是"把两种判据混为一谈"。**先正确，再快**；真需要时再另案加缓存。
 *   ② 官方遇错**抛**（:23/:39/:75）；本文件遇错**如实报原因**（`ok:false` + `reason`），
 *      因为本插件是**旁观者**：宁可放弃这一次替换，也绝不把宿主搞挂（R006 风险 5）。
 */

export const DELTA_KIND = Object.freeze({
  ASSISTANT_MESSAGE: 'assistant/message',
  TOOL_RESULT: 'tool/result'
});

export class PairingError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'PairingError';
    this.code = code;
  }
}

/**
 * 逐字复刻官方 `eventDelta`（:9–18）。
 * `assistant/message` 的增量 = 该消息里 **`tool-call` 块的数量**；`tool/result` = −1；其余 = 0。
 */
export function eventDelta(event) {
  switch (event.type) {
    case DELTA_KIND.ASSISTANT_MESSAGE: {
      const msg = event.data && event.data.message;
      const content = msg && msg.content;
      if (!Array.isArray(content)) {
        throw new PairingError('BAD_MESSAGE_CONTENT', `assistant/message 的 data.message.content 必须是数组`);
      }
      return content.filter((block) => block && block.type === 'tool-call').length;
    }
    case DELTA_KIND.TOOL_RESULT:
      return -1;
    default:
      return 0;
  }
}

/**
 * 逐字复刻官方 `eventForSeq`（:20–26）—— ★ 官方用 **`events[seq]`**：
 * `session.events` 是**按 seq 直接索引的数组**，且断言 `events[seq].seq === seq`（不一致即判"surface 损坏"）。
 * 本文件同时接受 `Map<seq,event>`（便于离线造数），语义不变。
 */
export function eventForSeq(events, seq) {
  const event = events instanceof Map ? events.get(seq) : events[seq];
  if (event === undefined || event.seq !== seq) {
    throw new PairingError('NO_MATCHING_EVENT', `surface seq ${seq} 无对应会话事件（surface 损坏）`);
  }
  return event;
}

/**
 * 逐字复刻官方 fold（`extendCache` :28–47 从空态起算 = `balanceCache` 的重建分支 :57-62）。
 * @returns {{cutBalanced:boolean[], indexBySeq:Map<number,number>, inProgressToolCalls:number, ok:true}}
 */
export function buildCutBalance(nodes, events) {
  if (!Array.isArray(nodes)) throw new PairingError('BAD_NODES', `nodes 必须是数组，收到 ${typeof nodes}`);
  const cutBalanced = [true];          // 官方 :59 —— 空前缀切口平凡平衡
  const indexBySeq = new Map();
  let inProgress = 0;
  nodes.forEach((seq, offset) => {
    if (typeof seq !== 'number') throw new PairingError('BAD_SEQ', `nodes[${offset}] 必须是数字 seq`);
    inProgress += eventDelta(eventForSeq(events, seq));
    if (inProgress < 0) {
      throw new PairingError('UNMATCHED_RESULT', `surface seq ${seq} 的 tool/result 无前置 tool-call（surface 损坏）`);
    }
    cutBalanced.push(inProgress === 0);
    indexBySeq.set(seq, offset);
  });
  return { cutBalanced, indexBySeq, inProgressToolCalls: inProgress, ok: true };
}

/** 逐字复刻官方 `cutBalance`（:70–78）：取切口；seq 不在表面即如实报错。 */
export function cutBalance(cache, seq, offset) {
  const index = cache.indexBySeq.get(seq);
  const balanced = index === undefined ? undefined : cache.cutBalanced[index + offset];
  if (balanced === undefined) {
    throw new PairingError('SEQ_NOT_ON_SURFACE', `tool-pairing balance: surface seq ${seq} 不在当前表面`);
  }
  return balanced;
}

/** 官方 `toolPairingBalancedBefore`（:87–89）。 */
export function balancedBefore(cache, seq) {
  return cutBalance(cache, seq, 0);
}
/** 官方 `toolPairingBalancedAfter`（:98–100）。 */
export function balancedAfter(cache, seq) {
  return cutBalance(cache, seq, 1);
}

/**
 * ★ 本插件特有（官方没有这一步，因为官方是在**已知合法切点**上调用 `compactRegion`）：
 * 给定**期望**的被遮区间，找一对**最近且合法**的切口。
 *
 * 语义（保守优先）：
 *   · 起点只许**往后**收（把期望起点里那些"跨切口"的节点留在原地，绝不提前劈开）；
 *   · 终点只许**往前**收（同上，绝不把还没闭合的 step 卷进去）；
 *   · 收无可收 ⇒ 如实判 `ok:false`（本步不动，记 skipped）——**绝不硬来**（立项书 §6 风险 2）。
 *
 * @returns {{ok:boolean, startSeq:number|null, endSeq:number|null, startShift:number, endShift:number,
 *            reason:string, shadowedCount:number}}
 */
export function findBalancedWindow(nodes, events, desiredStartSeq, desiredEndSeq) {
  let cache;
  try {
    cache = buildCutBalance(nodes, events);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return Object.freeze({ ok: false, startSeq: null, endSeq: null, startShift: 0, endShift: 0, shadowedCount: 0, reason: `表面不可读（${msg}）⇒ 本步不动` });
  }
  const si = cache.indexBySeq.get(desiredStartSeq);
  const ei = cache.indexBySeq.get(desiredEndSeq);
  if (si === undefined || ei === undefined) {
    return Object.freeze({ ok: false, startSeq: null, endSeq: null, startShift: 0, endShift: 0, shadowedCount: 0, reason: `期望区间 ${desiredStartSeq}-${desiredEndSeq} 不在当前表面 ⇒ 本步不动` });
  }
  if (si >= ei) {
    return Object.freeze({ ok: false, startSeq: null, endSeq: null, startShift: 0, endShift: 0, shadowedCount: 0, reason: `期望区间起止倒置或同点（${si} >= ${ei}）⇒ 本步不动` });
  }
  // 起点往后收：找到第一个 cutBalanced[i] === true 的 i ≥ si
  let a = -1;
  for (let i = si; i < ei; i++) if (cache.cutBalanced[i] === true) { a = i; break; }
  // 终点往前收：找到最后一个 cutBalanced[j+1] === true 的 j ≤ ei，且 j > a
  let b = -1;
  for (let j = ei; j > si; j--) if (cache.cutBalanced[j + 1] === true) { b = j; break; }
  if (a === -1 || b === -1 || a >= b) {
    return Object.freeze({
      ok: false, startSeq: null, endSeq: null, startShift: 0, endShift: 0, shadowedCount: 0,
      reason: `期望区间内不存在合法的配对平衡切口（a=${a} b=${b}）⇒ 本步不动，如实记 skipped`
    });
  }
  return Object.freeze({
    ok: true,
    startSeq: nodes[a], endSeq: nodes[b],
    startShift: a - si, endShift: ei - b,
    shadowedCount: b - a + 1,
    reason: `合法窗口 seq ${nodes[a]}-${nodes[b]}（${b - a + 1} 条；起点后移 ${a - si}、终点前移 ${ei - b}）`
  });
}

/** 一行摘要。 */
export function describeWindow(w) {
  return w.ok
    ? `window=ok seqs=${w.startSeq}-${w.endSeq} n=${w.shadowedCount} shift=${w.startShift}/${w.endShift}`
    : `window=none reason=${w.reason}`;
}
