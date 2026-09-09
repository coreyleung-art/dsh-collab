# 本地模型新版本 / 更高效模型评估 · 算力优化周报②（2026W35）

> 调研日期：2026-08-18 ｜ 目标机：mac-mini M4 + LM Studio(1234) + Ollama(11434)
> 现装模型（本机实测目录）：Qwen3.5-2B-GGUF(1.8G)、Qwen3.5-9B-GGUF(6.1G)、GLM-4.6V-Flash-MLX-4bit(6.6G)、Gemma-4-E4B-it-MLX-4bit(6.4G)、MiniCPM5-1B(656M)、Gemma-4-12B-it-QAT-GGUF(6.7G)、Qwen3.6-27B / Qwen3.8-27B(16~17G)、olmOCR-2-7B；Ollama 有 bge-m3、gemma4:e4b、nomic-embed-text、qwen:1.8b。
> 预算敏感：多 agents 网络优先本地模型省钱，M4 内存是硬约束。

## 本周结论（推荐模型 / 路由建议）

1. **Qwen3.5 小模型系是当前 0.5B–9B 性价比首选**：0.8B/2B/4B/9B（2026-03 发布，Apache 2.0，262K 上下文、原生多模态、thinking 混合）。人工分析 Intelligence Index：9B=32（<10B 最强）、4B=27（<5B 最强）、2B=16（≈Falcon-H1R-7B，超过 Nemotron Nano 9B V2）、0.8B=9。Q4 内存约 9B≈6GB / 4B≈3GB / 2B、0.8B<2GB。**本机已有的 Qwen3.5-2B 与 9B 值得保留，缺的 4B 是工具调用甜点位，建议补一个 Qwen3.5-4B（Q4，~3GB）。**
2. **工具调用（agent 任务）小模型已够用**：Qwen3-4B-Instruct-2507 是 2026 上半年 sub-7B 的 BFCL v4 第一（高 80 分档）；Gemma 4 E4B（4B dense、Apache 2.0、原生 function-call 特殊 token）紧随其后，且工具调用输出 token 少 15–20%。微调后两者差距收窄约 70%，都可达 95%+ 联合准确率。
3. **中文 + 多模态单独留 GLM-4.6V-Flash（9B VL，本地 MLX-4bit 已装）**；纯文本任务不要用它，它是多模态/截图/视觉 agent 档。
4. **MiniCPM5-1B（2026-05）是 1B 级黑马**：1B 类开源 SOTA（均值 42.57 vs 同档 35.61），agentic 工具使用、代码、竞赛数学突出，本机仅 656M——意图识别/标签/格式化/嵌入兜底首选。
5. **路由建议**：默认 80% 请求走 Qwen3.5-2B / MiniCPM5-1B；工具调用走 Qwen3.5-4B 或 Gemma4-E4B；多模态走 GLM-4.6V-Flash；复杂推理/代码/长文升级到 Qwen3.5-9B 或 27B MoE（或 API 兜底）。规则路由优先，语义路由（RouteLLM 思路）做第二层。

## 候选模型评估表

