/**
 * ledger-io.test.js — lib/ledger-io.js 的**真文件**往返测试（node:test；零 dsh 依赖）
 * =============================================================================
 *   node --test lib/ledger-io.test.js
 *
 * ★ 为什么不放进 CLI 自检：本插件的 CLI 承诺「全程只读，不改变任何外部状态」，
 *   而这一层必须**真读写文件**才能验证。⇒ 分工：纯序列化与只读三态进 CLI 自检（`--recall-check` 的 Q 组），
 *   真文件往返留在本文件（node:test）。
 * ★ 全部落在 `os.tmpdir()` 下的**本次运行独占子目录**，跑完即删；不触碰任何既有文件。
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  READ_STATUS, LEDGER_IO_DEFAULTS, serializeLedger, deserializeLedger,
  loadLedgerFile, ledgerForUse, saveLedgerFile
} from './ledger-io.js';
import { emptyLedger, recordCheckpoint, recall, RECALL_STATUS } from './ledger.js';

const NASTY = '  前导空格\n第二行\t制表符\n  中文与 emoji 🎯 尾随空格  ';

function withTmp(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'csx-ledger-'));
  try { return fn(dir); } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

function mkLedger() {
  let L = emptyLedger({ maxCheckpoints: 4, maxChars: 100000 });
  L = recordCheckpoint(L, { id: 'cp1', startSeq: 1, endSeq: 2, entries: [{ seq: 1, kind: 'user/message', text: NASTY }, { seq: 2, kind: 'tool/result', text: 'tool-out' }] });
  L = recordCheckpoint(L, { id: 'cp2', startSeq: 3, endSeq: 3, entries: [{ seq: 3, kind: 'user/message', text: 'B3' }] });
  return L;
}

test('★ 真文件往返：save → load 后账本语义与逐字内容均不变', () => {
  withTmp((dir) => {
    const p = path.join(dir, 'nested', 'deeper', 'ledger.json');   // ★ 父目录不存在 ⇒ 应被创建
    const L = mkLedger();
    const w = saveLedgerFile(p, L);
    assert.equal(w.ok, true, `写盘应成功：${w.reason}`);
    assert.ok(w.bytes > 0);
    assert.ok(fs.existsSync(p), '目标文件应存在（且父目录被创建）');

    const r = loadLedgerFile(p);
    assert.equal(r.status, READ_STATUS.OK, `应载入成功：${r.reason}`);
    assert.equal(r.ledger.checkpoints.length, 2);
    assert.equal(r.ledger.evicted, L.evicted);
    assert.equal(r.ledger.maxCheckpoints, 4);
    // ★ 逐字保真
    assert.equal(r.ledger.checkpoints[0].entries[0].text, NASTY);
    // ★ 再序列化必须逐字节相同（确定序）
    assert.equal(serializeLedger(r.ledger), serializeLedger(L));
    // ★ 载入后召回仍然逐字相等（端到端：落盘不破坏立论链）
    const hit = recall(r.ledger, { kind: 'seq', id: '1', seq: 1 });
    assert.equal(hit.status, RECALL_STATUS.HIT);
    assert.equal(hit.text, NASTY);
  });
});

test('★ 原子写：成功路径不留 .tmp 残件', () => {
  withTmp((dir) => {
    const p = path.join(dir, 'ledger.json');
    saveLedgerFile(p, mkLedger());
    assert.ok(!fs.existsSync(`${p}.tmp`), '成功写盘后不应残留 .tmp');
    const entries = fs.readdirSync(dir);
    assert.deepEqual(entries.sort(), ['ledger.json'], `目录内只应有目标文件，实得 ${JSON.stringify(entries)}`);
  });
});

test('★ 读盘三态在真文件上成立：ABSENT / OK / DEGRADED 互不同痕', () => {
  withTmp((dir) => {
    const absent = path.join(dir, 'nope.json');
    assert.equal(loadLedgerFile(absent).status, READ_STATUS.ABSENT);
    assert.equal(ledgerForUse(absent).degraded, false, '首次运行不应被当成故障');
    assert.equal(ledgerForUse(absent).ledger.checkpoints.length, 0);

    const ok = path.join(dir, 'ok.json');
    saveLedgerFile(ok, mkLedger());
    assert.equal(loadLedgerFile(ok).status, READ_STATUS.OK);
    assert.equal(ledgerForUse(ok).degraded, false);

    // —— 以下四种都必须是 DEGRADED（**不是** ABSENT、**不是**空账本）——
    const empty = path.join(dir, 'empty.json');
    fs.writeFileSync(empty, '');
    assert.equal(loadLedgerFile(empty).status, READ_STATUS.DEGRADED, '0 字节文件是异常，不是"空账本"');

    const bad = path.join(dir, 'bad.json');
    fs.writeFileSync(bad, '{not json');
    assert.equal(loadLedgerFile(bad).status, READ_STATUS.DEGRADED);

    const wrongSchema = path.join(dir, 'schema.json');
    fs.writeFileSync(wrongSchema, JSON.stringify({ schema: 'other/v9', checkpoints: [] }));
    assert.equal(loadLedgerFile(wrongSchema).status, READ_STATUS.DEGRADED);

    const isDir = path.join(dir, 'adir');
    fs.mkdirSync(isDir);
    assert.equal(loadLedgerFile(isDir).status, READ_STATUS.DEGRADED, '目录不是账本文件');

    for (const p of [empty, bad, wrongSchema, isDir]) {
      const r = ledgerForUse(p);
      assert.equal(r.degraded, true, `${path.basename(p)} 必须打 degraded 旗（不得静默当作空账本）`);
      assert.ok(r.ledger === null, ' 降级时不得给出一个"看起来能用"的账本');
      assert.ok(r.reason && r.reason.length > 0, ' 降级必须带原因');
    }
  });
});

test('★ 超上限文件被拒且**不读进内存**（大小先判）', () => {
  withTmp((dir) => {
    const p = path.join(dir, 'big.json');
    fs.writeFileSync(p, 'x'.repeat(2048));
    const r = loadLedgerFile(p, { maxBytes: 1024 });
    assert.equal(r.status, READ_STATUS.DEGRADED);
    assert.ok(/超过上限/.test(r.reason), `原因应说明超限：${r.reason}`);
    assert.equal(r.bytes, 2048, '应回报实测大小');
  });
});

test('★ 有界：写入一个已被裁剪过的账本，载回后上限与逐出计数均保持', () => {
  withTmp((dir) => {
    const p = path.join(dir, 'bounded.json');
    let L = emptyLedger({ maxCheckpoints: 2, maxChars: 100000 });
    for (let i = 1; i <= 6; i++) L = recordCheckpoint(L, { id: `c${i}`, startSeq: i, endSeq: i, entries: [{ seq: i, kind: 'user/message', text: `b${i}` }] });
    assert.equal(L.checkpoints.length, 2);
    assert.equal(L.evicted, 4);
    saveLedgerFile(p, L);
    const r = loadLedgerFile(p);
    assert.equal(r.status, READ_STATUS.OK);
    assert.equal(r.ledger.checkpoints.length, 2);
    assert.equal(r.ledger.evicted, 4, '逐出计数必须一并持久化（被裁也是事实）');
    assert.equal(recall(r.ledger, { kind: 'checkpoint', id: 'c1' }).status, RECALL_STATUS.MISS);
  });
});

test('★ 确定序：同一账本无论构造顺序如何，序列化恒得同字节', () => {
  const L = mkLedger();
  const reordered = Object.freeze({
    checkpoints: L.checkpoints, chars: L.chars, maxChars: L.maxChars,
    maxCheckpoints: L.maxCheckpoints, evicted: L.evicted, ok: true, reason: 'x'
  });
  const a = serializeLedger(L);
  assert.equal(serializeLedger(reordered), a);
  assert.equal(a, serializeLedger(L));
  assert.ok(!a.includes('\n'), '应为单行');
});

test('写盘失败不抛出而是如实回报（路径不可写）', () => {
  const w = saveLedgerFile('/proc/definitely/not/writable/ledger.json', mkLedger());
  assert.equal(w.ok, false);
  assert.ok(w.reason.length > 0);
});

test('反序列化不信任文件：逐项校验，任一不过即 DEGRADED 且不给半个账本', () => {
  const schema = LEDGER_IO_DEFAULTS.schema;
  const base = { schema, maxCheckpoints: 1, maxChars: 1, evicted: 0, chars: 0 };
  const cases = [
    ['缺 checkpoints', { ...base }],
    ['checkpoints 非数组', { ...base, checkpoints: {} }],
    ['检查点非对象', { ...base, checkpoints: [1] }],
    ['id 空', { ...base, checkpoints: [{ id: '', startSeq: 1, endSeq: 1, entries: [{ seq: 1, kind: 'k', text: 'x' }] }] }],
    ['seq 非整', { ...base, checkpoints: [{ id: 'a', startSeq: 1.5, endSeq: 1, entries: [{ seq: 1, kind: 'k', text: 'x' }] }] }],
    ['entries 空', { ...base, checkpoints: [{ id: 'a', startSeq: 1, endSeq: 1, entries: [] }] }],
    ['text 非串', { ...base, checkpoints: [{ id: 'a', startSeq: 1, endSeq: 1, entries: [{ seq: 1, kind: 'k', text: 7 }] }] }],
    ['evicted 负', { ...base, evicted: -1, checkpoints: [] }],
  ];
  for (const [label, obj] of cases) {
    const r = deserializeLedger(JSON.stringify(obj));
    assert.equal(r.status, READ_STATUS.DEGRADED, `${label} 应判 DEGRADED`);
    assert.equal(r.ledger, null, `${label} 不得给出半个账本`);
  }
});
