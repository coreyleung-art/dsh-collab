# Q-K 目标（blocked）归档快照 —— 目标位让渡给 v6.1 主线

> **快照时刻**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **原因**：用户指令「设置目标」指向 **v6.1 锚点主线**；DSH 同一会话只允许一个长期目标 ⇒ 本目标归档后让渡。
> ★ **本件是快照，不是裁定**；★ 本件**不宣布任何事项已闭合**；★ 逐条核对表仍在 `docs/qk-goal-objective-checklist.md`（权威）。

## 已归档目标（原文照录）

- **goal_id**：`goal-6b352bc9-6936-418d-82a9-26b37ddb6291`
- **revision**：4 · **phase**：`blocked` · **roundsStarted**：17 / maxGoalRounds 20 · **activation**：disarmed
- **objective**（逐字）：
  > 【优先目标 · 2026-10-10 用户重设】推进 Q-K「上下文存活后端」至闭环——治 P26 机制二（官方压缩器摘要模板地板 > 被遮内容，无配置解），做非摘要、有界、保证能缩小的检查点后端，与官方 compaction-basic 并存（seam b，不接管 ctx.compaction）。三段：(A) **K3** —— 非摘要检查点产出（`<context_handoff v1 seq-range=A-B>`：目标/阶段/todo/最近人类请求逐字/notes/省略账带 seq 指针/召回指南）+ 有界丢弃阶梯（三级降级·保证每步都减）+ 表面替换 + 并发护栏（接 assertNoActiveCompaction 真判据，读 session.events 的 unmatchedCompactionStart）；`canShrink` 门必须先于 `enableGuard` 被证明，期间 enableGuard 保持 false；(B) **K4+K5** —— csx_recall 工具 + 事件流落盘，然后立项书 §5 正控 1–4 与负控 1–3 全跑通（负控 1 = 把活跃窗口压到摘要地板以下仍能缩小，立论所系）+ R006 十项齐活，每条判据附可复跑命令；(C) **K6 就绪** —— 挂载点选定（待用户答 Q-K6）+ 前置门全绿 + 回滚点就位，挂载动作本身交用户执行（不可逆）。每完成一个里程碑同步更新 docs/context-survival-tracker.md §5 与 data/registry/continuity-index 的 Q-K 条目（两处不许漂，写完独立回读比 payload sha，不信 bb_dualwrite 的 values_equal）。禁令不变：不重启 CLD · 不改 profile · 不换载体 · 不复活首任 · 不删历史留痕 · 不用 all=true 广播 · 不为过门禁削字 · 不执行 lib/index.js 的 apply()（除单独授权）。
- **blockedReason**（逐字）：
  > 同一阻塞条件自第 5 轮起持续 13 轮，且离线工作已穷尽。具体阻塞：剩余全部工作需二选一 —— (a) **解除「不执行 lib/index.js 的 apply()（除单独授权）」禁令的授权**，覆盖五处：正控 1（守卫触发后 totalTokens 严格下降）· 负控 2（与官方 compaction-basic 并存不打架）· 负控 3 投递半（通知真写进事件流）· K3 真写入（session.append(..., {surfaceOp})）· K4 工具出口（recall() 接到 csx_recall 工具）；或 (b) **回答 Q-K6 挂载点**（三选项已核实现状：需先答 Q-K6，推荐 (b) 留 devices/ 写绝对路径 link）。判据：27 条逐条核对表（docs/qk-goal-objective-checklist.md）实测 ✅17 · ◐5 · ⏸1 · ⊘3，剩余 ◐/⏸ **全部**指向上述两件，无第三类。工作区已处于「一次授权即可解锁全部」的干净状态：插件七门 exit 0 · node --test 36/36 · 五套治理判据（变异/常量变异/canfail/漂移/禁令）全 exit 0 · 未挂载 · enableGuard=false · 回滚点 guard/backups/k6-rollback-point-20261010-044155 在位 · 前置门清单 docs/k6-preflight-and-rollback.md 已交付。

## 让渡说明（★ 用户已勘正的事实）

★ 用户 2026-10-11 明确：**K6 上下文守卫只是主线的一条分支线**。
⇒ 本目标（Q-K/K6）**不是**主线本身；它并入 v6.1 主线目标下的**分支工作流**继续跟踪。
⇒ 它的**两项待决**（(a) 授权执行 `apply()` · (b) 答 Q-K6 挂载点）**仍在等用户**，不因目标让渡而消失。
⇒ ★ **无工作被废弃**：27 条核对表、前置门清单、回滚点、插件七门状态**全部保持在位**。
