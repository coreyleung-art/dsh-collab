// dsh-plugin-guard — CLD/DSH 操作治理工具面 v0.2（五道闸 agent 化 + P0 官方预查 + 健康检查 + 报告）
// 暴露工具：guard_doc_check(P0) / guard_check_writable(P1) / guard_backup(P2) / guard_version_check(P3)
//           guard_deps_scan(P4) / cld_health_check(P5) / session_recovery_check(P6)
//           brand_plugin_scaffold(P7) / repair_report(P8)
import { readFileSync, copyFileSync, existsSync, mkdirSync, readdirSync, unlinkSync, lstatSync, writeFileSync, appendFileSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { homedir } from "node:os";
import { defineTool } from "@deepseek-ai/dsh-tools";

export const name = "guard";
export const inject = ["tools"];

// ---------------- 常量 ----------------
const GUARD_DIR = join(homedir(), "dsh-collab", "guard");
const BACKUP_DIR = join(GUARD_DIR, "backups");
const STATE_FILE = join(GUARD_DIR, "gate-state.json");
const MIRROR_ROOT = join(homedir(), "tech-research"); // 官方文档镜像（MBP 有；mini 可走 --web）
const CLD_LOG_DIR = join(homedir(), ".cld", "logs");
const SESSIONS_DIR = join(homedir(), ".dsh", "sessions");
const KEEP_GOOD = 2;
const PROFILE_NM = join(homedir(), ".dsh", "profiles", "web", "node_modules", "@deepseek-ai");
const RUNTIME_NM = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai";
const DOMAIN_DIRS = { dsh: "dsh-docs", electron: "electron-docs", swift: "swift-docs" };

// ---------------- 不可写清单 ----------------
const FORBIDDEN_PATTERNS = [
  "/Applications/CLD\\.app/Contents/Frameworks/Electron Framework\\.framework/",
  "/Applications/CLD\\.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools/lib/",
  "\\.dsh/profiles/web/node_modules/\\.pnpm/",
  "com\\.user\\.auto-index\\.plist",
  "/Applications/CLD\\.app/Contents/Resources/app\\.asar$",
  "\\.dsh/profiles/web/package\\.json$",
  "\\.dsh/profiles/web/cordis\\.patch\\.yml$",
  "\\.dsh/profiles/web/pnpm-lock\\.yaml$",
  "\\.dsh/profiles/web/pnpm-workspace\\.yaml$",
  "dsh-runtime/runtime/node_modules/@deepseek-ai/",
];

// ---------------- 基础工具函数 ----------------
function isForbidden(path) {
  return FORBIDDEN_PATTERNS.some((pat) => new RegExp(pat).test(String(path)));
}

function pkgVersion(pkgDir) {
  try {
    return JSON.parse(readFileSync(join(pkgDir, "package.json"), "utf8")).version || "?";
  } catch {
    return "?";
  }
}

function expand(p) {
  return p.startsWith("~") ? join(homedir(), p.slice(1)) : p;
}

function readJson(fp, fallback) {
  try {
    return JSON.parse(readFileSync(fp, "utf8"));
  } catch {
    return fallback;
  }
}

function safeWrite(fp, data) {
  mkdirSync(dirname(fp), { recursive: true });
  writeFileSync(fp, data, { mode: 0o600 });
}

function nowIso() {
  return new Date().toISOString();
}

// ---------------- P0: 官方标准预查（门锁 v2 新增） ----------------
function inferDomain(target) {
  const t = String(target || "").toLowerCase();
  if (/\.swift$|swift/.test(t)) return "swift";
  if (/electron|app\.asar|CLD\.app|framework|node_options|crashreport|heap/.test(t)) return "electron";
  return "dsh";
}

function norm(s) {
  return String(s).toLowerCase().replace(/[\s_-]+/g, "");
}

function searchMirror(domain, topic, limit = 10) {
  const d = join(MIRROR_ROOT, DOMAIN_DIRS[domain] || "");
  if (!existsSync(d)) return [];
  const tokens = String(topic).toLowerCase().split(/[\s_-]+/).filter(Boolean);
  const normTokens = tokens.map(norm);
  const hits = [];
  const stack = [d];
  while (stack.length && hits.length < limit) {
    const dir = stack.pop();
    let entries = [];
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      if (e.name.startsWith(".") || e.name === "node_modules") continue;
      const fp = join(dir, e.name);
      if (e.isDirectory()) { stack.push(fp); continue; }
      if (!/\.(md|mdx|html)$/i.test(e.name)) continue;
      const rel = fp.slice(d.length + 1);
      const base = norm(e.name);
      if (normTokens.every((nt) => base.includes(nt))) { hits.push(rel); if (hits.length >= limit) break; continue; }
      try {
        const head = norm(readFileSync(fp, "utf8").slice(0, 6000));
        if (normTokens.every((nt) => head.includes(nt))) hits.push(rel);
      } catch { /* skip */ }
      if (hits.length >= limit) break;
    }
  }
  return hits;
}

