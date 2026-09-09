# 🛰 设备通讯桥视图（并入 🖥 硬件载体 Tab）

- 作者: 明鉴 v2 · 日期: 2026-09-03
- 状态: ✅ 已上线（bb-blueprint-gallery.py + device-links.json 双文件）

## 需求
「设备与设备之间的通讯桥如何呈现」→ 用户裁定：**并入现有 🖥 硬件载体 Tab**
（物理拓扑 ⇄ 设备通讯桥 切换）+ **静态链路 + 实时探测**。

## 心智模型
- **物理拓扑视图**: 原有 —— 设备/服务器/云端的业务归属关系（托管/远程/算力委托）。
- **设备通讯桥视图**(新): 设备为中心，**真实通讯通道**为边 —— 每条边 = 一条通道
  （Tailscale 隧道/黑板总线/agent-bus/SSH/向日葵远控/Funnel 公网/云桥/本地托管），
  带通道类型颜色、协议端口、方向箭头；hover 边高亮并显示协议与端口。
- 边状态: 有探针的边绿=实时探通 / 红虚线=断开；同对端多通道以平行曲线分隔。

## 实时探测（权威源，25s 缓存，60s 前端轮询 + 手动「↻ 重新探测」）
| 通道 | 探测方式 |
|------|---------|
| Tailscale 隧道 | `tailscale status` 解析 peer 在线集（ICMP 会被防火墙误判，弃用 ping） |
| 黑板/本地 http 服务 | urllib GET，4xx 也视为通（服务在响应即活） |
| Funnel 公网 | HTTPS GET https://coreymac-mini.taild3fd86.ts.net |

## 数据文件: data/blueprint/gallery/device-links.json
- 8 通道类型（颜色/图标）: tailscale🔵 blackboard🟣 agentbus🟣 ssh🟡 sunflower🟡 funnel🟢 cloud⚪ local◽
- 17 条链路（macmini 中枢: ↔MBP Tailscale+黑板注入、↔MBP-agent、↔i9 Tailscale+向日葵+远程MCP、
  ↔iPhone、→天河/佛山/江南西 向日葵、本机 Verdaccio/GeneBank/Coze桥、→企微/飞书/Coze 云端、Funnel 入口）
- 探测锚点 6 条（mbp/pci9/iphone Tailscale、Funnel、黑板 8792、Verdaccio 4873）

## 实测（2026-09-03）
- /api/hwcomm: nodes 14 / links 17 / probe {mbp:通, pci9:通, iphone:断(offline 16d), Funnel:通, 黑板:通, Verdaccio:通}
- headless Chromium 截图 + DOM 断言 9/9 通过（canvas 渲染 80 色非空）
- SystemGraph.app 已同步最新版并重启（launchctl 托管）

## 代码变更
- scripts/bb-blueprint-gallery.py:
  - 后端: `build_hw_comm_graph()` + `probe_comm_channels()` + `ts_online_set()` + `/api/hwcomm` + `/api/hwprobe`
  - 前端: `renderHardware()` 双视图切换；`renderHwComm()` + `refreshCommProbe()`；
    `buildForceGraph` 增加 isHwComm 模式（平行曲线/箭头/状态着色/通道标签）+ drawArrow()
  - 深链: `#hardware-comm` 直达通讯桥
- data/blueprint/gallery/device-links.json: 新建

## 后续候选
- 通道日志/流量统计（黑板 seq、agent-bus 消息量 → 边粗细）
- 断线自动告警（探针连续 2 次失败 → 置顶提醒）
