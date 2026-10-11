# bb-prep-learn.py · 存量脚本补课文档

> 路径 `~/dsh-collab/scripts/bb-prep-learn.py` · 形态：独立 py 脚本（非 dsh 插件）
> 本文档满足 R006 ⑤ 与 R039（工具中文描述文档）· 2026-10-03 存量补课（r006-retrofit-scripts.js 生成）

## ① 为什么需要（事故/证据）

存量工具对齐（用户指示 2026-10-03）：此前该脚本无版本声明、无中文文档，读者无法独立复现。
本批按 R006 独立工具口径补齐三件：版本常量单一来源、本中文文档、显式偏离声明。

> 脚本自述：bb-prep-learn.py — 提前学习扫描器（R025 学习调查类提前并行）；用户指示（2026-08-31）：把『提前学习』输出为符合 R006 九标准的工具。；功能：扫描蓝图 taskboard 的 todo 卡 → 识别可提前学习类（数据学习/规则学习/模型学习）→ 插卡标记 prep_ahead + 生成委派清单。；R006 九标准：① CLI 形态（dsh 插件化预留）② TCC 检测（--selfcheck）③ CLD 自适应（无耦合）④ dsh 版本自适应 ⑤ 文档化（README）⑥ 版本管理（--tool-version）⑦ 统一日志（黑板落链）⑧ 自动落链（黑板 taskboard）⑨ CLI 治理（argparse）；用法：；python3 bb-prep-learn.py --scan                # 扫描 todo 卡，识别可提前学习项；python3 bb-prep-learn.py --insert --who 知了    # 自动插卡（识别结果 → taskboard）；python3 bb-prep-learn.py --selfcheck           # TCC 自检（语法+依赖）

## ② 用法（含退出码）

```bash
python3 ~/dsh-collab/scripts/bb-prep-learn.py --help   # 用法以脚本自身 --help 为准
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
head -20 ~/dsh-collab/scripts/bb-prep-learn.py   # 看 docstring 与版本常量
python3 ~/dsh-collab/scripts/doc-cn-check.py ~/dsh-collab/docs/bb-prep-learn-README.md
```
