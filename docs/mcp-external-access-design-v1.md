# MCP 外部接入层设计 v1.0（Comm 架构版 blackboard-mcp）

> 明鉴 v3 · 2026-09-06 · 用户指示「先完成设计方案和架构图」
> 依据: docs/mcp-server-logic-archaeology-20260906.md(考古) + docs/mcp-comm-mapping-eval-20260906.md(映射评估)
> 定位: 评估方案 S3 —— 任意支持 MCP 的客户端(Claude Desktop/IDE/第三方 agent/手机)经 E2 注册 + 授权接入 comm 通讯架构, 成为外部节点
> 状态: 设计 v1.0 · 待用户评审

---

## 〇、设计原则(承接治理哲学)

- **Φ9 约束前置**: 接入即受身份/授权/白名单门约束, 不可绕过
- **R030 无验证成功=未成功**: 每阶段接入后实测验证
- **R-ERR4 单源**: 节点身份以 E2 注册表为唯一事实源(不另造身份)
- **读写分离**: 读公开(注册表查询)/写需 token(黑板写)
- **复用不重建**: 复用黑板 API/SSE/bus-bridge/E2, 不复制旧 blackboard-mcp 私有栈

## 一、目标与范围

### 目标
任意 MCP 客户端零开发接入 comm 架构: 经标准 MCP 协议读黑板/发消息/订阅事件/查节点, 成为分布式协作节点(24h 服务器可达)。

### 非目标(明确不做)
- ❌ 不做消息路由中枢(域自治 + bus 兜底, 评估已否决 SPOF 方案)
- ❌ 不迁移 mcp-station(留本机作管理面)
- ❌ 不迁移 feature-mcp(数据源绑本机)

## 二、分层架构

```
┌─────────────────────────────────────────────────────────┐
│  外部 MCP 客户端层                                        │
│  Claude Desktop / Cursor / VS Code / 自研 agent / 手机   │
└──────────────┬──────────────────────────────────────────┘
               │ MCP JSON-RPC 2.0 (stdio 本地 / SSE 远程)
┌──────────────▼──────────────────────────────────────────┐
│  MCP 接入层 (comm-mcp-server)  ← 本设计核心              │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 协议面: JSON-RPC2 (initialize/tools/list/call)    │  │
│  │ 鉴权面: Bearer token → E2 注册校验 → 会话          │  │
│  │ 工具面(白名单映射到 comm 层):                     │  │
│  │   bb_read      → 黑板 GET /<key>                  │  │
│  │   bb_write     → 黑板 PUT /<key> (需写权 token)    │  │
│  │   bb_subscribe → SSE 8803 事件(角色域白名单)       │  │
│  │   bus_send     → bus-bridge 8791 (任务入队)        │  │
│  │   node_whoami  → E2 data/discovery 查自己          │  │
│  │   node_list    → E2 查在线节点(读公开)             │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────┘
               │ 内部调用(本机/服务器, 非 MCP)
┌──────────────▼──────────────────────────────────────────┐
│  Comm 通讯层 (xingqiao 服务器 /opt/comm-layer)           │
│  Prod 黑板 8792 · SSE 8803 · bus-bridge 8791 · E2 注册表 │
│  bb-sub×8 · Test 黑板 8794 隔离验证                       │
└─────────────────────────────────────────────────────────┘
```

### 部署位置
- **comm-mcp-server**: 服务器 xingqiao(/opt/comm-layer/mcp-server/) 或 mac-mini 本机(首版)
  - 服务器版: 外部设备直达(24h 可达), 与中枢同机延迟低
  - 首版建议 mac-mini(复用现有 MCP 栈) → 稳定后迁服务器
- 复用现有: blackboard-mcp v0.7.0 二进制逻辑 + rust-blackboard-mcp 工具面

## 三、MCP 工具面(白名单映射)

| Tool | MCP 语义 | Comm 后端 | 授权 |
|------|---------|----------|------|
| `bb_read` | 读黑板 KV | 黑板 GET /<key> | 任意已注册节点(读公开) |
| `bb_write` | 写黑板 | 黑板 PUT /<key> | token + 写权(角色域) |
| `bb_subscribe` | 订阅事件 | SSE 8803 topic 订阅 | token + topic 白名单 |
| `bus_send` | 发消息/任务 | bus-bridge POST /bus/send | token(R-ERR2 目标域) |
| `node_whoami` | 查自身注册 | E2 data/discovery/agents/<dev> | token |
| `node_list` | 列在线节点 | E2 + G5 活性判定 | 读公开 |

