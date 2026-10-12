# v7 待裁事项 · 裁决案卷（S1–S9 · 逐项七栏）

> **产出**：2026-10-13 · 待裁事项整理代理（本线）
> **主输入**：`docs/v7-skip-register-20261012.md`（★ 登记册 · 9 项）
> **辅助**：`docs/v7-skip-batch-submission-20261013.md` · `docs/v7-family-index-20261013.md` · `docs/v7-mechanization-coverage-20261013.md` · `docs/deviation-ledger-20261011.md`（264 条）
> ★★ **本件的职责是【把问题写清楚】，不是替用户决定。** 每节 ⑤ 栏只是本线建议，**裁决权在用户**。
> ★★ **本件不主张任何事项已闭合**（S3 不可自审）。

---

## 阅读前必读（★ 三条）

**① 什么叫「不可判」**：本件里凡是写着 **「未跑 ⇒ 不可判」** 的，意思是**本线没有真跑出原始输出**，因此**不得**被读成「成立」或「不成立」。本线**不用转述冒充证据**。

**② 本件的证据分级**（每节 ② 栏都标了）：

| 标 | 含义 |
|---|---|
| **实测** | 本线本轮真跑了命令，附未编辑原始输出 + 退出码 |
| **只读结构** | 本线真读了源码/配置文本，附行号 + 逐字，**不执行** |
| **未跑 ⇒ 不可判** | 需外部机器 / 需授权 / 需冷启动，本线**没跑**，**不猜** |

**③ ★★ 一个会误导你的环境事实（本线在核验途中发现）**：本工作区有一条 **`com.dsh.cron.git-snapshot` 定时提交**（`launchctl list` ⇒ `- 0 com.dsh.cron.git-snapshot`），**实测每 2–3 分钟自动 commit 一次**（本轮实测提交序列 `c187dcf 01:10:16` → `47790b6 01:13:35` → `70d87f1 01:15:44` → `d6bf8ce 01:17:55`）。
★★ **后果**：开工时 `git status` 报的「有 1 个已修改文件」在 2 分钟后**变成了 0** —— **不是因为没人改，而是因为快照把它提交了**。
⇒ **故「git status 干净」在这个仓里【不能作为「无人改动」的证据】**。本件文末的「不修改既有文件」自查**据此加了口径说明**。

---

## S1 · `drift-scan` 12 项判据零负控（★ 归属不明）

### ① 一句话
有一台「体检仪」每天自动给系统的 12 条通道量体温，**12 条全是绿的**；但**从来没人试过把它弄坏看看会不会变红** —— 所以「全绿」到底是「真健康」还是「仪器死了」，**分不出来**。

### ② 现状证据

**证据 1（实测 · 12 项全绿）** —— 复跑命令：
```
/opt/homebrew/bin/node ~/dsh-plugin-drift-scan/cli.js --json
```
**退出码 = 0**。未编辑原始输出（节录头部 + 逐项判定）：
```json
{"scannedAt":"2026-10-12T17:16:09.836Z","matrixSource":"lib/channel-matrix.json","total":12,"driftCount":0,"rows":[
{"check":"board-local","kind":"endpoint","expected":"http://127.0.0.1:8792","actual":"HTTP 200","drift":false},
{"check":"board-central",... "actual":"HTTP 200","drift":false},
{"check":"sse-8803",... "actual":"SSE hello 已收到（curl 28=流被截断，属预期）","drift":false},
{"check":"bus-8791",... "actual":"HTTP 200 (body含期望串)","drift":false},
{"check":"node-bridge",... "actual":"argv 符合矩阵","drift":false},
{"check":"sync-from-central",... "actual":"进程运行中","drift":false},
{"check":"hb-fwd",... "actual":"job 已加载","drift":false},
{"check":"device-daemon",... "actual":"进程运行中","drift":false},
{"check":"tailscale-direct",... "actual":"对端均 active","drift":false},
{"check":"funnel-public",... "actual":"HTTP 200","drift":false},
{"check":"e2-registry-services",... "actual":"services 在位（9 组件）","drift":false},
{"check":"bus-8791 token 权限","kind":"file-perm","expected":"600","actual":"600","drift":false}]}
```
**★ 口径申报（凡报「0」必附扫过的面）**：`total=12` · `len(rows)=12` · `driftCount=0`。**判据面 = 这 12 个具名 check**，逐字为：
`board-local` · `board-central` · `sse-8803` · `bus-8791` · `node-bridge` · `sync-from-central` · `hb-fwd` · `device-daemon` · `tailscale-direct` · `funnel-public` · `e2-registry-services` · `bus-8791 token 权限`。
**★ 时效注**：`scannedAt` = `2026-10-12T17:16:09.836Z`，本线同期 `date -u` = `2026-10-12T17:16:13Z` ⇒ **差 4 秒 ⇒ 是当场真跑，不是读缓存**（源码 `cli.js` 无缓存分支，已核）。

**证据 2（实测 · 零负控，★ 附阳性对照）** —— 复跑命令与退出码：
```
grep -rn 'negctl\|负控\|negative' ~/.dsh/profiles/web/node_modules/dsh-plugin-drift-scan/lib/*.js
```
**退出码 = 1**（grep 未命中 ⇒ 1）· **命中行数 = 0**。

**★ 扫过的面（明写）**：目录 `~/.dsh/profiles/web/node_modules/dsh-plugin-drift-scan/lib/`，**4 个 `.js` 文件**（`core.js` 9713 B · `gate.js` 1155 B · `index.js` 818 B · `selfcheck.js` 4109 B）+ `channel-matrix.json` 2123 B。**扩展名面 = `.js`**。
**★ 阳性对照（先证明检索能命中已知存在的东西）**：同一条关键词在 `~/dsh-collab/tools` `~/dsh-collab/scripts` 下**命中**（退出码 0），例如 `tools/bus-pending-age.py`、`tools/verify-cld-release.sh`、`tools/k6-partial-guard.py`、`tools/csx-t1-wiring-mutation.py` ⇒ **故上面那个 0 是【真阴性】，不是检索坏了**。

**证据 3（实测 · 插件自带的自检不覆盖这 12 项）** —— `lib/selfcheck.js`（4109 B）**只查包结构**（peer 解析器 / peer `@deepseek-ai/cordis` / peer `@deepseek-ai/dsh-tools` / `type:module`），**不碰那 12 项判据**。（与 D-186 一致；本线逐字读过该文件清单。）

**证据 4（实测 · 归属：★ 与登记册的记载不同，须更正）**
登记册逐字说：「其登记卡 `data/registry/dsh-plugin-drift-scan` **无 owner/作者/属主字段**（★ 现测三字段皆 `None`）」。
本线现测：
```
curl -s …/data/registry/dsh-plugin-drift-scan   ⇒ http_code=404
body = {"detail":"404 = 键写法合法，但该键不存在（≠ 400 写法非法）","error":"not found","key":"data/registry/dsh-plugin-drift-scan"}
```
★★ **那张卡【不存在】** —— 登记册查的键名多写了 `dsh-plugin-` 前缀。
**枚举 `data/registry/` 全命名空间（`total=1287` 键）**，drift 相关命中逐字：
`brief-v2-audit-hash-drift-reanchor-20260910` · **`drift-scan`** · `hr-ruling-value-domain-is-a-type-pollution-drifts-toward-success-20260914` · `rules-ledger-two-representations-drift-20260911` · `xingqiao-recheck-hr-conservation-and-ident-drift-found-20260914`。
⇒ **真正的卡是 `data/registry/drift-scan`**（`http_code=200`），其 `value` 全部字段逐字：
```json
{"doc":"~/dsh-plugin-drift-scan/docs/README.md",
 "form":"dsh 插件 + CLI 双形态（全只读）",
 "industry_basis":"GitOps reconcile 本地版（Flux/ArgoCD 漂移检测，调研 2026-10-02）",
 "location":"~/dsh-plugin-drift-scan",
 "purpose":"通道漂移检测：实测通道配置 vs 期望矩阵，漂移告警（检测与修复分离）",
 "r006_ten":"十项全达标（--lean4-check A-F 全绿 / 真实扫描 9/9 绿）",
 "registered_at_epoch_ms":1790942000000,
 "registered_by":"session-fa1f9150-c949-401f-ba8c-d265f6221676",
 "tool":"drift-scan","type":"r006-tooling","version":"1.0.0"}
```
**★ 三态判**：`owner` / `author` / `maintainer` **三字段确不在卡内** ⇒ 登记册「三字段皆无」这一句**成立**；
但登记册**给的键名是错的**（404），且 **`registered_by` 这一字段其实有值** = `session-fa1f9150-c949-401f-ba8c-d265f6221676` —— **而那是【第一任星桥】的会话 id**（登记册 §背景与提示词均指本会话语境为「星桥第二任」）。
⇒ ★ **归属的实际状态是：「属主字段无 · 但登记者是一个已不在任的会话 id」** —— **不能据此认定有活体属主**。

### ③ 为什么需要你裁
**★ 归属不明。** 不是技术做不到，是**改别人的件需要知道谁是主人**：
- 补 12 项负控是**收紧类改动**（允许），但落点在 `dsh-plugin-drift-scan` —— **本线不是它的属主**；
- 登记卡**没有 `owner`/`author`/`maintainer`**，只有 `registered_by = session-fa1f9150…`（**第一任的会话，非活体**）；
- `agent_profiles` 的能力登记表里**亦无该插件的属主登记**（登记册语，本线未另行复跑该表）。
⇒ **卡点 =「谁有权批这 12 处改动」这个事实无人可指认。**

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 你直接裁定「本线可改」** | 低（1 轮） | 12 条判据各得一个能造红的输入 ⇒ 「全绿」重新变得可判；★ 但**开了「无属主件由本线改」的先例** |
| **B. 你指认属主后由属主改** | 中（要找到/召回那个人或会话） | 属主责任制完整；★ 但**属主可能已不在任**（`registered_by` 那个会话） ⇒ 可能长期挂起 |
| **C. 本线只交「收紧类建议单」，不动代码** | 低 | 与你已批过的 `docs/drift-scan-tightening-proposal-20261012.md` 同路径；★ 后果 = **判据仍是「全绿而不可判」**，只是留了痕 |
| **D. 不改，但把 12 项在读数上标「未验」而非「绿」** | 极低（改文案） | 至少**不再被读成健康**；★ 但**没有解决「检查全死也不报」** |

### ⑤ 本线建议
★★ **建议 A（你裁定本线可改），并同时采用 D 的标注口径。**
理由：**这 12 项是【通道可用性】的最后一道自动面**，而它现在**结构上无法证明自己活着**。
★ **但必须声明：这只是本线的建议，裁决权在你。** 若你更看重「不越属主」，选 C 同样自洽 —— 代价是这 12 项继续停留在「不可判」。

### ⑥ 不裁的后果
- **不阻塞别的**：S1 不被任何其他项依赖，放着不动不会恶化。
- **但会持续误导**：`drift_scan` **每 30 分钟**跑一轮（launchd `com.dsh.cron.drift-scan`），产出的「12 项全绿」会被后续所有会话读成「通道健康」。**而 D-186 已记：全绿恰恰是它本想防的状态。**
- **恶化风险**：**低但非零** —— 若某条判据悄悄退化成恒绿，**没有任何机制会响**。

