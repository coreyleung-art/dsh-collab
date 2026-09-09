# 评估报告：dsh 工具/搜索/科研类插件

> 评估人：数据调查员委派子代理 · 日期：2026-09-06
> 评估对象：DeepSeek Harness (dsh) 社区「工具/搜索/视觉/科研」类 6 候选插件
> 方法：web_search + GitHub 源码/README/结构分析 + npm registry 元数据 + GitHub API（star/issue/活跃度）交叉验证 + 本机实测对照

---

## 0. 本机实测基线（mac-mini，DSH 宿主）

| 项 | 实测值 |
|---|---|
| dsh 运行时版本 | **0.1.1-rc.2**（/Applications/CLD.app 内嵌 @deepseek-ai/dsh 0.1.1-rc.2，@deepseek-ai/dsh-tools 0.1.1-rc.2） |
| Node | v25.9.0（✓ ≥22） |
| LaTeX 引擎 | ❌ 未装（无 tectonic/latexmk/pdflatex） |
| 本机 bundle 数 | 32（cordis.patch.yml 层之上，`package.json` → dsh.profile.bundles 实测） |
| 相关已装插件 | `dsh-plugin-research`（web_search→交叉验证→research-fetch→Obsidian→wiki→ChromaDB）、`dsh-knowledge`+`dsh-plugin-knowledge-tools`（embedding=Ollama nomic-embed-text）、`dsh-doc`、`dsh-files`、`dsh-plugin-office`（office_write 生成→dshdoc_extract 解析）、`@liustack/modlens` v3.16.7、`dsh-ui-spec` v0.1.0（截图→前端规格）、**`@omdsh-dev/dsh-genui` v0.8.6**、`dsh-plugin-mcp-station`（vision_analyze→llm-pi-ai/LM Studio）、`dsh-plugin-market`、`dsh-read-url` |
| 数据资产 | papers-db=**203 篇** sqlite（自研 seed/search/embed 脚本）；research 流水线产物落 Obsidian + ChromaDB |
| 搜索 seam 配置 | `searchProvider` 未显式配置 → 默认 `deepseek-official`（dsh 官方原生 web_search） |
| 模型侧 | DeepSeek 官方 + 本地 Ollama（qwen2.5:3b / nomic-embed-text）+ LM Studio（vision_analyze 默认） |
| 本机搜索工具 | web_search（原生 seam）、read_url / dsh-read-url |

⚠️ **一项事实纠偏**：任务描述中候选 5「dsh-genui 未装」不成立——本机 bundle 已含 `@omdsh-dev/dsh-genui v0.8.6`（旧包名旧版），本会话在用的 dsh-ui fence / render_ui / validate_dsh_ui / [genui-action] 即其渲染链路。

---

## 1. modsearch — @liustack/modsearch ★391（MIT）

- **GitHub**：https://github.com/liustack/modsearch（npm `@liustack/modsearch` **5.10.1**；pushed 2026-09-03；**1 open issue**；市场索引快照 347★，GitHub API 实测 391★）
- **形态**：skill + CLI + dsh bundle。`cordis.patch.yml` 把 dsh web seam 的 `searchProvider` 由默认 `deepseek-official` 替换为 `modsearch` 并自注册插件。

### 核心能力
- 搜索/抓取桥：**默认 Firecrawl keyless——1000 免费额度/月，免注册、免 API key、免卡**
- 可选引擎：Tavily（1000 credits/月，免卡）、Exa（$10 循环额度 ≈1400 次）、Antigravity CLI（浏览器登录即可）、Grok Build X 搜索（SuperGrok/X Premium 订阅）、本地抓取
- **多引擎自动 failover + 每引擎多 key 轮换**（鉴权/限流/额度失败先轮 key 再降级引擎）
- 输出**结构化 JSON 证据**（含 uncertainty 字段）；read_page 整页抓取；X/Twitter 语料（web 索引覆盖不到）
- 兼容 dsh/Claude Code/Codex/Pi/OpenCode；dsh 内支持 Settings→Plugins 图形化配引擎

