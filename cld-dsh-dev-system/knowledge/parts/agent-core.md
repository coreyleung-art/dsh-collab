# 部件卡 · dsh-agent-core（Agent 核心 / 六包脊柱）

> 填卡：2026-09-05 · 依据：官方 subsystems/core.md 全文(1148行)
> 状态：learned（registry: agent-core）

## 1. 一句话定位
agent-loop 脊柱的六包组合：一个 turn 流经 session(日志/单一真相) → system-prompt(请求组装) → tools(工具) → agent(接口/注册表) → agent-loop(驱动) → scope(per-agent 注册原语)，每个 model-visible 事实 append 回日志后下一步才从它派生。

## 2. 概念与定义
- **六包职责**：session(ctx.sessions append-only log 单一真相)/system-prompt(ctx.systemPrompt)/tools(ctx.tools)/agent(ctx.agents, Agent接口+live registry+initiator scope+agent/* 事件)/agent-loop(ctx.agentLoop 唯一具体驱动)/scope(无服务库, 在其下防环)。
- **AgentHandle**：{agent, dispose()}——dispose 是 **CAPABILITY**（只有持有者能 tear down）；provider unload 停+drain 它做的所有 live handle。dispose = stop loop→await exit→unregister→从 store 移除 session→unwind scoped world。
- **创建**：create(新 session+agent, caller 给 SessionId) / resume(先 load persisted session)；AgentSetup 在两个 id 未发布时组 scoped world——agentCtx 注册先于 agent/created 与首个 prompt；setup 拒/commit 抛/owner dispose → **事务回滚不发布任何 id**。
- **Agent 接口**：id/options/session/inbox/status/ctx + cancel(cause,{keepInbox})/whenIdle()/runMaintenance(task)/send(message,target,wakeup)/followup/steer/inject(定 preset 别名)。
- **send 语义**：identified input → inbox 边界 + 可选 wake driver；wake 在 idle 总开 turn 边界；cancel 后 wake → 下轮跑。
- **withInitiator()**：每个 driver 在 ctx.agents.withInitiator() 内跑——extension 依赖 agent(需 initiating Agent) 而非 agent-loop(保 loop 可换)。

## 3. 作用与生命周期
loop 驱动一轮 turn：claim prompt → session 开 turn → system-prompt 组装前缀 + 从 log 派生 history → LLM stream → tools dispatch → 所有 model-visible 事实 append 日志。agent/created→(agent/status 镜像 lifecycle)→agent/disposed。

## 4. 约束（红线/不可违）
- agent-loop 是唯一具体 Agent 实现；外插件依赖 agent 接口不依赖 agent-loop（loop 可换）。
- dispose 是能力非方法——非持有者不能拆 agent。
- setup 在发布前组 scoped world；失败事务回滚两 id。
- agentCtx 注册 agent-local、dispose 时 unwind、之后拒绝再注册（同 scope 卡）。

## 5. 依赖
- agent-loop 依赖 session/system-prompt/tools/scope；agent 依赖 session。ctx.agentDefaultModel/agentPresets 配模型与预设。
- agent/* 事件: created/disposed/error/status。

## 6. 规范要点（标准）
- 诊断"agent 行为异常/会话不推进"：按六包定位——日志没 append？prompt 组装？tool dispatch 卡？loop 没 claim？scope 错挂？
- 会话不可恢复时：resume() 先 load persisted——区分 live 丢失 vs persisted 损坏。

## 7. 关联
- 官方文档：core.md · 工具箱：T1/T5 · 路由：无直接 OP
- 代码：dsh-agent/dsh-agent-loop/dsh-system-prompt 等
- 知识：session/scope/tools-exec/llm-streaming(待) 卡

## 8. 待补
- agentPresets 组合语义(当前 profile 用什么 preset)。
- follow/control stream 与 Agent.send 的关系(web-client 卡衔接)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
