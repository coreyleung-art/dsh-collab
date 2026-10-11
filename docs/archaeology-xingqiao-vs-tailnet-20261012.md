# 考古：xingqiao 与 tailnet 的设计关系（2026-10-12）

> **出件**：子代理 `136de40c-5ef3-4fba-b852-eb896435d7cc`（受星桥第二任 `session-e317d6ab` 委托）
> **落盘**：2026-10-12T02:2x（+08:00）· 星桥第二任代落（原子代理受 CLD 自重启影响未完成落盘）
> **效力档位 L1（已记录）** · ★ **不宣布任何事项已闭合**
> ★ 本线**逐条亲验**了本文的决定性引用（★ 未采信转述）

---

## 一、一句话结论

★ **「互补」在 2026-09-06 ~ 09-08 的分层口径下成立**；★ 但**同一天同一作者写下过「路由中枢冗余、不做」**；★★ 且存在多条「替代/弃用」证据
⇒ ★ **「自始至今稳定互补」不成立**；★ **「自始设计为可互换冗余」同样不成立**。

---

## 二、扫过的面

| 命令 | 读数 |
|---|---|
| `find docs/ -name "*.md" \| wc -l` | **616** |
| `ls *.md \| wc -l`（根级早期文档） | **109** |
| `find . -name "*.md" -not -path "./guard/*" -not -path "./.git/*" -not -path "*/node_modules/*"` | **3308** |
| `ls comm-server/` | **46 项**（★ 早期设计层在这里，不在 docs/） |
| `grep -rniI "tailscale" docs/` | **124 行 / 41 文件** |
| `grep -rniI "tailnet" docs/` | **33 行 / 13 文件** |
| `grep -rniI "xingqiao" docs/` | **87 行 / 36 文件** |
| `grep -rniI "funnel" docs/` | **139 行 / 29 文件** |
| `grep -rniI "内网穿透" docs/ *.md` | **0**（★ 该词在本仓不存在） |
| `grep -rniI "互补" docs/*.md comm-server/*.md *.md` | 20 行 / 20 文件 —— ★★ **零条**讲 xingqiao 与 tailnet |

★ **未扫**：`guard/backups/`（38,000+ 文件，按铁律跳过）· `.git/` · `*/node_modules/` · `docs/xdom-diff-20261012/` 的 .py/.diff

---

## 三、时间线（★ 逐条附 `文件:行号` + 逐字原文）

