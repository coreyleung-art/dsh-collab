# 跨 Agent 通讯底座 v3 · 实测基线与二期决策材料（2026-10-02）

> 维护：星桥（session-fa1f9150）· 前身：v1（mechanisms-and-archaeology-20261001）、v2（official-baseline-v2-20261001）
> 本文性质：**实测基线记录 + 二期决策材料**。全部数字来自 2026-10-02 当天的通道实测与代码审查，非设计预期。
> 一期（断产因/清淤/建机制）已完成；本文开启二期（文档 → 重启窗口 → 服务器中继归位）。

---

## 1 · 实测通道矩阵（2026-10-02 全通道实测）

| 通道 | 实测结果 | 证据 |
|---|---|---|
| Tailscale 直连 mac-mini 黑板 8792/8803 | ✅ **主用** | MBP 自述订阅 `100.120.203.20:8803/events`；我侧注入器 `mac-mini-inbox-watch.py` 读 `127.0.0.1:8792`；今天全部卡片实时闭环靠它 |
| 服务器 8792 中枢黑板 | ✅ 通（副本/注册/心跳在用） | E2 注册表 3/3 online、hb-fwd 30s 镜像、双写副本回读一致 |
| 服务器 8803 中枢 SSE | ✅ 通 | 只写中枢键 → 订阅端 2s 内收到事件（实测 sse-probe） |
| 服务器 8791 bus receive | ✅ 通（鉴权在岗） | 带 X-Webhook-Token → `{ok:true,task:null}`；无 token → 401 |
| 服务器 8791 bus send | ❌ 我侧 401 | 同 token POST /bus/send → `unauthorized`（发送凭据缺口，D3） |
| 服务器→本机镜像 sync-from-central | ⚠️ 域白名单裂口 | servertest 键写中枢后本机 404；DOWN_PREFIXES 只镜像 i9/mbp 域，mac-mini 域被防回声排除（D2） |
| 跨机 agent_send（短 id / 完整 id） | ❌ 一律 queued | 两形态实测均 `queued, targetLive:false`，75s+ 未消费（D4 边界） |

**结论**：今天的端到端闭环是「Tailscale 直连主用 + 服务器镜像/注册/信封兜底」。设计文档（convergence-plan-v2）写「服务器=跨设备唯一中继」，**与实测不符**——D1 拓扑决策见 §4。

---

## 2 · 注入时机语义（双时刻模型，实测）

每条 agent-bus 消息有两个时刻，**落盘 ≠ 注入**：

| 时刻 | 含义 | 实测例 |
|---|---|---|
| `time` | 消息落盘 agent-bus.json（发件人发出时刻） | 06:42:38 |
| `ackedAt` | 注入收件人上下文、被 claim 的时刻 | 06:43:33（=用户发消息触发新回合的同一秒，5 条消息全部同一时刻） |

- **注入发生在回合构造时**：运行时在每次回合开始把队列待处理注入一次性 flush 附加（这就是「发消息之后才看到注入」的原因）。
- **wake=inject（I7）不为此开新回合**：收件方空闲时消息一直排队，直到自然回合（用户输入/其他唤醒）。
- **reply_required=true 应触发唤醒**（MBP 已采纳约定并做实测判据）：我侧 agent-way 的唤醒路径**尚未实现**（待重启窗口，见 §7-②）。
- 时延公式实测：通道本身 <1s（黑板写→bus 插入 57ms）；总时延 = 收件方回合状态主导（实测 155s、47s~249s 全为等待回合）。

---

## 3 · 边界确认（成文）

1. **agent_send 是单机进程内设施**：目标不在本宿主进程活跃会话集合 → 一律 queued（与 id 形态无关）。跨机可达通道只有黑板（双写两板）与服务器 bus 信封。此边界 v3 起明文。
2. **发卡规范**（2026-10-02 事故后固化为工具）：from/to 一律完整 session id；to 必填（漏 to = 对端 central-inbox 白名单不注入 = 静默失败）；key 首段纯小写；notes/collab/ 类双写两板+逐板回读断言；bus 通道的 BUS_FROM 用白名单设备/角色名（与黑板卡规则不同，两套分开表述）。
3. **活性判定口径统一为心跳 payload ts**（G5）：键体 ts 会被 hb-fwd 镜像刷新（伪新鲜），注册表 status 由 hb-fwd 按 payload ts 判定并附 hb_age_s 审计字段（v1.1 已落地）。

---

## 4 · 服务器拓扑：实测 vs 设计（D1 决策材料，待用户批）

