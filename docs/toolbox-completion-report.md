# 审查工具库完善目标 · 收口报告（v1.0）

> `goal-5051b1f8-a9ad-446b-a5e7-d012ed6025f9` · round 10/30
> **口径**：本文件全部 16 位 hex = **SHA-256 全量摘要前 16 位小写 hex**
> **生成者**：裁判 `session-1ffded95`

---

## §1 目标

> 把「先查存量工具面 → 缺口才新建 → 新建必过 R006 → 改动必实跑自检」**从【已做到 2 个工具】推到【可机械覆盖全量】**，三面逐个闭合。

---

## §2 三面状态

### 面① 覆盖面 —— ✅ **闭合**

| 项 | 结果 |
|---|---|
| **实跑面** | `scripts/` **全部 308 个 `.py`**（目标写 306，实测 308） |
| **判据** | 取自 `selftest-inventory.py`：**看自测标识行，不看退出码** |
| **PASS_CLEAN** | **298（96.8%）** |
| **NO_ENTRY** | **5**（真无 CLI 自检入口） |
| **PASS_NOMARK** | 2 · **FAIL 3** · **TIMEOUT 0** |
| **限时/并发** | 10s / 8 |

**★ 本面最有价值的部分是【入口判定的三代口径】**（同一批 308 文件、同一判据，仅入口判定不同）：

| 口径 | 判定方式 | 假阳性 | 假阴性 | PASS_CLEAN | NO_ENTRY |
|---|---|---|---|---|---|
| ① **源码级** | 源码里出现 `--selfcheck` 字样 | **有**（5 个工具注释含字样但 CLI 未实现） | 无 | 296 | 1 |
| ② **`--help` 级** | `--help` 输出里列出 | 无 | ★ **94%** | 182 | 122 |
| ③ **★ 试跑级** | 真跑旗标，看是否 `unrecognized` | 有（不解析 argv 的脚本） | 无 | **298** | **5** |

> **★ 教训**：**「声明」不止是源码字符串 —— `--help`、文档、注释、字段名都是声明。**
> **只有【真跑那个动作】才是实跑级。**

### 面② R006 达标 —— ⚠️ **被一个已报缺陷阻塞**

| 项 | 结果 |
|---|---|
| **缺口表** | 已出（10 个核心工具逐项）· 见卡 `data/registry/u5-r006-gap-table-and-u6-commission` |
| **按项缺口** | ②7 · ⑥7 · ⑦7 · ⑨8 · ⑩7 · ①2 · ⑤2 · ③④0 · ⑧10（**口径差，不属缺口**） |
| **委托** | ✅ 已发（**executor = PSTD · adjudicator = 裁判 · proposer = R006 规格**，R046 三元分离） |
| **其交付** | ✅ **已批量注入**（11 个工具，mtime 全为 `03:43:38`） |
| **★ 阻塞** | ★ **注入块第 7 项核验取错对象** ⇒ **11 个工具 `--selfcheck` 全 `rc=1`** ⇒ **审查器 ② 判定要求 `rc==0` ⇒ ② 项全部 FAIL** |
| **U6.1 复核** | ⏳ **已停**（**读数无意义**：② 全 FAIL 系缺陷所致，非真实缺口） |

**★ 缺陷详情**（见卡 `data/registry/batch-defect-injected-check7-conflates-runtime-with-source`）：
```
✅ …（前 6 项全过）
❌ Python 版本读数非硬编码 — 3.9.6
rc=1
```
**该项读 `platform.python_version()` 得 `3.9.6`，却判「源码里硬编码了 Python 版本」** ——
**而源码里没有任何 `3.9.6` 字面量** ⇒ **结构上无法通过**。
**修法建议**：扫【源码剥离面】里是否出现形如 `3\.\d+\.\d+` 的字面量（与判据 ④ 同法），**而非读运行时值**。

### 面③ 缺口识别 —— ✅ **闭合（以否证）**

| 项 | 结果 |
|---|---|
| **判据** | **信号的价值 = 命中率 × 后果** + 辅判据「**可门化 ⇔ 形态与真值源都可显式给出**」 |
| **分诊** | **16 条** ⇒ **已工具化 4 · 判定不建 12 · ★ 值得新建的门 = 0** |
| **收口件** | `docs/audit-criteria-triage-decision.md`（`104b8b6930c66325`） |
| **★ 产出就是否证** | **先查存量 → 缺口才新建 → 本轮无缺口 ⇒ 不新建**。**若强行建，就是造出第 2 个「228 误报的绝对词门」** |

