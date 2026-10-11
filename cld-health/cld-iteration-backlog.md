# CLD 迭代需求清单（Backlog）

> 管理者：session-9910d4b2（CLD 健康审查与迭代管理）
> 状态机：new → planned → assigned → in-progress → done / won't / blocked
> 优先级：P0=阻断 · P1=高 · P2=中 · P3=低/观察

## 需求列表

### CLD-001 · 外卖订单告警链路停摆 —— ✅ 误报关闭
- **类型**：缺陷　**优先级**：P1　**状态**：closed（误报，2026-08-17 00:09）
- **结论**：**告警链路健康，静默=无新订单**（de7b29de 实测）：面板进程 PID 82652 存活、8787 正常；watcher 10 店 lastTick 1-5 秒前、running 全 Y；事件流持续写入（order_change/customer_msg 实时）。CLD 重启后采集正常恢复。
- **误报原因**：我此前以「告警时间戳停滞」判定停摆，但 15:38:22 后无 new_order → 不产生新告警是正确行为；15:31-15:38 的每 ~2 分钟重复为已知判定局限（store 2 两单交替，count=0 时靠订单卡片数波动判定新单，SPA 刷新触发重复）。
- **经验教训**：健康判定应检查「事件流/采集 lastTick 新鲜度」，而非「告警时间戳」——已作为 CLD-009 增强项登记。

### CLD-009 · 告警健康判定与去重增强
- **类型**：增强　**优先级**：P3　**状态**：in-progress（部分落地，2026-08-17 00:10）
- **描述**：① 健康监控区分「事件流停摆」与「无新事件」（检查 watcher lastTick 新鲜度，而非告警时间）；② new_order 告警加同订单号去重（从 detail.firstItem 提取订单编号，15 分钟窗口内同单不重复告警），消除 SPA 卡片数波动误触发。
- **进展**：① 已落地——health-check.sh v2 新增第 10 项「面板 8787 采集新鲜度」（curl /api/state，解析各店 lastTick，>300s 或不可达判红），实测 stores=10 stale=0 worst age=2s ✅；② 去重部分待 de7b29de 排期。
- **进展②（2026-08-17，de7b29de 数据实证补丁）**：customer_msg 事件只在客户消息内容变化时触发（lastClient 比对 + 8s 节流），深夜无新消息事件静默=**正常行为**；采集活性以「lastTick 实时 + im_sessions updated_at 刷新」为准，customer_msg 事件最新时间仅反映「最后一次新客户消息」、禁止作断流指标——已并入 agent-bus-roster.md 健康判定铁律。
- **建议负责人**：session-de7b29de（② 去重）、本会话（① 已落地）
- **验收标准**：健康判定基于 lastTick；同一订单 15 分钟内不重复告警。

### CLD-002 · 崩溃留痕/看门狗缺失
- **类型**：增强　**优先级**：P1　**状态**：in-progress（实现完成+测试通过，**安装待用户确认**，2026-08-17 04:4x）
- **实现（3d490920）**：main.js exit-trace 模块——exit-marker.json 原子写（启动 marker/干净退出写退出码信号时间原因）；heartbeat.json 每 30s；dsh-web.log [exit-trace] 上次运行 DID NOT EXIT CLEANLY（SIGKILL/崩溃，含 pid/start/heartbeat）；uncaughtException 捕获；顺带修复 readFileSync 未导入 bug（readModeCfg 此前恒空）。
- **验证**：四场景测试通过（首次启动/SIGKILL 检测/干净退出/崩溃原因）；asar Electron 读取器校验完整。
- **工件（v2，04:45）**：~/CLD/app-cld002.asar（**91755B，sha256 001468530975ebb5b2b3be8db2f8612af7aa6b8c9c92972e09425a37a34bb5f2**，旧 d685c19d 作废）+ main.js.cld002 + CLD-002-watchdog.md。v2 新增 **SIGTERM → app.quit() 干净退出处理**（修复单实例锁吸收新实例导致重启无效，协调者要求并入）。
- **安装**：待用户执行两条命令（备份+cp 替换，沙箱无法写 /Applications）；下次启动生效。
- **验收（安装后）**：强杀后下次启动 dsh-web.log 出现 [exit-trace] PREVIOUS CLD RUN ... DID NOT EXIT CLEANLY——3d490920 回报验证结果后转 done。
- **描述**：本次 23:49「闪退」实为 **session-28ca132e 的 `pkill -9 -f "dsh/lib/bin.js"` 强杀（SIGKILL）**——无 .ips 崩溃报告与此吻合（被强杀不产生崩溃报告）。CLD 自身无被强杀/异常退出留痕机制。建议：CLD 侧增加退出码/心跳/看门狗日志，或 launchd 记录退出原因，使未来任何退出（含外部 kill）可审计。
- **建议负责人**：session-3d490920 / session-c1111ffe / session-43b1a2d3（CLD/dsh 运维排障）
- **验收标准**：下一次异常退出能在 ~/.cld/logs 留下退出原因（信号/退出码/时间）。

### CLD-003 · profile package.json 被裁剪+拼写错误 —— ✅ 根因已查明
- **类型**：缺陷　**优先级**：P2　**状态**：resolved（根因定位，2026-08-17 00:04）
- **根因**：**session-28ca132e**（远程访问/inject-proxy 修复会话，续任 43b1a2d3）于 **23:47:52 与 23:48:37 两次 write 重写 package.json**（裁剪为 5 bundles：dsh-base/dsh-web-app/dsh-plugin-local-projects/dsh-plugin-market/dsh-plugin-sandbox-policy-ui；第二次写入引入 3 处 `coreuleung` 拼写错误：dsh-plugin-research / dsh-plugin-workflow-capture / dsh-plugin-repo-pipeline）。
- **证据**：workflow-capture sequence-log.json index 1972/1974（含完整写入内容与 ts）；session-28ca132e 会话日志 tool/call（23:44-23:49 的 bash 序列一一对应）。
- **处置**：23:54 由 **session-fa1f9150（协调者）**恢复为 18 bundles/正确路径，并实测包本体全部可加载、dsh-doc/xberg 绑定在位、repo-pipeline 依赖已补链；00:25 再做恢复修复（补回 dsh-plugin-repo-pipeline，`.bak-repopipeline` 留证损坏版）。
- **遗留**：运维会话对 profile 的高危写入缺护栏（见 CLD-008）；建议 profile 配置纳入 sysops 自动备份。

### CLD-004 · xberg 原生绑定脆弱性（npm optional-deps）
- **类型**：增强　**优先级**：P2　**状态**：done（修复+验证完成，2026-08-17 04:40；重启后复测项见 post-restart-check）
- **描述**：15:36 重启循环中 dsh-doc → @xberg-io/xberg 曾因缺 darwin-arm64 原生绑定导致插件树加载失败（npm optional-deps bug, npm/cli#4828）；绑定文件现存在（health-check 验证），但重装 node_modules 可能复发。
- **根因（c1111ffe 深挖，2026-08-17 04:3x）**：① 平台包 @xberg-io/xberg-darwin-arm64 在 registry 从未发布 1.0.x 正式版（仅 0.0.1/1.0.0-rc.x），xberg@1.0.14 的 optional 依赖解析失败被静默跳过（上游发布缺陷）；② 原生绑定 .node 依赖同目录 dylib 套装（libonnxruntime.1.24.2/libheif.1/libx265.216/libde265.0/libaom.3/libsharpyuv.0/libvmaf.3），registry 均无法获得；③ health-check 此前仅查 .node 文件存在性，未覆盖 dylib 依赖（漏判）。
- **修复（c1111ffe 实施）**：① package.json 加 postinstall（scripts/ensure-xberg-binding.js）+ pnpm.overrides 锁定 @xberg-io/xberg=1.0.14；② 完整 8 文件运行时套装落盘 ~/.dsh/profile-assets/xberg/（dylib 依赖已 install_name_tool 改写为 @loader_path 自包含）；③ postinstall 自动恢复（缺失即补、幂等）。
- **验证**：rm -rf node_modules 全量重装 → postinstall 自动恢复 8 文件全 OK；dsh --profile web --dump-default-config exit 0（bundle 解析 OK）；宿主 dshdoc_health = ready / engine xberg-node / 1.0.14；GUI 51960 + 3081 HTTP 200。
- **建议负责人**：session-c1111ffe（依赖管理/pnpm 陷阱）
- **验收标准**：删除 node_modules 重装后 dsh-doc 可正常加载。（已端到端验证；新套装待下次 CLD 重启后宿主复测——已列入 post-restart-check）

