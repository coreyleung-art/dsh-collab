/**
 * checkpoint.test.js — lib/checkpoint.js 的离线单测（node:test；零 dsh 依赖）
 * =============================================================================
 *   node --test lib/checkpoint.test.js
 *
 * 用例本体在 lib/k3-selftest.js（与 `cli.js --checkpoint-check` 共用同一份，避免两处漂）；
 * 本文件把它交给 node:test，并补上几条**跨用例的不变量**（扫描式断言，不是逐例）：
 * 逐例断言证明"我想到的那些点是对的"，扫描断言证明"我没把它写成只在样例上成立"。
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { k3Cases, runK3SelfTest } from './k3-selftest.js';
import {
  RUNG_ORDER, PLAN, CP_DEFAULTS, estimateTokens, assemble, makeCharAccount,
  planCheckpoint, splitRetain
} from './checkpoint.js';
import { compactionGuardFrom, inspectCompactionEntryState } from './events.js';
import { buildCutBalance } from './pairing.js';
import { buildReplacement } from './replace.js';

const FIELDS = { goal: 'G', wave: 'W', todos: 'T', lastHumanRequest: 'H', notes: 'N' };
const mk = (n, tokens, kinds = ['tool/result', 'user/message']) =>
  Array.from({ length: n }, (_, i) => ({
    seq: i + 1, kind: kinds[i % kinds.length], tokens, text: 'x'.repeat(tokens * CP_DEFAULTS.charsPerToken)
  }));

test('K3 用例全绿（每条期望值都是手写的）', () => {
  const cases = k3Cases();
  const bad = cases.filter((c) => !c.ok);
  assert.equal(bad.length, 0,
    bad.map((c) => `  ✗ ${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`).join('\n'));
  assert.ok(cases.length >= 80, `断言条数应 ≥80，实得 ${cases.length}`);
});

test('K3 全量自检全绿且分组计数自洽', () => {
  const r = runK3SelfTest();
  assert.equal(r.failed, 0);
  assert.equal(Object.values(r.bySuite).reduce((a, b) => a + b, 0), r.total);
  assert.ok(r.bySuite.L >= 4, `增量账等价性用例应 ≥4，实得 ${r.bySuite.L}`);
});

test('★ 扫描：增量账 ≡ 真构建（全档位 × 全 k，非样例）', () => {
  // 用多种形状（连续同类 / 交替 / 长短混杂）扫，确保分组延长与新建两条路径都被走到。
  for (const kinds of [['tool/result', 'user/message'], ['tool/result'], ['user/message', 'assistant/message', 'tool/result'],
    ['tool/call', 'tool/result', 'tool/result', 'user/message']]) {
    for (const n of [1, 2, 7, 23]) {
      const entries = mk(n, 47, kinds);
      for (const rung of RUNG_ORDER) {
        const acct = makeCharAccount(entries, rung, FIELDS, CP_DEFAULTS, n);
        for (let k = 1; k <= n; k++) {
          assert.equal(acct.push(k), assemble(entries, rung, FIELDS, CP_DEFAULTS, k).text.length,
            `kinds=${kinds.join(',')} n=${n} rung=${rung} k=${k}`);
        }
      }
    }
  }
});

test('★ 扫描：任意规模/任意要求下，报数自洽且不违反 canShrink 契约', () => {
  for (const n of [0, 1, 3, 40]) {
    for (const per of [4, 60, 400]) {
      for (const need of [0, 500, 100000]) {
        const entries = mk(n, per);
        const p = planCheckpoint({ entries, retainTokens: 100, minSavingsTokens: 32, neededSavingsTokens: need, ...FIELDS });
        // 报数自洽：无论 OK / IMPOSSIBLE，检点 token 必须等于正文实测 token
        if (p.handoffText !== null) {
          assert.equal(p.checkpointTokens, estimateTokens(p.handoffText), `n=${n} per=${per} need=${need}`);
        }
        if (p.ok) {
          assert.equal(p.verdict, PLAN.OK);
          assert.ok(p.checkpointTokens < p.shadowedTokens, ' 检点必须严格小于被遮内容');
          assert.ok(p.savings >= p.requiredSavings, `节省 ${p.savings} 应 ≥ 要求 ${p.requiredSavings}`);
          assert.equal(p.savings, p.shadowedTokens - p.checkpointTokens);
        } else {
          assert.ok(p.verdict === PLAN.IMPOSSIBLE || p.verdict === PLAN.NOTHING_TO_SHADOW);
        }
      }
    }
  }
});

test('★ 不变量：保活窗口内的条目永不出现在被遮区（任意规模扫描）', () => {
  for (const n of [5, 20, 60]) {
    for (const retain of [0, 1, 100, 999, 100000]) {
      const entries = mk(n, 50);
      const { retained } = splitRetain(entries, retain);
      const p = planCheckpoint({ entries, retainTokens: retain, minSavingsTokens: 32, ...FIELDS });
      if (p.range === null) continue;
      const retainedSeqs = new Set(retained.map((e) => e.seq));
      for (let s = p.range.startSeq; s <= p.range.endSeq; s++) {
        assert.ok(!retainedSeqs.has(s), `n=${n} retain=${retain}: seq ${s} 属保活区却被送进被遮区`);
      }
      assert.ok(p.range.endSeq < (retained[0] ? retained[0].seq : Number.MAX_SAFE_INTEGER),
        `被遮区末端必须早于保活区首条`);
    }
  }
});

test('纯函数：planCheckpoint 不修改输入 entries（逐位比对调用前后）', () => {
  const entries = mk(30, 90);
  const before = JSON.stringify(entries);
  planCheckpoint({ entries, retainTokens: 100, minSavingsTokens: 32, neededSavingsTokens: 5000, ...FIELDS });
  assert.equal(JSON.stringify(entries), before);
});

test('确定性：同输入重复调用逐字节相同（无时钟、无随机、无迭代序依赖）', () => {
  const entries = mk(50, 120);
  const a = planCheckpoint({ entries, retainTokens: 200, minSavingsTokens: 32, ...FIELDS });
  const b = planCheckpoint({ entries, retainTokens: 200, minSavingsTokens: 32, ...FIELDS });
  assert.equal(a.handoffText, b.handoffText);
  assert.equal(JSON.stringify(a.range), JSON.stringify(b.range));
  assert.equal(a.rung, b.rung);
  assert.equal(a.checkpointTokens, b.checkpointTokens);
});

test('★ 扫描：并发护栏对任意事件流都与官方原式逐字一致', () => {
  // 用穷举组合扫：4 类事件 × 长度 0..5 —— 覆盖 start/end/endSeed 全部交错形态。
  const TYPES = ['compaction/start', 'compaction/end', 'session/end-seed', 'user/message'];
  const all = [];
  for (let n = 0; n <= 5; n++) {
    const total = TYPES.length ** n;
    for (let k = 0; k < total; k++) {
      let x = k; const evs = [];
      for (let i = 0; i < n; i++) { evs.push({ type: TYPES[x % TYPES.length], seq: i + 1 }); x = Math.floor(x / TYPES.length); }
      all.push(evs);
    }
  }
  let checked = 0;
  for (const evs of all) {
    const st = inspectCompactionEntryState(evs);
    const u = st.unmatchedCompactionStart; const s = st.latestEndSeedSeq;
    const official = !(u === undefined || (s !== undefined && s > u.seq));   // 官方 :505 原式
    assert.equal(compactionGuardFrom(evs).busy, official, `事件流 ${JSON.stringify(evs)}`);
    checked += 1;
  }
  assert.ok(checked >= 1000, `扫描组合数应 ≥1000，实得 ${checked}`);
});

test('★ 扫描：buildReplacement 选出的终点永远是**配对安全切口**（穷举小表面）', () => {
  const F = { goal: 'G', wave: 'W', todos: 'T', lastHumanRequest: 'H', notes: 'N' };
  const mk = (seq, k) => k === 'r' ? { seq, type: 'tool/result' }
    : k === 'o' ? { seq, type: 'user/message' }
      : { seq, type: 'assistant/message', data: { message: { content: Array.from({ length: Number(k) }, () => ({ type: 'tool-call' })) } } };
  const KINDS = ['1', '0', 'r', 'o'];
  let withOk = 0; let refused = 0;
  for (let n = 1; n <= 4; n++) {
    for (let k = 0; k < KINDS.length ** n; k++) {
      let x = k; const list = [];
      for (let i = 0; i < n; i++) { list.push(mk(i + 1, KINDS[x % KINDS.length])); x = Math.floor(x / KINDS.length); }
      const ev = []; for (const e of list) ev[e.seq] = e;
      const nodes = list.map((e) => ({ seq: e.seq, tokens: 500 }));
      let cb = null;
      try { cb = buildCutBalance(nodes.map((nd) => nd.seq), ev).cutBalanced; } catch { continue; }  // 损坏表面跳过
      const r = buildReplacement({ nodes, events: ev, handoffFields: F, retainTokens: 0, minSavingsTokens: 32 });
      if (!r.ok) { refused += 1; continue; }
      withOk += 1;
      // ① 终点必须是合法切口
      assert.equal(cb[r.shadowedSeqs.length], true,
        `终点非法: ${JSON.stringify(list.map((e) => e.type))} -> n=${r.shadowedSeqs.length}`);
      // ② 区间必须连续无缺口
      const want = Array.from({ length: r.shadowedSeqs.length }, (_, i) => r.shadowedSeqs[0] + i);
      assert.deepEqual([...r.shadowedSeqs], want, '被遮 seq 必须连续');
      // ③ surfaceOp 与 shadowedSeqs 必须同源
      assert.equal(r.surfaceOp.start, r.shadowedSeqs[0]);
      assert.equal(r.surfaceOp.end, r.shadowedSeqs[r.shadowedSeqs.length - 1]);
    }
  }
  assert.ok(withOk >= 20, `成功装配的样本应 ≥20，实得 ${withOk}`);
  assert.ok(refused >= 1, '应至少有被拒绝的样本（否则拒绝路径未被覆盖）');
});

test('★ 扫描：配对平衡 fold 与朴素参照实现逐项一致（穷举小序列）', () => {
  const mkEv = (seq, k) => k === 'r' ? { seq, type: 'tool/result' }
    : k === 'o' ? { seq, type: 'user/message' }
      : { seq, type: 'assistant/message', data: { message: { content: Array.from({ length: Number(k) }, () => ({ type: 'tool-call' })) } } };
  const KINDS = ['0', '1', '0', '2', 'r', 'o'];
  let checked = 0; let invalidSeen = 0;
  for (let n = 0; n <= 4; n++) {
    for (let k = 0; k < KINDS.length ** n; k++) {
      let x = k; const list = [];
      for (let i = 0; i < n; i++) { list.push(mkEv(i + 1, KINDS[x % KINDS.length])); x = Math.floor(x / KINDS.length); }
      const ev = []; for (const e of list) ev[e.seq] = e;
      // 朴素参照：直接数在途 tool-call，负值即"孤立结果"
      let inprog = 0; const naive = [true]; let bad = false;
      for (const e of list) {
        inprog += e.type === 'tool/result' ? -1 : (e.type === 'assistant/message' ? e.data.message.content.length : 0);
        if (inprog < 0) { bad = true; break; }
        naive.push(inprog === 0);
      }
      let got = null; let threw = false;
      try { got = buildCutBalance(list.map((e) => e.seq), ev).cutBalanced; } catch { threw = true; }
      if (bad) { assert.equal(threw, true, `应判损坏: ${JSON.stringify(list.map((e) => e.type))}`); invalidSeen += 1; }
      else { assert.equal(threw, false, '不应抛出'); assert.deepEqual(got, naive); checked += 1; }
    }
  }
  assert.ok(checked >= 200, `有效序列应 ≥200，实得 ${checked}`);
  assert.ok(invalidSeen >= 1, '应至少覆盖一条孤立结果（否则负控面为空）');
});

test('★ 并发护栏绝不抛出（任意坏输入）', () => {
  for (const bad of [null, undefined, 42, 'x', {}, [null], [42], [{}, undefined], [[]]]) {
    let threw = false;
    try { compactionGuardFrom(bad); } catch { threw = true; }
    assert.equal(threw, false, `输入 ${JSON.stringify(bad)} 不应抛出`);
    assert.equal(compactionGuardFrom(bad).busy, false, ' 读不到时应保守判"不忙"并如实标 ok:false');
  }
});

test('★ 立论所系：官方摘要帧大于被遮内容时（官方死锁态），本核仍能给出缩小方案', () => {
  // 官方实测 docs/compaction-lowerbound-crash-20261009.md：摘要帧 3435 token ≥ 被遮内容 2466 token。
  const entries = mk(41, 60);
  const shadowed = entries.reduce((a, e) => a + e.tokens, 0);
  const p = planCheckpoint({ entries, retainTokens: 0, minSavingsTokens: 32, neededSavingsTokens: 0, ...FIELDS });
  assert.ok(3435 > shadowed, '构造的被遮内容须小于官方摘要帧（否则死锁条件不成立）');
  assert.equal(p.ok, true, '本核必须能缩小——官方在此判"压不动"');
  assert.ok(p.checkpointTokens < 3435, `检点 ${p.checkpointTokens} 必须远小于官方摘要帧 3435`);
  assert.ok(p.savings >= p.requiredSavings);
});
