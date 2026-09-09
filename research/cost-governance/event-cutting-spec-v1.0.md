# 智能体行为事件切割规范 v1.0

> 建立：2026-08-19 · HR · 用途=CAHAC 离线回放的统一切割定义（所有智能体行为 → 7 类）
> 数据源适配：agent_send 内容分类 / 工具调用映射 / 面板告警 / 广播

## 一、切割规则（行为 → CAHAC 类）

| CAHAC 类 | 切割规则 | 判定示例 | 通道权重 |
|---|---|---|---|
| ACK | agent_send 确认回执（短消息 <120 字，含收到/收悉/✓/🤝/保持联动/确认在案） | 「收到 ✓」「🤝 确认在案」 | 0.05 黑板读 |
| STATUS | 状态汇报/登记/进度/结果（已登记/已更新/状态/回报/完成/落盘）+ gov 治理操作 | 「已登记 v1.0.260」「状态：DONE」 | 0.10 黑板写 |
| TASK | 任务委派/请求执行（请/执行/调查/查找/回复/分析）+ 执行类工具（run_code/bash/read/edit/write） | 「请查 phoneuse」「run_code: ...」 | 1.0 p2p |
| COLLAB | 线程内多轮实质讨论（≥200 字或含方案/对比/分析） | 深度分析消息 | 0.8 p2p-thread |
| EVENT | 告警/事件（new_order/delivery/refund/异常/离线/风控） | 面板告警、异常通知 | 0.5 事件总线 |
| BATCH | 批量任务（知识库批量入库/批量文件/批量操作） | knowledge_add 多篇、批量导出 | 0.05 邮箱 |
| BROADCAST | 广播（kind=broadcast，白名单三类） | 重启窗口/制度发布/重大事件 | 10.0 广播 |

## 二、工具调用映射（非 agent_send）

| 工具 | 映射 | 说明 |
|---|---|---|
| run_code/bash | TASK（执行） | 代码/命令执行面，CAHAC 下走本地路由+压缩 |
| read/edit/write/glob/grep | TASK（文件） | 文件操作 |
| gov | STATUS（治理） | 策略/配额/审计 |
| knowledge_* | BATCH（知识） | 批量入库 |
| agent_light/lock/unlock | STATUS（红绿灯） | 资源状态 |
| validate_dsh_ui/render_ui | TASK（输出） | 界面产出 |

## 三、切割执行

1. agent_send：按消息内容启发式分类（ACK/STATUS/TASK/COLLAB/EVENT/BROADCAST）
2. 非 agent_send 工具：按上表映射
3. 面板告警：EVENT 类（按 kind 细分）
4. 归因比例（成本结构）：通信 40% / 执行 35% / 自动化事件 25%（12.8h+峰值归因实测校准）

---
*切割规范 v1.0 · HR · 2026-08-19 · 配套 cahac-replay-week.py*