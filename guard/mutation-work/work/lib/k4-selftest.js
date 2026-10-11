/**
 * k4-selftest.js — K4 自检（检查点账本 + 召回逐字相等）的**唯一来源**
 * =============================================================================
 * 两个消费者，同一份用例（避免两处漂）：
 *   · `cli.js --recall-check` —— 进程内跑（本插件 ALLOWED_COMMANDS = []，连测试进程都不能起）；
 *   · `lib/ledger.test.js`    —— 交给 node:test 驱动，逐条变成断言。
 *
 * ★ 全部用例只 import 纯核（ledger.js），**零 dsh import、零 I/O、零时钟**。
 *
 * ★ 本套用例的重心是**立项书 §5 正控 3**：「被省略段用 `csx_recall` 取回，与原文**逐字相等**」——
 *   故有一条用例把正文做成含**换行 / 中文 / emoji / 制表符 / 前后空格**的刁钻样本，
 *   任何一处"顺手 trim/归一化"都会被打红。
 * ★ 另一重心是**三态不许同痕**：`DEGRADED`（账本不可用）与 `MISS`（真未命中）**必须可区分** ——
 *   把「没有账本」报成「该段不存在」，会让使用者以为内容从未被压，而实际它被压掉且取不回来。
 */
import { createHash } from 'node:crypto';
import { canonicalJson } from './budget-selftest.js';
import { eq, okTrue, errHelper } from './assert-helpers.js';
import {
  RECALL_STATUS, LEDGER_DEFAULTS, LedgerError,
  emptyLedger, recordCheckpoint, ledgerUsable, recall, describeRecall
} from './ledger.js';
import {
  READ_STATUS, LEDGER_IO_DEFAULTS, LedgerIoError,
  serializeLedger, deserializeLedger, loadLedgerFile, ledgerForUse, describeLoad
} from './ledger-io.js';
import {
  OFFICIAL_FLOOR, CALIB_DEFAULTS, measureOurFloor, calibrationReport, renderCalibration, budgetSanity
} from './calibration.js';
import { planCheckpoint, splitRetain } from './checkpoint.js';
import { EV } from './events.js';
import {
  NoticeError, NOTICE_KIND, NOTICE_LEVEL, CANNOT_SHRINK_REASON,
  buildCannotShrinkNotice, describeNotice, isSilent, distinguishable
} from './notice.js';

// 断言助手统一来自 lib/assert-helpers.js（第 3 次重复后提取，见该文件头）
// 本文件自用的造数助手（k3-selftest 里也有同名者；两文件各自独立，不跨文件 import 以免耦合）
const FIELDS = Object.freeze({ goal: 'G', wave: 'W', todos: 'T', lastHumanRequest: 'H', notes: 'N' });
const mixed = (n, perTokens, startSeq = 1) => Array.from({ length: n }, (_, i) => ({
  seq: startSeq + i, kind: i % 2 === 0 ? 'tool/result' : 'user/message',
  tokens: perTokens, text: 'x'.repeat(perTokens * 4)
}));

const lerr = errHelper(LedgerError);
const ioerr = errHelper(LedgerIoError);

/** 刁钻正文：任何归一化都会破坏"逐字相等"。 */
const NASTY = '  首行有前导空格\n第二行\t有制表符\n  第三行中文与 emoji 🎯 结尾两个空格  ';
const E = (seq, kind, text) => ({ seq, kind, text });

