# CLD 跨会话跨设备分布式智能体节点网络 · 治理架构管理计划书 v6.1

> **state_version**: 6 ｜ **updated_at**: 2026-10-11T03:48:35+08:00（★ 由 `date` 实读，非估算）
> ★ **本行的更正（第六轮复核 S1-新①）**：初稿曾写 `2026-10-11T03:10:20+08:00`（**那是上一轮 fix2 的时刻**），而本件实际落盘在 `03:28:29`（fix3）⇒ ★ **一个自称「`date` 实读」的字段，值却是上一轮的** ⇒ 已改为实读值。★ **为何这算 S1 而非整洁级**：`updated_at` 正是**下游（续接提示词 / 自启动注入 / §4.6 四件同步）用来判「件是否已更新」的字段**，★ 它失实 ⇒ 下游会把本件读成「仍是上一轮那份」。
> **samples**: 2026-10-10 夜 ~ 2026-10-11 晨（单机 mac-mini），主题族＝「**主线目标定义（用户原话）+ 通讯通道缺陷族 + 假绿族（探针判据缺陷）+ 业界对标**」；★ **v6.1 追加主题族＝「跨会话协作协议族的收编（§18）」**。本计划阈值均以此为样本窗，**引用须连同样本窗一起引**。
> **本文件为锚点基线**（连续性信标四件套之①）· **取代 v6**（`docs/distributed-agent-network-governance-plan-v6-20261011.md`，**冻结为历史，只读不改**）· 并**取代 v5 及更早**
> **起草**: 星桥第二任 `session-e317d6ab-5302-4b33-b095-947983ba16f4` · 经用户 2026-10-11 指令（「修完 15 项必修，再进阶段 2 合并」+「按调研结论给我出那个 meta 角色的落地方案」）
> ★ **verifier: 待第三方复核** —— 本件由起草人自行升版，按 S3「不可自审」**不得由本人裁定成立**；v4/v5 的更正账亦采此署名制。
> ★★ **四件同步状态（★ 必读，防双规范源）**：本件为 v6.1，`state_version = 6`，**取代 v6**；
> ★ **但四件同步【尚未执行】** —— 索引 `data/registry/continuity-index.json` 与 `~/.dsh/continuity-last-version` **在同步前仍指向 v6**。
> ★ **同步的触发条件**：依用户 2026-10-11 裁决的顺序「**更新多一稿 → 再跑评审**」⇒ ★ **同步待本轮第三方复核通过后执行**（外部复核 S2-10 要求明示）。
> ★ **⇒ 在同步完成前，只消费索引的下游（续接提示词、自启动注入）读到的仍是 v6** —— 这**不是**故障，是**已申报的过渡态**。

★★ **备份命名陷阱（第六轮复核 S2-新⑤，★ 如实记）**：`guard/backups/v61-20261011-031020/` 内的 `…v6.1…md` **内容是 v6**（sha `a23ae4d1…`，227,464 B）—— ★ 因为那一台是在 **v6.1 创建后、patch 前**做的备份。
> 　★ **⇒ 若按文件名字面回滚，会退回 v6 并【丢掉整个 §18】**。⇒ 回滚请以 **sha** 判，勿以文件名判。
> ★ **v6 的证据来源与限度**：本版内容由**三条独立审查线**（R1/R2/R3，对抗性，均逐条复跑）+ **四条编辑线**（W1–W4，均非原作者）产出，**全部为本机子代理** ⇒ ★ **均属内部产出，不满足 v5 §4.5 与本版 §5.5 的第三方 verifier 要求**；交付前须补第三方复核。

## ★ 自足性声明（v6 与 v5 的根本差别）

**v5 的诸多章节在本文件内被完整内联，不复用「见 v5 §X」式指针。** 理由与 v5 同（见下），且 v6 另加一条：

1. **承继 v5 的理由**：锚点的唯一用途是**让新会话只读这一份就能恢复认知**（§4.1① + M0）。若锚点把内容留给另一份文件，它就退化成**形态④「标 available 却指不出源」**——而 v5 自身又把它称「历史」，等于**用历史当规范源**，自相矛盾。
2. ★ **v6 新增的理由（本版最重要的一条）**：**用户的目标措辞此前【不在任何锚点、也不在任何 `.md` 里】**（实测：`dsh-collab` 全部 3,2xx 个 `.md` 中「跟得上业界」0 命中）。v6 首次把它**逐字收录**为 §0.1（见该节），从此**目标本身有了规范源**。
⇒ **本文件是唯一规范源**；v5 及更早版本冻结只读 ⇒ **双份漂移不可能发生**。
⇒ 凡 v6 相对 v5 有改动者，均在 §0.0「v5 → v6 更正账」逐条列出；凡未列入者，即为**原样承继**。

---

# §0.0 v4 → v5 更正账（六条）

> 每条附**实测来源**。本账的存在本身即 v4 §4.3「半修防护」的兑现：**升版不自称完美，只自称比上一版更接近事实**。

1. **Wave S 由 `blocked` 改判为「工具面已交付」** —— v4 与 `continuity-index` 均记「只见设计，未见建成证据」；实测 **2026-10-10T03:31 已交付五项工具 + 两项新增门**，且**全部走完 R006 §5 三步**。来源：`docs/wave-s-toolchain-delivery-v1.md`（214 行）+ 七件实体在 `tools/` 逐个 `ls` 核对字节数。
2. **S5 计数更正** —— v4 §10 写「G-CR **十五条**校验脚本」，而其 §7.9 **实列 17 条**（G-CR1…G-CR17）。v5 **按 17 条建档，不为凑数删条**。
3. **§6.1「24h 留证」要求长期失效（既成事实入册）** —— S4 首跑实测：**全机 9 条留证全部过期**，最新 97.4h 前，其余 189–845h。⇒ 补「**留证过期即视为无留证**」。
4. **新增 P27「判据失明族」** —— 反遗忘校验 17 PASS / exit 0，而索引内容已落后交付物、时间戳落在未来、两段自相矛盾。**本版最重要的一条。**
5. **新增 §17「交付规程」** —— 升版四件同步升为规程；钉死**时间戳一律 `date` 读出**。
6. **§15 未决问题重排** —— Q-F 已废（保留改题记录）· Q-K 已批立项（补现状）· **补入 v4 漏载的 Q-M**（`dsh-plugin-excalidraw` 致 CLD 起不来）· 新增 Q-N / Q-O / Q-P / Q-Q。

★ **另有三条**为正文内更正，不单列：§0.1 的「compaction 未挂载」已过期 · §0.2 新增 Wave S 交付清单 · §16 证据索引补可解性标注。

---

# §0.0b v5 → v6 更正账（八条）

> **本账性质**：v5 的更正账（上）**原样保留**（历史基线不动）；本账记 v6 相对 v5 的改动。
> ★ 每条附**实测来源**。本账的存在本身即 §4.3「半修防护」的兑现：**升版不自称完美，只自称比上一版更接近事实**。

1. ★★ **新增 §0.1「主线目标定义」—— 用户目标措辞首次入锚点**。此前该措辞**不在任何锚点、也不在任何 `.md` 里**（实测 0 命中）；唯一载体是会话转录 `session-e317d6ab` 的 `user/message`（`seq=3682614`）。来源：§0.1 的一手载体表 + 复跑命令。
2. ★★ **新增 §7.10「P28 通讯通道缺陷族」**（六条：未登记跃迁方 · 离线投递无撤回且 TTL 执行不确定 · `reply_required` 死字段 · `awaiting` 无消费者 · 失实日志 · 去重粒度错）。来源：`docs/v6-draft-w2-20261010.md`（三条审查线复核后定稿）。
3. ★★ **新增 §7.11「P29 假绿族」**（五处：C7 分母归零 · drift 成功失败分属两 fd · 有界重试计数器重置 · `/health` 空壳 · 健康检查零通讯通道）。来源：`docs/v6-draft-w3-20261010.md`。
4. ★ **新增 §3.4「业界最优性对照」**，并**收窄 v5 的落后层表述**：五项属「**有定义无落地**」（建工具+接调用点），仅**认证授权**属真缺口（写条款）。来源：`docs/v6-draft-w4-20261010.md`。
5. ★ **§13 新增三条规则并按全局账本改号**：`R060 静默失败禁止` · `R061 假绿禁止` · `R062 未登记通道（无通道治理层 owner）`。★ **改号理由**：`rules-registry/RULES.md` 已占用 **R018/R019/R020**（异义），三个号全被占。
6. ★ **§14 改写：M0–M3 补「解除条件」列，并新增 M4 通讯基线** —— v5 的 M0–M3 全部是**进程内/单机**里程碑，**没有一个覆盖「跨会话/跨智能体/跨设备通讯」本身**，而后者恰是 §0.1 的目标原话。
7. ★ **§12 SLO 扩充三面**（通讯面 / 健康面 / 业界面），并确立**同名指标只允许一个宿主节**（「信封符合度」归业界面）。
8. ★ **§10 追加三组 W 项**（W6 通讯 / W7 健康 / W8 演进），**不重编号 v5 既有 39 项**。

★ **另有两条**为正文内更正，不单列：§16 补「旧阶段图 = 历史轴」声明（该图 `mtime == birth == 2026-08-22`、v5 全文「阶段」0 命中）· §17.8 新增「起草前置对表」（由本次踩坑逼出）。

---

## ★ v6 → v6.1 更正账（**三条 + 一条归属更正**）

> ★ **本版只做【收编】，不改判据、不改结论** —— 依据用户 2026-10-11 裁决：「**断点 b 既有协议规划收进锚点，更新多一稿**」。

1. ★★ **新增 §18「跨会话协作协议族」** —— 收编**五份既有活件**的核心条款：**CCEP 永续通讯**（4,508 B）· **黑板值班投递**（2,425 B）· **跨域邮箱 xdom**（9,355 B）· **通讯规范端口**（7,079 B）· ★ **失败可见性体系**（starbridge-v2 §四，96 行）。
   ★ **依据**：2026-10-11 实测「**断点 B · 锚点未收**」—— 这些件在 **v6** 中以**【文件名】口径**实测：`CCEP` **0** · `blackboard-dispatch` **0** · `xdom` **0** · ★ **`agent-comm-portal` = 4** · `starbridge-v2` **1** ⇒ **新会话只读锚点恢复不到**。
   > ★★ **口径更正（外部复核 S1-2，★ 第七轮复核 S3-新⑦ 补充轮次标记：本处为第六轮 S3-新⑦ 的缩进修正对象）**：本行初稿曾写「0 / 0 / 0 / **0** / 1」（第 4 项不实）。★ **根因**：v6 自己在 `:808`/`:2367` 打印过「`docs/agent-comm-portal-20261002.md` : **命中 0 条 / 共 100 行**」—— 那是**【内容关键词】口径**，起草人把它当成**【文件名命中】口径**抄入 ⇒ **同一行混用两种口径**。
   > ★ **讽刺处（如实记）**：紧邻本节新增的「**编辑规程 E1**」正是「**凡给『某字面串计数 = 0』类判据，须先核该字面是否被你要求写入的内容所包含**」—— ★ **起草人立了 E1，又在同一节犯了 E1**。
   ★ **收法**：**内联核心条款 + 标注全文位置**（它们是**活规范件**、非历史锚点 ⇒ 不违反 §17.6 自足性）。
2. ★ **§10 给 `C4 自启动注入` 标注兑现路径** —— 依据用户 2026-10-11 裁决：「**选项 1 兑现 v6 的 c4 这个工作放回 v6 整体按步骤做**」⇒ ★ **不单独施工**，**按 §14 里程碑 + 本节步骤推进**。
3. ★ **§18.6.2 登记独立立项件** —— **MCP 外部接入层**（设计 11,210 B + 架构图 3,296 B）：★ 用户裁决「**4 个评审点【挂起】，但【立项独立做】**」⇒ **其正文 / 进度 / 决策不进本锚点**，仅在 §18.6.2 留一条索引。

★ **本版不新增任何判据**；★ **§1–§17 全部原样承继 v6**（未列入本账者即为原样）。

★ **本条另记一条方法论更新**：**编辑规程 E1** —— 凡给「某字面串计数必须 = 0」类判据，**须先核该字面是否被你自己要求写入的内容所包含**（**三次**同型错误，均由编辑线发现并停下报告）。
> ★★ **归属更正（第六轮复核 S1-新②，★ 如实记）**：
> 　· **该「三次」同型错误发生在【v6 起草期】，不是 v6.1** —— 证据：E1 记录的事件 =「**指令表自身三次自相矛盾**」，其正文在 **§17**（该节**逐字承继自 v6**）。
> 　· ★ **该段原在 §0.0b（v5→v6 更正账）内** ⇒ **本版把它移入 v6→v6.1 账，构成归属错标**（把 v6 的事记到 v6.1 名下）。
> 　· ★ 且**该改动【未列入】原「三条」**，而本节标题曾称「三条」⇒ **账目不全**（本行起标题已改为「三条 + 一条归属更正」）。
> 　· ★ 本节曾自称「**非章节改动**」⇒ ★ **不实**（§0.0b 内容被移动，属章节改动）—— **该措辞已改**。
> 　· ★ **是否本轮新引入**：**否** —— 该形态在上轮被审件（`23f50098…`）已存在，**系上轮遗留 + 上轮复核漏报**。
> 　· ★ **它给出的方法学教训（记入本件供后续引用）**：**「删除行数」与「多重集」两种 diff 判据都对【移动】盲** —— 移动既不改变行数、也不改变多重集。

---


## §0.1 主线目标定义

> **本节性质**：v6 新增节。**唯一权威产的是「用户原话」**，不是本节的任何转述。
> **起草**：W1 线（本件）· **判定日期**：2026-10-10T23:56:25+0800（`date` 实读）
> **纪律**：本节所有引文为**逐字**，所有数字附**复跑命令**；凡我未能核到的，如实标「不可判」，**不折成任何一侧**。

---

### 0.1.1 用户目标措辞（逐字 · 一手载体）

**用户第一人称原话（全句，111 字，逐字）**：

> 按你的说法，这是我们计划目标其中一条分支线，解决的的是上下文问题。但是我们真正的主线目标是让整个 cld 分布式智能体协作网络的跨会话跨智能体跨设备通讯更稳定更健康跟得上业界，也保持领先，这样才对，你安排子代理去考古一下吧

**其中「主线目标子句」（48 字，逐字，本节的目标定义源）**：

> **让整个 cld 分布式智能体协作网络的跨会话跨智能体跨设备通讯更稳定更健康跟得上业界，也保持领先**

**载体（一手，两处，同一 `rpcId`）**：

| # | 文件 | `type` | `seq` | `time`（epoch ms） | 本地时刻（+08:00） | `source.kind` | `rpcId` |
|---|---|---|---|---|---|---|---|
| 1 | `~/.dsh/sessions/--Users-coreyleung--/session-e317d6ab-5302-4b33-b095-947983ba16f4/session.jsonl.zstd` | `user/message` | 3682614 | 1791645930224 | **2026-10-10T23:25:30.224** | `user` | `8fc14793-c3df-443a-ac77-3089a9d4b79a` |
| 2 | 同文件 | `agent/inbox/spliced` | 3668311 | 1791645839495 | 2026-10-10T23:23:59.495 | `user` | 同上 |

副本 `clientTimeZone` = `Asia/Shanghai` ⇒ 上述本地时刻即用户所在时区时刻。

**复跑命令（取一手载体并逐字回印）**：

~~~bash
cd ~/.dsh/sessions
python3 - <<'PY'
import zstandard as zstd, json, io
p='./--Users-coreyleung--/session-e317d6ab-5302-4b33-b095-947983ba16f4/session.jsonl.zstd'
dctx=zstd.ZstdDecompressor()
with open(p,'rb') as fh, dctx.stream_reader(fh) as r:
    tr=io.TextIOWrapper(r,encoding='utf-8',errors='replace')
    for line in tr:
        if '跟得上业界' not in line: continue
        o=json.loads(line)
        if o.get('type')!='user/message': continue
        for it in (o.get('data',{}).get('inserted') or [o.get('data',{})]):
            if it.get('role')=='user' and (it.get('source') or {}).get('kind')=='user':
                print(o['seq'], o['time'], repr(' '.join(c['text'] for c in it['content'])))
PY
~~~

退出码 0；输出即上表第 1 行原话。

---

### 0.1.2 ★ 三处载体之间的措辞差异（**必须写进 v6，否则升版即引入漂移**）

同一目标在三个面上一共有 **三种写法**，只有第一种是逐字原文：

| 面 | 写法（逐字） | 与原文的差异 |
|---|---|---|
| **① 用户原话（权威）** | `让整个 cld 分布式智能体协作网络的跨会话跨智能体跨设备通讯更稳定更健康跟得上业界，也保持领先` | —（基准） |
| ② agent-bus 消息 `bus-mv2jsn1s-g94urelp`（`thread-mv1d8mb2-gu7lizdm`，`time=1791646043824` ⇒ **2026-10-10T23:27:23**，`session-e317d6ab` → `session-0d4aec63`） | `整个 CLD 分布式智能体协作网络的跨会话/跨智能体/跨设备通讯更稳定更健康、跟得上业界也保持领先` | 丢「让」前缀 · `cld`→`CLD` · 三跨间**加 `/`** · 「更健康」后**改顿号 `、`** · 「跟得上业界」后**无逗号** |
| ③ 本任务 prompt 所述措辞 | `让整个 CLD 分布式智能体协作网络的跨会话/跨智能体/跨设备通讯更稳定更健康，跟得上业界，也保持领先` | `cld`→`CLD` · 三跨间**加 `/`** · 「更健康」后**加逗号 `，`** |

**逐位差异（difflib，原文 vs ③）**：

    diff: '- c'  '- l'  '- d'  '+ C'  '+ L'  '+ D'  '+ /'  '+ /'  '+ ，'

⇒ **三面不等**。②③ 都是**规范化改写**，不是逐字。**v6 §0.1 必须以 ① 为准**；②③ 只能作为「载体」被引用，不得作为「措辞」被引用。

---

### 0.1.3 三态声明

**声明 A：v5 未载该措辞 —— ✅ 成立（不是「未核」）**

    $ grep -c '跟得上业界' docs/distributed-agent-network-governance-plan-v5-20261010.md   → 0
    $ grep -c '保持领先'   docs/distributed-agent-network-governance-plan-v5-20261010.md   → 0
    $ wc -l docs/distributed-agent-network-governance-plan-v5-20261010.md                   → 588

扫过的面：v5 全文 588 行整份。v5 定义的是**对象与治理架构**（标题块 `:1` + §1 病理模型），**没有**那句目标措辞。

**声明 B：「任何 `.md` 均未载」—— 实质成立 / 字面已不成立**

    $ cd ~/dsh-collab
    $ find . -name '*.md' -type f -not -path '*/node_modules/*' | wc -l      → 3254
    $ grep -rn '跟得上业界' --include='*.md' . | wc -l                        → 0
    $ grep -rn '保持领先'   --include='*.md' . | wc -l                        → 1

**扫过的面须连数字一起读**（三面，分别打印）：

    A 全仓(含 node_modules/.git): 5964
    B 排除 node_modules:          3254      ← 上报口径
    C 排除 node_modules+.git+.pnpm: 3254
    D git 已跟踪 .md:             2233
    E docs/ 下 .md:                548

★ **`保持领先` 的那 1 处命中，就是本大纲自己**：`docs/mainline-v6-outline-20261010.md:42`（四维枚举行「稳定性 / 健康 / 业界对标 / **保持领先**」）⇒ **自指，不是载**。
★ 口径说明：3254 = 3253 + **本大纲自己**（大纲 10-10 23:50 生成，你引的 3253 是大纲存在之前的读数）⇒ **两个数都对，差在本大纲自己是不是分母**。这与本线已入册的「单位也是坐标系」同族，**引用时须连分母一起引**。

**声明 C：「原文载体是 agent-bus 消息 `bus-mv2jsn1s-g94urelp`」—— ❌ 不成立（该说法不完整）**

转录面实测：**用户侧载体 6 处**，其中**一手 2 处**（`source.kind == "user"`，见 0.1.1 表），**余 4 处是子代理报告的回声**（非用户原话）：

    #1 line=119825 agent/inbox/spliced seq=3668311 time=1791645839495 srcKIND=user  ← 一手
    #2 line=120304 user/message      seq=3682614 time=1791645930224 srcKIND=user  ← 一手
    #3 line=122879 agent/inbox/spliced seq=3764872 srcKIND=subagent-report
    #4 line=122883 user/message       seq=3764876 srcKIND=subagent-report
    #5 line=123704 agent/inbox/spliced seq=3792718 srcKIND=subagent-settled
    #6 line=123727 user/message       seq=3793380 srcKIND=subagent-settled

⇒ **一手载体是会话转录 `user/message`，不是 agent-bus 消息**。bus 消息是**转发**（同为 `session-e317d6ab` 发出，且是**改写后的**顿号版）。二者的关系是「转录原文 → 改写 → 转发」。
★ 转录面**只扫了 `session-e317d6ab` 一件**（★ 该项的完整交代见 §7.11.10「未核清单」及本件 §16 证据索引；★ 原文所引「文末『我没核什么』」一节在本版中不存在，据外部复核 N3 更正）。

**★ 本节自己踩到的那条坑（如实记录）**：我第一遍扫转录时报「0 命中」，**因为 `zstdcat` 未安装**（`bash: zstdcat: command not found`），我把 stderr 用 `2>/dev/null` 丢掉 ⇒ **解压字节数 = 0 ⇒ `grep -c` 恒为 0**，**469 个文件全部如此**。**是正控救了这次判定**：

    $ zstdcat "$f" 2>/dev/null | wc -c     → 0        (假)
    $ which zstdcat                        → (空)     ← 根因
    $ /opt/homebrew/bin/zstd -dc "$f" | wc -c            → 124863735
    $ /opt/homebrew/bin/zstd -dc "$f" | grep -c '星桥'    → 2037     ← ★ 正控通过（★ 此数为【彼时历史值】，现值见本节末的复跑式注）
    $ /opt/homebrew/bin/zstd -dc "$f" | grep -c '跟得上业界' → 48     ← ★ 【彼时历史值】（现值见本节末复跑注；本行保留以存原貌）
    $ /opt/homebrew/bin/zstd -dc "$f" | grep -c '保持领先'   → 51     ← ★ 【彼时历史值】（同上）

⇒ 这正是 §7.11 P29 假绿族①「**分母被过滤成 0 ⇒ 判据恒真**」的**又一次实例，且这次长在本节的判据上**。⇒ **v6 本条须写进 §7.11 作第三个具体形态：「读不到 ≠ 0 条」**。

---

★ **本节三数须以复跑命令取值**（外部复核 N6）：`/opt/homebrew/bin/zstd -dc <会话转录> | { wc -l; grep -c 跟得上业界; grep -c 保持领先; }`；★ 本轮实测：行数 **129942** · 跟得上业界 **280** · 保持领先 **315**（★ 会随会话增长变化）。★ 本条同时补上 v6 缺的**全局纪律**：『凡会随编辑变化的数字一律附复跑命令』**对全文有效**，非逐节自订。

### 0.1.4 目标拆解：四维可判项（每维给可执行判据）

**拆解依据**：原话把目标写成一句话、四个并列项 —— 「更**稳定**」「更**健康**」「跟得上**业界**」「保持**领先**」。四维即原话自身的四个词，**不是我另立的分法**。

#### 维度一 · 稳定性（原话：「更稳定」）

| # | 候选判据（可执行） | 现状读数（附复跑命令） |
|---|---|---|
| S-1 | **每条活体通道都有可复跑探测** ⇒ `drift_scan` 检查项数 ≥ 通道总数 | `drift_scan` → `total=12`；通道侧：`channel_gate` **7 条**（`gate.js:22-30` 逐字：`local-agent-bus`/`board-local`/`board-central`/`bus-8791`/`sse-8803`/`tailscale-direct`/`launchd-daemons`）+ **未登记 ≥1**（见 M4②）⇒ **覆盖不全** ❌ |
| S-2 | **中断的可发现时间 ≤ 1 个巡检周期**（`com.dsh.cron.drift-scan` 每 30 分钟 ⇒ 阈值 **≤60 min**） | 中枢侧告警**最后一次到达**（★ **板级 `ts`**）停在 `2026-10-03T13:27:35+08:00`，冻结 **≈7.5 天**（★ 同一张卡的**内层 `value.ts`** ＝ `2026-10-03T12:30:49.275`，两者差 **56m46s** —— 该差异本身是活体事实，须登记）❌ |
| S-3 | **投递三态可区分且落在输出面**：`delivered` / `queued` / `expired` 必须在**卡面或日志或返回体**可读，`queued` **不得**被呈现为「已发」 | `queued` 真达率 **不可判**（★ 唯一出处为源码注释自述、窗口未载明、修复前口径）；可复现口径＝全量终态分布（★ **以复跑命令取值，不写死数字**；本线两次实测已不同：`delivered 31228 / expired 2377 / queued 8（N=33613）` → `delivered 31229 / expired 2377 / queued 8（N=33614）`）；`expired` **无告警无日志**（见 M4③）❌ |
| S-4 | **无单点**：关键链路任一节点挂掉不得同时带走订阅面 | SSE 8803 与黑板**同进程**（同一 PID 1221）；`bb-sub` **8 个**订阅端随之全断 ❌ |

#### 维度二 · 健康度（原话：「更健康」）

> ★ **H 编号统一（v6 合并时执行）**：本表的 `H-1…H-4` 是 **§0.1 的目标拆解用的临时编号**；v6 已在 **§12 健康面 SLO** 建立**唯一规范序列 `H1–H5`**。映射关系：
> `H-1 假绿数` → **H1** · `H-2 静默失败读者` → **H2** · `H-3 通讯通道检查` → **并入 H2/H3 的判据** · `H-4 双板送达率` → **H3 探针投递率**。
> ⇒ **凡引用一律以 §12 的 `H1–H5` 为准**；本表的旧编号仅为阅读便利保留。


| # | 候选判据（可执行） | 现状读数 |
|---|---|---|
| H-1 | **假绿数 = 0**：凡判据，其**分母为 0 时必须报「不可判」而非 OK**（复现谓词：造空分母 ⇒ **必须红**） | 已具名 ≥3 处（C7 遮蔽扫描 0 包报 OK / drift 跨机 401 只打印成功侧 / 有界重试 822 次恒记 1/3）；**本轮又新增第 4 例**（0.1.3 ★）❌ |
| H-2 | **每条静默失败路径有告警读者** | `launchctl list` 中处于失败终态且无告警通道的任务 ≥8（含 `com.external-link.digest` exit 127）❌ |
| H-3 | **健康检查须覆盖通讯通道** | 现覆盖 **0 条**通讯通道；且 `/health` 是命名空间列举的**假阳性**（`{"total":0}` 空壳）❌ |
| H-4 | **告警送达率**（双板）= 100% | 见 M4①（**现状 6.25%**）❌ |

复跑命令：

    launchctl list | awk '$1=="-"{print}' | wc -l
    launchd_scan

#### 维度三 · 与业界对齐（原话：「跟得上业界」）

| # | 候选判据（可执行） | 现状读数 |
|---|---|---|
| I-1 | **信封符合度**（CAHAC §3 字段级采样） | **0%**（`notes/collab` 全量 **564** 张，复跑命令见 §7.10 的复跑段：`signature` 0/564 · `channel` 0/564 · `priority` 2/564 · `dedup_key` 0/564 …；实际字段是自造 schema `from`/`to`/`subject`/`_via`）❌ |
| I-2 | **四项业界等价物到位**：能力卡+签名 / 任务生命周期 / **认证授权** / 版本协商 | 能力卡 §11 未实现（实际用 `agent_profile`，schema 不同）；邮箱 §7 未实现；错误码 §13 未实现 ❌ |
| I-3 | **协议一致性套件**存在且可跑（非离线脚本） | `scripts/bb-channel.py` 存在但是**离线脚本、不在运行时链路里** ⇒ 定义了没接入 ❌ |

★ **两个口径不得混**（大纲 §三 W2 行的专属判据）：**自报合规率**（`curl -s http://127.0.0.1:8792/data/health/cahac-compliance` 的 `rate_legal` —— ★ **以复跑命令 + 取值时刻记，一律不写死数字**；本线三次实测已各不相同：`0.041909` → `0.046136` → `0.04822 @ver175`（末次 2026-10-11T00:32:12 实测）；量的是**邮箱任务卡 `state` 字段的合法率**）**≠ 信封符合度 0%**。引用时须写出量的是哪个字段。

#### 维度四 · 保持领先（原话：「保持领先」）

★ **判定必须保守**（大纲 §三 W4 行专属判据）。**判据**：

| # | 候选判据（可执行） | 现状 |
|---|---|---|
| L-1 | 只在**同时满足三条**时才记领先：①本机有实现 ②已给出**业界等价物**并说明差在哪 ③有**阴性证据**（写清搜过的词与面，且标「未搜到 ≠ 不存在」） | 候选 **1 项**（保守计数）；**其余各项均落在「落后」或「对齐」** |
| L-2 | 每个「领先」主张须挂一个**可被第三方复跑**的对照实验 | 未建 ⇒ 当前**不可判**，不得记领先 ⚠ |

⇒ **本维度的当前正确表述是**：「**对齐 4 方向 / 落后 6–7 层 / 领先仅 1 项候选且未验证**」——**不是**「已领先」。若 v6 写成「保持领先已达成」，即是把**目标**冒充**现状**。

---

### 0.1.5 四维与里程碑的挂靠

| 维度 | 主挂靠 | 说明 |
|---|---|---|
| 稳定性 S-1/S-2/S-3 | **§14 M4 ①②③** | M4 即「通讯基线」，是稳定性从「目标措辞」落成「判据」的第一次 |
| 健康度 **H1–H5**（旧号 H-1…H-4 已统一，见 §0.1 映射声明）| **§14 M4① + §7.11 P29 + §13 R19** | 假绿入册；H-4 与 M4① 同一读数 |
| 与业界对齐 I-1…I-3 | **§14 M4 之后的 §3.4 / §12 业界面** | **不进 M4**——M4 是通讯基线，不是协议符合度；二者混装会让 M4 无法收敛 |
| 保持领先 L-1/L-2 | **§12 业界面 + §15 开放项 2** | 投入顺序待用户裁；未裁前不得记领先 |

---

**本节一句话**：**用户的目标措辞只以 0.1.1 的 48 字为准；它的一手载体是会话转录，不是 bus 消息也不是任何 `.md`；三面写法互不相同，v6 采原文、其余只作载体引。**

---

# §0 复核结论（既有深度调研 + 能力到位性）

## 0.1 能力到位性（机械复核，判定四态）
✅ **到位**：L2 死形态清理 · L3 TTL/DLQ · 黑板双写+域白名单 · 治理门（验收门/命名门/账本/名册）· **Wave S 五项门工具 + 两项新增门（v5 改判）**。
🟡 **在位未生效或不可观测**：L1 限速（32,634 条消息中 `rateLimited` 仅 **1 次**；无计数无日志）· L4 语义合并（无日志）· `antistorm`（名不副实，仅安全启动守卫一行文案 `index.js:740`）。
🔴 **名不副实或缺失**：去重不持久（实测发送侧真重复 **410 组**）· 黑板**零 GC**（审计 PUT 23,722 / DELETE **0**）· 两个注入器并存 · 无订阅唤醒 · 无 DLQ 重放工具 · **无计划级信标**（v5 已补）· 单会话 **256MB**（本会话历史压缩 **50 次**）· **信标自检存在判据缺口（v5 新增，见 P27）**。
★ **v4 此处曾记「compaction 在 web profile 未挂载（41 项无一项）」—— 该条已过期**：profile `dsh.profile.bundles` 现含 `dsh-plugin-context-survival`（挂载 sha16 `ae922a5ff8ff85d7`，三会话独立确认）。

## 0.2 既有「单文件/键空间无限增长」深调研复核：足够深，且有已建成实现
来源 `research/agent-comm-paths/`（**12,101 行**，十七份 A0/A1–A5/B0/C0/C1/C1a/D0/E0/F0–F2/G0–G3 + L0/L1 + 原始笔记）：
- **纠正问题前提**：不是「单键追加」，而是**键空间无 GC**（实测 snapshot 中 list 型键 **0 个** ⇒ 覆盖式写入；「用新键代替覆盖」≡ 往全局日志追加，而该日志是 keyspace 本身，无 MaxAge/MaxMsgs/compaction/GC）。
- **Q1–Q5 五病灶**（§1）。
- **OOM 完整因果链**（一手日志）与**监控测错对象**。
- **跨来源收敛**：**事件 WAL + 确定性投影**（AG2 已核实 append-only MemoryStream + `TailWindowCompact`；ESAA 一族写侧 append-only / 读侧确定性投影 / agent 只读投影）· **TTL/Lease 是唯一不需共识的回收安全点**（三路独立）· **大对象应外置为引用**（三路独立）。
- **Hearsay-II 两条真经验**（一手核实）：① **焦点机制**（限制「此刻执行什么」，非「存什么」）② **「草稿不入共享区」**——把 parse tree 放黑板被原文定性为 *misuse of the blackboard*，改内部结构后**快两个数量级** ⇒ 我方把 `assistant/chunk` **108,692 条**落进会话正是同一错误。
- **已建成 L1**：`~/dsh-collab/comm-server/agent-mailbox.py` **799 行**（`PRAGMA`×8 · `journal_mode`×10 · `busy_timeout`×3 · `BEGIN IMMEDIATE`×3 · `expires_at`×8 · `claim`×49 · 23 函数），报告 41 PASS、导入 30,755 行/3.97s、幂等重跑 0 新增；SQLite **语言中立已实证**（Rust/Python/Node 并发写同一 DB 400/400，integrity ok）。
- **其自认缺口（照录）**：`audience=[]` 未一手核实 · 「压缩能否真解 OOM」未验证 · 404 会话事件数为**体积外推** · **从未复现崩溃**（因果链是证据推断）。

## ★ 0.3 Wave S 实际交付清单（v5 新增；来源：`docs/wave-s-toolchain-delivery-v1.md` + 实体逐件核对）

| 锚点 | 名义 | 实现（实体在 `tools/`，字节数为实测） | 结构门 | 零变更 |
|---|---|---|---|---|
| **S1** | 沙箱模拟框架 | `sandbox-script.py`（23,760 B）· 补「脚本类四检」之其余 4 项 | 6/6 | ✓（自身即沙箱） |
| **S2** | 信息包模板 | `infopack-check.py`（24,953 B）· 14 项 + 两条硬要求 | 6/6 | ✓ |
| **S3** | 独立审查员逐个审查流程 | `review-gate.py`（26,473 B）· 依据为 **`R048`**（非锚点概述） | 6/6 | ✓ |
| **S4** | 官方规范校对门 | `official-ref-gate.py`（19,376 B）· 封装 `guard_doc_check`（不重造检索能力） | 6/6 | ✓ |
| **S5** | G-CR 校验脚本 | `gcr-gate.py`（33,157 B）· **覆盖 17 条** | 6/6 | ✓（源码无写调用） |
| 增① | 身份声称门 | `node-claim-gate.py`（10,659 B）· + `rules-registry/lean4/node-claim-gate.lean` | 6/6 | ✓ |
| 增② | 自指破坏门 | `self-destruct-gate.py`（23,495 B）· + **`R059`** | 6/6 | ✓ |

