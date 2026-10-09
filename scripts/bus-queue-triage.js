#!/usr/bin/env node

// ★ R006 ⑦ 统一日志：固定路径，失败也留痕
//
// ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
// 依据：r006-debt-assess.py 机械扫描未检出以下原语：
//       subprocess / os.system / eval / exec / os.remove / rmtree /
//       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
// ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
//


// ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
//   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）· .js 版
function r006Selfcheck() {
  console.log("== bus-queue-triage 自查（TCC 能力边界）==");
  console.log("【① 能力清单】");
  console.log("  · ★ R006 ⑦ 统一日志：固定路径，失败也留痕");
  console.log("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。");
  console.log("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：");
  console.log("【② 不该发生路径清单】");
  console.log("  · 本工具涉及「修改权限」⇒ 该路径须受控");
  console.log("【③ 依赖完整性】");
  console.log("  · node " + process.version);
  console.log("  · 依赖: node 内置模块");
  return 0;
}

if (process.argv.includes("--selfcheck")) { process.exit(r006Selfcheck()); }

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
