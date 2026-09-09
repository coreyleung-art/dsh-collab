# 智能体图形化表达工具规范（工作类型 → 工具优先级）

> 数据调查员 4787d717 · 2026-08-30 · 基于 visual-diagram-tools-2026 调研（18 工具矩阵）+ 本机已装工具实测
> 目的：全网络统一「什么工作类型用什么工具」的优先级排序，避免各会话乱选工具

## 一、核心原则
1. **文本 as code 优先**：能用 Mermaid/D2/PlantUML 文本描述就不开 GUI 白板（可版本化/可审阅/省资源）
2. **文档内嵌默认 Mermaid**（已装 mmdc + 系统 Chrome 渲染）：本机默认图语言
3. **工具按能力分级**：通用（Mermaid）→ 专业（PlantUML 的 UML、D2 的架构）→ 专用（Graphviz 自动布局、Structurizr C4）
4. **GUI 工具仅人工/交付场景**：Excalidraw/Penpot/Figma（白板/线框/设计稿）

## 二、工具选择优先级表（工作类型 → 优先工具）

| 工作类型 | P1（首选） | P2（备选） | P3（补充） | 说明 |
|----------|-----------|-----------|-----------|------|
| 架构图 | Mermaid flowchart | D2 | Structurizr（C4） | 文档内嵌 mermaid；正式架构文档用 structurizr |
| 流程图 | Mermaid flowchart | D2 | PlantUML activity | |
| 泳道图 | Mermaid（subgraph 泳道） | PlantUML activity | — | mermaid 泳道够用 |
| 时序图 | Mermaid sequenceDiagram | PlantUML sequence | — | |
| 状态图 | Mermaid stateDiagram-v2 | PlantUML state | — | |
| UML 类图/用例/部署 | PlantUML | — | — | plantuml 已装（JRE 21） |
| 甘特图/计划 | Mermaid gantt | — | — | |
| ER 图 | Mermaid erDiagram | PlantUML | — | |
| 数据流/依赖图（自动布局） | Graphviz dot（可选） | Mermaid | — | graphviz 待环境（sudo） |
| 白板/头脑风暴（GUI） | Excalidraw | draw.io | — | 人工交互场景 |
| UXUI 线框/设计稿（GUI） | Penpot（开源） | Figma/Balsamiq | — | 商业工具按需 |
| 终端/PR/文档内 ASCII | tools-visual-ascii-arch 技能 | ditaa/goat | — | 已装技能 |
| 数据可视化（图表） | Python chart 库/LIDA | Mermaid pie/xy | — | 数据报告 |
| LaTeX 文档图 | TikZ | Typst+Cetz | — | 学术文档 |

## 三、选择规则（决策逻辑）
1. 文档/报告内嵌图 → **Mermaid**（默认，已装可渲染验证）
2. 需要 UML 全家族（类/用例/部署）→ **PlantUML**
3. 架构文档（C4 语境）→ **Structurizr**（DSL as code）
4. 复杂自动布局（依赖/数据流）→ **Graphviz**（待环境，装后用）
5. 快速草图/终端分享 → **ASCII 技能**（tools-visual-ascii-arch）
6. 交互白板/设计稿 → GUI（Excalidraw/Penpot），仅人工场景
7. 拿不准 → 用 Mermaid（最通用、已装、可渲染）

## 四、落地工具状态（本机已就绪）
| 工具 | 状态 | 渲染 |
|------|------|------|
| mermaid-cli (mmdc) | ✅ 已装 | SVG/PNG（系统 Chrome） |
| plantuml | ✅ 已装（JRE 21 + jar） | PNG/SVG |
| d2 | ✅ 已装（v0.8.2） | SVG/PNG |
| graphviz | ⏳ 待环境（sudo） | — |
| Claude 可视化技能 6 个 | ✅ 已有 | ASCII/Mermaid |

## 五、执行建议（交 HR 固化）
- 本规范登记为网络级工具选择标准（resource-conflict-policy 或新规范文件）
- 各会话生成图表时按此优先级；新工具引入先评估登记（供应链流程）
- 渲染验证命令可复用：mmdc -p puppeteer-config.json -i x.mmd -o x.svg（visual-tools/ 下）
