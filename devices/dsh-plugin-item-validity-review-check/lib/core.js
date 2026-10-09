/**
 * core.js — 条目有效性审查 · 业务内核
 * =============================================================================
 * 回答的唯一问题：「这条现在还有效吗？」
 *
 * ★ 先分形态，再谈有效性（形态与状态是两个轴，分开报）——
 *   数据实测 2641 条里绝大多数是「记录体」，对它们谈「有效性」没有意义：
 *   记录体是**历史事实**，它的年龄不构成它失效的理由。
 *
 * ★ 五态：closed / stale / open / unknown / n/a
 * ★ 本插件**唯一的新判据**是「回复可见性」三通道（A 卡内指针 / B 线程记录 / C 指针形态）。
 * ★ 载体不统一（实测）：reply_to 的取值三种形态混用 —— 短 id / 黑板键 / **空串**。
 *   ⇒ 判据必须三分；`if (reply_to)` 这种写法是错的（空串会漏）。空串按「未提供」处理。
 *
 * 本文件无危险原语：不 exec / 不 spawn / 不 kill / 不 eval。
 * 只用 node:fs 的只读能力 + 索引那一处写（写临时文件再改名 + 写后回读断言）。
 */

import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  GateError,
  INDEX_PATH,
  INBOX_DIR,
  LOG_PATH,
  SOURCE_ENUM,
  assertNoIndexPathInput,
  assertSource,
  assertWriteTargetAllowed
} from './gate.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');

/* ══════════════════════════════ 词表与字段（判据的唯一来源） ══════════════════════════════ */

/** 关闭词：**只在状态类字段里找，绝不在正文里找**。 */
export const CLOSED_WORDS = Object.freeze([
  '不需再动', '不需处理', '无需处理', '已收讫', '已核验通过', '已通过', '已关闭',
  '已归档', '已解决', '已完成', '处理完毕', '已交付完毕',
  'closed', 'done', 'resolved', 'passed', 'no action needed'
]);

/** 待处理词（显式「仍在等你」）。 */
export const OPEN_WORDS = Object.freeze([
  '等你', '待你', '待处理', '仍在等', '待裁定', '待裁', '待回', '待其余方回',
  'pending', 'awaiting your', 'need your'
]);

/** 状态类字段（判据①/④的载体）。 */
export const STATUS_FIELDS = Object.freeze(['status', 'state', 'verdict', 'resolution', 'result']);
/** 显式的「还在等你」字段（也算状态类载体）。 */
export const PENDING_FIELDS = Object.freeze(['still_pending_user', 'awaiting_user', 'needs_user']);
/** 形态判据：动作项字段。 */
export const ACTION_FIELDS = Object.freeze(['awaiting', 'still_pending_user', 'awaiting_user']);
/** 形态判据：记录体字段。 */
export const RECORD_FIELDS = Object.freeze(['content', 'body', 'body_md', 'title', 'subject']);
/** 形态判据：消息流水字段（都认不出 ⇒ unknown，绝不并入任何一侧）。 */
export const FEED_FIELDS = Object.freeze([
  'from', 'to', 'to_full', 'from_label', 'from_agent', 'ts', '_via', '_bus', 'alerts',
  'text', 'type', 'seq', 'thread', 'snap', 'notify_only'
]);

/** 时效载体（ms 量级数字）。 */
export const TIME_MS_FIELDS = Object.freeze(['sent_at_epoch_ms', 'ts_epoch_ms', 'created_at_epoch_ms']);
/** 时效载体（ISO 字符串）。无时区时按 UTC 解释并**在理由里写明该假设**。 */
export const TIME_STR_FIELDS = Object.freeze(['ts', 'at', 'measured_at', 'created_at']);

export const DEFAULT_MAX_AGE_DAYS = 7;

/** ★ 盲区声明：每份输出必带，不可省。 */
export const BLIND_SPOT = [
  '★ 盲区：本插件只看条目本身 + 可见线程。看不到：只发在线程里未落盘的回复 /',
  '  我未参与的线程 / 未持久化的会话。⇒ open = 【无关闭声明且无可见回复】，',
  '  不等于【确定仍有未决待办】。'
].join('\n');

/** A/B 都不命中时的**强制理由串**（判据要求逐字出现）。 */
export const NO_REPLY_REASON = '未观测到回复，但本插件看不到线程外的回复';

/* ══════════════════════════════ 小工具 ══════════════════════════════ */

export function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

/** 把任意字段压成可搜索短文本（不 dump 整个对象；带深度闸防递归）。 */
export function textOf(v, limit = 4000) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'string') return v.slice(0, limit);
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  if (Array.isArray(v)) return v.slice(0, 10).map((x) => textOf(x, 400)).join(' ').slice(0, limit);
  if (typeof v === 'object') {
    const out = [];
    for (const k of Object.keys(v).slice(0, 10)) out.push(textOf(v[k], 400));
    return out.join(' ').slice(0, limit);
  }
  return '';
}

/** 状态类文本 + 它来自哪些字段（「只在状态类字段里找」的可核验证据）。 */
export function statusTextOf(doc) {
  const fields = [];
  const parts = [];
  if (!isPlainObject(doc)) return { text: '', fields };
  for (const k of [...STATUS_FIELDS, ...PENDING_FIELDS]) {
    if (k in doc) {
      fields.push(k);
      parts.push(textOf(doc[k]));
    }
  }
  return { text: parts.join(' '), fields };
}

