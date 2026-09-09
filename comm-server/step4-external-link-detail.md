# external-link Step 4 迁移窗口 · 展开说明（2026-09-06 星桥）

## 现状（驿使 external-link-mcp 域）
| 组件 | 端口 | 形态 | 现状可达性 |
|---|---|---|---|
| external-link-mcp (index.js) | 8910 | StreamableHTTP MCP（--sse 模式，跨设备 P3）| 本机，Tailscale 内可达，公网不可达 |
| webhook.js | 8790 | HTTP /send /read（企微 webhook 收发）| localhost 仅本机 |
| wecom-inbox.js | 长连 | 企微官方 API 长连接监听（四态/进群/全量入库）| 本机，依赖 mac-mini 在线 |
| bus-bridge.js (external) | 8791 | 消息总线（已被 comm-layer 服务器版覆盖）| 已迁 ✅ |

## 迁移内容（Step 4 = 外链层公网化）
1. **SSE 8910 → 服务器**：external-link MCP 的 StreamableHTTP 端点部署 xingqiao——外部设备/云端 MCP 客户端可**公网直连** external-link 的 channel.send/status + bus.send 能力（当前仅 Tailscale 内）
2. **webhook 8790 → 服务器**：企微 webhook 回调需公网 URL——服务器公网可达后企微消息直达（当前 localhost 需隧道）
3. **wecom-inbox token 迁移**：企微长连 token 迁服务器（安全评估——token 秘密，迁移需轮换+0600）
4. **域名指向**：xingqiao.meetfunbp.com 已指服务器——外链入口用子域/路径（如 xingqiao.meetfunbp.com:8910/mcp 或子域）or 本机+服务器双入口（备灾）

## 为什么迁（价值）
- 外链通道（企微/飞书/外部智能体）**公网 24h 可达**——不依赖 mac-mini 在线
- 驿使外链交互（客服确认卡/外部触发）在 mac-mini 重启期间不断

## 阻碍与风险
- wecom token 安全迁移（秘密 0600 + 轮换）
- SSE MCP 对外暴露鉴权（防未授权调用——需 token/白名单，同 bus-bridge X-Webhook-Token 模式）
- webhook 公网端口（服务器已有 8791/8792 放行先例——需再加）
- 双入口语义（本机+服务器同时收会重复？需单活或去重）

## 与蓝图
- = comm-server 迁移计划 Step 4（外链层）+ 明鉴评估 S1（external-link 迁服务器）
- 优先级：用户定近期做（MCP 客户端接入需求）
