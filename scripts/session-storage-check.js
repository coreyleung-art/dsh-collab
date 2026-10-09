#!/usr/bin/env node

// ★ R006 ⑦ 统一日志：固定路径，失败也留痕
const DSH_LOG = require("os").homedir() + "/dsh-collab/logs/session-storage-check.log";
function dshLog(msg) {
  try {
    require("fs").mkdirSync(require("path").dirname(DSH_LOG), { recursive: true });
    require("fs").appendFileSync(DSH_LOG, new Date().toISOString() + " " + msg + "\n");
  } catch (e) {}
}

const VERSION = '1.0.0'; // ★ R006 ⑥ 唯一版本声明处（补课生成）
/**
 * 会话存储健康检查脚本（回归基线素材 v1）
 * 作者：session-b278baab（DSH 基础设施根因研究与协作）
 * 用途：post-restart / QA 回归可复跑用例源
 *
 * 检测项：
 *  1. 撕裂帧（torn frame）：ZSTD 帧结构扫描（magic/帧头/块头/校验和），EOF 残留不完整帧即 torn
 *  2. 行级 JSON 解析错误（parse error）
 *  3. 重复 seq / seq 缺口（普通事件行；打包 chunk 行跳过精确 seq 校验，标注为 packed）
 *
 * 用法：node session-storage-check.js [会话根目录]
 *  默认：~/.dsh/sessions/--Users-coreyleung--
 *  退出码：0=全部健康；1=发现问题（供 CI/哨兵使用）
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const z = require("node:zlib");
const os = require("node:os");

const ZSTD_MAGIC = 0xfd2fb528;

/** 尝试从已知安装路径加载真实解码器（展开打包 chunk 行），找不到返回 null */
function loadDecoder() {
  const candidates = [
    process.env.DSH_SESSION_LIB,
    "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-session/lib/types/chunk-rows.js",
    path.join(os.homedir(), ".dsh", "profiles", "web", "node_modules", "@deepseek-ai", "dsh-session", "lib", "types", "chunk-rows.js"),
    path.join(os.homedir(), ".npm", "_npx", "1e7f6d9597241db0", "node_modules", "@deepseek-ai", "dsh-session", "lib", "types", "chunk-rows.js")
  ];
  for (const c of candidates) {
    if (!c) continue;
    try { if (fs.existsSync(c)) return require(c).decodeStorageRecord ?? null; } catch { /* 继续尝试 */ }
  }
  return null;
}
const decodeStorageRecord = loadDecoder();

/** 扫描 ZSTD 帧，返回 { frames:[{start,end}], tornStart } */
function scanFrames(buf) {
  const frames = [];
  let off = 0;
  let tornStart;
  while (off < buf.length) {
    const start = off;
    if (buf.length - off < 4) { tornStart = start; break; }
    if (buf.readUInt32LE(off) !== ZSTD_MAGIC) { tornStart = start; break; }
    off += 4;
    const desc = buf.readUInt8(off); off += 1;
    const contentSizeFlag = desc >>> 6;
    const singleSegment = (desc & 32) !== 0;
    const checksum = (desc & 4) !== 0;
    const dictFlag = desc & 3;
    const dictBytes = dictFlag === 3 ? 4 : dictFlag;
    const csBytes = contentSizeFlag === 0 ? (singleSegment ? 1 : 0) : (1 << contentSizeFlag);
    const remHeader = (singleSegment ? 0 : 1) + dictBytes + csBytes;
    if (buf.length - off < remHeader) { tornStart = start; break; }
    off += remHeader;
    let closed = false;
    for (;;) {
      if (buf.length - off < 3) { tornStart = start; break; }
      const blockHeader = buf.readUIntLE(off, 3);
      off += 3;
      const last = (blockHeader & 1) !== 0;
      const blockType = (blockHeader >>> 1) & 3;
      const blockSize = blockHeader >>> 3;
      const payloadBytes = blockType === 1 ? 1 : blockSize;
      if (buf.length - off < payloadBytes) { tornStart = start; break; }
      off += payloadBytes;
      if (last) { closed = true; break; }
    }
    if (tornStart !== undefined) break;
    if (!closed) { tornStart = start; break; }
    if (checksum) {
      if (buf.length - off < 4) { tornStart = start; break; }
      off += 4;
    }
    frames.push({ start, end: off });
  }
  return { frames, tornStart };
}

