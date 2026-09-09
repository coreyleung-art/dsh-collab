# Agent-Network 底座蓝图候选调研 · R025 提前并行

> 调研：数据调查员调研子代理 · 2026-09-01
> 任务：为多蓝图系统的新候选 **agent-network（底座）** 提供论文/情报支撑——本机多智能体网络（20+ 前台角色 / agent bus / 黑板 / 红绿灯互斥）的底座设计
> 衔接已落链：黑板 2507.01701 · HLC 1808.05698 · Exactly-Once 1911.11286 · FlowerNet 协议 v1.0（`research/cost-governance/flowernet-protocol-v1.0-2026-08-23.md`）

---

## 结论（候选可行性 + 设计建议）

**候选可行，且是现有五蓝图里唯一缺位的"横切底座"——建议立项，定位为「演进型整合蓝图」，而非新建。** 判定依据：

1. **本机已有完整实践底座**：FlowerNet 协议 v1.0（FNP）已正式化黑板 KV（:8792）、HLC 全局时间轴、任务卡生命周期、事件桥（8803 SSE）、X-Writer 归属、红绿灯治理、通道分级、落链五步——**理论原型全部落地**，蓝图候选是把实践规范化为元层可复用资产，风险低。
2. **学界方向吻合**：2024-2026 多 agent 系统研究主线正是「黑板状态共享 + 事件驱动选择 + 共识收敛」（2507.01701）、「从单体编排走向微服务/分布式运行时」（2505.07838）、「控制面与计算面分离」（OpenClaw RFC #42026）、「协议栈分层」（Agent-OSI 2602.13795）——本机 FNP 的四层架构（应用/语义/传输/物理）与 Agent-OSI 分层思路同构，属于前沿而非过时设计。
3. **缺口明确**：agent bus（线程/消息/唤醒）与黑板（状态/任务）目前是两套并行机制，缺少统一规范层与监控层；`bus-queue-mechanism-analysis` 已暴露上下文膨胀/inbox 串行/重启唤醒风暴三大工程债——底座蓝图正是承接这些债的载体。

**设计建议（一句话）**：agent-network 蓝图 = FNP 语义层（自有协议，防逆向）+ agent bus 消息层（线程/红绿灯，演进保留）+ 监控安全层（落链/值班/授权），三层合一，对外暴露为元层可复用规范，与 flowernet-platform（技术）区分开——flowernet-platform 管"花店业务技术栈"，agent-network 管"多智能体协作底座本身"。

---

## 多 agent 系统论文（arXiv ID）

### 综述 / 架构（或然性最高，优先引用）

| arXiv ID | 标题 | 与本候选的关联 |
|---|---|---|
| **2507.01701** | Exploring Advanced LLM Multi-Agent Systems Based on Blackboard Architecture（已缓存） | **黑板架构直接理论依据**：agent 共享全部信息、按黑板当前内容选择执行 agent、迭代至黑板共识；token 更省——本机黑板 + 任务卡正是该模式的工程实现 |
| **2402.01680** | Large Language Model based Multi-Agents: A Survey of Progress and Challenges | 多 agent 协作机制全景：角色分工/通信/共识/记忆分类，可作为蓝图能力域清单的检核表 |
| **2504.19678** | From LLM Reasoning to Autonomous AI Agents: A Comprehensive Review | 单 agent → 自主 agent 的能力分层，用于定义"agent-network 上的节点最小能力契约" |
| **2601.01743** | AI Agent Systems: Architectures, Applications, and Evaluation（JACM） | 权威综述，架构模式归纳（含 orchestration 分类），支撑"底座蓝图"的架构域划分 |
| MDPI Future Internet 2026;18(6):326 | LLM-Based Multi-Agent Orchestration: A Survey of Frameworks, Communication Protocols, and Emerging Patterns | 框架/通信协议/新兴模式三角综述，直接对应本候选的编排+通信两大能力域 |

