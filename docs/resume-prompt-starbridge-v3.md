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

## 已知缺口（**别当已建成**）

- ★ 2026-10-12 本线新增第二十四批（D-140）：★★★★ **两插件【同名文件 + 同编号 G1】不同义**（★ 本线在复核 `ext` 问 2 时发现）：★ 对方引 `dsh-plugin-channel-gate/lib/gate.js` 说「G1 只注释无 enforce」，★★ **而原文实在 `dsh-plugin-drift-scan/lib/gate.js:4`** —— ★ 两插件**各有一个 gate.js、各有一个 G1**：★ `channel-gate` 的 G1 =「通道枚举外不可表达」（★ **有 enforce**：`:49-50 throw UNKNOWN_CHANNEL` + `CHANNELS` 已 `Object.freeze`）；★ `drift-scan` 的 G1 =「MATRIX 冻结加载」。★★★ **本质问题比「只有注释」更深**：在正确文件上核 —— `:23 export const MATRIX_SOURCE = 'lib/channel-matrix.json'`（**常量，无 freeze**），而 `:16 export const COMMAND_WHITELIST = Object.freeze({…})` ⇒ ★ **G1 声称冻结的对象（MATRIX）与实际 freeze 的对象（白名单）【不符】** ⇒ ★ 不是「没 enforce」，是 **enforce 在另一个对象上、而声称在这个对象上**。★ 另核：`drift_scan` 自述的仓库根 `lib/channel-matrix.json` **确实不存在**；★ 但 `core.js:14` 用 `path.join(__dirname,…)` ⇒ **解析正确、工具读得到**；★ 错的是 `core.js:183` 的 `matrixSource` 展示名与工具描述。★ **建议**：引插件内文件必带插件名全路径；G 编号宜带插件前缀（`drift:G1` / `gate:G1`）。★ 台账现 **139 条**。
- ★ 2026-10-12 本线新增第二十三批（D-139）：★★★★★ **【上界值】仍被当确切时刻比对**（★ 由 `session-c05b831c` 指出）：★ 本线已立「值不是确切时刻 ⇒ 不参与分钟级比对」，通配位遵守了；★★ 而 `ledger-true-times.json` 里的 **69 条 `time_exact:False`（commit_upper_bound）** 的真值**同样不是确切时刻**⇒ 应同一规则，而 `--audit` 既不带该标记、又照算 `delta_min` ⇒ 「D-001 晚 108 分」**不是偏移，是批次延迟**。★ **已修**：`audit()` 新增 `_exact_map()` 读 `time_exact`；上界值不参与偏移、改标 `upper_bound`；输出三类分开；★ 并按其建议新增负控 **③d「上界值不得参与分钟级差」** ⇒ **负控 6/6 → 7/7**。★★★ **修后新读数：比对 118 · 不一致 2 · 不可判（通配）49 · 不参与（上界）67**；★ 不一致 **15 → 2**；★★ **唯一可精确比对的两条 = D-073（早 5 分）· D-074（早 6 分）**，两者 `time_exact=True`。★★ **⇒ 118 条里只有 2 条可精确比对 ⇒ 「台账时刻列失实」的范围需再次收紧。**★ 台账现 **138 条**。
- ★ 2026-10-12 本线新增第二十二批（D-138）：★★★★ **对方【自撤回】上一条（waves[C].updated 陈旧），本线采信并三态处置**：★ 它实查消费点：`beacon-check.py:322-337` 对 waves **只读 `state` 与 `note`**，**`waves[].updated` 一次未被读**⇒ 它那句「下游会读到 10-10」是**凭空加的因果**。★★ 当场反证：`waves[S]` 与 `waves[C]` 此值**同日同秒** ⇒ 该字段呈**批量写入特征**，更可能是「该段最后一次批量同步的时刻」，★ 若如此 **10-10 就是对的**。★★★ **本线处置（三态）**：★ **保留本线改动**（确实改了该段 note）★ **但标「该字段语义【不可判】」**（全仓无消费点 ⇒ 无权威定义；两种读法都说得通）★ **并记「改前 S/C 同秒 ⇒ 批量特征已被本线破坏」**。★ **它的一般教训本线采纳**：★ **凡报「字段 A 与 B 不一致」，须先证明 A【被当作 B 的判据消费】**；★ 否则「我没查到它被用」会被说成「它错了」。★ 本线在 D-137 引用其因果而未独立核 ⇒ **同型已认领**。★ 台账现 **137 条**。

## 纪律（违反即失去意义）

- **R030**：不陈述没验证的东西；算不出的记 `absent`，**绝不填 0 冒充通过**。
- **closure 三要素**：DoD（含边界+负控）· evidence（可解指针）· **verifier（第三方，禁自证）**。
- **半修清单**：开关装上 ≠ 机制生效 ≠ 结果可控；**不可逆动作（重启/改 profile/载体换）先登记后执行**。
<!-- generated from state_version=6; anchor_sha256=bf5a4e6b76fdedeb… -->
