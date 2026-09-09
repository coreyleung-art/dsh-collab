# AI 能力提升高质量论文库 —— 建库调研报告

> 调研时间：2025（基于 2023–2026 论文趋势）；方法：9 次中英文 web_search（Agent/推理/RL/GUI 智能体/长上下文/评测/信源 API/建库方案），优先官方 arXiv/OpenReview/会议/官方博客，交叉验证；经典论文的 arXiv ID 同时经语义核对，新论文以官方页面为准。

## 调研结论

1. **主题覆盖建议锁定 8 个方向**：Agent 规划与工具使用、推理增强、RL/偏好对齐、多模态与 GUI 智能体、长上下文与记忆、评测基准、上下文工程、蒸馏压缩。这 8 类论文是 2023–2026 提升 LLM/Agent 能力的主干线，且彼此有引用链（如 AgentBench→SWE-bench→OSWorld 的评测演进）。
2. **论文质量评级是建库核心**：以「会议收录 + 代码开源 + 高引用/高复现 + 权威实验室」四要素打分，S/A/B 三级。单靠 arXiv 下载量不可靠（如 MMLU 引用极高但代码无官方实现），需结合 Semantic Scholar citations API 与 Papers with Code 复现标记交叉评级。
3. **信源体系应分层自动化**：arXiv 分类订阅（cs.AI/cs.CL/cs.LG）+ HF Daily Papers + OpenReview 截稿扫描作「发现层」，Semantic Scholar/OpenAlex API 作「元数据与引用层」，本地 SQLite+向量库作「沉淀层」。
4. **推荐单机方案**：SQLite（FTS5 全文检索）+ ChromaDB（嵌入语义检索）+ 增量 cron 流水线；论文全文以 PDF 落盘本地，元数据可增量 upsert（arXiv ID/DOI 为唯一键）。团队/多端再迁移 PostgreSQL+pgvector。
5. **合规边界**：本库不收集任何敏感个人数据；arXiv 为非独占许可、可本地缓存与再分发（保留署名），会议论文注意版权（仅个人使用）；调用 Semantic Scholar/OpenAlex/arXiv API 须遵守速率限制与 ToS；若后续把「论文库」扩展到电商/外卖平台自动化场景，须先审阅平台规则、账号封禁风险与法律边界（爬虫条款、数据安全法）。

### ① 关键论文主题清单（每主题 3–8 篇，含 arXiv ID/出处）

**A. Agent 规划与工具使用**
- Toolformer（2302.04761，Meta）——模型自监督学习调用工具
- ReAct: Synergizing Reasoning and Acting（2210.03629，ICLR 2023）——推理+行动交错
- Reflexion（2303.11366，NeurIPS 2023）——语言强化自我反思
- Voyager（2305.16291）——LLM 驱动的 Minecraft 终身学习智能体
- Generative Agents（2304.03442，UIST 2023）——记忆+规划+社交模拟
- Gorilla / ToolBench（2305.15334 / 2305.16504，ICLR 2024）——API 调用与工具学习基准
- SWE-agent（2405.15793，NeurIPS 2024）——软件工程任务智能体
- 综述：The Rise and Potential of LLM-based Agents（2309.07864）；A Survey on LLM-based Autonomous Agents（2308.11432）；A Review of Prominent Paradigms for LLM-Based Agents（2406.05804）

**B. 推理增强（CoT/ToT/自洽/测试时计算）**
- Chain-of-Thought Prompting（2201.11903，NeurIPS 2022）
- Self-Consistency（2203.11171，ICLR 2023）
- Tree of Thoughts（2305.10601，NeurIPS 2023）
- Least-to-Most Prompting（2205.10625，ICLR 2022）
- Zero-shot CoT（2205.11916，NeurIPS 2022）；Program of Thoughts（2211.12588）
- Scaling LLM Test-Time Compute Optimally（2408.03314，OpenAI）；s1: Simple test-time scaling（2501.19393）
- DeepSeek-R1（2501.12948）；Kimi k1.5（2501.12599）——推理强化学习代表
- 综述：Reasoning with Large Language Models, a Survey（2407.11511）；Chain-of-X 范式综述（2404.15676）

