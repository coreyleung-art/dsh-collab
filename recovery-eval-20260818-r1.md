# 恢复评估报告 R1（2026-08-18 00:3x）

> 自查员：session-6ed4daf2 · 依据 SOP：~/dsh-collab/disaster-recovery-selfcheck.md v1.1
> 触发：重启窗口（用户安排 mac-mini 重启，批次清单 restart-window-batch.md）

## 恢复事件
- 方式：重启窗口（用户安排，多批次挂载生效）
- 最后 boot：2026-08-17T16:29:59Z（本地 00:29）· 启动后错误计数 = 0

## 自查结果

| 维度 | 项 | 结果 | 证据 |
|------|----|------|------|
| 核心链路 | GUI | ✅ 200 | 127.0.0.1:55397（端口变化属预期） |
| 核心链路 | 3080 哨兵 | ✅ 无监听 | 无双 dsh 实例 |
| 核心链路 | 3081 远程入口 | ✅ LISTEN | 100.120.203.20:3081 PID 57718 |
| 核心链路 | /agent-bus 路由 | ✅ 200 | api/state + dashboard |
| 核心链路 | 服务端口 | ✅ | 8787 面板 / 8091 论坛 / 8910 MCP |
| 插件挂载 | bundles | ✅ 21 | 19→21 = OpenPencil + ui-spec（重启批次④）；genui 升 v0.8.6；bus-mcp/R3 **未入 profile bundles**（协调者权威核实：未挂载，e0c391f7 补挂载中） |
| 业务数据 | 外卖面板 | ✅ 10 店 logged_in | waimai_state + 8787 Electron PID 8667 |
| 业务数据 | 帧完整性 | ✅ corrupt=0 | doctor healthy=110 fixed=0 |
| 总线 | 持久化 | ✅ 290 线程 / 42 档案 / 0 锁 | agent-bus.json + agent_light |

## 关注项
- 无（locks=0，无受控变更锁；bundles 21 为重启窗口预期变更）
- ℹ GUI 端口 51960→55397：dsh web 端口变化属预期（每次启动可能不同）
- ⚠ 口径修正（协调者权威核实，通道区分）：① external-link MCP 服务器经 8910 MCP 机制挂载在线（不依赖 profile bundles）；② bus-mcp 插件工具（dsh-plugin-bus-bridge 原生工具）+ R3 external-link-policy 面板需 profile 挂载（cordis.patch.yml），当前未挂载待 e0c391f7 补；本报告 bundles 21 = 原 19 + OpenPencil + ui-spec

## 结论
**✅ 恢复健康** —— 重启窗口批次生效后无遗留损伤；21 bundles 全挂载、总线数据完整（290 线程）、业务链路在线、帧完整 0 损坏。

## 遗留
- 批次专属验证：genui 渲染 / OpenPencil / waimai_focus 由归属方回报；bus-mcp 插件工具 + R3 面板待 e0c391f7 补 profile 挂载后复验（QA #014/#016 待闭环）
- 下次恢复事件继续按 SOP 执行