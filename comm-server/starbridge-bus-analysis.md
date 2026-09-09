# 星台桥：对话走服务器 bus vs 保持本地黑板 · 完整分析（2026-09-06 星桥）

## 一、星台桥对话当前架构（本地黑板路径）
POST /api/chat → 写本机黑板 notes/{target}/sb-dialog-<ts>-task（8ms）
→ 目标端（MBP/i9 总线）轮询读 → 回写 reply 键
→ 星台 GET /api/reply 轮询读（i9→notes/i9/starbridge-reply-latest；其他→notes/mac-mini/mobile-reply/latest-<session>）

## 二、关键洞察：感知延迟由「轮询」主导，非传输延迟
- 星台 App → 桥传输：本地 ~8ms / 服务器 bus 40-180ms —— **差 ~100ms**
- 但 /api/reply 是**客户端轮询**（星台 App 定期 GET）——用户感知回复延迟 ≈ 轮询周期（数百 ms~s 级）
- 100ms 传输差在轮询架构下**几乎无感**（远小于轮询周期）
- 结论：实时性不是 bus 化的实质障碍（明鉴提醒的 8ms vs 180ms 差异被轮询稀释）

## 三、双路径对比矩阵
| 维度 | 本地黑板(现) | 服务器 bus(改) | 判定 |
|---|---|---|---|
| 传输延迟 | 8ms | 40-180ms | bus 劣 ~100ms，但被轮询稀释，体验近同 |
| 可靠性 | 随 mac-mini CLD 重启断 | 服务器 24h systemd | **bus 胜**（星台对话不随 CLD 断）|
| 依赖 | mac-mini CLD 活 | xingqiao 活 | bus 依赖更独立 |
| 改动成本 | — | 星台桥 chat→bus/send + reply→outbox + **MBP/i9 需加 bus receive 端** | bus 大（三端配合）|
| 语义 | 黑板消息键 | 任务队列 send/reply | bus 更结构化(task/ack)|
| 备灾 | 黑板双轨(本机+中枢镜像) | bus 独立 | 可互补 |

## 四、推荐：双轨混合（主本地黑板 + bus 备灾），非全切
理由：
1. 全切 bus 改动大（星台桥+MBP/i9 三端），收益主要是「CLD 重启期间对话不断」——该场景低频（CLD 重启有窗口）
2. 本地黑板主通道已工作 + 双轨镜像（CLD 挂→中枢镜像在），星台桥读端可配 fallback 中枢
3. 建议落地（低改动高收益）：
   a. 星台桥写端加 failover：本机黑板写失败 → 自动切服务器 bus（或中枢黑板）
   b. 星台桥读端 /api/reply 加 fallback 源（中枢 notes/... 或 bus outbox）
   c. MBP/i9 侧保持黑板轮询为主，bus 为任务通道（已有能力）
4. 若未来「对话任务化」需求强（结构化 ack/审计/重放），再评估全量 bus

## 五、结论
- 星台桥**不建议全量改走服务器 bus**（改动大、收益被轮询稀释）
- 建议**主本地黑板 + 自动 failover 到中枢/bus**（双轨，符合通讯架构 R031/永续哲学）
- 实时性担忧（明鉴提醒）实为伪问题（轮询主导）；真正收益在可靠性（failover）