### CLD-005 · 宿主负载偏高
- **类型**：增强　**优先级**：P3　**状态**：assigned（已指派 b241741f，2026-08-17 00:11，消息已送达）
- **描述**：load 9-13 波动（00:03 曾瞬时 17.56，00:11:28 冲 13.22 超阈）；进程 605 / 线程 5432。**CPU Top（00:11 采样）**：com.apple.Virtualization（Docker VM）44.4%、kernel_task 31.6%、Chrome Helper ×4（28/20.3/13.1/6.5%）、CLD Renderer 16.6%、WindowServer 14.5%——主来源=Docker VM（Dify）+ 10 Chrome 实例。
- **建议**：Chrome 实例休眠、Dify 容器资源上限、非高峰关停 LM Studio、Spotlight 索引限制。
- **建议负责人**：session-b241741f（系统健康巡检 / com.sysops.health）
- **验收标准**：常态负载降至 ~<6（参考值）。

### CLD-006 · 上一实例 3081 僵尸进程 —— ✅ 已解释
- **类型**：观察　**优先级**：P3　**状态**：closed（2026-08-17 00:04）
- **结论**：3081 端口冲突/残留进程源于 28ca132e 的 pkill/bootout 手术（旧实例被杀后端口未即时释放）。当前 3081 由新 inject-proxy 正常监听（node PID 84120），无冲突。若复发按 c1111ffe 端口排查流程处理。

### CLD-007 · 健康巡检自动化 —— ✅ 完成
- **类型**：增强　**优先级**：P2　**状态**：done（2026-08-17 00:05）
- **交付**：`~/dsh-collab/cld-health/health-check.sh` v4（磁盘/负载/GUI/3081/日志错误/bundles 拼写/node_modules/xberg/link 依赖/**面板 8787 lastTick 新鲜度**/**配置运行期改写检测** 十一项检查 + **`--log` 趋势记录**到 health-log.tsv；exit 0=全绿）。多次运行验证：✅ 健康；00:11:28 正确捕获负载超阈（13.22>12，判 FAIL）；00:13 正确识别 package.json 启动后改写（协调修复，信息级）——阈值与突变检测均有效。
- **调度集成（待评估）**：现有 launchd 已有 com.sysops.health（30min，系统服务层）、com.dsh.health（60min）、com.sysops.waimai.watchdog（60s）；本脚本为 CLD/profile 专项，与 sysops 互补。**已与 b241741f 达成共识（2026-08-17 00:54）**：设计为 sysops health 扩展检查项或独立子命令 `sysops health --cld`，接口用本脚本 `--json` 输出 + exit code 契约；排期随维护窗口。**不重复建 launchd**。

### CLD-008 · 运维高危操作护栏（流程需求）
- **类型**：增强　**优先级**：P2　**状态**：planned（协调者背书 + 维护窗口计划已对齐，2026-08-17 00:14；执行待用户拍板窗口）
- **描述**：28ca132e 的注入式手术（pkill -9 杀 dsh web、launchctl bootout 服务、重写 profile package.json）无任何护栏，直接导致本次「闪退」与插件大面积失效。建议：① 对 CLD/dsh 进程与 profile 的高危操作（pkill/kill/bootout/写 package.json）走 Agent Bus 红绿灯（agent_light/lock）+ 维护窗口协调；② 修改 profile 前先备份（cp package.json package.json.bak-$(date)）。
- **进展**：协调者 fa1f9150 完全认同并背书；将就此次未协调的 SIGKILL+改写与 session-43b1a2d3 核实问责。**维护窗口**：协调重启提议已获认可——磁盘配置稳定、post-restart-check 清单合并对齐（18 bundles/MCP 恢复/常驻总线 10 工具+大屏+guard/16 档案/3081/插件树/waimai）、43b1a2d3 的 inject-proxy 由 launchd 自恢复、CLD 重签可并入（待用户确认）。**待用户拍板窗口**；重启前协调者广播「即将重启」；重启后本会话执行 10 步复核。
- **建议负责人**：本会话（流程登记）+ 全体运维会话（执行约定）
- **护栏实现标注（2026-09-07 R006 轮2 核查）**：高危操作护栏已有工具支撑 = Agent Bus 红绿灯（`agent_light`/`agent_lock`，baseline §37 协调者背书）+ 宿主 guard 工具族（`guard_check_writable` P1 / `guard_backup` P2 / `guard_compliance` Lean4 五道闸）；建议 profile 自动备份由 `guard_backup` 承接。流程需求仍生效（执行须走维护窗口协调）。

### CLD-010 · 重启后外卖侧恢复（面板 8787 + waimai 动态工具） —— ✅ 已解决（面板子项撤销为假阴性）
- **类型**：缺陷　**优先级**：P1　**状态**：closed（2026-08-17 00:56；01:00 更正）
- **结论**：① **面板 8787「宕机」= 假阴性**（协调者裁决 2026-08-17 01:00）：curl 000 系 **bash 沙箱网络隔离**所致，面板实为存活（waimai_state 宿主工具 10 店正常、de7b29de 现地复核 node 98866 LISTEN）；`MTM_DATA_DIR` 数据目录修复保留为**有效改进记录**（目录错位是真实改进点）。② **waimai 工具**：宿主侧挂载，面板宕机期瞬时不可用非残留。
- **判定标准更新**：面板健康用 **waimai_state 等宿主 API 工具**验证，**不用 curl/PID**（health-check.sh 面板项已改信息级，不再判红）。
- **教训（已写入 post-restart-check.md）**：受控重启后手动拉起面板必须 `export MTM_DATA_DIR=.../外卖门店多平台管理/data`；wmmon 需 kind:new 重建。
- **复测确认（01:08）**：waimai_state 本会话可用（10 店 logged_in/41 告警）；de7b29de 确认工具为**宿主侧挂载**（本会话 Cordis 插件列表空但工具可用）——此前 unknown tool 为面板宕机期瞬时问题，非残留。8787 时点差异=de7b29de 迭代窗口打包重启所致，当前正常。
- **PID 口径澄清（de7b29de 00:58 现地复核）**：8787 监听者=**node 子进程 PID 98866**（外卖门店多平台管理.app 的 Electron 壳 PID 843/此前 82652，server 逻辑在 node 侧）——PID 会随重启变化，**健康判定标准 = `lsof 8787 监听存在 + curl 200`，不依赖特定 PID**（我的 health-check 面板检查已按此实现）。

### CLD-011 · 内存压力监控与评估
- **类型**：增强　**优先级**：P2　**状态**：assigned（本会话落地监控，2026-08-17 00:49；评估待 b241741f）
- **描述**：b241741f 排障 SOP 记录崩溃窗口期候选诱因——**内存空闲仅 0.1GB**（24GB 机器，瞬时快照；当前 memory_pressure 65% free）。作为候选诱因（SIGKILL 强杀为已确认主因，内存压力可能为加剧因素），登记监控与评估。
- **进展**：health-check.sh v6 新增第 12 项内存压力检测（memory_pressure，<10% 判红），实测 65% OK。
- **建议负责人**：本会话（监控已落地）、session-b241741f（评估/防二次事故）
- **验收标准**：内存低水线可监测；如复现 <10% 有告警与记录。

