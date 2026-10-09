# 回应正当性门 · 中文文档

> 路径 `~/dsh-collab/devices/dsh-plugin-response-justification-gate/`
> 形态：**P3 独立 CLI**（判据执行器，非常驻）· v1.0.0 · 2026-10-10
> 本文档满足 R006 ⑤（文档化）与 R039（工具中文描述文档）

## ① 为什么需要（事故/证据）

**用户 2026-10-10 对审查线的批评**：该线「产出方法学价值，但不再产出针对交付物的缺陷」，
且**沟通质量随轮数下降**（近 14 卡中确认类占 50%）。由此提炼出「**判据贬值**」判据：
**一个规范若不被任何角色的默认流程引用，它就与它所反对的那些「无人使用的规范」同构。**

用户随后指示：**「梳理为全局判断器 · 正向约束性规范 · 沉淀为价值产物」** ⇒ 进一步
**「直接做成符合 10 项标准的工具插件以及符合 lean4 标准的逻辑工程门」** ⇒ **授权入册**。

⇒ **本器把规范 §8 的「fail-closed 三层」做成可执行判据**，使 R050 不落回「无人引用的文档」。

> 脚本自述：`response-justification-gate.py — 回应正当性门（v1.0.0）`；
> 判定一条待发输出是否具有**结构性正当依据**（有无 R 类 / 四元组是否完整）。

## ② 用法（含退出码）

```bash
cd ~/dsh-collab/devices/dsh-plugin-response-justification-gate

python3 response-justification-gate.py --check <input.json>                  # 主判（默认 advisory）
python3 response-justification-gate.py --check <input.json> --mode enforced  # ★ 真 fail-closed
python3 response-justification-gate.py --check <input.json> --mode enforced --force-send
python3 response-justification-gate.py --negative-control                    # ★ 门自身负控（独立可跑）
python3 response-justification-gate.py --selftest                            # 正例+负控矩阵
python3 response-justification-gate.py --selfcheck                           # TCC（★ 剥离字符串/注释）
python3 response-justification-gate.py --prove-strip                         # ★ 自证剥离确实生效
python3 response-justification-gate.py --lean4-check                         # ★ 与 Lean4 谓词真比对
python3 response-justification-gate.py --version
python3 mount-smoke.py                                                       # ★ 真挂载冒烟（四态）
```

**输入形态**（规范 §8）：
```json
{"to":"...", "thread":"...", "text":"...", "refs":[...],
 "claimed_r":"R1"|null,
 "quadruple":{"to":true,"thread":true,"refs":true,"text":true}}
```

**退出码**（★ R006 ⑨）：
| 码 | 含义 |
|---|---|
| `0` | 可发送（含 advisory 模式下的记录） |
| `1` | `--selftest` 有 FAIL |
| `2` | 用法或输入错误 |
| `3` | ★ **被拒**（fail-closed）—— **与「用法错 2」显式区分**，便于上游断言 |

## ③ R006 达标矩阵

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ✓ | P3 独立 CLI（规范 §7 建议形态）；★ **真挂载冒烟四态如实分报**（`mount-smoke.py`：pass 12 / fail 0 / skipped 0 / timeout 0）|
| ② TCC 检测 | ✓ | `--selfcheck` 三段齐；★ **扫描前剥离字符串与注释**（`strip_code`），并有 `--prove-strip` **自证剥离确实生效** |
| ③ CLD 自适应 | ✓ | 不依赖 CLD 专有路径；缺 `docs/` 时仍可判（只影响 `--lean4-check` 的规范源检查）|
| ④ dsh 版本自适应 | ✓ | 不读 dsh 版本；仅用 Python 标准库 |
| ⑤ 文档化 | ✓ | 本文件 + `docs/response-justification-policy.md`（规范正文，**sha256 7c84d4b4…**）|
| ⑥ 版本管理 | ✓ | `__version__` **单一赋值处**（其余 3 处为引用：注释 / banner 派生 / `--version`）—— 由 `grep -cE '^__version__\s*='` = 1 可核 |
| ⑦ 统一日志 | ✓ | `~/dsh-collab/logs/dsh-plugin-response-justification-gate.log`，**追加**，含时刻 + 判定 + 输入 sha |
| ⑧ 自动落链 | ✓ | 登记卡 `data/registry/dsh-plugin-response-justification-gate`（本器产出）；★ 无网络时**如实标记未验证** |
| ⑨ CLI 治理 | ✓ | `--help` / `--version` / `--selftest` / `--selfcheck` / `--dry-run` / `--lean4-check` / `--negative-control` / `--prove-strip` |
| ⑩ 约束门 | ✓ | ★ 见 §④；`--lean4-check` 为**真比对**（18/18）|

## ④ 约束门（⑩）与 fail-closed 三层

**规范 §8 三层**（本器的实现）：

| 层 | 条件 | 行为 | 可核 |
|---|---|---|---|
| **1 默认拒绝** | `enforced` ∧ 无 R 类或四元组不全 ∧ 未 `--force-send` | **exit 3**，不出可被误用的读数 | `--check no_r.json --mode enforced` ⇒ 3 |
| **2 显式承担** | 加 `--force-send` | exit 0，但输出**自标**「`[无 §2 依据]`」 | 输出含该标记 |
| **3 豁免后仍标注** | 即使越过 | `annotate()` **把标记真的注入 text**，不只在读数里说明 | `--prove` 见 selftest 的 `annotate` 用例 |

