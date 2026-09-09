# 图形化表达工具与插件生态调研（2026）

> 范围：架构图 / 流程图 / 泳道图 / 时序图 / 状态图 / 甘特图 / BPMN / UML / C4 / UXUI 表达图 / ASCII 图 / SVG 生成
> 调研方式：web_search 多角度检索（12 次）+ 官网 URL 实测验证 + arXiv 交叉验证
> 产出日期：2026-08-30 ｜ 归属：数据调查员调研子代理 → dsh-collab 研究库

---

## 结论（推荐工具栈：按场景）

**一句话推荐默认栈**：`Mermaid（文档内嵌）+ PlantUML（UML 全家族）+ Structurizr DSL（C4 架构）+ D2（云拓扑）+ Graphviz（自动布局）+ Kroki（统一渲染网关）+ TikZ/Typst（学术出版）+ Penpot（开源 UI 设计）` —— 全部开源、可本地部署、均为「文本 as code」或可自托管，对 LLM/Agent 生成最友好。

| 场景 | 首选 | 备选/说明 |
|---|---|---|
| Markdown/README/PR/知识库内嵌图（架构、流程、泳道、时序、状态、甘特、饼图、脑图） | **Mermaid**（MIT，文本 DSL，GitHub/GitLab/Obsidian/VS Code 原生渲染，LLM 生成最成熟） | PlantUML（UML 子集更全但渲染需服务端） |
| UML 软件建模（类图/用例/组件/部署/时序/活动） | **PlantUML**（UML 覆盖最全） | Mermaid（class/sequence 子集）；C4-PlantUML 桥接 |
| C4 软件架构文档（Context→Container→Component→Code） | **Structurizr DSL**（模型 as code，一模型多视图，C4 作者官方实现） | C4-PlantUML / Mermaid C4 图 |
| 云拓扑/网络架构图（AWS/Azure/GCP/K8s） | **D2**（声明式、主题美、sketch 手绘模式）或 **diagrams.py**（云图标最全） | Graphviz（复杂布局兜底） |
| 依赖图/层级树/大图自动布局 | **Graphviz/DOT**（dot/neato/sfdp 布局引擎最强） | Mermaid flowchart |
| 业务流程建模（BPMN 2.0 标准、可执行） | **bpmn-js / Camunda Modeler** | PlantUML activity（轻量） |
| 学术出版（论文插图、数学标注） | **TikZ/PGF**（LaTeX 生态成熟）｜新项目 **Typst + Cetz**（更快、编译秒级） | — |
| 低保真 wireframe / 产品原型 | **Balsamiq**（商业，手绘低保真标杆）｜免费 **Excalidraw**（手绘风） | Penpot（开源设计平台） |
| UI 设计与团队协作 | **Figma**（商业 freemium）｜开源替代 **Penpot**（MPL-2.0，可自托管） | — |
| 终端/PR/ADR 内 ASCII 层级图 | **tools-visual-ascii-arch 技能**（本机已装，cc-visualization-skills 包）+ **ASCIIFlow** 在线 | ASCII→真图：**ditaa** / **goat** |
| 程序化/批量生成 SVG | **svg.js**（JS）/ **svgwrite**（Python）；HTML/SVG→PNG 截图用 **Puppeteer** | — |
| 统一渲染网关（CI/文档系统一次接入多种 DSL） | **Kroki**（Docker 自托管，聚合 mermaid/plantuml/graphviz/bpmn/d2/excalidraw 等 20+） | — |
| 通用交互式白板（手工绘制、团队协作） | **draw.io/diagrams.net**（Apache-2.0，.drawio XML 可版本管理） | Excalidraw（手绘风） |
| LLM/Agent 自动生成图（研发侧） | 优先文本 DSL（Mermaid/PlantUML/D2/Structurizr），配 Kroki 渲染；benchmark 见论文清单（MermaidSeqBench、DiagrammerGPT、Text2Arch 等） | — |

