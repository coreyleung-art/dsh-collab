# 服务器架构专项审查 · 2026-10-03（事故后复审）

> 审查人：星桥（协调者）｜ 方法：ssh 实测取证 + 事故复盘对照｜ 触发：2026-10-03 黑板数据丢失+颠簸事故后复审

## 1. 结论摘要

服务器承载 11 个 comm 单元（黑板 8792/SSE 8803、bus-bridge 8791、bb-sub ×8、测试区），**功能面经今日三项变更已升级**，但**结构面有两处高危 + 三类隐患**。本轮已落 4 项加固，1 项（写鉴权）列为需协调的变更。

## 2. 实测证据（2026-10-03 13:4x 取证）

| 项 | 实测 | 判定 |
|---|---|---|
| 全部 11 单元 | `Restart=always` + `MemoryMax=infinity` + `User=ubuntu` | 🔴 事故根因结构面：崩溃必重启 + 无内存上限 ⇒ OOM 杀随机进程 ⇒ 整机颠簸（kernel 日志实证：13:23 OOM killed rust-blackboard anon-rss 641MB） |
| 8792 写鉴权 | 启动日志 `token=off`；**无 token PUT → 200** | 🔴 公网可匿名写中央板：任何可达者都能写/覆盖任意键（含 notes/mac-mini/* 注入键 ⇒ 跨会话注入面） |
| 持久化 | 9-06 起 27 天静默失败（root 属主+ubuntu 运行，audit 写入被吞） | 🔴 已修：chown + v0.6.11 失败告警 |
| s3fs/COS | 进程在（lhcos-3c75f）但 mount 无挂载点 | 🟡 备份通道存在但未生效 |
| 磁盘 | 40G 用 17% | 🟢 |
| 双广播 | store.notify 与 http 层各广播一次 | 🔴 已修 v0.6.10（SSE 客户端曾每事件收两遍） |
| SSE 重放 | 原无 id/无缓冲 | 🟢 已修 v0.6.9-0.6.11（500 条缓冲 + Last-Event-ID，主线验收通过） |

## 3. 本轮已落加固（2026-10-03 13:46）

1. **内存上限**：comm-server 300M / bus-bridge 128M / bb-sub×8 各 64M（MemoryMax drop-in）——超限由 systemd 干净杀该服务，不再由内核 OOM 随机杀进程。
2. **重启循环断路器**：全部单元 StartLimitBurst=3 / StartLimitIntervalSec=300——持久故障不再无限重启颠簸。
3. **目录属主**：/opt/comm-server → ubuntu。
4. **验证**：加固后全单元 active；8792/8803 正常；内存可用 505MB（较此前 303MB 提升）。

## 4. 待协调项（列为下一变更，不擅动）

### 变更 A：黑板写鉴权启用（token=on）
- 现状：写端免鉴权（公网匿名可写）。启用后 PUT 需 Bearer；GET/SSE 仍公开；i9 路径豁免已内建（nodes/i9/*、notes/i9/*、tasks?node=i9）。
- 动作：①comm-server 单元加 `Environment=BLACKBOARD_TOKEN=<mac-mini 既有 token>` ②所有合法写方加认证头：hb-fwd put_central、sync-up、bus-bridge 写卡、bb-card-send core、MBP 侧全部写方 ③MBP 先改完再 flip（避免断他链路）④flip 后正负验收（无头 401 / 带 token 200 / i9 豁免路径仍 200）。
- 风险：MBP/i9 写方漏改会断链 ⇒ 需两端同步窗口。

### 变更 B：备份通道修复
- s3fs 挂载失效（进程 init 但无挂载点）⇒ 修挂载或换通道（如 scp 到 mac-mini 双备份）。修好后装 04:30 快照备份 cron（脚本已备好）。

### 变更 C：comm-server-test 隔离区对公网不可达（现状如此=隔离正确，保持）

## 5. 复现命令

```bash
ssh -i ~/Downloads/startbrige.pem ubuntu@106.53.214.108 \
  "systemctl show comm-server -p Restart -p MemoryMax; curl -s -o /dev/null -w '%{http_code}' -X PUT -d '{}' http://127.0.0.1:8792/data/ops/probe"
```
