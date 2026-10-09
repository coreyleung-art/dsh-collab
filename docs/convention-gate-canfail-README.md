# gate-canfail.py · 通用判据能红门 — 中文文档

> 路径 `~/dsh-collab/scripts/gate-canfail.py` · 形态：**独立 py 脚本**（R006 ⑩ 口径下的 `scripts/` 共享族，非插件包）
> 本文档满足 **R006 ⑤ 文档化**（含 ① 为什么需要 ② 用法含退出码 ③ 达标矩阵；每条命令可复制即用）
> 补课时间：**2026-10-10** · 补课内容：**R006 ⑤ / ⑦ / ⑩**（②③④⑥⑧⑨ 原本已达标）

## ① 为什么需要（事故/证据）

**事故**：星桥审查线 2026-10-09 —— 对侧的三个判据（M1 索引 / 版本登记 / 状态机）**只记录**不合规，
而进程仍 `exit 0` ⇒ **判据没有失败路径** ⇒ 「**等于不会红**」。

**其自述（本工具的核心判据来源）**：
> **「一个判据若没有能让它失败的输入，它就不是判据，是日志。」**

⇒ 本工具**抽象自** `tools/selftest-starbridge-gates.py`（该脚本首次运行即抓出 **4 项假 closed**）。

**J44 查重**：机械搜索确认本机无同类通用门 —— `must_fail` / `expect_fail` / `canfail` **命中 0 文件**
（`INJECT_BAD` 仅存在于星桥三个专用脚本里）⇒ J44 裁决 `no-overlap`。

---

## ② 用法（含实测退出码）

```bash
cd ~/dsh-collab/scripts

python3 gate-canfail.py --cases cases.json                    # 跑判据能红检查
python3 gate-canfail.py --cases cases.json --dry-run          # 只列将执行什么，不执行
python3 gate-canfail.py --cases cases.json --json             # 机器可读
python3 gate-canfail.py --selftest                            # ★ 门自己的负控矩阵
python3 gate-canfail.py --selfcheck                           # R006 ② TCC 能力边界自检
python3 gate-canfail.py --lean4-check                          # R006 ⑩ 约束门（本器的不变量声明）
python3 gate-canfail.py --help
python3 gate-canfail.py --version
```

### 退出码（★ 2026-10-10 实测，非读代码）

| 命令 | 实测 `rc` |
|---|---|
| `--selftest` | `0` |
| `--selfcheck` | `0` |
| `--version` | `0` |
| `--lean4-check` | `0` |
| **无参数（用法错）** | **`2`** |

★ 业务退出码取决于 `cases.json` 的判定结果（**三态**见下）；本批补课**未改变**任何退出码语义。

---

## ③ 判据（三态 —— 不看单次退出码，看「期望 vs 实得」是否一致）

| 态 | 定义 |
|---|---|
| `CAN_FAIL` | 负控例：不合规输入 ⇒ 退出码**落在期望集合** ∧ 输出含期望文本 ⇒ **判据会红** |
| `CANNOT_FAIL` | 负控例：不合规输入 ⇒ 退出码**不在期望集合** ⇒ **判据不会红**（= 日志，不是判据） |
| `POSITIVE_OK` | 正例：合规输入 ⇒ 退出码落在期望集合 |

### ★ 输出纪律（照抄本线教训）

**分离报告「判据不红」与「数据不合规」**（`is_data_case: true` 的例）：
- 前者是**判据的问题**
- 后者是**数据的问题，而判据正确地红了**

---

## ④ R006 达标矩阵

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ✓ | **独立脚本形态**（R006 口径下 `scripts/` 共享族）—— 一次性调用的判据执行器不引常驻成本 |
| ② TCC 检测 | ✓ | `--selfcheck` 三段齐（原有） |
| ③ CLD 自适应 | ✓ | 不依赖 CLD 专有路径 |
| ④ dsh 版本自适应 | ✓ | 不读 dsh 版本 |
| ⑤ 文档化 | ✓ | **本文件**（2026-10-10 补课新增）|
| ⑥ 版本管理 | ✓ | `VERSION` 单一赋值处（原有） |
| ⑦ 统一日志 | ✓ | `~/dsh-collab/logs/gate-canfail.log`（2026-10-10 补课新增）|
| ⑧ 自动落链 | ✓ | 已收录本机索引 `local-registry`（`[S1\|script] gate-canfail.py`）|
| ⑨ CLI 治理 | ✓ | **实跑 `--help` 输出含全部 5 旗标**（`--help`/`--version`/`--selftest`/`--selfcheck`/`--dry-run`）|
| ⑩ 约束门 | ✓ | `--lean4-check`（2026-10-10 补课新增；★ **如实声明本器无 `.lean` 规范源，不冒充编译**）|

---

## ⑤ 本批补课的契约声明（★ 不改行为）

**新增三件，全部【只增不改】**：
1. `log()` —— **只追加写日志**，不改变 stdout 内容与退出码
2. `--lean4-check` —— **新增旗标**，原有旗标行为不变
3. `import os` —— 为 `log()` 所需（原文件无此导入）

**★ 验证方式**：`--version` / `--selftest` / `--selfcheck` 的输出与本批前一致（实测见 §②）。

---

## ⑥ 坑（如实）

1. **只支持「退出码 + 输出文本」两类断言** —— 不做通用注入框架（有限即安全）。
2. **超时计失败** —— 不做「未观测」与「无失败」的区分。
3. ★ **本工具的 `log()` 不在【每次判定】时调用** —— 它只在 `--lean4-check` / `--dry-run` 等**入口**留痕。
   若需记录每次判定的结果，应显式调用（本批**未改业务路径**，以免改变行为契约）。

---

## ⑦ 复现命令（每条可复制即用）

```bash
cd ~/dsh-collab/scripts
python3 gate-canfail.py --help                                  # 应列出全部旗标
python3 gate-canfail.py --selftest; echo "exit=$?"              # 应 0 且报「门能区分会红与不会红」
python3 gate-canfail.py --lean4-check; echo "exit=$?"           # 应 0
python3 gate-canfail.py --version                               # 应打印版本
python3 gate-canfail.py; echo "exit=$?"                          # 应 2（用法错）
ls -l ~/dsh-collab/logs/gate-canfail.log                        # ⑦ 日志文件
```
