# AI 时代按结果付费（Outcome-Based Pricing）调研报告

> 调研：数据调查员 4787d717 · 2026-09-06 · 需求：用户「调研 AI 时代的按结果付费」
> 方法：web_search 多轮（中英 12+ 次）+ 关键原文抓取 6 篇（Intercom/Salesforce 韩媒/零犀/网易/东方财富/36氪摘要）
> 衔接：本地已有 open-core-mcp-subscription-r1 / vertical-saas-pricing-band-r1（传统佣金/订阅带）
> 用途：花店 AI 运营官产品定价设计参考（AI 时代结果付费新模式）
> 结论有效期：2026-09（定价模型快速演进中）

---

## 一、核心结论

**AI 时代的按结果付费（pay-for-outcome / pay-per-resolution）已从概念走向落地**——2025-2026 主流厂商密集转向：Salesforce Agentforce Help Agent（$2/单解决）、HubSpot Breeze（pay-per-result）、Intercom Fin（$0.99/outcome）、Zendesk（Verified Resolution）都在做。

**但反共识分析指出：纯 pay-for-outcome 不是终局**——「基础订阅 + 用量阶梯 + 少量按结果」三层结构才是 AI Agent 商业化终点（网易/OPC Agentic Economy 深度分析）。

**对花店 AI 运营官的启示**：结果付费（如按「多接的订单」「省的人工小时」抽成）天花板高于月费制，但需要**可验证产物 + 可靠归因**——这正好是本地 SaaS 交叉验证报告（¥300-5,000 价格带 + BloomNation 28% 佣金）的升级方向。

---

## 二、AI Agent 定价模型全景（2026）

Intercom 调研 7 家头部 AI 客服 Agent，归纳 **5 种计费模型**：

| 模型 | 计费单位 | 代表 | 公布价 | 特点 |
|---|---|---|---|---|
| **Outcome-based（按结果）** | 成功解决一次 | Intercom Fin | **$0.99/outcome** | 成本直接绑定价值 |
| **Per resolution（验证解决）** | 验证的解决 | Zendesk AI | $1.20-1.50/verified（承诺）/ $2.00 现付 | "解决"定义因厂而异 |
| **Per conversation（按对话）** | 每会话 | Salesforce Agentforce | $2.00/conversation | 失败转人工也付费 ⚠️ |
| **Per action（Flex Credits）** | 单个动作 | Salesforce Agentforce | $0.10/action（20 credits） | 替代按会话 |
| **Per session/interaction** | 每互动 | Freshdesk Freddy | 未公布 | 多触点问题多收费 ⚠️ |
| **企业定制合约** | 不可比 | Ada/Sierra/Decagon | 销售报价 | 完全黑盒 |

**关键洞察**：相同贴牌价在不同模型下账单差异巨大——「$1/互动」按会话计费 vs 按解决计费，若 AI 解决率 60%，按会话你为失败的 40% 也付费。

## 三、标志性案例（2025-2026 落地）

