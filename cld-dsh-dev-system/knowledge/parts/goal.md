# 部件卡 · dsh-goal（同会话目标）

> 填卡：2026-09-05 · 依据：官方 subsystems/goal.md
> 状态：learned（registry: goal）

## 1. 一句话定位
Same-session goal：一个直接 human 请求 → 一个持久化 completion objective，可跨自动轮继续。GoalId branded；caller 经 GoalRef 改**恰好一个 revision**，每次 durable mutation 递增 revision(CAS)。

## 2. 概念与定义
- **GoalRef**：{id, revision>0}。**GoalPhase**(durable)：active|paused|blocked|complete；activation(能否续轮)是 **process-local 分离**的。blocked 是唯一 durable 停因状态，带 {code(lower-kebab 路由), message}。
- **GoalSnapshot**：Ref + objective + phase + blockedReason?(仅 blocked)+ maxGoalRounds。**GoalView** = Snapshot + 派生值(roundsStarted/createdAt/updatedAt 等)。
- **Requests**：Create{objective, maxGoalRounds?→服务 config 解析}; Edit(至少一字段); GoalChanged 通知(带 accepted operation+exact revision, clear 省略 goal=tombstone)。
- **Service**：strict replay from `goal` projection；enforce exact-live-agent identity + CAS；发 goal/changed。首依赖访问时 projection 缺失 → fail。

## 3. 作用与生命周期
create → roundsStarted 递增(自动续) → phase 迁移(active/blocked/complete) → clear(tombstone)。回放严格可重建。

## 4. 约束（红线/不可违）
- 只改自己精确 revision(CAS)——别人改了先重读。
- durable phase ≠ activation：rounds 已满但未 complete 仍可(不许)续——activation 策略单独判。
- blocked 需 code 路由(同一阻塞条件持续 N 轮才 blocked——本环境实证)。

## 5. 依赖
- ctx.goals 依赖 session log(projection)；被 agent-loop 续轮驱动。本会话 goal 工具(create/get/update)= 界面实例。

## 6. 规范要点（标准）
- 长期修复目标用 goal 跨轮自动推进(如本 12 轮学习目标)；单轮任务不用。
- 报告 blocked 前须同条件 ≥3 轮实证(本环境规则)。

## 7. 关联
- 官方：goal.md · 工具箱：— · 路由：—
- 代码：dsh-goal/lib

## 8. 待补
- projection 注册点(goal unit)与回放边界。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
