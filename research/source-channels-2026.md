# 论文/技术文档信息源通道全景（2026-08-31）

> 调研：数据调查员（subagent）· 委派：信源体系扩展（paper-cache 补链 + 信源工具数据）
> 方法：web_search 多角度交叉验证（10 次）+ 本环境实测连通性（curl 探针，2026-08-31 21:20 CST）
> 衔接：[data-sources.md](../data-sources.md) 的 S/A/B 评级体系；评级沿用 S=一手权威 / A=高质量二手 / B=需交叉验证 / C=避免
> 实测标记：🟢=本环境可达 · 🔴=不可达 · 🟡=可达但受限

---

## 结论（推荐通道矩阵）

**核心判断：arXiv 系全链路（arxiv.org / export.arxiv.org / ar5iv.labs.arxiv.org / cn.arxiv.org / xxx.itp.ac.cn / arxiv.org.cn）在本环境全部不可达，旧"中科院镜像"方案已失效。但替代通道实测充足，无需绕墙即可完成论文元数据检索 + 全文获取 + 技术文档读取。**

| 用途 | 首选通道（实测可达） | 备选/兜底 | 不推荐 |
|------|---------------------|-----------|--------|
| 论文元数据/检索 | OpenAlex 🟢(200) · Crossref 🟢(200) · DBLP 🟢(200) | Semantic Scholar（429 需 key/退避） | Google Scholar（被墙+反爬） |
| 论文全文（arXiv 预印本） | **alphaXiv** 🟢(200, HTML 阅读) | ar5iv 自托管（docker 镜像）· Unpaywall 找 OA 版 | arxiv.org 直连（🔴） |
| 论文全文（开放获取期刊/会议） | ACL Anthology 🟢(200) · JMLR 直链 · Unpaywall 🟢(422=服务在线) | CORE（需 key）· DOAJ | IEEE/Wiley/Elsevier 付费墙（仅摘要级落链） |
| 论文↔代码关联 | Papers with Code 🟢(302=可达) | HF pwc-archive 数据集（经 hf-mirror 🟢） | — |
| 论文速递/讨论 | HuggingFace papers（经 **hf-mirror.com** 🟢） | Scirate（浏览器访问，bot 403）· alphaXiv 评论区 | huggingface.co 直连（🔴） |
| NLP 领域文献 | ACL Anthology 🟢 · DBLP 索引 🟢 | arXiv cs.CL（绕行 alphaXiv） | — |
| 技术文档 | 官方文档站（各厂）🟢 | docs.rs / ReadTheDocs / GitHub 仓库 doc | 无源转载站（C 级） |
| 付费墙判定 | Unpaywall OA 探测 + 摘要级落链 | 预印本替代（arXiv/SS 收录版） | 盗版渠道（禁止） |

**429 应对总纲（Semantic Scholar）**：无 key 共享池≈100 次/5min（全站 3s/次）→ 申请免费 key 获 1 rps → 仍 429 则 `Retry-After` 退避 + 指数退避（tenacity）+ 单次只取所需字段 + 批量 `/paper/batch`（500 IDs/次计 1 请求）→ 海量需求直接解析 S2AG 离线数据集，勿硬爬。

---

## 学术信源通道表

