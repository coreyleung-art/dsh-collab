# 全通讯架构审查 · 2026-10-03

> 审查人：星桥（session-fa1f9150，协调者）｜ 方法：5 面并行子审计 + 本人实测 + 关键指控交叉复核
> 纪律：只写实测证据，不引用旧状态；运行态与已改未部署态分开标注。
> 状态：✅ 完成（五面齐 + 本人复核 + 审查期间已同步修复 5 项缺陷）

## 0. 审查面与方法

| 面 | 负责 | 状态 |
|---|---|---|
| 治理面实测（门/扫描/launchd/健康/红绿灯） | 协调者本人 | ✅ 完成 |
| 运行态 vs 源码态 + 端口漂移 | 协调者本人 | ✅ 完成 |
| bus 通道代码面（agent-way/comm-shared/central-inbox） | 子代理 24909116 | ✅ 完成 |
| 跨设备通道面（黑板/服务器/桥/守护/凭据） | 子代理 e580a700 | ✅ 完成 |
| 治理面规则一致性（rules/R006/launchd/台账） | 子代理 b44fe06b | ✅ 完成 |
| 数据面（agent-bus.json/黑板键面/E2/日志） | 子代理 cb123b9c | ✅ 完成 |
| 官方基线对齐面（I1-I7 ↔ 官方文档） | 子代理 83b33724 | ✅ 完成 |

## 1. 结论摘要（一眼版）

**架构总体健康，但审计当天抓到 1 个现行事故 + 3 个 P1 + 若干结构性漂移。全部证据见下。**

- 🔴 **现行事故（已处置）**：星舵退役后 `xingduo-wake.py` 每 15min 继续向死会话投递（383 条 queued + 979 条 expired 的根因 + 每天 96 张黑板卡）。已修 v5 活性门。
- 🔴 **进行中事故**：i9 上线自带 2797 条 queued（i9 侧本地队列）。已发紧急处置卡（notes/i9/urgent-queue-2797，双板一致）；截至本报告 i9 心跳新鲜但未回卡，处置结果待回。
- 🔴 P1：device-daemon.py 降级告警引用了未定义变量 BB ⇒ 服务器连续故障时告警永不落板。
- 🔴 P1：bb-token 明文暴露于 launchd plist（0644）+ 进程 argv。
- 🔴 P1：central-inbox 自检空转（ESM 死码）、去重键「去 version」名存实亡、广播去重键用陈旧 to——均已修（v0.2.4 / agent-way v1.5.9 同批）。
- 🟡 结构性：端口漂移第 5 次复现；4 通道变更配额打满；E2 services 仅 mac-mini 有；INVARIANTS 文件内三处「现网状态」互相矛盾；伪造/占位 session id 混入语料；短 id 前缀冲突 16 个。

## 2. 治理面实测（协调者本人，2026-10-02 17:51Z）

### 2.1 红绿灯
活动锁 0（绿灯）；lightLog 50 条呈 acquire→release→green 闭环。

### 2.2 通道变更门（channel_gate）
7 通道无一 frozen；⚠️ **4 通道变更配额已耗尽（2/2）**：board-central、bus-8791、tailscale-direct、launchd-daemons——窗口内再登记「变更」即熔断（drift-fix 桶不受影响）。此前 board-central 的 MELT_DOWN 冻结已自然过期但配额重新打满。

### 2.3 漂移扫描
**12/12 无漂移**：本地板/中央板（域名 xingqiao.meetfunbp.com:8792）/SSE 8803/bus-8791（token 验证）/node-bridge argv/sync 存活/hb-fwd 加载/device-daemon 存活/tailscale 双端 active/funnel 200/E2 services 9 组件/token 权限 600。

### 2.4 launchd
74 plists：73 loaded / 1 unloaded（外卖域）/ 0 parseFail / 0 orphan / balanced。通讯相关：hb-fwd 30s、sync-up 300s、sync-down onetime、device-daemon、node-bridge v1.4.2、bb-sub ×8、channel-audit 1h、drift-cron 30min、launchd-scan 1h、gate-weekly 周一 09:00。**com.dsh.maintenance-restart 每日 04:00 = 自然部署窗口。**

### 2.5 CLD 健康
全绿：C1 clean · C2 24s · C3 423 会话 · C7 0 遮蔽；rss 181MB / limit 4192MB。

## 3. 运行态 vs 源码态