function checkSession(logFile) {
  const result = { file: logFile, frames: 0, records: 0, maxSeq: -1, dups: 0, gaps: 0, parseErrors: 0, packedRows: 0, torn: false, issues: [] };
  let buf;
  try {
    buf = fs.readFileSync(logFile);
  } catch (e) {
    result.issues.push(`读取失败: ${e.message}`);
    return result;
  }
  const { frames, tornStart } = scanFrames(buf);
  result.frames = frames.length;
  result.torn = tornStart !== undefined;

  const seenSeq = new Set();
  for (const { start, end } of frames) {
    let text;
    try {
      text = z.zstdDecompressSync(buf.subarray(start, end)).toString("utf8");
    } catch (e) {
      result.parseErrors++;
      result.issues.push(`帧 ${start}-${end} 解压失败: ${e.message}`);
      continue;
    }
    for (const line of text.split("\n")) {
      if (!line.trim()) continue;
      result.records++;
      let rec;
      try {
        rec = JSON.parse(line);
      } catch (e) {
        result.parseErrors++;
        result.issues.push(`行 JSON 解析失败（帧 ${start}）`);
        continue;
      }
      if (rec.type === "session") continue;
      // 有真实解码器：展开打包 chunk 行做精确 seq 校验
      if (decodeStorageRecord) {
        let events;
        try { events = decodeStorageRecord(rec); } catch { events = [rec]; }
        if (events.length > 1) result.packedRows++;
        for (const ev of events) {
          if (typeof ev.seq !== "number") continue;
          if (seenSeq.has(ev.seq)) { result.dups++; continue; }
          seenSeq.add(ev.seq);
          if (ev.seq !== result.maxSeq + 1) result.gaps++;
          if (ev.seq > result.maxSeq) result.maxSeq = ev.seq;
        }
        continue;
      }
      // 无解码器（退化模式）：打包行只计数，不参与 seq 校验
      if (/^(text|reasoning|tool-call)-chunks$/.test(rec.type)) {
        result.packedRows++;
        if (typeof rec.seq0 !== "number") result.issues.push(`打包行缺 seq0（帧 ${start}）`);
        continue;
      }
      if (typeof rec.seq !== "number") continue;
      if (seenSeq.has(rec.seq)) { result.dups++; continue; }
      seenSeq.add(rec.seq);
      if (rec.seq !== result.maxSeq + 1) result.gaps++;
      if (rec.seq > result.maxSeq) result.maxSeq = rec.seq;
    }
  }
  return result;
}

/** 递归收集会话日志文件 */
function collectLogs(dir, out = []) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) collectLogs(full, out);
    else if (entry.name === "session.jsonl.zstd") out.push(full);
  }
  return out;
}

function main() {
  const root = path.resolve(process.argv[2] || path.join(os.homedir(), ".dsh", "sessions"));
  if (!fs.existsSync(root)) { console.error(`会话根不存在: ${root}`); process.exit(2); }
  const logs = collectLogs(root);
  let totalFiles = 0, tornCount = 0, dupCount = 0, gapCount = 0, parseErrCount = 0, badSessions = 0;
  console.log(`会话根: ${root}`);
  console.log(`检测到 ${logs.length} 个会话日志...\n`);
  for (const logFile of logs) {
    totalFiles++;
    const r = checkSession(logFile);
    const flag = r.torn || r.dups > 0 || r.gaps > 0 || r.parseErrors > 0 ? "❌" : "✅";
    if (flag === "❌") badSessions++;
    tornCount += r.torn ? 1 : 0;
    dupCount += r.dups;
    gapCount += r.gaps;
    parseErrCount += r.parseErrors;
    const rel = path.relative(root, logFile);
    console.log(`${flag} ${rel.slice(0, 50).padEnd(52)} frames=${r.frames} maxSeq=${r.maxSeq} dups=${r.dups} gaps=${r.gaps} parseErr=${r.parseErrors} packed=${r.packedRows}${r.torn ? " TORN" : ""}`);
    for (const issue of r.issues.slice(0, 3)) console.log(`     ${issue}`);
  }
  console.log(`\n汇总: 文件=${totalFiles} 异常会话=${badSessions} 撕裂=${tornCount} 重复seq=${dupCount} seq缺口=${gapCount} 解析错误=${parseErrCount}（解码器: ${decodeStorageRecord ? "精确(已加载)" : "退化(未加载)"}）`);
  process.exit(badSessions > 0 ? 1 : 0);
}

main();
