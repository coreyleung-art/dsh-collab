/**
 * ledger-io.js — K4 检查点账本的**落盘层**（确定序序列化 + 原子写 + 三态读）
 * =============================================================================
 * ★ 为什么单独一层：`lib/ledger.js` 是**纯核**（无 I/O），本文件只负责"把它安全地放到盘上、再安全地拿回来"。
 *   分开的收益是可验证性：落盘是**文件 I/O**，不需要执行 `apply()` 就能真跑真测
 *   （与"真写入会话"那一类不同——后者必须挂载才能验证）。
 *
 * ★★ 读盘也是三态，不是二态（与 `recall()` 的 HIT/MISS/DEGRADED 同一条教训）：
 *     ABSENT    文件不存在 —— **首次运行，正常**，等价于空账本（这不是故障）
 *     OK        读到了且解析成功
 *     DEGRADED  文件在、但**不可用**（读失败 / 超出上限 / JSON 坏 / schema 不认）
 *   为什么不能把 ABSENT 与 DEGRADED 并成一个"没有账本"：
 *     前者该继续跑（第一次用），后者**必须告警**（账本丢了 ⇒ 已压掉的内容取不回来了）。
 *     并成一个态就必然有一边被错待 —— 这正是本线反复出现的「两种成因同痕」。
 *
 * ★ 确定序序列化：键序固定 ⇒ 同账本恒得同字节 ⇒ 可做 sha 比对与"落盘前后逐字节一致"的断言。
 *   不用 `JSON.stringify(obj)` 的插入序（那由构造顺序决定，跨版本会漂）。
 *
 * ★ 原子写：先写 `<path>.tmp` 再 `rename`（同目录内 rename 原子）⇒ 读方只会看到旧的完整内容或新的完整内容，
 *   不会看到半截文件。崩溃/断电在写入中途也不会留一个残缺账本 —— 残缺账本会让下次读判 DEGRADED 而**丢掉全部历史**。
 */

import fs from 'node:fs';
import path from 'node:path';
import { emptyLedger } from './ledger.js';

/** 读盘三态。 */
export const READ_STATUS = Object.freeze({
  ABSENT: 'absent',
  OK: 'ok',
  DEGRADED: 'degraded'
});

export const LEDGER_IO_DEFAULTS = Object.freeze({
  schema: 'context-survival-ledger/v1',
  maxBytes: 32 * 1024 * 1024   // 32 MiB —— 远超账本自身上限（默认 2M 字符），到这儿必然是异常文件
});

export class LedgerIoError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'LedgerIoError';
    this.code = code;
  }
}

/* ------------------------------- 纯序列化 ------------------------------- */

/**
 * 确定序序列化：键序**写死**，与对象属性插入序无关。
 * 输出是单行紧凑 JSON（不带换行）⇒ 便于按行追加/比对。
 */
export function serializeLedger(ledger, opts = {}) {
  if (!ledger || typeof ledger !== 'object' || !Array.isArray(ledger.checkpoints)) {
    throw new LedgerIoError('BAD_LEDGER', 'serializeLedger 需要 emptyLedger()/recordCheckpoint() 的产物');
  }
  const schema = opts.schema === undefined ? LEDGER_IO_DEFAULTS.schema : opts.schema;
  const payload = {
    schema,
    maxCheckpoints: ledger.maxCheckpoints,
    maxChars: ledger.maxChars,
    evicted: ledger.evicted,
    chars: ledger.chars,
    checkpoints: ledger.checkpoints.map((cp) => ({
      id: cp.id,
      startSeq: cp.startSeq,
      endSeq: cp.endSeq,
      entries: cp.entries.map((e) => ({ seq: e.seq, kind: e.kind, text: e.text }))
    }))
  };
  return JSON.stringify(payload);
}

/**
 * 反序列化 → 账本。**一切异常都转成 DEGRADED 描述，绝不抛出**（调用方按态处置）。
 * ★ 不信任文件内容：schema / 上限 / 条目形状逐项校验，任何一项不过即 DEGRADED，
 *   绝不"尽力解析出一点是一点"——半个账本比没有账本更危险（会给出看似可信的 MISS）。
 */
