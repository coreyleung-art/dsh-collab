# 论文档案 · 版本管理自动化 / 多仓同步 / Agent 记忆系统

> 调研：2026-08-28 ｜ 中枢 fa1f9150 ｜ 背景：repo-pipeline × dsh-tools version 合并评估 + OpenChronicle 吸收评估
> 状态：B 级临时入库（待全文抓取 + 交叉验证后升 A）

---

## A. 版本管理自动化（repo-pipeline × version 合并的学术依据）

### A1. Automated Versioning for Software Releases: A Retrospective Study and a New Lightweight Approach
- **出处**: IEICE Transactions on Information and Systems, E109.D(3), pp.299-316, 2026-03
- **作者**: Xingfeng CHENG, Xin CHONG, Weiyu LAN, Caimiao ZHAO（杭州悠云科技 / 中国联通浙江）
- **DOI**: https://doi.org/10.1587/transinf.2025MPP0003
- **链接**: https://www.jstage.jst.go.jp/article/transinf/E109.D/3/E109.D_2025MPP0003/_article/-char/ja
- **核心**: 第三方库大量不遵循 semver（major/minor/patch 应对 breaking/non-breaking/internal），给依赖升级带来巨大成本。回顾了**三类自动版本化技术**：
  1. 规则型（只看关键词）
  2. ML 型（考虑更多特征）
  3. 轻量混合（本文提出）
- **与我们的关系**: **直接对应 dsh-tools version 工具**——我们目前的 --type fix/feat/breaking 是「规则型」；论文指出可升级到「ML 型」（从 commit 内容自动判断版本类型）。这是 version 工具 v2 的升级方向（自动检测 breaking 而非手动指定）。
- **待办**: 拉全文（J-STAGE 开放获取）→ 本地 PDF + 提取关键表（三技术对比）

## B. Agent 记忆系统（OpenChronicle 吸收的学术依据）

### B1. MemGPT: Towards LLMs as Operating Systems
- **出处**: arXiv:2310.08560（v2, 2024-02-12）
- **作者**: Charles Packer et al.（UC Berkeley）
- **链接**: https://arxiv.org/abs/2310.08560
- **核心**: OS 式「虚拟上下文管理」——把 LLM 当有限内存进程，**层次化记忆**：
  - main context（系统指令 + 工作上下文 + FIFO）
  - external context（recall DB + archival DB）
  - 通过 **LLM 函数调用**在层间分页（paging）
- **与 OpenChronicle 的关系**: 学术锚点——OpenChronicle 的 capture→store→writer→timeline 本质是「把屏幕上下文写进外部记忆库」，MemGPT 提供「层次化 + 分页 + 事件驱动」的设计理论。OpenChronicle 缺的正是 MemGPT 的「函数调用式记忆操作 + 事件驱动控制流」。
- **安全警示（论文也指出）**: 函数调用读写是安全边界，无写门控时记忆可能成为 prompt injection 持久化向量——**这对我们吸收 OpenChronicle 极重要**（记忆写入必须门控）。
- **已有条目**: ai-papers-database.md E 主题已收录

### B2. AriadneMem: Threading the Maze of Lifelong Memory for LLM Agents
- **出处**: arXiv:2603.03290（2026-02-05, cs.CL/cs.AI/cs.IR/cs.LG）
- **作者**: Wenhui Zhu, Xiwen Chen, et al.（14 作者）
- **链接**: https://arxiv.org/abs/2603.03290 ｜ 代码: https://github.com/LLM-VLM-GSL/AriadneMem
- **核心**: 固定上下文预算下的**图结构记忆**，解决两大难题：
  1. disconnected evidence（跨时间多跳事实关联）
  2. state updates（信息演化 vs 旧静态日志冲突）
  - 离线构建：entropy-aware gating 滤噪 + conflict-aware coarsening 合并静态重复、保留状态迁移为时间边
  - 在线推理：algorithmic bridge discovery 重建缺失逻辑路径 + 单次拓扑感知合成
  - **LoCoMo 上 Multi-Hop F1 +15.2% / Average F1 +9.0%，总运行时间 -77.8%（仅 497 context tokens）**
- **与 OpenChronicle 的关系**: OpenChronicle 的 timeline（事件时间线）可借鉴「时间边 + 状态迁移」；其「冲突感知合并」正是记忆系统防重复的关键——对应我们的记忆去重/归档需求。

### B3. ID-RAG: Identity Retrieval-Augmented Generation for Long-Horizon Persona Coherence in Generative Agents
- **出处**: arXiv:2509.25299
- **链接**: https://arxiv.org/abs/2509.25299
- **核心**: 身份检索增强生成——生成式智能体长程 persona 一致性（身份记忆检索）
- **与 OpenChronicle 的关系**: 多智能体场景下，OpenChronicle 若做「每智能体身份记忆」，ID-RAG 提供检索一致性方案；对应我们 agent-bus 的 50 个 agent_profile 档案演进。

## C. 多仓/CI（repo-pipeline 双仓同步的参考）

### C1. Monorepo vs. Polyrepo 决策（非论文，工程实践）
- **链接**: https://spacelift.io/blog/monorepo-vs-polyrepo
- **核心**: monorepo 易 CI 瓶颈 + 权限耦合；polyrepo 易 SDK 版本碎片化
- **与我们的关系**: repo-pipeline 的 GitHub+Gitee 双仓 = polyrepo + 镜像同步；可对比 monorepo 方案的取舍（我们的 19 插件是 polyrepo，双仓同步工作流即缓解碎片化）

---

## 评级与后续

| 论文 | 主题 | 评级 | 优先级 |
|------|------|------|--------|
| Automated Versioning | 版本管理自动化 | B | **高**（直接支撑 version 工具 v2）|
| MemGPT | 记忆系统 | A（经典）| 高（OpenChronicle 理论锚点）|
| AriadneMem | 记忆系统 | B | 中（时间线/去重借鉴）|
| ID-RAG | 记忆系统 | B | 低（多智能体身份）|

**待办**：
1. 拉全文（J-STAGE 开放获取 + arxiv PDF 走可用通道）→ papers-local/ 落 PDF
2. 逐篇提取要点 → 编译 wiki 页 → ChromaDB 索引（research-pipeline 3-5 步）
3. 升级 version 工具到 ML 型自动版本检测（参考 A1）

---
*关联：repo-pipeline-vs-version-tool-20260828.md / OpenChronicle 吸收评估 / 工具台账*
