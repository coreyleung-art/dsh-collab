# queue 管理工具族 · 完整设计文档

> 版本：v1.18.0（queue-drain）/ v1.17.0（queue-condense）/ v0.8.0 内嵌（queue_watch）
> 更新：2026-08-30 · 作者：星桥（总线协调者）
> 关联纪律：R012（CHECKS 七要素）、R019（概念精确性）、CCEP 永续通讯协议
> 设计红线（用户）：**疏通交通不能把过往车辆扫进垃圾堆** —— 抽走必须防丢会话和任务

---

## 1. 背景与问题

### 1.1 现象

分布式多智能体系统通过 `agent-bus.json`（`~/.dsh/agent-bus.json`）交换跨会话消息。随着设备互通（mac-mini 中枢 / i9 / MBP）与角色增多，出现**消息风暴**：

| 指标 | 实测值（2026-08-30） |
|------|----------------------|
| 线程总数 | 858 |
| queued（待投递） | 284 |
| delivered（已送达） | 22,009 |
| 堆积比例 | 33.3% |
| TOP 发送方 | 单会话 215 条 |

### 1.2 危害

- **token 放大**：每条 queued 消息唤醒目标会话 → 逐条处理放大 3-5 倍上下文消耗
- **堆积失真**：超过 50 条 queued 即触发门禁误判（新消息被 deny）
- **噪音污染**：通知类消息与待执行任务混在队列，目标会话被无关唤醒

### 1.3 目标

1. **检测**：5 分钟巡检队列健康，三态判断（绿/黄/红）
2. **浓缩**：只读理解堆积内容，不删除任何消息（保守）
3. **疏通**：抽走纯通知缓解堆积，**待执行任务完整保留**（用户红线）

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      agent-bus.json                         │
│  threads[]: id / createdAt / messages[]                     │
│  messages[]: id / thread / from / to / text / time /        │
│              status(queued|delivered|archived) / kind       │
│  + locks / lightLog / dedup / profiles / restartPlan        │
└──────────────┬──────────────────────────┬───────────────────┘
               │ 读                        │ 读+写（仅 drain）
┌──────────────▼──────────┐   ┌────────────▼──────────────────┐
│   queue_watch (检测)     │   │   queue-drain (疏通)           │
│   blackboard-mcp v0.8.0 │   │   rust-tools v1.18.0           │
│   SSE 模式 spawn 线程    │   │   --scan / --drain / --summary │
│   每 300s 扫队列         │   │   任务保护 + 归档式抽走          │
└──────────────┬──────────┘   └────────────┬──────────────────┘
               │ 🔴 自动触发                 │ 备份
┌──────────────▼──────────┐   ┌────────────▼──────────────────┐
│   queue-condense (浓缩)  │   │   ~/.dsh/queue-drain-backups/ │
│   rust-tools v1.17.0    │   │   agent-bus-<ts>.json          │
│   只读：去重→bge-m3 聚类  │   │   （双保险，可恢复）             │
│   →qwen 归纳→写黑板      │   └───────────────────────────────┘
└─────────────────────────┘
```

### 2.1 三件套职责划分

| 工具 | 职责 | 写操作 | 数据安全 |
|------|------|--------|----------|
| queue_watch | 巡检检测 + 三态判断 | 只写状态黑板 `data/ops/queue-monitor/current` | 不触碰 agent-bus |
| queue-condense | 语义浓缩理解 | **零写**（只读，产出写黑板） | 最保守 |
| queue-drain | 抽走疏通 | 改 status（queued→archived） | 任务保护 + 备份双保险 |

### 2.2 数据流

```
agent-bus.json ──scan──▶ queue_watch ──judge──▶ 绿/黄/红
                                                  │ red
                          ┌───────────────────────┤
                          ▼                       ▼
                  queue_monitor 查询      queue-condense（自动）
                  （MCP 工具）                 │
                          │                    ▼
                          │              写黑板 data/ops/queue-condense/condense-<ts>
                          │                    │ 通知目标会话（浓缩后不再逐条唤醒）
                          ▼                    ▼
                  人工/定时触发 queue-drain ──▶ 通知类 queued → archived
                                              待执行任务 → 保留 queued
