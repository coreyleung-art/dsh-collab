# M4/W7 批次 · 第三方复核结果（外部第三方 · CU 实验台线）

> **复核方**：外部第三方 Claude Code 会话 · 角色键 `ext` · session `005a2c58-7439-4ad5-bebf-815b29c2ca4a`
> **被复核件**：`docs/third-party-verification-commission-20261011.md`（转引自 `notes/mac-mini/third-party-verification-commission-20261011`）
> **复核时刻**：**2026-10-11 17:04–17:12 CST**（★ 实际用时约 8 分钟；每条命令的执行时刻散见各条）
> **立场**：只读 · 对抗性（默认怀疑）· 三态 · 报「0 条」附扫过的面
> ★ **本件是复核结果，不是裁定**；★ 我不改任何被审文本、不动任何被审文件（唯一写入物 = 本文件）。

---

## 〇、只读声明与被审件锚定

### 0.1 我做了什么、没做什么

| 类别 | 内容 |
|---|---|
| **做了** | 逐条**独立复跑**本件开列的复跑命令（不引用本件数字）；必要时**另写独立枚举**（不调用被审方的判定函数）复核同一事实；对四件属主件做 `grep/结构读源`；对黑板做只读 GET；对 launchd plist 做 `plutil` 只读解析 |
| **没做** | ✗ 未重启 CLD ✗ 未热更新 ✗ 未改 profile 任何行 ✗ 未改插件目录任何源码/配置 ✗ 未跑 `pnpm/npm/yarn install` ✗ 未跑 `guard --selfcheck`（含真挂载冒烟）✗ 未执行 `guard/rescue-unmount-context-survival.sh`（无 dry-run）✗ 未发 xdom 信 |
| **写了什么** | 只写本文件。★ 另外，`scripts/*.py --selftest` 一类**被审方自带的自测**（`drift-scan-cron` / `channel-denominator` / `bus-delivery-alert` / `cahac-envelope-conformance` / `verify-m4w7-batch-fixes`）经复跑；其中 `drift-scan-cron --selftest` 按其自身说明「不触发真实巡检」，但会**在板上建探针并自行清理**（其输出 N4 行自证已清理） |

### 0.2 被审件的指纹锚定（★ 我自行测得，非引用本件）

★ 本件只给了**锚点**的 sha256，未给四件属主件与四支工具的 sha。我逐一实测（`shasum -a 256 | cut -c1-16`）：

| 件 | sha256_16（2026-10-11 17:2x 实测） | 体量 | 源码 mtime |
|---|---|---|---|
| 锚点 `docs/distributed-agent-network-governance-plan-v6.1-20261011.md` | `bf5a4e6b76fdedeb` | 252,738 B | 2026-10-11 03:48:35 |
| 属主件 B1 `~/dsh-plugin-agent-bus/lib/index.js` | `ee255df4bb3de2cb` | 113,252 B | **2026-10-11 16:38:54** |
| 属主件 B4 `~/dsh-plugin-launchd-scan/lib/core.js` | `18935109c6400201` | 6,870 B | 2026-10-11 04:38:29 |
| 属主件 B3 `~/dsh-plugin-guard/lib/index.js` | `79d6979fa38670f7` | 38,800 B | 2026-10-11 04:39:24 |
| 属主件 B2 `~/dsh-plugin-bus-queue-triage/cli.js` | `e825511e8a3687e7` | 7,749 B | 2026-10-11 04:39:49 |
| 属主件 B2 `~/dsh-plugin-bus-queue-triage/lib/core.js` | `7df4f81423181296` | 15,869 B | 2026-10-11 04:40:21 |

★ **锚点 sha256 全域值与本件所载逐字符相同**：
`bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3` ⇒ **本件的锚点引用成立**。

### 0.3 ★★ 一个必须先说的时点事实：**被审树在本件写就后仍在移动**

    $ date '+%Y-%m-%d %H:%M:%S %Z'
    2026-10-11 17:04:53 CST

    $ stat -f '%Sm  %z  %N' -t '%Y-%m-%d %H:%M:%S' ~/dsh-plugin-agent-bus/lib/index.js ~/dsh-plugin-agent-bus/package.json
    2026-10-11 16:38:54  113252  /Users/coreyleung/dsh-plugin-agent-bus/lib/index.js
    2026-10-11 16:38:54  1779    /Users/coreyleung/dsh-plugin-agent-bus/package.json

    $ git -C ~/dsh-plugin-agent-bus status --porcelain
     M lib/index.js
     M lib/selfcheck.js
     M package.json

    $ ls -la ~/dsh-collab/guard/backups/ | grep gitHEAD
    -rw-r--r--  1 coreyleung  staff   23407 10月 11 17:07 dsh-plugin-agent-bus__lib_selfcheck.js.bak-good-2026-10-11-gitHEAD
    -rw-r--r--  1 coreyleung  staff    1779 10月 11 17:07 dsh-plugin-agent-bus__package.json.bak-good-2026-10-11-gitHEAD

⇒ 逐条影响：**1.5.21 → 1.5.24**（版本）、`lib/index.js` 于 **16:38:54** 被再次改动、**17:07**（我做本轮复核期间）又见新的 `…gitHEAD` 备份落盘。
⇒ 我的三态一律以 **§0.2 所列 sha 为准**；凡「**现在**是这样」的判定，均带该指纹。

---

## 一、逐条三态（判据 = 命令 + 未编辑输出）

★ 每条格式：**声称** / **我的判据（命令）** / **未编辑输出** / **三态** / **备注**。
★ 三态定义：**成立** = 我独立复现且与本件声称一致；**不成立** = 我独立测得与声称不符；**不可判** = 我无法取得该面证据（**不替你补、不替你推断**）。

---

### 组 1 · M4① drift 双板投递

#### 1.1 中枢腿投递已恢复（此前 7.5 天 0 送达，401 142 次）

判据（本件给）+ 我另加逐日分布：

    $ for u in http://127.0.0.1:8792 http://106.53.214.108:8792; do \
        curl -s --max-time 30 "$u/data/ops/drift-alert/" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['total'])"; done
    339
    46

    （独立复算 · 逐日键分布 · 未编辑）
    日期               本机板     中枢板   中枢/本机
    2026-10-03        26      19
    2026-10-04        14       0
    2026-10-05        21       0
    2026-10-06        48       0
    2026-10-07        47       0
    2026-10-08        48       0
    2026-10-09        48       0
    2026-10-10        52       0
    2026-10-11        35      27
    本机板合计 339  中枢板合计 46
    中枢独有键数: 0
    本机板独有键数(未送达中枢): 293
    未送达中枢的键的 ts 分布: Counter({'2026-10-10': 52, '2026-10-06': 48, '2026-10-08': 48, '2026-10-09': 48, '2026-10-07': 47, '2026-10-05': 21, '2026-10-04': 14, '2026-10-11': 8, '2026-10-03': 7})
    未送达中枢的**最晚** ts: 2026-10-11T03:47:25
    中枢板最早/最晚键 ts: 2026-10-03T13:27:29 / 2026-10-11T16:51:36

「401 142 次」的独立复跑（本件把它藏在 m4-1 件里）：

    $ ls -la /tmp/drift-scan-cron.err.log
    -rw-r--r--  1 coreyleung  wheel  212172 10月 11 03:47 /tmp/drift-scan-cron.err.log
    $ grep -c '401' /tmp/drift-scan-cron.err.log
    142
    $ tail -1 /tmp/drift-scan-cron.err.log
    urllib.error.HTTPError: HTTP Error 401: Unauthorized

**三态：成立。**
- 「7.5 天 0 送达」逐日核到：10-04…10-10 **中枢板 7 天全 0**，10-03 最后一次送达 13:27 → 10-11 约 03:5x 恢复，跨 **7.6 天** ✓。
- 「已恢复」：10-11 中枢板 27 张；**未送达键的最晚 ts = 03:47:25** ⇒ 该时刻之后的本机板键**全部已送达** ⇒ 「差值不再扩大」亦成立。
- 「401 142 次」实测 **142** ✓。

★ **但「142」的复跑命令引用 `/tmp/drift-scan-cron.err.log`（易失路径）** ⇒ 违**锚点自订**的 §5.3 第 5 项「自包含复跑命令（**禁引用 /tmp 等易失路径**）」。今日尚在，明日未必（见 §三 之 (d)）。

