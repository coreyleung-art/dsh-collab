# 调用判断器 / 分发器 —— 立项卡（v1.0 草案）

> **口径**：本文件全部 16 位 hex = **SHA-256 全量摘要前 16 位小写 hex**
> **来源**：用户 2026-10-10 指令
> **裁前门**：J44 复用执行门 **已跑并显式裁决 `adapt`** ⇒ **门 exit=0 通过**

---

## §1 用户原话

> **工作流程**：当 DSH 的会话发起工具调用时，**第一时间进入这个分发器**，对需求进行判断，**并核查是否已有类似的功能或能力**。
> **立项目的**：避免不同的智能体、不同的会话**不断重复造轮子**，造成资源浪费；避免**忘记其他智能体产出的有价值资产**，导致重复浪费时间去"考古"，或者需要**人工去提醒**，从而浪费人力资源。

---

## §2 存量核查（★ 按 J44，先查后建）

**J44 门实跑**：`python3 scripts/j44-reuse-gate.py --intent "…"` ⇒ **命中 12 条** ⇒ **门拒绝**（有命中而未显式裁决）
⇒ **显式裁决 `adapt` 后门通过（exit=0）**

**已有资产（我逐个读了 docstring）**：

| 资产 | 实际职责 | 与需求的差 |
|---|---|---|
| **`scripts/j44-reuse-gate.py`**（38 KB） | **J44「资源复用纪律」的执行门**：`--intent` 查重（**已有 2100+ 资产库**）· `--verdict` 显式裁决 · 有台账 | ★ **能力面【就是这个】** —— 但**它是「人要记得跑」的** |
| **`scripts/bb-dispatch.py`**（13 KB） | ★ **「事件分发决策器（协调者判断门工具化）」** —— 其 docstring 记：**「用户指示（2026-08-23）：具体事件/工作该分发给谁 + 哪个角色应加入评估——这个判断过程工具化、插件化、沉淀到链」** | ★ **同构的需求，但它判【角色】不判【能力】** |
| **`scripts/bb-dispatch-learn.py`**（6.8 KB） | **分发决策器自进化学习器**（维护黑板 `data/frameworks/dispatch-kb`，含新角色同步 / 决策回灌 / 版本化） | ★ **可直接复用其自进化骨架** |
| `scripts/bb-reuse-check.py` | **底座能力复用性评估器**（判"该能力是否适合复用到分布式节点"） | ★ **不同问题**（节点复用 ≠ 避免重复造轮子） |
| `scripts/local-router.py` · `route-*.py` | **本地模型路由**（调 Ollama，按 confidence 分流） | ★ **不同问题**（模型分流） |
| **skills** `local-prior-art` · `reuse-before-build` | **建前考古入口**（查本机 2100+ 已有资产） | ★ **能力面同位** —— 但**要人主动调用** |

---

## §3 裁决：`adapt`（不是新建）

> **能力面已存在；缺口是【挂载点】与【判定对象】。**

| 缺口 | 现状 | 要建的部分 |
|---|---|---|
| **① 挂载点** | ★ **现有全部是「人要记得跑」的**（门 / skill 都要主动调用） | ★★ **调用链上必经**：DSH 会话发起工具调用时**第一时间进入** |
| **② 判定对象** | `bb-dispatch` 判**角色**（该给谁 + 谁加入评估） | ★★ **判【能力/功能】**（是否已有类似者） |

**⇒ 即：`bb-dispatch` 的「角色面」与 `j44-reuse-gate` 的「资产面」需要**合流到一个调用点**。

---

## §4 ★★★ 技术前提【已核：成立】（2026-10-10 核清）

> 原为"不能假设"的未决项，**现已实查 DSH runtime 源码确认成立**。

### 证据（源码原文）

`node_modules/@deepseek-ai/dsh-tools/lib/index.js` L2795–2809：

```js
/**
 * Register a monotonic guard after the extensible `tools/pre-execute`
 * waterfall. A plain-context guard applies globally; one registered through
 * `agent.ctx` applies only to that agent. Any matching guard may deny by
 * returning a reason, while no guard can force-allow a call another guard
 * denied. The exact effect disposer is returned for ordered ownership and
 * HMR cleanup.
 * @param guard - synchronous check; a returned string denies the execution.
 * @returns the exact disposer that unregisters the guard.
 */
guard(guard) {
  return this.layers.effect(this.ctx, (layer) => layer.guards.append(guard),
    { label: "tools.guard()", notify: false });
}
```

### 四项关键性质

| 性质 | 原文依据 | 对本立项的意义 |
|---|---|---|
| **① 有前置钩子** | `tools/pre-execute`（**extensible waterfall**） | ★ **可做"第一时间进入"** |
| **② 可拒绝** | *"a returned string denies the execution"* | ★★ **符合本线判据「绕过须【失败】而非更贵」** —— 不是"更贵"，是**直接 deny** |
| **③ 守卫单调** | *"no guard can force-allow a call another guard denied"* | ★★★ **下游插件也无法推翻** ⇒ **不可绕过** |
| **④ 可限定作用域** | *"plain-context guard applies globally; one registered through `agent.ctx` applies only to that agent"* | ★ **可按全局 / 按会话 / 按 agent 施加** |

### 附带的第二条通道

**`tools.restrict({ allow, deny })`**（同文件 L2782–2793）—— **白/黑名单**：
- `allow` 与 `deny` **至少给一个**（否则 `throw new Error("tools.restrict({}) is a no-op")` —— ★ **它自己就防"空转"**）；
- **不能命名保留工具 `run_code`**；
- **未知工具名会 `throw`**（不是静默忽略）。

