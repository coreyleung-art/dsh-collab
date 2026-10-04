# CLD 分布式智能体节点网络公约 v1.5（通道卫生 · 表达规范 · 角色沟通模型）
> 星桥 2026-09-09 · 用户定名「CLD 分布式智能体节点网络公约」· 各节点/角色共同遵守
> Lean4 契约化：本公约条文均配可执行断言（convention-lean4-check.py 校验），纸面条文 → 结构门
> 状态: v1.6（+§十四 节点投递可见性 L/M · 服务器 v0.3.7 已实施 · 校验器 31 项断言 全 PASS）

## 〇、Lean4 结构规范（本公约的机器可验证层）

本公约的每条规则都有对应**可验证断言**（G-C 前缀），由 `convention-lean4-check.py` 自动校验，
纸面条文不是"建议"而是"契约"——违反即 GATE FAIL，阻塞相关操作：

| 公约条款 | Lean4 断言 | 校验什么 |
|---|---|---|
| §1.2-1 自报身份 | G-C1 identity-self | 设备注册 via=self（禁他机代管身份） |
| §1.2-2 守护常驻 | G-C2 daemon-alive | 守护进程在跑（SSE 连接数≥设备数-1） |
| §1.2-3 无默认身份 | G-C3 env-no-default | DSH_NODE_ID 等身份 env 无默认值（部署门联动） |
| §1.2-4 队列零积压 | G-C4 queue-zero | bus/status queued=0 且无 processing 幽灵(>10min) |
| §1.2-5 断线兜底 | G-C5 reconnect-catchup | 守护断线重连后 receive 补拉（代码含兜底分支） |
| §1.2-6 token 私存 | G-C6 token-0600 | token 文件权限 0600 且不进日志 |
| §1.2-7 target 精确 | G-C7 target-scoped | receive/订阅带明确 target（禁空抢） |
| §2.1 信封格式 | G-C8 envelope-schema | send payload 含 to/text，action 命名规范 |
| §3.3 寻址 | G-C9 addressing | target=设备 + payload.to=角色（禁只给角色名） |
| §4 部署门 | G-C10 deploy-gate | 新脚本过 gate-deploy-check（漏变量门） |

Lean4 语义：`∀ 设备 d ∈ {mac-mini,mbp,i9}: convention(d) 满足 ⇒ d 可接入；∃ 断言失败 ⇒ GATE FAIL`。

---

## 一、通道卫生规则（服务器通讯治理）

### 1.1 通道分层与职责（谁走哪条路）

| 通道 | 端点 | 用途 | 路径 |
|---|---|---|---|
| **bus 信封**（可靠队列） | xingqiao:8791 | 跨设备任务/消息投递 | 公网 106.53.214.108 |
| **bus SSE 推送** | xingqiao:8791/bus/events | 服务器→设备实时推送（免轮询） | 公网 |
| **黑板** | 本机 8792 / 中枢 106.53.214.108:8792 | 状态/记录/域消息 | 本机 local / 服务器 |
| **实时 SSE** | 设备→mac-mini:8803 | 黑板事件订阅（TS 直连） | Tailscale |
| **心跳/注册** | hb-fwd → 中枢 | 设备存活宣告 | 公网 |

**判定分界**：可靠投递=bus 信封（公网）；实时黑板推送=Tailscale 直连；两者独立——
TS 断不影响 bus 信封（已实测）。**设备守护必须 SSE 订阅 bus/events（推），禁止轮询 receive 作主通道。**

### 1.2 设备接入七条卫生规则（对全部设备强制）

1. **自报身份**：设备启动须自注册（via:self），禁止他机代管注册身份（hb-fwd 仅心跳兜底）。
2. **守护常驻**：SSE 订阅 bus/events?node=<本机>，25s 无事件须主动重连（服务器 25s 心跳）。
3. **无默认身份**：DSH_NODE_ID 等身份 env 无默认值（部署门 G-D2 强制），缺失即报错退出。
4. **队列零积压**：任务处理后立即 /bus/reply ACK 清队；TTL 过期自动 failed；不得留 processing 幽灵。
5. **断线兜底**：SSE 断线重连后 receive 补拉一次（覆盖断线窗口），不得丢消息。
6. **token 0600**：X-Webhook-Token 私存 0600/等效，禁止黑板明文、禁止进日志。
7. **target 精确**：receive/订阅必须带明确 target，禁止空 target 抢拉他人任务（历史 bug）。

