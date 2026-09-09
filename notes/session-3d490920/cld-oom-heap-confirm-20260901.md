# CLD OOM 预案 · --max-old-space-size 配置确认（3d490920）

> 2026-09-01/02 · 回复协调者 data/recovery/cld-oom-20260901-plan

## 启动链路确认
- dsh web 子进程：主进程 spawnDsh → `process.execPath --expose-internals <bin> web --port 0`（ELECTRON_RUN_AS_NODE=1，继承 env）。
- 主进程：/Applications/CLD.app/Contents/MacOS/CLD（当前无 launchd plist，GUI 启动）。

## 关键实证：--max-old-space-size=8192 在此构建**无效**
- 该 Electron/Node 构建启用 **V8 指针压缩**：堆上限硬顶 ~4GB（heap_size_limit=4192MB）。
- 实测（ELECTRON_RUN_AS_NODE 直测）：1024→1120MB ✅ flag 可解析；**8192→4192MB / 16384→4192MB ❌ 被钳制到 cage 上限**。
- NODE_OPTIONS 对 Electron 主进程**禁用**（实测无效）。
- 结论：8GB 堆在该构建上不可达；想突破需非指针压缩的自定义 Node 构建（成本高，不建议）。

## OOM 实况（dsh-web.log，均 dsh web 子进程）
- pid 68528：uptime 604s，old space 3.62→3.64GB last resort GC → FATAL。
- pid 1748：uptime 7.3h，old space 3.78GB → FATAL（疑似缓慢泄漏/大负载累积）。
- 另 2 个主进程 .ips 崩溃（09-01 14:55 / 09-02 00:44）需单独查。

## 建议方向（替代堆扩容）
1. 排查 dsh web 子进程内存增长源：超大 session 日志加载 / 插件树 / 会话列表常驻。
2. 若可调：限制 session 载入量、定期重启回收、监控 old space 水位（>3.5GB 预警）。
3. 主进程 .ips 崩溃单独归因（可能与子进程 OOM 联动的退出处理有关）。
4. --max-old-space-size 如需保留，只能 ≤4096（当前 cage 内，无收益）。