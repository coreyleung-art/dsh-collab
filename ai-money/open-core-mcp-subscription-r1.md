# Open Core / MCP 订阅商业模式深调研 R1

> 调研：数据调查员子代理 · 2026-08-18 · 委托：用户洞察智能体（session-2fe61625）
> 立项背景：用户观察 DSH-Office「开源一半+外网依赖」现象 → 判断该模式可做订阅制 → 规划「花店 AI 运营官」订阅服务（¥300–5,000/店/月）
> 口径：公开可验证来源；收入数字带来源时点；关键数字 ≥2 独立来源；拿不准标「不可得」；已过滤营销软文与同源转载
> 方法：web_search 14 次中英检索 + 关键原文抓取（CuratedMCP / Dodo Payments / SEC 财报 / Manifold Security / Godot 基金会财务报告 / PostHog handbook / Immich 官方博客 / GitHub API）
> 说明：本文件为 R1 合并版，整合此前并行调研与本次补采数据；结构按委托规格重排

---

## 结论摘要（一人创业者视角 TOP 建议）

1. **「开源一半 + 订阅收费」是被验证的主流模式，但付费侧卖的不是代码，而是「托管/聚合/服务/SLA」**。GitLab（FY2026 营收 $955M、跨 $1B ARR 里程碑）、n8n（估值 $2.5B→$5.2B）、PostHog（$57.5M ARR→目标 $100M）、Sentry（$3B 估值）全部是「免费开源核心 + 付费托管/企业功能」。开源侧必须是一个**完整可用**的产品（LavaPi 反复强调），付费侧放「一个人搞不定的东西」：托管、多店聚合、竞品情报、自动运营、兜底服务。
2. **MCP 生态 2026 年已到「人人做服务器、没人收得到钱」的分水岭**：15,930+ 注册服务器、97M 月 SDK 下载，但 95% 开发者零收入（DEV 社区 2026-06）。定价已收敛到 **$19–29/mo 个人档 / $99–499/mo 团队档**（CuratedMCP 2026-05）——花店 AI 运营官 ¥300–5,000/店/月正好落在该区间向中国垂直 SaaS 的映射上，定价锚合理。
3. **给花店 AI 运营官的具体打法：开源「单店自托管版」（采集+告警+话术库，完整可跑），订阅卖「托管多店版」（多店聚合、竞品情报、定价引擎、自动回复、人工兜底）」**；建议**同日双轨发布**（开源与订阅同时上线），避免「先免费后收费」的社区信任税（DEV 社区与 Immich 2:1 差评的教训）。
4. **最大风险不是模式本身，而是口碑**：半成品发布、核心功能依赖未明示的外部服务、许可突变、市场审核形同虚设——四类已被反复验证的「口碑杀手」（Elasticsearch/Redis/HashiCorp 许可翻车 + OpenClaw ClawHub 冒名插件事件 2026-06）。**「开源一半」可以，「没做完就开源 + 核心依赖说不清」必死。**
5. **收入数字可信度分层**：上市公司（GitLab $955M FY2026）与官方披露（PostHog 目标 $100M、Godot 基金会 €465K/2023）可信度最高；n8n/Immich/Cursor ARR 类数字多为融资新闻或单一来源，标注时点与来源，不当「已验证事实」用。

---

## 模式清单（变体表）

| 模式 | 定义 | 代表案例 | 适合场景 | 风险 |
|---|---|---|---|---|
| **Open Core（经典）** | 核心代码开源（OSI 许可），高级功能闭源收费 | GitLab（MIT 核心 + Premium/Ultimate）、Sentry（BSL + 付费企业）、Supabase/Hasura/Mattermost | 开发者工具/基础设施：免费版是获客漏斗，付费版是「一个人搞不定的企业功能」（SSO/审计/托管/合规） | 免费/付费分界线被质疑「人为阉割」；社区信任脆弱；单人难做托管规模化 |
| **Source-available（源码可用）** | 源码公开可读但不满足 OSI 开源定义，许可限制商用/竞品 | Redis（RSALv2/SSPLv2，2024）、HashiCorp（BUSL，2023）、Elastic（SSPL，2021）、n8n（Sustainable Use License「fair-code」） | 想防云厂商白嫖、想保留商业灵活性 | **2024–2025 连续三起翻车**：社区 fork（Valkey/OpenTofu/OpenSearch）、口碑崩塌、被迫回退；n8n 即便做到 $2.5B 估值仍被社区追骂「不是开源」——慎用 |
| **SaaS 化托管（Managed Cloud）** | 代码完全开源，靠官方托管服务收费 | PostHog（MIT + PostHog Cloud）、WordPress（GPL + WordPress.com）、Immich（AGPL + 周边/托管） | 目标用户「能用但不想运维」；开源获客+托管变现 | 云厂商可抢托管生意；免费托管成本失控；转化率低 |
| **免费引擎 + 付费插件/资产** | 引擎/平台免费，靠插件市场、资产、服务收费 | Godot（MIT 引擎 + 资产/赞助）、WordPress（GPL 核心 + 商业插件生态）、VSCode（MIT + 扩展生态）、Unreal/Unity（引擎 + 资产商店 88/12、70/30） | 平台型产品：生态规模是护城河 | 平台不直接收钱（Godot 官方商店付费功能未开放）；靠周边/服务/企业支持变现；生态质量失控风险 |
| **捐赠/基金会** | 无商业主体，靠社区/企业赞助 | Godot 基金会（2023 收入 €465K）、Immich（FUTO 资助全职开发） | 项目有强社区情感、创始人不想商业化 | 收入不稳定、依赖单一大金主；难规模化 |
| **开源核心 + 自愿付费许可** | 完全免费可用，额外「许可」自愿购买 | Immich Server $99.99 / Individual $24.99 终身许可（2024-07） | 口碑优先、不设付费墙 | 收入天花板低；「收钱」动作本身触发社区防御（Immich 134👍/285👎） |
| **MCP 服务器订阅（2026 新形态）** | MCP 服务器/网关按订阅收费（含配额/按调用/按会话） | Anysite（$30/$99/$199/mo）、Composio（$29–229/mo）、Klavis（$99–499/mo）、Glama（$26/mo）、x402 协议（$0.01/调用） | Agent 时代的新 SaaS 形态：垂直数据、工具、网关、治理 | 95% 开发者零收入；「薄包装公开 API」会被绕过；市场均价比服务成本低 |
| **垂直 AI 代运营/订阅** | 卖业务闭环不卖代码：部署费 + 月费 | 白标 AI 接待员 $100–500/客户/月、托管 AI 员工 <$1,500/月（前序报告） | 有行业 know-how 与现成客户的一人创业者 | 交付是服务不是产品，规模受限；需人工兜底 |

