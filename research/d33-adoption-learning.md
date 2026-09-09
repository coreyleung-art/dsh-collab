# 蓝图 d3-3 · 采纳率学习模型调研（Learning to Defer / 渐进自动化 T3）

> 目标：为「运营建议 → 人工采纳 → 自动执行」的渐进自动化（T3）做方法准备。
> 核心问题：如何让模型学会"何时该自己决策、何时该交给人类"，并从"人类是否采纳建议"的日志中持续学习采纳概率，达到阈值后自动执行。
> 调研日期：2026-08（通过 web_search 交叉验证，共 11 次检索）。

---

## 结论（模型设计建议）

1. **统一为"学习式拒识/授权"（Learning to Defer, L2D）框架**：把"给出建议"建模为分类/决策器，把"是否自动执行 vs 交给人工"建模为 deferral 决策器。二者可以共享一个打分器，也可以分开学（two-stage），已有成熟的可学习、可证明一致性的算法（Mozannar & Sontag 2006.01862；Mozannar et al. 2301.06197）。

2. **采纳率学习 = 带噪声/有偏的专家示教（learning from deferral feedback）**：日志里"人类是否采纳"是隐式的 deferral 标签，属于"从人类最终动作反推监督信号"的离线学习问题。直接把它当分类标签有偏（人类会犯错、会过度依赖/忽略 AI），要用 L2D 的 consistent estimator 或 post-hoc 校正（Narasimhan et al. post-hoc estimator），而非朴素交叉熵。

3. **主动学习衔接**：用主动学习/bandit 选样策略决定"哪些建议值得先拿去做人工确认"，以最小成本收集最稀缺的采纳/拒绝标签。已关联的 2507.06537（model-agnostic active learning）正好可直接用于"对建议做不确定性排序、挑最有信息量的样本人工确认"。

4. **渐进自动化四阶段达标判定**：不要只看采纳率单点阈值，要组合三层门控——(a) 采纳率（P(采纳)）置信区间下界过阈值；(b) 预测置信度/校准度（Brier/ECE）；(c) 风险门控（高成本/不可逆动作强制 defer）。达标 = 连续 N 个周期三指标同时过线，再做小流量灰度。

5. **推荐模型设计**：输入 = 建议 + 上下文（店铺/时段/历史/操作类型），输出 = 采纳概率 P(采纳)；用 deferral-aware 损失同时学"采纳概率"与"是否该自动执行"，达到阈值且风险门控放行才自动执行。落地为轻量二分类头 + 校准 + 阈值策略，而非重 RL。

---

## L2D 方法/论文

**核心概念**：Learning to Defer（L2D，也称 reject option / selective prediction / learning to abstain）解决"模型何时自己预测、何时 defer 给专家（人类）"，目标是联合最小化错误率 + defer 成本。

