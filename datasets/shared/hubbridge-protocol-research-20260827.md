# HubBridge Server · 深度调研与自研协议评估（企业级定位）

> 作者：mac-mini 中枢 ｜ 2026-08-27
> 定位升级：**企业级**（复用到所有门店 + 开放给付费订阅花店商家）——不考虑开发时间成本，产品要完整、稳定、可靠。
> 内容：①genebank 原始设计落差 ②EMQX A2A 深度调研（协议源文件分析）③自研协议可行性评估 ④企业级架构修订。

---

## 一、genebank 原始设计 vs 实际实现（落差确认）

### 原始设计（2026-08-23，远超我认知）
**发现**：`~/dsh-collab/rust-genebank` 是**独立 Rust 项目**（v1.0.0，三平台已编译），有完整的「基因/染色体」隐喻架构：

| 设计要素 | 原始设计 | 实际实现（我用的） |
|---------|---------|------------------|
| 形态 | **独立 Rust 服务器**（genebank-server）| 黑板静态文件区（datasets/shared/）|
| 注册层 | manifest schema（gene_id=内容寻址哈希 / 染色体分类 / 表达谱 / 遗传信息 / 表型）| 无（直接放文件）|
| 存储 | 内容寻址去重（同内容同基因）| 无去重 |
| 检索 | 本地精确 + 本地 bge-m3 语义检索 | 无检索 |
| token | **零 token 设计**（HTTP 字节流 + 规则 manifest + 本地模型门控）| 符合（文件传输天然零 token）|
| API | 与 Python 版一字兼容（/api/v1/genes）| 无 |

### 设计落差确认
**设计意图**：genebank 是**独立的 AI 网盘服务器**（注册层+存储层+检索层，零 token），不是静态文件区。
**实际落地**：退化为「黑板挂载的共享目录」——注册/检索/去重/语义全部没接上。

**用户判断正确**：设计想法与实现有落差。genebank 的独立服务器能力（Rust 三平台产物）**已存在但未启用**。

### 落差的意义（企业级）
genebank 的原始设计**正好是 HubBridge Server 的「分发/资产层」**——内容寻址 + 注册 + 语义检索 + 零 token，本就是为「AI 网盘」设计的独立服务。**应恢复启用 rust-genebank 作为 HubBridge 的资产/分发层**，而非静态文件区。

---

## 二、EMQX A2A 深度调研（协议源文件分析）

### 1. 哪些是标准协议，哪些是 EMQX 自命名

