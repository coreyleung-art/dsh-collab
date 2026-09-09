# 自动沉淀交付链 · 运行手册（Runbook）

> 日期：2026-08-22 · 协调者 · 用途：值班 HR/协调者照此手册执行「任务完成 → 自动沉淀」闭环，省 token、防重复推导。
> 配套：sedimentation-chain-scan.py（扫描器）· sedimentation-chain-model-routing-2026-08-22.md（模型路由决策表）· preset-scoped-tool-pattern + cordis-crash-audit-sop（七步链各环节模板）。

## 一、运行模式（B+ 半自动，当前启用）

**一句话**：扫描器（脚本，零 LLM）生成「待沉淀清单」→ 值班 agent 在实质回合按模型路由决策表执行七步链。

```
任务完成
   ↓
event-bus 发布 task.completed
   ↓
sedimentation-chain-scan.py 扫描（纯规则，零 LLM）
   ↓ 判定 deposit / skip / review
   ↓
待沉淀清单（token-monitor/sedimentation-queue/YYYY-MM-DD.json）
   ↓
值班 HR/协调者 实质回合消费清单 → 按决策表执行七步链
   ↓ 只本地环节（判定/查重/向量化/登记）自动，工具化/提炼按门控升级订阅
```

## 二、值班回合标准动作（每次实质回合顺带做）

1. **扫清单**：`python3 scripts/sedimentation-chain-scan.py --since 7`（零成本）
2. **看 deposit 项**：逐条按七步链执行（见 §三）
3. **skip 项**：直接忽略（纯执行无复用，结果已进登记表）
4. **review 项**：人工判断值不值得沉淀（无信号或信号冲突）
5. **标记已处理**：`python3 scripts/sedimentation-chain-scan.py --mark-consumed`

## 三、七步链执行（deposit 项照此）

| 步 | 动作 | 用什么 | 成本 |
|---|---|---|---|
| 1 | 判定（值不值得沉淀） | qwen:1.8b 本地分类 | 0 |
| 2 | 查重（先查后写） | knowledge_search + bge-m3 向量检索 | 0 |
| 3 | 安全审查（仅插件改动） | cordis-crash-audit.py 规则脚本 | 0 |
| 4 | 工具化（生成脚本） | gemma4 本地→低置信升级 flash | 0→按需 |
| 5 | 双文档沉淀（复用经验总结） | gemma4 本地→低置信升级 flash | 0→按需 |
| 6 | KB 向量化 | knowledge_add_document（自动嵌入） | 0 |
| 7 | chroma 向量化 | bge-m3 本地 1024 维 | 0 |
| 8 | profile/registry 登记 | 规则化 append | 0 |

**关键**：步骤 1/2/3/6/7/8 全本地零订阅；只有 4/5 可能用订阅模型，且按置信度门控（gemma4 先干，conf<0.7 才升级 flash）。

## 四、C 模式（全自动，后续升级）

**升级条件**：B+ 跑通几轮、命中率稳定后，`--auto` 启用编排器。

**落地形态**（重要，非纯脚本）：
- 扫描器（脚本）已就绪，但「自动调 knowledge_add_document / chroma_index / agent_profile」是 **agent 工具**，脚本无法直接调（需 agent 回合）——与 event-bus「消费端需 agent 回合代发」同款限制。
- 所以 C 模式 = 扫描器（脚本）+ **值班 agent 回合自动消费**：值班回合时，扫描器生成清单 → agent 用本地模型自动执行本地化环节（判定/查重/向量化/登记）→ 仅工具化/提炼按门控升级。
- 即 C 不是「全无人值守脚本」，而是「脚本扫描 + agent 本地自动执行」，订阅消耗仅在 4/5 低置信时发生。

## 五、省钱量化（自测基线）

| 任务类型 | 订阅 token |
|---|---|
| 纯执行（skip） | 0 |
| 沉淀但无工具化 | 0（全本地） |
| 沉淀+工具化 | 0~数万（仅低置信升级） |

- 预期 60-80% 任务全程零订阅；综合成本 = 纯云端 30-50%（与 v1.1 门控一致）。
- 每次沉淀记录「本地命中/升级订阅」计数 → 供 v1.2 学习型路由（RouteLLM）积累数据。

## 六、值班纪律

1. 值班回合顺带扫清单（零成本，别单独开一轮只为扫描）。
2. 只执行 deposit 项，skip/review 不花 token。
3. 工具化/提炼先本地 gemma4，conf<0.7 才升级 flash（J35 用完即关 gemma4）。
4. 嵌入与推理串行（J35 互斥）：先 bge-m3 向量化 → unload → 再 gemma4 提炼。
5. 周抽 5% 云端对比质量（v1.0 质量护栏）。

## 七、关联

- sedimentation-chain-scan.py（扫描器）
- sedimentation-chain-model-routing-2026-08-22.md（模型路由决策表）
- preset-scoped-tool-pattern-2026-08-22.md（步骤 5 产物模板）
- cordis-crash-audit-sop-2026-08-22.md（步骤 3 审查 SOP）
- model-routing-rules v1.0/v1.1（通用路由规则）
- J35/J36/J46（本地互斥/沉淀闸门/官方文档沉淀）

---
*自动沉淀交付链 Runbook v1.0 · 协调者 2026-08-22 · B+ 启用，C 后续升级*
