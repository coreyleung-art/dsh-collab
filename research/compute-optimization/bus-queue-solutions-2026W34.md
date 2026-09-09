# 多智能体会话上下文膨胀 / 总线排队 解决方案调研 · 2026-W34

> 调研：数据调查员 · 2026-08-17
> 基线：bus-queue-mechanism-analysis.md（~/dsh-collab/）
> 方法：18 次中英文 web_search（框架官方文档 / 论文 / 社区分析）+ 本机实测（~/.dsh 配置、agent-bus.json、session.jsonl.zstd、插件市场索引、预设清单）
> 置信度标注：**【高】**=官方文档/一手实测；**【中】**=多源交叉一致或权威第三方；**【低】**=单源/社区分析/待验证

---

## 结论摘要（问题本质 + 关键解法）

**问题本质**：DSH 会话上下文「只增不减」——每个会话（含推理碎片、tool 调用、工具结果、inbox 拼接实体）永久保留并全量重注入。实测 3b5efeef 会话 10701 条中，推理碎片(3249)+assistant 块(2734)+tool-call 块(1699)合计 7682 条 ≈ **71.8%（72%）**；总上下文 239MB；处理变慢 → inbox 逐条 splice（160 次）→ 新消息排队（69 条 queued）→ 成本随 inputTokens 膨胀。**根因不是总线锁，而是上下文膨胀放大了每个会话的处理时间，队列只是结果。**

**关键解法（按杠杆排序）**：
1. **会话压缩/摘要（compaction）**：官方/主流框架（Claude Code /compact、OpenHands Context Condenser、LangGraph summarization）一致做法——长会话折叠为结构化摘要 + 保留近期原文窗口。**DSH 本机已内置整套 compaction 插件**（@deepseek-ai/dsh-compaction-basic + dsh-command-compact + dsh-compaction-tool-result-pruner，默认预设 liangshen/librarian/waimai-ops 均已挂载），但存量会话 preset=standard 未挂载 → 从未触发压缩。
2. **工具结果裁剪**（72% 体积大头）：OpenAI Agents SDK 内置 ToolOutputTrimmer、DSH 自带 pruner（阈值 8192 字符，头 4096 / 尾 1024）——大输出落盘 + 行号引用，只回摘要/diff。
3. **队列批处理 + 优先级**：总线已有 10 分钟去重（dedup 机制），缺「批量合并 + 优先级」——重启唤醒类消息应聚合为单条广播而非 18 条逐条排队。
4. **上下文缓存**：DeepSeek 缓存命中价 ¥0.05-0.30/百万 vs 未命中 ¥1.5-3.0/百万（差 30 倍）——保持前缀稳定即可大幅降本。

---

## ① LLM agent 会话上下文管理最佳实践

**现状（业界共识）**
- 三大流派：**滑动窗口截断**（零成本但丢早期事实）、**LLM 摘要压缩**（compact/condense，保留语义但引入摘要漂移）、**外部记忆（RAG）**（只注入检索片段，但引入检索误差）。实践中多采用「摘要 + 滑动窗口」混合：早期历史折叠为滚动摘要，近期保留原文窗口（Microsoft Q&A 明确推荐该组合）【中】。
- 系统提示瘦身：固定前缀按每次调用计费，Anthropic 曾砍 Opus 系统提示 80%；Claude Code 文档列出启动即占上下文的大头（CLAUDE.md、memory、技能描述、MCP 工具名）【高】。
- 触发式压缩优于人工：Claude Code /autocompact 支持阈值配置（社区分析：上下文达 ~95% 时自动触发）【中，官方文档确认存在 /compact 与 /autocompact，95% 阈值来自社区反编译分析】。

**方案**
- 分层：系统提示/工具定义 = 常驻前缀（配合缓存）；最近 N 轮 = 原文；更早 = 滚动摘要；跨会话事实 = 外部记忆库。
- 压缩时保留：目标/约束/决策/未完成任务/关键数字；丢弃：过程性推理链、已消费的工具结果。

**置信度**：高（Claude Code 官方文档、OpenHands 官方文档、LangGraph/langmem 官方文档一致）；具体阈值数字为中。

## ② 推理碎片 / tool 调用存储优化（72% 体积）

