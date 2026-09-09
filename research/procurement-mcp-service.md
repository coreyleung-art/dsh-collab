---
title: 采购端采集聚合 + MCP 服务化形态（任务 E）调研报告
tags: [research, report, procurement, mcp]
updated: 2026-08-17
---

# 采购端采集聚合 + MCP 服务化形态（任务 E）调研报告

> 调研时间：2026-08-17 · 方法：16 次中英文 web_search（8+8 组关键词）+ 10 个来源全文抓取 + 交叉验证（官方文档 > 权威媒体 > 二手转载）

## 调研结论

### 一、采购端自动化：分平台可行路径

**1. 1688（阿里巴巴）：目前唯一有官方采购自动化通道的平台**
- 开放平台 open.1688.com 提供交易类 API：alibaba.trade.fastCreateOrder（快速下单）、买家订单列表，以及 alibaba.logistics.waybill.cloudPrint.applyUpdate 电子面单云打印等；官方设有「买家采购」类解决方案（BuyerPurchase）。
- 接入流程：注册开发者 → 创建应用/资质审核 → 申请订单交易权限 → AppKey/AppSecret 签名鉴权。阿里云开发者社区 2025–2026 多篇实战指南印证同一流程。
- 结论：**首选官方 API 通道**，合规、稳定，适合做「采购订单自动回写 + ERP 对接」主链路。

**2. 淘宝：买家侧无官方订单导出/API，卖家侧才有**
- 淘宝开放平台的订单 API（如 taobao.trade.fullinfo.get）与消息推送（TMC）面向**卖家身份**，需应用审核与类目授权；花店作为采购方没有官方买家订单接口。
- 买家侧可行路径：网页版订单人工导出（Excel/CSV）→ 半自动导入；或 UI 自动化采集。但淘宝明确打击未授权抓取——「搬家软件」爬取商品/订单数据已被多起判例认定为不正当竞争（有 500 万判赔案例），**风险高，不建议作为自动化主路径**。

**3. 花伍：无公开开放平台/订单导出功能**
- 官网与应用商店检索未发现开放 API、开放平台或订单导出入口；花伍是封闭 App 交易 + 官方代运营模式（云南鲜花 B2B 平台，App 2021 年上线，宣称服务数万家花店/批发商）。
- 自动采集只能走 App 端 UI 自动化（无障碍/RPA/抓包/模拟点击）：技术可行，但属**未授权自动化**——违反服务条款、触发账号风控、界面与接口随时变更。
- 建议：先商务合作（企业账户报表导出/数据合作），否则保持人工/半自动导入，用 Excel 模板兜底。

**4. 聚合与 ERP 对接**
- 统一采购订单模型落 PostgreSQL（关系表 + 审计事件表）；对接 ERP 采购模块用「标准 API + 文件导入」双通道；核心字段：供应商/品种/规格/数量/单价/金额/订单状态/物流单号/预计到货。

**5. 合规红线（通用）**
- 未授权爬取/自动化：违反平台服务条款，可能构成不正当竞争（反不正当竞争法「互联网专条」）；
- 订单含收货人姓名/电话/地址 = 个人信息，采集须有合法依据并遵循《个人信息保护法》最小必要原则；
- 电子面单 API 需物流资质与平台授权；自动化操作账号存在封禁/处罚风险；
- 开放订阅给外部花店时，须在 SLA 中注明平台侧风险由客户自担，并取得平台授权。

### 二、MCP 服务化最终形态

**1. 架构选型**
- 传输：本机/内测用 stdio（简单、无网络暴露）；对外服务用 **Streamable HTTP**（2025-03-26 规范取代 HTTP+SSE，原生支持 OAuth 2.0 与 Session 管理）；WebSocket 可作实时补充。
- SDK：TypeScript（@modelcontextprotocol/sdk）适合与现有 TS 栈整合；Python SDK 生态成熟（FastAPI/Starlette 适配，SageMCP 等参考实现）。建议业务侧 TS 实现（与门店三端自动化同栈），团队 Python 为主则 Python 亦可。
- 参考实现：SageMCP（开源多租户 MCP 平台）给出完整形态——多租户路径隔离 + OAuth/API Key + 令牌桶限流（每租户 RPM）+ Mcp-Session-Id 会话 + Prometheus 指标 + K8s 探针 + 字段级加密。