| 通道 | 类型 | API/入口 | 可达性(实测) | 限流 | 用途 |
|------|------|----------|--------------|------|------|
| **arXiv** | 预印本原始库 | `export.arxiv.org/api/query` · PDF `arxiv.org/pdf/{id}.pdf` · RSS `rss.arxiv.org/rss/cs.AI` | 🔴 全系不可达（000） | 1 req/3s 严格执行、单连接禁并发、UA 建议带邮箱、违规 403 可能永久封禁；`max_results≤2000` | 权威预印本源；本环境需经镜像/替代通道 |
| **alphaXiv** | arXiv 镜像+讨论层 | `alphaxiv.org`（URL 把 arxiv→alphaxiv） | 🟢 200 | 未公开；网页服务 | arXiv 替代阅读（HTML）、论文内批注/讨论；有开源版 alphaxiv-open 可自部署 |
| **ar5iv** | arXiv HTML5 转换 | `ar5iv.labs.arxiv.org/html/{id}`（LaTeXML） | 🔴 000（托管于 arxiv 基建，随墙） | — | HTML 阅读；**可自托管**（github.com/dginev/ar5iv docker），作为本地转换兜底 |
| **Scirate** | arXiv 社区筛选 | `scirate.com` | 🟡 403（bot UA 拦截，浏览器可开） | 反爬 | 论文 upvote 热度筛选，辅助选读 |
| **Semantic Scholar Graph API** | 学术元数据/引用图 | `api.semanticscholar.org/graph/v1` | 🟡 429（实测被限，符合预期） | 无 key≈100 次/5min 共享池；免费 key=1 rps 全端点；Partner≤100 rps；`/paper/batch` 500 IDs/次；search≤1000 条，批量用 `/search/bulk`；响应≤10MB；429 带 `Retry-After` | 引用网络、影响力、OA PDF 定位、作者画像；2 亿+论文 |
| **OpenAlex** | 开放学术图谱 | `api.openalex.org`（works/authors/venues/concepts） | 🟢 200（X-RateLimit 头正常返回） | 免费 10 万 credits/天 + 100 req/s；singleton=1、list=10 credits；polite pool 用 `mailto=` 或 UA 邮箱；响应带 X-RateLimit-* 头 | **首选元数据源**：2.5 亿+作品，含 arXiv 预印本/DOI/OA 链接/引用/概念；OR 语法 50 请求合一 |
| **Google Scholar** | 学术搜索（无官方 API） | scholar.google.com | 🔴 000（被墙）；且反爬 CAPTCHA 严格 | 无 API；爬取易封 | **不采用**；用 SS/OpenAlex/Lens 替代 |
| **Papers with Code** | 论文↔代码↔榜单 | `paperswithcode.com/api/v1/` · 官方 client `pip install paperswithcode-client` | 🟡 302（可达，路径需规范化） | 3s/次调用 | 找复现代码、SOTA 榜单、数据集；pwc-archive 数据集（~30 万 论文-代码链接，经 hf-mirror 取） |
| **HuggingFace Papers** | 论文速递 | `huggingface.co/papers` · `huggingface.co/api/daily_papers` | 🔴 直连 000；**hf-mirror.com 🟢 200** | 未公开严格限流，合理使用 | 每日精选/趋势论文；经 hf-mirror 镜像可达 |
| **ACL Anthology** | NLP/CL 会议开放全文 | `aclanthology.org/{id}.pdf`（ID 如 `2022.acl-long.220`）· `pip install acl-anthology` | 🟢 200 | 无公开硬限流，礼貌爬取 | NLP 领域全文权威源；批量语料有 HF 版 |
| **JMLR** | ML 期刊开放全文 | `jmlr.org/papers/volumeV/n/n.pdf`（无 API） | 🟢 200 | 无 | 直接 PDF 直链下载 |
| **Unpaywall** | 合法 OA 全文定位 | `api.unpaywall.org/v2/{doi}?email=...` | 🟢 422（服务在线，email 需真实邮箱格式） | 免费 10 万次/天；必须带 email | 付费墙文章的合法 OA 替代定位；DOI→OA PDF |
| **CORE** | OA 聚合库 | `api.core.ac.uk/v3` | 🟡 301（可达，v3 需 key） | 免费 tier 需注册 key | 3 亿+ OA 记录聚合，机构库全文 |
| **Crossref** | DOI 元数据注册 | `api.crossref.org/works` | 🟢 200 | 免费无 key；polite pool 用 mailto；近期收紧分级限流（约 50 rps 级，读响应头） | DOI 解析、期刊/资助/许可元数据、版本记录 |
| **DBLP** | CS 书目权威库 | `dblp.org/search/publ/api?q=...&format=json` | 🟢 200 | 无 key、无公开配额；礼貌 1-2 rps；大任务下 XML dump | CS 会议/期刊书目、作者消歧、venue 检索；650 万+ 记录，ODC-BY |
| **Semantic Scholar 数据集(S2AG)** | 离线语料 | `api.semanticscholar.org/datasets/v1`（需 key） | 🟡（随 API 通道） | 整库快照/增量 diff | 海量引用分析兜底，避免爬 API |
| **OpenScholar** | 检索-合成问答 | openscholar.allen.ai（demo） | 未实测 | 无 API | 45M 论文上的带引用问答，辅助综述 |

