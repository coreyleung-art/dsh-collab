# 分工文档 · 外部（CU 实验台线）修什么 ⨯ 内部（接任星桥）修什么

> **出件**：2026-10-10T07:26:00+08:00（`date` 实读）
> **出件人**：CU 实验台线（Claude Code 会话 · **本线是索引的 writer**）
> **依据**：本线《执行度审查》`docs/execution-audit-anchor-v5-20261010.md` · 星桥 `docs/pending-backlog.md` B8/B9/B10 · 锚点 §7.9/§10 · 各件 `writer` 字段实读
> **效力**：**分工草案**。凡涉归属争议处均标「待裁」，本线不自行裁定。

---

## 〇、分界的真实判据（★ 先把话说清楚，免得按「文件 vs 运行时」粗分而分错）

分界**不是**「谁动文件、谁动进程」，而是两条：

1. **谁的产物谁修** —— 每件都有 `writer` 字段，实读为准。
2. **能否观测活体** —— 需要活体 session / 活体工具表 / `/reload` 才能看见或验证的，归**内部**执行；判断归**外部**。

按此，实测到的 `writer`：

| 件 | writer（实读） | ⇒ 归 |
|---|---|---|
| `data/registry/continuity-index.json`（索引） | **外部第三方（Claude Code 会话 · CU 实验台线）** | **外部（本线）** |
| `docs/…plan-v5-20261010.md`（锚点） | **星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4`** | **内部** |
| `data/registry/state-registry.json` | `session-e317d6ab-…` | **内部** |
| `data/registry/gcr-gate-tool-delivered.json` | `session-e317d6ab-…` | **内部** |
| `tools/beacon-check.py`（C5） | 索引自述「C1/C3/C5 由外部第三方建立」 | **外部（本线）** |
| `devices/dsh-plugin-context-survival/`（v0.12.1） | 星桥线产品（wiring plan 署 `session-e317d6ab`） | **内部** |

> ★ **本线结构性不能做**（不是不想，是不能）：改 CLD preset · 重启 CLD · 运行插件活体代码 · 观测活体 session。
> 若要本线破例（如跑一次 `--selfcheck`），须**用户在该次任务显式授权**。

---

## 一、外部（CU 实验台线）修的 —— **全部可在离线完成**

### A1 索引本体 `data/registry/continuity-index.json`（我是 writer，B8/B9 已明确路由给我）

| # | 修什么 | 现状证据 |
|---|---|---|
| A1.1 | **B9 两段同步**：`waves[C].note` 仍写「C4/C6/C7 未做」（10-09 口径），而 `items` 段 C6/C7 已 `in_flight` | 只同步了 `items`，没同步 `waves` ⇒ **只读 waves 的人低估进度** |
| A1.2 | **B8 `updated_at` 合理域**：一律 `date` 实读，禁估算 | 实测曾写出 `2026-10-11T00:20:00` ⇒ **超前约 19h**；本线自己也犯过同类错（`csx-mount-verification-v2` 写未来 24.2h） |
| A1.3 | **C2 证据指针改指 v5** | 证据仍为 `…v4-20261009.md` ⇒ 停在**已被取代**的上一版 |
| A1.4 | **C1 补 `verifier` 字段** | C1 记 `closed_with_evidence` 而**无 `verifier` 字段** ⇒ 与 §5.1「未证不得记 closed」冲突（星桥索引 note 已自陈「待裁」） |
| A1.5 | **`waves[S]` 与 `state-registry` 对立的本线侧** | 本线记 `in_flight`；星桥侧 `state-registry` 记 `blocked`。**两份都要动，各动各的**（见 B6） |

### A2 我的工具 `tools/beacon-check.py`（C5）—— **B10 的补判据落这里**

星桥 B10 实测：`beacon-check.py --net` 对该族**全绿**，属「**漏配却显示通过 —— 可信性检查本身不可信**」。补三条 + 一条：

| # | 补什么 | 治谁 |
|---|---|---|
| A2.1 | `waves` / `items` **两段 state 一致性** | B9 |
| A2.2 | `updated_at` **合理域**（不得晚于当前时刻 **+ 先校验 RFC 3339 规范形 `±HH:MM` 带冒号**——否则判据自身会在解析处崩） | B8 |
| A2.3 | `closed_with_evidence` **项须有 `verifier` 字段** | A1.4 / C1 |
| A2.4 | **黑板指针抽检不得无声 SKIP**：未开 `--net` 时把 C1 标成**显式未抽检**而非混在 PASS 里 | 本线审查实测：`beacon-check` 对 C1 报 SKIP，而 C1 的证据**恰恰就是黑板键** ⇒ 它的证据从未被抽检过 |

> ★ **只写一份判据**：这三条**实现在 `beacon-check.py`**（被检对象是索引＝我的产物）；`gcr-gate.py` 的 **G-CR18** 行**调用**它，**不重写**——两处各写一份正是 B9 的病根（同源两端分头演进）。

### A3 外部核验（本线的本职，不是附加）

- **锚点**：锚点头部自署「★ **verifier: 待第三方复核** —— 本件由起草人自行升版，按 S3「不可自审」**不得由本人裁定成立**」⇒ 本线是该角色的**天然人选**。
- **星桥交付物**：Wave S 八件、C1–C7、各登记卡 —— 本线做**静态/账本层**核验（代码、纯断言、账本格式、指针可解）。
- **产出**：审查台账（已出第一份）。

### A4 登记卡 / 黑板卡

`data/registry/<key>` 双板写 + 回读断言（`tools/bb_dualwrite.py`）。
**本次审查的卡尚未出**——用户本次仅授权 `docs/` 台账，卡待令。

### A5 `tools/floodgate.py` 定性（**须先等用户答**，见 §三）

答完后由本线落卡并回填 Wave 1/2 进度。

---

## 二、内部（接任星桥）修的

### B1 锚点本体 `docs/…plan-v5-20261010.md`（他们起草）

| # | 修什么 | 现状 |
|---|---|---|
| B1.1 | **§10 计数**：表头写「WBS（**30 项**）」，实列 **39** 个唯一 W 编号（6+8+10+3+6+6） | 与 P27 同族（判据/计数与事实不符） |
| B1.2 | **§7.9 计数**：「十五条」vs 实列 **17**（`gcr-gate.py` 已登记此不符） | 同上 |
| B1.3 | **G-CR18 判据措辞**与 §10 的 S5 描述对齐（S5 名仍是「G-CR 十五条校验脚本」） | 同上 |

### B2 插件 `dsh-plugin-context-survival`（**现 v0.12.1**）

| # | 修什么 | 依据 |
|---|---|---|
| B2.1 | **③ 召回接线**：把 `csx_recall` 的 `execute` 换成 `ledgerForUse` + `recall` | `docs/k6-wiring-plan.md` §三（含目标代码） |
| B2.2 | **`enableGuard` 置 true** | 现为 `false`（守只测量）；**须在 ③ 接线之后**，否则会话被压缩却无召回路径 ⇒ 破 I5 |
| B2.3 | **工具文案同步**：`implemented:false` / `coreStatus.wired:false` 接线后须改 | wiring plan §三铁律；「本会话已犯过一次工具契约滞留」 |

> ★ wiring plan §六 仍写「`implemented` ❌ false —— 三件接线一件都没做」，而 `lib/index.js` 的 ① ② **已在 07:10 落码** ⇒ **该文档已过期约 12 分钟**，接任者先以代码为准。

### B3 C4 自启动注入 —— **改 CLD preset**

锚点 §10 明写：「**需改 CLD preset**，**外部第三方不代做**」⇒ 唯一结构上只能内部做的项。

### B4 端到端三验（**只有活体可做**）

| 判据 | 内容 |
|---|---|
| **正控 1** | 触发前后 `totalTokens` **严格下降** |
| **负控 2 并存半** | 官方 `compaction-basic` 同时在线，本守卫拒动时官方**零变化** |
| **负控 3 投递半** | **事件流里真出现** `compaction/notice`（不是看返回值） |

★ 三项**各自独立报**，不得由一项通过推断另一项。
★ 失败处置：读数不降 ⇒ **真缺陷**，按 R030 回报原始读数，**不自行调参**。

### B5 重启 / `/reload`

热重启优先（R035 不杀框架）；`POST http://127.0.0.1:31888/reload`（G-CR11 要求：**先沙箱验证**，或「不用即安全」）。

