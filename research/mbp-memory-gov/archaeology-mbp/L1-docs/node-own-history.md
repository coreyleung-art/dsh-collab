# MBP 节点自身考古

> 考古组：节点自身考古组（node=mbp）｜日期：2026-08-26
> 范围：~/.dsh/（177MB）+ ~/dsh-collab/（482MB）
> 纪律遵守：bus-bridge-token / credentials.yaml / settings.yaml / market tokens 只记存在，未读未记值。

## 节点身份与能力清单（profile/插件/工具）

**节点身份**：`mbp-node` =「MBP 资源节点」，运行于 MacBook Pro（M3/16G/macOS 26.5.2），分布式智能体网络的 MBP 侧执行节点。经 MCP 总线桥/黑板与 mac-mini 中枢（100.120.203.20:8792）双向联通，执行 MBP 本地命令/文件/CLD 能力并回传。身份定义见 `~/.dsh/.agent-presets/mbp-node/`：
- `preset.yml`：名称「MBP 资源节点」，order 5，一句话定位（MCP 总线桥与 mac-mini 双向联通）。
- `agent.cordis.yml`：persona（协调者 fa1f9150 提供）——定位、核心能力（资源执行/任务接收/结果回传/状态上报）、任务类型（算力/文件/信息/CLD）、边界纪律（危险操作需确认、凭据不落盘、敏感不跨总线传明文、操作前查灯、高算力先报）。

**Profile 清单**（~/.dsh/profiles/，均为 pnpm 本地 link 装配，DSH 版本 0.1.0-rc.6）：
| Profile | 装配 bundle | 用途 |
|---|---|---|
| `dev` | @deepseek-ai/dsh-base + dsh-headless + dsh-plugin-hello + dsh-plugin-local-projects + dsh-plugin-fapai-intel | 无头/开发调试 |
| `market` | dsh-base + dsh-web-app + dsh-plugin-market | 插件市场 Web |
| `web` | dsh-base + dsh-web-app + local-projects + market + sandbox-policy-ui + fapai-intel | GUI（CLD 桌面应用运行的 profile，含 .bak-cld 备份） |
| `node_modules` | 全部软链到 `/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules` | 运行时共享依赖（含 @deepseek-ai 202 个包） |

**本地自研插件（均 v0.1.0，源码在外链项目目录）**：
- `dsh-plugin-fapai-intel`：法拍行业情报系统——采集/去噪/竞对追踪/向量检索/定时简报（fapai_collect/maintain/query/report/scan_competitors/status 六工具）。
- `dsh-plugin-hello`：hello 工具（工作流示例）。
- `dsh-plugin-local-projects`：一键扫描/读取/统筹本地项目，侧边栏入口 + 项目面板。
- `dsh-plugin-market`：插件市场——监控 npm @deepseek-ai 官方包 / GitHub / Gitee，一键授权与发布。
- `dsh-plugin-sandbox-policy-ui`：沙箱安全策略控制台（read-only / workspace-write / danger-full-access 三档可视化调整）。

**平台级能力**（来自 market 官方 @deepseek-ai 注册表 191 个官方包 + 实际装配）：bash/fs/subprocess/PTY 执行、沙箱策略、后台任务、subagent（fork/spawn）、workflow、ralph、goal、todo、skill 装载、web 搜索、MCP 客户端桥、LLM（deepseek adapter + pi-ai）、会话持久化（JSONL + SQLite FTS5 查询）、spill/attachment/schedule/telemetry(otel)。

**插件市场**（~/.dsh/market/index.json，1.3MB，scannedAt 2026-08-25T19:20Z）：收录 **2263** 个插件条目（bundle 979 / other 763 / service 408 / ui 56 / tool 50 / command 7；来源 GitHub 2073 + npm 190；官方 191）。tokens.json 仅 2B 占位。

## 数据资产清单（data/ 下各库的规模与主题）

