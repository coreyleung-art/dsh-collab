# 本系统本地模型选型 v1.0 · 决策文档

> 起草：2026-08-19 · HR · 研究性决策（J40：论文/评测支撑）· 承接 model-eval-weekly-2026W35（通用评测）+ 本次专项调研
> 目标：外卖运营/CAHAC 系统（A4 PoC 5 场景 + 嵌入/OCR + 未来补单/竞对/垂直引擎）在本设备的模型选型

---

## 一、设备与现有资产（实测）

**Mac mini M4/24G**（宿主）：
- LM Studio(1234) 实装 11 模型：qwen3.5-2b · qwen3.8-27b · gemma-4-12b-qat · minicpm5-1b · qwen3.6-35b-a3b · glm-4.6v-flash · olmocr-2-7b · mixtral-8x7b · yi-34b · llama-3-8b · nomic-embed-v1.5
- Ollama(11434)：bge-m3（嵌入）等 4 模型
- **分工（J35 判定）**：Ollama=嵌入，LM Studio=推理

**PC-i9（32G/RTX 4060 Ti，Windows）**：Ollama 原生可用（不依赖 Docker）——CUDA 推理节点（8-14B 量化）

## 二、任务分层 → 模型映射（专项选型）

| A4 场景/任务 | 推荐模型 | 已装？ | 内存 | 理由 |
|---|---|---|---|---|
| 消息分类（ACK/STATUS/TASK...） | **minicpm5-1b** 或 qwen3.5-2b | ✅ 已装 | 1.5-3G | 高频可错；MiniCPM5-1B=1B 级 SOTA（意图/标签） |
| 关键词/标签提取 | minicpm5-1b / qwen3.5-2b | ✅ | 1.5-3G | 结构化输出+schema 校验 |
| 短摘要（<500 字） | qwen3.5-2b（质量敏感升 llama-3-8b） | ✅ | 3-6G | 2B 够用，8B 兜底 |
| JSON 结构化提取 | qwen3.5-2b / llama-3-8b | ✅ | 3-6G | schema 校验兜底 |
| 回复/文案草稿（中文） | **llama-3-8b** 或 gemma-4-12b（需复核） | ✅ | 6-9G | 中文质量敏感；复核门控 |
| 工具调用（未来 agent 副脑） | **Qwen3.5-4B（建议下载）** | ❌ 3GB | BFCL sub-7B 第一；工具调用甜点位（周报②结论） |
| 复杂推理/正式产出 | 云端 flash（兜底）或 27B（夜间批量） | — | — | 小模型幻觉率高（4B/9B AA-Omniscience 80%+） |
| 嵌入 | bge-m3（Ollama）/ nomic-embed | ✅ | 1G | 零成本 |
| OCR/截图理解 | olmocr-2-7b / glm-4.6v-flash | ✅ | 7-9G | 中文多模态 |

## 三、内存预算与加载策略（M4 24G 硬约束）

| 策略 | 说明 |
|---|---|
| 同时加载上限 | 常驻 ≤2 个推理模型（1b+2b ≈4.5G 或 2b+8b ≈9G）——避免 24G 高压（周报：27B 建议卸载） |
| 按需加载 | local-router 按场景动态切换模型（minicpm 分类 / llama 草稿） |
| 大模型档 | 27B/35B 移 PC-i9（CUDA）或夜间批量用；M4 日常卸载 |
| 嵌入常驻 | bge-m3 常驻（1G，检索必需） |

## 四、A4 PoC 实测计划（衔接 local-router）

| 周 | 场景 | 模型 |
|---|---|---|
| 第 1 周 | 分类/关键词 | minicpm5-1b + qwen3.5-2b（对比） |
| 第 2 周 | 摘要/JSON/草稿 | qwen3.5-2b + llama-3-8b（对比） |
| 待补 | 工具调用 | Qwen3.5-4B（下载后） |

## 五、决策结论

1. **无需新模型即可启动**：A4 PoC 场景 1-5 全部有已装模型覆盖（1b/2b/8b/12b）
2. **唯一建议下载**：Qwen3.5-4B（3GB，工具调用甜点位，为未来 agent 副脑/补单系统储备）
3. **设备分工**：M4=日常轻量（1b/2b/8b）+嵌入；PC-i9=重推理（9-14B CUDA，Docker 恢复不影响 Ollama）
4. **兜底**：复杂/不可复核 → 云端 flash（模型路由规则 v1.1）
5. **local-router 配置**：endpoint=lmstudio（qwen3.5-2b 已装）；场景 1-2 可切 minicpm5-1b

## 六、论文支撑（J40）

- Multi-Turn RL for Tool-Calling Agents（2604.02869，已入库）——工具调用 agent 的强化训练，支撑 4B 工具调用选型
- 基础：model-eval-weekly-2026W35（Qwen3.5 系 BFCL 评测）+ Local-Splitter（本地路由省 45-79%）

---
*本地模型选型 v1.0 · HR · 2026-08-19 · 设备=M4 24G + PC-i9 · 已装模型优先，唯一建议新增 Qwen3.5-4B*