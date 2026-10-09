/**
 * profiles.js — 归属判定的数据面（只读）
 * =============================================================================
 * 目标索引来源（按顺序尝试，各自标注 source，绝不"猜一个"）：
 *   1. ~/.dsh/agent-bus.json      → profiles（**当前** Agent Bus 能力登记表，实测 62 条）
 *   2. ~/.dsh-agent-bus.json      → profiles（旧路径遗留，实测仅 17 条且已停更 2026-08-17）
 *   3. ~/dsh-collab/data/agents/index.json（本地镜像，若存在）
 *   4. 黑板 GET /data/agents（若存在；只读）
 * 全部拿不到 → 抛 PROFILES_UNAVAILABLE（**拒绝执行**，因为无法验证目标存在，
 * 而"无法验证目标存在时继续派发"正是本工具要封堵的那条路径）。
 *
 * ★ 实测踩坑（2026-09-10，本工具首跑时被自己抓到）：只读旧路径 ~/.dsh-agent-bus.json
 *   会拿到一份 2026-08-17 的停更快照（17 条），于是当天真正干活的智能体全被判成
 *   "no-events"，10 条事件里 8 条变成 unassigned。**"档案看起来读到了"不等于读对了** ——
 *   所以这里按新→旧顺序尝试，并把实际用的文件路径写进结果与卡片，让人一眼能复核。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { GateError, makeIndex } from './gate.js';

export const HOME = os.homedir();
/** 当前 Agent Bus store（新路径，优先）。 */
export const BUS_STORE = path.join(HOME, '.dsh', 'agent-bus.json');
/** 旧路径遗留快照（次选，可能停更）。 */
export const BUS_STORE_LEGACY = path.join(HOME, '.dsh-agent-bus.json');
export const LOCAL_AGENTS = path.join(HOME, 'dsh-collab', 'data', 'agents', 'index.json');
export const RULES_MD = path.join(HOME, 'dsh-collab', 'rules-registry', 'RULES.md');

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

function profilesFrom(file) {
  const j = readJson(file);
  if (!j) return null;
  const arr = Array.isArray(j.profiles) ? j.profiles
    : (j.profiles && typeof j.profiles === 'object' ? Object.values(j.profiles) : null);
  if (!arr || !arr.length) return null;
  const src = file === BUS_STORE ? 'agent-bus' : (file === BUS_STORE_LEGACY ? 'agent-bus-legacy' : 'local-mirror');
  return arr
    .filter((p) => p && typeof p.agentId === 'string')
    .map((p) => ({ agentId: p.agentId, role: p.role || '', abilities: p.abilities || [], resources: p.resources || [], source: src }));
}

function fromLocalMirror() {
  const j = readJson(LOCAL_AGENTS);
  const arr = j && (Array.isArray(j) ? j : (Array.isArray(j.agents) ? j.agents : null));
  if (!arr || !arr.length) return null;
  return arr
    .filter((p) => p && typeof p.agentId === 'string')
    .map((p) => ({ agentId: p.agentId, role: p.role || '', abilities: p.abilities || [], resources: p.resources || [], source: 'local-mirror' }));
}

function fromBoard(bbGet) {
  try {
    const doc = bbGet('data/agents');
    const arr = doc && (Array.isArray(doc.agents) ? doc.agents : (Array.isArray(doc.profiles) ? doc.profiles : null));
    if (!arr || !arr.length) return null;
    return arr
      .filter((p) => p && typeof p.agentId === 'string')
      .map((p) => ({ agentId: p.agentId, role: p.role || '', abilities: p.abilities || [], resources: p.resources || [], source: 'blackboard' }));
  } catch { return null; }
}

/**
 * 载入档案 → 目标索引。
 * @param {{bbGet?:Function, profilesPath?:string}} opts
 */
export function loadTargets(opts = {}) {
  if (opts.profilesPath) {
    const j = readJson(opts.profilesPath);
    const arr = j && (Array.isArray(j) ? j : (Array.isArray(j.profiles) ? j.profiles : (Array.isArray(j.agents) ? j.agents : null)));
    if (!arr || !arr.length) throw new GateError('PROFILES_UNAVAILABLE', `--profiles 指定的文件里没有可用档案: ${opts.profilesPath}`);
    return { source: 'explicit', file: opts.profilesPath, index: makeIndex(arr) };
  }
  for (const [src, fn, file] of [
    ['agent-bus', () => profilesFrom(BUS_STORE), BUS_STORE],
    ['agent-bus-legacy', () => profilesFrom(BUS_STORE_LEGACY), BUS_STORE_LEGACY],
    ['local-mirror', fromLocalMirror, LOCAL_AGENTS],
    ['blackboard', () => fromBoard(opts.bbGet || (() => null)), 'data/agents']
  ]) {
    let arr = null;
    try { arr = fn(); } catch { arr = null; }
    if (arr && arr.length) return { source: src, file, index: makeIndex(arr) };
  }
  throw new GateError('PROFILES_UNAVAILABLE',
    `拿不到能力登记表（agent_profiles）：${BUS_STORE} / ${BUS_STORE_LEGACY} / 本地镜像 / 黑板 data/agents 都读不到可用档案。` +
    '**拒绝执行** —— 无法验证目标存在时继续派发，正是本工具要封堵的路径。请先让目标用 agent_profile 登记，或用 --profiles 指定档案文件。');
}

/* ══════════════════════ 规则账本（Q3 的候选规则） ══════════════════════ */

let rulesCache = null;

export function loadRules() {
  if (rulesCache) return rulesCache;
  const txt = (() => { try { return fs.readFileSync(RULES_MD, 'utf8'); } catch { return ''; } })();
  const rules = [];
  const blocks = txt.split(/\n(?=##\s)/);
  for (const b of blocks) {
    const m = b.match(/^##\s+([A-Za-z][\w.-]*|\d+)\s*(.*)$/m);
    if (!m) continue;
    const id = m[1];
    if (!/^(R\d|phi|Φ)/i.test(id)) continue;
    const head = m[2].replace(/[✅⚠️❌]/g, '').trim();
    const sum = (b.match(/-\s*摘要:\s*(.*)/) || [, ''])[1].trim();
    const det = (b.match(/-\s*详情:\s*(.*)/) || [, ''])[1].trim();
    rules.push({ id, head, sum, text: `${head} ${sum} ${det}`.toLowerCase() });
  }
  rulesCache = rules;
  return rules;
}

/** 按关键词在规则账本里检索候选规则号（供 Q3 对照；命中不了就如实说没有）。 */
export function findRuleCandidates(keywords, limit = 3) {
  const rules = loadRules();
  const scored = [];
  for (const r of rules) {
    let score = 0;
    const hit = [];
    for (const kw of keywords) {
      const k = String(kw || '').toLowerCase().trim();
      if (k.length < 3) continue;
      if (r.text.includes(k)) { score += k.length; hit.push(kw); }
    }
    if (score > 0) scored.push({ id: r.id, label: `${r.id} ${r.head || r.sum}`.slice(0, 64), score, hit: hit.slice(0, 4) });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit);
}
