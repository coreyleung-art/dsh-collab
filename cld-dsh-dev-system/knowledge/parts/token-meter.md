# 部件卡 · dsh-token-meter（token 计量）

> 填卡：2026-09-05 · 依据：官方 subsystems/token-meter.md
> 状态：learned（registry: token-meter）

## 1. 一句话定位
Replay owner for **one service-wide estimator** + isolated per-session folds：ctx.tokenMeter 以某 consumed log revision 给 detached immutable request-pressure + surface 快照。compaction 区间选择/retention 读它定价。

## 2. 概念与定义
- **TokenMeasurement**：{logRevision(=下一未读 seq), baseline(usage|estimated 锚), surfaceDeltaTokens(相对匹配锚的 signed 重定价), totalTokens(request+response 压力, 非负), surfaceTokens(surface-only route-priced=节点和), nodes(位置序)}。
- **定价**：解析 effective envelope 的 routed provider/model → ctx.llm 声明的 request-image pricing(image=visual tokens+实际发送的 model-visible text)；无声明定价 route 用固定 heuristic。
- **baseline.kind**：'usage'=最新成功 provider call 同 canonical envelope 且 total 不低于其 route-priced 锚；'estimated'=无复用锚，服务自定价全 envelope+surface。后续成功 request 替换旧锚。
- **TokenSurfaceNode**：{seq, tokens(route-priced, compaction 触发/retention/区间读它), heuristicTokens(route 无关固定, shadow-price 协议用它价替换, 保 O(1) 投影 fold 与自身 append 一致)}。
- **Surface order 权威**：replacement 节点 durable seq 可比位置序更高；snapshot 不可变，replay fold 前进不增它。

## 3. 作用与生命周期
测量每次 request 前(compaction 压力判定)；每成功 call 更新 usage 锚；fold 随事件推进重算。compaction-basic 经它 remeasure(见 compaction 卡)。

## 4. 约束（红线/不可违）
- surfaceTokens=节点和(route-priced)；totalTokens 含 response——勿混用。
- heuristicTokens 用于 shadow-price(compaction 替换价)——与 fold append 一致。

## 5. 依赖
- 依赖 ctx.llm(route pricing)/session replay；被 compaction/session 触发逻辑消费。

## 6. 规范要点（标准）
- 成本观测(大会话 token 趋势)经 tokenMeter 口径；估算与 usage 锚差异=定价边界。

## 7. 关联
- 官方：token-meter.md · 工具箱：T2(大会话内存/OOM 关联) · 路由：—
- 代码：dsh-token-meter/lib；知识：compaction 卡衔接。

## 8. 待补
- heuristic 定价表具体值。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
