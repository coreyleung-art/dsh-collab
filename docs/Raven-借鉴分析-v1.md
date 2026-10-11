# Raven (The Harness of Harnesses) → CLD/DSH 借鉴分析 v1

> 调研日期：2026-09-28 · 一手材料：Raven 官方 README/文档站/插件 README + HarnessBank arXiv 论文
> 沉淀：`wiki/research/raven-harness-of-harnesses.md` · `raw/research/2026-09-28-raven-harness-of-harnesses/`
> 本地基线实测：`~/dsh-plugin-*`（25 个）· `~/.dsh/.agent-presets/`（4 个）· `~/.dsh/skills/`（16 个）

---

## 0. 一句话结论

Raven 值得抄的**不是自进化**，而是**"如何证明一次改进是真的"这套验证协议**——而我们的 `guard_archaeology` + `repair-reports` 已经是这套协议需要的原料，只差 (WHERE × WHY) 坐标和两道缺失的门。

---

## 1. 现状映射：我们其实已经有一个 harness，只是没被形式化

Raven 把 harness 形式化为 `H = K ∪ X`（不可变内核 ∪ 可变面），并把 Agent 循环拆成**四个解耦策略座席**：Memory（本轮看到什么）/ Planning（如何着手）/ Capability（开放哪些工具）/ Action（做什么 + 执行前判断）。

对照我们实测的 DSH preset 结构（`~/.dsh/.agent-presets/liangshen/agent.cordis.yml`，326 行，注释明确写着 **"This file is an AGENT-PLANE composition"**）：

| Raven 座席 | DSH 里已存在的对应物 | 状态 |
|---|---|---|
| Memory（本轮可见） | `contexts` 注入 + `tool-bootstrap` 的 pre-step 消息 | ✅ 已有，未命名 |
| Planning | `@deepseek-ai/dsh-persona` + `plan:policy` + phase 切换 | ✅ 已有，未命名 |
| Capability | `tools` 注册 + Code Mode (PTC) `run_code` 切换 | ✅ 已有，未命名 |
| Action | tool envelope + sandbox + approval 栈 | ✅ 已有，未命名 |
| Assembly Root | `base.cordis.yml` + `web.cordis.yml` + preset 组合 | ⚠️ 有等价物，缺 "Generation" 概念 |
| **Curator**（运行时自进化） | —— | ❌ 空白 |
| **Evolver**（离线门控进化） | `guard_compliance` 五道闸 + `guard_archaeology` | ⚠️ 形似，缺统计门 |

**核心判断**：我们的 `agent.cordis.yml` 本身就是一个声明式 harness 定义，四座席已经物理存在，只是没有被当作"可独立替换的座席"来设计，也没有内核/可变面的边界。Raven 的价值在于**给这套已有的东西命名并加上边界**。

---

## 2. 最高价值洞察：我们已有一个未完工的 HarnessBank

HarnessBank 的语义基因库用 **(WHERE × WHY)** 二维坐标存档：

- **WHERE ∈ {prompt, knowledge, runtime, config}** — 改在哪，**由实际改动的文件机械推导，绝不采信自我声明**（论文实现名 `bind_where`）
- **WHY = 失败病理类** — LLM 假设，**非真值**；因为 WHY 只决定"试哪个候选"，信用完全来自门控，所以**标错标签最多浪费一个候选，永不产生坏 harness**

对照我们现有的：

| 我们已有 | 缺什么 |
|---|---|
| `guard_archaeology` 的 **M1 遮蔽 / M2 物化 OOM / M3 重启竞态 / M4 插件协议 / M5 凭旧认知 / M6 不验证** | 这就是一个 **WHY 分类器**雏形 —— 但只用于统计，不用于导航 |
| `repair-reports` 双目录历史修复报告 | 这就是**候选档案** —— 但按时间线性存放，没有语义坐标，无法重组 |
| `guard_compliance`（P2 红线→P0 预查→P1 备份→P4 沙箱→P5 有界→pre-mortem） | 形似门控，但**没有一道是统计门**，全靠纪律 |

**结论**：把 `guard_archaeology` 的 WHY 轴接上机械推导的 WHERE 轴，再把 `repair-reports` 按坐标入库，我们就得到了一个跑在**真实生产故障**上的 HarnessBank——比论文跑基准测试更有价值，因为输入是真实病理。

---

## 3. 四道门：我们缺的正好是第 2 和第 3 道

HarnessBank 的 Gated Harness Screening 按顺序过四道门（论文公式见 arXiv 2607.13683 §3.3）：

