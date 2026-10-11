# 给星桥（CLD）会话的交接 —— 规则账本：trae 总纲整合核验 + 计数收尾

> **用途**：把 2026-10-10 完成的「i9 trae 总纲三层整合」交接给 CLD 内部会话。
> **变更已由 `session-505612bd-1b12-47a1-91c3-9a6e6b5357a8` 落盘**（工作区，**未提交**）；
> 除非用户明确指示重做，你的活是 **核验 + 收尾两件**，**不是**重做。
> 下面 `---8<---` 两条线之间的**全部内容**就是粘进新会话的正文。

---8<--- 复制从这里开始 ---8<---

你是**星桥（CLD）会话**，接手一次**已落盘的规则账本变更**的核验与收尾。

**背景（一句话）**：i9 设备的 trae 规则集《AI工程规则总纲》v2.0（**27 条** = 22 条编号规则【一～二十三，**缺十四**】+ 5 条基础规则）
已按用户裁定的「三层轻整合」并入规则账本 —— **不占编号**、只加一节走查表；工作区有**未提交**改动。
剩 **一个待用户拍板后执行**的项：`RULES.md` 首行计数修正。

**先做这 4 步，别跳（每步给了期望输出；不符先报，别绕）：**

① **读新节**（账本内唯一权威，不是本交接）：
```bash
sed -n '448,512p' ~/dsh-collab/rules-registry/RULES.md      # 「外部来源规则集」走查表
cat ~/dsh-collab/rules-registry/sources/PROVENANCE.md        # 原件来源档案
```
期望：新节标题为 `## 外部来源规则集（映射 · 不占编号 · trae:E*）`，含 **27 行**走查表，
表下小结为「**已覆盖 6（等价4·超集1·部分等价1）· 相关 6 · 新增 15**」。

② **跑计数门**（本次变更**前后判定应完全一致**）：
```bash
python3 ~/dsh-collab/scripts/rules-integrity.py
```
期望：`声明: v2.23.7 | 66 条` / `实际: 67 个标题` / **硬问题 1 项（计数不符）**，
且提示里出现 3 行 `非规则小节（分区标题，跳过）`：`治理哲学` · **`外部来源规则集`** · `retiredEntries`。
⇒ **这条红在本次整合前就存在**（根因见下「待拍板项」），**不是**新节引入的 —— 新节被正确跳过、**没动计数**。

③ **跑反遗忘校验**（须 `exit 0` 才继续）：
```bash
python3 ~/dsh-collab/tools/beacon-check.py --net
```
期望：**全绿（0 条 WARN，0 条 SKIP）**。索引 `evidence_index` 现为 **29** 条，
`state_version` 仍 **3**、`anchor_sha256` **未改**（本次只动 `evidence_index`/`updated_at`/`_p0_sync_note`）。
> 若你的环境无网：去掉 `--net` 会显示 1 条 **SKIP**（C1 未抽检）—— **SKIP ≠ PASS**，不要读成「全绿」。

④ **回读知识索引**（KB）：
```bash
~/.openchronicle/venv/bin/python ~/dsh-collab/scripts/index-rules-kb.py --dry-run   # 期望「解析: 27 条」
~/.openchronicle/venv/bin/python - <<'PY'
import sys; from pathlib import Path
sys.path.insert(0, str(Path("~/.claude/automation").expanduser()))
import lib
c = lib._get_chroma().get_collection("rules")
print("rules 集合计数:", c.count(), "| E14 应缺号:", c.get(ids=["trae:E14"])["ids"])
PY
```
期望：计数 **27**，`E14` 返回**空**（总纲无规则十四，正确缺号）。

**做完这 4 步，先向我复述**：① 新节共几条、小结的三组数字 ② 计数门的红是**本次引入**还是**既有** ③ 信标是否全绿。
**复述对了再动手。**

---

### 唯一待拍板项：`RULES.md` 首行计数修正（**须用户先说「改」**）

**症状**：计数门报 `声明 66 / 实际 67`（RED）。
**根因（实测，非推断）**：本账工作区里 `R049` 由上一会话加入时把 `65 条 → 66 条`（`git diff` 可见），
但**其后 `R050` 于 2026-10-10T00:40 追加时只写了正文、没再同步首行** ⇒ 差 1。
`R001–R050` 连续无重号无跳号（除**刻意的**第十四号不存在）⇒ 就是 R050 这一条。

