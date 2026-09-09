# 企微办公模块接入外链体系 · 需求梳理

外链通讯员 92623479 · 2026-08-21 · J42 需求确认文档

## 状态：✅ 已实现（2026-08-21）

- 6 个 office.* 工具已上线（MCP 8910，tools 列表 9 个）
- 实测通过：todo.list / doc.search / todo.create（读写全通）✅ 测试数据已清理
- 待办/日历/文档模块绕过 853006 可用；消息正文仍受限（长连接为主通道）

## 背景

企业微信 5.0.10 开放 CLI/MCP，实测 @wecom/cli v1.1.0 办公模块（待办/日历/文档等）绕过 853006 企业规模限制可用（消息正文仍受限）。用户确认：把办公模块接入外链体系。

## 目标

在 external-link-mcp（MCP 服务器 + webhook 8790 同体系）增加办公模块工具，agent 可原生调用：
- 待办：创建/查询（todo.create / todo.list）
- 日历：创建/查询（calendar.create / calendar.list）
- 文档：创建/搜索（doc.create / doc.search）

## 工具设计（薄壳模式，同 channel.send 风格）

| 工具 | 参数 | 实现（wecom-cli 子命令） |
|---|---|---|
| office.todo.create | {items:[{title, description?, due_date?, participants?}]} | `todo create --items <json>` |
| office.todo.list | {} | `todo list` |
| office.calendar.create | {subject, begin_time, end_time, description?, location?} | `calendar schedules create` |
| office.calendar.list | {begin_time?, end_time?} | `calendar schedules list` |
| office.doc.create | {doc_name, content?} | `doc create --doc-name --content` |
| office.doc.search | {keywords} | `doc search --keywords` |

## 分级与审批（J45）

- 查询类（list/search）：L0/L1 自动
- 创建类（create）：L1 宽松（写台账 approval-ledger.md）——非破坏性、可撤销（待办/日程/文档创建）
- 命中硬性升级（外部承诺/跨域等）：L3 用户确认

## 实现步骤

1. external-link-mcp/index.js 加 office.* 工具（6 个，stdio + SSE 双模式）
2. webhook 8790 加 office 转发端点（脚本可调，如 /office/todo/create）
3. 测试：todo.create 创建一条测试待办 → todo.list 验证
4. 文档更新（介绍页能力清单 + 契约）

## 待确认

- 工具前缀：office.* vs 独立命名？（建议 office.* 清晰）
- 是否需要 webhook 转发端点（脚本用）？（建议加，与 /send 同模式）
- 智能表格（smartsheet）AI 分析报告是否本轮接入？（建议下一轮，需大圆/官方确认）

确认后实施。
