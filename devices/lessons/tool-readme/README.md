# 设备协调工具集 · Tool README

> 维护：罗盘-mac-mini-设备协调（5a5368af）· 2026-09-06 · R006 十项补全（文档化/版本/CLI 治理）
> 工具路径：~/.dsh/devices/ + ~/dsh-collab/devices/

## 工具清单

| # | 工具 | 版本 | 路径 | 用途 | 依赖 |
|---|------|------|------|------|------|
| 1 | awesun-mcp.py | v1.1.0 | ~/.dsh/devices/awesun-mcp.py | 向日葵 MCP 工具调用（python 版） | python3 + AweSun |
| 2 | awesun-mcp.sh | v1.1.0 | ~/.dsh/devices/awesun-mcp.sh | 向日葵 MCP 工具调用（bash 版） | bash + python3 |
| 3 | mcp-sse-test.js | v1.1.0 | ~/.dsh/devices/mcp-sse-test.js | external-link-mcp SSE 端点验证 | node + MCP SDK |
| 4 | mbp-bus-client.sh | v1.1.0 | ~/dsh-collab/devices/mbp-bus-client.sh | MBP 总线桥客户端（轮询） | curl + python3 |
| 5 | mbp-node-agent.py | v1.1.0 | ~/dsh-collab/devices/mbp-node-agent.py | MBP 节点执行器（黑板任务卡） | python3 |
| 6 | i9-node-agent.py | v1.1.0 | ~/dsh-collab/devices/i9-node-agent.py | i9 节点执行器（黑板任务卡） | python3 |

## 详细文档
- [awesun-mcp.md](awesun-mcp.md) — 向日葵 MCP 工具
- [mcp-sse-test.md](mcp-sse-test.md) — SSE 端点验证
- [node-agents.md](node-agents.md) — mbp-bus-client + mbp/i9-node-agent

## R006 十项对照

| 项 | 覆盖 |
|---|---|
| ⑤ 文档化 | 本目录各工具 README |
| ⑥ 版本管理 | 各工具 v1.1.0 + --version + CHANGELOG.md |
| ⑦ 统一日志 | 各工具 stdout 结构（[test]/log 前缀）；node-agent 结构化输出 |
| ⑧ 自动落链 | 本文档 + CHANGELOG 入 ops-science-research KB |
| ⑨ CLI 治理 | 各工具 --help/--version/usage 自描述 |

## 变更记录

见 CHANGELOG.md

## 凭据纪律

- awesun.env / bus-bridge-token：0600 私有不落共享（token 经环境变量注入）
