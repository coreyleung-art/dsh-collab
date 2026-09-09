# GeneBank 上传下载 · token 最小化模式

> 日期：2026-08-23 · 协调者 fa1f9150 · 用户问「ai 网盘上传下载能否不消耗或最小化 token」
> 结论：**当前实现已零 token**（HTTP 字节流 + 规则 manifest），最小化模式=资产处理全程本地化/规则化，LLM 只做非做不可的事且用本地模型

## 一、直接回答：上传下载零 token

| 环节 | 实现 | token 消耗 |
|---|---|---|
| 上传（资产→基因）文件传输 | HTTP PUT 字节流（genebank-server /api/v1/genes） | **0**（字节流非 LLM） |
| 上传 manifest 生成 | scan-to-genebank.py 纯规则（路径/类型/大小→染色体映射） | **0**（无 LLM） |
| 下载/调用（基因→使用） | HTTP GET 字节流 | **0** |
| 检索（registry.search） | 本地精确查询（按染色体/名称/gene_id） | **0**（无 LLM） |
| 基因操作（register/query/list） | 本地 HTTP + JSON | **0** |

**上传下载过程完全零 token**——LLM token 是模型推理计量，文件字节流传输不产生 token。

## 二、可能引入 token 的环节（如何避免/门控）

| 潜在 LLM 环节 | 默认策略 | 门控 |
|---|---|---|
| 资产描述（给基因写 description） | **跳过**（manifest 不含 description，或本地 qwen2.5:3b 零订阅生成） | 本地模型，零订阅 |
| 资产分类（自动归类染色体） | **规则映射**（类型→染色体表，已实现） | 规则优先，未知类型才问本地模型 |
| 语义检索（按含义搜基因） | **本地向量**（bge-m3 零订阅 embedding）而非在线 embedding | 本地嵌入，零订阅 |
| 组合规划（compose 方案设计） | **规则模板**（预定义配方模式） | 复杂设计才用本地模型 |
| 摘要/提炼（资产内容摘要） | **跳过**或本地模型 | 本地模型，零订阅 |

## 三、最小化 token 模式（设计原则）

```
原则 1：传输零 token——上传下载永远是 HTTP 字节流，不经过 LLM
原则 2：manifest 规则化——路径/类型/大小/可复用性 → 染色体映射（纯规则表）
原则 3：检索本地化——精确查询本地 + 语义检索用本地 bge-m3（零订阅）
原则 4：LLM 门控——描述/摘要/组合规划仅用本地 qwen2.5:3b，且「可跳过」优先
原则 5：级联兜底——本地不可用才升级（复用 route-learner FrugalGPT 级联思路）
```

## 四、当前实现验证（零 token 证据）

- scan-to-genebank.py：无 LLM 调用（grep 确认），manifest 纯规则
- genebank-server.py：HTTP + JSON，无 LLM 调用
- 校验器 gene.* ：纯规则校验（manifest 必填/染色体枚举/gene_id 格式）
- 完整链路（scan → manifest → 注册 → 检索）零 LLM

## 五、未来增强（保持零 token）

1. **基因描述**：本地 qwen2.5:3b 生成（零订阅）或留空（manifest 描述可选）
2. **语义检索**：本地 bge-m3 向量索引（复用现有 ChromaDB 基础设施）
3. **组合配方**：规则模板（预定义 recipe 模式）优先
4. **监控**：genebank.log 记录每次操作类型，若引入 LLM 环节可审计 token

## 六、结论

**GeneBank 上传下载零 token 已达成**（纯 HTTP 字节流 + 规则 manifest）。最小化模式=「资产处理全程本地化/规则化，LLM 仅本地模型且可跳过」——这正好复用本系统已验证的「本地优先 + 零订阅」成本治理原则（外卖自动化、本地展开器、事件驱动同一范式）。

---
*GeneBank token 最小化模式 v1.0 · 协调者 2026-08-23*
