# v7 外部审查 · **第二轮**（锚点可复跑性 + 十件检查器对抗测试 + W1/W2 + 「十四次」表）（外部线 `ext` · 2026-10-13）

> **审查员**：`ext`（外部第三方线 · 本机之内 · 同一 OS 账户）
> **锚点**：`docs/distributed-agent-network-governance-plan-v7-20261012.md` · **295 行** · sha16 **`0792872860d75af7`** · state_version 7 · updated_at `2026-10-13T02:42:08+08:00`
> ★★ **我不声称自己是「独立 verifier」** —— 只声明实际到哪一层（见 §三.1）。
> ★ 本件**未修改任何既有文件**（只新建本件）。★ **不宣布任何事项已闭合**。★ **不代裁**。

---

## 节〇 · 先说三处**对上轮结论的更正**（★ 对抗纪律要求先自曝）

★ 本轮先复核我上一轮的六条。**三条成立、三条要改**：

| 上轮 | 本轮复核 | ★ 处置 |
|---|---|---|
| **E-1** `denominator-declare` 假阴性 | ★ **复现**（见 §一.2） | **维持** |
| **E-2** `false-result-patterns` P2「声明与执行不一致」 | ★ 事实**仍成立**，但**性质要降** | ★★ **降级·改成「同条目内两处 regex 未同步」**（见 §二 F-6） |
| **E-3** `false-result-patterns` 三变体静默 | ★★ **不再复现**（工具已改） | ★★ **撤回**（见 §一.2） |
| **E-4** `selftest-audit` 三变体静默 | ★ **复现** | **维持** |
| **E-5** 两件不可外部驱动 | ★ 成立（一件略有变） | **维持** |
| **E-6** v7 自证 `6/6` 过期 | ★ **已闭合**（锚点已改 10/10） | ★ **撤回** |

★★ **E-2 为什么降级**：我上轮写它「漏检一个真阳性」。读源码后发现 —— **作者是【有意】收窄的**：P2 同一元组里 `:54–57` 逐字写着「上一版补了 `== None or`/`is None or` ⇒ **报了 33 处假阳性**（实例 `if gap is None or gap > 1:` 那是**正常的空值检查**）★ 只有【把 None 与 0 放进同一集合】才是本形态」。⇒ ★ **「漏检真阳性」不成立**；成立的只是「同一条目里**声明串**（`:52`，含 `== None or`）与**编译式**（`:58–59`，不含）**未同步**」。

★ 另：我上轮 `E-3` 的夹具里 `b.py`（`not in {0, None}`）**现已命中** ⇒ **十件工具在我上轮之后被改过**（`false-result-patterns.py` mtime **`10-13 02:47:40`**）。⇒ ★ 本报告的一切读数**只对此刻的文件负责**。

---

## 节一 · 逐条判定

> 格式：**声称 · 我跑了什么 · 原始输出（未编辑） · 退出码 · 三态判**

### 1.1 Task 一 · 锚点可复跑性（11 条）

★ 先说**扫过的面**：锚点 **295 行全文**逐节读过；凡**锚点写了命令或给了可判读数**处，逐条真跑。★ **锚点里明写「命令」的只有一处**（`§0.1.1` 的 `tailscale status`），其余是**读数**（无命令）⇒ 我为读数**自建等价命令**，命令随读数一并给出。

| # | 锚点声称（行） | 我跑了什么 | ★ 原始输出 | rc | ★ 三态判 |
|---|---|---|---|---|---|
| 1 | `:105–110` 「`tailscale status` 4 节点属主全 `coreyleung@`」（★ §0.1.1 的**最强证据**、「外部控制面」） | `/Applications/Tailscale.app/Contents/MacOS/Tailscale status` | **`Logged out.`** | 0 | ★★ **本刻不可复跑** ⇒ 「该 4 节点读数**本刻不可验证**」（★ **≠ 当时为假**） |
| 2 | `:54` 更正账 #17「在役黑板 PID **1221**」 | `lsof -nP -iTCP:8792 -sTCP:LISTEN` | `rust-blac 1221 coreyleung … TCP *:8792 (LISTEN)` | 0 | ★ **成立** |
| 3 | `:38` 更正账 #1「**6/6** 个 agent 预设」含 `continuity-index` | `ls ~/.dsh/.agent-presets/*/agent.cordis.yml` + `grep continuity-index` | 6 文件全含 · mtime `10月12 03:08–03:09` | 0 | ★ **成立**（★ 与锚点逐字相符） |
| 4 | `:178`「`false-result-patterns.py` 自证 **10/10**」 | `python3 tools/false-result-patterns.py --selftest` | `自证：10/10` | **0** | ★ **成立**（★ 但见 §二 F-8：读时刻早于对象 mtime） |
| 5 | `:41` 更正账 #4「`gcr-gate` **现测 `exit=1`**（`G-CR8 ❌ FAIL`）」 | `python3 tools/gcr-gate.py`（**裸跑**，非 `--selftest`） | `❌ G-CR8 装载前事件数门` · `══ 汇总：PASS 7 · FAIL 1 · N-A 9（共 17）══` | **1** | ★ **成立**（★ 可复跑） |
| 6 | `:289` 附D「`docs/deviation-ledger-20261011.md` —— **202 条**」 | `grep -oE 'D-[0-9]{2,3}' … \| sort -u \| wc -l` | **276**（最大 `D-276`）· 行数 **7794** | 0 | ★★ **不成立**（见 §二 F-7） |
| 7 | `:52` 更正账 #15「会话目录 **1.4G**」 | `du -sh ~/.dsh/sessions` | **`1.5G`** | 0 | ★ **已变**（★ 该行**未附复跑命令** ⇒ 不可复算） |
| 8 | `:31` §0.0「更正账（**22 条**）」 | `awk` 数表行 | **22** | 0 | ★ **成立** |
| 9 | `:61` §0.0.1「本线自己的错（**5 条**）」 | `awk` 数表行 | **5** | 0 | ★ **成立** |
| 10 | `:285` 附C「`research/v7-review-{V1,V3,V4}/` —— V2 两次皆空」 | `ls -la research/v7-review-V2/` | `total 0`（**目录在、内容空**） | 0 | ★ **成立**（★ 与 §0.1.3 第 14 行自洽） |
| 11 | 请求件 对象C 表 · 十件工具的第二列读数 | 十件逐个 `--selftest` | `10/10 · 8/8 · 5/5 · 5/5 · 9/9 · 5/5 · 5/5 · 8/8 · 6/6 · 5/5` | 全 0 | ★ **逐条相符** ✓ |