**Open Core 分界线最佳实践（LavaPi 2025-10）**：开源侧 = 解决核心问题的完整功能 + 个人/小团队够用 + 全部 API 与扩展点 + 社区驱动功能；付费侧 = 托管基础设施 + 高级权限/审计/合规/SSO + 高量级支持 + 行业专用工具。**判断标准：免费版单独拿出来是一个完整可用的产品，而不是残缺 demo。**

---

## MCP 订阅专题（2026 案例 + 定价）

### 生态规模（2026-05/06 快照）

| 指标 | 数字 | 来源时点 |
|---|---|---|
| 公开目录收录 MCP 服务器 | 10,000+（另有 ~10,000 forks/废弃） | CuratedMCP 2026-05-05 |
| 注册服务器（PulseMCP+Smithery+官方 registry） | 15,930+ | DEV 社区 2026-06-11 |
| 月 SDK 下载（Python+TS） | 97M | 同上 |
| Smithery 平台服务器 | 7,300+ | 同上 |
| MCP 服务器开发者零收入比例 | ~95%（另一口径：变现 <5%） | DEV 社区 2026-05/06 |
| 付费 MCP 价格区间 | $19–149/mo | CuratedMCP 2026-05 |

### 定价收敛（2026 年中观测，CuratedMCP）

- **个人档 $19–29/mo**：Glama $26、Composio Standard $29、多数付费 MCP $19。对标 Cursor Pro $20、Claude Pro $20、Copilot $10–39——「$20–30/mo 是 pro 级开发者工具的心理价位」。
- **团队档 $99–499/mo**：Klavis $99–499、Composio Pro。
- **企业档**：不公开定价（定制合同）。
- **托管集成平台**：Composio 500+ apps、$29–229/mo；Klavis 企业网关。
- **按调用协议 x402**：已处理 1.65 亿笔交易、$50M 流水、$0.01/API call（DEV 社区 2026-06，单源待验证）；Apify 宣称接入 2 万+ 工具（官方博客）。
- **发布者收入案例**：Apify 上 MCP 发布者已达 $2k+/mo（CuratedMCP）；预计 2027 随市场订阅分账基建成熟翻倍。

### 一手定价案例

| 产品 | 类型 | 定价 | 来源（时点） |
|---|---|---|---|
| **Anysite MCP** | 数据类 MCP 服务器（400+ 数据源） | MCP $30/mo、MCP x5 $99/mo、MCP x15 $199/mo；API $49/月起按信用点；7 天试用 | 官方博客 2026-07-04 |
| **XPack** | 开源 MCP 交易市场（Apache-2.0 自部署） | 平台内置按调用/Token 计费 + Stripe；抽成未披露（不可得） | GitHub README / Product Hunt |
| **个体开发者带** | 定制/retainer | $19–49/服务器挂单；定制 $1,000–3,000/个；retainer $500–1,500/月；Upwork $130–185/小时 | DEV 社区 2026-05（单源） |

### 一个真实的一人运营案例（DEV 社区 2026-06）

一人管理 **61 个 MCP 服务器**、同构基础设施、三层定价：`free（限速）/$19 Pro/$99 Unlimited`，用 Stripe 支付链接 + 作用域 token + 审计追踪。作者坦承：**计费基建是自己搭的（作用域凭据、基础设施级支付执行、防 token 共享），大多数 MCP 开发者没时间/背景搭这套**——这是 MCP 变现的基础设施缺口，也是「托管/网关」订阅的生意空间。

### 四种定价模型（Dodo Payments 2026-05-20）

1. **订阅含配额**：月费含固定调用/读取次数，超额计费或限流——适合可预估用量、企业采购偏好固定条目。
2. **按调用（纯用量）**：按工具调用/资源读取计费——适合波动大的早期采用，但账单不可预测、采购难、用户易流失。
3. **按会话/按 Agent**：按并发活跃会话收费——适合「会话级状态比单次调用重要」的产品；会话强度差异大时易错收。
4. **混合订阅+超额（主流）**：订阅锚定关系 + 配额 + 超额费率 + 大额承诺降单价——**大多数 MCP 服务器的正确起点**，与整个 AI 产品定价收敛方向一致。

### 定价常见错误（Dodo Payments）

- 按「容易计量」而非「用户感知价值」收费（用户买结果，你按调用收 → 觉得价不符值）。
- 纯用量无订阅锚（第一张意外账单 = 流失）。
- 隐藏计量（用户看不到用量如何映射到账单）。
- 让少数重度用户主导成本结构（免费用户补贴重度用户 → 模型脆弱）。
- 只按边际成本定价（漏掉工程/支持/安全/SLA 的固定成本）。
- **薄包装收太贵**：若只是包一层公开 API，用户会发现直接调 API 更便宜；认证、限速池、可观测性、便利性是真价值，但不超过底层 API 成本的 3 倍。

### 质量危机（CuratedMCP 2026-05）

最近半年事故流：过度授权 MCP 服务器窃取凭据；捆绑含已知 CVE 的过时依赖；「好心」服务器静默执行未披露的 shell 命令；废弃服务器跟不上最新 MCP 规范。结论：**10,000 个服务器的量贩市场无法审核，68 个服务器的精选市场每个都人工测试**。高级开发者已转向「装更少、更高质量」并愿意为安全付钱。

---

## 成功案例营收表

