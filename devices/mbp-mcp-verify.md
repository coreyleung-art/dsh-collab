# MBP 接入验证脚本（复用 PC-i9 已验证同款）

> 用途：MacBook Pro 接入 external-link-mcp 验证（目标第②步）
> 前置：用户在 AweSun 远控 MBP 勾选「信任此设备」解锁会话层后，5a5368af 走 desktop/forward 通道执行
> 对应端点：http://100.120.203.20:8910/mcp（Tailscale）

## 脚本（Node，SDK 1.30.0）

```js
// mcp-sse-test.js — 验证 external-link-mcp SSE 端点（本机 + 远程）
// 用法: node mcp-sse-test.js <endpoint>  e.g. http://127.0.0.1:8910/mcp
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StreamableHTTPClientTransport } = require('@modelcontextprotocol/sdk/client/streamableHttp.js');

async function main() {
  const endpoint = process.argv[2] || 'http://127.0.0.1:8910/mcp';
  console.log(`[test] 连接 ${endpoint}`);
  const transport = new StreamableHTTPClientTransport(new URL(endpoint));
  const client = new Client({ name: 'p3-test', version: '1.0' });
  await client.connect(transport);
  console.log('[test] 连接成功 ✅');
  const tools = await client.listTools();
  console.log('[test] tools:', tools.tools.map(t => t.name).join(', '));
  try {
    const r = await client.callTool({ name: 'channel.status', arguments: {} });
    console.log('[test] channel.status:', JSON.stringify(r).slice(0, 300));
  } catch (e) {
    console.log('[test] channel.status error:', e.message.slice(0, 200));
  }
  await client.close();
}
main().catch(e => { console.error('[test] FAIL:', e.message.slice(0, 300)); process.exit(1); });
```

## MBP 执行步骤（信任解锁后）

1. 经向日葵 desktop/forward 通道进入 MBP
2. `npm i @modelcontextprotocol/sdk`（或复用已有 node_modules）
3. `node mcp-sse-test.js http://100.120.203.20:8910/mcp`
4. 期望输出：连接成功 ✅ → tools: channel.send, channel.status → channel.status 企微 bound

## 无 Node 备选（curl 握手）

```bash
curl -s -X POST http://100.120.203.20:8910/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"mbp","version":"1.0"}}}'
```
返回 serverInfo 即握手成功（端点可达 + MCP 协议通）。

---
*准备：协调者 fa1f9150 · 2026-08-17 · 等待用户 AweSun 远控 MBP 解锁*
