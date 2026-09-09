# 学习→封装→交付 自动化流水线（learn-to-tool）

> 建立：2026-08-23 · a3bc8cba 学习系统 · 用户要求「每次学习后自动封装工具给运营智能体，过程插件化工具化自动化」

## 一、机制概述

每次学习完成 → **自动封装成可复用工具 → 交付外卖运营智能体**，三步闭环：

1. **学习**：探索/探测/验证（学习侧职责）
2. **封装**：参数矩阵入库 → 通用导出器生成 → 原语注册（learn-to-tool 流水线自动执行）
3. **交付**：黑板通知运营 → 运营直接调用（确定性执行）

## 二、流水线（scripts/learn-to-tool.js）

```bash
node scripts/learn-to-tool.js              # 全量：扫描成果→校验矩阵→注册原语→交付运营
node scripts/learn-to-tool.js --only-validate  # 只校验矩阵
node scripts/learn-to-tool.js --report poiDataDetail  # 只处理单报表
```

**5 步**：
① 扫描学习成果（dsh-collab/learning/ 最新文档）
② 校验报表参数矩阵（12 报表状态：ok / probe-fail / todo）
③ 注册原语（capabilities report_export_<key>）
④ 黑板交付运营（data/ops/report-export-delivery）
⑤ 黑板状态（data/learning/learn-to-tool-pipeline）

## 三、通用报表导出器（lib/report-export.js）

```js
const re = require("lib/report-export");
const r = await re.exportReport(store, "poiFinanceDetail", { date: "20260805" });
// → { ok, file, via: "taskList"|"direct" }
re.listReports(); // 12 报表配置
```

**参数矩阵**（12 报表，学习成果）：
- 通道机制：type61→taskList 异步（2-4min）；type5+flowOpen=4→浏览器直下（确认弹窗后下载）
- radio value ≠ reportType（poiFinanceDetail→daySgBusinessAnalysisDetail）
- selectIndex 三形态：indexGroup+indexId / 无（默认全字段）/ 中文名

## 四、已注册原语（9 个，id 1981-1990）

| 原语 | 报表 | 通道 |
|---|---|---|
| report_export_product | 商品数据 | taskList |
| report_export_poiFinanceDetail | 门店财务明细 | taskList |
| report_export_poiDataDetail | 门店成交明细 | direct |
| report_export_deliveryFee | 配送费用数据 | taskList |
| report_export_order | 问题订单数据 | taskList |
| report_export_trafficDetail | 流量明细(新) | taskList |
| report_export_hotSaleClassify | 商品分类销售 | direct |
| report_export_hotSaleSingle | 商品销售 | direct |
| report_export_afterSalesOrderDetails | 售后订单数据 | taskList |

## 五、踩坑记录（重要教训）

1. **store 模块级冻结**：lib/store.js 的 DATA_ROOT 在 require 时读 env——**必须在 require 前设置 MTM_DATA_DIR**，否则写错 DB（曾写进 Library/Application Support/0/）
2. **node -e 中文编码**：命令行传中文目录会被 bash 破坏成 `0`——脚本内中文用文件 UTF-8 安全，不要用 node -e 传中文路径
3. **type5 直下需确认弹窗**：点击下载后弹「我知道了」确认框，确认后才发 taskCreator 请求
4. **文件名≠报表名**：hotSaleSingle 直下文件名为「商品热销」非「商品销售」——direct 通道检测需放宽匹配

## 六、后续优化

- direct 通道返回判定调优（等待更长/检测时间戳更新）
- 评价/流量旧 参数深挖后补入矩阵
- 流水线可挂事件驱动（学习成果落盘 → 自动触发封装交付）