| 日期 | 文件:行号 | 逐字原文 | 说的是谁 |
|---|---|---|---|
| 2026-08-16 | `cld-server-mode-fix-20260816.md:40-41` | `> 排查陷阱：日志 \`trusted: \` 为空不代表没传 host —— 该行只打印自动收集的` / `> Tailscale/LAN IP（autoTrusted），\`CLD_TRUSTED_HOSTS\` 的 host 不显示。` | ★ **tailnet 首现**（面内最早） |
| 2026-08-16 | `dsh-platform-deliverables.md:23,27` | `## 3. 远程访问拓扑（Tailscale × remote-web-ui）` / `\| 反代入口 \| \`~/.cld/tools/dsh-tailnet-proxy.mjs\`（0.0.0.0:3081 → GUI 动态端口，WebSocket，自动跟随） \| launchd \`com.dsh.remote\`（KeepAlive）✅ \|` | tailnet = **远程访问反代入口** |
| 2026-08-17 | `device-orchestrator-role.md:18,31,52,68` | `\| 设备 \| OS \| Tailscale IP \| 状态 \| 算力 \| 定位 \|` / `- 定期探测在线状态（Tailscale status / ping / SSH 探活）` / `\| Tailscale 网络 \| 4 设备组网 \| ✅ 已有 \|` | tailnet = **设备私网直连 + 在线探测底座** |
| 2026-08-28 | `docs/memory-chain-vs-openchronicle-20260828.md:50` | `- **本机**：✅ 黑板跨 mac-mini/MBP/i9（Tailscale）` | tailnet = 跨设备黑板可达性承载（★ docs/ 内最早） |
| 2026-08-30 | `docs/blackboard-mcp-server-design-v1.md:21` | `- **SSE**（远程设备，经 Tailscale/授权）——复用黑板 8803 SSE 基础` | tailnet = 远程设备访问黑板的通道之一 |
| 2026-09-03 | `docs/comm-bridge-view-20260903.md:13,20,25` | `（Tailscale 隧道/黑板总线/agent-bus/SSH/向日葵远控/Funnel 公网/云桥/本地托管），` / `\| Tailscale 隧道 \| \`tailscale status\` 解析 peer 在线集（ICMP 会被防火墙误判，弃用 ping） \|` / `- 8 通道类型（颜色/图标）: tailscale🔵 blackboard🟣 agentbus🟣 ssh🟡 sunflower🟡 funnel🟢 cloud⚪ local◽` | tailnet = **与黑板并列的 8 条通道之一**（此时 xingqiao 尚未出现） |
| **2026-09-06 19:07** | **`comm-server/server-governance-v1.md:3,5`** | `> 2026-09-06 星桥起草 · 服务器：xingqiao.meetfunbp.com (106.53.214.108, Ubuntu 22.04)` / `> 状态：🟢 中枢已部署（systemd comm-server active）` | ★★ **xingqiao 首现（全仓最早）** |
| 2026-09-06 19:16 | `comm-server/dual-track-plan-v1.md:4,9,10` | `> 架构：**本机黑板主（8ms 低延迟）+ 中枢跨设备（40-180ms 公网）**` / `\| 本机 :8792 \| 8ms \| 本地低延迟主：central-inbox 注入/星台轮询/本机会话 \|` / `\| 中枢 :8792 \| 40-180ms \| 跨设备事实源：i9/MBP 互通、容灾备份 \|` | 中枢 = **跨设备事实源 + 容灾备份**（★ 该「双轨」是**本机板 vs 中枢**，非 Tailscale vs 中枢） |
| 2026-09-06 19:40 | `comm-server/architecture-diagrams-v1.md:12,13` | `☁️ 通讯中枢 xingqiao.meetfunbp.com（Ubuntu 22.04 · 2026-09-06 上线）` / `├── Prod 黑板 :8792/:8803（跨设备事实源/镜像）rust-blackboard v0.6.0` | 中枢 = 跨设备事实源/镜像 |
| 2026-09-06 22:28 | `comm-server/cross-device-arch-eval-v1.md:147,153,166,184,185` | `### 核心区分（重新评估的关键）` / `\| L2 消息传输 \| — \| ✅ 本地黑板域(发布-订阅) \| 消息必经服务器 = 唯一 SPOF + 违背自治；域路由已解 \|` / `- **消息路由中心化是危险的**（必经点 SPOF）——故服务器不做全量路由` / `- 本机黑板仍是 mac-mini 侧主黑板（8ms 本地）——服务器是全局发现+备灾+总线，非替代` | ★★ **反证锚点**：中枢**明确不做**消息路由 |
| 2026-09-06 22:40 | `comm-server/e2-registry-plan-v1.md:22,25,34` | `### B. 消息路由中枢（传输层中心化）—— 不做（低价值高风险）` / `2. 冗余：发布-订阅已解消息流（域直读零中间人）——路由中枢增量价值 ≈ 0` / `\| 消息路由中枢 \| 低 \| 高(SPOF) \| 高 \| ❌ 不做（域自治+bus 兜底）\|` | ★★★ **最硬反证**：中枢路由被判**「冗余」** |
| **2026-09-08 14:06** | **`comm-server/perpetual-comms-convergence-plan-v1.md:15,24,28`** | `\| 传输层 \| sync-up/down + Funnel + Tailscale \| ✅ \| 都是通道，无寻址/无送达保证 \|` / `[i9 agent] ──┼─ PUT/SSE ─> [xingqiao 服务器=唯一消息总线] ─ 路由 ─┤` / `1. **唯一消息中枢**：跨设备消息统一收口到 xingqiao（写 PUT 带信封 to/from/msgid，读走 SSE 订阅自己域）。` | ★★ 设计**翻转为「唯一消息总线」**；且把 Tailscale/Funnel 与 sync 并列称「**都是通道**」 |
| **2026-09-08 23:03** | **`comm-server/perpetual-comms-convergence-plan-v2.md:22,23,28,29`** | `\| L2 中枢 \| xingqiao 服务器 8792/8791/8803 \| **服务器（跨机、跨重启）** \| ✅ 存活 \| 跨设备消息唯一中继、E2 注册、outbox 持久化 \|` / `\| L3 通道 \| Tailscale / Funnel \| 网络层 \| — \| 设备间直连快道 + 公网下载 \|` / `完全存续于本体（mac-mini）**，不经任何网络、不经服务器。这是"本体通讯"，本地执行优先（R031）——**永不改为走服务器**（会引入无谓延迟与单点）。` / `2. **跨设备（MBP/i9/手机）的消息才走 L2 中枢。** 中枢的角色 = 跨机中继 + 持久化 + 送达保证，不是本机 agent 的替代。` | ★★★ **两者被分层的唯一权威出处**：中枢=L2，Tailscale=L3 |
| 2026-09-09 00:05 | `docs/distributed-agent-network-arch.md:25,34,37,40` | `mac-mini(主源) · MBP · i9(Windows边缘) · xingqiao(服务器)` / `\| bus 信封(可靠队列) \| xingqiao:8791 \| 跨设备任务/消息投递 \| 公网 106.53.214.108 \| ✅ \|` / `\| 实时 SSE \| 设备→mac-mini:8803 \| 黑板事件订阅 \| Tailscale \| ❌(走TS) \|` / `**判定分界**：可靠投递=bus 信封(公网)；实时黑板推送=TS 直连；两者独立——TS 断不影响 bus 信封(已实测)。` | ★ **分工最明确的一句**（各担一类）+ **可实测判据** |
| 2026-09-09 00:29 | `comm-server/server-degrade-discipline-v1.md:31-32` | `2. **禁多路径乱试**：黄灯 = 唯一降级路径「黑板域 notes/<node>/」留痕；红灯 = 停发本地缓存` / `   禁止 agent 自行尝试 Tailscale 直连/Funnel/其它通道当备胎` | ★★★ **反证**：Tailscale **被明文禁止当服务器的备胎** |
| 2026-10-01 | `research/cost-governance/local-comm-architecture-L1L2L3-20261001.md:12,32,38,42,52` | `> 服务器（L3）不做投递权威，只做中继 + 跨设备收敛点 + 健康裁决。` / `\| 权威 \| 本设备 L1 库 \| 双方各自 L1 + **幂等键** \| **仅**跨设备键 + 健康裁决 \|` / `\| 不做什么 \| 不跨 WAN \| 不搬**状态**，只搬**信封** \| **不做投递权威、不做 per-agent inbox、不做注入决策** \|` / `★ 但 L3 **必须**是「跨设备状态的单一事实源」与「健康裁决者」——这两件事**只能**在服务器做，...` | 中枢 = 中继+收敛点+健康裁决（★ 该文 **tailscale 命中 = 0**） |
| 2026-10-02 | `docs/agent-comm-substrate-v3-20261002.md:21,53,55,56,59` | `**结论**：今天的端到端闭环是「Tailscale 直连主用 + 服务器镜像/注册/信封兜底」。设计文档（convergence-plan-v2）写「服务器=跨设备唯一中继」，**与实测不符**——D1 拓扑决策见 §4。` / `\| 定位 \| Tailscale 直连主用（实时、低延迟），服务器=镜像/注册/信封/兜底 \| 跨设备消息一律经服务器 8792/8791，设备只连服务器 \|` / `\| 收益 \| 零改动、承认现状、本地快 \| 与「服务器唯一中继」设计一致；设备间不依赖 Tailscale \|` / `**★ 2026-10-02 定稿：用户实践裁决 = 方案 A（明示双轨）**...服务器定位正式为「跨网兜底中继 + 注册 + 信封 + 镜像」，不再是「唯一中继」。` | ★★★ **正式宣布原设计「唯一中继」作废** |
| 2026-10-03 | `docs/server-topology-dual-track-v1.md:8,19-20,36` | `**Tailscale 直连是主用通道；服务器（xingqiao）是「跨网兜底中继 + 注册 + 信封 + 镜像」，不再是「唯一中继」。**` / `\| 主轨（Tailscale 直连） \| tailscale-direct \| 跨设备直连会话、funnel 公网入口 \| 自动退向兜底轨 \|` / `\| 文档 L2 措辞（「唯一中继」→「兜底中继+注册+镜像」） \| ✅ 本成文即该措辞的正式载体；历史文档中的「唯一中继」为原设计前提的如实记录，不改写历史 \|` | ★ 中枢↔Tailscale **主次反转** |
| 2026-10-02 | `docs/comm-channel-rules-v2-20261002.md:29` | `\| 跨设备内容卡 \| 黑板双写（mac-mini 127.0.0.1:8792 经 Tailscale + 中枢 xingqiao:8792） \| 仅中枢（断 TS 时；sync v1.1 镜像收口） \| 不得只写单板（collab 类必须双写+回读断言） \|` | ★ 矩阵里**两者并列双写**，且**互为兜底** |
| 2026-10-02 | `docs/rules-architecture-map-20261002.md:74` | `1. **L3 Tailscale/Funnel 无专门规则**：只有 R031 提及。通道矩阵 v2 已把它列为通道，但无「L3 故障/降级」规则（现状依赖「服务器兜底」的隐式假设）。` | ★★ 分工是**隐式假设**，**从未成文为显式规则** |
| **2026-09-11** | **`docs/systemgraph-on-comms-server-plan-20260911.md:61-65,77`** | `**D. Tailscale-only（推荐用于"只要内部可达、零公网暴露"）**` / `- 做法：让服务器加入 tailnet（\`tailscale up --authkey=...\`），静态服务只绑 tailnet 地址。` / `- 需：**你提供 tailnet auth key**（或你手动登录一次）。` / `- 优：**零公网暴露**（蓝图不上公网）、无需改安全组、三端（mac-mini/MBP/i9）已在 tailnet。` / `**推荐组合**：**D（tailnet-only）+ 保留公网那份作为"外部可看的旧快照"**，或 **C（443+BasicAuth）** ...` | ★★★ **tailnet 被设计为「公网暴露」的替代手段（安全边界层）**，而非与中枢并列的消息通道 |
| 2026-10-08 | `docs/星桥-memory-inheritance-2026-10-08.md:1689` | `- 服务器状态：comm-server(Prod 8792) + comm-server-test(Test 8794) 双 active；公网 IPv4+域名通（IPv6 不通）；SSH 免钥（ubuntu + mac-mini ed25519）；禁 root 密码+禁密码认证；Tailscale 未装（用户喊停「先别搞 tailscale」，走防火墙放行方案）` | ★★★ **中枢加入 tailnet 的计划被用户喊停** |
| 2026-10-05 | `docs/星桥-memory-inheritance-2026-10-08.md:2836,2839` | `"帮我看看星台的通讯通道，能不能通过服务器完成中继而不是 tailscale 网络"`（★ 记为 user directive verbatim） / `StarBridge mobile app: server relay channel (public HTTPS instead of Tailscale), ...` | ★★★ **用户亲自提出：用服务器中继「而不是」tailnet** |
| 2026-10-08 | `docs/星桥-memory-inheritance-2026-10-08.md:1811` | `- 双路径分界（channel-map.py 实测）：实时黑板推送=Tailscale 100.x 直连；信封队列/心跳/注册=公网 106.53 服务器；本机 agent-bus=local` | 实证分工：**推送 vs 队列** |
| 2026-10-12 | `docs/deviation-ledger-20261011.md` D-072 | ★ 中枢 ufw **对 \`Anywhere\` 放行 `8792/tcp` 与 `8803/tcp`**；板监听 `0.0.0.0:8792`；`GET /data/` 无头 ⇒ 200；★ **中枢本身未登录 tailscale** ⇒ **不存在「靠 tailnet 隔离」这一层** | ★★★ 当前实现 |
| 2026-10-12 | `docs/deviation-ledger-20261011.md` D-074 | ★ 原设计「**8792/8803 仅白名单 IP**」+「**公网匿名 ❌ 拒绝**」 ⇒ **Anywhere 是漂移** | ★★★ 设计漂移 |

---

## 四、各自的设计职责（★ 逐字引用）

### 4.1 xingqiao / 中枢

**(a) 最早（09-06 19:16）—— 跨设备事实源 + 容灾备份**
`comm-server/dual-track-plan-v1.md:10`｜`\| 中枢 :8792 \| 40-180ms \| 跨设备事实源：i9/MBP 互通、容灾备份 \|`
`:46`｜`- 本机为主、中枢为镜像：以本机时间戳为准（写入先本机后推中枢）`
`:60`｜`- 中枢挂了：本机黑板独立可跑（双轨的天然容灾）`
⇒ ★ **此设计里中枢是「镜像」，本机才是主。**

**(b) 安全边界（同日 09-06）**
`comm-server/server-governance-v1.md:13`｜`约束0 访问层：SSH 仅密钥（root 禁用密码）+ 8792/8803 仅白名单 IP`
`:53`｜（攻击面矩阵末行）`\| 公网匿名 \| ❌ 拒绝 \| ❌ 拒绝 \| ❌ 拒绝 \| ❌ \|`
`:57`｜`D1 网络层：腾讯云安全组仅放行 {mac-mini/MBP/i9 出口 IP} × {8792,8803,22}`
`:131`｜`I5 安全组白名单最小化（不放开不必要端口/IP）`

**(c) 否决路由中枢（同日 09-06 22:40）** —— 见 §三，`e2-registry-plan-v1.md:22,25,34`
`comm-server/cross-device-arch-eval-v1.md:166`｜`- **消息路由中心化是危险的**（必经点 SPOF）——故服务器不做全量路由`
`:185`｜`- 本机黑板仍是 mac-mini 侧主黑板（8ms 本地）——服务器是全局发现+备灾+总线，**非替代**`

**(d) 翻转为「唯一消息总线」（09-08）** —— 见 §三
`comm-server/perpetual-comms-convergence-plan-v2.md:60`｜`### 2.2 结论：**不装 CLD，不装 LLM；服务器保持纯消息总线（无状态、低内存）**`

