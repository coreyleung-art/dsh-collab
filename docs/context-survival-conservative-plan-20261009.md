# 上下文存活 · 保守路线执行依据

> **日期**：2026-10-09　**作者**：外部第三方（Claude Code 会话 · CU 实验台线）
> **性质**：**执行依据**（不是规格）。唯一权威仍是锚点
> `docs/distributed-agent-network-governance-plan-v4-20261009.md`；本文件只承载一件事——
> **在"不挂任何第三方插件"的前提下，如何让 CLD 会话不被上下文硬死锁锁死**。
> **适用纪律**：R030（不陈述未验证之物）· 不可逆动作**先登记后执行** · 开关装上 ≠ 机制生效 ≠ 结果可控。

---

## §0 一句话结论

**保守路线（只改配置）能把"撞墙"的概率降下来，但给不了"保证不死"。**
保证只能来自**运营层**——不让任何单会话跑够久到撞墙，用信标四件套交接状态。
理由见 §1：病灶是**两个**机制，配置只修得了第一个。

---

## §1 病灶：两个机制（全部代码核实，非推断）

| # | 机制 | 代码位置（一手） | 配置能修吗 |
|---|---|---|---|
| **一** | **阈值不可达**。压缩压力阈值 = `floor(contextWindow × thresholdRatio)`。默认 `thresholdRatio 0.8` ⇒ `floor(1e6 × 0.8) = 800,000`；而 provider 把 messages + completion 一起算上限 1,048,576，适配器默认 completion 预留 **256,000** ⇒ 消息侧可达上限仅 **792,576 < 800,000** ⇒ **压力检查永远晚于 provider 溢出，主动压缩从不触发** | `dsh-compaction-basic/lib/index.js:13`（`DEFAULT_THRESHOLD_RATIO = .8`）· `dsh-llm-deepseek/lib/index.js:1735`（`config.maxTokens ?? 256e3`） | ✅ **已修**。`maxTokens` 降到 65,536 ⇒ 消息侧上限升到 **983,040**，阈值 800,000 留 **183,040** 余量 |
| **二** | **模板地板**（**真死因**）。压缩唯一产出 = `frameSummary(summary)` 包出来的 checkpoint 消息，其体积须 `< shadowedTokenCount`（`:556`）。而压缩指令**强制 8 段结构**且明令"keep every section… never drop a section"（`:218`）⇒ 摘要体量有**结构性下界**；实测 framed = **3435 / 3450 估算 token ≥ 被遮 2466** ⇒ `:556` 每抛，压缩**在数学上永久失效** | `dsh-compaction-basic/lib/index.js:556`（shrink 判据）· `:218`（8 段指令）· `:322`（`frameSummary`） | ❌ **配不出**。见下 |

### 1.1 为什么机制二配不出来（这是本文件的关键论据）

`BASIC_COMPACT_CONFIG_KEYS`（`:28`）只允许这些键：
`thresholdRatio` · `retainRatio` · `retainTokens` · `summarizationProvider` · `summarizationModel` ·
`maxTokens` · `compactionRetries` · `maxOverflowRetries` · `modelPolicies` · `auto`。

**没有任何一把键能改掉 8 段模板或 shrink 判据本身。** 该判据要改，只能**在代码层覆盖**
（源码 docstring `:231` 自己写了："Override this sole hook for a template or remote summarizer"）——
即自研后端，不是改配置。

### 1.2 失败时**没有兜底**（代码核实）

- **`agent/pre-step`**（`:780`）压力检查抛错时：`ctx.logger.warn("step compaction failed: …; continuing the turn")` ⇒ **只记警告，继续本轮**（`:790`）。
- **`agent/request-error`**（`:802`）溢出恢复抛错时：`"…preserving the original request error"` ⇒ **原样保留溢出错误，不降级、不兜底**（`:821`）。
- 结果是：**既不崩，也不自救**——会话停在"再也发不出任何一次请求"的状态，**不被现有崩溃监控捕获**。

### 1.3 所有阈值都算在**低估**的 meter 上（削弱"微调阈值"整条路）

