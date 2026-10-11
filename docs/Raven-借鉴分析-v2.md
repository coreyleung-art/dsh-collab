# Raven (The Harness of Harnesses) → CLD/DSH 借鉴分析 v2

> 调研日期：2026-09-28 · 一手材料：技术报告 PDF（82 页，全文读取）+ 官方 README/文档站 + HarnessBank arXiv 2607.13683 + EverOS DSH 插件 README
> 沉淀：`wiki/research/raven-harness-of-harnesses.md` · `raw/research/2026-09-28-raven-harness-of-harnesses/`（12 份）
> 本地基线实测：`~/dsh-plugin-*`（25）· `~/.dsh/.agent-presets/`（4）· `~/.dsh/skills/`（16）

---

## 0. v2 更正记录（先读，v1 有四处错误）

技术报告全文（82 页）读完后，**v1 的四处论断被证伪或需大幅收紧**：

| # | v1 的说法 | 报告实际 | 影响 |
|---|---|---|---|
| **C1** | "四道门：有效性 → 激活 → 显著性 → 增益" | 论文 §3.3 是**三道门** `g_scn = g_valid × g_act × g_sig`，增益门是**通过后进完整训练集再比**，不在同一合成式里。"四道门"是媒体通俗转述 | 中：协议本体不变，数字要改 |
| **C2** | 把 Curator 当作 Raven 的核心机制来引用 | **"Curator" 在报告全文 0 次命中**。报告 §4 是**离线、基准驱动**的 Evolver（Diagnosis-Driven Harness Evolution + Harness Gene Bank）。Curator 只出自 README | **高**：证据强度差一个量级 |
| **C3** | "四类内容 = 模块/代码/提示/策略" | **两个不同的四元组被我混成一个**：① **四策略接口** `h=(id,Mem,Plan,Cap,Act;θ)`（Eq.39）；② **四类编辑位置** `W_edit = {prompt, knowledge, runtime, config}`（Eq.45）。报告 §4.3 p26 明文："These edit categories are **distinct** from the four strategy roles" | **高**：混轴会让基因库坐标失去意义 |
| **C4** | "对应大脑皮层/海马的类比" | 报告 **0 处**提到 cortex/brain/hippocampus。此说法出自媒体（c114 / 雷峰网） | 中：属于**厂商叙事**，非论文 |

**连带结论**：Raven 的证据链**全部集中在离线 Evolver + 封存测试**上；"运行时自进化（Curator）"是路线图宣传，报告未为其提供任何证据。**不要把运行时自我修改当作已有结论来建设。**

---

## 1. 一句话结论

Raven 经得起检验的不是"agent 自己改自己"，而是三件事：**① 把 harness 形式化成可寻址的策略空间；② 把多 agent 协作变成带准入检查的显式 DAG；③ 把每次"改进"都压在「分母不缩水 + 测试集封存 + 配对显著性」三道门上**。而我们的 `guard_archaeology` + `repair-reports` 已经是第 ③ 条需要的原料，只差坐标轴和两道门。

---

## 2. 现状映射：我们已有一个 harness，只是没被形式化

Raven 把 harness 形式化为 `H = K ∪ X`（不可变内核 ∪ 可变面）：
`H(X_edit) = {h : Exec(h)=Exec(Apply(h0,Δpatch)), scope(Δpatch)⊆X_edit, h|K_fixed = h0|K_fixed, InterfaceValid(h)=1}`（Eq.42）
——**允许改的位置、保护的位置、接口合法性，三者必须先声明**，否则"自我修改"无因果可言。

对照我们实测的 DSH preset（`~/.dsh/.agent-presets/liangshen/agent.cordis.yml`，326 行，注释自述 **"This file is an AGENT-PLANE composition"**）：

