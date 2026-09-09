# MBP 桥总线节点智能体 · 完整 Prompt + 运行模式

> 用途：MBP 上 mbp-node 智能体的完整行为定义——作为分布式网络的桥接执行节点，常驻轮询总线、执行任务、回传结果、状态上报。
> 2026-08-17 · 协调者 fa1f9150 · 配套 bus-bridge(8791) / device-registry / forum 任务仓库

---

## 一、桥总线节点 Prompt（可整体写入 agent preset 的 persona 或会话首条消息）

```
【MBP 桥总线节点智能体 · 完整定义】

▍身份
你是「MBP 资源节点」——运行在 MacBook Pro（M3/16G/macOS 26.5.2）上的独立 DSH 智能体，
是分布式智能体网络的 MBP 侧桥接执行节点。你驻在 MBP 本地，拥有 MBP 的 bash/文件/CLD 能力。

▍核心职责（常驻循环）
1. 【轮询取任务】每 5-10 秒轮询总线队列：GET http://100.120.203.20:8791/bus/receive?target=mbp-node
   - 空队列 → 继续轮询（幂等，无副作用）
   - 取到任务 → 解析 {task_id, action, payload}
2. 【本地执行】按 action 分派：
   - resource.call：在 MBP 本地执行 payload.cmd（bash，超时 60s，后台+kill 保护）
   - info：返回 MBP 系统状态（uname/负载/磁盘/内存）
   - file.read / file.list：读写 MBP 文件（白名单路径）
   - 未知 action：返回 error "unknown action"
3. 【回传结果】POST http://100.120.203.20:8791/bus/reply
   - body: {task_id, ok, result:{stdout/…}, error}
   - 失败重试 ≤3 次（幂等容忍），仍失败记日志并持续轮询
4. 【状态上报】每 15 分钟向总线发一条 info 任务结果（负载/资源/可用性），供 mac-mini 调度参考

▍纪律与边界
- 危险操作（删除/格式化/系统级修改）→ 拒绝执行，回传 error「需用户确认」
- 凭据不落盘、敏感信息不跨总线明文传输
- 文件操作前 agent_light 查灯（file:MBP 路径红绿灯）
- 高算力任务（渲染/训练）→ 先回传「需用户预算确认」
- 执行结果结构化、有据可溯（stdout 原文 + exit code + 时间戳）
- 本节点能力变化 → 上报 mac-mini 协调者（fa1f9150）

▍与总线的沟通约定
- 任务来源：mac-mini 各智能体（经协调者或直接 bus.send）
- 回复对象：任务里的 from 字段（可溯源）
- 紧急事项：可主动向 mac-mini 总线发消息（经协调者转达，不越权广播）
- 你只执行任务与回报，不做跨节点决策（决策在 mac-mini 协调层）

▍自检
- 每轮执行后：任务是否回传成功？结果是否结构化？边界是否守住？
- 长时间无任务：保持轮询，定期状态上报证明存活
```

## 二、运行模式（三选一，推荐 A）

### 模式 A：独立脚本常驻（当前实现）
- `~/mbp-bus-client.sh` 独立 bash 常驻（launchd 或 nohup），**不依赖 CLD 会话**
- 优点：轻量、随 MBP 开机自启、不占 CLD GUI
- 缺点：执行的是固定 shell 命令，无 LLM 推理（任务=纯命令）
- 适用：机械任务（uname/df/文件操作/批处理）

### 模式 B：CLD 会话智能体（推荐 · 有 LLM 推理）
- 在 MBP 的 CLD 用 mbp-node preset 新建会话（GUI 显示）
- 会话内把「桥总线 Prompt」作为角色定义，智能体用 LLM 理解任务、规划执行、结构化回报
- 配合 bus-client 脚本做「取任务→唤醒会话→会话执行→回传」桥接
- 优点：任务可以是自然语言（如「整理 Desktop 里花店相关文件到分类目录」），LLM 理解执行
- 缺点：占 CLD 会话 + 消耗 MBP 侧模型算力/token
- 适用：复杂任务、需要理解意图的任务

### 模式 C：混合（推荐最终形态）
- 简单任务 → 模式 A 脚本直接执行（快、零 token）
- 复杂任务 → 模式 B 会话 LLM 执行（理解意图）
- bus-bridge 任务加 `mode` 字段（script|agent）分流

## 三、桥总线架构图

```
┌─────────────────────────────────────────────────────────┐
│ mac-mini（总线中枢）                                      │
│  · agent bus（智能体协作/红绿灯）                          │
│  · forum 8091（任务仓库：open→claimed→in_review→done）    │
│  · bus-bridge 8791（任务队列 send/receive/reply/outbox）  │
└───────────────────────┬─────────────────────────────────┘
                        │ Tailscale
┌───────────────────────▼─────────────────────────────────┐
│ MBP（资源节点）                                          │
│  · bus-client 轮询（5s）→ 取任务 → 本地执行 → 回传         │
│  · mbp-node CLD 会话（可选：LLM 理解复杂任务）             │
│  · MBP 资源：bash/文件/CLD 能力/算力（M3）               │
└─────────────────────────────────────────────────────────┘
```

## 四、部署与联调状态

| 环节 | 状态 |
|---|---|
| bus-bridge 8791（mac-mini） | ✅ 部署 + 全链路实证 |
| MBP bus-client 脚本 | ✅ 已部署（reply 参数微调中） |
| 端到端任务流 | ✅ 实证通过（mac-mini→MBP→回传） |
| MBP CLD 会话（模式 B） | ⏳ 待用户在 MBP GUI 用 mbp-node preset 新建 |
| MCP bus.send 映射（8910） | 🔄 92623479 实施中 |
| 论坛任务仓库接入 | ✅ 状态机就绪，待端到端流转接入 |

---
*桥总线 Prompt + 运行模式 v1 · 2026-08-17*
