# 知识持续更新机制（知识飞轮 · M2 运营）

> 建立：2026-08-19 · HR · 用户确认「持续更新」后沉淀 · 衔接 local-knowledge-asset-strategy.md（飞轮 M2）

## 自动化保障（2026-08-22 强化）

- **入库即向量化**：knowledge_import_url / knowledge_add_document 自动嵌入（KB embedded=true，无需手动确认）
- **每日自动验证**：kb-health.py（每日 09:25）检查索引文件一致性/异常告警——**不依赖人工提醒**
- **索引自动更新**：kb-index-gen.py 随入库重生成（subagent/角色入库后执行或 HR 统一）
- **流程纪律**：任何论文/文档入库 = 向量化自动完成 + 每日巡检兜底验证，用户无需介入

## 触发条件

以下任一发生 → 增量索引（无需全量重跑）：

1. 新讨论沉淀：花店演进/战略/规则等新内容写入 vault（wiki/ 页、raw/ 原始页、日记/）
2. 规则更新：J 规则集新增/修订（policy → vault 规则页同步后）
3. 会话摘要：重要对话结束后写日记并索引

## 操作流程

```
沉淀（write vault 页面/日记）
  → 增量索引（~/.claude/automation/hr-kb-index.py <rel path>）
  → 验证（chroma_search 命中新页面）
  → 登记（wiki/log.md + registry）
```

## 工具

| 工具 | 用途 | 备注 |
|---|---|---|
| hr-kb-index.py | 增量索引指定页面（可多文件） | **中文路径需硬编码在脚本内**（bash 传参会损坏中文目录名） |
| index-vault.py | 全量重索引（954 文件） | 后台 nohup 跑（>300s 前台会超时），日志 logs/full-index-YYYYMMDD.log |
| chroma_search | 验证命中 | lib 直调 |

## 本次落地（2026-08-19）

- 增量索引 5 页面：J41 规则页 18 + 花店演进 26 + 原始思考 10 + 今日日记 7 = **61 chunks**
- 全量重索引后台进行中（PID 49116，日志 logs/full-index-20260819.log）

*HR · 2026-08-19*