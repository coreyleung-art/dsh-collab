/**
 * index.js — dsh 插件形态（宿主平面 / host plane）：注册 csx_* 工具 + 空守卫
 * =============================================================================
 * ★ 当前阶段见 `lib/meta.js` 的 `STAGE`；**三件的逐件接线状态见同一处的 `WIRING`** ——
 *   本文件**不重复声明**（2026-10-10 实测：同一文件里 csx_status 报 wired 而 csx_checkpoint 报未接线，
 *   根因就是状态被手写在多处；现由 `WIRING` 派生，并由 `contract-check ⑤` 守住）。
 *   ① 判据在 `lib/wire.js`、副作用在本文件 `runWritePath`；② `persistCheckpoint`；③ `csx_recall` → `ledgerForUse` + `recall`。
 *   ★ 但**开关仍是 `enableGuard: false`**：接线完成 ≠ 已启用；启用要等独立验证（K6 明文纪律）。
 *
 *   本文件此刻做四件事：
 *     1) apply() 最前跑 R014 自查（失败不阻塞挂载）；
 *     2) 注册三个工具：
 *        · csx_status  —— 只读，回报守卫读数 + **逐件接线状态**（wiring.write/persist/recall）；
 *        · csx_checkpoint —— 手动立即版：走**同一条**写入路径，但 `enableGuard=false` 时**只预演不落笔**；
 *        · csx_recall   —— 从**本会话自己的账本**三态召回（HIT/MISS/DEGRADED）；
 *     3) 若 config.enableGuard === true，注册 agent/pre-step 监听器——它**读**压力（tokenMeter 测量 +
 *        适配器 contextWindow + 预算阈值判定），**仅在达阈值那一步**走写入路径；
 *     4) 无论 3) 是否开启，注册过程与运行期都可能零动作。
 *   ★ **`enableGuard` 默认为 false**：① 接线完成后**仍保持 false**，直到它被独立验证（K6 明文纪律）。
 *   ★ 仍**不接管** ctx.compaction：本插件与官方 compaction-basic 并存。
 *   见 docs/project-init-context-survival-backend-20261010.md §7。
 *
 *   为什么"测量"也用 ctx.get() 取服务而不是写进 inject：见 lib/guard.js 文件头
 *   （inject 缺一条 ⇒ 整棵插件树加载失败；可选服务一律 get 取，拿不到就如实报跳过）。
 *
 * ★ 两条结构性铁律（源码层写死，`--lean4-check` 逐条证明）：
 *   - **inject 只有 'tools'**：宿主端绝不 inject 客户端专属服务（slots）或官方 realm 独占服务
 *     （compaction / toolResultPruner）。写错 ⇒ 该条永久 pending ⇒ 整棵插件树加载失败、CLD 起不来
 *     （2026-10-09 excalidraw 事故）。见 lib/gate.js checkInject()。
 *   - **不接管压缩后端**（seam b）：本插件与官方 compaction-basic **并存**，
 *     `ctx.compaction` 仍归官方——本守卫崩溃/拒动时，官方行为零变化（立项书不变量 I4）。
 */
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { PLUGIN_SLUG, PLUGIN_NAME, VERSION, STAGE, WIRING, wiringText, log, logMount } from './meta.js';
import { RECALL_KINDS, resolveRecallTarget, GateError, GATE_META } from './gate.js';
import { observePressure, formatReading } from './guard.js';
import { BUDGET_DEFAULTS, DECISION } from './budget.js';
import { compactionGuardFrom, describeGuardResult } from './events.js';
import { saveLedgerFile, ledgerForUse, READ_STATUS } from './ledger-io.js';
import { recordCheckpoint, recall, RECALL_STATUS } from './ledger.js';
import {
  WIRE_ACTION, decideWrite, hostMeterRecheck, buildCheckpointMessage, appendArgs,
  describeWire, describeNoticeOrNone, resolveLedgerPath, ledgerRecordFrom, LEDGER_FILE_TEMPLATE
} from './wire.js';

/**
 * K3 并发护栏：从**会话事件流**读"是否已有压缩在途"（复刻官方 assertNoActiveCompaction）。
 * ★ 纯读、绝不抛出（`compactionGuardFrom` 内部已包）——读不到就如实报 unknown 并保守放行，
 *   因为本插件是**旁观者**：它误判"忙"只是不压，误判"闲"也只是多压一次；**绝不能把宿主搞挂**。
 */
function readCompactionGuard(payload) {
  return compactionGuardFrom(payload?.agent?.session?.events);
}

/**
 * ★★ K6 ② 落盘（副作用层）：把刚写入的检查点记进账本并原子落盘。
 *
 * ★ 两条不可让步的判据：
 *   1) **绝不覆盖 DEGRADED 账本**：一个读不回来的账本可能是该历史**唯一**的副本，
 *      覆盖 = 永久丢掉"已压掉的那一段"（而那正是 csx_recall 唯一能取回的东西）。
 *      ⇒ 读回三态里 DEGRADED 一律**不写**，只告警 + 计数。
 *   2) **落盘失败绝不静默、也绝不影响会话**：写失败 ⇒ 记读数 + 告警；会话侧的写入已经成功，
 *      不回滚（观察器契约：守卫的次级目标失败，不得反噬主路径）。
 *
 * @returns 冻结的 {ok, path, bytes, scoped, degraded, reason}
 */
