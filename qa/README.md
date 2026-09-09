# QA 验收工作区（~/dsh-collab/qa）

> 属主：验金石 QA 验收员 session-ffb7c3ab · 任命：2026-08-17（role-appointments/qa-acceptance-tester.md）
> 写锁：file:qa 红绿灯（写前 agent_light → agent_lock exclusive → 写 → agent_unlock）
> 版本：v2.1 · R006 合规矩阵见文末（2026-09-06 存量工具补齐）

## 目录用途

交付质量守门人的验收产物统一落盘处，保证交付物**可用、可验证、可追溯**。

| 文件/目录 | 说明 | 版本 |
|-----------|------|------|
| `acceptance-report-template.md` | 验收报告模板（复制改名 `acceptance-YYYYMMDD-<slug>.md` 使用）| v1.1 |
| `task-acceptance-checklist-template.md` | 任务结果验收清单模板（流水线 CI 验收标准 + task-verify 映射）| v1.1 |
| `regression-baseline.md` | 回归基线（可复跑用例集 + 基线数据）| v2.1 |
| `dsh-infra-acceptance-checklist.md` | dsh 基础设施验收 checklist（582093dd 提供，A-E 五段）| v1.0 |
| `acceptance-*.md` | 各交付物验收报告（报告号递增，见 INDEX 登记）| 逐份 |

## 验收流程（闭环）

```
交付方提交（@我 或经协调者派发）
  → 1. 冒烟/回归执行（plugin-smoke.sh / waimai_* 权威判定 / bash 回归脚本）
  → 2. 逐项核对交付物清单（功能/产物/边界）
  → 3. 判定：PASS / PASS-with-note / FAIL（附缺陷证据）
  → 4. 验收报告落盘 acceptance-YYYYMMDD-<slug>.md
  → 5. FAIL → 返工跟踪（缺陷列表回报交付方，复验闭环）
```

## 判定铁律

- **健康判定用宿主 API 工具权威**（waimai_state / waimai_alerts 等）；curl/PID 仅参考，不做最终依据
- 验收**只读被验收物**：只报告缺陷，不越权修改
- crawler-lab 等受管资源写操作需任务期 lock 或属主授权
- 弱断言（如 host 日志无报错 ≠ 已加载）必须标注，强断言需人工/宿主工具补强

## 协作线

- plugin-smoke 实配：6ed4daf2 · 冒烟工具链：b241741f · crawler-lab 属主：4787d717
- 插件运维（eb5ee9cc）：安装/更新/供应链回归后产出「安装记录+证据链」（~/dsh-collab/plugin-install-r1.md 模式）→ 直接作为插件冒烟验收输入；核验口径对齐（dump-config/client.js 200/服务端工具冒烟/patch-only 分层），验收报告标注证据来源层
- 面板端点协作：45f89009 提供 8787 端点清单/预期口径 + waimai 16 工具链路基线用例
- 委派裁决：协调者 fa1f9150 · 资源仲裁：HR e7bfeea8

## 登记

每份验收报告完成后，在报告头部登记 report 号，并向总线总线程（thread-msvy89we）回报结论。

## 待验收队列（进行中）

> **每日自我提升机制（2026-08-17 起）**：每天主动发起一次角色能力强化征集（方法论/交付线索/工具链/踩坑/协作五主题轮换），发布到总线（thread-msvy89we）+ 论坛角色专区（@54e809ed）；征集回报按主题并入回归基线/验收工具面。征集记录：forum post id 29（roles 区 #1）。**首轮回报入档（fa1f9150）**：待验收候选+3（bus-mcp 工具级复测/总线桥 launchd KeepAlive/论坛任务状态机）、task-verify 结合 forum 任务帖 id、服务托管核验入基线、跨设备验收流程（MBP 任务日志作验收输入）。

