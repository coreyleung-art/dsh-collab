#!/usr/bin/env node

// ★ R006 ⑦ 统一日志：固定路径，失败也留痕
const DSH_LOG = require("os").homedir() + "/dsh-collab/logs/bus-queue-triage.log";
function dshLog(msg) {
  try {
    require("fs").mkdirSync(require("path").dirname(DSH_LOG), { recursive: true });
    require("fs").appendFileSync(DSH_LOG, new Date().toISOString() + " " + msg + "\n");
  } catch (e) {}
}

const VERSION = '1.0.0'; // ★ R006 ⑥ 唯一版本声明处（补课生成）
// bus-queue-triage.js — 薄封装：真实逻辑在 ~/dsh-plugin-bus-queue-triage/（插件+CLI 共用 lib/core.js 单一真相源）
// 保留本入口是为了兼容既有调用路径与文档；跨设备投递请以插件目录 cli.js + lib/core.js 打包。
import { pathToFileURL } from 'node:url';
const mod = await import(pathToFileURL('/Users/coreyleung/dsh-plugin-bus-queue-triage/cli.js').href);
// cli.js 顶层即执行 main()，无需再调用
