# DSH 多会话重启后「会话丢失 / 被其他会话截断」根因分析与根治方案

> 分析日期：2026-08-15　分析对象：本机实际运行环境（`~/.dsh`，profile `web`，dsh 0.1.0-rc.6）
> 产出会话：session-b278baab（会话持久化根因研究）

---

## 一、结论（TL;DR）

**根本原因：同一份会话存储（`~/.dsh/sessions` + `~/.dsh/storages`）同时被两个互相不知道对方的 dsh 服务器进程占用，而持久化层没有任何跨进程互斥（锁/租约）机制。** 持久化层的正确性（内存游标续 seq、撕裂尾部修复时 truncate、每会话串行化）全部建立在「同一时刻只有一个进程持有该根目录」的假设上，但当前机器上这个假设被打破了：

1. **本机现在正同时跑着两个 dsh web 服务器**（端口 3080 的 npx 实例 + CLD.app 桌面壳内置实例），同一 profile、同一 `~/.dsh` 根。
2. 已在本机会话日志里找到**实证**：`session-c73d4226` 与 `session-ce836fb7` 两个日志文件出现**重复 seq**——两个进程用各自**陈旧的 in-memory 游标**并发 append，事件互相覆盖。两次重复 seq 的时间（16:19:48、16:22:22）都发生在 **CLD 每次启动后约 5 秒**，与 CLD 的 4 次启动日志一一对应。
3. 会话「丢失」来自三个叠加因素：CLD 退出时用 **SIGKILL** 杀掉 dsh 子进程（写入后端的 200ms 写合并窗口内的尾部事件来不及落盘即丢失）；`workspace.json` 会话清单是**整文件 last-write-wins**（两个进程各自一份内存态，谁后写谁覆盖，一个进程里新建的会话会在清单里消失）；未落盘的会话在重启后不可见。

---

## 二、本机证据

### 2.1 两个服务器同时在线（同一 root）

| 进程 | 来源 | 端口 | 使用的 profile / 根 |
|---|---|---|---|
| PID 46438（node 25.5.0） | `~/.npm/_npx/1e7f6d9597241db0/.../@deepseek-ai/dsh/lib/bin.js`（终端 ttys000 启动） | **3080**（即当前 GUI） | `~/.dsh/profiles/web`，会话根 `~/.dsh/sessions` |
| PID 46823（CLD.app） | `/Applications/CLD.app/.../dsh-runtime/.../bin.js web --port 0`（端口 64439） | 随机 | 同一 `~/.dsh/profiles/web`，同一 `~/.dsh/sessions` |

CLD 当日启动记录（`~/.cld/logs/dsh-web.log`）：16:06、16:09、16:19、16:22 —— 每次都和 3080 服务器重叠运行。

### 2.2 会话日志中的重复 seq（跨进程写入铁证）

对 8 个会话日志逐一用真实解码器（`decodeStorageRecord`）检查：

| 会话 | 重复 seq | 事件对 | 时间（本地） |
|---|---|---|---|
| `session-c73d4226…` | 136804 / 136805 | 先写 `step/end`+`turn/end`（关回合），紧接着另一进程写 `reasoning-chunks`（seq0=136804，同一回合还在流式输出） | **16:22:22**（CLD 16:22:17 启动后 4.8s） |
| `session-ce836fb7…` | 171280 / 171281 | 同上模式 | **16:19:48**（CLD 16:19:43 启动后 5s） |

含义：两个服务器各自内存里都认为「下一个 seq 是 136804」，A 写了 `step/end`+`turn/end`，B 用陈旧游标把同一序号的流式 chunk 追加在后面 → 同一会话文件里出现两个 136804/136805。任何读取方都会看到「回合已结束后又冒出 chunk」的坏表面，这正是用户看到的「会话被截断/错乱」。

### 2.3 会话清单不一致（workspace.json vs 磁盘）

- `~/.dsh/storages/workspace.json` 的 `sessionIds` 缺了磁盘上确实存在的 `session-45f89009…`、`session-9cb82993…`；
- 两个会话目录在磁盘上、日志完好（`45f89009` maxSeq=98，`9cb82993` maxSeq=3），只是没进任一服务器的清单；
- `workspace.json` 被两个服务器**整文件覆盖**（原子替换，谁后写谁赢），互相看不见对方新建的会话。