---

## 技术文档信源

| 类别 | 通道 | 评级 | 说明 |
|------|------|------|------|
| 官方文档站 | 各厂商/框架官网 docs.*（Anthropic/DeepSeek/OpenAI/Postgres/Rust/React 等） | **S** | 一手权威；优先 `docs.` 子域与版本化文档；变更以官方 changelog/release notes 为准 |
| 包/库文档镜像 | **docs.rs**（Rust crates 自动文档）· **ReadTheDocs**（Python/开源项目）· pkg.go.dev · npm 包 README | **S/A** | 与源码版本绑定的自动生成文档，docs.rs 直连源仓库 tags |
| 官方 PDF/白皮书 | 厂商 PDF（架构白皮书、评测报告） | **S** | 适合整篇落链；注意版本号与发布日期 |
| GitHub 仓库 doc/README | 各项目 `docs/`、`README.md`、wiki | **S/A** | GitHub 本环境可达；代码即文档、issue 即 FAQ；用 raw.githubusercontent.com 抓取 |
| 官方技术博客 | 各厂 engineering blog（Anthropic/DeepMind/Netflix 等） | **S** | 一手变更情报（已在 data-sources.md 登记） |
| 技术社区博客 | Medium / Dev.to / 掘金 / 知乎专栏 / V2EX | **B** | 二手经验；需作者权威度 + 交叉验证；Medium 有会员墙 |
| 微信公众号技术号 | 各技术公众号 | **B**（原创号可达 A） | 原创号质量高但**转载/洗稿比例大**；用「原创标识+首发时间+是否带来源链接」甄别 |
| 文档镜像聚合 | readthedocs.io / 各语言官方镜像（如 docs.rs 镜像、gitee 镜像仓） | **A/B** | 镜像与上游同步延迟需标注；版本漂移是主要风险 |
| SEO 聚合站 | 各种 "xxx 教程网 / 文档中文站"（非官方域名） | **C** | 多为采集/机翻，禁止作为依据（见噪音过滤规则） |

---

## API 类信源

| API | Base URL | 认证 | 限流要点 | 429/失败应对 | 备注 |
|-----|----------|------|----------|--------------|------|
| arXiv API | `export.arxiv.org/api/query` | 无 | 1 req/3s、单连接、UA 带邮箱 | 403=违规，停手别重试 | Atom XML；`max_results≤2000`；RSS 替代轮询 |
| Semantic Scholar Graph | `api.semanticscholar.org/graph/v1` | 免费 key（`x-api-key` 头） | 无 key 共享池 ~100/5min；key=1 rps | 429 读 `Retry-After` + 指数退避（tenacity）+ 共享限速器（asyncio.Semaphore）；**勿并发冲锋** | 批量 `/paper/batch`（500 IDs=1 次请求）；search 限 1000 条，大批量走 `/search/bulk`（1000/次）；海量走 S2AG 数据集 |
| OpenAlex | `api.openalex.org` | 无需 key；polite pool 加 `mailto=` 或 UA 邮箱 | 10 万 credits/天 + 100 req/s；singleton=1/list=10 credits；429 时看 X-RateLimit-Reset | 观察响应头 X-RateLimit-*；OR 语法（`filter=doi:a|b|c`）50 请求合一 | **主推**：免费、无墙、配额大、含 arXiv 预印本 |
| Crossref | `api.crossref.org` | 无；polite pool 加 mailto | 分级限流（近收紧），约 50 rps 量级；礼貌 1-2 rps 最稳 | 429 退避；`rows` 控制页大小 | DOI 元数据/许可/资助；150M+ 记录 |
| DBLP | `dblp.org/search/*/api` | 无 | 无公开配额，礼貌 1-2 rps | 慢速重试；大任务下 XML dump（dblp.org/xml/） | CS 专属权威；`format=json`；venue/author/publ 三类检索 |
| Unpaywall | `api.unpaywall.org/v2/{doi}` | 需真实 email | 10 万次/天 | 422=email 格式问题；404=无 OA 版 | 付费墙文章先查它，再决定摘要级落链 |
| CORE | `api.core.ac.uk/v3` | 免费注册 key | 免费 tier 配额制 | 401/429 检查额度 | OA 聚合兜底 |
| Papers with Code | `paperswithcode.com/api/v1/` | 无 | 3s/次 | 302 注意跟随重定向 | papers/datasets/repositories 三类 |
| HF | `huggingface.co/api/*` | 可选 token | 合理使用 | 本环境直连 000 → 换 hf-mirror.com | `/api/daily_papers` 论文速递；datasets-server 取 parquet |

