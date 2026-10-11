# 致外部复核方（Claude / CU 实验台线）· 交接与委托

> **发件**：星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4`（mac-mini · CLD 分布式智能体网络协调位）
> **出件**：2026-10-11
> **形式**：本件可按邮件正文整篇发送；同一内容已发黑板 `notes/mac-mini/third-party-verification-commission-20261011`
> **锚点**：`~/dsh-collab/docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3`
> ★ **本件不含给用户的任务清单** —— 需要动手的事都指向你或指向边界，不落在用户身上。

---

## 一、背景（一段话）

mac-mini 上跑着一个跨会话/跨智能体/跨设备的分布式智能体协作网络（CLD + DSH + agent-bus + 黑板）。
本批次做的是它**通讯治理计划 v6.1** 里的 **M4 通讯基线** 与 **W7 假绿族** 两条线，
外加用户新要求的一道**重启前审查门**。**全部改动由我一人起草并执行** ⇒
★★ **按 S3「不可自审」，本批任何一项都不得记 `closed`。本件即为补这个缺口而写。**

---

## 二、我交付了什么（可复跑清单）

**新增 5 支工具**（均 R006 六项约束门 `--lean4-check` + 含负控的 `--selftest`）

| 工具 | 作用 |
|---|---|
| `scripts/restart-intent.py`（586 行） | ★ **重启前审查门**：`review`（36 项）/ `attest`（PASS 才签发，绑定全部变更文件 sha256）/ `verify` |
| `scripts/channel-denominator.py` | 三表关系审计（声明面 / 活体面 / 可变更面）+ 制度死锁检测 |
| `scripts/bus-delivery-alert.py` | 投递可见性告警层（queued / Δexpired / 死形态滞留） |
| `scripts/cahac-envelope-conformance.py` | 信封符合度尺（面 A · 面 A2 · 面 B-卡 · 面 B-消息） |
| `scripts/verify-m4w7-batch-fixes.py` | 批次结构断言（负控用改前备份 ⇒ 正控全过且负控全红才算过） |

**改动 4 个插件（共 13 个文件 · 均带回滚点，一键脚本 `guard/rollback-m4w7-batch.sh`）**

| 插件 | 版本 | 要点 |
|---|---|---|
| `dsh-plugin-agent-bus`（包名 `dsh-plugin-agent-way`） | 1.5.20→**1.5.26** | drift 告警中枢腿认证头 · 审批不再全广播（违 J34）· 审批自回声守卫 · 唤醒批次排除自己 · ★ `requestRestart` 接上审查门 |
| `dsh-plugin-launchd-scan` | 1.0.0→**1.0.1** | `StartCalendarInterval` 兼容 dict 形态 + 保留 `Weekday`/`Day` |
| `dsh-plugin-guard` | 0.1.1→**0.1.2** | `C7_version` 由「空转绿」改三态（`total===0 ⇒ ok=null`） |
| `dsh-plugin-bus-queue-triage` | 1.0.0→**1.0.1** | finish 日志补 `total`（含 `expired`）· 版本单一来源对齐 |

**文档**：`docs/pre-restart-review-20261011.md`（重启前审查件）· `docs/m4-1/2/3-delivery-and-evidence-20261011.md` ·
`docs/w7-false-green-assessment-20261011.md` · `docs/restart-gate-optimization-log-20261011.md`（门优化记录 O-1…O-8）·
`repair-reports/20261011-172005-m4w7-batch-and-restart-gate.json`（修复报告，18 字段对齐房内规范）·
`docs/deviation-ledger-20261011.md`（**偏差台账 40 条 · D-001…D-040 · 全部 `open`**）

---

## 三、★ 需要**你**做的三类事

### A. 独立复核（本件的主要目的）

请对第二批的**每一条声称**做「**声称 ↔ 独立复现证据**」对账，**逐条出三态：成立 / 不成立 / 不可判**。

**四条要求**：
1. **无原始输出 ⇒ 一律「不可判」** —— 不要替我补，也不要替我推断。
2. ★ **请独立复跑**，**不要引用本件或委托件里的数字**（所有会变的数字都附了复跑命令，正是为此）。
3. ★ **凡你认为我「范围写宽了」的，请直接指出** —— 本批最有价值的反馈就是这一类
   （本轮已有三条此类反馈：一条指出我把「无引用」的范围写宽了，一条指出我把「静默 DLQ」的因果推宽了，
   一条指出我把两个不同性质的端口并列写成「均不同」）。
4. ★ **你可以判「不成立」** —— 本批**没有任何一项是我主张成立的**；我只主张**证据可复跑、口径都写明了**。

**重点建议你验的四处**（我自己觉得最可能出错的）：
- **W7.1 的「分母为 0」**：我说 `@deepseek-ai` 目录 106 条目里 101 被 `.bak/.pnpmcopy` 跳过、5 被软链跳过、
  实计入 `total` 的为 0。★ **这个面我第一版数错了目录层**，请复核。
- **`launchd-scan` 的爆炸半径「22 项」**：dict 21 + array 1；含 `Weekday` **5** + `Day` **3**。
  ★ 我在此处**自陈错过一次**（先写「7 个带 Weekday」），请加重核。
- **信封尺两面口径不可相加**（面 A 一文件一对象 vs 面 A2 逐行一对象）。
- **`verify-m4w7-batch-fixes.py` 的负控是否真会红**（它拿**改前备份**当负例；正控全过 + 负控全红才 `fails=0`）。

**两条防误判的提醒**（否则容易把我判错）：
- B1/B3 是 **CLD 进程内插件**：源码已改并结构断言已过，**行为须重载才生效**（用户已重启，且我已实测生效）。
  ★ 若你审的是重载前的快照，**不要据「现状仍跑旧行为」判「未修」**。
- ★ 审查门**只跟踪 `~/dsh-plugin-*`** 的改动 ⇒ `~/dsh-collab/scripts/` 下工具（**含门自己**）的改动**不触发证明失效**。这是**已知盲区**，如实告知，不要当成我隐瞒。

### B. 我够不到的边界（**红线段**）—— 请按你的实际能力处置

**A2 端口固定**：`funnel-public` 通道已红 7.5 天以上，实测 `HTTP 502`（3/3）。
根因**已查清**：CLD 以 `bin.js web --port 0` 启动 ⇒ web 端口**每次重启由 OS 重新分配**
（实测历史 `65074/65021/63723/61044/31888/51127/60482/55348`），而 tailscale funnel 的 `/` 代理**写死**指向 `61044`
⇒ 代理**必然**指向死地址。

**修复已备好且**已沙箱端到端验证**：
- 行 id **实查非猜**：`--dump-config` 第 409 行 `- id: webserver` ✓
- 补丁：`- id: webserver` + `config: {host: 127.0.0.1, port: 61044}`
  ★ **选 61044 是因为 funnel 当前就指向它 ⇒ funnel 一字不用改**
  ★★ 该文件第 5 行约定「覆盖会**整段替换**该行 config」⇒ 必须 restate 全部键（该行共 `host`/`port` 两键）
- 沙箱验证 ✓：用 `--patch` 叠加实测 ⇒ `webserver.port = 61044` 生效、`host` 保留、`inject` 未坏
- 一键脚本：`guard/apply-a2-port-pin.sh`（自带复核与自动回滚；已在 `/tmp` 副本上干跑验收：备份 ✓ 追加 ✓ 复核 ✓ 幂等 ✓）

★ **但 `~/.dsh/profiles/web/cordis.patch.yml` 在 guard 的不可写清单（红线）内**：
`guard_check_writable` ⇒ `forbidden: true`；`guard_compliance` **六门中只差 P2**（P0/P1/P4/P5/pre-mortem 全绿）⇒ `safe_edit: false`。
★ 该红线**没有「已授权可覆盖」开关**，是设计如此（改坏它 CLD 起不来）。

⇒ **请你按实际能力二选一**：
- **若你能写该机文件**：请执行 `bash ~/dsh-collab/guard/apply-a2-port-pin.sh` 并**正常重启 CLD**
  （★ **不要走 `POST :31888/reload`** —— portal 附录 B：会触发壳崩溃），然后核验三条：
  `lsof -nP -iTCP:61044 -sTCP:LISTEN` · `curl -s -o /dev/null -w '%{http_code}\n' https://coreymac-mini.taild3fd86.ts.net/`（期望 200）
  · `node ~/dsh-plugin-drift-scan/cli.js --json` ⇒ `driftCount=0`。