**现状**
- 推理碎片（reasoning-chunks 3249 条）与 assistant 块（2734 条）+ tool-call 块（1699 条）合计占 3b5efeef 会话 **71.8%** —— 与社区观察一致：agent 循环中工具输出/中间推理是上下文膨胀主因【高，本机实测】。
- 主流框架做法：
  - **OpenAI Agents SDK**：内置 ToolOutputTrimmer（call_model_input_filter），自动裁剪旧轮次的大工具输出【高，官方源码】。
  - **AgentScope**：Agent 类支持 tool result compact；官方文档有「上下文压缩」章节【高】。
  - **Eino (CloudWeGo)**：middleware_toolreduction 中间件做工具结果缩减【中】。
  - **DSH 自带**：dsh-compaction-tool-result-pruner，配置 thresholdChars=8192 / headChars=4096 / tailChars=1024（保留头尾）【高，本机预设实测】。

**方案**
- 工具结果三层处理：① 短结果（<8k 字符）原样保留；② 长结果裁剪头尾；③ 超长输出落盘 + 行号/摘要引用。
- 推理碎片：仅保留结论层（final reasoning），中间链压缩存储、不注入上下文；或按任务分级 reasoningEffort（简单任务 low）。
- 结构化结果（JSON）压缩存储（去空白/去冗余字段），同一轮多次 tool call 的结果聚合为单条摘要。

**置信度**：高（本机实测 + OpenAI/AgentScope 官方机制一致）。

## ③ 消息队列批处理 / 优先级 / 限流

**现状（本机实测）**
- agent-bus.json：213 线程、4417 delivered、**69 queued**；queued 构成 = 重启恢复·唤醒批量广播 + ui 通道确认。
- 消息字段：id/thread/from/to/text/time/status/kind —— **无 priority、无 batch、无 group 字段**；按到达顺序逐条投递。
- 已有机制：**10 分钟同发件人+同线程+同内容去重**（agent_send 返回 status: duplicate）、红绿灯锁（当前 0 锁 0 waiting，锁层通畅）。
- 行业做法：RMQ 支持合并+优先级的消息队列；agent-kernel 有 queue-mode（优先级队列）；Letta 有 queue runtime；OpenClaw messages 文档把 queueing 列为会话级概念【中】。

**方案**
- **合并（coalescing）**：同一 from+主题（如「重启唤醒·18 会话验证」）在短窗口内合并为 1 条聚合消息/广播，而不是 18 条独立排队 —— 直接消除当前 queued 主体。
- **优先级**：restart-wakeup 类批量高优但合并投递；ui-ack/确认类低优延迟批量；实时任务（外卖告警/客服）最高优。
- **限流**：per-session 投递速率限制（如 1 msg/2s），避免单会话 inbox 瞬间爆满；重启恢复时按会话分批唤醒（如 5 个/批）。
- **去重升级**：内容相似去重（同主题不同文本 → 合并为最新一条）。

**置信度**：现状高（本机实测）；方案为中（行业模式，未在 DSH 落地）。

## ④ openclaw / Claude Code / 其他 agent 框架的上下文管理

| 框架 | 机制（依据） | 置信度 |
|---|---|---|
| **Claude Code** | /compact 手动压缩为摘要；/autocompact 阈值自动压缩（社区：~95% 上下文触发）；/clear 清空；system prompt + 工具定义作为稳定前缀配合 prompt caching；官方文档《Explore the context window》《session management and 1M context》 | 高（官方文档+社区反编译交叉） |
| **OpenHands** | Context Condenser：把早期事件 LLM 摘要化，保留近期事件原文；condenser 接口可插拔默认实现（PR #5306）；官方博客《OpenHands Context Condensation》 | 高（官方文档） |
| **LangGraph / langmem** | Checkpoint 存完整状态 + SummarizationNode 把旧消息折叠为摘要，配合 Redis 持久化 | 高（官方文档） |
| **CrewAI** | 三层记忆：短期（RAG 上下文）、长期、实体记忆；单会话内膨胀控制弱于 Claude Code | 中 |
| **Mem0 / Letta (MemGPT)** | 外部记忆层：MemGPT 把 LLM 当 OS 管理虚拟内存层级（上下文分页）；Mem0 做跨会话事实抽取与检索注入 | 中 |
| **OpenClaw** | 官方 messages 文档含 queueing/会话概念；社区 issue 提出 Skills/Compression/Caching/RAG 上下文管理方案与持久化 Memory Bank（survive compaction/restart）；memclaw 社区实现 cortex memory 引擎 | 中（文档 snippet，未抓全文；检索到的 openclaw 生态与任务所指框架的一致性**待查证**） |

**共性结论**：主流框架全部采用「摘要替代全量 + 保留近窗口 + 可插拔策略」；Claude Code 与 OpenHands 是 DSH 可对标的两套实现。

## ⑤ 上下文摘要化记忆方案