### 工具 schema(示例)
```json
{ "name": "bb_write", "description": "写黑板 KV(data/notes/tasks 域)",
  "inputSchema": { "type": "object", "properties": {
     "key": {"type":"string"}, "value": {"type":"object"},
     "domain": {"enum":["data","notes","tasks"]} },
    "required": ["key","value"] } }
```

## 四、接入流程(新设备 onboarding)

```
1. 设备/客户端 → GET xingqiao:8791/bus/onboard (公开指引, 免 token)
2. 管理端或自助: node_register → E2 注册 {device, role} → 得 {device_id, token}
   (E2 schema v1 + R-ERR4: 写入方=心跳代理/注册器)
3. MCP client 配置: server URL + Authorization: Bearer <token>
4. 首次连接: initialize → 鉴权校验(E2 存在 + token 有效)
5. node_heartbeat 启动(30s) → E2 显示 online(G5 <90s)
6. 工具可用: bb_read/bb_write(域内)/bus_send/subscribe
7. 接入完成 = 成为 comm 分布式节点(黑板上心跳镜像, 他端可见)
```

## 五、鉴权与安全(Φ9 约束门)

| 层 | 约束 | 实现 |
|----|------|------|
| 身份 | 必须 E2 已注册(device_id 真实) | 服务器查 data/discovery/agents/ |
| 传输 | Bearer token 每请求 | 黑板认证中间件(v0.6.5 Bearer 复用) |
| 写权 | token 关联角色域(R-ERR2 域规范) | bb_write 仅允许该角色 notes/<域>/ |
| 订阅 | topic 白名单 | bb_subscribe 拒绝未授权前缀 |
| 隔离 | Test 黑板 8794 供新版本验证 | 升级先 Test 24h |

### 越权路径 & 拒绝(Lean4 门思路)
| 不该发生 | 门 |
|---------|-----|
| 幽灵 device 接入 | E2 查无 → 拒(401) |
| 写他角色域 | 域白名单 → 拒(403) |
| 无 token 写 | Bearer 缺 → 拒(401) |
| 订阅未授权 topic | 前缀白名单 → 拒 |

## 六、与现有规则/机制对齐

| 规则 | 对齐方式 |
|------|---------|
| R-ERR4(E2) | node 身份单源; 接入=注册先于使用 |
| R-ERR2(域规范) | bb_write/bus_send 目标域 = 角色授权域 |
| R001 红绿灯 | mcp-server 写共享资源前查灯 |
| R006#10 | comm-mcp-server 自带 --lean4-check(违规路径拒实证) |
| J25 | 外部 client 配置不写 ~/.claude.json(经 mcp-station 或独立配置) |
| R020 | 本设计即新工具 → 蓝图落点见 §八 |

## 七、分阶段实施(每阶段验证后确认)

| 阶段 | 内容 | 验证(R030) | 依赖 |
|------|------|-----------|------|
| P0 | comm-mcp-server 骨架: JSON-RPC + bb_read/node_list(只读) | Claude 客户端本地连 → node_list 返回 E2 三端 | 服务器 MCP 栈复用 |
| P1 | + 鉴权(Bearer/E2 校验) + bb_write(域白名单) | 错 token 401 / 越域 403 实测 | E2 完成 ✅ |
| P2 | + bb_subscribe(SSE 白名单) + bus_send | 订阅事件实时收 / 任务入队 | bus-bridge 8791 ✅ |
| P3 | onboarding 自助注册(新设备 node_register) | 手机/新机全流程接入 | R-ERR4 ✅ |
| P4 | 迁服务器 /opt/comm-layer + 文档 | 公网设备接入实测 | Step 4 外链窗口 |

## 八、蓝图落点(SystemGraph/agent-network)

