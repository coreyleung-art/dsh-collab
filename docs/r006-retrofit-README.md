# r006-retrofit.js · 存量插件 R006 补课生成器

> 版本 1.1（版本单一来源：脚本内 `const VERSION`——本工具随脚本演进，版本记录于 CHANGELOG 与登记卡）
> 路径 `~/dsh-collab/scripts/r006-retrofit.js` · 满足 R039（本文件中文字符 > 100）。

## ① 为什么需要（事故/证据）

用户指示「对存量所有工具进行标准对齐」（2026-10-03）后，首轮盘点 274 个存量工具中 262 个有缺口。
逐个人工补课不可规模化——本生成器把「四文件补课」（中文文档 / selfcheck 真挂载冒烟 / cli 治理入口 /
CHANGELOG 与 peer 声明）固化为可复跑程序，每插件输出 selfcheck 与 doc-cn 的**实测结果**（含三态，
绝不伪装通过）。

## ② 用法（含退出码）

```bash
node r006-retrofit.js <插件目录...>      # 增量补课 + 每插件实测回报
```

- 增量语义：已达标文件不覆盖（CHANGELOG / 中文文档 ≥100 字 / 既有 cli.js 保留）。
- 必做动作：version 缺失补 1.0.0；import 了未声明的 `@deepseek-ai/*` peer → 补 peerDependencies 声明；
  缺 peer 软链补齐。
- 退出码：0 全部完成（含实测记录）· 1 某插件实测失败（如实报告）· 2 用法错误。

## ③ R006 达标矩阵

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | N/A | 本工具是独立脚本（治理工具，不挂宿主）；按 R006 独立工具口径声明偏离 |
| ② TCC 检测 | ✓ | 输出即实测三态（pass/fail/skipped/fail-to-verify） |
| ③④ CLD/版本自适应 | ✓ | 零宿主依赖，仅 node 内置 + 系统命令（python3 doc-cn 探测） |
| ⑤ 文档化 | ✓ | 本文件 |
| ⑥ 版本管理 | ⚠️ 单一来源在脚本头注释；独立工具口径 | |
| ⑦ 统一日志 | ⚠️ 无专用日志（批次结果 stdout + 矩阵落盘） | |
| ⑧ 自动落链 | ✓ | 合规矩阵 JSON + 登记卡随批更新 |
| ⑨ CLI 治理 | ✓ | 无参数→用法提示；未知旗标→exit 2（本工具旗标=位置参数） |
| ⑩ 约束前置 | ✓ | 只写目标插件目录内 4 类文件；已达标不覆盖（增量幂等） |

## ④ 坑（实测）

1. **空集通过**：inject tools 但源码抽不到工具名 → 报 `fail-to-verify` 拒绝假绿（本工具自己的门）。
2. **编译产物插件**（如 dock-cards 的 index.js 是 TS 转译件）：import 扫描不可靠，peer 补声明可能漏/误抓
   （误抓过 `dsh-typert-protocol`）——此类插件必须人工核对注册形态，生成器只负责暴露。
3. **真挂载冒烟 ≠ 宿主真挂载**：桩 ctx 的 no-op 代理只能验证「apply 不因缺服务崩溃 + 工具注册」，
   宿主内真实行为仍需 `--dump-config`/挂载验收另证。

## ⑤ 复现命令

```bash
node ~/dsh-collab/scripts/r006-retrofit.js dsh-plugin-xxx   # 单插件补课+实测
python3 ~/dsh-collab/scripts/doc-cn-check.py ~/dsh-collab/docs/r006-retrofit-README.md
```
