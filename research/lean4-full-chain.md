# Lean 4 全链路调研（R025 R1）：语言 · 类型即证明 · AlphaProof · 工具链 · 落链

> 调研角色：数据调查员调研子代理 ｜ 产出时间：2026-09-01 ｜ 状态：R1 完成
> 目标衔接：R027 自动化开关锁「Lean4 类型锁」——用 Lean 依赖类型系统把安全不变量编码进类型，由内核机制级强制。

---

## 结论

Lean 4 是「交互式定理证明器 + 通用编程语言」的统一体，基于**依赖类型理论**，以**最小可信内核**（minimal trusted kernel）对所有证明做机器校验，是当前形式化数学与 AI 数学推理的主流载体（mathlib4 约百万行形式化数学库）。**Curry-Howard 对应**（命题即类型、证明即程序）是它可靠性的机制根源：一个「证明」只是一个类型正确的程序项，内核只做类型检查，无法伪造、无法旁路——这正是 R027「Lean4 类型锁」可以做到**机制级保证**（而非运行时检查）的理论基础。**AlphaProof**（DeepMind，2024.7 首秀，2025.11 Nature 公开全技术细节）证明 Lean 环境 + 强化学习可以在 IMO 达到奖牌级（4/6 题、银牌 28 分，改进版达金牌水平），其核心引擎就是「在 Lean 里把证明当游戏打」。工具链成熟且**本地可装**（elan 版本管理器 + lake 包管理器 + VS Code 扩展，macOS 一条命令），工业界已有 AWS Cedar（授权语言验证）、DeepMind、Harmonic 等实战。落链：5 篇核心 arXiv 论文已入 paper-cache 与 KB，详见文末。

---

## Lean4 原理

### 是什么
- **定义**：Lean 4 是一个交互式定理证明器（interactive theorem prover, ITP）兼编程语言，由 Leonardo de Moura（微软研究院 → 2023 年成立 Lean Focused Research Organization, Lean FRO）主导开发。
- **理论基础**：依赖类型理论（dependent type theory，Martin-Löf 风格，支持商类型 quotients、单射构造类型），类型可以依赖值（如 `Vector α n`、`Fin n`），使「数据 + 性质」能合一编码。
- **最小可信内核**：一切证明最终由内核校验。内核只做一件事——**类型检查**（约数千行、独立实现、不依赖外部库）。「绝对正确性」来自：你无法构造一个类型错误却声称是证明的项。官网原话："Lean's minimal trusted kernel guarantees absolute correctness in mathematical proof, software and hardware verification."
- **元编程**：Lean 4 最重要的设计是**自举**——元程序（tactic、notation、elaborator）全部用 Lean 本身编写（Lean 3 用 C++ 写）。这让社区能无限扩展证明自动化与领域特定语法。
- **运行时**：编译为 C，引用计数 GC（"Counting Immutable Beans"），性能接近常规编译语言，可作通用语言使用。

### 与 Lean 3 的差异
| 维度 | Lean 3 | Lean 4 |
|---|---|---|
| 元编程 | C++ 宏展开/外部 tactic | 完全自举，Lean 写 Lean（hygienic macro，IJCAR 2020） |
| 定位 | 数学证明器为主 | 证明器 + 通用编程语言统一（do notation 局部命令式，ICFP 2022） |
| 运行时 | 解释器/虚拟机 | 编译为 C，引用计数 GC，性能大幅提升 |
| tactic 模式 | 内建 tactic 集合 | tactic 即元程序，可完全自定义/编程 |
| 内核 | 较复杂 | 更精简；支持商类型、更干净的环境检查 |
| 数学库 | mathlib3（~100 万行） | mathlib4（mathport 工具迁移，2021–2023 完成，现持续增长） |
| 社区协作 | Zulip + GitHub | Zulip（leanprover-community）+ GitHub 同构，规模更大 |