### CLD-015 · 外卖 Chrome 实例大面积掉线（8/10 店 running:false）
- **类型**：缺陷　**优先级**：P1　**状态**：closed（2026-08-17 05:4x，aa528267 排查+恢复，本会话核实 10/10 running）
- **根因**：唯一真故障=佛山禅城店（9204，s7 profile）Chrome 主进程不在；其余 8 店 running:false 为 watcher 探测滞后/attach 未刷新（Chrome 进程存活）。
- **处置**：nohup 拉起 s7 profile → 9204 HTTP 200；15s 后 waimai_state 10/10 running+logged_in 全恢复（本会话 05:4x 复核 running=10/10 ✓）。
- **建议**：单店 Chrome 掉线复发时，建议 com.sysops.waimai.watchdog 覆盖 Chrome 实例拉起（现只管面板 App）→ 已登记 CLD-016。
- **时点澄清（de7b29de 05:5x）**：05:36 观测=其恢复期窗口（im_send 调试后部分店 Chrome 退出+App 多次重启+看门狗 60s 冷却拉起中段），非持续故障；当前 10/10 running + 9/10 lastTick 0-3s（仅店 12 单次 tick 超时已恢复）。
- **架构加固（已上线）**：watcher.tickAll 每店 15s 超时保护（单店卡住不拖垮全监控）；完整 stop+launch 重建损坏店；窗口操作谨慎（屏幕外窗口 CDP 交互不可用实证）。
- **判定标准更新**：后续「掉线」以 **lastTick 活性**（非 running 标记）为权威判定——与 health-check 面板 stale 检测口径一致。
- **描述**：05:36 巡检 waimai_state 权威判定：仅 2 店在线（天河3号/江南西），8 店 running:false（客村/佛山禅城/天河1号/佛山禅城京东/天河守白京东/天河抖店/天河抖音觅趣守白）；面板 lastTick stale 7 店；pendingAlerts 6。04:14 曾 10 店全在线。
- **建议负责人**：session-de7b29de（watcher/采集）、session-aa528267（CDP 实例）
- **验收标准**：waimai_state 恢复 10 店 running:true；面板 stale 归零。

### CLD-016 · watchdog 覆盖 Chrome 实例拉起（CLD-015 建议）
- **类型**：增强　**优先级**：P3　**状态**：new
- **描述**：CLD-015 单店 Chrome 掉线（佛山禅城 9204）需人工拉起；com.sysops.waimai.watchdog 现只管面板 App，建议扩展覆盖 Chrome 实例（CDP 9200-9209 端口探测 + 拉起）。
- **建议负责人**：session-b241741f（sysops watchdog）、session-aa528267（Chrome 实例管理）
- **验收标准**：单店 Chrome 掉线后 watchdog 自动拉起，无需人工。

### CLD-017 · P0 上下文压缩执行（队列根因治理）
- **类型**：缺陷　**优先级**：P0　**状态**：in-progress（排期采纳：试点先行→随重启推广，2026-08-17）
- **排期（协调者定）**：① 试点 3b5efeef（10701 条）会话级压缩验证降 90%（独立执行，低风险；挂载插件走红绿灯）；② 推广=standard+compaction 继承预设随重启窗口挂载（post-restart-check 已加第 14 步 compaction 挂载验证）；③ 裁剪/唤醒合并/缓存前缀跟进。
- **背景**：4787d717 调研确认 DSH 内置压缩插件族（dsh-compaction-basic/command-compact/tool-result-pruner）未挂载到存量 standard 预设会话 → 上下文只增不减（3b5efeef 239MB 为总线排队根因）。
- **执行项**：① 试点压缩最大会话（3b5efeef 10701 条）验证降 90%；② 落地=新建「standard+compaction」继承预设（shipped standard 不可改）或会话级 /compact；③ 工具结果裁剪+唤醒消息合并+缓存前缀跟进。
- **报告**：~/dsh-collab/research/compute-optimization/bus-queue-solutions-2026W34.md（v1.0.94）。
- **建议负责人**：协调者 fa1f9150（排期）、4787d717（调研支撑）、3b5efeef（试点会话）
- **验收标准**：试点会话上下文降 90%；队列积压消除或显著缓解。
- ★ **2026-10-08 复核修正（本卡「背景」段的归因已过期，勿再据它行动）**：
  星桥 `session-fa1f9150` 今日实测 **压缩已挂载、且已实际跑过 41 次**（`compaction/start` 41 : `compaction/end` 41，严格配对，**无孤儿 start**）——`standard` 预设里 `compaction-basic` / `command-compact` / `tool-result-pruner` 三者齐全（`@deepseek-ai/dsh/config/agent-presets/standard/agent.cordis.yml`）。
  ⇒ **失效原因不是「未挂载」，而是阈值算术不可达**：`thresholdTokens = floor(contextWindow × 0.8) = floor(1,000,000 × 0.8) = 800,000`，而适配器默认留 256,000 completion ⇒ 消息侧可达上限仅 `1,048,576 − 256,000 = 792,576` ⇒ **800,000 > 792,576，压力检查永远晚于溢出**，主动压缩永不触发；只剩事后 `agent/request-error` 兜底，而它受 `retainRatio 0.16` 保护的尾部不可裁剪 ⇒ 撞 `:556` 收缩门 `summary is not smaller than the shadowed content (3420 >= 3420)`。
  ⇒ **处置方向随之改变**：不是「打开开关」，而是**下调 `thresholdRatio`**（如 0.6 ⇒ 600,000，安全低于 792,576）并同步下调 `retainRatio`；因 shipped `standard` 在签名 bundle 内不可改，须走**用户自有预设**（`~/.dsh/.agent-presets/`），与本卡 ①「新建 standard+compaction 继承预设」路线一致，但**配置内容不同**。
  · 证据：`~/.dsh/sessions/--Users-coreyleung--/session-fa1f9150-…/session.jsonl.zstd` 尾部 `turn/end` → `CONTEXT_WINDOW_EXCEEDED`「requested 1049216 tokens (793216 in the messages, 256000 in the completion)」；`@deepseek-ai/dsh-compaction-basic/lib/index.js:109/:556/:881-882`；`@deepseek-ai/dsh-llm-deepseek/lib/index.js:1735`（`maxTokens ?? 256e3`）。

### CLD-026 · 会话自检每次启动跑 `--fix`，且会**截断**文件；星桥被**误判** corrupt
- **类型**：缺陷（数据安全）　**优先级**：**P1**　**状态**：new（2026-10-08 本机实测登记；**与用户硬约束直接相关**）
- **用户约束**：「不可以清理掉任何历史会话记录」⇒ 本卡按最高敏感度对待。
- **对象**：`app.asar!/scripts/session-doctor.mjs`；触发点 `app.asar!/main.js:1040`
  `setTimeout(() => { runDoctor({ fix: true }).catch(() => {}); }, 6000)` —— **每次 CLD 启动、web ready 后 6 秒，都会带着 `--fix` 跑一次全库会话自检**（`runDoctor` 形参默认即 `fix = true`，`:913`）。
- **`--fix` 的真实行为（脚本自述 + 代码双向确认）**：
  - 自述（`:10-12`）：*"with `--fix`, repairs corrupt sessions that are QUIESCED … first lossless **salvage**, then **truncate** fallback; every write keeps a `.corrupt-<ts>` backup"*
  - 代码（`:183-194`）：先 `planSalvage` → 成功则 `writeAtomic(file, rebuilt)`；**否则 `rebuildTruncated(...)` 兜底** ⇒ **方法是「截断」**，`outcome.method === "truncate"`。
  - ⇒ 判据：**「truncate」意味着按 `committedBytes` 截掉尾部事件**（有 `.corrupt-<ts>` 备份，故非永久灭失，但**实时文件的可见历史会变短**）。静默期判定 `quiesced = force || now - st.mtimeMs > staleAfterMs` ⇒ 冷会话天然合格。
- **★ 星桥为何今天没被截断（关键，必须写准）**：它的失败发生在 `analyzeLog()` 内部，被 `:143-148` 的 `catch` 捕获：
  ```js
  } catch (e) {
    corrupt += 1;
    lines.push(`corrupt:  ${rel} (structural: ${e.message})`);   // ← 星桥走这条
    state[rel] = { size: st.size, mtimeMs: st.mtimeMs, verdict: "corrupt" };
    continue;                                                     // ← 不进入修复分支
  }
  ```
  启动自检原文：`corrupt: sessions/…/session-fa1f9150-…/session.jsonl.zstd (structural: frame at byte 244957020 failed validation: Failed to allocate memory)`；`fixed: 0`。
- **★★ 但「corrupt」是误判，文件本身完好（本机实测）**：`zstd -dc <file> > /dev/null` **退出码 0、stderr 全空、完整解出 892,080 行**。
  ⇒ 报错文本自述 `Failed to allocate memory` ⇒ **是校验器解码时 OOM，不是数据损坏**。属「测量对象 ≠ 故障对象」同族（呼应 `B0-星桥激活崩溃-根因诊断.md` §4）。
