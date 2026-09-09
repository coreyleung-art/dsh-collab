# MLX LoRA 微调 qwen2.5-3b 沉积判定模型 · 完整计划

> ⛔ **【已止损归档 2026-08-22】** 微调「技术成功、语义失败」——学到长度代理而非语义，实测比词频级联差（3/4 vs 4/4）。见 §八 最终结果。模型保留归档，不接入。
>
> 日期：2026-08-22 · 协调者 · 前置调研：local-llm-mac-mini-2026（选型）+ 油菜品种 LoRA 实战
> 目标：把 qwen2.5-3b 从「通用模型」微调成「沉积判定专用模型」，三分类（deposit/skip/review）稳定，替代「词频+qwen布尔」级联。

## 一、目标与预期

| 项 | 现状 | 微调后预期 |
|---|---|---|
| 三分类稳定性 | 通用 qwen2.5:3b 波动（7/8→4/8） | 专用模型稳定（目标 ≥90% 一致率） |
| 判定方式 | 词频权重(96.1%) + qwen布尔兜底 | 单一专用模型直判三分类 |
| 推理成本 | 本地免费 | 本地免费（3b 仍轻量） |
| 部署 | Ollama qwen2.5:3b (GGUF) | MLX 微调后 fuse → 转 GGUF 回 Ollama 或 MLX 直跑 |

## 二、前置问题（必须先解决，否则微调效果打折）

### ⚠️ P0：训练数据缺「review」类样本

当前 1152 条只有 deposit(860)/skip(292) 二分类，**没有 review 样本**。三分类模型的 review 类学不到。

**解法**（二选一，推荐 A）：
- **A. 先做二分类微调**（deposit/skip），review 由「低置信→人工」兜底——与当前级联逻辑一致，review 本就不是模型该独立判的（它是「拿不准」的信号）。微调目标改为「稳定二分类」，review 仍是置信度阈值产物。
- **B. 补 review 样本**——从 agent-bus 里找「拿不准」的消息人工标 review，成本高、慢。

**结论：采纳 A（二分类微调 + review 由置信度阈值出）**，符合「review=人工兜底」的设计。

## 三、执行步骤（6 步）

### Step 1：数据转 MLX 指令格式（协调者脚本，零外网）
- 输入：`route-feedback-train.jsonl`（1152 条 `{summary, actual}`）
- 输出：`train.jsonl / valid.jsonl / test.jsonl`（MLX messages 格式，二分类指令）
- 指令模板：
  ```json
  {"messages": [
    {"role":"system","content":"你是沉积判定器。判断任务摘要是否值得沉淀复用经验（产生了可复用产出：脚本/插件/文档/规范/知识入库/修复bug/SOP/模式）。只回答「沉淀」或「跳过」。"},
    {"role":"user","content":"<summary>"},
    {"role":"assistant","content":"沉淀|跳过"}
  ]}
  ```
- 划分：train/valid/test = 8:1:1（铁律：test 训练期绝不碰）
- 脚本：`scripts/mlx-data-prep.py`（新写）

### Step 2：环境准备（用户终端，需外网）
```bash
pip install -U mlx mlx-lm huggingface_hub
# 下载 MLX 格式基座（约 2GB，需外网，沙箱禁网故用户执行）
hf download mlx-community/Qwen2.5-3B-Instruct-4bit --local-dir ~/mlx-models/Qwen2.5-3B-Instruct-4bit
```

### Step 3：LoRA 微调（用户终端）
```bash
mlx_lm.lora --model ~/mlx-models/Qwen2.5-3B-Instruct-4bit \
  --data ~/dsh-collab/token-monitor/mlx-data/ \
  --train --adapter-path ~/mlx-adapters/deposit-judge \
  --iters 200 --batch-size 2 --learning-rate 1e-5
```
- 内存：16GB 即可（mac-mini 24GB 够）
- 时间：1152 条小数据，预计 30-60 分钟
- LoRA 权重产出：几十 MB

### Step 4：评估（用户终端 + 协调者判读）
```bash
# 用 test.jsonl 评估（训练期唯一一次）
mlx_lm.evaluate --model ~/mlx-models/Qwen2.5-3B-Instruct-4bit --adapter-path ~/mlx-adapters/deposit-judge --data test
```
- 目标：二分类一致率 ≥90%（对比通用模型 7/8）
- 不达标 → 调 rank/learning-rate/iters 重训（但不得碰 test，用 valid 调）

### Step 5：融合 + 部署回 Ollama（用户终端）
```bash
# fuse 合并 LoRA 回基座
mlx_lm.fuse --model ~/mlx-models/Qwen2.5-3B-Instruct-4bit --adapter-path ~/mlx-adapters/deposit-judge
# 转 GGUF 或直接 MLX 推理；最简=MLX 直跑，Ollama 留通用 qwen2.5:3b 兜底
```

### Step 6：接入 route-learner（协调者脚本）
- route-learner.py 增加 `--use-finetuned` 模式：直接调微调模型二分类，词频/qwen布尔降级为「模型不可用时的兜底」
- 部署后：主判=微调模型，兜底=词频权重