**★ 交付方自陈的关键限度（照录，不代其美化）**：
- **S5**：17 条中**机械化 10 条**，其余 7 条标 `N-A` **并注明归属** —— ★ **`N-A` 不是通过**。
- **S4**：`official-ref-gate` 揭出的事实是**全机留证全部过期**；且**它抓到交付方自己的动作**（P3 改插件前无 24h 留证 ⇒ 立即补证）。
- **S3**：`review-gate` **首跑就抓到交付方自己**（把裁判同时登为 executor 与 verifier，R046 明禁）⇒ 已加 `norm_sid` 归一化并移除违规登记。
- **增①**：★ **Lean 文件未实际编译**（本机无 lean 工具链）⇒ 定理的**证明正确性未经机器检验**，只有 `--lean4-check` 的静态对应性；只覆盖「设备归属」一类。
- **增②**：建门过程**自测抓出交付方自己的 7 个缺陷**（全在自测时，非上线后）。
- **全批**：★ **补课（走全 R006 §5 三步）本身抓出 7 个问题** ⇒ 证明这两个开关不是形式。

**★ 待核项（v5 不替其裁决）**：交付说明对 `sandbox-script.py` 同时给出 `--selfcheck` **5/5** 与 `--selftest` **4/4**。经比对 §2 与 §3 上下文，二者**应为不同检查**（`--selfcheck` 属 R006 §5 三步之①，`--selftest` 属自证矩阵），**但 v5 未逐一实跑复核** ⇒ 记为「**未测**」，**不并入任一侧**。

---

# §1 病理模型（Q1–Q5，实测）

| # | 病灶 | 实测 | 本质 | 解法 |
|---|---|---|---|---|
| Q1 | **键只增不减** | 56,439 键 / 累计 DELETE **116** / `data/audit/channel-violations/` 588 键 @1/秒 ×26.7 天 | 键基数失控、无回收路径 | TTL/lease + 周期键改覆盖式 + 大对象外置 |
| Q2 | **写入信噪比极低** | `tasks/i9/results/` 12,891 键中 **12,435（96%）** 为 `ok:true` 且 `output=""` | 缺写前准入/判空 | 焦点机制 + 写前准入 |
| Q3 | **大对象污染 KV** | **19 个 ≥1MB 键 = 全部字节 41%（26.6MB）**，含 1.0–2.3MB PNG 截图 | 缺二进制外置+引用 | 外置为引用（不必换黑板即回收 41%） |
| Q4 | **消息无队列语义** | inbox **1,822 平铺文件**；sessions **1.0GB/413** | 缺分箱/ack/背压/TTL | per-agent inbox 四件套（`queue_size` 满则拒 + `retention_s` + `expires_at` + `since_msg_id`） |
| **Q5** | **会话事件数 ⇒ OOM** | 星桥 **11,777,249 events / 185MB 压缩 / 0.44GB 解压**；compaction 仅跑 **14 次**；`CRASH 67 / SIGKILL 17`（09-09→09-24） | **长度本身**（非噪声） | 挂载 compaction + 约束钉住 + 监控改对象 + 装载前拒绝；中期改投影 |

---

# §2 因果链（含失忆与自设计）

**直接机制**（代码级）：
```
agent_send(from,to,text)   dsh-plugin-agent-bus/lib/index.js:1381
 └─ ① normalizeTo(to):1111 ② 短id前缀解析:1125 ③ 自回声检查(normalizeTo(from)∩normalizeTo(to))
    ④ checkDedup（内存窗口 10 分钟）⑤ store.addMessage:1140 ⑥ persist()（整份 22.8MB；实测三次 `Unterminated string` 撕裂读）
    ⑦ flushQueue() ⑧ deliver → agentsSvc.get(to).followup()   ← 注入完整上下文并唤醒一个回合
```
**放大器**：A1 平方级成本（19 天 26B tokens；`agent_send` 占工具调用 61.8%）· A2 上下文只增不减（某会话 10,701 条中 72% 是碎片/tool 块）· A3 inbox 逐条 splice（160 次）· A4 无订阅唤醒 · A5 两个注入器 · A6 去重不持久 · A7 无熔断无优先级 · A8 治理工具可制造同类问题（08-31 回灌 121 条）· **A9 自设计 + 重启失忆（本会话压缩 50 次）+ 半修被记为已修**。
**根因（08-17 实测原话）**：**「根因不是总线锁，而是上下文膨胀放大了每个会话的处理时间，队列只是结果。」**
**Q5 链条（09-28 一手）**：协调者角色收全网报告 ⇒ 累计 1,178 万事件 ⇒ 装载实例化 ~1,180 万对象 ⇒ 超 V8 堆上限 **4192MB**（pointer compression 硬顶，**调大 heap 无效**）⇒ SIGABRT ⇒ `dsh-crash-after-child` 拖垮 CLD；而监控只看本体（崩溃前 10 分钟本体 RSS 平的 105MB）。

---

# §3 最优性评估

## 3.1 L1 载体：SQLite/WAL 为当前最优
| 候选 | 崩溃安全 | 并发/claim | 语言中立 | 运维重量（1 vCPU/957MB） | 有界手段 | 我们已有 | 判定 |
|---|---|---|---|---|---|---|---|
| **SQLite+WAL（既有 L1）** | 强（WAL+`BEGIN IMMEDIATE`） | 事务级 claim | **已实证** | **零**（嵌入式） | `expires_at`+vacuum/覆盖式 | **799 行+41 PASS** | ✅ **最优** |
| append-only JSONL 分片 | 中 | 弱（需自造锁/claim） | 强 | 零 | 需自造 rotation | 无 | ⚠️ 次优（先前误选，已废弃） |
| NATS JetStream | 强（WorkQueue: first ack removes for everyone，已核实） | consumer ack | 强 | **+1 进程**；★限额默认 unlimited | MaxAge/MaxMsgs+Nats-TTL | 无 | ⚠️ 备选（L2/规模化；**必须显式设限额**） |
| Redis Streams | 中 | XACK+XAUTOCLAIM | 强 | +1 进程 | `MAXLEN ~`/`XTRIM ACKED`（默认不裁） | 无 | ⚠️ 备选 |
| Kafka compaction | 强 | 分区消费 | 强 | 重（JVM） | **体积上界=key 空间** | 无 | ❌ 过重 |
| CRDT | — | — | — | — | **无天赋**（eg-walker：图单调增长） | 无 | ❌ 不解决有界 |

**架构**：L1 设备内（SQLite/WAL，热路径零网络）· L2 跨设备（信封传递，`comm_domains` 前缀单一来源）· L3 服务器（中继+收敛点+健康裁决；**非投递权威**）。

## 3.2 会话（Q5）双层解法
短期 P0：挂载 compaction + **约束钉住**（不先抽约束，压缩后违规率 0%→30%，`arXiv:2606.22528` 已核实）+ 监控改对象 + 装载前拒绝。
中期：会话改**投影**（写侧 append-only、读侧确定性投影、agent 只读投影）。未知项：压缩后是「投影」还是「截断」决定能否恢复会话语义 ⇒ **必须 POC**。

## 3.3 明确不做

## §3.4 业界最优性对照（与 CAHAC v1.2 对表）

> **本节取证边界**（W4 线 · 2026-10-10 夜）
> - **本机侧**：`research/cost-governance/cahac-protocol-v1.2.md`（721 行，实读全文）；活体实测命令与原始输出见各条内嵌。
> - **外部侧**：只采官方规范/官网为一类，二手博客/论文为二类，逐条标注。**「未搜到」一律写作「本轮未发现」，不写作「业界没有」**。
> - **三态**：成立 / 不成立 / **不可判**。数字凡会随编辑变化者，以**复跑命令**代替写死值。
> - ★ **本节的独立更正**（与前序外部调研结论不同者）见 §3.4.6 —— **五处**。
> - ★ **更正账（2026-10-11，编辑线留痕）**：§3.4.3 的 FIPA-ACL 官方 PDF 镜像域名，主机段原**将 `pucpr` 误写作 `pucb`**（`p`↔`b` 之误），**已更正为 `ppgia.pucpr.br`** —— 与本稿「来源清单」中的同一链接（此前即作 `pucpr`）对齐；★ 此更正**留痕**，不静默。

### 3.4.0 先说结论（一句话表）

| 面 | 判定 | 依据强度 |
|---|---|---|
| 一致层（4 方向同向） | ✅ **成立** | 官方规范逐条核过 |
| 落后层 | 成立，但**层数与内涵被前序调研高估**（实为 **6 层 + 1 层半缺**，见 3.4.2） | 官方规范逐条核过 |
| 落后层中的「认证授权最大缺口」 | ✅ **成立**（本机侧仅 agent-id 白名单） | 本机 §10 + A2A/MCP/AIP 三方官方 |
| 领先层 | ⚠️ **仅 1 项候选，且为阴性证据**；「7 类分级」「黑板+邮箱双模」**均不成立** | 阴性证据已显式标注 |
| 已消亡项（ACP / Agent Protocol） | ✅ 成立（ACP 2025-08-29 并入 A2A） | 官方基金会公告 |

---

### 3.4.1 一致层（4 方向）—— 独立复核后**成立**

前序调研给出「4 方向同向」。我逐条核了业界原件的**字段级**，结论**成立**，并补出两处前序未提的**同向细节**。