`dsh-token-meter/lib/index.js:15`：`const CHARS_PER_TOKEN = 4`——**固定启发式，无配置**。
CJK / JSON 重的会话里，4 字符/token **低估约 4×** ⇒ §1 表格里那些"余量"（183,040）
对 CJK 重会话是**虚的**。⇒ **不要指望调阈值来保命。**

### 1.4 铁证（一手日志，非推断）

星桥 `session-fa1f9150-c949-401f-ba8c-d265f6221676`（2026-10-09T05:39:52+08:00 bricked）
`turn/end` 实录：
```
"requested 1049216 tokens (793216 in the messages, 256000 in the completion)"   ← 机制一
"summary is not smaller than the shadowed content (3435 estimated framed tokens >= 2466)"  ← 机制二
"…(3450 estimated framed tokens >= 2466)"
code: CONTEXT_WINDOW_EXCEEDED, status 400
```
全文证据：`docs/compaction-lowerbound-crash-20261009.md:33/:41/:48`。

**决定性时间线**：`maxTokens 256000→65536`（机制一之修）与 `standard-compact`（机制二之试图修）
**都是 2026-10-08 落的**；会话 **2026-10-09 05:39** 照样 bricked。
⇒ **机制一修好了，机制二仍然杀了它。**

---

## §2 现状核实：**建了 ≠ 挂上 ≠ 生效**（本次逐项实测）

| 物 | 位置 | 核实结果 |
|---|---|---|
| `llm-deepseek.maxTokens: 65536` | `~/.dsh/settings.yaml:62` | ✅ **在位且生效**（全局）。注释自带"关键项，勿删"。**风险：升级 dsh 后可能被重置 ⇒ 每次升级后须回读这一行** |
| `standard-compact` 预设 | `~/.dsh/.agent-presets/standard-compact/` | ⚠️ **建了，但没选上** |
| ├ `preset.yml` | 同上 | `name: 标准模式（压缩强化）`, `order: 2` |
| ├ `agent.cordis.yml` | 同上 | 与 shipped `standard` **仅三处差异**：11 行 provenance 头 + 14 行注释 + `compaction-basic` 的 `config{thresholdRatio 0.6, retainRatio 0.12}` |
| ├ 拷贝基线校验 | — | shipped `standard` 现 sha256 = `fa14feb98daef20b810fef30bb7239a89a786de3c45c602b37743f7100d9a5af` = 头部记录的基线 ⇒ **未过期，逐字等价** |
| └ 是否被使用 | `~/.dsh/settings.yaml:50` | ❌ `agent-presets.default: standard` ⇒ **跑的仍是原版 standard** |
| 死会话实际用的预设 | 会话日志 | ❌ `"agentPreset":"standard"` ⇒ 与上一致，**`standard-compact` 从未挂上** |

> **本次关闭一个开放项**：此前挂起的"completion 预留 256,000 vs 65,536 的背离"**不是矛盾，是修法前后**。
> 256,000 = 适配器默认（修前）；65,536 = 2026-10-08 改后。P26 的 `986,282 + 65,536 = 1,051,818`
> 超 3,242 是**修后**读数 ⇒ 自洽。（另：meter 对 CJK 的 ~4× 低估是**另一件事**，仍开放。）

---

## §3 保守路线：三条轨道

**性质标注**：`配置` = 只改 yaml，不动代码；`运营` = 只改人的做法，零代码零挂载；`自研` = 要写代码。

### ① 配置轨道（**降概率，不保命**）

