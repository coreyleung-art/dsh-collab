# Rust 常驻守护进程（节点桥）依赖选型调研报告

> 场景：跨平台（Windows x86_64 / Linux x86_64 / macOS arm64）常驻守护程序。职责单一：每 2-5s 向黑板服务（HTTP JSON API：`GET /tasks/...`、`POST /result`、`PUT heartbeat`）长轮询/上报 → 解析 JSON → 执行本地 shell 命令 → 回报 stdout/stderr。
> 硬约束：内存占用低、启动快、单二进制免安装、代码量小、易交叉编译。
> 调研日期：2026-07；方法：web_search 多角度检索 + 一手信源交叉验证（详见文末「数据来源与噪音排除」）。

---

## 0. 结论摘要（推荐栈一句话）

**纯 `std::thread` + `std::net`（无 async 运行时）＋ `ureq` 2.x（`default-features = false`，纯 HTTP/1.1 无 TLS）＋ `serde`/`serde_json`（按需 derive）＋ `log` + `env_logger`（Windows 上 `Target::Pipe` 落文件）；将来要 HTTPS 时仅需给 ureq 开 `tls` feature（默认即 rustls，纯 Rust、零系统依赖）。**

- **运行时**：不需要 tokio。这是顺序执行的同步阻塞型轮询负载，单线程死循环 + `thread::sleep` 心跳即可，tokio 只带来体积、内存与心智负担。
- **HTTP**：ureq 2.x 同步客户端（连接池/重定向/三级超时齐备，依赖树个位数）。不选 reqwest（tokio+hyper 全家桶），不选手写 HTTP（除非体积硬指标 < 500KB 且你完全控制服务端）。
- **JSON**：serde + serde_json。协议虽薄但会增长，serde_json 体积代价仅 ~150-300KB，手写解析器不划算。
- **日志**：`log` facade + env_logger；Windows 无 console 时 stdout 句柄无效（`println!` 会 panic），必须 `Target::Pipe` 到文件。
- **体积/内存预期**：无 TLS 版二进制 **≈ 0.4–0.8 MB**（Linux x86_64），加 rustls 后 **≈ 1.3–1.8 MB**；常驻 RSS **≈ 3–8 MB**（单线程）。对照：reqwest+tokio 方案 ≈ 3–4 MB / RSS 15–30 MB。

---

## 1. 异步运行时：到底需不需要 tokio？

**结论：不需要。** 该守护进程的负载是「一个线程顺序执行：请求 → 解析 → 跑命令 → 回报」，全程同步阻塞，无并发、无高吞吐、无大量并发连接需求。轮询间隔 2-5s 本身远大于任何单次操作耗时，异步的「省线程」收益为零。

| 方案 | 二进制增量(估) | 常驻内存(估) | 代码复杂度 | 适用性 |
|---|---|---|---|---|
| (a) tokio 全量（`features=["full"]`） | +2–4 MB（含 hyper 等间接依赖） | 多线程 runtime：worker 线程(默认=核数) + 每线程 2MB 栈 + epoll/kqueue 事件循环 + timer wheel，RSS 常见 15–30 MB | 高：async fn / await / spawn / 错误跨 await 传播 | ❌ 完全不需要 |
| (b) tokio 最小 feature（`rt` + `net` + `time` + `macros` + `sync`） | +1–3 MB | 仍要一个 runtime + 事件循环；current_thread 模式可降到 ~10 MB 上下 | 中高：仍是 async 心智 | ❌ 收益仍为零 |
| (c) **纯 `std::thread` + `std::net`（推荐）** | +0 | 单线程：二进制映射 + 小堆 + 1 个栈，RSS 3–8 MB | 最低：普通同步代码，`thread::sleep` 即定时器 | ✅ 完全够用 |
| (d) async-std / smol | smol +0.3–1 MB（比 tokio 轻）；async-std 接近 tokio | 均需 runtime 线程与事件循环 | 中 | ❌ 生态弱、无收益 |

**理由（按你的四项约束逐条）：**

