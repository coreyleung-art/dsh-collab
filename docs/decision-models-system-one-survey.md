# 云厂商与基础设施厂商的「决策模型 / System One」层：设计逻辑与产品形态调研

调研日期：2026-10-08 · 全部结论附来源 URL，并标注「官方文档 / README 自述 / 第三方报道」

---

## 0. 结论摘要（先看这 7 条）

1. **类别定义已被全行业接受**，但**命名分裂成两派**：TypeSafe 叫 System One，Simon Willison 与多数开发者叫 decision models。两个词在官方文档里已混用（Cloudflare、AWS、Ollama、vLLM-SR 都同时写两种）。
2. **`/v1/systemone` 已成为事实标准**，但不是唯一方言。采纳者：Cloudflare（自称 fully compatible）、Fastino、Ollama、OpenRouter、LiteLLM、Vercel（TypeSafe 客户端路径）、AWS Strands Decider（自托管 server 路径）、vLLM-SR（SystemOne-compatible）。**唯一公开背离的是 OpenAI**：走 `POST /v1/decisions`，用 `input` 而非 `state`、`questions` 数组而非 map、`predicate` 而非 `noul`。
3. **各家设计逻辑的真正分歧不在「要不要做决策模型」，而在「决策能力物理上住在哪一层」**——权重里 / 网关里 / 路由算法里 / 用户设备上。据此可分成 4 条主路线（见第三节）。
4. **共同的技术内核是三件事**：(a) 输出空间由调用方在请求时枚举，模型永不产出无界文本；(b) 单次前向、无解码循环，因此 output tokens ≈ 每题 1 个，输出近乎免费；(c) 质量指标从 accuracy 转为**校准**（ECE / Brier）。
5. **「不用训练分类器」是被最多厂商独立引用的价值主张**——Cloudflare、AWS、vLLM-SR 三家原文都说了同一件事：新类别写进请求即可生效，不必重新训练。
6. **AWS Strands Decider 的 pointer head 是这批产品里最独特的架构选择**（去掉 LM head，换一个约百万参数的指针头），且官方明说前一代 slot head "performed significantly worse"。详见第五节。
7. **Cloudflare 做 Clef 的核心动机是边缘推理**：官方原文强调请求跑在"接近用户的 Cloudflare 网络 GPU 上"，让决策可以直接放进 agent 的请求路径。而且它有一个真实内部客户（威胁情报域名分类）。

---

## 一、厂商 × 设计逻辑对照表

| 厂商 / 产品 | 放在哪一层 | 形态 | 为什么（设计逻辑） | 官方原文 |
|---|---|---|---|---|
| **TypeSafe · Jev 1.13** | 模型层（本源） | 独立决策模型 + 自有协议 | 把「LLM 被用来做判定」这件事从 prompt-and-parse 变成类型化函数调用；定价与架构都为"高频窄判定"优化 | "Think of Jev as a frontier-intelligence function call: unstructured state in, typed probabilistic decisions out."（官方博客，经 Simon Willison 转引） |
| **Cloudflare · Clef / Clef-flash** | 模型层 **+** 边缘运行时 **+** 网关层（Workers AI） | 自研开源权重 + 边缘托管 + RL 微调服务 | 决策是低延迟、高 QPS、廉价的负载，天然适合边缘；且有真实内部需求（威胁情报域名分类）；RL 微调服务是变现路径 | "Requests run on GPUs across Cloudflare's network, running close to your users, so the network round trip stays short. You can put Clef directly in the request path of your agent."（官方博客） |
| **Perplexity · pplx-decider-v1 / v1.1-27b** | 模型层（自家 API 平台的一个模态） | 独立决策模型 + 自有端点 | 与搜索/多模态基础设施复用；以 $0.02/M 输入低于 Jev 定价切入 | "A decision model is a class of model built to make fast, structured decisions that software can use directly. … your code does the reasoning with the numbers it returns."（官方文档） |
| **Together AI · Tev1-4B-experimental** | 模型层，但真正卖的是**微调平台** | 复用 chat completions 的轻量模型 + 完整可复制配方 | 不卷模型卷平台：把"造一个决策模型"的成本压到 $17、25 分钟，让客户自己造 | README："We fine-tuned Qwen3.5-4B on Together AI… This repo contains the data recipe, training example, and saved results so you can fine-tune your own decision model." |
| **AWS · Strands Decider 2B** | 模型层，服务对象是**编排层**（Strands Agents SDK） | 开源权重 + CLI + 自托管 server + 训练配方 | 定位为 agent tool-call 前的窄检查点；企业要"在 AWS 安全边界内、不把数据发出去"；走 Strands Labs 实验项目生态打法 | "a small decision model optimized for fast experimentation, local development, and innovation"；"You can do all of this within your AWS security boundary, without sending data to any provider or service outside of this perimeter."（官方博客 / AWS 官方教程） |
| **Fastino · GLiDE** | 模型层（差异化=带思考） | 独立模型 + 自有端点 | 补上决策模型最大的能力缺口：复杂 multi-hop 判定；快评估、不确定时再分配算力 | "It makes a fast initial assessment, then allocates additional reasoning when the choice is uncertain."（官方博客） |
| **Ollama 0.35+** | 运行时层（本地） | 协议适配 + 本地推理运行时 | 让决策模型从"云 API"下沉为"本地库"：零网络往返、无额外成本、数据不出机器 | "Decision models can now be run at no cost with low latency. … This is great for tasks that require fast decisions, such as ticket triage, model routing, and content or safety moderation."（官方博客） |
| **OpenAI** | 模型层，但形态是**端点/模式**而非新模型族 | `gpt-6-luna` 上的专用端点 | 不新训非生成模型，而是在既有小模型上加一条 10x 快的专用评估路径 | "The Decisions API evaluates text, images, or both and returns typed answers about 10x faster than the Responses API."（官方文档） |
| **vLLM Semantic Router** | 编排层（决策模型作为路由的 signal 来源） | 自研 Vela / Decision 系列模型 + 路由器配置 | 让路由器用自然语言定义路由问题，替代"每种信号训一个分类器" | "Fixed-label classifiers answer only the questions they were trained for. A decision model answers 'does this need step-by-step reasoning?' … from the question text alone."（官方文档） |
| **NVIDIA · NeMo Switchyard** | 编排/网关层 | **路由库**，**未采纳 System One 协议** | 走的是另一条路：不用决策模型做判定，而是用路由算法选模型 | "模型路由通过编排专业模型和前沿模型来解决这一挑战"（官方技术博客） |
| **OpenRouter / LiteLLM / Vercel AI Gateway** | 网关层 | 纯协议适配 | 不改模型，做统一入口 + 计费 + 日志 + 格式转换 | LiteLLM："it has its own evaluate endpoint rather than `/chat/completions`. LiteLLM proxies that endpoint with logging and cost tracking."（官方博客） |

