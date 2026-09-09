# 跨设备 MCP 客户端接入指南 · external-link-mcp

> 产出：协调者 session-fa1f9150 · 2026-08-17 · 目标「i9 及其他设备经 MCP 接入本网络」
> 服务器：external-link-mcp（92623479 维护，ELA-2026-0817-03）
> 端点：`http://100.120.203.20:8910/mcp`（Tailscale）· 本机 `http://127.0.0.1:8910/mcp`

---

## 一、端点状态（当前）

| 项 | 值 | 说明 |
|---|---|---|
| 传输 | Streamable HTTP（MCP 2025-03-26 规范） | stateful session（每会话独立 server+transport+重连） |
| 协议版本 | 2024-11-05 / 2025-03-26 / 2025-06-18 / 2025-11-25 | SDK 客户端自动协商 |
| 鉴权 | SSE_TOKEN（X-MCP-Token header，可选） | 当前未启用（Tailscale 内网）；云端暴露前须启用 |
| 工具 | `channel.send` / `channel.status` | 分级策略 P0-P3 |
| 监听 | 0.0.0.0:8910 | 本机 + Tailscale 可达 |

## 二、分级策略（channel.send 的 level 参数）

| 级别 | 行为 | 来源推断 |
|---|---|---|
| P0 | 即时推送 | 业务即时（订单/告警） |
| P1 | 推送 | 业务关键 |
| P2 | 默认汇总（`priority:now` 可即时） | 未填默认 |
| P3 | **拦截**（返回 block） | dsh-health/sysops/cld-watchdog 等系统运维来源 |

安全设计：P3 来源（系统运维侧）默认拦截，即使用户不传 level 也不会把内部运维消息推到企微。

## 三、客户端接入配置

### 3.1 通用（任何 MCP 客户端）

端点 URL：`http://100.120.203.20:8910/mcp`（远程设备经 Tailscale）
或 `http://127.0.0.1:8910/mcp`（本机）

### 3.2 Claude Code

```json
// .mcp.json（项目根）
{
  "mcpServers": {
    "external-link": {
      "type": "streamable-http",
      "url": "http://100.120.203.20:8910/mcp"
    }
  }
}
```

或 CLI：
```bash
claude mcp add external-link --transport streamable-http http://100.120.203.20:8910/mcp
```

### 3.3 Cursor

Settings → MCP → Add new MCP server：
- Name: `external-link`
- Type: `streamable-http`
- URL: `http://100.120.203.20:8910/mcp`

### 3.4 DSH agent（本网络）

mcp-station 挂载（1e54d56d 维护）或 Node SDK 直连：

```js
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StreamableHTTPClientTransport } = require('@modelcontextprotocol/sdk/client/streamableHttp.js');
const transport = new StreamableHTTPClientTransport(new URL('http://100.120.203.20:8910/mcp'));
const client = new Client({ name: 'my-agent', version: '1.0' });
await client.connect(transport);
const tools = await client.listTools(); // channel.send / channel.status
const r = await client.callTool({ name: 'channel.status', arguments: {} });
```

### 3.5 鉴权（云端暴露时）

```bash
SSE_TOKEN=<token> node index.js --sse
```
客户端需带 header：`X-MCP-Token: <token>`

## 四、PC-i9 验证路径（目标第①步）

PC-i9（Windows，Tailscale 100.118.15.71）经向日葵 cmd2 或本机 Node：

```bash
# curl 握手（无 Node 环境）
curl -s -X POST http://100.120.203.20:8910/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"pc-i9","version":"1.0"}}}'
# 期望：返回 serverInfo external-link-mcp + capabilities.tools
```

```bash
# Node SDK（PC-i9 有 Node 时）
npm i @modelcontextprotocol/sdk
node -e "（同 3.4 脚本，endpoint 用 http://100.120.203.20:8910/mcp）"
```

## 五、验证清单（P3 闭环标准）

- [x] 本机 SDK 客户端 connect/tools/list/channel.status ✅（已验）
- [x] Tailscale 路径（100.120.203.20:8910）SDK 全链路 ✅（已验）
- [x] **PC-i9 远程握手 + 工具调用 ✅（2026-08-17，5a5368af 官方 SDK 客户端，P3 跨设备闭环达成）**
- [ ] MBP 上线后同路径验证（待其联网）
- [ ] iPhone（可选，MCP 客户端生态有限，可先用 Safari/curl 验证端点可达）

> 里程碑：**P3 跨设备分发正式达成（2026-08-17）**——external-link-mcp 现可被 Tailscale 内任意设备调用（mac-mini 主实例 → PC-i9 远程 channel.status 验证通过，企微 bound）。

## 六、护栏

- 凭据纪律：channels.json 只存配置结构，凭据值在 0600 文件（keyring/credentials.enc），跨设备只传引用
- 云端暴露前必须启用 SSE_TOKEN；Tailscale 内网阶段可不启用（组网已认证）
- P3 系统运维来源默认拦截（用户指令：系统运维侧信息暂不推送企微）
- 任何 channel.send 真发前确认目标与内容（可先用 channel.status / P3 来源测试决策链）

---
*接入指南 v1 · 与 external-link-mcp-plan.md 衔接 · 设备协调 5a5368af 执行远程验证*
