# dsh-plugin-self-report-gate

> 自述可证性门（R-SR）的**宿主侧入口**：SR1 现场重测 / SR2 阳性对照 / SR3 撤回传播 / SR4 写盘自证 / SR5 环境指纹 / SR6 修复路径覆盖

由 **PSTD PSTD/1.0.4** 按模式 `P2_bundled_plugin` 生成骨架，随后接入真实内核（见 `CHANGELOG.md` · Unreleased）。

## ★ 设计主张：本插件不是判据的第二个实现

R-SR 门（SR1–SR6）的**唯一实现**是：

```
~/dsh-collab/scripts/self-report-gate.py
```

本插件**只调用、不重写**。JS 侧职责仅四项：① 定位门与环境 ② 白名单校验 ③ 转调 ④ 原样回报。

**为什么刻意这样做**：如果在 JS 里再实现一遍 SR1–SR6，就会出现两套逻辑各自演化、互不同步 ——
而那正是本门要检出的缺陷形状（同一事实两个来源）。**审查工具自己犯它要检出的错，是最坏的一种失败。**

## 用法与退出码

```bash
NODE=/opt/homebrew/bin/node      # 本机 PATH 常不含 node，见下「③ CLD 自适应」
cd ~/dsh-collab/devices/dsh-plugin-self-report-gate
$NODE cli.js --help
$NODE cli.js --selfcheck         # 能力清单 / 不该发生路径 / 依赖完整性 + 真挂载冒烟（三态）
$NODE cli.js --lean4-check       # 约束门六项 A–F 自证
$NODE cli.js --tool-version      # 本包版本（唯一来源 package.json）
$NODE cli.js --dry-run --json    # 零变更演练（不派生子进程、不写盘）
```

退出码：`0` 成功 · `1` 失败/门失效 · `2` 用法或 IO 错误。

## 宿主工具

工具名 `self_report_check`，参数 `action` ∈ `{status, version, selftest, check}`（冻结枚举），
`check` 需附 `claim_path`（受控根内的 R046 声明体 JSON）。

| action | 做什么 | 写盘 |
|---|---|---|
| `status` | 探测 python3 与门脚本是否在位，回报 PATH / node / 候选路径 | 否 |
| `version` | **现场读取**门版本（不硬编码会变的值） | 否 |
| `selftest` | 转调门的自测矩阵并原样回报 | 否 |
| `check` | 对受控根内声明体转调门检查，原样回报 stdout | 否 |

## R006 达标矩阵（**自查口径，逐项如实**）

| 项 | 判据 | 本包状态 |
|---|---|---|
| ① dsh 插件形态 | package.json + cordis.patch.yml + `apply` + **真挂载冒烟** | 已生成；冒烟在 `--selfcheck`，三态分开报 |
| ② TCC 自检 | 三段输出（能力 / 不该发生 / 依赖） | `lib/selfcheck.js`，5+5 条已填实 |
| ③ CLD 自适应 | 不假设 PATH、不假设 peer 位置 | 已实现：python3 候选探测 + peer 三级解析 |
| ④ dsh 版本自适应 | peerDependencies 全声明 | 已满足 |
| ⑤ 文档化 | 本文件 + `r006.documented` | 已满足 |
| ⑥ 版本单一来源 | package.json 唯一 | 已满足（`cli.js` 从 package.json 读） |
| ⑦ 统一日志 | `~/dsh-collab/logs/dsh-plugin-self-report-gate.log` | **未接入（如实登记）** |
| ⑧ 自动落链 | `data/registry/dsh-plugin-self-report-gate` | **未登记（如实登记）** |
| ⑨ CLI 治理 | 未知旗标 exit 2 / dry-run / json | 已满足（实测 `--bogus` ⇒ rc=2） |
| ⑩ 约束门 | 冻结枚举 + 负例矩阵 + 命令/路径白名单 | `lib/gate.js` + `--lean4-check`；负例 7 / 正例 4 |

## ③ CLD 自适应：本机实测到的事实（不是假设）

```bash
$ echo $PATH
/usr/bin:/bin:/usr/sbin:/sbin          # ← 没有 /opt/homebrew/bin
$ command -v node ; echo $?
1                                       # ← node 不在 PATH 里
$ ls -d /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules
... exists                              # ← peer 只在这里
```

⇒ 因此：**命令一律用探测到的绝对路径**；`lib/gate.js` 的目录白名单同时防止「basename 伪装」。

## 坑（都踩过）

1. **门太宽**：把合法键也当违规 → 先精确白名单命中，再对非白名单输入判禁用词。
2. **扫描器误伤自己**：扫源码前先剥注释/字符串/正则字面量，否则自己的检测正则会被当靶子。
3. **空洞通过**：剥离字面量后读不到实参 → 调用点枚举为 0 → 「0 ⊆ 允许」假通过。
4. **假失败**：依赖解析不到就说插件挂不上 —— 应先分辨「环境问题」与「包问题」。
5. **两处版本**：`const VERSION` 与 package.json 各写一份必然漂移，只留 package.json。
6. ★ **放宽一个门时要同时收紧另一维**：把「首 token 白名单」改成「basename 白名单」会开出
   `/tmp/evil/python3` 这类旁路 ⇒ 必须补目录白名单，否则修一个假拒换来一个真旁路。

## 复现命令

```bash
cd ~/dsh-collab/devices/dsh-plugin-self-report-gate
NODE=/opt/homebrew/bin/node
$NODE cli.js --selfcheck | head -40
$NODE cli.js --lean4-check | head -20
$NODE cli.js --tool-version
$NODE cli.js --bogus ; echo "rc=$?   # 期望 2"
```

## 下一步（S4 / S5）

1. **S4**：patch 到属主侧 —— `gate-auditor.py` 的 `STRUCTURAL_TOOLS` 登记 · `types.json` 增 `self_report` 类型 · `RULES.md` 增条目。
2. **S5**：接入 ⑦ 日志与 ⑧ 落链后收口，并跑 `plugin_review(target="dsh-plugin-self-report-gate", deep=true)`。