### ⑦ 裁完需要什么
- **若选 A**：需要 (i) **一句授权**（「本线可改 `dsh-plugin-drift-scan`」）；(ii) **回滚点** —— 该目录**不在本 git 仓内**（`~/dsh-plugin-drift-scan`），故**须先单独做一份拷贝或 `git init`**，否则**改坏无法回退**；(iii) **改后须跑一次真面看命中率**（D-242 的教训：检查器必先在真面跑）。
- **若选 B**：需要你指认属主；**本线无法代你指认**。
- **若选 C/D**：不需要外部，本线可立即做。

---

## S2 · `bb-upgrade` 通道自举修复（★ 涉升级链路 = 不可逆面）

### ① 一句话
有一支**升级底座自己用的脚本**，它在最后一步「登记本次升级已完成」时，是**对着【正在被升级的那块黑板自己】写**的 —— 而且它写下的「已通过验证」是**一句固定的话**，不是真的测出来的结果。

### ② 现状证据

**证据 1（只读结构 · 落链在第 [7/7] 步）** —— 命令与退出码：
```
sed -n '190,215p' scripts/bb-upgrade.py        # 退出码 0
grep -n 'verify' scripts/bb-upgrade.py         # 退出码 0 ⇒ 唯一命中 :201
```
未编辑原始输出（`:194–:209` 逐字，行号为本线加）：
```
 6    # 7. 落链登记
 7    print("[7/7] 落链登记...")
 8    body = json.dumps({
 9        "item": "blackboard-%s（升级流水线）" % args.vto,
10        "what": args.what,
11        "reuse_grade": grade,
12        "verify": "冒烟全过 + 生产验证",
13        "rollback": "plist 指回 blackboard-server-%s.py" % args.vfrom,
14        "ts": datetime.datetime.now().isoformat(timespec="seconds")
15    }).encode()
16    req = urllib.request.Request(BB + "/data/iterations/upgrade-%s" % args.vto, data=body, method="PUT",
17                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
18    with urllib.request.urlopen(req, timeout=5) as r:
19        print("  ✅ 落链: %s" % r.read().decode()[:60])
```
**★ 三条登记册主张，逐条核**：
- 「落链在第 `[7/7]` 步」 ⇒ **成立**（`:196` 逐字 `print("[7/7] 落链登记...")`）。
- 「`verify` 是冻结串于 `:201`」 ⇒ **成立**（`grep -n 'verify'` 全文件**唯一命中就是 `:201`**，值为字符串常量 `"冒烟全过 + 生产验证"`）。
- 「PUT 到被升级的黑板自己」 ⇒ **成立**：`:67` 逐字 `BB = "http://127.0.0.1:8792"`，而 `:205` 的 PUT 目标就是 `BB + "/data/iterations/upgrade-%s"` —— **`BB` 是硬编码的本机黑板地址**。

**证据 2（实测 · 同文件另有一处真 `.status` 误用，与 S2 同族）**
`tools/false-result-patterns.py` 的 P1 检查**在 `scripts/bb-upgrade.py:77` 命中**（D-242 记「★ 正是【跳过册 S2】那个件 ⇒ 又添一处证据」）。本线**未复跑**该检查器（避免建/跑新件），**照录 D-242 的记载，不冒充本线实测**。

**★ ③ 栏需要的一个关键区分（★★ 本线在此声明一项不可判）**：
登记册与进度表把本件描述为「**通道自举**」。但本线**只读到的**是**落链的目标板**问题（写向自己）+ **verify 是常量**。
**「自举」的具体语义（例如：是否指升级过程中黑板会重启、导致这一步写不进去）本线【未能从源码单独确证】** ⇒
★★ **该语义判「不可判」**，**本线不替它下定义**。（可能与 D-191 那类「归档覆盖板级 `ts`」有关，但**那是推断，不作证据**。）

### ③ 为什么需要你裁
**★ 不可逆面 + 归属/授权。**
- 这脚本**是升级链路本身**：它做「版本递增 → 注入变更 → 起测试实例 → 冒烟 → 切 plist → 验证生产 → 落链」。
- 改它**可能影响在役升级流程** —— 而升级流程**一旦中途出错，不是回滚一行代码就能复原的**（涉及 launchd plist 切换、服务重启）。
- ⇒ **卡点 = 授权 + 必须带回滚点 + 必须先在干跑里验证。**

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 完整修（落链改写到【不被升级的那块板】+ `verify` 改成实测结果）** | **中高**（改升级链路 + 需端到端 dry-run） | 根治；★ 但**改动面最大，最可能伤到在役升级** |
| **B. 最小修（只把 `verify` 常量改成真实冒烟结果，落链目标不动）** | 中（一处改动） | 消掉「假证据」这一半；★ **「写向自己」这一半仍在** |
| **C. 只加护栏（dry-run 时强制打印落链目标板，让人工看见）** | 低（不改逻辑） | **零功能风险**；★ 但**只是让人看见，不解决问题** |
| **D. 不动，只登记** | 零 | 现状保持；★ 违反它**不需做任何事、不报错**（登记册语） |

### ⑤ 本线建议
★★ **建议先做 C（加护栏，零风险），把 A/B 留到你有迁移窗口时再做。**
理由：**本件的危险恰在于「违反了也不报错」** —— 先把「静默违规」变成「可见」，**用最小代价消除最坏的性质（静默）**；而 A/B 触及在役链路，**不宜与本次批量裁决捆绑**。
★ **声明：这只是建议，裁决权在你。**

### ⑥ 不裁的后果
- **不阻塞别的**（S2 无下游依赖）。
- **会持续产生假记录**：每次升级都会往黑板写一条 `verify = "冒烟全过 + 生产验证"` —— **这句是常量，与本次是否真过无关** ⇒ **黑板上积累的升级记录【不可作为验证证据】**。
- **恶化风险**：**中** —— 若将来有人**读这些记录做决策**（例如「上次升级验证过了」），**会被一句常量骗到**。

### ⑦ 裁完需要什么
- **授权**（改升级链路）；
- **★ 回滚点**：登记册明写「改前须有回滚点 + 干跑验证」。`bb-upgrade.py` **在本 git 仓内**（`scripts/`）⇒ 回滚点可由 `git` 承担，**但 plist 与在役服务的状态不在 git 里** ⇒ 还需一份 plist 备份；
- **★ 一个迁移/升级窗口**（因为 dry-run 之外的真跑会切 plist）；
- **外部人**：不需要。

---

## S3 · M8 在役 L1 与计划 L1 不一致（★ 架构级）

### ① 一句话
计划书说「咱们的黑板用 **SQLite 数据库**存，那是最优的」；**可是真正在跑的那块黑板，一个数据库文件都没有** —— 它用的是计划书**自己标成「已废弃」的那种存法**。

### ② 现状证据

**证据 1（实测 · 在役进程）** —— 命令 `ps aux | grep -i rust-blackboard`，**退出码 0**，未编辑原始输出：
```
coreyleung  1221  5.2  4.3 435787264 1078656  ??  S  Thu04AM 1513:15.76 /Users/coreyleung/dsh-collab/rust-blackboard/dist/rust-blackboard-macos-arm64-v0.6.18 --port 8792 --sse-port 8803 --data-dir /Users/coreyleung/dsh-collab/token-monitor/blackboard
```

**证据 2（实测 · 数据目录里没有 `.db`）** —— 命令 `ls -la ~/dsh-collab/token-monitor/blackboard/`，**退出码 0**，未编辑原始输出：
```
-rw-r--r--@  ... 5260148  audit-20261012-19301.jsonl
-rw-r--r--@  ... 5245672  audit-20261012-20102.jsonl
-rw-r--r--@  ... 5244248  audit-20261012-20483.jsonl
-rw-r--r--@  ... 5244729  audit-20261012-21242.jsonl
-rw-r--r--@  ... 5242945  audit-20261012-21550.jsonl
-rw-r--r--@  ... 5244212  audit-20261012-22235.jsonl
-rw-r--r--@  ... 5396663  audit-20261012-22543.jsonl
-rw-r--r--@  ... 5245661  audit-20261012-23324.jsonl
-rw-r--r--@  ... 5243963  audit-20261013-00135.jsonl
-rw-r--r--@  ... 5244498  audit-20261013-00474.jsonl
-rw-r--r--@  ... 2958025  audit.jsonl
-rw-r--r--@  ... 111475073 snapshot.json
-rw-r--r--    12         subs.json
-rw-r--r--    399        subs.json.bak-before-laodeng-probe-cleanup-1789388300
```
**★ 口径申报（凡报「0」必附扫过的面）**：
- **扫过的面** = `~/dsh-collab/token-monitor/blackboard/` 目录下**全部 14 个文件**。
- `.db` 命中：`ls …/blackboard/*.db` ⇒ `No such file or directory`，**退出码 1** ⇒ **0 个**。
- `-wal` 命中：`ls …/blackboard/*-wal` ⇒ `No such file or directory`，**退出码 1** ⇒ **0 个**。
- `.jsonl` 计数：`ls …/blackboard/*.jsonl | wc -l` ⇒ **11 个**。
- **阳性对照**（先证明「找得到 `.db`」不是机器能力问题）：`ls -1 ~/.dsh/*.db` ⇒ **命中 `/Users/coreyleung/.dsh/wecom-inbox.db`**（退出码 0）⇒ ★ **故「黑板目录无 `.db`」是真阴性，不是探针坏了**。
**★ 与 D-199 的差异（如实记）**：D-199 记 `.db = 0 · -wal = 0`、`11 个 JSONL + snapshot.json 106 MB` 且 snapshot `111,135,353 B`。本线现测 `snapshot.json = 111,475,073 B`（**仍 ≈106 MB**）· **JSONL 仍是 11 个**，但**文件名与大小已翻新**（D-199 记的 `audit-20261012-15560/16365` 已不在，现存最早为 `-19301`）⇒ ★ **目录内容在滚动轮换，属正常行为；结论（无 `.db`）不变**。

**证据 3（只读结构 · 计划侧原文）** —— 依 D-199 逐字记载：`v6.1:355` 标题「**3.1 L1 载体：SQLite/WAL 为当前最优**」，`v6.1:359` 表内把 `append-only JSONL 分片` 标为「⚠️ **次优（先前误选，【已废弃】）**」。
★ **本线未重新打开 v6.1 原文逐字核对**（v6.1 在本仓 `docs/distributed-agent-network-governance-plan-v6.1-20261011.md`）⇒ ★ **这一条本线【照录 D-199】，标「未经本线二次核」**。

**★ 三态判**：**不一致【成立】** —— 计划侧说 SQLite 最优/JSONL 已废弃，在役侧实测 **`.db` = 0 而 JSONL = 11**。这是**两条独立面的读数**（进程命令行 + 目录列举），**非单一来源自证**。