### 与本机已有能力对比
| 维度 | 本机现状 | modsearch 增量 |
|---|---|---|
| web_search | dsh 原生 seam（deepseek-official 单后端） | 免 key 兜底 + 引擎降级链 + X 语料 |
| 抓页 | dsh-read-url / read_url | read_page 并入同引擎链 |
| research-pipeline | 第一步即 web_search | **直插该环**，遇官方限流/故障自动切换 |

### 评分与建议
- **新增价值：5/5**（情报/信源采集直接增强，非重复）
- **安装建议：装-优先**
  ```bash
  dsh plugin --profile web add @liustack/modsearch@5.10.1
  # 重启 dsh web → 会话验证：搜索返回带源链接的结构化结果
  ```
- **风险：低**。依赖 Firecrawl keyless 网络可达性（README 注明 Steam++/Watt Toolkit/VPN 类代理可能触发私网屏蔽报错）；额度按月重置；回滚简单（移除 patch 行 / `searchProvider` 改回 `deepseek-official`）。作者 liustack = **本机已装 modlens(3713★) 同作者**，信任背书强。

---

## 2. dsh-genui ★409（MIT）—— ⚠️ 已装等效，只需迁移升级

- **GitHub**：https://github.com/omdsh-dev/dsh-genui（npm **`@changfenhuang/dsh-genui`** **0.9.8**；★409；7 open issues；pushed 2026-09-06）
- **包名变更**：v0.9.2 起仓库声明包名由 `@omdsh-dev/dsh-genui` 迁至 `@changfenhuang/dsh-genui`

### 核心能力
- dsh-ui fence 交互组件：布局/表格/图表/plot/表单/测验/mermaid/3D/文件树等白名单组件，**内联渲染进模型回复**
- action 事件回环（组件交互回传模型重渲染）；会话面板 dock；跨刷新持久化；本地判分/重置零往返
- 双通道渲染（registry / DOM），streaming 渲染（≥0.7.2 组件边写边出）

### 与本机已有能力对比（关键）
| 维度 | 实测 |
|---|---|
| 安装状态 | **已装** `@omdsh-dev/dsh-genui v0.8.6`（bundle 列表实测） |
| 功能等效性 | **100% 等效并已在用**——本会话 dsh-ui fence / render_ui 即其能力 |
| 缺口 | 旧包名旧版：官方 README 明示旧键下重装会报 `Cannot find package '@changfenhuang/dsh-genui'`；0.8.6→0.9.8 有 streaming/多 surface fence 发现增强 |

### 评分与建议
- **新增价值：无需新装（已等效）**；行动项 = **必做迁移升级**
  ```bash
  dsh plugin --profile web remove @omdsh-dev/dsh-genui
  dsh plugin --profile web add @changfenhuang/dsh-genui    # → 0.9.8
  # 重启 dsh + 浏览器硬刷新，控制台应见：
  #   [genui] client active; fence-channel=registry|dom
  ```
- **风险：低**；迁移属预防性维护（防将来某次 pnpm 重装即坏）。

---

## 3. dsh-univer-office（dream-num）★276（Apache-2.0）

- **GitHub**：https://github.com/dream-num/dsh-univer-office（npm `dsh-univer-office` **0.2.14**；2 open issues；pushed 2026-09-05）
- **版本兼容：✅ 官方 README 明示支持 dsh 0.1.1-rc.2 与 0.1.2-rc.1 → 本机版本精确命中**

### 核心能力
- 真实 office 运行时（Univer）：Sheet/Doc/Slide/Base/Board 多类型**组合进同一 .univer 文件**，公式可跨内容引用
- agent 自然语言建/改：电子表格（公式/图表/透视/筛选/条件格式/校验/sparklines）、文档排版、PPT（版式 lint/越界检测）、轻量数据库 Base、可编辑画布 Board
- **会话内审阅流**：隔离草稿 → live preview → approve/discard → 与 trunk 语义 compare（逐 Sheet/Doc/Slide diff）
- 双向导入导出：`.xlsx/.csv/.tsv/.docx/.pptx`（Base/Board 结构性校验，Board 暂不可导出文件）