export function deserializeLedger(text, opts = {}) {
  const schema = opts.schema === undefined ? LEDGER_IO_DEFAULTS.schema : opts.schema;
  if (typeof text !== 'string') {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `账本内容不是字符串（收到 ${typeof text}）` });
  }
  if (text.trim() === '') {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: '账本文件存在但为空（0 字节）⇒ 不当作"空账本"，须告警' });
  }
  let raw;
  try { raw = JSON.parse(text); } catch (e) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `账本 JSON 解析失败（${e instanceof Error ? e.message : String(e)}）` });
  }
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: '账本顶层不是对象' });
  }
  if (raw.schema !== schema) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `账本 schema 不认：期望 ${schema}，实得 ${JSON.stringify(raw.schema)}` });
  }
  if (!Array.isArray(raw.checkpoints)) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: '账本 checkpoints 不是数组' });
  }
  for (const k of ['maxCheckpoints', 'maxChars', 'evicted', 'chars']) {
    if (!Number.isInteger(raw[k]) || raw[k] < 0) {
      return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `账本字段 ${k} 非法：${JSON.stringify(raw[k])}` });
    }
  }
  for (const cp of raw.checkpoints) {
    if (cp === null || typeof cp !== 'object') return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: '检查点不是对象' });
    if (typeof cp.id !== 'string' || cp.id.length === 0) return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: '检查点 id 非法' });
    if (!Number.isInteger(cp.startSeq) || !Number.isInteger(cp.endSeq)) return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `检查点 ${cp.id} 的 seq 非法` });
    if (!Array.isArray(cp.entries) || cp.entries.length === 0) return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `检查点 ${cp.id} 的 entries 非法` });
    for (const e of cp.entries) {
      if (e === null || typeof e !== 'object') return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `检查点 ${cp.id} 的条目不是对象` });
      if (!Number.isInteger(e.seq) || typeof e.kind !== 'string' || typeof e.text !== 'string') {
        return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: `检查点 ${cp.id} 的条目形状非法（seq/kind/text）` });
      }
    }
  }
  // 校验通过 ⇒ 冻结重建（字段序统一，便于逐字节比对）
  const checkpoints = raw.checkpoints.map((cp) => Object.freeze({
    id: cp.id, startSeq: cp.startSeq, endSeq: cp.endSeq,
    entries: Object.freeze(cp.entries.map((e) => Object.freeze({ seq: e.seq, kind: e.kind, text: e.text })))
  }));
  const ledger = Object.freeze({
    checkpoints: Object.freeze(checkpoints),
    evicted: raw.evicted, chars: raw.chars,
    maxCheckpoints: raw.maxCheckpoints, maxChars: raw.maxChars,
    ok: true, reason: `已载入 ${checkpoints.length} 个检查点（逐出累计 ${raw.evicted}）`
  });
  return Object.freeze({ status: READ_STATUS.OK, ledger, reason: ledger.reason });
}

/* --------------------------------- I/O --------------------------------- */

/**
 * 读盘（三态，绝不抛出）。超上限直接判 DEGRADED —— 不读进来再判（防内存被打爆）。
 * @returns {{status:string, ledger:object|null, reason:string, bytes:number}}
 */
export function loadLedgerFile(filePath, opts = {}) {
  const maxBytes = opts.maxBytes === undefined ? LEDGER_IO_DEFAULTS.maxBytes : opts.maxBytes;
  if (typeof filePath !== 'string' || filePath.length === 0) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, reason: '账本路径为空', bytes: 0 });
  }
  let st;
  try { st = fs.statSync(filePath); } catch (e) {
    if (e && e.code === 'ENOENT') {
      return Object.freeze({ status: READ_STATUS.ABSENT, ledger: null, bytes: 0, reason: '账本文件不存在 ⇒ 首次运行，正常（等价空账本）' });
    }
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, bytes: 0, reason: `账本 stat 失败（${e && e.code ? e.code : String(e)}）` });
  }
  if (!st.isFile()) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, bytes: 0, reason: '账本路径不是普通文件' });
  }
  if (st.size > maxBytes) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, bytes: st.size, reason: `账本大小 ${st.size} 超过上限 ${maxBytes} ⇒ 拒绝载入（异常文件）` });
  }
  let text;
  try { text = fs.readFileSync(filePath, 'utf8'); } catch (e) {
    return Object.freeze({ status: READ_STATUS.DEGRADED, ledger: null, bytes: st.size, reason: `账本读取失败（${e && e.code ? e.code : String(e)}）` });
  }
  const r = deserializeLedger(text, opts);
  return Object.freeze({ status: r.status, ledger: r.ledger, bytes: st.size, reason: r.reason });
}

/**
 * 读盘 → 得到**可直接用**的账本：ABSENT 转空账本；DEGRADED 原样上报（**不掩盖**）。
 * ★ 这是给调用方的便利入口：它把"首次运行"和"账本坏了"分得很清楚。
 */
export function ledgerForUse(filePath, opts = {}) {
  const r = loadLedgerFile(filePath, opts);
  if (r.status === READ_STATUS.OK) return Object.freeze({ ...r, degraded: false });
  if (r.status === READ_STATUS.ABSENT) {
    return Object.freeze({ ...r, ledger: emptyLedger(opts), degraded: false, reason: r.reason });
  }
  return Object.freeze({ ...r, degraded: true });
}

/**
 * 原子写：先写 `<path>.tmp` 再同目录 `rename` ⇒ 读方只会看到旧的完整内容或新的完整内容。
 * @returns {{ok:boolean, bytes:number, reason:string}}
 */
export function saveLedgerFile(filePath, ledger, opts = {}) {
  if (typeof filePath !== 'string' || filePath.length === 0) {
    return Object.freeze({ ok: false, bytes: 0, reason: '账本路径为空' });
  }
  let text;
  try { text = serializeLedger(ledger, opts); } catch (e) {
    return Object.freeze({ ok: false, bytes: 0, reason: `序列化失败（${e instanceof Error ? e.message : String(e)}）` });
  }
  const tmp = `${filePath}.tmp`;
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(tmp, text, 'utf8');
    fs.renameSync(tmp, filePath);
  } catch (e) {
    try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch { /* 清理失败不掩盖主错误 */ }
    return Object.freeze({ ok: false, bytes: 0, reason: `写盘失败（${e && e.code ? e.code : String(e)}）` });
  }
  return Object.freeze({ ok: true, bytes: Buffer.byteLength(text, 'utf8'), reason: `已原子写入 ${Buffer.byteLength(text, 'utf8')} 字节` });
}

/** 一行摘要。 */
export function describeLoad(r) {
  return `ledger=${r.status}${r.degraded ? '(degraded)' : ''} bytes=${r.bytes}`
    + (r.ledger ? ` n=${r.ledger.checkpoints.length} evicted=${r.ledger.evicted}` : '')
    + (r.status === READ_STATUS.OK ? '' : ` reason=${r.reason}`);
}