**(e) 收窄为「三件事」（10-01）**
`research/cost-governance/local-comm-architecture-L1L2L3-20261001.md:12`｜`> 服务器（L3）不做投递权威，只做中继 + 跨设备收敛点 + 健康裁决。`

**(f) 终局定位（10-02/03）**
`docs/server-topology-dual-track-v1.md:8`｜`**Tailscale 直连是主用通道；服务器（xingqiao）是「跨网兜底中继 + 注册 + 信封 + 镜像」，不再是「唯一中继」。**`

### 4.2 tailnet / Tailscale

**(a) 设备私网 + 远程访问（08-16/17）** —— 见 §三
**(b) 八通道之一（09-03）**｜`docs/comm-bridge-view-20260903.md:25`｜`- 8 通道类型（颜色/图标）: tailscale🔵 blackboard🟣 agentbus🟣 ssh🟡 sunflower🟡 funnel🟢 cloud⚪ local◽`
**(c) L3 通道 = 直连快道 + 公网下载（09-08）**｜`perpetual-comms-convergence-plan-v2.md:23`
**(d) 「都是通道，无寻址/无送达保证」（09-08）**｜`perpetual-comms-convergence-plan-v1.md:15`
★ 即：**在设计者眼里，Tailscale 与 sync-up/down、Funnel 同级 —— 是「通道」，不具备寻址与送达保证**（寻址/送达划给中枢）。
**(e) 变为主用（10-03）**｜`docs/server-topology-dual-track-v1.md:19-20`
**(f) 被提议作为中枢的【安全边界层】（09-11）**｜`docs/systemgraph-on-comms-server-plan-20260911.md:61-65`