★★ **Task 一 小结**：**11 条里 8 条成立，2 条不成立/已变（#6 #7），1 条本刻不可复跑（#1）**。
★★ **最重的是 #1**：锚点用来论证「②设备独立未取得」的**唯一外部证据**（`tailscale status` 4 节点），**本刻跑不出来**（`Logged out.`）。★ 三态：★ **「该命令现在给不出该读数」成立**；★ **「当时那个读数是假的」不可判**（我无当时的原始输出）。

### 1.2 Task 二 · 十件检查器对抗测试

★ **方法**：① 先造**阳性对照**（已知缺陷形态 ⇒ 必须报红）；② 再造**等价变体**（同缺陷类、不同拼法）⇒ 看是否**静默**。
★ **钉死一条**（符合任务书纪律 4）：★★ **每个「静默」都只是【召回缺口】，不是【缺陷确证】** —— 我在表里逐条标「需作者确认」。

#### (A) 上轮四件 · 复核

| 件 | 我的夹具 | 阳性对照 | 等价变体 | ★ 判 |
|---|---|---|---|---|
| `denominator-declare` | `a.md`=`通过率 87%。` / `b.md`=a + 一句**无关的**「本段讲窗口：窗口为 24h」 | ★ a ⇒ `未申报口径 1` · **rc=1** | ★ b ⇒ **`未申报口径 0` · rc=0 · `✅ 全部数值均带口径`** | ★★ **E-1 复现** ⇒ **假阴性成立**（★ 无关邻句的口径词把裸数洗白） |
| `false-result-patterns`（E-2） | `x.py` = `r.returncode == None or r.returncode == 0` | ★ 需看 `:52` 声明串 ⇒ 应命中 | ★ **`命中：0`** | ★ **声明串含 / 编译式不含**（★ 但作者**有意**，见 §〇） |
| `false-result-patterns`（E-3） | a=`getattr(p,"status")` · b=`not in {0,None}` · c=硬编码日期 · ctrl=`not in (0,None)` | ★ ctrl 命中 | ★★ **a/b/c 本轮全命中**（`命中 4`） | ★★ **E-3 撤回**（已修） |
| `selftest-audit` | `t.py`：`正控`·`变体A`(f-串)·`变体B`(`negatives` 表)·`变体C`(`3-3==0`)，**四条同为 `0==0` 恒真** | ★ **`正控` 被标**（★ 且**同一行报两次**） | ★★ **变体 A/B/C 全静默** ⇒ 过拟合到 `cases.append(("字面串", 0 == 0,`；★★ 且第二探测器「未调本地函数」报 **0** —— **四条全都没调本地函数** | ★★ **E-4 复现** ⇒ **静默 + 单行双报成立** |
| `atomic-write-guard` / `correction-ledger-gen`（E-5） | `grep add_argument` | — | — | ★★ **两件均无路径/根参数** ⇒ **结构性不可外部驱动**（★ 如实标，★ 不硬凑） |

#### (B) 余下六件

