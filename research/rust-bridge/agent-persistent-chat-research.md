# 多宿主 LLM 智能体「常驻对话 / 随时对话」调研报告

> 调研日期：2026-08
> 调研目标：多个相互独立封闭的 LLM 智能体宿主（Claude Code / DSH 这类独立进程）之间，如何实现「像微信一样，随时发消息对方就能回（不管对方会话是否激活）」
> 场景：mac-mini（中枢，DSH 宿主多会话）+ MBP（macOS，独立 DSH 宿主）+ i9（Windows，独立 DSH 宿主），已有 Rust node-bridge 常驻传输层（心跳/任务卡/inbox-outbox）+ 黑板 KV

---

## 0. 结论摘要（按可行性排序）

**核心结论：业界共识是「常驻传输层 + 按需唤醒推理」（Always-On Transport, On-Demand Inference），而不是让 LLM 会话本身常驻。** 所有被调研的主流方案（OpenClaw、Claude Code Channels、claudetalk、claude-relay、agent-channels、Claude Agent SDK）都验证了这一点：**消息通道 24/7 常驻，LLM 会话按消息惰性唤醒、处理完即退出**。我们已有的 node-bridge 正是「常驻传输层」，缺的是「唤醒器（waker）」这一环。

1. **【P0 · 最可行】事件驱动唤醒器（Headless + on-demand activation）**：node-bridge 收到 inbox 消息 → 本地唤醒器检查目标会话是否存活（pid 表）→ 无则用 headless 模式程序化拉起/续接会话（`claude -p --resume` / Agent SDK `query()` / DSH 的 `agents.resume`）→ 处理 → 回复写 outbox → 进程退出。常驻成本≈0 token，只有处理消息才烧 token，实时性秒级。参考实现：Claude Agent SDK、claude-relay 的 delegate wake、claudetalk 的 hooks 机制。

2. **【P1 · 会话存活期实时通道】官方 Channels / 跨会话消息**：Claude Code Channels（v2.1.80+，2026-03-20 发布）用 MCP server 把消息推入**正在运行**的会话；跨会话消息（v2.1.224，2026-08）支持不同终端/不同机器会话互发。**关键限制：会话必须开着才收得到消息——它解决「在线实时」但不解决「未激活」**，必须与 P0 配合。

3. **【P1 · 文件/黑板通道】append-only 通道 + watch 原语**：agent-channels 模式——每个话题一条 append-only JSONL 文件（flock 写、fsync），`channels watch` 阻塞等待新消息（零 token 空闲、来消息 exit 0 触发）。与我们已有的黑板 KV 结构同构，可无缝复用。

4. **【P2 · 协议标准化】A2A / MCP-remote / MMP**：Google A2A（JSON-RPC 2.0 + agent card + Task/Message，SSE 流式）是跨厂商 agent 互操作的事实标准草案；MCP streamable HTTP 把端侧暴露为远程工具面；MMP（Mesh Memory Protocol）提供身份 + 认知消息 + 接收方准入。用于把 node-bridge 的消息格式标准化，非必需。

5. **【P3 · 中心化编排】durable execution / gateway daemon**：Temporal 把 agent 执行做成可断点续跑的工作流（signal 唤醒、query 查询）；OpenClaw 的 Gateway daemon（launchd/systemd 用户服务）是「常驻网关 + RPC 入口 + webhook/cron 触发」的完整参考。三设备规模暂时不需要，预留演进位。

---

## 1. 方案对比表

| 方案 | 原理 | 常驻成本 | Token 成本 | 实时性 | 落地难度 | 成熟度 |
|---|---|---|---|---|---|---|
| **A. 事件驱动唤醒器（headless + resume）** | 消息→spawn/续接会话→处理→退出 | 仅唤醒器进程（已有 node-bridge）≈0 | 按消息计（理想） | 秒级 | ★★☆ 低-中 | 高（官方 SDK + 多个开源验证） |
| **B. 官方 Channels / 跨会话消息** | MCP channel 把事件推入**运行中**会话 | 会话需常开 | 常驻会话持续烧 | 毫秒-秒级（推送） | ★★☆ 低 | 官方 research preview / GA 演进中 |
| **C. 文件/黑板通道 + watch** | append-only JSONL + 阻塞 watch | 仅 watcher ≈0 | 按消息计 | 秒级（轮询间隔可调 0.05s+） | ★☆☆ 低 | 高（agent-channels 已生产使用） |
| **D. A2A / MCP-remote 协议层** | 标准协议暴露 agent 为可寻址服务 | 每端一个协议适配进程 | 按消息计 | 秒级（HTTP/SSE） | ★★★ 中-高 | A2A 2025-04 发布、框架适配中 |
| **E. Temporal / gateway daemon 编排** | durable workflow 做执行层，signal 唤醒 | 每机一个 worker 进程 | 按消息计 + 编排开销 | 秒级 | ★★★★ 高 | 中（Temporal 成熟、agent 集成新） |

