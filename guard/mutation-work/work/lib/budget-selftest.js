/**
 * budget-selftest.js — lib/budget.js 的**可复算自检表**（纯离线，无模型、无会话、无 I/O）
 * =============================================================================
 * 为什么自检表要在 lib/ 里而不是只在 test 文件里：
 *   ① `--budget-check` 必须在不 spawn 任何进程的前提下跑得起来（本插件 ALLOWED_COMMANDS = []，
 *      连 `node --test` 都不能起）⇒ 自检逻辑必须在**进程内**可调用；
 *   ② 每一条期望值都是**手算**写死的（不是用同一段代码算出来的），所以它是一次真正的对拍，
 *      而不是自我循环（R030：断言的值必须独立于被测代码得来）。
 *
 * ★ 逐位确定的证明方式：digest() 把整张结果表规范化成字符串再取 sha256。
 *   两次独立进程运行若得同一 digest ⇒ 本核逐位确定（同 P4b「跨进程 + 磁盘往返」的做法）。
 *   digest 只覆盖 (名字, 是否通过, 实得值)，覆盖不到"期望值"——期望值由 test 文件单独钉。
 */
import { createHash } from 'node:crypto';
import {
  BUDGET_DEFAULTS, DECISION, GUARD_REASON, SHRINK, OFFICIAL_THRESHOLD_PCT,
  BudgetError, pctFromRatio, resolveBudget, pickTarget, decide, canShrink, describeBudget, advisoryTokens
} from './budget.js';

/** 规范 JSON：键序无关（递归排序），供 digest 使用。 */
export function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort()
      .map((k) => JSON.stringify(k) + ':' + canonicalJson(value[k])).join(',') + '}';
  }
  return JSON.stringify(value === undefined ? null : value);
}

const ok = (name, got, want) => ({ name, kind: 'case', ok: Object.is(got, want), got, want });
const err = (name, fn, wantCode) => {
  try { fn(); return { name, kind: 'error', ok: false, got: '(未抛错)', want: wantCode }; }
  catch (e) { return { name, kind: 'error', ok: e instanceof BudgetError && e.code === wantCode, got: e instanceof BudgetError ? e.code : String(e && e.message), want: wantCode }; }
};
const deep = (name, got, want) => ({ name, kind: 'deep', ok: canonicalJson(got) === canonicalJson(want), got, want });

