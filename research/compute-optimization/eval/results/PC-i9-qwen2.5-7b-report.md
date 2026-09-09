# PC-i9 模型评估结果（qwen2.5:7b / 4060 Ti · 全量 8 例）

> 执行：算力优化调研子代理远程直跑（2026-08-18，endpoint http://100.118.15.71:11434/v1，run_eval.py v0.2 sha256 0d914c82，eval-set.json 08f0fb1d，max_tokens 768）
> 结果：✅ 8/8 跑通｜规则判分平均 **0.833**（6/8 可判）｜2 条 summary 待 LLM-judge
> 精确 CSV：eval/results/pc-i9-results.csv（UTF-8，13 列，含 raw 输出）

## 全量明细

| 样本 | 类别 | score | tok/s | per10k 秒 | 备注 |
|---|---|---|---|---|---|
| sum-01 | summary | 待 judge | 45.1 | 221.9 | 摘要结构完整 |
| sum-02 | summary | 待 judge | 36.6 | 273.5 | 摘要结构完整 |
| ext-01 | extraction | 1.0 | 49.0 | 204.1 | JSON 围栏容忍生效 |
| ext-02 | extraction | 1.0 | 47.9 | 208.8 | JSON 围栏容忍生效 |
| cls-01 | classification | 0.0 | 7.1 | 1413.1 | 输出「投诉」，答案「投诉/催单」——标签口径问题（宽容匹配后可判对） |
| cls-02 | classification | 1.0 | 9.9 | 1012.0 | 输出「餐饮咨询」 |
| tool-01 | tool_call | 1.0 | 36.1 | 277.2 | PriceChecker JSON 正确 |
| tool-02 | tool_call | 1.0 | 39.9 | 250.5 | reject_orders JSON 正确 |

## 观察

1. 结构化任务（extraction/tool_call）全 1.0，qwen2.5:7b 在 4060 Ti 上表现稳定；JSON 围栏容忍让 ```json 输出正常判分
2. classification tok/s 偏低（7–10）属短输出+首 token 延迟主导，per10k 口径会放大——路由表阶段需同时看延迟与吞吐
3. cls-01 为标签口径差异而非能力失败：LLM-judge 阶段将宽容匹配或统一标签集（「投诉」⊆「投诉/催单」）
4. 对比 mac-mini qwen3.5-2b（51.7 tok/s 但 thinking 模型 content 为空）：结构化任务建议优先 qwen2.5:7b 类非思考模型

## 待办

- [x] PC-i9 全量跑测（qwen2.5:7b）
- [ ] 其余模型登记（mistral:7b / llama3.1:8b / deepseek-r1:8b 等，同一脚本）
- [ ] LLM-judge 补判 2 条 summary + 标签宽容匹配
- [ ] 汇总路由表 v1

---
*PC-i9 全量结果 · 2026-08-18 · 算力优化调研子代理*