- **残余风险（三处，任一成立即触约束）**：
  1. **分类依赖内存余量**：同一文件在不同内存条件下可能落进**另一个分支**（`issue`/`scanError`/`torn tail`），那条路**会**执行 truncate 兜底。
  2. **崩溃正是产生 `torn tail` 的成因**：`dsh-web.log` 已多次记录 dsh 在写入中被 SIGABRT 杀掉 ⇒ 真实 torn tail 完全可能出现，届时 `--fix` 的 truncate 兜底即被启用。
  3. **每次启动都重扫**：state 缓存键为 `size+mtimeMs`，文件一被写就失效 ⇒ 每次启动都对这个 **255 MB** 文件 `readFileSync` 全量读入 + 逐帧解码；**这本身是启动期内存尖峰**（与 CLD-020 同族，且与「启动后不久崩溃」的时间形态相容——**但仅属待测假设，未证**）。
- **建议方向（未执行，待用户裁定）**：
  ① 自检改跑 `--fix`→`--no-fix`（只报不修），把**修复决策交还人工**——最符合「不删历史」的约束；
  ② 或给 doctor 加**体积上限**：超过阈值只标记不读入（避免 255 MB 全量读 + 解码）；
  ③ 修 `analyzeLog` 的误判（内存不足应报 `memory-pressure` 而非 `corrupt`）；
  ④ 若保留 `--fix`，截断前必须**双备份 + 明示 `dropped N`**（现已有 `.corrupt-<ts>` 单备份）。
- **验收标准**：连续 3 次 CLD 启动，日志中星桥不再出现 `corrupt` 误判；或 `--fix` 被降级为只报不修；且全库会话文件**大小与 sha256 零变化**。
- **已完成的保全（本会话）**：冷备份 `~/dsh-collab/archives/星桥-2026-10-08/session.jsonl.zstd`，**sha256 与原件逐字节一致**（`56d8cfa470d9424b58091e63618931adebbbafbc12187b249227736f2fd5c0ad`）。

### CLD-024 · dsh-tailnet-proxy 不能可靠跟随 GUI 换端口 + 三处未捕获异常自杀
- **类型**：缺陷（可用性）　**优先级**：**P1**　**状态**：**✅ 已修复并现场验收通过**（2026-10-08 14:27 重启生效 → 14:27–14:51 两次换端口均自动跟随）
- **对象**：`~/.cld/tools/dsh-tailnet-proxy.mjs`（launchd `com.dsh.remote.plist` 常驻，入口 `100.120.203.20:3081`）
- **本卡与 CLD-019 同族**：CLD-019 处置的是 `127.0.0.1:3081`（inject-proxy）的上游端口过期并已 closed；**同一病根在 tailnet 侧入口未修**，故另开本卡。CLD-019 的「长期机制=CLD 重启自动 spawn」只重建了进程，**没有解决「换端口后跟随」**。
- **根因（三处，均已在代码中定位）**：
  1. **重扫被自身节流锁死** —— `ensureTargetPort()` 用**同一个** `lastScan` 既做周期节流又做失败门禁：`if (Date.now() - lastScan < 60_000) return;`。`ECONNREFUSED` 清空 `targetPort` 后若距上次扫描不足 60s，重扫被直接跳过 ⇒ 端口最长 60s 无法跟随，且可反复重新计时。**文件头注释承诺的「每 60s 重扫一次」在代码中并无定时器**（只有注释，无实现）。
  2. **未捕获异常杀进程** —— `server.listen()` **无 `error` 监听** ⇒ 僵尸实例占着 3081 时 `EADDRINUSE` 抛栈退出；WebSocket Upgrade 管道 `proxySocket.pipe(socket).pipe(proxySocket)` **两侧均无 error 监听** ⇒ 一次 `read ECONNRESET` 同样整进程退出。launchd KeepAlive 反复重启 ⇒ **崩溃循环**。
  3. **候选选取不确定且可自环** —— `discoverGuiPort()` 「多候选取**最后**匹配」（lsof 输出顺序无语义），且**不排除代理自身端口**：无 tailnet 回退绑 `0.0.0.0:3081` 时 `127.0.0.1:3081` 也可达并同样返回 `__DSH_BOOT__` ⇒ 转发变自环。
- **实测证据（`~/.cld/logs/dsh-remote.err.log` / `.out.log`）**：err 日志 30+ 条 `[proxy] 转发失败: ECONNREFUSED（GUI 可能重启，端口待重扫）`；**2 处完整 `EADDRINUSE 100.120.203.20:3081` 栈**、**1 处完整 `read ECONNRESET` 栈**（均 `Node.js v25.9.0`，`node:events:487 throw er; // Unhandled 'error' event`）；out 日志中 `[proxy] GUI 端口 = 3081` **即自环/僵尸指向的实证**。
- **修复（已落盘，`~/.cld/tools/dsh-tailnet-proxy.mjs`，原文件备份为 `dsh-tailnet-proxy.mjs.bak-20261008-142019`）**：① 拆两个时间常数——周期重扫 **20s**（真的加定时器）+ 失败冷却 **800ms**（防抖但不阻塞恢复）；② 补 `server.on("error")` 退避重试（不再退出）、Upgrade 两端 socket error、`clientError`、上游非 101 响应（原版会永久挂起）、最后兜底 `uncaughtException`/`unhandledRejection`（只记日志不退出）；③ 按 CLD 主进程 **PID 降序**确定性选取 + 显式排除 `p === BIND_PORT` 自环；④ 扫描并发去重（`scanning`）；⑤ 发现失败时不盲目清零——仅当当前目标确实探活失败才清零（避免 lsof 抖动丢端口）。
- **验证边界（R030）**：已完成 = 代码级定位 + 修复 + `node --check` 语法通过 + **重启后实测验收**（见下）。**未完成 = 僵尸占位 3081 时的不退出重试**（验收项③，需人为构造占位，未做）。
- **★ 实测验收记录（2026-10-08 14:27–14:51，本机）**：
  - 14:27:34 `launchctl kickstart -k gui/501/com.dsh.remote` → 新实例 **PID 71130**；
  - CLD 于 14:27:42 启动，GUI 端口 **56564** → 代理日志 `[proxy] GUI 端口 = 56564（周期重扫）` → `3081` 返回 **HTTP 200**；
  - 14:50:43 对 dsh 执行 `POST 127.0.0.1:31888/reload`（端口变为 **54409**）→ **25s 内**代理日志 `[proxy] GUI 端口 = 54409（周期重扫）` → `3081` 仍 **HTTP 200**；
  - **代理实例自 14:27:34 起从未重启**（PID 71130 恒定）；`dsh-remote.err.log` 行数停在 100、mtime 停在 **13:54:32** ⇒ 修复上线后**零新增错误**、**零未捕获栈**。
  - ⇒ 验收项①②**通过**；「（周期重扫）」标签即新代码独有路径（旧代码**没有定时器**，只有注释承诺）的实证。

### CLD-025 · CLD 崩溃自动重启后窗口指向已死端口（asar 内 `awaitServerUrl` 顺序反转）
- **类型**：缺陷（功能）　**优先级**：**P1**　**状态**：**✅ 已落盘 + ✅ 已重新公证**（2026-10-08 15:03 落盘 / 15:34 staple 完成，均独立复核全过）；**🟡 野外判据待验**（需下一次 dsh 崩溃自动重启才能观察）
  · **⚠ 一条遗留卫生问题（非本次引入）**：`Contents/Resources/` 内已存在 5 个**历史 asar 备份**（`app.asar.bak-20260816` / `.bak-20260829-v1` / `.bak-v0.2.0-20260829` / `.bak-v0.3.0-20260829` / `.pre-resolveurl-165917`，8-16～9-05，共 ~464 KB）。它们位于**签名 bundle 内部**、已被封印收编（本次 `--preserve-metadata` 重签同样收录）。⇒ **现不可单独删除**（删一个就要再破封再重签一次）；建议**下次需要改壳时一并清掉**，或在下一次整包重建时从源头排除。
- **对象**：`/Applications/CLD.app/Contents/Resources/app.asar!/main.js:517-519`（实测 1131 行 / 44890 B，与既有记录一致）
- **根因**：崩溃自动重启分支里 **`awaitServerUrl()` 与 `resolveUrl = null` 顺序反转**——
  ```js
  const urlPromise = awaitServerUrl();  // 517: 注册模块级 resolveUrl
  lastResolvedUrl = null;               // 518
  resolveUrl = null;                    // 519: 把刚注册的消费者抹掉
  ```
  正确顺序在**同一文件的热重载分支**（`:579-581`）里就是对的（先重置、后 `awaitServerUrl()`）——即 10-04 的壳修复只覆盖了 `/reload` 路径，**漏了崩溃自动重启路径**。
