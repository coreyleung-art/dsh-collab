/**
 * budget.test.js — lib/budget.js 的离线单测（node:test；零 dsh 依赖，可直接跑）
 * =============================================================================
 *   node --test lib/budget.test.js          # 在插件目录内
 *
 * 为什么可以跑：budget.js / budget-selftest.js **不 import 任何 dsh/cordis 模块**，
 * 也不做任何 I/O —— 它只是数字进、数字出。这与 K1 的约束一致：
 * "不执行插件代码" 指不跑 apply() / 不拉起插件树；纯决策核的离线对拍是它的验收手段本身。
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { runBudgetSelfTest, digest, CASES } from './budget-selftest.js';
import * as B from './budget.js';

test('自检表全绿（每条例子的期望值是手算写死的，不是同段代码算出来的）', () => {
  const r = runBudgetSelfTest();
  if (!r.ok) {
    const bad = r.cases.filter((c) => !c.ok)
      .map((c) => `  ✗ ${c.group} / ${c.case} / ${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`)
      .join('\n');
    assert.fail(`自检表 ${r.failed}/${r.total} 条不符：\n${bad}`);
  }
  assert.equal(r.failed, 0);
  assert.ok(r.total >= 60, `断言条数应 ≥60，实得 ${r.total}`);
});

test('用例表本身非空且分组齐全', () => {
  assert.ok(CASES.length >= 25, `用例数应 ≥25，实得 ${CASES.length}`);
  const groups = new Set(CASES.map((c) => c.group));
  for (const g of ['resolveBudget', 'decide', 'canShrink', 'pickTarget', 'misc']) {
    assert.ok(groups.has(g), `缺分组 ${g}`);
  }
});

test('逐位确定：同进程内重复跑，digest 与结果完全一致', () => {
  const a = digest();
  const b = digest();
  assert.equal(a.sha256, b.sha256);
  assert.equal(a.assertions, b.assertions);
  assert.ok(a.allPass, `自检表未全绿：${JSON.stringify(runBudgetSelfTest().cases.filter((c) => !c.ok))}`);
});

test('threshold ≤ usable 恒成立（在窗口范围内扫一遍）', () => {
  for (const cw of [100, 1000, 8192, 32768, 131072, 1048576, 2000000]) {
    for (const cap of [undefined, 0, 500, 100000, 1 << 20]) {
      const bud = B.resolveBudget(cap === undefined ? { contextWindow: cw } : { contextWindow: cw, configCap: cap });
      assert.ok(bud.threshold <= bud.usable, `cw=${cw} cap=${cap}: threshold ${bud.threshold} > usable ${bud.usable}`);
      assert.ok(bud.limit <= bud.usable, `cw=${cw} cap=${cap}: limit ${bud.limit} > usable ${bud.usable}`);
      assert.ok(bud.threshold >= 0 && bud.limit >= 0, 'pre 非负');
    }
  }
});

test('decide 的单调性：测量值越大越不可能"未达阈值"', () => {
  const bud = B.resolveBudget({ contextWindow: 1048576 });
  let seenCompress = false;
  for (let t = 0; t <= 1048576; t += 9877) {
    const d = B.decide({ measuredTokens: t, budget: bud });
    if (d.action === B.DECISION.COMPRESS) seenCompress = true;
    else assert.ok(!seenCompress, `在 t=${t} 出现"未达阈值"，但它前面已经有 COMPRESS 了（非单调）`);
  }
  assert.ok(seenCompress, '扫完整个窗口都没触发压缩，说明阈值高到不可达（正是 P26 机制一的形态）');
});

test('canShrink 恰好复刻 P26 死锁数字（2466 / 3435）', () => {
  const r = B.canShrink({ shadowedTokens: 2466, checkpointTokens: 3435 });
  assert.equal(r.ok, false);
  assert.equal(r.verdict, B.SHRINK.IMPOSSIBLE);
  assert.equal(r.savings, -969);
});
