# LLM 智能体「常驻后台响应 / 按需唤醒」工程实践调研报告

> 调研日期：2026-08（基于公开文档与社区实践）
> 场景：3 台设备各跑独立 DSH/CLD（类 Claude Code 桌面壳）智能体宿主；已有常驻 Rust 传输层 node-bridge（收消息落盘 `~/.dsh/inbox/`，发消息写 `~/.dsh/outbox/`）；目标：**消息到达时自动唤醒本地 LLM 会话处理并回复，不常驻 GUI、不空耗 token**。

---

## 1. 结论摘要（可落地路径）

调研的核心结论：**「常驻 agent 会话」不是主流推荐，「按需 spawn 一次性 agent」才是。** 社区共识（含 Claude 官方 SDK 定位、Cloudflare agents 文档、以及多个 token 成本实测）都指向：**有消息才起 agent，处理完即退，用确定性代码（队列/幂等/重试/DLQ）保证可靠性，把「决策」留给模型、把「可靠性」留给代码。**

四条可落地路径（按推荐度排序）：

| # | 路径 | 一句话 | 适用 |
|---|------|--------|------|
| **P1（首选）** | **node-bridge 直接 spawn 一次性 agent**：inbox 来消息 → `claude -p` 或 Agent SDK `query()` 起一个无会话 agent → 结果写 outbox | 零 GUI 依赖、token 与消息数严格成正比、可无头运行 | 大部分「消息→回复」场景 |
| **P2** | **事件驱动骨架**：inbox 文件监听 → 持久队列 → 幂等 ledger → 退避重试 → 死信队列 | 模型只做决策，确定性代码管可靠性，可无人值守 | 生产化必须项，叠加在 P1/P3 之上 |
| **P3** | **有状态按需**：需要跨消息上下文时用 `--session-id` + `--resume`（或 Agent SDK `ClaudeSDKClient`），**进程不常驻、会话不心跳**，只在消息到达时拉起 | 同一任务流的多轮对话 | 客服式连续对话、长任务续作 |
| **P4** | **桌面唤醒 UX**：OS 通知 + deep link 激活 GUI（参考 hermes-agent 的 Electron 实现），复杂任务才唤醒 DSH 会话 | 需要人工介入/可视化时才唤醒 GUI | 混合模式：简单消息自动回，复杂任务弹通知 |

**混合推荐**：热路径（单轮、低风险消息）走 P1 秒回；需要工具链/Dify/MCP 生态或人工确认的走 P4 唤醒 DSH 会话。两条路共用 P2 的队列骨架。

---

## 2. 核心模式推荐：「消息 → 按需唤醒 agent → 回复」

### 2.1 成熟参照：Telegram bot + LLM（这是已被验证的生产模式）

现代 Telegram AI bot（如 HoneyChat，生产级参考架构）本质就是你要的东西——**常驻的只是一个轻量 dispatcher，LLM 是「按消息拉起、用完即走」的**：

```
Telegram 消息
   │ (webhook POST / long polling)
   ▼
Bot Service (Dispatcher: aiogram/grammY)
   ├─ middleware 链：鉴权 / 限流 / 套餐 / 成本闸门   ← 0-50ms，纯确定性代码
   ├─ 上下文装配：Redis 短期记忆 + 向量库长期记忆      ← 100ms
   ├─ prompt 构造：system + 检索记忆 + 历史 + 新消息   ← 200ms
   ├─ LLM inference（流式/一次性）                    ← 300ms-5s，**唯一花钱的地方**
   └─ 回发 + 异步任务队列（Celery）处理长任务（图/语音）← 3-30s
```

关键洞察（迁移到本地多设备场景）：
1. **常驻的只是「收件调度器」**（Telegram 的 bot 进程 / 我们的 node-bridge），它永远不阻塞等 LLM；
2. **LLM 调用是被消息触发的、短命的**——没有消息就没有 LLM 调用，没有 token 消耗；
3. **可靠性（幂等、重试、限流、死信）全部由确定性代码承担**，模型只做决策。这正是「可以无人值守地长期运行」的原因。

### 2.2 事件驱动 agent 的黄金骨架（社区已验证的通用模式）

