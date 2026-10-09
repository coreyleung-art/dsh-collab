/**
 * k2-selftest.js — K2 自检（预算表 + 守卫行为）的**唯一来源**
 * =============================================================================
 * 两个消费者，同一份用例（避免两处漂）：
 *   · `cli.js --budget-check`  —— 进程内跑（本插件 ALLOWED_COMMANDS = []，连测试进程都不能起）；
 *   · `lib/guard.test.js`      —— 交给 node:test 驱动，逐条变成断言。
 *
 * 假宿主（fakeCtx / fakeSession / …）复刻的是**官方的真实形状**，不是我们想象的形状：
 *   requestHeader().config.{provider,model}  ← dsh-compaction-basic/lib/index.js:696
 *   agent.options.{provider,model}           ← 同 :705
 *   surface.replaceGeneration                ← 同 :810/:816/:824（溢出重试新鲜度，非并发护栏）
 *   并发护栏 assertNoActiveCompaction         ← 同 :513（:878 调用，读 session.events）
 *   tokenMeter.measure(session).totalTokens  ← 同 :859
 *   llm.resolveModelInfo(p, m, signal).context.contextWindow ← 同 :877
 *   官方触发比率 .8（⇒ 守卫须早于它）          ← 同 :13 + budget.js 的 preemptCeil
 */
import { createHash } from 'node:crypto';
import { observePressure, formatReading, budgetConfigFrom } from './guard.js';
import { DECISION, GUARD_REASON, SHRINK, canShrink, resolveBudget } from './budget.js';
import { runBudgetSelfTest, canonicalJson } from './budget-selftest.js';

/* ------------------------------- 假宿主 ------------------------------- */
export const fakeCtx = (services = {}) => ({ get: (n) => services[n] });
export const fakeSession = ({ provider = 'deepseek', model = 'deepseek-chat', generation = 0, headerThrows = false } = {}) => ({
  surface: { replaceGeneration: generation },
  requestHeader() {
    if (headerThrows) throw new Error('session 已销毁');
    return { config: { provider, model } };
  }
});
export const fakeMeter = (totalTokens) => ({ measure: () => ({ totalTokens }) });
export const fakeLlm = (contextWindow) => ({ resolveModelInfo: async () => ({ context: { contextWindow } }) });
export const payloadOf = (session, options = {}) => ({ agent: { session, options }, signal: { aborted: false } });

const norm = (v) => (Array.isArray(v) ? v.map(norm) : (v !== null && typeof v === 'object' ? { ...v } : v));
const eq = (name, got, want) => ({ name, ok: Object.is(got, want), got, want });
const deq = (name, got, want) => ({ name, ok: canonicalJson(norm(got)) === canonicalJson(norm(want)), got, want });

