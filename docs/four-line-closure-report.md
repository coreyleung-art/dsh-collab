# 四线收口报告（2026-10-10）

> `goal-5051b1f8-a9ad-446b-a5e7-d012ed6025f9` · revision 3 · round 12/40 · **active**
> **口径**：本文件全部 16 位 hex = **SHA-256 全量摘要前 16 位小写 hex**
> **生成者**：裁判 `session-1ffded95`

---

## §1 四线状态

| 线 | 内容 | 状态 |
|---|---|---|
| **① R006 工具库** | 批次3（⑥⑦⑤）executor=PSTD · 我作 adjudicator | ⚠️ **我方复核已完成；PSTD 施工后未报** |
| **② 我方自办** | (a) 新 ⑦ 判据全批复跑 (b) 新判据入方法学 | ✅ **完成** |
| **③ call-dispatcher** | adjudicator 复核（负控 0–5 + R006 十项） | ⏳ **本体未施工** |
| **④ 语音域审查** | 待核两项（误报率 · R038 通道） | ✅ **完成** |

### 线① 的实质判定

**批次3 的 ⑥⑦ 均未解决**（用 T3 的独立实跑读数）：

| 项 | 6 个批次3 工具中的状态 |
|---|---|
| **⑥ 版本单一来源** | **5/6 仍缺**（`gate-canfail` 是唯一不缺的） |
| **⑦ 统一日志** | **6/6 仍缺**（5 个「声明但文件不存在」+ 1 个「存在但未追加 7→7」） |

**★ 与 T7 互相印证**：**⑥ 未解决的原因就是【补课器注入的第二处 `__version__`】** —— 已独立复现：
`absence-claim-lint` `1.0.0` vs `3.13.0` · `citation-stale-check` `1.0.0` vs `2.1.0` · `verification-level-lint` `1.0.0` vs `2.0.0`

**★ 但我如实标明**：**我不判「未交付」** —— **我只测了结果面，没看它的变更声明**（它尚未报批次3）。
**若它报「已修但仍红」⇒ 属「实测不符」；若未报 ⇒ 属「施工未完成」。两者不同。**

---

## §2 交付物

| 文件 | sha256[0:16] | 规模 |
|---|---|---|
| `docs/audit-method-notes.md` | **`443507935f7c2934`** | 26159 B · **449 行 · 19 节** |
| `docs/call-dispatcher-project-charter.md` | **`8b4953bd8863b616`** | 10536 B · 177 行 |
| `docs/audit-criteria-triage-decision.md` | `994a1145093fbacd` | 5235 B · 98 行 |
| `docs/toolbox-completion-report.md` | `c95730cb2d3cb4c6` | 6871 B · 141 行 |
| `scripts/r006-two-tool-audit.py` | **`1791e14cac75808b`** | 48031 B（⑦ 三次升级） |
| `scripts/toolbox-selftest-sweep.py` | `388a68a2d78aaa48` | 35560 B · selftest **6/6** |
| `audits/_review-toolmap.md` | `1661d35d05facdc6` | v3.3 · 86 行 |

**卡（`data/registry/`）**：`t3-done-and-t6-batch3-verdict-6-and-7-unresolved` · `t7-verified-retrofit-created-the-violation-it-fixes` · `voice-detector-false-positive-rate-measured` · `voice-r038-channel-verdict-two-channels-not-linked` · `i-was-wrong-on-lines-and-missed-the-guard-chain` · `diagnosis-family-third-member-and-my-fresh-example` · `handover-process-judgment-toolkit-to-xq`

---

## §3 关键发现（本轮的判据级产出）

### ① 「实跑级」不是终点，还要选对【跑哪个动作】

**⑦ 判据连错三级**：源码含 `logs/` 字面量（声明级）→ `logs/` 下文件存在 → **跑一次后追加行数 > 0** → **触发入口须选对**（`--dry-run`/`--help` → `--selftest`）。

**⇒ 判据（跑后追加 > 0）从第二级起就没变，变的是用什么触发它。**
**⇒ 所以「实跑级」是【相对】概念：跑一个不相干的动作，仍是声明级。**

### ② ★★ 诊断族第三员：**判据覆盖缺口**（星桥分类）

| 族 | 症状 | 防线 |
|---|---|---|
| **仪器失明** | 没读到 | ✅ 换仪器 |
| **空集通过** | 读到空集 | ✅ 负控求证能红 |
| ★★ **判据覆盖缺口** | ★ **读到了，但判据没问** | ★ **无** |

