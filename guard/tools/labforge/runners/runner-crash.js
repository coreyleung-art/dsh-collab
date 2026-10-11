"use strict";
/**
 * runner-crash.js — 内存崩溃类实验 runner（labforge 通用）
 *
 * 契约：读取输入 .zstd 会话副本 → full/tail 双路径受限 heap 子进程 →
 * 聚合指标输出 JSON（供卡片断言提取）。
 *
 * 参数（来自卡片 data/params）:
 *   <file1> <file2>...   会话文件（多会话叠加）
 *   --heap=512,1024      heap 顶列表
 *   --tail-frames=200    tail 窗口帧数
 *   --clone=true         是否 structuredClone 放大（模拟 adopt）
 *   --json-out=<path>    结果输出路径
 */

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

// ---- 参数 ----
const args = { files: [], heap: [512, 1024], tailFrames: 200, clone: false, jsonOut: null };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--json-out=")) args.jsonOut = a.split("=")[1];
  else if (a.startsWith("--heap=")) args.heap = a.split("=")[1].split(",").map(Number);
  else if (a.startsWith("--tail-frames=")) args.tailFrames = parseInt(a.split("=")[1], 10);
  else if (a.startsWith("--clone=")) args.clone = a.split("=")[1] === "true";
  else if (a.startsWith("--")) { /* ignore unknown */ }
  else args.files.push(a);
}
if (!args.files.length) { console.error("用法: runner-crash.js <会话副本...> [--heap=512,1024]"); process.exit(2); }

const OOM_SIM = path.join(__dirname, "oom-sim.js"); // 复用 memory-crash-lab 的模拟器
if (!fs.existsSync(OOM_SIM)) {
  // 尝试从 memory-crash-lab 复制
  const alt = path.join(__dirname, "..", "..", "..", "..", "poc", "memory-crash-lab", "runner", "oom-sim.js");
  if (fs.existsSync(alt)) fs.copyFileSync(alt, OOM_SIM);
  else { console.error("oom-sim.js 缺失"); process.exit(2); }
}

function runOne(mode, heapMB) {
  const childArgs = ["--expose-gc", `--max-old-space-size=${heapMB}`,
    OOM_SIM, "--multi", args.files.join(","), "--mode", mode,
    "--tail-frames", String(args.tailFrames)];
  if (args.clone) childArgs.push("--clone", "true");
  const r = spawnSync(process.execPath, childArgs, { encoding: "utf8", timeout: 120000 });
  const stdout = (r.stdout || "").trim();
  let sim = null;
  try { sim = stdout ? JSON.parse(stdout.split("\n").filter(Boolean).pop()) : null; } catch {}
  const stderr = (r.stderr || "");
  let outcome = "ok";
  if (r.signal) outcome = `KILLED:${r.signal}`;
  else if (r.status !== 0 && r.status !== 3) outcome = `exit-${r.status}`;
  else if (sim?.outcome === "error") outcome = "error";
  if (/FATAL ERROR|heap out of memory|allocation failed|SIGABRT/i.test(stderr)) outcome = "OOM";
  return {
    mode, heapMB,
    outcome,
    crashed: outcome === "OOM" || outcome.includes("KILLED") || outcome === "error",
    ms: sim?.ms ?? null,
    peakHeapMB: sim?.peakHeapMB ?? null,
    retainedHeapMB: sim?.retainedHeapMB ?? null,
    plaintextMB: sim?.plaintextMB ?? null,
    totalFrames: sim?.totalFrames ?? null,
    detail: stderr.slice(0, 200),
  };
}

// ---- 执行矩阵 ----
const rows = [];
for (const mode of ["full", "tail"]) {
  for (const heapMB of args.heap) {
    rows.push(runOne(mode, heapMB));
  }
}

// ---- 聚合指标（供断言提取） ----
const full = rows.filter((r) => r.mode === "full");
const tail = rows.filter((r) => r.mode === "tail");
const summary = {
  sample: args.files.map((f) => path.basename(f)).join("+"),
  files: args.files.length,
  fileSizeMB: +(fs.statSync(args.files[0]).size / 1048576).toFixed(1),
  tailFrames: args.tailFrames,
  clone: args.clone,
  heaps: args.heap,
  // 断言用: 任意 heap 顶下 full 崩溃？
  fullCrashedAny: full.some((r) => r.crashed),
  fullCrashHeaps: full.filter((r) => r.crashed).map((r) => r.heapMB),
  tailAliveAtCrashHeaps: full.filter((r) => r.crashed).every((fc) => tail.find((t) => t.heapMB === fc.heapMB && !t.crashed)),
  tailPeakAtCrashHeaps: (() => {
    const heaps = full.filter((r) => r.crashed).map((r) => r.heapMB);
    const alive = tail.filter((t) => heaps.includes(t.heapMB) && !t.crashed);
    return alive.length ? Math.max(...alive.map((t) => t.peakHeapMB || 0)) : null;
  })(),
  // 同 heap 顶最大内存比/耗时比（tail 存活且 full 存活处）
  maxMemRatio: (() => {
    let m = 0;
    for (const f of full) {
      const t = tail.find((x) => x.heapMB === f.heapMB);
      if (f.peakHeapMB && t?.peakHeapMB && !f.crashed && !t.crashed) m = Math.max(m, f.peakHeapMB / Math.max(t.peakHeapMB, 0.1));
    }
    return +m.toFixed(1);
  })(),
  maxTimeRatio: (() => {
    let m = 0;
    for (const f of full) {
      const t = tail.find((x) => x.heapMB === f.heapMB);
      if (f.ms && t?.ms && !f.crashed && !t.crashed) m = Math.max(m, f.ms / Math.max(t.ms, 0.1));
    }
    return +m.toFixed(1);
  })(),
  maxFullPeakMB: Math.max(...full.map((r) => r.peakHeapMB || 0)),
  minTailPeakMB: Math.min(...tail.filter((r) => !r.crashed).map((r) => r.peakHeapMB || Infinity)),
  runs: rows,
  note: "crash 类: full=全量物化(现状) tail=帧索引尾部窗口(治理后); crashed 顶需受限heap才复现",
};

if (args.jsonOut) fs.writeFileSync(args.jsonOut, JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2).slice(0, 2000));