### ③ 为什么需要你裁
**★ 架构级 + 涉大体积数据的迁移。** 卡在一个**方向选择**上：
- 要么**改计划**（承认 JSONL 就是在役最优，把 v7 措辞改过来）—— **零数据风险**；
- 要么**改在役**（把 11 个 JSONL + **106 MB 快照**迁进 SQLite）—— **要动在役数据**。
⇒ **这不是本线能单方决定的**：它**改变架构承诺**，且**选后者就进入了不可逆面的迁移窗口**。

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 改计划（v7 措辞改认 JSONL）** | **低**（改一段文字） | 计划与在役一致；★ 代价 = **放弃了 SQLite/WAL 的并发与锁优势**（D-199 表列它「强」），**等于承认现状最优** —— 而**现状是否真最优本线未评**（W5 草稿在评） |
| **B. 改在役（迁 SQLite）** | **高**（动 106 MB 在役数据 + 停/起黑板） | 计划与在役一致，且得 WAL 并发；★ **风险集中**：迁移失败 → **跨设备唯一共享面中断**；★ **须有快照回滚点** |
| **C. 先不改方向，只把不一致【显式化】**（在 v7 写明「在役 = JSONL，与 §3.1 的 SQLite 建议不一致，待裁」） | 极低 | **消掉「静默不一致」**（正是 v7 自足性声明要防的）；★ **不解决**方向问题 |
| **D. 双轨：新面用 SQLite，旧 JSONL 只读保留** | 中高 | 得并发优势且不动历史；★ 代价 = **两套载体长期并存**，**分母/口径复杂度上升** |

### ⑤ 本线建议
★★ **建议 C → 之后择机 A 或 B。**
理由：**「不一致」本身现在是无害的（黑板跑得好好的）；有害的是「没人知道它不一致」**。先用最低代价把它变成显式登记项，**把方向选择留到你有迁移窗口时**。
★ 若你**确定不迁**，直接选 A 更省事 —— 但请一并接受「放弃 SQLite 并发优势」。
★ **声明：这只是建议，裁决权在你。**

### ⑥ 不裁的后果
- **不阻塞别的**（登记册亦记「代价最高，且不阻塞其他」）。
- **会持续误导**：任何读 §3.1 的人（含未来的会话）会以为**黑板跑在 SQLite 上**；**而实际在役的数据面是 JSONL**。若基于此判断「我们有 WAL 并发保护」，**结论会是错的**。
- **恶化风险**：**中** —— `snapshot.json` **已 106 MB 且单文件全量**，**每轮滚动都在长**（本线实测它比 D-199 时又大了 ≈340 KB）。**拖得越久，将来迁移的代价越大。**

### ⑦ 裁完需要什么
- **若选 B**：需要 (i) **授权**；(ii) **迁移窗口**（要停下正在服务的黑板）；(iii) **`snapshot.json` + 11 个 JSONL 的快照回滚点**（**这些不在 git 仓的普通追踪面内** ⇒ 须单独备份）；(iv) **迁移后的等价性核**（键空间 `encodeURI` 编码，`data/ops/` 一类**含非 ASCII 键**，**直接迁名会 404** —— 这一点本线**未测**，标 **不可判**）。
- **若选 A/C**：不需要外部、不需要窗口，本线可做（**但 A 属改锚点本体内容 ⇒ 见 S6 的同一条约束**）。

---

## S4 · 独立 verifier（★ 本机结构上不可得 ⇒ 需外部）

### ① 一句话
规矩说「**自己不能给自己发合格证，得找一个第三方来验**」；**可是这台机器上从操作系统用户到网络所有节点，全是你一个人** —— **找不到一个「不是我们」的人来盖章**。

### ② 现状证据

**证据 1（实测 · OS 用户只有一个）**：
```
$ whoami
coreyleung            # 退出码 0

$ ps aux | grep -iE 'CLD|dsh' | grep -v grep | awk '{print $1}' | sort -u
coreyleung            # 退出码 0 ⇒ 全部相关进程属主【去重后仅 1 个】
```
**★ 口径申报**：面 = **当前时刻所有命令行含 `CLD` 或 `dsh` 的进程**（`ps aux` 全量后过滤），**属主去重 = 1 个**。

**证据 2（实测 · 会话文件属主只有一个）**：
```
$ ls -l ~/.dsh/sessions/ | head -5
total 0
drwx------  526 coreyleung  staff  16832 Oct 13 01:14 --Users-coreyleung--
drwx------    4 coreyleung  staff    128 Aug 15 15:28 --Users-coreyleung-dsh-plugin-local-projects--
```
**★ 口径申报**：面 = `~/.dsh/sessions/` 下**全部工作区目录**，其中 `--Users-coreyleung--` 一个工作区下 **526 项**，**属主全部 `coreyleung`** ⇒ **无第二个 OS 用户**。

**证据 3（实测 · tailscale 四节点同属主）** —— 命令 `/usr/local/bin/tailscale status`（**注意：`tailscale` 不在 `PATH`，`which tailscale` 退出码 1**），**退出码 0**，未编辑原始输出：
```
100.120.203.20   coreymac-mini    coreyleung@  macOS    -
100.118.15.71    desktop-p8e7op1  coreyleung@  windows  active; direct 192.168.1.5:41641, tx 470356579464 rx 16211069928
100.98.251.77    iphone171        coreyleung@  iOS      offline, last seen 7d ago
100.112.111.120  macbook-pro-2    coreyleung@  macOS    active; relay "hkg", tx 10994016 rx 202684
```
⇒ **4/4 节点属主均为 `coreyleung@`** ⇒ **网络层也拿不到第二个「人」。**

**证据 4（实测 · 登记层面确有「第二方」= 外部线 `ext`）**：
```
$ ls -la ~/.dsh/xdom-keys/
-rw-------  1 coreyleung  staff  189 Oct 11 23:05 ext.key
-rw-------  1 coreyleung  staff  189 Oct 11 18:55 int.key
```
⇒ **有 `ext` 与 `int` 两把钥匙** ⇒ 「外部线」**在登记层面存在**。

**★ 三态判**：**「本机结构上不可得独立 verifier」【成立】** —— 三条独立面（OS 用户 · 会话文件属主 · 网络节点属主）**全部指向同一个 `coreyleung`**。
★ **不可判项（如实分开）**：**外部线 `ext` 是否【当前仍在位、可被派单】** —— 本线**未探测 `ext` 的存活**（那需要发消息/占资源） ⇒ **不可判**。登记册记「已用过一次」（`docs/v7-subject-independence-review-20261012-ext.md`，305 行），**本线未打开该件核其时效**。

### ③ 为什么需要你裁
**★ 需外部（并且是结构性的，不是「努力一下就能做到」）。**
- R046/S3 要求 `closed` 必须带**独立** verifier（「起草人/执行人不得自证」）；
- **本机全部面都是同一个人** ⇒ **本机【不可能】满足**；
- 唯一出路是**外部线 `ext`**，而**派出外部线需要你的授权/协调**（本线无权）。
⇒ **卡点 = 这不是技术活，是「谁来当第三方」的组织问题。**

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 派外部线 `ext` 做独立审查** | 低（登记册记「派单即可」，且**已用过一次**） | **真正满足 R046**；★ 且**一项同时解掉 S5**（6 项 verifier）；★ 代价 = 依赖 `ext` 在位 |
| **B. 你裁定「认知独立性即够」，取消第三方要求** | 极低（一句裁定） | 立刻解掉 S4+S5 的结构性卡点；★ **代价 = 放弃了「不可自审」这条防线**，此后**所有自查都算数** |
| **C. 用异构模型/另一套 harness 当「准第三方」** | 中 | 部分独立（**不同模型 ≠ 不同主体**）；★ **须明写这是【降级方案】**，不得冒充 R046 的第三方 |
| **D. 维持现状，所有相关项一律记「不可判」** | 零 | **诚实**；★ 代价 = **大量事项永久停在「不可判」**，**never 可闭合** |

### ⑤ 本线建议
★★ **建议 A（派外部线 `ext`）。**
理由：**一项裁决同时解掉 S4 与 S5**（性价比最高），且**这条路已经走通过一次**（有 305 行的成品审查件），**不是新开路径**。
★ 若 `ext` 已不在位，**退而选 B 并把「取消第三方要求」写成明文规则**（**不要让它悬着**）。
★ **声明：这只是建议，裁决权在你。** —— 特别是 B：**那是一条治理原则的取舍，不该由本线代你定。**

### ⑥ 不裁的后果
- **★ 会阻塞 S5**：S5 的 6 项 verifier **与 S4 同根因** ⇒ **不裁 S4，S5 永久 0/6**。
- **会阻塞一切「闭合」**：台账纪律是**任何 `closed` 必须附独立 verifier** ⇒ **不解决第三方，台账上大量条目【结构上不可能 closed】**，只能长期 `open` / `accepted`。
- **恶化风险**：**低（不会变坏），但也不会变好** —— 这是一个**静止的阻塞**。

### ⑦ 裁完需要什么
- **若选 A**：需要 (i) **你的授权/协调**去派外部线；(ii) **确认 `ext` 在位**（本线未探测 ⇒ 不可判）；(iii) **一份待验清单**（S5 的 6 项 + 其他 `closed_with_evidence` 项）。
- **若选 B**：需要 (i) **一句明文裁定**；(ii) ★ **须同步改写台账纪律**（`deviation-ledger` 首行纪律「凡 `closed` 必须带独立 verifier」）—— **否则规则与实际做法分叉**。
- **外部人**：选 A 需要；选 B/C 不需要。

---

## S5 · 6 项 verifier 真正到位（0/6）

### ① 一句话
有 **6 件事被标成了「已关闭（附证据）」**，**可是每一件的「复核人」栏里都没有真正的人** —— 5 件写着「等第三方来复核」，1 件写着「未验」。

### ② 现状证据

**证据 1（实测 · 逐项列举）** —— 命令与退出码：
```
curl -s http://127.0.0.1:8792/data/registry/continuity-index -o /tmp/dsh-ev-s5.json    # 退出码 0
```
用 Python 解出 `value.items` 中 `state == 'closed_with_evidence'` 的项，**未编辑原始输出**：
```
total items: 10
closed_with_evidence 数: 6
   C1    | verifier= '待第三方复核（本件由外部第三方建立，按 S3「不可自审」须另找复核人；★ 是否维持 closed_with_evidence 由用户裁 —— 见 docs/pending-backlog.md B8/B9/B10 路由…
   C2    | verifier= '待第三方复核（本件由外部第三方建立，按 S3「不可自审」须另找复核人；★ 是否维持 closed_with_evidence 由用户裁 —— 见 docs/pending-backlog.md B8/B9/B10 路由…
   C3    | verifier= '待第三方复核（本件由外部第三方自建，按 S3「不可自审」必须另找复核人）'
   C4    | verifier= '★ **missing**：★ 仅「注入完成」这一子项可证；★★ **生效未验** ⇒ 另立 **C4-b**。★ 依 S3，本项不得重新计为「未做」。'
   C5    | verifier= '待第三方复核（同上，禁自证）'
   R049  | verifier= '待第三方复核（本件由外部第三方建立，按 S3「不可自审」须另找复核人；★ 是否维持 closed_with_evidence 由用户裁 —— 见 docs/pending-backlog.md B8/B9/B10 路由…
```
**★ 口径申报**：面 = `data/registry/continuity-index` 的 `value.items`（**共 10 项**），其中 `closed_with_evidence` = **6 项**（C1/C2/C3/C4/C5/R049）。
**★ 三态判**：
- 「**6 项**」⇒ **成立**（本线独立数得 6）。
- 「**verifier 到位 0/6**」⇒ **成立** —— **6 项里 5 项逐字「待第三方复核」、1 项（C4）逐字 `missing` + 「生效未验」** ⇒ **无一项有真正到位的复核人**。
- ★ **登记册把它拆成「5 个待第三方复核 + 1 个 `★ missing`」** ⇒ **与本线读数逐字一致**（5 + 1 = 6）。

