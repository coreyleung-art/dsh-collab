# 外卖运营端自动化集成与语音控制 · 调研报告（任务 D）

> 调研类型：任务 D 深化方向调研 · 调研子代理产出
> 日期：2026-08-17 · 搜索轮次：3 批 18 次中英文检索
> 范围：① ERP/小程序数据对接 ② 语音控制 ③ 多门店多账号 ④ Agent 架构演进 ⑤ 技术路线
> 合规声明：本报告不收集敏感个人数据；所有平台自动化方案均标注合规风险（平台规则/账号风险/法律边界）。落地前须以平台最新官方政策与开放平台文档为准。

## 调研结论

1. **官方开放平台 API 是合规「数据/操作主通道」，页面抓取（CDP）只能做兜底。**
   - 美团外卖开放平台（developer.waimai.meituan.com / developer.meituan.com）文档明确提供「接收订单数据接口【必须】」、批量获取库存、多商品库存批量查询、商品/门店/营销等接口；服务商体系含资质申请、应用审核、商家授权，并有「商家账号通」支持连锁多门店（官方通知 announcement-1444）。
   - 饿了么 OpenAPI（openapi-doc.faas.ele.me）提供商户/店铺/商品/订单/消息五类 API 及数据推送/回调机制；官方接入流程为：入驻资质认证 → 创建应用（个人/企业）→ 开发调试 → 应用审核（约 3 个工作日）→ 商家授权；连锁店总账号可授权品牌下所有门店。2017 版《饿了么开放平台接入指南》PDF 的流程仍有效，接口细节以现网文档为准。
   - **合规红线**：美团开放平台设有《合规分管理规则》（comm-dev-rule-7）并公开服务商违规处罚决定书（2022/2024 多例）；广州黄埔区法院 2026 年判例认定「通过技术手段突破平台规则、妨碍平台正常运营」构成不正当竞争（抢单外挂判赔 300 万元）。自动化必须走官方授权通道、控制频率、全程审计，严禁绕过验证码/风控或抢占式外挂逻辑。

2. **ERP/小程序商城对接优先「集成中台 + 官方 API/Webhook + 消息队列」，不要数据库直连。**
   - 数据模型映射四张核心表：**订单**（含履约状态机：待接→接单→出餐→配送→完成/取消/退款）、**商品/菜品**（SKU、规格、价格、上下架）、**库存**（门店库存 + 渠道安全库存池）、**会员**（平台会员通与自营小程序会员按手机号/union-id 合并，仅业务必要字段）。
   - 同步策略：订单走 **Webhook 推送 + 拉取兜底**（美团「接收订单」、Deliveroo order/rider/menu 事件均为 HMAC 签名 webhook，无需轮询）；商品/库存用 **API 双向同步 + 定时增量对账**（10–30 分钟窗口）；会员增量同步 + 去重合并。
   - 行业参照：KPaaS 集成实践明确推荐「OMS → 集成中台（API 网关+数据清洗+消息队列）→ ERP」而非点对点；有赞 OMS/「美团外卖对接系统」落地了多平台订单统一、库存同步、渠道安全库存与防超卖；Deliverect/UrbanPiper 是海外聚合器成熟模式（按渠道约束管理菜单/库存/订单状态，且各渠道限制不同）。

3. **语音控制：本地 ASR 首选 FunASR（流式/中文/边缘部署），Whisper 需 streaming 改造；云端 ASR 作备选。**
   - FunASR 官方定位「offline + streaming + edge」工业级工具箱，含 ASR/VAD/标点/说话人管道与 OpenAI 兼容服务，中文场景优于 Whisper 直用；WhisperStreaming 论文实测 3.3s 流式延迟，2025 年起官方已转向 SimulStreaming。
   - 意图层复用现有 waimai_voice 路由（自然语言→意图→动作），升级为 LLM function calling + 正则兜底；写操作沿用 dry-run → 二次确认 → 审计三段式护栏（现有 waimai_operate/waimai_action）。
   - 免提运营关键指标：端到端 <2s、命令式短语高准确率、TTS 播报确认、多门店上下文记忆（如「上次说的店」）。