| 项 | 文件 / 键 | 现值 → 目标 | 性质 | 负控（怎么算它真的生效） | 执行者 |
|---|---|---|---|---|---|
| **A1** | `~/.dsh/settings.yaml` → `llm-deepseek.maxTokens` | **65536（保持）** | 配置 | 升级 dsh 后回读该行仍为 65536；否则压缩可达性回到机制一 | 用户（升级时） |
| **A2** | `~/.dsh/settings.yaml` → `agent-presets.default` | `standard` → **`standard-compact`** | 配置（**改 profile，须重启生效**） | 换上后跑一个长会话，日志出现 `compaction (step pressure): shadowed N surface nodes`；且**不**出现 `CONTEXT_WINDOW_EXCEEDED` | 用户（**先登记后执行**） |
| **A3** | `~/.dsh/.agent-presets/standard-compact/agent.cordis.yml` → `thresholdRatio / retainRatio` | `0.6 / 0.12`（保持） | 配置 | 反向负控：临时调到 `0.99 / 0.1` 应能**复现** bricked ⇒ 证明该阈值确实生效（**只在独立试验会话里做，勿动生产**） | 用户 |

> ⚠️ **A2 的诚实边界**：换上 `standard-compact` 让**机制一**的余量从 183,040 扩到 **383,040**
> （阈值降到 600,000），**但机制二一点没动** —— 活跃窗口一旦低于摘要模板地板，
> `:556` 照样每抛。**A2 是把 `thresholdRatio` 下调，而 `thresholdRatio` 恰恰是"多久压一次"，
> 不是"能不能压成"**。别把 A2 读成治本。

### ② 运营轨道 ⭐ **唯一能保命**（零代码、零挂载）

| 项 | 做法 | 判据 | 现存工具 |
|---|---|---|---|
| **B1** | **会话长度策略**：协调者/总线类长会话**主动限寿**——按轮数或压力主动开新会话，**不等它撞墙** | 交接时会话压力 < 阈值 | 无（人的纪律） |
| **B2** | **交接 = 信标四件套**（C1 索引键 / C2 锚点 / C3 续接提示词 / C5 反遗忘校验） | **新会话按前 3 步复述出「当前 wave + 下一步」**（= M0 判据） | 已全部在位 |
| **B3** | **机器化交接**：改状态 → 重渲续接提示词 → 校验 → 再开新会话 | `mk-resume-prompt.py` **越界即拒绝生成**（>40 行 exit 2）；`beacon-check.py --net` **exit 0 才继续** | `tools/mk-resume-prompt.py` · `tools/beacon-check.py` · `tools/bb_dualwrite.py` |

**为什么这条能保命**：机制二的失效条件是"活跃窗口低于摘要模板地板"。
**只要会话在到达那个地板之前就交班，机制二永远没有机会发作。**
这不是"绕开 bug"，而是把**不可控的会话内压缩**换成**可控的会话间交接**——
后者是确定性的（文件 + 校验脚本），前者是概率性的（模型产出体量随内容浮动）。

**负控（怎么算这条真的成立了）**：按 B1–B3 完整跑一个"交班周期"（旧会话 → 落状态 → 新会话），
新会话必须能答出复述题。答不出 ⇒ 交接无效，**回到 B2 修四件套**，别开新会话往前冲。

### ③ 自研轨道（终局，**唯一能治机制二**的路径）—— **v2：两条 seam 已分清**

| 项 | 做什么 | 约束 |
|---|---|---|
| **C1（seam a）** | 照 `compaction-basic` 的**契约**自写**替换式后端**（补 L3「保证能减」的确定性兜底：压文本预算 → 丢最旧工具结果行 → 丢最旧条目，**最新永远保活**）。社区包 `instant` 已证明此路可行（源码核实：`class … extends CompactionEngine`、同 inject 表、确定性编译） | **每个 realm 只能有一个 `ctx.compaction`** ⇒ 只能**替换**，不能与官方叠加 |
| **C2（seam b）** | 做**并列式守卫**：host 平面 `agent/pre-step` 拦截 + `user/message` 表面替换，产出结构化 `目标 + 阶段 + todo + notes + 最后人类请求`（**不叫"摘要"**，故不经 `summary < shadowed` 判据）。社区包 `ctxwin` 已证明**此路可与官方后端并存** | 不替换 `ctx.compaction` ⇒ **无"一闪失就整个压缩失效"的风险**；但换窗落在 step 边界（tool-pairing 平衡） |
| **C3** | 交付照 **R006 十项标准**（`~/dsh-collab/docs/R006-插件化工具化标准-v3.0.md`） | 参考实现 `devices/dsh-plugin-cldvoice-activate/` |