**证据 2（实测 · 工具把这一条单列成 PEND）** —— 命令与退出码：
```
python3 tools/beacon-check.py --net     # 退出码 = 1
```
未编辑原始输出（节录相关两行）：
```
PASS closed 项 verifier 字段齐备（B10③）
PEND closed 项审查员已到位（§11 六者之「审查员」）   << C1/C2/C3/C5/R049 记为 closed_with_evidence，而 verifier 仍是待复核 ⇒ **未验证 ≠ 已关闭**

反遗忘校验：**有红**（2 条 FAIL）（0 条 WARN，1 条 SKIP，1 项待复核）
```
⇒ **工具自己有这条判据，且它判的是 PEND（待复核）而不是 PASS** ⇒ ★ **与 S5 主张一致**。

**★ ③ 栏必须说清的一个【口径分歧】（登记册自己指出的）**：
登记册记：「②`C4` 的分母待裁（`0/6` vs `0/5`）」。
本线现测到的**事实**：
- `continuity-index` 里 **C4 仍记 `state=closed_with_evidence`**（**未被移出 closed**）；
- 但它同时**已另立 `C4-b` 记 `state=open`**（D-201 逐字：`C4-b state=open verifier=None`）。
⇒ **故分母有两个算法**：**`0/6`（C4 仍留在 closed 里，原样）** 与 **`0/5`（把 C4 移出 closed，因为它已拆给 C4-b）**。
★★ **两个分母之下「verifier 到位数」都是 0** ⇒ **结论（0）不随口径变**，但**「分母是几」需要你裁**才能写成一个值。

### ③ 为什么需要你裁
**★ 与 S4 同根因（没有第三方）+ 一个口径分歧（C4 分母）。**
- 主要卡点 = **S4**（本机结构上无独立 verifier）⇒ **本项不能单独解**；
- 次要卡点 = **分母未定**：`0/6` 还是 `0/5`，**这是题面本身的一部分**，**不裁就没法写成一个数**。

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 与 S4 一并派外部线** | 低 | 6 项 verifier 一次性到位 ⇒ **本项从 0/6 变 6/6**；★ 一条裁决解两件事 |
| **B. 裁「C4 移出 closed」⇒ 分母定为 `0/5`** | 极低（一句裁定） | 分母与 D-201 已做的拆分**一致**；★ 须**同步改 `continuity-index` 里 C4 的 state**（否则登记表与口径分叉） |
| **C. 裁「C4 留在 closed」⇒ 分母定为 `0/6`** | 极低 | **保持现状不改数据**；★ 但**须接受「一个 `state=closed_with_evidence` 的项其 verifier 是 `missing`」**（即台账纪律被自身违反） |
| **D. 你裁定降级（见 S4 选项 B），不再要求第三方** | 极低 | 这 6 项**可以立即改记**（不用等外部人）；★ 代价同 S4-B：**放弃不可自审** |

### ⑤ 本线建议
★★ **建议 A（派外部线）＋ B（分母定 `0/5`）。**
理由：**A 解根因**；**B 让「分母是几」这件事不再悬着** —— 因为 **D-201 事实上已经把 C4 拆出去了**（另立 `C4-b`），**登记表却把 C4 留在 closed 里**，**这是一个【内外不一致】的活样本**：**拆了，但没移**。
★ **声明：这只是建议，裁决权在你。** 若你更看重「不动数据」，选 C 也自洽，**但请一并裁定「closed 项可否 verifier=missing」**。

### ⑥ 不裁的后果
- **不阻塞别的**（无下游依赖）。
- **会持续违反台账纪律**：**6 项 `closed_with_evidence` 长期无 verifier** ⇒ 台账自己首行写的「**凡 `closed` 必须带独立 verifier**」**在账面上被持续违反**。
- **恶化风险**：**低** —— 但**分母悬着会让每个引用它的件各写各的**（`0/6` 与 `0/5` 已在不同件里同时存在）。

### ⑦ 裁完需要什么
- **若选 A**：同 S4（需要你的授权 + 确认 `ext` 在位）；+ **6 项的具体交付物清单**（每项的「证据指针」可解 —— `beacon-check` 实测 `C1..C5/R049 证据指针可解` 全 PASS ⇒ **待验材料是齐的**）。
- **若选 B**：需要**改动 `data/registry/continuity-index`**（把 C4 的 state 改为移出 closed）—— ★ **那是本线维护的登记表吗？** ★ 本线**未核该表的属主** ⇒ **若表主不是本线，仍需属主批**。
- **外部人**：选 A 需要；B/C/D 不需要。

---

## S6 · M1 里程碑改记（★ 锚点本体内容）

### ① 一句话
那份**总纲（锚点）里有一条里程碑**，说「自启动注入没做 ⇒ 所以还不算完」；**可是实测那件事【早就做完了】** —— 所以那条里程碑**写错了**，该改成「**不知道**（没测过）」；**而总纲是那份不能随便动的主文件**。

### ② 现状证据

**证据 1（实测 · C4 注入其实已 6/6 完成）** —— 命令与退出码：
```
grep -rl continuity-index ~/.dsh/.agent-presets/        # 退出码 0
```
未编辑原始输出：
```
/Users/coreyleung/.dsh/.agent-presets/librarian/agent.cordis.yml
/Users/coreyleung/.dsh/.agent-presets/resource-manager/agent.cordis.yml
/Users/coreyleung/.dsh/.agent-presets/liangshen/agent.cordis.yml
/Users/coreyleung/.dsh/.agent-presets/audit-reviewer/agent.cordis.yml
/Users/coreyleung/.dsh/.agent-presets/standard-compact/agent.cordis.yml
/Users/coreyleung/.dsh/.agent-presets/waimai-ops/agent.cordis.yml
命中数=6
```
**★ 口径申报（凡报「6/6」必附分母）**：
- **分子面** = 上列 grep 命中的 **6 个** `agent.cordis.yml`；
- **分母面（本线独立核过）**：`ls -1d ~/.dsh/.agent-presets/*/` ⇒ **6 个目录**；`find ~/.dsh/.agent-presets/ -name 'agent.cordis.yml' | wc -l` ⇒ **6 个文件** ⇒ ★ **分子分母都是 6 ⇒ 真的是 6/6，不是「分母取小了」**。
- **mtime**（`ls -l`）：全部为 **`Oct 12 03:08`–`03:09`** ⇒ **与 D-193 记载一致**（在 v6.1 出件之后 28 小时）。

**证据 2（实测 · C4 在登记表里仍是 missing / 未验）** —— 见 S5 证据 1 的 `C4` 行逐字：`★ **missing**：★ 仅「注入完成」这一子项可证；★★ **生效未验** ⇒ 另立 **C4-b**。`

**证据 3（实测 · `C4-b` 仍 open）** —— 依 D-201 逐字（本线见 S5 证据 1 的 `items` 面；`C4-b` 在查询输出内）：
```
C4     state=closed_with_evidence   verifier=★ missing：… 生效未验 ⇒ 另立 C4-b
C4-b   state=open                  verifier=None
```

**★ 三态判（拆成两问，★ 不许合成一个）**：
- **问 1：「C4 自启动注入是否已完成？」** ⇒ ★ **成立**（6/6 注入，**本线实测**）。
- **问 2：「新会话能否因此恢复认知（M0 的谓词）？」** ⇒ ★★ **未跑 ⇒ 不可判** —— **因为测它【必须冷启动一个新会话】**，而**本线在本轮【不能新开会话】**（那会越过本轮的任务边界，且**新会话的恢复效果无法在本轮内被本线观察到**）。D-193 逐字同判：「**谓词已给但本纳未跑**」。

★ **故 M0 的正确状态** = **不是 `open`（因为缺口已补）、也不是「已成」（因为效果没测）、而是 `不可判`** —— **这一点本线据实测【支持】**（注入 6/6 是实测，「效果未测」也是实测的事实）。

### ③ 为什么需要你裁
**★ 改红线（改锚点本体）。**
- v7 **是锚点**：文首逐字「**本件为锚点基线**（连续性信标四件套之①）」，且**它自己的纪律要求「改了正文须同时升 state_version 并重盖章」**（`beacon-check` 实测有这条 PASS 判据）。
- 改它 ⇒ **牵动四件套同步 + 指纹 + 所有引用它的件**。
- **且** M0 的谓词（新会话 ≤5 分钟恢复认知）**需冷启动实测，而实测会新开会话** ⇒ **测它本身是一个有副作用的动作**。
⇒ **卡点 = 「锚点是否即时改」这个治理抉择 + 「是否授权做冷启动实测」。**

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 授权冷启动实测，先拿到 M0 的真读数，再据实改记** | 中（要新开会话 + 人工观察 + 按 D-193 的谓词判 a/b/c 三槽） | **M0 从「不可判」变成有真读数**（成立或不成立）；★ 代价 = **开了新会话**，本身是状态变更 |
| **B. 直接改记 M0 = `不可判`（不做实测）** | 低（改一处文字 + 升 state_version + 重盖章） | 锚点不再写错；★ 代价 = **仍是「不可判」**，**没拿到新知识**，只是**不再谎报** |
| **C. 不改锚点，另出【勘误件】指明 M0 应改记** | 极低（新增一文件） | **不动锚点**（守住「锚点谨慎改」）；★ 代价 = **锚点本体仍是错的**，读它的人**仍会被误导** |
| **D. 不改，维持现状** | 零 | 零风险；★ 代价 = **锚点持续写着「缺口未补」，而实测它已补** |

### ⑤ 本线建议
★★ **建议 B 先行（低成本消除错误陈述），A 另择时做（拿真读数）。**
理由：**「写错了」和「不知道」是两种不同的问题** —— **B 只花一处文字就消灭了「写错」，而 A 需要新开会话这个副作用**。**先消灭确定性错误，再把不确定性留给下一次专门的实测。**
★ 若你倾向「锚点一个字都别动」，**C 是可接受的替代**（并**须把勘误件挂进家族索引**，否则会被遗忘）。
★ **声明：这只是建议，裁决权在你** —— 特别是「锚点可否即时改」**是治理原则，不该由本线定**。