4. **多门店/多账号：优先官方授权模型；本地多开仅限自有账号低频使用；第三方「多开/代运营」工具不宜进核心链路。**
   - 官方路径：美团「商家账号通」、饿了么连锁总账号授权、美团外卖服务市场《连锁账号管理规则》。
   - 本地现状（10 店 Chrome 9200-9209 + 面板 127.0.0.1:8787）可保留为兜底/补盲（快手、淘宝闪购等未开放场景），但必须降频 + 审计 + 避免触发风控。

5. **Agent 架构从「脚本 + 单 Agent」演进为「编排层 + 可组合原语 + 事件驱动流水线」。**
   - 京东云《商家智能助手》给出电商垂域实证：master + subagents、ReAct 规划 + Tools DAG，工具调用准确率提升 10%、扩展维护效率提升 60%+；Minimal 案例（LangGraph + LangSmith）预计 2025 年 90% 客服工单自治、80%+ 效率提升。
   - 本地可复用：Dify（v1.13.3）、LangGraph/MCPHub、task-board cron、企微 webhook、知识库工具。
   - 演进路径：原语库（已有 13 个动作）→ 事件驱动流水线（新订单→接单→打印→扣库存→对账）→ 多 Agent 分工（监控/经营/客服/语音）→ 人机确认闸门 + 可观测（审计表、trace）。

## 候选方案对比表

### 表 A：ERP/小程序数据对接模式

| 维度 | 数据库直连 | 官方 API 直连 | 集成中台 + API/MQ |
|---|---|---|---|
| 实时性 | 依赖轮询/CDC，延迟高 | Webhook 近实时 | Webhook 近实时 + 队列削峰 |
| 耦合度 | 高（库结构变更即断） | 中（按平台适配） | 低（字段映射/校验在中间层） |
| 双向一致性 | 弱（无幂等/对账） | 中（需自建幂等与补偿） | 强（幂等、补偿、对账一体化） |
| 合规性 | 差（数据边界不清） | 中高（需授权与合规分管理） | 高（可控可审计） |
| 开发/运维成本 | 低 | 中 | 中高（一次性投入） |
| 适用 | 仅存量系统临时过渡 | 单平台少门店 | 多平台多门店长期演进 |

### 表 B：ASR 语音识别方案

| 维度 | 本地 Whisper | 本地 FunASR | 云端 ASR（讯飞/阿里/腾讯等） |
|---|---|---|---|
| 中文准确率 | 中（large 尚可，需调优） | 高（中文工业级） | 高（持续优化） |
| 流式/实时 | 弱（需 WhisperStreaming/SimulStreaming 改造） | 强（官方流式 + VAD） | 强（流式接口成熟） |
| 隐私/数据 | 不出本机（GPU 成本） | 不出本机（可 CPU/边缘） | 数据上云、按量计费 |
| 免提延迟 | ~3.3s 级（论文实测） | <1s 级 | <1s 级 |
| 结论 | 备用 | **推荐主力** | 备选/容灾 |

### 表 C：多门店/多账号管理

| 方案 | 合规 | 控制力 | 成本 | 扩展性 | 主要风险 |
|---|---|---|---|---|---|
| 官方开放平台授权（账号通/连锁总号） | 高 | 中（限平台能力） | 低 | 高（品牌下所有店） | 资质申请可能受阻、接口权限受限 |
| 本地多开 + CDP（现有 9200-9209） | 中低（页面自动化兜底） | 高 | 低（已有） | 中（每窗口一账号） | 平台规则/封号风险，须降频+审计 |
| 第三方 SaaS（外卖邦/有赞等） | 中（看服务商资质） | 低 | 中高（订阅/扣点） | 高 | 数据外流、依赖服务商 |

### 表 D：运营 Agent 编排架构

| 方案 | 适用阶段 | 特点 | 风险 |
|---|---|---|---|
| 脚本 + 正则路由（现状） | 1–2 | 快、透明、易审计 | 意图泛化差、难编排 |
| LLM 意图 + 原语执行器（waimai_voice 升级） | 2–3 | 自然语言操作闭环 | 幻觉需护栏（确认闸门） |
| 编排流水线（LangGraph/n8n + 事件驱动） | 3–4 | 多步任务、可重试、可观测 | 学习与运维成本 |
| 多 Agent 平台（master + subagents） | 4+ | 经营/客服/语音分工 | 复杂度与成本高 |