**C. 强化学习与对齐（RLHF/DPO/GRPO）**
- Deep RL from Human Preferences（1706.03741）——RLHF 源头
- InstructGPT（2203.02155，NeurIPS 2022）
- Constitutional AI（2212.08073）——RLAIF 的规则化对齐
- DPO（2305.18290，NeurIPS 2023）——无需显式奖励模型的偏好优化
- KTO（2402.01306）；ORPO（2403.07691）——更轻量对齐
- RLAIF（2309.00267）——AI 反馈替代人工反馈
- DeepSeekMath（2402.03300）——GRPO 原始出处；配合 DeepSeek-R1（2501.12948）
- Secrets of RLHF in LLaMA-2（2307.04964）——工程细节一手资料

**D. 多模态理解与 GUI 智能体**
- Flamingo（2204.14198，DeepMind）；LLaVA: Visual Instruction Tuning（2304.08485，NeurIPS 2023）；Qwen-VL（2308.12966）；InternVL（2312.14238）
- WebGPT（2112.09332）；WebGUM（2311.18707）——网页任务早期代表
- Mind2Web（2306.05572）；WebArena（2307.13854，ICLR 2024）；WebVoyager（2401.13919）
- OSWorld（2404.07972，NeurIPS 2024）——真实计算机环境统一基准
- AppWorld（2407.18901）——真实 App 任务执行环境
- UI-TARS: Pioneering Automated GUI Interaction with Native Agents（2501.12326，字节 Seed）——原生 GUI Agent 训练范式

**E. 长上下文与记忆**
- Longformer（2004.05150）；Big Bird（2007.14062）——稀疏注意力先驱
- Lost in the Middle（2307.03172，ICLR 2024）——位置偏置关键发现
- Effective Long-Context Scaling of Foundation Models（2309.16039，Gemini 1.5 相关）
- YaRN（2309.00071）；LongRoPE（2402.13753）——RoPE 外推
- Ring Attention（2310.06236）；MemGPT（2310.08560）——分层记忆 OS
- 综述：Memory Mechanisms of LLM-based Agents（2404.13501）；Techniques to Extend Context Length（2402.02244，IJCAI 2024）
- 批判视角：Is It Really Long Context if All You Need Is Retrieval?（EMNLP 2024 main）；Long Context vs. RAG（2501.01880）

**F. 评测基准（AgentBench/SWE-bench/GAIA 等）**
- MMLU（2009.03300）；GSM8K（2110.14168）；HumanEval（2107.03374）；BIG-bench（2206.04615）
- AgentBench（2308.03688）——LLM Agent 综合评测
- SWE-bench（2310.06770，ICLR 2024）——真实 GitHub issue 解决
- GAIA（2311.12983）——通用助手能力问答基准
- WebArena（2307.13854）；OSWorld（2404.07972）
- MMLU-Pro（2406.01574）；GPQA（2311.12022）；LiveBench（2406.19314）；Chatbot Arena（2403.04132）

**G. 上下文工程（ICL/提示/检索增强）**
- GPT-3 Few-Shot（2005.14165，NeurIPS 2020）——ICL 奠基
- Rethinking the Role of Demonstrations（2202.12837，EMNLP 2022）；What Makes Good In-Context Examples（2101.06804）
- APE（2211.01910，ICLR 2023）；Active-Prompt（2302.12246）；Promptbreeder（2309.16797）；Meta-Prompting（2401.12954）
- RAG（2005.11401，NeurIPS 2020）；Self-RAG（2310.11511，ICLR 2024）；CRAG（2401.15884）；GraphRAG（2404.16130）；MemoRAG（2409.05591）