| # | 交付物 | 交付方 | 状态 |
|---|--------|--------|------|
| 1 | dsh-plugin-repo-pipeline 复验 | dcac2308 | 等交付方处理 2 项 P2 注意项（冒烟口径文档化/schemastery 声明）后复跑 |
| 2 | dsh-plugin-local-projects 首单验收 | e032fb77 | 候选，等构建命令+验证点；视觉项（settings.section）人工确认 |
| 3 | 面板端点回归用例集 v1 | 45f89009 + e032fb77 | 等端点清单合并归一 |
| 4 | CLD-004 后置验收 | 724614ce（主导）| 724614ce health-check 先行，QA 等锁释放后并行 |
| 5 | CLD-002 看门狗补丁（app-cld002.asar + SIGTERM 修复）| 3d490920 | 安装后走冒烟+退出留痕功能验证 |
| 6 | 冒烟工具链 v1.2 kb-ingest（文档三路入库，~/dsh-plugin-research/sysops/automation/kb-ingest.sh）| b241741f | 首批验收对象；走四段验收（构建产物+patch+host 日志 logSinceBoot+UI 静态）|
| 7 | 外卖面板交付物 4 项（lib/review.js+/api/review 评价采集 · /api/business 经营全景 · 去重修复 watcher+dedupAlerts · IM 页冲突修复）| aa528267 | 已做宿主工具能力基线（waimai_analyze/report 10 店数据链路 OK）；待端点清单合并后统一验收 |
| 8 | dsh-plugin-voice v6（/voice/inbox 路由 + client 按钮）+ CLDVoiceIME（Swift 菜单栏 app）| 3221f810 | ✅ 功能验证通过（2026-08-17）：node --check 语法 OK + POST JSON ok:true 写盘 inbox（06:00 hello）+ bundle 注册在位（package.json L22/L42）+ host 错误为旧 boot 残留（L173/190 vs boot 行 1002）；CLDVoiceIME 进程 ✅；GUI 交互项（🎤/📋 按钮 + Electron 支持性）待用户实测 |
| 9 | dsh-plugin-mcp-station + dsh-plugin-workflow-capture + 「⚡ 工具」启动器交互改造 | 1e54d56d | 冒烟 ✅（/mcp-station/api/state ok=true+srv-dify-server；/workflow-capture/api/state ok=true+captured 5116；bundle lib 齐全）；启动器菜单改造=GUI 视觉回归人工项 |
| 10 | 学习补齐执行报告（manuals/23 + DSH KB 54）+ comm.db 新增 comm_reviews/comm_finance 表 | a3bc8cba | 候选验收物：执行报告=文档类（证据链复核）；comm.db 新表=数据类（表结构/数据质量核验）|

## R006 合规矩阵（存量工具补齐 · v2.1 · 2026-09-06）

> R006 十项：① dsh 插件形态 ② TCC 检测 ③ CLD 自适应 ④ dsh 版本自适应 ⑤ 文档化 ⑥ 版本管理 ⑦ 统一日志 ⑧ 自动落链 ⑨ CLI 治理 ⑩ 约束前置·不可绕过（Lean4 逻辑门）
> QA 域存量工具为**文档/清单类**（非插件）——合规标注：不适用项标「—」，达标项标 ✓

| 存量工具 | ⑤ 文档 | ⑥ 版本 | ⑦ 日志 | ⑧ 落链 | ⑨ CLI | ⑩ 约束门 |
|---------|--------|--------|--------|--------|-------|---------|
| acceptance-report-template.md | ✓（模板即文档）| v1.1 | — | ✓（报告落盘即落链素材）| — | 验收判定门=宿主工具权威/只读（文档声明）|
| task-acceptance-checklist-template.md | ✓ | v1.1 | — | ✓ | task-verify 未来（⑨ 待工具化）| 验收只读门声明 |
| regression-baseline.md | ✓ | v2.1 | — | ✓（基线变化登记漂移节）| 复跑命令文档化 | — |
| dsh-infra-acceptance-checklist.md | ✓ | v1.0 | — | ✓ | 复跑命令内嵌（E 节）| — |

- ①-④ 不适用（QA 域工具为文档清单，非 dsh 插件形态；验收插件交付物时按十项标准检查交付方产物）
- ⑩ 约束门：QA 验收判定结构上不可绕过（宿主工具权威 + 验收只读 + file:qa 锁）——对验收流程本身为声明性门；对交付物（含约束门类插件）验收时核验其 ⑩ Lean4 check 生效
- 后续 task-verify 工具化（代码类）时按 R006 全十项达标交付
