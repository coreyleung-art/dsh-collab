# MCP 服务器逻辑 ↔ Comm 架构映射对照 + 评估方案

> 明鉴 v3 · 2026-09-06 · 用户指示: MCP 逻辑与 comm 架构映射 + 查 R017 + 完整评估给星桥
> 关联: docs/mcp-server-logic-archaeology-20260906.md(考古) · comm-server/migration-plan-v1.md · agent-network v1.3

---

## 一、R017「MCP 开放接入」入账状态(查证结论)

**❌ 未入账**：规则账本 RULES.md/rules.json 的 R017 = 「抽象事务图形化表达(visualization)」——
原 blackboard-mcp-server-design-v1.md(08-29 星桥) 提议的 R017「MCP 开放接入」**编号被占、内容未落地**。
MCP 相关实际在账规则仅 3 条:
- J10 向日葵 MCP 会话独占(resource 冲突)
- J25 ~/.claude.json MCP 配置源(mcp-station 统一管理)
- R020 新工具(含 MCP/插件/技能)→ 同步明鉴蓝图闭环

**含义**: MCP 开放接入从未成为正式规则 —— 但 E2 注册表(R-ERR4) 与 comm-layer 实际承载了它的逻辑(见下映射),
规则层缺口 = 建议补新条目(编号需重排, 不能占 R017)。

## 二、MCP 逻辑 ↔ Comm 架构映射对照表

### 2.1 组件映射(考古 7 线 → comm 现架构)

| MCP 逻辑(历史组件) | 原位置/端口 | Comm 架构对应 | 状态 | 映射关系 |
|---|---|---|---|---|
| blackboard-mcp: bb_read/write(黑板 KV) | 8792 | 中枢 Prod 黑板 :8792 | ✅ 服务器化 | 数据面直接承接(comm-server Prod) |
| blackboard-mcp: bb_subscribe(SSE) | 8803 | bb-sub×8 订阅器 SSE :8803 | ✅ comm-layer 9 services | 订阅面增强(8 角色化订阅) |
| blackboard-mcp: bb_publish(发布) | 8792 | bus-bridge 8791(send/publish) | ✅ 服务器版 8791 | 消息面(bus)承接 |
| blackboard-mcp: node_register/heartbeat/list | — | E2 全局注册表 data/discovery(R-ERR4) | ✅ 核心完成 | 节点面承接(node 3 工具语义 = E2) |
| external-link-mcp: channel.send/status | 8910 | Step 4 外链层迁移(待) | ⏳ 迁移排队 | 通道面(企微/飞书)待迁服务器 |
| external-link-mcp: bus.send/outbox | 8791 | bus-bridge 服务器版 | ✅ | 消息面统一 |
| rust-blackboard-mcp v0.7(10 工具) | 8810 | comm-layer bin(dsh-tools) | 🔀 融合 | Rust 二进制 = comm 层运行载体 |
| node.bootstrap(入职自举) | 8910 | E2 端侧注册 + onboard 页 | ✅ 演进 | 自举思想 → R-ERR4 端侧注册 |
| feature-mcp 8811 | 8811 | 暂缓 | ⏸ | 数据源绑本机(chroma+ollama)不可迁 |

### 2.2 功能分层映射(MCP 服务器层 → comm 三层)

```
MCP 时代(08-17~08-29)                 Comm 架构(09-06)
────────────────────                  ─────────────────
MCP 客户端(任意设备)                   三端+任意节点(经 E2 注册)
   ↓ MCP JSON-RPC + token                 ↓ R-ERR4 注册 + 黑板 REST/SSE
MCP 服务器层:                          通讯层(comm-layer 服务器):
  ├ blackboard-mcp(数据/消息/节点)   →  bb-sub×8 + bus-bridge + E2
  ├ external-link-mcp(通道/路由/bus) →  外链层(Step 4 排队) + bus-bridge
  ├ rust-blackboard-mcp(10 工具)     →  comm-layer bin(dsh-tools)
  └ mcp-station(挂载)                →  (管理面未迁移, 留本机)
后端: 黑板8792/SSE8803/bus8791/通道     中枢: Prod黑板+Test黑板+comm-layer
```

### 2.3 核心洞察(映射揭示)
1. **MCP 时代的"服务器=工具进程" → comm 时代"服务器=通讯中枢"**：MCP 是单机能力暴露协议, comm 是跨设备通讯架构——两者是"接口协议"与"部署架构"的关系, 不冲突而是演进
2. **node 3 工具(E2)已独立成 R-ERR4 规则**：MCP 里 node_register/list 只是工具, comm 里升级为带规则的注册表(R-ERR4)——治理升级
3. **真正未迁移的 MCP 面**: mcp-station(管理) + external-link 通道(Step 4 排队) + feature-mcp(暂缓) — 三者都有明确原因
4. **MCP 协议本身仍是未来接入方式**: 任意第三方设备(Claude/IDE/手机)经 MCP 接入 comm 架构 = blackboard-mcp 原始愿景的 comm 版实现(经 E2 注册+黑板 API), 建议保留 MCP server 作为外部接入层

## 三、评估方案(补充给星桥)

### 3.1 规则层补口(R017 空缺)
**建议**: 新增 R-MCP1「外部 MCP 客户端接入规范」或并入 R-ERR 族——任意外部 MCP 客户端接入需: ①E2 注册(身份) ②token 授权(黑板 Bearer) ③订阅白名单(topic 级) ④读写分离(读公开/写 token)
- 编号建议: 不占 R017(已用), 走 R-ERR5 或新 R0xx, 由 HR R008 流程裁决

### 3.2 架构层建议(三步)
| 步骤 | 内容 | 归属 |
|---|---|---|
| S1 | external-link 外链层迁服务器(Step 4 执行) — 通道面服务器化收官 | 星桥/驿使 |
| S2 | 保留本机 mcp-station 作为"管理面", 明确其与 comm 层边界(管理工具 vs 通讯通道) | 明鉴/1e54d56d |
| S3 | 若未来需任意设备接入: 起 blackboard-mcp-server(comm 版) 面向 E2 注册+黑板 API, 而非旧私有协议 | 明鉴评估/星桥实现 |

### 3.3 蓝图落点
- agent-network 蓝图: MCP 接入面作为 cs4 后附注或新主线候选(MCP 外部接入层)
- SystemGraph: 若做外部接入, 资产图加 "MCP 外部接入层" 资产(归 xingqiao/comm 层)

### 3.4 待用户/星桥裁决点
1. 外部 MCP 客户端接入是否近期需求?(决定 S3 优先级)
2. R-MCP1/新规则是否走 R008?(补规则层空缺)
3. external-link Step 4 迁移窗口(与 Step 3 灰度衔接)

---
*映射+评估 v1 · 明鉴 v3 · 2026-09-06 · 交星桥评审*
