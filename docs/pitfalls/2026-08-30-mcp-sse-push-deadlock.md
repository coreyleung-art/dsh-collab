# 踩坑档案：MCP bb_subscribe 真实推送验证（2026-08-30）

> 状态：已闭环（v0.3.0 推送验证通过）
> 关联：R017 候选 blackboard-mcp、MCP 服务器设计规范

## 现象

`bb_subscribe` 返回「已订阅（SSE 推送激活）」，但真实长驻 MCP client 场景下：
1. 写黑板触发 change 事件后，8s 内收不到 `notifications/message`
2. 加入 stderr 诊断后定位到两层故障（见下）

## 故障一：SSE 线程连错端口

| 项 | 值 |
|---|---|
| 现象 | 订阅确认返回，推送永远不来 |
| 根因 | MCP 的 SSE 后台线程用 `BB` 常量连 `127.0.0.1:8792`（REST API 端口）；而 `/events` SSE 事件桥监听**独立端口 8803**（原 blackboard-events.py 语义，v0.6 并入黑板单进程） |
| 关键误区 | 8792 有监听 → `TcpStream::connect` 成功 → 诊断以为连接正常；实际 REST 对 `GET /events` 返回 404 后关连接 → 3s 重连循环 |
| 修复 | 新增 `BB_SSE: &str = "127.0.0.1:8803"`，SSE 线程改连 `BB_SSE`（v0.3.0） |

**教训**：「TCP 能连上」≠「协议正确」。多端口服务必须为每个端口定义独立常量，连接成功可能只是连到了错误端口的监听。

## 故障二：Rust stdout 锁死锁

| 项 | 值 |
|---|---|
| 现象 | 诊断日志 `MATCH -> push notification` 已打印，但 notification 永远写不出 stdout |
| 根因 | `main()` 中 `let mut out = stdout.lock()` 在 `for line in stdin.lock().lines()` 循环作用域内**长期持有** stdout 锁（阻塞读 stdin 期间不释放）；SSE 后台线程 `std::io::stdout().lock()` 等待该锁 → 主循环永不释放 → 死锁 |
| 修复 | main() 与 SSE 线程均改为**写时短暂 lock**（每次 write 时 lock + flush 即释放） |

**教训**：Rust `Stdout` 锁不可重入，`StdoutLock` 存活于作用域。stdin 长读循环中绝不能长期持有 stdout 锁，否则所有其他线程的 stdout 输出全部死锁。

## 验证证据（沙箱先行，生产黑板实测）

```
[1] initialize → {'name': 'blackboard-mcp', 'version': '0.3.0'}
[2] bb_subscribe → 已订阅 data/mcp-test/
[3] 已写黑板 data/mcp-test/hello → version 6
[4] ✅ 真实推送到达: notifications/message key=data/mcp-test/hello version=6
    data = {"key":"data/mcp-test/hello","ts":"...","value":{"from":"mcp-test",...},"version":6}
```

curl 直连 8803 对照：黑板 SSE 桥本身正常（`event: change\ndata: {...}`），问题全在 MCP 侧 → 隔离定位有效。

## SOP 更新

- `blackboard-mcp-server-design-v1.md`：端口拓扑明确 8792 REST / 8803 SSE
- MCP 服务器设计规范：后台推送线程与主循环写 stdout 一律用「写时短暂 lock」模式
