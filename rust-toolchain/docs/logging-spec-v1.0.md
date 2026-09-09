# Rust 工具链 · 统一日志规范 v1.0

> 目的：三项目（node-bridge / rust-blackboard / rust-genebank）日志一致，可 grep 可轮转可归档
> 状态：2026-08-25 · mac-mini 中枢

---

## 一、日志格式（结构化，每行一个 JSON）

```json
{"ts":"2026-08-25T23:50:00","level":"INFO","comp":"heartbeat","msg":"nodes/i9/heartbeat -> 200","node":"i9"}
```

| 字段 | 说明 | 示例 |
|---|---|---|
| ts | ISO 本地时间（秒）| 2026-08-25T23:50:00 |
| level | DEBUG/INFO/WARN/ERROR | INFO |
| comp | 组件/线程名 | heartbeat / queue / worker / notes / http / sse |
| msg | 消息正文 | 见上 |
| node/port | 可选附加（节点 ID/端口）| i9 |

**为什么 JSON**：可被 jq/grep 过滤、可被后续日志采集（filebeat/loki）直接消费。

## 二、落盘路径

| 平台 | 路径 | 说明 |
|---|---|---|
| macOS | `~/dsh-collab/logs/<project>.log` | 中枢侧统一收集 |
| Linux | `/var/log/<project>.log`（root）或 `~/dsh-collab/logs/` | 可配 |
| Windows | `%USERPROFILE%\.dsh\logs\<project>.log` | 无 console 服务模式 |

环境变量覆盖：`DSH_LOG_DIR=<dir>` 优先于默认路径。

## 三、轮转（内置，无外部依赖）

```
规则：单文件 > 5MB → 轮转为 <project>.log.1，保留最近 3 个
实现：写入前检查大小 → 超限则 rename .log → .log.1（.log.1→.log.2，丢弃 .log.3）
同步双写：stdout（可关）+ 文件
```

## 四、级别

```
--log-level DEBUG|INFO|WARN|ERROR   （默认 INFO）
级别过滤在写入前：低于阈值的日志跳过
```

## 五、三项目接入

| 项目 | 组件名 | 说明 |
|---|---|---|
| node-bridge | heartbeat/queue/worker/notes | 桥线程日志 |
| rust-blackboard | http/put/delete/sub/sse/clock | 黑板请求日志 |
| rust-genebank | register/file/registry | 基因库操作日志 |

## 六、变更记录
- v1.0（2026-08-25）：首版规范。JSON 结构化 + 5MB 轮转 + 双写 + 级别过滤。
