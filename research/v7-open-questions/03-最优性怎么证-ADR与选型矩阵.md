# 03 · 「最优性」怎么证？—— 业界标准做法 vs 本机 §3.1 现测

> **作者**：调研代理 R-M7M8 · 2026-10-12 · 全程现测
> **本件回答**：本机 §3.1 自称「SQLite/WAL 为**当前最优**」。★ **业界标准做法是什么**？★ **本机差在哪**？

---

## §0 §3.1 被查的原话（逐字引，不转述）

锚点 `docs/distributed-agent-network-governance-plan-v6.1-20261011.md:355-363`：

> ## 3.1 L1 载体：SQLite/WAL 为当前最优
> | 候选 | 崩溃安全 | 并发/claim | 语言中立 | 运维重量（1 vCPU/957MB） | 有界手段 | 我们已有 | 判定 |
> |---|---|---|---|---|---|---|---|
> | **SQLite+WAL（既有 L1）** | 强（WAL+`BEGIN IMMEDIATE`） | 事务级 claim | **已实证** | **零**（嵌入式） | `expires_at`+vacuum/覆盖式 | **799 行+41 PASS** | ✅ **最优** |
> | append-only JSONL 分片 | 中 | 弱（需自造锁/claim） | 强 | 零 | 需自造 rotation | 无 | ⚠️ 次优（先前误选，已废弃） |
> | NATS JetStream | 强… | consumer ack | 强 | **+1 进程**；★限额默认 unlimited | MaxAge/MaxMsgs+Nats-TTL | 无 | ⚠️ 备选（L2/规模化；**必须显式设限额**） |
> | Redis Streams | 中 | XACK+XAUTOCLAIM | 强 | +1 进程 | `MAXLEN ~`/`XTRIM ACKED`（默认不裁） | 无 | ⚠️ 备选 |
> | Kafka compaction | 强 | 分区消费 | 强 | 重（JVM） | **体积上界=key 空间** | 无 | ❌ 过重 |
> | CRDT | — | — | — | — | **无天赋**（eg-walker：图单调增长） | 无 | ❌ 不解决有界 |

★★ **★ 先说一句公道话**：**这张表本身已经是一张「技术选型矩阵」**（候选行 × 判据列）—— ★ **它已经比「拍脑袋选一个」强得多**。本件要问的是：**它够不够叫「最优」？**

★ 相关的**本仓自定纪律**（锚点 `:276` 逐字）：
> 保持领先 L-1/L-2 | **§12 业界面 + §15 开放项 2** | **投入顺序待用户裁；未裁前不得记领先**

★ **其「三条同时满足才可记领先」的表述**（任务给出，★ 本次在锚点内**未逐字找到该三条件的成文原文**；找到的是上面这句 + §3.4.3 的处置）—— ★ **如实标：三条件的具体措辞本件未取到原文，按任务转述使用。**

---

## §1 业界标准做法（五件，逐件给一类来源）

### 1.1 **ADR / 决策记录** —— 有名字、有状态、有后果

