# mac-mini 可共享给 i9 的知识资产清单（省资源分析）

> 日期：2026-08-23 · 协调者 fa1f9150 · 目标：让 i9 节点复用 mac-mini 已有知识资产，避免重复获取/构建/设计，最大化成本最优

## 一、核心思路

i9 作为算力节点 + 数据节点，最贵的资源是「重复获取」。mac-mini 已有大量沉淀（知识库/工具链/数据集/设计），**共享给 i9 = 让 i9 直接复用，省下载/省构建/省设计/省 token**。

## 二、可共享资产清单（按价值排序）

### 1. datasets/flower-yolo（3.2G）—— 🏆 最大省资源点
- 位置：`~/dsh-collab/datasets/flower-yolo`（3.2G）
- **价值**：花店 YOLO 数据集——**i9 的 RTX 4060 Ti 是 CUDA GPU，正是训练这个数据集的理想宿主**（mac-mini M4 无 CUDA 生态）
- 省什么：i9 不用重复采集/标注数据，直接拿现成数据集训 YOLO
- 共享方式：Tailscale 文件共享（SMB/NFS）或经黑板 data/ 传输

### 2. 知识库 KB（ops-science-research）
- 153 docs / 11168 chunks（MCP 安全/接入分级/多租户/ZTNA 等）
- **价值**：i9 智能体经知识库检索，不用重复拉论文/文档
- 省什么：省论文下载 + 解析 + 向量化（全部已做）

### 3. research/（27M）—— 设计文档 + 调研
- 位置：`~/dsh-collab/research/`（cost-governance/ops-science/compute-optimization 等）
- **价值**：架构设计（node-relationship-model、architecture-evolution-stages）、成本治理、模型选型、竞品调研
- 省什么：i9 不用重复设计/调研，直接读结论

### 4. scripts/（480K）—— 工具链
- 位置：`~/dsh-collab/scripts/`
- **价值**：sedimentation-chain-scan.py（沉淀扫描）、route-learner.py（判定）、node-agent.py、event-bus.py 等
- 省什么：i9 不用重复写工具，直接复用/调用

### 5. token-monitor/（2.2M）—— 判定链 + 反馈数据
- 位置：`~/dsh-collab/token-monitor/`（route-feedback-train.jsonl 1152 条、mlx-data、route-weights.json）
- **价值**：学习型路由的反馈数据 + 训练数据
- 省什么：i9 不用重复收集反馈/训练数据

### 6. papers-db（3.0M）—— AI 论文库
- 位置：`~/papers-db/`（SQLite + bge-m3 嵌入 + 检索脚本）
- **价值**：AI 论文库（69 篇 × 8 主题，1024 维向量）
- 省什么：i9 不用重复拉论文/建库

### 7. Obsidian vault（3.3M）—— 知识沉淀
- 位置：iCloud Obsidian（raw/ + wiki/）
- **价值**：LLM Wiki（Karpathy 模式，raw 原始资料 + wiki 编译页）
- 省什么：i9 不用重复整理知识

### 8. registry 资源登记表
- 位置：`~/dsh-collab/resource-registry.md`（v1.0.338）
- **价值**：全网络资源归属/分工/登记
- 省什么：i9 不用重复登记/查资源

### 9. 黑板本身（共享命名空间）
- nodes/tasks/data/notes 命名空间
- **价值**：节点注册/任务卡/文件分发/笔记共享
- 省什么：跨设备通信免额外通道

## 三、共享方式（三选一）

| 方式 | 适用 | 说明 |
|---|---|---|
| 黑板 data/ 命名空间 | 小文件（<10MB） | PUT/GET 文件内容，i9 拉取（已验证：脚本分发 7KB 成功） |
| Tailscale 文件共享 | 大文件（数据集 3.2G） | SMB/NFS/rsync over Tailscale，i9 挂载 mac-mini 目录 |
| DSH 智能体总线读取 | 知识查询 | i9 智能体经总线读 KB/registry/文档 |

## 四、省资源量化（估算）

| 资产 | 共享后 i9 省什么 | 估算价值 |
|---|---|---|
| flower-yolo 3.2G | 省数据采集/标注 | 数天人力 + 采集成本 |
| KB 153 docs | 省论文下载/解析/向量化 | 数百次 API 调用 |
| research 27M | 省设计/调研 | 数十小时 agent 时间 |
| scripts 480K | 省工具开发 | 数十次开发迭代 |
| 判定训练数据 | 省反馈收集冷启动 | 500 条阈值直接可用 |

## 五、建议（按优先级）

1. **先把 flower-yolo 数据集共享给 i9**（最大价值：i9 GPU 直接训练，mac-mini 省 CUDA 缺失的短板）
2. **KB 检索开放给 i9 智能体**（让 i9 经总线查知识，不用重复拉）
3. **research/scripts 挂载给 i9**（Tailscale 共享，i9 直接读设计/工具）
4. 判定链反馈数据共享（i9 参与判定学习）

## 六、风险与边界

- 敏感数据（凭据/审批台账）**不共享**（只共享知识类资产）
- 共享目录只读给 i9（i9 写回经任务卡回报，不直接写共享目录）
- 3.2G 数据集共享走 Tailscale 内网，不暴露公网

---
*i9 共享资产分析 v1.0 · 协调者 2026-08-23*