**关键判断**：
1. 「文本 as code」是 2024–2026 年主流趋势——所有头部工具（Mermaid/PlantUML/D2/Structurizr/Graphviz）都是 DSL，天然适合 LLM 生成与版本管理；GUI 白板（draw.io/Excalidraw）定位为人工精修层。
2. 本机生态已内置可视化技能包（tools-mermaid、tools-visual-ascii-arch、C4 模型技能、architecture-canvas、walkthrough），与上面推荐栈高度重合，优先复用。
3. 学术侧两条新线：**Typst 替代 LaTeX 绘图**（MIT，比 TikZ 学习曲线低）与 **LLM 图生成评测基准**（MermaidSeqBench、FlowLearn、ChartArena），值得持续跟踪。

---

## 工具矩阵表（工具/能力/安装/许可/场景）

| 工具 | 能力 | 安装方式 | 许可 | 适用场景 |
|---|---|---|---|---|
| **Mermaid** | 文本→图：flowchart/sequence/class/state/ER/gantt/pie/journey/timeline/mindmap/C4/requirement/packet/block | npm `@mermaid-js/mermaid-cli`(mmdc)、CDN、VS Code 扩展、mermaid.live；GitHub/GitLab/Obsidian 原生 | MIT | Markdown 文档内嵌图、README/PR、知识库（本机 Wiki 规则指定 Mermaid） |
| **PlantUML** | 文本→UML 全家族：sequence/class/activity/state/usecase/component/deployment/timing + wireframe(salt)/gantt/mindmap/wbs | jar（需 Java）、Docker `plantuml/plantuml-server`、VS Code 扩展、在线编辑器 | GPL v3（含分发例外） | UML 软件建模、C4-PlantUML、服务端批量渲染 |
| **Graphviz/DOT** | dot/neato/fdp/sfdp/twopi/circo 布局引擎；有向/无向图、层级树、集群 | `brew install graphviz`、apt、pip `graphviz`、Docker | EPL-1.0 | 依赖图、拓扑、层级结构、大图自动布局 |
| **Kroki** | 聚合渲染 API：mermaid+plantuml+graphviz+bpmn+excalidraw+d2+ditaa+blockdiag 等 20+ 格式 | Docker `yuzutech/kroki`、kroki.io 在线 | Apache-2.0 | 文档系统/CI 统一渲染多种 DSL、内网自托管 |
| **draw.io / diagrams.net** | 通用白板：流程图/架构/泳道/网络/ER；.drawio XML 文件；VS Code 扩展；桌面+web | 桌面 app（macOS/Win/Linux）、VS Code 扩展、web | Apache-2.0 | 人工绘制通用图、团队协作、mxGraph 生态 |
| **Excalidraw** | 手绘风白板；JSON 存储；实时协作；支持 Mermaid→Excalidraw 转换（mermaid-to-excalidraw CLI） | web、npm 包、VS Code 扩展、Docker 自托管 | MIT | 快速草图、手绘风示意、白板协作 |
| **BPMN（bpmn-js / Camunda Modeler）** | BPMN 2.0 标准流程建模/查看；bpmn-js 可嵌入 web；Modeler 桌面可视化建模 | npm `bpmn-js`、Camunda Modeler 桌面 | bpmn-js: MIT；Modeler: 免费（Camunda 许可） | 业务流程建模、流程自动化、BPMN 标准合规 |
| **Typst（+Cetz）** | 现代排版系统；内置绘图 + Cetz 包（声明式绘图，Tantivy 风格）；编译秒级 | `brew install typst`、typst.app 在线 | Typst: Apache-2.0；Cetz: MIT | 学术文档插图、替代 LaTeX、快速出版 |
| **TikZ/PGF** | LaTeX 声明式绘图宏包；精确坐标、数学标注、重复结构 | TeX Live / MacTeX（随 LaTeX） | LPPL | 学术论文精确插图、数学/物理图形 |
| **Balsamiq** | 低保真手绘风 wireframe；拖拽组件库 | 桌面/web（商业订阅） | 商业专有 | 产品原型低保真线框图 |
| **Penpot** | 开源设计+原型平台（Figma 替代）；wireframe/设计系统/CSS Grid/Flex；可自托管 | Docker 自托管、penpot.app 云 | MPL-2.0 | UI 设计、wireframe、开源团队协作、设计系统 |
| **Figma** | UI 设计/原型/协作/设计系统 | 桌面/web（freemium） | 商业专有 | 团队 UI 设计（非开源场景） |
| **ASCII 架构图** | 层级 ASCII 图：tools-visual-ascii-arch 技能（本机已装）、ASCIIFlow 在线、ditaa/goat ASCII→SVG | 技能本地安装；ASCIIFlow web；`brew install ditaa`（或 Go 版 goat） | 技能: 社区包；ASCIIFlow: 免费 web；ditaa: GPL；goat: MIT | 终端/PR/ADR/注释内层级图 |
| **D2** | 声明式文本→图；专注架构/云拓扑；主题系统 + sketch 手绘模式 | `brew install d2`、二进制、Docker | MPL-2.0 | 架构图/云拓扑 as code、版本控制友好 |
| **Structurizr DSL** | C4 模型 as code：一个 DSL 模型生成多张架构图；Structurizr Lite 本地渲染 | jar/CLI、Docker `structurizr/lite` | Apache-2.0 | C4 软件架构文档、架构决策记录 |
| **diagrams (Python)** | Python 代码画云架构图；AWS/Azure/GCP/K8s/阿里云图标库 | `pip install diagrams` | Apache-2.0 | 云架构原型 as code、CI 渲染 |
| **SVG 生成** | svg.js（JS 操作 SVG）、svgwrite（Python）、Puppeteer（headless Chrome 渲染 HTML/SVG→PNG） | npm `@svgdotjs/svg.js`、pip `svgwrite`、npm `puppeteer` | svg.js: MIT；svgwrite: MIT；Puppeteer: Apache-2.0 | 程序化矢量图、图表导出、截图渲染 |
| **BlockDiag** | Python 文本 DSL：block/seqn/actdiag/nwdiag（网络图/时序/活动） | pip `blockdiag` | Apache-2.0 | 网络拓扑/时序/活动图 as code（轻量） |

