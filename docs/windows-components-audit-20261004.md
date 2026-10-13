# Windows 部件考古审计（2026-10-04 · 星桥）

> 范围：~/dsh-collab 全树 Windows 目标产物（.exe / win-* 构建 / .bat/.ps1）。目的：盘清「给 Windows（i9 PC）做的部件」的版本与状态，交 i9 评估测试。
> ★ i9 评估回执已并入（12:37）：实际对账与风险标注见第五节。

## 一、Agent 基础设施（rust 跨端四家族）

| 组件 | Windows 最新构建（本地） | 源码版本 | macOS 运行版 | 差距 |
|---|---|---|---|---|
| rust-blackboard（黑板） | **v0.6.0**（dist + releases 20260825） | 0.6.17 | v0.6.8 | **win 落后 17 版**：缺 v0.6.12 多端白名单（BLACKBOARD_TOKENS）、鉴权强化、i9 路径豁免等全部后续修复 |
| rust-tools（dsh-tools） | v1.15.0（datasets/shared）· dist 内 v1.13.1 | 1.25.3 | v1.12.2 | 全线落后（最新构建 1.15.0 vs 源码 1.25.3） |
| node-bridge | v1.4.0 | 1.4.2 | v1.4.2 | win 落后 2 个小版 |
| rust-genebank | v1.0.0 | 1.0.0 | — | 持平（仅初版，无 mac 运行记录） |
| CLD（Electron 桌面壳） | Setup 0.3.2 + win-unpacked/CLD.exe（2026-08-31 构建，约 225MB） | — | 0.3.x（本机） | Windows 安装包仅有 8-31 版 |

## 二、业务侧 Windows 脚本（erp-workspace/chuheng_erp，非 agent 基础设施）
- .bat：一键启动/启动ERP/start/build-exe/pull-backups/gradlew/fix-items-500/e2e-verify/fix-nginx-403/deploy-wecom 系列
- .ps1：rfid-local-build-deploy-to-staging / rfid-pipeline-install / _iter1_migrate_staging
- 定位：花店 ERP（Java/nginx/wecom）的 Windows 部署运维脚本，与跨端通讯部件无关。单列备查。

## 三、交叉编译设施（可重建 win 构建）
- 工具链在位：~/.cargo/bin/cargo + cargo-zigbuild；已有 target/x86_64-pc-windows-gnu 构建缓存（blackboard/bridge/genebank/tools）。
- ⇒ 需要时我可以补 Windows 新构建（blackboard 0.6.17 / dsh-tools 最新 / node-bridge 1.4.2），zigbuild 产物免 MSVC 依赖。

## 四、评估请求（给 i9）
1. **盘点对账**：i9 机器上实际运行的各组件版本（板/工具/桥/CLD），与上表对账——本地留存版本 ≠ 你机器运行版本，以实测为准。
2. **实测优先级**：
   a. rust-blackboard win v0.6.0 是否在跑？若在跑，请报运行日志首行（版本/鉴权状态）——v0.6.0 无多端白名单，且鉴权语义与现代版不同。
   b. dsh-tools win v1.15.0 基本命令自测（--version / --help）。
   c. node-bridge win v1.4.0 起停自测。
   d. CLD Setup 0.3.2 安装/启动（若你机器没有 CLD，这个是桌面壳候选）。
3. **回执格式**：每项「版本实测值 + exit/状态码 + 日志首行」，不采信自述声明（R030）。
4. **重建决策**：你回执后我决定补哪些 Windows 新构建（优先 blackboard 0.6.17——它有我们今天所有鉴权修复）。

## 五、本地留存（取证）
- 全量清单：find *.exe 命中 40+；dist 目录保留历史版本作为回滚点；releases/20260825-* 为快照。
- 审计日期 2026-10-04；本表版本号以磁盘文件名为准，源码以 Cargo.toml 为准。


## 六、i9 评估回执对账（2026-10-04 12:37 · 只读实测）
| 组件 | i9 实测 | 结论 |
|---|---|---|
| rust-blackboard | 无二进制无进程 | **不运行**——「win 落后 17 版」对 i9 实际风险为零；标注为「构建产物留存，无已知运行方」 |
| rust-tools | 无二进制 | 不使用 |
| node-bridge | v1.4.0.exe 存在（08-30），未运行 | 版本与表一致 ✓ |
| rust-genebank | 无 | 不使用 |
| ★ CLD 桌面壳 | **0.1.1（08-22）运行中** | **真正落后且运行的关键件**，Windows 侧版本对齐排第一位 |
- i9 与黑板的一切交互 = Python + HTTP（~120 脚本 + 3 常驻守护），无 Rust/Node 黑板客户端。
- i9 无交叉编译设施（rustup 仅 msvc）⇒ win 构建只能在 mac-mini 做。

## 七、v0.6.17 对 i9 旧脚本的回归（i9 报告，预期效应）
- i9-8h-cycle.py（下次触发 15:39）无 token 头写 notes/i9/** ⇒ 401 ⇒ 走既有「401→本地兜底」⇒ 静默不上板（不报错）。
- 修复计划（待 i9 用户 go）：共享凭据读取 + 机器级环境变量 + 只补活跃 6-8 脚本。
- 判定：这是豁免移除的预期后果，非新缺陷；i9 本地兜底保证无数据丢失。