---

## 二、接口形态详细对比表

### 2.1 端点与协议关系

| 厂商 / 产品 | endpoint | 与 Jev 协议的关系 |
|---|---|---|
| TypeSafe Jev 1.13 | `POST /v1/systemone`（官方 HTTP API）；OpenRouter 上另有 `POST /api/alpha/decisions` | **本源** |
| Cloudflare Clef / Clef-flash | Workers AI：`env.AI.run("@cf/cloudflare/clef", …)`；模型卡另提供 `systemone()` 函数，接受并返回 `POST /v1/systemone` 请求/响应体 | **完全兼容**。官方原文："Clef follows the System One API, so you can switch an existing Jev integration to Clef by changing the endpoint and model." |
| Perplexity Decider | `POST https://api.perplexity.ai/v1/decisions` | **同构，路径不同**。三原语名称一致（noul/choice/score），但是独立端点、独立文档体系 |
| Together Tev1 | `POST https://api.together.ai/v1/chat/completions` | **不兼容**。README 自述为"independent, Jev-inspired implementation and does not use Jev's answers as training labels" |
| AWS Strands Decider 2B | CLI：`strands-decider ask`；server：`strands-decider serve --port 8000` → `POST localhost:8000/v1/systemone`；SageMaker：自建容器实现 `/invocations` + `/ping` | **server 路径暴露 `/v1/systemone`**；CLI 路径为自有形态 |
| Fastino GLiDE | `POST https://api.fastino.ai/v1/systemone`，`model: "fastino/glide"` | **conforms to the System One model schema**（官方原文） |
| Ollama 0.35+ | `POST http://localhost:11434/v1/systemone` | **基于 Jev API**，且可把 TypeSafe 官方 SDK 直接指向本地（`TYPESAFE_BASE_URL`） |
| OpenAI | `POST https://api.openai.com/v1/decisions` | **自有方言**（见下） |
| vLLM Semantic Router (Vela 2.0 / Decision 1.0) | 非公共 API：`AutoModel.from_pretrained(..., trust_remote_code=True)` 后调 `m.system_one(state=…, questions=…)`；路由器内作为 `model_runtime` deployment 配置 | **SystemOne-compatible interface**，但**扩展了协议**：新增 `set` 与 `span` |
| OpenRouter | `POST /api/v1/systemone`（TypeSafe SDK 仅改 baseURL）+ `POST /api/alpha/decisions` | 双 surface 转发 |
| LiteLLM | `POST /v1/systemone`（System One 格式）+ `POST /v1/decisions`（OpenAI Decisions 格式） | **同时支持两个方言**，内部统一为共享格式 |
| Vercel AI Gateway | `POST https://ai-gateway.vercel.sh/v1/evaluate`（自有）；TypeSafe 客户端用 baseURL `https://ai-gateway.vercel.sh/typesafe`；另有 OpenAI 兼容 `/v1/decisions` | 三条路径并存 |
| NVIDIA NeMo Switchyard | OpenAI / Anthropic / Responses API（"模拟 LLM 网关"） | **未查到任何采纳 System One 协议的说明** |

### 2.2 两个方言的具体差异（关键发现）

| 维度 | System One 方言（TypeSafe 系） | OpenAI Decisions 方言 |
|---|---|---|
| 输入字段 | `state` | `input`（字符串，或含文本/图像的用户消息数组） |
| questions 结构 | **对象 map**，key 即问题名 | **数组**，每项带 `name` |
| yes/no 原语名 | `noul` | `predicate` |
| 返回结构 | `answers` **map**（按问题名索引） | `answers` **数组**（按提问顺序，每项带 `name`） |
| 额外返回类型 | — | `refusal`（拒答） |
| Vercel AI SDK 命名 | — | `boolean`（原语名第三次改名） |

> **分析**：同一个原语在生态里已有三个名字（noul / predicate / boolean），端点也分裂成 `/v1/systemone` 与 `/v1/decisions`。LiteLLM 在 v1.105.0-rc.3 同时上两条路由并在内部做统一转换，事实上**确认了两个方言并存**，而不是收敛成一个。这是本次调研最重要的标准-状态判断。

### 2.3 返回内容、原语支持、鉴权与计价、限制

