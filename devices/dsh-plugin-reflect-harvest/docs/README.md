# dsh-plugin-reflect-harvest · 每日反思流水线「收牌」（④）— R006 十项达标

> 星桥 · 2026-09-10 · **v1.1.0（★ 跨设备层）** · R006 ①–⑩ 全达标 · 位置 `~/dsh-collab/devices/dsh-plugin-reflect-harvest/`

## 为什么需要它（实证，不是推测）

流水线全貌：

```
① reflect-collect     采集当日事件        → events-<date>.json
② reflect-dispatch    发思考卡            → cards/<date>/<agent>.md
③ 各智能体回填                            → answers/<date>/<agent>.json
④ reflect-harvest     ★ 本工具：收牌      → harvested-<date>.json
⑤ reflect-synthesize  提炼 + 对照 + 分类  → proposal-<date>.md
⑥ 用户裁定
⑦ reflect-enroll      入册 + 反馈
```

**本工具的核心不是"合并"，是"校验"。** 原因是这条链上有一处死线：

| 现象 | 后果 |
|---|---|
| 无证据的条目被当成有效混进汇总 | ① 复现计数（recurrence）虚高 → **排序失真**，飞轮按噪音加速；② 用户按提案入册，而入册依据**根本不存在** → 污染规则库/哲学库；③ **事后看不出来** —— 输出里分不清哪条是编的 |

顺带一提，这不是假想：fixture `agent-gamma` 的 R2 就是当天真实发生过的形态
（`harvested-2026-09-09.json` 里 12 条"有效"中有 4 条 `evidence` 为空对象）。

所以证据门做在**结构层**，不是"检查后放行"：

```
entries → adjudicate() → mintAdmitted()  ← 唯一入口；不通过 → null（条目到此为止）
                              ↓
                        buildValidSet()  ← 唯一 push 点；裸对象 → GateError(UNBRANDED_ENTRY)
```

**没有** `skipEvidence` / `force` / `lenient` / `ignore-evidence` 这类旗标（见下方 ⑩ 节）。

## 用法

```bash
node cli.js --date 2026-09-10                # 全设备收牌（本地 + 中央黑板）
node cli.js --date 2026-09-10 --summary      # 摘要（按设备分组 + ★拒收原因分布 + 跨设备复现排序）
node cli.js --date 2026-09-10 --devices mac-mini,mbp,lab-mbp,i9   # 显式设备表
node cli.js --date 2026-09-10 --local-only   # 只读本机（离线/测试，完全不触网）
node cli.js --date 2026-09-10 --allow-late   # 额外收 T-1/T-2 补填（标注实际提交时刻）
node cli.js --date 2026-09-10 --dry-run      # 只算不写：数据产物/日志/参照库/回填目录 全部零变更
node cli.js --date 2026-09-10 --json         # 机器可读（含 similarity 灰区矩阵 + per_device）
node cli.js --selfcheck                      # ②③④：能力清单 / 不该发生路径清单 / 依赖完整性
node cli.js --lean4-check                    # ⑩ 结构门自证（A–F 六项）
node cli.js --tool-version                   # ⑥ 与 package.json 一致
node cli.js --help
```

**退出码（R006 ⑨ 固定语义）**：`0` 成功/门生效 · `1` 失败/门失效 · `2` 用法错误或 IO 错误

真实的退出码边界：

| 情形 | 退出码 | 实测 |
|---|---|---|
| 正常收牌 | 0 | `--lean4-check` / `--selfcheck` / 收牌 均 0 |
| 未知旗标 `--nope` | 2 | `用法错误: Unknown option '--nope'` |
| 多余位置参数 `foo` | 2 | `Unexpected argument 'foo'` |
| 日期格式错 `2026/09/10` | 2 | `--date 必须是 YYYY-MM-DD` |
| `answers/<date>/` 不存在 | 2 | `IO 错误 [NO_ANSWERS_DIR] …（不代建、不猜）` |
| 门失效（A–F 有红） | 1 | `门未生效，禁止交付` |

## ★ 跨设备层（v1.1.0）

