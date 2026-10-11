# xdom-directory.py · 变更日志

> **版本单一来源**：脚本内 `VERSION` 常量（★ 本文件**只记历史**，**不构成**第二个版本声明）。
> `python3 docs/xdom-index/xdom-directory.py --tool-version` 会自动反查源码自证「只有一处声明」。
> ★ 依据 R006 ⑥（版本管理）。★ 本文件**不宣布任何版本「已验证」**——验证归独立方。

每条格式：`## [版本] 日期 · 触发事件` → 改动逐条 → **该项的控制是什么** → 复跑。

---

## [0.4.2] 2026-10-12 · ★ 触发事件是**把 ⑧ 卡真的推上板之后，回头读自己推上去的那张卡**

**触发**：⑧ 落链由外部写手（`tools/bb_dualwrite.py`）**真的落地**后，回读板上的卡 ——
★ 卡里写着「★ pull-only（有已知风险）… 该链目前只能由**人/别的工具 pull 后落地**」。
★★ 而那张卡**正坐在板上**说自己是 pull-only。

★ **三态，我说准**：★ 那句话**不是假话** —— 逐句都成立（本工具确实无写原语、确实须外部代理）；
★ 但「**pull-only**」这个**标签**会被**合理地读成【状态陈述】**（＝该链尚未落地），
★ 而那个**状态已经变了** ⇒ ★ 这是**易误导**，**不是错误**。★ 两者不可混为一谈。

★★ **根因（★ 同族：判据不得自指）**：★ **卡描述不了自己落地这件事** ——
卡是**推板之前**生成的；它一旦被推上板，卡里任何「尚未推板」式的**状态自述当场作废**，
★ 而且**自相矛盾在字面上就看得见**（卡在板上说自己不在板上）。

### 改动

| # | 改动 | 它的**控制**是什么 |
|---|---|---|
| ① | ⑧ 卡**只留【机制】陈述，删掉【状态】陈述**：改述为「本工具无写原语 ⇒ 落链须由外部写手代理；**本卡不自述板状态，请读板判定**」 | ★ **键名 `r006_8_gap` 沿用不改**（不破坏既有消费方）· 断言：文本**不得**再含 `pull-only`，**必须**含「不自述板状态」 |
| ② | `VERSION` → `0.4.2` | R006 ⑥ `--tool-version` 自证单一来源 |

★ **修法不是改口，是把状态从卡里拿掉** —— 机制一句话恒真，状态**由读板得出**。

### ★★ 同时记一处结构性张力（★ 不是缺陷，是**两条要求互斥**）

★ **R006 ⑧ 说「自动落链」**（工具自己写板）· ★ **本支的只读结构门说「代码面无写原语」**
⇒ ★ **同一支工具不可能同时满足这两条** —— 它最强的安全属性**正是**让它无法自动落链的那条。
⇒ ★ 本线采取的解法：**把落链移出工具，由外部写手代理**（`tools/bb_dualwrite.py`，写者与键由调用方显式给出）。
★ **本工具仍无写原语**（`--lean4-check` F 项：外部命令调用点 = **0**）—— ★ 这条性质**没有被这次落地削弱**。

### 落地实测（★ 我这次**不写「未推板」**了 —— 状态归读板）

| 项 | 读数 |
|---|---|
| 键 | `data/registry/xdom-directory` |
| 写手 | `ext-registry-card`（★ **ASCII** —— 中文写者会在**两块板上**双双 `UnicodeEncodeError`） |
| 两板 PUT/GET | local `200/200` · central `200/200` |
| 两板值 sha16 | **`9a2e4d7ae7707c3a`（相等）** |
| 结论 | ★ **未出现 `UNKNOWN_CHANNEL`** ⇒ 此前那条「⑧ 落链会撞 `UNKNOWN_CHANNEL`」的断言**被实测打掉** |

### 复跑（★ 自包含绝对路径 · 不含 `/tmp`）