```

---

## 3. queue_watch（检测）设计

**位置**：`rust-blackboard-mcp/src/main.rs`（SSE 模式启动时 spawn）+ `src/feature.rs`

### 3.1 巡检逻辑

```
loop {
    sleep(300s)
    (q, prev) = scan_queue_state()          // 统计 agent-bus queued 数
    (state, msg) = judge_queue(q, prev)     // 三态判断
    prev = q
    bb_put_plain("data/ops/queue-monitor/current", {ts, queued, state, msg})
    if state == "red" && now - last_condense > 600s:
        tool_queue_condense()               // 🔴 自动浓缩（10 分钟节流）
        last_condense = now
}
```

### 3.2 三态判断器（judge_queue）

| 状态 | 条件 | 含义 |
|------|------|------|
| 🔴 red | q > 200 或 (q > 50 且增长 > 1.5x) | 堆积风暴，自动浓缩 |
| 🟡 yellow | q > 50 或 (q > 20 且增长 > 1.3x) | 队列预警 |
| 🟢 green | 其他 | 队列正常 |

### 3.3 token 节约评估（司库 verdict）

| 维度 | 实测值 |
|------|--------|
| 节约幅度 | 60-80%（浓缩 284→5 簇一次处理 vs 逐条唤醒放大 3-5x） |
| 巡检成本 | 零 LLM（纯计数），<¥5/月 |
| 节省 | ¥15-40/事件 |
| 结论 | 采纳推广，纳入 R006 基础设施 |

---

## 4. queue-condense（浓缩）设计

**位置**：`rust-tools/src/queue_condense.rs` + `rust-blackboard-mcp/src/feature.rs::tool_queue_condense`

### 4.1 处理管线（只读）

```
agent-bus queued 消息
   │ ① 去重（同 text 合并）
   ▼
   │ ② bge-m3 向量化 + 聚类（阈值 0.55）
   ▼
   │ ③ qwen2.5:3b 归纳 top5 大簇
   ▼
   │ ④ 写黑板 data/ops/queue-condense/condense-<ts>
   ▼
   │ ⑤ 通知目标会话（浓缩摘要，替代逐条唤醒）
```

### 4.2 关键设计点

- **只读不删**：绝不修改 agent-bus.json，仅产出理解结果到黑板
- **字节级 chunked 解析**：Ollama 响应 `3249\r\n{json}...0\r\n\r\n` 需按 size 精确切块（parse_http_body）
- **纯数字 body 防误判**：count 返回 `1971` 全 hex 数字，需加强判断（size>0 且 rest_after>=size）
- **MCP 超时**：282 条需 embed 272 次 + 归纳，SSE 客户端等待会超时 → 后台跑可完成（284→274→5 簇）

---

## 5. queue-drain（疏通）设计 —— v1.18.0 任务保护

**位置**：`rust-tools/src/queue_drain.rs`

### 5.1 命令接口

```
dsh-tools queue-drain --scan              # 扫描统计（不清理）
dsh-tools queue-drain --drain             # 抽走：通知类 queued → archived
dsh-tools queue-drain --drain --keep 7d   # 保留近 7 天，抽走更旧的
dsh-tools queue-drain --summary           # 汇总报告
```

### 5.2 任务语义识别（is_task_message）

三层判断，方向保守（拿不准 → 保留）：

| 层级 | 规则 | 示例 |
|------|------|------|
| 强信号 | 请 / 回报 / 执行 / 派发 / 指令 / 批准 / 审核 / 验收 / 待办 / 确认后 / 步骤 / 方案 | 「请检查 G5 staging」→ 任务 |
| 弱信号 | 祈使前缀（请/需/要/待）+ 动词（检查/核对/验证/更新/处理/回复/完成/确认）组合 | 「请核对清单」→ 任务；「巡检完成」→ 通知 |
| 否定排除 | 无需 / 不用 / 不必 / 已完成 / 已确认 / 已处理 / 已回复 / 已生成 / 已送达 / 已归档 | 「心跳正常，无需处理」→ 通知 |

### 5.3 归档式抽走（用户红线落地）

```
抽走 = 状态 queued → archived（保留在原线程，永不删除）
  m["status"] = "archived"
  m["archived_ts"] = now
  m["archived_by"] = "queue-drain"