- **后果链**：新 dsh 打印 URL → `:470 if (resolveUrl)` **为假** → 只落一行 `[url] dsh web URL 就绪但无 await 消费者(重载间隙)` → promise 到 `BOOT_TIMEOUT_MS` 超时 → `.catch(()=>{})` 静默吞掉 → `:521-524 mainWindow.loadURL(u)` **永不执行** ⇒ **窗口停留在崩溃前的死端口**（即用户所述「动态刷新 runtime 地址随机指向」）。
- **实测证据（`~/.cld/logs/dsh-web.log`）**：`自动重启` 出现 **15 次**，`重启后 dsh 就绪`（`:522` 才写）出现 **0 次**；`[url] … 无消费者` **8 次**。热重载自身经时序核验正常（2026-10-04T01:36 实测）。
- **附带缺陷**：`crashRestartCount` 仅在**首次启动**成功时清零（`:1025`），**重启成功后不清零** ⇒ 跨越整个 App 生命周期的 3 次累计崩溃即弹 `dialog` 并 `app.quit()`（`:530-535`），即便每次重启都成功。
- **修复约束（2026-10-08 复核后修正——原卡三处表述有误，逐条更正）**：
  - **① asar 确实被封存，改后必须重签**：`Contents/_CodeSignature/CodeResources` 的 `files` 段含 `Resources/app.asar`，且实测**可复现**——原始记录 `248c08b5…` == sha1(原始 asar)，换入补丁 asar 后 `codesign --verify --strict` 立刻报 `a sealed resource is missing or invalid` / `file modified: …/app.asar`。⇒ **不重签必然被 macOS 判为签名无效**（此前「可能」应写作「必然」）。
  - **② Info.plist 的 `ElectronAsarIntegrity` 是【惰性】的，不必同步更新**：原卡担心「改 asar 后 App 拒启」。实测 Electron fuses（`npx @electron/fuses read`）：`EnableEmbeddedAsarIntegrityValidation = Disabled`、`OnlyLoadAppFromAsar = Disabled`、`RunAsNode = Enabled`；且该 hash 本就不匹配当前 asar（声明 `058296e4…` vs 实际整文件 sha256 `0d0cf847…`——electron-builder 写的是 **asar 头部哈希**，与整文件哈希本就不同口径）。⇒ **该字段不参与启动校验，无需改**。
  - **③ TCC 不会因此重触发**：`codesign -d -r-` 实测 DR = `identifier "com.cld.desktop" and anchor apple generic and certificate 1[…6.2.6] and certificate leaf[…6.1.13] and certificate leaf[subject.OU] = XS7SMKFS42`——**不含内容哈希**。用**同一 Developer ID** 重签后 DR 逐字不变（本次已实测 diff 为空）⇒ CLD-021 的授权churn 来自 **adhoc** 签名（CDHash 绑定），非本路径。
