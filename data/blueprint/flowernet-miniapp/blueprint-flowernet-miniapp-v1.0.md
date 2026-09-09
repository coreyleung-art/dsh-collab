# blueprint:flowernet-miniapp · 初蘅小程序（前后台） · v1.0

> 生成：bb-blueprint-create.py · 2026-09-02T13:16:43 · 三件套纪律（文档/代码/依赖）
> 状态：todo · 门禁：① 前台商品浏览跑通 ② 下单+私域转化达标 ③ 后台+飞书同步——对接 flowernet 私域占比>30% 终态门禁
> 依据：device-data-map（E:\chuheng_miniprogram_backup）+ 妙记私域管理（01:44）+ aistartup 产品线衔接

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | flowernet-miniapp |
| name | 初蘅小程序（前后台） |
| version | v1.0 |
| mainlines | {"admin": "小程序后台（管理端：商品/订单/库存）", "front": "小程序前台（用户端：商品浏览/下单/私域会员）", "sync": "飞书... |
| stages | [{"id": "fma1", "name": "前台基础", "stage": "1.0", "status": "todo", "substages": [... |
| works | [{"owner": "i9 扫描确认中", "stage": "fma1-1", "status": "todo", "work": "小程序源码盘点（uni... |
| gate | ① 前台商品浏览跑通 ② 下单+私域转化达标 ③ 后台+飞书同步——对接 flowernet 私域占比>30% 终态门禁 |
| status | todo |
| ts | 2026-09-02T13:16:43 |

## 一、主线

- **admin**：小程序后台（管理端：商品/订单/库存）
- **front**：小程序前台（用户端：商品浏览/下单/私域会员）
- **sync**：飞书同步（sync-service：数据同步/导出）

## 二、阶段与子阶段

### 1.0 前台基础 [todo]
- fma1-1 商品浏览 [todo] — uni-app 用户端：花束/盆栽/周边展示
- fma1-2 品牌视觉 [todo] — 初蘅东方美学/守白高定视觉体系

### 2.0 交易+私域 [todo]
- fma2-1 下单支付 [todo] — 订单流程+支付（对接平台/自建）
- fma2-2 私域会员 [todo] — 会员/复购/券包（对接 flowernet 私域爬升卡）
- fma2-3 企微联动 [todo] — 下单→客服/交付（门店私域管理，妙记 01:44 实证）

### 3.0 后台+同步 [todo]
- fma3-1 管理后台 [todo] — 商品/订单/库存管理端
- fma3-2 飞书 sync-service [todo] — 数据同步/商品导出脚本（uni-app 配套）

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| todo | 小程序源码盘点（uni-app 结构/功能模块） | i9 扫描确认中 | fma1-1 |
| todo | 私域会员体系（对接私域爬升） | 明鉴/开发 | fma2-2 |
| todo | 飞书 sync-service 数据同步 | 开发 | fma3-2 |

## 四、依赖关系（relations）

- **parent**：flowernet
- **references**：aistartup

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

（无自动化开关声明——非 AI 自动化阶段或待补）

## 五、门禁链

① 前台商品浏览跑通 ② 下单+私域转化达标 ③ 后台+飞书同步——对接 flowernet 私域占比>30% 终态门禁

---
*blueprint:flowernet-miniapp · v1.0 · 三件套纪律落盘*
