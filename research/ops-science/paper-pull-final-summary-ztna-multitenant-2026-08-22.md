# 论文拉取汇总 · 接入分级/角色权限/多租户/分布式节点身份（2026-08-22）

> 调研专员 · KB ops-science-research 131 → **139 docs** · 11,038 chunks · 1,634,147 tokens · embedded
> 议题：接入即分级 —— Tailscale 内网=自有设备 / 公网=门店或订阅用户，连接时按网络来源+认证判定角色权限

## 总览

| 方向 | 论文 | 全文 | 摘要 | 待补 |
|---|---|---|---|---|
| 1 多租户架构（SaaS 隔离/数据边界） | 2403.01862 · 2505.07692 | 2 | 0 | 0 |
| 2 ABAC/RBAC 访问控制理论 | 2405.07685 | 1 | 0 | 0 |
| 3 零信任网络访问 ZTNA | 2503.11659 · 2410.20611 | 2 | 0 | 0 |
| 4 WireGuard/Tailscale 类安全网络 | 2512.10135 | 1 | 0 | 0 |
| 5 分布式设备身份/零接触配置 | 2603.16745 | 1 | 0 | 0 |
| 6 API 网关认证授权模式 | 2508.01863 | 1 | 0 | 0 |
| **合计** | **8** | **8** | **0** | **0** |

## 优先方向标注 ⭐

- ⭐ ZTNA：2503.11659 ZTA 系统文献综述（PRISMA 2016-2025，持续认证/条件访问/最小权限分类）+ 2410.20611 ZTNA 专论（never-trust-always-verify 架构、云/IoT/混合网络场景）
- ⭐ WireGuard：2512.10135 工业 Open RAN 工厂实测（WireGuard vs IPsec，N3/N2 接口防护，性能可比、配置复杂度显著降低）
- ⭐ 多租户 SaaS 隔离：2505.07692 ABase（字节跳动多租户 NoSQL serverless DB，缓存感知隔离+预测式扩缩容，13B QPS/1EB）+ 2403.01862 MTS（虚拟网络交换层租户隔离，最小特权/完全中介）

## 入库清单

| # | 论文 | arXiv | 来源 | chunks |
|---|---|---|---|---|
| 1 | [2503.11659] Zero Trust Architecture: A Systematic Literature Review | https://arxiv.org/abs/2503.11659 | HTML 全文 | 308 |
| 2 | [2405.07685] Edge Computing for IoT: Novel Insights from a Comparative Analysis of Access Control Models | https://arxiv.org/abs/2405.07685 | HTML 全文 | 203 |
| 3 | [2603.16745] Persistent Device Identity for Network Access Control in the Era of MAC Address Randomization: A RADIUS-Based Framework | https://arxiv.org/abs/2603.16745 | PDF 全文 | 191 |
| 4 | [2505.07692] ABase: the Multi-Tenant NoSQL Serverless Database for Diverse and Dynamic Workloads in Large-scale Cloud Environments | https://arxiv.org/abs/2505.07692 | HTML 全文 | 138 |
| 5 | [2512.10135] Lightweight Security for Private Networks: Real-World Evaluation of WireGuard | https://arxiv.org/abs/2512.10135 | PDF 全文 | 131 |
| 6 | [2403.01862] MTS: Bringing Multi-Tenancy to Virtual Networking | https://arxiv.org/abs/2403.01862 | HTML 全文 | 112 |
| 7 | [2410.20611] Zero-Trust Network Access (ZTNA) | https://arxiv.org/abs/2410.20611 | PDF 全文 | 51 |
| 8 | [2508.01863] Hard-Earned Lessons in Access Control at Scale: Enforcing Identity and Policy Across Trust Boundaries with Reverse Proxies and mTLS | https://arxiv.org/abs/2508.01863 | HTML 全文 | 45 |

## 摘要（1 句）

1. 2503.11659 — ZTA 系统文献综述：PRISMA 梳理 2016-2025 十年研究，给出应用域/使能技术/落地障碍分类与演进脉络。
2. 2410.20611 — ZTNA 专论：以 never-trust-always-verify 为核心框架，分析 ZTNA 原理、架构（云/IoT/混合网络）与开放挑战。
3. 2512.10135 — WireGuard 工业实测：在真实 O-RAN 工厂以 WG 替代 IPsec 保护 N3/N2 接口，吞吐/时延/CPU 开销相当且配置复杂度显著更低。
4. 2403.01862 — MTS：为虚拟网络交换层引入多租户隔离（分舱、最小特权、完全中介、缩减共享 TCB），吞吐 1.5-2x 且开销低。
5. 2505.07692 — ABase：字节跳动多租户 NoSQL serverless 数据库，双缓存层+缓存感知隔离+预测扩缩容，支撑 13B QPS/1EB 规模。
6. 2405.07685 — 访问控制模型比较综述：按数据生命周期（采集/存储/使用）组织 IoT 边缘计算访问控制方案并综述区块链辅助手段。
7. 2603.16745 — 设备身份框架：RADIUS 分发 GUID 应对 MAC 随机化对 NAC 的冲击，覆盖 BYOD/托管/VPN/访客/IoT 六类用例。
8. 2508.01863 — 规模化访问控制经验：反向代理+mTLS+集中 SSO 实现每设备/每用户双重认证与集中策略执行，零信任对齐。

## 预算纪律

全部免费 arXiv 全文（5 篇 HTML + 3 篇 PDF），每源 1 次尝试即成功、零重试、零付费墙；未触碰已入库 8 篇 MCP 相关（2603.22489/2604.07551/2512.08290/2605.18414/2606.30317/2508.03095/2605.30998/2605.16699）。

## 已知缺口（待补）

- WireGuard 经典协议论文（Donenfeld, "WireGuard: Next Generation Kernel Network Tunnel", NDSS 2017）不在 arXiv，全文开放于 NDSS/wireguard.com —— 如需入库可走 PDF 直采流程，本期按预算纪律未拉。
- Tailscale 专属论文稀缺：arXiv 仅有工程型用例（如 2608.07226 双节点 DGX over Tailscale），本期未纳入；Tailscale 的控制平面/设备认证机制建议以官方白皮书补充。

## 落库

- KB: afa7de13-011a-4c73-a9d6-13492c05cdf7（139 docs）
- 索引: research/ops-science/research-paper-library-index.md（kb-index-gen.py 已重生成）
- 摘要缓存: research/paper-cache/<id>.md × 8；PDF 原文: research/paper-cache/pdf/ × 3
- 快照: kb-docs-latest.json / kb-stats-latest.json

*调研专员 · 2026-08-22*
