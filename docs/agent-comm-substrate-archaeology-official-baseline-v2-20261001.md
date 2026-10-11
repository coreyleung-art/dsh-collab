# 智能体通信底座 · 考古全图 + 官方基准重审（v2）

> **日期** 2026-10-01 ｜ **节点** mac-mini ｜ **会话** session-fa1f9150（中枢）
> **v2 相对 v1 的变化**：① 考古往前推到 **DSH 安装日 2026-08-15**（v1 的锚点 08-17 晚了两天，且漏掉真正的原型期）
> ② 新增**第三部分：DSH 官方文档深度阅读与架构重审**（v1 完全没有官方基准，只在自研体系内部打转）
> ③ 结论从「若干缺陷」收敛为「**一个根因 + 一套应立不变量 + 一个已存在的官方正解**」
> **v1 仍有效**：`docs/agent-comm-substrate-mechanisms-and-archaeology-20261001.md`（机制细节、三回路证据链、闸门空转实证）；
> 本文不重复其证据，只做**压缩引用**与**结论升级**。

---

## 0. 阅读顺序

1. 只想知道结论 → **§5**
2. 想知道我们做过什么、哪一步断了 → **§2 时间线** + **§3 真相三则**
3. 想知道官方怎么规定的、我们哪里重复造轮子 → **§4 官方基准**
4. 要决定下一步动手做什么 → **§6**

证据分级沿用 v1：**★★★ 代码行级/对照实验坐实** ｜ **★★ 有观测无对照** ｜ **★ 推断** ｜ **⛔ 已证伪**。

---

## 1. 一句话结论

**我们在 DSH 安装的 2026-08-15 次日（08-16）就造出了总线原型，在第三天（08-17）就诊断出了今天仍在处理的同一个根因；45 天后 queued 从 69 涨到 2059（30×）。**

但真正的问题不是"没想到"——考古查到的证据（§3.4）比这严重：

> **关键机制我们解过、生效过，后来又被解开了。**
> · **08-23** 黑板已生效纪律：「**迭代报告走黑板归档即止；纯确认不再 agent_send**」+ 通道分级（STATUS/ACK→黑板；TASK→p2p；COLLAB→线程；EVENT→事件总线；BATCH→邮箱）—— **而今天的迭代报告协议正是走消息通道**，直接制造了 33 条自回路。
> · **08-22** `subscriptions.json` 订阅表已建成（含中枢自己的 topic 列表）；S6 评估（08-20）称"唯一缺口是无订阅唤醒"，**两天后缺口就被补上了**——但 **central-inbox 至今硬编码单目标**，订阅层从未接进注入路径。
> · **08-17** 初代契约里就有 `ttl_sec`（TTL）的**任务队列**，实盘目录 `~/.dsh/bus-queue/` 真在跑；**TTL 后来在 agent-bus 上丢失**，而"queued 永久滞留"正是缺 TTL 的直接后果。

而官方文档里对这个问题的正解——一个带 `senderId`/`messageId`/持久 mailbox/`queued-minus-delivered` ack 的**类型化消息模型**（`docs/subsystems/agent-team.zh.md`，Agent Note 日期 **2026-08-05**）——**早在我们动手之前就已写好**，却**从未被对照过一次**（08-27 的官方调研只做了"我们引用了哪些官方 API"，没做"官方已经提供了什么、我们该不该改用"）。

**⇒ 缺陷性质**：不是能力不足，是 **① 解过的方案被解开（回归）** + **② 自研体系内部反复重造、只修站点不修不变量** + **③ 官方基准从未被真正对照**。
**⇒ 修复方向**：**别再造了**——把官方已规范化的不变量（§5.2 I1–I7）立成契约并断言，同时把三条"解过的方案"恢复回来（§6 D2）。

---

## 2. 真实时间线（从安装日往前推，不再是"我以为的起点"）

