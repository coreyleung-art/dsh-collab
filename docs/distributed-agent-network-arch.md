# 分布式智能体节点网络架构 v1

> 明鉴 v3 · 2026-09-09 · SystemGraph 主源 · 基于永续通讯收敛里程碑(2026-09-09 实测验收)
> 快照: gallery/snapshots/distributed-network-arch-<ts>.svg（GUI 可缩放）
> 关联: CLD 分布式智能体节点网络公约 v1 · bus-push-rule v1 · perpetual-comms-convergence-plan-v2

## 一、四层模型总览

```
┌─────────────────────────────────────────────────────────────┐
│ L4 治理与中枢层                                               │
│   星桥(总线协调·规则账本R001-R034·永续通讯主理)                │
│   司库(资源管理者+成本监察·agent-role-map 角色映射)            │
├─────────────────────────────────────────────────────────────┤
│ L3 业务与专业智能体层                                          │
│   明鉴(蓝图主编·SystemGraph主源·Φ1-Φ11)                      │
│   数据调查员(情报/信源) · 灯塔/老登(外卖采集运营)               │
│   知了(学习·守白限定) · 验金石(QA) · 守灯/守链/罗盘/回声…      │
├─────────────────────────────────────────────────────────────┤
│ L2 通讯与投递层                                               │
│   黑板 Blackboard(8792) · bus-bridge(8791 send/receive/SSE) │
│   central-inbox(角色名→会话映射·精确唤醒)                      │
├─────────────────────────────────────────────────────────────┤
│ L1 设备与守护层                                               │
│   mac-mini(主源) · MBP · i9(Windows边缘) · xingqiao(服务器)  │
│   各端 device-daemon(SSE长连订阅·免轮询·25s心跳)              │
└─────────────────────────────────────────────────────────────┘
```

## 二、通道矩阵（谁走哪条路）

| 通道 | 端点 | 用途 | 路径 | 断TS可用 |
|------|------|------|------|---------|
| bus 信封(可靠队列) | xingqiao:8791 | 跨设备任务/消息投递 | 公网 106.53.214.108 | ✅ |
| bus SSE 推送 | :8791/bus/events | 服务器→设备实时推送(免轮询) | 公网 | ✅ |
| 黑板 | 本机8792/中枢:8792 | 状态/记录/域消息 | local/服务器 | 本机✅ |
| 实时 SSE | 设备→mac-mini:8803 | 黑板事件订阅 | Tailscale | ❌(走TS) |
| agent-bus | 本机进程内 | 同机角色互发(agent_send) | 本机 | ✅ |

**判定分界**：可靠投递=bus 信封(公网)；实时黑板推送=TS 直连；两者独立——TS 断不影响 bus 信封(已实测)。

## 三、关键链路（推送与唤醒）

```
星桥/任意设备 → POST /bus/send {from,target,action,payload}
  → 服务器 bus-bridge 入队(tasks持久化+TTL) + notifyTarget SSE推送
  → 对端设备守护(device-daemon) 长连收到 new-task
  → 转写本机黑板 notes/<node>/ (payload.to=角色)
  → central-inbox 角色映射 → 精确唤醒目标 agent(agent-role-map.json)
  → 目标角色处理 → reply ACK 清队(队列零积压)
```

## 四、寻址三层

| 想发给谁 | 写什么 | 走哪 |
|---|---|---|
| 同机角色 | agent_send(角色) | 本机 agent-bus |
| 异机(知设备) | bus send target=<设备> payload.to=<角色> | 服务器 |
| 广播 | bus send target=any | 服务器 |

**关键澄清**：设备≠角色；设备是宿主(mac-mini/mbp/i9)，角色是设备内 agent 会话。
agent-id 全局唯一 = `<device>:<role>`（如 mac-mini:明鉴）。

---
*distributed-agent-network-arch v1 · 明鉴 · 2026-09-09 · 四层模型+通道矩阵+推送链路*
