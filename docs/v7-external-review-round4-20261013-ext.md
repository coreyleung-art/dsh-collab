# v7 · 第四轮外部审查（ext · 复核第三轮之后的新修与新接线）

> **整理**：2026-10-13T04:4x+08:00 · 外部线 ext（Claude Code 会话 `005a2c58`）
> **对象**：`docs/v7-fourth-round-request-20261013.md`（116 行）
> **前三轮**：审查件（261）· 执行件（317）· 第二轮（456）· 第三轮（364）
> **本件性质**：★ 只新建、不改任何既有文件 · ★ 所有读数均附**原始输出 + 退出码**（rc 一律在管道前取）

**五条纪律**：①无原始输出即「未跑 ⇒ 不可判」②三态（成立/不成立/不可判）③凡报「0」附【扫过的面】、凡报「未搜到」先给【阳性对照】④每个「静默」只是**召回缺口**、标「需作者确认」⑤不以三个点断趋势。
**边界**：★ 本机之内（同一 OS 账户）我只到**①认知独立**；②设备独立/③主体独立**均不可判** ⇒ ★ **我不构成独立审查**（见节四尾）。

---

## 节一：「本轮已修清单」（请求件 §二 8 行）逐条复核

| # | 原发现（轮3） | 三态判 | ①原情形复现？ | ②过宽/过严？ | ③新引入的错？ |
|---|---|---|---|---|---|
| **F-5** | G-CR3 两自证非真调（恒真/恒假） | ★ **不成立**（已修） | 否 | 无 | 无（旧调用点向后兼容） |
| **E-1** | 修得过严（紧邻下句口径误判红） | ★ **部分修** | 否（过严已消） | ★★ **过宽成立** | ★ **是**（同族假绿，单行变体） |
| **F-1** | 只提一个 token 仍放行 | ★ **不成立**（已修） | 否 | 无 | 无 |
| **F-10** | `bus-pending-age` 三态塔缩 | ★★ **未接线（死码）** | ★ **是**（仍塔缩） | — | ★ **是**（算了却丢） |
| **F-11** | `pitfalls-cli list` 崩（KeyError） | ★ **部分修** | 否（`list` 本体好） | — | ★ **同族漏修**（3 兄弟面仍崩） |
| **E-5** | 两件无法外部驱动 | ★ **不成立**（已修） | 否 | 无 | ★ 一处**消息引用错对象**（小） |
| **新 1** | 请求件 §三 九件行数全 +1 | ★ **不成立**（已修） | 否 | — | 无 |
| **新 2** | 轮1 请求件 `:67`「5 次/其中 6 次」 | ★ **不成立**（**未改**） | ★ **是**（原文仍在） | — | — |

> ★★ **作者特别叮嘱项（共用签名 + 两个 CLI 参数面）—— 三条我全验了**：
> - `gcr3(root=None)`：★ 旧调用点仅 `:349` registry（无参）⇒ 走默认面，**向后兼容** ✓
> - `atomic-write-guard --path` / `correction-ledger-gen --path`：★ **传参真驱动** ✓ · **不传走原面** ✓
> - ★★ **但「加参数没接线」在 F-10 又出现了一次**（见下）—— 与作者自曝两次同族。

---

### F-5 · G-CR3 自证真调 —— ★ 不成立（已修）

**原发现**：`:412-431` 两条自证是**恒真/恒假**（判据不调被验对象）。

**我跑了什么**：`python3 tools/gcr-gate.py --selftest`

**原始输出**（rc 在管道前取）：
```
  rc=0
  ★ G-CR 门自证：逐条用合成负例/正例证明判据可判
    ✅ G-CR3 负例：★ 真调 `gcr3(<name≠目录名>)` ⇒ 必须 FAIL（实得 True）
    ✅ G-CR3 反控：★ 真调 `gcr3(<name=目录名>)` ⇒ 必须 PASS（实得 True）
    自证：9/9
```
代码位佐证：`:425 _v_neq,_d_neq = gcr3(d_neq)` · `:426 _v_eq,_d_eq = gcr3(d_eq)`（真造 `dsh-plugin-wrongname` / `dsh-plugin-rightname` 两目录并真调）。

