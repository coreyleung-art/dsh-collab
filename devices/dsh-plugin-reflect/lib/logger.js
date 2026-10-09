import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const LOG = path.join(os.homedir(), 'dsh-collab/logs/dsh-plugin-reflect.log');

export function log(rec) {
  try {
    fs.mkdirSync(path.dirname(LOG), { recursive: true });
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      tool: 'dsh-plugin-reflect',
      ...rec,
    });
    fs.appendFileSync(LOG, line + '\n');
  } catch (e) {
    // ⑩ 失败即停的要求下，日志写失败也不能静默 —— 但主流程不因此崩
    try { process.stderr.write(`[reflect] 日志写入失败：${e.message}\n`); } catch {}
  }
}

export function logPath() { return LOG; }
