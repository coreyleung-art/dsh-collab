/**
 * calibration.js — K5「负控 1」的全尺寸标定（纯函数，零 dsh import / 零 I/O / 零时钟）
 * =============================================================================
 * ★ 立项书 §5 **负控 1（立论所系）**：「把活跃窗口压到摘要模板地板以下（机制二复发条件），
 *   本后端**仍能缩小**；若它判『缩不动』⇒ **立项失败**」。
 *   本文件把该判据从"一个用例"扩成"一条曲线"：**在多大的被遮内容上，谁缩得动**。
 *
 * ★★ 两个地板的来源**必须分清**（R030：不许把算出来的说成量出来的）：
 *
 *   ① **官方地板 = 实测值**，不是模型。
 *      来源 `docs/compaction-lowerbound-crash-20261009.md`：会话 `session-fa1f9150` 于
 *      2026-10-09T05:39:52 bricked 时，官方 `frameSummary` 的成帧摘要为 **3435**（另一读法 **3450**）token，
 *      而被遮内容 **2466** token。官方判据是 `framedSummaryTokenCount >= shadowedTokenCount` 即拒绝
 *      （`dsh-compaction-basic/lib/index.js:556`，**相等也拒**）⇒ `3435 ≥ 2466` 成立 ⇒ 判"压不动" ⇒ 硬死锁。
 *      ⇒ **官方地板 ≈ 3435**：被遮内容只要不超过它，官方**结构上**无法通过自己的下界判据。
 *      · 本文件把这个数当**输入常量**，并在报告里注明其出处；它**不是**本文件算出来的。
 *
 *   ② **本核地板 = 本核实算**。
 *      由 `planCheckpoint` 在给定被遮内容上真跑得出：最小的"被遮 token 总量"使得
 *      `被遮 − 检查点 ≥ 要求节省量` 成立。它随**条目粒度**变化（检查点有常量开销），
 *      故本文件对多个粒度分别标定，并把"最差粒度"也报出来（不藏）。
 *
 *   ⇒ **两者之间的区间**（本核缩得动 ∧ 官方缩不动）**就是本后端存在的理由**。
 *     该区间为空 ⇒ 立项无价值（这正是本项目该被判死的那种结论，故必须实算而不是假定它非空）。
 */

import { planCheckpoint, estimateTokens, CP_DEFAULTS } from './checkpoint.js';
import { resolveBudget, canShrink } from './budget.js';

/**
 * 官方地板（**实测常量**，出处见文件头）。两个读法都保留，报告里两个都出。
 * ★ 这不是本文件算的，是本文件**引用**的；任何改动必须同时改出处引用。
 */
export const OFFICIAL_FLOOR = Object.freeze({
  framedSummaryTokens: 3435,
  framedSummaryTokensAlt: 3450,
  shadowedTokensAtCrash: 2466,
  source: 'docs/compaction-lowerbound-crash-20261009.md（session-fa1f9150 · 2026-10-09T05:39:52 bricked）',
  judge: 'dsh-compaction-basic/lib/index.js:556 —— framedSummaryTokenCount >= shadowedTokenCount 即拒（相等也拒）'
});

export const CALIB_DEFAULTS = Object.freeze({
  entryTokens: 100,        // 单条被遮内容的 token（粒度）
  maxEntries: 4000,        // 扫描上限（足够覆盖官方地板量级）
  minSavingsTokens: 32,
  neededSavingsTokens: 0
});

/**
 * ★ 本核地板：多大的被遮内容开始，本核能给出缩小方案。
 * 用**二分**而不是线性扫（避免 O(N) 次 planCheckpoint）：判据在下述意义上是单调的 ——
 * 被遮内容越大，检查点的常量开销被摊得越薄 ⇒ 节省量单调不减。**该单调性本身由测试断言**（见 k5 用例），
 * 若它不成立，二分就会给出错答案 ⇒ 故测试里另有一条线性复算做交叉核对。
 * @returns {{ok:boolean, floorTokens:number|null, checkpointTokens:number|null, entryTokens:number, entriesAtFloor:number|null, reason:string}}
 */
