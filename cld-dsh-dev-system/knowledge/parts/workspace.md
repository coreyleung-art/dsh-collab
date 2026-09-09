# 部件卡 · dsh-workspace（工作区注册表 / 会话归属）

> 填卡：2026-09-04 · 依据：官方 workspace.md + 会话消失竞态实证（50467 vs 16870）
> 状态：learned（registry: workspace）

## 1. 一句话定位
用户工作目录的**持久注册表**（stable id ↔ canonical path ↔ title ↔ 归属会话有序账），`ctx.workspaceRegistry`；可选 host 能力，不参与 agent-loop，对模型不可见（无工具/无提示/无会话事件）。

## 2. 概念与定义
- **实体**：`{path(realpath canonical), title, sessionIds 有序}`，id 稳定。
- **Ungrouped**：cwd-less 遗留会话；注册删除后其会话也变 Ungrouped（日志文件不删）。
- **attachSession**：会话创建时由 API gateway 从其 workspace path 定 cwd → create → 校验 header.cwd==workspace path → 挂账。
- **storage domain**：workspace.json（global: initialized/workspaceIds/archivedSessionIds + tables.workspaces），domain spec name=workspace version=2。

## 3. 作用与生命周期
init：`storageDomain.open` → recoverPendingMutation → validate → **若 !initialized: list()+bootstrap（一次性）**；若 initialized 且 table>0: `replaceHeaderIndex(list())`（内存重建，不落盘）→ indexLiveSessions → rebuildEntities。create/delete 走 pending-mutation marker（两写防撕裂，启动按标记恢复；create 中断回滚、delete 中断补完）。

## 4. 约束（红线/不可违）
- **sessionPersistence 依赖强制**：官方原文 "an unavailable persistence peer leaves the plugin **pending** rather than being mistaken for an empty history"——这是防"误判空历史后提交 initialized"的设计。
- **首窗竞态（实证）**：web listen 早于 workspace active 时，renderer 首查命中 pending → UI 空列表不自动重试；关窗重开（dsh 进程不变）即好。重启可能再踩（OP-restart 概率 0.3）。
- workspace.json 的 sessionIds 是**内存态**（72 ≠ 磁盘 191；72=active，归档走 archivedSessionIds），从不随 boot 落盘——勿以文件内容判断 UI 会话数。

## 5. 依赖
- 依赖：`ctx.storageDomain`、`ctx.sessionPersistence`（mandatory startup）。
- 被依赖：dsh-workspace-controller（GUI CRUD）、dsh-session-controller（create-then-attach）。

## 6. 规范要点（标准）
- 会话空诊断：先 P6(session_recovery_check) 判定数据健康 → 健康 = 竞态 → **关窗重开/Cmd+R，勿重启勿动数据**。
- cwd 决定归属：会话的 projectKey 由创建时 cwd 定，与 workspace path 一致才挂账。

## 7. 关联
- 官方文档：`tech-research/dsh-docs/docs/subsystems/workspace.md`（line5/120/122/126/249）
- 工具箱：T1 · 路由表：OP-restart、OP-session-data
- 代码：`dsh-runtime/.../dsh-workspace/lib/index.js`（312 init / 224 domainSpec）
- 存储：`~/.dsh/storages/workspace.json`

## 8. 已知坑 / 待补
- 根因修复方向（runtime restricted）：UI 会话查询失败自动重试 / workspace init 前置 web listen —— 未实施（需完整门禁）。
- archivedSessionIds 与 sessionIds 的关系、归档 UI 行为 —— 待实证。

## 9. 学-建-用 沉淀
- 2026-09-04：工具箱 T1 v1.1（竞态根因 + 关窗重开处置 + doctor 误导警示）；risk-router OP-restart（概率 0.3）；cld-monitor workspace_session_ids 信号。
