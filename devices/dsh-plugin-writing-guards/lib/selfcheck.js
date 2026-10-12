// dsh-plugin-writing-guards · R006 ② TCC 能力边界自检
// 三段：① 能力清单 ② 不该发生路径 ③ 依赖完整性；★ 含 R006 ① 第 5 项真挂载冒烟（三态）
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
// ★ ② 能力清单与「不该发生」直接从内核取真值 ——★ 不再留骨架占位符
import { describeCapabilities } from "./core.js"

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, "..")

const _CAPS = describeCapabilities()
export const CAPABILITIES = Object.freeze([
  `能力清单：${_CAPS.purpose}`,
  ..._CAPS.can.map((c) => `能力清单：${c}`),
])
export const FORBIDDEN_PATHS = Object.freeze(
  _CAPS.cannot.map((c) => `不该发生：${c}`)
)
export const PEERS = Object.freeze(["@deepseek-ai/cordis", "@deepseek-ai/dsh-tools"])

export function dependencyReport() {
  // 两级解析：本目录 node_modules → profile node_modules（只试一级 = 假失败）
  return PEERS.map((name) => {
    const local = join(ROOT, "node_modules", name, "package.json")
    const profile = resolve(ROOT, "..", "..", "node_modules", name, "package.json")
    if (existsSync(local)) return { peer: name, resolved: true, where: "plugin/node_modules" }
    if (existsSync(profile)) return { peer: name, resolved: true, where: "profile/node_modules" }
    return { peer: name, resolved: false, where: null }
  })
}

export function symbolCheck(required, sourceFiles) {
  // ★ 必须显式给 sourceFiles：不给就会扫到本文件自身 → 假失败或假通过
  if (!Array.isArray(sourceFiles) || sourceFiles.length === 0) {
    return { ok: null, skipped: true, reason: "未提供 sourceFiles，符号检查如实跳过（不假装通过）" }
  }
  const text = sourceFiles.map((f) => { try { return readFileSync(join(ROOT, f), "utf8") } catch (e) { return "" } }).join(" ")
  const missing = required.filter((s) => text.indexOf(s) === -1)
  return { ok: missing.length === 0, missing: missing }
}

export async function mountSmoke(entry = join(ROOT, "lib", "index.js")) {
  // R006 ① 第 5 项：真 import + 桩 ctx 调 apply + 断言注册结果。三态分开报，绝不假装通过。
  const out = { state: "pass", registered: [], errors: [] }
  const anyStub = (label) => new Proxy(function () {}, {
    get: (_t, k) => {
      if (typeof k === "symbol" || k === "then") return undefined
      if (k === "register") return (d) => { out.registered.push(typeof d === "string" ? d : (d && d.name) || "?"); return () => {} }
      return anyStub(label + "." + String(k))
    },
    apply: () => anyStub(label + "()"),
    set: () => true,
  })
  const base = {
    on: () => () => {},
    effect: (cb) => { try { const d = cb(); return typeof d === "function" ? d : () => {} } catch (e) { out.errors.push(String((e && e.message) || e)); return () => {} } },
    get: (n) => anyStub("get:" + String(n)),
  }
  const ctx = new Proxy(base, { get: (t, k) => (k in t ? t[k] : typeof k === "symbol" ? undefined : anyStub("ctx:" + String(k))) })
  try {
    const mod = await import(pathToFileURL(entry).href)
    const apply = typeof mod.apply === "function" ? mod.apply : mod.default && typeof mod.default.apply === "function" ? mod.default.apply : null
    if (apply === null) { out.state = "fail"; out.errors.push("入口未导出 apply(ctx, config)") } else { await apply(ctx, {}) }
  } catch (e) {
    const msg = String((e && e.message) || e)
    if ((e && e.code === "ERR_MODULE_NOT_FOUND") || /Cannot find (package|module)/.test(msg)) { out.state = "skipped"; out.reason = msg }
    else { out.state = "fail"; out.errors.push(msg) }
  }
  return out
}

// ★ 递归闸：apply 会调 runSelfCheck，而冒烟又会 import 入口再调 apply。
//   调用方应传 skipSmoke:true（模板生成的 index.js 已这么传）；这里再加一道闸，
//   即使调用方忘了传也不会自递归——如实标 skipped，不假装通过。
let __smokeInFlight = false

export async function runSelfCheck(name, spec = {}) {
  const deps = dependencyReport()
  const symbols = symbolCheck(spec.requiredSymbols || [], spec.sourceFiles || [])
  let smoke
  if (spec.skipSmoke === true) {
    smoke = { state: "skipped", registered: [], errors: [], reason: "skipSmoke：apply 期自查只查 peer/符号，冒烟由 --selfcheck 执行" }
  } else if (__smokeInFlight) {
    smoke = { state: "skipped", registered: [], errors: [], reason: "冒烟已在执行中（递归闸）：如实跳过，不假装通过" }
  } else {
    __smokeInFlight = true
    try { smoke = await mountSmoke() } finally { __smokeInFlight = false }
  }
  const result = {
    ok: symbols.ok !== false && smoke.state !== "fail",
    tool: name,
    sections: { capabilities: CAPABILITIES, forbidden: FORBIDDEN_PATHS, dependencies: deps, symbols: symbols, smoke: smoke },
  }
  try {
    const dir = join(process.env.HOME || ".", ".dsh", "plugin-selfcheck")
    mkdirSync(dir, { recursive: true })
    writeFileSync(join(dir, name + ".json"), JSON.stringify(result, null, 2))
  } catch (e) { /* 落盘失败不阻断挂载 */ }
  return result
}
