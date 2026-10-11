# System One / 快速决策模型：美国主流大厂的「逻辑设计」对标调研

- 调研日期：2026-10-10（材料截至 2026-10-09）
- 基线事件：2026-09-15 TypeSafe AI 发布 Jev，定义「System One 模型」
- 标注约定：**【官方原文】**=厂商自己的文档/博客/官方账号；**【媒体】**=第三方报道/社区；**【推断】**=本报告作者的判断

---

## 摘要：四条结论

1. **「System One」在 30 天内从一家公司的术语变成了行业品类词。** 四家被点名的厂里只有 OpenAI 直接跟进产品；AWS 用开源 2B 模型跟进；Anthropic / Google 走的是「思考预算」路线，**没有踏进这个品类**；Cohere / AI21 完全没动。

2. **OpenAI 的答案是「新端点 + 新提问契约」，不是「新模型」。** 它复用 gpt-6-luna 权重，用 `POST /v1/decisions` 把提问方式收窄成 predicate/choice/score 三种。这与 Jev/AWS/Perplexity 的「换架构（砍掉 LM head）」是**两种不同的技术路线**。

3. **「思考预算可调」与「独立决策模型」不对立，但也不互相覆盖。** 预算管的是「生成时花多少算力」，决策模型管的是「要不要生成」。真正的分水岭是**校准概率是否作为产品交付物**——而这恰好是 Gemini 3 系停返 logprobs、Anthropic 无原生概率分布之后留下的空缺。

4. **最强的互补性证据来自同时拥有两条产品线的 OpenAI 自己**：官方文档教你把 Decisions API 当作通往推理模型的**路由入口**（Voice → Decisions → `reason: 转 Responses API reasoning model`）。即决策层是 System 2 的看门人，不是替代品。

---

## 一、厂商 × 设计逻辑对照表

| 厂商 | 如何理解 System 1 | 产品形态 | 接口 | 是否返回概率 | 官方原文引用 |
|---|---|---|---|---|---|
| **OpenAI** | **同一前沿模型的一个「收窄提问」的专用推理模式**，独立成端点 | DevDay 2026 发布 Decisions API，`gpt-6-luna` 为唯一模型；09-29 有限预览 → **10-06 公开 beta** | **独立端点** `POST /v1/decisions`（非 chat/responses 参数） | ✅ 是。「Both `choice` and `score` return probabilities over discrete options」，另有 confidence | 「By focusing the model on that choice, we can make it extremely fast while keeping capabilities like image understanding, broad language support, and safety protections.」——Sam Altman, DevDay 2026【官方/转述】<br>「The Decisions API evaluates text, images, or both and returns typed answers **about 10x faster than the Responses API**.」【官方文档】 |
| **Google** | **思考预算的档位问题**（同一模型，档位从 0 到高） | 无独立决策模型；`thinking_level` / `thinkingBudget` | **同一 `generate_content` 端点的参数** | ❌ 无概率分布。Gemini 3 系**不再返回 logprobs**（官方论坛答复为「intended behavior」） | 「Gemini 3 models use the `thinking_level` parameter ... optimize between latency and reasoning depth.」`MINIMAL`: 「Uses the fewest possible tokens for thinking. Best for straightforward tasks.」【官方文档】 |
| **Anthropic** | **不是独立品类**，只是「结构化输出 + 可控思考」的工程组合 | 无决策模型产品线。2026-09/10 的发布是 Claude Code mods、Claude for Government、plugins、Tag connectors | **同一 Messages API 的参数**：`output_config.format`（JSON schema）+ `thinking.budget_tokens` | ❌ 无原生概率分布（第三方适配器用「prompted estimate of P(true)」代替） | 「Structured outputs constrain Claude's responses to follow a specific schema」；「Extended thinking in manual mode gives you direct control over how much Claude thinks.」【官方文档】 |
| **AWS** | **一类新的小模型**——砍掉 LM head 的「指针头」模型，专供混合 agent | **Strands Decider 2B**，2026-10-01 开源（Apache-2.0），权重上 Hugging Face | **独立模型 + CLI**（`strands-decider`），非 `/v1/systemone` 契约 | ✅ 是。官方称每次决策带「high-quality reliability score」 | 「In exchange for this reduction in flexibility, decision models are faster and more capable at a given size ... **the probability is meant to be calibrated** ... That last property is what lets you build 'decide when sure, escalate when not' into your code.」【AWS Builder Center，AWS 员工】<br>「this approach ... makes it significantly worse at solving complex problems than reasoning models」【官方博客】 |
| **Microsoft / Azure** | **网关/路由层的契约支持**，不是自研模型 | 无自研决策模型。Azure Databricks 把 System One 当作**托管模型的对外契约** | `POST https://<host>/ai-gateway/typesafe/v1/systemone`（Unity Gateway 路由到 Unity Catalog 模型服务）；另有 SQL 函数 `ai_decide` | ✅ 是（透传契约，含 `probabilities` / `confidence`） | 「TypeSafe 的 System One API 是一种请求和响应格式 ... 在 Azure Databricks 上，你通过 Unity Gateway 向 Databricks 托管的 Unity Catalog 模型服务发送 System One 请求，**而不是发送给 TypeSafe 模型**。」【官方文档，页面更新于 2026-10-08】 |
| **Perplexity** | 一类可以**开源**的独立决策模型 | **Decisions API + `pplx-decider-v1-27b`**（Qwen3.8-27B 微调，Apache-2.0），2026-10-01 | 独立 Decisions API（`docs.perplexity.ai/docs/decisions/quickstart`） | ✅ 是 | 自测 11 项基准 7,210 样本：**85.71% vs Jev 84.51%**（厂商自测，非独立复现）【媒体引用官方文档】 |
| **Cloudflare** | 独立小模型，跑在自己的推理平台上 | **Clef / Clef-flash**，2026-10-01 上线 Workers AI | Workers AI 模型 + API | ✅ 是 | 官方 changelog 称其为 decision model【官方 changelog，经第三方引用】 |
| **Cohere** | **老式分类器**，不属于 System One 品类 | 无决策模型。最新发布是 Command A+（218B A25B MoE，开源权重） | **Classify v1/v2**（`/v1/classify`）：给 `examples` 的 text+label 对 | ⚠️ 返回 label + 每类置信度，但机制是 few-shot 分类而非校准决策原语 | 「To make a prediction, Classify uses the provided `examples` of text + label pairs as a reference.」【官方文档】 |
| **AI21** | 未表达任何立场 | **无对应产品**。2026 主线是并购（Nvidia $2–3B 谈崩 → 与 Nebius 接触），继续经营 Jamba / Jurassic / AI21 Studio | 无 | — | 未查到任何决策模型相关表述 |

