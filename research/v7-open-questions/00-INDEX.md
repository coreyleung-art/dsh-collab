# 00 · INDEX —— v7 未决问题（Q-A…Q-Q）调研产出

> **调研代理**：R-M7M8 · **工作目录** `~/dsh-collab`
> **取数时刻**：2026-10-12T19:5x–20:1x+08:00
> **锚点**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md`（**只读，未改**）
> **纪律**：★ 未改 `docs/` 下任何既有文件；★ 所有产出只写进 `research/v7-open-questions/`；★ **不代裁**；★ **不升格**（本件推断与本件判读均显式标注）。

---

## 一、篇目

| # | 文件 | ★ 一句话结论 |
|---|---|---|
| **01** | [`01-QA至QQ逐条可裁形态.md`](01-QA至QQ逐条可裁形态.md) | §15 的未决问题是 **17 条**（不是清点件里的 3 条、也不是「九条」）；**17 条里可裁 5、差一个定义或数据 7、不可裁 2、无需裁 1、问句已过期 2**；★ **且登记表与锚点对 Q-G/Q-P/Q-M 的状态已经分叉**。 |
| **02** | [`02-未决问题编号纪律-业界怎么管.md`](02-未决问题编号纪律-业界怎么管.md) | 业界的「先对表再编号」= **有名字的登记表 + 明写的分配策略 + 不得复用 + lint**（[RFC 8126 BCP 26](https://www.rfc-editor.org/rfc/rfc8126.txt) / [GDS Way](https://raw.githubusercontent.com/alphagov/gds-way/acc80bb8e30bca3c8823300a0d3a1637af99a691/source/standards/architecture-decisions.html.md.erb) / [AWS PG](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/best-practices.html)）；★ 本机只有**中间那句纪律**、**`Q-x` 无校验器**，★★ **而 `R-x`/`J-x` 的校验器 `scripts/rules-integrity.py` 现在正红着**（`exit=1`）。 |
| **03** | [`03-最优性怎么证-ADR与选型矩阵.md`](03-最优性怎么证-ADR与选型矩阵.md) | §3.1 已是一张**选型矩阵**（好），但缺 **ADR 的 Status/Consequences**、缺**权重**、缺**复跑命令**；★★ **现测：§3.1 的「799 行 / 41 PASS」数字仍然成立，但口径从未声明**（`journal_mode` 7 行 vs 10 次 · `claim` 40 行 vs 49 次），且**四代（v4/v5/v6/v6.1）逐字继承、无一版重测**。 |
| **04** | [`04-§3.4.3领先层-阴性证据与可复跑对照实验.md`](04-§3.4.3领先层-阴性证据与可复跑对照实验.md) | §3.4.3 的「保守」是**四条不可判叠加的必然措辞**（阴性不可证否 · 检索面不全 · 候选有表无数据 · 领先门未裁）；★ 要变成可复跑对照实验需 **6 件**，其中**最关键的一件是「阴性对照」**（已知存在的一条**必须命中**，否则该次检索作废）。 |
| **05** | [`05-W8.1信封尺鉴定与§3.4对照进度.md`](05-W8.1信封尺鉴定与§3.4对照进度.md) | ★★ `scripts/cahac-envelope-conformance.py` **是一把正当的尺，但不是 W8.1 说的那把** —— W8.1 提的 **4 条具名要求 0 条成立**（`--status` 不存在 `exit=2` · 无 `objects` 字段 jq `exit=5` · 打 14 项而非 10 · **没有「能绿」自测**）；★★ **它也不能替代 §12 的临时尺**（它是 HTTP 取数，读不了 `~/.dsh/inbox`）。 |
| **06** | [`06-若只能裁三条.md`](06-若只能裁三条.md) | 建议 **① Q-G+Q-L+Q-P 合并为一次「M0 是否成立」的裁** ② **Q-O（独立 verifier）** ③ **Q-Q（单一来源）** —— 三条合起来 = **「里程碑可判 + 读数可信」**；★ 明确列出**为什么没选 Q-B/Q-E/Q-C/Q-N**。 |

**证据留档**（`evidence/`）：
- [`evidence/R-M7M8-原始输出-20261012.txt`](evidence/R-M7M8-原始输出-20261012.txt) —— 12 组命令 + 未编辑原始输出 + 退出码
- [`evidence/Q-Q-本地副本vs板值-20261012.json`](evidence/Q-Q-本地副本vs板值-20261012.json) —— 逐键、逐条对照
- [`evidence/Q-x位置寻址演示-20261012.txt`](evidence/Q-x位置寻址演示-20261012.txt) —— 只读演示 + 源码寻址点

---

## 二、★★★ 最重要的三条发现（★ 全部现测，附复跑命令）

### 发现 1 · **§15 是 17 条，不是 3 条；且登记表与锚点已经分叉**

```bash
$ cd ~/dsh-collab && python3 -c "
import json; d=json.load(open('data/registry/continuity-index.json'))
print('open_questions 长度 =', len(d['open_questions']))"
open_questions 长度 = 17
[exit=0]
```
★ 清点件 M7 只抽到 **3 条**（`docs/v7-unfinished-inventory-20261012.md:97-101`）⇒ ★ **v7 若按它派工，会漏 14 条**。

★★ **分叉（同一批编号，两份件给不同状态）**：

| 编号 | v6.1 §15 | `continuity-index`（现测） |
|---|---|---|
| **Q-G** | 列入「状态未变（九条）」= 未决 | `state=answered` · 「2026-10-12 C4 已注入（6/6 预设）⇒ 本项解除」 |
| **Q-P** | 列入「v5 新增」= 未决 | `state=answered` · `voided=true` · 「用户 2026-10-12 裁：计划本身我都同意过了」 |
| **Q-M** | 「**状态：未决**」 | `status: fixed_pending_user_restart` · 「修复：两处 `inject=[]`（已只读验证）」 |

★ **现测佐证**：`~/.dsh/.agent-presets/` 下 **6/6** 个预设的 `agent.cordis.yml` 均含 `continuity-index` + 「开工三步」（`mtime` 2026-10-12 03:08–03:09）。
★★ **⇒ Q-G/Q-P 的「批准」事实上已经发生**，但**锚点仍写未决**；★ **而这两份件都没错到"该判假"的程度 —— 它们是两份不同时刻的登记**。★ **本件不裁谁为准。**

### 发现 2 · **「编号纪律」的机械判据在本机是【部分建成】的，而且现在正红**

```bash
$ cd ~/dsh-collab && python3 scripts/rules-integrity.py; echo "[exit=$?]"
规则账本完整性检查 · /Users/coreyleung/dsh-collab/rules-registry/RULES.md
  声明: v2.23.8 | 75 条
  实际: 76 个标题 / 76 个唯一编号
