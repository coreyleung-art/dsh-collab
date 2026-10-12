# 04 · `dod.full_table` 从未落盘 —— DoD 该怎么存成可机器判的形态

> **调研代理**：R-M4M5 · **出件时刻**：2026-10-12T20:4x+0800
> **问题**：`dod.full_table` 仍为「缺席」。业界的 DoD 该怎么存？给可机器判的形态。

---

## 一、现测：`dod.full_table` 此刻是什么

**复跑命令**：

```bash
python3 -c "
import json,os
d=json.load(open(os.path.expanduser('~/dsh-collab/data/registry/continuity-index.json')))
print(json.dumps(d['dod'],ensure_ascii=False,indent=1))"
echo "rc=$?"
```

**未编辑原始输出（2026-10-12T20:4x+0800，rc=0）**：

```json
{
 "_note": "§11 原文称「全文表见 data/registry/continuity-index 的 dod 字段」——实测该字段从未建立，即 §11 正文表格只是代表性摘录。**不得凭空补全**（R030）：补全须由各项负责人在沙箱复跑后逐条填入 8 字段（正向判据 / 负控 / 边界 / 测量方法与样本量 / 阈值 / 证据形态 / 审查员 / 沙箱复跑方式）。",
 "_status": "**缺席**",
 "full_table": null,
 "rule": "正向 ∧ 负控红 ∧ 边界不崩 ∧ 阈值达标 ∧ 沙箱复跑一致 ∧ 官方条款无未声明差异 —— 六者缺一不得记 closed_with_evidence"
}
```

★★ **三条现测事实**：

1. **`full_table` 确为 `null`，`_status` 是字符串 `"**缺席**"`** ⇒ v6.1 §11.1（`:1955`）的自陈**仍然成立**。
2. ★★ **`dod` 字段里唯一有内容是那个 `rule` 字符串** —— 它是**六者齐备规则**的**自然语言抄本**，
   **不是可执行断言**。★ 这一点很重要：
   **本机已经"存了规则"，但规则"没有形态"** ⇒ 见 `05`（把这条规则变成可跑检查）。
3. ★★ **`beacon-check.py --net` 里有一条 `PASS dod.full_table 的缺席是显式声明的`** ——
   **这条检查把「缺席」判成了绿**。它是本轮现测的（`01` §一 的原始输出里逐字可见）。
   ⇒ ★★★ **这是 P27 家族的一个新实例**：判据从「表填没填」退化成了「有没有声明没填」。
   ★ **本项目纪律「一个断言若从未红过，它就不是判据」** ——
   这条断言**只会在「有人删掉那句声明」时红**，而与「DoD 有没有落盘」**完全无关**。

**分母有多大（现测）**：

```bash
grep -oE 'W[0-9]\.[0-9]+' ~/dsh-collab/docs/distributed-agent-network-governance-plan-v6.1-20261011.md | sort -u | wc -l
grep -n '^| \*\*S[1-5]\*\*' ~/dsh-collab/docs/distributed-agent-network-governance-plan-v6.1-20261011.md | wc -l
sed -n '1944,1950p' ~/dsh-collab/docs/distributed-agent-network-governance-plan-v6.1-20261011.md | grep -c '^|'
```

- 锚点 §10 自称 **39 项 W**（`:1702` 的计数更正）+ **S1–S5** ⇒ **需求 DoD 的项约 44**。
- ★ §11 正文**代表性表只有 7 行**（S5 G-CR 门 · C5 反遗忘校验 · W0.1 · W0.6 · W1.1 · W2.5 · W4.1）。
- ⇒ ★★ **落盘率 = 0 / 44**（★ 且这个 44 本身**不是权威计数**：`grep` 唯一 W 号得 72，
  与 §10 自称的 39 对不上 —— **锚点内部第二次出现「计数不符」**，第一次见 `01` §六的「25 vs 28」）。

---

## 二、业界做法（一手来源）

### 2.1 DoD 分成**两栏**：机器可判 / 人来判

