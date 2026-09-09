# 企查查 MCP 接入计划

> 制定：数据调查员 4787d717 · 2026-09-07 · 状态：✅ 已接入（2026-09-09 用户完成公账打款，9 server 全部激活 + 冒烟通过）
> 用途：多智能体网络接入企查查工商/风险/IP/经营/高管数据（竞品监控/融资情报/供应商背调）
> 调研依据：research/qcc-mcp-research-2026.md（完整调研报告）

---

## 一、目标与价值

接入企查查官方 MCP（9 个 streamable-http server），为多智能体网络提供企业工商数据能力：
- **竞品月度深扫（L1/L3）**：竞对工商/融资动态自动化（补 web 盲区）
- **融资情报雷达**：operation server 盯「鲜花×AI 融资标的」
- **供应商/代运营背调**：risk server 核验花娃/花递风险
- **citywar 尽调**：区域代理/合作方（声通/黄紫阳等已确认实体）背调
- **花店 SaaS 目标公司**：company server 获客画像

## 二、已完成的进度（阶段 1）

| 项 | 状态 | 位置 |
|---|---|---|
| 调研报告 | ✅ | research/qcc-mcp-research-2026.md |
| Token 获取 | ✅ 已验证有效 | 用户提供 |
| Token 安全存储 | ✅ 0600 | ~/.dsh/qcc/qcc.token |
| 9 server 注册 | ✅ 未激活 | ~/.dsh/mcp-station/servers.json（0600） |
| Token 验证 | ✅ company 握手 + 16 工具列全 | — |

## 三、阻塞点（已解除 2026-09-09）

~~**公账打款认证**：企查查完整能力需企业认证（公账打款），用户暂缓。~~
✅ 用户 2026-09-09 完成公账打款认证，token 验证有效、9 server 全激活、冒烟通过。

## 四、接入结果（2026-09-09 阶段 2 完成）

1. ✅ **MCP-station 激活**：9 server stopped → **running**（无 error）
2. ✅ **冒烟验证**：company（实体检索+工商登记）+ risk（35 项风险全扫）双真实查询通过
3. ✅ **能力验证**：9 server 全工具列齐 —— company16 / risk38 / ipr18 / operation35 / history34 / executive44 / regulation6 / case4 / tender6 = **201 工具**
4. **接入工具链**（下一步）：
   - 竞品监控 L1/L3：company + operation（融资）补情报
   - 融资雷达：operation 盯标的
   - 供应商背调：risk
5. **注册闭环**：已通知星桥（R020）/HR（资源）/明鉴（citywar 工具链）——`data/investigate/qcc-mcp-registered`

### 调用方式
- 激活端点：`POST 127.0.0.1:51235/mcp-station/api/mount {id}`（MCP-station 插件 HTTP，仅 localhost）
- 查询端点：`GET 127.0.0.1:51235/mcp-station/api/state` 查 running/tools
- 工具命名：`mcp__<server>__<tool>`（如 `mcp__qcc-company__get_company_registration_info`）
- server id：srv-qcc-{company,risk,ipr,operation,history,executive,regulation,case,tender}

### 冒烟实测记录（2026-09-09）
| 查询 | 结果 |
|---|---|
| company get_company_by_query 声通科技 | ✅ 多候选完整返回（声通科技股份 913100007831452642 等 5 家） |
| company 登记（精确信用代码） | ✅ 需完整名/代码；模糊名走 by_query 先锁定 |
| risk get_company_risk_scan 声通科技股份 | ✅ 35 项全扫（裁判文书8/立案3/开庭2，余32无） |

## 五、安全规范（已执行）

- Token 0600 存 ~/.dsh/qcc/qcc.token，不落盘明文于业务文件
- servers.json 0600
- 凭据归属：数据调查员 4787d717（已报 HR）

## 六、搁置清单（已全部执行 2026-09-09 ✅）

```bash
# 1. 重读 token
TOKEN=$(cat ~/.dsh/qcc/qcc.token)

# 2. 验证（✅ 认证后仍有效，company tools/list 通过）
# 3. ✅ 激活 MCP-station（9 server，POST /mcp-station/api/mount）
# 4. ✅ 冒烟查公司（company/risk 双通过）
```

## 七、相关资产

- 调研报告：research/qcc-mcp-research-2026.md
- Token：~/.dsh/qcc/qcc.token（0600）
- 注册配置：~/.dsh/mcp-station/servers.json（9 个 srv-qcc-*，0600）
- 黑板登记：data/investigate/qcc-mcp-registered

---
*沉淀计划 · 4787d717 · 2026-09-07 制定 / 2026-09-09 ✅ 接入完成*