| 件 | 可驱动？ | 阳性对照（必须红） | 等价变体 | ★ 判 |
|---|---|---|---|---|
| `lint-inventory` | ★ 可（`--check "<文本>"`） | `--check "请你去写一份调研报告"` ⇒ `❌ 未含清单` · **rc=1** ✓ 可红 | ★★ `--check "请先跑 lint-inventory 再干活"` ⇒ **rc=0 · `✅ 提示词已含既有 lint 清单（hits=['lint-inventory']）`** | ★★★ **缺陷**（见 §二 F-1） |
| `subagent-work-checklist` | ★ 可（`--prompt-file <路径>`） | `--stage pre --prompt-file <空文件>` ⇒ `❌ 未含 7 项：P2..P8` · **rc=1** ✓ | ★★ `--stage post --artifacts <dir>` ⇒ **rc=2 · `unrecognized arguments: --artifacts`** | ★★ **声明与执行不一致**（见 §二 F-4） |
| `slo-target-form` | ★ 可（`--draft <路径>`） | ① `通道投递落后 ≤ 5` ⇒ **FAIL**（`F2 缺窗口`）② `端口固定` ⇒ **FAIL**（F1+F4）✓ 均可红 | ★★ 同义词 `滞后`/`延宕`/`陈旧 ≤ 5` ⇒ **全 PASS**；★★ 带装饰数 `端口全绿 ≤ 1 个` / `端口稳定 ≤ 1 个` ⇒ **全 PASS** | ★ **静默成立** ⇒ **召回缺口**（§二 F-9 · 需作者确认） |
| `bus-pending-age` | ★ 可（`--dir <路径>`） | 30 天前 `{sent:false, ts}` ⇒ `should_be_expired=1` · **工具可红（非 json 输出 rc=1）** ✓ | ★ `{sent:false, sent_at:…}`（**无 `ts`**）⇒ **静默不判超时** | ★ **静默成立**，★★ **但对真实语料不适用** —— 实测 `send-instructions/` **122/122 都有 `ts`** ⇒ ★★ **仅召回缺口**（§二 F-10） |
| `atomic-write-guard` | ★★ **结构性做不到**（仅 `--json/--selftest/--version`） | — | — | ★★ **如实标：无法外部驱动** |
| `correction-ledger-gen` | ★★ **结构性做不到**（新增 `--tail/--ids/--summary`，**但仍无路径参数**） | — | — | ★★ **如实标：无法外部驱动**（★ `--ids` 只能筛已有台账，★ 不能指向夹具） |

#### (C) 附带发现（**不在十件之内**，但锚点 `:41` 引它）

★ `gcr-gate.py` 的「自证 **8/8**」里，**G-CR3 那条是恒真字面量**（见 §二 F-5）。

★★ **Task 二 小结**：**十件自证全绿（读数全对）**，★ **而其中五件在等价变体上静默或自指放行**。⇒ ★★ **「自证 N/N 全绿」仍不能推出「它能抓到那一类」**（★ 与上轮同一结论，本轮**样本更大**）。

### 1.3 Task 三 · W1/W2 三个切口

★★ 扫描面声明：W1 **1247 行**、W2 **914 行** 全文过了一遍 grep 面 + **真跑了两个文件的复跑块**；★ **未逐行精读全文**（见 §三.3）。

**切口① 可复跑性** —— ★ **两件都有复跑块，且我抽跑的都对得上**：

| 来源 | 命令 | ★ 原始输出 | rc |
|---|---|---|---|
| W1 `:1197` | `python3 scripts/rules-integrity.py` | `结论: ✅ 账本通过完整性检查` | **0** |
| W1 `:1198` | `python3 tools/gcr-gate.py` | `══ 汇总：PASS 7 · FAIL 1 · N-A 9（共 17）══` | **1** |
| W1 `:1199` | `python3 tools/gcr-gate.py --selftest` | `自证：8/8` | **0** |
| W1 `:1200` | `python3 tools/incident-regression.py` | `❌ 有 1 起未通过：['INC-02']` | **1** |
| W2 `:235–236` | `F=docs/distributed-agent-network-governance-plan-v6.1-20261011.md; grep -c "C4-b" $F` / `grep -c "C4" $F` | `0` / **`15`** | **1** / **0** |

★★ **W2 那两条【逐字复现】**（`C4-b` 0 命中 rc=1；阳性对照 `C4` 15 命中 rc=0）⇒ ★ **这一处是本计划里我见过的**最规范**的阴性证据**（★ 自带给阳性对照）。
★ **W1 复跑块**4 条亦复现。★★ **但同一块里有一条崩了**：`python3 scripts/pitfalls-cli.py list` ⇒ `KeyError: 'severity'` · **rc=1**（见 §二 F-11）。

**切口② 阴性证据与出处（凡说「未找到」有没有阳性对照）**：

| 处 | 阴性声称 | ★ 阳性对照 | 判 |
|---|---|---|---|
| W2 `:235–249` | 「`C4-b` 在锚点 **0 命中**」 | ★ **有**（`C4` 15 命中） | ★ **规范** ✓ |
| W2 `:331–335` | 「`mailbox.db` **不存在**」 | ★ **有**（给了负控：`ls` 不存在 **或** `count(*) ≠ 30755 ⇒ 红`） | ★ **规范** ✓ |
| W1 `:449` | 「**本件未发现任何迁移产物**」（M3①） | ★ **未见同句阳性对照** | ★ **需作者确认**（★ 但该行**明确区分**「未开工 ≠ 判据失败」，措辞自律 ✓） |

★ **W1 本件自己也认领了这个坑**（`:99`「报『未搜到/0 命中/空』之前必须先给必定命中的阳性对照」· `:182` 自曝只读 `state` 得假结论、改读 `status` 才纠正）⇒ ★ **方法论语与做法大体一致**。

**切口③ 两两矛盾与未察觉的不确定** —— ★★ **本切口的重头在 Task 四**（见 §1.4）。★ W1/W2 **之间**未发现直接互相打架的读数；★ 但发现 **W1 与锚点**、**锚点与覆盖表** 的计数打架（§1.4）。

