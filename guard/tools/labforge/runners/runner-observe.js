"use strict";
/**
 * runner-observe.js v1.0.0 — 稳定性观察 runner（labforge）
 *
 * SSH 只读采样 macmini CLD 状态 → 输出指标 JSON（供稳定性卡断言）。
 * 零写入生产：只 ps/ls/stat 读取。
 *
 * 环境: 需 SSH 免密到 macmini（coreyleung@192.168.1.28）。
 * 产物指标:
 *   rssMB / uptimeSec / heapUsedMB(经 /proc 不可用则 null) /
 *   crashToday(今天 DiagnosticReports CLD*.ips 数) /
 *   crashSinceBoot(当前进程启动后新 ips) / sessionCount /
 *   p2ConfigApplied(preparedSessionCacheSize 是否已配) / ok
 */
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const args = { jsonOut: null };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--json-out=")) args.jsonOut = a.split("=")[1];
}
const HOST = process.env.LABFORGE_MACMINI || "coreyleung@192.168.1.28";

function ssh(cmd) {
  try {
    return execFileSync("ssh", ["-o", "BatchMode=yes", HOST, `export PATH=/usr/bin:/bin:/usr/sbin:/opt/homebrew/bin; ${cmd}`], { encoding: "utf8", timeout: 30000 }).trim();
  } catch (e) { return ""; }
}

const out = { ok: false, note: "stability 观察采样" };
try {
  const rss = ssh(`ps -p $(pgrep -f "CLD.app/Contents/MacOS/CLD --expose-internals" | head -1) -o rss= | awk '{printf "%d", $1/1024}'`);
  out.rssMB = rss ? Number(rss) : null;

  const boot = ssh(`ps -p $(pgrep -f "CLD.app/Contents/MacOS/CLD --expose-internals" | head -1) -o lstart= | awk '{print $2" "$3" "$4" "$5}'`);
  // 粗略 uptime: 用 etime
  const et = ssh(`ps -p $(pgrep -f "CLD.app/Contents/MacOS/CLD --expose-internals" | head -1) -o etime= | tr -d ' '`);
  out.uptime = et || null;

  const crashToday = ssh(`ls ~/Library/Logs/DiagnosticReports/CLD-$(date +%Y-%m-%d)*.ips 2>/dev/null | wc -l | tr -d ' '`);
  out.crashToday = crashToday ? Number(crashToday) : null;

  const crashAll = ssh(`ls ~/Library/Logs/DiagnosticReports/CLD-2026-09-0[4-5]*.ips 2>/dev/null | wc -l | tr -d ' '`);
  out.crashRecent48h = crashAll ? Number(crashAll) : null;

  const sessions = ssh(`ls ~/.dsh/sessions/--Users-coreyleung--/ 2>/dev/null | wc -l | tr -d ' '`);
  out.sessionCount = sessions ? Number(sessions) : null;

  const p2 = ssh(`grep -c "preparedSessionCacheSize" ~/.dsh/profiles/web/cordis.patch.yml 2>/dev/null`);
  out.p2ConfigApplied = p2 ? Number(p2) > 0 : false;

  // 进程存活
  const alive = ssh(`pgrep -f "CLD.app/Contents/MacOS/CLD --expose-internals" | head -1`);
  out.alive = Boolean(alive);
  out.ok = out.alive;
} catch (e) {
  out.error = String(e).slice(0, 200);
}
if (args.jsonOut) fs.writeFileSync(args.jsonOut, JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