| 厂商 / 产品 | 返回内容 | 原语支持 | 鉴权与计价 | 限制 |
|---|---|---|---|---|
| **TypeSafe Jev 1.13** | `choice` → 选中项 + 每项概率 + confidence；`score` → 概率加权分 + 每级概率 + confidence（+legend）；`noul` → 0–1 概率 | choice / score / noul | Bearer；**$0.042/M 输入，输出免费** | context 32,000 tokens；**仅文本**（图像/音频/视频不支持）；官方称多问题并行评估，耗时≈单问题 |
| **Cloudflare Clef / Clef-flash** | 同 Jev；choice → choice + confidence + probabilities；score → 期望 score + confidence + legend + probabilities；noul → 概率 | noul / choice / score | Workers AI 计费；**权重 Apache-2.0**，可自托管 | context **64K**；**单请求最多 64 个问题**；文本 / JSON / **图像 / 视频**（最多四张图）；27B 与 9B 两档 |
| **Perplexity Decider v1.1-27b** | noul → 概率；choice → 每选项概率 + 最可能项；score → 每级概率 + expected score | noul / choice / score | Bearer（任意 Perplexity key）；**$0.02/M 输入，输出免费** | context **262K**（OpenRouter 数据）；**单请求最多 128 个问题**；v1.1 支持 text/JSON/images，v1 在 OpenRouter 上仅 text/JSON |
| **Together Tev1-4B** | **单个字母**（A/B/C…），应用侧映射回语义 key。README 明确："Logprobs are model preferences, not calibrated confidence." | **仅 choice** | Bearer；$0.04/M 输入，输出免费 | **选项 2–24 个**；`max_tokens: 8`；`temperature: 0`；`enable_thinking: false` |
| **AWS Strands Decider 2B** | choice → choice + confidence + 每选项概率；noul → 概率；score → score + confidence + 每级概率；server 额外返回 `latency_ms` | choice / noul / score | **无托管 API、无按调用计费**（Amazon 发言人，经 VentureBeat）；Apache-2.0 自托管，成本自负 | 1.9B 参数，base Qwen3.5-2B-Base；`--device mlx/cuda/mps/cpu`；vision 需 `--vision` + transformers ≥ 5.18，base64 图像放进 state |
| **Fastino GLiDE** | 选中 choice + confidence（margin）+ 每选项 probabilities | 官方示例**仅展示 choice**；noul/score 是否支持**未查到** | `Authorization: Bearer $FASTINO_API_KEY`；**计价未查到** | **未查到**（模型规模、选项上限、context 均未在公开材料中给出） |
| **Ollama 0.35+** | 同 Jev 结构；choice + probabilities + confidence；noul；score + legend + probabilities + confidence；含 `usage.input_tokens / output_tokens` | noul / choice / score | **本地运行无额外成本**；SDK 需设 `TYPESAFE_API_KEY=ollama` | 明确的选项数/状态长度上限**未查到**；首波模型：nimble 9B（Bespoke Labs）、tev1 4B、tev1:0.8b（Together） |
| **OpenAI gpt-6-luna** | `answers` 数组；predicate → probability；choice → choice + 每选项概率；score → 概率加权平均（可落在级别之间）；另有 `refusal` | predicate / choice / score | Bearer；**独立费率**（具体数字未查到，官方称 billed at its rates） | **public beta**；**仅 gpt-6-luna 一个模型**；官方称"10x faster than the Responses API" |
| **vLLM-SR Vela 2.0** | `answers` + `spans`；span 返回 `{label, start, end, text, probability}` | choice / noul / score **+ set + span** | 自托管；模型卡 Apache-2.0 | Vela-2.0-0.3B：8,192 token 输入；0.8B/4B/9B：16,384；span 目标 > 2048 token 需额外窗口序列 |
| **LiteLLM（网关）** | 透传上游格式（两种方言各自保持） | 取决于上游 provider | Bearer（LiteLLM 虚拟 key）；按上游 token 计价并做 spend tracking | 校验前置：缺 `state`、问题格式错误、**>128 问题**、单选项、非 JSON body → 400 |
| **Vercel AI Gateway（网关）** | 透传；AI SDK 侧返回 `.answers.<name>.probability` | 视上游；AI SDK 中原语叫 `boolean` | Bearer（AI Gateway key） | 未查到具体上限（见官方 decisions 参考页） |

### 2.4 延迟数据（**测试条件不同，不可直接比较**）

| 产品 | 数字 | 测试条件（引用时必须带） | 来源类型 |
|---|---|---|---|
| Clef / Clef-flash / Jev | Clef 中位 **209.3 ms**、p95 238.6 ms；Clef-flash 中位 **38.8 ms**、p95 122.4 ms；Jev 中位 **524.1 ms**、p95 536.0 ms | Cloudflare 自述："Across our **43 benchmark runs**"（Cloudflare 自家 benchmark，托管在 Workers AI 上） | 官方博客 |
| Clef（威胁情报工作流） | **2.2 s** fetch+render+classify vs gpt-oss-120b **4.7 s** | 含 Browser Run 抓取与渲染的**端到端工作流**，不是纯推理延迟；且 gpt-oss-120b 同一工作流只返回 2 个分类 | 官方博客 |
| Strands Decider 2B | 中位 **约 115 ms**；README 另称"median 115 ms on an RTX 3090"；M3 MacBook 上小任务中位 **约 153 ms**；v18 图表：230 次请求中位 **106 ms**、p95 **296 ms** | **本地推理**，RTX 3090 / M3 MacBook。106 ms 那组"包括 HTTP 往返"，且**排除了一次 7.7 秒的首次冷启动** | 官方博客 + README 自述 |
| Strands Decider（server 示例） | `"latency_ms": 140.03` | 单次示例响应，非统计量 | README 自述 |
| Ollama nimble 9B | **平均 91 ms/决策** | **本地运行**于 MacBook Pro **M5 Max**，Pac-Man 示例场景 | 官方博客 |
| Jev（托管服务） | 端到端**约 70–500 ms** | TypeSafe 自述的托管服务端到端区间 | 官方博客（经 Simon Willison / VentureBeat 转引） |
| Perplexity pplx-decider-v1.1-27b | P50 **0.28 s** | OpenRouter 聚合的 provider P50 | 第三方平台数据 |
| OpenAI Decisions API | "**10x faster** than the Responses API" | 相对倍数，**无绝对数字** | 官方文档 |

> ⚠️ 纪律提示：上表 **209.3 ms（Cloudflare 托管，自家 43 次 benchmark）**、**38.8 ms（Clef-flash，同上）**、**115 ms（AWS 本地 RTX 3090）**、**91 ms（Ollama 本地 M5 Max）** 四组数字分属不同厂商、不同硬件、不同负载、不同统计口径，**任何横向对比都是无效的**。

---

## 三、设计路线分类

