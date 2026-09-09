# 外部网络接入分级 · 实施设计 v1.0

> 设计：2026-08-22 · HR · 用户指示（「外部网络下的接入分级信息」）· 阶段 3 实施细化 · 衔接 access-tiering-role-model-v0.1 + cloud-mcp-gateway-design-v1.0

## 一、内外双通道架构

```
┌────────── 内部通道（Tailscale 安全网络）──────────┐
│ 自有设备（MBP/mac-mini/i9）→ 黑板自举(node.bootstrap) → 角色=internal → 全权限
└──────────────────────────────────────────────┘

┌────────── 外部通道（公网 → 云网关）───────────────┐
│ 门店/员工/订阅用户 → https://域名/mcp（云网关）    │
│   → 认证：门店=企微身份/账号 · 订阅=API key       │
│   → 角色判定：store / subscriber                  │
│   → 返回分级信息（入职包 v2）→ 工具白名单+租户边界  │
└──────────────────────────────────────────────┘
```

## 二、公网接入时序（5 步）

| # | 步 | 内容 |
|---|---|---|
| 1 | 连接 | 外部 MCP client → https://域名/mcp（TLS） |
| 2 | 认证 | 门店=企微 OAuth/门店账号 · 订阅=作用域 API key（x402 风格） |
| 3 | 角色判定 | 网关按认证结果 → store / subscriber（+租户 id） |
| 4 | 分级信息返回 | node.bootstrap v2 返回：role/tenant/permissions/tool_whitelist/data_boundary |
| 5 | 调用过滤 | 网关 ABAC 双重拦截（工具发现+调用）→ 只放行白名单 → 审计 |

## 三、分级信息 schema（node.bootstrap v2）

```json
{
  "channel": "external",
  "role": "store | subscriber",
  "tenant": "store-xxx | sub-xxx",
  "permissions": ["data.read", "reply.draft", "report.read"],
  "tool_whitelist": ["waimai.review-stats", "ops.alerts", "knowledge.search", ...],
  "data_boundary": "data/<tenant>/*",
  "writes": false | ["reply.draft"],
  "approval_required": ["price.change", "shelf.change"],
  "quota": { "calls_per_day": 1000, "tokens_per_day": 100000 }
}
```

## 四、门店角色权限清单（store）

| 能力 | 权限 | 审批 |
|---|---|---|
| 本店订单/评价/报表查看 | ✅ data.read（仅本店） | 无 |
| 客服回复草稿 | ✅ reply.draft（本店） | 无（草稿） |
| 改价/上下架 | ❌ 默认禁 | **必须**店长/总部确认（J45 升级） |
| 跨店数据 | ❌ 硬隔离 | — |
| 内部工具（监察/审批/总线） | ❌ 白名单外全禁 | — |

## 五、订阅用户角色权限清单（subscriber）

| 能力 | 权限 | 说明 |
|---|---|---|
| 简报/报告（每日评价分析/成本趋势） | ✅ report.read | 只读聚合，脱敏 |
| 知识检索 | ✅ knowledge.search | 订阅库范围 |
| 任何写操作 | ❌ 网关层硬过滤 | 无审批路径（比门店更窄） |
| 配额 | 按档限流 | $19-29/mo 个人 / $99-499/mo 团队（open-core 调研） |

## 六、安全执行（外部通道必须）

| 层 | 要求 | 支撑论文 |
|---|---|---|
| 传输 | HTTPS（TLS 证书） | — |
| 认证 | 门店=企微身份；订阅=作用域 key | 2605.30998（x402） |
| 授权 | 网关 ABAC 双重拦截（发现+调用） | 2605.18414（0% 越权） |
| 隔离 | data/<tenant>/* + 权限过滤 | 2403.01862 / 2505.07692（多租户） |
| 审计 | 全量：调用方/租户/工具/时间 | 监察体系扩展 |
| 限流 | 按角色配额（防滥用） | 2605.30998 |

## 七、部署路径（外部通道）

1. **云网关**：CloudBase 云托管（推荐，免运维）或腾讯轻量云——部署 mcp-gateway（node），绑域名+TLS
2. **隧道**：云↔本地 external-link-mcp :8910（Tailscale 子网路由 / frp）
3. **认证服务**：企微身份（已有通道）+ 订阅 key 管理（x402 或自建）
4. **分级配置**：role-config.json（角色→白名单/边界/配额），网关加载

## 八、与内部衔接

| 项 | 衔接 |
|---|---|
| 黑板 nodes/ 域 | 内部节点=nodes/<id>（internal 角色）· 外部=不入 nodes/（租户域 data/<tenant>/* 隔离） |
| node-join-notify | 内部节点上线告知照常；外部租户接入=云网关审计（不进黑板 nodes） |
| J45 审批 | 门店写操作自动升级审批；订阅无写权 |
| 监察 | 外部调用全审计（租户维度），与内部审计同库不同标记 |

## 九、实施顺序（PoC）

1. role-config.json + 网关分级逻辑（本机模拟门店/订阅两角色）
2. 门店模拟：企微身份认证 → 返回 store 分级 → 验证只能看本店 data/
3. 订阅模拟：API key → subscriber 分级 → 验证只读聚合
4. 隔离测试：A 店 token 访问 B 店数据 → 应 403
5. 云部署（CloudBase）+ 真实门店接入（投放时）

---
*外部接入分级 v1.0 · HR · 2026-08-22*