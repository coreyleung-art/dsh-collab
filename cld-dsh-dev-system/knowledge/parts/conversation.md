# 部件卡 · dsh-conversation（会话组装 / 事件→视图）

> 填卡：2026-09-05 · 依据：官方 subsystems/conversation.md
> 状态：learned（registry: conversation）

## 1. 一句话定位
Client `SessionEventLikeEntry` 窗口与 browser views 之间的 **target-neutral 组装层**：ui-conversation own event/view registry + 每 SessionBinding 一个 identity-stable binding + Turn/Step Location + 增量 Context 组装 + shared shell + 输入编排。Target 包(ui-chat/ui-trajectory)own 各自 Definition/最终 snapshot/渲染。

## 2. 概念与定义
- **数据模型**：SessionEventLikeEntry = {type:'event', event}|{type:'chunks', event:ChunkRowEvent}——均暴露 type/seq/time/data；assembler 直接消费不另开 history 流/不转换/不展开 packed。每 Session 一个 ConversationNodeAssembler 应用全部注册 Definition 并为每个 view target 发独立 source。
- **四概念**：Event Definition(业务包配对事件, 稳定 (kind,id) 关联, 折叠确定性 State, 可物化 target node) | Context(引擎 own 有序 Matches+State, packed run 占一个 update Match) | Location(引擎 own Session/Turn/Step 坐标, 从 durable boundary events 派生) | View Definition(target 包每 Session 一个增量 builder, own 最终 snapshot 型) | View(Slot 如 Chat/Trajectory 只读自己 snapshot 渲染)。
- **Target activation**：创建/读 source 不激活；shell 显式激活(首激活建 builder + 一次 replace()；后续 flush 对每个 active target 调 apply())。assembler 只收 resolved target id，**不默认选 Chat**。
- **Replayable event families**：写 Definition 前定一个稳定业务 id；同一 node 的所有事件带该 id 或自派生——**client 永不把 update 赋给 "latest unfinished" Context**。每 (kind,id) 至多一个 start；whole-value checkpoint 优于 delta(窗口外 start 也有用)。
- **Chunk rows**：历史连续同块 assistant/chunk 增量以 chunkrow/* 到达(text/reasoning/tool-call-chunks)——Client-only 只能 update，start() 收标准 SessionEvent。

## 3. 作用与生命周期
window 更新 → assembler(每 active target) → Definition match/update 折叠 → target snapshot → Slot view 渲染。Chat/Trajectory 可认同一事件族但各自 State/node 独立。

## 4. 约束（红线/不可违）
- Definition 必须确定性 replay(升序 seq)——勿依赖 live-only memory。
- 窗口只有 update 时 pending Context 不建 State，直到旧页补 start。
- 渲染依赖 → 终端/checkpoint 事件须带足够 whole fallback state。

## 5. 依赖
- 依赖 web-client(模型)/session；被 view 包(chat/trajectory/三方) 消费。自定义 Definition = 业务事件 UI 化路径。

## 6. 规范要点（标准）
- 想让某业务事件进 UI(像 review/approval 卡片)：写 Event Definition(稳定 id+确定性 State)+ View 贡献 —— 勿 hack 渲染层。
- 诊断"会话里某类节点不显示"：查 Definition 配对/State 折叠/start 是否在窗口内。

## 7. 关联
- 官方：conversation.md、web-client.md · 工具箱：— · 路由：—
- 代码：dsh-client-ui-conversation、dsh-client-ui-workspace(client 组装参照)

## 8. 待补
- 具体业务 Definition 实例(client 插件如何注册)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