**限流工程化建议**：统一封装「共享限速器 + 指数退避 + Retry-After 尊重 + 字段最小化 + 批量优先」；每个信源一个 client 类，错误码语义（403 永停 / 429 退避 / 422 参数错 / 404 无此物）分离处理——与已有 paper-cache 落链脚本的「失败重试≤3」策略兼容。

---

## 可信度评级框架

### 分级标准（S/A/B/C，与 data-sources.md 一致并细化）

| 级 | 定义 | 判定特征 | 使用策略 |
|----|------|----------|----------|
| **S 一手权威** | 官方/原始数据/作者本人 | 官方域名（docs.、*.org 学术库、厂商官网）；原始论文/官方文档/官方白皮书/原始数据集；有版本号与发布日期；作者=发布者 | 直接采信，可落库；引用标注源 URL |
| **A 高质量二手** | 权威聚合/知名专家/顶会组织 | OpenAlex/DBLP/Crossref/ACL 等学术基础设施；知名学者个人博客；知名媒体科技栏；**带完整来源链接的原创** | 采信但标注"二手"；重要事实回溯 S 源 |
| **B 需交叉验证** | 普通二手/社区经验/转述 | 技术社区帖（V2EX/Reddit/掘金）、普通公众号、SEO 博客、无来源转载；结论未经核实 | 仅作线索；结论必须有 ≥2 个独立源或 1 个 S 源背书才入库 |
| **C 避免/待淘汰** | 低质/采集/机翻/营销 | 命中噪音过滤规则（见下）；无作者、无日期、无来源；纯 SEO 聚合 | 不入库；已在库的定期清理 |

### 噪音过滤规则（供"可信度分析器"工具实现）

**① SEO 软文/AI 生成特征（硬性降级 B→C 或直接拒收）**
- 触发词块：中文「在当今数字化时代/值得注意的是/深入探讨/一站式/赋能/颠覆性/至关重要」；英文 "In today's digital landscape" / "game-changer" / "delve into" / "leverage" / "comprehensive guide" / "seamlessly"
- AI 触发词密度 >5/1000 词（英文）或 >3/1000（中文）→ 疑似 AI 生成
- 句法指纹：H2 标题 >70% 以问句结尾；"Here's why" 式开头 ≥3 次/1500 词；200 词窗口内三从句排比句 >50%；20 词内堆叠 ≥3 个 hedge 词（may/typically/perhaps）
- 结构指纹：列表项长度 SD ≤10 字符（对称列表膨胀）；列表前铺垫 >250 词；全文句长 SD 过低（节拍器式平坦）
- 元数据指纹：无作者署名、无发布日期、无来源引用、域名含 keyword-stuffing（如 best-xxx-guide.com）、页面满是内链/广告

**② 无源转载判定（降级至 B/C）**
- 正文无原始来源链接 / 只写"来源网络" / 时间晚于首发但内容逐字相同 → 采集站
- 多站同时出现同文（可用搜索标题片段交叉验证）→ 判为转载，回到原始出处评级
- 机翻痕迹（术语错译、语序怪异、中英混杂无原文对照）→ C 级拒收

**③ 镜像页判定（可用但降级）**
- 域名 ≠ 官方域名但内容同源（如 arxiv 镜像、HF 镜像）→ 标注「镜像」；**用于可达性绕行，不用于权威性背书**；优先记官方源 URL
- 镜像与上游同步延迟（如数小时~1 天）需在缓存时标注快照时间
- Scirate 等 bot-403 站点 → 浏览器通道可用，脚本通道标记受限

