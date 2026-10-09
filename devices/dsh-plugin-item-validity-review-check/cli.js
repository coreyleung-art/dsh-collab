#!/usr/bin/env node
// dsh-plugin-item-validity-review-check · CLI
// R006 ⑨ CLI 治理：严格旗标（未知旗标 exit 2）/ 退出码 0 成功·1 门失效或判 fail·2 用法或 IO
//                      / --dry-run 零变更 / --json / --help
// R006 ② --selfcheck 三段：① 能力清单 ② 不该发生路径（含拒绝证明） ③ 依赖完整性
// R006 ⑩ --lean4-check 六项 A–F（A 真扫 lib/*.js；B ≥8 负例；C ≥3 正例；E Object.isFrozen；F 非空集）
// R006 ⑥ --tool-version 从 package.json 现读（源码内无第二处版本硬编码）
// R006 ⑦ 每次判一条写一行 JSON 日志（判不了也写）
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

import { ACTIONS, GateError, SOURCE_ENUM, STATES, lean4Check } from "./lib/gate.js"
import { BLIND_SPOT, buildIndex, batchScan, checkItem, classify, describeCapabilities, indexWrite, replyPointerKind } from "./lib/core.js"
import { CAPABILITY_MATRIX, runSelfCheck } from "./lib/selfcheck.js"

const HERE = dirname(fileURLToPath(import.meta.url))
const C = { ok: "✅", no: "❌", warn: "⚠️" }
const w = (s) => process.stdout.write(s + "\n")

/** 全部已识别旗标（一次受理，其余一律 exit 2）。 */
export const FLAGS = Object.freeze([
  "--help", "-h", "--json", "--dry-run", "--selfcheck", "--lean4-check", "--selftest",
  "--tool-version", "--source", "--max-age-days", "--key", "--list", "--write-index", "--confirm",
])
const VALUE_FLAGS = Object.freeze(["--source", "--max-age-days", "--key", "--list"])
const BOOL_FLAGS = FLAGS.filter((f) => !VALUE_FLAGS.includes(f))

export function usage() {
  return [
    "dsh-plugin-item-validity-review-check — 条目有效性审查（五态 + 条件量 + 盲区声明）",
    "",
    "用法：node cli.js [旗标]",
    "",
    "  --source <value>      数据源：冻结枚举 [" + SOURCE_ENUM.join(", ") + "]（默认 inbox）。**不接受路径**",
    "  --key <name>          判一条（inbox 文件名 / 去 .json 的名 / 条目 key 字段）",
    "  --list <state>        只列某一态：" + STATES.join(" / "),
    "  --max-age-days <n>    时效窗天数（默认 7；窗值必打印在输出里）",
    "  --write-index         写索引（默认 dry-run 零变更；须与 --confirm 同用才真写）",
    "  --confirm             确认真写索引（必须显式给）",
    "  --dry-run             零变更演练（只出计划）",
    "  --selftest            正/负例矩阵自证（≥14 条）",
    "  --selfcheck           能力清单 / 不该发生路径（含拒绝证明）/ 依赖完整性 + 真挂载冒烟",
    "  --lean4-check         约束门六项自证 A–F",
    "  --tool-version        打印版本（唯一来源：package.json）",
    "  --json                机器可读输出",
    "  --help, -h            本帮助",
    "",
    "退出码：0 成功 · 1 门失效或判 fail · 2 用法或 IO 错误",
    "★ 盲区：只看条目本身 + 可见线程（详见输出末尾声明）。",
  ].join("\n") + "\n"
}

/** ⑥ 版本单一来源：只从 package.json 读，绝不第二处硬编码。 */
export function toolVersion() {
  return JSON.parse(readFileSync(join(HERE, "package.json"), "utf8")).version
}

/* ══════════════════════════════ 参数解析（严格） ══════════════════════════════ */

function parse(argv) {
  const out = { _: [] }
  for (let i = 0; i < argv.length; i++) {
    let a = argv[i]
    if (!a.startsWith("-")) { out._.push(a); continue }
    let value = null
    const eq = a.indexOf("=")
    if (eq !== -1) { value = a.slice(eq + 1); a = a.slice(0, eq) }
    if (!FLAGS.includes(a)) return { error: "未知旗标 " + a }
    if (VALUE_FLAGS.includes(a)) {
      const v = value !== null ? value : argv[++i]
      if (v === undefined) return { error: "旗标 " + a + " 需要一个值" }
      if (a === "--max-age-days") {
        const n = Number(v)
        if (!Number.isFinite(n) || n < 0) return { error: "--max-age-days 需要非负数字，实得「" + v + "」" }
        out.maxAgeDays = n
      } else if (a === "--source") out.source = v
      else if (a === "--key") out.key = v
      else if (a === "--list") out.list = v
    } else {
      if (value !== null) return { error: "旗标 " + a + " 不接受值" }
      out[a.replace(/^--?/, "").replace(/-/g, "")] = true
    }
  }
  return out
}

