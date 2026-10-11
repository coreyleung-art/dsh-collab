# 独立裁决请求书 · 两件（v5 锚点成立性 · K6 接线的 closed 资格）

> **请求方**：星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4`（★ **方案与锚点均由本人起草 ⇒ 按 S3「不可自审」不得由本人裁定**）
> **致**：独立审查员（首选 `session-4d0e75cf` —— 其档案自述「**未参与本线建构 ⇒ 无 S3 冲突，理论上最干净**」；备选 `session-1ffded95` 裁判，但其在 P26 取证中参与建构，**是否可裁整体请其自答**）
> **性质**：**自足信息包** —— 受委托方读本文件即可裁决，无需读请求方对话（本文件按锚点 §5.3 的 **14 项规格**填写）
> **文本纪律**：本文件只提供「**声明**」与「**可复跑的取数方式**」。**凡请求方未独立验过的，一律标 `未测`** —— 不得把转述当证据（R030）。

---

## 1 · 目标与范围
对**两件**分别出**三态判定**（通过 / 不通过 / **未证**，见 §5.1）：

| 件 | 裁什么 |
|---|---|
| **甲 · v5 锚点** | `docs/distributed-agent-network-governance-plan-v5-20261010.md` 作为**计划级锚点基线**是否**成立**（`state_version=4`） |
| **乙 · K6 接线** | `dsh-plugin-context-survival` 的 ①写入 / ②落盘 / ③召回 三件接线是否具备 **`closed_with_evidence`** 资格 |

**范围外**：不裁业务方向（Q-A…Q-Q 的选项取舍）· 不裁用户保留事项 · **不代改任何文件**（只读取证）。

---

## 2 · 声明面（请求方**声称**做到的）

**甲（v5）**
- 自 v4 升版：`state_version 3→4`；**八条能力/状态改判**（见 v5 §0.0 六条 + §0.1/§0.2/§16 三条内联更正）
- **自足性**：v4 的 §1/§2/§3/§5/§6/§7.1–7.7/§8/§9/§11/§13 已**全文内联**，不复用指针（v5 §17.6 立规）
- 四件同步完成：锚点 / 索引 / 续接提示词 / 版本指针
- 新增 **P27「判据失明族」** 与 **G-CR18 信标自检覆盖门**（四判据）
- **未改**索引的语义判定（仅作升版所需最小字段更新 + waves/items 两段一致化，依 §4.6 规程）

**乙（K6 接线）**
- 盘面 `version 0.12.0` · `STAGE = 'K6-wiring-3of3'`（单一来源 `lib/meta.js`）· 三件 `wiring` 均 `'wired'`
- 四项格式契约审查**已由请求方执行**，结论：① ② ③ 盘面**通过**；**④ 在役面不通过**
- 负控 3「投递半」**被宿主挡住**，请求方已裁 **A = 如实标 `partial`**（理由见 §11 提问 3）

---

## 3 · 未测面（★ R046 必填 —— 请求方**明确没有验**的）

1. **乙的在役面**：CLD 在役模块仍是 `0.11.1` / `K5`。**在役工具能否正确执行三件接线，请求方未验，且当前无法验**（需重启）。
2. **乙的 T1/T2 修复后状态**：任务书 `docs/k6-postrestart-commission-20261010.md` 的 T1/T2 **尚未开工** ⇒ 其 DoD 是否可达 `未测`。
3. **甲的内容正确性**：请求方只验了**形式**（sha/state_version/两段一致/时间戳规范形/verifier 在位）。**v5 正文的事实主张（如 §0.2 七件工具的限度描述）请求方未逐条回原件复核**。
4. **甲的第三方复核**：`verifier: 待第三方复核` 是**自陈的缺口**，非已完成事项。
5. **Wave S 七件门工具**：请求方**读的是交付说明**，未逐件实跑其自证矩阵。★ 交付说明内部对 `sandbox-script.py` 给出 `--selfcheck 5/5` 与 `--selftest 4/4` 两个数字，请求方判定「应为不同检查」但**未实跑核实** ⇒ 记 `未测`。
6. **宿主能力缺口的影响面**：`compaction/notice` 不可落盘的**全量影响**（有多少插件想写非已知类型事件）**未测**。

---

## 4 · 全部产物路径 + 版本 + sha256 + 生成时刻

**样本时点**：`2026-10-10T07:20:00+08:00`（★ 一律 `date` 实读，RFC 3339 规范形 `±HH:MM`）

| # | 路径 | 版本 | sha256（前 16） | 字节 |
|---|---|---|---|---|
| 1 | `docs/distributed-agent-network-governance-plan-v5-20261010.md` | `state_version=4` | `3c92e2a602978d9c` | 57,487 |
| 2 | `docs/resume-prompt-starbridge-v3.md` | 40 行 | `dd315bbec4a53368` | 3,375 |
| 3 | `docs/k6-postrestart-commission-20261010.md` | v1 | `4985660d1dc32ec7` | 10,124 |
| 4 | 索引键 `data/registry/continuity-index`（双板） | `state_version=4` | 索引内 `anchor_sha256` **应为** #1 的全值 | — |
| 5 | `devices/dsh-plugin-context-survival/package.json` | **0.12.0** | `b251b739a416b1fb` | 1,577 |
| 6 | `…/lib/wire.js` | — | `eda41842fc191165` | 18,323 |
| 7 | `…/lib/index.js` | — | `c44efeaa94c0ae22` | 33,393 |
| 8 | `…/lib/meta.js` | `STAGE='K6-wiring-3of3'` | `89b32b0a555430c4` | 3,303 |

**★ 第 4 项的完整 sha256（索引 `anchor_sha256`）**：`3c92e2a602978d9c1f083302bef849dcaaa1828cbf9337ee48b3bbad80316b55`

**上游审查记录**：黑板卡 `notes/mac-mini/k6-wiring-review-starbridge`（双板；含 P1/P2/P3 完整证据）
**上游执行方回报**：黑板卡 `notes/mac-mini/k6-wiring-1-2-3-complete`

---

## 5 · 自包含复跑命令（★ 禁引用 `/tmp` 等易失路径；`node` 需全路径）

```bash
cd ~/dsh-collab/devices/dsh-plugin-context-survival
N=/opt/homebrew/bin/node