**关键更正**：任务给出的线索里，OpenAI「Luna 模型有限预览」准确，但要补两点——(a) DevDay 本体在 **2026-09-29（当地时间，周二）**，TechCrunch 报道于 09-30；(b) 09-29 是**有限预览**，**2026-10-06 已转为面向全体开发者的公开 beta**，官方称「expect to GA in the coming weeks」。

---

## 二、四种设计路线的对比

### 路线 A：独立模型（换架构）

**谁**：AWS（Strands Decider 2B）、Perplexity（pplx-decider-v1-27b）、Cloudflare（Clef）、Liquid AI（d1）、Fastino（GLiDE）、TypeSafe（Jev）

**为什么**：
- 架构本身就说明了立场。AWS 的做法是「拿 Qwen3.5-2B 的躯干，**把 LM head 摘掉**，换成一个约 100 万参数的 pointer head」——不是让它少说话，而是**让它结构上无法生成文本**。
- 这带来三个只有独立模型才有的性质：输出永远不会是非法类型；**在给定尺寸下**判断准确率更高；概率分布是原生产物而非事后拟合。
- 代价也说得直白。AWS 官方博客承认：「this approach（single parallel pass）makes it **significantly worse at solving complex problems than reasoning models**」。
- 经济性是结构性的，不是折扣：Jev 输出 token 计费为 0（$0.042/M 输入）、pplx 输出免费、d1 输出免费、OpenRouter 上 gpt-6-luna-decisions 输出 $0。**没有自回归解码，所以输出 token 根本不存在。**

### 路线 B：模式切换（同一模型调档）

**谁**：Google、Anthropic