| 日期 | 事件 | 关键内容 | 落地状态 |
|---|---|---|---|
| **2026-04-23** | **AgentHub**（比 DSH 早 4 个月） | `~/Downloads/AgentHub_2026-04-23_开发任务清单_v1.0.md`、`AgentHub_2026-04-23_设备注册测试_v1.0.md`、`agenthub代码导出04231128版本.gz`、`agenthub多智能体协作可视化平台.gz` —— **多智能体协作平台 + 设备注册** | 独立项目，未有证据表明被继承 |
| 2026-04-26 | `~/.claude/automation/` | `auto-multi-agent.py`、`langgraph-rag.py`、`autoresearch-karpathy/`（Claude Code 时期） | 已归档 |
| **2026-08-15** | **DSH 安装日** | 最早会话文件 `…/session-908749c1-…/session.jsonl.zstd` **16:30**；`~/.dsh/.anonymous-user-id`、`market/tokens.json`、`settings.yaml.bak` 均为当日 | — |
| **2026-08-16 15:17:33** | **总线首条消息**（★★★ agent-bus.json 实测） | 发件人已是 `session-fa1f9150`；**`~/.dsh-agent-bus.json` 是搬家前快照：574 条消息、仅 08-16 15:17→16:23 一小时** | ✅ 原型在跑 |
| **2026-08-17** | **原型日（安装第 3 天）** | `bus-plugin-contract.md`（**`dsh-plugin-bus-bridge`，HTTP 8791 + token，工具 `bus.send`/`bus.outbox`，任务模型 `target/action/payload/`**`ttl_sec`**`/wait` —— **TTL 初代就有**）· **`bus-queue-mechanism-analysis.md` v0.1** · `agent-bus-roster.md` / `agent-bus-permissions.md` / `agent-bus-restart-state.md` · **`~/external-link-mcp/bus-bridge.js`（11.5KB）+ `bus-client.js`** · `device-orchestrator-analysis.md` · 8 份 `role-appointments/` · 15 份 `qa/acceptance-20260817-*.md`（**当日即建验收体系**） | ✅ 工具链、角色、验收同日齐备 |
| 2026-08-18 | `architecture-v2-plan.md`（155 行） | **架构 v2 计划** | 未落地（见 §3） |
| 2026-08-21 | `exlink-blackboard-architecture.md` | 外链 ↔ 黑板架构 | 部分 |
| 2026-08-23 | `blackboard-dispatch-protocol.md` + `bb-*.py`（12 个） | 黑板派发协议 + 工具链（bb-gate/handshake/dispatch/reuse-check…）；**黑板 v0.5/v0.6 server** | ✅ 在跑 |
| **2026-08-27** | 插件 git 化 + **官方文档调研** | 两个插件仓库首次提交；**`docs/dsh-official-docs-and-community-survey-20260827.md`（118 行）+ `docs/agent-bus-official-doc-references.md`（86 行）**；`docs/hubbridge-{protocol,server-architecture,strategic-assessment}-20260827.md`；`docs/cross-device-bridge-postmortem-20260827.md`（193 行） | **调研做了，未转成"该改用什么"** ⚠️ |
| **2026-08-28** | central-inbox `85b8990 v0.1.1 自注入防护 + 探针噪音过滤` | 判据 **`value.from === NODE_ID`**；同名修复报告 `docs/bidirectional-injection-fix-report-20260828.md` | **⚠️ 修过没修住**（v1 §3.5 回路 2 今日实证仍活） |
| 2026-08-29 | `docs/plugin-selfcheck-spec-v1.md`（72 行）+ `scripts/send-repair-report.py` | **自查门规格 + 修复报告投递脚本（`from:"mbp-ops"` 硬编码源头）** | ✅ 规格在；**实现是空转的**（v1 §3.6） |
| 2026-08-31 | 队列治理三件套 | `docs/queue-governance-design.md`（267 行）、`queue-tool-design-review-v2.md`（102 行）、**`queue-tool-storm-incident-postmortem-20260831.md`**、`scripts/agent-send-gate.py` | **治理工具制造了同题事故** ⇒ 立 R022 |
| 2026-09-05 | M1–M6 根因模式考古 | 六类历史故障模式 | ✅ 已用于本次 |
| **2026-09-28** | `A0b-存量调研盘点.md` | 文档标题即「**这个题目我们已经做过三次**」 | 认知已到位，**动作未跟上** |
| **2026-10-01** | v1 机制文档 + 本文 | 三回路 / from 完整性 / 载体 / 闸门空转 + **官方基准** | 见 §6 |

