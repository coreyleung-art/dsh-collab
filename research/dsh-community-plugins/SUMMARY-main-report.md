# dsh 社区插件调研 · 完整报告（2026-09-06）

> 调研：数据调查员 4787d717 + 子代理×2（12616c26 上下文/记忆类 · 1a1f0850 工具/搜索/科研类）
> 生态来源：~/.dsh/market/index.json（4508 条，2026-09-06 扫描）+ awesome-dsh-plugin（14554★）+ dshmarket README + GitHub/npm 交叉验证
> 本机基线：dsh 0.1.1-rc.2（实测）· 已装 30+ 插件 · 状态：**调研完成，待用户决定是否安装**

---

## 一、生态总览

### 1.1 市场规模

| 维度 | 数值 |
|---|---|
| 市场索引总数 | **4508**（GitHub 4316 + npm 192） |
| 官方 / 社区 | 193 / 4315 |
| bundle / service / other / tool / ui | 2105 / 728 / 1518 / 84 / 66 |
| 能力分类 Top | 浏览器Web 636 · 工具 294 · 计费 285 · 搜索 252 · UI 249 · 视觉 194 · 记忆 179 · 主题 117 · MCP 112 · 工作流 65 · 语音 54 |

### 1.2 高星标杆（Top 15）

| 插件 | star | 说明 |
|---|---|---|
| dsh-root（仓库） | 210K | DSH 官方仓库「Everything is a Plugin」 |
| open-design | 94K | 设计插件（Claude Design 开源版） |
| awesome-dsh-plugin | 14.5K | 精选列表（本报告交叉参考） |
| dsh-web-ui | 5.7K | Web GUI 插件生态（本机在用其全家桶） |
| iPolloWork | 5.4K | Agent Workbench |
| modlens | 3.7K | 视觉桥（**本机已装 3.16.7**） |
| dshmarket | 3.2K | 官方社区市场（Settings→Plugin Market） |
| dsh-context | 1.3K | 上下文观测仪表 |
| dsh-agent-teams | 1.4K | Agent 团队编排 |
| deepseek-harness-desktop | 1.7K | Tauri 桌面版 |

### 1.3 核心洞察

1. **DSH「一切皆插件」生态已成熟**——dsh web 本身就是插件聚合；官方/社区 4500+ 插件覆盖模型/工具/UI/记忆/主题全层
2. **本机已是深度用户**（30+ 插件含官方全家桶 + 自研 market/guard/waimai 等），但存在 **3 个关键差距**：
   - ① 无上下文观测/compaction 插件（CLD-017「上下文只增不减」缺口，本机 harness 0.1.1-rc.2 未挂）
   - ② genui 用**旧包名**（@omdsh-dev/dsh-genui 0.8.6，须迁 @changfenhuang 0.9.8）
   - ③ 搜索单后端（deepseek-official，无限流兜底）
3. **版本红线是最大约束**：本机 0.1.1-rc.2 vs 生态新插件多要求 0.1.2-alpha+ → 部分高价值候选被版本墙挡住

---

## 二、候选评估（11 个 + 官方市场，共 12 项）

### 🟢 A 组 · 装-优先（3 项）

