# 分布式智能体网络 · MCP 服务器介绍页

> 面向：新智能体设备 / 新智能体角色接入本网络的标准介绍
> 服务器：external-link-mcp（ELA-2026-0817-03，外链通讯员 92623479 维护）
> 端点：`http://100.120.203.20:8910/mcp`（mac-mini 宿主，Tailscale）· 本机 `http://127.0.0.1:8910/mcp`
> 总线桥：`/bus/*` 队列部署于 mac-mini（bus-bridge，待上线）
> 2026-08-17 · 协调者 fa1f9150 制度化

---

## 一、这是什么

**跨设备跨平台外链 MCP 服务器**——分布式智能体网络的「统一通道枢纽」。任何设备/智能体经 MCP 协议接入后，即可：
- **出向**：推消息到企微/飞书/钉钉等外部通道（通知/告警/报告）
- **入向**：接收外部消息并按规则路由（客服/运营/洞察）
- **总线桥**：与 mac-mini agent bus 双向联通（跨实例任务下发/结果回传）
- **跨设备**：Tailscale 内任意设备（mac-mini/MBP/PC-i9）即插即用

## 二、能力清单

| 工具 | 用途 | 级别 | 实现状态 |
|---|---|---|---|
| `channel.send` | 出向推送（企微/飞书/钉钉） | 分级 P0-P3（P3 系统运维拦截） | ✅ 已上线（MCP + HTTP 双入口） |
| `channel.status` | 查询各通道绑定/健康 | 只读 | ✅ 已上线 |
| `bus.send`（MCP 工具 8910 + HTTP `/bus/send`） | 总线桥任务下发（入队，`wait=true` 同步等结果） | 双向 | ✅ 已上线（SSE 实测入队成功） |
| `bus.receive/reply/outbox`（HTTP 8791） | 任务队列取/回/拉（含 `?consume=1`） | 双向 | ✅ 已上线（mac-mini bus-bridge 运行中，全链路实测闭环） |

> 现状说明：MCP 工具面 = `channel.send` / `channel.status` / `bus.send`（v0.3）；`/bus/*` 队列由 bus-bridge 服务提供（mac-mini 本机 8791，PID 62137），MBP 侧客户端经 Tailscale 访问 `http://100.120.203.20:8791/bus/*`。

## 三、接入三步（新设备/智能体）

1. **网络**：加入 Tailscale 组网（联系设备协调 5a5368af 登记）
2. **客户端**：用 MCP SDK（Node/Python）连端点 `http://100.120.203.20:8910/mcp`（Streamable HTTP，mac-mini 宿主），或 Claude Code/Cursor 配置
3. **提示词**：复制「一键接入提示词」（见 onboarding-prompt.md），写入你的角色定义

> 跨设备调用验证：PC-i9 / MBP / mac-mini 均经 Tailscale 调用 8910 实测通过（SDK 1.30.0）。

## 四、安全与纪律

- 凭据纪律：通道凭据在 0600 文件（keyring/credentials.enc），跨设备只传引用
- 云端暴露前必须启用 SSE_TOKEN（X-MCP-Token）；Tailscale 内网阶段可不启用
- P3 系统运维来源默认拦截（用户指令：系统运维侧信息暂不推送企微）
- 资源冲突规范集 v1.1（~/dsh-collab/resource-conflict-policy.md）：查灯/声明/即关/替代/错峰
- 设备注册表：接入后必须登记（device-registry.md，5a5368af 维护）

## 五、已接入节点（见 device-registry.md 完整表）

| 节点 | 角色 | 验证 |
|---|---|---|
| mac-mini（100.120.203.20） | **MCP 服务器宿主**（8910/8790）+ 总线桥部署侧（/bus/* 待上线） | 本机 SDK 全链路 |
| PC-i9（100.118.15.71） | 远程 MCP 调用节点 | SDK 1.30.0 真机实证 |
| MBP（100.112.111.120） | DSH 节点 + MCP 客户端 | curl + SDK 双证 |

> 主机关系（协调者权威实测）：MCP 服务器（8910）= **mac-mini** 宿主；MBP 无 8910 服务（SSH 实测 lsof 无输出）。外链通讯员会话亦运行于 mac-mini。

## 六、相关文档

- 接入技术细节：`external-link-mcp-client-onboarding.md`
- 一键接入提示词：`onboarding-prompt.md`
- 设备注册表：`devices/device-registry.md`
- 总线桥设计：`external-link-mcp-plan.md`（P3 跨设备）+ 总线桥部署包：`external-link-bus-bridge-deploy.md`（92623479）

---
*介绍页 v1.3（bus.* 已上线更新）· 制度化接入体系 · 2026-08-17*