function doDocCheck(args) {
  const topic = String(args?.topic || "").trim();
  const target = String(args?.target || topic || "");
  const web = String(args?.web || "").trim();
  if (!topic && !target) return { error: "需传 topic（或 target+--topic 语义）" };
  const domain = inferDomain(target || topic);
  const hits = searchMirror(domain, topic || target);
  // 镜像新鲜度（目录 birthtime）
  const mdir = join(MIRROR_ROOT, DOMAIN_DIRS[domain] || "");
  let ageDays = null;
  try {
    const st = statSync(mdir);
    ageDays = Math.round((Date.now() - (st.birthtimeMs || st.mtimeMs)) / 86400000 * 10) / 10;
  } catch { /* no mirror */ }
  const stale = ageDays !== null && ageDays > 14;
  const ok = hits.length > 0 || Boolean(web);
  if (ok) {
    const st = readJson(STATE_FILE, {});
    const checks = st._doc_checks || [];
    checks.push({
      ts: nowIso(), ts_epoch: Date.now() / 1000, target, topic, domain,
      mirror_hits: hits.length, hit_files: hits.slice(0, 10),
      mirror_age_days: ageDays, mirror_stale: stale, web_evidence: web || null,
      note: hits.length ? `本地镜像命中 ${hits.length} 个官方文档` : "web 补证",
    });
    st._doc_checks = checks.slice(-40);
    safeWrite(STATE_FILE, JSON.stringify(st, null, 1));
  }
  return {
    ok,
    domain,
    topic: topic || target,
    mirror: mdir && existsSync(mdir) ? mdir : null,
    mirror_age_days: ageDays,
    mirror_stale: stale,
    mirror_hits: hits.length,
    hit_files: hits.slice(0, 5),
    web_evidence: web || null,
    evidence_recorded: ok,
    hint: ok ? "P0 证据已写入 gate-state.json（24h 有效）" : "无命中且无 web 补证：先查官方（本地镜像或 --web）再动手",
  };
}


