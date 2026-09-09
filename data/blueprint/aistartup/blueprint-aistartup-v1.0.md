# blueprint:aistartup · AI 创业探索（一人 AI 公司：情报→产品→变现） · v1.0

> 生成：bb-blueprint-create.py · 2026-09-01T06:11:28 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① 情报库 12 模式齐全才进产品选型 ② 产品验证（需求/定价/渠道三问）通过才进变现 ③ 首产品月收入>¥0 为 v1 里程碑
> 依据：用户画像 v1.3（AI 创业优先级较高）+ ai-money 情报库 + flower-intel 平台雏形

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | aistartup |
| name | AI 创业探索（一人 AI 公司：情报→产品→变现） |
| version | v1.0 |
| mainlines | {"intel": {"desc": "AI 赚钱情报库→机会识别→验证（先建库再变现，用户画像确认方向）", "name": "情报线"}, "monetiz... |
| stages | [{"id": "ai1", "mainline": "intel", "name": "情报库建设", "stage": "1.0", "status": "... |
| works | [{"owner": "明鉴", "stage": "ai1-1", "status": "active", "work": "AI 赚钱情报库（8 文件已建→... |
| gate | ① 情报库 12 模式齐全才进产品选型 ② 产品验证（需求/定价/渠道三问）通过才进变现 ③ 首产品月收入>¥0 为 v1 里程碑 |
| status | active |
| ts | 2026-09-01T06:11:21 |

## 一、主线

- **intel**：情报线 — AI 赚钱情报库→机会识别→验证（先建库再变现，用户画像确认方向）
- **monetize**：变现线 — 订阅/一次性/服务费——参考 ai-money 8 模式（Base44 $80M/Chatbase $10M ARR）
- **product**：产品线 — 已有原型（花觅小程序/主持人手卡/拍摄分镜/绿植签收/AI 工具平台）→选型打磨→发布

## 二、阶段与子阶段

### 1.0 情报库建设 [active]
- ai1-1 模式库沉淀 [active] — ai-money 8 文件已建（foreign-ai-money-modes/vertical-saas-pricing/open-core 等）→补全 12 模式
- ai1-2 机会识别 [todo] — 从情报库筛 3-5 个可复制方向（结合花店/活动资源禀赋）
- ai1-3 验证 [todo] — 最小验证：需求/定价/渠道三问

### 2.0 产品选型与打磨 [todo]
- ai2-1 原型盘点 [todo] — 5 原型清单（花觅/手卡/分镜/签收/工具平台）+ flower-intel 平台雏形（PC-i9 竞品采集+智能定价）
- ai2-2 选型 [todo] — 按市场机会×资源匹配选 1-2 个主攻
- ai2-3 打磨发布 [todo] — MVP→发布（订阅/商城/平台）

### 3.0 变现 [todo]
- ai3-1 定价策略 [todo] — 参考 vertical-saas-pricing-band-r1（垂直 SaaS 定价带）
- ai3-2 渠道 [todo] — 私域/公众号/企微/平台分发
- ai3-3 增长 [todo] — 首批客户→复购→口碑

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| active | AI 赚钱情报库（8 文件已建→补全 12 模式） | 明鉴 | ai1-1 |
| todo | 机会筛选（结合花店/活动资源禀赋） | 明鉴 | ai1-2 |
| todo | flower-intel 平台评估（dogfooding 演进） | 明鉴/i9 | ai2-1 |
| todo | 原型选型（5 原型→1-2 主攻） | 明鉴 | ai2-2 |
| todo | 垂直 SaaS 定价带设计 | 明鉴 | ai3-1 |

## 四、依赖关系（relations）

（无声明）

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

- **ai2-3**：AI 运营官：自动改价/上下架/竞品监控（产品化后客户侧开关）
  - 开关点：`automation-switch on --bp <bp> --stage ai2-3 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp <bp> --stage ai2-3 --by <人类> --reason <原因>`
  - 授权：HumanApproval(L3) 或 VerifiedGate(L2) —— Lean4 类型保证：无 Authorization 无法构造 Unlocked

## 五、门禁链

① 情报库 12 模式齐全才进产品选型 ② 产品验证（需求/定价/渠道三问）通过才进变现 ③ 首产品月收入>¥0 为 v1 里程碑

---
*blueprint:aistartup · v1.0 · 三件套纪律落盘*
