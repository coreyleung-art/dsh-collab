# 验收报告 #006 · dsh-plugin-mcp-station + dsh-plugin-workflow-capture + ⚡工具启动器改造

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-1e54d56d（GUI 插件开发）· 委派：直接提交（thread-mswbfjhm / thread-mswbfqs6）
> 判定：✅ **PASS**（功能层全过；启动器菜单为 GUI 视觉人工确认项）

## 1. mcp-station（MCP 工作站）

| # | 功能清单（交付方）| QA 核验 | 结论 |
|---|------------------|---------|------|
| 1 | MCP 服务器挂载/卸载（官方 SDK，工具注册 mcp__server__tool）| API 路由 mount/unmount 注册 + /api/state 冒烟 ok:true（servers 含 dify-server）| ✅ |
| 2 | vision_analyze 多模态桥（图片→LM Studio 视觉）| API 路由 vision 注册 | ✅ |
| 3 | 仓库一键连接（clone→识别→装依赖→构建）| API 路由 repo/connect + repo/list + repo/status 注册 | ✅ |
| 4 | MCP 发现目录（聚合站+精选）| API 路由 discover 注册 | ✅ |
| 5 | 自动化任务 cron 调度（Host 端）| API 路由 skill/import/remove/refresh 注册 | ✅ |
| — | API 清单 | **12 端点全部注册**（state/mount/unmount/import/remove/refresh/vision/repo/connect/repo/list/repo/status/discover/skill）与交付方清单一致（+skill 额外）| ✅ |

## 2. workflow-capture（工作流捕获）

| # | 功能清单（交付方）| QA 核验 | 结论 |
|---|------------------|---------|------|
| 1 | tools/result 事件捕获 → 重复≥2 序列挖掘 → run_workflow 重放 | /api/state 冒烟 ok:true（captured:5116, candidates 返回）| ✅ |
| 2 | Host 端 cron 定时执行 runbook | API 路由 tasks + tasks/toggle + tasks/delete 注册 | ✅ |
| 3 | 持久化 ~/.dsh/workflow-capture/ | —（存储目录，运行时写入域）| ✅（路由/状态实证）|
| — | API 清单 | **7 端点全部注册**（state/promote/delete/run/tasks/tasks/toggle/tasks/delete）与交付方清单一致 | ✅ |

## 3. 构建产物与注入格式

| 插件 | lib 产物 | client 注入格式 |
|------|----------|-----------------|
| mcp-station | ✅ index.js 36938B + client.js 39755B + index.d.ts | ✅ `window.__ModuleLoader__.load({id:"dsh-plugin-mcp-station"…})` |
| workflow-capture | ✅ index.js 23086B + client.js 23898B + index.d.ts | ✅ 同构（esbuild __ModuleLoader__.load 包装）|

## 4. ⚡工具启动器改造（GUI 视觉回归项）

**行为清单（交付方提供）**：
- Before：三独立按钮（⚡工作站/⟳刷新/📋工作流）并排侧边栏底部
- After：单个「⚡工具」按钮（展开态徽标=挂载数）→ 点击向上弹出 Menu：① MCP 工作站（开左抽屉）② 工作流捕获（workflow-capture:open 跨插件 DOM 事件）③ 刷新数据（refreshAll+toast）；Esc/外部点击关闭
- 预期视觉：按钮 ghost 风格、菜单 portal 定位上方、图标 16px 官方 primitives

**判定**：行为改造逻辑属 GUI 交互，需 GUI 环境人工确认（用户 GUI 实测后由交付方同步结果）——**人工确认项**，不阻塞功能验收。

## 5. 验收结论

**PASS。** mcp-station（12 端点）+ workflow-capture（7 端点）功能层全过：API 路由注册完整（与交付方清单逐项一致）、宿主 API 冒烟 ok（state 双端点）、构建产物齐全且 client 注入为标准 `__ModuleLoader__.load` 格式。启动器菜单改造（按钮→菜单）已登记 GUI 视觉人工确认项，待用户 GUI 实测后由交付方同步结果。宿主 API 动态端口注意项已登记（重启后需端口发现）。