**为什么**：
- Google：Gemini 3 用 `thinking_level`（`MINIMAL` / `LOW` / `MEDIUM` / `HIGH`），官方对 `MINIMAL` 的描述是「Uses the fewest possible tokens for thinking. Best for straightforward tasks.」——这是把「快」当作**算力档位**，不是新品类。Gemini 2.5 的 `thinkingBudget` 可设 0 关闭思考、-1 动态。
- Anthropic：`thinking: {type: "enabled", budget_tokens: N}`（最小 1024），官方定位「Manual mode remains useful when your workload requires predictable latency or precise control over thinking costs.」——同样是旋钮。
- **这条路线的结构性缺口**：调低档位得到的是「更快的生成」，不是「校准的概率」。Gemini 3 系已不返回 logprobs（官方开发者论坛答复这是 intended behavior），Gemini 2.5 于 2026-10 退场；两家都没有原生的 `probabilities` / `confidence` 字段。
- 第三方只能自己补。Vercel AI SDK 的 `decisionModel` 适配器明确记载：Anthropic 与 Google 的适配器「adapt structured language-model output for all three types, evaluating all questions in one prompt. Their Boolean answers contain **prompted estimates of P(true)**, and Choice and Score answers **omit probability distributions**.」并且默认请求 `reasoning: 'none'`。
- 换句话说：**Vercel 把「模式切换 + 结构化输出」拼成了一个决策模型的形状**，但概率是「问出来的」而不是「算出来的」。这是路线 B 与路线 A 最本质的差别。

### 路线 C：路由层 / 网关特性

**谁**：Microsoft/Azure、Vercel AI Gateway、OpenRouter、LangChain

**为什么**：
- Microsoft 是最纯粹的例子。Azure Databricks 不让 System One 落到 TypeSafe 的模型上，而是**把 System One 当作一种请求/响应格式**，经 Unity Gateway 路由到自己的 Unity Catalog 托管模型（示例用开源 `system.ai.openjev-qwen35-4b`）。同一套契约还能进 SQL：`ai_decide` 函数。
- 这等于宣告：**System One 是一种接口标准，不是一个必须外购的模型。**
- 网关侧同理：Vercel AI Gateway 在 Jev 发布后第 2 天就接入，官方称 24 小时内触达近 13% 的付费团队（同期约为 GPT-5.6 家族的 2 倍）；LangChain 出 TypeSafeClassifier + AutoMode 中间件；OpenRouter 出 Jev Router（用 Jev 给每个请求挑模型和推理力度）。

### 路线 D：仅 API 契约（结构化输出）

**谁**：Anthropic；Cohere（老式版本）

**为什么**：
- Anthropic 的答案在官方博客里写得很清楚：Structured outputs = 「JSON outputs」（`output_config.format`）+「Strict tool use」（`strict: true`），目标是「guarantee schema-compliant responses through constrained decoding」——解决的是**解析失败**，不是**决策校准**。
- 时间线也支持「没跟进」的判断：结构化输出 2025-11 发布、2026-02-04 GA；而 2026-09-24 至 10-01 的 Claude 官方博客条目全是 Claude Code mods、Claude for Government GA、plugins 开发者门户、Claude Tag connectors——**没有一条与决策模型有关**。
- Cohere 的 Classify 是另一回事：它是 few-shot 分类器（需要每个标签至少 2 个示例、最多 2500 个示例、单次最多 96 条输入），**标签集合在训练/示例期就固定**。Jev 式的「请求时用自然语言声明任意 bounded 问题」它做不到。所以 Cohere 属于「有相关能力，但不是同一品类」。

### 归类的边界情况：OpenAI 属于哪一类？

**OpenAI 是 A + C 的混合体，且更偏 C。**

- 它有**独立端点**（`POST /v1/decisions`）、**独立计量**（$0.10/M 输入、输出 $0）、**独立 serving 路径**——形态上像路线 A。
- 但它**没有训练新模型**：`gpt-6-luna` 是 2026-09 已发布的通用模型，Altman 的措辞是「By **focusing the model on that choice**」——是**收窄提问**，不是换架构。
- 官方文档还专门划了边界：「Use Decisions when your application needs one of these answer types. Use **Structured Outputs** with the Responses API when you need to generate an object that follows your own JSON schema ... or **function calling** when you need a model to request a tool call with arguments.」
- **【推断】** 这说明 OpenAI 的赌注是「System 1 = 服务端的一种受约束推理契约」，而不是「System 1 = 一种新模型」。它与 AWS/Perplexity 的路线在**产品结果**上趋同，在**技术成本**上分道：OpenAI 不需要新权重，AWS 需要一个新架构。

