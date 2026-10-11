# System One 决策模型 · DSH Preset 设计 v1

> 日期：2026-10-06 · 状态：**设计稿（未实施）**
> 依据：DSH 运行时实际契约（本机读源码核实）+ 我方 R6–R10 实测 + 五条外部调研线程
> 配套：`SystemOne-四方向实证轮-R6R10.md` · `SystemOne-生态扩展与学术谱系-v1.md`

---

## 0. 先说三个结论

| # | 结论 |
|---|---|
| 1 | **可行** —— preset 目录可自带本地插件注册工具，契约已核实（`ctx.tools.register(defineTool({...}))`） |
| 2 | **但不该把 Laya / CLM / opendecider 对等并列** —— 我方的实测与文献证据显示前两者在我们的场景明显更弱 |
| 3 | **这个 preset 的真正价值不是"能调三个模型"，而是"一个能在同一批输入上对照不同后端的测试台"** —— 这正是外部调研里反复缺的东西（社区各测各的，口径不通） |

---

## 1. 可行性核实（本机读源码）

### 1.1 Preset 契约

| 项 | 内容 | 出处 |
|---|---|---|
| 组合文件 | `agent.cordis.yml`（`COMPOSITION_FILE`） | `dsh-agent-presets/lib/types/discovery.d.ts` |
| 元数据文件 | `preset.yml`（`METADATA_FILE`） | `metadata.d.ts` |
| 预设 id | **目录名** | `discovery.d.ts` |
| 用户预设根 | `.agent-presets`（`USER_PRESET_DIR`） | `discovery.d.ts` |
| 热发现 | "Discovery **re-reads the roots on every call** so a preset authored while the process is running is visible **without a restart**" | `discovery.d.ts` |

### 1.2 预设可自带本地插件

现有预设已经这么做了：`liangshen` 有 `./tool-bootstrap.mjs`，`resource-manager` 有 `./model-fallback.mjs`。

**工具注册 API（从 `dsh-tool-todo` 源码读到）**：

```js
ctx.tools.register(defineTool({
  name: "...",
  description: "...",
  parameters: { /* schema */ },
  execute(args, exec) { /* ... */ }
}))
```

`defineTool` 由 `@deepseek-ai/dsh-tools` 导出。

→ **preset 目录内放一个 `.mjs`，即可注册任意工具面。不必开发独立插件包。**

### 1.3 后端可得性（hf-mirror 实测）

| 模型 | HF ID | 可得 | 格式 | 体积 |
|---|---|---|---|---|
| Laya | `convaiinnovations/laya` | ✅ dl=11733 | safetensors | ~1.7 GB |
| Laya GGUF | `ggml-org/Laya-GGUF` | ✅ | **官方 GGUF（BF16/Q8_0）** | ~0.45 GB |
| CLM | `Contrastive-LM/CLM-v0.1-8B` | ✅ dl=3445 | 需查（无 safetensors） | ~8–16 GB |
| CLM GGUF | `czl/CLM-v0.1-8B-GGUF` | ✅ | GGUF | — |
| CLM MLX | `mlx-community/CLM-v0.1-8B-MLX-8bit` | ✅ | MLX 8bit | ~8.5 GB |
| Lev | `interfaze-ai/lev` | ✅ | LoRA adapter | ~0.1 GB + 基座 |
| opendecider | `manjunathshiva/opendecider-nano` | ✅ **已下载并跑通** | safetensors | 0.8 GB |
| opendecider GGUF | `manjunathshiva/opendecider-small-GGUF` | ✅ | GGUF q4/q8 | ~4.3 GB |

> **⚠️ 更正**：我先前报告里写"Laya 的 GGUF 是非标准 ggmlc 格式、Ollama 打不开"——**现已证伪**：`ggml-org/Laya-GGUF` 是官方 ggml-org 发布的标准 GGUF。
>
> **⚠️ 更正**：我先前用 `NandhaKishorM/laya` 查 HF 失败——**GitHub org ≠ HF org**。正确 ID 是 `convaiinnovations/laya`。

---

## 2. 为什么不能"对等并列"（这是设计前提）

三个模型的 **API 完全不同**：

| | Laya | CLM | opendecider |
|---|---|---|---|
| 运行形态 | HF transformers | HF transformers / vLLM | **HTTP `/v1/systemone`** |
| 输入布局 | **选项在前 + 每项 `[MASK]`，状态在后** | 状态与选项**分开编码** | 状态 + 结构化问题 |
| 决策读取点 | `[MASK]` 处的向量 → MLP → softmax | 两 embedding 的**余弦** | 模型内部（推断为提示词末尾） |
| 原语 | 仅 choice | 仅 choice | **choice / noul / score** |
| 选项上限 | 受 token 预算限制（512，**会静默截断**） | 无硬限但精度崩 | 256（HTTP 26） |