---

## 2. 方案详细说明

### 方案 A：事件驱动唤醒器（Headless + on-demand activation）—— 核心推荐

**原理**：LLM 会话不做成常驻进程，而是做成「可被消息唤醒、可程序化续接」的惰性资源。常驻的只有零成本的唤醒器（监听消息通道）。消息到达 → 唤醒器判断目标会话当前是否有活跃进程：
- 有 → 通过 channel/注入把消息推进去（方案 B/C）；
- 无 → spawn 一个 headless 会话（或 resume 历史会话）→ agent 读 inbox、处理、把回复写 outbox → 进程退出。
会话的「记忆」靠宿主自己的持久化（Claude Code 的 session 存档 + `--resume`；DSH 的 session 持久化 + `agents.resume`），所以每次唤醒都是「同一个对话的续接」，用户感知就是微信式的「对方随时在」。

**Claude Code headless 模式（官方）**：
```
claude -p "处理 inbox 里的新消息" --output-format stream-json --input-format stream-json --resume <session-id>
```
- `-p/--print` 非交互单次执行；`--output-format stream-json`（NDJSON 事件流，含 system/assistant/user/tool_use 事件）；`--input-format stream-json` 程序化注入输入；`--resume <session-id>` 续接历史会话；`--continue/-c` 续接最近会话；还有 `--max-turns`、`--permission-mode`、`--model`。
- 社区已把该协议封装成可复用 skill：`claude-cli-agent-protocol`（LobeHub/Skills.rest，2026）——集成 Claude CLI headless 模式、处理 stream-json NDJSON。

**Claude Agent SDK（官方程序化 API，比 CLI 更适合做唤醒器）**：
- Python：`claude-agent-sdk`（`pip install claude-agent-sdk`）。`query(prompt, options)` 一次性问答；`run_agent(agent_definition)` 多轮 agent 循环；`AgentDefinition` 支持 `background`、`effort`、`permission_mode`（2026 年 commit 7c6902b 加入）；流式部分消息用 `include_partial_messages=True`（PR #168）。文档：code.claude.com/docs/en/agent-sdk/python（本环境不可达，经搜索快照验证）。
- TypeScript：`@anthropic-ai/claude-agent-sdk`，`query()` / `runAgent()` + `streamEvent()`。

**参考实现（已开源、可抄作业）**：

1. **claude-relay（gvorwaller）** —— 最贴近我们架构的参考。WebSocket relay server（`server.js`，端口 9999，loopback 仅本机）+ 每宿主一个 stdio MCP server（`mcp-server.js`）；跨机器走 SSH local-forward 隧道（自带 launchd LaunchAgent 保活）；会话注册表 `sessions/registry.json`（人类可读 ID，如 CC-1）。**最关键是它的 delegate wake 机制**：交互会话的 label 可以被一个「唤醒委托」接管——`RELAY_DELEGATE_FOR` 标记的 headless 会话被唤醒去读/回邮件，身份显示为 `~wake-*`，凭证带 1 小时租约、同一时刻只允许一个 delegate、任务结束即吊销；邮件在 owner 忙时持久化，**多条通知合流为任务终态后的单次尾随唤醒（coalesced trailing wake）**——这正是「微信式随时回复」的落地方案骨架。