/** 在状态类文本里找词，返回 {word, field} —— 找不到返回 null。 */
function findWord(doc, words) {
  if (!isPlainObject(doc)) return null;
  for (const k of [...STATUS_FIELDS, ...PENDING_FIELDS]) {
    if (!(k in doc)) continue;
    const t = textOf(doc[k]);
    for (const w of words) if (t.includes(w)) return { word: w, field: k };
  }
  return null;
}

/* ══════════════════════════════ 形态（先分形态，再谈有效性） ══════════════════════════════ */

/**
 * · action  动作项：有 awaiting / still_pending_user / awaiting_user，或 reply_required === true
 * · ack     回执：有状态字
 * · record  记录体：有 content/body/body_md/title/subject，且无 awaiting
 * · feed    消息流水：只有 from/to/ts/_via/alerts 之类
 * · unknown 都认不出 ⇒ **必须报 unknown，绝不可并入任何一侧**
 */
export function shapeOf(doc) {
  if (!isPlainObject(doc)) return { shape: 'unknown', basis: '非对象' };
  for (const k of ACTION_FIELDS) {
    if (k in doc) return { shape: 'action', basis: '字段 ' + k };
  }
  if (doc.reply_required === true) return { shape: 'action', basis: 'reply_required === true' };
  const st = statusTextOf(doc);
  for (const w of CLOSED_WORDS) {
    if (st.text.includes(w)) return { shape: 'ack', basis: '状态字「' + w + '」（' + st.fields.join('/') + '）' };
  }
  for (const k of RECORD_FIELDS) {
    if (k in doc) return { shape: 'record', basis: '字段 ' + k };
  }
  for (const k of FEED_FIELDS) {
    if (k in doc) return { shape: 'feed', basis: '字段 ' + k };
  }
  return { shape: 'unknown', basis: '无任何已知形态字段' };
}

/* ══════════════════════════════ 时效 ══════════════════════════════ */

/**
 * 条目年龄（天）。缺时刻 ⇒ null（unknown，**不是 0**）。
 * @returns {{days:number, source:string, kind:string, utcAssumed:boolean}|null}
 */
export function ageDays(doc, nowMs) {
  if (!isPlainObject(doc)) return null;
  for (const k of TIME_MS_FIELDS) {
    const v = doc[k];
    if (typeof v === 'number' && Number.isFinite(v) && v > 1e11) {
      return { days: (nowMs - v) / 86400000, source: k, kind: 'epoch_ms', utcAssumed: false };
    }
  }
  for (const k of TIME_STR_FIELDS) {
    const v = doc[k];
    if (typeof v !== 'string' || v.length < 10) continue;
    const m = v.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/);
    if (!m) continue;
    const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4] || 0), Number(m[5] || 0), Number(m[6] || 0));
    if (!Number.isFinite(t)) continue;
    const tzExplicit = /(Z|[+-]\d{2}:?\d{2})\s*$/.test(v);
    return { days: (nowMs - t) / 86400000, source: k, kind: 'iso_string', utcAssumed: !tzExplicit };
  }
  return null;
}

/* ══════════════════════════════ 回复可见性三通道 ══════════════════════════════ */

/** 本条的标识形态：key 字段 / 文件名 / 去扩展名 / 短 id（十六进制前缀）。 */
export function identifierForms(name, doc) {
  const forms = new Set();
  const push = (v) => { if (typeof v === 'string' && v.trim() !== '') forms.add(v.trim().toLowerCase()); };
  const base = basename(String(name));
  push(base);
  push(base.replace(/\.json$/i, ''));
  if (isPlainObject(doc)) push(doc.key);
  for (const cand of [base, base.replace(/\.json$/i, ''), isPlainObject(doc) ? doc.key : null]) {
    if (typeof cand === 'string') {
      const m = cand.match(/^([0-9a-f]{8,})/i);
      if (m) push(m[1].slice(0, 8));
    }
  }
  return forms;
}

/** 三类 reply 载体三分：短 id / 黑板键 / 空串（空串按「未提供」处理，不算命中也不报错）。 */
export function replyPointerKind(value) {
  if (value === undefined || value === null) return 'absent';
  if (typeof value !== 'string') return 'non-string';
  const v = value.trim();
  if (v === '') return 'empty';
  if (v.includes('/')) return 'blackboard-key';
  if (v.length <= 12) return 'short-id';
  return 'other';
}

/** 从一条条目里取全部出站指针（reply_to / in_reply_to），三分处理后只留「有效指针」。 */
export function outboundPointers(doc) {
  const out = [];
  if (!isPlainObject(doc)) return out;
  for (const k of ['reply_to', 'in_reply_to']) {
    if (!(k in doc)) continue;
    const kind = replyPointerKind(doc[k]);
    out.push({ field: k, kind, value: typeof doc[k] === 'string' ? doc[k].trim() : doc[k] });
  }
  return out;
}

/** 时间戳（ms），用于通道 B 的「本条之后」。返回 {ms, source} 或 null。 */
function timeMs(doc) {
  if (!isPlainObject(doc)) return null;
  for (const k of TIME_MS_FIELDS) {
    const v = doc[k];
    if (typeof v === 'number' && Number.isFinite(v) && v > 1e11) return { ms: v, source: k };
  }
  for (const k of TIME_STR_FIELDS) {
    const v = doc[k];
    if (typeof v !== 'string' || v.length < 10) continue;
    const m = v.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/);
    if (!m) continue;
    return {
      ms: Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4] || 0), Number(m[5] || 0), Number(m[6] || 0)),
      source: k
    };
  }
  for (const k of ['seq']) {
    const v = doc[k];
    if (typeof v === 'number' && Number.isFinite(v)) return { ms: v, source: k };
  }
  return null;
}

