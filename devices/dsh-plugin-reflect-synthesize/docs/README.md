# dsh-plugin-reflect-synthesize · 每日反思流水线「提炼」（⑤）— R006 十项达标

> 星桥 · 2026-09-10 · v1.0.0 · R006 ①–⑩ 全达标 · 位置 `~/dsh-collab/devices/dsh-plugin-reflect-synthesize/`

## 为什么需要它（实证，不是推测）

流水线：

```
① collect → ② dispatch → ③ 各智能体回填 → ④ harvest（收牌+证据门+复现计数）
   → ⑤ synthesize ★本工具（提炼成**待裁定的提案**）→ ⑥ 用户裁定 → ⑦ enroll（入册+反馈）
```

**本工具是全流水线里唯一需要"判断"的环节**（design §七「诚实的边界」明确承认：
「是应用还是新维度」需要语义判断，无法纯规则化）。所以它必须诚实地分成两半：

| 一半 | 做法 | 例子 |
|---|---|---|
| **机械可判** | 规则 + 关键词重合 + 显式措辞 | `related_rule` 是否存在、lesson 与某条目的 bigram 重合度、有没有带新词、有没有**显式**冲突措辞 |
| **判不了** | ★ **显式标 `unclear`，进「需人工/LLM 复核」清单** | 「这条和那条规则是不是在说同一件事」、多条目并列时该并给谁 |

**为什么"不许硬猜"不是洁癖**：synthesize 的输出会变成用户裁定的依据。一个被硬猜出来的
`already-application`（"已有规则覆盖了"）会让一条真正的盲区**连被看见的机会都没有** ——
它被归进"无需动作"，然后消失。而标 `unclear` 只让用户多看一眼。
**两种错的代价不对称，所以拿不准的一律进待复核清单。**

## 用法

```bash
node cli.js --date 2026-09-10              # 生成 proposal-2026-09-10.md（待裁定）
node cli.js --date 2026-09-10 --preview    # 提案全文打到 stdout，不落盘
node cli.js --date 2026-09-10 --summary    # 终端摘要（跨设备优先 + 复现广度）
node cli.js --date 2026-09-10 --dry-run    # 只算不写：提案产物/日志/参照库 全部零变更
node cli.js --date 2026-09-10 --json       # 机器可读
node cli.js --selfcheck | --lean4-check | --tool-version | --help
```

**退出码（R006 ⑨ 固定语义）**：`0` 成功/门生效 · `1` 失败/门失效 · `2` 用法错误或 IO 错误

| 情形 | 退出码 | 实测 |
|---|---|---|
| 正常提炼 | 0 | `--summary` / `--preview` / 生成 均 0 |
| 未知旗标 `--nope` | 2 | `用法错误: Unknown option '--nope'` |
| 多余位置参数 | 2 | `Unexpected argument 'foo'` |
| `harvested-<date>.json` 不存在 | 2 | `IO 错误 [NO_HARVESTED] …（不代跑、不猜）` |
| 收牌产物结构不对 | 2 | `IO 错误 [BAD_SHAPE] 缺 clusters 数组` |
| 门失效（A–F 有红） | 1 | `门未生效，禁止交付` |

## 四步（每步都在输出里体现）

### 第 1 步 · 对照现有库

读 `rules-registry/RULES.md`（规则）与 `data/blueprint/gallery/governance-philosophy.json`（哲学），
对每个 cluster 判定（闭集，冻结）：

| 判定 | 含义 | 机械判据 |
|---|---|---|
| `already-application` | 已有条目**覆盖**它，这只是应用 | 命中**决定性**（最佳重合 ≥ 明显领先第二名）且覆盖率 ≥ 60% 且智能体自评「无需动作」 |
| `extends-existing` | 是已有条目的**延伸/补维** | 命中决定性，且相对该条目带 ≥4 个新词（如 Φ13 之于 phi-facts） |
| `new-dimension` | 现有条目**未覆盖** | 与全部条目的最高重合 < 5 |
| `conflicts` | 与现有条目**冲突** | **仅**在出现显式冲突措辞时（`与 <id> 直接冲突`/`推翻 <id>`/`<id> 已失效`）；**工具不猜语义冲突** |
| `unclear` | ★ 规则判不了 | 命中非决定性（多条目并列）/ 引用了**不存在**的条目号 / 重合落在灰区 —— **必须显式标出，交人工/LLM 复核** |

