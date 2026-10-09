/**
 * index.js — dsh 插件形态（宿主平面 / host plane）：注册 csx_* 工具 + 空守卫
 * =============================================================================
 * ★ K2：**只测量的守卫**。本文件此刻做四件事，**没有一件会改变会话状态**：
 *     1) apply() 最前跑 R014 自查（失败不阻塞挂载）；
 *     2) 注册三个工具（csx_status 只读可用并回报守卫读数；csx_checkpoint / csx_recall 诚实报"未实现"）；
 *     3) 若 config.enableGuard === true，注册 agent/pre-step 监听器——它**读**压力（tokenMeter 测量 +
 *        适配器 contextWindow + 预算阈值判定），写一行日志，**然后原样放行**；
 *     4) 无论 3) 是否开启，注册过程与运行期都可能零动作。
 *   检查点产出（K3）、表面替换（K3）、召回（K4）会**在此之上**加，仍不接管 ctx.compaction。
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
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { PLUGIN_SLUG, PLUGIN_NAME, VERSION } from './meta.js';
import { RECALL_KINDS, resolveRecallTarget, GateError, GATE_META } from './gate.js';
import { observePressure, formatReading } from './guard.js';
import { BUDGET_DEFAULTS } from './budget.js';

/** K2 阶段标识（csx_status / cli --status 共用一处字符串，避免两处漂）。 */
const STAGE = 'K2-measure-only';

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
        stage: { type: 'string' },
        implemented: { type: 'boolean' },
        invariants: { type: 'array', items: obj({ properties: { id: { type: 'string' }, claim: { type: 'string' } } }) },
        gate: obj(),
        guard: obj(),
        note: { type: 'string' }
      }
    })
  };
}

function makeCheckpointOutput() {
  return {
    schema: obj({
      properties: {
        ok: { type: 'boolean' },
        implemented: { type: 'boolean' },
        reason: { type: 'string' },
        version: { type: 'string' }
      }
    })
  };
}

function makeRecallOutput() {
  return {
    schema: obj({
      properties: {
        ok: { type: 'boolean' },
        implemented: { type: 'boolean' },
        target: obj(),
        error: obj(),
        reason: { type: 'string' },
        version: { type: 'string' }
      }
    })
  };
}

export function apply(ctx, config = {}) {
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
    skipReasons: {}, last: null, lastAt: null
  };

  const tools = [
    defineTool({
      name: 'csx_status',
      description:
        '上下文存活守卫状态（只读）：本插件版本、当前阶段、六条不变量、结构门元信息，' +
        '以及 K2 守卫的累计读数（步数 / 触发 / 未达阈 / 跳过原因）。**不读会话、不改状态**。',
      parameters: {},
      output: makeStatusOutput(),
      async execute() {
        return {
          ok: true,
          plugin: PLUGIN_NAME,
          version: VERSION,
          stage: STAGE,
          implemented: false,
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
            mode: 'measure-only',
            budgetDefaults: { ...BUDGET_DEFAULTS },
            note: 'K2：只测量、只记录；不做检查点、不替换表面（检查点 K3、召回 K4）。'
          },
          note: `阶段 ${STAGE}：守卫只测量不修改；挂载（K6）是不可逆动作，由用户在独立试验会话内执行。`
        };
      }
    }),
    defineTool({
      name: 'csx_checkpoint',
      description:
        '手动插入一个非摘要检查点（等价于自动触发的立即版）。**尚未实现**（K3 交付），' +
        '调用会如实返回 implemented=false，不会做任何变更。',
      parameters: {},
      output: makeCheckpointOutput(),
      async execute() {
        return { ok: false, implemented: false, reason: 'K1 骨架：检查点产出在 K3 实现。', version: VERSION };
      }
    }),
    defineTool({
      name: 'csx_recall',
      description:
        '按会话内指针逐字取回被省略的内容。目标种类在 schema 层枚举（seq / range / checkpoint），' +
        'id 只能是有界数字或数字区间——**不接受路径、命令或 URL**。取回尚未实现（K4 交付）。',
      parameters: {
        kind: { type: 'string', required: true, enum: [...RECALL_KINDS], description: '目标种类（枚举，无法传入其它值）' },
        id: { type: 'string', required: true, description: 'seq/checkpoint 为 1-7 位数字；range 为 <数字>-<数字>' }
      },
      output: makeRecallOutput(),
      async execute(args) {
        let target;
        try {
          target = resolveRecallTarget({ kind: args.kind, id: args.id });
        } catch (e) {
          if (e instanceof GateError) {
            return { ok: false, implemented: false, error: { code: e.code, message: e.message }, version: VERSION };
          }
          throw e;
        }
        return { ok: false, implemented: false, target, reason: 'K1 骨架：召回取回在 K4 实现（当前仅完成 schema 层结构约束）。', version: VERSION };
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
        const reading = await observePressure(ctx, payload, config, { hasOpenCompaction: false });
        guardStats.steps += 1;
        guardStats.lastAt = new Date().toISOString();
        guardStats.last = reading.ok === true
          ? { action: reading.decision.action, measuredTokens: reading.measuredTokens, threshold: reading.decision.threshold, pressure: reading.decision.pressure }
          : { action: 'skip', reason: reading.reason };
        if (reading.ok === true && reading.decision.action === 'compress') guardStats.compress += 1;
        else if (reading.ok === true) guardStats.belowThreshold += 1;
        else {
          guardStats.skipped += 1;
          guardStats.skipReasons[reading.reason] = (guardStats.skipReasons[reading.reason] ?? 0) + 1;
        }
        // 只写日志。**此处不做任何会话变更** —— K2 的"不做"正是被测对象。
        ctx.logger.info(`context-survival ${formatReading(reading)}`);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        ctx.logger.warn(`context-survival: 压力测量异常（${msg}）；本轮零修改、原样放行`);
      }
      return typeof next === 'function' ? next() : undefined;
    }));
  }
}
