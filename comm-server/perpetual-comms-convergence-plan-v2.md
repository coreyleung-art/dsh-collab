# 永续通讯收敛方案 v2（完整版 · 2026-09-08 · 用户批准推进）

> v1 诊断已获认可；v2 = 完整实施计划（防上下文丢失，含架构划清 + 服务器角色评估）
> 批准：用户 2026-09-08「允许按这个收敛方案推进（把完整计划做出来）+ 评估服务器是否装 CLD/最小 LLM + 划清星桥本体通讯架构」

---

## 〇、目标一句话

**让「任何设备发的消息 → 对应 agent 被唤醒处理 → 回执可达」成为一条有送达保证的链路，用户不再当传话员；并划清哪层通讯存续于本体、哪层必须经服务器。**

---

## 一、架构划清（用户第 3 问：星桥本体 ↔ 所在会话 通讯存续边界）

### 1.1 分层模型（谁存续于哪）

| 层 | 载体 | 存续于 | CLD 重启后 | 服务内容 |
|---|---|---|---|---|
| L0 进程内 | agent-bus（agent_send/threads） | mac-mini CLD 宿主进程 | ❌ 内存态丢失（有 agent-bus.json 落盘兜底） | 星桥↔同机明鉴/老登等**会话级即时通讯** |
| L1 本机黑板 | rust-blackboard 127.0.0.1:8792 | mac-mini 本机（独立 rust 进程） | ✅ 存活 | 本机全部 agent 的消息落点/历史/队列 |
| L2 中枢 | xingqiao 服务器 8792/8791/8803 | **服务器（跨机、跨重启）** | ✅ 存活 | 跨设备消息唯一中继、E2 注册、outbox 持久化 |
| L3 通道 | Tailscale / Funnel | 网络层 | — | 设备间直连快道 + 公网下载 |

### 1.2 关键结论（划清边界）

1. **星桥本体 = session-fa1f9150，住在 mac-mini CLD 进程里。**
   「星桥↔同机会话」（明鉴/老登/守灯等）的通讯 = **L0 agent-bus + L1 本机黑板**，**完全存续于本体（mac-mini）**，不经任何网络、不经服务器。这是"本体通讯"，本地执行优先（R031）——**永不改为走服务器**（会引入无谓延迟与单点）。
2. **跨设备（MBP/i9/手机）的消息才走 L2 中枢。** 中枢的角色 = 跨机中继 + 持久化 + 送达保证，不是本机 agent 的替代。
3. **星桥自己的"能被跨设备找到"** = 中枢 E2 注册（data/discovery/agents/mac-mini）里 session-fa1f9150 是中枢可寻址目标。MBP 写中枢 → 中枢判定 to=fa1f9150 → mac-mini 守护经 L0 agent_wake 注入本机星桥。
4. **因此正确的收敛方向不是"把一切搬服务器"，而是**：
   - 本机 L0/L1 保持本体自治（快、稳）；
   - 服务器 L2 只做**跨设备那一段**的收口 + 送达保证；
   - 缺口在「中枢消息 → 本机 agent 精确唤醒」这一段（现 not-found 空转），补上即闭环。

### 1.3 本机会话唤醒的正确链路（目标）

```
MBP/i9/星台 写中枢 notes/... (to=fa1f9150/星桥)
  → 中枢 SSE 8803 事件
  → mac-mini 守护(bb-sub coordinator 已订阅 notes/collab/,notes/mac-mini/)
  → central-inbox v2: 解析 to → 角色名映射表(星桥=fa1f9150/明鉴=a190c54c...) 
  → agentBus.list() 确认在线 → agent_wake 精确注入本机真实会话
  → 星桥/明鉴 收到，处理，回复写中枢 → 源设备读到
```

---

## 二、服务器角色评估（用户第 2 问：装 CLD？最小 LLM？）

### 2.1 服务器实测资源

| 资源 | 值 | 含义 |
|---|---|---|
| 内存 | **957MB 总 / 432MB 可用** | 极紧张 |
| CPU | 2 核 | 弱 |
| 磁盘 | 40G（33G 空闲） | 磁盘够 |
| 现负载 | rust-blackboard×2 + node×N 已占 ~360MB | 余量 ~430MB |

### 2.2 结论：**不装 CLD，不装 LLM；服务器保持纯消息总线（无状态、低内存）**

理由（每条可验证）：

1. **CLD = 桌面壳 + 多会话宿主，是给 mac-mini 的**。装到无 GUI 的 1G 服务器 = 内存不足 + 架构错位（服务器应无状态转发，不是再开一个 agent 农场）。**明确否决。**
2. **LLM 是"思考"不是"传递"。** 永续通讯要解决的是"消息不丢、能路由、能唤醒"——这是 IO 问题，**不需要推理**。在 432MB 余量上塞任何 LLM（哪怕 0.5B 量化也要 ~500MB+）都会挤爆总线进程 → 反而破坏永续。**明确否决（除非未来服务器升配）。**
3. 若将来需要"mac-mini 全挂时的最后应答兜底"，正确方案是**云函数/轻脚本自动 ACK**（无 LLM：收到消息→自动回"mac 离线，已留痕，恢复后处理"），由 bus-bridge 或 bb-sub 实现，内存占用 <50MB。

### 2.3 服务器最小依赖清单（维持现状即可，不新增）

- rust-blackboard ×2（8792 主 + 8794 测试）≈ 92MB —— 已有
- node bus-bridge（8791）≈ 已有
- bb-sub ×8（服务器留痕）≈ 已有
- **不新增任何推理/桌面组件**

---

## 三、实施步骤 S1–S5（每步含改动文件 + 验证，防上下文丢失）