### ⑥ 不裁的后果
- **不阻塞别的**（S6 无下游）。
- **会持续误导**：锚点是**所有会话的起点** ⇒ **每个新会话都会读到「C4 未做 ⇒ M0 的缺口还在」**，**而实测它已补** ⇒ **这恰好复现了 D-193 标题那句「★ 而无任何文档记下」**。
- **恶化风险**：**中** —— 错误在**锚点**上，**传播面最大**（它被「四件套 + 索引 + 台账」多处引用）。

### ⑦ 裁完需要什么
- **若选 B/C**：需要 (i) **你裁定「锚点是否即时改」**；(ii) **若改锚点** ⇒ 须**同步升 `state_version` 并重盖章**（`tools/beacon-check.py --stamp`），**否则会被自己的门判为「改过但未递增」**；(iii) **回滚点**：锚点在 git 仓内 ⇒ `git` 可承担。
- **若选 A**：额外需要 (i) **授权新开会话**；(ii) **D-193 给的谓词**（前 3 条 `agent/message` 内 **a 阶段名 / b 下一步 / c 键名** 三槽全中 + **N2 归因负控**：去掉 C4 段 ⇒ 必须不再说出）；(iii) ★ **须在同一个操作系统用户下做** ⇒ **仍不是独立验证**（受 S4 约束）。
- **外部人**：不需要（但见 S4）。

---

## S7 · 三条新纪律入册（★ `RULES.md` 是共享账本）

### ① 一句话
有人提出了**三条新的工作经验教训**，想写进**团队共用的规则簿**；**而规则簿是大家共享的** —— **往里加东西得先问属主**。

### ② 现状证据

**证据 1（实测 · 三条纪律确实不在账本里）** —— 命令与退出码：
```
grep -n 'D-W4-1\|D-W4-2\|D-W4-3\|_archived_at' rules-registry/RULES.md
```
**退出码 = 1**（未命中）· **命中行数 = 0**。
**★ 口径申报（凡报「0」必附扫过的面）**：面 = **`rules-registry/RULES.md` 单一文件全文**，4 个关键词任意命中即算。
**★ 阳性对照**：同一批关键词在**台账**里**命中**（`docs/deviation-ledger-20261011.md` ⇒ `grep` 退出码 0，命中 `D-W4-1`/`D-W4-2`/`D-W4-3`/`_archived_at` 多行，例如 `:4968`–`:4970` 逐字列出三条） ⇒ ★ **故 RULES.md 那个 0 是【真阴性】：三条纪律确实【只落在台账里，未入规则账本】**。

**证据 2（实测 · 三条纪律的原文，台账 `:4968`–`:4970` 逐字）**：
```
| ★ 它建议的三条新纪律（★ 待裁） | ★ **D-W4-1**：**`_archived_at` ≠ 已处理**；
★ **D-W4-2**：**板级 `ts` 被归档覆盖**（★ 凡按它计龄须同时读内层 `value.ts`）；
★ **D-W4-3**：**本板无段存在原语** ⇒ 须建**板外段登记表**。 |
```
★ 其背景（台账 `:4755` 逐字）：「★★★ **二、归档把红变绿，而 7 条告警一条都没被处理** —— ★ R2 逐字：「同一板态：不带 `_archived_at` 过滤 **n=7 ⇒ 红**；带过滤 **n=0 ⇒ 绿**」」。

**证据 3（★★ 实测 · 登记册说的「`rules-integrity.py` 现测 exit=1」【不成立】）** —— 命令与退出码（**连跑两次**）：
```
python3 ~/dsh-collab/scripts/rules-integrity.py > /tmp/out.txt 2>&1; echo $?
run1 exit=0
run2 exit=0
```
未编辑原始输出（末 10 行）：
```
⚠️ 提示 5 项:
   · 行296 非规则小节（分区标题，跳过）: 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）
   · 行449 非规则小节（分区标题，跳过）: 外部来源规则集（映射 · 不占编号 · trae:E*）
   · 行696 非规则小节（分区标题，跳过）: retiredEntries（R041 退役索引 · 数据搬出账本留痕，溯源不悬空）
   · 编号乱序: R047(行419) 出现在 R048(行412) 之后
   · 编号乱序: J38(行159) 出现在 J44(行153) 之后

结论: ✅ 账本通过完整性检查
```
★★ **故登记册那句「`rules-integrity.py` 现测 exit=1」与实测不符** —— **现测 exit=0，账本通过检查**。
★ **三态判**：登记册该句 ⇒ **不成立**（**本线连跑两次均 exit=0，命令与退出码均在管道之前取**）。
★ **但**「`RULES.md` 是共享账本、入册前应先知会属主」这一**判断** ⇒ **不受影响**（那是治理判断，不是读数）。

### ③ 为什么需要你裁
**★ `RULES.md` 是共享账本（跨会话、跨设备的规则总账）。**
- 往里加编号条目，**等于设定了所有会话都要遵守的约束**；
- **且有编号分配问题**：本线实测 `rules-integrity.py` 报「**编号乱序: R047(行419) 出现在 R048(行412) 之后**」与「**J38(行159) 出现在 J44(行153) 之后**」 ⇒ **账本编号已存在两处乱序** ⇒ **再加三条会加剧这个面**；
- ⇒ **卡点 = 归属/授权（谁批新条目）+ 编号纪律（加在哪、怎么编号）**。

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 三条全入 `RULES.md`（编号 + 详情行）** | 低（3 条） | 三条纪律**对所有会话生效**；★ 须**同步首行条数**（`CLAUDE.md` 明写：「★ 2026-10-12 实测：R059/R060 入账时均曾漏同步」）+ **处理编号乱序** |
| **B. 只入第 1 条（`_archived_at` ≠ 已处理），2/3 条继续留台账** | 低 | 入**最普适**的那条（它是一条**读法纪律**）；★ 2/3 条是**板级实现细节**，留在台账更合适 |
| **C. 三条都不入，只在台账留建议** | 零 | 账本不变（零风险）；★ 代价 = **纪律不成文 ⇒ 下一个会话不会读到它**，**D-W4-1 那个坑有复发空间** |
| **D. 先问 `RULES.md` 属主再定** | 低（但需要找到属主） | 程序正确；★ 可能**拖时间**（属主可能不在位） |

### ⑤ 本线建议
★★ **建议 B（只入 D-W4-1，另两条留在台账）。**
理由：**三条的性质不同** ——
- **D-W4-1（`_archived_at` ≠ 已处理）** 是**跨件普适的读法纪律**（「归档 ≠ 处理」），**放在总账里对所有人有用**；
- **D-W4-2（板级 `ts` 被归档覆盖）** 与 **D-W4-3（本板无段存在原语）** 是**特定板实现的细节** ⇒ **放台账更贴切**（台账才是记细节的地方）。
★ 且**入册时务必同步首行条数**（这是 `CLAUDE.md` 明写的已知坑）。
★ **声明：这只是建议，裁决权在你** —— 尤其**若你判断 `RULES.md` 属主不是你本人**，**请选 D**。

### ⑥ 不裁的后果
- **不阻塞别的**。
- **★ 会留下一个已实证的坑**：**「归档把红变绿、7 条告警没人处理」这个形态【已经真实发生过】**（台账 `:4755`）⇒ **不成文 ⇒ 下一个人不知道 ⇒ 可复发**。
- **恶化风险**：**低到中** —— 取决于**板归档行为还会不会发生**（**会的**，`_archived_at` 机制仍在用）。
- ★ **附带**：**编号乱序（R047/R048 · J38/J44）不裁也会一直在**，且**每加新条都会更乱**。

### ⑦ 裁完需要什么
- **授权**：**入册需先知会/取得 `RULES.md` 属主同意**（登记册明写）。
- **落地**：(i) 新增编号条目 + 详情行；(ii) ★ **同步首行 `N 条`**；(iii) **跑 `python3 ~/dsh-collab/scripts/rules-integrity.py` 复核**（**现测 exit=0，是本线实测的基线**）；(iv) **回滚点**：`RULES.md` 在 git 仓内 ⇒ `git` 可承担。
- **外部人**：不需要（除非属主是外部线）。

---

## S8 · `scripts/lock-audit.py` 的真 `TypeError`（★ 归属不明）

### ① 一句话
有一支**查「谁锁着东西没还」的审计脚本**，它假设「加锁时间」是一个数字；**可实测那个字段其实是一个小字典（表）** —— 脚本一旦遇到真数据就**当场崩掉**。

### ② 现状证据

**证据 1（只读结构 · 出错的那一行）** —— 命令 `sed -n '85,95p' scripts/lock-audit.py`，**退出码 0**，未编辑原始输出（`scripts/lock-audit.py` 相对第 85 行起）：
```
85: （空行）
86:    # 1. 当前持有锁检查
87:    for lk in locks:
88:        holder = lk.get("holder", "?")
89:        resource = lk.get("resource", "?")
90:        acquired = lk.get("acquiredAt", 0)
91:        age_h = (time.time() - acquired / 1000) / 3600 if acquired else 0
92:        note = lk.get("note", "")
93:        # 持锁超 24h = 疑似残留（正常任务锁秒级~分钟级）
94:        if age_h > 24:
95:            issues.append({
```
⇒ **第 91 行**把 `acquired` **当作数字除以 1000**。这是**只读证据，不执行**。

**证据 2（★★ 实测 · 真数据上必崩 —— 本线复现）**
**复跑方法（★ 自包含，不引用 `/tmp` 等易失路径 —— 照本仓既有先例 `docs/v5-and-k6-adjudication-request.md` §5 的纪律）**：
因该脚本**把路径硬编码为 `~/.dsh/agent-bus.json`**（`scripts/lock-audit.py:75`，**无 env / 无参数可覆盖**），本线用 **importlib 进程内 monkeypatch** —— ★ **不写、不改任何生产文件**。**把下面整段存为任意路径的 `.py` 后 `python3 <该路径>` 即可复跑**：
```python
import importlib.util, os, traceback
spec = importlib.util.spec_from_file_location(
    "la", os.path.expanduser("~/dsh-collab/scripts/lock-audit.py"))
la = importlib.util.module_from_spec(spec); spec.loader.exec_module(la)

# 正控：真实在役数据（本线实测 locks 为 [] ⇒ 不触发）
print("[正控A 真实在役数据]", la.audit())

# 负控：按 D-232 记录的形态造一份（acquiredAt 为 dict）
orig = la.load_bus
la.load_bus = lambda: {"locks": [{"holder": "session-a190c54c", "resource": "file:x",
                                  "acquiredAt": {"session-a190c54c-1111": 1791815424754}}],
                       "lightLog": []}
try:
    print("[负控 dict-acquiredAt] OK 未崩", la.audit())
except Exception as e:
    print("[负控 dict-acquiredAt] EXC:", type(e).__name__, "->", e)
    traceback.print_exc(limit=2)
finally:
    la.load_bus = orig
```
**执行退出码 = 0**（脚本自身的 `except` 捕获了异常并打印）。未编辑原始输出：
```
[正控A 真实在役数据] OK rc=None issues= 2
[负控 dict-acquiredAt] EXC: TypeError -> unsupported operand type(s) for /: 'dict' and 'int'
Traceback (most recent call last):
  File "/tmp/dsh-s8-repro.py", line 20, in <module>
    r = la.audit()
  File "/Users/coreyleung/dsh-collab/scripts/lock-audit.py", line 91, in audit
    age_h = (time.time() - acquired / 1000) / 3600 if acquired else 0
TypeError: unsupported operand type(s) for /: 'dict' and 'int'
```
★★ **三态判**：
- 「**`acquiredAt` 为 dict 时，第 91 行必抛 `TypeError`**」⇒ ★ **成立**（**本线复现，附完整 traceback 指到 `line 91`**）。
- 「**在【今天的真数据】上必崩**」⇒ ★★ **未跑 ⇒ 不可判** —— **因为本线现测 `locks` 是【空列表】**：
```
$ python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.dsh/agent-bus.json')));print(type(d['locks']).__name__,len(d['locks']))"
list 0
```
⇒ **`locks` 现为 `list`，长度 0** ⇒ **循环体一次都不进** ⇒ ★ **今天跑它不会崩**（正控实测 `OK issues=2`）。
★ **而 D-232 记载的【当时】状态是 `len=1` 且 `acquiredAt` type=dict**：
```
★ locks 数: 1
★★ acquiredAt 类型分布: {'dict': 1}
★ sample = {'session-a190c54c-…': 1791815424754}
```
⇒ ★★ **故正确记法：「崩溃条件成立，但今天在役数据【不再触发它】（锁是空的）」** —— **属「休眠 bug」，不是「已消失」**。**锁一回来就复发。**

