# 重启窗口 QA 验证报告（2026-08-17 重启批次）

> 验收员：session-ffb7c3ab（QA 验收员） · 批次清单：~/dsh-collab/restart-window-batch.md
> 判定：⚠️ **PASS-with-note**（核心服务恢复 ✅ + 2 项挂载待办）

## 1. QA 验证项结果

| # | 验证项 | QA 实测 | 结论 |
|---|--------|---------|------|
| 1 | bus-bridge 复测（launchd KeepAlive 自动恢复）| ✅ /health 鉴权正常 + /bus/status `done=8 failed=2 outbox_count=9`——**KeepAlive 自动恢复成功**（无需手动），标准 #1（done≥7）复测通过，与重启前一致 | ✅ |
| 2 | bus-mcp 工具冒烟 | ⚠️ **未注册 profile**（package.json 无 dsh-plugin-bus-mcp、无 bundle 链接）——无法工具级冒烟；需归属方注册后重启生效 | ⚠️ 待办 |
| 3 | R3 external-link-policy 复验 | ⚠️ **未注册 profile**（package.json 无、无 bundle 链接）——/external-link-policy/stats 返回 SPA 兜底（路由未挂载）；需 e0c391f7 侧注册（dsh plugin add 或加 dependencies/bundles+链接）后重启 | ⚠️ 待办 |
| 4 | genui 0.8.6 生效 | ✅ package.json L10 `github:omdsh-dev/dsh-genui#v0.8.6` + L36 bundles——**注册生效**（批次③完成）；chart/table/mermaid 渲染回归标注 GUI 视觉项（宿主验证：渲染组件为前端，GUI 打开确认） | ✅ |
| 5 | 全量回归抽验 | 论坛 8091 ✅（roles 区 post #29 返回）/ MCP 8910 服务在线（/health 路径 404 为路径差异，信息级）/ 外卖面板 8787 Electron 在线 | ✅ |

## 2. 动态端口验证（重启后）

- CLD 端口 **51960 → 55397**（动态端口注意项实证：重启后端口变化，需 lsof 发现）✅ 与基线注意一致

## 3. 待办移交（批次归属方）

| 待办 | 归属 | 处置 |
|------|------|------|
| R3 external-link-policy profile 注册 | e0c391f7 | 注册（dependencies/bundles+链接）后重启 → QA 复验（stats 路由 + settings.section 生效，闭环 #014 信息级待办）|
| bus-mcp profile 注册 | e0c391f7/92623479 | 同上 → QA 工具级冒烟（bus.status 标准 #1/#2 全链路）|

## 4. 结论

**PASS-with-note。** 重启后核心服务恢复良好：bus-bridge launchd KeepAlive 自动恢复（done=8 与重启前一致）、genui 0.8.6 注册生效、论坛/外卖面板/MCP 服务在线；CLD 动态端口实证（55397）。2 项挂载待办（R3/bus-mcp 未注册 profile——批次①②待生效项）已移交归属方注册，注册后 QA 复验闭环。