---

## 论文清单（arXiv ID/标题/方向）

验证标注：✅=本轮检索直接出现（HF/alphaXiv/ar5iv/官方列表）｜经典=领域公认基线论文

### A. 文本/自然语言 → 图生成（diagram generation）

| arXiv ID | 标题 | 方向/要点 |
|---|---|---|
| 2310.12128 ✅ | DiagrammerGPT: Generating Open-Domain, Open-Platform Diagrams via LLM Planning | LLM 规划+布局生成开放域图表；配套 AI2D-Caption 数据集 |
| 2508.15222 ✅ | See it. Say it. Sorted: Agentic System for Compositional Diagram Generation | 组合式图生成的 agentic 多步系统 |
| 2604.09568 ✅ | EvoDiagram: Agentic Editable Diagram Creation via Design Expertise Evolution | 可编辑图创建的 agentic 设计经验演化 |
| 2604.14941 ✅ | Text2Arch: A Dataset for Generating Scientific Architecture Diagrams from NL | 科学架构图生成数据集（文本→架构图） |
| 2604.23816 ✅ | Query2Diagram: Answering Developer Queries with UML Diagrams | 开发者自然语言查询→UML 图 |
| 2411.11916 ✅ | From Words to Structured Visuals: A Benchmark and Framework for Text-to-Diagram Generation and Editing | 文本→图生成+编辑 benchmark 与框架 |
| 2511.14967 ✅ | MermaidSeqBench: An Evaluation Benchmark for LLM-to-Mermaid Sequence Diagram Generation | **LLM→Mermaid 时序图生成评估基准**（NeurIPS 2025） |
| 2512.02170 ✅ | Flowchart2Mermaid: VLM Powered System for Converting Flowcharts into Editable Diagram Code | 流程图→Mermaid 可编辑代码（VLM） |
| 2407.05183 ✅ | FlowLearn: Evaluating Large Vision-Language Models on Flowchart Understanding | LVLM 流程图理解评估（含代码化表达） |
| 2311.01920 ✅ | Leveraging LLMs to Generate Charts from Abstract Natural Language | LLM 从抽象自然语言生成图表 |
| 2608.08964 ✅ | Math-Vision Diagrams: A Benchmark for Evaluating LLM Mathematical Diagram Generation | LLM 数学图生成评测 |
| 2512.12063 ✅ | Instruction-Tuning Open-Weight Language Models for BPMN Model Generation | 微调开源模型生成 BPMN 模型 |
| 2509.24592 ✅ | BPMN Assistant: An LLM-Based Approach to Business Process Modeling | LLM 业务流程建模助手 |
| 2605.24546 ✅ | Beyond Control-Flow: Resource Perspective in Multi-Collaborative Process Modeling from Text | 文本→多协作流程建模（含资源视角） |
| 2507.11356 ✅ | What is the Best Process Model Representation? Comparative Analysis for Process Modeling with LLMs | LLM 流程建模表示形式对比（BPMN 等） |

