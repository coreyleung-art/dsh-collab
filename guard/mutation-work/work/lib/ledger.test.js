/**
 * ledger.test.js — lib/ledger.js 的离线单测（node:test；零 dsh 依赖）
 * =============================================================================
 *   node --test lib/ledger.test.js
 *
 * 用例本体在 lib/k4-selftest.js（与 `cli.js --recall-check` 共用同一份，避免两处漂）；
 * 本文件把它交给 node:test，并补上**跨用例的扫描式不变量**。
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { k4Cases, runK4SelfTest } from './k4-selftest.js';
import { RECALL_STATUS, emptyLedger, recordCheckpoint, recall } from './ledger.js';

test('K4 用例全绿（每条期望值都是手写的）', () => {
  const cases = k4Cases();
  const bad = cases.filter((c) => !c.ok);
  assert.equal(bad.length, 0,
    bad.map((c) => `  ✗ ${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`).join('\n'));
  assert.ok(cases.length >= 50, `断言条数应 ≥50，实得 ${cases.length}`);
});

test('K4 全量自检全绿且分组计数自洽', () => {
  const r = runK4SelfTest();
  assert.equal(r.failed, 0);
  assert.equal(Object.values(r.bySuite).reduce((a, b) => a + b, 0), r.total);
});

test('★ 扫描：任意正文经记账→召回必须**逐字节相等**（含不可见字符）', () => {
  const SAMPLES = [
    '', ' ', '\n', '\t', '  a  ', 'a\nb\nc', '中文', '🎯', '中文 🎯\t混合  ',
    '\r\n', 'a'.repeat(1000), '\u0000', '\u200b', ' 　全角空格 ',
  ];
  let n = 0;
  for (const s of SAMPLES) {
    let L = emptyLedger();
    L = recordCheckpoint(L, { id: 's', startSeq: 1, endSeq: 1, entries: [{ seq: 1, kind: 'user/message', text: s }] });
    const r = recall(L, { kind: 'seq', id: '1', seq: 1 });
    assert.equal(r.status, RECALL_STATUS.HIT, `样本 ${JSON.stringify(s)} 应命中`);
    assert.equal(r.text, s, `样本 ${JSON.stringify(s)} 召回后必须逐字节相等`);
    assert.equal(r.text.length, s.length);
    n += 1;
  }
  assert.ok(n >= 10, '样本面应 ≥10');
});

test('★ 扫描：DEGRADED 与 MISS 在任何坏输入下都不同痕', () => {
  const degradedInputs = [null, undefined, 42, 'x', {}, { checkpoints: 'nope' }, emptyLedger()];
  for (const bad of degradedInputs) {
    const r = recall(bad, { kind: 'seq', id: '1', seq: 1 });
    assert.equal(r.status, RECALL_STATUS.DEGRADED, `输入 ${JSON.stringify(bad)} 应判 DEGRADED`);
    assert.notEqual(r.status, RECALL_STATUS.MISS, 'DEGRADED 绝不可与 MISS 同痕');
    assert.ok(/不代表该内容不存在/.test(r.reason), 'DEGRADED 必须明说"不代表不存在"');
  }
  // 对照：账本在位而内容不在 ⇒ MISS，且**不得**说自己"不代表不存在"
  let L = emptyLedger();
  L = recordCheckpoint(L, { id: 'a', startSeq: 1, endSeq: 1, entries: [{ seq: 1, kind: 'user/message', text: 'x' }] });
  const miss = recall(L, { kind: 'seq', id: '77', seq: 77 });
  assert.equal(miss.status, RECALL_STATUS.MISS);
  assert.ok(!/不代表该内容不存在/.test(miss.reason), 'MISS 不应带 DEGRADED 的免责措辞');
});

test('★ 有界：任意次记账后账本都不越界，且逐出总量守恒', () => {
  let L = emptyLedger({ maxCheckpoints: 4, maxChars: 500 });
  for (let i = 1; i <= 50; i++) {
    L = recordCheckpoint(L, { id: `c${i}`, startSeq: i, endSeq: i, entries: [{ seq: i, kind: 'user/message', text: 'y'.repeat(10) }] });
    assert.ok(L.checkpoints.length <= 4, `第 ${i} 次后超过 maxCheckpoints`);
    assert.ok(L.chars <= 500 || L.checkpoints.length === 1, `第 ${i} 次后超过 maxChars`);
  }
  assert.equal(50 - L.checkpoints.length, L.evicted, '逐出计数必须守恒（入账数 − 现存数）');
});
