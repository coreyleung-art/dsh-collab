#!/usr/bin/env node
// dsh-plugin-self-report-gate · 自述可证性门（R-SR）：SR1 现场重测 / SR2 阳性对照 / SR3 撤回传播 / SR4 写盘自证 / SR5 环境指纹 / SR6 修复路径覆盖
// R006 ⑨ CLI 治理：严格参数（未知旗标 exit 2）/ 退出码 0 成功·1 失败·2 用法 / --dry-run 零变更 / --json / --help
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { lean4Check } from "./lib/gate.js"
import { runSelfCheck } from "./lib/selfcheck.js"
import { describeCapabilities, runStatus } from "./lib/core.js"

const HERE = dirname(fileURLToPath(import.meta.url))
export const FLAGS = Object.freeze(["--help", "-h", "--json", "--dry-run", "--selfcheck", "--lean4-check", "--tool-version"])

export function usage() {
  return [
    "dsh-plugin-self-report-gate — 自述可证性门（R-SR）：SR1 现场重测 / SR2 阳性对照 / SR3 撤回传播 / SR4 写盘自证 / SR5 环境指纹 / SR6 修复路径覆盖",
    "",
    "用法：self-report-gate [旗标]",
    "",
    "  --selfcheck      能力清单 / 不该发生路径 / 依赖完整性 + 真挂载冒烟（R006 ②）",
    "  --lean4-check    约束门六项自证 A–F（R006 ⑩）",
    "  --tool-version   打印版本（唯一来源：package.json）",
    "  --dry-run        零变更演练",
    "  --json           机器可读输出",
    "  --help           本帮助",
    "",
    "退出码：0 成功 · 1 失败/门失效 · 2 用法或 IO 错误",
  ].join("\n") + "\n"
}

export function toolVersion() {
  // ⑥ 版本单一来源：只从 package.json 读，绝不第二处硬编码
  return JSON.parse(readFileSync(join(HERE, "package.json"), "utf8")).version
}

export async function main(argv) {
  const unknown = argv.filter((a) => a.indexOf("-") === 0 && FLAGS.indexOf(a) === -1)
  if (unknown.length > 0) { process.stderr.write("用法错误：未知旗标 " + unknown.join(" ") + "\n"); return 2 }
  const asJson = argv.indexOf("--json") !== -1
  const emit = (value) => process.stdout.write(JSON.stringify(value, null, 2) + "\n")
  if (argv.length === 0 || argv.indexOf("--help") !== -1 || argv.indexOf("-h") !== -1) { process.stdout.write(usage()); return 0 }
  if (argv.indexOf("--tool-version") !== -1) { process.stdout.write(toolVersion() + "\n"); return 0 }
  if (argv.indexOf("--selfcheck") !== -1) {
    const result = await runSelfCheck("self-report-gate", { sourceFiles: ["cli.js", "lib/core.js"], requiredSymbols: ["runStatus"] })
    emit(result)
    return result.ok ? 0 : 1
  }
  if (argv.indexOf("--lean4-check") !== -1) {
    const result = lean4Check()
    emit(result)
    return result.ok ? 0 : 1
  }
  if (argv.indexOf("--dry-run") !== -1) { emit(await runStatus({ dryRun: true })); return 0 }
  const result = await runStatus({ dryRun: false })
  if (!asJson) emit({ text: JSON.stringify(result, null, 2), capabilities: describeCapabilities() })
  else emit(result)
  return result.ok ? 0 : 1
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await main(process.argv.slice(2)))
}