export function measureOurFloor(opts = {}) {
  const entryTokens = opts.entryTokens === undefined ? CALIB_DEFAULTS.entryTokens : opts.entryTokens;
  const maxEntries = opts.maxEntries === undefined ? CALIB_DEFAULTS.maxEntries : opts.maxEntries;
  const minSavingsTokens = opts.minSavingsTokens === undefined ? CALIB_DEFAULTS.minSavingsTokens : opts.minSavingsTokens;
  const neededSavingsTokens = opts.neededSavingsTokens === undefined ? CALIB_DEFAULTS.neededSavingsTokens : opts.neededSavingsTokens;
  if (!Number.isInteger(entryTokens) || entryTokens < 1) throw new Error(`entryTokens 必须是 ≥1 的整数，收到 ${entryTokens}`);

  const probe = (n) => {
    if (n < 1) return null;
    const entries = Array.from({ length: n }, (_, i) => ({
      seq: i + 1, kind: i % 2 === 0 ? 'tool/result' : 'user/message',
      tokens: entryTokens, text: 'x'.repeat(entryTokens * CP_DEFAULTS.charsPerToken)
    }));
    const p = planCheckpoint({ entries, retainTokens: 0, minSavingsTokens, neededSavingsTokens, maxScan: maxEntries });
    return { n, shadowed: n * entryTokens, ok: p.ok === true, checkpointTokens: p.checkpointTokens, savings: p.savings };
  };

  const hi0 = probe(1);
  if (hi0 === null) return Object.freeze({ ok: false, floorTokens: null, checkpointTokens: null, entryTokens, entriesAtFloor: null, reason: '探测失败' });
  if (hi0.ok) return Object.freeze({ ok: true, floorTokens: entryTokens, checkpointTokens: hi0.checkpointTokens, entryTokens, entriesAtFloor: 1, reason: '单条即可缩小（粒度已足够大）' });
  const hiMax = probe(maxEntries);
  if (!hiMax.ok) {
    return Object.freeze({
      ok: false, floorTokens: null, checkpointTokens: hiMax.checkpointTokens, entryTokens, entriesAtFloor: null,
      reason: `扫到 ${maxEntries} 条（${maxEntries * entryTokens} token）仍缩不动 ⇒ **本核在此粒度下无效**（这等价于立项失败，必须如实报出）`
    });
  }
  // 二分：找最小的可行 n（依赖单调性；测试里有线性复算交叉核对）
  let lo = 1, hi = maxEntries;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (probe(mid).ok) hi = mid; else lo = mid + 1;
  }
  const hit = probe(lo);
  return Object.freeze({
    ok: true, floorTokens: hit.shadowed, checkpointTokens: hit.checkpointTokens,
    entryTokens, entriesAtFloor: lo,
    reason: `本核地板 ${hit.shadowed} token（${lo} 条 × ${entryTokens}）⇒ 检查点 ${hit.checkpointTokens}，省 ${hit.savings}`
  });
}

/**
 * ★ 全尺寸标定：把「本核地板」与「官方地板」摆在一起，给出**区间**与逐点对照。
 * @returns 冻结的标定报告（含可复跑所需的全部参数）
 */
