# M4② 交付与证据件 · 通道登记分母活体实测 + 三表关系审计

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **锚点依据**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3`
> **锚点条目**：§14.4 **M4② 解除条件 ②c**「登记表**分母由活体实测生成**（不得手写、不得只读矩阵文件）」+ **②a 具名未登记通道全部登记**
> ★ **本件是交付证据件，不是裁定**；★ **不宣布任何事项已闭合**（S3 不可自审）；★ 效力档位 **L1（已记录）**

---

## 一、交付物

**新工具**：`scripts/channel-denominator.py` · **v1.1.0** · 395 行 · 20,295 B
**J44 复用门**：✅ 通过（12 条命中**已显式裁决** `no-overlap`；裁决理由：四类候选逐一核过且域不同，见 §五）
**性质**：★ **只读审计** —— 不写黑板、不改插件、不改矩阵、**不登记任何变更单**

| 能力 | 判据 |
|---|---|
| **活体分母** | 真跑 `drift-scan --json` 取运行时实际执行过的检查项（不再抄矩阵文件、不再抄文档） |
| **三面采集** | 声明面（矩阵）· 活体面（drift 运行时）· 可变更面（gate 冻结枚举，**只读源码解析**） |
| **三态判定** | `MATCH` / `DIVERGENT` / `UNDECIDABLE`；退出码 **0 / 1 / 2**；任一面不可判 ⇒ 整份不可判，**不冒充通过** |
| **负控** | `--selftest` **7 条负控** + 1 正控 + 2 冒烟，全部走**同一条报告代码路径**（`build_report`） |
| **R006** | ② `--selfcheck` · ⑥ 版本单一来源 · ⑦ 统一日志 · ⑩ `--lean4-check` 六项 A–F |

---

## 二、★ 主结果：三表关系（真实读数，未编辑）

    $ /usr/bin/python3 scripts/channel-denominator.py --status
      判定: DIVERGENT
      分母: 声明(矩阵) n=11 · 活体(drift) n=12 · 可变更(gate) n=7 · 有效并集 n=12

      ── 同一面的两口径 ──
      ★ 仅声明（被过滤）: 无
      ★ 仅活体（未登记/运行时追加）: ['bus-8791 token 权限']

      ── ★ 跨面：可观测性 vs 可变更性（两者不可互相替代）──
      交集 矩阵∩gate n=5 : ['board-central', 'board-local', 'bus-8791', 'sse-8803', 'tailscale-direct']
      ★ 仅矩阵（被监测但【变更不可表达】）n=6 :
          ['device-daemon', 'e2-registry-services', 'funnel-public', 'hb-fwd', 'node-bridge', 'sync-from-central']
      ★ 仅 gate（可变更但【未被监测】）n=2 : ['launchd-daemons', 'local-agent-bus']

      ── ★★ 制度死锁（红的 ∧ 不可经门变更）──
      当前为红的通道: ['funnel-public']
      ★ 死锁通道: ['funnel-public']

      声明取值: version=2026-10-02 注释键=['_comment_l3'] ★带 owner 字段的声明项=无（矩阵无 owner 字段）
      活体取值: scannedAt=2026-10-10T20:11:05.923Z reported_total=12 driftCount=1
      exit=1

---

## 三、★ 三项实质发现

### 3.1 **「分母」实测有三个互不相同的口径**（②c 的直接对象）

| 口径 | 值 | 来源 | 问题 |
|---|---|---|---|
| 文档口径 | **9 项** | `docs/agent-comm-portal-20261002.md` §0 | ★ **陈旧** |
| 文件口径 | **11 键**（+1 注释键 `_comment_l3`） | `lib/channel-matrix.json` 的 `matrix` 子对象 | ★ **少数一项** |
| **活体口径** | **12 项** | `drift-scan --json` 的 `rows` | 第 12 项 `bus-8791 token 权限` 为**运行时追加**（`kind: file-perm`） |

⇒ ★ **只读矩阵文件会少数一项；只抄文档会多数三项**。②c 点名的正是这件事，**本工具即为该判据的机械化实现**。

### 3.2 ★★ **两张登记表不可互相替代** —— 锚点 M4② 判据口径不成立

锚点 M4② 判据 ② 原文：「至少登记在 `drift` 矩阵 **12** 项 **或** `channel_gate` 枚举 **7** 条**之一**」。

**实测反证**：两表**交集仅 n=5**，各自有对方没有的项 ⇒ 二者量的是**不同能力**：

| 表 | 量的是什么 | 实测规模 |
|---|---|---|
| `drift` 矩阵 | **可观测性**（监测什么） | 11 声明 / 12 活体 |
| `gate` 枚举 | **可变更性**（能对什么登记变更单） | 7 |

⇒ ★ **「登记在之一」使该判据失去鉴别力**：一条通道只要在任一表里就算「已登记」，**但它可能仍然无法被变更**。
⇒ ★ **更正建议（收紧类）**：判据须改为**双面**（可观测性 **∧** 可变更性），或显式声明二者分离并**各自给判据**。★ 本线**不改已放行的 v6.1**，先入台账 **D-013**。

### 3.3 ★★ **制度死锁**：红的通道 ∃ 不可变更集合

    ★ 死锁通道: ['funnel-public']

**决定性检验（未编辑输出）**：

    $ echo '{"channel":"funnel-public","action":"probe: 验证该通道是否可经门表达（不执行任何变更）", ...}' \
        | node ~/dsh-plugin-channel-gate/cli.js register --json
      {"ok":false,"error":"channel 不在冻结枚举: funnel-public。正确姿势：7 个合法通道
       local-agent-bus/board-local/board-central/bus-8791/sse-8803/tailscale-direct/launchd-daemons
       之一（portal §0 矩阵）","code":"UNKNOWN_CHANNEL"}
      exit = 1

⇒ ★ **结构性闭环**：**当前正在红的那条通道（`funnel-public`），恰是无法经合规范流程变更的那条。**
  任何人想修它 ⇒ 门口被拒（`UNKNOWN_CHANNEL`）；而 portal 附录 A 又写「**勿绕门**」⇒ **它不能被合法修复**。
  ★ 这与「红了 **7.5 天**无人修」的实相**互相印证** —— 但**不等同于**因果已证（见 §六 未证项）。

★ **附带**：`gate` 枚举 **7 条全部带 `owner` 字段**，而 `drift` 矩阵 **11 条声明项无一有 owner 字段**
   ⇒ 矩阵侧通道**无属主声明** —— 与锚点 **W7.10「值守义务人」**缺口同源。

---

## 四、★ ②a 的对象：`dsh-plugin-central-inbox`

**锚点 §18.6.3 待办 3 逐字**：
> `dsh-plugin-central-inbox` **至今不在任何登记表** ⇒ ★ **启动 MCP P0 前须先补登记**

**本线独立复跑（★ 报 0 须附扫过的面 —— 下表两张表都扫了，不是只看一张）**：

| 通道 | `drift` 矩阵 | `gate` 枚举 |
|---|---|---|
| `central-inbox` | **0** | **0** |
| `bb-sub` | **0** | **0** |
| `wake` | **0** | **0** |
| `card` | **0** | **0** |

★ **`bb-sub` 活体规模 = 8**（`launchctl list | grep -c 'bb-sub'`）；★ 但其**是否属「副作用跃迁方」不可判**
（锚点原文同判：「其既定职责为订阅落 inbox」）—— ★ **本线不代裁**。

★★ **执行权**：锚点 §18.6.3 的**节标题逐字为**「本节待办（**执行权不在起草人**）」+ 待办 3 明写「**启动 MCP P0 前须先补登记**」。
⇒ ★ **本线不自行登记**（不代裁归属 · 不改对方件；两张表分别在 `dsh-plugin-drift-scan` 与 `dsh` profile 内）。
⇒ **本线可给的是**：**收紧类提案**（登记 = 扩大覆盖 = 收紧）+ 精确的落点与判据 —— 见 §七。

---

## 五、J44 复用门裁决留痕（★ 「查了没」可事后核）

    $ python3 scripts/j44-reuse-gate.py --intent "…通道登记分母活体实测…" \
        --artifact channel-denominator.py --verdict no-overlap --note "…"
      ⇒ 门：✅ 通过 —— 有 12 条命中，已显式裁决

**四类候选逐一核过**：

| 候选 | 是否重复 | 理由 |
|---|---|---|
| `scripts/channel-audit.py` | ✗ **域不同** | 管**对外通道**（企微/飞书/钉钉，源 `~/.dsh/channels.json`），非 CLD 内部通道矩阵 —— **名字撞车但域不同** |
| `scripts/comm-invariant-audit.py` | ✗ | 管 I1–I7 通信底座不变量，不做分母/集合比对 |
| `scripts/channel-gate-weekly.py` | ✗ | 读 `channel-changes.jsonl` 做变更留痕周审 |
| `dsh-plugin-drift-scan/lib/core.js:183` | ★ **部分能力已在** | 它**已报**活体 `total` —— 但**无任何工具**把它与矩阵声明集、与 gate 枚举做比对（`grep -rln 'channel-matrix'` 在 `scripts/`+`tools/` **零命中**） |

---

## 六、★ 未证项与边界（**不得读作已证**）

| # | 项 | 状态 |
|---|---|---|
| 1 | **「不可变更」是否是「7.5 天无人修」的【原因】** | ★ **未证**（仅**结构性吻合**）。归因需另证；★ 本线**不做**因果断言 |
| 2 | **「活体通道」的完整集合** | ★ **本工具不声明覆盖**。它只能枚举 `drift-scan` 的 `rows`。`central-inbox`（插件）**不在该枚举内** ⇒ 工具**测不到**它 ⇒ ★ **本工具的输出不构成「无未登记通道」的证据** |
| 3 | **`bb-sub` 是否属跃迁方** | ★ **不可判**（锚点同判） |
| 4 | **`funnel-public` 502 的修法** | ★ **本线不出方案**（61044 服务身份与意图未查明；全库零引用）—— 见 `docs/m4-1-delivery-and-evidence-20261011.md` §五 D-012 |
| 5 | **本件全部结论** | ★ **本线自测，无独立 verifier** ⇒ 按 S3 **不得记 `closed`** |

---

## 七、★ 交出的收紧类提案（**待属主/用户批**）

| # | 提案 | 落点 | 判据 |
|---|---|---|---|
| **P-M4②-1** | 把 `dsh-plugin-central-inbox`（「卡 → 自动唤起会话」跃迁方）**登记进登记表** | 建议 **`gate` 枚举**（因为它有 `owner`/`blast` 字段位，且它本身就是**可以被改的东西**）；若归 `drift` 矩阵则需补 `owner` 字段 | 登记后 `channel-denominator --status` 的「仅活体/未登记」项**不含**该项；且**须配负控（造断 ⇒ 必红）** |
| **P-M4②-2** | **矩阵侧补 `owner` 字段** | `lib/channel-matrix.json` 的 11 项 | 每项有 `owner`；无 owner ⇒ 不得计入「已登记」 |
| **P-M4②-3** | **`funnel-public` 解除死锁**（二选一：把它加进 `gate` 枚举 **或** 明确宣告该通道停用并留痕） | `gate.js` 冻结枚举 / 矩阵 | 二选一完成后 `--status` 的「死锁通道」为空 |
| **P-M4②-4** | **判据更正**：M4② 判据 ② 由「**或**」改「**双面 ∧**」 | **锚点下一版** | 见 §3.2；已入台账 **D-013** |

---

## 八、复跑块（★ 本节所有会变的数字，一条命令全出）

    # [1] 三表关系总报告（主判据，带退出码：0=MATCH 1=DIVERGENT 2=UNDECIDABLE）
    /usr/bin/python3 ~/dsh-collab/scripts/channel-denominator.py --status
    # [2] 自证（1 正控 + 7 负控 + 2 冒烟；须 fails=0 且 undecidable=0）
    /usr/bin/python3 ~/dsh-collab/scripts/channel-denominator.py --selftest
    # [3] 约束门六项 A–F
    /usr/bin/python3 ~/dsh-collab/scripts/channel-denominator.py --lean4-check
    # [4] 三个口径逐一对表
    grep -c '矩阵' ~/dsh-collab/docs/agent-comm-portal-20261002.md          # 文档口径（陈旧）
    python3 -c "import json;d=json.load(open('$HOME/dsh-plugin-drift-scan/lib/channel-matrix.json'));print(len([k for k in d['matrix'] if not k.startswith('_')]))"
    /opt/homebrew/bin/node ~/dsh-plugin-drift-scan/cli.js --json | python3 -c "import sys,json;print(json.load(sys.stdin)['total'])"
    # [5] 死锁通道是否仍红 / 是否仍不可变更
    /opt/homebrew/bin/node ~/dsh-plugin-drift-scan/cli.js --json | python3 -c "import sys,json;print([r['check'] for r in json.load(sys.stdin)['rows'] if r['drift']])"
    echo '{"channel":"funnel-public","action":"probe","evidence":"probe","rollback":"不改动","blast_radius":"zero"}' \
      | /opt/homebrew/bin/node ~/dsh-plugin-channel-gate/cli.js register --json   # 期望 UNKNOWN_CHANNEL
    # [6] central-inbox 是否仍在两张表外（★ 两张表都要扫）
    for t in central-inbox; do echo "$t matrix=$(grep -c "$t" ~/dsh-plugin-drift-scan/lib/channel-matrix.json) gate=$(grep -c "$t" ~/.dsh/profiles/web/node_modules/dsh-plugin-channel-gate/lib/gate.js)"; done
    # [7] J44 留痕回读
    python3 ~/dsh-collab/scripts/j44-reuse-gate.py --check channel-denominator.py

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
