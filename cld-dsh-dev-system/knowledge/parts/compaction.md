# 部件卡 · dsh-compaction（会话压缩 / 事件折叠）

> 填卡：2026-09-04 · 依据：官方 subsystems/compaction.md 全文
> 状态：learned（registry: compaction）

## 1. 一句话定位
**可选能力接缝**（capability seam）：把 agent 超长会话的历史事件压缩成摘要 + 折叠（shadowed）旧内容，控制上下文长度与 token 成本；由 Service Definition(dsh-compaction) / Provider(dsh-compaction-basic) / Consumer(dsh-command-compact) 三段组成，**不在 agent-loop 脊柱上**。

## 2. 概念与定义
- **compaction/* 事件**（log-only，不 join surface）：`compaction/start`(拿锁, turn=数值=自动轮/null=手动) → `compaction/summary`(摘要+shadowedRange+shadowedSeqs+token数+provider/model) → `compaction/end`(放锁, error?)。
- **锁语义**：锁括住**整个操作**；end 最后放——中途崩溃 → 可检测的孤儿锁（有 start 无 end），而非假 end。
- **surface 替换**：摘要搭 `user/message` 带 `surfaceOp:{op:'replace',start,end}`——compaction 唯一的 surface 变更。shadowedRange 是**位置跨距**非数值区间（replace 后 start 可 > end）；权威集是 shadowedSeqs。
- **CompactionResult**：compactionId/sourceCommandId/startSeq/summarySeq/endSeq/summary/shadowed*。
- **触发器**：`pressure`(token 压力) | `context-overflow`(确认溢出, 更激进)。
- **入口**：compactIfNeeded(自动 policy) / compactNow(空闲维护, 无有用区间返回 null) / compactRegion(显式区间)。
- **ManualCompactionErrorCode**：busy/cancelled/changed/summary/commit/persistence。
- **toolPairing**：region 边界保 tool-call/result 配对不保整轮（可压缩超大轮内早期已闭步）。

## 3. 作用与生命周期
自动：`agent/pre-step` waterfall 在 request 派生前跑 pressure compaction；qualify 后 compaction-basic 先调可选 `ctx.toolResultPruner`（压掉大 tool-result）→ 经 tokenMeter 重测 → 无摘要也能推进 surface。失败恢复走 `agent/request-error`，仅当 surface 替换代际前进才给 retry。

## 4. 约束（红线/不可违）
- 依赖 dsh-session + dsh-llm（动词作用于 agent-owned Session，摘要用 ContentBlock 词汇）。
- 摘要事件不 join surface（只有 user/message 替换会）。
- start/end 锁不互斥外部注入——手动路径只 revalidate 自己选的位置跨距。
- live unmatched start 阻塞一切入口（孤儿锁检测）。

## 5. 依赖
- 被依赖：无（可选能力）。依赖：ctx.compaction(seam) → provider 实现；ctx.tokenMeter(token 估计)；ctx.toolResultPruner(可选)；ctx.llm.stream(摘要调用)。
- consumer：dsh-command-compact（手动 /compact 命令）。

## 6. 规范要点（标准）
- **OOM 关联（本机实证方向）**：126 万事件大会话打开/扫描吃内存——compaction/裁剪是控长手段；但 compaction 本身也要调 LLM 摘要，压力下勿在 OOM 边缘自动触发。
- 排查大会话时：先查是否已 compaction（compaction/start..end 事件存在？孤儿 start？）——孤儿锁=上次崩在压缩中。

## 7. 关联
- 官方文档：`tech-research/dsh-docs/docs/subsystems/compaction.md`、token-meter.md、session.md
- 工具箱：T2(OOM)、T3(内存) · 路由表：无直接 OP（自动机制，非手动操作）
- 代码：`dsh-runtime/.../dsh-compaction{,-basic,-tool-result-pruner}/lib/`

## 8. 已知坑 / 待补
- 大会话(126万事件) 与 compaction 阈值的实证关系待查（tokenMeter 估计 vs 实际内存）。
- tool-result-pruner 默认阈值未确认（包内 config）。

## 9. 学-建-用 沉淀
- 2026-09-04：部件卡毕业；关键词入 guard-recall（检索 "compaction 孤儿锁 大会话" 可命中本卡）。