### 社区与生态
- **mathlib4**（leanprover-community/mathlib4）：社区驱动的巨型数学库，约 100 万行 Lean 代码；2025 年有系统论文《Growing Mathlib: maintenance of a large scale mathematical library》（arXiv:2508.21593）。
- **协作**：Zulip chat 是主要交流场所；年度会议 ITP / CADE / FSCD / Lean Together。
- **机构**：Lean FRO（维护 Lean 4 本体）、leanprover-community（mathlib 与工具）、Microsoft Research（历史）、AWS/DeepMind/Harmonic（工业用户）。
- **著名形式化成果**：球面定理、多项式 FLT（Mason–Stothers）、格罗滕迪克消失定理、卡普雷卡问题等；Kevin Buzzard 团队在 mathlib 中推进费马大定理相关代数学基础。

---

## Curry-Howard 类型即证明

### 对应关系
**命题即类型（propositions as types）；证明即程序（proofs as programs）。** 形式化表述：

| 逻辑（命题） | 类型论（类型/项） |
|---|---|
| 命题 P | 类型 P |
| 证明 π : P | 程序/项 π : P |
| 蕴含 P → Q | 函数类型 P → Q |
| 合取 P ∧ Q | 积类型 P × Q |
| 析取 P ∨ Q | 和类型 P ⊎ Q |
| 全称 ∀x, P(x) | 依赖函数类型 Π x, P(x) |
| 存在 ∃x, P(x) | 依赖对类型 Σ x, P(x) |
| 假 ⊥ | 空类型 Empty |

- 历史谱系：Curry（组合子逻辑，1930s–50s 类型思想）→ Howard 1969《The formulae-as-types notion of construction》→ de Bruijn AUTOMATH（1968，首个证明检查器）→ Martin-Löf 类型论 → Coquand 归纳构造演算（Coq）→ 现代 ITP（Lean/Agda/Coq/Isabelle）。
- 经典综述：Philip Wadler, *Propositions as Types*, CACM 2015（"Proofs are Programs"）。在 Lean 里：`theorem t : P := proof_term` 中 `P` 是一个 `Prop`（= 一种 Type），`proof_term` 是构造该类型的程序项。

### 为何形式化验证可靠（机制级保证）
1. **证明不可伪造**：没有「测试充分」的说法——一个证明必须是一个**类型正确的项**，由内核逐项检查；任何分支、任何 case 都必须在类型检查时被覆盖。
2. **内核即信任边界**：整个系统只需信任内核（以及显式声明的公理 axiom）。metaprogramming/tactic/自动化生成的都是「候选证明」，全部要过内核这一关——**生成过程不可信，校验过程可信**。
3. **无法旁路**：Lean 不支持在证明中调用 unsafe 绕过内核；未声明的公理即错误。类型锁因此是「编译期/内核级强制」，不是运行时断言。
4. **与 LLM 的关系**：LLM 生成的证明可以错，但**内核会拒绝**——这正是 AlphaProof 可靠性来源，也是「Proof-Carrying Certificates for LLM Pipelines」（arXiv:2605.16407 方向）的思想：用证明携带正确性，而非信任生成器。

### 衔接 R027「Lean4 类型锁」
「类型锁」= 把安全不变量**编码进类型**，让不合法的状态在构造时就不可表示：
- 例：用 `Fin n` 代替 `Nat` 做数组下标（越界不可表示）；用 `Satisfies spec` 证明值携带规格；用 `NonEmpty` 避免空列表操作。
- 开关锁自动化：锁状态机（locked/unlocked 及转移条件）建模为归纳类型，`unlock : Locked → Key → Unlocked` 这类函数签名即规则——**错误的转移在类型层面就不存在**，自动化 agent 无法构造非法状态，因此是机制级保证而非事后检查。这比运行时断言/策略审计强一个层级：违反不变量 = 类型错误 = 编译失败。

---

## AlphaProof

