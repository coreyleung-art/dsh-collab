# 立项书 · 上下文存活自研后端（Q-K）

> **日期**：2026-10-10　**立项人**：外部第三方（Claude Code 会话 · CU 实验台线）
> **批准**：用户 2026-10-09 回复「**2. 立项**」= 批准启动 C 轨自研后端项目。
> **性质**：**立项书**（设计依据 + 不变量 + 验收门）。不是规格全文；规格在交付件里出。
> **唯一权威**：锚点 `docs/distributed-agent-network-governance-plan-v4-20261009.md`（§7.8 P26 + Q-K）。
> **适用纪律**：R030（不陈述未验证之物）· R006（插件化工具化十项标准）· R047（插件命名门）· R049（上下文存活运营门）· 不可逆动作先登记后执行。

---

## §0 一句话

**P26 机制二（摘要模板地板 > 被遮内容）无配置解、且失败时无兜底**（`docs/context-survival-conservative-plan-20261009.md` §1.1–1.2）。
唯一能治它的路径是**代码层**。本立项落地一个**并列式守卫后端**：在会话到达压缩器开销下界**之前**，
用一个 **N→1、有界、非摘要** 的检查点把活跃窗口压下去，**与官方 `compaction-basic` 并存**，不替换 `ctx.compaction`。

**立项验收的核心负控**：**构造 P26 复发态（活跃窗口已低于摘要模板地板），本后端必须仍能缩小会话。**
若它也判"缩不动"，则它没有买到任何东西（详见 §5）。

---

## §1 不变量（违反任一条 = 设计失败）

| # | 不变量 | 为什么 |
|---|---|---|
| **I1** | **保证能减**：任何步的内存态，本后端要么产出严格更小的活跃窗口，要么**明确判"不可压"并告警**——**绝不静默 no-op** | 机制二的病就是"判不动 = 永久失效且不告警"。本后端的存在理由就是消掉这一条 |
| **I2** | **不摘要**：检查点由**原文片段 + 指针**组成，不做任何模型生成 ⇒ 结构上**不存在** `summary < shadowed` 这种"产出浮动"判据 | 绕开机制二的数学根因，而非在其上打补丁 |
| **I3** | **最新保活**：最近内容（近 N 回合 / `retainTokens` 硬上限内）**逐字保留**，永不被收走 | 正在进行的对话不能被压掉（抄 instant 的 retain 语义） |
| **I4** | **并存不独占**：走 **seam（b）**（host 平面 `agent/pre-step` 守卫 + 表面替换），`ctx.compaction` 仍归官方 ⇒ 本守卫崩溃/拒动时，官方后端行为**完全不受影响** | 独占 seam（a）会把"官方压缩"这个安全网整个拿掉（源码核实：一 realm 一个 `ctx.compaction`） |
| **I5** | **可召回**：被压掉的每一段都有 `seq` 指针，模型/人可逐字找回 | 近无损的前提是"丢得起"（抄 instant 的 `recall`/`search` 范式） |
| **I6** | **交接可续**：检查点带结构化交接字段，供**跨会话**信标四件套复用 | 与 R049 运营门合流：会内可召回 + 会间可交接 |

---

## §2 设计（seam b 并列守卫）

### 2.1 挂载位置（决定性，源码核实）

| 需求 | 挂载位置 | 源码依据 |
|---|---|---|
| 本守卫（`agent/pre-step` + 工具 + 提示） | **profile（host 平面）** | `ctxwin` handoff.md §4：host 平面可用，且**与官方后端不冲突** |
| ~~接管后端~~ | ~~agent preset 的 `compaction` realm~~ | ❌ **本立项不采用**（一 realm 一个 `ctx.compaction`，会独占） |

### 2.2 触发与决策（`agent/pre-step` 守卫）

```
每个 step 边界：
  m = ctx.tokenMeter.measure(session)          # 与官方同一计量源，口径一致
  cw = ctx.llm.resolveModelInfo(provider, model).context.contextWindow
  threshold = min(limit + buffer, usable, floor(cw × preemptRatio))   # 见下方 ★ 修正
  若 m.totalTokens ≥ threshold 且 未在压缩中：
      在阈值前插入一个检查点（本后端），而非等官方触发
  本后端产出后：仍让 next() 继续 ⇒ 官方后端若也触发，二者互不干扰
```