来源：[agentic-dev-framework – definition-of-done.md](https://github.com/laugiov/agentic-dev-framework/blob/master/runtime/quality-gates/definition-of-done.md)（**已读原文**）。

原文逐字：

> Criteria are organized by change type and split into **machine-checkable and human-judgment categories**.

它对每一类改动（文档类 / 代码类 / 配置类 / schema 类 / 安全敏感类）各给一张表，**每张表两栏**：

| 类别 | Machine-Checkable（例） | Human-Judgment（例） | Proof Artifacts |
|---|---|---|---|
| 通用 | 内部链接不坏 · 无合并冲突 · 提交信息合规范 · **所有必需文件在位** | 改动匹配原始目标 · 无意外副作用 · 文档清晰准确 | — |
| 代码 | **测试通过** · lint 通过 · 静态分析通过 · **覆盖率未下降** · 无新安全漏洞(SAST) | 可读性 · 遵循既有模式 · 错误处理恰当 | 测试输出 · lint 输出 · 覆盖率报告 |
| 配置 | 语法有效 · **schema 校验通过** · **无明文密钥** · 无硬编码环境值 | 向后兼容 · 环境适配 · 安全影响 | schema 校验输出 · 密钥扫描输出 |
| 安全敏感 | SAST 通过 · 依赖漏洞已查 · 无密钥提交 | **安全评审已完成** · 威胁模型已更新 | 安全扫描输出 · **安全评审批准** · 威胁模型引用 |

★ 末尾一句（**与我们的「不得静默通过」同源**）：

> If a criterion cannot be met: Document the exception clearly · Explain why it cannot be met · **Get approval from human reviewer** · Track as technical debt if appropriate.
> **Never silently skip criteria.** Done means done. Not "mostly done" or "done except for."

★★ **对本机的直接映射**：本机 §11 的八字段里，**「审查员」就是 Human-Judgment 那一栏**，
**其余七个都是 machine-checkable 的**。⇒ **八字段天然分成 7 + 1**，
**而 v6.1 把「审查员」与其余七个并列成同一种字段，导致它被当成「填个名字就行」**
（现测：6 个 closed 项的 verifier 全部填了**占位串**，见 `01` §四）⇒ **这正是把两栏混成一栏的后果**。

### 2.2 DoD 存成**可跑断言列表**（executable acceptance DSL）

来源：[agentbazaar – Acceptance Guide](https://github.com/aiskillstore/marketplace/blob/5526951beaeca22519572a471618555839b53b05/skills/ptreezh/agentbazaar/references/acceptance-guide.md)（**已读原文**）。

核心主张逐字：

> The platform rejects vague acceptance. Every task's `acceptance[]` must be a list of **runnable assertions**.
> This is how agents keep review deterministic and low-context: **the same assertions any reviewer runs**.

它给的 DSL 只有 5 个谓词（**这一点值得照抄：谓词要少**）：

| type | 必填字段 | 含义 |
|---|---|---|
| `file_exists` | `path` | 文件存在 |
| `row_count` | `path, op, value` | CSV 行数与 op+value 比较（`ge`/`gt`/`eq`…） |
| `col_check` | `path, col, op, value` | 该列所有行满足 op+value |
| `json_path` | `path, path_expr, op, value` | JSON path 等于/比较某值 |
| `hash_match` | `path, sha256` | 文件 sha256 等于期望 |

原文的 spec 示例（逐字）：

```yaml
acceptance:
  - {type: file_exists, path: result/result.md}
  - {type: file_exists, path: result/result.json}
  - {type: json_path, path: result/result.json, path_expr: "$.status", op: eq, value: "done"}
  - {type: hash_match, path: result/output.csv, sha256: "9f2c..."}
```

**CI/CD 风格门（原文）**：

```yaml
verification:
  script: "node check.js"    # exit 0 = pass, non-0 = fail
  timeout: 60
```

原文对边界的诚实声明（★ 值得照抄这句态度）：

> **Honest boundary**: the script can still touch the filesystem — reviewers must run it in an isolated environment with no sensitive data or keys.

原文的**反模式清单**（逐字，**几乎逐条命中本机的 §11 现状**）：

> - "Looks good", "basic completion", "reasonable quality" → **rejected**.
> - **Acceptance without input samples or runnable rules** → rejected.
> - Acceptance that requires human judgment of taste → split into objective checks.

★★★ **第二条「没有输入样本或可跑规则的验收 ⇒ 拒收」**，正是本机 `dod.full_table` 的**缺席原因**与**解法**：
本机 §11 的八字段里**恰恰有 `测量方法与样本量`** —— 这条字段**就是业界说的「input samples」**。
⇒ ★ **本机八字段的设计本身是对的**（比 agentbazaar 的 5 谓词 DSL 更细），
**缺的不是 schema 设计，是「存下来 + 接进 CI」**。

### 2.3 DoR/DoD 并置（避免「不满足前提就开工」）

来源：[HugeRouter – Definition of Ready and Definition of Done](https://raw.githubusercontent.com/OpenHuge/HugeRouter/refs/heads/main/docs/execution/05-definition-of-ready-and-done.md)（**已读原文**）。

DoR（开工前）：上游依赖已合并或打桩 · **文件归属清晰** · 输入输出已指定 · **验收标准可测** ·
需要的 schema/迁移/配置变量已识别 · 未完全暴露的特性有隐藏开关声明。

DoD（完工）：编译与本地检查通过 · **针对被改动行为的测试已加或已更新** · 按仓库政策需提交的产物已提交 ·
用户/运维可见流程变化时文档已更新 · **运维上有意义的特性有 metrics/traces/logs** ·
安全敏感改动在适用时**发审计事件** · 无明文密钥或环境特定值。

★ DoD-plus（热点网关与计费类）：考虑延迟/吞吐影响 · **幂等与重放行为已定义** · 降级依赖行为已测 ·
**失效模式产生规范化错误与诊断上下文**。

★★ **对本机的价值**：本机缺 **DoR 这一整栏**。
现测证据：`docs/v7-unfinished-inventory-20261012.md` 里 M2 的 39 项 W 项**全部 `open`**，
而 M1 记着「39 项完成 0 项」⇒ ★ **不是「做完没记」，是「一批从未定义开工前提的工作」**。
⇒ ★ v7 应当**先落 DoR**（本机的 DoR 现成：§5.3 的信息包 14 项 + §11 的「沙箱复跑方式」）。

### 2.4 ★ 一条必须知道的分界：**attestation 是证据，不是接受决定**

来源：[A SLSA Attestation Is Evidence, Not the Acceptance Decision](https://btw.media/en/slsa-attestation-evidence-not-acceptance-decision)
（★ **本件未读到原文 —— 页面读取超时**，**仅见标题与检索摘要** ⇒ **如实标：未读原文**）。

★ 但该标题所指的分界，在本机**已有独立印证**：
锚点 §5.1 的「**未证不得记 closed**」+ `review-tracker.json` 的那条 `_correction`
（「移除一条违规登记：executor 与 verifier 同为 session-1ffded95」）。
⇒ ★★ **本机已经区分了「有证据」与「被判通过」** —— 这与上述标题同向。
★ **本件不把这条外部来源当作论据**（未读原文），只作**旁证命名**。

---

## 三、★ v7 的可落地形态

### 3.1 存储形态：**一项一条 JSON 记录，落盘在索引里（不是 markdown 表）**

```jsonc
// data/registry/continuity-index.json → dod.full_table[]
{
  "schema": "dod/v1",
  "items": [
    {
      "id": "W0.6",
      "title": "装载事件数门",
      "spec_ref": "docs/distributed-agent-network-governance-plan-v6.1-20261011.md#10",

      "//": "─── §11 八字段，逐字保留原字段名（不重命名，避免漂移）───",
      "正向判据":        "超阈值报错而非崩；阈值内放行",
      "负控（必须能红）": "构造超大会话 ⇒ 必须以非 0 退出且打印拒绝日志",
      "边界用例":        ["恰好等于阈值", "阈值下 1 行", "空会话"],
      "测量方法与样本量": {"n": 3, "samples": ["合成会话 240MB", "合成会话 199MB", "空会话"]},
      "阈值与判定规则":   {"expr": "refuse_rate == 1.0 and crash_count == 0", "window": "per-run"},
      "证据形态":        {"kind": "stdout+exit_code", "path": "evidence/out/W0.6.txt"},
      "审查员":          {"session": null, "status": "verifier_unavailable", "reason": "S3 禁自审"},
      "沙箱复跑方式":     "cp -a profile /tmp/sbx && DSH_HOME=/tmp/sbx dsh …",

      "//machine": "─── 机器可判部分（★ 新增，八字段里没有的）───",
      "assertion": {
        "type": "run_and_exit",
        "cmd": "python3 tools/load-gate-test.py --session /tmp/big.jsonl",
        "expect_exit_nonzero": true,
        "timeout_s": 60
      },
      "negative_control": {
        "cmd": "python3 tools/load-gate-test.py --session /tmp/small.jsonl",
        "expect_exit": 0
      },
      "state": "open",
      "last_run": {"at": null, "exit": null}
    }
  ]
}
```

### 3.2 ★ 四条「能红」的机器判据（CheckDoD）

```bash
# CheckDoD：读 dod.full_table，对每一项做四条断言；缺一即红
python3 tools/dod-check.py --index data/registry/continuity-index.json --strict; echo "rc=$?"
```

| 判据 | 正向 | **负控（必须红）** |
|---|---|---|
| **D1 · 八字段齐** | 每项八个键都存在且**非空**（`审查员` 允许 `verifier_unavailable`，但**必须带 reason**） | 删掉任意一个键 ⇒ 必须红。★ 本机已有同型实现在 `tools/infopack-check.py`（14 项 + 两条硬要求，`--selftest` 5/5） |
| **D2 · 可执行** | 每项的 `assertion.cmd` 是**自包含**的（★ 禁引用 `/tmp` 等易失路径，§5.3 第 5 条已立此规矩） | 把 cmd 里的路径改成 `/tmp/x` ⇒ 必须红 |
| **D3 · 负控能红** | `negative_control` 存在，且**最近一次运行确实使它红过**（`last_run` 有 `expect_exit` 与实得不符的历史） | ★★ **从未红过的负控 ⇒ 必须红** ← **本项目纪律的机器化** |
| **D4 · 双状态分离** | `state == closed_with_evidence` **要求** `审查员.session != null` 且 `status == "approved"` | 把 `审查员.session` 置 null 而 `state` 仍为 closed ⇒ 必须红（★ 本机 `beacon-check` 已有近似项：`PEND closed 项审查员已到位`） |

★★ **D3 是本件最重要的一条**：它把**项目纪律**（「从未红过就不是判据」）**变成了 CI 判据**。
★ 本机**已有的活标本**证明这条纪律可行：
`evidence_index` 里那条逐字写着「**⇒ 这是一个【能红能绿】的完整演示**：加检查→红（抓到 7 条）→处理→绿，且**没删任何数据**」。
⇒ ★★ **本机已经证明过「一条判据能红能绿」是做得出来的** ⇒ **现在要做的是把它变成对每一项 DoD 的强制要求**。

### 3.3 ★ 接进 CI（三条具体接法）

1. **`dod-check.py` 进 pre-commit / git hook** —— 改 `continuity-index.json` 即跑 D1。
2. **`dod-check.py --execute` 进夜间 launchd** —— 跑每项的 `assertion.cmd`，结果写回 `last_run`。
   ★ 本机已有 **79 个 `com.dsh.*` launchd 任务**（`01` §六）；**新增一个的边际成本极低**。
3. **门禁**：`beacon-check.py --net` 加一条 **`FAIL dod 项已 closed 而 D3 未满足`**。
   ★ **注意**：现在的 `PASS dod.full_table 的缺席是显式声明的` **必须被替换**，
   **不是被追加** —— 否则新判据会被旧判据的绿掩盖（**这正是 B9 两份实现的老毛病**）。

### 3.4 ★ 与「不得凭空补全」（R030）的关系

锚点 §11.1 原文：

> ★ 按 R030，**v5 不凭空补全**；补全须由各项负责人在沙箱复跑后逐条填入。

★★ **这条约束是对的，本件不主张 v7 一次性补全 44 项**。
⇒ ★ **本件主张的是一个更小的动作**：**先落「形态」，再逐条填「内容」**。

```
第一步（可立即做，零内容）  →  落 schema + dod-check.py + D1..D4 四条判据
                              ⇒ 此时 full_table = []，D1 报「0 项 / 0 项」= ★ **不可判**（不是绿）
第二步（逐项）              →  每完成一项，填一条；D1 由「不可判」转「n/n」
第三步（可选）              →  --execute 接夜间任务，D3 开始有数据
```

★ **第一步的关键**：`full_table = []` 时 **D1 必须报「不可判」**（因为「应填多少项」这个分母**本身没定义**，见 §一 的 72 vs 39）。
★★ **这正是本项目「空 ≠ 无」纪律的直接应用**：**空表不得报 OK，也不得报 0%**。

---

## 四、★ 本件的阴性证据

**搜过的面**：
- 本机：`continuity-index.json` 的 `dod` / `items` / `evidence_index`(74 条) / `known_gaps` / `waves`；
  `tools/beacon-check.py --net`（含 `dod.full_table` 那一行）；`tools/infopack-check.py`（14 项 + `--selftest` 5/5）；
  `tools/review-gate.py`（R048 时值）；`docs/…-v6.1…md` §10/§11 全文。
- 外网：DoD 机器可判/人判分栏、可执行验收 DSL、DoR/DoD、SLSA attestation 定位。

**未搜到（★ 未搜到 ≠ 不存在）**：
1. ★ **未找到本机任何一处存放「逐项 DoD」的结构化文件** ——
   搜索面 = `continuity-index.json` 的 `dod` 字段、`data/registry/*.json` 的文件名、
   `tools/infopack-check.py`（它是**信息包**检查器，**不是 DoD 检查器**，两者**不等价**）。
   ⇒ **未搜到 ≠ 不存在**：`data/registry/` 有 1278 键，**本轮未逐键读内容**。
2. ★ **未查** `§11 的 8 字段是否在别处（如 `docs/wave-s-toolchain-delivery-v1.md`）以 markdown 形式散落**。
   ⇒ 若散落，**「从未落盘」这个表述就不精确**（可能只是「从未以结构化形式落盘」）。
3. ★ **未读原文**：SLSA「attestation is evidence, not the acceptance decision」（页面读取超时）⇒ 本件不当论据用。
4. ★ **未做**：`dod-check.py` 的**实现**（本件只给形态与判据；★ **图纸不等于落成**）。

★ 本件不主张任何事项闭合（S3）。