```bash
cd /Users/coreyleung/dsh-collab
python3 docs/xdom-index/xdom-directory.py --selftest ; echo "rc=$?"          # 期望 51 PASS / 0 FAIL
python3 docs/xdom-index/xdom-directory.py --lean4-check ; echo "rc=$?"       # 期望 6/6 绿
python3 docs/xdom-index/xdom-directory.py --tool-version ; echo "rc=$?"      # 期望 0.4.2 · 单一来源=OK
python3 docs/xdom-index/probe/mutation_directory_selftest.py ; echo "rc=$?"  # 期望 16/16 变红
# ★ 状态**归读板**（不归卡自述）：
curl -s http://127.0.0.1:8792/data/registry/xdom-directory | head -c 200
curl -s http://xingqiao.meetfunbp.com:8792/data/registry/xdom-directory | head -c 200
# ★ 取 v0.4.1 的旧件（用于核「改前」而不是只信记述）：
git -C /Users/coreyleung/dsh-collab log --oneline -- docs/xdom-index/xdom-directory.py
```

★ **注**：v0.4.1 的 sha16 `5ebd6e70ba902869` 已随本次改动**不在工作区**；
★★ **已实测可复原**（不是「应该能」）：自动快照 `5af4a6c8fa4b9d61d1cfe2897160a5a6d6747ee0`
里那件 **sha16 恰为 `5ebd6e70ba902869`** —— ★ **就是我发出去的那封信里引的那一件**。
⇒ 收到的信里引了那个 sha 的读法：
```bash
cd /Users/coreyleung/dsh-collab
git show 5af4a6c8fa4b9d61d1cfe2897160a5a6d6747ee0:docs/xdom-index/xdom-directory.py | shasum -a 256 | cut -c1-16   # 期望 5ebd6e70ba902869
```
★ 教训一句：**引用一个 sha 到对外信件里，等于承诺它可复原** —— ★ 所以改版之后**必须回核**，
不能假设「反正有快照」（★ 本线此前的做法正是「假设」）。

---

## [0.4.1] 2026-10-12 · ★ 触发事件是**把 v0.4.0 与活板对了一遍**（不是评审，是实测）

**触发**：落盘 v0.4.0 后按惯例做「落盘物 vs 活板」对照 ⇒ ★ 发现 **v0.4.0 自己宣称「必亮」的那条告警，
在活板上一次都没亮过**。

★ 活板 `notes/xdom/log/**` 的两封 v2 信，键段**只有 13 位**（`20261012T0240` / `20261012T0330`，
`%Y%m%dT%H%M`，**只到分钟**）；而 `_KEY_TS_RE` 只认 **15 位**（`%Y%m%dT%H%M%S`）
⇒ 短键段落进 `kts is None` 分支 ⇒ ★ **「键段 vs 字段时间不符」这条检查整段被跳过**。
★★ 而 v0.4.0 里点名「键段 02:40 vs epoch 02:02:02 ⇒ 差 38 分钟 ⇒ **必亮**」的那封信，
**恰恰就是短键段的那封** ⇒ ★ **实测活板 warnings 仅 2 条，全是 `W-KEY-TS-FORMAT`**，那条一条都没有。

★ **本线自评：又是「判据守错了对象」，而且这次更难看 —— 连控都是空转的**：
v0.4.0 的 v2 夹具用的是 **15 位**键（`…T024000`）⇒ ★ **它复刻的键形态活板上根本不存在**
⇒ `N PASS / 0 FAIL` **把这件事盖住了**。（对照旧账：这条控当时是被变异 M15 打红过的 ——
★ **说明「能被变异打红」也不等于「复刻了活板」**。两条要一起满足。）

### 改动

