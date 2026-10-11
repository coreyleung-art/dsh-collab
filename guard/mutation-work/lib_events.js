/**
 * events.js — K3 并发护栏：**从会话事件流判定"是否已有压缩在途"**（纯函数，零 dsh import）
 * =============================================================================
 * 本文件零 I/O、零时钟、零随机 —— `events` 只是一个普通数组，故这条护栏可离线跑、可逐位复算。
 *
 * ★ 本文件**逐字复刻官方判据**（R030：源码已读，不是推断）：
 *   来源 `@deepseek-ai/dsh-compaction-basic/lib/index.js`
 *     · `inspectCompactionEntryState(events)`  :659–687   ← 扫描语义
 *     · `assertCompactionInactive(...)`        :504–507   ← 判定本体
 *     · `assertNoActiveCompaction(session,...)` :513–516   ← 取 `session.events` 喂上面两个
 *     · 调用点                                 :878       ← `"automatic pressure compaction"`
 *
 *   官方原文（:504–507）：
 *     function assertCompactionInactive(unmatchedCompactionStart, latestEndSeedSeq, stage) {
 *       if (unmatchedCompactionStart === void 0
 *           || latestEndSeedSeq !== void 0 && latestEndSeedSeq > unmatchedCompactionStart.seq) return;
 *       throw new ManualCompactionError("busy", `${stage}: compaction already in progress; ...`);
 *     }
 *   ⇒ **忙** ⟺ 「存在未配对 compaction/start」∧ ¬「有一个比它更新的 session/end-seed 边界」。
 *
 *   ★ 那个 `endSeed` 豁免不是可有可无的装饰：`session/end-seed` 是**构造期种子边界**，
 *     比未配对 start 更新 ⇒ 证明那个 start 属于**更早的会话生命周期**，是**陈旧标记**，不是真在跑。
 *     少了它，一次崩溃/重启留下的孤儿 start 会让本插件**永久**判"忙"而再不敢压 —— 那正是 P26 要消灭的那种静默失效。
 *
 * ★ 与 `surface.replaceGeneration` 的区别（K2 曾把两者混为一谈，F2 已正）：
 *   后者（:810/:816/:824）是**溢出重试的新鲜度判据**（"异步压缩期间表面是否已被别人换过"），
 *   与本护栏是两回事。本文件只实现真护栏。
 */

/** 官方扫描用的三个事件类型（逐字取自 :667/:669/:672）。 */
export const EV = Object.freeze({
  END_SEED: 'session/end-seed',
  COMPACTION_START: 'compaction/start',
  COMPACTION_END: 'compaction/end'
});

export class EventsError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'EventsError';
    this.code = code;
  }
}

/**
 * 逐字复刻官方 `inspectCompactionEntryState`（:659–687）。
 * **从尾部倒着扫**；每类状态各自"第一次命中即定"，且三类都定下后可提前退出（官方 :680 的 break）。
 * ⇒ 结果是"最新一次"的语义，且**与更早的历史无关**。
 * @param {Array<{type:string, seq:number, data?:object}>} events
 * @returns {{openTurn:*, unmatchedCompactionStart:object|undefined, latestEndSeedSeq:number|undefined}}
 */
export function inspectCompactionEntryState(events) {
  if (!Array.isArray(events)) throw new EventsError('BAD_EVENTS', `events 必须是数组，收到 ${typeof events}`);
  let openTurn = null;
  let openTurnStateKnown = false;
  let unmatchedCompactionStart;
  let compactionEntryStateKnown = false;
  let latestEndSeedSeq;
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event === null || typeof event !== 'object') throw new EventsError('BAD_EVENT', `events[${index}] 必须是对象`);
    if (latestEndSeedSeq === undefined && event.type === EV.END_SEED) latestEndSeedSeq = event.seq;
    if (!compactionEntryStateKnown) {
      if (event.type === EV.COMPACTION_START) {
        unmatchedCompactionStart = event;
        compactionEntryStateKnown = true;
      } else if (event.type === EV.COMPACTION_END) compactionEntryStateKnown = true;
    }
    if (!openTurnStateKnown) {
      if (event.type === 'turn/start') {
        openTurn = event.data === undefined ? null : event.data.turn;
        openTurnStateKnown = true;
      } else if (event.type === 'turn/end') openTurnStateKnown = true;
    }
    if (openTurnStateKnown && compactionEntryStateKnown && latestEndSeedSeq !== undefined) break;
  }
  return { openTurn, unmatchedCompactionStart, latestEndSeedSeq };
}

/**
 * 逐字复刻官方 `assertCompactionInactive`（:504–507）的**判定**，但不抛错——
 * 本插件是**旁观者**：官方抛错是"我要开工了，先撞一下"，我们只需知道"忙不忙"以决定是否叠加。
 * @returns {{busy:boolean, reason:string, staleBySeed:boolean, unmatchedStartSeq:number|null, latestEndSeedSeq:number|null}}
 */
export function compactionActivity(unmatchedCompactionStart, latestEndSeedSeq) {
  const startSeq = unmatchedCompactionStart === undefined || unmatchedCompactionStart === null
    ? null : unmatchedCompactionStart.seq;
  const seedSeq = latestEndSeedSeq === undefined ? null : latestEndSeedSeq;

  if (startSeq === null) {
    return Object.freeze({
      busy: false, staleBySeed: false, unmatchedStartSeq: null, latestEndSeedSeq: seedSeq,
      reason: '无未配对 compaction/start ⇒ 无压缩在途'
    });
  }
  if (seedSeq !== null && seedSeq > startSeq) {
    return Object.freeze({
      busy: false, staleBySeed: true, unmatchedStartSeq: startSeq, latestEndSeedSeq: seedSeq,
      reason: `未配对 start(seq=${startSeq}) 早于更新的 session/end-seed(seq=${seedSeq}) ⇒ 属更早生命周期，判陈旧、不视为在途`
    });
  }
  return Object.freeze({
    busy: true, staleBySeed: false, unmatchedStartSeq: startSeq, latestEndSeedSeq: seedSeq,
    reason: `存在未配对 compaction/start(seq=${startSeq}) 且无更新的 end-seed 边界 ⇒ 压缩在途，不叠加`
  });
}

/**
 * 一站式：从 `session.events` 直接得结论（官方 `assertNoActiveCompaction(session,…)` :513 的只读版）。
 * ★ 绝不抛出：读不到就如实报"读不到"，由调用方决定（本插件的观察器契约）。
 * @returns {{ok:boolean, busy:boolean, reason:string, ...}}
 */
export function compactionGuardFrom(events) {
  try {
    const st = inspectCompactionEntryState(events);
    const act = compactionActivity(st.unmatchedCompactionStart, st.latestEndSeedSeq);
    return Object.freeze({ ok: true, openTurn: st.openTurn, ...act });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return Object.freeze({
      ok: false, busy: false, staleBySeed: false, unmatchedStartSeq: null, latestEndSeedSeq: null,
      reason: `事件流读取失败（${msg}）⇒ 如实报未知，调用方须自行决定是否保守放行`
    });
  }
}

/** 一行摘要，供日志与 CLI 打印。 */
export function describeGuardResult(g) {
  if (!g || g.ok !== true) return `concurrency=unknown reason=${g ? g.reason : 'null'}`;
  return `concurrency=${g.busy ? 'BUSY' : 'free'}${g.staleBySeed ? '(stale-start-ignored)' : ''}`
    + ` start=${g.unmatchedStartSeq ?? '-'} endSeed=${g.latestEndSeedSeq ?? '-'}`;
}