### 1.4 Task 四 · §0.1.3「十四次实证」表是否已自洽

| 项 | 读数 | ★ 判 |
|---|---|---|
| 标题「**十四次**」 | `:143` | ★ **成立** |
| 表行数 | `:149–162` ⇒ **14 行**（编号 1–14） | ★ **成立**（★ **与标题自洽**） |
| `:169`「十四次里【六次是本线自己写的工具/脚本】（#3、#5、#6、#8、#9、#10）」 | 列了 **6 个**号 ⇒ **个数对** | ★★ **但口径与内容不符**（见 F-3b） |
| `:174`「『次』数 = **下表**的行数（现 14）」 | 表在**其上方** | ★ **方位词错**（下表 → 上表） |
| **`:174`「若两处不一致，以覆盖表为准」** | ★★ **覆盖表自己**：标题 `:1`「**十三次**同形」，表体 **14 行**，汇总 8+6=14 | ★★★ **兜底条款失效**（见 F-2） |
| **`:174`「本节与覆盖表逐行对齐」** | ★★ 实测 #11/#12/#13 **错位** | ★★★ **不成立**（见 F-2） |

★★ **⇒ Task 四 结论：标题「十四」与表行数**已自洽**；★ 但【另有三处仍打架】—— 其中一处（覆盖表标题「十三」）**恰好是锚点指定的仲裁者**。

---

## 节二 · 发现的错（按严重度 · 每条带复现命令）

### ★★★ F-1 · `lint-inventory` 的**门**可被【自指】放行 —— 报「已含清单」而清单不在

★ **形态**：门判「提示词是否含既有 lint 清单」，实为**子串包含 5 个 token 之一**，★ **第一个 token 就是工具自己的名字**。

★ **源码**（`tools/lint-inventory.py:105–109`，逐字）：
```python
def check_prompt(text):
    """★ 门：提示词是否含【既有 lint 清单】。"""
    hits = [m for m in ("lint-inventory", "既有 lint", "evidence-channel-guard",
                        "csx-canfail-check", "text-assertion-lint") if m in text]
    return (len(hits) > 0), hits
```

★ **复现**（★ 阳性对照 + 变体对照，两条都取退出码）：
```bash
cd /Users/coreyleung/dsh-collab
python3 tools/lint-inventory.py --check "请你去写一份调研报告，注意质量。" > /tmp/f1a 2>&1; echo "rc=$?"; cat /tmp/f1a
#   rc=1  ❌ 提示词【未含】既有 lint 清单 ⇒ …            ← ★ 阳性对照：会红 ✓
python3 tools/lint-inventory.py --check "请先跑 lint-inventory 再干活" > /tmp/f1b 2>&1; echo "rc=$?"; cat /tmp/f1b
#   rc=0  ✅ 提示词已含既有 lint 清单（hits=['lint-inventory']）  ← ★★ 假结果
```

★ **三态**：★★ **「仅含工具名即判『已含清单』」＝ 成立**（可复现）。★ **「该判据本意即允许提名」**＝**不可判**（★ 但其 docstring 逐字说门管的是「提示词**是否含清单**」，★ 故我判这是**报了一个假结果**）。

★★ **加重项**：★ 该工具的**自证**（`:139`「含关键词 ⇒ 判『已含』hits=…」）**用的是同一条判据** ⇒ ★★ **自证把过拟合当真值来断言** ⇒ **自证 5/5 全绿而毫无警示**。★ 与「判据不得自指」（§17.4）**同族**。

---

### ★★★ F-2 · 锚点 §0.1.3 声称与覆盖表「**逐行对齐**」⇒ **不成立**；且**仲裁者自己标题打架**

★ **锚点 `:174` 逐字**：「★ **且本节与 `v7-mechanization-coverage-20261013.md` 逐行对齐**；★★ 若两处不一致，★ **以覆盖表为准**」。

★ **实测（两处不一致）**：

| 行 | 锚点 `:149–162` | 覆盖表 `:13–26` | ★ |
|---|---|---|---|
| #11 | ★ **`None` 当绿**（P2） | ★ **序号不升序**（P6） | ★ **错位** |
| #12 | ★ **负控硬编码时间**（C2） | ★ **`None` 当绿** | ★ **错位** |
| #13 | ★ **序号不升序 + 重复序号** | ★ **硬编码时间戳** | ★ **错位** |