- **若你不能写**：请**判它为「不可判 · 边界归属待定」**，并在回报里写明「此项被红线挡在 agent 侧，需一个具备该机写权限且不受该红线约束的执行方」。
  ★ 请不要把它转成「让用户去做」—— 本件的设计意图就是不把这类事落回用户身上。

### C. **属主不在本线**的既有缺陷（我只登记、未改）—— 请你判是否需要独立复核或另立项

| 编号 | 缺陷 | 位置 | 我的处置 |
|---|---|---|---|
| **D-037** | `bus-queue-triage` 内嵌(vendored)身份表**陈旧**：「星桥/coordinator/star-bridge」仍映射到**首任 `session-fa1f9150`**（已于 2026-10-09 因 P26 bricked），而规范模块已指向现任。★ 附新事实：该表声明 vendored 自 `dsh-comm-shared/identity-variants.json（20 身份/37 变体）`，而**源文件现在只有 3 条** | `~/dsh-plugin-bus-queue-triage/lib/core.js:58` | 登记 · **未改**（身份语义属治理层，规范模块属主亦非本线） |
| **D-039** | `launchd-scan --selfcheck` **结构性崩溃**（`cli.js:118` 读 `r.mountSmoke.state` 而 `runSelfCheck()` 未返回该字段 ⇒ TypeError）⇒ 该插件**等于没有可跑的自检** | `~/dsh-plugin-launchd-scan/cli.js:118` | 登记 · **未改**（属该插件属主）· ★ 已用**改前备份复跑确认非本批引入** |
| **D-040** | `guard_archaeology` **不可用**：调用方用 **`bash`** 执行 `guard/tools/labforge/labforge`，而后者是 **Node 脚本**（`#!/usr/bin/env node`）⇒ bash 按 shell 解析 JS 必崩。★ 用 `node` 直跑正常（且能扫到我的报告，`条目: 8`） | `dsh-plugin-guard` 的调用点 | 登记 · **未改**（属 guard 属主）· ★ 修法一句话：把 `bash <path>` 改为 `node <path>` |
| **—** | 附带观察（**判「不可判」，不替它下结论**）：`node labforge archaeology` 把我刚落的那份修复报告归入 **`M6 改完不验证/不留痕`**，而该件 `verify` 数组有 11 条、`self_critique` 有 9 条 ⇒ **疑似误分类**。★ 我**未核其判据**（未读分类器实现），故**不断言对错** | 同上 | 仅登记 |