| Raven 概念 | DSH 已有对应物 | 状态 |
|---|---|---|
| Memory 座席（本轮可见） | `contexts` 注入 + `tool-bootstrap` pre-step | ✅ 已有，未命名 |
| Planning 座席 | `dsh-persona` + `plan:policy` + 相位切换 | ✅ 已有，未命名 |
| Capability 座席 | `tools` 注册 + Code Mode (PTC) `run_code` | ✅ 已有，未命名 |
| Action 座席 | tool envelope + sandbox + approval 栈 | ✅ 已有，未命名 |
| Assembly Root | `base.cordis.yml` + `web.cordis.yml` + preset | ⚠️ 有等价物，缺 Generation 概念 |
| 不可变内核 K | `guard_*` 红线清单 | ⚠️ 是纪律，非机制 |
| **Evolver**（离线门控） | `guard_compliance` 五道闸 + `guard_archaeology` | ⚠️ 形似，**缺统计门** |
| **Curator**（运行时） | —— | ❌ 空白（且报告不支持，见 C2） |

**判断**：四座席在我们这里**物理存在**，只是没被当作"可独立替换的座席"设计，也没有内核/可变面边界。Raven 的价值是**给已有的东西命名并加边界**。

---

## 3. 最高价值洞察：我们已有一个未完工的 HarnessBank

基因库用 **(WHERE × WHY)** 二维坐标存档 `B_r : W_edit × Y_fail → H(X_edit) ∪ {⊥}`（Eq.45）：

- **WHERE ∈ {prompt, knowledge, runtime, config}** —— 改在哪，**由实际改动的文件机械推导，绝不采信自我声明**（实现名 `bind_where`；自我声明的 `patch_where` 只入账审计）
- **WHY = 失败病理类** —— **"Pathology labels remain hypotheses, not established causes"**（§4.3 p26）。因为 WHY 只决定"试哪个候选"，信用完全来自门控，**标错标签最多浪费一个候选，永不产生坏 harness**
- **同格竞争只留最优，跨格可重组**；且明确承认重组**不可加**："their gains need not be additive"，组合必须重新评估
- **反直觉设计**：存档准入与父代选择**用不同比较**——"A candidate can outperform its parent on the screening subset yet fall below it on the full training set"

对照我们的：

| 我们已有 | 缺什么 |
|---|---|
| `guard_archaeology` 的 **M1 遮蔽 / M2 物化 OOM / M3 重启竞态 / M4 插件协议 / M5 凭旧认知 / M6 不验证** | 这就是 **WHY 分类器雏形** —— 但只用于统计，不用于导航 |
| `repair-reports` 双目录历史修复报告 | 这就是**候选档案** —— 但按时间线性存放，无语义坐标，无法重组 |
| `guard_compliance`（P2 红线→P0 预查→P1 备份→P4 沙箱→P5 有界→pre-mortem） | **没有一道是统计门**，全靠纪律 |

**结论**：把 `guard_archaeology` 的 WHY 轴接上机械推导的 WHERE 轴，`repair-reports` 按坐标入库，我们就得到一个跑在**真实生产故障**上的 HarnessBank——比论文跑基准更有价值，因为输入是真实病理。

---

## 4. 三道门：我们缺的正好是第 2 和第 3 道

论文 §3.3–4.4 的三道门（**不是四道**，见 C1）：

| # | 门 | 判据（论文原式） | 我们的现状 |
|---|---|---|---|
| 1 | **有效性门** `g_valid` | `I[Log 协议合法]`；基础设施故障（沙箱崩溃/验证器超时）触发**修复重试**，而非计为 agent 失败 | ✅ `cld_health_check` + `guard_deps_scan` + `session_recovery_check` |
| 2 | **激活门** `g_act` | `I[ΣᵢΣ_k active_{i,k} > 0]`——提案**在评估前固定** activation predicate，运行时确定性上报"机制真的执行过" | ❌ **完全空白** |
| 3 | **显著性门** `g_sig` | 配对差 `γᵢ = s̄ᵢ(候选) − s̄ᵢ(父代)`，`t_pair = γ̄/(se) ≥ 1.96`；**先对 K 次取平均，测量单位是"任务"，样本量 n 而非 n·K** | ❌ **完全空白** |

**增益要求**（不在合成式内，在完整训练集阶段）：必须胜过**固定的 vanilla 基线**，不是上一个父代。

**消融证据（最该记住的数字）**：去掉显著性门后，**收敛后轮次中 62%–76% 是"幻影进展"**，循环只能在轮次上限处停下；带完整门控的版本能在 **10 轮下限**干净退出。另有反例：**无门控的 DGM 在 Omni-MATH 上部署了比 vanilla 更差的版本（−1.1%）**——"an ungated loop can deploy a regression"。

