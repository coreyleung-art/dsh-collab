# 美团闪购商家版 · 报表导出体系深度学习（12 报表全量）

> 学习：a3bc8cba · 2026-08-23 · 实测初蘅 9201（acctId 280637477 / poiId 32768686）
> 入口：manageAnalysis/pc#/report（报表下载页）· taskCreator API（页面内 fetch 携带签名上下文）
> 报表页结构：5 分类 tab（交易/订单/流量/商品/服务）× 每类 2-4 报表 = **12 个报表**

## 一、报表全景与参数速查

| 分类 | 报表 | radio value | taskCreator reportType | type | selectIndex 说明 | 下载方式 | 实测 |
|---|---|---|---|---|---|---|---|---|
|---|---|---|---|---|---|---|
| 交易 | 门店财务明细 | poiFinanceDetail | **daySgBusinessAnalysisDetail** | 61 | indexGroup 1001(14项)+1002(6项)=26列 | taskList 异步（2-4min）| ✅已验证 |
| 交易 | 门店成交明细 | poiDataDetail | poiDataDetail | **5** | **无 selectIndex**（默认全字段 41 列）| **浏览器直下** | ✅已验证 |
| 交易 | 配送费用数据 | deliveryFee | deliveryFee | 5/61 均通 | 0 指标 | 直下/taskList | ✅code=0 |
| 订单 | 商品数据 | product | commodityData | 61 | indexGroup 1001(37项)=43列 | taskList 异步 | ✅已验证 |
| 订单 | 问题订单数据 | order | order | 61 | 中文名 12 列（空selectIndex通）| taskList | ✅code=0 |
| 流量 | 门店流量明细(旧) | poiTrafficDetail | poiTrafficDetail | ? | indexGroup 1001(18项)试败 | 待测 | ⚠️失败 |
| 流量 | 流量明细(新) | trafficDetail | trafficDetail | 61 | 英文 key（PoiViewUv 等 9 项，空SI通）| taskList | ✅code=0 |
| 流量 | 流量渠道明细(新) | trafficChannelDetail | flowAnalysisChannelByAcctPoiAndDayDetail | **66** | channel24（indexName+indexId 24项）| taskList | ✅已验证 |
| 商品 | 商品分类销售 | hotSaleClassify | hotSaleClassify | 5 | 中文名 10 项（空SI通）| 直下 | ✅code=0 |
| 商品 | 商品销售 | hotSaleSingle | hotSaleSingle | 5 | 中文名 14 项（空SI通）| 直下 | ✅code=0 |
| 服务 | 评价数据 | evaluate | evaluate | ? | 中文名 18 项试败 | 待测 | ⚠️失败 |
| 服务 | 售后订单数据 | afterSalesOrderDetails | afterSalesOrderDetails | 61 | 中文名 20 项（空SI通）| taskList | ✅code=0 |

**关键机制**：
1. **radio value ≠ reportType**：poiFinanceDetail(UI) → daySgBusinessAnalysisDetail(后端) —— 最大坑！
2. **两种下载通道**：type=61 走 taskList 异步（fileUrl 30 天有效）；type=5 + flowOpen=4 走浏览器直下（文件名 `日期-日期-店铺-报表名-ts.csv`，不在下载列表展示）
3. **selectIndex 三种形态**：indexGroup+indexId（财务/商品/流量旧）、无 selectIndex 默认全字段（成交明细）、中文/英文 key（部分报表）

## 二、各报表字段逻辑与业务关联

### 1. 门店财务明细（26 列）—— 商家实收口径 ★核心
- 收入/实付交易额/佣金/配送服务费/营业支出/商家补贴/营业额/取消单系列
- **业务**：回答「商家实收多少」——收入=实收，佣金=平台抽成，取消单损失可见
- 验证：初蘅 8/5 收入¥1309.32/实付¥2006.61/佣金¥245.04
- 已固化 lib/finance-export.js + 原语 finance_export(1980)

### 2. 门店成交明细（41 列）—— 门店经营健康度 ★最全
- 基础：商家ID/运营组/在线状态/首次上线/营业时长
- 交易：推单数/有效订单/原价/实付/商家补贴
- **服务质量**：拒单数/超时未接单/取消不告知/缺货退款/少送错送/质量问题退款/拣货超时/骑手等待
- **客服**：IM 会话/回复/回复率/1分钟回复
- **口碑**：差评/投诉/商家评分/商品评分/配送评分/配送时长
- **业务**：一表看全店运营健康度——服务问题订单=拒单+超时+取消+退款 是重点监测项

