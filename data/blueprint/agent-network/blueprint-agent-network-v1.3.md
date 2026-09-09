# blueprint:agent-network · 多智能体协作底座（FNP 语义 + Agent Bus 消息 + comm-server 通讯根治 + 内存治理双层 + 监控安全） · v1.3

> 生成：明鉴 v2 · 2026-09-03 · 三件套纪律（文档/代码/依赖）
> 状态：active · 门禁：① P0 通信契约冻结（envelope v1.0）才进 P1 ② P2 状态契约（重启对齐+幂等）才进 P3 ③ 每阶段 Rust 化达标（dsh-tools 子命令）④ comm-server 部署 SOP 可复跑才算上线
> 依据：research/agent-network-blueprint-candidate.md + 用户定案 2026-09-03（永续通讯根治·彻底持久化工作流）+ comm-server-blueprint-task-1788459402432 + i9 失联教训（心跳假阳性/数据分叉/无自动健康 ack）
> 新增：**comm-server 主线**（用户定案：hub-spoke 独立通讯服务器，根治 mac-mini 黑板单点）

## 〇、BP-9 元信息

| 字段 | 值 |
|------|-----|
| id | agent-network |
| name | 多智能体协作底座（FNP + Agent Bus + comm-server 通讯根治 + 内存双层 + 监控安全） |
| version | v1.3 |
| mainlines | bus / fnp / comm-server（通讯根治·新）/ mem-l1 / mem-l2 / security |
| stages | P0-P5 + cs0-cs4（comm-server）+ mg1-mg7 |
| works | an0-1… + cs0-1…cs4-1 + mg1-1…mg7-2 |
| gate | ① P0 契约冻结才进 P1 ② P2 状态契约才进 P3 ③ Rust 化达标 ④ comm-server SOP 可复跑 ⑤ mem-l2 MG4 才进 MG5 |
| status | active |
| ts | 2026-09-03 |

## 一、主线

- **bus**：Agent Bus 消息层 — 线程/红绿灯/inbox 背压/消息路由（演进保留）
- **fnp**：FNP 语义层 — 自有协议防逆向：黑板 KV/事件桥 SSE/FNP 信封/HLC 时间轴
- **comm-server**：通讯根治线（新·用户定案） — 独立 hub-spoke 通讯服务器：单一事实源 + 统一裁决健康 + 三端独立连接
- **mcp-access**：外部 MCP 接入层（新·2026-09-06） — comm-mcp-server：任意 MCP 客户端经 E2 注册+token 接入 comm 架构；工具面 bb_read/write/subscribe/bus_send/node_*（设计 docs/mcp-external-access-design-v1.md · 计划 A 附录）
- **mem-l1**：内存治理 L1 · 工具链（现时·效率）
- **mem-l2**：内存治理 L2 · 体系化持久化（未来·知识）
- **security**：监控安全层 — 落链/值班/授权/积压告警/上下文监控

## 二、comm-server 主线 · 阶段与子阶段

### 现状缺陷（用户亲自指出 · 2026-09-03）
1. **通讯星型中心化**：黑板 :8792 在 mac-mini——i9/MBP 全连 mac-mini，mac-mini 异常 = 全网断
2. **i9 反复失联根因**：
   - 心跳假阳性——守护进程写心跳 ≠ CLD 会话活着
   - 数据分叉——i9 误用 /api/notes 前缀，两侧各存一份互不见
   - 无自动化健康 ack——验证靠手动写测试键

### cs0 方案定案 [active]
- cs0-1 架构定案 [done] — hub-spoke：独立服务器中心，mac-mini/i9/MBP 各自独立连接；单一事实源 + 服务器统一裁决健康（每端独立心跳 + 守护自动 ack）；mac-mini 重启不影响 i9/MBP
- cs0-2 备选方案评估 [done] — i9 desktop-p8e7op1（100.118.15.71，8ms，SSH22 开）——无独立服务器时先建机器直连通道 + 双心跳标准健康协议

### cs1 部署目标 [active]
- cs1-1 服务器候选 [active] — 24h 在线 Linux 服务器（rust-blackboard linux-x64 v0.6.0 产物已备：~/dsh-collab/rust-blackboard/dist/）
- cs1-2 直连备选 [todo] — i9 机器直连通道（Tailscale 100.118.15.71 已验证可达）——若服务器就绪则此线降级为 fallback 文档
- cs1-3 端口/域名规划 [todo] — comm-server 端口/反代/访问控制定案

### cs2 服务器部署 [todo]
- cs2-1 部署 SOP v1 [todo] — 文档 + 脚本版本化（可复跑）：scp 二进制 → systemd/nssm 服务 → 端口开放 → 验证
- cs2-2 健康协议 v1 [todo] — 每端独立心跳 + 守护自动 ack（CLD 会话活性用真 ack 而非守护心跳）；服务器统一裁决
- cs2-2b 全局注册表(E2) [done 核心 2026-09-06] — 三端注册在线(mac-mini/i9/mbp)+bb-gate 查询通; 剩余: MBP 自注册覆盖兜底(可选)+罗盘 device-assets 会话级(steps4)
- cs2-3 数据迁移 [todo] — 黑板现有键/线程迁到 comm-server（单一事实源）；i9 /api/notes 前缀分叉修复（两侧合并去重）

