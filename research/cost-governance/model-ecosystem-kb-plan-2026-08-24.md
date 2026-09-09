# 全模型生态知识库建设方案 v1.0

> 2026-08-24 · 协调者 · 用户指示：调研所有大模型厂商技术说明+论文+上下游论文，拉到本地链

## 一、目标
建立覆盖「全部主流大模型厂商」的本地知识库（可检索、可落链、支撑提案依据）

## 二、覆盖范围

### A. 厂商技术说明（官方报告/blog——非 arXiv，需抓取）
| 厂商 | 技术说明 |
|---|---|
| OpenAI | GPT-4/4o/o1/o3 系统卡 + 技术报告 |
| Anthropic | Claude 3/3.5/4 系统卡 + Constitutional AI blog |
| Google | Gemini 1.5/2.0 技术报告 + PaLM/PaLM2 |
| DeepSeek | V2/V3/R1 技术报告（本地优先——自家核心） |
| Meta | Llama 2/3/3.1 论文 + 系统说明 |
| Mistral | Mixtral/Mistral 7B 技术报告 |
| Qwen | Qwen2.5/Qwen-VL 技术报告 |
| 其他 | xAI Grok / Cohere / 阿里千问 / 百度文心 等（可选） |

### B. 厂商系核心论文（arXiv）
- Transformer/Attention（上游奠基）
- RLHF/DPO/PPO/InstructGPT（对齐系列）
- 各厂商标志性论文（GPT-3/4、Claude、Gemini、Llama、DeepSeek-Math/R1 等）

### C. 上下游论文
- 算力：推理优化(vLLM/TensorRT)、训练并行、量化(INT8/FP8)、蒸馏
- 数据：合成数据、数据治理、scaling law
- 推理：CoT、测试时扩展(Test-Time Compute)、思维树
- 部署：模型服务、边缘部署
- 安全：红队、对齐、越狱防御

## 三、执行方式（4787d717 数据调查员）
1. 厂商技术说明：web 抓取官方报告 → 存 paper-cache/reports/ → 抽取文本 → 入库向量化
2. arXiv 论文：走既有论文管道（download→extract→KB）
3. 落链：KB paper-cache + 基因库自动同步（kb-genebank-watch 已常驻）
4. 分阶段：先 A 厂商技术说明 + B 核心论文（高优先），再 C 上下游

## 四、产出
- KB paper-cache（厂商系文档/论文向量化）
- 基因库（PDF/报告内容寻址）
- 检索验证：knowledge_search 'GPT-4' / 'DeepSeek R1' / 'RLHF' 命中

## 五、成本治理
- 遵守：定时默认不启用，按指令推进；礼貌限速抓取
- 复用：既有论文管道 + kb-genebank-sync 自动同步