**现状**
- **滚动摘要（rolling summary）**：每 N 轮把旧对话折叠为一段摘要，替代全量历史；问题：摘要漂移（summarization drift）——早期事实逐步丢失（社区/论文提及）【中，单源论文待验证】。
- **分层记忆（hierarchical）**：短期原文窗口 → 中期滚动摘要 → 长期外部库（向量/结构化）；hierarchical-context-ai-agent 宣称 100+ 轮对话保持 95% 事实保留（单源，**待验证**）【低】。
- **外部记忆库 RAG**：CrewAI 短期记忆即 RAG 检索注入；Mem0/Letta 做事实级记忆；DSH 本机已有 knowledge-chunks.sqlite（Chroma 向量库）+ knowledge.json，具备现成底座【高，本机实测】。

**方案（针对 DSH）**
1. 会话内：滚动摘要替换 >N 轮历史（保留：目标/决策/未完成任务/关键数字；丢弃：推理链/已消费工具结果）。
2. 会话间：跨会话事实（角色档案、资源归属、任务状态）写 knowledge 库，会话只注入检索片段 —— 避免每个会话重复携带全量协作历史。
3. 归档：冷会话导出为摘要文档 + zstd 压缩（存储已是 zstd），从注入路径移除原文。

**置信度**：滚动摘要/分层记忆 = 中（多框架采用但保真需实测）；外部记忆 = 高（DSH 已有向量库底座）。

## ⑥ DSH 是否已有相关配置/开关

**本机实测结论：有，且相当完整（重点发现）**

1. **compaction 插件族已存在于插件市场与预设**（~/.dsh/market/index.json）：
   - npm:@deepseek-ai/dsh-command-compact —— 显式 /compact 斜杠命令【高，本机索引】
   - npm:@deepseek-ai/dsh-compaction —— 抽象 compaction 服务缝（ctx.compaction）【高】
   - npm:@deepseek-ai/dsh-compaction-basic —— token-meter 驱动的压缩策略 + LLM 摘要后端【高】
   - npm:@deepseek-ai/dsh-compaction-tool-result-pruner —— 工具结果裁剪（thresholdChars=8192, head=4096, tail=1024）【高，三个预设均含此配置】
   - 第三方 dsh-auto-compact（github: Zh-U-hB/dsh-auto-compact）—— 默认 256K 阈值自动压缩【中，第三方待评估】
2. **默认预设已挂载 compaction 组**：liangshen / librarian / waimai-ops 的 agent.cordis.yml 均含 compaction 组（compaction-basic + command-compact + tool-result-pruner），并带注释说明 tokenMeter 在 host 平面【高，本机实测】。
3. **存量会话未受益**：3b5efeef 会话首行 "agentPreset":"standard" —— 该会话创建于默认预设切换前，未挂载 compaction → 与 10701 条、239MB 直接相关【高，本机实测；机制推断待查证】。
4. **contextWindow**：session_projcache.json 中模型 contextWindow=1000000（1M）—— 是模型能力声明，不是压缩开关【高，本机实测】。
5. settings.yaml 无 compact/truncate 键；~/.dsh 全局配置中未发现自动压缩阈值开关（除第三方插件）——**自动触发的默认阈值/行为待查证**（compaction-basic 的 token 阈值未在本地配置文件中可见，可能在插件包内）。

---

## 对我方 DSH 网络的可落地建议（P0 / P1 / P2）

### P0 —— 本周立即做（零/低改动，收益最大）

1. **为存量长会话启用 compaction（最高杠杆）**
   对 de7b29de（21.1MB）、fa1f9150（18.6MB）、aa528267（15.4MB）、b241741f（14.4MB）、3b5efeef（3.1MB/10701 条）执行 /compact（或等价触发 compaction-basic）。
   - 新会话默认预设已含 compaction（liangshen）；存量 standard 预设会话需确认挂载或重建。
   - 预期：单会话注入上下文降 **90%+**（只剩摘要 + 近期窗口）；后续每次调用的 inputTokens 按同比例降。
2. **全局启用工具结果裁剪**
   确认 tool-result-pruner 在所有会话生效（thresholdChars=8192/head=4096/tail=1024 已配置）；对 bash/grep/read 输出追加单次 ≤2000 token 约定，超长落盘 + 行号引用。
   - 预期：72% 体积中工具结果部分降 **50-70%**；上下文总量 239MB → <100MB。
