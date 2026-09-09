# 部件卡 · dsh-todo（待办清单）

> 填卡：2026-09-05 · 依据：官方 subsystems/todo.md
> 状态：learned（registry: todo）

## 1. 一句话定位
[dsh-tool-todo] durable todo 词汇：model-facing 工具**整体替换**一个 agent session 的整个列表；包也 own 事件声明、回放投影与 invariant companion。

## 2. 概念与定义
- **TodoItem**：{content(短祈使行, UI 显示), status:'pending'|'in_progress'|'completed'}——**刻意最小**：无 id/priority/activeForm——列表每次写**整体替换**(last-write-wins)，条目无需稳定身份。in_progress 可多条目并行。
- **todo/write 事件**：{todos: TodoItem[]}——declaration-merge 进 SessionEventMap，**log-only**，带完整替换列表。
- **Invariant companion**：一遍验证 existing+newly announced sessions，然后增量跟踪 committed turn boundaries——每个 live todo/write append 前被查，不重扫 log。

## 3. 作用与生命周期
模型/agent 写 todo/write(整体快照) → 事件入 session log → 投影重建列表 → UI/模型读当前全量。回放一致性由 invariant 保。

## 4. 约束（红线/不可违）
- 全量替换语义：发 todo/write 必须带**完整**列表(不是增量 diff)——丢条目=真丢(无 id 无 merge)。
- log-only：todo 状态从 log 投影，不回写别处。

## 5. 依赖
- 依赖 session log；被 agent-loop/todo 工具消费。本环境 todo_write 工具(全量替换清单)= 界面实例。

## 6. 规范要点（标准）
- 每次 todo_write 发全量(保留未完成项+新项)——验证本会话惯例(每轮整表重发)。
- 并行任务可多 in_progress；完成即标。

## 7. 关联
- 官方：todo.md · 工具箱：— · 路由：—
- 代码：dsh-tool-todo/lib

## 8. 待补
- invariant 详细(committed turn boundary 跟踪)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业——印证 todo_write 全量惯例。
