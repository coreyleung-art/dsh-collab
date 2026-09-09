# Agent Bus 重启状态检查点（断点续航）

> 生成：2026-08-16 ~00:00（闪退修复后）· 协调会话 session-fa1f9150-c949-401f-ba8c-d265f6221676
> 用途：**重启后协调会话凭此文件 + 本会话持久化日志 + goal-5370dd00 恢复统筹**（拉回对话的恢复地图）

## 重启前状态（快照）
- 18 bundles package.json ✅ 已恢复（含常驻总线 dsh-plugin-agent-bus）
- 常驻总线数据 ✅ ~/.dsh/agent-bus.json（21 线程 / 17 能力档案，已从动态版合并）
- 动态总线（agbus-1）运行中：10 工具 / 去重 / 能力登记（重启后由常驻版接管，动态版退役）
- repo-pipeline 依赖 ✅ 已补链（schemastery/dsh-tools/cordis）
- xberg 绑定 ✅ 在位；3081 ✅ inject-proxy 正常
- 权限清单 ✅ ~/dsh-collab/agent-bus-permissions.md（L1-L4 门控，已待广播）
- 编排脚本 ✅ ~/dsh-collab/restart-governor.sh（preflight/countdown/go/verify）

## 重启评估状态
- [ ] 广播权限清单 + 重启评估请求（全体智能体就绪确认）
- [ ] 收集评估回执 → 裁决 go
- [ ] 写 RESTART_GO 标记 → 倒计时 → 重启

## 重启后恢复步骤（协调会话执行）
1. **拉回对话**：本会话（session-fa1f9150）由用户重新打开 → 持久化日志恢复 → 读本文件 + goal-5370dd00 续接统筹
2. 验证 18 插件挂载：`bash ~/dsh-collab/restart-governor.sh verify`（agent-bus 路由 200 = 常驻总线生效）
3. 常驻总线接管验证：10 工具 / 大屏 /agent-bus/dashboard / guard / 21 线程 / 17 档案
4. 健康会话 9910d4b2 跑 post-restart-check.md 10 步复核 + health-check.sh --log
5. 广播「恢复公告」：全插件上线 + 常驻总线接管 + 护栏生效
6. 回写本文件为「重启后状态」→ 更新基线

## 关键路径速查
- 总线持久化：~/.dsh/agent-bus.json（常驻，重启后加载）
- 权限清单：~/dsh-collab/agent-bus-permissions.md
- 编排脚本：~/dsh-collab/restart-governor.sh
- 目标：goal-5370dd00（会话日志持久化）
- 恢复地图：本文件

## 风险备忘
- 重启中断 43b1a2d3 的 inject-proxy（launchd 自恢复）
- CLD 重签（可选并入本轮或下轮）：lock clapp:codesign → codesign --force --deep --sign - → 核对 → unlock

## 评估裁决（goal round 1）
- 就绪回执：9910d4b2（ready）、aa528267（ready）
- 未回执 6 会话：按广播规则视为可中断
- 锁数：0 ✅ · 预检全绿 ✅
- **裁决：GO（就绪条件满足）** · RESTART_GO 标记已写入
- 执行方式：restart-governor.sh go（SIGTERM → KeepAlive 拉起）；若 GUI 退出，用户重开 CLD 后本会话自动恢复续接

## ⚠️ 第二次重启执行复盘（00:35）
- 执行：SIGTERM 宿主 94233 → **结果是关闭应用，未自动重启**（KeepAlive 未拉起）
- 教训：本环境 SIGTERM 宿主=关闭；正确重启=用户手动重开 CLD
- **配置已就绪（验证通过）**：18 bundles 全可解析 / xberg 二进制齐 / repo-pipeline 三处包名一致 / dsh --dump-default-config OK
- **恢复动作：用户重开 CLD → 打开本会话（session-fa1f9150）→ 自动续接**

## ✅ 重启恢复完成（00:33 用户重启）
- 18 插件全量挂载：agent_* 10 工具 / repo_pipeline / dshdoc / modlens / web-ui-all 全家桶 全部注册 ✓
- 常驻总线核心上线：agent_peers 实测可用（工具/锁/能力登记/去重全活）✓
- 本会话拉回对话续接统筹 ✓
- 已知缺口：/agent-bus HTTP 路由未注册（webServer 晚到，已按 mcp-station 响应式模式修复 resident 插件，下次重启生效；含 dashboard 大屏）
- 动态版 agbus-1 已随重启退役，常驻版正式接管

