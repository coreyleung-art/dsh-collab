# mcp-sse-test.js · external-link-mcp SSE 端点验证

> 版本 v1.1.0 · 维护：罗盘 5a5368af · 2026-09-06 R006 补全

## 用途
验证 external-link-mcp SSE 端点（本机或跨设备 Tailscale）连通性：连接握手 → listTools → channel.status。

## 用法
```bash
node ~/.dsh/devices/mcp-sse-test.js                    # 默认 http://127.0.0.1:8910/mcp
node ~/.dsh/devices/mcp-sse-test.js http://100.120.203.20:8910/mcp   # 跨设备
node ~/.dsh/devices/mcp-sse-test.js --version          # v1.1.0
```

## 依赖
- node + @modelcontextprotocol/sdk（在含 node_modules 的目录运行；--version/--help 免依赖）

## 验证输出
- `[test] 连接成功 ✅` / `[test] tools: ...` / `[test] channel.status: ...`

## 注意
- SSE_TOKEN 鉴权已启用：无 token → 401；需 header X-MCP-Token（token 在 ~/.dsh/sse-token 0600）