**只采本机 = 只看到四分之一。** MBP 上跑着独立的 DSH 智能体网络，i9 经 MCP 接入 ——
它们的经验若不被吸收，就是**永久的盲区**（design v1.1 §10.1）。

**黑板即协议**（不引入新传输通道）：

| key | 谁写 | 谁读 |
|---|---|---|
| `data/reflect/answers/<device>/<date>` | **各设备智能体回填** | **本工具 harvest（只 GET）** |
| `data/reflect/cards/<device>/<date>` | 本机 dispatch | 该设备的智能体（本工具只探测"卡派没派"） |

### 设备表与设备名门

```
设备表来源优先级（每一步都写进输出，不留隐式行为）：
  1) --devices a,b,c                                    ← 显式
  2) ~/dsh-collab/data/reflect/devices.json 的 devices  ← 上游可写，本工具只读
  3) 冻结默认表 ['mac-mini','mbp','i9']                  ← 并在 notes 里说明"用了默认表"
本机设备名：--device → env REFLECT_DEVICE/DSH_DEVICE → registry.local → hostname

设备名门：^[a-z0-9][a-z0-9._-]{0,31}$
  —— 设备名同时是**黑板 key 的路径段**与**本地目录段**，所以这条门一次挡两类穿越
     （../ 、含 / 、空白、前导点/横线、超长、空值 全部拒绝；实测负例 16/16 被拒）
```

### 五种"跨设备污染"全部有对策

| 风险 | 对策 | 实测证据 |
|---|---|---|
| 同一台设备本地+黑板两份 → **算两遍** | **(device, agent) 去重，来源优先级 = 黑板 > 本地**（黑板是跨设备的约定通道） | `lab-mbp` 源计数 本地 1 · 黑板 2 → 去重记录「保留 blackboard，丢弃 local」 |
| key 说 A 设备、内容自称 B 设备 | `device_mismatch` → **拒绝该条**并计数 | 单元级：载荷 `device: 'mbp'` 落在 `lab-mbp` 的 key → 拒 |
| 同步盘把同一份文件带到多台设备 → **伪造跨设备复现** | `possible_sync_duplicate`：`lesson` **逐字相同** + 跨 ≥2 设备 + `evidence.ts` 时点接近（<24h）→ 标出但**不重复计入 recurrence** | `mbp:agent-echo#R2` 与 mac-mini 逐字相同 → 剔除，`recurrence` 保持 2（而非 3），`cross_device=false` |
| 设备间版本漂移 | 回填带 `plugin_version` → 比对；不一致进 notes + 摘要 + 提案统计表 | 实测 `0.9.9 vs 1.0.0` → 提案里标「★ 裁定前请先确认口径」 |
| 各设备时钟不同步 | **不做跨设备时间戳一致性判定**，只标注（`evidence_no_collected_at`：有对象时刻 `ts` 但缺采集时刻 `collected_at`） | 8 条 mac-mini 记录被标注（mbp 侧已补 `collected_at`，未标） |

### pending ≠ missing

设备当天没有回填时，**先看卡派没派**：

| 情形 | 状态 | 含义 |
|---|---|---|
| 有回填 | `submitted` | 正常 |
| 无回填 + **卡已派出** | `pending` | **可能离线**（复用已有"待投递队列"语义，而不是判它"缺数据"） |
| 无回填 + 未派卡 | `not_dispatched` | 本就没派 |
| 卡探测失败 | `unknown` | 如实说未知，不猜 |

`--allow-late`：额外读 `T-1`/`T-2` 的 key，**只收 `date` 归属当日**的记录，
并标注 `late_by_key` / `late_key_offset` / `submitted_at` —— **这正是 Φ13（证据有时点）的实践**。

### ★ 复现广度的语义升级

```
v1.0：recurrence = 本机有几个智能体独立提到
v1.1：recurrence = 有几个 **<设备>:<智能体>** 独立提到        ← 集群 agents 字段形如 "mbp:agent-echo"
      + cross_device: true/false                            ← 是否跨设备复现
```

