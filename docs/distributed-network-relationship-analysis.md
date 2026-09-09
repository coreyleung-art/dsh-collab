# Distributed-Network 蓝图 · 关系与边界分析（建蓝图前置）

> 明鉴 v2 · 2026-09-02 · 用户指示：先分析关系再建蓝图
> 核心问题：跨设备分布式节点网络 与 agent-network（底座）是否重叠？

## 〇、结论：不重叠——是「物理传输层」vs「逻辑协作层」

```
┌─────────────────────────────────────────────────┐
│ 逻辑层（agent-network 蓝图）                      │
│   bus 消息层 · fnp 语义层(黑板/事件桥/FNP信封)      │
│   memory · security（协议语义/内容）               │
├─────────────────────────────────────────────────┤
│ ═══════════ 边界：逻辑不管『消息走哪台机器』 ═══════│
├─────────────────────────────────────────────────┤
│ 物理层（distributed-network 蓝图·候选）           │
│   node-bridge 桥 · 总线桥 · 跨设备通道(Tailscale/   │
│   向日葵) · 端侧 agent · 设备资产/健康             │
└─────────────────────────────────────────────────┘
```

- **agent-network**：管「智能体之间怎么通信」（消息格式/黑板语义/红绿灯/内存）——**逻辑契约**
- **distributed-network**：管「消息如何跨设备到达」（哪台机器/什么桥/设备健康/端侧节点）——**物理传输**

## 一、重叠点排查（为什么看似重叠）

| agent-network 内容 | 实际归属 | 判定 |
|-------------------|---------|------|
| fnp 主线「事件桥 SSE」 | 黑板 SSE = 跨设备事件通道 | ⚠️ 语义在 fnp，传输在 distributed |
| an4-2「设备/门店接入标准化」 | agent-network P4 扩展 | ⚠️ 与 distributed 的端侧接入重叠 |
| an0-1 FNP 信封 | 消息格式（逻辑） | ✅ 留 agent-network |
| 红绿灯/内存/监控 | 逻辑治理 | ✅ 留 agent-network |

**裁定**：fnp 的「事件桥 SSE」与 an4-2「设备接入」是**逻辑侧对分布式的要求**；distributed-network 提供**物理实现**——两者是「接口 vs 实现」关系，非重复。

## 二、distributed-network 应含什么（独立蓝图范围）

### 主线候选
1. **node-net**：节点网络 — 4 设备拓扑（mac-mini宿主/MBP/i9/iPhone）+ Tailscale 组网 + 设备资产表
2. **bridge**：桥接层 — node-bridge v1.0 / 总线桥 8791 / 黑板桥 / 事件桥 8803 / SSE 8910
3. **edge**：端侧节点 — i9-node-agent / MBP-node-agent / 接入模板 / preset
4. **remote**：远程通道 — 向日葵 MCP(22工具) / SSH / tailnet proxy 3081 / 外链通道
5. **health**：设备健康 — 在线探测 / 算力调度 / 任务路由 / 恢复（衔接罗盘 5a5368af）

### 已落地证据（全运行）
| 组件 | 状态 | 端口/位置 |
|------|------|----------|
| node-bridge | ✅ rust | 守护 |
| 总线桥 bus-bridge | ✅ | 8791 |
| 黑板桥 | ✅ | 8792 分布式共享 |
| 事件桥 SSE | ✅ | 8803 |
| 黑板 MCP | ✅ | 8810 |
| tailnet proxy | ✅ | 3081 |
| i9/MBP node-agent | ✅ py+preset | devices/ |

## 三、关系网（relations 规划）

```
distributed-network
 ├─ child_of: agent-network      （底座的物理传输实现层）
 ├─ depends_on: agent-network    （遵循 bus/fnp 协议语义）
 ├─ references: flowernet-platform（跨设备存储/黑板）
 ├─ manages: 罗盘设备资产（数据源角色——蓝图管规划，罗盘管运营）
 ├─ references: rule-judge      （跨设备操作验证）
 └─ consumed_by: 驿使外链(SSE通道)/拾光(跨设备发布)
```

**关键反向**：agent-network fnp 的「事件桥 SSE 已有 90%」实际运行在分布式层——此蓝图是把它从「agent-network 一段」独立为「物理层完整蓝图」的自然演进（同 gene-bank 从系统资产升蓝图的逻辑）。

## 四、与知识内核图谱关联

- **溯源报告**：cross-device-bridge-postmortem-20260827（复盘）· hubbridge-protocol-research/architecture/assessment · 通道稳定性评估-20260826 → 均支撑此蓝图
- **原创资产**：node-bridge 协议 v1.0 / 总线桥 / 黑板桥 = 原创（已入 💎 列表候选）

## 五、建议

1. 建 `blueprint:distributed-network`（v1.0，BP-9，child_of agent-network，5 主线）
2. 关系：child_of agent-network + references 罗盘/flowernet-platform/rule-judge + consumed_by 驿使
3. 把 an4-2「设备/门店接入」标为「→ distributed-network 承接」（agent-network 侧标注依赖）
4. 蓝图落盘后 registry/relations/versionlog 登记 + 管理器自动可见

---
*distributed-network 关系分析 · 明鉴 v2 · 2026-09-02*
