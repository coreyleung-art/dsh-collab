# bus-mcp DSH 插件 · 工具 schema 契约

外链通讯员 session-92623479 · 2026-08-17
依据：协调者 fa1f9150 确认方案（独立插件 dsh-plugin-bus-bridge；e0c391f7 承接 Cordis 壳）

## 插件信息
- 名称：`dsh-plugin-bus-bridge`（独立，不并入 external-link-policy）
- 形态：Cordis 插件，注册 host 工具（agent 原生调用）
- 注册机制：`harness.defineTool`（@deepseek-ai/dsh-tools 统一 schema DSL）+ `ctx.tools.register`（dsh-cordis-host-runner）
- 调用后端：`bus-client.js`（~/.dsh/bus-bridge/bus-client.js 或打包进 lib）→ HTTP 127.0.0.1:8791/bus/*
- 鉴权：自动读 `~/.dsh/bus-bridge-token`（0600）带 `X-Webhook-Token` 头（bus-client 已内置）

## 工具 schema（与 MCP bus.send 命名一致）

### 1. bus.send — 派发任务
```json
{
  "name": "bus.send",
  "description": "跨设备总线桥任务下发：入队任务供目标节点（如 mbp-node）拉取执行并回传结果。wait=true 同步等结果（≤30s），否则异步返回 task_id",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target": { "type": "string", "description": "目标节点（如 mbp-node；缺省 any=任意节点可取）" },
      "action": { "type": "string", "description": "任务动作（如 shell/info/resource.call，由目标节点分派）" },
      "payload": { "type": "object", "description": "任务参数（如 {cmd:...}）" },
      "ttl_sec": { "type": "number", "description": "TTL 秒（默认 3600，超时自动 failed）" },
      "wait": { "type": "boolean", "description": "true=长轮询等结果（≤30s）" }
    },
    "required": ["target", "action"]
  }
}
```
实现：`busSend({target, action, payload, ttl_sec, wait})` → POST /bus/send(?wait=1)

### 2. bus.outbox — 拉取任务结果
```json
{
  "name": "bus.outbox",
  "description": "拉取总线桥已完成任务结果（outbox 队列）；consume=true 拉后删除",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": { "type": "string", "description": "按任务 ID 过滤（可选）" },
      "from": { "type": "string", "description": "按来源过滤（可选，如 mbp-node）" },
      "consume": { "type": "boolean", "description": "true=拉取后删除（默认 false 保留）" }
    }
  }
}
```
实现：`busOutbox({task_id, from, consume})` → GET /bus/outbox(?task_id=&from=&consume=1)

### 3. bus.status — 队列统计
```json
{
  "name": "bus.status",
  "description": "总线桥队列统计：queued/processing/done/failed 数量 + 最近任务列表",
  "inputSchema": { "type": "object", "properties": {} }
}
```
实现：`busStatus()` → GET /bus/status

### 4. bus.receive — 取任务（可选，调试/节点用）
```json
{
  "name": "bus.receive",
  "description": "从总线桥取一个任务（queued→processing）；节点轮询用（MBP bus-client 已自轮询，此工具供 mac-mini 侧调试）",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target": { "type": "string", "description": "按目标过滤（可选）" }
    }
  }
}
```
实现：`busReceive({target})` → GET /bus/receive(?target=)

## 与 MCP 并存
- MCP bus.send（8910）→ 跨设备（PC-i9/MBP 远程调用）
- 插件 bus.*（agent 原生）→ mac-mini agent 便捷通道
- 同一队列（8791 bus-bridge），无冲突

## 验收标准（QA ffb7c3ab）
1. 插件冒烟：`bus.status` 返回队列统计（桥在线时 done ≥7）
2. `bus.send`（action=info, target=mbp-node）→ MBP 自动执行 → `bus.outbox` 可见 done + 结果（MacBook-Pro 系统信息）
3. 鉴权：无 token 环境工具返回 errmsg（bus-client 未读到 token 时 401 透传）
4. 桥离线时工具返回「bus-bridge 不可达」错误（不崩溃）

## 交付物
- `~/external-link-mcp/bus-client.js`（调用模块，含全部 4 函数，无依赖）
- 本契约文档（e0c391f7 按此搭 Cordis 壳）
