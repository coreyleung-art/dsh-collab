# 持续产物保留策略登记（2026-09-11）

> 维护: HR 司库 · 来源: 明鉴资源披露(主动/好实践) · 定位: 纳入 HR 资源审查范围

## 一、dsh-plugin-reflect 流水线(明鉴)

**产物目录**: `~/dsh-collab/data/reflect/`(**持续增长**, 须受审)
**增速**: 每日 1-2MB → 年化 ~0.5GB
**现状**: 44K / 3 文件(流水线未跑)

### 保留策略(明鉴建议 + HR 采纳)
| 产物 | 保留期 | 理由 |
|---|---|---|
| events-*.json | **30 天** | 原始事件流, 过提炼期价值低 |
| cards / answers | **90 天** | 回填有复盘价值 |
| proposal / feedback | **永久** | 规则来源证据(不可删) |
| 日志(dsh-plugin-reflect*.log) | 按惯例轮转 | append-only |

**配套**: 6 插件(devices/dsh-plugin-reflect*)~620K, 代码级, 不需清理

## 二、哲学库(HR 域登记)
- governance-philosophy.json **v1.5, 13 条**(+Φ12 引用即复制 / Φ13 证据有时点)
- 第三条「指称完整性」征询中(data/registry/philosophy-proposal-referential-integrity-20260910)
- 证据链: 7 方征询 5 支持零反对 + 用户裁定

## 三、审查机制说明
- **不做定时自动化**(遵守 v1.0.236「停掉一切定时自动化」指令)
- 改为: **HR 值班轮次按需审查**(手动触发), 覆盖 data/reflect/ 等新增长点
- 原则: 「靠自觉的清理一定会漏」(明鉴 Φ9)——登记入审查范围即结构保障

---
*策略 v1.0 · HR 司库 · 2026-09-11*