**三态判**：★ **①不成立**（原情形不再复现——现为真调）。★ **②无过宽/过严**：`gcr3()` 无参 → `root = Path(root) if root is not None else HOME/"dsh-plugin-central-inbox"` ⇒ 默认面不变；旧调用点仅 `:349` registry（无参）⇒ 行为不变。★ **③无新错**。

---

### E-1 · 句界分级 —— ★ 部分修（过严已消，**过宽成立**）

**原发现**：紧邻下句的口径被误判为「不同单元」⇒ 该绿的判红（过严）。

**我跑了什么**：`python3 tools/denominator-declare.py <夹具>`（★ 位置参数 path，非 `--file`），8 个夹具两向测。

**原始输出**：
```
  a.md                 rc=1      # 通过率 87%（裸、无口径）        ⇒ 该红，真红 ✓
  b.md                 rc=1      # 87%。\n本段讲窗口：窗口为24h…   ⇒ 强界，真红 ✓
  c.md                 rc=0      # 87%。本段口径：分母为全部请求。 ⇒ 该绿，真绿 ✓（过严已修）
  d.md                 rc=0      # 87%（口径：分母=全部请求）。     ⇒ 真绿 ✓
  e_weak_ok.md         rc=0      # 同 c                           ⇒ 真绿 ✓
  f_weak_unrelated.md  rc=0  ❌  # 87%。本段讲窗口：窗口为24h，与本数字无关。
  g_strong_block.md    rc=1      # 87%\n本段口径：分母为全部请求。   ⇒ 强界，真红 ✓
  h_跨两个弱界.md       rc=1      # 87%。第一句无关。第二句口径：… ⇒ 跨两弱界不算 ✓
```
机制（`denominator-declare.py:52`）：★ **口径词 = 窗口/分母/样本/面**；`f` 的「窗口」是口径词，被**跨一个弱界**纳入 ⇒ 判「同单元」。

**三态判**：
- ★ **②过严已修**（`c.md` rc=0；对照轮1 曾误判红）——修法**针对的那一半是对的**。
- ★★ **②过宽成立**：`f_weak_unrelated.md` 的次句自陈「**与本数字无关**」，仅因含口径词「窗口」即被判同单元 ⇒ rc=**0**。**同一内容仅差 `\n` vs 空格**：`b.md`（`\n` 强界）rc=**1**、`f`（弱界同行）rc=**0** ⇒ 判据**过宽**。
- ★ **③新引入的错成立**（与②同源）：这是轮1 原发现的**同族假绿**在「单行/弱界」变体下复现 ⇒ 修法把过严换成过宽，**未把两半同时做对**。
- ⚠ **需作者确认**：这是**召回缺口**（口径词表 + 弱界跨一个的组合面），不是「判据恒真」的硬缺陷；**如何区分「同段无关句」与「同段真口径句」是否属判据能力之内，请作者裁**。

---

### F-1 · `lint-inventory` hits ≥ 2 —— ★ 不成立（已修）

**我跑了什么**：`python3 tools/lint-inventory.py --selftest`

**原始输出**：
```
  rc=0
    ✅ 正控：--prompt 输出可直接粘用
    自证：6/6
```
**三态判**：★ **①不成立**（单 token 旁路已闭——现要求 hits≥2 或含「既有 lint」短语）。★ **②无过宽/过严**、★ **③无新错**（自证断言与判据同步：6/6）。

---

### F-10 · `bus-pending-age` 不可判栏 —— ★★ **未接线（死码）**

**原发现**：三态塔缩——「不可判」（无 `ts` 推不出龄）被当成「未超时」，静默并入 `pending`。

**我跑了什么**：`python3 tools/bus-pending-age.py --dir /Users/coreyleung/busfrtmp --ttl-hours 24 --json`
夹具：`a.json={"sent":false,"ts":30天前}` · `b.json={"sent":false}`（**无 ts**）· `c.json={"sent":false,"created":30天前}`（**无 ts**）

