# dsh-plugin-context-survival

**上下文存活守卫（K2 只测量）** — 在会话到达压缩器开销下界**之前**，用一个 **N→1、有界、非摘要**的检查点把活跃窗口压下去；与官方 `compaction-basic` **并存**，不接管 `ctx.compaction`。

> **当前阶段 = K2**：守卫已能**测量压力并判定阈值**（`lib/budget.js` + `lib/guard.js`），但**只测量、只记录**——
> 不产出检查点、不替换表面。检查点产出与表面替换在 **K3**。默认 `enableGuard: false`，且**尚未挂载**。
>
> **K2.1（2026-10-10）**：阈值加了第三项**抢先上限** `preemptCeil = floor(cw × 0.70)`，使本守卫**严格早于**
> 官方 `compaction-basic` 的 `floor(cw × 0.8)` 触发（原值 `min(0.9cw+8000, 0.95cw)` 反而**晚** 108,000）。
> 这是 K0–K2 复盘查出 F1（规格内部矛盾）后的裁决结果，见坑 11。

> 立项书：`~/dsh-collab/docs/project-init-context-survival-backend-20261010.md`
> 执行依据：`~/dsh-collab/docs/context-survival-conservative-plan-20261009.md`
> 锚点：`~/dsh-collab/docs/distributed-agent-network-governance-plan-v4-20261009.md`（§7.8 P26 + Q-K）

## 为什么存在（要解决的问题）

P26 = 会话硬死锁，两个机制叠加：

- **机制一（阈值不可达）** — 压力阈值 `floor(cw×thresholdRatio)` 落在消息侧上限之上 ⇒ 主动压缩永不触发。**已修**（配置层，`~/.dsh/settings.yaml`）。**这个不是本插件治的。**
- **机制二（模板地板，终局杀手）** — 官方压缩器 `frameSummary` 的输出必须 `< shadowedTokenCount`，而摘要指令**强制 8 段**、禁删段 ⇒ 存在**结构性下界**；活跃窗口低于该下界时，压缩器**判不动**，且失败时**只告警、无兜底**。**源码核实：无任何配置键可改模板或判据** ⇒ 只能代码层解。

**本插件的立论**：机制二的病是"判不动 = 永久失效且不告警"。本插件要么产出**严格更小**的活跃窗口，要么**明确判"不可压"并告警**——绝不静默 no-op。

## 六条不变量（违反任一条 = 设计失败）

| # | 不变量 |
|---|---|
| **I1** | **保证能减**：要么产出严格更小的活跃窗口，要么明确判"不可压"并告警——绝不静默 no-op |
| **I2** | **不摘要**：检查点由原文片段 + 指针组成，不做模型生成（结构上不存在 `summary < shadowed` 判据） |
| **I3** | **最新保活**：`retainTokens` 窗口内逐字保留 |
| **I4** | **并存不独占**：`ctx.compaction` 仍归官方；本守卫崩溃/拒动时官方行为零变化 |
| **I5** | **可召回**：被压掉的每一段都有 `seq` 指针，可逐字找回 |
| **I6** | **交接可续**：检查点带结构化交接字段，供跨会话信标四件套复用 |

## 工具（N4 前缀 `csx`）

| 工具 | 作用 | 状态 |
|---|---|---|
| `csx_status` | 只读：版本 / 阶段 / 不变量 / 结构门 / **K2 守卫读数** | ✅ 可用（只读） |
| `csx_checkpoint` | 手动插入非摘要检查点 | ⏳ 未实现（K3），如实返回 `implemented:false` |
| `csx_recall` | 按 `seq`/`range`/`checkpoint` 逐字取回 | ⏳ 未实现（K4），**schema 层结构约束已在位** |

## K2 守卫（只测量）——两条来源与三个判据

`lib/budget.js` 是**纯决策核**（零 import、零 I/O、逐位确定），`lib/guard.js` 是**观察器**（把宿主对象读成一条读数）。
三者都照官方源码对齐，不靠猜：

| 判据 | 公式 / 语义 | 官方对照 |
|---|---|---|
| **预算** | `usable = floor(cw×usableRatio)`；`limit = min(maxTokens, floor(cw×limitRatio))`；`threshold = min(limit + bufferTokens, usable, preemptCeil)` | 前两项是 ctxwin 形态；`threshold ≤ usable` 由构造保证 |
| **抢先** | `preemptCeil = floor(cw×preemptRatio)`，`preemptRatio` 默认 **0.70** 且**强制 < 0.8** | 官方在 `floor(cw×0.8)` 触发（`:13 DEFAULT_THRESHOLD_RATIO`）；够不着就晚于官方，立论落空 |
| **触发** | `measured < threshold ⇒ 不压`（**相等即压**） | `dsh-compaction-basic/lib/index.js:882` |
| **下界** | 检查点必须**严格小于**被遮内容且省 ≥ `minSavingsTokens` | 同文件 `:556`（官方**没有**这条余量判据，故会死锁） |