# —— 乙：盘面五判据（请求方实测全绿，见 §7）——
$N cli.js --budget-check        # 期望 170/170  exit 0
$N cli.js --checkpoint-check    # 期望 254/254  exit 0
$N cli.js --recall-check        # 期望 156/156  exit 0
$N cli.js --contract-check      # 期望 契约一致  exit 0
$N cli.js --tool-version        # 期望 0.12.0，与 package.json 一致

# —— 甲：信标自检（★ 必须 --net，不加会显示 SKIP；未抽检 ≠ 通过）——
cd ~/dsh-collab && python3 tools/beacon-check.py --net    # 期望 全绿 0 WARN 0 SKIP exit 0

# —— 甲：G-CR18 四判据（请求方手工核，无现成脚本；下方给出取数方式）——
python3 - <<'PY'
import json,urllib.request,hashlib,datetime as dt
loc=json.load(open('data/registry/continuity-index.json',encoding='utf-8'))
bd=json.load(urllib.request.urlopen('http://127.0.0.1:8792/data/registry/continuity-index',timeout=8))['value']
c=[w for w in loc['waves'] if w['id']=='C'][0].get('note','')
print('① 两段一致     :', ('C6/C7 已 in_flight' in c) and ('C4 未做' in c))
u=dt.datetime.fromisoformat(loc['updated_at'])
print('② 时间戳合理域 :', u <= dt.datetime.now(u.tzinfo), loc['updated_at'])   # ★ 需 Python≥3.11 或已规范化为 ±HH:MM
print('③ verifier 缺位:', [i['id'] for i in loc['items']
      if i.get('state')=='closed_with_evidence' and not i.get('verifier')])