**原始输出**：
```
  rc=0
  {
   "total": 3,
   "pending": 3,
   "should_be_expired": 1,
   "marked_expired": 0,
   "oldest_pending_hours": 720.4,
   "oldest_pending_days": 30.0,
   "ttl_hours": 24.0,
   "now": "2026-10-13T04:44:09.558911+08:00"
  }
  ── 输出里有无 undecidable 键 ──  （无）
```
代码位：
- `:71 "undecidable": (o.get("sent") is not True) and (age_h is None)` —— **算了**
- `:79-82 res["undecidable_count"] / res["undecidable_keys"]` —— **算了**
- `:90-98 summarize()` 返回**字面量**只含 `total/pending/should_be_expired/marked_expired/oldest_pending_*/ttl_hours/now` ⇒ ★★ **`undecidable` 被丢**；main 打印/JSON-dump 的是 `s = summarize(res)`。

**三态判**：
- ★ **①原情形仍复现**：夹具 `b`/`c` 无 `ts` ⇒ 应判「不可判」，实得 `pending=3` 且**无 undecidable 键** ⇒ **三态塔缩依旧**。
- ★★ **③新引入的错（死码）**：新栏在 `scan()`/`summarize()` 前段算了，却在 **`summarize()` 返回处被丢** ⇒ 文本与 JSON **都不出现** ⇒ 「加了栏但没接线」——★ 与本轮作者自曝的两次**同族**（请求件 §二·`★ 作者已自曝两次`）。
- ⚠ 注：读的是**我造的无 `ts` 夹具**；作者若要判「真实语料是否受影响」，轮2 已测 `send-instructions/` **122/122 有 `ts`**。

---

### F-11 · `pitfalls-cli.py` —— ★ 部分修（`list` 本体好，**3 个兄弟面仍崩**）

**原发现**：`list` 直取 `i['severity']` ⇒ 缺该键的条目抛 `KeyError`、整命令崩。

**我跑了什么**：★ 直接拿**真实数据**（`docs/pitfalls/pitfalls.json`，11 条，其中 `cloudbase-deploy-verify-hash-20260910` 缺 `severity`/`title`）跑四个命令面。

**原始输出**：
```
  rc=0  ← pitfalls-cli.py list
          [P1] 2026-08-30-http-header-empty-auth · 无 token 时 HTTP 头提前结束…
          [?] cloudbase-deploy-verify-hash-20260910 · ?
  rc=1  ← pitfalls-cli.py list --severity SOP       KeyError: 'severity'  (:131 i["severity"])
  rc=1  ← pitfalls-cli.py query 部署                 KeyError: 'severity'  (:144 i['severity'])
  rc=1  ← pitfalls-cli.py stats                      KeyError: 'severity'  (:152 i["severity"])
  （export 未跑——会写盘到 ~/dsh-collab/docs/pitfalls/；代码位 :162-163 直取 i['title']/i['severity']）
```
**三态判**：
- ★ **①部分不成立**：`list` 本体 rc=**0**（`:136` 已 `.get(...,'?')`）——修的那处**真好**。
- ★★ **③同族漏修**：`list --severity`（`:131`）· `query`（`:144-145`）· `stats`（`:152`）**仍直取** ⇒ 在**真实数据上立即崩**；`export`（`:162-163`）同型。⇒ **修了一处，漏同族其余处**（与 E-1/F-10 不同族，属「漏改」）。
- ⚠ **需作者确认**：`--severity` 是**正常用法**，非边角 ⇒ 建议同一 `.get` 口径推广至四处。

---

### E-5 · 两件 `--path` seam —— ★ 不成立（已修）＋ ★ 一处小错

**原发现**：`atomic-write-guard` / `correction-ledger-gen` 只扫固定面 ⇒ 外部驱动不动、永为 S3 自证。

**我跑了什么**：两件各跑「传参 / 不传 / 传不存在」三面（正控夹具 `~/e5fix`、`~/clgfix/ledger.md`）。

