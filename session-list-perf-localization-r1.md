# session.list 性能缺陷源码级定位（R1）

- **贡献会话**: session-43b1a2d3-3b77-41ed-aa9e-effcef446af3
- **日期**: 2026-08-17
- **状态**: 定位完成（只读取证，无代码变更）；根治待上游 patch / backlog
- **关联**: 会话列表全量投影累计延迟（40s+，手机+桌面会话列表不可用）

## 现象
- session.list / session.search RPC 120s+ 无响应（0 字节），直连 / 代理 / 移动端 /m 通道均复现
- session.history（含 676k 事件大会话）正常（0.5–0.75s）；workspace.list / session.models / GET / events.mux 正常
- 宿主侧逐会话 readSurface 实测：大会话阻塞分布 aa528267(2.3s) / fa1f9150(1.2s) / 7b8381dc(848ms) …

## 代码路径（runtime @deepseek-ai，版本 0.1.0-rc.6）
```
POST /api/session.list 或 /m/api/session.list
→ dsh-host-apiproxy listVisibleSessionSummaries  (lib/types/api-proxy.js:1455)
  ├─ attached（内存）会话: summarizeAttached —— 廉价
  └─ cold（持久化）会话: 每会话 summarizeCold (api-proxy.js:494)，批次 COLD_SUMMARY_BATCH_SIZE=16
       ├─ 投影: listProjectionsFor → sessionProjectionCache.cachedSnapshot(meta)
       │    （缓存仅 3 条目/79 会话 → 多数 miss → 投影块缺省，非主成本）
       └─ blank 探测: probeColdSessionMetadata (api-proxy.js:~510)
            ├─ stat(path) 大小 ≤ coldBlankProbeMaxBytes ?
            └─ persistence.readFrom(id, 0)  ←★ 全量读日志（zstd 全流解压 + sessionListMetadata 全事件 fold）
                 —— 每个 cold 会话、每次 session.list 都重跑，无列表时记忆化
```

## 根因（三要素叠加）
1. **列表时 blank 探测全量读**：probeColdSessionMetadata 对每个 size 未超限的 cold 会话执行
   `persistence.readFrom(id, 0)` = 整条日志解压 + 全事件 fold，用于判定 blank/updatedAt；
2. **无列表级记忆化**：该探测结果不写投影缓存（sessionProjectionCache 只在会话活动时写入，
   writeEveryEvents=200 / writeIntervalMs=5000），每次列表重复全量计算；
3. **大会话放大**：79 会话含 676k 事件级大会话，单会话 fold 0.5–2.3s，累加 40s+。

> 注：协调方宿主侧 sessionQuery.listSessions 曾测得 192ms（轻路径）与 40s（深层探测）两种结果，
> 与「依赖缓存/会话 attach 状态、成本不稳定」一致——wire 路径的 blank 探测是稳定复现的主成本。

## 根治方向（backlog）
1. **blank 探测结果入持久化投影缓存**（identity-checked，文件变更失效）——首次列表计算，后续 O(头行读取)；
2. **流式早停探测**：zstd 分块解压，读到首个用户/助手事件即判 blank，避免全量 readFrom(0)；
3. **列表缺省 header-only、投影按需懒加载**（代码注释已表明设计意图：无投影行是降级而非破损）；
4. 短期缓解：归档/清理冷会话（79→N）、调大 coldBlankProbeMaxBytes 跳过超大会话探测；
5. 批次并发已为 16（Promise.allSettled），CPU 解压在线程池竞争，可评估限流防延迟尖峰。

## 相关文件（runtime）
- dsh-host-apiproxy/lib/types/api-proxy.js（listVisibleSessionSummaries / summarizeCold / probeColdSessionMetadata）
- dsh-session-projection-cache/lib/index.js（cachedSnapshot / writeEveryEvents / writeIntervalMs）
- dsh-session-query/lib/index.js（listSessions / listPersisted）
- dsh-session-persistence-jsonl/lib/index.js（listArtifacts / readFirstZstdLine / readFrom）
- dsh-host-apiproxy/lib/types/api/sessions.schema.js（session.list 响应带 projections 块）

## 延迟基线测量协议（重启前后对比用，session-43b1a2d3 担当）
- 命令：POST /api/session.list，body {"type":"client-request","rpcId":"bl","method":"session.list","payload":{}}，计时 -w "code=%{http_code} time=%{time_total}s bytes=%{size_download}"
- 采样：直连 127.0.0.1:<GUI端口> ×3 + 经代理 127.0.0.1:3081（Host: 100.120.203.20:3081）×3，取中位数；超时 60s
- 重启前基线（实测）：直连/代理均 >120s 0 字节（超时中止）
- 重启后预期：记录三组数据（冷缓存首次 / 热缓存二次 / 经代理），供 backlog 量化

## 验证证据
- 多通道复现：直连 51960 / 代理 3081 / 移动端 /m/api（配对 cookie）均 >120s 0 字节
- 并发两个 session.list 均阻塞（无串行化，同时挂起）
- 对照：session.history(0.5s) / workspace.list(200) / session.models(200) / events.mux(426)
- 协调方宿主侧 readSurface 逐会话耗时分布