### S1 修唤醒断点（当前缺口 · 最高优先）

**问题**：central-inbox 用会话 id 匹配 `to` 中文角色名（星桥/明鉴），无映射表 → not-found 24 次 → 回退中枢副本 → 本机在线会话收不到。

**改动**：
- 文件：`~/dsh-plugin-central-inbox/lib/index.js`（或 `~/dsh-collab/sb-mobile/central-inbox-v2/lib/index.js` 部署）
- 内容：加角色名→id 映射表（数据源 `~/.dsh/agent-bus.json` profiles 的 role+agentId，或硬编码白名单），resolveTargetId 匹配顺序：精确 id → 稳定片段 → **角色名** → 回退中枢
- 沙箱：先在 /tmp 副本改 → node --check 语法 → 再部署 → 重启插件

**验证**：
- `to=星桥` 的测试卡 → 注入 session-fa1f9150（本机在线）非中枢副本
- coordinator inbox 不再增长（消费闭环）
- 实测：写黑板一条 to=明鉴 → 明鉴被唤醒

### S2 服务器信封路由

**改动**：xingqiao bus-bridge（8791）加 `/bus/send` 信封（to/from/msgid）+ 每设备 outbox + SSE 推送。复用 comm-bus-bridge.service。
**验证**：curl 服务器发 `{to:"mac-mini/星桥"}` → outbox 有该消息 → SSE 订阅端收到。

### S3 送达保证（ACK/重试/死信）

**改动**：设备守护收到→ACK 清队；outbox 超时重试×3；尽→死信写黑板 data/ops/deadletter/<date>（不再静默堆积）。
**验证**：人为停 mac-mini 守护 60s → 消息入 outbox → 恢复后补投 → 死信仅当重试尽。

### S4 全设备守护统一

**改动**：MBP/i9/mac-mini 各跑同一守护（订阅服务器 SSE + 本地 agent_wake + ACK），替换各自 node-bridge/hb-fwd 消息段。守护脚本 `~/dsh-collab/comm-server/device-daemon.py`（单文件，env 配置节点）。
**验证**：三设备各发一条互达，全程无人工。

### S5 星台 App 接入信封

**改动**：`~/sb-mobile/server.js` /api/chat 改走服务器信封（to=星桥 显式），而非本机 inbox 隐含。
**验证**：手机发消息 → 中枢路由 → 星桥唤醒回复 → 手机收到。

---

## 四、风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| central-inbox 改动崩唤醒 | /tmp 沙箱验证语法 + 备份 .bak | 恢复备份重启 |
| 信封协议不兼容旧端 | 双写兼容期（信封+旧键并存一周） | 停用信封 |
| 守护抢占 | 每设备幂等锁（agent_light） | kill 守护 |

---

## 五、验收清单（R030：无验证不陈述）

- [ ] MBP 外网发消息 → mac-mini 星桥自动唤醒并回复，全程无用户传话
- [ ] i9 发消息 → 同链路
- [ ] 服务器重启 / mac-mini 重启 → outbox 不丢，恢复补投
- [ ] coordinator inbox 不再无界堆积（死信有告警）
- [ ] 手机星台对话仍正常（S5 回归）
- [ ] 本机 agent 间通讯（L0）未受影响（仍本地，无服务器依赖）

---

## 六、分工

- 星桥（本会话）：S1-S5 主理 + 服务器/守护改动 + 实测验收
- 明鉴：架构评审 + SystemGraph 侧自检集成（S2 信封后蓝图登记走信封可选）
- 守灯/守望：S3 死信告警对接 + 重启窗口
- 数据调查员：若需跨设备压测辅助

---
*星桥 2026-09-08 v2 · 用户批准 · 每步落盘防上下文丢失*

---

## 三之二、S2 实测进展与设计决策（2026-09-08 星桥）

### 侦察结论（服务器 bus-bridge 已具备信封全部端点）
- xingqiao:8791 bus-bridge 端点齐全：POST /bus/send{from,target,action,payload,ttl_sec} / GET /bus/receive?target= / POST /bus/reply / GET /bus/outbox / GET /bus/status
- 实测闭环通过：send→queued→receive 取到任务（task cfda2156）✅
- 鉴权：X-Webhook-Token 头（服务器 token 已取，勿黑板明文）
- 无 SSE（轮询模型）；队列目录 /opt/comm-layer/bus-queue/{tasks,outbox}

### 架构决策（避免做错方向）
1. **服务器队列 = 跨设备信封权威**：MBP/i9 客户端 + mac-mini 守护都连 xingqiao:8791，不再各自为政
2. **mac-mini 守护（新写 device-daemon.py）= 桥**：轮询 receive target=mac-mini → 解析信封 payload → 转写黑板 notes/... → central-inbox 角色映射唤醒对应 agent → 处理后 reply 回服务器 outbox
3. **本机 8791 保留**：mac 内部工具/驿使外链继续用（不动）
4. **target 约定**：mac-mini 内 agent 用角色名（明鉴/守灯...），跨设备用 device 名（mbp/i9）
5. S3（ACK/死信）在守护内实现：receive 成功→reply(ok) 清队；超时重试→死信黑板

### S2 改动清单
- [ ] 新写 ~/dsh-collab/comm-server/device-daemon.py（mac-mini 守护：轮询服务器 bus + 黑板转写）
- [ ] launchd 常驻（com.dsh.comm-device-daemon.plist）
- [ ] 服务器 bus token 入 ~/.dsh/bus-bridge-token（0600）
- [ ] 端到端实测：MBP/模拟 send → mac-mini 星桥被唤醒
