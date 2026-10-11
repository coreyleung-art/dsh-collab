# M4① 交付与证据件 · drift 告警跨板投递修复

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **锚点依据**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3`
> **锚点条目**：§14.4 **M4①c**「`drift-scan-cron.py:87-89` 补认证头（**经 `channel_gate` 登记变更单**，通道 = `board-central`）」+ **W7.6**
> **变更单**：`cg-mv2tmsth-1-dsi7` · channel `board-central` · meltRisk `ok` · `loggedAt 2026-10-10T20:02:47.525Z`
> ★ **本件是交付证据件，不是裁定**；★ **不宣布任何事项已闭合**（S3 不可自审）；★ 效力档位依 `docs/spec-effectivity-levels-v1-20261011.md` = **L1（已记录）**

---

## 一、修了什么（单文件）

**文件**：`scripts/drift-scan-cron.py` · `1.0.0` → **`1.1.0`**
**改前**：6,737 B · sha256 `ec7047d9b992da8bd3b2cbdbb9037a9956841731b96c9c4eacdc58475179be4f`
**改后**：15,287 B · sha256 `612841e7752100d96ab31ad99891486e4fb4832cfd7924207b47b27646980197` · 318 行

| # | 改动 | 锚点/规则依据 |
|---|---|---|
| 1 | **双板认证头**：本机板 `Authorization: Bearer`（`~/.dsh/board-token`）· 中枢板 `X-Blackboard-Token`（`~/.dsh/blackboard-token`）。口径源自 `tools/bb_dualwrite.py:47-54`（单一来源） | **M4①c** |
| 2 | **4xx 记终态、不重试**；仅 5xx/超时/连接失败**有界重试 2 次** | **W7.6** |
| 3 | **单腿失败不再中断另一腿**；两腿结果分别记录 | M4① 判据 |
| 4 | **投递腿失败写终态告警卡** `data/ops/drift-delivery-failure/<ts>`（本机+中枢尽力而写）+ 统一日志 | **M4③b** |
| 5 | **回读一致性只在两腿都成功时才可判**；一腿失败 ⇒ **不可判**，不报「不一致」 | 三态纪律 |
| 6 | ★ **`log()` 接上调用点**：正常/零漂移/工具异常/解析失败/两腿结果全部留痕 | **R006 ⑦** |
| 7 | ★ **新增 `--selftest`（真实现 + 入口分派）**：正控 + **活体负控** | **M4①d** |
| 8 | ★ **收紧门 D**：原判据 `'--selftest' in _self` 是**自指**，改为要求「真实现 + 入口分派」 | **锚点 §17.4「判据不得自指」** |
| 9 | 退出码语义：`0`=正常 · `1`=工具/解析异常 · **`2`=告警投递腿失败**（新增，不再以 0 冒充） | M4③a 精神 |

**回滚点**：`guard/backups/Users__coreyleung__dsh-collab__scripts__drift-scan-cron.py.bak-good-2026-10-10-20-0`（6,737 B · sha256 `ec7047d9b992da8b…` · **已与原文件逐字节比对一致**）

---

## 二、修复前定性取证（未编辑输出）

    $ for h in "无认证头" "X-Blackboard-Token" "Bearer"; do ... PUT 中枢 ... done
      无认证头           HTTP=401
      X-Blackboard-Token     HTTP=200
      Bearer                 HTTP=200

    $ for u in http://127.0.0.1:8792 ...; do curl -s "$u/data/ops/drift-alert/" | ... done
      http://127.0.0.1:8792              total= 312
      http://106.53.214.108:8792         total= 19
      http://xingqiao.meetfunbp.com:8792 HTTP-OK total= 19

    $ grep -c '401' /tmp/drift-scan-cron.err.log
      142          ← 锚点记 134，仍在增长
    $ tail -1 /tmp/drift-scan-cron.err.log
      urllib.error.HTTPError: HTTP Error 401: Unauthorized
    $ launchctl list | grep -i drift
      -	1	com.dsh.cron.drift-scan          ← exit 1，每 1800s 重复，零告警

★ **同源对照**：域名 `xingqiao.meetfunbp.com:8792` 与 IP `106.53.214.108:8792` 读同键**同值（19）** ⇒ **同一板，非两板**（脚本用域名、锚点 §14.5 复跑块用 IP —— 口径不同但同源，已消除「比错板」的假红风险）。

---

## 三、修复后实测（★ 写与观测分离：先跑，后另起一次读）

    $ /usr/bin/python3 scripts/drift-scan-cron.py          # 写入
      [drift-cron] 告警卡 local PUT HTTP=200 attempts=1
      [drift-cron] 告警卡 central PUT HTTP=200 attempts=1   ← ★ 首次成功
      [drift-cron] 漂移 1 项 → 告警卡 data/ops/drift-alert/1791662660041 双写一致
      exit=0

**独立观测（另一次调用）**：

    $ 本机板 total= 313   ·   中枢板 total= 20      ← 各 +1
    本机板 value sha16 = 2d928ddd3360911f | ts = 2026-10-11T04:04:20
    中枢板 value sha16 = 2d928ddd3360911f | ts = 2026-10-11T04:04:20
    ==> 两板 value 一致: True

    $ ls -la logs/drift-scan-cron.log                  ← ★ 此前【不存在】
      -rw-r--r-- 279 B
      2026-10-11T04:04:20 alert-card leg=local ok=True HTTP=200 attempts=1
      2026-10-11T04:04:20 alert-card leg=central ok=True HTTP=200 attempts=1
      2026-10-11T04:04:20 alert-card data/ops/drift-alert/1791662660041 双写一致 drift=1

    $ grep -c '401' /tmp/drift-scan-cron.err.log   →  142（未增长）
    $ stat -f '%Sm' /tmp/drift-scan-cron.err.log   →  2026-10-11 03:47:25（早于本次改动 04:04）

⇒ ★ **无新错误**（err.log 最后修改时刻早于改动时刻）。

---

## 四、负控（**能红才算数**）

### 4.1 活体负控：`--selftest`

    $ /usr/bin/python3 scripts/drift-scan-cron.py --selftest
      OK  P1 认证头按板构造（local=Authorization / central=X-Blackboard-Token）
      OK  P2 负控注入点确实去掉认证头（force_unauth）
      OK  N1 活体负控：去认证头打中枢 ⇒ HTTP=401 (4xx 终态，不重试)（必须红 ✓）
      OK  N2 活体正控：带认证头打中枢并回读 ⇒ HTTP=200 attempts=1
      OK  N3 回读断言：value.selftest == 1
      OK  N4 探针已清理 data/ops/drift-selftest-1791662635024
      => fails=0 undecidable=0 version=1.1.0
      exit=0

★ **N1 是活体负控**（真打中枢、真去掉认证头、真收 401）—— 不是恒真判据。
★ **三态**：中枢不可达时 N1 记 **`??` 不可判**（不冒充通过、也不冒充失败）；工具打印「`undecidable>0` 时**不得**读作通过」。
★ 探针键用完即删（N4），已实测清理成功。

### 4.2 门 D 收紧的负控：拿**旧版当负例**

    $ 新判据跑旧文件（guard/backups/…bak-good-2026-10-10-20-0）
      旧判据 ('--selftest' in _self)        => True   ← 旧版【通过】= 自指假绿
      新判据: 实现=False 入口分派=False => False
      ==> 收紧有效（旧通过 / 新不通过）: True
      旧文件中 '--selftest' 的全部出现位置：
         L136  c("D", "状态机：本工具可自证（--selftest 在位）",
         L137  '--selftest' in _self, "selftest 在位")
      旧文件是否真含 def selftest(: False
      旧文件入口分派是否存在   : False

---

## 五、★ 本次附带发现（**锚点未载** ⇒ 已入偏差台账）

| 编号 | 发现 | 证据 |
|---|---|---|
| **D-010** | ★ **门 D 判据自指**（违反锚点 §17.4）。`'--selftest' in _self` 为真**仅因为门自己写了那个字符串**；旧文件无 `def selftest(`、无入口分派 | 见 §4.2 未编辑输出 |
| **D-011** | ★ **`log()` 零调用点** ⇒ `logs/drift-scan-cron.log` **从未存在**，R006 ⑦「统一日志」**形同虚设** | 修复前 `ls logs/drift-scan-cron.log` → `No such file or directory` |
| **D-012** | ★ **锚点 §14.4 M4② 归因不完整**：①「公网入口」措辞不准 —— 实测 funnel 为 **`(tailnet only)`**；② 根因不止「告警送不出去」：`funnel-public` 的 `/` 代理到 **`127.0.0.1:61044`，该端口无任何进程监听、且无任何 launchd plist 管理**，全库零引用 ⇒ **根路径服务无属主** | `lsof -iTCP:61044 -sTCP:LISTEN` 空 · `curl` exit 7 · `Tailscale funnel status --json` 全文见下 |

**Funnel 配置原文（未编辑）**：

    { "Web": { "coreymac-mini.taild3fd86.ts.net:443": { "Handlers": {
        "/":         { "Proxy": "http://127.0.0.1:61044" },   ← ★ 无监听者
        "/asr":      { "Proxy": "http://127.0.0.1:8780" },
        "/laodeng":  { "Proxy": "http://127.0.0.1:8765" },
        "/plan":     { "Proxy": "http://127.0.0.1:8812" },
        "/sb":       { "Proxy": "http://127.0.0.1:8820" },   ← pid 56945 在跑
        "/sg":       { "Proxy": "http://127.0.0.1:8798" } } } } }   ← pid 5516 在跑

★ **不代裁归属**：61044 的服务**身份与意图未查明**（全库零引用），**本线不新建、不改路由、不猜实现** —— 按席位纪律移交属主/用户裁决。

★ **附带正面事实**：这条红**恰恰证明 `funnel-public` 的探测是活的** —— **「探测在」成立**。坏的是第二环（投递断，本次已修）与第三环（无人知，= 锚点 **W7.10 值守义务人**，属治理层）。

---

## 六、★ 口径声明（**P4：多口径须一处声明关系**）

「双板到达率」有**两个不同口径**，**不得混用**：

| 口径 | 定义 | 本次读数 | 用途 |
|---|---|---|---|
| **存量到达率** | 中枢 `total` ÷ 本机 `total`（含历史未达） | 20 / 313 = **6.4%** | ★ **不可用于判 M4①** —— 历史 293 张中枢从未收到，修复投递**不能倒填历史** |
| **增量到达率** | 修复后**新写卡片**的到达率 | 本次 n=1，**1/1 = 100%** | ★ **M4①a 的判据口径**（锚点原文含「**连续 7 天**」⇒ 本就指向前向增量） |

★ **本线不主张补投历史 293 张**：理由是锚点 §14.4 自己写明「**单看「到达率」可被作弊**」—— 把 7.5 天前的陈旧告警倒灌进中枢，**属同一类刷指标**，且它们是**已失效的历史告警**。★ 补投与否**属用户/属主裁决**，本线**不出豁免药方也不代拍**。

---

## 七、残留与未决（★ 别当已闭合）

| # | 项 | 状态 |
|---|---|---|
| 1 | **M4①a「连续 7 天」** | ⏳ **时钟自 2026-10-11T04:04 起算**，本线**无法在单次会话内完成** |
| 2 | **M4①d「造 401 ⇒ 必须红且必须有人收到」** | 🟡 前半（**必须红**）已由 `--selftest` N1 实测；★ 后半（**有人收到**）依赖 **W7.10 值守义务人**，**属治理层，本线不做** |
| 3 | **`funnel-public` 502 / 61044 无属主** | ❌ **仍在红**（持续中）—— 已留证 D-012，**待属主/用户裁决** |
| 4 | **本件全部结论** | ★ **本线自测，无独立 verifier** ⇒ 按 S3 **不得记 `closed`** |
| 5 | **存量 293 张历史告警** | 🟡 口径已声明（§六）；**是否补投待裁决** |

---

## 八、复跑块（★ 本节所有会变的数字，一条命令全出）

    # [1] 双板到达（两口径）
    for u in http://127.0.0.1:8792 http://106.53.214.108:8792; do
      printf "%s → " "$u"; curl -s --max-time 10 "$u/data/ops/drift-alert/" \
        | python3 -c "import sys,json;print('total=',json.load(sys.stdin).get('total'))"; done
    # [2] 自证（正控 + 活体负控，须 exit 0 且 undecidable=0）
    /usr/bin/python3 ~/dsh-collab/scripts/drift-scan-cron.py --selftest
    # [3] 约束门六项 A–F
    /usr/bin/python3 ~/dsh-collab/scripts/drift-scan-cron.py --lean4-check
    # [4] 统一日志是否在长（修复前该文件不存在）
    ls -la ~/dsh-collab/logs/drift-scan-cron.log && tail -3 ~/dsh-collab/logs/drift-scan-cron.log
    # [5] 401 是否停止增长 + err.log 是否停在改动之前
    grep -c '401' /tmp/drift-scan-cron.err.log; stat -f '%Sm' -t '%F %T' /tmp/drift-scan-cron.err.log
    # [6] launchd 退出码（应不再为 1）
    launchctl list | grep -i drift
    # [7] funnel-public 红是否仍在（61044 无属主）
    lsof -nP -iTCP:61044 -sTCP:LISTEN; curl -s -o /dev/null -w '%{http_code}\n' \
      --max-time 15 https://coreymac-mini.taild3fd86.ts.net/
    # [8] 投递失败卡命名空间（正常应为 0 条）
    curl -s --max-time 10 "http://127.0.0.1:8792/data/ops/drift-delivery-failure/" \
      | python3 -c "import sys,json;print('delivery-failure total=',json.load(sys.stdin).get('total'))"

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