| 模型（版本时点） | 参数 | 量化/体积 | 内存占用* | 强项 | 适合任务 | 来源 |
|---|---|---|---|---|---|---|
| Qwen3.5-9B（2026-03） | 9B dense | GGUF Q4≈6GB（本机 6.1G） | ~8–9GB | <10B 最强智能（IQ32）；MMMU-Pro 69.2%；原生多模态+262K ctx | 复杂推理/代码/长文；小模型兜底升级档 | AA 文章；HF 官方 collection |
| Qwen3.5-4B（2026-03） | 4B dense | Q4≈3GB | ~4–5GB | <5B 最强（IQ27）；工具调用强先验；MMMU-Pro 65.4% | 单轮/并行工具调用、agent 副脑、中等推理 | AA 文章；Ertas 对比 |
| Qwen3.5-2B（2026-03，本机已装） | 2B dense | GGUF 1.8G（≈Q4/Q5） | ~2.5–3GB | IQ16≈7B 级（Falcon-H1R-7B）；多模态 | 意图识别/简单问答/格式化/标签/摘要 | AA 文章；HF 官方 |
| Qwen3.5-0.8B（2026-03） | 0.8B dense | Q4<1.5GB | ~1.5–2GB | 极省内存；仍原生多模态 | 高频低价值子任务、预过滤、嵌入兜底 | AA 文章 |
| Qwen3-4B-Instruct-2507 | 4B dense | Q4_K_M≈2.5–3GB | ~3.5–4.5GB | BFCL v4 sub-7B 第一（高 80s）；并行函数调用强 | 纯工具调用/agent 基座（微调后 95%+） | Ertas 2026-04/05；D-Central BFCL |
| Gemma 4 E4B（2026-04） | 4B dense | Q4≈3.2GB（本机 MLX-4bit 6.4G†） | ~4–5GB | 原生 function-call token（输出少 15–20%）；BFCL 中高 80s；Apache 2.0；32K ctx | 工具调用/chat/coding；格式稳定性要求高的 agent | gemma4.dev；Ertas |
| Gemma 4 26B A4B | 26B MoE/4B active | Q4≈16.4GB | ~20GB+ | 128K 长上下文；能力接近 13B+ dense、算力≈4B | 长文 RAG、技术写作（内存 ≥32G 才考虑） | gemma4.dev |
| GLM-4.6V-Flash（2025-12，本机已装） | 9B VL | MLX-4bit 6.6G | ~7–9GB | 中文多模态/截图理解/视觉 agent；8GB 显存可跑 | 截图转网页、搜图购物、视觉问答 | 智谱官方；bianews；CSDN 实测 |
| MiniCPM5-1B（2026-05，本机已装） | 1B dense | 656M（4bit） | ~1–1.5GB | 1B 类 SOTA（均值 42.57）；agentic 工具/代码/竞赛数学；hybrid reasoning | 意图识别/标签/格式化/轻工具调用/嵌入 | OpenBMB GitHub |
| Qwen3.6-27B / Qwen3.8-27B（本机已装） | 27B（A3B 系列） | GGUF 16–17G | ~20GB+ | 大模型能力档 | 仅内存充足时作为「大模型」档；**M4 高压下建议卸载** | 本机目录（版本信息待官方核对） |

*内存 ≈ 权重文件 ×1.2~1.5（含 KV cache 与运行时开销，按 4–16K ctx 估算）。†本机 MLX-4bit 6.4G 明显大于理论 Q4 3.2G，可能是含视觉/更大变体，待实测确认。

## 任务→模型路由表

| 任务类别 | 最小达标模型 | 说明 |
|---|---|---|
| 意图识别 / 标签 / 实体抽取 / 格式化 / JSON 结构化 | Qwen3.5-0.8B~2B 或 MiniCPM5-1B | 结构化输出 + schema 校验/约束解码兜底；1B 即可 |
| 简单问答 / 短文本摘要 / 改写 / 分类 | Qwen3.5-2B | 质量敏感可升 Gemma4-E4B |
| 单轮 / 并行工具调用 | Qwen3.5-4B 或 Gemma4-E4B 或 Qwen3-4B-2507 | BFCL 高 80s；微调后 95%+；Gemma4 输出更省 token |
| 多轮复杂 agent（需要规划、状态管理） | Qwen3.5-9B 起步，复杂场景上 27B MoE 或 API | 小模型推理链短、幻觉率高（4B/9B AA-Omniscience 幻觉 80%+） |
| 中文多模态 / 截图理解 | GLM-4.6V-Flash | 文本任务别用，浪费内存 |
| 代码生成 / 调试 / 复杂推理 | Qwen3.5-9B 起步；高难上 27B/API | 代码建议 Q5_K_M/Q6 保质量 |
| 长文 / 多跳 RAG / 128K 级上下文 | Gemma4 26B-A4B（需 32G+）或 API | 小模型只做局部抽取，不做全局推理 |
| 嵌入（RAG 检索） | bge-m3（已装，Ollama） | 与 LLM 分开，保持常驻，内存占用小 |

## 量化对比

