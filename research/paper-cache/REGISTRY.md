# 论文全文落链登记表（paper-cache registry）

> 维护：数据调查员 4787d717 · 首期：2026-08-20 · 落链制度 5 步：落盘→入库→向量化→登记→报告

## 目录
- 缓存根：~/dsh-collab/research/paper-cache/
- PDF 库：pdfs/（arXiv ID.pdf）
- 清单：arxiv-ids.txt（149 条，来自 papers-db）
- 脚本：download_papers.py（增量可复用，礼貌限速 3s）

## 状态
| 项 | 值 |
|----|----|
| 清单源 | papers-db（149 篇 seed+arxiv_sync 增量） |
| 首期下载 | ✅ 149/149 完成（paper-cache/pdfs/） |
| 全文抽取 | ✅ 149/149 抽取（texts/） |
| 知识库入库 | ✅ knowledge base paper-cache（149 篇，chunked+embedded） |
| 向量化 | ✅ knowledge 库自动 chunked+embedded（bge-m3 配置时） |

## 增量机制（成本治理下不配自动定时）
- 脚本就绪：download_papers.py + arxiv_sync.py（papers-db 增量）
- 触发：手动/按需（成本治理恢复后可由用户或协调者安排定期）

## 更新记录
- 2026-08-20：首期拉取启动，registry 建立
- 2026-08-20：首期 26 篇抽取+入库完成，下载后台续跑- 2026-08-20：149/149 全部下载+抽取+入库完成

## 2026-08-31 双轨审计回填
- 存量双轨审计（data/ops/paper-dual-track-audit-20260831）：43 篇有全文缺 papers-db 索引 → 已回填（backfill_papers_db.py）
- papers-db 总量 149→192 篇，embedding 192 条
- 落链管道改双写：texts/ + KB paper-cache + papers-db 一次完成（PIPELINE.md 已更新）