function persistCheckpoint(args) {
  const { ctx, session, config, plan } = args;
  const resolved = resolveLedgerPath(config.ledgerFile, session?.id, os.homedir());
  if (resolved.ok !== true) return Object.freeze({ ok: false, path: null, scoped: false, degraded: false, reason: resolved.reason });
  if (resolved.scoped !== true) ctx.logger.warn(`context-survival ${resolved.reason}`);
  const record = ledgerRecordFrom(plan, () => randomUUID());
  if (record === null) {
    return Object.freeze({ ok: false, path: resolved.path, scoped: resolved.scoped, degraded: false, reason: '计划缺原始条目 ⇒ 账本记录造不出，未落盘（不伪造账本）' });
  }
  const led = ledgerForUse(resolved.path);
  if (led.degraded === true) {
    return Object.freeze({
      ok: false, path: resolved.path, scoped: resolved.scoped, degraded: true,
      reason: `账本不可用（${led.reason}）⇒ **不覆盖**、不落盘，保留原文件待人工处置`
    });
  }
  let next;
  try { next = recordCheckpoint(led.ledger, record); }
  catch (e) {
    return Object.freeze({ ok: false, path: resolved.path, scoped: resolved.scoped, degraded: false, reason: `记账失败（${e instanceof Error ? e.message : String(e)}）⇒ 未落盘` });
  }
  const w = saveLedgerFile(resolved.path, next);
  return Object.freeze({
    ok: w.ok === true, path: resolved.path, scoped: resolved.scoped, degraded: false, bytes: w.bytes,
    reason: w.ok === true
      ? `${w.reason}｜检查点 ${record.id.slice(0, 8)} seq ${record.startSeq}-${record.endSeq}（${record.entries.length} 条原文）`
      : `${w.reason} ⇒ 未落盘（会话侧写入已成功，不回滚）`
  });
}

/**
 * ★★ K6 ① 写入路径（副作用层）。判据在 `lib/wire.js`（纯、可离线全覆盖），此处**只做一件事**：
 *    把判据说"可以写"的那一份计划，真的接到 `session.append(...)` 上。
 *
 * 三条硬约束（逐条对应宿主源码，R030 已核实）：
 *   · **宿主尺复核**（`requiresHostMeterCheck`，replace.js:141；官方同判据 dsh-compaction-basic:555-556）
 *   · **写前再判一次并发护栏**（官方 assertNoActiveCompaction 在异步决策后会复查，:504-516）
 *   · 形状必须过宿主表面契约（dsh-session/lib/index.js:1444-1465 + assertProvenance:324-340）
 *
 * ★ 契约：本函数**绝不抛出**。任何一步不满足都如实返回 `wrote:false` + 原因（观察器契约）。
 *
 * @param {{ctx:object, session:object, config:object, decision:object, busy:boolean, commit:boolean, payload:object}} args
 *        `commit:false` ⇒ 只走到"计划 + 宿主尺复核"为止（**预演**，零副作用）
 */
function runWritePath(args) {
  const { ctx, session, config, decision, busy, commit, payload, manual } = args;
  const out = { action: null, plan: null, notice: null, wrote: false, appendedSeq: null, reason: '', recheck: null, persist: null };

  const meter = ctx.get('tokenMeter');
  if (meter === undefined || typeof meter.measure !== 'function') {
    return { ...out, action: 'no_token_meter', reason: '宿主无 tokenMeter ⇒ 不写（宁可不压）' };
  }
  let measurement;
  try { measurement = meter.measure(session); }
  catch (e) { return { ...out, action: 'measure_failed', reason: `measure 抛错（${e instanceof Error ? e.message : String(e)}）⇒ 不写` }; }
  const estimateMessage = typeof meter.estimateMessage === 'function' ? (m) => meter.estimateMessage(m) : undefined;

  // 手动路径（csx_checkpoint）：不等阈值，把"当前压力"当阈值 ⇒ neededSavings=0，只受 minSavingsTokens 约束
  const effective = manual === true
    ? { action: DECISION.COMPRESS, measuredTokens: Number.isFinite(measurement?.totalTokens) ? measurement.totalTokens : 0, threshold: Number.isFinite(measurement?.totalTokens) ? measurement.totalTokens : 0 }
    : decision;

  const decided = decideWrite({
    measurement,
    events: session.events,
    config,
    decision: effective,
    hasOpenCompaction: busy === true
  });
  out.action = decided.action;
  out.reason = decided.reason;
  if (decided.plan !== undefined) out.plan = decided.plan;
  if (decided.notice !== undefined && decided.notice !== null) out.notice = decided.notice;

  if (decided.action !== WIRE_ACTION.WRITE) return out;

  const plan = decided.plan;
  const message = buildCheckpointMessage(plan.handoffText, () => randomUUID(), PLUGIN_SLUG);
  if (message === null) return { ...out, action: 'bad_message', reason: '交接块正文为空或 id 工厂失效 ⇒ 不写' };

  const recheck = hostMeterRecheck({ plan, message, estimateMessage, nodes: measurement.nodes });
  out.recheck = recheck;
  if (recheck.ok !== true) return { ...out, action: 'host_meter_reject', reason: recheck.reason };

  if (commit !== true) return { ...out, action: 'dry_run', reason: '预演：判据全过，但未写入（enableGuard=false）' };

  // ★ 写前**再判一次**并发护栏：decide 时的读数可能已经过期（官方在异步决策后同样复查）
  const cguard2 = readCompactionGuard(payload);
  if (cguard2.busy === true) {
    return { ...out, action: 'busy_before_write', reason: '写前复查：官方压缩在途 ⇒ 放弃本次写入' };
  }

  let event;
  try {
    event = session.append('user/message', message, appendArgs(plan));
  } catch (e) {
    // 宿主表面契约拒收（例如区间已不再合法）⇒ 如实记，绝不重试、绝不改形状硬塞
    return { ...out, action: 'append_rejected', reason: `宿主拒收（${e instanceof Error ? e.message : String(e)}）⇒ 本次零变更` };
  }
  return { ...out, wrote: true, appendedSeq: event?.seq ?? null, reason: `${recheck.reason} ⇒ 已写入 seq=${event?.seq}`, persist: persistCheckpoint({ ctx, session, config, plan }) };
}

