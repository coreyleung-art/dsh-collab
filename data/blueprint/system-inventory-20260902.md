# 已落地独立系统/存储层 · 全景盘点（System Inventory）

> 明鉴 v2 · 2026-09-02 · 用户指示：GeneBank 纳入并定归属；全量搜遗漏的「已落地独立存储层/系统」
> 方法：端口监听盘点 + rust 项目扫描 + 独立数据库/存储定位 + 蓝图登记对照

## 〇、核心结论

**系统里存在多个『已落地运行、但未纳入蓝图体系』的独立系统/存储层。** 它们都已投产，却不在 11 蓝图管理内——是治理盲区。GeneBank 只是其中最完整的一个。

## 一、已落地独立系统/存储层全景（运行中实测）

| # | 系统 | 技术栈 | 端口/位置 | 状态 | 归属判定 |
|---|------|--------|----------|------|---------|
| 1 | **GeneBank 基因库（AI 网盘）** | Rust v1.0 + Python | 8801 / ~/.genebank | ✅ 运行(5.5万注册) | 独立存储底座（见后） |
| 2 | **黑板 blackboard** | **Rust v0.6** | 8792 | ✅ Rust 版运行 | flowernet-platform 已含? 待查 |
| 3 | 黑板 MCP Server | Rust v0.8.4 | 8810 | ✅ 运行 | 接入层（随黑板） |
| 4 | node-bridge 分布式桥 | Rust | (守护) | ✅ | 分布式底座组件 |
| 5 | 外卖管理面板 MTM | node | 8787 | ✅ | flowernet 采集面（灯塔管） |
| 6 | 外链 MCP/bus-bridge | node | 8790/8791/8910/8911 | ✅ | agent-network 外联层 |
| 7 | ChromaDB 向量库 | Python | 8000 | ✅ | 知识层组件 |
| 8 | Obsidian vault | iCloud | — | ✅ | 知识层（raw/wiki/日记） |
| 9 | DSH KB knowledge | SQLite | ~/.dsh/storages | ✅ | 知识层 |
| 10 | rust-data-tools | Rust v0.2 | CLI | ✅ | 学习侧工具 |
| 11 | rust-toolchain | — | — | ? | 工具链发布物 |
| 12 | 各种 jsonl/db | — | ~/.dsh/*.jsonl | ✅ | 消息/审计/队列等 |

## 二、GeneBank 归属分析（用户问题）

**定位：独立存储底座（infrastructure），非商业工具。**

理由：
1. **服务对象是体系本身**——6 染色体存的是体系资产（models/datasets/corpora/knowledge/artifacts/recipes），非对外售卖产品
2. **与 aistartup（AI 运营官）区别**：aistartup 是面向花店的商业产品蓝图；GeneBank 存的是支撑这些产品的原料
3. **与 knowledge 层关系**：GeneBank=存储底座（内容寻址+血缘+版本），knowledge=语义检索层（向量），ChromaDB/Obsidian/KB 是知识的具体形态
4. **最佳归属**：作为**新独立蓝图 `gene-bank`（技术/底座维度）**，或归入 flowernet-platform 的 infra 主线。因它横切所有蓝图（任何蓝图都可存资产），建议独立蓝图 child_of agent-network（底座系）

## 三、GeneBank ↔ 知识内核图谱关系

```
知识内核图谱（📚 tab）         GeneBank（存储底座）
┌──────────────────┐           ┌──────────────────────┐
│ 📄 调研报告 (92)  │───语料──▶│ corpora/ (论文 PDF)   │
│ 🎓 论文 (108)     │───落链──▶│ corpora/ + datasets/  │
│ 📐 蓝图 (11)      │───产物──▶│ artifacts/ (评估/日志) │
│ knowledge KB     │───快照──▶│ knowledge/ (向量导出)  │
└──────────────────┘           └──────────────────────┘
     溯源展示层                      存储底座层
```

- **关系**：知识内核图谱是「谁支撑谁」的**逻辑视图**（可浏览）；GeneBank 是资产**物理存储**（内容寻址可下载）
- paper-cache 的 PDF、调研落盘 = GeneBank corpora 的**上游写入源**；蓝图的快照/评估 = artifacts 染色体
- **互为表里**：图谱回答「为什么引用」，GeneBank 回答「资产在哪存/版本多少」

## 四、遗漏盘点结论

**未纳入蓝图管理的已落地系统至少 8+ 个**（GeneBank/黑板Rust版/黑板MCP/node-bridge/外卖面板/外链服务/ChromaDB/data-tools 等）。其中：
- **存储底座类**（应独立蓝图）：GeneBank ← 本次纳入
- **平台组件类**（随属主蓝图）：黑板→flowernet-platform、node-bridge→agent-network、外卖面板→flowernet
- **知识层**（应入知识内核图谱）：ChromaDB/Obsidian/KB/paper-cache 已在📚呈现（作为报告/论文节点），存储层归属待标

## 五、建议行动

1. GeneBank 建独立蓝图 `blueprint:gene-bank`（v1.0，child_of agent-network 或独立底座维度）
2. 蓝图管理器加「🗄 系统资产」视图或并入项目视图：展示全部运行系统（端口/状态/属主蓝图）
3. 知识内核图谱加 GeneBank 节点（与 corpora/artifacts 边）——展示「图谱↔存储」表里关系
4. 其余已落地系统标属主蓝图（在 relations 登记）

---
*已落地系统全景盘点 · 明鉴 v2 · 2026-09-02*
