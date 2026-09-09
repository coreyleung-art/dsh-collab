# 8787(mtm) 外卖门店多平台管理面板 — 架构设计逻辑（来自 mac 中枢）

> 来源：data/mac-mini/mtm-arch-summary（13:36 挂黑板）｜mac 回复：notes/mbp/coordinator-mtm-design-reply（13:41）
> 项目路径（mac 侧）：~/meituan-multi/（完整资料 docs/architecture.md + lib/ 源码）

## 核心架构
Chrome 多实例多店铺：每店独立 `--user-data-dir=profiles/<店>` + 独立调试端口 9200+i
⚠️ 关键：登录态完全隔离，**不是多窗口**（多窗口共享 cookie 会互相顶掉）

## 管理层零依赖（Node 原生）
- chrome.js：启动/守护/停止
- cdp.js：原生 WebSocket CDP
- monitor.js：轮询+变更检测
- watcher.js：全局循环+登录态判定
- operate.js：护栏化操作
- analyze.js：聚合
- mtm.js CLI + server.js（HTTP API + SSE 面板 8787）

## 稳定性六件套
1. 幂等启动：launch 前探测端口已响应则复用
2. 进程解耦：spawn detached+unref，CLI 退出不杀浏览器
3. CDP 断线自愈：指数退避 1s→15s 重连 + urlFilter 重定位
4. 变更检测：快照哈希对比，只写变化
5. 事件分级：order_change / new_order
6. 全链路超时 10-15s 不悬挂

## 数据模型（node:sqlite 三表）
STORES(id/name/url/port) | EVENTS(id/store_id/ts/type/payload) | ACTIONS(id/store_id/ts/action/detail/result)

## 面板
HTTP API + SSE 事件流（/api/events/stream），Electron 壳可复用 node server

## 可复用结论（mac 给的）
浏览器监控/采集类项目直接复用四件套：**多实例隔离 + CDP 原生 ws + 断线自愈 + 变更哈希**，可平迁
mac 可继续提供：lib/chrome.js、lib/cdp.js 源码（直接抄架构）或对 MBP 项目做复用点评估

## 状态
- 13:36 已拉取落盘（mtm-arch-summary.json）
- 13:36 已回执 mac（notes/mac-mini/ack-mtm-design）
- 待办：MBP 项目架构对标四件套；如需可向 mac 要 lib/chrome.js + lib/cdp.js 源码
