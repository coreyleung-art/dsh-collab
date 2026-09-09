# MBP 协作规则同步文档 · 底层规则 + 资源管理 + 规则门

> 版本：v1.0 → **v2.2.0（2026-08-31 同步规则账本 v2.2.0）** · 产出：HR 司库（资源管理者）
> 账本 v2.2.0 变更：R020 新工具蓝图适配闭环（新工具出现→同步明鉴→蓝图适配分析→纳入交付规则）+ R017-R019 同步修复
> R024（v2.6.0）：子代理新建前评估纪律——新建子代理前必查现有（subagent-govern check-new/audit），同类型可复用则复用不新建；任务完成即归档不做常驻；主角色黑名单灾难防护
> 账本同步：R002 v1.1 collab 广播纪律生效（①全局重要→collab ②定向→notes/<node>/ 或 agent_send ③写前自问所有端都需要吗 ④定向能达不用 collab ⑤collab 留档兜底）
> 用途：MBP（独立 DSH 设备）接入 Agent Bus 协作网络的规则说明——正确参与红绿灯/资源登记/审批/成本门禁
> 配套：resource-registry.md（登记表）· resource-conflict-policy.md（规范集）· agent-bus-permissions.md（权限门控）· approval-config.json（审批配置）· token-cost-management.md（成本策略）

---

## 一、底层规则：Agent Bus 原理与通道纪律

### 1.1 总线原理
- **消息**：agent_send 定向投递（目标会话被唤醒）；agent_broadcast 群发/广播；agent_thread 线程会话
- **线程**：thread id 串联多轮讨论（COLLAB）；消息带 thread 可续聊
- **持久化**：总线状态存 ~/.dsh/agent-bus.json（消息队列/线程/锁/档案）
- **唤醒**：消息走宿主真实收件箱（followup 唤醒），与用户消息同路径；离线目标进待投递队列，上线自动送达
- **去重**：同发件人同线程同内容 10 分钟内自动去重（status: duplicate）
- **8 个全局工具**：agent_peers / agent_send / agent_broadcast / agent_thread / agent_light / agent_lock / agent_unlock / agent_unlock_all

### 1.2 通道分级纪律（cahac-protocol v1.0 + event-cutting-spec v1.0 固化）

| 通道类型 | 语义 | 通道 | 权重 |
|---|---|---|---|
| STATUS | 状态汇报/登记/结果 | **黑板写** | 0.1 |
| ACK | 确认回执（<120字） | **黑板读** | 0.05 |
| TASK | 任务委派/请求执行 | p2p | 1.0 |
| COLLAB | 线程多轮实质讨论（≥200字） | p2p-thread | 0.8 |
| EVENT | 告警/事件 | 事件总线 | 0.5 |
| BATCH | 批量任务 | 邮箱 | 0.05 |
| BROADCAST | 全员广播（仅紧急/制度/重启三类，≤月5次） | 广播 | 10.0 |

**硬规则**：
- STATUS/ACK **禁止**走消息通道（强制黑板）
- BROADCAST 仅三类白名单（紧急/制度/重启）且 ≤月 5 次
- 迭代报告 → 黑板 data/iterations/ 归档即止，协调者不逐条确认
- agent_send 目标==自己时跳过（防回环）
- 纯确认/重复/低价值消息不发 agent_send（agent_send v2.1：非紧急只发「看黑板 <key>」最短提示）

### 1.3 职责命名空间（各角色 STATUS/结果写自己的 namespace）

