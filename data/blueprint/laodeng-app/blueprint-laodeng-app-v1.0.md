# blueprint:laodeng-app · 外卖老登 App（行业商家触达层智能体壳） · v1.1

> 生成：明鉴 v2 · 2026-09-03 · 三件套纪律（文档/代码/依赖）
> 状态：active（展示 Demo） · 门禁：① 展示版协议 v1.1 保持纯展示不接真实后台 ② 行业商家触达演进需用户确认定位 ③ 语音/对话功能先验证可用性再扩展
> 依据：产品定位 v1（黑板 data/ops/laodeng-vs-mtm-positioning-v1）+ laodeng-h5 实际代码（dist/asr-server/ios-shell）+ 版本管理 v0.1.0
> ⚠️ 定位：老登 App ≠ MTM —— 本蓝图只管「面向鲜花行业商家的前端智能体壳」，不管代运营作业工具（见 docs/product-positioning-laodeng-vs-mtm-v1.md）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | laodeng-app |
| name | 外卖老登 App（鲜花行业商家 · 前端智能体壳） |
| version | v1.1 |
| mainlines | {"shell": {"desc": "Agent Front-end Shell：语音/对话 + 功能页承载", "name": "壳线"}, "pages": {"desc": "功能页：订单/财务/库存/采购/售后/投流/评价", "name": "功能页线"}, "reach": {"desc": "触达鲜花行业商家客户群", "name": "触达线"}} |
| gate | ① 展示版协议 v1.1 保持纯展示不接真实后台 ② 商家触达演进需用户确认 ③ 语音/对话先验可用性再扩展 |
| status | active |
| ts | 2026-09-03 |

## 一、主线

- **shell**：壳线 — Agent Front-end Shell：语音输入/对话式交互 + 功能页承载（laodeng-h5 的 ios-shell + asr-server）
- **pages**：功能页线 — 订单/财务/库存/采购/售后/投流/评价功能页（H5 dist）
- **reach**：触达线 — 面向整个鲜花行业商家（非仅自营 10 店），AI 助手形态触达

## 二、阶段与子阶段

### 1.0 展示 Demo [active] (基线 v0.1.0 · git bbcc707 已锁)
- ld1-1 H5 前端 [done] — laodeng-h5/dist（功能页 + 语音/对话 UI）
- ld1-2 语音服务 [done] — laodeng-h5/asr-server（ASR 识别: 真实语音 + 男声 TTS + PTT/文字/唤醒词）
- ld1-3 iOS 壳 [done] — laodeng-h5/ios-shell（移动端承载, 四端）
- ld1-4 对话意图 [done] — 7 意图 + 状态流转（展示版）
- ld1-5 协议 v1.1 [done] — 建议工具·纯展示·执行需用户确认（不接真实后台, 全程虚拟数据零承诺）
- ld1-6 品牌约束 [done] — 真实名禁示(守白/天河等), 虚拟多店命名(繁花森林·云间等)

### 2.0 体验打磨 [planned] (v0.2.0)
- ld2-1 品牌与 UI [planned] — i9 新图标 / UI 细节 / 唤醒 PTT 微调（依赖 i9 图标）

### 3.0 环境与内容 [planned] (v0.3.0)
- ld3-1 正式环境 [planned] — waimailaodeng 迁移 / 排练录制 / 多店示例（依赖平台）
- ld3-2 多渠道订单评价 [planned] — 订单/评价管理多店示例（繁花森林·云间等虚拟名）

### 4.0 对话深化 [planned] (v0.4.0)
- ld4-1 多轮上下文 [planned] — 多轮对话 / 追问澄清 / 数据多样化

### 5.0 原生分发 [planned] (v0.5.0)
- ld5-1 唤醒与分发评估 [planned] — Siri 式唤醒 / TestFlight / 安卓分发评估

## 三、relations

- references: mtm（未来可能调用运营能力 → 产品规划，当前展示版纯 Demo）
- references: flowernet（花店生意场景是其目标商家画像之一）
- ⚠️ distinct_from: mtm（MTM = 代运营作业工具，非商家触达壳——勿混淆）

## 四、资产与版本
- 代码: ~/meituan-multi/laodeng-h5/{dist, asr-server, ios-shell}
- 版本管理: git v0.1.0 (tag bbcc707) + SemVer（version.json/CHANGELOG/VERSIONING.md）→ 老登维护
- 服务/日志: service.sh 统一服务管理 + logs/ 轮转（>2MB 保留 5 份）

---
*blueprint:laodeng-app v1.0 · 明鉴 v2 · 2026-09-03*