---

## 五、互补假说：支持 / 反证

### 5.1 支持

- **S1（最强）**：`perpetual-comms-convergence-plan-v2.md:22-23` 的 **L2/L3 分层表** + `docs/distributed-agent-network-arch.md:34-37,40` 的**可实测判据**：

| 通道 | 端点 | 用途 | 路径 | 断 TS 可用 |
|---|---|---|---|---|
| bus 信封（可靠队列） | `xingqiao:8791` | 跨设备任务/消息投递 | 公网 `106.53.214.108` | ✅ |
| 实时 SSE | 设备 → `mac-mini:8803` | 黑板事件订阅 | Tailscale | ❌（走 TS） |

⇒ ★ **在「分层」口径下，互补【成立】**；`:40` 明写「两者独立」。
- **S2**：`星桥-memory-inheritance-2026-10-08.md:1785`｜`- 用户定义架构：「区分 Tailscale vs 服务器路径」「消息管理/分发路由做多设备污染隔离」`
- **S3**：`comm-channel-rules-v2-20261002.md:29` 通道矩阵把两者写成「主用 + 兜底」成对（★ 但同时是反证，见 R3）
- **S4**：`architecture-diagrams-v1.md:28,37`（「旧通道保留=降级备灾」）—— ★ 但说的是**本机板 vs 中枢**，非 Tailscale vs 中枢
- **S5（既是支持也是弱点）**：`rules-architecture-map-20261002.md:74`｜★ 分工是**隐式假设**，**从未成文为显式规则**

### 5.2 ★★ 能推翻「互补」的证据（★ 主动去找的）

- **R1（最硬）**：`e2-registry-plan-v1.md:25,34` —— ★ 中枢的**路由角色被判「冗余」、明确「不做」**（「路由中枢增量价值 ≈ 0」）。★★ **若「中枢=消息中继」是它的设计职责，则设计者亲口说该职责冗余 ⇒ 与「两者分工互补」直接冲突。**
- **R2**：`server-degrade-discipline-v1.md:31-32` —— ★★ **Tailscale 被明文禁止当服务器的备胎**。★ 这是「冗余假说」的直接反证，**同时也是「互补假说」的削弱**（互补意味着可协同降级，这里禁止协同）。★ 该条约 3.5 周后被 10-02 的「双轨兜底」完全反转。
- **R3**：`comm-channel-rules-v2-20261002.md:29` 的「兜底通道」列 = `仅中枢（断 TS 时）` ⇒ ★ **两者互为兜底（可替代）**。
- **R4**：`agent-comm-substrate-v3-20261002.md:53,55` —— ★ 存在一个被**正式评估**的「用服务器完全取代 Tailscale」方案（方案 B：`跨设备消息一律经服务器 8792/8791，设备只连服务器`，收益逐字 `设备间不依赖 Tailscale`），虽最终选 A。
- **R5**：`星桥-memory-inheritance-2026-10-08.md:2836` —— ★★ **用户本人提出「用服务器完成中继而不是 tailscale 网络」**。
- **R6**：`systemgraph-on-comms-server-plan-20260911.md:61-77` —— ★★ **tailnet 被设计为「公网暴露」的替代手段（安全边界层）**，★ **而不是与中枢并列的另一条消息通道** ⇒ ★★ **与「L2 消息中继 vs L3 直连通道」是两套不同关系。**
- **R7**：`grep -rniI "互补"` 全仓 **20 行 / 20 文件，零条**讲 xingqiao 与 tailnet（★★ **该二元对立是提问框架，不是文档里的既有表述**）。

---

## 六、设计漂移（★ 设计 vs 现在跑的）