#### A1. dsh-context — ⭐1305（评分 5/5）
- **URL**：[bowenliang123/dsh-context](https://github.com/bowenliang123/dsh-context)（npm `dsh-context`，Apache-2.0，v0.43.0）
- **核心能力**：纯**上下文观测仪表**——Context 页（Stats/Token 环/Trend/Browser/Events/File Activity）+ `/context` 命令；逐请求展示上下文组成与增量，把 **compaction/prune 事件**钉在趋势柱上显示回收量；Context Browser 可展开每个元素（system prompt/工具 schema/tool 结果/图片 token），可回看 compaction 前步骤。读数与官方 composer context ring 同源。
- **与 CLD-017 关系**：不执行 compaction，但回答「谁在涨/compaction 何时发生/回收多少」——**先归因后治理**，也是挂 compactor 后验证效果的仪表。真正的回收需另配 compaction 插件。
- **⚠️ 版本红线**：官方 compat.md——0.1.1 线仅支持 **@0.41.x**；0.42+/0.43 需 dsh 0.1.2-rc.1+。**本机必须装 0.41.x，勿装 latest**。
- **安装**：`dsh plugin --profile web add dsh-context@0.41.x`（零构建）
- **风险**：低（只读仪表）；主要风险是误装 0.42+ 在 rc.2 上 seam 断链

#### A2. modsearch — ⭐391（评分 5/5）
- **URL**：[liustack/modsearch](https://github.com/liustack/modsearch)（npm `@liustack/modsearch` 5.10.1，MIT，**1 open issue**，pushed 2026-09-03）
- **核心能力**：把 dsh web seam 的 `searchProvider` 从 deepseek-official 换为 modsearch 多引擎链——**默认 Firecrawl keyless（1000 免费/月，免注册免 key）** + Tavily（1000/月免卡）/Exa（$10≈1400 次）/Antigravity/Grok X 可选；多引擎**自动 failover + key 轮换**；输出**结构化 JSON 证据**（含 uncertainty）；read_page 整页抓取；X/Twitter 语料。
- **与本机对比**：本机 web_search = deepseek-official 单后端；modsearch 直插 research-pipeline 第一步，遇官方限流/故障自动切换（**免 key 兜底**）。
- **作者可信**：liustack = 已装 modlens 同作者；可回滚。
- **安装**：`dsh plugin --profile web add @liustack/modsearch@5.10.1`
- **风险**：低

#### A3. dshmarket（官方版）— ⭐3241
- **URL**：[dsh-market/dsh-market](https://github.com/dsh-market/dsh-market)（npm `dshmarket` v1.44.0）
- **核心能力**（本报告亲测源码）：Settings→**Plugin Market**——2300+ 插件浏览/搜索/分类筛选/截图轮播/评论（giscus）/收藏；**主题一键装/切换免重启**；一键安装直播进度；**备份恢复**（JSON 导出/WebDAV/Gist，merge 恢复）；**热 disable/enable**（写 cordis.patch.yml，HMR ~1s）；**更新检测**（npm 版本/HEAD）；**中国下载路由**（GitHub 加速 fallback）；public update API。
- **工程质量**：TypeScript + 59 测试 + **仅 2 运行时依赖**（js-yaml + undici）+ 标准 dsh.bundle（cordis.patch.yml insert）
- **版本要求**：dsh web **0.1.0-rc.6+**（本机 0.1.1-rc.2 ✅）
- **与本机对比**：本机已装自研 `dsh-plugin-market` 0.1.0（link 自 ~/dsh-plugin-workflow/market/，监控 npm 官方包/GitHub/Gitee）——**官方版能力明显更全**（主题/热装/备份/更新/评论），建议作为市场层升级替代（可并行保留自研版或退役）
- **安装**：`dsh plugin --profile web add dshmarket`
- **风险**：低（成熟度高、依赖轻）

### 🟡 B 组 · 必做迁移 / 可选推荐（3 项）

#### B1. dsh-genui 迁移（必做，防重装即坏）— ⭐409
- **事实纠偏**（子代理实测）：本机 bundle 已含 `@omdsh-dev/dsh-genui` **0.8.6**（旧包名旧版），本会话 dsh-ui fence / render_ui / validate_dsh_ui 即其渲染链路——**已装等效，无需新装**
- **行动项**：v0.9.2 起包名迁至 `@changfenhuang/dsh-genui` 0.9.8；旧键下任何一次 pnpm 重装会报 `Cannot find package` → **必须迁移**
- **顺带增量**：0.9.8 有 streaming 渲染 + 多 surface fence 发现增强
- **安装**：
  ```bash
  dsh plugin --profile web remove @omdsh-dev/dsh-genui
  dsh plugin --profile web add @changfenhuang/dsh-genui   # → 0.9.8
  # 重启 + Cmd+R，控制台验证: [genui] client active; fence-channel=registry|dom
  ```
- **风险**：低（预防性维护）

#### B2. dsh-univer-office — ⭐276（评分 4/5）
- **URL**：[dream-num/dsh-univer-office](https://github.com/dream-num/dsh-univer-office)（npm `dsh-univer-office` 0.2.14，Apache-2.0）
- **✅ 版本兼容**：官方 README 明示支持 **0.1.1-rc.2**（本机精确命中）
- **核心能力**：真实 office 运行时（Univer）——Sheet/Doc/Slide/Base/Board 组合进同一 .univer 文件；agent 自然语言建/改（公式/图表/透视/筛选/格式/校验）；会话内审阅流（隔离草稿→live preview→approve/discard→语义 compare）；双向导入导出 .xlsx/.csv/.tsv/.docx/.pptx
- **与本机对比**：dsh-plugin-office（已装）= 轻量文件生成；univer = **交互式可编辑可审阅环境**——信源清单/数据表/LBS 库/周报交付质量跃升
- **安装**：`dsh plugin --profile web add dsh-univer-office`（装后需重启）
- **风险**：中——重依赖（@univerjs-pro + libsql + puppeteer-core），体积/启动开销；与现有 office 并存不冲突

#### B3. evolve-modes — ⭐197（评分 3/5）
- **URL**：[GraySilver/dsh-evolve-modes](https://github.com/GraySilver/dsh-evolve-modes)（npm `@graysilver/dsh-evolve-modes` 0.4.0，MIT）
- **✅ 版本兼容**：peerDeps `^0.1.1-rc.2` → 本机**精确兼容**（候选里唯一现装即合）
- **核心能力**：输入区四维组合——工作状态（正常/计划）+ 思考策略（标准/第一性原理/Grilling）+ 质量门禁（关/对抗性审查/验收审查）+ 自进化（Propose 默认：每 3 次父回复触发隔离学习请求 → 人工确认的规则提议 → 注入 system prompt，**不写 AGENTS.md**）
- **与 R006 关系**：质量门禁/思考组合 = R006 外纯增量；自进化 = 独立第二规则通道，可与 R006 人审桥接
- **⚠️ 副作用**：每条已批准全局规则永久占 system prompt → **与 CLD-017 相悖**；建议只开 Propose 不批准
- **安装**：`dsh plugin --profile web add @graysilver/dsh-evolve-modes@0.4.0`
- **风险**：中（上下文膨胀/每次审查+1 调用）

### ⚪ C 组 · 不装 / 暂缓（6 项）

| 候选 | ⭐ | 结论 | 理由 |
|---|---|---|---|
| modlens | 3713 | **不装-已等效** | 本机已装 3.16.7 + vision_analyze/describe_image/analyze_ui_image 多通道；追新 3.25.4 等 harness≥0.1.2 |
| dsh-memory (joyiok) | 0 | **不装-重复** | 单文件 JSON 关键词库无向量，弱于本机 dsh-knowledge（评分 1/5） |
| dsh-memory (Cairn) | 1 | **不装-通道冗余** | BM25+compaction-aware flush 工程优，但需自挂管线，与本机 KB/OC/ChromaDB 三通道重叠（评分 2/5） |
| DSH-taskboard | 232 | **不装-暂缓** | SQLite 任务权威 + 人审 done 优于本机 localStorage 版，但 peerDeps **钉死 0.1.2-alpha.2**（版本墙）；harness 升级后首批替换 |
| Mimir | 208 | **不装-条件性** | pin 0.16.0（0.18 需 ≥0.1.2-alpha.4）+ 需 brew install tectonic + 自建 SearXNG；仅学术写作场景值得 |
| dsh-plugin-subscriptions | 328 | **不装-合规风险** | 逆向/非官方端点 + 订阅 ToS 灰区封号风险 + 10 open issues（评分 2/5，R006 扣分） |

### 📌 补充：dsh-vision-toolkit（⭐854，评分 3/5）
- **URL**：[Anionex/dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit)（npm `@anionex/dsh-vision-toolkit` 0.1.40）
- **能力**：粘贴图直问/多图问答；长截图**分块 OCR**；grounding 定位/裁剪/pixel-diff；**截图→前端 UI 还原（HTML）**
- **与本机**：读图与 modlens/ui-spec 重叠高；但**长截图逐段 OCR 是本机缺的系统化能力**（情报采集价值）
- **建议**：可选——出现「长截图 OCR/带框定位」硬需求再装（provider 可指向现有 LM Studio/Ollama）

---

## 三、推荐安装顺序（3 批，均需重启窗口 + 用户批准）

```
批 1（立即·装-优先，最高 ROI）：
  dsh plugin --profile web add dsh-context@0.41.x        # 上下文归因仪表（CLD-017）
  dsh plugin --profile web add @liustack/modsearch@5.10.1 # 多引擎搜索免key兜底

批 2（必做迁移，防重装即坏）：
  dsh plugin --profile web remove @omdsh-dev/dsh-genui
  dsh plugin --profile web add @changfenhuang/dsh-genui   # → 0.9.8

批 3（可选，按需）：
  dsh plugin --profile web add dshmarket                  # 官方市场（升级自研市场层）
  dsh plugin --profile web add dsh-univer-office          # 有数据表/报表交付需求时
  # @graysilver/dsh-evolve-modes@0.4.0                    # 流程门禁增量（只开 Propose）

每步后：重启 dsh → 浏览器 Cmd+R
验证：搜索带源 JSON 结果 / console [genui] client active / Settings 出现 Plugin Market
```

---

## 四、与在办事项衔接

| 插件 | 衔接项 | 价值 |
|---|---|---|
| dsh-context | CLD-017/CLD-020 内存治理 | 补「上下文归因」观测层（配合 compaction 落地治本） |
| modsearch | research-pipeline | 增强 web_search 可靠性与证据结构化（数据调研主链） |
| dshmarket | 插件治理/R006 | 升级为官方市场，后续插件发现/安装走它 |
| dsh-univer-office | 信源清单/LBS 库交付 | 数据表可视化编辑审阅交付 |

## 五、风险与边界

1. **第三方代码权限**：安装插件运行本机权限代码（可读文件/用凭据/联网）——所有候选已审源码（package.json/cordis.patch.yml/结构），但仍建议 J37 隔离验证后再正式启用
2. **版本红线**：本机 0.1.1-rc.2 vs 生态 0.1.2-alpha 是最大约束（dsh-context 必须 0.41.x / taskboard 暂缓 / Mimir pin 0.16.0）；**harness 升级后应重评**（Mimir 0.18 Venues / univer 新特性 / taskboard 解锁）
3. **需重启窗口**（批次安装）——R027/审批流
4. **genui 迁移**必须做但低风险（防将来 pnpm 重装失败）
5. **subscriptions 明确不装**（逆向端点 + ToS 灰区，R006 合规扣分）

## 六、后续动作（待用户决定）

- [ ] 仅出报告（已完成本报告）→ 暂不安装
- [ ] 按批 1 安装 dsh-context@0.41.x + modsearch（需审批 + 重启窗口）
- [ ] 批 2 genui 迁移（预防性）
- [ ] 批 3 可选（dshmarket / univer-office / evolve-modes）
- [ ] harness 升级至 ≥0.1.2 后重评被版本墙挡住的候选（taskboard/Mimir/context 最新）

---

## 附录 · 信源

- 本机：~/.dsh/market/index.json（4508 条）· ~/.dsh/profiles/web/package.json（bundles/deps 实测）· ~/.dsh/profiles/node_modules/@deepseek-ai/*（版本）
- 分报告：`context-memory-eval.md`（103 行）+ `tools-search-eval.md`（246 行，含每候选安装命令）
- 生态：awesome-dsh-plugin（github.com/awesome-dsh-plugin/awesome-dsh-plugin）· dshmarket（github.com/dsh-market/dsh-market）
- 候选：bowenliang123/dsh-context · liustack/modsearch · liustack/modlens · dream-num/dsh-univer-office · GraySilver/dsh-evolve-modes · shengsheng90/DSH-taskboard · 1692775560/dsh-Mimir · Anionex/dsh-vision-toolkit · V1ki/dsh-plugin-subscriptions · omdsh-dev/dsh-genui → @changfenhuang/dsh-genui

---
*完整报告 · 4787d717 · 2026-09-06 · 数据截至市场扫描日 · star 随快照波动*