| 案例 | 模式 | 营收/估值数字 | 来源（时点） | 可信度 |
|---|---|---|---|---|
| **GitLab** | Open Core（MIT 核心 + Premium/Ultimate 订阅） | FY2025 营收 **$759M**（+31%） | SEC 10-K（2025-03） | ✅ 官方 |
| | | FY2026（截至 2026-01-31）营收 **$955M**（+25.8%）；跨 **$1B ARR 里程碑**（Q4 FY26 财报）；TTM $1.00B | SEC 8-K / GuruFocus+Investing.com / 官方 IR（2026-03） | ✅ 官方多源 |
| | | 市值 $6.89B、P/S 6.9（2026-08-17） | stockanalysis（SEC 聚合） | ✅ |
| **n8n** | fair-code（Sustainable Use License，社区版免费自托管 + 云/企业） | 201K GitHub stars；融资：Series B €55M（2023）→ $60M（2025-03）→ Series C **$180M @ $2.5B 估值**（2025-10，官方口径 10x 收入增长）→ SAP 战略投资后 **$5.2B 估值**（2026） | 官方博客 / TechCrunch 2025-03 / PitchBook+TFN / PYMNTS 2026 | ✅ 融资官方+媒体双源；⚠️ 营收金额未披露（不可得） |
| **Immich** | 完全开源 AGPL-3.0 + 自愿许可 + 企业资助 | 111K stars（2026-08，GitHub API）；2024-07 推出终身许可 Server $99.99/Individual $24.99（社区 134👍/285👎 反对后改措辞）；**2024 年底获 FUTO（Louis Rossman）资助全职开发**；Open Collective 仅小额渠道（余额 $447） | GitHub API / GitHub 讨论 #11186 / immich.app 官方博客 / opencollective.com | ✅ 事实；⚠️ 具体收入金额不可得 |
| **Cursor（Anysphere）** | 闭源 AI 编辑器（定价参照；基于 MIT VSCode fork） | **$1B ARR**（2025，dev.to 单源）→ **$200M ARR**（2026 行业报告）→ **$2B ARR/$60B 估值**（2026-04/05，agentmarketcap 单源，低可信）；360K 付费用户、1M+ DAU、64% 财富 500 强（CuratedMCP 2026-05）；Pro $20/mo | dev.to 2025 / 虎嗅 2026 / AgentMarketCap 2026 / CuratedMCP 2026-05 | ⚠️ ARR 口径互相矛盾（$1B vs $200M vs $2B），标传闻与低可信 |
| **PostHog** | 开源 MIT + 官方云托管 | 观测点 **$57.5M ARR**（99% YoY，~2025 中）；另见 $58M/year 报道；官方目标 **$100M ARR by 2026 底**（需 ~7%/月增长） | Smartkarma 2025 / PostHog handbook（官方） | ✅ 官方目标 + 媒体观测双源 |
| **Sentry** | 开源核心 + 付费（BSL 许可） | Series E **$90M @ $3B 估值**（2022-05）；2024 ARR **$100M**、估值 $1.3B（Getlatka 单源，与 $3B 时点冲突，待验证） | Business Wire/Wedbush 2022-05；Getlatka 2024 | ⚠️ 估值官方多源；ARR 单源待验证 |
| **WordPress/Automattic** | GPL 开源 + 商业托管/插件生态 | **$500M+ ARR**（2025-04，The SaaS Podcast 采访 Matt Mullenweg） | listennotes/saastock 2025-04 | ⚠️ 创始人访谈单源（官方口径） |
| **Godot 基金会** | 免费引擎 MIT + 捐赠/赞助 | 2023 收入 **€465,667**：企业赞助 54%（€248K）+ 个人捐赠 28%（€133K）+ SFC 一次性拨款 18%（€84K） | Godot 基金会官方财务报告 2023（内部编制未审计） | ✅ 官方 |
| **MCP 发布者（Apify）** | MCP 服务器订阅 | 头部发布者 $2k+/mo | CuratedMCP 2026-05 | ⚠️ 单源 |

---

## 免费引擎 + 付费插件（生态抽成模式）

| 平台 | 引擎/平台许可 | 市场/生态收费 | 抽成 | 生态激励与风险 |
|---|---|---|---|---|
| **Godot** | MIT（引擎完全自由） | 官方 Asset Library 免费；2026-05 官方新 Asset Store 上线，但 **beta 阶段只允许免费资产，付费/买卖仍在 roadmap、分成未公布（不可得）**；第三方商店（Getly 等）自行收费 | 0%（官方，当前） | 激励：零门槛生态、社区信任强；风险：官方收入靠捐赠（€465K/2023），第三方商店出现「免费资源收费版」乱象促成官方下场 |
| **WordPress** | GPL（核心完全开源） | wordpress.org 免费；商业插件在第三方市场；WooCommerce 官方市场对开发者收费 | 官方市场有抽成（具体比例各家不一，Woo 曾以更高分成换取开发者承担全部支持；统一数字不可得） | 激励：全球最大 CMS 生态、插件即生意；风险：生态碎片化、主题/插件质量与安全漏洞泛滥、2024 起 WP Engine 与 Automattic 商标/托管权大战动摇社区 |
| **VSCode** | MIT + 扩展市场 | 扩展市场免费、微软不抽成（官方 FAQ：扩展作者可自选任何许可） | 0%（微软） | 激励：生态即护城河、免费获客；微软通过 Copilot 订阅/云服务变现；风险：市场审核弱、恶意扩展时有发生（遥测争议催生 VSCodium 分支） |
| **Unreal/Unity** | 引擎免费/部分免费 | 资产商店交易抽成 | Unreal **88/12**（创 88、平台 12，2018-07 起，Ars Technica）；Unity **70/30** | 激励：百亿美元级闭环（引擎免费 + 资产抽成 + 企业许可）；风险：平台政策随时可变 |
| **MCP 生态（2026 新兴）** | 协议开源 | 网关/托管平台收费（Composio $29–229/mo 等）；目录市场免费挂单 | 平台抽成/订阅分账正在形成，无统一比例 | 激励：Agent 时代新分销；风险：95% 作者零收入、量贩市场质量危机、冒名/恶意服务器 |

**模式启示**：抽成越低 → 开发者涌入越快 → 生态越大，但平台自身变现越难（Godot/VSCode 都靠「生态之外」的收入：捐赠/云服务/企业支持）。想靠抽成吃饭，就要提供量贩市场给不了的「审核/治理/分发」——这正是 CuratedMCP 的定位（68 个精选服务器 vs 10,000 个量贩）。

---

## 风险面（翻车案例归纳 + 规避清单）

### 案例 1：Elasticsearch 许可争议（2021 → 2024）

- 2021-01 Elastic 将 Elasticsearch/Kibana 从 Apache-2.0 改 **SSPL**（针对 AWS 托管白嫖）→ 社区与 AWS 激烈反弹，AWS 随即 fork **OpenSearch**，生态分裂。
- 2024-09 Elastic 宣布回到开源（**AGPLv3 + Elastic License 2.0 双许可**），官方称「兑现 2021 承诺」；但 InfoQ/ITPro 报道：**社区信任是否回归存疑**，部分玩家不买账。
- 教训：许可突变是信任杀手；防白嫖的正确姿势是服务化（开源核心 + 官方托管），而不是改许可锁死生态。

### 案例 2：Redis 许可变化（2024 → 2025）

- 2024-03 Redis 从 BSD-3-Clause 改 **RSALv2/SSPLv2** → 社区 fork **Valkey**（Linux 基金会托管，获得大量发行版/云厂商支持）；ITPro 直言「可能面临用户出走」。
- Percona 量化「许可变更后的社区流失」；2025-05 Redis 宣布回 **AGPLv3**，InfoQ 标题即问「是否为时已晚」。
- 教训：即便回退，流失的用户与信任不会全部回来；**fork 是社区对「背叛开源承诺」的标准报复手段**。

### 案例 3：HashiCorp BSL 事件（2023 → 2025）

