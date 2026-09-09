# 运维告警模板（sysops health → 企微）

## 1. CRIT 告警（严重）
🚨 **【运维告警 · 严重】**
- 时间：{{timestamp}}
- 项：{{item}}（如 Dify/Ollama/LM Studio/面板/xberg）
- 状态：{{status}}（掉线/失败/高压）
- 影响：{{impact}}
- 处置：{{action}}（如 watchdog 已拉起/需人工介入）

## 2. 恢复通知
✅ **【运维恢复】**
- 时间：{{timestamp}}
- 项：{{item}}
- 状态：已恢复（{{detail}}）

## 3. 入库通知
📥 **【知识入库完成】**
- 文档：{{doc}}
- 三路：Dify ✓ / ChromaDB +{{chunks}}块 / vault ✓
- 集合：{{collection}}
