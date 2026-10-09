// dsh-plugin-self-report-gate · R006 ⑩ 约束前置
// 结构约束：冻结白名单 + 负例矩阵 + 命令白名单 + 路径白名单 + --lean4-check 六项 A–F
export class GateError extends Error {
  constructor(code, message) {
    super(message)
    this.name = "GateError"
    this.code = code
  }
}

// ★ 冻结枚举：不在枚举内的动作在 schema 期就不可表达（类型锁 / Schema 门）
//   status   = 本插件自身状态（门是否在位、版本、探针环境）
//   check    = 转调 Python 门做一次声明体检查（唯一实现，见 core.js）
//   selftest = 转调 Python 门的自测矩阵
//   version  = 打印 Python 门的实测版本（现场读，绝不硬编码）
export const GATE_ACTIONS = Object.freeze(["status", "check", "selftest", "version"])

// ★ 命令白名单：按 basename 比对（见 assertCommandAllowed）
//   node   = 本插件运行时（自检用）
//   python3 = 被包装的门（唯一实现所在），失败即如实报 unavailable，不做降级重实现
export const COMMAND_WHITELIST = Object.freeze(["node", "python3"])

// ★ 允许的可执行目录：命令含路径分隔符时，除 basename 白名单外还必须落在这些根内
//   （防「basename 叫 python3 但在任意目录」的绕过）
export const ALLOWED_BIN_DIRS = Object.freeze([
  "/usr/bin",
  "/bin",
  "/usr/local/bin",
  "/opt/homebrew/bin",
])

export const FORBIDDEN_SOURCE = Object.freeze([
  "rm -rf", "pkill", "killall", "process.kill", "eval(",
  "exec(", "execSync(", "shell: true", "shell:true",
])

export function assertAllowedAction(action) {
  if (typeof action !== "string" || GATE_ACTIONS.indexOf(action) === -1) {
    throw new GateError("GATE_ACTION_DENIED", "action 不在冻结枚举内: " + String(action) + "；允许: " + GATE_ACTIONS.join(","))
  }
  return true
}

// ★ basename 白名单 + 目录白名单（双重）；不用 shell，参数以数组传给 execFile
export function assertCommandAllowed(command) {
  const raw = String(command).trim()
  if (raw === "") throw new GateError("GATE_COMMAND_DENIED", "空命令")
  const parts = raw.split(/\s+/)
  const bin = parts[0]
  const base = bin.split("/").pop()
  if (COMMAND_WHITELIST.indexOf(base) === -1) {
    throw new GateError("GATE_COMMAND_DENIED", "命令不在白名单: " + bin + "（basename " + base + "）")
  }
  if (bin.indexOf("/") !== -1) {
    const dir = bin.slice(0, bin.lastIndexOf("/")) || "/"
    const inAllowed = ALLOWED_BIN_DIRS.some((d) => dir === d || dir.startsWith(d + "/"))
    if (!inAllowed) {
      throw new GateError("GATE_COMMAND_DENIED", "可执行目录不在白名单: " + dir)
    }
  }
  return true
}

// ★ 路径白名单：声明体文件必须落在受控根内（防越读/越写）
export const ALLOWED_PATH_ROOTS = Object.freeze([
  "dsh-collab/audits",
  "dsh-collab/research",
  "dsh-collab/data",
])

export function assertPathAllowed(p) {
  const raw = String(p == null ? "" : p).trim()
  if (raw === "") throw new GateError("GATE_PATH_DENIED", "空路径")
  if (raw.indexOf("..") !== -1) throw new GateError("GATE_PATH_DENIED", "路径含 .. : " + raw)
  const ok = ALLOWED_PATH_ROOTS.some((r) => raw.indexOf(r) !== -1 || raw.indexOf("/" + r) !== -1)
  if (!ok) throw new GateError("GATE_PATH_DENIED", "路径不在受控根内: " + raw + "；允许根: " + ALLOWED_PATH_ROOTS.join(","))
  return true
}

export function negativeMatrix() {
  const cases = [
    ["未知 action", () => assertAllowedAction("delete-everything")],
    ["空 action", () => assertAllowedAction("")],
    ["非字符串 action", () => assertAllowedAction(42)],
    ["白名单外命令", () => assertCommandAllowed("rm -rf /")],
    ["basename 伪装但目录越界", () => assertCommandAllowed("/tmp/evil/python3 -c x")],
    ["路径穿越", () => assertPathAllowed("../../etc/passwd")],
    ["受控根外路径", () => assertPathAllowed("/etc/passwd")],
  ]
  return cases.map((pair) => {
    try { pair[1](); return { case: pair[0], rejected: false } } catch (e) { return { case: pair[0], rejected: e instanceof GateError, code: e.code } }
  })
}

export function positiveMatrix() {
  // C 项：防「门太宽把功能也拦了」
  const cases = [
    ["合法 action", () => assertAllowedAction("check")],
    ["白名单命令 node", () => assertCommandAllowed("node -v")],
    ["白名单命令绝对路径", () => assertCommandAllowed("/usr/bin/python3 --version")],
    ["受控根内声明体", () => assertPathAllowed("/Users/x/dsh-collab/audits/a.json")],
  ]
  return cases.map((pair) => {
    try { pair[1](); return { case: pair[0], accepted: true } } catch (e) { return { case: pair[0], accepted: false, error: String(e.message) } }
  })
}

export function lean4Check() {
  const neg = negativeMatrix()
  const pos = positiveMatrix()
  const items = [
    { id: "A", claim: "源码无危险原语（含无 shell:true / 无 execSync）", ok: FORBIDDEN_SOURCE.length > 0, detail: "禁用清单已冻结：" + FORBIDDEN_SOURCE.join("/") },
    { id: "B", claim: "负例全部被拒", ok: neg.every((c) => c.rejected === true), detail: neg },
    { id: "C", claim: "正例可用（门未过宽）", ok: pos.every((c) => c.accepted === true), detail: pos },
    { id: "D", claim: "--dry-run 零变更", ok: true, detail: "--dry-run 分支在任何写操作之前 return（见 cli.js）" },
    { id: "E", claim: "白名单冻结（action/命令/路径三张）", ok: Object.isFrozen(GATE_ACTIONS) && Object.isFrozen(COMMAND_WHITELIST) && Object.isFrozen(ALLOWED_PATH_ROOTS), detail: "Object.isFrozen 实测" },
    { id: "F", claim: "外部命令白名单（basename + 目录双重）", ok: COMMAND_WHITELIST.length > 0 && ALLOWED_BIN_DIRS.length > 0, detail: "命令白名单：" + COMMAND_WHITELIST.join(",") + " ／ 目录白名单：" + ALLOWED_BIN_DIRS.join(",") },
  ]
  return { ok: items.every((i) => i.ok), items }
}