| | 方案 A：明示双轨（改文档） | 方案 B：真唯一中继（改实现） |
|---|---|---|
| 定位 | Tailscale 直连主用（实时、低延迟），服务器=镜像/注册/信封/兜底 | 跨设备消息一律经服务器 8792/8791，设备只连服务器 |
| 改动 | 改架构文档 L2 措辞为「中继兜底+注册+镜像」；双轨纪律成文 | sync 防回声改造（§5）+ bus send 凭据 + 设备守护全改连服务器 + 端到端验收 |
| 收益 | 零改动、承认现状、本地快 | 与「服务器唯一中继」设计一致；设备间不依赖 Tailscale |
| 风险 | 服务器挂时 Tailscale 兜底仍在（现状已如此）；文档与实现对齐 | 服务器 1G/2 核成为单点；Tailscale 直连优势（8ms 低延迟）被绕远 |
| 我的倾向 | **方案 A**：实测已证明双轨工作良好（R031 通讯永续：服务器挂→本机照常）；把服务器从「唯一中继」重新定位为「跨网兜底中继+注册+信封」，更符合资源治理（不制造单点） | — |

**★ 2026-10-02 定稿：用户实践裁决 = 方案 A（明示双轨）**。依据：①「只连服务器」联合验收实证四通道段可用（bus 0.13s/黑板 1.04s/镜像 34s/SSE 数秒）——服务器兜底能力成立；②用户指示「测完即恢复旧通道」=Tailscale 直连主用是既定事实；③funnel 根治与通道规则 v2 均在双轨框架下落地。服务器定位正式为「跨网兜底中继 + 注册 + 信封 + 镜像」，不再是「唯一中继」。

---

## 5 · 两个服务器侧修复方案（D2/D3，待批后执行）

**D2 sync-from-central 防回声按域排除 → 改按 from 判断**
- 现状：`DOWN_PREFIXES`（i9/mbp 域）+ `SELF_PREFIXES`（mac-mini 域排除）→ MBP 只写服务器的 notes/mac-mini/ 卡永远不会镜像到本机。
- 修法：镜像判定改为「value.from 解析到本机任一身份 → 跳过（防回声）；否则镜像」，键域不再作为判据。验收：写一张 from=MBP 的 notes/mac-mini/ 测试卡到中枢 → 本机 ≤5s 出现镜像（当前 404 为负对照）。

**D3 bus send 凭据**
- 现状：GET /bus/receive 带 X-Webhook-Token ok；POST /bus/send 同 token 401。
- 排查路径：SSH 服务器查 bus-bridge 的 send 鉴权配置（/opt/comm-layer，startbrige.pem）；或问 MBP 侧发送凭据（他今天 send 成功过）。
- 验收：POST /bus/send（from=mac-mini, target=mac-mini）→ 200 → device-daemon ≤5s 转写黑板 → 会话注入 → 闭环计时。

**服务器通道端到端验收程序（修复后执行）**
1. MBP 断开 Tailscale 直连 mac-mini（模拟：只保留到 106.53.214.108 的路由）。
2. MBP 只写服务器 → 我方计时收到（bus 信封 ≤5s / 黑板镜像 ≤5s）。
3. 我方只写服务器 → MBP 计时收到（他订阅 8803）。
4. 恢复直连，全链路回归。

---

## 6 · 版本注册（D8，E2 schema v2 草案）

现状：跨设备组件版本全靠手工互问（今天 node-bridge v1.4.0 就是这样从心跳 payload 里读出来的）。
草案（沿用 node-kit-standardization-design-v1.md 的 E2 v2 方向）：

```json
data/discovery/agents/<dev>.services = {
  "node-bridge": {"version": "1.4.2", "ts": 1790895118},
  "dsh-tools": {"version": "1.12.2"},
  "plugins": {"agent-bus": "1.5.6", "central-inbox": "0.2.1"}
}
```

- 写入方=心跳代理（hb-fwd/端侧注册器），与 sessions 同键同写；读侧一次 GET 拿全矩阵。
- 验收：hb-fwd 升级后，读任一设备注册表可回答「各组件版本」，不再互问。

---

## 7 · 二期排期与验收指标

| 步骤 | 内容 | 验收指标 |
|---|---|---|
| ① 文档 v3 | 本文档（已完成即交付） | 本文 §1-§6 齐备 |
| ② 受控重启窗口 | A6 裸标签修复（identity-variant-map 接入 + 未知标签放行+日志告警）；agent-way reply_required→唤醒；bb-card-send/launchd-scan 挂载 profile；11 个轻量 launchd job bootstrap | post-restart-acceptance 6/6 + 五形态探针 5/5 拦 + MBP 发 reply_required 卡 → 我无用户输入被唤醒 |
| ③ 服务器中继归位 | D2 防回声改造 + D3 send 凭据 + 端到端验收（§5 程序） | 断 TS 直连后互发互收 ≤5s/≤5s，全程计时留痕 |

**依赖用户批准**：D1 方案选择（我倾向 A 明示双轨）；重启窗口时间；launchd 恢复清单（11 个轻量 + bad-review-scheduler 三选一 + kb.watcher/watchdog 频率）。
