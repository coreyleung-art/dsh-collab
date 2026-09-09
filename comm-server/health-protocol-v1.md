# comm-server 标准化健康协议 v1（cs2-2 · agent-network v1.3 蓝图）

> 2026-09-04 星桥起草 · 根治「心跳假阳性」（i9 反复失联教训）
> 核心：健康判定 = 守护自动 ack，不是「进程写心跳」

## 一、为什么心跳会假阳性（i9 教训）

| 信号 | 谁写的 | 能代表什么 |
|---|---|---|
| `nodes/<node>/heartbeat` | 独立守护进程（60s 定时） | ❌ 只代表「机器/守护活着」，不代表 CLD 会话在处理 |
| 手动测试键（link-probe） | 人（老板转达时手写） | ❌ 一次性手动，不证明自动化链路 |
| 回执卡 version | bb-sub 读卡 | ❌ 读卡不改写 version，无法判断消费 |

**判据错误 → 反复「虚假修复」**：验证用了「手动写的键存在」当证据，人写的东西当然存在，但自动化链路根本没恢复。

## 二、协议：双心跳 + 自动 ack

### 1. 双心跳（区分机器活 vs 智能体活）
- `nodes/<node>/hb-daemon`：守护进程写（现有 heartbeat 改名语义）——机器级
- `nodes/<node>/hb-session`：**CLD 会话内的 bb-sub/agent 写**（含 session-id、最后处理黑板卡时间戳）——智能体级

判定规则（服务器/协调者执行）：
- hb-daemon 新鲜 + hb-session 新鲜 → **健康**
- hb-daemon 新鲜 + hb-session 陈旧 → **会话失联**（告警，不判整体死）
- 两者都陈旧 → **节点失联**

### 2. 自动 ping/ack（权威判活，不经 LLM）
- 协调者每 **10 分钟**写 `tasks/health/ping-<node>-<ts>`
- 目标节点**守护进程**（非 LLM 会话）自动回写 `tasks/health/ack-<node>-<ts>`（HTTP 直达 < 1s）
- **连续 3 轮（30 分钟）无 ack → 判真失联** → cs4 自动恢复触发
- 守护代答机制：ack/回报类确定性任务由守护直接完成，不进 LLM 上下文

### 3. 部署要求（各端守护必须实现）
每端一个轻量常驻进程（mac-mini launchd / i9 Windows nssm / MBP launchd）：
- [ ] 60s 写 hb-daemon
- [ ] 轮询 ping 卡 → 即时写 ack（带自身 session 活性状态）
- [ ] 检测 hb-session 超时 → 本地自动唤醒 CLD 会话（agents.resume 等）
- [ ] 收任务卡 → 简单任务直接完成回报；复杂任务写入注入队列等会话处理

## 三、数据一致性（防分叉）

1. **前缀规范**：唯一合法键 = `notes/<node>/<topic>`（**无 /api 前缀**）+ 扁平 `content` 结构
2. 写前验证：PUT 后 GET 回读非空才算成功（i9 曾写 401/落错存储）
3. 迁移（cs2-3）：`api/notes/*` 分叉数据扫描 → 合并去重到 `notes/*` → 归档旧键

## 四、验收标准（cs3-4 故障演练）

- [ ] A1: mac-mini 重启模拟 → i9/MBP 通讯不中断（单一事实源生效）
- [ ] A2: i9 会话假死 → 守护检测 hb-session 陈旧 → 30 分钟内自动恢复（非手动）
- [ ] A3: ping→ack 全自动，无人工写测试键
- [ ] A4: 前缀分叉为零（扫描 api/notes 无新键）
- [ ] A5: 部署 SOP 可复跑（服务器重装后一键恢复）
