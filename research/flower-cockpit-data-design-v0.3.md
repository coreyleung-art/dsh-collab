# 花店驾驶舱 · 数据设计文档 v0.3（数据契约终稿）

> 数据调查员 4787d717 · 2026-08-18 · 与运营需求包（aa528267）合并版 · v0.3 定稿（3 项缺口数据源已确认）

## 一、数据源可用性矩阵（终稿）

### P1 可编辑周报指标（全部有源）
| 指标 | 数据源（定稿映射） | 粒度 | 刷新 | 备注 |
|------|-------------------|------|------|------|
| 周订单 | waimai_report(days=7) | 按店/按日 | 小时 | ✅ |
| **销售额** | **双源：①报表下载「门店成交明细」（权威，营业额/实付单均价全店全量）②events.firstItem 含「合计¥」实付金额（实时趋势，非结构化需正则，仅店2近期有）** | 按店 | 报表日/events 实时 | 趋势用 events，对账用报表 |
| 差评分类 | waimai_review_daily | 按店/按日 | 每日 | ✅ |
| **推广 ROI** | **charge.js fetchFeeFlow（订单级流水：扣款/随单返/充值，日聚合）** | 按店/按日 | 日 | ROI=订单金额÷净投入（扣款−随单返）；周=日求和；初蘅 8-16 实测 35.7 倍 |
| **新客占比** | **/api/business/module customer（顾客分析页：新客/老客占比）** | 全店 | 日 | 无客户身份字段（订单号全局单号、客户名脱敏） |
| 高峰时段 | waimai_report | 按店 | 小时 | ✅ |
| 环比 | dify_report（"较上周期"）+ 自算 | 单店 | 日 | 订单环比自算 |

### 图表数据契约（3 图表位）
| 图表 | 数据契约（JSON） | 数据源（定稿） |
|------|-----------------|----------------|
| 营业额趋势（7 天） | `[{date, store, revenue}]` | events 合计¥（趋势）+ 报表成交明细（对账） |
| 差评分类 | `[{category, count, store}]` | waimai_review_daily |
| 推广 ROI | `[{period, spend, revenue, roi}]` | charge.js fetchFeeFlow（spend=净投入） |

### P2 驾驶舱主页卡片
| 卡 | 数据源（定稿） | 契约 |
|----|----------------|------|
| 顶部4卡：订单/营业额/待回复/告警 | report / events合计¥+报表 / review_daily(待回复) / alerts | `{orders, revenue, pendingReplies, alerts}` |
| 中部：评价/流量 | review_daily / traffic(charge.js 曝光进店) | `{reviewStats, traffic}` |
| 下部：7天趋势/营销 | report(7d) / capabilities+活动页 | `{trend:[7d], promo:[active]}` |
| 顾客分析（新客） | /api/business/module customer | `{newCustomerRatio, oldCustomerRatio}` |

## 二、数据源缺口（已全部闭合）
1. 销售额 → 双源定稿（报表权威 + events 实时）✅
2. 推广 ROI → charge.js fetchFeeFlow 定稿 ✅
3. 新客占比 → customer 模块页面数据定稿 ✅

## 三、刷新频率与调度建议（不变）
实时卡 5 分钟 / 运营卡 15-30 分钟 / 流量评价 小时-每日 / 周报关键词 每周

## 四、双 agent 回传（P3，详见 flower-cockpit-ipollowork-ref.md）
产物契约：`{type, data, editable, confirm_required, audit}`——生成→编辑→回传执行（high 动作带 confirm）

## 五、待办（实现侧 1e54d56d）
- [x] 三缺口数据源确认
- [ ] events 合计¥正则提取实现（实时趋势）
- [ ] charge.js fetchFeeFlow 聚合实现（ROI）
- [ ] customer 模块对接（新客占比）
- [ ] 周报模板占位符绑定 + 驾驶舱卡片 schema 定稿
