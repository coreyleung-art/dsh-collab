# CLD 重启后复核（M4/W7 批次 · 外部第三方 · CU 实验台线）

> **复核方**：外部第三方 · Claude Code 会话 · 角色键 `ext` · session `005a2c58-7439-4ad5-bebf-815b29c2ca4a`
> **触发**：用户 2026-10-11「已经重启」
> **前置件**：`docs/v6-third-party-review-result-ext-cu-m4w7-batch-20261011.md`（含 §八 漂移记录 / §八之二 定向复跑）
> **纪律**：只读 · 对抗性 · 三态 · 报「0 条」附扫过的面 · ★ **未重启任何进程、未改任何文件、未跑插件自检**
> **窗口**：**2026-10-11 17:37–17:52 CST**

---

## 〇、一句话结论

**重启已确认（17:30:22）；被审四件加载的是修复版（推断，非直接观测）；M4/W7 批次的 B1/B3 行为面仍不可判（我无插件内省工具，且不越权跑插件自检）。★ 另在重启面上抓到 3 条本批之外的新事实，其中 1 条是「插件自检报 false 而实为判据缺陷」。**

---

## 一、重启事实（逐条证据）

### 1.1 重启确已发生

    $ ps -Ao pid,lstart,etime,command | grep 'CLD.app/Contents/MacOS'
    57615 日 10月/11 17:30:22 2026    10:22  /Applications/CLD.app/Contents/MacOS/CLD
    57676 日 10月/11 17:30:22 2026    10:22  /Applications/CLD.app/Contents/MacOS/CLD --expose-internals \
        /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js web --port 0 --no-open

★ 主进程 **pid 57615 / 57676，启动于 2026-10-11 17:30:22**（观测时已运行 10 分 22 秒）。⇒ **成立**。
★ 注：`crashpad_handler` 子进程的 lstart 为 10-10（进程复用），**不可**用作重启判据 —— 我用主可执行路径判定。

### 1.2 ★ 加载的是修复版（**推断**，见 §三 声明）

    $ （被审件 mtime vs 重启时刻）
    agent-bus/lib/index.js          17:15:54   < 17:30:22 ✓
    agent-bus/lib/selfcheck.js      17:07:12   ✓
    agent-bus/package.json          17:16:02   ✓
    launchd-scan/lib/core.js        17:15:23   ✓
    guard/lib/index.js              04:39:24   ✓
    bus-queue-triage/cli.js         04:39:49   ✓
    bus-queue-triage/lib/core.js    04:40:21   ✓

    $ ls -la ~/.dsh/profiles/web/node_modules/ | grep -E 'agent-way|launchd-scan|guard'
    dsh-plugin-agent-way     -> ../../../../dsh-plugin-agent-bus
    dsh-plugin-guard         -> ../../../../dsh-plugin-guard
    dsh-plugin-launchd-scan  -> ../../../../dsh-plugin-launchd-scan

⇒ **全部被审件 mtime 早于重启** + **profile 经软链指向 `~/dsh-plugin-*`** ⇒ 加载的即为我持有的修订（`8802f6736dc3fdfe` 等）。

### 1.3 ★ B1 插件加载成功（**运行时输出**，非推断）

    $ cat ~/.dsh/plugin-selfcheck/agent-way.json          # mtime 10-11 17:30:28
    {
      "plugin": "agent-way",
      "ok": true,
      "missing": [],
      "warnings": [],
      "resolved": [
        "@deepseek-ai/cordis   → …/dsh-runtime/runtime/node_modules/@deepseek-ai/cordis/lib/index.js",
        "@deepseek-ai/dsh-tools → …/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools/lib/index.js"
      ],
      "ts": 1791711028655
    }

★ `ts 1791711028655` = **2026-10-11T17:30:28.655+08:00** = 重启后 6 秒。⇒ **agent-way（= B1 的 agent-bus）在本次重启中成功加载，peer 依赖全部解析** ⇒ **成立**。

---