| 量化 | 困惑度损失（vs FP16） | 7B 文件/速度 | 结论 |
|---|---|---|---|
| Q8_0 | +0.03%（近无损） | 7.0GB / 25 t/s | 精度敏感（代码/数学）用 |
| Q6_K | +0.13% | 5.5GB / 30 t/s | 质量/体积最佳折中 |
| Q5_K_M | +0.39% | 4.8GB / 35 t/s | 有多余内存时优先 |
| **Q4_K_M** | **+1.68%** | **4.1GB / 40 t/s** | **内存高压首选（推荐）** |
| Q3_K_M | +6.07% | 3.3GB / 45 t/s | 仅小模型/极端省内存 |
| Q2_K | +15.3% | 2.7GB / 50 t/s | 不推荐（质量崩） |

补充要点（2026 实测/官方资料）：
- **MLX 4bit vs GGUF Q4_K_M**（Apple Silicon）：MLX 吞吐高 15–40%；GGUF Q4_K_M 因层内混合精度质量略优（MMLU 损失 0.4–0.8 vs 0.6–1.2 分）；>30B 模型两者差距 <1%。→ LM Studio 上 **MLX 4bit 优先**（省内存+快），GGUF Q4_K_M 用于 Ollama/跨平台。
- **QAT 模型**：官方 QAT 训练过的权重在低位宽损失更小（Gemma 3/4 官方 QAT GGUF 已常见）。同模型有官方 QAT 时优先于普通量化。本机 Gemma-4-12B-it-QAT-GGUF 属此类，值得实测。
- **内存公式**：实际占用 ≈ 权重文件 ×1.2~1.5（KV cache 随 ctx 增长）；8K→32K ctx 内存显著上升，M4 高压下把 ctx 压在 8–16K。
- 量化有 imatrix（重要性矩阵）可再降 10–20% 困惑度，Q3 以下必用；domain 校准数据（代码/中文）效果更好。

## 落地建议（M4 内存高压配置）

1. **常驻两件套**：Qwen3.5-2B（Q4，~1.8G）做默认文本任务 + bge-m3（Ollama）做嵌入。合计 <3GB，其余留给系统与 agents 网络。
2. **按需加载**：工具调用场景临时加载 Qwen3.5-4B 或 Gemma4-E4B（~3–6GB）；多模态才加载 GLM-4.6V-Flash（~7GB）；**卸载/不装 27B 与 35B 大文件（16–17G）**，或仅在夜间批处理时用。
3. **服务端调优**：Ollama `keep_alive=5m`（不长期驻留大模型）；LM Studio 限制 GPU offload、单模型内存上限；ctx 压到 8–16K；启用 KV cache 量化（如 Q8/Q4 KV）省 30–50% 缓存内存。
4. **路由层（本周可落地）**：octoroute（Rust，Ollama/LM Studio/llama.cpp 统一网关，规则+LLM 路由、健康检查、负载均衡）或自写 OpenAI 兼容代理（LM Studio :1234 + Ollama :11434 都兼容 /v1）。第一层规则路由（任务类型→模型），第二层可加嵌入相似度阈值（RouteLLM 思路），失败自动升级到大模型。
5. **成本账（本地 vs API，估算）**：
   - 本地边际成本 ≈ 电费 + 硬件折旧。M4 mini 推理平均 ~10–30W，1M token 电费约 ¥0.01–0.1；含 5 年折旧（¥4–5k 机器），重度使用下 1M token 综合成本约 ¥0.5–2，且不随用量上涨。
   - API：GLM-4.5-Flash 有免费层/极低价、Qwen-Turbo 约 ¥0.3/M in + ¥1.2/M out 档位，GPT/Claude 类 ¥20–150/M。
   - 结论：**高量、格式固定、延迟不敏感的任务走本地（2B/4B 足够）；复杂推理/代码/长文用 API 兜底**——本地省的是「便宜模型也能干」的那部分，不是省大模型能力。

## 证据来源