- **阈值语义对齐 Codex**（可抄 `ctxwin/src/budget.ts`）：`usable = floor(cw×95%)`、`limit = min(config, floor(cw×90%))`、`threshold = min(limit+buffer, usable)`，`buffer` 默认取 8000。
  - **★ 2026-10-10 修正（F1：本节原文自相矛盾）**：上面的 ctxwin 形态给到 `min(0.9cw+8000, 0.95cw) ≈ 0.91cw`，而并存的官方 `compaction-basic` 在 `floor(cw×0.8)` 触发（`:13 DEFAULT_THRESHOLD_RATIO = .8`）⇒ 照抄 ctxwin 会让本守卫**晚于**官方触发，与本节「而非等官方触发」直接冲突（ctxwin 的 0.9 是「对用户给定**绝对上限**的 clamp」，**不是**触发比率）。
    **用户 2026-10-10 裁决：走「抢先」（A）**。故阈值加**第三项**为比率式上限：`preemptCeil = floor(cw × preemptRatio)`、`threshold = min(limit + buffer, usable, preemptCeil)`，`preemptRatio` 默认 **0.70**；`≥ 0.8` 由 `resolveBudget` 直接拒绝（`BAD_PREEMPT`）。加性 `buffer` 在小窗口结构上做不到抢先（cw=8192 时 `0.9cw+8000` 被 `usable` 夹到 7782，仍高于官方 6553）⇒ **必须**是比率项。实现与证据见 `devices/dsh-plugin-context-survival/lib/budget.js` 与台账 `docs/context-survival-tracker.md` §5。
- **并发护栏**：抄 `ctxwin` 的 `hasOpenCompaction`——检测到已有压缩在途则不叠加。
- **只读不写直到决定**：守卫先测量；只有确定要压时才做表面替换（`session.append('user/message', msg, {surfaceOp:{op:'replace',start,end}, sourceEventSeqs})`）。

### 2.3 检查点内容形状（**非摘要**）

N→1：把 `[最旧的被选区域]` 压成**一条** `user/message`（标记为 plugin source，`form:'snapshot'`）：

```
<context_handoff v1 seq-range=A-B>
  目标:      <从 goal 投影抄>
  阶段/波次:  <从当前 wave/step 状态抄>
  todo:      <从 todo 投影抄>
  最近人类请求: <最后一条 user 文本，逐字>
  notes:     <NotesBuffer 累积的跨窗要点>
  省略账:     [N tool/result entries elided: seqs a-b]  ← 每一处省略都带 seq 指针
  召回指南:   一行，告诉模型用 <slug>_recall 取回
</context_handoff>
```

字段来源与理由：`目标/阶段/todo/最近人类请求` = `ctxwin/src/handoff.ts` 的现成骨架（**直接可抄**，它正是为修 Codex #43335「换窗后无任务状态」而做）；`省略账 + 召回指南` = `instant` 的指针范式；`notes` = 信标四件套的会话内镜像。

### 2.4 有界丢弃阶梯（**保证能减**）

若检查点仍超预算，**按固定次序**降级（抄 instant 的"工具行永远挤不掉对话"）：

```
1. 压缩对话文本预算（每条最少保留 32 token）
2. 丢最旧的工具结果条目（留 [N tool/result entries elided: seqs a-b]）
3. 丢最旧的其余条目（留 [N earlier entries elided: seqs a-b]）
—— 工具调用行不缩放；retainTokens 窗口内永不动
```

**I1 的落地**：走到阶梯末端仍缩小不了 ⇒ **不再静默**——写一条 `compaction/notice` 到会话 + 打 `WARN`，
判据与告警同时落事件流（R030：不隐藏"压不动"）。

---

## §3 与逆向素材的对应（R030：源码已核实，见 `research/rev-20261009/`）

| 本设计要素 | 抄自 | 源码位置 |
|---|---|---|
| 触发 seam（`agent/pre-step` 压力 + `agent/request-error` 溢出） | instant | `dsh-compaction-instant/src/index.js:531/:553` |
| 有界丢弃阶梯 + "工具行挤不掉对话" | instant | README §预算两道保险 |
| `seq` 指针 + `recall`/`search` 召回 | instant | `src/{recall,search,tool,command}.js` |
| 交接块字段形状（目标/阶段/todo/notes/最后人类请求） | ctxwin | `src/handoff.ts` `src/notice.ts` |
| 无摘要表面替换 + 并发护栏 | ctxwin | `src/replace.ts`（`hasOpenCompaction`） |
| 预算纯函数（usable/limit/threshold） | ctxwin | `src/budget.ts` |
| **并存而非独占**（seam b） | ctxwin | `docs/handoff.md §4` 挂载分区表 |

