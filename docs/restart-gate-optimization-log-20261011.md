# 重启前审查门 · 优化记录归档

> **归档件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **缘起**：用户逐字指示 —— 「把重启前审查这个动作变成，**凡事你给我提议重启之前，就会遇到的门**，
> 必须要经过重启前审查才能正式跟我提议的一种机制以及类似 lean4 结构门？
> **不用我每次提醒你才去做，避免我忘记提醒，但实际存在问题，然后就导致各种崩溃需要救援的情况**」
> **本质**：把「**靠人记得提醒**」换成「**结构上过不去**」（结构 beats 纪律）。
> ★ 本件是**归档**，不是结项；★ 不主张任何事项已闭合（S3）。

---

## 一、这道门是什么

| 项 | 内容 |
|---|---|
| **落点** | `scripts/restart-intent.py`（★ **改造既有件**，非新建 —— J44 裁决 `adapt`） |
| **接线点** | `dsh-plugin-agent-bus` 的 `requestRestart()` —— ★ **在任何其它判断之前**先校证明 |
| **拒绝语义** | 无有效证明 ⇒ `requestRestart` 返回 `{ok:false, _gate:{verdict:'deny', howto:[…]}}` ⇒ **不发起重启征询** |
| **逃生口** | ★ **用户可随时手动重启** —— 本门**只拦 agent 的提议**，不拦人 |
| **三命令** | `review`（跑审查）→ `attest`（PASS 才签发，绑定 sha256）→ `verify`（校验是否仍有效） |

---

## 二、★ 优化记录（按发生顺序，逐条含「为什么」与证据）

### O-1 · 为什么选 `adapt` 而不是新建工具

**J44 门跑出 1 条命中：`scripts/restart-intent.py`。** 读后发现它**已经有 R011 强制门**
（`:113` 逐字「❌ R011 强制门 FAIL，禁止重启（先修复插件）」）且已是**重启留档**的既定入口（R013）。
⇒ ★ 新写平行工具 = 又一个「同一件事两处实现」⇒ **裁决 `adapt`：扩它**。

### O-2 · ★ 修既有缺陷①：**重定向 token 被当成实参**（原门「不是拦，是崩」）

原 `run_guard()`：

    _sp.run([guard, "restart-guard", …, ">", "/tmp/restart-guard.txt", "2>&1"], capture_output=True, text=True)

★ `subprocess.run(列表)` **不经 shell** ⇒ `>`、路径、`2>&1` 被二进制当作**普通参数**接收 ⇒
**文件从未写出**（实测 `/tmp/restart-guard.txt` **不存在**）；而紧随的 `open(out_file)` **无 try**
⇒ `prepare` 会 **FileNotFoundError 崩掉**。
⇒ ★ **原来的门不是「拦」，是「崩」**。改为 `capture_output` 收 stdout/stderr，**由脚本自己写文件**。

**证据**：`stat /tmp/restart-guard.txt` ⇒ 不存在；`restart-intent.py:106` 的 `open()` 无 try。

### O-3 · ★ 修既有缺陷②：**工具缺失即静默放行**（假绿路径）

原实现 `guard = os.path.expanduser("…dsh-tools-macos-arm64-v1.10.0")` —— ★ **版本号写死**；
不存在时 `return None`，而调用方 `if ok is False:` **只拦 False** ⇒ ★ **升版换名 ⇒ 静默放行**。

⇒ 两处修：① `_find_guard()` **按 glob 取最新版**，不写死版本号；② 调用方按**三态**处理
（`ok is not True` ⇒ 拒绝）⇒ ★ **不可判 ≠ 通过 ⇒ 拒绝**。

**证据**：`ls ~/dsh-collab/rust-tools/dist/` 显示存在多版本 ⇒ 写死路径确有失效风险。

### O-4 · ★ 核心设计：证明与**每一个被改文件的 sha256** 绑定

**为什么**：一次性通过的证明会变成「**旧绿**」—— 审完之后再改代码，证明却仍然有效。
这正是本机反复出现的同族缺陷（「算了不用」/「判据绑在形式上」）。
⇒ `attest` 写入 `{文件路径: sha256}`；`verify` **逐个复算**，任一不符即**失效**。

