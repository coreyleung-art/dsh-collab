# i9 协作规则同步文档（Windows）· 底层规则 + 资源管理 + 规则门

> 版本：v1.0 → **v2.2.0（2026-08-31 同步规则账本 v2.2.0）** · 产出：HR 司库（资源管理者）
> 账本 v2.2.0 变更：R020 新工具蓝图适配闭环（新工具出现→同步明鉴→蓝图适配分析→纳入交付规则）+ R017-R019 同步修复
> R024（v2.6.0）：子代理新建前评估纪律——新建子代理前必查现有（subagent-govern check-new/audit），同类型可复用则复用不新建；任务完成即归档不做常驻；主角色黑名单灾难防护
> 账本同步：R002 v1.1 collab 广播纪律生效（①全局重要→collab ②定向→notes/<node>/ 或 agent_send ③写前自问所有端都需要吗 ④定向能达不用 collab ⑤collab 留档兜底）
> 用途：i9（Windows 节点）接入 Agent Bus 协作网络的规则说明——正确参与红绿灯/资源登记/审批/成本门禁
> 基础：docs/mbp-collab-rules-sync.md（MBP 版，本版做 Windows 适配 + i9 特有补充）
> 配套：resource-registry.md（登记表 v1.0.355）· resource-conflict-policy.md（规范集）· agent-bus-permissions.md（权限门控）· approval-config.json（审批配置）· token-cost-management.md（成本策略）

---

## 一、底层规则：Agent Bus 原理与通道纪律

### 1.1 总线原理（与 MBP 版一致）
- **消息**：agent_send 定向投递（目标被唤醒）；agent_broadcast 群发/广播；agent_thread 线程会话
- **线程**：thread id 串联多轮讨论（COLLAB）；消息带 thread 可续聊
- **持久化**：总线状态存 ~/.dsh/agent-bus.json（Windows: %USERPROFILE%\.dsh\agent-bus.json）
- **唤醒**：消息走宿主真实收件箱（followup 唤醒）；离线目标进待投递队列，上线自动送达
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
- 纯确认/重复/低价值消息不发 agent_send（v2.1：非紧急只发「看黑板 <key>」最短提示）

### 1.3 职责命名空间（i9 侧）

| 角色 | 命名空间 |
|---|---|
| i9 职责角色-数据沉淀 | data/i9/sediment/ |
| i9 职责角色-算力训练 | data/i9/compute/ |
| i9 职责角色-ERP 打通 | data/i9/erp/ |
| i9 职责角色-工具链 | data/i9/tools/ |
| i9 族智能体（5 族） | data/i9/families/<family_id>/ |
| mac 侧各角色 | data/<role>/（mac 命名空间约定） |

写一次 → 黑板事件桥自动推回 → 事件驱动消费（零轮询零 ACK）。

---

## 二、资源管理逻辑：红绿灯协议 + 登记表 + 同源互斥

### 2.1 红绿灯协议（所有会话必守，与 MBP 版一致）
1. **同源操作前必查灯**：`agent_light(resource)`——绿灯直接做；红灯看 holders/模式/队列
2. **独占时锁**：`agent_lock(resource, mode:"exclusive"|"shared", wait:true)`——红灯不兼容可排队（FIFO），轮到收 🚦 通知
3. **完成后必解锁**：`agent_unlock(resource)`——变绿或转交队列下一位
4. **禁止绕过锁**：write/edit 命中红灯自动拦截；工具异常退出后必须 agent_light 复核锁状态

### 2.2 资源登记表（resource-registry.md）
- **权威登记表**：~/dsh-collab/resource-registry.md（维护者=HR，版本化 v1.0.355）
- **归属以登记表 + data-ownership.md 为准绳；锁状态以 agent_light 实测为准**
- 新资源/新能力 → agent_profile 登记 + registry 登记（走红绿灯）

### 2.3 同源互斥（i9 特有扩展）
- 通用：同一文件/后台/任务/智能体/店铺窗口 → 操作前必查灯
- **device:pc-i9:gpu 锁（i9 特有）**：4060Ti 8GB VRAM 是单点约束——
  - flower-biz 训练（CUDA PyTorch）持 exclusive 锁，ai-lab/supply-chain 推理排队
  - Ollama 模型加载走 lm:model 锁（load/unload 独占）
  - **3 路 Ollama qwen2.5:7b 不能同时常驻 GPU**（3×~5GB > 8GB）→ 单实例按需加载，用完即卸（J35 本地模型互斥）
- **config.json / i9-bb 写通道**：黑板服务端只认显式 Content-Length（i9-bb.py 已封装），写前查灯

### 2.4 数据归属
- i9 侧：E 盘资产吸收/扫描/档案归 i9-duty-sediment；训练/模型库归 i9-duty-compute；ERP 数据归 i9-duty-erp
- mac 侧数据归属按 data-ownership.md；跨域写先 agent_light 声明 + 对方同意

---

## 三、所有规则门（与 MBP 版一致 + i9 适配）

### 3.1 权限分级门控（agent-bus-permissions.md）

| 级别 | 示例 | 门控要求 |
|---|---|---|
| L1 只读/本地 | 查状态/读文件/KB 检索/agent_light | 无需锁，可随时 |
| L2 共享资源写 | 改共享文件/同店运营动作 | agent_light → agent_lock(wait:true) → 操作 → agent_unlock |
| L3 系统级操作 | pkill/重启服务/改 CLD.app/重签/package.json/node_modules | **aibus 评估门**（广播评估+协调裁决）+ 红绿灯独占 |
| L4 全局重启 | 重启 CLD 宿主 | aibus 评估门全流程（预检→广播→就绪确认→倒计时→重启→恢复验证） |