| 来源 | 时点 | 可信度 | 要点 |
|---|---|---|---|
| [Artificial Analysis：Qwen3.5 small models](https://artificialanalysis.ai/articles/qwen3-5-small-models) | 2026-03-05 | 高（独立评测机构） | 0.8–9B 四档 IQ 指数、MMMU-Pro、4bit 内存、幻觉弱点 |
| [HF：Qwen3.5 发布帖](https://huggingface.co/posts/sergiopaniego/211066152403082) | 2026-03 | 高（官方） | 262K ctx、原生多模态、thinking 混合、Apache 2.0 |
| [Ertas AI：端侧工具调用 2026（Qwen3-4B vs Gemma4 E4B vs Phi-4-Mini）](https://www.ertas.ai/blog/on-device-tool-calling-2026-qwen3-gemma4-phi4) | 2026-04/05 | 中高（合成公开基准，作者声明示意区间） | BFCL v4 档位、延迟、微调后 95%+、Gemma4 token 节省 |
| [D-Central：Local LLM Agent-Capability（BFCL 2026）](https://d-central.tech/local-llm-agent-capability/) | 2026 年中 | 中高 | Qwen 占 BFCL 约 10/13 席；重 agent 任务 GLM-4.5/4.6、Kimi K2.6 领先 |
| [gemma4.dev Model Reference](https://gemma4.dev/docs/models) | 2026 | 高（官方系） | E2B/E4B/26B-A4B/31B 规格、Q4 VRAM、用途 |
| [OpenBMB MiniCPM GitHub](https://github.com/OpenBMB/MiniCPM) | 2026-05-19 发布 | 高（官方） | MiniCPM5-1B 1B 类 SOTA 42.57，agentic 强项 |
| [GGUF Quantization Guide（firecrawl/huggingface skills）](https://github.com/firecrawl/ai-research-skills/blob/main/12-inference-serving/llama-cpp/references/quantization.md) | 2026 | 高（llama.cpp 系） | Q2–Q8 困惑度/体积/速度表、imatrix |
| [Contra Collective：GGUF vs MLX on Apple Silicon](https://contracollective.com/blog/gguf-vs-mlx-quantization-formats-apple-silicon-2026) | 2026 | 中高（实测对比） | MLX 快 15–40%、GGUF 质量略优、量化差异 |
| [LMSYS RouteLLM 博客](https://lmsys.org/blog/2024-07-01-routellm/) | 2024-07（方法论仍有效） | 高（学术） | 矩阵分解路由：MT-Bench 省 85% 成本、保 95% GPT-4 质量 |
| [octoroute（GitHub）](https://github.com/slb350/octoroute) | 2026 | 中（新项目，待实测） | Ollama/LM Studio/llama.cpp 统一路由网关 |
| [bianews：GLM-4.6V 开源报道](https://www.bianews.com/news/details?id=226897) | 2025-12-09 | 中高 | GLM-4.6V=106B-A12B，Flash=9B 本地版 |
| 智谱官方文档（GLM-4.6V-Flash 免费模型） | 2026 | 高（官方） | 免费层/VL 能力（页面过大未全文抓取） |

噪音排除记录：Tripo AI 赞助类页面（toolify）、标题党「马斯克大赞」类转载（36kr/hk01，仅作背景不采信数值）、本机未注明的 Qwen3.6/3.8-27B 文件名（非官方命名，未纳入推荐表）。

## 置信度与待实测

- **高置信**：Qwen3.5 四档规格与 IQ（官方+AA 双源）；Gemma4 变体规格（官方）；MiniCPM5-1B 定位（官方）；GGUF 量化相对差异（llama.cpp 系指南）。
- **中置信**：BFCL 档位与「Qwen 领先」结论（多源一致但数字是区间）；MLX vs GGUF 的 15–40% 速度差（第三方单源）。
- **低置信/待实测**：
  1. M4 mini 上各模型的真实 t/s、峰值内存（需跑 llama.cpp/mlx benchmark，量化档各测 10 次）；
  2. Qwen3.5-2B/9B 本机 GGUF 的具体量化（Q4/Q5/Q6）与质量差异；
  3. Gemma-4-E4B-it-MLX-4bit 体积 6.4G 与官方 Q4 3.2G 不符的原因（是否含视觉权重/更大变体）；
  4. Ollama 库中 Qwen3.5 各档的确切 tag 与是否官方支持（本机 Ollama 暂无 qwen3.5 tag，需 `ollama pull` 前确认）；
  5. 语义路由（嵌入阈值）在本机任务分布上的准确率与误路由率；
  6. GLM-4.6V-Flash 在纯文本 agent 任务上的性价比（预期不如 Qwen3.5-4B，待验证）。