| 维度 | 最早设计 | 当前实现 | 证据 |
|---|---|---|---|
| **中枢暴露范围** | **仅白名单 IP**（`{mac-mini/MBP/i9 出口 IP} × {8792,8803,22}`）· `公网匿名 ❌ 拒绝` · 不变量 `I5 白名单最小化` | **`ufw` 对 `Anywhere` 放行 8792/8803**·板绑 `0.0.0.0:8792`·`GET /data/` 无令牌 **200** | 设计：`server-governance-v1.md:13,53,57,131`；实现：D-072 |
| **中枢是否在 tailnet 内** | **曾计划加入**（09-11 `D. Tailscale-only`，推荐为「零公网暴露」） | ★ **未登录**（`tailscale status` 仅 4 节点，无 xingqiao） | `systemgraph-on-comms-server-plan-20260911.md:61-65` / D-072 |
| **中枢消息角色** | 09-06 19:16 `镜像`（本机为主）→ 09-06 22:40 `❌ 不做`（冗余）→ 09-08 `唯一消息总线` → 10-01 `中继+收敛点+健康裁决` → 10-02 `兜底轨，不再是唯一中继` | **兜底轨** | 5 处，见 §三 |
| **Tailscale 主/备** | 09-03 八通道之一 · 09-08 `都是通道，无寻址/无送达保证` · 09-09 ★ **禁止当备胎** | **主轨**（`Tailscale 直连是主用通道`） | 见 §三 |
| **Funnel 是否公网可达** | 文档口径：公网可达（`经 Funnel 公网 URL 实测 200`） | ★ 实测 **`(tailnet only)`**，路径不含 8792 | D-066 |
| **谁是权威板** | 09-06：`本机为主、中枢为镜像，以本机时间戳为准` | 章程：`本机板与中央板**不自动互传**` ⇒ 需显式双写；实测键数 **中枢 6140 vs 本机 33625** | `dual-track-plan-v1.md:46` / `AGENT-NETWORK-CHARTER.md:12,17` |
| **中枢上是否跑 CLD/LLM** | `**不装 CLD，不装 LLM；服务器保持纯消息总线（无状态、低内存）**`（明确否决×2） | ★ 与设计一致（本线未发现反例） | `perpetual-comms-convergence-plan-v2.md:60,64,65` |

---

## 七、三态结论

### ✅ 成立

1. **xingqiao 作为设计对象的最早出处** = `comm-server/server-governance-v1.md:3`（2026-09-06，mtime 19:07，文件头自述 `2026-09-06 星桥起草`）。
2. **tailnet 最早出处** = `cld-server-mode-fix-20260816.md:41`（2026-08-16）；`docs/` 内最早 = `docs/memory-chain-vs-openchronicle-20260828.md:50`。⇒ ★ **tailnet 早于 xingqiao 约 3 周出现。**
3. **两者被显式分层的唯一成文出处** = `perpetual-comms-convergence-plan-v2.md:22-23`（L2 中枢 / L3 通道）⇒ **在该分层口径下「互补」成立。**
4. **存在分工的可实测判据**：`distributed-agent-network-arch.md:40`。
5. **原设计的「服务器=跨设备唯一中继」已被正式作废**（2026-10-02 用户实践裁决）。
6. **曾有计划让中枢加入 tailnet**，且该计划**被用户喊停**；★ 且**卡点是「需你提供 tailnet auth key」**（09-11），★★ **至 2026-10-12 本线独立探明仍是同一卡点**（无 `tskey-` · CLI 无 `key` 子命令 ⇒ 需 admin）。
7. **当前实现中中枢未登录 tailnet**，且**对公网 Anywhere 开放 8792/8803 且读路径无鉴权**。
8. **Funnel 的文档口径（公网入口）与实测（`(tailnet only)`）不一致。**

### ❌ 不成立

1. **「两者自始至今是稳定的功能互补」**—— 因为 09-06 22:40 中枢路由职责被判「冗余·不做」，09-09 Tailscale 被禁止当备胎，10-02 又反转为主/兜底双轨。★ **四次定位变更，跨 26 天。**
2. **「两者自始被设计为可互相替代的冗余」**—— 因为 09-09 明文**禁止** Tailscale 当服务器的备胎；可替代性主张是 10-02 才作为**被否决的备选方案**出现。
3. **「xingqiao 最早定义在 `docs/`」**—— ★ **首现与全部早期定义都在 `comm-server/`，不在 `docs/`。** ★★ **只扫 `docs/` 会漏掉 09-06~09-09 的全部最早设计层**。
4. **「`docs/` 是 2026-10-12 才入版本控制」**（★ 本线任务书的前提）—— 实测最早入库提交为 **`d7a6f29`（2026-09-09）**。
5. **「两词在文档中被写成『互补』或『互为冗余』」**—— 见 R7。

### ❓ 不可判（★ 及缺什么证据）

1. **2026-09-06 之前**设计者心里两者的分工。★ 面内最早 comm-server 件为 `health-protocol-v1.md`（09-04 02:21），`grep -ci "xingqiao\|tailscale"` = **0** ⇒ ★ **面内无，不等于不存在**。
2. **「互补」还是「冗余」是本问题的正确二分吗。** ★ 证据显示存在**第三种关系**：★ **层级上的从属** —— tailnet 曾被提议作为中枢的**安全边界层**（09-11 tailnet-only 部署），此时二者不在同一功能轴上，**既非互补也非冗余**。
3. **用户「先别搞 tailscale」这句喊停的确切范围** —— 是只否决「本次 SystemGraph 部署用 tailnet-only」，还是否决「中枢加入 tailnet」作为长期路线。★ 该记录为**二手压缩产物**（记忆段 compact 产物），**非原始裁决件**。
4. **Funnel 是否曾经真的公网可达** —— 二者可同时为真（曾 `funnel` 后降为 `serve`），★ **未找到状态变更留痕**。
5. **「唯一中继」是否曾是被批准的正式设计** —— 批准文本**未给完整原话逐字引用**（只给转述）。

---

## 八、复跑命令块