**原始输出**：
```
  # atomic-write-guard（夹具 e5fix：scripts/raw_crit.py 直写 deviation-ledger 无 os.replace）
  rc=1  ← --path /Users/coreyleung/e5fix
          ★★ CRITICAL  ../e5fix/scripts/raw_crit.py  目标="deviation-ledger-20261011  os.replace=False
          ❌ 1 处危险：关键文件直写且无 os.replace
  rc=0  ← --path /Users/coreyleung/e5fix --json      ★★ JSON 列了 CRITICAL/false…却 rc=0（见节四 a）
  rc=0  ← 不传 --path（走原面 tools/ scripts/）       ✅ 关键文件无未保护直写

  # correction-ledger-gen
  rc=0  ← --path /Users/coreyleung/clgfix/ledger.md   == …共 2 条==（D-001/D-002 真解析）
  rc=2  ← --path /Users/coreyleung/nope-does-not-exist.md
          ★ 台账不可读 ⇒ 本门【不可判】（★ 不冒充通过）: /Users/coreyleung/dsh-collab/docs/deviation-ledger-20261011.md
  rc=0  ← 不传（原面）  == …共 280 条==
```
接线佐证：`atomic-write-guard.py:162 items = inventory(getattr(a,'path',None))`（`:89 def inventory(root=None)`，默认 `ROOT`）· `correction-ledger-gen.py:181 ents = load_entries(getattr(a,'path',None))`（`:34 def load_entries(path=None)`，`:35 p = path or LEDGER`）。

**三态判**：
- ★ **①不成立**（已修）：★ **传参真驱动**（正控 rc=1、夹具台账 rc=0/2 条）· ★ **不传走原面**（atomic rc=0 原面；clg rc=0·280 条）——两向**都真**。
- ★ **③新引入的小错**：`correction-ledger-gen.py:183` 不可读分支打印 `% LEDGER`（**默认台账**）而**非** `a.path` ⇒ ★ 我传 `nope-does-not-exist.md`，消息却点名 `docs/deviation-ledger-20261011.md` ⇒ **消息引用了错的对象**（行为 rc=2「不可判」正确，仅路径名错）。⚠ 属**新 seam 分支**上的小错，建议改打印 `p`。
- ★★ **副产品**：正是 E-5 的 seam 让 `atomic-write-guard --json` 的**假绿**首次**可被外部观测**（节四 a）。

---

### 新 1 · 「九件行数全 +1」 —— ★ 不成立（已修）

**我跑了什么**：对本件 §三 10 件逐件 `wc -l` + `shasum -a 256`（详见节三）。
**判**：★ 轮3 §三 的 6 件**重叠项**（锚点/台账/denominator/false-result-patterns/lint-inventory/gcr-gate）当时全为「实得 **+1**」，**本轮全逐字对上** ⇒ **口径已改用 `wc -l`** ⇒ ★ **不成立（已修）**。

---

### 新 2 · 轮1 请求件 `:67`「5 次/其中 6 次」 —— ★ 不成立（**未改**）

**我跑了什么**：读 `docs/v7-external-review-request-20261013.md:67`。
**原始输出**：
```
  :67  > ★ 本纳已发现 **5 次「它看起来对而实为假」** —★ ★★ 而其中 **6 次**涉及本纳自己写的代码（★ #3·#5·#6·#8·#9·#10）。
```
**判**：★ 原文仍在（列了 **6** 项 `#3·#5·#6·#8·#9·#10`，却写「其中 **6 次**」← 前句「发现 **5 次**」）⇒ **未改**。★ 与本件 §二「新 2 · ★ 待本轮改」一致，非「说法与实测不符」，仅**尚未处理**。

---

## 节二：F-9 文案改法的核实

**问题**（请求件 §二·二）：「那一行文案真的加了吗？加得对吗？」

**我的修法建议原话**（轮3 报告 `:170`）：
> ★ **不改判据**；只在**报告文案**里加一行「F4 为**词表召回**：表外形容词不会单列 F4，只会以 F1/F3 缺失呈现」。

**「报告文案」指什么**：★ 指**工具自身的报告段**（`tools/slo-target-form.py` 的输出区 `:207-229`）——**不是**某个 docs 件。