**H. 模型蒸馏与压缩**
- Distilling the Knowledge in a Neural Network（1503.02531，Hinton）
- DistilBERT（1910.01108）；TinyBERT（1909.10351）；MiniLM（2002.10957）
- Textbooks Are All You Need / phi-1（2306.11644）
- Orca / Orca 2（2306.02707 / 2311.11045）；WizardLM（2304.12244）；Zephyr（2310.16944）；LIMA（2305.11206）
- Distilling Step-by-Step（2305.02301）
- 量化：LLM.int8()（2208.07339）；GPTQ（2210.17323）；AWQ（2306.00978）

### ② 论文信源体系

| 层级 | 信源 | 用法 |
|---|---|---|
| 发现层 | arXiv 分类订阅（cs.AI / cs.CL / cs.LG，RSS 或 export.arxiv.org/api/query） | 每日拉取新论文，关键词过滤 |
| 发现层 | Hugging Face Daily Papers（huggingface.co/papers） | 社区热度排序，追热点 |
| 发现层 | OpenReview（ICLR/NeurIPS 审稿期） | 抢跑未收录论文 + 审稿意见 |
| 会议层 | NeurIPS / ICML / ICLR / ACL / EMNLP 官方 proceedings | 录用定稿 + 版本核对 |
| 元数据层 | Semantic Scholar Graph API（api.semanticscholar.org/graph/v1）；OpenAlex（api.openalex.org） | 引用数、作者、摘要、去重、相关性排序 |
| 复现/榜单位 | Papers with Code；HF Daily Papers | 复现标记、SOTA 榜、质量交叉验证 |

### ③ 建库方案（SQLite + 向量检索）

    -- papers 元数据表
    CREATE TABLE papers (
      id INTEGER PRIMARY KEY,
      arxiv_id TEXT UNIQUE,            -- 唯一键（arXiv/DOI 二选一）
      doi TEXT UNIQUE,
      title TEXT NOT NULL,
      abstract TEXT,
      year INTEGER,
      venue TEXT,                      -- NeurIPS 2023 / arXiv 预印本等
      authors TEXT,                    -- JSON 数组，或独立 authors 表
      keywords TEXT,                   -- 逗号分隔
      quality_rating TEXT,             -- S/A/B
      rating_reason TEXT,
      verification_status TEXT,        -- unverified / verified / outdated
      local_pdf_path TEXT,             -- 全文路径（如 papers/2305.18290.pdf）
      citation_count INTEGER,
      source_rank TEXT,                -- S/A/B 信息源评级
      created_at TEXT, updated_at TEXT
    );
    -- 建议补充
    -- 1) FTS5 虚拟表做关键词全文检索（title+abstract）
    -- 2) embeddings 表或独立 ChromaDB collection：chunk_text + vector + paper_id
    -- 3) paper_topics 关联表（8 大主题）；paper_tags 自由标签
    -- 4) update_log 表记录每次增量来源与变更

- **增量更新**：以 arXiv ID / DOI 为主键 UPSERT；每日 cron 拉 arXiv 新条目 → 关键词/主题匹配 → 抓 PDF → 生成嵌入 → 入 FTS5 + 向量库；去重、更新引用数与评级。
- **语义检索**：推荐 sentence-transformers（bge-m3 / gte-Qwen2 等中文多语模型）生成 chunk 嵌入，存 ChromaDB（或 SQLite + sqlite-vec）；检索时混合 BM25（FTS5）+ 向量相似度，按主题过滤。
- **可选演进**：多用户/团队 → PostgreSQL + pgvector；大规模 → Qdrant/Milvus；与已有 Obsidian + ChromaDB（dsh-research 集合）打通复用。

### ④ 信息源评级（S/A/B）与更新机制