**证据 3（实测 · 归属三项判据，★ 其中一项与登记册不同）**
- **① 无登记卡**：登记册记「`data/registry/{dsh-plugin-lock-audit, lock-audit}` 均 404」。本线**枚举 `data/registry/` 全部 1287 键**，`lock` 相关命中逐字为：
  `addendum14-response-absence-and-deadlock` · `approval-queue-lint-blocking-20260914` · `blocker-cleared-check7-fixed-and-20-tools-9of10` · `empty-blockable-domain-is-not-a-fake-gate-laodeng-20260914` · `hr-probe-clock-20260922` · `hr-reply-external-link-structural-block-20260911` · `hr-ruling-stub-verified-and-two-blockers-20260914` · `r006-u6-batch1-tcc-lean4-block` · `stub-blockers-cleared-20260914` · `systemgraph-tls-staged-443-blocked-20260913` · `toolbox-round10-areas-1-and-3-closed-area2-blocked` · `x10-dirty-key-blocked`
  ⇒ ★ **无一与 `lock-audit` 相关**（那些是 `blocked`/`deadlock` 撞词，不是本工具）⇒ ★ **「无登记卡」这一条【成立】**，且**本线用全命名空间枚举加强了它**（不只是试两个键名）。
- **② git 里它在【别人的】批量补课提交里**：D-232 记 `6a4a08b`、`80c12ee`。★ **本线未复跑 git log 核这两个 sha** ⇒ ★ **照录 D-232，标「未经本线二次核」**。
- **③ `docs/lock-audit-README.md` 逐字「本批未改动脚本逻辑」**：D-232 记该 README 写「2026-10-03 存量补课（`r006-retrofit-scripts.js` 生成）」+「**本批未改动脚本逻辑**（只加版本常量与文档）」。★ **本线未打开该 README 逐字核** ⇒ ★ **照录，标「未经本线二次核」**。

### ③ 为什么需要你裁
**★ 归属不明（同 S1 的结构）。**
- 修法**极简单**（D-232 已写好建议：**一处 `isinstance` 判断** ⇒ 登记册记「极低（一处 if）」）；
- **但没有属主**：无登记卡 · 在别人的补课提交里 · README 声明「本批未改动脚本逻辑」 ⇒ **bug 是【原脚本的】，不是补课批引入的，而原脚本已无主**；
- ⇒ **卡点 = 归属，不是难度。**

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 你裁定「本线可改」** | 极低（一处 `if`） | **修掉一个真 bug**；★ 须**配一条负控**（造 `acquiredAt` 为 dict 的样本 ⇒ 必须不崩）—— D-232 已建议 |
| **B. 按 D-232 的「收紧类建议 + 属主批」路径走** | 低，但**要找到属主** | 程序正确；★ **属主可能不存在**（无登记卡） ⇒ **可能长期挂着** |
| **C. 本线在脚本里**只加**防御性判据 + 负控**，不改语义 | 极低 | 同 A，但**改动更保守**；★ 仍是**改了别人的件** |
| **D. 不动，只保留台账建议** | 零 | **休眠 bug 继续休眠**；★ 风险 = **锁一回来它就崩** |

### ⑤ 本线建议
★★ **建议 A（授权本线修，且务必带负控）。**
理由：**这是一处 `if` 修一个真 bug**，**投入产出比全场最高**；而**它现在只是「休眠」而不是「消失」** —— **`locks` 空只是当下状态**（**本线实测 `len=0`**），**总线一忙就会再有锁**。
★ 且**它是一支审计工具**：**审计工具崩了，等于审计面整块消失**（D-232 逐字：「★ 它是一支【审计工具】⇒ 在真实数据上【必崩】」）。
★ **声明：这只是建议，裁决权在你。**

### ⑥ 不裁的后果
- **不阻塞别的**。
- **★ 会在下一次有锁时静默崩掉**：`TypeError` 被 `except` 捕获后**只打印**（实测正控 `issues=2` ⇒ **异常路径不会中断进程**）⇒ ★ **最坏情形不是崩，而是【什么都没报、看起来正常】。**
- **恶化风险**：**中** —— **锁一回来就复发**，**且不会自己好**。

### ⑦ 裁完需要什么
- **若选 A**：需要 (i) **一句授权**（「本线可改 `scripts/lock-audit.py`」）；(ii) **回滚点** —— ★ **它在 git 仓内**（`scripts/`）⇒ `git` 可承担；(iii) **负控**（D-232 已给：造 `acquiredAt` 为 dict 的样本 ⇒ 必须不崩）；(iv) ★ **须在真数据上跑一次看命中率**（D-232 立的纪律：「凡审计工具，必在【真数据】上跑一次」）—— **而今天 `locks=0`，真数据面是空的** ⇒ ★ **须明写「真面暂空，本次只证负控」**，**不得冒充已在真面验证**。
- **外部人**：不需要。

---

## S9 · `research/v7-review-V2/` 仍空（★ 审查面缺）

### ① 一句话
按计划该有一份**「请别人来独立复查」的报告**放在指定目录里；**那个目录现在是空的** —— **派了两次都没人交东西**。**结果那部分内容【只有自己人查过自己】**，而**自己人不能给自己发合格证**。

### ② 现状证据

**证据 1（实测 · 目录确实空，★ 附阳性对照）** —— 命令与退出码：
```
ls -la research/v7-review-V2/            # 退出码 0
find research/v7-review-V2/ -type f | wc -l   # 退出码 0
```
未编辑原始输出：
```
total 0
drwxr-xr-x    2 coreyleung  staff   64 Oct 12 20:42 .
drwxr-xr-x  153 coreyleung  staff  4896 Oct 12 20:47 ..
```
```
0
```
**★ 口径申报（凡报「0」必附扫过的面）**：面 = **`research/v7-review-V2/` 整个子树**，用 `find … -type f`（**含隐藏文件**）⇒ **文件数 = 0**。目录本身存在（`drwxr-xr-x … 64 Oct 12 20:42`，`64` = **空目录的典型大小**），**最后修改时间 20:42**（与登记册记「20:33 派第二次」吻合）。
**★ 阳性对照（先证明 `find` 在同类目录上能命中）**：
```
v7-review-V1:  5
v7-review-V3:  5
v7-review-V4:  5
```
⇒ ★ **同一命令在同族另三个目录各命中 5 个文件** ⇒ **故 V2 那个 0 是【真阴性】，不是 `find` 坏了或路径写错。**

**证据 2（实测 · 门也在报同一件事）** —— `python3 tools/beacon-check.py --net`（**退出码 1**）未编辑原始输出：
```
SKIP 审查/调研目录非空（D-258）   << ★★ 1 个空目录：v7-review-V2 ★ 空 ⇒ 【不可判】（★ 不得读成已审）
```
⇒ ★ **门的态度是 SKIP（不可判），不是 PASS** ⇒ ★ **与登记册「若仍空 ⇒ 明确标【不可判】而非『已审』」的要求一致，且工具已经在这么做了。**

**★ 三态判**：
- 「**`research/v7-review-V2/` 仍空**」⇒ ★ **成立**（实测 0 文件，含隐藏）。
- 「**W1/W2 的审查面因此缺失**」⇒ ★ **成立**（**但须分清**：**缺的是【独立】审查面**，**不是完全没人看过**）。
- ★★ **不可判项（如实分开）**：「**W1/W2 是否真的零审查**」⇒ **不是** —— 登记册明写「**W1/W2 已【自查】了 V2 的面**（它们各自替代核查并抓到本线 3 处错），**但【同一主体 ⇒ 不能自证独立】**」⇒ ★ **故准确说法是「有自查、无独立审查」**，**本线未核那 3 处错的具体内容** ⇒ **照录登记册**。

### ③ 为什么需要你裁
**★ 审查面缺 + 两次派单失败 + 需外部（三者叠加）。**
- **不是「还没做」** —— 登记册记：**「★★ 两次的审查代理均【零产出】」（20:33 派第二次，至 22:00 仍 0 篇）** ⇒ ★ **这是【已试两次仍失败】的状态**；
- **而它要审的对象（W1/W2）已经自查过了** ⇒ **再派第三次，成功率与立场都是未知的**；
- ⇒ **卡点 =「继续自派」还是「改走外部」** —— **而派外部（S4）也需要你裁。**

### ④ 可选项
| 选项 | 代价 | 后果 |
|---|---|---|
| **A. 派第三次内部审查代理** | **中**（已试两次均零产出，**这是第三次的边际成本**） | 若成 ⇒ 补上审查面；★ 若再空 ⇒ **第三次失败**，且**仍不是独立主体**（受 S4 约束） |
| **B. 改派外部线 `ext`（与 S4 合并）** | 低–中 | **一次解掉 S4 与 S9**（外部线既能当 verifier 也能做审查）；★ 依赖 `ext` 在位 |
| **C. 明确标【不可判】入册，不再重试** | 零 | **诚实**（登记册自己就主张这条：「若仍空 ⇒ 明确标【不可判】而非『已审』」）；★ 代价 = **W1/W2 永久没有独立审查面** |
| **D. 由本线自己补一份「自查 + 边界声明」** | 低 | **有产出**；★ ★★ **但【同一主体 ⇒ 不构成独立审查】** —— **本件自身就受此限** |