### 通信协议 / 网络拓扑

| arXiv ID | 标题 | 关联 |
|---|---|---|
| **2506.19676** | A Survey of LLM-Driven AI Agent Communication: Protocols, Security Risks, and Defense Countermeasures | agent 通信协议分类 + 安全风险面——为 FNP 信封格式与防逆向边界提供安全论据 |
| **2504.21030** | Advancing Multi-Agent Systems Through Model Context Protocol | MCP 用于多 agent 通信的架构分析；衔接 FNP「只借鉴工具描述思想」的边界声明 |
| **2602.13795** | Agent-OSI: A Layered Protocol Stack Toward a Decentralized Internet of Agents | **协议栈分层**（物理/链路/网络/传输/会话/表示/应用类比）——支撑 FNP 四层架构的合理性 |
| **2606.20573** | AONA: A Comprehensive Architecture and Workflow Design for Global Agentic Collaboration | 全局 agentic 协作架构，跨组织 agent 网络设计参考 |
| **2604.19540** | Mesh Memory Protocol: Semantic Infrastructure for Multi-Agent LLM Systems | 多 agent 共享语义基础设施（记忆网格）——对应黑板作为"共享状态层"的定位 |

### 编排 / 运行时

| arXiv ID | 标题 | 关联 |
|---|---|---|
| **2308.08155** | AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | conversation-driven 编排 + group chat manager——对应本机协调者 + thread 协作模式 |
| **2505.07838** | Moving From Monolithic To Microservices Architecture for Multi-Agent Systems | **单体→微服务**迁移路径，论证"agent 即服务"与总线解耦方向 |
| **2410.21793** | Histrio: A Serverless Actor System | 无服务器 Actor 运行时——actor 封装 agent + 自动扩缩的学术实现 |
| **2604.00344** | Agent Q-Mix: Selecting the Right Action for LLM Multi-Agent Systems through Reinforcement Learning | 动态 agent 选择——衔接黑板「按内容选 agent」的可学习升级路径 |

### 群体智能 / 去中心化

| arXiv ID | 标题 | 关联 |
|---|---|---|
| **2510.10047** | SwarmSys: Decentralized Swarm-Inspired Agents for Scalable and Adaptive Reasoning | 去中心化 swarm 推理——本机 20+ 角色网络的轻量协作参考 |
| **2505.04364** | Benchmarking LLMs' Swarm Intelligence | swarm 智能评测——为底座提供「协作增益」度量思路 |
| **2506.14496** | LLM-Powered Swarms: A New Frontier or a Conceptual Stretch? | 批判性视角：swarm 何时有意义——约束本机不要为 swarm 而 swarm |

---

## 通信 / 编排框架对比

### 范式对比（学术侧）

| 范式 | 代表 | 核心机制 | 本机对应 | 差距 |
|---|---|---|---|---|
| **黑板架构** | 2507.01701、Hearsay-II（1980） | 共享黑板 + 知识源竞争 + 迭代共识 | 黑板 :8792 + 任务卡 + 值班消费 | 缺「知识源触发条件」的显式声明（现靠值班轮询） |
| **Actor 模型** | Erlang/Akka、Histrio 2410.21793、Hewitt 1973 / Agha 1986 | 每个实体独立邮箱 + 消息传递 + 无共享内存 | agent inbox 拼接（splice 进上下文） | **inbox 即邮箱但无背压/优先级**——bus-queue 分析已点名 |
| **消息总线 / Pub-Sub** | Kafka/MQTT/事件桥 | 事件发布 → 订阅者消费，解耦生产消费 | 事件桥 8803 SSE + subscribe 去重 | 基本对齐；缺 QoS 分级与重放策略（已有 since_seq 可补） |
| **群体智能（Swarm）** | SwarmSys 2510.10047 | 大量轻量 agent 涌现式协作 | 值班巡检 / 批量唤醒 | 仅局部使用，不建议全量引入（2506.14496 提醒边界） |