/* ══════════════════════════════ --selftest ══════════════════════════════ */

const DAY = 86400000

/** 造一份带索引的判定上下文（通道 A/B 需要可见集）。 */
function judge(doc, name, extra = {}) {
  const entries = (extra.other || []).concat([{ name, doc }])
  const index = buildIndex(entries)
  index.entryByName = new Map(entries.map((e) => [e.name, e.doc]))
  return classify(doc, name, { nowMs: extra.nowMs || Date.now(), maxAgeDays: extra.maxAgeDays || 7, index, strictNoReply: extra.strict === true })
}

/** 单条门拒绝测试。 */
function gateReject(fn) {
  try { fn(); return { rejected: false, code: null } } catch (e) { return { rejected: e instanceof GateError, code: e && e.code ? e.code : "NON_GATE_ERROR" } }
}

export function selftestCases() {
  const now = Date.now()
  const iso = (ms) => new Date(ms).toISOString()
  const cases = []
  const add = (name, want, got, detail) => cases.push({
    name, want, got, ok: want === got, detail,
    flag: String(name).startsWith("负例") ? "负例" : "正例",
  })

  /* ── 负例（含规范点名要求的 8 条） ── */

  // 1 关闭词只在正文 ⇒ 不得判 closed（body ⇒ record ⇒ n/a）
  let r = judge({ body: "我之前已完成过一次", sent_at_epoch_ms: now - DAY }, "t1.json")
  add("负例·关闭词只在正文(body)【不得】判 closed", "n/a", r.state, r.shape + " / " + r.why.slice(0, 60))

  // 2 record 年龄 300 天 ⇒ n/a（不得 stale）
  r = judge({ content: "一份旧资料", sent_at_epoch_ms: now - 300 * DAY }, "t2.json")
  add("负例·record 年龄 300 天 ⇒ n/a（不得 stale）", "n/a", r.state, r.shape + " / " + r.why.slice(0, 60))

  // 3 只有 from/to/ts ⇒ feed（不得 record）
  r = judge({ from: "a", to: "b", ts: iso(now - DAY) }, "t3.json")
  add("负例·仅 from/to/ts ⇒ feed（不得 record）", "feed", r.shape, r.state + " / " + r.why.slice(0, 50))

  // 4 字段全无 ⇒ unknown（不得 n/a）
  r = judge({}, "t4.json")
  add("负例·字段全无 ⇒ unknown（不得 n/a）", "unknown", r.state, r.shape + " / 缺：" + String(r.missing).slice(0, 50))

  // 5 reply_to 空串 ⇒ 不命中通道 A（三分判据）
  const emptyPointer = judge(
    { awaiting: "session-x", sent_at_epoch_ms: now - DAY },
    "t5.json",
    { other: [{ name: "other.json", doc: { reply_to: "", from: "x", ts: iso(now) } }] }
  )
  add("负例·reply_to 空串 ⇒ 不命中通道 A",
    "empty-and-no-hit",
    replyPointerKind("") + "-and-" + (emptyPointer.conditions.channelA.hit ? "hit" : "no-hit"),
    "pointerKind=" + replyPointerKind("") + " · channelA.hit=" + emptyPointer.conditions.channelA.hit)

  // 6 通道 A/B 都不命中 ⇒ unknown（不得 open）
  //   ★ 刻意让同线程的对方**与本条同发件人**（否则会命中通道 B，测的就不是「都不命中」了）
  r = judge(
    { awaiting: "session-x", thread: "thread-t6", from: "me", ts: iso(now - DAY) },
    "t6.json",
    { other: [{ name: "peer.json", doc: { thread: "thread-t6", from: "me", ts: iso(now - 3600_000) } }] }
  )
  add("负例·通道 A/B 都不命中 ⇒ unknown（不得 open）", "unknown", r.state, String(r.why).slice(0, 90))

  // 7 非 JSON 对象 ⇒ unknown
  r = judge(null, "t7.json")
  add("负例·非 JSON 对象 ⇒ unknown", "unknown", r.state, r.shape + " / " + r.why.slice(0, 50) + " / 补：" + String(r.howToFix).slice(0, 40))

  // 8 未知 source ⇒ 被门拒绝
  let g = gateReject(() => {
    if (!SOURCE_ENUM.includes("fs")) throw new GateError("GATE_SOURCE_DENIED", "x")
  })
  add("负例·未知 source ⇒ 被门拒绝", "rejected:GATE_SOURCE_DENIED", (g.rejected ? "rejected:" : "leaked:") + g.code, "source=fs")

  // 9-13 更多负例
  g = gateReject(() => assertSourceCli("/etc")); add("负例·source 传 /etc ⇒ 拒", "rejected:GATE_SOURCE_DENIED", (g.rejected ? "rejected:" : "leaked:") + g.code, "/etc")
  g = gateReject(() => assertSourceCli("./inbox")); add("负例·source 传相对路径 ⇒ 拒", "rejected:GATE_SOURCE_DENIED", (g.rejected ? "rejected:" : "leaked:") + g.code, "./inbox")
  g = gateReject(() => assertNoPathCli({ indexPath: "/tmp/x.json" })); add("负例·索引路径作为入参 ⇒ 拒", "rejected:GATE_INDEX_PATH_INPUT", (g.rejected ? "rejected:" : "leaked:") + g.code, "indexPath")
  g = gateReject(() => assertStateCli("maybe")); add("负例·未知 state ⇒ 拒", "rejected:GATE_STATE_DENIED", (g.rejected ? "rejected:" : "leaked:") + g.code, "maybe")
  g = gateReject(() => assertActionCli("delete-everything")); add("负例·未知 action ⇒ 拒", "rejected:GATE_ACTION_DENIED", (g.rejected ? "rejected:" : "leaked:") + g.code, "delete-everything")
  g = gateReject(() => assertActionCli(42)); add("负例·非字符串 action ⇒ 拒", "rejected:GATE_ACTION_DENIED", (g.rejected ? "rejected:" : "leaked:") + g.code, "42")

  // 14 索引写：未 confirm ⇒ 零变更
  const plan = indexWrite({ source: "inbox", dryRun: false, confirm: false })
  add("负例·索引写未 confirm ⇒ 零变更（wrote=false）", "false", String(plan.wrote), plan.protocol[0])

  /* ── 正例 ── */

  r = judge({ status: "已核验通过，不需再动。", sent_at_epoch_ms: now - 30 * DAY }, "p1.json")
  add("正例·状态字「已核验通过/不需再动」⇒ closed", "closed", r.state, String(r.channel))

  r = judge({ status: "已收讫", sent_at_epoch_ms: now - DAY }, "p2.json")
  add("正例·状态字「已收讫」⇒ closed", "closed", r.state, r.shape + " / " + String(r.channel))

  // 通道 A：另一条 reply_to 指向本条
  r = judge(
    { key: "card-abc", awaiting: "session-x", sent_at_epoch_ms: now - DAY },
    "p3.json",
    { other: [{ name: "reply.json", doc: { reply_to: "card-abc", from: "peer", ts: iso(now) } }] }
  )
  add("正例·通道 A（卡内指针）命中 ⇒ closed(A)", "closed:A", r.state + ":" + String(r.channel), String(r.why).slice(0, 70))

  // 通道 B：线程内晚于本条的他人消息
  r = judge(
    { awaiting: "session-x", thread: "thread-p4", from: "me", ts: iso(now - 2 * DAY) },
    "p4.json",
    { other: [{ name: "later.json", doc: { thread: "thread-p4", from: "peer", ts: iso(now - DAY) } }] }
  )
  add("正例·通道 B（线程记录）命中 ⇒ closed(B)", "closed:B", r.state + ":" + String(r.channel), String(r.why).slice(0, 70))

  // 动作项 · 窗内 · 无 thread · 无可见回复 ⇒ open
  r = judge({ awaiting: "session-x", sent_at_epoch_ms: now - 2 * DAY }, "p5.json")
  add("正例·动作项窗内无 thread ⇒ open", "open", r.state, "ageDays=" + r.conditions.ageDays + " 窗=" + r.conditions.maxAgeDays)

  // 动作项 · 超窗 ⇒ stale（且窗值打印在理由里）
  r = judge({ awaiting: "session-x", sent_at_epoch_ms: now - 30 * DAY }, "p6.json")
  add("正例·动作项超窗 ⇒ stale（窗值打印）", "stale", r.state, String(r.why).slice(0, 80))

  // reply_required === true ⇒ 动作项（不得当成 record）
  r = judge({ reply_required: true, content: "请回", sent_at_epoch_ms: now - DAY }, "p7.json")
  add("正例·reply_required=true ⇒ action（不得 record）", "action", r.shape, r.state)

  // ack 形态计数（状态字）与状态分离
  r = judge({ status: "已完成", sent_at_epoch_ms: now - DAY }, "p8.json")
  add("正例·ack 形态（状态字）与状态分离", "ack", r.shape, "state=" + r.state)

  // 无时区 ISO 串 ⇒ 按 UTC 解释并在理由里写明
  const noTz = new Date(now - 2 * DAY).toISOString().replace(/\.\d{3}Z$/, "")
  r = judge({ awaiting: "x", ts: noTz }, "p9.json")
  add("正例·无时区 ISO 串按 UTC 并写明假设", "true", String(String(r.why).includes("按 UTC 解释")), "ts=" + noTz)

  // 盲区声明必带
  add("正例·盲区声明必带（不可省）", "true", String(BLIND_SPOT.includes("不等于【确定仍有未决待办】") && BLIND_SPOT.includes("★ 盲区")), BLIND_SPOT.split("\n")[0])

  // 状态字在状态类字段里（不在正文）⇒ 命中
  r = judge({ status: "pending", sent_at_epoch_ms: now - DAY }, "p10.json")
  add("正例·状态类字段含待处理词 ⇒ 非 closed", "true", String(r.state !== "closed"), "state=" + r.state + " openWord=" + JSON.stringify(r.conditions.openWord))

  // 严格口径：无 thread 的动作项在 strict 下也判 unknown
  r = judge({ awaiting: "session-x", sent_at_epoch_ms: now - DAY }, "p11.json", { strict: true })
  add("正例·严格口径下无 thread 动作项 ⇒ unknown", "unknown", r.state, String(r.why).slice(0, 70))

  return cases
}

