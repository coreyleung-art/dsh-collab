# 服务器消息分发路由 · 多设备污染隔离设计 v1（2026-09-09 星桥）
> 用户要求根治多设备信息污染：设计服务器上的消息管理/分发路由，做多设备隔离。

## 一、现状污染问题（实测证据）

1. **collab 域噪音灌跨设备**：mac-mini 本机 collab 信息（星桥/明鉴迭代报告等）会经
   relay/同步让 i9/MBP 看到——违反 R-ERR2（给设备走 notes/<dev>/ 域）
2. **无角色级路由**：服务器只懂设备（target=mac-mini/mbp/i9），payload.to 角色名透传
   → 设备守护本地解析 → 设备间不能角色直连
3. **无源审计**：消息从哪来发给谁不可追溯（污染时无法定位）

## 二、根治设计：服务器消息分发路由（comm-router）

### 2.1 分层隔离原则
```
设备内(角色间)     → agent-bus 本地, 永不进服务器        [零 token 零污染]
设备间(节点消息)   → 服务器 bus 信封 notes/<node>/ 域      [按设备隔离]
节点间角色寻址     → 信封 to=role@device 语法, 设备侧解析   [服务器透传+校验]
广播(any)         → 显式+审计, 默认禁                  [防污染扩散]
```

### 2.2 comm-router 职责（服务器上新增/强化）

| 功能 | 实现 | 隔离效果 |
|---|---|---|
| **域边界路由** | 消息按 target 只投目标设备守护；notes/<node>/ 仅该设备可读 | collab 不灌跨设备 |
| **白名单校验** | from 的 device:role 须在信任表(trust-map)；陌生→untrusted/拒 | 防 spoof/伪造源 |
| **hash 去重** | 服务器按 (from,task_id) 去重，防 relay+直发双收 | 消重复处理 |
| **风暴熔断** | 同目标 10min >5 次→死信暂缓 | 防轰炸 |
| **审计日志** | 每信封记 data/registry/comms-route-log/{date}（from/to/ts） | 污染可溯源 |
| **TTL 治理** | 任务 TTL 自动 failed；离线转 notes/<dev>/ 不塞队列 | 防积压 |

### 2.3 角色直连语法（设计）
```
发送: bus/send {from:"mac-mini:星桥", target:"mbp:mbp-bus" 或 "mbp", payload:{...}}
解析: 服务器若见 target 含 ':' → 拆 role@device → 投 device; payload.to=role 原样
     设备守护收信 → 按 payload.to 本地 agent-role-map 唤醒该角色
     若 target 是纯 device → 守护按 payload.to 或缺省 coordinator 唤醒
```

### 2.4 设备守护收信隔离（守护侧配合）
- mac 守护只处理 target=mac-mini（已实现）
- i9 守护只处理 target=i9（已实现）
- relay 只代收显式配置的黑板域设备（RELAY_TARGETS），不再盲收

## 三、实施步骤

- [ ] S-A: comm-router 域边界检查（服务器验证 target 合法设备/role@device，拒绝未知）
- [ ] S-B: 审计日志（每信封写 comms-route-log）
- [ ] S-C: 白名单 trust-map（防 spoof，采纳数据调查员 S1）
- [ ] S-D: hash 去重（采纳 HR G-C15，消 relay/直发双收）
- [ ] S-E: 风暴熔断（采纳 HR G-C13）
- [ ] S-F: collab 域停止灌跨设备（relay/同步边界修正）

## 四、验证
- [ ] mac 内角色互发不进服务器日志（零 token）
- [ ] mac→MBP 信封只 MBP 守护收到，i9 无感知
- [ ] role@device 语法端到端唤醒
- [ ] 伪造 from 被拒；重复信封去重；风暴被熔断
- [ ] comms-route-log 可溯源任一消息

---
*星桥 2026-09-09 · 待用户确认后实施 + 并发起节点级公约签署*