**不抄的部分**：instant 的 seal（a）独占式接入；ctxwin 的 `new_context` 模型自选换窗（本后端**自动**触发，模型无需决定）。

---

## §4 交付物（R006 十项，参考 `devices/dsh-plugin-cldvoice-activate/`）

目录 `~/dsh-collab/devices/dsh-plugin-<slug>/`：

```
package.json        # type:module/main/dsh.bundle.patch/dsh.client/r006 段
cordis.patch.yml    # - insert: [{id:<slug>, name:dsh-plugin-<slug>, config:{}}]（放入 profile/bundle，非 realm）
lib/index.js        # export const inject=[...]; apply(ctx,config); ctx.effect(()=> ctx.on('agent/pre-step', guard))
lib/selfcheck.js    # ★ 显式 sourceFiles；真挂载冒烟三态 pass/fail/skipped
lib/gate.js         # ⑩ 冻结白名单 + 命令白名单
lib/client.js       # ★ 客户端出口（可选：检查点可视化）
cli.js              # --selfcheck/--lean4-check/--tool-version/--dry-run/--json/--help
docs/README.md      # R039 中文 >100 字 + R006 十项矩阵 + 坑 + 复现
CHANGELOG.md
```

**工具名（N4：首段=领域前缀，全局唯一，snake_case ≥2 段）**——拟前缀 `csx`（context-survival 自定，须过 `plugin_name_gate`）：

| 工具 | 作用 |
|---|---|
| `csx_status` | 读当前压力/阈值/上次检查点（只读） |
| `csx_checkpoint` | 手动插入一个检查点（等价 Automatic 触发的立即版） |
| `csx_recall` | 按 `seq`/`range` 逐字取回被省略内容 |

**⑩ 结构约束**：`csx_recall` 的入参在 schema 层枚举（`{kind: enum["seq","range","checkpoint"], id: string|number}`）——**无任意文件路径、无任意命令**。

**slug 候选**（须先过 `plugin_name_gate`）：**`context-survival`**（首选）/ `ctx-guard` / `survive`。
不得与已挂载插件重名（`-excalidraw` / `-guard` / `-gate` / `-sandbox-policy-ui` / `-flower-cockpit` / `-dock-cards` / `-mcp-station` / `-openchronicle` …）。

**落链**：日志 `~/dsh-collab/logs/dsh-plugin-<slug>.log`；登记卡 `data/registry/dsh-plugin-<slug>`（黑板 key 首段须**纯小写字母**，**写完必须回读验语义相等**）；版本单一来源 = `package.json`。

---

## §5 验收（正控 + 负控，缺一不得记完成）

| 判据 | 怎么算它成立 | 类型 |
|---|---|---|
| **正控 1（能减）** | 构造"活跃窗口 ≥ 阈值"的会话，守卫触发后 `tokenMeter.measure` 的 `totalTokens` **严格下降** | 正控 |
| **正控 2（保活）** | `retainTokens` 窗口内的最近内容**逐字未变**（sha 比对） | 正控 |
| **正控 3（可召回）** | 被省略段用 `csx_recall` 取回，与原文**逐字相等** | 正控 |
| **正控 4（抢先）** | 本守卫阈值**严格小于**官方 `floor(cw×0.8)`（对**所有** cw，含 8192 级小窗）⇒ 官方尚未触发时本守卫已介入；`preemptRatio ≥ 0.8` 被 `resolveBudget` 拒绝 | 正控 |
| **🔴 负控 1（P26 复发态，立论所系）** | **把活跃窗口压到摘要模板地板以下**（机制二复发条件），本后端**仍能缩小**；若它判"缩不动"⇒ **立项失败** | 负控 |
| **负控 2（并存不打架）** | 官方 `compaction-basic` 同时在线；本守卫拒动/报错时，官方行为**零变化**（对照事件流） | 负控 |
| **负控 3（不静默）** | 阶梯走到尽头时，事件流**必须出现** `WARN` + notice（不能只有"没动作"） | 负控 |
| **边界** | 空会话 / 只有一条消息 / 活跃窗口已低于任何可行预算 ⇒ 如实判"不可压"，不崩 | 边界 |
| **R006** | `node cli.js --selfcheck` exit 0（含真挂载冒烟三态）· `--lean4-check` A–F 全绿 · `--dry-run` 前后外部状态一致 · 未知旗标 exit 2 | 标准 |