**端到端证据（7 步）**：

    verify            ⇒ ❌ 尚无证明（拒绝）
    prepare …         ⇒ ❌ 拒绝生成重启提议（核心要求达成）
    review            ⇒ 36 项 · PASS
    attest            ⇒ ✅ 绑定 13 个变更文件
    verify            ⇒ ✅ 有效
    echo //x >> core.js; verify  ⇒ ❌ 立即失效（core.js 内容已变）
    prepare …         ⇒ ❌ 同步被拒
    （还原）verify     ⇒ ✅ 重新有效（sha 一致）

### O-5 · ★ 优化：R2「加载路径」检查 —— 本审查**最有价值的一项**

**为什么必须有**：本机 `agent-bus` 的**目录名 `-bus` ≠ 包名 `-way`**，若按目录名查 profile，
会得出「**不在 profile**」的**错误结论** ⇒ 进而误判「**全部修复重启后不生效**」。
（本线当日**真的差点据此推翻整批修复的有效性**。）

**两轮优化**：
- **① 相对 `link:` 的解析基准错了**。`"dsh-plugin-launchd-scan": "link:../../../dsh-plugin-launchd-scan"` 是
  **相对路径**，原实现用 `realpath(expanduser(v))` ⇒ **按 CWD 解析** ⇒ 得到错路径 ⇒
  把**确实在 profile 里**的插件误判「不在」= **假不可判**。
  ⇒ 修为 **以 profile 目录为基准**解析。
- **② 判据从「二元」改为「三分支」**：进程内插件看 profile `link:` 目标；
  **launchd 直调 CLI** 看它是否被任一 plist 的 `ProgramArguments` 引用；
  两者都不是才是真问题。
  ⇒ 治「把 CLI 工具误判为『不在 profile』」的假不可判。

**效果**：修后 5 个目录**全部正确解析**，假不可判 = **0**：

    OK  R2 加载路径: dsh-plugin-agent-bus      ✓ profile link: 目标（包名 dsh-plugin-agent-way）⇒ 改动会被加载
    OK  R2 加载路径: dsh-plugin-bus-queue-triage ✓ launchd 直调 CLI ⇒ 改动会被加载
    OK  R2 加载路径: dsh-plugin-guard          ✓ profile link: 目标
    OK  R2 加载路径: dsh-plugin-launchd-scan   ✓ profile link: 目标
    OK  R2 加载路径: dsh-plugin-voice          ✓ profile link: 目标

### O-6 · ★★ 优化：**既有失败申报表**（这条决定门能不能活下来）

**问题**：本机存在**与本轮改动无关的既有失败**。若门不区分「既有」与「新引入」⇒ **永久红** ⇒
**人为绕过** ⇒ **门失去意义**。

**解法**：`~/.dsh/restart-review/preexisting.json` —— 允许把既有失败**显式申报**，门标为 `PRE-EXISTING`：
- ★ **不阻断**（否则死锁）
- ★★ **但每一次审查都大声列出**（不是静默放行）
- ★ **硬约束**：每条**必须带 `reason` 与 `evidence`**，缺任一 ⇒ **该条不生效**（防「填个名字就过」）

**效果**：判定由 `FAIL（FAIL 2 · 不可判 2）` 变为
`PASS（FAIL 0 · 不可判 0 · **既有失败 2** · 共 36 项）`，且两项**带理由与证据逐条打印**。

### O-7 · ★ 优化：三态聚合（不可判不放行）

审查项与整体判定都是**三态**：`True / False / None(不可判)`。
★ 聚合规则 `FAIL > UNDECIDABLE > PASS` —— **只要有一项不可判，整体就不是 PASS**。
**负控证明**（`--selftest`）：

    全通过 ⇒ PASS ✓   有一项 False ⇒ FAIL ✓
    ★有不可判 ⇒ UNDECIDABLE（不得 PASS）✓   FAIL 优先于不可判 ✓

### O-8 · 优化：R006 门与自证

`--lean4-check` **6/6**（A 类型锁 / B 无 shell / C argparse / D 真实现+分派 / E try / F 负控矩阵）
+ `--selftest` **6/6**（含「文件改动后 sha 改变 ⇒ 证明会失效」与「无证明时走拒绝分支」两条负控）。

