# GeneBank 存储协议 v0.2 · AI 网盘存储协议（基因库）

> 起草：2026-08-23 · 协调者 fa1f9150 · 用户确认概念（文件基因工程）
> 协议名：**GeneBank（基因库）**——备注：类似 AI 网盘，服务于智能体网络的知识/数据/模型资产
> 命名：**混合「隐喻精神 + 工程命名」**——核心概念用基因隐喻（Gene/Chromosome/Heredity），接口字段用工程名（asset/registry/compose）
> 落地：注册层 manifest JSON schema（v0.2 完成）→ 基因操作 API（HTTP + 黑板接入，下一步）
> 融合：MLOps 调研（Pacha 血缘/语义版本/加密完整性 + MLflow 模型注册 + lakeFS 数据版本）

## 一、核心隐喻映射（混合命名）

| 基因工程（隐喻） | GeneBank 概念 | 工程字段 |
|---|---|---|
| DNA 序列 | 资产内容 | `body`（content-addressed） |
| 基因 Gene | 资产原子 | `asset`（gene_id 内容寻址） |
| 基因组 Genome | 资产完整定义 | `manifest`（注册清单） |
| 染色体 Chromosome | 分类目录 | `chromosome`（六类） |
| 基因表达 Expression | 能力声明 | `expression`（capabilities） |
| 遗传 Heredity | 血缘+版本 | `heredity`（lineage+version） |
| 表型 Phenotype | 评估/效果 | `phenotype`（metrics） |
| 基因库 GeneBank | 存储+注册 | `registry`（注册表） |

## 二、染色体（分类目录）——六条标准 + 自进化

| 染色体 | 内容 | 示例 |
|---|---|---|
| `models/` | 模型权重 | yolov8n、qwen2.5:3b、MLX fused |
| `datasets/` | 训练数据集 | flower-yolo、采集数据 |
| `corpora/` | 语料库 | 论文原文、行业资料 |
| `knowledge/` | 知识库+向量 | KB 导出、ChromaDB 快照 |
| `artifacts/` | AI 产物 | 训练日志、评估、推理输出 |
| `recipes/` | **训练配方（新增）** | 数据+模型+参数 组合定义 |

**自进化机制**：`chromosome` 枚举可扩展（schema `enum` + `additionalProperties: true`），新增染色体只需在注册层声明，无需改协议——允许基因库按需进化出新的资产类别。

## 三、遗传法则（协议规则）

1. **唯一性**：内容寻址——同内容同 `gene_id`（sha256），存储去重
2. **遗传**：子基因记录 `parent_genes`，血缘可溯（源自哪个数据/模型/配方）
3. **变异**：语义版本（1.0.0→1.1.0→2.0.0），变异记录可回退
4. **表达**：`expression` 是承诺，必须可验证（manifest 与内容一致）
5. **完整性**：`gene_id` 哈希校验，防篡改（Pacha 加密完整性）

## 四、基因操作（协议动作 · 混合命名）

| 操作 | 隐喻 | 工程名 | 实现 |
|---|---|---|---|
| 转录 | 读取基因 | `asset.get` | GET 资产 |
| 翻译 | 表达基因 | `asset.use` | 训练/推理/检索调用 |
| 剪接 | 切基因片段 | `asset.splice` | 提取子集 |
| 杂交 | 组合基因 | `asset.compose` | 组合生成新基因（配方） |
| 诱变 | 基因突变 | `asset.mutate` | 新版本（迭代） |
| 克隆 | 复制基因 | `asset.clone` | 复制（去重共享） |
| 表达分析 | 测基因表达 | `registry.search` | 检索/评估能力 |

## 五、注册层（v0.2 已完成）

- **manifest JSON schema**：`research/cost-governance/genebank-manifest.schema.json`
- 字段：`gene_id / name / chromosome / body / expression / heredity / phenotype`
- 必填：`gene_id, name, chromosome, body, expression, heredity`（phenotype 可选）
- 校验：schema JSON 合法 + 示例 manifest 必填匹配验证通过

## 六、基因操作 API（下一步，HTTP + 黑板接入）

```
REST（GeneBank 服务，i9 或 mac 侧）：
  PUT   /api/v1/genes           注册新基因（manifest）
  GET   /api/v1/genes/{id}      读基因
  GET   /api/v1/registry?chromosome=datasets   检索
  POST  /api/v1/genes/{id}/compose   杂交（组合）
  POST  /api/v1/genes/{id}/mutate    诱变（新版本）
  
黑板调度（基因操作经任务卡，延续 v1.1 协议）：
  action=gene.* （gene.get/gene.compose/gene.splice）
  schema 校验器扩展：gene 类 action + manifest 校验
  本地展开器：机械基因操作本地展开，复杂（设计实验）在线
```

## 七、与现有架构衔接

- **调度**：基因操作经黑板任务卡（v1.1 协议 + 校验器生死线）
- **展开**：机械指令（compose/splice）本地模型，复杂（实验设计）在线
- **数据沉淀**：i9 scan 结果 → 新基因注册（provenance=i9-scan-*）
- **算力调度**：`expression.trainable` 声明 → 调度到 i9 GPU 或 mac 本地
- **知识链**：`chromosome=knowledge` 资产 ↔ KB/ChromaDB 同步

## 八、落地示例（flower-yolo）

```json
{
  "gene_id": "sha256:aaaa...",
  "name": "flower-yolo-v1",
  "chromosome": "datasets",
  "body": {"path": "E:\\Genebank\\datasets\\flower-yolo", "size_bytes": 3200000000, "format": "yolo", "checksum": "abc"},
  "expression": {"trainable": "yolo", "inferable": false, "retrievable": false, "composable": ["recipe"]},
  "heredity": {"parent_genes": [], "mutation": "1.0.0", "provenance": "mac-share-20260823"},
  "phenotype": {"quality": 0.95, "evaluated_by": "i9-training"}
}
```

训练配方（杂交 flower-yolo + yolov8n + 参数）→ recipes 染色体新基因，血缘指向 flower-yolo 基因。

## 九、版本历史

- v0.1（草案）：概念设计，五类染色体
- v0.2（定稿，用户确认）：GeneBank 命名 + 混合命名 + 六类染色体（含 recipes）+ 自进化 + manifest schema 完成 + API 落地路径

---
*GeneBank 存储协议 v0.2 · AI 网盘 · 协调者 2026-08-23*