## 四、风险与回退

| 风险 | 概率 | 回退 |
|---|---|---|
| 1152 条对 LoRA 太少、过拟合 | 中 | 数据够小任务二分类（油菜案例 86 条即有效）；过拟合则降低 iters 或加 early stop |
| 二分类不够（缺 review） | 低 | review 本就是「拿不准」阈值产物，不影响二分类微调 |
| 沙箱禁外网 | 确定 | Step 2-5 全用户终端执行，Step 1/6 协调者脚本（零外网） |
| 微调后反而不如级联 | 低 | 保留词频权重兜底，微调模型仅作主判，可随时切回 |

## 五、分工

| 步骤 | 谁 | 外网 | 说明 |
|---|---|---|---|
| Step 1 数据准备 | 协调者（写脚本跑） | 否 | mlx-data-prep.py |
| Step 2 装 mlx+下基座 | 用户终端 | 是 | 2GB 下载 |
| Step 3 训练 | 用户终端 | 否（已下载） | 30-60min |
| Step 4 评估 | 用户终端+协调者 | 否 | 协调者判读指标 |
| Step 5 融合部署 | 用户终端 | 否 | fuse |
| Step 6 接入 | 协调者 | 否 | 改 route-learner |

## 六、成功标准

1. test 集二分类一致率 ≥90%
2. 「查询订单状态」→ 跳过、「状态机落地」→ 沉淀（词歧义样本稳定）
3. 微调模型推理速度 ≥ 现有 qwen2.5:3b（不劣化）
4. 部署后 route-learner 以微调模型为主判，级联降为兜底

## 七、关联

- local-llm-mac-mini-2026.md（模型选型）
- decision-system-principle-2026-08-22.md（设计原则：数据驱动而非规则驱动，微调=最彻底的「补数据」）
- route-learner.py / route-feedback-replay.py（训练数据来源）
- 油菜品种 LoRA 实战（https://a2htray.github.io/post/learn-ai/mlx-lm-model-finetuning/）

## 八、最终结果（2026-08-22 · 止损归档 ❌）

> 结论：融合模型能加载能跑，但学到的是「长度=格式」代理，不是语义；实测比现有词频级联还差。**决定：冻结归档，不接入 route-learner，词频级联继续当家。**

### 实测证据（关键样本判定对比）

| 样本 | 词频级联 | MLX 融合模型 | 期望 |
|---|---|---|---|
| 查询外卖今日订单状态 | 跳过 ✓ | 跳过 ✓ | 跳过 |
| 新建了 cordis-crash-audit 审查脚本 | 沉淀 ✓ | 沉淀 ✓ | 沉淀 |
| 保持协作 收到 | 跳过 ✓ | 跳过 ✓ | 跳过 |
| 花店驾驶舱状态机落地 13 子项收官 | 沉淀 ✓ (0.96) | 跳过 ✗ | 沉淀 |

词频级联 **4/4**，MLX **3/4**——MLX 是负资产，比现状还差。

### 根因：训练数据「长度零重叠」

| 标签 | 平均长度 | 最短~最长 | <30字 | 30~100字 | >100字 |
|---|---|---|---|---|---|
| 跳过 | 3 字 | 1~12 字 | 100% | 0% | 0% |
| 沉淀 | 182 字 | 37~200 字 | 0% | 100% | 100% |

- 真实数据 1152 条里 **0 条短沉淀、0 条长跳过**——长度是完美分隔面（迭代报告协议 J46 让实质产出必长、纯回执必短）。
- 模型没学「语义」，学了「短=回执、长=报告」的格式代理。
- **100% eval 是假象**：test 集与 train 同分布，测的是「测长度」而非「测语义」，在真实边界样本上原形毕露。

### 教训（可复用，已并入 decision-system-principle）

1. **评估集必须与生产分布一致**，否则 100% 是「自己出题自己批」——用同分布切出的 test 验证等于没验证边界。
2. **微调前先做「混淆面体检」**：标签 × 特征（长度/关键词）交叉分布，发现零重叠即警告「模型会学代理而非目标概念」。
3. **成功标准里的关键边界样本必须实测，不能只信聚合准确率**——本计划成功标准 #2 明确写了「状态机落地→沉淀」，但评估阶段没拿它实测就宣布 100%，缺「边界样本验收」这道关。
4. **微调前先对标现状基线**：目标模型须「打赢」现有级联才上岗。本次现有词频级联 4/4、MLX 3/4，结论一票否决。

### 处置

- 模型权重（`~/mlx-models/deposit-judge-fused` 1.7GB + `~/mlx-adapters/deposit-judge`）**保留归档**，不删除，供未来有真实边界数据时重启。
- `scripts/deposit-judge.py` 标记 **archived**，不接入 route-learner。
- `route-learner.py` 维持「词频权重 + MIN_KNOWN_HITS 门控 + qwen2.5:3b 布尔兜底」不变（当前最优）。
- 磁盘可选项：用户可自行删 fused 模型省 1.7GB（本次不代删）。

---
*MLX LoRA 微调计划 v1.0 → 已止损归档 · 协调者 2026-08-22*
