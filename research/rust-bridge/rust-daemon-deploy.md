# Rust 常驻守护进程跨平台部署最佳实践（node-bridge）

> 调研对象：分布式节点的常驻节点桥二进制 `node-bridge`（Rust 编写），跑在 Windows 机器（i9）、macOS 机器（mbp）、Linux 服务器上。
> 硬性要求：**开机自启、崩溃自动重启、日志落盘轮转、尽量无需用户登录**（Windows 上特别说明）。
> 调研日期：2026-08；结论基于官方文档 / man 页 / 社区实践交叉验证。

---

## 0. 结论摘要（TL;DR）

| 平台 | 推荐方案 | 一句话理由 |
|------|----------|-----------|
| **Windows (i9)** | **首选：Rust `windows-service` crate 原生服务模式**（单二进制、无外部依赖、SCM 管理）；**即插即用备选：NSSM 2.27 封装** | 服务在 Session 0 由 SCM 启动，无需登录、开机自启、崩溃重启 + 失败恢复（`sc failure`）原生支持；NSSM 是零代码的最快路径 |
| **macOS (mbp)** | **LaunchDaemon（`/Library/LaunchDaemons`）+ KeepAlive** | 系统域守护进程开机即起、无登录；KeepAlive 崩溃自动拉起；日志重定向到文件 |
| **Linux (server)** | **systemd unit（`Restart=on-failure` + 退避 + 硬化）** | 事实标准；journald 日志归集 + 限额轮转；`network-online.target` 保证网络就绪 |
| **日志轮转** | **桥自己写固定大小滚动日志（flexi_logger/tracing-appender）为唯一事实源**，平台日志（journald/事件日志）仅作辅助 | 三平台行为一致、零系统配置依赖；NSSM/newsyslog/logrotate 都只覆盖单平台且各有 inode/句柄坑 |

**统一运维模型**：**「平台服务注册（主）+ 桥内健康检测快速失败（辅）」双层**——平台负责开机自启、崩溃拉起、日志归集；桥内部只做平台做不到的两件事：① panic/假死时**主动以非零码退出**让平台重启（ogre-watchdog 式 stall 检测），② 优雅处理 `SIGTERM`/`SERVICE_CONTROL_STOP`。**不推荐**用纯内置父子进程 watchdog 代替平台机制（会丢掉开机自启与无登录能力，且三平台重复造轮子）。

**Windows 无登录一句话**：服务方式 = SCM 在 Session 0 直接拉起，天然无登录；任务计划「不管用户是否登录」= 需要存凭据或 S4U，S4U 有网络资源访问限制，重启语义弱——**常驻守护不要用任务计划**。

---

## 1. Windows 方案对比与推荐

### 1.1 五个候选方案

#### (a) NSSM（Non-Sucking Service Manager）
把任意 exe 包装成 NT 服务，**默认行为就是「应用非预期退出即重启」**，自带重启退避（每次失败暂停渐增、上限 4 分钟），自带 stdout/stderr 重定向与日志轮转（2.22+，大小/时间触发、move 或 copy-and-truncate 两种策略）。