2. **claudetalk（g-cqd）** —— MCP server 做 Claude 实例间聊天，Bun + bun:sqlite + SSE 看板。**它解决了「会话在 turn 间隙怎么自动发现新消息」**：注册 6 个 hooks（`SessionStart`、`UserPromptSubmit`、`PostToolUse`（匹配 `mcp__claudetalk__.*`）、`PostToolBatch`、`SubagentStop`、`Stop`）→ 每个 hook 都跑 `check-inbox.ts`，在回合之间自动提醒 Claude 查看 inbox——**无轮询、无常驻**。跨机器靠自托管 Bun WS relay（约 280 行，`relay/src/index.ts`），消息 Ed25519 签名 + AES-GCM-256 端到端加密，`~/.claudetalk/network.json` 配 `relay_url + shared_secret`，跨机延迟 ~200ms，30 天 catch-up。

3. **agent-channels（cheapsteak）** 的 `watch` 原语 —— `channels watch help --since N`：**阻塞等待新消息，来消息 exit 0，超时 exit 2**。官方文档原话：「launch with the agent's background tool, idle (zero tokens) until the binary exits, react to stdout, re-launch with bumped --since」——这就是唤醒器的标准循环，零 token 空闲。

4. **claude-coordinate（evrimagaci）** —— 纯文件方案（无网络监听），但它的 **fallback 机制值得抄**：目标会话没有 live channel 时，`send` 自动降级为「上下文感知的 transcript resume」——`claude -p --resume` 用该会话的存档续接并拿到真实回复，只是不能在已开 TUI 里实时渲染。附带 90 秒 anti-interleave 防抖（会话最近 90s 活跃则拒绝并发 resume 写）。

**DSH 侧对应**：DSH 已有 `agents.resume`（程序化恢复持久化会话）与 agent_wake（对离线会话投递唤醒消息）——本机内「消息→唤醒会话」已经打通；缺的是把 node-bridge 的跨机 inbox 事件接到本地唤醒器上（见第 4 节）。

**成本核算**：常驻 = 唤醒器进程（node-bridge 已常驻，复用同一进程即可）+ 零 LLM 调用；每消息 token = 1 次完整对话续接；空闲 = 0 token。

---

### 方案 B：官方 Channels / 跨会话消息（会话存活期的实时通道）

**Claude Code Channels**（research preview，2026-03-20，需 v2.1.80+ / Bun / claude.ai 登录）：
- 官方定义：「**A Channel is an MCP server that pushes events into your running Claude Code session**」——Channel 是 MCP server，把外部事件（Telegram/Discord 消息、CI 事件）推入运行中的会话，agent 处理后经同一 channel 回推。
- 启动：`claude --channels plugin:telegram@anthropic`（官方插件）；非官方 channel 需 `--dangerously-load-development-channels` 逃生口（claudetalk、sym-mesh-channel、claude-coordinate 都用它）。
- **硬限制（对我们最关键）**：LOW/CODE 官方认证解读明确指出——「**Session must be open to receive messages: Channels is not always-on**；关掉终端 channel 就熄灯」。所以 Channels 只解决「会话开着时怎么从外面推消息」，不解决「会话没开」。
- 演进：Claude Code 2.1.224（2026-08）上线**跨会话消息**——不同终端会话互发消息、共享发现、跨机器回复（「在一台机器上运行的会话可直接向另一台机器的会话发消息」），Claude 自动当信使措辞；明确**不适用**权限批准/配置修改。限制 macOS/Linux（Windows 未提及，i9 需验证）。

**对我们的意义**：P0 唤醒后，会话存活期内用 channel 实现实时双向（不再轮询）；会话未激活时仍靠 P0 的唤醒器。两者是互补的「冷热双通道」。

---

### 方案 C：文件/黑板通道 + watch（与黑板 KV 同构，零基础设施）

**agent-channels（cheapsteak）**：
- 每个话题一条 **append-only JSONL** 文件（`~/.agent-channels/`，回退 `~/.claude/channels/`）；写入走二进制 + `flock(2)` 独占锁 + 撕裂尾行修复 + `fsync`；读无锁直读。消息跨进程重启存活，可 `cat/grep/tail/jq` 审计。
- CLI：`channels post --from auth-rewrite help "…"`（正文上限 64 KiB）、`channels read/--since N`、`channels tail --follow`（流式）、`channels watch --timeout SECONDS`（阻塞-触发原语）、`channels list/archive`。
- 跨宿主身份：`$CLAUDE_CODE_SESSION_ID` / `$CODEX_THREAD_ID` 缓存 `--from` slug。
- Codex / Claude Code / shell agent 三端同一数据面，插件市场一键装。

