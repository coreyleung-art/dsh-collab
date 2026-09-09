# 调研派单 · 内容/资源优化论文与方案（守灯 → 4787d717 数据调查员）

> 发起：守灯（CLD 健康审查）· 2026-09-02
> 状态：待调研 · 优先级：P1（关联 CLD-020 处置）
> 执行方：session-4787d717（数据调查员，research-pipeline）

## 背景
CLD（Electron/Node 宿主）内存问题：
- CLD 主进程 2.2GB（曾 3.78GB V8 heap OOM 崩溃，CLD-020）
- swap 高位历史（92% on 16GB → 现已缓解至 61% on 3GB）
- 多 Helper/Worker 常驻（Lark×3/Feishu/Coze/CLD Renderer）

用户要求：查「内容/资源优化」所有相关论文与解决方案（宿主进程内存/上下文/资源管理优化）。

## 调研范围（论文+工程；先 papers-db 再 web_search；官方文档优先 J46）
1. Electron/Node.js V8 堆内存管理与 OOM 缓解（heap 上限、CALL_AND_RETRY_LAST、GC 调优、snapshot/deserialization）
2. worker_threads 并发与内存边界（Worker 数限制、SharedArrayBuffer、隔离）
3. LLM/agent 上下文/会话状态累积压缩优化（context compaction、token 预算、状态快照/摘要——关联 CLD-017）
4. 长驻进程内存泄漏检测治理（heap snapshot 对比、leak 模式、Electron 常见泄漏源）
5. 系统级内存压力/swap 缓解（macOS memory purge、压缩内存、jetsam）
6. 资源优化综合落地清单（Electron 宿主可行方案）

## 产出要求
1. 结论综述 + 按可行性分级（立即/短期/中期）解决方案清单
2. 论文依据标注（题目/作者/年份/核心方法）+ 工程来源（官方文档/issue URL）
3. 落盘 ~/dsh-collab/research/memory-resource-optimization/ + 入知识库（摄取/ChromaDB）
4. 回报守灯：结构化摘要（Top 5 可行方案 + 依据 + 预期收益）

## 合规
- 被动应答执行（非定时任务，符合成本治理/R027）
- 入库标注来源（J46）；论文筑基（理论/方案论证）
- 完成后回报，守灯并入 CLD-020 处置