- **~/.dsh/data/fapai-intel/**（136K，08-21 建成，唯一持久数据域）：
  - `sources.json` 26 个信息源登记（官方/机构/媒体/平台/社区分级）
  - `competitors.json` 42 家竞对（全案服务商/内容流量/代运营培训/加盟招商/司辅机构/平台竞合 六类）
  - `noise-rules.json` 9 条噪音过滤规则
  - `articles.json` 27 条采集条目（stats: 采集 2 轮 kept 6 / downgraded 5，主题：法拍房市场、易槌拍卖/润鸿/法辅在线司辅机构）
  - `vectors.json` 64KB，6 条向量化条目（本地 embedding）
- **~/.dsh/storages/**：`workspace.json`（3 个工作区登记：`coreyleung`@~ 14 会话、`法拍辅助法拍项目`@Desktop 3 会话、`景鸿国际项目`@~/景鸿国际项目 1 会话）+ `session_projcache.json`（112KB 投影缓存）。
- 另有会话内大资产不落 data/：法拍信号源雷达 App（Desktop 项目，非本节点数据域）；景鸿国际向量库建在会话工作区。

## 会话与记忆组织

- **存储**：~/.dsh/sessions/（70MB）按工作区目录分组（路径以 UTF-16BE 百分号编码转义，如 `--Users-coreyleung-Desktop-~6CD5~62CD~8F85~52A9~6CD5~62CD~9879~76EE--`=Desktop/法拍辅助法拍项目）；每个会话一个目录，内含 zstd 压缩的事件溯源 JSONL（session.jsonl.zstd）。
- **组织方式**：事件流（session / permission·preset / sandbox·mode / approval·policy / agent·inbox·spliced / turn·start / step·start / user·message …），可回放、可统计。
- **规模**：4 个工作区约 70 个会话目录，覆盖 08-15 → 08-26。最大会话：CLD 桌面 GUI 封装（46 用户消息/32 轮）、mac-mini dsh 崩溃排查（104 用户消息/78 轮）、法拍行业调研（198 用户消息/124 轮）、i9 故障排查（55/47）、景鸿国际深度调研（36/25）。
- **主题谱系**：DSH 插件生产工作流 → CAH 跨设备工具 → CLD 桌面封装 → 总线桥/黑板联调 → MBP 资源验证 → 法拍情报系统（调研/工具联调/六轮代码审计）→ 景鸿国际（移民/教育/房产向量库）→ Rust 环境安装 → i9 协助运维 → MBP 全量深度考古（进行中）。
- **记忆**：无独立 memory 域；记忆载体 = 会话日志 + archeology-from-i9 拉取的 i9 方法论框架（五层挖掘 L1 文档→L2 记忆→L3 会话→L4 语义→L5 资产；6 步收尾：落盘→sediment→向量化→registry→report→同步中枢）。

## 关键组件（bridge/events/executor）职责

位于 ~/dsh-collab/devices/（本节点分布式执行栈，三件套 + 辅助）：

| 组件 | 版本/形态 | 职责 |
|---|---|---|
| `node-bridge` | v1.0.7，Rust 编译 Mach-O（621KB） | 总线桥主程序：连接黑板 100.120.203.20:8792，任务队列 GET/PUT/DELETE（/tasks、/notes/queue），`status=online` 心跳 + capabilities（shell/ollama/dsh/rust-bridge），本地 Ollama qwen2.5:7b 推理，health 上报；`bridge_ver=1.0.7`。启动日志 ~/dsh-collab/logs/node-bridge.log（4 个 ~5MB 轮转 ≈ 15MB）。 |
| `blackboard-events.py` | v1.0 | 黑板事件桥：轮询中枢黑板 → 版本/时间戳差异检测 → 双路输出：① SSE 推送 127.0.0.1:8803/events ② 落盘 `~/.dsh/inbox/notes/<key>-<epoch>.json` + touch `~/.dsh/inbox/WAKE`（离线不丢事件）。监听 notes/mbp/、notes/collab/、tasks/mbp/、nodes/mbp/heartbeat、notes/i9/*mbp*。launchd 常驻（~/.dsh/blackboard-events.pid）。 |
| `mbp-node-agent.py` | v1.0 | 资源节点执行器（任务卡协议，与 i9 同构）：中枢 PUT /tasks/mbp/cmd（action=shell|info|dsh|ollama|scan）→ GET 拉取 → 执行 → PUT /tasks/mbp/result → DELETE 清卡；DSH_CLI 直指 CLD runtime bin.js。stdout 落 `mbp-agent.log`（**512MB**，err 0B）。 |
| `mbp-memory-vectorize.py` | v1.0 | 考古记忆向量化（零依赖）：文档→分块→ollama bge-m3 嵌入→JSON 向量库（~/dsh-collab/archaeology-mbp/vector-kb），build/query/status。 |
| `outbox/` | — | 节点发信暂存（ready.json："MBP v1.0.6 outbox 已就绪"）。 |

**消息邮箱**：~/.dsh/inbox/（34MB，8686 个 json）——跨节点消息，前缀主题：stab×101（i9 压测 50 连发）、coordinator×14、autonomy×7、rust×3（rust-survey/rust-network-summary/rust-hardening-request）、docker/training/erp/sediment/protocol/channel/events 等；`notes/` 子目录 58 条 notes__mbp__* 事件桥落盘。~/.dsh/outbox/ 为空。

## 节点发展时间线（从目录时间戳/log 推断）

- **08-15 15:03~**：~/.dsh 诞生（credentials/settings/anonymous-id），首批会话：审批策略调整、DSH 插件生产工作流、CAH 跨设备工具。
- **08-15 15:27~**：dsh-plugin-local-projects 工作区建起；**15:30 起** CLD 桌面 GUI 封装大会话（dsh→CLD 设想落地，46 用户消息）；**16:24** mac-mini dsh 崩溃排查（104 消息，跨机运维起点）。
- **08-15 17:23**：profiles/ 与 .agent-presets/mbp-node 建立（节点人格 preset 落盘）。
- **08-16 15:23**：MBP 桥总线节点智能体完整定义会话。
- **08-17 23:21~**：MBP 资源验证会话（uname/df 系列）；23:34 bus-bridge-token 生成（桥认证上线）。
- **08-18 04:05**：DSH client 插件构建机制研究；**11:52** mbp-bus-client.log 显示任务处理（action=info 回传成功）；**17:15** mac-mini agent-bus 考古。
- **08-21 15:21**：CLD Windows 版封装会话；**16:56** 更新 dsh；**17:22~19:02**：法拍情报系统建成（data/fapai-intel 全套 + dev/web profile 重装 node_modules，17:39）。
- **08-22 03:42**：景鸿国际项目工作区 + 深度调研会话（向量库）；**15:21** i9 电脑 CLD 故障排查；**17:17** doctor-singleton 日志（单例守护检查）；**19:55** 安装 Rust 环境。
- **08-23 01:34~02:00**：法拍信号源雷达 App 六轮代码审计（Node.js/前端/Electron/数据质量）；02:58 settings.yaml 更新。
- **08-25 20:20**：市场 index.json 重扫 2263 条目；**23:58** node-bridge 日志开写（v1.0.7 运行）。
- **08-26 02:53**：devices/outbox 上线测试；**03:09~03:23**：MBP 节点侧总线角色会话 + blackboard-events/mbp-bus-client 双守护 pid；**03:20** 市场重扫；**03:27~03:30**：从黑板拉取 i9 考古资产（archeology-from-i9，含方法论框架与 5 族考古成果）；**03:30~03:42**：archaeology-mbp 骨架（L1~L5 + reports）建立，全量深度考古组（Claude Code/Shell 历史/项目普查/节点自身）并行开跑（本组即其一）。

## 敏感项位置清单（不写值）

- `~/.dsh/bus-bridge-token`（65B，08-17 23:34）— 总线桥认证令牌，仅记存在。
- `~/.dsh/.credentials.yaml`（54B，08-15）— 凭据文件，仅记存在。
- `~/.dsh/settings.yaml`（154B，08-23 02:58）— 设置含密钥引用，仅记存在。
- `~/.dsh/market/tokens.json`（2B，08-15 15:56）— 市场授权令牌位，仅记存在。
- `~/.dsh/.anonymous-user-id`（37B）— 匿名身份。
- 注意：inbox 中跨节点消息可能携带凭据类内容，本考古未展开读取。