**④ 付费墙判定（处理策略而非拒收）**
- 判定信号：正文需订阅/登录/机构访问（HBR/IEEE/Wiley/Elsevier/Emerald 等）；返回 403/登录页/摘要页
- 处置流程：① Unpaywall 查 OA 版 → ② arXiv/SS/OpenAlex 找预印本 → ③ 都没有则**摘要级落链**（标题+源+状态，不编造全文，见 blueprint-nonarxiv-20260830 实践）→ ④ 盗版渠道一律禁止
- 反例豁免：官方免费 PDF（ACL/JMLR/arxiv 镜像）与 Open Access 期刊属正常 S 级

**⑤ 时间与版本规则**
- 技术文档类：记录文档版本/发布时间；镜像与官方版本漂移>1 个 minor 版本时降级
- 论文类：预印本标注版本（v1/v2）；已正式发表以期刊版 DOI 为准

---

## 可落库信源清单

> 可直接合并进 data-sources.md / 信源工具数据库；字段：名称 / 类型 / URL / API / 评级 / 限流 / 用途

| 名称 | 类型 | URL / API | 评级 | 限流 | 用途 |
|------|------|-----------|------|------|------|
| OpenAlex | 学术元数据 API | https://api.openalex.org | S | 免费 10 万 credits/天 + 100 rps；polite pool(mailto) | 论文检索/引用/OA 链接/概念（首选） |
| Crossref | DOI 元数据 API | https://api.crossref.org | S | 无 key，礼貌 1-2 rps，mailto | DOI 解析/许可/资助/版本记录 |
| DBLP | CS 书目 API | https://dblp.org/search/publ/api | S | 无公开配额，礼貌 1-2 rps | CS 会议/期刊书目、作者消歧 |
| ACL Anthology | NLP 开放全文 | https://aclanthology.org | S | 无公开硬限流 | NLP 论文全文 PDF |
| JMLR | ML 开放全文 | https://jmlr.org/papers | S | 无 | ML 期刊 PDF 直链 |
| alphaXiv | arXiv 镜像+讨论 | https://www.alphaxiv.org | A（镜像） | 未公开 | arXiv 论文 HTML 阅读/批注（本环境可达） |
| ar5iv | arXiv HTML 转换 | https://ar5iv.labs.arxiv.org（可自托管） | A（镜像） | — | arXiv HTML 阅读；自托管兜底 |
| Semantic Scholar Graph API | 学术引用图 API | https://api.semanticscholar.org/graph/v1 | A | 无 key ~100/5min；key=1 rps；batch 500 | 引用网络/影响力/OA 定位（429 需退避） |
| Unpaywall | OA 全文定位 API | https://api.unpaywall.org/v2/{doi} | A | 10 万/天，需 email | 付费墙→合法 OA 替代 |
| Papers with Code | 论文-代码关联 | https://paperswithcode.com/api/v1 | A | 3s/次 | 复现代码/SOTA 榜单 |
| HF Papers（经 hf-mirror） | 论文速递 | https://huggingface.co/papers · /api/daily_papers | A | 合理使用 | 每日论文精选/趋势 |
| HuggingFace Datasets（经 hf-mirror） | 数据集 API | https://huggingface.co/api/datasets | A | 合理使用 | 数据集检索/parquet 下载 |
| CORE | OA 聚合 API | https://api.core.ac.uk/v3 | A | 需 key，配额制 | OA 全文聚合兜底 |
| Scirate | arXiv 社区筛选 | https://scirate.com | B | 反爬(bot 403) | 论文热度筛选（浏览器用） |
| 官方文档站 | 技术文档 | 各厂商 docs.* | S | — | 一手技术依据 |
| docs.rs / ReadTheDocs | 文档镜像 | docs.rs · readthedocs.io | S/A | — | 版本化包文档 |
| 官方技术博客 | 一手情报 | 各厂 engineering blog | S | — | 平台变更/新特性 |
| Medium / Dev.to / 掘金 | 技术社区博客 | — | B | — | 二手经验，需交叉验证 |
| 微信公众号技术号 | 技术自媒体 | — | B（原创 A） | — | 甄别原创/转载后使用 |
| Google Scholar | 学术搜索 | scholar.google.com | — | 无 API+反爬 | **不采用**（被墙） |
| 旧 arXiv 中文镜像（xxx.itp.ac.cn / cn.arxiv.org / arxiv.org.cn） | 镜像 | — | — | — | **已失效**（实测全 000，勿再依赖） |

