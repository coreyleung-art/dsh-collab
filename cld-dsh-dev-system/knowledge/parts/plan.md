# 部件卡 · dsh-plan（Plan Mode）

> 填卡：2026-09-05 · 依据：官方 subsystems/plan.md
> 状态：learned（registry: plan）

## 1. 一句话定位
Per-agent 登录态协作状态(ctx.planMode)：active 时 deployment-owned 指引段(plan:policy)进每次模型请求。**soft guidance**——sandbox/approval 独立强制，互不读写 plan state；可选包，agent-loop 不依赖。贡献 plan:policy prompt section + exit_plan_mode 工具 + /plan 命令。

## 2. 概念与定义
- **plan/mode {active}**：log-only whole-value-replace session event——durable/replayable，永不在模型 transcript。
- **Pending selections + pre-step append**：所有 session event turn-enclosed → 用户选择保持 pending 直到下一被接受 in-turn pre-step 在 request 派生前 append。append 唯一点是 running 中 agent 的 prepended `agent/pre-step` listener(先跑下游 listeners 接受才 append)。append 失败不阻塞 turn，选择留 pending。
- **Config**：{section}(缺失/空/非 string/未知 key → plugin load 即 fail)。active 时 section 以 order 50 渲染为 plan:policy 段。
- **exit_plan_mode**：inactive 也注册(进出 plan 只改 prompt 段不改 tool catalog)；mode 外执行 fail。in-plan 需完整 markdown 计划(# heading 开头)，经 user-questions 呈审；批准 → silent pending exit 下个 pre-step append——plan 指引维持到当前 tool batch 结束。keep-planning=failed call 带反馈。
- **/plan**：bare=选 on；非空消息=on + agent.steer() 提交；off=inactive(取消 pending)。

## 3. 作用与生命周期
set(agent,active) → 'committed'(turn 间立即 append)|'queued'(open turn 等 pre-step)|'cancelled'|'noop'。resume/fork/compaction 从 log 恢复。Client 只收 {active, pending}。

## 4. 约束（红线/不可违）
- plan 是 soft——别指望它拦操作(那是 sandbox/approval 的事)。
- turn 尾之后的选择 process-local，进程退即失(README limitation)。

## 5. 依赖
- 依赖 session log/commands(user-questions);被 agent-loop(request 组装)。exit_plan_mode 工具定义见 tool-catalog。

## 6. 规范要点（标准）
- 大改前用 plan mode 呈审(本环境 exit_plan_mode 呈计划等批准)——与 approval fail-closed 配合。

## 7. 关联
- 官方：plan.md · 工具箱：— · 路由：—
- 代码：dsh-plan-mode/lib

## 8. 待补
- plan:policy section 与其他 contributor 的同 order 排序。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
