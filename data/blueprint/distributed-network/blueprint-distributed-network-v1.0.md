# blueprint:distributed-network · 跨设备分布式智能体节点网络 · v1.1

> 明鉴 v3 · 2026-09-09 · 三件套纪律 · +P5 通讯治理（永续通讯里程碑同步）
> 依据：docs/distributed-network-relationship-analysis.md + devices/（设备资产/接入模板）+ cross-device-bridge-postmortem
> ⚠️ 定位：agent-network 的**物理传输实现层**——接口（消息怎么通信）在 agent-network，实现在此（消息跨设备到达哪台机器）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | distributed-network |
| name | 跨设备分布式智能体节点网络 |
| version | v1.1 |
| dim | 底座 |
| mainlines | {"node-net": {"desc": "节点网络：4 设备拓扑 + Tailscale + 设备资产", "name": "节点网络"}, "bridge": {"desc": "桥接层：node-bridge/总线桥/黑板桥/事件桥/SSE", "name": "桥接层"}, "edge": {"desc": "端侧节点：i9/MBP node-agent + 接入模板", "name": "端侧节点"}, "remote": {"desc": "远程通道：向日葵 MCP/SSH/tailnet proxy", "name": "远程通道"}, "health": {"desc": "设备健康：探测/算力调度/恢复", "name": "设备健康"}, "comm-gov": {"desc": "通讯治理：守护SSE推送/central-inbox角色映射/送达保证/公约Lean4门(R033/R034)", "name": "通讯治理"}} |
| gate | ① 逻辑语义遵循 agent-network(bus/fnp) ② 通道迭代走 CCEP ③ 端侧接入走接入模板 ④ 设备变更登记设备资产表 ⑤ 远程操作遵 R027 人控 |
| status | active |
| ts | 2026-09-09 |

## 一、主线

- **node-net**：节点网络 — 4 设备拓扑(mac-mini宿主/MBP/i9/iPhone) + Tailscale + 设备资产表
- **bridge**：桥接层 — node-bridge v1.0/总线桥8791/黑板桥/事件桥8803/SSE8910
- **edge**：端侧节点 — i9 node-agent + MBP node-agent + 接入模板/preset（新设备即插即用）
- **remote**：远程通道 — 向日葵 MCP(22工具) + SSH + tailnet proxy + 外链
- **health**：设备健康 — 在线探测/算力调度/任务路由/恢复（衔接罗盘）
- **comm-gov**：通讯治理 — 守护SSE推送/central-inbox角色映射/送达保证S3/CLD公约Lean4门(R033/R034)

## 二、阶段与子阶段

### P0 节点网络 [done]
- dn1-1 4 设备组网 [done] — mac-mini/MBP/i9 Tailscale 100.x 全在线
- dn1-2 设备资产表 [done] — device-assets.md 罗盘维护（权威登记）

### P1 桥接层 [done]
- dn2-1 node-bridge [done] — 协议 v1.0 rust 实现（i9/mbp 节点桥）
- dn2-2 总线桥+事件桥 [done] — 总线桥8791/事件桥8803/SSE8910 全运行
- dn2-3 黑板桥 [done] — 黑板跨设备共享 8792

### P2 端侧节点 [active]
- dn3-1 i9 node-agent [done] — i9-node-agent.py + preset
- dn3-2 MBP node-agent [done] — mbp-node-agent.py + preset
- dn3-3 接入模板标准化 [todo] — node 接入模板/任命提示词（新设备即插即用）

### P3 远程通道 [active]
- dn4-1 向日葵 MCP [done] — 22 工具 device_search/info/wakeup/control
- dn4-2 tailnet proxy+SSH [active] — 3081 代理 + SSH 备选

### P4 设备健康 [todo]
- dn5-1 健康探测 [todo] — 在线/负载/告警（守望/罗盘协作）
- dn5-2 算力调度 [todo] — 任务-算力匹配（渲染/训练/批处理→空闲设备）

### P5 通讯治理 [active]（永续通讯里程碑 2026-09-08/09）
- dn6-1 守护 SSE 推送 [done] — device-daemon 三端常驻 /bus/events 免轮询 25s 心跳(09-08)
- dn6-2 送达保证 S3 [done] — 黑板写失败重试×2 + 死信告警 data/ops/deadletter/(09-08)
- dn6-3 central-inbox 角色映射 [done] — S1 精确唤醒 agent-role-map.json 20 角色(09-01起/09-09验收)
- dn6-4 CLD 节点网络公约 v1 [done] — Lean4 校验 convention-lean4-check.py 10/10 PASS(09-09)
- dn6-5 R033/R034 生效 [done] — 通道治理+探照灯送达入 RULES.md 78 条(09-09 用户 GUI 批准)

## 三、relations

- **child_of**: agent-network（接口在 agent-network，实现在此）
- **depends_on**: agent-network（bus/fnp 语义）
- **references**: rule-judge / flowernet-platform
- **manages**: blueprint-platform
- 反向：agent-network references（an4-2 承接）

---
*blueprint:distributed-network v1.1 · 明鉴 v3 · 2026-09-09 · BP-9 标准格式 + P5 通讯治理*
