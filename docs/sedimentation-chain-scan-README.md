# sedimentation-chain-scan.py · 存量脚本补课文档

> 路径 `~/dsh-collab/scripts/sedimentation-chain-scan.py` · 形态：独立 py 脚本（非 dsh 插件）
> 本文档满足 R006 ⑤ 与 R039（工具中文描述文档）· 2026-10-03 存量补课（r006-retrofit-scripts.js 生成）

## ① 为什么需要（事故/证据）

存量工具对齐（用户指示 2026-10-03）：此前该脚本无版本声明、无中文文档，读者无法独立复现。
本批按 R006 独立工具口径补齐三件：版本常量单一来源、本中文文档、显式偏离声明。

> 脚本自述：sedimentation-chain-scan.py v1.0 — 自动沉淀交付链 · 待沉淀清单扫描器（纯规则，零 LLM）；职责：扫描 event-bus 的 task.completed 事件 → 按「是否新建脚本/文档/踩坑修复」信号；→ 判定「值得沉淀 / 跳过」→ 生成「待沉淀清单」（值班 HR/协调者按决策表执行七步链）。；B+ / C 两用：；B+ 模式（默认）: 只扫描+生成清单，人工执行沉淀（值班 HR/协调者）；C  模式（--auto）: 生成清单后自动执行本地环节（判定/查重/向量化/登记）——；仅「工具化写脚本/提炼总结」按置信度门控升级订阅。；零 LLM 判定信号（纯规则，不调模型）：

## ② 用法（含退出码）

```bash
python3 ~/dsh-collab/scripts/sedimentation-chain-scan.py --help   # 用法以脚本自身 --help 为准
```

退出码约定按脚本自身实现；本批未改动脚本逻辑（只加版本常量与文档）。

## ③ R006 达标矩阵（独立工具口径）

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ⚠️ 显式偏离（声明） | 独立脚本，非插件形态；按 R006 §2 独立工具口径交付 |
| ② TCC 检测 | ⚠️ 部分 | 无 --selfcheck；能力边界见本文档 |
| ③④ CLD/版本自适应 | ✓ | 不依赖宿主内部 API |
| ⑤ 文档化 | ✓ | 本文件 |
| ⑥ 版本管理 | ✓ | 版本常量单一来源（脚本内唯一声明处） |
| ⑦ 统一日志 | ⚠️ 部分 | 以脚本自身输出为准 |
| ⑧ 自动落链 | ⚠️ 待登记 | 合规矩阵 JSON 收录 |
| ⑨ CLI 治理 | ⚠️ 部分 | 按脚本自身参数约定 |
| ⑩ 约束前置 | N/A | 无「不该发生路径」类危险操作（如涉及需单独评审） |

## ④ 坑（如实）

1. 本文档由补课生成器生成；docstring 摘录自脚本头部，若与实际行为不符以源码为准。
2. 脚本逻辑本批**未改动**——只新增版本常量与文档，行为零变化。

## ⑤ 复现命令

```bash
head -20 ~/dsh-collab/scripts/sedimentation-chain-scan.py   # 看 docstring 与版本常量
python3 ~/dsh-collab/scripts/doc-cn-check.py ~/dsh-collab/docs/sedimentation-chain-scan-README.md
```