### 1.3 服务器通道健康检查

- 队列统计（bus/status）：queued 应≈0；processing 滞留 >10min = 幽灵任务需清理
- SSE 订阅者数：应 = 接入设备数（channel-map --live 校验）
- 心跳年龄：节点心跳 <90s 新鲜
- 巡检工具：channel-map.py（路径测绘）+ 守护日志（device-daemon.log 无异常重连）

---

## 二、表达规范（信封 + 黑板卡统一格式）

### 2.1 bus 信封格式（send 请求）

```json
{
  "from": "<device>:<agent>",      // 发件：设备:角色（如 "mbp:mbp-bus"）
  "target": "<device>",            // 收件设备：mac-mini | mbp | i9 | any
  "action": "<动词-对象>",          // 动作语义（小写连字符，如 order-sales-daily）
  "payload": {                      // 业务内容
    "to": "<角色名|agent-id|coordinator>",  // 设备内唤醒目标（角色映射表）
    "text": "...",                  // 消息正文
    "...": "..."                    // 业务字段
  },
  "ttl_sec": 3600                   // 过期秒数（默认 1h）
}
```

### 2.2 黑卡片格式（守护转写后，供 central-inbox 解析）

```json
{
  "key": "notes/<node>/bus-<action>-<task8>",
  "content": "[bus:<action>] <text>",
  "from": "bus:<device>",
  "to": "<角色名|coordinator>",     // central-inbox 按此精确唤醒
  "type": "bus-envelope",
  "_bus": {"task_id": "...", "from": "...", "action": "..."}
}
```

### 2.3 命名规范

- **设备 id**：mac-mini / mbp / i9（小写连字符）
- **角色名**：中文名（星桥/明鉴/司库…）——映射表 `~/.dsh/agent-role-map.json`
- **agent-id 全局唯一**：`<device>:<role>`（如 `mac-mini:星桥`、`mbp:mbp-bus`）——跨设备寻址用
- **action**：动词-名词 小写连字符（`i9-direct-verify`、`order-sales-daily`）
- **task_id**：服务器 UUID；黑卡片 key 用前 8 位做短引用

---

## 三、角色沟通模型（设备内 vs 跨设备）

### 3.1 设备内角色沟通（同机 agent）——**不走服务器**

```
星桥 ⇄ 明鉴/守灯/老登...（同在 mac-mini CLD）
  通道: agent-bus（agent_send/threads）+ 本机黑板 127.0.0.1:8792
  存续: 本机进程内/本机黑板 —— 本地自治，永不改走服务器
```
- 规则：**同设备角色互发 = agent_send 直达 + 本机黑板**，零网络开销
- 适用：mac-mini 上星桥↔明鉴、MBP 上 mbp-bus↔资源中枢 等

### 3.1.1 设备内通讯治理细则（与跨设备治理对等 · 2026-09-09 补强）

**A. 何时用 agent_send（通道选择）**
```
agent_send 适用(同机定向):  明确对方角色 + 单点收件 + 需即时响应
黑板域 适用(同机异步/留痕): 状态登记/迭代报告/任务卡(供轮询/审计)
agent_broadcast 适用(同机): 仅协调者 且 真正需要全员知悉(如重启窗口)
agent_send 禁用于:          跨设备(走 bus 信封 G-C12 分界) / 纯登记(走黑板)
```

**B. 同机成本约束（Φ4：同机消息也占 token）**
- 同机 agent_send 亦有 token 成本（唤醒+注入）——**能黑板登记解决的不用 agent_send**
- 纯确认/ack 类：能静默则静默（同机无 G-C16 跨设备版，但同样防 ack 风暴）
- 一对多通知：优先**黑板域单卡**（读方自取），非 agent_broadcast 逐发（省放大）
- 群聊/线程放大：同机多角色线程同样按 G1-G4 收敛（参与者≈需知者）

