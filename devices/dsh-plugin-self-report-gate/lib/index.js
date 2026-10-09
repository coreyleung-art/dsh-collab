// dsh-plugin-self-report-gate · 自述可证性门（R-SR）
// R006 ① dsh 插件形态：export apply(ctx, config) + inject:["tools"] + 工具注册归属本插件 Fiber
//
// ★ 本插件的定位是【宿主侧入口】，不是判据的第二个实现：
//   SR1–SR6 的唯一实现在 Python 门 `~/dsh-collab/scripts/self-report-gate.py`（见 lib/core.js 顶部说明）。
import { defineTool } from "@deepseek-ai/dsh-tools"
import { runSelfCheck } from "./selfcheck.js"
import { GATE_ACTIONS, assertAllowedAction } from "./gate.js"
import { gateCheck, gateSelftest, gateVersion, runStatus } from "./core.js"

export const name = "self-report-gate"
export const inject = ["tools"]

const TOOL_NAMES = ["self_report_check"]

export function apply(ctx, config = {}) {
  // R006 ② 自查门：apply 最开始调用（缺 peer / 缺符号在启动期即暴露）
  // ★ skipSmoke：apply 期**不得**跑挂载冒烟——冒烟会 import 本入口再调 apply，
  //   瞬间形成无界异步自递归（真宿主里会把事件循环饿死；CLI 因 process.exit 恰好掩盖它）。
  runSelfCheck("self-report-gate", { sourceFiles: ["lib/index.js"], requiredSymbols: ["defineTool", "runSelfCheck"], config, skipSmoke: true })
  for (const toolName of TOOL_NAMES) {
    ctx.effect(
      () =>
        ctx.tools.register(
          defineTool({
            name: toolName,
            description:
              "自述可证性门（R-SR）的宿主侧入口：status=探针环境 / version=现场读门版本 / selftest=转调门自测 / check=对受控根内的 R046 声明体转调门检查。全程只读，判据唯一实现在 Python 门内。",
            parameters: {
              action: {
                type: "string",
                required: true,
                enum: GATE_ACTIONS,
                description: "动作；枚举即约束——不在枚举内的值在解析期被拒（Schema 门）",
              },
              claim_path: {
                type: "string",
                required: false,
                description: "仅 action=check 必填：受控根（dsh-collab/audits·research·data）内的 R046 声明体 JSON 路径",
              },
            },
            output: {
              // 注意：object 节点必须显式写 additionalProperties，否则 dsh-tools 抛 UNSUPPORTED_SCHEMA（挂不上）
              schema: { type: "json" },
              render: (_args, value) => [{ type: "text", text: JSON.stringify(value, null, 2) }],
            },
            async execute(args) {
              assertAllowedAction(args.action) // 冻结枚举（Schema 门之外再加一道运行期断言）
              switch (args.action) {
                case "status":
                  return await runStatus({ dryRun: false })
                case "version":
                  return await gateVersion()
                case "selftest":
                  return await gateSelftest()
                case "check":
                  return await gateCheck(args.claim_path)
                default:
                  // 结构上不可达：action 已过冻结枚举断言
                  throw new Error("UNREACHABLE_ACTION: " + String(args.action))
              }
            },
          }),
        ),
      "self-report-gate: tool " + toolName,
    )
  }
}
