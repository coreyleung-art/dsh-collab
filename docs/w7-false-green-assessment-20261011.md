# W7 假绿族 · 评估与证据件

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **锚点依据**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` · sha256 `bf5a4e6b76fdedeb3c7c48cc5d3830ea29c441ca0051091ec4f6adb7948e49e3` · **§10 W7 段（W7.1–W7.11）+ §7.11**
> ★ **本件是评估与证据件，不是裁定**；★ **不宣布任何事项已闭合**（S3 不可自审）；★ 效力档位 **L1（已记录）**
> ★ **归属纪律**：W7 各项的**归属列**锚点已写明（守卫属主 / 通道属主 / 壳桥属主 / 治理层）⇒ ★ **本线不代裁归属、不改对方件**，只做**复现与评估**，出**收紧类提案**。

---

## 一、W7.1 `doDepsScan` 分母三态化 —— ★ **活体复现成立**（含精确数字）

**锚点声称**：`ok = (scan.count === 0)`（`~/dsh-plugin-guard/lib/index.js:356`）；分母经 **101+5** 两次跳过归零。

**本线独立复跑**（未编辑输出）：

    $ guard_deps_scan（工具直调）
      {"total": 0, "mismatches": [], "count": 0}

    ★ 扫过的面: /Users/coreyleung/.dsh/profiles/web/node_modules/@deepseek-ai
    ★ 该目录条目总数 = 106
      ① 被 .bak/.pnpmcopy 正则跳过          = 101
      ② 其余中：符号链接（再被跳过）        = 5  ['cordis','dsh-api-gateway','dsh-base','dsh-client-runtime','dsh-web-app']
      ③ 其余中：普通文件（非目录，跳过）    = 0
      ④ 读不到的                            = 0
      ⑤ ★ 真正计入 total 的【普通目录】     = 0

    ⇒ 判据 :356 { ok: scan.count === 0 }，而 count=0 且 total=0
    ⇒ ★ verdict: ok=True ——【空转绿】（分母为 0，判据恒真）

★ **锚点写的「101+5」与本线实测的两个数字逐字吻合**（101 + 5 = 106 = 全部条目）。
★ **语义倒置证据**：被跳过的 5 个软链**全部指向 runtime 实体** —— 那**正是「不遮蔽」的健康态**；
  runtime 侧实体数 = **202**。⇒ 扫描器**跳过的是健康态、保留的是（可能不存在的）病态态**。

**源码机制**（`lib/index.js:288-306`，逐字）：

    function doDepsScan() {
      if (!existsSync(PROFILE_NM)) return { total: 0, mismatches: [], count: 0 };   // 早退
      for (const name of readdirSync(PROFILE_NM)) {
        if (/\.(bak|pnpmcopy)/.test(name)) continue;            // ①②跳过
        try { st = lstatSync(pdir); } catch { continue; }        // ④跳过
        if (!st.isDirectory() || st.isSymbolicLink()) continue;  // ②跳过
        total += 1;
      }
      return { total, mismatches, count };
    }
    // :356  out.checks.C7_version = { ok: scan.count === 0, ... }   ← ★ total 被返回，判据却不看它

**结论**：✅ 锚点 W7.1 **成立**。修法即锚点所写：`total===0 ⇒ ok = null`（不可判），**不得** `true`。
★ **归属 = 守卫属主**；★ 本线**不改**对方件。
★ **本线额外给出**：现网**已经是**「全 `.bak` + 全软链」的退化形态 ⇒ **负控用例不必另造，现网即是**。

---

## 二、W7.3 `all_ok` 语义修正 —— 由 §一 直接支撑

`lib/index.js:362` 逐字：`out.all_ok = Object.values(out.checks).every((c) => c.ok);`
⇒ 当 `C7_version` 因**分母为 0** 而 `ok: true` 时，`all_ok` **被空转项满足**。
⇒ ✅ 锚点 W7.3 **成立**（其成立性由 §一的活体读数直接支撑，非推断）。
★ 归属 = 守卫属主。

---

## 三、W7.2 检查项负控覆盖 —— **部分复现**

`out.checks.` 赋值点实点 **5 处**（C1 / C2 / C3 / C7 + 一处），锚点写「H5：**0/4** → 4/4」。
**本线实测**：守卫插件内**存在**一处负控自检 —— `lib/index.js:338` 逐字：
> 「判据为**多源表决 + fail-closed**；纯函数见 `./c1-judge.mjs`，**负控自检见 ./c1-selftest.mjs（9/9）**」

⇒ ★ **C1 有负控（9/9）**，其余检查项**未找到对应负控**。
⇒ 锚点「0/4」的说法在 **C1** 上**不成立**（C1 有），在 C2/C3/C7 上**成立**（未见负控）。
★ 精确表述应为 **1/4 有负控**（C1 ✅ / C2,C3,C7 ❌）—— ★ 以**当前源码**为准，**归属 = 守卫属主**。

---

## 四、★ W7.8 部分复现，且**发现一个锚点未载的新缺陷**

### 4.1 锚点部分的复现

    $ launchd_scan
      totalPlists: 80 · loaded: 78 · unloaded: 2 · parseFail: 0 · orphanLabels: [] · balanced: true
    $ plist 文件数（不含 .bak）
      80        ← ★ 分母已天然排除 .bak（.bak 命名为 com.dsh.X.plist.bak-*，不匹配 com.dsh.*.plist）
    $ grep -l 'env node' ~/Library/LaunchAgents/com.dsh.*.plist | wc -l
      0         ← ★ 未复现
    $ grep -l '<string>node</string>' … | wc -l
      0         ← ★ 未复现（80 个 plist 全部使用绝对路径）

| 锚点 W7.8 分句 | 判定 |
|---|---|
| 「**2** 项未载」 | ✅ **成立**（`com.dsh.auto-reminder` · `com.dsh.waimai.bad-review-scheduler`） |
| 「分母须剔 `.plist.bak-*`」 | ✅ 成立（且**现网已天然剔除**） |
| 「`env node` 改绝对路径」 | ❌ **未复现**（`env node` 0 命中；无相对路径 node） |
| 「digest `exit 127`」 | ⚠️ **不可判** —— 本线在 80 个 `com.dsh.*.plist` 中**未见 digest 类**，无法定位该现象；★ **不声明其不存在**（可能在他处/已消失） |

### 4.2 ★★ 新发现：`launchd-scan` 的 `StartCalendarInterval` 解析缺陷（**锚点未载**）

`~/dsh-plugin-launchd-scan/lib/core.js:65,83` 逐字：

    const cal = Array.isArray(plist.StartCalendarInterval) && plist.StartCalendarInterval.length > 0
      ? plist.StartCalendarInterval[0] : null;
    …
    calendar: cal ? { hour: cal.Hour, minute: cal.Minute } : null,

**两处缺陷**：
1. **`Array.isArray` 只认数组形态** —— `StartCalendarInterval` 在 plist 中**既可为 dict（单个）也可为 array（多个）**；为 dict 时 `cal = null`。
2. **`Weekday` / `Day` 被整个丢弃** —— 即使解析成功，只取 `Hour`/`Minute` ⇒ **周任务与日任务在报告里长得一样**。

**爆炸半径实测**（★ 分母 = `com.dsh.*.plist` **80** 个，逐份 `plistlib` 实读）：

| 形态 | 个数 | 后果 |
|---|---|---|
| `StartCalendarInterval` 为 **dict** | **21** | ⇒ `calendar: null`（报成「无排程」） |
| `StartCalendarInterval` 为 **array** | **1**（`com.dsh.maintenance-restart`） | 只取 `[0]` ⇒ 丢 `Day` |
| **合计受影响** | ★ **22** | 含 **7 个带 `Weekday` 的周任务** |

**逐字对照（最刺眼的一例）**：

    $ cat ~/Library/LaunchAgents/com.dsh.cron.bus-triage.plist
      <key>StartCalendarInterval</key>
      <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    $ launchd_scan 对同一任务报：
      "intervalS": null, "calendar": null, "runAtLoad": false, "freqClass": "onetime"

⇒ ★ **一个「每周一 09:00」的周期任务，被报成「`onetime`（一次性）、无排程」**。

**第二例（`maintenance-restart`）**：真身 `[{'Day':1,'Hour':4},…,{'Day':28,'Hour':4}]` = **每 3 天一次**
  ⇒ 工具报 `{"hour":4,"minute":0}`，**读起来像每天 04:00**。

### 4.3 ★★ 本线**亲身躲过**的一次误判（这是该缺陷的真实代价）

M4③ 分析时，本线据「`bus-triage-cron.log` 停在 **2026-10-05 09:00**」一度怀疑**该 cron 的输出面已失效**。
★ **若信 `launchd_scan` 的 `freqClass: onetime` + `calendar: null`，会强化该误判**（「它根本不定时跑」）。
★ **实际**：直读 plist 得 `Weekday:1 09:00`（**每周一**），而 2026-10-05 **正是上一个周一** ⇒ **日志不陈旧，是正常**。
⇒ ★ 该缺陷会**把一个健康的周期任务读成死的**，并**连带误判其下游产物「没人看」**。

---

## 五、★★ 跨件综合：一个反复出现的形态 —— 「**算了不用**」

本夜两个**互不相关**的组件，出现了**同一个**缺陷形态：

| # | 组件 | 算什么 | 怎么丢 | 后果 |
|---|---|---|---|---|
| 1 | `dsh-plugin-agent-bus:1327` | `expired` 计数（`:1303/1312`） | **`return delivered;` 处丢弃**（`expired` 变量成死代码） | `expired` **静默**（M4③②） |
| 2 | `dsh-plugin-guard:356` | `total`（分母，`:304` 返回） | **判据只看 `count`，不看 `total`** | `total=0` ⇒ **空转绿**（W7.1） |
| 3 | `dsh-plugin-launchd-scan:83` | `StartCalendarInterval` 全文 | **只取 `Hour`/`Minute`，丢 `Weekday`/`Day`** | **周任务读成日任务 / 无排程**（§4.2） |

★ **三者同型**：**量已经算出来了，但【判据或返回面】没有用它** ⇒ 判据恒真、或信号静默。
★★ **可机械检出**：凡「**局部变量被计算后从未在判据/返回中使用**」，以及
**「判据引用的字段 ⊊ 采集到的字段」**，都是本形态的实例。
★ 本线**建议**（架构级，收紧类）：把「**采集字段 ↔ 判据引用字段**」的差集做成一条**机械自查**
（与本线 `channel-denominator.py` 的「声明↔活体」比对同型）—— ★ **归属与实施须另行立项**，本线**不施工**。

---

## 六、★ 边界与未证项

| # | 项 | 状态 |
|---|---|---|
| 1 | **W7.4 / W7.5 / W7.6 / W7.7 / W7.9 / W7.10 / W7.11** | ★ **未评估**（本轮聚焦 W7.1/W7.2/W7.3/W7.8）—— ★ **不声明其余各项的判定** |
| 2 | **W7.6** | ★ **已随 M4① 落地**（drift 跨板判据取代「本地 PUT 200」）—— 证据见 `docs/m4-1-delivery-and-evidence-20261011.md` |
| 3 | **本线是否修改了上述任一对方件** | ★ **没有**。全部改动只在**本线自己的件**（`scripts/drift-scan-cron.py` 经变更单 / 两个新工具 / 本线文档） |
| 4 | **各缺陷的独立性** | ★ **本线自测，无独立 verifier** ⇒ 按 S3 **一律不得记 `closed`** |
| 5 | **`digest exit 127`** | ⚠️ **不可判**（未定位到 digest 类 plist） |

---

## 七、★ 复跑块（★ 本节所有会变的数字，一条命令全出）

    # [1] W7.1 分母（★ 注意面是 @deepseek-ai 目录本身，不是它的父目录）
    python3 - <<'PY'
    import os,re
    NM=os.path.expanduser("~/.dsh/profiles/web/node_modules/@deepseek-ai")
    e=sorted(os.listdir(NM)); bak=[n for n in e if re.search(r'\.(bak|pnpmcopy)',n)]
    rest=[n for n in e if n not in bak]
    sym=[n for n in rest if os.path.islink(os.path.join(NM,n))]
    d=[n for n in rest if os.path.isdir(os.path.join(NM,n)) and not os.path.islink(os.path.join(NM,n))]
    print("条目=%d  bak跳过=%d  软链跳过=%d  ★计入total=%d"%(len(e),len(bak),len(sym),len(d)))
    PY
    guard_deps_scan        # → total / count（★ count=0 而 total=0 = 空转）
    # [2] W7.3 判据
    grep -n 'all_ok' ~/dsh-plugin-guard/lib/index.js
    # [3] W7.2 负控
    grep -n 'selftest\|负控' ~/dsh-plugin-guard/lib/index.js | head -5
    # [4] §4.2 calendar 解析缺陷（爆炸半径）
    python3 - <<'PY'
    import os,glob,plistlib
    D=os.path.expanduser("~/Library/LaunchAgents"); n=0; f=[]
    for p in sorted(glob.glob(os.path.join(D,"com.dsh.*.plist"))):
        sci=plistlib.load(open(p,"rb")).get("StartCalendarInterval")
        if sci is None: continue
        n+=1; f.append(os.path.basename(p))
    print("受 calendar 解析缺陷影响（dict+array 合计）=",n)
    PY
    launchd_scan | grep -A2 'bus-triage'      # → calendar:null / freqClass:onetime（错报）
    # [5] W7.8
    launchctl list | grep -c com.dsh ; ls ~/Library/LaunchAgents/com.dsh.*.plist | wc -l
    grep -l 'env node' ~/Library/LaunchAgents/com.dsh.*.plist | wc -l    # → 0（该分句未复现）
    # [6] §五 形态自查（「算了不用」两处）
    grep -n 'let expired = 0\|return delivered;' ~/dsh-plugin-agent-bus/lib/index.js
    grep -n 'total, mismatches, count\|scan.count === 0' ~/dsh-plugin-guard/lib/index.js

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
