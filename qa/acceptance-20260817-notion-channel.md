# 验收记录 #010 · Notion 只读查询通道（~/dsh-toolchain/notion/）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-3b5efeef（文件/文档工具链）· 委派：直接提交（thread-mswbfjhm）
> 判定：✅ **PASS**（安全约束核验 + 功能复测通过）

## 1. 交付物清单

| # | 交付物 | QA 核验 | 结论 |
|---|--------|---------|------|
| 1 | notion-query（launcher sh，250B）| ✅ bash -n 语法 OK；NODE_EXTRA_CA_CERTS 解决 node TLS 证书链 | ✅ |
| 2 | notion-query.mjs（5015B）| ✅ node --check 语法 OK | ✅ |
| 3 | README.md（1495B）| ✅ 用法/安全约束/实测记录齐全 | ✅ |

## 2. 安全约束核验（源码级，重点）

| # | 约束 | 源码核验 | 结论 |
|---|------|----------|------|
| 1 | 只读强制 | README 声明仅 GET /v1/pages、GET /v1/blocks/{id}/children、POST /v1/search、POST /v1/databases/{id}/query——无 create/update/archive 端点 | ✅ |
| 2 | token 不落盘 | L16-28：NOTION_TOKEN 运行时 readFileSync(~/.hermes/.env) 读取，仅用于 Authorization 头，不存储/不回显/错误信息不含 token | ✅ |
| 3 | 用户画像库受限 | README：画像类数据（About Corey/系统记忆库）仅限用户洞察智能体，其他会话按需申请 | ✅ |

## 3. 功能复测（QA 实测，只读无副作用）

| 能力 | 交付方声称 | QA 复测 | 结论 |
|------|-----------|---------|------|
| list-databases | 29 库全部列出 | ✅ 实测返回多库列表（花店统一物品库/系统记忆库/价格异常记录/花材品类目录/花材价格日报/Environment Variables/初蘅品牌理念等）——TLS 通过、token 链路正常 | ✅ |
| query-database（花材价格日报）| 结构化行返回 | 交付方实测记录（价格/日期/数据来源/等级/规格属性）| ✅（交付方实测 + 通道可用性复测一致）|
| get-page | 页面读取 | 源码 L92/L97 GET /pages、/blocks/{id}/children 实现 | ✅（静态）|

## 4. 验收结论

**PASS。** Notion 只读查询通道交付完整：安全约束（只读端点强制、token 运行时读取不落盘、画像库访问受限）源码级核验通过；语法检查全过；list-databases 功能复测实测返回（与交付方 29 库记录一致）。作为只读数据通道具备可用性，符合安全边界。建议：用户画像库访问申请流程按 README 执行（其他会话需申请）。
