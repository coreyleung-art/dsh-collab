/**
 * k3-selftest.js — K3 自检（检查点产出 + 有界阶梯 + 保证能减）的**唯一来源**
 * =============================================================================
 * 两个消费者，同一份用例（避免两处漂）：
 *   · `cli.js --checkpoint-check` —— 进程内跑（本插件 ALLOWED_COMMANDS = []，连测试进程都不能起）；
 *   · `lib/checkpoint.test.js`    —— 交给 node:test 驱动，逐条变成断言。
 *
 * ★ 全部用例只 import 纯决策核（budget.js / checkpoint.js / budget-selftest.js），
 *   **零 dsh import、零 I/O、零时钟** —— 跑它就是 K3 的验收手段本身（§4 第 2 条）。
 *
 * ★ 用例里的"官方死锁态"不是编的：`docs/compaction-lowerbound-crash-20261009.md` 实测
 *   `3435/3450 ≥ 2466`，即**摘要帧（3435–3450 token）比它替换掉的被遮内容（2466 token）还大**，
 *   压缩器因此判"压不动"⇒ 会话硬死锁。本套用例把它固化成负控 1（立论所系）。
 */
import { createHash } from 'node:crypto';
import { canonicalJson } from './budget-selftest.js';
import { eq, deq, okTrue, errHelper } from './assert-helpers.js';
import { SHRINK, OFFICIAL_THRESHOLD_PCT, BUDGET_DEFAULTS } from './budget.js';
import {
  RUNG, RUNG_ORDER, PLAN, CP_DEFAULTS, CheckpointError,
  estimateTokens, trimToTokens, splitRetain, quoteBudget, groupElided, elisionLine,
  buildHandoff, assemble, makeCharAccount, planCheckpoint, describePlan
} from './checkpoint.js';
import {
  EV, inspectCompactionEntryState, compactionActivity, compactionGuardFrom, describeGuardResult
} from './events.js';
import {
  PairingError, eventDelta, buildCutBalance, balancedBefore, balancedAfter,
  findBalancedWindow, describeWindow
} from './pairing.js';
import {
  buildReplacement, describeReplacement, defaultEntryText, defaultEntryKind
} from './replace.js';

/* ------------------------------- 断言小工具 ------------------------------- */
// 断言助手统一来自 lib/assert-helpers.js（第 3 次重复后提取，见该文件头）
const err = errHelper(CheckpointError);
const perr = errHelper(PairingError);

/* ------------------------------- 造数 ------------------------------- */
/** 造一条正文恰为 tokens*4 字符的条目（使 estimateTokens(text) === tokens，口径可预期）。 */
const entry = (seq, kind, tokens) => ({ seq, kind, tokens, text: 'x'.repeat(tokens * CP_DEFAULTS.charsPerToken) });
/** 混合条目：一半 tool/result 一半 user/message，各 perTokens，共 n 条。 */
const mixed = (n, perTokens, startSeq = 1) => Array.from({ length: n }, (_, i) =>
  entry(startSeq + i, i % 2 === 0 ? 'tool/result' : 'user/message', perTokens));

const FIELDS = Object.freeze({
  goal: '推进 Q-K 上下文存活后端',
  wave: 'K3',
  todos: '- [ ] 检查点产出',
  lastHumanRequest: '你结合我这个想法，能不能先把这个作为优先推进目标来重新设定目标呢？',
  notes: '台账与索引两处不许漂'
});

