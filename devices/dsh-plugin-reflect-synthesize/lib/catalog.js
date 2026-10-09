/**
 * catalog.js — 现有库索引（**只读**）：RULES.md 规则 + governance-philosophy.json 哲学
 * =============================================================================
 * 与 harvest 的 catalog 的差别：harvest 只要"这个 id 存不存在"；
 * synthesize 还要"这条讲的是什么"—— 因为要做**关键词重合**判定，所以每条建一个 bigram 词表。
 *
 * ★ 结构性只读：本模块只 import `fs.readFileSync`，不 import 任何写函数。
 *   "不写治理库"不是纪律问题 —— 写出口全在 lib/out.js，而它的 WRITE_SPEC 里
 *   **没有** rules-registry / data/blueprint/gallery 这两个目录，路径根本构造不出来。
 *
 * 诚实边界：文件不存在 / 解析失败 → `available:false`，synthesize 据此**跳过**对照判定
 * 并把整批 cluster 标 `unclear`（而不是假装"没有匹配 = 新维度"）。
 * 这个区分很关键：**读不到库**和**库里没有**是两件事，混在一起会把"读失败"误判成"新维度提案"。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { bigrams } from './lesson.js';

const COLLAB = path.join(os.homedir(), 'dsh-collab');
export const RULES_PATH = path.join(COLLAB, 'rules-registry', 'RULES.md');
export const PHILOSOPHY_PATH = path.join(COLLAB, 'data', 'blueprint', 'gallery', 'governance-philosophy.json');

/** 解析 RULES.md：`## R001 ✅ 标题` + `- 摘要: …` + `- 详情: …` */
export function parseRules(markdown) {
  const out = new Map();
  const lines = String(markdown).split('\n');
  let cur = null;
  for (const line of lines) {
    const h = line.match(/^##\s+([A-Z]\d+)\s+(.*)$/);
    if (h) {
      cur = { id: h[1], title: h[2].replace(/^[✅⚠️❌\s]+/, '').trim(), summary: '', detail: '' };
      out.set(cur.id, cur);
      continue;
    }
    if (!cur) continue;
    const s = line.match(/^-\s*摘要:\s*(.*)$/);
    if (s) { cur.summary = s[1].trim(); continue; }
    const d = line.match(/^-\s*详情:\s*(.*)$/);
    if (d) { cur.detail = d[1].trim(); continue; }
  }
  return out;
}

/** 给每个条目建 bigram 词表（标题 + 摘要 + 详情 / 名称 + core + children + principles + examples + detail） */
function vocabOf(...texts) {
  const set = new Set();
  for (const t of texts) for (const g of bigrams(String(t || ''))) set.add(g);
  return set;
}

/** 构建索引。返回 { rules: Map, phis: Map, available:{rules,phis}, notes:[] } */
export function loadCatalog() {
  const notes = [];
  const rules = new Map();
  const phis = new Map();
  let rulesAvailable = false, phisAvailable = false;

  try {
    const md = fs.readFileSync(RULES_PATH, 'utf8');
    for (const [, r] of parseRules(md)) {
      rules.set(r.id, { kind: 'rule', id: r.id, title: r.title, vocab: vocabOf(r.id, r.title, r.summary, r.detail) });
    }
    rulesAvailable = rules.size > 0;
    if (!rulesAvailable) notes.push(`RULES.md 解析出 0 条规则（格式变化？）→ 跳过对照判定：${RULES_PATH}`);
  } catch (e) {
    notes.push(`RULES.md 不可读（${e.code || e.message}）→ 跳过对照判定：${RULES_PATH}`);
  }

  try {
    const j = JSON.parse(fs.readFileSync(PHILOSOPHY_PATH, 'utf8'));
    for (const p of j.philosophies || []) {
      if (!p || !p.id) continue;
      phis.set(String(p.id), {
        kind: 'phi', id: String(p.id), title: String(p.name || ''),
        vocab: vocabOf(p.id, p.name, p.core, p.detail, (p.children || []).join(' '), (p.principles || []).join(' '), (p.examples || []).join(' '))
      });
    }
    phisAvailable = phis.size > 0;
    if (!phisAvailable) notes.push(`governance-philosophy.json 解析出 0 条哲学 → 跳过对照判定：${PHILOSOPHY_PATH}`);
  } catch (e) {
    notes.push(`governance-philosophy.json 不可读（${e.code || e.message}）→ 跳过对照判定：${PHILOSOPHY_PATH}`);
  }

  return { rules, phis, available: { rules: rulesAvailable, phis: phisAvailable }, notes };
}

export const CATALOG_META = Object.freeze({
  rulesPath: RULES_PATH,
  philosophyPath: PHILOSOPHY_PATH,
  access: 'read-only（本模块不 import 任何写函数；治理库目录不在写白名单基目录之下）'
});
