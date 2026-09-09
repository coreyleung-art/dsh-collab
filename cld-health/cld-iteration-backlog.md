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