### B. 图/图表理解与视觉语言（diagram comprehension / visual language）

| arXiv ID | 标题 | 方向/要点 |
|---|---|---|
| 1603.07396 ✅ | A Diagram Is Worth A Dozen Images: Diagram Classification with Digitizing and Feature Engineering | **AI2D 科学图理解经典基准** |
| 2403.12027 ✅ | From Pixels to Insights: A Survey on Automatic Chart Understanding in the Era of Large Foundation Models | 大模型时代图表理解综述（必读） |
| 2410.00193 ✅ | Do Vision-Language Models Really Understand Visual Language? | VLM 视觉语言真实理解力评测 |
| 2602.23589 ✅ | Pseudo Contrastive Learning for Diagram Comprehension in Multimodal Models | 图理解的伪对比学习方法 |
| 2109.02762 经典 | Chart2Text: Generating Natural Language Explanations for Charts by Adapting the Transformer (INLG 2020) | 图表→文本（图表摘要，diagram2text 方向源头） |
| 2203.06486 ✅ | Chart-to-Text: A Large-Scale Benchmark for Chart Summarization | 图表摘要大规模基准 |
| 2606.01348 ✅ | ChartArena: Benchmarking Chart Parsing across Languages, Scenarios, and Formats | **图表解析基准（含 SVG/PlantUML 多格式）** |
| 2605.15677 ✅ | VCG-Bench: Towards A Unified Visual-Centric Benchmark for Structured Generation and Editing | 结构化生成/编辑统一基准 |
| 2203.10244 经典 | ChartQA: A Benchmark for Question Answering about Charts | 图表问答基准 |

### C. UML / 软件工程图生成

| arXiv ID | 标题 | 方向/要点 |
|---|---|---|
| 2204.00932 ✅ | Automatic Transformation of Natural to Unified Modeling Language: A Systematic Review | NL→UML 系统综述 |
| 2404.17739 ✅ | How LLMs Aid in UML Modeling: An Exploratory Study with Novice Analysts | LLM 辅助 UML 建模实证 |
| 2607.26100 ✅ | Large Language Models for Software Engineering Diagrams: A Systematic Review of UML and ER Modelling | **LLM 软件工程图（UML/ER）系统综述** |
| （IEEE 9464433） | Generating UML Class Diagram from Natural Language Requirements: A Survey（IEEE 2021） | NL 需求→UML 类图方法综述（非 arXiv） |

### D. UI/UX → 代码与可视化生成（UI-to-code / wireframe）

| arXiv ID | 标题 | 方向/要点 |
|---|---|---|
| 1705.07962 经典 | pix2code: Generating Code from a Graphical User Interface Screenshot | **UI 截图→代码鼻祖** |
| 2210.03347 ✅ | pix2struct: Screenshot Parsing as Pretraining for Visual Language Understanding | 截图解析预训练（Web 截图→结构化理解） |
| 2403.03163 ✅ | Design2Code: How Far Are We From Automating Front-End Engineering? | 截图→前端代码基准（斯坦福/微软） |
| 1905.13750 ✅ | sketch2code: Generating a website from a paper mockup | 纸质 mockup→网站（wireframe-to-code） |
| 2211.14607 ✅ | Sketch2FullStack: Generating Skeleton Code of Full Stack Website from Sketch | 草图→全栈骨架代码 |
| 2506.10376 ✅ | LayoutCoder: MLLM-Based UI2Code Automation Guided by UI Layout Information | UI 布局信息引导的 UI2Code |
| 2604.13648 ✅ | Figma2Code: Automating Multimodal Design to Code in the Wild | Figma 设计→代码（真实场景多模态） |
| 2303.02927 ✅ | LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using LLMs | **LLM 自动可视化/信息图生成工具**（微软） |
| 2403.03346 ✅ | Screen Parsing（原 Screen Parsing 目标论文） | 屏幕结构解析 |

