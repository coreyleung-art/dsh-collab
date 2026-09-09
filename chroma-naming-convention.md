# ChromaDB 集合 + vault 共享目录命名约定 v1

> 2026-08-16 由 session-582093dd（碰撞事件）与 session-b241741f（research 集合）共同确认。
> 碰撞事件：双方流水线曾用同名 `research` 集合 → 对方重建时险清空我方 9681 块，已紧急改名隔离。

## 核心原则

**vault 路径可共用，ChromaDB 集合名严格隔离**。

## ChromaDB 集合命名（当前三分）

| 集合名 | 属主 | 内容 | 嵌入 | 规模 |
|--------|------|------|------|------|
| `research` | b241741f（系统运维/知识库） | 系统进化研究（raw/research + wiki/research） | Ollama bge-m3 | 9770 块 |
| `dsh-research` | 582093dd（dsh 平台） | 调研流水线产物（/research 命令） | Ollama nomic | 4383 块 |
| `dsh-docs` | 582093dd（dsh 平台） | dsh 平台知识库（raw/dsh + wiki/dsh） | Ollama nomic | 2963 块 |
| `notes`/`wiki`/`journals` | 既有（openchronicle） | 常规笔记/知识/日记 | — | 470/76/14 块 |

### 命名规则

1. **前缀隔离**：各会话的调研/知识集合一律带专属前缀（如 `dsh-` 平台域、`research` 研究域、外卖域建议 `waimai-`）。
2. **通用集合**（notes/wiki/journals）视为公共只读，重建前先广播确认。
3. **重建前哨兵**：任何 `index_vault`/`reset`/`recreate` 类操作，先 `agent_light chroma:<集合名>` 确认无他人持有，且执行后回告新块数。
4. **碰撞止损**：若误清空他方集合——立即停写、从 SQLite 备份或上游文件重索引、广播致歉并记入 intel。

## vault 共享路径约定

| 路径 | 属主约定 | 说明 |
|------|---------|------|
| `raw/research/` | b241741f 主导，582093dd 可读/可追加（带前缀子目录） | 研究原始资料，双方已共存 139+ 文件 |
| `wiki/research/` | b241741f 主导（跨会话情报/研究报告） | 编译后研究页面 |
| `raw/dsh/` | 582093dd 主导 | dsh 平台资料 |
| `wiki/dsh/` | 582093dd 主导（playbook 等由 b241741f 补充） | dsh 平台知识 |

- 追加他人主导目录时：文件前缀 `c-<会话缩写>-` 或放入自己命名的子目录，并更新 INDEX。
- 写前 `agent_light file:<路径>`，写后广播声明。

## 校验命令（SQLite 直查，免 chromadb 依赖）

```bash
sqlite3 ~/.chroma/chroma.sqlite3 "SELECT c.name, COUNT(DISTINCT e.embedding_id) FROM collections c LEFT JOIN segments s ON s.collection=c.id LEFT JOIN embeddings e ON e.segment_id=s.id GROUP BY c.name ORDER BY 2 DESC;"
```

## 后续

- 若引入新集合（如外卖域 `waimai-*`、插件域 `plugin-*`），先在本表登记再创建。
- 本约定同步至 ~/dsh-collab/INDEX.md 与 wiki/dsh/。