来自 [An agent that runs on events, not chat](https://dev.to/dev48v/an-agent-that-runs-on-events-not-chat-webhooks-a-queue-idempotent-execution-and-a-17h6)（带真实运行录屏的参考实现）和 [Cloudflare agents 官方文档](https://github.com/cloudflare/agents/blob/99a1f31/docs/server-driven-messages.md)：

```
事件源（webhook / 文件到达 / 队列消息）
   │  立即 202/ACK，绝不阻塞等模型
   ▼
持久队列（append-only，落盘）
   ▼
Worker（单消费者循环）
   ├─ 幂等 ledger 检查：event id 已处理？→ skip（零模型调用）
   ├─ 分发器：event type → handler（handler 里才调 LLM）
   ├─ 瞬时失败 → 指数退避重试（封顶次数）
   ├─ 业务拒绝 → 标记处理、**不重试**（不是错误）
   └─ 重试耗尽 → 死信队列（带 payload + last_error）
```

Cloudflare agents 给出的语义化原语（可直接映射到我们的设计）：
- `saveMessages(msg)` —— 注入消息 **并触发** LLM 回复（等它完成）；
- `submitMessages(msg, {idempotencyKey})` —— **耐久异步提交**：先落盘、幂等、可查询状态，适合 webhook 处理器（不阻塞调用方）→ 对应我们「inbox 落盘即 ACK」；
- `persistMessages(msg)` —— 只注入上下文、**不触发**模型（对应预热/注入背景信息）；
- `waitUntilStable()` —— 触发前等会话稳定，避免与在途流重叠 → 对应我们的**单会话互斥**。

### 2.3 为什么「按需 spawn」胜出（token 成本实测）

[Standard Compute 的实测报告](https://standardcompute.com/blog/how-session-reuse-cost-35-daily-and-caused-context-drift-after-5-tasks)：**常驻会话的「心跳」本身就烧钱**——30 分钟间隔的 heartbeat 检查，纯 idle 状态一天 $35；高并发场景 40–60% 的成本方差来自会话保活；上下文跨任务继承导致漂移和 token 浪费；有案例多会话常驻一个月烧掉 $700。

三种模式对比（社区共识）：

| 模式 | 空闲成本 | 上下文隔离 | 多任务适用性 |
|------|---------|-----------|-------------|
| 常驻绑定 agent（有 heartbeat） | ❌ 高（idle 也烧） | 差（自动继承漂移） | 差 |
| **按需 spawn（新会话/次）** | ✅ 零 | 好 | **好（主流推荐）** |
| 手动管理 + 定期 reset | 中 | 中（依赖纪律） | 中 |

例外：单一长线工作流（持续维护同一项目）适合常驻保留上下文；多任务场景必须按需。Claude Agent SDK 的 `ResultMessage` 直接返回 `total_cost_usd`，成本可度量。

---

## 3. 技术细节

### 3.1 Claude Agent SDK 编程式调用（Python）—— P1 的主引擎

**注意命名**：原「Claude Code SDK」已更名 **Claude Agent SDK**，包名 `claude_code_sdk` → `claude_agent_sdk`，网上旧代码的 import 已过期。

- 安装：`pip install claude-agent-sdk`（Python ≥3.10，**自动捆绑 Claude Code CLI，无需单独安装**）——对应我们的场景：3 台设备装了 CLI 就等于装了 SDK。
- **一次性调用**（正是「按需唤醒」的核心 API）：

```python
import anyio
from claude_agent_sdk import query

async def main():
    async for message in query(
        prompt="收到新消息，请处理：<inbox 消息内容>",
        options={"permission_mode": "bypassPermissions",  # 仅限沙箱/无头环境
                 "allowed_tools": ["Read", "Write", "Bash"],  # 按需收窄
                 "cwd": "/path/to/workspace"},
    ):
        # AssistantMessage → 流式输出；ResultMessage → stop_reason + total_cost_usd
        print(message)

anyio.run(main)
```

- **多轮/有状态**（P3）：`ClaudeSDKClient` 双向会话，支持 `query()` + `receive_response()` 流式接收、`interrupt()` 中断、async iterable 批量喂消息；`ClaudeAgentOptions` 可配 `allowed_tools` / `system_prompt` / `env`（如 `ANTHROPIC_MODEL`）。
- **本质**：SDK 就是 Claude Code 引擎本身（同一套工具 Read/Write/Edit/Bash/Glob/Grep/WebSearch/WebFetch、同一套权限系统、hooks、子代理机制），只是「驱动者从人变成你的代码」。**无头无人值守正是官方列出的适用场景**（CI / cron / webhook 响应）。路由同 CLI 一样支持 Anthropic API / Bedrock / Vertex。
- 参考：[Agent SDK 官方文档](https://code.claude.com/docs/en/agent-sdk/python)、[流式模式示例](https://mintlify.wiki/anthropics/claude-agent-sdk-python/examples/streaming-mode)、[完整指南（含 SDK vs Messages API 对比）](https://hidekazu-konishi.com/entry/claude_agent_sdk_complete_guide.html)。

### 3.2 CLI 非交互模式（`claude -p`）—— 零依赖的备选/兜底

即使不写 SDK 代码，脚本也能直接驱动：

```bash
# 一次性执行（stdin 或参数传 prompt），stdout 出结果后退出
echo "$(cat ~/.dsh/inbox/msg-001.json)" | claude -p "处理这条消息" \
  --output-format json \
  --permission-mode bypassPermissions \
  --no-session-persistence          # 不落盘会话，避免会话文件堆积

# json 输出自带 usage 计量
# {"type":"result","subtype":"success","result":"...","usage":{"inputTokens":1200,"outputTokens":18,"costUSD":0.002}}
```

关键 flag 速查（详见 [CLI flags 文档](https://mintlify.wiki/VineeTagarwaL-code/claude-code/reference/commands/cli-flags)）：

| flag | 用途 |
|------|------|
| `-p, --print` | 非交互单次执行，处理完退出，无 REPL；信任对话框跳过 |
| `--output-format text\|json\|stream-json` | 文本 / 单 JSON（含 costUSD）/ 行分隔 JSON 流（实时事件） |
| `--input-format stream-json` | stdin 流式输入（与 stream-json 输出配对，可做双向流） |
| `--permission-mode bypassPermissions` | 全部免确认（**仅限沙箱/CI/无网络隔离环境**）；`acceptEdits` 半自动 |
| `--allowedTools` `--max-turns` | 收窄工具集、限制轮数（防失控） |
| `--model` `--fallback-model` `--effort` | 模型/降级/推理强度 |
| `--no-session-persistence` | 单次任务不写会话（省磁盘、防上下文污染） |
| `--session-id <uuid>` `--resume <id>` `--fork-session` | P3 有状态按需：固定会话 id / 续接 / 分支 |
| 退出码 0/1/2 | 脚本据此判断成功/失败/用法错误 |

另有**内建定时任务**：`.claude/scheduled_tasks.json`（cron + prompt），以及 `watchScheduledTasks()` 供外部守护进程接管调度——如果将来要加「周期性自检」可直接用。环境变量：`ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` / `CLAUDE_CONFIG_DIR`（可把每个设备/会话的配置隔离）、`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`（防止 agent 自己拉后台任务）。

### 3.3 桌面 app 通知唤醒机制（P4）

**最贴合的现成案例：hermes-agent（NousResearch 的桌面 agent 宿主，架构与 DSH/CLD 同型）** 在 Electron 壳里实现了「OS 通知 + deeplink 激活」：

1. 后台服务收消息 → 经 IPC `hermes:notify` → 发 **OS 原生通知**（`new Notification({title, body, actions:[...]})`）；
2. 用户点通知正文/动作按钮 → `notification.on('action')` → `focusWindow(mainWindow)` + `hermes:notification-activate` 事件把 `{activate, notifyId, sessionId}` 送给渲染层；
3. 渲染层据此**激活目标会话**（session-less 路径用 `activate` 载荷，无需已有 sessionId）；deep link 形如 `hermes://index-network/...`。

机制归纳（跨平台）：

| 平台 | 后台触发 GUI 的标准机制 |
|------|------------------------|
| macOS | ① URL scheme / deep link：`open "cld://session/<id>?msg=..."`（应用注册 CFBundleURLTypes）；② AppleScript：`osascript -e 'tell application "CLD" to activate'`；③ launchd LaunchAgent 常驻后台守护（进程常驻但**不做 LLM 工作**，只监听）；④ Notification Center 通知点击自带激活 |
| Windows | 注册 URL protocol（注册表 `HKEY_CLASSES_ROOT\cld`）→ 任意进程 `start cld://...`；toast notification 带 activation；后台服务用 Windows Service / Task Scheduler |
| Linux | freedesktop URL handler（`xdg-open`）、Desktop Notifications spec |

**与我们的关系**：node-bridge 本就是常驻守护（等价于 launchd agent / bot dispatcher），它不需要唤醒 GUI 就能走 P1 直接回复；只有当消息需要人工介入或必须用 DSH 会话生态时，才由 node-bridge 发 OS 通知 / 调 deep link 唤醒 CLD。

---

## 4. 我们场景的实现草图（node-bridge 消息驱动）

```
┌─ 设备 A（Rust node-bridge 常驻守护）─────────────────────────────┐
│                                                                  │
│  ~/.dsh/inbox/  ──FSEvents/ReadDirectoryChangesW/inotify──► 监听 │
│   (新消息落盘)        (Rust notify crate，内核事件，零轮询)          │
│                                                                  │
│  消息到达 ──► 路由：目标设备/会话/任务类型  ──► 幂等 ledger 检查      │
│                                            (msg_id 去重，已处理跳过) │
│                                              │                    │
│                              ┌───────────────┴──────────────┐    │
│                              ▼                              ▼    │
│                   P1 热路径（自动回复）               P4 人工路径     │
│              spawn 一次性 agent                     OS 通知 + deep  │
│              ┌─────────────────────┐               link 唤醒 CLD   │
│              │ claude -p …          │               (cld://session/…)│
│              │ 或 Agent SDK query() │                  │           │
│              │ (bypassPermissions,  │              DSH 会话处理      │
│              │  收窄 allowedTools,  │                  │           │
│              │  no-session-persist)│              │               │
│              └─────────┬───────────┘              │               │
│                        ▼                          ▼               │
│              ~/.dsh/outbox/  ◄────── 结果/回复（跨设备同步层回发）  │
│                                                                  │
│  可靠性（确定性代码，不占模型）：                                  │
│   • 持久队列（append-only）+ 指数退避重试（封顶）                    │
│   • 死信队列（payload + last_error）                               │
│   • 并发池 + 每会话互斥（等价 Cloudflare waitUntilStable）          │
│   • 限流/冷却（防止消息风暴打爆 API 额度）                           │
│   • 每次运行记录 total_cost_usd（SDK ResultMessage / CLI json）    │
└──────────────────────────────────────────────────────────────────┘
```

**落地要点**：
1. **监听**：Rust `notify` crate（macOS FSEvents / Windows ReadDirectoryChangesW / Linux inotify），事件驱动而非轮询——node-bridge 已有传输层，只需加一个目录 watcher；
2. **路由与去重**：inbox 消息带 `msg_id`（幂等键），ledger（SQLite 或简单 kv）记已处理 id；
3. **P1 执行器**：优先 Agent SDK `query()`（结构化、拿得到 `total_cost_usd`、可设 `allowed_tools`）；备选 `claude -p --output-format json`（零额外依赖，脚本即用）；`bypassPermissions` 必须配合沙箱/白名单工具，`--no-session-persistence` 防止会话文件堆积；
4. **P3 有状态**：同一 thread 的消息用固定 `--session-id` + `--resume`（或 `ClaudeSDKClient` 长进程**只持有客户端、不跑 heartbeat**）——进程可常驻但**模型调用仍按消息触发**；
5. **P4 人工介入**：node-bridge 发 OS 通知（参考 hermes-agent 的 `hermes:notify` → click → `hermes:notification-activate` 模式），CLD 注册 `cld://` URL scheme，点击即聚焦对应会话并注入消息；
6. **回复**：结果写 `~/.dsh/outbox/`，由既有跨设备同步层回发，与 node-bridge 现有收发语义完全一致。

---

## 5. Token 成本估算（常驻 vs 按需）

| 项 | 常驻 GUI 会话 | 按需 spawn（P1） |
|----|--------------|-----------------|
| 空闲成本 | **高**：会话心跳/保活持续消耗（实测 30min 心跳纯 idle ≈ **$35/天**；社区报告 40–60% 成本方差来自保活） | **零**：无消息 = 无 LLM 调用 = 零 token |
| 单条消息成本 | 同（但**上下文随会话累积**，越到后面每条越贵；跨任务漂移浪费） | 只算本条消息的 prompt+输出（`usage.costUSD` 可精确记账） |
| 多设备×多会话 | 成本随「会话数×存活时间」指数膨胀（有案例 $700/月） | 成本随「消息数」线性增长 |
| 上下文利用率 | 长期会话上下文被无关任务稀释 | 每次 prompt 只含需要的内容（可手动注入历史） |
| 磁盘/状态 | 会话文件持续增长 | `--no-session-persistence` 无残留 |

**估算示例**（假设 sonnet 级模型、单条消息含工具调用约 5k in / 1k out ≈ $0.05–0.15）：
- **按需**：日 100 条消息 ≈ $5–15/天；零消息 = $0；
- **常驻**：3 设备 × 3 会话 × 常驻心跳 ≈ 每天稳定烧掉数美元～$35（即使没人发消息）；
- **结论**：按需模式在「多设备、低活跃、长空闲」场景下成本低 1–2 个数量级，且更可预测。

---

## 6. 参考链接

**Claude Agent SDK（编程式调用）**
- [Agent SDK reference - Python（官方）](https://code.claude.com/docs/en/agent-sdk/python)
- [Stream responses in real-time（官方）](https://code.claude.com/docs/en/agent-sdk/streaming-output)
- [Streaming vs single mode（官方）](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode)
- [Claude Agent SDK Complete Guide（SDK vs Messages API 对比）](https://hidekazu-konishi.com/entry/claude_agent_sdk_complete_guide.html)
- [SDK 流式模式示例（官方仓库）](https://github.com/anthropics/claude-agent-sdk-python/blob/3010aaf/examples/streaming_mode_ipython.py)
- [Claude Agent SDK for Python（镜像文档）](https://mintlify.wiki/anthropics/claude-agent-sdk-python/introduction)

**CLI 非交互模式**
- [CLI flags - Claude Code](https://mintlify.wiki/VineeTagarwaL-code/claude-code/reference/commands/cli-flags)
- [Automation and Scripting - Claude Code（-p / output-format / cron / CI 集成）](https://mintlify.wiki/harshul786/claude-code-source/advanced/automation)
- [Claude Code headless 文档](https://code.claude.com/docs/en/headless.md)

**消息驱动 agent 唤醒框架**
- [An agent that runs on events, not chat（webhook+队列+幂等+DLQ 实战）](https://dev.to/dev48v/an-agent-that-runs-on-events-not-chat-webhooks-a-queue-idempotent-execution-and-a-17h6)
- [Cloudflare agents - Server-driven messages（saveMessages/submitMessages/waitUntilStable）](https://github.com/cloudflare/agents/blob/99a1f31/docs/server-driven-messages.md)
- [AgentBus - open-source event bus for AI agents（webhooks in → agents out）](https://github.com/Kanevry/agentbus)
- [hermes-agent Issue #491: Webhook-Triggered Agent Sessions](https://github.com/NousResearch/hermes-agent/issues/491)

**常驻 vs 按需（token 成本）**
- [How Session Reuse Cost $35 Daily and Caused Context Drift After 5 Tasks](https://standardcompute.com/blog/how-session-reuse-cost-35-daily-and-caused-context-drift-after-5-tasks)
- [Token economics for session-bound agents（会话绑定 agent 的成本模型）](https://thecolony.cc/post/1059818b-b470-414e-a762-0ae82bc521ff)

**桌面通知唤醒**
- [hermes-agent: rich plugin OS notifications with deeplink activation（Electron 实现，最贴合的参考）](https://github.com/NousResearch/hermes-agent/commit/73ddf6665c5ec85965f169847370b585d6f83865)
- [URL Schemes Implementation（macOS/Windows URL scheme 注册）](https://littlegreenviper.com/url-schemes-implementation-step-one/)

**Telegram bot + LLM（成熟模式）**
- [How Telegram AI Bots Work — Architecture Behind the Chat（生产级架构详解）](https://honeychat.bot/en/blog/how-telegram-ai-bots-work-architecture/)
- [LLM-AIOGRAM-BOT（aiogram + LLM 参考实现）](https://github.com/shwballl/LLM-AIOGRAM-BOT)

**目录监听（inbox 事件源）**
- [fswatch - macOS 文件系统监控（内核事件驱动，零轮询）](https://einverne.github.io/post/2026/06/fswatch-file-system-monitor.html)
- [Monitoring directory changes in macOS（serverfault 讨论）](https://serverfault.com/feeds/question/1034991)