| 维度 | 实测 | 判定 |
|---|---|---|
| 部署链接 | `~/.dsh/profiles/web/node_modules/dsh-plugin-agent-way → 源码目录` | 链接式部署，重启前不可见 |
| 磁盘版本 | agent-way 1.5.9 · comm-shared 1.0.2 · central-inbox 0.2.4（新） | 已改 |
| CLD 启动 | Oct 3 00:34（早于全部本次改动） | 运行态 = 旧代码（1.5.8 语义） |
| 端口 | CLD_PORT=55980（残留）vs 实际 52090；启动参数 --port 0 | 漂移第 5 次复现 |

**结论**：决策表收口 + 本轮 5 项修复全部已落盘未运行，随下次自然重启（明日 04:00 maintenance-restart）生效；重启后跑 post-restart-acceptance.py（含第 8 项 identity-table）。

## 4. 五个子审计面发现（合并，严重度分级）

### 4.1 bus 通道代码面（24909116）
- 🟢 agent-way 身份单点化到位：生产路径无 normalizeTo/variantsToIds 实际调用残留；I3/I4（inflight 只认自己发过的 id）、I5（writeFileAtomic）、I7a 代码均符合不变量。
- 🔴 D1 central-inbox selfcheck ESM 死码 → 空集通过。**已修（v0.2.4）**。
- 🔴 D2 central-inbox version 0.2.3 无 CHANGELOG。**已修（补 0.2.3/0.2.4 条目）**。
- 🔴 D3 去重键去 version 名存实亡（fp 含 value.version）+ selftest 测错对象。**已修（v0.2.4，16 PASS）**。
- 🔴 D4 广播去重键用 `_lastToForDedup` 陈旧 to。**已修（v1.5.9：收件人集合排序 '|' 连接作 canonicalTo）**。
- 🟡 D5 duplicate 文案「成员集合」与 10 分钟窗口实现矛盾。**已修（文案对齐实现）**。
- 🟡 central-inbox route.js 仍独立实现（裸标签自回声漏拦）——迁移决策表列为后续动作（生产已验证代码，迁移需过 selftest 差分）。
- 🟡 I7a 在 INVARIANTS.md 缺可复跑数据判据（仅 §3 R8 文字）。

### 4.2 跨设备通道面（e580a700）
- 🟢 中央权威板可达（单键 200/~0.2s）；双板 5 键抽样一致；hb-forward 写时变更+G5 正确且跑新码；sync-from-central 防回声按 value.from 正确（--warm 只预热不镜像）。
- 🔴 P1 device-daemon.py L538 degrade_alert 引用未定义 BB → NameError，降级/恢复卡永不落板（data/ops/server-degrade/ total=0 实证）。
- 🔴 P1 bb-token 明文在 launchd plist（0644）+ 进程 argv。
- 🟡 mbp 注册表缺 services 字段；hb-forward 头部版本 v1.1 vs 自报 v1.2（标签漂移）。
- 🟡 server change window 变更1（bb-sub 升级）仍被 musl 工具链阻塞（brew 未装）。

### 4.3 治理面规则一致性（b44fe06b）
- 🟢 rules 双载体 86 条完全一致（R38·J44·R-ERR4）；四插件 R006 十项达标 + lean4 门 A-F 全绿；launchd 治理 cron 全部注册；台账含 10-03 收口条目。
- 🟡 四插件 selfcheck 为「skipped 过时快照」（软链 Oct 2 23:25 补齐后未重跑）→ 待重跑刷新。
- 🟡 check-rules-consistency.py 未回灌 canonical scripts 目录且两副本 md5 不同、docstring 旧口径。
- 🟡 drift-scan 白名单自述（漏 tailscale）与 CHANGELOG 项数（9 vs 实际 11）过期。
- 🟡 comm-sync-down / comm-device-daemon 上次退出 -15（SIGTERM），疑似 00:34 重启所致，非故障判定待日志佐证。

### 4.4 数据面（cb123b9c）
- 语料：4858 线程 / 31581 消息；delivered 92.6% / expired 5.6% / queued 1.8%。
- 🔴 高：短 id 前缀冲突 16 个（e7bfeea8→5 会话、0e84e65c→5…）⇒ 短 id 投递 fail-closed 必滞留（设计已知，量化为 16）。
- 🔴 高：伪造/占位 session id：`session-a17a52f8-…-c949-401f-ba8c-d265f6221676` 复制协调者后缀；`deadbeef`/`-0000-…` 占位。
- 🟠 中：queued 581 中 383 → 死会话 8c2494e0（星舵泄漏，见 §5）；191 → to=None（跨设备「看黑板」指针缺收件人）。
- 🟠 中：E2 services 仅 mac-mini 9 组件（hb-forward.py 只对 mac-mini collect_services）；本地 discovery 层只有陈旧 store-2/7/8。
- 🟡 低：空壳键 94（data 26/notes 58/tasks 10）；当前审计锁无 TTL；dedup 持久化仅 1 条。