// ---------------- 合规编排: guard_compliance (五道闸一键) ----------------
function doComplianceGate(args) {
  const target = String(args?.target || "").trim();
  const topic = String(args?.topic || target || "").trim();
  const operation = String(args?.operation || "").trim();
  if (!target) return { error: "需传 target（目标路径）" };
  const gates = [];
  // P2 非红线
  const w = doCheckWritable([target]);
  const forbidden = w.blocked > 0;
  gates.push({ gate: "P2 非红线", ok: !forbidden, detail: forbidden ? w.results[0].reason : "通过(非红线/受限区)" });
  // P0 官方预查（topic 有才跑; 无则提示必填）
  let p0 = null;
  if (topic) {
    p0 = doDocCheck({ topic, target, web: args?.web });
    gates.push({ gate: "P0 官方预查", ok: !!p0.ok, detail: p0.hint || "" });
  } else {
    gates.push({ gate: "P0 官方预查", ok: false, detail: "缺 topic：需先 guard_doc_check 主题(如 session persistence)" });
  }
  // P1 备份
  let p1 = null;
  if (args?.backup !== false) {
    p1 = doBackup([target]);
    const okBak = p1.backups?.every((b) => b.ok);
    gates.push({ gate: "P1 备份", ok: !!okBak, detail: okBak ? p1.backups[0].backup : (p1.backups?.[0]?.error || "备份失败") });
  } else {
    gates.push({ gate: "P1 备份", ok: false, detail: "backup=false 跳过(应显式确认已有备份)" });
  }
  // P4 沙箱提示(编排器无法代跑外部进程, 提示人工/模型先沙箱)
  const sbox = args?.sbox_verified === true;
  gates.push({ gate: "P4 沙箱验证", ok: sbox, detail: sbox ? "已确认沙箱验证(/tmp 副本语法通过)" : "需在 /tmp 副本验证语法后再真改(--sbox_verified=true 确认)" });
  // P5 有界
  gates.push({ gate: "P5 操作有界", ok: args?.new_task === true, detail: args?.new_task ? "已声明 --new-task(审计通道)" : "建议 --new_task=true 声明立项(防试错计数)" });
  // pre-mortem
  const pmOk = args?.premortem === true;
  gates.push({ gate: "pre-mortem 反例", ok: pmOk, detail: pmOk ? "已确认 Q0-Q4 反例检查" : "建议先 guard_premortem 生成反例检查记录" });
  const allOk = gates.every((g) => g.ok);
  return {
    target, operation: operation || "write",
    gates,
    safe_edit: allOk,
    verdict: allOk ? "safe_edit 可构造 → 允许执行" : "前提不满足 → 操作被拒绝(类型错误); 补齐失败门后重试",
    evidence: {
      p0_recorded: !!p0?.evidence_recorded,
      backup_file: p1?.backups?.[0]?.backup || null,
    },
  };
}

// ---------------- 反例检查: guard_premortem (Q0-Q4 模板) ----------------
function doPreMortem(args) {
  const target = String(args?.target || "").trim();
  const change = String(args?.change || "").trim();
  if (!target || !change) return { error: "需传 target 与 change(改什么)" };
  return {
    target, change,
    questions: [
      { q: "Q0 对系统的理解基于哪份官方文档? 是最新的吗?(P0 锚点)", a: args?.q0 || "" },
      { q: "Q1 什么会让这次修改把 CLD 搞崩?(类型错/依赖缺/路径错)", a: args?.q1 || "" },
      { q: "Q2 什么会让会话消失/历史读不了?(版本遮蔽/服务 pending)", a: args?.q2 || "" },
      { q: "Q3 怎么知道改坏了?(C1-C7 哪项先报警)", a: args?.q3 || "" },
      { q: "Q4 回滚点在哪?(.bak-good-* 路径)", a: args?.q4 || "" },
    ],
    complete: [args?.q0, args?.q1, args?.q2, args?.q3, args?.q4].every((x) => String(x || "").trim().length > 0),
    hint: "逐项作答后 complete=true; 将 Q4 回滚路径记入操作记录",
  };
}

// ---------------- P1-P4: 既有五道闸 ----------------
function doCheckWritable(paths) {
  const results = paths.map((p) => {
    const forb = isForbidden(p);
    return { path: p, writable: !forb, forbidden: forb, reason: forb ? "命中不可写清单（红线）" : "" };
  });
  return { results, blocked: results.filter((r) => r.forbidden).length };
}

