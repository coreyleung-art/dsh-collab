# blueprint:flowernet-erp · 初蘅 ERP（CH-RFID/flower-chain 数字化底座） · v1.0

> 生成：bb-blueprint-create.py · 2026-09-02T13:16:43 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① 数据底座（PG16/规范）稳定 ② 业务闭环（进销存/财务）跑通 ③ RFID+移动端接入——对应 flowernet d25-4 门禁（p2-1 完成才启动流程闭环）
> 依据：PROJECT_SNAPSHOT_2026-07-19（v1.2.0-r1）+ 妙记仓库管理ERP需求（2026-08-31）+ device-data-map（i9 路径）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | flowernet-erp |
| name | 初蘅 ERP（CH-RFID/flower-chain 数字化底座） |
| version | v1.0 |
| mainlines | {"core": "核心 ERP（进销存/采购/生产/销售/财务 一体化——57 控制器/PG16）", "deploy": "部署运维（Gitee 推送/腾讯... |
| stages | [{"id": "ferp1", "name": "数据底座", "stage": "1.0", "status": "active", "substages"... |
| works | [{"owner": "TRAE/开发", "stage": "ferp1-3", "status": "todo", "work": "ERP 代码推送 Gi... |
| gate | ① 数据底座（PG16/规范）稳定 ② 业务闭环（进销存/财务）跑通 ③ RFID+移动端接入——对应 flowernet d25-4 门禁（p2-1 完成才启动流程闭环） |
| status | active |
| ts | 2026-09-02T13:16:43 |

## 一、主线

- **core**：核心 ERP（进销存/采购/生产/销售/财务 一体化——57 控制器/PG16）
- **deploy**：部署运维（Gitee 推送/腾讯云/域名/备份）
- **rfid**：RFID 链路（Android PDA 入库/出库/盘点 + SyncHttpServer 同步 + HCPDA UHF SDK）

## 二、阶段与子阶段

### 1.0 数据底座 [active]
- ferp1-1 d25-1 数据规范性底座 [done] — chuheng_erp v1.2.0-r1 已建（57 控制器/PG16/PDA-RFID）✅
- ferp1-2 d25-2 AI MCP 接入 [done] — 14 工具 + robot-ai 门店绑定 ✅
- ferp1-3 代码仓库化 [todo] — 69 待提交文件 → Gitee 推送（coreyleung/chuheng_erp 待推）

### 2.0 业务闭环 [active]
- ferp2-1 进销存闭环 [active] — 采购→入库→销售→出库一体化（妙记需求：跨店调拨实时库存/出库自动同步）
- ferp2-2 报销识别优化 [todo] — 截图金额自动提取+多金额规避（打码/裁剪）——妙记需求
- ferp2-3 审批迁移 [todo] — 企业微信审批逻辑平移 ERP，对齐操作习惯——妙记需求

### 3.0 RFID+移动 [partial]
- ferp3-1 PDA 入库/出库/盘点 [partial] — HcpdaInventory（PDA 库存）+ rfid-bridge（i9 实测确认）
- ferp3-2 SyncHttpServer [active] — :8081 PDA 同步端口

## 三、工作项（works）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| todo | ERP 代码推送 Gitee（69 待提交） | TRAE/开发 | ferp1-3 |
| active | 跨店调拨实时库存 + 出库自动同步 | TRAE/开发 | ferp2-1 |
| todo | 报销截图金额识别（打码/裁剪规避） | TRAE/开发 | ferp2-2 |
| todo | 企业微信审批逻辑迁移 ERP | TRAE/开发 | ferp2-3 |

## 四、依赖关系（relations）

- **parent**：flowernet
- **requires**：flowernet-platform

## 四b、自动化开关锁（R027 + Lean4 逻辑锁）

- **ferp2-2**：报销截图自动识别（未来）
  - 开关点：`automation-switch on --bp flowernet-erp --stage ferp2-2 --by <人类> --level L3` · 默认态：OFF
  - 熔断：`automation-switch off --bp flowernet-erp --stage ferp2-2`
  - 授权：HumanApproval(L3)

## 五、门禁链

① 数据底座（PG16/规范）稳定 ② 业务闭环（进销存/财务）跑通 ③ RFID+移动端接入——对应 flowernet d25-4 门禁（p2-1 完成才启动流程闭环）

---
*blueprint:flowernet-erp · v1.0 · 三件套纪律落盘*
