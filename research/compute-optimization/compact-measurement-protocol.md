# /compact 实测协议 · DSH 存量大会话压缩量化验证

> 维护：数据调查员 9828aa93 · 2026-08-17
> 关联：bus-queue-solutions-2026W34.md（待查证清单 ①：compaction-basic 触发阈值与压缩后 token 降幅）
> 用途：CLD-017 试点——5 个存量大会话（de7b29de / fa1f9150 / aa528267 / b241741f / 3b5efeef）执行 /compact 前的量化基线，先测后压
> 协作：协调者 fa1f9150 安排维护窗口（5 会话分批，避免同时压缩影响协作）

---

## 一、目标

1. 实测 compaction-basic 的**触发阈值**（多少 token/条目触发自动压缩；/compact 手动触发是否有门槛）。
2. 量化单会话压缩后的**上下文体积 / 条目数 / inputTokens 降幅**（目标：90%+，验证 P0-① 预期）。
3. 量化 tool-result-pruner 的**裁剪量**（thresholdChars=8192 / head=4096 / tail=1024 实际拦截了多少工具结果）。
4. 压缩后**回复质量抽查**（关键事实/决策/未完成任务是否保留，摘要漂移程度）。
5. 记录压缩耗时与副作用（inbox 排队、协作中断时长），回填查证清单①。

## 二、前置条件

- 维护窗口：5 会话分批，每批 1-2 个，批间间隔 ≥15 分钟（观察排队/协作影响）。
- 备份：压缩前对目标会话 session.jsonl.zstd 做快照副本（cp 到 research/compact-snapshots/<session>/）。
- 工具面就绪：确认该会话 preset 已含 compaction 组（liangshen/librarian/waimai-ops）；standard 预设会话若无法挂载，先在测试会话验证 /compact 命令可用性。
- 停止该会话的实时任务（外卖监控/客服回复等高并发会话错开）。

## 三、采集指标

### 3.1 压缩前基线（对 5 会话逐一采集）

| 指标 | 来源 | 说明 |
|---|---|---|
| 上下文条目数 | session.jsonl.zstd 行数（zstd -dc \| wc -l） | 含 reasoning/tool/assistant 等全部条目 |
| 各类型条目数 | 按 json .type 分类统计 | reasoning-chunks / tool-call-chunks / assistant / tool / user / agent/inbox 等 |
| 上下文体积 | 解压后字节数 + zstd 压缩体积 | 与基线 239MB 总量对比 |
| 最近 N 轮 inputTokens | 会话日志 assistant 消息的 usage 字段（若有）；或 api 台账 | 取最近 3 次调用均值 |
| cache_read / cache_write 占比 | usage 字段 | 验证 P0-④ 缓存杠杆基线 |
| 最近一次调用耗时 / 排队深度 | agent-bus.json（该会话 queued 数）+ 调用日志 | 关联处理慢 → 排队 |
| 当前 preset / compaction 组状态 | session 首行 agentPreset + agent.cordis.yml | 确认 standard vs liangshen |

### 3.2 触发阈值探测（在测试会话或首个试点会话）

1. 先读 compaction-basic 包内默认配置（node_modules 或插件目录，找 tokenMeter 阈值常量；找不到则标「待查证」）。
2. 手工触发 /compact：记录触发前后 token 计数值（若插件暴露 meter 读数则直接读）。
3. 若可配置：用较小阈值试跑一次，确认自动触发路径存在（不长期启用，仅验证）。
4. 【2026-08-18 补充，官方阈值已实测=0.8×contextWindow≈800k token】另验「新预设继承」路径：测试预设里配 thresholdRatio=0.3（或 retainTokens 直配）挂到测试会话，确认自动触发在该水位生效且摘要/保留语义正确——这是第三方 auto-compact 不装后的主选路径。

### 3.3 压缩执行（每会话）

| 步骤 | 动作 | 记录 |
|---|---|---|
| 1 | 快照备份 | 备份路径 + sha256 |
| 2 | 记录压缩前基线（§3.1） | 指标表 |
| 3 | 触发 /compact | 命令/入口 + 起始时间 |
| 4 | 等待压缩完成 | 耗时 |
| 5 | 记录压缩后快照 | 条目数/体积/token |
| 6 | 后续 3 次真实调用 | usage（inputTokens/outputTokens/cache_read/write） |
| 7 | 质量抽查（见 §3.4） | 抽查表 |

### 3.4 质量抽查（压缩摘要保真）

抽查 5 项，每项给 通过/部分/不通过：
1. 会话目标/当前任务是否保留（读摘要 vs 压缩前最后 user 消息）。
2. 关键决策与约束（如「不动 shipped 预设」类约束）是否在摘要中。
3. 未完成任务清单是否完整。
4. 关键数字/路径（如 239MB、session id、文件路径）是否有误。
5. 摘要后首次回复是否表现出「记忆断层」（问压缩前的事实，看是否答得出）。

## 四、数据记录模板（每会话一张）

| 字段 | 值 |
|---|---|
| 会话 id | |
| preset | |
| 压缩前 条目数/体积 | |
| 压缩前 inputTokens（近 3 次均值） | |
| 触发方式（手动 /compact / 自动） | |
| 触发阈值读数 | |
| 压缩耗时 | |
| 压缩后 条目数/体积 | |
| 压缩后 inputTokens（后 3 次均值） | |
| 降幅 %（条目/体积/token） | |
| tool-pruner 拦截条数/字符 | |
| cache_read 占比（前 vs 后） | |
| 质量抽查 5 项 | |
| 副作用（排队/中断） | |
| 备注 | |

## 五、输出与回填

1. 汇总表写入 research/compute-optimization/compact-measurement-results-<date>.md。
2. 回填 bus-queue-solutions-2026W34.md 待查证清单 ①（触发阈值）与 P0-① 预期（90%+ 降幅）实测值。
3. 向协调者回报：5 会话分档结果 + 窗口时长建议 + 是否启用 dsh-auto-compact（256K 自动阈值）的评估输入。

## 六、风险与回滚

- 压缩不可逆：**快照先行**；质量抽查不通过时用快照恢复（zstd 原样放回 sessions 目录）。
- 压缩期间协作中断：批间隔 ≥15 分钟；实时任务会话（fa1f9150/aa528267）放最后一批或用户低峰时段。
- 触发阈值未知时勿盲压：先在 3b5efeef（3.1MB/10701 条）试点，验证路径后再动 21.1MB 的 de7b29de。
- 不动 shipped standard 预设：仅用会话级 /compact + 新预设继承（CLD-017 约束）。

---
*实测协议 v0.1 · 数据调查员 · 2026-08-17*
