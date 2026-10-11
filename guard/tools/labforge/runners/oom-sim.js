"use strict";
/**
 * oom-sim.js — 内存崩溃实验室 · 单样本单模式模拟器（黑箱子进程）
 *
 * 由 run-lab.js spawn，带 --max-old-space-size=<heapMB> 硬顶。
 * 模拟 runtime 两条路径：
 *   full: readFile 整文件 → 扫帧 → 解压全部帧 → 逐行 JSON.parse → 事件对象驻留
 *         （复现历史 OOM：JS heap 硬顶崩溃 / FATAL ERROR / SIGABRT）
 *   tail: readFile → 扫帧 → 只解尾部 N 帧 → 窗口事件对象驻留（P2-1 治理后）
 *
 * 输出一行 JSON 到 stdout（供父进程解析）；崩溃/被杀时由父进程判定 outcome。
 */

const fs = require("node:fs");
const { zstdDecompressSync } = require("node:zlib");
const v8 = require("node:v8");

// ---- 参数 ----
const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--")) {
    const key = a.slice(2);
    const val = process.argv[i + 1];
    if (val !== undefined && !val.startsWith("--")) { args[key] = val; i++; }
    else args[key] = true;
  }
}
const FILE = args.file;
const MULTI = args.multi ? args.multi.split(",") : (args.files ? args.files.split(",") : null); // 多会话叠加（boot/doctor 场景）
const MODE = args.mode || "full"; // full | tail
const TAIL_FRAMES = parseInt(args["tail-frames"] || "200", 10);
const KEEP_EVENTS = args["keep-events"] !== "false"; // 驻留事件对象（模拟 events 数组常驻）
if (!FILE && !MULTI) { console.error(JSON.stringify({ outcome: "error", error: "no file/multi" })); process.exit(2); }
const CLONE = args.clone === "true";
const EXPAND = args.expand !== "false";
const AMPLIFY = parseInt(args.amplify || "1", 10); // 每事件多视图引用放大（模拟 surface/projection/context 多视图）

// ---- 帧扫描（与 runtime scanZstdFrames 同逻辑的独立移植）----
function scanZstdFrames(buffer) {
  const frames = [];
  let offset = 0;
  while (offset < buffer.length) {
    const start = offset;
    if (buffer.length - offset < 4) return { frames, tornStart: start };
    if (buffer.readUInt32LE(offset) !== 0xfd2fb528) throw new Error("bad magic@" + offset);
    offset += 4;
    const d = buffer.readUInt8(offset); offset += 1;
    const csFlag = d >>> 6, single = (d & 32) !== 0, checksum = (d & 4) !== 0;
    const df = d & 3, db = df === 3 ? 4 : df;
    const cb = csFlag === 0 ? (single ? 1 : 0) : 1 << csFlag;
    offset += (single ? 0 : 1) + db + cb;
    for (;;) {
      if (buffer.length - offset < 3) return { frames, tornStart: start };
      const bh = buffer.readUIntLE(offset, 3); offset += 3;
      const last = (bh & 1) !== 0, type = (bh >>> 1) & 3, size = bh >>> 3;
      if (type === 3) throw new Error("reserved block@" + (offset - 3));
      const payload = type === 1 ? 1 : size;
      if (buffer.length - offset < payload) return { frames, tornStart: start };
      offset += payload;
      if (last) break;
    }
    if (checksum) offset += 4;
    frames.push({ start, end: offset });
  }
  return { frames };
}

function heapNow() {
  return v8.getHeapStatistics().used_heap_size;
}
let peakHeap = 0;
function sampleHeap() { peakHeap = Math.max(peakHeap, heapNow()); }

const t0 = performance.now();
let fileSize = 0, totalFrames = 0, decodedFrames = 0, eventObjects = 0, plaintextBytes = 0;

// 多会话叠加：逐个 full 读，事件全部驻留（模拟 boot/doctor 把 N 个会话同时物化）
const files = MULTI || [FILE];
const allEventHolders = []; // 防止 GC 回收，模拟"同时驻留"

try {
  for (const oneFile of files) {
    const st = fs.statSync(oneFile);
    fileSize += st.size;
    const buf = fs.readFileSync(oneFile); // readStableFile 等价（整文件读）
    sampleHeap();

    const { frames } = scanZstdFrames(buf);
    totalFrames += frames.length;
    sampleHeap();

    const startIdx = MODE === "tail" ? Math.max(0, frames.length - TAIL_FRAMES) : 0;
    const decodedParts = [];

    for (let i = startIdx; i < frames.length; i++) {
      const f = frames[i];
      const plain = zstdDecompressSync(buf.subarray(f.start, f.end)); // 逐帧解
      decodedFrames++;
      plaintextBytes += plain.length;
      decodedParts.push(plain);
      sampleHeap();
    }

    const fullText = Buffer.concat(decodedParts).toString("utf8");
    const events = [];
    if (KEEP_EVENTS) {
      for (const line of fullText.split("\n")) {
        if (!line.trim()) continue;
        try {
          const j = JSON.parse(line);
          if (typeof j.seq === "number" && j.seq >= 0) {
            const holder = CLONE ? structuredClone(j) : j;
            events.push(holder);
            // 放大：模拟 runtime 对同一事件的多个派生视图（surface节点/投影快照/上下文引用）
            for (let a = 1; a < AMPLIFY; a++) { events.push(holder); }
            sampleHeap();
          } else if (EXPAND && typeof j.seq0 === "number" && Array.isArray(j.payload)) {
            for (let k = 0; k < j.payload.length; k++) {
              const evt = { type: j.type, seq: j.seq0 + k, ts: j.ts };
              const holder = CLONE ? structuredClone(evt) : evt;
              events.push(holder);
              for (let a = 1; a < AMPLIFY; a++) { events.push(holder); }
              sampleHeap();
            }
          }
        } catch { /* 非 JSON 行跳过 */ }
      }
      eventObjects += events.length;
    }
    allEventHolders.push(events); // 驻留到实验结束
    sampleHeap();
  }

  const t1 = performance.now();
  // GC 后测驻留（若有 --expose-gc）
  if (global.gc) { global.gc(); global.gc(); }
  const retainedHeap = heapNow();

  console.log(JSON.stringify({
    outcome: "ok",
    mode: MODE,
    files: files.length,
    file: files.length === 1 ? files[0].split("/").pop() : `${files.length} files`,
    fileSize,
    totalFrames,
    decodedFrames,
    decodedPct: +((decodedFrames / totalFrames) * 100).toFixed(3),
    plaintextBytes,
    plaintextMB: +(plaintextBytes / 1048576).toFixed(2),
    eventObjects,
    eventsKept: KEEP_EVENTS,
    clone: CLONE,
    amplify: AMPLIFY,
    ms: +(t1 - t0).toFixed(1),
    peakHeapMB: +(peakHeap / 1048576).toFixed(1),
    retainedHeapMB: +(retainedHeap / 1048576).toFixed(1),
    rssMB: +(process.memoryUsage().rss / 1048576).toFixed(1),
  }));
  process.exit(0);
} catch (err) {
  console.error(JSON.stringify({ outcome: "error", mode: MODE, error: String(err).slice(0, 300), ms: +(performance.now() - t0).toFixed(1), peakHeapMB: +(peakHeap / 1048576).toFixed(1) }));
  process.exit(3);
}