---

## 三、理论框架对照：thinking budget vs 独立决策模型

### 3.1 两者根本不在同一根轴上

| 维度 | 思考预算（Google / Anthropic） | 独立决策模型（Jev / Decider / gpt-6-luna decisions） |
|---|---|---|
| 控制的量 | 生成时投入多少算力 | 要不要生成 |
| 输出 | 仍是 token 序列 | 类型化答案，0 输出 token |
| 概率来源 | logprobs（Gemini 3 已停返）或让模型「说出」置信度 | 原生 `probabilities` + `confidence` |
| 计费单位 | 输入 + 输出 token | 主要/仅输入 token |
| 失败模式 | 解析失败、幻觉标签 | 类型不可能非法，但**可能给出一个格式正确却错误的答案** |

### 3.2 「预算可调就够了」为什么不够

三个具体的、可验证的缺口：

1. **输出 token 成本没有消失。** 把 `thinking_level` 调到 `MINIMAL` 仍然要跑自回归解码、按输出 token 计费。而 Jev / d1 / pplx-decider / gpt-6-luna-decisions 的输出计费是 0。AWS 在官方文章里把这一点总结成「classifier-like price and latency」。
2. **校准不是副产品，是产品。** AWS Builder Center 的表述最清楚：「**Calibration as a product feature.** The probability is the point, not a by-product, so you can set thresholds in code.」预算旋钮不承诺任何校准保证。
3. **概率信号本身在退化。** 一篇 2026-09-10 的 arXiv 论文（2609.10996）记录了所谓「compatibility shift」：在 2025 年后的头部闭源模型上，「优先用 logprobs」这条经典建议**已经不再成立**，verbalized confidence 反而是更稳健的信号。而 Gemini 3 系连 logprobs 都不再提供。**当上游厂商把概率通道关掉时，需要校准的下游就只剩两条路：要么自己问、要么换一个把概率当交付物的模型。**

### 3.3 对立还是互补？——互补，而且厂商自己已经证明了

**直接证据（来自 OpenAI 自己的官方文档）**：`decisions-voice` 指南教开发者用 Decisions API 做**路由**，选项中显式包含一个 `reason` 分支：

> 「Choose a matching slide action that is available in the current state. **Otherwise, choose `reason`.**」
> 「For `reason`, call the **Responses API with a reasoning model**, passing the original request and relevant context.」

这是最干净的设计逻辑表述：**决策模型是通向 System 2 的看门人，而不是 System 2 的替代品。** OpenAI 是唯一同时握有两条产品线的厂商，它的做法是让 System 1 决定「这次要不要花 System 2 的钱」。

**互补在架构上的三个落点**（均为社区/厂商已实现的模式）：
- **置信度门禁**：高置信直接执行、中段升到强模型、低段转人工（Jev 文档的 `Confidence` 页与 OpenRouter cookbook 的「Jev-Verified Cascade」）。
- **每步护栏**：对 agent 的每一个工具调用做判定（OpenRouter 的「Gate Agent Tool Calls」、LangChain 的 AutoMode 中间件、Perplexity/Cloudflare 的同类用法）。成本差距是数量级的：一个社区 demo 报告同一段 agent 监控用 Jev 花 $2.94，用前沿 LLM 花 $372。
- **混合 agent**：AWS 官方把它写成了战略表述——「support the development of 'hybrid agents' in which a dedicated decision engine lets the decision model handle selections while an LLM handles complex reasoning」。

**同时要承认互斥的部分**：在「只是想要低延迟且不需要校准概率」的场景，模式切换（路线 B）确实可以替代独立决策模型，且不用多接一家供应商。反过来，在需要精确排序、海量并发、或要把概率阈值写进业务代码的场景，路线 B 给不出东西。**腾讯技术工程的实测文章给出的边界判断比较公允：大模型厂商用结构化输出 + 低延迟模型 + 蒸馏「只要做到够好够便宜」，独立决策模型的空间就会受压；但在「需要通用语义理解、候选集频繁变化、又不想为每个小判断单独训练」的夹缝里，这一类模型有真实位置。**

---

## 四、战略表态与时间线

### 4.1 明确的战略表态

