# R-ERR4 草案 · 全局注册表规范（E2 发现层 · 明鉴起草 2026-09-06）

> 状态: **draft**（待 R008 流程吸收：星桥/明鉴提案 → HR 打磨 → 用户裁决）
> 关联: E2 全局注册表计划（comm-server/e2-registry-plan-v1.md v1.2）· agent-network cs2-2b · R-ERR1/2/3 同族

---

## 规则条目（拟入 RULES.md + rules.json）

### R-ERR4 ✅ 全局注册表写入规范（E2 发现层 · 2026-09-06 提案）
- 分类: 工程 | 范围: all-bus-devices | 状态: draft
- 摘要: 跨设备身份/发现层 data/discovery/agents/<device>：**写入方=心跳代理(hb-fwd/端侧注册器)，读=全体**；键 schema v1；心跳驱动单源；G5 活性判定(<90s=online)读侧统一
- 详情: ①命名空间 data/discovery/agents/ 独立于治理域(data/registry)，防写权限混叠 ②写入权：仅心跳代理（mac-mini hb-forward.py + 各端注册器），其余会话只读——发现层数据不被随意覆盖 ③schema v1 = {device, sessions:[{session_id, role, status, ts}], ts}，device/session/role 从 comm_domains + agent_profiles 单源对齐 ④活性判定统一：读侧用同一规则(心跳 ts < 90s = online)，防各工具口径分叉 ⑤键用 PUT 覆盖续期(非 append)，防膨胀 ⑥注册表查不到 ≠ 不存在——降级本地缓存(服务器不可达设计内)

### 实施对齐
| 项 | 值 |
|---|---|
| 位置 | data/discovery/agents/<device>（xingqiao 中枢，公网 24h） |
| 写入方 | hb-fwd 扩展 / i9 executor / MBP agent 注册器（端侧） |
| 读取方 | 全体（bb-gate registry / dsh-tools who-is-online / 罗盘 device-assets） |
| 验证 | 步骤 5 跑 R-ERR3 实例（登记/查重）；周复盘入 ErrorNet 轮值 |

### 与既有规则关系
- R-ERR1/2/3：同族（ErrorNet 防复发）；R-ERR4 是"发现层写入"规范延伸
- R001 红绿灯：data/discovery/ 域写前查灯（心跳代理多写竞争）
- R004 central-inbox：端侧注册与会话活性判定供其消费

---
*R-ERR4 draft v1 · 明鉴 · 2026-09-06 · 待 R008 流程*
