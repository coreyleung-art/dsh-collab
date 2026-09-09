# 第一份算力优化周报 —— 节省 token 的方法/工具清单（2026-W34）

> 调研日期：2026-08-17（ISO 2026-W34）｜调研对象：DSH 多会话 agent 网络 + Claude Code + LM Studio/Ollama 本地模型
> 调研方法：12+10 次中英文 web_search + 官方文档抓取交叉验证（Anthropic/OpenAI/微软 LLMLingua/llama.cpp/Ollama/Claude Code 官方文档为主，第三方教程佐证）
> 标注约定：**【官方】**=厂商一手数据；**【实测/论文】**=有论文或实测支撑；**【宣称】**=项目宣传口径，未独立复现；**【估算】**=基于常见工作负载的工程估算，无权威数据。

## 本周结论

1. **缓存是性价比最高的第一杠杆（官方数据，优先级最高）**。Anthropic 官方文档：prompt caching 命中部分按基础输入价的 **10%（省 90%）** 计费，写入部分 5 分钟 TTL 时 **+25%**、1 小时 TTL 时 **+100%**；官方口径「多数组织输入成本下降 50–90%」。OpenAI 侧为自动缓存（≥1024 token 前缀），缓存输入约 **5 折**。本地（llama.cpp/Ollama）同样有 KV cache 前缀复用 + KV 量化（Q8_0 省 **50%** KV 内存），LM Studio/Ollama 直接可配。
2. **提示压缩能削 token，但有保真与二次开销权衡**。微软 LLMLingua 系列官方 README：最高 **20x** 压缩率；LongLLMLingua 在 1M token 场景 prefill 延迟降 **10x**；LLMLingua-2 比初代快 3–6x。适合「一次性注入的长文档/RAG 填充」，不适合高频交互与精确数字任务（压缩器本身也要花 token/算力）。
3. **工程侧优化空间大且零风险**：系统提示精简、工具输出截断、结构化输出、批量 API（**50% 折扣**）、语义缓存、RAG 替代长上下文。Claude Code 官方文档展示了启动即占大量上下文的构成（CLAUDE.md、memory、技能描述、MCP 工具名），并有 /compact、/autocompact 阈值配置。
4. **量化/蒸馏是本地省钱主路径**：GGUF Q4/Q8 相对 FP16 权重内存降约 75%/50%；蒸馏小模型（如 Qwen3-0.6B 系列）把「简单任务」从大模型分流，API 单价低一个数量级或本地吞吐高数倍。**注意**：Q4 与极小模型有质量损失，需按任务评估（下周主题）。

## 技巧清单表