| # | 改动 | 它的**控制**是什么 |
|---|---|---|
| ① | **短键段也解析**：新增 `_KEY_TS_SHORT_RE`（13 位）；`_key_ts` 两种都返回 | 夹具控 + 变异 **M17**（打回旧口径 ⇒ 必须变红） |
| ② | **格式告警照发、时间检查不再跳过**：短形态 → `W-KEY-TS-FORMAT`（语义不变），但下面那段时间比对**不再 `elif` 掉** | 正控（短键段 02:40 vs epoch 02:02:02 ⇒ 差 38 分钟 ⇒ **必须**亮） |
| ③ | **按长度选解析格式**（13→`%Y%m%dT%H%M`，15→`%Y%m%dT%H%M%S`） | ★ **解析控**：见下面「自己踩的第二个坑」 |
| ④ | **新增夹具 `_fixture_shortkey()`**：逐字复刻**活板真实键形态**（13 位），两封 —— 一封差 38 分钟、一封对齐 | 正控（必亮）**+ 负控**（对齐 ⇒ **不得**亮，证非恒真） |
| ⑤ | 措辞更正：★ **不再把 R6 叫「旗舰读数」** | 〇表的旗舰是「现在还欠谁一句」，v0.3.0/v0.4.0 **都印「不可判」**；R6 是「最新一封天然「尚未被回」」 |
| ⑥ | README 措辞更正：v0.4.0 说 `xdom-directory-finding-20261012.md`「**并不存在**」—— ★ **那句话是错的** | 实测：该文件**在**，位于**上一级** `docs/`，只是 v0.3.0 把它错列进了 `docs/xdom-index/` 清单 |

### ★★ 落这一版时**自己踩的第二个坑**（★ 一并记下，因为它是同族）

「短键段怎么解析」最省事的写法是「**先试 15 位格式，失败再试 13 位**」—— ★ 实测**不报错，但答案是错的**：

```
>>> time.strptime("20261012T0305", "%Y%m%dT%H%M%S")   # ★ 不抛异常
time.struct_time(... tm_hour=3, tm_min=0, tm_sec=5 ...)     ⇒ 解析成 03:00:05（错 5 分钟）
```

★ 原因：Python 的 `%M` / `%S` **接受 1–2 位**数字 ⇒ `0305` 被拆成 `03` + `0` + `5`。
★★ ⇒ 若照那样写，判据会拿一个**静默错 5 分钟的假时间**去比 —— ★ **判据取错对象**的同族。
⇒ 现按**长度**选格式，并配**解析控**（`_parse_keyts("20261012T0305")` 必须等于 `03:05:00`）。

### 活板实测（同一时刻，v0.4.0 → v0.4.1）

| 读数 | v0.4.0 | **v0.4.1** |
|---|---|---|
| `warnings` 条数 | **2**（全是 `W-KEY-TS-FORMAT`） | **4** ⇒ ★ 两封 v2 信**各自**多出 `W-KEY-VS-FIELD-TS` |
| 其余读数 | 18 楼 · 要求回 11 · 事实边 4 · 推断边 9 · 共线 18/18 · 归一后参与方 2 | ★ **全部不变**（★ 本次只动告警，不动账目） |

### 复跑（★ 自包含绝对路径 · 不含 `/tmp`）

```bash
cd /Users/coreyleung/dsh-collab
python3 docs/xdom-index/xdom-directory.py --selftest ; echo "rc=$?"          # 期望 51 PASS / 0 FAIL, rc=0
python3 docs/xdom-index/xdom-directory.py --lean4-check ; echo "rc=$?"       # 期望 6/6 绿, rc=0
python3 docs/xdom-index/xdom-directory.py --tool-version ; echo "rc=$?"      # 期望 0.4.1
python3 docs/xdom-index/probe/mutation_directory_selftest.py ; echo "rc=$?"  # 期望 16/16 变红, rc=0
python3 -I docs/xdom-index/xdom-directory.py --dry-run --json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(len(d['warnings']), d['warnings'])"   # 期望 4 条（含 2 条 VS-FIELD）
```

★ **本版对照旧版跑法**（★ v0.3.0 可从自动快照取回，用于核「改前/改后」而不是只信记述）：
```bash
cd /Users/coreyleung/dsh-collab
git log --oneline -- docs/xdom-index/xdom-directory.py          # 找 VERSION 为 0.3.0 的那个快照
git show <sha>:docs/xdom-index/xdom-directory.py > ~/dsh-collab/.tmp-xdom-baseline/xdom-directory-v030.py
python3 -I ~/dsh-collab/.tmp-xdom-baseline/xdom-directory-v030.py --dry-run --json | head -c 400
```

---

## [0.4.0] 2026-10-12 · ★ 触发事件是**活板上的一封真信**，不是设计评审

