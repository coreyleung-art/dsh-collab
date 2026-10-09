/**
 * log.js — ⑦ 统一日志
 * =============================================================================
 * 固定路径：~/dsh-collab/logs/dsh-plugin-reflect-enroll.log（可用 DSH_REFLECT_ENROLL_LOG 覆盖）
 * 每次动作一行 JSON：时间 / 输入 / 判断 / 结果 / 诊断。
 * ★ 失败也必须留痕：所有错误路径（门拒绝、IO 失败、回滚）都调用 log() 后再抛/返回。
 * 日志落盘失败**不阻塞**主流程（但会在 stderr 提示一次），绝不因为写日志失败而污染库写入语义。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { VERSION } from './version.js';

export const DEFAULT_LOG = path.join(os.homedir(), 'dsh-collab', 'logs', 'dsh-plugin-reflect-enroll.log');
let currentLog = process.env.DSH_REFLECT_ENROLL_LOG || DEFAULT_LOG;

export function setLogFile(p) { if (p) currentLog = path.resolve(String(p).replace(/^~/, os.homedir())); }
export function logFile() { return currentLog; }

export function log(event, data = {}) {
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    tool: 'dsh-plugin-reflect-enroll',
    version: VERSION,
    event,
    ...data
  });
  try {
    fs.mkdirSync(path.dirname(currentLog), { recursive: true });
    fs.appendFileSync(currentLog, line + '\n');
  } catch (e) {
    try { process.stderr.write(`[reflect-enroll] 日志落盘失败（不阻塞）: ${e.message}\n`); } catch { /* 忽略 */ }
  }
  return line;
}