### 3.2 agent_send 门禁（v2.1/2.3 最短提示）
- 非紧急（回报/通知/待办提醒）→ 只发「看黑板 <key>」，内容写黑板
- 紧急（立即行动/决策/数字时间凭据）→ 可全文 ≤200 字
- 纯确认 → 不回（防刷屏）；工具层门禁：>200 字非紧急拦截；双向适用

### 3.3 审批分级（J45 / approval-tier / approval-config.json）
- **四级审批**：L0 auto → L1 sink → L2 confirm → L3 confirm（高成本确认）
- 模式开关：auto / loose / normal（默认：L0/L1 sink + L2/L3 confirm）/ strict
- **12 条硬性升级**（命中即 L3）：cost_trigger / external_commit / destructive / compliance / cross_domain / batch_multi_store / data_exfiltration / role_permission_change / rule_self_change / audit_tamper / credential_change / off_hours_batch

### 3.4 成本门禁（approval-config.json cost_gate）
- **单任务预估闸门**：基线 L0 ¥10 / L1 ¥30 / L2 ¥100 / L3 ¥200 × 价值系数（low 0.5 / normal 1 / high 2 / strategic 3）
- **ROI 阈值**：high ≥2 / keep ≥1 / watch <0.5
- **全局熔断**：单日累计真实成本 fused ¥100 / halt ¥200
- **周期兜底**：周 ¥500 / 月 ¥1000
- **错峰调度**：高峰 09-12/14-18 只跑实时必需；批处理排空闲半价窗
- **本地模型**：Ollama 零订阅（i9 主力：qwen2.5:7b/3b + CUDA 训练本地推理）

### 3.5 去重
- agent_send 同内容 10 分钟去重；事件总线 dedup_key + sent 标记；>24h 过期归档

### 3.6 审计
- gov audit：工具调用全记录（~/.dsh/gov/audit.jsonl），per-agent 配额
- 每日日审 + 周汇总 + 成本审计（HR 职责）

---

## 四、Windows 侧差异适配（i9 特有）

| 项 | mac（MBP/mac-mini） | Windows（i9） |
|---|---|---|
| 环境变量 | launchctl / ~/.zshrc | **setx / 注册表**（重启生效） |
| 路径 | ~/... （/Users/xxx） | **%USERPROFILE%\...**（C:\Users\xxx） |
| 常驻服务 | launchd plist（~/Library/LaunchAgents/） | **任务计划程序**（schtasks）或 NSSM 服务 |
| 进程管理 | pgrep / ps aux / kill | tasklist / taskkill / PowerShell Get-Process |
| 编码 | UTF-8 | **GBK 需转码**（systeminfo 等输出回报前转 UTF-8） |
| 换行 | LF | CRLF（脚本注意） |
| 网络 | localhost 127.0.0.1 | 同（Tailscale 组网） |
| 写黑板 | curl + Content-Length | **i9-bb.py**（显式 Content-Length 封装，http.client） |

### 4.1 i9 双通道（executor 轮询 + 中央注入）
- **executor 轮询**：任务卡轮询（tasks/i9/queue/*）→ 执行 shell/info/ollama/scan → 结构化回报（task_id + ok + output）
- **中央注入**：中枢消息注入 central-inbox → 唤醒/指令
- 两通道职责：轮询接任务（TASK），注入接消息（COLLAB/通知）；心跳/自检 8h 周期 + 每日自检
- **模型约束**：i9 无 claude CLI（LLM 执行器触发即失败，不烧钱）；LLM 能力启用必须过三因子检查（模型配置核对/成本门禁/防循环）

### 4.2 i9 角色与族（registry 已登记 v1.0.355）
- 职责角色 ×4：i9-duty-sediment / compute / erp / toolchain（agent:i9-duty-*）
- 族智能体 ×5：flower-biz / supply-chain / tools / ai-lab / activity（project-family:*）
- 模型策略：flower-biz/activity/erp 在线 v4-flash；其余 Ollama 零订阅
- 属主：全部归属 i9 总线（边界纪律 v2.0：i9 设备侧归 i9 智能体，协调者只读）

---

## 五、i9 参与要点（速查）

1. **接入**：agent_profile 登记角色/能力/资源归属；agent_peers 看在线会话
2. **消息**：STATUS/ACK 写黑板（data/i9/<duty>/ 或 data/i9/families/<族>/），TASK 走 p2p；非紧急只发「看黑板 <key>」
3. **资源**：动共享资源前 agent_light → 独占 agent_lock(wait:true) → 完成 agent_unlock
4. **GPU**：训练持 device:pc-i9:gpu 锁；Ollama 单实例按需加载（8GB VRAM 装不下 3×7b）；训练与推理错峰
5. **新资源**：agent_profile 登记 + registry 登记（可委托 HR）
6. **高危**：L3/L4 系统级操作必须走 aibus 评估门（协调者裁决）；12 条硬性升级命中即 L3
7. **成本**：单任务 >¥10 评估；日累计 >¥100 熔断提醒、>¥200 停止；pro 模型（3 倍价）仅高危任务；i9 本地算力零订阅优先
8. **审批**：需用户裁决挂异步审批队列（不阻塞主线），高危即时事项走协调者弹窗
9. **边界**：系统级变更（CLD/DSH 本体/签名/目录迁移/插件热重载）不经用户批准不得执行；提案依据必须本地向量化来源
10. **环境**：Windows 命令用 tasklist/taskkill、路径 %USERPROFILE%、GBK 输出转码、写黑板用 i9-bb.py

---

*i9 协作规则同步 v1.0 · HR 2a15e6b1 · 2026-08-27 · 疑问咨询协调者或 HR*
