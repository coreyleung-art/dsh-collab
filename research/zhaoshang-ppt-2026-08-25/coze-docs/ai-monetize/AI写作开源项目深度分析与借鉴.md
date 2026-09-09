# AI写作开源项目深度分析与借鉴

> 2026-06-23 | 基于Webnovel Writer源码+同类项目调研

---

## 一、Webnovel Writer 深度架构解析

**项目**: [lingfengQAQ/webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer)
**版本**: v6.2.0 | **Stars**: 3470+ | **协议**: GPL v3 | **语言**: Python 93.8%

### 1.1 核心架构：Story System（合同驱动体系）

这是整个项目最核心的设计，解决"AI写长篇不忘事"的问题：

```
┌─────────────────────────────────────────────────┐
│ Claude Code                                      │
├─────────────────────────────────────────────────┤
│ Skills (7个):                                    │
│ init / plan / write / review / query / learn /   │
│ dashboard                                        │
├─────────────────────────────────────────────────┤
│ Agents (3个):                                    │
│ Context Agent / Data Agent / Reviewer(六维审查)  │
├─────────────────────────────────────────────────┤
│ Data Layer:                                      │
│ state.json / index.db(SQLite) / vectors.db       │
├─────────────────────────────────────────────────┤
│ Story System:                                    │
│ .story-system/ (合同·提交·事件)                  │
└─────────────────────────────────────────────────┘
```

**关键设计：真源（Source of Truth）与投影（Projection）分离**

| 层级 | 作用 | 数据 |
|------|------|------|
| **真源** | 唯一事实来源 | `.story-system/`（合同+提交+事件审计） |
| **投影** | 只读视图，从真源派生 | `state.json` / `index.db` / `summaries/` / `memory_scratchpad.json` |

这跟数据库的 CQRS（命令查询职责分离）是同一个思路——写入走主链，查询走投影。

### 1.2 防幻觉三定律

| 定律 | 说明 | 执行方式 |
|------|------|----------|
| **大纲即法律** | 遵循大纲，不擅自发挥 | Context Agent 强制加载章节大纲 |
| **设定即物理** | 遵守设定，不自相矛盾 | Reviewer Agent 内置一致性审查 |
| **发明需识别** | 新实体必须入库管理 | Data Agent 自动提取并消歧 |

### 1.3 写章流水线（9步关卡）

`/webnovel-write` 不是一次生成，而是带关卡的完整流水线：

1. 预检项目根、占位符和Story System健康状态
2. 刷新本章runtime contract
3. 调用`context-agent`生成**写作任务书**（关键：把相关上下文压缩成一个结构化任务文档）
4. 根据任务书起草正文
5. 调用`reviewer`做多维审查，**blocking issue不通过则阻断**
6. 润色、排版、Anti-AI终检
7. 调用`data-agent`提取事实
8. 生成`CHAPTER_COMMIT`，驱动state/index/summary/memory/vector投影
9. 执行章节级备份

### 1.4 RAG检索架构

```
查询 → QueryRouter(auto) → vector / bm25 / hybrid / graph_hybrid
 └→ RRF融合 + Rerank → Top-K
```

- **auto模式**：优先向量检索，失败自动回退BM25
- **graph_hybrid模式**：叠加实体图谱关联（人物/地点/物品关系网）
- **Embedding**: Qwen3-Embedding-8B（ModelScope免费）
- **Reranker**: jina-reranker-v3（Jina AI）

**关键**：没配Embedding Key也能用——自动退回BM25关键词检索。这种降级容错设计很实用。

### 1.5 追读力系统（Strand Weave节奏系统）

| Strand | 含义 | 理想占比 | 说明 |
|--------|------|----------|------|
| **Quest** | 主线剧情 | 60% | 推动核心冲突 |
| **Fire** | 感情线 | 20% | 人物关系发展 |
| **Constellation** | 世界观扩展 | 20% | 背景/势力/设定 |

节奏红线：Quest连续不超5章、Fire断档不超10章、Constellation断档不超15章。

### 1.6 六维审查体系

| 审查维度 | 检查重点 |
|----------|----------|
| High-point Checker | 爽点密度与质量 |
| Consistency Checker | 设定一致性（战力/地点/时间线） |
| Pacing Checker | Strand比例与断档 |
| OOC Checker | 人物行为是否偏离人设 |
| Continuity Checker | 场景与叙事连贯性 |
| Reader-pull Checker | 钩子强度、期待管理、追读力 |