### cs3 三端接入 [todo]
- cs3-1 mac-mini 接入 [todo] — 连 comm-server，黑板降级为本地缓存/只读归档
- cs3-2 i9 接入 [todo] — win-x64 v0.6.0.exe 部署；修复前缀分叉（统一 /notes 规范）
- cs3-3 MBP 接入 [todo] — 连 comm-server（心跳/订阅/注入闭环走单一事实源）
- cs3-4 故障切换演练 [todo] — mac-mini 重启模拟：验证 i9/MBP 通讯不中断（验收标准核心）

### cs4 持久化运维 [todo]
- cs4-1 健康看板 [todo] — 三端心跳/ack/通道状态可视化（服务器统一裁决结果）
- cs4-2 异常自动恢复 [todo] — 心跳连续 N 次假阳性/超时 → 自动告警 + 重启订阅器（bootout+bootstrap）
- cs4-3 SOP 复跑验证 [todo] — 全新环境按 SOP 部署一次通过（验收：文档+脚本可复跑）

## 二b、验收标准（comm-server 主线）

| # | 标准 | 验证方式 |
|---|------|---------|
| A1 | mac-mini 重启，i9/MBP 通讯不断 | 故障切换演练（cs3-4）实录 |
| A2 | 心跳真实反映会话活性 | CLD 会话死 → 服务器 3 轮内判离线；守护进程假心跳不误判 |
| A3 | 数据单一事实源无分叉 | i9 与 mac-mini 读写同一键可见（前缀规范统一） |
| A4 | 健康 ack 自动化 | 无需手动写测试键，服务器自动产出健康报告 |
| A5 | SOP 可复跑 | 全新 Linux 服务器按部署 SOP 一次通过（cs4-3） |

## 三、部署 SOP（草案 · cs2-1 落成后版本化）

```
# 目标: 24h 在线 Linux 服务器
1. scp rust-blackboard-linux-x64-v0.6.0 → /opt/comm-server/
2. systemd 服务: [Service] ExecStart=/opt/comm-server/rust-blackboard-linux-x64-v0.6.0 --port <PORT>
   (或 i9/win: nssm install rust-blackboard ...exe --port <PORT>)
3. 端口开放 + 访问控制(仅 Tailscale/白名单)
4. 验证: curl http://<server>/health → 200; 各端注册心跳可见
5. 三端各自改指向 comm-server(保留本地回退)
6. 故障演练: 重启任一节点 → 验证其余通讯不断
# 产物: scripts/comm-deploy-<ver>.sh + docs/comm-server-sop-<ver>.md(版本化可复跑)
```

## 四、工作项（works · comm-server 新增）

| 状态 | 工作 | owner | stage |
|------|------|-------|-------|
| done | comm-server 架构定案（hub-spoke） | 明鉴/星桥 | cs0-1 |
| done | 备选评估（i9 直连双心跳） | 明鉴 | cs0-2 |
| active | Linux 服务器候选确认 | 星桥/老登 | cs1-1 |
| todo | 部署 SOP v1（文档+脚本版本化） | 明鉴 | cs2-1 |
| todo | 健康协议 v1（真 ack 非守护心跳） | 星桥 | cs2-2 |
| done | 全局注册表 E2 核心（三端在线+bb-gate 查询；剩余 step4 罗盘会话级） | 星桥 | cs2-2b |
| todo | 数据迁移 + i9 前缀分叉修复 | 星桥/i9 | cs2-3 |
| todo | mac-mini/i9/MBP 三端接入 | 星桥/i9 | cs3-* |
| todo | 故障切换演练（验收 A1-A4） | 星桥/明鉴 | cs3-4 |
| todo | 健康看板 + 自动恢复 | 星桥/4787d717 | cs4-* |

## 五、relations（新增）

- **comm-server 主线**：depends_on fnp（复用 FNP 信封/SSE 语义）；references rust-blackboard（产物）；requires 24h Linux 服务器（或 i9 fallback）
- **关联 BP-9**：agent-network#comm-server 阶段 cs0-cs4 与 rule-judge#R031（通讯永续·G2 通讯健康门）对齐——R031 是规则层，comm-server 是落地层

## 六、门禁链（v1.3 全）

① P0 通信契约冻结才进 P1 ② P2 状态契约才进 P3 ③ 每阶段 Rust 化达标 ④ comm-server：cs1 部署目标定案 → cs2 SOP 可复跑才进 cs3 三端接入 → cs4 运维 ⑤ mem-l2 MG4 写入治理落地才进 MG5 检索

---
*blueprint:agent-network · v1.3 · comm-server 通讯根治主线（用户定案 2026-09-03）*
> 2026-09-06 E2 全局注册表 cs2-2b 核心完成（三端注册在线；评估明鉴 mingjian-e2-registry-review-20260906；剩余: step4 罗盘 device-assets 会话级）