---

## 技术文档源（官方 URL，✅=本轮实测可达）

**文本 DSL 类**
- Mermaid 文档：https://mermaid.js.org/ ✅ ｜ Live 编辑器：https://mermaid.live/ ｜ mermaid-cli：https://github.com/mermaid-js/mermaid-cli
- PlantUML 文档：https://plantuml.com/ ✅ ｜ 服务端：https://github.com/plantuml/plantuml-server ｜ C4-PlantUML：https://github.com/plantuml-stdlib/C4-PlantUML
- Graphviz 文档：https://graphviz.org/
- D2 文档：https://d2lang.com/ ✅（含教程/主题/sketch 模式）
- Structurizr：https://structurizr.com/ ✅ ｜ DSL 仓库：https://github.com/structurizr/dsl ｜ C4 模型官方：https://c4model.com/
- diagrams.py：https://diagrams.mingrammer.com/ ✅ ｜ BlockDiag：https://blockdiag.com/

**聚合渲染**
- Kroki：https://kroki.io/ ✅（自托管 Docker：yuzutech/kroki）

**白板/设计类**
- draw.io：https://www.drawio.com/ ✅ ｜ 源码：https://github.com/jgraph/drawio
- Excalidraw：https://excalidraw.com/ ✅ ｜ 源码：https://github.com/excalidraw/excalidraw ｜ Mermaid→Excalidraw：https://github.com/excalidraw/mermaid-to-excalidraw
- Penpot：https://penpot.app/ ✅ ｜ 帮助：https://help.penpot.app/
- Balsamiq：https://balsamiq.com/ ｜ Figma：https://www.figma.com/

**流程建模**
- bpmn-js：https://bpmn.io/toolkit/bpmn-js/ ✅（bpmn.io 全家族：BPMN/DMN/CMMN/Forms）｜ BPMN 2.0 规范：https://www.omg.org/spec/BPMN/ ｜ Camunda Modeler：https://camunda.com/platform/modeler/

**出版/排版**
- Typst 文档：https://typst.app/docs/ ✅ ｜ Cetz 包：https://typst.app/universe/package/cetz
- TikZ/PGF 手册：https://tikz.dev/ ✅ ｜ 示例库：https://texample.net/tikz/examples/

**ASCII / SVG / 渲染**
- ASCIIFlow：https://asciiflow.com/ ✅ ｜ ditaa：https://github.com/stathissideris/ditaa ｜ goat：https://github.com/blampe/goat
- svg.js：https://svgjs.dev/ ✅ ｜ Puppeteer：https://pptr.dev/ ✅
- 本机 ASCII 技能：`~/.claude/skills/tools-visual-ascii-arch/SKILL.md`（cc-visualization-skills 包，含 tools-mermaid / tools-visual-workflows / tools-visual-state-machines / c4-model / architecture-canvas / walkthrough）

---

## 本地落链建议（哪些装本地/哪些文档抓取）

**A. 建议装本地（CLI/自托管，支撑「as code + CI 渲染」工作流）**
- `brew install graphviz`、`brew install d2`、`brew install typst`、`brew install ditaa`（或 goat）
- npm 全局：`@mermaid-js/mermaid-cli`（mmdc 出 PNG/SVG）、`puppeteer`（截图）
- pip：`diagrams`、`blockdiag`、`svgwrite`
- Docker：`yuzutech/kroki`（统一渲染网关）、`plantuml/plantuml-server`、`structurizr/lite`（C4 本地预览）、Penpot 自托管（如需开源 Figma 替代）
- Java jar：PlantUML（无 Docker 时）

