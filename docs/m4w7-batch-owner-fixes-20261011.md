# M4/W7 批次属主件整改 · 交付与证据件

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **锚点依据**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3`
> ★ **更正**（本件自捕，2026-10-11）：初稿此行 sha 末段误写为 `…948e49e9e3`（多一个 `9`），★ **已以 `shasum -a 256` 实读更正**。
> **授权**：★ **用户 2026-10-11 逐字**「只要是锚点 6.1 的目标我都同意授权你做」；授权记录见 `docs/deviation-ledger-20261011.md` **D-030**
> ★ 本件是**交付证据件**；★ **不宣布任何事项闭合**（S3 不可自审）；★ 效力档位 **L1**

---

## 一、★ 先读这一段：哪两件**已生效**、哪两件**待重载**

| 件 | 形态 | 生效条件 | 实测状态 |
|---|---|---|---|
| **B4** `dsh-plugin-launchd-scan` | ★ **launchd 直调 CLI**（`node ~/dsh-plugin-launchd-scan/cli.js`），**不经 CLD 进程** | 下次调用 | ✅ **已实测生效**（见 §三） |
| **B2** `dsh-plugin-bus-queue-triage` | ★ **launchd 直调 CLI** | 下次调用 | ✅ **已实测生效**（见 §四） |
| **B1** `dsh-plugin-agent-bus` | ❌ **CLD 进程内加载**的插件 | ★ **须重载 CLD** | 🟡 **源码已改，行为待重载** |
| **B3** `dsh-plugin-guard` | ❌ **CLD 进程内加载**（`cld_health_check` 即由它提供） | ★ **须重载 CLD** | 🟡 **源码已改，行为待重载** |

★★ **B3 的「待重载」有直接实证**：改动后调 `cld_health_check`，其输出仍为
`C7_version: {ok: true, count: 0}` 且 `all_ok: true` ⇒ **跑的仍是旧内存副本**。
★★ **★★ 重载路径的硬约束**：**不得走热重载** —— `docs/agent-comm-portal-20261002.md` 附录 B 逐字：
> 「**禁用 `POST http://127.0.0.1:31888/reload`**：CLD 壳 `main.js:570` 存在 `undefined.reloading` 缺陷
> （2026-10-02 16:29 实测触发 uncaughtException → **壳崩溃自动重启**）。插件代码生效走**正常重启**，不走热重载。」
⇒ ★ **生效方式 = 你正常重启一次 CLD**（本线不改启动方式、不触发重载端点）。

---

## 二、四件改动清单（逐处）

### B1 · `dsh-plugin-agent-bus/lib/index.js` · `1.5.20 → 1.5.21`

| # | 位置 | 改动 |
|---|---|---|
| 1 | `flushQueue()` 尾部 | `return delivered;` → **`return { delivered, expired };`** ★ `expired` 此前被算出后**在 return 处丢弃**，调用方连数量都拿不到（台账 D-024/D-025） |
| 2 | `sendMessage()` | `msg.status = ok ? …` → **`if (msg.status !== 'boarded-pending') msg.status = …`** ★ 原式把 `deliver()` 设好的**诚实态**覆盖掉，使异步 `settle()` 的守卫 `status === 'boarded-pending'` **永不满足** |
| 3 | `broadcast()` | 同上（第二处同型覆盖点） |
| 4 | HTTP `/api/flush` | `{ ok: true, delivered: flushQueue() }` → **`{ ok: true, ...flushQueue() }`** ★ 响应含 `delivered` **与** `expired` 两键（**向后兼容**：`delivered` 键保留） |
| 5 | `flush()` 导出 | **保持原数字契约** `flushQueue().delivered`（★ 全机**无**外部消费者，仍不变更契约） |

**回滚点**：`guard/backups/Users__coreyleung__dsh-plugin-agent-bus__lib__index.js.bak-good-2026-10-10-20-3`

### B4 · `dsh-plugin-launchd-scan/lib/core.js` · `1.0.0 → 1.0.1`

`StartCalendarInterval` **既可为 dict（单个）也可为 array（多个）**；原实现用 `Array.isArray(...)` 只认数组形态 ⇒
**dict 形态被判「无排程」**；且只取 `Hour`/`Minute` ⇒ **丢掉 `Weekday`/`Day`**。