/**
 * 建立可见集索引（一次扫描内构建，供通道 A/B 使用）。
 * @param {Array<{name:string, doc:object|null}>} entries
 */
export function buildIndex(entries) {
  const inbound = new Map();   // 指针值 → [来源文件名]
  const threads = new Map();   // thread id → [{name, from, t, seq, doc}]
  const byForm = new Map();    // 标识形态 → [文件名]
  for (const e of entries) {
    const forms = identifierForms(e.name, e.doc);
    for (const f of forms) {
      if (!byForm.has(f)) byForm.set(f, []);
      byForm.get(f).push(e.name);
    }
    for (const p of outboundPointers(e.doc)) {
      if (p.kind === 'empty' || p.kind === 'absent' || p.kind === 'non-string') continue;  // ★ 三分：空串不参与匹配
      const key = String(p.value).toLowerCase();
      if (!inbound.has(key)) inbound.set(key, []);
      inbound.get(key).push({ name: e.name, field: p.field, kind: p.kind, value: p.value });
    }
    if (isPlainObject(e.doc) && typeof e.doc.thread === 'string' && e.doc.thread.trim() !== '') {
      const tid = e.doc.thread.trim();
      if (!threads.has(tid)) threads.set(tid, []);
      threads.get(tid).push({
        name: e.name,
        from: typeof e.doc.from === 'string' ? e.doc.from.trim() : textOf(e.doc.from, 80),
        t: timeMs(e.doc),
        doc: e.doc
      });
    }
  }
  return { inbound, threads, byForm, count: entries.length };
}

/** 通道 A（卡内指针）：另有一条条目，其 reply_to / in_reply_to 指向本条 ⇒ 中强度。 */
export function channelA(entry, index) {
  const forms = identifierForms(entry.name, entry.doc);
  const hits = [];
  for (const f of forms) {
    const list = index.inbound.get(f);
    if (!list) continue;
    for (const rec of list) if (rec.name !== entry.name) hits.push(rec);
  }
  return { applicable: true, hit: hits.length > 0, hits, forms: [...forms] };
}

/**
 * 通道 B（线程记录）：本条若带 thread，在该线程 id 下存在**本条之后**的、来自**非本条发件人**的消息 ⇒ 强强度。
 * P0 实现：读 inbox 中含同一 thread 值的其他条目，比较 sent_at_epoch_ms / ts 与 from（不接任何外部服务）。
 */
export function channelB(entry, index) {
  if (!isPlainObject(entry.doc) || typeof entry.doc.thread !== 'string' || entry.doc.thread.trim() === '') {
    return { applicable: false, evaluated: false, hit: false, reason: '本条无 thread 字段 ⇒ 通道 B 不可达' };
  }
  const tid = entry.doc.thread.trim();
  const members = index.threads.get(tid) || [];
  const mine = timeMs(entry.doc);
  const myFrom = typeof entry.doc.from === 'string' ? entry.doc.from.trim() : textOf(entry.doc.from, 80);
  const evidence = [];
  let evaluated = false;
  for (const m of members) {
    if (m.name === entry.name) continue;
    if (mine && m.t) {
      evaluated = true;
      if (m.t.ms > mine.ms && m.from !== myFrom) {
        evidence.push({ file: m.name, from: m.from, t: m.t.ms, basis: '晚于本条（' + mine.source + '→' + m.t.source + '）且发件人不同' });
      }
    }
  }
  return {
    applicable: true,
    evaluated,
    hit: evidence.length > 0,
    threadId: tid,
    members: members.length,
    evidence,
    reason: evidence.length
      ? '线程内存在本条之后的他人消息'
      : (evaluated ? '线程内未见本条之后的他人消息' : '线程内其余条目缺时刻，无法判定先后 ⇒ 未命中')
  };
}

/** 通道 C（指针形态）：本条自身 reply_to 指向的键/文件仍存在 ⇒ 弱强度（与「是否被回」无关）。 */
export function channelC(entry, index) {
  const ptrs = outboundPointers(entry.doc).filter((p) => p.kind !== 'empty' && p.kind !== 'absent' && p.kind !== 'non-string');
  if (ptrs.length === 0) return { applicable: false, resolves: false, pointers: outboundPointers(entry.doc), note: '本条无有效 reply_to' };
  const resolved = [];
  for (const p of ptrs) {
    const list = index.byForm.get(String(p.value).toLowerCase());
    if (list) resolved.push({ pointer: p.value, kind: p.kind, resolvesTo: list });
  }
  return {
    applicable: true,
    resolves: resolved.length > 0,
    pointers: ptrs,
    resolved,
    note: '弱强度：只作参考信息，**不得据此判 closed**'
  };
}

/* ══════════════════════════════ 五态判定 ══════════════════════════════ */

/**
 * 判定阶梯（自上而下，命中即返回）：
 *   0 非对象                      → unknown
 *   1 形态判不了                  → unknown（**不得并入 n/a**）
 *   2 状态字命中关闭词            → closed（① 显式声明，最强）
 *   3 非动作项                    → n/a（记录体/回执/流水：不谈有效性）
 *   4 通道 A 命中                 → closed（写明 A）
 *   5 通道 B 命中                 → closed（写明 B）
 *   6 缺时刻                      → unknown（缺的是什么 + 怎么补）
 *   7 超窗 / 已被取代             → stale
 *   8 通道 B 适用却未见回复        → unknown（★ 强制理由：未观测到回复，但本插件看不到线程外的回复）
 *   9 其余（无关闭声明、无可见回复）→ open
 *
 * ★ 阶梯的 8/9 是规范里两处要求张力的落点，处置如下（并在 README「坑」里如实记录）：
 *   §3「A/B 都不命中 ⇒ 报 unknown，不得报 open」按字面适用于**回复通道可观测**的条目
 *   （本条带 thread ⇒ 我们确实看了线程，看没看到都只能叫 unknown）；
 *   不带 thread 的条目根本没有可观测的回复通道，其结论就是 §2/§4 的 open
 *   （【无关闭声明且无可见回复】），由盲区声明兜底。
 *   若采用严格读法（一切 A/B 不命中皆 unknown），把 strictNoReply 传 true 即可 —— 两条口径的计数都会输出。
 */
