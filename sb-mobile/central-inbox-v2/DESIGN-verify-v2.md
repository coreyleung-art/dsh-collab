# central-inbox 定向注入改造 · 研究结论 / 设计 / 验证 / 风险（v9.7 P2）

> 日期：2026-09-04 · 沙箱副本改造（J37：未改部署）· 产物目录：`~/dsh-collab/sb-mobile/central-inbox-v2/`
> 范围：只做 P2 的「读 value.to → 定向注入」核心改造；「注入后回报 latest-<session>」是 P2 后续项，不在本包。

---

## 1. 研究结论（全部源码实读，无猜测）

### 1.1 基线文件（重要纠偏）
任务给的材料 bundle 是 **v0.1.4**（`datasets/shared/dsh-plugin-central-inbox-full-bundle-v0.1.4.tar.gz`），但其 `lib/index.js` 顶部直接使用 `join/homedir` 无 import（CJS 隐式全局写法）。部署现状已演进：
- 本机 profile 注册：`~/.dsh/profiles/web/package.json` → `dsh-plugin-central-inbox: link:/Users/coreyleung/dsh-plugin-central-inbox`（symlink → git 工作树，**工作树即部署代码**），列入 `dsh.profile.bundles`。
- 实际运行代码 = `~/dsh-plugin-central-inbox/lib/index.js`（164 行）：v0.1.6 起补全 ESM import（`node:os/node:path/node:fs` + `selfcheck.js`），v0.1.7~v0.1.10 增加 hostname 探测 NODE_ID、mac-mini 硬编码中枢兜底、自查门；工作树另有**未提交**的 45s 假活检测 + 重连抖动。
- git 日志：v0.1.4 → v0.1.10（`e6be744`），当前 `git status` 有未提交改动。
- **因此 v2 基底 = 部署工作树文件**（不是 v0.1.4 bundle，直接以 v0.1.4 为基底会重蹈 v0.1.6「加载即 SyntaxError」崩溃）。本包已注明差异。

### 1.2 agentBus 服务契约（源码实读 `~/dsh-plugin-agent-bus/lib/index.js` v1.5.3，1627 行）
`ctx.provide('agentBus', {...})`（L1617）：
- `list()` → `agentList()`（L1172）＝ `agentsSvc.list()` 映射 **`{id, status, locks, waiting}`** —— **只含当前在线（已加载）会话**。本机实测（agent_peers 同源）20 个在线：18 个 `session-<uuid>` + 2 个裸 uuid 子代理；`session-fa1f9150-c949-401f-ba8c-d265f6221676`（星桥中枢）在线 ✅；`session-aa528267-0434-4bf5-87c5-d5a61f8215b2`（老登）在线 ✅。
- `send(from,to,text,threadId)` → `sendMessage()`（L1096）：
  - 目标在线（`agentsSvc.get(to)` 存在且可 `followup`）→ `deliver()`（L353）`target.followup(...)` 注入上下文 → 返回 **`{threadId, messageId, status:'delivered', targetLive:true, mentions}`**。
  - 目标离线/不存在 → `deliver()` 返回 false → **不抛错**，消息入库 `status:'queued'`，返回 `{status:'queued', targetLive:false}`；`flushQueue()`（L1077）在目标上线后自动补投。
  - `to` 若为节点别名（i9/mbp/mac-mini/mbp-bus…且本机无此会话）→ `deliverViaBlackboard`（L324）转黑板 `notes/<node>/agentbus-<ts>`。
- 去重：`checkDedup`（L259）以 **from+thread+text** 为键、10 分钟窗口 → `{status:'duplicate'}` 不投递；central-inbox 每次 `send` 不带 threadId → 每卡新线程，因此跨卡去重实际由插件自己的 `lastInjected`（单 key 记忆）承担。
- 运行时实证：`~/.dsh/central-inbox.log` 尾行显示 `📩 注入 mac-mini: notes/mac-mini/mobile-inbox/<ts> → delivered`（sendMessage 返回的 `.status`）。
- **结论：send 到不存在/离线会话不会被拒，而是静默 queued——正是必须「先查 agentBus.list() 存在性再 send」的原因**（历史教训：mbp-bus 别名不在 → 消息永久 queued，v1.5.x 三连修复）。

### 1.3 现网黑板卡实际形态（黑板书 8792 GET 实测）
星台对话卡（今天最新一条，与本次需求同源）：
```json
{ "key": "notes/mac-mini/mobile-inbox/1788460243394",
  "value": { "from": "sb-mobile", "session": "main",
             "text": "能不能将星台目前的状态…设备内智能体切换？",
             "to": "coordinator", "ts": 1788460243394 } }
```
- `value.from` = `sb-mobile`（星台桥写，非节点名 → 现有自回声守卫不拦，符合预期）。
- **`value.to` 现网已经带值且 = `"coordinator"`（符号名，非会话 id）** → v2 必须把 `coordinator`/`central` 当「中枢」符号处理。
- 回报卡 `notes/mac-mini/mobile-reply/latest-mbp`：`{from:'mbp-bus', reply_to, session, text}` —— 每会话独立回报（`latest-<session>`）是 P2 后续项。
- 环境变量：本机 `CENTRAL_AGENT`/`DSH_NODE_ID` **均未设** → 实际走 v0.1.9 的 mac-mini 硬编码 `session-fa1f9150-…` 兜底；NODE_ID 由 hostname `CoreydeMac-mini.local` 探测为 `mac-mini`。v2 不依赖这两个环境变量（保持不变）。

