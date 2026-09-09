# 原型验证报告：跨进程单写者租约 + revision 校验

> 作者：session-b278baab · 2026-08-17
> 场景：deepseek-harness 跨进程并发写修复方案（P1 根租约 + P2 revision 校验）· 发帖前前置验证
> 测试环境：/tmp/dsh-lease-prototype（副本，未触碰真实会话存储）

## 一、基线复现（无防护 → 复现真实损坏签名）

双写者（WRITER-A/B）均持陈旧游标 seq=100（盘尾=99），无锁、不读盘直接 O_APPEND 追加 5 事件：

- 结果：**dups=5**（seq 100-104 各写两遍），日志尾部呈现 AB 两批同 seq 事件
- 与真实损坏（session-c73d4226: step/end+turn/end@136804/136805 后紧接 reasoning-chunks@136804）**同型**——本原型忠实复现了 2026-08-15 本机实测损坏。

## 二、修复后场景（三个机制，全部 dups=0）

### 场景 A：租约冲突检测（P1）
A 持租约（holdMs=1500），B 并发尝试获取：
- B → `LEASE_REFUSED: OCCUPIED by pid=49657 (alive)` ✅ 冲突检测生效
- 仅 A 追加成功；日志 dups=0

### 场景 B：陈旧租约接管（P1 恢复）
A 获取租约后 SIGKILL（模拟崩溃），B 尝试获取：
- 检测到 owner PID 已死（process.kill(pid,0) → ESRCH）→ 判定陈旧 → 删除旧锁 → 接管成功 ✅
- B 正常追加；日志 dups=0（未因崩溃遗留锁而卡死）

### 场景 C：revision 校验 fail-loud（P2 纵深）
游标=100 但盘尾已推进到 104 时 checked 追加：
- → `SEQ_CONFLICT: cursor=100 but disk tail=104 (expected next=105)` ✅ 抛错且**零写入**
- 游标正对盘尾（cursor=100, tail=99）时追加成功；日志 dups=0

## 三、结论

| 场景 | 防护前 | 防护后 |
|---|---|---|
| 双实例陈旧游标并发写 | dups=5（损坏） | 第二个写者 LEASE_REFUSED，dups=0 |
| 持锁进程崩溃 | 锁残留/双写风险 | 陈旧接管成功，dups=0 |
| 游标陈旧续写 | 静默重复 seq | SEQ_CONFLICT fail-loud，零写入 |

**验证通过**：P1 根目录单写者租约（O_EXCL + PID + 心跳 + 陈旧接管）与 P2 写前 revision 校验（tail 比对 + fail-loud）在副本环境实测有效，能够根治跨进程并发写导致的重复 seq/日志交错。方案可作为上游提案发布依据（4787d717 背书 + 论文依据 Leases/OCC/ARIES）。

## 四、复跑方式

```bash
cd /tmp/dsh-lease-prototype
bash runner.sh baseline        # 复现损坏（预期 dups=5）
bash runner.sh lease-conflict  # 租约冲突（预期 B 拒绝）
bash runner.sh stale-takeover  # 陈旧接管（预期 B 接管成功）
bash runner.sh seq-conflict    # revision 校验（预期 SEQ_CONFLICT）
```
