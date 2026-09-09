# FlowerNet · 分布式智能体网络协议 v1.0

> 版本：v1.0 · 2026-08-23 · 协调者 fa1f9150
> 定位：服务于花店数字化蓝图（3.0 端侧 / 4.0 垂直引擎）的自有分布式智能体通讯协议
> 原则：**自研语义层 + 通用传输**——传输用标准 HTTP/Tailscale，但语义（时间轴/归属/任务/权限）为自有设计，不开源、不依赖开源网络工程，防逆向
> 编制方式：将已实践沉淀（黑板任务卡 v1.1/v1.2/v1.3/v2.0、CAHAC v1.0、节点总线 v1.0、时间轴 v0.3、归属 v0.6）正式化为统一规范

---

## 0. 协议标识

- **协议名**：FlowerNet（花网）· Distributed Agent Network Protocol
- **缩写**：FNP
- **当前版本**：1.0
- **兼容**：向后兼容全部既有实现（blackboard 0.1-0.6 / 任务卡 / CAHAC）

## 1. 分层架构

```
┌─────────────────────────────────────────┐
│ 应用层：智能体/节点业务逻辑               │
├─────────────────────────────────────────┤
│ 语义层（FNP 自有，防逆向核心）            │
│  · 状态语义：命名空间 + 版本 + 归属       │
│  · 时间语义：全局 seq（HLC 唯一时间戳）   │
│  · 任务语义：任务卡（队列/定向/回报）     │
│  · 事件语义：订阅/事件桥（SSE 推送）      │
│  · 治理语义：红绿灯锁 / 通道分级 / 落链   │
├─────────────────────────────────────────┤
│ 传输层：HTTP 1.1（黑板 KV）+ SSE（事件）  │
│  · Tailscale 内网（跨设备）              │
├─────────────────────────────────────────┤
│ 物理层：mac-mini 中枢 / i9 / MBP / 门店   │
└─────────────────────────────────────────┘
```

**关键**：传输层是通用标准（HTTP），但**语义层全部自有**——别人看到 HTTP 请求也看不懂语义（seq 规则、命名空间约定、任务卡生命周期、红绿灯协议都是我们的设计）。

## 2. 核心概念

### 2.1 节点（Node）
- 中枢（hub）：mac-mini，黑板宿主，全局权威
- 节点（node）：i9 / MBP 等，注册于 `nodes/<id>`
- 门店（store）：蓝图 3.0 接入，`type=store` 注册于 `nodes/<store-id>`（v0.6 已支持）

### 2.2 黑板（Blackboard）
- 单一共享状态区（KV），跑在中枢 :8792
- 命名空间：`nodes/`（身份）`tasks/`（任务）`data/`（业务数据）`notes/`（通知）
- 每次写：全局唯一 seq + key 版本号 + writer（X-Writer，v0.6）

### 2.3 全局时间轴（Timeline）
- 每次 PUT/DELETE 由黑板分配全局单调 seq（HLC：物理秒×10⁶+同秒逻辑计数）
- `GET /clock` 对时；`GET /timeline?since_seq=` 增量补漏（重启对齐基线）

### 2.4 任务卡（Task Card）
- 生命周期：`tasks/<node>/queue/<seq>`（CREATED）→ 取卡执行 → `tasks/<node>/result`（回报，自动镜像 `results/<seq>`）→ 清卡
- 定向：key 前缀 + `recipient` 字段（v0.6）+ `?node=` 取卡过滤
- 并发：max_concurrent（多执行器并行，回报各自镜像）

### 2.5 事件（Event）
- 订阅：`POST /subscribe {topic, callback}`（去重/持久化/退订）
- 事件桥：黑板变更 → 8803 → SSE 推送给订阅者（零轮询）

### 2.6 身份与归属（Identity & Ownership, v0.6）
- 写入签名：`X-Writer: <agent-id|node-id>`（audit 可追溯，无签名=anonymous）
- 命名空间归属：`GET /ns-registry`（角色→职责命名空间）
- 门店身份：`nodes/<store-id>` 带 store_id/code/location/type