### 框架对比（工程侧）

| 框架 | 编排模型 | 状态持久化 | 通信 | 对本底座的借鉴 |
|---|---|---|---|---|
| **OpenClaw** | daemon + Router（通道/账户/内容）+ Orchestrator + Scheduler | SQLite 本地状态 | adapter 集成层 + gateway RPC | Router 三路由维度（通道/账户/内容）、daemon 常驻、control/compute 分离 RFC #42026 |
| **AutoGen** | 对话驱动（group chat manager） | conversation history | 消息线程 | thread 协作模式已在本机 COLLAB 通道实现 |
| **AgentScope** | actor 式异步消息 + 分布式编排 | actor state | 异步消息传递 | actor 封装 + 消息背压设计（对标 inbox 改造） |
| **LangGraph** | 显式 StateGraph + checkpoint | **checkpointer 持久化**（每步快照） | 图边传递 | 任务卡生命周期 = 图节点；HLC seq = 版本化状态 |
| **A2A（Linux Foundation）** | AgentCard 能力发现 + 任务委托（JSON-RPC） | — | 跨组织互操作 | **能力发现**正对应 FNP v1.1 预告的 capabilities 上报 |
| **MCP** | 工具标准化（client-server） | — | 工具调用 | 仅借鉴工具描述思想（FNP §5 已声明边界） |

---

## 状态与一致性衔接

本机已有三篇一致性论文落链，agent-network 蓝图应显式引用为"状态域的理论契约"：

| 衔接论文 | 内容 | 在底座的落点 |
|---|---|---|
| **1808.05698**（已缓存） | Session Guarantees with Raft and HLC——混合逻辑时钟：物理秒×10⁶+逻辑计数 | **直接对应黑板时间轴 v0.3**：GET /clock 对时、GET /timeline?since_seq= 增量补漏、重启对齐基线——HLC 已工程化 |
| **1911.11286**（已缓存） | LogPlayer: Fault-tolerant Exactly-once | 任务卡回报幂等：result 镜像 results/<seq>、清卡 DELETE 幂等；「至少一次 + 幂等消费」应写入蓝图规范 |
| **1907.06250**（已缓存） | Delivery, consistency guarantees in distributed stream processing | 事件桥（8803 SSE）投递语义分级（at-most-once / at-least-once / exactly-once）的选择依据 |
| 2606.23521 / 2604.28138 / 2608.03836 | Concordia（LLM 推理 checkpoint）、CRAB（agent 沙箱 checkpoint/restore）、Resume Means Resume（工作流持久化一致性契约） | **会话恢复契约**：断点续跑、非幂等副作用跨重启的语义——本机 session.jsonl.zstd + 重启唤醒风暴的解法参考 |

**关键工程债衔接**（来自 `bus-queue-mechanism-analysis`）：
- 上下文只增不减 → 底座应定义「上下文压缩/归档策略」（HLC seq 可作压缩边界）
- inbox 拼接串行无背压 → Actor 邮箱背压 + 优先级队列（对标 Akka/AgentScope）
- 重启唤醒风暴 → since_seq 增量恢复（时间轴已有）+ 分批发唤醒

---

## 能力域建议

agent-network 底座建议五大能力域（均已有 FNP v1.0 实践雏形，蓝图负责规范化 + 补监控）：