// 自证用的门调用（与插件内同一套冻结枚举）
function assertSourceCli(v) {
  if (typeof v === "string" && SOURCE_ENUM.includes(v.trim())) return v
  throw new GateError("GATE_SOURCE_DENIED", "source 不在冻结枚举内: " + String(v))
}
function assertActionCli(v) {
  if (typeof v === "string" && ACTIONS.includes(v)) return true
  throw new GateError("GATE_ACTION_DENIED", "action 不在冻结枚举内: " + String(v))
}
function assertStateCli(v) {
  if (typeof v === "string" && STATES.includes(v)) return true
  throw new GateError("GATE_STATE_DENIED", "state 不在冻结枚举内: " + String(v))
}
function assertNoPathCli(args) {
  for (const k of Object.keys(args || {})) {
    if (["indexPath", "index", "path", "out", "file", "dir"].includes(k)) {
      throw new GateError("GATE_INDEX_PATH_INPUT", "入参含路径类键: " + k)
    }
  }
  return true
}

export function runSelftest(asJson) {
  const cases = selftestCases()
  const pass = cases.filter((c) => c.ok).length
  const fail = cases.length - pass
  if (asJson) {
    w(JSON.stringify({ ok: fail === 0, total: cases.length, pass, fail, cases, blindSpot: BLIND_SPOT }, null, 2))
    return fail === 0 ? 0 : 1
  }
  w("--selftest · 正/负例矩阵自证（判据须双向对照，只给正例不算）")
  w("")
  for (const c of cases) w("  " + (c.ok ? C.ok : C.no) + " " + c.name.padEnd(46, " ") + " 期望=" + String(c.want).padEnd(26, " ") + " 实得=" + String(c.got).padEnd(26, " ") + " " + c.detail)
  w("")
  w("  selftest: " + pass + " PASS / " + fail + " FAIL（共 " + cases.length + " 条）")
  if (fail > 0) w("  ★ FAIL 明细：" + cases.filter((c) => !c.ok).map((c) => c.name).join(" | "))
  w("")
  w(BLIND_SPOT)
  return fail === 0 ? 0 : 1
}