/** 大窗口 = 官方 deepseek 1M 上下文；小窗口 = 本机 nano 的 8192。 */
export const CASES = Object.freeze([
  // ---- resolveBudget ----
  { group: 'resolveBudget', name: 'B1 默认 1M（阈值由抢先上限决定）', run: () => {
    const b = resolveBudget({ contextWindow: 1048576 });
    return [ok('usable', b.usable, 996147), ok('limitBase', b.limitBase, 943718), ok('limit', b.limit, 943718),
      ok('preemptCeil', b.preemptCeil, 734003), ok('threshold', b.threshold, 734003), ok('src', b.thresholdSource, 'preempt'),
      ok('official', b.officialThreshold, 838860), ok('preempts', b.preemptsOfficial, true), ok('configCap', b.configCap, null)];
  } },
  { group: 'resolveBudget', name: 'B2 cap 更小则 cap 生效（且此时抢先前于上限）', run: () => {
    const b = resolveBudget({ contextWindow: 1048576, configCap: 100000 });
    return [ok('limit', b.limit, 100000), ok('threshold', b.threshold, 108000), ok('src', b.thresholdSource, 'limit+buffer')];
  } },
  { group: 'resolveBudget', name: 'B3 cap 更大则不生效', run: () => {
    const b = resolveBudget({ contextWindow: 1048576, configCap: 983040 });
    return [ok('limit', b.limit, 943718), ok('threshold', b.threshold, 734003), ok('src', b.thresholdSource, 'preempt')];
  } },
  { group: 'resolveBudget', name: 'B4 小窗口：加性 buffer 会被 usable 夹住，但抢先上限仍生效', run: () => {
    const b = resolveBudget({ contextWindow: 8192 });
    return [ok('usable', b.usable, 7782), ok('limit', b.limit, 7372), ok('threshold', b.threshold, 5734),
      ok('src', b.thresholdSource, 'preempt'), ok('preempts', b.preemptsOfficial, true)];
  } },
  { group: 'resolveBudget', name: 'B5 buffer=0', run: () => {
    const b = resolveBudget({ contextWindow: 8192, bufferTokens: 0 });
    return [ok('threshold', b.threshold, 5734), ok('src', b.thresholdSource, 'preempt')];
  } },
  { group: 'resolveBudget', name: 'B6 cw=1000（buffer 远大于窗口）', run: () => {
    const b = resolveBudget({ contextWindow: 1000 });
    return [ok('usable', b.usable, 950), ok('limit', b.limit, 900), ok('threshold', b.threshold, 700), ok('src', b.thresholdSource, 'preempt')];
  } },
  { group: 'resolveBudget', name: 'B7 自定义百分比（阈值远低于上限时抢先用不上）', run: () => {
    const b = resolveBudget({ contextWindow: 10000, usablePct: 80, limitPct: 50, bufferTokens: 100 });
    return [ok('usable', b.usable, 8000), ok('limit', b.limit, 5000), ok('threshold', b.threshold, 5100), ok('src', b.thresholdSource, 'limit+buffer')];
  } },
  { group: 'resolveBudget', name: 'B8 返回值冻结', run: () => {
    const b = resolveBudget({ contextWindow: 8192 });
    return [ok('frozen', Object.isFrozen(b), true)];
  } },
  { group: 'resolveBudget', name: 'B9 非法输入全抛错（不静默 clamp）', run: () => [
    err('cw=0', () => resolveBudget({ contextWindow: 0 }), 'BAD_CONTEXT_WINDOW'),
    err('cw=1.5', () => resolveBudget({ contextWindow: 1.5 }), 'BAD_CONTEXT_WINDOW'),
    err('cw 缺失', () => resolveBudget({}), 'BAD_CONTEXT_WINDOW'),
    err('usablePct=101', () => resolveBudget({ contextWindow: 1000, usablePct: 101 }), 'BAD_PCT'),
    err('limitPct=0', () => resolveBudget({ contextWindow: 1000, limitPct: 0 }), 'BAD_PCT'),
    err('buffer=-1', () => resolveBudget({ contextWindow: 1000, bufferTokens: -1 }), 'BAD_BUFFER'),
    err('cap=-5', () => resolveBudget({ contextWindow: 1000, configCap: -5 }), 'BAD_CAP'),
    err('preemptPct=0', () => resolveBudget({ contextWindow: 1000, preemptPct: 0 }), 'BAD_PREEMPT'),
    err('preemptPct=80（= 官方比率 ⇒ 放弃抢先）', () => resolveBudget({ contextWindow: 1000, preemptPct: 80 }), 'BAD_PREEMPT'),
    err('preemptPct=100', () => resolveBudget({ contextWindow: 1000, preemptPct: 100 }), 'BAD_PREEMPT'),
    err('preemptPct=1.5', () => resolveBudget({ contextWindow: 1000, preemptPct: 1.5 }), 'BAD_PREEMPT')
  ] },

  // ---- pctFromRatio ----
  { group: 'pctFromRatio', name: 'B10 换算与拒绝', run: () => [
    ok('0.95→95', pctFromRatio(0.95), 95),
    ok('0.7→70', pctFromRatio(0.7), 70),
    ok('1→100', pctFromRatio(1), 100),
    err('0', () => pctFromRatio(0), 'BAD_RATIO'),
    err('1.5', () => pctFromRatio(1.5), 'BAD_RATIO'),
    err('字符串', () => pctFromRatio('0.9'), 'BAD_RATIO')
  ] },

  // ---- decide（用 B1 的预算：threshold = 734003，来源 preempt） ----
  { group: 'decide', name: 'B11 未达阈值', run: () => {
    const budget = resolveBudget({ contextWindow: 1048576 });
    const d = decide({ measuredTokens: 700000, budget });
    return [ok('action', d.action, DECISION.SKIP_BELOW_THRESHOLD), ok('headroom', d.headroom, 34003), ok('overBy', d.overBy, -34003)];
  } },
  { group: 'decide', name: 'B12 恰好等于阈值 ⇒ 压（与官方 < 判据一致）', run: () => {
    const budget = resolveBudget({ contextWindow: 1048576 });
    const d = decide({ measuredTokens: 734003, budget });
    return [ok('action', d.action, DECISION.COMPRESS), ok('overBy', d.overBy, 0), ok('thresholdSource', d.thresholdSource, 'preempt')];
  } },
  { group: 'decide', name: 'B13 差 1 ⇒ 不压（边界）', run: () => {
    const budget = resolveBudget({ contextWindow: 1048576 });
    const d = decide({ measuredTokens: 734002, budget });
    return [ok('action', d.action, DECISION.SKIP_BELOW_THRESHOLD), ok('headroom', d.headroom, 1)];
  } },
  { group: 'decide', name: 'B14 超阈', run: () => {
    const budget = resolveBudget({ contextWindow: 1048576 });
    const d = decide({ measuredTokens: 1000000, budget });
    return [ok('action', d.action, DECISION.COMPRESS), ok('overBy', d.overBy, 265997), ok('pressure', d.pressure, 0.953674)];
  } },
  { group: 'decide', name: 'B15 并发护栏优先于阈值', run: () => {
    const budget = resolveBudget({ contextWindow: 1048576 });
    const d = decide({ measuredTokens: 1000000, budget, hasOpenCompaction: true });
    return [ok('action', d.action, DECISION.SKIP_COMPACTION_IN_PROGRESS), ok('overBy', d.overBy, 265997)];
  } },
  { group: 'decide', name: 'B15b 官方阈值尚未到时本守卫已触发（抢先的直接证据）', run: () => {
    const budget = resolveBudget({ contextWindow: 1048576 });
    // 官方 = floor(1048576×0.8) = 838860；810000 落在「本守卫已触发、官方还没到」那一带。
    const d = decide({ measuredTokens: 810000, budget });
    return [ok('本守卫压', d.action, DECISION.COMPRESS), ok('官方未到', 810000 < budget.officialThreshold, true),
      ok('区间宽度', budget.officialThreshold - budget.threshold, 104857)];
  } },
  { group: 'decide', name: 'B16 非法输入', run: () => [
    err('measured=-1', () => decide({ measuredTokens: -1, budget: resolveBudget({ contextWindow: 8192 }) }), 'BAD_MEASURED'),
    err('budget=null', () => decide({ measuredTokens: 1, budget: null }), 'BAD_BUDGET'),
    err('budget 缺 threshold', () => decide({ measuredTokens: 1, budget: {} }), 'BAD_BUDGET')
  ] },
  { group: 'decide', name: 'B17 返回值冻结', run: () => {
    const d = decide({ measuredTokens: 1, budget: resolveBudget({ contextWindow: 8192 }) });
    return [ok('frozen', Object.isFrozen(d), true)];
  } },

  // ---- canShrink（P26 机制二本体；2466 / 3435 是真实事故数字） ----
  { group: 'canShrink', name: 'B18 真实死锁：被遮 2466 / 摘要 3435', run: () => {
    const r = canShrink({ shadowedTokens: 2466, checkpointTokens: 3435 });
    return [ok('ok', r.ok, false), ok('verdict', r.verdict, SHRINK.IMPOSSIBLE), ok('savings', r.savings, -969), ok('savingsPct', r.savingsPct, -40)];
  } },
  { group: 'canShrink', name: 'B19 够省才放行', run: () => {
    const r = canShrink({ shadowedTokens: 2466, checkpointTokens: 2400 });
    return [ok('ok', r.ok, true), ok('verdict', r.verdict, SHRINK.OK), ok('savings', r.savings, 66), ok('savingsPct', r.savingsPct, 2)];
  } },
  { group: 'canShrink', name: 'B20 省得不够（10 < 32）', run: () => {
    const r = canShrink({ shadowedTokens: 100, checkpointTokens: 90 });
    return [ok('ok', r.ok, false), ok('savings', r.savings, 10), ok('savingsPct', r.savingsPct, 10)];
  } },
  { group: 'canShrink', name: 'B21 余额恰好等于门槛', run: () => {
    return [ok('32≥32 ok', canShrink({ shadowedTokens: 32, checkpointTokens: 0 }).ok, true),
      ok('31≥32 不 ok', canShrink({ shadowedTokens: 31, checkpointTokens: 0 }).ok, false)];
  } },
  { group: 'canShrink', name: 'B22 无可遮内容', run: () => {
    const r = canShrink({ shadowedTokens: 0, checkpointTokens: 0 });
    return [ok('ok', r.ok, false), ok('verdict', r.verdict, SHRINK.NOTHING_TO_SHADOW), ok('savingsPct', r.savingsPct, 0)];
  } },
  { group: 'canShrink', name: 'B23 非法输入', run: () => [
    err('shadowed=字符串', () => canShrink({ shadowedTokens: 'x', checkpointTokens: 1 }), 'BAD_SHADOWED'),
    err('checkpoint=-1', () => canShrink({ shadowedTokens: 10, checkpointTokens: -1 }), 'BAD_CHECKPOINT'),
    err('minSavings=-1', () => canShrink({ shadowedTokens: 10, checkpointTokens: 1, minSavingsTokens: -1 }), 'BAD_MIN_SAVINGS')
  ] },

  // ---- pickTarget（与官方 routedTarget / conversationTarget 同序） ----
  { group: 'pickTarget', name: 'B24 首选请求头', run: () => {
    return [deep('header 优先', pickTarget({ provider: 'p', model: 'm' }, { provider: 'x', model: 'y' }), { provider: 'p', model: 'm', source: 'request-header' })];
  } },
  { group: 'pickTarget', name: 'B25 请求头为空则用 agent.options', run: () => [
    deep('空 header', pickTarget({ provider: '', model: 'm' }, { provider: 'p', model: 'm' }), { provider: 'p', model: 'm', source: 'agent-options' }),
    deep('undefined header', pickTarget(undefined, { provider: 'p', model: 'm' }), { provider: 'p', model: 'm', source: 'agent-options' })
  ] },
  { group: 'pickTarget', name: 'B26 都取不到 ⇒ null（不抛错）', run: () => [
    ok('都空', pickTarget(undefined, undefined), null),
    ok('空对象', pickTarget({}, {}), null),
    ok('model 空串', pickTarget({ provider: 'p', model: '' }, { provider: '', model: '' }), null)
  ] },

  // ---- describeBudget / advisoryTokens ----
  { group: 'misc', name: 'B27 describeBudget', run: () => [
    ok('无 cap', describeBudget(resolveBudget({ contextWindow: 8192 })),
      'cw=8192 usable=7782 limit=7372 threshold=5734 src=preempt ceil=5734 official=6553 preempts=true (usablePct=95% limitPct=90% preemptPct=70% buffer=8000)'),
    ok('有 cap', describeBudget(resolveBudget({ contextWindow: 8192, configCap: 1000 })),
      'cw=8192 usable=7782 limit=1000 threshold=5734 src=preempt ceil=5734 official=6553 preempts=true (usablePct=95% limitPct=90% preemptPct=70% buffer=8000 cap=1000)')
  ] },
  { group: 'misc', name: 'B28 advisoryTokens 默认不改行为', run: () => {
    const a = advisoryTokens(1000);
    return [ok('effective==measured', a.effectiveTokens, 1000), ok('applied', a.applied, false), ok('factor', a.factor, 1)];
  } },
  { group: 'misc', name: 'B29 advisoryTokens 显式 4×', run: () => {
    const a = advisoryTokens(1000, 4);
    return [ok('effective', a.effectiveTokens, 4000), ok('applied', a.applied, true)];
  } },
  { group: 'misc', name: 'B30 advisoryTokens 非法', run: () => [
    err('factor=0.5', () => advisoryTokens(1000, 0.5), 'BAD_FACTOR'),
    err('measured=-1', () => advisoryTokens(-1), 'BAD_MEASURED')
  ] },
  { group: 'misc', name: 'B31 环境原因码齐全且冻结', run: () => [
    ok('reason 数', Object.keys(GUARD_REASON).length, 5),
    ok('冻结', Object.isFrozen(GUARD_REASON) && Object.isFrozen(DECISION) && Object.isFrozen(SHRINK) && Object.isFrozen(BUDGET_DEFAULTS), true),
    ok('官方比率常量', OFFICIAL_THRESHOLD_PCT, 80),
    ok('默认抢先低于官方', BUDGET_DEFAULTS.preemptPct < OFFICIAL_THRESHOLD_PCT, true)
  ] },

  // ---- preempt（F1 裁决「抢先」的不变式：把设计决定做成可跑的判据） ----
  { group: 'preempt', name: 'B32 抢先不变式：任何 cw 下 threshold < 官方阈值', run: () => {
    // 官方 = floor(cw × 0.8)（dsh-compaction-basic:13）。本守卫阈值必须严格更早。
    return [1000, 4096, 8192, 10000, 131072, 200000, 400000, 1048576, 2000000].map((cw) => {
      const b = resolveBudget({ contextWindow: cw });
      const official = Math.floor((cw * OFFICIAL_THRESHOLD_PCT) / 100);
      return ok(`cw=${cw}（${b.threshold} < ${official}）`, b.threshold < official && b.preemptsOfficial === true, true);
    });
  } },
  { group: 'preempt', name: 'B33 显式 preemptPct：范围端点与夹取', run: () => {
    const half = resolveBudget({ contextWindow: 1048576, preemptPct: 50 });
    const top = resolveBudget({ contextWindow: 1048576, preemptPct: 79 });
    const tiny = resolveBudget({ contextWindow: 1000, preemptPct: 79 });
    return [ok('50% → ceil', half.preemptCeil, 524288), ok('50% → threshold', half.threshold, 524288), ok('50% src', half.thresholdSource, 'preempt'),
      ok('79% → ceil', top.preemptCeil, 828375), ok('79% 仍早于官方', top.preemptsOfficial, true),
      ok('小窗 79% 仍取 ceil 而非 usable', tiny.threshold, 790)];
  } }
]);

/** 跑全表。返回 { ok, total, failed, cases }。 */
export function runBudgetSelfTest() {
  const cases = [];
  for (const c of CASES) {
    let results;
    try { results = c.run(); }
    catch (e) { results = [{ name: '(整个用例抛错)', ok: false, got: String(e && e.message), want: '不抛错' }]; }
    for (const r of results) cases.push({ group: c.group, case: c.name, ...r });
  }
  const failed = cases.filter((c) => !c.ok);
  return { ok: failed.length === 0, total: cases.length, failed: failed.length, cases };
}

/** 逐位确定的证明用摘要：只覆盖 (group, case, name, ok, got)。 */
export function digest() {
  const r = runBudgetSelfTest();
  const canon = canonicalJson(r.cases.map((c) => ({ g: c.group, c: c.case, n: c.name, ok: c.ok, got: c.got })));
  return { sha256: createHash('sha256').update(canon).digest('hex'), assertions: r.total, allPass: r.ok };
}
