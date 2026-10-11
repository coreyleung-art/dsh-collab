/**
 * guard.test.js — lib/guard.js 的离线单测（node:test；零 dsh 依赖）
 * =============================================================================
 *   node --test lib/guard.test.js
 *
 * 用例本体在 lib/k2-selftest.js（与 `cli.js --budget-check` 共用同一份，避免两处漂）；
 * 本文件只是把它交给 node:test，并补上几条**跨用例的不变量**（扫描式断言，不是逐例）。
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { guardCases, runK2SelfTest, fakeCtx, fakeMeter, fakeLlm, fakeSession, payloadOf } from './k2-selftest.js';
import { observePressure } from './guard.js';
import { DECISION, resolveBudget, decide, BUDGET_DEFAULTS } from './budget.js';

test('K2 守卫用例全绿（每条期望值都是手写的）', async () => {
  const cases = await guardCases();
  const bad = cases.filter((c) => !c.ok);
  assert.equal(bad.length, 0,
    bad.map((c) => `  ✗ ${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`).join('\n'));
  assert.ok(cases.length >= 30, `断言条数应 ≥30，实得 ${cases.length}`);
});

test('K2 全量自检（预算 + 守卫）全绿且分组计数自洽', async () => {
  const r = await runK2SelfTest();
  assert.equal(r.failed, 0);
  assert.equal(r.bySuite.budget + r.bySuite.guard, r.total);
  assert.ok(r.bySuite.guard >= 30, `守卫侧断言应 ≥30，实得 ${r.bySuite.guard}`);
});

test('观察器不改会话：surface 与 agent 在调用前后逐位相同', async () => {
  const session = fakeSession();
  const agent = { session, options: { provider: 'p', model: 'm' } };
  const before = JSON.stringify(agent);
  await observePressure(fakeCtx({ tokenMeter: fakeMeter(1000000), llm: fakeLlm(1048576) }), { agent, signal: {} }, {});
  assert.equal(JSON.stringify(agent), before);
});

test('扫描：任意窗口/任意测量值下，观察器都不会让 measured > usable 而判"未达阈值"', async () => {
  const ctx = fakeCtx({ tokenMeter: fakeMeter(0), llm: fakeLlm(8192) });
  for (let t = 0; t <= 9000; t += 613) {
    const ctxT = fakeCtx({ tokenMeter: fakeMeter(t), llm: fakeLlm(8192) });
    const r = await observePressure(ctxT, payloadOf(fakeSession()), {});
    const above = t >= r.budget.threshold;
    assert.equal(r.decision.action === DECISION.COMPRESS, above, `t=${t} threshold=${r.budget.threshold}`);
  }
  const r0 = await observePressure(ctx, payloadOf(fakeSession()), {});
  assert.equal(r0.ok, true);
});

test('预算与判定的合成性质在窗口扫描下保持', () => {
  for (const cw of [1024, 8192, 32768, 131072, 1048576]) {
    const b = resolveBudget({ contextWindow: cw });
    for (const t of [0, 1, b.threshold - 1, b.threshold, b.usable, cw]) {
      const d = decide({ measuredTokens: Math.max(0, t), budget: b });
      assert.equal(d.action === DECISION.COMPRESS, Math.max(0, t) >= b.threshold);
    }
  }
  assert.equal(BUDGET_DEFAULTS.usablePct, 95);
});