### 时间线的读法

**不是"很多尝试都失败了"，而是"诊断一直是对的，执行停在最后一公里"。** 三个定量锚点：

| 锚点 | 08-17（第 3 天） | 10-01（今天） | 倍数 |
|---|---|---|---|
| `queued` | **69** | **2059** | **30×** |
| 线程 | 213 | 4050 | 19× |
| 协调者会话上下文 | **18.6 MB / ~5000 条** | 1.1 GB 全会话 | — |

而 08-17 那份 `bus-queue-mechanism-analysis.md` 的 §3 根因四条——**上下文只增不减 / inbox 拼接串行 / 重启唤醒风暴 / token 放大**——**今天一字未改地仍然成立**。

---

## 3. 真相三则（考古带来的三个判断）

### 3.1 我们造的不是"总线"，是**两套并存且语义不同的东西**

`bus-plugin-contract.md`（08-17）显示初代是 **`bus-bridge`：HTTP 8791 + token 鉴权 + `target/action/payload/ttl_sec/wait` 的任务队列**，工具是 `bus.send` / `bus.outbox`。
而 `agent-bus.json` 是**另一条线**：`threads[].messages[]` 的**点对点消息总线**，08-16 就在跑。

**⇒ 我们从一开始就有"任务队列"（带 TTL、可 wait、有 outbox）和"消息总线"（带 thread、无 TTL）两条血统。**
今天的困境恰好是**两者的坏交集**：消息总线**没有 TTL/outbox/ack**，却被当任务队列用（`status:'queued'` 当"待办"）。

**TTL 在初代就存在，后来在 agent-bus 上丢失了。** 这是"丢掉已有正确设计"的实证，比"从未想到"更值得记录。

### 3.2 官方文档我们**读过**，但只读了"我们用了什么"，没读"官方提供什么"

08-27 两份文档的定位很明确：`agent-bus-official-doc-references.md` 的副标题是「列出 agent-bus 开发中**实际引用**的官方文档方面」——**这是一份"事后追认"清单，不是"事前对照"审计**。

它的结论是"我们的用法与官方一致"（defineTool ✓、约定式插件 ✓、followup ✓）。**但没有任何一行问："官方是否已经提供了这个能力，我们为什么要自己写？"**

⇒ §4 要补的就是这一问。

### 3.3 「治理工具制造同题事故」已发生一次，今天我又复现了一次

`queue-tool-storm-incident-postmortem-20260831.md` 立的 **R022「治理工具不得制造同类问题」**，在 v1 §附录 B 里被我今天复现：**我的 A6 探针因旧码仍在线而被真的投递，把 `from===to` 从 33 增到 34**——验证动作自己往被测缺陷里加了一条实例（★★★）。

### 3.4 ★★★ 最重的一条考古结论：**我们解过，然后又把它解开了**

扫尾阶段查到三处直接证据，说明关键机制**曾经存在过并生效过**，后来在演进中被绕过或遗忘：

