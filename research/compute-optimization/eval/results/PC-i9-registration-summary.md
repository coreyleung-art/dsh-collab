# PC-i9 模型登记汇总（4 模型 × 8 例）

> 执行：算力优化调研子代理远程直跑（endpoint http://100.118.15.71:11434/v1，run_eval.py v0.2，2026-08-18）
> 规则判分口径：extraction/tool_call 为 JSON 合法+关键字段；classification 为答案子串匹配；summary 主观项待 LLM-judge（不计入平均）

## 汇总

| 模型 | 规则判分平均 | 可判 | extraction | tool_call | classification | 备注 |
|---|---|---|---|---|---|---|
| qwen2.5:7b | **0.833** | 6/8 | 1.0 / 1.0 | 1.0 / 1.0 | 0.0（口径）/ 1.0 | 全任务最稳，结构化全过 |
| mistral:7b | 0.667 | 6/8 | 1.0 / 1.0 | 1.0 / 1.0 | 0.0 / 0.0 | 分类输出英文标签/解释性文本，格式不稳 |
| llama3.1:8b | 0.500 | 6/8 | 1.0 / 1.0 | 1.0 / 0.0（拒绝） | 0.0（口径）/ 0.0 | tool-02 直接拒绝生成拒单工具调用 |
| deepseek-r1:8b | 0.500 | 6/8 | 0.0（空输出）/ 1.0 | 1.0 / 0.0（空输出） | 0.0 / 1.0 | 思考模型：2 条空 content（1024 max_tokens 仍耗尽） |

## 原始 CSV

- eval/results/pc-i9-qwen2.5-7b.csv（全量明细见 PC-i9-qwen2.5-7b-report.md）
- eval/results/pc-i9-mistral-7b.csv
- eval/results/pc-i9-llama3.1-8b.csv
- eval/results/pc-i9-deepseek-r1-8b.csv

## 关键观察

1. **qwen2.5:7b 是当前 PC-i9 上结构化任务最优**（ext/tool 全 1.0）；分类类别的两个 0 分均为标签口径（「投诉」vs「投诉/催单」），LLM-judge 宽容匹配后可达 0.83–1.0
2. **llama3.1:8b 的拒绝行为**（tool-02）值得关注：对「拒绝订单」类动作生成了安全拒答，若任务需要此类动作输出，需换模型或加系统提示
3. **deepseek-r1:8b 思考开销**：1024 max_tokens 下仍有空 content 输出；结构化任务建议 max_tokens 2048+ 或改用非思考模型
4. **classification 标签稳定性**：4 个模型标签格式各不相同（投诉/Customer_Complaint/服务投诉/生活服务）——路由表阶段建议统一标签集 + 宽容匹配，或将分类任务改用受限输出（constrained decoding）
5. 吞吐参考（per10k 秒）：qwen2.5:7b ~200–280（分类类短输出 ~1000+ 为延迟主导）；路由决策需延迟+吞吐同看

## deepseek-r1:8b 复测（max_tokens 2048，2026-08-18）

- 复测范围：extraction × 2 + tool_call × 2（原空输出/低分样本）
- 结果：**4/4 全 1.0**（ext-01 1.0 / ext-02 1.0 / tool-01 1.0 / tool-02 1.0）
- 结论：空 content 确系 1024 max_tokens 截断；deepseek-r1:8b 结构化能力本身稳定，但思考开销大（如 ext-01：35.5s / 1745 completion tokens），路由表建议「推理型模型给足 max_tokens（≥2048）或用于复杂推理任务，结构化高频任务优先 qwen2.5:7b」
- CSV：eval/results/pc-i9-deepseek-r1-8b-mt2048.csv

## 路由表草案要点（待 mac-mini 基线合入）

1. tool_call 场景避开 llama3.1:8b（拒单调用被拒）
2. classification 统一标签集 + 宽容匹配（或 constrained decoding）；deepseek-r1 输出「服务投诉/产品咨询」格式最接近统一标签
3. 结构化高频任务首选 qwen2.5:7b（0.833，ext/tool 全 1.0）；复杂/需推理任务考虑 deepseek-r1:8b（2048 tokens）
4. 视觉/OCR 模型（llava/glm-ocr/moondream）留待 OCR 场景单独评估

## 下一步

- [ ] LLM-judge 补判 8 条 summary + 分类宽容匹配复判
- [ ] 统一标签集复测 classification（或加 constrained decoding 选项）
- [x] deepseek-r1:8b 提高 max_tokens 复测（2048，4/4 通过）
- [ ] 汇总路由表 v1（含 mac-mini 侧基线）

---
*PC-i9 模型登记汇总 · 2026-08-18 · 算力优化调研子代理*
