# 端到端语音对话助手 / 语音 Agent 品类调研

> 调研日期：2026-10-11 · 视角：产品市场调研员
> 对照对象：本地语音交互体系（对话范式/电话式 · 输入法 · 记录员 · 投递）
> 纪律：只写查到出处的内容；查不到一律写「未查到」，不推测填充。延迟数字均标出处与测量条件。

---

## 结论先行（TL;DR）

1. **★ 核心问题的答案是「非独创」**。你的「电话式一问一答」与「投递」两个范式，**在 2026 年都已经有落地实现**，但**不在主流商业语音产品里，而在自托管/本地优先的开发者工具里**：
   - **AgentVoice**（原名 Cursor Voice）2026-09 已实现「列出所有 agent 会话 → 用语音把消息送进任意一个会话」，含**语音命名、序数指代（"the second one"）、语音改名、目标与投递方式回读确认**。
   - **AIfred-Intelligence** 的 "Direct Agent Addressing"：「Sokrates, what do you think about…?」→ Sokrates 作答 → TTS 读回，**四要件全中**。
   - **主流商业平台（Vapi / Retell / ElevenLabs / LiveKit / Pipecat / Bland / GoHighLevel / yellow.ai）全部做的是「呼叫转移」，不是「消息投递」**——控制权离开当前 agent，且**目标由模型或开发者配置决定，说话人无法用语音指名**。
   - **消费级音箱已经商品化了「传输半程」**：Yandex Alice 可「Алиса, передай на кухню（转达给厨房）」并指名**房间或设备名**，且能回话；百度专利 CN104951077A 明确记载「谢谢小度，**请转达豆豆**」——但收件人是**人/位置**，不是 agent。

2. **延迟上，你的 60 秒长轮询落后于市场约 2 个数量级。** 最权威的独立实测把**级联式（ASR→LLM→TTS）标准语音模式测成「每轮约 5 秒」，并直接称之为 "museum piece"（博物馆展品）**。前沿档已进入 **sub-300ms**。你的 60s 不仅是全表最慢，还比"已被判为过时"的级联方案慢 12 倍。

3. **架构上，行业已从「三段串联」明确转向「原生语音模型」**，并进一步分化出**第三档：全双工语音前台 + 后台 Agent 异步委派**（GPT-Live、Qwen-Audio-Agent）。**这一档正是你「记录员/投递」范式的行业化版本**——你的方向是对的，但工程实现晚了一代。

4. **你的真正差异点不在"电话式"本身，而在「四范式共存 + 本地优先 + 多会话定向」的组合**。单看任一范式都有先行者；四者共存、且面向本地 CLD 会话的，未查到同类。

---

## 一、品类全景：技术路线分几档

行业已形成**明确的四档**，分水岭是「文本是否作为中间表示」与「轮次由谁决定」。

