# v7 外部审查 · **执行件**（对象 C 对抗测试 + 对象 A 自证核验）（外部线 `ext` · 2026-10-13）

> **★ 授权**：用户于本轮**显式授权**执行工具代码（「如果需要给你授权才能做的审查，授权」）。
> **★ 按谁的要求**：`docs/v7-external-review-request-20261013.md`
> **★ 交付格式**：依该请求件 §三「交付格式」——**节一 逐条判定 · 节二 发现的错 · 节三 我的限制**。
> **★ 模式**：★ **只审不处理** —— ★ **未修改任何文件**（★ 工具指纹跑前=跑后，见文末）。
> **★ 执行时刻**：2026-10-13T02:0x（★ 本件所有读数皆为**该轮**读数；★ 会变）

---

## 节一 · 逐条判定

### 1.1 ★ 对象 A 的【自证 N/N】核验（十条命令，逐条报 命令 · 原始输出 · 退出码）

★ 命令一律 `cd /Users/coreyleung/dsh-collab && python3 tools/<t>.py --selftest`。★ 下表「原始输出」栏给的是**该工具自报的收尾行**（★ 全量输出在 §1.3 复跑块可复现）。

| # | 工具 | ★ 请求件 声称 | ★ 我实测 `rc` | ★ 原始输出收尾行 | 三态 |
|---|---|---|---|---|---|
| 1 | `false-result-patterns.py` | 10/10 | **0** | `自证：10/10` | ★ **成立** |
| 2 | `selftest-audit.py` | 8/8 | **0** | `自证：8/8` | ★ **成立** |
| 3 | `lint-inventory.py` | 5/5 | **0** | `自证：5/5` | ★ **成立** |
| 4 | `subagent-work-checklist.py` | 5/5 | **0** | `自证：5/5` | ★ **成立** |
| 5 | `slo-target-form.py` | 9/9 | **0** | `自证：9/9` | ★ **成立** |
| 6 | `bus-pending-age.py` | 5/5 | **0** | `自证：5/5` | ★ **成立** |
| 7 | `atomic-write-guard.py` | 5/5 | **0** | `自证：5/5` | ★ **成立** |
| 8 | `denominator-declare.py` | 8/8 | **0** | `自证：8/8` | ★ **成立** |
| 9 | `correction-ledger-gen.py` | 6/6 | **0** | `自证：6/6` | ★ **成立** |
| 10 | `live-read-guard.py` | 5/5 | **0** | `自证：5/5` | ★ **成立** |

★★ **⇒ 10/10 条的「自证 N/N」与请求件表格【逐个相符】。**

### ★★ 1.2 ★★★ 顺带闭合了上一轮 **E1**（文档间矛盾）

| 件 | 对 `false-result-patterns.py` 的自证 |
|---|---|
| **本刻实测** | ★★ **10/10**（rc=0） |
| **请求件** 54 行 | **10/10** ⇒ ★ **是现值，对** |
| **v7** §0.1.3（178 行） | **6/6** ⇒ ★★ **是过期值** |

★★★ **⇒ E1 判定：两文档矛盾中，【v7 才是要改的那一个】。** ★ 请求件无误。

### 1.3 ★★ 对象 C 的【对抗测试】—— ★ 这才是请求件说的「最重要的一部分」

★★ 请求件的原话：「**它声称能红的那个情形，真的能让它红吗？** ★★ 具体：**自己构造一个反例输入**，看它是否真的报红。」

★ **我的方法**：★ 每个可驱动的工具，构造 ① 一个**阳性对照**（canonical 缺陷形态 ⇒ 必须报红，★ 用来证明**我的夹具真能驱动它**）+ ② 若干个**等价变体**（**同一缺陷类**、**不同拼法**）⇒ 看它是否**静默**。
★★ **判据**：★ 阳性对照必须红（★ 否则我的夹具不可判，不是工具的错）；★ 变体若静默 ⇒ ★ **过拟合到作者的拼法**。

#### ★★★ F1 · `denominator-declare.py` —— ★★ **假阴性：无关邻句的口径词把数字「洗白」**

★ **阳性对照**（`isolated.md` 全文 = 一行）：
```
通过率 87%。
```
★ 实测输出：
```
  数值总数 1 · ★ 未申报口径 1
  ❌ [pct] 87%         … 通过率 87%。
```
★ ⇒ ★ **阳性对照报红 ✓（夹具能驱动它）**