实测对照（独立 Python 复算与 `resolveBudget` 逐位相同）：

| cw | 本守卫阈值 | 官方阈值 | 早多少 |
|---|---|---|---|
| 8,192 | 5,734 | 6,553 | 819 |
| 131,072 | 91,750 | 104,857 | 13,107 |
| 1,000,000（本机 deepseek） | **700,000** | 800,000 | **100,000** |
| 1,048,576 | 734,003 | 838,860 | 104,857 |

服务一律用 **`ctx.get()`** 取（`tokenMeter` / `llm`），**不写进 `inject`** —— 见坑 6。

K2 的验收 = **`node cli.js --budget-check`**：进程内跑 170 条断言（预算 121 + 守卫 49），
每条期望值都是手写的；末尾打印 `sha256` 摘要，两次独立进程运行摘要相同 ⇒ 逐位确定。

## 结构约束（R006 ⑩：让不该发生的路径在语法上不存在）

1. **零外部命令** — `ALLOWED_COMMANDS = []`（冻结空集）。`--lean4-check` A 项证明源码里**执行点个数为 0**（能力为零，不是"没找到危险命令"）。
2. **召回目标枚举化** — `kind ∈ {seq, range, checkpoint}`，`id` 只能是有界数字 / 数字区间。**没有路径、命令、URL 的入口**；`../`、`$(...)`、`;`、8 位越界数字全部在门入口被拒。
3. **宿主端 inject 白名单** — 只允许 `['tools']`；禁 `slots`（客户端专属）、`compaction` / `toolResultPruner`（官方 realm 独占）。**写错即整棵插件树加载失败、CLD 起不来。**

## R006 十项矩阵

| # | 项 | 本插件 |
|---|---|---|
| ① | 真挂载冒烟 | `cli.js --selfcheck` 三态（pass/fail/skipped）；**K1/K2 均未跑**（会执行 `apply()`，需显式授权） |
| ② | 自检 | `lib/selfcheck.js`（R014），`apply()` 最前调用，失败不阻塞挂载；K2 另加 `--budget-check`（170 条断言，进程内） |
| ③ | CLD 自适应 | 运行期只依赖 node 内置模块，不调 dsh 私有 API |
| ④ | dsh 版本自适应 | 同上 |
| ⑤ | 统一日志 | `~/dsh-collab/logs/dsh-plugin-context-survival.log`（N5） |
| ⑥ | 版本单一来源 | `package.json`；`lib/meta.js` 读取，`--tool-version` 打印同一值（N7） |
| ⑦ | 固定路径落链 | 日志（N5）+ 登记卡 `data/registry/dsh-plugin-context-survival`（N6） |
| ⑧ | 文档 | 本文件（R039 中文 >100 字 + 矩阵 + 坑 + 复现） |
| ⑨ | CLI 治理 | `argparse` 式校验，退出码 0/1/2，未知旗标 exit 2 |
| ⑩ | Lean4 约束门 | `lib/gate.js`：A–F 六项自证（见下） |

## 坑（踩过或已知）

