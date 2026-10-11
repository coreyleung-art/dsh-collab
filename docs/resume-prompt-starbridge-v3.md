# 续接提示词 · 星桥治理计划 v? —— 给新会话的前 3 步

> 生成自 `data/registry/continuity-index.json`（state_version=6）· 由 `tools/mk-resume-prompt.py` 渲染
> 锚点：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md`（**唯一权威**，本提示词只是索引，不是规格）

## 前 3 步（照做，别跳）

**① 读锚点** `docs/distributed-agent-network-governance-plan-v6.1-20261011.md` —— **先读**头部 + §0/§1/§14/§15；其余各节**已全部内联**（锚点自足 ⇒ 不必跳转他文件），需要时再展开。
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
- **Q-P**（用户（须授权/须批））：C4 自启动注入是否值得做 —— 它是 M0 唯一缺口，代价是改 CLD preset（须批 + 涉重启窗口）

## 已知缺口（**别当已建成**）

- ★ 2026-10-12 本线新增（台账 D-090…D-099）：① **M4② 论域已裁**（用户 2026-10-12：端口 + 守护进程 + 黑板命名空间）⇒ **L3=44 为正式读数**，且含已知假阳（作业类/系统件类），假阳裁断权已请 `ext`；② **M4③② expired 告警已实现**（`dsh-plugin-agent-bus` 的 `writeExpiredAlert`），★★ **负控未做** ⇒ 依锚点判据不得判 ✅；③ **中枢 8792/8803 对公网开放 + 读路径无鉴权**（P0，`board-central` 通道被 R036 熔断冻结 24h）；④ **本机板 8792 写路径零鉴权**（爆炸半径 ≈108 写者）；⑤ **两圈之分**：★ v6.1 里「门店」出现 **0 次**，而圈二（门店投放）的设计在 `research/cost-governance/`（存在且已验），真门店零部署；⑥ **J44 门本身是假绿**（换词即变 · 候选不可裁 · 旗舰反例不命中）⇒ 已落 **D-097**；⑦ **C4 已注入**（6/6 预设，待新会话验）。★ 台账现 **98 条**（`docs/deviation-ledger-20261011.md`）。
- ★★ **A2 端口固定已生效并复核**：web 端口钉于 61044（实测 pid 94517 监听）；★ **funnel-public 由红转绿 · driftCount 0**；★ 同一根因还治好了 **GUI 卡住**（前端 URL 固定 61044，而端口漂到 60482/55348 ⇒ fetch 全打向无后端端口）
- ★★ **W8.2 落地**：`tools/xdom-mail.py` 的跨域邮箱开始携带 CAHAC §3 信封（**10/10 字段**）；★ 验收面 **面 C · 跨域邮箱** 已加进信封尺（v1.1.0）—— ★ 加之前该落地**不可验证**（原四面无一含 `notes/xdom/log/`）

## 纪律（违反即失去意义）

- **R030**：不陈述没验证的东西；算不出的记 `absent`，**绝不填 0 冒充通过**。
- **closure 三要素**：DoD（含边界+负控）· evidence（可解指针）· **verifier（第三方，禁自证）**。
- **半修清单**：开关装上 ≠ 机制生效 ≠ 结果可控；**不可逆动作（重启/改 profile/载体换）先登记后执行**。
<!-- generated from state_version=6; anchor_sha256=bf5a4e6b76fdedeb… -->