1. **轮询是同步阻塞型负载**：`ureq` 的 `.call()` 本身就是阻塞 API，包一层 async 纯属「为了异步而异步」。单连接串行轮询，没有任何等待点需要并发调度。
2. **心跳是定时器**：`std::thread::sleep(Duration)` 在 2-5s 粒度下精度绰绰有余；如需补偿漂移，用 `std::time::Instant` 计算下一拍起点即可。tokio 的 `interval()` 在这里毫无优势。
3. **代码要简单可维护**：纯 std 方案全程序没有 `async`/`await`/`Pin`/`Send` 边界，错误处理就是普通 `Result`，新人可读。
4. **二进制要小**：tokio 最小 feature 仍带来 1MB+ 体积与事件循环内存；纯 std 为零增量。
5. 如果未来出现「跑 shell 命令要 30s，而轮询不能阻塞」的需求，`std::thread::scope` 开 1-2 个工作线程 + `mpsc` 通道即可，依旧不需要 async 运行时。

**纯 std 方案的长轮询超时可行性论证（可行）：**

- 连接超时：`TcpStream::connect_timeout(addr, Duration)`（std 稳定 API，1.21+）。
- 读超时：`TcpStream::set_read_timeout(Duration)` 设置 SO_RCVTIMEO；超时到期后 `read()` 返回 `Err(io::ErrorKind::WouldBlock)`（个别平台/旧版本可能为 `TimedOut`，代码里两个分支都处理）。
- 长轮询语义：设 `read_timeout` 略大于服务端 hold 时长（如服务端最长 hold 60s，则设 70-90s），到期即 `WouldBlock` → 关连接 → 下一轮重连。这是长轮询的标准退避循环。
- 注意点：手写客户端要自己处理 HTTP 头解析、`Content-Length`/chunked、半包粘包缓冲、`Connection: keep-alive` 复用；服务端必须总是发 `Content-Length`（黑板服务是你们自己的，可强制）。

> 推论：既然纯 std 能覆盖全部需求，**ureq 的「同步、无 runtime」定位与此完全一致**——它替你把 HTTP 细节（超时、重定向、连接池、Content-Length 解析）都做完了，却不需要引入任何异步运行时。所以推荐栈是「std 线程 + ureq」，而不是「std 线程 + 手写 HTTP」也不是「tokio + reqwest」。

---

## 2. HTTP 客户端：reqwest vs ureq vs 手写

| 维度 | reqwest (blocking) | **ureq 2.x** | 手写 HTTP/1.1 | tiny_http |
|---|---|---|---|---|
| 运行时依赖 | tokio（blocking 内部也要起 runtime）| 无（纯同步）| 无 | 无（但它**是服务器库**，不是客户端）|
| 依赖树 | ~50+ 传递依赖（hyper/tower/http/tokio…）| 个位数（`default-features=false` 时：log/once_cell/url 等）| 0 | n/a |
| 默认 TLS | 默认 `default-tls` = native-tls（Windows 走 schannel / Linux 走 openssl）| 默认 `tls` = **rustls**（纯 Rust，webpki-roots）| 无 | n/a |
| 无 TLS 纯 HTTP | 需 `default-features=false` 显式关 | `default-features=false` 即纯 HTTP/1.1，零 TLS 代码 | 天然无 | n/a |
| 重定向 | 默认跟随（上限 10）| 默认跟随（上限 10，可配）| 自己写（或直接不做）| n/a |
| 超时 | connect/read/write + 总超时 | `timeout_connect`（默认 30s）/`timeout_read`（默认**无**！）/`timeout_write`/`timeout`（总超时）| `connect_timeout`/`set_read_timeout` 自己拼 | n/a |
| 连接池 | hyper 池 | Agent 池，默认 per-host 1 条空闲连接（2-5s 轮询正合适）| 自己维护 keep-alive | n/a |
| Windows 交叉编译负担 | 用 native-tls 需处理 openssl；用 rustls 无痛但体积大 | rustls 纯 Rust，交叉编译零系统依赖 | 无依赖 | n/a |
| 实测体积（tealdeer 全 CLI 对比，见文末来源）| 默认 4.01 MB / native-tls 3.29 MB | 默认 3.50 MB（-12%）/ webpki-roots 3.18 MB（-19%）/ native-tls 2.18 MB（-33%）| — | — |

**推荐：ureq 2.x。** 三个论据：