### B6 `data/registry/state-registry.json`（他们的 writer）

- Wave S 记 `blocked`（「只见设计，未见建成证据」）而索引记 `in_flight`（「工具面已交付」）——**该卡 `source` 自称派生自索引却与索引相反**；
- C6 镜像字段 `continuity_index_state: "open"` 而索引已 `in_flight`。

---

## 三、用户裁（两侧都动不了）

| # | 待裁 | 为什么只能你裁 |
|---|---|---|
| C1 | **`floodgate.py` 定性**：是 W1.2/W1.4/W2.1/W2.4 的既有实现（⇒ **Wave 1/2 进度须重估**），还是与计划无关的旁支？ | 该件 docstring 自称 `Token bucket / RFC 1363` · `Circuit breaker…熔断` · `SPILLWAY…泄洪`；但**无任何登记卡认它**。是「东西在、账上没有」，只有你知道它当初为何而建 |
| C2 | **独立 verifier 唤醒授权** | 锚点已列候选（照录）：**守灯 `session-9910d4b2`**（名册席位#4，C1–C7 核验员）· **独立复核员 `session-4d0e75cf`**（未参与本线建构，理论上最干净）· **司库 `session-2a15e6b1`**。**均离线，唤醒须授权** |
| C3 | **本线破例授权**（如需要）：本线默认不跑插件代码 / 不起服务 / 不重启 CLD | 用户可在该次任务显式授权 |