**四条必须照抄的纪律**：
1. **分母不可缩水**："Agent failures remain scored outcomes and cannot be removed from its `|D|·K_att` denominator"（§4.2 p26）。污染任务计 0，**不剔除**；Gate-f 只报告污染清单。
2. **测试集封存**："Test outcomes do not revise proposals, thresholds, archive cells, or the selected harness"（p28）。**机械断言 `assert_no_test_leak`，泄漏在启动时直接 raise**。
3. **晋级 ≠ 显著**：`promoted`（导航用）与 `credited_2sigma`（论文用）是**两个独立字段**。官方原话："A promoted candidate can have `credited_2sigma: false`; that is **not proof** of a statistically significant improvement."
4. **激活门是弱证据（照抄其诚实）**：这是**存在级、呈现级归因**——只证明"某段被插桩的代码跑过"，**不证明它位于机制的触发条件内，也不建立因果贡献**；"an **unconditionally-placed beacon degrades Gate-b to a no-op**"。

---

## 5. 编排层可直接搬的五个细节

| 机制 | 出处 | 为什么值得抄 |
|---|---|---|
| **分阶段披露编排指南** | §3.1 p13–14 | 完整编排规则放每轮上下文会产生**恒定输入成本**。Raven 每轮只带**短描述**，需要多 agent 时才指示加载完整指南并 **pin** 在会话里；**被拒的图返回"校验错误 + 指南指针"**。→ 直接可用于我们的 skill catalog 与 Guard SOP 注入 |
| **节点产物落盘 + 记忆异步** | §3.3 p19 | "Artifact completion therefore releases dependencies, while memory recording proceeds **asynchronously**"。产物 `prompt.md/out.md/transcript/memory.json`，后继按路径读。最省 token、最可审计 |
| **依赖域路径传播** `Paths_v = {MemPath(u) : u ∈ Anc(v)}` | §3.3 p20 Eq.32 | 给有能力读文件的节点追加**传递前驱的记忆路径**，"without eagerly copying all ancestor memories into its prompt"。→ 我们有黑板/文件系统，天然适配 |
| **澄清请求 host autofill** | §3.2 p17–18 | subagent 反复问"要什么格式"是最常见的 token 浪费。host 用「问题 + 会话快照 + EverOS 召回」先代答；**仅当用户明确说过或召回唯一确定答案时才答**；**永不代答审批类请求**（push/delete/send/pay） |
| **判官（Verdict）外置** | §3.2 p16 | "An **independent model call** therefore judges each finished node"；负判**必须给出类别与证据**；判官失败按可用性回退视为完成（官方承认这是**可用性权衡而非正确性证明**） |

**编排参数（Appendix B.3 Table 10 p74）**：共享并发 8（私有回退 5）· 派发预算 30/小时 · 判官超时 180s · 轨迹尾部 8,000 字符 · 每节点 continuation 2 · 挂起决策截止 600s。

---

## 6. 记忆与技能：四个可直接照搬的设计

| 设计 | 出处 | 要点 |
|---|---|---|
| **Markdown 权威源 + 索引可丢弃** | §5.5 p34 | "EverOS stores episodes, facts, profiles, cases, and skills as **Markdown records**. SQLite 维护运维态，派生索引支持检索。**The Markdown records can be used to rebuild the search index.**" → 我们有 Obsidian + ChromaDB 两层，正好是这个形状，但**需要补"Markdown 为权威、索引可丢弃"的硬约定**，否则两层会漂移 |
| **召回两段拼接 + 围栏** | §5.4 p33 Eq.65 | `MemContext(q) = Archive(q) ++ Fence(Recall(q))`；召回内容标记为**不可信上下文数据**。Archive 取"与消息词法重叠最大的 2 个 profile 段 + 全部 Notes" |
| **RRF 两级分离** | §6.2 Eq.71–72 | "**RRF determines expansion order, while calibrated scores determine final relevance**"；名字分组用**精确名折叠**（不做语义等价），代表选择才比原生分。→ 多源技能融合可直接照搬；注意它**不解决同义技能** |
| **fail-open + 防递归自捕获** | DSH 插件 README | 已由 EverMind **官方发布给 DSH**（`@everos-ai/dsh-plugin`）。两条设计无论装不装都该进我们的 `knowledge-tools`：① 记忆后端故障**只记日志，绝不拒绝用户的 turn**；② 召回围栏 token 在注入前**被中和**，插件生成的上下文**永不**被当作直接输入再捕获；原始推理与图片字节刻意排除 |

