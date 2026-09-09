# 部件卡 · dsh-agent-team（Agent 团队 / 实验性 Team 域）

> 填卡：2026-09-05 · 依据：官方 subsystems/agent-team.md
> 状态：learned（registry: agent-team）

## 1. 一句话定位
实验性 implicit-root **Team 域**共享类型（身份/邮箱/任务 DAG/host adapters）：TeamId = root SessionId（distinct brand）；模型工具 + host 适配器围绕它组多 agent 协作。ctx.agentTeams(TeamService) 是私有 opt-in 协调接缝（非 agent-loop 脊柱）。

## 2. 概念与定义
- **TeamId** = root SessionId(brand)；**TeamTaskId** = Team-local 单调 `task-<n>`；**TeamMessageId** = 全局随机。
- **TeamMemberSnapshot**（每次 teammate 生命周期变更整值写）：{id(持久身份), name(不可变 label), description, provider, context:'fresh'|'fork', phase, error?}。成员从 provisioning 起 → 恰一个终态 roster phase：active|failed；running/idle/inactive 是**派生 status 永不重写该记录**。
- **Durable mailbox**：Lead Session 先存完整 queued message；target receipt 仅在其 pending inbox item 或 user/message 落盘后 ack——queued-minus-delivered = 恢复邮箱。
- **TeamMessageSnapshot**：{id, senderId, senderName, targetId, content}。
- **Shared task DAG / Replay**：团队任务图 + 日志回放（详细见 Agent Note）。

## 3. 作用与生命周期
Lead(implicit root) 建 team → provisioning 成员(各持 Session) → 邮件投递(先持久后 ack) → 任务 DAG 流转 → 成员 active/failed 终态。host adapter(agent 总线类) 消费。

## 4. 约束（红线/不可违）
- 实验性/opt-in——非默认脊柱，别当核心依赖。
- roster phase 与运行时 status 分离：勿以 running/idle 改写 active/failed 记录。
- 邮件先持久后 ack（投递可靠性）。

## 5. 依赖
- 依赖 agent-core(session/agent)/branded ids；被模型 team tools 与 host 适配器消费。本环境 agent 总线(agent_send/peers/broadcast)是同类机制的宿主实现。

## 6. 规范要点（标准）
- 跨 agent 协作设计参照：Lead-root + 持久邮箱(先持久后ack) + 单调任务 id + phase 终态。
- 诊断多 agent 消息丢失：查 queued-minus-delivered 恢复邮箱语义。

## 7. 关联
- 官方：agent-team.md、subagent.md · 工具箱：— · 路由：—
- 代码：dsh-agent-team(experimental)/lib

## 8. 待补
- 与本环境 agent-bus 的异同对照(结构 vs 语义)可做一次。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
