# 花店驾驶舱 · 数据设计文档 v0.2（含数据契约与缺口）

> 数据调查员 4787d717 · 2026-08-18 · 与运营需求包（aa528267）合并版
> 数据源口径：waimai 工具实测 + 运营侧依赖（events/review_daily.json/charge.js/alerts）

## 一、数据源可用性矩阵（按运营需求包指标逐项核对）

### P1 可编辑周报指标
| 指标 | 数据源 | 可用性 | 粒度 | 刷新 | 缺口 |
|------|--------|--------|------|------|------|
| 周订单 | waimai_report(days=7) | ✅ 实测（新订单事件） | 按店/按日 | 小时 | — |
| **销售额** | export_report 原语 / events | ⚠️ report 无金额字段 | 按店 | 日 | **缺口：需 events/导出补销售额字段** |
| 差评分类 | waimai_review_daily | ✅ 实测（好评/中评/差评+分类） | 按店/按日 | 每日 | — |
| **推广 ROI** | waimai_traffic + 推广费 | ⚠️ 有曝光/转化，无费用/收入比 | 单店 | 小时 | **缺口：推广费数据源未明确（charge.js 疑含）** |
| **新客** | events | ⚠️ 无直接新客指标 | — | — | **缺口：需 events 首单标记或平台数据** |
| 高峰时段 | waimai_report | ✅ 实测（高峰时段） | 按店 | 小时 | — |
| 环比 | dify_report（"较上周期"） | ✅ 部分（曝光/转化环比） | 单店 | 日 | 订单环比需自算 |

### 图表数据契约（3 图表位）
| 图表 | 数据契约（JSON） | 数据源 |
|------|-----------------|--------|
| 营业额趋势（7 天） | `[{date, store, revenue}]` | export_report/events（缺口补） |
| 差评分类 | `[{category, count, store}]` | waimai_review_daily |
| 推广 ROI | `[{period, spend, revenue, roi}]` | charge.js（缺口核对）+ export |

### P2 驾驶舱主页卡片（8 卡 → 运营需求布局）
| 卡 | 数据源 | 契约 |
|----|--------|------|
| 顶部4卡：订单/营业额/待回复/告警 | report/review_daily(待回复)/alerts | `{orders, revenue, pendingReplies, alerts}` |
| 中部：评价/流量 | review_daily / traffic | `{reviewStats, traffic:{exposure,conv}}` |
| 下部：7天趋势/营销 | report(7d)/capabilities+活动页 | `{trend:[7d], promo:[active]}` |

### 促销工作流（P1）
目标→选品(query_orders/export_products)→定价(change_price)→文案(模板)→海报(AI配图)→方案卡(确认)→一键上下架(on/off_shelf)——high 动作确认门控保留（见 v0.1 风险机制）。

## 二、数据源缺口清单（需运营/实现侧确认）
1. **销售额**：waimai_report 无金额字段——需 export_report(财务) 或 events 金额聚合，或运营侧补
2. **推广 ROI**：推广费数据源未定位（charge.js 疑似含曝光/费用，需核）；ROI 需收入(export)÷费用
3. **新客数**：无直接指标——需 events 首单标记/平台「新客」口径
4. **营业额趋势**：依赖销售额补全（同缺口 1）
5. 待确认：charge.js 数据可用性（运营侧依赖，我无直接工具）

## 三、刷新频率与调度建议
| 层级 | 频率 | 工具 |
|------|------|------|
| 实时卡（状态/告警） | 5 分钟 | waimai_state / waimai_alerts |
| 运营卡（订单/消息） | 15-30 分钟 | waimai_report |
| 流量/评价 | 小时/每日 | waimai_traffic / waimai_review_daily |
| 周报/关键词 | 每周 | dify_report / waimai_keywords |

## 四、双 agent 回传（P3，详见 flower-cockpit-ipollowork-ref.md）
产物契约建议：`{type, data, editable, confirm_required, audit}`——生成 agent 产出 → 用户编辑 → 回传执行（high 动作带 confirm）。

## 五、待办（实现侧 1e54d56d 排期前确认）
- [ ] 销售额/新客/ROI 数据源补全（运营侧 events/charge.js 核对）
- [ ] 周报模板字段绑定（占位符 ↔ 指标）
- [ ] 驾驶舱卡片 JSON schema 定稿