| 名词 | 来源 | 性质 |
|------|------|------|
| **A2A 协议** | [Google A2A](https://deepwiki.com/google/A2A/1.2-agent-discovery)（公开协议，specification/a2a.proto）| **标准公开协议** |
| **Agent Card** | Google A2A 规范（lf.a2a.v1.AgentCard，JSON 文档）| **标准**（机器可读「名片」）|
| **Agent Discovery** | Google A2A 规范（三种机制）| **标准** |
| **A2A over MQTT** | EMQX 6.2 扩展 | **EMQX 自命名/扩展**（A2A 的 MQTT 传输绑定）|
| **a2a-status**（online/offline/lwt）| EMQX 实现 | **EMQX 自命名**（A2A 用户属性扩展）|
| **$a2a/v1/discovery/...** 主题 | EMQX 实现 | **EMQX 自命名**（MQTT 发现主题）|
| **响应主题 + Correlation Data** | MQTT 5.0 标准 + EMQX 应用 | MQTT 标准 |
| **Keep Alive 动态管理** | EMQX 6.2 | EMQX 扩展（$SETOPTS/mqtt/keepalive）|

### 2. A2A 协议核心（Google 规范源）

**Agent Card 结构**（specification/a2a.proto）：
```
lf.a2a.v1.AgentCard
├─ name / description / provider（身份）
├─ interfaces: [{url, protocol_binding(grpc|json-rpc|rest), protocol_version, tenant}]
├─ capabilities: {streaming, pushNotifications, extendedAgentCard}
├─ skills: [{AgentSkill: inputModes, outputModes}]
└─ security: {securitySchemes(OAuth2/APIKey), securityRequirements}
```

**三种发现机制**：
1. **Well-Known URI**：`https://{domain}/.well-known/agent-card.json`（RFC 8615，公共 agent）
2. **Curated Registry**：中心注册表按 skills/tags 查询（企业/市场场景）
3. **Direct Configuration**：直接配置 Agent Card（私有/静态）

### 3. EMQX A2A over MQTT 具体机制
- **发现主题**：`$a2a/v1/discovery/{org_id}/{unit_id}/{agent_id}`（Agent Card 保留消息注册）
- **在线状态**：a2a-status 用户属性（online/offline/lwt——last will testament）
- **交互**：MQTT v5 响应主题 + Correlation Data（请求/响应/流式/多轮/负载均衡/任务移交）
- **Schema 校验**：Agent Card 入注册表前按 A2A 规范校验
- **认证授权**：MQTT 认证（username/password/cert）统一生效
- **治理**：Dashboard / emqx ctl a2a-registry / /api-spec.md

### 4. 能拉回来分析吗？
- **EMQX 是开源**（Apache 2.0）——可下载源码分析 a2a-registry 实现
- **A2A 是 Google 开源**（specification/a2a.proto 在 GitHub）——协议源文件可拉
- 可借鉴其「Agent Card 结构 + 发现机制 + 在线状态」思想

---

## 三、自研协议评估

### 问题：我们是否可以专门写一套自己的协议？重新设计注册机制？

### 答案：可以，且**应该**——但分层决策

| 层 | 自研 or 借鉴 | 理由 |
|----|-------------|------|
| **传输层** | 自研（现有 HTTP+SSE / 可选 MQTT）| 我们已有黑板协议（KV+SSE）验证可用 |
| **注册机制** | **自研**（基于 genebank manifest 思想）| genebank 的「基因/染色体/manifest」是**我们自己的设计**——内容寻址+分类+表达谱，比 Agent Card 更贴合「AI 网盘」场景 |
| **身份层** | 借鉴思想（UUID+密钥对）| 通用需求，无必要发明 |
| **在线状态** | 自研（心跳已有）| 现有心跳 60s + verify-watch，够用 |
| **消息路由** | 自研（黑板 KV+SSE）| 已验证（三端注入/零轮询）|

### 关键洞察：**genebank 的 manifest schema 就是我们的「Agent Card」**
```
我们的 Agent Card = genebank manifest（基因/染色体/表达谱）
  gene_id = sha256（内容寻址——唯一性）
  chromosome = 分类（models/datasets/knowledge/...）
  expression = 能力声明（trainable/inferable）
  heredity = 血缘（依赖/来源）
  phenotype = 表型（实际用法）
```
这比 A2A 的 AgentCard（name/skills/security）**更丰富**——已内置「内容寻址 + 血缘 + 表型」，正是 AI 资产网盘需要的。

### 结论：**自研协议有基础，且不是从零**——genebank manifest 已是我们的协议原型
- 传输层：黑板协议（自研，验证可用）
- 注册层：genebank manifest（自研，已有 schema）
- 身份层：借鉴（UUID+密钥）
- 组合 = HubBridge 协议 v1（自研为主，借鉴思想）

---

## 四、企业级架构修订（定位升级）

### 修订后的 HubBridge Server（企业级）

```
┌─────────────────────────────────────────────────────────────┐
│              HubBridge Server（企业级，独立部署）              │
│  部署：腾讯云轻量/CloudBase（多租户）                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 协议层：HubBridge Protocol v1（自研）                  │  │
│  │  · 注册：genebank manifest（基因/染色体/表达谱）        │  │
│  │  · 身份：device-id + Ed25519 + token                  │  │
│  │  · 消息：黑板 KV + SSE（可选 MQTT 桥）                 │  │
│  │  · 状态：heartbeat + a2a-status 等价（在线/离线/LWT）  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌─────────────┬──────────────┬──────────────┬───────────┐ │
│  │ 身份注册层   │ 消息路由层    │ 资产/分发层   │ 计量/订阅层 │ │
│  │ device 白名单│ 黑板 KV+SSE  │ rust-genebank│ token 计量 │ │
│  │ 多租户隔离   │ (MQTT 可选)  │ (恢复启用)    │ 订阅层级   │ │
│  └─────────────┴──────────────┴──────────────┴───────────┘ │
│  安全：TLS/mTLS + token + 消息签名                          │
└─────────────────────────────────────────────────────────────┘
```

### 多租户（门店/商家订阅）
```
tenant（门店/商家）→ 独立 namespace（genebank chromosome 前缀 + 身份隔离）
  · 每个订阅商家：自己的设备白名单 + 资产空间 + 计量账户
  · 设备身份：device-id 绑定 tenant
  · 未来：可整合其他智能体套壳一起收订阅费（用户意图）
```

### 企业级设计要点（用户要求：完整/稳定/可靠）
1. **多租户隔离**：数据/身份/计量按 tenant 隔离
2. **高可用**：独立服务器（不依赖单台 CLD）+ 状态持久化 + 故障恢复
3. **安全**：TLS/mTLS + 设备认证 + 消息签名（防伪造）
4. **可观测**：全链路审计（消息/认证/计量日志）
5. **协议规范**：HubBridge Protocol v1（自研，文档化）

---

## 五、行动建议（企业级）

| 阶段 | 内容 |
|------|------|
| **P0（立即）** | 恢复启用 rust-genebank（独立服务器，三平台产物已编译）——作为 HubBridge 资产层 |
| **P1** | 插件 npm 发布 + peerDeps 补全（修复 MBP/i9 可用性）|
| **P2** | HubBridge Protocol v1 设计（基于 genebank manifest + 黑板协议 + 身份层）|
| **P3** | 独立部署（腾讯云轻量/CloudBase）+ 多租户 + 订阅计量 |
| **P4** | 开源（协议规范 + 实现）→ 生态 |

---

## 六、结论

1. **genebank 设计落差确认**：原始设计是独立 Rust AI 网盘（manifest 注册/内容寻址/零 token），实际退化为静态文件区——**应恢复启用**。
2. **A2A 协议**：Google 标准（Agent Card/发现）；EMQX 扩展（A2A over MQTT/a2a-status/$a2a 主题）——**可拉源码分析，借鉴思想**。
3. **自研协议**：**可以且应该**——genebank manifest 已是我们的协议原型（比 AgentCard 更丰富），+ 黑板传输 + 身份层 = HubBridge Protocol v1。
4. **企业级**：多租户隔离 + 独立部署 + 安全 + 可观测 + 订阅计量——用户定位正确，产品应完整稳定可靠。
5. **原创性**：genebank「基因/染色体/manifest」是**我们自己的设计**（早于 A2A 调研）——协议原创性有基础，可主张。