> **v2 更正（R030）**：v1 写「只能替换、不能叠加」——**对 seam（a）成立，对 seam（b）不成立**。
> 用户 2026-10-09 批「立项」的 **Q-K 走 seam（b）**（并列守卫），理由：不独占 `ctx.compaction`，风险面小得多。

**负控（C 的立论所系）**：构造"活跃窗口已低于压缩器开销"的会话（= P26 复发），
**新后端必须仍能把会话缩小**；若它也判"缩不动"，则它没有买到任何东西。
⇒ **P26 的正控恰恰是"挂载了也可能等于没挂"**，阳性判据必须带这条负控。

---

## §4 逆向素材（**不挂载**，只提取思路）—— **v2：源码已读**

用户 2026-10-09 定：*"外部插件只适合提取思路和完整逆向后来自研。除非属于一些临时性工具调用逻辑，否则能不挂尽量不挂。"*
⇒ 两个社区插件（marketplace 已核实，**均非官方**）**不进挂载清单**，只作逆向素材。
**2026-10-09 晚：两包均已 `git clone --depth 1` 只读通读源码（`research/rev-20261009/`），下表由"自述"升格为"源码核实"（R030）。**

### 4.1 `TsFreddie/dsh-compaction-instant`（v0.1.4）★ 源码核实

**它用的是 seam（a）：顶替压缩后端。** `package.json` 明写 *"a drop-in replacement for `@deepseek-ai/dsh-compaction-basic`"*；`src/index.js:398` `class InstantCompactionEngine extends CompactionEngine`，同名导出、同一 `ctx.compaction` 接口，**同依赖注入表** `static inject = ["llm","tokenMeter","sessions"]`（`:399`）。

| 抽到的机制 | 源码位置 | 对我们的价值 |
|---|---|---|
| **确定性编译，零模型调用**：`compile()` 是唯一覆写钩子，把被遮区域交给 `./compiler.js`（VCC 思路）编译成"检查点"，**从不 route 一个模型请求** | `:611`（`compile`）· `:398` 类注释 | C 轨的核心：**这就是"保证能减"的存在性证明**——毫秒级、只用原文 |
| **有界丢弃阶梯**：超预算先删最旧**工具行**（`[N tool/result entries elided: seqs a-b]`）→ 再删其余最旧条目；**工具调用永远挤不掉对话**（每条对话最少留 32 token）；**最新永远保活** | README §预算两道保险 | C1 的 L3 兜底（有序 drop-to-cap） |
| **召回不丢**：`recall`/`search` 工具 + `/recall` 命令，按 `(seq N)`/`result N`/`[checkpoint N]` 指针从只增日志里**逐字恢复**被省略内容；`maxRecallTokens` 默认 16000 | README §Recall · `src/{recall,search,tool,command}.js` | 与信标四件套互补：**会话内**可召回 + **会话间**可交接 |
| **压力/溢出双触发**：`agent/pre-step` 压力（`thresholdRatio` 默认 **0.5**）+ `agent/request-error` 溢出恢复（`maxOverflowRetries`）——**与官方同构** | `:531` `agent/pre-step` · `:553` `agent/request-error` | 证明"同 seam 换后端"在工程上完全可行 |
| **cap 是硬顶不再按比例缩放**：`effectiveMaxTokens()` 恒返回 `checkpointCap`（默认 65536）；`maxTokens/checkpointScale` 已弃用 | `:599` | 比官方的"shrink 判据"更可控 |
| **实测压缩率**：工具密集会话 9.0%（2,523,012→226,205）；纯文本 68.3% | README §实测 | 校准"能减多少"的预期 |

⚠️ **它也证实了那条硬约束**：README 末尾 *"每个上下文只能挂载一个 `ctx.compaction` 实现"* ⇒ 换后端 = **per-realm 独占**。

### 4.2 `CooperZhuang/dsh-context-window`（v0.0.1，0 star）★ 源码核实

