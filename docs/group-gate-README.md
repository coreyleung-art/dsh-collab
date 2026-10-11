# group-gate.py · 存量脚本补课文档

> 路径 `~/dsh-collab/scripts/group-gate.py` · 形态：独立 py 脚本（非 dsh 插件）
> 本文档满足 R006 ⑤ 与 R039（工具中文描述文档）· 2026-10-03 存量补课（r006-retrofit-scripts.js 生成）

## ① 为什么需要（事故/证据）

存量工具对齐（用户指示 2026-10-03）：此前该脚本无版本声明、无中文文档，读者无法独立复现。
本批按 R006 独立工具口径补齐三件：版本常量单一来源、本中文文档、显式偏离声明。

> 脚本自述：group-gate v1.0.0 (HR) - 群聊治理门 (R006 十项标准 / 2026-09-07)；职责: 群聊(群发广播线程)治理——开群前决策树评估(check), 存量群健康审计(audit)。；实证: 群聊上下文放大 20.8x(消息x参与者), 40+ 人大群是资源黑洞。；规范: docs/group-chat-governance-v1.md (G1-G4 分类 + C1-C6 约束)。；R006: 1插件(P2) 2selfcheck 3cld-check 4version-check 5README 6--version 7日志 8落链 9CLI 10lean4-check；用法:；group-gate.py check --desc "<场景>" [--participants N] [--mutual yes/no] [--duration once/temp/long]；group-gate.py classify --desc "<场景>"

## ② 用法（含退出码）

```bash
python3 ~/dsh-collab/scripts/group-gate.py --help   # 用法以脚本自身 --help 为准
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
head -20 ~/dsh-collab/scripts/group-gate.py   # 看 docstring 与版本常量
python3 ~/dsh-collab/scripts/doc-cn-check.py ~/dsh-collab/docs/group-gate-README.md
```
