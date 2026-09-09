---
title: 花店驾驶舱项目总结
date: 2026-08-18
status: complete（待重启验证+QA 收口）
tags: [flower-cockpit, project, dsh-plugin]
---

# 花店驾驶舱项目总结

## 概述
花店智能体产品化项目（用户命名「花店驾驶舱」），借鉴 iPolloWork 对外逻辑（可编辑结果/可视化工作台/agent-first 流程），四子项 13 个交付全完成。

## 交付物
- **插件**：dsh-plugin-flower-cockpit v0.1.0（lib/index.js 4802B + lib/client.js 15960B）
- **collector 9 脚本**：events-revenue / roi / customer / data-provider / report-template / report-skeleton / promo / promo-exec / artifact
- **数据产物**：~/.dsh/flower-cockpit/data/（events-revenue / roi / customer / report-template / report-skeleton / promos / cockpit-export / provider-cache）

## 四子项
| 子项 | 内容 | 状态 |
|------|------|------|
| D0 数据层 | events 正则/ROI 聚合/customer 解析/dataProvider 统一接口 | ✅ |
| A 周报 | 模板引擎+结构化骨架+可编辑 UI（五段+Pill+图表位） | ✅ |
| B 促销 | 方案卡状态机+编排（三重门控）+UI | ✅ |
| C 8卡主页 | 数据聚合+驾驶舱 Tab（顶部4卡/中部/下部） | ✅ |
| D 双agent回传 | 产物契约+artifacts API | ✅ |

## 关键技术点
- 排期 16-18d → 实际 8-9d（提前过半）
- 构建：tsc 0 错误 + esbuild（index 4802B + client 15960B）
- 挂载：profiles/web bundles 21→29
- 安全：促销 dry-run 门控 + 审计 + confirm_required（draft→confirmed→executing→done）
- 数据源：D0 实测 ROI 35.71x（初蘅 8-16）

## 商业联动
- W3（8/19）试点外售：周报模板 + 8卡演示 + 方案卡流程
- W5 双轨发布就绪
- D2 定价 ¥1,000-2,000（AI 接听 + know-how 溢价）；成本测算表 ai-operator-cost-model-v0.1.md（边际 ~¥15/月/店）

## 参考
- 运营需求包（aa528267）+ 数据契约 v0.3（4787d717）+ iPolloWork 参考（flower-cockpit-ipollowork-ref.md）
- 实现排期 v2（1e54d56d）+ 里程碑登记（HR a17a52f8）

*b241741f · 2026-08-18*
