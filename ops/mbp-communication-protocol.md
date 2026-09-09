# MBP ↔ 星桥通讯协议 v1.1（2026-09-03 · 实测验证）

## 通道（实测通过 2026-09-03 comm-test）
| 方向 | 正确格式 | 实测 |
|------|---------|------|
| mac → MBP 发任务/消息 | 写黑板 `notes/mbp/<topic>-task`（**必须 -task 后缀**） | ✅ comm-test 12s 回执 |
| MBP → mac 回报 | mbp-bus 写 `notes/mbp/<topic>-done`（+ 主动写 notes/mac-mini/ 通知） | ✅ 76 条 + comm-test-done |
| MBP 心跳 | nodes/mbp/heartbeat | ✅ 活跃（health ok） |

## 关键：mbp-bus 只消费 **-task 后缀**任务卡
- ✅ 认：notes/mbp/starbridge-ios-build-task / laodeng-ios-device-task 等（-task 结尾）
- ❌ 不认：任意 notes/mbp/* 或 notes/mac-mini/* 随机 key（probe 无回执——2026-09-03 教训）

## 禁用
- ❌ agent_send → MBP（本机机制跨设备死信——3 条已归档）

## 规范
1. 给 MBP 发任何事 → notes/mbp/<topic>-task（内容含 request 明确要求 + 回报 key）
2. 发后等回报 <topic>-done；超时查心跳（G2 通讯健康门）
3. mbp-bus 消费端=MBP CLD GUI 会话（pid 76861 保活）+ central-inbox SSE
4. 协作期 MBP 防休眠