3. **总线消息合并 + 优先级（消除 69 条 queued）**
   - 重启唤醒：18 会话验证清单合并为 1 条广播（或 5 个/批分批唤醒），而非 18 条逐条排队。
   - 消息结构增加 priority 字段：restart-wakeup=高优但合并、ui-ack=低优延迟批量、实时告警=最高优直投。
   - 去重升级：同主题不同文本在 5 分钟窗口内合并为最新一条（现有 10 分钟同内容去重保留）。
   - 预期：queued 峰值 69 → **<10**；inbox spliced 160 → <20。
4. **上下文缓存利用**
   保持 system prompt/工具定义/预设指令为稳定前缀（顺序不变、不夹易变内容），抽查 usage 中缓存命中占比。
   - 预期：inputTokens 成本降 **50-70%**（DeepSeek 命中 ¥0.05-0.30 vs 未命中 ¥1.5-3.0/百万，差 30 倍）。

### P1 —— 下周推进

5. **滚动摘要 + 归档策略**：>50k 条或 >3 个月的会话做滚动摘要归档；归档后从注入路径移除原文，改为「滚动摘要 + 最近 N 轮原文 + 按需 RAG 检索」。
6. **推理碎片降噪**：reasoningEffort 按任务分级（简单会话 low、复杂 high）；reasoning-chunks 只保留结论层，中间链压缩存储不注入。
7. **外部记忆库**：把跨会话事实（角色/资源/任务状态）迁入已有 knowledge 库（knowledge-chunks.sqlite + Chroma），会话只注入检索片段，减少跨会话重复携带。
8. **per-session 投递限流**：1 msg/2s 级别限速，避免单会话 inbox 瞬间爆满；与优先级配合。

### P2 —— 评估后做

9. **LLMLingua 压缩**：长文档一次性注入/离线批处理场景用 LLMLingua（官方 20x 压缩、1M prefill 延迟降 10x），注意保真度与压缩器二次开销，先做 A/B。
10. **dsh-auto-compact 自动压缩**：第三方插件（默认 256K 阈值）评估可信度与安装方式后启用，实现无人值守自动 compact。
11. **冷数据迁移**：历史会话导出摘要 + 保留 zstd 存储，从活跃注入路径移除；容量与检索策略见 resource-capacity 系列文档。

**预期总效果（估算）**：上下文总量 239MB → <30MB；单会话注入 token 降 70-90%；queued 峰值降 90%；云端 inputTokens 成本降 50-70%（缓存+裁剪+摘要叠加）。

---

## 证据来源