**分类依据（两条正交的判据轴）**：
- **主轴——「决策能力物理上住在哪一层」**：权重里 / 网关里 / 路由算法里 / 用户设备上。
- **副轴——「交付物是什么形态」**：端点（API）/ 权重（可下载）/ 配方（可复制）/ 协议（可转换）。

### 路线 1：模型层 · 自研决策模型（Model-first）
**包含**：TypeSafe Jev、Cloudflare Clef、Perplexity Decider、Together Tev1、AWS Strands Decider、Fastino GLiDE、Bespoke Labs nimble、vLLM-SR Vela/Decision，以及社区开源（Mapika decider-4b、Imajev-4B、Kev 9B、Laya、Plumb-4B、Liquid d1、JevK5 等）

**判据**：拥有自己的权重 / 后训练流程；返回概率分布而非文本；在 JevBench 或 Decision Index 上有独立分数。

**内部再分三派（架构分歧）**：

| 子派 | 做法 | 代表 | 证据 |
|---|---|---|---|
| **换头派** | 去掉 LM head，换成专用打分头 | AWS（pointer head，~1M 参数）、Cloudflare（joint schema head） | Strands README："discard its language-modelling head … replace it with a small pointer head"；Clef 模型卡："Joint schema head … scores all options of all questions jointly" |
| **复用头派** | 保留原 LM head，只让它吐一个字母 | Together Tev1 | README："We use ordinary LoRA supervised fine-tuning with **Qwen's existing language-model output head**." |
| **自适应推理派** | 在决策模型里加 thinking，不确定时增加算力 | Fastino GLiDE | 官方博客："first thinking decision model"；"allocates additional reasoning when the choice is uncertain" |

> 注意：**OpenAI 是这一路线里的异类**——官方文档没说 `gpt-6-luna` 是新训练的决策模型，只说是 Responses API 之外的一条更快评估路径。是否去除了生成能力，**官方未说明**，不下结论。

### 路线 2：网关层 · 协议适配（Protocol-adaptation）
**包含**：OpenRouter、LiteLLM、Vercel AI Gateway、（Ollama 也带强适配色彩）

**判据**：不自研模型；核心工作是**把某个决策协议端到端接进自己的基础设施**（鉴权、计费、日志、可观测、格式转换）。

**证据**：
- LiteLLM："it has its own evaluate endpoint rather than `/chat/completions`. LiteLLM proxies that endpoint with logging and cost tracking."
- Vercel："Change the base URL and API key. Your `systemOne` calls, `noul` questions, and response shapes stay exactly as they are."
- OpenRouter："Point an existing TypeSafe client at OpenRouter by changing its base URL."

**为什么选这个位置**：决策模型的调用模式与 chat 完全不同（无 messages、无流式、无 output token），**必须独立端点**，因此网关必须做真实的协议适配而非简单转发。这也解释了为什么 LiteLLM 要同时维护两条路由并在内部统一格式。

### 路线 3：编排层 · 路由优先（Router-first）
**包含**：NVIDIA NeMo Switchyard、OpenRouter Jev Router、vLLM Semantic Router（作为路由器时）

**判据**：决策能力不产出"业务答案"，而产出"把请求送给哪个模型"。

**关键区分——同一目标的两条不同实现路径**：
- **用决策模型做路由**：OpenRouter `typesafe/jev-router` —— "Jev assesses the task, its difficulty, and the potential benefit of a stronger model. … **Jev makes the routing decision; the selected model generates the response.**"
- **用路由算法做路由**：NVIDIA Switchyard —— 提供免调优路由器（LLM 分类器、阶段路由器、升级路由器）与可调优路由器（预填充路由器，读 LLM 残差流估计查询复杂度）。**未查到 Switchyard 采纳 System One 协议的任何说明。**

> 也就是说，用户线索里把 NVIDIA Switchyard 归入这一层是对的，但它**不属于 System One 生态**，而是"另一种 System One"——用路由器实现决策，而非用决策模型。

### 路线 4：边缘 / 本地运行时（Edge & Runtime）
**包含**：Cloudflare Workers AI（边缘）、Ollama（本地）

**判据**：卖点不是模型质量，而是**决策发生的位置**。

**证据**：
- Cloudflare："Requests run on GPUs across Cloudflare's network, running close to your users, so the network round trip stays short."
- Ollama："Decision models on Ollama are fast, as requests don't have to travel over a network. Nimble 9B averaged 91ms per decision … when running locally on an M5 Max."
- Ollama 另一层意义：**"No additional costs"** —— 决策模型的单位经济学从"按 token 付费"变成"电费"。

### 副轴：交付形态（与主路线正交）

| 交付形态 | 代表 | 商业逻辑 |
|---|---|---|
| **端点** | Perplexity、Fastino、OpenAI | 按调用/按 token 收租 |
| **权重** | Cloudflare（Apache-2.0）、AWS（Apache-2.0）、vLLM-SR（Apache-2.0） | 开源引流，向上卖托管/微调/硬件 |
| **配方** | Together（$17 / 25 分钟）、AWS（含完整训练数据与脚本）、Cloudflare（RL 微调服务） | 卖"造模型的能力"而不是模型 |
| **协议** | OpenRouter、LiteLLM、Vercel | 卖统一入口与可观测 |

> **Cloudflare 是唯一同时占据「模型层 + 边缘运行时 + 网关层」三层的厂商**，且交付形态是"权重 + 托管 + 微调服务"三件套——这是本次调研中最完整的一次卡位。

---

## 四、基础设施采纳现状

### 4.1 Ollama 0.35+ 的原生 `/v1/systemone` 意味着什么