**C. 广播收敛（防同机也乱广播）**
- **agent_broadcast/all=true 仅协调者可用**（星桥/司库），且限「重启窗口/全员裁决」场景
- 普通角色无广播权——定向 agent_send 或黑板卡
- 广播前自查：真需全员？能否黑板域单卡替代？——防止「内部广播本身也浪费 token」（用户 9/9）
- 广播审计：广播必留痕（thread 参与者），事后可查谁广播了什么

**D. 审计（设备内也留痕可溯源）**
- 同机重要协作（跨角色任务分派/广播/纠错）落本机黑板 notes/<domain>/（非内存态）
- agent-bus threads 即审计源（from/to/时间在 agent-bus.json 全量）
- 设备内无结构门可拦的（agent_send 直发）→ 靠 §D 审计 + 角色自觉；结构边界在跨设备层

**E. Lean4 断言（并入 convention-lean4-check.py）**
| 断言 | 校验 |
|---|---|
| G-C28 broadcast-scope | 广播白名单(仅协调者)配置存在 |
| G-C29 internal-audit | agent-bus.json threads 留存(审计源在位) |

### 3.1.2 设备内 vs 跨设备治理对等对照

| 治理项 | 跨设备(已详) | 设备内(本节) |
|---|---|---|
| 通道选择 | §3.2 信封 | §3.1.1-A agent_send/黑板 |
| 成本约束 | §6.2 每消息=信封+1唤醒 | §3.1.1-B 黑板替代/防ack风暴 |
| 广播收敛 | G1-G4 群聊 | §3.1.1-C 协调者专属+自查 |
| 审计 | comms-route-log | §3.1.1-D threads+黑板落痕 |
| 结构门 | G-C1~C27 | G-C28/C29(广播/审计) |

### 3.2 跨设备角色沟通——经服务器 bus 信封

```
发送方设备内角色 → 信封 from=<dev>:<role> target=<对端设备>
   → 服务器 bus 入队 + SSE 推送
   → 对端设备守护收信 → 转写本机黑板 notes/<dev>/ (payload.to=角色名)
   → central-inbox 角色映射 → 精确唤醒对端设备内目标角色
   → 目标角色处理 → (可经 bus/send 回发 from=<dev>:<role>)
```

### 3.3 寻址三层（一句话记）

| 想发给谁 | 写什么 | 走哪 |
|---|---|---|
| 同机角色 | agent_send(角色) | 本机 |
| 异机（知道设备） | bus send target=<设备> payload.to=<角色> | 服务器 |
| 异机（只知角色名） | bus send target=<设备> payload.to=<角色>（守护 relay 兜底） | 服务器 |
| 广播 | bus send target=any | 服务器 |

### 3.4 关键澄清（防混淆）

1. **设备 ≠ 角色**：设备是宿主（mac-mini/mbp/i9），角色是设备内的 agent 会话。
2. **发「设备」** → 该设备守护收 → 转黑板 → 唤醒默认/指定角色。
3. **发「角色」** → 必须连带设备（信封 target=设备 + payload.to=角色）；只给角色名无法路由（除非 relay）。
4. **角色映射表**是设备内概念（每设备自己的 agent-role-map）；跨设备寻址 = device:role 组合。
5. **i9 模式**：Windows 端守护收信转本机可读黑板域；回报走 bus reply（task 语义闭环）。

---

## 四、配套工具与落地

| 工具 | 作用 | 路径 |
|---|---|---|
| device-daemon.py | mac/MBP 守护（SSE 推送 + relay 兜底） | ~/dsh-collab/comm-server/ |
| device-daemon-i9.py | i9(Windows) 精简守护 | 同上 |
| channel-map.py | 通道路径测绘（TS/服务器/本机） | 同上 |
| gate-deploy-check.py | 部署门（防漏变量/env 契约） | ~/dsh-collab/scripts/ |
| bus-push-rule-v1.md | 推送规则（并入本文档 §1） | ~/dsh-collab/comm-server/ |