**官方/一手**
- [Claude Code — Explore the context window](https://code.claude.com/docs/en/context-window)（/compact、/autocompact、上下文构成）
- [Claude — Using Claude Code: session management and 1M context](https://claude.com/blog/using-claude-code-session-management-and-1m-context)
- [OpenHands — Context Condenser](https://docs.openhands.dev/sdk/guides/context-condenser) / [Condenser arch](https://docs.openhands.dev/sdk/arch/condenser) / [PR #5306](https://github.com/OpenHands/OpenHands/pull/5306)
- [LangChain langmem — Summarization](https://langchain-ai.github.io/langmem/guides/summarization/)
- [CrewAI — Memory](https://docs.crewai.com/v1.11.0/en/concepts/memory)
- [LLMLingua 官网/论文](https://llmlingua.com/llmlingua.html)（最高 20x 压缩、1M prefill 10x）
- [Anthropic — Prompt caching](https://claude.com/blog/prompt-caching)（缓存读按基础价 10%、写 +25%/5min 或 +100%/1h）
- [OpenAI Agents SDK — ToolOutputTrimmer 源码](https://github.com/Aphroq/openai-agents-python/blob/f078581d221b3337ff9b1558cdeb07e250312b89/src/agents/extensions/tool_output_trimmer.py)
- [AgentScope — 上下文压缩文档](https://java.agentscope.io/v2/zh/docs/harness/compaction.html) / [tool result compact PR #1585](https://github.com/agentscope-ai/agentscope/pull/1585)
- [OpenClaw — Message flow/queueing 文档](https://docs.openclaw.ai/concepts/messages.md) / [openclaw 上下文管理 issue #2](https://github.com/JnBrymn/openclaw/issues/2)

**社区/第三方分析**
- [Claude Code from scratch — 07-context（snip/microcompact 策略）](https://github.com/Windy3f3f3f3f/claude-code-from-scratch/blob/main/docs/07-context.md)
- [Claude Code 设计指南 — compaction](https://github.com/6551Team/claude-code-design-guide/blob/main/part5/15-compact.md)
- [claude-code-best — compaction.mdx](https://github.com/claude-code-best/claude-code/blob/main/docs/context/compaction.mdx)
- [OpenHands Context Condensation 博客](https://openhands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents)
- [Microsoft Q&A — Summarized Context + Sliding Window](https://learn.microsoft.com/en-us/answers/questions/2259997/is-summarized-context-sliding-window-the-best-memo)
- [hierarchical-context-ai-agent（100+ 轮 95% 事实保留，单源待验证）](https://github.com/koladilip/hierarchical-context-ai-agent)
- [Agentic memory HEMA 分析（arxiv 2504.16754）](https://github.com/lhl/agentic-memory/blob/32e2bec4f65aa1286c81b6866fe815d7a61b71c2/ANALYSIS-arxiv-2504.16754-hema.md)
- [RMQ — 支持合并和优先级的消息队列](https://developer.aliyun.com/article/780217) / [agent-kernel queue-mode 指南](https://github.com/yaalalabs/agent-kernel/blob/develop/docs/docs/advanced/queue-mode-guide.md) / [Letta queue runtime (DeepWiki)](https://deepwiki.com/letta-ai/letta-code/6.3-queue-runtime)
- [Elastic — 智能体记忆与上下文管理](https://www.elastic.co/cn/search-labs/blog/agentic-memory-management-elasticsearch)

**本机一手证据**
- ~/dsh-collab/bus-queue-mechanism-analysis.md（基线：239MB、10701 条、72%、69 queued、160 spliced）
- ~/.dsh/agent-bus.json（69 条 queued 实测样本：重启唤醒广播 + ui 确认；消息无 priority/batch 字段；dedup 列表）
- ~/.dsh/sessions/--Users-coreyleung--/session-3b5efeef-*/session.jsonl.zstd（10714 行；首行 agentPreset=standard）
- ~/.dsh/.agent-presets/{liangshen,librarian,waimai-ops}/agent.cordis.yml（compaction 组：compaction-basic + command-compact + tool-result-pruner 8192/4096/1024）
- ~/.dsh/market/index.json（dsh-command-compact / dsh-compaction / dsh-compaction-basic / dsh-compaction-tool-result-pruner / dsh-auto-compact）
- ~/.dsh/storages/session_projcache.json（contextWindow=1000000，模型能力声明）
- ~/.dsh/settings.yaml（agent-presets.default: liangshen；无 compact/truncate 键）

## 噪音排除记录
- 搜索到的「Mem0 vs Letta / 记忆系统 2026」等营销向文章仅作方向佐证，未采信具体数字。
- github XIAOHAY/agentdesk、alekbot-core 等项目与主题相关性低，未采信。
- arxiv 2603.07670（summarization drift）编号异常（远期时间戳），仅标注存在该观点、**未采信具体数据**。

---

## 待查证清单

1. **compaction-basic 触发条件/默认阈值**【2026-08-18 已部分实测解决】：DEFAULT_THRESHOLD_RATIO=0.8（1M contextWindow → 800k token 触发）、DEFAULT_RETAIN_RATIO=0.16、maxTokens=8192、auto 默认 true（runtime 包 v0.1.0-rc.6 源码实测）。结论：官方自动压缩默认阈值过高，当前会话水位远达不到 → 从未自动触发；手动 /compact 是否受 0.8 门控仍待实测。详见 compaction-official-vs-auto-compact.md。
2. **standard 预设是否确无 compaction**：3b5efeef agentPreset=standard 与 10701 条的直接因果（推断强，未验证运行时行为）。
3. **存量会话挂载 compaction 后是否需重建/迁移**：插件组随 preset 挂载，存量会话是否热生效待查证。
4. **bus 批量投递能力**：agent-bus.json 消息结构未见 priority/batch 字段，但宿主可能有未落盘的调度逻辑（需查 DSH 源码，本机 runtime checkout 仅有 node_modules，无源码）。
5. **dsh-auto-compact 插件**（github: Zh-U-hB/dsh-auto-compact）：可信度、安装方式、与 compaction-basic 的冲突关系未验证。
6. **Claude Code 95% 自动压缩阈值**：社区反编译结论，非官方文档原文。
7. **DeepSeek 缓存命中实测**：官方价格表有缓存命中价，本网络实际命中率未统计（建议抽查 usage.cache_read 占比）。
8. **LLMLingua 在 DeepSeek 长上下文场景的保真度**：需离线 A/B。
9. **OpenClaw 上下文管理细节**：本次仅拿到文档 snippet 与 issue 标题，未抓全文。
10. **hierarchical-context 95% 事实保留、summarization drift 论文**：单源/编号存疑，需独立验证。

*报告 v0.1 · 数据调查员 · 2026W34*