function doBackup(paths) {
  mkdirSync(BACKUP_DIR, { recursive: true });
  const ts = new Date().toISOString().replace(/[:T]/g, "-").slice(0, 15);
  const made = [];
  for (const p of paths) {
    const full = expand(p);
    if (!existsSync(full)) { made.push({ path: p, ok: false, error: "不存在" }); continue; }
    const safe = full.replace(/^\//, "").replace(/\//g, "__");
    let existing = [];
    try { existing = readdirSync(BACKUP_DIR).filter((f) => f.startsWith(safe + ".bak-good-")); } catch { /* first */ }
    existing.sort().slice(0, Math.max(0, existing.length - KEEP_GOOD + 1)).forEach((f) => {
      try { unlinkSync(join(BACKUP_DIR, f)); } catch { /* ignore */ }
    });
    const dest = join(BACKUP_DIR, `${safe}.bak-good-${ts}`);
    try {
      copyFileSync(full, dest);
      made.push({ path: full, ok: true, backup: dest });
    } catch (e) {
      made.push({ path: full, ok: false, error: String(e) });
    }
  }
  return { backups: made };
}

function doVersionCheck(pkgs) {
  return { versions: pkgs.map((p) => {
    const rdir = join(RUNTIME_NM, p);
    return { pkg: p, local: existsSync(rdir) ? pkgVersion(rdir) : "?" };
  }) };
}

function doDepsScan() {
  if (!existsSync(PROFILE_NM)) return { total: 0, mismatches: [], count: 0 };
  const mismatches = [];
  let total = 0;
  for (const name of readdirSync(PROFILE_NM)) {
    if (/\.(bak|pnpmcopy)/.test(name)) continue;
    const pdir = join(PROFILE_NM, name);
    let st;
    try { st = lstatSync(pdir); } catch { continue; }
    if (!st.isDirectory() || st.isSymbolicLink()) continue;
    total += 1;
    const pv = pkgVersion(pdir);
    const rdir = join(RUNTIME_NM, name);
    const rv = existsSync(rdir) ? pkgVersion(rdir) : null;
    if (rv === null || pv !== rv) mismatches.push({ name, profile: pv, runtime: rv ?? "runtime无" });
  }
  return { total, mismatches, count: mismatches.length };
}

// ---------------- P5: cld_health_check（一键健康检查 C1-C7 概览） ----------------
function countSessions() {
  // 真实结构: ~/.dsh/sessions/<workspace>/<uuid|session-uuid>/session.jsonl.zstd
  // 与 doctor healthy 语义一致：统计递归一层的 session.jsonl.zstd
  let total = 0, workspaces = 0;
  const wsDetail = [];
  try {
    for (const ws of readdirSync(SESSIONS_DIR)) {
      if (ws.startsWith(".")) continue;
      const wdir = join(SESSIONS_DIR, ws);
      if (!lstatSync(wdir).isDirectory()) continue;
      workspaces += 1;
      let wsCount = 0;
      try {
        for (const sess of readdirSync(wdir)) {
          const sdir = join(wdir, sess);
          if (!lstatSync(sdir).isDirectory()) continue;
          if (existsSync(join(sdir, "session.jsonl.zstd"))) { wsCount += 1; total += 1; }
        }
      } catch { /* unreadable */ }
      wsDetail.push({ workspace: ws, sessions: wsCount });
    }
  } catch { /* dir 不存在 */ }
  return { total, workspaces, wsDetail };
}

function doHealthCheck() {
  const out = { ts: nowIso(), checks: {} };
  // C1 boot_ok: exit-marker 上次是否 clean
  const em = readJson(join(CLD_LOG_DIR, "exit-marker.json"), null);
  out.checks.C1_boot = em ? { ok: em.cleanExit !== false || em.reason !== "dsh-crash", marker: em.reason || "clean", cleanExit: em.cleanExit } : { ok: false, error: "无 exit-marker（CLD 未跑过？）" };
  // 心跳新鲜度（C2 web 侧间接）
  const hb = readJson(join(CLD_LOG_DIR, "heartbeat.json"), null);
  if (hb) {
    const ageSec = Math.round((Date.now() - (hb.ts || 0)) / 1000);
    out.checks.C2_heartbeat = { ok: ageSec < 180, age_sec: ageSec, pid: hb.pid };
  } else out.checks.C2_heartbeat = { ok: false, error: "无 heartbeat.json" };
  // C3 data_ok: 会话目录计数（doctor 语义）
  const { total: sessionCount, workspaces } = countSessions();
  out.checks.C3_data = { ok: sessionCount > 0, sessions_on_disk: sessionCount, workspaces };
  // C7 version_ok
  const scan = doDepsScan();
  out.checks.C7_version = { ok: scan.count === 0, mismatches: scan.mismatches.slice(0, 5), count: scan.count };
  // memory-trend 尾部（若存在）
  try {
    const lines = readFileSync(join(CLD_LOG_DIR, "memory-trend.json"), "utf8").trim().split("\n");
    if (lines.length) out.memory_last = readJson(join(CLD_LOG_DIR, "memory-trend.json"), null) || JSON.parse(lines[lines.length - 1]);
  } catch { /* 尚无采样 */ }
  out.all_ok = Object.values(out.checks).every((c) => c.ok);
  return out;
}

// ---------------- P6: session_recovery_check（会话/历史可读性） ----------------
function doSessionRecoveryCheck() {
  const out = { ts: nowIso(), workspaces: [], runtime: {} };
  // runtime 是否具备 dsh-session 解析能力
  for (const pkg of ["dsh-session", "dsh-session-query-sqlite", "dsh-session-persistence-jsonl"]) {
    out.runtime[pkg] = existsSync(join(RUNTIME_NM, pkg)) ? pkgVersion(join(RUNTIME_NM, pkg)) : null;
  }
  // 结构: ~/.dsh/sessions/<workspace>/<session-id>/session.jsonl.zstd
  let total = 0, empty = 0, missingJsonl = 0;
  try {
    for (const ws of readdirSync(SESSIONS_DIR)) {
      if (ws.startsWith(".")) continue;
      const wdir = join(SESSIONS_DIR, ws);
      let st;
      try { st = lstatSync(wdir); } catch { continue; }
      if (!st.isDirectory()) continue;
      let wsCount = 0, wsEmpty = 0, wsMissing = 0, wsBytes = 0;
      for (const sess of readdirSync(wdir)) {
        const sdir = join(wdir, sess);
        let sst;
        try { sst = lstatSync(sdir); } catch { continue; }
        if (!sst.isDirectory()) continue;
        const jf = join(sdir, "session.jsonl.zstd");
        if (!existsSync(jf)) { wsMissing += 1; missingJsonl += 1; continue; }
        wsCount += 1; total += 1;
        const sz = statSync(jf).size;
        wsBytes += sz;
        if (sz === 0) { wsEmpty += 1; empty += 1; }
      }
      out.workspaces.push({
        workspace: ws, count: wsCount,
        total_mb: Math.round(wsBytes / 1048576 * 10) / 10,
        empty_files: wsEmpty, missing_jsonl: wsMissing,
      });
    }
  } catch { /* none */ }
  out.total_sessions = total;
  out.empty_files = empty;
  out.missing_jsonl = missingJsonl;
  // 关键判定：runtime 有解析器 + 盘上有非空文件 = 可恢复
  const resolverOk = out.runtime["dsh-session"] || out.runtime["dsh-session-persistence-jsonl"];
  out.recoverable = Boolean(resolverOk && total > 0 && empty === 0 && missingJsonl === 0);
  out.verdict = out.recoverable
    ? `✅ 会话可恢复：runtime 解析器在位，${total} 个会话文件健康（doctor 基线同口径）`
    : (total === 0 ? "⚠️ 磁盘无会话文件（空库，非故障）" : `❌ 会话异常：empty=${empty} missing=${missingJsonl} — 查解析器/遮蔽/损坏文件`);
  return out;
}

// ---------------- P7: brand_plugin_scaffold（品牌插件骨架生成） ----------------
function doBrandScaffold(name) {
  const clean = String(name || "").replace(/[^a-zA-Z0-9-_]/g, "");
  if (!clean) return { error: "需传合法插件名（如 my-brand → dsh-plugin-my-brand）" };
  const pkgName = clean.startsWith("dsh-plugin-") ? clean : `dsh-plugin-${clean}`;
  const id = clean.replace(/^dsh-plugin-/, "");
  const dir = join(homedir(), pkgName);
  if (existsSync(dir)) return { error: `目录已存在: ${dir}（勿覆盖，先 backup）` };
  const files = {
    "package.json": JSON.stringify({
      name: pkgName, version: "0.1.0", type: "module", main: "lib/index.js",
      exports: { ".": { default: "./lib/index.js" }, "./cordis.patch.yml": "./cordis.patch.yml", "./package.json": "./package.json" },
      dsh: { bundle: { patch: "./cordis.patch.yml" } },
      license: "MIT",
    }, null, 2) + "\n",
    "cordis.patch.yml": `# ${pkgName} bundle patch: 插入宿主行\n- insert:\n    - id: ${id}\n      name: ${pkgName}\n`,
    "lib/index.js": `// ${pkgName} — host 端入口\n// host 工具示例：defineTool 注册（记得每个 tool 带 output: makeOutput()）\nexport const name = "${id}";\nexport const inject = ["tools"];\n\nimport { defineTool } from "@deepseek-ai/dsh-tools";\n\nfunction makeOutput() {\n  return {\n    schema: { type: "json" },\n    render: (_a, v) => [{ type: "text", text: JSON.stringify(v, null, 2) }],\n  };\n}\n\nexport function apply(ctx) {\n  const tools = [\n    defineTool({\n      name: "${id}_ping",\n      description: "连通性自检：返回 ok。",\n      parameters: {},\n      output: makeOutput(),\n      execute() { return { ok: true, plugin: "${pkgName}" }; },\n    }),\n  ];\n  for (const t of tools) ctx.effect(() => ctx.tools.register(t));\n}\n`,
  };
  for (const [rel, content] of Object.entries(files)) {
    const fp = join(dir, rel);
    mkdirSync(dirname(fp), { recursive: true });
    writeFileSync(fp, content, { mode: 0o600 });
  }
  return { ok: true, dir, files: Object.keys(files), next: [`dsh plugin add ${pkgName}（或手改 profile deps+bundles）`, "需 node_modules/@deepseek-ai/dsh-tools symlink（host 工具插件）"] };
}

// ---------------- P8: repair_report（修复报告生成+黑板投递） ----------------
async function doRepairReport(args) {
  const node = String(args?.node || "mac-mini");
  const title = String(args?.title || "");
  const body = args?.body;
  if (!title || !body) return { error: "需传 title + body(对象)" };
  const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
  const slug = title.replace(/[^\x00-\x7f]/g, "").replace(/[^\w-]/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "repair";
  const value = { title, node, ts, from: "mbp-ops", ...(typeof body === "object" ? body : { body }) };
  // 读黑板 token（~/.dsh/.env 或环境）
  let token = "";
  try {
    const envRaw = readFileSync(join(homedir(), ".dsh", ".env"), "utf8");
    const m = envRaw.match(/^BLACKBOARD_TOKEN=(.*)$/m);
    if (m) token = m[1].trim().replace(/^["']|["']$/g, "");
  } catch { /* no env */ }
  const BB = process.env.BB || "http://127.0.0.1:8792";
  const key = `notes/${node}/repair-report-${ts}-${slug}`;
  try {
    const resp = await fetch(`${BB}/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Writer": "mbp-ops", ...(token ? { "X-Blackboard-Token": token } : {}) },
      body: JSON.stringify(value),
    });
    if (!resp.ok) {
      const txt = await resp.text().catch(() => "");
      return { ok: false, key, title, node, http: resp.status, error: txt.slice(0, 200) };
    }
    const j = await resp.json().catch(() => ({}));
    return { ok: true, key, title, node, seq: j.seq ?? null, note: `已投递 ${BB}/${key}` };
  } catch (e) {
    return { ok: false, key, title, node, error: String(e).slice(0, 300) };
  }
}

// ---------------- 工具定义（agent-way 模式） ----------------
function makeOutput() {
  return {
    schema: { type: "json" },
    render: (_args, value) => [{ type: "text", text: JSON.stringify(value, null, 2) }],
  };
}

export function apply(ctx) {
  const tools = [
    defineTool({
      name: "guard_compliance",
      description: "一键 Lean4 合规审查编排：输入目标路径+操作主题，自动串 P2 红线→P0 官方预查→P1 备份→P4 沙箱确认→P5 有界→pre-mortem，输出五道闸矩阵与 safe_edit 结论。受限区写操作(如 cordis.patch.yml/package.json/app.asar)前调用。",
      parameters: {
        target: { type: "string", description: "目标路径(如 ~/.dsh/profiles/web/cordis.patch.yml)" },
        topic: { type: "string", description: "P0 预查主题(如 session persistence / cordis patch config)" },
        operation: { type: "string", description: "操作描述(如 write / patch / replace)" },
        web: { type: "string", description: "可选: 官方来源补证 'url: 结论'(镜像无命中时)" },
        backup: { type: "boolean", description: "默认 true 自动备份; false 跳过(已有备份时)" },
        sbox_verified: { type: "boolean", description: "是否已在 /tmp 副本沙箱验证语法" },
        new_task: { type: "boolean", description: "是否立项新部署任务(审计通道, 建议 true)" },
        premortem: { type: "boolean", description: "是否已做 Q0-Q4 反例检查" },
      },
      output: makeOutput(),
      execute(args) { return doComplianceGate(args || {}); },
    }),
    defineTool({
      name: "guard_premortem",
      description: "pre-mortem 反例检查模板(Q0-Q4)：动手改底层前必答五问——Q0 依据哪份官方文档/Q1 什么会崩/Q2 什么会丢会话/Q3 怎么知道坏了/Q4 回滚点。输出作答记录与 complete 判定。",
      parameters: {
        target: { type: "string", description: "目标路径" },
        change: { type: "string", description: "改动描述(如 覆盖 session-persistence-jsonl config 加 preparedSessionCacheSize)" },
        q0: { type: "string", description: "Q0 答案(官方文档锚点)" },
        q1: { type: "string", description: "Q1 答案(什么会崩)" },
        q2: { type: "string", description: "Q2 答案(什么会丢会话)" },
        q3: { type: "string", description: "Q3 答案(哪项 C 先报警)" },
        q4: { type: "string", description: "Q4 答案(回滚点路径)" },
      },
      output: makeOutput(),
      execute(args) { return doPreMortem(args || {}); },
    }),
    defineTool({
      name: "guard_doc_check",
      description: "P0 官方标准预查：改 CLD/dsh 底层前必跑。在本地官方镜像(~/tech-research)检索主题并留证 gate-state.json(24h 有效)；镜像过期/无命中时用 --web 补官方来源。",
      parameters: {
        topic: { type: "string", description: "查询主题，如 session persistence / node options whitelist" },
        target: { type: "string", description: "可选：目标路径，用于推断领域(electron/dsh/swift)" },
        web: { type: "string", description: "可选：官方来源补证，格式 'url: 结论要点'（本地镜像过期或无命中时必填）" },
      },
      output: makeOutput(),
      execute(args) { return doDocCheck(args); },
    }),
    defineTool({
      name: "guard_check_writable",
      description: "P1 检查路径是否在 CLD/dsh 不可写清单（红线：Electron 二进制/dsh-tools lib/.pnpm/auto-index/app.asar/package.json 等）。任何写操作前必查，命中即拒绝。",
      parameters: {
        paths: { type: "array", items: { type: "string" }, description: "要检查的路径列表（可含 ~）" },
      },
      output: makeOutput(),
      execute(args) {
        const paths = Array.isArray(args?.paths) ? args.paths.map(String) : [];
        if (paths.length === 0) return { error: "需传 paths" };
        return doCheckWritable(paths);
      },
    }),
    defineTool({
      name: "guard_backup",
      description: "P2 写操作前备份目标文件到 ~/dsh-collab/guard/backups（滚动保留最后 2 个 good 态）。改 CLD/dsh 底层文件前必调。",
      parameters: {
        paths: { type: "array", items: { type: "string" }, description: "要备份的路径列表（如 ~/.dsh/profiles/web/package.json）" },
      },
      output: makeOutput(),
      execute(args) {
        const paths = Array.isArray(args?.paths) ? args.paths.map(String) : [];
        if (paths.length === 0) return { error: "需传 paths" };
        return doBackup(paths);
      },
    }),
    defineTool({
      name: "guard_version_check",
      description: "P3 版本校对：查 runtime @deepseek-ai 包版本。改依赖前调用，确认目标版本与 runtime 一致（防遮蔽）。",
      parameters: {
        pkgs: { type: "array", items: { type: "string" }, description: "要查的包名（如 dsh/dsh-tools/dsh-session），省略查 dsh+dsh-tools" },
      },
      output: makeOutput(),
      execute(args) {
        const pkgs = Array.isArray(args?.pkgs) && args.pkgs.length ? args.pkgs.map(String) : ["dsh", "dsh-tools"];
        return doVersionCheck(pkgs);
      },
    }),
    defineTool({
      name: "guard_deps_scan",
      description: "P4 依赖一致性扫描：检测 profile node_modules 里遮蔽 runtime 的 @deepseek-ai 旧包（pnpm 事故根因）。遇版本类 bug 先跑本工具。",
      parameters: {},
      output: makeOutput(),
      execute() { return doDepsScan(); },
    }),
    defineTool({
      name: "cld_health_check",
      description: "P5 一键健康检查：C1 exit-marker 是否 clean / C2 心跳新鲜度 / C3 磁盘会话数 / C7 遮蔽扫描 + 内存趋势尾部。修完必跑，等价 C1-C7 概览。",
      parameters: {},
      output: makeOutput(),
      execute() { return doHealthCheck(); },
    }),
    defineTool({
      name: "session_recovery_check",
      description: "P6 会话/历史可读性验证：检查 runtime 会话解析器在位、磁盘各 workspace 会话文件数/空文件、输出 recoverable 判定（会话消失类故障专用）。",
      parameters: {},
      output: makeOutput(),
      execute() { return doSessionRecoveryCheck(); },
    }),
    defineTool({
      name: "brand_plugin_scaffold",
      description: "P7 生成品牌插件骨架到 ~/dsh-plugin-<name>/（package.json + cordis.patch.yml + lib/index.js 含 ping 工具与 makeOutput 示例）。",
      parameters: {
        name: { type: "string", description: "插件名（如 my-brand → dsh-plugin-my-brand）" },
      },
      output: makeOutput(),
      execute(args) { return doBrandScaffold(args?.name); },
    }),
    defineTool({
      name: "repair_report",
      description: "P8 修复报告生成+黑板投递：写 notes/<node>/repair-report-*（X-Writer + token 自动读取 ~/.dsh/.env）。修复完成后调用留痕。",
      parameters: {
        node: { type: "string", description: "目标节点名，默认 mac-mini" },
        title: { type: "string", description: "报告标题（英文/数字，自动 slug）" },
        body: { type: "object", additionalProperties: true, description: "报告体：{root_cause, fix, verify, artifacts, followups}" },
      },
      output: makeOutput(),
      execute(args) { return doRepairReport(args); },  // async → Promise（框架 await 工具结果）
    }),
  ];
  for (const tool of tools) {
    ctx.effect(() => ctx.tools.register(tool));
  }
}
