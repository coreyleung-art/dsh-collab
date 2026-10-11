"use strict";
/**
 * runner-perf.js v1.0.0 — 性能对比类实验 runner（labforge 通用）
 *
 * 对比"全量解码(full)" vs "帧索引尾部窗口(tail)" 的耗时与解码量（P2-1 帧索引 POC 沉淀）。
 * 对每个输入 .zstd 会话副本：全量解压全部帧 vs 只解尾部 N 帧 → 输出指标供卡片断言。
 *
 * 参数:
 *   <file1>...            会话文件（可多个，逐个出指标）
 *   --tail-frames=N       尾部窗口帧数（默认 200）
 *   --json-out=<path>     结果输出
 * 产物指标(每文件 + 聚合):
 *   perf.<basename>.fullMs / tailMs / speedup / tailDecodedPct
 */
const fs = require("node:fs");
const path = require("node:path");
const { zstdDecompressSync } = require("node:zlib");

const args = { files: [], tailFrames: 200, jsonOut: null };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--json-out=")) args.jsonOut = a.split("=")[1];
  else if (a.startsWith("--tail-frames=")) args.tailFrames = parseInt(a.split("=")[1], 10);
  else if (a.startsWith("--")) { /* ignore */ }
  else args.files.push(a);
}
if (!args.files.length) { console.error("用法: runner-perf.js <会话副本...> [--tail-frames=200]"); process.exit(2); }

function scanZstdFrames(buffer) {
  const frames = []; let offset = 0;
  while (offset < buffer.length) {
    const start = offset;
    if (buffer.length - offset < 4) return { frames };
    if (buffer.readUInt32LE(offset) !== 0xfd2fb528) throw new Error("bad magic@" + offset);
    offset += 4;
    const d = buffer.readUInt8(offset); offset += 1;
    const cs = d >>> 6, single = (d & 32) !== 0, ck = (d & 4) !== 0, df = d & 3, db = df === 3 ? 4 : df;
    const cb = cs === 0 ? (single ? 1 : 0) : 1 << cs;
    offset += (single ? 0 : 1) + db + cb;
    for (;;) {
      if (buffer.length - offset < 3) return { frames };
      const bh = buffer.readUIntLE(offset, 3); offset += 3;
      const last = (bh & 1) !== 0, type = (bh >>> 1) & 3, size = bh >>> 3;
      offset += (type === 1 ? 1 : size);
      if (last) break;
    }
    if (ck) offset += 4;
    frames.push({ start, end: offset });
  }
  return { frames };
}

function decodeRange(buf, frames, start, end) {
  let bytes = 0, count = 0;
  const t0 = performance.now();
  for (let i = start; i < end; i++) {
    const p = zstdDecompressSync(buf.subarray(frames[i].start, frames[i].end));
    bytes += p.length; count++;
  }
  return { ms: performance.now() - t0, bytes, count };
}

const out = { sample: args.files.map((f) => path.basename(f)).join("+"), files: args.files.length, tailFrames: args.tailFrames, perf: {} };
const perFile = [];
for (const file of args.files) {
  const buf = fs.readFileSync(file);
  const { frames } = scanZstdFrames(buf);
  // 预热
  decodeRange(buf, frames, 0, Math.min(frames.length, 50));
  // full: 全量解码
  const full = decodeRange(buf, frames, 0, frames.length);
  // tail: 只解尾 N 帧（多轮取中位降噪）
  const tailStart = Math.max(0, frames.length - args.tailFrames);
  const tailRuns = [];
  for (let i = 0; i < 3; i++) tailRuns.push(decodeRange(buf, frames, tailStart, frames.length).ms);
  const tailMs = tailRuns.sort((a, b) => a - b)[1];
  const name = path.basename(file).replace(/\.zstd$/, "").replace(/\./g, "_");
  const entry = {
    name,
    sizeMB: +(buf.length / 1048576).toFixed(2),
    frames: frames.length,
    fullMs: +full.ms.toFixed(2),
    tailMs: +tailMs.toFixed(2),
    speedup: +(full.ms / Math.max(tailMs, 0.01)).toFixed(1),
    tailDecodedPct: +(((frames.length - tailStart) / frames.length) * 100).toFixed(3),
  };
  perFile.push(entry);
  out.perf[`${name}.fullMs`] = entry.fullMs;
  out.perf[`${name}.tailMs`] = entry.tailMs;
  out.perf[`${name}.speedup`] = entry.speedup;
  out.perf[`${name}.tailDecodedPct`] = entry.tailDecodedPct;
}
// 聚合
out.maxSpeedup = Math.max(...perFile.map((p) => p.speedup));
out.minTailMs = Math.min(...perFile.map((p) => p.tailMs));
out.maxFullMs = Math.max(...perFile.map((p) => p.fullMs));
out.perFile = perFile;
out.note = "perf 类: fullMs=全量解码 tailMs=尾部窗口解码 speedup=加速比 (P2-1 帧索引)";

if (args.jsonOut) fs.writeFileSync(args.jsonOut, JSON.stringify(out, null, 2));
console.log(JSON.stringify({ maxSpeedup: out.maxSpeedup, minTailMs: out.minTailMs, maxFullMs: out.maxFullMs, perFile: perFile.map((p) => ({ name: p.name, frames: p.frames, fullMs: p.fullMs, tailMs: p.tailMs, speedup: p.speedup })) }, null, 2).slice(0, 1500));