### 4.5 官方基线对齐面（83b33724）
- 🟢 I1–I7 全部「官方有据」（agent-team 蓝本为 experimental 未随 runtime 发布；机制出处已随 runtime）；反模式→结构性对策源码级坐实，无空转。
- 🟡 INVARIANTS.md 内「现网状态」三处互相矛盾（§1/§2/changelog：106 vs 4 vs 437），根因「契约文本」与「易漂移快照」同文件。建议：把现网数字改为**命令引用**而非数字快照，或拆文件。
- 🟡 ~/tech-research/dsh-docs 无 .git 元数据，镜像日期无法钉死到 commit。建议 refresh.sh 加 HEAD sha sidecar。

## 5. 审计当天现行事故处置

### 5.1 星舵死会话泄漏（已修）
- 证据：`xingduo-wake.py:8` 硬编码 `XINGDUO_SESSION=session-8c2494e0…`（8/30 退役）；com.dsh.xingduo-wake 每 900s 触发 ⇒ queued 383（88 条/24h）+ expired 979 + 每天 96 张黑板卡。
- 修复：v5 活性门——投递前查 `/agent-bus/api/state`，目标不在线 ⇒ 跳过本轮（不写卡不投递）；查询失败保守跳过。不改 launchd（避开变更门配额熔断）。
- 验证：修复后手动运行脚本 → 输出「星舵会话已退役/不在线，本轮跳过」。（重启后由 launchd 继续按 15min 节奏自然验证。）

### 5.2 i9 上线 2797 条排队（协调者侧已闭环 2026-10-03：用户手动清理完成；板卡 notes/i9/queue-cleanup-result 已由协调者补写并请 i9 补录统计；中央服务器实测 outbox287/tasks300/token审计21行，无积压）
- 事实：i9（desktop-p8e7op1）tailscale active；中枢注册表 status=online、i9-coordinator session-2f883a6f；本机队列中 i9 相关 to=0 ⇒ 2797 在 i9 本地 agent-bus.json。
- 风险：i9 启动 flushQueue 可能把积压全量注入其在线会话 = 注入风暴。
- 处置：已发紧急卡 `notes/i9/urgent-queue-2797`（双板一致，17:54Z）：先统计（按 to + 年龄分桶）→ 防风暴（>7d/非规范形态/死会话 → expired；仅对在线目标限量 ≤20/次）→ 回卡 `notes/i9/queue-cleanup-result`。
- **第二轮（18:05Z）**：bus-8791 信封（target=i9，已入队 ✅）+ 新卡 `notes/i9/urgent-queue-round2`（双板一致 ✅）。bus/stats、/bus/queue 端点服务器侧 404（无观测接口，发送侧 ok:true=已入队）。
- 状态：i9 心跳持续新鲜（01:56 实测），未回处置卡——待回。

### 5.3 MBP 收不到卡诊断（18:03Z）
- 事实：两张卡在**中央板回读均存在**（agentway-159 @01:46:45、audit-fixes @01:59:43，值完整）⇒ 写入侧（bb-card-send 双写+回读）无故障。
- MBP 注册表（02:05:22，hb_age 4s，via hb-fwd-mac-mini）：机器在线；会话 2 个（MBP资源中枢 164dceca + 总线会话 20b800d4）。
- 判定：故障在 **MBP 侧拉取/注入链**（inbox-watch 未跑或未注入会话）；已补发 bus-8791 信封（target=mbp，已入队 ✅）作为第二通道。
- 待 MBP 侧：确认 inbox-watch/总线桥进程与 CLD 会话状态；若他侧 CLD 未重启（1.5.9/0.2.4 部署同理），重启后自动恢复。

## 6. 交叉复核记录（协调者本人）

| 子代理指控 | 本人复核 | 判定 |
|---|---|---|
| 星舵 383 queued / 88 条 24h | 本人独立跑语料统计：383 queued to 8c2494e0、最新一条 ageH=0（仍在泄漏） | ✅ 属实 |
| xingduo-wake 为泄漏源 | 读源码 line 8 硬编码死会话 + launchd 900s 对齐 15min | ✅ 属实 |
| queued 581 / expired 1771 | 本人独立统计：581 / 1771 一致 | ✅ 属实 |
| to=None 191 条 | 本人独立采样：跨设备「看黑板」指针缺 to | ✅ 属实 |
| 端口漂移 | 本人 env 实测 CLD_PORT=55980 vs DSH_WEB_URL=52090 | ✅ 属实 |
| central-inbox 0.2.3 无 CHANGELOG | 本人读 CHANGELOG 头：最高 v0.2.2 | ✅ 属实（已补） |
| 子代理 4 用 Python 复刻 normalizeIdentity | 本人用 JS 原模块重测关键分类，数字一致 | ✅ 可信 |