### 是什么
- Google DeepMind 的 AI 数学证明系统，**用 Lean 驱动**：把数学证明变成 RL 可训练的游戏环境。2024 年 7 月宣布在 IMO 2024 达到银牌级（首次 AI 达到任何奖牌级），2025 年 11 月 Nature 刊发完整技术论文《Olympiad-level formal mathematical reasoning with reinforcement learning》（DOI: 10.1038/s41586-025-09833-y，约 10 人核心团队，IMO 金牌得主 Miklós Horváth 为关键成员）。

### 原理（Nature 论文 + 官方技术披露）
1. **证明即游戏**：基于 Lean 构建 RL 环境——每个数学命题是一个「关卡」，动作 = 选择 tactic；tactic 成功推进得到新子目标，全部子目标完成 = 证明完成。
2. **证明网络**：30 亿参数 encoder-decoder transformer，输入当前证明状态，输出 (a) 候选 tactic 建议，(b) 估计还需多少步（作 value function 引导搜索与算力分配）。
3. **搜索**：AlphaZero 启发树搜索 + **AND-OR 树**（多个独立子目标分解并行攻克）+ 渐进采样（关键路径探索更多策略）。
4. **训练数据**：约 3000 亿 token 代码+数学文本预训练 → 用 mathlib 约 30 万人写证明微调学会 Lean 语法 → **自动形式化**：基于 Gemini 1.5 Pro 的翻译系统把约 100 万道自然语言数学题转成约 8000 万道 Lean 形式化问题（远超所有既有数据集）。
5. **主 RL 循环**：约 8 万 TPU 天；成功证明/反证/超时全部成为经验回馈更新网络。
6. **测试时 RL（TTRL）**：对难题现场生成约 40 万个变体（简化、推广、类比），为这道题单独跑一个 AlphaZero 式学习进程，逐步积累解原题的洞察；每道题约 2–3 天算力（远超人类 9 小时，但已是里程碑）。

### IMO 2024 成绩
- 系统总成绩 28/42，**银牌级**；解决 4/6 题：AlphaProof 解出代数+数论 P1、P2、P6（P6 为全场最难题，609 名选手中仅 5 人解出），AlphaGeometry 2 解出几何 P4。
- 比赛期间 TTRL 后台继续跑，三天后 3 个完整证明陆续完成——2025 年报道称改进版已到**金牌水平**；此后 DeepMind 向科学家开放试用。
- 数学家实测反馈（Nature 报道）：Alex Kontorovich 发现其擅长**找反例**（快速指出陈述漏洞）；Talia Ringer 的博士生两个引理，一个 1 分钟内证出、一个被**反证**（原定义有漏洞）；Kevin Buzzard 用它翻译费马大定理证明时，在「大量自定义定义」处受挫。

### 局限与启示
- 依赖 Lean 的持续演进（环境不稳定）；数学题数据有限（RL 需要自生成问题）；对 mathlib 已有概念强、对全新定义弱。
- **启示（与 R027 直接相关）**：AI 生成 + 形式化校验 = 可靠性闭环。AlphaProof 之所以可信，不是因为模型强，而是因为**每个「成功」都过了 Lean 内核的机制级检查**——这为「自动化 agent 操作开关锁」提供了同样的信任模型：agent 可以自由尝试，内核/类型层裁决。

---

## 工具链与实战

### 工具链（本地可装性确认）
| 组件 | 说明 | 来源 |
|---|---|---|
| leanprover/lean4 | 核心仓库（实现 + 标准库） | GitHub |
| **elan** | Lean 版本管理器（类 rustup），`curl -fsSL https://elan.lean-lang.org/elan-init.sh | sh` | github.com/leanprover/elan |
| **lake** | Lean 包管理器（lakefile.toml 声明依赖），随 elan 安装 | lean-lang.org 文档 |
| **lean4-cli** | Lean 4 库：配置 CLI、解析命令行参数（`leanprover/lean4-cli`） | GitHub |
| VS Code 扩展 | `leanprover.vscode-lean4`（infoview 实时显示目标/状态） | marketplace |
| 中文教程 | leanprover.cn（安装 + elan/lake 工具链指南） | 中文社区 |