## 五、入账本
- [ ] R033：服务器通道卫生（§1 七条）
- [ ] R034：跨设备寻址 agent-id=<device>:<role>（§3）
- [ ] 待用户确认后入 RULES.md + SystemGraph 同步

---
*星桥 2026-09-09 v1 · 三问合一（通道卫生/表达规范/沟通模型）*

---

## 六、公约 v1.1 增补（2026-09-09 用户确认 + 6 方审批补充合并）

### 6.1 路由架构决策（用户确认：方案 A）
- 服务器=设备级路由（无全局角色注册表，零状态零维护成本）
- 设备守护=角色分发（agent-role-map 设备本地，最准）
- role@device 语法保留（如 target="mbp:mbp-bus"）：服务器只拆设备段透传，映射设备侧解——纯寻址糖不增服务器状态

### 6.2 成本治理原则（Φ4 + HR 统一规范）
- 同设备角色互发 = agent-bus 本地，**永不进服务器**（零 token 零污染）
- 每消息成本 = 信封 1 次 + 目标角色唤醒 1 次，无冗余放大
- 群聊放大 20.8x / 无效投递 6.5% → 探照灯三灯 + G1-G4 约束

### 6.3 服务器故障降级纪律（§五详细版在 server-degrade-discipline-v1.md）
- 状态机: 绿(正常)/黄(转黑板域)/红(停发缓存)——守护 30s 探测
- 硬约束: agent 禁自发重试 / 禁多路径乱试 / 守护唯一代理 / 降级收敛 / 审计
- Lean4: G-C19 degrade-state / G-C20 no-agent-retry / G-C21 single-proxy
- 人类求救兜底: L1自动→L2守护→L3求救提示词给管理员(模板 ~/Desktop/node-sos-template.txt)

### 6.4 污染隔离 comm-router（§详细版在 comm-router-isolation-design-v1.md）
- 域边界: collab 本机信息不灌跨设备; 设备间走 notes/<node>/
- 白名单 trust-map 防 spoof(采纳调查员 S1=G-C11s) / hash 去重(G-C15) / 风暴熔断(G-C13) / 审计日志
- 外部消息入网信封化(采纳驿使 G-C11e)

### 6.5 审批补充（6 方 11 条全并入）
- 守望: G-C FAIL 联动 incident 门 / 部署门入 J37 pre-release
- 驿使: G-C11e 外部信封标准化
- 明鉴: agent-role-map 多设备各自维护(v1.1 精化)
- HR: 离线目标黄灯转黑板 / 信封 size 上限(>4KB 走黑板引用=G-C18) / 群聊跨设备 G1-G4 泛化(G-C17)
- 守灯: health-check 17 项通道卫生巡检(已集成) / post-restart 守护自恢复验证
- 调查员: G-C11s 信源可信校验(防 spoof) / agent_send 门禁仅同机(G-C12 分界) / ttl_sec 分语义待人工不误杀(G-C16)

### 6.6 Lean4 断言全表（convention-lean4-check.py 扩展）
G-C1..C10(基线) + G-C11s trust-source + G-C11e external-envelope + G-C13 风暴熔断
+ G-C14 发送方黄灯义务 + G-C15 hash去重 + G-C16 纯确认不回跨设备 + G-C17 跨设备群聊
+ G-C18 大payload门 + G-C19 degrade-state + G-C20 no-agent-retry + G-C21 single-proxy

## 七、签署（节点级）
- [ ] mac-mini / MBP / i9 三节点经服务器发起签署请求(notes/<node>/) → 节点内确认 → 回签
- [ ] R033/R034 已入账(2026-09-09 user 裁决)；v1.1 增补待入账

---
*星桥 2026-09-09 · 公约 v1.1（v1 + 6方审批 + 用户确认设计）*

---