---

## 三、根因链（按代码位置）

### 根因 1：持久化层零跨进程互斥（主根因）

- `dsh-session-persistence` 的 `PersistenceCoordinator` 所有串行化（`serialize()`，lib/index.js:1079）都是**进程内 per-id promise 链**；`states`/`live`/`chains` 全部是进程内对象。
- `appendCore`（lib/index.js:829-840）只校验「事件 seq == 内存游标 + i」，**从不先读文件确认磁盘上已推进到哪**。另一个进程已把文件写到 136805，本进程仍从 136804 开始写 → 重复 seq 静默落盘。
- `commitRepair`（lib/index.js:1025-1027 → jsonl `repair()`，lib/index.js:1238-1247）会 `truncate()` 文件：A 进程读到撕裂尾部（B 正在写一半）就会把 B 刚写的帧裁掉 → 这就是「被其他会话截断」的另一种直接机制。
- `appendLines`（jsonl lib/index.js:1200-1227）用 `open(path,"a")` 无锁追加；`materialize` 用硬链接发布（lib/index.js:1128），两个进程并发创建同一会话时一个会抛「refusing to materialize」。
- 全代码库 grep 不到任何 `flock`/`lease`/跨进程锁。

### 根因 2：CLD 退出用 SIGKILL，写合并尾部必丢

- dsh 写入采用「每会话 write-behind 批量合并，默认窗口 200ms」（`DEFAULT_WRITE_BATCH_MAX_DELAY_MS=200`）；事件先进内存队列，200ms 后才 fsync 落盘。
- dsh 自己优雅停机预算 5s（profile-boot `PROCESS_SHUTDOWN_TIMEOUT_MS=5000`），SIGTERM 时 `fiber.dispose()` 会 drain 全部 write-behind。
- 但 CLD 的 `main.js`：`before-quit` 发 SIGTERM 后 3s 补 SIGKILL，**且 `process.on("exit")` 里无条件 `child.kill("SIGKILL")`** —— Electron 正常退出时立刻 SIGKILL 子进程，dsh 的 5s dispose（含 flush）基本没有机会跑完 → 每个会话最后 ≤200ms（外加正在写的大帧）的尾部事件丢失 → 「会话丢失/尾部截断」。CLD 的 3s 也短于 dsh 的 5s 预算。

### 根因 3：workspace 清单是整文件 last-write-wins

- `dsh-storage-json` 整文件原子替换（tmp+rename），注释明说「one writer per process and last-write-wins is correct」——默认只有一个进程。
- `dsh-workspace` 的 `sessionIds` 只在**创建会话时**（dsh-host-apiproxy lib/index.js:2617、2809 调 `attachSession`）加入，重启后**不会**用 `list()` 回填磁盘上已存在的会话 → 两个服务器各写各的，后写者覆盖，另一边的会话从清单消失。

### 根因 4：会话延迟物化（次要）

- `createCore`（lib/index.js:808-816）只登记元数据，**首次 append 才写文件**。空会话（无 seed 事件）若在写合并窗口内被 SIGKILL，磁盘上什么都没有 → 重启后从列表消失。

---

## 四、根治方案（分层）

### 第 0 层：立刻可做（本机，不需要改代码）

1. **同一时间只跑一个 dsh 服务器**：关掉多余的实例（3080 npx 终端实例 或 CLD 桌面壳，二选一），或让 CLD 用独立 profile/根（`DSH_HOME`/`--profile` 分开）。这一步直接消除根因 1，能立刻止血。
2. 重启 CLD 前先确认 3080 实例（或另一实例）已停止；不要「开着浏览器端 + 桌面端」同时聊天。

### 第 1 层：持久化层加「根目录单写者租约」（根治根因 1，需改 `@deepseek-ai/dsh-session-persistence-jsonl`）

在 `JsonlSessionPersistence` 打开根目录时获取独占租约（建议放 `assertUsableRoot()` 处）：

