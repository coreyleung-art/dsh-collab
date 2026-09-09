# 论文流水线 · 工具化自动化说明（paper-pipeline）

> 数据调查员 4787d717 · 2026-08-20 · 用户指示：过程插件化工具化自动化

## 链路（5 步）
arxiv_sync(增量拉新) → download(下载 PDF) → extract(全文抽取) → ingest(KB 入库+向量化) → registry(登记)

## 组件（已就绪）
| 组件 | 路径 | 性质 |
|------|------|------|
| arxiv_sync.py | ~/papers-db/ | CLI（papers-db 增量 + 主题归位 + bge-m3 向量） |
| download_papers.py | paper-cache/ | CLI（arXiv PDF 批量下载，礼貌限速，已有跳过） |
| 抽取+入库 | DSH 工具（dshdoc_extract + knowledge_*） | 需 DSH 会话内调用 |
| REGISTRY.md | paper-cache/ | 落链登记 |

## 自动化（两级）
### A 级：CLI 自动（可 launchd 定时）——arxiv_sync + download
```bash
launchctl bootstrap gui/$(id -u) ~/dsh-collab/research/paper-cache/com.investigate.paper-sync.plist  # 每日 3:00
```
⚠️ 默认不启用（成本治理）；用户明确开启时执行。产出：papers-db 增量 + 新 PDF 落盘。

### B 级：DSH 工具自动（抽取+入库）——需会话内调用
一键流程（run_code 模板，见下）：
1. glob 新 PDF（texts 缺失的）
2. dshdoc_extract 批量抽取 → texts/
3. knowledge_add_document 入库（KB paper-cache）
4. 更新 REGISTRY + 报告

## 一键流程（run_code 复制即用）
```js
// paper-pipeline 一键：新 PDF → 抽取 → 入库
const pdfs = await tools.glob({pattern:"*.pdf", path:".../paper-cache/pdfs"});
const done = await tools.glob({pattern:"*.txt", path:".../paper-cache/texts"});
const todo = pdfs.paths.filter(p => !doneSet.has(...));
// 循环 dshdoc_extract → write texts/ → knowledge_add_document → 更新 REGISTRY
```

## 触发方式（按成本治理）
- 手动：用户/协调者指示时执行一键流程
- 定时 B 级：DSH 侧无 cron（工具依赖会话）；可由黑板指令触发（事件驱动）
- 定时 A 级：launchd plist（用户启用后，每日拉新下载；抽取入库随黑板提示手动/半自动）

## 插件化（当 cordis 工具面可用时）
- 可注册动态插件工具：paper_pipeline（一键）/ paper_sync_status（查询）——cordis_define + run
- 当前 Code Mode 无 cordis 工具面，先以 run_code 模板 + CLI 双形态落地

## 双写 + 自检（2026-08-31 升级，防索引断层）
- **落链双写**：新论文一次完成 texts/ + KB paper-cache + papers-db（papers 表+topics+bge-m3 embedding）
- **审计自检**：audit_papers.py（三处一致性：texts ↔ papers-db ↔ KB；输出缺口清单；--fix 自动回填）
  - 落链完成后自动跑一次（管道内自检）
  - 按需全量：python3 audit_papers.py / audit_papers.py --fix
  - 当前状态：192/192 一致，无缺口（2026-08-31 实测）
- **组件**：backfill_papers_db.py（存量回填）/ audit_papers.py（审计修复）/ download_papers.py / arxiv_sync.py / fetch_alphaxiv.py