### 与本机已有能力对比
| 维度 | dsh-plugin-office（已装 0.1.0） | dsh-univer-office |
|---|---|---|
| 层级 | 轻量文件生成（office_write→dshdoc_extract 闭环） | **交互式可编辑可审阅 office 环境** |
| 交付 | 生成即交付 | 会话内可视化编辑→审阅→导出 .xlsx/.docx |
| 场景增益 | 已有 | 信源清单/数据表/LBS 数据源库/周报交付质量跃升 |

### 评分与建议
- **新增价值：4/5**
- **安装建议：可选-推荐**（有数据表/文档交付需求即装）
  ```bash
  dsh plugin --profile web add dsh-univer-office
  # DSH 运行中安装后当前进程不会自动加载 → 重启 dsh → Cmd+R 刷新页面
  ```
- **风险：中**。重依赖（@univerjs-pro 资产 + libsql + puppeteer-core，可能需浏览器运行时做截图/PDF 打印）；体积与启动开销；与现有 office 工具职能重叠但工具名不冲突，可并存观察。

---

## 4. Mimir — dsh-mimir ★208（MIT）

- **GitHub**：https://github.com/1692775560/dsh-Mimir-Academic-research（npm `dsh-mimir` latest **0.18.1**；8 open issues；pushed 2026-09-06；市场索引名 mimir-monorepo）
- **版本兼容：⚠️ 0.18.x 要求 dsh ≥0.1.2-alpha.4（上游 breaking）；本机 0.1.1-rc.2 → 必须 pin `dsh-mimir@0.16.0`**（因而缺失 Venues 视图与 SSE 实时刷新）

### 核心能力（9 视图工作台）
- **Paper**：Overleaf 式 LaTeX 论文工作台——边写边编译 → PDF 预览，一键 AI 修复
- **Library**：arXiv + web 搜索、AI 相关性打分、全屏 PDF 阅读器
- **Experiments**：实验指标图表、一键生成论文图；**Figures**：图片上传/组织/插入论文
- **Meetings**：一键组会 PPT（真实论文图 + 可选 AI 插图）
- **Servers**：GPU 集群探测 + 远程任务编排（server_list/check/submit_job/list_jobs）
- **Ledger**：人性化科研日志（想法演化 worktree 自动捕捉、六视角摘要胶囊、一键进度报告）
- **Venues**（0.18+）：CCF 会议截稿倒计时（ccfddl 目录）+ CCF-A 期刊目录
- 自带 11 个科研 skill（文献综述/新颖性检查/实验规划/引文审计/双语去 AI 味润色/rebuttal…）
- 数据：wiki 存 `~/.dsh/storages/research_wiki.json`；产物落 `./.research`；web 搜索需自建 SearXNG（sxng）

### 与本机已有能力对比
| 维度 | 本机现状 | Mimir 增量 | 备注 |
|---|---|---|---|
| 论文库 | papers-db 203 篇 sqlite（自研脚本） | arXiv 整合检索+相关性打分+PDF 阅读 | 存储范式不同 |
| 知识/wiki | Obsidian raw→wiki→ChromaDB | research_wiki.json（**第二套 wiki 双轨**） | 需人工归口 |
| GPU 编排 | dsh-ssh（cluster/exec/tunnel） | server_* 工具 | 重叠 |
| LaTeX | ❌ 无引擎 | 边写边编译 | 需 `brew install tectonic` |
| web 搜索 | 原生 seam | 需另起 SearXNG | 新增依赖 |

### 评分与建议
- **新增价值：3/5**（数据调查员「论文落链」受益有限；除非向学术写作/LaTeX 演进）
- **安装建议：可选（条件性）**——确定走论文写作方向才装：
  ```bash
  dsh plugin --profile web add dsh-mimir@0.16.0   # 本机 dsh 0.1.1-rc.2 必须 pin
  brew install tectonic                            # LaTeX 编译引擎
  ```
  否则维持现状，等 dsh 升级到 ≥0.1.2-alpha.4 再上 0.18.x（解锁 Venues/SSE）。
