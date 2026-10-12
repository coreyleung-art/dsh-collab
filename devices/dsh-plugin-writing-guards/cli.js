#!/usr/bin/env node
// dsh-plugin-writing-guards · 写作过程守卫
// R006 ⑨ CLI 治理：严格参数（未知旗标 exit 2）/ 退出码 0 成功·1 失败·2 用法 / --dry-run 零变更 / --json / --help
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { lean4Check } from "./lib/gate.js"
import { runSelfCheck } from "./lib/selfcheck.js"
import { describeCapabilities, runStatus, runGuard, WHITELIST, logPath } from "./lib/core.js"

const HERE = dirname(fileURLToPath(import.meta.url))
export const FLAGS = Object.freeze([
  "--help", "-h", "--json", "--dry-run",
  "--selfcheck", "--lean4-check", "--tool-version",
  // ★ 白名单子命令入口（★ ⑩-1：不在 WHITELIST 里的 key 结构上无法表达）
  "--list", "--run",
])

export function usage() {
  return [
    "dsh-plugin-writing-guards — 写作过程守卫",
    "  非原子写扫描 · 数字口径申报 · 更正账生成 · 照抄旧读数疑似检测 · 既有 lint 清单",
    "",
    "用法：writing-guards [旗标]        # 治理面",
    "      writing-guards --list        # 列出白名单子命令",
    "      writing-guards --run <key> [args...]   # 执行白名单子命令",
    "",
    "旗标：",
    "  --selfcheck      能力清单 / 不该发生路径 / 依赖完整性 + 真挂载冒烟（R006 ②）",
    "  --lean4-check    约束门六项自证 A–F（R006 ⑩）",
    "  --tool-version   打印版本（唯一来源：package.json）",
    "  --dry-run        零变更演练（★ 与 --run 合用则只报将执行什么）",
    "  --json           机器可读输出",
    "  --list           列出白名单子命令",
    "  --run <key>      执行白名单子命令（★ 不在表内的 key ⇒ exit 2）",
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
  const dryRun = argv.indexOf("--dry-run") !== -1
  const emit = (value) => process.stdout.write(JSON.stringify(value, null, 2) + "\n")

  if (argv.length === 0 || argv.indexOf("--help") !== -1 || argv.indexOf("-h") !== -1) { process.stdout.write(usage()); return 0 }
  if (argv.indexOf("--tool-version") !== -1) { process.stdout.write(toolVersion() + "\n"); return 0 }

  if (argv.indexOf("--selfcheck") !== -1) {
    const result = await runSelfCheck("writing-guards", {
      sourceFiles: ["cli.js", "lib/core.js", "lib/gate.js", "lib/selfcheck.js"],
      requiredSymbols: ["runStatus", "runGuard", "WHITELIST"],
    })
    emit(result)
    return result.ok ? 0 : 1
  }
  if (argv.indexOf("--lean4-check") !== -1) {
    const result = lean4Check()
    emit(result)
    return result.ok ? 0 : 1
  }

  if (argv.indexOf("--list") !== -1) {
    const keys = Object.keys(WHITELIST)
    if (asJson) emit({ ok: true, whitelist: keys, logPath: logPath() })
    else {
      process.stdout.write("白名单子命令（★ 冻结常量）：\n")
      for (const k of keys) process.stdout.write("  " + k.padEnd(22) + " → ~/dsh-collab/" + WHITELIST[k].script + "\n")
    }
    return 0
  }

  // ★ ⑩-1：子命令只能从 WHITELIST 取；不在表内 ⇒ runGuard 直接拒（exit 2）
  const ri = argv.indexOf("--run")
  if (ri !== -1) {
    const key = argv[ri + 1]
    if (!key) { process.stderr.write("用法错误：--run 需要一个子命令名（见 --list）\n"); return 2 }
    // ★ 余下非旗标参数原样透传给被调工具
    const passthru = argv.slice(ri + 2).filter((a) => a.indexOf("--") !== 0)
    const r = runGuard(key, passthru, { dryRun })
    if (asJson) emit(r)
    else {
      if (r.dryRun) {
        // ★ ⑨ dry-run 必须【出声】：报将执行什么，否则读者无法确认「零变更」是否真做到
        process.stdout.write("[dry-run] 将执行：" + (r.wouldRun || []).join(" ") + "\n")
        process.stdout.write("[dry-run] 未做任何变更\n")
      }
      if (r.stdout) process.stdout.write(r.stdout)
      if (r.stderr) process.stderr.write(r.stderr)
      if (r.error) process.stderr.write(r.error + "\n")
    }
    return r.code
  }

  if (dryRun) { emit(await runStatus({ dryRun: true })); return 0 }
  const result = await runStatus({ dryRun: false })
  if (!asJson) emit({ text: JSON.stringify(result, null, 2), capabilities: describeCapabilities() })
  else emit(result)
  return result.ok ? 0 : 1
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await main(process.argv.slice(2)))
}