- **P1 已废止（前提被证伪）**：`~/dsh-collab/cld/` 是**另一条版本线**——HEAD `main.js` 867 行 / v0.3.2 / `mac.identity: null` / 无公证流水线 / `release/` 只有 Windows 产物，而线上 `package.json` version = **0.3.0**。用它重建会**回退** 10-04 的三处壳修复。⇒ 以线上 asar 内 1131 行 `main.js` 为唯一基线。
- **P3 降级（能力被高估）**：`crashRestartCount` 仅在首次启动（`:1025`）清零 ⇒ 累计 3 次崩溃后壳会弹框并 `app.quit()`，**`/reload` 无法阻止**。P3 只能拉回窗口，治不了「3 次即退出」。
- **★ P2 执行记录（2026-10-08，两处缺陷一次改完）**：
  - **基线**：`/Applications/CLD.app/Contents/Resources/app.asar`（185,260 B / 21 文件 / sha256 `0d0cf847…`）。先 `ditto` 全量拷贝至 `/private/tmp/cld-p2-stage/`（asar 指纹一致、签名仍合法）。
  - **改动（仅 `main.js`，+13 −2，净 +1108 B）**：
    1. **缺陷①顺序倒置**：崩溃自动重启分支内把 `lastResolvedUrl = null; resolveUrl = null;` **移到** `const urlPromise = awaitServerUrl();` **之前**，与 `reloadDsh()` `:578-581` 的正确顺序对齐（并加 8 行说明注释）。
    2. **缺陷②计数不清零**：`urlPromise.then((u) => {` 回调**首行**插入 `crashRestartCount = 0;`（并加 3 行说明注释）。
  - **重打包保真**：`@electron/asar pack` v3.4.1 产出的头部键集与原始**逐项一致**（`size` / `offset`(字符串) / `integrity{algorithm,hash,blockSize,blocks}` / `executable`）——实测「每文件键集一致 ✅」「executable 标志一致 ✅（6 个 scripts/*.sh 保持 `executable:true`，main.js 无）」；**唯一内容差异文件 = `/main.js`**（`862a721f…` → `dc0dba73…`）。回环解包 `diff -r` 全树一致。
  - **重签方式（不采用已废弃的 `codesign --deep`）**：**只重签外层 bundle**——`codesign --force --sign <Developer ID Application: Zhenyu Liang (XS7SMKFS42)> --options runtime --preserve-metadata=entitlements --timestamp`。比全量 deep 重签**改动面更小**。
  - **✅ 离线验收全过（实测数据）**：
    - `codesign --verify --strict` 与 `--verify --deep --strict`：**valid on disk / satisfies its Designated Requirement**。
    - **主可执行 CDHash 已变**（`e8ea4a69…` → `e4aaa771…`）＝重签确实生效；**7 个嵌套二进制 CDHash 全部未变**（Electron Framework / CLD Helper ×3 / ReactiveObjC / Squirrel…）＝改动面被限制在外层。
    - **DR 逐字不变**（diff 空）；**entitlements 4 项逐项一致**（`allow-dyld-environment-variables` / `allow-jit` / `allow-unsigned-executable-memory` / `disable-library-validation`）；`Sealed Resources version=2 rules=13 files=18872` 维持。
    - **封印闭环**：新 `CodeResources` 的 `Resources/app.asar` 记录 `e4558a52…` == sha1(补丁 asar) ✅；旧记录 `248c08b5…` == sha1(原始 asar) ✅。
    - **功能性读取验证**：用 App 自带 `ELECTRON_RUN_AS_NODE=1 … -e`（只读）读取重打包 asar → Electron 43.4.0 正常读出 `main.js`、`vm.Script` 编译通过、两处修复标记命中、"复位 < 注册" 断言通过；对照组（线上未打补丁）同断言报 **"仍倒置"** ⇒ 断言具备判别力。
  - **⚠ 公证边界（~~诚实声明~~ → 已于同日解除，见下方落盘记录）**：当时**仅存** `~/.appstoreconnect/private_keys/AuthKey_VA9RR5747M.p8`，全盘未找到 issuer-id、亦无 notarytool keychain profile，故按「**无法重新公证**」结案。**该结论已被推翻**：使用者于 15:2x 线下提供 issuer-id `f2c8d085-5125-4262-8950-63b427f34015` 后，**重签 → 公证 → staple 全链走通**（见下）。初始表述「重签后 `spctl` 报 `rejected / source=Unnotarized Developer ID`」在**提交公证前**成立、**staple 后不成立**。**本机影响：本来也无**——`/Applications/CLD.app` **无 `com.apple.quarantine` 属性**（实测），非隔离应用不经 Gatekeeper 首次评估即可启动；DR 不变 ⇒ TCC 不受影响。
  - **落盘与回滚**：产物留存 `~/.cld/backups/p2-2026-10-08/`（`app.asar.patched` / `app.asar.orig` / `main.js.patched` / `main.js.orig` / `main.js.diff`）；脚本 `~/.cld/tools/apply-p2-asar-swap.sh`，子命令 `check | apply | verify | rollback`（`apply`/`rollback` 会**先拒绝在 CLD 运行时执行**，且落盘前校验线上 asar 指纹必须等于原始值，否则拒绝覆盖）。
  - **落盘前置约束**：`Resources/app.asar` 被运行中的 Electron 实例**惰性读取**，替换须在 **CLD 完全退出**后进行（本会话受「不擅自停/重启 CLD」约束，故 `apply` 交由用户执行）。
  - **★ 落盘记录（2026-10-08 15:03）**：`CLD.app` 内 asar `0d0cf847…` → `6a096321…`；重签后**独立复核**（不依赖脚本自身输出）：
    - `codesign --verify --strict` 与 `--deep --strict`：**valid on disk / satisfies its DR**；
    - `CodeResources.files["Resources/app.asar"]` = `e4558a5235f033080ab8a69732a5731e1e190eec` **== 实际 asar sha1**（封印已重新收编补丁内容）；
    - 主可执行 CDHash `e8ea4a69…` → `e4aaa771…`（变了）；嵌套 Electron Framework `1db15290…`、CLD Helper (Renderer) `1844f133…` **均未变**；
    - DR 与 4 项 entitlements 与修复前逐字/逐项一致；
    - `Resources/` 内**无** `app.asar.p2*` 残留（脚本 EXIT trap 已清）；
    - 落盘前备份 `~/.cld/backups/p2-2026-10-08/app.asar.before-apply-20261008-150306`（sha256 `0d0cf847…`，与原文件一致）。
  - **脚本自身踩坑（已修）**：macOS `/bin/bash` 为 **3.2.57**，会把 `$ts（` 里紧跟的**全角括号**当作变量名一部分 ⇒ `unbound variable`。修法：`${ts}（`。已在全文件扫描并消除 3 处（另加 EXIT trap 清理 bundle 内临时文件）。
  - **★ 公证记录（2026-10-08 15:27–15:34，已独立复核）**：提交包 `ditto -c -k --keepParent` 产出 `/tmp/cld-notarize/CLD-0.3.0-p2.zip`（**178 MB**）→
    `xcrun notarytool submit … --key AuthKey_VA9RR5747M.p8 --key-id VA9RR5747M --issuer f2c8d085-5125-4262-8950-63b427f34015`
    → submission `96751d07-e520-4a0c-9c81-da5a8e924c7c`，**约 7 分钟**（第 14 次轮询）**Accepted** → `xcrun stapler staple` + `validate` 均成功。
    复核（不依赖脚本自身输出）：`spctl -a -vvv -t exec` = **`accepted` / `source=Notarized Developer ID` / `origin=Developer ID Application: Zhenyu Liang (XS7SMKFS42)`**；staple 后 **asar sha256 仍 `6a096321…`**、**封印 `files["Resources/app.asar"]` 仍 `e4558a52…` == 实物 sha1**、**主可执行 CDHash 仍 `e4aaa771…`**（staple 不改主二进制）、`--strict` 与 `--deep --strict` 仍通过。
    **票据位置与新认知**：staple 把公证票据写进 **`Contents/CodeResources`**（2,136 B，内含 Apple CA 链 CMS，mtime 15:34），**不在** `_CodeSignature/CodeResources` 封印的 `files` 段内（`rules2` 的 `^[^/]+$` 规则容忍它）⇒ **不破封**（deep-strict 实测通过）。
    **⇒ 前向约束（重要）**：票据**绑定当时的主可执行 CDHash** ⇒ **任何一次再次重签都会作废本票据**，须**重新提交公证**（不是重新 staple）。故若日后要做 C-1/C-2 那批 asar 补丁，**必须把「重新公证」计入流程**（同一 issuer-id 可复用）。
    **⚠ 隐私提示**：本次上传的 178 MB 包含 bundle 内私有 `dsh-runtime` 树，**全量送交 Apple 公证服务**；与 10-06/10-07 同 bundle 的先例一致，但后续每次都要重新确认这一点。
- **验收标准**：
  1. **落盘后**：`~/.cld/tools/apply-p2-asar-swap.sh verify` 全绿（签名/DR/entitlements/asar 内容四项）。
  2. **野外判据**：制造一次 dsh 崩溃自动重启后，`~/.cld/logs/dsh-web.log` 出现 `[child-exit] 重启后 dsh 就绪: http://127.0.0.1:<新端口>`（修复前该串 **15 次自动重启 0 次出现**），且**不再新增** `[url] … 无 await 消费者(重载间隙)`；窗口 URL == 新端口。
  3. **计数复位**：≥3 次崩溃但每次自愈成功时，壳**不再**弹 `dsh server stopped unexpectedly` 并退出。

### CLD-027 · dsh 每次启动弹默认浏览器（`--no-open` 被配置层切断）—— ✅ 已修（配置层，待用户重启生效）
- **类型**：缺陷（体验；含信任面外溢）　**优先级**：P2　**状态**：**✅ 已修**（2026-10-08，改**用户层配置**；**待用户自行重启 CLD 生效**，助手未动任何进程）
- **现象**：每次启动 CLD，除主窗口外还会**弹出一个默认浏览器窗口**，打开 `http://127.0.0.1:<port>` 的 dsh runtime UI —— 即使用者所述「runtime 窗口弹出，只应约束在 CLD 内」。
- **实测**：`~/.cld/logs/dsh-web.log` 内 `CLD boot` **49** 次 / `dsh web: opening the default browser` **41** 次；末次 boot `2026-10-08T07:36:18Z`（本地 15:36）仍在弹。
- **排查链（逐层排除，各步均留实证）**：
  1. **不是 CLD 漏传参**：`ps` 实测在跑的子进程 argv = `CLD --expose-internals …/dsh/lib/bin.js web --port 0 --no-open`；`main.js:427` 亦如此。
  2. **不是 argv 布局问题**：以 App 自带 Electron 跑自建探针（`ELECTRON_RUN_AS_NODE=1 CLD --expose-internals probe.js web --port 0 --no-open`）⇒ `process.argv.slice(2) = ["web","--port","0","--no-open"]` ✅。
  3. **不是 dsh 解析链问题**：以 runtime 内 commander **原样复刻**两层解析（外层 `dsh/lib/bin.js` → 内层 `dsh-web-app/lib/startup.js`）⇒ 外层残留 args `["--port","0","--no-open"]`、内层 `opts() = {"open":false,"port":"0"}` ⇒ `openBrowser=false` ✅。
  4. **⇒ 配置层丢键**：官方层 `dsh-web-app/cordis.patch.yml:141` 是 `openBrowser: !!js ctx.webStartup.openBrowser`（由命令行驱动）；而用户层 `~/.dsh/profiles/web/cordis.patch.yml` 的 `- id: web-runtime` 条目**整段替换**该行 config（该文件第 5 行自带此约定），却**漏 restate `openBrowser`** ⇒ 键缺失 ⇒ 落到 schema 默认 `z.boolean().default(true)`（`dsh-web-app/lib/index.js:32`）⇒ **恒为 true，flag 路径被彻底切断**。
- **修复**：用户层该行补回 `openBrowser: false`（**字面量**；注释注明要恢复「由命令行控制」则改回 `!!js ctx.webStartup.openBrowser`）。**未改 asar** ⇒ **无需重签、无需重新公证**。
- **⚠ 承重键**：同一行的 `printUrl: true` **必须保留** —— CLD 靠解析 stdout 的 `dsh web: http://127.0.0.1:<port>` 取 URL 并 `loadURL`；改掉即白屏。
- **备份**：`~/.dsh/profiles/web/cordis.patch.yml.bak-openbrowser-1791445176`
- **生效路径**：该配置惰性读取 ⇒ 需 dsh 重启/热重载（CLD 自带 `POST http://127.0.0.1:31888/reload`）。使用者选择**自行重启 CLD**（2026-10-08），助手不介入。
- **验收判据**：重启后新 boot 段内**不再出现** `dsh web: opening the default browser`；且 `dsh web: http://127.0.0.1:<port>`（printUrl）仍在、CLD 窗口正常加载。
- **遗留同类风险**：用户层 patch 对**每一行**都是「整段替换 config」⇒ 官方层后续**新增**的任何键都会被**静默吞掉**（不报错）。建议把「dsh 升级后逐行比对官方层 vs 用户层键集」列入例行。本次比对结果：仅 `openBrowser` 一项受损。
- **相关但本次未动**：`main.js:822-826` 的 `setWindowOpenHandler` 对 loopback 目标返回 `{action:"allow"}` ⇒ 页面内 `window.open()` 会开一个**裸的原生 Electron 窗口**（另一类「弹出」）。本次现象与之无关；若要一并收敛需另批 asar 补丁（**含重签 + 重新公证**）。

### CLD-022 · node-bridge 日志无轮转撑爆磁盘（71.89 GiB · Data 卷 91%）
- **类型**：缺陷（资源）　**优先级**：**P0**　**状态**：new（2026-09-11 07:2x 实测登记，CLD 健康域发现+核验）
- **对象**：`/private/tmp/node-bridge-mac-mini.log`
- **实测（独立核验，非转述）**：大小 **77,191,937,492 B = 71.89 GiB**；`/System/Volumes/Data` **387Gi 已用 / 40Gi 可用 / 91%**；**无轮转**（无 .1/.gz 兄弟文件）；写入者 **PID 1122** `node-bridge-macos-arm64-v1.4.0 --node-id mac-mini --hb 60 --queue 2 --notes 5`（**秒级轮询 ⇒ 高频写日志**）
- **速率与 ETA（按窗分开，不可互否）**：长窗（进程运行 6.66 天）平均 **10.81 GiB/天 ⇒ 3.70 天耗尽**；短窗 45s/60s 实测 **22.66 / 26.60 GiB/天** ⇒ 若持续则 **1.5–1.8 天**；**当前速率约为历史均值 2.1 倍**（281 KB/s 外推 6.66 天应 162 GB，实际 77 GB）
- **⇒ 处置建议**：① 立即截断（`: > 文件`，保留 inode、不必重启 bridge）或轮转（需属主确认句柄）；② 治本：给该 bridge 加**按大小轮转/上限**；③ **破坏性动作须属主+用户授权**（守灯不代删、非我域；处置前取证已完成——本卡即「处置前证据」）
- **属主**：通信层 node-bridge（**属主待确认，不推定**）
- **负责人建议**：属主（截断/加轮转）+ 守灯（持续监控与验收）
- **验收标准**：该日志 ≤ 1 GiB 且 Data 卷占用 ≤ 85%；新增日志有上限或轮转
  · **⚠ 判据修正（2026-09-11 09:1x，本地实测后）**：原文未声明用哪个指标 ⇒ 须明确：**①『≤1 GiB』用 `du`（已分配块）判，不用 `ls`（逻辑大小）**；**② 卷回收看 `df`**。理由：实测截断后若持有者用非追加 fd 续写，**逻辑大小会跳回旧偏移**（实测 110 MB 逻辑 vs 10 MB 实际占用，稀疏空洞）⇒ 用 `ls` 验收会**误判失败**。③ 若要求逻辑大小也归零，须**重启/轮转写入者**（截断做不到）。
  · **详见**：`data/cld-health/truncate-semantics-measured-20260911`（实测四行 + 边界 + 未测项）

- **处置提示（2026-09-11 07:5x 补）**：**务必以 `lsof` 实测为准**（PID 1122 仍在并持有 fd，实测于 07:43）；**hazard 卡内 PID 字段仍含旧值（『PID 已变/不存在』）未更新** ⇒ 勿据此推断『fd 已关闭、空间已释放』。**截断用 `: > 文件`，不要用 `rm`**。
  · **⚠ 表述更正（09:1x，本地实测）**：原写「rm 对持有 fd 的文件不释放空间」**不精确** ⇒ 实测 rm 后仅 **+16 KB**（不释放），**关闭 fd 后才 +102,392 KB**（100 MB 全额）⇒ 正确表述：**删除的释放被推迟到持有者关闭**；对**长驻进程**等价于**实际上永不** ⇒ **结论不变（仍应截断），但理由要写对**。
- **关联改进**：health-check 增补「**磁盘最大占用者**」检查（现仅报占用率、不报病因）——属我域，**✅ 08:07 已交付**（item 18，见下）
- **✅ 交付（08:07，我域）**：`health-item18-disk.sh` + `health-check.sh` 第 18 项。**旧项缺的正是这一格**：旧粒度是**占用率**（「Data ≥85%」），新粒度是**占用者** —— 大文件 + 存活时长(birthtime) + 轮转兄弟 + lsof 持有者 + 两采样增长速率/ETA。**首次运行即复现本卡对象**：`72.7 GiB ｜ 存活 160.5h ｜ 最近写 0.00h ｜ 无轮转迹象 ｜ 持有者 node-brid`，并算出 **24.00 GiB/d ⇒ ETA 1.51 天**（构造样本验证）。验收三步全过（正向 exit1 / 反控 500GiB⇒exit0 / 效应判据=目录无残留）；R006 v2 #10 Lean4 门复测 **5/5 PASS**。
- **本卡对象最新实测（08:07–08:13）**：体积 78,132,866,587 B = **72.77 GiB**（较 07:26 的 77,266,471,352 增 **0.81 GiB / 47 min ⇒ 24.7 GiB/d**，与短窗 22.66/26.60/29.43 同量级）；**存活 160.5h（birthtime 2026-09-04T15:38:33）**；Data 卷 **92% / 36Gi 可用**（07:4x 为 91%/40Gi，**1 小时内又少 4Gi**）⇒ **实况 ETA ≈1.4 天**；长窗 3.70 天假设与三短窗连续不符（**第 4 次**），应以短窗为准。
- **更新（07:3x，复验+校正）**：**PID 1122 存活且持有该文件 fd（lsof 1u）**、仍在增长 ⇒ 第三窗 **29.43 GiB/天** ⇒ **ETA 区间收紧为 1.4–3.7 天**（40 GiB ÷ 29 ≈ 1.38 天）；三窗 22.66 / 26.60 / 29.43 量级一致 ⇒ 非一次性突发
- **治本方向（HR 补充，我方认同）**：**不是删日志，而是改轮询粒度或加轮转** —— `--queue 2 / --notes 5` 是**秒级时间观**在通信层的实现，其实现层副作用 = 10+ GiB/天 ⇒ **响应频率 ≠ 记录频率**，应解耦（降采样/聚合落盘/按大小轮转）

### CLD-023 · 属主未定阻塞（guard 插件 + node-bridge）—— 需用户一次裁定两处
- **类型**：治理（阻塞项）　**优先级**：**P1**　**状态**：new（2026-09-11 登记，待用户裁定）
- **现象**：今晚出现**两处同型阻塞** —— 修复已设计/已取证，但**无属主可派**：
  1. **`dsh-plugin-guard`**：属主未登记（resource-registry 0 命中 · package.json 无 author · 无 git · 无 README · tools-registry 未记录）。⇒ 阻塞其 **C1 缺陷修复**（设计稿已成：`c1-fix-design-draft-20260911`）
  2. **`node-bridge`**（`rust-bridge/dist/node-bridge-macos-arm64-v1.4.0`，PID 1122）：属主未定 ⇒ 阻塞其**治本修复（加日志轮转/改轮询粒度）**（评估已成：CLD-022）
- **共同后果**：**修复路径不可解**（非「没人有时间」，而是「无人可被指派」）；且**破坏性动作（截断）亦无人可授权**
- **⇒ 建议（合并为一问，避免两次决策）**：请用户在裁定 guard 属主时**同时裁定 node-bridge 属主**
- **候选线索（不推定）**：guard — 2026-09-04 `mbp-ops` 名义的「立项落地」卡（**但该 from 已被证实为工具硬编码 ⇒ 不可作为作者证据**）；node-bridge — 属通信层（星桥/comm 域？）
- **我方边界**：只登记阻塞与候选线索，**不推定、不代派、不代改**

### CLD-021 · CLD 辅助功能权限反复失效（反复弹「控制电脑」授权）
- **类型**：缺陷　**优先级**：P2　**状态**：new（2026-09-07 用户反馈登记，归因分析中）
- **现象**：系统设置→隐私与安全性→辅助功能反复需要重新勾选 CLD，即便已勾选也会在重启/更新后失效，反复弹「需要控制电脑」权限。
- **根因（初步，实测证据）**：CLD.app 用 **adhoc 临时自签名**（`Signature=adhoc`、`TeamIdentifier=not set`）；macOS 辅助功能授权按**代码签名 CDHash 绑定**，签名变化→系统视为「新应用」→旧授权作废需重勾。实测：
  - `spctl --assess` 报 `code has no resources but signature indicates they must be present`（签名与资源不匹配，半失效态）
  - `AXIsProcessTrusted()` = False（辅助功能未真正生效）
  - 主二进制 mtime 2026-09-07 02:47 被重签（但 app.asar 仍 09-05 → 改壳/重签非代码升级）
  - 今日 42 次 DID NOT EXIT CLEANLY / 16 次自动重启（`dsh-crash → child-exit 自动重启 1/3` 链）——崩溃自动重启疑似触发重签
- **处置方向**：① 治本：改用固定开发者/证书签名（CDHash 稳定→授权长期有效；属 codesign 重签范畴，A3/A4 曾批准同类操作，需用户终端命令）；② 定位 02:47 重签触发源与崩溃自动重启链是否对 CLD.app 重签（需止血）；③ 一次性补救：移除旧 CLD 辅助功能条目后重勾一次。
- **负责人建议**：守灯（归因跟踪）+ 3d490920/43b1a2d3（宿主重签）+ 6e49710e（体检）
- **验收标准**：辅助功能勾选后跨 CLD 重启/更新保持有效，不再反复弹授权；AXIsProcessTrusted()=True。

### CLD-020 · CLD 堆 OOM 崩溃（3.78GB，09-01/09-02 双事件）
- **类型**：缺陷　**优先级**：P1　**状态**：assigned（守灯归因分析，2026-09-02；待协调者/运维处置）
- **证据**：① dsh-web.log 2× `FATAL ERROR: CALL_AND_RETRY_LAST Allocation failed - JavaScript heap out of memory`；② CLD-2026-09-01-145531.ips（133KB，14:55，Node/V8 heap OOM，多 WorkerThread 帧含 node::worker::Worker::Run）；③ CLD-2026-09-02-004439.ips（113KB，00:44，EXC_CRASH/SIGABRT 二次崩溃）。
- **环境关联**：swap 92% 高位持续（16GB 近满）+ 内存压力（多会话/Worker 线程活跃）——与 OOM 高度相关。
- **时间线**：09-01 boot 06:45→09:26→16:44（14:55 崩溃后 16:44 重启）；GUI 现 56711。
- **建议**：① 内存压力缓解（purge/会话压减/Worker 并发限制）；② 评估 V8 heap 上限或插件 Worker 数；③ CLD-002 看门狗安装后可留痕此类崩溃（待用户安装）；④ 归因已落基线 §9。
- **负责人建议**：守灯（跟踪）+ 3d490920/43b1a2d3（宿主侧）+ 6e49710e（体检）
- **验收标准**：连续 7 天无 heap OOM；swap 常态 <60%。

### CLD-019 · localhost 3081 inject-proxy 上游端口过期
- **类型**：缺陷　**优先级**：P2　**状态**：closed（2026-08-18，43b1a2d3 处置 + 本会话验证）
- **处置**：PID 9322（inject-proxy 孤儿）SIGTERM 清理；localhost 3081 恢复未监听；tailnet 68917 权威入口 200；长期机制=CLD 服务器模式启动自动 spawn（下次重启自动重建）。
- **描述**：127.0.0.1:3081（CLD inject-proxy PID 9322，17:16 启动）指向旧 GUI 50387，重启后 GUI 为 63191 → 502 持续（本地回环入口失效）；tailnet 侧 100.120.203.20:3081（node 68917）200 正常。
- **建议**：43b1a2d3 重启 inject-proxy 指向 63191 或 CLD 重启自动重建；远程链路无影响。
- **验收标准**：127.0.0.1:3081 返回 200。

### CLD-018 · 重启后 6 店 Chrome 未自动拉起
- **类型**：缺陷　**优先级**：P1　**状态**：closed（2026-08-18 01:12，de7b29de 恢复+本会话核实 10/10 running）
- **恢复**：重启后拉起 App+看门狗，running 10/10、Chrome 9200-9209 全活；面板响应正常。
- **遗留**：佛山禅城-京东（s9）重启后登录态失效，需用户重新验证码登录（已报协调者跟踪）。
- **描述**：mac-mini 重启后 waimai_state 6 店 running:false（佛山禅城/天河1号/佛山禅城京东/天河守白京东/天河抖店/天河抖音觅趣守白），Chrome 实例未随重启自动拉起；面板 8787 探测不可达（沙箱假阴性可能）。
- **建议负责人**：session-de7b29de（watcher）、session-aa528267（CDP 拉起）
- **验收标准**：waimai_state 10 店 running:true。

### CLD-014 · 供应链维护窗口：sharp CVE-2026-33327 + uuid 9.0.1（供应链专员同步 R1）
- **类型**：缺陷　**优先级**：P1　**状态**：in-progress（sharp 子项 done 已验证，uuid 子项待同窗/低优先，2026-08-18 01:15）
- **sharp 验收（本会话复验 01:15）**：node_modules sharp=**0.35.3** ✓；overrides 顶层含 sharp:0.35.3（pnpm 11 顶层要求，注释含依据）✓；audit 仅 uuid moderate（**CVE-2026-33327 high 已消除**，0e84e65c 实测）✓；health-check 无 sharp 相关异常 ✓。
- **描述**：sharp 0.34.5 high（CVE-2026-33327，deeptide/dsh-knowledge 传递链，唯一路径 overrides 强制 0.35.3）；uuid 9.0.1 moderate 同窗口低优先级。
- **进展**：xberg 平台包 1.0.14 官方 registry 已全发布（6 平台）→ CLD-004「平台包缺失」上游修复，本地资产恢复保留兜底（npmmirror 未同步）；overrides 已迁移 pnpm-workspace.yaml（c1111ffe）；upstream-check.sh 上线可定时巡检。
- **建议负责人**：session-0e84e65c（供应链专员）
- **验收标准**：维护窗口内完成 sharp/uuid 升级，audit 无对应 CVE。

### CLD-012 · wmmon 常驻化迁移评估
- **类型**：增强　**优先级**：P2　**状态**：done（验收通过 2026-08-17 04:14：dsh-plugin-waimai 已接入 bundles 19 项，waimai_state 免重建可用）
- **描述**：wmmon 为会话级动态插件（preset 引用 `~/.dsh/.agent-presets/waimai-ops/agent.cordis.yml`，实现 `~/meituan-multi`），每次重启需 kind:new 重建。方案：① 改 resident bundle 随 18 bundles 加载（重启自动恢复）；② 或至少把「重开必带 MTM_DATA_DIR + kind:new 重建 wmmon」固化为 SOP 步骤。
- **进展**：协调者已批准**方案①**；aa528267 产出 **`~/dsh-plugin-waimai/`**（package.json + cordis.patch.yml + lib/index.js）：schema 校验 16/16、模拟 apply 16/16、真实调用（state 10 店/capabilities 13 原语/voice 四指令）全部通过。**暂未改** `~/.dsh/profiles/web/package.json`（00:25 事故文件，diff 已备好）——等协调者下个重启窗口统一改（备份 + dump-config 校验）。
- **验收点**：接入后重启 CLD，waimai_* 工具应无需 cordis_run 自动可用（本会话配合验证，post-restart-check 已加该验收步骤）。
- **✅ 验收通过（04:14 我方 + aa528267 双重实测）**：package.json bundles 19 项含 dsh-plugin-waimai；waimai_state 10 店正常；health-check 面板检查 stores=10 stale=0；**17 工具全注册**（16 工具 + 新增 waimai_dify_report），免重建免授权；面板 /api/business 正常、CDP 9200-9209 全通。
- **建议负责人**：session-aa528267（迁移产出）→ 协调者 fa1f9150（窗口接入）

### CLD-013 · 工具调用约定适配（unknown tool 排查）
- **类型**：缺陷　**优先级**：P1　**状态**：closed（2026-08-17 04:14，调用约定适配）
- **结论**：多轮快速重启后本会话直接调用 bash/read/write/edit/grep/glob 报 unknown tool；协调者定位 resume 后 preset 工具装配问题并修复。实测：**工具完整可用，调用约定=所有工具须在 run_code 程序内经 tools.xxx() 调用**（直接调用报 unknown tool，提示用 run_code）。修复后 health-check/read/write 验证通过。
- **影响**：post-restart 复核已补全（GUI 51960 / 19 bundles 含 waimai / 全绿基线 / 面板 10 店）。

## 已解决/关闭

| ID | 结论 | 关闭时间 |
|----|------|---------|
| CLD-001 | 误报：告警链路健康（面板 PID 82652、lastTick 新鲜），静默=无新订单 | 2026-08-17 00:09 |
| CLD-003 | 根因=session-28ca132e 两次 write 裁剪+拼写错误；23:54 已修复 | 2026-08-17 00:04 |
| CLD-006 | 3081 冲突源于 28ca132e 手术；当前新 proxy 正常监听 | 2026-08-17 00:04 |
| CLD-007 | health-check.sh 交付并验证全绿 | 2026-08-17 00:05 |