**对比我们现状**：黑板 KV + inbox/outbox 就是「通道」，只是从「话题文件」变成「KV 键」。差异点：KV 的写入原子性（CAS）、顺序号（seq）、撕裂检测（JSON 尾行校验）需要对照 JSONL+flock 的设计补强。`watch` 语义可直接映射为 node-bridge 的「订阅 inbox 前缀 + 触发回调」。

---

### 方案 D：协议标准化（A2A / MCP-remote / MMP）

**A2A（Agent2Agent，Google，2025-04 发布）**：
- JSON-RPC 2.0 之上定义 `agent card`（`/.well-known/agent.json` 发现能力）+ `Task`/`TaskUpdate`/`Message` 生命周期 + SSE 流式；2025-11 AG2 原生支持、Agno 出 `A2AClient`（远程 agent 运行协调）、CrewAI/Google ADK 可互连（2025-09 教程）。
- 定位：**agent 与 agent** 的互操作（MCP 是 agent 与工具）。对我们：三设备 agent 若按 A2A 暴露，则任意一端可 `task/send` 给另一端，天然支持「发消息→对方响应」，且协议是开放的（不锁 Anthropic 生态）。

**MCP streamable HTTP（2025-03 规范）**：把端侧能力暴露为远程 MCP server；Cloudflare 有完整参考（`developers.cloudflare.com/agents/guides/remote-mcp-server/`，Python + streamable HTTP + 鉴权）。适合把某台设备的能力（如 i9 上的 Windows 工具）暴露给其它设备调用。

**MMP（Mesh Memory Protocol，sym-bot）**：开源协议（github.com/sym-bot/mesh-memory-protocol，有 arXiv 论文 2604.19540）——身份（authenticated peer identity）+ CAT7 结构化认知消息（focus/issue/intent/motivation/commitment/perspective/mood）+ 接收方准入（SVAF 相关性门控：**先评估再进认知状态，避免每条消息都打断 agent**）。sym-mesh-channel 就是它的实现：`npx -y @sym-bot/mesh-channel@latest start --room your-room`，同机 loopback / 局域网 Bonjour 自动发现 / 跨网可选 relay，消息可在 agent turn 进行中全双工进入。

**取舍**：三设备私有场景不需要全协议栈；只需借鉴其消息信封（from/to/thread/seq/type）与「接收方门控」思想，格式对齐 A2A 的 Message 即可，避免自造协议日后难接生态。

---

### 方案 E：中心化编排 / durable execution（演进位）

**Temporal**：把 agent 执行包装为 durable workflow——`signal` 唤醒（对应「来消息」）、`query` 同步读状态、断点续跑（进程崩溃不丢任务）。官方 demo：`temporal-sa/durable-agentic-harness`（Temporal 作为 Agentic AI 的 Durable OS 层，底下跑 OpenAI Agents SDK）；Rust 侧有 `temporal-agent-rs` crate。适合「跨设备多步编排 + 可靠重试」，单聊场景过重。

**OpenClaw Gateway daemon**（always-on 参考标杆）：`openclaw onboard --install-daemon` 装成 launchd/systemd **用户服务**，Gateway（`ws://127.0.0.1:18789`）常驻，CLI / WebChat / macOS app / iOS/Android node 都连它；触发源包括 Telegram/WhatsApp/Slack/Discord/iMessage 渠道、cron 定时任务（`automation.cron`）、webhook（`POST /webhook`）、Gmail Pub/Sub。HuggingFace 有一篇同名文章《Always-On OpenClaw, On-Demand Inference》——即「传输常驻、推理按需」的范式命名。Claude Code 官方 2026-03 的 Channels 也被 LOW/CODE 称为「Anthropic's answer to OpenClaw」。

**maestro-mcp**（rmstxrx）：multi-host 机器舰队 + AI agent 编排的 MCP server——把多台机器当作可编排舰队，是「三设备注册中心」的直接参考。

---

## 3. 针对我们场景的推荐（node-bridge + 黑板 KV + 三设备）

我们的架构已经站在正确的位置：**node-bridge = 常驻传输层（业界共识的 A 面），缺的是「唤醒器 + 会话存活期实时注入」（B 面）**。

