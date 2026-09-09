# 回归基线（QA 验收员维护）

> 目的：交付物改动后，可复跑用例集 + 基线数据，快速判断是否回归。
> 更新：每次验收发现基线漂移时更新并登记。

## 1. 插件冒烟基线（plugin-smoke）

> 工具链版本状态：**脚本已含 v1.2 功能**（logSinceBoot/bootMarker 配置位，plugin-smoke.sh L71-80，04:59 快照）；README 标题仍「模板 v1」未同步——文档一致性注意项（2026-08-17 核对）。plugins.json 实配 4 插件（agent-bus/repo-pipeline/local-projects/waimai）。
> 冒烟口径样例（e0c391f7，plugins.smoke.json）：双通道（构建产物存在 + host 加载日志模式匹配），纯客户端无 HTTP 端口适用；与 v1.2 合并统一模板在途（b241741f 属主 + e0c391f7 校准）。
> ⚠️ logGlob 差异（2026-08-17 e0c391f7 实测确认）：原样例 `~/.dsh/sessions/**/*.log` **匹配不到任何日志**（该路径下为会话目录非 *.log），已废弃；统一模板以 `~/.cld/logs/dsh-web.log` 为主（6ed4daf2 实配正确）；参数化：hostLog=~/.cld/logs/dsh-web.log、sessionDir=~/.dsh/sessions/（仅会话清单参考）。

来源：~/dsh-collab/plugin-smoke/（6ed4daf2 实配 · b241741f 工具链）

| 插件 | 基线判定 | 基线证据 |
|------|----------|----------|
| dsh-plugin-agent-bus | PASS | lib 三产物齐 + 挂载标记 + /agent-bus/dashboard 200 |
| dsh-plugin-repo-pipeline | **PASS** | 复验通过（2026-08-17 复验）：f9b659e 修复 2 注意项（schemastery→peerDependencies + README 前置条件文档）+ CI [success]（npm ci 权威构建）+ 双仓一致；宿主工具 repo_pipeline_status 可用 |
| dsh-plugin-waimai | PASS | lib/index.js + 挂载标记 + waimai_* 16 工具 + 8787 10 店在线 |
| dsh-plugin-local-projects | PASS | build 双产物 + 挂载标记 + 侧边栏面板（人工项）|

**复跑命令**：`~/dsh-collab/plugin-smoke/plugin-smoke.sh [插件名]`
**口径**：构建 exit=0 + 产物存在 + patch 挂载标记 + host 日志（logSinceBoot 甄别旧残留）+ 宿主工具补强

## 2. 面板端点基线（8787，宿主 API 权威）

> 协作方：session-45f89009（外卖门店多平台运营）提供端点清单/预期口径（店铺数/字段语义），2026-08-17 建立协作线；waimai 16 工具链路（state/alerts/report 三件套）为基线用例之一。

| 端点/工具 | 基线判定 | 基线值 |
|-----------|----------|--------|
| waimai_state | PASS | 10 店在线、告警数可读 |
| waimai_alerts | PASS | 待处理告警列表返回 |
| waimai_report | PASS | 按店聚合事件/拒单率/高峰时段 |
| waimai_traffic | PASS | 曝光/入店率/下单率/渠道占比 |
| waimai_issues | PASS | 异常列表返回（拒单率红线等）|

**面板端点回归用例集 v1**（2026-08-17 合并归一：45f89009 完整清单 + de7b29de 清单 + 宿主工具对照）