**官方博客怎么说**（2026-09-29，官方）：
- 端点：`/v1/systemone`，as of **Ollama 0.35**
- 定位原话："Ollama now supports decision models, based on TypeSafe's Jev API for fast, typed decisions"
- 三大卖点原文列出：**No additional costs** / **Lower latency when run locally** / **Three new decision models available today via Ollama**
- 场景原文："This is great for tasks that require fast decisions, such as ticket triage, model routing, and content or safety moderation."
- 可把 **TypeSafe 官方 Python SDK** 直接指向本地：`TYPESAFE_BASE_URL=http://localhost:11434` / `TYPESAFE_API_KEY=ollama` / `TYPESAFE_DEFAULT_MODEL=nimble`
- 路线图："Faster performance on Apple Silicon powered by MLX"、"More models specializing in different kinds of decision making"

**首波支持模型**（官方原文）：
| 模型 | 来源 | 规模 |
|---|---|---|
| `nimble` | Bespoke Labs | 9B |
| `tev1` | Together AI | 4B |
| `tev1:0.8b` | Together AI | 0.8B |

**战略含义**：这是决策模型类别的**第一次"下沉"**。此前全部是云 API；Ollama 把它变成和 `ollama pull llama3` 同级的本地资源。**三方 SDK 兼容是信号最强的一点**——TypeSafe 官方的 Python SDK 不改代码即可跑在 Ollama 上，说明协议已经足够稳定到被第三方运行时独立实现。

> 注：`docs.ollama.com/capabilities/decision` 与 `docs.ollama.com/api/systemone` 两个官方文档页确实存在（见来源），但该站为 SPA、正文抓取为空，**其页面内容未获核实**，本节全部细节来自官方博客。

### 4.2 OpenRouter / Vercel AI Gateway / LiteLLM

| 网关 | 决策模型支持 | 关键细节 |
|---|---|---|
| **OpenRouter** | ✅ 双 surface：`POST /api/v1/systemone` + `POST /api/alpha/decisions` | 模型 ID 映射：`jev-1.13` → `typesafe/jev-1.13`；`jev-latest` → `~typesafe/jev-latest`。额外返回 `id` / `provider` / `usage.cost`。**注意**：SDK 的 `client.models.list()` 会失败，因为 OpenRouter 的 `/api/v1/models` 返回 OpenRouter 自己的响应结构，SDK 会拒绝 |
| **Vercel AI Gateway** | ✅ 三路径 | ① TypeSafe 客户端：baseURL `https://ai-gateway.vercel.sh/typesafe`；② 自有 HTTP API：`POST /v1/evaluate`；③ **OpenAI 兼容 `/v1/decisions`**。AI SDK：`experimental_evaluate`（旧）/ `experimental_decide`（新，yes/no 类型叫 `boolean`）。新集成模型名 `typesafe-ai/jev`；OpenAI 侧模型 ID 是 `openai/gpt-6-luna-decisions`（与 `openai/gpt-6-luna` 语言模型 ID **分开**）。另有 `eve` 框架把 Jev 作为默认评估模型 |
| **LiteLLM** | ✅ 双路由 | v1.103.0-rc 起先支持 Jev（`/typesafe/v1/systemone` 透传）；**v1.105.0-rc.3 新增 Decisions API 路由**：`/v1/systemone`（System One 格式）+ `/v1/decisions`（OpenAI 格式），**两路由共用一个内部格式**，因此任意 Decisions 模型可在任一路由上调用。Providers：`openai/`（gpt-6-luna）、`perplexity/`、`typesafe/`、`openrouter/`、`cloudflare/clef`、`cloudflare/clef-flash`、自托管 `strands_decider/`（需 `api_base`）。`/health` 会用单问题 Decisions 调用探活 |

### 4.3 vLLM Semantic Router 的设计逻辑

**它的设计逻辑与所有其他厂商都不同**：它不是"提供一个决策模型 API"，而是**让路由器内部的信号机制换成决策模型**。

官方原文（"Decision Signal" 文档）：
- 问题陈述："Fixed-label classifiers answer only the questions they were trained for. A decision model answers 'does this need step-by-step reasoning?' or 'is this about our product?' from the question text alone."
- 优势："A new question works as soon as you write it; there is no classifier to train."
- 工程细节："All questions of one request to the same model travel in one call, including the PII question"；"A late or failed answer makes the signal unknown; the request still goes through."（**决策失败不阻断请求**，这是路由场景特有的容错设计）
- 配置形态：把自然语言问题写成 `routing.signals.decision[]`，配 `predicate: gte: 0.7` 阈值，再在 `routing.decisions[].rules` 里消费

**与 System One 的关系**：Vela 2.0 博客原文 **"Bringing span-level decisions to System One"**，接口自称 **"SystemOne-compatible interface"**——即**采纳协议并扩展**。扩展了两个原语：
- **`set`**：哪些标签适用（多标签）
- **`span`**：文本中每个标签出现在哪（返回字符偏移）

`span` 的机制很有巧思，官方描述为："A span question is a grid of yes/no decisions: one for every word of the text and every label in the question."

**模型谱系**（官方 + 模型卡）：
- Vela 2.0 家族：0.3B（encoder，307M）/ 0.8B（756M）/ 4B（4.2B）/ 9B（7.9B），输入 8,192 或 16,384 tokens
- Vela 2.0 混合模型建立在 **Decision 2.0 的 Eos-0.8B / Nox-4B / Lux-9B** 之上，用 Qwen3.5 文本骨干
- 0.3B encoder 起自 **Decision-1.0-Kai** 的 Choice trunk
- Decision-1.0-Route-0.6B 是 Kai 在路由器信号语料上微调的版本（Apache-2.0）

### 4.4 有没有形成事实标准？

**结论：形成了一半——协议层是事实标准，端点与命名层在分裂。**

**已标准化的部分**（多方独立实现同一协议，证据充分）：

| 采纳者 | 采纳证据 | 来源类型 |
|---|---|---|
| Cloudflare | "fully Jev-API compatible"；"Clef follows the System One API" | 官方博客 |
| Fastino | "conforms to the System One model schema" | 官方博客 |
| Ollama | "based on TypeSafe's Jev API"；可直接接官方 SDK | 官方博客 |
| AWS Strands Decider | server 暴露 `/v1/systemone` | README 自述 |
| vLLM-SR | "SystemOne-compatible interface" | 官方博客 |
| OpenRouter / LiteLLM / Vercel | 端点级兼容 + SDK baseURL 迁移 | 官方文档 |

