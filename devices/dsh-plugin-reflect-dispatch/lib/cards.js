/**
 * cards.js — 归属判定 + 定制卡生成（业务内核，无危险原语）
 * =============================================================================
 * 核心设计意图：**卡片必须按"它今天真正做了什么"定制，否则智能体只会写套话。**
 * 所以这里做两件别人容易糊过去的事：
 *   ① 归属判定可解释：每条事件对每个目标都给出 score 与 via（凭哪条 resources 命中的），
 *      卡里把它印出来 —— 让被派卡的人能自己判断"这条到底算不算我的"。
 *   ② 四个问题各带**该目标自己的上下文**（动作分布、可疑事件号、自动检索到的候选规则号），
 *      而不是四句通用问句。
 * 归属不上的事件**如实报告**（unassigned），不硬塞给谁，也不静默丢弃。
 */
import path from 'node:path';
import { findRuleCandidates } from './profiles.js';

/* ══════════════════════ 资源字符串规范化 ══════════════════════ */

const PATHISH_EXT = /\.(js|mjs|cjs|ts|py|json|md|yml|yaml|db|html|css|sh|txt|jsonl|log|plist)$/i;

/** 把 profile 里杂乱的 resources 字符串拆成可匹配的原子。 */
export function normalizeResource(raw, home) {
  const out = [];
  let s = String(raw ?? '').trim();
  if (!s) return out;
  s = s.replace(/^[-*]\s+/, '');
  // 拆并列项："store:N / im_window:N"、"A + B"
  const parts = s.split(/\s+\/\s+|\s+\+\s+/);
  for (let part of parts) {
    part = part.trim();
    // 去掉括号注释（中英文）
    part = part.replace(/[（(][^）)]*[）)]/g, '').trim();
    // 去掉尾部修饰词
    part = part.replace(/(读写|只读|共享写|共享|专属维护|可写|只读参考|独占写|只读\+?|写|读)$/u, '').trim();
    part = part.replace(/^mod:/, '').replace(/^file:/, '').replace(/^dir:/, '').trim();
    if (!part) continue;

    // 占位符通配：`store:N` / `im_window:N` → 视为前缀（只看前缀，不把 N 当字面量）。
    // ★ 必须放在 ns 解析**之前**：否则 `im_window:N` 会被拆成 ns=im_window / value=N，
    //   前缀信息就丢了（首跑时 E008 因此漏判）。
    const ph = part.match(/^(.+:)N$/);
    if (ph) { out.push({ kind: 'prefix', value: ph[1], ns: null, raw: String(raw) }); continue; }
    const nsMatch = part.match(/^([A-Za-z][A-Za-z0-9_-]*):(?!\/\/)(.+)$/);
    if (nsMatch) {
      const ns = nsMatch[1].toLowerCase();
      let val = nsMatch[2].trim().replace(/^['"]|['"]$/g, '');
      if (val.endsWith('/*')) { out.push({ kind: 'prefix', value: val.slice(0, -1), ns, raw: String(raw) }); continue; }
      out.push({ kind: 'ns', value: val, ns, raw: String(raw) });
      continue;
    }
    if (part.startsWith('~')) {
      const v = path.join(home, part.slice(1)).replace(/\/$/, '');
      out.push({ kind: 'path', value: v, ns: null, tail: homeTail(v, home), raw: String(raw) });
      continue;
    }
    if (part.startsWith('/')) {
      const v = part.replace(/\/$/, '');
      out.push({ kind: 'path', value: v, ns: null, tail: homeTail(v, home), raw: String(raw) });
      continue;
    }
    if (part.includes('/') || PATHISH_EXT.test(part)) {
      out.push({ kind: 'rel', value: part.replace(/^\.\//, '').replace(/\/$/, ''), ns: null, raw: String(raw) });
      continue;
    }
    out.push({ kind: 'token', value: part, ns: null, raw: String(raw) });
  }
  return out;
}

/** 路径深度（段数）：用于给"宽泛容器资源"降权。 */
export function depth(p) {
  return String(p).split('/').filter(Boolean).length;
}

/**
 * 绝对路径 → 去掉 $HOME 前缀的相对尾部。
 * ★ 为什么必须做（2026-09-10 与兄弟组件 reflect-collect 对接时发现）：
 *   collect 产出的 **事件 path 是相对路径**（如 `dsh-collab/scripts/verify-ui.py`），
 *   而 profile 里的 resources 多为**绝对路径**（`file:/Users/coreyleung/dsh-collab/scripts/verify-ui.py`）。
 *   不归一 → 精确/前缀规则一条都不命中，只剩 basename 弱匹配，
 *   真实数据上的归属会大面积退化（"门太窄也会漏掉自己人"）。
 */
function homeTail(absPath, home) {
  const h = String(home || '').replace(/\/$/, '');
  const p = String(absPath || '');
  if (h && p.startsWith(h + '/')) return p.slice(h.length + 1);
  return null;
}

/**
 * 标识符归一：`im_sessions` 与 `im-sessions-timeout-contract` 说的其实是同一个东西。
 * 实测（2026-09-10 首跑）：不做这一步时，黑板键用连字符、profile 资源用下划线 →
 * 「灯塔」的 E007 完全漏判成 unassigned。归一后仍要求 ≥6 字符，避免短词乱撞。
 */
function normIdent(s) {
  return String(s).toLowerCase().replace(/[-_]/g, '');
}
function identHit(hay, needle) {
  const n = normIdent(needle);
  if (n.length < 6) return false;
  return normIdent(hay).includes(n);
}

function basename(p) {
  const segs = String(p).split('/').filter(Boolean);
  return segs.length ? segs[segs.length - 1] : String(p);
}
function stem(b) {
  return String(b).replace(/\.[A-Za-z0-9]{1,6}$/, '');
}

/* ══════════════════════ 归属判定 ══════════════════════ */

/**
 * 「宽泛容器资源」降权：深度差越大，说明这条资源只是"装着一切的大目录"，
 * 对"这件事到底该问谁"几乎没有信息量。
 * 反例（真实数据里就有）：某智能体把 `~/dsh-collab/` 登记为自己的资源 →
 * 若不降权，它对 **当天所有** collab 文件事件都会拿到 92 分，卡片就退化成垃圾。
 * 降权后仍在 `via` 里如实标注（`路径前缀（深度差 N，已降权）`），不隐藏。
 */
function prefixScore(evPath, resValue, base) {
  const d = depth(evPath) - depth(resValue) - 1;
  if (d <= 0) return { score: base, penalty: 0 };
  const score = Math.max(30, base - d * 15);
  return { score, penalty: d };
}

/**
 * 单条事件对单个原子资源的匹配分（0 = 不匹配）。
 * 每档同时返回 `level`（归属层级），供 attributeEvents 做层级裁决：
 *   specific = 这条资源**就是**那个东西（精确路径 / 相对路径全尾 / 键命中 / `X:N` 占位前缀 / 显式命名空间）
 *   dir      = 这条资源**装着**那个东西（目录前缀 / 相对路径包含；宽泛容器按深度差 ×15 降权）
 *   weak     = 只命中名字的一部分（basename / 词干 / 描述关键词）
 */
function scoreAtom(ev, atom, haystack) {
  const evPath = ev.path ? String(ev.path).replace(/^file:/, '') : '';
  const evKey = ev.key ? String(ev.key) : '';
  const text = haystack.toLowerCase();

  if (atom.kind === 'path') {
    if (!evPath) return { score: 0 };
    // ① 事件 path 是绝对值 → 与资源路径直接比
    if (evPath.startsWith('/')) {
      if (evPath === atom.value) return { score: 100, via: '路径精确', level: 'specific' };
      if (evPath.startsWith(atom.value + '/')) {
        const { score, penalty } = prefixScore(evPath, atom.value, 92);
        return { score, via: penalty ? `路径前缀（深度差 ${penalty}，已降权）` : '路径前缀', level: 'dir' };
      }
    } else if (atom.tail) {
      // ② 事件 path 是相对路径（兄弟组件 collect 的实际产出）→ 与去 $HOME 前缀的尾部比
      const t = atom.tail;
      if (evPath === t) return { score: 96, via: '路径精确（相对/绝对归一）', level: 'specific' };
      if (evPath.endsWith('/' + t)) return { score: 88, via: '路径尾匹配（相对/绝对归一）', level: 'specific' };
      if (evPath.startsWith(t + '/')) {
        const { score, penalty } = prefixScore(evPath, t, 80);
        return { score, via: penalty ? `路径包含（归一，深度差 ${penalty}，已降权）` : '路径包含（归一）', level: 'dir' };
      }
    }
    if (basename(evPath) === basename(atom.value)) return { score: 74, via: '路径 basename', level: 'weak' };
    const st = stem(basename(atom.value));
    if (identHit(basename(evPath), st)) return { score: 58, via: '路径词干', level: 'weak' };
    return { score: 0 };
  }
  if (atom.kind === 'rel') {
    const v = atom.value.replace(/\/$/, '');
    if (evPath && evPath === v) return { score: 96, via: '相对路径精确', level: 'specific' };
    if (evPath && evPath.endsWith('/' + v)) return { score: 88, via: '相对路径尾匹配', level: 'specific' };
    if (evPath && evPath.includes('/' + v + '/')) {
      const { score, penalty } = prefixScore(evPath, v, 80);
      return { score, via: penalty ? `相对路径包含（深度差 ${penalty}，已降权）` : '相对路径包含', level: 'dir' };
    }
    if (evKey && (evKey === v || evKey.startsWith(v + '/') || evKey.endsWith('/' + v))) return { score: 82, via: '键命中相对路径', level: 'specific' };
    if (basename(evPath || evKey) === basename(v)) return { score: 72, via: 'basename 命中', level: 'weak' };
    const st = stem(basename(v));
    if (identHit(basename(evPath || evKey), st) || (evKey && identHit(evKey, st))) return { score: 60, via: '词干命中（标识符归一）', level: 'weak' };
    return { score: 0 };
  }
  if (atom.kind === 'prefix') {
    const v = atom.value;
    if (evKey && evKey.startsWith(v)) return { score: 90, via: `键前缀（${v}*）`, level: 'specific' };
    if (evPath && evPath.startsWith(v)) return { score: 90, via: `路径前缀（${v}*）`, level: 'specific' };
    if (text.includes(v.toLowerCase())) return { score: 62, via: `文本命中前缀（${v}*）`, level: 'weak' };
    return { score: 0 };
  }
  if (atom.kind === 'ns') {
    const v = atom.value;
    if (v.length < 3 && atom.ns === 'store') {
      // 短数字（store:8）必须显式形态，否则 "8" 会命中一切
      const pats = [`store:${v}`, `store_id=${v}`, `storeid=${v}`, `store ${v}`, `store=${v}`];
      const hit = pats.find((p) => text.includes(p));
      return hit ? { score: 86, via: `显式形态 ${hit}`, level: 'specific' } : { score: 0 };
    }
    const full = `${atom.ns}:${v}`.toLowerCase();
    if (text.includes(full)) return { score: 85, via: `命名空间命中 ${atom.ns}:`, level: 'specific' };
    if (v.length >= 4 && text.includes(v.toLowerCase())) return { score: 66, via: '命名空间值命中', level: 'weak' };
    return { score: 0 };
  }
  if (atom.kind === 'token') {
    const v = atom.value.toLowerCase();
    if (v.length >= 4 && text.includes(v)) return { score: 55, via: '描述关键词（整词）', level: 'weak' };
    // 多词资源（如 "meituan-multi 脚本与发布工具"）按子词再试一次（弱信号）
    const subs = String(atom.value).split(/\s+/).map((s) => s.toLowerCase()).filter((s) => s.length >= 4);
    for (const s of subs) if (text.includes(s)) return { score: 45, via: `描述关键词（子词 ${s}）`, level: 'weak' };
    return { score: 0 };
  }
  return { score: 0 };
}

/**
 * 归属层级裁决（首跑后加，2026-09-10）：
 * 同一事件的多个候选按 **specific > dir > weak** 取最高非空层级，其余进 `suppressed`。
 *
 * 为什么需要：真实档案里多个智能体把 `~/dsh-collab/scripts`、`~/dsh-collab/` 这类
 * **共享大目录**登记成了自己的 resources（实测 4 个会话都这样）。若不裁决，
 * 「审查工具链」精确改了 `scripts/verify-ui.py` 这件事，会同时派给那 4 个"只是目录装着它"的会话，
 * 它们的卡片就全是别人的事 —— 那正是本工具要消灭的"套话卡"。
 * 裁决是**精确优先**（precision over recall）：宁可少派，也不派无关的卡。
 * 被压下的候选**全部记入 suppressed 并落台账**，不静默丢弃。
 */
const LEVEL_RANK = Object.freeze(['specific', 'dir', 'weak']);

/**
 * 「容器资源」实测降级（真实数据跑出来的规则，2026-09-10）：
 * 一个原子若在**当天事件集**里命中超过 10 条**且**占比 >5%，那它不是"归属关系"，
 * 而是一个**容器**（把 `~/dsh-collab/` 登记成自己的资源，就会命中当天所有 collab 文件事件）。
 * 实测：真实 1692 条事件里，`~/dsh-collab/` 命中 271 条（16%）—— 卡片取 top-8 会全是别人的事。
 * 处理：把该原子的层级从 `dir` 降为 `weak` 并封顶 45 分（< 默认阈值 50 → 实际不参与归属），
 * 但同时**记入 broadResources 并写进卡片**，让本人知道"你的资源登记得太宽"——这是可回填的观察，
 * 不是悄悄丢掉。占比阈值用**实测数据**算，不是拍脑袋的常量。
 */
const BROAD_MIN_HITS = 10;
const BROAD_RATIO = 0.05;

/**
 * 归属判定：把事件分给"该问谁"。
 * @returns {{perAgent:Map, suppressed:Map, unassigned:Array, all:Array, broadResources:Map, stats:object}}
 */
export function attributeEvents(events, targets, opts = {}) {
  const home = opts.home;
  const threshold = Number.isFinite(opts.threshold) ? opts.threshold : 50;
  const index = targets.index;
  const agents = index.list();
  const atomsByAgent = new Map();
  for (const a of agents) {
    const atoms = [];
    for (const r of a.resources || []) for (const atom of normalizeResource(r, home)) atoms.push(atom);
    atomsByAgent.set(a.agentId, atoms);
  }

  // ── 预扫：统计每个 (agent, atom) 的**包含级**命中数，用于容器降级 ──
  // 容器只在"包含"语义下才可能出现（精确命中天生稀有），故只统计 dir 级，省一半开销。
  const dirHits = new Map();          // `${agentId}#${atomIdx}` → count
  const hitSample = new Map();
  const preHay = events.map((ev) => [ev.path, ev.key, ev.desc, ev.source, ev.kind].filter(Boolean).join(' '));
  for (let i = 0; i < events.length; i++) {
    for (const a of agents) {
      const atoms = atomsByAgent.get(a.agentId) || [];
      for (let k = 0; k < atoms.length; k++) {
        const s = scoreAtom(events[i], atoms[k], preHay[i]);
        if (s.level === 'dir') {
          const key = `${a.agentId}#${k}`;
          dirHits.set(key, (dirHits.get(key) || 0) + 1);
          if (!hitSample.has(key)) hitSample.set(key, events[i].id);
        }
      }
    }
  }
  const broad = new Map();            // key → {count, ratio}
  for (const [key, count] of dirHits) {
    if (count > BROAD_MIN_HITS && count / events.length > BROAD_RATIO) broad.set(key, { count, ratio: count / events.length });
  }

  const broadResources = new Map(agents.map((a) => [a.agentId, []]));
  for (const [key, info] of broad) {
    const [agentId, idxStr] = key.split('#');
    const atom = (atomsByAgent.get(agentId) || [])[Number(idxStr)];
    if (!atom) continue;
    broadResources.get(agentId).push({
      resource: atom.raw, atom: `${atom.kind}:${atom.value}`, matched: info.count,
      ratio: Number((info.ratio * 100).toFixed(1)), sampleEvent: hitSample.get(key) || null
    });
  }
  for (const list of broadResources.values()) list.sort((a, b) => b.matched - a.matched);

  const perAgent = new Map(agents.map((a) => [a.agentId, []]));
  const suppressed = new Map(agents.map((a) => [a.agentId, []]));
  const unassigned = [];
  const all = [];

  for (const ev of events) {
    const haystack = [ev.path, ev.key, ev.desc, ev.source, ev.kind].filter(Boolean).join(' ');
    const cands = [];
    for (const a of agents) {
      const atoms = atomsByAgent.get(a.agentId) || [];
      let best = { score: 0 };
      for (let k = 0; k < atoms.length; k++) {
        const atom = atoms[k];
        let s = scoreAtom(ev, atom, haystack);
        if (s.level === 'dir' && broad.has(`${a.agentId}#${k}`)) {
          const info = broad.get(`${a.agentId}#${k}`);
          s = { score: Math.min(45, s.score), via: `${s.via}｜容器资源已降级（命中 ${info.count} 条 / ${(info.ratio * 100).toFixed(1)}%）`, level: 'weak' };
        }
        if (s.score > best.score) best = { ...s, resource: atom.raw, atom: `${atom.kind}:${atom.value}` };
      }
      if (best.score >= threshold) cands.push({ agentId: a.agentId, shortKey: a.shortKey, score: best.score, via: best.via, level: best.level, resource: best.resource, atom: best.atom });
    }
    const topLevel = LEVEL_RANK.find((lv) => cands.some((c) => c.level === lv)) || null;
    const kept = cands.filter((c) => c.level === topLevel).sort((x, y) => y.score - x.score);
    const dropped = cands.filter((c) => c.level !== topLevel);

    const rec = { event: ev, hits: kept, suppressed: dropped, level: topLevel, candidateCount: cands.length };
    all.push(rec);
    if (!kept.length) unassigned.push(ev);
    for (const h of kept) perAgent.get(h.agentId).push({ event: ev, score: h.score, via: h.via, level: h.level, resource: h.resource, atom: h.atom, shared: kept.length > 1 });
    for (const d of dropped) suppressed.get(d.agentId).push({ event: ev, score: d.score, via: d.via, level: d.level, resource: d.resource, keptBy: kept.map((k) => k.shortKey) });
  }

  return {
    perAgent, suppressed, unassigned, all, broadResources,
    stats: {
      events: events.length, unassigned: unassigned.length,
      suppressedTotal: [...suppressed.values()].reduce((n, v) => n + v.length, 0),
      broadResourcesTotal: [...broadResources.values()].reduce((n, v) => n + v.length, 0)
    }
  };
}

/** 每个目标取 top-N：按 分数 → 时间倒序。 */
export function pickForAgent(matched, maxEvents) {
  const ts = (e) => { const t = Date.parse(e.event.ts || ''); return Number.isFinite(t) ? t : 0; };
  const sorted = matched.slice().sort((a, b) => (b.score - a.score) || (ts(b) - ts(a)));
  return sorted.slice(0, Math.max(1, maxEvents));
}

/* ══════════════════════ 上下文素材（避免套话的关键） ══════════════════════ */

function compactTime(ts) {
  const t = Date.parse(String(ts || ''));
  if (!Number.isFinite(t)) return String(ts || '—').slice(0, 19);
  const d = new Date(t);
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function eventLine(ev) {
  return ev.path ? `\`${ev.path}\`` : (ev.key ? `\`${ev.key}\`` : `\`${ev.id}\``);
}

/** 动作分布（Q1 的上下文）。 */
export function actionDistribution(matched) {
  const bySource = new Map();
  const byResource = new Map();
  for (const m of matched) {
    const s = `${m.event.source}/${m.event.kind || 'event'}`;
    bySource.set(s, (bySource.get(s) || 0) + 1);
    const r = m.resource || '（无依据）';
    byResource.set(r, (byResource.get(r) || 0) + 1);
  }
  const top = (m, n) => [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `${k}×${v}`).join('、') || '—';
  return { sources: top(bySource, 4), resources: top(byResource, 4) };
}

/** 规则关键词：路径词干 + 描述里的实词。 */
export function ruleKeywords(matched) {
  const kws = new Set();
  for (const m of matched) {
    const ev = m.event;
    if (ev.path) {
      kws.add(basename(ev.path));
      kws.add(stem(basename(ev.path)));
    }
    if (ev.key) kws.add(basename(ev.key));
    if (ev.source) kws.add(String(ev.source));
    for (const tok of String(ev.desc || '').split(/[\s,，。:：;；、()（）\[\]【】/|"'`]+/)) {
      const t = tok.trim();
      if (t.length >= 3 && t.length <= 16) kws.add(t);
    }
  }
  for (const w of ['插件', '黑板', '会话', '规则', '门禁', '重启', '验证', '审计', '派发', '反思', '事件', '日志']) kws.add(w);
  return [...kws];
}

/* ══════════════════════ 卡片正文（含设备维度 · v1.1） ══════════════════════ */

/**
 * 回填 schema。**跨设备层新增字段**（设计文档 §10.5 / §10.6）：
 *   · `device` / `origin_device` —— 区分"采集者"与"文件在哪"（同步盘会让同一文件在两台设备都可见）
 *   · `device_scope` —— ★ 第 5 问的答案（普遍 / 仅本设备 / 不确定）
 *   · `plugin_version` —— 回填补版本，harvest 才能检出设备间版本漂移
 *   · `evidence.ts` 与 `evidence.collected_at` **分开标** —— Φ13 证据有时点：
 *     前者=该设备的本地时间（你自己的钟），后者=采集/提交时刻（采集者的钟）。两台设备的钟可能不同步。
 */
export function replySchema(agentFullId, dateIso, device) {
  return {
    agent: agentFullId,
    device,
    origin_device: device,
    date: dateIso,
    plugin_version: '1.1.0',
    items: [
      {
        id: 'R1',
        event_ref: 'E012',
        pit: '具体事件描述',
        lesson: '一句话抽象',
        related_rule: 'R012 / phi-cost / 无',
        suggestion: { type: '新增|修订|转规范|无需动作', detail: '...', reason: '...' },
        device_scope: '普遍|仅本设备|不确定',
        evidence: {
          ts: '...（你设备的本地时间）',
          collected_at: '...（采集/提交时刻，与上者分开标）',
          cmd: '...',
          output: '...（片段）'
        }
      }
    ],
    declined: false
  };
}

/** 第 5 问的冻结三选一（与 gate.SUGGESTION_TYPES 同一条纪律：schema 即门）。 */
export const DEVICE_SCOPE_TYPES = Object.freeze(['普遍', '仅本设备', '不确定']);

function h(level, text) { return `${'#'.repeat(level)} ${text}`; }

/**
 * 生成一个智能体的卡片正文段（标题层级可调：独立成卡时 2，嵌进设备合并卡时 3）。
 *
 * `crossDevice` 是跨设备层的核心增量（设计文档 §10.7）：
 *   同一资源/关键词在**别的设备**上也出现了事件 → 独立复现 = 更强的信号。
 *   有了它，第 5 问就不是空问句，而是有具体线索可对照。
 */
export function buildAgentSection(input, opts = {}) {
  const { agent, picked, matchedAll, eventTotal, unassignedCount, dateCompact, dateDash, window, version,
    notice, emit, indexSource, ruleCands, topicNote, suppressedForMe, broadResourcesForMe, device, deviceNote } = input;
  const level = opts.level || 2;
  const L = [];
  const role = String(agent.role || '').replace(/\s+/g, ' ').trim();
  const roleShort = role.length > 110 ? role.slice(0, 110) + '…' : role;
  const dist = actionDistribution(matchedAll);
  const ids = picked.map((m) => m.event.id);
  const cross = input.crossDevice || { devices: [], totalOther: 0 };

  L.push(h(level, `① 你的今日任务（按归属实摘：${picked.length}/${eventTotal} 条事件与你相关）`));
  L.push('');
  L.push(`你登记的职责：${roleShort || '（档案里 role 为空 —— 这本身就是一条可回填的观察）'}`);
  L.push('');
  L.push('| # | 事件 | 时间 | 来源 | 归属依据（凭什么算你的） | 事实 |');
  L.push('|---|------|------|------|--------------------------|------|');
  picked.forEach((m, i) => {
    const ev = m.event;
    let desc = String(ev.desc || '').replace(/\|/g, '\\|').replace(/\s+/g, ' ').slice(0, 90) || '（上游未给 desc）';
    // 跨设备污染提示（设计文档 §10.5）：事件带 origin_device（**采集者**），不是"文件在哪"
    if (ev.origin_device && ev.origin_device !== device) desc = `⚠️origin=${ev.origin_device} ${desc}`;
    L.push(`| ${i + 1} | ${ev.id} | ${compactTime(ev.ts)} | ${ev.source}${ev.kind ? '/' + ev.kind : ''} | \`${m.resource}\`（${m.via}，score ${m.score}${m.shared ? '，**与他方共享**' : ''}） | ${desc} |`);
  });
  L.push('');
  const withCollected = picked.filter((m) => m.event.collected_at);
  if (withCollected.length) {
    L.push(`- ⧗ 上游事件已带 **Φ13 双时点**（本工具原样保留，不覆盖）：${withCollected.slice(0, 3).map((m) => `${m.event.id}: ts=${m.event.ts || '—'} / collected_at=${m.event.collected_at}`).join('；')}${withCollected.length > 3 ? ` …共 ${withCollected.length} 条` : ''}`);
    L.push('  - 口径：`ts` = 该事件的**设备本地时间**；`collected_at` = **采集时刻**。两者的钟可能不同步，别混用（Φ13）。');
  } else {
    L.push('- ⧗ 本设备事件流**未带** `collected_at`（采集时刻）字段 → 回填时请自己把「设备本地时间」与「提交时刻」**分开标**（Φ13 双时点）。');
  }
  const crossOrigin = picked.filter((m) => m.event.origin_device && m.event.origin_device !== device);
  if (crossOrigin.length) {
    L.push(`- ⚠️ 其中 **${crossOrigin.length}** 条事件的 \`origin_device\` 不是你（${[...new Set(crossOrigin.map((m) => m.event.origin_device))].join(', ')}）→ 说明它是在别处采集、经同步盘/黑板可见的：**别把它算成"你这边发生的事"**（§10.5 跨设备污染）。`);
  }
  L.push(`- 你的**完整**归属事件共 **${matchedAll.length}** 条，本卡按归属强度取前 ${picked.length} 条；其余：${matchedAll.slice(picked.length).map((m) => m.event.id).join(', ') || '（无）'}`);
  L.push(`- 本设备（\`${device}\`）事件流共 **${eventTotal}** 条，其中 **${matchedAll.length}** 条归属到你；**${unassignedCount}** 条未归属到任何目标（如实报告，**没有**硬塞给谁）。`);
  L.push(`- 你的动作分布：${dist.sources}；归属资源集中在：${dist.resources}`);
  L.push(`- 设备：**${device}**（${deviceNote || '—'}）· 档案来源：\`${indexSource}\``);
  L.push('- 归属层级裁决：**specific > dir > weak**；出现「具体归属」就不再向下兼容。specific：精确 100 / 相对路径尾 88 / 键命中 82 / X:N 占位前缀 90 / 显式命名空间 85-86；dir：路径前缀 92（宽泛容器按深度差 ×15 降权）；weak：basename 74 / 词干 60（标识符 - 与 _ 归一）/ 描述关键词 55-45');
  if (suppressedForMe && suppressedForMe.length) {
    const byId = suppressedForMe.map((s) => `${s.id}（${s.via}，score ${s.score} → 交给 ${(s.keptBy || []).join('/')}）`);
    L.push(`- ⚠️ 另有 **${suppressedForMe.length}** 条事件你只是**次强归属**，已被层级裁决压下（**如实告诉你，不静默**）：${byId.join('；')}`);
    L.push('  - 若你认为其中某条本该归你 → 请在 Q4 里给出你的资源依据（这属于「你的 resources 登记得不精确」这类可回填的观察）。');
  }
  if (broadResourcesForMe && broadResourcesForMe.length) {
    L.push(`- ⚠️ **你的 resources 里有 ${broadResourcesForMe.length} 条是「容器级」的**（实测：它在当天事件集里命中了远超"归属关系"应有量的事件）——已被自动降级，**未**用来给你派事件：`);
    for (const b of broadResourcesForMe) L.push(`  - \`${b.resource}\` — 命中 **${b.matched}** 条（占当天 **${b.ratio}%**，例：${b.sampleEvent || '—'}）`);
    L.push('  - 处置口径（**用实测占比算，不是我拍脑袋**）：命中 >10 条 **且** 占比 >5% → 判为容器，层级从 `dir` 降为 `weak`（≤45 分，低于阈值 50）→ 不参与归属。');
    L.push('  - 这**不是**你的锅，但是**最值得回填的一条**：把 `~/dsh-collab/` 这种"装着一切的大目录"拆成你真正独占的那几项（文件/表/端口/键前缀），下次的卡就会准得多。');
  }
  if (topicNote) L.push(`- 上游给的当日议题：${topicNote}`);
  L.push('');
  L.push(h(level, '② 请回填（5 问 · 每题附你今天的上下文）'));
  L.push('');
  L.push('**Q1 今天你踩了什么坑？**（具体到事件：什么动作、什么现象、怎么发现）');
  L.push(`- 你今天的动作集中在：${dist.sources}`);
  L.push(`- 归属资源集中在：${dist.resources}`);
  L.push(`- 请从 ① 里**点名事件号**（如 ${ids.slice(0, 3).join(' / ') || 'E0xx'}），写清三件事：你做了什么 → 出现什么现象 → **你怎么发现的**（哪条日志 / 哪个断言 / 谁提醒的）`);
  L.push('- 若你当天确实无事可说：允许填 `declined: true`，但**必须给理由**（写进 `pit`），不能空着。');
  L.push('');
  L.push('**Q2 教训是什么？**（一句话抽象，不要复述现象）');
  L.push(`- 反例（不算）：「改完 ${basename(picked[0]?.event?.path || '') || '那个文件'} 要记得再跑一次测试」——这是现象。`);
  L.push('- 正例（算）：「口径类改动必须在写入前用旧口径重算差异，否则错误会静默向下游传播」——这是抽象。');
  L.push(`- 对照你的事件 ${ids.slice(0, 2).join(' / ') || 'E0xx'} 想：**下次遇到同类情形，你会在哪一步改变动作？**`);
  L.push('');
  L.push('**Q3 有没有对应或冲突的现有规则？**（给规则号或哲学号；没有则说没有）');
  if (ruleCands && ruleCands.length) {
    L.push('- 规则账本 `rules-registry/RULES.md` 按你的事件关键词自动检索到的**候选**（供对照，允许判为无关）：');
    for (const c of ruleCands) L.push(`  - \`${c.id}\` — ${c.label.replace(/^[^\s]+\s*/, '')}（命中：${c.hit.join('、')}）`);
  } else {
    L.push('- 规则账本里**没有检索到**与你今天事件直接相关的规则 —— 那就如实写「无」；若你心里想到了某条，请写规则号。');
  }
  L.push('- 也请检查**冲突**：例「R035 说能热重启就不要杀框架，但我今天先杀了进程」——冲突比缺失更值钱。');
  L.push('');
  L.push('**Q4 你的建议**（**四选一**：`新增` / `修订` / `转规范` / `无需动作`）+ 理由');
  L.push(`- 你的上下文：${matchedAll.length} 条归属事件里，${dist.resources}`);
  L.push('- 提示：若现象可能重演 → `新增`；若有规则但口径/做法不对 → `修订`；若已稳定可复用 → `转规范`；若只是我多虑 → `无需动作`（**允许选它，诚实比产出量重要**）。');
  L.push('- 理由必须能指向具体事件号；只写「建议加强意识」这类**不算理由**。');
  L.push('');
  L.push(`**Q5 ★ 这个坑在你的设备/环境下是普遍的，还是特定于你这边？**（**三选一**：\`${DEVICE_SCOPE_TYPES.join('` / `')}\`）`);
  L.push('');
  L.push('> 为什么这一问是新增的核心价值：**不同设备上跑的是不同的任务、看的是不同的上下文**，');
  L.push('> 它们**独立**踩到同一个坑，说明这不是某条工作流的偶然，而是**系统性的**（设计文档 §10.7）。');
  L.push('> 跨设备复现，比同机多会话复现是**更强的信号**。');
  L.push('');
  if (cross.totalOther > 0) {
    L.push(`- ★ **跨设备线索（已实测到）**：你的事件特征词，在 **${cross.devices.length} 台别的设备**上也出现了 ${cross.totalOther} 条事件：`);
    for (const d of cross.devices) L.push(`  - \`${d.device}\`：${d.count} 条（例：${(d.sampleIds || []).join(', ')}）—— 归属依据 \`${d.resource}\``);
    L.push('- 若你确认这与你的坑是**同一个** → 第 5 问请选 `普遍`（这将把复现计数从"同机"升级为"跨设备"，是最有价值的信号）。');
    L.push('- 若看起来只是同名不同事 → 选 `仅本设备`，并顺手说明区别（这本身也是在纠正归属）。');
  } else {
    L.push('- 本次**没有**在别的设备上探测到同类事件（注意：这是"**没读到**"，不是"**不存在**" —— ');
    L.push('  别的设备可能没上报，或那台设备离线）。因此**不要**因为"只有我"就默认选 `仅本设备`；');
    L.push('  请按你自己的判断回答：如果这个坑**换一台设备、换一批任务也会遇到**，就选 `普遍`。');
  }
  L.push(`- 判断口径：问自己「换一台设备、换一批任务，同样的动作顺序会不会再踩一次？」会 → \`普遍\`；`);
  L.push('  只有当它明显依赖**你这边**特有的东西（本机路径、本机服务、本机凭据、你的特殊权限）时才选 `仅本设备`。');
  L.push('- 拿不准就选 `不确定` —— **允许不确定**，比硬猜一个答案有用。');
  L.push('');
  L.push(h(level, '③ 证据要求 ★（**无证据的回填视为无效**）'));
  L.push('');
  L.push('每条 `item` 必须同时带齐下列字段，缺一即该条**无效**：');
  L.push('');
  L.push('| 字段 | 要求 | 反例（会被判无效） |');
  L.push('|---|---|---|');
  L.push('| `evidence.ts` | 你**设备本地**的时间戳，或你日志里的时间 | `"今天"` / 空 |');
  L.push('| `evidence.collected_at` | **采集/提交时刻**，与上者**分开标**（Φ13：两台设备的钟可能不同步） | 与 `ts` 填同一个值 / 空 |');
  L.push('| `evidence.cmd` | 你**实际执行过**的命令或调用的工具名（含关键参数） | `"检查了一下"` |');
  L.push('| `evidence.output` | **真实输出片段 ≥1 行**（原样粘贴） | `"成功"` / `"正常"` / `"无报错"` |');
  L.push('');
  L.push('> 判定口径：`output` 里若只有结论词（成功/正常/没问题/已修复）而无具体文本，视同未给证据 —— 与 R030「无验证不陈述」同源。');
  L.push('> `ts` 与 `collected_at` 若填成同一个值，视同只给了时点的一半（Φ13：时点必须由测量行为本身产出）。');
  L.push('');
  L.push(h(level, '④ 回填格式（机器可读 JSON）'));
  L.push('');
  L.push('```json');
  L.push(JSON.stringify(replySchema(agent.agentId, dateDash, device), null, 2));
  L.push('```');
  L.push('');
  L.push('- `suggestion.type` 只能取 `新增|修订|转规范|无需动作`（工具侧冻结四选一，非法值会被 `SUGGESTION_INVALID` 拒绝）；');
  L.push(`- \`device_scope\` 只能取 \`${DEVICE_SCOPE_TYPES.join('|')}\`；`);
  L.push('- `event_ref` 必须是 ① 里出现过的事件 id（不在 ① 里的事件请写明来源）；`declined` 仅在当天确实无事可说时为 `true`；');
  L.push('- `plugin_version` 请填你**本机插件**的版本（harvest 用它检出设备间版本漂移）；`origin_device` 填**采集者**，不是"文件在哪"。');
  L.push('');
  L.push(h(level, '⑤ 回填去向'));
  L.push('');
  L.push(`- 写黑板（**中央板**）：\`${emit.replyKey}\`（PUT JSON，**写后立即回读确认**；400=写法非法 / 404=不存在，都不能当成功）`);
  L.push('- 或回投本会话。两者取其一即可，不要两边都写（防重复计数）。');
  L.push('');
  return L.join('\n');
}

/** 独立成卡的完整 markdown（落盘用）。 */
export function buildCard(input) {
  const { agent, dateDash, window, version, emit, device, deviceNote, eventsNote } = input;
  const L = [];
  L.push(`# 🎴 反思卡 · ${device}:${agent.shortKey} · ${dateDash}`);
  L.push('');
  L.push(`> 由 \`dsh-plugin-reflect-dispatch\` v${version} 生成 · 设备 **${device}** · 事件窗口 ${window.since || '—'} → ${window.until || '—'}`);
  L.push('> **本卡不是统一问卷**：① 的每条事件都是按你登记的 `resources` 从当天事件流里挑出来的；② 的每个问题各带你**自己**的上下文。');
  L.push(`> 设备视角：${deviceNote || '—'}${eventsNote ? ` · ${eventsNote}` : ''}`);
  L.push(`> 落盘：\`${emit.cardPath}\` · 派发：${emit.mode}${emit.boardKey ? ` · 中央板键 \`${emit.boardKey}\`` : ''}`);
  L.push('');
  L.push(buildAgentSection({ ...input, level: 2 }, { level: 2 }));
  L.push('---');
  L.push(`> 生成器：\`~/dsh-collab/devices/dsh-plugin-reflect-dispatch/\` · 归属可复核：跑 \`node cli.js --events <同一份 events.json> --json\` 看同一套 score/via`);
  L.push('');
  return L.join('\n');
}

/**
 * 设备级合并卡（**写中央板的那一张**）：
 * 一个设备一个 key `data/reflect/cards/<device>/<date>`，内含该设备各智能体的定制段。
 * 为什么合并：一台离线设备上线后**只需读一个键**就能拿到派给它的全部反思任务；
 * 分散成 N 个键会让"待投递队列"退化成"要 N 次轮询"。
 */
export function buildDeviceCard(input) {
  const { device, deviceNote, dateDash, version, window, agents, eventsNote, eventsKey, cardKey } = input;
  const L = [];
  L.push(`# 🎴 反思卡 · 设备 ${device} · ${dateDash}`);
  L.push('');
  L.push(`> 由 \`dsh-plugin-reflect-dispatch\` v${version} 生成（跨设备层）· 日期 ${dateDash}`);
  L.push(`> 本卡含 **${agents.length}** 个智能体的定制段（各段按该智能体的 \`resources\` 从**该设备当天的事件流**里实摘，非统一问卷）。`);
  L.push(`> 设备：**${device}**（${deviceNote || '—'}）${eventsNote ? ` · ${eventsNote}` : ''}`);
  L.push(`> 事件流键：\`${eventsKey}\` · 本卡键：\`${cardKey}\``);
  L.push('> 回填：写中央板 `' + (input.answersKey || '') + '`（写后**回读校验**）。');
  L.push('');
  L.push('## 目录');
  L.push('');
  agents.forEach((a, i) => {
    L.push(`${i + 1}. **${device}:${a.agent.shortKey}** — ${String(a.agent.role || '').replace(/\s+/g, ' ').slice(0, 70)} → 事件 ${a.picked.map((m) => m.event.id).join(', ')}`);
  });
  L.push('');
  L.push('> 找到你自己那一段：搜索 \`' + `## 你的段 · ${device}:` + '\`');
  L.push('');
  agents.forEach((a, i) => {
    L.push('---');
    L.push('');
    L.push(`## 你的段 · ${device}:${a.agent.shortKey}（${i + 1}/${agents.length}）`);
    L.push('');
    L.push(`> ${String(a.agent.role || '').replace(/\s+/g, ' ').slice(0, 150)}`);
    L.push('');
    L.push(buildAgentSection({ ...a, device, deviceNote, version, window, indexSource: input.indexSource, dateDash }, { level: 3 }));
  });
  L.push('---');
  L.push('');
  L.push(`> 生成器：\`~/dsh-collab/devices/dsh-plugin-reflect-dispatch/\` · 本卡由本机 dispatch 生成并 PUT 到中央板，**写入后已回读校验**`);
  L.push('');
  return L.join('\n');
}
