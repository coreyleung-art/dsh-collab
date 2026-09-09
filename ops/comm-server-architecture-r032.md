# 通讯架构根治：独立通讯服务器（hub-spoke）· 用户定案

> 2026-09-04 星桥（fa1f9150）起草 · 蓝图任务已投明鉴（f38244df）升级 agent-network
> 状态：📋 蓝图持久化推进中（用户要求彻底持久化工作流，不再每次手修）

## 一、问题根源（用户亲自指出 + 实测确认，非猜测）

### 架构缺陷：星型中心化
- 当前所有跨设备通讯依赖 **mac-mini 黑板 :8792**（rust-blackboard 跑在 mac-mini 上）
- i9 / MBP 都是「客户端连到 mac-mini」，不是「连共同中枢」
- 后果：mac-mini 服务异常 / 网络抖动 / 重启 = 全网通讯断

### i9 反复失联的假阳性根因（R021 实测）
| 假象 | 真相 |
|---|---|
| i9 心跳活跃（60s 更新） | 守护进程独立写的，**不代表 CLD 会话活着** |
| link-probe / 资产键存在 | 老板转达时**手动写的**，不证明自动化链路 |
| 回执卡 version=1 | bb-sub 读卡不改写 version，无法判断消费 |

**核心教训**：健康判定不能用「心跳/手动键」，必须用「**自动化 ping → 守护自动 ack**」——超时才算失联。

### 数据分叉
- i9 早期回报误用 `/api/notes/` 前缀 → 数据落在独立存储（`api/notes/i9/`）
- mac-mini 读 `notes/i9/` 看到空 value={}，两侧各存一份互不见

## 二、根治方案（用户方向，已验证可行）

### 方案 A：独立通讯服务器 hub-spoke（首选）
```
        ┌── Linux 服务器（24h 在线）──┐
        │  rust-blackboard 通讯中枢    │
        └───┬───────────┬─────────┬───┘
       mac-mini        i9        MBP
    （各自独立客户端连接，互不依赖）
```

**可行性已验证**：
- `~/dsh-collab/rust-blackboard/dist/` 有：
  - `rust-blackboard-linux-x64-v0.6.0` ✅（服务器可跑）
  - `rust-blackboard-win-x64-v0.6.0.exe` ✅（i9 Windows 也能本地跑/作为客户端）
  - `rust-blackboard-macos-arm64-v0.6.7`（当前 mac-mini 跑的就是它，--port 8792 --sse-port 8803）
- 当前实例命令实证：`rust-blackboard-macos-arm64-v0.6.7 --port 8792 --sse-port 8803 --data-dir <dir>`

**优点**：
1. 单一事实源：三端读写同一份数据，不再分叉
2. mac-mini 重启不影响 i9/MBP 通讯
3. 服务器统一裁决健康（每端独立心跳 + 守护自动 ack）
4. 部署脚本版本化可复跑

### 方案 B：Tailscale 直连 + 双心跳（无服务器时）
- i9 = desktop-p8e7op1，Tailscale IP **100.118.15.71**（直连活跃 8ms，SSH 22 开，8915 开）
- 备选：建 mac-mini ↔ i9 机器直连通道 + 标准健康协议（ping/ack 双心跳）

## 三、标准化健康协议（两方案共用）

1. **双心跳**：`nodes/<node>/hb-daemon`（守护进程，60s）+ `nodes/<node>/hb-session`（CLD 会话，含会话 id）——服务器据此区分「机器活」vs「智能体活」
2. **自动 ping/ack**：每 10 分钟发 `tasks/health/ping-<node>` → 目标守护自动回 `tasks/health/ack-<node>`（HTTP 直达，不经 LLM）——超时 3 轮判失联
3. **确定性任务由守护代答**：ack/回报类不走 LLM 会话，守护直接完成
4. **前缀规范**：统一 `notes/<node>/<topic>` 无 /api 前缀 + 扁平 content 结构；跨端写前先 GET 验证

## 四、待办
- [ ] 明鉴：升级 blueprint:agent-network → comm-server 主线（阶段/门禁/验收/SOP）
- [ ] 用户：提供 Linux 服务器（腾讯云 129.204.12.142 或指定）
- [ ] 星桥：写部署脚本（服务器端 rust-blackboard + 三端客户端配置）
- [ ] i9 侧：部署守护（Windows 看门狗：自动 ack + 会话看护）