| 论文 | arXiv ID | 要点 |
|---|---|---|
| Consistent Estimators for Learning to Defer to an Expert（Mozannar & Sontag, ICML 2020） | **2006.01862** | 奠基作。给出学习 deferral 规则的**一致估计器**与替代损失（surrogate loss），允许"真实专家标签不可观测"时仍能一致学习；可证明优于朴素的"用模型置信度阈值做 reject"。开源实现 `clinicalml/learn-to-defer`。 |
| Who Should Predict? Exact Algorithms for Learning to Defer to Humans（Mozannar et al., AISTATS 2023） | **2301.06197** | Two-stage：先学专家/模型，再学 deferral 规则；给出**精确算法**（非近似），并指出"模型+专家互补性"（complementarity）是 defer 价值来源。 |
| Post-hoc estimators for learning to defer to an expert（Narasimhan et al., NeurIPS 2022, Google） | 2207.05830（[Google Research](https://research.google/pubs/post-hoc-estimators-for-learning-to-defer-to-an-expert/)） | **Post-hoc 校正**：给已训练分类器加 deferral，无需重新训练；对"日志里只有最终决策、无真实标签"的离线场景尤其实用（正对应采纳日志）。 |
| Learning to Defer（survey / 综述） | **2403.03870** | L2D 领域综述，覆盖方法分类、损失函数、评估指标。 |
| Learning to Partially Defer for Sequences | **2502.01459** | 序列场景下"部分 defer"，适用于分步运营动作（部分步骤自动、部分人工）。 |
| To Ask or Not to Ask: Learning to Require Human Feedback | **2510.08314** | 学习"何时需要向人索取反馈"，与采纳率学习直接相关。 |
| When to Act and When to Ask: Policy Learning with Deferral Under Hidden Confounding（NeurIPS 2024） | [NeurIPS](https://mlanthology.org/neurips/2024/ghoummaid2024neurips-act/) | 处理 deferral 学习中的**隐藏混杂**（人类采纳行为受不可观测因素影响）。 |
| Cascaded Language Models for Cost-Effective Human–AI Decision-Making（NeurIPS 2025） | [NeurIPS](https://papers.neurips.cc/paper_files/paper/2025/hash/10e0c427408ccc6e073d9464e2280f89-Abstract-Conference.html) | 级联：小模型先答，不确定则升级到大模型/人类，成本最优，是"渐进自动化"的架构模板。 |

**不确定度 vs 学习式 deferral 的争论**：有工作指出 naive uncertainty 阈值不是最优 deferral（需学习），也有工作主张标定良好的 UQ 可以近似替代（[Is UQ a viable alternative to learned deferral?](https://link.springer.com/chapter/10.1007/978-3-032-06593-3_4)）。结论：**纯置信度阈值是下限基线，学习式 deferral 更优，但工程上可先用校准置信度冷启动**。

**安全医疗场景**：Incorporating uncertainty in LDU for safe CAD（Scientific Reports 2022，[10.1038/s41598-022-05725-7](https://link.springer.com/article/10.1038/s41598-022-05725-7)）把预测不确定度并入 L2D，是"风险门控 + defer"的典型。

---

## 采纳率学习

从"人类是否采纳 AI 建议"学习决策策略，本质是**从 deferral/偏好反馈中做模仿学习或 bandit 学习**：

- **离线模仿学习 / 专家示教**：把"人类最终动作"当示教标签，但需用 L2D 一致估计器/post-hoc 校正消除"人类也会错、会过度依赖（automation bias）或忽略 AI（disuse）"造成的标签偏。医学 HITL 文献（[Automation Bias 系统综述](https://zenodo.org/records/20641572)、[Trust/Scrutiny/Collaboration NEJM AI](https://ai.nejm.org/doi/abs/10.1056/AIe2600354)、[Calibrating Reliance AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/41457)）反复强调：**信任校准是"技能问题"而非"信息问题"**，采纳率不是可靠的真值，需显式建模 human error model。
- **上下文 bandit / 偏好学习**：
  - Jump Starting Bandits with LLM-Generated Prior Knowledge（**2406.19317**）：用 LLM 先验冷启动 bandit，适合"初期采纳样本稀疏"。
  - Neural Dueling Bandits（ICLR 2025）：基于偏好的优化，适合"两建议对比"型采纳反馈。
  - Off-Policy Learning for Personalization（ACM）：离线 off-policy 从日志学习个性化策略，对应"按店/按上下文个性化采纳阈值"。
- **离线 RL / 安全策略优化**：Offline Safe Policy Optimization From Heterogeneous Feedback（**2512.20173**）、Safe RL with Preference-based Constraint Inference（ICML 2026，**2603.23565**）——用偏好/采纳反馈学"受约束的策略"，即"在安全约束下最大化采纳/执行收益"。

> **落地结论**：采纳日志 = 隐式 deferral 标签，正确做法是 L2D 的 post-hoc estimator 或 offline bandit/off-policy 学习，而非朴素地"采纳=1 否则=0"的交叉熵。样本稀疏期用 LLM 先验 / 校准置信度冷启动。

---

## 主动学习衔接

主动学习（active learning / selective sampling）决定"哪些建议最值得拿去人工确认"，用最小标注成本收集最稀缺的采纳标签，与 L2D 形成闭环：**主动学习选样 → 人工确认 → 更新采纳率模型**。

- **已关联本地论文 2507.06537**：A model-agnostic active learning approach for animal detection from camera traps —— **模型无关**的主动学习框架，可直接迁移到"对每条运营建议做不确定性打分 → 挑 Top-K 最不确定/最有信息量的建议人工确认"，不必改动采纳率模型本体。
- Learning to Rank for Active Learning via Multi-Task Bilevel Optimization（UAI 2024）：用排序学习替代单一 acquisition function，适合"建议有多维价值（不确定性×业务影响×成本）"的排序选样。
- Active Learning with Logged Data（**1802.09069**）：离线日志下的主动学习，与"从历史采纳日志里选样再确认"的场景一致。
- Cartography Active Learning（**2109.04282**）：用训练动态（易/难/歧义样本）做选样，可用于识别"模型一贯没把握的建议"。

> **衔接方案**：acquisition = uncertainty（采纳概率接近 0.5 / 熵最大）× 业务影响（改价/下架影响面）× 成本。主动学习挑出的样本既用于提升采纳率模型，也直接驱动"哪些建议需要人工 review"。

---

## 渐进自动化达标判定（四阶段：人工 → 建议 → 采纳率达标 → 自动）

四阶段判定的核心不是单一阈值，而是**分层门控 + 置信区间 + 灰度**：

1. **采纳率阈值（P(采纳) 下界）**：不取点估计，取**置信区间下界**（如 Wilson / Clopper-Pearson / Beta posterior 的 95% 下界）过阈值才算达标，避免小样本波动误判。例如"近 30 天 ≥ 200 条建议、采纳率 95% 下界 ≥ 90%"。
2. **置信度/校准门控**：模型对单条建议的输出须**校准**（ECE/Brier 达标），且"自动执行"只放行高置信（如 P(采纳) ≥ 0.95）。可参考 selective classification / confidence threshold（[JumpCloud 置信阈值](https://jumpcloud.com/it-index/what-is-a-confidence-threshold)、[review gates](https://turingpulse.ai/blog/human-in-the-loop-design)）。
3. **风险门控（cost-aware defer）**：按动作成本分级——低成本可逆动作（如改商品描述）门槛低；高成本/不可逆动作（改价、下架、退款）永远 defer 或要求双签。对应 L2D 的"defer 成本"项。
4. **灰度/持续达标**：连续 N 个周期三指标同时过线 → 进入小流量自动执行 → 监控回退指标（拒单率、差评、退款）→ 全量。达标不是一次性事件而是**在线监控下的持续条件**。

> 可直接复用 L2D 的评估指标（system accuracy、coverage、deferral cost）作为自动化程度的量化度量：coverage（自动处理占比）随采纳率提升而上升，即"渐进自动化"的量化曲线。

---

## 推荐模型设计（运营建议 → 人工采纳 → 自动执行）

**输入**：建议文本/结构化字段（动作类型、目标商品、参数）+ 上下文（店铺、时段、历史采纳率、操作成本、风险等级）。

**输出**：采纳概率 `P(采纳)`（标定后）+ 可选的"是否 defer"二值。

**模型**：
1. **轻量二分类头**（采纳/拒绝），backbone 用现有建议生成模型的 embedding 或特征工程（店铺历史采纳率、动作成本、时段等强特征）。
2. **损失函数**：deferral-aware / post-hoc 校正损失（Narasimhan et al. 2207.05830），或直接二分类 + 温度缩放校准，避免把人类错误动作当金标准。
3. **决策策略**：`自动执行 ⇔ P(采纳) 95% 下界 ≥ θ_execute 且 risk_level ≤ 门控`；否则 defer 给人工 review。θ 按动作成本分层。
4. **冷启动**：样本稀疏期用规则先验（如"改价=高危永远人工"）+ 校准置信度；随日志积累切换为学习式 deferral（LLM 先验 bandit 2406.19317 可加速）。
5. **闭环**：主动学习（2507.06537）挑最有信息量的建议人工确认 → 回写日志 → 更新模型与阈值 → 达标灰度放行。

**渐进路线**：阶段1 全人工（采集日志基线）→ 阶段2 纯建议（记录采纳率）→ 阶段3 采纳率达标 + 风险分层（低风险自动、高风险 defer）→ 阶段4 自动执行 + 在线监控回退。

---

## 证据来源

- [Consistent Estimators for Learning to Defer to an Expert（2006.01862）](https://arxiv.org/abs/2006.01862) / [GitHub clinicalml/learn-to-defer](https://github.com/clinicalml/learn-to-defer)
- [Who Should Predict? Exact Algorithms for Learning to Defer to Humans（2301.06197）](https://mlanthology.org/aistats/2023/mozannar2023aistats-predict/)
- [Post-hoc estimators for learning to defer to an expert（Google Research）](https://research.google/pubs/post-hoc-estimators-for-learning-to-defer-to-an-expert/)
- [Learning to Defer（survey, 2403.03870）](https://arxiv.org/pdf/2403.03870)
- [Learning to Partially Defer for Sequences（2502.01459）](https://arxiv.org/abs/2502.01459)
- [To Ask or Not to Ask: Learning to Require Human Feedback（2510.08314）](https://browse-export.arxiv.org/pdf/2510.08314)
- [When to Act and When to Ask: Deferral Under Hidden Confounding（NeurIPS 2024）](https://mlanthology.org/neurips/2024/ghoummaid2024neurips-act/)
- [Cascaded Language Models for Cost-Effective Human–AI Decision-Making（NeurIPS 2025）](https://papers.neurips.cc/paper_files/paper/2025/hash/10e0c427408ccc6e073d9464e2280f89-Abstract-Conference.html)
- [Is UQ a viable alternative to learned deferral?（Springer）](https://link.springer.com/chapter/10.1007/978-3-032-06593-3_4)
- [Incorporating uncertainty in LDU for safe CAD（Scientific Reports 2022）](https://link.springer.com/article/10.1038/s41598-022-05725-7)
- [Jump Starting Bandits with LLM-Generated Prior Knowledge（2406.19317）](https://arxiv.org/abs/2406.19317)
- [Neural Dueling Bandits（ICLR 2025）](https://mlanthology.org/iclr/2025/verma2025iclr-neural/)
- [Offline Safe Policy Optimization From Heterogeneous Feedback（2512.20173）](https://ar5iv.labs.arxiv.org/html/2512.20173)
- [Safe RL with Preference-based Constraint Inference（ICML 2026, 2603.23565）](https://icml.cc/virtual/2026/poster/66726)
- [A model-agnostic active learning for camera traps（2507.06537，本地已关联）](https://scirate.com/arxiv/2507.06537)
- [Learning to Rank for Active Learning via Multi-Task Bilevel Opt（UAI 2024）](https://mlanthology.org/uai/2024/ding2024uai-learning/)
- [Active Learning with Logged Data（1802.09069）](https://ar5iv.labs.arxiv.org/html/1802.09069)
- [Automation Bias/Anchoring 系统综述](https://zenodo.org/records/20641572) · [Calibrating Reliance（AAAI）](https://ojs.aaai.org/index.php/AAAI/article/view/41457) · [NEJM AI Trust/Scrutiny/Collaboration](https://ai.nejm.org/doi/abs/10.1056/AIe2600354)
- [Review Gates That Scale（Turing Pulse）](https://turingpulse.ai/blog/human-in-the-loop-design)