| 级别 | 含义 | 示例 | 更新频率 |
|---|---|---|---|
| S | 一手权威：官方 arXiv / OpenReview / 会议 proceedings / 实验室官方仓库与博客 / 官方 API | arxiv.org、openreview.net、papers.nips.cc、OpenAI/DeepMind/Meta 官方博客 | 每日（arXiv API）；会议期即时 |
| A | 高可信聚合：HF Daily Papers、Papers with Code、AMiner、顶会官方社交账号 | huggingface.co/papers、paperswithcode.com | 每日/每周 |
| B | 二手/媒体：技术媒体、第三方论文榜、中文社区文章 | 机器之心、公众号榜单、第三方 Awesome 列表 | 每周核查，仅作线索，需回落到 S 源验证 |
| 更新机制 | 每日 arXiv 分类拉取 + 每周 HF 摘要 → 入库；月度核对会议录用与引用数（Semantic Scholar）；季度人工复评 S/A/B 与 verification_status；发现旧结论被推翻（如 Lost in the Middle 之后的上下文研究）即标记 outdated | | |

### 噪音排除记录（本次调研）
- arxiv-org.ezproxy.obspm.fr / export.arxiv.org 镜像页 —— 仅作线索，统一回落到官方 arxiv.org abs 页。
- MDPI/preprints.org 泛综述、无作者无日期的 SEO 页（ossaihub、x-mol、lobehub MCP 页）—— 不采信，只用于发现线索。
- 中文二手实践文（阿里云开发者社区 RAG 教程等）—— 仅实践参考，不进入论文证据。
- 对个别 2025 新综述的 arXiv ID 未能在搜索中二次确认者，报告以「经典论文 + 官方页核对」为主，未确证 ID 不列入。

## 候选方案对比表

| 方案 | 适用规模 | 语义检索 | 增量更新 | 维护成本 | 推荐度 | 备注 |
|---|---|---|---|---|---|---|
| SQLite + FTS5 + 本地 ChromaDB | 个人/单机（数百~数万篇） | ✅（bge-m3 等） | ✅ UPSERT + cron | 低 | ⭐⭐⭐⭐⭐ | 本机默认方案，零服务依赖 |
| SQLite + sqlite-vec | 个人/单机 | ✅（同库向量） | ✅ | 低 | ⭐⭐⭐⭐ | 单文件、备份简单，生态较新 |
| PostgreSQL + pgvector | 团队/多端 | ✅ | ✅ | 中 | ⭐⭐⭐⭐ | 多用户并发、SQL 强一致，适合后续迁移 |
| Obsidian + ChromaDB（复用 research-pipeline） | 个人笔记生态 | ✅ | 半自动 | 中 | ⭐⭐⭐ | 与现有 dsh-research 集合打通，但批量元数据管理弱 |
| 托管知识库（Dify / Qdrant Cloud / 阿里云） | 云端/协作 | ✅ | ✅ | 中高 | ⭐⭐⭐ | 省运维，但论文数据出本地需注意授权与合规 |

## 推荐路线

1. **第 1 阶段（1 周）**：建 SQLite 库（上面 schema）+ FTS5；按 8 大主题人工录入首批 ~40–60 篇核心论文（本报告清单为种子），抓 PDF 到本地 papers/，记录 quality_rating 与 verification_status。
2. **第 2 阶段（1–2 周）**：接 arXiv API 每日增量（cs.AI+cs.CL+cs.LG，关键词过滤 8 主题），去重入库；接 Semantic Scholar/OpenAlex 批量补引用数与元数据；HF Daily Papers 周摘要作人工复核队列。
3. **第 3 阶段（2 周）**：bge-m3 嵌入 + ChromaDB 语义检索，提供混合检索 CLI/API；写入 update_log，纳入 dsh-research 向量索引（与 Obsidian 打通）。
4. **第 4 阶段（按需）**：多端需求时迁移 pgvector；增加 LLM 自动摘要、相关性推荐、评级复核工作流（月度）。