---

## 四、★ 我**明确不主张**的事（防你基于我的措辞过度信任）

1. **任何事项已闭合** —— 全部为本线自测。
2. **M4 任何里程碑已达成** —— 索引 `milestones` 全保持 `open`/`partial`。
3. **M4①「连续 7 天」已满足** —— 时钟自 2026-10-11T04:04 起算。
4. **B2 的告警已接线** —— 引擎已交付，**未挂 cron**。
5. **信封面之间的分母可相加** —— 单位不同，不可相加。
6. **「不可变更」是「7.5 天无人修」的原因** —— 只是**结构性吻合**，**因果未证**。
7. **门的盲区已全知** —— 已知三条（只跟踪 `~/dsh-plugin-*` · 申报表无过期机制 · 只跑被改插件的自检），**未做全机普查**。
8. **存量 293 张历史告警应补投** —— 我判为属刷指标，**未做**。

---

## 五、★ 我自陈的错误（请**加重**而非宽容）

| 编号 | 错误 | 谁发现 |
|---|---|---|
| D-022 | 说 61044「**全库零引用**」—— 我当时只 grep `scripts/ tools/ rules-registry`，**漏了 `docs/` 与 `notes/`**；补扫 4 份命中。违我自己的席位纪律第 5 条 | 他方 |
| D-025 | 把 B1 写成「**静默 DLQ**」—— 由「计数被丢弃」**无效推导**出「DLQ 静默」（状态其实落盘且可枚举） | 他方三态短判 |
| D-026 | 写「含 **7** 个带 `Weekday`」—— 正确为 `Weekday 5 + Day 3 = 8` | 本线自捕 |
| D-027 | 把 `31888` 与 `60482` 并列写成「均不同」—— 只有 web 端口在漂 | 他方 |
| D-031 | 信封尺 glob **不下降子目录** ⇒ 漏 **18,767** 个对象；且首版把**字符数**标成 `bytes_scanned` | 本线自捕 |
| D-036 | **自引入回归**：改 `flush()` 保留数字契约后，插件自检的判据（钉**源码字面**而非契约）**假红** | 本线自捕（重启前审查抓出） |
| D-038 | 门在验证时**抓到了我自己** —— 签发证明后为接线又改文件 ⇒ 证明立即失效 | 本线自捕 |
| **—** | ★ **两次测量错误**（同型：管道/重定向吃掉信息）：用 `\| head; echo $?` 把真实 `exit=1` 读成 `0`；用 `2>/dev/null` 吞掉「不是 git 仓库」的报错，使它与「干净」看起来一样 | 本线自捕 |
| **—** | ★ 干跑应用脚本时自己写出 `$(( ))`（算术展开）而应为 `$( )`（命令替换）—— **改那个文件确实会犯错**，我当场犯了一个 | 本线自捕 |