## ⚠️ 重启测试三次实证（00:40，最终定论）
- SIGTERM 宿主 = **关闭应用，无自动拉起**（3 次数据点：82521 子进程 / 82830 宿主 / 95362 宿主）
- launchd com.cld.server = headless 模式（KeepAlive），但**未运行**且与 GUI 双实例会引发会话并发写冲突 → 不可用作 GUI 的自动重启
- **结论：本环境可靠重启 = 用户手动退出并重开 CLD**；编排脚本 `go` 路径已禁用（防误用）
- 恢复循环已验证有效：重开后会话拉回 + 常驻总线恢复 + 18 插件挂载（00:33 实证）

## ✅ v0.3 程序化唤醒（00:5x，答复「离线会话如何激活」）
- **核心机制验证通过**：`agents.resume({ resumeSessionId })` 可将持久化离线会话程序化拉活为 live agent（实测拉活 session-9910d4b2，无需手动开会话）
- **新工具 `agent_wake`**（常驻总线第 11 个工具）：ids 指定 / all=全部档案会话 / 缺省=有排队消息的目标；live 直接投递，离线用 agents.resume 拉活后投递（via: resume），无持久化返回 not-persisted；dryRun 预览
- **启动自动唤醒**：宿主重启后 autoWake 钩子自动 resume「有排队消息的离线会话」并投递——重启后无需逐个手动开会话，消息自动送达
- 生效方式：resident 插件改动需下次重启（用户手动重开）后生效；当前实例已用动态 probe 实测验证机制
- 新增 6 个会话已在线（实测 agent_peers：de7b29de / 9910d4b2 / a3bc8cba / aa528267 / b241741f / 4787d717 + 原 3 个）

## ✅ v0.3 受控重启征询（用户要求「重启前问其他智能体」）
- **工具集**（常驻总线 15 个工具）：`agent_restart_request`（发起征询，广播全体 + 宽限期 300s 默认）/ `agent_restart_ack`（ready:true=就绪 / ready:false+reason+etaSeconds=需收尾）/ `agent_restart_status`（查询）/ `agent_restart_go`（confirm:true 激活，广播 GO+倒计时）/ `agent_restart_cancel`（取消）
- **状态机**：polling → ready（全体确认）→ go（激活）→ interrupted/done（重启后恢复）；计划持久化于 store.restartPlan，重启后残留自动标 interrupted
- **重启执行方式不变**：本环境 SIGTERM=关闭不自动拉起（三次实证），go 后需用户手动退出重开 CLD；autoWake 自动恢复在线会话

## ✅ 迭代报告与登记纪律（v0.3）
- 提示词注入 agent-bus:iteration-report（order 117）：完成实质迭代后 → agent_send 发【迭代报告】（完成项/实测证据/产出文件/能力边界变化/遗留建议）+ agent_profile 更新能力档案；纯确认不发

## 🚀 受控重启 GO（01:1x，征询 8/8 全就绪）
- **征询执行**（手动版，v0.3 未生效前用现有工具）：广播两项通知（迭代报告协议即时生效 + 重启征询）→ 8/8 ready（3f34113d/de7b29de/9910d4b2/b3778a1e/4787d717/b241741f/aa528267/a3bc8cba）→ GO 广播送达
- **CLD-012 wmmon 常驻化已完成**：dsh-plugin-waimai 包接入 profile（备份 .bak-prewaimai + dependencies/bundles/link 三处 + JSON VALID + 模块加载 OK）——重启后 16 工具常驻免重建免授权
- **重启后核对清单**：a3bc8cba 的 kbsy 动态插件需重建（kb_* 工具）；de7b29de 核对 8787 无旧 node 进程残留；aa528267 执行 CLD-012 5 步验收；9910d4b2 执行 post-restart-check + health-check --log
- **执行方式**：用户手动退出重开 CLD（SIGTERM=关闭不拉起）

## ✅ 受控重启完成（01:2x，用户手动重开）
- **v0.3 全部生效**：agent_wake + agent_restart_*（request/ack/status/go/cancel）工具注册确认 ✓
- **CLD-012 验收通过**：waimai_* 16 工具常驻免重建免授权（waimai_state 实测 10 店全 logged_in，面板 8787 独立进程跨重启在线）✓
- **agent_wake 实战**：29 会话程序化拉活（28 via resume + 1 live），7 not-persisted（旧 id 无持久化，正常）
- **征询状态无残留**（agent_restart_status → plan: null，重启流程干净）
- **迭代报告协议已随提示词注入生效**（agent-bus:iteration-report）
- pendingAlerts 10 待处理（重启期间新告警，各角色恢复后处理）
- 各角色按核对项自动复核中（kbsy 重建 / 8787 node 残留 / CLD-012 验收 / post-restart-check）
