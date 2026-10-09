/**
 * catalog.js — 参照库索引（**只读**）：RULES.md 规则号 + governance-philosophy.json 哲学号
 * =============================================================================
 * 用途：harvest 校验 related_rule 是否**真实存在**（不存在 → 打 flag `unknown_rule`，**不拒收**）。
 *
 * ★ 结构性只读：本模块只 import `fs.readFileSync`，不 import 任何写函数。
 *   "不写治理库"不是纪律，是因为这里**没有那个能力**（写出口全在 lib/out.js，
 *   而 out.js 的白名单里没有 rules-registry / gallery 这两个目录）。
 *
 * 诚实边界：文件不存在 / 解析失败时，**不猜**——返回 available=false，
 * harvest 据此**跳过** unknown_rule 判定并在输出里写明原因（宁可漏标，不可误标）。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const COLLAB = path.join(os.homedir(), 'dsh-collab');

export const RULES_PATH = path.join(COLLAB, 'rules-registry', 'RULES.md');
export const PHILOSOPHY_PATH = path.join(COLLAB, 'data', 'blueprint', 'gallery', 'governance-philosophy.json');

/** 解析 RULES.md 的条目标题：`## R001 ✅ 红绿灯互斥协议` / `## J31 ✅ ...` */
export function parseRuleIds(markdown) {
  const ids = new Set();
  const titles = {};
  for (const line of String(markdown).split('\n')) {
    const m = line.match(/^##\s+([A-Z]\d+)\s+(.*)$/);
    if (m) {
      const id = m[1];
      ids.add(id);
      titles[id] = m[2].replace(/^[✅⚠️❌\s]+/, '').trim();
    }
  }
  return { ids, titles };
}

/** 解析 governance-philosophy.json 的哲学 id 列表 */
export function parsePhilosophyIds(json) {
  const ids = new Set();
  const titles = {};
  for (const p of (json && json.philosophies) || []) {
    if (p && p.id) { ids.add(String(p.id)); titles[String(p.id)] = String(p.name || ''); }
  }
  return { ids, titles };
}

/**
 * 构建目录。返回：
 *   { rules:Set, phis:Set, ruleTitles, phiTitles, available:{rules,phis}, notes:[] }
 * available=false 表示该库读不到 → 调用方须跳过对应判定。
 */
export function loadCatalog() {
  const notes = [];
  let rules = new Set(), phis = new Set(), ruleTitles = {}, phiTitles = {};
  let rulesAvailable = false, phisAvailable = false;

  try {
    const md = fs.readFileSync(RULES_PATH, 'utf8');
    const r = parseRuleIds(md);
    rules = r.ids; ruleTitles = r.titles;
    rulesAvailable = rules.size > 0;
    if (!rulesAvailable) notes.push(`RULES.md 解析出 0 条规则号（格式变化？）→ 跳过 unknown_rule 判定：${RULES_PATH}`);
  } catch (e) {
    notes.push(`RULES.md 不可读（${e.code || e.message}）→ 跳过 unknown_rule 判定：${RULES_PATH}`);
  }

  try {
    const j = JSON.parse(fs.readFileSync(PHILOSOPHY_PATH, 'utf8'));
    const p = parsePhilosophyIds(j);
    phis = p.ids; phiTitles = p.titles;
    phisAvailable = phis.size > 0;
    if (!phisAvailable) notes.push(`governance-philosophy.json 解析出 0 条哲学号 → 跳过 unknown_rule 判定：${PHILOSOPHY_PATH}`);
  } catch (e) {
    notes.push(`governance-philosophy.json 不可读（${e.code || e.message}）→ 跳过 unknown_rule 判定：${PHILOSOPHY_PATH}`);
  }

  return {
    rules, phis, ruleTitles, phiTitles,
    available: { rules: rulesAvailable, phis: phisAvailable },
    notes
  };
}

export const CATALOG_META = Object.freeze({
  rulesPath: RULES_PATH,
  philosophyPath: PHILOSOPHY_PATH,
  access: 'read-only（本模块不 import 任何写函数）'
});
