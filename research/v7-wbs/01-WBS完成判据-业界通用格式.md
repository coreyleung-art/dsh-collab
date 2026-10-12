# R-M2 · 篇一 · 一个 WBS 项「做完了没有」——业界通用判据格式

> **出件**：v7 调研代理 R-M2 · 2026-10-12（+08:00）
> **题目**：业界怎么判「一个 WBS 项做完了」？特别是当该项是**治理机制**（如「审查门可跑」「信标在位」）而非代码时。
> **纪律**：本件所有引用**先现测**；★ 不照抄 v6.1 状态；★ 不得把「本机已有」写成「业界最新」。
> **★ 本件不主张任何事项闭合。**

---

## §0 一句话结论

**业界判「做完」不靠「声称」，靠一条可复跑的【三件式判据】：`正向谓词 ∧ 负控曾红 ∧ 边界不崩`，且判据的【执行者】必须不是【产出者】。**
本仓 §11 已经写出了这条规则的**等价物**（八字段 + 六者齐备），但它缺的不是「写法」，是 **①`dod.full_table` 从未落盘（分母为 0）②verifier 结构性缺席**。

---

## §1 复跑命令与原始输出（本件结论的全部来源）

### 1.1 现测：Σ WBS 编号（v6.1 自己的复跑命令）

```bash
cd /Users/coreyleung/dsh-collab
grep -oE 'W[0-9]+\.[0-9]+' docs/distributed-agent-network-governance-plan-v6.1-20261011.md | sort -u | wc -l
grep -oE 'W[0-5]\.[0-9]+' docs/distributed-agent-network-governance-plan-v6.1-20261011.md | sort -u | wc -l
```

**未编辑原始输出**：

```
      72
      39
```

**退出码**：`0`

★ **读数**：`W0–W5` 段**恰为 39**，与 §10 表头一致；全文唯一 W 编号 **72**（39 + W6×8 + W7×11 + W8×14 = 72，✓ 自洽）。
⇒ **「39 项」这个分母本身是可复跑的**（★ 这是 v6.1 里少见的一个**能红也能绿**的判据）。

### 1.2 现测：锚点 sha256

```bash
shasum -a 256 docs/distributed-agent-network-governance-plan-v6.1-20261011.md
```

**未编辑原始输出**：

```
bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3  docs/distributed-agent-network-governance-plan-v6.1-20261011.md
```

**退出码**：`0`

★ 与 `docs/v7-outline-revised-20261012.md:5` 自报值**逐字相同** ⇒ **锚点未漂**（阳性对照通过）。

### 1.3 现测：§11 的「八字段」表是否落盘

```bash
cd /Users/coreyleung/dsh-collab
grep -c "dod.full_table" docs/distributed-agent-network-governance-plan-v6.1-20261011.md
grep -n "dod.full_table" docs/distributed-agent-network-governance-plan-v6.1-20261011.md
```

**未编辑原始输出**：

```
1
1955:**实测：`dod.full_table` 仍为 `缺席`** —— v4 §11 正文表格只是代表性摘录，全文表从未落盘。
```

**退出码**：`0`

★ **读数**：v6.1 自认 `dod.full_table` **缺席**（`:1955`），我只查到**这一处自认**，未见全文表实体。
★ **★ 这正是「空 ≠ 无」的最干净例子**：39 项 WBS，**0 项**有落盘的完整 DoD ⇒ **不可判「有多少项有 DoD」**，**不得报「0% 有 DoD」**（那会把「没数过」读成「数过是 0」——与 v5 表头「30 vs 39」同族）。

---

## §2 业界判据格式：三件式

### 2.1 形式定义