## 推荐路线

**Phase 0 · 合规与架构基线（1–2 周）**
- 梳理平台授权现状（美团 waimai 开放平台资质、饿了么 openapi 申请状态），输出《数据对接合规清单》。
- 确立基线：官方 API 优先、页面抓取兜底、频率控制 + 全量审计、不绕过验证码/风控。

**Phase 1 · ERP/小程序数据对接（4–8 周，先做）**
- 订单：官方 Webhook 接入（美团接收订单 / 饿了么数据推送），落 events/orders 表；用数据契约双保险模式扩展（复用 waimai-customer-msg-data-contract 经验）。
- 库存：API 双向同步 + 渠道安全库存池 + 10 分钟增量对账；商品上下架/改价走确认闸门。
- 商品/菜单：以 ERP/小程序为商品主数据源，向各平台下发（注意平台差异约束）。
- 会员：平台会员通与小程序会员按手机号合并，仅业务必要字段，不做敏感画像。
- 小程序商城：自营订单直接入 OMS，与外卖订单统一视图。

**Phase 2 · 语音增强（4–6 周，再做强体验）**
- ASR：FunASR 流式本地部署（CPU/MLX 验证中文准确率与延迟）；macOS 听写/手机端输入为过渡。
- 意图：LLM function calling（Dify）+ 现有正则兜底；写操作 dry-run → 确认 → 审计。
- 免提：多门店上下文、命令模板、端到端延迟 <2s 验收；TTS 用 macOS say 起步，后续接 Web Speech Synthesis。

**Phase 3 · 多门店/多账号深化（持续）**
- 优先商家账号通/连锁总账号授权；本地多开降频 + 审计；评估快手/淘宝闪购接入（对齐 roadmap-v2 迭代 4）。

**Phase 4 · Agent 编排化（6–12 周）**
- 事件驱动流水线：新订单→接单→打印→扣库存→对账；用 LangGraph 或 n8n 编排，LangSmith 类 trace 观测。
- 高险动作人工确认闸门 + 回滚记录；能力/资源变化同步登记 agent_profile。

## 证据来源（URL 列表）

**官方文档（一手）**
- 美团开放平台·接收订单数据接口【必须】：https://developer.meituan.com/docs/msg/msg_waimaing_0b380f3e-dd60-473e-9c0f-1addcbfc1a0e
- 美团开放平台·批量获取库存：https://developer.meituan.com/docs/msg/msg_ddzh_3e3c9cce-babf-4faf-9e87-6949e471b8dc
- 美团开放平台·多商品库存批量查询：https://developer.meituan.com/docs/msg/msg_ddzh_e1371f36-2c45-4e90-8b9e-43dda8bb16e8
- 美团技术服务合作中心·外卖接入：https://developer.waimai.meituan.com/home/guide/4
- 美团·合规分管理规则：https://developer.meituan.com/docs/biz/comm-dev-rule-7
- 美团·《合规分管理规则》解读（announcement-5026）：https://developer.meituan.com/isv/announcement/detail?dockey=anno-all&id=announcement-5026
- 美团·商家账号通上线通知（announcement-1444）：https://developer.meituan.com/isv/announcement/detail?dockey=anno-all&id=announcement-1444
- 美团外卖服务市场·连锁账号管理规则：https://rules-center.meituan.com/rule-detail/1362/1
- 饿了么 OpenAPI 开发文档（快速入门）：https://openapi-doc.faas.ele.me/v2/quickstart.html
- 饿了么 OpenAPI 总览：https://openapi-doc.faas.ele.me/v2/index.html
- 饿了么开放平台接入指南（2017 PDF，流程参照）：https://open.shop.ele.me/static/files/join-eleme-openapi.pdf
- Deliverect·Retail POS 集成文档：https://resources.developers.deliverect.com/en/articles/13845356-build-a-retail-pos-integration
- Deliverect·Restaurant 集成流程：https://developers.deliverect.com/page/pos-diagram-restaurant
- Deliveroo Webhooks（AsyncAPI，HMAC 签名事件）：https://raw.githubusercontent.com/api-evangelist/deliveroo/refs/heads/main/asyncapi/deliveroo-webhooks-asyncapi.yml
- UrbanPiper·UberEats 渠道约束：https://api-docs.urbanpiper.com/downstream/aggregator-constraints/ubereats.md
- FunASR 官方仓库：https://github.com/modelscope/FunASR
- WhisperStreaming（论文与实现）：https://github.com/ufal/whisper_streaming