★★★ **反例**（`laundered.md`）—— ★ **只加一句与 87%【无关】的话**：
```
通过率 87%。
本段讲窗口：窗口为 24h，与上一段的数字无关。
```
★ 实测输出：
```
  数值总数 1 · ★ 未申报口径 0
  ✅ 全部数值均带口径
```
★★★ **⇒ 假阴性。** ★ 87% **仍然没有分母**，★ 工具却报「全部带口径」。
★ **距离实验**：★ 「窗口」距数字 **50 字 ⇒ 仍洗白**（未申报 0）；★ **200 / 300 字 ⇒ 不再洗白**（未申报 1）⇒ ★ 洗白半径 = 该工具的**段落窗**（源码 `para_of(..., back=260, fwd=160)`）。

★★ **为什么它自己的自证覆盖不到**：★ 它的负控是 `"24h 窗口内到达率 91.67%（分母 = 12）"` —— ★★ **口径词与分母在同一句**。⇒ ★ **自证的负控从不出现「口径词在别处」这一形态** ⇒ ★★ **这正是「自证 ≠ 对抗测试」的实证。**

#### ★★ F2 · `false-result-patterns.py` —— **【声明】与【执行】不一致（P2）**

★ 源码 58–59 行（★ 本刻实读）：
```
("P2", r'in\s*\(\s*0\s*,\s*None\s*\)|==\s*None\s*or|not\s+in\s*\(0,\s*None\)',   ← ★ 标注模式【含】== None or
 '★ `None` 被当绿…', re.compile(r'not\s+in\s*\(\s*0\s*,\s*None\s*\)|in\s*\(\s*0\s*,\s*None\s*\)'))  ← ★ 实际编译的【不含】
```
★★ **⇒ 该条自己标注能抓 `== None or`，而真正编译执行的 regex 里【没有这一支】。**

★ **实测**（`adv_p2_idiom.py`）：
```python
import subprocess
r = subprocess.run(["true"])
ok = r.returncode == None or r.returncode == 0
```
★ 实测：★ **静默**（该轮总命中 1，且那 1 是阳性对照文件，不是它）。
★★ ⇒ ★ **标注说能红，实际不红** —— ★★ 这正是被审计划在抓的那一族（「**工具自己的说法与自己不符**」）。

#### ★★ F3 · `false-result-patterns.py` —— **三处等价变体全静默**

★ 同一夹具目录（5 个 .py）一轮跑完，★ **阳性对照命中 1，三个变体 0 命中**：

| # | 变体（同一缺陷类 · 不同拼法） | ★ 实测 |
|---|---|---|
| A | `s = getattr(p, "status")`（P1 的真 getattr 形态） | ★ **静默** |
| B | `if r.returncode not in {0, None}:`（**集合**字面量） | ★ **静默** |
| C | `DEADLINE = "2026-10-12 08:00:00"`（P5，**空格**而非 `T`） | ★ **静默** |

★★ **A 尤其值得记**：★ P1 的 regex 是 `\b(getattr\s*\(\s*)?\w+\.status\b(?!\s*=)` —— ★ 那个 `(getattr\()?` 前缀**看起来是想覆盖 getattr 形态**，★ 但 `getattr(p, "status")` 里**没有 `.status` 子串**（是 `, "status"`）⇒ ★★ **该分支永远匹配不了真形态，是【死分支】** ⇒ ★ **意图与实现分叉**。

#### ★★ F4 · `selftest-audit.py` —— **三处等价变体全静默**

★ 夹具（含 `def selftest(` 与四条恒真条目），★ 阳性对照命中：

| # | 变体 | ★ 实测 |
|---|---|---|
| A | `cases.append((f"反例", 0 == 0, True))` —— ★ 标签是 **f-string** | ★ **静默** |
| B | `negatives.append(("反例", 0 == 0, True))` —— ★ **列表名不同** | ★ **静默** |
| C | `cases.append(("反例", 3 - 3 == 0, True))` —— ★ **算术恒真** | ★ **静默** |

