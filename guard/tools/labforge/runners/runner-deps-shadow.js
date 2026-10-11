"use strict";
/**
 * runner-deps-shadow.js v1.0.0 — 遮蔽包回归 runner（labforge）
 *
 * 守护考古 M1（27 遮蔽包事故）：检测 profile node_modules 里遮蔽 runtime 的 @deepseek-ai 旧包。
 * 调用 macmini guard-check-deps（SSH 只读）→ 归一化判定"真实遮蔽数"（排除 .bak/.pnpmcopy 备份残留）。
 *
 * 产物: shadowCount / hasRealShadow / backupResidue / verdict
 */
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");

const args = { jsonOut: null };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--json-out=")) args.jsonOut = a.split("=")[1];
}
const HOST = process.env.LABFORGE_MACMINI || "coreyleung@192.168.1.28";

function ssh(cmd) {
  try {
    return execFileSync("ssh", ["-o", "BatchMode=yes", HOST, `export PATH=/usr/bin:/bin:/usr/sbin:/opt/homebrew/bin; ${cmd}`], { encoding: "utf8", timeout: 60000 }).trim();
  } catch (e) { return ""; }
}

const out = { ok: false };
try {
  // 真实遮蔽 = profile 有裸名目录且 runtime 版本不同（备份残留不算）
  const probe = ssh(`cd ~/.dsh/profiles/web/node_modules/@deepseek-ai && for d in */; do n="\${d%/}"; case "$n" in *.bak-*|*.pnpmcopy-*) ;; *) echo "$n";; esac; done`);
  const bareDirs = probe ? probe.split("\n").filter(Boolean) : [];
  // 对比 runtime 同名包版本
  let realShadow = 0;
  const shadows = [];
  for (const pkg of bareDirs) {
    const pv = ssh(`node -e "try{console.log(require('/Users/coreyleung/.dsh/profiles/web/node_modules/@deepseek-ai/${pkg}/package.json').version)}catch(e){console.log('?')}"`).trim();
    const rv = ssh(`node -e "try{console.log(require('/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/${pkg}/package.json').version)}catch(e){console.log('?')}"`).trim();
    if (pv && rv && pv !== rv) { realShadow++; shadows.push({ pkg, profile: pv, runtime: rv }); }
  }
  out.bareDirs = bareDirs.length;
  out.shadowCount = realShadow;
  out.hasRealShadow = realShadow > 0;
  out.shadows = shadows.slice(0, 10);
  out.verdict = realShadow === 0 ? "无真实遮蔽（备份残留已排除）" : `发现 ${realShadow} 个真实遮蔽包`;
  out.ok = true;
} catch (e) { out.error = String(e).slice(0, 200); }
if (args.jsonOut) fs.writeFileSync(args.jsonOut, JSON.stringify(out, null, 2));
console.log(JSON.stringify({ shadowCount: out.shadowCount, hasRealShadow: out.hasRealShadow, bareDirs: out.bareDirs, verdict: out.verdict }, null, 2));
