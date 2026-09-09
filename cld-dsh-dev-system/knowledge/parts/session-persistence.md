# 部件卡 · dsh-session-persistence（会话持久化 JSONL/zstd）

> 填卡：2026-09-04 · 依据：官方 persistence.md + session.md + 2026-09-04 会话消失实证
> 状态：learned（registry: session-persistence）

## 1. 一句话定位
会话事件日志（append-only SessionEvent）的**持久化接缝（durability seam）**：抽象服务 `ctx.sessionPersistence`（create/open/stat/list），shipped provider = `dsh-session-persistence-jsonl`（zstd 压缩 JSONL）。

## 2. 概念与定义
- **SessionHandle**：对某会话的"唯一门"——所有读写走 handle，单写者所有权（第二 open(write) → SessionAlreadyOwnedError；closed handle 操作 → SessionHandleClosedError；read handle 上 mutation → SessionReadOnlyError）。
- **flush checkpoint**：append 是 best-effort，只有 resolve 的 flush 才承诺跨崩溃存活（write-behind 有界批处理窗口）。
- **SessionHeader**：日志旁的不可变元数据（id/cwd/createdAt…），create 时固化。
- **manifest 布局**：`~/.dsh/sessions/<projectKey(cwd)>/<encodeSegment(id)>/session.<suffix>`；suffix = `.jsonl.zstd`(zstd) 或 `.jsonl`(none)；无 cwd → `_no-cwd/`。
- **zstd 帧纪律**：**首帧必须恰含一行 header**（assertZstdHeaderFrame），首帧多行 → "corrupt Zstandard session log"；materialize = header 行 + 首批事件分帧写。
- **torn tail**：不完整末帧可恢复（tornStart + recoveredEvents），doctor/repair 会修。
- **compression 配置**：`JsonlCompressionSchema` zstd/none，默认 zstd；oppositeCompression 检测物理编码冲突。

## 3. 作用与生命周期
启动：backend 注册 `ctx.sessionPersistence` → workspace init 强制依赖它（见 workspace 卡）。写路径：session/event → bounded write-behind → flush 落盘。读路径：list()（只读各日志首帧 header，全量 191 实测仅 0.01s）。

## 4. 约束（红线/不可违）
- **数据健康时禁止 mv/删 session 文件**（不可逆，概率 0.9 → T1）——先 session_recovery_check。
- 文件在 ≠ 列表有：数据层(此部件) 与 索引层(workspace) 分离；doctor sessions:[] 是缓存统计勿信。
- listArtifacts 任一文件 assert 失败 → **整个 list() 抛错**（workspace 依赖它，牵一发动全身）。

## 5. 依赖
- 被依赖：dsh-workspace（init 强制等它）、session store（in-memory Session 经它持久）。
- 依赖：node:zlib zstd、koffi（schema）、storage 无关（自己管 root 目录）。
- inject：`["sessions"]`（经 coordinator 装写路径监听）。

## 6. 规范要点（标准）
- P6 工具 session_recovery_check 口径 = 递归 `session.jsonl.zstd`（与 doctor healthy 同源 191）。
- 诊断顺序：①数据层(此卡) → ②索引层(workspace) → ③解析层(遮蔽) —— 不许跳层动数据。
- 首帧完整性可用 scan-first-frame 脚本逐文件验证（191 全 ok = 数据健康）。

## 7. 关联
- 官方文档：`tech-research/dsh-docs/docs/subsystems/persistence.md`、`session.md`、`persistence-catalog.md`
- 工具箱：T1（会话空）、T2（OOM——大文件全量解压）
- 路由表：OP-session-data（critical）
- 代码：`dsh-runtime/.../dsh-session-persistence-jsonl/lib/index.js`（742 assertZstdHeaderFrame / 1036 list / 1279 readFirstZstdLine）

## 8. 已知坑 / 待补
- 126 万事件大会话（7MB+ zstd）在打开/扫描时的内存峰值 → 关联 compaction 部件（未学）。
- ui-reference 的 fileReferences 走 remote 服务（另卡 session-reference，todo）。

## 9. 学-建-用 沉淀
- 2026-09-04：P6 session_recovery_check 修正为 manifest 真实结构（曾误用扁平 .jsonl.zstd 过滤导致误报 0）；scan-first-frame/time-list 诊断脚本；工具箱 T1 v1.1。