```bash
cd /Users/coreyleung/dsh-collab

# ── 0. 面盘点 ──
find docs/ -name "*.md" | wc -l            # 616
ls *.md | wc -l                            # 109
ls comm-server/ | wc -l                    # 46  \u2190 \u2605 早期设计层在这里
grep -rniI "tailscale" docs/ | wc -l ; grep -rliI "tailscale" docs/ | wc -l   # 124 / 41
grep -rniI "xingqiao"  docs/ | wc -l ; grep -rliI "xingqiao"  docs/ | wc -l   #  87 / 36
grep -rniI "\u4e92\u8865" docs/*.md comm-server/*.md *.md | wc -l            #  20（全部与本题无关）

# ── 1. 时间线取首（\u2605 必须再核文件头自述日期）──
grep -rliI "xingqiao" . --exclude-dir=.git --exclude-dir=guard --exclude-dir=node_modules \
  | while read f; do stat -f "%Sm %N" -t "%Y-%m-%d %H:%M" "$f"; done | sort | head -3
head -3 comm-server/server-governance-v1.md      # 自述 2026-09-06 → 一致

# ── 2. 分工的「唯一成文出处」与可实测判据 ──
sed -n '20,34p' comm-server/perpetual-comms-convergence-plan-v2.md
sed -n '30,41p' docs/distributed-agent-network-arch.md

# ── 3. \u2605 反证四连 ──
sed -n '22p;25p;34p' comm-server/e2-registry-plan-v1.md            # 中枢路由「冗余…❌ 不做」
sed -n '31,32p'       comm-server/server-degrade-discipline-v1.md  # 禁止 Tailscale 当备胎
sed -n '49,59p'       docs/agent-comm-substrate-v3-20261002.md     # 方案 B「不依赖 Tailscale」
sed -n '2836p;2839p'  docs/\u661f\u6865-memory-inheritance-2026-10-08.md    # 用户原话「而不是 tailscale 网络」

# ── 4. \u2605 设计漂移：曾经打算让中枢加入 tailnet ──
sed -n '61,65p;77p' docs/systemgraph-on-comms-server-plan-20260911.md
sed -n '1689p'      docs/\u661f\u6865-memory-inheritance-2026-10-08.md   # 用户喊停

# ── 5. \u2605 设计 vs 实现：白名单要求 ──
sed -n '13p;53p;57p;131p' comm-server/server-governance-v1.md
ssh -i ~/.ssh/id_ed25519 ubuntu@106.53.214.108 'sudo ufw status numbered'

# ── 6. git 面（\u2605 更正本线任务书前提）──
git log --reverse --format="%h %ad %s" --date=short --all | head -1      # d7a6f29 2026-09-09
git log --format="%h %ad" --date=short --all -- docs/ | tail -1          # d7a6f29 2026-09-09
```

---

## 附：三条方法论副产品（★ 供后续复用）

1. **`comm-server/` 是被忽略的早期设计地层。** `docs/` 里最早讲中枢的是 **09-06 23:20**，而 `comm-server/` 里是 **09-06 19:07** —— ★ **同一晚早 4 小时**，且 `dual-track-plan-v1` · `e2-registry-plan-v1` · `cross-device-arch-eval-v1` · `perpetual-comms-convergence-plan-v1/v2` · `server-degrade-discipline-v1` **全部只在 `comm-server/`**。★★ **只扫 `docs/` 会得到一份方向性错误的时间线。**
2. **`mtime` 必须与文件头自述日期交叉核对后才可用**；本次 4 个「最早」候选全部核对一致。
3. **同一个晚上会写出互相矛盾的架构结论**（09-06 19:16 `本机为主、中枢为镜像` vs 09-06 19:40 `中枢=跨设备事实源`；09-06 22:28/22:40 `不做路由中枢` vs 09-08 `唯一消息总线`）。★ **因此任何「原设计」的单点引用都不足以定性，必须给出同日的反向引用。**

---

*本件为【证据 + 三态判定】，不是最终裁定。★ 不宣布任何事项已闭合。*

---

# 补遗 · 第二轮换面重跑（2026-10-12 03:1x）

> **出件**：同一子代理 `136de40c-5ef3-4fba-b852-eb896435d7cc` 的**第二轮**（★ 换方法：★ **不再从 `docs/` 起搜，改为先建全量候选面**）
> **落盘**：2026-10-12T03:1x · 星桥第二任代落
> ★★ **本补遗【不改上文】** —— ★ 上文是**第一轮的如实记录**；★★★ **本补遗推翻其中一处结构性判断**。
> ★ 本线已亲验本补遗的关键读数（★ 见 §补四）。

## 补〇 · 两个元层面的坑（★ 影响任何复跑者）

**坑 1 · 自污染。** ★★ **本件（上一轮报告）已被落盘，成了文档库内的文件**：
```
$ ls -la docs/archaeology-xingqiao-vs-tailnet-20261012.md
-rw-r--r--  1 coreyleung  staff  27919 Oct 12 02:15
$ grep -ciI "xingqiao\|tailscale\|tailnet" docs/archaeology-xingqiao-vs-tailnet-20261012.md
63
```
★ ⇒ 它使 `docs/` 从 **616 → 623**、`xingqiao` 计数 **+19 行** ⇒ ★★ **两轮计数【不可直接比】**；★ 本轮已**全部剔除自指件**。
★★ **本线的责任**：★ 这是我按「探明就落档」指令落盘造成的 —— ★ **落盘件会反过来成为下一轮的面。**

**坑 2 · 假阳性陷阱（★ 必做，否则会误判「最早 xingqiao」）。**
★ 板 KV 里 `data/investigate/lbs-poi-alignment`（ts `2026-09-01T09:03:36`）含 `xingqiao` —— ★★ **但原文是字段名 `for_xingqiao`（指【角色】「星桥」），不是服务器名** ⇒ **假阳性**。
★★ 另有方法学更正：★ **KV 的 `ts` 是【末次写】而非【首现】**。

## 补一 · ★★★★★ 本轮的钥匙：设计的起点【不叫 xingqiao】

★★ **它叫 `comm-server`，定案于 2026-09-03（用户定案），落笔于 2026-09-04T02:16:42 / 02:17:32** ——
★★★ **早于字面量 `xingqiao` 首现（09-06 19:07）【2 天 17 小时】。**

