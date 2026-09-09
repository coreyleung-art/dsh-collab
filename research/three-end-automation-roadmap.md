# 三端自动化路线图 + MCP 服务化架构（总报告）

> 数据调查员 · session-4787d717 · 2026-08-17
> 整合 5 路调研：A 论文库 / B 手机 GUI / C 竞品调研 / D 运营端 / E 采购+MCP
> 子报告：~/dsh-collab/research/ 下 ai-papers-database / mobile-gui-control / waimai-competitor-research / waimai-ops-integration / procurement-mcp-service

## 一、总览：一条主线，三端推进，一个出口

核心能力底座：手机 GUI 控制（看-交互-采集）+ 爬虫工具链 + 本地知识库

市场调研端（消费者视角）：竞品门店/商品/价格/排名/视频流
运营端（商家视角）：监控/操作/ERP对接/语音控制
采购端（供应商视角）：花伍/淘宝/1688 订单采集聚合

↓ 最终收敛：MCP 服务化（门店自用 → 外部花店订阅制）

## 二、核心基础设施（共享底座）

### 2.1 手机 GUI 控制 AI 技术路线（调研 B）— Android 优先
| 层 | 方案 | 说明 |
|----|------|------|
| 感知 | Accessibility 树（uiautomator2）+ PaddleOCR + Qwen2.5-VL 截图理解双通道 | 自绘 UI 用 VLM 兜底 |
| 执行 | adb / Appium / Maestro 分层组合 | iOS 归 XCUITest |
| Agent | MobileUse（AndroidWorld 62.9%）、AppAgent、AutoGLM 开源可用 | 桌面 computer use 不宜直接套移动端 |
| 多设备 | scrcpy + adb 自建设备池 | 支持并发调度 |
| 视频流 | 录屏 + ffmpeg 抽帧 + VLM 分析 | 直播/短视频内容情报 |

### 2.2 合规基线（贯穿三端）
- 平台官方开放 API 为主通道，页面/App 自动化仅兜底
- 测试账号 + 低频只读 + 合规评审；虚拟定位、抢单外挂已有真实判例（最高法 2025 / 判赔 300 万案）
- 不采集敏感个人数据；入库数据标注来源与验证状态

### 2.3 AI 能力底座（调研 A）— 论文库
- 8 大主题 60+ 篇高质量论文（Agent 规划/推理增强/RL 对齐/多模态 GUI 智能体/长上下文/评测/上下文工程/蒸馏）
- 信源三层：arXiv API 每日 + HF Daily Papers 每周 + 会议（NeurIPS/ICML/ICLR/ACL/EMNLP）
- 建库：SQLite(FTS5) + ChromaDB，arXiv ID 主键 UPSERT，bge-m3 混合检索

## 三、市场调研端（调研 B+C）

目标：控制手机消费者端外卖 app，切换定位到门店周边，自动分析竞品线上门店。
技术路线：uiautomator2 + scrcpy + 虚拟定位（测试账号）→ 四层采集：
1. 门店基础：评分/月售/配送/活动
2. 商品明细：名称/价格/规格/销量
3. 排名快照：分类排名/搜索排名/榜单（时间戳快照 + 增量对比）
4. 促销策略：满减/折扣/会员
视频流：录制 + 抽帧 + VLM（Qwen2.5-VL/GLM-4.6V）理解花艺展示/价格话术/优惠信息。
落地路线：POC（单店单机 5 店×3 天，完整率≥90%、零封禁）→ 定期巡检 → 竞品周报自动化。
合规红线：平台协议明确禁止机器人/截屏程序；虚拟定位已有封号案例；2025 最高法认定平台对商品数据享有经营性利益——仅内部调研不发布。

## 四、运营端（调研 D）

主通道：美团开放平台（订单接收/批量库存）、饿了么开放平台（五类 API + 回调）；CDP 页面抓取仅兜底。
ERP/小程序对接：集成中台 + Webhook/API + 消息队列（避免数据库直连）；订单近实时推送；库存双向同步 + 10-30 分钟对账；会员按手机号最小化合并。
语音控制门店运营：ASR 本地 FunASR（流式/中文/边缘）首选，Whisper 需 streaming 改造（3.3s 延迟）；意图复用 waimai_voice 升级 LLM function calling；写操作 dry-run → 确认 → 审计。
多门店：优先官方授权（商家账号通/饿了么连锁总账号）；本地多开仅兜底。
Agent 演进：脚本 → 事件驱动编排流水线（LangGraph/n8n），参照京东 master+subagents 与 Minimal。
分阶段路线：Phase0 合规基线 → Phase1 ERP 对接（4-8 周）→ Phase2 语音（4-6 周）→ Phase3 多门店 → Phase4 编排化。

## 五、采购端（调研 E）

| 平台 | 通道 | 风险/建议 |
|------|------|-----------|
| 1688 阿里巴巴 | 官方开放 API（交易/订单/电子面单 + 买家采购方案） | 唯一合规主通道，首选 |
| 淘宝 | 卖家侧 API（需授权） | 买家侧无官方接口；未授权爬虫有不正当竞争判例 |
| 花伍 | 无开放平台 | App 自动化灰色高风险 → 先商务合作数据导出 |

聚合：PostgreSQL 统一订单模型（含 tenant_id）；API/导入双通道对接 ERP 采购模块。

## 六、MCP 服务化最终形态（调研 E）

门店侧：三端能力封装为 MCP 工具集（市场调研/运营/采购）
→ MCP Server：stdio 起步 → Streamable HTTP + 网关演进（TS/Python SDK）
→ 多租户：API Key/OAuth + RLS 行级隔离 + 配额 + 超量计费 + 限流审计
→ 开放：面向外部花店提供订阅式 MCP 服务，其他花店 AI 直接接入

能力清单草案（MCP 工具集）：
- 市场调研：competitor_scan（门店扫描）、product_compare、price_trend、video_insight
- 运营：order_sync、inventory_sync、voice_operate、report_daily
- 采购：procurement_pull（1688 订单）、procurement_aggregate、procurement_cost_analysis

商业模式：订阅制（按门店数/按工具调用/按数据量）+ 配额 + 超量计费；SLA 与审计。

## 七、下一步建议（按优先级）

1. P0 论文库落地：按调研 A 方案建 SQLite+ChromaDB 论文库（可先跑 research-pipeline 补抓全文）
2. P1 手机 GUI POC：Android 测试机 + uiautomator2 + scrcpy，单店单机竞品扫描 POC（合规：测试账号/低频只读）
3. P2 ERP 对接：按调研 D Phase1 设计集成中台（Webhook + MQ），与已有 ERP/小程序打通订单库存
4. P3 采购聚合：1688 开放 API 接入 → PostgreSQL 统一订单模型 → ERP 采购模块对接
5. P4 MCP 服务化：先把门店侧能力封装 stdio MCP，验证后升级 HTTP + 多租户，再谈外部订阅

## 八、风险与合规总提醒

- 平台自动化是高风险区：美团/饿了么/淘宝协议均禁自动化，判例存在（300 万判赔、最高法 2025）
- 所有采集仅限内部调研使用，不发布不转售；测试账号隔离
- 每个平台动手前先做合规评审，输出评审记录归档