**B. 建议抓取离线文档（沉淀进 raw/ + wiki 知识库）**
- **mermaid.js.org**（核心语法全量）、**tikz.dev**（体积大但离线查图好用）、**plantuml.com**、**d2lang.com/docs**、**graphviz.org**、**typst.app/docs** —— 抓取为 markdown 存 `raw/`，编译成 wiki 页并做 ChromaDB 索引（复用本机 LLM Wiki 三层架构）
- 论文 PDF：抓入 `/Users/coreyleung/dsh-collab/research/paper-cache/`（该目录已存在），重点优先：2403.12027（综述）、2310.12128（DiagrammerGPT）、2511.14967（MermaidSeqBench）、2407.05183（FlowLearn）、2606.01348（ChartArena）

**C. 不装本地（GUI/在线即可）**
- draw.io、Excalidraw、Balsamiq、Figma、Penpot 云 —— 人工精修层，用桌面/web 即可
- bpmn-js —— 作为 npm 依赖按项目引入，不必全局装

**D. 与现有 DSH/Claude 栈的落链**
- 本机 Wiki 规则已规定「图表一律用 Mermaid，禁止 ASCII art」→ 默认图语言定为 Mermaid，Kroki 作为 CI/文档统一渲染兜底
- 已装可视化技能（tools-mermaid / tools-visual-ascii-arch / c4-model / architecture-canvas / walkthrough）与推荐栈重合，优先调用；ASCII 技能仅用于终端/PR 场景，正式文档转 Mermaid
- 架构文档采用 Structurizr DSL（模型 as code）或 C4-PlantUML，输出到 `docs/architecture/`
- 跟踪 LLM 图生成方向：关注 MermaidSeqBench / DiagrammerGPT / Text2Arch / ChartArena 后续工作，作为 Agent 图生成能力选型依据

---

## 证据来源

- arXiv 交叉验证（Hugging Face papers / alphaXiv / ar5iv / scirate 镜像）：[DiagrammerGPT 2310.12128](https://huggingface.co/papers/2310.12128)、[MermaidSeqBench 2511.14967](https://huggingface.co/papers/2511.14967)、[FlowLearn 2407.05183](https://ar5iv.labs.arxiv.org/html/2407.05183)、[Text2Arch 2604.14941](https://huggingface.co/papers/2604.14941)、[LIDA 2303.02927](https://huggingface.co/papers/2303.02927)、[chart 综述 2403.12027](https://www.alphaxiv.org/overview/2403.12027)、[See-it-Say-it 2508.15222](https://www.alphaxiv.org/abs/2508.15222)、[Design2Code](https://raw.githubusercontent.com/NoviScl/Design2Code/main/README.md)、[sketch2code 1905.13750](https://ar5iv.labs.arxiv.org/html/1905.13750)、[Sketch2FullStack 2211.14607](https://arxiv.org/abs/2211.14607)、[NL2UML 综述 2204.00932](https://ui.adsabs.harvard.edu/abs/2022arXiv220400932A)、[Chart-to-Text 2203.06486](https://scirate.com/arxiv/2203.06486)、[Words-to-Structured-Visuals 2411.11916](https://ar5iv.labs.arxiv.org/html/2411.11916)、[ChartArena 2606.01348](https://arxiv-org.ezproxy.obspm.fr/html/2606.01348v2)
- 官网实测（read_url 直达，✅ 见上节）：mermaid.js.org、plantuml.com、d2lang.com、kroki.io、penpot.app、bpmn.io、typst.app/docs、tikz.dev、svgjs.dev、pptr.dev、structurizr.com、diagrams.mingrammer.com、excalidraw.com、drawio.com、asciiflow.com
- 本机事实（CLAUDE.md / 本地技能目录）：cc-visualization-skills 九技能、C4 模型技能、architecture-canvas、walkthrough、paper-cache 目录、LLM Wiki 三层架构（Mermaid 规则）