❌ 硬问题 1 项（账本不可信，须修）:
   · 计数不符: 声明 75 / 实际 76
⚠️ 提示 5 项:
   · 编号乱序: R047(行418) 出现在 R048(行411) 之后
   · 编号乱序: J38(行158) 出现在 J44(行152) 之后
结论: ❌ 账本存在硬问题 —— 依账本做的判断不可核，应先修复
[exit=1]
```
★ **R-x/J-x 有校验器（且现在红）**；★★ **Q-x 没有对应的全集校验器**（`grep -rln "open_questions" scripts/ tools/` ⇒ 5 个文件，**无一是全集一致性校验**）。
★★★ **更硬的一条**：`tools/qk-tracker-drift-check.py:26` **按位置寻址** —— `QK_INDEX = 10`（"open_questions[10] = Q-K"）。★ 只读演示：

```
现态 open_questions[10].id = Q-K
插入一条 Q-R 后 open_questions[10].id = Q-J      ← ★ 一次"插入新问"就悄悄读错对象
[exit=0]
```
★ **而 v7 的主要工作就是「新增编号」** ⇒ ★ **这个坑是 v7 必然踩的**，且**该工具自己的源码注释已写明这个风险**。

### 发现 3 · **W8.1 的尺按原文跑不通；且它没有「能绿」自测**

```bash
$ cd ~/dsh-collab && python3 scripts/cahac-envelope-conformance.py --status; echo "[exit=$?]"
cahac-envelope-conformance.py: error: unrecognized arguments: --status
[exit=2]
$ python3 scripts/cahac-envelope-conformance.py --json | jq '.envelope_ok/.objects'; echo "[exit=$?]"
jq: error (at <stdin>:31): number (0) and null (null) cannot be divided
[exit=5]
$ python3 scripts/cahac-envelope-conformance.py --selfcheck | tail -2
== 负控 5/5 ==
[exit=0]              # ← ★ 5 条全是「必须红」或结构自洽，★ 无一条是 W8.1 要求的「构造合法信封 ⇒ 必须能绿」
```
★★ **⇒ 它从未被证明过「能绿」。** ★ 而**本件补测：判决逻辑本身是能绿的**（用脚本同一 `all(f in v for f in req)`，合法信封 ⇒ `envelope_ok = 1/1`）⇒ ★ **能绿是源码的性质，不是判据** —— ★ **下一个人改坏 `req` 不会被发现。**

★ **修法极便宜**：`--status` 别名 1 行 · `objects` 别名 1 行 · 「能绿」自测 ~10 行 · 输出加时刻 1 行 ⇒ **约 15 行**。

---

## 三、★★ 未查到的部分（★ 如实列，★「未搜到 ≠ 不存在」）

| # | 未查到什么 | 影响哪一篇 | 为什么没查 |
|---|---|---|---|
| **1** | **`tools/` 面是否另有信封工具** | 05 | §3.4.6-⑤ 的原命令只查 `scripts/`；本件也只跑了 `scripts/` 面 ⇒ **未核 `tools/`** |
| **2** | **W8.1 的 owner（谁裁「改尺 vs 改规格」）** | 05 | 未在锚点/登记表找到 W8.1 的归属会话 |
| **3** | **「10 字段 vs 14 字段」的裁决记录** | 05 | `grep` 未命中；★ 三处（W8.1「10」/ §12 `REQ`「10」/ CAHAC §3「14」）**三方不一致** |
| **4** | **「领先三条件」的逐字原文** | 03 · 04 | 只找到 `:276`「未裁前不得记领先」与 `:1929` W8.14；★ **三条件按任务转述使用，已显式标注** |
| **5** | **第二支注入器的具名身份** | 01（Q-D） | `grep` 只命中名词、无实体 ⇒ ★ **Q-D 因此判为「不可裁」** |
| **6** | **Q-J 四项（板鉴权/A 类仓/meituan-multi/「-」仓）的展开** | 01（Q-J） | 全锚点 `grep` **仅 1 命中**（§15 那一行本身）⇒ ★ **不可裁** |
| **7** | **`beacon-check` 的「本地↔板值一致」是字段级还是规范化 sha 级** | 06（Q-Q） | 未读该判据实现 ⇒ ★ **若为字段级，它拦不住 B8/B9 那类不一致** |
| **8** | **Wave S「七件门」的具体名单** | 06（Q-O） | `docs/wave-s-toolchain-delivery-v1.md` 在位但**未逐字核七件** |
| **9** | **重复的时间跨度分布**（410 组重复的 Δt） | 01（Q-A） | 未测 ⇒ ★ **Q-A 选 (a)/(b)/(c) 的唯一决定性数据** |
| **10** | **端口引用面穷举** | 01（Q-B） | 只抽到 3 处硬编码（central-inbox `:44` · channel-matrix `:21` · node-bridge 命令行）⇒ **未穷举** |
| **11** | **威胁模型（机内 / 机外）** | 01（Q-E） | 未搜到成文件 ⇒ ★ **Q-E 裁不出正确方案** |
| **12** | **`§3.4.3` 的独立复检索** | 04 | ★ 本件**明确不重复检索**；只指出「缺什么才能升级」 |
| **13** | **`~/.dsh/inbox` 面在新尺下的读数** | 05 | ★ 新尺**取数是 HTTP**，**读不了文件系统**（`--ns $HOME/.dsh/inbox` ⇒ `UNDECIDABLE`）⇒ ★ 该面只有 §12 的内联 bash |
| **14** | **锚点 §3.1 的权重 / SQLite 的代价列 / Status 的裁决人** | 03 | 文件内不存在 |
| **15** | **`research/cost-governance/`（74 篇）与 `research/agent-comm-paths/`（28 篇）的逐篇通读** | 全部 | ★ **本件按需抽查**（CAHAC v1.2 §3/§7.4/§8.3、C0/C1-FINAL/E0 篇目），**未逐篇读** ⇒ ★ **不主张穷尽** |

★ **另有一处「未核」的自述必须留痕**：`compose-index-sync-local.py` 自述「**不取锁**（`agent_light`/`agent_lock` **本机不存在**）」；★ **本件实测这两个工具是存在的**（本会话可调用）⇒ ★ **该自述所指的「锁」与本机 agent-bus 锁**是否等价，本件未裁**，★ 如实标为疑点。

---

## 四、本调研自身的口径与限制

1. ★ **凡引 v6.1 读数者，本件都先现测**；★ 现测与原读数**不同的**已逐处标出（`notes/collab` 564→**618** · `~/.dsh/inbox` 2949→**3111** · `RULES.md` 声明 86→**75/76 不一致**）。
2. ★★ **「空 ≠ 无」**：本件所有「零命中」均**同时报出扫过的面**（如 `grep -rl "nats" docs/ scripts/ tools/` ⇒ **三面零命中**，不是「业界没有 NATS」）。
3. ★★ **「一个断言若从未红过，它就不是判据」**：★ 本件对**自己引用的关键判据**都给了「能否红」一栏（见各篇 §末「本件自证」）。
4. ★★★ **不升格**：★ **本件所有「可裁度」「建议选哪三条」「是不是 W8.1 的尺」均为本件判读**，**不是用户的裁定**，也**不是任何既有登记表的原话**。
5. ★★★ **不代裁归属**：★ 凡有 owner 的条目（Q-A=CLD · Q-I=**裁判** · Q-K/Q-M=外部第三方 · Q-L=CLD 新会话 · Q-O/Q-P/Q-Q=用户/裁决方），**本件只报状态与选项，不填答案**。
6. ★ **本件不主张任何一条已闭合**（S3）。