| 类别 | 技巧 | 原理 | 预期节省 | 适用场景 | 来源 |
|---|---|---|---|---|---|
| 提示压缩 | LLMLingua 系列 prompt 压缩 | 小模型对 prompt 做 token 级压缩后喂给大模型，保留关键信息 | 最高 **20x** 压缩；1M token prefill 延迟降 **10x**【官方 README/论文】 | 一次性长文档注入、RAG 上下文填充、离线批处理 | [LLMLingua README](https://raw.githubusercontent.com/microsoft/LLMLingua/main/README.md)、[LongLLMLingua](https://llmlingua.com/longllmlingua.html) |
| 提示压缩 | 系统提示精简（删冗余/合并技能描述） | 固定前缀按每次调用计费；精简直接线性降输入 token | 常见 10–40% 输入 token【估算】；Claude 官方曾砍系统提示 80%【媒体报道】 | 所有 agent 会话、DSH 多会话网络、Claude Code 的 CLAUDE.md | [ifanr：Opus 5 系统提示砍 80%](https://www.ifanr.com/1673165)、[Claude Code context-window](https://code.claude.com/docs/en/context-window) |
| 提示压缩 | 工具输出裁剪/截断（token budget、行数/字节上限、只回摘要） | 工具结果常占上下文大头；截断后仅保留决策所需片段 | 上下文占用降 30–70%【估算，取决于工具使用模式】 | agent 循环中的 bash/grep/read、DSH 消息传递 | [AgentScope Context Compaction](https://java.agentscope.io/v2/en/docs/harness/compaction.html) |
| 上下文缓存 | Anthropic prompt caching（cache_control / 自动缓存） | 相同前缀命中缓存：读按 10% 基础价、写 +25%（5min TTL）或 +100%（1h TTL） | 输入成本降 **50–90%**【官方口径，需高前缀复用】 | Claude API 多轮 agent 会话、固定系统提示+工具定义 | [Anthropic 官方文档](https://docs.claude.com/en/docs/build-with-claude/prompt-caching) |
| 上下文缓存 | OpenAI 自动 prompt caching | ≥1024 token 前缀自动缓存，缓存输入约 5 折，无需手动标记 | 缓存部分输入省约 **50%**【官方+社区交叉验证】 | OpenAI API 多轮 chat、长固定前缀 | [OpenAI 官方](https://openai.com/index/api-prompt-caching/)、[DO 教程](https://www.digitalocean.com/community/tutorials/prompt-caching-cost-break-even) |
| 上下文缓存 | 本地 KV cache 复用（llama.cpp/Ollama） | 相同前缀复用 KV 状态跳过重复 prefill；KV 可量化 | Q8_0 KV 省 **50%** RAM/VRAM【官方 PR】；前缀复用 TTFT 大幅下降（社区实测 9.9x） | LM Studio/Ollama 多轮、多 agent 共享同一本地服务 | [llama.cpp PR#2969](https://github.com/ggml-org/llama.cpp/pull/2969)、[Ollama PR#6279](https://github.com/ollama/ollama/pull/6279)、[llama.cpp 讨论](https://github.com/ggml-org/llama.cpp/discussions/14556) |
| 上下文缓存 | 会话 compact（Claude Code /compact、/autocompact；DSH 会话压缩） | 长会话压缩为结构化摘要+元数据，释放上下文 | 上下文占用降 90%+（只剩摘要）但丢失细节【官方机制】 | 会话接近上限时主动触发；切换无关任务用 /clear | [Claude Code context-window](https://code.claude.com/docs/en/context-window)；DSH 机制**待实测** |
| 量化 | GGUF Q4/Q8、AWQ 权重量化 | 低比特存储权重，内存/带宽下降；Q4 约 4.5 bit/权重 | Q4 权重内存降约 **75%**、Q8 约 **50%**（相对 FP16）【估算+厂商文档】 | 本地推理、更大上下文/并发、显存受限机器 | [GGUF vs AWQ vs GPTQ](https://intelligibberish.com/articles/which-quantization-gguf-awq-gptq-mlx/)、[量化详解](https://www.generalcompute.com/blog/quantization-explained-int4-gguf-gptq) |
| 蒸馏/小模型 | 同任务用更小模型（Qwen3-0.6B/蒸馏系、Haiku/Flash 级） | 小模型单价低/本地推理快；蒸馏保留大模型部分能力 | API 单价低 5–20x（按型号）【估算】；本地吞吐高数倍 | 分类、抽取、格式化、路由筛选等非复杂推理 | [HF 蒸馏模型](https://huggingface.co/reaperdoesntknow/Qwen3-0.6B-Distilled-30B-A3B-Thinking-SFT-GGUF) |
| 工程 | 结构化输出（JSON schema、CFG/grammar 约束） | 约束解码避免冗长自由文本与解析重试 | 输出 token 降 20–60%【估算】 | 机器解析结果、工具调用参数 | [tokenless](https://github.com/tokenfleet-ai/tokenless)（宣称 60–90%，**待验证**）、TASS |
| 工程 | 批量 API（Batch） | 24h 内异步处理，官方 50% 折扣 | **50%** 成本【官方】 | 日报/周报生成、批量摘要、离线分析 | [batchata](https://github.com/agamm/batchata)（聚合 50%）、Anthropic/OpenAI Batch 官方文档 |
| 工程 | 语义缓存（GPTCache 等） | 相似问题命中缓存直接返回，不调 LLM | 命中时该次 100% 省；项目宣称成本 **10x** 降【宣称，依赖命中率】 | 重复查询高的客服/检索/固定报表 | [GPTCache README](https://raw.githubusercontent.com/zilliztech/GPTCache/main/README.md) |
| 工程 | RAG 代替长上下文 | 只注入检索命中片段而非全文 | 输入 token 常降 1–2 个数量级（视库大小）【估算】；引入检索误差 | 大知识库问答、长期记忆、跨会话知识 | [Elastic: RAG vs long context](https://www.elastic.co/search-labs/blog/rag-vs-long-context-model-llm)、[Hivenet](https://www.hivenet.com/post/long-context-vs-rag) |
| 工程 | 去重/请求合并 | 相同请求合并、任务批量合并（一次工具调用返回多结果） | 减少重复 prefill 与轮次数【估算】 | agent 网络内部消息合并、重复查询去重（DSH agent bus 已有 10 分钟去重） | [llmfleet](https://github.com/MukundaKatta/llmfleet)、DSH 本地机制 |

## 工具清单

| 名称 | 类型 | 省 token 原理 | 适用场景 | 成本影响 | 来源 |
|---|---|---|---|---|---|
| LLMLingua / LongLLMLingua（pypi: llmlingua） | prompt 压缩库 | 小模型压缩 prompt/KV，最高 20x | 长文档注入、RAG 填充、离线批处理 | token 大降，但增加压缩器开销 | [官方 README](https://raw.githubusercontent.com/microsoft/LLMLingua/main/README.md) |
| Prompt-Compression-Benchmarker | 压缩方案评测 | 对实际负载打分 token 节省/质量 | 选型前对比 LLMLingua/Selective-Context 等 | 帮助决策 | [GitHub](https://github.com/dakshjain-1616/Prompt-Compression-Benchmarker) |
| Anthropic prompt caching（cache_control / 自动缓存） | API 缓存 | 前缀命中读按 10% 计价 | Claude API 多轮会话、固定系统提示 | 输入省 50–90%【官方】 | [官方文档](https://docs.claude.com/en/docs/build-with-claude/prompt-caching) |
| OpenAI prompt caching | API 缓存 | ≥1024 token 前缀自动缓存，约 5 折 | OpenAI API 多轮 | 缓存输入省约 50% | [官方](https://openai.com/index/api-prompt-caching/) |
| LiteLLM / langchain anthropicPromptCachingMiddleware | 接入层 | 自动加 cache_control 断点 | 代码接入 Claude 缓存 | 简化启用 | [langchain middleware](https://reference.langchain.com/javascript/langchain/index/anthropicPromptCachingMiddleware) |
| llama.cpp（llama-server：KV q8_0、prefix reuse、context shift） | 本地推理引擎 | 前缀复用 + KV 量化 | LM Studio/Ollama 后端、多请求共享前缀 | KV 内存省 50%；TTFT 大降 | [PR#2969](https://github.com/ggml-org/llama.cpp/pull/2969)、[讨论#14556](https://github.com/ggml-org/llama.cpp/discussions/14556) |
| Ollama KV 量化（OLLAMA_KV_CACHE_TYPE=q8_0） | 本地推理配置 | KV cache 量化 | 本地长上下文 | 省 50% VRAM，无可见质量损失【官方 PR 口径】 | [PR#6279](https://github.com/ollama/ollama/pull/6279) |
| vLLM Automatic Prefix Caching | 服务端缓存 | 服务端前缀缓存跳过重复 prefill | 高并发本地部署 | 吞吐↑、单位 token 成本↓ | [vLLM 文档](https://docs.vllm.ai/) |
| GPTCache | 语义缓存 | 相似 query 直接返回缓存结果 | 重复查询高的服务 | 宣称成本 10x 降【宣称】 | [README](https://raw.githubusercontent.com/zilliztech/GPTCache/main/README.md) |
| Claude Code /compact、/autocompact、/clear | 会话管理 | 压缩为结构化摘要；设自动压缩阈值（如 /autocompact 500k） | Claude Code 长会话 | 释放上下文、省后续输入 | [context-window 文档](https://code.claude.com/docs/en/context-window) |
| DSH 会话 compact/clear（平台内置） | 会话管理 | 长会话压缩/清空，机制与 Claude Code 类似 | DSH 多会话网络 | **待实测量化** | 本地平台（未见独立实现源码） |
| llama.cpp quantize / Ollama / LM Studio GGUF Q4/Q8 | 量化工具链 | 低比特权重 | 本地模型部署 | 内存降 50–75% | [quantization 指南](https://www.generalcompute.com/blog/quantization-explained-int4-gguf-gptq) |
| AutoAWQ / ExLlamaV2（AWQ） | 量化工具链 | AWQ 激活感知量化 | 本地/边缘部署 | 类似 Q4 级内存降 | [intelligibberish 对比](https://intelligibberish.com/articles/which-quantization-gguf-awq-gptq-mlx/) |
| Anthropic / OpenAI Batch API | 批量接口 | 异步 24h 处理 5 折 | 日报、批量摘要 | 50% 成本 | [batchata](https://github.com/agamm/batchata) |
| Dify 知识库（检索调参：top-k、rerank、引用策略） | RAG 平台 | 只注入命中片段；检索参数影响注入量 | 知识问答、长期记忆 | 输入 token 数量级下降（案例称 32%） | [Dify 文档](https://docs.dify.ai/en/cloud/use-dify/knowledge/create-knowledge/setting-indexing-methods) |
| 结构化输出：JSON mode / llama.cpp grammar / Outlines / Instructor | 输出约束 | 约束解码减少冗长输出与重试 | 机器解析、工具参数 | 输出 token 降 20–60%【估算】 | [TASS](https://zenodo.org/records/20467618) |
| 模型路由：liteLLM / OpenRouter / DSH 预设按任务选模型 | 路由层 | 简单任务走小模型 | 多模型混合网络 | 单价差 5–20x | 行业实践 |

## 对我方 agent 网络的可落地建议（按优先级）

**P0 —— 本周立即做（零成本或低改动）**

1. **给 Claude 侧会话启用/验证 prompt caching**：把 CLAUDE.md、工具定义、技能描述、固定系统提示作为稳定前缀，多轮保持一致（不把易变内容插在前缀前部）；优先用 Anthropic 自动缓存，复杂场景用 cache_control 断点。预期输入成本降 50–90%（官方口径，前提是复用率高）。落地动作：抽查一个高频 agent 会话的 usage 字段，统计 cache_read_input_tokens 占比。
2. **工具输出裁剪基线**：为 bash/grep/read 等设 token budget（建议单次 ≤2000 token；超长输出落盘+行号引用；只回摘要/diff）；DSH 跨 agent 消息同步截断。Claude Code 官方文档显示工具/文件读入是上下文大头，收益直接。
3. **本地模型开 KV 量化与前缀复用**：LM Studio/Ollama 设置 KV cache q8_0（OLLAMA_KV_CACHE_TYPE=q8_0）；让多个 agent 共享同一本地服务实例并复用固定前缀（系统提示/工具 schema 放前面）。预期 KV 内存省 50%、长上下文吞吐提升。
4. **系统提示精简审计**：用 token 计数对每个 agent preset 的 system prompt 建基线，砍冗余；技能描述控制在 Claude Code 官方上限（5000 token/技能、25000 总）内，未用的技能不进上下文。
5. **批量任务走 Batch**：日报/周报/离线摘要等 24h 可容忍任务改用 Batch API（50% 折扣）。

**P1 —— 下周推进**

6. **语义缓存/去重层**：对高频查询（状态查询、知识库检索）加 GPTCache 或自建 embedding 相似缓存；先测 1–2 周命中率，>30% 才值得投入。
7. **模型路由**：简单任务（分类、抽取、格式化、消息路由）分流到 Qwen3-0.6B/蒸馏小模型或 Haiku/Flash 级；复杂推理保留大模型。本地 0.6B 足够跑分类/摘要初筛。
8. **长文档 RAG 化**：把常驻长文档从系统提示移入 Dify/Chroma 检索，控制 top-k 与 rerank，避免全文注入。
9. **量化 A/B 基线**：LM Studio 对常用模型做 Q4_K_M vs Q8 vs FP16 的质量-成本对比（衔接下周「模型评估」主题）。

## 证据来源

| 来源 | 类型 | 采信点 |
|---|---|---|
| [Anthropic Prompt Caching 官方文档](https://docs.claude.com/en/docs/build-with-claude/prompt-caching) | 官方一手 | cache read=10%、write=+25%（5min）/2x（1h）；自动缓存；多数组织输入成本降 50–90% |
| [OpenAI Prompt Caching 官方页](https://openai.com/index/api-prompt-caching/) | 官方一手 | 自动缓存、≥1024 token 前缀（页面 403 未能抓取，数字经 DO 教程+社区帖交叉验证） |
| [DigitalOcean 缓存盈亏分析](https://www.digitalocean.com/community/tutorials/prompt-caching-cost-break-even) | 权威第三方 | Anthropic 费率表（0.10x 读/1.25x 或 2.0x 写/1024 下限）、OpenAI 缓存非自动、1024 下限 |
| [LLMLingua 官方 README](https://raw.githubusercontent.com/microsoft/LLMLingua/main/README.md) | 官方一手/论文 | 最高 20x 压缩、1M token prefill 延迟降 10x、LLMLingua-2 快 3–6x |
| [llama.cpp PR#2969（KV q8_0）](https://github.com/ggml-org/llama.cpp/pull/2969) | 官方仓库 | KV 量化 q8_0 省 50% RAM/VRAM |
| [Ollama PR#6279（KV 量化）](https://github.com/ollama/ollama/pull/6279) | 官方仓库 | Q8_0 KV 省 50% VRAM，无可见质量损失 |
| [Claude Code Context Window 文档](https://code.claude.com/docs/en/context-window) | 官方一手 | /compact 摘要化、/autocompact 阈值、技能体量上限、启动上下文构成 |
| [llama.cpp 讨论#14556（KV 复用）](https://github.com/ggml-org/llama.cpp/discussions/14556) | 社区实测 | 前缀复用 TTFT 大幅下降（案例 9.9x） |
| [GPTCache README](https://raw.githubusercontent.com/zilliztech/GPTCache/main/README.md) | 项目宣传 | 语义缓存、宣称 10x 成本/100x 延迟（营销口径） |
| [Elastic: RAG vs long context](https://www.elastic.co/search-labs/blog/rag-vs-long-context-model-llm) | 权威博客 | RAG 与长上下文取舍 |
| [tokenless](https://github.com/tokenfleet-ai/tokenless) | 新项目（低可信） | 宣称 60–90% 削减，待验证 |

**噪音排除记录**：callsphere 等 SEO 站对 LLMLingua 的「4–20x」数字与官方 README 一致才采用；crazyrouter 抓取超时弃用；openai.com 403 未直接抓取，改用官方 URL+DO 教程+OpenAI 社区帖（「Half-Priced Prompt Caching」）交叉验证；GPTCache「10x/100x」与 tokenless「60–90%」为宣传口径，标注待验证。

**局限与待验证**：① OpenAI 缓存 50% 数字未能直接抓取官方页（403），为官方页+社区+DO 三方交叉，置信度中高；② DSH 会话 compact 机制未在本机源码中找到独立实现，标注待实测；③ 「工具输出截断 30–70%」「结构化输出 20–60%」等为工程估算，无权威基准；④ 各项节省量级高度依赖工作负载（复用率、工具使用密度、任务复杂度），落地后应以 1–2 周真实 usage 数据校准。

## 下周预告（模型评估）

- **目标**：产出「每任务最低成本达标模型」路由表。
- **方法**：建本地评估集（摘要/抽取/分类/工具调用 4 类 × 20 例，含参考答案），在 LM Studio/Ollama 上对比 Qwen3-0.6B / 3B / 14B 及蒸馏模型在 FP16 / Q8 / Q4_K_M 下的质量-成本-延迟曲线；同时抽样对比 Claude Haiku/Flash 级 API 与本地模型的性价比拐点。
- **产出**：评估脚本+数据集沉淀到 `compute-optimization/eval/`；路由规则写回 DSH agent preset；量化选择建议（哪些任务可接受 Q4，哪些必须 Q8+）。
