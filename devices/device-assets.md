# 设备资产表 v1.1 · Device Assets

> 维护：session-5a5368af（设备协调智能体）· 2026-08-17 · v1.1（远程实测接入：向日葵 MCP 通道打通）
> 探测方式：Tailscale status + ping + **向日葵 MCP device_search/device_info**（远程实测已接入，2026-08-17 07:30）
> 权威登记：resource-registry.md §3「设备资产（Tailscale 组网）」

---

## 一、设备概览（4 台 + 关联设备）

| 设备 | 主机名 | OS | Tailscale IP | 状态 | 算力 | 生产定位 |
|---|---|---|---|---|---|---|
| **mac-mini**（本机） | CoreydeMac-mini.local | macOS 26.5.2 (25F84) | 100.120.203.20 | 🟢 在线（宿主） | Apple M4 / 10 核 (4P+6E) / 24GB / Metal 4 | 主工作台：DSH 智能体网络宿主 |
| **MacBook Pro** | MacBook-Pro | macOS 26.5.2 (Darwin 2550) | 100.112.111.120 | 🟢 在线（SSH 通 + CLD 运行） | **Apple M3 / 16GB** / 1512×982 / 磁盘 926Gi（13% 用） | **独立 DSH 节点**（CLD 0.1.0 运行，dsh 服务 57043）+ 移动生产力 + 备份节点候选 |
| **PC-i9** | DESKTOP-P8E7OP1 | **Windows 11 Pro** | 100.118.15.71 | 🟢 在线（MCP） | **i9-14900KF / 32GB / RTX 4060 Ti** | Windows 专属 + 高性能工作站（含 GPU） |
| **iPhone 17** | iphone171 | iOS | 100.98.251.77 | 🟢 在线 | — | 移动端/随手记录 |

> **2026-08-17 实测（向日葵 MCP 通道）**：4 设备 Tailscale 全部 active；MacBook Pro / PC-i9 均已在向日葵账号设备列表且在线（fastcode 各自独立）。
> **接入通道（用户选定 2026-08-17）**：向日葵 MCP（AweSun 16.3.0 + awesun-mcp-server，22 工具）——MCP 握手 ✅、device_search ✅、device_info ✅ 均已实测通过；账号含 SL-MCP 授权（超级会员）。token 存 ~/.dsh/devices/awesun.env（0600，不落知识库）。**限制**：① ssh 会话插件仅支持 Linux（MacBook Pro 需换路径）② 远程 CMD/桌面会话需先「手动远控一次」建立设备信任（待用户操作）。SSH 为备选：macbook 用户=coreyleung、PC-i9 用户=corey liang（公钥未装，仅登记归属）。

### 向日葵设备列表发现（关联设备）
| remote_id | 名称 | 硬件 | 状态 |
|---|---|---|---|
| 1687489763 | 天河店 | Xeon E5-2680 v2 / 64GB / GTX 1050 Ti / Win10 | 🟢 在线 |
| 1696416965 | foshan（佛山店） | Xeon E5-2666 v3 / 32GB / GTX 750 / Win10 | ⚪ 离线 |
| 1676234999 | chuheng-jiangnanxi | i5-6500 / 16GB / Win10 | ⚪ 离线 |
| 1669856948 | MacBook Pro（旧记录） | M3 / 16GB | ⚪ 离线（重复记录） |
| 1663274513 | iPad | iOS | ⚪ 离线 |

## 二、mac-mini（本机）详细实测（2026-08-17 07:12）

| 项 | 值 | 备注 |
|---|---|---|
| 型号 | Apple M4 | 10 核：4 性能 + 6 能效 |
| 内存 | 24 GB | — |
| GPU | Metal 4 | 本地推理可用（LM Studio） |
| 系统盘 | 460Gi，数据卷 **90% 满**（379Gi/460Gi，剩 46Gi） | ✅ 已改善（Step 1 回收 12.7G：95%→90%，2026-08-17） |
| 内存压力 | 交换 28.7G（used 28.2G / free 0.5G） | ⚠️ 高；根因=外卖采集栈（10 Chrome）+ LM Studio 常驻（de7b29de 实测：free 58MB/llama-server 4.4G/Virtualization 979M/openchronicle 963M/CLD 1.4G） |
| 负载 | **1min 22.0 / 5min 24.1 / 15min 27.7** | ⚠️ 持续 2.2-2.8 倍过载（10 核基准），疑似多会话 + Docker 后台叠加 |
| 运行时长 | 1 天 1 小时 | 上次重启 2026-08-16 06:00 前后 |
| 磁盘大头 | Docker 容器 58G、TRAE SOLO 6.2G、Notion 4.0G、Trae CN 3.9G、WeCom 2.9G、Lark 2.6G、Caches 7.0G | 合计 ~85G，可清理空间大 |