| 角色 | 命名空间 |
|---|---|
| 恢复自查 6ed4daf2 | data/recovery/ |
| 学习 a3bc8cba | data/learning/ |
| 运营 aa528267 / 45f89009 | data/ops/ |
| 数据调查 4787d717 | data/investigate/ |
| 供应链 0e84e65c | data/supply-chain/ |
| QA ffb7c3ab | data/qa/ |
| 媒体 54e809ed | data/media/ |
| 摄取 55d4d1bd | data/ingest/ |
| **HR（资源管理者）** | **data/registry/** |
| 协调者 | data/iterations/ |

写一次 → 黑板事件桥自动推回 → 事件驱动消费（零轮询零 ACK）。

---

## 二、资源管理逻辑：红绿灯协议 + 登记表 + 同源互斥

### 2.1 红绿灯协议（所有会话必守）
1. **同源操作前必查灯**：`agent_light(resource)`——绿灯=空闲可直接做；红灯=被占用（看 holders/模式/队列）
2. **独占时锁**：`agent_lock(resource, mode:"exclusive"|"shared", wait:true)`——红灯且不兼容可排队（FIFO），轮到收 🚦 通知
3. **完成后必解锁**：`agent_unlock(resource)`——变绿或转交队列下一位
4. **禁止绕过锁**：write/edit 命中红灯会被自动拦截（自动冲突检测）；工具异常退出后必须 agent_light 复核锁状态（实战教训：b3778a1e 交接 edit 报错遗留锁）

### 2.2 资源登记表（resource-registry.md）
- **权威登记表**：~/.dsh-collab/resource-registry.md（维护者=HR，版本化 v1.0.355）
- 登记内容：资源类型分类（file:/panel:/store:/im_window:/port:/db:/chroma:/device:/service:/msg:/channel:/browser:/task:/agent:）、能力档案登记索引（agent_profiles）、当前活动锁快照、仲裁记录
- **归属以登记表 + data-ownership.md 为准绳；锁状态以 agent_light 实测为准**
- 新资源/新能力 → agent_profile 登记 + registry 登记（走红绿灯）

### 2.3 同源互斥
- 同源 = 同一文件/同一后台/同一任务/占用某智能体/同一店铺窗口
- 多智能体可能同时操作 → 操作前必查灯（§2.1）
- 常见锁约定：
  - 店铺窗口（store:N）→ 单店串行，同店写操作复用 lock("store:N")
  - IM 窗口（im_window:N）→ 导航权归属监控方，导航前查灯
  - 模型（lm:model / device:pc-i9:gpu）→ load/unload 独占，训练持锁推理排队
  - 共享工作区 ~/dsh-collab/ → L2 红绿灯落盘约定
  - config.json → lock("file:config.json")

### 2.4 数据归属（data-ownership.md）
- 外卖数据层：comm.db（a3bc8cba 专属写）/ app.db events+im_sessions（de7b29de 专属写）/ kb_docs（a3bc8cba 可写）/ stores（双方只读）
- 跨域写：先 agent_light 声明 + 对方同意，或走红绿灯锁排队
- 只读连接不持锁（SQLite WAL 并发安全）

---

## 三、所有规则门

### 3.1 权限分级门控（agent-bus-permissions.md）

| 级别 | 示例 | 门控要求 |
|---|---|---|
| L1 只读/本地 | 查状态/读文件/KB 检索/agent_peers/agent_light | 无需锁，可随时 |
| L2 共享资源写 | 改共享文件/同店运营动作 | agent_light → agent_lock(wait:true) → 操作 → agent_unlock |
| L3 系统级操作 | pkill/重启服务/改 CLD.app/重签/package.json/node_modules | **aibus 评估门**（广播评估+协调裁决）+ 红绿灯独占 |
| L4 全局重启 | 重启 CLD 宿主 | aibus 评估门全流程（预检→广播→就绪确认→倒计时→重启→恢复验证） |

### 3.2 agent_send 门禁（v2.1/2.3 最短提示）
- 非紧急（回报/通知/待办提醒）→ 只发「看黑板 <key>」，内容写黑板
- 紧急（立即行动/决策/数字时间凭据）→ 可全文 ≤200 字
- 纯确认 → 不回（防刷屏）
- 工具层门禁：>200 字非紧急拦截（已工具化硬化）
- 双向适用：智能体↔中枢

### 3.3 审批分级（J45 / approval-tier / approval-config.json）
- **四级审批**：L0 auto（自动放行）→ L1 sink（记录）→ L2 confirm（确认）→ L3 confirm（高成本确认）
- 模式开关：auto / loose / normal（默认）/ strict
  - auto: L0 only
  - loose: L0/L1 sink
  - normal: L0/L1 sink + L2/L3 confirm（当前默认）
  - strict: L0-L2 all confirm
- **12 条硬性升级**（hard_escalation，任何一级命中即升 L3 审批）：
  cost_trigger（成本触发）/ external_commit（外部承诺/金钱往来）/ destructive（破坏性变更）/ compliance（合规边界）/ cross_domain（跨域架构变更）/ batch_multi_store（批量多店）/ data_exfiltration（数据出域隐私）/ role_permission_change（角色权限变更）/ rule_self_change（规则自改）/ audit_tamper（审计防线）/ credential_change（凭据变更）/ off_hours_batch（非营业时间批量）

### 3.4 成本门禁（approval-config.json cost_gate）
- **单任务预估闸门**（task_gate）：基线 L0 ¥10 / L1 ¥30 / L2 ¥100 / L3 ¥200 × 价值系数（low 0.5 / normal 1 / high 2 / strategic 3）
- **ROI 阈值**：high ≥2（高价值做）/ keep ≥1（维持）/ watch <0.5（观察）
- **全局熔断**（global_fuse）：单日累计真实成本 fused ¥100（熔断提醒）/ halt ¥200（停止）
- **周期兜底**（period_fuse）：周 ¥500 / 月 ¥1000 熔断
- **错峰调度**：高峰 09-12/14-18 只跑实时必需；批处理排空闲半价窗（flash 高峰 ¥9 vs 空闲 ¥4.5/百万）
- **本地模型路由**：LM Studio/Ollama 零订阅；J35 本地模型互斥（不同时开模型，用完即关）

### 3.5 去重
- 同发件人同线程同内容 10 分钟自动去重（agent_send 返回 duplicate）
- 事件总线：dedup_key + sent 标记；已过期信号（>24h）归档不发送

### 3.6 审计
- gov audit：工具调用事件全记录（按 agent/tool 聚合），支撑 token 台账/成本核算
- 数据源：~/.dsh/gov/audit.jsonl + gov.json（per-agent 配额，global 日 5 亿 token 上限）
- 每日日审 + 周汇总 + 成本审计（HR 职责）

---

## 四、MBP 参与要点（速查）

1. **接入**：agent_profile 登记角色/能力/资源归属；agent_peers 看在线会话
2. **消息**：STATUS/ACK 写黑板（data/<role>/），TASK 走 p2p，实质讨论走线程；非紧急只发「看黑板 <key>」
3. **资源**：动共享资源前 agent_light → 需要独占 agent_lock(wait:true) → 完成 agent_unlock
4. **新资源**：agent_profile 登记 + registry 登记（可委托 HR）
5. **高危**：L3/L4 系统级操作必须走 aibus 评估门（协调者裁决）；12 条硬性升级命中即 L3 审批
6. **成本**：单任务 >¥10 触发 L0+ 评估；日累计 >¥100 熔断提醒、>¥200 停止；pro 模型（3 倍价）仅高危任务
7. **审批**：需用户裁决事项挂异步审批队列（不阻塞主线），高危即时事项走协调者弹窗
8. **边界**：系统级变更（CLD/DSH 本体/签名/目录迁移/插件热重载）不经用户批准不得执行；提案依据必须本地向量化来源

---

*MBP 协作规则同步 v1.0 · HR 2a15e6b1 · 2026-08-27 · 疑问咨询协调者或 HR*
