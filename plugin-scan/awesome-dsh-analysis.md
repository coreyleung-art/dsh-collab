# awesome-dsh-plugin 深度分析（20 分类 1247 插件）

来源: https://github.com/awesome-dsh-plugin/awesome-dsh-plugin

## 与本系统高相关候选（按分类）

### UI Enhancements（筛选 3）
- **0xsline/dsh-spotlight** - Keyboard-first command palette for the DSH Web UI.
- **2768651338/dsh-effort-slider** - A Claude Code-style reasoning-effort slider for the DSH Web UI: stepless drag, snap-on-rel
- **a1073097082/dsh-model-search** - Adds searchable filtering to the model selector by provider, model name, and model ID; spa

### Models & Providers（筛选 4）
- **BruceLanLan/dsh-tier-router** - Two-tier model routing: a strong tier plans, advises and reviews while a cheap tier implem
- **btspoony/dsh-llm-fallbacks** - Role-based LLM retry & fallback strategies.
- **dawnliming/dsh-chinese-mode** - Global Simplified-Chinese mode: a 中 switch in the input box that injects language requirem
- **dylan121322/llm-adaptive** - Adaptive model routing: per-request complexity classification with automatic provider rout

### Memory（筛选 4）
- **863683348/dsh-plugin-focus** - Focus board for DeepSeek Harness agents: durable, model-maintained notes in the session wo
- **aerince/dsh-active-context-pruning** - Model-authored context pruning for DeepSeek Harness through the official compaction API.
- **Aik358/dsh-auto-memory** - Cache-friendly three-layer memory for DSH: lean auto injection, per-turn AI consolidation,
- **baaai123/dsh-memory-protocol** - Memory protocol enforcement plugin: bridges the opencode-memory MCP server, forces memory_