export const name = PLUGIN_NAME;
/** 宿主端只 inject host 平面真实存在的服务。**不得**加 slots / compaction（见文件头）。 */
export const inject = ['tools'];

/** 立项书 §1 六条不变量（随 csx_status 一起返回，供模型/人对照）。 */
const INVARIANTS = Object.freeze([
  { id: 'I1', claim: '保证能减：要么产出严格更小的活跃窗口，要么明确判"不可压"并告警——绝不静默 no-op' },
  { id: 'I2', claim: '不摘要：检查点由原文片段 + 指针组成，不做模型生成' },
  { id: 'I3', claim: '最新保活：retainTokens 窗口内逐字保留' },
  { id: 'I4', claim: '并存不独占：ctx.compaction 仍归官方，本守卫崩溃时官方行为零变化' },
  { id: 'I5', claim: '可召回：被压掉的每一段都有 seq 指针，可逐字找回' },
  { id: 'I6', claim: '交接可续：检查点带结构化交接字段，供跨会话信标四件套复用' }
]);

/** ★ 嵌套 object 必须显式声明 additionalProperties，否则 defineTool 抛 UNSUPPORTED_SCHEMA。 */
function obj(extra = {}) { return { type: 'object', additionalProperties: true, ...extra }; }

function makeStatusOutput() {
  return {
    schema: obj({
      properties: {
        ok: { type: 'boolean' },
        plugin: { type: 'string' },
        version: { type: 'string' },
        caliber: obj(),
        stage: { type: 'string' },
        implemented: { type: 'boolean' },
        wiring: obj(),
        invariants: { type: 'array', items: obj({ properties: { id: { type: 'string' }, claim: { type: 'string' } } }) },
        gate: obj(),
        guard: obj(),
        wiring: obj(),
        note: { type: 'string' }
      }
    }),
    // ★★ 官方契约：defineTool 取 options.output.render 并包一层 render() 调用它。
    //    缺 render ⇒ userRender 为 undefined ⇒ 一调工具即 'userRender is not a function'。
    //    ★ 本条由**第一次真实调用**发现（322 条纯断言找不到 —— 它不在我的逻辑里，在宿主契约里）。
    //    形态照本机既有插件（agent-bus / bb-card-send / channel-gate / drift-scan 等）。
    render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]
  };
}

function makeCheckpointOutput() {
  return {
    schema: obj({
      properties: {
        ok: { type: 'boolean' },
        implemented: { type: 'boolean' },
        // ★ K6 ① 接线后新增（逐一显式声明：嵌套 object 不声明 additionalProperties 会被 defineTool 拒）
        wrote: { type: 'boolean' },
        dryRun: { type: 'boolean' },
        commit: { type: 'boolean' },
        action: { type: 'string' },
        // ★ 可空字段必须显式 oneOf [T, null]：宿主**会按 output.schema 校验返回值**
        //   （dsh-tools/lib/index.js:3406 validateJsonSchemaValue(tool.output.schema, …)），
        //   而 `type: ['number','null']` 这种**数组 type 不被支持** —— 我第一次就是这么写错的，
        //   322 条纯断言全绿、apply() 冒烟一跑就报 "schema.properties.appendedSeq.type must be …"。
        //   ⇒ 与 output.render 同族：**缺陷在宿主契约里，不在逻辑里**。
        appendedSeq: { oneOf: [{ type: 'number' }, { type: 'null' }] },
        plan: { oneOf: [obj(), { type: 'null' }] },
        hostMeterCheck: { oneOf: [obj(), { type: 'null' }] },
        persist: { oneOf: [obj(), { type: 'null' }] },
        notice: { oneOf: [obj(), { type: 'null' }] },
        coreStatus: obj(),
        reason: { type: 'string' },
        version: { type: 'string' }
      }
    }),
    // ★★ 官方契约：defineTool 取 options.output.render 并包一层 render() 调用它。
    //    缺 render ⇒ userRender 为 undefined ⇒ 一调工具即 'userRender is not a function'。
    //    ★ 本条由**第一次真实调用**发现（322 条纯断言找不到 —— 它不在我的逻辑里，在宿主契约里）。
    //    形态照本机既有插件（agent-bus / bb-card-send / channel-gate / drift-scan 等）。
    render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]
  };
}

