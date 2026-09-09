# 蓝图关系网络（relations v1.0）

> 生成：明鉴 v2 · 2026-09-01 · 三件套纪律（文档/代码/依赖）

## 五蓝图
- **blueprint:flowernet**（业务·生意演进 v2.3）
- **blueprint:flowernet-platform**（技术·基础设施 v1.0）
- **blueprint:agent-network**（底座·多智能体协作 v1.0）
- **blueprint:blueprint-platform**（元层·蓝图平台 v1.0）
- **blueprint:aistartup**（业务·AI 创业 v1.0）

## 关系边（8 条）
| 从 | 到 | 类型 | 说明 |
|----|----|------|------|
| flowernet-platform | flowernet | contains | 技术 P5 含业务（花店双主线归入 P5） |
| flowernet | flowernet-platform | depends_on | 业务依赖技术底座 |
| agent-network | flowernet-platform | requires | 底座要求 platform P1 就绪 |
| blueprint-platform | agent-network | consumes | 元层消费底座规范 |
| blueprint-platform | flowernet/flowernet-platform/aistartup | manages | 元层管理全部蓝图 |
| flowernet | aistartup | references | d4-2 引用 ai2 视觉模型 |
| aistartup | flowernet | references | AI 运营官 dogfooding 自营店 |

## 影响传播规则
1. agent-network 缺口 → platform 受阻 → 业务连锁
2. platform P1 未达 → agent-network requires 不满足
3. blueprint-platform 工具未就绪 → 新蓝图正式化慢

---
*relations v1.0 · 2026-09-01 · 明鉴 v2*

## 补充（2026-09-07）· 业务扩张蓝图关系

> 权威登记点: gallery/business-asset-map.json(relations 数组, 65资产/7边) —— 本文件 v1.0 保留历史五蓝图, 新关系以下表为准

| 从 | 到 | 类型 | 说明 |
|----|----|------|------|
| flowernet-citywar(城市战引擎) | flowernet-ops(代运营) | provides | 商家池供给: 平移/新签商家是 ops 服务商家来源 |
| flowernet-citywar(城市战引擎) | flowernet-supply(供应链) | provides | 商家池供给: 成都750店等是 supply 贸易线初始客户基数 |
| 成都商家池 | 城市合伙人资格(成都已下) | part_of | 750鲜花店强建联由城市合伙人掌握 |
| 资材/耗材/包材供货线(supply trade) | 供应链公司(flowernet-supply) | part_of | trade 主线(聚焦资材, 花材红海不做) |
| IP配件标准化供货线(supply ip-license) | 供应链公司(flowernet-supply) | part_of | ip-license 主线(面向花店IP配件, 初蘅优先) |

### 分布式通讯治理关系（2026-09-09 永续通讯里程碑）
| 从 | 到 | 类型 | 说明 |
|----|----|------|------|
| agent-network | distributed-network | contains | 通讯治理物理实现层（接口在 agent-network, 实现在 distributed-network） |
| distributed-network | agent-network | depends_on | 依赖 agent-network 的 bus/fnp 语义 |
| distributed-network | blueprint-platform | manages | 通讯治理文档/公约在蓝图平台管理 |

### 新增蓝图清单(2026-09-07)
- **blueprint:flowernet-ops**（业务·代运营服务 v1.0 草稿→已登记 asset-map）
- **blueprint:flowernet-supply**（业务·供应链公司 v1.2 **已登记** 2026-09-07 用户确认）
- **blueprint:flowernet-citywar**（业务·城市战引擎 v1.1 已登记+确认 2026-09-07 用户确认调研修正）

---
*relations 补充 2026-09-07 · 明鉴 v3 · 权威=asset-map.json · supply v1.2/citywar v1.1 已登记确认*