**为什么跨设备更强**：不同设备上的智能体跑的是**不同的任务、不同的上下文** ——
它们独立踩到同一个坑，说明**这不是某条工作流的偶然，而是系统性的**（design §10.7）。
因此 ⑤ synthesize 的排序键是 **(cross_device, recurrence)** 二元组：**跨设备优先**。

实测（4 设备）：

```
[C1] ★跨设备 recurrence=5（lab-mbp×1 + mac-mini×3 + mbp×1）· 条目 5
     破坏性动作之前必须先取证，证据要标注采集时点……
[C2] recurrence=2（mac-mini×2）· 条目 3
     引用即复制：为了说明而引用会让信息多一份副本……
     ⚠ possible_sync_duplicate（逐字相同、不重复计入 recurrence）: mbp:agent-echo#R2
```

设备表：`mac-mini` 本地 4 · `mbp` 本地 2 · `lab-mbp`（**走中央黑板 GET**）本地 1 + 黑板 2 · `i9` **pending**

## 五类校验（本工具的实际功能面）

| 校验项 | 判定 | 处理 |
|---|---|---|
| **★ 证据完整性** | 每条 item 必须含 `evidence.ts` +（`cmd` 或 `output`） | 无证据 → `invalid_evidence`，**隔离**，不进汇总 |
| 必填字段 | `pit` / `lesson` / `suggestion.type` 齐全且非空 | 缺 → `incomplete` |
| `suggestion.type` 合法性 | 必须是四选一（闭集，冻结） | 非法 → `invalid_type` |
| `related_rule` 可解析 | 填了就去 `rules-registry/RULES.md` 与 `governance-philosophy.json` 核对 | 不存在 → flag `unknown_rule`（**不拒收，但要标**） |
| `declined` 合法性 | `declined:true` 必须给理由 | 无理由 → `invalid_decline`（**文件级**） |

判定优先级（同时收集全部 issues，主 reason 取最高优先）：`incomplete > invalid_type > invalid_evidence`。
理由：结构缺失比内容非法更前置；而只要证据不通过，无论其它字段多完整都进不了 valid —— 这是死线。

**参照库读不到时不猜**：`catalog.js` 返回 `available:false`，据此**跳过** `unknown_rule` 判定并在输出里写明原因（宁可漏标，不可误标）。

## 去重与 ★ 复现广度（飞轮指标）

复现计数 `recurrence` = **独立智能体数**，不是条目数 —— 同一个 agent 提 3 次只算 1。
否则"一个人反复说"会被误读成"大家都这么说"。

聚类用**双判据**（`lib/lesson.js` 的冻结 `SIM_RULE`）：

```
merge  ⟺  dice ≥ 0.52   或   ( shared_bigrams ≥ 8  且  dice ≥ 0.40 )
```

为什么一条不够（实测）：两句同一件事的复述，共享 13 个 bigram、内容高度重叠，Dice 却只有 **0.491**。
只按 Dice≥0.52 会**漏合** → 把「3 个智能体独立提到」错拆成「1+1+1」，而复现广度正是本工具存在的理由。
地板值 0.40 防的是「长 lesson 与短 lesson 只因一句套话而共享」的错合。

**已如实登记的局限**：这是**字面层**近似，不是语义近似（真正换述如"取证"↔"留证据"可能并不到一起）。
因此输出里带 `similarity` 灰区矩阵 —— 把所有 `dice ≥ 0.25` 或 `shared ≥ 8` 的对列出来并标 `merged` 与否，
**"可能是同一条但没敢合"看得见**。宁可显式暴露灰区，不可静默错合/错拆。

## R006 十项达标矩阵