**星桥指它无防线的理由（本轮最重要一句）**：
> **「它长得像『已经核过了』——判据存在、真的在跑、也可能在别的输入上真的红过。」**

**两个实例**：**星桥的 K5 标定**（交叉核对只覆盖 1/4 粒度，自评**「实测全一致，但那是运气不是覆盖」**）· **我的 F118**（`"追加" in l7` 匹配到「未追加」）。

### ③ `allow` 不是终点 —— guard 链（星桥发现，我漏了）

```
3116  const denialReason = decision.kind === "allow" ? this.guardReason(exec) : decision.reason;
2813      const globalReason = this.layers.global.guardReason(exec);   ← 先全局层
2815      if (exec.agent === void 0) return void 0;                    ← 再 scope 链
```
**⇒ 「建议式拒绝」有两条通路；只挂 waterfall 的 dispatcher 看不到 guard 链的拒绝** ⇒ **采纳为负控 5**。

### ④ 语音域②：误报率实测 = 1/3，根因是【容差口径】

**6 项 / 3 命中滞后**：**1 真误报**（`C`：差 3782s ≈ 63 分钟，而两文件「同为初次创建当天」）· **1 已知未提交** · **1 待处置**
**⇒ `--lag-tolerance` 默认 120s，拦不住它想拦的「同一次创建」。**

### ⑤ 语音域③：两通道未互引 + 一处位置错

`version-matrix.json` 里 `services/心跳/hb-fwd/registry/drift-scan` **全 0 命中**；
**且 R038 声明的 `drift-scan` 不在 `scripts/`** —— 它是**插件层 `drift_scan` 工具** ⇒ **不是不存在，而是「不在账本读者会去找的位置」**。

### ⑥ 「权限」不是防线（星桥）

> **「我把『可独立复跑的事实』说成了『你的范围』—— 那一刻我就把事实换成了权威，而权威正是最容易被下一个人继承而不复核的东西。」**

**⇒ 正确做法是【并列而非取代】**：不删除前人的声称，而是重上一条证据。

---

## §4 未闭合（不假装完成）

1. **线① 批次3 的实际交付状态** —— PSTD 施工后未报；我方复核读数已出
2. **线③ call-dispatcher** —— **本体未施工**（`~/dsh-plugin-call-dispatcher` 与 `devices/` 下均无）
3. **`audits/_review-toolmap.md` 未用新 ⑦ 判据重生成**（T3 读数已在 `/tmp/r006-planb.json`，但 toolmap 仍是 v3.3）
4. **⑦ 的 2/18 真写日志** —— 16 个工具的 ⑦ 缺口未修（属 PSTD 范围）
5. **语音域 ② 的误报已 ack 但未修** —— 容差改为「同一次创建」类判据属属主权
6. **`devices/` 52 个插件未纳入** R006 全面（已抽审 5 个：`pass10 = 0`）

---

## §5 我方失误（本轮新增）

| # | 内容 | 族 |
|---|---|---|
| **F116** | 行数用「段数」（`split("\n")` 长度 3578）当「行数」（实为 3577） | **口径错** |
| **F117** | 判据只问「waterfall 能否 deny」，未覆盖「allow 之后」 | **判据覆盖缺口** |
| **F118** | `"追加" in l7` 匹配到「未追加」 | **判据覆盖缺口** |
| **F114/F115** | `arguments` wrapper ×2（累计 **9 次**） | **接口约定** |
| **F109/F110** | 卡缺 `subject` ×2 | **接口约定** |
| **路径错** | system prompt 里故障模式库写作 `20260404`，真名 `20261004` | **引用未核** |

---

## §6 复现命令

```bash
# 线① 批次3 复核（R006 十项逐工具）
python3 ~/dsh-collab/scripts/r006-two-tool-audit.py --tool <path> --json
# 新 ⑦ 全批复跑（T3 的读数来源）
python3 /tmp/r006-planb.py   # 结果 /tmp/r006-planb.json
# ⑥ 违规独立复现
grep -n "^__version__\|^VERSION" ~/dsh-collab/scripts/{absence-claim-lint,citation-stale-check,verification-level-lint}.py
# 线④ 语音域检测器
python3 ~/dsh-collab/cld-voice/tools/check-version-sync.py
# 线③ 挂载点证据（call-dispatcher 前置）
F=/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools/lib/index.js
grep -n 'tools/pre-execute' "$F"; grep -n 'no guard can force-allow' "$F"; wc -l "$F"
```

---

*四线收口报告 v1.0 · 2026-10-10 · 线②④ 完成 · 线① 我方部分完成 · 线③ 未开始*