- **风险：中**。重插件（9 视图）；版本 pin 锁死功能；LaTeX 依赖缺失；wiki 双轨需人工归口；web 搜索需另起 SearXNG 服务。

---

## 5. dsh-vision-toolkit（@anionex/dsh-vision-toolkit）★854（MIT）

- **GitHub**：https://github.com/Anionex/dsh-vision-toolkit（npm `@anionex/dsh-vision-toolkit` **0.1.40**；6 open issues；pushed 2026-09-04；GitHub API 实测 854★）
- 说明：同名「dsh-vision」系生态中另有多个低星变体（joyiok/liuweifly/MoneShadow 等），本报告以 ★850+ 主力 Anionex 实现为准

### 核心能力
- 为纯文本模型设计的视觉工具箱：**粘贴图片直问**（DSH Web 粘贴图自动切换 (Vision Toolkit) 变体，transparent routing 可关）、多图问答
- **长截图/长页面分块 OCR**（低内容条带检测→逐段 OCR→合并重叠→标注可疑边界）
- grounding 定位/裁剪/pixel-diff/Artifacts 预览；**截图或草图→前端 UI 还原（HTML）**
- 配套 vision-skills playbook（教 agent 何时 inspect/ground/OCR/crop/trace/compare）
- 默认视觉模型 Gemini 3.7 Flash，Settings→Vision Toolkit 可配自有 provider

### 与本机已有能力对比
| 维度 | 本机现状 | vision-toolkit 增量 |
|---|---|---|
| 读图 | vision_analyze（LM Studio）+ **modlens v3.16.7 已装** + describe_image | 多图问答、变体自动路由 |
| UI 还原 | dsh-ui-spec v0.1.0 已装（截图→前端规格） | **重叠**（sketch→HTML） |
| 长截图 OCR | 无系统化方案 | 分块 OCR 方法论 + grounding/裁剪/diff |

### 评分与建议
- **新增价值：3/5**（截图取证、长页面/聊天记录 OCR 对情报采集有真实价值；UI 还原与 dsh-ui-spec 重叠无增量）
- **安装建议：可选**——不急于装；出现「长截图逐段 OCR / 带框定位 / UI 还原」硬需求再装（provider 可指向现有 LM Studio/Ollama，无需新 key）：
  ```bash
  dsh plugin --profile web add @anionex/dsh-vision-toolkit
  ```
- **风险：中低**。0.1.x 较新迭代快；变体路由侵入模型选择器（可关）；默认外部 Gemini key 依赖（可换自配）。

---

## 6. dsh-plugin-subscriptions（V1ki）★328（MIT）

- **GitHub**：https://github.com/V1ki/dsh-plugin-subscriptions（npm `dsh-plugin-subscriptions` **0.7.1**；**10 open issues（候选最多）**；pushed 2026-09-06）

### 核心能力
- 用 ChatGPT(Codex)/Claude/Grok(X Premium)/GitHub Copilot **订阅账户 OAuth 作为 dsh LLM provider，免 API key**（Settings→Subscriptions 登录）
- live 模型目录（含 reasoning effort 选择器）、订阅用量卡片（5h 窗口/周窗口/每模型周配额 + 进度条 + 重置时间）
- Claude 凭据可导入已有 Claude Code 会话（macOS Keychain / ~/.claude/.credentials.json）
- 附带工具：`x_search`（Grok X 搜索）、`image_generate`（gpt-image-2 / grok-imagine）、`video_generate`（grok-imagine-video-1.5）
- tokens 存 `~/.dsh/plugins/subscriptions/auth.json`（mode 0600）自动刷新