## 证据来源（URL 列表）

- arXiv 官方检索/API：https://arxiv.org/list/cs.AI/recent ；https://export.arxiv.org/api/query
- UI-TARS 官方论文页：https://arxiv.org/abs/2501.12326 （搜索结果确认）
- 长上下文批判：https://aclanthology.org/2024.emnlp-main.924/ ；上下文扩展综述 https://arxiv.org/abs/2402.02244
- 长上下文 vs RAG 评测：https://arxiv.org/abs/2501.01880
- 推理综述（Reasoning with LLMs, a Survey）：https://arxiv.org/abs/2407.11511
- Agent 范式综述：https://arxiv.org/abs/2406.05804 ；Agent 架构综述（Semantic Scholar 收录页）：https://www.semanticscholar.org/paper/25ae2fce719c6f6f0b09de1e0f917a7b719e5e99
- Agent 评测综述（Agent Harness Survey）：https://github.com/Gloriaameng/Awesome-Agent-Harness
- 每日论文追踪实践：https://github.com/alloevil/AI-Paper-Daily
- HF Daily Papers：https://huggingface.co/papers ；Papers with Code：https://paperswithcode.com
- Semantic Scholar API：https://www.semanticscholar.org/product/api ；OpenAlex：https://docs.openalex.org
- 论文库/RAG 建库参考：https://github.com/naholav/rag-academic-assistant ；https://github.com/Noel-Alex/Scientific-RAG
- 经典论文（CoT/DPO/RLHF/SWE-bench/GAIA 等）均以官方 arXiv abs 页面为准，如 https://arxiv.org/abs/2201.11903 、https://arxiv.org/abs/2305.18290 、https://arxiv.org/abs/2310.06770 、https://arxiv.org/abs/2311.12983

> 说明：本次环境无抓全文工具链（research-fetch），未将全文落 Obsidian raw；建议下一步由宿主按 research-pipeline 补抓并向量索引。

## 下一步建议

1. 由宿主确认是否执行 dsh research-pipeline 第 3–5 步（research-fetch 抓全文 → 编译 wiki 页 → ChromaDB 索引），把本报告沉淀进 dsh-research 集合。
2. 用 arXiv API 脚本对上述 60+ 论文批量校验 arXiv ID 与最新版本（v2/v3），产出种子数据 CSV/JSON。
3. 确定嵌入模型（推荐 bge-m3 或 gte-Qwen2-7B 本地部署）与 chunk 策略（按段落/标题切 512–1024 token）。
4. 建立评级工作流：新论文先 B 级临时入库存证，达 2 个独立来源交叉验证 + 代码开源/会议收录后升 A/S。
5. 合规检查清单：API 速率限制、arXiv 许可署名、会议论文仅个人使用、不采集个人数据；若扩展至平台自动化业务需另行合规评审。

## 2026-08-28 增量：版本管理自动化 / 多仓 / 记忆系统

- Automated Versioning for Software Releases（IEICE 2026, DOI 10.1587/transinf.2025MPP0003）——自动版本化三类技术（规则/ML/轻量混合），**直接支撑 dsh-tools version 工具升级方向**
- AriadneMem: Threading the Maze of Lifelong Memory（arXiv:2603.03290）——图结构记忆：entropy gating + 冲突感知合并 + 桥接检索；LoCoMo Multi-Hop F1 +15.2%
- ID-RAG（arXiv:2509.25299）——身份检索增强生成，长程 persona 一致性
- MemGPT（2310.08560，已有）→ 补充「函数调用式记忆操作 + 写门控安全」要点（见论文档案）

> 完整档案：research/papers-local/versioning-memory-papers-20260828.md（含与 repo-pipeline × version 合并、OpenChronicle 吸收的关联分析）
> 待办：拉全文 PDF 落 papers-local/ → 编译 wiki 页 → ChromaDB 索引（research-pipeline 3-5 步）
