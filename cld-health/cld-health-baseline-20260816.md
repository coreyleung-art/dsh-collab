# CLD 健康基线报告 · 2026-08-16（深夜，重启后）

> 审查会话：session-9910d4b2（CLD 健康审查与迭代管理）
> 生成时间：2026-08-16 ~00:00（CST，CLD 于 23:49:40 重启后）
> 触发：23:48-49 宿主闪退自检 + 用户指派健康审查职责

## 1. 总体健康度

**🟢 基本健康**：宿主已恢复运行，核心服务/插件树/会话数据均正常；存在 1 个 P1 异常（告警链路停摆）与若干隐患/观察项，见 §5。

## 2. 宿主状态（当前）

| 项 | 值 | 判定 |
|----|----|------|
| 磁盘 | 460Gi 总量 / 12Gi 已用（20%） | 🟢 |
| 负载 | load 7.94 / 9.26 / 8.42（1 用户） | 🟡 偏高（多 Chrome 实例+LM Studio+Dify） |
| 主机 uptime | 18h06m | 🟢 |
| GUI | http://127.0.0.1:50120 → HTTP 200 | 🟢 |
| 远程入口 | 0.0.0.0:3081 → node PID 84120 LISTEN | 🟢（当前实例正常占用） |
| launchd | com.cld.server.plist 存在，KeepAlive=true（沙箱内 launchctl list 查询受限，进程存活已由端口/HTTP 佐证） | 🟢 |

## 3. 崩溃事件复盘（2026-08-16 23:48-49）

### 3.1 崩溃根因（✅ 已查明，2026-08-17 00:04）

本次「闪退」**不是自发崩溃，而是被强杀**：

- **执行者**：session-28ca132e（远程访问/inject-proxy 修复会话，其续任为 session-43b1a2d3）
- **动作序列**（workflow-capture sequence-log + 28ca132e 会话日志 tool/call 双重印证）：
  - 23:46:21 / 23:47:16 / 23:47:52 / 23:48:37 四次 `pkill -9 -f "dsh/lib/bin.js"`（+ pkill inject-proxy）
  - 23:48:37 `kill -9 82272`（运行中的 CLD/dsh 实例）→ **SIGKILL 强杀，无 .ips 崩溃报告 ✓**
  - 23:47:52 / 23:48:37 两次 `write` 重写 ~/.dsh/profiles/web/package.json（裁剪为 5 bundles；第二次引入 3 处 `coreuleung` 拼写错误）→ 重启后插件挂载大面积失效
  - 23:49:31 `launchctl bootout` com.cld.server（试图阻止 KeepAlive 复活）
- **结果**：launchd KeepAlive 于 23:49:40 仍拉起新实例（GUI 50120），加载被裁剪的 5-bundle profile → 「大量插件工具暂时不可用」；package.json 于 23:54 由 **session-fa1f9150（协调者）**恢复为 18 bundles，并实测包本体全部可加载、dsh-doc/xberg 绑定在位、repo-pipeline 依赖已补链。
- **⚠ 运行时/磁盘差异（协调者确认，关键）**：**当前运行实例仍为 5-bundle 运行态**（23:49:40 启动时加载的是被裁剪清单）；磁盘上已恢复的 18 bundles **对下次重启生效**——这解释了当前 MCP 工具（obsidian/chroma 等）未挂载。重启后应复核插件全量挂载。
- **关联**：该会话同时在做 inject-proxy 替换（/tmp/inject-proxy.mjs + mobile.css + tailnet trusted hosts），当前 3081 的监听者（node PID 84120）即其新 proxy——属 43b1a2d3 的进行中工作；协调者已清理旧孤儿进程 82499。
- **护栏**：协调者背书 CLD-008（高危操作需维护窗口协调 + agent_light），并将就此次未协调的 SIGKILL+改写与 43b1a2d3 核实问责。
- **候选加剧因素（b241741f 排障 SOP）**：崩溃窗口期曾观测**内存空闲仅 0.1GB**（24GB 机器瞬时快照；SIGKILL 为已确认主因，内存压力可能为加剧因素）→ 已登记 CLD-011，health-check.sh 已加内存监控（memory_pressure <10% 判红）。
- **排障教训（SOP v2 定论，b241741f 广播）**：同一事故两环节——①闪退直接机制=28ca132e 4× pkill -9（SIGKILL，无 .ips，workflow-capture 序列日志已证）；②boot 失败=package.json 被裁剪（5-bundle）+ 拼写错误（缺 repo-pipeline plugin、coreuleung）→ ERR_MODULE_NOT_FOUND。**排障优先 SIGTERM**（SIGKILL 绕开优雅停机，与 b278baab 丢尾部同源）。

### 3.2 原始时间线（崩溃前）

- 崩溃前实例：最后一次启动 07:36:34Z（15:36 CST），GUI 端口 63866，运行约 8h13m。
- 23:38:22 起 waimai 订单告警停摆（见 CLD-001）；23:39 market/index.json 重写；23:41-23:47 两会话活跃；23:47 pet.json/settings.yaml 写入；23:49:31 崩溃前最后会话事件；23:49:40 重启。

## 4. 组件健康

| 组件 | 状态 | 证据 |
|------|------|------|
| dsh-web.log | 🟢 重启后（line 779+）零 Error | grep 无命中 |
| 插件树 | 🟢 本次启动无加载失败 | 日志无 plugin tree 错误 |
| profile package.json | 🟢 18 bundles、路径正确（coreyleung） | 23:54 重写后状态 |
| link 依赖 | 🟢 9/9 存在 | dsh-plugin-* 及 dsh-plugin-workflow/market 全部 OK |
| node_modules | 🟢 367 项；xberg-node.darwin-arm64.node 存在 | 15:36 曾缺绑定，现已存在 |
| 配置 | 🟢 settings.yaml / pet.json 可解析、内容一致 | 读取正常 |
| 会话库 | 🟢 doctor：30 会话 healthy（23:49 boot） | boot 日志 |
| Agent Bus | 🟢 7 在线会话、14 线程、16 profile | agent_peers |
| waimai 面板 | 🟡 10 店登录态正常，但告警流停摆 | waimai_state / waimai_alerts |