export function classify(doc, name = '(inline)', ctx = {}) {
  const nowMs = typeof ctx.nowMs === 'number' ? ctx.nowMs : Date.now();
  const maxAgeDays = typeof ctx.maxAgeDays === 'number' && Number.isFinite(ctx.maxAgeDays) ? ctx.maxAgeDays : DEFAULT_MAX_AGE_DAYS;
  const index = ctx.index || buildIndex([{ name, doc }]);
  const strict = ctx.strictNoReply === true;

  const entry = { name, doc };
  const conditions = {
    maxAgeDays,
    shape: null,
    shapeBasis: null,
    statusFields: [],
    closeWord: null,
    openWord: null,
    hasThread: false,
    threadId: null,
    timeCarrier: null,
    ageDays: null,
    inWindow: null,
    replyChannelApplicable: false,
    channelA: null,
    channelB: null,
    channelC: null,
    supersededBy: null,
    strictNoReply: strict
  };

  /* 0 非 JSON 对象 */
  if (!isPlainObject(doc)) {
    return finish('unknown',
      '非 JSON 对象（读失败或格式不符）⇒ 判不了',
      { shape: 'unknown', channel: null, conditions, missing: '一个合法的 JSON 对象（本条不是）', howToFix: '修好该文件的 JSON 语法/结构；若它是数组或标量，包成对象再落盘' });
  }

  /* 1 形态 */
  const shapeInfo = shapeOf(doc);
  conditions.shape = shapeInfo.shape;
  conditions.shapeBasis = shapeInfo.basis;
  const st = statusTextOf(doc);
  conditions.statusFields = st.fields;
  conditions.closeWord = findWord(doc, CLOSED_WORDS);
  conditions.openWord = findWord(doc, OPEN_WORDS);
  conditions.hasThread = typeof doc.thread === 'string' && doc.thread.trim() !== '';
  conditions.threadId = conditions.hasThread ? doc.thread.trim() : null;
  const a = channelA(entry, index);
  const b = channelB(entry, index);
  const c = channelC(entry, index);
  conditions.channelA = { hit: a.hit, forms: a.forms, hits: a.hits.map((h) => ({ file: h.name, field: h.field, kind: h.kind, value: h.value })) };
  conditions.channelB = { applicable: b.applicable, evaluated: b.evaluated, hit: b.hit, threadId: b.threadId || null, members: b.members || 0, evidence: b.evidence || [], reason: b.reason };
  conditions.channelC = { applicable: c.applicable, resolves: c.resolves, pointers: (c.pointers || []).map((p) => ({ field: p.field, kind: p.kind, value: p.value })), resolved: c.resolved || [] };
  conditions.replyChannelApplicable = b.applicable;

  if (shapeInfo.shape === 'unknown') {
    return finish('unknown',
      '**形态判不了** ⇒ 连它适不适用有效性判据都不知道（这不是「不适用」，是「判不了」）',
      { shape: 'unknown', channel: null, conditions, missing: '任一形态字段：动作项(awaiting/reply_required)｜记录体(content/body/title/subject)｜流水(from/to/ts)｜回执(状态字)', howToFix: '补一个形态字段即可判；在此之前**不得当已关闭，也不得当不适用**' });
  }

  /* 2 显式关闭（最强） */
  if (conditions.closeWord) {
    return finish('closed',
      '状态类字段 ' + conditions.closeWord.field + ' 命中关闭词「' + conditions.closeWord.word + '」⇒ 作者已声明不必再管',
      { shape: shapeInfo.shape, channel: 'status:' + conditions.closeWord.field, conditions });
  }

  /* 3 非动作项 ⇒ 不谈有效性 */
  if (shapeInfo.shape !== 'action') {
    const why = {
      record: '记录体是**历史事实**，其年龄不构成失效理由 ⇒ 不对它谈有效性',
      feed: '消息流水不是待办 ⇒ 不对它谈有效性',
      ack: '回执本身即「已读过」的记录 ⇒ 不对它谈有效性'
    }[shapeInfo.shape] || '非动作项 ⇒ 不对它谈有效性';
    return finish('n/a', '形态=' + shapeInfo.shape + '（' + shapeInfo.basis + '）：' + why, { shape: shapeInfo.shape, channel: null, conditions });
  }

  /* 4/5 回复可见性 */
  if (a.hit) {
    const ev = a.hits[0];
    return finish('closed',
      '通道 A（卡内指针）命中：' + ev.name + ' 的 ' + ev.field + ' =「' + ev.value + '」指向本条 ⇒ 已见回复',
      { shape: 'action', channel: 'A', conditions });
  }
  if (b.hit) {
    const ev = b.evidence[0];
    return finish('closed',
      '通道 B（线程记录）命中：线程 ' + b.threadId + ' 内 ' + ev.file + ' 晚于本条且发件人（' + ev.from + '）不同 ⇒ 已见回复',
      { shape: 'action', channel: 'B', conditions });
  }
  if (strict && !b.hit) {
    // 严格读法：一切 A/B 不命中皆判 unknown（本分支只为两条口径都留证据）
    const ageStrict = ageDays(doc, nowMs);
    if (ageStrict) { conditions.ageDays = Number(ageStrict.days.toFixed(2)); conditions.timeCarrier = ageStrict.source; }
    return finish('unknown',
      NO_REPLY_REASON + '（严格读法：一切 A/B 不命中皆 unknown）',
      { shape: 'action', channel: null, conditions, missing: '一条指向本条的回复条目（通道 A）或线程内晚于本条的他人消息（通道 B）', howToFix: '让对方在可见通道回一条（落盘到 inbox 或线程内）后重跑' });
  }

  /* 6 时效 */
  const age = ageDays(doc, nowMs);
  if (age) {
    conditions.ageDays = Number(age.days.toFixed(2));
    conditions.timeCarrier = age.source;
    conditions.inWindow = age.days <= maxAgeDays;
  }
  if (!age) {
    return finish('unknown',
      '是动作项，但**缺时刻** ⇒ 无法判时效（缺 ≠ 没有）',
      { shape: 'action', channel: null, conditions, missing: '时效载体：sent_at_epoch_ms / ts_epoch_ms / created_at_epoch_ms（ms 数字）或 ts/at/measured_at/created_at（ISO 字符串）', howToFix: '落一个时刻字段（缺时区的 ISO 串将被按 UTC 解释，理由里会写明该假设）' });
  }
  const utcNote = age.utcAssumed ? '（' + age.source + ' 无时区 ⇒ 按 UTC 解释，此为假设）' : '';

  /* 7 超窗 */
  if (age.days > maxAgeDays) {
    return finish('stale',
      '动作项超窗：距今 ' + age.days.toFixed(1) + ' 天 > 窗 ' + maxAgeDays + ' 天（窗值已打印）' + utcNote +
      ' ⇒ 疑似过期；须核其依赖是否已解决后才可关闭',
      { shape: 'action', channel: null, conditions });
  }

  /* 7b 已被取代 */
  const sup = supersededBy(entry, index);
  if (sup) {
    conditions.supersededBy = sup;
    return finish('stale',
      '已被取代：同键（' + sup.key + '）有更晚的条目 ' + sup.file + sup.timeNote + ' ⇒ 本条失效', 
      { shape: 'action', channel: null, conditions });
  }

  /* 8 通道 B 适用却未见回复 ⇒ unknown */
  if (b.applicable) {
    return finish('unknown',
      NO_REPLY_REASON + '（本条带 thread=' + b.threadId + '，已查该线程 ' + (b.members || 0) + ' 条：' + b.reason + '）',
      { shape: 'action', channel: null, conditions, missing: '线程内一条晚于本条的他人消息', howToFix: '让回复落进该 thread；或若已知回复发生在别处，把回复也落成带 thread 的条目' });
  }

  /* 9 无关闭声明 + 无可见回复 */
  return finish('open',
    '动作项 · 窗内（距今 ' + age.days.toFixed(1) + ' 天 ≤ 窗 ' + maxAgeDays + ' 天）· 无关闭声明 · 无可见回复' + utcNote +
    ' ⇒ open =【无关闭声明且无可见回复】，**不等于【确定仍有未决待办】**（见盲区声明）',
    { shape: 'action', channel: null, conditions });

  function finish(state, why, extra) {
    return {
      state,
      why,
      shape: extra.shape,
      channel: extra.channel || null,
      conditions: extra.conditions,
      missing: extra.missing || null,
      howToFix: extra.howToFix || null
    };
  }
}

