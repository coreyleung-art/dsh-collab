// dsh-plugin-item-validity-review-check · 条目有效性审查
// R006 ① dsh 插件形态：export apply(ctx, config) + inject:["tools"] + 工具注册归属本插件 Fiber
// ★ schema 即门（R006 ⑩）：source 是冻结枚举 ["inbox"]；**没有任何 path / indexPath 入参** ——
//   「把索引写到别处」「扫别的目录」在语法上不可表达，不是被拒绝，而是无处可传。
import { defineTool } from "@deepseek-ai/dsh-tools"
import { runSelfCheck } from "./selfcheck.js"
import { ACTIONS, SOURCE_ENUM, assertNoIndexPathInput, assertSource, assertState, assertToolActions } from "./gate.js"
import { batchScan, checkItem, explainItem, indexWrite } from "./core.js"

export const name = "item-validity-review-check"
export const inject = ["tools"]

/** 四个工具（R006 命名门已过，名字不得改）。 */
export const TOOL_NAMES = ["item_validity_check", "item_validity_batch", "item_validity_explain", "item_validity_index_write"]

/** 工具 → 冻结动作名（apply 期用 assertToolActions 校验，门是承重的）。 */
const TOOL_ACTIONS = TOOL_NAMES.map((n, i) => [n, ACTIONS[i]])

/**
 * ★ 嵌套 object 必须显式写 additionalProperties，否则 defineTool 抛 UNSUPPORTED_SCHEMA → apply() 崩
 *   → 插件挂不上（2026-09-13 由「真挂载冒烟」抓到，此前九项全绿却整包不可挂载）。
 */
function makeOutput() {
  return {
    schema: {
      type: "object",
      additionalProperties: true,
      properties: {
        ok: { type: "boolean" },
        tool: { type: "string" },
        source: { type: "string" },
        key: { type: "string" },
        found: { type: "boolean" },
        state: { type: "string" },
        shape: { type: "string" },
        why: { type: "string" },
        channel: { type: "string" },
        missing: { type: "string" },
        howToFix: { type: "string" },
        total: { type: "integer" },
        maxAgeDays: { type: "number" },
        returned: { type: "integer" },
        tally: { type: "object", additionalProperties: true },
        shapeTally: { type: "object", additionalProperties: true },
        strictTally: { type: "object", additionalProperties: true },
        conditions: { type: "object", additionalProperties: true },
        dependencyCounts: { type: "object", additionalProperties: true },
        rows: { type: "array", items: { type: "json" } },
        wrote: { type: "boolean" },
        dryRun: { type: "boolean" },
        path: { type: "string" },
        protocol: { type: "array", items: { type: "string" } },
        blindSpot: { type: "string" },
        elapsed_ms: { type: "integer" },
      },
    },
  }
}

/** 参数声明：**没有 path / indexPath / dir / file 这类键**（结构约束）。 */
const PARAMS_COMMON = {
  source: {
    type: "string",
    enum: [...SOURCE_ENUM],
    description: "数据源：冻结枚举，P0 只做 inbox。**不接受任意路径** —— 传 /etc、相对路径、~、通配一律被门拒绝。",
  },
  maxAgeDays: {
    type: "number",
    description: "时效窗天数（默认 7）；**窗值会打印在输出与理由里**。",
  },
}

