# festival-pipeline · 节日备货流水线

> 版本 1.0.0 · 2026-09-01 · 学习侧固化（a3bc8cba）· 教师节事件资产沉淀 · 老板指示标准化工具化
> 触发词：节日备货/备货流水线/价格雷达/成本核算/款式BOM/报名核查/双旦/情人节备货

## 用途

节日备货全流程流水线工具：**价格雷达 → 成本核算 → 报名核查 → 款式 BOM** 四段闭环。
基于教师节事件沉淀（coze 价格雷达 + 真实成本方法 + apply-status-check 报名核查 + 款式 BOM 模板），
双旦（12/24-1/1）/情人节（2/14）等节日可直接复用。

## 流水线四段

| 段 | 功能 | 数据源 |
|----|------|--------|
| ① 价格雷达 | 花材市场价监控 | coze 价格雷达日报（~/.dsh/datasets/coze-archive/花材价格监控中心/） |
| ② 成本核算 | BOM × 单价 → 成本/毛利 | 价格雷达 + 款式 BOM |
| ③ 报名核查 | 活动报名状态权威判定 | getInviteList enterTime>0（apply-status-check） |
| ④ 款式BOM | 款式设计 → 花材/数量/配饰/包装 | 模板（花束/抱抱桶/花盒）+ 款式图配方 |

## 使用

### CLI
```bash
node scripts/festival-pipeline.js radar            # 价格雷达（最新花材价）
node scripts/festival-pipeline.js cost '<BOM JSON>' # 成本核算
node scripts/festival-pipeline.js bom 抱抱桶        # 款式BOM模板
node scripts/festival-pipeline.js check 9205 80125527  # 报名核查
node scripts/festival-pipeline.js plan 双旦         # 全流水线
node scripts/festival-pipeline.js selfcheck        # 自检（R030 反向用例）
```

### 模块
```js
const fp = require("lib/festival-pipeline");
fp.priceRadar();                                  // {ok, latest:{prices:[{name,price,unit}]}}
fp.costCalc({ bom: { retailPrice: 99, items: [{material:"康乃馨",qty:21,unitPrice:0.9}] } });
fp.applyCheck({ port: 9205, actId: 80125527 });   // {applied, enterTime, enteredStatus}
fp.bomBuild({ style: "束脩礼", spec: { type: "抱抱桶" } });
fp.plan({ festival: "双旦" });
```

### 成本核算示例（教师节束脩礼实测）
```
康乃馨 ×21 @0.9 = ¥18.9
玫瑰 ×5 @2.5 = ¥12.5
蝴蝶兰 ×1 @8 = ¥8
配叶 ×1 @3 = ¥3
总成本 ¥42.4 | 零售 ¥76.5 | 毛利 44.6%
```

## 设计原则

- **R030**：报名判定用权威字段（enterTime>0）；成本基于真实市场价；异常输入返回失败（null 保护）
- 全函数 selfcheck 4/4 通过（缺BOM/缺款式/空对象 → 必须失败）
- BOM 可追溯（花材/数量/配饰/包装逐项）

## 文件

- 模块：`~/meituan-multi/lib/festival-pipeline.js`
- CLI：`~/meituan-multi/scripts/festival-pipeline.js`
- 原语：`festival_pipeline`（read，id=2256）
- 数据源：`~/dsh-collab/datasets/coze-archive/花材价格监控中心/花材价格日报/`
- 报告：`docs/reports/40-节日备货流水线工具包-20260901.md`