- **agent-network 蓝图**: 新增主线候选 mcp-access(外部 MCP 接入层) 或 comm-server 附注 —— cs4 后节点, works mcp-a0~mcp-a4 对应 P0-P4
- **SystemGraph 资产图**: +"MCP 外部接入层(comm-mcp-server)" 资产归 xingqiao; 物理层标注
- **规则**: R-MCP1(或并入 R-ERR) — 任意外部 MCP 客户端接入规范(草案见评估方案 §3.1), 走 R008

## 九、风险与门

| 风险 | 缓解 |
|------|------|
| 外部设备写入污染 | 域白名单 + R-ERR2 + 写审计(黑板留痕) |
| token 泄露 | 每设备独立 token + 可单吊销 + 0600 存储 |
| 服务器不可达 | 客户端本地缓存 + 断线重连(复用 SSE 机制) |
| 范围膨胀 | P0 只读先行验证价值, 逐步加写权 |
| MCP 协议版本漂移 | 锁定 JSON-RPC 2.0 + tools/list 动态发现 |

## 十、待用户确认(设计评审点)
1. 首版部署 mac-mini 后迁服务器, 还是直接服务器? 
2. P0 只读先行是否合适(先验证外部接入价值)?
3. 是否现在启动 P0(组件骨架 ~1-2h), 还是等 external-link Step 4 一起?
4. 蓝图落点: mcp-access 新主线 vs comm-server 附注?

---

## 附录 A · 完整实施计划（纳入 agent-network 蓝图 mcp-access 主线）

### A1. 蓝图归属
- **蓝图**: agent-network (mcp-access 主线 · comm-server 同域底座性质)
- **works 规划**: mcp-a1 设计定稿(本文档) → mcp-a2 comm-mcp-server 骨架(P0 只读) → mcp-a3 鉴权+写权(P1) → mcp-a4 订阅+bus(P2) → mcp-a5 自助注册(P3) → mcp-a6 迁服务器+文档(P4)
- **owner**: 明鉴(设计/评估) + 星桥(实现, 复用 MCP 栈) · gate: 每阶段 R030 验证

### A2. 里程碑与验收
| 里程碑 | 内容 | 验收 |
|--------|------|------|
| M1 (P0) | JSON-RPC + bb_read/node_list 只读 | 外部客户端 node_list 返回 E2 三端 |
| M2 (P1) | Bearer 鉴权 + bb_write 域白名单 | 401/403 越权实测拒 |
| M3 (P2) | bb_subscribe + bus_send | 订阅实时 + 任务入队 |
| M4 (P3) | onboard 自助 node_register | 新设备全流程接入 |
| M5 (P4) | 迁服务器 + 文档 | 公网设备接入实测 |

### A3. 风险登记
| 风险 | 影响 | 缓解 |
|------|------|------|
| 外部写污染 | 高 | 域白名单 + R-ERR2 + 审计 |
| token 泄露 | 高 | 独立 token + 吊销 + 0600 |
| 协议漂移 | 中 | 锁 JSON-RPC2 + 动态 tools/list |
| 范围膨胀 | 中 | P0 只读先行验证 |

### A4. 依赖与前置
- E2 注册表 ✅(R-ERR4) · bus-bridge ✅ · 黑板认证中间件 ✅ · rust-blackboard-mcp 栈 ✅
- 全部前置已就绪, 可直接启动 P0

---

## 十一、现状核查(2026-09-06 实施前确认)
**栈1 底座已实际运行**: blackboard-mcp v0.8.4(MCP SSE :8810, PID 1120) 已在生产——暴露 bb_read/bb_write/bb_publish 等工具(JSON-RPC2 over SSE)。即栈1 通讯层 MCP 无需从零实现, 而是:
1. 复用 v0.8.4 作底座(E2 注册 + 黑板读写 + 发布)
2. 补 gap: 外部设备 onboarding 接入面(P3) + 与 comm 架构的 R-ERR4 注册对齐
3. P0 验证 = 确认 SSE 工具面可达(已实测 initialize + tools/list ✅)

> 结论: 栈1 实施重心从"写 server"转为"接线+补面", 大幅降本

*设计 v1.0 + 计划 A1-A4 + 现状核查 · 明鉴 · 2026-09-06 · 架构图见 mcp-comm-architecture.md*
