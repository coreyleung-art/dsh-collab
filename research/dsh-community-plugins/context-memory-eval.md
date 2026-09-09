# 评估报告：dsh 上下文/记忆类插件

> 数据调查员委派子代理 · 深度评估报告（web_search + GitHub 源码/package.json + 本机实测三方交叉核验）
> 评估日期：2026-09（market index 扫描 2026-09-06，4508 条）

## 本机环境基线（评估前提，实测）

| 项 | 实测值 |
|---|---|
| Harness 核心 | `@deepseek-ai/dsh-base/session/agent/tools/web-app` 全系 **0.1.1-rc.2**（`~/.dsh/profiles/node_modules`） |
| 已装相关插件 | `@liustack/modlens ^3.16.7`、`@linxin666/dsh-web-ui-all 0.1.16`（含 localStorage 任务看板/SSH）、`dsh-knowledge ^0.1.0` + knowledge-tools(link)、openchronicle、guard、central-inbox、bus-bridge、market、genui 等 30+ |
| 记忆/上下文栈 | dsh-knowledge（混合 BM25+向量、文档/文件夹级）+ OpenChronicle + Obsidian/ChromaDB MCP + 编号规则/报告纪律（R006 体系） |
| 缺口确认 | 无 dsh-context、无任何 compaction 插件（CLD-017「上下文只增不减、compaction 未挂载」描述属实） |

---

## 1️⃣ bowenliang123/dsh-context — 1305★