- 优点：零改代码、一条 `nssm install` 即用；崩溃重启、日志重定向、轮转、环境变量、退出码策略（`AppExit 78 Exit` 之类）全内置；GUI + CLI 双通道。
- 缺点：**官方 nssm.cc 已停更**（最后正式版 2.24，2014）；社区 fork [burgerbecky/nssm](https://github.com/burgerbecky/nssm) 维护到 2.27（2022-05），基本可用但长期维护风险在；多一个要随二进制分发的 exe；对复杂进程树清理一般。
- 适用：**快速交付、不想/来不及改 Rust 代码**的过渡方案；Windows 上最常见的工业实践。

#### (b) WinSW（Windows Service Wrapper）
XML 配置驱动的服务包装器（Jenkins 在用）。`<executable>` + `<arguments>` + `<log mode="roll">` + `<onfailure action="restart">`。

- 优点：XML 配置可版本化管理、可声明式；官方仍在维护（3.x 有 .NET 7 原生二进制，2.x 稳定）；重启动作可配。
- 缺点：**崩溃重启语义不如 NSSM 顺手**（靠 onfailure 恢复动作，粒度与退避控制弱）；日志轮转能力基础；纯 CLI 无 GUI。
- 适用：Jenkins 生态、喜欢 XML 声明式配置、且应用本身很少崩的场景。

#### (c) 任务计划程序（Task Scheduler）
「登录触发」= 只在用户登录会话里跑（会话 1+），注销即停；「开机触发（At startup）+ 不管用户是否登录」= 在非交互会话跑，但需要保存凭据或 S4U（见 §2）。

- 优点：系统自带零依赖；「At startup」可开机即起。
- 缺点：**对常驻进程是错误工具**——重启语义弱（「If the task fails, restart every N min, up to M times」有次数上限、无指数退避）；At startup 任务可能在网络就绪前就起；无登录运行要存凭据且 S4U 不能访问网络资源；Task Scheduler 服务本身有启动竞态。
- 适用：**定时批处理**（每天 23:00 同步之类），不适用常驻守护。

#### (d) rust `windows-service` crate 原生服务
用 `define_windows_service!` 宏生成 FFI 服务入口，`service_dispatcher::start()` 注册到 SCM，`service_control_handler::register()` 处理 `SERVICE_CONTROL_STOP/PAUSE` 等，`ServiceManager` API 可编程安装/配置，**失败恢复动作（等价 `sc failure`）也有对应 API**。参考 [mullvad/windows-service-rs](https://github.com/mullvad/windows-service-rs)（DeepWiki: [Getting Started](https://deepwiki.com/mullvad/windows-service-rs/2-getting-started) / [Core Concepts](https://deepwiki.com/mullvad/windows-service-rs/3-core-concepts)）。

- 优点：**单二进制、零外部工具**——一个 exe 既是服务本体又是安装器（`node-bridge --install-service`）；SCM 原生管理（开机自启、Session 0、失败恢复）；`SERVICE_CONTROL_STOP` 优雅停机天然对接；对 i9 这种要「最小配置」的机器最干净：一条命令装完。
- 缺点：要写服务样板代码（状态机：StartPending→Running→StopPending→Stopped、控制事件循环）；调试时要有 console 模式分支（`--console`）；安装需管理员权限。
- 适用：**我们控制 Rust 源码时的产品级正解**。

#### (e) 启动文件夹（`shell:startup`）
快捷方式丢进 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`。

- 优点：零工具。
- 缺点：**仅用户登录后**才起、注销即停；**无崩溃重启**；无日志管理。
- 适用：个人小工具，**本场景直接排除**。

### 1.2 推荐（i9 零配置/最小配置 + 崩溃自动拉起）

```
优先级 1（最终形态）：windows-service crate 原生服务
  交付物 = 单个 node-bridge.exe：
    node-bridge --install   # 以服务注册（ServiceManager + 失败恢复动作）
    node-bridge --console   # 前台调试模式
  崩溃重启 = sc failure NodeBridge ...（或 crate 的 failure_actions API 配置）
  日志 = 桥自滚文件（§6）

优先级 2（今天就能跑、零改代码）：NSSM 2.27
  分发 nssm.exe + install-node-bridge.bat 一条脚本（命令见 §1.3）
  崩溃重启 = NSSM 默认行为（AppExit Default Restart + AppRestartDelay）
```

任务计划程序、启动文件夹：**不用于常驻守护**。

### 1.3 可直接复制的 NSSM 命令（Windows）

```bat
@echo off
set SVC=NodeBridge
set DIR=C:\node-bridge

nssm install %SVC% "%DIR%\node-bridge.exe" --daemon
nssm set %SVC% AppDirectory %DIR%
nssm set %SVC% Start SERVICE_AUTO_START          :: 开机自启
nssm set %SVC% ObjectName LocalSystem             :: 服务账户（见 §2）
nssm set %SVC% AppExit Default Restart            :: 任何非预期退出都重启
nssm set %SVC% AppRestartDelay 5000               :: 重启前等待 5 秒（ms）
nssm set %SVC% AppStdout "%DIR%\logs\bridge-out.log"
nssm set %SVC% AppStderr  "%DIR%\logs\bridge-err.log"
nssm set %SVC% AppRotateFiles 1                   :: 启用轮转
nssm set %SVC% AppRotateBytes 10485760            :: 10 MB 触发
nssm set %SVC% AppRotateOnline 1                  :: 运行中即可轮转（copy-truncate）
nssm start %SVC%
```

> NSSM 2.27（burgerbecky fork）下载：https://github.com/burgerbecky/nssm/releases

### 1.4 原生服务（windows-service crate）要点

```rust
// 结构骨架（示意）：
// 1) 入口：main() 里判断参数，--install 走 ServiceManager，--console 走前台循环
// 2) 服务模式：
//    windows_service::define_windows_service!(ffi_service_main, node_bridge_service_main);
//    service_dispatcher::start("NodeBridge", ffi_service_main)?;
// 3) service_main 内：
//    service_control_handler::register("NodeBridge", event_handler)?;  // Stop/Pause...
//    报告 ServiceStatus: StartPending -> Running；Stop 时 -> StopPending -> Stopped
// 4) 安装时配失败恢复（等价 sc failure）：
//    sc failure NodeBridge reset= 86400 actions= restart/5000/restart/15000/restart/60000
```

```bat
:: 原生服务安装（无需 NSSM）
node-bridge.exe --install
sc failure NodeBridge reset= 86400 actions= restart/5000/restart/15000/restart/60000
sc start NodeBridge
```

---

## 2. Windows「无登录跑服务」专题

### 2.1 服务 vs 任务计划「不管用户是否登录」的本质差异

| 维度 | Windows 服务（SCM） | 任务计划「Run whether user is logged on or not」 |
|------|--------------------|------------------------------------------------|
| 启动时机 | 开机即由 SCM 拉起（Startup=Automatic），**无需任何用户登录** | At startup 触发，同样可在无登录时跑 |
| 运行会话 | **Session 0**（非交互），SCM 生命周期管理 | 非交互会话，由 Task Scheduler 服务托管 |
| 账户 | LocalSystem/NetworkService/自定义账户（`SeServiceLogonRight`） | 需**保存凭据**或勾选 **Do not store password**（走 **S4U**） |
| S4U 限制 | 无 | **S4U 无法访问网络资源**（除非域约束委派），也不能访问加密文件；要求「Logon as batch job」权限 |
| 崩溃重启 | 服务恢复（`sc failure`：重启/退避/重置计数） | 「If the task fails, restart every N, up to M」——有次数上限、无指数退避，**常驻进程语义弱** |
| 适合 | 常驻守护进程 | 定时任务/批处理 |

来源：[MS Learn – Task Security Context](https://learn.microsoft.com/en-au/previous-versions/windows/it-pro/windows-server-2008-r2-and-2008/cc722152(v=ws.10))：默认任务仅在调度用户登录时运行；选「Run whether user is logged on or not」后任务非交互运行，保存凭据或经 S4U 获取令牌，S4U 只能访问本地资源、无法访问网络资源（除约束委派）。

**结论：node-bridge 是常驻网络守护 → 必须用服务方式**，别用任务计划。

### 2.2 服务账户选择

| 账户 | 权限 | 适用 |
|------|------|------|
| **LocalSystem** | 本机最高权限（SYSTEM） | 图省事的默认；**权限过大**，被攻破=机器沦陷；网络访问以机器账户身份 |
| **NetworkService** | 低权限 + 网络凭据（本机账户） | **桥推荐**：主动连协调端（出方向）够用 |
| **自定义本地账户** | 最低权限，需授 `SeServiceLogonRight`（Log on as a service） | 需要精细 ACL（只写 logs/ 目录）时 |
| gMSA（域环境） | 自动轮换密码、无密码存储 | 域内多机统一管理时 |

注意点：
- 用自定义账户要给 `logs/` 目录配写权限（ACL），否则日志落不了盘；
- 换账户后必须 `sc config NodeBridge obj= .\nodeuser password= xxx` 且给「作为服务登录」权限；
- LocalSystem 下写 `%USERPROFILE%` 是 `C:\Windows\System32\config\systemprofile`，**容易踩坑**——桥的工作目录/配置路径要显式绝对路径。

---

## 3. macOS：launchd

### 3.1 概念

- **LaunchDaemon**（`/Library/LaunchDaemons/*.plist`，系统域 `system`）：开机即起、**无需用户登录**、可指定 `UserName`（默认 root）、注销不影响——**本场景用这个**。
- **LaunchAgent**（`~/Library/LaunchAgents` 或 `/Library/LaunchAgents`，`gui/$UID`）：跟随用户登录会话，注销即停——不适合「无登录」要求。
- 关键键：`RunAtLoad`（加载即运行）、`KeepAlive`（**退出即重启**；`true`=任何退出都重启，dict 形式可细化为 `SuccessfulExit=false` 仅非零退出重启、`Crashed=true`）、`ThrottleInterval`（**重启最小间隔，默认 10s**，防崩溃风暴）、`StandardOutPath`/`StandardErrorPath`（重定向日志文件，**注意：不轮转**，见 §6）。

来源：[launchd.plist(5) man page](https://keith.github.io/xcode-man-pages/launchd.plist.5.html)、[launchd 深度参考](https://github.com/0xdarkmatter/claude-mods/blob/main/skills/mac-ops/references/launchd-deep-dive.md)。

### 3.2 可直接使用的 plist 模板

`/Library/LaunchDaemons/com.distributed.nodebridge.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.distributed.nodebridge</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/node-bridge/node-bridge</string>
        <string>--daemon</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <!-- 崩溃/退出自动重启；dict 形式可只对非零退出重启：
         <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict> -->
    <key>KeepAlive</key>
    <true/>

    <!-- 失败退避：两次重启之间至少间隔 10s（默认就是 10） -->
    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>WorkingDirectory</key>
    <string>/opt/node-bridge</string>

    <!-- 非 root 运行；需创建该用户 -->
    <key>UserName</key>
    <string>nodeuser</string>
    <key>GroupName</key>
    <string>nodeuser</string>

    <!-- 日志重定向（文件；轮转见 §6） -->
    <key>StandardOutPath</key>
    <string>/opt/node-bridge/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/opt/node-bridge/logs/stderr.log</string>

    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
```

安装（需 sudo）：

```bash
sudo cp com.distributed.nodebridge.plist /Library/LaunchDaemons/
sudo launchctl bootstrap system /Library/LaunchDaemons/com.distributed.nodebridge.plist
sudo launchctl enable system/com.distributed.nodebridge   # 开机自动加载
# 状态查看
sudo launchctl print system/com.distributed.nodebridge
```

要点：
- launchd 要求被管理进程**不要自己 daemonize**（不要 fork 后父进程退出）——桥以 `--daemon` 前台方式跑即可，launchd 会处理好 setsid/stdio；
- 崩溃风暴会被 `ThrottleInterval` 节流（日志里出现 "service throttled by N seconds"）；
- **KeepAlive=true 连「正常退出」也会重启**——如果桥需要「配置错误就停止」的语义，改成 dict 形式 `SuccessfulExit=false`。

---

## 4. Linux：systemd

### 4.1 unit 模板

`/etc/systemd/system/node-bridge.service`：

```ini
[Unit]
Description=Node Bridge (Rust distributed node daemon)
After=network-online.target
Wants=network-online.target
# 防崩溃风暴：300 秒内最多 5 次启动失败即停（避免无限重启烧 CPU）
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=nodeuser
Group=nodeuser
WorkingDirectory=/opt/node-bridge
ExecStart=/opt/node-bridge/node-bridge --daemon

# ---- 重启策略 ----
Restart=on-failure        # 非零退出才重启；若要"退出必拉起"用 always
RestartSec=5s             # 重启退避
RestartPreventExitStatus=78   # 78=EX_CONFIG，配置错误不重试

# ---- 硬化（成本极低，收益大）----
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
LimitNOFILE=65536         # 默认 1024，连接多时必调

# ---- 日志：journald 归集（限额轮转见 §6）----
StandardOutput=journal
StandardError=journal

# ---- 可选：systemd 看门狗（桥用 sd_notify 喂狗）----
# WatchdogSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now node-bridge
systemctl status node-bridge
journalctl -u node-bridge -f          # 看日志
journalctl -u node-bridge --since "1 hour ago" -o short-precise
```

### 4.2 关键说明（交叉验证自 [systemd 生产实践](https://stackharbor.com/en/knowledge-base/systemd-unit-patterns-production/)）

- `Restart=always` vs `on-failure`：`always` 连退出码 0 也重启（配合 `RestartPreventExitStatus` 排除"主动退出"）；`on-failure` 只重启非零退出——**常驻守护二选一，务必配 `RestartSec` 退避**，否则裸 `Restart=always` 会在崩溃循环里烧 CPU 直到 StartLimit 触顶变 failed。
- `network-online.target` 依赖 `NetworkManager-wait-online` / `systemd-networkd-wait-online` 已启用才真正"等网络"；桥本身最好也有重连逻辑兜底。
- 硬化项（`NoNewPrivileges`/`ProtectSystem`/`PrivateTmp`）几乎零成本，直接上。
- journald 日志默认持久化在 `/var/log/journal`（`journalctl --disk-usage` 可查），上限由 `/etc/systemd/journald.conf` 的 `SystemMaxUse=` 控制。

---

## 5. 统一运维视角

### 5.1 配置下发与安装抽象

三平台各一条「注册 + 启动」命令，其余全交给平台：

| 平台 | 注册/启动 | 配置文件位置 | 卸载 |
|------|-----------|--------------|------|
| Windows | `node-bridge --install`（或 `install.bat` 调 NSSM） | `C:\node-bridge\config.toml` | `node-bridge --uninstall` |
| macOS | `sudo launchctl bootstrap system ...` | `/opt/node-bridge/config.toml` | `sudo launchctl bootout system/...` |
| Linux | `sudo systemctl enable --now node-bridge` | `/etc/node-bridge/config.toml` | `sudo systemctl disable --now node-bridge` |

- **远端下发**：二进制 + 配置 + 安装脚本打包成一个 tarball/zip，用已有的通道（Ansible/ssh/组策略/临时脚本）推下去，`install.sh`/`install.ps1` 幂等执行（检测已装则仅更新配置并重启）。`config.toml` 单一事实源，三平台解析同一份。
- 桥的 CLI 保持统一：`--daemon`（前台跑，交给平台托管）、`--console`/`--debug`（手动调试）、`--install`/`--uninstall`（Windows 专用）。
- **不要**用裸 `--daemon` 参数自己 double-fork：launchd 明确禁止、systemd `Type=simple` 也不需要、Windows 服务由 SCM 管。前台进程 + 平台托管是最简契约。

### 5.2 内置 watchdog vs 纯平台机制：推荐「平台为主 + 桥内快速失败为辅」

| 维度 | 纯平台机制 | 内置 watchdog（父进程拉起子进程） | **平台 + 桥内健康检测（推荐）** |
|------|-----------|--------------------------------|--------------------------------|
| 开机自启/无登录 | ✅ 平台原生 | ❌ 做不到（watchdog 也得有人拉） | ✅ 平台 |
| 崩溃重启 | ✅ | ✅ | ✅ 平台 |
| **假死（不退出但卡死）** | ❌ 进程活着，平台不重启 | ✅ 父进程可杀子进程 | ✅ 桥内 stall 检测→主动 exit→平台拉起 |
| 优雅停机信号 | ✅ SIGTERM/Stop | 需要信号转发 | ✅ 桥处理信号，平台传 |
| 实现成本 | 0 | 高（进程管理、退出码语义、孤儿进程） | 低（一个 watchdog 线程 + panic hook） |

**推荐落地（双层）**：
1. **平台层**：systemd/launchd/SCM 负责进程生命周期（§1-4）。这是唯一能覆盖「开机自启 + 无登录」的层，不能省。
2. **桥内层**（只补平台盲区，不做进程管理）：
   - `panic` hook：输出诊断后 `std::process::exit(101)`（非零）→ 平台立刻重启；
   - **主循环 stall 检测**（借鉴 [ogre-watchdog](https://github.com/zertyz/ogre-watchdog) 思路）：心跳线程监控主循环推进，超时判定假死 → 主动非零退出 → 平台拉起；
   - 可选：连 systemd 的 `WatchdogSec`/`sd_notify`（Linux）做带外存活探针；
   - 优雅关闭：监听 `SIGTERM`/`SERVICE_CONTROL_STOP`，先摘流量再落盘退出（`ExitTimeOut`/`TimeoutStopSec` 内完成）。
3. **不推荐**纯内置「父进程拉起子进程」替代平台：三平台重复造轮子、丢自启/无登录、退出码与孤儿进程语义复杂。除非桥内确需 worker 隔离（比如可崩溃的插件），才用子进程 + 父进程拉起那一层。

### 5.3 监控

平台状态（`systemctl status` / `launchctl print` / `sc query`）+ **桥自身心跳上报协调端**：心跳超时才是"真死"信号，平台重启是执行手段。心跳带上进程启动时间戳，可区分"刚重启"与"稳定运行"。

---

## 6. 日志轮转

### 6.1 推荐：桥自己写固定大小滚动日志（唯一事实源）

用 `flexi_logger`（大小+时间双触发、保留份数、跨平台）或 `tracing-appender`（时间轮转为主）。理由：

1. **三平台行为一致**——一套代码、一套轮转语义、一套清理策略，不用维护三套系统配置；
2. **绕开所有平台坑**（见下）；
3. 桥自己轮转时**必须用 reopen-on-rotate**（每次写前打开/或轮转时重新打开文件句柄），让外部工具（logrotate copytruncate、newsyslog）也能安全处理——不过既然自滚，外部就不需要了。

```toml
# config.toml（示意）
[log]
dir = "/opt/node-bridge/logs"        # 三平台各自绝对路径
rotate_size = "10 MB"
rotate_time = "1 day"
max_files = 14                        # 保留 14 份
level = "info"
```

### 6.2 三平台系统级方案（备选，各自局限）

| 平台 | 方案 | 机制 | 坑 |
|------|------|------|----|
| Windows | NSSM `AppRotateBytes`/`AppRotateOnline` | 大小触发，move 或 **copy-and-truncate**（应用持有句柄时用后者） | 只覆盖 NSSM 管的服务；原生服务模式没有系统轮转（得靠自滚） |
| macOS | **newsyslog**（`/etc/newsyslog.conf`） | 定时/大小触发 + 压缩，对 launchd 重定向出的固定文件有效 | launchd 的 `StandardOutPath` **本身不轮转**，必须靠 newsyslog 或自滚；文件需可写 |
| Linux | **logrotate** + **copytruncate** | 定时触发、压缩、保留份数 | 应用持有 fd 时必须 `copytruncate`（否则日志写到已删除 inode 上）；每次轮转触发一次 reload |

newsyslog 示例（macOS 备选）：

```
# /etc/newsyslog.conf 追加
/opt/node-bridge/logs/stdout.log  nodeuser:nodeuser  644  5  10000  *  J
/opt/node-bridge/logs/stderr.log  nodeuser:nodeuser  644  5  10000  *  J
```

logrotate 示例（Linux 备选）：

```
# /etc/logrotate.d/node-bridge
/opt/node-bridge/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate        # 桥持有 fd，必须 copytruncate
}
```

journald 限额（Linux 主日志）：`/etc/systemd/journald.conf` → `SystemMaxUse=500M`，`systemctl restart systemd-journald`。

### 6.3 结论

**双写策略**：① 桥自滚文件（`flexi_logger`，大小+时间+保留份数）作为排障唯一事实源；② 平台日志（journald / Windows Event Log / launchd 重定向）只写启动/退出/致命事件（`--daemon` 下由平台重定向 stdout/stderr 即可）。Windows 原生服务模式没有系统轮转，自滚是唯一一致解——这也是推荐自滚的最强理由。

---

## 7. 参考链接

- NSSM 官方/社区：<https://nssm.cc/> · <https://github.com/burgerbecky/nssm>（2.27 fork）
- WinSW：<https://github.com/winsw/winsw> · [Servy vs NSSM vs WinSW 对比](https://dev.to/aelassas/servy-vs-nssm-vs-winsw-2k46)
- Rust Windows 服务：<https://github.com/mullvad/windows-service-rs> · [DeepWiki: Getting Started](https://deepwiki.com/mullvad/windows-service-rs/2-getting-started) · [Core Concepts](https://deepwiki.com/mullvad/windows-service-rs/3-core-concepts)
- Windows 任务计划安全上下文：<https://learn.microsoft.com/en-au/previous-versions/windows/it-pro/windows-server-2008-r2-and-2008/cc722152(v=ws.10)>
- launchd：<https://keith.github.io/xcode-man-pages/launchd.plist.5.html> · [launchd 深度参考](https://github.com/0xdarkmatter/claude-mods/blob/main/skills/mac-ops/references/launchd-deep-dive.md)
- systemd：<https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html> · [systemd 生产实践（Restart/StartLimit/硬化）](https://stackharbor.com/en/knowledge-base/systemd-unit-patterns-production/) · [systemd.unit(5)](https://manpages.debian.org/buster-backports/systemd/systemd.unit.5)
- NSSM 日志轮转实现：<https://deepwiki.com/kirillkovalenko/nssm/6.2-file-rotation-and-timestamping>
- Rust 进程内 watchdog：<https://github.com/zertyz/ogre-watchdog> · <https://lib.rs/crates/ogre-watchdog>
- 日志轮转通用：<http://www.mdwiki.org/wiki/Log_rotation>
