# 服务器推送规则（SSE 推送 · 免轮询）v1 · 2026-09-08 星桥

> 用户规则：服务器本身转发时，能插入上下文给到所有接入设备——不应要求本地 agent 轮询。

## 一、推送架构（已实测生效）

```
[发送方: 任意设备/星台/脚本]
   │ POST /bus/send {from,target,action,payload}
   ▼
[xingqiao 服务器 bus-bridge v0.2]
   ├─ 入队写 tasks/ (持久化, TTL 兜底)
   └─ notifyTarget(target) → SSE 推送
         │ data: {type:"new-task", task_id, action, payload, ts}
         ▼
[接入设备守护 device-daemon v0.3]
   ├─ 长连接 GET /bus/events?node=<本机>  (常驻订阅, 25s 心跳保活)
   ├─ 收到 new-task → 转写本机黑板 notes/... (带 payload.to)
   ├─ central-inbox → 角色映射 → 插入目标 agent 上下文
   └─ 断线 → 3s 重连 + receive 补拉一次兜底(不丢消息)
```

## 二、规则条文（接入设备必须遵守）

1. **免轮询**：设备守护必须 SSE 长连接订阅 `/bus/events?node=<id>`；
   禁止定时轮询 /bus/receive 作为主通道（轮询仅作断线重连兜底，一次）。
2. **节点身份**：订阅 `?node=` 必须 = 本设备 DSH_NODE_ID（由部署门 G-D2 强制，无默认）。
3. **上下文插入**：守护收到推送后转写本机黑板（mac 系 127.0.0.1:8792；
   无本机黑板节点走中枢），由 central-inbox 精确唤醒目标 agent（角色映射）。
4. **送达不丢**：SSE 断线重连后须 receive 补拉一次（服务器队列持久化 + TTL，
   补拉覆盖断线窗口）；处理完 reply ACK 清队。
5. **心跳保活**：服务器 25s 推 hb 事件；守护 30s 无任何事件须主动重连。
6. **广播语义**：target=any 推所有订阅；target=<node> 只推该节点订阅者。
7. **鉴权**：SSE 与 send 同用 X-Webhook-Token（token 0600 私存，勿黑板明文）。

## 三、端点契约

| 端点 | 方法 | 用途 | 参数 |
|---|---|---|---|
| /bus/events | GET(SSE) | 设备守护长连订阅 | ?node=<id> |
| /bus/send | POST | 发信封(入队+推送) | {from,target,action,payload,ttl_sec} |
| /bus/receive | GET | 兜底补拉(重连后一次) | ?target=<id> |
| /bus/reply | POST | 处理完回执 | {task_id,ok,result,error} |
| /bus/status | GET | 队列统计 | - |

## 四、验证（R030 实测）

- [x] 服务器 SSE 订阅: mac-mini + mbp 双连接 (log "SSE 订阅 node=mbp 当前 2 连接")
- [x] mac→mac: sse-probe2 推送→黑板→星桥注入 (23:48:22)
- [x] mac→MBP: mbp-sse-final 推送→MBP守护→黑板 (23:49:10, 服务器"已推送 SSE")
- [x] 守护日志无轮询痕迹 (仅 SSE 连接/收推送/断线兜底)

## 五、部署（双端已上线）
- 服务器: bus-bridge.js v0.2 (SSE 端点 + send 触发推送), .bak-push 可回滚
- mac-mini: device-daemon v0.3 launchd interval=0 (SSE), PID 11406
- MBP: 同版本, PID 33697
- 兜底: receive 仍在 (重连补拉), 服务器 TTL 自动 failed
