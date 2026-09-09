# 星桥「失忆」根因分析（2026-09-03 考古）

> 现象：i9 回复（notes/i9/*）、回传内容（trae 文档）我未及时感知，需用户/i9 提醒才发现
> 本质：不是记忆丢失，是「感知盲区」——内容都在黑板持久化，但事件注入没覆盖

## 失忆事件时间线（证据）
| 时间 | 事件 | 我的响应 |
|------|------|---------|
| 01:39 | i9 写 trae-design-doc-content + done | ❌ 未感知（直到 02:00 用户提醒才转老登，21 分钟延迟） |
| 01:45 | i9 写 coordinator-sync-reply（含完整通道说明） | ❌ 未感知（直到 i9 完整提示 + 用户转述才读到） |
| 01:53 | i9 写 page-structure-list-001-done（内容空） | ❌ 未感知 |
| 多任务 | tasks/i9/cmd 投递后 i9 消费到 empty cmd | 通道反复失败（festival-pipeline/trae/asset-inventory） |

## 根因三层

### 1. 架构层：会话消息驱动，无主动感知跨设备回复域
- 会话动作由「消息注入」触发（agent_send/用户消息/bb-sub 事件注入）
- 无后台主动轮询黑板的能力（或未配置）
- i9 写 notes/i9/ 回复 → 若无注入事件 → 内容静默等待 → 我「看不到」
- **agent_send 只覆盖本机进程**（agent-bus 架构限制）——i9 跨设备无法 agent_send 到 mac

### 2. 配置层：bb-sub 订阅范围假设错误（监控盲区）
- bb-sub.coordinator 订阅 notes/collab/ + notes/mac-mini/ + tasks/central/queue/
- **假设：跨设备节点会走 collab/mac-mini 域回复** → 实际 i9 因 W75 认证只能写 notes/i9/（匿名可读域）
- i9 的回复域 = coordinator 订阅盲区 → 设计假设与实际通道不符

### 3. 执行层：修复未验证端到端
- 修复 bb-sub 加 notes/i9/ 用 `kickstart -k` → launchd 未重载 plist（缓存旧配置）→ 修复表面做了实际未生效
- 只验证「我→黑板」单向写入，未验证「i9 写 → 事件注入 → 我感知」端到端
- tasks/i9/cmd 多写者冲突（我+罗盘等多方写同一 key）→ empty cmd 反复

## 修复（已做）
1. bb-sub.coordinator 订阅加 notes/i9/（bootout+bootstrap 真正重载）✅
2. i9 任务改走 notes/i9/ 域（弃用 tasks/i9/cmd——trae 文档成功验证）✅
3. 清理空任务卡 + 回执机制（i9 写回复我读后回执）✅

## 防复发（机制）
1. **重启 SOP 加「跨设备回复域检查」**：重启后验证 bb-sub 订阅含 notes/i9/（不只 collab/mac-mini）
2. **配置变更后必 bootout+bootstrap**（kickstart 不可靠——两次教训）
3. **端到端验证**：跨设备通道变更后，实测「对方写→我收到」闭环（不只单向）
4. **感知覆盖原则**：所有跨设备节点的「可写域」必须是星桥订阅域——新增节点/认证变更时同步检查

## 核心教训
- 「失忆」= 感知盲区 ≠ 记忆丢失——数据都在，缺的是事件注入
- 感知覆盖必须匹配节点的实际可写域（W75 下 i9 只能写 notes/i9/）
- 单向验证 ≠ 通道可用——必须端到端