### ⑤ 本线建议
★★ **建议 B（与 S4 合并派外部线）；若外部线不可用，退 C（明确标不可判，不硬凑）。**
理由：**「第三次自派」的期望值已经被两次零产出压得很低**，而**即便成功也不是独立审查**（自派代理与 W1/W2 受同一协调者派出）⇒ ★ **继续自派的边际收益低**。
★ **且「明确标不可判」比「补一份自审冒充审查」好得多** —— **这正是本件文末声明所限的同一件事**。
★ **声明：这只是建议，裁决权在你。**

### ⑥ 不裁的后果
- **不阻塞别的**（W1/W2 内容本身已完成，只是缺独立审查面）。
- **会持续违反「不可自审」**：**W1/W2 处于「已自查、未独立审查」的状态**，若被后续件引用为「已审」，**就会是假的**。★ **好消息**：`beacon-check` **已经在报 SKIP 而非 PASS**（实测）⇒ **这一条【已被机械化挡住】**，不会静默变成「已审」。
- **恶化风险**：**低** —— **机制已经把它标成不可判了**（这是这一项**比其他项安全**的地方）。

### ⑦ 裁完需要什么
- **若选 A**：需要 (i) **派单**（本线可做，但**已失败两次**）；(ii) **明确定义「零产出」的判据**（例如：N 小时内目录仍为空 ⇒ 判失败），**否则第三次仍不可判**；(iii) ★ **须明写「内部代理 ≠ 独立」**。
- **若选 B**：需要 **S4 的同一套授权**（派外部线）。
- **若选 C**：需要 (i) **一句裁定**；(ii) **在各引用处把 W1/W2 标为「已自查 · 无独立审查」**（**防止被读成已审**）；
- **回滚点**：若选 D 产出文件 ⇒ `research/` 在 git 仓内。
- **外部人**：选 B 需要；A/C/D 不需要。

---

# 文末自报（★ 三节 + 一）

## 一、★ 本线跑过的命令与真实退出码

**★★ 纪律声明**：以下**每个退出码都在管道之前取**（`cmd > f 2>&1; echo $?`），**未使用 `timeout`**（macOS 无此命令；本线**全程未用任何超时命令**），`node` 用绝对路径 `/opt/homebrew/bin/node`。

| # | 命令（节录） | 退出码 | 用于 |
|---|---|---|---|
| 1 | `pwd` | 0 | 确认工作目录 |
| 2 | `git status --porcelain`（**开工基线**） | 0 | 输出 ` M scripts/logs/bb-request-watch.out` |
| 3 | `wc -l docs/deviation-ledger-20261011.md` | 0 | 7462 行 |
| 4 | `grep -c '^## D-' docs/deviation-ledger-20261011.md` | 0 | **264** |
| 5 | `wc -l docs/distributed-agent-network-governance-plan-v7-20261012.md` | 0 | **291** 行（★ 非 287） |
| 6 | `wc -l docs/v7-skip-register-20261012.md` | 0 | 39 行 |
| 7 | `grep -o '^\| \*\*S[0-9]\*\*' docs/v7-skip-register-20261012.md` | 0 | **9 项**（S1–S9 全在） |
| 8 | Python 脚本核台账 ID 连续性（`/tmp`） | 0 | min 1 / max 266 / count 264；**缺 D-075、D-191** |
| 9 | `/opt/homebrew/bin/node ~/dsh-plugin-drift-scan/cli.js --json` | **0** | S1 证据 1：`total=12 driftCount=0` |
| 10 | `grep -rl '负控' ~/dsh-collab/tools ~/dsh-collab/scripts`（阳性对照） | **0** | S1 证据 2 对照：命中 |
| 11 | `ls -la ~/.dsh/profiles/web/node_modules/dsh-plugin-drift-scan/lib/` | 0 | S1：4 个 `.js` + 1 个 json |
| 12 | `grep -rn 'negctl\|负控\|negative' …/dsh-plugin-drift-scan/lib/*.js` | **1** | S1 证据 2：**0 命中（真阴性）** |
| 13 | `curl -s -o … -w 'http_code=%{http_code}' …/data/registry/dsh-plugin-drift-scan` | 0 | S1：**404 ⇒ 该卡不存在** |
| 14 | `curl -s -o … -w 'http_code=%{http_code}' …/data/registry/continuity-index`（阳性对照） | 0 | **200 ⇒ 真卡存在** |
| 15 | `curl -s …/data/registry/ \| python3 …`（枚举） | 0 | **total=1287** |
| 16 | `curl -s -o /dev/null -w 'http_code=%{http_code}' …/data/registry/definitely-not-a-real-key-xyz` | 0 | **404**（阴性对照） |
| 17 | `curl -s -o … -w 'http_code=%{http_code}' …/data/registry/drift-scan` | 0 | S1：**200 ⇒ 真卡**（无 owner/author/maintainer） |
| 18 | `sed -n '190,215p' scripts/bb-upgrade.py` | 0 | S2 证据 1（只读） |
| 19 | `grep -n 'verify' scripts/bb-upgrade.py` | 0 | S2：唯一命中 `:201` |
| 20 | `grep -n 'BB' scripts/bb-upgrade.py` | 0 | S2：`:67 BB = "http://127.0.0.1:8792"` |
| 21 | `ps aux \| grep -i rust-blackboard`（过滤后） | 0 | S3 证据 1 |
| 22 | `ls -la ~/dsh-collab/token-monitor/blackboard/` | 0 | S3 证据 2 |
| 23 | `ls -1 …/blackboard/*.db` | **1** | S3：**0 个 `.db`** |
| 24 | `ls -1 …/blackboard/*-wal` | **1** | S3：**0 个 `-wal`** |
| 25 | `ls -1 …/blackboard/*.jsonl \| wc -l` | 0 | S3：**11** |
| 26 | `ls -1 ~/.dsh/*.db`（阳性对照） | **0** | S3：命中 `wecom-inbox.db` |
| 27 | `whoami` | 0 | S4：`coreyleung` |
| 28 | `ps aux \| grep -iE 'CLD\|dsh' \| awk '{print $1}' \| sort -u` | 0 | S4：**仅 1 个属主** |
| 29 | `ls -l ~/.dsh/sessions/` | 0 | S4：属主全 `coreyleung` |
| 30 | `which tailscale` | **1** | ★ **不在 PATH** |
| 31 | `/usr/local/bin/tailscale status` | **0** | S4：**4/4 节点属主 `coreyleung@`** |
| 32 | `ls -la ~/.dsh/xdom-keys/` | 0 | S4：`ext.key` + `int.key` 存在 |
| 33 | `curl -s …/data/registry/continuity-index` + Python 计数 | 0 | S5：**items=10 · closed_with_evidence=6** |
| 34 | `python3 tools/beacon-check.py --net` | **1** | S5（PEND 行）/ S9（SKIP 行） |
| 35 | `ls -1d ~/.dsh/.agent-presets/*/` | 0 | S6：**6 个目录** |
| 36 | `find ~/.dsh/.agent-presets/ -name 'agent.cordis.yml' \| wc -l` | 0 | S6：**6 个文件**（分母） |
| 37 | `grep -rl continuity-index ~/.dsh/.agent-presets/` | **0** | S6：**6/6 命中** |
| 38 | `ls -l ~/.dsh/.agent-presets/*/agent.cordis.yml` | 0 | S6：mtime 全为 `Oct 12 03:08–03:09` |
| 39 | `python3 ~/dsh-collab/scripts/rules-integrity.py > f 2>&1; echo $?` **×2** | **0 · 0** | ★★ S7：**与登记册「exit=1」不符** |
| 40 | `grep -n 'D-W4-…\|_archived_at' rules-registry/RULES.md` | **1** | S7：**0 命中（真阴性）** |
| 41 | `grep -n 'D-W4-…' docs/deviation-ledger-20261011.md`（阳性对照） | **0** | S7 对照：命中 `:4968–4970` |
| 42 | `sed -n '85,95p' scripts/lock-audit.py` | 0 | S8 证据 1（只读，`:91` 即出错行） |
| 43 | `python3 /tmp/dsh-s8-repro.py`（**importlib，不改文件**） | **0** | S8 证据 2：**TypeError @ line 91 复现** |
| 44 | Python 读 `~/.dsh/agent-bus.json` 的 `locks` | **1**（首跑，我把 list 当 dict）| S8：**`locks` 是 `list`** |
| 45 | 同上的修正版 | 0 | S8：**`locks` len = 0**（⇒ 今天不触发） |
| 46 | `ls -la research/v7-review-V2/` | 0 | S9：**空**（`64` 字节目录） |
| 47 | `find research/v7-review-V2/ -type f \| wc -l` | 0 | S9：**0** |
| 48 | 同命令跑 V1/V3/V4（阳性对照） | 0 | S9：**各 5 个文件** |
| 49 | `shasum -a 256` / `md5 -q`（4 个关键件） | 0 | ★ 见「二、限制」与「四、差异」 |
| 50 | `wc -l docs/v7-adjudication-dossier-20261013.md`（**写完自查**） | 0 | 见报告 |
| 51 | `git status --porcelain`（**收工**） | 0 | **0 行**（★ 见下方口径说明） |

**★ 两个首跑失败（如实记）**：
- **#44**：本线首版 Python 把 `locks` 当 `dict` 用 `.items()` ⇒ `AttributeError: 'list' object has no attribute 'items'`，**退出码 1**。**修正后**得 `list len=0`。★ **如实记：这是本线的一次探针故障，不是被检对象的缺陷。**
- **#13 相关**：本线**起初照登记册的键名**去查 `data/registry/dsh-plugin-drift-scan`，得 404；**改查枚举结果里的 `data/registry/drift-scan` 才得 200**。★ **过程如实记如上。**

## 二、★ 本线的限制（没核的 · 只能靠推理的）

**★★ 以下事项本线【没有核】，照录他人记载并已逐条标注：**
1. **`bb-upgrade.py` 的「通道自举」语义** —— 本线只核到「落链写向自己」+「`verify` 是常量」两件；**「自举」到底指什么，本线未从源码确证** ⇒ **标不可判，不替它下定义**。
2. **`v6.1:355/359` 的逐字原文**（S3 计划侧）—— **照录 D-199**，本线**未重新打开 v6.1 核对**。
3. **`scripts/bb-upgrade.py:77` 的 P1 命中**（S2）—— **照录 D-242**，本线**未复跑 `false-result-patterns.py`**（避免建/跑新件）。
4. **D-232 的两条 git/README 判据**（S8 归属 ②③）—— **照录**，本线**未核 `6a4a08b`/`80c12ee`，未打开 `docs/lock-audit-README.md` 逐字**。
5. **`ext`（外部线）当前是否在位**（S4/S9）—— **本线未做任何存活探测**（那会发消息/占资源）⇒ **不可判**。
6. **`continuity-index` 这张表的属主**（S5 选项 B 的落地前提）—— **本线未核**。
7. **W1/W2 自查时抓到的那 3 处错的具体内容**（S9）—— **照录登记册**，**未核**。
8. **`agent_profiles` 里是否真的没有 drift-scan 属主**（S1）—— 登记册这么说，**本线未复跑该表**。
9. **S3 的「迁移后会 404」（非 ASCII 键编码）** —— 本线**未测**，**在文中已明标不可判**。
10. **台账 D-075 / D-191 的【内容】** —— 本线只能证明**编号缺失**与**文本里被引用过**；**内容去了哪里本线不知道**（**不猜**）。

