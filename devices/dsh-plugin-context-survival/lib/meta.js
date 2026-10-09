/**
 * meta.js — 标识 / 版本 / 统一日志（**纯模块**：不 import 任何 dsh/cordis 依赖）
 * =============================================================================
 * 为什么单独一个文件：cli.js 要能在**没挂载、peer 解析不到**时照跑
 * （--selfcheck / --lean4-check / --tool-version）。若 VERSION 放在 lib/index.js，
 * cli.js 一 import 就会拉起 `@deepseek-ai/dsh-tools`，检查本身先崩。
 * 故标识与版本放在这里，lib/index.js 与 cli.js 都从这里取。
 *
 * R006 ⑥：版本**单一来源** = package.json。除本文件外不得第二处硬编码。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const PLUGIN_SLUG = 'context-survival';
export const PLUGIN_NAME = 'dsh-plugin-context-survival';

export const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version; }
  catch { return '0.0.0-unreadable'; }
})();

/** N5：日志固定路径，失败也留痕。 */
export const LOG_FILE = path.join(os.homedir(), 'dsh-collab', 'logs', `dsh-plugin-${PLUGIN_SLUG}.log`);

export function log(line, extra) {
  const rec = { ts: new Date().toISOString(), plugin: PLUGIN_SLUG, line, ...(extra || {}) };
  try {
    fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
    fs.appendFileSync(LOG_FILE, JSON.stringify(rec) + '\n');
  } catch {
    /* 落盘失败不阻塞主流程 */
  }
  return rec;
}