1. **fnm 官方 commit 实证**：fnm（Node 版本管理器）把 reqwest（blocking+json+rustls-tls+brotli）换成 ureq 2.2 + url，Cargo.lock 净减 **442 行**（+28/-442），这正是「依赖树体积」差距的直接证据。
2. **tealdeer 实测**：同样功能下 ureq 比 reqwest 小 12–33%；rustls 加密库本身约占 1MB，是二进制中 TLS 部分的成本大头——你们内网纯 HTTP 时直接砍掉这 1MB。
3. **API 直接命中长轮询**：`AgentBuilder::timeout_read()` 是「单次 read 超时」，正好覆盖长轮询（服务端 hold 期间不发字节、不发超时）场景；`timeout_connect()` 防挂死；`.timeout()` 做总时长保险。

**关于 TLS 的未来路径（明确回答）**：将来要 HTTPS 时，给 ureq 开 `tls` feature 即可——**默认就是 rustls**（纯 Rust，webpki-roots 内置根证书），**不要用 native-tls**：native-tls 在 Linux 交叉编译时需要系统 openssl 头文件/库，是跨平台构建的最大痛点；rustls 全平台零系统依赖。Windows 上 native-tls 虽走 schannel（免装库），但为了三平台一致性与 CI 简单，rustls 是唯一合理选择。

**手写 HTTP/1.1 的适用边界**：只有当「体积硬指标 < 500KB」且「黑板服务完全由你控制（强制 Content-Length、无 chunked、无重定向）」时才值得——约 150-250 行代码，但要自己处理半包/粘包、keep-alive 复用、超时分支。对你们这种「职责单一、代码量小」的诉求，ureq 已是体积/健壮性的最优平衡点。

> 澄清：`tiny_http` 是 **HTTP 服务器**库（做本地接收端用的），没有「客户端」一说；若有人用它做客户端，等于手写 HTTP。本场景不需要它。

---

## 3. JSON 解析：serde_json vs json crate vs 手写

**结论：serde + serde_json。** 协议虽薄（key-value + 字符串数组），但：

| 方案 | 体积增量(估) | 依赖 | 能力边界 | 评价 |
|---|---|---|---|---|
| **serde + serde_json（derive）** | ~150–300 KB | serde + serde_derive（syn/quote/proc-macro2，仅编译期）| 完整：任意嵌套/类型/错误定位 | ✅ 推荐 |
| serde_json::Value（不 derive）| ~150–250 KB | 仅 serde_json（itoa/ryu/memchr，无 proc-macro）| 动态 Value，手写取字段 | ✅ 薄协议够用、编译更快 |
| json crate | ~100–200 KB | 极少 | API 老旧、维护停滞、错误信息差 | ⚠️ 不推荐 |
| miniserde | ~80–150 KB | 少 | 仅 derive、无任意 Value | ⚠️ 协议增长后受限 |
| 手写解析器 | +0 | 0 | 只能应付你已知的固定格式 | ❌ 边界 case 多（转义/unicode/数字/错误恢复），省不了多少体积还难维护 |

**理由**：
- serde_json 的运行时依赖（itoa/ryu/memchr）都是纯 Rust 零依赖小库，交叉编译零负担。
- 协议「很薄」只是**今天**很薄——`/tasks` 响应里迟早会出现嵌套对象、数组、可选字段；serde derive 给类型安全，`Value` 模式给灵活性，两者随时可切。
- 手写解析省下的 ~150KB 换来的是一堆容易出错的边界处理，且每次协议改动都要改解析器；对「代码量小、可维护」是负分。
- 权衡：若想极致控制编译时间/二进制，先上 `serde_json::Value`（不启用 serde derive），协议字段稳定后再补 derive。

---

## 4. 日志：env_logger / simplelog / println 重定向？

**结论：`log` facade + `env_logger`，Windows 无 console 时用 `env_logger::Builder::target(env_logger::Target::Pipe(Box::new(file)))` 落文件。** 不推荐 println。

| 方案 | 优点 | 缺点 |
|---|---|---|
| **env_logger（推荐）** | 与 ureq 共用 `log` crate（ureq 的 DEBUG/TRACE 日志可直接开启）；RUST_LOG 过滤、时间戳；`Target::Pipe` 可重定向到任意 `Write`（含文件）| Windows GUI subsystem 下默认 stderr 无效，必须显式 Pipe 到文件 |
| simplelog | 自带 `WriteLogger` 落文件、`TermLogger` 终端 | 无内置轮转；多一层抽象 |
| println! + 重定向 | 零依赖 | **Windows 上不可行**：`#![windows_subsystem = "windows"]` 下 stdout/stderr 句柄无效，`println!` 写失败会 **panic**（"failed printing to stdout"）；且进程崩溃时输出缓冲区可能丢 |
| tracing + tracing-subscriber | 结构化/span | 对单职责守护进程过重，编译体积 +300KB 上下 |