改后：兼容两形态 + 保留日期限定 + `freqClass` 细分（`weekly-scheduled` / `monthly-scheduled` / `multi-scheduled`，
原 `daily-scheduled` 与 `high`/`mid`/`low` **保留不动** ⇒ 消费者不受影响）。

**回滚点**：`guard/backups/Users__coreyleung__dsh-plugin-launchd-scan__lib__core.js.bak-good-2026-10-10-20-3`

### B3 · `dsh-plugin-guard/lib/index.js` · `0.1.1 → 0.1.2`

| # | 改动 |
|---|---|
| 1 | `doDepsScan()` 两个 return 分支**都带 `degenerate: total === 0`** |
| 2 | `C7_version` 判据由 `ok: scan.count === 0` 改为**三态**：`scan.degenerate ? null : (scan.count === 0)`，并附 `degenerate`/`total`/`note` |
| 3 | `all_ok` 由 `.every(c => c.ok)` 改为**显式** `.every(c => c.ok === true)`，并新增 **`unverified`** 计数与 `unverified_checks` 名单 ⇒ 「全绿」须以「无不可判项」为前提 |

**回滚点**：`guard/backups/Users__coreyleung__dsh-plugin-guard__lib__index.js.bak-good-2026-10-10-20-3`

### B2 · `dsh-plugin-bus-queue-triage` · `1.0.0 → 1.0.1`（`cli.js` + `lib/core.js`）

★ **设计取舍（避免重复建设，J44）**：**不**把阈值告警再实现一遍（那会与本线已交付的
`scripts/bus-delivery-alert.py` **同一工作两处立账**）。本件只补**真正的缺口**：

- `cli.js` 的 `logLine('finish', …)` 原只记 `queued`/`expireable`，**漏掉 `report.total`** ——
  而 `total.expired` 恰是「静默 DLQ」那一项。★ 且 `logLine` 是**唯一 append 留历史的面**
  （`StandardOutPath` 每次**覆盖**）⇒ **唯一留历史的面上，恰恰没有那个要命的指标**（台账 D-017）。
  ⇒ 已补 `total: report.total`。
- `lib/core.js` 的 `VERSION` **同步**为 `1.0.1`（★ 见 §六 第 3 条：本线当晚实捕的不一致）。

**回滚点**：`guard/backups/Users__coreyleung__dsh-plugin-bus-queue-triage__cli.js.bak-good-2026-10-10-20-3`

---

## 三、B4 实测（★ 已生效，未编辑输出）

    $ node ~/dsh-plugin-launchd-scan/cli.js --json
      com.dsh.cron.bus-triage       freq=weekly-scheduled    cal={'hour': 9, 'minute': 0, 'weekday': 1}
      com.dsh.gate-weekly-audit     freq=weekly-scheduled    cal={'hour': 9, 'minute': 30, 'weekday': 1}
      com.dsh.archive-logs          freq=monthly-scheduled   cal={'hour': 3, 'minute': 0, 'day': 1}
      com.dsh.maintenance-restart   freq=multi-scheduled     cal={'hour': 4, 'minute': 0, 'day': 1, 'entries': 10}
      com.dsh.hr.daily-brief        freq=daily-scheduled     cal={'hour': 22, 'minute': 0}

    freqClass 分布: {'onetime':29,'weekly-scheduled':5,'monthly-scheduled':2,'multi-scheduled':1,
                     'daily-scheduled':14,'mid':20,'low':6,'high':3}
    highFreq 消费者（只认 'high'，未受影响）: ['com.dsh.comm-hb-fwd','com.dsh.hb-watchdog','com.dsh.hr.bb-request-watch']

★ **逐项吻合实测的爆炸半径**：`weekly-scheduled 5` + （`monthly-scheduled 2` + `multi-scheduled 1`）= **8**，
即「含 `Weekday` 5 个 + 含 `Day` 3 个」（台账 **D-026**）。

## 四、B2 实测（★ 已生效，未编辑输出）

    $ node ~/dsh-plugin-bus-queue-triage/cli.js --scan --json
      报告 total = {'delivered': 31272, 'expired': 2377, 'queued': 8}
    $ tail -1 ~/dsh-collab/logs/bus-queue-triage.log
      {"ts":"2026-10-10T20:40:06.126Z","kind":"finish","version":"1.0.1","mode":"scan",
       "queued":8,"expireable":0,"total":{"delivered":31272,"expired":2377,"queued":8}}
    $ node … cli.js --tool-version   →  1.0.1