**行业方案与案例（二手但权威/厂商一手）**
- KPaaS·餐饮 OMS→ERP 集成（集成中台/MQ）：https://cloud.tencent.cn/developer/article/2597770
- 有赞 OMS·多平台订单同步：https://www.youzan.com/chanpin/oms
- 有赞·美团外卖对接系统：https://www.youzan.com/chanpin/meituanwaimaidjxt
- 厂佳ERP·ERP 与美团/饿了么对接路径：http://changjiaerp.com/news/4418.html
- 京东云·商家智能助手多智能体技术探索：https://developer.jdcloud.com/article/4196
- LangChain·Minimal 多 Agent 客服系统：https://www.langchain.com/blog/how-minimal-built-a-multi-agent-customer-support-system-with-langgraph-langsmith

**合规与法律**
- 广东政法网·抢单外挂不正当竞争案：https://www.gdzf.org.cn/yasf/content/post_199060.html
- 人民法院报·抢单外挂诉前禁令报道：https://www.rmfyb.com/content/202606/17/article_1028572_1391903745_6665206.html
- 上海观察·售卖抢单外挂判赔 300 万：https://www.shobserver.cn/wx/detail.do?id=1130956
- 美团·服务商数据交互 1 期整改通知：https://developer.meituan.com/isv/announcement/detail?dockey=anno-all&id=announcement-1489

**本地上下文**
- ~/meituan-multi/docs/voice-operation-plan.md、iteration-roadmap-v2.md、architecture.md
- ~/dsh-collab/waimai-ops-deliverables.md、waimai-customer-msg-data-contract.md

## 下一步建议

1. **立即评估官方资质**：申请/确认美团 waimai 开放平台与饿了么 openapi 资质（商家账号 vs 开发者账号、应用审核、商家授权），实测「接收订单」「批量库存」接口；受阻则记录原因并维持页面抓取兜底。
2. **先定义数据契约 v1**：在 dsh-collab 落盘《外卖-ERP 数据契约 v1》（订单/商品/库存/会员字段映射、幂等键、对账窗口），复用事件表双保险协作模式，供相关会话共同消费。
3. **语音 PoC**：本机部署 FunASR，用 10 条真实运营指令（接单/下架/改价/查告警/周报）测中文流式准确率与端到端延迟，对比现有 webkitSpeechRecognition 基线；结果写入 voice-operation-plan.md。
4. **合规自查清单**：高频操作限频、高险二次确认、全量审计；不绕过验证码/风控；不采集顾客敏感个人信息；第三方 SaaS（若引入）须服务商资质 + 数据协议 + 最小化授权。
5. **执行顺序**：先 Phase 1 ERP 对接（离钱最近），再 Phase 2 语音（体验最顺），与 roadmap-v2 迭代 1/3/4 对齐；每阶段设验收与回滚点。

## 附：噪音排除记录（简要）

- 百度云/CSDN/今日头条等 SEO 软文（如「Whisper 部署教程」「170 倍」）：数据夸大或转载无出处，仅作线索；事实以官方 GitHub README / 论文为准。
- 「外卖卫士/外卖科技社」等第三方多开工具软文：无官方资质证明，仅作风险示例，不作推荐。
- 通用「智慧餐饮/聪蛙」等对接文档：与目标场景弱相关或过时（2017–2019），排除。
- 美团/饿了么官网部分 SPA 页面抓取为空：以官方页面标题 + 搜索快照为准，接口细节需登录开发者后台确认（标注为待验证）。

## 局限

- 美团/饿了么接口细节多为官方文档标题级证据（SPA 未抓到全文）；具体字段/权限/限流需在开发者后台以最新文档为准。
- 厂商软文中的量化收益（如「降低 30% 人工成本」「订单处理提升 5 倍」）仅作方向参考，未独立验证。
- 海外（Deliverect/UrbanPiper/Deliveroo）的渠道约束不能直接照搬到美团/饿了么，只借鉴架构模式与事件驱动设计。
