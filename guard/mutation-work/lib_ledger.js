/**
 * ledger.js — K4 检查点账本与召回**纯核**（零 dsh import、零 I/O、零时钟）
 * =============================================================================
 * 本文件只管两件事：**把被遮内容记成账** + **按 seq/range/checkpoint 逐字取回**。
 * 落盘（事件流）与工具出口留在 `lib/index.js`。
 *
 * ★ 立论链上它是**必需**的一环，不是附属功能：
 *   检查点是「投影 + 原文片段 + seq 指针」而非摘要 ⇒ **被省略的内容必须能被逐字取回**，
 *   否则整套「非摘要」立论就落空（那只是把摘要换成了丢内容）。
 *   立项书 §5 **正控 3**：「被省略段用 `csx_recall` 取回，与原文**逐字相等**」——本文件即是该判据的实现体。
 *
 * ★ 三态而非二态（照 R046 线正在推的「索引不可用不得冒充无命中」）：
 *     HIT      找到了
 *     MISS     账本**在位且可读**，但该 seq 确实不在账里（真未命中）
 *     DEGRADED 账本**不可用**（未启用 / 为空 / 结构损坏）—— **绝不冒充 MISS**
 *   为什么必须分开：把「没有账本」报成「该段不存在」，会让使用者以为内容从未被压，
 *   而实际上它被压掉且取不回来。**这两种情况的处置完全不同**（前者继续，后者必须停机告警）。
 *   本线反复出现的假绿正是这一类「两种成因同痕」。
 *
 * ★ 有界（不设上限就是另一种泄漏）：账本按 `maxCheckpoints` 与 `maxChars` **双上限**裁剪，
 *   由旧到新逐出，且**逐出计数必须留在账上**（`evicted`）——被裁掉这件事本身也是事实，
 *   不能因为"裁掉就不存在"而静默。裁剪后若某 seq 取不回，它报的是 MISS 且 `evicted > 0` 可解释。
 */

/** 召回结果三态。 */
export const RECALL_STATUS = Object.freeze({
  HIT: 'hit',
  MISS: 'miss',
  DEGRADED: 'degraded'
});

export const LEDGER_DEFAULTS = Object.freeze({
  maxCheckpoints: 8,      // 保留最近 N 次检查点
  maxChars: 2_000_000     // 总字符上限（约 500k token 量级，远超任何单会话需要）
});

export class LedgerError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'LedgerError';
    this.code = code;
  }
}

/** 空账本（冻结）。 */
export function emptyLedger(opts = {}) {
  const maxCheckpoints = opts.maxCheckpoints === undefined ? LEDGER_DEFAULTS.maxCheckpoints : opts.maxCheckpoints;
  const maxChars = opts.maxChars === undefined ? LEDGER_DEFAULTS.maxChars : opts.maxChars;
  if (!Number.isInteger(maxCheckpoints) || maxCheckpoints < 1) throw new LedgerError('BAD_CAP', `maxCheckpoints 必须是 ≥1 的整数，收到 ${maxCheckpoints}`);
  if (!Number.isInteger(maxChars) || maxChars < 1) throw new LedgerError('BAD_CAP', `maxChars 必须是 ≥1 的整数，收到 ${maxChars}`);
  return Object.freeze({ checkpoints: Object.freeze([]), evicted: 0, chars: 0, maxCheckpoints, maxChars, ok: true, reason: '空账本（尚无任何检查点）' });
}

function totalChars(cps) {
  let n = 0;
  for (const cp of cps) for (const e of cp.entries) n += (typeof e.text === 'string' ? e.text.length : 0);
  return n;
}

/** 从旧到新逐出，直到不超过双上限。返回新数组与新增逐出数。 */
function trim(checkpoints, maxCheckpoints, maxChars) {
  const cps = checkpoints.slice();
  let evicted = 0;
  while (cps.length > maxCheckpoints) { cps.shift(); evicted += 1; }
  let chars = totalChars(cps);
  while (chars > maxChars && cps.length > 1) {
    const gone = cps.shift();
    chars -= totalChars([gone]);
    evicted += 1;
  }
  return { cps, chars, evicted };
}

/**
 * 记一次检查点。**返回新账本**（不改变入参）—— 纯函数，便于离线复算。
 * @param {object} ledger 由 emptyLedger() 或本函数产出
 * @param {{id:string, startSeq:number, endSeq:number, entries:Array<{seq:number,kind:string,text:string}>}} rec
 *   `entries[].text` 必须是**原文逐字**（不是被裁剪后的引文），否则召回就不是"逐字相等"。
 */
