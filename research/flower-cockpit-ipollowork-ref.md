# 花店驾驶舱 · 外部参考调研：iPolloWork（可编辑结果 / 工作台布局 / agent-first 流程）

> 调研日期：2026-08-18 · 调研人：数据调查员（调研子代理）
> 任务背景：花店驾驶舱项目（4 子项：可编辑经营周报 / 促销工作流 / 驾驶舱主页 / 双 agent 回传）需借鉴 iPolloWork 的「可编辑结果 / 工作台布局 / agent-first 流程」。
> 证据策略：官方 GitHub 仓库（README + 源码 + specs + evals）为一手证据；DoNews/tycp.xyz 为二手报道（仅交叉验证）；官方演示视频链接已 404、本机无视觉模型可用，**界面截图不可得，布局/交互结论均基于官方文档与源码结构归纳**（置信度分级：🟢高=官方源码/文档直接证据，🟡中=官方自述+二手交叉，🔴低=单源/待验证）。

---

## 调研结论（iPolloWork 定位 + 可借鉴点 TOP5）

**定位一句话**：iPolloWork 是「本地优先的可视化 AI 工作台」——从一个目标出发，让 agent 直接产出**可继续编辑**的代码、文档、演示稿、网站、设计与视频，是 Codex / Claude Code 的源码可用（source-available）替代品，且正在原生接入 DeepSeek Harness 作为子代理运行时（🟢 官方 README）。

**对花店驾驶舱可借鉴点 TOP5**：

1. **「左对话、右结果、同一处继续编辑」范式**：AI 产出不是聊天文本，而是落在右侧可编辑 artifact（报告/表格/画布）里，改完 agent 可继续跑下一段。→ 直接对应「可编辑经营周报」子项（🟢 官方 README + DoNews 报道交叉）。
2. **可编辑结果的分层实现**：markdown「合并编辑」（所见即所得，语法标记随光标显隐）+ 表格 artifact 的 spreadsheet 编辑器（CSV/TSV/XLSX 双向解析回写）+ 保存状态机（draft/saved/failed/retry/discard）。→ 对应周报的「指标卡+图表位+表格」编辑闭环（🟢 源码 artifacts/ 目录直接证据）。
3. **动作确认门控（permission once/always/reject）**：agent 每类敏感动作弹出审批，用户可选「仅本次/始终允许/拒绝」，审批与提问（question）都回流到同一会话。→ 对应促销工作流的「动作串接+确认门控」（🟢 conversation-engine.ts 类型定义）。
4. **三区工作台布局 + 布局状态持久化**：左侧 sidebar（工作区+会话树）+ 中间会话面（composer + 流式转录 + 实时 todos）+ 右侧 tab 面板（artifact/浏览器/侧栏），宽度与开合状态按工作区持久化。→ 对应驾驶舱主页的「一屏卡片」信息架构（🟢 evals/workspace-layout-state-flows.md）。
5. **brief 模板 + 参考文件注入**：模板带「标题/受众/细节」三字段 brief，可挂载 CSV/JSON/图片/PDF 等参考文件，保存的 prompt 模板进 localStorage、有模板市场。→ 对应促销工作流模板化 + 周报数据（CSV）注入（🟢 templates/ 源码）。

---

## iPolloWork 详析（产品 / GitHub / 核心能力）

### 产品定位
- **一句话**：本地优先（local-first）的可视化 AI 工作台，一个工作空间同时处理代码仓库、本地文件、浏览器任务、文档、演示稿、网站、设计和视频（🟢 官方 README）。
- **差异化主张**（官方「它真正解决的三件事」，🟢）：
  1. **智能体执行**（agent-first execution）— 规划工作、调用工具、读写文件、运行命令，并从当前状态继续推进；
  2. **结果可编辑**（editable results）— 生成之后文字、图片、布局、画面仍能继续修改，不交付「一次性答案」或「黑盒成品」；
  3. **本地可控**（local control）— 自带模型/服务商、逐项批准权限、用 Skills/插件/MCP/浏览器自动化扩展；
  4. **双智能体生态协作** — 原生接入 DeepSeek Harness 子代理（开发中，未进稳定版）：iPolloWork 保持主工作空间，边界明确的任务委派给 DSH 子代理，结构化结果带回同一任务，两边保留各自 Skills/插件生态（🟢）。