**改法（若用户同意，共 3 处，都在文件头部 6–9 行）**：
1. `> v2.23.7 | 66 条 | …` → `> v2.23.8 | 67 条 | …`（**`N 条` 形式必须保留**——改格式会让门读成 `v? | ? 条`）
2. 计数口径注：`R49 · J13 · R-ERR4 = 66` → `R50 · J13 · R-ERR4 = 67`
3. 复核：`python3 ~/dsh-collab/scripts/rules-integrity.py` ⇒ 期望 **硬问题 0 项**（提示里仍会有 2 条「编号乱序」+ 3 个分区标题，属正常）

**为什么单列成"待拍板"而不是顺手改**：用户所选整合选项**明确排除**修计数。
且这正是总纲**「规则二十一 · 判据不得退化成恒为常量」的活例** —— 计数一旦与实际脱钩，
门仍显示绿、但已不核验任何东西。**所以要么改对，要么留着并让人知道它是红的；不要静默。**

---

### 护栏（违反即失去意义）

- **不改编号、不重排**：`编号冻结不重编`（重编会破坏 `retiredEntries` 与外挂表 `ruleId` 溯源）。
- **别把 27 条拆进编号账**：`trae:E<n>` 与 `xq:R<n>` **数形相撞**（`rules-id-collision-map.md` 记的同类教训）；
  它是**指针节**，引用一律写 `trae:E<n>`。
- **`sources/` 只增不改**：原件内容永不编辑；`SHA256SUMS` 可用 `shasum -a 256 -c` 复验。
- **别把 KB 集合 `rules` 并进 `wiki`**：`wiki` 放 wiki 页面，混入会污染其检索面。
- **不动信标的 `state_version`(3) / `anchor_sha256`**：该指纹只对**锚点文件**算，改正文不使其失配。
- 跨设备写黑板一律走 `~/dsh-collab/tools/bb_dualwrite.py`，且**必须独立回读**
  （不信它的 `equal=True`；比对磁盘载荷与两板 `.value` 的规范化 JSON sha256）。
- 不可逆动作（重启 / 改 profile / 载体换 / 挂载）**先登记后执行**。

### 回滚（**别用 `git checkout`**）

`RULES.md` 的工作区里**同时**有**别的会话未提交的改动**（`R049`、`R050`）。
⇒ **`git checkout -- rules-registry/RULES.md` 会把它们的活一起回退。**
回滚只应**外科式删除**「`## 外部来源规则集`」这一节（从该标题行到 `## retiredEntries` 之前），
以及撤销 `rules-id-collision-map.md` 的 §5、`continuity-index.json` 的 6 条新证据指针与同步注。
`sources/`、`scripts/index-rules-kb.py`、`data/registry/ai-engineering-rules-v2.json` 可独立保留或删除，互不影响。

---8<--- 复制到这里结束 ---8<---

## 使用说明（**不要**复制这一段）

- **正文自包含**：新会话不需要你先解释背景。
- **本交接对应的工作区状态**（2026-10-10T02:4x，供你核对是否已被他人改过）：

  | 文件 | 状态 | 大小 / 指纹 |
  |---|---|---|
  | `rules-registry/RULES.md` | 已改（未提交） | 78241 B / 544 行 · 新节起 **L448** · sha256 `49bd74e6d3dd064b…` |
  | `rules-registry/sources/` | 新增（4 文件） | 总纲 48254 B · sha256 `5e82079068765969e38499f00fed32ec493f5a9ef4db5374a863178713566e12` |
  | `rules-registry/rules-id-collision-map.md` | 已改（新增 §5） | 5090 B · sha256 `e5d2b122a51b3419…` |
  | `scripts/index-rules-kb.py` | 新增 | 5860 B |
  | `data/registry/ai-engineering-rules-v2.json` | 新增（登记卡） | 8371 B · 规范化 sha256 `756731d42816f06f51c7e4d87fcfdafc434c5f8a4300508d2eb6eb24715e679a` |
  | `data/registry/continuity-index.json` | 已改 | `evidence_index` 23 → **29** |
  | `~/CLAUDE.md` | 已改 | 新增「外部规则集：行为类条目」4 条 |

- **若新会话读到的数与上表不符**：说明工作区已被改过 ⇒ **先让它报差异，别按旧状态干活**。
- **登记卡与黑板**：`data/registry/ai-engineering-rules-v2`（黑板同名键，双板已双写、独立回读逐位相同）。
- **相关文档**：`rules-registry/sources/PROVENANCE.md`（来源与"原创件在 i9"的说明）·
  `rules-registry/RULES.md` 走查节 · 同目录 `rules-id-collision-map.md` §5（第三命名空间）。
- **一项不属于本次、但同处工作区**：`rules-registry/rules.json` 与 `lean4/acceptance-gate.lean` 也是 `M`（已改未提交），
  **不是**本次整合产物 —— 别把它们算进这次变更，也别顺手回滚。