export function calibrationReport(opts = {}) {
  const granularities = opts.granularities === undefined ? [32, 100, 500, 2000] : opts.granularities;
  const minSavingsTokens = opts.minSavingsTokens === undefined ? CALIB_DEFAULTS.minSavingsTokens : opts.minSavingsTokens;
  const neededSavingsTokens = opts.neededSavingsTokens === undefined ? CALIB_DEFAULTS.neededSavingsTokens : opts.neededSavingsTokens;

  const rows = granularities.map((entryTokens) => {
    const f = measureOurFloor({ entryTokens, minSavingsTokens, neededSavingsTokens, maxEntries: opts.maxEntries });
    return Object.freeze({
      entryTokens,
      ourFloorTokens: f.ok ? f.floorTokens : null,
      ourCheckpointAtFloor: f.checkpointTokens,
      ok: f.ok,
      reason: f.reason
    });
  });

  const okRows = rows.filter((r) => r.ok && r.ourFloorTokens !== null);
  const worstFloor = okRows.length > 0 ? Math.max(...okRows.map((r) => r.ourFloorTokens)) : null;
  const bestFloor = okRows.length > 0 ? Math.min(...okRows.map((r) => r.ourFloorTokens)) : null;

  // 区间 = [本核最差地板, 官方地板)：本核缩得动 ∧ 官方缩不动
  const band = worstFloor === null ? null : Object.freeze({
    from: worstFloor,
    toExclusive: OFFICIAL_FLOOR.framedSummaryTokens,
    width: OFFICIAL_FLOOR.framedSummaryTokens - worstFloor,
    empty: OFFICIAL_FLOOR.framedSummaryTokens <= worstFloor
  });

  // ★★ 决定性判据：**在官方崩溃的那一点上**（被遮内容 = 崩溃时实测值），本核能否缩小？
  //   这是 §5 负控 1 的最强形式：不是"某个区间存在"，而是"官方判死的那一点本核活着"。
  const crashShadowed = OFFICIAL_FLOOR.shadowedTokensAtCrash;
  const atCrash = (() => {
    // 用**本核最差地板**作判据（保守）：最差地板 < 崩溃点被遮内容 ⇒ 在该点必能缩小
    if (worstFloor === null) return { ok: false, reason: '本核无地板（标定粒度下均缩不动）⇒ 崩溃点上必不能缩小' };
    if (worstFloor < crashShadowed) {
      return {
        ok: true,
        reason: `本核**最差**地板 ${worstFloor} < 官方崩溃点被遮内容 ${crashShadowed} ⇒ 在该点上本核必能缩小（保守判据，未取最优粒度）`
      };
    }
    return {
      ok: false,
      reason: `本核最差地板 ${worstFloor} ≥ 官方崩溃点被遮内容 ${crashShadowed} ⇒ **在最差粒度下崩溃点仍缩不动**（须改用更细粒度，或在报告中如实标注该边界）`
    };
  })();

  return Object.freeze({
    officialFloor: OFFICIAL_FLOOR,
    atOfficialCrashPoint: Object.freeze({ shadowedTokens: crashShadowed, ...atCrash }),
    rows: Object.freeze(rows),
    ourWorstFloorTokens: worstFloor,
    ourBestFloorTokens: bestFloor,
    band,
    verdict: (() => {
      if (band === null) return '★ **立项失败**：本核在所有标定粒度下都缩不动（地板不存在）—— 按 §5 负控 1，本项目应被判死';
      if (band.empty) return '★ **立项失败**：本核地板不优于官方地板 ⇒ 区间为空 ⇒ 本后端无存在理由（按 §5 负控 1 应判死）';
      const head = `★ **立论成立**：区间 [${band.from}, ${band.toExclusive}) 宽 ${band.width} token —— 本区间内本核缩得动而官方缩不动`;
      return atCrash.ok ? `${head}；**且官方崩溃点（被遮 ${crashShadowed}）落在区间内** ⇒ 该点本核活着` : `${head}；★ 但 ${atCrash.reason}`;
    })(),
    params: Object.freeze({ granularities: Object.freeze([...granularities]), minSavingsTokens, neededSavingsTokens }),
    reproCmd: 'node cli.js --calibration [--json]'
  });
}