| # | 门 | 判据 | 我们的现状 |
|---|---|---|---|
| 1 | **有效性门** Gate-valid | 评估产出协议完整；基础设施故障（沙箱崩溃/验证器超时）触发**修复重试**而非计为 agent 失败 | ✅ `cld_health_check` + `guard_deps_scan` + `session_recovery_check` |
| 2 | **激活门** Gate-act | 候选改动必须携带 `activation_beacon()`，运行时确定性上报"这段代码真的执行过了"；**从未触发的改动 = inert（惰性）** | ❌ **完全空白** |
| 3 | **显著性门** Gate-sig | 配对差 δᵢ = s(候选) − s(父代) 逐任务算，z = Δ̂/(σ̂_δ/√n)，**z ≥ 1.96** | ❌ **完全空白** |
| 4 | **增益门** Gate-gain | 必须超过**固定的 vanilla 基线**（不是上一个父代） | ⚠️ 部分（我们比"上一版"） |

**消融证据（这是最该记住的数字）**：去掉显著性检验门后，**收敛后轮次中 62%–76% 是"幻影进展"**，循环只能在轮次上限处停下；而带完整门控的版本能在 10 轮下限干净退出。

**官方诚实声明（照抄其纪律）**：
- 激活门是**"存在级归因"**——只能证明*某个*信标执行过，**不能**证明该机制是增益原因；**无条件放置的信标会让激活门退化为空操作**。
- Gate-b 无仪表数据时 **fail-open**（绝不误杀一个无仪表但诚实的候选）。
- **绝不缩减报告分母**——基础设施污染的任务计 0 分留在分母里，不剔除。

---

## 4. 分层行动建议

### A 级 — 立即可做（低成本、高杠杆）

**A1. 给 Guard 加"激活门"⭐ 最高杠杆**

现有 `guard_compliance` 五道闸扩为六道，新增 `guard_activation_check`：
- 修复类改动必须声明并植入可检索的信标（如一个特定的日志标记 / 一个计数器键）
- 验证阶段检查信标是否**在真实运行中被触发**，未触发 = `pruned_inert`，**不得入库**
- 必须同时记录其局限：存在级归因 ≠ 因果归因；无条件信标 = 空操作

**A2. 给 `guard_archaeology` 加 WHERE 维度**

把二维坐标真正建起来：
- WHY 轴：沿用 M1–M6，允许扩展
- WHERE 轴：{prompt, knowledge, runtime, config}，**从实际改动的文件路径机械推导**
- 产出 `~/.dsh-collab/archaeology/gene-bank.json`：`(WHERE, WHY) → 最优修复方案`，同格竞争只留最优，跨格可重组
- 论文的 `bind_where` 纪律：**自我声明的 WHERE 只入账审计，绝不决定坐标**

**A3. 给 subagent / workflow 加 Verdict**

Raven 原话：**"一个正常的进程返回本身并不充分"**。我们目前 subagent 完成即算完成。建议：对关键派发加一层模型裁决（检查返回结果是否真的完成了 prompt），异常走 continue / abandon / replan 三选一。

**A4. 抄 DSH 记忆插件的两条设计**（即使不装 EverOS）

`@everos-ai/dsh-plugin` 是 EverMind **官方发布给 DSH 的插件**，最低成本采纳路径是直接装；但其中两条设计无论装不装都该进我们的 `knowledge-tools` / `openchronicle`：
- **fail-open**：记忆后端故障只记日志，**绝不拒绝用户的 turn**
- **防递归自捕获**：召回内容围栏标记为"不可信历史证据"，且**存储的围栏 token 在注入前被中和**；插件生成的上下文**永不**被当作直接用户输入再捕获；原始模型推理与图片字节刻意排除

### B 级 — 需建设（中等成本）

**B1. harness 形式化切分（内核 / 可变面）**

- **不可变内核 K**：`guard_*` 全部门控 + 验证器 + RULES 执行器 + archaeology 记账 + `repair_report`
- **可变面 X**：persona / tools / skills / injection / config（即 `agent.cordis.yml` 的可编辑部分）
- 落地方式：`guard_check_writable` 从"红线清单"升级为**内核路径白名单 + 写入拒绝**；参考 Raven 的 *candidate edits are constrained to a per-bench path whitelist, an immutable kernel protects the measurement surface*

**B2. 候选改动走 git 子提交，不原地覆盖**

Raven 的 `commit_files_as_child`：候选编辑落为**真实的 git 子提交**（`evolver refs` 锚定防 gc），**主工作树与 HEAD 保持不动**；评估在 `work_dir/tmp` 下的临时 worktree 里做。
对照：我们现在是 `guard_backup`（滚动保留 2 个 good 态）+ 原地改写。建议对自我修改类操作改用 git 子提交 + worktree。

**B3. 配对显著性门（统计工具化）**

写一个小工具 `paired_sig.py`：输入两组逐任务配对得分（候选 vs 基线），输出 Δ̂、σ̂_δ、z、是否 ≥1.96。用于：
- waimai 改价 / 折扣效果
- prompt / skill 改动效果
- 任何我们声称"变好了"的地方