★ 阳性对照（`cases.append(("正控", 0 == 0, True))`）★ **命中** ✓。
★ 公平说明：★ 该工具**已声明**一条局限（「**跳行赋值**型检不出」）—— ★ 但我这三个变体**都不是**那个形态 ⇒ ★★ **是文档未覆盖的召回缺口**。

#### ★ F5 · `selftest-audit.py` —— **单行重复计数**

★ 阳性对照那一行 `0 == 0` 被**两条模式同时匹配**（「字面量自等 `N == N`」+「字面量相等」）⇒ ★ 列表里出现**两条**。
★ ⇒ ★ 若该工具或下游按「**条数**」统计恒真 ⇒ ★ **会翻倍**。

#### ★★ F6 · **两件工具【不接受路径参数】⇒ 请求件 对象 C 的指令对它们【无法执行】**

| 工具 | ★ CLI | ★ 能否用外部夹具驱动 |
|---|---|---|
| `atomic-write-guard.py` | 仅 `--json/--selftest/--version` | ★★ **不能**（`inventory()` 扫写死的面） |
| `correction-ledger-gen.py` | 仅 `--tail/--ids/--summary/--json/--selftest/--version` | ★★ **不能**（读写死的 `LEDGER`） |

★★ **⇒ 请求件写的「自己构造一个反例输入，看它是否真的报红」—— ★ 对这两件【做不到】。**
★★ 它们**唯一的夹具通道就是作者自己的 `--selftest`** —— ★★ **而那份请求件自己在 对象 C 表头写着「自证不是证据」**。⇒ ★ **这两件的可验证性 = 0（在「外部对抗」这一层）。**
★ 其余八件**可以**（`--root` / `--draft --reference` / `--prompt` / `--dir` / 位置参数）。

#### ★ `live-read-guard.py` —— 正负控**都对**（★ 记录在案）

| 夹具 | ★ 实测 |
|---|---|
| 正控（draft/ref 共享 2 个读数） | `★ 共同读数 2 · 仅本件 0 · 仅旧件 0` ⇒ ★ 正确识别 |
| 负控（ref 无读数） | `★ 一侧无读数 ⇒ 本门【不适用】（★ 不是通过）` ⇒ ★ **三态正确** |

★ 说明：★ 默认门槛 3，★ 我的正控只有 2 条 ⇒ 它报「未见系统性疑似」。★ **这是按声明行事，不是缺陷。**
★ 附一条**设计层观察**（★ 不判为错）：★ 它**按【数】匹配，不按【对象】** —— ★ 若本件写「队列 205 条」、旧件写「端口 205」，★ 会被算成「共同读数」。★ 因其自述是**启发式提示**（「低重合 ≠ 已现测」）⇒ ★ **可接受**，★ 但下游不得把它当判据。

---

## 节二 · 发现的错（按严重度 · 每条带复现命令）

### ★★★ E-1 · `denominator-declare.py` 有可复现的**假阴性**（F1）

★ **复现**（★ 自包含，★ 不依赖仓内文件）：
```bash
cd /Users/coreyleung/dsh-collab
D=$(mktemp -d)
printf '通过率 87%%。\n' > "$D/a.md"                                    # 阳性对照
printf '通过率 87%%。\n本段讲窗口：窗口为 24h，与本数字无关。\n' > "$D/b.md"   # 反例
python3 tools/denominator-declare.py "$D/a.md"   # ★ 期望 未申报口径 1
python3 tools/denominator-declare.py "$D/b.md"   # ★ 实测 未申报口径 0 ⇒ 假阴性
rm -rf "$D"
```

### ★★ E-2 · `false-result-patterns.py` 的 **P2 声明与执行不一致**（F2）

★ **复现**：
```bash
cd /Users/coreyleung/dsh-collab
sed -n '58,59p' tools/false-result-patterns.py     # ★ 标注含 == None or，编译式不含
D=$(mktemp -d)
printf 'import subprocess\nr = subprocess.run(["true"])\nok = r.returncode == None or r.returncode == 0\n' > "$D/x.py"
python3 tools/false-result-patterns.py --root "$D"  # ★ 实测：0 命中
rm -rf "$D"
```

### ★★ E-3 · `false-result-patterns.py` **三处等价变体静默**（F3）

