# 部件卡 · dsh-session-projection（会话投影）

> 填卡：2026-09-05 · 依据：官方 subsystems/session-projection.md
> 状态：learned（registry: session-projection）

## 1. 一句话定位
SessionEvent 之上的**状态驱动计算单元**：SessionProjectionStateMap(host fold 状态表 merge-extensible) + SessionProjectionMap(client 可见 whole 值)。域为每个 state key 贡献一个 ProjectionDefinition；wire 块使 key client 可见；**渲染属 slot 系统不属本层**。

## 2. 概念与定义
- **ProjectionDefinition**：{key, stateSchema(zod 校验持久态), init(header,inheritedCount)→初始, apply(state,event)→next(纯同步;不关心的事件必须返回**同引用** Object.is→零下游工作), wire?(viewSchema+view(state)→client whole value;live drive 保最近两 raw 结果 Object.is 比较抑制内态变更发布), stateVersion(持久缓存失效号, 序列化字段/fold 语义变则 bump——旧行丢弃非前向应用)}。
- **纯同步强制**：async unit 会撕 carriers 一致性 cut；state 必须 plain JSON(持久缓存前提)。
- **whole-value 事件规则(load-bearing)**：带状态事件载**完整变更后状态**非裸 delta——transition 便宜、served value 自描述(last-wins)。
- **ProjectionSnapshot**：一致读 cut over 全部 client-visible unit;asOfSeq 共享水位(空 log=-1)。

## 3. 作用与生命周期
framework 对每个 committed event 驱动各 unit apply → 状态折叠 → wire view 发布 client。host-only unit 无 wire。registry ctx.sessionProjections / ctx.sessionProjectionCache。

## 4. 约束（红线/不可违）
- apply 纯同步 + 不感兴趣事件返回同引用(否则下游无谓工作)。
- 带状态事件须 whole-value 非 delta。
- stateVersion 变了必须 bump——否则陈旧投影污染。

## 5. 依赖
- 依赖 session log(事件源)/zod；被 UI(client 值)/host 查询消费。

## 6. 规范要点（标准）
- 诊断"UI 状态不更新/旧值"：投影 unit apply 引用语义 / stateVersion 陈旧 / 事件非 whole-value。
- 自研投影式状态(如 gate-state)参照：whole-value + 纯 fold + 版本号。

## 7. 关联
- 官方：session-projection.md · 工具箱：T1 · 路由：—
- 代码：dsh-session-projection{,-cache}/lib

## 8. 待补
- 实际 unit 例子(workspace/telemetry 用)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