**Windows 上日志落地的具体建议**：
1. `#![cfg_attr(windows, windows_subsystem = "windows")]` 之后，**禁止一切 println!/eprintln!**，统一走 `log`。
2. 启动时打开 `%APPDATA%\<app>\node-bridge.log`（用 `dirs` crate 或 `std::env::var("APPDATA")`），`env_logger::Builder::target(Target::Pipe(Box::new(file)))`。
3. 轮转：简单方案是「按天归档」——启动时若当日文件已存在则追加；或加一个按大小截断的极简 wrapper（~30 行）。Linux 端可配合 logrotate。
4. 加 `std::panic::set_hook` 把 panic 信息写进同一文件（配合 `panic = "abort"`，崩溃至少留痕）。
5. 生产 Windows 服务模式（见 §6）下，日志就是文件 + Windows 服务自身的 `ServiceExitCode`。

---

## 5. 二进制体积与内存：预期量级

**体积基线（实测/公认数据）**：
- min-sized-rust（官方基准仓库）：macOS stripped + `-Z build-std` + `optimize_for_size` → **51 KB**；加 `panic_immediate_abort` → **30 KB**；`no_std` 极限 → **8 KB**（nightly-only，仅供量级参照）。稳定版常规优化（`strip + lto + opt-level="z" + panic="abort" + codegen-units=1`）的 hello world：Linux x86_64 **≈ 150–250 KB**。
- tealdeer 实测（完整 CLI 应用）：reqwest 默认 **4.01 MB** vs ureq 默认 **3.50 MB**（-12%）；rustls 加密库本身 ≈ **1 MB**。
- fnm：换 ureq 后 Cargo.lock **-442 行**。

**本守护进程的预期体积（估算，标注依据）**：

| 组合 | Linux x86_64 二进制(估) | 依据 |
|---|---|---|
| 纯 std + serde_json::Value（无 HTTP 库、无 TLS）| ~0.3–0.5 MB | hello world 基线 + serde_json ~150KB |
| **std 线程 + ureq(无 feature) + serde_json + env_logger（推荐）** | **~0.4–0.8 MB** | 基线 + ureq 核心 ~200-400KB + serde_json |
| 上者 + ureq `tls`（rustls，将来 HTTPS）| ~1.3–1.8 MB | +rustls ~800KB–1MB |
| tokio 最小 feature + reqwest(blocking, rustls) | ~3–4 MB | tealdeer 4.01MB 为全 CLI；裸 daemon 更低但同量级 |
| Windows PE 版本 | 通常比 Linux 小 10–30% | PE 无 .symtab，strip 更彻底 |

**内存预期（估算）**：
- **推荐栈（单线程 std + ureq）RSS ≈ 3–8 MB**：1 个线程栈（8MB 虚拟、按需提交）+ 二进制映射 ~1-2MB + ureq 连接池 1 条连接 + 分配器 arena（glibc/jemalloc 默认）。远低于任何常规门槛。
- tokio+reqwest 对照 RSS ≈ 15–30 MB：worker 线程组（默认 = CPU 核数，每线程 2MB 栈虚拟）+ 事件循环 + hyper 连接池 + 分配器。即使 `current_thread` 模式也难低于 ~10MB。
- 启动时间：两者都是毫秒级，纯 std 方案（无 runtime 初始化）更快，常驻进程通常只看稳态内存。

> 均为量级估算，最终以三平台 `cargo build --release` 后 `size`/`du` 与 `/proc/<pid>/status` 实测为准（建议 CI 里加一步体积断言防回归）。

---

## 6. Windows 特殊性（坑清单）