export function apply(ctx, config = {}) {
  // R006 ② 自查门：apply 最开始调用（缺 peer / 缺符号在启动期即暴露）
  // ★ skipSmoke：apply 期**不得**跑挂载冒烟——冒烟会 import 本入口再调 apply，
  //   瞬间形成无界异步自递归（真宿主里会把事件循环饿死；CLI 因 process.exit 恰好掩盖它）。
  runSelfCheck("item-validity-review-check", { sourceFiles: ["lib/index.js"], requiredSymbols: ["defineTool", "runSelfCheck"], config, skipSmoke: true })
  // ⑩ 门是承重的：四个工具声明的动作必须都在冻结枚举内，否则插件不挂
  assertToolActions(TOOL_ACTIONS)

  const tools = [
    defineTool({
      name: "item_validity_check",
      description:
        "条目有效性审查（单条）：对一张卡 / 一条待办 / 一个条目回答「它现在还有效吗」。先分形态（action/record/feed/ack/unknown），再给五态" +
        "（closed/stale/open/unknown/n/a），并附每态所依赖的条件量与盲区声明。只读，不产生任何变更。",
      parameters: {
        source: PARAMS_COMMON.source,
        key: { type: "string", required: true, description: "inbox 条目标识：文件名 / 去 .json 的名 / 条目自身 key 字段" },
        maxAgeDays: PARAMS_COMMON.maxAgeDays,
      },
      output: makeOutput(),
      async execute(args) {
        assertNoIndexPathInput(args)
        assertSource(args.source === undefined ? SOURCE_ENUM[0] : args.source)
        return checkItem(args)
      },
    }),
    defineTool({
      name: "item_validity_batch",
      description:
        "条目有效性审查（批量）：扫描 inbox 全部条目，输出五态计数 + 形态计数 + 逐条判定行（含 why/channel）。只读。" +
        "附严格口径计数（strictTally：一切 A/B 不命中皆 unknown）。",
      parameters: {
        source: PARAMS_COMMON.source,
        maxAgeDays: PARAMS_COMMON.maxAgeDays,
        state: {
          type: "string",
          enum: ["closed", "stale", "open", "unknown", "n/a"],
          description: "只看某一态（省略=全部）。不在枚举内的值在解析期被拒。",
        },
        limit: { type: "integer", description: "最多返回多少行（默认全部）" },
      },
      output: makeOutput(),
      async execute(args) {
        assertNoIndexPathInput(args)
        assertSource(args.source === undefined ? SOURCE_ENUM[0] : args.source)
        if (args.state !== undefined) assertState(args.state)
        return batchScan(args)
      },
    }),
    defineTool({
      name: "item_validity_explain",
      description:
        "条目有效性审查（解释）：给出这一条为什么落在该态的**完整判据链** —— 形态依据、状态类字段命中、三通道各自的适用/求值/命中、" +
        "时效载体与窗值、缺失字段与怎么补，以及依赖条件量。可传 sample（内存样条）离线推演。只读。",
      parameters: {
        source: PARAMS_COMMON.source,
        key: { type: "string", description: "inbox 条目标识（与 sample 二选一）" },
        sample: { type: "json", description: "内存样条：直接解释一份 JSON（不读盘、不落盘）" },
        maxAgeDays: PARAMS_COMMON.maxAgeDays,
      },
      output: makeOutput(),
      async execute(args) {
        assertNoIndexPathInput(args)
        assertSource(args.source === undefined ? SOURCE_ENUM[0] : args.source)
        return explainItem(args)
      },
    }),
    defineTool({
      name: "item_validity_index_write",
      description:
        "写条目有效性索引（**本插件唯一的写操作**）：把 closed + stale 落成一份索引，供以后先查。目标路径写死为模块常量 " +
        "（不是入参 —— 「写到别处」结构上不可表达）。dryRun 默认 true，必须 confirm:true 才真写；写临时文件再原子改名，**写后回读断言**。" +
        "绝不写任何被审条目。",
      parameters: {
        source: PARAMS_COMMON.source,
        maxAgeDays: PARAMS_COMMON.maxAgeDays,
        dryRun: { type: "boolean", description: "默认 true：只出计划，零变更" },
        confirm: { type: "boolean", description: "必须显式 true 才真写（与 dryRun:false 同时满足）" },
      },
      output: makeOutput(),
      async execute(args) {
        assertNoIndexPathInput(args)
        assertSource(args.source === undefined ? SOURCE_ENUM[0] : args.source)
        return indexWrite(args)
      },
    }),
  ]

  for (const t of tools) {
    ctx.effect(
      () => ctx.tools.register(t),
      "item-validity-review-check: tool " + t.name,
    )
  }
}