| 时间 | 主体 | 原文 | 来源类型 |
|---|---|---|---|
| 2026-09-29 | **Sam Altman（OpenAI CEO）** | 「By focusing the model on that choice, we can make it extremely fast while keeping capabilities like image understanding, broad language support, and safety protections.」 | 【官方发布会，经 TechCrunch 转述】 |
| 2026-09-29 | Sam Altman | 承认用独立模型监控 agent 恶行会产生「**significant compute cost**」 | 【同上】 |
| 2026-10-06 | **@OpenAIDevs（官方账号）** | 「Let your app choose the right model, tool, or action in near real-time with Decisions API, now available to all developers in public beta. The Decisions API makes decisions **up to 10x faster than GPT-6 Luna through the Responses API**.」 | 【官方 X】 |
| 2026-09-30 前后 | **Diogo Almeida（TypeSafe CEO）** | 在 X 上开玩笑称「**the start of the clone wars**」；并称 OpenAI 的兴趣可能是「a sign…that building in a **System One compatible way is the future**」 | 【媒体转述 X】 |
| 2026-09 下旬 | Diogo Almeida（接受 TechCrunch 采访） | 「**Fast and cheap is very easy, you know. If you want it really fast and cheap, use dice, right?** Intelligence is the hard part, and my North Star is always pushing the intelligence-per-dollar Pareto curve.」 | 【媒体采访】 |
| 2026-10-01 | **Strands Labs / AWS（官方博客）** | 承认该类模型「significantly worse at solving complex problems than reasoning models」；同时判断「this class of model is going to lead to a lot of interesting innovation ... over the next few weeks, months, and years」 | 【官方博客】 |
| 2026-10-06 | **AWS Builder Center（AWS 员工）** | 「The first reaction from many engineers was 'isn't this just a classifier?' It's a fair question. Almost every part of a decision model existed before 2026 ... So what did Jev change? **Not the parts, but the contract.**」 | 【官方平台，署名 AWS 员工】 |
| 2026-09-30 前后 | **Armin Ronacher（Earendil CTO）** | 该设计「**delegates the hallucination problem a little bit to the user**」，用户得自己决定 50% 的概率值不值得行动；并认为模型路由是另一个好落点 | 【媒体采访】 |
| 2026-10-06 | **Ethan Kam（前 OpenAI）** | 「We've been testing the Decisions API for over a week. One of the coolest things was how many use cases the team found that **just weren't practical before**.」 | 【个人 X】 |

**公开质疑 / 反方意见**：
- Hacker News 上有讨论串题为「**Jev Can't Be Calibrated**」（正文未能抓取，仅确认标题存在）。
- InfoQ 收录的一条 HN 评论：「Jev 不能输出非法类型，但它仍然可以输出一个**完全错误的合法值**」；并质疑「不能幻觉」的说法与速度对比的公平性。
- TypeSafe 自己的 `jev-1.13 jaggedness` 页面（官方）主动记录了不可靠的计数、算术、日期比较，以及大而嘈杂输入下的准确率下降，建议把数学留在代码里。
- **未查到** Anthropic 或 Google 任何高管对 Jev / System One 的公开评价——既没有跟进表态，也没有质疑表态。

### 4.2 时间线（2026-09-15 起）