★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
sed -n '159,161p' docs/distributed-agent-network-governance-plan-v7-20261012.md   # 锚点 #11/#12/#13
sed -n '23,25p'   docs/v7-mechanization-coverage-20261013.md                      # 覆盖表 #11/#12/#13
#   ⇒ 锚点 #11=None当绿 / #12=硬编码时间 / #13=序号不升序
#   ⇒ 覆盖表 #11=序号不升序 / #12=None当绿 / #13=硬编码时间   ← ★ 三行错位
```

★★ **加重项（本报告最重的一处）**：★ 锚点说「**不一致以覆盖表为准**」—— ★ **而覆盖表自己的标题 `:1` 写「v7 §0.1.3 **十三次**同形」，其表体却是 **14 行**、其汇总 8+6=**14**、其占比 8/14=57% · 6/14=43% 亦按 14 算**。
```bash
sed -n '1p'  docs/v7-mechanization-coverage-20261013.md   # 「…十三次同形…」
sed -n '32,38p' docs/v7-mechanization-coverage-20261013.md # 8 + 6 = 14
```
★★ ⇒ **指定的兜底条款【无仲裁者】**：★ 「以覆盖表为准」在遇到分歧时**取不到唯一值**（★ 它的标题说 13、表体说 14）。

★ **三态**：★★ **「两处 #11–#13 错位」＝ 成立**。★★ **「覆盖表标题与表体不一致（13 vs 14）」＝ 成立**。★ **「以哪一版为对」＝ 不可判**（★ 我不代裁，见 §三）。

---

### ★★ F-3 · 锚点 §0.1.2 的**条数**，标题与正文打架

★ `:128` 标题逐字「§0.1.2 ★★★ 判据纪律（**七条** · 每条都有当晚的实证）」，其表 **①–⑦ ＝ 7 行**（★ 数过）。
★ `:131` 正文逐字「★ **五种形态**当晚共出现 **五次**，故单列成纪律」。
★★ **5 ≠ 7**，★ 且**同一节内**、**相隔 3 行**。

★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
sed -n '128p;131p' docs/distributed-agent-network-governance-plan-v7-20261012.md
awk 'NR>=134 && NR<=141 && /^\| \*\*[①-⑦]\*\*/' docs/distributed-agent-network-governance-plan-v7-20261012.md | wc -l   # ⇒ 7
```

★ **三态**：★★ **「同一节内 5 与 7 并存」＝ 成立**。★ **「哪个对」＝ 不可判**（★ 若「形态」与「条」是两种口径，则须作者**在正文写明口径**——★ 现在没写）。

---

### ★★ F-3b · `:169`「六次是本线自己写的**工具/脚本**」的**清单口径与内容不符**

★ `:169` 逐字：「★★★ **⇒ 十四次里【六次是本线自己写的工具/脚本】**（★ **#3、#5、#6、#8、#9、#10**）」。

★ 逐条核（表内原文）：`#3` 本线外部脚本（**工具** ✓）· `#5` 本线的**并发跑法**（★ **跑法**，非工具）· `#6` 本线的 **grep**（★ **调用法**，非工具）· `#8` 本线的**查板用法**（★ **用法**，非工具）· `#9`/`#10` `false-result-patterns.py`（**工具** ✓）。
★★ 反之：`#4` **`tools/selftest-audit.py` 自身**、`#11` **`tools/false-result-patterns.py` 的 P2** —— ★ 二者**同为该线自写工具**，**却未计入**。

★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
sed -n '151p;153p;154p;156p;157p;158p;159p' docs/distributed-agent-network-governance-plan-v7-20261012.md  # #3/#5/#6/#8/#9/#10/#11 原文
```
★ **三态**：★ **「清单里的 #5/#6/#8 不是『工具/脚本』」＝ 成立**（表内原文如此）。★★ **「该六项是否算『本线自写工具』」＝ 需作者确认**（★ 口径未定义 ⇒ **召回缺口**，★ 我不升格成缺陷）。

---

### ★★ F-4 · `subagent-work-checklist` 自报一个**不存在的旗标**

★ 头 docstring 逐字（`tools/subagent-work-checklist.py:18`）：「`subagent-work-checklist.py --stage post [--artifacts <dir>]`」。
★ 而 `add_argument`（`:164–168`）**只有** `--stage/--prompt-file/--module/--selftest/--version` ⇒ ★ **无 `--artifacts`**。

★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
python3 tools/subagent-work-checklist.py --stage post --artifacts /tmp > /tmp/f4 2>&1; echo "rc=$?"; cat /tmp/f4
#   rc=2  subagent-work-checklist.py: error: unrecognized arguments: --artifacts /tmp
python3 tools/subagent-work-checklist.py --stage post > /tmp/f4b 2>&1; echo "rc=$?"   # ⇒ rc=0（★ 无 artifacts 也能"通过"）
```
★ **三态**：★★ **「声明有 `--artifacts`、执行无」＝ 成立**。★ **「post 阶段是否因此做不到产物核验」＝ 需作者确认**。

---

### ★★ F-5 · `gcr-gate` 自证里的 G-CR3 **是恒真字面量** —— ★ 同一纪律它自己违

★ `gcr-gate.py` 的 `:383–389` **逐字认领**过这一形态：「**本函数旧版的五条「负例」是恒真字面量** … **`0 == 0` 永远为 True** … ⇒ **四条负例【从未调用被测判据函数】**」并在 **2026-10-12（D-204）** 修过。★ **它修了 G-CR16/G-CR8/G-CR6（改真调 `_synth_*`），★ G-CR3 原样留着**：

```python
# tools/gcr-gate.py:412–413（逐字）
cases.append(("G-CR3 负例：目录名与 package.name 不等 ⇒ 应判不过",
              pkg_name != d.name, True))          # ← ★ 只比两个字面串，★ 从未调用 gcr3()
```

