# MCP 服务器分布式智能体网络 · 推进状态台账

> 维护：HR 驾驶舱 session-a17a52f8 · 2026-08-18 · 检索实测版
> 来源：external-link-mcp-plan/intro/deploy/onboarding + 运行时实测

## 一、已建成/生效（实测 2026-08-18）

| 组件 | 状态 | 证据 |
|---|---|---|
| MCP 服务器 external-link-mcp（8910 SSE/Streamable HTTP） | ✅ 运行 | index.js --sse 进程在（重启维护中） |
| channel.send / channel.status（分级 P0-P3） | ✅ 上线 | 本 agent 工具面可用 |
| 企微通道 | ✅ bound | channel_status 实测（app_id 授权） |
| 飞书通道 | ✅ bound | channel_status 实测（cli_aa0842...） |
| webhook 8790 | ✅ 运行 | PID 48060 |
| bus-bridge 8791（~/.dsh/bus-bridge/） | ✅ 常驻 | launchd PID 87197（与 restart-window-batch 一致） |
| wecom-inbox 长连接 | ✅ 运行 | 监听重启维护中（92623479 侧） |
| P3 跨设备闭环（PC-i9 远程握手） | ✅ 达成 | onboarding 验证清单（08-17） |
| MCP 工具注入本 agent | ✅ 生效 | mcp__external-link__* 4 工具可用 |

## 二、缺口/阻塞（实测发现）

| # | 缺口 | 证据 | 影响 |
|---|---|---|---|
| 1 | ~~bus.send unauthorized~~ → **已修复 ✅（2026-08-18）** | 根因=8910 旧代码实例无 busBridgeToken 逻辑；重启加载 v0.3 后自动带 token | 外链实测：curl 带 token ok / MCP bus.send 入队成功（task 904a127c）→ **MBP 自动执行回传（Darwin MacBook-Pro.local）全链路闭环** |
| 2 | MBP node **在线可执行 ✅（实测 2026-08-18）** | 外链 bus.send→MBP 回传 Darwin 系统信息 | MBP 侧桥接执行节点已实际执行任务；常驻轮询按 P1 跟踪 |
| 3 | 飞书外发未端到端验证 | bound 但外链未完成计划列「secret 扫码流程」 | 飞书通道仅绑定未证实可发 |
| 4 | MBP 异步审批器开发中 | hr-handover 资产清单 | 审批队列功能未落地 |
| 5 | SSE_TOKEN 未启用 | onboarding 护栏「Tailscale 内网阶段可不启用」 | 云端暴露前必须启用（暂不阻塞） |

## 三、继续推进方案

### P0 · 现在可做（不依赖用户）
1. **bus.send 鉴权打通**：定位 MCP 工具 bus.send 的 token 透传；协调外链 92623479 核对 bus-bridge WEBHOOK_TOKEN 与客户端密钥同步（mac-mini/MBP 两侧）→ 实测「下发→执行→回传」全链路
2. 修通后跨设备实测：本 agent 发 info 任务 → mbp-node（在线则直连，离线则验证队列）
3. 登记表/台账更新：bus-bridge 部署位置（~/.dsh/bus-bridge/）+ 通道状态（飞书 bound）+ 缺口入账

### P1 · 等用户/重启窗口
4. CLD 重启后 bus-mcp 插件正式生效验证（已排 §5.2 #1：QA/外链/健康三方复验）
5. MBP node 联网后接入：同路径验证 + 常驻轮询（bus-bridge-node-prompt.md 定义就绪）
6. MBP 异步审批器落地（用户开发中）→ 登记 + 审批队列接入

### P2 · 增强
7. dsh-messaging 通道对照（等供应链评估）
8. SSE_TOKEN 启用（云端暴露前）
9. iPhone 端点验证（可选）+ 新设备接入引导（onboarding-prompt 就绪）

## 四、待办登记
- [x] bus.send 鉴权修复 + 全链路实测（P0，外链 92623479，**已闭环**：curl 带 token ok + MCP 入队 + MBP 回传）
- [x] 残余澄清（92623479）："No valid session" 是 MCP Streamable HTTP **预期行为**（8910 重启清空 session 表，客户端需重新握手；官方 stateful 模式标准返回）——非功能缺口
- [ ] 可选增强（低优先）：客户端封装增加「收到 No valid session 时自动重建 Client」逻辑（curl/MCP 新建 Client 已验证可用）
- [ ] MBP node 接入验证（P1，待联网）
- [ ] 飞书外发端到端验证（P1，用户扫码/secret）
- [ ] 异步审批器落地登记（P1，用户 MBP）
