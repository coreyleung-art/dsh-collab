# 全模型生态知识库 · A+B 阶段落链回报（data/blueprint/model-ecosystem-kb）

> 数据调查员 4787d717 · 2026-08-24 · 用户指示：全模型厂商技术说明+论文落链

## 本轮落链（11 篇，KB paper-cache，eco- 前缀）
| 厂商/系 | arXiv ID | 说明 |
|---------|----------|------|
| OpenAI | 2303.08774 | GPT-4 技术报告 |
| OpenAI | 2410.21276 | GPT-4o System Card |
| DeepSeek | 2405.04434 | DeepSeek-V2 |
| DeepSeek | 2412.19437 | DeepSeek-V3（168 chunks） |
| DeepSeek | 2501.12948 | DeepSeek-R1（此前已落） |
| Meta | 2407.21783 | Llama-3 |
| Mistral | 2310.06825 | Mistral-7B |
| Alibaba | 2412.15115 | Qwen2.5 |
| Google | 2403.05530 | Gemini-1.5 |
| 上游 | 1706.03762 | Transformer（Attention 奠基） |
| 对齐 | 1707.06347 | PPO |
| Scaling | 2001.08361 | Scaling Laws |

## 检索验证（实测）
- 'GPT-4 system card' → eco-2303.08774 (0.992) ✅
- 'DeepSeek R1' → 2501.12948 (1.000) ✅
- 'RLHF' → 2403.07691 (1.000) ✅

## 待补（C 阶段 + 非 arXiv）
- Claude 3/3.5 model card：官网 PDF 直链失效（CDN 路径变），待补网页抓取或新链接
- 厂商官方 blog/系统卡：GPT-4o 已 arXiv 版覆盖；其余非 arXiv 报告按需网页抓取
- C 上下游（量化/蒸馏/推理/安全）多数已覆盖（LLM.int8/GPTQ/CoT/DPO 等此前已落）

## 基因库同步
- kb-genebank-watch 常驻自动同步（KB 新增即入基因库）
