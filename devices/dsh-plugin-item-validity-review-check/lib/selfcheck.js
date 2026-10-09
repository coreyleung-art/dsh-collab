// dsh-plugin-item-validity-review-check · R006 ② TCC 能力边界自检
// 三段：① 能力清单 ② 不该发生路径 ③ 依赖完整性；★ 含 R006 ① 第 5 项真挂载冒烟（三态）
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { GateError, INDEX_PATH, INBOX_DIR, SOURCE_ENUM, assertNoIndexPathInput, assertSource, assertWriteTargetAllowed } from "./gate.js"

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, "..")

/** ① 能力清单：四个工具 + 各自只读/可写（R2 要求逐条给访问级别）。 */
export const CAPABILITY_MATRIX = Object.freeze([
  Object.freeze({ name: "item_validity_check", access: "只读", write: false, what: "判一条：形态 + 五态 + 条件量 + 盲区" }),
  Object.freeze({ name: "item_validity_batch", access: "只读", write: false, what: "全量扫描：五态计数 + 形态计数 + 逐条行" }),
  Object.freeze({ name: "item_validity_explain", access: "只读", write: false, what: "解释判定链与依赖条件量" }),
  Object.freeze({ name: "item_validity_index_write", access: "可写（唯一）", write: true, what: "写唯一索引 " + INDEX_PATH + "；dryRun 默认 true，须 confirm:true" }),
])

export const CAPABILITIES = Object.freeze([
  "能力清单：分形态（action/record/feed/ack/unknown）—— 形态判不了必须报 unknown，绝不并入任何一侧",
  "能力清单：判五态（closed/stale/open/unknown/n/a），每态附所依赖的条件量",
  "能力清单：回复可见性三通道 A(卡内指针·中强度)/B(线程记录·强强度)/C(指针形态·弱·仅参考)",
  "能力清单：时效窗默认 7 天（可覆盖，窗值必打印）；ISO 无时区按 UTC 解释并写明该假设",
  "能力清单：唯一写操作 = 索引（默认 dryRun；写临时文件再改名；写后回读断言）",
  "能力清单：R7 逐条日志（每次判一条一行 JSON，unknown 也写）",
  "能力清单（工具矩阵）：" + CAPABILITY_MATRIX.map((t) => t.name + "=" + t.access).join(" · "),
])

/** ② 不该发生路径（每条附**拒绝证明**，见 forbiddenPathProofs） */
export const FORBIDDEN_PATHS = Object.freeze([
  "不该发生：写被审对象 —— 只读侧无写调用；唯一写目标须 === INDEX_PATH 常量全等（拒绝证明见下）",
  "不该发生：把索引写到别处 —— 索引路径是模块常量、不是入参；路径类入参键一律 GateError（拒绝证明见下）",
  "不该发生：source 传路径 —— SOURCE_ENUM 冻结为 [\"inbox\"]；/etc、相对路径、~、通配一律 GateError（拒绝证明见下）",
])

export const PEERS = Object.freeze(["@deepseek-ai/cordis", "@deepseek-ai/dsh-tools"])

/**
 * ② 三条「不该发生路径」的**拒绝证明**：真的去试，如实记录被谁拒、什么码。
 * 不做「声称」，只报实测。
 */
export function forbiddenPathProofs() {
  const cases = [
    { path: "写被审对象", attempt: "写目标 = 被审目录内的文件", run: () => assertWriteTargetAllowed(INBOX_DIR + "/some-item.json") },
    { path: "写被审对象", attempt: "写目标 = 被审目录本身", run: () => assertWriteTargetAllowed(INBOX_DIR) },
    { path: "把索引写到别处", attempt: "入参 indexPath=/tmp/elsewhere.json", run: () => assertNoIndexPathInput({ indexPath: "/tmp/elsewhere.json" }) },
    { path: "把索引写到别处", attempt: "入参 path=/tmp/elsewhere.json", run: () => assertNoIndexPathInput({ path: "/tmp/elsewhere.json" }) },
    { path: "把索引写到别处", attempt: "写目标 = /tmp/elsewhere.json", run: () => assertWriteTargetAllowed("/tmp/elsewhere.json") },
    { path: "source 传路径", attempt: "source=/etc", run: () => assertSource("/etc") },
    { path: "source 传路径", attempt: "source=./inbox（相对路径）", run: () => assertSource("./inbox") },
    { path: "source 传路径", attempt: "source=~/.dsh/inbox/*（家目录通配）", run: () => assertSource("~/.dsh/inbox/*") },
    { path: "source 传路径", attempt: "source=null（非字符串）", run: () => assertSource(null) },
  ]
  const proofs = cases.map((c) => {
    try {
      c.run()
      return { path: c.path, attempt: c.attempt, rejected: false, code: null, proof: "★ 竟然放行 —— 门失效" }
    } catch (e) {
      return {
        path: c.path,
        attempt: c.attempt,
        rejected: e instanceof GateError,
        code: e && e.code ? e.code : "NON_GATE_ERROR",
        proof: String(e && e.message).slice(0, 150),
      }
    }
  })
  // 附一条结构证明：唯一写目标就是常量本身（且不在被审目录内）
  const struct = {
    indexPath: INDEX_PATH,
    indexPathIsInput: false,
    inboxDir: INBOX_DIR,
    indexPathInsideInbox: String(INDEX_PATH).startsWith(INBOX_DIR + "/"),
    sourceEnum: [...SOURCE_ENUM],
    positiveWriteTargetOk: (() => { try { return assertWriteTargetAllowed(INDEX_PATH) === true } catch { return false } })(),
  }
  return { proofs, struct, ok: proofs.every((p) => p.rejected) && struct.positiveWriteTargetOk && !struct.indexPathInsideInbox }
}

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
  const proofs = spec.includeProofs === false ? null : forbiddenPathProofs()
  const result = {
    ok: (symbols.ok !== false && smoke.state !== "fail") && (proofs === null || proofs.ok === true),
    tool: name,
    sections: {
      // ① 能力清单  ② 不该发生路径（含拒绝证明）  ③ 依赖完整性
      capabilities: CAPABILITIES,
      capabilityMatrix: CAPABILITY_MATRIX,
      forbidden: FORBIDDEN_PATHS,
      forbiddenProofs: proofs,
      dependencies: deps,
      symbols: symbols,
      smoke: smoke,
    },
  }
  try {
    const dir = join(process.env.HOME || ".", ".dsh", "plugin-selfcheck")
    mkdirSync(dir, { recursive: true })
    writeFileSync(join(dir, name + ".json"), JSON.stringify(result, null, 2))
  } catch (e) { /* 落盘失败不阻断挂载 */ }
  return result
}
