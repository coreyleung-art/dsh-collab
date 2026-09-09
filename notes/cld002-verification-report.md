# A3 CLD-002 看门狗 · 参与项②③验证报告（c1111ffe）

> 时间：2026-09-01（重启后自查）
> 内容：崩溃留痕验证 + 重签回归 + 真实崩溃发现

## 参与项②（留痕验证）— 全部通过

| 场景 | 结果 |
|---|---|
| 正常退出留痕 | ✅ crash-reason.log 大量 process-exit / code 0 / signal null 记录（08-29~09-01） |
| 崩溃捕获 | ✅ 2 次真实 uncaughtException 完整记录（reason + 堆栈 + endedAt） |
| SIGKILL 推断 | ✅ "DID NOT EXIT CLEANLY — crash or external kill?" 心跳超时推断机制在 |
| 权限 | ✅ 三文件均 0600 |
| 格式对齐 | ✅ 与 exit-marker-spec-draft v0.1 对齐（3d490920 v2.1 实现） |
| heartbeat | ✅ 正常更新（pid 68525，uptime 150s） |

## 参与项③（重签回归）— 通过

- app.asar 已装新版（sha 74505212，含看门狗）
- dump-config OK（bundle 树正常）

## ⚠️ 意外发现：真实崩溃源（看门狗首次实战价值）

crash-reason.log 显示 **08-30 发生 2 次真实 CLD 崩溃**：

- pid 97761（08-29 启动 ~ 08-30 11:06 崩溃）
- pid 58791（08-30 17:35 启动 ~ 17:41 崩溃）

**崩溃模式**：`TypeError: Cannot read properties of undefined (reading 'reloading')`
at `app.asar/main.js:462:55`（HTTP server 请求处理路径，Server.onRequest → parserOnIncoming）

**建议**：登记新迭代项（CLD 崩溃源，建议 P1），由 3d490920（app.asar 维护）定位修复——看门狗机制已证明其价值（此前 SIGKILL 事故零留痕，现在崩溃源可定位）。

## 结论

A3 参与项全部完成，看门狗规范落地验证闭环。';
