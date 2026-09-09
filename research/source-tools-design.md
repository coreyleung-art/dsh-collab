# 信息源体系工具设计文档（source-tools design v1.0）

> 数据调查员 4787d717 · 2026-08-31 · 三工具：source-trust / source-extend / 信源调研
> 实现：dsh-tools v1.21.0（Rust，rust-tools 工程）· 标准：R006 插件化工具化 9 项

## 一、背景与目标

信息源体系（论文/技术文档信源）需要：**调研**（通道发现）→ **评级**（可信度判断）→ **扩展**（登记管理）→ **落库**（可检索）闭环。
本组工具将信息源管理工具化，过滤噪音与虚假信息，支撑论文落链与调研管线的信源质量。

## 二、工具设计

### 1. source-trust — 信源可信度分析器
- **目的**：评估信源可信度（S/A/B/C 四级）+ 检测文本噪音/虚假信息特征
- **架构**：dsh-tools 子命令（Rust，src/source_trust.rs，纯 std + serde_json）
- **评级规则**（内置表）：
  - S 官方一手：官方域（openai/anthropic/deepseek）+ arXiv + 会议 proceedings + 实验室官方 + github 官方仓库
  - A 权威聚合：学术元数据（semantic scholar/openalex/crossref/dblp）+ 知名媒体（nature/ieee/acm/reuters）
  - B 二手/媒体：博客（medium/dev.to/掘金/知乎/CSDN）+ 社区
  - C 低质：中文商业域 + SEO 特征 + 无源转载
- **噪音检测**（8 特征词）：点击这里/限时优惠/立即购买/加微信/扫码领取/震惊/全网首发/独家爆料 → ≥3 命中判 C 高噪音
- **CLI**：`source-trust <url>`（评级+得分+JSON）/ `--check <text>`（噪音分）/ `--list`（规则表）
- **关联**：[[research/source-channels-2026]]（评级框架细化）、[[dsh-collab/data-sources.md]]（S/A/B 体系）、依据论文（fake news detection / information credibility）

### 2. source-extend — 信源扩展登记
- **目的**：新增信息源登记（URL 校验 → 自动评级 → 追加 source-registry.json）
- **架构**：dsh-tools 子命令（src/source_extend.rs）
- **数据**：source-registry.json（name/url/type/grade/domain/added 6 字段，12 信源已登记）
- **自动评级**：复用 S/A 域表（未命中默认 B）
- **CLI**：`source-extend <name> <url> [type] [grade]` / `--list`
- **关联**：[[dsh-collab/research/source-registry.json]]、R020（新工具蓝图适配）

### 3. 信源调研（通道矩阵）
- **目的**：信息源通道发现与可达性维护
- **产出**：source-channels-2026.md（181 行：通道实测矩阵 + 20 条可落库清单）
- **实测**（2026-08-31）：OpenAlex/Crossref/DBLP/alphaXiv/hf-mirror 可达 200；Semantic Scholar 429（需 key/退避）；Google Scholar 弃用
- **工具衔接**：source-trust --list / source-extend --list 查询登记；通道新增走 source-extend

## 三、数据流（调研→评级→登记→落库 闭环）

```
信源发现（web_search/调研子代理/source-channels 更新）
  → source-trust 评级（S/A/B/C + 噪音过滤）→ 通过则
  → source-extend 登记（source-registry.json）→
  → 论文落链管道（paper-cache：fetch→extract→KB+papers-db 双写）→
  → 检索验证（knowledge_search / paper-audit 自检）
```

## 四、R006 9 项达标对照
| 项 | source-trust | source-extend |
|----|-------------|---------------|
| dsh 插件形态 | dsh-tools 单二进制子命令 ✅ | 同 ✅ |
| TCC 检测 | N/A（CLI 工具） | N/A |
| CLD 自适应 | 无 CLD 依赖 ✅ | 同 ✅ |
| dsh 版本自适应 | --version v1.0.0 ✅ | 同 ✅ |
| 文档化 | --help + 头注释 + 本文档 ✅ | 同 ✅ |
| 版本管理 | dsh-tools v1.21.0 + CHANGELOG ✅ | 同 ✅ |
| 统一日志 | stdout 结构化 + JSON ✅ | 同 ✅ |
| 自动落链 | 输出可 JSON 管道 | registry 落盘 ✅ |
| CLI 治理 | 子命令 + 参数 + help ✅ | 同 ✅ |

## 五、关联文档索引
| 文档 | 路径 | 关系 |
|------|------|------|
| 信源通道调研 | research/source-channels-2026.md | 评级框架/通道矩阵依据 |
| 信息源登记表 | dsh-collab/data-sources.md | S/A/B 体系源 |
| 信源登记库 | research/source-registry.json | source-extend 数据 |
| R006 标准 | rules-registry/RULES.md §R006 | 工具化标准 |
| rust-tools 工程 | ~/dsh-collab/rust-tools/ | 实现工程（queue_condense 模板） |
| 论文落链管道 | research/paper-cache/PIPELINE.md | 数据流下游 |
| 可信度依据论文 | paper-cache/texts/（补拉） | 评级/噪音方法依据 |

## 六、下一步
1. 可信度评级规则扩展（融合 fake news 检测研究：来源信誉/内容特征/传播特征）
2. source-trust 接入调研子代理（产出自动评级）
3. source-extend 与 data-sources.md 同步（人工登记 ↔ 工具登记双写）
