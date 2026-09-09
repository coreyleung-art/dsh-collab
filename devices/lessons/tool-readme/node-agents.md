# 节点/客户端工具 · mbp-bus-client · mbp/i9-node-agent

> 版本 v1.1.0 · 维护：罗盘 5a5368af · 2026-09-06 R006 补全

## mbp-bus-client.sh（MBP 总线桥客户端）
- 用途：MBP 节点轮询 mac-mini bus-bridge（8791）收任务并回报
- 用法：`bash mbp-bus-client.sh {start|stop|once|--version|--help}`
- 协议：GET /bus/receive?target=mbp-node → POST /bus/reply
- 配置 env：BUS_BASE / TOKEN_FILE(0600) / POLL_INTERVAL(5) / TASK_TIMEOUT(60)
- 依赖：curl + python3（macOS 自带）
- 成本治理：轮询已停，恢复待协调者广播

## mbp-node-agent.py / i9-node-agent.py（黑板任务卡执行器）
- 用途：MBP/i9 节点执行黑板任务卡（shell/info/scan/ollama/dsh 动作）并回报
- 用法：`python3 X-node-agent.py --node-id <mbp|i9> --blackboard http://100.120.203.20:8792 [--once] [--interval 15] [--version]`
- 协议（node-relationship-model）：
  - 中枢 PUT /tasks/i9/cmd（固定 key，body={task_id,action:shell,payload:{cmd}}，显式 Content-Length）
  - 节点 GET /tasks/i9/cmd → 执行 → PUT /tasks/i9/result → DELETE /tasks/i9/cmd
- **坑**：payload 字段是 `cmd`（非 command）；Content-Length 必须显式；GET 读 queue/<ts> 会 not found（i9 轮询 cmd 固定 key）
- 标准库（urllib/subprocess），Windows/macOS Python3 直跑

## 文档索引
- 向日葵 MCP：awesun-mcp.md
- SSE 验证：mcp-sse-test.md