---

## 三、★ 这道门**立刻抓到的东西**（它的价值证明）

| # | 抓到什么 | 性质 |
|---|---|---|
| 1 | ★★ **它抓到了本线自己** —— 签发证明后本线为接线又改了 `index.js`/`package.json` ⇒ `verify` 报「**2 个文件在签发后又被改动**」并拒绝 | ★ **设计意图的实现**：改了就必须重审 |
| 2 | ★ **本线 R2 检查项自身的 bug**（相对 `link:` 按 CWD 解析 ⇒ 假不可判） | 本线自查自修（O-5） |
| 3 | ★ **`dsh-plugin-launchd-scan --selfcheck` 结构性崩溃**（`cli.js:118` 读 `r.mountSmoke.state` 而它不存在 ⇒ TypeError） | ★ **既有缺陷**（用改前备份复跑确认非本线引入）· 台账 **D-039** |
| 4 | ✅ **复现 `bus-queue-triage` 自检红**（内嵌身份表陈旧，星桥→已死会话） | 既有缺陷 · 台账 **D-037** |

★ **3 与 4 是「此前从未有人跑过这些插件的 `--selfcheck`」的直接证据** —— 门一建，两个「等于没有自检」的插件立刻现形。

---

## 四、★ 已知盲区（**如实列出，别当已全覆盖**）

| # | 盲区 | 后果 |
|---|---|---|
| 1 | ★ 变更窗口只扫 **`~/dsh-plugin-*`** | `~/dsh-collab/scripts/` 下工具（**含门自己**）的改动**不触发失效** ⇒ 门逻辑被改后旧证明仍有效 |
| 2 | ★ 申报表**无过期机制** | 已申报的既有失败**会一直生效**，不会被要求复验 |
| 3 | ★ 只跑**被改动过**的插件的自检 | 其它插件的自检崩溃**不会被发现**（未做全机普查） |
| 4 | 变更窗口默认 24h | 超过 24h 前改的文件不在审查面内 |
| 5 | ★ 本门**未接** `agent_restart_go`（激活） | 只拦**发起征询**；理论上可先有证明再改文件后直接 go ⇒ ★ **未验** |

★ 门自己也不主张完备：**盲区 1 与 5 应优先补**。

---

## 五、复跑块（★ 本件所有会变的数字，一条命令全出）

    # [1] 门三命令
    python3 ~/dsh-collab/scripts/restart-intent.py review --hours 24     # 36 项；exit 0/1/2
    python3 ~/dsh-collab/scripts/restart-intent.py attest --hours 24     # 仅 PASS 时签发
    python3 ~/dsh-collab/scripts/restart-intent.py verify                # 证明是否仍有效
    # [2] 门自证（六项约束门 + 含负控的自证）
    python3 ~/dsh-collab/scripts/restart-intent.py --lean4-check
    python3 ~/dsh-collab/scripts/restart-intent.py --selftest
    # [3] ★ 拒绝语义（不写黑板：无证明时在写盘前就退出）
    python3 ~/dsh-collab/scripts/restart-intent.py prepare --node mac-mini --reason "probe" --rescuer mbp; echo "exit=$?"
    # [4] ★ 失效验证（改一个文件 ⇒ 证明必须立即失效；跑完请还原）
    cp ~/dsh-plugin-launchd-scan/lib/core.js /tmp/k.js && echo "//x" >> ~/dsh-plugin-launchd-scan/lib/core.js
    python3 ~/dsh-collab/scripts/restart-intent.py verify; echo "期望非 0"
    cp /tmp/k.js ~/dsh-plugin-launchd-scan/lib/core.js
    # [5] 接线在不在
    grep -n 'function restartReviewGate\|gate.ok !== true' ~/dsh-plugin-agent-bus/lib/index.js
    # [6] 申报表（每条须带 reason + evidence，否则不生效）
    python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.dsh/restart-review/preexisting.json')));print({k:(bool(v.get('reason') and v.get('evidence'))) for k,v in d.items()})"
    # [7] 审计轨迹（每次 review/attest 都写）
    tail -5 ~/dsh-collab/logs/restart-intent.log

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
