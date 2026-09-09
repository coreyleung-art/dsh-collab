# 模型考古清单 · LM Studio 清理（2026-08-29）

> 生成：2026-08-29 · HR session-2a15e6b1 · 工具：pre-delete-archaeology.py v1.0 + 人工补全
> 用途：删除前考古留档——记录曾有哪些模型/为何删/如需恢复从哪重下
> 删除对象：9 个弃用模型（89.4GB）· 保留 6 个刚需（46.4GB）
> 原则：模型均为开源 GGUF/MLX 可重下，删除不丢失能力；本清单为可追溯恢复依据

---

## 🗑️ 删除清单（9 个 · 89.4GB）

### 1. Qwen3.6-27B-GGUF（lmstudio-community）
- 大小：17.5GB（Q4_K_M + mmproj）
- 来源：LM Studio Hub / HuggingFace lmstudio-community
- 判定理由：**旧版重复**——已有新版 Qwen3.8-27B（17.7G）覆盖同档能力
- 重下渠道：https://huggingface.co/lmstudio-community/Qwen3.6-27B-GGUF

### 2. Qwen3.6-35B-A3B-Uncensored（HauhauCS）
- 大小：15.9GB（Q2_K_P）
- 来源：HuggingFace HauhauCS
- 判定理由：**特化非刚需**——uncensored 特化版，日常任务无此需求；且 Q2 量化质量低
- 重下渠道：https://huggingface.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive

### 3. Mixtral-8x7B-Instruct-v0.1（TheBloke）
- 大小：15.6GB（Q2_K）
- 来源：HuggingFace TheBloke（已归档，官方迁移 unsloth）
- 判定理由：**能力重复**——Qwen3.8-27B 已覆盖其 MOE 能力；Q2 量化质量低
- 重下渠道：https://huggingface.co/unsloth/Mixtral-8x7B-Instruct-v0.1-GGUF

### 4. OrionStar-Yi-34B-Chat（TheBloke）
- 大小：15.0GB（Q3_K_S）
- 来源：HuggingFace TheBloke
- 判定理由：**能力重复**——Yi-34B 被 Qwen3.8-27B 全面覆盖，无独有优势
- 重下渠道：https://huggingface.co/TheBloke/OrionStar-Yi-34B-Chat-Llama-GGUF

### 5. Ternary-Bonsai-27B-mlx-2bit（prism-ml）
- 大小：8.5GB（safetensors MLX）
- 来源：HuggingFace prism-ml
- 判定理由：**实验归档**——MLX 2bit 实验模型，2bit 量化质量不可用；MLX 实验已止损归档（2026-08-22 决策）
- 重下渠道：https://huggingface.co/prism-ml/Ternary-Bonsai-27B-mlx-2bit

### 6. gemma-4-E4B-it-MLX-4bit（lmstudio-community）
- 大小：6.9GB（MLX 4bit）
- 来源：LM Studio Hub
- 判定理由：**能力重复**——E4B 小模型被 Qwen3.5-2B 覆盖（轻量档只需一个）
- 重下渠道：https://huggingface.co/lmstudio-community/gemma-4-E4B-it-MLX-4bit

### 7. Meta-Llama-3-8B-Instruct（lmstudio-community）
- 大小：4.9GB（Q4_K_M）
- 来源：LM Studio Hub / HuggingFace
- 判定理由：**能力重复**——Llama-3-8B 被 Qwen3.5-9B/Qwen3.5-2B 覆盖
- 重下渠道：https://huggingface.co/lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF

### 8. Mistral-7B-Instruct-v0.3（lmstudio-community）
- 大小：4.4GB（Q4_K_M）
- 来源：LM Studio Hub
- 判定理由：**能力重复**——Mistral-7B 被 Qwen 系列覆盖
- 重下渠道：https://huggingface.co/lmstudio-community/Mistral-7B-Instruct-v0.3-GGUF

### 9. MiniCPM5-1B（saidutta69）
- 大小：0.7GB（Q4_K_M）
- 来源：HuggingFace saidutta69
- 判定理由：**测试用**——1B 特化模型，仅测试价值
- 重下渠道：https://huggingface.co/saidutta69/MiniCPM5-1B-Claude-Opus-Fable5-V2-Thinking-heretic

---

## ✅ 保留清单（6 个 · 46.4GB）

| 模型 | 大小 | 用途 |
|---|---|---|
| Qwen3.8-27B-GGUF | 17.7G | 主力通用推理（27B 档唯一） |
| gemma-4-12B-it-QAT | 7.2G | 轻量主力推理 |
| GLM-4.6V-Flash-MLX | 7.1G | 视觉理解（i9 无法跑 MLX） |
| Qwen3.5-9B-GGUF | 6.5G | 中量级通用 |
| olmOCR-2-7B | 6.0G | OCR（刚需） |
| Qwen3.5-2B-GGUF | 1.9G | 轻量快速 |

---

## 📁 同步清理：LM Studio 旧日志（19.5GB）

| 目录 | 大小 | 判定 |
|---|---|---|
| server-logs/2026-04 | 9.7G | 旧日志（噪音主导，无考古价值） |
| server-logs/2026-05 | 9.8G | 旧日志（噪音主导，无考古价值） |

---

*考古清单 v1.0 · HR 2a15e6b1 · 2026-08-29 · 删除后可追溯恢复*