## 八、v1.2 变更（2026-09-09 · 设备内治理补强）
- §3.1.1 设备内通讯治理细则（A 通道选择/B 成本/C 广播收敛/D 审计/E Lean4 断言）
- §3.1.2 设备内 vs 跨设备治理对等对照
- 新增 G-C28 broadcast-scope / G-C29 internal-audit → 校验器 18/18 PASS
- 防 spoof 三端守护落地(G-C11s 实测) + 域隔离 G-C27 修复 collab 污染 + pollution-scanner 持续根治(10 类污染/30min 常驻)
- 变更同步: 星桥 → 6 相关方(2026-09-09)

---
*星桥 2026-09-09 · 公约 v1.2（v1.1 + §3.1 设备内治理补强）*

## 九、接入设备签署与公共文本抄送（2026-09-09 用户指示）

### 9.1 节点签署义务（公约约束方都应签）
- 公约约束**所有接入设备节点**（mac-mini/mbp/i9），非仅发起方
- 版本更新（如 v1.1→v1.2）→ 服务器向各节点发签署请求（信封 action=convention-sign-*）
- 各节点协调者须回签（同意/异议写 notes/<node>/convention-sign-ack）
- 未回签节点 = 公约未生效约束（记录在案，协调者跟进）

### 9.2 服务器公共文本更新抄送接入设备（用户 9/9）
- **范围**：公约/通讯规则/通道契约等服务器侧公共文本的每次更新
- **通道**：走各节点域 notes/<node>/（**非 collab**——避免污染/噪音，G-C27 域隔离）
- **格式**：短通知（变更点+文档键），正文留原域文档
- **义务方**：更新发起者（星桥/HR/明鉴 等）须抄送；遗漏=治理缺口（用户指出）
- Lean4: G-C30 notify-nodes-on-update（更新公共文本时须投 notes/<node>/）

---
*星桥 2026-09-09 · 公约 v1.2 补 §九（节点签署 + 公共文本抄送）*

## 十、公约维护与提案通道（convention-PR · 2026-09-09 用户指示）

### 10.1 共治理念（非单方面维护）
- 公约维护不只 mac-mini 星桥——**端侧主桥(MBP/i9)是约束方, 有权提交补充意见**(类比 Git PR)
- 任何接入设备可提提案 → 评审 → 裁决 → 合并 → 版本 bump → notify-nodes 全节点

### 10.2 提案流程
```
端侧提交(convention-pr.py submit 或 bus action=convention-propose)
  → pending
  → review(星桥汇总+相关方评审)
  → merged(并入公约+版本bump+notify-nodes) | rejected(带理由)
```
- 提案须带实测/场景理由(无理由=纸面, R030)
- 端侧主桥提案优先响应(最懂落地痛点)
- 重大变更走 R008 用户裁决

### 10.3 工具与断言
- convention-pr.py: submit/list/review/merge/reject (提案区 data/registry/convention-proposals/)
- Lean4: G-C34 proposal-channel / G-C35 end-node-propose(端侧可提)
- 校验器现 27 项断言（G-C1~C38，2026-09-09 全 PASS）

---
*星桥 2026-09-09 · 公约 v1.2 §十 · PR 机制(端侧共治)*

### 10.4 提交后唤醒（MBP CP-004 · 2026-09-09 采纳）
- 任何设备提交公约 PR / bug 报告后，**须向目标方发短消息提醒**（≤50 字指向黑板键/task_id）
- 形成闭环: 提交 → 提醒 → 处理 → 回执（防 PR 滞留不被处理）
- 理由（MBP 实测）: 黑板/bus 是持久态但守护可能不即时感知; 短消息是唤醒通道确保及时
- Lean4: G-C38 pr-notify（提案提交后发短消息提醒）

---

## 十一、v1.3 变更（2026-09-09 · 端侧自治 + 服务器投递过滤 · i9 CP-005/006 采纳）

### 11.1 端侧消息自治治理（CP-005 · 各端侧节点强制）
- 各端侧节点运行**确定性过滤引擎（非人工判断）**，四条硬规则：
  - **A1 乱码必反馈**：收到乱码/编码错乱消息 → 必向信源反馈，不静默忽略（老板裁定固化）
  - **A2 污染必上报**：识别到污染/越权/域错配内容 → 拦截并上报治理方，不私下消化
  - **A3 不可读请解决**：内容不可读/上下文缺失 → 显式请求解决而非猜测执行
  - **A4 信源可信**：陌生/伪造信源拒路由（G-C11s 防 spoof），端侧不得放行