```bash
cd /Users/coreyleung/dsh-collab
D=$(mktemp -d)
printf 'import subprocess\np = subprocess.run(["true"])\ns = getattr(p, "status")\n' > "$D/a.py"
printf 'import subprocess\nr = subprocess.run(["x"])\nif r.returncode not in {0, None}:\n    pass\n' > "$D/b.py"
printf 'DEADLINE = "2026-10-12 08:00:00"\n' > "$D/c.py"
printf 'import subprocess\nr = subprocess.run(["x"])\nif r.returncode not in (0, None):\n    pass\n' > "$D/ctrl.py"  # 阳性对照
python3 tools/false-result-patterns.py --root "$D"   # ★ 实测：命中 1（= ctrl），a/b/c 全静默
rm -rf "$D"
```

### ★★ E-4 · `selftest-audit.py` **三处等价变体静默 + 单行重复计数**（F4/F5）

```bash
cd /Users/coreyleung/dsh-collab
D=$(mktemp -d)
cat > "$D/t.py" <<'PY'
def selftest():
    cases = []
    cases.append(("正控", 0 == 0, True))
    cases.append((f"变体A", 0 == 0, True))
    negatives = []
    negatives.append(("变体B", 0 == 0, True))
    cases.append(("变体C", 3 - 3 == 0, True))
    return 0
PY
python3 tools/selftest-audit.py --root "$D"
# ★ 实测：只命中「正控」一行，且该行被【两条模式各报一次】⇒ 变体 A/B/C 静默
rm -rf "$D"
```

### ★★ E-5 · 两件工具**不可外部驱动**（F6）

```bash
cd /Users/coreyleung/dsh-collab
grep -n 'add_argument' tools/atomic-write-guard.py tools/correction-ledger-gen.py
# ★ 实测：两件都【没有】路径参数 ⇒ 请求件 对象 C「构造反例输入」对它们做不到
```

### ★★ E-6 · **v7 §0.1.3 的 `自证 6/6` 是过期值**（★ 上轮 E1 的收口）

```bash
cd /Users/coreyleung/dsh-collab
python3 tools/false-result-patterns.py --selftest | tail -2   # ★ 实测 10/10
grep -n '自证 6/6' docs/distributed-agent-network-governance-plan-v7-20261012.md
```

### ★ 汇总表

| 编号 | 对象 | ★ 形态 | 严重度 |
|---|---|---|---|
| **E-1** | `denominator-declare.py` | ★★ **假阴性**（邻句口径词洗白） | ★★★ |
| **E-2** | `false-result-patterns.py` | ★★ 声明与执行不一致（P2 死支） | ★★ |
| **E-3** | `false-result-patterns.py` | ★ 三变体静默（过拟合） | ★★ |
| **E-4** | `selftest-audit.py` | ★ 三变体静默 + 单行双报 | ★★ |
| **E-5** | 两件工具 | ★★ 不可外部驱动 ⇒ 可验证性=0 | ★★ |
| **E-6** | v7 §0.1.3 | ★ 自证数过期（6/6 → 实为 10/10） | ★★ |

★ **它们共同的一族**：★★ **「工具跑得好好的，在报一个假结果」** —— ★★ 与 v7 §0.1.3 自述的那一族**同形**。★ 十件工具**自证全绿**，★ 而其中**四件**在**等价变体**上静默、**一件**有可复现假阴性。⇒ ★★ **「自证 N/N 全绿」不能推出「它能抓到那一类」。**

---

## 节三 · 我的限制

### 3.1 ★ 本轮**做了**什么

- ★ 十条 `--selftest`：★ **真跑**，★ 报 命令 + 原始输出 + 退出码（节一 1.1）。
- ★ 四件工具的**输入域对抗测试**：`false-result-patterns` · `selftest-audit` · `denominator-declare` · `live-read-guard`（节一 1.3）。
- ★ 两件工具的**不可驱动性**已实测（F6）。
- ★ 工具**指纹跑前=跑后** ⇒ 证明我未改动它们（§3.4）。

### 3.2 ★ 本轮**没有**做

| 面 | ★ 状态 |
|---|---|
| ★ 对象 A「抽查锚点可复跑性 ≥ 8 条」 | ★★ **未做** |
| ★ 对象 B（W1/W2 三切口） | ★★ **未做** |
| ★ 余下 6 件的**输入域对抗**（`lint-inventory` · `subagent-work-checklist` · `slo-target-form` · `bus-pending-age` · `atomic-write-guard` · `correction-ledger-gen`） | ★ **只跑了 `--selftest`**，★ **未构造反例** |
| ★ 两件不可驱动的工具 | ★★ **结构上做不到**（F6） |