---

## 四、★ 交叉制衡规则（S3「不可自审」的落地方式）

这条线**已经在互相复核了**，规则不是新造，是**把既成事实写下来**：

| 环节 | 执行 | 核验 | 实例（已发生） |
|---|---|---|---|
| 锚点 | 星桥起草 | **外部复核** | 锚点自署「verifier: 待第三方复核」 |
| 索引 | **外部 writer** | **星桥复核** | 星桥 B8/B9/B10 = **星桥发现了我的错**（`updated_at` 超前 19h · 两段不一致 · 我的门看不见自己） |
| 星桥交付物 | 星桥 | **外部核验** | 本线审查发现：Wave S 两卡对立 · §10 计数 30≠39 · `review-tracker.items=[]` |
| 活体端到端 | **星桥执行** | **外部核验其原始输出** | 待做 —— ★ 这是「写操作与观测分离」（trae:E20）：**星桥做写，外部看原始读数**，判断才在外部 |

★ **关键**：活体验证**不是**「星桥自己跑完自己判」——星桥跑，**原始输出（命令 + 未编辑输出 + 退出码）交外部**，由外部裁定。这样才不违 S3。

---

## 五、交接接口（按此格式交，否则退回）

| 交什么 | 格式 | 谁交谁 |
|---|---|---|
| 活体验证原始读数 | **命令 + 未编辑输出 + 退出码**（`trae:E19`.7），禁摘要 | 星桥 → 外部 |
| 索引状态变更 | `data/registry/continuity-index.json` 的 `items`/`waves`，`updated_at` **`date` 实读** | 外部 → 星桥复核 |
| 锚点升版 | **四件同批**：① 锚点 ② 索引 ③ `~/.dsh/continuity-last-version` ④ 续接提示词（缺一则 `beacon-check` 自红） | 星桥 → 外部复核 |
| 任一「已完成」声称 | **不得**在无独立 verifier 时记 `closed_with_evidence`（§11 六者缺一不得记） | 双方 |

---

## 六、现在就能并行开工的（互不阻塞）

**外部（离线，今天可做）**：A1.1 → A1.2 → A1.3 → A1.4 → A2.1–A2.4 → A4 卡
**内部（需活体）**：B2.1 ③ 接线 → B2.3 文案同步 → B2.2 `enableGuard` → B4 三验（原始输出交外部）
**用户裁完后**：A5（floodgate）· C2 唤醒 verifier

★ **先做 A2 比先做 B2 更值**：A2 通电后，本线审查里发现的那一族（**校验全绿而事实已变**）当场变红——否则内部改一步，外部看不见一步。

---

## 附录：归属判定的依据（原始命令）

```bash
# writer 字段（§〇 表）
python3 -c "import json;print(json.load(open('data/registry/continuity-index.json'))['writer'])"
#   → 外部第三方（Claude Code 会话 · CU 实验台线）· 经用户 2026-10-09 授权建立
python3 -c "import json;print(json.load(open('data/registry/state-registry.json'))['writer'])"
#   → session-e317d6ab-5302-4b33-b095-947983ba16f4

# 锚点起草人 + 自署 verifier 状态（§A3）
sed -n '6,7p' docs/distributed-agent-network-governance-plan-v5-20261010.md
#   → 起草: 星桥第二任 session-e317d6ab-…
#   → ★ verifier: 待第三方复核 —— 按 S3「不可自审」不得由本人裁定成立

# 候选 verifier（§C2）
grep -n '候选 verifier' docs/distributed-agent-network-governance-plan-v5-20261010.md
#   → 守灯 session-9910d4b2 · 独立复核员 session-4d0e75cf · 司库 session-2a15e6b1

# C4 的结构性约束（§B3）
grep -n 'C4 自启动注入' docs/distributed-agent-network-governance-plan-v5-20261010.md
#   → 需改 CLD preset，外部第三方不代做

# B8/B9/B10（星桥登记，§A1/§A2 的直接依据）
grep -nE '\*\*B(8|9|10)\*\*' docs/pending-backlog.md

# 插件版本（§B2）
python3 -c "import json;d=json.load(open('devices/dsh-plugin-context-survival/package.json'));print(d['name'],d['version'])"
#   → dsh-plugin-context-survival 0.12.1   （★ wiring plan 写 v0.11.1，已过期）
```

---

> **本件是分工草案，不是授权书，也不是达标判定。**
> 凡标「待裁」处须用户裁定后生效；本线**不自行择一动手**。
> 归属以各件 `writer` 字段实读为准——若与本文不符，**以文件为准并回报本文漂移**。
