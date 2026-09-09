# 黑板 v0.6 设计：显式归属 + 收件定向 + 门店身份（规模化前补齐）

> 2026-08-23 · 协调者 · 用户指示「提前规划推进」——门店节点接入前补齐归属机制
> 背景：蓝图 3.0 端侧/4.0 垂直引擎将接入门店节点，当前 2-3 节点靠命名空间约定够用，10+ 门店靠约定会乱

## 一、问题清单（门店规模化风险）

| # | 风险 | 现状 | v0.6 补齐 |
|---|---|---|---|
| 1 | 任务卡取错 | tasks/<node>/queue 前缀约定 | 卡带 recipient 字段 + 取卡校验 |
| 2 | 通知无收件人 | notes/ key 前缀猜 | 通知带 to/from 字段（可选） |
| 3 | 写者不可追溯 | 无 writer 记录 | 每次写带 X-Writer 签名 + audit 记录 |
| 4 | 门店身份无结构化 | nodes/<name> 自由注册 | 身份注册表：store-id/店码/位置/类型 |
| 5 | 无权限边界 | 全局 token | per-namespace 授权（v0.7 分阶段） |

## 二、v0.6 变更（本次实施）

### 1. 写者签名（X-Writer）
- 请求头 `X-Writer: <agent-id|node-id>`（可选，内网信任）
- 黑板 audit.jsonl 记录 writer；value 元数据带 writer 字段
- 无签名记为 `anonymous`（向后兼容旧客户端）

### 2. 任务卡收件定向（recipient 校验）
- 任务卡 body 支持 `recipient: "<node-id>"` 字段
- 取卡 LIST：执行器取卡时可带 `?node=<id>` 过滤，黑板只返回 recipient==该 id 的卡
- 兼容：无 recipient 字段的卡保持现状（前缀定向）

### 3. 门店身份注册（nodes/ 结构化）
- `PUT /nodes/<store-id>` 支持字段：store_id / code / location / type(store|node|hub)
- `GET /stores` 列出所有 store 类型节点
- 蓝图：STORE-TH（天河店）等门店接入时按此注册

### 4. 权限边界（v0.7 预告，本次只做基础）
- 本次：写者签名 + 审计（为 v0.7 的 per-ns 授权打基础）
- v0.7：per-namespace 授权表（如 STORE-A 只能写 data/store-a/*）

## 三、API 变更

| 端点 | 变更 |
|---|---|
| PUT/DELETE | 支持 `X-Writer` 头，audit 记录 writer |
| GET /tasks?node=<id> | 新增 node 过滤参数（收件定向） |
| PUT /nodes/<id> | 支持 store 类型字段（store_id/code/location/type） |
| GET /stores | 新增：列出门店类型节点 |

## 四、兼容性

- 全部旧 API 不变；无 X-Writer 的旧客户端照常工作（记为 anonymous）
- 任务卡无 recipient 字段的照旧（前缀定向）
- nodes/ 旧注册格式兼容（新增字段可选）

## 五、验证判据

- [ ] 带 X-Writer 写入 → audit 有 writer 记录
- [ ] 无 X-Writer 写入 → anonymous（不报错）
- [ ] 任务卡带 recipient → ?node= 过滤只取到自己的
- [ ] 注册 store 类型节点 → GET /stores 列出
- [ ] 旧客户端（无新字段）全兼容

---
*v0.6 设计 · 协调者 2026-08-23 · 配套进化循环工具链实施*
