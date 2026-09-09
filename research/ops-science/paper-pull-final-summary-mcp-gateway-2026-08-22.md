# 论文拉取汇总 · MCP 网关/服务化公网出口（2026-08-22）

> 调研专员 · KB ops-science-research 123 → **131 docs** · 9,859 chunks · 1,481,480 tokens · embedded
> 议题：智能体能力封装为 MCP 服务器 → 公网云部署（腾讯轻量云+域名）→ 外部 MCP client 调用

## 总览

| 方向 | 论文 | 全文 | 摘要 | 待补 |
|---|---|---|---|---|
| 1 MCP 安全/远程调用安全 | 2603.22489 · 2604.07551 · 2512.08290 | 3 | 0 | 0 |
| 6 云原生安全（MCP 代理网关） | 2605.18414 | 1 | 0 | 0 |
| 2 分布式/远程 MCP 服务器 | 2606.30317 | 1 | 0 | 0 |
| 4 MCP 生态/注册表/可发现性 | 2508.03095 | 1 | 0 | 0 |
| 3 API 经济/x402 按调用计费 | 2605.30998 | 1 | 0 | 0 |
| 5 订阅制 SaaS 经济学 | 2605.16699 | 1 | 0 | 0 |
| **合计** | **8** | **8** | **0** | **0** |

## MCP 公网部署安全专题（优先标注 ⭐）

- ⭐ 2603.22489 MCP Threat Modeling + Tool Poisoning（客户端侧威胁建模 STRIDE/DREAD，工具投毒实证）
- ⭐ 2604.07551 MCP-DPT（六层防御落位分类法，指出 host 编排/传输/供应链层防护缺口）
- ⭐ 2512.08290 SoK MCP 生态安全（威胁/安全分类法 + 现有防御盘点，含远程/多智能体场景）
- ⭐ 2605.18414 MCP Proxy 架构强制访问控制（属性 ABAC 网关，工具发现/调用双重拦截，0% 越权调用率）

## 入库清单

| # | 论文 | arXiv | chunks |
|---|---|---|---|
| 1 | [2603.22489] MCP Threat Modeling & Tool Poisoning | https://arxiv.org/abs/2603.22489 | 177 |
| 2 | [2604.07551] MCP-DPT | https://arxiv.org/abs/2604.07551 | 157 |
| 3 | [2512.08290] SoK MCP Ecosystem Security | https://arxiv.org/abs/2512.08290 | 212 |
| 4 | [2605.18414] MCP Proxy Access Control | https://arxiv.org/abs/2605.18414 | 39 |
| 5 | [2606.30317] MCP Server Architecture Patterns | https://arxiv.org/abs/2606.30317 | 78 |
| 6 | [2508.03095] Agent Registry Solutions | https://arxiv.org/abs/2508.03095 | 78 |
| 7 | [2605.30998] x402 Free-Riding Security | https://arxiv.org/abs/2605.30998 | 188 |
| 8 | [2605.16699] SaaS as Insurance Product | https://arxiv.org/abs/2605.16699 | 149 |

## 预算纪律

全部免费 arXiv HTML 全文（knowledge_import_url），每源 1 次尝试即成功，零重试、零付费墙；未触碰已入库 5 篇（2601.11595 / 2510.13467 / 2506.01804 / 2504.16736 / 2506.19676）。

## 落库

- KB: afa7de13-011a-4c73-a9d6-13492c05cdf7（131 docs）
- 索引: research/ops-science/research-paper-library-index.md（kb-index-gen.py 已重生成）
- 摘要缓存: research/paper-cache/<id>.md × 8
- 快照: kb-docs-latest.json / kb-stats-latest.json

*调研专员 · 2026-08-22*
