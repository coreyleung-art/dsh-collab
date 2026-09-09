# ErrorNet 错误收集网 · 条目库

> 建立: HR 司库 · 2026-09-06 · 来源: i9 协调提案(E1-E6, notes/i9/err-net-proposal-1788701457876)
> 机制: 跨节点统一错误登记 + 自动上报 + 周复盘 → 工具层固化(R-ERR1/2/3 enforced)

## 首批条目(E1-E6 · i9 2026-09-06 通讯排障实证)

| ID | 类别 | 现象 | 根因 | 证据 | 状态 |
|---|---|---|---|---|---|
| E1 | 域错配 | 多节点给 i9 消息写 collab/mbp/mac-mini 域 | 域规范未在工具层固化 | comm-test 等数十键 401 | ✅ R-ERR2 已固化 |
| E2 | 写入BOM污染 | 黑板键 value={} 空对象 | PowerShell Out-File utf8 带 BOM → JSON 解析失败 | starbridge-reply 多次空 | ✅ R-ERR1 已固化 |
| E3 | agent_bus误导 | 跨设备 agent_send 返回 queued/false | agent_bus 仅本机宿主, i9 不在内(设计使然) | mac-confirm 澄清 | 📋 文档化: 跨设备走黑板 notes/i9 |
| E4 | socket耗尽 | executor WinError 10055 | socket 缓冲区耗尽 | executor.log | 📋 i9 侧观察 |
| E5 | SSE假活 | event-bridge 09-04 后 coordinator-* 零事件 | SSE 长连接假活/过滤不匹配 | inbox/events 停更 | 🔍 待排查 |
| E6 | 时间格式混乱 | 键 ts 字符串非毫秒/键名截断 | 各工具时间格式不统一 | central-dualwrite-task-...43N | 📋 统一毫秒 |

## 登记协议(R-ERR3)
1. 节点遇跨设备通讯/写入错误 → 先查本库同类(有则计数合并)
2. 无同类 → 新登记: {id, ts, node, category, severity, desc, root_cause, evidence, status}
3. 处理完 → 标 resolved + prevent_rule
4. 周复盘: mac HR / i9 协调轮值

## 防复发规则(已入规则账本)
- R-ERR1: 黑板写入统一 JSON body 封装
- R-ERR2: 消息域规范(给 i9 写 notes/i9/)
- R-ERR3: 错误登记先查重

---
*ErrorNet v1.0 · HR 司库 · 2026-09-06 · 采纳 i9 提案*