## 二、★ 重启门（D-038）在生产中跑通 —— 并**当场抓到一次窗口内变更**

    $ cat logs/restart-intent.log
    2026-10-11T17:13:54 prepare REFUSED: 尚无重启前审查证明（先跑 restart-intent review 再 attest）
    2026-10-11T17:13:57 review verdict=FAIL items=36 changed=13
    2026-10-11T17:14:06 review verdict=FAIL items=36 changed=13
    2026-10-11T17:14:49 review verdict=FAIL items=36 changed=13
    2026-10-11T17:15:13 review verdict=PASS items=36 changed=13
    2026-10-11T17:15:23 attest ok files=13
    2026-10-11T17:15:23 prepare REFUSED: ★ 证明已失效：1 个文件在签发后又被改动 ⇒ core.js（内容已变）
    2026-10-11T17:16:20 review verdict=PASS items=36 changed=13
    2026-10-11T17:16:22 attest ok files=13
    2026-10-11T17:17:25 review verdict=PASS items=36 changed=13
    2026-10-11T17:28:52 review verdict=PASS items=36 changed=13

**读法（三态）**：
1. **门存在且在路径上**：第一次 `prepare` 被 **REFUSED**（「尚无重启前审查证明」）⇒ 门**不是**装饰 ⇒ **成立**。
2. ★ **门抓到了一次真实的 TOCTOU**：`17:15:23 attest ok files=13` → **同一秒** `REFUSED：证明已失效 ⇒ core.js（内容已变）`。★ 而 `launchd-scan/lib/core.js` 的 mtime **正是 17:15:23** ⇒ 该 REFUSED **属实**（非假阳）。
3. 随后重审 → `17:16:22 attest ok` → `PASS`（17:17:25 / 17:28:52）⇒ **恢复闭环**。

⇒ ★★ **这与我同日提交的提议件（`docs/proposal-review-window-traceability-20261011.md`）§四 A 层是同一件事，且已经实现**：
**哈希绑定被审集 + 签发后变更即拒**。★ **我据此下调该提议的必要性**（见 §五）。

---

## 三、★ 三态：B1 / B3 的行为面

| 问题 | 三态 | 判据 |
|---|---|---|
| 修复版**被加载** | ★ **成立（推断）** | §1.2 mtime + symlink + §1.3 运行时 `ok:true` |
| 修复**行为已生效** | ★ **不可判** | ★ **我无任何直接行为观测**（未触发 flush、未观察 `boarded-pending` 保留）；且**我未跑插件自检**（属「执行插件代码」，需显式授权） |
| B3（guard）加载 | ★ **不可判** | `~/.dsh/plugin-selfcheck/` **无 `guard.json`**（扫过的面 = 该目录全部 30 个文件）⇒ 该插件**无加载期自检记录**，我无从读 |
| B4（launchd-scan）加载 | ★ **不可判** | `launchd-scan.json` mtime = **10-02 23:09**（**陈旧**，未随本次刷新）⇒ 无本次加载记录 |

★ **诚实声明**：「加载 = 修复版」是**推断链**（mtime 早于重启 + 软链 + 该插件自检通过），**不是**对修复代码路径的直接观测。★ 要闭合「行为已生效」，唯一途径是**跑插件自检**（`~/dsh-plugin-agent-bus/cli.js --selfcheck`）—— 那属「执行插件代码」，**我不越权；已在 §六 列出等你裁**。

---

## 四、★ 重启面上新抓的 3 条（**均在本批 M4/W7 之外**）

### 4.1 ★★ 一个插件自检报 `ok:false`，而**实为判据缺陷**

    $ cat ~/.dsh/plugin-selfcheck/context-survival.json      # mtime 10-11 17:30:28
    { "plugin": "context-survival", "ok": false,
      "missing": [
        "lib/index.js 中未见 resolveBudget 的导入/定义（裸用将 ReferenceError）",
        "lib/budget.js 中未见 defineTool 的导入/定义（裸用将 ReferenceError）",
        "lib/budget.js 中未见 resolveRecallTarget 的导入/定义（裸用将 ReferenceError）",
        "lib/budget.js 中未见 observePressure 的导入/定义（裸用将 ReferenceError）",
        "lib/guard.js 中未见 defineTool 的导入/定义（裸用将 ReferenceError）",
        "lib/guard.js 中未见 resolveRecallTarget 的导入/定义（裸用将 ReferenceError）"
      ], "ts": "2026-10-11T09:30:28.652Z" }

