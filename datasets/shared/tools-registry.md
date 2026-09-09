# 跨设备工具链 · 全量版本台账（tools-registry）

> 维护者：mac-mini 中枢（session-fa1f9150）｜ 更新：2026-08-27
> 目的：所有工具的版本、状态、分发、三端部署情况的**唯一事实源**（Single Source of Truth）
> 规则：新增/升级工具必须在此登记；版本台账同时落黑板 data/mac-mini/registry/tools

## 一、Rust 工具链

| 工具 | 最新版本 | 平台产物 | 源码 | 说明 | 状态 |
|------|---------|---------|------|------|------|
| dsh-tools | v1.17.0 | macos-arm64/win-x64（GitHub Release 双资产）| ~/dsh-collab/rust-tools（git + GitHub + tag）| 黑板固化工具集：bb-read/bb-sub/handoff/workflow/bus-bridge/tailnet-proxy/agent-msg/agent-thread/assess/**deploy-check**/**restart-guard**/**restart-gate**/**version**/**repo**/**ledger**/**health**/**channel-audit**（通道卫生巡检）/**noise**（R018 反馈链）/**load-gate**（资源总控门）/**queue-drain**/**queue-condense**（堆积浓缩）/sign（Ed25519） | ✅ 三端分发 + GitHub |
| node-bridge | v1.3.2 | macos-arm64/win-x64/linux-x64（GitHub Release 双资产）| ~/dsh-collab/rust-bridge（git + GitHub + tag）| 跨设备桥常驻：heartbeat/queue/worker/notes/outbox + LLM 执行器 v2 + identity（P1-3b）+ token 请求头（P1-1c）| ✅ mac-mini 运行 v1.3.2（08-29 修复 header 空行 bug）· i9 v1.3.0（待升）· MBP v1.1.1（待升） |
| blackboard-mcp | v0.7.0 | macos-arm64（GitHub Release）| ~/dsh-collab/rust-blackboard-mcp（git + tag v0.4.0-v0.7.0）| MCP 开放节点服务器（Rust 全栈 10 工具）：黑板 7（bb_read/write/publish/subscribe+node 3）+ 特征库 2（feature_search/stats）+ 消息治理 1（queue_condense）；SSE 8810 常驻 | ✅ mac 运行（Python feature-mcp 已退役） |
| rust-blackboard | v0.6.4 | macos-arm64 | ~/dsh-collab/rust-blackboard（git + GitHub + tag）| 黑板 8792 + SSE 8803 | ✅ mac-mini 运行（08-28 SSE 广播修复 + audit 保留 + register API）|

### dsh-tools 版本历史

| 版本 | 日期 | 新增 | 状态 |
|------|------|------|------|
| v1.0.0 | 08-25 | bb-read/bb-sub/handoff 初版 | 已分发（i9/MBP） |
| v1.2.0 | 08-26 | workflow/bus-bridge/tailnet-proxy | 已分发 |
| v1.3.0 | 08-27 | agent-msg/agent-thread（跨设备 agent_send） | 已分发 |
| v1.3.1 | 08-27 | assess 评估器 + agent-msg 门禁 | 已分发 |
| v1.4.0 | 08-27 | **deploy-check**（部署安全审查：依赖链/API漂移/版本漂移） | 已分发 |
| v1.4.1 | 08-27 | deploy-check 四段审查（link语法/bundles顺序/补丁/JS语法） | 已分发 |
| v1.4.2 | 08-27 | 版本比较修复（宿主≥期望，rc 感知） | ✅ 最新 |
| v1.12.0 | 08-29 | deploy-check restart_guard + restart_gate（R011 v3 三级门） | ✅ 已分发 |
| v1.13.0 | 08-30 | **health** 子命令（吸收 i9 dsh-plugin-health-check v0.1.0：health-check/upgrade-status/pitfall query/add，Rust 化+mac 适配+动态插件扫描） | ✅ 已分发 |
| v1.13.1 | 08-30 | restart-gate 新增 **--post-health** 阶段（升级后自动 health-check 确认，R011 联动） | ✅ 最新 |