### 推荐分层落地（按优先级）

**L0（P0，先做，1-2 天）——跨机唤醒器**
```
[远端发消息] → node-bridge 收 inbox(目标=mac-mini 某会话)
             → 本地唤醒器：
               1. 查会话注册表（黑板 KV：session_id → pid/状态/宿主）
               2. pid 存活？ → 走 L1 channel 注入
               3. 未存活 → spawn headless：DSH 侧用 agents.resume（本机已有）
                          或 Claude Code 侧 claude -p --resume <session-id>
               4. agent 读 inbox → 处理 → 回复写 outbox → 退出（可选保留 60s 热窗口）
```
- 会话注册表：复用 node-bridge 现有心跳，把「会话在线/离线」作为注册状态写入黑板 KV（对标 claude-relay 的 `registry.json`：PROCESS 存活 + RELAY 在线 双状态）。
- 唤醒去重：对标 claude-relay 的 coalesced trailing wake——owner 忙时消息持久化，任务终态后单次尾随唤醒，禁止并发 delegate。
- 身份：跨设备唯一 session-id 作路由地址（对标 claudetalk 的 pseudonym = f(SHA-256(pubkey))，我们可直接用 DSH session id）。
- 消息持久化：inbox 未读不丢（黑板 KV 已具备），处理后标 seq 防重放。

**L1（P1）——会话存活期实时注入**
- 存活会话间用 channel 机制实时互推（claudetalk 的 hooks 模式：turn 间隙 check-inbox 自动提醒；或 DSH 若支持类 channel 注入则直接用）。
- 目标体验：消息进来 ≤2-3s 内对方会话「感知到」并回复（claudetalk 实测跨机 ~200ms 传输 + 模型耗时）。

**L2（P2）——协议与安全**
- 消息信封对齐 A2A Message（from/to/thread/seq/type/payload），避免自造协议。
- 安全三件套：① channel 本质是「输入注入」——必须过现有审批栈（DSH 已有 approval 体系，claude-relay/coordinate 都强调 keep human approval for consequential actions）；② 端到端加密（claudetalk 的 Ed25519 + AES-GCM-256 是现成模板，relay 只持密文）；③ 唤醒凭证短租约（claude-relay 的 1 小时 lease 模式）。

**L3（P3，可选）**——需要跨设备多步编排时引入 Temporal（durable workflow + signal 唤醒）；单聊/单步任务不需要。

### 直接可抄的参考组合
| 需求 | 抄谁 | 抄什么 |
|---|---|---|
| 跨机唤醒-回复闭环 | claude-relay（gvorwaller） | delegate wake + 尾随合流 + 凭证租约 |
| 会话内自动感知消息 | claudetalk（g-cqd） | 6 hooks check-inbox + 跨机 relay 加密 |
| 零 token 等待原语 | agent-channels（cheapsteak） | `watch` 阻塞-触发循环 |
| 无 live 会话的降级回复 | claude-coordinate（evrimagaci） | `-p --resume` 上下文续接 + anti-interleave |
| 常驻网关形态 | OpenClaw | launchd/systemd 用户服务 + webhook/cron 触发 |
| 端到端安全信封 | claudetalk / MMP | Ed25519 签名 + AES-GCM + 接收方门控 |

### 一句话架构
> **node-bridge（常驻、已就绪）= 微信服务器；唤醒器（新增、≈200 行）= 消息→`agents.resume`/`claude -p --resume` 的触发器；会话 = 按消息活、干完即睡；黑板 KV = 注册表 + inbox/outbox + 未读持久化。**

---

## 4. 参考链接

**官方文档**
- Run Claude Code programmatically（headless）：https://code.claude.com/docs/en/headless
- Agent SDK Python reference：https://code.claude.com/docs/en/agent-sdk/python
- Streaming output（Agent SDK）：https://code.claude.com/docs/en/agent-sdk/streaming-output
- Push events into a running session with channels：https://code.claude.com/docs/en/channels
- Message your other Claude Code sessions：https://code.claude.com/docs/en/cross-session-messaging
- Agent Teams（官方）：https://code.claude.com/docs/en/agent-teams
- A2A 发布博客（Google）：https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/

