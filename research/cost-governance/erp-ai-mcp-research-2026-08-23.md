# ERP AI 接入调研 · 初蘅 chuheng_erp（数据规范性底座）

> 日期：2026-08-23 · 协调者 fa1f9150 · 用户指示「深度调研 ERP AI MCP 接口，让 ERP 成为数据规范性底座」
> 来源：Gitee 私人仓库 coreyleung/chuheng_erp（源码直读）+ 生产探测 + 架构交接文档

## 一、ERP 本体定位

| 项 | 值 |
|---|---|
| 仓库 | Gitee 私人 `coreyleung/chuheng_erp`（+ 小程序 `chuhengminiprogram`） |
| 本地路径 | `c:\Users\admin\.trae-cn\worktrees\RFID\`（i9，TRAE 开发） |
| 生产 | `flowerclaw.meetfunbp.com`（前端 SPA）+ `erp.chuhenghd.com`（ERP 桥） |
| 版本 | v1.19.12（2026-08-22：仪表盘 5 大看板/审批驳回/下单渠道选择） |
| 技术栈 | Spring Boot 3.2（57 控制器/40 服务/11 仓库）+ Vue3 + PostgreSQL 16 + Android PDA + 企业微信 |

## 二、业务覆盖（供应链全流程）

采购 / 库存 / BOM 配方 / 销售 / 调拨 / 财务 / 供应链定价 / 审批（8 类单据）——三终端（PC 管理后台/手机/ PDA 扫码枪）+ 企微集成（扫码登录/审批 OA/Bot 通知）。

## 三、AI 三通道 + 一规范（统一操作层）

```
AI/智能体 → [MCP 通道 /mcp Streamable HTTP] ──┐
人或脚本 → [CLI 通道 flowerctl] ────────────────┼→ 统一操作层（复用 Service+规范）→ ERP 数据
function → [OpenAPI 通道 /v3] ────────────────┘
```

- **认证**：JWT（Bearer Token），AI 用**专用机器人账号**（`robot-ai`，绑定 supply_chain 角色，V76 追加 purchaser）
- **审计**：AI 写操作落 `audit_logs`（操作人=机器人账号名）
- **幂等**：写操作自动 `Idempotency-Key`（24h 缓存，并发 409 BUSY_IDEMPOTENCY_RETRY）
- **错误码**：统一 `{error, code, message, requestId}`（AUTH_/VALID_/NOT_FOUND_/STATE_/BUSY_/INTERNAL_ 前缀）

## 四、MCP 端点与工具清单（14 个已实现）

**端点**：`/mcp`（Streamable HTTP，MCP 协议）。实现：`McpAgentToolkit.java`（官方 io.modelcontextprotocol SDK）。

| 工具 | 动作 | 只读 |
|---|---|---|
| `erp.api_call` | 通用：按 /api/... 调任意接口（全 ERP 覆盖，写可传 idempotencyKey） | - |
| `dashboard.queryRankings` | 多维统计看板（品种/颜色/等级/门店/趋势） | ✅ |
| `inventory.query` / `inventory.queryLedger` | 库存查询 / 出入库流水 | ✅ |
| `product.query` | 商品/花材查询（SKU/UPC/名称） | ✅ |
| `purchaseOrder.list` / `salesOrder.list` | 采购单 / 销售单列表 | ✅ |
| `approval.list` / `approval.review` / `approval.resubmit` / `approval.myRejected` | 审批 4 工具 | 部分 |
| `supplier.query` / `variety.list` / `variety.upsert` | 供应商 / 品种库 | 部分 |

命名规范：`<业务域>.<动作>`（如 inventory.query、approval.review）。

## 五、数据规范性底座评估（对接蓝图）

ERP MCP 已具备「数据规范性底座」条件：
1. **统一数据口径**：PG16 唯一 DataSource + 供应链全流程（采购/库存/BOM/销售/调拨/财务）
2. **AI 可调用**：MCP 14 工具 + erp.api_call 全 ERP 覆盖（robot-ai 身份，幂等/审计完备）
3. **对接方向**：
   - 外卖订单销售数据下载（waimai_order_export）→ ERP（打通外卖订单与 ERP 库存/销售）
   - ERP ↔ 小程序（chuhengminiprogram，.mcp.json cloudbase MCP + cloudfunctions）
   - ERP = 数据底座 → 蓝图 3.0 端侧完整（感知-决策-执行）→ 4.0 垂直引擎（数据飞轮起点）

## 六、接入待办

1. **robot-ai 凭据**：账号+密码 → 登录拿 JWT（访问 /mcp 用）——需用户提供或从 TRAE 配置/仓库找
2. **MCP 接入测试**：拿 JWT 后调 /mcp initialize + tools/list → 实测 ERP 数据（库存/订单/销售）
3. **数据打通设计**：外卖订单下载 → ERP 映射 + ERP ↔ 小程序 → 统一数据流

## 七、关联

- 全景蓝图：research/ops-science/flower-shop-evolution-research.md（2.5 ERP → 3.0 端侧 → 4.0 引擎）
- 项目统筹：黑板 data/projects/overview（6 项目）
- 小程序：Gitee coreyleung/chuhengminiprogram（.mcp.json + cloudfunctions）

---
*ERP AI 接入调研 v1.0 · 协调者 2026-08-23 · 用户指示深度调研*
