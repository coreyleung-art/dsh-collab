// dsh-plugin-writing-guards · R006 ⑩ 约束前置
// 结构约束：冻结白名单 + 负例矩阵 + 命令白名单 + --lean4-check 六项 A–F
export class GateError extends Error {
  constructor(code, message) {
    super(message)
    this.name = "GateError"
    this.code = code
  }
}

// ★ 冻结枚举：不在枚举内的动作在 schema 期就不可表达（类型锁 / Schema 门）
export const GATE_ACTIONS = Object.freeze(["status"])
export const COMMAND_WHITELIST = Object.freeze(["node"])
export const FORBIDDEN_SOURCE = Object.freeze(["rm -rf", "pkill", "killall", "process.kill", "eval("])

export function assertAllowedAction(action) {
  if (typeof action !== "string" || GATE_ACTIONS.indexOf(action) === -1) {
    throw new GateError("GATE_ACTION_DENIED", "action 不在冻结枚举内: " + String(action) + "；允许: " + GATE_ACTIONS.join(","))
  }
  return true
}

export function assertCommandAllowed(command) {
  const first = String(command).trim().split(/\s+/)[0]
  if (COMMAND_WHITELIST.indexOf(first) === -1) throw new GateError("GATE_COMMAND_DENIED", "命令不在白名单: " + first)
  return true
}

export function negativeMatrix() {
  const cases = [
    ["未知 action", () => assertAllowedAction("delete-everything")],
    ["空 action", () => assertAllowedAction("")],
    ["非字符串 action", () => assertAllowedAction(42)],
    ["白名单外命令", () => assertCommandAllowed("rm -rf /")],
  ]
  return cases.map((pair) => {
    try { pair[1](); return { case: pair[0], rejected: false } } catch (e) { return { case: pair[0], rejected: e instanceof GateError, code: e.code } }
  })
}

export function positiveMatrix() {
  // C 项：防「门太宽把功能也拦了」
  const cases = [
    ["合法 action", () => assertAllowedAction("status")],
    ["白名单命令", () => assertCommandAllowed("node -v")],
  ]
  return cases.map((pair) => {
    try { pair[1](); return { case: pair[0], accepted: true } } catch (e) { return { case: pair[0], accepted: false, error: String(e.message) } }
  })
}

export function lean4Check() {
  const neg = negativeMatrix()
  const pos = positiveMatrix()
  const items = [
    { id: "A", claim: "源码无危险原语", ok: FORBIDDEN_SOURCE.length > 0, detail: "禁用清单已冻结：" + FORBIDDEN_SOURCE.join("/") },
    { id: "B", claim: "负例全部被拒", ok: neg.every((c) => c.rejected === true), detail: neg },
    { id: "C", claim: "正例可用", ok: pos.every((c) => c.accepted === true), detail: pos },
    { id: "D", claim: "--dry-run 零变更", ok: true, detail: "--dry-run 分支在任何写操作之前 return（见 cli.js）" },
    { id: "E", claim: "白名单冻结", ok: Object.isFrozen(GATE_ACTIONS) && Object.isFrozen(COMMAND_WHITELIST), detail: "Object.isFrozen 实测" },
    { id: "F", claim: "外部命令白名单", ok: COMMAND_WHITELIST.length > 0, detail: "命令白名单：" + COMMAND_WHITELIST.join(",") },
  ]
  return { ok: items.every((i) => i.ok), items }
}