**更要紧的是能力差距**（我方实测 + 文献，均为已核实数字）：

| 证据 | Laya | CLM | opendecider |
|---|---|---|---|
| 通用检查点 vs 多数类基线 | **0.362 / 0.342，低于 0.461 基线** | — | 0.796（官方 benchmark） |
| 选项数扩展准确率 | 0.93 → 0.20 | 0.64 → 0.00 | — |
| 最小编辑（否定/数字/角色/量词） | 0.17–0.92 | **0.00–0.08** | — |
| 短标签可分性 | 名称压过描述（72%） | **不可分（余弦 0.95）** | — |
| 我方本机实测 | 未跑 | 未跑 | **跑通：P50 34.5ms，5 次逐位一致** |

> **文献对 CLM 的结论原文**："**CLM is not suited to classifying text into short intent labels.** It fits the task it was designed for: agents choosing among many stable actions, described in longer texts, where caching pays off."
>
> **文献对 Laya 的结论**：通用检查点低于多数类基线；延迟与准确率**从未被接在同一列**。

**因此设计立场**：**架构上支持三者，但默认只启用 opendecider；Laya/CLM 作为"可切换的实验后端"，并在注册表里显式标注其已知限制。**

---

## 3. Preset 目录结构

```
~/.dsh/.agent-presets/systemone/          # ← 目录名即 preset id
├── preset.yml                             # 元数据（name / description / order）
├── agent.cordis.yml                       # 组合：persona + 工具插件 + 上下文
├── systemone-tools.mjs                    # ← 本地插件：统一决策工具面
└── backends.json                          # 后端注册表（含已知限制）
```

**理由**：与现有预设（`liangshen`/`resource-manager`）同构，**无需独立插件包、无需改 DSH 核心**。

---

## 4. 工具面设计（四个工具）

统一的**外观（facade）**吸收三个后端的 API 差异。

| 工具 | 用途 | 返回 |
|---|---|---|
| `systemone_choice` | 从 N 个选项选一个 | 选中项 + 每项概率 + 置信度 |
| `systemone_noul` | 是/否概率判断 | 0–1 概率 |
| `systemone_score` | 有序刻度评分 | `expected`（**可落在刻度之间**）+ 最可能级别 + 分布 |
| `systemone_coverage` | **前置覆盖守卫**（见 §6） | `in_coverage: bool` + 诊断 |

**统一返回结构**：

```json
{
  "answer": "billing",
  "probabilities": { "billing": 0.927, "technical": 0.033, "other": 0.040 },
  "confidence": 0.927,
  "backend": "nano",
  "latency_ms": 34.5,
  "in_coverage": true,
  "truncated": false,
  "warnings": []
}
```

**为什么统一返回结构很重要**：`backend` 字段让**同一批输入可以跨后端对照**——这是测试台价值的技术前提。

---

## 5. 后端注册表设计

```json
{
  "version": 1,
  "backends": {
    "nano": {
      "kind": "opendecider-http",
      "endpoint": "http://127.0.0.1:8010",
      "primitives": ["choice", "noul", "score"],
      "maxOptions": 256,
      "default": true,
      "verified": {
        "by": "本机 R6–R10 实测",
        "deterministic": true,
        "p50_ms": 34.5,
        "batch_3_states_ms": 116,
        "ece_over_noise_floor": 2.03
      }
    },
    "laya": {
      "kind": "hf-transformers",
      "repo": "convaiinnovations/laya",
      "primitives": ["choice"],
      "maxOptions": 20,
      "enabled": false,
      "known_limits": [
        "通用检查点 0.362/0.342，低于多数类基线 0.461",
        "距离敏感：每 100 token 答对几率 ×0.71（p=0.0008）",
        "名称压过描述（误导性名称下跟随名称 72%）",
        "512 token 预算会静默截断，可丢光状态仍返回分布"
      ]
    },
    "clm": {
      "kind": "hf-transformers",
      "repo": "Contrastive-LM/CLM-v0.1-8B",
      "primitives": ["choice"],
      "enabled": false,
      "known_limits": [
        "短标签不可分（不同选项平均余弦 0.95）",
        "最小编辑失败（0.00–0.08，13/24 模板对两段文本给相同答案）",
        "文献结论：不适合把文本分类到短意图标签；适合长文本下的动作选择"
      ]
    }
  }
}
```

**设计要点**：`known_limits` **不是注释，是注册表的一等字段**——它让"为什么这个后端默认关闭"成为可查询的事实，而不是口口相传的默会知识。