---

## §3 交付物

| 文件 | sha256[0:16] | 说明 |
|---|---|---|
| `audits/_review-toolmap.md` | **`1661d35d05facdc6`** | 全量实跑版 v3.3 · 86 行 · 六节 |
| `scripts/toolbox-selftest-sweep.py` | **`ccbcd9b74125b400`**（**被 PSTD 注入后**） | 全量自检实跑器 · selftest 6/6 |
| `scripts/r006-two-tool-audit.py` | **`82903f663bf38d4e`** → 后被注入 | R006 十项审查器 |
| `scripts/archive/audit-criteria-triage.py` | **`94ad21864d61b6e5`**（**被注入后**） | 判据分诊器 · 我已补到 8/10 |
| `docs/audit-criteria-triage-decision.md` | **`104b8b6930c66325`** | 面③ 收口件 |
| 卡 `u5-r006-gap-table-and-u6-commission` | — | 面② 缺口表 + 委托 |
| 卡 `batch-defect-injected-check7-...` | — | ★ 批量缺陷报告 |

---

## §4 本目标查出的真缺陷

| # | 对象 | 内容 | 性质 |
|---|---|---|---|
| ① | `bb-blueprint-ui2.py` | `NameError: name 'sys' is not defined` | **真 bug（缺一行 import）** |
| ② | `bb-asset-relations.py` | from/to 不存在 + 非法类型 | **真数据不一致** |
| ③ | `bb-waimai-mcp-core.py` · `gate-plugin-inject.py` | 8787 不可达 · 长跑超时 | **外部依赖** |
| ④ | `index-rules-kb.py` | 真无自检入口 | **真 NO_ENTRY** |
| ⑤ | **11 个工具（批量）** | **注入块第 7 项核验取错对象 ⇒ `selfcheck` 全 rc=1** | ★ **批量缺陷 · 阻塞面②** |

---

## §5 未闭合（不假装完成）

1. **面② 的 ② 项读数** —— 须 PSTD 修第 7 项核验后重跑；
2. **U6.1 完整复核** —— 已停（读数无意义）；
3. **`toolbox-selftest-sweep.py` 的 ⑤** —— 缺 `docs/` 文档（**我是属主，但它在被注入中，未动**）；
4. **`index-rules-kb.py`** —— 未在被注入批内（mtime `02:40:01`）；
5. **`devices/` 下 17 个插件目录与 `tools/` 未纳入**索引面；
6. **R006 只覆盖 10 个核心工具** —— 其余 298 个未跑。

---

## §6 我方失误（本目标累计）

| # | 内容 |
|---|---|
| **F102** | 重生 toolmap 时覆盖掉 v2 内容（**退化**，已补回） |
| **F103 / F104 / F108 / F111** | 内联命令/`sleep`/`%` 格式化 —— **同族四次** |
| **F105** | 扫描器用源码级判入口 ⇒ 5 个假 `NEEDS_ARGS` |
| **F107** | 改用 `--help` 级 ⇒ **误判率 94%** |
| **F109** | 卡缺 `subject`（**第 7 次**） |
| **F110** | `arguments` wrapper（**第 7 次** —— **抽取过却没门化**） |
| **夹具未同步 ×2** | 改判据后自检红（1/4 · 3/5）⇒ **已补，现 6/6** |

---

## §7 复现命令

```bash
# 面① 全量自检实跑
python3 ~/dsh-collab/scripts/toolbox-selftest-sweep.py --timeout 10 --workers 8 --out /tmp/sweep-v3.json
python3 ~/dsh-collab/scripts/toolbox-selftest-sweep.py --selftest      # 6/6

# 面② R006 逐项
python3 ~/dsh-collab/scripts/r006-two-tool-audit.py --tool <path> --json

# 面③ 判据分诊
python3 ~/dsh-collab/scripts/archive/audit-criteria-triage.py

# 批量缺陷复现（0.6s）
python3 ~/dsh-collab/scripts/gate-canfail.py --selfcheck; echo rc=$?
```

---

*审查工具库完善 · 收口报告 v1.0 · 2026-10-10 · 面①③ 闭合 · 面② 待一个已报缺陷修复*
