# 模型路由表 v1（草案 · 跨设备）

> 编制：算力优化调研子代理 · 2026-08-18 · 依据：PC-i9 4 模型登记 + mac-mini 2 模型基线（规则判分，summary 待 LLM-judge）
> 口径：规则判分平均（可判子集）；「标签」= 分类标签格式/口径差异，宽容匹配后可提升

## 路由决策

| 任务类型 | 首选 | 备选 | 避开 | 理由 |
|---|---|---|---|---|
| 结构化抽取 extraction | **qwen2.5:7b @ PC-i9** | mistral:7b / llama3.1:8b | qwen3.5-2b（thinking，预算耗尽无 JSON） | PC-i9 全 1.0；mac-mini 非思考模型亦可 |
| 工具调用 tool_call | **qwen2.5:7b @ PC-i9** | deepseek-r1:8b（≥2048）/ meta-llama-3-8b | **llama3.1:8b**（拒单被拒） | qwen2.5 全 1.0；r1 2048 后全 1.0 但开销大 |
| 摘要 summary | qwen2.5:7b / deepseek-r1:8b（待 judge） | qwen3.5-2b（质量尚可） | — | 均待 LLM-judge 定论 |
| 分类 classification | 待统一标签集后复测 | deepseek-r1:8b（「服务投诉/产品咨询」最接近统一标签） | llama3.1:8b（拒绝行为）/ 直接子串判分 | 4 模型标签格式各异，需宽容匹配或 constrained decoding |
| 复杂/推理任务 | deepseek-r1:8b @ PC-i9（≥2048） | — | — | 思考型适合推理，接受开销 |
| 视觉/OCR | glm-4.6v-flash / olmocr-2-7b（mac-mini，待 OCR 场景） | — | — | 未纳入本次文本评估 |

## 跨设备吞吐参考（per10k token 秒，越低越快）

| 模型 | PC-i9 GPU | mac-mini M4 |
|---|---|---|
| qwen2.5:7b | ~200–280 | —（本机无此模型） |
| llama 家族 8B | ~242–1475 | 584–1286（llama3-8b-instruct） |
| qwen3.5-2b | — | ~200–280（分类短输出除外） |
| deepseek-r1:8b | ~203–521 | — |

结论：结构化高频任务优先 PC-i9（GPU）；小模型分流（0.6B/3B）待 W35 拉取后补充；短输出任务（分类）延迟主导，路由时以单请求延迟为决策维度。

## 待办

- [x] LLM-judge 补判 summary（12 条 = 6 模型 × 2；全部 4/5，1 条解析失败待重判）→ results/llm-judge-and-classification-retest.md
- [x] 分类统一标签集复测（宽容上限 0.83，受 verbose 污染；待 constrained decoding 转正式）
- [ ] 0.6B/3B 小模型双端拉取后补充路由表
- [x] 路由规则回写 DSH agent preset（task-env-map v1.3 已联动）

---
*模型路由表 v1 草案 · 2026-08-18 · 算力优化调研子代理*