**来源**：
- [Michael Nygard · Documenting Architecture Decisions（2011）](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [UK GDS Way · Documenting architecture decisions（英国政府数字服务标准）](https://raw.githubusercontent.com/alphagov/gds-way/acc80bb8e30bca3c8823300a0d3a1637af99a691/source/standards/architecture-decisions.html.md.erb)
- [AWS Prescriptive Guidance · Best practices for using ADRs](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/best-practices.html)
- [MADR v3（adr/madr 官方仓库）](https://raw.githubusercontent.com/adr/madr/refs/heads/release/v3/docs/index.md)

**GDS Way 逐字**（五段，**含 Consequences**）：

> **Title**: A description of the decision (not the problem) · **Status**: eg **Proposed, Accepted, Superseded** · **Context**: The facts behind the need to make the decision · **Decision**: What the team has decided to do · **Consequences** — **Both positive and negative consequences** of the decision

**AWS Prescriptive Guidance 逐字**：

> **Preserve ADR history.** … change the status of the old ADR to **Superseded**, note their changes in the change history of the new ADR, and **keep the old ADR in the decision log**. … **Address non-compliant code.** The ADR process doesn't solve the issue of non-compliant legacy code.

★ **⇒ 与 §3.1 对照（四条差距，逐条）**：

| # | 业界 ADR 要素 | §3.1 现状 | 后果 |
|---|---|---|---|
| ① | **Status**（Proposed / Accepted / Superseded） | ★ **无**（表格里只有「判定」列：✅最优 / ⚠️次优 / ❌过重） | 「最优」是**结论**，但**它处于什么状态**读不出来：是**提案**？是**已接受**？★ 而 §3.1 是**已按它施工过的**（既有 L1 已建成 799 行）⇒ **最可能的真状态是「Accepted」**，★ **但文件里没写** |
| ② | **Consequences（正反两面）** | ★ **无** —— 表格**只写好处**（"零运维"/"已实证"），**没有一列写 SQLite 的代价** | ★★ **这是最实质的缺口**：SQLite 的真实代价（**单写者锁** / WAL 文件增长 / 跨设备**不能直接用** ⇒ 必须配 L2 信封）**一处未写**。⇒ **读者会以为选它是免费的** |
| ③ | **Superseded 的旧 ADR 保留** | ★ **有一条先例**：「append-only JSONL 分片 … ⚠️ 次优（**先前误选，已废弃**）」★ **保留在表内** | ✅ **这条本机做对了**（**不删旧选项**） |
| ④ | **Context（事实依据）** | ⚠️ **部分** —— 「799 行+41 PASS」是一个**数字**，**不是一条复跑命令** | ★ 见 §2：★ **数字本身可复现，但复现它的【口径】未写** |

### 1.2 **选型矩阵 / 加权决策矩阵（Trade Study）** —— 要有**权重**，不只是列

**来源**：[NASA Systems Engineering Handbook（NTRS 官方 PDF，trade study 章节）](https://ntrs.nasa.gov/api/citations/19930011999/downloads/19930011999.pdf)

★ **通例（源自系统工程实践）**：trade study 的三件事 —— ① **准则（criteria）** ② **权重（weights）** ③ **每候选每准则的评分与依据**。
★ **⇒ 与 §3.1 对照**：

| trade study 要素 | §3.1 现状 |
|---|---|
| 准则 | ✅ **有 6 列**（崩溃安全/并发·claim/语言中立/运维重量/有界手段/我们已有）★ **列选得相当好** |
| **权重** | ★ **无** —— 「运维重量」与「有界手段」孰重？**没写**。★ **后果**：别人换一套权重就能选出 NATS（若把「跨设备」权重拉高） |
| **每格的可复跑依据** | ⚠️ **部分** —— 有些格是实测（799 行+41 PASS），有些格是**断言**（「强」「已实证」「零」）★ **未附命令** |

★ **⇒ 结论 1.2**：★ **§3.1 的**「唯一性最强**的一格是「语言中立 = **已实证**」（Rust/Python/Node 并发写同一 DB 400/400，integrity ok）—— ★ **这一格是真实验**；其余格多为**判断**。★ **本件不否证表，只指出：这张表里有实验的只有一格。**

### 1.3 **基准（benchmark）的可复现三件** —— 命令 + 口径 + 时刻

★ **通例**：一个 benchmark 结果若无 ① **命令** ② **口径**（分子分母/环境） ③ **时刻**，**它不可复跑**。
★ ★ **本仓自己就有这条纪律**（`§3.4.6` 前言逐字）：「**数字凡会随编辑变化者，以复跑命令代替写死值**」；`CAHAC §1.5.4 :108`：「**判据不落在命令上，就等于没核**」。
★ **⇒ 与 §3.1 对照**：★ **§3.1 没给任何复跑命令** ⇒ **它自己的纪律没被用在自己身上**（★ 这是本件最直接的一条发现）。

### 1.4 **可证伪性（falsifiability）与「领先」的门**

★ 本仓的**优良实践**（值得点名）：`§12` 有 **W8.14「『领先项』的证伪条件」**（`:1929` 逐字）：
> 产出**可证伪命题 + 检索词清单 + 检索面声明**，交第三方复检；★ **证伪前不得在 v6 写「领先」结论**

★ **⇒ 这是本机自己发明的、且与业界一致的机制**（可证伪命题 + 检索面声明 + 第三方复检）。
★★ **但「最优」没有对应的 W 项。** ★ 现测：
```bash
$ cd ~/dsh-collab && grep -n "证伪" docs/distributed-agent-network-governance-plan-v6.1-20261011.md | head
1929:| **W8.14** | **「领先项」的证伪条件**（本轮唯一候选：成本权重入选择器，属**阴性证据**） | 产出**可证伪命题 + 检索词清单 + 检索面声明**，交第三方复检；★ **证伪前不得在 v6 写「领先」结论** | 新增（治理类） |
```
★ **全锚点「证伪」只命中这一处**（在 §10 W8 表内）⇒ ★ **§3.1 的「最优」不在该门之下。**

### 1.5 **对照实验与「阴性证据」的 report 规范**

**来源**：[PRISMA 2020（BMJ 补充材料）](https://bmjpublichealth.bmj.com/content/bmjph/3/1/e001648/DC1/embed/inline-supplementary-material-1.pdf)，及本仓 §3.4.3 自己的做法。
★ **通例**：系统性检索**必须报告检索串与检索面**，否则「未搜到」不可读。
★ **⇒ 本机在 §3.4.3 做对了**（见 04 篇），**但 §3.1 没做** —— §3.1 **没有一句说「我怎么知道业界没有更好的」**。

---

## §2 ★★ 现测：§3.1 的关键读数**可复现**，但**口径未声明**（这是可修的）

### 2.1 「799 行」现测

```bash
$ cd ~/dsh-collab && wc -l comm-server/agent-mailbox.py
     799 comm-server/agent-mailbox.py
[exit=0]
$ stat -f 'mtime=%Sm birth=%SB size=%z' -t '%F %T' comm-server/agent-mailbox.py
mtime=2026-10-01 21:27:19 birth=2026-10-01 21:26:43 size=39487
$ shasum -a 256 comm-server/agent-mailbox.py
7a55e54b3d4bcf1cf0a00c10c0925efd8b80de74e41b12c18c1a25498ef10056  comm-server/agent-mailbox.py
```
✅ **799 行复现。** ★ 且 `mtime = 2026-10-01` < v6.1 的成件日（10-11）⇒ ★ **文件自 v6.1 以来未改** ⇒ **读数不该变**。

### 2.2 ★★ 「PRAGMA×8 · journal_mode×10 · … · claim×49 · 23 函数」现测 —— **口径不一致**

```bash
$ cd ~/dsh-collab && P=comm-server/agent-mailbox.py
$ printf "  grep -c（行数口径）: PRAGMA=%s journal_mode=%s busy_timeout=%s BEGIN_IMMEDIATE=%s expires_at=%s claim=%s\n" \
   "$(grep -c 'PRAGMA' $P)" "$(grep -c 'journal_mode' $P)" "$(grep -c 'busy_timeout' $P)" \
   "$(grep -c 'BEGIN IMMEDIATE' $P)" "$(grep -c 'expires_at' $P)" "$(grep -c 'claim' $P)"
  grep -c（行数口径）: PRAGMA=8 journal_mode=7 busy_timeout=3 BEGIN_IMMEDIATE=3 expires_at=8 claim=40
$ printf "  grep -o|wc -l（出现次数口径）: PRAGMA=%s journal_mode=%s busy_timeout=%s BEGIN_IMMEDIATE=%s expires_at=%s claim=%s\n" \
   "$(grep -o 'PRAGMA' $P | wc -l | tr -d ' ')" "$(grep -o 'journal_mode' $P | wc -l | tr -d ' ')" \
   "$(grep -o 'busy_timeout' $P | wc -l | tr -d ' ')" "$(grep -o 'BEGIN IMMEDIATE' $P | wc -l | tr -d ' ')" \
   "$(grep -o 'expires_at' $P | wc -l | tr -d ' ')" "$(grep -o 'claim' $P | wc -l | tr -d ' ')"
  grep -o|wc -l（出现次数口径）: PRAGMA=8 journal_mode=10 busy_timeout=3 BEGIN_IMMEDIATE=3 expires_at=8 claim=49
$ echo "  def 数 = $(grep -cE '^[[:space:]]*def ' $P)"
  def 数 = 23
[exit=0]
```

★★★ **判读（这是本件最有用的一条工程结论）**：

| 项 | v6.1 §3.1 声称 | `grep -c`（行数） | `grep -o \| wc -l`（出现次数） | 结论 |
|---|---|---|---|---|
| PRAGMA | ×8 | 8 ✅ | 8 ✅ | 两口径同 |
| **journal_mode** | **×10** | **7** ❌ | **10** ✅ | **只有出现次数口径对** |
| busy_timeout | ×3 | 3 ✅ | 3 ✅ | 两口径同 |
| BEGIN IMMEDIATE | ×3 | 3 ✅ | 3 ✅ | 两口径同 |
| expires_at | ×8 | 8 ✅ | 8 ✅ | 两口径同 |
| **claim** | **×49** | **40** ❌ | **49** ✅ | **只有出现次数口径对** |
| 函数数 | 23 | — | 23 ✅ | — |

★ **⇒ 结论**：
1. ★★ **v6.1 的数字【是对的】，但【口径从未声明】** ⇒ 用 `grep -c` 的人会**读成「v6.1 写错了」** —— ★ **这是**第二条假问题的生成机制（第一条见 `rules-registry/RULES.md:14` 那条「恒差 1 的假问题」）。
2. ★★★ **修法极便宜**：在 §3.1 那一格后加六个字 **「（`grep -o|wc -l` 口径）」**。★ **未加 ⇒ 下一轮复核者必然重踩**（本件就是踩着它进来的）。
3. ★ **本仓已有同族教训**（D-160，登记表 `known_gaps` 逐字）：★ 「★ **方法对了 ≠ 知道这个坑**」——★ `grep -c 'PEND'` ⇒ 2（假数）· `grep -c '^PEND'` ⇒ 1（真）。★ **与本次完全同构。**

### 2.3 ★★ 「41 PASS」现测 —— **可复跑，且我复跑到了**

```bash
$ cd ~/dsh-collab && python3 comm-server/agent-mailbox.py selftest 2>&1 | tail -6
    PASS  优先级：inbox() 返回按 priority 升序（第二调用点）
    PASS  replay：不存在的 msg_id 被拒（第二调用点）
    FAIL  反控：check() 对假条件确实记 FAIL  反控探针
    PASS  反控：上一条确实产生了 1 个 FAIL

  selftest: 41 PASS / 0 FAIL
[exit=0]
```
★ ✅ **「41 PASS / 0 FAIL」复现，`exit=0`。**
★★ **但注意那一行 `FAIL`** —— ★ 它是**故意的反控**（下一条 PASS 明写「反控：上一条确实产生了 1 个 FAIL」）。⇒ ★★ **`grep -c FAIL` 会读到 1，读成「有 1 个失败」** —— ★ **与 §2.2 完全同族：判据的匹配面【宽于】它要数的对象。**

### 2.4 ★★ 四代文本继承：同一句话在 v4/v5/v6/v6.1 逐字出现

```bash
$ cd ~/dsh-collab && grep -rn "799 行" docs/distributed-agent-network-governance-plan-v{4,5,6,6.1}-*.md | cut -c1-90
docs/distributed-agent-network-governance-plan-v4-20261009.md:27:- **已建成 L1**：`~/dsh-collab/comm-server/agent-mailbox.py` **799 行**（`PRAGMA`×8 …
docs/distributed-agent-network-governance-plan-v5-20261010.md:48:- **已建成 L1**：`~/dsh-collab/comm-server/agent-mailbox.py` **799 行**（`PRAGMA`×8 …
docs/distributed-agent-network-governance-plan-v6-20261011.md:268:- **已建成 L1**：`~/dsh-collab/comm-server/agent-mailbox.py` **799 行**（`PRAGMA`×8 …
docs/distributed-agent-network-governance-plan-v6.1-20261011.md:299:- **已建成 L1**：`~/dsh-collab/comm-server/agent-mailbox.py` **799 行**（`PRAGMA`×8 …
[exit=0]
```
★ **四代逐字相同，无一版标注「本轮重测」或「取值时刻」。** ★ **本次我替它重测了**（§2.1–§2.3）：★ **结论是「数字仍然成立」** —— ★★ **但「仍然成立」是【运气+文件未改】的结果，不是【流程】的结果。**
★ ★ 现测加固了这条：`mtime = 2026-10-01`（早于四代成件日）⇒ **文件确实没改** ⇒ ★ **若哪天改了，四代会【一致地错】。**

---

## §3 本机「最优性」章节的可裁形态（★ 不代裁）

### 问题是什么

> **§3.1 的「✅ 最优」这个判定，要满足什么，才能被称为**可复核的**「当前最优」？**

### 可选项（★ 三档）

| 选项 | 内容 | 代价 | 后果 |
|---|---|---|---|
| **(a) 只补口径与命令**（最小） | 给 §3.1 每一格附**复跑命令 + 口径 + 取值时刻**；不引入 ADR 格式 | ★ **极低**（半天内可做完，只动 §3 文本）★ **不改任何实现** | ★ 「数字可核」了；★ **但「最优」仍是**没有状态、没有代价列、没有权重**的一句结论** |
| **(b) 升格为 ADR**（中） | 按 [GDS Way 五段](https://raw.githubusercontent.com/alphagov/gds-way/acc80bb8e30bca3c8823300a0d3a1637af99a691/source/standards/architecture-decisions.html.md.erb) 把 §3.1 写成一份 ADR：**Status / Context / Decision / Consequences（正反）**；旧选项标 **Superseded** 但保留 | ★ 中（一次成文 + 一次裁决登记）★ **须用户裁「Accept」**（Status 不能自己填） | ★ 「最优」变成一条**有状态、有代价、可被 supersede 的决策**；★★ **代价列会被迫写出 SQLite 的真实代价**（单写者锁 / WAL 增长 / 跨设备不可直用 ⇒ 必须配 L2） |
| **(c) (b) + 对照实验臂**（最大） | 在 (b) 之上，按 trade study 补 **权重**，并**至少给一个候选做真实 PoC**（NATS 影子 PoC = Q-C） | ★ 最高（装 `nats-server` + 双写对照 + 窗口）★ **须用户批窗口** | ★★ **「最优」第一次有了**对照臂** —— ★ 本仓 §3.4.3 的「领先」标准要求「已给出业界等价物并说明差在哪」，(c) 是它的「选型」版 |

### 每选项的**代价与后果**（★ 汇总，含本件实测证据）

- **(a)** ★ **必做项，不构成一个「选项」**：★ 无论选 (b)/(c)，(a) 都要做，因为**现在 §3.1 无一条复跑命令**，而锚点自己在 §3.4.6 前言写了「**数字凡会随编辑变化者，以复跑命令代替写死值**」⇒ ★ **(a) 是补自己欠自己的账**。
- **(b)** ★ 真正的收益不是格式好看，是 **Consequences 列会逼出「SQLite 的代价」**（现测：**§3.1 全文没有一处写 SQLite 的代价**）。
- **(c)** ★★ **唯一能让「最优」变成「对照后最优」的做法** —— ★ 现测：`nats-server` **不在本机 PATH**，`grep nats docs/scripts/tools` **零命中** ⇒ ★ **(c) 目前连一台可跑的服务都没有**，成本不是"想一想"，是"装+建 PoC+窗口"。

### 裁它需要什么信息（★ 缺什么）

1. ★★ **缺：权重**（六列孰重）。★ 现测在文件里**找不到**任何权重表述。
2. ★★ **缺：SQLite 的代价列**（谁来写「代价」？起草方写会违 S3 吗？）。
3. ★★ **缺：Status 的裁决人** —— ★ ADR 的 Status 是 **Proposed→Accepted** 的**人工动作**；★ 本机「最优」现在**既非 Proposed 也非 Accepted**（读不出来）。★ **这不是本件能填的。**
4. ★ **缺：「最优」与「领先」的关系** —— ★ 本仓有「领先」的三条件（①本机有实现 ②给出业界等价物并说明差在哪 ③有阴性证据）与 **W8.14 证伪门**；★ **但「最优」不在任何门之下**（现测：全锚点「证伪」只命中 W8.14 那一处）。⇒ ★ **须裁：要不要给「最优」也配一个 W 项（学 W8.14）？**
5. ★ **缺（本件未能提供）：§3.1 那张表**有没有对应的**已占号**（它是 §3 正文，不是 W 项）⇒ ★ 它**不受任何证伪门约束**。

---

## §4 ★ 阴性证据

| # | 面 / 命令 | 结果 |
|---|---|---|
| 1 | `wc -l comm-server/agent-mailbox.py` | 799 ✅ |
| 2 | `grep -c` × 6 关键词 + `grep -o\|wc -l` × 6 | **两口径差 2 项**（journal_mode 7/10 · claim 40/49） |
| 3 | `python3 comm-server/agent-mailbox.py selftest` | **41 PASS / 0 FAIL，exit 0** ✅ |
| 4 | `grep -rn "799 行" docs/*v{4,5,6,6.1}*` | **四代逐字相同**，无重测标注 |
| 5 | `grep -n "证伪" <锚点>` | **仅 1 命中**（W8.14）⇒ §3.1 不在证伪门内 |
| 6 | `command -v nats-server` | **不在 PATH**（exit 1） |
| 7 | `grep -rl "nats" docs/ scripts/ tools/` | **零命中** |
| 8 | 外网：ADR / trade study / 选型矩阵 | ✅ 取到：GDS Way · AWS PG · MADR v3 · NASA SE Handbook（一类） |
| 9 | 外网：搜「technology selection decision matrix trade study weighted criteria engineering」 | ★ **只回页内片段**（波兰技术评论 PDF 的权重表），**未取到权威单点** |
| 10 | 外网：搜「benchmark reproducibility experimental control baseline comparison methodology」 | ★ **只回一份实验设计 SKILL.md（非权威）** ⇒ ★ **本件未引用它** |

**未搜到 ≠ 不存在**：
- ★ **未找到**本仓任何**权重或评分**的成文件（§3.1 无权重列）。
- ★ **未系统检索** arXiv/IEEE-ACM；★ **未检索** ISO/IEC/IEEE 42010（架构描述）原文。
- ★ **未做**：NATS/Redis 的真实 PoC（**本次不越界**：会装机 + 占窗口）。

---

## §5 本件自证

| 断言 | 能否红 | 本次 |
|---|---|---|
| 「41 PASS」可复跑 | 跑出来 ≠ 41 ⇒ 本件错 | ✅ 复跑 exit 0 |
| v6.1 的两个计数**口径不同** | 若 `grep -c` 也是 10/49 ⇒ 本件错 | ✅ 实测 7/40 |
| 四代文本逐字继承 | `grep` 命中数 ≠ 4 ⇒ 本件错 | ✅ 4 命中 |
| 「证伪」只在 W8.14 | `grep -c` > 1 ⇒ 本件错 | ✅ 1 命中 |
| §3.1 **无复跑命令** | ★ **反例：若表内藏命令（如脚注）本件即错** | ⚠️ 我读了 `:355-363` 全表 + `:299` 一行；★ **未逐行扫 §3 全文找脚注** ⇒ **如实标：可信度 = 所读面内** |

★ **本件不主张任何一条已闭合**（S3）。★ **「可裁形态」三档是本件提出的选项，不是用户的裁定。**