**为什么"最高重合 < 5"算未覆盖**：中文短句之间**总会有** 1-3 个偶然共享的 bigram。
实测（2026-09-10 fixtures）：两条完全无关的 lesson（"移动设备休眠" vs "红绿灯互斥"）共享 2 个 bigram。
若把 2 当"弱命中"，就会把噪音当成"已有条目覆盖"，**进而阻塞真正的新维度**。

**为什么"引用不存在条目"必须 unclear**：agent 填了 `R099`（库里没有）——
是笔误？还是它想新建一条？**机器无从判断**，只能交人。

### 第 2 步 · 分类归档（闭集，冻结）

| 判定 | → 类别 | 处置 |
|---|---|---|
| `already-application` | 归档为案例 | 只登记，不新增 |
| `extends-existing` | 并入/补维 | 指出并入哪条 + 补的是哪些新词 |
| `new-dimension` + `转规范` | 转规范 | 目标 SOP 由关键词**推测**并标注"需人工确认" |
| `new-dimension` | 拟新增哲学 / 拟新增规则 | 内容形态**启发式**（信号词），**并强制把"哲学还是规则"作为用户的裁定项** |
| `conflicts` | 需裁决冲突 | 用户裁决：修订既有条目 / 本条作废 / 并存 |
| `unclear` | 需人工复核 | ★ 单列 |

### 第 3 步 · ★ 排序 = `(cross_device, recurrence)` 二元组

**跨设备优先，同设备内再按复现广度**（design §10.7）。

> 不同设备跑的是**不同任务、不同上下文**，它们**独立**踩到同一个坑 ⇒
> 这不是某条工作流的偶然，而是**系统性缺陷**。比"同机多会话"强得多。

### 第 4 步 · 生成提案（看一眼就能裁）

`proposal-<date>.md` 结构：

```
〇 裁定速览（30 秒）   一句话 | 复现 | 跨设备 | 对照现有库 | 建议处置 | 你要裁什么
一 逐项明细          摘要 / 涉及智能体 / 证据引用表 / 对照结果与依据 / 建议处置与提案片段 / ★你要裁什么
二 无需裁定          已归档为案例（仅登记）
三 ★ 需人工/LLM 复核清单
四 统计与来源        设备表 / pending / 判定与处置分布 / 拒收分布 / 版本漂移
附 裁定怎么落下去（⑥→⑦）
```

格式约定：**速览表在前，理由在后**（想裁的人看表，想看理由的人往下翻）；
每项都带**勾选框**（裁定是打勾，不是写文章）；★ 跨设备信号**必须一眼可见**；
涉及启发式判断的（哲学 vs 规则）**不藏起来**，直接在"你要裁什么"里让用户选。

安全：提案正文含**agent 提交的原始文本**，一律先做 markdown 转义（表格 `|`、换行、反引号）——
否则一条含 `|` 的 `pit` 就能把整张表拆坏（渲染层注入）。

## R006 十项达标矩阵

