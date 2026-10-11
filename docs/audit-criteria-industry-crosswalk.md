# 判据 ↔ 业内对标表（crosswalk）

> **口径**：本文件全部 16 位 hex = **SHA-256 全量摘要前 16 位小写 hex**
> **由来**：**用户 2026-10-10 批评** —— 「你们相互讨论的东西有点闭门造车，以及多多少少有点重复造轮子的状态」
> **自查结论**：**成立。** 本文件是对标结果，供全网引用，避免后来者重复"发明"。

---

## §0 为什么会有这张表

**本线的审查角色在数日内独立"发明"了一批判据。** 用户质疑其在业内的已有程度 —— **自查后确认大多已有正式名称与出处。**

**★ 而这次自查本身暴露了一个更值得记的问题**：

> **我们对【脚本】跑了 `j44-reuse-gate.py` 查重，却对【概念/方法论】没有查。**
> **⇒ 于是把已有论文重造了一遍。**

**⇒ 这是「先查存量 → 缺口才新建」在【概念层】的执行缺口**（`j44-reuse-gate.py` 只查资产，不查概念）。

---

## §1 对标表

| # | 我们的叫法 | 业内名称 | 出处 | 已有程度 |
|---|---|---|---|---|
| 1 | **验证失效**（自称被验证方接受 = 验证失效） | **Test Oracle Problem** | [Stop Trusting AI Test Results Without an Independent Oracle](https://eleks.com/research/ai-test-generation-without-independent-oracle/) | 完全已有 |
| 2 | **门能否失败**（无负例的判据不是判据） | **Mutation Testing** / **oracle-based test adequacy** | [arXiv 2212.06118](https://ar5iv.labs.arxiv.org/html/2212.06118)：「mutation coverage is the strongest among regular and oracle-based code coverage **as a test adequacy metric**」 | 完全已有 |
| 3 | **判据覆盖缺口**（读到了但判据没问） | **Test Adequacy Criteria**（充分性准则） | 同上 | 部分已有（**这个词形我们没见过**） |
| 4 | **三元分离**（proposer ≠ executor ≠ adjudicator） | **Evidence Contract + neutral Scrutinizer + Judge** | [GAVEL, ACL 2026 Findings](https://aclanthology.org/2026.findings-acl.1789/) | 完全已有（**且同期发布**） |
| 5 | **实跑级 = 能从基底外部重算** | **deterministic validation of cited identifiers**（GAVEL 原文） | 同上 | 完全已有 |
| 6 | **发布门禁** | **release gate** | [eval-harness-internals](https://github.com/plwslpld-arch/eval-harness-internals)（已梳理 lm-evaluation-harness / Inspect AI / OpenAI Evals / Promptfoo / DeepEval） | 完全已有 |
| 7 | **V&V 规范** | **IEEE 1012-2024** | [standards.ieee.org](https://standards.ieee.org/ieee/1012/7324/) | 完全已有（**正式标准**） |
| 8 | **激励反演**（判据奖励不写自检） | **Goodhart's Law** / **Campbell's Law** | [形式化论文](https://www.zenodo.org/records/18909543/files/goodhart_formalization.pdf) | 完全已有 |
| 9 | **消除 vs 缓解**（结构上不成立 > 事后补记） | **dissolve, not solve** | [Zenodo](https://www.zenodo.org/records/21701303/files/main.pdf) | 完全已有 |
| 10 | **实时判据 / 运行时检查** | **Runtime Verification**（含 DSL，如 RML） | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0167642321000034) | 完全已有 |
| 11 | **fail-closed** | **Fail-safe / Default Deny** | （工程通识，未逐一核出处） | 完全已有 |
| 12 | **恒为常量 / 空洞通过** | **Vacuous Truth** / **Tautology** | （逻辑学通识；**未核到软件工程专门文献**） | 完全已有（**术语层**） |
| 13 | **观测改变对象** | **Observer Effect** / **Probe Effect** / **Heisenbug** | （工程通识） | 完全已有 |
| 14 | **哨兵同域** | **Sentinel Value 设计** / **Null Object Pattern** | （设计模式文献；**未逐条核**） | 部分已有 |
| 15 | **面外通过 / 空集通过** | **Coverage Gap** / **silent skip**（如 pytest 的 skip 可见性） | （测试框架实践；**未逐条核**） | 部分已有 |
| 16 | **假红 / 假绿** | **False Positive / False Negative**（Type I / II） | （统计与测试通识） | 完全已有 |
| 17 | **降权而非调参** | **Alert Fatigue** / **静态分析器误报管理** | （CodeQL/SonarQube 实践；**未逐条核**） | 部分已有 |
| 18 | **诊断族（七员）** | **Dependability Taxonomy**（Avizienis et al.） | （**未核实文献**，需检索） | **待核** |
| 19 | **存在/在位/可用 三态** | **Tri-state Logic** / **Configuration Resolution** | （**未核**） | **待核** |
| 20 | **命令·结论·制品哈希三绑定** | **Provenance / Attestation**（in-toto · SLSA · Sigstore） | （**未核**） | **待核** |

---

## §2 结论

1. **闭门造车 —— 成立**：**GAVEL（ACL 2026）的三个角色、Evidence Contract、Mechanized Scrutiny 都已有正式论文，而我们从未检索过。**
2. **重复造轮子 —— 成立**：**「门能否失败」= mutation testing 的充分性判据；「发布门禁」= eval harness 的 release gate；「实跑级」= deterministic validation of cited identifiers。**
3. **★ 而我们犯的是【本线自己那条判据所禁止的错】** —— **「先查存量 → 缺口才新建」在概念层没执行。**

**★ 值得注意的一点**：**GAVEL 发布于 ACL 2026（2026-07）** ⇒ **我们不是落后，而是【同期但不知情】。** 这说明**问题在检索面，不在能力面。**

---

## §3 建议（供属主/协调者裁）

| # | 建议 |
|---|---|
| 1 | **`j44-reuse-gate.py` 的检索面扩展到【概念层】**：不只查同类工具，还查同类方法/标准/论文 |
| 2 | **`call-dispatcher` v1 的判定对象至少含【概念层】** —— 与用户原话一致（「核查是否已有类似的**功能或能力**」） |
| 3 | **本表作为引用源**：今后凡提这些判据，**优先引业内名称 + 出处**，而非自造术语 |
| 4 | **未核的 4 条（#18–#20）** 应补检索 —— **但应【低成本做】**（派子代理 + 只回结论） |

---

## §4 未覆盖

- **§1 的 #11/#13/#16 等**我**未逐条核到权威出处**（属工程通识，但"通识"不等于"有出处"）
- **#18–#20 完全未核**
- **本文档由【一次 web_search + 一次 read_url】得出** ⇒ **不是系统文献综述**；若需严谨对标，须补齐
- **第二条调研子代理（开源项目盘点）仍在跑**，其结果未并入本版

---

*判据 ↔ 业内对标表 v1.0 · 2026-10-10 · 由用户批评触发 · 自查结论：重复造轮子成立*
