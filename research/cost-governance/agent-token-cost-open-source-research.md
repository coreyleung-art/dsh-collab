# Agent Token 成本治理 · 开源方案与论文调研

> 调研：2026-08-19 · HR 驾驶舱自主调研（未走总线/子代理通道）· 数据源=web 检索+原文抓取
> 目的：为「token 用量监控/成本治理/多智能体成本控制」找现成方案与学术依据（先调研后自研原则）

---

## 一、调研结论速览

1. **问题已被业界拆成三层**：可观测（事后）→ 网关（途中限流）→ 预检硬预算（事前拦截）——我们当前只有 gov 审计（事后代理口径），**缺途中/事前两层**
2. **多智能体 token 预算治理已有开源中间件**（agent-cost-guardrails 等，纯 Python、无网关依赖），可替代自研 gov quota
3. **论文给出两条硬杠杆**：① 缓存经济（keepalive 经济学：热缓存可省 10-100 倍输入成本）② 本地路由+提示压缩（Local-Splitter：编辑/解释类负载省 45-79% 云 token）——直接对应我们的 run_code 上下文放大问题
4. **ack/通信风暴（我们 61.8% 的头号问题）是学界研究热点**：KV-cache 通信压缩、多智能体路由预算化、通信剪枝——已有可直接借鉴的机制

## 二、开源方案全景（按请求生命周期三阶段 + 专项）

### 2.1 可观测层（事后记录 · 已有同类=gov audit）
| 工具 | 关键能力 | 自托管 | 备注 |
|---|---|---|---|
| **Langfuse** | traces/token/成本/延迟/eval | ✅ | 事实标准，社区大 |
| **AgentOps** | agent 会话级追踪+成本 | ✅ | 面向 agent |
| **Helicone** | 代理式采集，token/成本 | ✅ | 轻量 |
| **OpenLLM-Monitor** | 多供应商统一观测 | ✅ | 即插即用 |
| **llm-accounting** (PyPI) | 纯库记账 | ✅ | 轻量库 |
| **openmeter** | 用量计量计费引擎 | ✅ | 通用 metering |

### 2.2 网关层（途中限流 · 我们当前完全没有）
| 工具 | 关键能力 | 备注 |
|---|---|---|
| **LiteLLM** | 统一网关：按 key 月预算（超限 429）、限速、多供应商路由、缓存 | 可直接包在我们模型调用前 |
| **Portkey** | 网关+缓存+预算 | 商业/自托管 |
| OpenRouter | 统一 API（预算按 key） | SaaS |

### 2.3 预检硬预算层（事前拦截 · 对我们最有价值）
| 工具 | 关键能力 | 备注 |
|---|---|---|
| **Runcap** | **运行前成本预估 + 运行中硬上限（超限 429 中止）+ 无损压缩（delta-encode 实测省 ~38%）** | 编码 agent 循环场景神器，100% 本地 |
| **agent-cost-guardrails** (GitHub sapph1re) | CrewAI/AutoGen/LangGraph 中间件：**per-agent 硬预算、circuit breaker、50/80/100% 告警回调、30+ 模型价目（含 DeepSeek）** | 纯 Python 零基础设施，**直接对标我们的 gov quota 自研方案** |

### 2.4 多智能体专项预算治理
| 工具 | 关键能力 |
|---|---|
| **tokenbudgetorchestrator** | 多智能体主动预算治理引擎 |
| **agent-tokenops** (PyPI) | run 级 token 治理控制面 + SDK |
| **llm-budget** | agent 舰队硬预算原语 |
| **token-budget-contracts** | 预算契约库 |

## 三、论文清单（按三个问题域）

### 3.1 缓存经济（对应：上下文重复放大）
| 论文 | 核心发现 | 我们的应用 |
|---|---|---|
| **Keeping the Cache Warm Pays: Keepalive Economics for Agentic Workloads** (arXiv:2607.19214) | agent 工作负载下 keepalive/热缓存的经济性——缓存命中输入价差 30-60 倍，保持缓存热=最大单项杠杆 | 长会话/循环读取场景：主动保活缓存，省 90%+ 输入成本 |
| **Tail-Optimized Caching for LLM Inference** (2025) | 面向 agent 尾延迟的缓存优化 | 缓存策略设计参考 |
| **Learning to Compress Prompts with Gist Tokens** (2304.08467) | 提示压缩 token | 与 Local-Splitter T2 同族 |

