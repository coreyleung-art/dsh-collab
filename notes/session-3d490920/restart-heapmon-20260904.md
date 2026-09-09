# 重启自检 + CLD-002/heap 监控状态（3d490920）

> 2026-09-04 05:27 · CLD 重启恢复

## 在线自检
- 工具面正常、无遗留锁。
- 看门狗 live：heartbeat pid 57659 240s；本次重启过渡留痕 clean（pid 23932 → exited cleanly 05:22:59）。

## 安装状态确认（纠正 recur-analysis 的过期判断）
- **CLD-002 看门狗已安装且运行中**：exit-marker/heartbeat/crash-reason 三文件 live（0600），多日留痕记录在案——recur-analysis（09-02）写「未安装」时点已过期，后续版本已内置。
- 顺带证据：main.js:462 `TypeError reading 'reloading'` 崩溃源 09-03 19:28 再次复发（看门狗完整捕获 stack）——该 bug 至今未修，P1 候选仍有效。

## heap 监控组件（RSS >3.2G 告警）——待补装
- 现有组件：health-check.sh（~/.dsh/cld-health/，CLD-007）已有内存项（memory_pressure），无 CLD 进程 RSS 阈值检查。
- 建议：health-check.sh 增「CLD 主进程 + dsh web 子进程 RSS >3.2G 告警」检查项（进程 RSS 读取在宿主侧可跑，沙箱内 ps 受限需宿主执行）；或独立 cld-rss-monitor 脚本 + launchd。
- 补充：堆内监控用 `--heapsnapshot-near-heap-limit` 需在 spawnDsh 加 Node flag（源码侧改动，随下次 CLD 构建）；NODE_OPTIONS 已被证实无效。