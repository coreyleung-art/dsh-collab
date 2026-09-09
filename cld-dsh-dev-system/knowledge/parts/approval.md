# 部件卡 · dsh-user-approval（用户审批接缝）

> 填卡：2026-09-05 · 依据：官方 subsystems/approval.md
> 状态：learned（registry: approval）

## 1. 一句话定位
[dsb-user-approval] 回答一个问题：**此具体动作可否继续**？own 共享 request/outcome 词汇 + `ctx.approval` dispatch + `approval/request` answerer waterfall + log-only audit 对 + per-session ask/never 策略。UI 渠道提供 human answerer；ACP bridge 提供一次性机器决定。

## 2. 概念与定义
- **ApprovalRequestId**：每次 request 全新 Branded id——pair approval/asked↔approval/decided，不与 tool-call/agent/session id 互换。
- **ApprovalOutcome(closed, fail-closed)**：'allowed-once'(只授所问动作) | 'rejected' | 'cancelled' | 'unavailable'(缺失/非owning/throw/不合规 answerer → unavailable 而非开门)。
- **ApprovalPolicy**：'ask'(默认, 委托 answerer 链, 无 answerer → unavailable) | 'never'(确定性 rejected, 不 dispatch——CI/无人值守)。effective = session log 最后一个 approval/policy 事件，fallback 服务 config；setApprovalPolicy 是唯一写路径(回放可重建)。
- **ApprovalRequest**：{agent(路由+audit), toolName, callId(关联已展示的 tool call——**不复制参数**, 防第二份漂移)}——略参数。
- **dispatch 与 audit**：callers(tools/tool-bash) 消费 closed outcome，**非 allowed-once 即 fail closed**。

## 3. 作用与生命周期
tools 请求前(pre-execute gate) → ctx.approval.request → answerer 链(按 session policy) → outcome → allowed-once 才执行。sourced user/message 是持久 model-visible 输入；改 policy append 新 full snapshot 不重写 header 的 system prompt。

## 4. 约束（红线/不可违）
- fail-closed：unavailable/rejected/cancelled 一律拒绝——**缺失 answerer 不会开门**。
- 本环境实证：DSH 审批弹窗/agent_approval_* = 此接缝的一个 answerer 通道。

## 5. 依赖
- 被依赖：tools/tool-bash(执行前)。依赖：session log(policy 事件)、answerer 组合(UI/ACP)。

## 6. 规范要点（标准）
- 高危操作(改底层/重启/删数据)走 approval——fail-closed 保证无人审时拒。
- guard-gate 与 approval 分工：gate=agent 自锁，approval=human/机器裁决——双层。

## 7. 关联
- 官方：approval.md · 工具箱：— · 路由：—
- 代码：dsh-user-approval/lib；本会话审批工具(agent_approval_*)即 answerer 实例。

## 8. 待补
- answerer 组合链与 UI 弹窗如何注册(改 host 插件时)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