## 五、B1 / B3 的验证方式（★ 不能重启 CLD ⇒ 用结构断言 + 负控）

**新建**：`scripts/verify-m4w7-batch-fixes.py` —— ★ **只断言源码结构**，并**拿改前备份当负例**。

    $ python3 scripts/verify-m4w7-batch-fixes.py --selftest
      正控（当前文件）：B1 PASS · B4 PASS · B3 PASS · B2 PASS  ⇒ exit=0
      ★ 负控（改前备份）：B1 FAIL(预期) · B4 FAIL(预期) · B3 FAIL(预期) · B2 FAIL(预期)
      => fails=0
      ★ 仅 fails=0 方可读作通过：正控全过【且】负控全红 = 断言既成立又有鉴别力。

★ **为什么不用行为测试**：这四件里 B1/B3 是**进程内插件**，行为测试须重启 CLD，而重启由用户执行
（既有规约）。⇒ 本件**只主张源码结构成立**，★ **不主张 B1/B3 的行为已生效**。

---

## 六、★ 过程中自捕的三个缺陷（均为本线自己引入或本线自己的工具）

| # | 缺陷 | 处置 |
|---|---|---|
| 1 | **验证脚本首版把「全部四件的断言」跑在「每一个文件」上** ⇒ B1 的报告里显示了 B4/B3/B2 的判据 | 已修为只跑该件自己的断言（`ASSERTS.get(tag)`） |
| 2 | ★ **验证脚本的断言撞上自指** —— B4 的「该串必须不存在」被**我自己的注释**打红（注释里为解释原实现而写了那个串） | 新增 `strip_comments()`，**断言一律跑在剥注释后的源码上**。★ 这与同日修过的 `drift-scan-cron` 门 D **是同一形态**（判据自指） |
| 3 | ★ **版本两处不一致** —— 只改 `package.json` 未改 `lib/core.js` 的 `VERSION` ⇒ 日志里出现「package.json 1.0.1 / 日志 version 1.0.0」 | 已同步 `lib/core.js` 至 `1.0.1`，并在该行注释里写明此坑 |

---

## 七、★ 未做与未证（别当已完成）

| # | 项 | 状态 |
|---|---|---|
| 1 | **B1 / B3 行为生效** | 🟡 **待你正常重启 CLD**（★ 不得走热重载，见 §一） |
| 2 | **B2 的「阈值告警接线」** | ❌ **未接线** —— 引擎 `scripts/bus-delivery-alert.py` 已交付（6 条负控），**未挂 cron**。★ 本线**不自行加 launchd job**（须先经 `channel_gate` 登记变更单，通道 = `launchd-daemons`） |
| 3 | **M4① 「连续 7 天」** | ⏳ 时钟自 2026-10-11T04:04 起算 |
| 4 | **四件全部结论** | ★ **本线自测，无独立 verifier** ⇒ 按 S3 **不得记 `closed`**；第三方复核**延后合并为一份委托件**（用户 2026-10-11 指示） |

## 八、复跑块

    # [1] 四件结构断言 + 负控（须 fails=0）
    python3 ~/dsh-collab/scripts/verify-m4w7-batch-fixes.py --selftest
    # [2] B4 已生效证据
    node ~/dsh-plugin-launchd-scan/cli.js --json | python3 -c "import sys,json;d=json.load(sys.stdin);print([ (r['label'],r['freqClass'],r['calendar']) for r in d['rows'] if r['label'] in ('com.dsh.cron.bus-triage','com.dsh.maintenance-restart')])"
    # [3] B2 已生效证据（日志须含 total.expired）
    tail -1 ~/dsh-collab/logs/bus-queue-triage.log; node ~/dsh-plugin-bus-queue-triage/cli.js --tool-version
    # [4] B1/B3 是否已随重载生效（★ 重启后此条才有意义）
    cld_health_check        # → C7_version.degenerate 应为 true 且 ok 应为 null、all_ok 应为 false
    grep -n 'return { delivered, expired }' ~/dsh-plugin-agent-bus/lib/index.js
    # [5] 四件语法与版本一致
    for f in ~/dsh-plugin-agent-bus/lib/index.js ~/dsh-plugin-launchd-scan/lib/core.js ~/dsh-plugin-guard/lib/index.js ~/dsh-plugin-bus-queue-triage/cli.js; do node --check "$f" && echo "OK $f"; done

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
