# 续接提示词 · 星桥治理计划 v7 —— 给新会话的前 3 步

> 生成自 `data/registry/continuity-index.json`（state_version=7）· 由 `tools/mk-resume-prompt.py` 渲染
> 锚点：`docs/distributed-agent-network-governance-plan-v7-20261012.md`（**唯一权威**，本提示词只是索引，不是规格）

## 前 3 步（照做，别跳）

**① 读锚点** `docs/distributed-agent-network-governance-plan-v7-20261012.md` —— **先读**头部 + §0/§1/§14/§15；其余各节**已全部内联**（锚点自足 ⇒ 不必跳转他文件），需要时再展开。
**② 读索引** 黑板 `data/registry/continuity-index`（本地副本 `data/registry/continuity-index.json`），比对 `state_version` 与锚点一致。
**③ 跑反遗忘校验** `python3 tools/beacon-check.py --net` —— 必须 exit 0 才继续；有红先报，别绕。（`--net` 抽检黑板指针；不加会显示 `SKIP`——**未抽检 ≠ 通过，别读成全绿**。）

## 复述题（第 3 步之后立刻回答，答完再动手）

- **当前 wave = `Wave S`**：门（沙箱模拟框架 / 信息包模板 / 独立审查流程 / 官方校对门 / G-CR 校验脚本）
  - 现状：★ P27 同步（2026-10-10，v4→v5）：S1–S5 五项 + 增① 身份声称门 + 增② 自指破坏门（+R059）**工具面已交付**（10-10 03:31，见 docs/wave-s-toolchain-delivery-v1.md；七件实体在 tools/ 已逐一核对字节数），全部走完 R006 §5 三步。★ **但七件均为作者自测，缺独立 verifier** ⇒ 整体 in_flight，**不得记 closed**。　★ 与 `state-registry.json` 记 `blocked` 不一致（P27 族；见分工书 §B6）。
- **下一步 = `C4-b`**：自启动注入的【生效验证】（新会话实测 ≤5 分钟恢复认知）

## 上一会话是怎么死的（**别重蹈**）

- `session-fa1f9150-c949-401f-ba8c-d265f6221676` ⇒ **bricked**（2026-10-09T05:39:52+08:00）
- 因：CONTEXT_WINDOW_EXCEEDED（超 3242 token，全来自 completion 预留）+ compaction 永久失效（摘要开销 3435/3450 ≥ 被遮内容 2466） ｜ 一手证据 + 门建议：`docs/compaction-lowerbound-crash-20261009.md`

## 要你（用户）拍板的（阻塞在决策，不阻塞在能力）

- **Q-O**（用户（须授权/须批））：Wave S 七件门的独立 verifier 由谁担任 —— 候选：守灯 9910d4b2 / 独立复核员 4d0e75cf / 司库 2a15e6b1（均离线）

## 已知缺口（**别当已建成**）