| # | R006 项 | 达标 | 实现与可核验证据 |
|---|---------|------|------------------|
| ① | dsh 插件形态 | ✅ | `package.json`（`type:module`+`main`+`dsh.bundle.patch`）+ `cordis.patch.yml`（`- insert:`）+ `lib/index.js`（`inject=['tools']`、`apply(ctx,config)`、`ctx.tools.register` 包在 `ctx.effect`）注册工具 `reflect_synthesize` |
| ② | TCC 检测 | ✅ | `--selfcheck` 三段：① 能力清单 ② **不该发生路径清单**（含集合运算证明）③ 依赖完整性；exit 0 |
| ③ | CLD 自适应 | ✅ | 只用 node 内置（fs/path/os/crypto/util）；**零外部命令、零网络**；不 import 宿主私有路径 |
| ④ | dsh 版本自适应 | ✅ | `peerDependencies` 正式声明 cordis/dsh-tools；`--selfcheck` 显示两级解析结果 + 实际版本（本机 `cordis@4.0.2` / `dsh-tools@0.1.1-rc.2` via `profile`） |
| ⑤ | 文档化 | ✅ | 本文件（为什么/用法/退出码/四步/十项矩阵/坑/复现命令）+ 源码 docstring；`package.json → r006.documented` |
| ⑥ | 版本管理 | ✅ | 版本只写 `package.json`；`--tool-version` 从包读；`CHANGELOG.md` 含错误模型复盘 |
| ⑦ | 统一日志 | ✅ | `~/dsh-collab/logs/dsh-plugin-reflect-synthesize.log`（时间/输入/判断/结果/诊断，失败也留痕）；`--dry-run` 例外（零变更） |
| ⑧ | 自动落链 | ✅ | `data/registry/dsh-plugin-reflect-synthesize` 登记卡 + `package.json → r006.auto_chain` + 本文件 |
| ⑨ | CLI 治理 | ✅ | 旗标单一来源 `lib/options.js`（冻结）；未知旗标/位置参数 → exit 2；`--dry-run` 零变更（D 项实测）；`--json` / `--preview` / `--help` |
| ⑩ | 约束前置·不可绕过 | ✅ | 见下节 |

## ⑩ 结构门：为什么"不能改库"不是靠自觉

**唯一的"不该发生路径"**：替用户改**哲学库 / 规则库**（`RULES.md` / `governance-philosophy.json`）。

依 据 `phi-user-sovereignty`（决策权在用户）+ `phi-027`（能力与权限分离）：
synthesize 在 ⑤ 只是**提案生成器**；入册（⑦ enroll）才可能碰库，且那在用户 ⑥ 裁定**之后**。

| R006 §2 ⑩ 验收四条 | 实现 |
|---|---|
| **1. 没有那个入口** | 旗标/入参来自**冻结**的 `lib/options.js`，`--lean4-check` B 项用**集合运算**证明 13 个键里命中禁用名 **0 个**（禁用名：`apply/enroll/write-rules/write-philosophy/out/output/target/dest/destination/rule/rules-file/phi-file/registry`…） |
| **2. 没有那个能力** | 写目标来自冻结的 `WRITE_SPEC`，只有三个语义名 `proposal-md / unified-log / selfcheck-state`。`guardWritePath()` 四道判定：kind 白名单 → 禁用词（`RULES.md`/`governance-philosophy.json`/`rules.json`/`rules-registry`/`gallery`/`blueprint`）→ 必须在基目录内且**不得多一级子目录** → 文件名匹配模板。**`rules-registry/` 与 `data/blueprint/gallery/` 根本不在任何基目录之下 → 那些路径构造不出来** |
| **3. 有那个证明** | `--lean4-check` A–F 全绿、exit 0（见下） |
| **4. 失败即停** | `guardWritePath` 抛 `GateError`，调用方拿不到路径；**没有任何"警告后继续"的分支** |

### `--lean4-check` 六项

| 项 | 证明内容 | 方法 |
|---|---|---|
| **A** | 源码无危险原语 | 去注释/字符串/正则字面量后扫描 `eval` / `new Function` / `child_process` |
| **B** | 负例全部被拒 | **写门负例 13/13**（写 RULES.md / governance-philosophy.json / rules.json / rules-registry / gallery / `../` 穿越 / 子目录 / 假 kind `apply`·`enroll` / 空值）+ **输入侧证据门负例 11/11** + 旗标集合运算 0/13 命中 |
| **C** | 正例可用 | 写目标 5/5 可用 + 输入侧证据门正例 3/3 + **判定分支覆盖 5/5**（`already-application`/`extends-existing`/`new-dimension`/`conflicts`/`unclear` 各造一条合成 cluster 实测 —— 防"分支从来没被执行过"） |
| **D** | `--dry-run` 零变更 **+ 产出不变量** | 前后 **5 项**外部状态一致（提案 / 日志大小 / RULES.md / 哲学库 / 包内 harvested）+ 不变量：跨设备优先排序生效、复现明细之和 = `recurrence`、`cross_device ↔ devices`、分布求和 = 项数 |
| **E** | 白名单冻结 | `Object.isFrozen` 检查 `JUDGMENTS`/`CATEGORIES`/`ALLOWED_COMMANDS`/`GATE_META`/`OPTIONS_META`/`OUT_META`/`JUDGE_RULE` |
| **F** | 命令白名单 + **扫描器正控** + 写出口收口 | ① 正控：喂 `pExecFile('rm')`+`cp.exec('curl …')`+`re.exec`+`fs.writeFileSync('/tmp/RULES.md')`，断言真调用 2 / 良性 1 / 写点 1；② 本包非良性 exec 调用点 **0**；③ **写调用点全部位于 `lib/out.js`**；④ 写语句命中治理库禁用词 **0** —— 「无写库路径」由此得到源码级证明 |

