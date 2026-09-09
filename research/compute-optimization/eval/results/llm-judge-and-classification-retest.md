# LLM-judge + 分类统一标签复测（2026-08-18）

> 执行：算力优化调研子代理｜judge 模型：meta-llama-3-8b-instruct（LM Studio 本机，温度 0）
> 数据源：6 模型 × 8 例 CSV（eval/results/）

## 一、LLM-judge 补判 summary（共 12 条 = 6 模型 × 2 条）

| 模型 | sum-01 | sum-02 | 备注 |
|---|---|---|---|
| qwen2.5:7b | 4 | 4 | 覆盖完整 |
| mistral:7b | 4 | 4 | — |
| llama3.1:8b | 4 | 4 | sum-02 缺 W35 具体任务类别细节 |
| deepseek-r1:8b | 4 | 4 | — |
| mac-llama3-8b | 4 | 4 | — |
| mac-qwen3.5-2b | **解析失败** | 4 | sum-01 输出非 JSON（重判或人工） |

结论：各模型摘要质量接近（4/5 档），**summary 路由可转正式**：首选 qwen2.5:7b@PC-i9（结构化同源），deepseek-r1/llama3 亦可。CSV：eval/results/llm-judge-summaries.csv

## 二、分类统一标签宽容复测（离线，基于已存 raw）

统一标签集：投诉（含 complaint）/ 咨询 / 催单 / 其他

| 模型 | cls-01 | cls-02 | 宽容判分 |
|---|---|---|---|
| qwen2.5:7b | ✅ 投诉 | ✅ 餐饮咨询 | 2/2 |
| mistral:7b | ✅ Customer_Complaint | ❌ 解释性文本 | 1/2 |
| llama3.1:8b | ✅ 投诉 | ❌ 生活服务 | 1/2 |
| deepseek-r1:8b | ✅ 服务投诉 | ✅ 产品咨询 | 2/2 |
| mac-llama3-8b | ✅ 服务投诉 | ⚠️ 生活服务（raw 备注污染误判） | 1-2/2 |
| mac-qwen3.5-2b | ⚠️ CoT 文本含关键词 | ⚠️ CoT 文本含关键词 | 2/2（不可信） |

合计：宽容匹配上限 **10/12 = 0.83**；但 verbose/思考模型输出（CoT 含关键词、解释性文本）会污染判定。

**结论**：统一标签+宽容匹配可显著提升（0.5→0.83 上限），但**可靠落地必须 constrained decoding 或提示词强制标签集**（如「只输出以下之一：投诉/咨询/催单/其他」）；classification 路由维持 provisional，待受限输出复测后转正式。

## 三、路由表更新

- summary：provisional → **正式**（首选 qwen2.5:7b，全部 4/5）
- classification：维持 provisional（宽容 0.83 上限，待 constrained decoding 复测）
- 下一步：80 例正式评估集时同步实现受限输出（llama.cpp grammar / 提示词强制标签集）

---
*LLM-judge + 分类复测 · 2026-08-18 · 算力优化调研子代理*
