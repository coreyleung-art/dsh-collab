# 队列积压治理规划 + 业界去重/语义合并调研结论

> 2026-10-03 · 依据：i9 2797 积压事故 + 本机 581 积压实测 + Tavily 业界调研（用户指示）

## 一、业界方法结论（调研证据）

### 1. 队列去重：业界共识 = 「恰好一次 = 至少一次投递 + 幂等键 + 去重存储」
- Kafka：幂等生产者 + 事务消费者；代价高（HN 讨论共识：多数系统用 at-least-once + 幂等消费者更划算）。
- 通用模式：**幂等键（idempotency key）**——稳定键 + 持久去重表；重复投递时消费者按幂等键跳过。
- **对照我们**：内容指纹去重键（key#fingerprint）+ seen 成员集合 = 正是幂等键模式 ✅ 已对齐。缺口：seen 表**进程内/容量有界**（FIFO 2000），重启即失——长期防重需持久化（bb-sub 已有 seen 边车文件，central-inbox 未持久化，列为补项）。

### 2. 语义合并：业界两个流派
- **LLM 语义去重**：SemanticDeduplicator（gkamradt）/ LOTUS sem_dedup——按语义合并冗余条目（非逐字相同也合并）。
- **消息历史压缩**：rolling summary + 动态截断 + 保留最近全文（agentailor/slimcontext 模式）。
- **对照我们**：rust-tools `queue-condense`（去重→bge-m3 聚类→qwen 归纳→写黑板）就是这两个流派的合体 ✅ 方向正确。缺口：只做过单次运行，未挂定期调度；归纳结果的「原文可追溯」链需保留（DLQ 不删除已保证）。

## 二、积压治理规划（四层，全部已有组件，只差编排）

| 层 | 机制 | 现状 | 动作 |
|---|---|---|---|
| L1 发端限速 | 方案 A-2：同 from→to 10 分钟 >10 条降级 inject + rate_limited 标注 | ✅ 已实现（1.5.9 批） | 随重启生效；观察期 7 天 |
| L2 死形态清理 | bus-queue-triage：空 to/裸 UUID/角色标签/占位 id/短 id 歧义 → expired（DLQ 不删除） | ✅ 工具 v1.0.0（插件+CLI） | 挂定期 cron（见下） |
| L3 超龄回收 | A2 TTL 7 天 queued → expired | ✅ 已有 | 保持 |
| L4 语义合并兜底 | queue-condense：积压 → 去重/聚类/归纳 → 黑板汇总 | ✅ 已有 | 挂月级调度 + 原文可追溯链接 |

### 调度编排（新增 2 个 launchd/cron）

1. `com.dsh.cron.bus-triage`（每周一 09:00）：`node ~/dsh-plugin-bus-queue-triage/cli.js --scan` → expireable>0 时把报告写黑板 data/ops/bus-triage-weekly（只报告不处置；处置走人工窗口——CLD 停止期间 --apply，护栏强制）。
2. `com.dsh.cron.queue-condense`（每月 1 日 09:30）：`dsh-tools queue-condense --condense --to <协调者>`（积压语义归纳；仅当 queued > 阈值 100 触发，防空跑）。

### 验收判据
- 每周 triage 报告：queued 死形态占比趋势下降；expired 数稳定（不再 2797 级突增）。
- 观察期 7 天后：同对限速触发次数与误伤率（合法高频协作对是否被误限——若误伤，N 上调到 20）。

## 三、已落盘实现（本轮）

- 方案 A-1/A-2/A-3 + central-inbox notify_only 透传（agent-way 1.5.9 批 / central-inbox 0.2.7 批）。
- 语义合并与去重对照结论并入本文档，随 RULES 引用（R006 ⑧ 落链：矩阵 JSON 已收录）。