- 端侧实现须附 Lean4 断言（如 msg-filter G1-G7）；i9 侧落地证据待其重启新版 daemon 复核（R030）
- 与 pollution-scanner（10 类污染/30min 常驻）配套：端侧拦头道 + 治理侧持续扫描双保险

### 11.2 服务器端投递过滤（CP-006 · 端侧只收本设备定向）
- 服务器投递按 **target 定向 + 域语义 + 订阅过滤**（D1-D5），**非定向键不广播端侧**
- SSE 推送仅发 target=本节点 的信封；跨设备信封按域分区写 notes/<node>/（G-C27）
- 端侧只感知：①target=自己的信封 ②自己域 notes/<node>/ 的变更；collab 类非定向不灌端侧
- 与已落地 v0.3.3（协调者别名归一）+ G-C7（target-scoped）一致，正式入约
- 语义: reply_required（须 agent 级 done）/ notify_only（纯通知 delivered 即终态）——防「投递=完成」假闭环

---
*星桥 2026-09-09 · 公约 v1.3（v1.2 + i9 CP-005/006：端侧自治 A1-A4 + 服务器投递过滤 D1-D5）*

## 十二、v1.4 变更（2026-09-09 · §3.1 结构门化：设备内消息禁进广播域）

### 12.1 根因（明鉴治理卡泄漏 i9 事件）
- 本机角色（明鉴/星桥等）把治理/回执/评审卡写进 `notes/collab/`（广播域）→ sync-up 上行中枢 → i9/mbp 可见 → i9 msg-filter 误报簇
- 违反 §3.1「设备内角色沟通不走服务器」——此前仅文字条款无运行时门

### 12.2 结构门（机器可验证，非自觉）
- **comm_domains v1.1 语义单源**：`collab_broadcast_ok(val)` —— collab 卡须带广播语义（type=bus-envelope / _bus 信封 / broadcast-|collab- 前缀 / scope∈{broadcast,collab}）；无标记=设备内消息
- **sync-up 上行过滤（G-C39）**：上行咽喉处无标记 collab 卡不上行中枢——连直写绕过 bb-gate 的也拦（本机 8792 局部泄漏不再跨端）
- **bb-gate 写入门（G-C40）**：cmd_put 写 notes/collab/ 缺广播语义直接拒（§3.1 提示写本机角色域）
- **本机角色治理卡默认域**：notes/<role>/（如 notes/mingjian/，不上行）；仅显式广播/守护信封落 collab
- Lean4: G-C39 collab-upstream-gate / G-C40 collab-semantic-source → 校验器 29 项

### 12.3 实测
- envelope 卡 → 中央 200（放行）；无标记 ack 卡 → 中央 404（拦截 🚫）
- bb-gate G6 自检 5 项 + comm_domains 自检全过 + 29/29 PASS

### 12.4 消息完成语义完备（i9 PR#3 = CP-007 采纳 · 2026-09-09）
- 背景：老板问「mac 在等 i9 done 什么」→ 实证：纯测试/通知消息无处理者，delivered 永挂（状态机只有 delivered→done，无免处理终态/超时兜底）
- **条款 F 三路径完成语义**：实质任务(含 text/cmd/request) → delivered→done；通知/纯测试/探活 → 送达即 done（守护 is_test_only 判定，防假等待）；歧义 → delivered + 提示显式标注（防假闭环）
- **条款 G 测试消息显式标注**（发送方义务）：action 前缀 test-/probe- 或 payload test:true/notify_only；禁负载启发式猜
- **条款 H delivered 生命周期**（服务器）：notify_only delivered 30min 自动 done（v0.3.6 已落）/ 单查端点 /bus/task/<id>（已落）/ 全量 stats 口径（已落）；processing 幽灵 10min 回收（C4 对齐，已落）
- **条款 I 回执可观测**：端侧 reply 失败记日志+重试一次（i9 已实修）
- Lean4: C4 queue-zero 维持 + CP-007 归入提案区（29/29 PASS）