**验证纪律（全程）**：只读入口 / `node --check`；**不执行插件代码、不起服务、不代你重启 CLD**；
挂载与重启是**不可逆动作** ⇒ **先登记后执行、由你执行**。

---

## §6 风险与边界

| # | 风险 | 缓解 |
|---|---|---|
| 1 | 与官方后端**同一 `agent/pre-step` 事件**上叠加，可能双重压缩 | 并发护栏（抄 `hasOpenCompaction`）+ 对照事件流（负控 2） |
| 2 | 表面替换落在 step 边界（tool-pairing 平衡），可能找不到合法切点 | 用官方 `toolPairingBalancedBefore/After` 判据；找不到则本步不动（记 `skipped`，R030） |
| 3 | `tokenMeter` 对 CJK ~4× 低估 ⇒ 阈值判断失真 | 阈值用**同一 meter**（与官方同口径）；CJK 余量问题**另案**（`docs/…conservative-plan` §1.3），不在本后端兜 |
| 4 | 交接块字段依赖 goal/todo 投影，某些会话无该投影 | 缺字段如实留空，不编造（R030）；投影 API：`ctx.sessionProjections.stateOf(session,'todos'\|'goal')` |
| 5 | 本守卫自身出错 | `ctx.effect` 注册、`try/catch` 全包，`apply()` 不得抛（R006 ① 真挂载冒烟覆盖）；**绝不把宿主搞挂**（excalidraw 事故的教训：宿主端 inject 只能写真正存在的服务） |
| 6 | 与 R049 运营门重复 | 二者**互补**：R049 管会话间（人的纪律），本后端管会话内（机器的兜底）；本后端正是 R049「门未过不得推进」的**机器化前置**（Q-L） |

---

## §7 里程碑

| 阶段 | 交付 | 依赖 |
|---|---|---|
| **K0** | 立项书（本文件）+ 锚点/索引/规则入账 | — |
| **K1** | 骨架：`package.json`/`cordis.patch.yml`/`lib/index.js`（空守卫）+ `cli.js`/`selfcheck` ⇒ 过 `plugin_name_gate`、`node --check` | 本机 node |
| **K2** | `agent/pre-step` 守卫 + 测量 + 阈值（**只测量不替换**，离线单测逐位确定） | K1 |
| **K3** | 检查点产出（交接块 + 有界阶梯）+ 表面替换 + 并发护栏 | K2 |
| **K4** | `csx_recall` 工具 + 事件流落盘 + TUI/（可选）客户端面板 | K3 |
| **K5** | §5 全部正控/负控跑通；R006 十项齐活 | K4 |
| **K6** | **挂载（不可逆）**——由用户在**独立试验会话**里挂，先登记后执行 | K5 + 用户批准 |
| **K7** | 由 K6 的实测结果决定 → 并入 R049 的机器化（Q-L） | K6 |

---

## §8 未决（不阻塞 K1）

- **Q-K1**：slug 定名（首选 `context-survival`）并授权过 `plugin_name_gate`。
- ~~**Q-K2**：阈值首值~~ → ✅ **已决（2026-10-10）**：`threshold = min(limit+buffer, usable, floor(cw×0.70))`，即 ctxwin 形态 + 抢先上限 `preemptRatio 0.70`（< 官方 0.8）。`buffer` 仍取 8000，K5 标定。
- **Q-K3**：是否复刻 `recall`/`search` 两个独立工具（instant 把它们做成**不依赖引擎**的独立行）。
- **Q-K4**：客户端可视化范围（P5 型 dsh 面板，还是先 TUI）。
- **Q-K5**：K6 挂载窗口与「独立试验会话」的安排。

---

**关联**：`docs/context-survival-conservative-plan-20261009.md`（执行依据）· 锚点 §7.8 + Q-K · `research/rev-20261009/`（逆向素材）· R049 · `docs/R006-插件化工具化标准-v3.0.md` · 记忆 `feedback-no-third-party-dsh-plugins`。
