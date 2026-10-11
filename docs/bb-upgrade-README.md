# bb-upgrade.py · 存量脚本补课文档

> 路径 `~/dsh-collab/scripts/bb-upgrade.py` · 形态：独立 py 脚本（非 dsh 插件）
> 本文档满足 R006 ⑤ 与 R039（工具中文描述文档）· 2026-10-03 存量补课（r006-retrofit-scripts.js 生成）

## ① 为什么需要（事故/证据）

存量工具对齐（用户指示 2026-10-03）：此前该脚本无版本声明、无中文文档，读者无法独立复现。
本批按 R006 独立工具口径补齐三件：版本常量单一来源、本中文文档、显式偏离声明。

> 脚本自述：bb-upgrade.py — 底座升级流水线（进化循环第 2 步，半自动）；标准化底座升级流程：版本递增 → 注入变更 → 语法检查 → 起测试实例 → 冒烟测试 →；切换 plist → 验证生产 → 落链（黑板+registry）→ 复用评估（自动调 bb-reuse-check）。；用法：；python3 bb-upgrade.py --from v0.5 --to v0.6 --script scripts/blackboard-server-v0.6.py；--what "新增能力描述" --deps "依赖" --hub-dep "中枢依赖" --node-side "节点侧"；python3 bb-upgrade.py --dry-run --from v0.5 --to v0.6 --script <path>   # 只跑到测试；流程步骤（每步打印 + 可选 --dry-run 截断）：

## ② 用法（含退出码）

```bash
python3 ~/dsh-collab/scripts/bb-upgrade.py --help   # 用法以脚本自身 --help 为准
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
head -20 ~/dsh-collab/scripts/bb-upgrade.py   # 看 docstring 与版本常量
python3 ~/dsh-collab/scripts/doc-cn-check.py ~/dsh-collab/docs/bb-upgrade-README.md
```