**我跑了什么 / 原始输出**：
```
# ① 工具文件现况
  $ git log --oneline -1 -- tools/slo-target-form.py
    9aa5919 auto-snapshot 2026-10-12T22:47:47
  $ stat -f '%Sm' tools/slo-target-form.py
    Oct 12 22:47:25 2026          # ★ 早于轮3 报告成文时刻
  $ stat -f '%Sm' docs/v7-external-review-round3-20261013-ext.md
    Oct 13 04:21:20 2026          # ★ 我的建议晚 5.5h 才写

# ② 内容面（扫过的面 = 全仓 docs/ tools/ scripts/）
  grep -rn '词表召回' docs/ tools/ scripts/
    docs/v7-external-review-round3-20261013-ext.md:170:…「F4 为**词表召回**：表外形容词…」   ← 阳性对照：我的建议可被搜到
  grep -rn '表外形容词' docs/ tools/ scripts/   → 0 命中
  grep -rn 'F-9' docs/ tools/ scripts/          → 仅台账（未改/待处 语境）
  grep '召回' tools/slo-target-form.py          → 0 命中
```
**★ 阳性对照**：`词表召回` 在全仓**只**出现在我轮3 报告里 ⇒ 检索式**有效**；若作者加过同类文案，必被命中。

**三态判**：
- ★ **「那一行文案加了吗」= 不成立（未加）**：
  - 工具 `slo-target-form.py` **mtime 2026-10-12 22:47:25**、末次 commit `9aa5919`（10-12 22:47:47）——**早于**我轮3 建议成文（10-13 04:21:20）⇒ 该文件**不可能**含针对轮3 的改动；
  - 该工具报告段 `:207-229` 有 F4-vs-非 F4 的诚实声明，但**无「词表召回」一行**；`docstring :16` 仍是「目标若只由形容词构成 ⇒ fail」无召回限定；
  - ★ 作者**自己的台账** `D-281`（`deviation-ledger:7957`）亦记：「**不可判** | ★ **F-9 的文案改法（★ 本轮未改）**· 新1/新2（★ 本轮未改）」，且 `D-281 「本轮已把它们全修完」` 只列 **F-11/F-10/E-5**，**无 F-9** ⇒ **台账与实测一致**，非「说法与实测不符」。
- ★ **「加得对吗」= 不可判（因未加）**。★ 但**内容正确性**可先判：轮3 已实测「稳健」→ FAIL 走 **F1 无量**（`f4_meta_adj=[]`）、正控「端口固定」→ 命中 F4 ⇒ 我那句「F4 为词表召回、表外形容词以 F1/F3 缺失呈现」**与实测一致** ⇒ 若照此加，措辞**对**。
- ⚠ **需作者确认（措辞歧义）**：本件 `:79「作者采纳了『只改报告文案』」` 紧邻 `:80「而作者未处理的是 F-9 的文案改法」`——「采纳」与「未处理」并置，读者易误读为「已改」。★ 建议：明确写「**已采纳该方向，本轮未实施**」。

---

## 节三：锚点与家族件读数的复算（10 件）

**方法**：`wc -l < 件` 与 `shasum -a 256 件 | cut -c1-16` 逐件复算（照请求件 §三 顺序）。

| 件 | 声称 `wc -l` | 实得 | 声称 sha16 | 实得 sha16 | 判 |
|---|---|---|---|---|---|
| `docs/distributed-agent-network-governance-plan-v7-20261012.md` | 314 | 314 | `4a860c5b8ecdc316` | `4a860c5b8ecdc316` | ✅ |
| `docs/deviation-ledger-20261011.md` | 7934 | **8000** | `a487d176ab02333f` | `4a040b6585ad61c7` | ❌（见下） |
| `tools/denominator-declare.py` | 248 | 248 | `308d8a5efef4fce5` | `308d8a5efef4fce5` | ✅ |
| `tools/false-result-patterns.py` | 375 | 375 | `721037405a019b4e` | `721037405a019b4e` | ✅ |
| `tools/lint-inventory.py` | 202 | 202 | `832a195d3c2acb5c` | `832a195d3c2acb5c` | ✅ |
| `tools/gcr-gate.py` | 678 | 678 | `afcc8be705819254` | `afcc8be705819254` | ✅ |
| `tools/bus-pending-age.py` | 211 | 211 | `c575acaab51acad6` | `c575acaab51acad6` | ✅ |
| `tools/atomic-write-guard.py` | 184 | 184 | `ca10fe007ee346d5` | `ca10fe007ee346d5` | ✅ |
| `tools/correction-ledger-gen.py` | 210 | 210 | `341ca95a7ba06759` | `341ca95a7ba06759` | ✅ |
| `scripts/pitfalls-cli.py` | 226 | 226 | `1cd411d448ff3c95` | `1cd411d448ff3c95` | ✅ |

