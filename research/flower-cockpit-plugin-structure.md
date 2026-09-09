# 花店驾驶舱插件 · 结构 + Collector API 文档

> GUI 插件开发 1e54d56d · 2026-08-18 · 供知识库 doc-ingest（插件级实现参考）

## 一、插件结构（dsh-plugin-flower-cockpit v0.1.0）

```
dsh-plugin-flower-cockpit/
├── src/
│   ├── index.ts          # host：/flower-cockpit/api/state + artifacts API（D2）
│   └── client/index.tsx  # client：驾驶舱Tab（8卡）/ 经营周报Tab / 促销方案Tab
├── collector/            # 数据采集层（D0/A/B 脚本）
│   ├── events-revenue.js # D0-1 events 合计¥正则提取
│   ├── roi.js            # D0-2 charge.js fetchFeeFlow ROI 聚合
│   ├── customer.js       # D0-3 customer 模块解析（占比/人数）
│   ├── data-provider.js  # D0-4 7源统一接口（缓存+ttl+refresh）
│   ├── report-template.js# A1 周报模板引擎（五段+占位符+图表位）
│   ├── report-skeleton.js# A2 结构化骨架（诊断/联动/图表）
│   ├── promo.js          # B1 促销状态机（方案卡+审计+dry-run）
│   ├── promo-exec.js     # B2 促销编排（三重门控）
│   └── artifact.cjs      # D1 产物契约（{type,data,editable,confirm_required,audit}）
├── lib/                  # 构建产物（index.js host + client.js ModuleLoader 格式）
├── scripts/build.mjs     # 构建（tsc + esbuild + ModuleLoader 包装）
└── cordis.patch.yml      # bundle 注册（id: flower-cockpit）
```

## 二、数据流

```
waimai_* 工具 / charge.js / customer 页
        ↓ (collector 脚本)
~/.dsh/flower-cockpit/data/*.json
        ↓ (dataProvider 统一接口)
/flower-cockpit/api/state (host webServer)
        ↓
client UI（驾驶舱Tab 8卡 / 周报 / 促销）
        ↓ (D2 artifacts API)
跨 agent 产物回传消费
```

## 三、Collector 脚本 API

| 脚本 | 命令 | 输出 |
|------|------|------|
| events-revenue.js | `node events-revenue.js --input <analyze.txt>` | events-revenue.json（{store, revenue, orderCount}） |
| roi.js | `node roi.js --input <fee-flow.txt> [--revenue N]` | roi.json（{period, spend, roi}） |
| customer.js | `node customer.js --input <page.txt>` / `--new N --old N` | customer.json（{newCustomerRatio, oldCustomerRatio}） |
| data-provider.js | `list|get <id>|refresh <id>|refresh-all|export` | provider-cache.json / cockpit-export.json |
| report-template.js | `--input <report.md> [--store S] [--period P]` | report-template.json（五段+placeholders+charts） |
| report-skeleton.js | `--template <tpl.json>` | report-skeleton.json（diagnosis/linkages/charts） |
| promo.js | `create|list|get|transition|audit` | promos.json（方案卡+状态机+审计） |
| promo-exec.js | `plan|execute|audit <promoId>` | promos.json（编排执行） |
| artifact.cjs | `validate|wrap|list` | artifacts.json（契约产物） |

## 四、Host API（webServer）

- GET /flower-cockpit/api/state → { report, promos, dashboard, dataDir }
- GET /flower-cockpit/api/artifacts → { artifacts, contract }
- POST /flower-cockpit/api/artifacts → 契约校验入库（400 拒绝非法）

## 五、关键契约

- 数据契约 v0.3：~/dsh-collab/research/flower-cockpit-data-design-v0.3.md
- 产物契约：{type, data, editable, confirm_required, audit}
- 促销状态机：draft→confirmed→executing→done（+rejected/cancelled/failed）
- ROI 口径：净投入=扣款−随单返；ROI=订单金额÷净投入
