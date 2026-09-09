# 恢复评估报告 R1（2026-08-17 04:17）

> 自查员：session-6ed4daf2 · 依据 SOP：~/dsh-collab/disaster-recovery-selfcheck.md v1

## 恢复事件
- 方式：quick-restart（ui 发起，countdown 3，marker at 1786907655689）
- 最后 boot：2026-08-16T19:58:06Z（03:58 本地）· 启动后错误计数 = 0

## 自查结果

| 维度 | 项 | 结果 | 证据 |
|------|----|------|------|
| 核心链路 | GUI | ✅ 200 | 127.0.0.1:51960 |
| 核心链路 | 远程入口 3081 | ✅ LISTEN | node PID 84120 |
| 核心链路 | 总线持久化 | ✅ 63 线程 / 23 档案 | ~/.dsh/agent-bus.json |
| 核心链路 | /agent-bus 路由 | ✅ 200 | api/state 736KB + dashboard 12.7KB |
| 核心链路 | detached 存活 | ✅ 5/5 轮 | stress.mjs 复跑 + watcher.log 两轮实证 |
| 插件挂载 | bundles | ✅ 19 / 拼写 0 | package.json 直读 |
| 插件挂载 | link 依赖 | ✅ 无缺失 | health-check 第 8 项 |
| 插件挂载 | 工具面 | ✅ 可用 | agent_*/waimai_*/repo_pipeline/dshdoc |
| 业务链路 | 外卖面板 | ✅ 10 店 logged_in | waimai_state + panel stale=0 age=0s |
| 资源 | 磁盘/内存 | ✅ 52Gi free / mem 37% | health-check |
| 巡检对照 | health-log.tsv | ✅ 04:14 OK | load 4.38 / GUI 200 / boot_err 0 / bundles 19 |

## 关注项（不降级）
- ⚠ **profile package.json 运行期改写**：config_after_boot=modified
  - 归因：session-c1111ffe 持锁 CLD-004 xberg 加固（改 package.json + 重建 node_modules）
  - 判定：受控变更（agent_light 独占锁 TTL 30min）→ 下次重启生效，非事故复发
- ℹ 沙箱边界：health-check.sh 的 pgrep/部分 lsof 受限，已用等价证据替代

## 结论
**✅ 恢复健康** —— 03:54 恢复事件无遗留损伤；19 bundles 全挂载、总线数据完整、业务链路在线、受控变更已甄别。

## 遗留
- CLD-004 加固完成后需再跑一轮自查确认 package.json 变更生效后仍全绿
- 自查 SOP v1 已落盘，后续恢复事件自动复用