**触发**：活板 `notes/xdom/log/**` 长出**第 16 楼**（`…int-s3-reproduced-and-conceded`），
★ **用的是另一套字段名**（v2：`awaiting` / `reply_to_key` / `sent_at_epoch_ms` / `thread` / `from_label_hint`），
而本工具按 v1（`ts` / `ball` / `ref` / `from_session`）读 ⇒ **把那封真信读成空信**
⇒ ★ **旗舰读数「现在还欠谁一句」报 0 是错的**（实际 `reply_required=true ∧ awaiting='ext'`）。
★ **勘误（v0.4.1）**：★ **上面这一句措辞错了** —— ★ **报 0 的是 `R6`，不是旗舰**；
★ 〇表的旗舰「现在还欠谁一句」在 v0.3.0 / v0.4.0 **都印「不可判」**（★ 它**不是算得 0，是没得算**）。
★ 原文**保留不改**，以便核「错在哪」；★ 正确读法：**R6 由 0 变 1 · 旗舰始终不可判。**

★ **本线自评：这是第 6 次「判据的对象取错了」** —— 判据没错，**取字段取错了**。

### 改动

| # | 改动 | 它的**控制**是什么 |
|---|---|---|
| ① | **schema 适配**：v1/v2 双字段名并读（`ball`/`awaiting` · `ts`/`sent_at_epoch_ms` · `ref`/`reply_to_key`） | 回归控：v2 信 `requires_reply` 必须 **True**（v0.3.0 此处 False）· 变异 **M12** 打回 v0.3.0 口径必须变红 |
| ② | **参与方归一**：剥 `session-` 前缀 + **语料内自证**映射（v1 信自己声明的 `(from, from_session)` 对） | 归一键控 + 变异 **M13**（不剥前缀 ⇒ 变红）· ★ **不猜**：归一不了**原样保留**并记 R8 |
| ③ | **R7**：`reply_required=true` 但**两套球权字段都缺** ⇒ 旧口径**静默丢弃** | R7 正控（造一封无球权的 rr 信 ⇒ R7=1）**与**负控（正常夹具 ⇒ R7=0，证非恒真） |
| ④ | **R8**：参与方归一失败 | R8 正控：`to` 是合法会话 ID 但映射表里没有 ⇒ R8=1，**且原样保留不猜** |
| ⑤ | **`warnings` 五种**：`W-UNKNOWN-SCHEMA` / `W-NO-TIME` / `W-PARTY-UNRESOLVED` / `W-KEY-TS-FORMAT` / `W-KEY-VS-FIELD-TS` | 告警控（键段 02:40 vs epoch 02:02:02 ⇒ 差 38 分钟 ⇒ 必亮）· 变异 **M15** · ★ **不判哪个时间源权威**，只报不一致 **★ 勘误（v0.4.1）：本条控在 0.4.0 里是【空转的】** —— 夹具用 15 位键，而活板那封信的键是 **13 位** ⇒ 该告警在活板上一次都没亮过。见上方 `[0.4.1]`** |
| ⑥ | **共线读数两栏并印**：`ball_eq_to`（归一后）与 `ball_eq_to_raw`（原始串比） | ★ **归一非空转控**：两栏**必须不同**（活板实测 18/18 vs 16/18） |
| ⑦ | **`reply_to_key` 计入事实边**，逐边标 `via`（`dst.ref → src` / `dst.reply_to_key → src`） | 事实边控 + 变异 **M14**（丢掉 `reply_to_key` ⇒ 变红） |

### ★★ 同时修掉自己身上两处「空转绿」（★ **由新增的变异检验抓出来，不是我自己看出来的**）

1. **恒真判据**：自检里一行原文是 `chk(all(... for e in []) or X, ...)`
   —— `all([])` 恒 True、`True or X` **恒 True** ⇒ ★ **这一行无论怎么改都是绿的**。
   ★ 它不是「写错」，是**根本没有断言**。现 M9 变异已能把该行打红。