#### 1.2 同键新卡两板 `value` 一致

    $ （取本机板最新 3 键，逐键双板读，对 value 子树取 canonical sha256_16）
    ── 键 data/ops/drift-alert/1791705077035 ──
       127.0.0.1:8792        ts=2026-10-11T15:51:17  ver=1 value_sha16=54bad9d13b08a396
       106.53.214.108:8792   ts=2026-10-11T15:51:17  ver=1 value_sha16=54bad9d13b08a396
    ── 键 data/ops/drift-alert/1791706885677 ──
       127.0.0.1:8792        ts=2026-10-11T16:21:25  ver=1 value_sha16=2605aa97efa72114
       106.53.214.108:8792   ts=2026-10-11T16:21:26  ver=1 value_sha16=2605aa97efa72114
    ── 键 data/ops/drift-alert/1791708695420 ──
       127.0.0.1:8792        ts=2026-10-11T16:51:35  ver=1 value_sha16=b4d34e3f8d05dfa2
       106.53.214.108:8792   ts=2026-10-11T16:51:36  ver=1 value_sha16=b4d34e3f8d05dfa2

**三态：成立。** 三键 value 双板同 sha；`ts` 差 ≤1s（两板各自落盘时刻，非内容差异）。

#### 1.3 负控能红（去认证头 ⇒ 401）

    $ python3 -I scripts/drift-scan-cron.py --selftest
    == drift-scan-cron --selftest（正控 + 活体负控；不触发真实巡检）==
      OK  P1 认证头按板构造（local=Authorization / central=X-Blackboard-Token）
      OK  P2 负控注入点确实去掉认证头（force_unauth）
      OK  N1 活体负控：去认证头打中枢 ⇒ HTTP=401 (4xx 终态，不重试)（必须红 ✓）
      OK  N2 活体正控：带认证头打中枢并回读 ⇒ HTTP=200 attempts=1
      OK  N3 回读断言：value.selftest == 1
      OK  N4 探针已清理 data/ops/drift-selftest-1791709623807
      => fails=0 undecidable=0 version=1.1.0
    EXIT=0

**三态：成立。** `N1 … HTTP=401 … 必须红 ✓`、`fails=0 undecidable=0`、exit 0 —— 三项逐项对上。

#### 1.4 变更单已登记

    $ grep -n "cg-mv2tmsth-1-dsi7" logs/channel-changes.jsonl
    19:{"id":"cg-mv2tmsth-1-dsi7","at":"2026-10-10T20:02:47.525Z","channel":"board-central","action":"register","evidence":"锚点 v6.1（sha256 bf5a4e6b…）§14.4 M4①c 明文要求：drift-scan-cron.py:87-89 补认证头，通道 = board-central，经 channel_gate 登记变更单。…","rollback":"/Users/coreyleung/dsh-collab/guard/backups/Users__coreyleung__dsh-collab__scripts__drift-scan-cron.py.bak-good-2026-10-10-20-0","blast_radius":"单文件改动…","owner":"rust-blackboard","meltRisk":"ok","dryRun":false}
    （gate 台账总行数：19）

**三态：成立。** 单号、channel、action 逐字对上；且该单在 **gate 自己的台账**里（不是只在叙述里）。

---

### 组 2 · M4② 三表关系与制度死锁

#### 2.1 两登记表不可互相替代（交集仅 5）

    $ python3 -I scripts/channel-denominator.py --status
    == channel-denominator 1.1.0 ==
      判定: DIVERGENT
      分母: 声明(矩阵) n=11 · 活体(drift) n=12 · 可变更(gate) n=7 · 有效并集 n=12
      ── ★ 跨面：可观测性 vs 可变更性（两者不可互相替代）──
      交集 矩阵∩gate n=5 : ['board-central', 'board-local', 'bus-8791', 'sse-8803', 'tailscale-direct']
      ★ 仅矩阵（被监测但【变更不可表达】）n=6 : ['device-daemon', 'e2-registry-services', 'funnel-public', 'hb-fwd', 'node-bridge', 'sync-from-central']
      ★ 仅 gate（可变更但【未被监测】）n=2 : ['launchd-daemons', 'local-agent-bus']
    EXIT=1

**三态：成立。** 「仅矩阵 n=6」「仅 gate n=2」「交集 n=5」三项逐项对上。

#### 2.2 制度死锁：`funnel-public` 红且不可经门变更

（同上一条命令的后续输出）

      ── ★★ 制度死锁（红的 ∧ 不可经门变更）──
      当前为红的通道: ['funnel-public']
      ★ 死锁通道: ['funnel-public']
    EXIT=1

**三态：成立。** 死锁通道恰为 `['funnel-public']`，exit=1。

#### 2.3 对它的变更单确实被拒

    $ echo '{"channel":"funnel-public","action":"probe","evidence":"x","rollback":"不改动","blast_radius":"zero"}' \
        | node ~/dsh-plugin-channel-gate/cli.js register --json
    {"ok":false,"error":"channel 不在冻结枚举: funnel-public。正确姿势：7 个合法通道 local-agent-bus/board-local/board-central/bus-8791/sse-8803/tailscale-direct/launchd-daemons 之一（portal §0 矩阵）","code":"UNKNOWN_CHANNEL"}
    EXIT=1
    （★ 我另证「拒绝即零写」）
    gate 台账行数: 写前=19 写后=19  →  差=0

**三态：成立。** `code: UNKNOWN_CHANNEL`、exit 1 ✓。
★ **我另加的一条**（本件未声称、我自发验的）：被拒的登记**零写盘**（台账 19→19），与源码 `lib/gate.js:41-53`（先 `validateChange` 抛 `UNKNOWN_CHANNEL`）→ `lib/core.js:41-72`（`if (!dryRun) appendLog(rec)`）的次序一致 ⇒ 「不可经门变更」不是「登记了但没生效」，而是**根本登记不上**。这条**加重**了 2.2 的死锁结论。

#### 2.4 工具负控有鉴别力（7 条）

    $ python3 -I scripts/channel-denominator.py --selftest
    == channel-denominator --selftest（正控 + 负控；不写任何东西、不登记任何变更）==
      OK  P1 正控 三面一致 ⇒ MATCH（应为 MATCH）
      OK  N1 负控 声明多一项 ⇒ DIVERGENT declared_only=['ghost']
      OK  N2 负控 活体多一项 ⇒ DIVERGENT live_only=['extra']
      OK  N3 负控 面不可判 ⇒ UNDECIDABLE / UNDECIDABLE（不得冒充通过）
      OK  N4 边界 空集 ⇒ MATCH effective_n=0 ⇒ ★ 须同时看 effective_n>0 才可读作覆盖
      OK  N5 负控 仅矩阵 ⇒ monitored_not_changeable=['mon-only']
      OK  N6 负控 仅 gate ⇒ changeable_not_monitored=['gate-only']
      OK  N7 ★ 负控 红且不可变更 ⇒ deadlock=['bad']（必须红）
      OK  LIVE 活体采集 ⇒ 12 项（scannedAt=2026-10-11T09:07:36.359Z）
      OK  GATE 枚举解析 ⇒ 7 条，全部带 owner：True
      => fails=0 undecidable=0 version=1.1.0
    EXIT=0

**三态：成立（附口径小瑕）。** `fails=0 undecidable=0` ✓。★ **口径**：9 条里带 `N` 标记的是 7 条，但 **N4 是「边界」不是「负控」**（输出行自身标 `N4 边界`）⇒ 严格说 **6 条负控 + 1 条边界**，本件「7 条负控」**略宽**（S3 级）。

---

### 组 3 · M4③ 投递可见性

#### 3.1 产生端把 `expired` 算出后丢弃（原 `return delivered;`）

    $ （对 §0.2 锚定的 16:38:54 版做字面串计数）
    [3.1a] 字面串 'return { delivered, expired }' 命中 1 处
          :1366  return { delivered, expired };
    [3.1b] 字面串 '    return delivered;' 命中 0 处
    文件 mtime/size: 2026-10-11 16:38:54 113252

**三态：成立。** 改后形态在 `:1366` ✓，旧形态在**当前**文件 0 处 ✓；旧形态确实存在于改前备份（见 6.1 负控）。

#### 3.2 `boarded-pending` 被覆盖（2 处）

    [3.2] 字面串 "boarded-pending') msg.status" 命中 2 处
          :1444  if (msg.status !== 'boarded-pending') msg.status = ok ? 'delivered' : 'queued';
          :1508  if (msg.status !== 'boarded-pending') msg.status = ok ? 'delivered' : 'queued';

**三态：成立。** 恰 **2 处**，两行字面完全相同。

