# 黑板 MCP Server 设计 v1.0（任意设备标准接入）

> 2026-08-29 星桥-mac-mini-协调者 · 用户设想：完全解耦后 MCP 服务器化——任意设备经订阅/授权接入成为新分布式节点
> 定位：把黑板（消息总线）+ 桥（通讯）能力暴露为标准 MCP 服务，打破三端固定，开放任意设备接入

## 一、核心洞察（解耦 → MCP 化的价值）

当前架构：三端固定（mac-mini/MBP/i9）+ 私有协议（node-bridge 专用二进制）。
解耦后：桥/黑板已独立进程 → 可进一步 MCP 化 → **任意支持 MCP 的客户端**（Claude Desktop/IDE/自研 agent/手机）经授权接入成为新节点。

**价值**：
- 任意设备零开发接入（MCP 标准）
- 订阅式消息（事件驱动，省 token）
- 授权可控（token/设备注册）
- 复用黑板（存储/审计/时序）

## 二、MCP Server 设计（blackboard-mcp）

### 传输
- **stdio**（本地 client 直连）
- **SSE**（远程设备，经 Tailscale/授权）——复用黑板 8803 SSE 基础

### 端口拓扑（重要：REST 与 SSE 分离）

| 端口 | 用途 | MCP 使用 |
|------|------|----------|
| 8792 | 黑板 REST API（读/写 KV，带 token） | `bb_read` 直连 |
| 8803 | 黑板 SSE 事件桥（`GET /events`，公开读） | `bb_subscribe` 后台线程连这里 |

> ⚠️ 踩坑（2026-08-30）：MCP 的 SSE 线程曾误连 8792（REST）导致推送永远不来——8792 有监听故 TCP 连接成功，但 REST 对 `GET /events` 返回 404。**必须为每个端口定义独立常量（`BB` / `BB_SSE`）**。
> ⚠️ 踩坑（2026-08-30）：SSE 线程推送 stdout 时与主循环 stdout 锁死锁（Rust StdoutLock 长期持有）——**写 stdout 一律用写时短暂 lock**。

### Tools（暴露能力）

| Tool | 功能 | 授权 |
|------|------|------|
| `bb_read` | 读黑板 KV（key → value）✅ v0.3.0 | token |
| `bb_write` | 写黑板 KV（data/notes/tasks）✅ v0.4.0 已实现 | token |
| `bb_subscribe` | 订阅 topic（SSE 推送）✅ v0.3.0 | token |
| `bb_publish` | 发布消息到 topic | token |
| `node_register` | 节点注册（生成 device-id+token）| 开放/管理 |
| `node_heartbeat` | 节点心跳 | token |
| `node_list` | 列出在线节点 | 只读 |

### 协议（MCP JSON-RPC 2.0）
```json
// 初始化
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{}}}
// 列工具
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
// 调用
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"bb_read","arguments":{"key":"nodes/i9/heartbeat"}}}
```

### 授权（订阅/授权服务）
```
1. 新设备 → node_register（或管理端发 token）→ 得 device-id + token
2. MCP client 每次请求带 token（Authorization: Bearer）
3. 黑板认证中间件校验（v0.6.5 已实现 Bearer + 白名单）
4. 订阅 topic → SSE 推送（事件驱动）
```

## 三、接入流程（任意设备成为新节点）

```
任意设备（手机/新电脑/第三方 agent）
  1. 装 MCP client（或 node-bridge --token）
  2. node_register → 得 token
  3. MCP 连接黑板（Tailscale/授权 URL）
  4. bb_subscribe 订阅 → 实时收消息
  5. bb_write/publish → 发消息
  6. 成为分布式节点（心跳/消息/订阅全通）
```

## 四、与现有机制衔接

| 现有 | MCP 化后 |
|------|---------|
| node-bridge（专用二进制）| MCP client（标准，任意设备）|
| 黑板私有协议 | MCP JSON-RPC + 黑板后端 |
| 三端固定 | 任意设备接入 |
| SSE 8803（私有事件流）| MCP SSE 传输（标准）|
| token 认证（v0.6.5）| MCP Authorization 头复用 |

## 五、实现路线

1. **blackboard-mcp server**（Rust 或 Python）：
   - 实现 MCP JSON-RPC 2.0（initialize/list_tools/call_tools）
   - 后端调黑板 API（复用 Bb::with_token）
   - SSE 传输（订阅推送）
2. **接入 mcp-station**（本机注册）
3. **授权管理**：token 生成/撤销（管理端）
4. **任意设备验证**：手机/新电脑 MCP client 接入测试
5. **文档 + 广播**：开放节点接入指南

## 六、安全边界

- token 授权（每设备独立）
- 只读 vs 写权限分级（node_register 后可配）
- 黑板认证中间件兜底（v0.6.5）
- 订阅范围白名单（topic 级授权）

## 七、规则账本

- 新规则提案 **R017「MCP 开放接入」**（或并入 R002 通道扩展）
- 触发：任意设备申请成为分布式节点
- 与 R012（完整体）、R016（CLD 治理）、token 体系配套