- 2023-08 Terraform 从 MPL 改 **BUSL**（防云厂商白嫖）→ 2023-09 Linux 基金会孵化 **OpenTofu** fork → 2025-02 IBM 完成 **$6.4B** 收购 HashiCorp（The Register）。
- 2026 报道：38% Terraform 用户考虑迁移（yaw.sh）；OpenTofu 持续补 Terraform 没做的事（1.12 版本对比）。
- 教训：防白嫖的许可改动会把「反云厂商」叙事变成「反社区」叙事；收购进一步放大不确定性。

### 案例 4：OpenClaw ClawHub 冒名/恶意技能事件（2026-02 → 2026-07，最新）

- **Manifold Security（2026-06-19）**：发现 **23 个代码执行插件冒用 @openclaw/ 与 @clawhub/ scope**（ClawHub 收录 1,508 个插件中 557 个带 @owner/ scope，但未全部验证所有权）。其中 `@openclaw/security-gate`（名字像官方安全审查插件）**通过了平台自带安全扫描**。报告后 ClawHub 才补 scope 争议流程并下架。
- 云安全联盟 CSA 连续发文：Poisoned Skills、SkillCloak（恶意技能可绕过市场扫描器）、ClawHub Under the Microscope；Palo Alto Unit 42：AI 供应链风险；另报道 2 个 **macOS infostealer** 恶意技能。
- 媒体统计：1,508 个技能中多达 **55 个冒用知名开发商名义**（IT之家 2026-06-28）。
- 早期口径（2026-02/03，数字互相打架，方向一致）：clawctl 称 2,857 技能中 341 恶意 + 483 可疑（~12%）；虎嗅称「超 1/3 恶意或冗余包装」。两口径不一致，均列示不合并。
- 教训：**市场审核形同虚设 = 平台信任崩塌**；「名字像官方的插件」是 AI 供应链攻击最有效的伪装；一人/小团队做市场必须先解决审核与来源验证。

### 「什么会毁掉口碑」归纳（对 DSH-Office 现象的映射）

| 口碑杀手 | 机制 | 案例 |
|---|---|---|
| **半成品即发布** | 用户装了跑不通 → 第一印象即差评，且修复后口碑不回来 | 大量「v0.x 就开源」的 AI 项目；DSH-Office 现象 |
| **核心功能依赖未明示的外部服务** | 开源一半但核心依赖外网/付费 API，自托管跑不通 → 用户觉得被「钓鱼」 | DSH-Office 现象的直接类比；MCP 服务器静默依赖外部 API |
| **许可突变/回退** | 社区 fork + 信任崩塌，回退也难挽回 | Elasticsearch、Redis、HashiCorp |
| **免费转付费搬移功能** | 用户感觉被绑架 | LavaPi 点名的「版本间搬移功能」；Immich 自愿许可仍 2:1 差评 |
| **市场/生态审核形同虚设** | 恶意/冒名包横行，平台背书贬值 | ClawHub（2026-02~07） |
| **薄包装收高价** | 用户发现直接调底层 API 更便宜 | Dodo Payments 点名的 MCP 定价错误 |
| **宣称与事实不符** | 叫「开源」但许可不是 OSI 开源 → 被社区追骂 | n8n「is not open source」HN 长期争议（即便 $2.5B 估值） |
| **运行时不可审计** | 核心开源但运行时闭源/外部下载 → 供应链风险外溢给用户 | VSCodium 分支存在的原因；DSH-Office「壳开源+闭源引擎」 |

### 规避清单（落地到花店 AI 运营官）

1. **开源版本必须完整可跑**：单店版含采集、告警、话术库、基础报表——单独拿出来是一个能自用的产品，而不是「demo 外壳」。
2. **外网依赖明示**：哪些功能需要 AI API/外网服务、成本谁付，写进 README 与定价页；宁缺毋滥，不发布「没做完」。
3. **不碰许可突变**：开源核心用 MIT/Apache/AGPL 之一固定下来，商业模式靠「服务/托管/聚合」赚钱，永远不回头改许可；不宣称 OSI 开源除非真的符合（n8n 教训）。
4. **审核先行**：若做插件/技能市场，先解决来源验证与沙箱，再谈规模（ClawHub 的教训）。
5. **定价对得起价值**：别做「包一层公开 API 收 3 倍价」的薄包装；锚定结果价值（帮花店多接单/省人工），而不是调用次数。

---

## 一人创业者落地建议（花店 AI 运营官 ¥300–5,000/店/月）

### 产品化边界（开源哪一半 / 订阅卖什么）

| 层 | 内容 | 形态 |
|---|---|---|
| **开源层（免费，获客与信任）** | 单店版：订单/评价采集、告警、话术库、基础日报 | 自托管（Docker），MIT 许可，完整可跑 |
| **订阅层（付费，¥300–5,000/店/月）** | 多店聚合看板、竞品情报（flower-intel 定价引擎）、自动客服回复、运营日报自动化、AI 定价建议、人工兜底/SLA | 官方托管 SaaS |
| **增值（可选）** | 花材行情数据订阅（¥99–299/月）、模板/内容库 | 独立收费项 |

### 定价建议（锚定市场证据）

- **锚点**：MCP/开发者工具个人档 $19–29/mo、团队档 $99–499/mo（CuratedMCP 2026-05）；垂直数据型 MCP 一手定价 $30/$99/$199（Anysite 2026-07）；中国垂直 SaaS 花店场景订阅常见 ¥99–999/店/月。**¥300–5,000/店/月区间合理，建议分三档**：
  - ¥300/店/月：告警 + 话术库 + 基础日报（低门槛入门）
  - ¥1,000–2,000/店/月：+ 多店聚合 + 竞品情报 + 自动回复（主力档）
  - ¥3,000–5,000/店/月：+ 定价引擎 + 人工兜底运营 + SLA（旗舰档）
- **形状**：采用「订阅锚 + 用量超额」（Dodo Payments 推荐的主流形态）——订阅给确定性，超额（超出店铺数/消息量）保护成本。
- **先付费后免费的红线**：「先开源再收费」会触发社区「背叛感」（DEV 社区：加了付费墙像背叛 1000 活跃用户；Immich 自愿许可仍被 2:1 差评）。**建议一开始就双轨发布**：开源单店版与订阅托管版同日上线，避免「先免费后收费」的信任税。

### 落地验证路径（4–8 周，承接立项书 P0）

1. 用自己的 10 家店跑通接单/催单/售后自动化（8787 体系 dogfooding，已在跑）。
2. 记录 ROI 数字（省客服工时/少漏单/差评处理速度）。
3. 包装成「花店 AI 运营官」，本地 3–5 家花店试点（部署费 + 月费）。
4. 试点跑出留存数据后，再开放开源单店版 + MCP/API（本体开源、数据与托管闭源）。