★ 我**不采信该结论**，改去读源码（**独立复核，不引用其判定**）：

    $ grep -n 'requiredSymbols' ~/dsh-collab/devices/dsh-plugin-context-survival/lib/index.js
    289:      requiredSymbols: ['defineTool', 'resolveRecallTarget', 'resolveBudget', 'observePressure'],

    $ （逐符号实际出现次数）
    lib/budget.js  defineTool=0   resolveRecallTarget=0   observePressure=0
    lib/guard.js   defineTool=0   resolveRecallTarget=0
    lib/index.js   resolveBudget=1   ← ★ 唯一那 1 处 = :289 的清单【自身】

**判定**：★ **该 `ok:false` 是判据缺陷，不是回归**。三处成因：
1. **一张扁平清单套到每个文件**：`requiredSymbols` 是**模块级**声明，自检却拿它逐个文件地要求 ⇒ `budget.js` 被要求含 `defineTool`，而 `budget.js` 里 `defineTool` **出现 0 次**（它本就不用那个 API）⇒ 该报错**恒真**。
2. ★ **自指**：`lib/index.js 中未见 resolveBudget` —— 而 index.js 里 `resolveBudget` **恰好只出现在 :289 的 `requiredSymbols` 清单里** ⇒ **判据被自己的声明满足/触发**。★ 这与起草人自己的**编辑规程 E1**（「某字面串计数 = 0」的判据须先核该字面是否在你自己要求写入的正文里）**是同一族**。
3. 同一族第三次：本线复核件 **N7**（B3「null 语义」断言同义反复）· 起草人当日自修的 **1.5.25**（判据钉字面→钉契约）· 本条。

⇒ ★ **建议**：该自检改为**按文件的实际使用点**判（用了却没引入 ⇒ 报错；没用到 ⇒ 不报），而非按模块级清单逐文件套。★ **本条不在 M4/W7 批次内，我未修改任何东西**（只审不动）。

### 4.2 `bus-bridge` 在重启时刻连报工具注册失败（**既有，非本次引入**）

    $ tail -6 ~/.dsh/bus-bridge.log
    {"ts":"2026-10-10T14:34:32.100Z","plugin":"bus-bridge","type":"tool-register-error","error":"cannot get property \"tools\" without inject"}
    {"ts":"2026-10-11T09:30:28.629Z",…,"error":"cannot get property \"tools\" without inject"}
    {"ts":"2026-10-11T09:30:28.630Z",…}   ×4（同秒 5 条）

★ 时间戳 `09:30:28Z` = **17:30:28 CST**（本次重启）⇒ 该插件在加载期**未能注册其工具**。
★ **但同一错误在 10-10 14:34 已存在** ⇒ **既有缺陷，非本次重启引入**。★ 与我的记忆条「宿主端插件不得 inject 客户端服务，否则整棵插件树加载失败」同族，但此处**未致 CLD 起不来**（仅该插件的工具缺失）。
★ 扫过的面：`~/.dsh/bus-bridge.log`（全文尾部 6 行）。

### 4.3 `launchd-scan` / `guard` 在加载期自检面无记录

    $ ls -la ~/.dsh/plugin-selfcheck/ | grep -E 'launchd-scan|guard'
    launchd-scan.json   10月 2 23:09      ← 陈旧（未随本次刷新）
    （无 guard.json）

★ 这**不构成缺陷**（可能这两个插件本就无加载期自检钩子），★ 但它意味着：**B3/B4 的「已加载」我无法从该面读到** ⇒ 见 §三 的「不可判」。

---

## 五、★ 对本线自己提议件的下调（对抗性地对自己）

本线同日提交 `docs/proposal-review-window-traceability-20261011.md`，主张「开窗/闭窗指纹 + 变更留痕」。
★ **今日实测表明：其中 A 层（哈希绑定 + 签发后变更即拒）已被起草人以 D-038「重启门」实现并在生产中生效**（§二 第 2 条，且它真抓到一次 TOCTOU）。

⇒ **我据此下调该提议**：**A 层不再是「新提议」，而是「已实现，建议推广到复核窗口（现仅覆盖重启窗口）」**。
★ 仍**保留**的两点：
1. **适用范围**：现门覆盖**重启**（13 文件 / 36 项）；本线复核覆盖 **28 条声称** ⇒ 两集**不同**，复核窗口仍无等价机制。
2. **闭窗指纹**：本线复核件仍应登记结束时指纹（本件 §六 已补）。

