# HubBridge Server · 跨设备 Agent 注册地节点架构蓝图

> 作者：mac-mini 中枢 ｜ 2026-08-27
> 定位：把「黑板协议（HubBridge）」从「单机常驻」进化为「独立注册地节点」——设备身份、白名单接入、通用安装包、消息路由、计量（未来订阅）。
> 触发：用户指出「独立于每台设备的 MCP 服务器做信息交换注册地节点 + 设备唯一码 + 通用安装包 + 接入白名单 + 未来订阅」。

---

## 〇、背景与问题

### 现状痛点
1. **交付形态错误**：MBP/i9 装插件用「物理复制 + 手改 package.json」——绕过官方 `dsh plugin add`（pnpm 依赖解析 + profile bundles 组合）→ 依赖链不完整、bundle 不生效 → **MBP/i9 无法加载**。我们本机用 `link:` 本地目录（文件全）才可用。
2. **黑板物理依赖单机**：黑板 8792/8803 跑在 mac-mini 上——mac 挂则全断。
3. **无设备身份**：节点名（mac-mini/mbp/i9）可伪造，无加密身份。
4. **无接入控制**：任何节点可写黑板。
5. **无通用安装包**：genebank 分发 tar.gz（手动复制），非 npm 官方安装。

### 目标
把 HubBridge 进化为**独立注册地节点**：
- 设备唯一身份（注册制）
- 白名单接入控制
- 通用安装包（npm + `dsh plugin add` 官方路径）
- 消息路由 + 在线状态
- 计量（为未来订阅/付费铺垫）

---

## 一、参考与调研（可引用/借用）