| # | R006 项 | 达标 | 实现与可核验证据 |
|---|---------|------|------------------|
| ① | dsh 插件形态 | ✅ | `package.json`（`type:module` + `main` + `dsh.bundle.patch`）+ `cordis.patch.yml`（`- insert:`）+ `lib/index.js`（`export const inject=['tools']`、`apply(ctx,config)`、`ctx.tools.register` 包在 `ctx.effect` 里）注册工具 `reflect_harvest` |
| ② | TCC 检测（能力边界） | ✅ | `--selfcheck` 三段：① 能力清单 ② **不该发生路径清单** ③ 依赖完整性；退出码 0 |
| ③ | CLD 自适应 | ✅ | 运行期只用 node 内置（fs/path/os/crypto/util）+ **零外部命令**；不 import 宿主私有路径；CLI 与插件挂载点解耦，无 CLD 也给出结论 |
| ④ | dsh 版本自适应 | ✅ | `peerDependencies` 正式声明 `@deepseek-ai/cordis` / `@deepseek-ai/dsh-tools`；运行期不 import 未声明模块；`--selfcheck` 显示**两级解析结果 + 实际版本**（本机：`cordis@4.0.2` / `dsh-tools@0.1.1-rc.2` via `profile`） |
| ⑤ | 文档化 | ✅ | 本文件（为什么/用法/退出码/十项矩阵/坑/复现命令）+ 源码 docstring；`package.json` → `r006.documented` |
| ⑥ | 版本管理 | ✅ | 版本**只**写在 `package.json`；CLI `--tool-version` 从 `package.json` 读（源码零硬编码）；`CHANGELOG.md` 含错误模型复盘 |
| ⑦ | 统一日志 | ✅ | `~/dsh-collab/logs/dsh-plugin-reflect-harvest.log`，每次动作记 时间/输入/判断/结果/诊断，**失败也留痕**；`--dry-run` 例外（不写日志，因为它的定义就是零变更，would-be 日志行打到 stdout） |
| ⑧ | 自动落链 | ✅ | `data/registry/dsh-plugin-reflect-harvest` 登记卡 + `package.json` → `r006.auto_chain` + 本文件 |
| ⑨ | CLI 治理 | ✅ | 旗标**单一来源** `lib/options.js`（冻结）；未知旗标/位置参数 → exit 2；`--dry-run` 零变更（D 项实测）；`--json`；`--help` 自解释 |
| ⑩ | 约束前置·不可绕过 | ✅ | 见下节（品牌机制 + 集合运算证明 + 写门 + **HTTP 原语收口 + 设备名门** + `--lean4-check` A–F） |

## ⑩ 结构门：为什么"不可绕过"不是靠纪律

**唯一的"不该发生路径"**：把**无证据的条目**当成有效混进 valid 集合。

| R006 §2 ⑩ 验收四条 | 本工具的实现 |
|---|---|
| **1. 没有那个入口** | 入参/schema/config 里**无法表达**"跳过证据"。证据门的唯一入口是 `mintAdmitted()`（不通过返回 `null`）；`buildValidSet()` 是 valid 集合的唯一 push 点，只收带品牌（`Symbol`，**不导出**）的条目。CLI 旗标与工具入参来自冻结的 `lib/options.js`，`--lean4-check` B 项用**集合运算**证明 11 个键里命中禁用片段 0 个（禁用片段：`skip/force/lenient/ignore/bypass/unsafe/relax/allowmissing/no-verify/nocheck/no-check`） |
| **2. 没有那个能力** | 全包**零 exec/spawn/child_process**（命令白名单 = 空集）；写副作用**只**出现在 `lib/out.js`，且每个写调用先过 `guardWritePath()` —— 治理库名（`RULES.md` / `governance-philosophy.json` / `rules.json` / `gallery`）是显式禁用词 |
| **3. 有那个证明** | `--lean4-check` A–F 全绿、exit 0（下方逐项） |
| **4. 失败即停** | `adjudicate` 不通过 → 条目进 `rejected`（带原因），`mintAdmitted` 返回 null → 永远进不了 valid。**没有任何"警告后继续"的分支** |

### `--lean4-check` 六项