★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
python3 tools/gcr-gate.py --selftest > /tmp/f5 2>&1; echo "rc=$?"; grep 'G-CR3' /tmp/f5
#   ✅ G-CR3 负例：目录名与 package.name 不等 ⇒ 应判不过（实得 True）   ← ★ 「实得 True」= 该恒真式成立
sed -n '412,413p' tools/gcr-gate.py
grep -c '_synth_gcr3' tools/gcr-gate.py    # ⇒ 0（★ 无 G-CR3 的合成器 ⇒ ★ 该判据【无可信负控】）
```
★★ **加重项**：★ 它的标签写「**应判不过**」而实得 **True** 且标 **✅** ⇒ ★★ **读者会把「判据拒绝了某个东西」读进去，而实际【没有任何门被调用】**。★ 与 §0.1.2 纪律①（「凡自证必真调被测判据函数」）**正面对撞**。

★ **三态**：★★ **「G-CR3 自证项从不调用 `gcr3()`」＝ 成立**（源码 + `_synth_gcr3` 计数 0）。★ **「其余 7 项亦恒真」＝ 不成立**（G-CR16/G-CR8/G-CR6 确为真调）。

---

### ★★ F-6 · `false-result-patterns` 的 P2：**同条目内两处 regex 未同步**（★ 我上轮结论的更正版）

★ 同一 P2 元组里：
```python
# :52  声明串（含 == None or / is None or）
("P2", r'in\s*\(\s*0\s*,\s*None\s*\)|==\s*None\s*or|is\s+None\s+or|not\s+in\s*\(0,\s*None\)',
 # :54–57  ★ 逐字理由：上一版补了 == None or ⇒ 报 33 处假阳性（`if gap is None or gap > 1:`）
 #         ★ 只有【把 None 与 0 放进同一集合】才是本形态
 # :58–59  ★ 编译式（**不含** == None or / is None or）
 re.compile(r'not\s+in\s*[\(\{]\s*0\s*,\s*None\s*[\)\}]|in\s*[\(\{]\s*0\s*,\s*None\s*[\)\}]')),
```
★ **复现**（★ 生效的是编译式）：
```bash
cd /Users/coreyleung/dsh-collab
D=$(mktemp -d); printf 'import subprocess\nr = subprocess.run(["true"])\nok = r.returncode == None or r.returncode == 0\n' > "$D/x.py"
python3 tools/false-result-patterns.py --root "$D" > /tmp/f6 2>&1; echo "rc=$?"; grep -E '命中' /tmp/f6; rm -rf "$D"
#   命中：0（★ 按类：{}）   ← ★ `== None or` 不被抓
```
★ **三态**：★★ **「声明串与编译式不一致」＝ 成立**。★★ **「工具漏检真阳性」＝ 不成立**（★ **作者有意收窄**，理由逐字在 `:54–57`）。★ **降级为「未同步」的文档缺陷**。

---

### ★★ F-7 · 附D 的台账条数与台账实际不符

★ 锚点 `:289` 逐字：「`docs/deviation-ledger-20261011.md` —— ★ **202 条**（★ 其中今晚 +95）」。
★ 实测：台账 **唯一 D- 编号 = 276**（最大 `D-276`）· 行数 **7794**（★ 与任务书「274 条」**亦不等**）。
★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
grep -oE 'D-[0-9]{2,3}' docs/deviation-ledger-20261011.md | sort -u | wc -l    # ⇒ 276
wc -l docs/deviation-ledger-20261011.md                                       # ⇒ 7794
sed -n '289p' docs/distributed-agent-network-governance-plan-v7-20261012.md   # ⇒ 「202 条」
```
★ **三态**：★★ **「202 ≠ 台账现有编号数（276）」＝ 成立**。★ **「202 是哪个口径（条目？行数？某一时点？）」＝ 不可判**（★ 锚点未附口径亦未附复跑命令）。

---

### ★ F-8 · 锚点自报的读时刻**早于**被引对象的 mtime