### node-bridge 版本历史

| 版本 | 日期 | 新增 | 状态 |
|------|------|------|------|
| v1.1.1 | 08-25 | 五线程初版 | MBP 运行中 |
| v1.2.0 | 08-26 | LLM 执行器 v2（三因子门禁：flash/日配额/互斥锁/退避重试/dead-letter/台账） | ✅ mac-mini/i9 运行 |
| v1.3.0 | 08-28 | --identity 设备身份 + POST /register | ✅ i9 运行中 |
| v1.3.1 | 08-28 | --token 生效（X-Blackboard-Token 头） | ⚠️ 有 header 空行 bug（写入 value 空），已被 v1.3.2 取代 |
| v1.3.2 | 08-29 | **修复 token 请求头空行 bug**（带 token + 空 token 双向验证）+ 启动日志显示实际 bb 地址 | ✅ mac-mini 运行中（心跳 value 完整）；i9/MBP 待升 |

## 二、DSH 插件

| 插件 | 版本 | 源码 | 依赖 | 三端状态 |
|------|------|------|------|---------|
| **dsh-plugin-agent-way** 🏆（原名 agent-bus） | **1.3.0**（GitHub Release 含完整包）| ~/dsh-plugin-agent-bus（git tag v1.0.0~v1.3.0 已全部推 GitHub） | peer: 11 个补全（cordis/dsh-tools/dsh-client-runtime/dsh-agent/dsh-session-persistence/dsh-settings/dsh-system-prompt/dsh-host-webserver/dsh-agent-default-model/dsh-agent-presets/dsh-client-locale） | **dsh 首个原生插件** · 跨智能体高速公路 · HubBridge 跨设备桥品牌 · **mac ✅（link 源）/ MBP ✅（git+ #v1.3.0 实测加载，2026-08-28 修复 duplicate 冲突）/ i9 待确认（CLD 固定组合）** · 安装路径：git URL 锁 ref `git+...#v1.3.0`（npm 官方阻塞替代，见 docs/m1-git-url-install-path） |
| dsh-plugin-central-inbox | 0.1.4 | ~/dsh-plugin-central-inbox（git + GitHub + Release 完整包）| agentBus 服务 | mac-mini ✅ / MBP ✅ / i9 待装（v0.1.2 CENTRAL_AGENT 显式优先，注入关键）|
| dsh-plugin-flower-cockpit | 0.1.0 | ~/dsh-plugin-flower-cockpit | ws.register | mac-mini ✅（ws.register 修复版） |
| **dsh-plugin-openchronicle** 🆕 | **0.1.3** | ~/dsh-plugin-openchronicle（git + GitHub + tag）| Swift mac-ax-helper + peerDeps 补全 | **感知记忆层** · OpenChronicle 吸收 X3 · 7 工具（oc_capture/context/search/memories/snapshot/timeline/share）· mac ✅ 加载验证通过 |

### central-inbox 关键修复记录

| 版本 | 修复 | 说明 |
|------|------|------|
| 泛化版 02:54 | 配置化 DSH_NODE_ID/CENTRAL_AGENT/CENTRAL_INBOX_SSE | 多节点复用 |
| 03:16 | **删 definePlugin 悬空 import**（cordis 4.x 移除，靠 tree-shaking 才没崩） | 约定式 export name/inject/apply |
| v1.0.1+ | 同步进完整底座交付包 | MBP/i9 已收到修复版 |
| 08-28 | **自注入防护**（`value.from===NODE_ID` 跳过，防自回声循环）| MBP 自主修复，根治 llm-reply 无限回声 |
| 08-28 | **探针噪音过滤**（跳过 verify-*/verify-recovery/sse-probe）| mac-mini 源码已加，防注入刷屏 |
| 08-28 | **黑板 SSE 广播修复**（do_put 补 `sse::broadcast`）| rust-blackboard 根因，跨设备注入全链路打通 |

## 三、交付包（genebank /shared/）