- **本机现状**：`~/.elan` 不存在、`which lean` 无输出 → **当前未安装，但 macOS 可装**（elan 官方安装脚本 + `elan default stable` 即可；随包自带 lake）。
- 标准工作流：`lake new myproj` 建项目 → `lake build` 编译并跑内核校验 → VS Code 中交互式证明。

### 实战案例（Lean 驱动形式化验证）
- **AWS Cedar（官方公开案例）**：开源授权语言，驱动 Amazon Verified Permissions / AWS Verified Access；AWS 用 Lean 形式化验证 Cedar 核心组件，并把生产 Rust 代码对 Lean 形式化做连续测试（Byron Cook / Emina Torlak 引语）。
- **Google DeepMind AlphaProof**：见上节（Pushmeet Kohli：Lean 的可扩展性与验证能力是 AlphaProof 的关键）。
- **Harmonic**：Tudor Achim（CEO）宣称以 Lean 为基础的「数学超级智能（MSI）」将服务航空航天、汽车、医疗等安全攸关行业。
- **Lean4Lean**（arXiv:2403.14064）：用 Lean 验证 Lean 自身的类型检查器——自举式内核可信度论证。
- **mathlib 大规模数学**：数学界协作形式化（Terence Tao 公开背书）。
- **LLM 输出验证**：Proof-Carrying Certificates for LLM Pipelines（arXiv:2605.16407）等——用 Lean 证明携带 LLM 流水线正确性。
- **专利/领域分析形式化**：Formally Verified Patent Analysis via Dependent Type Theory（混合 AI + Lean 流水线，arXiv:2510.17829 引用 Lean）。
- **R027 衔接**：本研究的「自动化开关锁」即 Lean 类型锁的落地场景——用依赖类型把锁状态机与权限规则编码，自动化 agent 的操作在类型层被约束（见 Curry-Howard 节）。

---

## 论文清单（arXiv ID，供落链）

| arXiv ID | 标题 | 主题 | 落链状态 |
|---|---|---|---|
| (CADE 2021, DOI 10.1007/978-3-030-79876-5_37) | The Lean 4 Theorem Prover and Programming Language（de Moura & Ullrich） | Lean 4 本体（会议论文，无 arXiv） | 引用 CADE DOI |
| 2202.01344 | Formal Mathematics Statement Curriculum Learning（Polu, Han, Zheng 等；含 miniF2F benchmark） | 专家迭代 + Lean 自动证明；miniF2F 基准 | ✅ 已落链 |
| 2306.15626 | LeanDojo: Theorem Proving with Retrieval-Augmented Language Models | 检索增强证明（Lean 数据/基准） | ✅ 已落链 |
| 2403.14064 | Lean4Lean: Verifying a Typechecker for Lean, in Lean | 自举内核验证 | ✅ 已落链 |
| 2502.03544 | Gold-medalist Performance in Solving Olympiad Geometry with AlphaGeometry2 | AlphaGeometry2（金牌级） | ✅ 已落链 |
| 2508.21593 | Growing Mathlib: maintenance of a large scale mathematical library | mathlib4 运维/规模 | ✅ 已落链 |
| (Nature 2025, DOI 10.1038/s41586-025-09833-y) | Olympiad-level formal mathematical reasoning with reinforcement learning | **AlphaProof 主论文**（非 arXiv） | 引用 Nature DOI |
| (Nature 2024, DOI 10.1038/s41586-023-06747-5) | Solving olympiad geometry without human demonstrations | AlphaGeometry 1（非 arXiv） | 引用 Nature DOI |