## 开发中被自己的检查抓到的错误（如实登记）

| # | 错误模型 | 后果 | 怎么发现的 | 修法 |
|---|---|---|---|---|
| 1 | 以为 `extends-existing` 必须由 agent **自己填**规则号 | 一个与 Φ12 关键词重合 **17** 的 cluster 因为 agent 填了「无」而掉进 `unclear` —— **工具在最该认出它的时候瞎了**（恰恰是新入册的条目，agent 还不知道它存在） | `--json` 里逐项看 `best_match.overlap / novelty`，发现 17 却判 unclear | 去掉"必须自填引用"的要求；改用**决定性**（最佳重合明显领先第二名）+ 覆盖率 + novelty 判定 |
| 2 | 以为 bigram 列表可以直接给用户看 | 提案里出现「补的是『证证、据要、要标、注采』这一维」—— **实现细节泄漏到渲染层**，看着像乱码，反而让人不敢裁 | 人眼看生成的 proposal 全文 | 回到**归一化原文**上取连续 fresh 片段 → 输出「注采集时点」「据要标注」这类真词（初版从 bigram 反推只拼出 3 字符、丢了中间：实测「前集时」而非「前采集时」） |
| 3 | 冲突正则只允许紧邻 | 「与 R006 **直接**冲突」因为中间夹了 2 个字而**漏判** → `conflicts` 分支形同不存在 | **判定分支覆盖自测**（5 个分支逐条合成实测）：`conflicts→❌got:new-dimension` | 正则允许 ≤8 个非断句字符间隔；并把 5 分支自测固化成 C 项的常规检查 |
| 4 | 以为负例里放什么都会被拒 | 把合法的 `MAC-MINI`（应归一化）等错列成负例 → 制造"永远修不掉的红"（同类错误在 harvest 侧也犯过一次） | B 项 `★竟然放行` 明细 | 修正**我自己的测试期望** |

> 第 1 条最值得记：它不是崩溃，是**静默降级**（该认出的没认出）。
> 唯一能发现它的手段是**逐项打印判定的中间量**（overlap / novelty / coverage / decisive）——
> 所以这些量在 `--json` 输出里全部保留，可复核。

## 常见的坑（本工具实测踩过/防住的）

| # | 坑 | 本工具怎么防 |
|---|---|---|
| 1 | 门太宽 | 先精确命中白名单（三个语义名），再判非法值；C 项专门证明"合法输入能过"（写目标 5/5 + 判定分支 5/5） |
| 2 | 扫描器误伤自己 | `stripLiterals()` 先剥注释/字符串/正则；良性接收者（`re.exec`）**显式上报**而非静默豁免 |
| 3 | 空洞通过 | 扫描器**正控**（F）；去字面量定位 → **回原文读实参**（`literal:false` 显式暴露）；**判定分支覆盖自测**（C） |
| 4 | 假失败 | peer 两级解析；`sourceFiles` 未给时如实说"符号检查已跳过"；参照库不可读时标 `unclear` 而不是假装"没有匹配" |
| 5 | 检查报错原因 | 区分「**读不到库**」与「**库里没有**」—— 混为一谈会把"读失败"误判成"新维度提案"（notes 里显式写明） |
| 6 | 两处版本 | 版本单一来源 `package.json`；bigram 原语**不复制** harvest 的聚类规则（见 `lib/lesson.js` 的说明） |
| 7 | 落链缺失 | ⑧ 登记卡 + `package.json r006.auto_chain` + 本文件 |