1. **无 console 窗口**：crate 根加 `#![cfg_attr(windows, windows_subsystem = "windows")]`。后果：stdout/stderr 句柄无效 → **`println!`/`eprintln!` 会 panic**（"failed printing to stdout"），必须走文件日志（§4）。调试期可用 `RUST_LOG` + 临时 `Target::Pipe`。
2. **真正的服务模式**：生产环境用 **`windows-service` crate**（mullvad/vsrs 维护）：`define_windows_service!` 宏 + `service_dispatcher::start(name, ffi_main)`，并注册 `ServiceControl::Stop` 事件、上报 `ServiceState::Running`。服务在 **Session 0** 无桌面交互。轻量替代：`windows_subsystem` 普通进程 + NSSM 或任务计划程序自启（NSSM 还提供崩溃自动重启，配合 `panic="abort"` 兜底）。
3. **退出码**：`std::process::exit` 接收 `i32`，但 Windows 退出码是 **u32**——负数会回绕（`-1` → `4294967295`）。统一用 `0/1/2` 等小正整数；服务模式用 `ServiceExitCode::Win32(0)`。
4. **命令输出编码（高频坑）**：`Command::output()` 返回**原始字节**，编码取决于子进程写 stdout 时用的控制台代码页——中文 Windows 默认 **GBK/cp936**，`String::from_utf8_lossy` 会得到乱码。两个可靠方案：
   - 方案 A（推荐）：执行时前缀 `cmd /C chcp 65001 >nul & <命令>`，强制子进程 UTF-8 输出，再用 `from_utf8_lossy` 解码。
   - 方案 B：直接解码 GBK，加 `encoding_rs`（`encoding_rs::GBK.decode(&bytes)`），仅 `cfg(windows)` 依赖，不污染其他平台。
   - 注意 PowerShell 与 cmd 输出编码行为不同，固定用 cmd 路径。
5. **交叉编译**：
   - Windows MSVC 目标（`x86_64-pc-windows-msvc`）：用 **cargo-xwin**（自动下载 CRT/头文件，`cargo xwin build --release`），免装 MSVC 即可从 macOS/Linux 交叉构建；rustls 纯 Rust，无 openssl 痛点。
   - Linux：原生编译或 `x86_64-unknown-linux-musl` 出全静态单文件（体积 +~200-400KB）。
   - macOS arm64：需在 macOS 机器/CI runner 构建（Apple SDK 依赖），无法跨平台出 mac 目标。
6. **ureq 超时默认值陷阱**：`timeout_read` **默认无超时**（可永久阻塞）——长轮询必须显式设置，且它只作用于「单次 read」；总时长用 `.timeout()` 兜底。连接池默认 per-host 1 条空闲连接，够用。
7. **路径**：配置/日志目录用 `%APPDATA%`（`dirs` crate 或 `std::env::var`），别硬编码分隔符。
8. **杀软/签名**：未签名 exe 可能被 Windows Defender/企业策略拦截或告警；分发时考虑代码签名或加排除项。
9. **panic=abort 的后果**：任何 panic 直接进程退出（无 unwinding 清理）——依赖外部 supervisor（NSSM/服务 SCM/launchd/systemd）自动拉起。
10. **心跳精度**：`std::thread::sleep` 走 `Sleep()`，2-5s 粒度足够；用 `Instant` 补偿循环漂移，避免长期累积偏移。

---

## 7. 推荐 Cargo.toml（feature 已精简）

```toml
[package]
name = "node-bridge"
version = "0.1.0"
edition = "2021"

[dependencies]
# ── HTTP：纯 HTTP/1.1 内网轮询。将来要 HTTPS 时把 features 改为 ["tls"]（=rustls，纯 Rust）
ureq = { version = "2", default-features = false }        # 不需要 gzip/TLS/cookies/charset

# ── JSON：薄协议先用 serde_json::Value；字段稳定后再开 derive
serde = { version = "1", features = ["derive"] }          # 不想用 derive 可删这行
serde_json = "1"

# ── 日志：log facade + env_logger；Windows 上用 Target::Pipe 落文件
log = "0.4"
env_logger = "0.11"

# ── 仅 Windows：命令输出 GBK 解码 + 服务注册（简单部署可只留 encoding_rs）
[target.'cfg(windows)'.dependencies]
encoding_rs = "0.8"                                       # 解码 GBK 输出（或用 chcp 65001 方案可删）
windows-service = { version = "0.7", features = ["service"] }  # 生产服务模式

[profile.release]
opt-level = "z"        # 体积优先
lto = true             # 链接期优化
codegen-units = 1
strip = true           # 剥离符号
panic = "abort"        # 去掉 unwind 代码（配合外部 supervisor 重启）
```

main.rs 顶部：`#![cfg_attr(windows, windows_subsystem = "windows")]`