**DSH 插件三阶段生命周期**：Recall（每轮开始，user/agent 双轨并行搜索）→ Capture（每轮停止边界，**不调 LLM**，durable 追加到 SQLite buffer）→ Flush（idle 30s / token 12000 / 消息 50 / 最大延迟 300s / 会话切换 / 关闭，批量抽取）。默认 `recallMethod: keyword`（Tier 1 安全默认）。

---

## 7. 分层行动建议

### A 级 — 立即可做

**A1. 给 Guard 加"激活门"⭐ 最高杠杆**
`guard_compliance` 增 `guard_activation_check`：修复类改动声明并植入可检索信标 → 验证阶段检查**运行中是否真的触发** → 未触发 = `pruned_inert`，**不得入库**。必须同时记录其局限（存在级归因 ≠ 因果；无条件信标 = 空操作）。

**A2. 给 `guard_archaeology` 加 WHERE 轴**
产出 `~/.dsh-collab/archaeology/gene-bank.json`：`(WHERE, WHY) → 最优修复`，同格竞争留最优、跨格可重组。**WHERE 从实际改动文件机械推导**；自我声明只入账审计。

**A3. 给 subagent / workflow 加 Verdict**
我们目前"subagent 返回即算完成"。对关键派发加独立模型裁决（读「渲染后 prompt + 输出 + 轨迹尾部」），负判必须给类别与证据；异常走 continue / abandon / replan。

**A4. 抄 DSH 记忆插件的两条设计**（见 §6 第 4 行）；装与不装 EverOS 都该做。

**A5. 分阶段披露 SOP 注入**（§5 第 1 行）——把 Guard R006 全文 + 规则账本从"常驻注入"改为"短菜单 + 按需加载 + 错误驱动补课"。

### B 级 — 需建设

**B1. harness 形式化切分（K / X）**
- **内核 K**：`guard_*` 全部门控 + 验证器 + RULES 执行器 + archaeology 记账 + `repair_report`
- **可变面 X**：persona / tools / skills / injection / config（`agent.cordis.yml` 可编辑部分）
- `guard_check_writable` 从"红线清单"升级为**内核路径白名单 + 写入拒绝**

**B2. 候选改动走 git 子提交，不原地覆盖**
Raven `commit_files_as_child`：候选落为**真实 git 子提交**，**主工作树与 HEAD 保持不动**；评估在 `work_dir/tmp` 临时 worktree 做。我们目前是 `guard_backup`（滚动 2 个 good 态）+ 原地改写。

**B3. 配对显著性工具化**
`paired_sig.py`：输入两组逐任务配对得分 → 输出 Δ̂、σ̂_δ、t、是否 ≥1.96。用于 waimai 改价/折扣、prompt/skill 改动等一切我们声称"变好了"的地方。

**B4. 密封测试纪律**
train/test 不交叠 + **机械化断言在启动时 raise**；**最终交付物按训练分选，绝不在候选里挑测试分最高的**；报告 `retention = test lift ÷ train lift`；照抄诚实条款——小 n 下真实效应也可能不过门（论文 SWE-bench n=26 时 +5.2% 仍被判 preliminary）。

**B5. Charter 收窄语义**——agent-bus 派发补"**只做交集、永不扩大**"的 scope：只能收窄工具集/缩短 deadline。注意官方自承 "Charters are **not an OS sandbox or a fail-closed security boundary**"。

**B6. 澄清 autofill（永不代答审批）**——见 §5 第 4 行。

### C 级 — 明确不建议抄