### 风险规避（对照风险面清单）

- 开源版**不要**包含「必须连你的云才能跑」的核心逻辑——那等于半成品+外网依赖，正是 DSH-Office 被诟病的点。
- 竞品情报、定价引擎这类「持续运营才有价值」的能力放订阅层——天然防 copy、防白嫖，且符合「付费侧卖一个人搞不定的东西」原则。
- 不做插件市场（审核成本高、ClawHub 前车之鉴），做「开源单店 + 托管多店」的经典 Open Core 双轨。
- 合规红线：若用开放核心，用「源码可得/开放核心」表述而非「开源」；核心/付费边界写清楚（n8n + Immich 双重教训）。
- 收入预期管理：参照 n8n/Immich，一人项目早期营收主要靠「少数付费店 × 高价值订阅」；先 dogfooding 自证（已立项 P0），跑出留存数据再外售。

---

## 证据来源

**Open Core 模式**
- LavaPi《Open Core Models: Drawing the Line Between Free and Paid》2025-10-09 — https://www.lavapi.com/blog/open-core-free-vs-paid-features
- BuildMVPFast《Open-Source Business Models: Open Core vs Managed Cloud》2026 — https://www.buildmvpfast.com/blog/open-source-business-model-open-core-source-available-managed-cloud-2026
- ossalt.com《Open Source Business Models 2026》 — https://ossalt.com/guides/open-source-business-models-how-oss-companies-make-money

**MCP 生态与定价**
- CuratedMCP《The State of MCP in 2026》2026-05-05 — https://www.curatedmcp.com/learn/state-of-mcp-2026
- DEV《15,000 MCP Servers, 97M Monthly Downloads, and Almost No One Getting Paid》2026-06-11 — https://dev.to/t49qnsx7qtkpanks/15000-mcp-servers-97m-monthly-downloads-and-almost-no-one-getting-paid-4g7b
- DEV《The MCP Server Gold Rush: 97M Downloads/Month, Less Than 5% Monetized》2026-05-19 — https://dev.to/_0ab26c58dc71f018dd7c3e/the-mcp-server-gold-rush-97m-downloadsmonth-less-than-5-monetized-2eh6
- Dodo Payments《MCP Server Pricing Models》2026-05-20 — https://dodopayments.com/blogs/mcp-server-pricing-models
- Anysite 官方《New MCP Plans》2026-07-04 — https://anysite.io/blog/new-mcp-plans/
- Apify 官方《Introducing x402 support》2026 — https://blog.apify.com/introducing-x402-agentic-payments/
- Peliqan《MCP Server pricing 2026》 — https://peliqan.io/blog/mcp-server-pricing/
- MCP Marketplace《How to monetize your MCP server》 — https://mcp-marketplace.io/blog/how-to-monetize-mcp-server
- XPack GitHub（开源 MCP 市场） — https://github.com/xpack-ai/XPack-MCP-Marketplace

**成功案例营收**
- GitLab FY2025：SEC 10-K（2025-03）— https://www.sec.gov/Archives/edgar/data/1653482/000162828025021579/arsedgargitlabform10k.pdf
- GitLab FY2026 财报（2026-03-03，官方 IR）— https://ir.gitlab.com/news/news-details/2026/GitLab-Reports-Fourth-Quarter-and-Full-Year-Fiscal-Year-2026-Financial-Results-Board-of-Directors-Authorizes-400-million-for-Share-Repurchase-Program/ ；$1B ARR 里程碑 — GuruFocus（2026-03）：https://ca.investing.com/news/company-news/gitlab-inc-gtlb-q4-2026-earnings-call-highlights-surpassing-1-billion-arr-and-strong-cash--4493042 ；营收序列 — https://stockanalysis.com/stocks/gtlb/revenue/
- n8n Series C：官方博客（2025-10-09）— https://blog.n8n.io/series-c/ ；PitchBook — https://pitchbook.com/news/articles/ai-agent-startup-n8n-lands-2-5b-valuation-with-180m-series-c ；TFN — https://techfundingnews.com/n8n-raises-180m-series-c-2-5-billion-valuation-automation-ai/ ；SAP $5.2B：PYMNTS 2026 — https://www.pymnts.com/news/investment-tracker/2026/sap-integrates-n8n-to-scale-agentic-ai-for-enterprises/
- Immich：GitHub API（111K stars，2026-08）；终身许可讨论 #11186 / #11226 — https://github.com/immich-app/immich/discussions/11186 ；官方博客《2024 - A year in review》— https://immich.app/blog/2024-year-in-review ；Open Collective — https://opencollective.com/immich
- Cursor：dev.to $1B ARR 2025 — https://dev.to/andrew-ooo/how-cursor-became-the-fastest-b2b-company-to-1b-arr-with-just-300-employees-34na ；虎嗅 2026 — https://www.huxiu.com/article/4840795.html ；AgentMarketCap $60B/$2B 2026-05 — https://agentmarketcap.ai/blog/2026/05/22/anysphere-cursor-60b-valuation-2b-arr
- PostHog：官方 handbook future.md（$100M by 2026）— https://raw.githubusercontent.com/PostHog/posthog.com/master/contents/handbook/future.md ；Smartkarma $57.5M ARR 99% YoY — https://www.smartkarma.com/home/daily-briefs/daily-brief-private-markets-posthog-at-57-5m-arr-growing-99-yoy-and-more/
- Sentry：Series E $90M @ $3B，Business Wire 2022-05 — https://investor.wedbush.com/wedbush/article/bizwire-2022-5-4-sentry-raises-90-million-in-series-e-funding-to-expand-and-drive-adoption-of-developer-first-application-monitoring ；$100M ARR 2024 — https://getlatka.com/companies/sently.io
- Automattic $500M+ ARR：The SaaS Podcast 2025-04 — https://saastock.com/blog/how-matt-mullenweg-scaled-automattic-to-500m
- Godot 基金会 2023 财务报告（官方 PDF）— https://godot.foundation/downloads/Godot-Foundation-Financial-Report-2023.pdf

**免费引擎 + 付费插件**
- Unreal 88/12 — Ars Technica 2018-07 — https://arstechnica.com/gaming/2018/07/epic-ups-unreal-marketplace-creators-pay-well-above-industry-standard/
- Unity 70/30 对照 — Unity Discussions — https://discussions.unity.com/t/epic-ue4-shifting-from-70-30-payout-for-marketplace-publishers-to-88-12-thoughts/707847/12
- Godot 官方新商店上线 — 80.lv — https://80.lv/articles/godot-is-launching-a-new-asset-store-to-replace-the-old-asset-library ；Blips.fm 2026-05-25 — https://blog.blips.fm/articles/the-godot-game-engine-now-has-an-official-asset-store ；Godot Store Roadmap（付费未开放）— https://store.godotengine.org/roadmap/
- VSCode 扩展许可 FAQ（微软官方）— https://raw.githubusercontent.com/microsoft/vscode-docs/main/docs/supporting/faq.md

