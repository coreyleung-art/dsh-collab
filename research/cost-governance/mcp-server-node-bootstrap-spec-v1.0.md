# MCP 服务器更新规格 · node.bootstrap 自举（v1.0）

> 规格：2026-08-22 · HR · 目标服务器=external-link-mcp :8910（维护方=外联 92623479）· 阶段 2.2 节点自举落地

## 目标

MCP 客户端（i9 等 CLD）连接后调用 node.bootstrap → 返回**入职包** → 客户端自动注册黑板+心跳 → node-join-notify 感知 → 自动告知（零手动配置）。

## 新增工具规格

### node.bootstrap

```json
{
  "name": "node.bootstrap",
  "description": "节点接入自举：返回入职包（节点身份/角色/黑板地址/角色目录）",
  "inputSchema": {
    "type": "object",
    "properties": {
      "client_id": { "type": "string", "description": "客户端标识（如 i9）" }
    }
  }
}
```

**返回（入职包）**：

```json
{
  "node_id": "i9",
  "role": "internal",
  "blackboard_url": "http://<宿主IP>:8792",
  "roles_catalog": {
    "hr": "session-a17a52f8-...",
    "coordinator": "session-fa1f9150-...",
    "device": "session-5a5368af-..."
  },
  "heartbeat_interval": 60,
  "register_hint": "PUT nodes/<node_id> {status:online}，周期 PUT nodes/<node_id>/heartbeat"
}
```

### node.heartbeat（可选）

```json
{ "name": "node.heartbeat", "description": "节点心跳（服务器代写黑板 nodes/<id>/heartbeat）",
  "inputSchema": { "type": "object", "properties": { "node_id": {"type":"string"}, "load": {"type":"number"} } } }
```

## 服务器侧实现要点

1. **接入即注入**：客户端连接（initialize）成功后，工具列表包含 node.bootstrap（对外部=云网关层过滤，不进 8910）
2. **黑板地址**：宿主 Tailscale IP + 8792（配置项，勿硬编码）
3. **角色目录**：从 registry/agent_profiles 派生（可缓存 1h）
4. **鉴权**：沿用 SSE_TOKEN（内部通道），node.bootstrap 无需额外权限
5. **脱敏**：入职包不含内部敏感路径/凭据（仅角色 id+黑板地址）

## 验收

1. i9 CLD 连接 → 调 node.bootstrap → 拿到入职包
2. 按 register_hint 注册黑板 → node-join-notify 检测 → agent.online 事件 → 自动告知
3. 心跳 60s → nodes/i9/heartbeat 更新
4. 全程零手动配置（除首次 MCP server 接入）

---
*mcp-server-node-bootstrap-spec v1.0 · HR · 2026-08-22 · 交外联集成*