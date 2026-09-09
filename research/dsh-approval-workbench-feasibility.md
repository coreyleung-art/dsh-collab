# DSH 审批工作台可行性调研报告

> 调研人：DSH 平台能力调研员（子代理）· 2026-08-18 · 证据：本机运行时源码直查（agent-bus 插件 1516 行 Host / 382 行 Client / 12.7KB dashboard.html、web 壳 Slots 槽位枚举、web-ui-all 聚合包）+ web 交叉验证

## 结论先行
1. **可行**。审批底座已存在：dsh-plugin-agent-bus v0.4 的 Host 端 store.approvals（宿主进程单 Map，**多 agent 发起天然跨会话聚合**）+ REST API（GET/POST /agent-bus/api/approvals、POST /approvals/{id}/respond），持久化于 ~/.dsh/agent-bus.json。
2. **大尺寸看板不能只用 dsh-ui 面板 dock**：白名单组件 + 200 节点/200 次追加上限，只够紧凑面板。需自定义 React 槽位或独立页面。
3. **推荐扩展现有 agent-bus 插件**，不新建插件：批量接口 + 看板页面即可落地，预计 Host +40~60 行、Client 400~600 行。
4. 实时性用**轮询**（现状 2.5~5s 已成惯例），无需 SSE/WS。

## A. Client 挂载点（实测）
web 壳槽位（client Slots）：sidebar.footer.action / sidebar.workspaces / conversation.input.left|right|dock|overlay / conversation.session.header.actions / settings.section / shell.overlay 等。
三种大屏方案：
1. **自定义 Client 插件**：sidebar 入口 + ReactDOM.createPortal 全屏 overlay（agent-bus 抽屉先例，540px 可放大为全屏看板）；
2. **webServer 独立页面**：/agent-bus/dashboard 先例（dashboard.html，CSS grid 三栏 300px/1fr/300px，2.5s 轮询）——真正大屏、独立标签页；
3. **conversation.input.dock 停靠面板**（aionui-panel 先例，可拖拽 340~1200px）——中尺寸。

## B. 数据流
- Host：requestApproval 入 Map 并广播全员；respondApproval 改状态 + 通知发起者；status 守卫拒绝重复裁决（幂等安全）；防抖 1.5s 写盘、卸载 flush，跨 CLD 重启保留。
- 聚合：审批单在**宿主进程全局共享**，工作台只需 GET 全量 + 按 proposer/kind 分组即可；批量场景可加 kind=batch。
- 扩展点：agentBus 服务现**未暴露 approvals**（仅 list/send/broadcast/threads/light/lock/unlock/snapshot）→ 需补暴露，或工作台直接走 REST。

## C. 卡片交互
- 批准/拒绝/备注：现成 respond（approve+reason）够用；状态分列（待审/已批/已拒/挂起）、批量勾选、备注 modal **需自定义 React**——白名单组件无多选/批量/拖拽原语。
- dsh-ui table 可做只读列表兜底；交互主界面用自定义槽位。

## D. 约束与坑
1. **安全**：webServer 路由有 hostAllowed（仅 127.0.0.1/localhost）必须沿用；裁决以 'ui' 身份提交、无用户校验——多窗口需本地令牌，敏感操作保留确认弹窗。
2. **持久化**：单 JSON 防抖写盘；resolved 审批单无清理策略 → 加保留（如 100 条/30 天）。
3. **重启影响**：改 Host 需重建 bundle + CLD 重启（quick-restart 可用）；数据不丢；client-plugin 改动需 dev:web watcher 才有 HMR。
4. **多窗口**：双窗口同卡裁决被 status 守卫拒绝（安全），轮询下个周期收敛，无推送但有界延迟。

## E. 推荐架构与规模
- **方案**：扩展 dsh-plugin-agent-bus —— ① Host：agentBus 服务补 approvals 暴露 + POST /approvals/batch-respond + 保留策略（+40~60 行）；② Client：workbench 看板（全屏 portal 或 dashboard.html 独立页，CSS grid 分栏卡片 + 备注 modal + 批量操作条 + 3s 轮询，400~600 行）。
- **落地步骤**：批量接口 → 看板 UI → 轮询+变更即时刷新 → 审计（decidedBy 已有）→ 构建 bundle → CLD 重启 → QA 冒烟（ffb7c3ab）。

## 风险与下一步
- 风险：社区无现成审批工作台插件可复用（web 搜索仅见第三方 MCP/终端类插件，非本域）；独立页与嵌入 GUI 两种形态需协调者拍板（可先做嵌入版）。
- 下一步：与协调者确认交互形态 → 交由 GUI 插件开发会话（1e54d56d）排期实现。

## 噪音排除记录
- @sugarforever/dsh-mcp-apps、dsh-web-terminal、dsh-ui-pet 等 npm 第三方插件：与审批工作台无关，排除。
- 采信：deepseek.com/harness/en（官方 Everything is a plugin）、github deepseek-ai/deepseek-harness packages/client/web README（交叉验证插件体系公开存在）；本机源码为一级证据。
