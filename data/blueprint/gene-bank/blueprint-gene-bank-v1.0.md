# blueprint:gene-bank · GeneBank 基因库（AI 网盘存储底座） · v1.0

> 生成：明鉴 v2 · 2026-09-02 · 三件套纪律
> 状态：active · 门禁：① 内容寻址唯一 ② 血缘可溯 ③ 语义版本可回退 ④ 表达可验证 ⑤ 染色体可扩展 ⑥ 人类删除需确认
> 依据：research/cost-governance/ai-drive-genome-protocol-v0.1-2026-08-23.md + genebank-manifest.schema.json + 用户指示 2026-09-02（纳入管理器+定归属）

## 〇、定位

**GeneBank = 体系资产存储底座（AI 网盘）**——非商业工具蓝图，是服务所有蓝图的独立存储基础设施。已落地运行（rust-genebank 8801 端口 · registry 5.5万注册 · 6 染色体）。

## 一、主线

- **store**：存储底座 — 内容寻址+注册层（gene_id/genes/registry.jsonl）
- **classify**：染色体分类 — 6 类（models/datasets/corpora/knowledge/artifacts/recipes）可扩展
- **lineage**：血缘与版本 — parent_genes 血缘 + mutation 语义版本 + 回退
- **evolve**：自进化接口 — 新染色体声明即用

## 二、阶段

### P0 存储与注册 [active]
- gb1-1 注册层服务 [done] — Python+rust 双版 8801，API 一字兼容
- gb1-2 内容寻址存储 [done] — genes/<sha256>.bin+json 去重
- gb1-3 registry 日志 [done] — jsonl append-only 5.5万

### P1 染色体体系 [active]
- gb2-1 六染色体落地 [done] — datasets 5.5万 + artifacts 72 已存
- gb2-2 可扩展枚举 [done] — schema enum+additionalProperties

### P2 血缘与版本 [active]
- gb3-1 血缘追溯 [active] — parent_genes 链
- gb3-2 语义版本回退 [todo] — mutation 记录可回退

### P3 自进化 [todo]
- gb4-1 与知识图谱衔接 [todo] — paper-cache→corpora · 快照→artifacts · KB→knowledge
- gb4-2 跨蓝图资产登记 [todo] — 各蓝图资产统一入 gene-bank

## 三、与知识内核图谱关系（互为表里）

```
📚 知识内核图谱（逻辑视图）         🗄 gene-bank（物理存储）
报告/论文/蓝图 谁支撑谁            corpora=论文PDF · datasets=训练集
                                      knowledge=KB导出 · artifacts=快照评估
```

## 四、relations

- child_of: agent-network（底座系）
- references: flowernet-platform（存储衔接）
- manages: blueprint-platform
- references: flowernet（flower-yolo 等资产）

---
*blueprint:gene-bank v1.0 · 明鉴 v2 · 2026-09-02*
