# 原则落脚清单（PRINCIPLES → 落脚件 → 判据 → 反控）

> **为什么有这份文件**（星桥 2026-10-10 判决 F 逐字）：
> 「**原则不会自动跨门传导：一条原则落在一个门里，不保证下一个门继承它。**」
> 实证：`qk-structure-guard` 用了「开声明通路」（根级 `_qk_moved_to`），而**同一个作者**写的
> `evidence-channel-guard` 当时**只给建议、不给声明** —— 同一条原则没有跨过那道门。
> ⇒ 本清单是**原则的落脚表**：每一条原则都必须指名「落在哪个件的哪一节」，并被机械核验存在。

**机械核验**：`python3 tools/principle-landing-check.py`（每条原则的落脚文件必须存在且含标记串；
缺项即红）。这也让"清单自己过期"变成可发现的事。

| # | 原则（一句话） | 落脚件 | 判据（怎么被强制） | 反控（怎么知道它真的在起作用） |
|---|---|---|---|---|
| P1 | **判据必须有能让它失败的输入**（否则是日志） | `tools/*mutation*.py` · `--selftest` | 各 harness 自带正控 | 正控实跑变红 |
| P2 | **该绿的也要有**（只测必红＝只证明门没睡着） | 各 harness 的反控 | 反向对照常驻 | M5/M7 · 反控1–4 实跑为绿/黄 |
| P3 | **防假红的措施本身会制造假绿** | `tools/evidence-channel-guard.py` 文件头「两视图」 | live/raw 同下标合判 | v1 恒绿 → v2 正控红（已记） |
| P4 | **处置假红要开声明通路，不放宽判据** | `qk-structure-guard.py`（根级 `_qk_moved_to`）· `evidence-channel-guard.py` 文件头「声明通路」 | 未声明即红；声明只降为黄并逐条打印 | 正控3（未声明 pipefail 仍红）· M6 红 |
| P5 | **未声明 ⇒ 不可判，非 PASS** | `csx-mount-record-check.py`（`mode=unknown`）· `k6-partial-guard.py`（partial 必须带原因） | 缺字段即红 | M6/M8 红 · 负控 A/B 红 |
| P6 | **放宽前先量「已知事故是否被放绿」** | `tools/incident-regression.py` | 6 起事故语料一次跑完；`--enrollment-check` 核「新门有没有入网」（未入册/无声明 ⇒ 红；他人维护的列为**待办**逐次打印，`--strict` 下亦红） | 编排层 `--selftest`（注入必败 case） |
| P7 | **覆盖面必须显式声明**（写出**不覆盖**什么） | 各门文件头的「不覆盖 / 不主张」节 | 人工核 + 本清单核标记串 | 判决 D 的"未落盘命令不覆盖"即此条产物 |
| P9 | **原则要跨到「人的动作」上**：知道该查 ≠ 已经查了（规则在文档里，须有判据在管） | `tools/live-role-resolve.py`（两表交叉 + 歧义拒答）；**唯一硬信号＝发送时的 `targetLive`** | 三态/四态可分 + **默认路径须干净报错**（见右列「真跑」两条） | ★ **真跑（由 `principle-landing-check` 执行，非抄写）**：<br>① `python3 tools/live-role-resolve.py --selftest` ⇒ 期望 exit 0<br>② `python3 tools/live-role-resolve.py --role 裁判`（**不带 `--peers`**）⇒ 期望 exit **非 0 且不抛栈**<br>★ 完整解析命令须带前提：`--role 裁判 --peers <agent_peers 快照>`（`--peers` **事实上必需**，CLI 层却是选填 ⇒ 已加守卫） |
| P8 | **以声明代证据的机制，必须有「声明层何时复审」的规矩** | `tools/incident-regression.py`（`TABLE_REVIEWED_AT`）· `tools/principle-landing-check.py`（`REVIEWED_AT`） | 表级复审日 + 间隔；**过期即红**（不是提醒） | 沙箱把复审日改早 ⇒ 红（101 天 > 30 天） |

## 维护约定

- 新增一条原则 ⇒ 必须同时给出「落脚件 + 判据 + 反控」三列，并在落脚件里写可被 `principle-landing-check.py` 命中的**标记串**。
- 某门**只给建议、不给声明通路**时 ⇒ 要么补声明通路，要么在 P4 行里**显式标注不适用**（不适用也是一种声明）。
- **声明层到期复审（P8）**：本文件的落点表（REGISTRY）与各门的 EXEMPT/PENDING/COVERED_BY 表都是"以声明代证据"，
  故均带 `REVIEWED_AT` / `TABLE_REVIEWED_AT`；过期即红，复审内容 = 每项**要么入册、要么换理由、要么移除**。
- 本清单**不主张**覆盖全部工程原则：只收录「本轮由事故换来的、且已被机械核验」的那几条。
