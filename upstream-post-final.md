## 跨进程并发写同一会话日志导致 seq 重叠（corrupt session log）——补充证据与修复方案

> 关联：#1586（崩溃恢复与残留执行流并发写）、#1497（unclean exit 后 corrupt）、#483（force-kill 后 write-behind 丢尾部）
> 社区贡献性质：仅技术提案，不涉及业务数据。

### 问题界定

master 已实现的并发写防护（SessionWriteBehind 单写者、coordinator 串行化、torn-tail marker、SessionPersistenceRevision、preparations 恢复期保留）均为**进程内**机制，覆盖单进程并发/崩溃场景。但**跨进程**场景仍无防护：两个独立 dsh 进程（如桌面壳 + 浏览器实例，或宿主重启残留进程）各自持有独立内存游标与独立进程内串行链，同时向同一 ~/.dsh 根追加同一会话日志。

### 实证（本机 2026-08-15）

- 两个 dsh 实例（npx 实例 PID 46438 + CLD.app 内置实例 PID 46823，同一 profile/同一会话根）并发运行。
- 日志出现重复 seq：session-c73d4226 的 seq 136804/136805 被写两次（先 step/end+turn/end，紧接着另一进程以陈旧游标写入 reasoning-chunks seq0=136804）；session-ce836fb7 同样（seq 171280/171281）。两次均精确对应 CLD 启动后约 5 秒。
- 代码确认：session-persistence-jsonl 的 appendLines（open(path,"a") O_APPEND → writeFile → fsync）全程无 flock/fcntl/O_EXCL、无跨进程 revision 校验、无读当前尾部 seq 再校验。

### 修复方案

**P1 根目录单写者租约**（根治跨进程并发写）：
- 后端打开会话根时以 O_EXCL 创建 <root>/.dsh-owner（pid/startedAt + 心跳 mtime）。
- 第二实例启动检测到存活占用 → 拒绝启动并给出明确报错（另一 dsh 实例正占用该会话根）。
- 占用者崩溃后（PID 已死或心跳过期）→ 安全接管。
- 撕裂尾部修复（commitRepair truncate）仅允许持租约进程执行。

**P2 写前 revision 校验（防御纵深）**：
- appendCore 在 appendBatch 前以 readStoredRevision 比对：一致则写；不一致则重新加载——若磁盘前缀是待写事件的前缀则合并游标只追加后缀，否则 fail-loud 报错，绝不静默覆盖。

**P3（针对 #483）**：turn/end 事件立即 flush；宿主退出改为等待子进程优雅停机（≥ 当前 5s 预算），去掉无条件 SIGKILL。

### 验证（副本环境实测，未触碰真实存储）

原型：双写者陈旧游标并发写 → 基线 dups=5（与真实损坏同型）；加租约后第二写者 LEASE_REFUSED（dups=0）；持有者 SIGKILL 后新进程死 PID 接管成功（dups=0）；游标陈旧续写触发 SEQ_CONFLICT fail-loud 零写入（dups=0）。完整报告见 prototype-verification-cross-process-lease.md。

### 参考

- Leases（Gray & Cheriton, SOSP 1989）——租约/续租/接管
- OCC（Kung & Robinson, ACM TODS 1981）+ etcd/PG CAS 实践——写前校验
- ARIES（Mohan et al., ACM TODS 1992）——WAL 崩溃恢复语义
- group commit（DeWitt & Naughton 1995）——写合并窗口取舍

期待维护者意见；如可，愿配合补充补丁实现。