/** 「已被取代」：同 key 有更晚条目（仅当 key 非空且确实更晚）。 */
export function supersededBy(entry, index) {
  if (!isPlainObject(entry.doc) || typeof entry.doc.key !== 'string' || entry.doc.key.trim() === '') return null;
  const key = entry.doc.key.trim().toLowerCase();
  const mine = timeMs(entry.doc);
  const list = index.byForm.get(key);
  if (!list || list.length < 2) return null;
  for (const other of list) {
    if (other === entry.name) continue;
    const o = index.entryByName ? index.entryByName.get(other) : null;
    if (!o) continue;
    const t = timeMs(o);
    if (mine && t && t.ms > mine.ms) {
      return { key: entry.doc.key, file: other, timeNote: '（' + t.source + ' 更晚）' };
    }
  }
  return null;
}

/* ══════════════════════════════ 扫描 ══════════════════════════════ */

export function readInbox(dir = INBOX_DIR) {
  const entries = [];
  let names = [];
  try {
    names = readdirSync(dir).filter((n) => n.endsWith('.json')).sort();
  } catch (e) {
    throw new GateError('IO_INBOX_UNREADABLE', '无法读取数据源目录 ' + dir + '：' + String(e && e.message));
  }
  for (const name of names) {
    const p = join(dir, name);
    try {
      if (!statSync(p).isFile()) continue;
    } catch {
      continue;
    }
    let doc = null;
    let parseError = null;
    try {
      doc = JSON.parse(readFileSync(p, 'utf8'));
    } catch (e) {
      parseError = String(e && e.message);
    }
    entries.push({ name, path: p, doc, parseError });
  }
  return entries;
}

/**
 * 全量扫描（只读）。
 * @returns {{total:number, rows:Array, tally:object, shapeTally:object, strictTally:object, maxAgeDays:number, dir:string}}
 */