/* ============================== 主用例集 ============================== */
export function k3Cases() {
  const out = [];

  /* ---- Z0. ★★ 锚点常量绝对钉扎（变异检验暴露的缺口 · 2026-10-10）----
     为什么必须**绝对**钉而不是关系式钉：已有断言 B32 是 `threshold < floor(cw×OFFICIAL_THRESHOLD_PCT/100)` ——
     **它用同一个常量当参照系**，改常量则两边一起动，不变式照样成立 ⇒ **自指的断言守不住被自指的值**。
     而这两个是**外部事实**（官方源码比率 / 用户已决默认值），不是派生值 ⇒ 只能绝对钉。
     变异检验实证：把 80 改成 79、把 70 改成 75，**全部断言照样绿** —— 即该处此前无人看守。 */
  out.push(
    eq('Z0/★ 官方触发比率 = 80（绝对钉 · 出处见 budget.js 文件头 :13）', OFFICIAL_THRESHOLD_PCT, 80),
    eq('Z0/★ 抢先上限默认 = 70（绝对钉 · 用户 2026-10-10 裁决值）', BUDGET_DEFAULTS.preemptPct, 70),
    eq('Z0/★ 可用率默认 = 95', BUDGET_DEFAULTS.usablePct, 95),
    eq('Z0/★ 上限率默认 = 90', BUDGET_DEFAULTS.limitPct, 90),
    eq('Z0/★ 加性 buffer 默认 = 8000', BUDGET_DEFAULTS.bufferTokens, 8000),
    eq('Z0/★ 保活窗口默认 = 5120', BUDGET_DEFAULTS.retainTokens, 5120),
    eq('Z0/★ 最小节省默认 = 32', BUDGET_DEFAULTS.minSavingsTokens, 32),
    // ★ 关系式也要在（它守的是"抢先成立"，与上面的"值本身"是两件事，各自不可替代）
    eq('Z0/★ 关系：抢先上限 < 官方比率（两值独立钉后仍须成立）', BUDGET_DEFAULTS.preemptPct < OFFICIAL_THRESHOLD_PCT, true),
    eq('Z0/★ 常量被冻结（不可被运行期改写）', Object.isFrozen(BUDGET_DEFAULTS), true)
  );

  /* ---- A. token 口径与裁剪 ---- */
  out.push(
    eq('A/token 口径=ceil(len/4)', estimateTokens('abcdefgh'), 2),
    eq('A/空串=0 token', estimateTokens(''), 0),
    eq('A/单字符=1 token', estimateTokens('a'), 1),
    eq('A/中文按字符数同口径', estimateTokens('中文中文中文中文'), 2),
    deq('A/裁剪后必 ≤ 预算(恰等)', trimToTokens('x'.repeat(400), 100).tokens, 100),
    deq('A/裁剪后必 ≤ 预算(超1)', trimToTokens('x'.repeat(401), 100).tokens <= 100, true),
    deq('A/裁剪后必 ≤ 预算(超很多)', trimToTokens('x'.repeat(40000), 37).tokens <= 37, true),
    eq('A/未超预算则原样返回', trimToTokens('x'.repeat(10), 100).trimmed, false),
    eq('A/超预算则标记 trimmed', trimToTokens('x'.repeat(400), 10).trimmed, true),
    eq('A/裁剪保留省略号', trimToTokens('x'.repeat(400), 10).text.endsWith('…'), true),
    err('A/estimateTokens 拒非串', () => estimateTokens(42), 'BAD_TEXT'),
    err('A/estimateTokens 拒 cpt<1', () => estimateTokens('abc', 0), 'BAD_CPT'),
    err('A/trimToTokens 拒 maxTokens<1', () => trimToTokens('abc', 0), 'BAD_MAX_TOKENS')
  );

  /* ---- B. 条目几何与保留窗口 ---- */
  const e10 = mixed(10, 50);   // seq 1..10, 每条 50 token, 共 500
  out.push(
    deq('B/splitRetain 保活吃满即封口', splitRetain(e10, 100).retainedTokens >= 100, true),
    deq('B/splitRetain 保活区逐字未动', splitRetain(e10, 100).retained.map((e) => e.seq), [9, 10]),
    deq('B/splitRetain 可遮区=剩余前缀', splitRetain(e10, 100).shadowable.map((e) => e.seq), [1, 2, 3, 4, 5, 6, 7, 8]),
    eq('B/retain=0 时全部可遮', splitRetain(e10, 0).shadowable.length, 10),
    eq('B/retain 超全部时可遮为空', splitRetain(e10, 100000).shadowable.length, 0),
    err('B/拒非升序 entries', () => planCheckpoint({ entries: [entry(5, 'user/message', 10), entry(3, 'user/message', 10)] }), 'BAD_ORDER'),
    err('B/拒重复 seq', () => planCheckpoint({ entries: [entry(5, 'user/message', 10), entry(5, 'user/message', 10)] }), 'BAD_ORDER'),
    err('B/拒负 token', () => planCheckpoint({ entries: [{ seq: 1, kind: 'k', tokens: -1, text: '' }] }), 'BAD_TOKENS'),
    err('B/拒非整 token', () => planCheckpoint({ entries: [{ seq: 1, kind: 'k', tokens: 1.5, text: '' }] }), 'BAD_TOKENS')
  );

  /* ---- C. 检查点正文形状（逐字，不摘要） ---- */
  const one = mixed(3, 40);    // seq 1..3
  const asmL0 = assemble(one, RUNG.L0_QUOTE, FIELDS, CP_DEFAULTS, 3);
  out.push(
    eq('C/首行形状逐字', asmL0.text.split('\n')[0], '<context_handoff v1 seq-range=1-3>'),
    eq('C/末行形状逐字', asmL0.text.split('\n').at(-1), '</context_handoff>'),
    okTrue('C/含目标字段', asmL0.text.includes('目标:      推进 Q-K 上下文存活后端')),
    okTrue('C/含阶段字段', asmL0.text.includes('阶段/波次:  K3')),
    okTrue('C/含 todo 字段', asmL0.text.includes('todo:      - [ ] 检查点产出')),
    okTrue('C/最近人类请求逐字含问号', asmL0.text.includes('重新设定目标呢？')),
    okTrue('C/含原文节选标头', asmL0.text.includes('原文节选（逐字，未摘要）')),
    okTrue('C/含召回指南且带 csx_recall', /召回指南:.*csx_recall \{kind:"range", id:"1-3"\}/.test(asmL0.text)),
    eq('C/L0 三条全引文', asmL0.quotedCount, 3),
    eq('C/L0 无省略账', asmL0.elidedCount, 0)
  );

  /* ---- D. 缺字段如实留空，不编造（R030 / 立项书 §6 风险 4） ---- */
  const bare = buildHandoff({ startSeq: 1, endSeq: 1 });
  out.push(
    okTrue('D/缺 goal 含"投影缺失"', bare.includes('goal 投影缺失，如实留空不编造')),
    okTrue('D/缺字段标为(无)', bare.includes('(无)')),
    okTrue('D/缺字段不编造数字', !/\d{3,}/.test(bare.replace(/seq-range=\d+-\d+/, ''))),
    err('D/非法 seq-range 抛错', () => buildHandoff({ startSeq: 5, endSeq: 1 }), 'BAD_RANGE')
  );

  /* ---- E. 省略账分组与行形状（逐字照立项书 §2.4） ---- */
  const g = groupElided([entry(1, 'tool/result', 10), entry(2, 'tool/result', 10), entry(4, 'user/message', 10), entry(5, 'user/message', 10)]);
  out.push(
    eq('E/同类连续折成 1 组', g.length, 2),
    deq('E/组1 计数与区间', { c: g[0].count, s: g[0].startSeq, e: g[0].endSeq }, { c: 2, s: 1, e: 2 }),
    deq('E/断号另起一组', { c: g[1].count, s: g[1].startSeq, e: g[1].endSeq }, { c: 2, s: 4, e: 5 }),
    eq('E/工具结果行逐字', elisionLine(g[0]), '[2 tool/result entries elided: seqs 1-2]'),
    eq('E/其余条目行逐字', elisionLine(g[1]), '[2 earlier entries elided: seqs 4-5]')
  );

  /* ---- F. 阶梯取档：最小可用档，不跳档 ---- */
  // 阶梯按**忠实度降序**尝试，第一条能缩小的就是信息保留最多的方案。故取档正确性有两个方向：
  const fat = mixed(30, 500);    // 每条 500 token **>** L0 预算 128 ⇒ L0 真能省 ⇒ 应停在 L0（最忠实）
  const slim = mixed(60, 100);   // 每条 100 token **≤** L0 预算 ⇒ L0 等于全文照抄、省不下 ⇒ 必须升档
  const pFat = planCheckpoint({ entries: fat, retainTokens: 500, minSavingsTokens: 32, neededSavingsTokens: 0, ...FIELDS });
  const pSlim = planCheckpoint({ entries: slim, retainTokens: 100, minSavingsTokens: 32, neededSavingsTokens: 0, ...FIELDS });
  const pTiny = planCheckpoint({ entries: slim, retainTokens: 100, minSavingsTokens: 32, neededSavingsTokens: 4000, ...FIELDS });
  out.push(
    eq('F/大条目时停在 L0（最忠实）', pFat.rung, RUNG.L0_QUOTE),
    eq('F/大条目 L0 即可达标', pFat.ok, true),
    eq('F/★ 条目 ≤ L0 预算时 L0 省不下 ⇒ 必升档', pSlim.rung !== RUNG.L0_QUOTE, true),
    eq('F/★ 升档后仍然达标', pSlim.ok, true),
    // 要求节省 4000（远超 L1 能给的：L1 检点 ≈ 32×59+常量 ⇒ 省 ≈ 3900）⇒ 必须再升一档
    eq('F/要求提高后继续升档', pTiny.rung === RUNG.L2_DROP_TOOL_RESULTS || pTiny.rung === RUNG.L3_DROP_REST, true),
    okTrue('F/档位必在闭集内', RUNG_ORDER.includes(pSlim.rung) && RUNG_ORDER.includes(pTiny.rung)),
    okTrue('F/要求提高后节省量达标', pTiny.ok === false || pTiny.savings >= pTiny.requiredSavings),
    // 保活：可遮区不得越过保活窗口
    okTrue('F/保活窗口未被送进可遮区', pSlim.retainedTokens >= 100),
    okTrue('F/被遮区止于保活边界之前', pSlim.range.endSeq < slim.length)
  );

  /* ---- G. ★ 保证能减：canShrink 契约 + 报数自洽 ---- */
  out.push(
    okTrue('G/检定点严格小于被遮内容', pSlim.checkpointTokens < pSlim.shadowedTokens),
    eq('G/节省量 = 被遮 - 检点', pSlim.savings, pSlim.shadowedTokens - pSlim.checkpointTokens),
    eq('G/报数自洽(OK 路径)', pSlim.checkpointTokens, estimateTokens(pSlim.handoffText)),
    eq('G/shrinkVerdict 为 OK', pSlim.shrinkVerdict, SHRINK.OK),
    okTrue('G/影子 seqs 是两元素区间', Array.isArray(pSlim.shadowedSeqs) && pSlim.shadowedSeqs.length === 2),
    eq('G/区间起点=可遮区首条', pSlim.shadowedSeqs[0], 1)
  );

  /* ---- H. ★★ 负控 1（立论所系）：官方死锁态下本核仍能缩小 ---- */
  // 官方实测：摘要帧 3435 token ≥ 被遮内容 2466 token ⇒ 判"压不动"⇒ 硬死锁。
  // 构造同一数量的被遮内容（2466 token），看本核能否缩小。
  const deadlockContent = 41;                                    // 41 条 × 60 token = 2460 ≈ 2466
  const dl = mixed(deadlockContent, 60);
  const dlShadowed = dl.reduce((a, e) => a + e.tokens, 0);
  const OFFICIAL_SUMMARY_TOKENS = 3435;                          // 官方摘要帧实测值
  const dlPlan = planCheckpoint({ entries: dl, retainTokens: 0, minSavingsTokens: 32, neededSavingsTokens: 0, ...FIELDS });
  out.push(
    eq('H/造的态与被遮内容同量级', dlShadowed >= 2460 && dlShadowed <= 2470, true),
    okTrue('H/官方摘要帧确实大于被遮内容(死锁条件成立)', OFFICIAL_SUMMARY_TOKENS > dlShadowed),
    eq('H/★ 本核仍能缩小(官方在此死锁)', dlPlan.ok, true),
    okTrue('H/★ 检点远小于官方摘要帧', dlPlan.checkpointTokens < OFFICIAL_SUMMARY_TOKENS),
    okTrue('H/★ 达不到 L0 时确实升了档', dlPlan.rung !== RUNG.L0_QUOTE),
    okTrue('H/★ 节省量 ≥ 要求', dlPlan.savings >= dlPlan.requiredSavings),
    okTrue('H/被遮内容被完整记账(引文+省略=可遮条数)', dlPlan.quotedCount + dlPlan.elidedCount === dlPlan.range.count)
  );

  /* ---- I. 不可能态：如实报数、不静默（立项书 I1） ---- */
  const tinyOne = [{ seq: 1, kind: 'user/message', tokens: 4, text: 'abcd' }];
  const pImp = planCheckpoint({ entries: tinyOne, retainTokens: 0, minSavingsTokens: 100000, neededSavingsTokens: 0, ...FIELDS });
  const pNone = planCheckpoint({ entries: mixed(5, 10), retainTokens: 100000, minSavingsTokens: 32, ...FIELDS });
  const pEmpty = planCheckpoint({ entries: [], retainTokens: 100, minSavingsTokens: 32 });
  out.push(
    eq('I/压不动时 verdict=IMPOSSIBLE', pImp.verdict, PLAN.IMPOSSIBLE),
    eq('I/压不动时 ok=false', pImp.ok, false),
    okTrue('I/★ 压不动时带实测数字（不静默）', pImp.shadowedTokens > 0 && pImp.checkpointTokens > 0),
    okTrue('I/★ 压不动时 reason 含两组数字', /仍为 \d+ token/.test(pImp.reason) && /要求节省量 \d+/.test(pImp.reason)),
    eq('I/压不动时仍给出末档正文', typeof pImp.handoffText, 'string'),
    eq('I/★ 压不动时报数仍自洽', pImp.checkpointTokens, estimateTokens(pImp.handoffText)),
    eq('I/保活吃满 ⇒ NOTHING_TO_SHADOW', pNone.verdict, PLAN.NOTHING_TO_SHADOW),
    okTrue('I/NOTHING_TO_SHADOW 的 reason 说明保活', pNone.reason.includes('保活')),
    eq('I/空条目 ⇒ NOTHING_TO_SHADOW', pEmpty.verdict, PLAN.NOTHING_TO_SHADOW),
    eq('I/空条目时 checkpoints=0', pEmpty.checkpointTokens, 0)
  );

  /* ---- J. 逐位确定（同输入 ⇒ 同字节；无时钟无随机） ---- */
  const a1 = planCheckpoint({ entries: slim, retainTokens: 100, minSavingsTokens: 32, ...FIELDS });
  const a2 = planCheckpoint({ entries: slim, retainTokens: 100, minSavingsTokens: 32, ...FIELDS });
  out.push(
    eq('J/两次调用正文逐字节相同', a1.handoffText === a2.handoffText, true),
    eq('J/两次调用结论相同', describePlan(a1) === describePlan(a2), true),
    okTrue('J/正文不含时钟痕迹', !/\d{10,}/.test(a1.handoffText.replace(/seq /g, ''))),
    eq('J/describePlan 可读(含 rung)', /^plan=ok rung=[a-z0-9_]+ seqs=\d+-\d+ n=\d+/.test(describePlan(pFat)), true),
    eq('J/describePlan 对未达标态也可读', /^plan=plan_impossible ok=false/.test(describePlan(pImp)), true)
  );

  /* ---- K. quoteBudget 单调性（阶梯"每升一档必然更小"的骨架） ---- */
  const eMixed = [{ seq: 1, kind: 'tool/result', tokens: 500, text: 'x'.repeat(2000) }, { seq: 2, kind: 'tool/call', tokens: 500, text: 'x'.repeat(2000) }, { seq: 3, kind: 'user/message', tokens: 500, text: 'x'.repeat(2000) }];
  const budgets = RUNG_ORDER.map((r) => eMixed.map((e) => quoteBudget(e, r)));
  out.push(
    okTrue('K/★ 每升一档引文预算不增（逐条）', budgets.every((row, i) => i === 0 || row.every((v, j) => v <= budgets[i - 1][j])),
      budgets),
    eq('K/L0 工具结果按 128 截', budgets[0][0], 128),
    eq('K/L1 工具结果按 32 截', budgets[1][0], 32),
    eq('K/L2 工具结果不再引文', budgets[2][0], 0),
    eq('K/L3 全部不引文', budgets[3].reduce((a, v) => a + v, 0), 0),
    eq('K/★ 工具调用行在 L0 整行保留(不缩放)', budgets[0][1], 500),
    eq('K/★ 工具调用行在 L1 仍整行保留(不缩放)', budgets[1][1], 500),
    eq('K/工具调用行在 L3 一并丢弃', budgets[3][1], 0),
    err('K/拒未知档位', () => quoteBudget(eMixed[0], 'l9_nope'), 'BAD_RUNG')
  );

  /* ---- L. ★ 增量账 ≡ 真构建（优化的正确性必须由等价性钉死，不能由"结果没变"推断） ---- */
  // 造出各种丢弃/引文混合模式，特别是**连续同类段**与**断号**，以走到省略账的分组延长与新建两条路径。
  const pattern = ['tool/result', 'tool/result', 'tool/result', 'user/message', 'user/message',
    'tool/result', 'assistant/message', 'assistant/message', 'assistant/message', 'tool/result'];
  const eqEntries = Array.from({ length: 40 }, (_, i) => entry(i + 1, pattern[i % pattern.length], 60 + (i % 7) * 11));
  const mismatches = [];
  let compared = 0;
  for (const rung of RUNG_ORDER) {
    const acct = makeCharAccount(eqEntries, rung, FIELDS, CP_DEFAULTS, eqEntries.length);
    for (let k = 1; k <= eqEntries.length; k++) {
      const got = acct.push(k);
      const want = assemble(eqEntries, rung, FIELDS, CP_DEFAULTS, k).text.length;
      compared += 1;
      if (got !== want) mismatches.push({ rung, k, got, want, delta: got - want });
    }
  }
  out.push(
    deq('L/★ 增量账扫全 k 全档位与真构建逐位相同', mismatches.slice(0, 5), []),
    eq('L/比对点数 = 4 档 × 40 条', compared, 160),
    // 反控：故意用错档位驱动同一个账本，必须**能**测出不等（证明本判据不是恒真）
    (() => {
      const a = makeCharAccount(eqEntries, RUNG.L3_DROP_REST, FIELDS, CP_DEFAULTS, eqEntries.length);
      let wrong = 0;
      for (let k = 1; k <= eqEntries.length; k++) {
        const got = a.push(k);
        const want = assemble(eqEntries, RUNG.L0_QUOTE, FIELDS, CP_DEFAULTS, k).text.length;
        if (got !== want) wrong += 1;
      }
      return okTrue('L/反控：档位对不上时必须测出不等（判据非恒真）', wrong > 0, `不等的 k 有 ${wrong} 个`);
    })(),
    // 截断时如实标注（不假装扫完了）
    eq('L/maxScan 截断时标注 scanTruncated', planCheckpoint({ entries: mixed(50, 100), retainTokens: 0, maxScan: 10, ...FIELDS }).scanTruncated, true),
    eq('L/未截断时为 false', planCheckpoint({ entries: mixed(5, 100), retainTokens: 0, maxScan: 10, ...FIELDS }).scanTruncated, false)
  );

  /* ---- M. ★ 并发护栏（逐字复刻官方 assertNoActiveCompaction :504-507 / :513-516） ---- */
  const E = (type, seq) => ({ type, seq });
  const T = (type, seq, turn) => ({ type, seq, data: { turn } });
  const CASES = [
    // [名字, 事件流, **手写的**期望 busy] —— 期望值必须手写，不能拿自己的实现去算（那是循环论证）
    ['空流 ⇒ 不忙', [], false],
    ['只有 start ⇒ 忙', [E(EV.COMPACTION_START, 10)], true],
    ['start 后配 end ⇒ 不忙', [E(EV.COMPACTION_START, 10), E(EV.COMPACTION_END, 12)], false],
    ['★ start 未配对但后有更新 end-seed ⇒ 不忙（陈旧豁免）', [E(EV.COMPACTION_START, 10), E(EV.END_SEED, 20)], false],
    ['★ end-seed 早于未配对 start ⇒ 忙', [E(EV.END_SEED, 5), E(EV.COMPACTION_START, 10)], true],
    ['★ 倒扫语义：start,end,start ⇒ 忙（最后一个 start 未配对）', [E(EV.COMPACTION_START, 10), E(EV.COMPACTION_END, 12), E(EV.COMPACTION_START, 14)], true],
    ['start,end,start,end ⇒ 不忙', [E(EV.COMPACTION_START, 10), E(EV.COMPACTION_END, 12), E(EV.COMPACTION_START, 14), E(EV.COMPACTION_END, 16)], false],
    ['★ 陈旧豁免只在"更新"时成立（seq 相等不算更新）', [E(EV.COMPACTION_START, 10), E(EV.END_SEED, 10)], true],
    ['无关事件不干扰', [E('user/message', 1), E(EV.COMPACTION_START, 10), E('assistant/message', 11)], true],
    ['turn 开闭不干扰压缩判定', [T('turn/start', 1, 7), E(EV.COMPACTION_START, 10)], true]
  ];
  for (const [name, evs, want] of CASES) {
    const g = compactionGuardFrom(evs);
    out.push(
      eq(`M/${name}`, g.busy, want),
      // 独立对照：直接照官方 :505 那一行原式复算（不经本核的 activity 包装）
      eq(`M/与官方原式逐字一致 — ${name}`, g.busy, (() => {
        const st = inspectCompactionEntryState(evs);
        const u = st.unmatchedCompactionStart; const s = st.latestEndSeedSeq;
        return !(u === undefined || (s !== undefined && s > u.seq));
      })())
    );
  }
  out.push(
    // 陈旧豁免的**承重**证明：去掉 end-seed 就应当判忙 ⇒ 该判据不是装饰
    eq('M/★ 陈旧豁免承重：同一 start，去掉 end-seed 后必须转"忙"',
      compactionGuardFrom([E(EV.COMPACTION_START, 10)]).busy, true),
    eq('M/★ 陈旧豁免承重：有 end-seed 时判"不忙"', compactionGuardFrom([E(EV.COMPACTION_START, 10), E(EV.END_SEED, 20)]).busy, false),
    eq('M/陈旧时标 staleBySeed=true', compactionGuardFrom([E(EV.COMPACTION_START, 10), E(EV.END_SEED, 20)]).staleBySeed, true),
    eq('M/在途时 reason 说明不叠加', /不叠加/.test(compactionGuardFrom([E(EV.COMPACTION_START, 10)]).reason), true),
    // 观察器契约：读不到**绝不抛出**，如实报 ok:false
    eq('M/★ 非数组 ⇒ ok:false 而非抛出', compactionGuardFrom(null).ok, false),
    eq('M/非数组时 busy=false（保守放行，由调用方决断）', compactionGuardFrom(null).busy, false),
    eq('M/元素非对象 ⇒ 同样如实报错', compactionGuardFrom([{ type: 'x', seq: 1 }, 42]).ok, false),
    eq('M/坏输入不抛（返回而非 throw）', (() => { try { compactionGuardFrom(undefined); return 'no-throw'; } catch { return 'threw'; } })(), 'no-throw'),
    // openTurn 语义（官方 :674-679）
    eq('M/openTurn 读到未闭合 turn', inspectCompactionEntryState([T('turn/start', 1, 7), E('x', 2)]).openTurn, 7),
    eq('M/turn 已闭合 ⇒ openTurn=null', inspectCompactionEntryState([T('turn/start', 1, 7), E('turn/end', 2)]).openTurn, null),
    eq('M/endSeed 取最新', inspectCompactionEntryState([E(EV.END_SEED, 3), E(EV.END_SEED, 9)]).latestEndSeedSeq, 9),
    eq('M/describeGuardResult 可读', /concurrency=BUSY/.test(describeGuardResult(compactionGuardFrom([E(EV.COMPACTION_START, 10)]))), true),
    eq('M/describeGuardResult 标陈旧', /stale-start-ignored/.test(describeGuardResult(compactionGuardFrom([E(EV.COMPACTION_START, 10), E(EV.END_SEED, 20)]))), true),
  );
  out.push(
    eq('M/compactionActivity 无 start ⇒ 不忙', compactionActivity(undefined, undefined).busy, false),
    eq('M/compactionActivity 传 null start ⇒ 不忙', compactionActivity(null, 5).busy, false)
  );
  /* ---- N. ★ 工具配对平衡（逐字复刻官方 tool-pairing.js :9–100） ---- */
  const AM = (seq, nCalls) => ({ seq, type: 'assistant/message', data: { message: { content: Array.from({ length: nCalls }, () => ({ type: 'tool-call' })) } } });
  const TR = (seq) => ({ seq, type: 'tool/result' });
  const UM = (seq) => ({ seq, type: 'user/message' });
  // ★ `session.events` 是**按 seq 索引的数组**（官方 :21 `events[seq]`）⇒ 造数须把事件放在下标=seq 处
  const evIdx = (list) => { const a = []; for (const e of list) a[e.seq] = e; return a; };
  // 场景 A：完整的一对（2 调 3 结）
  const listA = [UM(1), AM(2, 1), TR(3), UM(4)];
  const evA = evIdx(listA);
  const nodesA = [1, 2, 3, 4];
  const cA = buildCutBalance(nodesA, evA);
  out.push(
    eq('N/空表面 ⇒ cutBalanced=[true]', JSON.stringify(buildCutBalance([], []).cutBalanced), '[true]'),
    // 官方 fold 语义（半开区间）：cut[0]=true，cut[i+1]=处理完 nodes[i] 后是否归零
    eq('N/★ 官方 fold 语义逐项', JSON.stringify(cA.cutBalanced), JSON.stringify([true, true, false, true, true])),
    eq('N/eventDelta: assistant 无 tool-call ⇒ 0', eventDelta(AM(1, 0)), 0),
    eq('N/eventDelta: assistant 3 个 tool-call ⇒ 3', eventDelta(AM(1, 3)), 3),
    eq('N/eventDelta: tool/result ⇒ -1', eventDelta(TR(2)), -1),
    eq('N/eventDelta: 其它类型 ⇒ 0', eventDelta({ type: 'turn/start', seq: 9 }), 0),
    // 官方 offsets：Before=cut[i]，After=cut[i+1]
    eq('N/Before(seq1)=cut[0]=true', balancedBefore(cA, 1), true),
    eq('N/After(seq1)=cut[1]=true', balancedAfter(cA, 1), true),
    eq('N/Before(seq2)=cut[1]=true', balancedBefore(cA, 2), true),
    eq('N/★ After(seq2)=cut[2]=false（劈开工具对）', balancedAfter(cA, 2), false),
    eq('N/★ Before(seq3)=cut[2]=false（劈开工具对）', balancedBefore(cA, 3), false),
    eq('N/After(seq3)=cut[3]=true', balancedAfter(cA, 3), true),
    eq('N/After 末节点=cut[n]=true', balancedAfter(cA, 4), true)
  );

  // 场景 B：孤立 tool/result（无前置调用）⇒ 官方抛错，本文件如实报错
  const evB = evIdx([TR(1)]);
  out.push(
    perr('N/★ 孤立 tool/result ⇒ 抛 UNMATCHED_RESULT（surface 损坏如实报）', () => buildCutBalance([1], evB), 'UNMATCHED_RESULT'),
    perr('N/seq 不在表面 ⇒ 抛 SEQ_NOT_ON_SURFACE', () => balancedBefore(cA, 999), 'SEQ_NOT_ON_SURFACE'),
    perr('N/事件缺失 ⇒ 抛 NO_MATCHING_EVENT', () => buildCutBalance([7], [UM(1)]), 'NO_MATCHING_EVENT'),
    perr('N/seq 不对齐 ⇒ 同样判损坏', () => buildCutBalance([2], [UM(1), UM(3)]), 'NO_MATCHING_EVENT'),
    perr('N/assistant content 非数组 ⇒ 如实报错', () => eventDelta({ type: 'assistant/message', seq: 1, data: { message: {} } }), 'BAD_MESSAGE_CONTENT'),
    // Map 形态与数组形态等价（离线造数便利，语义不变）
    eq('N/Map 与数组等价', JSON.stringify(buildCutBalance(nodesA, new Map(listA.map((e) => [e.seq, e]))).cutBalanced), JSON.stringify(cA.cutBalanced))
  );

  // 场景 C：findBalancedWindow —— 期望区间已合法 / 需收缩 / 无解
  const w1 = findBalancedWindow(nodesA, evA, 1, 4);
  const w2 = findBalancedWindow(nodesA, evA, 2, 3);
  // 场景 D：内层永远不闭合 ⇒ 终点收不回来 ⇒ 无解
  const evD = evIdx([AM(1, 1), UM(2)]);
  const nodesD = [1, 2];
  const wD = findBalancedWindow(nodesD, evD, 1, 2);
  out.push(
    eq('N/window 期望区间已合法 ⇒ ok', w1.ok, true),
    eq('N/window 起止逐字', `${w1.startSeq}-${w1.endSeq}`, '1-4'),
    eq('N/window 无位移', `${w1.startShift}/${w1.endShift}`, '0/0'),
    eq('N/window 恰好圈住一对工具调用 ⇒ ok', w2.ok, true),
    eq('N/window 圈住 2 条', w2.shadowedCount, 2),
    eq('N/★ 未闭合的 step ⇒ 拒绝（不硬来）', wD.ok, false),
    eq('N/★ 拒绝 reason 含"本步不动"', /本步不动/.test(wD.reason), true),
    eq('N/seq 不在表面 ⇒ 拒绝而非抛出', findBalancedWindow(nodesA, evA, 99, 101).ok, false),
    eq('N/起止倒置 ⇒ 拒绝', findBalancedWindow(nodesA, evA, 4, 1).ok, false),
    eq('N/表面损坏 ⇒ 拒绝而非抛出', findBalancedWindow([1], evB, 1, 1).ok, false),
    eq('N/describeWindow 可读', /^window=ok seqs=1-4 n=4/.test(describeWindow(w1)), true),
    eq('N/describeWindow 无解时标 none', /^window=none/.test(describeWindow(wD)), true),
    // ★ 负控（真对照）：朴素选法 = 「期望区间非空即接受」⇒ 它会接受 1-2；本判据必须拒绝。
    //   两者结论相反 ⇒ 证明本判据**有判别力**（不是恒真、不是空转）。
    okTrue('N/★ 负控：朴素选法接受 1-2 而本判据拒绝 ⇒ 判据有判别力',
      (() => { const naive = nodesD.length > 0; return naive === true && wD.ok === false; })(),
      `naive=${nodesD.length > 0} ours=${wD.ok}`)
  );

  /* ---- O. ★ 表面替换装配（含"合法切口掩码承重"负控） ---- */
  const N_ = (seq, tokens) => ({ seq, tokens });
  // 表面：node1 是"开了工具调用没结"的 assistant ⇒ 它之后的那个切口**非法**（会劈开工具对）
  const oNodes = [N_(1, 500), N_(2, 500), N_(3, 500)];
  const oEvList = [AM(1, 1), TR(2), UM(3)];
  const oEv = (() => { const a = []; for (const e of oEvList) a[e.seq] = e; return a; })();
  const oEntries = oNodes.map((n) => ({ seq: n.seq, kind: defaultEntryKind(oEv[n.seq]), tokens: n.tokens, text: defaultEntryText(oEv[n.seq]) }));
  const oPlanNoMask = planCheckpoint({ entries: oEntries, retainTokens: 0, minSavingsTokens: 32, ...FIELDS });
  const oRepl = buildReplacement({ nodes: oNodes, events: oEv, handoffFields: FIELDS, retainTokens: 0, minSavingsTokens: 32 });
  out.push(
    eq('O/装配成功', oRepl.ok, true),
    eq('O/★ 负控：不加掩码时会选中 k=1（劈开工具对）', oPlanNoMask.ok === true && oPlanNoMask.range.count === 1, true),
    okTrue('O/★ 承重：加掩码后避开了非法切口 k=1', oRepl.shadowedSeqs.length !== 1, `实得 ${oRepl.shadowedSeqs.length}`),
    eq('O/★ 被遮区间起点仍是最旧一条', oRepl.surfaceOp.start, 1),
    eq('O/★ 终点落在配对安全切口上', (() => {
      const c = buildCutBalance(oNodes.map((n) => n.seq), oEv);
      return c.cutBalanced[oRepl.shadowedSeqs.length];
    })(), true),
    eq('O/surfaceOp.op 逐字', oRepl.surfaceOp.op, 'replace'),
    eq('O/shadowedSeqs 恰为连续区间（start..end 无缺口）', oRepl.shadowedSeqs.join(','),
      Array.from({ length: oRepl.surfaceOp.end - oRepl.surfaceOp.start + 1 }, (_, i) => oRepl.surfaceOp.start + i).join(',')),
    eq('O/★ 契约：必须要求宿主尺复核', oRepl.requiresHostMeterCheck, true),
    okTrue('O/交接块正文非空且带 seq-range', oRepl.handoffText.includes(`<context_handoff v1 seq-range=${oRepl.surfaceOp.start}-${oRepl.surfaceOp.end}>`)),
    eq('O/describeReplacement 可读', /^replace=ok rung=/.test(describeReplacement(oRepl)), true),
    // 边界与失败态：一律**返回**而非抛出，且带 reason
    eq('O/空表面 ⇒ ok:false', buildReplacement({ nodes: [], events: [] }).ok, false),
    eq('O/nodes 非数组 ⇒ ok:false', buildReplacement({ nodes: null, events: [] }).ok, false),
    eq('O/事件流损坏 ⇒ ok:false 而非抛出', buildReplacement({ nodes: [N_(1, 10)], events: [], handoffFields: FIELDS }).ok, false),
    okTrue('O/失败态 reason 说明"本步不动"', /本步不动|无可替换/.test(buildReplacement({ nodes: [], events: [] }).reason)),
    eq('O/describeReplacement 失败态标 none', /^replace=none/.test(describeReplacement(buildReplacement({ nodes: [], events: [] }))), true),
    // defaultEntryText 尽力而为：取不到即空串（安全，不编造）
    eq('O/取文：抽到 content 内的 text 块', defaultEntryText({ seq: 1, type: 'user/message', data: { message: { content: [{ type: 'text', text: '甲' }] } } }), '甲'),
    eq('O/取文：多块以换行连接', defaultEntryText({ seq: 1, type: 'user/message', data: { message: { content: [{ text: 'A' }, { text: 'B' }] } } }), 'A\nB'),
    eq('O/取文：无 text 块的块被跳过', defaultEntryText({ seq: 1, type: 'assistant/message', data: { message: { content: [{ type: 'tool-call' }] } } }), ''),
    eq('O/★ 取文失败返回空串（不编造）', defaultEntryText({ seq: 1, type: 'tool/result', data: {} }), ''),
    eq('O/取文：非对象返回空串', defaultEntryText(null), ''),
    eq('O/kind 取不到报 unknown', defaultEntryKind({ seq: 1 }), 'unknown')
  );

  return out;
}

/** K3 全量自检。两个消费者共用（CLI 与 node:test）。 */
export function runK3SelfTest() {
  const raw = k3Cases();
  const cases = raw.map((c) => {
    const i = c.name.indexOf('/');
    return { suite: c.name.slice(0, i), name: c.name.slice(i + 1), ok: c.ok, got: c.got, want: c.want };
  });
  const failed = cases.filter((c) => !c.ok);
  const bySuite = {};
  for (const c of cases) bySuite[c.suite] = (bySuite[c.suite] || 0) + 1;
  return { ok: failed.length === 0, total: cases.length, failed: failed.length, bySuite, cases };
}

/** 逐位确定的证明用摘要（覆盖 套件/名字/是否通过/实得值）。 */
export function digestK3() {
  const r = runK3SelfTest();
  const canon = canonicalJson(r.cases.map((c) => ({ s: c.suite, n: c.name, ok: c.ok, got: c.got })));
  return { sha256: createHash('sha256').update(canon).digest('hex'), assertions: r.total, allPass: r.ok };
}