| 证据 | 时间 | 内容 | 与今天的关系 |
|---|---|---|---|
| **黑板 `data/ack/92623479`** | **2026-08-23** | 已生效的纪律记录（role=`external-link-agent`）：<br>`channel_discipline`：**STATUS/ACK→黑板；TASK→p2p；COLLAB→线程；EVENT→事件总线；BATCH→邮箱**<br>`adaptation`：**「迭代报告走黑板 `data/iterations/` 归档即止；纯确认不再 agent_send」** | **今天的迭代报告协议正是走消息通道** ⇒ 33 条自回路（v1 §3.5 回路 1）。**08-23 的规则就是那个修复，后来被推翻/遗忘** |
| **`~/dsh-collab/subscriptions.json`** | **2026-08-22**（84 行） | **订阅表真实存在**，按 agent 列 topic：含 `session-fa1f9150 → ["制度","规则","J4","重启","广播","审批"]`；配套 `blackboard-subscribe.py`(08-20) / `bb-sub-daemon.py`(08-27) / `bb-sub-gen.py`(08-30) | S6 架构评估（08-20）称「**当前唯一缺口就是「无订阅唤醒」**」——**两天后订阅表就建出来了**，但 **central-inbox 至今硬编码单目标**（v1 §3.5 回路 2），**订阅层从未接进注入路径** |
| **`~/.dsh/bus-queue/{tasks,outbox}`** + `~/.dsh/queue-drain-backups/agent-bus-1788103786.json`（**15.1 MB**，08-30） | 08-17 起 | **初代任务队列的实盘目录**（36 文件，最后活动 09-02/09-06）+ 队列工具事故期的 bus 快照 | 证明 **08-17 契约里的 `target/action/payload/`**`ttl_sec`**`/wait` 任务队列真实运行过**；TTL 在初代就有（§3.1），后来在 agent-bus 上丢失 |

**⇒ 修正 §1 的表述**：不只是"诊断对、执行停"，而是**"解过、生效过、后来被解开"**。
这类缺陷比"从未想到"更危险，因为**任何只读当前状态的审计都看不到它**——只有考古能看见。

### 3.5 闸门层其实非常厚，问题不在"没建闸门"

`~/dsh-collab/scripts/` 原型期至今的闸门工具（仅按名字即可见规模）：
`bb-gate.py`(08-23) · `bb-handshake.py`(08-23) · `bb-dispatch.py`(10 KB, 08-23) · `bb-dispatch-learn.py` · `bb-reuse-check.py` · `task-card-validator.py`(08-23) · `agent-send-gate.py`(08-31) · `bb-schema-gate.py`(09-06) · `gate-repairer.py`(**22 KB**, 09-07) · `gate-auditor.py`(**17 KB**, 09-08) · `group-gate.py`(09-08) · `deliver-gate.py`(12 KB, 09-11) · `gate-conformance.py`(09-14) · `subagent-govern.py`(**26 KB**, 09-06) · `subagent-audit.py`(09-11) · `bb-gallery-gate.sh` · `gate-j23/j24-lean4.py` …

**⇒ R006 十项标准不是凭空来的，是从这一层长出来的。** 所以 v1 §3.6 发现的"三处空转"**不是"缺闸门"，而是"闸门多到自己都测不过来"**——这本身就是架构信号：**闸门层已经大到无法被自身覆盖**（没有任何闸门在检查闸门）。
（官方对此的答案是 `dsh-invariants`：把不变式**下放到各包自注册**，并规定只允许断言权威事件流/可变数据 —— §4.4。）

---

## 4. 官方基准：深度阅读与架构重审

### 4.1 官方文档在哪（v1 时我误判"没有文档"）

| 源 | 位置 | 规模 |
|---|---|---|
| **在线官方文档** | `github.com/deepseek-ai/deepseek-harness` → `docs/` | **75 项**（含 `*.zh.md` 中文版），本次已取 11 篇 + 10 个子系统 |
| **包内 README** | `runtime/node_modules/@deepseek-ai/<pkg>/README.zh.md` | **196 / 202 个包有 README** |
| 源码 JSDoc + `.d.ts` | 同上 `lib/` | 08-27 已确认 |
| 官方 postmortem | `docs/postmortem/` | 编号制（`0001-…` 起） |
| ⚠️ `~/tech-research` | 家目录 | **空的（0 文件）** ⇒ `guard_doc_check` 这条 P0 闸门**无数据源** |

### 4.2 ★★★ 最大发现：官方自带 `Agent Teams`，覆盖的正是我们手搓的全部

`docs/subsystems/agent-team.zh.md`（231 行）+ Agent Note **`2026-08-05-agent-teams.zh.md`**（**比我们装 DSH 早 10 天**），覆盖 **「身份、mailbox、task 与共享 checkout 决策」**。