### 第 0 档 · 级联三段串联（ASR → LLM → TTS）
文本是中转站。VAD 机械切音 → ASR 转写 → LLM 生成文本 → TTS 合成。
- **代表**：OpenAI 初代 Standard Voice Mode、腾讯云 TWeTalk、**绝大多数 AI 玩具**、小度/小爱（架构未公开）
- **官方定性**：OpenAI 自己把级联描述为 "speech-to-text, the LLM, and text-to-speech each ran in series. **This sequencing added latency and ignored cues such as tone and pacing.**"（[OpenAI GPT-Live 工程博客](https://openai.com/index/continuous-voice-interaction-with-gpt-live/)）
- **实测延迟**：**约 5 秒/轮**（Agora Media Lab 实测，详见第三节）

### 第 1 档 · 原生语音对话模型（Speech-to-Speech，一问一答）
模型直接吃音频出音频，**但轮次仍由外部 turn detector 决定**——本质仍是回合制。
- **代表**：GPT-Realtime 系列、Gemini Live（2.5 Flash 原生音频）、Hume EVI 3、Sesame CSM、Seeduplex、Qwen-Audio Realtime、Kimi-Audio
- **关键特征**：OpenAI 明确说这一代 "the system still relied on the turn detector to decide when inference could begin. The model handled more of the interaction, but **the interaction remained turn-based**."

### 第 2 档 · 全双工（Full-Duplex）
**去掉外部 VAD/detector，边听边说**。
- **代表**：OpenAI **GPT-Live**、字节 **Seeduplex**、**SeedRealtime**、Google **Gemini 3.8 Live**
- **官方定性**：SeedRealtime——「**轮次判断不再交给外部 VAD 规则**，而由模型基于多模态信息持续决策」（[Seed 官方博客](https://seed.bytedance.com/zh/blog/seedrealtime-audio-visual-full-duplex-llm-released-toward-omni-modal-natural-interaction)）
- **工程代价**：全双工是**网络契约**，不是模型属性。Agora 指出 "a full-duplex model can't deliver a natural experience alone: **model, serving, transport, and client have to agree on time**."

### 第 3 档 · 全双工语音前台 + Agent/后台异步委派 ★ 与你最相关
语音层只负责"在场对话"，重活异步交给后台 agent，**对话不中断**。
- **代表**：**OpenAI GPT-Live**（delegation 到 GPT-5.5）、**阿里 Qwen-Audio-Agent**（Frontend Agent + Backend Agent + Orchestration Runtime）、**Thinking Machines TML-Interaction-Small**（Interaction Model + Background Model）
- **这是你「记录员」「投递」范式的行业化形态**——但注意：**Qwen-Audio-Agent 明确说"用户面对的始终是同一个助理"，不做具名会话寻址**。

### 第 4 档（前沿研究档）· 时间对齐微轮次（Time-aligned micro-turns）
- **代表**：**Thinking Machines Lab TML-Interaction-Small**（2026-05-11），276B MoE / 12B 激活
- **机制**：以 **200ms 为粒度**把音视频切片追加进持久 GPU 序列，同时并发生成自身音频/文本/工具调用
- **数据**：turn-taking latency **0.40s** vs GPT-Realtime-2 的 **1.18s**（FD-bench V1）；新指标 TimeSpeak 64.7% vs 4.3%、CueSpeak 81.7% vs 2.9%
- **状态**：**仅研究预览**，未公开发布（[NYU Shanghai RITS](http://rits.shanghai.nyu.edu/ai/thinking-machines-unveils-interaction-models-for-real-time-human-ai-collaboration/)）

### 独立横向基准 · Artificial Analysis Speech-to-Speech Index（2026-06-23）
**这是本次调研中最有价值的跨厂商可比数据**，由三个数据集合成：Big Bench Audio（语音推理）、Full Duplex Bench（对话动态）、τ-Voice（agentic 任务完成）。权重相等。

| 模型 | 索引分 | TTFA（首音频） | 成本/小时输入音频 |
|---|---|---|---|
| GPT-Realtime-2 (High) | **77.2%** | 2.33s | $4.14 |
| Grok Voice Think Fast 1.0 | 75.7% | 1.25s | $3.00 |
| GPT-Realtime-1.5 | 72.0% | 0.82s | — |
| Gemini 3.1 Flash Live Preview (High) | 69.5% | 2.98s | $1.75 |
| Deepslate Opal | 62.1% | **0.44s**（最快） | — |
| Gemini 3.1 Flash Live Preview (Minimal) | 56.6% | — | **$1.50**（最低） |

> **两个必须记下的行业现实**：
> ① **τ-Voice 是所有模型最难的一维，全部低于 53%**（Grok 最高 52.1%，GPT-Realtime-2 High 仅 39.8%）。即"语音 agent 真能办事"目前普遍不成立。
> ② **该榜单未收录任何中国模型**（豆包/元宝/Kimi/Qwen 均不在列），因此国产产品的横向比较只能依赖各自口径不一的厂商自述。
> 来源：[Artificial Analysis](https://artificialanalysis.ai/articles/announcing-the-artificial-analysis-speech-to-speech-index)

---

## 二、逐产品对比表

> 说明：**「定向」= 能否用语音把一条消息发给指定的 agent/会话/收件人**；**「多 Agent」= 是否支持多 agent/多会话路由**。
> 时延单位 ms 或 s。**「未查到」= 检索无果，不等于不存在。**

### 2.1 模型 / API 层

| 产品 | 端到端延迟 | 真端到端? | 打断? | 定向? | 多 Agent? | 定价 | 备注 |
|---|---|---|---|---|---|---|---|
| **OpenAI GPT-Live** | 实测 **~1.1s 确认 / 1.4s 让位**（Agora 2026-07-09，iPhone 13，n=30） | ✅ 原生全双工 | ✅ 但**让位慢 498ms**（蓄意设计：先判断是不是真打断） | ⚠️ **间接**（见 §2.4） | ✅ delegation 到 GPT-5.5 | 按秒计费 + 后台模型另计 | 2026-07-08 发布；API 一度 waitlist |
| **OpenAI Realtime API (gpt-realtime-2.1 / GPT-Realtime-2)** | **1.12s**（minimal reasoning）→ **2.33s**（high） | ✅ 原生 S2S | ✅ | ❌ 无 | ⚠️ SDK 支持 handoff（模型决定） | **$32/$0.40/$64** per M 音频 in/cached/out；文本 $4/$0.40/$24 | 官方明说"低于 500ms 才适合实时交互"，即**自身偏慢** |
| OpenAI 级联 Standard Voice Mode | **~5s/轮**（Agora 实测） | ❌ 三段串联 | ✅ 但"任何声音都算打断" | ❌ | ❌ | — | 已停产，被称 "museum piece" |
| **Google Gemini Live (3.8 Live)** | **亚秒级**（官方）；**2.0 Live API 时代官方给过 "600ms 首 token"** | ✅ 原生 | ✅ **但 3.8 改为"礼貌中断降级"**——用户说话时等到 WHEN_IDLE | ❌ | ⚠️ 异步函数调用 + Extended Thinking | **$0.75/M in, $4.50/M out**（Vercel AI Gateway） | GA 2026-09-15；24kHz 音频 + 24FPS 虚拟形象 |
| **Anthropic Claude 语音模式** | **未查到** | ❌ **明确是回合制** | ⚠️ hands-free + push-to-talk | ❌ | ❌ | 计入常规用量配额，全档可用 | 官方原文："**Voice mode takes turns, meaning Claude listens, pauses to think, and then responds.**" |
| **字节 Seeduplex** | 无绝对值；判停 **−250ms**、打断响应 **−300ms**（相对半双工） | ✅ 原生，"原生端到端的建模方式" | ✅ 「瞬间停止回复并平滑收声」 | ❌ | ❌ | 未查到 | 2026-04-09；豆包 App 全量 |
| **字节 SeedRealtime** | **未查到**（仅"节奏问题 −50%"） | ✅ 原生音视频全双工，去外部 VAD | ✅ | ❌ | ❌ | 未查到 | 2026-08-05；官方把"更低延迟"列为**未来工作** |
| **月之暗面 Kimi-Audio** | **未查到** | ✅ 原生 S2S（服务端拆 5 个服务） | 未查到 | ❌ | ❌（有 Agent Swarm，无语音路由） | 未查到 | 开源 7B，13M+ 小时音频预训练 |
| **阿里 Qwen-Audio Realtime** | **未查到绝对值** | ✅ 官方定义 "end-to-end real-time voice interaction model" | ✅ | ❌ | ⚠️ 见 Qwen-Audio-Agent | 3.1-plus 音频出 **$24/M**；3.0-flash 音频出 $1.696/M | 三种轮次模式：server_vad / smart_turn / push-to-talk |
| **腾讯元宝 Hunyuan-Voice** | **1.6s**（**唯一公布绝对值的国产**） | ✅ 端到端语音通话模型 | 未查到 | ❌ | ❌ | 未查到 | 数据来自 2025-05，**已陈旧约 17 个月** |
| **腾讯云 TWeTalk** | AI 对话 **1000ms** / TRTC 传输 300ms | ❌ **明确级联**（"STT/LLM/TTS 全流程流式处理"） | ✅ 双讲机制 | ❌ | 仅多模型热切换 | 未查到 | 硬件方案，非消费产品 |
| **Hume EVI 3** | 官方仅"conversational latency"无数字；SambaNova 案例 **100–300ms** | ✅ **同一模型处理转写+语言+语音** | ✅ 盲测含 interruption quality 且胜 GPT-4o | ❌ | ❌ | 约 **$0.07/min**（另有分档） | 盲测七维度全面优于 GPT-4o |
| **Sesame CSM** | **sub-300ms**（媒体口径）；官方只写"削减每一毫秒" | ✅ 端到端多模态 | ⚠️ 部分证实（可 mid-sentence pivoting） | ✅ **4 具名 agent** 各有独立记忆与权限 | ✅ agent 可协调其他 agent | 预览期免费；GA 后未查到 | 8.3B backbone + ~300M decoder；$250M B 轮 |
| **Thinking Machines TML-Interaction-Small** | **0.40s** turn-taking（vs GPT-Realtime-2 1.18s） | ✅ 时间对齐微轮次 | ✅ 原生并发 | ❌ | ❌ | 未发布 | **仅研究预览**，2026 年内有望扩大 |
| **阿里 Wan-Streamer** | **模型侧 ~200ms**，+350ms 网络 = **总 ~550ms** | ✅ 单 Transformer 音视频全双工 | ✅ | ❌ | ❌ | 未查到 | 流式单元 160ms @ 25fps（[arXiv 2606.25041](https://arxiv.org/html/2606.25041v1)） |

### 2.2 消费级产品 / 独立产品

| 产品 | 端到端延迟 | 真端到端? | 打断? | 定向? | 定价 | 备注 |
|---|---|---|---|---|---|---|
| **Pi (Inflection)** | **未查到** | **未查到** | **未查到** | **未查到** | 消费端免费；API 面议 | 2026-07 回归消费市场，推 Pi Journeys；只说 "improved voice" |
| **Character.AI Character Calls** | **未查到**（官方仅 "reduced latency"） | **未查到**（前身 Character Voice 确认是 TTS） | ✅ 但**是按按钮打断，非语音** | ❌ | 免费档含基础通话；c.ai+ **$9.99/月** | CEO 2026-10 出走迪士尼，无继任者 |
| **Sesame Personal Agents** | **sub-300ms** | ✅ | ⚠️ | ✅ **4 agent 各带一台 computer** | 预览免费 | 2026-10 GA（iOS+Android）；创始人称**团队用语音指挥 Devin/Claude Code/Codex 会话** |
| **Amazon Alexa+** | **未查到**（有用户投诉延迟增加） | ⚠️ 官方称 "voice-first unified pipeline"（Nova 2 Sonic） | ✅ 兼容 Echo Show 上**无需唤醒词** | ❌ | Prime 免费；非会员 **$19.99/月** | 2026-02-04 全美铺开 |

### 2.3 硬件

| 产品 | 状态 | 延迟 | 备注 |
|---|---|---|---|
| **Humane AI Pin** | ❌ **已彻底死亡** | — | 2025-02-18 停售，**2025-02-28 15:00 ET 停服**，设备退化为电子钟表；HP 以 **$1.16 亿**收购 CosmOS + 团队 + 300+ 专利（**不是收购产品线**）|
| **Rabbit R1** | ⚠️ **硬件已停产**，公司仍运营 | 首发实测**实景拍摄至少等 20 秒**；官方从未公布 | 2025-07 起曝停薪、10 月罢工；CEO 向 Wired 确认 R1 停产，转 OS3 + Cyberdeck（目标 ~$500）。**注意：可确认"停产"，不能确认"公司倒闭"**（两说并存） |
| **AI 玩具**（BubblePal ¥389 / Fuzozo ¥399…） | ✅ 爆发中（中国市场 2026 >¥300 亿） | 云厂商宣称 **1.5s 闭环**；**记者实测半数近 4 秒**；从业者承认 3–4 秒 | ❌ 典型**云端级联**："玩具本身几乎没有本地智能"；**普遍不支持打断**；退货率 30%–40% |

### 2.4 ★ 定向投递能力专项表（最关键）

| 产品 | 说话人**用语音指名**目标? | 目标 agent 作答? | 回复**语音读回**? | 状态 |
|---|---|---|---|---|
| **AIfred-Intelligence** (Peuqui) | ✅ **"Sokrates, what do you think…?"** | ✅ | ✅ | **四要件全中**；自托管开源；agent 是同一本地系统的多个**人格** |
| **AgentVoice** (dixonSolutions) | ✅ 自动双词名 / **序数 "the second one"** / **语音改名 "call that one billing"** | ✅ | ✅（含**投递状态朗读**） | **已实现（2026-09）**；自托管 OSS；npm `@ratitisrad/agentvoice`；iPhone **CallKit**（真电话 UI）或 PWA |
| **ChatGPT Voice 桌面版** (OpenAI) | ⚠️ **有旁证，官方文档未查到明确措辞** | ✅ | ✅ | 2026-07-23，build 26.715；OpenAI 官方推文：**"direct multiple agents running in ChatGPT Work or Codex, using just your voice"**；Impress：**「他スレッドの作業を調整」** |
| **agentwire-dev** | ⚠️ 多会话 + 语音层，指名机制未查到文档 | ✅ | ✅ | "Multi-session voice web interface for AI coding agents"，"every session is a window" |
| **voice-tunnel** | ❌ 单会话 | ✅ | ✅ | 本地 STT/TTS；"**The tunnel's own half of the round trip is about a second**" |
| **Qwen-Audio-Agent** (阿里) | ❌ **明确不做**："用户面对的始终是同一个助理" | ✅ 后台 agent | ✅ | 研究 harness；**支持 DeepSeek Harness 原生 ACP 后端** |
| **Yandex Alice / Station** | ✅ **"Алиса, передай на кухню"**——可指名**房间或设备名** | ❌ 收件人是**人** | ✅ 且**可回话** | **消费级已商品化的最接近形态** |
| **百度专利 CN104951077A** | ✅ **「谢谢小度，请转达豆豆」** | ❌ 收件人是**人** | ✅ 含语音回传路径 | 2015 年申请，**已专利化** |
| **Vapi / Retell / ElevenLabs / LiveKit / Pipecat / Bland / GoHighLevel / yellow.ai** | ❌ **目标由模型或开发者配置决定** | — | — | **做的是「呼叫转移」不是「消息投递」**；LiveKit 原文："the original agent **doesn't participate afterward**" |
| **openclaw PR #41603** | ✅ 唤醒词绑定 agentId（"Hey Sasha"→main） | ✅ | ✅ | ⚠️ **未合并的 PR**，评审发现 2 个正确性 bug，未在 macOS 编译运行 |

**★ 明确判定**：
- **主流商业多 agent 语音平台，没有任何一家**允许说话人**用语音指名**目标 agent，并在**保留自己通道**的同时拿回该 agent 的语音回答——它们的 handoff/transfer 是**相反操作**（控制权离开）。
- **「传输半程」（说话 → 指名目的地 → 在彼端读出）在消费级音箱中已完全商品化并已专利化**，但收件人是**人/位置**。
- **「agent 半程」（具名 AI agent 作答 → 语音读回）只在单一助手形态中商品化**。
- **两者组合目前只存在于自托管/本地优先项目（AIfred、AgentVoice）与一个未合并 PR**，**不在任何商业多 agent 语音平台中**。

> 因此：**你的「投递」范式不是独创概念，但它的完整组合在商业产品中仍是空白**。这是一个"有先行者、无商业竞品"的位置。

---

## 三、★ 技术路线对比：三段串联 vs 原生语音模型

### 3.1 三选一的架构决策（OpenAI 官方给出的分类法）

OpenAI 自己的 [Voice agents 文档](https://platform.openai.com/docs/guides/voice-agents) 把架构分成三选一，**这是目前业界最清晰的分类法**：

| 架构 | 官方定位 | 适用 |
|---|---|---|
| **Chained voice pipeline**（STT → agent → TTS） | "Inspect or transform **intermediate text** and replace each component independently" | 需要在文本层做策略检查、审计、录存 |
| **Realtime API**（单会话 S2S） | "Use one model to interpret audio, decide what to do, and respond in speech" | 对话即时感优先 |
| **GPT-Live**（全双工 + 独立后端委派） | "Keep your existing text workflow and choose its backend independently while the conversation continues" | **保留已有的文本 agent 体系**，只把语音当前台 |

**关键洞察**：OpenAI 把"保留已有文本 workflow、只加语音前台"独立成第一类架构，并提供 **client delegation**——"connect any model, agent harness, or service your application runs"。**这几乎就是你的"桥 + 本地 Python 后端 + CLD 会话"结构的官方等价物。**

### 3.2 延迟 / 成本 / 可控性 三维对比

| 维度 | 级联三段串联 | 原生语音模型（一问一答） | 全双工 + 后台委派 |
|---|---|---|---|
| **实测延迟** | **~5s/轮**（Agora，OpenAI 标准语音模式） | 0.44s–2.98s TTFA（AA 榜单区间） | ~1.1s 确认 / 1.4s 让位（GPT-Live 实测） |
| **延迟下界** | 三段延迟叠加，无法压缩 | 受 turn detector 拖累 | 受网络与 barge-in 往返约束 |
| **成本结构** | 三段分别计费（ASR 按分钟 + LLM 按 token + TTS 按字符） | 音频 token 计费，**音频出贵** | 语音按时长 + 后台模型单独计费，**双计** |
| **成本示例** | Vapi 估算模型：转写按分钟 + LLM 按 token + 音色按**字符** | GPT-Realtime-2 音频出 **$64/M**；Qwen 3.1-plus 音频出 **$24/M** | GPT-Live 会话按秒 + 后台模型 token |
| **可控性** | ★★★ 每段可替换、可审计、可插策略 | ★ 黑盒，文本不可见 | ★★ 前台黑盒 + 后台可控 |
| **保真度** | ✗ 丢语调/停顿/情绪 | ✓ 保留韵律与情绪 | ✓ |
| **抗丢包** | ✗ 一包丢=管线卡住 | 中 | ✓ **实测 10% 丢包仅 +314ms**（级联式前代 +2448ms） |
| **打断** | 靠 VAD 机械判断，**任何声音都算打断** | 有 detector，仍回合制 | ✓ 全双工，且**能区分真打断** |

### 3.3 三个必须内化的实测结论（Agora Media Lab，2026-07-09）

**方法**：iPhone 13，ChatGPT v1.2026.183，Plus 账号，人工嘴播放预录语料（每轮输入完全相同），双轨波形记录，n=30/条件，全部数据取自波形而非秒表。

1. **"响应快"与"结束快"是两件事**。GPT-Live 中断后 **498ms** 才静音（比前代**慢**），但它**拒绝了 30/30 次假打断**（咳嗽、背景人声），前代只拒绝 20/30，级联式全部误停。**"让位慢"是蓄意设计，不是退步。**
2. **真正跨代的不是中位数，是方差**。GPT-Live 中位数仅赢前代 **205ms**，但 **σ 从 489ms 塌缩到 104ms（约 5 倍）**，P90 仅比中位数高 104ms（前代 P90 达 2318ms）。**人脑把"稳定性"读作"自然"。**
3. **★ 延迟被"重新分配"而不是被消除**。需要检索/推理时，GPT-Live 先说 "let me check that"，同时 GPT-5.5 后台工作——**首个声音来得很早，但答案并没有更早**。
   → **Agora 提出「三个时钟」框架，这是本次调研最有价值的工程概念**：
   - **确认起始**（acknowledgment onset）
   - **实质答案起始**（substantive-answer onset）
   - **答案完成**（answer completion）
   > 对照：Agora 此轮只测了第一个。**你的「60 秒未回则朗读一句提示语」本质上是一个"确认时钟"的实现——但触发点是 60 秒，而市场基准是 1.1 秒。**

**人类基线**：日常对话轮次转换约 **200ms**（Stivers et al., PNAS 2009，经 Agora 引用）。

### 3.4 延迟分档速查

| 档位 | 量级 | 代表 | 用户体感 |
|---|---|---|---|
| 已过时 | **~5000ms** | OpenAI 级联 Standard Voice Mode | "对方在发呆" |
| 慢但可用 | 1600ms | 腾讯元宝 Hunyuan-Voice | 明显延迟 |
| 当前主流 | **1100–1400ms** | GPT-Live 确认/让位 | 可接受 |
| 好 | 440–820ms | Deepslate Opal 0.44s / GPT-Realtime-1.5 0.82s | 顺畅 |
| 优秀 | **<300ms** | Sesame、Hume、Seeduplex(~320ms)、Wan-Streamer(~200ms) | 接近自然 |
| 人类基线 | **~200ms** | Stivers et al. PNAS 2009 | — |

---

## 四、★ 与我们的对照

### 4.1 我们的「电话式一问一答」在市场中的位置

| 维度 | 我们的设计 | 市场位置 | 判定 |
|---|---|---|---|
| **交互形态** | 按住说话 → 单请求单响应 → TTS | 属**第 0/1 档**（回合制） | ⚠️ 落后一代：市场已进全双工 |
| **延迟** | **60 秒长轮询**，超时朗读提示语 | **全表最慢**。比"已被判过时"的级联式（5s）还慢 **12 倍** | 🔴 **最大风险点** |
| **打断** | 未提及 | 竞品普遍支持；GPT-Live 已做到"区分真假打断" | 🔴 缺失 |
| **文本中间层** | 有（ASR→LLM→TTS） | 第 0 档 | ⚠️ 但**换来了可控性**（见下） |
| **定向投递** | 「投递」说会话名 | 商业产品空白；自托管有先行者 | 🟢 **有效差异点** |
| **本地优先** | 本地 Python 后端 + 本地/云端 LLM 混合 | 竞品几乎全云端；自托管阵营存在 | 🟢 **有效差异点** |
| **多范式共存** | 4 种（输入法/记录员/投递/电话式） | **未查到同类** | 🟢 **最独特之处** |

### 4.2 我们缺什么

1. **🔴 延迟策略（最严重）**。60 秒轮询在架构上无法通过优化追上市场。**必须拆成两个时钟**：
   - **确认时钟**：按下说话后 **~300ms–1.1s** 内必须出声（"收到，正在处理"），而不是等 60 秒。
   - **答案时钟**：可以慢，但需**可感知进度**。
   > Agora 的"三个时钟"框架可直接照搬。

2. **🔴 打断（barge-in）**。竞品最低标准已支持；GPT-Live 更进一步做到**抗误打断**（背景人声 30/30 拒绝）。若走"电话式"路线，至少需要让用户在等待中能插话取消。

3. **🟡 轮次判定**。Seeduplex/Qwen 的 `smart_turn` 已做到"呃/嗯等填充音不打断对话"，"面对思考停顿耐心等待"。**我们的"按住说话"实际上是把判停责任完全交给用户**——这规避了问题，但也失去了自然感。

4. **🟡 会话上下文容量**。Qwen-Audio 明确限制"最多 50 轮 / 累计 300 秒音频"，超出自动丢弃。**我们需要自己的等价策略**（会话内/跨会话记忆边界）。

5. **🟡 抗丢包/弱网**。GPT-Live 在 10% 丢包下仅 +314ms，前代 +2448ms。**60 秒轮询在弱网下的行为未定义**。

6. **🟡 定向的"确认与诚实投递"**。AgentVoice 做了两件我们可能没做的好事：
   - **回读确认**："read back target, delivery method and message"
   - **诚实投递状态**：`live | mailbox_pending | queued_next_turn | forked | refused`，且"the voice agent says which happened"

### 4.3 我们多了什么（真实优势）

1. **🟢 四范式共存的组合**。单看"电话式"有 AgentVoice/voice-tunnel；单看"定向"有 AgentVoice/AIfred；单看"记录员"有 Qwen-Audio-Agent。**但四者共存于一套本地体系、面向个人多会话工作流的，未查到同类。**

2. **🟢 本地优先 + 混合 LLM**。商业竞品（OpenAI/Google/Anthropic/豆包）**全部闭源、不可自托管**（VentureBeat 明确指出 OpenAI 桌面语音 "the model weights, voice processing pipelines, and agent state architectures remain fully closed. Organizations cannot modify or self-host"）。我们与 AgentVoice/voice-tunnel/AIfred 同属本地优先阵营，但**它们都是单范式工具**。

3. **🟢 "投递"的语义比竞品更完整**。竞品的 handoff 是**转移控制权**，我们是**投递内容并取回结果**——这在语义上更接近 LiveKit 的 **supervisor/Task 模式**，而 LiveKit 官方承认该模式的回答由 supervisor **复述**，不是 specialist 原声。

4. **🟢 输入法范式（转写→成稿→人工发）几乎是空白**。未查到同类语音产品做"人工二次确认后发送"这一档——**这是被市场忽略的、认知负荷与准确率的中间解**。

### 4.4 一句话定位

> **我们的「电话式」在交互形态上落后市场一代（回合制 + 60s 延迟），但「投递」+「四范式共存」+「本地优先」的组合在商业市场是空白。**
> **正确的做法不是追赶全双工，而是把「电话式」重新定义为一个"低延迟确认 + 异步答案"的委派通道，并强化「投递」的确认与诚实状态回传。**

---

## 五、可借鉴的具体做法

### 5.1 立即可借鉴（低改造成本，高收益）

| # | 做法 | 来源 | 对我们的动作 |
|---|---|---|---|
| 1 | **三时钟框架**：确认起始 / 实质答案起始 / 答案完成 分别测量与优化 | Agora Media Lab | 把"60s 提示语"改成"300ms–1.1s 确认音"，并分别埋点三个时钟 |
| 2 | **诚实投递状态**：`live / queued / forked / refused`，且**语音说出实际发生了什么** | AgentVoice doc 37 | 投递范式加投递状态回传，且**失败必须说失败**（与我们 R030 无验证不陈述一致） |
| 3 | **回读确认**：投递前回读"目标 + 投递方式 + 内容" | AgentVoice doc 37 | 高影响投递（跨会话发指令）加确认门；低影响（记录员）可免 |
| 4 | **语音命名 + 序数指代 + 语音改名**：双词名、`"the second one"`、`"call that one billing"` | AgentVoice doc 37 | 给 CLD 会话自动生成可朗读名，支持序数与改名——**这比说会话 id 自然得多** |
| 5 | **抗误打断**：不把任何声音都当打断，需累积证据才让位 | GPT-Live（498ms 蓄意延迟换 30/30 抗误停） | 若做 barge-in，**优先抗误触发而非最快让位** |
| 6 | **异步委派 + 会话不停**：`spawn_thinking` 提交自包含目标，立即回 task id，对话继续 | Qwen-Audio-Agent（arXiv 2609.25195） | **这正是"记录员/投递"的正确形态**：提交即返回，结果后到 |
| 7 | **"说话即打断"与"取消任务"解耦** | Qwen-Audio-Agent | 打断朗读 ≠ 取消后台任务；结果保留到合适时机再播 |
| 8 | **弱网优先于峰值**：优化抖动（σ）而非中位数 | Agora（σ 489→104ms） | 长轮询改事件推送；把"稳定可预测"当第一指标 |

### 5.2 架构决策借鉴

| # | 做法 | 说明 |
|---|---|---|
| 9 | **照抄 OpenAI 的三分类法**做架构文档 | Chained / S2S / 全双工+委派。我们目前横跨三者，明确归类有助于取舍 |
| 10 | **client delegation 模式** | OpenAI 允许"connecting any model, agent harness, or service your application runs"——**与我们的"本地后端 + CLD 会话"同构**，可作为对外解释的行业标准语言 |
| 11 | **语音前台可插拔** | Qwen-Audio-Agent 支持 Qwen Realtime / GPT-Live / Gemini Live / Seeduplex / StepAudio / 本地 HF speech-to-speech / MiniCPM-o 七种前台，**且已原生接入 DeepSeek Harness ACP**。**值得评估直接复用其 Gateway 而非自建桥** |
| 12 | **前后台模型解耦** | GPT-Live 的教训：语音层"不需要是楼里最聪明的模型，它需要快、可打断、善于路由"。**我们不必让同一个模型既对话又办事** |
| 13 | **两档委派（Responses / client）** | 简单任务托管、复杂任务自管——对应我们的"记录员 vs 投递"分工 |
| 14 | **会话历史有界** | Qwen: 最多 50 轮/300 秒。**我们必须显式定义自己的上界**，否则上下文会无声劣化 |

### 5.3 值得直接研究/复用的开源实现

| 项目 | 价值 | 链接 |
|---|---|---|
| **Qwen-Audio-Agent** | 与我们架构最同构；**已支持 DeepSeek Harness ACP**；前台可插拔 | [GitHub](https://github.com/QwenAudio/qwen-audio-agent) · [README_ZH](https://raw.githubusercontent.com/QwenAudio/qwen-audio-agent/master/README_ZH.md) · [arXiv 2609.25195](https://arxiv.org/html/2609.25195v1) |
| **AgentVoice** | **定向投递 + 语音命名 + 诚实状态**的唯一成熟实现；CallKit 电话 UI | [GitHub](https://github.com/dixonSolutions/AgentVoice) · [doc 37](https://github.com/dixonSolutions/AgentVoice/blob/HEAD/docs/37-session-directory-and-inject.md) |
| **voice-tunnel** | 极简单请求单响应桥，秒级往返，全本地 STT/TTS | [GitHub](https://github.com/JuanjoFuchs/voice-tunnel) |
| **AIfred-Intelligence** | 「Direct Agent Addressing」四要件全中；每 agent 独立 TTS 配置 | [GitHub](https://github.com/Peuqui/AIfred-Intelligence) |
| **agentwire-dev** | 多会话语音 cockpit，"每个会话是一扇窗" | [PyPI](https://pypi.org/project/agentwire-dev/) · [agentwire.dev](https://agentwire.dev) |

### 5.4 明确**不要**照抄的

| 反面模式 | 为什么 |
|---|---|
| **把"任何声音"当打断 | GPT-Live 用 498ms 换 30/30 抗误停；级联式的"快而常错"是已知缺陷 |
| **只优化中位数延迟** | 真正被感知的是方差。σ 从 489→104ms 比中位数赢 205ms 更有价值 |
| **承诺绝对延迟却不给测量条件** | 本次调研中大量厂商只给相对改进量（豆包 −250ms/−300ms）或干脆不给（Kimi/Pi）。**我们不应对客户犯同样的错** |
| **把厂商自述当事实** | 阿里文档称 Qwen 3.0-flash "ranked #1 globally in Artificial Analysis benchmark"，但 AA 2026-06 榜单**未收录任何 Qwen 模型**——夸大表述 |

---

## 六、存疑 / 查不到的（如实列出）

### 6.1 关键问题上的证据边界

| 事项 | 状态 |
|---|---|
| OpenAI **官方文档**是否明确"可用语音指名 agent" | **未查到**。OpenAI 官方推文确认 "direct multiple agents"，Impress 称「他スレッドの作業を調整」，Codex 知识库给出 `"Tell the frontend thread to switch from Tailwind to vanilla CSS"` 等示例——**但后者是第三方知识库，非 OpenAI 官方文档**。**结论：能力有官方背书，指名语法仅有二手来源。** |
| AIfred-Intelligence 的成熟度 | 仅凭 README 级证据；**agent 是同一系统的多个人格，不是独立会话/任务**，与我们的"CLD 会话"不等价 |
| AgentVoice 是否逐字朗读**目标 agent 的回复** | 文档保证的是**投递状态**的朗读与 `get_agent_status` 的详细输出缓冲；**逐字回读目标的回复不是文档化保证** |
| openclaw PR #41603 | **未合并**，评审发现 2 个正确性 bug，未在 macOS 编译运行——**不计为已落地** |
| 学术界是否研究过该课题 | **未查到**。MMA2A（arXiv:2604.12213）按模态路由、llmvoice（arXiv:2609.04288）、OneVoice（arXiv:2609.31673）均非该主题 |

### 6.2 产品数据缺口

**完全未查到，不做任何推测**：
- Pi 的时延 / 架构 / 打断 / 定向能力（**全部未查到**）
- Character.AI Character Calls 的时延数字与双向架构
- Claude 语音模式的端到端延迟
- Kimi 语音通话的时延/架构/定价，**以及线上是否仍用 2025-04 的 Kimi-Audio**
- Qwen-Audio Realtime 的绝对 S2S 延迟
- 豆包 Seeduplex/SeedRealtime 的**绝对**端到端延迟
- Rabbit R1 的官方时延数字与 barge-in
- Alexa+ / 小度 / 小爱同学的官方毫秒级时延
- 元宝 Hunyuan-Voice 的打断支持表述
- **上述所有产品的「会话定向」能力（豆包/Kimi/Qwen/元宝：全部未查到）**
- 豆包、Kimi、元宝、TWeTalk 的按分钟 API 定价

### 6.3 存疑 / 需交叉验证

1. **⚠️ 豆包 "320ms 端到端延迟"** —— 来自机锋网（[gfan.com](https://www.gfan.com/info/598745.html)）**二手转述**，字节官方博客**未给绝对值**，只给相对改进量。**不可当官方数据引用。**
2. **⚠️ Qwen "全球第一"** —— 阿里文档称 qwen-audio-3.0-flash "ranked #1 globally in Artificial Analysis Speech-to-Speech benchmark"，但 AA 2026-06-23 榜单前四为 GPT-Realtime-2 / Grok / GPT-Realtime-1.5 / Gemini 3.1 Flash Live，**未列任何 Qwen 模型**。Qwen 自家文章说的是 **Preview 版**在 2026 年 5 月**分项指标**登顶——**与"整体榜第一"是两回事，厂商表述有夸大嫌疑。**
3. **⚠️ SeedRealtime 自认延迟未达标** —— 官方把"更低的延迟"列入"未来突破"，与营销口径的"流畅"需分开看。
4. **⚠️ 元宝 1.6s 数据陈旧** —— 来自 2025-05，距今约 17 个月，且为厂商对照级联方案的自测值。
5. **⚠️ Rabbit 是否"已倒闭"两说** —— 36Kr 2026-02 称资金链断裂倒下；36Kr 2026-03、第三方评测 2026-08、Wired 转述的 2026-09 创始访谈均显示公司仍运营。**可确认"R1 已停产"，不能确认"公司已倒闭"。**
6. **⚠️ HP 收购措辞** —— 应为"收购**大部分业务/核心技术**（CosmOS + 团队 + 300+ 专利）"，**不是**"收购 Humane 公司"或"收购 AI Pin 产品线"。中文报道多有表述过宽。
7. **⚠️ Sesame sub-300ms** —— 仅见于媒体 AlphaSignal，**官方博客未给数字**。
8. **⚠️ Hume 定价分档** —— 来自 CostBench（自述 45% confidence、单来源），**低置信度**；仅 $0.07/min 与媒体口径一致。
9. **⚠️ Alexa+ Nova 2 Sonic "单步处理音频并生成语音"** —— 出自第三方投研内容（自带免责声明）。**AWS 官方文档未使用"端到端取代级联"措辞**，只称 "unified speech understanding and generation architecture"。
10. **⚠️ TWeTalk 数字来源层级低** —— 300ms/1000ms 来自大会材料聚合文章，且**混合了传输延迟与全链路延迟两种口径**。
11. **⚠️ AI 玩具销量** —— BubblePal ">30 万台"（i黑马）vs ">350,000 台"（XINDITAI），口径不一；"全球第一"为**厂商自述**。
12. **⚠️ 中国产品普遍缺席独立语音评测** —— AA Speech-to-Speech Index **未见豆包/元宝/Kimi/Qwen 上榜**，横向比较只能依赖各自口径不一的厂商自述。

### 6.4 噪音排除记录（按调研纪律）

| 被排除来源 | 排除理由 |
|---|---|
| `opc.csdn.net/6a2bd821f874c425c6a000ea.html`（"ChatGPT语音模式与腾讯元宝通话的技术对比"） | **典型 AI 拼凑文**：编造 `yunbao.tencentcloudapi.com` 端点与"实测"表格（GPT-Voice 0.78s / YB-Call 0.65s），时间戳 2026-01 却用 2024 年的 `gpt-4o-realtime` 与 `OpenAI-Beta: realtime=v1` 头。**无作者资质、无可复现方法，全文剔除。** |
| `zhuanlan.zhihu.com` 相关页（403 Forbidden） | 无法读取全文，**不作为证据**，仅在能交叉验证时引用其标题级信息 |
| `benchlm.ai/voice-benchmarks/...` | 404，**不作为证据** |
| 各类"AI 玩具销量第一"厂商通稿 | 厂商自述，**无第三方核实**，已标注 |
| `layer3labs.io`（Rabbit/Humane 评测页） | 第三方评测站，**非一手来源**；其 Humane 停服时间与中文一手报道一致故可采信，Rabbit 描述标注来源层级 |

---

## 附：核心来源清单

**一手 / 官方**
- [OpenAI — How we built a realtime system for responsive voice AI in six months（GPT-Live）](https://openai.com/index/continuous-voice-interaction-with-gpt-live/)
- [OpenAI — How OpenAI delivers low-latency voice AI at scale（WebRTC 架构）](https://openai.com/index/delivering-low-latency-voice-ai-at-scale/)
- [OpenAI API — Voice agents（三分类法）](https://platform.openai.com/docs/guides/voice-agents) · [Getting started with GPT-Live](https://developers.openai.com/api/docs/guides/live) · [Delegation and tools](https://developers.openai.com/api/docs/guides/live-delegation)
- [Google — Gemini 2.0 Multimodal Live API（600ms 首 token）](https://developers.googleblog.com/en/gemini-2-0-level-up-your-apps-with-real-time-multimodal-interactions/)
- [Google Cloud — Gemini 3.8 Live 开发者指南](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-live?hl=zh-cn)
- [Anthropic — Think through hard problems in voice mode](https://claude.com/blog/think-through-hard-problems-in-voice-mode) · [Use voice mode](https://support.claude.com/en/articles/11101966-use-voice-mode)
- [字节 Seed — Seeduplex 发布](https://seed.bytedance.com/zh/blog/introducing-seed-full-duplex-speech-llm-attentive-listening-robust-interference-suppression-enabling-more-natural-interaction) · [SeedRealtime 发布](https://seed.bytedance.com/zh/blog/seedrealtime-audio-visual-full-duplex-llm-released-toward-omni-modal-natural-interaction)
- [阿里云 — Qwen-Audio realtime 用户指南](https://www.alibabacloud.com/help/en/model-studio/qwen-audio-realtime-user-guides)
- [Hume — Introducing EVI 3](https://www.hume.ai/blog/introducing-evi-3)
- [Vapi — Squad Handoff 文档](https://github.com/VapiAI/docs/blob/main/fern/squads/handoff.mdx)
- [AgentVoice doc 37 — 用语音向运行中的会话投递](https://github.com/dixonSolutions/AgentVoice/blob/HEAD/docs/37-session-directory-and-inject.md)
- [Qwen-Audio-Agent 技术报告（arXiv 2609.25195）](https://arxiv.org/html/2609.25195v1) · [README_ZH](https://raw.githubusercontent.com/QwenAudio/qwen-audio-agent/master/README_ZH.md)
- [Wan-Streamer（arXiv 2606.25041）](https://arxiv.org/html/2606.25041v1)
- [Dialogflow — Explicit Invocation（"talk to <name>" 定向调用）](https://developers.google.cn/assistant/df-asdk/discovery/explicit?authuser=0&hl=en)

**独立实测 / 基准**
- [Agora Media Lab — GPT-Live 延迟实测（2026-07-09，n=30）](https://prod.agora.io/es/blog/openai-didnt-publish-gpt-lives-latency-so-we-measured-it)
- [Artificial Analysis — Speech to Speech Index（2026-06-23）](https://artificialanalysis.ai/articles/announcing-the-artificial-analysis-speech-to-speech-index)
- [DeepLearning.AI The Batch — GPT-Realtime-2 评测](https://www.deeplearning.ai/the-batch/openai-challenges-speech-to-speech-leaders)

**行业媒体 / 分析**
- [VentureBeat — OpenAI 桌面语音全双工（2026-07-23）](https://venturebeat.com/orchestration/agentic-coding-goes-hands-free-as-openai-brings-gpt-lives-full-duplex-voice-control-to-codex-and-chatgpt-on-the-desktop)
- [Codex KB — Hands-Free Agent Orchestration（含语音指名线程示例）](https://codex.danielvaughan.com/2026/07/24/codex-gpt-live-voice-control-desktop-multi-agent-coordination-hands-free-coding/)
- [Impress AI Watch — ChatGPT Voice 桌面版（2026-07-24）](https://ai.watch.impress.co.jp/docs/news/2127627.html)
- [NYU Shanghai RITS — Thinking Machines 交互模型](http://rits.shanghai.nyu.edu/ai/thinking-machines-unveils-interaction-models-for-real-time-human-ai-collaboration/)
- [AlphaSignal — Sesame iOS 发布（4 agent / sub-300ms）](https://alphasignal.ai/news/sesame-launches-ios-voice-ai-app-with-4-distinct-agents-and-sub-300ms-responses)
- [经济参考网（新华社）— 腾讯混元 Voice 1.6s（2025-05-22）](http://www.jjckb.cn/20250522/491d0216ff594c499a5c93afe580d79c/c.html)
- [IT之家 — Rabbit 停薪调查（2025-11-14）](https://www.ithome.com/0/897/562.htm)
- [澎湃 — Humane AI Pin 停服（2025-02-20）](https://www.thepaper.cn/newsDetail_forward_30193375)