| 项 | 证明内容 | 方法 |
|---|---|---|
| **A** | 源码无危险原语 | **去注释/字符串/正则字面量后**扫描 `eval` / `new Function` / `child_process`（R006 §6 坑#2：扫原文会把自己当靶子） |
| **B** | 负例全部被拒 | 证据负例 10 条（evidence 缺失 / null / 字符串 / 数组 / `{}` / 只 cmd 无 ts / 有 ts 但 cmd+output 全空 / ts 非字符串…）+ 字段类型负例 8 条 + 品牌负例 6 条（裸对象 → `UNBRANDED_ENTRY`）+ **写门负例 12 条**（写 RULES.md / governance-philosophy.json / rules.json / `../` 穿越 / 子目录 / 假 kind / 空路径…）逐条实测 |
| **C** | 正例可用 | 合法证据三种形态 + 四种 type + **5 个合法写目标**必须通过（防「门太宽把功能也砍了」） |
| **D** | `--dry-run` 零变更 | 前后**实测 6 项外部状态一致**：harvested 产物 / 日志大小 / `RULES.md` / 哲学库 / 包内 testdata / 实盘回填目录 |
| **E** | 白名单冻结 | `Object.isFrozen` 检查 `SUGGESTION_TYPES` / `ALL_REJECT_REASONS` / `ALLOWED_COMMANDS` / `GATE_META` / `OPTIONS_META` |
| **F** | 命令白名单 + **扫描器正控** + 写出口收口 | ① 正控：喂合成源码 `pExecFile('rm',…)` + `cp.exec('curl …')` + `re.exec(code)` + `fs.writeFileSync('/tmp/RULES.md')`，断言**真调用点被枚举到 2 条、良性接收者被识别 1 条、写点实参读得到** —— 否则是「空洞通过」；② 本包非良性 exec 调用点 0 个 ⊆ 空集；③ 写调用点全部位于 `lib/out.js`；④ 写语句命中治理库禁用词 0 次 |

### v1.1.0 新增能力 = 新增"不该发生路径"候选（已同步封堵）

跨设备层给本工具**新增了出站能力**（读中央黑板）。按 R006 §2 ⑩ 的要求，新增能力必须立刻检查
"它现在能做什么不该做的事"，并给出结构约束：

| 新能力 | 不该发生的路径 | 结构封堵 | 证明 |
|---|---|---|---|
| HTTP GET 黑板 | **写黑板**（替别设备代填；一旦能写，证据链当场失效 —— 谁说的、什么时候说的都不可信） | `lib/http.js` 只导出 `httpGetJson(url)`：**无 method 参数**、无通用 request 原语 | F 项扫描：全包 `http.request`/`fetch`/`XMLHttpRequest`/`net.connect`/`dgram` 调用点 **0 个**；允许的 HTTP 方法闭集 = `['GET']` |
| 同上（扫描器不能瞎） | 「0 个通用入口」若是**空洞通过**就毫无意义 | **HTTP 扫描器正控**：喂含 `http.request({method:'PUT'})`、`fetch(...,{method:'POST'})`、`XMLHttpRequest`、`net.connect` 的合成源码 | 正控命中 **4/4**（明细里逐条列出），而后才断言"本包 0 个" |
| 按设备名拼路径 / 拼黑板 key | 路径穿越（`../`）、污染别的设备 | **设备名门** `^[a-z0-9][a-z0-9._-]{0,31}$` | B 项设备名负例 **16/16 被拒**；C 项正例 6/6（含 `MAC-MINI→mac-mini` 归一化、纯数字名 `42`） |
| 读到的回填直接进提案 | 无证据的条目被摆到用户面前 | 仍是原来那条死线：`adjudicate`/`mintAdmitted`/`buildValidSet` | 全设备一视同仁（本地与黑板走同一条门） |

> 另：黑板不可达 → 逐设备报错并**继续用本地数据**（降级，不是抛栈）；
> `--local-only` 完全不触网，保证离线与测试场景可跑。

## 开发过程中被自己的门抓到的错误（如实登记）

这台工具的开发过程本身又验证了一次「检查会撒谎」：

1. **写扫描器漏掉自己的主要目标**：初版正则写 `(?<![\w.$])`（把 `.` 也排除），因为 `fs.writeFileSync(` 的前缀是 `.`，
   **所有写调用点被漏掉** → 枚举 0 个 → 「0 个越界写」**空洞通过**。
   → 抓到的正是 B/F 的**扫描器正控**（喂进去的 `fs.writeFileSync('/tmp/RULES.md')` 命中 0）。修法：负向后顾只排除 `[\w$]`。