共同词汇：`state` / `questions`（map）/ `choice`·`noul`·`score` / 每题 `probabilities` + `confidence`。

**未标准化的部分**：
1. **端点**：`/v1/systemone`（多数）vs `/v1/decisions`（Perplexity、OpenAI）vs `/v1/evaluate`（Vercel 自有）
2. **yes/no 原语名**：`noul`（TypeSafe 系）vs `predicate`（OpenAI）vs `boolean`（Vercel AI SDK）
3. **输入字段**：`state` vs `input`
4. **questions 结构**：map vs 数组
5. **原语集合**：三方原语 vs vLLM-SR 的五原语（+set/span）
6. **评测基准也是两套**：**JevBench**（Benchmark Heaven 独立维护，官方声明"not affiliated with or endorsed by TypeSafe AI"）vs **Decision Index 0.2.1**（Cloudflare 称"Jev Decision Index"，HF Space 为 `multimodalart/jev-decision-index`，**是否 TypeSafe 官方维护未查到**）

**判断**：这是典型的"**由单一厂商定义、被生态快速采纳、但被最大厂商（OpenAI）另起方言**"的标准演化早期形态。LiteLLM 双路由并存是最强的证据——网关厂商已经**接受分裂为既成事实**，选择做转换层而不是等收敛。

---

## 五、重点对象深度档案

### 5.1 AWS Strands Decider 2B（pointer head 机制）

**pointer head 是什么**（官方 README + 官方博客，两者一致）：

> "take a pretrained decoder LLM torso (**Qwen3.5-2B-Base**), **discard its language-modelling head** — taking away its ability to generate text — and replace it with a small **pointer head** of about a million parameters. The head scores each option by comparing the hidden state at the `<mask>` position against the hidden state at **that option's own last token**."

即：不新增可学习的分类槽（slot），而是让模型**在自己已有的 token 表示空间里"指"向选项**——把每个候选选项文本的最后一个 token 的隐状态，与 `<mask>` 位置的隐状态做打分。躯干用 **rank-16 LoRA** 适配，head 跑 fp32。

**与其他家的关键差异**：Cloudflare 用的是"joint schema head"（可学习的接头），Together 干脆复用原 LM head 只出字母，而 AWS 是**唯一公开解释"指针"语义**的。官方明确说了上一代架构的失败："the first one was similar, but used a **slot head** that we found performed significantly worse"。当前发布版是 **v19**（`StrandsAgents/strands-decider-2B-hobson-v21`，架构代号 **"Hobson"**）。

**与 AWS 基础设施的关系**：**不通过 Bedrock**。官方路径是自托管——AWS Builder Center 的官方教程（2026-10-05）演示用 CodeBuild 构建推理镜像 → ECR 存镜像 → S3 存权重 → **SageMaker AI 实时端点**（`ml.g6.xlarge`，NVIDIA L4 24GB；模型权重约 5GB），通过 IAM 授权后用 `InvokeEndpoint` 调用。VentureBeat 引 Amazon 发言人（背景说明）：**目前只提供开源模型，无托管 API、无按调用计费**。因此问题 4 的答案是：**它属于 Strands Labs 实验项目生态，不是 Bedrock 托管服务，与 SageMaker 的关系是"用户可以自己部署上去"**。

**官方定位原文**："a small decision model optimized for fast experimentation, local development, and innovation"；"While you can run it locally during your development cycle, you can also deploy it on AWS infrastructure … **You can do all of this within your AWS security boundary, without sending data to any provider or service outside of this perimeter.**"——数据主权是 AWS 的核心卖点。

**性能自述（须带条件）**：JevBench 公开集上 v19 约 **72% 准确率、0.35 Brier**；官方自述"3rd of 33 in the 2B class, and 1st of 30 excluding the just-over-2B models"。**注意**：VentureBeat 指出同尺寸的 Mapika decider-2b v11 在这张图上约 76% / 0.32，**两项都优于 AWS**；且该图**不含 Jev 本身**，因此"Strands Decider 胜过 Jev"的说法未被证实。

### 5.2 Cloudflare Clef / Clef-flash

**为什么一个 CDN/边缘厂商要做决策模型**——三条动机，官方原文支持：

1. **边缘推理确实是核心动机**。"Hosting on Workers AI adds to that speed. Requests run on GPUs across Cloudflare's network, running close to your users, so the network round trip stays short. **You can put Clef directly in the request path of your agent**, then hand off to an LLM on Workers AI to take action." 决策模型是低延迟、高 QPS、单次前向的负载——与边缘 GPU 的产品形态天然匹配。
2. **有真实内部客户**。官方原文说在自家 **Threat Intelligence 团队**上测试，用于域名分类："it might classify a domain with a 95% chance it is a fashion website, 85% ecommerce, 1% phishing"。
3. **有明确的变现闭环**。同期发布 **RL 微调服务**，可把 Clef 按客户工作负载调优——模型开源（Apache-2.0）引流，托管 + 微调收费。

**官方技术说明**：Clef 后训练自 **Qwen3.8-27B**（含 vision encoder），Clef-flash 来自 **Qwen3.5-9B**，两者都是 **Apache-2.0** 权重。核心组件是 **joint schema head**——"a small transformer head that reads the backbone's final hidden states, **routes evidence from the state to each question**, and scores **all options of all questions jointly**"，输出每题每选项一个 logit，按题做 softmax。**关键差异化**：(a) **有 vision encoder**（对比 Jev 仅文本，官方明说"Unlike text-only decision models, Clef has a vision encoder"）；(b) **64K context**（对比 Jev 32K）；(c) 单请求最多 64 问题。命名由来官方也解释了（音乐谱号比喻，"CF" 呼应 Cloudflare）。

