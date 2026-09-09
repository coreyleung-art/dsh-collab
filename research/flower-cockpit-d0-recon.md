# 花店驾驶舱 D0 数据采集层 · 前置侦察报告

> GUI 插件开发 1e54d56d · 2026-08-18 · 基于数据契约 v0.3 的实现前置验证

## 一、数据源可用性实测（2026-08-18）

| 数据源 | 工具 | 实测结果 | D0 用途 |
|--------|------|---------|---------|
| 门店状态 | waimai_state | ✅ 10 店在线（美团 6/京东 2 登出/抖音 2） | 8 卡「告警」 |
| 7 天报告 | waimai_report(days=7) | ✅ 10 店聚合（订单/状态/消息/高峰） | 周报「高峰时段/环比」 |
| 事件流 | waimai_scenarios | ✅ 接口在线（近 1h 无异常） | D0-1 events 正则输入 |
| 报表导出 | waimai_action(export_report) | ✅ 原语可用（low risk） | 销售额「报表权威源」 |
| 流量 | waimai_traffic | 待测（storeId 默认 8） | 8 卡「流量」+ 周报曝光 |
| 评价 | waimai_review_daily | 待测 | 8 卡「评价」+ 差评分类图 |
| 关键词 | waimai_keywords | 待测 | 8 卡「关键词」 |

## 二、三缺口数据源实现路径（v0.3 定稿映射）

1. **events 合计¥正则**（实时趋势）：
   - 输入：events 流（声音事件+客户消息，waimai_scenarios 同源）
   - 提取：firstItem 含「合计¥」实付金额 → 正则 `/合计¥?\s*([\d,.]+)/`
   - 输出：`[{date, store, revenue}]` 7 天趋势
   - 已知：仅店2（体育东）近期有数据

2. **charge.js fetchFeeFlow 聚合**（ROI）：
   - 输入：推广充值页（waimai_focus promo_charge 聚焦）CDP 抓取 charge.js fetchFeeFlow
   - 口径：净投入 = 扣款 − 随单返；ROI = 订单金额 ÷ 净投入；周 = 日求和
   - 输出：`[{period, spend, revenue, roi}]`

3. **customer 模块对接**（新客占比）：
   - 输入：/api/business/module customer（顾客分析页）CDP 抓取
   - 输出：`{newCustomerRatio, oldCustomerRatio}`

## 三、D0-4 dataProvider 统一接口设计

```ts
interface DataProvider {
  id: string;                    // 'report' | 'events-revenue' | 'roi' | 'customer' | 'traffic' | 'review' | 'keywords'
  refresh(): Promise<CacheEntry>; // 拉取+缓存
  get(): CacheEntry;              // 读缓存
}
interface CacheEntry {
  data: unknown; fetchedAt: number; ttlMs: number; stale: boolean;
}
```
- 刷新频率（v0.3）：实时卡 5min / 运营卡 15-30min / 流量评价 小时-每日 / 周报关键词 每周
- 调度：复用 workflow-capture 已实现 cron 调度器（不新增 launchd 项）

## 四、风险与依赖

- charge.js/customer CDP 抓取依赖运营侧页面可访问（waimai_focus 已具备聚焦能力）
- events 数据仅店2 有——趋势图以店2 为样例，其他店走报表对账
- 京东 2 店登录态失效（B1 已批补登，恢复后数据才完整）

## 五、D0 子任务排期（3-4d）

- D0-1 events 正则提取（1d）
- D0-2 charge.js fetchFeeFlow 聚合（1d）
- D0-3 customer 模块对接（1d）
- D0-4 dataProvider 统一接口 + 缓存 + 刷新调度（1d）