- **URL**：[github.com/bowenliang123/dsh-context](https://github.com/bowenliang123/dsh-context)（npm `dsh-context`，Apache-2.0，v0.43.0）
- **核心能力**：纯**上下文观测/管理仪表**——Context 页（Stats / Token 环 / Trend / Browser / Events / File Activity / Agent Network）+ `/context` 命令。逐请求（Step 级）展示上下文组成与增量，把 **compaction / prune 事件钉在趋势柱上**显示回收量；Context Browser 可展开每个元素（system prompt、工具 schema、tool 结果、图片 token 估值），可回看 compaction 之前的步骤（从 removed-message 归档重建，标注 approximate）。占用读数与官方 composer context ring 同源（`contextPressure/contextBreakdown`），所见即 composer 所告。
- **与本机已有能力对比**：本机无任何"上下文组成/演进"可视化（仅 composer 环形灯 + 会话语义检索）。这是**诊断层**工具，不做回收。
- **CLD-017/compaction 关系**：**它不执行 compaction、不直接解决 CLD-017**，但回答 CLD-017 的"上下文到底谁在涨、compaction 何时发生/回收了多少"——先归因后治理，也是挂载任何 compactor 后验证效果的仪表。真正的回收需另配 compaction 插件（市场上如 `dsh-compaction-cacheaware` / `dsh-auto-compact` / `compact_now` 系 + preset compaction 配置），建议与 dsh-context 同批立项。
- **安装方式**：`dsh plugin --profile web add dsh-context` → 重启 `dsh web`。零构建（lib 已随包发布）。
- **⚠️ 版本红线（关键）**：官方 [compatibility.md](https://github.com/bowenliang123/dsh-context/blob/main/docs/compatibility.md) 实测矩阵——**0.1.1 线与 0.1.2-alpha 预览仅支持到 `dsh-context@0.41.x`**；0.42+/0.43（当前 main）要求 dsh **0.1.2-rc.1+**（peerDeps `dsh-session >=0.1.2-rc.1`，manifest 声明 `dshReleases: {0.1.2-rc.1: compatible}`）。本机是 0.1.1-rc.2 → **必须装 @0.41.x，勿装 latest**；或先升 harness 0.1.2-rc1 再装最新。
- **新增价值评分：5 / 5**（诊断层唯一，直接支撑 CLD-017 归因；其余候选与其无重叠）
- **安装建议：装-优先**（条件：`dsh-context@0.41.x`）
- **风险**：低——只读仪表 + 事件订阅，client 侧为主；主要风险是误装 0.42+ 在 rc.2 上 seam 断链。勿误认为装上即治 OOM。

---

## 2️⃣ dsh-memory —（名称歧义，实测 2 个同名仓）

简报描述（"shared persistent memory store across all sessions + memory_* tools + sidebar"）精确匹配 **joyiok/dsh-memory**：

- **joyiok/dsh-memory — 0★**：[github.com/joyiok/dsh-memory](https://github.com/joyiok/dsh-memory)
  - 共享 JSON 记忆库 `$DSH_HOME/storages/dsh-memory.json`（原子写：临时文件+rename、mtime 感知），工具 `memory_add / memory_search / memory_list / memory_remove` + Web 侧栏 Memory 面板；关键词/标签匹配，**无嵌入、无向量**。web / headless / 任意工作目录会话共享同一份数据。
- 另有工程好得多的同名仓 **chenhw7/dsh-memory「Cairn」— 1★**：[github.com/chenhw7/dsh-memory](https://github.com/chenhw7/dsh-memory)（npm `@chenhw7/dsh-memory`）
  - BM25（CJK 感知 unigram+bigram、CI 金标集 35×35 success@5=100%、MRR=0.902）、三层作用域（global/project/user）、9 个 memory_* 工具、写路径安全扫描/脱敏、**compaction-aware flush**（压缩遮蔽旧上下文时扫描 raw events 补记）、可选人工确认写入（confirmBeforeWrite）、过期软衰减、审计日志、Memory 管理 UI。

- **与本机已有能力对比**：本机已有 **dsh-knowledge（跨会话持久 + 混合 BM25/向量检索 + 文件夹/文档级）** + OpenChronicle（oc_* 活动记忆）+ Obsidian/ChromaDB MCP——三套跨会话记忆通道。joyiok 是**更弱的第四通道**（单文件、无语义检索、无安全扫描，作者自警勿存密钥）。Cairn 的"compaction-aware flush + 人工确认写"确实与 CLD-017 相关，但需自挂提取管线，且同样是"再开一条记忆通道"，与本机知识库重叠。
- **新增价值评分：1 / 5**（joyiok 完全重复且更弱）；Cairn 单独评 **2 / 5**（机制新，但通道冗余 > 增量）
- **安装建议：不装-重复**。若未来确有"跨 profile 共享 + 人审写入"硬需求，选 **Cairn 而非 joyiok**。
- **风险**：明文 JSON 全会话可见（敏感信息风险）；与 KB/OC 三库并存造成记忆漂移与检索不一致。

---

## 3️⃣ GraySilver/dsh-evolve-modes — 197★

- **URL**：[github.com/GraySilver/dsh-evolve-modes](https://github.com/GraySilver/dsh-evolve-modes)（npm `@graysilver/dsh-evolve-modes`，v0.4.0，MIT）
- **核心能力**：输入区四维可组合工作流控制——工作状态（正常/计划）+ 思考策略（标准/第一性原理/Grilling）+ 质量门禁（关/对抗性审查/验收审查）+ 自进化（关/开）。自进化为 **Propose 默认**：每 3 次父回复触发一次**隔离学习请求**（专用 persona、不带工具/历史/AGENTS.md），产出**须人工确认**的规则提议 → 写入插件自有 storage domain 的 "learned instructions" system-prompt section（**不写 AGENTS.md/CLAUDE.md/项目文件**，带自动备份/恢复、学习运行记录）。
- **与本机 R006 规则体系关系**：本机 R006 为部署级文件化规则 + 报告/登记纪律（agent 档案登记、guard P0-P8 等，属 preset/协调层治理）。evolve-modes 是**独立第二规则通道**：其"人工审阅 → 全局注入 system prompt"流程可作为 R006 的**提议采集器**（人审环节可与 R006 桥接对账），但批准后是**跨会话自动注入**，与 R006 文件规则并存需人工映射；两者可能重复或冲突。**质量门禁与思考策略维度是 R006 没有的纯增量**。
- **版本兼容**：0.4.0 peerDeps `^0.1.1-rc.2` → **与本机 0.1.1-rc.2 精确兼容**（5 个候选中唯一现装即合；0.3.1 为 0.1.0-rc.6 兼容线）。
- **新增价值评分：3 / 5**（门禁/组合是增量；进化通道与 R006 重叠，且全局注入有上下文膨胀副作用）
- **安装建议：可选**（推荐首期只开「质量门禁 + 计划/第一性原理」维度，进化保持 Propose 不批准或小批次）
- **安装命令**：`npx -y @deepseek-ai/dsh plugin --profile web add @graysilver/dsh-evolve-modes@0.4.0` 后重启 profile。
- **风险**：①每条已批准全局规则**永久占据 system prompt** → 与 CLD-017 目标相悖，务必克制批准量、只开 Propose；②每次质量审查 +1 次模型调用（成本/延迟）；③审查依赖 fork/subagent 能力（本机具备）；④注入段落位置影响 KV-cache 前缀稳定性。

---

## 4️⃣ liustack/modlens — 3713★

- **URL**：[github.com/liustack/modlens](https://github.com/liustack/modlens)（npm `@liustack/modlens`）
- **核心能力**：DSH 视觉桥——粘贴图片 → `modlens_read_image` 结构化证据（OCR/版面/语义）；自动把纯文本 DeepSeek/GLM/MiMo 模型包一层 "(modlens vision)" 路由（逐模型元数据判定，原生多模态模型不动）。零钩子、零守护进程，一个插件即装即用。
- **与本机已有能力对比（结论：已等效且已装）**：本机 web profile bundle 已含 **`@liustack/modlens ^3.16.7`**（node_modules 实测），`modlens_read_image` 工具在役；另有 `vision_analyze`（MCP-station / llm-pi-ai 路由）、`describe_image`、`analyze_ui_image`、`read_image` 等多条视觉通道并存。
- **新增价值评分：1 / 5**（已覆盖；唯一增量是最新 3.25.4 的功能增强，与本机 CLD-017/020 缺口无关）
- **安装建议：不装-重复（已安装等效）**；追新升级（3.16.7 → latest 3.25.4）建议等 harness ≥0.1.2 后一并验证。
- **风险**：无新增；多通道并存时需固定"哪条是主视觉通道"以免工具调用漂移。

---

## 5️⃣ shengsheng90/DSH-taskboard — 232★

- **URL**：[github.com/shengsheng90/DSH-taskboard](https://github.com/shengsheng90/DSH-taskboard)（npm `@shengsheng/dsh-taskboard` v0.1.4，Apache-2.0）
- **核心能力**：原生（非 iframe、非第二聊天运行时）**SQLite 任务看板——SQLite 为唯一任务权威**；进程内 `taskboard_*` agent 工具（可提交到 in_review，**无 accept / 无泛化状态变更**）；只有人类 UI/CLI 可 accept→done；CLI `dsh-taskboard` + packaged skill `manage-taskboard`；7 状态流（backlog→todo→in_progress→in_review→done + blocked/canceled）、稳定可读键 DSH-42、乐观版本；Harness Session/Goal/Workspace 仍是执行与对话所有者。
- **与本机已有能力对比**：本机已装 **dsh-task-board（localStorage、浏览器端、5 段 cron 定时执行、随 web-ui-all 0.1.16 一键安装，键 `dsh.taskBoard.v1`）**。SQLite 版三处更优：**跨刷新/跨进程耐久、agent 可经工具真实写任务（可执行闭环）、人审 accept→done 的审计门**；但**无 cron**——localStorage 版的定时执行（0 23 * * *）是其独有优点，迁移即丢。
- **安装方式（偏重）**：lib/ 不入 git → 必须 `pnpm install && pnpm build && pnpm pack`，用产物 tarball 执行 `dsh plugin --profile web add -w <tarball>`；依赖 node:sqlite（node ≥22.19 / 24）——本机 shell 无 node 命令，只能走 CLD 内置 node，需先确认其版本与 pnpm 11。
- **⚠️ 版本墙**：peerDeps **精确钉死 `0.1.2-alpha.2`** 全系（dsh-session/agent/tools/client-ui-* 等）；本机 0.1.1-rc.2 → **当前强装会 peer 冲突/运行错乱**。
- **新增价值评分：3 / 5**（能力上确实优于 localStorage 版，但当下不可装）
- **安装建议：不装-暂缓**（列入 harness 升 ≥0.1.2-alpha.2 后的升级清单；若中途想要"项目内 SQLite 任务文件"，轻量替代 `navid-kianfar/dsh-tasks-manager` 无版本门槛，0★）
- **风险**：版本墙为主；源码构建安装需避免 git-add 裸树（缺 lib/ 会装出无 Host/Client 的空包）；SQLite 任务权威与 dsh 会话/目标体系并存时需约定谁是 task 事实源，防与现有 todo/goal 工作流双写打架。

---

## Top 3 推荐

1. **dsh-context@0.41.x — 装-优先**（评分 5）：CLD-017 最直接的诊断仪表——逐请求看清上下文谁在涨、compaction 何时发生、回收多少，先归因后治理；零构建；唯一条件是**选 0.41.x 而非 latest**（本机 0.1.1-rc.2）。
2. **@graysilver/dsh-evolve-modes@0.4.0 — 可选**（评分 3）：唯一与本机 rc.2 精确兼容的高价值流程插件，质量门禁/组合控制是 R006 外增量；进化维度保持 Propose 即零写入、可与 R006 人审桥接，但防全局规则注入加剧上下文膨胀。
3. **@shengsheng/dsh-taskboard — 暂缓**（评分 3）：SQLite 任务权威 + 人审 done 门确实优于现有 localStorage 看板，值得排期，但被 0.1.2-alpha.2 版本墙挡住，应在 harness 升级后作为首批替换对象。

**一句话总纲**：modlens 已装等效、dsh-memory 与现有知识库三通道重复、taskboard 被版本墙卡住；当下唯一立即可装且直击 CLD-017 的是 **dsh-context@0.41.x（观测）+ 另配 compaction 插件（执行）**，evolve-modes 作为流程增量可选装。

---

## 附：方法说明与信源

- **方法**：web_search 定位仓库 → GitHub README/package.json/cordis.patch.yml 源码分析（cordis 插件形态、peerDeps、engines、dsh.compatibility 清单）→ 本机 `~/.dsh/profiles/web/package.json`（bundles/deps）、`~/.dsh/profiles/node_modules/@deepseek-ai/*`（版本）、`~/.dsh/market/index.json`（4508 条，2026-09-06 扫描，star 数为扫描时值）三方交叉核验。
- **主要信源**：
  - [bowenliang123/dsh-context](https://github.com/bowenliang123/dsh-context) · [compatibility.md](https://github.com/bowenliang123/dsh-context/blob/main/docs/compatibility.md)
  - [joyiok/dsh-memory](https://github.com/joyiok/dsh-memory) · [chenhw7/dsh-memory (Cairn)](https://github.com/chenhw7/dsh-memory)
  - [GraySilver/dsh-evolve-modes](https://github.com/GraySilver/dsh-evolve-modes) · npm [@graysilver/dsh-evolve-modes](https://www.npmjs.com/package/@graysilver/dsh-evolve-modes)
  - [liustack/modlens](https://github.com/liustack/modlens)
  - [shengsheng90/DSH-taskboard](https://github.com/shengsheng90/DSH-taskboard) · npm [@shengsheng/dsh-taskboard](https://www.npmjs.com/package/@shengsheng/dsh-taskboard)
  - 本机：`~/.dsh/profiles/web/package.json`、`~/.dsh/profiles/node_modules/@deepseek-ai/{dsh-base,dsh-session,dsh-agent,dsh-tools,dsh-web-app}/package.json`、`~/.dsh/market/index.json`