**翻车案例**
- Elastic 回开源官方新闻稿 2024-09 — https://ir.elastic.co/News--Events/news/news-details/2024/Elastic-Announces-Open-Source-License-for-Elasticsearch-and-Kibana-Source-Code/ ；InfoQ 2024-09 — https://www.infoq.com/news/2024/09/elastic-open-source-agpl/ ；ITPro — https://www.itpro.com/software/open-source/elastic-returns-to-open-source-but-can-it-regain-the-communitys-trust-some-industry-players-arent-holding-their-breath
- Redis 回 AGPL：InfoQ 2025-05 — https://www.infoq.com/news/2025/05/redis-agpl-license/ ；Percona《Community Erosion Post License Change》 — https://www.percona.com/blog/community-erosion-post-license-change-quantifying-the-power-of-open-source/ ；ITPro Redis 用户出走风险 — https://www.itpro.com/software/open-source/redis-insists-license-changes-were-the-only-way-to-compete-with-amazon-and-google-now-it-could-face-a-user-exodus
- HashiCorp/IBM $6.4B：The Register 2025-02 — https://www.theregister.com/2025/02/28/ibm_hashicorp_deal_closing/ ；OpenTofu 官方 fork 公告 — https://opentofu.org/blog/opentofu-announces-fork-of-terraform/ ；yaw.sh《38% of Terraform Users Want Out》 — https://yaw.sh/blog/ibm-bought-hashicorp-terraform-users-want-out/
- OpenClaw ClawHub：Manifold Security 2026-06-19 — https://www.manifold.security/blog/scope-squatting-clawhub-plugins ；CSA Poisoned Skills 2026-06-24 — https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-skill-supply-chain-attacks-20260624-csa/ ；CSA ClawHub 2026-07 — https://labs.cloudsecurityalliance.org/research/csa-research-note-openclaw-clawhub-supply-chain-risk-2026070/ ；Unit 42 — https://origin-unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk/ ；IT之家 2026-06-28（1508 技能中 55 冒名）；clawctl 2026-03-30 — https://www.clawctl.com/blog/openclaw-clawhub-malicious-skills-2026 ；虎嗅 2026-02-27 — https://m.huxiu.com/article/4837573.html ；OpenClaw 官方安全改进 issue — https://github.com/openclaw/openclaw/issues/92077
- n8n「不是开源」社区批评 — HN 2022/2025 — https://news.ycombinator.com/item?id=32797853 ；https://news.ycombinator.com/item?id=45453601
- VSCodium 为什么存在 — https://raw.githubusercontent.com/VSCodium/vscodium.github.io/master/_posts/2000-01-04-why.md

**花店垂直参考（前序报告）**
- 前序报告（AI 代运营定价带）：`/Users/coreyleung/dsh-collab/ai-money/foreign-ai-money-modes-r1.md`（2026-08）

**噪音排除记录**
- 搜索引擎命中但内容为 SEO 拼凑/无出处的 CSDN「开源创富」类文章（定价策略列表）——仅取模式概念，不采信其数字。
- opencollective.ecosyste.ms 的 Immich 聚合页（付费墙，改为官方 opencollective.com 核实）。
- SEC 官网直接抓取被反爬拦截，改用 stockanalysis（SEC 数据聚合）交叉核对。
- 二手转载的 Cursor ARR 报道（多个中文 SEO 站互相抄袭同一数据）——保留原始出处（dev.to/虎嗅/AgentMarketCap），淘汰转载站。
- pulsemcp.com 正文被 Cloudflare 拦截 → 仅用标题/摘要，正文数字未采。
- ClawHub 恶意技能两口径（clawctl 12% vs 虎嗅 >1/3）数字打架 → 并列呈现不合并。

---

## 置信度与不可得项

**高置信（≥2 独立来源或官方披露）**
- GitLab FY2025 $759M / FY2026 $955M / 跨 $1B ARR（SEC 财报 + GuruFocus/Investing.com + 官方 IR）
- n8n 融资轨迹与估值（官方博客 + TechCrunch/PitchBook/PYMNTS）
- MCP 生态规模与定价收敛（CuratedMCP + DEV 社区 + Dodo Payments 三方独立）
- Elasticsearch/Redis/HashiCorp 许可事件时间线（官方公告 + InfoQ/媒体）
- ClawHub 冒名插件事件（Manifold + CSA + Unit 42 + 媒体）
- Godot 基金会 2023 收入（官方财务报告）
- PostHog $100M 目标（官方 handbook）+ $57.5M 观测点（Smartkarma）
- Anysite MCP 定价 $30/$99/$199（官方博客一手）

**中等置信（单源或时点冲突，需谨慎引用）**
- Cursor ARR：$1B（2025 dev.to）vs $200M（2026 行业报告）vs $2B（AgentMarketCap）严重冲突——全部标注口径与低可信
- Sentry 2024 ARR $100M（Getlatka 单源，且与 2022 年 $3B 估值时点关系不清）
- Automattic $500M+ ARR（创始人访谈单源，官方口径）
- x402 的 165M 交易/$50M 流水（DEV 社区单源）
- Apify MCP 发布者 $2k+/mo（CuratedMCP 单源）
- ClawHub 恶意技能比例（12% vs >1/3 两口径冲突）

**不可得（明确标注）**
- n8n 具体营收/ARR（私人公司未披露；估值≠营收）
- Immich 具体收入金额（GitHub Sponsors 数据不公开；Open Collective 仅小额渠道；终身许可收入未披露）
- Cursor 确切 ARR（公司未官方披露，媒体口径互相矛盾）
- WooCommerce 官方市场确切佣金比例（多方说法不一，无官方统一披露）
- Godot 官方商店分成比例（付费功能未开放）
- XPack 平台抽成比例（未披露）
- 各付费 MCP 服务器的具体付费用户数

**局限**
- 收入数字多来自公司官方/融资公告（未经审计）或单源自述；「MCP 服务器月订阅收入」尚无可靠的行业汇总统计（<5% 变现率为单源估算）。
- 调研时点 2026-08；MCP/x402 生态变化极快，结论有效期约 6–12 个月。

---

# 深化补充 R1.1（2026-08-18 追加 · 委托方调整方向后补采）

> 委托方指示：不重跑已覆盖方向，重点深化两个缺口——A) 垂直行业 SaaS 定价带实测；B) 更多 MCP 定价实例。以下内容为在底稿核心结论（已保留于上文）之上的追加深化。底稿原文中的错误/需修正处见本文件末尾「修订记录」节。