**它用的是 seam（b）：host 平面 `agent/pre-step` 守卫 + 表面替换，不接管 `ctx.compaction`。** `docs/handoff.md §4` 有决定性的挂载分区表：

| 需求 | 挂载位置 | 结果 |
|---|---|---|
| 只要提示 + `new_context` 工具 | profile（host 平面） | ✅ 可用 |
| 接管压缩后端 | agent preset 的 `compaction` realm | ✅ 需把行挂进去 |
| **两个后端并存** | —— | ❌ 一个 realm 只允许一个 `ctx.compaction` |

| 抽到的机制 | 源码位置 | 对我们的价值 |
|---|---|---|
| **无摘要换窗**：`compaction/prune` 影子价 + `user/message` 整面 `replace`（`surfaceOp:{op:'replace',start,end}`）；`hasOpenCompaction` 并发护栏 | `src/replace.ts` · handoff.md §5 | **绕开 `summary < shadowed` 判据的现成范式**（D8 已实现，82 单测绿） |
| **交接检查点**：`<context_handoff>` 从 goal/todos 投影 + 最后一条人类消息拼骨架；`NotesBuffer`；`readPriorCheckpointNotes` 从日志回读 | `src/handoff.ts` · `src/notice.ts` | Q-K 的 C 轨交接块**直接可抄的字段形状** |
| **它要修的正是 P26 同类缺陷**：Codex issue #43335「换窗后第一个请求**完全没有任务状态**」⇒ 本项目做 handoff 换窗，换窗时**主动写交接检查点** | handoff.md §1 | **与我们的病同源**：纯换窗会丢状态，交接块是补丁 |
| **预算记账纯函数 + fail-loud**：`usable=floor(cw×95%)`、`limit=min(配置,floor(cw×90%))`、`threshold=min(limit+buffer,usable)`；越界即抛 | `src/budget.ts` | 阈值语义对齐 Codex（可抄进 C 轨） |
| **Codex 提示阈值**：开窗 + 25/50/75% 各一次（`NoticeThrottle`） | `src/emission.ts` | 提示时机参照 |

⚠️ **它也证实了机制一的病根**：handoff.md §2 陷阱 2 *"`settings.yaml` 里选用的模型没有 `contextWindow`……回落 adapter 默认 1e6……不先补这个，提示和阈值永远几乎不会触发"* — **与我们 §1 机制一逐字同源**。

### 4.3 两包合起来给出的**唯一正解形状**

instant 证明「同 seam 换后端、确定性可减」可行但**独占**；ctxwin 证明「host 平面守卫 + 表面替换 + 交接块」**可与官方后端并存**。
⇒ **Q-K 自研后端取 seam（b）**：host 平面 `agent/pre-step` 守卫，读 `tokenMeter`，在阈值前插入**N→1 有界非摘要检查点**（= instant 的有序 drop-to-cap + ctxwin 的交接块字段 + 信标四件套内容），**与官方 `compaction-basic` 并存**，不替换 `ctx.compaction`。立项书见 `docs/project-init-context-survival-backend-20261010.md`。

---

## §5 待用户拍板 —— **v2：三项已决（2026-10-09「1.写。2.立项。3 读」）**

| 项 | 问 | 状态 |
|---|---|---|
| **Q-F′** | `agent-presets.default: standard → standard-compact` 换不换？ | ⏳ **仍待你决定**（属"改 profile"，须重启生效 ⇒ **先登记后执行**，**由你执行**）。P26 已把 Q-F 前提换掉：问题不再是"要不要挂压缩"，而是"挂了在下界以下也不生效" |
| **Q-NEW-1** | 运营轨道（B1 会话限寿）**要不要写进纪律**？ | ✅ **已决＝写**。已入账 **R049 上下文存活运营门**（`rules-registry/RULES.md`）+ 锚点 §7.8 + 索引 Q-L |
| **Q-NEW-2** | C 轨（自研后端）**现在立不立项**？ | ✅ **已决＝立项**。取 **C2 seam（b）并列守卫**（见 §3 ③ 与 §4.3）；立项书 `docs/project-init-context-survival-backend-20261010.md`；索引 Q-K |
| **Q-NEW-3** | 读那两个插件源码，把"待逆向线索"升格为"已验证机制"？ | ✅ **已决＝读**。两包已只读通读，§4 已升格（R030） |