**2. 能力清单（三端工具集）**
- 市场调研端：market_price_lookup、holiday_calendar、keyword_analysis、competitor_tracking（只读）；
- 运营端：order_status、store_performance、issue_scan、review_reply、operation_alert（美团等平台优先走官方 API，动作类高险操作强制人工确认）；
- 采购端：list_purchase_orders、import_purchase_orders、sync_logistics、procurement_analytics、supplier_ledger；
- 工具按只读/低险/高险三级标记，高险操作 human-in-the-loop。

**3. 多租户与鉴权**
- 起步：每租户 API Key + tenant_id 注入；企业客户升级 OAuth 2.0（MCP 规范原生支持）。
- 数据隔离：共享库 + tenant_id 行级（数据库 RLS 行级安全 + 中间件自动注入双保险）；敏感租户可库级隔离；审计日志记录 tenant/tool/参数/结果/时间。

**4. 配额与计费**
- 主流模式（MCP 商业化实践）：**订阅含配额 + 超量按调用计费**（混合模式）。
- 计费单元：工具调用数 / 门店数 / 数据量；推荐「门店数 + 工具调用配额」组合。
- 必须实时额度上限 + 令牌桶限流：失控 agent 案例（8 小时 12.7 万次调用、约 4.7 万美元云成本）证明无上限风险巨大。

**5. 部署与开放订阅**
- 本机（stdio + Docker Compose）先跑通；对外订阅上云：HTTPS 网关（鉴权/限流/审计）+ 容器化部署 + Prometheus/Grafana 监控。
- SLA：内测 99.5%（无赔偿）→ 付费 99.9%（月度可用性，不达标返额度）；配额仪表盘透明展示；审计留存 ≥180 天；P95 响应目标；MCP 版本协商与变更公告。
- 商业模式：按门店数阶梯订阅（1-3 店 / 4-10 店 / 10+ 店）+ 工具调用配额 + 超量按次；企业年付可定制。

## 候选方案对比表

### 表 A：采购端采集路径

| 方案 | 平台 | 数据可得性 | 自动化程度 | 合规风险 | 实施成本 | 推荐度 |
|---|---|---|---|---|---|---|
| 1688 官方开放 API（交易/订单/面单） | 1688 | 高（需应用资质+权限审核） | 高（全自动） | 低（授权内合规） | 中（开发+资质） | ★★★★★ 首选 |
| 淘宝卖家侧订单 API/TMC | 淘宝 | 高（仅卖家身份） | 高 | 低（官方授权内） | 中 | ★★★☆ 仅适用自有店铺 |
| 淘宝买家订单人工导出+导入 | 淘宝 | 中（需手动） | 低（半自动） | 低 | 低 | ★★★ 兜底方案 |
| 花伍 App UI 自动化（RPA/抓包） | 花伍 | 中（屏幕数据，不稳定） | 高（可全自动） | 高（未授权/封号） | 中高（维护成本） | ★★ 谨慎，先谈商务 |
| 物流/电子面单聚合 API（快递鸟等） | 多平台 | 中（物流状态） | 高 | 中（需资质） | 中 | ★★★ 补充通道 |

### 表 B：MCP 服务化形态

| 方案 | 适用阶段 | 优点 | 缺点 | 推荐度 |
|---|---|---|---|---|
| stdio 本地 MCP Server | 内测/MVP | 简单、零暴露、调试方便 | 无法远程多租户 | ★★★★ 第一版 |
| Streamable HTTP 直连 | 小规模多租户 | 官方现代传输、支持 OAuth/会话 | 需自建鉴权/限流 | ★★★★ MVP 二期 |
| 网关 + Streamable HTTP | 对外订阅商业化 | 集中鉴权/限流/审计/计费 | 架构较重 | ★★★★★ 最终形态 |
| 现成多租户平台（SageMCP 自建） | 20+ 客户规模化 | 现成多租户/限流/OAuth | 运维与定制成本 | ★★★☆ 视团队规模 |

## 推荐路线

**Phase 0（1-2 周）— 半自动采购聚合 MVP**
1. 1688 开放平台应用申请（BuyerPurchase 场景），验证订单列表/交易 API；
2. 花伍采购记录以 Excel 模板人工导出导入；PostgreSQL 建统一采购订单表（含 tenant_id）；
3. TypeScript MCP SDK 实现 stdio 版采购工具集（import/list/logistics/analytics），对接内部 ERP 采购模块（API + 导入双通道）。

