/**
 * lesson.js — lesson 归一化 / 近似度 / 聚类（去重 + ★ 跨智能体复现计数）
 * =============================================================================
 * 这是「数据飞轮」与「日记」的分界线：
 *   日记：按**个人感受**排序（谁先说、说得多动情）。
 *   飞轮：按**复现广度**排序（同一条 lesson 被 N 个智能体**独立**提到）。
 * 因此聚类必须**确定性**（同样输入 → 同样 cluster_id / 同样顺序），否则复现计数会漂移。
 *
 * 算法（零外部依赖，纯 node 内置）：
 *   1) 归一化：去空白/标点/大小写
 *   2) 近似度：**字符 bigram**（对中文短句最稳，不需要分词器、不需要外部包）
 *   3) 聚类：并查集（union-find）+ 双判据（见 SIM_RULE）
 *   4) 代表句：取簇内**最长**的 lesson（信息量最大；等长取字典序最小 → 确定）
 *
 * 已如实登记的局限：这是**字面层**近似，不是真正的语义近似。真正换述（"取证" ↔ "留证据"）
 * 可能并不到一起。因此 `similarityReport` 会把**未合并但接近**的对也列出来（--summary / JSON 都含），
 * 让人工一眼看见"可能是同一条但没敢合"。宁可显式暴露灰区，不可静默错合/错拆。
 */

/**
 * 聚类判定规则（**冻结**：改它会改变复现计数，属版本级改动）。
 *
 * 为什么一条判据不够（实测证据，2026-09-10 fixtures）：
 *   Dice 系数**惩罚长度差**。下面两句是同一件事的两种复述，
 *   共享 13 个 bigram（内容高度重叠），Dice 却只有 0.491：
 *     A「破坏性动作之前必须先取证，且证据要标注是处置前还是处置后采集」
 *     B「处置之前必须先取证，证据要标注采集时点；处置后补注的只能算回忆」
 *   只按 Dice≥0.52 会**漏合** → 把「3 个智能体独立提到」错拆成「1+1+1」，
 *   而复现广度正是本工具存在的全部理由。
 *
 * 双判据：形状极像（Dice 高）**或**共享内容足够多（共享 bigram 绝对数高 + Dice 不低于地板）。
 * 地板值防的是「长 lesson 与短 lesson 只因一句套话而共享」的错合。
 */
export const SIM_RULE = Object.freeze({
  dice: 0.52,             // 主判据：bigram Dice ≥ 0.52
  sharedMin: 8,           // 次判据：共享 bigram 绝对数 ≥ 8
  sharedDiceFloor: 0.40   // 次判据前提：Dice ≥ 0.40
});

/** 兼容别名（README / 输出展示用） */
export const CLUSTER_THRESHOLD = SIM_RULE.dice;

