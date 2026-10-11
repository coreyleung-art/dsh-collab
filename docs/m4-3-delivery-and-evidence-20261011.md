# M4③ 交付与证据件 · 投递可见性（queued / expired）

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **锚点依据**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3` · **§14.4 M4③**
> ★ **本件是交付证据件，不是裁定**；★ **不宣布任何事项已闭合**（S3 不可自审）；★ 效力档位 **L1（已记录）**

---

## 一、★ 先更正锚点的一处**证据范围**（判定方向不变，理由须换）

锚点 M4③① 判 ❌，其证据为 `grep QUEUE_TTL_MS` + `sed -n '1305,1326p'`（只看了 `flushQueue`）。
**但 ③① 的判据文字是**「`queued` 在**输出面（卡面/日志/返回体）**显式标『未达』」—— **三面**。本线逐面复现：

| 面 | 判据 | 实测 | 依据（未编辑） |
|---|---|---|---|
| **返回体** | 须显式标「未达」 | ★ **成立** | `lib/index.js:1676-1683`：`if (res && res.status === 'queued') { res.queued_hint = … }`，逐字含「**queued 不等于「在投」**」「**agent_send 跨机不通——请改用节点别名或黑板卡（bb-card-send）**」 |
| **卡面** | 同上 | ❌ **不成立** | `dsh-plugin-bb-card-send` 全部 `.js`（core/index/selfcheck/gate/cli）grep `未达\|queued\|boarded\|delivered` ⇒ **0 命中** |
| **日志** | 同上 | ❌ **不成立** | `dsh-plugin-agent-bus/lib/index.js` grep `logLine\|appendFile\|writeFileSync` ⇒ **0 命中**；无统一日志（R006 ⑦ 未达） |

⇒ ★ **③① 应判「部分成立」**（返回体成立 / 卡面与日志不成立），而非整条 ❌。
★ **更正建议**：把 ③① 拆成**逐面判据**（三面各自给判定），否则一次 ❌ 会掩盖已成立的那面 ——
  后继会话照原文读，会**重做**已经存在的 `queued_hint`。已入台账 **D-016**。

---

## 二、★ ③② 的**精确版**：不是「没人看」，是「**有人看，但看的人不报警**」

锚点原文措辞是「字段**在**而**没人看**」。本线逐端复现后，精确形态是**两端各缺一半**：

| 端 | 实测（未编辑） | 缺什么 |
|---|---|---|
| **产生端** `~/dsh-plugin-agent-bus/lib/index.js` | `:1303 let expired = 0;` → `:1312 expired++;` → `:1327 **return delivered;**` ★ **`expired` 被算出，在 return 处丢弃** | 调用方**连数量都拿不到**（`/api/flush` 只回 `{ok:true, delivered:…}`，`:1916`） |
| **消费端** `com.dsh.cron.bus-triage` | 存在于 `launchctl`（exit 0）；plist = **每周一 09:00** `node …/bus-queue-triage/cli.js --scan --json`；输出**含** `total.expired`（实测 10-05 那次报 `expired:2001`） | ★ **无阈值判据**（主指标是 `expireable`）· **退出码恒 0** · 输出落 `StandardOutPath` ⇒ **每周覆盖**（size 恒 421 B，**无历史**） |

⇒ ★ **判据 ③②（`expired` 必须产生告警）结论不变：❌ 不成立**，但**理由更正**为：
  **「有读者，但读者不报警；且产生端把计数丢在 return 处」**。
  ★ 更正的重要性：若照原文「没人看」去修，会**新建一个读者**（重复劳动）；照精确版去修，只需
  **给已有读者加阈值与退出码**。

### 2.1 本线独立复现读数（流式扫全份，未整份载入）

★ 机器内存压力大（`swap used = 14,561 / 15,360 MB`），故用**分块流式**计数：

    ~/.dsh/agent-bus.json = 22.9 MB（23,971,287 B）
    ★ 扫过的面: 整份文件分块 4MB 全读，末块 64B 补扫
    status 总计 = 33661
      delivered  31241
      expired     2377    ← 静默 DLQ
      approved      30    （审批域）
      rejected       5    （审批域）
      queued         8

---

## 三、交付物：补上「**阈值 + 退出码 + 环比增量**」这一层

**新工具**：`scripts/bus-delivery-alert.py` · **v1.0.0** · 342 行 · 16,957 B
**J44 复用门**：✅ 通过（8 条命中**已显式裁决** `no-overlap`；四类候选逐一核过，见 §五）
★ **复用纪律**：**不重实现 bus 解析** —— 取数**唯一来源**是既有成熟工具
  `~/dsh-plugin-bus-queue-triage/cli.js --scan --json`（R006 齐备 · 原子写 · 备份回读 · 幂等）。

**三条判据（阈值单一处声明）**：

| # | 判据 | 默认阈值 |
|---|---|---|
| **A** | `queued > N` ⇒ 积压 | 50 |
| **B** | `expired` **环比上次增量** > N ⇒ 成批消息静默死亡 | 50 |
| **C** | `expireable > N` ⇒ 死形态消息滞留 | 0 |

**三态 + 退出码**：`OK`=0 · `ALERT`=1 · `UNDECIDABLE`=2 · 用法错=3。
★ **不可判 ≠ 无告警**：取数不可用 ⇒ `UNDECIDABLE`，**不降级成 OK**。
★ **首跑无基线 ⇒ Δ 标「不可判」**，★ **不把首跑读作「无增量」**（实测见下）。

---

## 四、实测（未编辑）

    $ /usr/bin/python3 scripts/bus-delivery-alert.py --lean4-check
      OK A · OK B · OK C · OK D · OK E · OK F
      => 6/6 pass, 0 FAIL        exit=0

    $ /usr/bin/python3 scripts/bus-delivery-alert.py --selftest
      OK  P1 正控 全在阈值内 ⇒ OK
      OK  N1 负控 queued 积压 ⇒ ALERT ['A']
      OK  N2 负控 expired 成批死亡 ⇒ ALERT Δ=400
      OK  N3 负控 死形态滞留 ⇒ ALERT ['C']
      OK  N4 负控 取数不可用 ⇒ UNDECIDABLE（不得冒充 OK）
      OK  N5 负控 首跑无基线 ⇒ verdict=OK 且 Δ不可判标记=True
      OK  N6 边界 Δexpired=0 ⇒ OK（判据非恒真）
      OK  LIVE 取数（经既有 triage --scan）⇒ queued=8 expireable=0 expired=2377
      => fails=0 undecidable=0 version=1.0.0        exit=0

    $ … --status      # 首跑
      判定: OK   queued=8 · expireable=0 · expired=2377 · Δexpired=None
      ★ Δexpired 不可判（无上次基线）—— 本工具【不】把首跑读作「无增量」
      exit=0
    $ … --status      # 二跑
      判定: OK   … Δexpired=0
      exit=0

    state: data/ops/bus-delivery-alert-state.json = {"expired":2377,"queued":8,"delivered":31241,"at":…}
    log:   logs/bus-delivery-alert.log = "status verdict=OK alerts=0 {"q": 8, "e": 2377}"

### 4.1 ★ 附带自证：门 D 抓住本工具自己的不一致

首版入口分派用了别名（`A = sys.argv` → `if "--selftest" in A:`），⑩ 门 **D FAIL**。
★ 依锚点 **§17.5「报不通过，不调参」**：**改代码，不改门** —— 分派改为直接写 `sys.argv`（与本机既有工具同形）。
★ 意义：**收紧后的门 D（D-010 那一次收紧）在真实场景中立刻抓到了新代码的同类不一致**，
  不只是构造夹具能红 —— 这是该收紧**有效**的一条现网证据。

---

## 五、J44 复用门裁决留痕

    ⇒ 门：✅ 通过 —— 有 8 条命中，已显式裁决

| 候选 | 是否重复 | 理由 |
|---|---|---|
| `~/dsh-plugin-bus-queue-triage`（成熟工具） | **不重复** | 其主指标是 `expireable`（**可处置量**），`total.expired` 只是**同级上下文数字**；**无阈值、无退出码语义**。★ 本工具**以它为唯一数据源**组合调用 |
| `scripts/post-restart-acceptance.py:104-106` | **语义相反** | 它有 `check("A2 expired 已回收", expired >= 1500, …)` —— ★ 这是**地板判据**（证 TTL 在回收＝机制活着），本工具是**增长告警**；且它是一次性重启验收脚本，非周期告警 |
| `dsh-plugin-guard/lib/*.js`（`cld_health_check` 所在） | **不覆盖** | grep `expired\|agent-bus\|queued` ⇒ **0 命中** |
| `scripts/` 下 alert/threshold/alarm 命名工具 | **不存在** | `ls scripts/ \| grep -iE 'alert\|warn\|threshold\|alarm'` ⇒ 空 |

---

## 六、★ 未证项与边界（**不得读作已证**）

| # | 项 | 状态 |
|---|---|---|
| 1 | ★ **③b 的「人的一半」** | **未交付**。本工具提供了**产生告警的机制**；★ **谁读它**属锚点 **W7.10「值守义务人」= 治理层（用户裁决）**，**非本线**。⇒ ★ **本线不主张 ③b 已成立** |
| 2 | **③a `queued` 在卡面/日志标「未达」** | ❌ **未做**（属 `dsh-plugin-bb-card-send` / `dsh-plugin-agent-bus` = **对方件**）。★ 返回体那半**已存在**（§一），**无需重做** |
| 3 | **③c 两路闭环**（`verify-delivery` 类工具接入发送路径） | ❌ **未做**（改 `agent-bus` = 对方件） |
| 4 | **③d 真达率 ≥95%** | ★ **不可判**（锚点同判；缺两路闭环口径） |
| 5 | **本工具是否被排进 cron** | ★ **本线不做**（改 launchd = 需登记 + 属主）。★ 本线**不主张**它已在运行 |
| 6 | **本件全部结论** | ★ **本线自测，无独立 verifier** ⇒ 按 S3 **不得记 `closed`** |

---

## 七、★ 交出的收紧类提案（**待属主/用户批**）

| # | 提案 | 落点 | 判据 |
|---|---|---|---|
| **P-M4③-1** | `flushQueue()` 的 `expired` **不再丢弃**：`return {delivered, expired}`（或至少落一行日志） | `~/dsh-plugin-agent-bus/lib/index.js:1327` | 调用方（`/api/flush`）**能拿到 expired**；负控：造 1 条超期 ⇒ expired 计数**可见** |
| **P-M4③-2** | **给已有读者加阈值与退出码**（★ 不是新建读者）：`bus-queue-triage --scan` 增 `--alert-if expired-delta>N`，非零退出 | `~/dsh-plugin-bus-queue-triage/cli.js` | 造 Δ ⇒ 退出码非 0；`bus-triage-cron.log` 改 **append** 以免每周覆盖丢历史 |
| **P-M4③-3** | 或：把 `bus-delivery-alert.py` **排进 cron**（本线已交付工具，只需接线） | `~/Library/LaunchAgents/`（**须登记**） | 按 §4.6/R036 流程；★ 本线**不自行接线** |
| **P-M4③-4** | ③① 判据**逐面拆分**（返回体/卡面/日志 三面各一判） | **锚点下一版** | 见 §一；已入台账 **D-016** |

---

## 八、复跑块（★ 本节所有会变的数字，一条命令全出）

    # [1] 静默 DLQ 现状（★ 流式，勿整份载入：本机 swap 压力大）
    python3 - <<'PY'
    import re,os
    p=os.path.expanduser("~/.dsh/agent-bus.json")
    pat=re.compile(r'"status"\s*:\s*"([a-z-]+)"'); c={}; buf=""
    with open(p,encoding="utf-8",errors="replace") as f:
        while True:
            ch=f.read(4*1024*1024)
            if not ch: break
            buf+=ch; safe=buf[:-64] if len(buf)>64 else ""
            for m in pat.finditer(safe): c[m.group(1)]=c.get(m.group(1),0)+1
            buf=buf[-64:]
    for m in pat.finditer(buf): c[m.group(1)]=c.get(m.group(1),0)+1
    print(c)
    PY
    # [2] 告警层三态（0=OK 1=ALERT 2=UNDECIDABLE）
    /usr/bin/python3 ~/dsh-collab/scripts/bus-delivery-alert.py --status
    # [3] 告警层自证（1 正控 + 6 负控 + 1 冒烟；须 fails=0 且 undecidable=0）
    /usr/bin/python3 ~/dsh-collab/scripts/bus-delivery-alert.py --selftest
    # [4] 产生端是否仍在 return 处丢弃 expired
    grep -n 'return delivered;' ~/dsh-plugin-agent-bus/lib/index.js
    grep -n 'let expired = 0' ~/dsh-plugin-agent-bus/lib/index.js
    # [5] 消费端现状（是否仍是每周覆盖、无阈值）
    launchctl list | grep -i 'bus-triage'; grep -c 'expired' ~/dsh-collab/logs/bus-triage-cron.log
    stat -f '%Sm size=%z' -t '%F %T' ~/dsh-collab/logs/bus-triage-cron.log
    # [6] 返回体那半（③①）是否仍在
    grep -n 'queued_hint' ~/dsh-plugin-agent-bus/lib/index.js | head -3
    # [7] J44 留痕回读
    python3 ~/dsh-collab/scripts/j44-reuse-gate.py --check bus-delivery-alert.py

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
