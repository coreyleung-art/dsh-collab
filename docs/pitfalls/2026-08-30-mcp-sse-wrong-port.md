# 2026-08-30-mcp-sse-wrong-port MCP bb_subscribe SSE 连错端口（8792 REST → 8803 SSE 桥）

> 级别: P1 · 日期: 2026-08-30

## 现象
bb_subscribe 返回「已订阅」但真实写黑板后永远收不到 notification 推送

## 根因
MCP 的 SSE 后台线程用 BB 常量连 127.0.0.1:8792（REST API 端口），而 /events SSE 事件桥在独立端口 8803（原 blackboard-events.py 语义）。8792 有监听 → TCP 连接成功 → REST 对 GET /events 返回 404 后关闭 → 重连循环，推送永远不来

## 修复
新增 BB_SSE 常量 = 127.0.0.1:8803，SSE 线程改连 BB_SSE（v0.3.0）

## 教训（→ SOP 更新点）
多端口服务（REST + SSE 分离）必须为每个端口定义独立常量；「TCP 能连上」不等于「协议正确」——连接成功可能是连到了错误端口的监听

## SOP 更新
blackboard-mcp-server-design-v1.md 更新端口拓扑（8792 REST / 8803 SSE）