**开源实现**
- claude-relay（WebSocket + MCP 跨机实时通信）：https://github.com/gvorwaller/claude-relay
- claudetalk（MCP 实例间聊天 + 跨机 relay + hooks）：https://github.com/g-cqd/claudetalk
- sym-mesh-channel（全双工 channel + Bonjour 发现）：https://github.com/sym-bot/sym-mesh-channel
- Mesh Memory Protocol（MMP）：https://github.com/sym-bot/mesh-memory-protocol （论文 https://export.arxiv.org/pdf/2604.19540 ）
- agent-channels（文件通道 + watch）：https://github.com/cheapsteak/agent-channels
- claude-coordinate（本地文件协调 + resume 降级）：https://github.com/evrimagaci/claude-coordinate
- cc-dm（Channels 协议 P2P 私信）：https://github.com/Akram012388/cc-dm
- maestro-mcp（多主机舰队编排）：https://github.com/rmstxrx/maestro-mcp
- durable-agentic-harness（Temporal agent 执行层 demo）：https://github.com/temporal-sa/durable-agentic-harness
- claude-agent-sdk-python（background/effort/permissionMode commit）：https://github.com/anthropics/claude-agent-sdk-python/commit/7c6902bbdcb855c026d5e839c77332265433f82a

**行业分析 / 教程**
- 9to5Mac：Claude Code 会话跨机互聊（2026-08）：https://9to5mac.com/2026/08/07/claude-code-now-lets-sessions-talk-to-each-other-on-macos/
- PChome：v2.1.224 跨会话通信上线：https://article.pchome.net/news/15414.html
- LOW/CODE：What Is Claude Code Channels（官方认证解读，含「非 always-on」限制）：https://www.lowcode.agency/blog/claude-code-channels
- OpenClaw 24/7 always-on（gateway daemon）：https://claw.so/blog/run-openclaw-247/
- claude-cli-agent-protocol skill（headless NDJSON 集成）：https://lobehub.com/skills/neversight-skills_feed-claude-cli-agent-protocol
- Agent Teams 完整指南（v2.1.83 实验特性）：https://github.com/ThamJiaHe/claude-code-handbook/blob/main/docs/agent-teams-guide.md

---

## 5. 噪音排除记录 & 局限

**噪音排除**
- 未采信：nuget/npm 上的 `oly`、`@suzuke/agend`、`agentflyer`、`aidaemon` 等小包（无维护信息、无独立佐证，疑似蹭词 SEO 包）。
- 未采信：`ServerCC`（App Store 第三方壳）、`swarmcode-mcp`、`claude-intercom`（无文档快照可验证）。
- 部分采信：ccb（claude-code-best 的 SSH Remote 分支）——仅采其 `--output-format stream-json` 双向协议与 AuthProxy 隧道思想，非官方实现。
- 时间线标注：多个结果日期在 2026 年中（Channels 2026-03-20、跨会话消息 2026-08-07），与当前调研日一致；A2A 于 2025-04 发布，属近 1 年权威信息。

**局限与待验证**
1. **code.claude.com 官方文档站本环境不可达**，官方细节（headless 精确 flag、Channels 完整 API）经搜索快照 + 官方认证第三方（LOW/CODE）+ 开源实现交叉验证，落地前需在真机复核。
2. **Windows 支持**：Claude Code 跨会话消息标注 macOS/Linux；claude-coordinate 明确 Windows 未测试。i9（Windows）侧的 DSH 宿主唤醒需走 DSH 自身机制（agents.resume 若跨平台则无碍），建议真机验证。
3. **DSH 宿主是否暴露 headless/SDK 接口**未在本报告中验证（DSH 为内部工具，无公开文档）——若 DSH 有 `agents.resume`（本会话工具列表确认存在）则 L0 直接成立；否则需在 DSH 宿主进程外做一层 CLI 包装。
4. **Channels 的 research preview 状态**：`--dangerously-load-development-channels` 随时可能因版本升级变化（claudetalk/coordinate 均提示此风险）。
5. A2A 在 2026 年生态适配进度（AG2/Agno/CrewAI）以各框架 changelog 为准，未逐一实测。

**落库**：raw 源已按流水线沉淀至 `raw/research/<date>-agent-persistent-chat/`（后台任务），wiki 页编译与 ChromaDB 索引由主会话按需执行。