| CAHAC v1.2 组件（行号） | 业界等价物（官方来源） | 复核结论 |
|---|---|---|
| **§3 统一信封** `:126-148`（14 字段） | MCP `_meta` 逐请求元数据（[MCP Versioning 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)）· A2A Message+Part（[A2A v1.0 spec](https://github.com/a2aproject/A2A/blob/v1.0.0/docs/specification.md)）· CloudEvents 上下文属性（[CloudEvents spec](https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md)） | ✅ **成立**。CloudEvents 必填 4（`id`/`source`/`specversion`/`type`）+ 可选（`subject`/`time`/`datacontenttype`/`dataschema`）—— 与 CAHAC 的 `id`/`ts`/`type` **同构**，CAHAC 的 `cost_cap`/`dedup_key` 为**业界无对应**的增量字段 |
| **§4 消息分类** `:150-162`（7 类型） | A2A 操作集 + 任务状态机 · AG-UI 事件枚举 · FIPA-ACL performatives | ✅ **成立**。★ **补充同向细节**：AG-UI 的 `EventType` 枚举在 commit `1625e70b` 实测 **26 项**（前序调研写「~16」，**偏低**，见 3.4.6-②） |
| **§6 黑板** `:209-235` | A2A Artifacts + `contextId`／任务可见性按调用者作用域 | ✅ **成立**。CAHAC 黑板 `PUT/GET/LIST/SUBSCRIBE/DELETE/AUDIT` `:221-228` 与 A2A `ListTasks`「可见性限定于已认证调用者」（[whats-new-v1](https://a2a-protocol.org/v1.0.0/whats-new-v1/)）同向 |
| **§7 邮箱** `:237-251` | A2A push notification（webhook）· MCP Tasks 轮询 | ✅ **成立**。MCP Tasks 扩展提供 `tasks/get`·`tasks/update`·`tasks/cancel` 三方法与 `pollIntervalMs`（[MCP Tasks ext](https://modelcontextprotocol.github.io/ext-tasks/specification/2026-07-28/tasks.html)）—— 等价于「邮箱+轮询」 |

**一致层的战略含义**：CAHAC **不是另起一套**，而是与三家主流规范的**信封/事件/制品/异步投递**四轴同构 ⇒ 后续对齐**不需要改骨架**，只需补**薄层**。这一点支持 §12 把业界面 SLO 定成「**薄层补齐**」而非「**重构**」。

---

### 3.4.2 落后层 —— 成立，但**内涵需逐层收窄**（前序调研把「有定义、无落地」误写成「缺定义」）

★ 本表是本节**最有裁决价值**的部分：**同一层的修法，在「缺定义」与「有定义无落地」下完全不同**。前者要写规范，后者要建工具+调用点。

| # | 层 | 业界等价物（来源分级） | **CAHAC v1.2 实况（文件:行号）** | 差在哪（精确） |
|---|---|---|---|---|
| ① | **能力卡与可发现性** | A2A Agent Card + `/.well-known/agent-card.json`（[Agent Discovery](https://a2a-protocol.org/latest/topics/agent-discovery/)，遵循 RFC 8615）· v1.0 起 JWS + **RFC 8785** 规范化签名 · MCP Registry（`server.json` + 反向 DNS 命名空间校验，[官方](https://modelcontextprotocol.io/registry/about)）【均官方】 | **★ 有定义**：§11 `:451-463` 已定义 Agent Card（`cahac_version`/`agent_id`/`channels`/`topics`/`budget`/`comm_style`/`capabilities`）。**无实例**：实测 `data/discovery/agents/` 仅 **2 个设备级卡**（mac-mini **9 服务**、mbp **11 服务**），**两卡均无 `cahac_version`** ⇒ 会话/服务级能力卡 **0** | **不是「缺能力卡」，是「缺实例 + 缺发现端点 + 缺签名」**。★ 且 §11 用**广播**下发卡更新（`policy` 类），而 §4 硬规则 `:162` 把广播限 **≤月 5 次** ⇒ **能力发现被自己的频控挤压**（**条款级冲突，本轮实测**） |
| ② | **任务生命周期** | A2A **TaskState 8 态** + 终态/中断态分类 + `isFinal()` + `ListTasks` **游标分页**（[Java SDK TaskState](https://a2aproject.github.io/a2a-java/1_2_0_Final/apidocs/org/a2aproject/sdk/spec/TaskState.html)，官方）【官方】 | **★ 有定义**：§7.2 `:251` 8 值枚举 · §7.3 `:305-323` 转移图 · §12 `:465-480` 状态图。**缺**：**无「终态不可变」条款**；**无任务查询/枚举接口**（§13 `:482-492` 仅 7 错误码，无查询类） | **不是「缺生命周期」，是「缺终态不可变 + 缺查询面」**。A2A 的「终态不再转移」是**硬约束**，CAHAC §12 图里 `timeout`/`verified` 虽指向 `[*]`，但**正文无条款禁止再转移** ⇒ 判据缺口 |
| ③ | ★ **认证授权** | A2A **把身份完全委托 HTTP 层**：明文「**No Identity in Payload**」，凭据走 `Authorization: Bearer` · HTTPS/mTLS · OAuth2/OIDC · PKCE（v1.0 新增 `pkce_required`）· Device Code **RFC 8628**（[Enterprise-Ready](https://a2a-protocol.org/latest/topics/enterprise-ready/)、[whats-new-v1](https://a2a-protocol.org/v1.0.0/whats-new-v1/)）· MCP 走 **OAuth 2.1 + RFC 8707 资源指示符**做受众绑定 + RFC 9728/9207（[MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)）· **IETF `draft-prakash-aip-02`**（2026-10-10 发布）**多跳委托衰减不变式**「no hop widened what it received」，并**明文给出 MCP/A2A/HTTP 三种绑定**（[IETF](https://www.ietf.org/archive/id/draft-prakash-aip-02.html)）【均官方】 | §10 `:444` 认证 = **「sender/recipient 校验（agent-id 白名单）」** · `:445` 授权 = **「黑板 topic 属主制」** · §3 `:144` `signature` **v1.0 可选** · §3 `:148`「signature v1.0 可选（启用时必填）」 | ✅ **最大缺口，成立**。差别**不在「有没有认证」而在「认证锚在什么上」**：A2A/MCP 锚在**可验证凭据**（HTTP 层 + 资源指示符绑定），CAHAC 锚在**自称的字符串 ID** ⇒ `sender` 字段可任意填写。★ **AIP 的衰减不变式直击本机场景**（跨设备/跨会话转派），而 CAHAC 对多跳委派**零条款** |
| ④ | **协议版本协商** | MCP **2026-07-28 已取消 initialize 握手**，改为**逐请求携带版本**（`_meta` + HTTP 头 `MCP-Protocol-Version`），服务器 **MUST 实现 `server/discover`**，错版返回 `-32022 UnsupportedProtocolVersionError` 并**列出 `supported[]`**；A2A 用 **`A2A-Version`** 头 + **按接口各自声明版本**（[MCP Versioning](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)、[whats-new-v1](https://a2a-protocol.org/v1.0.0/whats-new-v1/)）【官方】 | **★ 有声明字段**：§3 `:130` `"cahac":"1.2"` · §11 `:454` `cahac_version` · §16 `:519-524` 版本与演进 + **2 版本弃用过渡期**。**无**：协商流程 · **版本不匹配错误码**（§13 七码中无） | **不是「无版本协商」，是「有声明、无协商、无错版出口」**。MCP 的 `supported[]` 回执是关键设计：**让错版可判别**；CAHAC 无此出口 ⇒ 错版会**静默走 p2p**（§5.3 `:206` 默认安全）⇒ **正是「缺席不可判别」族** |
| ⑤ | **扩展机制** | A2A：扩展走 **URI 命名空间**（版本写进 URI）+ 卡内声明 + 每次调用 `A2A-Extensions` 头激活 + **「扩展不得变更核心 schema 契约 / 重定义核心枚举 / 绕过核心认证」**（[Extension & Binding Governance](https://a2a-protocol.org/latest/topics/extension-and-binding-governance/)，官方；社区页 [agent2agent.info](https://agent2agent.info/docs/topics/extensions/) 表述一致）· MCP：`capabilities.extensions` 映射 + **`_meta` 键命名规则 + 强制前缀**（[MCP Versioning](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)）【官方】 | **★ 有加法演进声明**：§16 `:523`「新增消息类型走 ADDITIVE（不破坏旧通道）」。**无**：URI 命名空间 · **「扩展不得改核心枚举」边界条款** · 无扩展声明字段 | **不是「无扩展机制」，是「只有一句加法承诺，无命名空间、无边界」**。缺边界 ⇒ 扩展可**静默重定义 §7.2 的 8 值枚举**，而 §7.2 判据只管「赋值是否 ∈ 枚举」，**管不到「枚举本身被改」**（同族于该节自陈的 N-19/N-20/N-21 教训） |
| ⑥ | **一致性测试/合规套件** | A2A **官方 TCK**：`a2aproject/a2a-tck`，**按 RFC 2119 分级（must/should/may）**、覆盖 **gRPC/JSON-RPC/HTTP+JSON 三传输**、Gherkin 场景 + `compatibility.json/html` 报告 + CI 接入（[官方仓库](https://github.com/a2aproject/a2a-tck)）· A2A **6 语言 SDK**（Python/Go/JS/Java/.NET/Rust，[官方仓库](https://github.com/a2aproject/A2A)）· MCP Inspector（Web/CLI/TUI 三态，[官方](https://github.com/modelcontextprotocol/inspector)）【官方】 | **★ 有三支条款级自检工具**（`cahac-compliance-report.py` · `comm-invariant-audit.py` · `cahac-clause-ownership-check.py`，后者带 `--selftest` 反例 5/正例 3，§18.2 `:615-619`）。**无**：协议一致性套件 · 无跨实现互操作用例 · **无 must/should/may 分级** | **不是「零测试」，是「有条款级体检、无协议级一致性套件」**。差别在**对象**：现有三支查**本机数据**是否符合条款；TCK 查**实现**是否符合规范 ⇒ **前者无法证明「第三方实现能互通」** |
| ⑦ | **断线恢复语义** | MCP 明确「**不重放，以新 id 重发**」（据前序调研转述为 2026-07-28 规范；★ **本条我未取到该句原文**，列入不确定清单）· A2A `SubscribeToTask` 定义**流重订阅生命周期**与**终态闭流**（[whats-new-v1](https://a2a-protocol.org/v1.0.0/whats-new-v1/)）【官方】 | **★ 事件层有**：§8.3 `:410`「事件日志 append-only；消费者**断点续读（offset 记录）**」= **有重放语义**。**会话层无**：§7.4 `:367-369` 只有容量与 TTL（24h） | ⚠️ **半缺（不可判为主）**。CAHAC 事件层**选的是「重放」（offset 续读）**，与 MCP 的「不重放」**取向相反** —— 二者都不算错，但**本机未声明会话级取值** ⇒ 判 **不可判**，须先成文再定 SLO |

---

### 3.4.3 领先层 —— **保守结论：仅 1 项候选，且属阴性证据**

★ 按要求：**每条先给业界等价物，再说差在哪**。

| 前序候选 | 业界等价物（来源） | 判定 |
|---|---|---|
| **「7 类消息分级」是否领先？** | **FIPA-ACL** 早在 2002 年就有标准化的 communicative act / **performative 库**（[SC00037J 官方 PDF 镜像](https://ppgia.pucpr.br/~fabricio/ftp/Aulas/Mestrado/AS/Aula3/SC00037J_FIPA_Performatives_Spec.pdf) —— ★ **本轮读取被拒（`Unsupported content-type: application/pdf`），未取到原文**，条数为二手）· AG-UI 26 事件 · A2A 操作集 | ❌ **不成立**。**分类维度本身在 2002 年已标准化**；CAHAC 与 FIPA-ACL 的真正差别是**分类之后接了通道选择器**，不是「分了 7 类」 |
| **「黑板+邮箱双模」是否领先？** | A2A **Artifacts + `contextId`**（黑板等价）与 **push notification**（邮箱等价）**同一规范内并存**（[A2A v1.0 spec](https://github.com/a2aproject/A2A/blob/v1.0.0/docs/specification.md)）· MCP 亦同（`_meta` 共享态 + Tasks 轮询） | ❌ **不成立**。**双模并存是业界基线，不是增量** |
| **「把成本权重写进通道选择器」是否领先？** | ① **CWEP / Context Window Economics Protocol**（2026-03-26，**Pre-publication Draft**）已有 **token 计量 · 双边结算 · 上下文定价 · QoS 分层 · 押注式反垃圾**（[白皮书](https://raw.githubusercontent.com/context-window-economics/context-window-economics/main/context_window_economics_whitepaper.md)【二手·草案】）② **BTUP: Best Token Use Path**（成本感知 LLM 推理流量工程，[Zenodo 论文](https://zenodo.org/records/21387024/files/BTUP_paper_v1.1.pdf)【二手·论文】）③ 预算分配路由策略（[dca_theory](https://zenodo.org/records/20819868/files/dca_theory_i.pdf)【二手·论文】）④ 通信效率综述（[Communication-Efficient Networking for Distributed Agentic AI](https://dergipark.org.tr/en/download/article-file/6260059)【二手·论文】）· **A2A 与 MCP 两规范全文均无成本/预算字段** | ⚠️ **唯一候选，且为阴性证据**。<br>**精确表述**：**成本感知**在业界**是活跃方向**（定价/结算/推理路由/预算分配**四类先例齐备**）；而**「把通道权重写进消息类型→通道的选择器」在协议层本轮未发现等价物**。<br>★ **阴性证据显式标注**：检索面 = A2A 规范全文 · MCP 规范全文 · CWEP · BTUP · dca_theory · 通信效率综述；**未系统检索** arXiv 全库 / IEEE-ACM / 企业私有规范。<br>★ **且该候选有一票否决前提**：CAHAC **尚无成本计量与归因落地**（§9.1 用 token、§9.2 用金额，换算靠 §9.2 `:423-431` 自己都标「**须校准**」）⇒ **权重选择器当前是「有表无数据」**。<br>**⇒ 结论：不得在补齐计量前写入「领先」**。 |

**⇒ 领先层净结论**：**本轮未发现 CAHAC 有可靠的领先项**。可诚实表述为——「**在『成本权重入选择器』这一维度上，我们与业界同向但表述形式不同；该判断为阴性证据，须第三方复检，且以成本计量补齐为前提**」。

---

### 3.4.4 已消亡 / 不值得投入（独立复核：**成立**）

| 项 | 结论 | 来源 |
|---|---|---|
| **ACP**（IBM / BeeAI） | ✅ **2025-08-29 并入 A2A**（Linux Foundation · LF AI & Data 官方社区公告）⇒ **不值得新投入** | [LF AI & Data](https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/)【官方】 |
| **Agent Protocol** | 属上一代（前序结论）；★ 本轮**未独立复核**，故标 **不可判**，不入 §3.4 结论 | — |

---

### 3.4.5 本节给 v6 的三条可执行推论

1. **对齐是「补薄层」，不是「改骨架」**（一致层 4/4 成立）⇒ §12 业界面 SLO 的**形态**应为「**同构字段的填充率**」，而非「协议重写」。
2. **落后层的修法分两类，必须分开派工**（3.4.2 表）：**「有定义无落地」类 = 建工具 + 接调用点**（①②⑦）；**「真有缺口」类 = 写条款**（④⑤⑥的部分）。★ **把前者当后者会重复写一遍规范而一行代码不动** —— 这正是 CAHAC §18 自陈的「42 天零落地」（`:611`）的成因形状。
3. **认证是最大缺口但不应先做**（理由见「投入顺序建议」）—— 因为 CAHAC 自身 §18.4 `:641` 已把「**认证被降级抵消类**」登记为缺口族：*§10 白名单 vs §11 无 Card，两个条款互相抵消*。**先有卡才有身份载体**。

---

### 3.4.6 ★ 与前序外部调研的差异（本线独立更正 **五处**）

> 纪律依据：CAHAC §1.5.4 `:108`「**判据不落在命令上，就等于没核**」。凡我更正处，均附复跑命令或文件行号。

| # | 前序结论 | 本线实测 | 证据（命令 + 原始输出 / 文件行号） |
|---|---|---|---|
| ① | 「缺能力卡」 | **有卡定义（§11 :451-463），无实例、无发现端点、无签名**；且 §11 走广播而广播月限 5 次 ⇒ **条款冲突** | `cahac-protocol-v1.2.md:451-463`；`curl -s http://127.0.0.1:8792/data/discovery/agents/` ⇒ 2 卡、mac-mini `services` **9** 项、mbp **11** 项、两卡 `has cahac_version: False` |
| ② | 「AG-UI ~16 事件」 | **该 commit 实测 26 项 `EventType`** | [ag-ui events.mdx @1625e70b](https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/1625e70b/docs/sdk/js/core/events.mdx)（`EventType` 枚举逐项可数） |
| ③ | 「MCP `server/discover`」（作为「有版本协商」的证据） | **2026-07-28 已取消 `initialize` 握手**：改为**逐请求** `_meta` 版本 + 服务器 **MUST** 实现 `server/discover`；错版返回 `-32022` 且**带 `supported[]`** | [MCP Versioning](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) 原文：「There is no negotiation handshake.」 |
| ④ | 「自报合规率 **4.19%**」 | ★ **以复跑命令 + 取值时刻记**（现约 **0.0478** @ver173）；★ **且其 285 条合规条目 100% 来自 3 个历史 JSONL 聚合文件；当前逐条写入路径合规率 = 0.00%** | 见下方「§12 业界面 SLO」的复跑命令与原始输出 |
| ⑤ | 「信封符合度 **0%**」（作为既知基线） | 数值**成立**（实测 `0 / 2949 = 0.0000`），★ **但此前本机无任何测量工具**（`ls scripts/ \| grep -iE 'envelope\|selector'` ⇒ **空**）⇒ **该数字此前不可复跑**，须先建尺 | 见 §12 第 1 行复跑命令 |

> ★ **合规率口径声明（W4-3）**：`LEGAL_STATES` 为 **7 值**，CAHAC §7.2（`:251`）为 **8 值（含 `superseded`）** ⇒ 该工具执行的是 §7.2 的**真子集**；★ 且本稿复跑脚本**原用 8 值**、报告工具用 **7 值** ⇒ 两者**同名不同指标**，**已统一为报告工具的 7 值口径**（脚本 `ENUM` 见 §12-C 的注释）；凡引合规率，一律按**报告工具的 7 值口径**读。

★ **自我更正（2026-10-11，R2 线查出）**：本稿先前把「合规率分母被非 JSON 行灌水」的怀疑判为【不成立】，**该判定错**：① 报告脚本 `cahac-compliance-report.py:164-171` 的 `total += 1` 在 `json.loads()` **之前** ⇒ 非 JSON 行**确实计入分母**；② `verify-watch.json` **不是 JSONL**，是**单个 pretty-print JSON 对象**，其 **11 行逐行全部不可解析**（真 JSONL 是 `collab-inbox.json`/`mac-mini-inbox.json`）⇒ **该 11 行正是被否定的现象本身**；③ 先前引证的三个「逐文件行数」读数（**经 R2 线核，此类字段无任何工具产生** —— 报告脚本 0 命中）⇒ **本次删除该引证**；④ 量级如实：**11 行 / 0.18%，不影响 4.6x% 的结论** —— 错的是**判定与证据**，不是结论。⇒ **该缺陷（虽小）现存，不因本次更正而关闭。**

---


---

## 投入顺序建议（按性价比排序，供用户裁决）

> **性价比 = （闭合缺口的实质增益）÷（改动面 × 依赖数 × 不可逆度）**。

| 序 | 项 | 为什么排这里 | 成本 | 依赖 |
|---|---|---|---|---|
| **1** | **W8.1 先建尺** | ★ **无尺则无基线**，且「信封符合度 0%」**当前不可复跑**。这是 CAHAC 自己 `:108` 的教训（「判据不落在命令上，就等于没核」）。**建尺不改任何写入方 ⇒ 零风险** | **极低**（1 支只读脚本） | 无 |
| **2** | **W8.2 信封注入** | 把**唯一实测 0.00% 的核心指标**从 0 拉起来；改动面**只在写入侧调用点**（CAHAC §7.5 `:360-364` 已把缺口与责任方写明） | 低 | W8.1（需尺验收） |
| **3** | **W8.3 + W8.4 能力卡** | **收益最高的实功能**：直接兑现「可发现性」，且**已有 `data/discovery/agents/` 现成载体可复用**（9+11 服务名已在板上）⇒ **是复用不是新建**；同时**解掉 §4↔§11 的广播配额冲突** | 中 | 无（可与 1/2 并行） |
| **4** | **W8.10 断线恢复语义** | **纯成文、零实现成本**，且直接回答 W2 §7.10 的「离线投递无撤回」——**文字成本换一个不可判→可判** | 极低 | 无 |
| **5** | **W8.7 版本不匹配错误码** | **§13 加一行 + 一个用例**，成本极低；消掉「错版静默走 p2p」这一**空缺不可判别**族实例 | 极低 | 无 |
| **6** | **W8.5 终态不可变 + W8.6 查询面** | 中等成本，但**终态违例检测与 P29 假绿族同构**（都是「判据看不见」）⇒ 顺带加固健康面 | 中 | W8.5 先于 W8.6 |
| **7** | **W8.8 扩展边界条款** | 条款级、低成本；收益偏长期（防「扩展静默改核心枚举」） | 低 | 无 |
| **8** | **W8.9 一致性套件** | ★ **必须等 W8.1/W8.2/W8.7 定稿后再做** —— 否则套件测的是**会变的对象**（制造返工与假绿） | 中高 | **依赖 1/2/5** |
| **9** | **W8.11 认证（最大缺口）** | ★★ **本条与直觉相反，须明确提请裁决**：认证**缺口最大**（A2A/MCP 锚可验证凭据，本机锚自称字符串），但**性价比最低** —— 它需要密钥分发/轮换/验签路径，是**改动面最大**且**不可逆度最高**的一项；且 CAHAC §18.4 `:641` 已登记「**认证被降级抵消类**：§10 白名单 vs §11 无 Card，两条款互相抵消」⇒ **先有卡才有身份载体** ⇒ **认证必须排在 W8.3/W8.4 之后**。★ **「缺口最大就先做」在这里是错的** | **高** | **依赖 W8.3/W8.4** |
| **10** | **W8.12 / W8.13 / W8.14 评估类** | 并行、零阻塞、可随时插队；**W8.14 尤其重要**：它约束 v6 **不得在证伪前写「领先」** | 低 | 无 |

**一句话拿给用户裁的版本**：
> **先建尺（W8.1）→ 再填信封（W8.2）→ 并行上能力卡（W8.3/W8.4）→ 顺手补两条零成本条款（W8.10/W8.7）→ 最后才碰认证（W8.11）。**
> ★ **与直觉冲突、最需您裁决的一条**：**认证虽是最大缺口，但应排第 9**，因为它依赖能力卡先立（否则 §10 认证规则继续被 §11 无卡抵消）。

---

## 来源清单

**【官方规范 / 官网】**（作为结论主依据）

| 主题 | URL |
|---|---|
| A2A v1.0 变更（JWS+RFC 8785 · ListTasks 游标 · `A2A-Version`/`A2A-Extensions` · PKCE · Device Code RFC 8628） | https://a2a-protocol.org/v1.0.0/whats-new-v1/ |
| A2A 企业就绪（**认证委托 HTTP 层 · No Identity in Payload** · mTLS · OAuth2/OIDC · 401/403 语义） | https://a2a-protocol.org/latest/topics/enterprise-ready/ |
| A2A 智能体发现（`/.well-known/agent-card.json` · RFC 8615 · 缓存/ETag） | https://a2a-protocol.org/latest/topics/agent-discovery/ |
| A2A 扩展与绑定治理（扩展不得改核心 schema/枚举/认证） | https://a2a-protocol.org/latest/topics/extension-and-binding-governance/ |
| A2A 规范 v1.0.0（源码） | https://github.com/a2aproject/A2A/blob/v1.0.0/docs/specification.md |
| A2A 主仓（**6 语言 SDK**：Python/Go/JS/Java/.NET/Rust） | https://github.com/a2aproject/A2A |
| **A2A 官方 TCK**（must/should/may 分级 · 三传输 · Gherkin · CI 报告） | https://github.com/a2aproject/a2a-tck |
| A2A TaskState（**8 态 + UNSPECIFIED · terminal/interrupted 分类 · `isFinal()`**） | https://a2aproject.github.io/a2a-java/1_2_0_Final/apidocs/org/a2aproject/sdk/spec/TaskState.html |
| MCP 版本与兼容（**2026-07-28 取消握手** · 逐请求 `_meta` · `server/discover` MUST · `-32022` + `supported[]` · 扩展 `_meta` 命名与强制前缀） | https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning |
| MCP 授权（**OAuth 2.1 + RFC 8707 资源指示符** · RFC 9728/9207 · OIDC） | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization |
| MCP Tasks 扩展（`tasks/get`·`update`·`cancel` · 5 状态 · `pollIntervalMs`） | https://modelcontextprotocol.github.io/ext-tasks/specification/2026-07-28/tasks.html |
| MCP Registry（`server.json` · 反向 DNS 命名空间校验 · preview） | https://modelcontextprotocol.io/registry/about |
| MCP Inspector（Web/CLI/TUI/mcpdo） | https://github.com/modelcontextprotocol/inspector |
| **IETF `draft-prakash-aip-02`**（多跳委托衰减不变式 · MCP/A2A/HTTP 绑定 · `/.well-known/aip/` · 引 RFC 8785） | https://www.ietf.org/archive/id/draft-prakash-aip-02.html |
| CloudEvents 规范（必填 4 上下文属性 + 可选） | https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md |
| AG-UI `EventType` 枚举（**该 commit 实测 26 项**） | https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/1625e70b/docs/sdk/js/core/events.mdx |
| **ACP → A2A**（2025-08-29，Linux Foundation LF AI & Data） | https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/ |

**【二手：博客 / 论文 / 草案】**（**仅作旁证，不作为结论唯一依据**）

| 主题 | URL |
|---|---|
| CWEP 上下文窗口经济学协议（token 计量/结算/定价/QoS/反垃圾） | https://raw.githubusercontent.com/context-window-economics/context-window-economics/main/context_window_economics_whitepaper.md |
| A2A 扩展（社区文档站，与官方治理页一致） | https://agent2agent.info/docs/topics/extensions/ |
| BTUP 成本感知 LLM 推理流量工程 | https://zenodo.org/records/21387024/files/BTUP_paper_v1.1.pdf |
| 预算分配路由策略（dca_theory） | https://zenodo.org/records/20819868/files/dca_theory_i.pdf |
| 分布式智能体通信效率综述 | https://dergipark.org.tr/en/download/article-file/6260059 |
| A2A TCK 合规报告（第三方实例，**v0.3.0 口径**） | https://raw.githubusercontent.com/thinkneo-ai/mcp-server/refs/heads/master/TCK_REPORT.md |
| FIPA-ACL SC00037J（performatives 规范镜像）★ **本轮读取被拒** | https://ppgia.pucpr.br/~fabricio/ftp/Aulas/Mestrado/AS/Aula3/SC00037J_FIPA_Performatives_Spec.pdf |

**【本机证据】**
- `~/dsh-collab/research/cost-governance/cahac-protocol-v1.2.md`（721 行，实读全文；引用均带行号）
- `~/dsh-collab/docs/distributed-agent-network-governance-plan-v5-20261010.md` §10 `:380-401` · §12 `:452-470`
- `~/dsh-collab/docs/mainline-v6-outline-20261010.md`
- 活体复跑：`cahac-compliance-report.py --status`（只读模式）· `comm-invariant-audit.py --json` · 黑板 `data/health/cahac-compliance`（version 172，ts `2026-10-10T23:47:10+0800`）· 黑板 `data/discovery/agents/` · `channel_gate status`

---

## 不确定清单（如实标注，不为给结论而模糊）

| # | 不确定项 | 为什么不可判 | 处置 |
|---|---|---|---|
| 1 | **FIPA-ACL performative 精确条数** | 官方 PDF 镜像**读取被拒**（`Unsupported content-type: application/pdf`），**未取到原文** ⇒ 「20+」为**二手** | §3.4.3 已按二手标注；**不得作为「7 类分级不领先」的唯一依据**（该判定另有 AG-UI 26 事件 + A2A 操作集两条官方旁证） |
| 2 | **CWEP 的「业界地位」** | 自标 **Pre-publication Draft**，署名含化名（Charlie/Alex/Bravo/Editor），**无标准组织背书** | 只能当「**同方向先例**」，**不得当「业界标准」** |
| 3 | ★ **「领先层」唯一候选** | **阴性证据**：本轮**未发现**协议层等价物。**未搜到 ≠ 不存在** | 检索面已声明（A2A/MCP 全文 · CWEP · BTUP · dca_theory · 通讯效率综述）；**未系统检索** arXiv 全库 / IEEE-ACM / 企业私有规范 ⇒ 须第三方复检，**见 W8.14** |
| 4 | **A2A v1.0 的 GA 状态** | 抓到的 `v1.0.0` 标签页头部同时写「Release Candidate v1.0」与「Latest Released Version **0.3.0**」⇒ **当场不可判** | v1.0 特性以 `whats-new-v1` 页为准；若 GA 状态变化，**本表结论不变**（特性清单不受影响） |
| 5 | **AG-UI 事件数 26** | 基于**单个 commit** `1625e70b`；主分支可能已增删 | 表述写死为「**该 commit 实测 26**」，不写「AG-UI 有 26 个事件」 |
| 6 | **AIP 规范状态** | `draft-prakash-aip-02` 发布于 2026-10-10，是 **I-D 非 RFC**，expires **2027-04-13**，可能有后续版本 | 仅作**方向指引**（W8.12 评估），**不作实施依据** |
| 7 | **MCP「不重放，以新 id 重发」原句** | ★ 该句是**前序调研的转述**，**本轮我未取到 MCP 2026-07-28 原文该句** | 见 §3.4.2 ⑦，**该格标 ⚠️ 半缺/不可判为主**，不写死为「MCP 规定」 |
| 8 | **MCP 2026-07-28 无握手对本机的影响** | 未评估本机 dsh/MCP 集成是否受影响（**属 W2/W5 面，非 W4 授权范围**） | 移交 W2/W5；本条**不并入** §3.4 结论 |
| 9 | **mac-mini 服务清单 9 项** | 取自 `data/discovery/agents/mac-mini` **单键快照**（version 9254，ts 23:52:25） | **服务集合会变** ⇒ §12 与 W8.3 的 **9/11 以复跑为准**，不写死 |
| 10 | **信封符合度的分母口径** | 我按「**可解析 JSON 对象** 2949」计；合规报告按「**条目行** 6079」计 | **分子为 0 ⇒ 两种口径下比值均为 0.0000**，**结论不受影响**；W8.1 建成时须**明文声明分母口径** |
| 11 | ★ **合规率分母口径**（本行原为「自我否证」条目 —— ★ **原判已作废**） | ★ **原判错**（R2 线查出四项叠加）：报告脚本 `cahac-compliance-report.py:164-171` 的 `total += 1` 在 `json.loads()` **之前** ⇒ 非 JSON 行**确实计入分母**；且 `verify-watch.json` **不是 JSONL**（**单个 pretty-print JSON 对象**，11 行逐行不可解析） | ★ **以 §3.4.6 的「★ 自我更正（2026-10-11，R2 线查出）」段为准**；该缺陷（11 行 / 0.18%）**现存，不因本次更正而关闭** |

# §4 连续性信标体系（治「计划失忆」）

## 4.1 四件套
| 件 | 载体 | 判据 |
|---|---|---|
| ① 锚点文档 | **本文件（v5）** | 头部 `state_version` 单调递增；`samples` 在位；★ **自足**（不依赖指针） |
| ② 单一索引键 | 黑板 `data/registry/continuity-index`（双板+回读） | 可解析；`closed_with_evidence` 项必有可解 `evidence` |
| ③ 续接提示词 | `docs/resume-prompt-starbridge-v3.md`（≤40 行）+ 生成脚本 | 新会话按前 3 步复述出「当前 wave + 下一步」 |
| ④ 自启动注入 | agent preset prompt section | 新会话首回合即引用索引键 —— ★ **仍未做（C4）**<br>★ **兑现路径（v6.1 登记）**：依用户 2026-10-11 裁决「**放回 v6 整体按步骤做**」⇒ **不单独施工**；★ 建议做法见 **§18.2 第 1 条**（开工先跑 `event-bus --status`）与 **§18.3**（`xdom-mail status --stale-hours`），★ **接线点 = `~/.dsh/.agent-presets/*` 的 prompt section**（属受限区 ⇒ 须备份 + 沙箱 + 回滚点） |

★ **③ 的容量约束（v5 实测入册）**：`≤40 行`是**硬上限**，`tools/mk-resume-prompt.py` 在越界时**拒绝写盘**（并明示「不要抬高上限」——这是正确行为，不是障碍）。
⇒ 实测推论：**40 行预算内，`urgent` 项最多容纳 2 条**（本次加入 4 条时渲染成 42 行被拒）。**索引可登记任意数量的未决问题，但续接提示词只能承载 2 条「要你拍板的」。**
⇒ **处置**：urgent 只标**「不给答复就动不了」**者（本次＝Q-O 唤醒授权 / Q-P C4 批准）；其余未决项留在索引 `open_questions`，由读者按第②步取。★ **不得为塞进更多 urgent 而抬高上限。**

## 4.2 状态机与闭环三要素
`open → in_flight → closed_with_evidence →(回归) regressed → in_flight`；旁支 `blocked(reason,owner,next_action)`。
**closure 三要素**：**DoD（含边界+负控）** · **evidence（可解指针）** · **verifier（第三方，禁自证）**。

## 4.3 半修防护与证伪门
半修可检形态：① 激活计数 0 且无日志 ② 依赖装了没挂载 ③ 修站点不修不变量 ④ 声明面 > 证据面。
★ **v5 补第⑤形态**：**自检全绿而事实已变**（见 P27）——它是①–④的**上游**：前四条靠人发现，第⑤条会**让人确信不必发现**。
**半修清单（9）**：compaction 未挂载 · antistorm 名不副实 · L4 无日志 · L1 几乎未触发 · `from` 三次「已修」 · 端口漂移第 5 次 · 两个注入器 · 黑板无 GC · inbox 物化点未识别。
**⛔ 证伪清单（6）**：热重载不成立 · `mbp-ops` 非真人（硬编码署名） · `/opt/homebrew/bin/node` 不区分来源 · 留痕层不能判投递层 · 「一律对 version 偏移告警」（噪声 27.8–53.4%）· 「`dv>0` 可作判据」（18.4% 噪声级）。

## 4.4 反遗忘校验（每次启动/新会话必跑）
索引 ↔ 锚点 `state_version` 比对 · 与 `~/.dsh/continuity-last-version` 比对（回退即告警）· `closed_with_evidence` 的 evidence 可解性抽检（**已实测过 evidence 因归档轮转而不可解**）。

## 4.5 自设计安全 S1–S5
S1 四步变更（备份→暂存→窗口应用→启动冒烟失败自动回滚）· S2 在役身份可观测（`runtimeVersion`/`std`/cdhash）· S3 不可自审 · S4 崩溃即回滚 · S5 一次一变量。

## ★ 4.6 四件同步规程（v5 新增）
**升版必须①→④同批完成**，缺一则 `beacon-check` 自身变红（索引仍指旧锚点 / `state_version` 不等 / 续接提示词漂移）。执行序：
```
0) 备份四件 → guard/backups/（★ 不放 /tmp）
1) 查红灯（agent_light resource=data/registry/continuity-index）→ 取独占锁
2) 写 ① 新锚点（v5）—— ★ 必须内容最终化后才可盖章
3) 改 ② 索引：anchor 路径 · state_version · updated_at（date 实读）· waves/items 一致化
   ★ 并核对「本地副本 data/registry/continuity-index.json」与「板值」是否一致
     （mk-resume-prompt 读本地副本，beacon-check --net 校验板值 ⇒ 两者是**独立的两份**）
4) 经 tools/bb_dualwrite.py 双板写 + 回读断言
5) 重生成 ③ 续接提示词（tools/mk-resume-prompt.py）
6) 写 ④ ~/.dsh/continuity-last-version
7) python3 tools/beacon-check.py --net ⇒ 必须 exit 0 且无 SKIP
8) 释锁
```
★ **任一步失败 ⇒ 整批回滚**，不留半成品（半成品比不做更坏：它会让下一次校验读到「改了一半」的状态）。

## ★ 4.7 判据补强（v5 新增，治 P27）
`beacon-check.py` 现有 17 条**不足以**发现下列**四类**，须补：
1. **两段一致性** —— 索引 `waves` 段与 `items` 段对同一项的 state 必须一致；
2. **时间戳合理域** —— `updated_at` **不得晚于当前时刻**；★ **并须先校验其为 RFC 3339 规范形（`±HH:MM` 带冒号）** —— 否则判据自身会在解析处崩（v5 起草时实测，见 §17.3③）；
3. **verifier 在位** —— `state == closed_with_evidence` 的项，`verifier` 字段**不得缺失**；
4. **本地副本 ↔ 板值一致性** —— 实测二者独立且曾有 4 字段不一致（§16 · P27 第四层）。

---

# §5 审查流水线（沙箱模拟审查 + 独立审查员逐个审查 + 信息包）

## 5.1 三段式（缺一不得记 closed）
```
① 自证（作者）       跑自检/负控/边界，产出证据
② 沙箱模拟审查（隔离）在隔离环境复跑同一产物，断言不触碰生产路径
③ 独立审查员审查      一件一裁（禁打包批量），按 §5.3 信息包给足信息
```
**裁决三态**：通过 / 不通过 / 未证（R046）；未证不得记 closed；作者不得自审。

## ★ 5.1.1 verifier 在位的机械判据（v5 新增）
现状实测：索引中 `C1` **无 verifier 字段**，`C3`/`C5` 的 verifier 写「待第三方复核」，**但三者 state 均为 `closed_with_evidence`** ⇒ 与 §5.1「未证不得记 closed」**直接冲突**。
⇒ **v5 不代其裁决**，但要求：**任一项若 verifier 未定，须显式记为 `in_flight` 或加 `verifier_pending: true`**，不得以 `closed_with_evidence` 静默承接。

## 5.2 沙箱模拟形态（按产物类型）
| 产物类型 | 沙箱做法 | 必测 |
|---|---|---|
| 插件（P2 常驻/树外） | 复制 profile 到临时 `DSH_HOME` → 挂载 → `--dump-config` 验证组合 → 真挂载冒烟（不写生产 profile）→ 「不该发生路径」拒绝证明 | 只读/可写能力清单；拒绝码；依赖两级解析 |
| 脚本/CLI | 临时目录 + 假输入；**断言未写生产路径**（路径白名单比对）；幂等复跑 | 幂等；失败态 exit≠0；无静默成功 |
| 配置/组合（profile/cordis） | 复制 profile → 改动 → `dump-config` 前后比对 → 再决定是否上生产；红线文件走 `dsh plugin add` | 组合树差异可解释；无「patch entry not found」 |
| 数据/迁移（如载体换） | 影子库导入对账 → 杀进程完整性 → 并发写 → **回滚演练** | integrity_check；并发不丢；回滚可执行 |
| 观测/判据工具 | 合成输入正例+负例+边界；**负控必须能红** | 负控红；未知不并入任何一侧 |

## 5.3 信息包规格（给独立审查员「足够信息量」，14 项）
1 目标与范围 · 2 **声明面** · 3 **未测面**（R046 必填） · 4 全部产物路径 + **版本 + sha256 + 生成时刻** · 5 **自包含复跑命令**（禁引用 /tmp 等易失路径） · 6 负控结果（能红的证据） · 7 边界用例结果 · 8 **官方规范引用**（条款+来源） · 9 已知未覆盖项 · 10 **回滚点 + 回滚演练结果** · 11 **提问清单**（要它裁什么） · 12 样本窗 · 13 机制激活证据 · 14 载体身份（onDisk vs inService）。
**硬要求**：不得只给概述——审查员必须能读到实现（源码路径+行号）；数字须带分子/分母定义。

## 5.4 禁止事项
不自审 · 不打包批量裁 · 未评审不上生产 · 不给概述代实现 · **不以「重复投递」标签替代内容比对**。

## ★ 5.5 Wave S 工具的独立 Verifier 缺口（v5 新增）
七件门工具**全部为交付方自测**（`--selfcheck`/`--selftest`/`--lean4-check` 均由作者跑）⇒ 按 §5.1 **尚不具备记 closed 的资格**，当前正确状态是 **`工具面已交付 · 规范面待复核`**。
**候选 verifier（照录 `starbridge-next-stage-plan` §四.C，均离线，唤醒须授权）**：守灯 `session-9910d4b2`（名册席位#4，C1–C7 核验员）· 独立复核员 `session-4d0e75cf`（未参与本线建构，理论上最干净）· 司库 `session-2a15e6b1`。

---

# §6 dsh 官方规范校对流程

## 6.1 强制前置（三条 + ★ v5 补第 4 条）
1. 跑 `guard_doc_check`（本地官方镜像 `~/tech-research/dsh-docs`，24h 留证 `gate-state.json`）；
2. 镜像无命中且需落地 ⇒ 官方来源 web 补证后再动；
3. 产物记录「官方条款 → 我们的设计 → 差异（一致/未覆写/未证）」；
4. ★ **留证过期即视为无留证** —— 实测：**全机 9 条留证全部过期**（最新 97.4h 前，其余 189–845h），本条要求**长期处于失效状态**，v5 起按事实判定，不再按名义判定。

## 6.2 权威来源与核对点
| 主题 | 官方来源 | 核对点 |
|---|---|---|
| 配置项与类型 | `config-catalog.md` | 例 `@deepseek-ai/dsh-host-webserver`：`host: '127.0.0.1'\|'0.0.0.0'` · **`port: number`（0=OS 随机）** · `compression` / `compressionLevel` / `compressionThresholdBytes` |
| 架构与端口 | `architecture.md` | **Desktop 默认端口 19387，profile 配置可覆盖** ⇒ 端口固定化官方路径 |
| 插件 DSL | 官方工具 schema 规则（10-06 实测汇总） | **根节点禁 `required`** · `type:"object"` 必须显式布尔 `additionalProperties` · `type` 单字符串 · 数组 `items` 禁 `required` · `defineTool` 的 `output.render` **必需** |
| 插件挂载 | 官方路径 | `dsh.profile.bundles` / `link:` 依赖 / `cordis.patch.yml` insert 三处一致 |
| 会话与上下文 | compaction 插件族 | `dsh-compaction` / `-basic` / `dsh-command-compact` / `-tool-result-pruner`（`thresholdChars=8192` / `head=4096` / `tail=1024`） |
| GUI/运行模式 | 官方 `postmortem/0003` | **当前 URL 与运行模式须可被 shell 查询**；**不得**另起不受管理的 `dsh web` |

## 6.3 纪律
- 引用须**连同限定域**一起引（已发现三次「丢限定语」属系统性）；
- 官方文档亦可能过期 ⇒ 引用附**镜像时点**，落地前 POC；
- 差异必须显式声明，禁静默偏离。

---

# §7 CLD 崩溃风险登记（已复现确定的坑 → 逐条设门）

## 7.1 插件树加载类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P1 | 任一插件 import/`apply()` 抛错 | **整棵插件树失败** + `installFailLoud` exit(1)，连续崩溃卡启动 | loader `Promise.allSettled` 收齐整组再抛 `AggregateError` | `docs/cld-boot-and-session-list-fix-20261006.md` §2.1 | **G-CR1** | 移除插件行 |
| P2 | 缺原生绑定 | `dsh-doc` 缺 `@xberg-io/xberg-darwin-arm64` | 依赖未写 `link:` | 同上 index 170 | G-CR1 | 补绑定/改 link |
| P3 | output schema 根级 `required` | `gov`/`gate` 加载失败 | 官方 DSL 根节点禁 `required` | 同上 index 171/172 §2.2 | **G-CR2** | 改 schema |
| P4 | 用不存在的 API + 无 `inject` | `knowledge-tools` 加载失败 | API 漂移 | 同上 index 173 | G-CR2 | 重写 defineTool |
| P5 | bundle/包名三处不一致 | 启动崩（手册崩溃 #3） | 目录名 / `package.json name` / patch `name` 必须一致 | `~/Desktop/归档/2026-08-18/DSH-macmini-防崩溃运维手册.md` | **G-CR3** 命名门 N1–N3 | 改至一致 |
| P6 | bundle 缺失 | 启动崩（手册崩溃 #1） | 打包不完整 | 同上 | G-CR1 | 重建 bundle |
| P7 | `patch entry not found` | dump-config 警告、条目空转 | 只写 config 无完整 insert | 存量已知 | G-CR2 | 改完整 insert |

## 7.2 模块实例分裂（遮蔽）类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P8 | profile 有 `@deepseek-ai/*` **物理目录** | `dsh-tools` 双实例 ⇒ Symbol 不一致 ⇒ **每回合 `reading 'prepare'`** | loader 锚=profile、运行时内部 import 锚=运行时 | `docs/cld-tools-instance-split-fix-20261006.md` §2 | **G-CR4** | 移走遮蔽 |
| P9 | 同上 | 客户端 `dsh-client-runtime` 旧版 ⇒ **会话列表全空** | profile 旧副本被服务 | `docs/cld-boot-and-session-list-fix-20261006.md` §3 | G-CR4 | 软链回运行时 |
| P10 | **去遮蔽顺序错** | `ERR_MODULE_NOT_FOUND` 启动崩 | 树外插件自有软链指向被移走的 web 遮蔽 | 同上 §5 | **G-CR5**（先重指→再移走） | 恢复链接 |
| P11 | `build-bundle.sh` 制造物理副本 | 新遮蔽 | 脚本注释原文「peerDependencies 物理副本（从 CLD runtime 拷，**避免符号链接**）」 | `scripts/build-bundle.sh:2,29` | G-CR4 | 去遮蔽 |
| P12 | 100 个惰性残骸目录 | 不崩但污染信号/易回流 | 历史备份未清 | 存量已知 | G-CR4 | 归档清理 |

## 7.3 签名与 dylib 类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P13 | `install_name_tool` 后未重签 | **SIGKILL exit137**（无报错），表现为 `Timed out waiting for dsh web to announce its URL` | dlopen 签名无效 ⇒ AMFI 杀进程 | 10-06 报告 §2.3（`libaom.3.dylib`/`libheif.1.dylib`） | **G-CR6** | `codesign --force -s -` |
| P14 | 逐二进制签名遗漏嵌套 Mach-O | 公证/启动失败 | `--deep` 不足 | 我方公证三轮（24 个 Mach-O） | G-CR6 | 全量重签 |
| P15 | 重签后 TCC 权限重置 | 每次启动弹辅助功能授权 | 权限绑定代码签名 | 实测（残留多条目 ×3） | **G-CR7** | 重置+重新授权 |

## 7.4 内存/事件数类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P16 | 会话事件数过大 | `MarkCompactCollector: young object promotion failed` ⇒ SIGABRT ⇒ `dsh-crash-after-child` | 装载 ~1,180 万对象 > V8 堆上限 4192MB（pointer compression 硬顶；**调大无效**） | `~/.cld/logs/dsh-web.log`（OOM ×13）+ 09-28 报告 Q5 | **G-CR8 装载前拒绝** + G-CR9 挂载 compaction+约束钉住 | 归档重建+记忆继承包 |
| P17 | 监控只测本体 | 崩溃前无告警（本体 RSS 平的 105MB） | OOM 在 dsh 子进程 | 09-28 报告 §2.3 | **G-CR10** | — |

## 7.5 热重载/升级类
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| P18 | `POST /reload`（31888） | `main.js:462 reading 'reloading' undefined` 崩 | 热重载路径缺陷 | 崩溃三模式① + 08-31 事故 | **G-CR11** | 不用即安全 |
| P19 | 运行中改 `app.asar` | `main.js:440 resolveUrl not a function` | 升级引入 + 初始化时序 | 崩溃三模式② | **G-CR12** | 还原 `.bak` |

## 7.6 动态插件沙箱类
| # | 坑 | 事实 | 门 |
|---|---|---|---|
| P20 | 无 `setTimeout` | 用 `ctx.get('timer')` | G-CR13 |
| P21 | `ctx.get('tools')` 是 façade | 只有 register/schemas/get，**无 guard** | G-CR13 |
| P22 | 动态沙箱 `webServer.register` 不生效 | 须 reactive 注册（`ctx.on('internal/service')`） | G-CR13 |
| P23 | client inject 未声明服务 | 静默失效 | G-CR13 |

## 7.7 运维/端口类
| # | 问题 | 症状 | 门 |
|---|---|---|---|
| P24 | `--port 0` = OS 随机 | 每次重启换地址（6 个历史端口）⇒ 用户侧 `Failed to fetch` | **G-CR14** 端口固定 |
| P25 | 重启语义 SIGTERM=关闭不自动拉起 | 需手动打开 | **G-CR15** 重启票 |

## 7.8 会话上下文/压缩类（P16 的同族不同病）

### P26（含 v5 补现状）
| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| **P26** | 活跃窗口已瘦到**低于压缩器自身开销** | **不崩**、进程与 CLD 均存活，但该会话**再也发不出请求**：`CONTEXT_WINDOW_EXCEEDED`（超 3,242 token，**全来自 completion 预留**）；自动 + 手动 `compact` **各失败一次**，报 `summary is not smaller than the shadowed content (3435/3450 ≥ 2466)` ⇒ **会话内唯一自救路径关闭** | 压缩判据「摘要必须小于被遮内容」的**必然推论**：待遮内容 2,466 < 压缩器开销 3.4k ⇒ **存在一个下界，越过它 compaction 永久失效** | `docs/compaction-lowerbound-crash-20261009.md`（一手 JSONL：`session-fa1f9150-…`，03:03:28 / 03:06:16 / 05:39:52 三条） | **G-CR16** 请求前 token 预算门 + **G-CR17** 压缩有效性门 | 会话外接手（新会话 + 锚点）／归档重建 |

**两机制（代码核实）**：
| 机制 | 内容 | 代码位置 | 配置能修吗 |
|---|---|---|---|
| **一 · 阈值不可达** | 压力阈值 `floor(contextWindow × thresholdRatio)` 默认 `floor(1e6×.8)=800,000`，而消息侧可达上限仅 `1,048,576 − 256,000 = 792,576` ⇒ **压力检查永远晚于溢出，主动压缩从不触发** | `dsh-compaction-basic/lib/index.js:13` · `dsh-llm-deepseek/lib/index.js:1735` | ✅ **已修**：`~/.dsh/settings.yaml:62` 的 `maxTokens 65536` ⇒ 上限升到 983,040，留 183,040 余量 |
| **二 · 模板地板**（**终局死因**） | 摘要**强制 8 段**且 "never drop a section" ⇒ 摘要体量有结构性下界；判据「摘要必须小于被遮内容」（`:556`）⇒ 活跃窗口低于该下界时**压缩在数学上永久失效** | `:218`（8 段指令）· `:322`（`frameSummary`）· `:556`（判据） | ❌ **无配置解**：`BASIC_COMPACT_CONFIG_KEYS`（`:28`）**十把键无一把可改模板或判据** |

**决定性时间线**：`maxTokens 256000→65536`（机制一之修）与 `standard-compact` 预设**同为 2026-10-08 落盘**；会话 `session-fa1f9150` 仍于 **2026-10-09T05:39 bricked**，报的正是**机制二**的 `(3435/3450 ≥ 2466)` ⇒ **「修了机制一 ≠ 病好了」有一手证据**。

**失败路径均不兜底**：压力路径抛错只 `logger.warn("…; continuing the turn")` 继续本轮（`:790`）；溢出恢复抛错 `"…preserving the original request error"` 保留原错误（`:821`）⇒ **不崩、不自救、不被崩溃监控覆盖**。

**与 P16 的分界**：P16 是**崩溃**（SIGABRT，操作系统杀）；P26 是**不崩的死锁**（谁都没杀它，是它自己再也张不开嘴）。

**★ v5 补现状**：治本项 **Q-K** 已进入实施 —— 三件接线（① 写入 → ② 落盘 → ③ 召回，**顺序不可颠倒**）**进行中**，执行方 `session-28174037`（持 `devices/dsh-plugin-context-survival` 独占锁）；「写入」件见新建的 `lib/wire.js`。★ **`enableGuard` 仍为 `false`，直到 ① 被独立验证**。

**★ v5 补（官方解释）**：S4 顺带产出官方 `defensive-patterns.md` L17 —— **「若被等待的转变永远不会发生，等待会挂住」** ⇒ 为 P26 机制二提供了官方侧解释，且支持止血方向。

**本病的保守保命机制 = R049（上下文存活运营门：会话限寿 + 交接前置）** —— 在活跃窗口到达下界**之前**交班。

### ★ P27 判据失明族（v5 新增 · 本版最重要的一条）

| # | 触发 | 症状 | 根因 | 证据 | 门 | 回滚 |
|---|---|---|---|---|---|---|
| **P27** | **检查项与变化项不是同一项** | **不崩、不报错、校验全绿**，而事实已经变了：权威索引落后于交付物、时间戳落在未来、内部两段互相矛盾 | 判据覆盖缺口 + **自指参照系**（比较的两端同源 ⇒ 一起变就永远相等） | 2026-10-10T07:0x 实测，三层同现（见下） | **G-CR18 信标自检覆盖门** | 重建判据后重跑；**不是回滚数据，是回滚判据** |

**实测三层（同一次检查内并发存在）**：
| 层 | 实测 | 后果 |
|---|---|---|
| **声明错** | 索引载荷 `updated_at = 2026-10-11T00:20:00+08:00`；板侧实际写入 `ts = 2026-10-10T05:22:09`；实读时钟 `2026-10-10T07:06:57+0800` ⇒ **超前约 19 小时** | 「更新于」不可信，且**使索引看起来比交付物更新** ⇒ 加剧误信 |
| **内部不一致** | `waves[C].note` 写「C4/C6/C7 未做」（10-09 口径）；同份索引 `items` 段 C6/C7 已 `state=in_flight`、`updated=2026-10-10T01:44:37` | **只读 waves 的人低估进度**；两段不一致而 `state_version` 仍为 3 |
| **检查看不见** | `beacon-check.py --net` 得 **17 PASS / 0 WARN / exit 0**。「索引 ↔ 锚点 state_version 相等」PASS —— 两边都是 3，**版本号没跟着内容动 ⇒ 该 PASS 空洞**；「续接提示词未漂移（== 现渲染结果）」PASS —— **渲染源正是 waves 段 ⇒ 两段不一致它看不见**；全程**无 `updated_at` 检查** | 校验全绿，上两层全漏 |

★ **第四层（v5 起草时新发现）**：**索引「本地副本」与「板值」不是同一份** —— 实测 4 字段不一致（`_p0_sync_note` · `evidence_index` 31 vs 19 · `open_questions` · `updated_at` 不同），而 **`mk-resume-prompt.py` 读本地副本、`beacon-check --net` 校验板值** ⇒ **二者永不互校**。归入 P27 同族。

**★ 与 P16 / P26 的三方分界（勿混成一条）**：
- **P16 是崩溃** —— 操作系统把它杀了；
- **P26 是发不出请求** —— 谁都没杀它，是它自己再也张不开嘴；
- **P27 是治理看不见自己已经变了** —— 全绿，且**没有任何东西在杀谁**。

**★ 为什么它是「最深」的**：P16/P26 的受害者是会话，而 P27 的受害者是**用来发现前两者的那套检查**。⇒ 按 §4.3 五形态，P27 是第⑤形态「**漏配却显示通过**」的可复现实例，且**落在本计划最核心的自保机制（§4 连续性信标）自己身上**。

**★ 已登记实例**：`docs/pending-backlog.md` **B8 / B9 / B10**（三层分别一条）。

## 7.9 预防门汇总（结构约束，可机器校验）

## §7.10 P28 通讯通道缺陷族

> **本章基准**：CAHAC 以 **`research/cost-governance/cahac-protocol-v1.2.md`（720 行，2026-10-09）** 为对照基准。
> ★ **路径更正（实测）**：`docs/cahac-protocol-v1.0.md` **不存在**；v1.0 真身在 `research/cost-governance/cahac-protocol-v1.0.md`（371 行）。
> ```
> $ cd ~/dsh-collab && wc -l docs/distributed-agent-network-governance-plan-v5-20261010.md research/cost-governance/cahac-protocol-v1.2.md research/cost-governance/cahac-protocol-v1.0.md
>      588 docs/distributed-agent-network-governance-plan-v5-20261010.md
>      720 research/cost-governance/cahac-protocol-v1.2.md
>      371 research/cost-governance/cahac-protocol-v1.0.md
> $ ls docs/cahac-protocol-v1.0.md
> ls: docs/cahac-protocol-v1.0.md: No such file or directory   [exit 1]
> ```
> **v1.0 与 v1.2 冲突两处，本章一律以 v1.2 为准**（对照写入即标注）：
> | 字段 | v1.0（371 行件） | v1.2（720 行件，**本章基准**） |
> |---|---|---|
> | `cahac` | `"1.0"`（v1.0:55） | `"1.2"`（v1.2:130，注 **N-11：原写 1.0 未随文档版本传播**） |
> | `dedup_key` | `"<stable-key>"`（v1.0:64，不透明键） | `"sha256:<hex>"` = 内容指纹 `SHA256(规范化 payload)`（v1.2:**139**，依 §8.3 裁定） |

---

### P28-① 未登记通道：「卡 → 自动唤起会话」的**消费方无属主**

**三态：成立（含一处口径更正）**

**调用链（具名，逐环给文件:行号）**：

| # | 环节 | 位置 | 原文 |
|---|---|---|---|
| 1 | 订阅黑板事件桥 | `~/dsh-plugin-central-inbox/lib/index.js:44` | `const SSE_URL = process.env.CENTRAL_INBOX_SSE \|\| 'http://127.0.0.1:8803/events';` |
| 2 | 声明用途 | `~/dsh-plugin-central-inbox/lib/index.js:3` | `// 原理：监听黑板事件桥 8803 SSE → 过滤 notes/<本节点>/* → agentBus.send 注入本节点会话` |
| 3 | 投递 | `~/dsh-plugin-central-inbox/lib/index.js:481` | `const r = agentBus.send(from, target, text, undefined, {` |
| 4 | 进 bus | `~/dsh-plugin-agent-bus/lib/index.js:1399` | `const ok = deliver(msg, 'normal');` |
| 5 | **唤起会话（副作用发生点）** | `~/dsh-plugin-agent-bus/lib/index.js:573` | `target.followup(message);` |

**登记面实测（两张登记表，逐面打印）**：

```
$ M=~/dsh-plugin-drift-scan/lib/channel-matrix.json
$ python3 -c "...统计 matrix 项与 channel_gate CHANNELS..."
drift-scan 矩阵项: 11  ['board-central','board-local','bus-8791','device-daemon',
  'e2-registry-services','funnel-public','hb-fwd','node-bridge','sse-8803',
  'sync-from-central','tailscale-direct']        ← drift_scan 实跑 total: 12（含 file-perm 动态项）
channel_gate 枚举: 7   ['board-central','board-local','bus-8791','launchd-daemons',
  'local-agent-bus','sse-8803','tailscale-direct']
★ 仅在 channel_gate（矩阵无）: ['launchd-daemons','local-agent-bus']
★ 仅在矩阵（gate 无）: ['device-daemon','e2-registry-services','funnel-public',
  'hb-fwd','node-bridge','sync-from-central']
```

> ★ **口径更正（须写进 v6，不得照抄「不在 drift-scan 12 项矩阵」）**：
> **通道名 `sse-8803` 是登记在册的**——`channel-matrix.json:**21**` 有 `sse-8803` 项（`kind:"sse"`，`expect:"http://xingqiao.meetfunbp.com:8803/events"`，探针 `expectFirstBytes:"event: hello"`），`channel-gate/lib/gate.js:22-30` 亦将其列入冻结枚举（`owner:'rust-blackboard'`，`blast:'订阅端'`）。
> **真正未登记的是「消费方」**：做「卡 → 唤起会话」这一**有副作用跃迁**的 actor `dsh-plugin-central-inbox`，在两张登记表中**均无条目、无 owner**，且在两份权威通讯文档中 **0 命中**：
> ```
> $ for f in docs/comm-channel-rules-v2-20261002.md docs/agent-comm-portal-20261002.md; do
>     echo "$f : 命中 $(grep -c 'central-inbox' $f) 条 / 共 $(wc -l < $f) 行"; done
> docs/comm-channel-rules-v2-20261002.md : 命中 0 条 / 共 69 行
> docs/agent-comm-portal-20261002.md      : 命中 0 条 / 共 100 行
> ```
> ⇒ **精确表述**：不是「有一条通道没名字」，而是**通道在册、跃迁方（consumer）无属主**——这恰是 CAHAC §18「未指定责任方的条款不得标 `enforced`」在实现层的同构形态。
> ★ **附带发现**：两张登记表**只共有 5 项**（`board-local`/`board-central`/`bus-8791`/`sse-8803`/`tailscale-direct`），并集 **13 项**。v5 §13 R6「双轨并存」在此有第二实例。

**复跑命令**：
```bash
python3 - <<'EOF'
import json,os,re
m=json.load(open(os.path.expanduser('~/dsh-plugin-drift-scan/lib/channel-matrix.json')))['matrix']
mn=set(k for k in m if not k.startswith('_'))
g=open(os.path.expanduser('~/dsh-plugin-channel-gate/lib/gate.js')).read()
gn=set(re.findall(r"'([a-z0-9-]+)':\s*\{", g[g.find('CHANNELS'):g.find('REQUIRED_FIELDS')]))
print("矩阵项",len(mn),sorted(mn)); print("gate 枚举",len(gn),sorted(gn))
print("仅 gate:",sorted(gn-mn)); print("仅矩阵:",sorted(mn-gn))
EOF
```

---

### P28-② 离线投递：**无撤回能力** + TTL 常量 7 天但**未确定性执行**（实测滞留上界 ~46 天）

**三态：成立（撤回面）；成立且**强于**原转述（TTL 面）**

**① 静置载体（内联在 `store.threads[].messages[]`）**——成立：
```
$ python3 -c "...解析 ~/.dsh/agent-bus.json..."
顶层键: ['threads','locks','lightLog','dedup','profiles','restartPlan','approvals']
threads 类型: list, 条数: 5544
messages 总数: 33613
--- status 分布 ---
  delivered         31228   92.9%
  expired            2377    7.1%
  queued                8    0.0%
```

**② 无撤回能力**——成立（0 命中，附扫过的面）：
```
$ cd ~/dsh-plugin-agent-bus && echo "[命中数: $(grep -cE 'recall|withdraw|revoke|撤回|撤销|unsend' lib/index.js)]"
[命中数: 0]
扫过的面: ~/dsh-plugin-agent-bus/lib/index.js（1975 行）
```
⇒ 消息一旦入 `store.threads[].messages[]`，**投递方无任何撤回/撤销入口**；`queued` 只能等 `flushQueue` 或等 TTL。

**③ TTL 常量与判定点**——成立：
- `~/dsh-plugin-agent-bus/lib/index.js:84` → `const QUEUE_TTL_MS = 7 * 864e5;`
- `~/dsh-plugin-agent-bus/lib/index.js:83` → `// ★ A2：queued 保留期（7 天），超期在 flushQueue 入 expired（DLQ 语义，不删除）`
- 判定点 `~/dsh-plugin-agent-bus/lib/index.js:1308-1312`：
  ```js
  // ★ A2（2026-10-02）：过期判定 —— queued 超 QUEUE_TTL_MS 入 expired（DLQ：可枚举可回放，不删除）
  if ((now - (m.time || 0)) > QUEUE_TTL_MS) {
    m.status = 'expired';
    m.expiredAt = now;
    expired++;
  ```

**★ 本轮新发现（原转述未载，请并入 v6）——TTL 不是确定性执行，实测滞留远超常量**：
```
expired 的 expiredAt 取值分布（前二大）:
  1790886845311 → 2026-10-02 04:34:05   1771 条   ← 单次批量清扫
  1791057609699 → 2026-10-04 04:00:09    214 条   ← 单次批量清扫
  ... 其余 392 条为单条/微量
expired 原始投递时间窗: 2026-08-17 00:42:19 → 2026-10-03 18:16:42（跨 47.7 天）
该批滞留时长(最长): 46.2 天
（★ 逐条真实最大滞留 = 2026-08-17 00:42:19 → 2026-10-02 04:34:05；54.7 天 = max(expiredAt) − min(time) 属【跨消息交叉配对】，非单条滞留，已作废）
```
⇒ **常量写 7 天，实测滞留最长 46.2 天**：2377 条 expired 中 **1771 条（74.5%）由同一次清扫**产出。
⇒ 结论精确化：**TTL 的「值」是确定的，「执行时点」不是**——`expired` 的产出由 `flushQueue()` 的**偶发触发**决定，而非定时器驱动。

**触发点普查**（`grep -n "flushQueue" lib/index.js`）：`load 一次 / sendMessage / lock / unlock / HTTP /api/flush / 目标回 idle`（:263、:349、:736、:1409、:1467、:1498、:1915）。**无 launchd/cron 周期项**。

**★ 口径钉死（须写入 v6，防再次混用）**——「真达率 15%」：
- 该数字**唯一来源是源码注释自述**，非本轮复测：
  `~/dsh-plugin-agent-bus/lib/index.js:261-263`
  ```js
  //   此前 flushQueue 触发点只有 load 一次/sendMessage/lock/unlock/HTTP /api/flush ⇒
  //   忙窗口收的消息排队后**永远等不到**下个触发点 ⇒ queued 事实上是终态（实测真达率 15%）。
  ```
- **口径**：**2026-10-04 `1.5.13` 修复前**、**「忙窗口排队」子群**的队列真达率——**窗口与分母未载明**。
- **本轮判定：不可判（不可复现）**。我**不**把 15% 写成 v6 的现状值。
- 本轮**可复现**的替代口径（全量 store，N=33613）：`delivered 92.9% / expired 7.1% / queued 0.0%`——**注意这是「全量终态分布」，不等于「曾入队者的真达率」**（曾入队后成功者与直投成功者在终态上不可区分），v6 **不得**将二者互换。

**复跑命令**：
```bash
python3 - <<'EOF'
import json,collections,os
from datetime import datetime,timezone,timedelta
CST=timezone(timedelta(hours=8)); f=lambda ms: datetime.fromtimestamp(int(ms)/1000,CST).strftime('%Y-%m-%d %H:%M:%S')
d=json.load(open(os.path.expanduser('~/.dsh/agent-bus.json')))
ms=[m for t in d.get('threads',[]) or [] if isinstance(t,dict) for m in t.get('messages',[]) or []]
print("messages:",len(ms)); print(collections.Counter(m.get('status') for m in ms).most_common())
ex=[m for m in ms if m.get('status')=='expired']
print("expired:",len(ex))
print("expiredAt 批量:",collections.Counter(str(m.get('expiredAt')) for m in ex).most_common(2))
ts=[int(m['time']) for m in ex if m.get('time')]
print("滞留最长(天):",round((max(int(m['expiredAt']) for m in ex)-min(ts))/864e5,1))
EOF
```

---

### P28-③ `reply_required`：**写了没人读** —— 且是一条**已登记规则的零实现**

**三态：成立（并强化：不只是死字段）**

**全仓命中（`~/dsh-plugin-agent-bus` lib + cli，1975 行 + 498 行）**：
```
lib/index.js:561:  //   reply_required 与 notify_only 并存时 notify_only 显式选择不唤醒 ⇒ inject 优先。）
lib/index.js:1381: // ★ I7a（2026-10-02）：reply_required 挂消息体，deliver 时据此把「看黑板」指针升级为唤醒
lib/index.js:1382: if (opts && opts.replyRequired === true) msg.replyRequired = true;      ← 唯一写点
lib/index.js:1621: reply_required: { type:'boolean', description:'true=要求收件方回复…' }  （schema 声明）
lib/index.js:1622: notify_only:    { type:'boolean', description:'true=纯通知不唤醒…' }     （schema 声明）
lib/index.js:1672: ...{ replyRequired: args.reply_required === true, notifyOnly: args.notify_only === true }
```
⇒ **写入点 1 处（:1382）、读取点 0 处**。

**`deliver()` 全文（`lib/index.js:508-601`）的唤醒判据只读两个字段**：
```js
const isNotify = msg.notifyOnly === true || msg.rateLimited === true;
if (isNotify && typeof target.inject === 'function') { target.inject(message); msg.wake='inject'; }
else { target.followup(message); }
```
`msg.replyRequired` **不在** `deliver()` 的任何判据里。

**★ 强化（本轮新增证据）**：它不只是一条死字段，而是一条**在册规则的零实现**——
`~/dsh-collab/docs/comm-channel-rules-v2-20261002.md` §2 通道矩阵（唯一权威，69 行件）第 32 行明文登记：
```
| 要求回复的信封 | reply_required=true（唤醒语义，I7a） | — | 不得用通知语义要求回复 |
```
⇒ 规则表承诺「`reply_required=true` ⇒ 唤醒」，而实现在 2026-10-03「方案 A-1 唤醒语义反转」后**改为默认即唤醒**，`reply_required` 沦为恒真无操作。**规则与实际语义已分叉，而规则未同步**（同族于 v5 §13 R12「引用丢限定语」/ R16「做了没说」）。

**用量实测**（卡片侧）：
```
分母（notes/collab 全量键）: 564
  reply_required          92/564      ← 实际有人在用
```
⇒ **有 92 张卡显式依赖该字段，实现侧零读取** —— 危害面不是「没人用」，而是「**用了也不生效**」。

**复跑命令**：
```bash
cd ~/dsh-plugin-agent-bus && grep -n "reply_required\|replyRequired" lib/*.js
sed -n '555,575p' lib/index.js          # deliver() 的唤醒判据
grep -n "reply_required" ~/dsh-collab/docs/comm-channel-rules-v2-20261002.md
```

---

### P28-④ `awaiting`：**无任何 daemon 消费者**（三面扫描全部为写时校验器/写入方/夹具）

**三态：成立**

**三面扫描（逐面打印分母）**：
```
--- py 面 ---   54 条命中
   面: ~/dsh-collab/**/*.py（--exclude-dir=node_modules）
--- js 面 ---   15 条命中
   面: ~/dsh-collab + ~/dsh-plugin-agent-bus/lib + ~/dsh-plugin-central-inbox/lib 的 *.js（排除 node_modules）
--- plist 面 --- 0 条命中
   面: ~/Library/LaunchAgents/com.dsh.*.plist（共 80 个）
```

**逐类归因（无一条是消费者）**：

| 类别 | 实例 | 性质 |
|---|---|---|
| 写时校验器 | `scripts/mbp-tools/comm-preflight.py:92-106` | `bad()/warn()/info()` 判 `awaiting` 与 `reply_required` 配对，**发消息前**跑 |
| 同类副本 | `mbp-side-export-20261004/tools/comm-preflight.py:92-106` | 同上（第二副本） |
| 卡写入方 | `report-iteration-20261004.py:70`、`report-r43-contribution.py:91`、`resend-voicecard-20261004.py:60`、`report-g30-boot-window.py:50` | 把 `"awaiting": "星桥(session-fa1f9150)"` 写进卡 |
| 离线分类器 | `scripts/inbox-validity-check.py:146,175-182` | 离线判「动作项/回执/记录体」形态 |
| 校验器夹具 | `devices/dsh-plugin-item-validity-review-check/cli.js:134,146,184,192,199,203,216,227` | `judge()` 的测试用例 |
| 卡写入方（备份） | `guard/backups/p2b-20261010-015253/server.js:496` | 写入方 |
| 无关噪音 | `cld-voice/**/venv/.../websockets/server.py:803` 等 6 处 | 英文散文 "awaiting at least one of" |

⇒ **消费者（daemon/订阅端）0 个**。`awaiting` 的球权语义**从未被任何常驻进程消费**，只有「写卡时拦一下」和「离线盘点时读一下」。

**复跑命令**：
```bash
grep -rn "awaiting" ~/dsh-collab --include=*.py --exclude-dir=node_modules | wc -l
grep -rn "awaiting" ~/dsh-collab ~/dsh-plugin-agent-bus/lib ~/dsh-plugin-central-inbox/lib \
     --include=*.js --exclude-dir=node_modules --exclude-dir=.git | wc -l
grep -rn "awaiting" ~/Library/LaunchAgents | wc -l; ls ~/Library/LaunchAgents/com.dsh.*.plist | wc -l
```

---

### P28-⑤ 失实日志：打印「→ 回退注入中枢」，而代码**不回退**

**三态：成立**

**两侧原文对照**：

| 侧 | 位置 | 原文 |
|---|---|---|
| **打印** | `~/dsh-plugin-central-inbox/lib/index.js:467` | `logLine('[central-inbox] ⚠️ to=' + String(value.to) + ' 未命中本机在线会话（' + (reason \|\| 'unknown') + '）→ 回退注入中枢 ' + centralAgent);` |
| **行为** | `~/dsh-plugin-central-inbox/lib/route.js:48` | `// ★ 修缺陷3：未命中【不再静默回退注入中枢】。回退只对显式中枢别名保留（见上）。` |
| **行为** | `~/dsh-plugin-central-inbox/lib/route.js:49` | `return { target: null, mode: 'skip', reason: 'unresolvable(' + one + ')' };` |
| **行为** | `~/dsh-plugin-central-inbox/lib/index.js:**472-475**` | `if (!target) { bufferPending({ key, value, ts: d.ts }, '目标 null (' + (reason \|\| 'unknown') + ')'); return; }` |

⇒ `unresolvable` 路径 `target === null` ⇒ 走 `bufferPending` **入缓冲**（**不是**回退注入中枢）。日志宣称的回退**在该路径上不存在**。
⇒ 该日志的**误导性已被历史实证**：`lib/index.js:**455**` 自承
`// 日志自相矛盾（「未命中（exact）」），MBP 实测被其误导去怀疑回退逻辑仍在。`
⇒ **误诊已发生**，与 v5 §13 R4「仪器失真」同族；且此处是**仪器主动撒谎**（不是静默），危害面是**排障方向被日志反转**。

**复跑命令**：
```bash
cd ~/dsh-plugin-central-inbox && grep -n "回退注入中枢" lib/index.js && sed -n '46,50p' lib/route.js
```

---

### P28-⑥ 双投去重：**有去重，但粒度＝整卡/整消息 ⇒ 半重复内容必漏判**

**三态：成立（须修正「无去重」的表述为「粒度错」）**

**两层去重键（均实测，非转述）**：

| 层 | 位置 | 键构成 | 粒度 |
|---|---|---|---|
| 卡层（central-inbox） | `~/dsh-plugin-central-inbox/lib/route.js:**92**` | `const dk = key + '#' + fp;` 其中 `fp = contentFingerprint(JSON.stringify(valueNoVersion))`（`:88-93`，仅剔 `version` 与 `_via`） | **整卡 JSON 指纹** |
| 消息层（agent-bus） | `~/dsh-comm-shared/identity.js:137-141` | `return f + '\|' + t + '\|' + contentFingerprint(text);` | **整条 text 指纹** |

**参数弱点**：
- `~/dsh-plugin-agent-bus/lib/index.js:364` → `const DEDUP_WINDOW_MS = 10 * 60 * 1000;`（**10 分钟**）
- `~/dsh-plugin-agent-bus/lib/index.js:385` → `if (store.dedup.size > 300) { ... }`（**容量 300**，对 33613 条消息）
- 卡层 `seen` cap 默认 2000（`route.js:98` `remember(seen, dedupKey, cap = 2000)`）

**⇒ 漏判形态（正是本条要治的）**：一张卡「**一半重复、一半新内容**」——
- 卡层：`valueNoVersion` 整体变 ⇒ `fp` 变 ⇒ 新键 ⇒ **整卡重注入**（重复的那一半跟着再注入一次）；
- 消息层：`text` 整体变 ⇒ 指纹变 ⇒ **不算 duplicate**。
⇒ **两层都按「卡/消息」为单位判重，没有任何一层按【内容项】判重** ⇒ 半重复卡**结构性必漏**，且漏的是「重复内容」而非「新内容」。

**★ 与规范的差距定位（关键，供 v6 定责）**：CAHAC **v1.2 已给出正确判据**，差距在**实现粒度**，不在「有无规范」：
- `cahac-protocol-v1.2.md:**139**` → `"dedup_key": "sha256:<hex>"  // ★ v1.2：内容指纹（SHA256(规范化 payload)），依 §8.3 裁定`
- `cahac-protocol-v1.2.md:611`（§18.3 已闭合缺口）→ `§8.3 去重键 | 接收方（消费侧去重）；键**不含 thread**（审计器 I2 独立印证）`
⇒ v1.2 要求：**内容指纹 · 不含 thread · 消费侧去重**。实现做到了「不含 thread」（`lib/index.js:367` `void threadId;`）、做到了「消费侧」，**没做到「内容项粒度」**。

**复跑命令**：
```bash
sed -n '86,95p' ~/dsh-plugin-central-inbox/lib/route.js
sed -n '137,141p' ~/dsh-comm-shared/identity.js
grep -n "DEDUP_WINDOW_MS =\|store.dedup.size >" ~/dsh-plugin-agent-bus/lib/index.js
```

---

### ★ §3 信封上线率 0% —— 全量复测（非抽样）

**三态：成立（两个独立面，各自 100% 覆盖，无需抽样）**

**面 A：黑板卡（`notes/collab`）**
```
$ curl -s "http://127.0.0.1:8792/notes/collab/" -o /tmp/collab-list.json
分母（notes/collab 全量键）: 564
--- CAHAC §3 信封字段命中 ---
  cahac        0/564     channel      0/564     sender       0/564
  recipient    0/564     dedup_key    0/564     signature    0/564
  id           0/564     thread       0/564     cost_cap     0/564
  expires      0/564     payload     11/564     priority     2/564
  type       394/564     ts         400/564
--- 实测实际字段命中 ---
  from       471/564     ts         400/564     to     271/564
  subject    237/564     body       148/564     _via   312/564
  from_label  74/564     content    142/564
--- 顶层键出现频次 top8 ---
  from 471 · ts 400 · type 394 · _via 312 · to 271 · subject 237 · body 148 · content 142
```

**面 B：运行时消息（`~/.dsh/agent-bus.json`）**
```
分母（agent-bus 全部 messages）: 33613
--- CAHAC §3 信封字段命中 ---
  cahac 0 · type 0 · channel 0 · sender 0 · recipient 0 · priority 0
  cost_cap 0 · dedup_key 0 · ts 0 · expires 0 · payload 0 · signature 0
  （仅 id 33613/33613 · thread 33613/33613 —— 非信封专属字段）
--- 实测实际顶层字段 top8 ---
  id 33613 · thread 33613 · from 33613 · to 33613 · text 33613 · time 33613 · status 33613 · kind 33613
★ 结论：channel/sender/recipient/dedup_key/signature 在运行时消息层命中 = 0 0 0 0 0
```
⇒ **§3 信封符合度 = 0%**，实际 schema 为自造 `{from,to,subject,body,_via}` / `{id,thread,from,to,text,time,status,kind}`。
⇒ 两面对 **`cahac`/`channel`/`sender`/`recipient`/`dedup_key`/`signature` 六字段** 的命中**均为 0**，全量覆盖（564 + 33613，**无抽样**）。
★ 附注：`dedup_key` 在消息层 0/33613 —— agent-bus **确有去重**（见 P28-⑥），但**去重键是内存态、从不落进信封字段** ⇒ 「有去重、无 `dedup_key` 字段」，规范字段与实现字段各活各的。

---

### ★★ 两个合规口径**必须分开写**（v6 硬约束）

| 口径 | 定义（源码级证据） | 本轮实测值 |
|---|---|---|
| **§3 信封符合度** | 卡/消息是否带 §3 信封字段集 | **0%**（564 + 33613 全量，见上） |
| **自报合规率 `rate_legal`** | **邮箱任务卡 `state` 字段值是否落在 §7.2 合法枚举内** ★ **口径声明（必须）**：`cahac-compliance-report.py:102` 的 `LEGAL_STATES` 为 **7 值**，而 CAHAC v1.2 §7.2（`:251`）为 **8 值（含 `superseded`）** ⇒ 该工具执行的是 §7.2 的**真子集**；凡引「唯一合规率」须同时声明此事。 | ★ **以复跑命令 + 取值时刻记，一律不写死数字**（外部复核 S1-3 更正；★ v6 内本指标曾有 0.041909 / 0.046136 / 0.04822@ver175 / 4.6136% 等多值，均须以复跑为准；复跑：`curl -s http://127.0.0.1:8792/data/health/cahac-compliance` 的 `rate_legal`） |

**口径二的真身（代码，非文档）**——`~/dsh-collab/scripts/cahac-compliance-report.py`：
```
:101  # CAHAC §7.2 的合法 state 枚举（v1.2.1：已对齐 bb-taskboard）
:102  LEGAL_STATES = {
:179      if str(obj.get("state")) in LEGAL_STATES:
:182  rate_legal = (legal / total) if total else 0.0
:193  # ★ 2026-10-09 实测发现：# with_state 会把【字段名叫 state 的内容字段】也算进去
:195  #   ⇒ **唯一合规率是 rate_legal**（值须在合法枚举内），rate_with_state 只作参考。
:196  "rate_is": "rate_legal（唯一合规率：state 值须在合法枚举内）",
```

**本轮实读（黑板，非文件）**：
```
$ curl -s "http://127.0.0.1:8792/data/health/cahac-compliance"
ts: 2026-10-10T23:47:10 | version: 172
  files 2946 | total 6069 | legal_state 280 | with_state 282
  rate_legal 0.046136 | rate_with_state 0.046466
  rate_is: rate_legal（唯一合规率：state 值须在合法枚举内）
```
★ **注意**：本项目前值 **4.61%**（280/6069），**不是 4.19%** —— 会随数据变化。v6 **须以「复跑命令 + 取值时刻」记，不写死数字**（对照 v5 §17.3 时间戳纪律）：
```bash
curl -s "http://127.0.0.1:8792/data/health/cahac-compliance" \
 | python3 -c "import json,sys;d=json.load(sys.stdin);v=d['value'];print(d['ts'],v['rate_legal'],f\"({v['legal_state']}/{v['total']})\")"
```

⇒ **v6 必须显式声明（否则两个数字会被当成同一件事）**：
> **「信封符合度 0%」与「自报合规率 4.6x%」不是同一指标的两次测量，而是两个不同坐标系**：前者量【§3 信封落地】，后者量【§7.2 `state` 枚举合法率】。**二者不可比、不可互换、不可相乘**，写 v6 时须各自标注分母与取值时刻。

---

### ★ CAHAC §18「偏离归属」复测（供 P28 定责复用）

CAHAC v1.2 §18.2 提供了**可复跑判据**，本轮实跑：
```
$ cd ~/dsh-collab && python3 scripts/cahac-clause-ownership-check.py
  条款总数 46 · **enforced 19** · **advisory（缺口）27** · 缺口比 58.7%
```
⇒ 与 v1.2 §18.1 表载 **46 / 19 / 27 / 58.7%** 一致（**独立复跑成立**）。
⇒ 其 §18.4「无执行方类」已点名两项与本章同族：`§7.4 上限与 TTL`（实测超 §7.4 的 100/agent 上限）、`§7.1 目录不存在`。
**本轮补测该项现状**（`~/.dsh/mailbox/` 不存在，故以 `~/.dsh/inbox/` 为实际载体）：
```
$ ls -la ~/.dsh/mailbox/
ls: /Users/coreyleung/.dsh/mailbox/: No such file or directory   [exit 1]     ← §7.1 目录不存在，成立
$ ls ~/.dsh/inbox | wc -l                     → 2957
$ python3 -c "...统计 ~/.dsh/inbox 文件数/行数..."  → 文件数 2956 · 条目 6088
```
⇒ `§7.4`「inbox 上限 100 文件/agent」在实测面（2957 文件）**无对应执行方**；v1.2 §18.4 记录的同口径值（2674 文件 / 5518 条目 @2026-10-09 06:29Z）**已增长**，缺口未收敛。

---

### ★ §11 Agent Card 未实现 —— 复测（实际用 `agent_profile`）

**三态：成立**
```
分母（agent-bus store.profiles）: 82 条
抽样[0]: {"agentId":"session-b241741f-…","role":"守灯塔-mac-mini-系统运维/知识库",
          "abilities":[...6 项...],"resources":[...]}
★ 字段频次: {'agentId':82,'role':82,'abilities':82,'resources':82,'updatedAt':82,'source':82}
★ CAHAC §11 Agent Card 专属四字段(channels/topics/budget/comm_style) 命中: 0 个
★ 非空档案 82/82
```
对照 `cahac-protocol-v1.2.md:451`（§11）要求的 Card 结构 `channels/topics/budget/comm_style` —— **实测 0 命中**。
⇒ §11 Agent Card **未实现**，在位的是**自由文本能力登记表** `agent_profile`（字段仅 `role`/`abilities`/`resources`）。
★ 且 CAHAC v1.2 §18.4 已把此缺口归入「**认证被降级抵消类**」：`§10 白名单 vs §11 无 Card | 两个条款互相抵消` —— 本轮**实现侧独立印证**。

---

### ★ §5 通道选择器：**离线脚本，不在运行时链路**

**三态：成立**
```
$ ls -la ~/dsh-collab/scripts/bb-channel.py
-rw-------@ 1 coreyleung  staff  9120 Oct  9 22:00 /Users/coreyleung/dsh-collab/scripts/bb-channel.py
$ ps aux | grep "bb-channel" | grep -v grep
（无输出，exit 1）                                    ← 无进程
$ grep -rl "bb-channel" ~/Library/LaunchAgents/
（无输出）                                            ← 不在 launchd
$ grep -rn "bb-channel" ~/dsh-collab --include=*.py --include=*.js --include=*.plist -l
scripts/bb-channel.py · scripts/bb-gate.py · docs/bb-channel-README.md
research/agent-network-blueprint-candidate.md · docs/星桥-memory-inheritance-2026-10-08.md · data/blueprint/agent-network-research.md
```
其自身头部即自述为**「发消息前」的离线裁决器**：
> ★ **引文更正（第七轮复核 S2-①，★ 非本轮引入 —— 系上轮遗留 + 上轮复核漏判）**：
> 　· **行域更正**：下方三行**实为源件 `scripts/bb-channel.py:8–:10`**，初稿标 `:10-11` ⇒ ★ 读者按 `:10-11` 去读会读到**另两行**（`已登记` / `请调查`），对不上所引正文。
> 　· **非逐字声明**：源件 `:8`/`:10` **无 `#` 前缀**（`:9` 的 `#` 在 2 空格缩进**之后**）⇒ ★ 下方三行**各加了 `# ` 前缀** ⇒ ★ **属【注释块式转写】，不是逐字引用**（本件 §0.1 的「引文逐字」纪律在此**不适用**，故不标逐字）。
```
~/dsh-collab/scripts/bb-channel.py:8–10（★ 见上方引文更正）
# 用法：
#   # 自动判定类型（基于内容启发式）
#   python3 bb-channel.py --text "已登记 v1.0.354"                  # → blackboard
```
⇒ 通道选择器（§5）**只有离线 CLI 形态**，**无运行时强制点** ⇒ §5 的「硬规则」不具约束力（同族于 §18.4「无执行方类」）。

---

### ★ P28 病理内容补记（R060 · R062，自 §13 迁入）

> ★ **迁入依据**：修订总表 §2.1（2026-10-11）—— **R060 的规则条目体裁取 W3 线**（规则 / 判据 / 证明义务 / 实例 / 理由）⇒ **§13 只留规则条目**；**W2 线自产的病理内容（三层实例 / 危害面 / 建议门）归本节 P28 正文、不在 §13 重复**。
> ★ **搬家方式**：原文**整段迁移、一字未改**（S3「不可自审」下由编辑子代理执行搬迁），仅随修订总表 §2.1 的**全局改号**换编号（映射见该表）。

#### ▶ R060 静默失败禁止 · 三层实例（病理）

| 层 | 实例（证据锚点） | 静默机制 |
|---|---|---|
| **投递层** | `~/dsh-plugin-agent-bus/lib/index.js:577-580`：`catch (e) { msg.lastError = …; return false; }` ⇒ 异常被吞 ⇒ **静默降级 `queued`**。源码自承（`:24`）：`不建立本地绑定 ⇒ deliver() 三处 replyCardHint(...) 抛 ReferenceError ⇒ 被 catch 吞 ⇒ queued ⇒ 跨机投递全挂（我侧 403 条积压同病）` | 异常 ⇒ 降级不可见 |
| **队列层** | `QUEUE_TTL_MS = 7 * 864e5`（`:84`）但**执行时点由偶发触发决定** ⇒ 实测**滞留上界 46.2 天**，2377 条 expired 中 **74.5% 由单次清扫产出** | 过期是**批量事件**，非连续过程 ⇒ 中途无任何信号 |
| **日志层** | `~/dsh-plugin-central-inbox/lib/index.js:467` 打印「→ 回退注入中枢」，而 `route.js:48-49` 对 `unresolvable` 返回 `{target:null, mode:'skip'}` | **日志主动失实**（比不报更坏：排障方向被反转，MBP 已被其误导——见 `index.js:**455**` 自承） |

**危害面**：**可达性 + 信任**（比 R4「仪器失真」更隐蔽——R4 是仪器读数错，R060 是**仪器压根不报**）。

**建议门（可机械核）**：① `expired` 占比设阈并**逐日**留证（非批量后才可见）；② 凡日志中出现「回退/降级/重投」类**动作词**，须有对应代码路径断言（日志-代码一致性门）；③ `catch` 分支落 `lastError` 的比例须 100% 可枚举。

#### ▶ R062 未登记通道 · 危害面与建议门（病理）

**危害面**：**治理 + 变更安全**（是 R6「双轨并存」与 CAHAC §18「无责任方」的**合流形态**）。

**建议门（可机械核）**：① **凡产生副作用跃迁的 actor 必须同时出现在「漂移矩阵」与「变更门枚举」**，差集须为 0（一键判据见 §12 复跑 ②）；② 新 actor 上线前须在 `channel_gate` 登记 owner，否则视为未登记通道并**拒其上线**（把 CAHAC §18 的 `enforced/advisory` 判定前移到运行时）。

---

## §7.10 P28 小结（供 v6 §7 表内使用）

| # | 缺陷 | 三态 | 关键证据锚点 | 危害面 |
|---|---|---|---|---|
| ① | 未登记通道（消费方无属主） | **成立**（口径更正：通道在册、**跃迁方**在册外） | `central-inbox/lib/index.js:44,481` → `agent-bus/lib/index.js:1399,573`；两表并集 13/共有 5 | 归属与变更治理 |
| ② | 离线投递无撤回 + TTL 未确定性执行 | **成立**（+新发现：滞留上界 ~46 天 vs 常量 7 天） | `agent-bus/lib/index.js:84,1308-1312`；撤回面 0 命中 | 消息可达性 |
| ③ | `reply_required` 死字段 | **成立**（+强化：**在册规则的零实现**） | 写 `:1382` / 读 0；规则 `comm-channel-rules-v2:32`；用量 92/564 | 规则可信度 |
| ④ | `awaiting` 无消费者 | **成立** | 三面 54 py / 15 js / 0 plist（80 plist） | 球权语义失效 |
| ⑤ | 失实日志 | **成立** | `central-inbox/lib/index.js:467` vs `route.js:48` | 排障方向反转 |
| ⑥ | 双投去重粒度错 | **成立**（修正：有去重，**粒度＝整卡/整消息**） | `route.js:**92**` · `identity.js:137-141` · `:364`(10min) · `:385`(cap 300) | 重复注入 |
| — | §3 信封符合度 | **0%** | 564 卡 + 33613 消息全量，六字段均 0 | 协议落地 |
| — | §11 Agent Card | **未实现** | `profiles` 82 条，Card 四字段 0 命中 | 能力发现/认证 |
| — | §5 通道选择器 | **离线** | 无进程、无 launchd、仅离线 CLI | 规则约束力 |
| — | §18 偏离归属 | **46/19/27，58.7%** | 复跑 `cahac-clause-ownership-check.py` | 责任方缺口 |

---

## §7.11 P29 假绿族

> **属主**：W3（健康与故障治理线）｜**依据**：本机实测复跑（命令+未编辑输出）｜**样本窗**：截至 2026-10-10 夜
> **纪律**：本文所有数字均标注**所在坐标系**；凡随编辑变化的数字，以**复跑命令**为准（§7.11.9）。
> **三态**：成立 / 不成立 / 不可判。**「不可判」不等于「不成立」**。

### 7.11.0 P29 是什么（与 P27 / P3 / P4 的区分）

**P29 假绿族**：判据**执行了、也确实返回了 `ok`**，但该 `ok` 由**退化的输入**得出，因而**不承载它所声称的结论**。

| 族 | 病灶 | 形态 |
|---|---|---|
| P3 判据假绿 | 判据**没跑**就报绿 | 缺负控 |
| P4 静默失败 | 失败**发生了但没人知道** | 缺读者 |
| **P29 假绿族** | 判据**跑了**，`ok` **恒真**（分母为 0 / 只看成功分支 / 计数器重置 / 空壳响应 / 检查项缺位） | **谓词缺陷** |

⇒ P29 与 M9（静态全绿≠能跑）是**近亲但不同**：M9 是**执行对象错层**，P29 是**谓词本身不许为假**。
⇒ **P29 的判别式**：`ok = true` 的**取值是否依赖于一个可能为空/可被过滤成空的量**？

### 7.11.1 假绿一：C7 遮蔽扫描扫了 0 个包却报 OK ★ **成立**

**判据原文**（`~/dsh-plugin-guard/lib/index.js:356`，`:288-305` 为 `doDepsScan`）：

```js
out.checks.C7_version = { ok: scan.count === 0, mismatches: scan.mismatches.slice(0, 5), count: scan.count };
```

**复现谓词（分母为什么会变成 0 —— 逐级算）**：

| 步骤 | 谓词 | 数（本次实读） |
|---|---|---|
| 0 | `readdirSync(PROFILE_NM)` 全部条目 | **106** |
| 1 | `if (/\.(bak\|pnpmcopy)/.test(name)) continue;` ⇒ 跳过 | **−101** |
| 2 | 余下 | **5** |
| 3 | `if (!st.isDirectory() \|\| st.isSymbolicLink()) continue;` ⇒ 5 项**全是符号链接** | **−5** |
| 4 | `total += 1` 实际累加 | **0** |
| 5 | `count = mismatches.length = 0` | **0** |
| 6 | `ok = (count === 0)` | **恒 `true`** |

**复跑命令（分母实证）**：

```bash
D=~/.dsh/profiles/web/node_modules/@deepseek-ai
ls "$D" | wc -l                                        # 106
ls "$D" | grep -cE '\.(bak|pnpmcopy)'                  # 101
find "$D" -maxdepth 1 -type l | wc -l                  # 5
find "$D" -maxdepth 1 -type l -exec basename {} \;
```

**未编辑输出**：

```
106
101
5
cordis
dsh-api-gateway
dsh-base
dsh-client-runtime
dsh-web-app
```

⇒ **步骤 1 与步骤 3 两个「跳过」串联后，分母精确归零**。剩余 5 项全是指向
`/Applications/CLD.app/.../runtime/node_modules/@deepseek-ai/*` 的软链（即**真身**）——
**唯一值得比的 5 个对象，恰好全被第二个谓词跳过**。

**活体复跑**（`cld_health_check`，2026-10-10T15:53:37Z）：

```json
"C7_version": { "ok": true, "mismatches": [], "count": 0 }
```

**为什么必须改**：`count: 0` 无法区分两种世界 ——
①「比了 N 个包，全一致」（真绿）与 ②「比了 0 个包」（假绿）。
**二者输出完全相同** ⇒ 这不是灵敏度问题，是**判据不含分母**的问题。

**对照 M1–M10**：**M1 成立（因）** —— 101 个 `.bak-*` / `.pnpmcopy-*` 正是 M1「版本遮蔽」的残留物，
而**为遮蔽而写的守卫，反被遮蔽物本身废掉**。**M9 部分成立**（判据只碰了「找不到」的表面）。

**修法（谓词面）**：
1. `doDepsScan` 增加 `degenerate: total === 0`，`ok` 改三态：`total===0 ⇒ ok:null（不可判）`。
2. 软链应**解析后比对**（软链目标即真身，`readlink` 后可取证；或显式走 `RUNTIME_NM` 比对 5 项）。
3. **负控**：构造「全跳过输入」时判据必须指向 `不可判`，**不得**指向 `绿`。

---

### 7.11.2 假绿二：drift 告警跨不了机（stdout 只打印成功侧）★ **成立**

**机制**：**成功分支写 stdout，失败分支写 stderr** ⇒ 读日志的人只读 stdout 即「全绿」。

**复跑命令**：

```bash
grep -o "PUT 200" /tmp/drift-scan-cron.log | wc -l        # stdout 成功侧
grep -o "401"     /tmp/drift-scan-cron.err.log | wc -l    # stderr 失败侧
wc -lc /tmp/drift-scan-cron.log /tmp/drift-scan-cron.err.log
head -5 /tmp/drift-scan-cron.log
```

**未编辑输出**：

```
135                       # stdout: [drift-cron] 告警卡 local PUT 200
134                       # stderr: HTTP Error 401: Unauthorized
  135   --- /tmp/drift-scan-cron.log
 2453   --- /tmp/drift-scan-cron.err.log
[drift-cron] 告警卡 local PUT 200
[drift-cron] 告警卡 local PUT 200
[drift-cron] 告警卡 local PUT 200
[drift-cron] 告警卡 local PUT 200
[drift-cron] 告警卡 local PUT 200
```

> ★ **口径更正**：简报记 134×200 / 133×401；**我再跑得 135 / 134**（`.log` 为 135 行且每行 1 次）。
> 差 1 系该 crontab 仍在跑、期间又追加了一轮。⇒ **凡此数必须以复跑命令为准，不引用本文数字**。
> ★ 另注：`.err.log` **2453 行 / 200,404 字节** ≠ 134 —— 134 是 **401 traceback 块数**，
> 每块含多行 Python 栈。**行数 ≠ 事件数**（见 7.11.6）。

**跨板实况（双板对读，判据=键前缀 `data/ops/drift-alert/`）**：

```bash
curl -s http://127.0.0.1:8792/data/      | python3 -c '...'
curl -s http://106.53.214.108:8792/data/ | python3 -c '...'
```

| 板 | `data/ops/drift-alert/` 卡数 | 最新 ts |
|---|---|---|
| 本机 `127.0.0.1:8792` | **304** | 2026-10-10T23:46:04（**仍在增长**） |
| 中枢 `106.53.214.108:8792` | **19** | 板级 `ts` = 2026-10-03T13:27:35（**冻结**）；★ 同时刻卡内层 `value.ts` = 12:30:49.275，两者差 **56m46s**（须登记） |

⇒ **到达率 19/304 = 6.2%**；**285 张卡只存在于本机**；中枢已停滞 **7.43 天**。
⇒ ★ 中枢 19 张的 ts **全部落在 `13:27:29`–`13:27:35` 六秒窗口内**，
　**形似一次性批量回填**，而非持续同步。**「批量对齐一次」的成因：不可判**（未定位该批次的执行者）。

**对照 M1–M10**：**M1 成立**（通道凭据漂移 ⇒ 401）。**不属 M9/M10** ——
与静态检查、截断均无关，**病灶是「成功/失败进不同 fd」**。

**修法**：① 成功与失败**都写同一投递台账**（含 `ok:false` 显式行）；
② 判据 = `central最新ts` 与 `本地最新ts` 之差，超时即红（**不得只看本地 PUT 200**）；
③ **401 是终态**（凭据坏，重试无用）⇒ 必须告警，重试仅对 5xx/超时开放。

---

### 7.11.3 假绿三：有界重试恒记 1/3（计数器每代重置）★ **成立（机制层）**

**复跑命令**：

```bash
cd ~/dsh-collab/logs
grep -oh "自动重启 [0-9]/[0-9]" node-bridge.log* | sort | uniq -c
```

**未编辑输出**：

```
  12 自动重启 1/3
```

⇒ **四份日志合计 5264 行内，`2/3` 与 `3/3` 出现次数均为 0**。

★ **报「0 条」必须连扫过的面一起打印**：

```bash
wc -l ~/dsh-collab/logs/node-bridge.log{,.1,.2,.3}
for p in "1/3" "2/3" "3/3"; do grep -o "自动重启 $p" node-bridge.log* | wc -l; done
```

| 文件 | 行数 | 字节 |
|---|---|---|
| `node-bridge.log` | 450 | 1,993,925 |
| `node-bridge.log.1` | 1209 | 5,245,100 |
| `node-bridge.log.2` | 1827 | 5,248,131 |
| `node-bridge.log.3` | 1778 | 5,244,155 |
| **合计** | **5264 行**（★ 其自列之和；**现约 5272，以复跑命令为准**） | — |

**扫过的面**：**4 个文件 / 5264 行 / 约 17.7 MB**。`2/3` = 0 · `3/3` = 0。

**复现谓词（为什么判据恒真）**：
计数器每次**从 1 起算** ⇒ 永不抵达 `3/3` ⇒ **永不走「达上限」分支** ⇒
**熔断/求援路径从未被触发**。而 `12 × "1/3"` 全绿的观感，正是「重试机制正常」的假绿。
★ 我**未**在 `node-bridge` 源码内定位该计数器的定义（见 §未核）⇒
**「每代重置」由「12 次 1/3 / 0 次 2/3」强推断，非源码直读**，故机制层**成立**、实现位置**不可判**。

**对照 M1–M10**：**M3 成立**（重启竞态；计数器未跨代持久化），与**P12（陈旧态静默自杀）同族**。

**修法**：① 计数器**持久化单一来源**（文件/registry）；② 达上限时**必须告警**，不得静默再试；
③ 判据 = `2/3` 与 `3/3` **可被观测**（当前为 0 且无解释）。

> ★ **口径更正**：简报记「CLD 启动 806 次 / `自动重启 1/3`×822」。**我在本机 4 份 bridge 日志内复现不到这两个数**
> （实得 12）。该 806/822 可能源于**已轮转的会话记录或另一坐标系**。⇒ **标记「不可判」，不进 v6 正文数字**；
> 但「**计数器不递增**」这一**机制结论由 12×1/3 · 0×2/3 独立支撑**，故本条**仍判成立**。

---

### 7.11.4 假绿四：`/health` 是命名空间列举的假阳性 ★ **成立**

**复跑命令**：

```bash
for p in health stats version data notes tasks; do
  printf "%-8s -> " "$p"; curl -s -o /tmp/_r.json -w "%{http_code} " "http://127.0.0.1:8792/$p"; head -c 120 /tmp/_r.json; echo
done
```

**未编辑输出**：

```
health   -> 200 {"limit":null,"list":{},"offset":0,"total":0}
stats    -> 200 {"limit":null,"list":{},"offset":0,"total":0}
version  -> 200 {"limit":null,"list":{},"offset":0,"total":0}
data     -> 200 {"limit":null,"list":{"data/ack/92623479":{"ts":"2026-08-23T18:15:32",...
notes    -> 200 {"limit":null,"list":{"notes/2a15e6b1/hr-pending-consolidated-...
tasks    -> 200 {"limit":null,"list":{"tasks/a3bc8cba/queue/17876726793N":{...
```

**谓词**：黑板对**任意**首段（`[a-z]+`）都返回 **HTTP 200 + `{list:{},total:0}`**。
⇒ **HTTP 200 只证明「8792 端口在听」**，**不证明** `/health` 这个**健康探针**存在或健康。

**反例（最强的一点）** —— `total:0` **不是因为「没有健康数据」**：

```bash
curl -s http://127.0.0.1:8792/data/ | python3 -c "
import sys,json; d=json.load(sys.stdin); ks=list(d['list'])
print('data/ 键总数:',len(ks))
print('其中名字含 health:',len([k for k in ks if 'health' in k.lower()]))
print('形如 */health 的:',len([k for k in ks if k.endswith('/health')]))"
```

**未编辑输出**：

```
data/ 键总数: 33625
其中名字含 health: 93
形如 */health 的: 0
```

> ★ **口径更正（2026-10-11）**：上「形如 `*/health` 的」数**由 5 更正为 0**（该命令谓词为 `k.endswith('/health')`）——
> **6 种谓词实测 0 / 3 / 0 / 13 / 93 / 76，无一为 5**；原「5」在该谓词下不复现。

⇒ 健康数据**确实存在**（93 个含 health 的键），只是**不叫 `/health`**。
`/health` 的 `total:0` 是**命名空间名与数据不同名**的假阳性，**不是健康缺失的证据**。

**对照 M1–M10**：**M9 成立** ——「探测返回 200」被当作「服务健康」，
但 200 的执行对象是**键列举**，结论是**健康** ⇒ **不同层**。

**修法**：探针必须 `assert` **确定的键存在且内容非空**；
**负控**：喂空内容时探针必须红。

---

### 7.11.5 假绿五：`cld_health_check` 全绿，而零条通讯通道检查 ★ **成立**

**判据原文（穷举）** —— `~/dsh-plugin-guard/lib/index.js` 内**全部** `out.checks.*` 赋值：

```bash
grep -n "out.checks\." ~/dsh-plugin-guard/lib/index.js
```

**未编辑输出**：

```
344:  out.checks.C1_boot = judgeC1(em, _traceLines);
349:    out.checks.C2_heartbeat = { ok: ageSec < 180, age_sec: ageSec, pid: hb.pid };
353:  out.checks.C3_data = { ok: sessionCount > 0, sessions_on_disk: sessionCount, workspaces };
356:  out.checks.C7_version = { ok: scan.count === 0, ... };
```

⇒ **全部检查项恰为 4 个**：`C1_boot` · `C2_heartbeat` · `C3_data` · `C7_version`。
★ **无 C4/C5/C6**（命名从 C3 跳到 C7）。

**活体复跑**（`cld_health_check`，2026-10-10T15:53:37Z）：

```json
{ "checks": { "C1_boot": {"ok":true}, "C2_heartbeat": {"ok":true,"age_sec":6},
              "C3_data": {"ok":true,"sessions_on_disk":469,"workspaces":2},
              "C7_version": {"ok":true,"mismatches":[],"count":0} },
  "all_ok": true }
```

**两个独立缺陷**：

1. **`all_ok` 由退化项满足**：`out.all_ok = Object.values(out.checks).every(c => c.ok)`（`:362`）。
   当 `C7_version` 因 7.11.1 **恒真**，`all_ok` 就**不再要求任何遮蔽证据** ⇒ 顶层「全绿」是**空集绿**。
2. **零条通讯通道检查**：**无** drift 双板到达 · **无**投递真达率 · **无** inbox 积压 · **无** launchd 失败终态。

**跨设备偏斜未被发现的谓词** —— `doHealthCheck()` 只读**本机 `homedir()`**：

```bash
grep -n "homedir()" ~/dsh-plugin-guard/lib/index.js | head
```

```
21:const GUARD_DIR = join(homedir(), "dsh-collab", "guard");
24:const MIRROR_ROOT = join(homedir(), "tech-research"); // 官方文档镜像（MBP 有；mini 可走 --web）
25:const CLD_LOG_DIR = join(homedir(), ".cld", "logs");
26:const SESSIONS_DIR = join(homedir(), ".dsh", "sessions");
28:const PROFILE_NM = join(homedir(), ".dsh", "profiles", "web", "node_modules", "@deepseek-ai");
```

⇒ 函数体内**无任何** peer / 中枢 / 远端口（`106.53.214.108`、`8792`）比对。
⇒ **「跨设备版本偏斜」在本机结构上不可被本检查发现** —— 这是**结构性结论**，不依赖对侧实测。

**对照 M1–M10**：**M1 不成立（此子项）** —— 偏斜**未被检测**，**非**被检测为一致；
本项成立的是「**检查面缺位**」。**M6 成立**（改完只验 C1–C7 四项即宣告健康）。

**修法**：① `C7` 三态化；② 新增 `C8_comm`（drift 双板 + 投递台账，断言而非列举）与 `C9_probe_delivery`；
③ 顶层「全绿」须以**负控曾红过**为前提，否则标 `unverified`。

---

### 7.11.6 ★ 自查：我自己犯过的同族错（口径纪律）

本节写的是**假绿**，编者须先自查**自己的眼睛**：

- **`grep -c` 数的是「行」不是「次」**：`node-bridge.log.2` 1827 行内实含 **4** 次 `自动重启 1/3`；
  若按行数报，会把 **4 读成 3**。⇒ **本文一律用 `grep -o ... | wc -l`**。
- **`wc -l` ≠ 事件数**：`.err.log` 2453 行只含 **134** 个 401 事件（每事件多行栈）。
- ⇒ 此二项与 **M10（静默截断）不宜混为一谈**，但**同属「读数被当作事实」**族，故在此标注。

### 7.11.7 对照 M1–M10 归类总表（★ 含明确「不成立」）

| 模式 | 判定 | 依据（可复跑） |
|---|---|---|
| **M1** 版本遮蔽/漂移 | **成立** | 106 项中 101 项为 `.bak-*`/`.pnpmcopy-*` 遮蔽残留（`ls "$D" \| grep -cE '\.(bak\|pnpmcopy)'` = 101）；drift 跨板 401；跨设备偏斜无检测 |
| **M2** 全量物化内存失控 | ★ **不成立** | `~/.cld/logs/memory-trend.json` 样本 **32736** 条（2026-09-04 **首样本 12:12:48Z** → 2026-10-10T15:54Z）· **max rss 342 MB · max heap 12 MB · heap_limit 4192 MB**；★ **采样面须声明**：全程含 **28 处 >10 min 空档**，窗口内最长空档 **833.5 min（≈13.9 h）** ⇒ 结论方向成立，但**不构成「全窗覆盖」**（★ 此点不得省略） |
| **M3** 重启竞态 | **部分成立** | 计数器 `1/3`×12 / `2/3`×0 / `3/3`×0（4 文件 5264 行）⇒ 未跨代持久化，与 P12 同族 |
| **M4** 插件加载协议不符 | ★ **不成立** | 五处假绿**无一处**由插件 apply/boot 崩溃引起 |
| **M5** 凭旧认知修 | **部分成立** | C7 用「`count===0` 即无遮蔽」的旧式空集判据；digest 用 `/usr/bin/env node` 而未核 launchd PATH |
| **M6** 改完不验证/不留痕 | **成立** | `cld_health_check` 仅 4 项即宣告 `all_ok`；只写不读读者（见 12 健康面探针投递率） |
| **M7** 层错 | **成立** | 7.11.4：**200 答的是「键列举」，被当「健康」** |
| **M8** 位置偏置 | ★ **不可判** | ★ **原判「不成立」依据不足**（该行无命令、无扫过的面，把「无证据」当「不成立」——与本稿 M10 行「未定位⇒不可判」自相矛盾）。⇒ 记**不可判**：未发现该形态，但未穷举扫描面 |
| **M9** 静态全绿≠能跑 | **成立** | 四文件 5264 行全绿，而真故障（401/127/计数器）在其中不可见；1209+1827+1778 行是**已轮转历史**，非当前健康 |
| **M10** 静默截断 | **成立** | ★ **理由已由 R1 证伪原判**：`~/dsh-plugin-guard/lib/index.js:356` 的 `mismatches.slice(0, 5)` **就在 C7 判据行内**（本稿 §7.11.1 自己引过）；且 `:342` 的 `…split("\n").slice(-2000)` 喂 **C1_boot**（`all_ok` 四分之一）**且不计数不标注** ⇒ 按 M10 定义即 SILENT |

> ★ **不成立项汇总：M2 · M4**；**不可判：M8**；**M10 已改判成立**（理由见上表）。
> ★ **`archaeology.js` 只实现 M1–M6**（`grep -c 'id: "M' → 6`）——
> 任务所称的「可执行版含 M1–M10」**不成立于代码层**：M7–M10 **仅存在于文档**（`failure-pattern-library-20261004.md:67-118`）。
> ⇒ 这本身是**§7.11 的一个新实例：注释/文档宣称十，代码实为六**（与 v5 §10「30 项 vs 39 项」**同族**）。

### 7.11.8 ★ 根因链「探测在、投递断、无人知」——每一环归谁修

```
   探测在              投递断                无人知
  ┌────────┐        ┌──────────┐        ┌──────────┐
  │ 手段存在 │───X───▶│ 断路处     │───X───▶│ 无义务人   │
  │ 判据恒真 │        │ 有技术根因 │        │ 无台账/升级│
  └────────┘        └──────────┘        └──────────┘
     要【修谓词】         要【修链】           要【加人】
```

| 环 | 三态 | 具体缺陷 | 归谁修 | 「加人」**还是**「修链」 |
|---|---|---|---|---|
| **探测在** | **成立** | 手段**齐备**：C1/C2/C3/C7 + drift cron + digest plist；**未被删除** | **守卫属主**（`dsh-plugin-guard`） | ★ **既非加人也非修链 —— 是修谓词**（`ok` 三态化 + 负控 + 解析软链） |
| **投递断** | **成立** | ① drift 中枢 **401**（凭据）② digest `/usr/bin/env node` ⇒ `exit 127`（launchd PATH）③ launchd 失败终态无告警 | **通道属主 / 运维**（各自 plist 与通道属主） | ★ **修链**（技术上可完全修复，与人数无关） |
| **无人知** | **成立** | **无指定义务人** · **无告警台账** · **无升级路径** | **治理层（用户裁决）** | ★ **这是唯一真正「要加人」的一环** |

**链条结构性根因（原文实读）** —— `~/dsh-collab/data/local-registry-index.json:5761`：

```
"desc": "v1.0.115 · **推送范围调整**（用户指令）：**系统运维类暂停**
（#7 dsh-health/#10 CLD 看门狗/#15 远程告警/#17 health-check/#20 sysops 及健康巡检类）；**业务侧继续**"
```

⇒ **暂停的恰是「投递与值守」类推送**（远程告警/看门狗/health-check），**探测类未停** ⇒
**精确地造出「探测在、投递断、无人知」三者之间的那一刀**。

★ **原始决策卡：不可判（标未核）**。扫过的面已打印——

| 面 | 文件数 | 命中 |
|---|---|---|
| `~/dsh-collab/data/registry/` | 94 | **0** |
| `~/dsh-collab/data/iterations/` | 2 | **0** |
| `~/dsh-collab/notes/` | 78 | **0** |
| 名含 `20260817` 的卡 | **0** | — |
| `local-registry-index.json` | — | **命中 1**（第 5761 行，**索引描述**，非决策卡本身） |

⇒ **索引里有这句，原始决策卡不在上述 174 个文件内** ⇒ **「未定位」成立，成因不判**。

### 7.11.9 复跑命令（★ 取代一切写死数字）

```bash
# 假绿一：分母为何为 0
D=~/.dsh/profiles/web/node_modules/@deepseek-ai
echo "总=$(ls $D|wc -l) 跳过1=$(ls $D|grep -cE '\.(bak|pnpmcopy)') 跳过2(软链)=$(find $D -maxdepth 1 -type l|wc -l)"
# 假绿二：成功/失败分属两个 fd
grep -o "PUT 200" /tmp/drift-scan-cron.log | wc -l
grep -o "401"     /tmp/drift-scan-cron.err.log | wc -l
# 假绿三：计数器（★ 用 -o，勿用 -c）
grep -oh "自动重启 [0-9]/[0-9]" ~/dsh-collab/logs/node-bridge.log* | sort | uniq -c
# 假绿四：空壳响应 vs 真实健康数据
curl -s http://127.0.0.1:8792/health | head -c 80; echo
curl -s http://127.0.0.1:8792/data/ | grep -o "cld-health" | wc -l
# 假绿五：检查项穷举 + 跨设备比对缺位
grep -n "out.checks\." ~/dsh-plugin-guard/lib/index.js
grep -n "homedir()"    ~/dsh-plugin-guard/lib/index.js
# 各语言包软链自证（I/O 抽检）
readlink ~/.dsh/profiles/web/node_modules/@deepseek-ai/dsh-web-app
```

### 7.11.10 未核清单（**不写进结论**）

| 项 | 状态 | 为什么 |
|---|---|---|
| 中枢 19 张卡「一次性批量回填」的执行者 | **不可判** | 仅由「ts 全落 13:27:29–13:27:35 六秒窗」推断，未见批次记录 |
| 「CLD 启动 806 次 / 1/3×822」 | **不可判** | 本机 4 份 bridge 日志复现为 12；数字或属已轮转坐标系 |
| 「过期消息静默丢弃 271,198 条」 | ★ **数字不可判 / 现象成立** | ★ **载体找错更正**：本机 `~/.dsh/central-inbox.log` 确无 `expired`/`过期`（全量扫，**0** 命中），但**真实载体是 `~/.dsh/agent-bus.json`** —— 实测 `status=="expired"` **恰 2377 条**（均带 `expiredAt`；★ **口径更正（外部复核 N4）**：`expiredAt` 区间 = **2026-10-02T04:34:05 → 2026-10-10T18:17:32**，`time` 区间 = **2026-08-17T00:42:19 → 2026-10-03T18:16:42** —— 原写「2026-08-17→10-03」是 **`time`** 的区间，**不得挂到 `expiredAt` 上**，与 §7.10 保持一致）；**本稿 W7.5/§12.H.2 与 W1 M4③ 讲的正是这条路径** ⇒ 该现象**成立**，仅 **271,198** 这个**数字不可判** |
| 跨设备版本偏斜 `central-inbox 0.2.14 vs 0.2.15` | **不可判** | 未取得对侧实测；**但「本检查无跨设备比对」为结构性成立**（★ 实测为 `:21/24/25/26/28` —— 原标 `:25-29` 系陈旧，据 R1 复核更正） |
| MBP 侧 `drift-scan` 12 项 / `channel_gate` 7 通道 | **不可判** | 属对侧资产，本机未取证 |

# §8 目标、原则、成本模型

**七目标**：G1 可信 · G2 有界 · G3 可退 · G4 根因受控 · G5 可观测 · G6 可治理 · **G7 连续性**。
**六原则**：① 优势优先 ② 开源优先→过渡自研 ③ 判据先行 ④ 不得制造同类问题（R022）⑤ 不依赖记性 ⑥ **一切产物先沙箱模拟、再经独立审查员逐个审查（信息包给足）**。
★ **v5 注**：原则③「判据先行」与④「不得制造同类问题」在本样本窗内**各被违反一次**（P27 即 R022 的自我实例）⇒ 两条标为**本版首要自查项**。
**成本权重**（CAHAC §5.2）：广播 10.0 ≫ p2p 1.0 > 事件总线 0.5 > 黑板写 0.1 / 读 0.05 > 邮箱 0.05。

---

# §9 架构（L0–L6 + I1–I4）

```
L6 连续性层  锚点·索引·续接·自启动·反遗忘·证伪门
L5 治理层    规则账本·验收门·命名门·名册·样本窗·审计留痕 + §5 审查流水线 + §6 官方校对门
L4 观测层    storm_score·队列滞后·机制激活计数·子进程内存·装载事件数·cron·告警
L3 上下文层  compaction（必须挂载）+ 约束钉住 + 体积/事件数 SLO + 投影（中期）
L2 拥塞层    反压·token bucket·优先级/公平·熔断·泄洪态
L1 传输层    SQLite/WAL 邮箱（已建）+ 持久幂等键 + DLQ + 信封 + 时序
L0 节点层    节点注册·心跳 SLO·HMAC 身份·归属双载体·端口稳定
```
**I1** 载体不得整份读入回写（零 torn read）· **I2** 入站串行（活跃 claim≤1）· **I3** 失败谱系（新 attempt 不覆盖，DLQ 可枚举可回放）· **I4** 投递≠消费（`done` ⟹ delivered ∧ agent receipt）。

---

# §10 WBS（**39 项** + v5 状态重标）

> ★ **计数更正（v5 自认，2026-10-10）**：表头原写「30 项」——**该数字未经清点，系从 v4 承继**。实测 §10 实列**唯一 W 编号 39 个**（W0.1–W0.6 · W1.1–W1.8 · W2.1–W2.10 · W3.1–W3.3 · W4.1–W4.6 · W5.1–W5.6）+ S1–S5。
> ⇒ 与 P27 同族：**把没数的当数过的写出来**。

> 状态来源标注：`[实测]` = 本轮实跑/实体核对；`[转述]` = 引自交付说明未复核；`[未测]` = 未验证。

- **Wave S（门，适用于其余每一项）** —— ★ **`blocked` → 工具面已交付** `[实测]`
  - S1 沙箱模拟框架 ✅ `sandbox-script.py` · S2 信息包模板 ✅ `infopack-check.py` · S3 独立审查流程 ✅ `review-gate.py`（依据更正为 `R048`）· S4 官方规范校对门 ✅ `official-ref-gate.py` · S5 **G-CR 校验脚本（实列 17 条**，非「十五条」）✅ `gcr-gate.py` · **覆盖 17 条**（机械化 10 · `N-A` 7）
  - 增① 身份声称门 ✅ `node-claim-gate.py` · 增② 自指破坏门 ✅ `self-destruct-gate.py` + **`R059`**
  - ★ **未关**：七件均**缺独立 verifier** ⇒ 整体 **`in_flight`，不得记 closed**
- **Wave C（信标）** —— `in_flight`
  - C1 索引键（✅ closed `[实测]`，★ **无 verifier 字段**）· C2 锚点文档（✅ closed，本文件即 v5 锚点）
  - C3 续接提示词（✅ closed，★ verifier 标「待第三方复核」）· C5 反遗忘校验（✅ closed，★ verifier 同上；**判据有缺口 ⇒ P27**）
  - C6 状态机登记（🟡 in_flight）· C7 证伪门与半修清单（🟡 in_flight，第 10 条半修已补）
  - **C4 自启动注入** ❌ `open` —— **需改 CLD preset**，外部第三方不代做
- **Wave 0（开关合上+可观测）** —— `open`（W0.1 挂载 compaction+约束钉住 · W0.2 定位现存压缩来源 · W0.3 机制激活计数 · W0.4 注入器合并 · W0.5 子进程内存监控 · W0.6 装载前事件数门）
- **Wave 1（P0）** —— `open`（W1.1 持久幂等键 · W1.2 熔断 · W1.3 根因指标 · W1.4 floodgate 改造 · W1.5 L4 可观测化 · W1.6 `expires_at`+DLQ · W1.7 accumulator upsert+rotation · W1.8 定位 inbox 物化点）
- **Wave 2（结构性；含唯一高危）** —— `open`（W2.1 token bucket · W2.2 优先级/公平 · W2.3 inbox 分箱四件套 · W2.4 泄洪态 · **W2.5 载体换 SQLite（独立窗口+回滚演练）** · W2.6 DLQ 重放 · W2.7 两级确认 · W2.8 大对象外置 · W2.9 TTL/lease · W2.10 周期键改覆盖式+历史另存）
- **Wave 3（可信）** —— `open`（W3.1 X-Writer HMAC · W3.2 identitySource 入卡 · W3.3 归属四级分档）
- **Wave 4（跨设备/载体）** —— `open`（W4.1 端口固定 · W4.2 黑板 GC · W4.3 ts+HLC · W4.4 换代率告警 · W4.5 凭据纪律 · W4.6 订阅唤醒 PoC）
- **Wave 5（长期）** —— `open`（W5.1 判据入工具 · W5.2 规则标样本窗 · W5.3 能力前置清单 · W5.4 名册扩席 · W5.5 会话改投影 · W5.6 OTel）

## ★ 10.1 依赖链（v5 更新实测状态）
```
Wave S 的门 ✅已建 ──解锁──> Wave 0 及以后（★ 但需独立 verifier 才算 close）
C7 verifier 未定 ──阻塞──> Wave C 无法整体 close
P1 停点 ──阻塞──> P2
P0 锚点升版 ⇦ 本次执行 ──解锁──> C6/C7/P26 状态同步进 continuity-index
Q-K 三件接线 ──进行中──> P26 治本；① 未独立验证前 enableGuard 保持 false
```

## ★ 10.2 `starbridge-next-stage-plan` 三方案的实测归宿（照录原方案 + 现状）
| 方案 | 原建议 | 实测归宿（2026-10-10） |
|---|---|---|
| **A 建 Wave S 的门** | 主推，可自主，排第 2 | ✅ **已由 10-10 03:31 交付做完**（该计划 10-09 22:07 成文时尚写「无脚本」） |
| **C 补负控** | 排第 1（全部声称的前置） | 🟡 **部分完成**：七件工具全部走完 R006 §5 三步；★ **补课本身抓出 7 个问题** |
| **B 处理紧迫活故障** | 排第 4（须批） | ❌ **未动**：死会话死后仍被点火 **9 次全失败**、turn→**11178**；`~/sb-mobile/server.js` **PID 1250**；`main-roles.json` 第二份角色映射 |

---


## §10 通讯类 W 项（追加）

> ★ **编号纪律（核实后执行）**：已读 v5 §10（`:380-401`）核对，v5 §10 **实列唯一 W 编号 39 项**
> （W0.1–W0.6 · W1.1–W1.8 · W2.1–W2.10 · W3.1–W3.3 · W4.1–W4.6 · W5.1–W5.6）+ S1–S5。
> ⇒ **本节只追加新编号，自 `W6.1` 起，不重编号、不改既有 39 项**；凡能归属既有项的**显式标注归属**，避免同一工作两处立账。

**归属对表（先判后立，避免重复建账）**：

| 新增项 | 归属既有项？ | 裁决 |
|---|---|---|
| W6.1 跃迁方属主登记 | 相邻 **W4.6**（订阅唤醒 PoC） | **新立**（W4.6 是**建能力**，W6.1 是**登记与定责**，交付物不同） |
| W6.2 双板到达率 SLO 化 + FAIL 归因 | 相邻 **W4.4**（换代率告警） | **新立**（W4.4 量「换代率」，W6.2 量「到达一致性」） |
| W6.3 队列 TTL 确定性执行 | **归属 W1.6（`expires_at`+DLQ）+ W2.9（TTL/lease）** | **不再立新账**——仅**补交付判据**（见 W6.3 条目内「并入」说明） |
| W6.4 `reply_required` 落实现或注销 | **归属 W3.3**（归属四级分档）无关 | **新立**（属「规则-实现一致性」，v5 无对应项） |
| W6.5 `awaiting` 消费者或注销 | 无 | **新立** |
| W6.6 日志-代码一致性门 | 相邻 **W1.3**（根因指标） | **新立**（W1.3 建指标，W6.6 治**失实**） |
| W6.7 去重粒度升为内容项 | **归属 W1.1（持久幂等键）** | **不再立新账**——**补交付判据**（见 W6.7 条目内「并入」说明） |
| W6.8 信封落地上线 | **归属 W8.1（建尺）/ W8.2（inbox 注入）** | ★ **不再立新账**（见 W6.8 条目内「归属」说明）—— W3.1/W3.2 是其两个**字段级子件** |

---

### W6 段（通讯面，本轮新增）

- **W6.1 跃迁方属主登记（治 P28-① / R062）** —— `open`
  - **交付**：凡产生**有副作用跃迁**的 actor（首例：`dsh-plugin-central-inbox`）须在**两表同时**登记 owner：`drift-scan` 矩阵 + `channel_gate` 冻结枚举。
  - **DoD**：§12 复跑 ② 输出「仅 gate / 仅矩阵」两个差集**均为空**；`central-inbox` 在两表各 ≥1 条且含 owner。
  - **现状基线**：共有 5 / 并集 13 / 该 actor **0 条登记**（2026-10-10 实测）。
  - **复跑**：§12 复跑 ② 。
  - **反例（负控）**：仅把 `sse-8803` 改名或加注释 **不满足**——本项要的是**跃迁方（consumer）**的 owner，不是通道名的 owner。

- **W6.2 双板到达率 SLO 化 + FAIL 逐条归因（治 P28-⑥ 的可观测前置）** —— `open`
  - **交付**：把 `logs/bb-card-send.log` 的 `boardsMatch`/`result` 变为**可查 SLO**；35 条 `FAIL` 逐条归因（区分：网络 / 中枢 401 / 双写中途失败）。
  - **DoD**：双板到达且一致率 **≥99.5%**，且 `FAIL` **0 条无归因**。
  - **现状基线**：**772/807 = 95.7%**；`result` = OK 771 · **FAIL 35** · OK-WITH-TIMEOUT 1（2026-10-10T23:51Z）。
  - **复跑**：§12 复跑 ① 。
  - **反例（负控）**：仅提高重试次数**不算达标**——本项要「FAIL 可见且有归因」，不是「把 FAIL 掩盖成更晚的 FAIL」。

- **W6.3 队列 TTL 确定性执行** —— `open`（★ **并入 W1.6 / W2.9，不另立交付**）
  - **归属说明**：W1.6（`expires_at`+DLQ）与 W2.9（TTL/lease）**已覆盖 TTL 机制**，本处**不重复建账**，仅**补两条交付判据**（W1.6/W2.9 原判据未含「执行时点」与「滞留上界」）：
    1. **执行时点确定性**：`flushQueue` 须有**周期触发源**（timer/cron），不得仅依赖 `load/sendMessage/lock/unlock/HTTP`；判据 = **无单次清扫占比 >10%**。
    2. **滞留上界可核**：`expired` 的 `expiredAt − time` 最大值 **≤ `QUEUE_TTL_MS` + 容差**。
  - **现状基线**：常数 **7 天**，实测滞留上界 **46.2 天**；2377 条 expired 中 **1771 条（74.5%）由单次清扫（2026-10-02 04:34:05）产出**。
  - **复跑**：§12 复跑 ⑥ 。
  - **反例（负控）**：把 `QUEUE_TTL_MS` 调大 **不算修复**——本项治的是「执行不确定」，不是「期限太短」。

- **W6.4 `reply_required` 落实现或从规则注销（治 P28-③）** —— `open`
  - **交付**：二选一**并同步两侧**——(a) 在 `deliver()` 中**增读** `msg.replyRequired` 并给出**可观测语义**（如「要求回执」标记 + 回执超时告警）；或 (b) 从 `comm-channel-rules-v2-20261002.md:32` **注销**该行并在协议中标注「唤醒已默认」。
  - **DoD**：**规则文本与代码判据一致**（同一判据可机械核）；`reply_required` 的**读取点 ≥1**（若选 a）或**规则命中 0**（若选 b）。
  - **现状基线**：写入点 **1**（`agent-bus/lib/index.js:1382`）· 读取点 **0** · 规则在册 **1 行**（v2 `:32`）· 实际用量 **92/564 张卡**。
  - **复跑**：`grep -n "reply_required" ~/dsh-plugin-agent-bus/lib/*.js ~/dsh-collab/docs/comm-channel-rules-v2-20261002.md`（当前 6 命中，**全为写/schema/注释，无读**）。
  - **反例（负控）**：只删代码或只改文档**任一单边**均**不达标**——本项治的是**分叉**，单边消除不解决分叉。

- **W6.5 `awaiting` 消费者顶班或注销（治 P28-④）** —— `open`
  - **交付**：二选一——(a) 建**常驻消费者**，把 `awaiting` 变成可查询的「球权在谁」并在超时未回时**主动告警**；或 (b) 承认其为「写时校验用字段」，从通讯规则中**降级为 advisory** 并停止以「球权」语义引用。
  - **DoD**：**daemon 面命中 ≥1**（若 a）或 **规则面引用 0**（若 b）。
  - **现状基线**：三面扫描 **py 54 / js 15 / plist 0**（面：`~/dsh-collab/**/*.py` 排除 node_modules · `dsh-collab + agent-bus/lib + central-inbox/lib` 的 `*.js` · `~/Library/LaunchAgents/com.dsh.*.plist` 共 **80 个**）——**消费者 0 个**。
  - **复跑**：§7.10 P28-④ 的复跑命令。
  - **反例（负控）**：仅**新增校验器**不算达标——本项要的是**消费者**（消费球权），不是**再拦一次**。

- **W6.6 日志-代码一致性门（治 P28-⑤ / R060）** —— `open`
  - **交付**：对日志中的**动作词**（`回退`/`降级`/`重投`/`注入中枢`/`已送达`）建立**机械门**：每个动作词须能指向**一条可达代码路径**；否则该日志行**不得合并**。
  - **DoD**：门可跑且**当前已知违例为 0**（首例 `central-inbox/lib/index.js:467` 已修）。
  - **现状基线**：**1 个已确证违例**（`:467` 打印「回退注入中枢」vs `route.js:48` `不再静默回退`），**且已造成实际误诊**（`index.js:**455**` 自承「MBP 实测被其误导去怀疑回退逻辑仍在」）。
  - **复跑**：`grep -n "回退注入中枢" ~/dsh-plugin-central-inbox/lib/index.js && sed -n '46,50p' ~/dsh-plugin-central-inbox/lib/route.js`
  - **反例（负控）**：把日志改成**更模糊的措辞**（如「走替代路径」）**不算修复**——本项治的是**失实**，模糊化只是把可判变成不可判。

- **W6.7 去重粒度升至【内容项】** —— `open`（★ **并入 W1.1 持久幂等键，不另立交付**）
  - **归属说明**：W1.1（持久幂等键）**已覆盖去重机制**，本处**不重复建账**，仅**补三条交付判据**（W1.1 原判据未含「粒度」「窗口」「容量」）：
    1. **粒度 = 内容项**（非整卡/整消息）：一张卡内重复的**内容项**不得二次注入。
    2. **窗口**：`DEDUP_WINDOW_MS`（现 **10 分钟**）不得小于**同一内容的最短重建间隔**（实测存在「同卡重建」形态，间隔可跨窗口）。
    3. **容量**：`store.dedup` 上限（现 **300**）须与**在役消息量**同阶（现 33613），或改为**内容指纹持久集合**。
  - **现状基线**：卡层 `dk = key + '#' + fp`（`route.js:**92**`，**整卡 JSON 指纹**）· 消息层 `f|t|contentFingerprint(text)`（`identity.js:137-141`，**整消息指纹**）· 窗口 **10 min**（`:364`）· 容量 **300**（`:385`）。
  - **复跑**：§7.10 P28-⑥ 的复跑命令。
  - **反例（负控）**：把窗口调大或容量调大**不算达标**——本项的核心判据是**粒度**；若粒度仍为整卡，则「半重复卡」依旧必漏（放大窗口只会更漏）。

- **W6.8 §3 信封落地上线** —— `open`（★ **归属 W8.1 建尺 + W8.2 inbox 注入，不另立交付**；本处只补：字段子集建议 `cahac`/`channel`/`dedup_key`，且**卡面与消息面须同时非 0**）
  - **交付**：选定**最少可行子集**先行落地（建议：`cahac` 版本号 + `channel` + `dedup_key` 三字段，因三者**已有实现侧对应物**：版本可自 v1.2、通道可自现有枚举、`dedup_key` 可自 `identity.js` 现有指纹），并在**分通道**设阶梯目标。
  - **DoD**：§12 复跑 ④ 的**六字段符合度从 0% 变为 >0**，且**单调上升**；所选子集字段在**卡面与消息面同时**非 0。
  - **现状基线**：**0%**——面 A 卡 **564**（`cahac`/`channel`/`sender`/`recipient`/`dedup_key`/`signature` **各 0/564**）· 面 B 消息 **33613**（同六字段**各 0/33613**）· 全量、**无抽样**。
  - **复跑**：§12 复跑 ④ 。
  - **★ 与既有项的边界**：**W3.1**（X-Writer HMAC → 对应 `signature`）与 **W3.2**（identitySource 入卡 → 对应 `sender`）是**本项的两个字段级子件**；W6.8 负责**其余四字段（`cahac`/`channel`/`recipient`/`dedup_key`）+ 整封一致性**。**执行顺序建议：W6.8 先行**（字段少、风险低、可观测），W3.1/W3.2 后续并入。
  - **反例（负控）**：只在**一处**（如只发卡侧）加字段**不算达标**——本项判据要求**卡面与消息面同时非 0**，否则又是「双轨」。

---

### §10 计数（实点后写入，**不在描述里写死**）

> 依 v5 §10 计数事故教训（表头写 30 实为 39），本节数字**须由命令实点**：
```bash

> ★ **计数实点（v6，由命令实点，不手写）**
> · v5 既有 W 编号（W0–W5）：**39** 个
> · v6 新增：**W6 = 8**（W6.1–W6.8）· **W7 = 11**（W7.1–W7.11）· **W8 = 14**（W8.1–W8.14）
> · **合计唯一 W 编号 = 72**
> 复跑：`grep -oE 'W[0-9]+\.[0-9]+' <本文件> | sort -u | wc -l`
> ⇒ 依 v5 §10 计数事故教训（表头写 30 实为 39）：**本节数字须由命令实点，不得手写。**

# 追加项数（本节新增）
grep -c '^\- \*\*W6\.' <本节正文>
# v6 §10 唯一 W 编号总数（合并后整体实点，勿手写）
grep -oE 'W[0-9]+\.[0-9]+' ~/dsh-collab/docs/distributed-agent-network-governance-plan-v6-*.md | sort -u | wc -l
```
> **本轮新增**：`W6.1–W6.8` 共 **8 条**，其中 **3 条（W6.3 / W6.7 / W6.8）标注归属既有项、不另立交付**，**5 条为新立交付**（W6.1 · W6.2 · W6.4 · W6.5 · W6.6）。
> ⇒ **v5 §10 的 39 项不变**，v6 合并后总数以**上面第二条命令实点**为准。


## §10 健康类 W 项（追加）

> ★ **编号纪律**：v5 §10 实列 **39 项**（W0.1–W0.6 · W1.1–W1.8 · W2.1–W2.10 · W3.1–W3.3 · W4.1–W4.6 · W5.1–W5.6）+ S1–S5。
> **本节只追加，不改/不删/不重编号任何既有项**。新增段 = **W7.x**（健康面）。
> **归属既有项者只做标注**（见 W7 末尾「归属既有项（不新增）」）。

### ★ W7 段（新增 · 健康面 / P29 假绿族专项）

- **W7.1 [P0] `doDepsScan` 分母三态化** —— 谓词缺陷（假绿一）
  - 现状：`ok = (scan.count === 0)`（`~/dsh-plugin-guard/lib/index.js:356`）；分母经 101+5 两次跳过归零。
  - 动作：返回 `total` 与 `degenerate`；`total===0 ⇒ ok = null`（不可判）；解析软链后比对真身。
  - 判据：构造「全 `.bak`」假 profile ⇒ 必须 `null`，**不得** `true`。
  - 复跑：`~/.dsh/profiles/web/node_modules/@deepseek-ai` 三项计数（§7.11.9）。
  - 归属：**守卫属主**（`dsh-plugin-guard`）。
- **W7.2 [P0] 检查项负控覆盖（H5：0/4 → 4/4）** —— 每项配「必须为红」的输入
  - 判据：`grep -n "out.checks\." ~/dsh-plugin-guard/lib/index.js` 的**每一项**都有对应负控用例。
  - 归属：**守卫属主**。
- **W7.3 [P0] `all_ok` 语义修正** —— 顶层全绿须以「负控曾红过」为前提，否则 `unverified`
  - 现状：`out.all_ok = Object.values(out.checks).every(c => c.ok)`（`:362`），被恒真项满足。
  - 归属：**守卫属主**。
- **W7.4 [P0] 新增 `C8_comm`（通讯通道检查，断言非列举）** —— 健康面零通讯检查（假绿五）
  - 内容：drift 双板到达 + 投递台账断言；★ **须为断言（键存在且值非空）**，不得退化为命名空间列举。
  - 归属：**守卫属主 + 通道属主**（联审）。
- **W7.5 [P1] 新增 `C9_probe_delivery` / 投递台账统一** —— 成功与失败写**同一**台账（R060）
  - 判据：断中枢跑一轮 ⇒ 台账须新增 `ok:false` 行且被读者回读。
  - 归属：**通道属主**。
- **W7.6 [P1] drift 跨板告警判据取代「本地 PUT 200」** —— 假绿二
  - 判据：`central最新ts` 与 `local最新ts` 之差超阈即红；**401 记终态并告警**（重试仅对 5xx/超时）。
  - 复跑：双板 `data/ops/drift-alert/` 计数（§7.11.9）。**归属**：**通道属主**。
- **W7.7 [P1] 有界重试计数器持久化 + 达上限告警** —— 假绿三 / M3
  - 判据：`2/3` 与 `3/3` **可被观测**；需先定位该计数器实现位置（**当前不可判** ⇒ 本项**前置=定位**）。
  - 复跑：`grep -oh "自动重启 [0-9]/[0-9]" ~/dsh-collab/logs/node-bridge.log* | sort | uniq -c`。**归属**：**壳/桥属主**。
- **W7.8 [P1] launchd 任务 `PATH` 与失败终态告警** —— digest `exit 127` / **2** 项未载（分母须剔 `.plist.bak-*`，见 §12.H.3）
  - 动作：plist 内 `env node` 改**绝对路径**或显式 `EnvironmentVariables.PATH`；失败终态须投递。
  - 复跑：`launchctl list | grep -c com.dsh` vs `ls ~/Library/LaunchAgents/com.dsh.*.plist | wc -l`。**归属**：**运维 + 各 plist 属主**。
- **W7.9 [P1] 跨设备版本偏斜检测（H4）** —— `doHealthCheck()` 只读本机 `homedir()`
  - 动作：对侧取版本并比对，超阈告警。**归属**：**跨设备/通道属主**。
- **W7.10 [P2] 「值守义务人 + 升级路径」登记** —— 根因链第三环「无人知」
  - ★ **这是全链唯一「要加人」的一环**：指定义务人（角色，非会话 id）· 建告警台账 · 定升级路径。
  - 归属：**治理层（用户裁决）**。★ **不属技术修复**。
- **W7.11 [P2] 原始决策卡补登** —— `v1.0.115 · 推送范围调整` 原文在索引（`local-registry-index.json:5761`），**决策卡未定位**
  - 动作：**或**定位归档**或**补登说明「原始卡缺失」；★ **未定位前不得据此推断停推范围**。
  - 归属：**治理层**。

### 归属既有项（**不新增编号**，仅标注）

| 既有项 | 追加归属 | 说明 |
|---|---|---|
| **W0.3** 机制激活计数 | +健康面 | 假绿三的计数器即「机制激活计数」缺持久化的实例 |
| **W1.3** 根因指标 | +健康面 | H1/H2/H3 应作为根因指标纳入 |
| **W1.6** `expires_at` + DLQ | +健康面 | 与「过期丢弃」同面（★ 现象**成立**：载体为 `agent-bus.json` 的 `status=="expired"` **2377** 条；**271,198** 这个**数字不可判**，见 §12.H.3 注） |
| **W3.2** identitySource 入卡 | — | 无健康面追加（避免套满） |
| **W4.4** 换代率告警 | +健康面 | 与假绿三（重试恒定）同族 |
| **W5.1** 判据入工具 | +健康面 | R060/R061 的机械化落点 |
| **Wave S 七件工具** | +健康面 | 七件**均缺独立 verifier** ⇒ 与 W7.2/W7.3 同一缺口 |

> ★ **计数纪律**：本节新增 **W7.1–W7.11（11 项）**；归属既有项 **6 处**（不新增编号）。
> **合并进 v6 时须实点后写入**（v5 的「30 vs 39」教训：**没数的不得当数过的写**）。


## §10 演进类 W 项（追加）

> ★ **编号纪律服从**：v5 §10 已有 **39 项**（W0.1–W0.6 · W1.1–W1.8 · W2.1–W2.10 · W3.1–W3.3 · W4.1–W4.6 · W5.1–W5.6 + S1–S5，`v5:382`/`:387-401` 已逐项核过）。**本节只追加 W8.x 新编号，不重编号、不改既有项**。
> **归属既有项者**只标关系，不新开号（见每项末「归属」栏）。
> 每条附 **复跑命令**（依 §1.5.4 `:108` 纪律）。

| 项 | 内容 | 复跑命令 / 判据 | 归属 |
|---|---|---|---|
| **W8.1** | ★ **先建尺：信封符合度测量工具** `cahac-envelope-conformance.py`（逐字段出现率 + `envelope_ok` 分子分母）。**理由**：本轮实测 `scripts/` 内**无任何信封实现**，故「0%」此前**不可复跑** | `python3 scripts/cahac-envelope-conformance.py --status` ⇒ 输出 `objects/envelope_ok/rate` + 10 字段逐项率。**负控**：构造 1 条合法信封 ⇒ 该条必须计为合规（**能绿**） | 与 W5.1「判据入工具」同族；**本项为其前置** |
| **W8.2** | inbox 写入侧注入 §3 信封（补 CAHAC §7.5 `:360-364` 自陈的**「调用点缺口」**）：给 `mac-mini-inbox-watch`/`central-wake` 加写 `cahac`/`sender`/`recipient`/`dedup_key`/`channel` | `python3 scripts/cahac-envelope-conformance.py --status \| jq '.envelope_ok/.objects'` ⇒ **≥0.90**（新建条目子集）。**须另授权**（改既有写入者） | 新增 |
| **W8.3** | 会话/服务级 **CAHAC §11 能力卡**生成与上报：mac-mini **9** 服务 + mbp **11** 服务 各一卡，含六字段 | 复跑 §12-B 命令 ⇒ `has_cahac_version=True` 计数 **= 服务总数** | 新增 |
| **W8.4** | **能力卡可发现性（pull 端点）** + **解除与广播配额的冲突**：把 §11 `:462`「广播 Agent Card 更新」改为 pull（黑板 `data/capability/<agent-id>` 或本地 well-known 等价） | ① pull 端点存在且新会话零配置拉取成功；② 静态核 §11 条款已不含「广播」字样。★ 现状证据：§4 `:162` ≤月 5 次 vs §11 `:462` 广播 ⇒ **冲突** | 新增（**修既有条款冲突**） |
| **W8.5** | **终态不可变条款** + 状态转移违例检测（对齐 A2A `isFinal()` 语义，**不照抄 A2A 枚举**；沿用 §7.2 `:251` 本机 8 值） | **负控**：造 `done→claimed` 违例 ⇒ **必须红**；正控：合法链 ⇒ 绿 | 新增（补 §12 `:465-480` 缺条款） |
| **W8.6** | **任务查询/枚举接口**（A2A `ListTasks` 等价最小版：枚举 + 游标）。理由：§13 `:482-492` 七错误码无查询类，任务卡当前**无法被程序化盘点** | 边界用例：**0 条 / 1 条 / 超一页** 三态不崩；枚举覆盖率 **100%** | 新增 |
| **W8.7** | **版本协商 + 版本不匹配错误码**：§13 增 `VERSION_UNSUPPORTED`（**须含 `supported[]` 回执**，学 MCP `-32022`） | **负控**：发 `cahac:"1.0"` ⇒ 收到该错误码 + 支持列表；**正控**：合法版本 ⇒ 不报错 | 新增 |
| **W8.8** | **扩展机制边界条款**：定义 `cahac-ext:<uri>` 命名空间 + 写死「**扩展不得改 §3/§4/§7.2 的核心类型与枚举**」 | `grep -c 'cahac-ext'` ≥1 **且** `grep -c '扩展不得'` ≥1；**负控**：造「扩展改核心枚举」用例 ⇒ 必须红 | 新增（补 §16 `:519-524`） |
| **W8.9** | **协议一致性套件**（学 a2a-tck 的 **RFC 2119 分级 must/should/may**，只覆盖本机规范，**不引外部传输**） | 覆盖 §3/§4/§5 **MUST ≥90%**；负控矩阵 **≥5 例全红**；报告机器可读 | 与 W5.3「能力前置清单」同族；**须等 W8.1/W8.2/W8.7 定稿后做** |
| **W8.10** | **断线恢复语义成文**：明确会话层取值（「以新 id 重发 / 不重放」**或**「重放」，二选一）+ 判据。现状：事件层有 offset 续读（§8.3 `:410`）、**会话层空白** | 语义成文 + **1 个可跑用例**；负控：断线重连后**不得出现静默丢件**（须可判别） | 新增（**与 W2 §7.10 离线投递无撤回同族**） |
| **W8.11** | **认证强度：从「白名单」到「逐条验签」**（§10 `:444` 现状＝agent-id 白名单 · §3 `:144` signature 可选） | 启用后**未签/伪签 100% 被拒**；**负控**：改 payload 1 字节 ⇒ 必须红；**正控**：未改 ⇒ 绿 | 新增（**直接闭合 §18.4 `:641`「认证被降级抵消类」**） |
| **W8.12** | **多跳委托衰减评估**（对齐 IETF `draft-prakash-aip-02` 的单条不变式，**仅评估不实施**）：本机存在跨设备/跨会话转派 | 出一页评估：现状能否回答「**谁授权 · 经谁 · 约束是否变宽**」三问。★ **结论允许为「不适用」** | 新增（评估类） |
| **W8.13** | **成本「选择器激励」vs「结算价」的边界声明**（对照 CWEP 类先例）：明确 CAHAC §5.2 权重是**选择器激励**、**不做结算** —— 并裁决是否写入 §1.3 非目标 | 一页对照 + §1.3 是否增句的裁决记录 | 与 W1.6/W5.x 无冲突；新增（条款级） |
| **W8.14** | **「领先项」的证伪条件**（本轮唯一候选：成本权重入选择器，属**阴性证据**） | 产出**可证伪命题 + 检索词清单 + 检索面声明**，交第三方复检；★ **证伪前不得在 v6 写「领先」结论** | 新增（治理类） |

> ★ **计数实点**（对齐 W2/W3 写法，**不在描述里写死**）：
> `grep -cE '^\| \*\*W8\.' ~/dsh-collab/docs/v6-draft-w4-20261010.md` ⇒ 本稿实点 **14 条**（W8.1–W8.14）。

---

# §11 验收标准（八字段 + 六者齐备规则）

**八字段**：`正向判据` · `负控（必须能红）` · `边界用例` · `测量方法与样本量` · `阈值与判定规则` · `证据形态` · `审查员` · `沙箱复跑方式`。
**通过规则**：正向 ∧ 负控红 ∧ 边界不崩 ∧ 阈值达标 ∧ 沙箱复跑一致 ∧ 官方条款无未声明差异 —— **六者缺一不得记 `closed_with_evidence`**。

代表性条目：
| 项 | 正向 | 负控 | 边界 | 样本/测量 | 阈值 | 证据/审查员 | 沙箱复跑 |
|---|---|---|---|---|---|---|---|
| S5 G-CR 门 | 17 条门各有可跑校验 | 造「遮蔽目录」「根级 required」「未重签 dylib」⇒ 必须红 | 干净仓库应全绿 | 3 类 ×2 | 3/3 红、0 误红 | 校验输出 / 独立复核员 | 临时仓库 |
| C5 反遗忘校验 | 一致时 exit 0 | 版本不一致 / evidence 被删 ⇒ 必告警 | 索引不存在 | 4 用例 | 4/4 | selftest / 独立复核员 | 合成 fixture |
| W0.1 挂载 compaction | dump 三行 + 新 `compaction/*` 事件 | 不挂载 ⇒ 事件数继续单调增（对照） | <1MB 不触发 | 前后各 1 次激活 | 触发≥1 且体积降 ≥50% | dump+事件计数 / 裁判 | 复制 profile |
| W0.6 装载事件数门 | 超阈值**报错而非崩** | 阈值内必须放行 | 恰好阈值 | 3 例 | 拒绝率 100% | 拒绝日志 / 裁判 | 合成超大会话 |
| W1.1 幂等键 | 重启后重放 0 重复；>10 分钟重发被抑制 | 不同内容/首次必放行 | 空/超大内容 | 每条 5 例 + 重启 | 抑制 100%、误伤 0 | 边车+注入记录 / 裁判 | 临时边车 |
| W2.5 载体换 | I1–I4 成立；30,755 行一致；幂等重跑 0 新增 | 中途 kill ⇒ integrity ok；3 语言并发 400 行全在 | 空库/超大/超时 | 各 ≥1 | integrity ok、400/400 | 迁移日志 / 裁判（独立窗口） | 影子库+回滚演练 |
| W4.1 端口固定 | 3 次重启地址不变 | 改端口后旧地址应失效 | 端口被占用 | 3 次重启 | 3/3 不变 | 进程表 / 你+裁判 | 副本 profile |

★ **W0.1 必须补 P26 负控**：构造「活跃窗口已低于压缩器开销」的会话 ⇒ **必须判「压缩不可用」并告警**；若判「已压缩」或静默通过，**不得记 `closed_with_evidence`**。

## ★ 11.1 现状（v5 新增：逐项标 DoD/负控有无）
**实测：`dod.full_table` 仍为 `缺席`** —— v4 §11 正文表格只是代表性摘录，全文表从未落盘。★ 按 R030，**v5 不凭空补全**；补全须由各项负责人在沙箱复跑后逐条填入。**本条保持缺口，不因升版而假装补齐。**

| 项 | 已有 DoD | 已有负控 | 可记 closed？ |
|---|---|---|---|
| Wave S 五门 + 两门 | ✅（各附自证矩阵） | 🟡 部分（`N-A` 7 条非通过） | ❌ **缺独立 verifier** |
| C1 / C2 | 🟡 简述 | ❌ | ❌ C1 无 verifier |
| C3 / C5 | 🟡 简述 | ❌ | ❌ verifier 待补 |
| P26 / Q-K | ✅（§5 判据矩阵 + 负控 1 已达标） | ✅ 负控 1；负控 2/3 **纯半达标** | ❌ 待 ① 完成 |
| R049 | ✅ | ❌ | 🟡 **由人执行，未机器化** |

---

# §12 SLO

| 指标 | 现状（v5 重测） | 目标 |
|---|---|---|
| 信标新鲜度 | **落后 ≥1 次状态变化**（索引 10-10 01:44 同步 vs 03:31 交付）· ★ **且 `updated_at` 落在未来使「新鲜」不可读** | 落后 ≤1 次状态变化，启动即校验 |
| **自检覆盖** | **有缺口**（P27 四层） | G-CR18 四条判据全绿 |
| 官方校对留证 | ★ **9/9 全部过期**（最新 97.4h，其余 189–845h） | 100% 涉 dsh 设计项有 **24h 内**留证 |
| 闭环率 | 索引 9 项中 **5 记 closed**，而其中 **3 项 verifier 未定或缺失** | ≥80%，每项有 verifier |
| 审查覆盖 | Wave S 七件**全部作者自测** | 100% 经沙箱+独立审查，一件一裁 |
| 崩溃复发 | 25 类已复现坑 | 同类复发 = 0（G-CR 门全绿） |
| 单会话体积/事件数 | 256MB（峰值 1,178 万事件） | ≤200MB + 事件数入监控 + 超限拒绝 |
| 会话目录 | 1.2GB | ≤500MB |
| inbox | 2,645 文件/108MB | ≤500/≤50MB |
| bus 单文件 | 22.8MB（撕裂 3 次） | 迁移后无整份读写 |
| 黑板数据 | 148MB / snapshot 96MB / DELETE 0 | 有 GC/TTL、大对象外置（-41%） |
| 真积压 / 去重漏判 / 风暴发现 | 103 / >10 分钟必漏 / 人肉 | ≤10 / 0 / 系统自动提前 ≥10 分钟 |
| 机制激活可观测 | 0 | 每次激活可计数可查 |
| 端口稳定性 | 6 个历史端口 | 固定 |

---


### §12 通讯面 SLO

> ★ 本节为 v6 §12 的**新增第三面**（v5 §12 只覆盖治理本身）。
> ★ **纪律**：本节所有会随编辑变化的数字**不写死**，一律附**复跑命令 + 取值时刻**（对照 v5 §17.3）。
> 取值时刻：**2026-10-10T23:5x+0800**（`date "+%Y-%m-%dT%H:%M:%S%z"` 实读）。

| 指标 | 定义（口径） | 现状（本轮实测） | 取值时刻 | 目标 | 复跑命令 |
|---|---|---|---|---|---|
| **双板到达且一致率** | `logs/bb-card-send.log` 中 `action=send` 完成行的 `boardsMatch===true` 占比 | **772/807 = 95.7%**（`result` 分布：OK 771 · FAIL 35 · OK-WITH-TIMEOUT 1） | 2026-10-10T23:51Z | **≥99.5%**，且 FAIL 逐条归因 | 见下 ①  |
| **双板漂移数** | `drift_scan` 的 `driftCount` / `total` | **1 / 12**（`funnel-public` HTTP 502） | 2026-10-10T15:54Z（工具自报 `scannedAt`） | **0**，且漂移**可跨机告警** | `drift_scan`（工具自跑） |
| **信道可达性（矩阵）** | `channel-matrix.json` 期望 vs 实测 | 11/11 矩阵静态项在位；`sse-8803` 探测通过（`SSE hello 已收到`） | 同上 | 保持 | `cat ~/dsh-plugin-drift-scan/lib/channel-matrix.json` |
| **未登记通道数（消费方口径）** | 做「卡→唤起会话」跃迁的 actor 在两张登记表中的条目数 | **0 条登记 / 1 个 actor**（`dsh-plugin-central-inbox`），owner 缺失 | 2026-10-10T23:5x | **0 个无属主跃迁方**（≠0 个未命名通道） | 见下 ② |
| **两张登记表一致性** | drift-scan 矩阵项 ∩/∪ channel_gate 枚举 | 共有 **5** · 并集 **13**（仅 gate 2 · 仅矩阵 6） | 同上 | 单一来源，差集 = 0 | 见下 ② |
| **投递真达率** | ★ 见口径警示 | **不可判（见下）** | — | 口径定义后方可设 | 见下 ③ |
| **§3 信封符合度** | ★ **宿主节为 §12 业界面**（本面不重复设行；口径与复跑命令见彼处） | — | — | — | — |
| **§7.2 自报合规率 `rate_legal`** | `state` 值 ∈ `LEGAL_STATES` 的比例（**≠ 上行**） | **0.046136**（280/6069）@ver172 | 2026-10-10T23:47:10 | 单调上升 | 见下 ⑤ |
| **离线队列滞留上界** | `expired` 消息 `expiredAt − time` 的最大值 vs 常量 `QUEUE_TTL_MS` | **46.2 天 vs 常量 7 天**（2377 expired，74.5% 由单次清扫产出） | 同上 | **滞留 ≤ 7 天**（TTL 确定性执行） | 见下 ⑥ |
| **队列终态分布** | `store.threads[].messages[]` 的 `status` | `delivered 92.9% / expired 7.1% / queued 0.0%`（N=33613） | 同上 | `expired` 单调下降 | 见下 ⑥ |
| **§7.4 邮箱容量执行** | 实际脚本体量 vs 规范上限（100/agent） | **2957 文件 / 6088 条目**，超限无执行方（`~/.dsh/mailbox/` 不存在） | 同上 | 有执行方且收敛 | 见下 ⑦ |
| **通道变更治理门覆盖** | `channel_gate` 枚举通道数 vs 实际在役通道数 | 枚举 **7**，矩阵在役 **11**（**两个集合不互相覆盖**） | 同上 | 在役通道 100% 在枚举内 | 见下 ② |

---

#### ★★ 口径警示：本节**不得**出现未定义分母的「真达率」

「投递真达率」在现状数据中**至少有三个互不相通的口径**，v6 **必须择一并写明分母**，否则该指标不可复核：

| 口径 | 值 | 分母 | 可复现性 |
|---|---|---|---|
| 全量终态分布 | `delivered 92.9%` | 33613 条消息终态 | **可复现**（见 ⑥） |
| 队列真达率（源码自述） | `15%` | 「忙窗口排队」子群（**窗口未载明**） | **不可判**——源码注释 `agent-bus/lib/index.js:262` 自述，且明标为 **2026-10-04 `1.5.13` 修复前**的口径 |
| 曾入队者最终送达率 | **不可计算** | 无 `queuedFrom` 类标记 ⇒ 终态无法区分「直投成功」与「入队后成功」 | **不可判**（数据结构不支持） |

⇒ **v6 写法建议**：本节**先落**「全量终态分布」为**唯一可复核口径**，并将 `15%` 标注为**历史自述值（修复前、窗口未载明）**，**不得**作为现状基线引用（对照 v5 §13 R12「引用丢限定语」——此处已三例，勿增第四例）。

---

#### 复跑命令集（本节全部数字的唯一来源）

① 双板到达率
```bash
python3 - <<'EOF'
import json,collections,os
rows=[json.loads(l) for l in open(os.path.expanduser('~/dsh-collab/logs/bb-card-send.log'),encoding='utf-8',errors='replace') if l.strip()]
s=[r for r in rows if r.get('action')=='send' and 'result' in r]
print("分母:",len(s)); print(collections.Counter(r.get('result') for r in s).most_common())
m=sum(1 for r in s if r.get('boardsMatch') is True)
print(f"双板到达且一致率 = {m}/{len(s)} = {m/len(s)*100:.1f}%")
EOF
```

② 登记表覆盖与差集（未登记通道数 / 两表一致性）
```bash
python3 - <<'EOF'
import json,os,re
m=json.load(open(os.path.expanduser('~/dsh-plugin-drift-scan/lib/channel-matrix.json')))['matrix']
mn=set(k for k in m if not k.startswith('_'))
g=open(os.path.expanduser('~/dsh-plugin-channel-gate/lib/gate.js')).read()
gn=set(re.findall(r"'([a-z0-9-]+)':\s*\{", g[g.find('CHANNELS'):g.find('REQUIRED_FIELDS')]))
print("矩阵",len(mn),"gate",len(gn),"共有",len(mn&gn),"并集",len(mn|gn))
print("仅gate",sorted(gn-mn)); print("仅矩阵",sorted(mn-gn))
EOF
grep -c "central-inbox" ~/dsh-collab/docs/comm-channel-rules-v2-20261002.md
grep -c "central-inbox" ~/dsh-collab/docs/agent-comm-portal-20261002.md
```

③ 投递真达率——**见上方口径警示**（三口径，其中两个不可判）

④ §3 信封符合度（双面全量）
```bash
curl -s "http://127.0.0.1:8792/notes/collab/" -o /tmp/collab-list.json
python3 - <<'EOF'
import json,os
CAHAC=['cahac','channel','sender','recipient','dedup_key','signature']
l=json.load(open('/tmp/collab-list.json'))['list']; c={k:0 for k in CAHAC}
for v in l.values():
    val=v.get('value') if isinstance(v,dict) else None
    if isinstance(val,dict):
        for f in CAHAC:
            if f in val: c[f]+=1
print("卡面 分母",len(l),{k:f"{c[k]}/{len(l)}" for k in CAHAC})
d=json.load(open(os.path.expanduser('~/.dsh/agent-bus.json')))
ms=[m for t in d.get('threads',[]) or [] if isinstance(t,dict) for m in t.get('messages',[]) or []]
c2={k:sum(1 for m in ms if k in m) for k in CAHAC}
print("消息面 分母",len(ms),{k:f"{c2[k]}/{len(ms)}" for k in CAHAC})
EOF
```

⑤ `rate_legal`（★ 与 ④ 不同口径，勿混）
```bash
curl -s "http://127.0.0.1:8792/data/health/cahac-compliance" \
 | python3 -c "import json,sys;d=json.load(sys.stdin);v=d['value'];print('ts',d['ts'],'ver',d['version'],'rate_legal',v['rate_legal'],f\"({v['legal_state']}/{v['total']})\")"
```

⑥ 队列 TTL 执行与终态分布
```bash
python3 - <<'EOF'
import json,collections,os
from datetime import datetime,timezone,timedelta
CST=timezone(timedelta(hours=8)); f=lambda ms: datetime.fromtimestamp(int(ms)/1000,CST).strftime('%Y-%m-%d %H:%M:%S')
d=json.load(open(os.path.expanduser('~/.dsh/agent-bus.json')))
ms=[m for t in d.get('threads',[]) or [] if isinstance(t,dict) for m in t.get('messages',[]) or []]
print("分母",len(ms),collections.Counter(m.get('status') for m in ms).most_common())
ex=[m for m in ms if m.get('status')=='expired']
print("过期批次数",len(set(str(m.get('expiredAt')) for m in ex)),"最大批",collections.Counter(str(m['expiredAt']) for m in ex).most_common(1))
print("滞留上界(天)",round((max(int(m['expiredAt']) for m in ex)-min(int(m['time']) for m in ex))/864e5,1))
EOF
```

⑦ §7.4 容量执行
```bash
ls -la ~/.dsh/mailbox/ ; echo "[exit=$?]"
ls ~/.dsh/inbox | wc -l
python3 -c "
import os,glob
fs=[f for f in glob.glob(os.path.expanduser('~/.dsh/inbox/*')) if os.path.isfile(f)]
print('文件数',len(fs),'条目',sum(sum(1 for _ in open(f,encoding='utf-8',errors='replace')) for f in fs))"
```

---

#### M4 通讯基线建议（供 v6 §14 引用）

| 判据 | 现状 | 是否可作 M4 出口 |
|---|---|---|
| drift 双板通 | **1/12 漂移**（`funnel-public` 502） | **未达**（需 0） |
| 无未登记通道 | 消费方 `dsh-plugin-central-inbox` **0 条登记** | **未达** |
| 投递可见 | 队列终态可枚举 ✅，但 **TTL 执行不可确定性复核**（滞留 46.2 天） | **未达** |
| 信封符合度 | **0%** | **未达**（需 >0 且分通道阶梯） |

⇒ **M4 判定：❌ 不成立**（与 v5 §14 中 M0/M2/M3 的 ❌ 同族）。

---


### §12 健康面 SLO

> **属主**：W3｜**样本窗**：截至 2026-10-10 夜｜**坐标系**：本机 `mac-mini`，除注明外均为本机实测
> ★ **凡随编辑变化的数字，以 §7.11.9 复跑命令为准**，下表数值仅为**本次快照**。

#### 12.H.1 三组 SLO（健康面）

| # | 指标 | 定义式 | **当前实测** | 目标 | 判据（可机械执行） |
|---|---|---|---|---|---|
| **H1** | **假绿数** | 计数：`ok=true` 而其判据分母可为 0 或可被完全跳过的检查项 | **3**（C7 恒真 · `/health` 空壳 · `all_ok` 由退化项满足） | **0** | ★ 每项**必须有负控**：构造空分母输入时判据指向 `不可判` 或 `红`，**不得指向绿** |
| **H2** | **静默失败数** | 计数：满足「有失败 + 有落盘 + 无主动投递/告警读者」三条件的失败类 | **≥5 类**（drift 跨板 · digest · launchd 终态 · bb-write exit≠0 · 中枢台账） | **0** | 任一失败落盘后 **1h 内**须有到达读者的投递证据；无证据 ⇒ 记 SILENT |
| **H3** | **探针投递率** | `到达读者的告警数 / 触发告警数` | **drift：19/304 = 6.2%**（跨板）<br>**digest：0/1 = 0%**（每跑每败） | **100%**（1h 内到达） | 每个探测器的**成功与失败分支写同一投递台账**，且台账有读者（回读断言） |
| **H4** | **跨设备偏斜检出** | 同一包在本机与对侧的版本对 | ★ **本机结构上不可检出** —— `doHealthCheck()` 只读 `homedir()` | 可检出且超阈告警 | 存在**真跨设备**比对项（断言，非列举） |
| **H5** | **探针负控覆盖率** | `有负控的检查项 / 全部检查项` | **0/4**（C1–C7 无一附负控） | **100%** | 每检查项配一组「必须为红」的输入；否则该检查项**不得计入全绿** |

#### 12.H.2 逐项判据与负控（供 §11 对齐）

| 项 | 判据 | 负控（必须红） |
|---|---|---|
| H1 C7 | `doDepsScan` 返回 `total`，且 `ok` 三态：`total===0 ⇒ null` | 喂「全部 `.bak`」的假 profile ⇒ 必须 `null`，**不得** `true` |
| H1 `/health` | 断言**指定键**存在且值非空 | 喂空内容 ⇒ 必须红 |
| H2 drift | `central最新ts` 与 `local最新ts` 之差 < 阈值 | 制造 1 张只在本地写的卡 ⇒ 必须红 |
| H2 digest | 逐次执行须留 `exit` 码；`exit≠0` 须投递 | 用不含 `node` 的 PATH 跑 ⇒ 必须红（**当前实为该情形**） |
| H3 | 投递台账内 `ok:false` 行须被计数并可见 | 断中枢后跑一轮 ⇒ 台账须增 `ok:false` |
| H4 | 对侧取版本并比对 | 伪造对侧版本 ⇒ 必须红 |

#### 12.H.3 本次快照的「静默失败」实测明细（**H2 的分母**）

| 失败类 | 实测证据（复跑命令） | 当前值 |
|---|---|---|
| drift 跨板 | 双板 `data/ops/drift-alert/` 计数 | 本机 **304** / 中枢 **19**；中枢冻结于板级 `ts` = `2026-10-03T13:27:35` |
| digest | `cat ~/Library/LaunchAgents/com.external-link.digest.plist` ⇒ `ProgramArguments=[/usr/bin/env, node, …]`；`tail /tmp/external-link-digest.log` | `env: node: No such file or directory` ×3；★ 机制证成：`echo $PATH` = `/usr/bin:/bin:/usr/sbin:/sbin` **不含** `/opt/homebrew/bin`，而 `node` 实在 `/opt/homebrew/bin/node` |
| launchd 终态 | `launchctl list \| grep -c com.dsh` vs `ls ~/Library/LaunchAgents/com.dsh.*.plist \| wc -l` | **78 已载 / 80 plist** ⇒ **2 未载**（★ 原 91 系分母混入 **11 个 `.plist.bak-*`** —— 与本稿批判的 C7 假绿①【.bak 坍缩分母】**同型**；复跑须剔 bak；如实分报；其中 `com.dsh.auto-reminder`、`com.dsh.waimai.bad-review-scheduler` 属 `com.dsh.*.plist` 命名） |
| bb-write | `grep -o "exit=1" ~/.dsh/bb-write.log \| wc -l` | **776**；退出码分布另含 `exit=2` **46** · `exit=6` **16** · `exit=5` **8** · `exit=3` **4** |
| 中枢台账 | 中枢 `data/` 键数 | **6140** vs 本机 **33625** |

> ★ **口径更正（重要）**：简报称 `central-inbox.log` 达 **1.04 GB / 5,646,660 行**、**过期消息静默丢弃 271,198 条**。
> 本机实读：文件在 **`~/.dsh/central-inbox.log`**（**不在** `~/dsh-collab/logs/`），
> 大小 **1,047,455,202 B**、**5,668,331 行**（与「1.04 GB / 5.6M 行」**量级相符**）；
> **但 `grep -o "expired"` = 0 · `grep -o "过期"` = 0**（**全量扫描 1,047,455,999 B**，非 `tail`）。
> ⇒ ★ **载体找错更正（撤回原「不成立」判定）**：`central-inbox.log` 确无 `expired`/`过期`（全量扫，**0** 命中），
> **但真实载体是 `~/.dsh/agent-bus.json`** —— 实测 `status=="expired"` **恰 2377 条**（均带 `expiredAt`；★ **口径更正（外部复核 N4）**：`expiredAt` 区间 = **2026-10-02T04:34:05 → 2026-10-10T18:17:32**，`time` 区间 = **2026-08-17T00:42:19 → 2026-10-03T18:16:42** —— 原写「2026-08-17→10-03」是 **`time`** 的区间，**不得挂到 `expiredAt` 上**，与 §7.10 保持一致）；
> **本稿 W7.5/§12.H.2 与 W1 M4③ 讲的正是这条路径** ⇒ **「过期消息静默丢弃」这一现象成立**，仅 **271,198** 这个**数字**不可判；
> 该数或源于**另一身份/坐标系**（如 MBP 或某轮会话统计）。**v6 不得引用该数**。
> ★ 且 `~/dsh-collab/logs/bb-write.log` **不存在**，实体在 **`~/.dsh/bb-write.log`** —— 两处路径须以复跑命令为准。

#### 12.H.4 与既有 SLO 的关系

v5 的 SLO **只覆盖治理本身**（四件套一致性 / 索引 sha / 锚点自足）。
**健康面 SLO 是新增的一整面**，**不修改** v5 任何既有阈值 —— 仅**追加** H1–H5。
⇒ 与 §10 的纪律一致：**只追加，不重编号**。



### §12 业界面 SLO

> 承接 v5 §12 表式（`:452-470`）。**每行给可判数值目标 + 复跑命令**；凡现状随编辑变化者，**不写死数字**。
> **坐标系**：`inbox_root = ~/.dsh/inbox` · 取值时刻 **2026-10-10 23:47–23:56 +0800** · 条目口径 = **非空行**（含 3 个历史 JSONL 聚合文件）。

**① 信封符合度（核心指标）**

| 指标 | 现状（W4 实测） | 目标 | 复跑命令 |
|---|---|---|---|
| **信封符合度**（§3 十必需字段中 ≥6 命中） | **0 / 2949 = 0.0000** | **新建条目 ≥90%**（历史存量不追） | 见下方 A |
| `cahac` 版本字段出现率 | **0 / 2949 = 0.00%** | ≥90% | 见下方 A |
| `sender` / `recipient` 出现率 | **0.00% / 0.00%** | 各 ≥90% | 见下方 A |
| `dedup_key` 出现率 | **0.00%** | ≥90% | 见下方 A |
| `channel` 出现率 | **1 / 2949 = 0.03%** | ≥90% | 见下方 A |
| `type` / `ts` 出现率（仅存的较高项） | **50.39% / 64.26%** | ≥90% | 见下方 A |

> ★ **口径与时刻声明（W4-2）**：分母统一为 `~/.dsh/inbox` 的**可解析 JSON 对象数**（附复跑命令与取值时刻；★ 本稿实测 **2955**，会随增长变化 ⇒ **不写死**）；★ 并声明：**本行是 §12「信封符合度」的唯一宿主节**（通讯面不重复设行）。

```bash
# A. 信封符合度（W8.1 建成前，用此临时尺；建成后以 W8.1 脚本为准）
cd ~ && python3 -c "
import glob,json,os
files=sorted(glob.glob(os.path.expanduser('~/.dsh/inbox/*')))
REQ=['cahac','id','type','channel','sender','recipient','priority','dedup_key','ts','payload']
n=ok=0; has={k:0 for k in REQ}
for f in files:
    try: o=json.load(open(f,encoding='utf-8'))
    except Exception: continue
    if not isinstance(o,dict): continue
    n+=1; h=sum(1 for k in REQ if k in o)
    if h>=6: ok+=1
    for k in REQ:
        if k in o: has[k]+=1
print('objects=%d envelope_ok=%d rate=%.4f'%(n,ok,ok/max(n,1)))
print({k:'%.2f%%'%(100.0*has[k]/max(n,1)) for k in REQ})
"
# 取值时刻实测: objects=2949 envelope_ok=0 rate=0.0000
#   {'cahac':'0.00%','id':'0.88%','type':'50.39%','channel':'0.03%','sender':'0.00%',
#    'recipient':'0.00%','priority':'1.12%','dedup_key':'0.00%','ts':'64.26%','payload':'0.44%'}
```

**② 能力卡覆盖与可发现性**

| 指标 | 现状（W4 实测） | 目标 | 复跑命令 |
|---|---|---|---|
| **会话/服务级能力卡（CAHAC §11）覆盖** | **0 / 9**（mac-mini 服务）· **0 / 11**（mbp 服务）· **0 会话** | **9/9 · 11/11 · 100% 上报会话** | 见下方 B |
| 卡内 §11 六字段齐备率（`cahac_version`/`channels`/`topics`/`budget`/`comm_style`/`capabilities`） | **0%**（两卡 `has cahac_version: False`） | **100%** | 见下方 B |
| **可发现性**：pull 式端点（well-known 等价） | **无**（仅有黑板 `data/discovery/agents/<node>`，push 广播式） | **存在 pull 端点**，新会话零配置拉取成功率 100% | 见下方 B |
| 卡更新是否挤占广播配额（§4 `:162` ≤月 5 次） | **冲突**（§11 `:462` 规定用广播） | **不计入广播配额**（月 5 次配额专供 emergency/policy/restart） | 静态核（条款） |

```bash
# B. 能力卡覆盖（结构实测）
curl -s --max-time 15 "http://127.0.0.1:8792/data/discovery/agents/" | python3 -c "
import sys,json; d=json.load(sys.stdin); L=d['list']
print('nodes=%d'%len(L))
for k,v in L.items():
    vv=v['value']; print(' %s services=%d sessions=%d has_cahac_version=%s'%(
        k, len(vv.get('services',{})), len(vv.get('sessions',[])), 'cahac_version' in vv))
"
# 取值时刻实测:
#  nodes=2
#   data/discovery/agents/mac-mini services=9 sessions=3 has_cahac_version=False
#   data/discovery/agents/mbp      services=11 sessions=1 has_cahac_version=False
```

**③ 任务状态与生命周期**

| 指标 | 现状（W4 实测） | 目标 | 复跑命令 |
|---|---|---|---|
| **合规率 `rate_legal`**（§7.5 `:356` 定义） | **0.046136**（黑板键上报，`total=6069`·`legal_state=280`） | **≥60%**（沿用 I8 阈值）· **且当前写入路径 ≥60%** | 见下方 C |
| ★ **当前逐条写入路径合规率** | **0.0000**（2948 个逐条文件：`with_state=2`·`legal=0`） | **≥60%** —— 该口径是**真实进度指标** | 见下方 C |
| 历史聚合文件合规率（**唯一有分子的地方**） | **0.0910**（285 / 3131，全部合规条目出自此处） | 冻结为历史基线（**不追**） | 见下方 C |
| **终态不可变**（终态再转移违例数） | **不可判**（§12 `:465-480` 无终态条款） | 条款成立后 **= 0** | 待 W8.5 |
| **任务查询/枚举面**（ListTasks 等价） | **不存在**（§13 七错误码无查询类） | 可枚举 **100%** 任务卡，分页边界不崩 | 待 W8.6 |

```bash
# C. 合规率：必须【分文件族】报，否则 4.61% 会把「历史」读成「进度」
cd ~ && python3 -c "
import glob,json,os
files=sorted(glob.glob(os.path.expanduser('~/.dsh/inbox/*.json')))
# ★ 口径统一（W4-3）：对齐报告工具 cahac-compliance-report.py:102 的 LEGAL_STATES ⇒ 取 7 值；
#   CAHAC §7.2（:251）为 8 值（另含 'superseded'），本脚本原按 8 值计 ⇒ 已剔除该值，以与报告工具同名同指标。
#   注：下列「取值时刻实测」中的 legal 计数系 8 值枚举下的读数；7 值口径一律以复跑为准。
ENUM={'todo','claimed','done','verified','blocked','failed','timeout'}
AGG={'collab-inbox.json','mac-mini-inbox.json','verify-watch.json'}
def scan(paths,label):
    tot=ws=lg=0
    for f in paths:
        for ln in open(f,encoding='utf-8'):
            s=ln.strip()
            if not s: continue
            tot+=1
            try: o=json.loads(s)
            except Exception: continue
            if isinstance(o,dict) and 'state' in o:
                ws+=1
                v=o['state']
                if isinstance(v,str) and v in ENUM: lg+=1
    print('%-26s entries=%5d with_state=%4d legal=%4d rate=%.4f'%(label,tot,ws,lg,lg/max(tot,1)))
scan(files,'ALL')
scan([f for f in files if os.path.basename(f) in AGG],'3 legacy JSONL aggregates')
scan([f for f in files if os.path.basename(f) not in AGG],'per-entry .json files (CURRENT)')
"
# 取值时刻实测:
#  ALL                        entries= 6079 with_state= 287 legal= 285 rate=0.0469
#  3 legacy JSONL aggregates  entries= 3131 with_state= 285 legal= 285 rate=0.0910
#  per-entry .json files      entries= 2948 with_state=   2 legal=   0 rate=0.0000
```

**④ 协议版本 / 扩展 / 一致性（条款面）**

| 指标 | 现状 | 目标 | 判定方式 |
|---|---|---|---|
| 版本不匹配**可判别率** | **0%**（§13 `:482-492` 七码中无版本类错误码） | 错版 **100%** 返回明示错误码 **含 `supported[]`** | W8.7 建成后用例 |
| 扩展**边界条款**存在性 | **不存在**（§16 `:519-524` 仅「ADDITIVE」一句） | 条款 + **「扩展不得改核心枚举」** 可 grep 到 | `grep -c 'cahac-ext'` ≥1 且 `grep -c '扩展不得'` ≥1 |
| 一致性套件 MUST 覆盖 | **0%**（仅条款级体检三支） | **§3/§4/§5 MUST 条款 ≥90%** + 负控矩阵 ≥5 例全红 | W8.9 建成后复跑 |
| 断线恢复语义成文 | **不可判**（事件层有 offset 续读 §8.3 `:410`；**会话层无**） | 二选一明示 + 1 个可跑用例 | W8.10 建成后复跑 |
| 逐条验签启用后的**未签/伪签拒绝率** | **不具备条件**（§3 `:144` signature 可选） | **100% 拒绝** | W8.11 建成后负控：改 1 字节 ⇒ 必红 |

---

# §13 风险登记

R1 治理工具制造同类问题 · R2 阈值无样本 · R3 不可逆操作 · R4 仪器失真 · R5 小机资源 · R6 双轨并存 · R7 时钟漂移 · R8 开关装了没合上 · R9 失忆 · R10 自设计崩溃 · R11 半修记为已修 · **R12 引用丢限定语（系统性，已三例）** · **R13 载体换 SQLite 唯一高危** · **R14 审查信息包不足 ⇒ 审查失效**。

★ **v5 新增**：
- **R15 判据失明** —— 自检全绿而事实已变；危害面是**信任**而非数据。
- **R16 计划自身滞后** —— 权威索引落后于交付物，**且无机制发现**；与 R11 同族但更隐蔽：R11 是**说了没做**，R16 是**做了没说**（进度被系统性低估，同样导致决策失真）。
- **R17 升版半成品** —— 四件同步做一半即停，会让下一次校验读到「改了一半」的状态，**比不做更坏**。

---


### R060 / R061

> **编号承接**：R001–**R059** 已见于 `~/dsh-collab/rules-registry/RULES.md`（**实点 59 条**）；**R060/R061** 为 **v6 主线内新增**，
> 编号沿用本主线既有序列（**落地进 `RULES.md` 时须由属主做全局唯一性复核**，避免与既有号冲突）。
> ★ **本稿新编号已统一为 R060/R061**。

#### R060 · 静默失败禁止

> ★ **本稿提供 R060 的规则条目体裁，W2 提供其实例与病理内容（归 §7.10）**。

**规则**：**任何失败，若其结局无法到达读者，即等同于未发生 —— 故禁止。**

**判据（三条件同时满足即判 SILENT，须立即整改）**：
1. **有失败**（非 0 退出 / 异常 / 超时 / 401 / 127 等终态）；
2. **有落盘**（写入了日志、JSONL、台账或卡片）；
3. ★ **无主动投递 / 无告警读者**（**没有**指向人的推送、**没有**可回读的台账断言）。

**证明义务**：任一处声称「已修复」，须提供**该项失败被投递到读者**的证据
（投递记录 + 回读断言），**不得**以「日志里有」充当「有人知道」。

**本条最近实例（本机实测）**：
- drift 跨板失败落盘于 `stderr`（401×134），而**成功侧独占 stdout**（200×135）⇒ 读 stdout 者以为全绿；
- digest 落盘于 `/tmp/external-link-digest.log`（`env: node: No such file or directory`），**无读者**；
- `bb-write.log` 记 `exit=1` **776** 次，**无告警**。

**理由**：与 v5 **P4 静默失败**同族但**可机械判定** —— R060 给出**三条件谓词**，
把「静默」从**感受**变成**可计数**（并计入 §12.H.1 的 **H2**）。

---

#### R061 · 假绿禁止

**规则**：**判据的分母不得为 0、不得被过滤为空、不得只看成功分支；
`ok` 的取值不得依赖于一个可能为空的量。**

**判据**：
1. 凡返回 `ok/通过/全绿` 的判据，**必须同时输出其分母**（比对了多少个对象）；
2. **分母为 0 ⇒ 必须判 `不可判`，不得判绿**（★ 核心条款）；
3. 成功与失败**必须进入同一统计口径**（不得只打印成功侧）；
4. 存在「跳过」谓词时，**须同时报告跳过数**，并**验证剩余集非空**；
5. 顶层「全绿」**须以负控曾红过**为前提，否则标 `unverified`。

**本条最近实例（本机实测，五处）**：
1. **C7 遮蔽扫描**：106 项 **−** 101（`.bak`/`.pnpmcopy`）**−** 5（软链）**= 0** ⇒ `count===0` **恒真**；
2. **drift 告警**：成功/失败分属 stdout/stderr ⇒ 读一侧即全绿；
3. **有界重试**：`1/3`×12 而 `2/3`/`3/3` **各 0** ⇒ 计数器每代重置，上限分支不可达；
4. **`/health`**：任意首段皆 `200 + {"total":0}` ⇒ 200 只证端口在听；
5. **`cld_health_check`**：检查项仅 4 个，`all_ok` 由恒真项满足，且零条通讯通道检查。

**理由**：**假绿比真红更危险** —— 真红触发修复，假绿**消耗掉本该用于修复的注意力**。
R061 的价值在于：它把「**没比过**」与「**比过且一致**」强制分开（二者当前输出完全相同）。

---

#### R060 / R061 的相互关系与 M 码映射

| 规则 | 对应 M 码 | 与 P 码关系 |
|---|---|---|
| **R060** | M6（改完不验证/不留痕）· M3（重启竞态） | 强化 **P4 静默失败**：给出三条件可机械判定式 |
| **R061** | M1（遮蔽）· M7（层错）· M9（静态全绿≠能跑） | 强化 **P3 判据假绿**：给出「分母必现 + 负控必红」可机械判定式 |

⇒ **R060 管「失败没人知道」；R061 管「成功是假的」。二者叠加即本节根因链「探测在、投递断、无人知」的规则化封堵。**



#### R062 未登记通道（无通道治理层 owner）

**一句话**：**能做「有副作用跃迁」的 actor，不在任何登记表内、无 owner** ⇒ 该跃迁**无【通道治理层】owner**（★ 反证：`RULES.md` 有 **R004**「central-inbox 注入目标显式配置」明文义务；黑板 `data/registry/` 含 **3 条专项登记**（★ 实测键名可复跑：`central-inbox-audit-and-fix-sandbox-20261001` · `central-inbox-collab-filter-ruling` · `central-inbox-v0.2.0-landed-preflight-go-20261001`；★ 注：本项曾由 W2 编辑线报「未复现」，经发起方复核**实测成立**（`data/registry/` 共 1267 键，键名含 `central-inbox` 者 **3**），**维持原引证**）；`data/discovery/agents/mac-mini` 亦登记为 central-inbox v0.2.15 ⇒ **不得表述为「无责任方」**）。

**判定**：成立（且**须修正表述**——见下）——★ **危害面与建议门已迁入 §7.10 P28「★ P28 病理内容补记」，本节不重复**。

**★ 精确表述（v6 请照此写，勿照抄「存在一条未登记通道」）**：
> **通道名 `sse-8803` 是在册的**（`channel-matrix.json` 有 `sse-8803` 项；`channel-gate/lib/gate.js:22-30` 冻结枚举含它，`owner:'rust-blackboard'`）。
> **不在册的是「跃迁方」**：执行 `卡 → 自动唤起会话` 这一副作用跃迁的 actor **`dsh-plugin-central-inbox`**，在 `drift-scan` 矩阵、`channel_gate` 冻结枚举中**均无条目**（0 条），在两份权威通讯文档中**0 命中**。
> ⇒ 缺陷不是「有个通道没名字」，而是「**通道在册、跃迁方无属主**」——正是 CAHAC §18「未指定责任方的条款不得标 `enforced`」的运行时同构。

**证据（三步全给）**：
```
① 调用链具名（逐环）
  central-inbox/lib/index.js:44  → SSE_URL = 'http://127.0.0.1:8803/events'
  central-inbox/lib/index.js:481 → agentBus.send(from, target, text, undefined, {…})
  agent-bus/lib/index.js:1399    → const ok = deliver(msg, 'normal');
  agent-bus/lib/index.js:573     → target.followup(message);      ← 副作用发生点（唤醒目标会话）

② 登记面（两表均无该 actor）
  drift-scan 矩阵项 11 / channel_gate 枚举 7 / 共有 5 / 并集 13
  「central-inbox」在两表中的条目数 = 0

③ 权威文档面（逐面打印分母）
  docs/comm-channel-rules-v2-20261002.md : 命中 0 条 / 共 69 行
  docs/agent-comm-portal-20261002.md      : 命中 0 条 / 共 100 行
```

**★ 附带风险（同一条 R062 内，请一并登记）**：**两张登记表本身不一致**——共有仅 **5** 项，并集 **13** 项（仅 gate 有 `launchd-daemons`/`local-agent-bus`；仅矩阵有 `device-daemon`/`e2-registry-services`/`funnel-public`/`hb-fwd`/`node-bridge`/`sync-from-central`）。
⇒ 存在一类通道：**能过变更门（在 gate 枚举内）但无漂移探测（不在矩阵内）**，以及反向的一类 ⇒ **治理与探测的覆盖集合不重合** ⇒ 「R6 双轨并存」的第二实例。

**关联既有项**：R6（双轨并存，**第二实例**）· R060（同根：无 owner ⇒ 无告警）· **CAHAC §18 偏离归属**（同构条款）· v5 **W4.6 订阅唤醒 PoC**（相邻但不同：W4.6 是**建**能力，R062 是**登记/定责**）。

---

# §14 执行序与里程碑

> **v6 改写节**：M0–M3 承继 v5 并按其**自身实测判定**重述；**新增 M4 通讯基线**。
> **判定日期**：2026-10-10T23:56:25+0800 · 全程只读。
> ★ **本节的「依据」列全部给可复跑命令或文件:行号；凡会随编辑变化的数字，以复跑命令代替写死。**

---

## 14.1 阶段轴声明（★ 只用 Wave + M0–M4）

**v6 的阶段轴 = `Wave`（S / C / 0–5）+ 里程碑 `M0–M4`。这是唯一阶段轴。**

**旧阶段图（阶段 0–4）在本版标为「历史」，不引用、不承继、不进任何表**：

    $ stat -f 'birth=%SB mtime=%Sm size=%z' -t '%F %T' research/cost-governance/architecture-evolution-stages-v1.0.md
    birth=2026-08-22 03:36:31 mtime=2026-08-22 03:36:31 size=2818
    $ grep -c '阶段' docs/distributed-agent-network-governance-plan-v5-20261010.md        → 0
    $ grep -c 'architecture-evolution-stages' docs/distributed-agent-network-governance-plan-v5-20261010.md → 0

⇒ 该件 `mtime == birth == 2026-08-22 03:36:31`，**从未更新**；v5 全文 588 行**「阶段」0 命中**、**从不引用该件**。**两条轴独立** ⇒ 混用会把 2026-08-22 的旧刻度当当前进度。**v6 只写 Wave 轴。**

---

## 14.2 执行序（v5 §14 原样承继 + 实测补注）

**v5 `:486-490` 逐字原文**：

    Wave S（门）✅工具面已交付 ──> Wave C（信标）in_flight ──> Wave 0 ──> Wave 1（P0）
    并行：NATS 影子 PoC（只读，必须显式设限额）
    Wave 2（含唯一高危载体换）→ Wave 3 → Wave 4 → Wave 5

**v6 补注（实测，v5 未载）**：

| 项 | 读数 | 依据 |
|---|---|---|
| Wave S | **`in_flight`** —— 七件门工具已在 `tools/` 交付（10-10 03:31），走完全部 R006 §5 三步；★ **但七件均为作者自测，缺独立 verifier** ⇒ **不得记 `closed`** | `docs/resume-prompt-starbridge-v3.md:14-15` |
| Wave 0–5 | **全 `open`**，WBS **39 项完成 0 项** | `docs/execution-audit-anchor-v5-20261010.md:51,260` |
| 下一步 | **`C4` 自启动注入**（= M0 唯一缺口） | `docs/execution-audit-anchor-v5-20261010.md:171`（`C4 自启动注入 \| open \| blocked_reason：需改 CLD preset（外部第三方不代做）`） |
| NATS 影子 PoC | 仍 `open`，**未开工** | v5 §15 Q-C |

    $ grep -n 'C4 自启动注入' docs/execution-audit-anchor-v5-20261010.md
    171:| C4 自启动注入 | `open` | `blocked_reason`：需改 CLD preset（外部第三方不代做） |

---

## 14.3 M0–M3（承继 v5 §14，判定按 v5 自己的实测）

**v5 `:492-497` 逐字原文（四行，未概括）**：

    492: | 里程碑 | 判定（v5 实测） | 依据 |
    493: |---|---|---|
    494: | **M0** 审查与校对门可跑；信标四件套在位 ⇒ 新会话 ≤5 分钟恢复计划认知 | ❌ **不成立** | **C4 自启动注入未做** ⇒ 新会话不会自动恢复认知，每次需人工指路 |
    495: | **M1** compaction 生效、单会话体积降 ≥50%；装载超限拒绝而非崩；子进程内存可见；同内容重放 0 重复；熔断可触发；风暴系统自动发现；一卡一次注入 | 🟡 **部分具备** | Wave S 门已备（审查/校对/沙箱/信息包/G-CR）；★ 但**开关未合**（Wave 0 未开工） |
    496: | **M2** 真积压 ≤10；限速无边界缺陷；风暴期关键消息通过率 ≥90%；端口固定 | ❌ `open` | 依赖 Wave 1–2 |
    497: | **M3** 载体迁移完成且 I1–I4 成立；归属可验；黑板有 GC；时序可全序复原；订阅唤醒上线；**25 类崩溃坑零复发** | ❌ `open` | 依赖 Wave 2–4 |

**v6 按上表重述（判定不变；★ 补「解除条件」，v5 无此列）**：

| 里程碑 | 判定 | 依据（v5 自身实测 + 本轮复核） | **解除条件（v6 新增）** |
|---|---|---|---|
| **M0** 审查与校对门可跑；信标四件套在位 ⇒ 新会话 ≤5 分钟恢复计划认知 | ❌ **不成立** | **C4 自启动注入未做** ⇒ 新会话不会自动恢复认知，每次需人工指路。★ 本轮复核：`C4` 仍 `open`（`execution-audit-anchor-v5-20261010.md:171`） | ①`C4` 落成（agent preset prompt section）②新会话**冷启动实测** ≤5 分钟恢复认知（须给实测记录，非声明）③`Q-G` 批准链闭合 |
| **M1** compaction 生效、单会话体积降 ≥50%；装载超限拒绝而非崩；子进程内存可见；同内容重放 0 重复；熔断可触发；风暴系统自动发现；一卡一次注入 | 🟡 **部分具备** | Wave S 门已备（审查/校对/沙箱/信息包/G-CR）；★ 但**开关未合**（Wave 0 未开工）。★ 本轮复核：Wave 0–5 全 `open`，**39 项 0 完成** | ①Wave 0 合闸 ②逐条给「触发 ≥1 且体积降 ≥50%」等**实测读数**（v5 §11 `:431` 已定判据）③`W0.1` 补 P26 负控**能红**（v5 `:437` 硬要求）④七件门获**独立 verifier**（v5 §11.1 `:444`：`❌ 缺独立 verifier`） |
| **M2** 真积压 ≤10；限速无边界缺陷；风暴期关键消息通过率 ≥90%；端口固定 | ❌ `open` | 依赖 Wave 1–2 | ①真积压读数 ≤10（现 **103**，v5 §12 `:467`）②风暴期关键消息通过率 ≥90%（实测）③端口固定：**3 次重启地址不变**（v5 §11 `:435` 判据） |
| **M3** 载体迁移完成且 I1–I4 成立；归属可验；黑板有 GC；时序可全序复原；订阅唤醒上线；**25 类崩溃坑零复发** | ❌ `open` | 依赖 Wave 2–4 | ①`W2.5` 载体换：I1–I4 成立 + `30,755` 行一致 + 幂等重跑 0 新增（v5 §11 `:434`）②黑板 GC/TTL 在位（现 `DELETE 0`）③**订阅唤醒上线**（现订阅者指向已 bricked 会话，见下）④同类崩溃复发 = 0 |

★ **M3 的「订阅唤醒上线」本轮实测反证**：`event_subscriptions` 首要订阅者 = `session-fa1f9150-…`（首任星桥，2026-10-09 因 P26 bricked），订阅全部 5 类 topic；`~/.dsh/agent-role-map.json` 已完全不含该 id（`grep -c` ⇒ 0）⇒ **所有新事件都生成一条指向死会话的指令**；`event-bus.py --status` ⇒ `events:122 · instructions: total=122 pending=111` ⇒ **91% 不可投递**。
★ 且 `central-inbox` 插件**已修**该常量（`lib/index.js:147` `DEAD_SESSIONS` 硬编码 + `:141` 注释「不再按 fa1f9150 优先匹配」）而 `subscriptions.json` **没修** ⇒ **插件修了、数据没修**，属「修了一半」。

---

## 14.4 ★ M4 通讯基线（v6 新增）

**M4 的定位**：v5 的 M0–M3 全部是**进程内/单机**的里程碑（认知恢复、compaction、积压、载体），**没有一个覆盖「跨会话/跨智能体/跨设备通讯」本身** —— 而后者恰是 §0.1 的**目标原话**。⇒ **M4 = 把目标措辞第一次落成可判基线**。
**排序**：M4 **独立于 M0–M3 的依赖链**（不依赖 Wave 2–4），可与 Wave 0 **并行**开工 —— 因为它量的是**现存链路**，不需要先合闸。

### 三条判据（我采纳建议 ①②③，但**各自收紧**，理由随条给）

| # | 判据（v6 定稿） | 依据（**复跑命令 + 未编辑输出**） | 判定 |
|---|---|---|---|
| **M4①** | **drift 告警双板到达率 == 100%**，且**中枢侧最新告警落后 ≤ 2×巡检周期（30 min ⇒ ≤60 min）** | `curl -s http://127.0.0.1:8792/data/ops/drift-alert/` ⇒ `total= 304`；`curl -s http://106.53.214.108:8792/data/ops/drift-alert/` ⇒ `total= 19` ⇒ **未达中枢 285 张 · 到达率 = 19/304 = 6.25%**。`time` 解析：本机板 `最新=2026-10-10T23:46:04.803+08:00` · 中枢板**最新卡**（板级 `ts`）＝ `2026-10-03T13:27:35+08:00`；★ 补充：同卡**内层 `value.ts`** ＝ `2026-10-03T12:30:49.275`，两者差 **56m46s**（须登记为活体事实） ⇒ **冻结 ≈7.5 天**。根因（代码级）：`scripts/drift-scan-cron.py:87-89` 对中枢 PUT 的 `headers` **只有 `Content-Type`，无认证头** ⇒ `/tmp/drift-scan-cron.err.log` 实测 `grep -c '401'` ⇒ **134**（末行 `urllib.error.HTTPError: HTTP Error 401: Unauthorized`）；`launchctl list` ⇒ `- 1 com.dsh.cron.drift-scan`（每 30 min 重复、exit 1、**无人告警**） | ❌ |
| **M4②** | **不存在未登记通道**。判据须写成**三条合取**：①每条活体通道**具名** ②至少登记在 `drift` 矩阵 **12** 项 或 `channel_gate` 枚举 **7** 条 之一 ③每条**有负控（造断 ⇒ 必红）** | `drift_scan` 实测 ⇒ `total: 12`（`scannedAt 2026-10-10T15:54:58.119Z`，`driftCount: 1`）。`channel_gate` 冻结枚举 **7 条**（`~/.dsh/profiles/web/node_modules/dsh-plugin-channel-gate/lib/gate.js:22-30` 逐字）：`local-agent-bus` · `board-local` · `board-central` · `bus-8791` · `sse-8803` · `tailscale-direct` · `launchd-daemons`。★ **未登记通道具名 = 「卡 → 自动唤起会话」的【跃迁方】`dsh-plugin-central-inbox`**（五环调用链见 §7.10 P28-①）；★ 另注：`bb-sub`（`launchctl list \| grep -c 'bb-sub'` ⇒ 8）**亦不在两张登记表内**，但其是否属「副作用跃迁方」**不可判**（其既定职责为订阅落 inbox）；而 `channel-matrix.json` 的 11 个检查键 **+ 运行时追加 1 项 = 12** 中，`grep` `wake\|card\|bb-sub` ⇒ **0 命中**；`channel_gate` 7 条中亦无此项 | ❌ |
| **M4③** | **投递可见**。判据须写成三层：①`queued` 在**输出面**（卡面/日志/返回体）**显式标「未达」** ②`expired` **必须产生告警** ③判据用**「运行面状态 + 收端转录」两路闭环**，**不得只看 bus 状态字段** | 代码级：`~/dsh-plugin-agent-bus/lib/index.js:84` ⇒ `const QUEUE_TTL_MS = 7 * 864e5;`（**7 天**）；`:1305-1326` `flushQueue()` 对超期项只做 `m.status='expired'; m.expiredAt=now; expired++; continue;`，**全程无任何告警/日志输出**，`:1326` 仅 `if (delivered>0\|\|expired>0) void persist();` ⇒ **静默**。真达率：★ **判不可判**（见 §12 通讯面口径警示）；可复现的现状读数＝全量终态分布（★ **以复跑命令取值，不写死数字**；两次实测：N=33613 → **N=33614**，`delivered` +1）＋复跑命令 | ❌ |

**★ 我对三条的修订及理由**

- **① 增「中枢落后 ≤60 min」** —— 理由：**单看「到达率」可被作弊**（把发送端停掉，到达率反而"稳定"）。**落后量才是能红的判据**，且它正是本次事故的实相（304 张里 285 张没过去，中枢冻结 7.5 天）。
- **② 增「③每条有负控」** —— 理由：`drift_scan` 现在 **12 项只有 1 项红**（`funnel-public` HTTP 502），而**公网入口真 502 却无人知道** —— 因为**告警送不出去**（M4①）。⇒ **「登记了」不等于「能发现」**；无负控的登记项就是恒真判据。★ 且「分母」必须由**活体实测**得来：本轮实测 `drift_scan` 报 `total: 12` 而 `channel-matrix.json` 只有 **11 个检查键 + 1 个 `_comment_l3` 注释键**，第 12 项是**运行时追加**的 `bus-8791 token 权限`（`kind: file-perm`）⇒ **只读矩阵文件会少数一项**，这就是「分母被过滤」的又一形态。
- **③ 增「输出面」「expired 告警」「两路闭环」** —— 理由：`expired` **已经是状态字段**，字段**在**而**没人看** ⇒ 不叫「可见」。**可见性的定义必须落在「有没有人/有没有工具会因此报警」上**，否则就是把「有字段」当「可见」。

### M4 判定与解除条件

| 里程碑 | 判定 | 解除条件 |
|---|---|---|
| **M4 通讯基线**（drift 双板通 · 无未登记通道 · 投递可见） | ❌ **不成立**（① 6.25% / ② 具名 1 条未登记 / ③ 静默 + 真达率不可判） | ①a 双板到达率 **100%** 且**连续 7 天**；①b 中枢落后 **≤60 min**；①c `drift-scan-cron.py:87-89` 补认证头（**经 `channel_gate` 登记变更单**，通道 = `board-central`）；①d 该项**有负控**：造 401 ⇒ **必须红且必须有人收到** ②a 具名未登记通道**全部登记**（至少在 `drift` 矩阵或 `channel_gate` 枚举之一）②b 每条登记项**有负控**（造断 ⇒ 必红）②c 登记表**分母由活体实测生成**（不得手写、不得只读矩阵文件）③a `queued` 在输出面显式标「未达」③b `expired` 产生告警且有读者 ③c 判据改为「运行面状态 ∧ 收端转录」两路闭环，`verify-delivery` 类工具接入发送路径 ③d 真达率实测 **≥ 95%**（以两路闭环口径计） |

### M4 与 §0.1 四维的对应

| §0.1 维度 | M4 判据 | 覆盖 |
|---|---|---|
| 稳定性 | ① ② ③ | 全覆盖 |
| 健康度 | ①（送达率）+ ②（负控） | 覆盖 **H2/H3**；**H1**（假绿）另挂 §7.11/§13 R19 |
| 与业界对齐 | **不覆盖** | 另挂 §3.4 / §12 业界面（见 §0.1.5） |
| 保持领先 | **不覆盖** | 另挂 §12 业界面 + §15 开放项 2 |

⇒ **M4 是「通讯基线」，不是「协议符合度门」。混装会让 M4 无法收敛。**

---

## 14.5 复跑块（★ 本节所有会变的数字，一条命令全出）

    # [1] 两板 drift 告警到达率（M4①）
    for u in http://127.0.0.1:8792 http://106.53.214.108:8792; do
      printf "%s → " "$u"; curl -s --max-time 10 "$u/data/ops/drift-alert/" \
        | python3 -c "import sys,json;print('total=',json.load(sys.stdin).get('total'))"
    done
    # [2] drift-scan 检查项数与被冻结的 401 计数（M4①②）
    drift_scan                       # → total / driftCount / rows
    grep -c '401' /tmp/drift-scan-cron.err.log
    # [3] channel_gate 冻结枚举条数（M4②）
    sed -n '22,30p' ~/.dsh/profiles/web/node_modules/dsh-plugin-channel-gate/lib/gate.js | grep -c 'owner:'
    # [4] 未登记通道的活体规模（M4②）
    launchctl list | grep -c 'bb-sub'
    # [5] queued TTL 与静默性（M4③）
    grep -n 'QUEUE_TTL_MS' ~/dsh-plugin-agent-bus/lib/index.js
    sed -n '1305,1326p' ~/dsh-plugin-agent-bus/lib/index.js
    # [6] M0 缺口（C4）
    grep -n 'C4 自启动注入' docs/execution-audit-anchor-v5-20261010.md
    # [7] 阶段轴（14.1）
    grep -c '阶段' docs/distributed-agent-network-governance-plan-v5-20261010.md
    stat -f 'birth=%SB mtime=%Sm size=%z' -t '%F %T' research/cost-governance/architecture-evolution-stages-v1.0.md

---

**本节一句话**：**M0 ❌ · M1 🟡 · M2 ❌ · M3 ❌ · M4 ❌**；M4 是 v6 唯一为「目标原话」而设的里程碑，**三条判据全部不成立，且三条的现状读数我都独立复跑过**。

# §15 未决问题

**沿用 v4，状态未变（九条）**：**Q-A** 去重淘汰语义（建议分层）· **Q-B** 端口固定值（你定）· **Q-C** 是否引入 NATS（先影子 PoC）· **Q-D** 注入器保留哪个（建议 SSE）· **Q-E** HMAC 密钥分发（本机 0600）· **Q-G** 自启动注入批准 · **Q-H** 载体换独立窗口安排 · **Q-I** `item-validity-review-check` 是否收编为闭环判定器（其 open 口径待裁判裁）· **Q-J** 四项历史决策（板鉴权/A 类仓/meituan-multi/「-」仓）。

**Q-F** ❌ **已废**（v3 改题记录保留）：原「挂载 compaction 批准」不再适用官方 `compaction-basic`（机制二无配置解）；用户 2026-10-09 以「**立项**」改为自研后端（见 Q-K）。

**Q-K** ✅ **已批立项** —— 自研 no-summary 压缩后端（走 `agent/pre-step` 守卫 seam，**与官方 backend 并存、不替换 `ctx.compaction`**；N→1 有界非摘要检查点，按 R006 十项交付）。
★ **v5 补现状**：三件接线（① 写入 → ② 落盘 → ③ 召回）**进行中**，执行方 `session-28174037`；起草方（本会话）持**审查位**（R046 分离：方案由起草方写 ⇒ 执行不该也是起草方）。**复核四项**：`requiresHostMeterCheck` 是否遵守 · 写前是否再判并发护栏 · `DEGRADED` 是否被冒充 `MISS` · 接线后工具文案是否同步更正。

**Q-L** R049 接入 C4（自启动注入）—— 待做；★ **与 C4 是同一件事**，M0 依赖它。

**Q-M** ★ **v4 与本版初稿均漏载、经与索引比对后补入**：`dsh-plugin-excalidraw` 宿主端 `inject=['slots']` 致 CLD 起不来（2026-10-09 事故）。**状态：未决**，与 P1/P3/P4（插件树加载类）同族。

## ★ v5 新增（★ 编号自 Q-N 起 —— `Q-M` 已被上式占用）
- **Q-N 索引判据缺口的修正归属** —— P27/G-CR18 的实例已登记为 `docs/pending-backlog.md` B8/B9/B10；索引的 writer 是**外部第三方**，起草方按 S3 不代改其语义判定。⇒ **待路由**。
  ★ 但**升版所需的最小字段更新**（anchor 路径 · `state_version` · `updated_at` · 两段一致化）**属 §4.6 规程，已由本次升版执行**，不与本问冲突。
- **Q-O Wave S 的独立 verifier 由谁担任** —— 七件门工具目前全部作者自测。候选（均离线，唤醒须授权）：守灯 `9910d4b2` / 独立复核员 `4d0e75cf` / 司库 `2a15e6b1`。
- **Q-P C4 自启动注入是否值得做** —— 它是 **M0 的唯一缺口**，代价是改 CLD preset（须批 + 涉重启窗口）。⇒ 一个待裁的性价比问题。
- **Q-Q 本地副本与板值的单一来源** —— 实测二者独立且可漂移（§7.8 P27 第四层）。⇒ 待裁：合并为单一来源，或补互校判据。

★ **编号纪律（本次踩坑记录）**：v5 §0.0 第 6 条本应包含「Q-M 漏载」，起草时未先与索引 `open_questions` 逐条对表 ⇒ **先撞号后察觉**。这与 F82（起草时未先检索本账本）**同族** ⇒ 该条纪律已并入 §17.7。

---

# §16 附录

**证据索引（v5 逐条标注可解性）**
| 证据 | 可解 |
|---|---|
| `agent-bus/lib/index.js:{70-78,191,561,740,1111,1125,1140,1296-1303,1375-1405}` | 待复核 |
| `~/.dsh/profiles/web/package.json`（★ v5 更正：**含** `dsh-plugin-context-survival`，非 v4 所记「41 bundles 无 compaction」） | ✅ 实测 |
| `~/.dsh/sessions/--Users-coreyleung--/session-fa1f9150-…/session.jsonl.zstd` | 待复核 |
| 黑板审计 PUT 23,722 / DELETE 0 | 待复核 |
| `~/.cld/logs/dsh-web.log`（OOM ×13） | 待复核 |
| `rules-registry/RULES.md`（**含 R059**，L571） | ✅ 实测 |
| `docs/wave-s-toolchain-delivery-v1.md`（214 行） | ✅ 实测 |
| `tools/{sandbox-script,infopack-check,review-gate,official-ref-gate,gcr-gate,node-claim-gate,self-destruct-gate}.py` | ✅ 实测（字节数已核） |
| `docs/pending-backlog.md`（B8/B9/B10） | ✅ 实测 |
| `docs/c7-half-fix-clause10-20261009.md` · `docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md` · `docs/context-survival-conservative-plan-20261009.md` · `docs/compaction-lowerbound-crash-20261009.md` · `docs/starbridge-stage-report-and-review-package-20261009.md` · `data/registry/state-registry.json` | ✅ **在位实测** |
| `scripts/build-bundle.sh:2,29` · `rust-blackboard/src/http.rs:237` · `comm-server/{comm_domains.py,agent-mailbox.py}` | 待复核 |
| `~/Desktop/归档/2026-08-18/DSH-macmini-防崩溃运维手册.md` · `docs/cld-{boot-and-session-list,tools-instance-split}-fix-20261006.md` | 待复核 |
| 既有深调研 12,101 行（`research/agent-comm-paths/`） | 待复核 |
| `docs/item-validity-index.json`（2,642 条）+ `devices/dsh-plugin-item-validity-review-check` | 待复核 |

**复用而非新造**：会话级继承（2 份）· 规则级闭环（R020）· 投递闭环语义 · L1 SQLite 实现 · `item-validity-review-check` 五态；v4 新增「计划级信标 + 审查流水线 + 官方校对门 + 崩溃坑登记」；**v5 新增「自足锚点 + 四件同步规程 + 判据补强 + P27/G-CR18 + §17 交付规程」**；**v6 新增「§0.1 主线目标定义 + §3.4 业界最优性对照 + §7.10 P28 通讯缺陷族 + §7.11 P29 假绿族 + §10 三组 W 项 + §12 三面 SLO + §13 R060–R062 + §14 M4」**。

## ★ 16.4 旧阶段图 = 历史轴（v6 新增）

★ **声明**：`research/cost-governance/architecture-evolution-stages-v1.0.md`（**阶段 0–4** 那张图）**是另一条与之独立、且已停摆的旧轴** ⇒ 本版**不引用、不承继、不进任何表**。

**判据（可复跑）**：

```bash
stat -f 'birth=%SB mtime=%Sm size=%z' -t '%F %T' research/cost-governance/architecture-evolution-stages-v1.0.md
grep -c '阶段' docs/distributed-agent-network-governance-plan-v5-20261010.md
grep -c 'architecture-evolution-stages' docs/distributed-agent-network-governance-plan-v5-20261010.md
```

★ **实测**：该件 `mtime == birth == 2026-08-22 03:36:31`、`size=2818`，**从未更新**；v5 全文 588 行**「阶段」0 命中**、**从不引用该件**。

⇒ **v6 的唯一阶段轴 = `Wave`（S / C / 0–5）+ 里程碑 `M0–M4`**（见 §14.1）。
⇒ 混用两条轴会把 **2026-08-22 的旧刻度当当前进度** —— 与 P27「判据失明」同族。

---

# §17 交付规程（★ v5 新增章）

## 17.1 升版（四件同步）
见 **§4.6**。一句话：**锚点升级不是改一个文件，是同一批动四件**（锚点 / 索引 / 续接提示词 / 版本指针），并须额外核对**本地副本 ↔ 板值**。

## 17.2 起草 → 成立
```
起草（作者）→ 自证（跑 beacon-check / selftest / 负控）→ 沙箱复跑 → 独立 verifier → 记 closed
```
**作者不得自审**（S3）。本件由起草方自行升版 ⇒ **`verifier: 待第三方复核`** 是必需字段，**不是客套**。

## 17.3 时间戳纪律（★ 由实测事故逼出）
**禁止手写、禁止按会话推进感觉估算；一律实读。** 且须用 **RFC 3339 规范形（含冒号）**：
```bash
# ★ 本机（macOS BSD date 不支持 %:z，实测输出 ":z"）——可移植写法：
TS="$(date '+%Y-%m-%dT%H:%M:%S')$(date '+%z' | sed 's/\(..\)$/:\1/')"
# 产出形如 2026-10-10T07:18:13+08:00   ⇒ 时区偏移必须带冒号
```
★ 本条规定源自 **三起** 同族事故：① 起草方 2026-10-10 把卡写成未来 24.2h；② 权威索引的 `updated_at` 超前约 19h（P27 第一层）；③ 起草方 v5 初版把公式写成 `date "+…%z"`，产出 `+0800`，而 `datetime.fromisoformat()` 在本机系统 python3（**Python 3.9.6**）下抛 `ValueError` ⇒ **判据当场崩**。**三起独立发生 ⇒ 判定为系统性，非偶发。**
★ 推论（重要）：**时间戳格式不统一，会使「时间戳合理域」这类判据自身不可靠** —— 与 P27 同族。⇒ 规范形 = **`YYYY-MM-DDTHH:MM:SS±HH:MM`**，两种偏移写法**不得混用**。

## 17.4 判据不得自指
新增检查项必须回答：**「如果事实变了，这条会红吗？它比较的两端是不是同一个源？」**
若两端同源 ⇒ 一起变则永远相等 ⇒ **该检查恒真，不具判别力**（P27 的直接成因）。

## 17.5 报不通过，不调参
门不通过 ⇒ **报不通过**；**不通过就调阈值使其通过 = 制造假绿**。

## 17.6 锚点必须自足（★ v5 新增）
锚点文档**不得以指针代替内容**。若某章内容留在另一份文件，则该文件**仍是规范源** ⇒ 与「历史冻结」矛盾，且使 M0「只读锚点即恢复认知」不成立。
⇒ 规则：**升版时须把承继内容完整内联**；旧版**冻结为只读历史**（不在其上继续编辑 ⇒ 不会漂移）。

## 17.7 起草前须与已登记项对表（★ v5 新增，由本次踩坑逼出）
起草任何带编号的新条目（Q-x / R-x / W-x / G-CR-x / P-x）之前，**必须先读现有登记表并逐条比对占号**。
★ 实证：本次 v5 起草时未先与索引 `open_questions` 对表 ⇒ 把「索引判据缺口归属」编成 `Q-M`，而 `Q-M` **早已被 `dsh-plugin-excalidraw` 事故占用** ⇒ **先撞号后察觉**；且因此**发现 v4 漏载了 Q-M 本身**。
⇒ 与 **F82（起草时未先检索本账本、把同族规则当作新发现）同族**。**规则：先对表，再编号。**

## 17.8 并行分派前须先划【共享编号空间】（★ v6 新增，由本次三处同型事故逼出）

**规程**：把一份大件拆给**多条互不知情的线并行撰写**之前，**必须先发一份共享编号空间清单**，至少覆盖四类：

| # | 空间 | 本次教训 |
|---|---|---|
| 1 | **规则号（R-x）** | ★ `R18` 被两条线**各写一次**；且新写的 `R18/R19/R20` 与 `rules-registry/RULES.md` 已占的 **R018/R019/R020 同号异义**（三号全被占）⇒ 最终改号 **R060–R062** |
| 2 | **判据号（H-x）** | ★ 两套语义并存：W1 用 `H-1..H-4`、W3 用 `H1..H5`，其中「假绿数 / 静默失败 / 送达率」三项**同题相撞** ⇒ 合并时须统一为一套 |
| 3 | **指标名** | ★ 「信封符合度」**同一指标落在两个宿主节**（通讯面 vs 业界面），分母与目标均不同 ⇒ 须**先指定唯一宿主节** |
| 4 | **W 项段位** | ★ 三线**各自预定** W6/W7/W8 段（大纲原写「我统一编号」）⇒ 此**次侥幸不相交**，属无协调下的运气 |

★★ **本次最重的一条：指令表自身三次自相矛盾**（**编辑规程 E1**）
> **三次同型**：我一边要求写入含某字面的内容，一边要求「该字面 `grep` 必须 = 0」。
> · W4：要「逐字替换成稿」+ 要 `nlines_ = 0` —— 而成稿文字**本身就含 `nlines_`**
> · W2：要「插一行含 `54.7` 的作废注」+ 要 `54.7 = 0`
> · W3：要写「不构成『完整覆盖』」+ 要 `完整覆盖 = 0`
>
> ★ **三条编辑线【无一替我猜】**：W4 交回二选一并给替换文本；W2 按令照插并主动给出**判别式**；W3 改为同义且不触发的「**全窗覆盖**」并注明「此点不得省略」。
>
> ⇒ **规程 E1**：**凡给「某字面串计数必须 = 0」类判据，须先核该字面是否被【你自己要求写入的内容】所包含。** 三选一：① 用**判别式**而非绝对计数（`grep -n X | grep -v <豁免标记>`）；② 把要写的内容改成**不触发该字面**的同义表述；③ 在判据里**明示豁免位**。
> ⇒ **理由**：这类判据本意是「防旧表述残留」，但若它**同时禁止了自己要求写入的新内容**，就把下级逼到「违反指令」与「违反验收」之间 —— **无论怎么选都是错**。

★ **另一条同族（写作侧）**：**定位锚必须唯一**。本次合并脚本用「上一块的末行」当链式插入锚，而那行是 ``` ``` ```（在文中出现 16 次）⇒ `str.replace(...,1)` **静默插到文件开头**，而脚本仍报「成功 4/4」。
⇒ **规程**：**插入/替换一律用【行索引】定位，不用字符串匹配**；且**验收要读【位置】（行号），不能只数【命中数】**。

---

# §18 跨会话协作协议族（★ v6.1 新增）

> **为什么新增本节**：2026-10-11 实测发现「**断点 B · 锚点未收**」—— 多份既有协作协议在本锚点中**命中 0**
> （`CCEP` 0 · `blackboard-dispatch` 0 · ★ **MCP 相关 12 份全部 0**），**新会话只读锚点恢复不到它们**。
> **与 §17.6 自足性的关系**：这些件是 **【活规范件】**（**不是**历史锚点）⇒ ★ **本节内联其核心条款 + 标注全文位置** ——
> 既满足「**读锚点即能恢复认知**」，又不复制**会漂移的全文**。
> ★ **判据**：本节每条内联内容，**必须足够让新会话不犯错**；读者**不必先读全文**。

## 18.1 CCEP · 永续通讯协议（五原则）

**全文**：`docs/CCEP-continuity-protocol-v1.md`（4,508 B · 2026-08-28 · 用户确立的根本原则）

**一句话**：通讯通道的任何迭代，都必须**用旧通道投递新通道、验证可行才切换** —— 除死机等极端情况外保持永续通讯，**永不需要人类手工重新打通**。

**五原则（不可违背）**：★ **编号更正注（外部复核 S2-6）**：源件 `:13–14` 的编号有缺陷（**两个「4.」**：一个「沙箱先行」、一个「可回滚」）⇒ ★ 本节按语义**重排为 1–5**，★ **此为静默规整，现补更正注**；★ **源件缺陷已回报**（见 §18.6.3）。

1. **永续通讯**：升级过程中**任何时刻至少有一条可用通道** —— 绝不出现「全部断掉需人工重连」。
2. **通道自举**：新版本必须**通过旧通道投递**，端侧在旧通道上收到完整迭代信息并**验证**，才切换。
3. **验证先行**：本地完全准备妥当（编译 + 测试 + 隔离验证）后才投递。
4. **沙箱先行**：任何重启/测试前先跑安全沙箱验证 ⇒ **沙箱验证 → 生产切换两步分离**。
5. **可回滚**：每次切换保留旧版本/旧配置快照，**失败可秒级回滚**。

**通道迭代五步**：① 准备（本地编译 + 单测 + 隔离验证）→ ② 投递（**用旧通道**）→ ③ 端侧验证（自检 + 回报）→ ④ **就绪确认（任一未就绪 ⇒ 不切换）** → ⑤ 切换 + 回滚保障（切换后 24h 观察心跳/注入/无 401）。

**禁止事项**：❌ 不验证就切换 · ❌ 单端先行切换 · ❌ 物理复制插件 · ❌ 依赖人类手工重连 · ❌ 破坏性变更不留回滚路径。

★ **与 §4.6 的关系**：§4.6 管**锚点升版**的四件同步；CCEP 管**通道本身**的迭代 —— **两者都要求「先验证后切换」。**

## 18.2 黑板值班投递协议

**全文**：`blackboard-dispatch-protocol.md`（2,425 B · 2026-08-20 · HR 建立 · 用户批准方案 1）

**机制**：

```
黑板变更/事件 → 脚本检测(5min) → 队列（wakeup-queue / send-instructions）
  → 值班 agent 回合消费 → agent_send 定向 → 目标 agent 上下文收到小 token 提醒
```

**值班规则（所有 agent）**：

1. **每个实质回合**先查待发队列：`python3 ~/dsh-collab/scripts/event-bus.py --status`（★ 外部复核 S2-7：补绝对路径，读者照抄不必在仓库根）
2. 有 pending ⇒ 读 `send-instructions/*.json` ⇒ **按 agent 定向 `agent_send`（只发摘要 + 指针，非全量）** ⇒ `--mark-sent <id>`
3. ★ **HR 为默认值班**（每次实质回合代发积压指令）
4. **daily-brief 22:00 批量兜底**
5. 不重复（`dedup_key` + sent 标记）；**已过期信号（>24h）归档不发送**

★★ **实测缺陷（2026-10-11，即「断点 A」）**：

```
$ python3 scripts/event-bus.py --status
  events: 122 {'task.completed': 4, 'agent.online': 59, 'agent.offline': 59}
  instructions: total=122 pending=111
    PENDING: … -> session-fa1f9150-c94 agent.online 节点上线: …
```

- **pending 111 条**（占 122 条的 **91%**）· ★ **全部指向 `session-fa1f9150-c94`**（**已 bricked**）
- ★★ **时间口径（★ 外部复核 S2-1/S2-2 更正）**：
  · **队列存在跨度** = 2026-08-20 15:10 → 2026-10-03 **14:54:24** = **44 天**（★ 本版初稿曾把终点写成 `14:58`，**不可复现**：`events` 与 `instructions` 的**最大 ts 均为 `14:54:24`**）
  · ★★ **积压（pending）跨度** = 2026-08-23T03:12:51 → 2026-10-03T14:54:24 = **41 天** ⇒ ★ **「积压 44 天」用词不准，正确说法是「队列存在跨度 44 天 / 其中积压 41 天」**
- **根因**：规则 3 的默认值班者 **HR 会话已缺位** ⇒ **队列在写、消费端死了**
- ⇒ ★ **本协议现状是「有机制、无人值守」**；★ **处置见 §18.6.3 待办 1**

## 18.3 跨域邮箱 xdom · 水位 / 球权 / 陈旧

**全文**：`docs/xdom-mailbox-protocol-v1.md`（9,355 B · 2026-10-10 · 外部 CU 线出件）· **工具**：`tools/xdom-mail.py`

**四个子命令**：`send`（只写自己域的信键）· `inbox`（读信，含水位与球权；**空 ≠ 无信**）· `ack`（推进自己的水位，只写自己的 `cursor` 键）· `status`（板可达 / 日志 / 双方水位 / 球权 / 陈旧）

**三条结构性质**：

1. **两域互不相交**：`log` 键归发方 · `cursor` 键归读方 ⇒ **无 read-modify-write**
2. **不同源**：判「对方读没读」比的是**发方写的信键**与**收方写的水位键** ⇒ **不可能一起漂移**（P27 根因）
3. ★ **球权不落盘**：由**日志最后一条的 `ball` 字段派生** ⇒ **无冗余状态源**

★ **域定义**：`party ∈ { ext = 外部会话, int = 内部会话 }` · ★ **别名共六个**（第六轮复核 S2-新⑥ 更正计数：初稿写「四组」，实列 **6 个**）：**`cld` / `星桥` / `内部` → `int`** · **`cu` / `claude-code` / `外部` → `ext`**（源件 `:105` 逐字）

★★ **两处已证伪的表述（2026-10-11 更正，勿再引用旧说法）**：

| 旧表述 | 实测 | 正确表述 |
|---|---|---|
| 「越域写入由 `owns_key()` **直接拒绝**」 | ★★ **更正本行的证据（外部复核 S1-5）**：`ack --as ext` 写的是 `cursor/ext`（**本域**），**不是越域尝试** ⇒ ★ **它不构成 `owns_key` 的反例**。★ 成立的是另一件事：★ **CLI 面的 key 恒由 `--as` 指定的 party 派生 ⇒ 「ext 写 cursor/int」这种输入在 CLI 面【构造不出来】**（见 `tools/xdom-mail.py:341/428`）。★ 且该负控**只覆盖函数层** —— ★ **行号更正（第六轮复核 S3-新⑨）**：判据实为 **`tools/xdom-mail.py:541`** 的 `chk(not owns_key(CUR_PREFIX + "int", "ext"), …)`（`:540` / `:543` 为另两条对照）；★ 初稿引的 `:531` **是注释行** ⇒ 已改 | `owns_key` 保证的是【**自洽**】，**不是鉴权**；★ 正确表述是 **【CLI 面『不可达』】**，而非【被拒绝】—— ★ 二者语义不同：**「被拒绝」可被违反、可验证；「不可达」构造不出该情形、不可验证**。★ 且原件的**核心定性是「判据假绿」**（源件 `xdom-mailbox-protocol-v1.md:54`） |
| ★ **（无「旧表述」——本行是【本版新增实证】，非对原件的更正）**（★ 本单元格改写属第六轮 S3-新⑧ 的修正对象） | ★ 本线实测（**本版新增**）：以 `--from ext` 发出即**写进 ext 域**，`writer_label` 被标成「外部（Claude Code）」 | ★★ **本工具【无身份概念】：`--as`/`--from` 是自称，CLI 面【无法阻止冒充域】。** ★★ **原件定性不可丢：这是一次【判据假绿】**——`--selftest` 的三条负控**只测纯函数、从未走 CLI 路径** ⇒ **负控绿在函数上，而函数不是被调用的那个对象**（与 §13 `R060`/`R061` 同型） |

⇒ ★ **待裁的两条路**：**(a)** 降级声明「本工具是**协作约定**，不是**访问控制**」；**(b)** 补**独立于 `--from` 的凭据**（每域 token / 0600）+ **走 CLI 路径的负控**。

## 18.4 通讯规范端口（操作 → 正确路径）

**全文**：`docs/agent-comm-portal-20261002.md`（7,079 B · 2026-10-02）

**一句话**：做任何跨会话/跨设备/通道操作前，**先查它拿正确姿势 —— 照做零摩擦**。

**核心总表（照做）**：

| 我要做什么 | 正确路径 | 工具/命令 | 走错的后果 |
|---|---|---|---|
| 同机会话间发消息 | **≤50 字 + 内容落黑板再发「看黑板」指针** | `agent_send` | 全文超限被门拦 |
| ★ **跨设备发消息** | **只有黑板卡一条真通道**（双写两板） | `bb-card-send` | `agent_send` 跨机不通：**静默排队 7 天进 DLQ** |
| 跨设备发内容卡 | **双写两板 + 回读断言 + `to` 必填完整 id** | `bb-card-send` | 漏 `to` ⇒ 对端白名单**静默不注** |
| 要求对方回复 | 信封 `reply_required=true`（**同机用 `agent_send` 参数；跨机 = 卡上标 `reply_required:true`**） | `agent_send` / 卡字段 | ★ **对方空闲时排队不唤醒**（源件 `:14` 原意；★ 本版曾误写为「对方不知道要回」，属**不同机制、不同修法**，已按外部复核 S1-7 还原） |
| ★ **变更任何通道/守护** | **先登记变更单（5 字段 + 回滚点真实存在）** → 人工执行 → 后跑 `drift-scan` | `channel-gate register` | 未登记变更 = 无治理 |
| 探测通道健康 | `drift-scan`（9 项矩阵）+ `launchd-scan` | 两工具 CLI | 漂移/静默失效不被发现 |
| ★ **接入新设备/新会话** | 按自检清单 → 回执给协调者 | — | 注册表不在册、心跳旧 |
| 报修 | 降级纪律的结构化求救提示词 | 模板 | 边求救边乱试 |

★★ **判活口径（★ 必内联 —— 纯索引会导致新会话用「键体 ts」判活而读成伪新鲜）**：

> **只信【心跳 payload ts】（`hb_age_s < 90` = online）**；★ **键体 ts 会被镜像刷新 ⇒ 【伪新鲜】，不可作判活依据**。
> 复跑：`curl http://xingqiao.meetfunbp.com:8792/data/discovery/agents/<dev>`（返回 `status` + `hb_age_s`）

★ **另有**：发卡模板 · **变更通道模板（`channel-gate` 合法变更单）** · 接入自检清单 · **门拒绝消息 → 正确姿势对照** · ★ **禁用清单（实测会崩/会坏的通道）**

## 18.5 ★ 失败可见性体系（三段链 + 八态）

**全文**：`docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md` **§四**（该件 40,506 B；**本节只内联 §四**，2026-10-09 · **经裁判独立审查 5 条修正**）

**正名**：**失败可见性**（failure visibility）—— ★ **统摄而非并列**，下列全部是它的展开。

**三段链（各有独立修法）**：

| 段 | 回答的问题 | 失败形态 | 修法 | 角色 |
|---|---|---|---|---|
| **观察段** | 世界真是什么？ | **看不见**（八态之 1–7） | **让 X 自报 X 的状态** | 产出方 |
| **转述段** | 数据里有什么？ | 数据里有、叙述里没有（第 8 态） | **结论附 n / distinct / 覆盖范围** | 转述方 |
| **决策段** | 我需要知道什么？ | 维度不对口（**值全对**） | **消费方先声明决策问题** | 消费方 |

★★ **关键性质**：**三段的失败是【静默传递】的** —— **本段失败不报错，只在下一段变成【合法输入】**。

★ **P26 = 三段全断**（第三方裁定 ✅ 成立）· **⊥ R046**（正交：三段对应**三种信息角色**；R046 管**三种人**）（**第三方裁定 ✅ 成立** ⇒ ★ 本轮补回该等级，第六轮复核 S1-新⑨ 残留②）—— ★ **人分离不蕴含信息分离**。

★★ **证据等级定义（★ 必内联 —— 缺它会致「未验当已验」）**：

> `实测` = **本会话**一手取证 · `独立复现` = 第三方自建探针复现 · `裁定` = 第三方出过三态判定 · ★★ **`他方自陈`** = 由他方提供、本会话**未独立验证** · **`未验证`** = 尚无前述任一。

**八态（观察段七态 + 转述段一态）· ★ 含证据等级列**：

| # | 态 | 含义 | ★ 证据等级（源件逐态） |
|---|---|---|---|
| 1 | **提取不到** | 工具/解析失败 | 实测 |
| 2 | **搜不到** | 搜索面不匹配 | 实测 |
| 3 | **不告警** | 机制静默记账 | 实测 + 裁定 |
| 4 | **不生效** | 在位但作用域为空 | 独立复现 + 裁定 |
| 5 | **看不见失效** | 合法但已失效 | 实测 + 裁定 |
| 6 | **确认≠发现** | 探针输入取自被检对象 ⇒ 只能确认预言、不能发现异例 | ★★ **他方自陈 + 裁定**（源件 v3 修正：其探针原文由他方自陈，**本会话未独立验证**） |
| 7 | **报活跃≠报可用** | 报了一个**不回答问题**的维度（没报错） | 实测（读实现）+ 裁定 |
| 8 | **数据里有≠叙述里有** | 转述失败（数据 → 叙述段） | 实测 + 裁定 |

★★ **逐态判据（至少第 6 态，★ 必内联 —— 缺它会把「他方自陈」当同等级证据）**：★ **（本处为【推导性重述】，非源件 §四逐字 —— 源件把该机制写在【八态表的「含义」单元格（`:305`）】与【`:524`】（后者在 §四 之外）；内联正当因其含判据性输入，但须标「重述」）**（第七轮复核 S3-③）

> **第 6 态「确认≠发现」的判据 = 探针输入是否取自被检对象。**
> ★ 若**取自被检对象** ⇒ 该探针**只能确认预言、不能发现异例**；★ 其证据等级为 **`他方自陈` + `裁定`**，★ **不得与 `实测` 混列**。

★★ **源件的检验判据（★ 判据本体，必内联 —— 缺它会致「未定义引用」）**：

> **任何判据若不能回答「它让谁的什么失败变得可见」，就不是本体系的一部分。**

★ **源件的限制（★ 必内联，防「用元判据为体系自身辩护」）**：它是**元判据** ⇒ 只能做**归属判定**，**不能做有效性判定** ⇒ ★ **元判据不可用于为体系自身辩护**（与 `S3`「不可自审」同源）。

> ★ **本行更正（第六轮复核 S1-新⑨）**：初稿**只内联了限制、未内联判据本体** ⇒ 读者看到「元判据不可用于为体系自身辩护」却**无从知道那个元判据是什么**（`grep -c '让谁的什么失败变得可见'` 曾为 **0**）。★ 按第五轮复核给出的判据（**核心是否含判据性输入**），源件 §4.5 的**检验判据**正是**判据本体** ⇒ **已补内联**。

★ **本节与 §7.10 / §7.11 的关系**：§7.10（P28 通讯缺陷族）与 §7.11（P29 假绿族）是**具体病理**；本节是**统摄框架**。

> ★ **本版误加更正（外部复核 S1-8）**：原文此处曾写「**凡新增判据，须先问『它防的是八态中的哪一态』**」—— ★ 该句**源文没有**，是**本版误加的义务性语句**，★ 且与 §0.0b「**本版不新增任何判据**」直接冲突 ⇒ **已删除**。

## 18.6 协议族索引与独立立项件

### 18.6.1 本节已内联的活件

| 件 | 体量 | 性质 | 全文位置 |
|---|---|---|---|
| CCEP · 永续通讯协议 | 4,508 B | 用户确立的根本原则 | `docs/CCEP-continuity-protocol-v1.md` |
| 黑板值班投递协议 | 2,425 B | HR 建立 · 用户批准 | `blackboard-dispatch-protocol.md` |
| 跨域邮箱 xdom | 9,355 B | 外部 CU 线出件 | `docs/xdom-mailbox-protocol-v1.md` |
| 通讯规范端口 | 7,079 B | 操作总表 | `docs/agent-comm-portal-20261002.md` |
| 失败可见性体系 | §四 · 96 行 | 经裁判独立审查 | `docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md` §四 |

### 18.6.2 ★ 独立立项件（**不并入本锚点**）

| 件 | 体量 | 状态 |
|---|---|---|
| ★★ **MCP 外部接入层** | **设计 11,210 B + 架构图 3,296 B** | ★ **用户 2026-10-11 裁决：4 个评审点【挂起】，但【立项独立做】** ⇒ 立项件 `docs/mcp-external-access-project-20261011.md`；★ **其正文 / 进度 / 决策不进本锚点** |
| MCP 相关其它件（文件名含 `mcp` 者） | ★ **另 12 份 · 合计 61,098 B**（含四栈总规划 9,252 B） | 同上 |
> ★ **份数更正（第六轮复核 S1-新④）**：初稿写「另 **10** 份」，而 **61,098 B** 的构成是 —— `docs/` 下文件名含 `mcp` 者 **13 份 / 67,008 B**，**减去立项件**（`mcp-external-access-project-20261011.md`，**5,910 B**）= **61,098 B（★ 那是 12 份，不是 10 份）**。★ 复核者**穷举了 C(13,10)=286 个「10 件」子集，无一等于 61,098** ⇒ **数字对、计数错配**（与上轮 S1-2 同型）。★ 本行已改为 **12 份**；★ **口径已申报**（「文件名含 mcp」）。

### 18.6.3 本节待办（**执行权不在起草人**）

| # | 项 | 说明 |
|---|---|---|
| 1 | ★ **`event-bus` 积压 111 条 / 队列存在跨度 44 天（其中积压 41 天）** | ★ **口径同 §18.2**（第六轮复核 S1-新③：初稿此处仍写「44 天」，与已更正的 §18.2 冲突 ⇒ 已同步）
     ★ **距离口径（第七轮复核 S3-① 更正）**：初稿写「相隔 **133** 行」，★ **该值在【§18.2 实测块首行 → 本节待办 1】这一未申报口径下成立；按最自然口径（两处冲突行之间）实测为 122**（上轮件口径：`:2709`→`:2842` = 133；`:2720`→`:2842` = **122**）。★ 本处已删该数字，改为【以复跑命令取值】：`grep -n '积压' <本件> | head`。★ **并如实记**：该「133」**源自复核方第六轮报告的措辞**，起草人**忠实抄入** ⇒ **责任共担**（复核方上轮自陈：应写「§18.2 实测块首行起算」而非裸给 133）；见 §18.2 实测；**三选一**处置（指定临时值班者并清理 / 按收件人存活状态过滤 / 明确宣告链停用并留痕）—— **属主：HR / 协调者** |
| 2 | ★ **xdom 身份问题** | 见 §18.3 待裁两条路。★ **球权值不在此写死**（它是**派生量**，由日志最后一条的 `ball` 派生 ⇒ **会变**）—— ★ **以复跑取值**：`python3 tools/xdom-mail.py status` |
| 3 | ★ **「卡→自动唤起会话」未登记** | `dsh-plugin-central-inbox` **至今不在任何登记表** ⇒ ★ **启动 MCP P0 前须先补登记** |
| 4 | ★ **§18.3「勿再引用旧说法」清单不完整**（外部复核 S2-9） | ★ **缺第三处**：`log/` 的「**永不修改**」**非 enforced** —— `tools/xdom-mail.py:624` 的 **DELETE 路径无 `owns_key`**。★ 口径声明：该事实确立于 03:09:48，**不判为收编失真**，判为「清单不完整」 |
| 5 | ★ **源件编号缺陷回报**（外部复核 S2-6） | `docs/CCEP-continuity-protocol-v1.md:13–14` 有**两个「4.」**（沙箱先行 / 可回滚）⇒ ★ **建议源件属主更正**（本节 §18.1 已按语义重排并补更正注） |

---

*本文件为锚点基线 **v6.1**，`state_version = 6`。起草：星桥第二任 `session-e317d6ab`。**本件成立与否不由起草人裁定**，待第三方 verifier。*