**逐条对照（官方 vs 我们的缺陷）：**

| 官方规定（原文） | 我们 | 判 |
|---|---|---|
| **持久 mailbox**：「**只有 target 的 pending inbox 条目或已记录用户消息完成持久化，才会写入独立 acknowledgement event**，**queued-minus-delivered 因而构成恢复 mailbox**」 | `status = ok ? 'delivered' : 'queued'`，而官方明说 **`followup()` 没有逐消息完成状态** ⇒ 我们的 `delivered` 是伪造的 | ❌ **我们违反官方防御模式「异步状态不是同步状态」** |
| **类型化 source**：`TeamMessageSource {kind:'team-message', teamId, messageId, senderId, senderName}`；「**跨 inbox 与历史折叠该 source 构成 target 侧去重键**」 | 去重键 = `from｜canonicalTo｜指纹`，而 `from` 是**自由文本且可被硬编码覆盖**（`guard:434` 写死 `mbp-ops`） | ❌ **根因在此** |
| **身份与标签分离**：「teammate 的 **Session id 始终是持久身份**，而 `name` 是**不可变的模型/UI 标签**」 | 身份与显示名混在同一 `from` 字段（`normalizeTo` 要花力气从 `"明鉴 (a190c54c)"` 里猜哪个是 id） | ❌ |
| **消息 ID**：`TeamMessageId` **全局随机**；`TeamTaskId` 单调 `task-<n>` | 我们靠 `from|to|指纹`+10 分钟窗口重算"同一条"，必然漏判 | ❌ |
| **投递模式**：每条消息都走 **Steer**（running 在步骤边界收，inactive 冷恢复）；「**调用方不能选择其他模式**」 | 我们有 `followup`（唤醒）与**官方存在的 `inject`（不唤醒）**，而 central-inbox 一律用 `followup` ⇒ **每张黑板卡强烧一个轮次** | ❌ |
| **任务模型**：`revision` 是 **compare-and-set**；`blockedBy` 维持**无环 DAG**；**`deleted` 是保留 tombstone**；`writeScopes` **是提示性路径前缀，不是锁** | 黑板 KV（12,891 键 **96% 空结果**）+ 自建红绿灯 + 无 CAS/无 DAG/无 tombstone | ❌ |
| **回放**：「按 Root Session **回放**出 roster/任务板/queued-minus-delivered mailbox；**Session event 的 `seq`/`time` 负责顺序与时间**」 | 20.3 MB 单 JSON 整份 persist + 79 MB KV（DELETE 仅 116 次 ⇒ **无 GC**） | ❌ |
| **投影**：`SessionProjectionMap.agentTeam` 把 roster/任务板发布给浏览器 | 自建 dashboard.html + 自定义 HTTP 端点 | ⚠️ 重复造轮子 |

**⚠️ 但必须同时记录两点，否则会误导决策**：
1. **Agent Teams 未随本 runtime 发布**（`ls node_modules/@deepseek-ai/ | grep -i team` → **无**；源码在 `packages/experimental/`，官方标注**实验性**）⇒ **只能借鉴设计，不能直接采用**（★★★）。
2. 它是 experimental，**稳定性不承诺**；因此正确动作是**对齐其不变量**，而非把我们的系统迁到它上面。

### 4.3 官方机制清单：我们自研的六个子系统，各自的"官方对应物"