### 1.7 数据持久化设计

```
project-root/
├── .story-system/          # 合同、章节提交和事件审计（真源）
├── .webnovel/              # 状态、索引、摘要、备份和长期记忆（投影）
│   ├── state.json          # 当前状态快照
│   ├── projection_log.jsonl # 投影执行日志
│   └── logs/               # 运行日志
├── 正文/                   # 章节正文
├── 大纲/                   # 总纲、卷纲、时间线和章纲
├── 设定集/                 # 世界观、角色、力量体系等设定
└── 审查报告/               # 章节审查报告
```

---

## 二、对我们现有项目的借鉴点

### 2.1 🔥 可以直接借鉴的设计

| Webnovel Writer 设计 | 我们的对应场景 | 借鉴方案 |
|---------------------|---------------|----------|
| **合同系统（真源+投影分离）** | 花材价格数据管线（4源→合并→Prophet→日报） | 把原始爬虫数据作为真源，价格看板/日报/趋势预警作为投影，任何投影失败可从真源重放 |
| **写作任务书（Context Agent）** | 小红书笔记创作流程 | 每次创作前自动生成"创作任务书"：提取账号定位+最近5篇笔记数据+对标爆款+本周热点，注入上下文 |
| **降级容错（BM25 fallback）** | 花材价格查询Skill的RAG | 查历史价格时，向量检索失败自动降级为关键词匹配+正则匹配 |
| **追读力系统** | 小红书笔记效果评估 | 定义"钩子力度"指标：标题CTR→正文完播率→赞藏比→关注转化率，量化每篇笔记的"追读力" |
| **六维审查** | 小红书笔记发布前审查 | 审查维度：①邪修味浓度 ②知识钩子合规 ③AI标注合规 ④引流路径完整 ⑤标签覆盖 ⑥格式规范 |
| **CHAPTER_COMMIT（事实提交）** | 每日数据采集+处理 | 每次采集完成后生成commit记录：源→原始数据→清洗后数据→衍生指标→日报→趋势预警，全链路可追溯 |
| **doctor命令（项目体检）** | 每日采集链路健康检查 | 检查项：4个爬虫源是否alive→latest.json是否今日→Prophet模型是否过期→日报是否生成 |

### 2.2 🎯 核心可迁移模式：CQRS + Event Sourcing

Webnovel Writer的"真源+投影"本质就是Event Sourcing模式。我们的花材价格系统可以这样改造：

```
真源层（不可变事件流）：
  daily_scrape_events/     # 每日爬取原始数据（JSON事件）
  └── 2026-06-23_dounan.json
  └── 2026-06-23_chenghui.json

投影层（从事件派生，可重算）：
  latest_prices.json       # 最新价格（from events）
  daily_report/            # 每日日报（from events）
  trend_alert/             # 趋势预警（from events + Prophet）
  prophet_model/           # 预测模型（from all events）

好处：
1. 任何投影损坏，从事件流重放即可修复
2. 新增投影（如新看板），不需要改真源
3. 审计追踪：每天的数据变更都有完整记录
```

### 2.3 💡 小红书笔记创作流水线（仿Webnovel Writer）

```
/webnovel-write 的思路 → /xhs-write 的思路

1. 预检：账号状态+上次发布时间+待发队列
2. 生成创作任务书：
   - 账号定位（花店邪修）
   - 近7天笔记数据
   - 本周热点/花材行情
   - 内容配比（养护50%+行情20%+AI邪修20%+冲突10%）
3. 起草正文+标题候选
4. 六维审查（邪修味/合规/引流/标签/格式/AI标注）
5. 生成封面图+要点卡片
6. 输出完整发布包（封面+卡片+正文+标签）
```

---

## 三、同类开源AI写作项目对比

### 3.1 项目一览