## 缺口 A：垂直行业 SaaS 定价带实测（花店/宠物/美业 + AI 代运营）

### A1. 花店垂直 SaaS

| 产品 | 定位 | 定价 | 来源（时点） | 可信度 |
|---|---|---|---|---|
| **Floranext** | 花店建站/电商 + 订单（美国，花商自建） | 起步 **$30/mo**（Florist Websites 套餐；免费试用） | softwaresuggest（2026-08-16 更新） | ✅ 第三方目录核实厂商定价 |
| **FloristWare** | 花店 POS/订单管理（加拿大） | 官网定价页未公开抓取到（**不可得**） | softwareadvice / floristware.com（2026-08 检索） | ⚠️ 不可得 |
| **宏达花店进销存**（阿里云市场） | 花店客户订单进销存（中文） | 云市场买断/年费制，具体价未在摘要露出（**不可得**） | 阿里云市场 | ⚠️ 不可得 |

### A2. 宠物美容垂直 SaaS（逐厂商核实定价，2026-07-28）

来源：Twizzlo《Best Pet Grooming Software 2026: Real Prices Compared》——作者逐一对照各厂商定价页核实（并纠正了其他榜单 4 处错误定价），可信度较高。

| 产品 | 月费 | 计费单位/备注 |
|---|---|---|
| DaySmart Pet Basic | **$29/mo**（前提用 DaySmart 支付；+$9/额外用户） | 入门档；Deluxe Growth $149、Premium $199 |
| Groomsoft | **$29.95/店**（移动美容 $39.90） | 固定月费 |
| Twizzlo | **$29.99/mo**（1 人美容师与 5 人两店同价） | 按店计费 |
| Groomer.io | **$99/mo/店面或 van**（含无限 SMS） | 限时 $79 |
| Pawfinity Royal | **$110/mo**（真实底价 $55，非某些榜单写的 $29） | 含 boarding/daycare |
| Gingr Spa / Play / Stay | **$109 / $169 / $179/mo**（Spa=美容+训练档；无 Gingr 支付时 Stay $209） | 按 location；SMS/支付为付费 add-on |

**区间**：宠物美容垂直 SaaS **$29–199/mo**（约 ¥210–1,430/月），主流入门档 $29–55，含 boarding 的旗舰档 $110–199。MoeGo（多数榜单第一）不公开定价（第三方报 $79/$149/$249，未验证）。

### A3. SPA/美业垂直 SaaS（逐厂商核实定价，2026-08-14）

来源：Twizzlo《Best Spa Management Software 2026: Real Prices, Compared》（核实日 2026-08-14）。

- **发布价区间 $19.95–410/mo**；Fresha、Vagaro、GlossGenius、DaySmart、Twizzlo 起步均 **<$30**。
- Twizzlo：Free（150 bookings/mo 上限）+ Business Pro **$29.99**（不限员工/门店/预约）。
- Mangomint **$120 + $10/用户**；Boulevard **$176/location**；Mindbody **$79 起步**；Zenoti 不公开（联系制）。
- 定价随「可预约技师数」非线性上升：1 人档约 $30、8 人档约 $120–200。

### A4. 中文美业 SaaS（直接对照人民币定价带）

| 产品 | 定价 | 折算月费 | 来源（时点） |
|---|---|---|---|
| **美管加 风尚版** | ¥2,000/单店/首年；¥1,600/分店/首年；**续费 ¥1,500/单店/年** | ≈ ¥125–167/店/月 | 思迅天店报道引美管加官网（2025-09-04） |
| **美管加 尊尚版** | ¥5,000/单店/首年；¥4,000/分店/首年；续费 ¥1,500/单店/年 | ≈ ¥333–417/店/月 | 同上 |

### A5. AI 电话接听/「AI 代运营」类服务定价（花店运营官最直接对标）

来源：NextPhone《Answering Service Cost Per Month 2026》（2026-08-11 更新，含多家竞品定价表）。

| 服务类型 | 月费区间 | 实例 |
|---|---|---|
| 自动 IVR | $25–100/mo | — |
| **AI 电话接听** | **$50–300/mo** | NextPhone $199/mo 无限通话（Growth $299 含 CRM/Zapier）；Smith.ai 30/90/300 通话 = $300/$810/$2,100/mo（超量 $11.50/$10.50/$8.50/通） |
| 真人话务员 | $200–2,000/mo | Ruby Receptionists 50/100/200/500 分钟 = $250/$395/$720/$1,725 |
| 混合（AI+真人） | $250–1,000/mo | ReceptionHQ $25/$35/$49/$49 起步 + 按通话计费 |

**关键结论**：AI 比真人便宜 **60–85%**；大多数小企业付 **$100–500/mo**；「AI 接听/代运营」作为服务而非软件的定价带是 **$50–300/mo（约 ¥360–2,160/月）**。

### A 缺口小结（对花店 AI 运营官的定价启示）

1. **垂直 SaaS 工具订阅带**：$20–200/mo（约 ¥140–1,440/店/月）——Floranext $30、宠物 $29–199、美业 $20–410、中文美业 ¥125–417/店/月。
2. **AI 代运营/服务带**：$50–300/mo（约 ¥360–2,160/店/月）——AI 电话接听实证（NextPhone/Smith.ai）。
3. **¥300–5,000/店/月 三档设计完全落在两个实证带之上**：¥300 档 ≈ 工具订阅带下限（对标美管加续费 ¥125–167/月 + AI 增值）；¥1,000–2,000 主力档 ≈ AI 代运营带（对标 $50–300/mo + 花店 know-how 溢价）；¥3,000–5,000 旗舰档 ≈ 真人代运营带（对标 $200–2,000/mo 的中低端，含人工兜底）。
4. **计费形态参照**：垂直 SaaS 普遍「按店/按 location + 附加模块收费」（Gingr 的 SMS/支付 add-on、DaySmart +$9/用户）——花店运营官可按「店数 + 附加模块（竞品情报/定价引擎/人工兜底）」拆档，而非纯按用量。

## 缺口 B：更多 MCP 定价实例（除 Anysite 外，2025–2026）