| 我们自研 | 官方对应 | 官方关键规定 | 建议 |
|---|---|---|---|
| **agent-bus 消息队列**（私有 `status`/`queued`） | **agent inbox**：`followup`/`steer`/`inject` + `next-turn` FIFO + `next-step` inbox；`agent/inbox/{inserted,spliced,claimed,discarded}`；**splice 原子领取** | 私建队列与官方 inbox **语义冲突**（我们的 `queued` = 解析不到人，官方 inbox 一定会被认领） | **改用官方 inbox + 三预设**；`inject`（不唤醒）给通知类 |
| **去重（10 分钟窗口）** | **`TeamMessageId`（全局随机）+ 类型化 source 折叠**；`dsh-agent-instructions` 用 **路径+SHA-1 digest** | 「路径与 SHA-1 内容 digest 都未变时，不会重复注入」 | **换成 ID/digest 身份判定**，弃窗口 |
| **载体**（20.3 MB 单 JSON 整份写） | **`dsh-atomic-write`**：`writeFileAtomic`（`wx` 独占临时文件 + 新 inode 走 rename，读方只见旧或完整新）+ `withFileLock`（跨进程串行、指数退避、超时失败） | 「读取方只会观察到旧内容或完整的新内容」 | **直接改用**（⇒ 路线图第 5 步"换 SQLite"**很可能不必做**） |
| **会话持久化** | `dsh-session-persistence-jsonl` + `SessionPersistence` seam + `session/flush` 显式屏障 + **崩溃恢复保留被中断轮次** | `session/event` → 延后写；flush 是观测屏障 | 对齐（我们的 persist 无屏障语义） |
| **后台任务 / DLQ** | **`ctx.jobs`（`JobRegistry`）** + `dsh-jobs-local` + `dsh-tool-jobs`；有 owner 隔离、`kill`/`wait`/`onJobDone`/`onJobsChanged`、`outputLimitBytes` | 「注册绑定调用方 fiber」「owner 释放会取消仍在运行的工作并等待守约生产方」 | **DLQ/重投应建在 `ctx.jobs` 上**，而非自建队列 |
| **通知/上下文注入** | **`dsh-agent-instructions`**：「若之前排队的 workspace 上下文仍在等待，插件会**删除并替换该确切 inbox 条目，不会不断累积副本**」「**没有文件 watcher**」「字面 `</system-reminder>` **都会转义**」「移除是 **tombstone**」「压缩会在事件离开可见表层后**重新启用**它」 | 见左 | **这是 central-inbox 的官方对应物**；我们缺 replace/tombstone/转义/compaction 协调 |
| **多智能体编排** | **`dsh-subagent` / `ctx.subagents` / `ctx.agents.create()`** + `dsh-tool-subagent*`；官方 loop README：「subagent 在循环外部实现为 `ctx.subagents` 提供方」 | 通用 `ctx.jobs` + `dsh-tool-subagent` 负责后台收集 | 评估是否取代部分自研 |

### 4.4 官方的"该怎么写"规则里，有三条是我们今天踩中的

| 官方规则（`docs/defensive-patterns.zh.md`） | 我们的违反 |
|---|---|
| **「异步状态不是同步状态」**：「`agent.followup()` **没有逐消息的完成状态或结果**；**切勿把 `agent/status` 或 `whenIdle()` 当作某次 `followup()` 的结果**……真正拥有一次运行的自动化调用方必须显式定义其区间——例如**从消息的持久 inbox 回执到整个 agent 下一次进入 `idle`**」 | 我们的 `delivered` 直接取自 `followup` 未抛异常（**★★★ 代码级**） |
| **「正交结果独立上报」**：「每个独立事实（`timedOut`/`signal`/`exitCode`）都应**单独上报**；**切勿把一个标志的上报嵌套在另一个标志的分支中**，否则调用方可能把提前终止的运行误判为正常成功」 | **v1 附录 B 两次误判**（把"看到某字段"嵌套成"热重载"）；更早的 **crash 被计为 SURVIVED** 也是这个形状 |
| **「公共约定两侧都要遵守」**：收到同一结果的多种表示时，**应在通过公共 API 返回前将其规范化** | 我们的 `to` 有无数种表示，规范化散落在调用点（A4/A4b 才补上） |

**另有两条直接否掉我们的闸门做法**：

- 官方 `dsh-invariants`（`ctx.invariants`）规定运行时不变式「**可以断言什么**（**权威事件流或可变数据，绝不是服务或方法是否存在**）」⇒ 我们的 `selfcheck.js` 查 `typeof require === 'function'` **正好是官方明令禁止的那类**。
- 官方 `testing.zh.md`「测试层面的对应规则（**真实入口路径**、**验证实际结果**、**资源归属**）」⇒ 我们的两个自检模块**无 CLI 入口**（v1 §3.6），连"真实入口路径"都不满足。