| 项 | 判断 | 依据 |
|---|---|---|
| **直接依赖 Evolver** | ❌ | 官方 `evolver/README.md` 标记该树"**for planned retirement**"；"registers **AppWorld only**"；"**not a full-scale multi-round run**" |
| **运行时 Curator 式自改** | ⚠️ **降级** | 报告 0 命中；README 自述 **experimental**，"ships with the repository rather than the installed package"。**报告的证据链支撑不到运行时自改**（见 C2） |
| **SkillHub 11 万技能** | ❌ | 供应链风险；官方自承"目录安全分**不是**安全保证"、缺失评分**不触发拒绝** |
| **A2A / ACP** | ❌ | 我们 agent-bus 更强；官方自承 A2A task store **内存态重启即丢**、不支持 push、`CancelTask` **不保证副作用回滚** |
| **DAG 的持久性** | ❌ | 官方自承"DAGs **do not provide** a durable, distributed task queue"、**history recovery is not automatic execution resumption** |
| **分组共享记忆（§3.4）** | ❌ | 报告原文："**Group memory is disabled by default and is not evaluated in this report.** Its effect ... **remains to be established**" |

---

## 8. 一条值得内化的纪律：给每个论断标注"实际含义 + 局限"

Raven 文档最反常识的优点是其**诚实度**。原文摘录：

- "a **receipt** is not proof of task success"
- "Gate-b proves **a** beacon executed, not that the beacon sat inside the mechanism's trigger condition"
- "this is an experiment protocol, **not an operating-system access barrier**"
- "Candidate/round caps are **not a hard currency spending limit**"
- "The Curator is **experimental**"；参考答案剥离只是 "**limits** how directly the answer is exposed"
- "Treat that as the **documented evidence boundary**, not a claim of production readiness"
- "The utility in Eq.(43) contains **no implicit cost penalty**"
- "**Lexical filtering alone cannot rule out paraphrased planning cues**"
- AI4AI 结论标注 **n=1**（"Each system ran one campaign"）

我们已有 **R030 无验证不陈述**。Raven 给的是**格式**：每个能力声明附一张「声称 → 实际含义 → 限制」对照表。建议在 Guard 报告 / repair report / 能力登记中采用这个三段式。

---

## 9. 优先级路线图

| 阶段 | 动作 | 预期收益 |
|---|---|---|
| **P0** | A1 激活门 + A3 Verdict | 堵住"改了个寂寞"与"假完成"两类漏洞 |
| **P1** | A2 (WHERE × WHY) 基因库 + A4 防递归捕获 | 修复知识可复用/可重组；记忆健壮性 |
| **P1** | A5 分阶段披露注入 | 砍掉常驻注入的恒定 token 成本 |
| **P2** | B3 显著性工具 + B4 密封测试纪律 | 声称"变好"时有统计底气 |
| **P2** | B1 内核/可变面切分 + B2 git 子提交 | 自我修改可回滚、可审计 |
| **P3** | B5 Charter + B6 澄清 autofill | 委派权限只减不增；省 token |

---

## 10. 参考来源

- [EverMind-AI/Raven](https://github.com/EverMind-AI/Raven) — 官方仓库（Apache-2.0，**pre-alpha**）
- [Raven 文档站](https://evermind-ai.github.io/Raven/) — 架构 / 编排 / Playbooks / Permissions / Evolver / self-evolution-map
- [HarnessBank 论文 arXiv 2607.13683](https://ar5iv.labs.arxiv.org/html/2607.13683) — 三门的公式、消融、跨模型匹配律
- 技术报告 PDF（82 页，`tech-report-v1`）— §2 形式化 / §3 编排 / §4 自进化 / §5 记忆 / §6 技能 / §7 评测 / Appendix B.3 默认值
- [EverOS DSH 插件](https://github.com/EverMind-AI/plugins/tree/main/dsh) — 官方 DSH 记忆插件
- 本地沉淀：`wiki/research/raven-harness-of-harnesses.md` + `raw/research/2026-09-28-raven-harness-of-harnesses/`

**一句话**：Raven 真正经得起检验的是 **① harness 形式化为可寻址策略空间、② 多 agent 协作变成带准入检查的显式 DAG、③ 每次晋级都压在「分母不缩水 + 测试集封存 + 配对显著性」三道门上**。Curator / Persona 是产品层叙事，**报告本身没有为其提供证据**。
