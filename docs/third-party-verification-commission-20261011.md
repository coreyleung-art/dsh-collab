# 第三方复核委托件（★ 一份 · 交 Claude）

> **委托人**：星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4`（mac-mini）
> **转交**：用户（2026-10-11 指示：「如果需要第三方的，等到最后全部再对外写一份委托给 claude，我明天帮你发」）
> **受委托方**：外部第三方（CU 实验台线 · Claude Code 会话 · 角色键 `ext`）
> **锚点**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3`
> ★ 本件**只此一份**，涵盖 2026-10-10 夜至 10-11 凌晨的全部交付。

---

## 〇、给复核者的第一句话

**本批全部结论均为「起草人自测，无独立 verifier」** ⇒ 依 S3（不可自审）**一律不得记 `closed`**。
本件即为补齐该缺口而写。★ **凡本件未列出的东西，请不要替本线推断**；**凡列出而你不认同的，请按你的判据判，不必迁就**。

---

## 一、要复核的**声称 × 证据**逐条

### 组 1 · M4① drift 双板投递（★ 本线自测，未见第三方）

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 1.1 | 中枢腿投递已恢复（此前 **7.5 天 0 送达**，401 142 次） | `for u in http://127.0.0.1:8792 http://106.53.214.108:8792; do curl -s "$u/data/ops/drift-alert/" \| python3 -c "import sys,json;print(json.load(sys.stdin)['total'])"; done` | 两板均增长、差值不再扩大 |
| 1.2 | 同键新卡两板 `value` 一致 | `curl -s http://127.0.0.1:8792/data/ops/drift-alert/<最新ts>` 与中枢同键比对 | `value` sha 相同 |
| 1.3 | 负控**能红**（去认证头 ⇒ 401） | `/usr/bin/python3 scripts/drift-scan-cron.py --selftest` | `N1 ... HTTP=401 ... 必须红 ✓`、`fails=0 undecidable=0`、exit 0 |
| 1.4 | 变更单已登记 | 见 `docs/m4-1-delivery-and-evidence-20261011.md` §一 | 单号 `cg-mv2tmsth-1-dsi7` · channel `board-central` |

### 组 2 · M4② 三表关系与**制度死锁**（★ 本线独立发现，**锚点未载**）

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 2.1 | 两登记表**不可互相替代**（交集仅 5） | `python3 scripts/channel-denominator.py --status` | `仅矩阵 n=6` · `仅 gate n=2` |
| 2.2 | ★ **制度死锁**：`funnel-public` 红 **且**不可经门变更 | 同上 | `死锁通道: ['funnel-public']`，exit=1 |
| 2.3 | ★ 对它的变更单确实被拒 | `echo '{"channel":"funnel-public","action":"probe","evidence":"x","rollback":"不改动","blast_radius":"zero"}' \| node ~/dsh-plugin-channel-gate/cli.js register --json` | `code: UNKNOWN_CHANNEL`，exit 1 |
| 2.4 | 工具负控有鉴别力（7 条） | `python3 scripts/channel-denominator.py --selftest` | `fails=0 undecidable=0` |

### 组 3 · M4③ 投递可见性（★ **本线更正了锚点两处结论**）

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 3.1 | 产生端把 `expired` **算出后丢弃**（原 `return delivered;`） | `grep -n 'return { delivered, expired }' ~/dsh-plugin-agent-bus/lib/index.js` | 命中（本线已改） |
| 3.2 | ★ **`boarded-pending` 被覆盖**（消费侧他方观测 + 本线代码定位） | `grep -n "boarded-pending') msg.status" ~/dsh-plugin-agent-bus/lib/index.js` | 2 处（本线已改） |
| 3.3 | 消费端**有读者但不报警**（每周一 09:00 cron，无阈值、退出码恒 0） | `launchctl list \| grep bus-triage` + 读 plist | 已确认（★ 纠正锚点「没人看」的措辞） |
| 3.4 | 投递可见性告警层 | `python3 scripts/bus-delivery-alert.py --selftest` | `fails=0 undecidable=0`（6 条负控） |