---

## 6. 内建守卫与校准（这是增量，不是可选项）

外部调研五条线程的一致结论：**决策模型本身不是难点，难点在"什么时候不该用它"和"阈值怎么定"**。

### 6.1 前置覆盖守卫（我方 R7b 实测方案）

```
sim = max cosine(input, 各选项的代表话语)
if not (sim >= 0.65 AND model_confidence >= 0.4):
    return { in_coverage: false }   # 让上层转 LLM / 人工
```

**实测效果**：越界误放 **0/12**（纯嵌入法会误放 33%）。
**设计原则**：**零误放优先**——被拦下不等于失败，只是升级到更贵的路径；放行一条越界请求去做自动决策才是不可接受。

> ⚠️ **已知改进方向**：外部线程建议用**保形预测**在留出校准集上取分位数来定阈值，而不是像我现在这样拍常数。**这是实施时应优先替换的部分。**

### 6.2 后置分档

按校准后的置信度分档：高 → 自动执行；中 → 标记复核；低 → 转 LLM/人工。

**我方 R9b 实测的分层收益**：规则层 59% + 模型层 12%（门槛 0.5，模型段准确率 100%）= **全链路自动 71%**。

### 6.3 校准（可选，需标注数据）

温度缩放（**16 条标注即可用**）/ Platt（**50 条是下限**）。我方 R8 实测：17 条标注把留出集 ECE 从 0.2416 降到 0.1565。

---

## 7. Persona 设计要点

preset 的 persona 要说清**职责边界**，否则模型会越界去做规划/生成：

> 你是**原子判断器**。你做的是「一个有经验的人一秒能拍板」的单维判断——分类、选择、评分、真伪。
> 你**不做**规划、不写文案、不做多因素权衡、不做算术。
> 你要注意**置信度**：低置信时明确说"我不确定"，让上层决定是否转人工或转给更强的模型。
> 输入越短、选项越多越抽象，你的判断越不可靠——遇到这种情况应主动要求更多上下文。

---

## 8. 与 DSH 其他机制的衔接

| 机制 | 衔接方式 |
|---|---|
| **MCP station** | `opendecider mcp --device mps` 可作为 stdio MCP 挂载（已实测 CLI 存在） |
| **`llm/stream` waterfall** | 未来可实现"三分法调度"：规则短路 / 决策模型短路 / 透传 LLM。**DSH 文档把 "routing" 写进了该事件的用途** |
| **Agent 级模型选择** | `installModelSelection()` / `agentOptions.provider/model`——每个 agent 可指定模型（我方 `agent-bus` 已在使用该机制） |
| **Subagent descriptor** | `agentProvider` / `agentModel` 可持久化，冷恢复保留 |

---

## 9. 实施范围（分三档，未执行）

| 档 | 内容 | 预估 |
|---|---|---|
| **A. 最小可用** | `preset.yml` + `agent.cordis.yml` + `systemone-tools.mjs`（对接已跑通的 opendecider HTTP），单后端 | 小 |
| **B. 测试台** | 加 `backends.json` + Laya/CLM 适配器（HF transformers + 本地 venv），支持跨后端对照 | 中 |
| **C. 生产形态** | 加覆盖守卫 + 校准流水线 + `llm/stream` 三分法路由 | 大 |

**建议顺序**：**A → 用真实数据验收 → 再决定 B**。理由：B 的两个后端（Laya/CLM）按现有证据在我们的场景价值存疑，**先证明 A 有收益，再决定是否投入 B**。

---

## 10. 未解问题（诚实清单）

| # | 问题 |
|---|---|
| 1 | **`Contrastive-LM/CLM-v0.1-8B` 无 safetensors 文件**（6 个文件但无权重）——需确认权重在哪（可能在 GGUF/MLX 仓，或需特定加载方式） |
| 2 | CLM 需 8B 模型 + 自定义 MLP 头 + vLLM 或本地 reader，**集成成本显著高于 Laya** |
| 3 | Laya 的 `[MASK]` 布局与选项在前的要求，需要专用适配器（不能复用通用 prompt 模板） |
| 4 | 24GB 内存下同时驻留多个后端不现实，**需设计按需加载/卸载** |
| 5 | 覆盖守卫的阈值目前是**拍的常数**，应换保形预测（外部线程建议） |
| 6 | 全部方案基于**中文短文本**场景；Laya 是 multilingual、CLM 未验证中文 |

---

*本文档为设计稿。实施前需确认：① 上表第 1 项（CLM 权重位置）② 是否接受"先做 A 档、B 档待验证"的取舍。*