核心循环骨架（示意）：

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(5))
        .timeout_read(std::time::Duration::from_secs(90))   // 长轮询：略大于服务端 hold
        .timeout(std::time::Duration::from_secs(100))       // 总超时兜底
        .build();
    loop {
        let started = std::time::Instant::now();
        // 1) GET /tasks/...（长轮询） → 2) serde_json 解析 → 3) Command 执行 → 4) POST /result
        // 5) PUT heartbeat
        let elapsed = started.elapsed();
        std::thread::sleep(std::time::Duration::from_secs(2).saturating_sub(elapsed)); // 补偿漂移
    }
}
```

---

## 8. 参考链接

**一手/权威**
- [min-sized-rust（官方体积最小化基准，含各阶段体积数字）](https://github.com/mikemadden42/min-sized-rust)
- [ureq 2.11.0 feature flags（默认 = gzip + tls，tls = rustls/webpki-roots）](https://docs.rs/crate/ureq/2.11.0/features)
- [ureq AgentBuilder 文档（timeout_connect/timeout_read/timeout_write 语义与默认值）](https://docs.rs/ureq/2.11.0/ureq/struct.AgentBuilder.html)
- [ureq README（charset/代理/log 集成/3.x 说明）](https://github.com/algesten/ureq)
- [fnm commit：Replace reqwest with ureq（Cargo.lock -442 行实证）](https://github.com/Schniz/fnm/commit/9c2e3605208a9a3980a2203f4bfc2bf72b9cc612)
- [windows-service crate（mullvad/vsrs，服务实现完整示例）](https://github.com/vsrs/windows-service-rs)
- [Writing a Windows Service in Rust（2026-02 实操文）](https://davidhamann.de/2026/02/28/writing-a-windows-service-in-rust/)
- [cargo-xwin（跨平台编 MSVC 目标）](https://github.com/nagua/cargo-xwin)
- [std::net::TcpStream set_read_timeout / connect_timeout（std 官方文档）](https://doc.rust-lang.org/std/net/struct.TcpStream.html)

**实测/佐证**
- [Tealdeer 项目 ureq 替代 reqwest 的二进制体积实测（4.01MB vs 3.50MB，rustls ≈1MB）](https://blog.gitcode.com/b057fa2483f13a5a7e0ef8f9ea3b2d59.html)
- [中文 Windows 下程序输出重定向乱码问题（GBK 编码坑）](https://blog.csdn.net/inksnowhl/article/details/148786073)
- [fnva 编码修复文档（Windows 输出编码处理实践）](https://github.com/Protagonistss/fnva/blob/HEAD/docs/user-guide/encoding-fixes.md)

**噪音排除记录**
- [rustify.rs 的 reqwest-vs-ureq-vs-hyper 2026](https://rustify.rs/articles/rust-reqwest-vs-ureq-vs-hyper-2026) 与 [async runtimes 2026](https://rustify.rs/articles/rust-async-runtimes-tokio-vs-async-std-2026)：抓取仅得 258–277 字符（JS 渲染空壳），无实质数据 → 排除，仅作标题线索。
- CSDN 多篇「Rust 异步运行时横向对比」（no1coder/etosss 等）：无作者可信度、二手拼贴、数据无法溯源 → 排除。
- pythonlib.ru、DuckDuckGo 聚合出的 lib.rs 目录页等 SEO 聚合站 → 排除。
- oneuptime.com 的 long-polling/Rust timeouts 教程：方向正确但内容浅、无版本细节 → 未采信具体数字。

**局限与待验证**
- 体积/内存数字为**量级估算**（依据 min-sized-rust 基线 + tealdeer 实测 + rustls ≈1MB 公认成本），最终以三平台实构建为准；建议 CI 加体积断言。
- tealdeer 数字来自二手转载博客，但方向性结论（ureq 更小、依赖更少）被 fnm 官方 commit（-442 行 lock）独立佐证。
- ureq 3.x 已发布（config_builder/Transport 新 API）；本报告按 2.x 稳定线给推荐（文档与生态示例最多），新项目可评估 3.x。
- 「println! 在 GUI subsystem 下 panic」为 Rust 社区公认行为（stdout 句柄无效、写失败即 panic），未逐版本实测；代码上以「禁用 println、统一 log」规避，不受该细节影响。