★ 锚点 `:178` 逐字：「`tools/false-result-patterns.py`（★ 自证 **10/10** · ★ 读于 **`2026-10-13T02:42:08+08:00`**）」，★ 而该文件 **mtime = `10-13 02:47:40`** ⇒ ★ **引的是【上一版】文件**。
★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
stat -f '%Sm' -t '%m-%d %H:%M:%S' tools/false-result-patterns.py   # ⇒ 10-13 02:47:40
sed -n '178p' docs/distributed-agent-network-governance-plan-v7-20261012.md
```
★ **三态**：★ **「读时刻早于对象 mtime」＝ 成立**。★ **「该读数已过期」＝ 不成立**（★ 我实测仍是 10/10，**数没变**）。★ 归为**时点标注问题**，★ 非数值错误。

---

### ★ F-9 · `slo-target-form` 的 F2/F4 是**封闭词表** ⇒ 同义词/装饰数静默（★ 召回缺口）

★ 判据（`:30–46`）：F2 由 **12 词** `TIME_WORDS` 触发的**条件性**要求；F4 的 `META_ADJ` 是 **14 词**封闭表，★ 且**仅当 F1（含量）为假时**才生效。
★ **复现**（★ 阳性对照 + 变体，全取原始输出）：
```bash
cd /Users/coreyleung/dsh-collab
python3 - <<'PY'
import importlib.util
s=importlib.util.spec_from_file_location("slo","tools/slo-target-form.py"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
for t in ["通道投递落后 ≤ 5","通道投递滞后 ≤ 5","端口固定","端口全绿 ≤ 1 个"]:
    print(t, m.judge(t)[0], m.judge(t)[1])
PY
#   通道投递落后 ≤ 5   FAIL ['F2 【时间相关量】却无【窗口】']   ← ★ 阳性对照：会红 ✓
#   通道投递滞后 ≤ 5   PASS []                                ← ★ 同义词静默
#   端口固定           FAIL ['F1 无【量】','F4 【元语言】: 固定…'] ← ★ 阳性对照：会红 ✓
#   端口全绿 ≤ 1 个    PASS []                                ← ★ 加装饰数即洗白
```
★ **三态**：★★ **「同义词/装饰数使判据静默」＝ 成立**（可复现，且 **`--draft` 端到端路径同样** —— 实测 `--draft` 报告里「通道投递滞后 ≤ 5」显示 **✅ PASS**）。★★ **「这是缺陷」＝ 不成立**：★ 作者在 `:32` 逐字写了「**只有当 F1 缺而含元语言词时才判元语言 —— 避免误伤「固定 ≤ 5 个」**」⇒ ★ **F4 的宽是【有意】的**。★ 归类：★★ **召回缺口，需作者确认是否收窄**。

---

### ★ F-10 · `bus-pending-age` 只用 `ts` 判龄（★ 对真实语料**不适用**）

★ 判据（`:26–38`）：`age_h` 只由 `o.get("ts")` 算出；★ 但它**自己把 `sent_at` 读进行里并显示** ⇒ ★ **读者会以为 `sent_at` 也参与判龄**。
★ 实测：`{sent:false, sent_at:<30天前>}`（**无 ts**）⇒ **静默不判超时**；★ 而 `{sent:false, ts:<30天前>}` ⇒ `should_be_expired=1`。
★★ **但对真实语料不适用**：`token-monitor/event-bus/send-instructions/` 实测 **122/122 都有 `ts`**（11 个另有 `sent_at`）。
★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
B=token-monitor/event-bus/send-instructions
echo "含 ts: $(grep -l '\"ts\"' $B/*.json | wc -l) / 共 $(ls $B/*.json | wc -l)"
python3 -c "import json,glob;print(sorted(json.load(open(glob.glob('$B/*.json')[0])).keys()))"
```
★ **三态**：★ **「无 `ts` 则静默」＝ 成立**。★★ **「这是本仓的真实缺陷」＝ 不成立**（★ 现有 122 条全有 `ts`）⇒ ★ **仅召回缺口**（★ 若未来有记录改用 `sent_at` 则漏）。

---

### ★ F-11 · W1 复跑块里有一条**崩了**

★ W1 `:1204` 的 `python3 scripts/pitfalls-cli.py list` 实测 **`KeyError: 'severity'` · rc=1**。
```bash
cd /Users/coreyleung/dsh-collab
python3 scripts/pitfalls-cli.py list > /tmp/f11 2>&1; echo "rc=$?"; tail -3 /tmp/f11
#   rc=1  … KeyError: 'severity'
```
★ **三态**：★★ **「该行 rc=1 且 traceback 为 KeyError」＝ 成立**。★ **「是工具缺陷还是我的环境/数据问题」＝ 不可判**（★ 未读 `pitfalls-cli.py` 源码；★ 归**需作者确认**）。

---

## 节三 · 我的限制

### 3.1 ★★ 我**不构成独立审查**（★ 这是本节最要紧的一句）

★ 我跑在**本机之内**、**同一个 OS 账户**下。按该计划 §0.1.1 自订的**独立性三层**：

| 层 | ★ 我实际到哪 | ★ 依据 |
|---|---|---|
| ① **认知独立性** | ★ **到**（不同会话可独立推理） | ★ 本轮全部结论均为我自跑 |
| ② **设备独立性** | ★★ **未到** | ★ 我在**同一台机**；★ 且锚点原引的 `tailscale status` 4 节点证据**本刻跑不出**（`Logged out.`）|
| ③ **主体独立性** | ★★ **不可判** | ★ 全机进程/会话文件属主同一人 |

★★ **⇒ 我不声称自己是「独立 verifier」。** ★ **R046 / S3 要的是 ③，我在①止步。** ★ 本报告的一切判断**只能**被当作**同一主体的一次复核**，★ **不能**充当「独立验证通过」。

### 3.2 ★ 我**没跑**的（★ 一律不写成结论）

- ★ **未跑 `register`** —— ★ 依 `docs/handoff-to-claude-m4-domain-review-20261012.md:169` 逐字警示「**会真冻结 24h**」⇒ ★ 相关机制我**只做静态核**。
- ★ **`atomic-write-guard` / `correction-ledger-gen` 未驱动** —— ★ **结构性做不到**（无路径参数）⇒ ★ 如实标，**不硬凑**。
- ★ **未读 W1/W2 全文** —— ★ 只做了**三切口**（grep 面 + 抽跑复跑块）⇒ ★ 我对 W1/W2 的**内容正确性**只覆盖抽到的部分。
- ★ **`pitfalls-cli.py` 未读源码** ⇒ F-11 只报现象。
- ★ **未核 §12 不可判清单 9 条 / §13 待裁 5 条**（★ 任务书未列入本轮四件事）。

### 3.3 ★★ 每条「静默」都只是【召回缺口】

★ 任务书纪律 4 要求我标出「需作者确认」。★ 本轮我标了 **F-3b · F-4 后半 · F-9 · F-10 · F-11** 五处 ⇒ ★★ **它们都不是「缺陷确证」**：★ 我**能**证明「我的等价变体让它静默」，★ **不能**证明「这在真实使用中会出错」。★ **判据归属在作者**。

### 3.4 ★ 我的三处自曝

1. ★★ **E-2 我上轮框错了**（说「漏检真阳性」，实为**作者有意收窄**）⇒ ★ 本轮已在 §〇 降级。
2. ★★ **E-3 我上轮所测现已不复现** ⇒ ★ 撤回（★ 并因此发现**十件工具在我上轮之后被改过**）。
3. ★★ **`bus-pending-age` 的 `ts` 变体**我一度当作缺陷 → 查真实语料（122/122 有 `ts`）后**自降为召回缺口**。

### 3.5 ★ 不声称的两件事

- ★ **本仓有 git-snapshot 每 2–3 分钟自动 commit** ⇒ ★ 我**不主张**「期间无人改动」（★ `git status` 干净**不是**证据）。
- ★ 本报告**不替用户拍板** —— ★ 所有「以哪版为准 / 哪个口径对」我一律写**不可判**或**需作者确认**。

---

## 附 · 复跑块（绝对路径 · 自包含 · 夹具自建自清）

```bash
cd /Users/coreyleung/dsh-collab

# ── Task 一：锚点可复跑性 ──
/Applications/Tailscale.app/Contents/MacOS/Tailscale status          # ⇒ Logged out.（★ 锚点 :105 不可复跑）
lsof -nP -iTCP:8792 -sTCP:LISTEN | tail -1                           # ⇒ rust-blac 1221 … LISTEN
du -sh ~/.dsh/sessions                                               # ⇒ 1.5G（锚点 :52 称 1.4G）
grep -oE 'D-[0-9]{2,3}' docs/deviation-ledger-20261011.md | sort -u | wc -l   # ⇒ 276（附D :289 称 202）
python3 tools/gcr-gate.py > /tmp/a 2>&1; echo "gcr-gate rc=$?"; grep 汇总 /tmp/a   # ⇒ rc=1
python3 tools/false-result-patterns.py --selftest | tail -2          # ⇒ 自证：10/10
ls -la research/v7-review-V2/                                        # ⇒ total 0（空目录在）

# ── F-1：lint-inventory 门自指放行 ──
python3 tools/lint-inventory.py --check "请先跑 lint-inventory 再干活"; echo "rc=$?"   # ⇒ rc=0 ✅「已含清单」

# ── F-2：锚点「逐行对齐」不成立 + 覆盖表标题 13 vs 表体 14 ──
sed -n '1p'   docs/v7-mechanization-coverage-20261013.md             # ⇒ 「…十三次同形…」
sed -n '159,161p' docs/distributed-agent-network-governance-plan-v7-20261012.md # 锚点 #11/#12/#13
sed -n '23,25p'   docs/v7-mechanization-coverage-20261013.md                    # 覆盖表 #11/#12/#13（错位）

# ── F-3：§0.1.2 条数打架 ──
sed -n '128p;131p' docs/distributed-agent-network-governance-plan-v7-20261012.md # 「七条」 vs 「五种形态…五次」

# ── F-4：--artifacts 不存在 ──
python3 tools/subagent-work-checklist.py --stage post --artifacts /tmp; echo "rc=$?"  # ⇒ rc=2

# ── F-5：gcr-gate G-CR3 恒真 ──
sed -n '412,413p' tools/gcr-gate.py; grep -c '_synth_gcr3' tools/gcr-gate.py   # ⇒ 0

# ── F-9：slo-target-form 同义词/装饰数静默 ──
python3 - <<'PY'
import importlib.util
s=importlib.util.spec_from_file_location("slo","tools/slo-target-form.py"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
for t in ["通道投递落后 ≤ 5","通道投递滞后 ≤ 5","端口全绿 ≤ 1 个"]: print(t, m.judge(t)[0])
PY

# ── F-10：bus 真实语料字段面 ──
B=token-monitor/event-bus/send-instructions
echo "含 ts: $(grep -l '\"ts\"' $B/*.json | wc -l) / $(ls $B/*.json | wc -l)"

# ── E-1（上轮最重 · 本轮复现）：denominator-declare 假阴性 ──
D=$(mktemp -d)
printf '通过率 87%%。\n' > "$D/a.md"
printf '通过率 87%%。\n本段讲窗口：窗口为 24h，与本数字无关。\n' > "$D/b.md"
python3 tools/denominator-declare.py "$D/a.md"; echo "rc=$?"   # ⇒ 1 · rc=1
python3 tools/denominator-declare.py "$D/b.md"; echo "rc=$?"   # ⇒ 0 · rc=0（★ 假阴性）
rm -rf "$D"
```

---

*（外部线 `ext` · 2026-10-13 · ★ 只审不处理 · ★ 未修改任何既有文件 · ★ 本件不宣布任何事项闭合 · ★ 只给判据与三态，不给改写措辞 · ★ **我不构成独立审查**）*