### 12.5 跨设备文件引用契约 file_refs（CP-008 采纳 · 用户同意 B 方案 · 2026-09-09）
- **规则**：跨设备二进制/大文件**不入信封**——写 genebank（chromosome=artifacts，内容寻址 sha256），bus 信封 payload 可选 `file_refs:[{ref,name,size,sha256}]`（ref=sha256:<hex> gene_id），文本通道只传引用（G-C18 4KB 内）
- **拉取**：收方按 `GET genebank:8801/api/v1/genes/<ref>/file` 拉取并比对 sha256；染色体限标准集（artifacts/datasets/models/corpora/knowledge/recipes），自定义染色体需先声明
- **工具**：bb-share.py（写 gene + 派单）为参考实现；读鉴权=tailnet 信任域（每设备 token 属 E2）
- **验收**：100KB jpg → 信封 523B ref-only → delivered i9 → 按 ref 拉取 sha256 一致 ✅
- Lean4: CP-008 归入提案区（30+1 断言体系内）

---
*星桥 2026-09-09 · 公约 v1.4 补 §12.5（file_refs 跨设备文件引用契约 CP-008）*

## 十三、v1.5 变更（2026-09-09 · 黑板跨实例一致性 · i9 PR#4 = CP-009 采纳）

### 13.1 根因（CLD-Voice 交付链实测）
- 交付键只写本地黑板(mac-mini:8792)未双写中枢(xingqiao:8792) → mbp/coordinator 读中枢 404/空；i9-bb._mirror_central 被临时直写绕过 → 双实例一致性不能靠自觉

### 13.2 条款
- **J1 共享键双写**：跨设备可读键(交付/通知/报告/记录)一律双写本地+中枢(或按域约定直写中枢)，禁只写本地
- **J2 服务器同步层(治本·分期)**：中枢 single-source+端侧镜像 或写入代理自动镜像——拓扑级变更，用户裁定后实施(backlog)
- **J3 404 语义**：读取端点区分 instance-missing(键不在本实例)/not-found(全局无)/no-permission；过渡期先在读 helper 层落地
- **J4 共享域以中枢为权威读面**：跨设备共享域键以中枢为准、端侧只读；纯本地工作键标注 scope=local
- **K1**：跨设备键写入只经带双写/路由的正式工具(i9-bb.py/comm-central)；**K2**：临时写入后必须验证中枢可达(非仅本地 200)

---
*星桥 2026-09-09 · 公约 v1.5（i9 PR#4 黑板跨实例一致性 J/K —— 消息治理四段合拢: 收的对 D + 收到会处理 A + 完成有闭环 F-H + 读得到 J）*

## 十四、v1.6 变更（2026-09-09 · 节点投递可见性与离线处理 · i9 PR#5 = CP-010 采纳）

### 14.1 根因（mbp 守护离线触发, 机制定性）
- mbp 守护离线期发它的任务 queued 静默滞留、发送方无感知、ttl 超时静默丢——投递机制对离线无可见性

### 14.2 条款与落地
- **L1 节点预检** /bus/nodes(在线/积压) → ✅ v0.3.7 实测三节点在线
- **L2 send 离线提示**：目标无 SSE 订阅时响应带 offline:true → ✅ v0.3.7
- **L3 ttl 语义**：queued 超时 → failed(offline-timeout) 可审计 → ✅ v0.3.7
- **L4 重连回放**：守护重连 SSE 自动补投积压(保原 task_id, replayed_after_offline) → ✅ v0.3.7 实测 mbp 9f23164c/5e08d737 delivered
- **M1** 重要消息离线降级黑板双写(J1)+target-offline 记录；**M2** 文件走共享域+CP-008

---
*星桥 2026-09-09 · 公约 v1.6（i9 PR#5 投递可见性 L/M —— 治理五段合拢: 收 D + 处理 A + 闭环 F-H + 读 J + 发得达 L）*