★ **新扫的两个面（第一轮完全没扫）**：
- ★ `data/blueprint/`（蓝图本体 · 8 个 .md）
- ★ `token-monitor/blackboard/snapshot.json`（★ **本机板全量 KV 66,273 键 + 时间戳**）

★★ **最早成文逐字**（`data/blueprint/agent-network/blueprint-agent-network-v1.3.md`）：
- `:5`｜`> 依据：research/agent-network-blueprint-candidate.md + **用户定案 2026-09-03**（永续通讯根治·彻底持久化工作流）+ comm-server-blueprint-task-1788459402432 + i9 失联教训（心跳假阳性/数据分叉/无自动健康 ack）`
- `:26`｜`- **comm-server**：通讯根治线（新·用户定案） — 独立 hub-spoke 通讯服务器：单一事实源 + 统一裁决健康 + 三端独立连接`
- `:35`｜`1. **通讯星型中心化**：黑板 :8792 在 mac-mini——i9/MBP 全连 mac-mini，mac-mini 异常 = 全网断`
- `:42`｜`- cs0-1 架构定案 [done] — hub-spoke：独立服务器中心，mac-mini/i9/MBP 各自独立连接；单一事实源 + 服务器统一裁决健康…；mac-mini 重启不影响 i9/MBP`
- `:57`｜`- cs3-1 mac-mini 接入 [todo] — 连 comm-server，**黑板降级为本地缓存/只读归档**`

★ **原始任务卡**（★ 从 KV 66,273 键中找到）：`notes/session-f38244df/comm-server-blueprint-task-1788459402432` ——
★ **板 `ts` 与【键名 epoch】均为 `1788459402432` = 2026-09-04T02:16:42**（★ 逐字相同）。
★ 其 `value.content` 逐字：
> `【用户要求】把跨设备通讯架构根治作为持久化蓝图项目推进（用户原话：彻底持久化工作流，别再每次手修）。`
> `①现状缺陷（用户亲自指出）：通讯星型中心化在 mac-mini 黑板 :8792——i9/MBP 都连 mac-mini，mac-mini 异常=全网断；...`
> `②用户方向（可行性已验证）：独立通讯服务器 hub-spoke——...；mac-mini/i9/MBP 三端各自独立连接；单一事实源 + 服务器统一裁决健康`
> `**③备选：i9 desktop-p8e7op1 在 Tailscale 直连可达（100.118.15.71，8ms，SSH22 开）——无独立服务器时先建机器直连通道 + 双心跳标准健康协议**`

★★★ **⇒ 在最早的任务卡里：中枢 = 【② 号方向】；Tailscale 直连 = 【③ 号「备选」】，前置条件是「无独立服务器时」。**

## 补二 · ★★★★★ 推翻上一轮的一处【结构性判断】

★ 上文 §七 判定：「**两者被显式分层的唯一成文出处 = `perpetual-comms-convergence-plan-v2.md:22-23`（09-08）** ⇒ **在该分层口径下「互补」成立**」。

★★ **本轮更正**：★★★ **更早（09-04）的成文不是「互补」，而是「主 + 备（带退役计划）」** ——
- `blueprint-agent-network-v1.3.md:43`｜`- cs0-2 备选方案评估 [done] — i9 desktop-p8e7op1（100.118.15.71，8ms，SSH22 开）——**无独立服务器时先建机器直连通道** + 双心跳标准健康协议`
- `:47`｜`- cs1-2 直连备选 [todo] — i9 机器直连通道（Tailscale 100.118.15.71 已验证可达）——**若服务器就绪则此线降级为 fallback 文档**`

★★ **⇒ 最早成文里，Tailscale 直连与中枢不是「各担不同功能的双轨」，★★★ 而是【同一条功能轴上的主方案与备选方案】，且备选明写了退役计划。**
★★ **⇒ 「互补」口径最早只见于 09-08（`channel-map.py` 的三分法），★★★ 晚于「主/备」4 天。**

★★ **另补：SOP 最早（09-04）就把中枢访问控制写成【仅 Tailscale/白名单】**
`blueprint-agent-network-v1.3.md:84`｜`3. 端口开放 + 访问控制(仅 Tailscale/白名单)`
★ ⇒ ★★ **这比 09-11 的 tailnet-only 方案又早 2 个月。**

## 补三 · ★★ 「双轨」的【原义】不是 xingqiao vs tailnet

★ `comm-server/dual-track-plan-v1.md:1` 标题自述 `# Comm-Server 双轨制接入方案 v1（cs3 · 用户选定）`，★ 而其「双轨」逐字是 `本机黑板主（8ms）+ 中枢跨设备（40-180ms 公网）`。
★ `channel-map.py:92` 又证 `("i9/MBP → mac 直连黑板", "tailscale", "100.120.203.20:8792")` —— ★ **tailnet 是【本机黑板那条轨】的传输手段**。
★★ **⇒「xingqiao vs tailnet 双轨」是 2026-10-02 才出现的【后起语义】。**

## 补四 · ★★ 本轮新增的三条正面材料（★ 第一轮未读）

**① 可核验的互补判据（三分法）** —— `comm-server/channel-map.py`
```
:8    tailscale: 对端 IP 属 100.x 网段 (tailnet)
:9    server:    对端 = xingqiao 106.53.214.108 (公网)
:124  判读: 实时消息(SSE/黑板直连)=tailscale; 信封队列/心跳/注册=server; 本机agent=local
```
**② 互备矩阵（★ 既是互补也是冗余）** —— `comm-server/migration-plan-v1.md`
```
:4    > 原则：**同步双轨、本地通道维持、备灾不抹旧**（R031 通讯永续 + Φ9 约束前置）
:12   I1 本地通道永不抹除（双轨并行，**非替换**）——中枢挂→本地照常
:63   | 服务器挂 | 服务器通讯层 | **本地 bb-sub + 本机黑板照常** | 自动 |
:64   | mac-mini 挂 | 本地黑板 | **服务器通讯层接管**（i9/MBP 直连中枢） | 需配置 fallback 地址 |
```
**③ 用户级原方向 D02（2026-09-08）** —— `data/registry/user-direction-scan-20260909-022441`
> `| D02 | 2026-09-08 | **区分 Tailscale vs 服务器路径**；消息管理/分发路由做多设备污染隔离 | done | 4 | 0 |`
★★ ⇒ **用户原方向就是「区分」，不是合并「互补」。**