**延迟数据（209ms / 38.8ms）的条件**：出自官方博客，原文限定 "**Across our 43 benchmark runs**"，即 Cloudflare 自家 benchmark 在 Workers AI 上的结果：Clef 中位 **209.3 ms**（p95 238.6 ms）、Clef-flash 中位 **38.8 ms**（p95 122.4 ms）、Jev 中位 **524.1 ms**（p95 536.0 ms）。官方自述 Clef 比 Jev 快 **2.5x**（中位）、Clef-flash 快 **13x**。**该组数字不适用于与其他厂商的自托管延迟做比较**（硬件、网络路径、负载构造均不同）。

**质量自述**：10 个 decision benchmark 中 7 个最高分；在 TypeSafe 自家 workflow evals 上 4 项中赢 3 项（发票处理、客服、安全事件）。**注意**：这些分数分别来自 Cloudflare 的自家评测与 TypeSafe 的评测集，标注为官方自述。

### 5.3 Fastino GLiDE

**定位**：自称"**the first thinking decision model**"（2026-09-30 发布）。核心创新是**自适应算力分配**——官方原文："It makes a fast initial assessment, then **allocates additional reasoning when the choice is uncertain**. This adaptive reasoning allows the model to excel in highly complex, multi-hop tasks such as making selections among hundreds of tools, selecting the best next action from hundreds of possible paths, and judging or verifying reasoning-intensive model output."

**这解决的是决策模型类别的公认短板**：AWS 官方博客明确写了这个短板——"this approach (generating all outputs in a single parallel pass) makes it **significantly worse at solving complex problems than reasoning models**"。GLiDE 试图在保持"类型化输出"的同时补上这条。名字 GLiDE = **G**eneralized **L**ightweight **D**ecision **E**ngine。

**性能（官方自述，非独立验证）**：使用官方 **Decision Index 0.2.1 scorer**，GLiDE 得 **64.81**，领先 Jev 公布的 **57.91** 达 **6.90 skill points**；五个评测领域全胜，38 个 benchmark 中赢 31 个；在 Knowledge and Reasoning 领先 **11.5** points；CLadder 88.7% vs 72.6%，CRUXEval 92.6% vs 73.0%。**重要限定**：官方自己声明"GLiDE has not been added to the public leaderboard, where submissions to version 0.2.1 are currently paused"——即**这是自我报告分数**。

**接口**：`POST https://api.fastino.ai/v1/systemone`，`model: "fastino/glide"`，**conforms to the System One model schema**。返回"the selected `choice`, its `confidence` margin, and `probabilities` for every option"。官方示例是 agent 破坏性工具调用把关场景（`DROP TABLE sessions`），很能说明它瞄准的用例。

**未查到**：模型规模、架构细节、许可、延迟数据、noul/score 是否支持、计价方式——Fastino 的博客与示例只覆盖 choice。`docs.fastino.ai` 未获取到内容。

---

## 六、未查到项

以下为明确未能核实的项目，**不做推测**：

**产品与模型层面**
1. **Fastino GLiDE 的模型规模、架构细节、许可协议、计价方式、延迟数据**——公开材料（博客 + 示例）均未给出。
2. **GLiDE 是否支持 noul / score 原语**——官方示例只展示 choice；`docs.fastino.ai` 未能获取内容。
3. **OpenAI `gpt-6-luna` 是否是新训练的非生成式（去 LM head）模型**——官方文档只说 Responses API 之外有更快评估路径，未说明模型内部形态。**"10x faster" 是相对倍数，无绝对延迟数字。**
4. **OpenAI Decisions API 的具体费率**——官方只写"billed at its rates"，未给出数字。
5. **Together Tev1 是否有独立于 `/v1/chat/completions` 的决策端点**——未查到；官方文档明确用 chat completions。
6. **各家的选项数上限（除 Tev1 的 2–24 外）与状态长度上限**——Jev 只给出 context 32K，Clef 只给出 64K/64 问，Perplexity 给出 128 问/262K，均未给出"单题选项数上限"。
7. **Bespoke Labs `nimble` 9B 的模型卡、训练方法、许可**——Ollama 博客只给了名字与规模，未深挖。
8. **NVIDIA Switchyard 是否有任何 System One / Jev 协议采纳**——**未查到**；从官方技术博客看它走的是独立的路由算法体系（LLM 分类器 / 阶段路由器 / 升级路由器 / 预填充路由器）。

**评测与标准层面**
9. **"Decision Index 0.2.1" 的维护方是否为 TypeSafe 官方**——Cloudflare 称之为"Jev Decision Index"，HF Space 路径为 `multimodalart/jev-decision-index`（非 typesafe 组织），**维护主体未确认**。而 JevBench 明确声明与 TypeSafe 无关联。
10. **是否存在任何官方标准组织（如 OpenAPI spec、IETF、厂商联盟）在推进 System One 协议规范化**——**未查到**。协议事实上由 TypeSafe 单方定义，靠生态采纳传播。

**文档可及性**
11. **Ollama 官方文档页 `docs.ollama.com/api/systemone` 与 `docs.ollama.com/capabilities/decision` 的正文内容**——页面确实存在，但站点为 SPA，抓取仅返回目录壳层，**内容未获核实**。本报告中所有 Ollama 细节均来自官方博客。
12. **AWS Strands Decider 在 docs.aws.amazon.com 上的官方产品文档**——**未查到**；现有官方材料为 strandsagents.com 官方博客、GitHub README、以及 AWS Builder Center 官方教程（builder.aws.com，作者标注为 AWS Employee）。
13. **Perplexity 的 `/docs/decisions/models` 与 `/docs/decisions/pricing` 独立页**——返回 404，相关数据取自 quickstart 页与 OpenRouter 模型页。

**架构细节**
14. **TypeSafe Jev 的具体架构（是否换头、backbone 是什么）**——官方文档聚焦概念与接口，**未公开架构细节**。已知它自称构建了"a new model architecture, a parallel sampler, and RLCD"。
15. **Cloudflare / AWS 是否公开了完整的训练配方**——Cloudflare 仅说明 post-train 来源与 head 形态，**未见完整训练脚本**；AWS **明确发布了完整训练数据与脚本**（README + 训练配方）。

