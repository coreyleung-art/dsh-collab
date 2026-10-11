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

- ★ 2026-10-12 本线新增第六批（D-119）：★★ **P29 五处【最终状态】**：★ 一 C7 遮蔽扫描 **✅ 已修**（★ `~/dsh-plugin-guard/lib/index.js:358` 逐字「`0.1.2（2026-10-11 星桥第二任）治空转绿」；★ 分母仍 0 但判据已三态化 `ok=null`+`degenerate`）·★ 二 drift 跨机 **✅ 已修**· ★ 三 有界重试 **❌ 仍成立**（★ 1/3=13 · 2/3=0 · 3/3=0）·★ 四 `/health` 空壳 **❌ 仍成立**（★ `{"list":{},"total":0}`）· ★ 五 零通道 **部分**（★ `cld_health_check` 不再报全绿：`all_ok:false`+`unverified:1`；★ 但仍无通道路检查）。★★★ **反推出一条可复用规律：【一个判据要么三态，要么一定会假绿】**（★ 已修的两处均为判据三态化；★ 仍成立的两处均为二值）。★ 台账现 **118 条**。
- ★ 2026-10-12 本线新增第五批（D-116…D-118）：① **M4③② 负控【已做】**：★ 函数层 **4/4 全绿**（★ 按行号提取函数体 + 注入假依赖：★ 键形/`PUT`/`count`/`sample截断`/降级不抛）；★ 脚本 `scripts/negctl-writeExpiredAlert.mjs`；★★ **但端到端待插件重载**（★ 实测两个 CLD 进程均**早于**改动）；② **P29 假绿族§7.11 核实**：★ 一 C7 遮蔽扫描 **❌ 仍成立**（★ 逐级复现 106→101→5→0；★★ **二阶故障：事故把检测它的仪器也弄坏了**）；★ 二 drift 跨机 **✅ 已修**（★ :207 失败侧有日志 · :108 `failedLegs` · :208 回读一致仅两腿成功时判）；★ 3/5/4 未核；★★ **两次「已修」均为【锚点记录过时】**。★ 台账现 **118 条**。
- ★ 2026-10-12 本线新增第四批（D-113…D-115）：① **P28 六项【首次核清】**：★ **1 ✅ · 2 部分 · 3 ❌**—―★ ⑤失实日志 **已修**（route.js:48 明写【不再静默回退】；锚点记录已过时）；★ ⑥双投去重 **仍成立**（dedupKey 粒度=from+to+整条内容指纹）；★ ③④ **仍成立**；★ ①② 部分推进；② **地层地图已出**：`docs/repo-strata-map-20261012.md`—―★★ **治理所依据的 docs/ 是信息量最小的地层**；③ **SystemGraph GUI `/api/blueprints`**：★ 实测**已恢复**（HTTP=200），卡片 03:37:41 的 `Fetch is aborted` 判为瞬时错误。★ 台账现 **114 条**。

## 纪律（违反即失去意义）

- **R030**：不陈述没验证的东西；算不出的记 `absent`，**绝不填 0 冒充通过**。
- **closure 三要素**：DoD（含边界+负控）· evidence（可解指针）· **verifier（第三方，禁自证）**。
- **半修清单**：开关装上 ≠ 机制生效 ≠ 结果可控；**不可逆动作（重启/改 profile/载体换）先登记后执行**。
<!-- generated from state_version=6; anchor_sha256=bf5a4e6b76fdedeb… -->