**★ 本线只能靠推理的部分（不冒充实测）：**
- S1 ③ 栏「谁有权批」的推理（**基于「无属主字段 + `registered_by` 是已离任会话」这两个实测事实**）；
- S3 ④ 栏「放弃 SQLite 并发优势」的后果推演（**基于 D-199 转述的表**，**非本线实测**）；
- 各项 ⑥ 栏的「不裁后果」**全部是推演**（**本线无预测能力，未做任何实验**）。

**★ 覆盖面的边界（本线明确没扫的地方）：**
- 本线**没有**扫 `devices/` · `~/dsh-plugin-*/`（除 S1 那一个插件的 `lib/`）· `~/dsh-plugin-*/` 全部 · `erp-workspace/`；
- 「本机是否存在第二方」这一条，**本线的面是**：`whoami` · 所有含 `CLD`/`dsh` 的进程 · `~/.dsh/sessions/` 全部工作区 · `tailscale status` 全节点 · `~/.dsh/xdom-keys/`。★ **面外的东西本线不主张。**

## 三、★★ 声明：本件【不构成独立审查】

**★★★ 本线（待裁事项整理代理）与撰写本锚点及 v7 家族各件的，是【同一主体】—— 同受「星桥第二任」协调者派出。**
⇒ 因此：
1. ★ **本件不能自证独立**；
2. ★★ **本件不构成对 v7 家族任何件的独立审查**，**包括 S9 所缺的那份审查**；
3. ★ **本件对 S4/S5 的处置，【不能】算作「第三方 verifier 已到位」** —— 那恰恰是 S4 说要解决的问题，**本线自身就是被它排除的那一类主体**；
4. ★ 本件 ⑤ 栏全部是**建议**，**没有一条具有裁决效力**；**裁决权在用户**；
5. ★ 本件**不主张任何事项已闭合**（S3）。

## 四、★ 本线发现的【登记册与实际的差异】（★ 只报，不代改）

**★★ 纪律声明**：本线**未修改任何既有文件**（**含登记册本身**）—— 差异**如实列出，供你决定是否修订**。

| # | 出处 | 它写 | 本线实测 | 判定 |
|---|---|---|---|---|
| **1** | `docs/v7-family-index-20261013.md:15` · `:16` · `:95` | 跳过册是 «**8 项**» | 登记册表格**实有 9 项**（`grep -o '^\| \*\*S[0-9]\*\*'` ⇒ 9 行：S1 S2 S3 S4 S5 S6 S8 S9 S7） | ★ **「8 项」不成立**（★ 登记册**自身标题**写「共 **9** 条」，与表格一致） |
| **2** | `docs/v7-skip-batch-submission-20261013.md:5` · `:16` | «★ 现状：可做项已全部做完；**剩下 8 项**全在此页» | 该页表格**实有 9 行**（S1 S2 S3 S4 S5 S6 S7 S9 S8） | ★ **「8 项」与自己的表格矛盾**（★ **表 9 行、文写 8 项**） |
| **3** | `docs/v7-skip-register-20261012.md:21` 等 | «`rules-integrity.py` **现测 exit=1**» | `python3 scripts/rules-integrity.py` **连跑两次均 exit=0** · 末行逐字 `结论: ✅ 账本通过完整性检查` | ★★ **不成立**（**命令与退出码均在管道之前取**） |
| **4** | `docs/v7-skip-register-20261012.md:13` | «其登记卡 `data/registry/dsh-plugin-drift-scan` **无 owner/作者/属主字段**（★ 现测三字段皆 `None`）» | 该键 **404（不存在）**；**真卡是 `data/registry/drift-scan`**（200） | ★ **键名错**；★ **「三字段皆无」这一句本身仍成立**（真卡确无 `owner`/`author`/`maintainer`）；★ **但 `registered_by` 有值**（`session-fa1f9150-…`）⇒ **「有登记、无属主」比「三字段皆 None」更准** |
| **5** | `docs/v7-skip-batch-submission-20261013.md:54` | «台账 **235 条**» | `grep -c '^## D-'` ⇒ **264**；台账自身 `:7384` 写 **262**、`:7437` 写 **263** | ★ **三个数互不一致**（235 / 262 / 263 / **实测 264**）⇒ **该行已过期** |
| **6** | `docs/v7-skip-register-20261012.md:3` | «**267 册**» | 登记册表格 **9 项**；**S1–S9 编号连续无缺** | ★ **「267」与本册内容无法对应**（★ **本线不猜它的含义，只报不一致**） |
| **7** | 台账编号 | 声称编号至 **D-266**（`docs/v7-skip-register…` 背景段：现 264 条 · D-001…D-266） | **max=266 · count=264** ⇒ **缺 D-075 与 D-191** | ★ **两条编号无条目**（★ **D-191 有[自证]**：台账 `:4475` 逐字「★ **仅 D-191 未写入**」· `:6911` 分段计数 `D-108–D-191` = **83** 条而该区间有 **84** 个号 ⇒ **台账自己印证了缺 1**；★ **D-075 仅在 `:1296` 被引用为「待产」，无条目**） |
| **8** | `docs/v7-family-index-20261013.md:13` | 锚点 «**286 行** · sha `85ae0f49b3899e57`» | **291 行** · `sha256` 前 16 = **`1e48d0a5520268dd`** | ★ **行数与 sha 均不符** ⇒ **族索引出件（01:10:16）后锚点被改过** |
| **9** | `docs/v7-progress-table-20261012.md:4` | 锚点 «sha256 `03a4fedb…`» | 实测 `sha256` = **`1e48d0a5…`** | ★ **不符**（★ **与 #8 同因：锚点在两份索引出件之后又被改过**） |
| **10** | `docs/v7-family-index-20261013.md:15` · `:16` | 跳过册 sha `8ca3935f7cca9f5a` · 批量呈报 sha `ceec4aec276aafbc` | 实测 `sha256` = **`b1bf922e8e385677`** · **`a0c151882d8057cd`** | ★ **均不符** ⇒ **这两件在族索引出件后也被改过**（★ **行数 39/61 未变** ⇒ **改的是内容，不是行数**） |
| **11** | 台账纪律 vs 台账内容 | 台账每节页脚：«**任何 `closed` 状态必须附独立 verifier**» | **S5 实测：6 项 `closed_with_evidence` 无 verifier**（`beacon-check` 亦判 **PEND**） | ★ **账面与纪律分叉**（★ **已知项，即 S5**；本线只确认其存在） |
| **12** | 环境（**非文件内容**） | «本件只新建一份、不修改既有文件»这一自查**通常用 `git status`** | 本仓有 **`com.dsh.cron.git-snapshot`**，**实测每 2–3 分钟自动 commit** ⇒ **开工时的 1 个 `M` 文件在 2 分钟后变 0** | ★★ **`git status` 在本仓【不能作为「无人改动」的证据】**（★ **见下方口径说明**） |

**★★ 关于 #12 的口径说明（本件「不修改既有文件」的自查）**：
- **开工时**（本轮最早一次）：`git status --porcelain` ⇒ ` M scripts/logs/bb-request-watch.out`（**1 个已修改文件**）。★ **本线未创建也未编辑该文件**。
- **收工后**：`git status --porcelain` ⇒ **0 行**。★ **这不是因为没人改，而是因为 `auto-snapshot`（`d6bf8ce 01:17:55`）把它提交了**。
- **★ 故本线对「不修改既有文件」的主张，依据【不是】`git status` 干净，而是**：
  1. 本线**全部写操作只落在 `/tmp/`**（`/tmp/dsh-*`）与**本件的目标路径** —— `git ls-files --error-unmatch` 实测三者**均不在仓内**；
  2. 本线**未执行任何** `edit` / `write` 指向既有文件的调用；**对既有文件只有 `read` 与 `sed -n` / `grep` / `ls`（全部只读）**；
  3. ★ **但本线必须如实声明一个不可判项**：**本仓在本轮内有【其他会话】在并发写入**（`auto-snapshot` 捕获到「另一会话的在制品」是既有记载），**且快照每 2–3 分钟提交一次** ⇒ ★★ **本线【无法】把「本轮对既有文件的改动」与「其他会话的改动」分离** ⇒ **本线只主张「本线自己的写操作没碰既有文件」，不主张「全仓本轮零改动」。**

**★ 收工 `git status --porcelain` 逐行归因（6 行 · 全部如实列出）**：
```
 M data/j44-reuse-ledger.json          ← ★ 本线跑 J44 门时【工具自己】追加的留痕（见下）
 M scripts/logs/bb-request-watch.err   ← ★ 非本线（后台订阅进程的日志）
 M scripts/logs/bb-request-watch.out   ← ★ 非本线（开工基线里就有它）
 M scripts/logs/blackboard-subscribe.log ← ★ 非本线
 M scripts/logs/event-bus.log          ← ★ 非本线
?? docs/v7-adjudication-dossier-20261013.md  ← ★ 本件（唯一未跟踪新文件）
```
★ **`data/j44-reuse-ledger.json` 那一行的说明（★ 本线主动披露）**：本线按派工要求在建件前跑了
`python3 scripts/j44-reuse-gate.py --intent "…"`（**退出码 0 · 判定 `no-overlap`**）。
★ **该门的实现是「命中 0 条 ⇒ 允许新建**并**把本次意图写入自己的账本」** —— 故那次运行**由工具自身**向 `data/j44-reuse-ledger.json` 追加了一条记录：
```json
{"intent": "写一份 v7 待裁事项裁决案卷文档 docs/v7-adjudication-dossier-20261013.md（把 S1-S9 九项逐项写成七栏可裁问题）",
 "artifact": null, "verdict": "no-overlap", "hits": 0, "note": "", "at": "2026-10-13T01:20:55"}
```
★★ **故严格地说：本线【没有用 `edit`/`write` 改任何既有文件】，但本线【运行的一件既有工具】改了自己的审计账本。** —— **本线不把它藏起来。**

**★ 证据面（`git diff` 直接证明以下五件【本线一字未改】）**：
```
$ git diff --stat docs/deviation-ledger-20261011.md docs/v7-skip-register-20261012.md \
      docs/v7-skip-batch-submission-20261013.md docs/v7-family-index-20261013.md \
      docs/distributed-agent-network-governance-plan-v7-20261012.md
（无输出 · 退出码 0）  ⇒ ★ 台账、登记册、批量呈报、家族索引、**锚点** —— 全部未改
```
★ 且 mtime 亦印证：台账 `2026-10-13T01:13:35`（**早于本件 `01:21:29`**）· 登记册 `01:10:16`（**更早**）。

---

★ 本件不主张任何事项已闭合（S3）。
★ 本件 ⑤ 栏全部为**建议**，**裁决权在用户**。
★ 本件**与锚点撰写者为同一主体 ⇒ 不构成独立审查**。