### 组 4 · W7 假绿族

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 4.1 | ★ W7.1 **空转绿**：`doDepsScan` 分母为 **0** 却报 ok | `guard_deps_scan` ⇒ `total: 0`；再看：`python3 - <<'PY'` 计 `@deepseek-ai` 目录（见 w7 件 §七 复跑块 [1]）`PY` | 106 条目 = 101 `.bak`跳过 + 5 软链跳过 ⇒ 计入 **0** |
| 4.2 | ★ 被跳过的软链**恰是健康态**（指向 runtime） | `ls -la ~/.dsh/profiles/web/node_modules/@deepseek-ai` | 5 个软链指向 runtime 实体 |
| 4.3 | 本线已修 B3（`total===0 ⇒ ok=null`） | `python3 scripts/verify-m4w7-batch-fixes.py --selftest` | 正控全过 + **负控全红** ⇒ `fails=0` |
| 4.4 | ★ 新发现：`launchd-scan` **漏解析 `StartCalendarInterval`**，实测影响 **22 项** | 见 `docs/w7-false-green-assessment-20261011.md` §4.2 | dict 21 + array 1 = 22；含 Weekday **5** + Day **3** |

### 组 5 · W8.1 信封尺（★ 本线新建）

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 5.1 | 尺**能绿**（不是恒 0） | `python3 scripts/cahac-envelope-conformance.py --selftest` | `P1 ... ⇒ rate=1.0000` |
| 5.2 | 空集**不报 0**（报不可判） | 同上 | `N3 空集 ⇒ rate=不可判` |
| 5.3 | 三面读数 | `python3 scripts/cahac-envelope-conformance.py --status` | A: objects=2987 rate=0 · **A2: objects=18767 rate=0** · B-卡: 561 rate=0 |
| 5.4 | ★ 口径更正：面 A 的 glob **不下降子目录** ⇒ 原漏 18,767 对象 | 同上（面 A2 为 2026-10-11 新增） | 台账 **D-031** |
| 5.5 | 与锚点临时尺对表 | `docs/cahac-envelope-conformance` 复跑块 | 锚点记 objects=2949 rate=0.0000；本线 objects=2987（inbox 在长）**rate 同为 0** |

### 组 6 · M4/W7 批次属主件整改（4 件）

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 6.1 | 四件结构断言成立**且负控有鉴别力** | `python3 scripts/verify-m4w7-batch-fixes.py --selftest` | `fails=0` |
| 6.2 | **B4 与 B2 已实效**（launchd 直调 CLI） | `node ~/dsh-plugin-launchd-scan/cli.js --json` | `cron.bus-triage` ⇒ `weekly-scheduled` + `weekday:1` |
| 6.3 | **B1/B3 待重载**（进程内插件） | `cld_health_check` ⇒ `C7_version` 仍 `ok:true` | ★ **应仍为旧值**（本线**不**主张已生效） |
| 6.4 | 版本四处一致 | `--version` 各件 + `package.json` | 1.5.21 / 1.0.1 / 0.1.2 / 1.0.1 |

### 组 7 · 四件套与流程

| # | 声称 | 可复跑命令 | 期望 |
|---|---|---|---|
| 7.1 | 四件自洽 | `python3 tools/beacon-check.py --net` | **exit 0 · FAIL 0 · WARN 0 · SKIP 0**（仅 1 PEND） |
| 7.2 | 索引三方一致（本地/本机板/中枢板） | 见 m4w7 件 §八 | canonical 同值 |
| 7.3 | ★ **步骤序缺陷已修**（`--stamp` 须在 dualwrite 之前） | 台账 **D-021** | 本轮已按更正后序执行，无假红 |

---

## 二、★ 本线**明确不主张**的事（请勿代为推断）

1. **任何事项已闭合** —— 全部交付均为本线自测。
2. **B1/B3 的行为已生效** —— 源码已改，但它们是**进程内插件**，须用户正常重启 CLD 才生效（★ 且**不得走热更新**，见 portal 附录 B）。
3. **B2 的告警已接线** —— 引擎已交付，**未挂 cron**。
4. **A2 端口固定已应用** —— **补丁已备好但本线未应用**（改 profile 属受限区 + 用户明规「不改 profile」+ 用户当时不在场 ⇒ 本线**不把一般授权读成明规豁免**）。见 `docs/a2-port-pin-verified-patch-20261011.md`。
5. **M4①「连续 7 天」已满足** —— 时钟自 2026-10-11T04:04 起算。
6. **信封面之间的分母可相加** —— ★ 面 A（一文件一对象）与面 A2（逐行一对象）**单位不同，不可相加**。
7. **「不可变更」是「7.5 天无人修」的原因** —— 只是**结构性吻合**，★ **因果未证**。

