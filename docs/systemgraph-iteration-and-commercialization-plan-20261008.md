# SystemGraph（系统架构管理器）功能迭代规划 + 商业化探索（2026-10-08 · 星桥）

> 需求来源：用户 2026-10-08「帮我规划改造系统架构管理器的 app 功能迭代，以及探索一下商业化可能性」
> 属主注记：SystemGraph 主源架构师 = 明鉴（session-a190c54c），本规划由星桥协调起草，实施前需与属主对齐（R006 §8 归属优先）。

## 一、现状盘点（2026-10-06/08 实测）

| 维度 | 现状 |
|---|---|
| 定位 | 多智能体系统的「架构地图」：蓝图（业务/系统设计）· 能力图（65 智能体 cap/perm 关系）· 资产清单 · 孤岛发现 |
| 规模 | 21 蓝图 · 53 关系边 · 65 智能体 · 83 快照 · 19 版本 · connect-lab 21 孤岛 / 588 候选 |
| 技术栈 | Python 只读后端（bb-blueprint-gallery.py v1.4.0，8798）+ 单页可视化（146KB shell）+ macOS/iOS 壳 |
| 数据流 | 静态导出为主（本地文件化快照），实时性弱；无编辑、无协作、无分析层 |
| 已注册 | ASC bundle com.coreyleung.systemgraph(+.ios)，app 记录 6819342786；源码在 MBP（明鉴/SystemGraph） |

## 二、功能迭代规划（四阶段）

### P0 · 收敛与实时（1-2 周）
1. 数据实时化：后端由静态快照改增量同步（黑板 SSE 已有基建，复用 ?nodes= 过滤）
2. 蓝图编辑与版本 diff：现只读 → 支持编辑 + 19 版本的双栏 diff 视图
3. 移动端壳对齐：iOS/macOS 壳指向实时后端（替换本地文件化包）

### P1 · 分析层（2-4 周）
4. 孤岛推荐引擎：connect-lab 588 候选 → 相似度排序 + 一键建边建议
5. 能力体检：能力冗余/缺口矩阵（65 agents 的 cap 分布）；权限越界告警（perm 边超出声明域）
6. 风险视图：单点依赖（一个 agent 独占关键资源）、扇出/扇入热点

### P2 · 协作与治理（1-2 月）
7. 变更审批流：蓝图变更走 R046 验收门（提出/执行/裁定三方分离已就绪，天然契合）
8. 只读分享页：对外链接（客户/合作方可看架构图，不含敏感字段）
9. 团队空间：多组织隔离 + 角色权限

### P3 · 智能层（2-3 月）
10. LLM 辅助：蓝图自然语言生成草稿（本机 LM Studio/Dify 已有）；「谁负责 X」自然语言查询
11. 自动架构体检周报：变更摘要 + 异常标注（对接现有晨报/日报体系）

## 三、商业化探索

### 3.1 市场对标（2026-10 检索）

| 参照 | 模式 | 价格锚点 | 借鉴点 |
|---|---|---|---|
| Langfuse / LangSmith | Agent 追踪可观测，开源+云托管 PLG | 免费起步，云按 trace/席位 | 开源核心+云托管的双轨 |
| Braintrust / Raindrop | 评测+追踪 | $29+/seat | 席位制、企业版 |
| Neo4j / GraphRAG | 图数据库+可视化，工业级 | Aura 按量付费 | 图可视化企业叙事 |
| Backstage (Spotify) | 开发者门户/服务目录（开源） | 免费开源，靠生态 | 最接近的形态类比：目录式架构管理 |
| CrewAI/AutoGen Studio | 框架自带面板 | 免费 | 证明「框架带面板」是标配而非卖点 |

### 3.2 SystemGraph 的差异化定位

**不做追踪（trace），做「多智能体组织的架构治理可视化」**：
- 追踪类竞品看「一次任务怎么跑的」；SystemGraph 看「整个 agent 组织长什么样、谁有什么能力、哪里有孤岛、变更怎么治理」。
- 形态类比 = Backstage 目录 + 架构图 + 治理门，目标用户 = 运营多智能体团队的组织。

### 3.3 四条商业化路径（按可行性排序）

| 路径 | 模式 | 现实度 | 说明 |
|---|---|---|---|
| ④ 内部先跑通再外化 | 用 SystemGraph 支撑自己的外卖代运营生意（agent 团队管理降本增效），先产生真实内部收益 | ★★★★★ 现在就能做 | 零外部依赖，验证需求真实性 |
| ② 垂直 SaaS：面向「小 B 商家管理自己的 AI 员工」 | 可视化面板管理 agent 团队，订阅制 | ★★★ 中期 | 你有真实场景（花店+多平台外卖+代运营），客单价 $29-99/月/店可期 |
| ① 开源核心+云托管（PLG） | 开源本地版 + 付费云（协作/托管/高级分析） | ★★ 长期 | 与 Langfuse/Backstage 正面对撞，需大量打磨 |
| ③ 治理咨询+工具包 | 卖方法论（R046 三方裁定、命名门等已被你验证的治理体系）+ 工具 | ★★ 利基 | 客单高但频次低 |

### 3.4 建议路线图

1. **0-3 月**：路径④——内部迭代（P0+P1），同时把外卖代运营的 agent 管理实际用起来，产出可量化收益
2. **3-6 月**：路径②试点——给 1-2 个代运营客户提供「agent 团队可视化报告」（白标分享页），验证付费意愿
3. **6-12 月**：视验证结果决定路径①（产品化开源）或继续垂直深挖

### 3.5 风险与前置

- 数据安全：蓝图含商业机密 → 分享页需字段级脱敏
- 单一维护者依赖（明鉴属主离线时的迭代连续性）→ 先落 git（已推 GitHub/Gitee）+ 文档化
- 竞品工程差距 → 借你独有的治理体系（R046 验收门/命名门）做差异化叙事，不打通用平台战

## 四、参考来源

- [The Agent Observability Landscape in 2026](https://dev.to/nicolas_fainstein/the-agent-observability-landscape-in-2026-who-traces-who-misses-8j0)
- [Braintrust vs Langfuse vs Raindrop (2026): Pricing](https://www.morphllm.com/comparisons/braintrust-vs-langfuse-vs-raindrop)
- [AI Agent Observability Tools (2026): 12 Platforms Compared](https://www.morphllm.com/ai-agent-observability-tools)
- [15 Best AI Agent Frameworks for Enterprise (2026)](https://www.premai.io/blog/15-best-ai-agent-frameworks-for-enterprise-open-source-to-managed-2026/)
- [Neo4j Industrial GraphRAG Demo](https://neo4j.com/videos/demo-industrial-graphrag-intelligence-for-wind-turbine-bom-exploration/)

## 五、遗留与下一步

- 与明鉴属主（session-a190c54c）对齐本规划后实施（离线，排队）
- SystemGraph 源码（MBP 明鉴/SystemGraph）需 scp 到 mac-mini 或明确双端分工
- P0 第 1 项依赖黑板 SSE 订阅在 App 壳的实现（星台已打通同款链路，可复用）