**★ 门自身负控（硬要求④）** —— `--negative-control`，**独立可跑、不藏在 selftest 里**：
```
无 R 类（四元组完整）  ⇒ exit=3 已拒
四元组不全（有 R 类）  ⇒ exit=3 已拒
两者皆缺              ⇒ exit=3 已拒
有 R 类 + 四元组完整   ⇒ exit=0 放行（正例对照）
```
> 依据：本机 `scripts/gate-canfail.py` —— **「一个判据若没有能让它失败的输入，
> 它就不是判据，是日志。」**

## ⑤ ★ 两处必须说明的实施决定（★ executor 对规范的报告，非自我裁定）

**决定一：`advisory` / `enforced` 双模式**
规范 §8 要求「默认拒绝」，而 R050 现为 `advisory`（依据规范 §9.1：R 类枚举不完备 ⇒ 会误拒）。
**二者不能同时字面执行。** 本器处置：
- `--mode advisory`（**默认**）：判定照跑、落日志、出读数，但 **exit 0**，输出带 `[advisory]`
- `--mode enforced`：§8 的**真三层 fail-closed**
- ★ **负控不受 mode 影响** —— 无论哪种模式，`--negative-control` 都必须产出拒绝读数

⇒ **该解释已在接单回报中向 proposer（裁判 `session-1ffded95`）提出并请求裁决。**
⇒ 本器**两种模式皆可实现**任一裁决 ⇒ 裁决到达后无需重写。

**决定二：`--lean4-check` 做【真比对】而非只打印声明**
本机范本 `tools/acceptance-gate.py` 的 `lean4_parity()` **恒 `return 0`**（只打印一行声明，
不比对任何东西）。★ 本器**真的读 `.lean` 文件并与 Python 函数名逐一对账**（18 项）——
否则「谓词 1:1」只是**声称**。**这正是本线今日反复出现的形态（声称已接上，实际未接）。**

## ⑥ 限度（规范 §5 · 不可自判性）—— 本门**不**判定

| 不判定 | 原因 |
|---|---|
| 「该回应是否真的改变了接收方的判定或行为」 | **不可事前测** |
| R1–R6 是否完备 | **尝试性穷举**；不完全 ⇒ 门会误拒（故保留 `--force-send`）|
| 跨角色适用性 | 判据基于**审查场景**；其他角色可能不同 |
| **规范本身是否成立** | ★ **本器作者是 executor，规范 proposer 是裁判** ⇒ **不自裁自审** |

⇒ **本门只拦【结构性缺席】**，并保留逃生口。

## ⑦ 坑（如实）

1. **命名门第一次未过**：purpose 写太长（含 `{to,thread,text,refs}` 等字段名）⇒ 机械提取把
   `to` 吸进 slug，产出 `response-justification-gate-to`。**收窄 purpose 为
   `response justification gate` 后通过**。⇒ 建议记入 R047 的坑位：**purpose 里的输入字段名会被当 token。**
2. **本机无 lean4 运行时**（`lean`/`lake`/`elan` 均缺席）⇒ `--lean4-check` 是**谓词对应性检查**，
   **不是编译**。此点已在输出中显式声明，**不冒充编译通过**。
3. **`--prove-strip` 的探针是弱判据**：它只证明「探针字符串在剥离后消失」，不证明剥离器对
   **所有**字面量正确。⇒ 真正的防线是 `strip_code` 用 `tokenize`（标准库词法器）而非手写正则。

## ⑧ 复现命令（第三方可独立实跑）

```bash
cd ~/dsh-collab/devices/dsh-plugin-response-justification-gate

# ★ 1. 真挂载冒烟（四态）
python3 mount-smoke.py

# ★ 2. 负控（门必须能红）—— 独立可跑，不在 selftest 里
python3 response-justification-gate.py --negative-control; echo "exit=$?"

# ★ 3. 三层的逐层实跑
echo '{"to":"x","thread":"y","text":"z","refs":["a"],"claimed_r":null,"quadruple":{"to":true,"thread":true,"refs":true,"text":true}}' > /tmp/nr.json
python3 response-justification-gate.py --check /tmp/nr.json --mode enforced; echo "层1 exit=$?（期望 3）"
python3 response-justification-gate.py --check /tmp/nr.json --mode enforced --force-send; echo "层2 exit=$?（期望 0，且输出带标注）"

# ★ 4. 剥离自证
python3 response-justification-gate.py --prove-strip

# ★ 5. Lean4 谓词真比对
python3 response-justification-gate.py --lean4-check

# ★ 6. 版本单一来源（赋值处须 = 1）
grep -cE '^__version__\s*=' response-justification-gate.py
```

## ⑨ 边界声明

- **本器不裁规范本身**（proposer ≠ executor 原则）
- **本器不自审自己的交付**（R046：执行方 ≠ 裁定方）⇒ 交付后由裁判独立实跑
- **本器不触碰星桥交接线**（`thread-mv11hpn9`），**不向 `session-e317d6ab` 投递任何内容**
