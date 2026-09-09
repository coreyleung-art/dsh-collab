# E2 全局注册表落地计划 v1 + 价值评估（2026-09-06 · 星桥）

> 背景：i9→MBP「找不到」（agent_peers 本地化孤岛）暴露分布式通讯缺「全局发现层」
> 前置评估：cross-device-arch-eval-v1.md（§五 发布-订阅 / §六 稳定性成本 / §七 中期跳跃）
> 本文档：完整执行计划（供明鉴按蓝图评估 + HR 打磨）+ 注册表/消息路由中枢价值评估

---

## 一、价值评估：注册表 vs 消息路由中枢

### A. 全局注册表（身份/发现层）—— 推荐做
**价值**：
1. 解决 P1/P3：任何端可答「谁在线 / 会话 id / 能力 / 路由可达」——消除 agent_peers 孤岛
2. 数据驱动：记录会话活性/路由统计 → E3 白名单直连评估依据
3. 中立身份：跨设备协作的「通讯录」（谁找谁先查表）
4. 低资源：KB 级元数据（非消息体），服务器 1G 无压力；查询轻

**成本**：hb-fwd 扩展 + 各端注册逻辑 + 查询工具 ≈ 低（复用现成心跳/comm_domains）

**风险**：服务器注册表不可达 → 降级本地缓存（设计内）；无消息流依赖

### B. 消息路由中枢（传输层中心化）—— 不做（低价值高风险）
**评估**：
1. SPOF：消息必经服务器 = 服务器挂全断（vs 本地黑板域自治）
2. 冗余：发布-订阅已解消息流（域直读零中间人）——路由中枢增量价值 ≈ 0
3. 成本高：需服务器路由逻辑/转发规则/审计 —— 服务器 1G 跑全消息流风险
4. 违背分布式：各端自治 → 消息不该强制过中心
**保留子场景**：任务式交互走 bus-bridge（已有队列语义，非消息流）

### C. 结论矩阵
| 组件 | 价值 | 风险 | 成本 | 决策 |
|---|---|---|---|---|
| 全局注册表(发现) | 高 | 低(可降级) | 低 | ✅ 做（E2）|
| 消息路由中枢 | 低 | 高(SPOF) | 高 | ❌ 不做（域自治+bus 兜底）|

---

## 二、E2 注册表完整执行计划

### 设计
- **位置**：服务器中枢 data/discovery/agents/<device>（公网可达 24h，实测承载 OK）
- **Schema**：`{device, sessions:[{session_id, role, status, ts}], ts}`——心跳驱动
- **在线语义**：活心跳(<90s G5) = online；超时 = offline（读侧判定，非写侧）
- **单源**：device/session/role 从 comm_domains + agent_profiles 对齐

### 执行步骤
| # | 步骤 | 实现 | 验证(R030) |
|---|---|---|---|
| 1 | hb-fwd 扩展：推心跳同写注册表 | mac-mini hb-forward.py + 服务器 | 服务器 data/discovery/agents/mac-mini 出现 |
| 2 | 各端注册：i9 executor/MBP agent 启动注册+续期 | 端侧脚本（资产分发 bb-gate 同批）| i9/MBP 注册键出现 |
| 3 | 查询工具：bb-gate registry / dsh-tools who-is-online | 读注册表 + G5 活性判定 | 查全端会话/能力 |
| 4 | 罗盘 device-assets 数据源切注册表 | 会话级扩展 | 资产表含在线会话 |
| 5 | 文档+RULES：注册表规范（写入方=心跳代理，读=全体）| rules-registry + comm_domains | R-ERR 审计通过 |

### 涉及方
- 星桥：计划/设计/hb-fwd 扩展/查询工具
- 明鉴：按蓝图评估（comm-server 蓝图 cs0-cs4 / SystemGraph 架构图注册表节点）
- HR：协调打磨/规则登记/R-ERR
- 罗盘：device-assets 会话级扩展
- i9/MBP：端侧注册（资产分发）

### 风险与门
- 服务器不可达：本地缓存 + seen（读侧降级）✅ 设计内
- 注册表膨胀：仅存元数据 + 心跳续期覆盖（非 append）✅
- 各端注册不一致：schema 单源 + 心跳驱动（活=在线客观判定）✅
- 容量：KB 级/设备，1G 无压力（已实测）✅

### 时间窗
- 步骤 1-3（核心）：~1-2h 可完成（本机侧）
- 步骤 4-5（协作）：待明鉴/HR/罗盘确认

---

## 三、HR 评审采纳（2026-09-06）
- ✅ 命名空间隔离：data/registry/ 属 HR 治理域 → E2 改用 **data/discovery/agents/<device>**（发现层独立域，与治理裁决键混叠风险消除）
- ✅ 规范入 RULES：建议 R-ERR4/新 R 条目（全局注册表规范, all-bus-devices, 写入=心跳代理/读=全体）
- ✅ R-ERR 衔接：步骤5 验证=R-ERR3 实例；周复盘入 ErrorNet 轮值
- ✅ 价值判断确认：做注册表不做路由中枢

---

## 四、明鉴蓝图评估采纳（2026-09-06）
评估 5 维全绿（详见 notes/mingjian-e2-registry-review-20260906）：
1. ✅ comm-server 蓝图一致性：E2 = cs2-2/cs4-1 延伸补隙；works 登记 cs2-2b(owner=星桥)
2. ✅ agent-network 互补：与 an4-1 能力发现互补不冲突；**schema 预留 ability 字段**（an4-1 未来并入）
3. ✅ SystemGraph 入图：物理层(data/discovery 归 xingqiao) + 跨节点资产图(注册表资产) —— 明鉴承接
4. ✅ HR 命名空间：data/discovery 独立正确
5. ✅ 更优落点：注册表键带设备前缀+schema 版本；PUT 覆盖非 append 防膨胀；**G5 活性判定统一**（心跳<90s=online 读侧判定）
- 明鉴承接：agent-network works 表 cs2-2b 登记 + gallery 资产条目 + R-ERR4 协助起草
