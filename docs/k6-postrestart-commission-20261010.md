# K6 接线 · 重启后收口任务书（任命新会话执行）

> **下达**：星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4` · 2026-10-10T07:2x+08:00
> **性质**：**自足任务书** —— 执行方**不需要读下达方的对话记录**，读本文件即可开工（这是本文件存在的全部意义）
> **上游**：本任务源自一次**审查位复核**，其完整证据在 `notes/mac-mini/k6-wiring-review-starbridge`（黑板卡，双板）
> **前置成果**：`session-28174037` 已完成 ①②③ 三件接线的**盘面**工作（`lib/wire.js` 新建 + `lib/index.js` 接线 + `lib/meta.js` STAGE 单一来源）

---

## §0 一句话现状（执行方读完这段即可开工）

**接线已在盘面完成且七门全绿，但「在役」未生效** —— 因为**插件在 CLD 启动时载入**（本机 CLD 于 `06:56` 启动），而执行方 `07:08–07:19` 才改盘。
⇒ **在役跑的是旧模块实例**（`version 0.11.1` / `stage K5-r006-7of10` / 无 `wiring` 字段），盘面才是 `0.12.0` / `K6-wiring-3of3`。

**⇒ 因此本任务书的三件事里，T3 必须先等一次 CLD 重启。**

---

## §1 证据基线（下达方已独立复跑，执行方可直接采信为起点）

| 判据 | 结果 | 备注 |
|---|---|---|
| `--budget-check` | ✅ 170/170 `[exit 0]` | sha `aa247227…` |
| `--checkpoint-check` | ✅ **254/254** `[exit 0]` | sha `8d02ace8…` |
| `--recall-check` | ✅ **156/156** `[exit 0]` | sha `1447f67f…` |
| `--contract-check` | ✅ 契约一致 `[exit 0]` | 覆盖 4 模块 |
| `--tool-version` | ✅ `0.12.0` | 与 `package.json` 一致 |

**复跑方式**（`node` 需全路径，PATH 里没有）：
```bash
cd ~/dsh-collab/devices/dsh-plugin-context-survival
/opt/homebrew/bin/node cli.js --budget-check
/opt/homebrew/bin/node cli.js --checkpoint-check
/opt/homebrew/bin/node cli.js --recall-check
/opt/homebrew/bin/node cli.js --contract-check
```

**★ 审查已通过的契约（不必重做，只需不回退）**：
- **① 宿主尺复核**：`lib/index.js:150` `hostMeterRecheck(...)` 必须在 `:164` `session.append(...)` **之前**；判据 `framed >= shadowed` 即拒（**严格小于，相等也拒**）。
- **② 写前并发复查**：`lib/index.js:158-159` `if (cguard2.busy === true) return { action: 'busy_before_write', ... }` —— **真放弃**；两条写入路径（`:418` 手动 / `:544` 自动）都须传 `busy`。
- **③ DEGRADED ≠ MISS**：`lib/ledger.js:131-161` 五条 DEGRADED 分支，`reason` 须明写「本结果**不代表该内容不存在**」。

---

## §2 任务

### T1 · 修工具文案的自相矛盾（**可立即做，无依赖**）

**问题（实测）**：同一个文件里两套工具对 ②③ 的状态说法**直接矛盾**：
| 位置 | 说法 |
|---|---|
| `lib/index.js:348-350`（`csx_status`） | `persist: 'wired'` · `recall: 'wired'` |
| `lib/index.js:411`（`csx_checkpoint`） | `coreStatus: { persistWired: false, recallWired: false }` |
| `lib/index.js:402`（`csx_checkpoint` 描述） | 「**② 落盘 / ③ 召回尚未接线**」 |
| `lib/index.js:13`（文件头） | 「`csx_recall` —— 仍如实报 `implemented:false`（③ 未接线）」 |

**根因（下达方已定位，供参考）**：上游执行方自修的 `--contract-check ④`（「阶段串不得有第二处字面量」）**只钉阶段串**，**不管逐件接线状态**。

**DoD**：
- **正向**：`--contract-check ④` **扩展**为「`coreStatus` 的接线状态（write/persist/recall）也须单一来源」，与 `STAGE`（`lib/meta.js`）同等对待；全库仅一处字面量。
- **负控（必须能红）**：在 `csx_checkpoint` 里故意写死一处 `persistWired: false` ⇒ `--contract-check` **必须变红**；改回 ⇒ 变绿。
- **边界**：`csx_status` / `csx_checkpoint` / `csx_recall` 三者的状态输出**在两条路径下都必须一致**（预演态 / 已接线态）。
- **证据形态**：负控前后两次 `--contract-check` 的**原始输出 + exit code**。
- **沙箱复跑**：在 `devices/dsh-plugin-context-survival` 的**整目录副本**上跑（★ **零接触**：不得改原件；参考既有 `tools/csx-mutation-check.py` 的复制式做法）。

---

### T2 · 把负控 3「投递半」如实标 partial + 落缺口卡（**可立即做，无依赖**）

**背景**：负控 3 的「投递半」原设计要求把「不可缩小」的通知写成 `compaction/notice` 事件。**实测被宿主挡住**：
- `compaction/notice` **不在** `KNOWN_SESSION_EVENT_TYPES`（`dsh-session/lib/index.js:1054+`）；
- `append` 无法打 `ignorable` ⇒ 一旦落盘，持久化读路径**拒绝解释整个会话**（`dsh-session-persistence/lib/index.js:1117-1121`，`SessionFormatUnsupportedError`）；
- **⇒ 照原样实现会让该会话下次加载读不回来**，比不告警严重得多。

**裁决（下达方已裁，不再讨论方案选择）**：**A —— 保持现状，如实标 `partial`（原因＝宿主不可达，非我方未做）**。
★ 理由：备选 B（改用 `user/message` + `surfaceOp:append`）的代价是通知**进模型可见表面、占上下文**，**直接顶 I2「不摘要」与本立项自身** —— 拿病治病；备选 C 方向对但本 build 明确 deferred。
★ 依 **§5.1 三态**（通过 / 不通过 / **未证**）——「未证不得记 closed」就是为这种情况写的。**把「宿主不可达」如实标出来本身就是产出。**

**DoD**：
- 在 `CHANGELOG.md` 与接线条目里写明：**负控 3 投递半 = `partial`，原因＝宿主不可达**（附上述行号证据）。
- 落一张**宿主能力缺口卡**：建议键 `data/registry/host-ignorable-event-gap`，内容含：缺口描述 · 两条行号证据 · 影响面（任何想写非已知类型事件的插件）· 建议路径（宿主侧提供 `ignorable` 注册通道）。
- **负控（必须能红）**：把该 `partial` 标注改回「通过」⇒ **须有判据能发现**（若现无，则**须新增一条**，例如收口脚本检查 `partial` 项必须带 `reason`）。
- **边界**：不得为了让负控 3「看起来通过」而放宽 `KNOWN_SESSION_EVENT_TYPES` 的判据。

---

### T3 · 重启后在役面三项验证（★ **依赖一次 CLD 重启**，由用户执行）

**为什么必须重启**：`--selfcheck --allow-apply` 是**新进程**，必然读到盘上代码 ⇒ **该证据在原理上无法证明在役面**。在役工具仅在 CLD 启动时载入的模块实例里。

**重启后先做归属自证**（不得凭旧认知）：
```bash
hostname; hw.model          # 本机应为 CoreydeMac-mini / Mac16,10
/opt/homebrew/bin/node -e "console.log(process.pid)"   # 记录在役 dsh 进程
```
**验证在役已换版**（★ 这是 T3 的前置判据，不成立则 T3 **整体不通过**）：
- ⛔ **原文（保留，不被删除）**：调 `csx_status` ⇒ 必须返回 `version 0.12.0` · `stage K6-wiring-3of3` · **含 `wiring` 字段**
- ✅ **2026-10-10 重启前裁决（判决位指出 · 执行方修订）**：上条把 `version` **钉成点值 `0.12.0`**，而盘面已推进到 **0.12.12**
  ⇒ **字面执行会把"已正确换版"判成不通过 ⇒ 误回滚**。判据改为：
  1. `csx_status.version` **≥ `0.12.0`**（`0.12.0` = 含三件接线的**首个**版本 ⇒ **钉下限，不钉点值**）；
  2. **且 `csx_status.version` == 盘面 `package.json` 的 `version`**（**同源判据** —— 这才是"在役已换版"的真正含义）；
  3. `stage == K6-wiring-3of3` · **含 `wiring` 字段**（这两条是**稳定标识**，不随版本推进而失真，保持原样）。
- 调 `csx_recall` ⇒ `coreStatus.wired` 必须为 `true`
★ **判据是「调一下」，不是「看工具表」** —— 工具表冻结在会话起点，看过会误判（本线已栽过九轮）。

**三项验证（对齐立项书 §五）**：
| # | 项 | 正向 | 负控/边界 |
|---|---|---|---|
| 1 | **正控 1** | 触发前后 `totalTokens` **严格下降** | 边界：不足阈值 ⇒ 不触发且**如实报** |
| 2 | **负控 3 投递半** | 压不动时**必须告警** | ★ 因 T2 已裁 `partial`，本项只验**能告警**（走已知类型路径），**不验落未知类型事件** |
| 3 | **负控 2 并存半** | 官方压缩在途时**放弃写入**（`busy_before_write`） | 边界：竞态窗口内不得双写 |

**DoD（六者齐备方可记 closed，见 v5 §11）**：正向 ∧ 负控红 ∧ 边界不崩 ∧ 阈值达标 ∧ 沙箱复跑一致 ∧ 无未声明差异。
**证据形态**：三项各自「命令 + 未编辑原始输出 + exit code」，**禁摘要代替**。

---

## §3 边界（不做什么）

- ⛔ **原条款（保留原文，不删除）**：❌ **不改 `enableGuard`** —— 在役面三项全绿**且**经独立审查员裁决之前，它必须是 `false`

### §3.1 2026-10-10 用户授权改写（本条经用户当面授权 · 原作者=星桥起草 · 改写人=执行方 session-28174037）
- **授权**：用户 2026-10-10 在本会话明确裁决「**授权写**」（范围 = A 改配置 + B 留痕 + C 本条改写），
  并选择「**只改配置、重启由用户另定时间**」。
- **改写后的次序**：`用户授权启用（配置就位）` → `用户重启（用户执行；执行方不重启 CLD）`
  → `在役面三项 T3 由独立裁判执行与裁决` → **裁决未通过 ⇒ 回滚 `enableGuard: false` 并重启**。
- **禁令范围的变化（明示，不留暗示）**：`enableGuard` **不再受「裁决前必须为 false」约束**；
  **其余各条一律不变** —— 执行方**不重启 CLD** · 不改 `~/.dsh/profiles/web` · 不删历史留痕 ·
  不用 `all=true` 广播 · 不动 `rules-registry/` 与 v5 锚点 · 不为过门禁削字 · 不改锚点与索引键。
- **生效条件（防误读）**：**配置就位 ≠ 生效** —— 重启前在役仍是旧版、守卫仍未激活。
- **回滚点**：`guard/backups/enableguard-authorize-20261010-192645/cordis.patch.yml.before`
  （`sha256 = ab5da05065f3f031…`）。
- ❌ 不重启 CLD（用户执行）· 不换载体 · 不改 `~/.dsh/profiles/web` · 不删历史留痕 · 不用 `all=true` 广播
- ❌ 不动 `rules-registry/` 与 `docs/distributed-agent-network-governance-plan-v5-*.md`（v5 锚点由星桥维护）
- ❌ 不为过门禁削字
- ❌ **不改锚点与索引键**（信标四件套由星桥维护；如确需，先 `agent_light` 查红灯再申请）

## §4 回滚

- **T1/T2**：改前备份到 `guard/backups/`（★ **不放 `/tmp`**）；T1 的负控实验必须在**整目录副本**上做，**原件永不写**。
- **T3**：纯观测，零写入 ⇒ 无需回滚；若发现异常，**如实报，不回滚数据**。

## §5 交付形态

1. **产出**：T1/T2 的代码与文档改动 + T3 的证据记录
2. **证据**：原始输出 + exit code（禁摘要）；负控**能红**的证据（禁只报正例）
3. **落链**：改动摘要落黑板 `notes/mac-mini/k6-postrestart-t1t2t3`（双板写 + 回读，用 `tools/bb_dualwrite.py`）
4. **回报**：给下达方 `session-e317d6ab` 发 **≤200 字指针**（正文落黑板；`agent_send` 是唤醒通道不是汇报通道，超 200 字会被门禁拒）
5. **★不得自审**：本任务**不构成验收通过**；裁决由**独立审查员**出（见 `docs/v5-and-k6-adjudication-request.md`）

## §6 纪律（违反即失去意义）

- **R030**：不陈述没验证的东西；算不出的记 `absent`，**绝不填 0 冒充通过**。
- **跑的动作必须与要测的行为相同** —— 本条是本任务书的**直接成因**（上游证据形态缺口的同族教训）。
- **一件一验**：T1/T2/T3 **分开报**，不要三件一起做完再报。
- **门不通过就报不通过**，**不调参使其通过**。
- **时间戳一律实读**，且用 RFC 3339 规范形（`±HH:MM` 带冒号）；macOS BSD `date` **不支持 `%:z`**：
  ```bash
  TS="$(date '+%Y-%m-%dT%H:%M:%S')$(date '+%z' | sed 's/\(..\)$/:\1/')"
  ```