---

## 六、闭窗指纹（本线复核的收束值 · 2026-10-11 17:40 实测）

| 件 | 闭窗 sha16 | 与本线开窗（复核件 §0.2）比 |
|---|---|---|
| `~/dsh-plugin-agent-bus/lib/index.js` | `8802f6736dc3fdfe` | ★ **已变**（开窗 `ee255df4bb3de2cb`） |
| `~/dsh-plugin-launchd-scan/lib/core.js` | `18935109c6400201` | 未变 |
| `~/dsh-plugin-guard/lib/index.js` | `79d6979fa38670f7` | 未变 |
| `~/dsh-plugin-bus-queue-triage/cli.js` | `e825511e8a3687e7` | 未变 |
| `~/dsh-plugin-bus-queue-triage/lib/core.js` | `7df4f81423181296` | 未变 |
| 锚点 v6.1 | `bf5a4e6b76fdedeb`（全 sha 未变） | 未变 |
| `agent-bus` 版本 | **1.5.26** | 开窗记 1.5.24 |
| 台账 D-0xx 条数 | **40** | 本件称 31 · 复核件记 35 |

---

## 七、三态总表（本件新增/更新）

| 项 | 三态 | 依据 |
|---|---|---|
| 重启已发生（17:30:22） | ★ **成立** | §1.1 ps |
| 被审件加载的是修复版 | ★ **成立（推断）** | §1.2 mtime+symlink；§1.3 运行时 ok:true |
| **B1 修复行为已生效** | ★ **不可判** | 无直接行为观测；未跑插件自检（未获授权） |
| **B3 修复行为已生效** | ★ **不可判** | 无 `guard.json`，加载面无记录 |
| B4（launchd-scan）已加载 | ★ **不可判** | `launchd-scan.json` 陈旧（10-02） |
| 重启门在位且非装饰 | ★ **成立** | §二 REFUSED + attach/attest 链 |
| 重启门抓到真实 TOCTOU | ★ **成立** | §二 `17:15:23` REFUSED 与 `core.js` mtime 同秒吻合 |
| `context-survival` 自检 ok:false | ★ **不成立（判据缺陷）** | §4.1 源码复核：扁平清单 + 自指 |
| `bus-bridge` 工具注册失败为本次引入 | ★ **不成立** | §4.2 10-10 14:34 已有 ⇒ 既有 |

---

## 八、★ 需要你裁的一件事（我不越权）

要**闭合 B1/B3 的行为面**，唯一途径是**跑被审插件自己的自检**：

    ~/dsh-plugin-agent-bus/cli.js --selfcheck      # B1（含 delivery-guard 判据）
    ~/dsh-plugin-guard/cli.js    --selfcheck      # B3

★ 这属「**执行插件代码**」，**超出我的默认只读边界** ⇒ **我不跑，等你显式授权**。
★ 若授权，我可复核：① 自检是否 exit 0 ② `delivery-guard` 判据是否真的**钉契约而非钉字面**（即 1.5.25 那处）③ B3 的 `degenerate ⇒ null` 是否在运行时成立。
★ 若你**不授权**，则 §三 的四条**保持「不可判」**（★ 不可判 ≠ 成立，也 ≠ 不成立）。

---

## 九、署名与声明

- **复核方**：外部第三方 · `ext` · session `005a2c58-…` · CU 实验台线
- **窗口**：2026-10-11 **17:37–17:52 CST**
- ★ **本件是复核结果，不是裁定**；★ **不宣布任何事项已闭合**（S3）。
- ★ **本轮未重启任何进程、未改任何文件、未跑插件自检、未热更新、未发 xdom 信**；唯一写入物 = 本件。
- ★ 报「0 条」的面：`~/.dsh/plugin-selfcheck/`（全 30 文件逐一看过）· `logs/restart-intent.log`（全文 10 行）· `~/.dsh/bus-bridge.log`（尾部）· `~/.dsh/plugin-selfcheck/selfcheck.log`（尾部 40 KB）· 被审 7 件 + 锚点 + 台账（sha/条数）· CLD 进程表。

*（本件只增不改；更正以新件追加。）*
