# 永续通讯收敛方案 v1（2026-09-08 星桥 · 用户批评后立项）

> 触发：用户指出「给了服务器仍东一块西一块、跨设备消息还要人传话」
> 定性：不是缺补丁，是架构未收敛。本文档为诊断+收敛路线，替代零散打补丁。

## 一、现状诊断（实测证据）

| 层 | 组件 | 状态 | 断裂点 |
|---|---|---|---|
| 数据层 | 本机黑板 127.0.0.1:8792（rust） | ✅ 跑 | 主库在本机，服务器只是镜像 |
| | xingqiao 服务器 106.53.214.108:8792 | ✅ 跑 | 未设为唯一消息中枢 |
| 订阅层 | bb-sub ×8（coordinator/device/hr/...） | ✅ 收 | 收到只落 inbox，不保证唤醒 |
| 唤醒层 | central-wake.py + central-inbox | ⚠️ 空转 | **注入目标错**：not-found 24 次回退"中枢 session"副本，本机在线会话收不到 → 4415 条堆积 |
| 心跳层 | hb-fwd / node-bridge | ✅ | 心跳通 ≠ 消息通（混淆点） |
| 传输层 | sync-up/down + Funnel + Tailscale | ✅ | 都是通道，无寻址/无送达保证 |

**核心断点**：跨设备消息写黑板键后，没有「服务器路由 → 设备守护 → agent_wake 唤醒对应 agent」的闭环。
用户被迫传话 = 系统把用户当成了那个缺失的路由器。

## 二、收敛设计（目标架构）

```
[MBP agent] ─┐                          ┌─> [mac-mini agent:星桥/明鉴/...]
[i9 agent] ──┼─ PUT/SSE ─> [xingqiao 服务器=唯一消息总线] ─ 路由 ─┤
[星台 App] ─┘   (to+from+msgid)          └─> ACK / 重试 / 死信告警
```

1. **唯一消息中枢**：跨设备消息统一收口到 xingqiao（写 PUT 带信封 to/from/msgid，读走 SSE 订阅自己域）。
2. **统一寻址**：信封格式 `{msgid, from: <device|agent>, to: <agent-id|role|device>, text, ts}`；服务器按 to 路由到目标设备 outbox。
3. **送达保证**：设备守护收到 → ACK 清队；超时重试；重试尽 → 死信告警黑板（不再静默堆积）。
4. **自动唤醒**：设备守护收信 → 探测本机 agent 在线（agent-bus agents/白名单）→ agent_wake 精确唤醒目标（修 not-found：注入本机真实会话而非中枢副本）。
5. **用户角色**：仅审批，不参与消息搬运。

## 三、分步执行（每步可验证）

- [ ] **S1 修唤醒断点**（立即可做）：central-inbox/wake 改为注入本机真实在线会话（agent-bus.json profiles 探测），修复 24 次 not-found。验证：MBP 写一条 → 星桥被唤醒收到，无需人转贴。
- [ ] **S2 服务器信封路由**：xingqiao 上加 to/from/msgid 信封 + 每设备 outbox + SSE 推送（复用 comm-bus-bridge 8791）。
- [ ] **S3 送达保证**：ACK/超时重试/死信告警接入。
- [ ] **S4 全设备守护统一**：MBP/i9/mac-mini 各跑同一守护（订阅+唤醒+ACK），替换各自为政的 node-bridge/hb-fwd 消息段。
- [ ] **S5 星台 App 接入信封**：/api/chat 走服务器信封而非本机 inbox。

## 四、验收（R030：无验证不陈述）

- [ ] MBP 外网发消息 → mac-mini 星桥自动唤醒并回复，全程无用户传话
- [ ] i9 发消息 → 同链路
- [ ] 服务器重启 / mac-mini 重启 → outbox 不丢，恢复后补投
- [ ] coordinator inbox 不再无界堆积（死信有告警）

---
*星桥 2026-09-08 · 用户批评后 · 不再零散打补丁，按此收敛*
