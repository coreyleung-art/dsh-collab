/**
 * lesson.js — 字符 bigram 原语（**只此一个函数族**，不复制 harvest 的聚类规则）
 * =============================================================================
 * ★ 为什么不把 harvest 的整个 lesson.js 拷过来（R006 §6 坑#6 两处版本）：
 *   **聚类的判定规则属于 harvest**（它决定 recurrence，是本工具的输入事实）。
 *   synthesize 只需要"把一句话切成字符 bigram"这一条**纯函数原语**来做关键词重合比较。
 *   复制聚类规则会导致两个包各自演化、口径漂移 —— 那正是"同名工具两处实现、行为不一致"的坑。
 *   因此本文件**只有** normalizeLesson + bigrams；聚类阈值/同步盘判定等规则一律不在本包。
 *
 * 与 `~/dsh-collab/devices/dsh-plugin-reflect-harvest/lib/lesson.js` 中同名函数语义一致
 * （归一化字符集完全相同）；若将来要改，改 harvest 那份并把这里同步为同一实现。
 */

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

export const LESSON_META = Object.freeze({
  source_of_truth: 'devices/dsh-plugin-reflect-harvest/lib/lesson.js',
  in_this_package: 'normalizeLesson + bigrams（纯函数原语）',
  not_in_this_package: '聚类规则 / 相似度阈值 / 同步盘判定 —— 那些是 harvest 的职责，本包不复制'
});
