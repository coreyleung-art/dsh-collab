# 蓝图 R025 R2 · AI 提议 → 机器验证 → 打回模式调研（AI Judge Pattern）

> 目标：为「AI 生成建议 → 确定性机器验证层 → 不通过打回（受限循环）→ 通过放行/降级」的验证-打回模式做方法准备。
> 核心问题：AI 输出是概率性的，如何在规模化执行前用**确定性/可审计**的机器层拦截错误，并把验证失败转化为模型改进信号。
> 调研日期：2026-08（web_search 8 次 + 关键源全文交叉验证）。
> 衔接：[d33-adoption-learning.md](./d33-adoption-learning.md)（L2D / 渐进自动化）——本蓝图是 d33 的"执行前防线"：d33 回答"何时该交给 AI/人工"，本蓝图回答"AI 提议后机器如何把关"。

---

## 结论（模式设计建议）

**推荐模式：AI 提议 → 三层验证漏斗 → 有界打回循环 → 降级（人工/L2D）→ 失败信号回流训练。**

1. **验证层按"可判定性"分层，机器能判定的绝不用模型判**：
   - **L1 机械层（100% 确定性）**：JSON Schema / 类型检查 / 参数枚举 / 格式约束。LLM 只产出**结构化动作契约**（action + 参数对象），机器校验契约本身。morphllm 六类护栏失败中只有 format 类是纯机械的，**schema 校验器是这一类恰好的工具**（[来源](https://www.morphllm.com/llm-guardrails)）。
   - **L2 规则层（确定性业务规则）**：Datalog / 规则引擎表达业务约束（如"折扣率 ∈ [0.5,0.9] 且不得与同店活动叠加"），编译成可执行策略，AI 提议必须满足约束才放行（[Policy Compiler 2602.16708](https://arxiv.org/pdf/2602.16708v1)）。
   - **L3 语义层（模型侧验证器，概率性）**：事实核查（claim extraction → evidence retrieval → scoring）、groundedness 检查、独立验证模型。**这一层永远不是最终防线**，它只决定"要不要打回/降级"。
   - 落地顺序：**L1、L2 是硬门（fail-closed），L3 是软门（决定 retry 还是 escalate）**。

2. **真值判定与执行准入分离（QWED 核心原则）**：验证结果三态 `VERIFIED / UNVERIFIABLE / BLOCKED`，其中 **"执行 ≠ 验证"**——计算成功但无确定性证明 = UNVERIFIABLE，绝不等于 VERIFIED；**准入（admission: ADMIT/BLOCKED）由策略独立门控**，不由验证状态单独决定（[qwed-verification](https://github.com/qwed-ai/qwed-verification)）。这正对应 d33 的"风险门控"：机器验证通过 ≠ 可自动执行，高成本动作仍需风险等级放行。

3. **打回循环必须"有界 + 有停止规则"**：不通过就重试会带来新问题——无界循环、重试漂移、验证器噪声。采用 verify-repair loop 的鲁棒停止：设定**最大重试次数 + 预算（token/成本）上限 + 单调退化检测**（连续 N 次修复质量不升即停），停止后统一降级路径（L2D 人工 / 简化方案 / 放弃）（[Verify, Repair, Repeat, or Stop? 2607.17641](https://browse-export.arxiv.org/pdf/2607.17641)）。

4. **验证点放在每个 agent 边界与每个动作执行前**，而不是只在最终输出：多 agent 流水线里一个 agent 的幻觉会成为下一个 agent 的输入，错误**沿链放大**；在每次交接处验证 + 生成**验证收据**（signed/timestamped）做合规审计（[Output Verification Loop 模式](https://www.agentic-patterns.com/patterns/output-verification-loop)）。

5. **衔接 d33 L2D 的分工**：机器验证与人工 deferral 互补——**L1/L2 能判定的（格式/规则/参数）机器直接打回，不进人工；L3 语义不确定 + 动作高风险的走 d33 的 P(采纳) 置信度与风险门控 defer 给人工**。即：机器确定性边界越宽，需要人工 review 的样本越少，自动化覆盖率越高——这是"渐进自动化"的机器侧加速器。

6. **验证失败 = 训练信号（RLVR 范式）**：把"打回/通过 + 证据"记录为可验证奖励（verifiable reward），回流到建议模型做 RL 微调。AlphaProof/DeepSeek-Prover 证明这是可扩展的闭环：**LLM 负责概率性提议，形式化验证器负责确定性裁决，裁决结果驱动模型改进**（详见 AlphaProof 章节）。

---

## Guardrails 框架对比

**六类失败类型**（[morphllm LLM Guardrails 2026](https://www.morphllm.com/llm-guardrails)）：jailbreak/提示注入、PII/数据泄露、毒性内容、主题/策略越界、幻觉/groundedness、格式结构。**前五类语义性、仅最后一类纯机械**——这决定了工具选型：正则/schema 只解决第六类，语义类必须用模型/检索。

**主流框架/服务**（许可与定位，2026-06 核验）：

| 工具 | 类型 | 定位 | 许可 |
|---|---|---|---|
| Guardrails AI | 开源框架 (Python) | 组合输入/输出 Guards 验证器库：PII/毒性/格式/竞品提及，**验证失败自动重试** | Apache 2.0 |
| NVIDIA NeMo Guardrails | 开源框架 (Python) | **Colang 可编程对话护栏**：对话流控制、话题边界、jailbreak rails、事实核查 rails | Apache 2.0 |
| Llama Guard 3 (Meta) | 开源权重分类器 | 按 MLCommons 危害分类法给输入/输出打 safe/unsafe 标签，1B/8B/11B-Vision | Llama 社区许可 |
| OpenAI moderation | 托管 API | omni-moderation 分类文本/图像（仇恨/自伤/色情等），API 用户免费 | 托管 |
| Azure AI Content Safety | 托管 API | Prompt Shields 检测直接/间接注入 + 内容审核 | 免费层+付费 |
| Lakera Guard | 托管 API（商业） | 实时注入/jailbreak/系统提示提取检测，一行接入 | 免费层+付费 |

**两条关键轴**：
- **输入护栏 vs 输出护栏**：输入护栏在模型看到用户消息前拦截（jailbreak/注入/PII，被拦不花推理费）；输出护栏在响应发出前拦截（毒性/泄露/无来源主张/格式错）。**一次攻击常跨两侧**（注入成功导致系统提示泄露=输入失败变输出失败），强系统两端都挂护栏。
- **构建时 vs 运行时**：构建时（预部署，红队/评估集/CI）只能证明"已知用例健全"；运行时（每轮真实流量）是"未知用例与用户之间唯一防线"。**本模式的验证层 = 运行时护栏的"格式/策略"子集**。

**关键局限（与本模式的关系）**：所有公共护栏只执行**公共分类法**（毒性/PII/MLCommons 危害），**都不知道你的业务策略**（退款规则、禁谈话题、折扣约束）——这正是 L2 规则层必须自建的原因，也是 AI-Judge 模式与通用 guardrails 的分野。

---

## AI提议→机器验证→打回模式

**参考模式 Output Verification Loop**（[agentic-patterns](https://www.agentic-patterns.com/patterns/output-verification-loop)）：生成与动作之间插入验证步骤，三阶段——**claim extraction**（把输出拆成原子主张）→ **evidence retrieval**（从权威源检索支持/反驳证据）→ **scoring**（逐主张信任分 + 总体置信），然后按阈值三选一：`proceed` / `retry_with_feedback(flagged_claims)` / `escalate_to_human`。多 agent 系统在**每次交接处**验证，防错误传播；验证收据留审计。

**打回循环的工程契约**（综合 [2607.17641](https://browse-export.arxiv.org/pdf/2607.17641)、[qwed-verification](https://github.com/qwed-ai/qwed-verification)、[Output Verification Loop](https://www.agentic-patterns.com/patterns/output-verification-loop)）：

```
proposal = agent.generate(prompt)
for attempt in 1..MAX_RETRIES:
    result = verify(proposal, context)      # L1 schema → L2 rules → L3 semantic
    if result.status == VERIFIED and admission == ADMIT:
        return execute(proposal)            # 放行
    elif result.status == BLOCKED:          # 硬违规（注入/规则违例）→ 不再重试
        return escalate(result)             # 降级人工 / 放弃（fail-closed）
    else:                                   # UNVERIFIABLE / 语义不过 → 打回
        proposal = repair(proposal, result.feedback)   # 携带具体反馈重试
        if not quality_monotonic(attempt):  # 修复质量不再上升 → 提前停止
            return escalate(result)
return escalate(last_result)                # 预算耗尽 → 降级
```

**QWED 的裁决语义（可直接复用）**：
- `DiagnosticResult`：**VERIFIED**（建立了证明，附证据）/ **UNVERIFIABLE**（证明无法建立）/ **BLOCKED**（策略或规则拒绝）。
- **执行 ≠ 验证**：成功计算报告 UNVERIFIABLE，绝不伪装成 VERIFIED——只有确定性、证据绑定的 proof 才算通过。
- **真值 vs 准入分离**：如 `POST /verify/code` 对"被证明不安全"的代码返回 VERIFIED-as-unsafe + admission=BLOCKED；**安全门控看 admission，不看 status**。
- **Fail-closed 批量**：批量验证只要有一条被反驳/阻止，整批失败。
- 适用边界：**需要开发者提供 ground truth（期望值/schema/契约）且 LLM 输出结构化**；不适用于"规范来自自然语言、输出自由文本"的场景——本模式的运营建议恰好是结构化契约型，适用。

**本场景落地**：建议体 = `{action: 改价|下架|上架|接单|回复, target: 商品ID, params: {...}, reason: 一句话}`。L1 校验 params 的 schema 与枚举（商品 ID 存在、价格为正、时间格式）；L2 校验业务规则（改价幅度上限、折扣不得叠活动、下架需在营业时段外）；L3 对 reason/回复话术做 groundedness（是否与订单/库存证据一致）。任一不过 → 打回带具体字段反馈，3 次内修复不达标 → 降级人工。

---

## 规则引擎确定性校验

**原则：Guardrails Beat Guidance**——护栏优于引导（[agentpatterns](https://learn.agentpatterns.ai/verification/guardrails-beat-guidance/)）：与其在提示词里"请求"模型遵守约束，不如在系统里"强制"校验约束。概率性模型 + 确定性校验 = 各取所长：**AI 负责生成，规则引擎负责裁决**。

- **规则层表达**：用**声明式规则**（Datalog 子集 / OPA Rego / 自定义 DSL）表达业务策略，与代码分离、可审计、可单测。Policy Compiler for Secure Agentic Systems（[2602.16708](https://arxiv.org/pdf/2602.16708v1)）展示了把 agentic 系统授权策略编译成可执行策略的思路——策略即代码，AI 动作过策略编译产物才执行。
- **"schema + 规则"组合**：JSON Schema（结构/类型/枚举）解决"形"，规则引擎（跨字段/跨实体约束、时序约束）解决"义"。例：schema 保证 `discount: number`，规则保证 `0.5 ≤ discount ≤ 0.9 ∧ 不与活动 A 叠加 ∧ 生效时间在营业窗口内`。
- **确定性验证适用条件（QWED 的边界）**：ground truth 可定义、输出结构化 → 用符号求解器/校验器（100% 可复现，同一查询永远同一结果）；无 ground truth / 自由文本 → 该领域不适用确定性校验，退回 L3 语义层或人工。
- **LLM 与规则引擎的衔接**：LLM 只产出**参数化动作**（而非自然语言指令），规则引擎对参数做裁决。这样"AI 概率性"被压缩在参数生成这一步，其后每一步都是确定性的——**错误概率只乘一次，不被下游放大**（呼应错误放大章节）。
- **审计**：每次裁决输出 proof/证据（哪个规则、哪个字段、什么值触发），与验证收据一起落盘——满足合规与 d33 的"采纳日志"复用（打回原因也是训练/阈值调整的输入）。

---

## AlphaProof失败→RL闭环

**范式：形式化验证器作为奖励函数（RLVR, Reinforcement Learning with Verifiable Rewards）**。

- **AlphaProof 架构**（2025 Nature 报道 + DeepMind 系列）：LLM 生成**候选 Lean 证明**（概率性搜索）→ **Lean 形式化内核做确定性验证**（证明被内核接受才算对）→ **验证失败/通过作为强化学习奖励信号** → 模型在"可验证领域"持续自我改进。AI 负责搜索空间，机器负责真相，真相回流训练——**裁判必须形式化，选手才敢概率化**。
- **DeepSeek-Prover-V1.5**（[2408.08152](https://github.com/intentlink/deepseek-news-research/blob/main/2024/deepseek-prover-v1-5-harnessing-proof-assistant.md)）：正式确立"proof assistant 反馈 + MCTS + RL"的工程配方——证明器给出**具体失败反馈**（哪一步、缺什么引理），模型据此修复再试，形成"提议→失败→修复→再验证"的闭环，且把**过程性信号（proof state）与结果性信号（内核接受）**都用上。
- **Agentic RL survey**（[2509.02547](https://arxiv-org.ezproxy.obspm.fr/html/2509.02547v5)）：outcome-only 奖励范式在 2024 年由 DeepSeek-Prover 规模化验证——**验证器自动给出 0/1 奖励 + 诊断，无需人工标注**，是 RL 数据飞轮的关键。
- **Prover-Verifier 家族**（[Trust but Verify: Prover-Verifier Deliberation, 2605.25133](https://ar5iv.labs.arxiv.org/html/2605.25133)）：除了训练模型，还有"可验证性"设计——**让提议者输出可被验证者核验的形式**（可检查证明/可执行测试），人类能验证的模型输出更可信。选择性预测（selective prediction）版本与 d33 的 defer 直接相关：**验证者判不了才 defer**。

**对运营建议场景的迁移设计**：
1. **领域 DSL + 形式化检查器**：把"动作 + 前置条件 + 期望后效"写成可机器检查的形式（如约束求解器可判定的价格/库存/时间约束），就像 Lean 之于数学。AI 提议动作，检查器裁决。
2. **执行后状态验证作为奖励**：动作执行后，用订单/库存/价格**真实状态机**校验"后效是否符合提议声明"（如：提议"改价至 ¥59"，执行后校验商品现价=¥59 且无价格冲突），符合=+1，不符=-1+诊断。这就是运营版的"Lean 内核"——**真实业务系统是最终验证器**。
3. **失败反馈结构化**：打回时记录失败字段 + 原因类别（schema/规则/事实/超预算），按类别聚合成训练集，对建议模型做 RL 或偏好微调，形成"验证失败→模型改进"的飞轮。

---

## 错误放大风险与缓解

**风险命题：AI 错误率在规模化/级联场景被放大，而非平均掉**（与经典 BFT 的"多数裁决消错"相反）。

- **级联幻觉实验**（[changkun/agents-verification Exp 06](https://github.com/changkun/agents-verification/blob/main/specs/06-cascading-hallucination.md)）：顺序 agent 链（K=2/4/6）三假设——**H1 传播主导纠正**：上游 subtle 错误在"仅首阶段可见源"条件下，下游几乎不纠正；**H2 源可见性可救**：每阶段重新锚定原始源可把纠正率提升 ≥30pp；**H3 超线性退化**：端到端正确率劣化快于 (单步正确率)^K（错误复合而非累积）。度量集：错误引入率/传播率/纠正率、错误幅度、端到端正确率。
- **错误级联建模**（[From Spark to Fire, 2603.04474](https://browse-export.arxiv.org/pdf/2603.04474)）：多 agent 协作中的 error cascade 建模与缓解——印证"任何 agent 流水线都是脆弱性放大器，除非每步有独立验证"。
- **放大机制**：① 链式传播（下游消费上游错误输出）；② 自动化偏误/过度信任（人对 AI 输出放松审查，衔接 d33 的 automation bias 文献）；③ 循环复读（自反馈循环强化同一错误）；④ 规模化乘法（N 条建议 × 单条错误率 = 期望错误量线性涨，但若带依赖则级联涨）。

**缓解清单**（综合各源）：
1. **每边界验证 + 验证收据**：交接处和动作前都过验证层，留审计痕（agentic-patterns / QWED）。
2. **重新锚定主源**：下游 agent/校验器必须能访问原始证据（订单、库存、价目表），不能只信上游文本输出（H2）。
3. **Fail-closed + 准入分离**：无法证明安全就不放行；高成本动作永远双门（验证门 + 风险门）。
4. **有界打回**：限制重试次数与预算，防无界循环（2607.17641）。
5. **错误率预算监控**：按 d33 的"在线监控持续条件"思路，跟踪每层验证的通过率/打回率/降级率，**打回率突降 = 验证器退化，打回率突升 = 模型漂移**——两者都要告警。
6. **分级放大策略**：低价值/可逆动作（描述修改）自动化；高价值/不可逆（改价、下架、退款）强制验证 + 风险门控 + 可选人工（d33 四阶段灰度）。

**量化直觉**：设单步错误率 ε，K 步流水线若不验证，端到端错误率 ~ 1-(1-ε)^K（K=4, ε=5% → ~18.5%）；每步验证把错误率压到 ε' 后回到 ~1-(1-ε')^K。**验证层省的不是单步，是幂次放大项**。

---

## 论文清单（arXiv ID）

| arXiv ID | 标题/主题 | 与本模式关系 |
|---|---|---|
| **2607.17641** | Verify, Repair, Repeat, or Stop? Robust Stopping for Noisy Verify-Repair Loops | 打回循环的**鲁棒停止**（噪声验证器下的重试边界） |
| **2603.04474** | From Spark to Fire: Error Cascades in LLM Multi-Agent Collaboration | 错误级联建模与缓解 |
| **2605.25133** | Trust but Verify: Prover-Verifier Deliberation for Selective LLM Prediction | 提议者-验证者分工 + 可验证输出 + 选择性预测（衔接 defer） |
| **2607.02615** | The Agent Creates, We Validate: Lightweight Framework for Agentic Artifact Generation | "AI 生成、机器验证"轻量框架 |
| **2602.16708** | Policy Compiler for Secure Agentic Systems | 授权/业务策略编译为可执行策略（规则层） |
| **2408.08152** | DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for RL and MCTS | RLVR 闭环工程配方（提议→失败反馈→修复→RL） |
| **2509.02547** | The Landscape of Agentic RL for LLMs: A Survey | agentic RL 综述（outcome-only 奖励范式） |
| **2312.06674** | Llama Guard: LLM-based Input-Output Safeguard | 输入/输出安全分类器（L0 公共安全层） |
| **2408.12935** | AI Safety Landscape for LLMs: Taxonomy, SOTA, Future Directions | 护栏全景综述（taxonomy） |
| **2402.01822** | Building Guardrails for Large Language Models | 护栏构建综述 |
| **2310.10501** | NeMo Guardrails: Controllable and Safe LLM Applications with Programmable Rails | Colang 可编程护栏（框架论文） |
| **2203.11171** | Self-Consistency Improves CoT Reasoning (Wang et al.) | 采样-多数表决（机器侧消错基线） |
| **2305.20050** | Let's Verify Step by Step (PRM, Lightman et al.) | 过程奖励验证器（L3 语义层代表） |
| — (Nature 2025) | AlphaProof: AI achieves gold-medal standard at IMO（DeepMind） | 形式化验证器作 RL 奖励的里程碑系统 |
| — (d33 关联) | 2006.01862 / 2301.06197 / 2207.05830 / 2403.03870（L2D） | 降级路径：机器验证之外的 deferral 决策 |

> 注：2310.10501 / 2203.11171 / 2305.20050 / 2408.08152 为经典或广泛引用的 ID（本次搜索以 GitHub/综述二次确认），其余 ID 均来自本次检索直接命中的 arXiv 源。

---

## 证据来源

- [LLM Guardrails (2026): Failure Taxonomy, Libraries Compared（morphllm）](https://www.morphllm.com/llm-guardrails)
- [NVIDIA NeMo Guardrails 文档：Guardrails Configuration / Process](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/yaml-schema/guardrails-configuration) · [NeMo Guardrails GitHub](https://github.com/NVIDIA-NeMo/Guardrails)
- [Llama Guard（arXiv 2312.06674）](https://arxiv.org/abs/2312.06674) · [Guardrails AI（GitHub）](https://github.com/guardrails-ai/guardrails)
- [Output Verification Loop — Agentic Patterns](https://www.agentic-patterns.com/patterns/output-verification-loop)
- [qwed-verification：确定性验证基础设施（GitHub）](https://github.com/qwed-ai/qwed-verification)
- [Guardrails Beat Guidance（agentpatterns.ai）](https://learn.agentpatterns.ai/verification/guardrails-beat-guidance/)
- [Verify, Repair, Repeat, or Stop?（2607.17641）](https://browse-export.arxiv.org/pdf/2607.17641)
- [From Spark to Fire: Error Cascades in Multi-Agent Collaboration（2603.04474）](https://browse-export.arxiv.org/pdf/2603.04474)
- [Cascading Hallucination in Sequential Agent Chains（changkun/agents-verification Exp 06）](https://github.com/changkun/agents-verification/blob/main/specs/06-cascading-hallucination.md)
- [Trust but Verify: Prover-Verifier Deliberation（2605.25133）](https://ar5iv.labs.arxiv.org/html/2605.25133)
- [The Agent Creates, We Validate（2607.02615）](https://arxiv.org/abs/2607.02615)
- [Policy Compiler for Secure Agentic Systems（2602.16708）](https://arxiv.org/pdf/2602.16708v1)
- [DeepSeek-Prover-V1.5 报道（GitHub intentlink）](https://github.com/intentlink/deepseek-news-research/blob/main/2024/deepseek-prover-v1-5-harnessing-proof-assistant.md)
- [The Landscape of Agentic RL for LLMs: A Survey（2509.02547）](https://arxiv.org/abs/2509.02547)
- [AI Safety Landscape for LLMs（2408.12935）](https://arxiv.org/html/2408.12935v3) · [Building Guardrails for LLMs（2402.01822）](https://ar5iv.labs.arxiv.org/html/2402.01822v1)
- [AlphaProof / DeepMind IMO 报道（Nature 2025）](http://www.natureasia.com/en/info/press-releases/detail/9147) · [DeepMind 报道（中科院网信网转载）](https://ecas.cas.cn/xxkw/kbcd/201115_149827/ml/xxhcxyyyal/202606/t20260604_5111757.html)
- 本地衔接：[d33-adoption-learning.md](./d33-adoption-learning.md)（L2D / 渐进自动化）