相关补充（可选后续落链）：Ebner et al., A metaprogramming framework for formal verification, ICFP 2017；Ullrich & de Moura, Beyond Notations: Hygienic Macro Expansion, IJCAR 2020 / LMCS 2022；Ullrich & de Moura, 'do' unchained, ICFP 2022；Proof-Carrying Certificates for LLM Pipelines, arXiv:2605.16407；GFLean: An Autoformalisation Framework for Lean via GF, arXiv:2404.01234。

---

## 官方文档源

- Lean 官网（What is Lean / 引语墙）：https://lean-lang.org/
- Theorem Proving in Lean 4（TPiL4 教科书）：https://lean-lang.org/theorem_proving_in_lean4/
- Functional Programming in Lean：https://lean-lang.org/functional_programming_in_lean/
- Lean Language Reference：https://lean-lang.org/doc/reference/4.19.0/
- GitHub：leanprover/lean4 · leanprover-community/mathlib4 · leanprover/elan · leanprover/lean4-cli
- 社区/Zulip：https://leanprover-community.github.io/ （archive + blog）
- 中文：https://www.leanprover.cn/ （安装 + 工具链教程）

---

## 证据来源

**Lean 4 本体与官方**
- https://lean-lang.org/ （最小可信内核、Tao/Cook/Kohli/Achim/Torlak 引语）
- https://lean-lang.org/doc/reference/4.19.0/Introduction/
- https://github.com/leanprover/lean4 （doc/setup.md）
- https://github.com/leanprover/elan · https://github.com/leanprover/lean4-cli
- https://www.leanprover.cn/tutorial/elan-lake/ · https://www.leanprover.cn/install/
- dblp（Ullrich 论文年表：CADE 2021 / IJCAR 2020 / ICFP 2022 / FSCD 2024）
- https://dl.acm.org/doi/10.1007/978-3-030-79876-5_37 （Lean 4 主论文，CADE 28）

**Curry-Howard**
- Wadler, Propositions as Types, CACM 2015: https://cacm.acm.org/research/propositions-as-types/
- Howard on Curry-Howard（Wadler blog）: https://wadler.blogspot.com/2014/08/howard-on-curry-howard.html
- Cornell CS 3110 Curry-Howard 讲义: https://cs3110.github.io/textbook/chapters/adv/curry-howard.html
- Harvard CS 152 讲义: https://groups.seas.harvard.edu/courses/cs152/2021sp/lectures/lec15-curryhoward.pdf

**AlphaProof**
- Nature 主论文: https://www.nature.com/articles/s41586-025-09833-y （摘要 + 方法与成绩细节）
- DeepMind 博客（IMO 2024 公告）: https://deepmind.google/blog/ai-solves-imo-problems-at-silver-medal-level/
- 36氪/量子位（Nature 技术细节中文解读，含 3B 参数/8000 万题/TTRL 细节）: https://www.36kr.com/p/3551243830589575
- ODSC（AlphaProof 原理概述）: https://opendatascience.com/alphaproof-and-alphageometry-2-solve-advanced-math-problems/
- Tom Zahavy 博客（开发过程）: https://www.tomzahavy.com/post/how-we-achieved-an-imo-medal-one-year-before-everyone-else

**mathlib / 生态**
- Growing Mathlib: https://arxiv.org/abs/2508.21593
- mathlib4 README: https://github.com/leanprover-community/mathlib4
- Lean4Lean: https://arxiv.org/abs/2403.14064
- LeanDojo: https://arxiv.org/abs/2306.15626
- miniF2F / FMS-CL: https://arxiv.org/abs/2202.01344
- AlphaGeometry2: https://arxiv.org/abs/2502.03544

---

*落链记录：2026-09-01 将 2202.01344、2306.15626、2403.14064、2502.03544、2508.21593 五篇写入 research/paper-cache/ 并索引到 KB（paper-cache 集合）。AlphaProof 与 AlphaGeometry 为 Nature 论文（无 arXiv），以 DOI 引用。*