- ★ 2026-10-12 ★★★ **【v7 建立 · 锚点切换】**：★ 五段流程走完 —— **大纲 → 调研（9 代理 55 篇 15462 行）→ 撰写（5 代理 4679 行）→ 审查（3 份 · V2 两次皆空）→ 合并**。★★★ **v7 更正账 22 条 + 本线自己的错 5 条**（★ 全部已独立复现）。★★ **跨模块同形诊断**：★ 本机的缺陷不是「没做」，而是【**做了而没有验收**】—— **有告警没有读者 · 有判据没有负控 · 有自证没有真的坏样本 · 有计划没有与在役对齐**。★★★ **最重的三条**：★ ① **`gcr-gate --selftest` 的 5 条「负例」是恒真字面量**（源码逐字 `0 == 0`）⇒ 可信负控 = 0；★ ② **§3.1「SQLite/WAL 为当前最优」而在役黑板 `.db`=0，实为 11 个 JSONL + 106 MB 快照** ⇒ 在役恰是它标「已废弃」那行；★ ③ **本线建的读者三态「读不到 ⇒ 不可判」结构上不可达**（不存在的段名也返回 200 + 空列表）。★ **锚点切换**：v6.1 保留未改（sha256 `bf5a4e6b…`），state_version **6 → 7**。
- ★ 2026-10-12 **【v7 调研阶段完成 · 8 个代理 · 15,462 行】—— 调研推翻 v6.1 登记 16 处**：★ 交付目录 `research/v7-{health,negctl,caliber,ccep,wbs,milestone-crash,open-questions,slo-acceptance}/`（★ 共 55 篇 · 15462 行 · 5 个 evidence 目录 32 项）。★★★ **推翻清单（★ 全部现测 + 本线独立复现）**：① **M0「唯一缺口」已补** —— C4 自启动注入 **6/6 预设已落成**（10-12 03:08）★ 无文档记下；② **§7.9「预防门汇总」是【空节】**；③ **「25 类零复发」无分母** —— 17 门中 **9 门恒 N-A** ⇒ 真分母 8；④ **`gcr-gate` 现测 exit=1** ⇒「G-CR 门全绿」字面不成立；⑤ **P27 四层全已修补**（v6.1 记「成立」）；⑥ **P28 ③⑥ 已修**；⑦ **W6.6 称「:467 已修」而现测该行仍在打印「回退注入中枢」**；⑧ **本线「自指闭环」推断被证伪**（23 张自指卡 21 张到达）；⑨ **`/health` 真读者 = 0**（本线曾记 ≥3）；⑩ **§15 未决问题 17 条**（本线清点件只 3 条）；⑪ **§18 ❌ 5 实为 1 条**（同行 5 字形）；⑫ **留证 9/9 → 12 条 · 24h 内 0/12**；⑬ **闭环 9→10 项 6 closed**；⑭ **真积压 103→111**；⑮ **会话目录 1.2G→1.4G**；⑯ **`updated_at 落未来` 已不成立**。★★★★★ **结构性命中（★ 最重）**：★ 全机 CLD/dsh 进程 · 全部会话文件 · `whoami` **全为 coreyleung** ⇒ **「换会话审」买到【认知独立性】、买不到【主体独立性】**（= SLSA 逐字形态「Single actor controls multiple accounts」）。★ 实证：`review-tracker` 唯一历史登记**因 `executor==verifier` 被撤**（R046 真红过）；§5.5 三位候选 verifier **均有会话但此刻全部离线**。★★ **同一份数据「一绿一黄」三处（★ v7 必须【替换】旧尺不得追加）**：`beacon-check` 判 verifier 字段齐备 PASS 而实为 **6/6 占位符**；判 `dod.full_table` 缺席已声明 PASS（★ 而它本就缺席）；`official-ref-gate` **不带 `--target` 打印 GO rc=0**。★★ **判据对真失效零判别力两处（★ 本线已独立复现）**：`bus-8791` 的 `body.includes("ok")`（401/403/500 全判绿）· `tailscale-direct` 的 `l.includes(peer) && l.includes('active')`（离线行同时含 active 与 offline）。★★ **`gcr-gate` 非确定性**：相隔 6 分钟给出 PASS 6·FAIL 2 与 PASS 7·FAIL 1。★★ **本线今晚自曝事故**：`io.open(p,"w")` 先截断 + 写入失败 ⇒ **台账 634 KB 被清空**，已从 git 恢复（★ 零丢失，救它的是 auto-snapshot）；已建 `atomic_append`（临时文件 + 三道保险 + 原子替换）⇒ **首次运行即真拦一次**。
- ★ 2026-10-12 **【用户裁定「归档」已落地】**：★ 7 条 `drift-delivery-failure` 已归档（★ **标记不删**）：① 原卡加 `_archived_at`/`_archived_by`/`_archived_note`（★ 7/7 · 双板均 200）；② 写归档汇总卡 `data/ops/_archived/drift-delivery-failure/<ts>`（★ **保留全部原 payload**）；③ **读者改为跳过带 `_archived_at` 的卡**，且**不隐藏已归档数**。★★★★ **改后读数：【PASS 26 · FAIL 0 · PEND 1】** —— ★ **PASS 25→26（新检查项计入）· FAIL 1→0**。★★★ **⇒ 这是一个【能红能绿】的完整演示**：加检查→红（抓到 7 条）→ 处理→绿，且**没删任何数据** ⇒ **该检查既不是恒真也不是恒假，它真的跟着事实变。**★ 为何标记不删：★ 本仓既有先例（agent-bus 对 DLQ 的语义「**可枚举可回放，不删除**」）；★ 而今晚刚有一个反例 —— **D-185 要追查那 4 次失败的【时刻】**，若当时删了就查不到。★ **剩余待办**：★ `drift-heartbeat.failedLegs` 仍无读者（D-185 ②）。

## 纪律（违反即失去意义）

- **R030**：不陈述没验证的东西；算不出的记 `absent`，**绝不填 0 冒充通过**。
- **closure 三要素**：DoD（含边界+负控）· evidence（可解指针）· **verifier（第三方，禁自证）**。
- **半修清单**：开关装上 ≠ 机制生效 ≠ 结果可控；**不可逆动作（重启/改 profile/载体换）先登记后执行**。
<!-- generated from state_version=7; anchor_sha256=1e45b47bb45cc29d… -->
