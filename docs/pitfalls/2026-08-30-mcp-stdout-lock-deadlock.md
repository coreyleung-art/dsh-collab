# 2026-08-30-mcp-stdout-lock-deadlock MCP SSE 推送 stdout 锁死锁（Rust StdoutLock 长期持有）

> 级别: P1 · 日期: 2026-08-30

## 现象
SSE 线程日志显示 MATCH 匹配成功，但 notification 永远写不出；Python MCP client 收不到推送

## 根因
main() 中 let out = stdout.lock() 在 for line in stdin.lock().lines() 循环作用域内长期持有 stdout 锁；SSE 后台线程 std::io::stdout().lock() 等待该锁 → 主循环永不释放 → 死锁

## 修复
main() 与 SSE 线程均改为「写时短暂 lock」（每次 write 时 lock+flush 即释放），不长期持有

## 教训（→ SOP 更新点）
Rust Stdout 锁不可重入且 StdoutLock 存活于作用域；stdin 长读循环中绝不能长期持有 stdout 锁，否则所有其他线程的 stdout 输出全部死锁

## SOP 更新
MCP 服务器设计规范：后台推送线程与主循环写 stdout 一律用写时短暂 lock 模式