| 包 | 版本 | 大小 | 内容 | 状态 |
|----|------|------|------|------|
| agentbus-full-bundle | v1.0.0 | 440K | 插件本体+依赖快照+脚本 | ❌ 有 definePlugin bug（已被 v1.0.3 取代） |
| agentbus-full-bundle | v1.0.1 | 1.3M | +deploy-check v1.4.0 | 中间版 |
| agentbus-full-bundle | v1.0.2 | 1.4M | +deploy-check v1.4.1 | 中间版 |
| agentbus-full-bundle | **v1.0.4** | 1.4M | +自适配+verify-watch+复盘+台账+日志规范 | ✅ **当前推荐** |
| dsh-tools-share | v1.4.3 | 976K | 三平台 + 源码 + CHANGELOG | ✅ **当前推荐** |
| mbp-bridge-upgrade | v1.2.0 | 376K | MBP node-bridge 升级（v1.1.1→v1.2.0 LLM 门禁） | ✅ 已备 |

> v1.0.4 含：自适配脚本（check-deps --auto-adapt + install-deps 保留宿主更新版本）、verify-watch 守护、复盘文档、tools-registry、logging-sop
> 版本管理审计（2026-08-27）：19 个自有插件全部补全 git 初始化 + CHANGELOG + README（此前仅 dsh-plugin-agent-way 完整）
> 注：github 安装的插件（dsh-plugin-gate / dsh-plugin-external-link-policy）为远程仓库形态，版本管理在远端
> 文档：agent-bus-principles.md（完整原理）+ agent-bus-official-doc-references.md（官方文档关联清单）（agent-bus 完整原理：架构/机制/19工具/跨设备扩展/部署/教训）
> 归档：2026-08-27 已将 v1.0.0~v1.0.3、dsh-tools v1.0.0~v1.4.1、i9-* 旧包移入 datasets/archive/2026-08-27/（/shared/ 仅保留当前推荐 + 业务文件）

## 四、脚本（~/dsh-collab/scripts/）