- **对外的口号**：成果可见、过程可控、结果可编辑（🟡 DoNews）。

### GitHub 仓库（一手）
- 官方仓库：**https://github.com/Devin-AXIS/iPolloWork**（组织 Devin-AXIS，中国团队）
- 数据（2026-08-18 实测 API）：⭐ 4,105 · fork 784 · TypeScript · 创建 2025-08-25 · 近期活跃（2026-08-17 有推送）· license 标记 NOASSERTION（非 OSI 开源）
- 官方描述：*"A next-generation, source-available AI workspace with a self-evolving agent runtime for editable code, design, presentations, websites, and video—a Codex alternative that integrates DeepSeek Harness for subagent delegation…"*（🟢）
- **许可**：iPolloWork Source Available License 1.0（非 MIT）——个人自用与 <3 人内部小规模使用免费；≥3 人使用、销售/SaaS/白标等需书面授权；前端须保留品牌署名（🟢 README/LICENSE）。⚠️ 二手文章（tycp.xyz）称「MIT 协议」与官方矛盾，**以官方为准，已在噪音排除记录中标注**。
- 传播数据：3 周破 3.9K stars；Trendshift TypeScript 日榜 #22 / 周榜 #24（2026-07-30 起）；DSH 相关 GitHub 社区项目关注度第 2（🟡 DoNews，2026-08-14）。
- 仓库结构（🟢）：`apps/app`（React 19 + Vite UI）/ `apps/desktop`（Electron）/ `apps/server` / `apps/orchestrator`（无头编排 sidecar）/ `packages` / `specs` / `evals`（可执行产品流程）/ `examples` / `external-plugins`。
- 架构边界（🟢）：`desktop/UI → 本地 API → server → OpenCode`（OpenCode 作为独立 sidecar，不 fork 不改写）；可选 iPolloCloud 负责身份/组织/托管 worker/商业 App。

