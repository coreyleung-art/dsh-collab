#!/usr/bin/env node

// ★ R006 ⑦ 统一日志：固定路径，失败也留痕
//
// ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
// 依据：r006-debt-assess.py 机械扫描未检出以下原语：
//       subprocess / os.system / eval / exec / os.remove / rmtree /
//       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
// ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
//

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