**★ 第三条通道**：`tools/post-execute`（**事后 waterfall**，`accept` 可替换 content / `block` 可转成 `isError` + 纠正反馈）。

### ⇒ 结论

> **「调用链上必经」【技术可行】，且是 DSH 的【一等 API】，不需要 hack。**
> **⇒ 本立项从「可能又建一个要记得跑的门」升级为「可做真前置守卫」。**

### 参考插件的 API 面（证明插件能拿到它）

`devices/dsh-plugin-cldvoice-activate/lib/index.js` 使用 **`ctx.effect`** · **`ctx.tools`**；
`dsh-agent-loop` 暴露 **`ctx.on` / `ctx.effect` / `ctx.inject` / `ctx.provide` / `ctx.tools`**。
**⇒ 插件可经 `ctx.tools` 取得该表面。**

### ★ 仍未核清的一处（不假设）

**`tools.guard()` 的 guard 是【同步 check】** ⇒ ★ **若"核查是否已有类似能力"需要【检索 2100+ 资产】，那是 I/O**
⇒ **故须确认：能否在 guard 内做检索，或须用 `agent.ctx` + 预载索引（同步查内存）。**
⇒ **这一项决定实现形态（同步守卫 vs 预载索引）。**

## §5 规格草案（待 §4 核清后定稿）

| 项 | 草案 |
|---|---|
| **形态** | ★ **取决于 §4**：支持前置钩子 ⇒ **P1/P4（宿主工具·真前置）**；不支持 ⇒ **P3 CLI + 全角色写进操作规范**（弱） |
| **复用面** | `j44-reuse-gate.py` 的**检索与台账** · `bb-dispatch-learn.py` 的**自进化骨架** · 黑板 `data/frameworks/dispatch-kb` |
| **新建面** | **仅**：判定对象从「角色」扩到「能力」+ 挂载点 |
| **输入** | 一次工具调用的**意图文本**（由发起方给出，或从调用参数提取） |
| **输出** | **三态**：`命中已有`（给路径 + 类型）/ `无命中`（放行并**自动登记**为新资产候补）/ `不确定`（**报送人工**而非静默放行） |
| **★ 判据（怎么知道它生效）** | ★ **负控**：给一个**已存在的能力**（如"查黑板键"）⇒ **必须命中**；给一个**真新的能力** ⇒ **必须放行**。★ **缺此负控，它就是日志。** |
| **★ 落点** | ★ **须过 R006 十项**（本目标刚建立的那套）· 且**须先过 R047 命名门** |

---

## §5b ★★ 负控 5（星桥发现，2026-10-10 采纳）—— `allow` 不是终点

> **来源**：星桥对裁判声称的独立复跑。**它读了我给的命令，然后发现了一条我漏掉的通路。**

### 源码依据（复跑命令见下）

```
3116  const denialReason = decision.kind === "allow" ? this.guardReason(exec) : decision.reason;
2813      const globalReason = this.layers.global.guardReason(exec);   ← 先全局层
2815      if (exec.agent === void 0) return void 0;                    ← 再 scope 链
2537      for (const guard of this.guards.values()) { const reason = guard(exec); if (reason !== void 0) return reason;
```

**⇒ `tools/pre-execute` 返回 `allow` 【不是终点】** —— 后面还有一条**单调 guard 链**（`tools.guard()` 注册的）。

### 对 `dispatcher_check` 的直接影响

**只挂 waterfall 的话** ⇒ **任何经 `tools.guard()` 注册的既有守卫仍可在它之后拒绝，而 `dispatcher_check` 看不到。**
**⇒ 若规格假设「我 allow 就一定放行」，它会在自己的账上记一次「已放行」而实际被拒。**
**⇒ 这正是四条强制负控想防的那类假绿，只是发生在另一条通路上。**

### 负控 5（强制）

> **构造「本器 allow 但 guard 链 deny」的场景** ⇒ **`dispatcher_ledger` 必须如实记「本器已放行、后续被 guard 链拒绝」，不得记成放行成功。**

### 复跑命令（任何人可核）

```bash
F=/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools/lib/index.js
grep -n 'tools/pre-execute' "$F"          # 应命中 2796 与 3105
grep -n 'no guard can force-allow' "$F"   # 应命中 2799
sed -n '3094,3145p' "$F"                  # 挂载点与两条通路
wc -l "$F"                                # 3577
```

---

## §6 我依据的本线既有判据

1. **「先查存量工具面 → 缺口才新建 → 新建必过 R006 → 改动必实跑自检」**（上一目标 `goal-46e982cb`）
2. ★ **「绕过须【失败】而非更贵」** ⇒ **若挂载点只是"建议调用"，人必然绕过** ⇒ **故必须挂到【调用链上】**（这也是用户说"第一时间进入"的技术含义）
3. ★ **「有门不用」**（本线实测：我手上有 `bb_card_send` 却一直用 heredoc）⇒ **能力存在 ≠ 会被用**
4. ★ **「信号的价值 = 命中率 × 后果」** ⇒ **若分发器误报率高，它会被忽略** ⇒ **误报率必须实测**

---

## §7 未决（不假装已定）

1. ★ **§4 的技术可行性**（**最重要**）；
2. **判定对象的粒度**：一个"能力"如何被结构化描述（自由文本？标签？签名？）；
3. **误报率**（与语音域那条同病：**若把"改注释"也当"已存在"，会逼人做无意义动作**）；
4. **归属**：是谁的产物（审查线自建？还是属主是别人）；
5. **是否需用户批准**（涉及"所有会话的工具调用"⇒ **属全局治理面**）。

---

*调用判断器/分发器 立项卡 v1.0 · 2026-10-10 · 状态：草案（待 §4 核清）*