### 健康信号（v1.5 基线，每日快照对比）
1. ✅ 数据卷 90%（379Gi/460Gi，剩 46Gi）——Step 1 已回收 12.7G（95%→90%）；**Step 2 Docker 清理可再回收 20-40G**（待用户授权）
2. ⚠️ 交换区近满（28.7G used）—— 内存压力高，影响所有推理/渲染类任务
3. ⚠️ 负载持续 22-28 —— 明显过载；需定位是 DSH 多会话还是 Docker 常驻
4. 建议动作：Step 2 Docker prune（b241741f 安全清单就绪，待授权）

## 三、远程设备实测（向日葵 MCP device_info · 2026-08-17 07:30）

### MacBook Pro（remote_id 1639073357）
| 项 | 值 |
|---|---|
| CPU | Apple M3 |
| 内存 | 16GB（16384MB） |
| 系统 | macOS 26（Darwin 2550） |
| 分辨率 | 1512×982 |
| 向日葵客户端 | 16.2.3.28762 |
| 在线 | ✅（login 2026-08-17 06:02:46） |

> ✅ **2026-09-06 SystemGraph 资产吸收（明鉴分配，收口归罗盘）**：MBP /Applications/SystemGraph.app **v1.4.0/build4 已确认安装**（新版 DMG ditto，实测 CFBundleShortVersionString=1.4.0/CFBundleVersion=4；明鉴 v3 核实正确，此前「CFBundleVersion=1 待确认」标注系 v1.0.0 时代旧产物 .bak 观察已更正）；旧版备份 SystemGraph.app.bak-1.0.0 保留；主源主权在 mac-mini（~/system-graph-app）；CloudBase 推送通道保留（数据镜像，老登）；黑板 notes/mbp/ 域 SystemGraph 相关 18 key 已归档收口至本机 data/device/mbp-sg-archive/

### PC-i9（remote_id 1640748650）
| 项 | 值 |
|---|---|
| CPU | **Intel Core i9-14900KF** |
| 内存 | 32GB（32581MB） |
| 系统 | **Windows 11 Pro** |
| 主板 | ASUS TUF GAMING B760M-PLUS WIFI II |
| 磁盘 | KINGSTON SNV3S1000G（1TB NVMe）+ WDC WD20EARZ（2TB HDD） |
| 显卡 | **NVIDIA GeForce RTX 4060 Ti**（用户确认 2026-08-17；MCP 显示 OrayIddDriver 为远程虚拟驱动，非真实显卡） |
| 向日葵客户端 | 16.5.0.30905 |
| 在线 | ✅（login 2026-08-16 01:07:12） |

> ⚠️ **算力定位升级**：PC-i9 = i9-14900KF（24 核高性能 CPU）+ RTX 4060 Ti（8GB 独显）——**GPU 渲染/推理任务首选**（macOS 侧无 CUDA 生态）。待远程会话打通后补磁盘剩余/负载实测。

> ✅ **2026-08-18 DSH 节点达成（D4②）**：PC-i9 已验证 dsh headless 链路（dsh 0.1.0-rc.5，位于 C:\Users\admin\.dsh\profiles\node_modules 既有安装；headless profile=dsh-base+dsh-headless、web profile 含 PhoneUse MCP 配置）——端到端实测通过（"say OK and exit"→OK、自定义任务→42）；启动器 `C:\Users\admin\dsh-run.ps1`（用法：`powershell -ExecutionPolicy Bypass -File dsh-run.ps1 "<task>"`）；凭据从 .credentials.yaml 冒号解析注入环境变量（不落明文，遵守凭据纪律）；命令通道=向日葵 cmd2（remote_id 1640748650，大输出超时策略=断开重连）。**PC-i9 现为分布式网络第 3 个 DSH 节点**（mac-mini 宿主 + MBP 独立节点 + PC-i9 headless）。注：Docker 桌面重启不影响 Ollama（11434 为 Windows 原生服务非容器）；tailscale 容器随 Docker 重启短暂断连（数秒恢复）。

### 待采集（远程会话建立后）
| 设备 | 待采集项 |
|---|---|
| MacBook Pro | 磁盘容量/剩余、负载、数据目录清单（ssh 会话插件仅支持 Linux，需另辟路径：桌面会话或 SSH 备选） |
| PC-i9 | 磁盘剩余、负载、数据目录清单（需用户先手动远控一次建立信任） |

## 四、探测机制（v1.2）

| 项 | 方式 | 频率 |
|---|---|---|
| 在线状态 | **tailscale status 解析**（offline, last seen 提示词；43b1a2d3 权威口径）替代纯 ping | 每日快照时 |
| 直连质量 | `tailscale ping <主机名>` 区分 direct/relay（relay=DERP 需打洞优化） | 每周 |
| 服务可达性 | `tailscale serve status` + 3081 代理 GUI 端口日志 | 每周 |
| 本机身份 | `tailscale ip -4` 核对 IP 漂移 | 每日快照时 |
| 远程硬件 | 向日葵 MCP device_info（CPU/内存/OS/磁盘/主板） | 每周 + 变化时 |
| 远程会话 | 向日葵 control_connect（cmd2=Windows / desktop；ssh 仅 Linux） | 按需 |
| 本机负载 | uptime / vm.swapusage / df（与 6e49710e/9910d4b2 宿主层互认） | 每日快照时 |
| 代理连通性 | lsof 监听 + curl 状态码（200/426/RPC 200；43b1a2d3 权威） | 按需 |
| 告警阈值 | 数据卷 ≥90% 满 / 负载 ≥2× 核数 / 设备离线 | 触发即报用户 |