---

## 附：时间线（仅列有明确日期来源的事件）

| 日期 | 事件 | 来源类型 |
|---|---|---|
| 2026-09-15 | TypeSafe AI 发布 Jev / System One 概念 | 第三方（OrcaRouter 博客明确写"TypeSafe 自己是在 2026-09-15 发布该模型的"） |
| 2026-09-17 | OpenRouter 侧出现 `typesafe/jev-1.13-20260917` 版本串 | 官方响应示例 |
| 2026-09-20 | LiteLLM v1.103.0-rc 支持 Jev | 官方博客 |
| 2026-09-21 | Simon Willison 撰文讨论 Jev | 第三方报道 |
| 2026-09-24 | OrcaRouter 把 `typesafe/jev-1.13` 加入目录（Jev 首次可经第三方网关调用） | 第三方博客 |
| 2026-09-29 | Ollama 0.35 支持 `/v1/systemone`，首批 3 个模型 | 官方博客 |
| 2026-09-30 | Fastino 发布 GLiDE | 官方博客 |
| 2026-10-01 | Cloudflare 发布 Clef / Clef-flash + RL 微调服务 | 官方博客 + Changelog |
| 2026-10-01 | Perplexity `pplx-decider-v1-27b` 上 OpenRouter | 平台模型页 |
| 2026-10-01 | AWS 发布 Strands Decider 2B（VentureBeat 9:43 am PT 报道） | 第三方报道（含 AWS 提前提供的材料） |
| 2026-10-05 | AWS Builder Center 发布 SageMaker 部署教程 | 官方教程（AWS Employee 署名） |
| 2026-10-07 | Perplexity `pplx-decider-v1.1-27b` 发布（新增图像输入） | 平台模型页 |
| 未标日期 | OpenAI Decisions API（public beta，仅 gpt-6-luna） | 官方文档 |

---

## 来源清单

**官方文档 / 官方博客**
- TypeSafe System One 概念：https://docs.typesafe.ai/concepts/system-one
- Cloudflare Clef 发布博客：https://blog.cloudflare.com/clef-decision-models/
- Cloudflare Workers AI Changelog：https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/
- Cloudflare Clef 模型卡：https://huggingface.co/Cloudflare/clef
- Cloudflare Clef-Flash 模型卡：https://huggingface.co/Cloudflare/clef-flash
- Perplexity Decisions API 文档：https://perplexity.mintlify.app/docs/decisions/quickstart
- Ollama 官方博客：https://ollama.com/blog/ollama-now-supports-jev-style-decision-models
- Ollama 决策模型端点文档（页面存在，正文未核实）：https://docs.ollama.com/api/systemone
- Ollama 决策能力文档（页面存在，正文未核实）：https://docs.ollama.com/capabilities/decision
- Fastino GLiDE 博客：https://fastino.ai/blog/introducing-glide-the-first-thinking-decision-model
- OpenAI Decisions API 文档：https://developers.openai.com/api/docs/guides/decisions
- AWS Strands Agents 官方博客：https://strandsagents.com/blog/introducing-strands-decider/
- AWS Builder Center 部署教程：https://builder.aws.com/content/3KFnkGmzL3oHhDMFc2aicUDfXNm/deploying-strands-decider-2b-on-sagemaker-ai
- NVIDIA NeMo Switchyard 技术博客：https://developer.nvidia.com/blog/route-ai-agent-workloads-across-models-with-nvidia-nemo-switchyard/
- vLLM Semantic Router · Decision Signal：https://vllm-sr.ai/zh-hans/docs/tutorials/signal/learned/decision/
- vLLM-SR · Vela 2.0 博客：https://vllm-sr.ai/blog/vela-2-0-open-foundation-routing-models/
- Vercel AI Gateway × TypeSafe：https://vercel.com/changelog/ai-gateway-now-supports-typesafe-clients-and-http-api-for-jev
- Vercel AI Gateway × OpenAI Decisions：https://vercel.com/changelog/openai-decisions-api-now-available-on-ai-gateway
- OpenRouter Jev 文档：https://openrouter.ai/docs/guides/community/jev
- OpenRouter Jev SDK 指南：https://openrouter.ai/docs/guides/community/typesafe-sdk
- OpenRouter Jev Router：https://openrouter.ai/docs/guides/routing/routers/jev-router
- LiteLLM Jev 博客：https://docs.litellm.ai/blog/typesafe_jev
- LiteLLM v1.105.0-rc.3 发布说明：https://docs.litellm.ai/release_notes/v1.105.0rc3/v1-105-0-rc-3

**README 自述 / 模型卡**
- Strands Decider README：https://raw.githubusercontent.com/strands-labs/strands-decider/main/README.md
- Together Tev1 README：https://raw.githubusercontent.com/togethercomputer/tev1/main/README.md
- Together Tev1 模型页：https://www.together.ai/models/tev1-4b-experimental
- vLLM-SR Decision-1.0-Route-0.6B 模型卡：https://huggingface.co/llm-semantic-router/Decision-1.0-Route-0.6B
- JevBench README：https://raw.githubusercontent.com/fstandhartinger/jevbench/main/README.md

**第三方报道 / 平台数据**
- Simon Willison：https://simonwillison.net/2026/Sep/21/jev/
- VentureBeat（Strands Decider，含 AWS 发言人与图表）：https://venturebeat.com/technology/amazon-unveils-a-free-fast-open-source-jev-killer-strands-decider-2b-makes-decisions-in-fractions-of-a-second
- OrcaRouter（RLCD 解析）：https://www.orcarouter.ai/zh-CN/blog/rlcd-explained
- OpenRouter Perplexity Decider V1：https://openrouter.ai/perplexity/pplx-decider-v1-27b-20261001
- OpenRouter Perplexity Decider V1.1：https://openrouter.ai/perplexity/pplx-decider-v1.1-27b-20261006