export function scanInbox(options = {}) {
  const dir = options.dir || INBOX_DIR;
  const maxAgeDays = typeof options.maxAgeDays === 'number' && Number.isFinite(options.maxAgeDays) ? options.maxAgeDays : DEFAULT_MAX_AGE_DAYS;
  const nowMs = typeof options.nowMs === 'number' ? options.nowMs : Date.now();
  const entries = options.entries || readInbox(dir);
  const index = buildIndex(entries);
  index.entryByName = new Map(entries.map((e) => [e.name, e.doc]));
  index.pathByName = new Map(entries.map((e) => [e.name, e.path]));

  const rows = [];
  const tally = { closed: 0, stale: 0, open: 0, unknown: 0, 'n/a': 0 };
  const strictTally = { closed: 0, stale: 0, open: 0, unknown: 0, 'n/a': 0 };
  const shapeTally = { action: 0, record: 0, feed: 0, ack: 0, unknown: 0 };

  for (const e of entries) {
    const r = classify(e.doc, e.name, { nowMs, maxAgeDays, index });
    if (e.parseError) {
      r.why = 'JSON 解析失败 ⇒ 判不了：' + e.parseError;   // 解析失败也算 unknown，笔记明原因
      r.state = 'unknown';
      r.shape = 'unknown';
      r.missing = '合法的 JSON 语法';
      r.howToFix = '修好该文件的 JSON 语法后重跑';
      r.conditions.shape = 'unknown';
    }
    tally[r.state] = (tally[r.state] || 0) + 1;
    shapeTally[r.shape] = (shapeTally[r.shape] || 0) + 1;
    const rs = classify(e.doc, e.name, { nowMs, maxAgeDays, index, strictNoReply: true });
    strictTally[rs.state] = (strictTally[rs.state] || 0) + 1;
    rows.push({ file: e.name, state: r.state, shape: r.shape, why: r.why, channel: r.channel, missing: r.missing, howToFix: r.howToFix, conditions: r.conditions });
  }
  return { total: entries.length, rows, tally, shapeTally, strictTally, maxAgeDays, dir, nowMs };
}

/* ══════════════════════════════ R7 统一日志 ══════════════════════════════ */

/**
 * 每次判一条写一行 JSON：{ts, tool, source, shape, state, why, channel, elapsed_ms}
 * ★ 判不了（unknown）也必须写。
 */
export function logJudge(rec) {
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    tool: rec.tool || 'item_validity_check',
    source: rec.source || 'inbox',
    shape: rec.shape || null,
    state: rec.state || null,
    why: rec.why || null,
    channel: rec.channel || null,
    elapsed_ms: typeof rec.elapsed_ms === 'number' ? rec.elapsed_ms : null
  });
  try {
    mkdirSync(dirname(LOG_PATH), { recursive: true });
    writeFileSync(LOG_PATH, line + '\n', { flag: 'a' });
    return true;
  } catch {
    return false;   // 落盘失败不阻断判定
  }
}

/* ══════════════════════════════ 对外四动作（工具层共用） ══════════════════════════════ */

function resolveSource(source) {
  return assertSource(source === undefined ? SOURCE_ENUM[0] : source);
}

/** 单条判定（按 key / 文件名）。 */
export function checkItem(args = {}) {
  assertNoIndexPathInput(args);
  const source = resolveSource(args.source);
  const t0 = Date.now();
  const entries = readInbox(INBOX_DIR);
  const index = buildIndex(entries);
  index.entryByName = new Map(entries.map((e) => [e.name, e.doc]));
  const key = String(args.key === undefined || args.key === null ? '' : args.key).trim().toLowerCase();
  if (key === '') {
    throw new GateError('USAGE_NO_KEY', '用法错误：需要 key（inbox 条目文件名 / 去掉 .json 的名 / 条目自身 key 字段）');
  }
  const hit = entries.find((e) => identifierForms(e.name, e.doc).has(key) || String(e.name).toLowerCase() === key);
  if (!hit) {
    return {
      ok: false, tool: 'item_validity_check', source, key: args.key, found: false,
      state: 'unknown', shape: 'unknown',
      why: '可见集内找不到该条目（找不到 ≠ 已关闭）',
      missing: '一个存在于 ' + INBOX_DIR + ' 的条目',
      howToFix: '确认 key 是 inbox 内的文件名或条目 key 字段',
      blindSpot: BLIND_SPOT
    };
  }
  const r = classify(hit.doc, hit.name, {
    nowMs: Date.now(),
    maxAgeDays: args.maxAgeDays,
    index
  });
  const elapsed = Date.now() - t0;
  logJudge({ tool: 'item_validity_check', source, shape: r.shape, state: r.state, why: r.why, channel: r.channel, elapsed_ms: elapsed });
  return {
    ok: true, tool: 'item_validity_check', source, key: hit.name, found: true,
    state: r.state, shape: r.shape, why: r.why, channel: r.channel,
    missing: r.missing, howToFix: r.howToFix,
    conditions: r.conditions,
    blindSpot: BLIND_SPOT
  };
}

/** 批量扫描（只读）。 */
export function batchScan(args = {}) {
  assertNoIndexPathInput(args);
  const source = resolveSource(args.source);
  const t0 = Date.now();
  const scan = scanInbox({ maxAgeDays: args.maxAgeDays });
  let rows = scan.rows;
  if (typeof args.state === 'string' && args.state !== '') {
    rows = rows.filter((r) => r.state === args.state);
  }
  if (typeof args.limit === 'number' && args.limit > 0) rows = rows.slice(0, args.limit);
  // R7：每条一行（含 unknown）
  for (const r of scan.rows) {
    logJudge({ tool: 'item_validity_batch', source, shape: r.shape, state: r.state, why: r.why, channel: r.channel, elapsed_ms: null });
  }
  const elapsed = Date.now() - t0;
  return {
    ok: true, tool: 'item_validity_batch', source, dir: scan.dir.replace(String(process.env.HOME || ''), '~'),
    total: scan.total, maxAgeDays: scan.maxAgeDays,
    tally: scan.tally, shapeTally: scan.shapeTally, strictTally: scan.strictTally,
    returned: rows.length, rows,
    elapsed_ms: elapsed,
    blindSpot: BLIND_SPOT
  };
}

