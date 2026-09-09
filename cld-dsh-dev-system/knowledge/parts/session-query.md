# 部件卡 · dsh-session-query（会话查询 / 全文本索引）

> 填卡：2026-09-05 · 依据：官方 subsystems/session-query.md 全文
> 状态：learned（registry: session-query）

## 1. 一句话定位
**查询词汇表 over live-preferred 逻辑会话语料**：Service Definition(dsh-session-query, `ctx.sessionQuery`) 管精确读/来源优先级/关系追踪/语义提取/provider 无关过滤器；SQLite provider(dsh-session-query-sqlite) 管具体全文本索引生命周期。**注：UI 侧栏会话列表来自 workspace registry（见 web-client/workspace 卡），本引擎服务搜索/精确读**。

## 2. 概念与定义
- **SessionRecord**（cross-corpus list 返回）：cloned live-preferred header + `live`(在 ctx.sessions) + `persisted`(persistence backend 列出) 独立暴露来源可用性。
- **SessionEventSurface**：'current'(模型上下文) | 'shadowed'(被替换) | 'log-only'(仅 raw log)。
- **SessionLogSnapshot**：完整 detached replay-validated raw log（resume preflight 用）。
- **SessionSurfaceSnapshot**：单次精确读 surface 观察（非保留订阅）。
- 分类用与 model-history 推导相同的 foldSurface() 转换。
- full-text search pages 由 sqlite FTS 支撑（provider 拥有索引生命周期）。

## 3. 作用与生命周期
提供者注册 ctx.sessionQuery；查询方(list/search/exact reads)用它读 live-preferred 语料（live 优先于 persisted）。索引由 provider 维护（sqlite FTS 生命周期）。

## 4. 约束（红线/不可违）
- live-preferred：live session 优先于 persisted 快照——同一 id 以 live 为准。
- 精确读返回 detached snapshot，非订阅——勿当实时流用。
- SQLite provider 的索引是派生物：语料变更需索引生命周期跟上（重建语义见 provider）。

## 5. 依赖
- 依赖 ctx.sessions(live) + sessionPersistence(persisted)；provider 依赖 sqlite 介质。
- 被依赖：搜索 UI / resume preflight / workspace 会话归属校验(header)。

## 6. 规范要点（标准）
- 会话"找不到/搜索不到"诊断：先分 live vs persisted（SessionRecord.live/persisted 位）；两者都假 = 真不在语料。
- 全文本索引落后 = 搜不到新会话内容 → provider 索引重建（勿当数据丢失）。

## 7. 关联
- 官方文档：session-query.md · 工具箱：T1（会话搜索相关）· 路由：无
- 代码：dsh-session-query{,-sqlite}/lib/ · 知识：persistence/session/workspace 卡

## 8. 待补
- UI 搜索走本引擎还是 workspace filter 的实证边界（ui-workspace client search deriveSearchResults 见 workspace 卡 §调研）。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