### 与本机已有能力对比
| 维度 | 本机现状 | 插件增量 |
|---|---|---|
| 模型侧 | DeepSeek 官方 + 本地 LM Studio/Ollama（自洽） | 白用闭源订阅模型（交叉验证/润色） |
| 价值评估 | 数据调查员属低频需求 | 边际价值有限 |

### 评分与建议
- **新增价值：2/5**
- **安装建议：不装**（除非明确持有上述订阅并接受灰区；届时优先观望同类中维护更稳的实现——生态内 10+ 竞品：subhub/codex-oauth/grok-build/randomix777 等）
- **风险：高-中（R006 合规视角扣分项）**
  1. 调用后端为**逆向/非官方端点**（chatgpt.com/backend-api、cli-chat-proxy.grok.com、api.anthropic.com/api/oauth、api.githubcopilot.com/models）——厂商策略一变即坏（10 open issues 佐证维护压力）
  2. **消费订阅跑 agentic/API 自动化调用在多家 ToS 属灰区，存在封号风险**
  3. OAuth/device flow 为第三方实现，凭据面扩大——本机存在 `~/.claude` 目录，若含 Claude Code 凭据会被该类插件导入，安装前须厘清授权边界
  4. 单作者维护、生态内卷，长期可用性存疑

---

## 7. 汇总对比

| 候选 | ★ | 版本兼容(0.1.1-rc.2) | 与本机重叠 | 新增价值 | 建议 |
|---|---|---|---|---|---|
| modsearch | 391 | ✅ patch 形态 | 低（增强 web_search） | **5/5** | **装-优先** |
| dsh-genui | 409 | ✅ 已装 0.8.6 | 100%（等效） | — | **不装；迁移升级到 0.9.8** |
| dsh-univer-office | 276 | ✅ 官方支持 | 中（dsh-plugin-office） | **4/5** | **可选-推荐** |
| Mimir | 208 | ⚠️ 需 pin 0.16.0 | 中高（research 栈/SSH） | 3/5 | 可选（学术写作才装） |
| dsh-vision-toolkit | 854 | ✅ | 高（modlens/ui-spec） | 3/5 | 可选（取证场景再装） |
| dsh-plugin-subscriptions | 328 | ✅ | 低 | 2/5 | **不装（合规/稳定性风险）** |

## 8. Top 3 推荐

1. **modsearch** — 免费多引擎搜索 failover 直插调研流水线首环，作者与已装 modlens 同源可信，一行安装可回滚（价值最高、风险最低）。
2. **dsh-genui 包名迁移升级**（0.8.6@`@omdsh-dev` → 0.9.8@`@changfenhuang`）— 不是新装而是修隐患：旧键下任何一次重装即失败，迁移顺带拿到 streaming/多 surface 渲染。
3. **dsh-univer-office** — dsh 版本精确匹配、会话内可视化编辑→审阅→.xlsx/.docx 交付，让数据表/信源清单/LBS 数据源库的交付质量跃升（重依赖，装前评估磁盘/启动开销）。

## 9. 安装顺序建议（执行清单）

```bash
# ① modsearch（装-优先，重启后生效）
dsh plugin --profile web add @liustack/modsearch@5.10.1

# ② dsh-genui 迁移升级（必做，防将来重装即坏）
dsh plugin --profile web remove @omdsh-dev/dsh-genui
dsh plugin --profile web add @changfenhuang/dsh-genui        # → 0.9.8

# ③ dsh-univer-office（可选-推荐，有数据表/报告交付需求时）
dsh plugin --profile web add dsh-univer-office

# 每步完成后：重启 dsh → 浏览器 Cmd+R 硬刷新
# 验证：① 会话搜索返回带源结构化结果；② 控制台 [genui] client active; fence-channel=registry|dom
```

**附带建议**：若随后 dsh 升级到 ≥0.1.2-alpha.4，Mimir 0.18 与 univer 新特性将全部解锁，届时应重评 Mimir（Venues/SSE）。

---
*报告基于 2026-09-06 本地实测与 GitHub/npm 实时数据；star 数随市场快照波动（如 modsearch 市场索引 347★ vs GitHub API 391★）。*