| 日期 | 事件 | 来源类型 |
|---|---|---|
| **2026-09-15** | TypeSafe AI 发布 **Jev**，定义 System One 模型；三原语 Choice / Score / Noul；训练法 RLCD；`/v1/systemone` | 【官方 + 媒体】 |
| 2026-09-16/17 | Vercel AI Gateway 接入 Jev（「day two」），官方称 24 小时内触达近 13% 付费团队 | 【媒体引 Vercel】 |
| 2026-09-17 | 社区用 Jev vs Claude Fable 5.1 下快棋，Jev 因对手超时获胜（该媒体自认「证明不了什么」） | 【社区/厂商博客】 |
| 2026-09-19/20 | 第三方分析预测「Anthropic 会在数月内跟进 Jev 型技术」，理由是 Dario Amodei 的 ASI 加速担忧与 Jev「不推高前沿能力却扩大经济收益」的性质吻合 | 【第三方分析，非 Anthropic 表态】 |
| 2026-09-23 | Jev 完成《宝可梦 红》（Claude Opus 5 在幕后改选项与描述，474 次 harness 修改） | 【社区 + 媒体】 |
| 2026-09-24 | OrcaRouter 将 Jev 1.13 加入目录 | 【厂商博客】 |
| **2026-09-29** | **OpenAI DevDay 2026（旧金山）**：Altman 发布 **Decisions API**（有限预览，`gpt-6-luna`）；同场还有 GPT-6.1 Sol、Codex Security Cloud、Ultrafast 档、Agents API 的 Computer Use、dots | 【官方 + 多家媒体】 |
| **2026-09-30** | TechCrunch 报道并定性为「OpenAI's Jev clone」；Almeida 回应「clone wars」同日；**Fastino 发布 GLiDE**（自称「first thinking decision model」，宣称 Decision Index 64.81 vs Jev 57.91） | 【媒体 + 厂商博客】 |
| **2026-10-01** | **同日三家**：Perplexity 开 Decisions API + 开源 `pplx-decider-v1-27b`；Cloudflare 上架 **Clef / Clef-flash**；AWS Strands Labs 开源 **Strands Decider 2B**（Apache-2.0） | 【媒体 + 官方】 |
| 2026-10-05 | AWS Builder Center 出现「AWS Just Open-Sourced a 2B 'Decision Model'」科普文 | 【AWS 平台，个人署名】 |
| **2026-10-06** | **OpenAI Decisions API 转入公开 beta（全体开发者）**；`openai/gpt-6-luna-decisions` 上 OpenRouter（$0.10/$0，1.1M 上下文，p50 0.18s，单请求最多 200 个问题）；AWS Builder Center 发「Decision Models Explained」（AWS 员工署名） | 【官方 X + 官方文档 + 平台】 |
| 2026-10-07 | GIGAZINE 详解 Decisions API 三问型与图像输入 | 【媒体】 |
| 2026-10-08 | Microsoft Learn 的「使用 TypeSafe System One API 查询模型」（Azure Databricks）页面最后更新 | 【官方文档】 |
| 2026-10-09 前后 | BlockBeats 报道 Perplexity 开源 27B 决策模型、自测综合分略超 Jev | 【媒体】 |

**没有发生的事（同样重要）**：截至 2026-10-10，**Anthropic、Google、Cohere、AI21 都没有任何 System One 相关发布**；Anthropic 与 Google 也没有任何高管就该品类公开表态。

---

## 五、明确没有跟进的厂商（附检索依据）

| 厂商 | 判断 | 检索依据 |
|---|---|---|
| **Anthropic** | **确认无独立决策模型产品线** | ① Claude Platform Docs 只有 Structured outputs（JSON outputs + strict tool use）与 extended thinking（`budget_tokens`），无 decisions 端点、无概率分布字段；② claude.com/blog 在 2026-09-24 ~ 10-01 的条目全是 Claude Code mods / Claude for Government / plugins / Tag connectors，无决策模型；③ 结构化输出 2025-11 首发、2026-02-04 GA，与 2026-09 的 Jev 无因果关系；④ 未查到任何高管表态 |
| **Google** | **确认无独立决策模型；路线是 thinking level** | ① 官方文档（Gemini API + Gemini Enterprise Agent Platform）只有 `thinking_level` / `thinkingBudget`，无 decisions 端点；② `MINIMAL` 档的官方描述就是「fewest possible tokens」；③ Gemini 3 系停返 logprobs（开发者论坛答复 intended behavior），Gemini 2.5 于 2026-10 退场；④ 未查到任何高管表态 |
| **Cohere** | **确认无 System One 产品；只有较老的 Classify** | ① `docs.cohere.com/v1/reference/classify` 仍是 few-shot 分类契约（每标签≥2 示例、≤2500 示例、单次≤96 输入）；② Classify 的最近一次实质变更来自 2024-09-26 的 v2 API 改版；③ 2026 年最新官方博客是 Command A+，与决策模型无关；④ 未查到任何相关表态 |
| **AI21** | **确认无对应产品** | ① 未检索到任何 AI21 决策模型/System One 相关内容；② 2026 年该公司公开主线是并购（Nvidia $2–3B 谈崩 → 与 Nebius 接触）与既有 Jamba / Jurassic / AI21 Studio 的延续 |