### 3.1 Salesforce Agentforce Help Agent — 按解决付费（$2/单）
- **来源**：[DigitalToday 韩媒](https://www.digitaltoday.co.kr/cn/view/74980/salesforce-unveils-ai-agent-for-customer-support-charges-only-when-issues-are-resolved) + [CX Today](https://www.cxtoday.com/ai-automation-in-cx/salesforce-introduces-prebuilt-service-agent-with-outcome-based-pricing-model/)
- **机制**：Help Agent 端到端独立解决问题才收费，**$2/次解决**；不再按功能调用/语音时长计费
- **意义**：Salesforce（CRM 巨头）带头转向「按结果」，证明企业接受结果定价

### 3.2 HubSpot Breeze — pay-per-result
- **来源**：[CMSWire](https://www.cmswire.com/customer-experience/hubspot-shifts-breeze-ai-agents-to-pay-per-result-pricing/)（403 未抓全文，摘要级）
- **机制**：Breeze AI Agent 成本与结果绑定而非用量
- **意义**：营销 SaaS 龙头跟进，验证「结果付费」在营销场景可行

### 3.3 零犀科技 — Agentic Sales 结果交付（国内标杆）
- **来源**：[投资界](https://news.pedaily.cn/20260320/125854.shtml) + [东方财富](https://finance.eastmoney.com/a/202607033793483451.html)
- **成果**：某头部保险公司**新增保费近 20 亿**；某银行累计 **3.79 万户小微授信**；汽车 CaRhino 按试驾邀约/成交付费
- **模式**：客户不为调用量付费，只为业务成果付费（保险=保费规模、汽车=试驾/成交）
- **技术底座**：因果大模型（非黑箱）——可靠性需 98-99%+，输出可溯源（"刚生二胎+房贷+年收入50万"→因果链推理出高额寿险需求）
- **意义**：国内首个大模型应用规模盈利，走「卖结果不卖工具」路径

### 3.4 Intercom Fin — $0.99/outcome（原生化先例）
- **来源**：[Intercom Learning Center](https://www.intercom.com/learning-center/ai-customer-service-agent-pricing-comparison)
- **机制**：Fin 每成功解决一单 $0.99，无需绑定 helpdesk
- **意义**：AI 客服原生玩家最早做纯结果付费

## 四、反共识分析：为什么纯 pay-for-outcome 不是终局

**来源**：[网易·Agent 商业化终局三层结构](http://www.163.com/dy/article/KRAN406O05568W0A.html)（OPC Agentic Economy 创业分析）

三个扎心真相：
1. **pay-for-outcome = 完美价格歧视，但三大零成本前提现实不满足**：
   - 零测量成本 ❌（AI 只降客观数据处理成本，解决不了多因素归因成本）
   - 零验证成本 ❌（怎么证明"结果"是你的贡献？）
   - 零谈判成本 ❌（用户主观价值认知差异大）
   - → 强行推 → 供方挑容易的单做 → 市场交易量缩水
2. **测量越便宜，合约越往粗颗粒走**（历史反复验证）：
   - 电信按分钟 → 无限量包月
   - SaaS 永久授权 → 按座订阅
   - → 不会越来越细
3. **终局 = 「基础订阅 + 用量阶梯 + 少量按结果」三层结构**，非单一 pay-for-outcome

**新视角补充**（[东方财富·SaaS→RaaS](https://finance.eastmoney.com/a/202606053761911529.html)）：全球效果广告市场近 ¥9000 亿，但 **70%+ 预算花在"可能有用但无法证明有用"的工具**——AI Agent 结果付费本质是把软件从 SaaS 推向 RaaS（Results-as-a-Service，结果即服务）。

## 五、AI 按结果付费的适用条件与挑战

### 适用条件（何时结果付费可行）
| 条件 | 说明 | 反例 |
|---|---|---|
| **结果可客观测量** | 单一/清晰 KPI（保费/成交/解决数） | 多因素归因的场景（品牌建设） |
| **AI 影响可隔离** | 能区分"是 AI 的功劳" | 多渠道混合营销 |
| **结果周期短** | 短期内可见（订单/试驾/解决） | 长周期价值（LTV/复购） |
| **供方技术可靠** | 98-99%+ 可靠性 | 幻觉率高会击穿成本 |

### 核心挑战（三座大山）
1. **归因**：多因素项目里怎么证明结果归 AI？→ 零犀用因果大模型、Salesforce 用端到端独立解决定义
2. **测量/验证**：什么算"结果"？谁定义？→ Zendesk "Verified Resolution" 三档、HubSpot 绑定结果
3. **道德风险**：供方挑简单单做（cherry-picking）→ 需合约约束 + 兜底条款

## 六、对花店 AI 运营官的落地启示（衔接本地定价报告）

| 定价层 | 模式 | 借鉴 | 落地建议 |
|---|---|---|---|
| 基础层 | 订阅（¥300-1,000/月） | 三层结构第 1 层 | 已有垂直定价带报告支持 |
| 用量层 | 阶梯（多店/多平台） | 三层结构第 2 层 | 跨平台聚合溢价 |
| **结果层** | **按结果抽成** | Salesforce $2/单 · BloomNation 28% · 零犀保费分成 | **按「多接的订单数」或「省的人工小时」抽成**——锚定可验证产物 |
| 旗舰层 | 结果分成 | BloomNation 28% GMV 佣金 | SaaS 交叉验证已建议补此档 |

**关键差异化**：国内代运营骗局带（¥240/月承诺保底）污染了「按结果」信任——花店 AI 运营官的结果付费必须**交付可验证产物**（实时看板/订单流水/AI 回复记录）+ **清晰归因**（哪些订单是 AI 拉的），这正是三层结构「少量按结果」的正确用法，而非全押 pay-for-outcome。

## 七、信源列表

1. [Intercom: AI Agent Pricing Compared (Fin/Zendesk/Agentforce)](https://www.intercom.com/learning-center/ai-customer-service-agent-pricing-comparison) — 5 模型对比表
2. [Salesforce Introduces Help Agent with Outcome-Based Pricing (CX Today)](https://www.cxtoday.com/ai-automation-in-cx/salesforce-introduces-prebuilt-service-agent-with-outcome-based-pricing-model/)
3. [Salesforce 客服 AI 代理按解决计费 (DigitalToday 韩媒)](https://www.digitaltoday.co.kr/cn/view/74980/) — $2/单
4. [HubSpot Breeze 转 pay-per-result (CMSWire)](https://www.cmswire.com/customer-experience/hubspot-shifts-breeze-ai-agents-to-pay-per-result-pricing/)
5. [零犀科技 Agentic Sales 可量化增长 (投资界)](https://news.pedaily.cn/20260320/125854.shtml) — 保费 20 亿/授信 3.79 万户
6. [Agent 商业化终局三层结构 (网易)](http://www.163.com/dy/article/KRAN406O05568W0A.html) — 反共识分析
7. [SaaS→RaaS 定价逻辑改写 (东方财富)](https://finance.eastmoney.com/a/202606053761911529.html) — 效果广告 70% 无法证明
8. [CloudZero AI ROI: $5.21 skill → 5 meetings](https://www.cloudzero.com/blog/ai-roi-dispatch-skill-closed-meeting/) — 微观 ROI 实证
9. [Futurum: Outcome-based pricing playbook 分析](https://futurumgroup.com/press-release/are-outcome-based-and-hybrid-ai-pricing-models-rewriting-the-vendor-playbook/)
10. [明略科技按结果收费实验 (Runwise)](https://runwise.co/corporate-innovation/genai/272846/)

---
*调研：4787d717 · 2026-09-06 · 中英 12+ 检索 + 6 原文 · J46 官方优先/来源可溯*
