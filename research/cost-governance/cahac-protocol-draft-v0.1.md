# CAHAC 协议层标准 · 草案 v0.1

> Cost-Aware Hybrid Agent Communication Protocol · 起草：2026-08-19 · HR 驾驶舱
> 定位：多智能体通信的**成本感知通道选择协议**（对标 A2A/MCP，差异化=按消息类型路由通信模式 + 回执-状态去耦 + 预算内建）
> 状态：草案（DRAFT）——供评审/试点，非强制

---

## 1. 协议目标与设计原则

1. **成本内建**：每条通信自带成本权重，通道选择器选最省模式
2. **消息-状态去耦**：确认/状态不进消息流，进共享黑板
3. **预算内建**：每会话配额+熔断是协议一部分（不是外部附加）
4. **渐进兼容**：软实现（纪律层）先行，硬实现（基础设施层）后行
5. **可审计**：全部通信可追溯（消息 ID/黑板版本/事件日志）

## 2. 消息分类法（Message Taxonomy）

| 类型 | 代码 | 定义 | 通道 | 必答 | 成本权重 |
|---|---|---|---|---|---|
| 实质任务 | TASK | 委派执行并回报 | 点对点 | 是 | 高（但低频） |
| 协作协商 | COLLAB | 多轮对齐/方案讨论 | 点对点（线程内） | 是 | 中 |
| 状态更新 | STATUS | 进度/资源/告警状态 | **黑板**（禁消息） | 否 | 低（一次写 N 读） |
| 确认回执 | ACK | 「收到✓」 | **黑板**（禁消息） | 否 | 极低（目标消灭） |
| 事件通知 | EVENT | 触发式告警 | 事件驱动 | 否 | 低（按订阅） |
| 批量任务 | BATCH | 低优先级队列 | 邮箱（文件） | 异步 | 低（增量读） |
| 全员广播 | BROADCAST | 紧急/制度/窗口 | 广播 | 是 | 最高（限三类≤月几次） |

## 3. 通道选择器（Channel Selector）规则

```
def select_channel(msg):
    if msg.type == "ACK" or msg.type == "STATUS":
        return "blackboard"          # 状态去耦：一次写 N 次读
    if msg.type == "BATCH":
        return "mailbox"             # 文件队列：增量处理
    if msg.type == "BROADCAST" and msg.urgency in ("emergency", "policy", "restart"):
        return "broadcast"           # 三类白名单
    if msg.type == "EVENT":
        return "eventbus"            # 有事件才唤醒
    return "point-to-point"          # TASK/COLLAB 保留直连
```

**成本权重表**（用于预算核算）：broadcast=10× / p2p=1× / event=0.5× / blackboard 读=0.1× / mailbox=0.05×

## 4. 黑板协议（Blackboard）

- **命名空间**：topic（如 ops.status / task.registry / alert）
- **写权限**：topic 属主制（红绿灯已有），写前查灯
- **版本与 TTL**：每条状态带 version + ttl；过期自动清理
- **订阅通知**：读者可选订阅（事件驱动模式），默认拉取
- **审计**：状态变更留痕（谁/何时/旧值/新值）
- **我们已有雏形**：resource-registry.md / pending-work-plan.md / 告警状态 = 黑板前身

## 5. 邮箱协议（Mailbox）

- **文件格式**：JSON 或 Markdown 任务卡（id/task/priority/deadline/owner）
- **目录**：~/dsh-collab/mailbox/<agent>/inbox/（代理读自己的 inbox）
- **入队**：投递方写文件；**出队**：处理完移 done/ + 日志
- **优先级**：文件名前缀（P0/P1/P2）
- **防积压**：TTL 清理 + 容量上限（如 ≤100 文件）

## 6. 事件协议（Event）

- **事件 schema**：{id, ts, source, type, payload, dedup_key}
- **幂等**：dedup_key 保证重复事件不重复处理
- **持久化**：事件日志 append-only（可重放）
- **唤醒**：订阅者按事件类型唤醒（替代轮询）

## 7. 预算协议（Budget）

- **每会话配额**：day 级（gov quota 已落地：500M tokens/日）
- **熔断**：日成本 >¥100 → 自动降级/回退（护栏）
- **任务级预算**：TASK 消息自带 cost_cap（Runcap 思想）
- **日审**：token-roi-review.py 产出 + 异常标红

## 8. 安全与审计

- 消息签名（可选，v0.2）；全量审计（已有 agent_thread/gov audit）
- 最小权限：黑板写权限分级；广播白名单
- 脱敏：日志/论文输出前 PII 脱敏

## 9. 版本与能力发现（对标 A2A Agent Card）

- **协议版本**：cahac/v0.1
- **Agent Card 扩展**：每会话声明 {channels: [p2p, blackboard, mailbox, eventbus], budget: {day_tokens}, topics: [...], comm_style: [task_collab]}
- **兼容**：未实现 CAHAC 的会话默认走 p2p（向后兼容）

## 10. 落地路线（软→硬）

| 阶段 | 内容 | 机制 |
|---|---|---|
| S1 纪律层 | ack 免回/状态写登记表（已执行 90%） | 行为规范 |
| S2 协议层 | 消息分级+通道选择器（Runbook 固化） | 文档+检查单 |
| S3 基础设施层 | 黑板/邮箱/事件总线落地（需宿主支持评估） | 插件/脚本 |
| S4 标准化 | Agent Card + 对外发布（论文/开源候选） | 标准文档 |

---
*CAHAC v0.1 DRAFT · HR · 2026-08-19 · 对标 A2A/MCP；差异化=成本感知通道选择+回执状态去耦+预算内建*