**顺带说明**：任务线索里「Anthropic 只有 Structured Outputs / tool use 等构件」「Google 是 thinking budget / 结构化输出」「AI21 无对应产品」「Cohere 有较老的 Classify API」**四条均被核实为准确**。真正的增量是：**Google 的情况比线索描述更值得注意**——它不只是「有思考预算」，而是**同时失去了概率输出通道**。

---

## 六、未查到项

1. **OpenAI 的 Decisions API 是否使用了单独训练/微调的 checkpoint**。官方只说「gpt-6-luna is the only model currently available」，未说明是纯 serving 约束还是另有微调。【推断】从 Altman「focusing the model on that choice」的措辞看更像前者，但**无官方确认**。
2. **OpenAI 官方博客形式的「决策 vs 生成」理论论述**。未查到。官方只有产品文档（`/api/docs/guides/decisions`）与 DevDay 一句口头表述；`openai.com/index/devday-2026-recap` 页面本身是 JS 渲染，正文未取到 Decisions 段落。
3. **Anthropic 对 Jev / System One 的任何公开表态**（跟进或质疑）。未查到。
4. **Google 对 Jev / System One 的任何公开表态**。未查到。
5. **Google 官方对「不再返回 logprobs」的原文**。只能通过第三方博客转引 Google 开发者论坛帖子（discuss.ai.google.dev 主题 176557），原帖未直接取到。
6. **Jev 的上下文长度存在互相矛盾的口径**：OpenRouter 模型页写 32,000 tokens；TypeSafe 相关文档被引为「每请求 64K」；OrcaRouter 的模型卡写 65,536。**未解决**，引用时需谨慎。
7. **Strands Decider 2B 的版本号矛盾**：Strands 官方博客称发布的是 v19；SiliconANGLE / DigitalToday 报道为 v.20。**未解决**。
8. **Hacker News「Jev Can't Be Calibrated」讨论串正文**未能抓取（仅确认标题存在），因此无法评估其具体论据。
9. **Preplexity 基准数字的独立复现**。85.71% vs 84.51% 全部来自 Perplexity 自测，cellcog.ai 指出其文档未公布基准表。**属厂商自报**。
10. **Jev 发布后是否有人公开质疑并得到 TypeSafe 正式回应**。只查到零散的 HN/博客质疑与 TypeSafe 自己的 jaggedness 页面，**未查到正式的书面回应**。

---

## 附录：噪音排除记录

| 被排除来源 | 排除理由 |
|---|---|
| `github.com/bakiabaci/awesome-jev`（自称「7,400+ Typed Decision Models」雷达） | 数字无法验证，内容大量 SEO 化（把「System One」与 Instructor/Outlines 对比的表格数字无出处），未作为证据使用 |
| `github.com/stefanwebb/meta-awesome-jev`（「Awesome List of Awesome Jev Lists」） | 明确的元玩笑仓库，非事实来源 |
| `huggingface.co/blog/karmen-beatapi/i-raised-my-jev-score-with-made-up-beta-data` | 标题即声明「用我编的 beta 数据把 Jev 分数从 59 提到 87」，是讽刺帖子 |
| `goldie.agency/jev-seo` | SEO 内容营销，把 Jev 与网站排名强绑，无事实价值 |
| `orcarouter.ai` Jev vs Claude Fable 5.1 | 模型路由厂商自营博客，行文含大量自家产品推广；仅取其**日期**（2026-09-24 上架）与**第三方测试引用**（Every 的 25 倍/1÷580 数据），不采信其自家性能口径 |
| CSDN / 腾讯云开发者社区转载文 | 二手聚合，且部分含 2025 年的旧文混入搜索结果；仅用于交叉验证，不作为一手来源 |
| `app.hncompanion.com/item?id=49816899` | 抓取只返回导航栏，正文不可用，仅记录标题 |
| 各类 AI 聚合站的「AI Weekly / explainx」转述 | 仅用于定位一手 URL；事实以一手页面为准 |

**口径纪律提醒**：TypeSafe 的 **70–500ms、快 20–200 倍、便宜 40–400 倍、最佳情形 193.6 倍** 全部为厂商自报。目前唯一可查的独立测试（Every，12 段合成文本）给出的是**约 25 倍快、约 1/580 成本**，且准确率上 Jev 抓到 7 个植入缺陷中的 6 个，Claude Fable 5.1 抓到 7 个。引用时请用后者。
