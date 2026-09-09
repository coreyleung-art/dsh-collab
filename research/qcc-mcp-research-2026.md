# 企查查等企业工商信息 MCP 服务器接入调研

> 调研：数据调查员 4787d717 · 2026-09-07 · 需求：用户「研究接入企查查等类型信息的 MCP 服务器」
> 关联：本机 MCP-station（已接 external-link HTTP MCP，可接 streamable-http MCP）；竞品/融资调查需工商数据
> 结论有效期：2026-09（企查查开放平台政策变化快）

---

## 一、核心结论

**企查查是工商信息 MCP 的最成熟接入方——官方开放平台提供 6 个 MCP server（146 tool），且近期有 2000 万数据免费开放计划。天眼查也有官方 MCP。** 对多智能体网络的「竞品调查/融资情报/供应商背调」价值极高。

接入方式：企查查官方 MCP 用 **Streamable HTTP**（`https://mcp.qcc.com/basic/stream?key=YOUR_KEY`），任意支持 MCP 的客户端可接；本机 MCP-station 已支持 HTTP MCP，可直连。

## 二、工商信息 MCP 生态（主流平台）

| 平台 | MCP 形态 | 规模 | 接入 | 免费/价格 |
|---|---|---|---|---|
| **企查查** | 官方开放平台 6 server / 146 tool | 最全（工商/司法/风险/IPR/经营/高管） | Streamable HTTP + SSE | 开放平台拿 key；**2000 万数据免费开放 3 个月**（AI 智能体扶持计划，惠 10 万创业者） |
| **天眼查** | 官方 MCP CLI（tyc-tech/tyc-cli）+ skills | 工商/风险/关联 | MCP CLI | 需企业实名认证部分功能 |
| 腾讯云 MCP 广场 | 企查查企业信息 MCP 托管 | 精简（FuzzySearch/RegistrationInfo/ChangeRecords 等） | Streamable HTTP | 云市场 |
| 爱企查/水滴信用 | 少公开 MCP | — | — | — |
| 海外 | ARES（捷克工商）等 | — | — | 参考 |

## 三、企查查 6 个 MCP server 明细（官方 agent.qcc.com）

| key | tool 数 | 用途 | 我方场景 |
|---|---|---|---|
| company | 16 | 工商/股东/UBO/对外投资/年报/财务/分支/上市 | 竞对主体、花店 SaaS 目标公司 |
| risk | 35 | 司法/失信/经营异常/行政处罚/税务/破产/抵质押 | 供应商/代运营风险背调 |
| ipr | 18 | 专利/商标/著作权/自媒体 | 竞品技术/品牌监测 |
| operation | 35 | 资质/招投标/招聘/融资/舆情/公告 | **融资情报**（T3 融资面核心） |
| executive | 42 | 法代/高管个人背调 | 花娃/竞对创始人 |
| history | — | 历史轨迹（需企业实名） | 暂不可用 |

## 四、一站式封装方案：zhanglunet/qcc（推荐）

**GitHub**：[zhanglunet/qcc](https://github.com/zhanglunet/qcc)（Apache-2.0）

把企查查官方 6 MCP server（146 tool）封装成 **8 个工作流 skill**，支持 4 接入形态：

| 接入形态 | 适合谁 | 我方价值 |
|---|---|---|
| Claude Code 原生 MCP | 调研/临时尽调 | 数据调查员日常查询 |
| OpenClaw | 常驻本地 Agent | 多智能体跨 IM |
| Hermes | 服务端编排/多用户/配额 | 多会话共享 |
| Python/TS CLI | 脚本/数据管道 | **自动化竞品/融资监控** |

**8 个 skill**（串 tool + 配额管理）：
- qcc-anchor（锁定主体）/ qcc-basic-profile（KYB 工商摘要）
- **qcc-ownership-trace**（股权穿透/UBO）/ **qcc-risk-screen**（34 tool 司法风险）
- **qcc-ipr-portfolio**（专利商标）/ **qcc-operation-pulse**（招投标/融资/舆情）
- **qcc-executive-background**（高管背调）/ qcc-person-portfolio（关联企业）

## 五、本机接入方案（MCP-station）

本机已有 `dsh-plugin-mcp-station`（管理 HTTP MCP），已接 external-link。接入企查查：

```json
{
  "mcpServers": {
    "qcc-mcp-server": {
      "transport": "streamable-http",
      "url": "https://mcp.qcc.com/basic/stream?key=YOUR_KEY"
    }
  }
}
```

**步骤**：① 企查查开放平台（agent.qcc.com/guide）注册拿 key → ② MCP-station 登记 streamable-http URL → ③ 授权（R027）→ ④ 冒烟查询一家公司验证。

## 六、对多智能体网络的落地价值

| 场景 | 用哪个 MCP | 价值 |
|---|---|---|
| 竞品月度深扫（L1/L3）| company + operation | 竞对工商/融资动态自动化（补 web 搜索盲区）|
| **融资情报雷达** | operation（融资） | 盯"鲜花×AI 融资标的"（现用 web 检索，工商更准）|
| 供应商/代运营背调 | risk | 花娃/花递/代运营公司风险核验 |
| 花店 SaaS 目标公司 | company | 外售获客时的目标公司画像 |
| citywar city 合伙人背调 | company/executive | 区域代理/合作方尽调 |

## 七、风险与注意

1. **key 费用**：企查查 MCP 有配额（skill 单次串 tool 数有上限）；免费 key 部分功能不可用（history 需企业实名）
2. **免费额度**：2000 万数据免费开放 3 个月计划（2026-04 启动，惠 10 万创业者）——尽快用可享
3. **合规**：只查公开工商数据（非涉隐私 D2 类），合法
4. **key 安全**：存本地环境变量不落盘（同现有凭据纪律）

## 八、信源
1. [腾讯云：企查查企业信息 MCP](https://cloud.tencent.cn/developer/mcp/server/11793)
2. [腾讯 Marvis 上线企查查 MCP（科技日报）](https://www.stdaily.com/web/gdxw/2026-08/17/content_565171.html)
3. [zhanglunet/qcc 企查查一站式接入](https://github.com/zhanglunet/qcc)
4. [天眼查官方 MCP CLI（tyc-tech/tyc-cli）](https://github.com/tyc-tech/tyc-cli)
5. [企查查 2000 万数据免费开放](https://sip.subaonet.com/2026/list/ffyq/sip_yqyw/0730/514l7Mg1.html)
6. [企查查 AI 智能体扶持计划](https://m.caizhongshe.cn/article-5300281980697566338.html)
7. [企查查 agent skills](https://agent.qcc.com/skills)

---
*调研：4787d717 · 2026-09-07 · J46 官方优先/来源可溯*
