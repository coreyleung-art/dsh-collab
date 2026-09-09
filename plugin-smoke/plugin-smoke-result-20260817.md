# plugin-smoke 探测结果（2026-08-17 04:2x · session-6ed4daf2 执行）

> 委派：协调会话 session-fa1f9150 · 配置：~/dsh-collab/plugin-smoke/plugins.json（实配 4 插件）

## 汇总：✅ PASS 11 / FAIL 0（exit=0）

| 插件 | ① 构建+产物 | ② patch | ③ host 日志 | ④ UI/宿主实测 |
|------|------------|---------|------------|--------------|
| dsh-plugin-agent-bus | ✅ lib 三产物齐 | ✅ 挂载标记 | ✅ 痕迹 + 旧残留甄别 | ✅ /agent-bus/dashboard 200 |
| dsh-plugin-repo-pipeline | ✅ typecheck（补装 devDeps 后）| ✅ 挂载标记 | ✅ 痕迹 + 旧残留甄别 | ✅ repo_pipeline_* 3 工具可用 |
| dsh-plugin-waimai | ✅ lib/index.js | ✅ 挂载标记 | ⚠️ 无痕迹（弱断言）| ✅ waimai_* 16 工具 + 8787 10 店在线 |
| dsh-plugin-local-projects | ✅ build + 双产物 | ✅ 挂载标记 | ✅ 痕迹 | ✅ 侧边栏面板（人工项）|

## 关键甄别
- host 日志中 agent-bus "Invalid or unexpected token" 与 repo-pipeline "Cannot find package" 均为**旧 boot 残留**（历史上构建损坏/未链接时期）；独立验证当前 boot（19:58:06Z）段：插件加载错误 = 0，总错误关键词 = 0。

## 发现的问题与处置
1. **repo-pipeline devDependencies 缺失**（node_modules 无 typescript → tsc not found，exit 127）→ 已执行 `npm install` 修复（+17 包），typecheck 通过。建议 CI/部署固定 `npm ci`。
2. **smoke 工具链改进建议（归属 b241741f）**：host 日志探测为全文件 grep，旧 boot 错误会误报；建议新增 `host.logSinceBoot: true` 配置位（仅扫最后 CLD boot 后段）。
3. waimai 在 dsh-web.log 无加载痕迹 → 弱断言边界（README 已知），已用宿主工具 waimai_state 实测补强。

## v1.1 补丁：bootMarker 修正（2026-08-17 05:3x · 6ed4daf2，QA 邀请）
- 背景：脚本已有 host.bootMarker 配置位（b241741f 实现，标注 6ed4daf2 建议），但 awk 取「首个 boot 后全段」，旧残留仍被捞出（实测 agent-bus Invalid token / repo-pipeline Cannot find package 复现）
- 修正：改为 grep -nF 定位最后 boot 行号 + tail -n +N 取最后 boot 段
- 对照：补丁前 PASS 11（含 2 条旧残留误报痕迹 + 1 条历史 doctor 痕迹）/ 补丁后 PASS 8（0 误报；4 插件日志段均「未见明确加载痕迹」=弱断言，由④ UI/宿主实测补强：dashboard 200 / 3 工具 / 16 工具+10 店 / 面板）
- 结论：bootMarker 口径正确生效，plugins.json 已为 4 插件启用 host.bootMarker="CLD boot"
- 附注：repo-pipeline 已被 QA/dcac2308 修复（git f9b659e fix(qa-001) + 4e32062 ci catch missing devDeps）；其 workspace 的 docs/（未跟踪，dsh-collab 有副本）与 node_modules 曾被 git clean 清除，npm install 已重建（20 包，tsc 在位）