**B4. 密封测试集纪律**

- train / test **不交叠**，并用**机械化断言在启动时抛出**（Raven: `assert_no_test_leak` raises at startup）
- **最终交付物按训练分选，绝不"在候选里挑测试分最高的"**
- 报告 `retention = test lift ÷ train lift`
- 诚实条款：小 n 下真实效应也可能不过 2σ 门槛（论文 SWE-bench n=26 时 +5.1% 仍 z=0.78，被标为 preliminary）

**B5. Charter（任务宪章）收窄语义**

我们 agent-bus 的派发已有 `agent_lock` + 审批。补一层"**只做交集、永不扩大**"的 scope：被派发的 worker 只能收窄工具集 / 缩短 deadline，**不能**恢复被禁用的工具或延长已配置的 deadline。

### C 级 — 长期 / 明确不建议抄

| 项 | 判断 |
|---|---|
| **Curator 式运行时自进化** | 概念值得借鉴，但我们的插件 + 热重启（R035 热重启优先）已能承载半自动版本。**建议先做"人工在环的 Persona 编译器"**：自然语言描述 → 生成 preset（主角色 + 从已有 agent 抽专家 + 工具范围 + 行动前检查），落盘为可复用 preset 目录。我们现有 4 个 preset 全是手写的。 |
| **直接依赖 Evolver** | ❌ **不要**。官方 `evolver/README.md` 已标记该树"计划随 vendored fork 一并退役"，明确"不构成长期支持承诺" |
| **引入 SkillHub 11 万技能目录** | ❌ 供应链风险。官方自己警告"目录安全分不是安全保证"，且缺失评分在当前策略下**不是硬拒绝** |
| **A2A / ACP 协议** | ❌ 不必抄。我们 agent-bus 更强，且 Raven 文档自承 A2A **task store 是内存态、重启即丢**、push notification 不支持、非流式不保证逐 token |
| **DAG 编排的持久性** | ❌ 不必抄。Raven 自承"DAGs 不提供持久分布式任务队列"、**history recovery is not automatic execution resumption**；我们黑板 + agent-bus 队列在这点上不弱 |

---

## 5. 一条值得内化的纪律：给每个论断标注"实际含义 + 局限"

Raven 文档最反常识的优点是其**诚实度**。原文摘录：

- "a **receipt** is not proof of task success"（回执不等于任务成功）
- "Gate-b proves *a* beacon executed, not that the beacon sat inside the mechanism's trigger condition"
- "this is an experiment protocol, **not an operating-system access barrier** against arbitrary code"
- "Candidate/round caps are **not a hard currency spending limit**"
- "Treat that as the **documented evidence boundary**, not a claim of production readiness"

我们已有 **R030 无验证不陈述**。Raven 给的是**格式**：每个能力声明后面附一张"实际含义 / 重要限制"对照表。建议在高风险文档（Guard 报告、repair report、能力登记）里采用这个三段式：**声称 → 实际含义 → 限制**。

---

## 6. 优先级路线图

| 阶段 | 动作 | 依赖 | 预期收益 |
|---|---|---|---|
| P0 | A1 激活门 + A3 Verdict | 无 | 堵住"改了个寂寞"与"假完成"两类漏洞 |
| P1 | A2 (WHERE × WHY) 基因库 | A1 | 修复知识可复用、可重组，替代时间线性检索 |
| P1 | A4 fail-open + 防递归捕获 | 无 | 记忆插件健壮性 |
| P2 | B3 配对显著性工具 + B4 密封测试纪律 | 无 | 声称"变好"时有统计底气 |
| P2 | B1 内核/可变面切分 + B2 git 子提交 | 需先划内核路径 | 自我修改可回滚、可审计 |
| P3 | B5 Charter | agent-bus 改造 | 委派权限只减不增 |
| P3 | C 级 Persona 编译器 | 需 Curator 式概念 | 手写 preset → 一句话生成 |

---

## 7. 参考来源

- [EverMind-AI/Raven](https://github.com/EverMind-AI/Raven) — 官方仓库（Apache-2.0，pre-alpha）
- [Raven 文档站](https://evermind-ai.github.io/Raven/) — 架构 / 编排 / Permissions / Playbooks
- [HarnessBank 论文 arXiv 2607.13683](https://ar5iv.labs.arxiv.org/html/2607.13683) — 四道门公式、消融、跨模型匹配律
- [EverOS DSH 插件](https://github.com/EverMind-AI/plugins/tree/main/dsh) — 官方 DSH 记忆插件
- 本地沉淀：`wiki/research/raven-harness-of-harnesses.md` + `raw/research/2026-09-28-raven-harness-of-harnesses/`（12 份一手材料）
