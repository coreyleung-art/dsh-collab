# Changelog 建议条目 · dsh-plugin-central-inbox v0.2.0（未部署，沙箱副本）

## [0.2.0] - 2026-09-04（建议；对应 v9.7 星台会话切换 P2）

### 新增：黑板卡定向注入（value.to 路由）
- **能力**：黑板事件卡带 `value.to`（目标会话 id）时，若命中本机 agentBus.list() 中某**在线**会话（精确 id 或唯一稳定片段，如 `fa1f9150`/`aa528267`），则 `agentBus.send` **注入该会话**而非总注入中枢；to 缺失/为空/`coordinator`/`central`/未命中/歧义 → 回退注入中枢（现逻辑，回归不破）。
- **用途**：星台 App 设备内会话切换（直接跟「老登/明鉴…」会话对话，不经星桥转发）。
- **防回声/去重保留**：`value.from === NODE_ID` 自回声跳过、`value.from==='coordinator' && mac-mini` 中枢不自注入、`lastInjected` 同 key 去重、文本仍为 `'看黑板 <key>'`、threadId 仍为空（每卡新线程）。
- **日志增强**：注入行带 `[direct]`/`[central]` 标记 + 目标会话 id；显式 to 未命中时追加 `⚠️ to=… 未命中本机在线会话（reason）→ 回退中枢` 告警行。
- **契约依据**（源码实读 dsh-plugin-agent-bus v1.5.3 lib/index.js）：`agentBus.list()` = `agentsSvc.list()` 映射 `{id,status,locks,waiting}`（仅在线会话）；`agentBus.send` = `sendMessage`，目标在线→`followup` 注入→`{status:'delivered'}`，目标离线/不存在→不抛错、静默入库 `{status:'queued',targetLive:false}`（先查存在性防永久 queued 积压）。

### 验证（沙箱，未部署）
- ESM 模块加载 OK（exports name/inject/apply）；mock-agentBus + mock SSE 功能 harness 12/12 通过（verify/mock-harness.mjs）：无 to/coordinator/中枢 id→中枢、精确 id/稳定片段→定向、未知/歧义→回退中枢、前缀过滤、防回声、coordinator×mac-mini、collab+定向、同 key 去重。

### 说明
- 基线 = 部署工作树 `~/dsh-plugin-central-inbox/lib/index.js`（v0.1.10 提交 + 未提交 45s 假活检测/重连抖动）——非 datasets 里过时的 v0.1.4 bundle（其缺 ESM import，直接作为 v2 基底会重蹈 v0.1.6 加载即崩）。
- `cordis.patch.yml` 无需改动（insert 行同 v0.1.x，配置仍走环境变量 CENTRAL_AGENT/DSH_NODE_ID/CENTRAL_INBOX_SSE/CENTRAL_INBOX_LOG/BLACKBOARD_TOKEN）。
- 范围外（P2 后续项）：注入后回报 `notes/<node>/mobile-reply/latest-<session>` 写回（星台按会话轮询）未包含在本改造中。
