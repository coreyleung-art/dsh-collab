# CLD-002 看门狗 · exit-marker 日志格式规范（草稿 v0.1）

> 起草：session-c1111ffe（DSH/CLD 运维排障，A3 参与项①）· 2026-08-18
> 执行：session-3d490920（看门狗安装）· 验收标准见 backlog CLD-002
> 目标：任何 CLD/dsh 退出（含外部 kill）在 ~/.cld/logs 留下可审计原因

## 1. 文件与写入点

| 文件 | 写入时机 | 内容 |
|---|---|---|
| ~/.cld/logs/exit-marker.json | CLD 退出时（正常/异常/被 kill 前） | 退出原因/信号/退出码/时间/pid |
| ~/.cld/logs/heartbeat.json | 运行期定期（如 60s） | 存活心跳：ts/pid/uptime/load |
| ~/.cld/logs/crash-reason.log | 启动时检测上一次 exit-marker | 人类可读摘要：上次退出原因 |

## 2. exit-marker.json 格式

```json
{
  "version": 1,
  "ts": "2026-08-18T10:00:00.000Z",
  "pid": 2128,
  "exit": {
    "code": 1,
    "signal": "SIGKILL",
    "reason": "external-kill",
    "detail": "pkill -9 -f dsh/lib/bin.js"
  },
  "uptime_sec": 12345,
  "gui_port": 55397
}
```

- `exit.code`：进程退出码（正常 0；异常非 0）
- `exit.signal`：终止信号（SIGKILL/SIGTERM/SIGABRT/SIGSEGV 等；正常退出为 null）
- `exit.reason`：枚举——normal-shutdown / external-kill / crash / restart-requested / unknown
- `exit.detail`：补充（如已知操作方/命令）

## 3. heartbeat.json 格式（追加式，保留最近 N 条）

```json
{"version":1,"ts":"...","pid":2128,"uptime_sec":60,"load_1m":3.2,"gui_port":55397}
```

## 4. 写入纪律

- 原子写：tmp + rename（防半写损坏）
- 权限 0600（含潜在路径信息）
- append-only 原则：exit-marker 每次退出覆盖（只留最近一次）；heartbeat 滚动保留
- 正常退出与异常退出都必须写（异常时用 process.on('exit'/'uncaughtException'/'SIGTERM'/'SIGINT') 兜底；SIGKILL 无法捕获——用 launchd 侧看门狗或心跳超时推断）

## 5. 验证场景（参与项②）

| 场景 | 预期 |
|---|---|
| 正常退出（kill TERM/quit） | exit-marker: code=0 signal=null reason=normal-shutdown |
| 外部强杀（kill -9） | 无 marker（SIGKILL 不可捕获）→ 启动时 heartbeat 超时推断 reason=external-kill |
| 崩溃（SIGSEGV/未捕获异常） | marker: signal=SIGSEGV / reason=crash |
| 重启后启动日志 | crash-reason.log 摘要上一次退出 |

> 待 3d490920 安装后对齐实现细节；本规范作为格式基准。
