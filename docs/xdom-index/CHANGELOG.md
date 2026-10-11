# xdom-directory.py · 变更日志

> **版本单一来源**：脚本内 `VERSION` 常量（★ 本文件**只记历史**，**不构成**第二个版本声明）。
> `python3 docs/xdom-index/xdom-directory.py --tool-version` 会自动反查源码自证「只有一处声明」。
> ★ 依据 R006 ⑥（版本管理）。★ 本文件**不宣布任何版本「已验证」**——验证归独立方。

每条格式：`## [版本] 日期 · 触发事件` → 改动逐条 → **该项的控制是什么** → 复跑。

---

## [0.4.0] 2026-10-12 · ★ 触发事件是**活板上的一封真信**，不是设计评审

**触发**：活板 `notes/xdom/log/**` 长出**第 16 楼**（`…int-s3-reproduced-and-conceded`），
★ **用的是另一套字段名**（v2：`awaiting` / `reply_to_key` / `sent_at_epoch_ms` / `thread` / `from_label_hint`），
而本工具按 v1（`ts` / `ball` / `ref` / `from_session`）读 ⇒ **把那封真信读成空信**
⇒ ★ **旗舰读数「现在还欠谁一句」报 0 是错的**（实际 `reply_required=true ∧ awaiting='ext'`）。

★ **本线自评：这是第 6 次「判据的对象取错了」** —— 判据没错，**取字段取错了**。

### 改动

| # | 改动 | 它的**控制**是什么 |
|---|---|---|
| ① | **schema 适配**：v1/v2 双字段名并读（`ball`/`awaiting` · `ts`/`sent_at_epoch_ms` · `ref`/`reply_to_key`） | 回归控：v2 信 `requires_reply` 必须 **True**（v0.3.0 此处 False）· 变异 **M12** 打回 v0.3.0 口径必须变红 |
| ② | **参与方归一**：剥 `session-` 前缀 + **语料内自证**映射（v1 信自己声明的 `(from, from_session)` 对） | 归一键控 + 变异 **M13**（不剥前缀 ⇒ 变红）· ★ **不猜**：归一不了**原样保留**并记 R8 |
| ③ | **R7**：`reply_required=true` 但**两套球权字段都缺** ⇒ 旧口径**静默丢弃** | R7 正控（造一封无球权的 rr 信 ⇒ R7=1）**与**负控（正常夹具 ⇒ R7=0，证非恒真） |
| ④ | **R8**：参与方归一失败 | R8 正控：`to` 是合法会话 ID 但映射表里没有 ⇒ R8=1，**且原样保留不猜** |
| ⑤ | **`warnings` 五种**：`W-UNKNOWN-SCHEMA` / `W-NO-TIME` / `W-PARTY-UNRESOLVED` / `W-KEY-TS-FORMAT` / `W-KEY-VS-FIELD-TS` | 告警控（键段 02:40 vs epoch 02:02:02 ⇒ 差 38 分钟 ⇒ 必亮）· 变异 **M15** · ★ **不判哪个时间源权威**，只报不一致 |
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