export function k4Cases() {
  const out = [];
  const L0 = emptyLedger();

  /* ---- Z1. ★★ 外部事实常量的绝对钉扎（常量变异面扩大后筛出的高风险子集）----
     系统化变异（tools/csx-constant-mutation.py）扫出 **29 个未杀常量**（远超手挑的 M1/M2），
     但**风险不等**。分界：
       **外部事实** —— 必须与外部来源逐字一致（官方运行时 / 立项书原文 / 持久化格式）
                      ⇒ 改了就**静默失效且无症状**（不会红、不会报错、只是不再工作）
       **内部枚举** —— 只要用到的地方都用同一常量，改了是自洽的
     ★ 故**只钉外部事实**：全钉 29 个会变成**噪声**，而噪声会被忽略（本线已有教训）。
     三处最会咬人的：
       · EV.* 若不等于官方事件类型串 ⇒ **并发护栏永不触发**（守卫永远以为"没有压缩在途"）
       · NOTICE_KIND 若不等于立项书 §2.4 原文 ⇒ 通知落不进事件流语义
       · ledger schema 若变 ⇒ **旧账本全部读不回**（判 DEGRADED ⇒ 逐字召回全废） */
  out.push(
    eq('Z1/★ 官方事件类型 compaction/start（并发护栏命门）', EV.COMPACTION_START, 'compaction/start'),
    eq('Z1/★ 官方事件类型 compaction/end', EV.COMPACTION_END, 'compaction/end'),
    eq('Z1/★ 官方事件类型 session/end-seed（陈旧豁免的判据源）', EV.END_SEED, 'session/end-seed'),
    eq('Z1/★ 通知类型 compaction/notice（立项书 §2.4 I1 逐字）', NOTICE_KIND, 'compaction/notice'),
    eq('Z1/★ 通知级别 WARN', NOTICE_LEVEL.WARN, 'WARN'),
    eq('Z1/★ 账本 schema 逐字（改了则旧账本判 DEGRADED ⇒ 逐字召回全废）', LEDGER_IO_DEFAULTS.schema, 'context-survival-ledger/v1'),
    eq('Z1/★ 召回态 HIT 对外契约', RECALL_STATUS.HIT, 'hit'),
    eq('Z1/★ 召回态 MISS 对外契约', RECALL_STATUS.MISS, 'miss'),
    eq('Z1/★ 召回态 DEGRADED 对外契约（与 MISS 必须可区分）', RECALL_STATUS.DEGRADED, 'degraded'),
    eq('Z1/★ 落盘态 ABSENT 对外契约', READ_STATUS.ABSENT, 'absent'),
    eq('Z1/★ 落盘态 OK 对外契约', READ_STATUS.OK, 'ok'),
    eq('Z1/★ 落盘态 DEGRADED 对外契约', READ_STATUS.DEGRADED, 'degraded')
  );

  /* ---- A. 账本基本形与不可变性 ---- */
  const rec = { id: 'cp1', startSeq: 1, endSeq: 3, entries: [E(1, 'user/message', NASTY), E(2, 'tool/result', 'tool out'), E(3, 'user/message', 'tail')] };
  const L1 = recordCheckpoint(L0, rec);
  out.push(
    eq('A/空账本 ok', L0.ok, true),
    eq('A/空账本 checkpoints 长度', L0.checkpoints.length, 0),
    eq('A/空账本 reason 明说为空', /空账本/.test(L0.reason), true),
    eq('A/记账后数量', L1.checkpoints.length, 1),
    eq('A/★ 不改入参（纯函数）', L0.checkpoints.length, 0),
    okTrue('A/账本被冻结', Object.isFrozen(L1)),
    okTrue('A/检查点被冻结', Object.isFrozen(L1.checkpoints[0])),
    okTrue('A/条目被冻结', Object.isFrozen(L1.checkpoints[0].entries[0])),
    eq('A/chars 已统计', L1.chars >= NASTY.length, true),
    eq('A/evicted 初值 0', L1.evicted, 0),
    eq('A/账本可用性自检', ledgerUsable(L1), true),
    eq('A/坏账本不可用', ledgerUsable({}), false)
  );

  /* ---- B. ★ 正控 3：召回与原文**逐字相等** ---- */
  const rSeq = recall(L1, { kind: 'seq', id: '1', seq: 1 });
  const rRange = recall(L1, { kind: 'range', id: '1-3', start: 1, end: 3 });
  const rCp = recall(L1, { kind: 'checkpoint', id: 'cp1' });
  out.push(
    eq('B/seq 命中', rSeq.status, RECALL_STATUS.HIT),
    eq('B/★ seq 召回与原文逐字节相等（含换行/制表/emoji/前后空格）', rSeq.text === NASTY, true),
    eq('B/★ 逐字节复核：长度相等', rSeq.text.length, NASTY.length),
    okTrue('B/★ 未被 trim（前导空格保留）', rSeq.text.startsWith('  ')),
    okTrue('B/★ 未被 trim（尾随空格保留）', rSeq.text.endsWith('  ')),
    okTrue('B/★ 制表符未被展开', rSeq.text.includes('\t')),
    okTrue('B/★ 换行结构未被改写', rSeq.text.split('\n').length === 3),
    okTrue('B/★ emoji 未被破坏', rSeq.text.includes('🎯')),
    eq('B/range 命中 3 条', rRange.entries.length, 3),
    eq('B/★ range 召回首条逐字相等', rRange.entries[0].text === NASTY, true),
    eq('B/range 以换行连接', rRange.text, [NASTY, 'tool out', 'tail'].join('\n')),
    eq('B/checkpoint 召回 3 条', rCp.entries.length, 3),
    eq('B/checkpoint 与 range 同内容', rCp.text === rRange.text, true),
    eq('B/describeRecall 可读', /^recall=hit n=1 chars=\d+$/.test(describeRecall(rSeq)), true),
    eq('B/kind 与 seq 一并返回', rSeq.entries[0].kind, 'user/message')
  );

  /* ---- C. ★ 三态不许同痕：DEGRADED ≠ MISS ---- */
  const missSeq = recall(L1, { kind: 'seq', id: '999', seq: 999 });
  const degNull = recall(null, { kind: 'seq', id: '1', seq: 1 });
  const degBad = recall({ checkpoints: 'nope' }, { kind: 'seq', id: '1', seq: 1 });
  const degEmpty = recall(emptyLedger(), { kind: 'seq', id: '1', seq: 1 });
  const degNoTarget = recall(L1, null);
  out.push(
    eq('C/真未命中 ⇒ MISS', missSeq.status, RECALL_STATUS.MISS),
    eq('C/账本为 null ⇒ DEGRADED', degNull.status, RECALL_STATUS.DEGRADED),
    eq('C/账本结构损坏 ⇒ DEGRADED', degBad.status, RECALL_STATUS.DEGRADED),
    eq('C/空账本 ⇒ DEGRADED', degEmpty.status, RECALL_STATUS.DEGRADED),
    eq('C/目标未解析 ⇒ DEGRADED', degNoTarget.status, RECALL_STATUS.DEGRADED),
    okTrue('C/★ MISS ≠ DEGRADED（两种成因必须可区分）', missSeq.status !== degEmpty.status),
    okTrue('C/★ DEGRADED 明说不代表不存在', /不代表该内容不存在/.test(degEmpty.reason)),
    okTrue('C/★ DEGRADED(null) 也明说不代表不存在', /不代表该内容不存在/.test(degNull.reason)),
    okTrue('C/★ MISS 说明账本在位且给出账本规模', /账本在位/.test(missSeq.reason)),
    eq('C/三种失败都不带正文', [missSeq, degNull, degEmpty].every((r) => r.text === ''), true)
  );

  /* ---- D. 有界：双上限与逐出记账 ---- */
  let Lb = emptyLedger({ maxCheckpoints: 3, maxChars: 10_000 });
  for (let i = 1; i <= 5; i++) Lb = recordCheckpoint(Lb, { id: `c${i}`, startSeq: i, endSeq: i, entries: [E(i, 'user/message', `body-${i}`)] });
  const Lc = (() => { let x = emptyLedger({ maxCheckpoints: 99, maxChars: 40 }); for (let i = 1; i <= 6; i++) x = recordCheckpoint(x, { id: `d${i}`, startSeq: i, endSeq: i, entries: [E(i, 'user/message', 'x'.repeat(20))] }); return x; })();
  out.push(
    eq('D/★ maxCheckpoints 生效（只留 3）', Lb.checkpoints.length, 3),
    eq('D/★ 逐出的是最旧的（留下 c3,c4,c5）', Lb.checkpoints.map((c) => c.id).join(), 'c3,c4,c5'),
    eq('D/★ 逐出被记账（evicted=2）', Lb.evicted, 2),
    eq('D/★ 被逐出的取不回 ⇒ MISS（而非 DEGRADED）', recall(Lb, { kind: 'checkpoint', id: 'c1' }).status, RECALL_STATUS.MISS),
    okTrue('D/★ MISS 时提示"可能因超界被裁"', /逐出/.test(recall(Lb, { kind: 'checkpoint', id: 'c1' }).reason)),
    eq('D/留下的仍可取回', recall(Lb, { kind: 'checkpoint', id: 'c5' }).status, RECALL_STATUS.HIT),
    eq('D/★ maxChars 生效', Lc.chars <= 40, true),
    eq('D/★ maxChars 逐出也记账', Lc.evicted >= 1, true),
    eq('D/默认上限值冻结', LEDGER_DEFAULTS.maxCheckpoints, 8)
  );

  /* ---- E. 记账校验（不静默接受坏数据） ---- */
  out.push(
    lerr('E/拒坏账本', () => recordCheckpoint({}, rec), 'BAD_LEDGER'),
    lerr('E/拒非对象记录', () => recordCheckpoint(L0, null), 'BAD_RECORD'),
    lerr('E/拒空 id', () => recordCheckpoint(L0, { ...rec, id: '' }), 'BAD_RECORD_ID'),
    lerr('E/拒非整 seq', () => recordCheckpoint(L0, { ...rec, startSeq: 1.5 }), 'BAD_RECORD_SEQ'),
    lerr('E/拒空 entries', () => recordCheckpoint(L0, { ...rec, entries: [] }), 'BAD_RECORD_ENTRIES'),
    lerr('E/拒非串 text（原文必须逐字可存）', () => recordCheckpoint(L0, { ...rec, entries: [E(1, 'k', 123)] }), 'BAD_ENTRY_TEXT'),
    lerr('E/拒同检查点内重复 seq', () => recordCheckpoint(L0, { ...rec, entries: [E(1, 'k', 'a'), E(1, 'k', 'b')] }), 'DUP_SEQ'),
    lerr('E/拒非法上限', () => emptyLedger({ maxCheckpoints: 0 }), 'BAD_CAP')
  );

  /* ---- F. 多检查点下的选取语义 ---- */
  const Lf = (() => {
    let x = emptyLedger();
    x = recordCheckpoint(x, { id: 'a', startSeq: 1, endSeq: 2, entries: [E(1, 'user/message', 'A1'), E(2, 'tool/result', 'A2')] });
    x = recordCheckpoint(x, { id: 'b', startSeq: 3, endSeq: 4, entries: [E(3, 'user/message', 'B3'), E(4, 'tool/result', 'B4')] });
    return x;
  })();
  out.push(
    eq('F/跨检查点 seq 命中第二个', recall(Lf, { kind: 'seq', id: '3', seq: 3 }).text, 'B3'),
    eq('F/range 落在单检查点内', recall(Lf, { kind: 'range', id: '1-2', start: 1, end: 2 }).text, 'A1\nA2'),
    eq('F/★ range 跨检查点只取最先命中的那个（不拼接，避免顺序造假）', recall(Lf, { kind: 'range', id: '2-3', start: 2, end: 3 }).text, 'A2'),
    eq('F/checkpoint 精确匹配 id', recall(Lf, { kind: 'checkpoint', id: 'b' }).text, 'B3\nB4'),
    eq('F/未知 checkpoint id ⇒ MISS', recall(Lf, { kind: 'checkpoint', id: 'zz' }).status, RECALL_STATUS.MISS),
    eq('F/未知 kind ⇒ DEGRADED', recall(Lf, { kind: 'nope', id: '1' }).status, RECALL_STATUS.DEGRADED)
  );

  /* ---- Q. ★ 落盘层：确定序序列化 + 反序列化三态（纯与只读，不产生任何写入） ---- */
  const SER = serializeLedger(L1);
  const rt = deserializeLedger(SER);
  // 键序与构造顺序无关：把同一账本的字段换个顺序重建，序列化必须逐字节相同
  const reordered = Object.freeze({
    checkpoints: L1.checkpoints, chars: L1.chars, maxChars: L1.maxChars,
    maxCheckpoints: L1.maxCheckpoints, evicted: L1.evicted, ok: true, reason: 'x'
  });
  out.push(
    eq('Q/序列化结果非空', SER.length > 0, true),
    eq('Q/序列化为单行（无换行）', SER.includes('\n'), false),
    eq('Q/★ 往返得到 OK', rt.status, READ_STATUS.OK),
    eq('Q/★ 往返后检查点数一致', rt.ledger.checkpoints.length, L1.checkpoints.length),
    eq('Q/★ 往返后逐字相等（刁钻正文）', rt.ledger.checkpoints[0].entries[0].text === NASTY, true),
    eq('Q/★ 往返后再序列化逐字节相同（确定序）', serializeLedger(rt.ledger), SER),
    eq('Q/★ 键序与构造顺序无关（同账本恒同字节）', serializeLedger(reordered), SER),
    eq('Q/往返后上限被保留', rt.ledger.maxCheckpoints, L1.maxCheckpoints),
    eq('Q/往返后 evicted 被保留', rt.ledger.evicted, L1.evicted),
    // 反序列化的失败面：一律 DEGRADED，绝不抛出、绝不"尽力解析出半个账本"
    eq('Q/★ 空文件 ⇒ DEGRADED（不是 ABSENT、不是空账本）', deserializeLedger('').status, READ_STATUS.DEGRADED),
    eq('Q/空文件 reason 明说"不当作空账本"', /不当作"空账本"/.test(deserializeLedger('').reason), true),
    eq('Q/坏 JSON ⇒ DEGRADED', deserializeLedger('{oops').status, READ_STATUS.DEGRADED),
    eq('Q/顶层非对象 ⇒ DEGRADED', deserializeLedger('[1,2]').status, READ_STATUS.DEGRADED),
    eq('Q/schema 不认 ⇒ DEGRADED', deserializeLedger(JSON.stringify({ schema: 'other/v9', checkpoints: [] })).status, READ_STATUS.DEGRADED),
    eq('Q/checkpoints 非数组 ⇒ DEGRADED', deserializeLedger(JSON.stringify({ schema: LEDGER_IO_DEFAULTS.schema, checkpoints: 'x', maxCheckpoints: 1, maxChars: 1, evicted: 0, chars: 0 })).status, READ_STATUS.DEGRADED),
    eq('Q/条目 text 非串 ⇒ DEGRADED', deserializeLedger(JSON.stringify({ schema: LEDGER_IO_DEFAULTS.schema, maxCheckpoints: 1, maxChars: 1, evicted: 0, chars: 0, checkpoints: [{ id: 'a', startSeq: 1, endSeq: 1, entries: [{ seq: 1, kind: 'k', text: 42 }] }] })).status, READ_STATUS.DEGRADED),
    eq('Q/非字符串输入 ⇒ DEGRADED', deserializeLedger(null).status, READ_STATUS.DEGRADED),
    ioerr('Q/序列化坏账本 ⇒ 抛 BAD_LEDGER（LedgerIoError）', () => serializeLedger({}), 'BAD_LEDGER'),
    // 只读：不存在的路径 ⇒ ABSENT（**不是** DEGRADED）
    eq('Q/★ 文件不存在 ⇒ ABSENT（首次运行，正常）', loadLedgerFile('/nonexistent/never/here.json').status, READ_STATUS.ABSENT),
    eq('Q/★ ABSENT 与 DEGRADED 必须不同痕', loadLedgerFile('/nonexistent/never/here.json').status !== deserializeLedger('').status, true),
    eq('Q/ledgerForUse: ABSENT ⇒ 空账本且不打 degraded 旗', ledgerForUse('/nonexistent/never/here.json').degraded, false),
    eq('Q/ledgerForUse: ABSENT ⇒ 账本可用', ledgerForUse('/nonexistent/never/here.json').ledger.checkpoints.length, 0),
    eq('Q/路径为空 ⇒ DEGRADED', loadLedgerFile('').status, READ_STATUS.DEGRADED),
    eq('Q/describeLoad 可读', /^ledger=absent/.test(describeLoad(loadLedgerFile('/nonexistent/never/here.json'))), true)
  );

  /* ---- R. ★★ K5 负控 1 标定：缩小地板对照（立论所系） ---- */
  const floor32 = measureOurFloor({ entryTokens: 32, maxEntries: 600 });
  const floor100 = measureOurFloor({ entryTokens: 100, maxEntries: 600 });
  const calib = calibrationReport({ granularities: [32, 100, 500, 2000], maxEntries: 600 });
  // ★ 负控：把要求节省量抬到不可能，标定**必须**报"立项失败" —— 证明该结论不是恒真
  const impossible = calibrationReport({ granularities: [100], maxEntries: 200, neededSavingsTokens: 10_000_000 });
  out.push(
    // 官方地板是**引用常量**，其出处与判据必须随卡一起在
    eq('R/官方地板值（实测常量）', OFFICIAL_FLOOR.framedSummaryTokens, 3435),
    // ★ 补（常量变异面扩大后扫出）：另一读法此前**无断言看守**
    eq('R/★ 官方地板另一读法（实测常量 · 补钉）', OFFICIAL_FLOOR.framedSummaryTokensAlt, 3450),
    eq('R/★ 崩溃点被遮内容的实测值（补钉）', OFFICIAL_FLOOR.shadowedTokensAtCrash, 2466),
    eq('R/崩溃点被遮内容（实测常量）', OFFICIAL_FLOOR.shadowedTokensAtCrash, 2466),
    okTrue('R/★ 官方地板标了出处（引用而非自算）', /compaction-lowerbound-crash/.test(OFFICIAL_FLOOR.source)),
    okTrue('R/★ 官方判据标了源码位置', /:556/.test(OFFICIAL_FLOOR.judge)),
    okTrue('R/常量被冻结', Object.isFrozen(OFFICIAL_FLOOR)),
    // 本核地板：实算
    eq('R/细粒度地板存在', floor32.ok, true),
    okTrue('R/细粒度地板远小于官方地板', floor32.floorTokens < OFFICIAL_FLOOR.framedSummaryTokens, `${floor32.floorTokens}`),
    eq('R/粒度 32 的地板 = 192', floor32.floorTokens, 192),
    eq('R/粒度 100 的地板 = 200', floor100.floorTokens, 200),
    okTrue('R/★ 粒度越细地板越低（或持平）', floor32.floorTokens <= floor100.floorTokens),
    // ★★ 单调性交叉核对：二分依赖它，故用**线性复算**独立验。
    //   ★ 判据覆盖面教训（裁判 2026-10-10 的诊断「读到了，但判据没覆盖」）：
    //     本项原只覆盖 granularity=100 —— 判据在、覆盖面不在。若某个粒度的二分错了，
    //     标定报告（= K6 前置门证据）里的数字就是错的，而原判据**不会红**。
    //     ⇒ 现扩到**全部标定粒度 + 奇数粒度**（7/13/1024，用于试探非整除与边界）。
    (() => {
      const linearFloor = (entryTokens, maxN) => {
        for (let n = 1; n <= maxN; n++) {
          const entries = Array.from({ length: n }, (_, i) => ({
            seq: i + 1, kind: i % 2 === 0 ? 'tool/result' : 'user/message',
            tokens: entryTokens, text: 'x'.repeat(entryTokens * 4)
          }));
          const p = planCheckpoint({ entries, retainTokens: 0, minSavingsTokens: 32, maxScan: maxN });
          if (p.ok) return n * entryTokens;
        }
        return null;
      };
      const mismatches = [];
      let checked = 0;
      for (const et of [32, 100, 500, 2000, 7, 13, 1024]) {
        const b = measureOurFloor({ entryTokens: et, maxEntries: 600 });
        const lin = linearFloor(et, 600);
        const agree = b.ok ? (b.floorTokens === lin) : (lin === null);
        if (!agree) mismatches.push({ et, binary: b.floorTokens, linear: lin });
        checked += 1;
      }
      return okTrue(`R/★★ 二分与线性复算在**全部**粒度上一致（判据覆盖面，检查 ${checked} 个粒度）`,
        mismatches.length === 0 && checked >= 7, JSON.stringify(mismatches));
    })(),
    // 区间与结论
    eq('R/标定区间非空', calib.band.empty, false),
    eq('R/区间下界 = 最差地板', calib.band.from, calib.ourWorstFloorTokens),
    eq('R/区间上界 = 官方地板', calib.band.toExclusive, OFFICIAL_FLOOR.framedSummaryTokens),
    eq('R/区间宽度', calib.band.width, OFFICIAL_FLOOR.framedSummaryTokens - calib.ourWorstFloorTokens),
    okTrue('R/★ 结论为"立论成立"', /立论成立/.test(calib.verdict)),
    // ★★ 决定性判据
    eq('R/★★ 官方崩溃点上本核能缩小', calib.atOfficialCrashPoint.ok, true),
    eq('R/★★ 判据用的是崩溃点实测值', calib.atOfficialCrashPoint.shadowedTokens, 2466),
    okTrue('R/★★ 判据取最差粒度（保守）', /最差/.test(calib.atOfficialCrashPoint.reason)),
    okTrue('R/★★ 崩溃点落在区间内', calib.atOfficialCrashPoint.shadowedTokens >= calib.band.from && calib.atOfficialCrashPoint.shadowedTokens < calib.band.toExclusive),
    // ★ 负控：结论**不是恒真**
    eq('R/★ 负控：要求抬到不可能时本核无地板', impossible.ourWorstFloorTokens, null),
    okTrue('R/★ 负控：此时结论必须报"立项失败"', /立项失败/.test(impossible.verdict), impossible.verdict),
    okTrue('R/★ 负控：此时崩溃点判据也必须为假', impossible.atOfficialCrashPoint.ok === false),
    // 渲染
    okTrue('R/渲染含逐粒度表', /\| 条目粒度\(token\) \|/.test(renderCalibration(calib))),
    okTrue('R/渲染含决定性判据节', /决定性判据/.test(renderCalibration(calib))),
    okTrue('R/渲染含复跑命令', /--calibration/.test(renderCalibration(calib))),
    okTrue('R/渲染标注官方值是引用', /引用/.test(renderCalibration(calib))),
    // 预算侧无新地板
    eq('R/预算侧不引入地板（半阈值可缩）', budgetSanity(1_000_000).canShrinkAtHalf, true),
    eq('R/预算侧仍抢先官方', budgetSanity(1_000_000).preemptsOfficial, true)
  );

  /* ---- S. ★★ 负控 3「不静默」：压不动必须落成**可判的通知**，且与「沉默」可区分 ---- */
  const nerr = errHelper(NoticeError);
  const impPlan = planCheckpoint({ entries: [{ seq: 1, kind: 'user/message', tokens: 4, text: 'abcd' }], retainTokens: 0, minSavingsTokens: 100000, ...FIELDS });
  const nothing = planCheckpoint({ entries: mixed(5, 10), retainTokens: 100000, minSavingsTokens: 32, ...FIELDS });
  const nImp = buildCannotShrinkNotice(impPlan, { sessionSeq: 42, at: '2026-10-10T10:00:00+08:00', phase: 'pre-step' });
  const nNothing = buildCannotShrinkNotice(nothing, {});
  out.push(
    // 通知本体
    eq('S/通知 kind 逐字', nImp.kind, 'compaction/notice'),
    eq('S/通知 level = WARN', nImp.level, 'WARN'),
    okTrue('S/★ 通知非空文本', nImp.text.length > 0),
    okTrue('S/★ 通知含四组实测数字', nImp.text.includes(String(nImp.metrics.shadowedTokens)) && nImp.text.includes(String(nImp.metrics.checkpointTokens))),
    okTrue('S/通知被冻结', Object.isFrozen(nImp)),
    okTrue('S/metrics 被冻结', Object.isFrozen(nImp.metrics)),
    eq('S/可选上下文原样带上（无则不补默认）', nImp.sessionSeq, 42),
    eq('S/未给 at 则为 null（不注时钟 ⇒ 保持纯）', buildCannotShrinkNotice(impPlan, {}).at, null),
    okTrue('S/describeNotice 可读且含四数', /^notice=WARN code=\S+ shadowed=\d+ cp=\d+ savings=-?\d+ required=\d+$/.test(describeNotice(nImp))),
    // 成因码（闭集）
    okTrue('S/成因码在闭集内', Object.values(CANNOT_SHRINK_REASON).includes(nImp.code)),
    eq('S/阶梯走到底 ⇒ ladder_exhausted', nImp.code, CANNOT_SHRINK_REASON.LADDER_EXHAUSTED),
    eq('S/可遮区为空 ⇒ nothing_to_shadow', nNothing.code, CANNOT_SHRINK_REASON.NOTHING_TO_SHADOW),
    // ★★ 负控 3 的负控：通知必须与「沉默」可区分
    eq('S/★★ 通知非沉默', isSilent(nImp), false),
    eq('S/★★ 通知可区分（带可核数字）', distinguishable(nImp), true),
    eq('S/★★ null 是沉默', isSilent(null), true),
    eq('S/★★ 无 kind 是沉默', isSilent({ text: 'x' }), true),
    eq('S/★★ 空文本是沉默', isSilent({ kind: 'k', text: '' }), true),
    eq('S/★★ 沉默者不可区分', distinguishable(null), false),
    eq('S/★★ 有 kind/文本但无 metrics ⇒ 仍不可区分', distinguishable({ kind: 'k', text: 'x' }), false),
    // ★ 不许给成功态发通知（否则通知会退化成噪声、进而被忽略）
    nerr('S/★ ok=true 时不发通知（抛 NOT_A_FAILURE）', () => buildCannotShrinkNotice({ ok: true }, {}), 'NOT_A_FAILURE'),
    nerr('S/非对象 ⇒ 抛 BAD_RESULT', () => buildCannotShrinkNotice(null, {}), 'BAD_RESULT'),
    nerr('S/缺实测数字 ⇒ 抛 MISSING_METRIC（不许"只有人话没有数字"）',
      () => buildCannotShrinkNotice({ ok: false, verdict: 'plan_impossible', reason: 'x' }, {}), 'MISSING_METRIC'),
    nerr('S/数字为 NaN ⇒ 同样抛 MISSING_METRIC',
      () => buildCannotShrinkNotice({ ok: false, verdict: 'plan_impossible', reason: 'x', shadowedTokens: NaN, checkpointTokens: 1, requiredSavings: 1, savings: 0 }, {}), 'MISSING_METRIC')
  );

  /* ---- T. ★ 正控 2（保活）：retainTokens 窗口内的条目**逐字未变** ---- */
  const NASTY2 = '  前导\n制表\t中文 🎯 尾随  ';
  const tEntries = [
    { seq: 1, kind: 'tool/result', tokens: 50, text: 'old-1' },
    { seq: 2, kind: 'user/message', tokens: 50, text: 'old-2' },
    { seq: 3, kind: 'user/message', tokens: 60, text: NASTY2 },
    { seq: 4, kind: 'assistant/message', tokens: 60, text: 'keep-4' }
  ];
  // 序列化快照（逐字节）
  const snap = (arr) => jsonS(arr);
  function jsonS(x) { return canonicalJson(x); }
  const tPlan = planCheckpoint({ entries: tEntries, retainTokens: 120, minSavingsTokens: 32, ...FIELDS });
  const tRet = splitRetain(tEntries, 120);
  out.push(
    okTrue('T/保活区非空', tRet.retained.length > 0),
    eq('T/★ 保活区 = 尾部两条（120 token）', tRet.retained.map((e) => e.seq).join(), '3,4'),
    eq('T/★ 保活区逐字节未变（规范 JSON 比对）', snap(tRet.retained), snap(tEntries.slice(2))),
    okTrue('T/★ 刁钻正文逐字保留（含前导/制表/emoji/尾随空格）', tRet.retained[0].text === NASTY2),
    eq('T/被遮区不含任何保活 seq', tPlan.range === null || tPlan.range.endSeq < 3, true),
    okTrue('T/计划未改动输入 entries（纯函数）', snap(tEntries) === snap([{ seq: 1, kind: 'tool/result', tokens: 50, text: 'old-1' }, { seq: 2, kind: 'user/message', tokens: 50, text: 'old-2' }, { seq: 3, kind: 'user/message', tokens: 60, text: NASTY2 }, { seq: 4, kind: 'assistant/message', tokens: 60, text: 'keep-4' }]))
  );

  return out;
}

/** K4 全量自检。两个消费者共用。 */
export function runK4SelfTest() {
  const raw = k4Cases();
  const cases = raw.map((c) => {
    const i = c.name.indexOf('/');
    return { suite: c.name.slice(0, i), name: c.name.slice(i + 1), ok: c.ok, got: c.got, want: c.want };
  });
  const failed = cases.filter((c) => !c.ok);
  const bySuite = {};
  for (const c of cases) bySuite[c.suite] = (bySuite[c.suite] || 0) + 1;
  return { ok: failed.length === 0, total: cases.length, failed: failed.length, bySuite, cases };
}

/** 逐位确定的证明用摘要。 */
export function digestK4() {
  const r = runK4SelfTest();
  const canon = canonicalJson(r.cases.map((c) => ({ s: c.suite, n: c.name, ok: c.ok, got: c.got })));
  return { sha256: createHash('sha256').update(canon).digest('hex'), assertions: r.total, allPass: r.ok };
}