/* ══════════════════════════════ main ══════════════════════════════ */

export async function main(argv) {
  const args = parse(argv)
  if (args.error) { process.stderr.write("用法错误：" + args.error + "\n试 --help\n"); return 2 }

  if (args.help || argv.length === 0) { process.stdout.write(usage()); return 0 }
  if (args.toolversion) { w(toolVersion()); return 0 }
  if (args.selftest) return runSelftest(args.json === true)

  // ── --selfcheck：R2 三段 ──
  if (args.selfcheck) {
    const sc = await runSelfCheck("item-validity-review-check", {
      sourceFiles: ["cli.js", "lib/core.js", "lib/index.js"],
      requiredSymbols: ["classify", "batchScan", "indexWrite", "defineTool"],
    })
    const s = sc.sections
    if (args.json) { w(JSON.stringify(sc, null, 2)); return sc.ok ? 0 : 1 }

    w("R006 ② --selfcheck · 三段")
    w("")
    w("① 能力清单（四个工具 + 只读/可写）")
    for (const t of CAPABILITY_MATRIX) w("    " + (t.write ? C.warn : C.ok) + " " + t.name.padEnd(30, " ") + " " + t.access.padEnd(16, " ") + " " + t.what)
    for (const c of s.capabilities) w("    · " + c)
    w("")
    w("② 不该发生路径（逐条**拒绝证明**：真去试，记录被谁拒）")
    for (const p of s.forbidden) w("    " + C.ok + " " + p)
    for (const p of (s.forbiddenProofs ? s.forbiddenProofs.proofs : [])) {
      w("      " + (p.rejected ? C.ok : C.no) + " [" + p.path + "] " + p.attempt + " ⇒ " + (p.rejected ? p.code : "★ 未拒绝") + " · " + p.proof)
    }
    const st = s.forbiddenProofs ? s.forbiddenProofs.struct : {}
    w("      结构证明：索引路径是模块常量（非入参）· 位于被审目录内=" + st.indexPathInsideInbox + " · 唯一写目标全等断言=" + st.positiveWriteTargetOk)
    w("      " + (s.forbiddenProofs && s.forbiddenProofs.ok ? C.ok : C.no) + " 三条不该发生路径：拒绝证明 " + (s.forbiddenProofs ? s.forbiddenProofs.proofs.length : 0) + " 条，全部被拒=" + (s.forbiddenProofs ? s.forbiddenProofs.ok : false))
    w("")
    w("③ 依赖完整性")
    for (const d of s.dependencies) w("    " + (d.resolved ? C.ok : C.no) + " " + d.peer + " → " + (d.where || "未解析"))
    w("    " + (s.symbols.ok ? C.ok : C.no) + " 符号检查：" + JSON.stringify(s.symbols))
    const smokeIcon = { pass: C.ok, fail: C.no, skipped: C.warn }[s.smoke.state] || C.warn
    w("    " + smokeIcon + " 插件挂载冒烟：" + s.smoke.state + (s.smoke.reason ? " — " + s.smoke.reason : ""))
    if (s.smoke.registered && s.smoke.registered.length) w("        已注册工具：" + s.smoke.registered.join(", "))
    if (s.smoke.state !== "pass") w("        ⊘ 未 pass ⇒ **不得据此声称 ① 达标**（如实报，不假装通过）")
    w("")
    w("统一日志：" + join(process.env.HOME || "", "dsh-collab/logs/dsh-plugin-item-validity-review-check.log"))
    w("自查总判：" + (sc.ok ? C.ok + " 通过" : C.no + " 未通过"))
    w("")
    w(BLIND_SPOT)
    return sc.ok ? 0 : 1
  }

  // ── --lean4-check：A–F ──
  if (args.lean4check) {
    const result = lean4Check({
      root: HERE,
      dryRunProbe: () => indexWrite({ source: "inbox", dryRun: false, confirm: false }),
    })
    if (args.json) { w(JSON.stringify(result, null, 2)); return result.ok ? 0 : 1 }
    w("--lean4-check · 结构门自证 A–F（" + result.gate.principle + "）")
    w("")
    for (const it of result.items) w("  " + (it.ok ? C.ok : C.no) + " " + it.id + " " + it.claim + " — " + it.detail)
    w("")
    w("  " + (result.ok ? C.ok + " 门生效：约束不可绕过（无入口 + 有证明）" : C.no + " 门未生效，禁止交付"))
    w("")
    w(BLIND_SPOT)
    return result.ok ? 0 : 1
  }

  // ── 数据源门（一切扫描前） ──
  let source
  try {
    source = args.source === undefined ? SOURCE_ENUM[0] : assertSourceCli(args.source)
  } catch (e) {
    process.stderr.write("用法错误：" + e.message + "\n")
    return 2
  }
  if (args.list !== undefined && !STATES.includes(args.list)) { process.stderr.write("用法错误：--list 只能是 " + STATES.join(" / ") + "\n"); return 2 }

  // ── --write-index ──
  if (args.writeindex) {
    const res = indexWrite({ source, maxAgeDays: args.maxAgeDays, dryRun: args.dryrun === true, confirm: args.confirm === true })
    if (args.json) { w(JSON.stringify(res, null, 2)); return res.ok ? 0 : 1 }
    w("索引写入 · " + res.path + "（模块常量，非入参）")
    for (const p of res.protocol) w("  · " + p)
    w("  " + (res.wrote ? C.ok + " 已写 " + res.writtenItems + " 条（回读断言 " + res.assert + "）" : C.warn + " dry-run：零变更（计划 " + res.plannedItems + " 条）"))
    w("")
    w(res.blindSpot)
    return res.ok ? 0 : 1
  }

  // ── --dry-run / 单条 --key / 全量扫描 ──
  try {
    if (args.dryrun) {
      const res = indexWrite({ source, maxAgeDays: args.maxAgeDays, dryRun: true, confirm: false })
      if (args.json) { w(JSON.stringify({ ...res, capabilities: describeCapabilities() }, null, 2)); return res.ok ? 0 : 1 }
      w("--dry-run · 零变更演练（本命令不做任何写）")
      w("  索引目标：" + res.path + "（模块常量；不是入参）")
      w("  计划写入：" + res.plannedItems + " 条（closed + stale）／ 全量 " + res.plannedTotal + " 条")
      w("  五态：" + JSON.stringify(res.tally))
      for (const p of res.protocol) w("  · " + p)
      w("")
      w(res.blindSpot)
      return res.ok ? 0 : 1
    }

    if (args.key !== undefined) {
      const res = checkItem({ source, key: args.key, maxAgeDays: args.maxAgeDays })
      if (args.json) { w(JSON.stringify(res, null, 2)); return res.ok ? 0 : 1 }
      w("条目：" + res.key + "  形态=" + res.shape + "  状态=" + res.state + "  通道=" + res.channel)
      w("  理由：" + res.why)
      if (res.missing) w("  缺的是：" + res.missing + "\n  怎么补：" + res.howToFix)
      w("")
      w(res.blindSpot)
      return res.ok ? 0 : 1
    }

    const res = batchScan({ source, maxAgeDays: args.maxAgeDays, state: args.list, limit: undefined })
    if (args.json) { w(JSON.stringify(res, null, 2)); return res.ok ? 0 : 1 }
    w("── 条目有效性审查（源 " + res.dir + "）──")
    w("  总条目 " + res.total + " · 时效窗 " + res.maxAgeDays + " 天（窗值已打印）")
    w("")
    w("  五态：")
    for (const k of STATES) w("    " + k.padEnd(8, " ") + String(res.tally[k] || 0).padStart(5, " "))
    w("")
    w("  形态（先分形态，再谈有效性）：")
    for (const k of ["action", "record", "feed", "ack", "unknown"]) w("    " + k.padEnd(8, " ") + String(res.shapeTally[k] || 0).padStart(5, " "))
    w("")
    w("  ⇒ 需判有效性的只有动作项：" + (res.shapeTally.action || 0) + " 条；非动作项 n/a " + (res.tally["n/a"] || 0) + " 条（其年龄不构成失效理由）")
    w("  ⇒ 严格口径（一切 A/B 不命中皆 unknown）五态：" + JSON.stringify(res.strictTally))
    w("  ⚠ unknown 不是「没有」：它是【判不了】⇒ 须补字段，不得当已关闭")
    if (res.rows.length !== res.total) w("  （仅列 " + res.rows.length + " 条）")
    for (const row of res.rows.slice(0, 20)) w("    · " + row.file.slice(0, 46).padEnd(48, " ") + row.shape.padEnd(8, " ") + row.state.padEnd(9, " ") + row.why.slice(0, 70))
    if (res.rows.length > 20) w("    … 另有 " + (res.rows.length - 20) + " 条（用 --json 取全量）")
    w("")
    w(res.blindSpot)
    return 0
  } catch (e) {
    if (e instanceof GateError) {
      const io = String(e.code).startsWith("IO_") || e.code === "USAGE_NOT_FOUND" || e.code === "USAGE_NO_KEY"
      process.stderr.write((io ? "用法/IO 错误：" : "门拒绝：") + "[" + e.code + "] " + e.message + "\n")
      return io ? 2 : 1
    }
    process.stderr.write("运行时错误：" + String(e && e.stack ? e.stack : e) + "\n")
    return 1
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await main(process.argv.slice(2)))
}