### 3.2 云 token 消减（对应：run_code 25.9% + 上下文放大）
| 论文 | 核心发现 | 我们的应用 |
|---|---|---|
| **Local-Splitter: Seven Tactics for Reducing Cloud LLM Token Usage on Coding-Agent Workloads** (arXiv:2604.12301) | 7 战术：本地路由/提示压缩/语义缓存/本地草稿+云审/minimal-diff 编辑/结构化意图提取/批处理+供应商缓存；**T1+T2=编辑·解释类省 45-79%，RAG 类全套省 51%**；开源 shim 讲 MCP+OpenAI 兼容 | 最贴近我们：run_code 重负载可前置本地小模型路由+压缩（qwen3.5-2b 已装） |

### 3.3 多智能体通信成本（对应：agent_send 61.8% ack 风暴）
| 论文 | 核心发现 | 我们的应用 |
|---|---|---|
| **KVCOMM: Cross-context KV-cache Communication** (NeurIPS 2025) | 跨会话共享 KV 缓存，避免整段上下文重发 | 我们的 ack/回执=短消息但触发整轮上下文——缓存共享可削放大器 |
| **Budgeted Multi-Agent Routing: Adaptive Role Assignment and Communication Compression** (IEEE) | 角色分配+通信压缩的预算化路由 | 直接对标「哪些回执值得发、哪些合并」——可固化为我们的 ack 纪律学术版 |
| **MOC: Multi-Order Communication** (ICML 2026) | 多阶通信优化 | 消息合并/批处理参考 |
| **SafeSieve** (AAAI) | 多智能体通信渐进剪枝 | 「纯确认免回」的形式化依据 |

## 四、与我们的映射（差距与落点）

| 我们的问题 | 现成方案 | 落点 |
|---|---|---|
| 无精确计量（代理口径） | Langfuse/LiteLLM 网关计量 或 llm-accounting 库 | P1：接入前先评估 DSH 宿主是否暴露用量 API |
| gov quota 自研 | **agent-cost-guardrails / tokenbudgetorchestrator** 直接对标 | P0 候选：不重复造轮子，评估适配 DSH 工具面 |
| ack 风暴（61.8%） | 论文 KVCOMM/Budgeted Routing/SafeSieve + 我们已执行的 ack 纪律 | 已执行纪律=第一刀；学术机制=长期 |
| run_code 上下文放大 | **Local-Splitter 7 战术**（本地路由+压缩+minimal-diff） | P1：qwen3.5-2b 本地前置路由实验 |
| 缓存经济 | Keepalive Economics 论文 | P1：长会话保活/缓存策略 |
| 自动化成本失控 | Runcap 预检硬上限（单次任务预算） | P2：任务级硬预算试点 |

## 五、落地建议

- **P0（立即）**：ack 纪律（已执行）+ 评估 agent-cost-guardrails 是否可替代 gov quota 自研（避免造轮子）
- **P1（1-2 周）**：Local-Splitter 本地路由实验（qwen3.5-2b 前置，编辑/解释类省 45-79%）；缓存保活策略
- **P2（储备）**：Runcap 式任务级硬预算；Langfuse 级精确可观测（需宿主 API 或网关接入）

---
*来源：GitHub（OpenLLM-Monitor/Lumina/agent-cost-guardrails/tokenbudgetorchestrator/llm-budget）、PyPI（llm-accounting/agent-tokenops）、n1n.ai 对比文（Runcap vs Langfuse vs LiteLLM）、arXiv 2604.12301/2607.19214/2510.15152/2304.08467、NeurIPS'25 KVCOMM、ICML'26 MOC、IEEE Budgeted Multi-Agent Routing、AAAI SafeSieve*
