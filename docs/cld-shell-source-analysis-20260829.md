# CLD 壳完整源码分析报告（深入分析）

> 2026-08-29 星桥-mac-mini-协调者 · 用户提供关键信息：CLD 是用户在 MBP 用 dsh 手搓的 app
> 源码位置：本机 `~/CLD/`（main.js.cld002 774 行 + app-cld002.asar + scripts/）
> 状态：深入分析完成

## 一、架构总览（CLD = 壳，dsh = 本体）

```
launchd (application.com.cld.desktop)
  └─ CLD 壳进程 (Electron, --expose-internals .../bin.js web)
       ├─ spawn dsh server (ELECTRON_RUN_AS_NODE 子进程, --port 0 随机端口)
       ├─ BrowserWindow (加载 dsh web URL)
       ├─ exit-trace/watchdog (崩溃追踪 + 30s 心跳)
       └─ inject-proxy (服务器模式, mobile css + Host 重写)
```

**关键**：dsh server 是壳的**子进程**（ELECTRON_RUN_AS_NODE），不是独立进程。
→ 重启 dsh = 重启壳（无单独通道）；dsh 退出 → 壳 child.on('exit') → 弹框 + quit。

## 二、关键机制（从源码确认）

| 机制 | 源码位置 | 说明 |
|------|---------|------|
| spawnDsh | L321 | 壳 spawn dsh（ELECTRON_RUN_AS_NODE），`--port 0` 随机端口，stdout 解析 `dsh web: URL` |
| dsh 崩溃处理 | L392 | `child.on('exit')` → 弹错误框 + `app.quit()`（**无自动重启**）|
| exit-trace | L130-171 | 崩溃原因落盘 `~/.cld/logs/`（exit-marker.json + heartbeat.json + crash-reason.log）|
| watchdog 心跳 | L620 | 每 30s `writeHeartbeat()`（外部可检测壳存活）|
| 模式选择 | L253-299 | config.json remember 控制（local+remember=true 不弹）|
| relaunchClean | L235 | spawn 新实例 + quit（仅切模式/服务器不可达回退用）|
| 单实例锁 | L723 | `app.requestSingleInstanceLock()`（防多实例）|
| runDoctor | L579 | 后台会话自检（修复损坏 session）|

## 三、版本差异（重要发现）

| 文件 | 大小 | 时间 | 说明 |
|------|------|------|------|
| `~/CLD/main.js.cld002` | 27720B | 08-18 | **修复版源码**（含 exit-trace/SIGTERM 干净退出）|
| `~/CLD/app-cld002.asar` | 92346B | 08-18 | 修复版打包 |
| 生产 `/Applications/CLD.app/.../app.asar` | 87238B | — | **旧版**（不含 cld002 的 exit-trace 增强）|

**推断**：用户手搓的修复版（cld002）可能未部署到生产 CLD，或生产是另一个构建。

## 四、对你问题的回答（基于完整源码）

### Q1: 壳内自重启？
**无**——`child.on('exit')` 直接弹框 + `app.quit()`（L392-400）。dsh 崩溃 → 壳退出 → 靠 macOS launchd KeepAlive 拉起新壳。

### Q2: 重启 CLD vs 重新刷 dsh？
**架构上无「单独重启 dsh」通道**（dsh 是壳子进程）。但：
- **前端问题** → 浏览器刷新（Cmd+R）即可（壳/dsh 服务不动）
- **插件/宿主/配置变更** → 需重启壳（dsh 随壳）
- **崩溃恢复** → launchd 拉起新壳 + 新 dsh

### Q3: 模式对话框？
config.json `{mode:local, remember:true}` → `resolveStartupMode` 直接 return（不弹）。已固化。

## 五、可优化点（源码在手后可改）

1. **dsh 崩溃自动重启**：改 `child.on('exit')` → 非干净退出时自动重新 spawn（而不是 quit）——但需避免崩溃循环（加退避/上限）
2. **生产 asar 更新**：确认生产 CLD 是否应升级到 cld002（exit-trace 增强）
3. **心跳外部检测**：watchdog 30s 心跳 → 可被监控（verify-watch 可加壳存活检测）
4. **热重载通道**：若需「只重载 dsh 不重启壳」，需在壳加消息通道（如 IPC/HTTP 触发 spawnDsh 重启）

## 六、安全/可靠性建议

- 崩溃循环防护：若加自动重启，必须带退避（2s→8s→30s）+ 次数上限（防 8/26 类循环）
- exit-trace 已是好机制：崩溃原因可追溯（~/.cld/logs/）
- 与 R011/R013 衔接：壳心跳可作救援方观察指标

## 七、下一步选项

1. **确认生产 asar 版本**：cld002 是否应部署？（用户决定）
2. **加 dsh 崩溃自动重启**（带退避）：源码在手可直接改 → 需沙箱验证（R015）
3. **壳心跳接入监控**：verify-watch/rescue-watch 加壳存活检测
4. 其他用户指定的 CLD 改进
