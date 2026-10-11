"use strict";
/**
 * runner-correctness.js v1.0.0 — 正确性类实验 runner（labforge 通用）
 *
 * 对每个输入 .zstd 会话副本：解码全部帧 → 折叠成消息视图(模拟 deriveMessages) →
 * 用 reconcile-orphan 检查"assistant tool_calls 无配对 tool-result"孤儿 →
 * 输出指标（供断言：修复后孤儿数=0）。
 *
 * 参数:
 *   <file1>...            会话文件（.zstd）
 *   --json-out=<path>     结果输出
 * 产物指标:
 *   orphanBefore / orphanAfter / injected / msgCount / perFile...
 */
const fs = require("node:fs");
const path = require("node:path");
const { zstdDecompressSync } = require("node:zlib");
const { reconcileOrphanToolCalls, findOrphanCalls } = require(path.join(__dirname, "..", "lib", "reconcile-orphan.js"));

const args = { files: [], jsonOut: null };
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith("--json-out=")) args.jsonOut = a.split("=")[1];
  else if (a.startsWith("--")) { /* ignore */ }
  else args.files.push(a);
}
if (!args.files.length) { console.error("用法: runner-correctness.js <会话副本...>"); process.exit(2); }

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

function eventSeqsOf(buf, frames, i) {
  // 返回该帧的所有顶层事件对象（带 seq），供折叠
  const evts = [];
  let plain;
  try { plain = zstdDecompressSync(buf.subarray(frames[i].start, frames[i].end)); }
  catch (e) { return evts; }
  for (const line of plain.toString("utf8").split("\n")) {
    if (!line.trim()) continue;
    let j; try { j = JSON.parse(line); } catch { continue; }
    evts.push(j);
  }
  return evts;
}

/** 模拟 surface 折叠：只保留 user/message、assistant/message、tool/result 的消息 */
function deriveMessages(evts) {
  const out = [];
  for (const j of evts) {
    const t = j.type;
    if (t === "user/message") out.push(j.data);
    else if (t === "assistant/message") out.push(j.data.message);
    else if (t === "tool/result") out.push(j.data.message);
  }
  return out;
}

const perFile = [];
let totalOrphanBefore = 0, totalInjected = 0, totalOrphanAfter = 0;
for (const file of args.files) {
  const buf = fs.readFileSync(file);
  const { frames } = scanZstdFrames(buf);
  // 收集所有帧事件（按帧序 → 近似 seq 序）
  const allEvents = [];
  for (let i = 0; i < frames.length; i++) allEvents.push(...eventSeqsOf(buf, frames, i));
  const messages = deriveMessages(allEvents);
  const orphansBefore = findOrphanCalls(messages);
  const fixed = reconcileOrphanToolCalls(messages);
  const orphansAfter = findOrphanCalls(fixed);
  const injected = fixed.length - messages.length;
  totalOrphanBefore += orphansBefore.length;
  totalInjected += injected;
  totalOrphanAfter += orphansAfter.length;
  const name = path.basename(file).replace(/\.zstd$/, "").replace(/\./g, "_");
  const entry = {
    name,
    sizeMB: +(buf.length / 1048576).toFixed(2),
    frames: frames.length,
    msgCount: messages.length,
    orphanBefore: orphansBefore.length,
    orphanAfter: orphansAfter.length,
    injected,
    sampleOrphans: orphansBefore.slice(0, 3),
  };
  perFile.push(entry);
}

const out = {
  sample: args.files.map((f) => path.basename(f)).join("+"),
  files: args.files.length,
  totalOrphanBefore,
  totalInjected,
  totalOrphanAfter,
  // 断言用
  noOrphanAfter: totalOrphanAfter === 0,
  hasOrphanBefore: totalOrphanBefore > 0, // 若样本确含孤儿则为 true
  perFile,
  note: "correctness 类: 孤儿 tool_calls 视图修复验证 (reconcile-orphan)",
};
if (args.jsonOut) fs.writeFileSync(args.jsonOut, JSON.stringify(out, null, 2));
console.log(JSON.stringify({ totalOrphanBefore, totalInjected, totalOrphanAfter, noOrphanAfter: out.noOrphanAfter, perFile: perFile.map((p) => ({ name: p.name, msgCount: p.msgCount, orphanBefore: p.orphanBefore, orphanAfter: p.orphanAfter, injected: p.injected })) }, null, 2).slice(0, 1500));
