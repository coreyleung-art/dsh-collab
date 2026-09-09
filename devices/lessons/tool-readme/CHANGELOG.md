# 设备协调工具集 · CHANGELOG

## v1.1.0（2026-09-06 · R006 十项补全）
- **awesun-mcp.py/sh**：+VERSION 常量 +USAGE/--help/--version/--list-tools（补 ⑤⑥⑨）
- **mcp-sse-test.js**：+VERSION/--help/--version，SDK require 延迟（--version 免依赖）
- **mbp-bus-client.sh**：+--help/--version 分支（补 ⑨）
- **mbp-node-agent.py / i9-node-agent.py**：+argparse --version（v1.1.0）
- 新增 tool-readme/（README 索引 + 各工具文档 + 本 CHANGELOG）
- 资产登记：device-assets-lessons 更新

## v1.0.x（2026-08-17~08-18 · 初始版本）
- awesun-mcp.py/sh：向日葵 MCP 通道打通（device_search/info/wakeup 实测）
- mcp-sse-test.js：SSE 端点验证（P3 跨设备链路）
- mbp-bus-client.sh：v1.1 协议定稿（数组鉴权 AUTH_ARGS + token tr 去尾换行）
- mbp/i9-node-agent.py：黑板任务卡协议执行器（shell/info/scan/ollama 动作）
