# heap 监控组件产出（3d490920）· RSS >3.2G 告警

> 2026-09-05 · 采纳自 restart-heapmon-20260904 建议

## 产出
- **~/dsh-collab/cld-health/cld-rss-monitor.sh**（可执行，bash -n 通过）
- 功能：检查 CLD 主进程（非 helper）+ dsh web 子进程（bin.js web --port）RSS；任一 >3.2GiB（3355648KB）→ 告警写 ~/.cld/logs/cld-rss.log + stderr，exit 1。
- 输出：普通 / --json（checked_at/threshold_kb/procs/alert）。
- 阈值依据：OOM 实况 old space 3.6-3.8GB（指针压缩 4GB cage 内），3.2G 预留告警余量。

## 集成建议
1. health-check.sh 增子命令：`bash cld-rss-monitor.sh --json`（exit 1 = 红）——与 CLD-011 内存项互补（memory_pressure 是系统级，本项是 CLD 进程级）。
2. 宿主侧调度：并入既有 health 巡检（com.dsh.health 60min 或按需），不新增独立 launchd（遵守成本纪律）。
3. 堆内快照（--heapsnapshot-near-heap-limit）需源码侧 spawnDsh 加 Node flag，随下次 CLD 构建（NODE_OPTIONS 已证无效）。

## 验证
- bash -n 通过；空运行 --json 输出有效（procs=[] 因沙箱 pgrep/ps 受限，宿主侧运行可查真实 CLD 进程）。
- 阈值逻辑：`ps -o rss=`（KB）与 3355648 比较，超阈写日志+exit 1。