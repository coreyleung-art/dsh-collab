# toolbox-selftest-sweep — 审查工具库全量自检实跑器（中文说明）

> R006 ⑤ 文档化 · 对应文件 `scripts/toolbox-selftest-sweep.py`
> **哈希口径**：本文件与源文件里的 16 位 hex = **SHA-256 全量摘要前 16 位小写 hex**

---

## 用途

对 `~/dsh-collab/scripts/` 下**全部 `.py`** 逐个实跑其**自检入口**，记录状态。
**它把「先查存量工具面」这一步的存量面从**（原先的）**34 个审查类**推到**全量 308 个**。

---

## 判据（★ 不看退出码）

> **判据取自 `selftest-inventory.py`：看输出里是否有【自测标识行】，不看 `exit` 码。**
> **理由**：`exit=0` 对「真通过」与「静默跑默认动作」**同痕**。

**自测标识行**：含 `selftest` / `自测` / `PASS` / `✅` / `期望` / `断言` / `通过` / `selfcheck` / `TCC` / `只读` 之一。

---

## 五态

| 态 | 含义 |
|---|---|
| **PASS_CLEAN** | rc=0 **且**输出含自测标识行 |
| **PASS_NOMARK** | rc=0 **但无自测标识行** ⇒ **无法证明跑的是自测**（可能是静默默认动作） |
| **FAIL** | rc≠0 真非零退出 |
| **TIMEOUT** | 超时（★ **不计入通过**） |
| **NO_ENTRY** | **试跑两个旗标均 `unrecognized`** ⇒ 真无 CLI 自检入口 |

---

## ★ 入口判定的三代口径（本器最重要的一节）

**同一批文件、同一判据，仅入口判定不同 ⇒ 差异完全归因于口径：**

| 口径 | 判定方式 | 假阳性 | 假阴性 | PASS_CLEAN | NO_ENTRY |
|---|---|---|---|---|---|
| ① **源码级** | 源码里出现 `--selfcheck` 字样 | **有**（注释含字样但 CLI 未实现） | 无 | 296 | 1 |
| ② **`--help` 级** | `--help` 输出里列出 | 无 | ★ **94%** | 182 | 122 |
| ③ **★ 试跑级（本器现用）** | 真跑旗标，看 `unrecognized` / `invalid choice` / `no such option` | 有（不解析 argv 的脚本） | 无 | **298** | **5** |

> **★ 结论：「声明」不止是源码字符串 —— `--help`、文档、注释、字段名都是声明。**
> **只有【真跑那个动作】才是实跑级。**

**口径③的假阳性为何可接受**：不解析 `argv` 的脚本跑任何旗标都 rc=0 ⇒ 判 `PASS_NOMARK`；
而 **跑它等于跑默认动作、且它不输出自测标识** ⇒ `PASS_NOMARK` **正是准确描述**。

---

## 用法

```bash
# 全量实跑（推荐限时 10s / 并发 8）
python3 ~/dsh-collab/scripts/toolbox-selftest-sweep.py --timeout 10 --workers 8 --out /tmp/sweep.json

# 自检（6 例：4 负例 + 2 正例，含「不解析 argv ⇒ PASS_NOMARK」与「源码含字样但 CLI 未实现 ⇒ NO_ENTRY」）
python3 ~/dsh-collab/scripts/toolbox-selftest-sweep.py --selftest

# 声明与实现一致性
python3 ~/dsh-collab/scripts/toolbox-selftest-sweep.py --selfcheck

# 只列将扫的对象
python3 ~/dsh-collab/scripts/toolbox-selftest-sweep.py --dry-run
```

**参数**：`--limit N` 只跑前 N 个 · `--timeout S` 每工具限时 · `--workers W` 并发 · `--out PATH` 结果落盘 · `--json` 只输出 JSON。

---

## 统一日志

`~/dsh-collab/logs/toolbox-selftest-sweep.log`（每次扫描追加一行汇总：`swept/clean/nomark/fail/timeout/noentry/secs`）。

---

## 已知限制

- **不跑业务功能** —— 只跑自检入口 ⇒ **业务面须按用例另行验证**；
- **不测写副作用** —— 自检入口是否写盘未逐一确认；
- **不覆盖 `devices/` 与 `tools/`** —— 只扫 `scripts/`；
- **`NO_ENTRY` 的判据依赖脚本解析 `argv`** —— 不解析者会落 `PASS_NOMARK` 而非 `NO_ENTRY`（★ 那是正确的：它的"默认动作"不是自检）。

---

*R006 ⑤ 文档 · 建于 2026-10-10 · 目标 `goal-5051b1f8` 面①*
