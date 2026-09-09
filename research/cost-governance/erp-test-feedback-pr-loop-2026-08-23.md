# ERP 实测 · 优化反馈 · PR 闭环（AI 实战测试）

> 日期：2026-08-23 · 协调者 fa1f9150 · 用户思路「接入 ERP 实际测试 + 优化反馈 + PR 逻辑」
> 定位：把「外卖商品订单 → ERP 商品导入」的数据打通，同时作为 **ERP 的 AI 实战测试**——实测发现问题 → 优化反馈 → 对 chuheng_erp 提 PR（质量闭环）

## 一、闭环流程

```
① 实测：调 ERP MCP 工具（登录/门店/数据）——记录可用性/问题/数据质量
② 反馈：发现问题 → 写成反馈报告（issue 级，含复现/影响/建议）
③ PR：对 chuheng_erp 仓库提 PR（修复/优化，Gitee token 可用）
④ 验证：PR 合入后回归（重测工具/数据流）
```

## 二、当前实测发现（问题清单）

| # | 问题 | 实测证据 | 影响 | 建议（PR 方向） |
|---|---|---|---|---|
| 1 | **robot-ai 未绑门店** | V74 换绑 purchaser 后 allowedStores 空，/mcp 返回 403 FORBIDDEN_STORE | AI 无法访问任何门店数据（登录成功但 403） | V 迁移或部署脚本补 user_store_authz 绑定（默认门店/供应链）+ 02_接入规范 补「AI 账号需绑门店」初始化说明 |
| 2 | **/mcp 门店上下文未文档化** | StoreAuthzFilter：query storeId / X-Store-Id header / JWT claim 三级 | 接入方不知道传门店上下文 | 02_接入规范 补 MCP 门店上下文示例（X-Store-Id header） |
| 3 | **生产 DB 访问通道缺** | 生产 flower-postgres 在独立服务器，无 SSH/DB 凭据 | 绑定/运维需人工 | 部署文档补生产访问途径（或配 dsh-ssh 主机） |

## 三、数据打通 = 首个实测场景

```
外卖商品订单导出（waimai_order_export，4 店）
  → 商品映射（外卖商品名/SKU → ERP product/variety）
  → 调 ERP MCP：product.upsert / variety.upsert（验证工具真实可用性 + 数据质量）
  → 实测记录：哪些工具可用/数据映射准确率/问题暴露
  → 后续：外卖订单 → ERP 销售单/库存联动
```

## 四、PR 通道

- 仓库：Gitee `coreyleung/chuheng_erp`（token 可用，可提 PR/issue）
- 首个 PR 候选：**robot-ai 门店绑定**（V 迁移或文档补全——让 AI 账号开箱可用）
- 原则：PR 前先复现（实测证据）+ 影响评估 + 最小改动

## 五、与落链制度衔接

- 每次实测发现 → 落链（问题清单 + 反馈报告 + PR 记录）
- 反馈报告（issue 级）→ 黑板 data/erp/ 登记

---
*ERP 实测反馈 PR 闭环 v1.0 · 协调者 2026-08-23 · 用户思路落地*
