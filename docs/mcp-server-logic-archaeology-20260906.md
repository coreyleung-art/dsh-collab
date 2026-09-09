# MCP 服务器逻辑 · 历次思考考古报告

> 考古: 明鉴 v3 (a190c54c) · 2026-09-06 · 用户指示「考古查一下之前所有关于 mcp 服务器逻辑的思考」
> 方法: 全库检索 docs/research/黑板台账/archives, 按时间线归并

---

## 时间线总览(MCP 服务器逻辑的 7 条演进线)

| # | 演进线 | 主理 | 时间 | 核心 | 落点 |
|---|--------|------|------|------|------|
| 1 | external-link-mcp(外链通道 MCP 化) | 驿使 92623479 | 08-17 | 企微/飞书/钉钉统一出向+入向路由, 跨设备共享通道 | external-link-mcp-plan.md + :8910 SSE |
| 2 | 黑板 MCP 化(blackboard-mcp) | 星桥 | 08-29 | 黑板(消息总线)+桥(通讯)暴露为标准 MCP, 任意设备接入成节点 | docs/blackboard-mcp-server-design-v1.md |
| 3 | rust-blackboard-mcp v0.7.0 | 星桥/工具域 | 08-29+ | Rust 全栈 10 工具: 黑板7(bb_read/write/publish/subscribe+node3)+特征库2+治理1 | ~/dsh-collab/rust-blackboard-mcp · SSE 8810 |
| 4 | node.bootstrap 节点自举 | HR/驿使 | 08-22 | MCP 客户端连后调 node.bootstrap → 入职包 → 自动注册+心跳 | mcp-server-node-bootstrap-spec-v1.0.md |
| 5 | mcp-station 挂载管理 | GUI 插件域 1e54d56d | 持续 | MCP 服务器 stdio/HTTP 挂载统一管理 | 插件 mcp-station |
| 6 | bus-bridge 消息总线 MCP 集成 | 驿使/星桥 | 08-18 | bus.send/outbox MCP 工具, 跨设备消息(8791) | external-link-mcp v0.3 + bus-bridge |
| 7 | MCP 网络推进台账 | HR 驾驶舱 a17a52f8 | 08-18 | 各 MCP 组件状态/缺口/推进分级(P0-P2) | mcp-network-progress.md |

---

## 关键设计逻辑要点

### A. blackboard-mcp(星桥设计 v1.0 — 最完整的服务器逻辑蓝图)
- **动机**: 完全解耦 → 桥/黑板独立进程 → MCP 化 → 任意支持 MCP 客户端(Claude/IDE/自研/手机)授权接入
- **传输双轨**: stdio(本地) + SSE(远程经 Tailscale); REST 8792 与 SSE 8803 分离
- **⚠️ 踩坑**(08-30): MCP SSE 线程误连 8792(REST)致推送永不来 → 每端口独立常量 BB/BB_SSE; stdout 锁死锁 → 写时短暂 lock
- **Tools**: bb_read/write/subscribe/publish + node_register/heartbeat/list
- **协议**: MCP JSON-RPC 2.0(initialize/tools/list/tools/call)
- **授权**: node_register→token→Bearer→认证中间件(v0.6.5)+topic 白名单
- **拟规则**: R017「MCP 开放接入」(未入账, 后被 R-ERR/comm 体系吸收?)

### B. external-link-mcp(驿使 — 外链出向/入向路由)
- 现成方案盘点(mcp-notify 等只出向) → 自建补 80% 缺口: 入向接收/统一路由/跨设备共享/DSH 集成
- 分级策略 P0-P3 + bus-bridge 集成 + P3 拦截

### C. rust-blackboard-mcp v0.7.0(Rust 全栈实现)
- 黑板 7: bb_read/write/publish/subscribe + node 3
- 特征库 2: feature_search/stats(Python feature-mcp 已退役, Rust 接管)
- 消息治理 1: queue_condense
- SSE 8810 常驻; GitHub Release 分发(mac-arm64)

### D. node.bootstrap(节点自举 — 面向任意设备)
- 客户端连 → node.bootstrap → 入职包(node_id/角色/黑板地址/角色目录) → 自动注册+心跳 → node-join-notify → 零手动配置
- 目标服务器 external-link-mcp :8910

### E. 架构层级关系(从考古归纳)
```
MCP 客户端(Claude/IDE/DSH agent/手机/任意设备)
    ↓ MCP JSON-RPC(stdio/SSE) + token
MCP 服务器层:
  ├ blackboard-mcp(黑板 7+node 3) — 数据/消息/节点
  ├ external-link-mcp(通道+路由+bus) — 外链/跨设备
  ├ rust-blackboard-mcp v0.7(合并接管) — Rust 全栈
  └ mcp-station(挂载管理)
    ↓ 后端
黑板 REST 8792 / SSE 8803 / bus-bridge 8791 / 通道(企微飞书) / 中枢(comm-server 8792)
```

---

## 与当前架构的衔接(2026-09-06 视角)
- comm-layer 服务器化(Step 1-2 完成)已含 feature-mcp 8811 暂缓(数据源绑本机) — 对应 C 的本地部署决策
- E2 全局注册表(R-ERR4) = node_register/heartbeat/list 逻辑的服务器化实现(原 blackboard-mcp node 3 工具语义)
- bus-bridge 服务器版(8791 公网) = 6 的服务器化
- onboard 接入页(免 token 指引) = D 自举思想的轻量落地
- MCP 化主线的 3 个成熟方向: 黑板服务/外链通道/节点接入 — 均已演进为 comm 体系组件

## 待归档/衔接线索
- R017「MCP 开放接入」提案未正式入账(需查规则账本是否已并入 R-ERR/comm 条款)
- mcp-station 插件域与 comm-layer 的关系待梳理(未在迁移计划内)

---
*考古报告 v1 · 明鉴 v3 · 2026-09-06 · 全库检索归档*