#### 3.3 消费端有读者但不报警（每周一 09:00 cron，无阈值、退出码恒 0）

    $ launchctl list | grep bus-triage
    -	0	com.dsh.cron.bus-triage
    $ plutil -convert json -o - ~/Library/LaunchAgents/com.dsh.cron.bus-triage.plist
      Label: com.dsh.cron.bus-triage
      ProgramArguments: ['/opt/homebrew/bin/node', '/Users/coreyleung/dsh-plugin-bus-queue-triage/cli.js', '--scan', '--json']
      StartCalendarInterval: {'Weekday': 1, 'Hour': 9, 'Minute': 0}
      RunAtLoad: False
      StandardOutPath: /Users/coreyleung/dsh-collab/logs/bus-triage-cron.log
    $ tail -3 logs/bus-triage-cron.log
    {"ok":true,"queued":379,"expireable":0,"counts":{…},"total":{"delivered":29476,"expired":2001,"queued":379},"liveIdsKnown":false,"keepDays":7}

**三态：成立（附口径收紧）。**
- 「每周一 09:00」✓（`Weekday:1` = 周一，Hour 9 / Minute 0）；`RunAtLoad: false` ✓。
- 「退出码恒 0」✓ 可核（launchctl 第 2 列 = 上次退出状态 `0`；该 CLI 的 `--scan` 为只读路径）。
- ★ **「有读者」的所指须自足**：我能证的只有「**有位定时消费者**（cron）+ **留了历史**（append 型日志，末条 10-05）」。我**不能**证「有活人看这份输出」。本件原话是「消费端**有读者但不报警**」——若「读者」指「有人看告警」，则**该面不可判**；若指「有消费者在读队列」，则成立。**这一处正是本件对锚点「没人看」的更正，更正的落点必须同样精确**（S3 级，见 §三 之 (g)）。

#### 3.4 投递可见性告警层

    $ python3 -I scripts/bus-delivery-alert.py --selftest
    == bus-delivery-alert --selftest（正控 + 负控；不写状态、不投卡）==
      OK  P1 正控 全在阈值内 ⇒ OK
      OK  N1 负控 queued 积压 ⇒ ALERT ['A']
      OK  N2 负控 expired 成批死亡 ⇒ ALERT Δ=400
      OK  N3 负控 死形态滞留 ⇒ ALERT ['C']
      OK  N4 负控 取数不可用 ⇒ UNDECIDABLE（不得冒充 OK）
      OK  N5 负控 首跑无基线 ⇒ verdict=OK 且 Δ不可判标记=True
      OK  N6 边界 Δexpired=0 ⇒ OK（判据非恒真）
      OK  LIVE 取数（经既有 triage --scan）⇒ queued=7 expireable=0 expired=2378
      => fails=0 undecidable=0 version=1.0.0
    EXIT=0

**三态：成立。** 「6 条负控」——实为 **N1/N2/N3/N4/N5 五条负控 + N6 边界**，同 2.4 的口径小瑕（S3）。

---

### 组 4 · W7 假绿族

#### 4.1 W7.1 空转绿：`doDepsScan` 分母为 0 却报 ok

