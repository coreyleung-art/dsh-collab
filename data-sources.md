# 信息源登记表（Data Sources Registry）

> 维护者：session-4787d717（数据调查员） · 版本：v0.1 初版 · 更新：2026-08-17
> 用途：跨会话共享的优质信息源清单，可评估、可迭代；入库信息必须标注来源与验证状态。
> 评级：S=一手权威（官方/原始数据） · A=高质量二手（可信专家/知名媒体） · B=需交叉验证 · C=避免/待淘汰

## 一、本机知识资产（S 级，本地权威）

| 源 | 路径 | 用途 | 验证状态 |
|----|------|------|----------|
| Obsidian LLM Wiki | ~/Library/Mobile Documents/iCloud~md~obsidian/Documents | 知识库沉淀（raw/wiki/日记） | ✅ 在用 |
| 爬虫工具链 | ~/crawler-lab（v0.21.0，654 测试） | 采集/解析/数据治理 | ✅ 20 轮迭代验证 |
| 协作登记区 | ~/dsh-collab/ | 跨会话产物/SOP/登记表 | ✅ 在用 |
| MCP 配置 | ~/.claude.json（11 servers） | 工具生态 | ✅ 已验证 |

## 二、自动化/爬虫领域（S/A 级）

| 源 | 类型 | 用途 | 评级 | 验证 |
|----|------|------|------|------|
| Playwright 官方（github.com/microsoft/playwright-mcp） | 官方仓库 | 浏览器自动化 MCP | S | ✅ 本机已装 |
| OpenClaw docs（docs.openclaw.ai/platforms/mac/permissions） | 官方文档 | macOS TCC/权限机制权威参考 | S | ✅ 实战验证（adhoc 签名根因） |
| electron-builder issues（#9062） | Issue 库 | Electron 辅助功能授权对象 | S | ✅ 实战验证 |
| Simon Willison blog（simonwillison.net） | 专家博客 | AI/工具实测情报 | A | ✅ 引用过 |
| HN Algolia API（hn.algolia.com） | 数据源 | 技术社区情报/搜索 | A | ✅ 爬虫适配过 |

## 三、AI/LLM 领域（S/A 级）

| 源 | 类型 | 用途 | 评级 | 验证 |
|----|------|------|------|------|
| Anthropic 官方文档 | 官方 | LLM API/最佳实践 | S | 待持续验证 |
| DeepSeek 文档 | 官方 | 模型/API | S | 待验证 |
| HuggingFace | 社区 | 模型/数据集 | A | 待验证 |
| Dify 文档 | 官方 | 本地 LLM 平台 | S | ✅ 本机部署 |

## 四、通用情报/技术发现（A/B 级）

| 源 | 类型 | 用途 | 评级 | 验证 |
|----|------|------|------|------|
| GitHub Trending | 平台 | 新项目发现 | A | 需交叉验证 |
| 官方技术博客（各厂） | 一手 | 平台变更/新特性 | S | 逐篇验证 |
| web_search 结果池 | 工具 | 多角度初筛 | B | 必须交叉验证 |
| 技术社区（V2EX/Reddit/掘金） | 二手 | 实战经验 | B | 需验证 |

## 五、流程规则

1. **入库前**：有效性验证（可用/准确）+ 安全性过滤（隐私/恶意/合规）双通过
2. **引用规范**：入库信息必须标注 来源 + 评级 + 验证状态
3. **评估周期**：每轮调查任务后增量更新；评级可升降；C 级定期清理
4. **共享**：其他会话可读本表，新增源可 @数据调查员登记

## 六、待扩充

- 各领域 RSS/Newsletter 清单
- 爬虫反爬策略情报源
- 工具/MCP 生态跟踪源（npm trends、MCP registry）

## 工具登记信源（source-registry.json 自动同步 · 2026-08-31）
| 名称 | URL | 类型 | 评级 |
|------|-----|------|------|
| OpenAlex API | https://openalex.org | api | A |
| alphaXiv | https://alphaxiv.org | mirror | S |
| OpenAlex API | https://openalex.org | api | A |
| Crossref | https://api.crossref.org | api | A |
| DBLP | https://dblp.org | api | A |
| ACL Anthology | https://aclanthology.org | proceedings | S |
| alphaXiv | https://alphaxiv.org | mirror | S |
| HF Papers(hf-mirror) | https://hf-mirror.com/papers | aggregator | A |
| Semantic Scholar | https://api.semanticscholar.org | api | A |
| Papers with Code | https://paperswithcode.com | aggregator | S |
| Unpaywall | https://unpaywall.org | api | A |
| CORE | https://core.ac.uk | api | A |

