# mac-mini 模型基线（LM Studio / M4）

> 执行：算力优化调研子代理本机直跑（endpoint http://127.0.0.1:1234/v1，run_eval.py v0.2，2026-08-18）
> 规则判分口径同 PC-i9；summary 主观项待 LLM-judge（不计平均）

## 结果

| 模型 | 规则判分平均 | 可判 | extraction | tool_call | classification | 备注 |
|---|---|---|---|---|---|---|
| meta-llama-3-8b-instruct | 0.667 | 6/8 | 1.0 / 1.0 | 1.0 / 1.0 | 0.0（标签）/ 0.0 | ext/tool 稳；分类标签格式化差；吞吐 8–17 tok/s（CPU） |
| qwen3.5-2b（thinking） | 0.500 | 6/8 | 0.0 / 0.0 | 1.0 / 1.0 | 0.0 / 1.0 | 思考模型：extraction 思考耗尽预算无最终 JSON；summary 质量尚可；吞吐 44–51 tok/s |

## 原始 CSV

- eval/results/macmini-llama3-8b-instruct.csv
- eval/results/macmini-qwen3.5-2b.csv

## 观察

1. **qwen3.5-2b（thinking 模式）不适合 extraction**：2048 max_tokens 下 2 条 extraction 均无最终 JSON（reasoning 占满预算）；tool_call 反而正常出 JSON
2. **meta-llama-3-8b-instruct（非思考）结构化稳**：ext/tool 全 1.0，与 PC-i9 llama3.1:8b 表现一致；分类同为标签格式问题
3. 吞吐：M4 CPU 侧 8–17 tok/s（llama3-8b）vs 44–51 tok/s（qwen3.5-2b 小模型）；PC-i9 GPU 侧 36–54 tok/s——同模型/同类任务 GPU 优势明显
4. 视觉/OCR 模型（glm-4.6v-flash / olmocr-2-7b 等）留待 OCR 场景

---
*mac-mini 模型基线 · 2026-08-18 · 算力优化调研子代理*