| 脚本 | 用途 | 运行方式 |
|------|------|---------|
| agent-send-gate.py | agent_send v2.3 事后扫描（业务对话豁免优化：只记纯汇报类长文；108265→34 条） | launchd 5min |
| bb-send-check.py | 发送前校验（pass/warn） | 手动/门禁 |
| central-wake.py | 中枢感知兜底（检测 inbox 新消息→写触发标记） | launchd 60s |
| **verify-watch.py** | **跨设备重启验证守护 v3.2（ack confirm 校验 + 离线恢复检测 + 探针停发不写黑板防注入刷屏；演进 v1每60s误触发→v2心跳间隔→v3探针→v3.1静默→v3.2探针停发）** | **launchd 5min** |
| **ensure-hub-symlinks.sh** | **web profile 符号链接守护 v2（校验/重建既有符号链接 + peerDeps 白名单防双实例 + pnpm 配置校验；幂等；三端可配环境变量）** | 手动/安装后必跑 |
| bb-read.py / bb-sub-daemon.py | 黑板读取/订阅（Python 参考版，Rust 已替代） | 参考 |
| **install-playbooks/** | **设备自主安装提示词库 v1.0.0**（node-bridge 升级 / central-inbox 过滤 / openchronicle 安装 / **windows-node-standard-deploy** 泛化模板）· genebank artifacts + GitHub coreyleung-art/dsh-collab-install-playbooks | 复制粘贴给设备智能体 |
| **规则账本 rules-registry** | **v1.0.0**（8 条规则 R001-R008 + rules-cli.py 治理 CLI + RULES.md 规则本 + GitHub）· 全设备服从 · 新规则提交流程：提交→审核→裁决→吸收→同步 | 中枢维护 |
| **老登能力注册表** | **34 项能力插件化**（console/plugins/capabilities.json，26 可用+8 落锁）· 订单原语10/商品批量4/查询4/经营4/报表8/知识2/监控1/基础1 · 黑板 data/ops/capabilities-inventory-v1 | aa528267 维护 |
| task-handoff.py | 任务移交（Python 参考版，Rust 已替代） | 参考 |

| **CLD 壳**（治理仓库）| **v0.3.1**（启动可见性增强，部署中；v0.3.0 热重载；v0.2.0 合并；v0.1.1 MBP 主干；v0.1.0 初版）| ~/dsh-collab/cld/（git 治理仓库 + GitHub coreyleung-art/dsh-collab-cld + genebank）| Electron 壳包装 dsh web（手搓 app）：spawnDsh(ELECTRON_RUN_AS_NODE)/exit-trace/watchdog/SIGTERM/模式选择/单实例锁/collectTrustedHosts | ✅ v0.2.0/v0.3.0 已部署，v0.3.1 部署中 · MBP 源码已回流（R016）|

## 五、三端部署矩阵

| 能力 | mac-mini（中枢） | MBP | i9 |
|------|-----------------|-----|-----|
| node-bridge | ✅ v1.3.2（08-29 header 修复） | ✅ v1.1.1（待升 v1.3.2） | ✅ v1.3.0（待升 v1.3.2） |
| central-inbox 注入 | ✅ 运行中 | 已装待重启 | 已装待重启 |
| agent-bus 完整版 | ✅ 运行中 | 已装待重启（v1.0.0 物理复制） | 已装待重启 |
| 心跳 | ✅ | ✅ | ✅ |
| deploy-check | ✅ v1.4.2 | 需更新 | 需更新 |
| verify-watch 守护 | ✅（本机） | — | — |

## 五-b、i9 插件/工具/工作流登记（2026-08-29 04:11 吸收自 i9-plugin-tool-registry）

> 来源：notes/mac-mini/i9-plugin-tool-registry（i9 回传，登记表 E:\dsh-collab\registry\plugin-tool-workflow-registry.json）
> 状态：已吸收待 R006 对齐（i9 请求 9 项达标细则后逐项评估）

| 类别 | 项 | 说明 |
|------|-----|------|
| 插件 4 | dsh-plugin-agent-way v1.3.0 | agentBus 总线+互斥+登记 |
| | dsh-plugin-central-inbox v0.1.1 | SSE 注入桥 |
| | **dsh-plugin-health-check v0.1.0**（新增） | 健康检查+踩坑档案：plugin_health/pitfall_query/pitfall_add/ops_upgrade_status |
| | dsh-workbench-plugin v0.1.27 | 官方 |
| 工具 20（活跃）| executor/heartbeat/event-bridge/8h-cycle/daily-selfcheck/link-gate(+daemon)/read-inbox/bb-proxy/calibration-review-prod/audit-question-bank/ingest-store-photos/i9-style-miner/train-l1+l2/build-l2-dataset/train-log/i9-memory-vectorize/upgrade-dsh-sandbox/upgrade-runner/check-plugin-health | 训练/升级/入库/审查闭环 |
| 工作流 5 | DSH 升级链路（沙箱→runner→健康检查）/校准真值闭环/训练证据链/实拍图入库/落链门禁 | 已插件化工具串联 |
| 踩坑档案 | pitfalls.json 31 条结构化（id/级别/日期/迭代/正文头）+ pitfall-archive.py + dsh 工具 pitfall_query/pitfall_add | 登记自动追加 markdown 真源 |

## 六、版本管理规则（固化）

1. **升级流程**：改源码 → 版本号 bump → CHANGELOG 记录 → 三平台编译 → genebank 部署 → 本台账更新 → 黑板通知
2. **自适配**：check-deps.sh --auto-adapt 检测宿主版本，install-deps.sh 按 adapted-deps.env 保留宿主更新版本（跟随 dsh rc 迭代，不降级宿主）
3. **部署门禁**：deploy-check exit=0 才允许部署（发包自检→收包二次自检→通过才上生产）
4. **审计**：llm-ledger.jsonl（node-bridge LLM 调用台账）+ agentsend-violations.jsonl（agent_send 违规记录）