| 要素 | 中文 | 判「做完」时的作用 | 业界名称与出处 |
|---|---|---|---|
| **① 正向谓词** | 可观察、可复跑的「必须为真」 | 只证**可能**，不证**做过** | **Verification**（ISO 9001:2015 设计开发控制；PMBOK/IEEE 定义见 [Verification and validation](https://en.wikipedia.org/wiki/Verification_and_validation)） |
| **② 负控曾红** | 必须有一条**输入使判据为红**，且**红过** | 无负例的判据不是判据 | **Mutation Testing / test adequacy**；本仓对标见 `docs/audit-criteria-industry-crosswalk.md` #2 → [arXiv 2212.06118](https://ar5iv.labs.arxiv.org/html/2212.06118) |
| **③ 边界不崩** | 0 条 / 1 条 / 超一页等边界**不崩且不可读作通过** | 防「空集通过」 | **Vacuous Truth / silent skip**；crosswalk #12 #15 |
| **④ 执行者 ≠ 产出者** | 判据的裁判必须是**独立第三方** | 自审在结构上不带信息 | **IV&V（Independent Verification and Validation）**；术语定义见上引维基条目「with 'independent', indicating that the verification and validation is to be performed by a disinterested third party」 |

### 2.2 「做完」在业界的两种不同含义 —— 本仓混用的根因

维基同一页逐字给出 ISO 9001:2015 的区分：

> 「**Validation** activities are conducted to ensure that the resulting products and services meet the requirements for the **specified application or intended use**. **Verification** activities are conducted to ensure that the design and development outputs meet the **input requirements**.」

中文对照：

| | 问的问题 | 本仓对应 |
|---|---|---|
| **Verification（验证）** | 「东西**造对了吗**」 | §11「六者齐备」「负控红」 |
| **Validation（确认）** | 「东西**管用吗**」 | **本仓几乎没有** —— M0 判据「新会话 ≤5 分钟恢复计划认知」是 validation 口径，而它靠的是 C4 |

★★ **⇒ 这是本仓「做了但没生效」（篇三）迟迟判不出的语言学根因**：本仓的判据体系是 **verification 面**的（代码在不在、门能不能跑），而 v6.1 真正要的 M0/M4 是 **validation 面**的（管不管用）。**两面的判据不可互相替代。**

### 2.3 治理机制类项的通用判据格式（★ 本件核心产出）

代码类项可以「跑一次看它红不红」；**治理机制类项**（审查门、信标、登记表、告警）多一层：**机制在位 ≠ 机制被用 ≠ 机制有效**。建议格式**四问**：

| # | 问 | 谓词形态 | 为什么必须有 |
|---|---|---|---|
| **Q1 在位？** | `实体存在` ∧ `可执行` ∧ `退出码 ∈ {0, 非0 有义}` | 可机器判 | ★ **在位是必要非充分**；「有尺没读者」即卡在 Q1 之后 |
| **Q2 曾红？** | `存在一条输入 ⇒ 该机制输出红` 且**有留痕** | 可机器判（若留痕） | **本仓纪律：「一个断言若从未红过，它就不是判据」** ⇒ Q2 是**判据资格的准入条件**，不是加分项 |
| **Q3 被用？** | `时间窗内命中数 > 0` ∧ `命中者 ≠ 作者` | 可机器判（需读日志） | 「建了尺没读者」= Q1 过、Q3 为 0 |
| **Q4 有效？** | `机制输出 → 下游动作` 的可追链路非空 | **只能人判或抽样** | 「写了告警没人读」= Q3 可能非 0（有人看见），Q4 = 0（看见了没动） |

★ **Q4 是最贵、也最常被跳过的**。业界名字见篇三。

### 2.4 判据格式的**反面**（本仓现成反例，★ 全部为现测）

| 反面 | 现测证据（可复跑） | 被判掉的要素 |
|---|---|---|
| **判据的命令面 ≠ 工具的 CLI 面** | W8.1 的 DoD 写 `cahac-envelope-conformance.py --status`，实跑 `exit=2`（篇四 §3） | ① 正向谓词**不可跑** |
| **门自证全绿而功能跑 FAIL** | 七件工具 `--selftest` 全绿；`gcr-gate.py` 无参实跑 `PASS 6 · FAIL 2 · N-A 9`，`exit=1`（篇四 §2） | ② 自证 ≠ 功能判据 |
| **同一份文件内三套口径** | §0.3「机械化 10 · N-A 7」vs 工具自述「11 条机械化」vs 实跑「非 N-A 8 · N-A 9」（篇四 §4） | ③ 阈值不可判 |

---

## §3 「三件式 + 四问」的落地模板（供 v7 每项填写）

```
项号：W<?>.<?>
① 正向谓词（可复跑）：<命令>  ⇒ 期望 <输出形>
   实测时刻：<ISO8601 +08:00>   实测输出：<原样贴>   退出码：<n>
② 负控：<构造输入的描述> ⇒ 期望【红】  留痕：<路径>  ★ 是否曾红：是/否
③ 边界：0 条 / 1 条 / 超限 三态 ⇒ <期望行为>   ★ 空分母时的判词：【不可判】（不得 OK）
④ 裁判（verifier）：<角色，非会话 id>  ★ 与产出者不同一
Q1 在位 / Q2 曾红 / Q3 被用 / Q4 有效：<四问逐答；未测写「未测」>
```

★ **填不出的格子必须留「未测」，不得留空** —— 留空会被读成「通过」。

---

## §4 阴性证据（★ 搜过什么、没搜到什么）

| 检索面 | 检索词 | 结果 |
|---|---|---|
| `docs/` + `research/` 的 `*.md` | `dod.full_table` | **1 命中**，且**仅为自认缺席**（`:1955`），**未搜到**全文表实体 |
| 同上 | `Definition of Done` 的中文/英文对照落盘 | **未搜到**本仓对业界 DoD 定义的引用 |
| 同上 | `IV&V` / `Independent Verification` | **未搜到**（本仓用「独立 verifier」自称，**未对上业界名**） |

★★ **未搜到 ≠ 不存在**：以上检索只覆盖 `docs/` 与 `research/` 的 `*.md`；**未覆盖** `notes/`、黑板键空间、`logs/`、KB、以及插件目录内的文档。★ 且本件**未检索黑板**（`curl 127.0.0.1:8792/...`）。

---

## §5 本件的限制（★ 如实标）

1. ★ 本件的业界出处以 **Wikipedia / 标准摘要页**为主，**非一手标准原文**（ISO 9001:2015 全文付费；IEEE 1012 未取到）。★ 与 `docs/audit-criteria-industry-crosswalk.md` §4 自陈的限度同族。
2. ★ 一次 `read_url` 取 NIST **SP 800-53A 失败**（`Fetch failed`），改由 CSRC 术语页取到定义；**未取到 SP 800-53A 正文**。
3. ★ 本件**未逐项实测 39 项 WBS**，只实测了**分母（39/72）**与**抽样若干**（篇四、篇五）。
4. ★ 本件**不主张**任何 WBS 项已完成或未完成。

---

*R-M2 · 篇一 fin · 2026-10-12 · 全部读数带【复跑命令 + 原始输出 + 退出码】*