### 4.5 官方对我们成本判断的一处补充（v1 完全没算）

`dsh-agent-loop` README「KV Cache 影响」：

> 普通历史增长仅追加，并保留可复用条目。**表层替换或压缩会从第一个被遮蔽的历史 token 起使复用失效。**

⇒ **每次注入都会打断 KV cache 复用，后续请求需重新 prefill。** 注入的成本**远不止**那几条消息的 token。这给"sender 侧尽量少注入"提供了官方论据，也解释了为什么官方把 `inject`（不唤醒）单独设为一个预设。

---

## 5. 收敛：一个根因、一套不变量、一个已存在的正解

### 5.1 单一根因

> **所有身份相关判定（自回声 / 自注入 / 去重 / @提及 / 审计）都建立在 `from` 上，而 `from` 是自由文本——不校验、可被硬编码覆盖、且把"身份"与"显示名"混成一个字段。**

三次"修过"（08-28 `value.from===NODE_ID` / 10-01 A6 v1 `isSelfEcho(from)` / 10-01 A6 v2 `from∩to`）**都只改了站点**。
官方 `TeamMessageSource` 给了正解：**`senderId`（持久身份）+ `senderName`（不可变标签）+ `messageId`（全局随机）三者分离**。

### 5.2 应立的不变量（对齐官方，而非我自创）

| # | 不变量 | 官方出处 |
|---|---|---|
| **I1** | 身份与标签分离：`senderId` 是持久 Session 身份，`name` 是不可变标签；**硬编码别名不得进入身份字段** | agent-team §身份与 roster |
| **I2** | 每条消息有**全局唯一 `messageId`**；去重键 = 该 id 或**内容 digest**，**不得用时间窗口** | agent-team / agent-instructions |
| **I3** | 投递语义分层：**ack 只在 target 的 pending inbox 条目或用户消息持久化之后写入**；`queued − delivered` = 恢复 mailbox | agent-team §持久 mailbox |
| **I4** | 不把 `followup()` 的返回当交付；运行区间 = **持久 inbox 回执 → 下次 idle** | defensive-patterns |
| **I5** | 载体改动走**原子替换 + 跨进程文件锁**；读方只见旧或完整新 | dsh-atomic-write |
| **I6** | 不变式断言**只允许**基于权威事件流或可变数据；**禁止**断言"服务/方法是否存在" | dsh-invariants |
| **I7** | 投递模式由**语义**决定，不由调用方随手选：通知类用 `inject`（不唤醒），需处理用 `steer`/`followup` | agent-loop §send 原语 |

### 5.3 一个已存在的正解

**别再造了。** 官方（实验性）的 `Agent Teams` 已经把这套东西设计完并写进文档；即使不采用其包，也**应当把上表 I1–I7 作为我们的目标契约**，并在 `~/dsh-comm-shared/identity.js` 里用断言固化。

---

## 6. 决策项与建议路径

### D1（必须先定）：**继续自研，还是对齐官方不变量？**

| 选项 | 代价 | 收益 |
|---|---|---|
| **A. 只对齐 I1–I7**（推荐） | 中：改 `from` 语义、去重键、ack 语义、载体 | 不动整体拓扑，风险可控；缺陷根因被拔掉 |
| B. 迁移到官方 Agent Teams | 高：**它未随 runtime 发布且为 experimental** | 拿到完整设计，但引入实验性依赖 |
| C. 维持现状、只做清淤（expires_at + DLQ） | 低 | queued 会降，但**新缺陷照旧产生** |

### D2：立刻可做且零风险的三件（不需重启、不改插件）

1. **修 `guard:434` 的伪造署名**：`repair_report` 不该把 `from` 写死 `mbp-ops`——记真实作者（`DSH_SESSION_ID`），`mbp-ops` 降为展示标签。⇒ 直接消灭"回路 2"的燃料（I1）。
2. **central-inbox 注入前判「作者 == 收件人」则跳过**（依赖 1；否则判据不存在）。
3. **`plugin-preflight.py` B 项隔离副作用**：冒烟时把 `CENTRAL_INBOX_LOG` 等指向临时路径，并断言"生产侧字节数/键数未变"（v1 §3.6 实证它会写生产日志）。

