# i9 DSH 智能体接入方案：订阅 notes/i9 打通双向对话（可直接执行）

> 用途：让 i9 侧的 DSH 智能体（能对话的）订阅黑板 notes/i9/*，接收 mac-mini 协调者的消息，形成双向对话
> 目标：mac-mini 协调者写 notes/i9/coordinator-* → i9 DSH 智能体实时收到 → 回复 notes/i9/i9-* → 协调者看到
> 前置：i9 侧已有运行中的 DSH 智能体（executor 回报「已升级 DSH 智能体接手」——即存在）

---

## 方案 A：i9 DSH 智能体订阅 notes/i9（推荐，最简单）

### A1. 在 i9 的 DSH 智能体会话里，粘贴以下配置

```
【任务】配置你的消息接收通道：订阅黑板 notes/i9/*，接收 mac-mini 协调者的消息。

【背景】
- 黑板地址: http://100.120.203.20:8792（mac-mini 中枢）
- 你的节点 ID: i9
- 协调者会写 notes/i9/coordinator-* 给你发消息
- 你需要实时收到并回复

【步骤】
1. 用 sse-sub 或黑板订阅订阅 notes/i9/ 前缀变化：
   方式①（推荐）：订阅黑板事件桥 SSE
     http://127.0.0.1:8803/events
     过滤事件 key 前缀 notes/i9/coordinator-*
   方式②：黑板原生订阅（若你有订阅能力）
     POST /subscribe  topic=notes/i9/  callback=<你的回调>
2. 收到 notes/i9/coordinator-* 消息后：
   读取该键内容 → 理解 → 回复写回 notes/i9/coordinator-reply-<topic>
   （或你约定的回复键，让协调者能读到）
3. 回复格式建议：{"from":"i9","to":"coordinator","ts":"...","reply":"..."}
4. 验证：协调者写测试键 notes/i9/coordinator-test → 你应收到并回复

【命令参考（Python，i9 可跑）】
订阅事件桥（方式①）：
  python -c "
  import urllib.request
  import json
  import time
  # 订阅 SSE，过滤 notes/i9/coordinator
  req = urllib.request.urlopen('http://100.120.203.20:8803/events', timeout=300)
  for line in req:
      if line.startswith(b'data:'):
          evt = json.loads(line[5:].strip())
          key = evt.get('key','')
          if key.startswith('notes/i9/coordinator'):
              print('收到:', evt)
  "
```

### A2. i9 侧需确认
```
① 黑板事件桥 :8803 从 i9 能否访问？（Tailscale 内应通，需验证）
② 事件桥事件格式：{key, op, ts, ...}（从黑板 SUBSCRIBE 回调转发）
③ 订阅方式：SSE 长连接（推荐）或 sse-sub 工具
```

---

## 方案 B：i9 executor 转发（不改 DSH 智能体，改 executor）

### B1. 在 i9 executor（i9-executor.py）加消息轮询
```
在 executor 主循环加：
  每 5s 检查 notes/i9/coordinator-* 是否有新键（GET /notes/i9/?limit= 找 coordinator 前缀）
  有 → 读内容 → 调本地 DSH 智能体处理（或直接记录到本地供智能体读取）
  处理结果 → 写 notes/i9/coordinator-reply-<topic>
```
> 本质：executor 当「消息信使」，把 notes 消息转给本地 DSH 智能体

---

## 方案 C：i9 注册进 agent-bus（最正规，跨宿主）

### C1. i9 DSH 智能体接入 agent-bus
```
① i9 侧 CLD/dsh 里配置 agent-bus 客户端（连 mac-mini 总线）
② 注册 agent 身份（agent_id: i9-dsh）
③ 通过总线消息（agent_send 等价物）与协调者双向对话
④ 需 agent-bus 跨宿主配置（Tailscale 可达）
```
> 最正规但配置重；若 i9 侧已有 agent-bus 接入能力则优先

---

## 验证清单（任一方案完成后）

| 项 | 验证方法 |
|---|---|
| i9 能收协调者消息 | 协调者写 notes/i9/coordinator-test → i9 回复 |
| 协调者能收 i9 回复 | i9 写 notes/i9/coordinator-reply-test → 协调者读到 |
| 双向实时 | 秒级/事件驱动，非轮询延迟 |

---

## 当前 mac-mini 侧已就绪（无需改）
- 协调者秒级轮询 i9-poll-seconds.py（2s 查回报）✅ 常驻
- 协调者事件订阅 i9-monitor-sub.py（tasks/i9/*）✅ 常驻
- 黑板事件桥 blackboard-events.py :8803 ✅ 常驻
- 通道协议 v1.0 已固化（notes/collab/channel-file-protocol-v1.0）

**缺的只是 i9 侧执行**：选 A/B/C 任一，在 i9 上配置即可。