- 用 `O_EXCL` 创建 `<root>/.dsh-owner` 锁文件，写入 `{pid, startedAt, heartbeat}`；持锁进程定期更新 mtime 心跳；`dispose` 释放。
- 第二个进程启动时读到锁：检查 PID 是否存活（`process.kill(pid,0)`），存活 → **拒绝启动**并给出明确报错（「另一 dsh 实例（PID x）正占用该会话根，请先停止它或使用独立根目录」）；已死 → 判定为陈旧锁，安全接管（PID 存活性 + 心跳过期双确认，避免误杀）。
- 备选：用 `proper-lockfile` 之类成熟库（O_EXCL + 陈旧检测）实现，约几十行。
- 同理 `dsh web`/`dsh headless` 都应在 boot 时拿锁（它们都写会话）。
- **注意**：进程内 `serialize()` 链保留不动；租约只解决「多个进程」这一层。

### 第 2 层：coordinator 加「写前校验 + 冲突即报错」（防御纵深，需改 `dsh-session-persistence`）

即使有了租约，也应把「静默损坏」变成「可检测冲突」：

- `appendCore` 在 `appendBatch` 前用 `readStoredRevision(id)` 快速比对：revision 与内存游标最后确认的一致 → 正常写；不一致 → 走 `adopt()` 重新加载：
  - 若磁盘前缀与本次待写事件**顺序一致**（即别人只是把文件往前推了，我们的事件正好接续）→ 合并游标后只追加后缀；
  - 否则（seq 重叠，如今天的重复 seq 场景）→ **抛错 fail-loud**，绝不静默覆盖。
- 撕裂尾部修复（`commitRepair` 的 truncate）只允许**持锁进程**执行。

### 第 3 层：消灭「重启丢尾部」（改 dsh + CLD）

- **dsh 侧**：`installWritePath()` 里监听 `session/event`，对 `turn/end` 事件立即 `flush(session)`（投影缓存已经这么做了，持久化层照做即可）→ 完整回合 100% 落盘，尾部丢失窗口从「整个回合」缩小到「回合内最后几百 ms 的流式 chunk」。
- **CLD 侧**：删掉 `process.on("exit")` 里的无条件 SIGKILL；SIGTERM 后等待子进程自然退出（放宽到 ≥ dsh 的 5s 预算，例如 8-10s）再兜底。这是对用户来说收益最大、成本最低的一处修复。

### 第 4 层：会话清单收敛（改 `dsh-workspace` / UI 数据源）

- `dsh-workspace` 初始化时用持久化 `list()` 回填 `sessionIds`：把磁盘上存在、cwd 匹配本工作区、但不在清单里的会话幂等补挂（`attachSession` 本身幂等，天然安全）。
- 更彻底：UI 会话列表以持久化 `list()` 为准（数据源），workspace 只负责排序/分组展示。
- 配合第 1 层的单写者租约，两个进程不再同时写 `workspace.json`，last-write-wins 冲突自然消失。

### 第 5 层（可选）：会话创建即物化

- `createCore` 在登记元数据时同步落盘 header（哪怕还没有事件），保证任何会话创建后立即在磁盘可见，SIGKILL 也不丢「整个会话」。

---

## 五、优先级建议

| 优先级 | 动作 | 成本 | 效果 |
|---|---|---|---|
| P0 | 停止双服务器（本机立刻执行） | 零 | 立即消除正在发生的重复 seq/截断 |
| P1 | CLD 退出不 SIGKILL（改 main.js / 等上游修） | 小 | 消除「每次退出丢尾部」 |
| P1 | 持久化层根目录单写者租约 | 中 | 根治跨进程并发写 |
| P2 | coordinator 写前校验 + 冲突报错 | 中 | 防御纵深，损坏变可见错误 |
| P2 | workspace 清单回填 / 以 list() 为数据源 | 小 | 根治「会话从列表消失」 |
| P3 | turn/end 立即 flush | 极小 | 进一步缩小丢尾部窗口 |

---

## 六、附：本机当前状态快照（分析时点 16:30）

- 两个服务器均在运行；`session-908749c1…`、`session-b278baab…` 等日志在 16:24-16:30 持续被写入（两进程都在写）。
- 磁盘 8 个会话日志**当前结构完好**（无 torn frame、无 parse error），说明损坏是「写坏」而非「文件烂」，越早止血越好。
- 已发现的重复 seq 不影响历史完整性（只是同一 seq 出现了两条），但任何一次新的并发写都可能让日志进入不可恢复状态（seq 缺口 + 撕裂帧 → 下次加载直接报 corrupt）。
