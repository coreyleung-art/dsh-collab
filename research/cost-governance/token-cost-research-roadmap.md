# Token 成本优化 · 技术/学术路径路线图

> 建立：2026-08-19 · HR 驾驶舱（承接 agent-token-cost-open-source-research.md 调研）
> 原则：每条路径先 2-4 人天 PoC 实测（省 token 数/成本/质量不降级）再扩；不重复造轮子

---

## 一、全景：4 族 10 路径

| 族 | 路径 | 机制 | 代表作品 | 预期收益 | 优先级 |
|---|---|---|---|---|---|
| A 用量侧 | A1 提示压缩 | 压缩输入 prompt | LLMLingua/LLMLingua-2（ICLR'24）、Gist Tokens、Local-Splitter T2 | 长上下文省 20-80% | P1 |
| A 用量侧 | A2 上下文工程/裁剪 | 分层/裁剪/编辑上下文 | Claude context editing、claude-code-context-pruner、compaction、OneDragon 上下文分层 | 省 30-60% | P1 |
| A 用量侧 | A3 语义缓存 | 相似请求缓存命中 | Local-Splitter T3、LiteLLM 缓存 | 重复问题≈0 成本 | P2 |
| A 用量侧 | A4 本地路由/小模型分流 | 本地模型前置判路由 | Local-Splitter T1、我们模型分层 v0.2（qwen3.5-2b/llama-3-8b 已装） | 编辑/解释类省 45-79% | **P0** |
| B 通信侧 | B1 通信压缩/剪枝 | 跨会话 KV 共享/渐进剪枝 | KVCOMM（NeurIPS'25）、Q-KVComm、SafeSieve（AAAI） | 治 ack 风暴放大器 | P2 研究 |
| B 通信侧 | B2 消息批处理/预算化路由 | 合并回执、角色分配 | MOC（ICML'26）、Budgeted Multi-Agent Routing（IEEE） | ack 减半+（已落地纪律=第一刀） | P1 纪律/ P3 形式化 |
| C 缓存推理 | C1 缓存保活经济 | 热缓存 keepalive | Keepalive Economics（2607.19214）、Tail-Optimized Caching | 命中价差 30-60 倍 | P1 |
| C 缓存推理 | C2 KV cache 压缩/共享 | 长会话缓存压缩 | H2O（ICML'24）、KVCOMM、Q-KVComm | 长会话内存/重发成本 | P3（宿主层依赖） |
| D 治理预算 | D1 硬预算/熔断 | 事前上限+circuit breaker | agent-cost-guardrails、Runcap、tokenbudgetorchestrator | 防失控兜底 | **P0** |
| D 治理预算 | D2 精确可观测/计量 | 用量 API/网关计量 | Langfuse、openmeter、llm-accounting | 精确口径 | P1 |
| D 治理预算 | D3 经济价值评估 | ROI 坐标+防护带 | ai-roi-value-matrix.md（已交付） | 防误判/决策 | ✅ 已建月结 |

## 二、推荐组合与叠加预期

**路线**：A4 + D1（P0，立即可做）→ A1/A2 + C1（P1）→ A3/B2（P2）→ B1/C2（P3 跟踪）

**叠加收益参考**（论文实测）：
- Local-Splitter：T1+T2（本地路由+压缩）= 编辑/解释类省 45-79%；全套含草稿审 = RAG 类省 51%
- Keepalive：热缓存输入价差 30-60 倍
- ack 纪律：agent_send 占比 61.8% → 目标腰斩
- 综合（保守）：**云 token 削减 50-75%** 为现实目标（质量不降级前提下）

## 三、投入预算（人天）

| 路径 | PoC | 说明 |
|---|---|---|
| A4 本地路由 | 3-5 人天 | qwen3.5-2b 前置：识别「编辑/解释类」请求本地消化；Ollama 已通 |
| D1 硬预算 | 2-3 人天 | 评估 agent-cost-guardrails 适配 DSH 工具面（替代 gov quota 自研） |
| A1 提示压缩 | 3-4 人天 | LLMLingua 在长文档/长会话输入前置压缩，质量抽样 |
| A2 上下文工程 | 3-4 人天 | 会话分层裁剪（对照 DSH 内置压缩插件族启用） |
| C1 缓存保活 | 2-3 人天 | 长会话 keepalive 策略 + 缓存命中率观测 |
| B2 消息合并 | 2 人天 | ack 纪律量化复盘（对比 08-19 前后 agent_send 占比） |

**合计首期 ≈ 15-21 人天**（非连续，穿插日常），月度复盘调优。

## 四、评估门槛（每条路径放行标准）

1. 实测省 token ≥ 20%（或成本 ≥ 20%）
2. 输出质量不降级（抽查/QA 对比）
3. 维护成本可控（不引入新基础设施依赖，除非必要）
4. 与 J37/红绿灯/成本治理指令不冲突
5. 达标才扩；不达标记录数据后暂停（不硬撑）

---
*依据：Local-Splitter（2604.12301）、Keepalive Economics（2607.19214）、LLMLingua（ICLR'24）、KVCOMM（NeurIPS'25）、MOC（ICML'26）、Budgeted Multi-Agent Routing（IEEE）、SafeSieve（AAAI）、H2O（ICML'24）、Claude context editing 文档、agent-cost-guardrails/Runcap/openmeter 等开源项目*

## 五、执行进度（2026-08-19 更新）

| 路径 | 状态 | 进展 |
|---|---|---|
| D1 硬预算 | 🔄 评估完成 | **选型结论=不引入新系统**：启用 gov quota per-agent 配额 + 借鉴 TBO 超限分级（block/fallback/warn）+ 日重置；配额起步 ¥75/日/agent（7 月日均 ×3），月复盘校准；详 d1-hard-budget-evaluation.md |
| 峰值归因 | ✅ 完成 | 8/17-18 ¥1,426=协调风暴 40%×台账 run_code 35%×自动化 25%；8/18 反推 ~10.7B token（日均 8 倍）；8/19 治理后 ¥5.79 验证归因 |
| 精确计量 | ✅ 接入 | DeepSeek 平台导出（7 月 ¥745.79 / 8 月 ¥1,906.04 / 峰值 ¥678-748 / 治理后 ¥5.79）；计量常态化=P0（平台导出周期化） |
| A4 本地路由 | ⏳ 设计待启动 | PoC 设计：qwen3.5-2b 前置识别「编辑/解释类」请求→本地消化；测量=省 token/成本+质量抽样；成本治理指令下先做设计、恢复后实测 |
| A1/A2 压缩裁剪 | ⏳ 待 A4 后 | 依赖 DSH 内置压缩插件族评估 + LLMLingua PoC |
| C1 缓存保活 | ⏳ 低优先 | 精确数据已证缓存命中 98%——保活边际收益有限，聚焦减重发量（A 族） |
| B2 ack 纪律复盘 | ⏳ 待一周数据 | 08-19 起执行，一周后对比 agent_send 占比（目标 61.8%→30%以下） |
