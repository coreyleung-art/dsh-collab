# 重启后复核 · 2026-09-04 03:19 CST（central-inbox v2 部署窗口）

> 执行：守灯（CLD 健康审查）· health-check.sh --log

## 结果：CLD 本体健康 ✅
- GUI 53477: HTTP 200；远程入口 3081: node PID 76361
- 最后启动 2026-09-03T19:16:33Z，启动后错误 0
- profile bundles 31（central-inbox v2 生效后计数）；coreuleung 拼写 0
- xberg 绑定 + dylib 8 文件 OK；link 依赖缺失 无
- 会话日志 187 个 / 撕裂 0；config 无运行期改写
- agentBus.list(): 39 会话在线，本会话 session-9910d4b2 可见（定向注入回归前提满足）

## ⚠ 待关注（非本次重启引入）
- swap 占用 91%（≥80% 红线，内存压力信号，关联 CLD-020/CLD-002）
- Data 卷 98% used（≥85% 红线）
- 负载 8.37/7.71/7.19（偏高，Chrome/Docker 常态）
- 面板 8787: 10 stores / 1 stale（天河抖音觅趣守白 age=8884s，信息级，权威判定用 waimai_state）

趋势已入 health-log.tsv。central-inbox v2 注入链路回归项：待协调者安排 A1/A2 用例验证。