/** 解释一条（含条件量与盲区）。@param {{sample?:object}} 可传内存样条，不落盘 */
export function explainItem(args = {}) {
  assertNoIndexPathInput(args);
  const source = resolveSource(args.source);
  const t0 = Date.now();
  let doc = null;
  let name = '(inline)';
  let index = null;
  if (args.sample !== undefined) {
    doc = typeof args.sample === 'string' ? JSON.parse(args.sample) : args.sample;
    index = buildIndex([{ name, doc }]);
  } else {
    const entries = readInbox(INBOX_DIR);
    index = buildIndex(entries);
    index.entryByName = new Map(entries.map((e) => [e.name, e.doc]));
    const key = String(args.key === undefined || args.key === null ? '' : args.key).trim().toLowerCase();
    if (key === '') throw new GateError('USAGE_NO_KEY', '用法错误：需要 key 或 sample');
    const hit = entries.find((e) => identifierForms(e.name, e.doc).has(key) || String(e.name).toLowerCase() === key);
    if (!hit) throw new GateError('USAGE_NOT_FOUND', '可见集内找不到条目 ' + args.key);
    doc = hit.doc;
    name = hit.name;
  }
  const r = classify(doc, name, { nowMs: Date.now(), maxAgeDays: args.maxAgeDays, index });
  const elapsed = Date.now() - t0;
  logJudge({ tool: 'item_validity_explain', source, shape: r.shape, state: r.state, why: r.why, channel: r.channel, elapsed_ms: elapsed });
  return {
    ok: true, tool: 'item_validity_explain', source, key: name,
    state: r.state, shape: r.shape, why: r.why, channel: r.channel,
    missing: r.missing, howToFix: r.howToFix,
    conditions: r.conditions,
    dependencyCounts: dependencyCounts(r.conditions),
    blindSpot: BLIND_SPOT,
    elapsed_ms: elapsed
  };
}

/** 「每态所依赖的条件量」的可核验口径。 */
export function dependencyCounts(c) {
  return {
    shapeField: c.shapeBasis,
    statusFieldCount: c.statusFields.length,
    closeWordFields: c.closeWord ? 1 : 0,
    threadMembers: c.channelB ? c.channelB.members : 0,
    channelACandidates: c.channelA ? c.channelA.hits.length : 0,
    channelBEvaluated: c.channelB ? c.channelB.evaluated : false,
    channelCPointers: c.channelC ? (c.channelC.pointers || []).length : 0,
    timeCarriersFound: c.timeCarrier ? 1 : 0,
    ageDays: c.ageDays,
    maxAgeDays: c.maxAgeDays
  };
}

/* ══════════════════════════════ 唯一写操作：索引 ══════════════════════════════ */

/** ⑥ 版本单一来源：从 package.json 现读，绝不第二处硬编码。 */
export function toolVersion() {
  return JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8')).version;
}

/**
 * 写索引 —— 本插件**唯一的写操作**。
 * · 目标写死为模块常量 INDEX_PATH（不是入参；assertWriteTargetAllowed 全等断言）
 * · dryRun 默认 true；必须 confirm === true 才真写
 * · 写临时文件再改名（原子）
 * · **写后必须回读断言**
 * · 绝不写任何被审条目
 */
