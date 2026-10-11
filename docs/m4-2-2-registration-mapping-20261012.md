# M4①② 【登记映射】—— 26 条具名 → `channel_gate` 冻结枚举的 7 类（2026-10-12）

> **出件**：星桥第二任 `session-e317d6ab`（mac-mini）· 2026-10-12T08:5x（+08:00）
> **依据**：锚点 v6.1 §14.4 M4①②（★ 判据逐字：「至少登记在 `drift` 矩阵 12 项 或 `channel_gate` 枚举 **7 条** 之**一**」）
> ★ 本件**不宣布已闭合**；★ **不代裁归属**（★ 假阳裁断权已请 `ext`）。

## 一、★★★ 重大重新定性（★ 本件最重要的发现）

★★ **`channel_gate` 的 7 条枚举是【类别】，不是【个体】。** 逐字：

```js
'local-agent-bus'  'board-local'  'board-central'  'bus-8791'
'sse-8803'         'tailscale-direct'  'launchd-daemons'
```

★★★ **其中 `launchd-daemons`（owner: launchd · blast: 本机守护）一类【已覆盖本机全部 launchd 服务】。**

### ⇒ 因此判据②出现两种读法，结论相反

| 读法 | 结果 |
|---|---|
| **按【类别】判** | ★ 26 条具名对象**均已落在 7 类之一** ⇒ 判据② **成立** |
| **按【个体】判** | ★ 26 条**全未作为个体登记** ⇒ 判据② **不成立** |

★★★ **⇒ 判据②本身需要论域细化**（★ 这与 `ext` 审查件指出的「`(a)(b)(c)` 两套定义未对账」同层）。
★ **本线初判（★ 不代裁）**：宜按【类别】判——★ 理由：★ 7 条枚举的 `blast`（爆炸半径）字段说明它本来就是**风险分级**，★ **而风险分级本来就应按类**。

## 二、★ 26 条 → 7 类 映射（★ 初判，★ 待独立方裁）

| # | 具名 | → 枚举类 | 理由 |
|---|---|---|---|
| 1 | `com.dsh.blackboard-mcp-sse` | `board-local` | 黑板 MCP SSE（:8810） ⇒ 本机黑板面 |
| 2 | `com.dsh.bb-sub.coordinator` | `board-local` | 黑板订阅（明确写着 bb-sub） |
| 3 | `com.dsh.bb-sub.device` | `board-local` | 同上 |
| 4 | `com.dsh.bb-sub.hr` | `board-local` | 同上（★ 业务线，但机制是黑板订阅） |
| 5 | `com.dsh.bb-sub.learning` | `board-local` | 同上 |
| 6 | `com.dsh.bb-sub.qa` | `board-local` | 同上 |
| 7 | `com.dsh.bb-sub.recovery` | `board-local` | 同上 |
| 8 | `com.dsh.bb-sub.supply` | `board-local` | 同上 |
| 9 | `com.dsh.bb-sub.xingduo` | `board-local` | 同上 |
| 10 | `com.dsh.learning-blackboard-sub` | `board-local` | 学习线订阅 |
| 11 | `com.dsh.hr.blackboard-server` | `board-local` | HR 黑板服务 |
| 12 | `com.dsh.hr.blackboard-subscribe` | `board-local` | HR 订阅 |
| 13 | `com.dsh.hr.event-bus` | `local-agent-bus` | ★ HR 事件总线（★ 归属待裁） |
| 14 | `com.dsh.agentsend-gate` | `local-agent-bus` | ★★ 发送门（跨会话投递） |
| 15 | `com.dsh.central-wake` | `board-central` | ★★ 中枢唤醒 ⇒ 跨设备 |
| 16 | `com.dsh.xingduo-wake` | `local-agent-bus` | 星多唤醒（本机） |
| 17 | `com.dsh.mac-mini-inbox-watch` | `local-agent-bus` | 收件箱盯盘 |
| 18 | `com.dsh.sb-mobile-bridge` | `tailscale-direct` | ★ 手机端桥（★ 假设走 tailnet，待核） |
| 19 | `com.dsh.comm-sync-up` | `board-central` | ★ 同步上行 ⇒ 中枢 |
| 20 | `com.dsh.comm-sync-down` | `board-central` | ★ 同步下行 ⇐ 中枢 |
| 21 | `com.dsh.bus-capture` | `bus-8791` | 总线采集（★ 采集面，非通道本体 — ★ 归属待裁） |
| 22 | `com.dsh.cron.bus-triage` | ★ 无 | ★★ **作业类，不是通道** —★ 本线初判：不入任何类 |
| 23 | `端口 :8792` | `board-local` | 本机黑板 |
| 24 | `端口 :8803` | `sse-8803` | 黑板 SSE |
| 25 | `端口 :8810` | `board-local` | 黑板 MCP SSE |
| 26 | `端口 :8791` | `bus-8791` | 总线 |

### 分布

| 枚举类 | 数 |
|---|---|
| `board-local` | 14 |
| `local-agent-bus` | 4 |
| `board-central` | 3 |
| `bus-8791` | 2 |
| `tailscale-direct` | 1 |
| `★ 无` | 1 |
| `sse-8803` | 1 |

## 三、★ 三态结论

- **✅ 成立**：★ 26 条具名对象可逐条归入 7 类枚举之一（★ **除 1 条初判不入类**：`com.dsh.cron.bus-triage` —— ★ 它是**作业**不是通道）。
- **❌ 不成立**：★ **「个体级登记」** —― ★ 索引/登记表里没有这 26 条的名字。
- **❓ 不可判**：★ ① **哪几条真属本网络通道**（★ vs 业务线/采集器/作业）—★ ★★ **已请 `ext`，本线不自裁**；★ ② **`sb-mobile-bridge` 是否走 tailnet** —★ 本线**未核**（★ 是假设）。

## 四、★ 下一步（★ 待独立方）

★ 本线**不代改枚举**（★ 7 条是 `ext`/原作者语义域）。★ **请 `ext` 裁**：
1. ★★ 判据②应按【类别】还是【个体】？
2. ★ 26 条里哪几条**不应入类**（★ 如 `cron.bus-triage`、`bus-capture`、`hr.*`）？
3. ★ 若按【个体】判 ⇒ ★★ **登记位容量（12+7=19）< 待登记对象（26）** —★ 那就得先决**是扩容量还是收论域**。

---

*★ 本件为【映射 + 三态】，不是最终裁定。★ 不声称已闭合。*
