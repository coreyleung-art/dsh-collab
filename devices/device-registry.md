# 分布式智能体网络 · 设备注册表

> 用途：登记所有已接入网络的设备/节点 + 分发接入凭据/配置引用（登记与分发中心）
> 维护：设备协调 5a5368af（专属）· 登记口径：接入即登记，变更即更新
> 2026-08-17 · v1.0

---

## 一、已登记节点

| 节点 ID | 设备 | Tailscale IP | 角色/能力 | 接入状态 | 验证方式 | 注册日期 |
|---|---|---|---|---|---|---|
| node-macmini | mac-mini | 100.120.203.20 | MCP 服务器主实例 / 总线宿主 / DSH 宿主 | ✅ 运行 | 本机 SDK 全链路 | 2026-08-17 |
| node-pci9 | PC-i9 | 100.118.15.71 | 远程 MCP 调用节点（i9-14900KF / 4060 Ti GPU 算力 / Docker+WSL2 fi-dify 栈） | ✅ 已接入 | SDK 1.30.0 真机实证 | 2026-08-17 |
| node-mbp | MacBook Pro | 100.112.111.120 | DSH 节点（CLD 0.1.0 运行 + dsh 57043）+ MCP 客户端 + 备份节点候选（926Gi/13%） | ✅ 已接入 | curl + SDK 双证（Node v25.5.0） | 2026-08-17 |
| node-mbp-agent | MBP 智能体（mbp-node） | 100.112.111.120 | **MBP 资源执行节点**（persona 已部署 ~/.dsh/.agent-presets/mbp-node/；本地 bash/文件/CLD 能力实证） | ✅ 已任命 + **全自动闭环** | uname/df/memory 本地执行实证 + 总线桥端到端（done 5/failed 0） | 2026-08-17 |
| node-iphone | iPhone 17 | 100.98.251.77 | 移动端（可选接入） | ⏳ 未接入 | — | — |

### 节点能力补充（5a5368af 侧实测 · 2026-08-17）
| 节点 | 补充能力 | 验证细节 |
|---|---|---|
| node-macmini | external-link-mcp SSE 服务器（8910）/ agent presets（liangshen/librarian/waimai-ops/mbp-node 可同步）/ devices 档案（资产/数据地图/任务映射） | SDK 客户端全链路 |
| node-pci9 | 向日葵 cmd2 远程命令 / SSH 22 开（待凭据）/ 12 类数据资产扫描完成 | SDK 1.30.0 真机 |
| node-mbp | SSH 通道（mac-mini 公钥授权）/ 向日葵 desktop/forward/file 会话 / M3 算力 / 磁盘 926Gi 备份候选 | curl + SDK 双证 |
| node-mbp-agent | dsh CLI headless 执行（`--profile dev "task"`）/ mbp-node persona（定位/能力/任务类型/边界） | uname/df/memory 实证 |

## 二、分发配置（接入引用）

| 配置 | 值 | 分发方式 |
|---|---|---|
| MCP 端点 | http://100.120.203.20:8910/mcp | 提示词模板 + onboarding 指南 |
| 总线桥端点 | http://100.120.203.20:8790/bus/* | 设备 agent 轮询取/回 |
| 鉴权 | SSE_TOKEN / X-Webhook-Token（内网可暂不启用） | 凭据 0600 私有 |
| 通道凭据 | keyring/credentials.enc（0600） | 只传引用不落盘 |
| MBP agent 执行 | MBP dsh CLI（bin.js）+ `--profile dev` headless | mbp-node preset（~/.dsh/.agent-presets/） |
| SSH（mac-mini→MBP） | coreyleung@100.112.111.120（公钥授权） | 已配置 |

## 三、接入流程（新设备）

1. 加入 Tailscale 组网（5a5368af 协助）
2. 取一键接入提示词（onboarding-prompt.md）+ 介绍页（external-link-mcp-intro.md）
3. 连 MCP 端点验证（curl 握手 / SDK 全链路）
4. 通知协调者 fa1f9150 广播到岗 + 本表登记

## 四、维护纪律

- 接入即登记、变更即更新（状态/能力/验证方式）
- 分发只传配置引用，凭据值不落本表（0600 私有）
- 节点掉线/下线标注状态，长期下线移入历史
- 与 device-assets.md（硬件台账）/ task-env-map.md（任务路由）联动

---
*设备注册表 v1.1 · 2026-08-17 · 5a5368af 维护（mbp-node 任命完成 + 节点能力补全 + SSH/MBP agent 分发配置）*