## 工具登记信源（source-registry.json 自动同步 · 2026-08-31）
| 名称 | URL | 类型 | 评级 |
|------|-----|------|------|
| OpenAlex API | https://openalex.org | api | A |
| alphaXiv | https://alphaxiv.org | mirror | S |
| Crossref | https://api.crossref.org | api | A |
| DBLP | https://dblp.org | api | A |
| ACL Anthology | https://aclanthology.org | proceedings | S |
| HF Papers(hf-mirror) | https://hf-mirror.com/papers | aggregator | A |
| Semantic Scholar | https://api.semanticscholar.org | api | A |
| Papers with Code | https://paperswithcode.com | aggregator | S |
| Unpaywall | https://unpaywall.org | api | A |
| CORE | https://core.ac.uk | api | A |
| city8 城市吧 | https://gz.city8.com | poi-aggregator | A |
| 城市惠 | https://www.cityhui.com | poi-aggregator | A |
| 图吧公交 | https://mbus.mapbar.com/guangzhou/ | poi-aggregator | A |
| 电话邦 | https://www.dianhua.cn | poi-aggregator | A |
| 花好网 | https://www.huahao.com | poi-aggregator | B |
| 花长廊/花浪漫 | https://www.hualangman.com | poi-aggregator | B |
| 顺企网名录 | https://foshan.11467.com | poi-aggregator | B |
| Apple 地图 POI | https://maps.apple.com | poi-aggregator | S |
| 高德排行榜 | https://ranks.amap.com | poi-aggregator | S |
| 天眼查（索引层） | https://www.tianyancha.com | poi-aggregator | S |

## 工具登记信源（source-registry.json 自动同步 · 2026-08-31）
| 名称 | URL | 类型 | 评级 |
|------|-----|------|------|
| OpenAlex API | https://openalex.org | api | A |
| alphaXiv | https://alphaxiv.org | mirror | S |
| Crossref | https://api.crossref.org | api | A |
| DBLP | https://dblp.org | api | A |
| ACL Anthology | https://aclanthology.org | proceedings | S |
| HF Papers(hf-mirror) | https://hf-mirror.com/papers | aggregator | A |
| Semantic Scholar | https://api.semanticscholar.org | api | A |
| Papers with Code | https://paperswithcode.com | aggregator | S |
| Unpaywall | https://unpaywall.org | api | A |
| CORE | https://core.ac.uk | api | A |
| city8 城市吧 | https://gz.city8.com | poi-aggregator | A |
| 城市惠 | https://www.cityhui.com | poi-aggregator | A |
| 图吧公交 | https://mbus.mapbar.com/guangzhou/ | poi-aggregator | A |
| 电话邦 | https://www.dianhua.cn | poi-aggregator | A |
| 花好网 | https://www.huahao.com | poi-aggregator | B |
| 花长廊/花浪漫 | https://www.hualangman.com | poi-aggregator | B |
| 顺企网名录 | https://foshan.11467.com | poi-aggregator | B |
| Apple 地图 POI | https://maps.apple.com | poi-aggregator | S |
| 高德排行榜 | https://ranks.amap.com | poi-aggregator | S |
| 天眼查（索引层） | https://www.tianyancha.com | poi-aggregator | S |
| 昆明市农业农村局日价格 | https://nyncj.km.gov.cn/nygz/jgxq/ | flower-price | A |
| 呈贡区月度统计表 | http://www.kmcg.gov.cn | flower-price | A |
| 云南省农业农村厅日价格 | https://nync.yn.gov.cn | flower-price | A |
| 云南省花卉价格监测月报 | https://weihengtech.com | flower-price | B |
| KIFA月报(中国花卉园艺) | https://chinahhxh.com | flower-price | B |
| 花易宝平台行情 | https://www.flowerpn.com | flower-price | B |
| 中国花卉园艺杂志 | https://chinahhxh.com | flower-price | B |
| 昆明国际数据交易所 | https://kmpde.com | flower-price | C |
| 学术论文数据(知网) | https://www.cnki.net | flower-price | C |
| OneAPI节假日接口 | https://timor.tech/api/holiday | factor | A |
| 心知天气 | https://www.seniverse.com | factor | A |
| 上海期货交易所原油 | https://www.shfe.com.cn | factor | A |