/** 归一化：去空白/常见中英标点，转小写 */
export function normalizeLesson(s) {
  return String(s ?? '')
    .toLowerCase()
    .replace(/[\s\u3000]+/g, '')
    .replace(/[，。、；：！？…—－·「」『』（）()【】\[\]{}"'`“”‘’《》,.;:!?<>\-_/\\|~@#$%^&*+=]/g, '');
}

/** 字符 bigram 集合（长度 1 的串退化为该字符本身） */
export function bigrams(s) {
  const t = normalizeLesson(s);
  const set = new Set();
  if (t.length === 1) set.add(t);
  for (let i = 0; i + 1 < t.length; i++) set.add(t.slice(i, i + 2));
  return set;
}

/** Dice 系数 = 2|A∩B| / (|A|+|B|)，范围 [0,1] */
export function dice(a, b) {
  const A = a instanceof Set ? a : bigrams(a);
  const B = b instanceof Set ? b : bigrams(b);
  if (A.size === 0 || B.size === 0) return 0;
  let inter = 0;
  for (const g of A) if (B.has(g)) inter++;
  return (2 * inter) / (A.size + B.size);
}

/** 共享 bigram 绝对数 */
export function sharedCount(a, b) {
  const A = a instanceof Set ? a : bigrams(a);
  const B = b instanceof Set ? b : bigrams(b);
  let inter = 0;
  for (const g of A) if (B.has(g)) inter++;
  return inter;
}

/** 是否同簇（双判据，返回判定依据以便审计） */
export function isSameLesson(a, b, rule = SIM_RULE) {
  const A = bigrams(a), B = bigrams(b);
  const d = dice(A, B);
  const sh = sharedCount(A, B);
  if (d >= rule.dice) return { merge: true, dice: d, shared: sh, why: `dice ${d.toFixed(3)} ≥ ${rule.dice}` };
  const merge = sh >= rule.sharedMin && d >= rule.sharedDiceFloor;
  return {
    merge, dice: d, shared: sh,
    why: merge
      ? `shared ${sh} ≥ ${rule.sharedMin} 且 dice ${d.toFixed(3)} ≥ ${rule.sharedDiceFloor}（长度差导致 Dice 偏低，但内容高度重叠）`
      : `dice ${d.toFixed(3)} < ${rule.dice}；shared ${sh} < ${rule.sharedMin} 或 dice < ${rule.sharedDiceFloor}`
  };
}

/**
 * 确定性聚类（并查集；entries 必须已按 key 排序）。
 * @param {Array<{key:string, agent:string, item_id:string, lesson:string, item:object, flags:string[]}>} entries
 * @param {object} rule
 * @returns {Array<{members:Array, representative:string}>}
 */
export function clusterLessons(entries, rule = SIM_RULE) {
  const n = entries.length;
  const parent = Array.from({ length: n }, (_, i) => i);
  const find = (i) => { let r = i; while (parent[r] !== r) r = parent[r]; while (parent[i] !== r) { const nx = parent[i]; parent[i] = r; i = nx; } return r; };
  const union = (i, j) => { const a = find(i), b = find(j); if (a !== b) parent[Math.max(a, b)] = Math.min(a, b); };

  // 确定性：按索引升序两两比较（entries 已按 key 排序）
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (isSameLesson(entries[i].lesson, entries[j].lesson, rule).merge) union(i, j);
    }
  }

  const groups = new Map();
  for (let i = 0; i < n; i++) {
    const r = find(i);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(entries[i]);
  }

  // 簇内排序：agent 升序 → item_id 升序（完全确定）→ 簇顺序按最小索引
  return [...groups.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([, members]) => {
      const sorted = members.slice().sort((x, y) =>
        x.agent.localeCompare(y.agent) || String(x.item_id).localeCompare(String(y.item_id)));
      return { members: sorted, representative: pickRepresentative(sorted) };
    });
}

/** 代表句：最长优先；等长取字典序最小（确定） */
export function pickRepresentative(members) {
  return members
    .map((m) => String(m.lesson))
    .sort((a, b) => b.length - a.length || a.localeCompare(b))[0];
}

/** 复现广度：**独立智能体数**（同一 agent 在同簇提 3 次只算 1） */
export function recurrenceOf(members) {
  return new Set(members.map((m) => m.agent)).size;
}

/**
 * 相似度矩阵（供 --summary / --json 审计）：
 * 列出所有 dice ≥ 0.25 的对，并标出 merged 与否 —— **灰区可见**是刻意设计。
 */
export function similarityReport(entries, rule = SIM_RULE) {
  const rows = [];
  for (let i = 0; i < entries.length; i++) {
    for (let j = i + 1; j < entries.length; j++) {
      const verdict = isSameLesson(entries[i].lesson, entries[j].lesson, rule);
      if (verdict.dice >= 0.25 || verdict.shared >= rule.sharedMin) {
        rows.push({
          a: entries[i].key, b: entries[j].key,
          sim: Number(verdict.dice.toFixed(3)), shared: verdict.shared,
          merged: verdict.merge, why: verdict.why
        });
      }
    }
  }
  return rows.sort((x, y) => y.sim - x.sim || y.shared - x.shared);
}
