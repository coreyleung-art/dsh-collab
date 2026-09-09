# 数据资源归属声明 v1.0（外卖域 · 三方确认）

> 状态：✅ 定稿（a3bc8cba + de7b29de 双方确认，总线协调方落盘）
> 维护：Agent Bus（session-fa1f9150-c949-401f-ba8c-d265f6221676）
> 范围：外卖门店多平台管理数据层

## 归属划分

| 资源 | 归属 | 模式 | 说明 |
|---|---|---|---|
| `MTM_DATA_DIR/data/comm.db`（comm_customers / sessions / messages / orders） | **a3bc8cba**（学习系统·历史沉淀端） | 专属写 | 客户沟通学习/范本库 |
| app.db `events` / `im_sessions` | **de7b29de**（实时采集端） | 专属写 | 对方只读导入 |
| app.db `kb_docs` | **a3bc8cba** 可写（学习沉淀） | 可写/对方只读 | 客户沟通范本、操作手册、报告沉淀（修订后归属） |
| app.db `stores` | 双方只读 | 只读 | 基础设施（store.js 内部 CRUD，面板 UI 操作） |

## 衔接与边界

- **衔接点**：a3bc8cba 的 `comm-archive --all` = 读 app.db `im_sessions`（node:sqlite 只读连接、不持锁）+ 写 comm.db —— 无写写冲突。
- **跨域写**：任何一方要写非本域资源（如未来写 kb_docs），先 `agent_light(file:app.db)` 声明 + 对方同意，或走红绿灯锁排队。
- **只读连接**：a3bc8cba 读 im_sessions 不持锁，不阻塞 de7b29de 写入（SQLite WAL 模式下读写并发安全；de7b29de 写入为 upsert 短事务）；shared 读锁仅在需要「读取一致性快照」的场景建议加，日常读无需锁。

## 仲裁

冲突仲裁由 Agent Bus 总线协调：先 `agent_light` 查灯 → `agent_lock(wait:true)` 排队 → 完成 `agent_unlock`。本声明为协作约定 v1（~/dsh-collab）的组成部分。
