# 上游讨论补充草稿：会话并发写 seq 重叠 / 非干净退出丢尾部

> 作者：session-b278baab（DSH 基础设施根因研究与协作）· 2026-08-17
> 用途：向 deepseek-harness Discussion #1586 / #1497 / #483 补充根因证据与修复方案
> 状态：FINAL v3——master 验证 + JSONL backend 跨进程锁最终确认均完成（4787d717，2026-08-17）：跨进程无锁成立，提案方向获验证方背书；唯一门控=用户确认外部发布

## 一、覆盖关系

| 上游讨论 | 现象 | 本会话实证 |
|---|---|---|
| #1586 | 崩溃恢复与残留执行流并发写同一日志，seq 重叠 | 同型：本机双 dsh 实例并发 append → 重复 seq（session-c73d4226: seq 136804/136805 双写；session-ce836fb7: seq 171280/171281 双写） |
| #1497 | unclean exit 后 corrupt session log，seq gap | 同型：非干净退出（SIGKILL）后残留进程与新进程用陈旧游标续写 |
| #483 | force-kill 宿主后 write-behind 丢未 flush 尾部 | 同型：CLD 退出 process.on("exit") 无条件 SIGKILL 子进程 → 200ms 写合并窗口尾部丢失 |

## 二、根因证据（本机实测）

1. **跨进程零互斥**（#1586/#1497 根因）：
   - PersistenceCoordinator 的 serialize() 是进程内 per-id promise 链；appendCore 只校验「seq == 内存游标 + i」，从不先读盘确认实际推进位置（dsh-session-persistence src: appendCore）。
   - commitRepair 撕裂尾部修复直接 truncate 文件，可裁掉另一进程刚写的帧。
   - JSONL 后端 appendLines 用 open(path,"a") 无锁追加；materialize 硬链接发布，并发创建时一个进程报 refusing to materialize。
   - 本机实证：2026-08-15 16:19:48 与 16:22:22，两个 dsh 实例（3080 npx 实例 + CLD.app 内置实例，同一 ~/.dsh 根）对同一会话日志并发 append，产生重复 seq，均精确对应 CLD 启动后约 5 秒。

2. **写合并窗口丢尾部**（#483 根因）：
   - 默认 writeBatchMaxDelayMs=200ms：事件先入内存队列，200ms 后才 fsync。
   - 优雅停机预算 5s（process shutdown timeout），但 CLD 的 process.on("exit") 无条件 SIGKILL 子进程 → flush 跑不完 → 尾部（≤200ms + 在途大帧）丢失。

## 三、修复方案（P1-P2，论文依据）

### P1：根目录单写者租约（根治跨进程并发写）
- 位置：dsh-session-persistence-jsonl 后端打开根目录时（assertUsableRoot）。
- 实现：O_EXCL 创建 <root>/.dsh-owner 锁文件（pid/startedAt/heartbeat），持锁进程周期心跳；dispose 释放；第二实例启动时校验 PID 存活→拒绝启动并明确报错；PID 已死→陈旧锁安全接管（存活性+心跳过期双确认）。
- 论文依据：Gray & Cheriton, "Leases", SOSP 1989。
- 效果：从根上消除「两个进程写同一会话根」，本机双实例场景直接不可发生。

### P2：写前 revision 校验 + 冲突即报错（防御纵深）
- 位置：PersistenceCoordinator.appendCore 在 appendBatch 前用 readStoredRevision 比对。
- 一致→正常写；不一致→重新 adopt：
  - 磁盘前缀是待写事件的顺序前缀 → 合并游标只追加后缀；
  - 否则（seq 重叠）→ fail-loud 抛错，绝不静默覆盖。
- 撕裂尾部修复（commitRepair truncate）仅允许持租约进程执行。
- 论文依据：Kung & Robinson, "OCC", ACM TODS 1981；ARIES（WAL 崩溃恢复），ACM TODS 1992。

### P3（针对 #483）：turn/end 立即 flush + 宿主优雅退出
- installWritePath 对 turn/end 事件立即 flush(session)（投影缓存已如此，持久化层照做）。
- 宿主（CLD）退出改为 SIGTERM 后等待子进程自然退出（宽限期 ≥ dsh 5s 预算），去掉 process.on("exit") 无条件 SIGKILL。
- 论文依据：group commit（DeWitt & Naughton 1995）解释合并窗口的取舍。

## 三·五、master 验证结论（4787d717，2026-08-17）

deepseek-harness master 已实现的并发写防护（均为**进程内**机制）：
1. SessionWriteBehind：per-session 单写者（pending + deadline + 单 active write + barrier）
2. coordinator 串行化 + cursor + readFrom 按 seq + torn-tail marker（崩溃丢尾部检测）
3. SessionPersistenceRevision：source-qualified revision 校验
4. preparations 恢复期保留

**界定**：以上覆盖「单进程内并发/崩溃」场景（#1497/#483/#466 的大部分），本地 rc.6 同源。

**仍存在的缺口（本会话实证属此区间）**：**跨进程**并发写同一会话根——两个独立 dsh 进程（3080 npx 实例 + CLD.app 内置实例，同一 ~/.dsh 根）各自持有独立内存游标与独立进程内串行链，任何进程内机制都无法互斥对方。master 防护清单中**无跨进程根租约/锁**。验证者结论自洽：「若跨进程写→需补充证据提新提案」。

→ 因此本草稿仍有效，聚焦 P1 根目录单写者租约（跨进程），证据=本机双实例重复 seq 实测。
**最终确认（4787d717，2026-08-17）**：dsh-session-persistence-jsonl rc.6 appendLines（lib/index.js 1200-1227）= open(path,"a") O_APPEND 追加 → stat before → writeFile → fsync → 失败 rollbackAppend(truncate)。全程**无 flock/fcntl/O_EXCL、无跨进程 revision 校验、无读当前尾部 seq 再校验**。跨进程场景两进程各自 O_APPEND、各自独立 seq 游标 → 日志交错/重复 seq（无防护）。进程内防护与 O_APPEND 原子单次写仅覆盖单进程与单次写撕裂。→ 跨进程根租约提案成立且必要（实现参考：root 级 lockfile O_EXCL+心跳租约，或跨进程 revision 文件写前 compare-and-swap）。


## 四、待执行步骤

1. [x] 4787d717 深读 master src/index.ts（已完成 2026-08-17）
2. [x] 界定：进程内防护已修（#1497/#483 单进程部分）；跨进程写缺口仍存
3. [ ] 将跨进程证据+根租约方案发布至 #1586/新 issue（验证方背书支持发布，仍需用户确认外部动作）
4. [ ] §6.5 登记：『会话并发写 seq 重叠：进程内已修（master），跨进程根租约缺口→提案中』（已请 HR 补记）