■ 只读核心端点（回归首选，宿主工具对照/面板只读）
| 端点 | 语义 | 预期口径 |
|------|------|----------|
| GET /api/state | 店铺状态数组 | 10 店，login: logged_in\|offline、running: bool；当前 pendingAlerts=6 |
| GET /api/alerts?status=&limit= | 告警列表 | {alerts:[]}；当前 pending 6 条 = 2 订单 + 4 批量 count>0 |
| GET /api/report?days=1 | 10 店日报 | 新订单/状态变化/客户消息/接单拒单/拒单率 0%/高峰时段 |
| GET /api/analyze?days= | 订单聚合 | 各店事件量/时段热力/最近订单 |
| GET /api/events?limit=30 | 事件流 | {events:[]} |
| GET /api/channels | 渠道 | {channels} |
| GET /api/kb?platform=&limit=60 / /api/kb/search?q= | 知识库 | {docs} / {results} |
| GET /api/im/stats / /api/im/replies?status=&storeId=&search= | IM 统筹 | imSessionStats() / {sessions,stats} |
| GET /api/im/overdue（超时统计，2026-08-17 de7b29de 新增）| IM 超时 | 只读回归用例 |
| GET /api/scenarios?minutes=60 / /api/issues | 场景/异常 | 场景扫描 / {issues,text} |
| GET /api/capabilities | 原语库 | {capabilities}（13 原语）|
| GET /api/business?storeId=&quick=1 / /api/business/module?module=… | 经营全景 | quick 模式；module=business\|service\|market\|customer\|comment\|diagnose\|grade\|product |
| GET /api/traffic?storeId= / /api/traffic/products / /api/keywords?days=7 | 流量/关键字 | 曝光/渠道/词频 |
| GET /api/review?storeId=&mid= | 评价 | {text,badText} |
| GET /api/insight?module=all&days=7&storeId= | 经营指导 | 双轨（aa528267 lib）|
| GET /api/mosaic / /api/desk/status / /api/shipping / /api/events/stream | 聚合/桌面/配送/SSE | {stores,ts} / {yabai} / {shipping} / SSE 25s ping |

