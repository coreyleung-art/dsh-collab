# blueprint:memory-governance · 内存治理（L1 工具链 + L2 体系化持久化 + risk 推进风险预判） · v1.0

> 生成：明鉴 v2（blueprint-create）· 2026-09-02 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① 每突进纳入生产：评估报告→人类确认（R027 L3）→才实施 ② 改 CLD 宿主配置先隔离验证+备份+dump-config 零报错 ③ 内存压力>85%/swap>90% 禁重操作 ④ mg1-2 CLD-017 试点完成才批量扩 thresholdRatio ⑤ L2 MG4 写入治理落地才进 MG5（先收敛后检索）
> 依据：memory-two-layer-design.md（分层总纲）· memory-L2-systemic-design.md（L2 深化）· memory-governance-risk-study.md（风险预判研究）· cld-health-baseline §3/§9 · crash-fix-20260818 · 用户分层洞察 2026-09-02

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | memory-governance |
| name | 内存治理（L1 工具链 + L2 体系化持久化 + risk 推进风险预判） |
| version | v1.0 |
| dimension | 子蓝图（child_of agent-network） |
| mainlines | mem-l1（工具链·现时）/ mem-l2（体系化·未来）/ risk（风险预判·横切） |
| gate | 见门禁链 §五 |
| status | active |
| ts | 2026-09-02 |

## 一、主线

- **mem-l1**：工具链内存治理（现时·效率） — 现有智能体工具链带出的内存延伸问题：compaction/pruner/批处理+缓存——239MB/71.8% 推理碎片膨胀治理
- **mem-l2**：体系化持久化治理（未来·知识） — 整个体系的长期记忆架构：写入通道收敛/体系检索/生命周期遗忘/记忆复利——知识复利（越用越聪明）
- **risk**：推进风险预判与变更管理（横切） — 推进动作本身的高风险预判识别：理论先行/最小化模型/每突进评估报告+人类确认——避免拉崩 CLD

## 二、阶段与子阶段