### 3. 商品数据（43 列）—— 订单×商品明细 ★已验证
- 订单基础+金额+商品+退款+活动+配送（一行=订单中一个商品 SKU）
- **业务**：「商品×日期×销量」分析；已固化 order-export.js

### 4. 问题订单数据（12 列）—— 问题单专项
- 订单编号/退款金额/退款商品/商家服务问题/退款类型/平台介入/缺货退款
- **业务**：追踪问题订单（退款/平台介入=风险信号）

### 5. 门店流量明细旧（18 指标）—— 流量漏斗
- 曝光/入店/下单 × 人数/次数/转化率 × 新客/老客
- **业务**：曝光→入店→下单 漏斗；新老客结构

### 6. 流量明细新（9 指标）—— 新版漏斗
- 曝光/入店/加购/下单人数 + 各环节转化率（含加购）
- **业务**：比旧版多「加购」环节，漏斗更完整

### 7. 流量渠道明细新 —— 渠道拆分
- 同新流量指标 + 渠道维度
- **业务**：搜索/推荐/活动等渠道贡献拆分

### 8. 商品分类销售（10 指标）—— 类目表现
- 类目名称/原价/实际销售额/占比/销量/曝光率/动销率/售罄率
- **业务**：类目健康度（动销率+售罄率=选品优化依据）

### 9. 商品销售（14 指标）—— 单品表现
- 商品名/原价/实际销售额/补贴/销量/价格区间/曝光/下单/订单量/交易额/售卖时长/条码/SKU
- **业务**：单品排行与转化（曝光→下单→订单量）

### 10. 评价数据（18 列）—— 评价明细
- 提交日期时间/订单/商品/用户评价/追评/商家回复/评分/子维度/配送评分/点踩率/退款
- **业务**：评价全量明细（差评识别/回复监督/评分分析）

### 11. 售后订单数据（20 列）—— 售后全流程
- 售后发起/展示订单号/退款类型/售后类型/原因/金额/商品/发起方/审核/处理时长/极速退款/退货免运费/平台判责
- **业务**：售后漏斗（发起→审核→判责），商责率=服务质量核心指标

### 12. 配送费用数据 —— 配送成本
- 0 指标（无字段选择），待实测确认

## 三、字段逻辑通则

1. **金额字段**：原价（标价合计）/实付（顾客支付）/补贴（平台+商家）/收入（商家实收）四级口径
2. **订单状态**：完成/已处理/取消（取消含原因分类：用户/商家/配送/其他）
3. **服务质量指标**：拒单/超时未接/取消/缺货/少送错送/质量问题 → 平台判商责的依据
4. **时间字段**：下单/完成/售后发起/退款处理 全覆盖
5. **编码**：导出 CSV 为 **gb18030**（Excel 打开需注意）

## 四、已固化资产

| 资产 | 报表 | 状态 |
|---|---|---|
| lib/order-export.js + 原语 1978 | 商品数据 | ✅ 生产可用 |
| lib/finance-export.js + 原语 1980 | 门店财务明细 | ✅ 生产可用 |
| 本文档 | 全 12 报表 | ✅ 本次沉淀 |

## 五、当前状态（2026-08-23 更新：12/12 全破解 ✅）

1. ✅ 12/12 报表全部破解：evaluate→type5 direct（评价分析明细，20 列含四维评分）；poiTrafficDetail→poiSgFlowAnalysisDetail（type61）
2. ✅ 通用导出器 lib/report-export.js 全部可用（direct UI 流程 + type61 taskList 轮询）
3. ✅ 12 原语 report_export_* 注册（id 1981-2001）
4. ✅ trafficChannelDetail 完整验证：type66 + flowAnalysisChannelByAcctPoiAndDayDetail + channel24（indexName+indexId）+ specialParams；26 列 = 渠道(搜索等) × 流量漏斗8项 × 整体/门店新客/门店老客三维度
5. 遗留：direct 通道偶发超时判定待调优（功能已可用）