**Phase 1（1-2 月）— 补全通道 + 上 HTTP**
4. 增加淘宝自有店铺订单 API/TMC（如适用）与物流聚合状态；
5. MCP 升级 Streamable HTTP + API Key/租户表 + 令牌桶限流 + 审计日志；
6. 3 家门店试点，沉淀计费计量（调用/门店/数据量）。

**Phase 2（3-6 月）— 开放订阅**
7. 花伍商务洽谈数据合作（不可行则维持半自动并明确列为产品边界）；
8. MCP 上云（HTTPS 网关 + 监控 + RLS 租户隔离），开放外部花店订阅；
9. 定价：门店数阶梯 + 工具调用配额 + 超量按次；SLA 99.9%；审计留存 ≥180 天。

**统一采购订单数据模型（建议字段）**
supplier_id、supplier_name、platform(huawu/taobao/1688)、order_no、order_status、flower_variety、spec(长度/支数/等级)、quantity、unit、unit_price、total_amount、currency、logistics_company、tracking_no、expected_arrival、remark、created_at、updated_at、tenant_id

## 证据来源（URL 列表）

- https://open.1688.com/api/apidocdetail.htm?aopApiCategory=trade_new&id=com.alibaba.trade%3Aalibaba.trade.fastCreateOrder-2
- https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.logistics%3Awaybill.cloudPrint.applyUpdate-1&aopApiCategory=category_new
- https://open.1688.com/solution/solutionDetail.htm?solutionKey=1612505416731&category=BuyerPurchase
- https://open.1688.com/solution/detail?key=1732675458654&category=null
- https://developer.aliyun.com/article/1703712
- https://developer.aliyun.com/article/1739694
- https://developer.aliyun.com/article/1724447
- https://developer.aliyun.com/article/1678772
- https://open.taobao.com/solutiondetail?id=38
- https://open.taobao.com/tmc.htm?docId=1412&docType=9
- https://www.hua5.com/intro
- https://www.hua5.com/about
- https://apps.apple.com/cn/app/%E8%8A%B1%E4%BC%8D-%E9%B2%9C%E8%8A%B1%E6%89%B9%E5%8F%91%E8%8A%B1%E5%BA%97%E8%B4%A7%E6%BA%90/id1541038932
- https://www.china-flower.com/newsinfo/8526611.html
- https://modelcontextprotocol.io/specification/2025-03-26
- https://github.com/sagemcp/sagemcp
- https://docs.mintmcp.com/blog/rate-limiting-with-mcp
- https://dodopayments.com/blogs/mcp-server-pricing-models
- https://zuplo.com/blog/charge-agents-for-mcp-tool-calls
- https://cloud.tencent.com.cn/developer/article/2714303?policyId=1004
- https://www.ciplawyer.cn/articles/152665.html
- https://www.ciplawyer.cn/articles/157675.html
- http://www.yzwb.net/news/jiangsu/202509/t20250913_263542.html
- https://www.kdniao.com/message/detail/126401

## 噪音排除记录
- 排除 e-com-net / itpub / CSDN 等多篇 1688 API 文章（同源 SEO 拼凑、无官方出处、互相转载），仅作流程参考不采信细节；
- 排除无日期/无出处的二手 App 评测与自动化工具软文；
- 花伍相关以官网与官方媒体报道为准；App 内部功能与接口无法验证（需实测）。

## 局限与待验证
- 1688/淘宝具体接口权限与审核门槛需真实账号实测；
- 花伍是否有企业数据合作/报表导出未公开，需商务沟通确认；
- MCP 规范与计费实践时效性强，2025-03-26 为当前稳定规范版本；
- 平台规则（服务条款、处罚细则）可能更新，上线前需法务复核。

## 下一步建议
1. 发商务函给花伍（数据导出/企业采购账户合作），同时准备 Excel 模板兜底；
2. 启动 1688 开放平台应用申请与接口验证（订单列表、fastCreateOrder、电子面单）；
3. 定义采购订单 schema 并建 PostgreSQL 表 + tenant_id；
4. 用 TS SDK 搭 stdio MVP（采购 4 工具），跑通「1688 拉单 → 归一化 → ERP 采购单」闭环；
5. 内部试点后进入 Streamable HTTP + 网关 + 计费设计；法务评审自动化合规与 SLA 免责条款。