2. **扫描器把自己当靶子**：改好之后 F 项立刻变红 —— 它把 gate.js 里的 `re.exec(code)` 当成了外部命令执行点（R006 §6 坑#2）。
   两种错修都要避免：收紧正则会**顺手关掉真漏洞**（`cp.exec('ls')` 漏掉），静默 filter 则是"看不见的豁免"。
   → 修法：照常枚举，识别接收者，标 `benign:true` 并**在图示里计数**（谁被豁免、豁免几次，输出里看得见）；
   正控同时断言"良性被识别 **且** 真调用仍被枚举"。
3. **聚类阈值单判据会漏合**：初版只用 `Dice ≥ 0.52`，实测把「3 个智能体独立提到」错拆成 `1+1+1`（A/B 共享 13 个 bigram 却只有 0.491）。
   → 修法：加双判据（见上），并把灰区对**显式列出**而不是隐藏。

4. **`items` 字段的语义歧义**（v1.1.0）：单体回填 `{agent, items:[反思条目]}` 被我当成捆扎包解析
   → 一条反思被拆成一堆"缺 agent"的碎片，mac-mini 的 4 份回填**全部文件级拒收**。
   靠按设备统计里的 `文件级拒收 4` + `第 N 条缺 agent` 发现。
5. **复现计数按错维度去重**（v1.1.0）：`recurrenceOf()` 按 `m.agent`（只有智能体名）去重，
   于是两台设备上同名的 `agent-echo` 被合并 → `recurrence=4`，而同一行明细 `lab-mbp×1 + mac-mini×3 + mbp×1` 加起来是 **5**。
   **这次是"人眼看明细"发现的，不是工具** —— 因此补上了 D 项的「**产出不变量**」自动检查
   （`recurrence === agents.length` / `cross_device ↔ devices` / 分设备求和=全局），让机器能自己抓住"同一份输出里两个字段互相矛盾"。

> 结论同 R006 §6：**假阳性会让人去修不存在的问题，空洞通过会让人误信不存在的能力** —— 两者都比"没检查"更危险。

## 常见的坑（本工具实测踩过/防住的）

| # | 坑 | 本工具怎么防 |
|---|---|---|
| 1 | 门太宽 | 先精确命中白名单（`SUGGESTION_TYPES` 闭集），再判非法值；C 项专门证明"合法输入能过" |
| 2 | 扫描器误伤自己 | `stripLiterals()` 先剥注释/字符串/正则字面量；良性接收者**显式上报**而非静默豁免 |
| 3 | 空洞通过 | 扫描器**正控**（B/F）；去字面量定位 → **回原文读实参**（`literal:false` 显式暴露） |
| 4 | 假失败 | peer 两级解析；`sourceFiles` 未给时如实说"符号检查已跳过"，不假装通过/失败 |
| 5 | 检查报错原因 | 环境问题（peer 缺失 / 目录不存在 / 参照库不可读）与包问题（源码缺符号）分开报告，且参照库不可读时**跳过**判定而不是误判 |
| 6 | 两处版本 | 版本单一来源 `package.json` |
| 7 | 落链缺失 | ⑧ 登记卡 + `package.json r006.auto_chain` + 本文件 |

> 另注：本机非登录 shell 的 `PATH` 里没有 node（在 `/opt/homebrew/bin`）。跑本包命令请先 `export PATH="/opt/homebrew/bin:$PATH"`，
> 或写绝对路径 —— 这属 R006 §6 坑#5（**环境问题不要报成包问题**）。

## 复现命令（可复制即用）