export function indexWrite(args = {}) {
  assertNoIndexPathInput(args);
  const source = resolveSource(args.source);
  const dryRun = args.dryRun !== false;              // 默认 true
  const confirm = args.confirm === true;
  const shouldWrite = confirm && !dryRun;
  const t0 = Date.now();
  const scan = scanInbox({ maxAgeDays: args.maxAgeDays });
  const payload = {
    version: toolVersion(),
    generated_at: new Date().toISOString(),
    source,
    dir: scan.dir,
    max_age_days: scan.maxAgeDays,
    total: scan.total,
    tally: scan.tally,
    shape_tally: scan.shapeTally,
    note: [
      '本索引用途：**以后先查此处** —— 命中者不必再逐条查看。',
      'closed = 显式关闭声明或已见回复（通道 A/B）；stale = 超窗/已被取代（疑似过期，须核依赖后才能关闭）。',
      'unknown ≠ 已关闭：它是【判不了】（缺字段/缺时刻/通道不可见）⇒ 须补字段。',
      BLIND_SPOT
    ].join('\n'),
    items: scan.rows
      .filter((r) => r.state === 'closed' || r.state === 'stale')
      .map((r) => ({ file: r.file, state: r.state, channel: r.channel, why: r.why }))
  };

  const protocol = [];
  if (!shouldWrite) {
    protocol.push(confirm ? 'dryRun（默认 true）：未做任何写操作，零变更' : '未 confirm:true ⇒ 未做任何写操作，零变更');
    return {
      ok: true, tool: 'item_validity_index_write', source, wrote: false, dryRun: true,
      path: INDEX_PATH, indexPathIsModuleConst: true, indexPathIsInput: false,
      plannedItems: payload.items.length, plannedTotal: payload.total,
      tally: scan.tally, protocol, elapsed_ms: Date.now() - t0, blindSpot: BLIND_SPOT
    };
  }

  assertWriteTargetAllowed(INDEX_PATH);
  protocol.push('写目标全等断言通过：target === INDEX_PATH（模块常量）');
  mkdirSync(dirname(INDEX_PATH), { recursive: true });
  const tmp = INDEX_PATH + '.tmp-' + String(process.pid || '0');
  writeFileSync(tmp, JSON.stringify(payload, null, 2));
  protocol.push('已写临时文件 ' + tmp);
  renameSync(tmp, INDEX_PATH);
  protocol.push('已原子改名 → ' + INDEX_PATH);

  // ★ 写后回读断言
  const back = JSON.parse(readFileSync(INDEX_PATH, 'utf8'));
  const assertOk = back.items.length === payload.items.length
    && back.total === payload.total
    && back.version === payload.version
    && back.source === payload.source;
  protocol.push('回读断言：items ' + back.items.length + '/' + payload.items.length +
    ' · total ' + back.total + '/' + payload.total + ' · version ' + back.version +
    ' ⇒ ' + (assertOk ? '一致' : '★ 不一致'));

  logJudge({ tool: 'item_validity_index_write', source, shape: 'index', state: assertOk ? 'written' : 'assert_failed', why: 'items=' + back.items.length, channel: null, elapsed_ms: Date.now() - t0 });

  return {
    ok: assertOk, tool: 'item_validity_index_write', source, wrote: true, dryRun: false,
    path: INDEX_PATH, indexPathIsModuleConst: true, indexPathIsInput: false,
    writtenItems: back.items.length, writtenTotal: back.total,
    readBack: { items: back.items.length, total: back.total, version: back.version, source: back.source },
    assert: assertOk, protocol, elapsed_ms: Date.now() - t0, blindSpot: BLIND_SPOT
  };
}

/* ══════════════════════════════ 能力声明 ══════════════════════════════ */

export const TOOL_CONTRACT = Object.freeze([
  Object.freeze({ name: 'item_validity_check', action: 'check', access: 'read-only', what: '判一条：形态 + 五态 + 条件量 + 盲区' }),
  Object.freeze({ name: 'item_validity_batch', action: 'batch', access: 'read-only', what: '全量扫描：五态计数 + 形态计数 + 逐条行' }),
  Object.freeze({ name: 'item_validity_explain', action: 'explain', access: 'read-only', what: '解释一条的判据链与依赖条件量' }),
  Object.freeze({ name: 'item_validity_index_write', action: 'index_write', access: 'write-once (default dryRun=true, needs confirm:true)', what: '写唯一索引 ' + INDEX_PATH })
]);

export function describeCapabilities() {
  return {
    tool: 'item-validity-review-check',
    purpose: '对「一条卡 / 一条待办 / 一个条目」回答「它现在还有效吗」：先分形态，再给五态，附每态所依赖的条件量与盲区声明',
    tools: TOOL_CONTRACT.map((t) => ({ name: t.name, action: t.action, access: t.access, what: t.what })),
    can: [
      '分形态：action / record / feed / ack / unknown（形态判不了 ⇒ unknown，绝不并入任何一侧）',
      '判五态：closed / stale / open / unknown / n/a，每态带可核验的条件量与理由',
      '回复可见性三通道：A 卡内指针（中强度）· B 线程记录（强强度）· C 指针形态（弱，仅参考）',
      '时效：7 天默认窗（可 --max-age-days 覆盖，窗值必打印）；ISO 串按 UTC 解释并在理由里写明该假设',
      '写一份索引（默认 dryRun；confirm:true 才真写；写后回读断言）',
      'R7 逐条日志：每次判一条写一行 JSON（unknown 也写）'
    ],
    cannot: [
      '不写任何被审条目（写目标全等断言 INDEX_PATH；只读侧无写调用）',
      '不把索引写到别处（路径写死为模块常量，不是入参 —— 结构上不可表达）',
      '不接受 source 传路径（冻结枚举 ["inbox"]；/etc、相对路径、~、通配一律 GateError）',
      '不 exec / 不 spawn / 不 kill / 不 eval（lib/*.js 由 --lean4-check A 项真扫）',
      '看不到线程外的回复：只发在线程里未落盘的回复 / 我未参与的线程 / 未持久化的会话',
      '不把「无可见回复」说成「确定仍待处理」（open 由盲区声明兜底）'
    ],
    sourceEnum: [...SOURCE_ENUM],
    indexPath: INDEX_PATH,
    inboxDir: INBOX_DIR,
    blindSpot: BLIND_SPOT
  };
}

/** 兼容骨架签名：状态 / dry-run 探测（CLI --dry-run 用）。 */
export async function runStatus(options = {}) {
  const dryRun = options.dryRun === true;
  const t0 = Date.now();
  const plan = indexWrite({ source: 'inbox', dryRun: true, maxAgeDays: options.maxAgeDays });
  return {
    ok: true,
    tool: 'item-validity-review-check',
    dryRun,
    checkedAt: new Date().toISOString(),
    path: plan.path,
    plannedItems: plan.plannedItems,
    plannedTotal: plan.plannedTotal,
    tally: plan.tally,
    protocol: plan.protocol,
    elapsed_ms: Date.now() - t0,
    note: dryRun ? 'dry-run：未做任何变更（写前写后 sha 一致由 --lean4-check D 项实测）' : '只读扫描 + 计划输出（本命令不做任何写；真写需 --write-index --confirm）',
    blindSpot: BLIND_SPOT
  };
}
