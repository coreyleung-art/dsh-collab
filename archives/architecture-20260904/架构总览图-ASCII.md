# CLD / DSH 架构总览图（ASCII）

> 2026-09-04 · 与《CLD-DSH-完整架构梳理》配套

```
═══════════════════════════════════════════════════════════════════
  ① 用户协作设施层（独立进程 · 不受 CLD 崩溃影响）
═══════════════════════════════════════════════════════════════════
 ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌─────────┐
 │rust-black │ │系统管理器 │ │node-bridge│ │bus-bridge   │ │central- │
 │board :8792│ │Python:8798│ │(mac-mini) │ │:8790        │ │inbox    │
 │+SSE:8803  │ │          │ │          │ │             │ │(桥)     │
 └──────────┘ └──────────┘ └──────────┘ └─────────────┘ └─────────┘
   launchd 定时器：auto-index(04:30)/bb-sub/agent-send-gate ···
═══════════════════════════════════════════════════════════════════
  ② CLD 桌面壳（Electron main · app.asar）
═══════════════════════════════════════════════════════════════════
  ┌─ 模式决策 (env/config.json/askMode) ────────────────────┐
  │  local(默认) │ remote │ server(bindHost) │ headless     │
  └──────────────────────────────────────────────────────────┘
  ┌─ start() ────────────────────────────────────────────────┐
  │ traceBoot→marker │ heartbeat(30s) │ spawnDsh │ runDoctor │
  │ startReloadServer(:31888) │ createWindow                 │
  └──────────────────────────────────────────────────────────┘
  看门狗文件：exit-marker.json · heartbeat.json · crash-reason.log
  缺陷：只看主进程退出 → 子进程 OOM 误判 clean exit ✗
═══════════════════════════════════════════════════════════════════
  ③ dsh runtime（ELECTRON_RUN_AS_NODE=1 子进程 · PID 6018）
═══════════════════════════════════════════════════════════════════
  @deepseek-ai/dsh/lib/bin.js web --port 0
  → dsh web: http://127.0.0.1:<port>   （stdout 解析取 URL）
  cordis 插件宿主（195 包）· 崩溃/日志写在 ~/.cld/logs/dsh-web.log
═══════════════════════════════════════════════════════════════════
  ④ profile 插件栈（177 插件 · 31 bundle 层 · 1GB）
═══════════════════════════════════════════════════════════════════
  ~/.dsh/profiles/web/
  package.json(bundles) ──→ cordis.yml(空) ──→ cordis.patch.yml(补丁)
  │
  ├─ [1-2]   dsh-base → dsh-web-app          (核心宿主)
  ├─ [3-6]   @linxin666/web-ui-all · modlens · genui · sidebar
  ├─ [7-13]  local-projects · market · mcp-station · research · voice · workflow-capture
  ├─ [14-20] knowledge · files · doc · repo-pipeline · waimai · gov · read-url
  ├─ [21-28] openpencil · ui-spec · external-link · bus-bridge · hr · dock-cards · flower-cockpit
  └─ [29-31] agent-way(agent-bus) · central-inbox · openchronicle  ← 协作核心
═══════════════════════════════════════════════════════════════════
  ⑤ 会话子系统（dsh 内 · OOM 主战场）
═══════════════════════════════════════════════════════════════════
  ┌ session（append-only 事件日志 · 唯一事实源）
  │   │ append（有界批窗）
  │   ▼
  ├ persistence-jsonl → session.jsonl.zstd（zstd 多帧 · 137MB 最大）
  │   │                （每批次一帧 · 302,413 帧可定位）
  │   ▼
  ├ query-sqlite（搜索/分页 limit 20 · readWindowMax 50）
  │   │
  │   ▼
  ├ projection（派生视图缓存 · zero-I/O 阶梯）
  │   │
  │   ▼
  ├ projection-cache（写检查点）
  │
  └ 读路径（现状 ✗）：打开会话=整文件解压+全量驻留 → OOM
        （LRU 缓存 5 · preparedSessionCacheSize=5 · revision 键）

  读路径（目标 ✓ · 你的模型「磁盘扩内存通道」）：
  readEvent(seq) → 帧索引(302,413 偏移表, KB级)
    → 命中 LRU 热帧缓存? 是→直用
    └ 否→磁盘 seek + 单帧解压(~477B→KB) 入缓存
    内存 = 索引 + 热帧 ≈ MB 级 · 磁盘 = 冷帧驻地 = 内存扩展层
═══════════════════════════════════════════════════════════════════
  存储：~/.dsh/sessions/--工作区--/<session-id>/session.jsonl.zstd
  状态：~/.dsh/{agent-bus.json · storages/ · profiles/ · settings.yaml}
═══════════════════════════════════════════════════════════════════

=== 治理锚点标注 ===
  ① 看门狗补 child exit 检测（修复 OOM 误判 clean）
  ② 打开会话改帧索引按需解压（消灭全量驻留）
  ③ doctor 改读帧头/stat（消灭启动 4GB 峰值）
  ④ 堆上限走 execArgv/--js-flags（NODE_OPTIONS 官方白名单外）
```