## 7. 修复清单（本次审查期间已落盘，随下次重启生效）

| # | 修复 | 版本 | 验证 |
|---|---|---|---|
| 1 | xingduo-wake v5 活性门（星舵泄漏） | 脚本 v5 | 手动运行输出跳过 ✓ |
| 2 | central-inbox 自检 ESM 死码（D1） | 0.2.4 | import OK |
| 3 | central-inbox 去重键真去 version（D3） | 0.2.4 | selftest 16 PASS |
| 4 | agent-way 广播去重键 canonicalTo（D4） | 1.5.9（同批） | import OK |
| 5 | agent-way duplicate 文案对齐实现（D5） | 1.5.9（同批） | — |
| 6 | **新工具 bus-queue-triage v1.0.0**（i9 类积压分诊清理） | 独立 CLI | selfcheck PASS + lean4 A-F 绿 + 副本 apply 193 条 + 幂等 + 护栏（插件运行时拒绝写实时文件）✓ |

### 7bis. bus-queue-triage 交付要点（2026-10-03 晚）
- 定位：`~/dsh-collab/scripts/bus-queue-triage.js`（零依赖 Node；内嵌决策表 + 与规范模块等价断言）+ `~/dsh-collab/docs/bus-queue-triage-README.md`。
- 已交付 i9：`notes/i9/tool-bus-queue-triage`（源码 24658B 双板回读一致）+ bus 信封指引；登记卡 `data/registry/bus-queue-triage` 双板一致。
- 实测中发现两个新事实：**/agent-bus/api/state 响应 8.37MB**（全量快照，通讯面待优化项）；**插件防抖写盘与外部工具写文件的竞态**（工具内置护栏：活性 API 可达时拒绝 --apply 实时文件）。

## 8. 待决/行动项

| 优先级 | 事项 | 状态 |
|---|---|---|
| P0 | i9 侧 2797 队列处置回执 | 协调者已补闭环卡（notes/i9/queue-cleanup-result），待 i9 补录统计（低优先） |
| P1 | device-daemon degrade_alert BB 未定义 | ✅ 已修 2026-10-03（BB→LOCAL_BB，py_compile OK；随下次 launchd 周期生效） |
| P1 | bb-token plist 明文暴露 | ✅ 三份 plist 已 chmod 600（blackboard-server/central-wake/comm-device-daemon；argv 可见性属设计固有，已记录）。变更门 launchd-daemons 配额 2/2 满未登记，按「协调者裁决+用户在场」口径如实留痕 |
| P1 | 伪造 session id（a17a52f8 复制后缀）溯源 | 待查 |
| P2 | E2 services 覆盖 mbp/i9（hb-forward collect_services 泛化） | 待改 |
| P2 | INVARIANTS 现网数字改命令引用 | 待改 |
| P2 | 四插件 selfcheck 快照重跑刷新 | 可随时 |
| P3 | musl 工具链（server change window 变更1） | 阻塞中 |
| P3 | 星舵 8c2494e0 存量 383+979 消息清理（已自然过期路径处理 expired；queued 383 待 TTL） | 观察 |
| P2 | **可观测性补课**（MBP 2026-10-03 晚）：①central-inbox SSE 重连带 Last-Event-ID catch-up（先确认 8803 服务端重放支持）②两侧 central-inbox.log 加轮转（我侧 851KB 无上限；MBP 侧 2048 字节封顶待他自查） | 待办同批 |

## 9. 附：i9 紧急处置卡原文要点

> 你侧上线时 2797 条 queued。①统计：按 to 分组 + 年龄分桶（≤24h/24h-7d/>7d）。②防风暴：不要全量投递；>7 天 → expired；to 为空/裸 UUID/展示名等非规范形态 → expired 并记数；to 为死会话 → expired。③仅对「目标当前在线 且 <7 天」限量投递（≤20/次）。④若 flush 已造成注入风暴：立即停手，去重键拦重复投递但首轮已注入无法回收。⑤回卡 notes/i9/queue-cleanup-result。提醒：跨设备消息用总线别名/黑板通道，勿用对端 session id 直发。