> 权威口径分层：tailnet 探测=43b1a2d3（dsh-health.py/tailscale status）；宿主层健康=6e49710e/9910d4b2；远程设备硬件/会话=向日葵 MCP（本会话）；磁盘/负载快照=本会话+6e49710e 互认。
> 2026-08-17 补充：mac-mini 端口登记——media-hub 8090（媒体内部专栏静态站，仅内网，属主 54e809ed，内容 ~/dsh-collab/media/hub/）
> 2026-08-17 P3 达成：external-link-mcp SSE 端点 8910（mac-mini tailnet IP 100.120.203.20:8910/mcp）——PC-i9 经 Tailscale 远程调用验证通过（tools/list + channel.status 企微 bound，官方 SDK 客户端）；Tailscale 内任意设备可调用；MBP 上线同理接入；客户端接入指南 ~/dsh-collab/external-link-mcp-client-onboarding.md
> 2026-08-17 MBP 对接达成：MBP 已有 CLD 0.1.0（自研产物）+ dsh 服务 57043 运行 = 独立 DSH 节点；MBP → mac-mini SSE 端点 curl 握手 + SDK 全链路（Node v25.5.0 /opt/homebrew/bin，SDK 1.30.0）双证通过——「MBP 独立 DSH 节点 ↔ mac-mini MCP 服务器」打通；i9 后续再上（需装 CLD+DSH）
> ✅ **2026-09-06 E2 会话级在线层（R-ERR4 发现注册表接入）**：device-assets 扩展会话级数据源——星桥服务器发现层 `data/discovery/agents/<device>`（xingqiao.meetfunbp.com:8792，schema v1，PUT 覆盖/心跳活性 G5）。查询工具：`python3 ~/dsh-collab/comm-server/bb-gate.py registry`。实测（2026-09-06）：mac-mini=3 会话在线（星桥协调者/明鉴 SystemGraph/HR 司库）、i9=1 会话（i9-coordinator）、mbp=1 会话（MBP 资源中枢）——**比设备级在线更细（会话粒度）**。设备资产表现有：设备级（Tailscale/向日葵）+ 会话级（discovery 注册表）双数据源。写入方=各端心跳代理（hb-fwd/executor 自注册）；读=全体。E2 核心完成，解 agent_peers 孤岛。

## 五、更新日志

| 时间 | 版本 | 变更 |
|---|---|---|
| 2026-08-17 | v1.0 | 首版：4 设备概览 + mac-mini 全量实测 + 健康基线（磁盘 95%⚠️/交换近满⚠️/负载 25⚠️） |
| 2026-08-17 | v1.1 | 向日葵 MCP 通道打通：远程实测接入（MacBook Pro=M3/16G/macOS26、PC-i9=i9-14900KF/32G/Win11/4060 Ti 独显）；发现 5 台关联设备（天河店在线/佛山/江南西/旧 MBP/iPad）；接入限制记录（ssh 仅 Linux、cmd2 需首次远控信任） |
| 2026-08-17 | v1.2 | 探测机制升级：tailnet 权威口径采纳（43b1a2d3：tailscale status 解析/direct-relay/serve status/IP 漂移/curl 状态码）——三源交叉变四源 |
| 2026-08-18 | v1.3 | **D4② i9 DSH 节点达成**：dsh 0.1.0-rc.5 headless 链路验证通过 + dsh-run.ps1 启动器就位（C:\Users\admin\dsh-run.ps1）；凭据冒号解析注入不落明文；PC-i9 = 分布式网络第 3 个 DSH 节点；Docker 桌面重启不影响 Ollama（原生服务） |
| 2026-09-06 | v1.4 | **MBP SystemGraph 资产吸收（明鉴分配）**：MBP /Applications/SystemGraph.app v1.4.0/build4 确认安装（旧版备份 .bak-1.0.0）；18 key 归档收口至 data/device/mbp-sg-archive/；主源主权 mac-mini |
| 2026-09-06 | v1.5 | **存量工具 R006 十项补全**：6 工具升级 v1.1.0（awesun-mcp.py/sh/mcp-sse-test.js/mbp-bus-client.sh/mbp-node-agent.py/i9-node-agent.py）+usage/--help/--version；tool-readme/ 文档目录 + CHANGELOG；KB 落链 |
| 2026-09-06 | v1.6 | **E2 会话级在线层（R-ERR4）**：device-assets 接星桥发现注册表 data/discovery/agents/<device>（bb-gate.py registry 查询）；实测 mac-mini 3 会话/i9 1/mbp 1——设备级+会话级双数据源 |