/* ------------------------------- 守卫用例 ------------------------------- */
/** @returns {Promise<Array<{name:string, ok:boolean, got:*, want:*}>>} 全部断言条（含逐条名字） */
export async function guardCases() {
  const out = [];
  const push = (...rs) => { for (const r of rs) out.push(r); };

  // G1 正常读数 —— 且证明"不动会话"
  {
    const session = fakeSession();
    const before = JSON.stringify(session.surface);
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(1000000), llm: fakeLlm(1048576) }), payloadOf(session), {});
    push(eq('G1 ok', r.ok, true),
      eq('G1 measured', r.measuredTokens, 1000000),
      deq('G1 target', r.target, { provider: 'deepseek', model: 'deepseek-chat', source: 'request-header' }),
      eq('G1 threshold', r.budget.threshold, 734003),
      eq('G1 thresholdSource', r.budget.thresholdSource, 'preempt'),
      eq('G1 早于官方', r.budget.preemptsOfficial, true),
      eq('G1 action', r.decision.action, DECISION.COMPRESS),
      eq('G1 overBy', r.decision.overBy, 265997),
      eq('G1 replaceGeneration', r.replaceGeneration, 0),
      eq('G1 会话表面未变', JSON.stringify(session.surface) === before, true),
      eq('G1 冻结', Object.isFrozen(r) && Object.isFrozen(r.decision), true));
  }

  // G2 未达阈值
  {
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(500000), llm: fakeLlm(1048576) }), payloadOf(fakeSession()), {});
    push(eq('G2 action', r.decision.action, DECISION.SKIP_BELOW_THRESHOLD), eq('G2 headroom', r.decision.headroom, 234003));
  }

  // G3 config 覆盖
  {
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(1), llm: fakeLlm(10000) }), payloadOf(fakeSession()),
      { usableRatio: 0.8, limitRatio: 0.5, maxTokens: 4000, bufferTokens: 100 });
    push(eq('G3 usable', r.budget.usable, 8000), eq('G3 limitBase', r.budget.limitBase, 5000),
      eq('G3 limit', r.budget.limit, 4000), eq('G3 threshold', r.budget.threshold, 4100));
  }

  // G4 回退到 agent.options
  {
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(10), llm: fakeLlm(8192) }),
      { agent: { session: fakeSession({ provider: '', model: '' }), options: { provider: 'openai', model: 'gpt' } }, signal: {} }, {});
    push(eq('G4 ok', r.ok, true), eq('G4 source', r.target.source, 'agent-options'), eq('G4 provider', r.target.provider, 'openai'));
  }

  // G5 五种"读不到"各自如实报告
  {
    const p = payloadOf(fakeSession());
    const cases = [
      ['no_token_meter', fakeCtx({ llm: fakeLlm(8192) }), p],
      ['no_session', fakeCtx({ tokenMeter: fakeMeter(1), llm: fakeLlm(8192) }), { agent: {}, signal: {} }],
      ['no_llm', fakeCtx({ tokenMeter: fakeMeter(1) }), p],
      ['no_context_window', fakeCtx({ tokenMeter: fakeMeter(1), llm: fakeLlm(undefined) }), p],
      ['no_target', fakeCtx({ tokenMeter: fakeMeter(1), llm: fakeLlm(8192) }),
        { agent: { session: fakeSession({ provider: '', model: '' }), options: {} }, signal: {} }]
    ];
    for (const [want, ctx, payload] of cases) {
      const r = await observePressure(ctx, payload, {});
      push(eq(`G5 ${want} ok=false`, r.ok, false), eq(`G5 ${want} reason`, r.reason, GUARD_REASON[want.toUpperCase()]));
    }
  }

  // G6 内部抛错不外泄（观察器的契约：绝不抛给调用方）
  {
    const r1 = await observePressure(fakeCtx({ tokenMeter: { measure: () => { throw new Error('meter 崩'); } }, llm: fakeLlm(8192) }), payloadOf(fakeSession()), {});
    push(eq('G6 measure 抛 → measure_failed', r1.reason, 'measure_failed'));
    const r2 = await observePressure(fakeCtx({ tokenMeter: fakeMeter(1), llm: fakeLlm(8192) }), payloadOf(fakeSession({ headerThrows: true })), {});
    push(eq('G6 requestHeader 抛 → no_target', r2.reason, GUARD_REASON.NO_TARGET));
    const badLlm = { resolveModelInfo: async () => { throw new Error('适配器离线'); } };
    const r3 = await observePressure(fakeCtx({ tokenMeter: fakeMeter(1), llm: badLlm }), payloadOf(fakeSession()), {});
    push(eq('G6 resolveModelInfo 抛 → resolve_model_failed', r3.reason, 'resolve_model_failed'));
  }

  // G7 measure() 不给 totalTokens
  {
    const r = await observePressure(fakeCtx({ tokenMeter: { measure: () => ({}) }, llm: fakeLlm(8192) }), payloadOf(fakeSession()), {});
    push(eq('G7 reason', r.reason, 'measure_no_total'));
  }

  // G8 并发护栏入参透传（K3 启用，此处证明接口已通）
  {
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(1000000), llm: fakeLlm(1048576) }), payloadOf(fakeSession()), {}, { hasOpenCompaction: true });
    push(eq('G8 action', r.decision.action, DECISION.SKIP_COMPACTION_IN_PROGRESS));
  }

  // G9 formatReading 只描述、且明写 measure-only
  {
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(1000000), llm: fakeLlm(1048576) }), payloadOf(fakeSession()), {});
    const line = formatReading(r);
    push(eq('G9 含 breath=compress', /breath=compress/.test(line), true),
      eq('G9 含 measure-only', /measure-only/.test(line), true),
      eq('G9 跳过行', formatReading({ ok: false, reason: 'no_llm' }), 'breath=skip reason=no_llm'));
  }

  // G10 budgetConfigFrom
  {
    push(deq('G10 换算', budgetConfigFrom({ usableRatio: 0.95, limitRatio: 0.9, preemptRatio: 0.7, maxTokens: 65536, bufferTokens: 100 }),
      { usablePct: 95, limitPct: 90, preemptPct: 70, configCap: 65536, bufferTokens: 100 }),
    deq('G10 空配置', budgetConfigFrom({}), { bufferTokens: 8000 }));
    let code = null;
    try { budgetConfigFrom({ usableRatio: 1.5 }); } catch (e) { code = e.code; }
    push(eq('G10 非法比率抛错', code, 'BAD_RATIO'));
  }

  // G11 与下界判据串起来 —— 观察器说"该压了"，下界判据说"官方那种压法压不动"
  {
    const r = canShrink({ shadowedTokens: 2466, checkpointTokens: 3435 });
    push(eq('G11 verdict', r.verdict, SHRINK.IMPOSSIBLE), eq('G11 savings<0', r.savings < 0, true));
  }

  // G12 config→预算的**真接线**：preemptRatio 必须真的到达 resolveBudget，且 ≥0.8 被拒
  //     （F1 裁决「抢先」的行为面；只断言 budgetConfigFrom 的映射是不够的，那只是字符串搬运）
  {
    const budget = resolveBudget({ contextWindow: 1048576, ...budgetConfigFrom({ usableRatio: 0.95, limitRatio: 0.9, preemptRatio: 0.7 }) });
    push(eq('G12 接线 preemptPct', budget.preemptPct, 70), eq('G12 接线 threshold', budget.threshold, 734003),
      eq('G12 接线早于官方', budget.preemptsOfficial, true));
    let code = null;
    try { resolveBudget({ contextWindow: 8192, ...budgetConfigFrom({ preemptRatio: 0.8 }) }); } catch (e) { code = e.code; }
    push(eq('G12 preemptRatio=0.8 被拒（= 放弃抢先）', code, 'BAD_PREEMPT'));
    // 观察器整条路上也要能看出"早于官方"——formatReading 里带 summary
    const r = await observePressure(fakeCtx({ tokenMeter: fakeMeter(800000), llm: fakeLlm(1048576) }), payloadOf(fakeSession()), {});
    push(eq('G12 读数早于官方', r.budget.preemptsOfficial, true),
      eq('G12 日志含 preempts=true', /preempts=true/.test(formatReading(r)), true));
  }

  return out;
}

/** K2 全量自检（预算表 + 守卫行为）。两个消费者共用。 */
export async function runK2SelfTest() {
  const budget = runBudgetSelfTest();
  const guard = await guardCases();
  const cases = [
    ...budget.cases.map((c) => ({ suite: 'budget', name: `${c.group}/${c.case}/${c.name}`, ok: c.ok, got: c.got, want: c.want })),
    ...guard.map((c) => ({ suite: 'guard', name: c.name, ok: c.ok, got: c.got, want: c.want }))
  ];
  const failed = cases.filter((c) => !c.ok);
  return { ok: failed.length === 0, total: cases.length, failed: failed.length, bySuite: { budget: budget.total, guard: guard.length }, cases };
}

/** 逐位确定的证明用摘要（覆盖 名字/是否通过/实得值）。 */
export async function digest() {
  const r = await runK2SelfTest();
  const canon = canonicalJson(r.cases.map((c) => ({ s: c.suite, n: c.name, ok: c.ok, got: c.got })));
  return { sha256: createHash('sha256').update(canon).digest('hex'), assertions: r.total, allPass: r.ok };
}