| 项目 | Stars | 语言 | 核心差异 | 协议 |
|------|-------|------|----------|------|
| **Webnovel Writer** | 3470 | Python | Claude Code插件，合同系统+RAG+追读力 | GPL v3 |
| **AI_NovelGenerator** | 新项目 | Python | 全流程自动化，Web可视化界面，支持本地大模型 | MIT |
| **Inkos** | 1600 | TypeScript | CLI多Agent流水线，33维审查，多模型路由 | MIT |
| **Novel Studio** | 新项目 | JS | 桌面App，12种AI写作模式，角色关系图+时间线 | 免费 |
| **rag-memory** | — | Python | 通用RAG记忆系统，PostgreSQL+pgvector+Neo4j | — |
| **NovelAIne** | — | Python+Flutter | 智能RAG触发器，Supabase pgvector，叙事模式切换 | — |

### 3.2 重点项目详细对比

#### AI_NovelGenerator
- **GitHub**: https://github.com/Novel-AI/AI_NovelGenerator
- **核心卖点**: 百万字长篇强一致性管控，全流程自动化
- **架构**: 多智能体协同 + 分层长文本记忆体系
- **流程**: 世界观设定→大纲搭建→分卷分章创作→一致性校验→伏笔回收→完结排版
- **亮点**:
  - Web可视化操作界面（非CLI）
  - 支持本地大模型（Llama3/Qwen2.5/DeepSeek/GLM-4），断网也能用
  - 支持云端API（GPT-4o/Claude）
  - 一键启动包，5分钟部署
  - 全流程干预：可随时修改设定/人设/大纲，系统自动更新记忆库
- **与我们场景关联**: 如果想做"花店知识助手"的桌面客户端，这种Web UI+本地模型的路子值得参考

#### Inkos
- **GitHub**: https://github.com/Narcooo/inkos
- **核心卖点**: 33维审查 + 多模型路由 + Anti-AI去味
- **架构**: TypeScript CLI，多Agent流水线（draft→audit→revise）
- **亮点**:
  - 33维审查（角色记忆/物品连续性/情节一致性）
  - 多模型路由：写作用Claude，审查用GPT-4o
  - De-AI flavoring：迭代修改减少AI痕迹
  - 导出EPUB
- **与我们场景关联**: "De-AI去味"功能对小红书笔记很重要——用户反馈改写后效果更好，本质就是去AI味

#### rag-memory
- **PyPI**: https://pypi.org/project/rag-memory/
- **核心卖点**: 通用RAG记忆系统，不是写作专用
- **架构**: PostgreSQL 17 + pgvector + Neo4j + Graphiti
- **技术栈**: FastAPI + LangGraph + React + MCP Server
- **亮点**:
  - 20个MCP工具
  - 知识图谱（Neo4j）+ 向量搜索双引擎
  - Web爬虫（Crawl4AI）
  - 成本极低：OpenAI embedding $0.02/1M tokens
- **与我们场景关联**: 如果要做花材价格/养护知识的RAG增强，这个通用框架比写作专用框架更合适

### 3.3 选型建议

| 场景 | 推荐项目 | 理由 |
|------|----------|------|
| 研究长篇一致性架构 | Webnovel Writer | 合同系统设计最成熟，CQRS+Event Sourcing |
| 快速搭建AI写作工具 | AI_NovelGenerator | Web UI + 一键部署 + 本地模型支持 |
| 笔记去AI味参考 | Inkos | De-AI flavoring + 多模型路由 |
| 花材知识RAG基建 | rag-memory | 通用RAG框架，PostgreSQL+Neo4j双引擎 |
| 小红书创作Agent | 自建（借鉴WNW） | 没有现成方案，但WNW的任务书+审查+追读力模式可移植 |

---

## 四、立即可执行的3个借鉴动作

### Action 1: 小红书笔记创作流水线（本周）
仿WNW的`/webnovel-write`，建立`/xhs-create`流程：
- 写前：自动生成创作任务书（账号数据+热点+内容配比）
- 写中：6维审查（邪修味/合规/引流/标签/格式/AI标注）
- 写后：效果追踪（48h数据回填→追读力评分→下次创作优化）

### Action 2: 花材数据管线CQRS改造（下周）
- 原始爬虫数据作为事件流（不可变真源）
- 价格看板/日报/预警/Prophet模型全部作为投影
- 新增投影只需从事件流重放，不改真源

### Action 3: De-AI去味功能研究
参考Inkos的De-AI flavoring实现，为小红书笔记增加"邪修味校准"步骤——确保输出不是AI腔而是"邪修偷懒法"口吻。用户已验证：自己改写>AI直发，本质就是去AI味。