### 核心能力清单
| 能力 | 证据（源码/文档） | 置信度 |
|---|---|---|
| 会话面：流式转录 + composer + 实时 todos | `domains/session/surface/*`、`conversation-engine.ts`（ConversationSnapshot 含 todos/status） | 🟢 |
| 可编辑结果：artifact 面板（markdown/表格/HTML/PDF/图片/文本） | `domains/session/artifacts/*`（artifact-panel、preview、markdown-live-preview、artifact-spreadsheet-editor/model、html-preview-mode） | 🟢 |
| 双会话引擎：OpenCode + DeepSeek Harness 可切换 | `domains/session/engine/*`（conversation-engines、opencode-*、deepseek-harness-*） | 🟢 |
| 审批门控 + 提问回流 | conversation-engine.ts：`permission.asked/replied`、`question.asked/replied`（once/always/reject） | 🟢 |
| 会话模式：execute/plan/code/minimal/create | ConversationModeIcon + DSH `agentPreset.select` | 🟢 |
| 模板 + brief + 参考文件注入（CSV/JSON/PDF/图片） | `domains/session/templates/*`、references/*（brief-autofill、prompt-pack、ingestion） | 🟢 |
| 设计画布（PPT 式在位编辑）+ PPT/PDF 导出 | `domains/session/design/*`（presentation-canvas、design-properties-inspector、pptx-export） | 🟢 |
| 视频工作台（时间轴/配音） | `domains/session/video/*` | 🟢 |
| 浏览器面板 + 浏览器自动化 | evals/workspace-layout-state-flows.md（browser panel） | 🟢 |
| 布局状态持久化（sidebar/面板宽度按工作区） | evals/workspace-layout-state-flows.md（Flow 1-4） | 🟢 |
| 插件平台（Skills/MCP/authorization 隔离） | specs/plugin-platform-architecture.md | 🟢 |

---

## 可编辑结果模式（图 / 表 / 报告如何可编辑，含样例）

> ⚠️ 界面截图不可得（官方 demo 视频附件 404、本机无视觉模型），以下为**官方源码 + evals 文档归纳**，置信度 🟢（结构事实）/ 🟡（交互细节）。

### 模式 1：markdown「合并编辑」——报告/文档类（对应周报正文）
- 实现：CodeMirror 6 的 Obsidian 式 merged 视图——文档始终是**可编辑的纯 markdown**，但标题/加粗/列表/引用/链接**实时内联渲染**；语法符号（`#`、`*`、`` ` ``、`>`、链接括号）只在光标触及该行时显示（🟢 `markdown-live-preview.ts` 源码注释原文）。
- 富内容识别：`findMarkdownCodeBlocks / findMarkdownImages / findMarkdownTables` —— **表格、图片、代码块被结构识别**，可在编辑器内直接改表格与图片引用（🟢 `markdown-rich-content.ts`）。
- 保存交互：面板头部有保存状态机 `unsaved → saving → saved / save_failed（可重试）` + 显式 **Save / Discard changes** 按钮 + 「Edit artifact」切换（🟢 `artifact-panel.tsx`）。
- 样例形态：agent 在转录里生成的 `.md` 报告 → 右侧 artifact 面板打开 → 所见即所得改文字/表格 → 保存回文件。

### 模式 2：spreadsheet 编辑器——表格/数据类（对应周报指标表）
- 解析/序列化：CSV/TSV 走自研 delimited 解析，XLS/XLSX/ODS 走 SheetJS（xlsx），统一归一为 `SpreadsheetRows`（二维字符串数组）后在 **artifact-spreadsheet-editor** 中编辑，保存时**按原格式回写**（CSV/TSV 文本、XLSX 二进制）（🟢 `artifact-spreadsheet-model.ts`）。
- 关键点：**格式无关的表格编辑层** —— 编辑的是归一化网格，落盘回原格式；这是「AI 产出数据表 → 人直接改数字 → 存回」的现成范式。

### 模式 3：HTML 预览 + 设计画布——视觉类（对应图表位/主页卡片）
- HTML artifact：inline stylesheet 注入的 HTML 实时预览 + 独立样式表（🟢 `html-preview-mode.ts`）。
- 设计画布：`presentation-canvas` + `design-properties-inspector`（属性检查器：改文字/换图/调色/字体/布局）+ 设计系统抽屉 + 撤销历史 + PPT/PDF 导出（🟢 design/ 源码）；二手报道归纳为「像 PowerPoint 一样在位编辑，改完 AI 接着跑下一段」（🟡 tycp.xyz）。

### 模式 4：artifact 的收集与呈现
- 转录中的「可收集 artifact 目标」会被 `panel-tab-store` 收集进右侧 artifact 面板（多 tab），按文件类型自动选预览器（markdown/text/sheet/html/pdf/image）（🟢 `artifact-panel.tsx`）。
- 关键设计：**结果既在转录流里，也在可编辑面板里，二者同源** —— 「生成处审阅、面板处编辑」双入口。

---

## 工作台布局参考（驾驶舱布局模式归纳）

> 布局结论基于官方源码目录 + evals（workspace-layout-state-flows / react-session-flows），无截图，置信度 🟢（结构）/ 🟡（视觉细节）。

### 三区布局（会话/任务型工作台）
```
┌──────────┬──────────────────────────────┬──────────────┐
│ Sidebar  │ Session Surface（会话面）      │ Right Panels │
│ 工作区+   │  Composer（输入+Run task）     │  Artifact 面板│
│ 会话树    │  Transcript（流式转录+工具流）  │  （多 tab）   │
│ New task │  Todos（实时任务清单）          │  Browser 面板│
│ 模式/设置 │  权限/提问弹层                 │  side panel  │
└──────────┴──────────────────────────────┴──────────────┘
```
- **Sidebar**：workspace 头部 + 会话列表 + 「New task」入口；新建任务即新会话（🟢 react-session-flows Flow 1）。
- **Session Surface**：composer（文本/文件引用/agent 引用）→ Run task → 流式转录（用户气泡即时出现、助手气泡流式填充）；转录中嵌入工具调用与实时 todos（🟢）。
- **Right Panels**：artifact 面板（结果编辑）、浏览器面板（自动化浏览）等，**带 tab 与可拖拽宽度**。
- **布局持久化**：sidebar 宽度、browser 面板宽度与开合状态**按工作区持久化**，导航/刷新/升级不丢，旧版存储自动迁移（🟢 evals Flow 1-4）。

### 可复用的驾驶舱布局模式（归纳）
1. **「操作入口在左、内容区在中、编辑/详情在右」** 的横向三区；中区一屏承载核心流（对话/数据流），右区承载「结果的可编辑视图」。
2. **布局状态是用户资产**：宽度/开合/迁移都要持久化（花店驾驶舱的卡片宽度、图表位开关同理）。
3. **会话即任务**：一个任务 = 一个会话 = 一段流式记录 + 一组 artifact（对应驾驶舱「一次周报 = 一次任务」）。
4. **同屏双入口**：结果既在流程流中（审阅上下文）又在编辑面板中（精修）——避免「看完再跳走」。

### 同类补充参考（🟡，仅作布局佐证，非主证据）
- **Count.co（Agentic Analytics 平台）**：canvas 协作 + agent 体验，agent 在画布上产出可编辑的图表/表格单元格，人机同画布协作（[官网](https://count.co/product/data-teams)、[canvas & agent 文档](https://learn.count.co/docs/collaborative-experience)）。与 iPolloWork 的「结果可编辑」同思路：**agent 产出的分析件本身就是可编辑资产**，而非一次性输出。
- 可参考其「画布即产物」：驾驶舱主页的每个指标卡/图表位设计为**可独立编辑的资产单元**，而不是渲染死的 HTML。

---

## agent-first 流程参考

> 基于 conversation-engine.ts / deepseek-harness-conversation-engine.ts / templates 源码归纳（🟢 结构事实）。

### 完整流程：prompt → agent → 工作流 → 结果
```
1. 选 agent/模式        ConversationAgent（name/description/mode）+ ConversationMode
                        （execute / plan / code / minimal / create，带图标，可设默认）
2. 组装 prompt          ConversationPromptPart = text | file(mime/url) | agent 引用
                        → 模板化：TemplateBrief（title/audience/details 三字段）
                          + 参考文件挂载（pdf/docx/md/txt/csv/json/图片）
3. 执行（工作流）        agent 规划 → 工具调用 → 读写文件 → 运行命令；
                        快照 ConversationSnapshot（session + messages + todos + status）
                        实时推送到会话面（todos 可见、status busy/idle/retry）
4. 确认门控             permission.asked → 用户回复 once | always | reject
                        （按 kind + resources 逐类授权，可记住选择）
5. 审阅/提问            question.asked（header/question/options/multiple/custom）
                        → 用户作答回流
6. 结果回传             transcript 中的 artifact 目标 → artifact 面板可编辑
                        （markdown/表格/HTML/PDF/图片）→ 保存回文件
                        → 可继续在同一会话下发下一段指令（「从当前状态继续」）
```

### 关键机制（对双 agent 回传最相关）
- **权限与提问是一等公民**：`ConversationPermission{id, sessionId, kind, resources, remember[], receivedAt}`、`ConversationQuestion{questions[]}`——审批不弹窗打断即可，而是作为**会话事件**回流，UI 渲染为可操作卡片（🟢）。
- **会话可分支**：ConversationSession 带 `parentID`，新任务可 fork 自现有会话（🟢）。
- **DSH 子代理回传（🟢 deepseek-harness-conversation-engine.ts）**：
  - 同一会话面可切换引擎（`conversation-engines.ts`），DSH 事件流（`permission.asked/replied`、`question.asked/replied`、tool parts）被**映射成 iPolloWork 统一会话模型**；
  - 工具输入归一化（`read/write/edit/apply_patch` 字段映射）；
  - RPC 桥：`session.create`（fork 新 DSH 会话）、`agentPreset.select`（切 agent 预设，对应模式选择）、`session.selectModel`；
  - 快照投影：`DshHistory{events, hasMore, projections{asOfSeq, values}}`——**结构化结果按序投影回主工作台**。
- 结论：**「主工作台 + 子代理运行时」= 任务委派 → 子代理执行 → 结构化结果（含审批/提问/工具 UI）回传 → 同一工作台继续编辑**。这正是花店驾驶舱「双 agent 回传」要抄的骨架。

---

## 对花店驾驶舱的借鉴清单（对应 4 子项）

### 子项 1：可编辑经营周报（指标卡 + 图表位）
- [ ] 周报正文用 **markdown 合并编辑**（所见即所得，语法标记随光标显隐）——仓库侧已具备 dsh-ui 可编辑能力，可对齐「表格/图片结构识别 + 在位修改」。
- [ ] 指标数据用 **spreadsheet 编辑层**：CSV/JSON 归一化为可编辑网格，保存回原格式——周报指标表允许运营直接改数字再存。
- [ ] 周报即 artifact：**生成处审阅 + 面板处编辑**双入口，保存状态机（draft/saved/failed/retry/discard）照搬。
- [ ] 图表位 = 可独立编辑的资产单元（参考 Count 画布思路），改数据源即时重渲染。

### 子项 2：促销工作流（动作串接 + 确认门控）
- [ ] 工作流 = 一组「动作 + 权限」：每个高险动作（改价/折扣/上下架）发 permission 卡片，用户回复 **once / always / reject**（逐类授权 + 记住选择）。
- [ ] 用 **question 机制**做分支决策（如「满减还是折扣？」选项卡片，支持多选/自定义）。
- [ ] 工作流模板化：**TemplateBrief（标题/受众/细节）+ 参考文件**（商品 CSV、活动日历）→ 一键起新促销任务；保存常用模板（localStorage 上限 24 条可参考）。
- [ ] 实时 **todos** 展示动作执行进度（已接/待审/拒绝），与操作日志联动。

### 子项 3：驾驶舱主页（一屏卡片）
- [ ] 三区布局抽象为驾驶舱版：左=入口/导航（店铺/任务），中=指标卡网格（一屏），右=详情/编辑抽屉（周报 artifact、促销审批流）。
- [ ] **布局状态持久化**：卡片宽度、抽屉开合、面板顺序按工作区存 localStorage，刷新不丢。
- [ ] 会话即任务：每次周报/促销 = 一个会话 = 流式记录 + artifact 组；主页卡片可点击展开对应会话。
- [ ] 同屏双入口：指标卡上既显示当前值（审阅），也直接可编辑（改目标值/改文案）。

### 子项 4：双 agent 回传（数据 → 生成 → 审阅 → 编辑）
- [ ] 骨架照抄 iPolloWork↔DSH：主会话（驾驶舱）委派子 agent（数据分析/文案）→ 子 agent 用工具读业务数据（CSV/JSON）→ **结构化结果按序投影回主会话**（对应 DshHistory projections/asOfSeq）。
- [ ] 审批/提问作为**会话事件回流**而非弹窗打断：驾驶舱内渲染为卡片，审阅完直接进入编辑。
- [ ] 工具输入/输出归一化层：子 agent 的 read/write/edit 结果统一映射为驾驶舱的 artifact 目标，进编辑面板。
- [ ] 会话分支（parentID）：从上一期周报 fork 出本期，保留历史上下文。

---

## 证据来源

| # | 来源 | 类型 | 用途 | 置信度 |
|---|---|---|---|---|
| 1 | [GitHub - Devin-AXIS/iPolloWork（README 英文+中文）](https://github.com/Devin-AXIS/iPolloWork) | 官方一手 | 定位/许可/架构/DSH 集成/安装 | 🟢 |
| 2 | iPolloWork 仓库源码：`apps/app/src/react-app/domains/session/{artifacts,engine,surface,panel,templates,references,design,video,spreadsheets}` | 官方一手 | 可编辑结果/双引擎/审批门控/模板 brief | 🟢 |
| 3 | iPolloWork 仓库 `evals/workspace-layout-state-flows.md`、`evals/react-session-flows.md` | 官方一手 | 工作台三区布局/布局持久化/会话流 | 🟢 |
| 4 | iPolloWork 仓库 `specs/plugin-platform-architecture.md`、`apps/app/src/react-app/ARCHITECTURE.md` | 官方一手 | 插件平台/UI 分层 | 🟢 |
| 5 | GitHub API `repos/Devin-AXIS/iPolloWork`（2026-08-18 实测） | 官方一手 | stars/语言/描述/活跃度 | 🟢 |
| 6 | [DoNews：三周突破3.9K Stars（2026-08-14）](https://www.donews.com/news/detail/4/6671693.html) | 行业媒体 | 传播数据/「左对话右编辑」定位佐证 | 🟡 |
| 7 | [tycp.xyz：iPolloWork 下一代 AI 编程助手（2026-07-14）](https://www.tycp.xyz/2486.html#1) | 自媒体 | 画布编辑/全模态功能归纳 | 🟡（部分事实与官方矛盾，见噪音排除） |
| 8 | [Count.co（产品页/文档）](https://count.co/product/data-teams) · [Collaborative Canvas & Agent Experience](https://learn.count.co/docs/collaborative-experience) | 同类官方 | 同类「结果可编辑」布局佐证 | 🟡 |
| 9 | [Count AI Agent 指南](https://learn.count.co/count-ai-agent/ai-agent-guide) | 同类官方 | 画布内 agent 协作补充 | 🟡 |

### 噪音排除记录
| 被排除/降级项 | 理由 |
|---|---|
| tycp.xyz 称「MIT 协议（个人/内部使用免费）」 | 与官方 LICENSE（iPolloWork Source Available License 1.0，≥3 人需书面授权）**直接矛盾**，以官方为准；该文其余功能描述保留为 🟡 |
| htx.com.ua / htx.com.jm 的「Codex 和 Claude Code 天天被吹」转载文 | 同源转载无独立信息，仅作传播现象记录，未采用 |
| README 中官方 demo 视频附件（github user-attachments 201b561a…） | 实测返回 404，无法作为截图证据；已改为基于文档/源码归纳 |
| 本机视觉通道（vision_analyze / modlens / read_image） | 无 vision provider/无 API key，截图分析不可行——布局结论全部标注为「文档归纳」 |

### 局限与待验证点
1. **无截图/视频证据**：布局与编辑交互的视觉细节（配色、卡片样式、拖拽手感）无法确认，需人工打开产品或后续补截图验证。
2. **DSH 子代理集成未发布**：官方明确「仍在积极开发、未包含在最新稳定版」，双 agent 回传的实现细节以源码为据，产品级稳定性待验证。
3. **中文二手报道时效**：DoNews/tycp.xyz 均为 2026-07~08，数据（stars）以官方 API 实测为准。
4. **Count 等同类仅作补充**，未深挖，如需更细布局参考可单开一轮调研。

---

*报告完 · 数据调查员*