## 补五 · ★★ 暴露漂移的记录★★【前移一个月】

★ 上文所引最早的暴露记录是 10-08 / 10-12。★★ **本轮在板 KV 里找到更早的两件**：
- ★ `data/registry/internal-docs-publicly-readable-access-control-invalid-20260910`（ts **2026-09-10T15:28:22**）
- ★★ `data/registry/central-blackboard-anonymous-public-write-20260913` —— 逐字：
> `"anonymous_write_proved": "从本机(公网)直接 PUT http://106.53.214.108:8792/<ns>/<key> → 200（data/registry 与 notes/ 两个命名空间各一次），DELETE 亦 200；探针键已删净（回读 404）"`
> `"sibling_service_has_auth": "同机 8791（总线桥）无 token 返回 401 —— 同一台机器上两个服务一个 401 一个敞开"`
> `"recommendation": "安全组收回「全部端口」，改为仅放行 80/443（...）；黑板自身加 token 或★ **改绑私网（Tailscale）** 是★ **设计层决定**，需用户裁"`

★★★ **⇒ 结论：★ 暴露面早在【2026-09-13】就被实测并写成卡，★★ 且当时就把「改绑 Tailscale」提为设计层选项** —— ★★ **本线 2026-10-12 的发现，是同一个问题的【第二次报告】，而不是首次发现。**

## 补六 · ★ 两条如实并列、不合并的活体事实

★ **① `/data/` 体积两次读数不同**：
```
第一轮：central /data/ ⇒ 200 size=15961831
本  轮：central /data/ ⇒ 200 size=8895504      （−7.07 MB）
```
★★ **⇒ 同一端点、同一命令、两次读数不同。★ 本补遗【不主张原因】**（★ 可能是键清理/回收/迁移），★ **仅如实并列登记** —— ★ 按章程不许两值合并成一句。

★ **② 本线的 curl 不是干净的外部视角**（★ 与台账 D-073 一致）：★ `route -n get default` ⇒ `interface: utun5`（代理/VPN 类）⇒ ★★ **「公网可达」的裁定应引台账的 tcpdump 第三方视角**（`eth0 In IP 120.230.80.3.9225 > 10.1.0.14.8792: Flags [S]`），★ **不得据本机 curl 单独下判**。

## 补七 · ★★ 最终表述（三态 · ★ 取代上文 §七 的单一结论）

★★ **在「2026-09-04 最早成文」口径下** ⇒ ★★★ **「互补」【不成立】**（当时是**主/备**，且备选带退役计划）。
★★ **在「2026-09-08 ~ 09-09 三分法」口径下** ⇒ ★★ **「互补」【成立】**，★ 且**用户原方向 D02 即要求「区分」**。
★★ **「自始至今稳定互补」** ⇒ ★ **不成立**。
★★ **「自始设计为可互换冗余」** ⇒ ★ **也不成立**（09-09 明文禁止当备胎）。

★ ⇒ ★★ **本线的「互补」直觉，在 09-08 之后的实现口径下是对的；★★ 但在【最早的设计意图】下，Tailscale 直连是【备用方案】—— ★ 这两件事同时为真。**

## 补八 · 复跑（本补遗新增部分）

```bash
cd /Users/coreyleung/dsh-collab

# ★ 钥匙：蓝图地层（比 docs/ 早 2 天 17 小时）
sed -n '5p;26p;35p;42p;43p;47p;57p;84p' data/blueprint/agent-network/blueprint-agent-network-v1.3.md

# ★ 板端 KV 原件（键名 epoch 与板 ts 逐字相同）
python3 - <<'PY'
import json,datetime
d=json.load(open("token-monitor/blackboard/snapshot.json",encoding="utf-8",errors="replace"))
st=d["state"]; print("KV 键数:",len(st))
k="notes/session-f38244df/comm-server-blueprint-task-1788459402432"
print("ts=",st[k]["ts"]); print(json.dumps(st[k]["value"],ensure_ascii=False,indent=1))
print("键名 epoch ->", datetime.datetime.fromtimestamp(1788459402.432).isoformat())
print("blueprint 板端 ts=", st["data/blueprint/agent-network"]["ts"])
PY

# ★ 互补/互备正证
sed -n '8p;9p;92,98p;124p' comm-server/channel-map.py
sed -n '4p;12p;63p;64p'    comm-server/migration-plan-v1.md

# ★ 暴露漂移（比上文所引早一个月）
python3 - <<'PY'
import json
d=json.load(open("token-monitor/blackboard/snapshot.json",encoding="utf-8",errors="replace"))
st=d["state"]
for k in ["data/registry/central-blackboard-anonymous-public-write-20260913",
          "data/registry/internal-docs-publicly-readable-access-control-invalid-20260910"]:
    print("="*60); print(k,"| ts=",st[k]["ts"]); print(json.dumps(st[k]["value"],ensure_ascii=False,indent=1)[:1000])
PY

# ★ 自污染复核
grep -ciI "xingqiao\|tailscale\|tailnet" docs/archaeology-xingqiao-vs-tailnet-20261012.md   # 63（衍生物）

# ★ 假阳性陷阱复现
python3 - <<'PY'
import json
d=json.load(open("token-monitor/blackboard/snapshot.json",encoding="utf-8",errors="replace"))
for k,v in d["state"].items():
    s=json.dumps(v,ensure_ascii=False)
    if "xingqiao" in s and (v.get("ts") or "").startswith("2026-09-01"):
        print(v.get("ts"),"|",k)   # → for_xingqiao（指角色，非服务器）⇒ 假阳性
PY
```

---

*★ 本补遗为【证据 + 三态】，★ 不主张已闭合。★ 上文 §七 的单一结论以本补遗 §补七 为准。*