### 1. A2A over MQTT（EMQX 6.2）—— 注册地节点直接对标
- **来源**：[EMQX 6.2 A2A over MQTT](https://www.emqx.com/zh/blog/emqx-6-2-0-release-notes)
- **核心**：MQTT Broker 内置 **A2A Registry**——智能体发布结构化 **Agent Card** 到发现主题 `$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}` 完成注册
- **可借用**：
  - 事件驱动发现（Agent Card 保留消息 + 上下线实时推送）
  - 在线状态（a2a-status: online/offline/lwt，整合存活检测）
  - 响应主题 + Correlation Data（请求/响应、多轮、任务移交）
  - Schema 校验（不合规 Agent Card 拒绝）
  - 认证与授权统一生效（设备互不知对方地址）
- **映射到我们**：Agent Card ≈ agent_profile 档案 + 设备身份；发现主题 ≈ nodes/<device>/heartbeat + registry

### 2. InterSAGE（DeepKernel Lab）—— 安全可验证互操作协议
- **来源**：[InterSAGE arXiv](https://arxiv.org/html/2608.13030v2)
- **核心**：Internet of Agents 的安全可验证互操作协议（身份验证 + 消息完整性）
- **可借用**：设备间消息的可验证性（签名/哈希链），防止伪造

### 3. Agentic Global Identity Layer
- **来源**：[Agentic-Global-Identity-Layer](https://github.com/MihaiCiprianChezan/Agentic-Global-Identity-Layer)
- **核心**：自主 Agent 的可验证身份（购物理由：agent 代表我们行动时需要身份）
- **可借用**：设备/Agent 身份生成与管理（UUID + 密钥对）

### 4. OSSA Federated Agent Registry
- **来源**：[OSSA federated registry research](https://gitlab.com/blueflyio/ossa/openstandardagents/-/blob/main/docs/research/federatedAgentRegistry.md)
- **核心**：分布式 Agent 注册表联邦（多注册中心互信）
- **可借用**：注册表结构（org/unit/agent 分层）+ 联邦扩展（未来多 HubBridge 互通）

### 5. Red Hat：Securing A2A Communication
- **来源**：[Red Hat securing A2A](https://next.redhat.com/2026/05/13/securing-agent-to-agent-communication/)
- **可借用**：传输安全（TLS/mTLS）、身份验证、授权模型

---

## 二、目标架构

```
┌─────────────────────────────────────────────────────────────┐
│              HubBridge Server（独立注册地节点）                │
│  部署：腾讯云轻量 / CloudBase / 独立容器（不依赖任何单台 CLD）  │
│                                                             │
│  ┌─────────────┬──────────────┬──────────────┬────────────┐ │
│  │ 身份注册层   │  消息路由层   │  设备管理层   │  分发/计量层 │ │
│  │ device-id   │  黑板 KV     │  在线状态    │ npm 安装包  │ │
│  │ + 密钥对    │  + SSE 事件桥 │  a2a-status  │ + token 计量│ │
│  │ 白名单      │  (MQTT 可选)  │  keepalive   │ + 订阅逻辑  │ │
│  └─────────────┴──────────────┴──────────────┴────────────┘ │
│              认证：TLS/mTLS + device token                    │
└─────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │ 注册+认证          │ 消息收发           │ dsh plugin add
  ┌──────┴─────┐       ┌──────┴─────┐       ┌──────┴─────┐
  │ mac-mini   │       │ MBP        │       │ i9         │
  │ device-id  │       │ device-id  │       │ device-id  │
  │ + agent-way│       │ + agent-way│       │ + agent-way│
  └────────────┘       └────────────┘       └────────────┘
```

### 分层设计

| 层 | 职责 | 实现 | 参考 |
|----|------|------|------|
| **身份注册层** | 设备唯一码（UUID+密钥对）、注册、白名单 | device registry（SQLite/JSON） | Agentic Identity / A2A Registry |
| **消息路由层** | 黑板 KV + SSE 事件桥；可选 MQTT | 现有 rust-blackboard + EMQX 可选 | A2A over MQTT |
| **设备管理层** | 在线状态（heartbeat→a2a-status）、keepalive | 现有心跳 + 状态扩展 | EMQX 动态 keepalive |
| **分发/计量层** | npm 安装包（dsh plugin add）+ token 计量 | npm registry + 计量器 | OSSA federated |
| **安全层** | TLS/mTLS + device token 认证 + 消息签名 | 现有 HTTP + 增强 | Red Hat A2A security |

---

## 三、核心机制设计

### 1. 设备身份（每台设备唯一码）
```
注册流程：
  设备装 dsh-plugin-agent-way（npm）→ 首次启动生成 device-id（UUID v4）
  → 生成密钥对（Ed25519）→ 公钥 + 设备信息 POST 到 HubBridge /register
  → 服务器签发 device-token（白名单写入）→ 设备保存 ~/.dsh/hubbridge/identity.json
身份用途：
  · 认证：所有 API 请求带 device-token（Bearer）
  · 消息签名：device 私钥签名消息 → 服务器验证（防伪造）
  · 溯源：消息带 device-id（替代现在可伪造的节点名）
```

### 2. 通用安装包（修复 MBP/i9 根因）
```
路径：npm 发布 dsh-plugin-agent-way（scoped: @coreyleung-art/）
  → 各设备: dsh plugin --profile web add @coreyleung-art/dsh-plugin-agent-way
  → pnpm 依赖解析（peerDeps 完整声明）→ profile bundles 组合 → 官方加载
关键：peerDeps 补全（对照 dsh-agent-teams 16 个写法）——源码用的 10 宿主服务 + 2 client 注入
```

### 3. 白名单接入
```
· HubBridge 配置 allowed-devices（device-id 白名单）或订阅逻辑（未来）
· 未注册设备 → 拒绝连接（401）
· 未来订阅：免费白名单 + 付费通道（设备数/流量/token 计量）
```

### 4. 计量（未来订阅铺垫）
```
· 每设备 token 计量（消息数/字节/LLM 调用）
· 订阅层级：free（N 设备）/ pro（无限制 + 优先路由）
· 支付：腾讯云/CloudBase 上可接（或未来微信支付）
```

---

## 四、部署选项评估（用户问题）

| 部署 | 可行性 | 优点 | 缺点 |
|------|--------|------|------|
| **腾讯云轻量服务器** | ✅ 推荐 | 公网固定 IP、常驻、可跑 docker、成本低（轻量 ¥50-100/月） | 需备案域名/公网安全组 |
| **CloudBase（腾讯云开发）** | ✅ 可行 | Serverless、免运维、云函数+云数据库 | 长连接（WebSocket/MQTT）需额外组件 |
| **独立容器（本机/局域网）** | ✅ 过渡 | 现成（rust-blackboard）零成本 | 依赖 mac-mini 在线 |

**推荐路径**：短期保持 mac-mini 黑板（过渡）→ 中期迁腾讯云轻量（docker 部署 rust-blackboard + 身份层）→ 长期 CloudBase 或轻量+订阅计量。

---

## 五、token 消耗问题（用户问题）

**问：独立服务器后分发是否消耗 token？**
答：**分发（npm 安装包）不消耗 LLM token**——`dsh plugin add` 走 pnpm 拉包，无模型调用。
但**消息处理消耗**：若消息触发 LLM 执行器（node-bridge llm:true）或智能体回复，消耗模型 token。计量层正是为此——把「分发」和「运行」的 token 分开计量。

---

## 六、实施路径（阶段）

### Phase 1（短期）：修复交付形态 —— 插件可独立安装
1. peerDeps 补全（10 宿主服务 + 2 client 注入）
2. npm 发布（scoped）
3. 各设备 `dsh plugin add` 官方安装 → 验证 MBP/i9 可用
4. **验证结论：MBP/i9 之前失败 = 物理复制绕过官方机制（非插件本身问题）**

### Phase 2（中期）：HubBridge Server 独立化
1. 身份层：device-id + 密钥对 + 注册 + token
2. 白名单接入
3. 迁腾讯云轻量（docker 部署）

### Phase 3（长期）：计量与订阅
1. token 计量（消息/流量/LLM）
2. 订阅层级（免费/Pro）
3. 联邦扩展（多 HubBridge 互通，参考 OSSA）

---

## 七、关键技术决策

| 决策 | 选项 | 建议 |
|------|------|------|
| 消息传输 | 现有 HTTP+SSE / MQTT（EMQX） | 过渡用现有；规模大再上 MQTT |
| 设备身份 | UUID+Ed25519 / SPIFFE | UUID+密钥对（轻量，够用） |
| 注册表 | SQLite / JSON / 云数据库 | 过渡 JSON/SQLite；CloudBase 用云 DB |
| 安装包 | npm 公开 / GitHub Packages | npm 公开（dsh plugin add 默认） |
| 计量存储 | 日志 / 数据库 | 数据库（SQLite→云 DB） |
| 部署 | mac 过渡 / 腾讯云轻量 / CloudBase | 见第四节 |

---

## 八、与现有资产的关系

| 现有 | 进化为 |
|------|--------|
| rust-blackboard（8792/8803） | HubBridge Server 核心（消息路由层） |
| node-bridge（心跳/队列） | 设备接入层（注册/在线） |
| dsh-plugin-agent-way | 通用安装包（npm 发布） |
| agent_profile 档案 | Agent Card（A2A 注册表结构） |
| genebank（tar.gz 分发） | npm registry 分发（替代手动复制） |
| verify-watch | 设备在线监控（a2a-status 化） |

---

*本文档基于用户架构设想 + 调研（EMQX A2A / InterSAGE / Agentic Identity / OSSA / Red Hat）沉淀。实施按 Phase 1 → 2 → 3 推进。*