export function recordCheckpoint(ledger, rec) {
  if (!ledger || typeof ledger !== 'object' || !Array.isArray(ledger.checkpoints)) {
    throw new LedgerError('BAD_LEDGER', 'ledger 必须是 emptyLedger() 或 recordCheckpoint() 的产物');
  }
  if (!rec || typeof rec !== 'object') throw new LedgerError('BAD_RECORD', '检查点记录必须是对象');
  if (typeof rec.id !== 'string' || rec.id.length === 0) throw new LedgerError('BAD_RECORD_ID', '检查点 id 必须是非空字符串');
  for (const k of ['startSeq', 'endSeq']) {
    if (!Number.isInteger(rec[k]) || rec[k] < 0) throw new LedgerError('BAD_RECORD_SEQ', `${k} 必须是 ≥0 的整数，收到 ${rec[k]}`);
  }
  if (!Array.isArray(rec.entries) || rec.entries.length === 0) throw new LedgerError('BAD_RECORD_ENTRIES', 'entries 必须是非空数组');
  const seen = new Set();
  for (const e of rec.entries) {
    if (!Number.isInteger(e.seq) || e.seq < 0) throw new LedgerError('BAD_ENTRY_SEQ', `entries[].seq 必须是 ≥0 的整数，收到 ${e.seq}`);
    if (typeof e.kind !== 'string' || e.kind.length === 0) throw new LedgerError('BAD_ENTRY_KIND', 'entries[].kind 必须是非空字符串');
    if (typeof e.text !== 'string') throw new LedgerError('BAD_ENTRY_TEXT', `entries[].text 必须是字符串（原文逐字），收到 ${typeof e.text}`);
    if (seen.has(e.seq)) throw new LedgerError('DUP_SEQ', `同一检查点内 seq ${e.seq} 重复`);
    seen.add(e.seq);
  }
  const frozen = Object.freeze({
    id: rec.id,
    startSeq: rec.startSeq,
    endSeq: rec.endSeq,
    entries: Object.freeze(rec.entries.map((e) => Object.freeze({ seq: e.seq, kind: e.kind, text: e.text })))
  });
  const all = [...ledger.checkpoints, frozen];
  const { cps, chars, evicted } = trim(all, ledger.maxCheckpoints, ledger.maxChars);
  return Object.freeze({
    checkpoints: Object.freeze(cps),
    evicted: ledger.evicted + evicted,
    chars,
    maxCheckpoints: ledger.maxCheckpoints,
    maxChars: ledger.maxChars,
    ok: true,
    reason: `已记 ${cps.length} 个检查点（逐出累计 ${ledger.evicted + evicted}）`
  });
}

/** 账本可用性自检：结构不对就返回 false（供 recall 判 DEGRADED）。 */
export function ledgerUsable(ledger) {
  return Boolean(ledger) && typeof ledger === 'object' && Array.isArray(ledger.checkpoints)
    && Number.isInteger(ledger.evicted) && Number.isFinite(ledger.chars);
}

/**
 * ★ 召回：按 target（`resolveRecallTarget` 的产物）逐字取回。
 * @param {object} ledger
 * @param {{kind:'seq'|'range'|'checkpoint', id:string, seq?:number, start?:number, end?:number}} target
 * @returns {{status:string, entries:Array, text:string, reason:string, evicted:number}}
 */
export function recall(ledger, target) {
  const base = { entries: [], text: '', evicted: ledger && Number.isFinite(ledger.evicted) ? ledger.evicted : 0 };
  // ---- 1) 账本不可用 ⇒ DEGRADED（**绝不冒充 MISS**）----
  if (!ledgerUsable(ledger)) {
    return Object.freeze({ ...base, status: RECALL_STATUS.DEGRADED, reason: '账本不可用（未启用或结构损坏）⇒ 本结果**不代表该内容不存在**；请检查检查点落盘是否启用' });
  }
  if (ledger.checkpoints.length === 0) {
    const tail = ledger.evicted > 0 ? `（历史已逐出 ${ledger.evicted} 次）` : '（从未记录过检查点）';
    return Object.freeze({ ...base, status: RECALL_STATUS.DEGRADED, reason: `账本为空 ${tail} ⇒ 本结果**不代表该内容不存在**` });
  }
  if (!target || typeof target !== 'object' || typeof target.kind !== 'string') {
    return Object.freeze({ ...base, status: RECALL_STATUS.DEGRADED, reason: '召回目标未解析（应由 resolveRecallTarget 产出）' });
  }

  // ---- 2) 取候选条目 ----
  let picked = [];
  if (target.kind === 'checkpoint') {
    const cp = ledger.checkpoints.find((c) => String(c.id) === String(target.id));
    if (cp) picked = cp.entries;
  } else if (target.kind === 'seq') {
    const seq = Number(target.seq === undefined ? target.id : target.seq);
    for (const cp of ledger.checkpoints) {
      const hitE = cp.entries.find((e) => e.seq === seq);
      if (hitE) { picked = [hitE]; break; }
    }
  } else if (target.kind === 'range') {
    const a = Number(target.start), b = Number(target.end);
    for (const cp of ledger.checkpoints) {
      const inRange = cp.entries.filter((e) => e.seq >= a && e.seq <= b);
      if (inRange.length > 0) { picked = inRange; break; }
    }
  } else {
    return Object.freeze({ ...base, status: RECALL_STATUS.DEGRADED, reason: `未知的召回种类 '${target.kind}'` });
  }

  // ---- 3) 真未命中（账本在位、内容不在账） ----
  if (picked.length === 0) {
    return Object.freeze({
      ...base, status: RECALL_STATUS.MISS,
      reason: `账本在位（${ledger.checkpoints.length} 个检查点），但 ${target.kind}=${target.id} 不在其中`
        + (ledger.evicted > 0 ? `；注意已有 ${ledger.evicted} 次逐出，该段可能因超界被裁` : '')
    });
  }
  const entries = picked.map((e) => ({ seq: e.seq, kind: e.kind, text: e.text }));
  return Object.freeze({
    status: RECALL_STATUS.HIT,
    entries: Object.freeze(entries),
    text: entries.map((e) => e.text).join('\n'),
    evicted: ledger.evicted,
    reason: `命中 ${entries.length} 条（seq ${entries[0].seq}-${entries[entries.length - 1].seq}），逐字返回`
  });
}

/** 一行摘要。 */
export function describeRecall(r) {
  return `recall=${r.status} n=${r.entries.length} chars=${r.text.length}`
    + (r.status === RECALL_STATUS.HIT ? '' : ` reason=${r.reason}`);
}