### M1-L1 上下文压缩（compaction） [active]
- mg1-1 compaction 挂载 [done] — 4 预设全挂（liangshen/librarian/resource-manager/waimai-ops）——实证 ~/.dsh/.agent-presets/*/agent.cordis.yml
- mg1-2 /compact 手动入口+水位试点 [active] — CLD-017 试点进行中（4787d717，thresholdRatio 0.8→实际水位）——门禁④
- mg1-3 摘要保留策略 [todo] — 压缩保留：目标/约束/决策/未完成/关键数字；丢弃：过程推理链/已消费工具结果

### M2-L1 工具结果裁剪 [active]
- mg2-1 pruner 启用 [done] — 全预设启用（threshold 8192/头 4096/尾 1024）——4 预设 agent.cordis.yml 实证
- mg2-2 大输出落盘 [todo] — 工具大输出落盘+行号引用，只回摘要/diff

### M3-L1 消息批处理+优先级 [todo]
- mg3-1 inbox 批量合并 [todo] — 重启唤醒类聚合为单条广播（69→<10）
- mg3-2 缓存前缀稳定 [todo] — DeepSeek 缓存命中价差 30 倍——前缀稳定降本

### MG4-L2 记忆写入治理 [todo]
- mg4-1 写入通道收敛 [todo] — 3 通道：迭代报告→黑板+KB 双写 / 决策教训→L2 断言库 / 感知→OpenChronicle
- mg4-2 固化 promote 规则 [todo] — compaction 摘要符合 promote 判定→固化长期记忆（对齐 rule-judge L2 断言模式）
- mg4-3 记忆库衔接 [todo] — 衔接 OpenChronicle/黑板 changelog/DSH KB（8 库 547 文档）/Obsidian wiki

### MG5-L2 体系检索 [todo]
- mg5-1 记忆索引目录 [todo] — 4 资产统一 memory-registry（对齐 message-registry）
- mg5-2 跨库检索面 [todo] — knowledge_search+oc_search+黑板 grep 聚合 CLI

### MG6-L2 生命周期与遗忘 [todo]
- mg6-1 记忆分级 TTL [todo] — 常量(规则/授权,永久)/长时(定案/教训,年)/短时(过程,季度)/瞬态(队列,周)
- mg6-2 归档与遗忘审计 [todo] — 冷存储+归档清单+定期遗忘审查

### MG7-L2 记忆复利（北极星） [todo]
- mg7-1 决策-教训闭环 [todo] — 失败/教训→L2 断言库→后续自动拦截（对齐教师节 5 教训入 rule-judge）
- mg7-2 记忆体检 [todo] — 固化率/检索命中/过期清理周期报告

### R0-risk 风险实证库（理论先行） [active]
- rg0-1 CLD 崩溃面盘点 [done] — 5 类事故实证：C1/C2 V8 OOM（09-01/09-02，swap 92%）· C3 SIGKILL 强杀（08-16）· C4 批量插件连环（08-18）· C5 签名不稳
- rg0-2 推进动作×风险矩阵 [done] — R1 preset 改动(高)/R2 thresholdRatio(高)/R3 重启(高)/R4 落盘脚本(中)/R5 记忆固化(低)/R6 并发 compaction(高)——含最小化模型
- rg0-3 预判信号清单 [done] — 6 信号：内存压力>85%/swap>90%/Worker 数/dump-config 报错/备份在位/看门狗留痕

### R1-risk 变更门控流程 [todo]
- rg1-1 评估报告模板 [todo] — 变更说明/风险分析/隔离验证/最小试点/影响收益/回滚预案——每次突进一份
- rg1-2 审批门接入 [todo] — GUI 审批流→R027 授权案例登记（每突进人类 ON）

### R2-risk 监控与并发限制 [todo]
- rg2-1 内存/swap 实时监控 [todo] — health-check.sh 接入推进期监控（CLD-011 已有判红）
- rg2-2 Worker 并发限制 [todo] — C1 崩溃帧=WorkerThread 并发→限制同时 compaction 的会话数

### R3-risk 最小化模型验证 [todo]
- rg3-1 隔离验证规程 [todo] — /tmp/dsh-test-home 或单 preset 副本验证可加载（C4 用户定论）
- rg3-2 单预设试点流程 [todo] — 单会话小步实施→观察内存曲线→扩大（禁一次改多预设）

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| done | CLD 崩溃面实证盘点（5 类 C1-C5） | 明鉴 | rg0-1 |
| done | 推进动作×风险矩阵 R1-R6 + 最小化模型 | 明鉴 | rg0-2 |
| done | 预判信号清单 6 条 | 明鉴 | rg0-3 |
| todo | 突进评估报告模板（变更/风险/隔离/试点/回滚） | 明鉴 | rg1-1 |
| todo | GUI 审批门接入（每突进 R027 授权 ON） | 明鉴 | rg1-2 |
| done | compaction 存量会话挂载（4 预设全挂） | 守灯塔 | mg1-1 |
| active | 上下文膨胀治理试点（CLD-017，thresholdRatio 评估） | 4787d717 | mg1-2 |
| done | 工具结果裁剪启用（pruner 全预设） | 守灯塔 | mg2-1 |
| todo | 记忆写入 3 通道收敛规范 | 明鉴 | mg4-1 |
| todo | memory-registry v1（4 资产统一目录） | 明鉴 | mg5-1 |
| todo | 首次遗忘审计（分级 TTL 试点） | 明鉴 | mg6-2 |
| todo | 记忆体检首份报告（固化率/检索命中/清理量） | 明鉴 | mg7-2 |

## 四、依赖关系（relations）

- **child_of**：agent-network（底座 memory 主线独立成册）
- **depends_on**：agent-network（compaction/pruner/批处理在底座预设面实施）
- **references**：rule-judge（promote 判定/L2 断言模式复用）
- **manages**：blueprint-platform（元层）

## 四b、自动化开关锁（R027 + 人类确认门）

**本蓝图核心：每个纳入生产的突进 = R027 授权案例，人类 GUI 审批 ON 才实施。**

- **任意突进（rg1-2 落地后）**：`automation-switch on --bp memory-governance --stage <stage> --by <人类> --level L3`
  - 前置：rg1-1 评估报告（变更说明/风险分析/隔离验证/最小试点/影响收益/回滚预案）经用户审阅
  - 默认态：OFF（未审批一律不实施）
  - 熔断：`automation-switch off --bp memory-governance --stage <stage> --by <人类> --reason <原因>`
  - 授权：HumanApproval(L3)——Lean4 类型保证：无 Authorization 无法构造 Unlocked

## 五、门禁链

① 每突进纳入生产：评估报告→人类确认（R027 L3）→才实施
② 改 CLD 宿主配置（preset/.cordis.yml/重启）：先隔离验证+备份+dump-config 零报错
③ 内存压力>85%/swap>90%：禁任何重操作（OOM 面 C1/C2）
④ mg1-2 CLD-017 试点完成才批量扩 thresholdRatio（先小步 0.8→0.75→0.7）
⑤ L2 MG4 写入治理落地才进 MG5（先收敛后检索，防垃圾进库）
⑥ 里程碑验收（M1-M4，见 memory-L2-systemic-design）：L2 两周新决策 80% 可溯源 / 检索 3 秒出结果 / 记忆增速受控 / 教训拦截命中≥1 次月

---
*blueprint:memory-governance · v1.0 · 理论先行 + 最小化模型 + 每突进人类确认（用户定论）*