### D3：仍需你裁决的旧项

- `agent-way` 去重**淘汰策略**是否统一到成员集合（现为 10 分钟窗口）
- 重启窗口：A 批（A4/A4b/A4c/A6 + 两处空转闸门）已 GO 待生效；是否与 D2 合批

### D4：官方基准带来的三个"可以不做"

| 原计划 | 新判断 |
|---|---|
| 路线图第 5 步：**换 SQLite 载体**（原标"唯一高危项"） | **很可能不必做**——`dsh-atomic-write` 已提供 I5 所需原语 |
| 自建 DLQ | 改为建在官方 **`ctx.jobs`** 上 |
| 自建去重语义 | 直接用 **`messageId` / digest**（I2） |

---

## 附录 A · 本次考古的检索路径（可复现）

```bash
# 安装纪年
find ~/.dsh/sessions -name "session.jsonl*" -exec stat -f "%Sm %N" -t "%Y-%m-%d %H:%M" {} \; | sort | head
stat -f "%Sm %N" -t "%Y-%m-%d" /Applications/CLD.app ~/.dsh
# bus 自身起点
node -e 'const j=require(process.env.HOME+"/.dsh/agent-bus.json");/* 见 v1 §3 */'
# 原型期（08-15~08-31）全量文本产物
find ~/dsh-collab -maxdepth 2 -type f \( -name "*.md" -o -name "*.js" -o -name "*.py" \) \
  -not -path "*/datasets/*" -not -path "*/target/*" -exec stat -f "%Sm|%N" -t "%Y-%m-%d" {} \; | sort
ls -lT ~/external-link-mcp/ ~/.dsh/bus-bridge/
# 更早祖先
ls -lT ~/Downloads/AgentHub* ~/Downloads/agenthub*
# 官方文档（本机镜像已空，改取 GitHub）
curl -s https://api.github.com/repos/deepseek-ai/deepseek-harness/contents/docs
curl -s -o /tmp/dshdocs/agent-lifecycle.zh.md \
  https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/agent-lifecycle.zh.md
```

## 附录 B · 官方文档本地副本

本次已落 `/tmp/dshdocs/`（易失）：`agent-lifecycle` / `capability-seams`(675行) / `defensive-patterns` / `event-producer-consumer` / `persistence-catalog`(8782行) / `architecture` / `development` / `testing` / `config-catalog`(4523行) / `module-graph`(1700行) / `session-format-status` + `sub-{agent-team,compaction,jobs,persistence,core,extensions,invariants,schedule,scope}.zh.md`。
**建议**：把 `docs/` 重新克隆到 `~/tech-research/`（恢复 `guard_doc_check` 的 P0 数据源），并纳入版本管理——**一个空的官方镜像等于这条闸门不存在**。

## 附录 C · ⛔ 本次已证伪的推论

| 推论 | 真相 |
|---|---|
| 「官方文档不在本地，所以没法对照」 | 官方文档在 **GitHub `docs/`（75 项）+ 196 个包内 README**；只有 `~/tech-research` 是空的 |
| 「我们把总线造出来了，说明官方没有对应能力」 | 官方 **Agent Teams**（2026-08-05）覆盖身份/mailbox/task；**未随 runtime 发布**但文档与源码在 |
| 「热重载让我的改动已生效」 | v1 附录 B：那是我自己工具（CLI 测试 + 预检冒烟）的副作用；**模块缓存使改动仍需重启** |
| 「A6 v2 修好了自回声问题」 | 只修了 `from==to`；**`from` 被伪造（`mbp-ops`）那一类仍在跑**（回路 2） |

---

*本文由 mac-mini 中枢（session-fa1f9150）于 2026-10-01 整理，v2 增补官方基准重审。*
*★★★ 断言均附可复核路径；★/★★ 项不得据此动手改。*