## 5. 已知问题与观察项（对应 backlog）

| ID | 优先级 | 摘要 |
|----|--------|------|
| CLD-001 | ~~P1~~ | ✅ 误报关闭：告警链路健康（PID 82652、lastTick 新鲜），静默=无新订单 |
| CLD-002 | P1 | 崩溃无留痕（本次为 28ca132e pkill -9 强杀，SIGKILL 无报告）；缺看门狗 |
| CLD-003 | ~~P2~~ | ✅ 已解决：根因=28ca132e 两次 write 裁剪+coreuleung 拼写；23:54 已修复 |
| CLD-004 | P2 | xberg 原生绑定 npm optional-deps 脆弱性（重装 node_modules 可能复发） |
| CLD-005 | P3 | 宿主负载偏高（load 8-17，00:03 瞬时 17.56 后回落） |
| CLD-006 | ~~P3~~ | ✅ 已解释并关闭：3081 冲突源于 28ca132e 手术；当前新 proxy 正常 |
| CLD-007 | ~~P2~~ | ✅ 完成：health-check.sh 交付并验证全绿 |
| CLD-008 | P2 | 运维高危操作护栏（pkill/kill/bootout/写 profile 需授权+备份） |

## 6. 基线快照（供后续对比）

- GUI 端口：50120（本次重启后）
- 3081 监听 PID：84120（新 inject-proxy，28ca132e/43b1a2d3 手术产物）
- package.json bundles 数：18；node_modules 项：367
- 在线会话数：7；profile 登记数：16
- 最后告警事件：23:38:22（已核实为正常静默，CLD-001 误报关闭；事件流持续写入）
- health-check.sh：首次运行 ✅ 健康（2026-08-17 00:05）

## 7. 受控重启复核（2026-08-17 00:33 执行，00:47 复核）

> 协调者 fa1f9150 组织、用户 00:33 执行受控重启；本会话（9910d4b2）按 post-restart-check.md 复核。

| 步骤 | 结果 |
|------|------|
| 新 boot 行 | 00:30:14 / 00:33:01 / 00:38:47（三次，当前 00:38:47） |
| GUI | **62902** HTTP 200（端口由 50120 变更，health-check 已改自动探测） |
| 启动后错误 | 0 |
| 运行态 bundles | 18（磁盘 18，无 coreuleung） |
| 插件树 | 无加载失败；协调者实测 agent_* 10 工具 / repo_pipeline / dshdoc / modlens 注册 |
| 常驻总线 | 接管；17 能力档案加载（agent_peers 可用） |
| 3081 | node PID 84120 监听正常（inject-proxy 存活） |
| 负载 | **2.57-2.94（大幅回落，此前 ~9-13）**——重启后显著改善 |
| 配置突变 | package.json 00:25 恢复修复 = **fa1f9150 协调操作**（补回 dsh-plugin-repo-pipeline；`.bak-repopipeline` 留证损坏版：18 bundles 但缺 repo-pipeline → ERR_MODULE_NOT_FOUND） |
| ⚠ 面板 8787 | **假阴性已撤销**（协调者 01:00 裁决）：curl 000 系 bash 沙箱网络隔离；面板实为存活（waimai_state 10 店 / node 98866 LISTEN）。MTM_DATA_DIR 修复保留为有效改进 |
| ⚠ waimai_* 工具 | **本会话不可用**（wmmon 动态插件未随重启重建）——已通知 aa528267 重建 |
| 已知缺口 | /agent-bus HTTP 路由未注册（协调者已按响应式模式修复 resident，下次重启含 dashboard 大屏） |

**结论**：CLD 本体重启后健康（18 插件全量挂载、零错误、负载下降）；外卖侧两项（面板 8787 / waimai 动态工具）待其所属会话恢复，跟踪见 backlog（登记为新项）。

## 8. 外卖侧数据快照（2026-08-17 01:00，de7b29de 现地实测提供）

- 事件流：2829 条持续写入（order_change 1881 / customer_msg 570 / sound_alert 188 / new_order 178）
- 告警：80 条（new_order 为主；P0-1 去重后不再重复刷）
- IM 统筹：112 会话 / 73 待回复 / 39 已回复
- 迭代后能力：`mtm cleanup --days N` 可用；分析页含客户消息维度
- 面板判定标准：lsof 8787 监听（node 子进程）+ waimai_state 宿主工具，不依赖 Electron 壳 PID

## 9. CLD 堆 OOM 崩溃归因（2026-09-02 补充）

**事件**：09-01 14:55 与 09-02 00:44 两次 CLD 崩溃。
**证据链**：
- dsh-web.log 2× `FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript heap out of memory`（V8 堆耗尽）
- CLD-2026-09-01-145531.ips：Node/V8 heap OOM，多 WorkerThread（node::worker::Worker::Run 帧）
- CLD-2026-09-02-004439.ips：EXC_CRASH/SIGABRT（二次）
**环境关联**：swap 92% 高位持续 + 内存压力（多会话/Worker 线程活跃）——OOM 与内存压力高度相关。
**时间线**：09-01 boot 06:45→09:26→16:44（14:55 崩溃后重启）；当前 GUI 56711。
**处置建议**：内存缓解（purge/会话压减/Worker 并发限制）、V8 heap/Worker 数评估、CLD-002 看门狗安装后留痕（待装）、归因跟踪见 CLD-020。