| 能力域 | 核心内容 | 已有基础 | 蓝图补齐 |
|---|---|---|---|
| **① 编排 Orchestration** | 任务卡生命周期（CREATED→执行→回报→清卡）、max_concurrent 并发、协调者/黑板选 agent | FNP §2.4、blackboard-dispatch-protocol v1.0 | 知识源触发条件声明、动态选 agent（Q-Mix 方向）、编排可观测（任务卡状态机可视） |
| **② 通信 Communication** | 黑板 KV（状态共享）+ 事件桥 SSE（pub-sub）+ 通道分级（STATUS/ACK→黑板；TASK→p2p；COLLAB→thread；EVENT→eventbus；BATCH→mailbox；BROADCAST→白名单） | FNP §2.2/§2.5/§2.7、exlink-blackboard 路由 | 信封格式版本协商（v1.1）、inbox 背压、QoS 分级与重放 |
| **③ 状态 State** | HLC 全局 seq 时间轴、since_seq 增量补漏、X-Writer 归属审计、幂等回报 | FNP §2.3/§2.6、blackboard-timeline v0.3 | 会话恢复契约（checkpoint 语义）、上下文压缩边界 |
| **④ 监控 Observability** | 落链 5 步（落盘→入库→向量化→registry→报告）、值班消费协议、队列积压告警 | 落链已实现、值班协议 v1.0 | 上下文膨胀监控、唤醒风暴抑制、token 成本仪表（衔接 token-ledger） |
| **⑤ 安全 Security** | 红绿灯互斥锁、per-namespace 授权（v0.7）、通道白名单、X-Writer 审计 | FNP §2.7、agent-bus-permissions | 审批门控接入（衔接 dsh-approval）、A2A 式能力发现+授权策略 |

**与现有 agent bus 的关系：演进，非新建。** agent bus（agent-bus.json 线程/消息、红绿灯锁、唤醒）是底座的消息层组件，保留其 API 与数据结构（向后兼容，避免迁移成本）；agent-network 蓝图在其上加：① FNP 语义层契约（时间轴/任务卡/归属）② 监控安全横切面 ③ 与黑板/值班的统一入口。两者是「蓝图层整合既有运行机制」，不是重写。

---

## 参考项目借鉴

