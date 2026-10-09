// dsh-plugin-self-report-gate · 业务内核
//
// ★ 单一来源设计（刻意不重实现）：
//   R-SR 门（SR1 现场重测 / SR2 阳性对照 / SR3 撤回传播 / SR4 写盘自证 / SR5 环境指纹 / SR6 修复路径覆盖）
//   的唯一实现在 Python 门 `~/dsh-collab/scripts/self-report-gate.py`。
//   本插件【只调用、不重写】—— 若在此用 JS 再实现一遍，就会出现两套逻辑各自漂移，
//   而这正是本门要检出的缺陷形状（同一事实两个来源）。
//   ⇒ 因此：JS 侧只能做 ① 定位 ② 校验 ③ 转调 ④ 原样回报；任何 SRx 判据都不在这里。
//
// ★ 写盘边界（R006 ⑦）：本插件全场只读，**唯一的写动作是追加统一日志**
//   （路径由 package.json 的 r006.unified_log 声明）。日志写失败必须如实体现，不得静默。
//
// ★ 安全：execFile + 参数数组，绝不经过 shell（无 eval / 无 execSync / 无 shell:true）。
//   命令与路径先过 lib/gate.js 的白名单断言。
import { execFile } from "node:child_process"
import { appendFileSync, existsSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { promisify } from "node:util"
import { ALLOWED_BIN_DIRS, assertCommandAllowed, assertPathAllowed } from "./gate.js"

const pExecFile = promisify(execFile)

export const GATE_SCRIPT = join(process.env.HOME || "", "dsh-collab", "scripts", "self-report-gate.py")
export const LOG_PATH = join(process.env.HOME || "", "dsh-collab", "logs", "dsh-plugin-self-report-gate.log")

// R006 ⑦ 统一日志：成功与失败分支都写；写失败返回 false（不抛，不静默）
export function logLine(kind, detail) {
  try {
    mkdirSync(dirname(LOG_PATH), { recursive: true })
    appendFileSync(LOG_PATH, JSON.stringify({ ts: new Date().toISOString(), tool: "self-report-gate", kind, detail }) + "\n", "utf8")
    return true
  } catch (e) {
    return false
  }
}

// ★ ③ CLD 自适应：本机 shell 的 PATH 常只有 /usr/bin:/bin:/usr/sbin:/sbin
//   （实测：`node` 不在其中，只有 /opt/homebrew/bin/node）⇒ 必须按候选列表探测绝对路径，
//   找不到就如实报 unavailable，绝不静默降级成「假装通过」。
export const PYTHON_CANDIDATES = ["/usr/bin/python3", "/opt/homebrew/bin/python3", "/usr/local/bin/python3"]

export function resolvePython() {
  for (const p of PYTHON_CANDIDATES) {
    if (existsSync(p)) return p
  }
  return null
}

export function probe() {
  const python = resolvePython()
  const script = existsSync(GATE_SCRIPT) ? GATE_SCRIPT : null
  return {
    python,
    script,
    available: Boolean(python && script),
    env: { PATH: process.env.PATH || "", node: process.execPath },
    candidates: { python: PYTHON_CANDIDATES, script: [GATE_SCRIPT], binDirs: ALLOWED_BIN_DIRS },
  }
}

async function runGate(action, args, timeoutMs = 30000) {
  const p = probe()
  if (!p.available) {
    const logOk = logLine("unavailable", { action, reason: !p.python ? "未找到 python3" : "未找到门脚本 " + GATE_SCRIPT, python: p.python, script: p.script })
    return { ok: false, unavailable: true, reason: !p.python ? "未找到 python3（已试候选列表）" : "未找到门脚本 " + GATE_SCRIPT, probe: p, logOk }
  }
  assertCommandAllowed(p.python)
  try {
    const { stdout, stderr } = await pExecFile(p.python, [p.script, ...args], { timeout: timeoutMs, maxBuffer: 8 * 1024 * 1024 })
    const logOk = logLine("gate-run", { action, args, python: p.python, script: p.script, rc: 0, stdoutBytes: String(stdout).length })
    return { ok: true, stdout: String(stdout), stderr: String(stderr), probe: p, logOk }
  } catch (e) {
    const rc = typeof e.code === "number" ? e.code : null
    const logOk = logLine("gate-run", { action, args, rc, error: String((e && e.message) || e), stdout: String((e && e.stdout) || "").slice(0, 2000), stderr: String((e && e.stderr) || "").slice(0, 2000) })
    return {
      ok: true,
      stdout: String((e && e.stdout) || ""),
      stderr: String((e && e.stderr) || ""),
      exitCode: rc,
      nonZeroExit: rc !== null && rc !== 0,
      probe: p,
      logOk,
    }
  }
}

// ★ 版本：现场实测，绝不硬编码（会变的值不进源码）
export async function gateVersion() {
  const r = await runGate("version", ["--version"])
  if (!r.ok) return r
  try {
    const j = JSON.parse(r.stdout)
    return { ok: true, gateVersion: j.version, rule: j.rule, assertions: j.assertions, raw: j, probe: r.probe, logOk: r.logOk }
  } catch (e) {
    return { ok: false, reason: "门版本输出不是 JSON", stdout: r.stdout, stderr: r.stderr }
  }
}

export async function gateSelftest() {
  const r = await runGate("selftest", ["--selftest"], 120000)
  if (!r.ok) return r
  return { ok: true, stdout: r.stdout, stderr: r.stderr, exitCode: r.exitCode, probe: r.probe, logOk: r.logOk }
}

// ★ 检查一个 R046 声明体文件（只读；路径先过受控根白名单）
export async function gateCheck(claimPath) {
  if (claimPath == null || String(claimPath).trim() === "") {
    logLine("check-denied", { reason: "缺少 claim_path" })
    return { ok: false, reason: "缺少 claim_path（check 动作必填）" }
  }
  try {
    assertPathAllowed(claimPath)
  } catch (e) {
    const logOk = logLine("check-denied", { claimPath: String(claimPath), code: e.code, reason: String(e.message) })
    return { ok: false, denied: true, code: e.code, reason: String(e.message), logOk }
  }
  const r = await runGate("check", ["--check", String(claimPath)], 60000)
  if (!r.ok) return r
  // 门的退出码语义：0=过门 / 1=拒 / 2=用法错 —— 原样回报，不替门改口径
  return { ok: true, claimPath: String(claimPath), stdout: r.stdout, stderr: r.stderr, exitCode: r.exitCode, nonZeroExit: r.nonZeroExit === true, probe: r.probe, logOk: r.logOk }
}

export function describeCapabilities() {
  return {
    tool: "self-report-gate",
    purpose: "自述可证性门（R-SR）的宿主侧入口：把声明体检查、门自测、门版本与探针环境暴露成一个工具调用",
    can: [
      "action=status：探测 python3 与门脚本是否在位，回报 PATH / node / 候选路径（只读）",
      "action=version：现场读取门版本（不硬编码）",
      "action=selftest：转调门的自测矩阵并原样回报",
      "action=check：对受控根内的声明体 JSON 转调门检查，原样回报 stdout 与退出码",
    ],
    cannot: [
      "不该发生：在 JS 侧重实现任何 SRx 判据（唯一实现在 Python 门；重实现会制造双来源漂移）",
      "不该发生：除声明日志外的任何写盘（不改被审对象、不删交付物）",
      "不该发生：经过 shell 执行命令（只用 execFile + 参数数组）",
      "不该发生：读取受控根之外的声明体路径（assertPathAllowed 前置）",
      "不该发生：python3 或门脚本缺失时假装通过（如实回报 unavailable）",
    ],
    log: LOG_PATH,
  }
}

export async function runStatus(options = {}) {
  const dryRun = options.dryRun === true
  const p = probe()
  const v = p.available && !dryRun ? await gateVersion() : null
  return {
    ok: p.available,
    tool: "self-report-gate",
    dryRun,
    checkedAt: new Date().toISOString(),
    gate: { available: p.available, python: p.python, script: p.script, version: v && v.ok ? v.gateVersion : null, assertions: v && v.ok ? v.assertions : null },
    env: p.env,
    log: LOG_PATH,
    note: dryRun
      ? "dry-run：未执行门（零变更，零子进程）"
      : p.available
        ? "门在位；SR1–SR6 的唯一实现在 Python 门内，本插件只转调"
        : "门不可用：如实回报，不降级、不假装通过",
  }
}