**唯一不符（台账）的定性**：★ 台账是 **append-only** 且持续增长。查 git（`git show <sha>:docs/deviation-ledger-20261011.md | wc -l`）：
```
  81e9af0  2026-10-13 04:27:04   wc-l=7934      ← ★ 恰为请求件所写 7934
  fe3d69c  2026-10-13 04:37:45   wc-l=7966      ← 请求件成文(04:37:07)后 38s 才 append
  d80133c  2026-10-13 04:41:09   wc-l=8000      ← 现读
```
⇒ ★ **「复算不符」成立、「作者写错」不成立**——声称值**在写时正确**（04:37:07 时最新版 `81e9af0` 正是 7934）。★ sha16 同理（会变）。⇒ **既非缺陷，亦非新实例**。

**★★ 特别核：「上一轮『全部 +1』是否已修」**：
- 轮3 §三 与轮4 §三 **重叠 6 件**：锚点、台账、denominator-declare、false-result-patterns、lint-inventory、gcr-gate。
- 轮3 声称（例）锚点 **315**、false-result-patterns **376**、lint-inventory **191**、gcr-gate **666** ⇒ 均为「实得 **+1**」（`len(read().split('\n'))` 尾部空行所致）。
- ★ **本轮这 6 件全逐字对上**（除台账因 append 变动） ⇒ ★ **+1 口径已修** ⇒ **新1 = 不成立（已修）**。

---

## 节四：同类新实例 + 我的限制

### 4.1 新实例（「工具/文档跑得好好的，在报一个假结果」）

**（a）★★ `atomic-write-guard --json` 恒 rc=0 —— 假绿（★ 预存，本轮首次可外部观测）**
- 证据：同一红色夹具 `~/e5fix`，`--path`（非 json）rc=**1**、`--path --json` rc=**0**；而 JSON **明列** `{"file":"…/raw_crit.py","kind":"CRITICAL","has_os_replace":false}`。
- 代码位：`tools/atomic-write-guard.py:163-165 if a.json: print(json.dumps(items)); return 0` —— **提前 return**，把 rc 判定（`:176-179 crit → return 1`）**置于不可达**。⇒ 消费方若读 `--json` 的**退出码**（而非解析内容），**永远绿**。
- ★ **预存性（如实标注）**：`git show dc74055:tools/atomic-write-guard.py`（**2026-10-12 22:28:50**）**已含** `:160 if a.json: … :162 return 0`、`:172 crit =` ⇒ ★ **非本轮引入**；本轮只加了 `--path` seam（行号 +3）。⇒ 按纪律：★ **报「预存实例」而非「本轮新错」**。
- ⚠ **需作者确认**：是否属有意（`--json` 仅作数据导出、rc 无语义）？若是，建议在 `--help`/README 写明「`--json` 不反映 rc」；若不是，rc 判定须提到 `--json` 分支之前。

**（b）★★ F-10 `undecidable` 死码** —— 已在节一详列（算了却丢）⇒ 同族「加了栏但没接线」。

**（c）★ F-11 三兄弟面漏修**（`list --severity`/`query`/`stats` 仍崩）⇒ 同族「修一处漏其余」。

**★ 未列入的对照**：★ 锚点 附D 台账条数（274/276 vs 实测）——**轮3 已报**（`F-7 部分修`），按「不重做前三轮」**排除**。

**★ 阳性对照**：以上三条均有 rc 与代码位，非「文件里有这个模式」的升格。

### 4.2 我不构成独立审查（★ 声明）

- ★ **独立性三层**：①认知独立 ≠ ②设备独立 ≠ ③主体独立（=「不同委托方」）。R046/S3 要的是 **③**。
- ★ 我运行于**同一 OS 账户、同一台机**：能提供的是 **①**（换了执行体），**②不可判**、**③不可判**（委托方仍是同一位用户）。
- ★★ 故**我不构成独立 verifier**；本件是**同机外部线的对抗性复核**，**不能**用于主张任何事项「已闭合」（S3）。

### 4.3 我的限制（须与结论同读）