---

## 2. 改造设计（lib/index.js v0.2.0）

路由规则（每次事件实时解析，不缓存）：
```
value.to 缺失 / '' / 'coordinator' / 'central'            → 注入中枢 centralAgent
value.to == 某在线会话完整 id                             → 定向注入该会话（=中枢则等同中枢路径）
value.to 是某在线会话 id 的唯一子串（稳定片段，如 fa1f9150）→ 定向注入
value.to 命中 >1 会话（歧义）/ 0 命中（不存在或离线）        → ⚠️ 告警日志 + 回退注入中枢（语义不变）
```
保持不动：WATCH_PREFIXES、`value.from===NODE_ID` 自回声跳过、`value.from==='coordinator' && mac-mini` 跳过、`lastInjected` 同 key 去重、文本 `'看黑板 <key>'`、threadId=undefined、SSE 心跳/重连逻辑。日志行升级为 `→ <target> [direct|central] <status>`，显式 to 未命中追加 ⚠️ 行。

### 文件清单（产物目录 `~/dsh-collab/sb-mobile/central-inbox-v2/`）
| 文件 | 说明 |
|---|---|
| `lib/index.js` | **改造版完整文件**（v0.2.0，约 205 行，ESM） |
| `lib/index.d.ts` / `lib/selfcheck.js` / `lib/adapt.js` | 原样副本（插件自包含可测） |
| `cordis.patch.yml` | v2 建议：insert 行与 v0.1.x **完全一致**（配置走环境变量，无需改） |
| `package.json` | v0.2.0（feat → minor；含 type:module + peerDeps 保持） |
| `CHANGELOG-v2.md` | 建议 changelog 条目 |
| `diff-v2-vs-deployed.diff` | unified diff（vs 部署工作树基线，96 行） |
| `verify/mock-harness.mjs` | mock agentBus + mock SSE 功能 harness（12 用例，已全绿） |

### diff 摘要（vs 部署工作树基线；共 3 hunks，+约 40 / -2 行）
1. 头注释：v0.2.0 改造说明 + 契约依据（`@@ -1,11 +1,31 @@`）。
2. 新增 `resolveTargetId(to, central)`（`@@ -86,6 +106,39 @@`）：精确 id → 唯一稳定片段 → 歧义/未命中回退中枢，全程 try/catch（agentBus.list 不可用 → 中枢）。
3. `handleEvent` 末尾路由段（`@@ -152,9 +205,18 @@`）：`send(from, target, …)` + `[direct|central]` 日志 + 未命中 ⚠️ 行。**其余 120+ 行零改动**。

---

## 3. 验证方案（未改部署；分三档，越往后越接近真机）

### 档 1 ✅ 已完成：沙箱 mock 功能验证（真实 lib/index.js 全链路）
`node verify/mock-harness.mjs` —— stub `global.fetch`（SSE 流）+ stub `agentBus{list,send}`，加载**真实模块**并跑真实 `apply → connect → SSE 解析 → 守卫 → resolveTargetId → send`。12/12 通过：无 to / coordinator / 中枢完整 id → 中枢；精确 id / 稳定片段 → 定向老登；未知 id / 歧义片段 → 回退中枢；非本节点前缀不注入；自回声跳过；coordinator×mac-mini 跳过（含定向）；collab+定向生效；同 key 去重。日志文件 `verify/test-central-inbox.log` 实证 ⚠️ 回退行与 `[direct] delivered` 行。

### 档 2（建议，只读不部署）：对真实 SSE 的黑盒观察
以独立进程跑本副本（`CENTRAL_INBOX_LOG` 指到测试文件、agentBus 为**记录型 stub 不真发**、SSE 连真实 8803）：
- 普通星台消息（无 to）→ 日志应显示 `[central]`；让用户经星台/curl 发一条 `to=<老登 session id>` 的卡到 `notes/mac-mini/mobile-inbox/`（写卡是 PUT，本机安全）→ 日志应显示 `[direct] …session-aa528267…` 且**无人被唤醒**（stub 不投递）。
- 验证真实负载形状（value 嵌套、字段名）与 resolver 的兼容性；跑 1-2 分钟即可。
- 注意：事件桥只在有新 key 写入选定前缀时推送，需配合写一条测试卡；结束后清理测试卡（黑板 PUT 删除或留档均可，属 notes/mac-mini/ 测试命名空间）。

