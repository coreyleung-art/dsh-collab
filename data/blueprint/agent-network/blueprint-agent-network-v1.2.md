# blueprint:agent-network · 多智能体协作底座（FNP 语义 + Agent Bus 消息 + 内存治理双层 + 监控安全） · v1.2

> 生成：明鉴 v2 · 2026-09-02 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① P0 通信契约冻结（envelope v1.0）才进 P1 ② P2 状态契约（重启对齐+幂等）才进 P3 ③ 每阶段 Rust 化达标（dsh-tools 子命令）
> 依据：research/agent-network-blueprint-candidate.md（4787d717 R025 调研） + bus-queue-solutions-2026W34 + compaction-official-vs-auto-compact + i9 memory-archeology + 用户分层洞察（memory-two-layer-design / memory-L2-systemic-design）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | agent-network |
| name | 多智能体协作底座（FNP 语义 + Agent Bus 消息 + 内存治理双层 + 监控安全） |
| version | v1.2 |
| mainlines | bus / fnp / mem-l1（工具链·现时）/ mem-l2（体系化持久化·未来）/ security |
| stages | P0-P5 + mg1-mg3（L1）+ mg4-mg7（L2） |
| works | an0-1…mg7-2（mg1-1/mg2-1 done） |
| gate | ① P0 通信契约冻结才进 P1 ② P2 状态契约才进 P3 ③ 每阶段 Rust 化达标 |
| status | active |
| ts | 2026-09-02 |

## 一、主线

- **bus**：Agent Bus 消息层 — 线程/红绿灯/inbox 背压/消息路由（演进保留）
- **fnp**：FNP 语义层 — 自有协议防逆向：黑板 KV/事件桥 SSE/FNP 信封/HLC 时间轴
- **mem-l1**：内存治理 L1 · 工具链（现时·效率） — 现有智能体工具链内存延伸问题：compaction/pruner/批处理+缓存
- **mem-l2**：内存治理 L2 · 体系化持久化（未来·知识） — 体系化内存持久化治理：写入通道收敛/体系检索/生命周期遗忘/记忆复利（用户分层洞察第二段）
- **security**：监控安全层 — 落链/值班/授权/积压告警/上下文监控

## 二、阶段与子阶段

### P0 基础通信 [active] …（同 v1.1）
### P1 编排 / P2 状态 / P3 监控 / P4 扩展 / P5 优化 …（同 v1.1）

---

## 内存治理 · 两层架构（用户 2026-09-02 分层洞察）

> **层1 = 现有智能体工具链带出的内存延伸问题（治标·现时效率）**
> **层2 = 日后整个体系化的内存持久化治理（治本·未来知识复利）**
> 衔接：层1 压缩摘要中符合 promote 判定 → 固化到层2 长期记忆

### M1-L1 上下文压缩（compaction） [active]
- mg1-1 compaction 挂载 [done] — 4 预设全挂（liangshen/librarian/resource-manager/waimai-ops）——实证 ~/.dsh/.agent-presets/*/agent.cordis.yml
- mg1-2 /compact 手动入口 [active] — CLD-017 试点进行中（4787d717，评估 thresholdRatio）
- mg1-3 摘要保留策略 [todo] — 压缩保留：目标/约束/决策/未完成/关键数字；丢弃：过程推理链

### M2-L1 工具结果裁剪 [active]
- mg2-1 pruner 启用 [done] — 全预设启用（threshold 8192/头 4096/尾 1024）——4 预设 agent.cordis.yml 实证
- mg2-2 大输出落盘 [todo] — 工具大输出落盘+行号引用，只回摘要/diff

### M3-L1 消息批处理+优先级 [todo]
- mg3-1 inbox 批量合并 [todo] — 重启唤醒类聚合为单条广播（69→<10）
- mg3-2 缓存前缀稳定 [todo] — DeepSeek 缓存命中价差 30 倍——前缀稳定降本

### MG4-L2 记忆写入治理 [todo]
- mg4-1 写入通道收敛 [todo] — 3 通道：迭代报告→黑板+KB 双写 / 决策教训→L2 断言库 / 感知→OpenChronicle
- mg4-2 固化 promote 规则 [todo] — compaction 摘要符合 promote 判定 → 固化长期记忆（对齐 rule-judge L2 断言模式）
- mg4-3 记忆库衔接 [todo] — 衔接 OpenChronicle/黑板 changelog/DSH KB（8 库 547 文档）/Obsidian wiki

### MG5-L2 体系检索 [todo]
- mg5-1 记忆索引目录 [todo] — 4 资产统一 memory-registry（对齐 message-registry 模式）
- mg5-2 跨库检索面 [todo] — knowledge_search+oc_search+黑板 grep 聚合 CLI

### MG6-L2 生命周期与遗忘 [todo]
- mg6-1 记忆分级 TTL [todo] — 常量(规则/授权,永久)/长时(定案/教训,年)/短时(过程,季度)/瞬态(队列,周)——授权档案不可被压缩遗忘
- mg6-2 归档与遗忘审计 [todo] — 冷存储+归档清单+定期遗忘审查

### MG7-L2 记忆复利（北极星） [todo]
- mg7-1 决策-教训闭环 [todo] — 失败/教训 → L2 断言库 → 后续自动拦截（对齐教师节 5 教训入 rule-judge）
- mg7-2 记忆体检 [todo] — 固化率/检索命中/过期清理周期报告

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| active | FNP 信封 v1.0 冻结（envelope 格式/版本协商） | 星桥/明鉴 | an0-1 |
| todo | inbox 背压/优先级设计（Actor 邮箱） | 星桥 | an0-2 |
| todo | bb-write Rust 化补位（dsh-tools） | 4787d717 | an0-3 |
| active | 任务卡生命周期规范化（taskboard v2） | 明鉴 | an1-1 |
| todo | per-namespace 授权 v0.7 落地 | 星桥 | an3-1 |
| todo | 三工程债监控仪表（膨胀/inbox 串行/唤醒风暴） | 4787d717 | an3-2 |
| done | compaction 存量会话挂载（4 预设全挂） | 守灯塔 | mg1-1 |
| active | 上下文膨胀治理试点（CLD-017） | 4787d717 | mg1-2 |
| done | 工具结果裁剪启用（pruner 全预设） | 守灯塔 | mg2-1 |
| todo | 记忆写入 3 通道收敛规范 | 明鉴 | mg4-1 |
| todo | memory-registry v1（4 资产统一目录） | 明鉴 | mg5-1 |
| todo | 首次遗忘审计（分级 TTL 试点） | 明鉴 | mg6-2 |
| todo | 记忆体检首份报告（固化率/检索命中/清理量） | 明鉴 | mg7-2 |

## 四、依赖关系（relations）

- **depends_on**：mem-l2 依赖 mem-l1（层1 压缩摘要是 L2 promote 输入）
- **references**：blueprint-platform · memory-two-layer-design · memory-L2-systemic-design
- **requires**：flowernet-platform#P1

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）…（同 v1.1，an1-2/an3-2）

## 五、门禁链

① P0 通信契约冻结才进 P1 ② P2 状态契约才进 P3 ③ 每阶段 Rust 化达标 ④ mem-l2 MG4 写入治理落地才进 MG5 检索（先收敛后检索）

---
*blueprint:agent-network · v1.2 · 内存治理双层拆分（用户分层洞察）*