### ★★ 3.3 判读这三条（★ 必须与结论一起读）

1. ★★ **「静默」≠「缺陷确证」** —— ★ 我构造的是**我判定的**「同一缺陷类的等价形态」；★ **作者可能认为该形态超出其设计范围**。★ ⇒ ★ **每个静默都需作者确认一次**（★ 这与我给 `false-result-patterns` P1 的**同一条**免责一致：★ 命中 ≠ 缺陷）。
2. ★★ **F1（假阴性）比 F3/F4（静默）强** —— ★ 因为 F1 里数字**确实没分母**，★ 那是**确定的错**；★ F3/F4 是**召回缺口**。
3. ★★ **我的对照也自指** —— ★ 夹具我造、判读我下 ⇒ ★ **本文一切判定都附复跑命令**，★ 请**第三方复跑**后再入库（★ 见 §四）。

### 3.4 ★ 指纹（★ 证明本轮未改任何文件）

```
工具（跑前 = 跑后）：
  ec4b41a5245a07f8  tools/false-result-patterns.py
  ef30344766c7c26f  tools/selftest-audit.py
  b1d672480a1d413d  tools/denominator-declare.py
  78e014c45080670b  tools/live-read-guard.py
  eafa7d378187acca  tools/atomic-write-guard.py
```

---

## 四 · 复跑块（绝对路径 · 自包含 · ★ 夹具自建自清，★ 不依赖仓外留存）

```bash
cd /Users/coreyleung/dsh-collab

# ── 节一 1.1：十条自证（★ 期望十条 rc=0，收尾行 N/N 与请求件表逐个相符）
for t in false-result-patterns selftest-audit lint-inventory subagent-work-checklist \
         slo-target-form bus-pending-age atomic-write-guard denominator-declare \
         correction-ledger-gen live-read-guard; do
  echo "===== $t"; python3 "tools/$t.py" --selftest 2>&1 | tail -2; echo "rc=$?"; done

# ── E-1：denominator-declare 假阴性（★ 本轮最重）
D=$(mktemp -d)
printf '通过率 87%%。\n' > "$D/a.md"
printf '通过率 87%%。\n本段讲窗口：窗口为 24h，与本数字无关。\n' > "$D/b.md"
python3 tools/denominator-declare.py "$D/a.md"    # 期望 未申报口径 1
python3 tools/denominator-declare.py "$D/b.md"    # 实测 未申报口径 0 ⇒ ★ 假阴性
rm -rf "$D"

# ── E-2：P2 声明与执行不一致
sed -n '58,59p' tools/false-result-patterns.py

# ── E-3 / E-4：等价变体静默（★ 见节二各条完整夹具）
# ── E-5：两件不可驱动
grep -n 'add_argument' tools/atomic-write-guard.py tools/correction-ledger-gen.py

# ── E-6：v7 自证数过期
grep -n '自证 6/6' docs/distributed-agent-network-governance-plan-v7-20261012.md
```

---

## 五 · ★ 独立性声明（★ 与上两轮一致）

- ★★ **我能提供的**：★ **① 认知独立性**（不同会话）+ ★ **本轮的执行**（★ 真跑了工具、真造了反例）。
- ★★ **我拿不出的**：★ **② 设备独立性**（★ 我就在本机）；★★ **③ 主体独立性**（★ 同一 OS 账户 `coreyleung`）。
- ★★★ **本件结论不能自证**：★ 夹具我造、工具我跑、判读我下 ⇒ ★★ **全部在同一账户下** ⇒ ★ **判据自指**。★ 故本件**每条都附复跑命令**，★ **请第三方复跑**。
- ★★ **本件不宣布任何事项闭合**（S3）。★ **不代裁**：★ 该不该改这些工具、哪些「静默」算缺陷 —— ★ **是作者与用户的事**。

---

*（外部线 `ext` · 2026-10-13 · ★ **已授权执行** · ★ **未修改任何文件** ✅ 指纹一致 · ★ **本审结论不自证**）*