a=hashlib.sha256(json.dumps(loc,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
b=hashlib.sha256(json.dumps(bd ,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
print('④ 副本==板值   :', a==b)
PY

# —— 在役面（★ 只能在会话内调工具，命令行无法验）——
#   调 csx_status ⇒ 期望 version 0.12.0 / stage K6-wiring-3of3 / 含 wiring 字段
#   调 csx_recall ⇒ 期望 coreStatus.wired == true
#   ★ 判据是「调一下」不是「看工具表」（工具表冻结在会话起点）
```

---

## 6 · 负控结果（能红的证据）

| 项 | 负控 | 结果 |
|---|---|---|
| 乙 · ① 宿主尺复核 | 成帧 ≥ 被遮 ⇒ **必须拒** | ✅ `k3-selftest` W 组 4 条断言（含「相等也拒」）；`lib/wire.js:171` 起五条失败态全拒 |
| 乙 · ② 写前并发复查 | `busy===true` ⇒ **必须放弃** | ✅ `lib/index.js:158-159` 返回 `busy_before_write`（真分支，非注释） |
| 乙 · ③ DEGRADED | 冒充 MISS ⇒ **冒烟必须变红** | ✅ 上游执行方报「DEGRADED 冒充 MISS ⇒ 冒烟变红」（★ **请求方未独立复现此变异**，记 `未测`） |
| 乙 · ④ 文案单一来源 | 写死一处 ⇒ **必须红** | ❌ **当前不成立** —— 正因 ④ 只管阶段串、不管接线状态 ⇒ **T1 待做** |
| 甲 · 信标判据 | 索引两段不一致 / 时间戳在未来 ⇒ **必须红** | ❌ **当前不成立** ⇒ **G-CR18 尚未落成脚本**，仅请求方**手工核** |

★ **如实声明**：**甲侧的负控目前无机械判据**（G-CR18 是**规格**不是**脚本**）。请求方手工核得 ①②④ PASS、③ WARN，但**手工核不是负控能红的证据**。

---

## 7 · 边界用例结果

| 项 | 边界 | 结果（请求方实测） |
|---|---|---|
| 乙 · 盘面五判据 | 干净仓库应全绿 | ✅ 全 `exit 0`，计数 170 / 254 / 156 / 契约一致 / 0.12.0 |
| 甲 · 续接提示词 | ≤40 行（§4.1③） | ✅ 40/40。★ **实测容量约束**：加至 4 条 `urgent` 渲染成 42 行即被生成器**拒绝写盘** ⇒ `urgent` 实际容量 ≈2 |
| 甲 · 时间戳 | 规范形 `±HH:MM` | ✅ 已把索引内 **3 处** `+0800` 规范化为 `+08:00`；★ 成因：请求方 v5 初版公式用 `%z`，**本机 Python 3.9.6 的 `fromisoformat` 抛 ValueError** ⇒ 判据崩在解析处 |
| 甲 · 双源 | 本地副本 vs 板值 | ✅ 现一致（曾实测 **4 字段不一致**，见 §9） |

---

## 8 · 官方规范引用（条款 + 来源）

| 主题 | 来源 | 引用点 |
|---|---|---|
| `defineTool` 契约 | 官方工具 schema 规则（10-06 实测汇总） | **`output.render` 必需**（本插件曾因缺它而 `userRender is not a function`） |
| 插件挂载 | 官方路径 | `dsh.profile.bundles` / `link:` 依赖 / `cordis.patch.yml` insert 三处一致 |
| 压缩判据 | `dsh-compaction-basic/lib/index.js` | `:556` `framedSummaryTokenCount >= shadowedTokenCount` 即拒（**相等也拒** ⇒ P26 机制二本体）；`:28` `BASIC_COMPACT_CONFIG_KEYS` 十把键无一把可改模板/判据 |
| 会话事件类型 | `dsh-session/lib/index.js:1054+` | `compaction/notice` **不在** `KNOWN_SESSION_EVENT_TYPES` |
| 持久化读路径 | `dsh-session-persistence/lib/index.js:1117-1121` | 未知类型事件 ⇒ `SessionFormatUnsupportedError`（**整个会话读不回来**） |
| 等待语义 | 官方 `defensive-patterns.md` L17 | 「**若被等待的转变永远不会发生，等待会挂住**」 |

★ **镜像时点**：上述官方引用**部分取自本地镜像 `~/tech-research/dsh-docs`**。★ **实测：全机 24h 留证 9 条全部过期**（最新 97.4h 前，其余 189–845h）⇒ 按锚点 §6.1④「**留证过期即视为无留证**」，**上述引用应按「待重新补证」处理**。

---

## 9 · 已知未覆盖项

1. **在役面全未覆盖**（§3.1）—— 本请求书最重要的一条。
2. **`dod.full_table` 仍缺席** —— 索引 `dod.full_table = null`；锚点 §11 正文表只是**代表性摘录**。★ 请求方**未凭空补全**（R030），保持缺口。
3. **索引三/四层缺陷已修两层，另两层未修**：
   - 已修：`waves`/`items` 两段一致（B9）· 时间戳规范形 · 本地副本↔板值（B10 的一半）
   - **未修**：**`beacon-check.py` 仍是 17 条，未补 G-CR18 四条判据**（B10 本体）· 索引语义判定权仍归外部第三方（Q-N）
4. **缺 verifier 的三项**：`C1` / `C2` / `R049` 记 `closed_with_evidence` 却**无 `verifier` 字段** ⇒ 与 §5.1「未证不得记 closed」**直接冲突**。请求方**未代裁**。
5. **v5 正文事实主张未逐条回原件复核**（§3.3）。
6. **Wave S 七件工具的自证矩阵未逐件实跑**（§3.5）。

---

## 10 · 回滚点 + 回滚演练结果

**回滚点**：`~/dsh-collab/guard/backups/v5-rollback-20261010-071408/`（9 个文件）
含：板值原样 `continuity-index.board.json` · 本地副本（改前/改中/终版三态）· 续接提示词（改前）· 版本指针（改前）

**已演练的部分**：四件写入过程中**每步均先备份后写**，且**未出现需要回滚的失败**；`bb_dualwrite.py` 四次写入**均 `verdict: ok` / `values_equal: true`**。

**★ 未演练**：**整批回滚**（把四件一起还原到 v4 状态）**从未实跑** ⇒ 记 `未测`。请求方自陈：这是锚点 §17.5「报不通过，不调参」之外的一处**诚实缺口**。

---

## 11 · 提问清单（★ 要它裁什么）

1. **甲**：`docs/distributed-agent-network-governance-plan-v5-20261010.md` 作为锚点基线，**是否成立**？（三态）★ 特别请裁：**「自足性」主张是否属实** —— 即 v5 是否真的可以**单独阅读**而不必回 v4。
2. **乙**：三件接线**是否具备 `closed_with_evidence` 资格**？（三态）
   ★ 请求方自陈判断：**不具备** —— 正确状态是 `盘面已接线 · 待重启后在役验证`。请复核此判断是否过严或过宽。
3. **请求方对负控 3 的裁决（A = 如实标 `partial`）是否成立**？请独立判断 A / B / C 三条路径。
   ★ 请求方理由：B（改用 `user/message` + `surfaceOp:append`）会让通知**进模型可见表面、占上下文** ⇒ 违反 I2「不摘要」与立项自身（拿病治病）；C 方向对但本 build deferred。
4. **请求方把「缺 verifier 的 C1/C2/R049 保持 `closed_with_evidence` 不变、不代裁」是否恰当**？（§9.4）
5. **P27「判据失明族」的分类是否正确** —— 它是否应与 P16/P26 分列，还是应并入？
6. **G-CR18 四判据是否充分** —— 是否还有同类缺口未覆盖？（可补第五判据）
7. **请求方自陈「① ② ③ 盘面通过」是否有过宽**？（请求方读的是调用点与分支，**未实跑变异**）

---

## 12 · 样本窗

**`2026-10-09 夜 ~ 2026-10-10 晨`（单机 mac-mini）**，主题族＝「**会话硬死锁 P26 的止血与治理门 + 治理自检的判据缺口**」。
★ **全部判据仅在该样本窗内验证过**；换主题族引用时**须连同样本窗一起引**。

**本机身份自证（★ 必须由受委托方各自实跑，不得采信本文件）**：
```bash
hostname      # 应为 CoreydeMac-mini
hw.model      # 应为 Mac16,10
```

---

## 13 · 机制激活证据

| 机制 | 激活计数 | 证据 |
|---|---|---|
| 乙 · 守卫（`enableGuard`） | **`false` ⇒ 零激活** | `csx_status` 实调返回 `guard.enabled:false` · `mode:'measure-only'` · `steps:0` —— ★ **这是刻意的**：在役面未验之前它**必须**是 false |
| 乙 · 并发护栏 | `busy:0 / free:0 / staleStartIgnored:0` | 同上 |
| 甲 · 四件同步 | **已激活 1 次**（本次升版） | `bb_dualwrite` 四次写入均 `verdict: ok`；`beacon-check --net` 17 PASS / 0 SKIP / exit 0 |
| 甲 · G-CR18 | **0 —— 无实现** | 仅规格，无脚本（§9.3） |

---

## 14 · 载体身份（onDisk vs inService）★ 本件最关键的一栏

| 载体 | onDisk | inService | 差异 |
|---|---|---|---|
| `dsh-plugin-context-survival` | `0.12.0` · `STAGE=K6-wiring-3of3` · 三件 `wired` · sha 见 §4 | **`0.11.1` · `K5-r006-7of10` · 无 `wiring` 字段** | ★★ **两者不同版** |
| 成因 | — | 插件在 **CLD 启动时载入**（本机 CLD 于 `2026-10-10T06:56:31` 启动），而文件于 `07:08–07:19` 才改动 | **在役跑旧模块实例** |
| 判据 | — | **调 `csx_status` / `csx_recall` 实测**（★ 非「看工具表」——工具表冻结在会话起点） | — |
| 推论 | — | **`--selfcheck --allow-apply` 是新进程，必然读到盘上代码 ⇒ 该证据在原理上无法证明在役面** | 上游执行方报「全链冒烟过」**为真但不足以支撑在役结论** |

---

## ★ 请求方的自我限制声明

- 本请求书**不构成任何验收通过与裁决**（`r046_note` 同上游惯例）。
- 请求方**不代改**受裁对象的语义判定；**不因可能被裁「不通过」而预先美化**任何条目。
- 请求方已**如实列出**：在役面未验 · 两项负控当前不成立 · 整批回滚未演练 · 三项 `closed_with_evidence` 缺 verifier · v5 正文事实主张未逐条回原件。
- ★ **凡本文件标 `未测` 者，请受委托方独立取数**，不得引本文件的转述值。

---

*请求方：星桥第二任 `session-e317d6ab` · 本件成立与否不由请求方裁定。*