| 产品/案例 | 定价 | 备注 | 来源（时点） |
|---|---|---|---|
| **Rumblingb 61 服务器矩阵**（一人 + AI 运维代理） | 每个 MCP：free 档（base 永远免费）+ **Pro $19/mo + Unlimited $99/mo** | 26 个 MCP 服务器全部 Stripe 订阅；总成本 $12–41/mo（DeepSeek API $2/mo + Stepfun $10–29/mo + 免费层）；**盈亏平衡 = 1 个 Pro 订阅**；1% 转化 @$19：1,000 用户 = $190 MRR | DEV 2026-06-11 |
| **MCPize 平台（定价指南 + 市场）** | 推荐 Pro 档 **$9–29/mo**；10x 规则（Price = 客户月价值/10）；免费档建议 100 calls/day | 平台抽成：**创始会员 15%（2026-06-10 前锁定）→ 标准 20%**——新生态平台费基准 | mcpize.com 2025-10-15 |
| **whoffagents 独立 MCP** | **$19/mo**（市场均价 $0 时主动定价） | 作者论证「市场均价 $0 ≠ 价值 $0」 | DEV 2026（正文已抓取） |
| **Composio** | Standard $29 → Pro $99+（$29–229/mo 区间） | 500+ apps 托管集成平台 | CuratedMCP 2026-05 |
| **Klavis** | $99–499/mo | 企业 MCP 网关 | CuratedMCP 2026-05 |
| **Glama** | $26/mo（Pro） | 发现 + 聊天平台 | CuratedMCP 2026-05 |
| **Smithery** | 定价页无公开数字；已并入 **Arcade.dev**（2026） | 7,300+ 服务器托管平台，收费改为联系制（**不可得**） | smithery.ai/pricing（2026-08 检索） |

### B 缺口小结

- **付费 MCP 服务器定价带收敛于 $9–29/mo（Pro）/ $99/mo（Unlimited）**，与垂直 SaaS 工具带（$20–200/mo）高度重合——MCP 订阅本质是「API/SaaS 的 MCP 皮肤」，价格锚来自底层价值而非协议。
- **平台抽成 15–20%**（MCPize）是新生态的分账基准；一人矩阵案例证明 **$19/mo × 少量付费用户即可盈亏平衡**（成本 $12–41/mo）。
- 对花店运营官的启示：若未来开放「花店运营 MCP」，按 **$19–29/mo（¥140–210）的 Pro 档 + 免费限速档**切入生态即可盈亏平衡，但真正收入在托管 SaaS 订阅（缺口 A 的 $50–300/mo 服务带）。

## 修订记录（对照委托方底稿）

> 底稿指委托方提供的 189 行版本（其 8 条结论已并入上文各节）。以下为本次复核发现的修正项：

| # | 底稿表述 | 修订 | 依据 |
|---|---|---|---|
| 1 | GitLab「FY2025 全年收入约 $742M」 | **FY2025 营收 $759M**（+31%）；FY2026 营收 $955M（+25.8%），财报口径「跨 $1B ARR」是 **ARR 而非营收**，两者并列勿混 | SEC 10-K（2025-03）/ SEC 8-K + stockanalysis（2026-03/08） |
| 2 | Cursor「2025 年达到约 $1B ARR」 | 标注**多口径冲突**：$1B（2025 dev.to 单源）、$200M（2026 行业报告）、$2B ARR/$60B（2026-04/05 agentmarketcap 低可信）——公司未官方披露，一律标传闻 | 三源并列 |
| 3 | ClawHub「2,857 技能中 341 恶意 + 483 可疑 ≈12%」（clawctl）与虎嗅「>1/3」两口径 | 保留并列；**补 Manifold 2026-06-19 数据**：1,508 插件中 23 个冒用 @openclaw/@clawhub 官方 scope、557 个带 scope 但非全部验证所有权，且通过平台自带扫描——口径不同（恶意统计 vs 冒名统计），不可合并 | Manifold Security / CSA / Unit 42 |
| 4 | Sentry「$3B 公司」 | 明确时点：**$3B 估值 = 2022-05 Series E（$90M）**；Getlatka「2024 ARR $100M、估值 $1.3B」与之冲突，标待验证 | Business Wire 2022-05 / Getlatka 2024 |
| 5 | Godot「2026-05 官方商店上线，付费未开放」 | 补充官方财务基线：**Godot 基金会 2023 收入 €465,667**（企业赞助 54% €248K / 个人捐赠 28% €133K / SFC 一次性拨款 18% €84K）——引擎免费 + 捐赠的模式量级参照 | Godot 基金会官方财务报告 2023 |
| 6 | 底稿未含垂直 SaaS 定价实测 | 补采（本 R1.1 缺口 A）：Floranext $30/mo、宠物美容 $29–199/mo、SPA/美业 $19.95–410/mo、中文美业美管加 ¥1,500–5,000/年、AI 接听 $50–300/mo | 本 R1.1 全部来源 |
| 7 | 底稿 MCP 定价实例仅 Anysite | 补采（本 R1.1 缺口 B）：Rumblingb $19/$99、MCPize $9–29 + 抽成 15–20%、whoffagents $19、Smithery 并入 Arcade.dev 定价不可得 | 本 R1.1 全部来源 |

### R1.1 新增证据来源
- Floranext 定价 — softwaresuggest（2026-08-16 更新）：https://www.softwaresuggest.com/floranext
- 宠物美容定价对比（逐厂商核实）— Twizzlo 2026-07-28：https://twizzlo.com/articles/best-pet-grooming-software/
- SPA 软件定价对比（逐厂商核实）— Twizzlo 2026-08-14：https://twizzlo.com/articles/best-spa-management-software/
- 美管加收费 — 思迅天店 2025-09-04：https://www.td365.com.cn/newsportal/detail/16568
- AI 电话接听成本 — NextPhone 2026-08-11：https://www.getnextphone.com/blog/phone-answering-costs
- Rumblingb《The Math on 61 MCP Servers, 0 Employees and $19/mo Subscriptions》— DEV 2026-06-11：https://dev.to/rumblingb/the-math-on-61-mcp-servers-0-employees-and-19mo-subscriptions-o4i
- MCPize《MCP Pricing Guide: How Much to Charge for Your MCP Server (2026)》— 2025-10-15：https://mcpize.com/blog/mcp-pricing-guide
- whoffagents《Pricing an MCP Server in 2026: Why We Charge $19/mo》— DEV：https://dev.to/whoffagents/pricing-an-mcp-server-in-2026-why-we-charge-19mo-when-the-market-average-is-0-nig
- Smithery 官方定价页（无公开数字，并入 Arcade.dev）— https://smithery.ai/pricing

### R1.1 新增置信度说明
- **高置信（逐厂商官方定价页核实）**：宠物美容 $29–199/mo、SPA/美业 $19.95–410/mo、AI 接听 $50–300/mo（Twizzlo/NextPhone 均标注核实日期与厂商名）
- **中置信**：Floranext $30/mo（第三方目录转引厂商定价）；美管加 ¥1,500–5,000/年（行业媒体引官网）；MCPize 抽成 15–20%（平台自述）
- **不可得**：FloristWare 定价、Smithery 定价（并入 Arcade.dev 后联系制）、宏达花店进销存价格、MoeGo 定价（第三方报 $79/$149/$249 未验证）