2. **判据读错了对象**：分栏断言原只读 `totals["edges_fact"]`（那个数是**局部变量**另算的）
   ⇒ ★ 谁真把返回结构里两栏合并了，`totals` **照样好看**。现改为**直接读消费方真正读的键**
   （`edges_fact` / `edges_inferred` 的长度 + 每条的 `kind` 与栏位是否一致）。M8 现能打红。
3. **结构门 A 项的假阳性**：禁止清单里的裸名 `compile` 用 `\bcompile\b` 匹配 ⇒
   ★ 本版一加 `re.compile(...)` 常量，门立刻变红 —— **但红的是门，不是代码**。
   ⇒ 判据改对：**裸名只认「非属性访问」的出现**（`re.compile` 与内建 `compile` 是两个东西）。
   ★ **反面风险必须自证**：A 项现在带**两个正控**（注入写请求 / 注入真 `compile(...)` 调用）
   **和一个负控**（`re.compile` 不得命中），防「改宽了」。

### 新增变异体（探针 v2 → v3：7 → **15** 条，且**新增 gate 模式**）

- M8 两栏合并 · M9 取「最后一封」而非「第一封」 · M10 忽略 `ball` · M12 丢 `awaiting`
- M13 不剥前缀 · M14 丢 `reply_to_key` · M15 丢时间不符告警
- ★ **M16（新引入 gate 模式）**：往源码注入**一处真写请求调用点**，再问**门自己**
  —— ★ 前 15 个变异都只检验「**读数**对不对」，**没有一个检验「门会不会拒绝」**。

### 复跑（★ 自包含绝对路径 · 不含 `/tmp`）

```bash
cd /Users/coreyleung/dsh-collab
python3 docs/xdom-index/xdom-directory.py --selftest ; echo "rc=$?"          # 期望 47 PASS / 0 FAIL, rc=0
python3 docs/xdom-index/xdom-directory.py --lean4-check ; echo "rc=$?"       # 期望 6/6 绿, rc=0
python3 docs/xdom-index/xdom-directory.py --selfcheck ; echo "rc=$?"         # 期望 rc=0
python3 docs/xdom-index/xdom-directory.py --tool-version ; echo "rc=$?"      # 期望 0.4.0 · 单一来源=OK
python3 docs/xdom-index/probe/mutation_directory_selftest.py ; echo "rc=$?"  # 期望 15/15 变红, rc=0
python3 -I docs/xdom-index/xdom-directory.py --dry-run --json | head -c 400
```

★ **变异探针须每次改版重跑**：锚点跟着源码漂，锚点对不上时探针会如实报「**不可判**」而不是假装通过。

---

## [0.3.0] 2026-10-12 · 触发事件是 P1 定桩实测

- ① **边升为一等对象**：`fact`（`ref` 指信键**且目标键存在**）与 `inferred`（顺序邻接推断）
  **两栏分开印**、JSON **分开给键**；逐封账目表**只放事实**。
  ★ 依据：P1 定桩件实测 —— 原方案那条「球权交接 ⇒ 回复链」**7 条边里 6 条不可判**，
  全库**事实边只有 1 条**。混印 = 把**推断**当**事实**卖。
- ② **不可判清单 R1–R6 逐条带计数**，其中 R5 **结构性** ⇒ 印「结构性不可判」**不印 0**。
- ③ **修自家缺陷**：v0.2.0 的 `--json` 的 `posts` 里**没有 `ref`** ⇒ 消费方取 `ref` 恒得空。
- ④ 补 **R006 ②⑦⑩**（`--selfcheck` / 统一日志 / `--lean4-check`）与 **⑥**（版本单一来源自证）。

## [0.2.0] 2026-10-12 · 触发事件是 v0.1 一跑真板

- 按 `topic` 分帖**退化成 15 个单楼帖**（15 楼 → 15 个互不相同的 `topic`）⇒ 聚合为零。
  ⇒ 改为**把三个读数当证据印出来**，并**明确标出哪一条算不出来**
  （`现在还欠谁一句` = **不可判**，因为缺「回复链」载体）。

## [0.1.0] 2026-10-12

- 初版：按 `topic` 分帖。

---

★ 本文件**只记已发生的事**，不记计划。未达标项见 `README.md` ③ 达标矩阵与 `P2-preflight-20261012.md`。
