/**
 * log.js — R006 ⑦ 统一日志 + ⑩ 唯一写入入口
 * =============================================================================
 * 本文件是**全包唯一允许出现写入原语的模块**（`WRITER_MODULES = ['lib/log.js']`）。
 * 三个封装函数（guardedMkdirp / guardedWrite / guardedAppend）构成了本工具
 * **全部**的落盘能力，每个函数第一行就是 `assertWriteAllowed(target)` ——
 * 白名单在 gate.js 里被冻结，这里只是它的执行点。
 *
 * 依此，`lib/collect.js` 与 `cli.js` 里没有任何写入/删除原语（A 项扫描证明），
 * 于是"采集动作写坏被采集对象"这条路径**在结构上不存在**（R006 ⑩ 能力缺失型门）。
 *
 * ⑦ 统一日志：固定落盘 `~/dsh-collab/logs/dsh-plugin-reflect-collect.log`，
 * 每次动作一行 JSON（时间/动作/输入/判断/结果/诊断），失败也留痕。
 */

import fs from 'node:fs';
import { LOG_FILE, assertWriteAllowed } from './gate.js';

/** 本进程的落盘计数（`--lean4-check` D 项用它证明 dry-run 零变更）。 */
const stats = { writeCalls: 0, appendCalls: 0, mkdirCalls: 0, attempts: [] };

export function writeStats() {
  return { writeCalls: stats.writeCalls, appendCalls: stats.appendCalls, mkdirCalls: stats.mkdirCalls, attempts: [...stats.attempts] };
}

function record(kind, target) {
  stats.attempts.push({ kind, target: String(target) });
}

/** 建目录（唯一入口） */
export function guardedMkdirp(dir) {
  assertWriteAllowed(dir); // ← 门（失败即停，不警告后继续）
  record('mkdir', dir);
  stats.mkdirCalls += 1;
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/** 覆盖写（唯一入口） */
export function guardedWrite(target, text) {
  assertWriteAllowed(target); // ← 门
  record('write', target);
  stats.writeCalls += 1;
  fs.writeFileSync(target, text);
  return target;
}

/** 追加写（唯一入口） */
export function guardedAppend(target, text) {
  assertWriteAllowed(target); // ← 门
  record('append', target);
  stats.appendCalls += 1;
  fs.appendFileSync(target, text);
  return target;
}

export { LOG_FILE };

/**
 * 统一日志：一行 JSON。
 * 字段固定：ts(时间) / action(动作) / input(输入) / judgement(判断) / result(结果) / diagnosis(诊断)
 * @param {string} action 动作名（如 collect / selfcheck / lean4-check）
 * @param {object} fields {input, judgement, result, diagnosis, ...}
 * @param {object} opts {dryRun:true 时不落盘，改为 stdout 打印 [dry-run] 行（零字节落盘）}
 */
export function log(action, fields = {}, opts = {}) {
  const line = {
    ts: new Date().toISOString(),
    action,
    input: fields.input ?? null,
    judgement: fields.judgement ?? null,
    result: fields.result ?? null,
    diagnosis: fields.diagnosis ?? null,
    extra: Object.fromEntries(Object.entries(fields).filter(([k]) => !['input', 'judgement', 'result', 'diagnosis'].includes(k)))
  };
  const text = JSON.stringify(line) + '\n';
  if (opts.dryRun) {
    // dry-run：零字节落盘。日志行打到 stdout 并显式标注未落盘。
    process.stdout.write(`[dry-run] log-not-persisted ${text}`);
    return { persisted: false, dryRun: true };
  }
  try {
    guardedAppend(LOG_FILE, text);
    return { persisted: true, file: LOG_FILE };
  } catch (e) {
    // 日志失败不遮蔽主流程，但**必须留痕到 stderr**（失败也留痕）
    process.stderr.write(`[log-failed] ${e.code || e.name}: ${e.message}\n`);
    return { persisted: false, error: e.message };
  }
}

/** 失败也留痕的统一封装：包住一段动作，异常时写 log 后再抛出。 */
export function logged(action, fields, fn, opts = {}) {
  const t0 = Date.now();
  try {
    const result = fn();
    log(action, { ...fields, judgement: fields.judgement ?? 'ok', result: 'success', diagnosis: { ms: Date.now() - t0 } }, opts);
    return result;
  } catch (e) {
    log(action, { ...fields, judgement: fields.judgement ?? 'throw', result: 'fail', diagnosis: { ms: Date.now() - t0, error: String(e.message || e), code: e.code || null } }, opts);
    throw e;
  }
}