```bash
export PATH="/opt/homebrew/bin:$PATH"
cd ~/dsh-collab/devices/dsh-plugin-reflect-harvest

# 1) 自查门 + 能力边界（②③④）—— 期望 exit 0
node cli.js --selfcheck; echo "exit=$?"

# 2) 结构门自证（⑩）—— 期望 A–F 全绿、exit 0
node cli.js --lean4-check; echo "exit=$?"

# 3) 版本与零变更（⑥⑨）
node cli.js --tool-version                     # 需与 package.json 的 version 一致
node cli.js --date 2026-09-10 --dry-run; echo "exit=$?"

# 4) 用包内 fixture 跑一遍跨设备收牌（零风险：testdata 只读）
mkdir -p ~/dsh-collab/data/reflect/answers ~/dsh-collab/data/reflect/cards
cp -R testdata/data/answers/mac-mini testdata/data/answers/mbp ~/dsh-collab/data/reflect/answers/
cp -R testdata/data/cards/i9 ~/dsh-collab/data/reflect/cards/
node cli.js --date 2026-09-10 --devices mac-mini,mbp,i9 --device mac-mini --summary
# 想要真跨设备：把某设备的回填 PUT 到中央黑板 data/reflect/answers/<device>/<date>，
# 再把 <device> 加进 --devices（本工具只 GET，写入由设备自己/上游完成）

# 5) CLI 治理（⑨）
node cli.js --nope; echo "exit=$?"             # 期望 2
node cli.js --date 2026-09-10 --json | python3 -m json.tool > /dev/null && echo "json ok"

# 6) ⑧ 落链回读（黑板 key 首段必须是纯小写字母，否则 400）
curl -s http://127.0.0.1:8792/data/registry/dsh-plugin-reflect-harvest | head -c 200

# 7) 跨设备源实测（可核验：lab-mbp 走黑板 GET）
curl -s http://106.53.214.108:8792/data/reflect/answers/lab-mbp/2026-09-10 | head -c 120
```

## 结构与职责

```
dsh-plugin-reflect-harvest/
├── package.json          ① shape + ⑥ 版本单一来源 + r006 段
├── cordis.patch.yml      ① 插件行（- insert: [{id,name,config}]）
├── cli.js                ⑨ CLI 治理 + ②selfcheck + ⑩lean4-check
├── lib/
│   ├── index.js          ① apply(ctx) + inject=['tools'] + ctx.tools.register
│   ├── gate.js           ⑩ 证据门（adjudicate / mintAdmitted / buildValidSet）+ 冻结闭集 + 扫描器
│   ├── out.js            ⑦ 统一日志 + ★ 全包唯一写副作用模块（guardWritePath 写门）
│   ├── harvest.js        业务内核：读取 → 文件级/条目级校验 → 聚类 → 复现计数（零危险原语）
│   ├── lesson.js         归一化 / bigram Dice / 双判据聚类 / 灰区矩阵
│   ├── catalog.js        参照库索引（**只读**）：RULES.md 规则号 + 哲学号
│   ├── http.js           ★ 出站原语（**只有 GET**，无 method 参数）+ HTTP 调用点扫描与正控
│   ├── devices.js        设备表解析 + 设备名门（挡黑板 key 与本地路径双穿越）
│   ├── source.js         回填源：本地目录 + 中央黑板 → 归一化 → (device,agent) 去重
│   ├── options.js        ⑨ 旗标与工具入参的单一来源（冻结）→ 「没有那个入口」用集合运算证明
│   └── selfcheck.js      ② R014 自查门（apply 最前调用）
├── testdata/data/        只读 fixture（跨设备布局：answers/{mac-mini,mbp,lab-mbp}/<date>/ + cards/i9/）
│                         —— 含 5 类故意缺陷，供 --lean4-check D 项实测（零出站）
├── docs/README.md        ⑤ 本文件
└── CHANGELOG.md          ⑥ 变更 + 纠错复盘
```

## 相关

- 规格：`~/dsh-collab/docs/R006-插件化工具化标准-v3.0.md`（唯一权威）
- 参考实现：`~/dsh-collab/devices/dsh-plugin-cldvoice-activate/`
- 下游：`~/dsh-collab/devices/dsh-plugin-reflect-synthesize/`（⑤ 提炼 → `proposal-<date>.md`）
- 哲学依据：`phi-constraint-frontloaded`（约束前置·不可绕过）· `phi-truth`（无验证的成功=未成功）· `phi-facts`（无验证不陈述）
