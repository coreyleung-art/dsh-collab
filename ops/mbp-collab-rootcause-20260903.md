# MBP 协作链路问题审查（2026-09-03）

> 现象：MBP 反复「联系不上」——agent_send 投递 queued、ssh 超时、签名失败、必须 GUI 会话执行
> 审查范围：星台 v7 构建/SystemGraph 安装等多次 MBP 协作的反复波折

## 根因（三层）

### 1. 架构层：agent-bus 是本机机制，跨设备会话不可达
- agent_send 只覆盖 **CLD 宿主进程内**的会话（agent-bus README「本机惯例」确认）
- MBP 的 CLD = **独立进程/独立机器**——其会话（mbp-bus/mbp-ops）不在 mac-mini agent-bus 里
- agent_peers 看不到 MBP 会话；agent_send → queued 永远投递不了（当前 3 条滞留）
- **跨设备唯一通道 = 黑板**（notes/mbp/ + SSE 订阅）

### 2. 设备层：MBP 反复离线 + 心跳陈旧
- nodes/mbp 心跳 = **08-30 旧记录**（几天未更新——node-bridge/rust-bridge 心跳未续）
- MBP 休眠 → Tailscale active 但 SSH 超时（网络栈冻结）、黑板消费端不跑
- 反复出现「scp 通→超时→恢复→超时」间歇模式

### 3. 执行层：签名锁死在 GUI 会话
- xcodebuild 真机签名 → **errSecInternalComponent**（SSH/后台会话无 GUI 钥匙串）
- 必须 MBP **GUI 登录会话**执行 → 该会话的存在/可达依赖 MBP 在线 + CLD 跑着
- 链：确认在线 → 传文件(ssh) → 唤醒会话(黑板) → GUI 执行 → 回传——每环都可能断

## 改进方向（防反复波折）
| 建议 | 效果 |
|------|------|
| ① 证书入钥匙串共享 + ssh 会话解锁钥匙串（security unlock-keychain） | ssh 也能签名——不再锁 GUI 会话 |
| ② MBP 侧 launchd 保活执行代理（消费 notes/mbp/ 任务，GUI 会话内跑） | 不依赖会话偶发在线 |
| ③ MBP 协作期 pmset 禁休眠（caffeinate） | 防离线中断 |
| ④ 跨设备消息统一走黑板 + 消费端保活 | 消除 agent_send 死信 |

## 本次星台构建教训
- ssh 直接构建 = errSecInternalComponent（已知）——浪费一轮
- 正确路径 = MBP GUI 会话（mbp-bus 通知执行）或 ①解锁钥匙串后 ssh 构建