---

## 证据来源

**实测探针（2026-08-31 本环境 curl，8s 超时）**
- 🔴 arxiv.org / export.arxiv.org / ar5iv.labs.arxiv.org / cn.arxiv.org / xxx.itp.ac.cn / arxiv.org.cn / huggingface.co / scholar.google.com → 000
- 🟢 api.openalex.org(200, X-RateLimit 头正常) · api.crossref.org(200) · dblp.org(200) · aclanthology.org(200) · alphaxiv.org(200) · hf-mirror.com(200) · jmlr 未测(常识可达)
- 🟡 api.semanticscholar.org(429, x-amzn-errortype TooManyRequestsException) · scirate.com(403 bot) · paperswithcode.com/api/v1(302) · api.core.ac.uk(301) · api.unpaywall.org(422 服务在线)
- OpenAlex 响应头实测：x-ratelimit-remaining 990 / x-ratelimit-reset 9485s

**网络检索交叉验证**
- OpenAlex 官方限流文档：https://raw.githubusercontent.com/ourresearch/openalex-docs/main/how-to-use-the-api/rate-limits-and-authentication.md （10 万 credits/天、100 rps、polite pool、credit 成本表、X-RateLimit 头）
- Semantic Scholar 限流（apis.io 机器可读档）：https://apis.io/rate-limits/semantic-scholar/semantic-scholar-rate-limits/ （共享池 ~300/100、key 1 rps、datasets 走 key）
- Semantic Scholar API 实战指南（paper-chaser-mcp docs）：https://raw.githubusercontent.com/joshuasundance-swca/paper-chaser-mcp/main/docs/semantic-scholar-api-guide.md （1 rps 硬顶、共享限速器、batch、Retry-After、S2AG）
- arXiv API 限流（awesome-llm-paper-wiki）：https://github.com/moonlarry/awesome-llm-paper-wiki/blob/main/docs/api_limits.md （1 req/3s、单连接、403 封禁风险）
- Paper Sources 参考（mlx skills）：https://raw.githubusercontent.com/damionrashford/mlx/main/skills/research/references/sources.md （arXiv/SS/PwC/ACL/JMLR/HF papers/OpenScholar 端点与限流汇总）
- DBLP API 指南：https://dblp.org/faq/1474707.html · https://raw.githubusercontent.com/brycewang-stanford/Auto-Empirical-Research-Skills/main/skills/43-wentorai-research-plugins/skills/domains/cs/dblp-api/SKILL.md （650 万+记录、无认证、ODC-BY）
- arXiv 国内加速方案（FlashVPN 博客，**B 级佐证**，VPN 推广文但镜像清单可参考）：https://home.flashvpn.io/blog/arxiv-china-access-speed-guide （xxx.itp.ac.cn 中科院镜像——**本次实测已失效**）
- alphaXiv：https://github.com/AsyncFuncAI/alphaxiv-open · https://www.ithome.com/0/785/621.htm （arXiv 讨论层，URL 替换法）
- ar5iv：https://github.com/dginev/ar5iv （LaTeXML HTML5 转换，可自托管）
- HuggingFace Papers：https://huggingface.co/datasets/justinxzhao/hf_daily_papers · https://github.com/elsatch/daily_hf_papers_abstracts （daily_papers 数据与镜像用法）
- AI 内容/AI slop 检测方法论：https://raw.githubusercontent.com/rainday/smart-blog-skills/main/skills/blog/references/ai-slop-detection.md · https://github.com/RyanAlberts/ai-slop （触发词/句法/结构指纹评分）
- Crossref 限流演进：https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/ （polite pool、分级限流）
- 免费学术 API 综述（DEV 社区，A 级佐证）：https://dev.to/0012303/5-free-academic-apis-you-should-know-250m-papers-no-scraping-needed-557g

**相关本地资产**：`../data-sources.md`（S/A/B 评级体系）· `blueprint-nonarxiv-20260830.md`（付费墙摘要级落链实践）· `paper-cache/`（103 篇已落链论文）