> 另注：本机非登录 shell 的 `PATH` 里没有 node（在 `/opt/homebrew/bin`）。跑本包命令请先
> `export PATH="/opt/homebrew/bin:$PATH"` —— 这属 R006 §6 坑#5（**环境问题不要报成包问题**）。

## 复现命令（可复制即用）

```bash
export PATH="/opt/homebrew/bin:$PATH"
cd ~/dsh-collab/devices/dsh-plugin-reflect-synthesize

# 1) 自查门 + 能力边界（②③④）—— 期望 exit 0
node cli.js --selfcheck; echo "exit=$?"

# 2) 结构门自证（⑩）—— 期望 A–F 全绿、exit 0
node cli.js --lean4-check; echo "exit=$?"

# 3) 版本与零变更（⑥⑨）
node cli.js --tool-version
node cli.js --date 2026-09-10 --dry-run; echo "exit=$?"

# 4) 用真实链路跑一遍（需先跑 ④ harvest）
node ~/dsh-collab/devices/dsh-plugin-reflect-harvest/cli.js --date 2026-09-10 --summary
node cli.js --date 2026-09-10 --summary
node cli.js --date 2026-09-10 --preview | head -40

# 5) CLI 治理（⑨）
node cli.js --nope; echo "exit=$?"                       # 期望 2
node cli.js --date 2026-09-10 --json | python3 -m json.tool > /dev/null && echo "json ok"

# 6) ★ 证明"写不了库"：直接试一把（会被门拒绝）
node -e "import('./lib/out.js').then(o=>{try{o.guardWritePath('proposal-md', process.env.HOME+'/dsh-collab/rules-registry/RULES.md')}catch(e){console.log('拒绝 OK:',e.code)}})"

# 7) ⑧ 落链回读
curl -s http://127.0.0.1:8792/data/registry/dsh-plugin-reflect-synthesize | head -c 200
```

## 结构与职责

```
dsh-plugin-reflect-synthesize/
├── package.json          ① shape + ⑥ 版本单一来源 + r006 段
├── cordis.patch.yml      ① 插件行（- insert: [{id,name,config}]）
├── cli.js                ⑨ CLI 治理 + ②selfcheck + ⑩lean4-check
├── lib/
│   ├── index.js          ① apply(ctx) + inject=['tools'] + ctx.tools.register
│   ├── gate.js           ⑩ 冻结闭集（判定/分类/写目标/禁用词）+ 输入侧证据门 + 扫描器
│   ├── out.js            ⑦ 统一日志 + ★ 全包唯一写副作用模块（guardWritePath 写门）
│   ├── synthesize.js     内核：读取 → 输入侧证据门 → 对照 → 分类 → 排序 → 生成
│   ├── analyze.js        第 1–3 步：judgeCluster / classify / sortKey + 5 分支自测
│   ├── proposal.js       第 4 步：proposal-<date>.md（看一眼就能裁）+ markdown 转义
│   ├── catalog.js        现有库索引（**只读**）：规则 + 哲学 + 每条的 bigram 词表
│   ├── lesson.js         字符 bigram 原语（**不复制** harvest 的聚类规则）
│   ├── options.js        ⑨ 旗标与入参单一来源（冻结）→「没有那个出口」用集合运算证明
│   └── selfcheck.js      ② R014 自查门（apply 最前调用）
├── testdata/             只读 fixture（real-ish harvested-<date>.json）—— 供 D 项实测（零变更）
├── docs/README.md        ⑤ 本文件
└── CHANGELOG.md          ⑥ 变更 + 纠错复盘
```

## 相关

- 规格：`~/dsh-collab/docs/R006-插件化工具化标准-v3.0.md`（唯一权威）
- 流水线设计与跨设备层：`~/dsh-collab/docs/daily-reflection-pipeline-design-v1.md`（§10）
- 上游：`~/dsh-collab/devices/dsh-plugin-reflect-harvest/`（④ 收牌 → `harvested-<date>.json`）
- 下游：`dsh-plugin-reflect-enroll`（⑦ 入册，**用户裁定之后**才写库）
- 哲学依据：`phi-user-sovereignty`（用户主权）· `phi-027`（能力权限分离）· `phi-facts`（无验证不陈述）