■ 写端点（回归谨慎：只读验收跳过；幂等 handle 类可选测，导航窗口/真实 Chrome 类不触碰）
- POST /api/alerts/:id/handle、/api/alerts/handle-all（幂等可测）
- POST /api/im/session/handle、/api/im/reply、**/api/im/send（IM 回复发送，智能客服接入中 2026-08-17 新增）**（导航窗口/真实发送类，不测；受控样本验收需 `IM_SEND_ALLOWED=1` 开关——当前全局关闭默认返回「IM 发送已停用」）
- POST /api/action（confirmed=false 演练模式可测）、/api/scan、/api/recorder/*
- POST/PUT/DELETE /api/stores、/api/shipping（数据变更，回归用临时数据+清理）
- POST /api/stores/:id/launch|stop|probe|focus|minimize|hide|orders|im|operate|refresh（真实窗口/Chrome——不测）

■ 错误码契约：400=参数错 / 404=店铺或任务不存在 / 500=异常；未匹配路由 404 {error:"未找到接口"}

■ 基线快照三件套（QA 宿主工具权威实测，2026-08-17）：
- waimai_state：10 店（meituan×6 + jd×2 + douyin×2）✅ + pendingAlerts=6 ✅
- waimai_alerts：6 条（2 订单 + 4 批量 count>0）✅ 与预期口径一致
- waimai_report/analyze：10 店聚合（37 新订单/629 客户消息/拒单率 0%）✅
- ⚠️ 注意：waimai_state 工具投影无 login 字段（宿主工具与 /api/state 字段集差异，标注）；running=false 为当前 watcher 状态，与「10 店在线=数据可查」口径区分

■ 基线快照对照（双时点归档，2026-08-17）：
| 时点 | state | report | alerts | 来源 |
|------|-------|--------|--------|------|
| 08-16 采集 | 10 店 logged_in+running:true，pending 6 | 37 新订单/637 消息/拒单率 0% | 6 条（2 订单+4 批量）| 45f89009 |
| 08-17 QA 实测 | 10 店（running 状态为采集时 watcher 状态），pending 6 | 37 新订单/629 消息/拒单率 0% | 6 条（2 订单+4 批量）| QA |
- 差异归因（45f89009 观察）：**面板重启后 watcher 逐店恢复需 ~80s**（0-40s 部分店 running:false → 80s 后全绿）——running 字段差异为恢复窗口所致，非面板异常
- **回归断言建议（已采纳）**：state 用例加「恢复窗口容忍」——面板重启后 90s 内断言 10 店全绿即可
- **login 字段澄清（45f89009 08-17 实测）**：恢复窗口后（>90s）waimai_state 含 login 字段（10 店全 logged_in）；「无 login」为重启初期快照（watcher 未恢复时 login 缺失）——**state 断言需在恢复窗口后（>90s）执行**（QA 08-17 实测 running:false 时点的 login 缺失即此状态）
- **report 滚动快照浮动容忍（45f89009）**：客户消息计数为实时事件流累积（08-16 637 vs 08-17 QA 629），基线断言 ±2% 浮动容忍

■ 回归测试数据位（aa528267 提供，2026-08-17）：
- /api/business：storeId=8（守白鲜花）quick=1（全景 9 模块）
- /api/review：storeId=2（天河3号店，39 卡 1 差评真实数据样本；差评 id80 订单 3302259321482867555）
- 差评分类用例：「真的不好看丑死了」→[商品品质]

> ⚠️ 健康判定铁律：宿主 API 工具权威（waimai_state 等）；bash curl 沙箱假阴性教训已入 playbook（de7b29de），curl 仅参考不做最终依据。
> ⚠️ **面板端点超时阈值（2026-08-17 aa528267 复测定案）**：review 加载 ~17s / business quick 串行 45-60s（traffic/product 慢页面）——回归测试需 `curl -m 90`，用例集 v1 超时阈值 90s（此前 30s 造成 review 空响应与 business fetch failed 误判）

## 3. GUI 视觉回归项（人工确认类）

| 项 | 基线行为 | 备注 |
|----|----------|------|
| settings.section 注册 | 设置弹窗可见插件 section | 需 GUI 打开确认（无法代点）|
| 侧边栏面板 | 面板可展开/收起 | 人工项 |

## 4. 可复跑回归用例源（协作交接）

| 用例源 | 协作方 | 内容 | 基线状态 |
|--------|--------|------|----------|
| session.list 延迟测量协议 | 43b1a2d3 | POST /api/session.list（rpcId:bl），直连 ×3 + 代理 3081 ×3 取中位数，超时 60s | **基线数据已归档（2026-08-17 重启后实测）**：重启前 >120s 0 字节（缺陷态）→ 重启后直连 55397：cold1=10.08s/warm2=0.86s/warm3=0.48s（冷启动投影预热、热缓存亚秒）；经代理 3081：15.56/20.36/10.53s（重启验证蜂拥期负载）——120s+ 挂起消失列表可用；冷启动 10s 印证 backlog 根治方向（blank 探测缓存/惰性化）；负载放大依旧需受控负载基线化 |
| 重启后复核清单 | 43b1a2d3 | 3081 代理自愈 / GUI 端口 / 围栏 426 / RPC 基线 | 待重启窗口后产首份数据 |
| 插件安装记录+证据链 | eb5ee9cc | ~/dsh-collab/plugin-install-r1.md 模式（dump-config/client.js 200/工具冒烟） | 每次插件变更后产出，作为冒烟验收输入 |
| 面板端点清单/预期口径 | 45f89009 | 8787 端点（店铺数/字段语义）| 待提供，到位后回填用例集 v1 |
| CLD-004 后置验收 | 724614ce | health-check 复跑：bundles 19 / 拼写 0 / xberg 在位 / link 无缺失 / config_after_boot 归零 | 724614ce 主导后置验收；QA 如需同类验收等锁释放后并行，避免重复 |
| 聚类质量回归 | a3bc8cba | SCENE_RULES 19 类规则变更后验证「其他」占比/场景分布合理性；范本库/话术库/分析报告完整性 | 数据质量类验收；comm.db 170 客户/493 会话为数据基线 |
| DSH-health-check.sh | 6e49710e / 9910d4b2 | bundles 解析/xberg 加载/配置 dump 三连；**v10=16 项**（新增 3080 哨兵/会话日志完整性/xberg 套装/供应链上游）；post-restart-check 13 步清单 | 共享基线：重启+重签窗口后运维复检 + QA 冒烟回归并行；验收维度含工具正确性/口径一致性；QA 已复测 v10（date bug 修复生效、协调变更准确判定）|
| dsh-health.py（远程访问）| 582093dd | 10 项健康检查（远程链路）| 远程访问回归基线；验收 checklist 模板（重启/重签/插件安装验证流程沉淀）即批即用 |
| 会话存储健康脚本 | b278baab | 帧完整性/重复 seq 检测（会话持久化存储）| 回归基线素材；CLD SIGKILL 修复/单写者租约补丁落地后挂验收链 |
| dsh-infra checklist（A-E）| 582093dd | ~/dsh-collab/qa/dsh-infra-acceptance-checklist.md：A 重启复核 10 项健康基线 / B 反代专项（WebSocket/绑定收口）/ C 知识库与嵌入双通道 / D 插件安装与重签后（headless 3082 注意）/ E 回归基线命令 | 远程访问/基础设施回归基线，并入验收流程可复跑 |
| 会话存储健康脚本 | b278baab | ~/dsh-collab/scripts/session-storage-check.js：撕裂帧 ZSTD 扫描/行级解析错误/重复 seq/seq 缺口；自动加载精确解码器 | **QA 独立复跑验证（2026-08-17）：92 会话全扫 0 异常 exit=0**；基线断言=「异常会话 0 + 退出码 0」，post-restart/CLD 或 dsh 升级后复跑；历史已知异常（c73d4226/ce836fb7 曾重复 seq）作负向用例 |

## 5. 注意事项（踩坑警示）

- ⚠️ ~~health-check.sh `date -j` 时区 bug~~ **已修复（2026-08-17 9910d4b2，v10）**：改用 python3 `fromisoformat` UTC 解析（health-check.sh L92/L122）；QA 复测确认——旧误报消失、真实协调变更（05:25 package.json 改写）准确判定。归属澄清：bug 在 cld-health/health-check.sh（v9→v10 修复），不在 6e49710e 桌面脚本（零 date 命令核查）。跑 logSinceBoot 类检查的绕开策略可解除，按 v10 口径复测即可
- ⚠️ **CLD web 动态端口**（2026-08-17 1e54d56d 情报）：`dsh web --port 0` 每次重启端口变化——插件冒烟需端口时用「扫 __DSH_BOOT__ 页面」或 CLD 主进程 lsof 发现（勿硬编码端口）
- ⚠️ **plugin-smoke 并发临时文件覆盖**（2026-08-17 6ed4daf2 反馈）：plugin-smoke.sh 写固定路径临时文件（/tmp/plugin-smoke-build.log + sinceboot.log）——并发冒烟会互相覆盖串读；复跑前先 agent_light 查是否有人跑（或临时文件加 PID 后缀；file:plugin-smoke 锁方案 HR 评估中）
- ⚠️ **repo-pipeline 零 node_modules 硬约束**（2026-08-17 HR J11）：file:~/dsh-plugin-repo-pipeline 禁止 npm install（本地副本遮蔽宿主 peer deps 致 inject 失效）——QA 验收该插件只读，构建验证走临时目录或 CI（npm ci 权威）。**根因补强（0e84e65c 调查）**：node_modules 反复丢失源自 `git clean -x` 级清理（清 ignored 依赖）——冒烟禁用 git clean -x*；纯净环境用 npm ci；可选加 node_modules 存在性前置检查
- ⚠️ **服务托管方式核验**（2026-08-17 fa1f9150 征集回报）：总线桥「切换空窗」教训——手动进程 vs launchd 托管切换时端口冲突/空窗——回归基线应含「服务托管方式核验」（`launchctl print` 权威视图 vs `list` 视图，避免误判）
- **冒烟端点扩展**（1e54d56d）：/mcp-station/api/state（servers/vision/tasks）、/workflow-capture/api/state（captured/candidates/runbooks/tasks）、/mcp-station/api/repo/list、/mcp-station/api/discover
- ⚠️ **工具调用级冒烟三阶段方法论**（2026-08-18 fa1f9150 征集 #2 贡献）：① schema 能加载（补丁生效）② **每种 action 的返回值逐一遍历校验**（补丁生效 ≠ 类型语义匹配——gov 实证：status 返回 data.rules 数字 vs schema 声明 rules:array，运行时校验拒绝）③ **同名不同义字段专项审查**（rules 数量 vs 数组；修复=status 字段改名 ruleCount）——「同名不同义字段」列入冒烟检查清单
- ⚠️ **schema 补丁类修复必须重启后复验**（2026-08-18 fa1f9150）：运行态加载旧代码、磁盘补丁不生效——J37「工具调用级验证」标注「重启前后各一次」；「修复类补丁」专项流程：备份→补丁→重启→全 action 遍历复验→QA 编号

## 6. 基线漂移登记

| 日期 | 项目 | 旧值 | 新值 | 原因 | 验收员 |
|------|------|------|------|------|--------|
| - | - | - | - | - | - |
