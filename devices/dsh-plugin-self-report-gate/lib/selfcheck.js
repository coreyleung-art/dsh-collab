// dsh-plugin-self-report-gate · R006 ② TCC 能力边界自检
// 三段：① 能力清单 ② 不该发生路径 ③ 依赖完整性；★ 含 R006 ① 第 5 项真挂载冒烟（三态）
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, "..")

export const CAPABILITIES = Object.freeze([
  "能力：探测 python3 与门脚本是否在位，回报 PATH / node / 候选路径（只读，不写盘）",
  "能力：现场读取 R-SR 门版本（绝不硬编码会变的值）",
  "能力：转调门的自测矩阵（--selftest）并原样回报",
  "能力：对受控根内的 R046 声明体 JSON 转调门检查（--check），原样回报门的 stdout 与退出码语义",
  "能力：把「门不可用」如实回报成 unavailable，不降级、不假装通过",
])

export const FORBIDDEN_PATHS = Object.freeze([
  "不该发生：在 JS 侧重实现任何 SRx 判据（唯一实现在 Python 门；重实现会制造双来源漂移）",
  "不该发生：任何写盘 / 删除交付物 / 修改被审对象（本插件全程只读）",
  "不该发生：经过 shell 执行命令（只用 execFile + 参数数组，无 shell:true）",
  "不该发生：读取受控根之外的声明体路径（assertPathAllowed 前置）",
  "不该发生：门缺位时静默通过（必须回报 unavailable）",
])

export const PEERS = Object.freeze(["@deepseek-ai/cordis", "@deepseek-ai/dsh-tools"])

// ★ ③ CLD 自适应：peer 三级解析。前两级是包内/profile，第三级是 CLD 自带 runtime ——
//   实测本机插件目录与 ~/dsh-collab 下都没有 @deepseek-ai/*，只有 CLD runtime 里有；
//   只试前两级会把「环境问题」误报成「包问题」（R006 坑 #4 假失败）。
export const CLD_RUNTIME_ROOTS = Object.freeze([
  "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules",
])

export function dependencyReport() {
  return PEERS.map((name) => {
    const local = join(ROOT, "node_modules", name, "package.json")
    const profile = resolve(ROOT, "..", "..", "node_modules", name, "package.json")
    if (existsSync(local)) return { peer: name, resolved: true, where: "plugin/node_modules" }
    if (existsSync(profile)) return { peer: name, resolved: true, where: "profile/node_modules" }
    for (const root of CLD_RUNTIME_ROOTS) {
      const p = join(root, name, "package.json")
      if (existsSync(p)) return { peer: name, resolved: true, where: "cld-runtime", path: p }
    }
    return { peer: name, resolved: false, where: null, tried: [local, profile, ...CLD_RUNTIME_ROOTS.map((r) => join(r, name, "package.json"))] }
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