| 项目 | 关键设计 | 本底座借鉴点 | 不借鉴点 |
|---|---|---|---|
| **OpenClaw**（[架构 deep-dive](https://openclawblog.space/articles/openclaw-architecture-deep-dive) · [RFC #42026](https://github.com/openclaw/openclaw/issues/42026)） | daemon 常驻 + Scheduler/Router/Orchestrator + adapter 集成 + SQLite 状态；**控制面与 agent 计算分离** RFC | Router 三维路由（通道/账户/内容）→ 本机 wecom-inbox 路由升级；daemon 常驻进程模型；control/compute 分离 → 协调者与执行 agent 分层 | TypeScript 单体；不引入其代码，仅模式 |
| **AutoGen**（2308.08155） | conversation-driven + group chat manager | thread 协作已有（COLLAB 通道），无需引入 | 重对话编排不适合 20+ 常驻角色 |
| **AgentScope**（阿里） | actor 式异步消息 + 分布式执行 | inbox 背压/优先级改造 | 整体框架 |
| **LangGraph** | StateGraph + checkpointer 持久化 | 任务卡=图节点、checkpoint=HLC 版本化状态的类比 | 图 DSL 约束过强 |
| **A2A 协议**（[Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)） | AgentCard 能力发现 + 任务委托 JSON-RPC | FNP v1.1 capabilities 上报的协议形态参考 | 全量互操作（FNP 防逆向原则 §5 维持） |
| **MCP**（Anthropic） | 工具标准化 client-server | 工具描述思想（已声明借鉴边界） | 语义层不采用（FNP §5） |

---

## 本机组件盘点（实测 · 2026-09-01）

> 全部实测于本机（mac-mini 中枢），非纯 web 调研。黑板 8792/8803 运行中（rust-blackboard PID 16521）。

### ① 黑板系统

| 组件 | 形态 | 能力 | Rust 化状态 |
|---|---|---|---|
| **rust-blackboard**（:8792 API + :8803 SSE） | Rust 常驻（launchd 托管） | KV 存储（notes/data/tasks/nodes 命名空间）、**HLC 全局 seq 时间轴**（GET /clock 对时、GET /timeline?since_seq= 增量）、audit.jsonl 审计（5MB 轮转 + ARCHIVE_KEEP=10）、SSE 事件桥（写即广播）、设备注册（POST /register v0.6.3 + token 认证） | ✅ **已 Rust 化**（v0.6.3，手写 HTTP/1.1 零外部依赖，数据格式与 Python 版一字兼容） |
| **bb-\* 脚本族**（28 个，`scripts/`） | Python | bb-read/bb-write（读写）、bb-sub-daemon/bb-sub-gen（订阅）、bb-dispatch/bb-dispatch-learn（派发）、bb-channel（通道）、bb-gate/bb-handshake/bb-share/bb-proxy（治理/握手/分享/代理）、bb-absorb/bb-absorb-watch（吸收）、bb-blueprint\*/bb-dashboard/bb-workbench/bb-taskboard（面板/工作台/看板 UI）、bb-request-watch/bb-reuse-check/bb-send-check/bb-upgrade（巡检） | ⚠️ **大部分仍 Python**；bb-read 已 Rust 化（dsh-tools bb-read），其余待评估 |
| **rust-blackboard-mcp**（v0.7.0） | Rust MCP 服务 | 黑板 7 + 特征库 2 + 消息治理 1 = **10 个 MCP 工具**（Rust 全栈） | ✅ **已 Rust 化** |

### ② node-bridge（跨设备桥，rust-bridge）

| 能力 | 说明 | 状态 |
|---|---|---|
| 心跳 | 定期写 `nodes/<id>/heartbeat`（60s 默认） | ✅ v1.3.0 |
| 任务队列 | 从黑板 `tasks/<node>/queue/*` 取卡执行 → 写 `tasks/<node>/result`（FNP §4.1 的节点侧实现） | ✅ |
| notes 同步 | 黑板 notes → 本地 inbox 落盘 | ✅ |
| LLM 执行器（v2） | **三因子门禁**（flash/日配额/互斥锁）+ 退避重试 + dead-letter + 台账 | ✅ |
| identity（v1.3.0） | 启动自动注册 device_id + token | ✅ |
| 平台产物 | node-bridge-macos-arm64 / win-x64.exe / linux-x64 | ✅ 三平台 |

### ③ dsh-tools（rust-tools · 黑板固化工具集，Rust）

22 个子命令，全部已 Rust 化：

| 域 | 子命令 |
|---|---|
| 黑板 | `bb-read` / `bb-sub` / `handoff` |
| 队列 | `queue-drain` / `queue-condense` |
| 论文 | `paper-fetch` / `paper-audit` |
| 信源 | `source-trust` / `source-extend` |
| 总线 | `bus-bridge` |
| 编排 | `workflow` / `load-gate` |
| 运维 | `deploy-check` / `restart-guard` / `restart-gate` / `health` / `channel-audit` / `noise` / `sign` / `version` / `repo` / `ledger` / `tailnet-proxy` |

### ④ bus 总线（agent-bus + bus-bridge）

| 组件 | 形态 | 能力 | 状态 |
|---|---|---|---|
| **agent-bus 插件**（DSH） | 插件（动态版 v11 agbus-2/pkg-39 + 常驻版 dsh-plugin-agent-bus） | 数据 `~/.dsh/agent-bus.json`：threads(909)/locks/lightLog(50)/dedup/profiles/restartPlan/approvals；**8 全局工具**：agent_peers/agent_send/agent_broadcast/agent_thread/agent_light/agent_lock/agent_unlock/agent_unlock_all；投递走宿主真实收件箱（followup 唤醒）+ 持久化防抖写盘 | ✅ 运行中（协作网络 15 会话登记） |
| **bus-bridge**（跨设备总线桥） | Rust（替代 bus-bridge.js） | POST /bus/send(?wait=1)/receive/reply/outbox/status + /health；文件队列 `~/.dsh/bus-queue`（tasks|outbox，状态机 queued→processing→done|failed）；X-Webhook-Token 鉴权 + 来源/动作白名单 + TTL | ✅ **已 Rust 化**（纯 std::net + serde_json，零外部依赖） |

### ⑤ agent-way（DSH 插件 bundle）

`datasets/shared/dsh-plugin-agent-way-full-bundle-v1.3.0.tar.gz` —— DSH 侧 agent 工作台插件包：`@deepseek-ai/dsh-agent-presets` / `dsh-tools` / `dsh-system-prompt` / `dsh-session-persistence` / `dsh-agent-default-model` 等模块 + 客户端 UI（lib/dashboard.html / adapt.js，含 antistorm 防风暴补丁）。**形态：DSH 宿主插件包**，agent-network 蓝图可将其「预设/持久化/工具注册」作为底座扩展面参考。

### ⑥ 其他 Rust 化工具

| 组件 | 能力 | 状态 |
|---|---|---|
| rust-genebank | GeneBank 基因库（AI 网盘）Rust 版：注册层 + 文件存储 + 静态共享，API 与 Python 版一字兼容 | ✅ |
| rust-data-tools | 数据工具集（data-tools.log 在跑） | ✅ |
| scripts/ 目录 | 126 个脚本（bb-\*、paper-fetch.py、event-bus.py、task-card-expander.py、task-card-validator.py、deposit-reflow.py 等） | ⚠️ 混合（核心链路已 Rust 化，周边仍 Python） |

---

## 技术栈现状与缺口（Rust 化清单）

### 已 Rust 化（✅ 28 项）

| 类别 | 已 Rust 化 | 替代的 Python/JS 前身 |
|---|---|---|
| 黑板访问 | dsh-tools `bb-read`/`bb-sub` | bb-read.py / bb-sub 脚本 |
| 队列治理 | `queue-drain`/`queue-condense` | `learning/feature-library/queue-condense.py` |
| 论文链路 | `paper-fetch`/`paper-audit` | `scripts/paper-fetch.py`、`paper-cache/fetch_alphaxiv.py`、`paper-cache/audit_papers.py` |
| 信源治理 | `source-trust`/`source-extend` | 新工具（source-tools-design v1.0，无前身） |
| 跨设备总线 | `bus-bridge` | bus-bridge.js |
| 黑板服务器 | rust-blackboard（:8792/:8803） | blackboard-server-v0.6.py |
| 跨设备桥 | node-bridge（rust-bridge） | node-bridge.js（如有） |
| MCP 面 | rust-blackboard-mcp（10 工具） | blackboard-mcp（早期） |
| 基因库 | rust-genebank | genebank.py |
| 运维/编排 | deploy-check/restart-guard/restart-gate/health/channel-audit/noise/sign/version/repo/ledger/tailnet-proxy/workflow/load-gate/handoff | 分散脚本 |

### 待 Rust 化（⚠️ 缺口清单）

| 脚本 | 位置 | 现状/建议 |
|---|---|---|
| `backfill_papers_db.py` | research/paper-cache/ | papers-db 回填；paper-audit --fix 已覆盖部分 → **可并入 paper-audit** |
| `download_papers.py` | research/paper-cache/ | 论文下载；与 paper-fetch 通道重叠 → **评估并入 paper-fetch** |
| `bb-write.py` | scripts/ | 黑板写；dsh-tools 无 bb-write → **建议补（P0）** |
| bb-dispatch/bb-channel/bb-gate/bb-handshake/bb-share/bb-proxy | scripts/ | 派发/通道/治理——黑板语义层核心 → **P1 编排域优先 Rust 化** |
| bb-absorb/bb-request-watch/bb-reuse-check/bb-send-check/bb-upgrade | scripts/ | 吸收/巡检类 → **P3 监控域 Rust 化** |
| bb-blueprint\*/bb-dashboard/bb-workbench/bb-taskboard | scripts/ | UI/面板类 → **不建议 Rust，迁 web UI（蓝图平台 blueprint-api）** |
| event-bus.py / task-card-expander.py / task-card-validator.py / deposit-reflow.py | scripts/ | 黑板事件/任务卡展开/校验/回流——**FNP 语义层核心，P1-P2 优先** |
| com.investigate.paper-sync.plist | paper-cache/ | launchd 定时（非脚本，评估并入 dsh-tools 定时面） |

**判据**：核心数据面（黑板/队列/论文/信源）已 90% Rust 化；**语义面（任务卡展开/校验/派发/回流）与监控面（吸收/巡检）是下一批 Rust 化对象**；UI 面不 Rust 化（迁 web）。

---

## 阶段草案（agent-network 底座 P0-P5 分层）

> 分层参考 blueprint-platform-design-v0.3 的 P0-P5 思路（能力域 → 阶段化交付）；阶段内容结合本机实测现状标注就绪度。

| 阶段 | 分层 | 内容 | 本机现状 | 阶段目标 |
|---|---|---|---|---|
| **P0** | 基础通信 | 黑板 KV + 事件桥 SSE + FNP 信封标准化 + bb-write 补位 + 信封版本协商 | 🟢 90% 就绪（rust-blackboard 运行中、bus-bridge 已 Rust 化） | 通信契约冻结：信封格式/envelope v1.0、inbox 背压设计 |
| **P1** | 编排 | 任务卡生命周期规范化（CREATED→执行→回报→清卡）+ 协调者模式 + 知识源触发声明 + 派发/展开/校验/回流 Rust 化 + workflow/load-gate 接入 | 🟢 80%（任务卡 v1.1-2.0 + workflow 子命令；bb-dispatch 等仍 Python） | 编排语义层全部 Rust 化，动态选 agent（Q-Mix 方向） |
| **P2** | 状态管理 | HLC 时间轴 + since_seq 增量恢复 + X-Writer 归属 + 幂等回报 + 会话恢复契约（checkpoint 语义）+ 上下文压缩边界 | 🟢 85%（timeline v0.3 + /clock 已工程化；会话恢复契约未定义） | 状态契约：重启对齐基线 + Exactly-Once 幂等规范 + 压缩策略 |
| **P3** | 监控安全 | 落链 5 步 + 值班消费 + 红绿灯 + per-namespace 授权（v0.7）+ 审批接入 + 队列积压告警 + 上下文膨胀监控 + 唤醒风暴抑制 | 🟡 60%（落链/值班/红绿灯已有；v0.7 授权与监控面待实现） | 可观测 + 治理闭环：膨胀/风暴指标仪表 |
| **P4** | 扩展 | 能力发现（capabilities 上报，FNP v1.1）+ 协议版本协商 + 门店/设备接入标准化 + 插件化工具注册（R006）+ agent-way 预设接入 | 🔴 20%（v1.1 预告；source-tools 已示范工具注册） | 开放扩展面：新 agent/设备/工具即插即用 |
| **P5** | 优化 | token 成本仪表（衔接 token-ledger）+ inbox 背压/优先级（Actor 邮箱模式）+ 上下文归档策略 + swarm 场景评估（2506.14496 边界）+ 动态选 agent | 🔴 10% | 成本/延迟优化 + 协作增益度量（2505.04364） |

**与现有蓝图关系**：agent-network 是 flowernet-platform 的「横切底座」——flowernet-platform 管花店业务技术栈（协议/部署），agent-network 管多智能体协作底座本身（通信/编排/状态/监控/安全）；blueprint-platform 消费本蓝图（data/blueprint/agent-network/ 独立 namespace）。P0-P2 建立在已 Rust 化的现状上（低风险），P3-P5 是真正的增量投入。

---

## 证据来源

**arXiv（论文）**
- [2507.01701 黑板 LLM MAS](https://arxiv.org/abs/2507.01701)（已缓存 `research/paper-cache/2507.01701.md`）
- [2402.01680 LLM-based Multi-Agents Survey](https://arxiv.org/abs/2402.01680)
- [2504.19678 From LLM Reasoning to Autonomous AI Agents](https://arxiv.org/abs/2504.19678)
- [2601.01743 AI Agent Systems (JACM)](https://ar5iv.labs.arxiv.org/html/2601.01743)
- [2506.19676 LLM Agent Communication: Protocols, Security](https://ar5iv.labs.arxiv.org/html/2506.19676v2)
- [2504.21030 Advancing MAS Through MCP](https://ar5iv.labs.arxiv.org/html/2504.21030)
- [2602.13795 Agent-OSI Layered Protocol Stack](https://ar5iv.labs.arxiv.org/html/2602.13795)
- [2606.20573 AONA Global Agentic Collaboration](https://arxiv.org/abs/2606.20573)
- [2604.19540 Mesh Memory Protocol](https://ui.adsabs.harvard.edu/abs/2026arXiv260419540X)
- [2308.08155 AutoGen](https://arxiv.org/abs/2308.08155)
- [2505.07838 Monolithic→Microservices MAS](https://www.alphaxiv.org/abs/2505.07838)
- [2410.21793 Histrio Serverless Actor System](https://arxiv.org/abs/2410.21793)
- [2604.00344 Agent Q-Mix](https://arxiv.org/abs/2604.00344)
- [2510.10047 SwarmSys](https://huggingface.co/papers/2510.10047)
- [2505.04364 Benchmarking LLMs' Swarm Intelligence](https://www.semanticscholar.org/paper/74907a7c4cfe4edacb6d4b1a159877f48fee07ce)
- [2506.14496 LLM-Powered Swarms: Frontier or Stretch?](https://ethicseido.com/de/Iode/DocumentDetail?repoid=arXiv_repo&catId=cs&id=oai%3AarXiv.org%3A2506.14496)
- [2606.23521 Concordia LLM Inference Checkpointing](https://arxiv.org/abs/2606.23521)
- [2604.28138 CRAB Agent Sandbox Checkpoint/Restore](https://arxiv.org/abs/2604.28138)
- [2608.03836 Resume Means Resume（工作流持久化契约）](https://arxiv.org/abs/2608.03836)
- [MDPI：LLM-Based Multi-Agent Orchestration Survey](https://www.mdpi.com/1999-5903/18/6/326)

**已缓存衔接论文（`research/paper-cache/texts/`）**：1808.05698（HLC/Raft）、1911.11286（LogPlayer Exactly-once）、1907.06250（流处理投递一致性）、2410.21793（Histrio）

**工程/标准**
- [OpenClaw Architecture Deep Dive](https://openclawblog.space/articles/openclaw-architecture-deep-dive) · [OpenClaw RFC #42026 分布式运行时](https://github.com/openclaw/openclaw/issues/42026) · [RFC #72072 RuntimePlan](https://github.com/openclaw/openclaw/issues/72072)
- [A2A 协议发布（Google）](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) · [A2A 捐赠 Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [OpenClaw 多代理模式](https://inbounter.com/learn/openclaw/production/multi-agent-patterns) · [OpenClaw 并行专家通道](https://docs2.openclaw.ai/concepts/parallel-specialist-lanes)

**本机衔接文档**
- `research/cost-governance/flowernet-protocol-v1.0-2026-08-23.md`（FNP v1.0，核心衔接）
- `research/cost-governance/blackboard-timeline-v0.3-design-2026-08-23.md`（HLC 时间轴）
- `dsh-collab/blackboard-dispatch-protocol.md`（值班消费协议 v1.0）
- `dsh-collab/exlink-blackboard-architecture.md`（集中黑板+路由）
- `dsh-collab/bus-queue-mechanism-analysis.md`（上下文膨胀/队列机制）
- `dsh-collab/agent-bus-permissions.md`、`dsh-collab/bus-plugin-contract.md`（bus 契约）