function makeRecallOutput() {
  return {
    schema: obj({
      properties: {
        ok: { type: 'boolean' },
        implemented: { type: 'boolean' },
        target: { oneOf: [obj(), { type: 'null' }] },
        error: { oneOf: [obj(), { type: 'null' }] },
        // ★ K6 ③ 接线后新增（HIT/MISS/DEGRADED 三态 + 逐字正文 + 账本三态）
        status: { type: 'string' },
        entries: { type: 'array', items: obj() },
        text: { oneOf: [{ type: 'string' }, { type: 'null' }] },
        evicted: { type: 'number' },
        ledger: { oneOf: [obj(), { type: 'null' }] },
        coreStatus: obj(),
        reason: { type: 'string' },
        version: { type: 'string' }
      }
    }),
    // ★★ 官方契约：defineTool 取 options.output.render 并包一层 render() 调用它。
    //    缺 render ⇒ userRender 为 undefined ⇒ 一调工具即 'userRender is not a function'。
    //    ★ 本条由**第一次真实调用**发现（322 条纯断言找不到 —— 它不在我的逻辑里，在宿主契约里）。
    //    形态照本机既有插件（agent-bus / bb-card-send / channel-gate / drift-scan 等）。
    render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]
  };
}

export function apply(ctx, config = {}) {
  // ★★ K6-P1 挂载记录（星桥批准 · 五条件）：**apply() 时立刻**落一行，别懒到首调（C3）。
  //   纯日志、绝不抛出、绝不改状态（C1）；字段见 lib/meta.js::mountRecord（C2）；
  //   一行 JSON 可 cat 读出（C4）；判据与负控在 tools/csx-mount-record-check.py（C5）。
  //   ★ 不替代 T3 的在役实测 —— 它只证「某进程在 ts 时刻以 pid 加载了这组哈希」。
  logMount({ stage: STAGE, wiring: { ...WIRING }, inject: [...inject], mountMode: config.__mountMode });

  // R014 自查门（apply 最前）。失败不阻塞挂载，但会留下 ~/.dsh/plugin-selfcheck 记录。
  try {
    runSelfCheck(PLUGIN_SLUG, {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'resolveRecallTarget', 'resolveBudget', 'observePressure'],
      sourceFiles: ['lib/index.js', 'lib/budget.js', 'lib/guard.js'],
      baseDir: path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  // ---- K2 守卫读数（只读累加，供 csx_status 回报；不参与任何决策） ----
  const guardStats = {
    enabled: config.enableGuard === true,
    steps: 0, compress: 0, belowThreshold: 0, skipped: 0,
    skipReasons: {}, last: null, lastAt: null,
    // ★ K3 并发护栏计数（真判据，非写死）：busy = 压缩在途；staleIgnored = 未配对 start 被 end-seed 判陈旧
    concurrencyBusy: 0, concurrencyFree: 0, concurrencyStaleIgnored: 0, lastConcurrency: null,
    // ★ K6 ① 写入读数（写入路径接线后新增；每一项都由 runWritePath 的真实返回值驱动，非写死）
    writes: 0,            // 真正 append 成功的次数
    writeAbandoned: 0,    // 走到写入步骤但放弃了（宿主尺拒 / 写前复查在途 / 宿主拒收）
    cannotShrink: 0,      // 判"压不动"的次数（I1：不静默）—— ★ **不含**"不适用面"（后者单列，见下）
    notApplicable: 0,     // ★ 模型不适用（如表面非单调）的次数：不是压不动，也不是失败
    notices: 0,           // 构造出的不可缩小通知条数
    lastWire: null,       // 最近一次写入路径的结论（describeWire 的一行）
    // ★★ 2026-10-10 星桥一问暴露的不可判：原读数只有 lastWire，缺「**哪条路径 · 何时 · 哪个会话**」
    //    ⇒ 读到一条 `wire=dry_run` 却无法判它来自谁、什么时候。补三项 + 一个**环形近期记录**。
    //    ★ 另须知道：这些计数是**进程级**（apply() 闭包），**跨会话共享** ⇒ 别人读到的是我这次会话的记录。
    lastVia: null,        // 'manual'(csx_checkpoint) | 'auto'(agent/pre-step 守卫)
    lastSessionId: null,  // 产生该记录**所在的会话**（截断显示）
    lastOutcomeAt: null,  // 最近一次"走到写入路径"的时刻（**含 dry_run**，不只是成功写入）
    recent: [],           // 最近 5 条结论（环形），每条 {at, via, sessionId, line}
    // ★★ 2026-10-10 判决（「读状态先定作用域」的**存储侧**修法）：上面的计数器是**进程级聚合**，
    //   而"进程级共享字段读出的是**所有会话的合并**"⇒ 光加时刻/lastSessionId 不够，**必须分域**。
    //   照本机既有范例：邮箱 `cursor/<party>` 分域 · `bb_dualwrite` 的 `writer` 字段。
    //   ⇒ 本表按 **sessionId 键**存每会话读数（有界：最多 8 个会话，超出淘汰最旧键）。
    bySession: {},        // { <sessionId>: {steps, writes, cannotShrink, notApplicable, abandoned, lastWire, lastOutcomeAt} }
    lastWriteSeq: null,   // 最近一次写入的事件 seq
    lastWriteAt: null,
    // ★ K6 ② 落盘读数
    ledgerWrites: 0,      // 账本成功落盘次数
    ledgerFailures: 0,    // 落盘失败/被拒次数（★ 不为 0 即须看原因，绝不静默）
    lastLedger: null      // 最近一次落盘的一行结论
  };

  // ---- 写入路径的读数记账（**一处**，供自动路径与手动工具共用，避免两处各记一份而漂）----
  /** 分域账（有界）：把每会话读数记到 bySession[sessionId] 下（**不是**把聚合值当某会话的事实）。 */
  function accountBySession(sid, patch) {
    const key = sid === undefined || sid === null ? '(unknown-session)' : String(sid).slice(0, 24);
    const cur = guardStats.bySession[key] === undefined
      ? { steps: 0, writes: 0, cannotShrink: 0, notApplicable: 0, abandoned: 0, lastWire: null, lastOutcomeAt: null }
      : guardStats.bySession[key];
    Object.assign(cur, patch);
    cur.lastOutcomeAt = new Date().toISOString();
    guardStats.bySession[key] = cur;
    const keys = Object.keys(guardStats.bySession);
    if (keys.length > 8) delete guardStats.bySession[keys[0]];   // 有界：超 8 会话淘汰最旧键
    return cur;
  }

  function accountWrite(w, meta = {}) {
    // ★ 记账元信息（路径/会话/时刻）——**每一次**都记，含 dry_run 与放弃（不再只记成功）
    guardStats.lastVia = meta.via === undefined ? null : meta.via;
    guardStats.lastSessionId = meta.sessionId === undefined ? null : meta.sessionId;
    guardStats.lastOutcomeAt = new Date().toISOString();
    guardStats.recent.unshift({ at: guardStats.lastOutcomeAt, via: guardStats.lastVia, sessionId: guardStats.lastSessionId, line: describeWire(w) });
    if (guardStats.recent.length > 5) guardStats.recent.length = 5;
    if (w.notice !== null && w.notice !== undefined) {
      guardStats.notices += 1;
      ctx.logger.warn(`context-survival ${describeNoticeOrNone(w.notice)}`);
    }
    if (w.wrote === true) {
      guardStats.writes += 1;
      guardStats.lastWriteSeq = w.appendedSeq;
      guardStats.lastWriteAt = new Date().toISOString();
      accountBySession(meta.sessionId, { writes: (guardStats.bySession[String(meta.sessionId ?? '(unknown-session)').slice(0, 24)]?.writes || 0) + 1, lastWire: describeWire(w) });
    } else if (w.action === WIRE_ACTION.CANNOT_SHRINK) {
      guardStats.cannotShrink += 1;
      accountBySession(meta.sessionId, { cannotShrink: (guardStats.bySession[String(meta.sessionId ?? '(unknown-session)').slice(0, 24)]?.cannotShrink || 0) + 1, lastWire: describeWire(w) });
    } else if (w.action === WIRE_ACTION.NOT_APPLICABLE) {   // ★ 不适用面单列，不混入"压不动"
      guardStats.notApplicable += 1;
      accountBySession(meta.sessionId, { notApplicable: (guardStats.bySession[String(meta.sessionId ?? '(unknown-session)').slice(0, 24)]?.notApplicable || 0) + 1, lastWire: describeWire(w) });
    } else if (w.action !== 'dry_run') {
      guardStats.writeAbandoned += 1;
      accountBySession(meta.sessionId, { abandoned: (guardStats.bySession[String(meta.sessionId ?? '(unknown-session)').slice(0, 24)]?.abandoned || 0) + 1, lastWire: describeWire(w) });
    } else {
      accountBySession(meta.sessionId, { lastWire: describeWire(w) });   // dry_run 也按会话记（它此前只改聚合）
    }
    if (w.persist !== null && w.persist !== undefined) {
      if (w.persist.ok === true) { guardStats.ledgerWrites += 1; guardStats.lastLedger = `ledger=ok ${w.persist.path}`; }
      else {
        guardStats.ledgerFailures += 1;
        guardStats.lastLedger = `ledger=FAIL(${w.persist.degraded ? 'degraded' : 'error'}) ${w.persist.reason}`;
        // ★ 落盘失败**不得静默**：会话侧写入已成功，但账本没记住 ⇒ 那段内容将来取不回来
        ctx.logger.warn(`context-survival ② 落盘未成功：${w.persist.reason}`);
        log('ledger-persist-failed', { path: w.persist.path, reason: w.persist.reason, degraded: w.persist.degraded === true });
      }
    }
    guardStats.lastWire = describeWire(w);
    return w;
  }

  const tools = [
    defineTool({
      name: 'csx_status',
      description:
        '上下文存活守卫状态（只读）：本插件版本、当前阶段、六条不变量、结构门元信息，' +
        '以及守卫的累计读数（步数 / 触发 / 未达阈 / 跳过原因 / 并发护栏计数）。**不读会话、不改状态**。',
      parameters: {},
      output: makeStatusOutput(),
      async execute() {
        return {
          ok: true,
          plugin: PLUGIN_NAME,
          version: VERSION,
          stage: STAGE,
          // ★★ 判决 2026-10-10：「三态不仅要有『不可判』，还要有**绿的成色**」——
          //   本读数是在役跑的、还是夹具里跑的？靠 config.__mountMode（正向证据）判定；
          //   **没有正向证据就写「口径未证」，而不是默认成"在役"**。
          caliber: (() => {
            const m = config.__mountMode === undefined || config.__mountMode === null
              ? null : String(config.__mountMode);
            const text = m === 'serve' ? '**在役口径**（宿主内运行）'
              : m === 'smoke' ? '**夹具口径** —— 进程内假 ctx/假会话，**不等于在役**'
              : '**口径未证**（无正向证据 ⇒ 不得当作在役）';
            return { mode: m, text };
          })(),
          implemented: false,
          // ★ K6 逐件状态（不是一句话的"实现了没"）：三件接线各自可判，避免又一处"契约滞留"
          // ★ 逐件状态**全部由 meta.WIRING 派生**（P2：此前手写在多处 ⇒ 同文件内自相矛盾）
          wiring: {
            write: WIRING.write ? 'wired' : 'pending',
            persist: WIRING.persist ? 'wired' : 'pending',
            recall: WIRING.recall ? 'wired' : 'pending',
            note: `${wiringText()}；` + (guardStats.enabled
              ? '守卫已启用 ⇒ 自动路径会写。'
              : '但守卫未启用（enableGuard=false）⇒ 自动路径不写；csx_checkpoint 只做**预演**（不写）。')
          },
          invariants: INVARIANTS.map((i) => ({ id: i.id, claim: i.claim })),
          gate: { recallKinds: [...GATE_META.recallKinds], allowedInject: [...GATE_META.allowedInject], principle: GATE_META.principle },
          guard: {
            enabled: guardStats.enabled,
            steps: guardStats.steps,
            compress: guardStats.compress,
            belowThreshold: guardStats.belowThreshold,
            skipped: guardStats.skipped,
            skipReasons: { ...guardStats.skipReasons },
            last: guardStats.last,
            lastAt: guardStats.lastAt,
            concurrency: {
              busy: guardStats.concurrencyBusy,
              free: guardStats.concurrencyFree,
              staleStartIgnored: guardStats.concurrencyStaleIgnored,
              last: guardStats.lastConcurrency
            },
            // ★ K6 ① 写入读数（真返回值驱动）
            write: {
              writes: guardStats.writes,
              abandoned: guardStats.writeAbandoned,
              cannotShrink: guardStats.cannotShrink,
              notApplicable: guardStats.notApplicable,
              notices: guardStats.notices,
              last: guardStats.lastWire,
              lastSeq: guardStats.lastWriteSeq,
              lastAt: guardStats.lastWriteAt,
              // ★ 判「这条结论是谁在何时留下的」所需的三项 + 近期环形（含 dry_run 与放弃）
              lastVia: guardStats.lastVia,
              lastSessionId: guardStats.lastSessionId,
              lastOutcomeAt: guardStats.lastOutcomeAt,
              recent: guardStats.recent,
              bySession: guardStats.bySession,   // ★ 分域读数：键=会话 id ⇒ 读状态先定作用域
              // ★★ 口径声明（防误读）：以下计数与 last* 均属**本进程**（apply 闭包）⇒ **跨会话共享**；
              //    要判"某会话发生了什么"，须看 lastSessionId / recent 里的 sessionId，而不是把它们当本会话的事实。
              caliber: (() => {
                // ★★ 判决（2026-10-10）：「三态不仅要有『不可判』，还要有**绿的成色**」——
                //   本读数是**在役**跑的、还是在**夹具**里跑的？答案来自 config.__mountMode（正向证据），
                //   没有正向证据就写「口径未证」而**不是**默认成"在役"。
                const m = config.__mountMode === undefined || config.__mountMode === null
                  ? null : String(config.__mountMode);
                const text = m === 'serve' ? '**在役口径**（宿主内运行）'
                  : m === 'smoke' ? '**夹具口径** —— 进程内假 ctx/假会话，**不等于在役**'
                  : '**口径未证**（无正向证据 ⇒ 不得当作在役）';
                return { mode: m, text };
              })(),
              scope: '进程级聚合 + bySession 分域两者并存：读**聚合**前请先定作用域（聚合=所有会话的合并；要判本会话请看 bySession[你的会话id]）'
            },
            // ★ K6 ② 落盘读数
            ledger: {
              fileTemplate: config.ledgerFile === undefined ? LEDGER_FILE_TEMPLATE : config.ledgerFile,
              writes: guardStats.ledgerWrites,
              failures: guardStats.ledgerFailures,
              last: guardStats.lastLedger
            },
            mode: guardStats.enabled ? 'wired' : 'measure-only',
            budgetDefaults: { ...BUDGET_DEFAULTS },
            note: guardStats.enabled
              ? '① 写入已接线且守卫已启用 ⇒ 达阈值时按 lib/wire.js 判据写入（宿主尺复核 + 写前并发复查）。'
              : `${WIRING.write ? '① 写入路径**已接线但未启用**' : '① 写入路径**未接线**'}（enableGuard=false）⇒ 自动路径零变更、csx_checkpoint 只预演。逐件状态：${wiringText()}。`
          },
          note: `阶段 ${STAGE}：${wiringText()}；开关仍为 enableGuard=${guardStats.enabled}（接线 ≠ 启用）。`
        };
      }
    }),
    defineTool({
      name: 'csx_checkpoint',
      description:
        '手动插入一个非摘要检查点（自动触发的立即版）：用宿主尺复核 + 写前并发复查后，把「原文片段 + seq 指针」写回会话。'
        + '★ 与自动守卫**共用同一个开关**：enableGuard=false 时**只预演不落笔**（返回完整计划与宿主尺复核结果，wrote=false，零变更）。'
        + `★ 产出核（lib/checkpoint.js）已实现并全绿，条数由调用时实时读回。逐件状态：${wiringText()}。`,
      parameters: {},
      output: makeCheckpointOutput(),
      async execute(_args, exec) {
        const session = exec?.agent?.session;
        if (session === undefined || session === null) {
          return {
            ok: false, implemented: true, wrote: false,
            reason: '本调用没拿到会话（exec.agent.session 缺失）⇒ 无从插入检查点，本步零变更。',
            coreStatus: { writeWired: WIRING.write, persistWired: WIRING.persist, recallWired: WIRING.recall },
            version: VERSION
          };
        }
        // ★ 同一个 enableGuard 开关：守卫关着 ⇒ 写入路径**只预演不落笔**（判据全跑，含宿主尺复核）
        const commit = config.enableGuard === true;
        const cguard = readCompactionGuard({ agent: exec?.agent });
        const r = accountWrite(runWritePath({ ctx, session, config, busy: cguard.busy, commit, manual: true, payload: { agent: exec?.agent } }),
          { via: 'manual', sessionId: session?.id === undefined ? null : String(session.id).slice(0, 24) });
        log('checkpoint-manual', { action: r.action, wrote: r.wrote, seq: r.appendedSeq, commit, ledgerOk: r.persist === null || r.persist === undefined ? null : r.persist.ok });
        return {
          ok: true, implemented: commit === true, wrote: r.wrote === true,
          dryRun: r.wrote !== true,
          action: r.action,
          commit,
          appendedSeq: r.appendedSeq,
          reason: r.reason,
          // ★ 计划的**失败态**不带 surfaceOp/shadowedSeqs（例如"表面为空"只有一句 reason）⇒ 逐字段设防，
          //   否则就是 `undefined.length` 当场崩。本条同样是**真调一次**才发现的（冒烟第三次抓到的缺陷）。
          plan: r.plan === null ? null : {
            ok: r.plan.ok === true,
            verdict: r.plan.verdict ?? null,
            rung: r.plan.rung ?? null,
            rungLabel: r.plan.rungLabel ?? null,
            surfaceOp: r.plan.surfaceOp ?? null,
            shadowedCount: Array.isArray(r.plan.shadowedSeqs) ? r.plan.shadowedSeqs.length : null,
            shadowedTokens: Number.isFinite(r.plan.shadowedTokens) ? r.plan.shadowedTokens : null,
            checkpointTokens: Number.isFinite(r.plan.checkpointTokens) ? r.plan.checkpointTokens : null,
            savings: Number.isFinite(r.plan.savings) ? r.plan.savings : null,
            requiredSavings: Number.isFinite(r.plan.requiredSavings) ? r.plan.requiredSavings : null,
            reason: typeof r.plan.reason === 'string' ? r.plan.reason : null
          },
          hostMeterCheck: r.recheck,
          persist: r.persist,
          notice: r.notice,
          // ★ 逐件状态 + 模块声明（contract-check ② 只扫 coreStatus 里的 module 字段，按值当路径核存在性；
          //   这里把"写入判据层"与"产出核"两处依赖都声明出来 —— 否则该检查的输入集会**静默变小**，
          //   正是本项目反复踩的那一族。★ 注意：连注释里都别写那个键值写法，否则也会被扫成一条路径）
          coreStatus: {
            module: 'lib/wire.js',
            planCore: { module: 'lib/checkpoint.js' },
            writeWired: WIRING.write, persistWired: WIRING.persist, recallWired: WIRING.recall
          },
          version: VERSION
        };
      }
    }),
    defineTool({
      name: 'csx_recall',
      description:
        '按会话内指针逐字取回被省略的内容。目标种类在 schema 层枚举（seq / range / checkpoint），' +
        'id 只能是有界数字或数字区间——**不接受路径、命令或 URL**。'
        + '★ 从**本会话自己的账本**取（账本按会话分文件：seq 是会话内编号，取错会话比 MISS 更坏）。'
        + '★ 三态如实：HIT / MISS / DEGRADED —— **账本读不回来时报 DEGRADED，绝不说"该内容不存在"**。',
      parameters: {
        kind: { type: 'string', required: true, enum: [...RECALL_KINDS], description: '目标种类（枚举，无法传入其它值）' },
        id: { type: 'string', required: true, description: 'seq/checkpoint 为 1-7 位数字；range 为 <数字>-<数字>' }
      },
      output: makeRecallOutput(),
      async execute(args, exec) {
        let target;
        try {
          target = resolveRecallTarget({ kind: args.kind, id: args.id });
        } catch (e) {
          if (e instanceof GateError) {
            return {
              ok: false, implemented: true, error: { code: e.code, message: e.message }, ledger: null,
              status: RECALL_STATUS.DEGRADED, coreStatus: { wired: WIRING.recall, recallWired: WIRING.recall }, version: VERSION
            };
          }
          throw e;
        }
        // ---- ★ K6 ③ 召回接线：账本按**本会话**定位（seq 是会话内编号，取错会话比 MISS 更坏）----
        const session = exec?.agent?.session;
        const resolved = resolveLedgerPath(config.ledgerFile, session?.id, os.homedir());
        if (resolved.ok !== true) {
          return {
            ok: true, implemented: true, target,
            status: RECALL_STATUS.DEGRADED, entries: [], text: null, evicted: 0,
            ledger: { path: null, status: 'unresolved', scoped: false, degraded: true },
            reason: `账本路径不可解析（${resolved.reason}）⇒ **本结果不代表该内容不存在**`,
            coreStatus: { wired: WIRING.recall, recallWired: WIRING.recall },
            version: VERSION
          };
        }
        const led = ledgerForUse(resolved.path);
        // ★ 三态如实下传：ABSENT ⇒ 空账本 ⇒ 核心判 DEGRADED（**绝不冒充 MISS**，见 lib/ledger.js:130-136）
        const r = recall(led.ledger, target);
        return {
          ok: true, implemented: true, target,
          status: r.status,
          entries: r.entries,
          text: r.status === RECALL_STATUS.HIT ? r.text : null,
          evicted: r.evicted,
          ledger: { path: resolved.path, status: led.status, scoped: resolved.scoped, degraded: led.degraded === true },
          reason: led.degraded === true ? `账本不可用（${led.reason}）⇒ ${r.reason}` : r.reason,
          // ★ 模块声明（contract-check ② 按值核存在性）：③ 召回依赖账本核与落盘层，两处都声明
          coreStatus: {
            module: 'lib/ledger.js',
            ioCore: { module: 'lib/ledger-io.js' },
            // ★ 逐件接线状态的**同源声明**（与 csx_status.wiring / csx_checkpoint.coreStatus 同出 WIRING）
            wired: WIRING.recall,
            writeWired: WIRING.write, persistWired: WIRING.persist, recallWired: WIRING.recall
          },
          version: VERSION
        };
      }
    })
  ];

  for (const t of tools) ctx.effect(() => ctx.tools.register(t));

  // ---- K2 守卫：**测量 + 记录**，默认关闭；只有显式 enableGuard=true 才注册 ----
  // 签名照官方：ctx.on("agent/pre-step", async ({ agent, signal }, next) => …)
  //   dsh-compaction-basic/lib/index.js:780 —— K1 里的 (_payload, next) 是猜的，已按真实形状改正。
  // 铁律：**无论发生什么都要 next()**（守卫自身缺陷绝不能影响会话；官方同样在 catch 后 next()）。
  if (config.enableGuard === true) {
    ctx.effect(() => ctx.on('agent/pre-step', async (payload, next) => {
      try {
        // ★ K3：并发护栏接**真判据**（此前写死 false = 假判据）。读 session.events，
        //   复刻官方 assertNoActiveCompaction（dsh-compaction-basic/lib/index.js:504-516）。
        const cguard = readCompactionGuard(payload);
        const reading = await observePressure(ctx, payload, config, { hasOpenCompaction: cguard.busy });
        guardStats.steps += 1;
        guardStats.lastAt = new Date().toISOString();
        guardStats.lastConcurrency = { ok: cguard.ok, busy: cguard.busy, staleBySeed: cguard.staleBySeed, reason: cguard.reason };
        if (cguard.busy) guardStats.concurrencyBusy += 1;
        else if (cguard.staleBySeed) guardStats.concurrencyStaleIgnored += 1;
        else guardStats.concurrencyFree += 1;
        guardStats.last = reading.ok === true
          ? { action: reading.decision.action, measuredTokens: reading.measuredTokens, threshold: reading.decision.threshold, pressure: reading.decision.pressure }
          : { action: 'skip', reason: reading.reason };
        if (reading.ok === true && reading.decision.action === DECISION.COMPRESS) guardStats.compress += 1;
        else if (reading.ok === true) guardStats.belowThreshold += 1;
        else {
          guardStats.skipped += 1;
          guardStats.skipReasons[reading.reason] = (guardStats.skipReasons[reading.reason] ?? 0) + 1;
        }

        // ---- ★★ K6 ① 写入接线：只在**真被请求压缩**时才走写入路径 ----
        //  为什么加这个前置条件：runWritePath 内部要再 measure(session) 一次（O(表面)）；
        //  若每步都跑，就是给正常步白加一次全表面计量。⇒ 只在达阈值那一步付这个代价。
        //  ★ 失败绝不外溢：runWritePath 自身不抛，外面还有一层 try/catch，且无论怎样都 next()。
        if (reading.ok === true && reading.decision.action === DECISION.COMPRESS) {
          const w = accountWrite(runWritePath({ ctx, session: payload?.agent?.session, config, decision: reading.decision, busy: cguard.busy, commit: true, payload }),
            { via: 'auto', sessionId: payload?.agent?.session?.id === undefined ? null : String(payload.agent.session.id).slice(0, 24) });
          log('write-path', { action: w.action, wrote: w.wrote, seq: w.appendedSeq, ledgerOk: w.persist === null || w.persist === undefined ? null : w.persist.ok, reason: w.reason });
          ctx.logger.info(`context-survival ${describeWire(w)}`);
        }
        // 只写日志。**此处不做任何会话变更** —— K2 的"不做"正是被测对象；K3 的表面替换接线仍未接。
        ctx.logger.info(`context-survival ${formatReading(reading)} ${describeGuardResult(cguard)}`);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        ctx.logger.warn(`context-survival: 压力测量异常（${msg}）；本轮零修改、原样放行`);
      }
      return typeof next === 'function' ? next() : undefined;
    }));
  }
}
