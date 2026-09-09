# HR 驾驶舱 · CLD 重启后恢复卡（post-restart）

> 生成：session-a17a52f8 · 2026-08-18 · A1 批准，用户执行 CLD 重启（几秒级）
> 用途：重启恢复后本会话凭此卡秒级续接 HR 职责

## 一、重启后立即执行（30 分钟内）
1. 核对登记表表头/版本（应为 v1.0.214，维护者=session-a17a52f8）
2. agent_light 全量查锁（无遗留锁；异常退出后必须复核——锁策略备注）
3. 拉 §5.2 重启批次三方复验：等待并收集各方回报（J34 定向）：
   - 外链 92623479：bus.status done≥7 + bus.send→MBP 全链路（#016）+ R3 /send（#014）
   - QA ffb7c3ab：R3 stats 路由 + settings.section + bus-bridge 冒烟 #014/#016
   - 健康 9910d4b2：post-restart-check + health-check 新基线
   - 运维 b241741f：三插件 bundle 生效 + external-link 封装 + 内存释放观察
   - GUI 1e54d56d：bundles 21→23 验证 + mcp-station/workflow-capture 存活
4. 汇总三方复验结果 → 登记表 v1.0.215 + 回报协调者/用户
5. 确认 dsh-plugin-hr 4 tab 面板 + resource-manager preset 生效

## 二、重启前待办快照（恢复后继续）
- 等你 GUI：A5 飞书扫码 / B1 s9 补登 / B2 确认卡 1/2/3 / B3 草稿审查（4 项）
- 执行链在途：D4 设备（③ 训练集归集先启动）、C1/C2 开工（cron 先行）、C3 Office、D3 Secret 联调、A3 看门狗（3d490920 安装→9910d4b2 验收）
- MCP 网络：bus.send 已闭环（v0.3）；本 agent 客户端会话重连确认（外链）
- 沉淀闸门：capture 纪要 ≥5 份提醒 55d4d1bd（当前 0 份）

## 三、重启后验证登记表基线
- 版本 v1.0.214（v1.0.215 留给重启复验汇总）
- 5 脚本 + dsh-plugin-hr + preset 核验
