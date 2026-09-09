# 服务器通讯治理标准化 v1（通道卫生 · 表达规范 · 角色沟通模型）
> ✅ 已定稿 2026-09-09（用户确认定稿）· R033/R034 已入 RULES.md(78条) · SystemGraph 已同步
> 星桥 2026-09-09 · 用户要求梳理：服务器通道卫生 / 表达规范 / 设备内 vs 跨设备角色沟通
> 沉淀自本轮实测：SSE 推送改造 / i9 治本部署 / 漏变量门 / channel-map / 路由 bug 修复

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
- [x] R033：服务器通道卫生（§1 七条）✅ 已入 RULES.md(2026-09-09)
- [x] R034：跨设备寻址 agent-id=<device>:<role>（§3）✅ 已入 RULES.md(2026-09-09)
- [x] 用户确认定稿 2026-09-09 + SystemGraph 同步

---
*comm-gov-standard v1 定稿 · 2026-09-09 · 用户确认 · R033/R034 已生效 · 明鉴同步 SystemGraph*
