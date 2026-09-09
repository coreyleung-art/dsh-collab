# blueprint:agent-network · 多智能体协作底座（FNP 语义 + Agent Bus 消息 + 监控安全） · v1.1

> 生成：bb-blueprint-create.py · 2026-09-02T13:15:15 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① P0 通信契约冻结（envelope v1.0）才进 P1 ② P2 状态契约（重启对齐+幂等）才进 P3 ③ 每阶段 Rust 化达标（dsh-tools 子命令）
> 依据：research/agent-network-blueprint-candidate.md（4787d717 R025 调研，22 篇论文） + bus-queue-solutions-2026W34 + compaction-official-vs-auto-compact + i9 memory-archeology

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | agent-network |
| name | 多智能体协作底座（FNP 语义 + Agent Bus 消息 + 监控安全） |
| version | v1.1 |
| mainlines | {"bus": {"desc": "线程/红绿灯/inbox 背压/消息路由（演进保留）", "name": "Agent Bus 消息层"}, "fnp": ... |
| stages | [{"id": "an0", "mainline": "fnp", "name": "基础通信", "stage": "P0", "status": "acti... |
| works | [{"owner": "星桥/明鉴", "stage": "an0-1", "status": "active", "work": "FNP 信封 v1.0 冻... |
| gate | ① P0 通信契约冻结（envelope v1.0）才进 P1 ② P2 状态契约（重启对齐+幂等）才进 P3 ③ 每阶段 Rust 化达标（dsh-tools 子命令） |
| status | active |
| ts | 2026-09-02T13:15:15 |

## 一、主线

- **bus**：Agent Bus 消息层 — 线程/红绿灯/inbox 背压/消息路由（演进保留）
- **fnp**：FNP 语义层 — 自有协议防逆向：黑板 KV/事件桥 SSE/FNP 信封/HLC 时间轴
- **memory**：内存治理（上下文管理） — 会话上下文只增不减治理：压缩/摘要/裁剪/记忆分层——实测 239MB/71.8% 推理碎片
- **security**：监控安全层 — 落链/值班/授权/积压告警/上下文监控

## 二、阶段与子阶段

### P0 基础通信 [active]
- an0-1 FNP 信封标准化 [active] — envelope v1.0 冻结：格式/版本协商；黑板 KV+事件桥 SSE 已有 90%
- an0-2 inbox 背压设计 [todo] — Actor 邮箱模式：背压/优先级（bus-queue 分析点名缺口）
- an0-3 bb-write Rust 化补位 [todo] — dsh-tools 缺 bb-write → 补（P0 优先）

### P1 编排 [active]
- an1-1 任务卡生命周期规范化 [active] — CREATED→执行→回报→清卡；已有 80%（taskboard）
- an1-2 派发/展开/校验/回流 Rust 化 [todo] — bb-dispatch/event-bus 等 Python→Rust
- an1-3 知识源触发声明 [todo] — 黑板架构：显式触发条件（现靠值班轮询）

### P2 状态管理 [active]
- an2-1 HLC 时间轴+增量恢复 [active] — since_seq 已有 85%（timeline v0.3）
- an2-2 会话恢复契约 [todo] — checkpoint 语义：重启对齐基线+Exactly-Once 幂等
- an2-3 上下文压缩边界 [todo] — 压缩策略（衔接上下文膨胀债）

### P3 监控安全 [partial]
- an3-1 per-namespace 授权 v0.7 [todo] — X-Writer 校验完善（已有 60%）
- an3-2 积压/膨胀/唤醒风暴监控 [todo] — 三工程债仪表：上下文膨胀/inbox 串行/唤醒风暴
- an3-3 落链+值班闭环 [active] — 落链 5 步+值班消费（已有）

### P4 扩展 [todo]
- an4-1 能力发现 v1.1 [todo] — capabilities 上报（20% 预告）
- an4-2 设备/门店接入标准化 [todo] — 新 agent/设备/工具即插即用
- an4-3 插件化工具注册 R006 [todo] — source-tools 已示范

### P5 优化 [todo]
- an5-1 token 成本仪表 [todo] — 衔接 token-ledger
- an5-2 inbox 优先级+背压 [todo] — Actor 邮箱模式落地
- an5-3 swarm 场景评估 [todo] — 2506.14496 边界：不为 swarm 而 swarm

### M1 上下文压缩（compaction） [todo]
- mg1-1 compaction 挂载 [todo] — 官方 dsh-compaction-basic 存量会话未挂载（preset=standard）；调低 thresholdRatio 0.8→实际水位——调研已定位
- mg1-2 /compact 手动入口 [todo] — dsh-command-compact 已装；大会话手动压缩降 90%+（CLD-017 试点）
- mg1-3 摘要保留策略 [todo] — 压缩保留：目标/约束/决策/未完成/关键数字；丢弃：过程推理链/已消费工具结果

### M2 工具结果裁剪 [todo]
- mg2-1 pruner 启用 [todo] — dsh-compaction-tool-result-pruner（阈值 8192/头 4096/尾 1024）——72% 体积大头
- mg2-2 大输出落盘 [todo] — 工具大输出落盘+行号引用，只回摘要/diff

### M3 消息批处理+优先级 [todo]
- mg3-1 inbox 批量合并 [todo] — 重启唤醒类聚合为单条广播而非逐条排队（69→<10）
- mg3-2 缓存前缀稳定 [todo] — DeepSeek 缓存命中价差 30 倍——保持前缀稳定降本

### M4 记忆分层+外部记忆 [todo]
- mg4-1 分层架构 [todo] — 系统提示常驻前缀+近期原文+更早滚动摘要+跨会话外部记忆
- mg4-2 记忆库衔接 [todo] — 衔接 OpenChronicle/黑板 changelog/knowledge（记忆持久化）

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| active | FNP 信封 v1.0 冻结（envelope 格式/版本协商） | 星桥/明鉴 | an0-1 |
| todo | inbox 背压/优先级设计（Actor 邮箱） | 星桥 | an0-2 |
| todo | bb-write Rust 化补位（dsh-tools） | 4787d717 | an0-3 |
| active | 任务卡生命周期规范化（taskboard v2） | 明鉴 | an1-1 |
| todo | per-namespace 授权 v0.7 落地 | 星桥 | an3-1 |
| todo | 三工程债监控仪表（膨胀/inbox 串行/唤醒风暴） | 4787d717 | an3-2 |
| todo | compaction 存量会话挂载（调低 thresholdRatio） | 守灯塔/运维 | mg1-1 |
| todo | 上下文膨胀治理试点（CLD-017） | 4787d717 | mg1-2 |
| todo | 工具结果裁剪启用（pruner） | 守灯塔/运维 | mg2-1 |

## 四、依赖关系（relations）

- **depends_on**：
- **references**：blueprint-platform
- **requires**：flowernet-platform#P1

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

- **an1-2**：自动派发/编排（Rust 化后的执行自动化）
  - 开关点：`automation-switch on --bp <bp> --stage an1-2 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp <bp> --stage an1-2 --by <人类> --reason <原因>`
  - 授权：HumanApproval(L3) 或 VerifiedGate(L2) —— Lean4 类型保证：无 Authorization 无法构造 Unlocked
- **an3-2**：自动值班/告警动作（监控自动化）
  - 开关点：`automation-switch on --bp <bp> --stage an3-2 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp <bp> --stage an3-2 --by <人类> --reason <原因>`
  - 授权：HumanApproval(L3) 或 VerifiedGate(L2) —— Lean4 类型保证：无 Authorization 无法构造 Unlocked

## 五、门禁链

① P0 通信契约冻结（envelope v1.0）才进 P1 ② P2 状态契约（重启对齐+幂等）才进 P3 ③ 每阶段 Rust 化达标（dsh-tools 子命令）

---
*blueprint:agent-network · v1.1 · 三件套纪律落盘*