1. **宿主端 inject 客户端服务 ⇒ 整棵树加载失败**（2026-10-09 excalidraw 事故）：`slots` 只由客户端 `dsh-client-runtime` 提供，宿主平面永远没有。boot 的 `assertEntriesActivated` 统计**全部**未激活项后抛错 ⇒ CLD 完全起不来。故本插件 `inject = ['tools']`，D 项把这条钉成结构判据。
2. **嵌套 object schema 缺 `additionalProperties` ⇒ `defineTool` 抛 `UNSUPPORTED_SCHEMA` ⇒ `apply()` 崩 ⇒ 挂不上**。本插件所有嵌套 schema 一律显式 `additionalProperties: true`。
3. **版本两处硬编码必漂移**：故 `lib/meta.js` 是唯一读取点，`VERSION` 只从 `package.json` 取。
4. **`cli.js` 不得 import `lib/index.js`**：那会拉起 `@deepseek-ai/dsh-tools`，使 `--lean4-check`/`--tool-version` 在未挂载时先崩。挂载冒烟才**动态** import。
5. **`--selfcheck` 会执行 `apply()`**（真挂载冒烟）——在本仓库纪律下**须由构建者显式授权后再跑**；K1/K2 只跑 `node --check` + `--lean4-check`（后者不 import index.js）+ `--budget-check`（只 import 纯决策核）。
6. **可选服务一律 `ctx.get()`，绝不写进 `inject`**。`inject` 是**强依赖**：声明了却拿不到 ⇒ 该条永久 pending ⇒ `assertEntriesActivated` 失败 ⇒ **整棵插件树加载失败、CLD 起不来**（同坑 1 的形态）。官方自己对可选服务用的就是 `this.ctx.get("toolResultPruner")`（`dsh-compaction-basic/lib/index.js:867`）。好处：K1 的 `inject=['tools']` 与结构门 D 项判据**一字不用改**，事故面保持为零。
7. **`node --test lib/` 在 Node 25 会加载该目录下每一个 `.js`**（含 `lib/index.js`）⇒ 立刻 `ERR_MODULE_NOT_FOUND: @deepseek-ai/dsh-tools`。**必须显式点名测试文件**：`node --test lib/budget.test.js lib/guard.test.js`（`npm test` 已这么写）。顺带：这也是"文件名里带 `test` 不代表只有它会被跑"的一条实证。
8. **`Math.floor(cw × 0.95)` 里 0.95 不是二进制精确值**，边界上与手算差 1。故决策核只收**整数百分比**，`floor(cw × pct / 100)` 在 `cw < 2^53/100` 内精确；配置侧给比率时由 `pctFromRatio()` 显式换算。
9. **有意偏离 ctxwin 的一处（别当成抄漏）**：ctxwin 默认 `bodyAfterPrefix: true`（只计「超出窗口基线的增量」），本插件**不实现**——因为与我们并存的官方 `compaction-basic` 用的是 `measurement.totalTokens`（**全额**，`dsh-token-meter` 口径）。本插件必须**与官方同尺**，否则"该不该压"两个后端各算各的。这条分歧是刻意的；将来若官方改口径，这里要跟着改。
10. **黑板回读要比 `value`，不能比原始信封**：`{key,ts,value,version}` 里的 `ts` 是**两板各自的写入时刻**（实测本机与中央实例差 1 秒），比整包 sha 会得到"两面不一致"的假警报。要比 `value` 的规范 JSON 摘要
11. **照抄 ctxwin 的阈值会让守卫晚于官方触发（F1）**：ctxwin 的 `autoCompactTokenLimitRatio 0.9` 是「对用户给定**绝对上限**的 clamp」（照 Codex），**不是触发比率**；而并存的官方 `compaction-basic` 在 `floor(cw×0.8)` 触发。直接照抄 ⇒ 本守卫 `min(0.9cw+8000, 0.95cw) ≈ 0.91cw`，cw=1e6 时 **908,000 vs 官方 800,000，晚 108,000** ⇒ 健康会话里官方先成功，本守卫永不触发（K5 也无数据可标定）。⇒ 加第三项**比率式**抢先上限 `preemptCeil`。**不要**想用调小 `bufferTokens` 来解决：固定加性项在**小窗口**结构上做不到抢先（cw=8192 时 `0.9cw+8000` 被 `usable` 夹到 7782，仍高于官方 6553），只有比率项对**所有** cw 成立。`preemptRatio ≥ 0.8` 抛 `BAD_PREEMPT`——把这条做成门而不是注释，否则又是一个「配置能改却不生效」的静默 no-op。

## 复现

```bash
cd ~/dsh-collab/devices/dsh-plugin-context-survival

# 语法
node --check cli.js && for f in lib/*.js; do node --check "$f"; done

# 版本（单一来源 = package.json）
node cli.js --tool-version

# 只读状态
node cli.js --status --json

# 守卫计划（零外部变更）
node cli.js --dry-run

# K2 纯决策核自检（进程内 170 条断言 + 逐位确定摘要）—— 不碰 dsh、不碰会话
node cli.js --budget-check
node cli.js --budget-check --json | python3 -c "import sys,json;print(json.load(sys.stdin)['digest']['sha256'])"

# 同一份用例交给 node:test 驱动（★ 必须点名文件，别给目录，见坑 7）
node --test lib/budget.test.js lib/guard.test.js

# 结构门自证 A–F（不执行插件代码、不 import index.js）
node cli.js --lean4-check
```

`--lean4-check` 六项：**A** 源码零执行点 · **B** 负例全部被拒 · **C** 正例可用 · **D** 宿主端 inject 合规 · **E** 白名单冻结 · **F** dry-run 零变更。

## 里程碑

| 阶段 | 交付 | 状态 |
|---|---|---|
| **K1** | 骨架：`package.json`/`cordis.patch.yml`/`lib/index.js`（空守卫）+ `cli.js`/`selfcheck` | ✅ 2026-10-10 |
| **K2** | `agent/pre-step` 守卫 + 测量 + 阈值（**只测量不替换**）：`lib/budget.js` 纯决策核 + `lib/guard.js` 观察器 + `--budget-check` | ✅ 2026-10-10 |
| **K2.1** | **抢先上限** `preemptCeil`（裁决 F1：守卫须早于官方 `floor(cw×0.8)`）——决策核加第三项 + `BAD_PREEMPT` 门 + 不变式用例 B32/B33/G12 | ✅ 2026-10-10 |
| K3 | 检查点产出 + 表面替换 + 并发护栏 | — |
| K4 | `csx_recall` + 事件流落盘 +（可选）客户端面板 | — |
| K5 | 立项书 §5 全部正/负控跑通；R006 十项齐活 | — |
| K6 | **挂载（不可逆）**——由用户在独立试验会话里执行，先登记后执行 | — |
| K7 | 并入 R049 的机器化（Q-L） | — |