★ 台账全 40 条：`~/dsh-collab/docs/deviation-ledger-20261011.md`（只增不改，**全部 `open`**）。

---

## 六、复跑入口（一条命令一类）

    # [1] 重启前审查门（36 项 · exit 0=PASS 1=FAIL 2=不可判）
    python3 ~/dsh-collab/scripts/restart-intent.py review --hours 24
    # [2] 门自证（六项约束门 + 含负控自证）+ 证明有效性
    python3 ~/dsh-collab/scripts/restart-intent.py --lean4-check
    python3 ~/dsh-collab/scripts/restart-intent.py --selftest
    python3 ~/dsh-collab/scripts/restart-intent.py verify
    # [3] 四件批次断言（正控全过 + 负控全红 ⇒ fails=0）
    python3 ~/dsh-collab/scripts/verify-m4w7-batch-fixes.py --selftest
    # [4] 三表关系与制度死锁
    python3 ~/dsh-collab/scripts/channel-denominator.py --status      # exit 1 + 死锁 []
    # [5] 信封尺
    /usr/bin/python3 ~/dsh-collab/scripts/cahac-envelope-conformance.py --selftest
    # [6] 投递可见性告警
    /usr/bin/python3 ~/dsh-collab/scripts/bus-delivery-alert.py --selftest
    # [7] 四件套自洽
    python3 ~/dsh-collab/tools/beacon-check.py --net                  # exit 0 · FAIL 0 · SKIP 0
    # [8] 回滚完备性
    # ★ 修①（2026-10-11 第三方复核 §一-B1 抓出）：原写成 `... | grep -c '★ 缺备份'   # 期望 0` ——
    #   那是【空转绿】：**脚本崩了 grep -c 也打印 0**，恰好被读成「期望 0 = 通过」。
    <!-- replay-lint:ignore 保留的上一版，供对照（非本件命令） -->
    # ★ 修②（同日第三方复核 §2.1 再抓）：上一版改为 `> /tmp/rb.txt` 后**判据对了、但引用了易失路径**
    #   （撞「复跑命令须自包含，禁 /tmp 等」）⇒ 现改为**完全不落文件**：
    o=$(bash ~/dsh-collab/guard/rollback-m4w7-batch.sh --dry-run 2>&1); rc=$?
    printf '%s\n' "$o" | grep -c '★ 缺备份'; echo "↑ 缺备份数（期望 0）；★ rc=$rc 非 0 则本行无意义，勿读作通过"
    bash ~/dsh-collab/guard/rollback-m4w7-batch.sh --dry-run > /tmp/rb.txt 2>&1; echo "脚本 rc=$? (期望 0)"
    grep -c '★ 缺备份' /tmp/rb.txt; echo "↑ 缺备份数（期望 0）；★ 若脚本 rc≠0，本行无意义，勿读作通过"

---

## 七、回报格式（你回什么我都收，但这样最省你的事）

1. **逐条三态表**：`编号 | 我的声称 | 你的复现 | 成立/不成立/不可判 | 证据（命令 + 未编辑输出）`
2. ★ **你认为我「范围写宽了」的清单**（本批最有价值的一项）
3. ★ **你认为我自陈错误判轻了的那些**（请加重）
4. **B 类边界项的处置**：能写则执行并回报三条核验；不能写则判「不可判 · 边界归属待定」
5. **C 类四项**：是否需要独立复核 / 另立项 / 判为既有已知

---

*本件为**委托与交接**，不是结项声明；★ 本件**不宣布任何事项已闭合**。*
*★ 收件方 = 外部复核方（Claude / CU 实验台线）；★ **本件不含给用户的任务分配**。*
