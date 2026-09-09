# 蓝图 4.0-1 · 数据聚合方案设计（垂直引擎数据底座）

> 数据调查员 4787d717 · 2026-08-20 · 蓝图评估器推进项
> 依据：papers-db/论文落链管道经验 + 花店驾驶舱数据契约 v0.3 + 握手协议论文（HLC/Lampson/Exactly-Once）

## 一、目标
垂直引擎（花店 AI 运营官/驾驶舱）的统一数据底座：订单/传感/工艺/履约 四域 → 统一 schema → 入库管道 → 可查询/可分析/可回放。

## 二、统一 Schema 草案（事件溯源 + 血缘）
```
events 表（核心，借鉴 papers-db update_log + 驾驶舱血缘）
- event_id: UUID（唯一）
- tenant_id: 门店/租户（多租户隔离，RLS）
- domain: order|sensor|craft|fulfillment|system
- entity_type / entity_id: 实体（订单号/传感器/工位）
- event_type: 状态变化（created/paid/status_changed/reading/craft_start/...）
- seq: 每实体单调递增（Exactly-Once/At-Least-Once 语义，握手协议论文支撑）
- payload: JSONB（事件数据）
- ts_utc: 时间戳
- ts_hlc: 混合逻辑时钟（跨源排序，HLC 论文支撑）
- source: 采集源（api/scan/import/agent）
- batch_id / run_id: 血缘（对齐 crawl 血缘）
- checksum: 行校验（防篡改/丢尾部）

实体表（当前状态投影）
- orders / sensors / crafts / fulfillments: 最新状态（由 events 回放或增量更新）
```

## 三、数据源清单（四域）
| 域 | 数据源 | 采集方式 | 现状 |
|----|--------|----------|------|
| 订单 | 外卖平台 events/报表下载/8787 | waimai_report/export/事件桥 | ✅ 已有（驾驶舱 v0.3 定稿） |
| 传感 | 温度/湿度/光照（花材环境）/摄像头（工艺） | 传感器网关/边缘采集（待 3.0-2 评估） | ⏳ 待投入 |
| 工艺 | 花艺制作步骤/工时/损耗 | 人工录入/传感器推导 | ⏳ 初建 |
| 履约 | 配送状态/门店操作/骑手 | 平台回调/APP 抓取 | 🔄 部分 |

## 四、入库管道设计（复用论文流水线模式）
```
采集（fetch：API/扫描/导入，幂等+限速）
  → 规范化（normalize：统一 schema/去重/校验，Exactly-Once 语义）
  → 入库（ingest：events 追加 + 实体 upsert，seq 校验防重叠——同论文落链管道）
  → 索引（index：可查询视图/聚合/血缘，时序用 HLC）
  → 登记（registry：数据源/批次/校验清单）
```
关键点：事件只追加（append-only，借鉴论文管道）；实体投影可重建；跨源事件用 HLC 排序（握手协议论文直接支撑）。

## 五、与现有资产衔接
- 复用：papers-db 的 update_log/血缘模式、crawler-lab 的 fetch/retry/limits、驾驶舱数据契约 v0.3 字段
- 论文依据（已向量化入 KB paper-cache）：HLC(1808.05698)、Exactly-Once(1911.11286/1907.06250)、Lampson 可靠消息(6.826)、黑板共享态(2507.01701)

## 六、实施建议（分阶段）
- Phase A（现成）：订单域 schema + 管道（复用驾驶舱链路，1-2 天）
- Phase B（传感评估后）：传感域接入（依赖 3.0-2 评估结论）
- Phase C：工艺/履约域（需业务定义采集点）
- 产出：SQLite/PostgreSQL events 表 + ingest 脚本 + registry

## 七、待办/风险
- 传感/工艺域数据源未定（等 3.0-2）
- 多租户隔离（RLS）与凭据纪律
- schema 需与实现侧（1e54d56d）对齐