### 档 3（部署执行，需另行审批 + 重启窗口）
1. 用本副本 `lib/index.js` 替换 `~/dsh-plugin-central-inbox/lib/index.js`（link 目标即部署代码），或把 profile 的 link 整体切到本目录（更干净，可整包回滚）。
2. 重启宿主（CLD）或 cordis 热载插件行；确认 `central-inbox.log` 启动行正常。
3. 回归 A2：星台不选会话发消息 → 注入星桥中枢（日志 `[central]` + `delivered`）。
4. 验收 A1：星台选「老登」发消息 → 日志 `[direct] …aa528267… delivered`，老登会话下一轮可见「看黑板 <key>」并可按 P2 回报协议写回（回报通道为后续项，先观察其 agent_thread 可达性）。
5. 版本化：按 dsh-tools 流程 bump 0.2.0 + CHANGELOG + tag（本包已备 CHANGELOG-v2.md）。

### 验证替代：直接用本机真实中枢做「宿主内测试」
因本轮是 shared 部署改造且 J37 要求副本先行，**不建议**在宿主当前实例上直接热载测试（改工作树 = 改部署）。若后续审批放行，最小侵入做法是档 3；若只想确认「send 到老登会不会被拒」，档 2 的 stub 已能回答「不会拒，只有 delivered/queued 两态」——真正的队列/送达语义证据来自 agent-bus 源码与历史日志，无需真发。

---

## 4. 风险清单（如实评估）

| # | 风险 | 评估与对策 |
|---|---|---|
| 1 | **list() 只含在线会话**：`agentBus.list()` 返回的是 agentsSvc 已加载会话（实测 20 个在线；agent-bus.json profiles 52 个含离线）。星台切到**离线**会话时 v2 解析不到 → 回退中枢（协调者收「看黑板」后自行决定是否转发/唤醒）。**不会拒、不会 queued 积压**（因为未命中就不 send）。 |
| 2 | **send 到离线/未知 id 会静默 queued 而非报错**：契约实证（L1096-1120）。若未来放开「离线也定向」，必须改用 agent_wake/resume 语义，否则消息永久滞留队列（历史 mbp-bus 教训）。v2 已通过先查 list() 规避。 |
| 3 | **歧义/片段误匹配**：`session-` 之类短片段会命中多个 → v2 判歧义回退中枢并 ⚠️ 告警，不猜测。星桥侧应只传完整 id 或 8+ 位稳定段。 |
| 4 | **跨会话唤醒成本**：定向注入 = 目标会话被唤醒消费一轮（token/上下文）。星台高频消息将不再只压在中枢一个会话，而是分散到各目标会话——总量可能上升；建议星台 UI 保持「选会话才定向」默认中枢。 |
| 5 | **中枢失去定向消息的可见性**：to 命中后消息不再进中枢上下文。若需协调者留痕/审计，后续可加「定向同时 CC 中枢」开关（双注入，成本翻倍，默认关）。 |
| 6 | **value.to 信任面**：黑板可写者即可指定注入目标（与现状「可写者即可注入中枢」同信任级，未扩大本质暴露面，但目标选择更广）。星台桥 P1 已规划会话白名单，建议保留。 |
| 7 | **coordinator×mac-mini 守卫对定向也生效**：from='coordinator' 的卡即使带 to 也不注入（测试 10 实证）。若未来协调者需要主动定向派发，需单独放开（改守卫语义，本期不动）。 |
| 8 | **同 key 重复注入偶发**（观测证据）：生产日志 2026-09-03T17:52:28.720/.734 同一 mobile-inbox key 被注入两次（乱序重投/多实例）。`lastInjected` 单 key 记忆拦不住乱序重投；agentBus 侧去重键含 thread（每次新线程）也不兜底。v2 **保持原逻辑**，此项列为后续可选加固（LRU 多 key 记忆），不在本期扩大改动面。 |
| 9 | **基线漂移**：部署基线含未提交改动（假活检测/抖动）；v2 diff 以工作树为准。上线前先 `git commit` 基线或确认基线不变，否则 diff 会失真。 |
| 10 | **部署重启窗口**：插件经 profile bundle 装载，改 link 目标需重启宿主才生效；受控重启需协调者发起（agent_restart 流程）。 |
| 11 | **版本号错位**：git tag 已到 v0.1.10 但 package.json 仍 0.1.6（版本管理以 tag 为准的历史偏差）；本期建议直接升 0.2.0（feat），CHANGELOG 已备。 |

---

## 5. 关键证据索引
- 部署代码：`~/dsh-plugin-central-inbox/lib/index.js`（v0.1.10+未提交改动，164 行）
- agentBus 契约：`~/dsh-plugin-agent-bus/lib/index.js`（v1.5.3，1627 行）：provide L1617 / sendMessage L1096 / deliver L353 / deliverViaBlackboard L324 / agentList L1172 / flushQueue L1077 / dedup L254-271
- 架构文档：`~/dsh-collab/docs/agent-bus-principles.md`、`~/dsh-collab/sb-mobile/session-switch-arch-v1.md`（P2 四勾选）、`iteration-plan-v1.md`
- 现网卡样本：黑板 GET `notes/mac-mini/mobile-inbox/1788460243394`、`notes/mac-mini/mobile-reply/latest-mbp`
- 运行时日志：`~/.dsh/central-inbox.log`
- 沙箱产物：`~/dsh-collab/sb-mobile/central-inbox-v2/`（本目录）