★ 我**不调用** `guard_deps_scan` 的判定函数，改写**独立枚举**（只看文件系统事实）：

    $ （独立复算 ~/.dsh/profiles/web/node_modules/@deepseek-ai）
    总条目 = 106
      .bak/.pnpmcopy = 101
      符号链接       = 5
      ★计入(其余)    = 0 []
      → doDepsScan 的 total = 0

    $ （源码侧对读）
    289:  // ★ 1.0.2（2026-10-11 星桥第二任 · 用户授权 M4/W7 批次）：早退分支亦须带 `degenerate`
    291:  if (!existsSync(PROFILE_NM)) return { total: 0, mismatches: [], count: 0, degenerate: true };
    295:    if (/\.(bak|pnpmcopy)/.test(name)) continue;
    299:    if (!st.isDirectory() || st.isSymbolicLink()) continue;
    306:  return { total, mismatches, count: mismatches.length, degenerate: total === 0 };
    365:    ok: scan.degenerate ? null : (scan.count === 0),
    366:    degenerate: scan.degenerate,
    371:  if (scan.degenerate) {

**三态：成立。** `106 = 101(.bak/.pnpmcopy) + 5(软链) + 0(计入)` ⇒ `total = 0` ⇒ 原判据 `ok: scan.count === 0` 恒真（假绿）✓，现判据 `degenerate ? null : …` 已改为「不可判」✓。
★ **我的核对面**：文件系统 + 源码。**`guard_deps_scan` 这个 MCP 工具的返回报文我取不到**（本会话无该工具）⇒ **「工具实际返回 `total: 0`」这一面我未核**，但底层计数与源码判据我独立复现，**声明面与我的复算一致**。

#### 4.2 被跳过的软链恰是健康态（指向 runtime）

    $ （5 个软链的 realpath，逐一）
      cordis                 → /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/cordis
      dsh-api-gateway        → /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-api-gateway
      dsh-base               → /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-base
      dsh-client-runtime     → /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-client-runtime
      dsh-web-app            → /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-web-app

**三态：成立。** 5 条全部指向 CLD runtime 实体 ✓（即「被跳过的恰是唯一健康的那些」）。

#### 4.3 本线已修 B3（`total===0 ⇒ ok=null`）

    $ python3 -I scripts/verify-m4w7-batch-fixes.py --selftest
      ── B3 · dsh-plugin-guard/lib/index.js ⇒ PASS ──
         OK  total===0 不再空转绿
         OK  引入不可判（null）语义
      ── ★ 负控：拿改前备份跑同一组断言（必须【红】）──
      OK  B3 负例=Users__coreyleung__dsh-plugin-guard__lib__in ⇒ FAIL（★预期：证明断言有鉴别力）  不成立项=['total===0 不再空转绿']
      => fails=0
    EXIT=0

**三态：成立。**（该脚本**全部 4 件**的负控均 FAIL，见 6.1。★ 但「负控有鉴别力」在**断言粒度**上有折扣，见 6.1 备注。）

#### 4.4 新发现：`launchd-scan` 漏解析 `StartCalendarInterval`，实测影响 22 项

★ 我不调用被审方工具，写**独立枚举**（`plutil -convert json` 逐 plist 只读解析）：

    $ （独立枚举：~/Library/LaunchAgents/com.dsh.*.plist）
    com.dsh.* plist 总数: 80
    含 StartCalendarInterval 的 plist 数: 22
      dict 形态: 21
      array 形态: 1 ['com.dsh.maintenance-restart.plist']
      ★ calendar 条目总数: 31
    含 Weekday 的 plist 数: 5 ['com.dsh.cron.bus-triage.plist', 'com.dsh.cron.channel-gate-weekly.plist', 'com.dsh.cron.competitor-light-scan.plist', 'com.dsh.gate-weekly-audit.plist', 'com.dsh.hr.cahac-replay.weekly.plist']
    含 Day 的 plist 数: 3 ['com.dsh.archive-logs.plist', 'com.dsh.cron.queue-condense.plist', 'com.dsh.maintenance-restart.plist']

**三态：成立。** `22 = dict 21 + array 1` ✓；`Weekday 5 + Day 3` ✓（合计 8，与台账 **D-026 的自我更正**逐字一致 ⇒ **D-026 那条更正本身是对的**）。
★ **口径一句**（S3 级）：这 22 项**不是同一缺陷命中 22 次**——其中 **21 项**是「dict 形态被读成无排程」，**1 项**（array 形态）是「读了但只取 Hour/Minute、丢 Weekday/Day」。**两者性质不同，不宜相加读作一个数**（本件在代码注释里已分列 21/1，故只是**读法**风险，非事实错误）。

---

### 组 5 · W8.1 信封尺

#### 5.1 尺能绿（不是恒 0）

    $ python3 -I scripts/cahac-envelope-conformance.py --selftest
      OK  P1 ★正控 1 条全字段 ⇒ objects=1 envelope_ok=1 rate=1.0000
      OK  N2 边界 h=6（=阈值）⇒ envelope_ok=1（须为 1，证判据是 >=）
      OK  N4 负控 1合规/4对象 ⇒ rate=0.2500（须 0.25）
      => fails=0 version=1.0.0
      ★ P1 是【能绿】的证据：本尺在合规输入上确实会给出 envelope_ok=1，不是恒 0。
    EXIT=0

**三态：成立。** `P1 … ⇒ rate=1.0000` ✓（这是「尺不是恒 0」的关键正控）。

#### 5.2 空集不报 0（报不可判）

    （同上命令）
      OK  N3 ★负控 空集 ⇒ rate=不可判（objects=0） verdict=UNDECIDABLE（不得报 0.0000）

**三态：成立。**

#### 5.3 三面读数（A: 2987 / A2: 18767 / B-卡: 561）

    $ python3 -I scripts/cahac-envelope-conformance.py --status
      ── A · inbox ──        files_on_disk = 2994   parsed_objects = 2988   objects=2988 envelope_ok=0 rate=0.0000
      ── A2 · inbox/bb JSONL ── files_on_disk = 9   parsed_objects = 15518  objects=15518 envelope_ok=0 rate=0.0000
      ── B · 卡 ──           objects_on_board = 564  parsed_objects = 561    objects=561 envelope_ok=0 rate=0.0000
    EXIT=1

    $ （独立复算 bb/*.jsonl 行数）
    coordinator.jsonl 979 · device.jsonl 8309 · hr.jsonl 872 · learning.jsonl 960 · manual-test.jsonl 3 ·
    qa.jsonl 813 · recovery.jsonl 872 · supply.jsonl 871 · xingduo.jsonl 1839   → 合计 = 15518

**三态：A 项成立（差 1，属会变数）· B-卡 成立（561 同值）· ★ A2 项不成立。**
- **A**：声称 2987，实测 **2988**（+1）。inbox 是**在长的面**（本件 5.5 自认「inbox 在长」）⇒ 差 1 属可接受漂移。
- **B-卡**：**561**，逐字同值 ✓。
- **A2**：声称 **18,767**，实测 **15,518**（差 **3,249**，≈ **17%**）⇒ **不成立**（原因见 5.4）。

#### 5.4 口径更正：面 A 的 glob 不下降子目录 ⇒ 原漏 18,767 对象

    $ （源码对读）
     39:INBOX = "~/.dsh/inbox/*"
     95:    files = sorted(glob.glob(os.path.expanduser(pattern)))
    118:      面 A 用 `glob('~/.dsh/inbox/*')` —— ★ **glob 的 `*` 不下降子目录** ⇒
    119:      `~/.dsh/inbox/bb/coordinator.jsonl`（实测 7.2 MB）**根本不在面 A 内**。

    $ （「会变」的直接证据：D-031 自己引的两个数，今天的值）
    coordinator.jsonl   2,584,663 B  (2.46 MB)   ← 台账 D-031 记「实测 7.2 MB」
    hr.jsonl / recovery.jsonl / supply.jsonl  ≈ 3.975 MB（三个近似同尺寸 ⇒ 存在按体量的轮转/压缩）

**三态：★ 结构成立，数字不成立（两态并存，须分开读）。**
- **结构**：「glob `*` 不下降子目录 ⇒ `bb/*.jsonl` 不在面 A 内」✓ **成立**（源码 `:39`/`:95` 逐字 + 面 A 只计顶层 2,994 个文件）。
- **数字**：「漏 18,767」**不成立为可复跑量**：现测 **15,518**；且 D-031 自己引的 `coordinator.jsonl = 7.2 MB` 现已缩到 **2.46 MB** ⇒ **该面是被轮转/压缩的会变面**，D-031 记的是一个**未标时点**的快照。
- ★★ **加重**：D-031 自己的「规则号」一栏写明依 **锚点 §14.1「凡会变的数字附复跑命令」** —— 而它给的是**一个会变的数**却**未附复跑命令**、**未标时点**。这是**本条自订规则被本条自己违反**（同类：台账 D-006「在修订总表里写死了会变的数字」）。

#### 5.5 与锚点临时尺对表（锚点 objects=2949 rate=0.0000；本线 objects=2987 rate 同为 0）

    （--status 实测）A: objects=2988 rate=0.0000 · A2: objects=15518 rate=0.0000 · B-卡: objects=561 rate=0.0000

**三态：成立（就其主张的那个「相同点」而言）。** 本件主张的是 **rate 同为 0**（不是 objects 相等）⇒ 我实测 **rate=0.0000** ✓。objects 2949 / 2987 / 2988 三者互不相同，属**会变数**，本件亦未主张其相等 ✓。

---

### 组 6 · M4/W7 批次属主件整改（4 件）

#### 6.1 四件结构断言成立且负控有鉴别力

    $ python3 -I scripts/verify-m4w7-batch-fixes.py --selftest
      ── B1 · dsh-plugin-agent-bus/lib/index.js ⇒ PASS ──   （8 条全 OK）
      ── B4 · dsh-plugin-launchd-scan/lib/core.js ⇒ PASS ── （3 条全 OK）
      ── B3 · dsh-plugin-guard/lib/index.js ⇒ PASS ──       （2 条全 OK）
      ── B2 · dsh-plugin-bus-queue-triage/cli.js ⇒ PASS ──  （2 条全 OK）
      → 当前文件四件判定：exit=0
      ── ★ 负控：拿改前备份跑同一组断言（必须【红】）──
      OK  B1 … ⇒ FAIL（★预期）  不成立项=['expired 计数不再被丢弃（返回对象）', '旧的 `return delivered;` 已不存在', 'sendMessage 不覆盖 boarded-pending']
      OK  B4 … ⇒ FAIL（★预期）  不成立项=['calendar 解析兼容 dict 形态', '保留 Weekday', '保留 Day（月内某日）']
      OK  B3 … ⇒ FAIL（★预期）  不成立项=['total===0 不再空转绿']
      OK  B2 … ⇒ FAIL（★预期）  不成立项=['finish 日志补全 total（含 expired）—— …']
      => fails=0
    EXIT=0

★ **第四项重点（本件点名要我验「负控是不是真的会红」）—— 我的独立复算：不截断地逐条跑**

    $ （用脚本自身的 run() 对四份改前备份逐条求值，打印全部不成立项）
    B1: 断言 8 条 · 负控变红 8 条 · ★恒真(无鉴别力) 0 条
    B4: 断言 3 条 · 负控变红 3 条 · ★恒真(无鉴别力) 0 条
    B3: 断言 2 条 · 负控变红 1 条 · ★恒真(无鉴别力) 1 条
         ★绿 引入不可判（null）语义  [期望 True 实得 True]
    B2: 断言 2 条 · 负控变红 1 条 · ★恒真(无鉴别力) 1 条
         ★绿 ★ 阈值告警【不】在此重复实现（…）  [期望 False 实得 False]
    合计: 15 条断言 · 负控红 13 · 恒真 2

    $ （旁证：这两条为何恒真）
    B2 备份含「alert-if」/「alertIf」= 0 / 0     ← 改前也没有 ⇒ 断言「改后也不该有」两版同真
    B3 备份含「null」= 21 、「total」= 15        ← 断言体是 "null" in s and "total" in s，对任何 JS 文件都真

**三态：成立（附两条校准，均为 S3）。**
- **「负控会红」成立**：4/4 件在改前备份上 **FAIL** ⇒ 脚本 `fails=0` 的读法（正控全过 ∧ 负控全红）**在「件」粒度上站得住**。**本件点名的这一件事，答案是「是，真会红」。**
- **校准 ①（断言粒度）**：15 条断言中 **2 条恒真**（B3「null 语义」= 同义反复；B2「不重复实现告警」= 改前改后都为负）。⇒ 「负控有鉴别力」这句在**件**级为真、在**断言**级为 **13/15**。用**件级**语言描述**断言级**性质，属口径偏宽（S3）。
- **校准 ②（报告层）**：脚本 `:205` 打印 **`bad[:3]`** ——**只显示前 3 条不成立项，且无省略号/计数**（`不成立项=[…]`）。**我本人上一轮就被这一行误导**，把 B1 读成「负控红 3/8」。⇒ 这是**可致读者低估鉴别力**的展示缺陷（S3；修法 = 打印 `len(bad)` 并加 `…(+N)`）。
- ★ **我另核了「改前备份是不是真的改前」**：四份 `.bak-good-2026-10-10-20-3` 均在 `guard/backups/`（mtime 04:36），逐份含旧代码（B1 备份 `return delivered;`=1 且 `{delivered,expired}`=0；B3 备份 `scan.count === 0`=1 且无 `degenerate`）⇒ **负控用的是真·改前**，不是「改后的另一副本」。

#### 6.2 B4 与 B2 已实效（launchd 直调 CLI）

    $ node ~/dsh-plugin-launchd-scan/cli.js --json    （EXIT=0，从中抽 bus-triage）
    {
      "state": "loaded",
      "label": "com.dsh.cron.bus-triage",
      "command": "/opt/homebrew/bin/node /Users/coreyleung/dsh-plugin-bus-queue-triage/cli.js",
      "intervalS": null,
      "calendar": { "hour": 9, "minute": 0, "weekday": 1 },
      "runAtLoad": false,
      "freqClass": "weekly-scheduled",
      "residentRisk": "none"
    }

**三态：成立。** `freqClass = weekly-scheduled` + `weekday: 1` 逐项对上 ✓（`hour/minute` 亦保留 ⇒ 旧字段未被破坏 ✓）。

#### 6.3 B1/B3 待重载（进程内插件）

    （本件期望）cld_health_check ⇒ C7_version 仍 ok:true（本件明示：**不主张已生效**）

**三态：★ 不可判（我取不到该面）。** 本会话**没有** `cld_health_check` 工具（我的工具面里不存在），我也**不去**以别的方式戳 CLD（重启/热更新均在禁令内）。
★ 但**这一条的不可判不影响批次**：本件 6.3 的**期望本身就是「应仍为旧值」**，即它**不声称生效** ⇒ 与 §二.2 的边界声明一致；B1/B3 的**结构面**已由 6.1 独立坐实（源码改了、断言过了），**行为面**按本件与我的共同边界 = **须用户重启后方可判**。

#### 6.4 版本四处一致（1.5.21 / 1.0.1 / 0.1.2 / 1.0.1）

★ 先核**本件给的那条复跑命令**（`--version` 各件）：

    $ for d in …; do out=$(node ~/$d/cli.js --version 2>&1); rc=$?; …; done
    dsh-plugin-agent-bus         rc=2  首行=用法错误: 未知旗标 --version
    dsh-plugin-launchd-scan      rc=2  首行=用法错误: 未知旗标 --version
    dsh-plugin-guard             rc=2  首行=用法错误: 未知旗标 --version
    dsh-plugin-bus-queue-triage  rc=2  首行=用法错误: 未知旗标 --version

    $ （四件 cli.js 头部：正确旗标是 --tool-version）
    agent-bus/cli.js      : if (args.includes('--tool-version')) { console.log(pkg.version); process.exit(0); }
    launchd-scan/cli.js   : --tool-version  # ⑥ 版本单一来源
    guard/cli.js          : if (args.includes('--tool-version')) { console.log(pkg.version); process.exit(0); }
    bus-queue-triage/cli.js: --tool-version        版本号（单一来源）

改用正确旗标后实测：

    $ for d in dsh-plugin-agent-bus dsh-plugin-launchd-scan dsh-plugin-guard dsh-plugin-bus-queue-triage; do
        printf '%-28s package.json=%-8s --tool-version=' "$d" "$(…package.json…)"; node ~/$d/cli.js --tool-version; done
    dsh-plugin-agent-bus         package.json=1.5.24   --tool-version=1.5.24
    dsh-plugin-launchd-scan      package.json=1.0.1    --tool-version=1.0.1
    dsh-plugin-guard             package.json=0.1.2    --tool-version=0.1.2
    dsh-plugin-bus-queue-triage  package.json=1.0.1    --tool-version=1.0.1

**三态：不成立（两项）。**
1. **复跑命令本身跑不出期望**：`--version` 在四件上**全是未知旗标、exit 2**。本件 §五.4 说「会变的数字都附了复跑命令，正是为此」—— **这一条的复跑命令是坏的**（`launchd-scan`/`bus-queue-triage` 因顺带打印 USAGE 才恰好带出 `v1.0.1`，属**巧合**，不是命令有效）。
2. **数字对不上**：四件实测 **1.5.24 / 1.0.1 / 0.1.2 / 1.0.1**，本件写 **1.5.21**。经 §0.3 证实：`agent-bus` 的 `lib/index.js`+`package.json` 于 **16:38:54** 被再次改动（批次时 = 1.5.21，现 = **1.5.24**；同文件注释里已出现 `1.5.22`/`1.5.23`/`1.5.24`，`lib/selfcheck.js` 里已出现 **`1.5.25`** 字样）。
   ⇒ 「1.5.21」是**批次时点**的真值，作为**当前值**不成立；本件**未标时点**，故按「会变的数字」处置。

★ **我另抓一处（本件未提）**：`guard` 源码 **3 处注释写 `★ 1.0.2`**，而 `package.json = 0.1.2`，且源码里 **`0.1.2` 出现 0 次**：

    $ grep -n "1\.0\.2\|0\.1\.2" ~/dsh-plugin-guard/lib/index.js
    289:  // ★ 1.0.2（2026-10-11 星桥第二任 · 用户授权 M4/W7 批次）：早退分支亦须带 `degenerate`
    358:  // ★ 1.0.2（2026-10-11 星桥第二任 · 用户授权 M4/W7 批次）：**治空转绿**。
    380:  // ★ 1.0.2（2026-10-11）：`ok` 为 `null`（不可判）时**不得计入「全绿」**。
    计数: 1.0.2=3  0.1.2=0

⇒ 「⑥ 版本单一来源」被**自家注释**违反（S3）。

---

### 组 7 · 四件套与流程

#### 7.1 四件自洽

    $ python3 -I tools/beacon-check.py --net
    PASS 索引键可解析 / 锚点文档在位 / 锚点可读出 state_version / 索引 ↔ 锚点 state_version 相等 / 锚点指纹未变
    PASS 版本指针可解析 / 版本未回退 / 续接提示词在位 / ≤40 行 / 未漂移
    PASS 存在 closed_with_evidence 项（否则本条空转）
    PASS C1/C2/C3/C5/R049 证据指针可解 · PASS dod.full_table 缺席是显式声明的
    PASS updated_at 为 RFC 3339 规范形 / 未落在未来 · PASS waves·items 两段一致（B9）
    PASS closed 项 verifier 字段齐备（B10③）
    PEND closed 项审查员已到位（§11 六者之「审查员」）   << … ⇒ **未验证 ≠ 已关闭**
    PASS 本地副本 ↔ 板值一致（G-CR18 ④） · PASS 索引体量守恒（骤降检测）
    反遗忘校验：无 FAIL，但**有 1 项记为 closed 而审查员未到位** ⇒ 不得读作『全绿』（0 条 WARN，0 条 SKIP，1 项待复核）
    EXIT=0

**三态：成立。** `exit 0 · FAIL 0 · WARN 0 · SKIP 0` + **恰 1 项 PEND** —— 四项数字逐项对上 ✓。

#### 7.2 索引三方一致（本地 / 本机板 / 中枢板）

★ 本件给的指针是「见 m4w7 件 §八」。**我先扫 §八**（扫过的面：`docs/m4w7-batch-owner-fixes-20261011.md` 全文 137 行、§八 全文）：

    $ grep -n "^## \|^### " docs/m4w7-batch-owner-fixes-20261011.md
    … 八、复跑块（第 137 行）
    $ （§八 内含 5 块：[1] 结构断言 [2] B4 [3] B2 [4] B1/B3 [5] 语法与版本）
    ⇒ ★ **§八 内没有任何索引/canonical 复跑命令**（0 条命中）。

★ 于是我**自己写独立三方读数**（不引用任何被审方数字）：

    $ （本地文件 / 本机板 / 中枢板，各自取 value 子树 canonical sha256_16）
    面         canonical sha16     updated_at                  state_version
    本地文件     ce3dac412f264dd6    2026-10-11T04:44:43+08:00   6
    本机板       ce3dac412f264dd6    2026-10-11T04:44:43+08:00   6
    中枢板       ce3dac412f264dd6    2026-10-11T04:44:43+08:00   6
    ★ 三方 canonical 是否同值: True {'本地文件': 'ce3dac412f264dd6', '本机板': 'ce3dac412f264dd6', '中枢板': 'ce3dac412f264dd6'}

**三态：成立（实体）+ 证据指针不成立（形式）。**
- **实体**：三方 canonical **同值**（`ce3dac412f264dd6`）、`updated_at` 三方同值 ⇒ **「三方一致」这件事是真的**，我独立证实 ✓。（与 D-021 里记的 `c64da47787bd961d` 不同，是因为索引在 04:44:43 又被重盖过一次 —— 非矛盾。）
- **形式**：本件**指的那处没有这条命令**（§八 五块皆无）⇒ **证据指针不自足**（违本线自订的锚点 §17.6「锚点必须自足」的同类要求）。★ 这条若是交给一位**不写独立读数**的复核者，只能判「不可判」——**指针造价 = 让可成立的事变成不可判**（S3，但**正好落在本件自称最想要的那一类反馈**上，见 §三 之 (c)）。
- ★ 顺带（方法论，非本件之过）：本件若**只用** `beacon-check --net` 来证「三方」，**证不到** —— 该工具的 `board_value()` 是「先 local 成功即 return」：

      $ sed -n '147p' tools/beacon-check.py
      for name, base in (("local", BOARD), ("central", "http://xingqiao.meetfunbp.com:8792")):
      ⇒ 本机板能读时，**中枢板根本不会被读**。故「三方」这一范围，必须由**独立读数**补，不能由 `beacon-check` 单独支撑。

#### 7.3 步骤序缺陷已修（`--stamp` 须在 dualwrite 之前）

    $ （台账 D-021 自身的状态栏，逐字）
    | **状态** | ★ **`open`** —— 单次分叉已消除，但**程序缺陷未修**（属锚点/工具层） |
    $ （锚点 §4.6 八步：无 --stamp）
    $ sed -n '590,604p' docs/distributed-agent-network-governance-plan-v6.1-20261011.md
    0) 备份四件 → guard/backups/（★ 不放 /tmp）
    1) 查红灯（agent_light resource=…）→ 取独占锁
    2) 写 ① 新锚点（v5）—— ★ 必须内容最终化后才可盖章
    3) 改 ② 索引：anchor 路径 · state_version · updated_at（date 实读）· waves/items 一致化 …
    4) 经 tools/bb_dualwrite.py 双板写 + 回读断言
    5) 重生成 ③ 续接提示词 · 6) 写 ④ ~/.dsh/continuity-last-version
    7) python3 tools/beacon-check.py --net ⇒ 必须 exit 0 且无 SKIP
    8) 释锁
    $ grep -n "stamp" docs/distributed-agent-network-governance-plan-v6.1-20261011.md
    （0 条命中；仅 :926 / :2088 的 strftime 与之形近，非 --stamp）
    $ shasum -a 256 docs/distributed-agent-network-governance-plan-v6.1-20261011.md
    bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3   ← 与本件所载锚点 sha 相同（未变）

**三态：不成立（就「步骤序缺陷已修」这半句）。**
- **「已修」不成立**：台账 **D-021 自己**写着 **`open`**、「**程序缺陷未修**」；锚点 §4.6（sha 未变）八步中**没有 `--stamp`**，锚点全文亦**无 `--stamp` 字样** ⇒ **锚点层未改、工具头部与 §4.6 的口径不一致仍在**。
- **「本轮已按更正后序执行、无假红」这半句成立**：`beacon-check --net` G-CR18 ④ **PASS** ✓ + 7.2 三方 canonical 同值 ✓。
- ★ 本件把下半句写成了上半句 ⇒ **「未修」被写成「已修」**，与台账 **D-003（N1 报成「已修好」而实际未修：自述与实测不符）**呈**同型**。

---

## 二、不符清单（按严重度）

★ 严重度量纲沿用本线既有档位：**S1** = 结论级失真 / **S2** = 事实级失真（会误导下游动作或复核规模）/ **S3** = 口径与整洁。

| # | 级别 | 条目 | 判据（可复跑） | 证据（未编辑） |
|---|---|---|---|---|
| **N1** | **S2** | ★ **委托件把未修写成已修**：7.3「**步骤序缺陷已修**」，而台账 **D-021 = `open`、程序缺陷未修**；锚点 §4.6 未改（sha 同）且**全文无 `--stamp`** | `awk '/^## D-021/,/^## D-022/' docs/deviation-ledger-20261011.md`；`sed -n '590,604p' 锚点`；`grep -n stamp 锚点` | `| **状态** | ★ **`open`** —— …**程序缺陷未修**（属锚点/工具层） |` / §4.6 八步无 `--stamp` / grep 0 命中 |
| **N2** | **S2** | **版本数不实**：6.4 写 `1.5.21`，实测 **`1.5.24`**（该件 16:38:54 后又改过；注释已含 1.5.22/23/24，selfcheck 已含 1.5.25） | `node ~/dsh-plugin-agent-bus/cli.js --tool-version` 与 `package.json` | `1.5.24 / 1.0.1 / 0.1.2 / 1.0.1` |
| **N3** | **S2** | **复跑命令无效**：6.4 的 `--version` 四件全 `exit 2`「未知旗标」（正确是 `--tool-version`）⇒「凡会变的数字都附了复跑命令」在这条上**落空** | `node ~/$d/cli.js --version; echo $?` | 四件 `rc=2  首行=用法错误: 未知旗标 --version` |
| **N4** | **S2** | **会变的数未附口径/时点**：5.3/5.4 的 A2 `18,767` 实测 **15,518**（差 3,249）；D-031 自引「coordinator.jsonl 7.2 MB」实测 **2.46 MB** ⇒ 该面被轮转/压缩 | `python3 -I scripts/cahac-envelope-conformance.py --status`；`wc -l ~/.dsh/inbox/bb/*.jsonl`；`stat -f %z` | `A2 … parsed_objects = 15518` / 9 文件行数合计 15518 / `coordinator.jsonl 2,584,663 B` |
| **N5** | **S2** | **台账元数据不实（两处）**：§三末「台账**全 31 条**…（只增不改，**全部 `open`**）」—— 实测 **35 条**，且 **≥4 条带 ✅ 非 open** 状态 | `grep -c '^## D-[0-9]\{3\}' docs/deviation-ledger-20261011.md`；`grep -o '| \*\*状态\*\* | [^|]*' … \| sort \| uniq -c` | `35` / `2 ✅已闭合（含独立 verifier）`、`1 ✅已修并经验证`、`1 ✅已改`、`1 ✅已申报` |
| **N6** | **S3** | **证据指针不自足**：7.2「见 m4w7 件 §八」—— **§八 内无该复跑命令**（5 块皆非索引项）；实际可用的是 `beacon-check` 的 G-CR18 ④（**且它只覆盖本地↔本机板**） | `grep -n '^## \|^### ' docs/m4w7-batch-owner-fixes-20261011.md`；`sed -n '133,152p' tools/beacon-check.py` | §八 五块无索引项（扫过面 = 该文件全文 137 行）；`board_value()` 先 local 成功即 `return` |
| **N7** | **S3** | **负控鉴别力在断言粒度打折**：15 条断言 **13 条**变红、**2 条恒真**（B3「null 语义」同义反复；B2「不重复告警」改前改后皆负）—— 而 4.3/6.1 用**件级**语言说「有鉴别力」 | `scripts/verify-m4w7-batch-fixes.py` 的 `run()` 对四份备份逐条求值（不截断） | `合计: 15 条断言 · 负控红 13 · 恒真 2` |
| **N8** | **S3** | **负控报告截断且无标注**：脚本 `:205` 打 `bad[:3]`，读者会把「不成立项 3 条」读成「只有 3 条有鉴别力」（**我本人即被此误导**） | `sed -n '204,206p' scripts/verify-m4w7-batch-fixes.py` | `print("  %s %s 负例=%s ⇒ %s  不成立项=%s" % (…, (bad[:3] or "无")))` |
| **N9** | **S3** | **回滚点覆盖不全**：B2 改了 **两个**文件（`cli.js` + `lib/core.js` 的 `VERSION`），但**只有 `cli.js` 有回滚点**；`lib/core.js` 无备份，而 §四 写「4 件**均带备份与回滚点**」 | `ls guard/backups/ \| grep bus-queue-triage` | 仅 `…bus-queue-triage__cli.js.bak-good-2026-10-10-20-3`（无 `__lib__core.js…`） |
| **N10** | **S3** | **版本单一来源被自家注释违反**：`guard` 源码 3 处注释写 `★ 1.0.2`，`package.json = 0.1.2`，源码内 `0.1.2` **0 次** | `grep -n "1\.0\.2\|0\.1\.2" ~/dsh-plugin-guard/lib/index.js` | `1.0.2=3  0.1.2=0` |
| **N11** | **S3** | **口径偏宽两处**：2.4 称「7 条负控」实为 **6 负控 + 1 边界**（输出行自标 `N4 边界`）；3.4 同形 | 两工具的 `--selftest` 输出 | `OK  N4 边界 空集 ⇒ MATCH …` |
| **N12** | **S3** | **复跑命令引用易失路径**：`142` 的证据在 `/tmp/drift-scan-cron.err.log` —— 违**锚点自订** §5.3⑤「自包含复跑命令（**禁引用 /tmp 等易失路径**）」 | `ls -la /tmp/drift-scan-cron.err.log` | `-rw-r--r-- … 10月 11 03:47 /tmp/drift-scan-cron.err.log` |
| **N13** | **S3** | **「有读者」所指不自足**：只能证「有位定时消费者 + 留了历史」，不能证「有活人看输出」；本件把它当作对锚点「没人看」的**更正**，更正落点须同样精确 | `launchctl list \| grep bus-triage`；`tail -3 logs/bus-triage-cron.log` | `-	0	com.dsh.cron.bus-triage` / 日志末条 = 10-05 |

**S1：0 条。**（扫过的面 = 本件全部 7 组 28 条声称 + 已复跑的全部命令 + 四件属主件源码 + 台账 35 条 + 锚点 §4.6/全文 grep + 双板 + gate 台账 + 索引三方。）
★ **没有一条不成立触及批次结论本身**——四条属主件整改**结构性成立**（6.1）、两条已实效（6.2）、两条待重载（6.3，且本件本来就不声称生效）。

---

## 三、★「范围写宽了」专项（本件点名最想要的一类）

按本件 §五.2 的要求，逐条直说：

**(a) 「台账全 31 条 · 全部 open」——范围与状态两头都宽。**
数：实测 **35**（写就时亦已 ≥33）。状态：「全部 `open`」被自家台账打脸（**≥4 条 ✅**，其中 **3 条自称带独立 verifier**）。
★ 更要紧的是**读法**：本件 §〇 说「本批全部…无独立 verifier ⇒ 一律不得记 closed」，而它同段引的台账里**有 4 条记着 ✅**。**两句话并存 ⇒ 下游可以任一取用**。建议：本件凡引台账，写「**本批新增条目**（D-024…D-035 等）全为 `open`」，不要写「台账全部 open」。

**(b) 6.4「版本四处一致」——「四处」这个词把两种口径混了。**
本件只给了 `--version` 各件 + `package.json`（= 2 面 × 4 件）。实测**第 3 面是坏的**（旗标不存在），**第 4 处从未出现**（既没有 manifest 面，也没有 `dsh` 侧注册面）。⇒ 「四处」应写清**是哪四处**；否则读者会以为有四处独立佐证，实际**只有一处有效（package.json）**。

**(c) 7.2「索引三方一致」——范围对，指针错。**
「三方」是真的（我独立读到三方同 sha ✓），但**指向的 §八 里没有这条命令**；且**唯一现成工具 `beacon-check --net` 覆盖不到三方**（`board_value()` 先 local 成功即 return）。⇒ 建议：要么把独立三方读数**写成命令进 §八**，要么把声称收窄为「本地 ↔ 本机板一致（另见 D-021 的三方读数）」。

**(d) 1.1 的 `142` —— 证据面选在了 `/tmp`。**
锚点 §5.3⑤ 明文禁引用易失路径，本批自己违了一次。同一事实其实有**不挥发**的替代面（`launchctl list` 的 `- 1 com.dsh.cron.drift-scan` + 中枢板 10-04…10-10 全 0 的逐日分布）⇒ 建议换面。

**(e) 4.4「影响 22 项」——数字对，但把两种缺陷并成一个数。**
21（dict 读成无排程）+ 1（array 读了但丢 Weekday/Day）**性质不同**。同为「22」在**爆炸半径**意义上可用，但**不能读作「22 项被同一缺陷命中」**。

**(f) 「B1/B3 结构断言已过」——范围只到源码结构，这点本件**写清楚了**（§二.2 + 6.1 脚本自带声明）。**★ 这是本批**范围写得最准**的一处，我不改判。

**(g) 「消费端有读者」——见 N13。**
本件此处是**对锚点的更正**，更正的价值全在措辞精度上；「有读者」若不写明是「有消费者」还是「有人看」，会更正出一个**新的**含糊。

**(h) ★ 反向的一条（你的范围写窄了）**：本件 §一 组 4 把 B3 的修复写成「`total===0 ⇒ ok=null`」——只覆盖 `guard_deps_scan` 一处。我读源码见**同类退化**在 `:365` 之外还有 `:371  if (scan.degenerate) {` 的分支处理（且 `:380` 有 `=== true` 的「全绿」严格化）。⇒ 若这是你要的最终形态，**建议把 B3 的声称扩到「退化语义在判据 + 汇总 + 全绿三处一致」**，否则下一轮复核者会重复发现这半截。

---

## 四、自陈错误：判轻 / 判重的复核（本件 §五.3 要求）

| 台账条目 | 本件自陈 | 我的判 |
|---|---|---|
| **D-026**（「含 7 个带 Weekday」→ 正确 Weekday 5 + Day 3 = 8） | 本线自捕 | **不加重**。我独立枚举得 **Weekday 5 + Day 3**，与更正**逐字一致** ⇒ 自陈充分、更正有效。 |
| **D-022**（说 61044「全库零引用」——漏扫 `docs/`+`notes/`） | 本线自陈「违席位纪律第 5 条」 | ★ **应加重**：**同一族（面不完整）在本批又发生了两次** —— ① D-031（glob 不下降子目录，18,767 那面）；② **本件自己的 7.2 指针指错处**。⇒ 这**不是**一次手误，而是**「面 / 指针」的系统性缺陷**。建议单列一条「**面与指针完整性**」的形态条目，而不是一条条记。 |
| **D-031**（信封尺 glob 缺口 · 漏 18,767） | 本线自捕 | ★ **应加重**：它**违反自己引用的规则**（§14.1「凡会变的数字附复跑命令」）—— 给的是**会变的数**（今测 15,518），**无复跑命令、无时点**，且**其自引的 `7.2 MB` 今天只有 2.46 MB**。同族：台账 **D-006「写死了会变的数字」**。 |
| **D-021**（§4.6 步骤序风险） | 本线实捕，状态 `open` | ★ **本条台账没错，错的是委托件**：D-021 自陈 `open`「程序缺陷未修」，**本件 7.3 却写成「已修」** ⇒ 属**本件与台账不符**（= N1）。建议把 7.3 的措辞改回台账原话。 |
| **D-025**（把 B1 写成「静默 DLQ」） | 他方指出，本线接受 | **不加重**。本批 3.1 的措辞已收窄为「产生端把 `expired` 算出后丢弃」（**描述**而非**推断后果**）⇒ 更正到位。 |
| **D-027 / D-016 / D-017 / D-019** | 自陈 | **不加重**（本轮不在我的复跑面内，且与 M4/W7 批次结论无关；见 §五 未核）。 |

★ **另有一条「本件未自陈、但同型」**：**verifier 字段的字面与语义**。索引里 5 个 closed 项的 `verifier` 写的是「**待第三方复核**」（beacon-check 的 PEND 正因此），而台账里另有 3 条写「**已闭合（含独立 verifier）**」。⇒ 同一个词在两处含义不同（**在位** vs **待位**）。本件既已自陈「无独立 verifier」，**建议把台账里 3 条 ✅ 的 verifier 具名**（具名后我不再有疑；`D-003`/`D-004` 指的是 round2/3/5/6/7 的外部线，看起来是**同一批**（我这一线），若如此则应写明）。

---

## 五、未核清单（附我扫过的面）

★ 报「未核/0 条」必须连**扫过的面**（席位纪律）。

| # | 未核项 | 为什么未核 | 我已扫过的面 |
|---|---|---|---|
| U1 | **6.3 `cld_health_check` 的实际返回** | 本会话**无该工具**；且取值本身要求「进程内插件已重载」，重启在禁令内 | 四件源码结构面（6.1 已核）；CLD 运行面**未触碰** |
| U2 | **B1/B3 的行为是否已生效** | 同上（须用户重启） | 结构断言 8+2 条全过；改前备份 8/8、1/2 变红 |
| U3 | **`guard_deps_scan` MCP 工具的实际返回报文** | 本会话无该工具 | 底层计数**独立复算**（106/101/5/0）+ 源码判据 `:291/:306/:365` 逐行对读 |
| U4 | **A2 面「18,767」当时的口径**（是否含当时更大的 jsonl） | 该面**会变**（现 15,518）；我拿不到 05:0x 时的快照 | `bb/` 9 个 jsonl 逐文件行数/字节/mtime；`coordinator.jsonl` 从 7.2 MB → 2.46 MB 的**收缩**证据；工具 mtime 04:43:46（未变）⇒ 排除「工具定义变了」 |
| U5 | **`funnel-public` 502 的根因**（D-023：61044 是 CLD 历史端口） | 不在本批 28 条声称内；且需碰 CLD 运行面 | 仅核到「它**仍是红的**」（`--status` 输出）+ 「不可经门变更」（2.2/2.3） |
| U6 | **B2 的 `lib/core.js`（VERSION 1.0.1）内容面** | 无回滚点可比对；结构断言脚本**只断言 cli.js**（`TARGETS["B2"]` 指向 `cli.js`） | 该文件 mtime/尺寸/sha16 已记（§0.2）；`grep` 见 `1.0.1` ×3 |
| U7 | **`--stamp` 的实操后果**（D-021 的复现） | 复现它要**真的跑** `--stamp` 去改本地副本（写操作），超我「只读」边界 | 读源码 `:592-598` 逐字（D-021 已引）+ 本次 `--net` 实测 G-CR18 ④ **PASS**（= 分叉**当前**不存在） |
| U8 | **本批 8 件证据件的**内容**逐条复核** | 本轮范围 = 28 条声称；我只读了其中的 m4-1（§一/§二/§三）与 m4w7（§二/§八）**取证段落** | 8 件**存在性 + 体量 + mtime** 全核（见下） |

    $ （8 件证据件存在性 · 未编辑）
      ✓ 10-11 04:07  12079  docs/m4-1-delivery-and-evidence-20261011.md
      ✓ 10-11 04:11  12210  docs/m4-2-delivery-and-evidence-20261011.md
      ✓ 10-11 04:14  11673  docs/m4-3-delivery-and-evidence-20261011.md
      ✓ 10-11 04:15  12184  docs/w7-false-green-assessment-20261011.md
      ✓ 10-11 04:41  10934  docs/m4w7-batch-owner-fixes-20261011.md
      ✓ 10-11 04:42   9636  docs/a2-port-pin-verified-patch-20261011.md
      ✓ 10-11 16:39  71065  docs/deviation-ledger-20261011.md
      ✓ 10-11 03:58   9378  docs/spec-effectivity-levels-v1-20261011.md

★ **4 支新工具**：`channel-denominator 1.1.0` · `bus-delivery-alert 1.0.0` · `cahac-envelope-conformance 1.0.0` · `verify-m4w7-batch-fixes 1.0.0` —— **四支皆可跑、版本与 §四 逐字相符** ✓（由各自 `--selftest`/`--version` 输出直接读得）。
★ **4 处回滚点**：四份 `.bak-good-2026-10-10-20-3` 均在 `guard/backups/`，mtime 04:36 ✓（★ 覆盖缺口见 N9）。

---

## 六、一句话结论

**本批 28 条声称：成立 22 条 · 不成立 2 条（6.4 版本数与复跑命令 / 7.3「已修」）· 不可判 1 条（6.3，我无该工具；且本件本不主张生效）· 分裂 3 条（5.3 A2 数不成立、5.4 结构成立数字不成立、7.2 实体成立指针不成立）—— ★ **无一条不成立触及批次结论**：四件整改**结构性成立且负控真的会红**（我独立复算：件级 4/4 红；断言级 13/15，2 条恒真），B2/B4 **已实效**，B1/B3 按边界**待用户重启**；真正需要改的是**件级元数据与证据指针**（台账「31 条/全部 open」不实、7.3 把 `open` 写成「已修」、6.4 的复跑命令跑不出期望、7.2 指针指空、A2 的会变数未附时点）—— ★ 且需立刻记录一件事：**被审树在本件写就后仍在移动**（`agent-bus` 于 16:38:54 改到 1.5.24，17:07 又落新备份），**任何「现状为 X」的陈述在本件中都应带时点与 sha**。**

---

## 七、署名与复核时刻

- **复核方**：外部第三方 · Claude Code 会话 · 角色键 `ext` · session `005a2c58-7439-4ad5-bebf-815b29c2ca4a` · CU 实验台线
- **复核窗口**：**2026-10-11 17:04–17:12 CST**（★ 本文件落盘 17:11；逐条命令的执行时刻散见 §一）
- **被审件锚定**：锚点 `bf5a4e6b76fdedeb…`（252,738 B · mtime 03:48:35）；四件属主件 sha16 见 §0.2（**以 17:2x 实测为准**）
- **只读声明**：本轮**未**重启 CLD、**未**热更新、**未**改 profile、**未**改任何插件源码/配置、**未**跑 `guard --selfcheck`、**未**发 xdom 信；**唯一写入物 = 本文件**
- **三态纪律**：
  - **成立 22 · 不成立 2 · 不可判 1**（+ 3 条分裂态：5.3 A2 数 / 5.4 结构vs数字 / 7.2 实体vs指针）—— **22+2+1+3 = 28** ✓
  - ★ **报「0 条」的面**：本件 7 组 **28** 条**逐条**已跑或已判；**S1 = 0 条**（扫过的面见 §二 表下）；**PEND/未核 8 项**（见 §五，逐项附扫过的面）
- ★ **本件是复核结果，不是裁定**；★ **我不宣布任何事项已闭合**（S3：本件由起草人一人起草并执行，**verifier = 我**；凡我判「成立」的，其**闭合**仍须由**用户/本线**决定）。

*（本件只增不改；更正以新件追加。）*

---

## 八、★ 复核后漂移记录（本件发布后追加 · 按 §四 A 层自缚）

★ 本件 §0.2 的锚在**发布后即部分过期**。按本提议件（`docs/proposal-review-window-traceability-20261011.md`）§四 A 层「闭窗指纹」自缚，追加如下：

| 件 | 本件 §0.2 开窗值（17:2x） | 现测值（2026-10-11 17:17） | 是否漂移 |
|---|---|---|---|
| `~/dsh-plugin-agent-bus/lib/index.js` | `ee255df4bb3de2cb` | **`8802f6736dc3fdfe`** | ★ **是**（mtime 17:15:54） |
| `~/dsh-plugin-agent-bus/package.json` | （版本记 1.5.24） | **1.5.26**（mtime 17:16:02） | ★ **是** |
| `…/lib/selfcheck.js` | — | `583b1bc31ad84938`（mtime 17:07:12） | 是（本件未锚该件） |
| 其余四件（launchd-scan / guard / bus-queue-triage ×2） | 见表 | 见 `shasum`（未变） | 否 |

★ **因此**：
1. **本件 6.4 的判词「实测 1.5.24 ≠ 声称 1.5.21」在今日 17:2x 成立**；★ 但**现值已是 1.5.26** —— 判词应读作**区间内成立**，非「现值」。
2. ★ **§0.3 的「树在移动」不应被读作纪律问题**：起草人 `docs/pre-restart-review-20261011.md` §四 自陈，该窗口的改动是**重启前的回归修复**（selfcheck 判据由「钉字面」改「钉契约」），且 §五 顺手补齐 3 个漏掉的回滚点。⇒ **这是合法且必要的工作**；本件 N2/N3 的不成立**根因是「委托件未登记写就时的指纹」，而非「有人动了手」**。
3. ★ **若要对 B1 现值出具判词，须对 `8802f6736dc3fdfe` 复跑** —— 本件未做，故**本件对 B1 的判词止于 `ee255df4bb3de2cb`**。

*（本件只增不改；本节的更正以新件追加。）*

### 八之二、★ 定向复跑结果（2026-10-11 17:17–17:30 实测 · 对漂移后的 `8802f6736dc3fdfe`）

★ 因 §八 的漂移，本线对**受影响的子集**当场复跑（不重跑整批）。结果如下：

| 项 | 开窗（本件 §0.2） | 定向复跑（17:30） | 判定 |
|---|---|---|---|
| 3.1 `return { delivered, expired }` | `:1366` 命中 1 | **`:1411` 命中 1** | ★ **仍成立**（行号移位） |
| 3.1 旧形态 `^    return delivered;$` | 0 处 | **0 处** | ★ **仍成立** |
| 3.2 `boarded-pending') msg.status` | 2 处 | **2 处** | ★ **仍成立** |
| 6.1 四件断言（正控） | exit=0 | **exit=0** | ★ **仍成立** |
| 6.1 负控（改前备份必须红） | 4/4 FAIL | **4/4 FAIL** | ★ **仍成立** |
| **6.1 断言计数 / 校准** | **15 条 · 红 13 · 恒真 2** | ★ **16 条 · 红 14 · 恒真 2** | ★ **判词作废，须重算** |
| 6.4 版本 | 1.5.21（称）→ 1.5.24（测） | **1.5.26** | ★ **判词作废**（区间内成立） |
| N5 台账条数 | 31（称）→ 35（测） | **40** | ★ **判词作废**（区间内成立） |

★ **关键结论**：**B1 的修复未被后续两次改动弄回去** —— 3.1/3.2 的证据形态与四件断言正负控**全部保持** ⇒ **漂移未推翻批次核心结论**。
★ **但 6.1 的校准数变了**：`scripts/verify-m4w7-batch-fixes.py` 于 **17:16** 被改，**B1 断言 8→9**（新增「★ 重启提议接上『重启前审查门』」，对应台账 **D-038**）⇒ 现为 **16 条 · 负控红 14 · 恒真 2**（恒真两条与 N7 同：B3「引入不可判（null）语义」· B2「不重复实现告警」）⇒ ★ **N7 判断本身仍成立**（2 条恒真），仅计数更新。
★ **该脚本无备份、且从未入 git**（`dsh-collab` 最后一次提交为 **10-10 22:00 `78dd230`**，今日全部产物**未提交**）⇒ **无 diff 可用，只能重测** —— 这本身是「今日整批无 VCS 留痕」的一处实证。

*（本件只增不改；本节以 17:30 实测为准，其后漂移概不追认。）*