### 2.7 治理语义（Governance）
- 红绿灯：agent_light/lock/unlock（同源互斥，写前查灯）
- 通道分级：STATUS/ACK→黑板；TASK→p2p；COLLAB→thread；EVENT→eventbus；BATCH→mailbox；BROADCAST→白名单三类
- 落链：5 步（落盘→入库→向量化→registry→报告）

## 3. 消息信封（Envelope）

所有任务卡/回报/通知统一信封（兼容 CAHAC Envelope 子集）：

```json
{
  "v": "fnp/1.0",
  "type": "task|result|notify|status|event",
  "task_id": "<唯一>",
  "sender": "<writer>",
  "recipient": "<target>|*",       // v0.6
  "action": "shell|info|ollama|scan|...",
  "payload": {...},
  "seq": 1787482886000001,          // 黑板分配（写后回填）
  "ts": "2026-08-23T18:00:00+08:00"
}
```

## 4. 时序（关键流）

### 4.1 任务派发-执行-回报（节点/门店）
```
中枢 → PUT tasks/<node>/queue/<seq> {recipient, action, payload}
节点 → GET /tasks?node=<id> （只取自己的卡）
节点 → 执行 → PUT tasks/<node>/result {task_id, ok, output}
黑板 → 自动镜像 result → results/<seq>（历史可追溯）+ 事件桥通知
节点 → DELETE queue/<seq>（清卡）
```

### 4.2 状态发布-事件回流（角色/门店）
```
角色 → PUT data/<role>/<key> {status}（带 X-Writer）
黑板 → 分配 seq → 事件桥 → SSE 推送给订阅 data/ 的消费方
```

### 4.3 门店接入（蓝图 3.0 路径）
```
注册 → PUT nodes/store-01 {type:store, store_id, location}
隔离 → 任务卡带 recipient:store-01 + ?node=store-01 取卡
数据 → data/store-01/* 命名空间 + X-Writer:store-01
权限 → v0.7 per-namespace 授权（store-01 只能写 data/store-01/*）
```

## 5. 与开源工程的边界（防逆向）

| 开源工程 | 我们的差异点 |
|---|---|
| MCP（工具调用标准） | 只借鉴「工具描述」思想；通讯语义（时间轴/归属/任务卡生命周期）自有 |
| A2A（agent 互操作） | 不采用；我们的 agent 协作靠黑板状态共享 + 红绿灯，非消息互操作 |
| robustmq/mqtt | 不采用；事件走自有事件桥（8803 SSE），订阅语义自有 |
| LangGraph/AutoGen 编排 | 不采用；编排靠黑板任务卡 + 协调者，自有 |

**防逆向核心**：即使外部看到 HTTP 流量，也看不到语义——seq 规则、命名空间约定、任务卡生命周期、红绿灯协议、通道分级均为自有设计，无公开文档。

## 6. 版本与演进

| 版本 | 内容 | 状态 |
|---|---|---|
| v1.0 | 本规范（正式化全部既有实践） | ✅ 本次 |
| v0.6 对应 | 归属/收件定向/门店身份 | ✅ 已实现 |
| v0.7 预告 | per-namespace 授权（门店数据隔离） | 待实现 |
| v1.1 预告 | 协议版本协商 + 能力发现（门店上报 capabilities） | 蓝图 3.0 |

## 7. 关联

- 实现：`scripts/blackboard-server-v0.6.py`（黑板，协议宿体）
- 规范前身：blackboard-task-card-protocol-v1.1、cahac-protocol-v1.0、node-bus-design-v1.0
- 蓝图：flower-shop-evolution-research.md（3.0 端侧按本协议接入门店）

---
*FlowerNet FNP v1.0 · 协调者 2026-08-23 · 自研协议正式化，服务蓝图防逆向*
