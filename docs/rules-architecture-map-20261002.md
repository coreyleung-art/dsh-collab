# 规则 ↔ 通讯架构 关系逻辑图（2026-10-02 重新梳理）

> 目的：回答「每条规则约束架构的哪个节点/哪条边，每个架构节点由哪些规则覆盖，哪里有空白」。
> 输入：RULES.md R001–R036（主账）+ R-ERR 防复发系列（rules.json）+ INVARIANTS I1–I7 + 通道规则 v2 + 降级纪律 v1 + R006 四工具。
> 状态：主账 R036 已含通道变更治理门；本图是「规则×架构」的覆盖矩阵，含 gap 清单。

## 1. 架构分层与规则附着（一图）

```mermaid
flowchart TB
  subgraph ARCH["通讯架构实体（v3 实测基线）"]
    SES["会话层<br/>星桥·明鉴·HR…·MBP 会话"]
    L0["L0 agent-bus<br/>进程内总线"]
    L1["L1 本机黑板<br/>127.0.0.1:8792"]
    DM["守护层<br/>node-bridge·bb-sub·central-inbox<br/>device-daemon·hb-fwd·sync"]
    L2["L2 服务器<br/>8792黑板·8791bus·8803SSE·E2注册"]
    L3["L3 Tailscale·Funnel"]
    SES -->|agent_send/threads| L0
    L0 -->|落盘兜底| L1
    DM -->|读写/订阅| L1
    L1 <-->|镜像/注册/信封| L2
    L2 <-->|直连/公网| L3
  end
  subgraph RG["规则附着（谁约束谁）"]
    R9["R009 角色命名<br/>R001 红绿灯<br/>发送纪律 v2.4"]
    R2["R002 通道分级<br/>I1–I7 不变量<br/>R036 变更门"]
    R3["R003 写板规范<br/>I5 原子写<br/>drift-scan 矩阵"]
    R4["R004 注入目标·R005 CCEP<br/>R014 自查门·R035 热重启<br/>R034 探照灯·降级纪律 v1<br/>R036+launchd-scan"]
    R5["R-ERR4 注册表<br/>R033 通道治理<br/>R036 bus 白名单<br/>hb-fwd G5 活性判定"]
    R6["R031 通讯永续（部分）<br/>⚠️ 无专门规则"]
  end
  subgraph VFY["验证层（机械检查）"]
    V1["convention-lean4-check<br/>G-C1…C44"]
    V2["comm-invariant-audit<br/>I1–I7 矩阵"]
    V3["post-restart-acceptance 7 项"]
    V4["四工具 --lean4-check<br/>+ --selfcheck"]
  end
  R9 -.-> SES
  R2 -.-> L0
  R3 -.-> L1
  R4 -.-> DM
  R5 -.-> L2
  R6 -.-> L3
  V1 -.->|公约接入自动跑| ARCH
  V2 -.->|身份不变量审计| L0
  V3 -.->|重启后验收| ARCH
  V4 -.->|交付前自证| ARCH
```

## 2. 覆盖矩阵（规则 → 架构节点 → 检查器）

| 规则 | 约束对象 | 架构节点/边 | 机械检查器 | 状态 |
|---|---|---|---|---|
| I1–I7 不变量 | 消息身份/回执/原子写/注入语义 | L0 agent-bus | comm-invariant-audit + selftest 65 条 | ✅ |
| R001 红绿灯 | 会话间同源操作 | 会话层 | agent-bus 实现（agent_light/lock） | ✅ |
| R002 通道分级 | 消息通道选择 | 会话→L0 边 | 无独立检查器（纪律+去重） | ⚠️ 靠自觉 |
| R003 写板规范 | 黑板写入 | L1 | 无（靠 bb-card-send G4 key 语法门） | ⚠️ 部分 |
| R004/R005 | 注入目标/心跳协议 | 守护层 | convention G-C 族 | ✅ |
| R-ERR4 | E2 注册表写入权 | L2 注册键 | hb-fwd 实现 | ✅ |
| R006 | 工具化标准 | 全部工具 | 各工具 --lean4-check | ✅（4 工具达标） |
| R014 | 插件自查门 | 插件 | selfcheck CLI | ✅ |
| R030 | 无验证不陈述 | 全局 | 各工具回读断言 | ✅ |
| R031 | 通讯永续/本地优先 | L0–L3 全链路 | 无独立检查器 | ⚠️ 靠架构 |
| R033 | 通道治理 | L2 | convention G-C 族 | ✅ |
| R034 | 探照灯活性 | 守护层 | G5 判定 + hb_age_s | ✅ |
| R035 | 热重启优先 | 守护/框架 | cldvoice-activate 门 | ✅ |
| **R036** | **通道变更治理门** | **全部通道** | **G-C43 channel-gate + G-C44 drift-scan** | ✅ 今日新增 |
| 降级纪律 v1 | 服务器故障时行为 | L2 故障面 | 无机械检查（纪律+求救通道） | ⚠️ 纪律 |
| 通道规则 v2 | 矩阵+变更语义 | 全部通道 | channel-gate + drift-scan | ✅（门已结构） |
| 发送纪律 v2.4 | 全文发送拦截 | agent-way 工具 | 工具内闸门 | ⚠️ 未入规则账本 |

## 3. Gap 清单（无覆盖/弱覆盖，按优先级）

1. **L3 Tailscale/Funnel 无专门规则**：只有 R031 提及。通道矩阵 v2 已把它列为通道，但无「L3 故障/降级」规则（现状依赖「服务器兜底」的隐式假设）。
2. **发送侧门禁未入账**：agent-way 的 v2.4 全文拦截（>50 字需先写黑板）是强闸门但无规则编号——建议并入 R002 详情或独立条目。
3. **D8 版本注册无规则**：E2 schema v2 services 版本字段（node-kit 方案）未落地 → 无「组件版本可远程核」的规则约束。
4. **R002/R003/降级纪律缺机械检查器**：三条靠纪律自觉，与 R036「结构门」标准不一致——补课方向：bb-card-send 已覆盖 R003 的 key 门，R002/降级纪律可参照 R036 模式工具化。
5. **SSE 真探测技术债务**：drift-scan 的 sse-8803 用键 ts 等价判活（node 环境 curl 对 SSE 流超时），矩阵已留 note，待修。