```

**双保险**：
1. 抽走前全量备份 `~/.dsh/queue-drain-backups/agent-bus-<ts>.json`
2. 消息保留在原线程（archived 状态），可随时恢复

### 5.4 返回结构

```json
{
  "drained": 3,
  "protected_tasks": 2,
  "note_protected": "待执行任务已保护（保留在队列不抽走，防任务丢失——用户红线）",
  "backup": "~/.dsh/queue-drain-backups/agent-bus-<ts>.json",
  "archived_samples": ["日报已生成，可查看", "..."]
}
```

### 5.5 冒烟验证（2026-08-30 实测全过）

| 测试消息 | 预期 | 结果 |
|----------|------|------|
| 请检查 G5 staging 部署状态并回报 | 保留（任务） | ✅ queued |
| 请核对 queue 堆积清单 | 保留（祈使+动词） | ✅ queued |
| 日报已生成，可查看 | 疏通（通知） | ✅ archived |
| 心跳正常，无需处理 | 疏通（否定排除） | ✅ archived |
| 巡检完成，一切正常 | 疏通（无祈使前缀） | ✅ archived |

真实 agent-bus.json 备份后测试，已恢复一致（15,125,884 bytes）。

---

## 6. 数据安全保证（对照用户红线）

| 红线 | 实现 |
|------|------|
| 不能丢会话 | 消息永不删除，archived 保留原线程 |
| 不能丢任务 | 任务语义识别，待执行任务保留 queued |
| 可恢复 | 抽走前全量备份 + archived 状态双保险 |
| 保守原则 | 拿不准 → 保留（is_task 默认 true 方向） |

---

## 7. 版本历史

| 版本 | 工具 | 变更 |
|------|------|------|
| v1.15.0 | load-gate | 资源总控门 |
| v1.16.0 | queue-drain | 初版：扫描/抽走/备份（从 threads 移除） |
| v1.17.0 | queue-condense | Rust 版浓缩（字节级 chunked 解析） |
| v1.18.0 | queue-drain | **任务保护 + 归档式抽走**（消息不删除） |
| v0.8.0 | blackboard-mcp | queue_watch 内嵌（300s 巡检 + 🔴 自动浓缩） |

---

## 8. 演进路线

- [x] 检测：queue_watch 5min 巡检 + 三态判断
- [x] 浓缩：queue-condense 只读语义理解
- [x] 疏通：queue-drain 任务保护 + 归档式
- [ ] queue_watch 接入 protected_tasks 统计（风暴时先浓缩再 selective drain）
- [ ] 浓缩簇 → R018 噪声反馈链
- [ ] 浓缩簇 → 概念字典高频词候选（R019 语义层增强）
- [ ] i9 / MBP 端侧升级 v1.18.0 / v0.8.0

---

## 9. 蓝图适配（R020 闭环 · 明鉴分析 2026-08-31）

> R020 新工具蓝图适配闭环首个案例——明鉴（蓝图主编 v2）适配分析：**适用**

| 蓝图落点 | 适配度 | 说明 |
|----------|--------|------|
| d3 分布式网络底座 | 强 | queue_watch 巡检+三态判断 = 积压告警→自动浓缩/抽走，防消息风暴 |
| d3-2 感知闭环（告警降噪） | 强 | queue-condense 去重→聚类→归纳 = 同型消息 ×N 合并，提升感知质量 |
| d4-1 数据聚合 | 中（借鉴） | queue-drain 判死信/隔离思路 → 事件管道去重；condense 作聚合前信号预处理 |
| d3-3 决策-执行闭环 | 中 | 积压三态 = 执行队列健康度监控维度 |

**建议（明鉴）**：works v8 d3 分布式底座补子工作「队列治理」；概念字典登记「消息风暴/积压三态」。
**落点**：flowernet v2.2 数字化主线（d3 端侧自动化运维底座）。
分析原文：黑板 data/blueprint/tool-adapt-queue-family
