# 资源监察面板 · Token Monitor

> 生成：2026-08-18T11:47:59.825Z · 采样 200 事件 / 窗口 5.0 分钟
> 数据源：gov audit_query（工具调用事件=token 消耗代理指标）· 属主：HR 驾驶舱

## 一、Agent 调用强度排行（窗口内）

| 排行 | Agent | 工具调用 | 错误 | 错误率 | 主要工具 |
|---|---|---|---|---|---|
| 1 | a17a52f8 | 78 | 1 | 1.3% | run_code35 agent_send32 gov7 read4 |
| 2 | fa1f9150 | 54 | 0 | 0.0% | agent_send54 |
| 3 | b241741f | 28 | 2 | 7.1% | run_code13 bash13 agent_send2 |
| 4 | e7bfeea8 | 13 | 0 | 0.0% | agent_send13 |
| 5 | 55d4d1bd | 12 | 0 | 0.0% | agent_send12 |
| 6 | 9910d4b2 | 8 | 0 | 0.0% | run_code4 agent_send4 |
| 7 | 5a5368af | 7 | 0 | 0.0% | bash7 |

## 二、工具调用分布

| 工具 | 调用 | 占比 |
|---|---|---|
| agent_send | 117 | 58.5% |
| run_code | 52 | 26.0% |
| bash | 20 | 10.0% |
| gov | 7 | 3.5% |
| read | 4 | 2.0% |

## 三、监察结论与建议

- **热点 agent**：调用强度前 3 名消耗显著，建议错峰/精简（高峰 09-12/14-18 只跑实时必需）
- **错误率预警**：错误率 >5% 的会话提示工具面异常（J37 关联），建议排查
- **配额建议**：基于强度为前台角色设置 gov quota（day/week），超限自动告警
- **精确 token**：工具调用为代理指标；精确 token 需宿主用量 API（待接入，token-ledger.md §五）

---
*resource-monitor v1.0 · 采集=HR(gov audit_query) → 聚合=token-monitor.py → 面板=本文件*