### Tools & Capabilities（筛选 4）
- **1na-ko/dsh-hdc-bridge** - HarmonyOS device bridge: hdc screenshot/install/log/crash/UI automation loop with read_ima
- **6Mikao9/dsh-wsl-workspace** - Add a WSL workspace from the web GUI without needing to install dsh or related tools again
- **863683348/dsh-plugin-academic-writing** - Academic writing toolkit for DSH agents: paper outlines, title and abstract skeletons, GB/
- **863683348/dsh-plugin-finance-data** - Finance data toolkit for DSH agents: number and currency formatting (incl. Chinese wan/yi 

### Browser & Web（筛选 12）
- **1624318455/dsh-plugin-tavily** - Tavily-backed web search provider for the built-in web_search tool, with a settings card f
- **2672243194/dsh-read-url** - Read any page as clean main content: charset auto-detect (GBK/GB2312/UTF-8/Big5), noise st
- **anweat/dsh-browser** - Self-contained browser runtime: Playwright (chromium) + OpenCLI as plugin-local dependenci
- **anweat/dsh-web-search-pro** - Persistent enhanced web search: multi-engine routing (DeepSeek/Exa/DDG/Bing/Jina + GitHub/

### Vision & Multimodal（筛选 33）
- **314857493/dsh-vision#vision-route** - Registers a `deepseek-vision` provider route: the Web GUI accepts pasted images and transc
- **314857493/dsh-vision#vision-tool** - Model-facing `vision` tool for DeepSeek Harness: describe and OCR image files by calling t
- **54xkeee/dsh-vision** - Vision for text-only DeepSeek via Doubao Web by default (zero-cost, no API key — drives yo
- **54xkeee/dsh-youreyes** - Vision toolkit for text-only DeepSeek: model-invokable `vision` tool, wrapper adapters for

### Voice & Audio（筛选 5）
- **0nt-one/dsh-voice-input** - Mic button in the composer tool row: Web Speech API speech-to-text (Chrome/Edge), language
- **1624318455/dsh-plugin-tts** - Reads assistant replies aloud via free Edge TTS or your own RVC voice models: read-aloud b
- **MaRi23333/dsh-fish-tts** - Reads assistant replies aloud via Fish Audio API only (bring your own key): per-message re
- **NewDaNew/dsh-voice-input** - Voice input for the web UI: a mic button in the composer that transcribes speech into the 

### Docs & Rendering（筛选 7）
- **AKS1st/dsh-mermaid** - Render Mermaid code fences in DSH Web chat messages as lazy-loaded SVG diagrams with stric
- **baconbao/dsh-mermaid-image-preview** - Preview Mermaid diagrams as images via local rendering in DSH Web when the chat message co
- **bill9109/dsh-101** - Document reading mode for DSH.
- **didclawapp-ai/DSH-Office** - Create, read, and edit PPTX, DOCX, XLSX, and PDF via the local zagens-office CLI as office

### Workflow & Automation（筛选 3）
- **1052326311/dsh-plan-lattice** - Adds persistent execution contracts, recursive work graphs, critical clarification, and ev
- **534119219/chicheng-cron** - Cron scheduler with a sidebar UI: run shell, Python or Node scripts, skills, or agent task
- **akqwpeter-prog/dsh-agent-conductor** - Dispatch self-contained tasks from DSH to 11 external agent CLIs (Codex, Claude Code, Trae

### Git & Code Review（筛选 3）
- **BrambleXu/dsh-revdiff** - Native interactive Git diff review for DeepSeek Harness with structured annotations sent b
- **DamonKoy/dsh-web-ui#dsh-git-graph** - Git branch selector and Git graph in the conversation header of the dsh web GUI.
- **WhitePlusMS/dsh-git-graph** - Dedicated read-only Git Graph view beside Chat and Trajectory: commit topology, local/remo

### Notifications & Integrations（筛选 4）
- **534119219/chicheng-push** - Multi-channel push for DeepSeek Harness: Server酱, PushPlus, Bark, DingTalk, WeCom, Telegra
- **534119219/dsh-messaging** - Unified messaging gateway for DeepSeek Harness: 27 IM platforms (Telegram, QQ, WeChat, Dis
- **AbcdefgXW/dsh-msg-hub** - IM channel bridge: WeChat (ilinkai) / QQ / Feishu with proactive push — wake the channel b
- **JamesYasR/dsh-email-push-master** - Email reminders from your DSH agent when you are away, with stable SMTP (no 535 retry loop

### Development & Runtime（筛选 3）
- **1123762794/dsh-web-restart** - One-click restart button for the DSH Web UI: a sidebar footer button that restarts the dsh
- **863683348/dsh-plugin-verify** - Verification toolkit for DSH agents: evidence-based claim checking against workspace files
- **863683348/dsh-trend-radar** - Ecosystem trend dashboard (行情面板): snapshot the dsh-plugin topic and the awesome list into 

### Security & Permissions（筛选 7）
- **030611/dsh-telemetry-redactor** - Redacts supported secret patterns from the `session-telemetry/record` export copy before c
- **863683348/dsh-gov** - Agent governance suite: policy-based tool gating (allow/deny/ask with wildcards and priori
- **863683348/dsh-plugin-gate** - Installation safety gate for DSH plugins: antivirus-style scan of install scripts, permiss
- **moon09300731/dsh-approval-gate** - Risk-gated approval automation for DeepSeek Harness: flash pre-classifies whether a write/

### Plugin Markets & Managers（筛选 10）
- **1e0zj/dsh-plugin-mall** - Open plugin marketplace: live GitHub dsh-plugin topic search with per-repo package.json ve
- **2768651338/dsh-plugin-manager** - A plugin manager tab in Settings → Plugins: Chinese names and plain-language descriptions 
- **863683348/dsh-feed** - Cross-ecosystem aggregation data layer: syncs the GitHub dsh-plugin topic and the npm regi
- **863683348/dsh-insight** - Plugin insight center: one answer to "哪些值得装" — plugin_guide matches needs to plugins, reci

## 重点推荐 Top 10（高相关 + 高价值）
- [dsh-agent-conductor](Workflow & Automation) - dispatch tasks to 11 external agent CLIs（Codex/Claude）——跨 agent 编排
- [chicheng-cron](Workflow & Automation) - Cron scheduler with sidebar UI——本地定时任务（可替代 launchd 部分场景）
- [dsh-messaging](Notifications & Integrations) - 27 IM 平台统一消息网关（Telegram/QQ/Feishu/WeCom）——外链体系增强
- [dsh-auto-memory](Memory) - 三层缓存记忆（lean 自动注入/AI 整理）——记忆管理增强
- [dsh-web-search-pro](Browser & Web) - 多引擎搜索路由（DeepSeek/Exa/DDG/Bing/Jina）——研究管线增强
- [DSH-Office](Docs & Rendering) - 本地 zagens-office 创建编辑 PPTX/DOCX/XLSX/PDF——文档能力增强
- [dsh-gov](Security & Permissions) - 策略化工具门控（allow/deny/ask + wildcards）——安全治理
- [dsh-plugin-gate](Security & Permissions) - 插件安装安全扫描（antivirus 式扫描安装脚本）——供应链安全
- [dsh-insight](Plugin Markets & Managers) - 插件洞察中心「哪些值得装」——插件评估自动化
- [dsh-feed](Plugin Markets & Managers) - 跨生态聚合数据层（GitHub dsh-plugin 主题同步）——插件扫描数据源增强

## 结论
- 1247 插件 = DSH 生态目录总览（20 类）
- 与已有能力重叠：dsh-market（=本地已装）、modlens（已装）、web-ui-all（已装）
- 高价值候选：dsh-agent-conductor（跨 agent）、chicheng-cron（定时）、DSH-Office（办公文档）、dsh-gov/plugin-gate（安全）
- 安装纪律：README 警告「非安全审查，装前查源码」——装任何新插件前走供应链专员评估