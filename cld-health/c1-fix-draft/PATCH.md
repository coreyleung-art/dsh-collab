# C1 修复提案（G9）· 守灯席位#4

**目标文件（线上）**：`~/dsh-plugin-guard/lib/index.js`（mtime 2026-10-02，L334）
**同一逻辑的第二份拷贝**：`~/.dsh/profiles/web/node_modules/dsh-plugin-guard/lib/index.js`（同 mtime，同 L334）
**第三份（陈旧）**：`~/dsh-collab/guard/tools/labforge/plugins/dsh-plugin-guard/index.js`（mtime 2026-09-05，L315）

> ★ 附带发现（R006 ⑥ 版本单一来源）：**同一段判据存在 3 份物理拷贝**，行号已分叉（334 vs 334 vs 315）⇒ 只改一处会造成「修了但没生效」或「两份行为不同」。**建议同步落盘 + 记录主副本**；本提案不代改，交由裁判裁定落盘范围。

---

## 1. 缺陷（G9 · 已复核）

线上 L334 原文：

```js
out.checks.C1_boot = em ? { ok: em.cleanExit !== false || em.reason !== "dsh-crash", marker: em.reason || "clean", cleanExit: em.cleanExit } : { ok: false, error: "无 exit-marker（CLD 未跑过？）" };
```

| # | 缺陷 | 机制 | 可复核证据 |
|---|---|---|---|
| ① | **不可能变红** | `em.reason !== "dsh-crash"` 在 live marker（boot 写入、**无 `reason` 字段**）下恒真 ⇒ `ok` 恒真 | 负控 6 例中旧判据仅 1 例红（且该例是完全无 marker） |
| ② | **伪造 "clean"** | `marker: em.reason \|\| "clean"` ⇒ 字段缺失时凭空印出 `clean`（`{}` 也印 clean） | 负控矩阵：旧判据 5/6 例印 `clean`，其中 4 例为**不可判定或未干净退出** |
| ③ | **同名不同对象** | `cleanExit` 取自**当前运行**的 marker（false=正在运行，属正常）；同名值在 `[exit-trace]` 里指**已结束那次** | 实况：末行 `PREVIOUS CLD RUN (pid 12492 …) DID NOT EXIT CLEANLY`，而 C1 报 `ok:true, marker:"clean"` |

**根因（一句话）**：C1 的问题是「**上一次运行**是否干净退出」，而它读的是「**当前运行**的 boot marker」⇒ **对象错位**（不是阈值问题）。

---

## 2. 修复（最小改动 + 一处结构性抽取）

### 2.1 结构性抽取（可测性的前提）

把判断逻辑从「读文件系统的那一行」抽成**纯函数** —— 否则「仪器是否已证明会红」无法执行验证。

已交付可跑原型：`~/dsh-collab/cld-health/c1-fix-draft/`
- `c1-judge.mjs` —— `judgeC1(liveMarker, logLines) → { ok, status, marker, attribution, evidence }`
- `c1-selftest.mjs` —— 6 例负控自检（含旧判据对照）

### 2.2 L334 替换（drop-in）

```js
  // C1 boot_ok: **上一次运行**是否干净退出（证据在 append-only 的 [exit-trace]，不在 live marker）
  const em = readJson(join(CLD_LOG_DIR, "exit-marker.json"), null);
  let traceLines = [];
  try {
    traceLines = readFileSync(join(CLD_LOG_DIR, "dsh-web.log"), "utf8").split("\n").slice(-2000); // 限读尾部 2000 行
  } catch { /* 日志不存在 ⇒ 走不可判定分支，不报 clean */ }
  out.checks.C1_boot = judgeC1(em, traceLines);
```

并在文件顶部 import `judgeC1`（或内联同逻辑；**内联则 selftest 不可复用 ⇒ 建议抽模块**）。

### 2.3 输出契约（新增字段）

| 字段 | 语义 | 变化 |
|---|---|---|
| `ok` | 布尔，**不可判定时也 false**（fail-closed） | 语义收紧 |
| `status` | `clean` / `unclean` / `unjudgeable`（**三态，不留白**） | 新增 |
| `marker` | **记录里的 reason**（无则 `null`）—— **绝不默认 "clean"** | 由伪造改为如实 |
| `attribution` | `{pid, startedAt}` —— 声明该结论属于**哪一次运行** | 新增（消歧同名） |
| `evidence` | 结论依据（`exit-trace: DID NOT EXIT CLEANLY` 等） | 新增 |

---

## 3. 影响面（必须先说清，再裁定）

1. **`all_ok` 语义变化**：`all_ok = Object.values(checks).every(c => c.ok)` ⇒ **不可判定现在也算失败**。本机有 9 条历史 `PREVIOUS CLD RUN` 行 ⇒ **本机立刻可判**；但**全新机器/日志被轮转**时，首次运行会红。
   - **备选方案（不推荐）**：`unjudgeable` 时 `ok:true`。**不选的理由**：那正是本缺陷的形态（**把「判不出」与「通过」合并**）；且与既有约定（rules-cli **fail-closed**、四态纪律「unknown 不得并入 consistent」）冲突。
   - **折中（可选）**：`ok:false` 但新增 `out.all_ok_strict` / `all_ok` 区分，由裁判定。
2. **读取成本**：`dsh-web.log` 当前 0.1 MiB / 1373 行（小）；补丁**限读尾部 2000 行**以防轮转前膨胀。
3. **不改其它 C 项**：C2/C3/C7 与 `memory_last` 逻辑**一行不动**。
4. **三份拷贝**：落盘须覆盖 2 份（线上 + profile），并决定陈旧副本（labforge）是否同步或归档。

---

## 4. 验收三步（可复跑）

```bash
cd ~/dsh-collab/cld-health/c1-fix-draft && /opt/homebrew/bin/node c1-selftest.mjs   # 期望 exit=0
```

| 步 | 内容 | 实测结果 |
|---|---|---|
| **① 正向** | 有 clean-exit 记录 ⇒ `ok:true, status:clean` | ✅ 例 1 通过 |
| **② 反控（必须能红）** | 未干净退出 / 被 kill ⇒ `ok:false, status:unclean` | ✅ 例 2、3 通过；**旧判据在同样两例报 true/clean** |
| **③ 效应判据** | 伪造 `"clean"` 次数 = 0；不可判定显式表达 | ✅ 旧 5 次 → **新 0 次**；3 例 `unjudgeable` |

**判据级效应量**：旧判据 **1/6** 会红 ⇒ 新判据 **5/6** 会红（判别力成立）。

---

## 5. 待裁定项（提交裁判）

| # | 待裁 |
|---|---|
| Q1 | 是否采纳 `unjudgeable ⇒ ok:false`（fail-closed）；若否，采用哪种折中 |
| Q2 | 落盘范围：线上 1 份 / 2 份（含 profile 拷贝）/ 3 份（含 labforge 陈旧副本） |
| Q3 | selftest 的挂载点：并入 `lib/selfcheck.js`，还是独立 `lib/c1-selftest.mjs` + package.json script |
| Q4 | 是否需要同时把 `marker`→`status` 的**读者迁移**（谁在读 `C1_boot.marker`） |

**我方边界**：本提案**未改动任何线上文件**（原型在 `~/dsh-collab/cld-health/c1-fix-draft/`，我域内）；属主/裁判裁定后方可落盘。