/** 把标定报告渲染成人类可读的 Markdown 表（供落盘/贴卡）。 */
export function renderCalibration(r) {
  const L = [];
  L.push('# K5 负控 1 标定 · 缩小地板对照');
  L.push('');
  L.push('> 本文件由 `node cli.js --calibration` 生成，全部数值可复跑。');
  L.push('');
  L.push('## 两个地板的来源（必须分清）');
  L.push('');
  L.push(`- **官方地板 = 实测常量 ${r.officialFloor.framedSummaryTokens}**（另一读法 ${r.officialFloor.framedSummaryTokensAlt}）——**引用**，非本文件所算。`);
  L.push(`  · 出处：${r.officialFloor.source}`);
  L.push(`  · 判据：${r.officialFloor.judge}`);
  L.push(`  · 崩溃时被遮内容 ${r.officialFloor.shadowedTokensAtCrash} token ⇒ ${r.officialFloor.framedSummaryTokens} ≥ ${r.officialFloor.shadowedTokensAtCrash} 成立 ⇒ 官方判"压不动"。`);
  L.push('- **本核地板 = 本核实算**（`planCheckpoint` 真跑）。随条目粒度变化，故按多粒度标定，并把**最差地板**也报出。');
  L.push('');
  L.push('## 逐粒度对照');
  L.push('');
  L.push('| 条目粒度(token) | 本核地板(token) | 地板处检查点(token) | 可缩小 | 说明 |');
  L.push('|---|---|---|---|---|');
  for (const row of r.rows) {
    L.push(`| ${row.entryTokens} | ${row.ourFloorTokens ?? '—'} | ${row.ourCheckpointAtFloor ?? '—'} | ${row.ok ? '✅' : '❌'} | ${row.reason} |`);
  }
  L.push('');
  L.push('## 地板对照小结');
  L.push('');
  L.push(`- 本核地板区间：最优 **${r.ourBestFloorTokens ?? '—'}** / 最差 **${r.ourWorstFloorTokens ?? '—'}**`);
  L.push(`- 官方地板：**${r.officialFloor.framedSummaryTokens}**`);
  L.push('');
  L.push('## ★★ 决定性判据：官方崩溃的那一点');
  L.push('');
  L.push(`官方崩溃时被遮内容 **${r.atOfficialCrashPoint.shadowedTokens}** token（实测，出处见上）。`);
  L.push(`- ${r.atOfficialCrashPoint.ok ? '✅' : '❌'} ${r.atOfficialCrashPoint.reason}`);
  L.push('');
  L.push('> 判据取**最差粒度**（保守），未取最优粒度 —— 故其为真即无需再论粒度。');
  L.push('');
  L.push('> ★★ **口径说明（本判据与「区间」回答的是两个不同问题，勿读成矛盾）**：');
  L.push('> · **本判据**陈述**能力**：`worstFloor < shadowedTokensAtCrash`，用的是**实测**值（2466）⇒ 与官方地板声明无关；');
  L.push('> · **区间**陈述**比较优势**：`framedSummaryTokens <= worstFloor`，用的是**官方地板声明**（3435）。');
  L.push('> ⇒ 若官方地板被改动，**区间会翻，而本判据不动** —— 那时会看到 ✅ 与 ❌ 并排，');
  L.push('>   那是**两个问题的答案**，不是自相矛盾。（此说明由一次 canfail 注入发现：见 CHANGELOG 0.10.1）');
  L.push('');
  L.push('## 结论与区间');
  L.push('');
  L.push(`- ${r.verdict}`);
  L.push('');
  L.push(`复跑：\`${r.reproCmd}\``);
  return L.join('\n');
}

/** 顺带把"本核地板 vs ctxwin 预算"也对一次（预算侧不构成地板，但要确认没有引入新的地板）。 */
export function budgetSanity(cw) {
  const b = resolveBudget({ contextWindow: cw });
  const r = canShrink({ shadowedTokens: b.threshold, checkpointTokens: Math.floor(b.threshold / 2), minSavingsTokens: CALIB_DEFAULTS.minSavingsTokens });
  return Object.freeze({ cw, threshold: b.threshold, preemptsOfficial: b.preemptsOfficial, canShrinkAtHalf: r.ok });
}