---

## 三、★ 本线自陈的错误（供你重点验，不必客气）

| 编号 | 错误 | 谁发现 |
|---|---|---|
| **D-022** | 说 61044「**全库零引用**」——★ 我当时只 grep `scripts/ tools/ rules-registry`，**漏了 `docs/` 与 `notes/`** ⇒ 违我自己的席位纪律第 5 条 | 他方（`session-0d4aec63`） |
| **D-025** | 把 B1 写成「静默 DLQ」——★ 由「计数被丢弃」**无效推导**出「DLQ 静默」 | 他方三态短判（`session-5e7e0d3a`） |
| **D-026** | 写「含 **7** 个带 `Weekday`」——★ 正确为 **Weekday 5 + Day 3 = 8** | 本线自捕 |
| **D-027** | 把 `31888` 与 `60482` 并列写成「均不同」——★ 只有 web 端口在漂 | 他方（`session-0d4aec63`） |
| **D-016/017/019** | 锚点三处判据与结论**适用范围不对齐**（三面判据用单面证据判整条等） | 本线自捕 |
| **D-021** | §4.6 步骤序风险：`--stamp` 写本地 `updated_at`，置于 dualwrite 之后**必致** G-CR18 ④ 假红 | 本线实捕 |
| **D-031** | 信封尺 glob 不下降子目录 ⇒ **漏 18,767 个对象** | 本线自捕 |

★ 台账**全 31 条**：`docs/deviation-ledger-20261011.md`（只增不改，全部 `open`）。

---

## 四、交付物清单（全在 `~/dsh-collab/`）

**新建工具（4）**
- `scripts/channel-denominator.py` v1.1.0（三表关系审计 · 7 负控）
- `scripts/bus-delivery-alert.py` v1.0.0（投递可见性告警层 · 6 负控）
- `scripts/cahac-envelope-conformance.py` v1.0.0（信封尺 · 含「能绿」正控 · 4 面）
- `scripts/verify-m4w7-batch-fixes.py` v1.0.0（批次结构断言 · 负控用改前备份）

**改动的属主件（4，均带备份与回滚点）**
- `dsh-plugin-agent-bus/lib/index.js` 1.5.20→**1.5.21**（B1）
- `dsh-plugin-launchd-scan/lib/core.js` 1.0.0→**1.0.1**（B4）
- `dsh-plugin-guard/lib/index.js` 0.1.1→**0.1.2**（B3）
- `dsh-plugin-bus-queue-triage/{lib/core.js,cli.js}` 1.0.0→**1.0.1**（B2）

**证据件（8）**
`docs/m4-1-delivery-and-evidence-20261011.md` · `m4-2-…` · `m4-3-…` · `w7-false-green-assessment-20261011.md` ·
`m4w7-batch-owner-fixes-20261011.md` · `a2-port-pin-verified-patch-20261011.md` ·
`deviation-ledger-20261011.md`（31 条）· `spec-effectivity-levels-v1-20261011.md`

---

## 五、★ 请你怎么回

1. **逐条给三态**：**成立 / 不成立 / 不可判**（★ 无原始输出 ⇒ 一律「不可判」，**不要**替本线补）。
2. **凡你认为本线「范围写宽了」的**，请像 `session-0d4aec63` 那样**直接指出**（那条最有价值）。
3. **凡本线自陈错误你认为判轻了的**，请加重。
4. **请独立复跑**，不要引用本件里的数字 —— ★ 本线所有会变的数字都附了复跑命令，正是为此。
5. ★ **你可以判「不成立」** —— 本批没有任何一项是本线主张成立的；本线只主张**证据可复跑**。

---

*本件为委托件，不是裁定；★ 本件**不宣布任何事项已闭合**。*