---

## §6 复现命令（本文件全部结论可自行复算）

```bash
# 机制一/二 的代码常量与判据（只读，不执行）
F=/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-compaction-basic/lib/index.js
grep -n 'DEFAULT_THRESHOLD_RATIO\|DEFAULT_RETAIN_RATIO\|BASIC_COMPACT_CONFIG_KEYS\|COMPACTION_INSTRUCTION' "$F"
sed -n '550,560p' "$F"     # :556 shrink 判据
sed -n '780,795p' "$F"     # :790 失败只警告、继续本轮
sed -n '802,825p' "$F"     # :821 失败保留原错误、不兜底
grep -n 'CHARS_PER_TOKEN' /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-token-meter/lib/index.js

# 现状核实
sed -n '49,62p' ~/.dsh/settings.yaml                      # agent-presets.default + llm-deepseek.maxTokens
shasum -a 256 /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/config/agent-presets/standard/agent.cordis.yml
#   ↑ 应等于 fa14feb98daef20b810fef30bb7239a89a786de3c45c602b37743f7100d9a5af
diff /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/config/agent-presets/standard/agent.cordis.yml \
     ~/.dsh/.agent-presets/standard-compact/agent.cordis.yml   # 只应有 头+注释+config 三处

# 运营轨道（保命机制）
python3 ~/dsh-collab/tools/mk-resume-prompt.py --check          # 越界即 exit 2
python3 ~/dsh-collab/tools/beacon-check.py --net                # 必须 exit 0；--net 抽检黑板指针
```

---

## §7 纪律与边界（违反即失去意义）

- **R030**：本文件区分「代码核实」与「推断/自述」。§1 全部代码核实；§4 **v2 起两包源码已读、升格为源码核实**（v1 时仅为自述）。
- **不可逆动作先登记后执行**：改 `agent-presets.default` 属改 profile，**执行者是你，不是我**。
- **不挂第三方插件**：§4 两个插件是**逆向素材**，不是安装候选。见记忆 `feedback-no-third-party-dsh-plugins`。
- **实测纪律**：验证只用 `node --check` / 只读入口；不执行插件代码、不起服务、**不代你重启 CLD**。
- **不清理任何历史会话记录**（绝对约束）。
- **不要因为"机制一修好了"就以为病好了**——机制二在 2026-10-09 05:39 事实上杀了会话，
  而当时机制一已经是修好的状态。

### 7.1 实测发现：C1 双写工具有一个**假绿**缺口（2026-10-10，R030 如实记）

`tools/bb_dualwrite.py` 的 `values_equal` 只比较**两块板彼此是否相等**（`put_both` `:124-130`），
**不与"刚发出去的 payload"比较**。后果：**一次没有真正落盘的写，只要两块板都还停在同一个旧值上，
就会报 `verdict=ok`**。本次两次真撞上：
① 首次写 `data/registry/project-init-…` 卡 46 字键 → `equal=False`（幸而没被当成功）；
重试才落盘。② 首次写索引 v3+evidence → 报 `ok equal=True`，但**两板实际仍是 12 条证据的旧值**，
`--net` 也只查"可读"不查"内容相等" ⇒ **假绿**；重试后才真落盘（evidence 12→13）。

⇒ **纪律**：C1 落盘后**必须独立回读并比对内容 sha**（不能只信 `bb_dualwrite` 的 verdict，
也不能只信 `beacon-check --net` 的绿灯——它抽检的是**可读性**，不是**内容一致性**）。
`[待修]` 可给 `bb_dualwrite` 加一条"回读值 == payload"的判据，或给 `beacon-check --net` 增一条
"板值 sha == 本地文件 sha" 的抽检。
```