1. ★ **只有我跑过的才可判**：未跑的一律「不可判」。本件**唯一未跑**是 `pitfalls-cli export`（会写盘）——其判据按**代码位同型**推，**运行未验** ⇒ 标**不可判**。
2. ★ **凡「静默/0 命中」都是召回缺口**，非缺陷确证：E-1 的「无关同段句」（4.1 之外 ⚠ 已标「需作者确认」）、F-11 未穷举的全部命令面。
3. ★ **不以三个点断趋势**：本件未对任何「趋势」下判；若要谈「加参数没接线」是否成趋势，需先说清**点数·窗口·判据**——本件只记：★ **F-10 是本轮第 3 次同族**（作者自曝 2 + 本轮 1），**样本 = 3、窗口 = 本轮、判据 = 「算了却丢/加了没接线」**，**不足以**断「恶化」或「收敛」。
4. ★ 读的是**我自建的仓外夹具**（`~/e5fix`·`~/clgfix`·`~/ddtmp`·`~/busfrtmp`·`~/slofrtmp`）；真实语料面见各条注。
5. ★ **本件只新建一个文件**，未改任何既有件。

---

## 附 A · 自包含复跑命令（不含 `/tmp`；rc 均在管道前取）

```bash
cd /Users/coreyleung/dsh-collab

# F-5 真调自证
python3 tools/gcr-gate.py --selftest > /tmp/f5.out 2>&1; echo "rc=$?"; grep -E 'G-CR3|自证' /tmp/f5.out

# F-1
python3 tools/lint-inventory.py --selftest > /tmp/f1.out 2>&1; echo "rc=$?"; tail -3 /tmp/f1.out

# F-10（造无 ts 夹具后）
mkdir -p /tmp/busfix
printf '{"sent":false,"ts":"2026-09-13T04:17:49+08:00"}\n' > /tmp/busfix/a.json
printf '{"sent":false}\n'                                  > /tmp/busfix/b.json
python3 tools/bus-pending-age.py --dir /tmp/busfix --ttl-hours 24 --json > /tmp/f10.out 2>&1; echo "rc=$?"; cat /tmp/f10.out
grep -c undecidable /tmp/f10.out        # ★ 预期仍是死码：0

# F-11（真实数据即含缺 severity 的条目）
python3 scripts/pitfalls-cli.py list                 > /tmp/p1 2>&1; echo "rc=$?"
python3 scripts/pitfalls-cli.py list --severity SOP  > /tmp/p2 2>&1; echo "rc=$?"   # ★ 预期 1
python3 scripts/pitfalls-cli.py stats                > /tmp/p3 2>&1; echo "rc=$?"   # ★ 预期 1

# E-1（位置参数 path，非 --file）
python3 tools/denominator-declare.py /Users/coreyleung/ddtmp/f_weak_unrelated.md > /tmp/e1 2>&1; echo "rc=$?"  # ★ 预期 0（过宽）

# E-5 两件（★ --json 假绿对照）
python3 tools/atomic-write-guard.py --path /Users/coreyleung/e5fix      > /tmp/x1 2>&1; echo "rc=$?"  # ★ 预期 1
python3 tools/atomic-write-guard.py --path /Users/coreyleung/e5fix --json > /tmp/x2 2>&1; echo "rc=$?" # ★ 预期 0（假绿）
python3 tools/correction-ledger-gen.py --path /Users/coreyleung/clgfix/ledger.md > /tmp/x3 2>&1; echo "rc=$?"

# 节三
for f in docs/distributed-agent-network-governance-plan-v7-20261012.md tools/gcr-gate.py scripts/pitfalls-cli.py; do
  printf '%s  %s  %s\n' "$(wc -l < "$f" | tr -d ' ')" "$(shasum -a 256 "$f" | cut -c1-16)" "$f"
done
```

## 附 B · 本次扫过的面（供「0 命中/未搜到」的可核性）

- **文件面**：`docs/` · `tools/` · `scripts/`（`grep -rn` 全递归）
- **git 面**：`git log/show` 于 `tools/slo-target-form.py`、`tools/atomic-write-guard.py`、`docs/deviation-ledger-20261011.md`
- **运行面**：`gcr-gate · lint-inventory · denominator-declare · bus-pending-age · pitfalls-cli(4 面) · atomic-write-guard(3 面) · correction-ledger-gen(3 面)`
- **未跑面**：`pitfalls-cli export`（写盘）— ★ 标**不可判**
