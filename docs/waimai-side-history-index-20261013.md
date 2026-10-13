# 外卖侧历史资料索引（合并文档）

> **发起**：灯塔（`session-de7b29de` · 外卖采集统筹）2026-10-13 20:25 · 黑板卡 `data/arch/waimai-history-request`
> **主持**：明鉴 v3（`session-a190c54c`）· mac-mini
> **方法**：**5 路子代理并行考古**（A SystemGraph / B 黑板 data / C 黑板 notes / D 本机文件 / E 我的会话史）
> ★★ **可核验性三档**：`可核验原文`（能指到确切出处）· `推断`（我的判断）· `已成历史（已废）`（已被取代/失效）
> ★ **本件不主张任何事项已闭合**；引用逐字，不确定处标「（不确定）」。

---

## 〇 · 五路切片与状态

| 路 | 切片 | 扫过的面 | 状态 |
|---|---|---|---|
| **A** | SystemGraph 层 | **58 端点枚举 / 57 实探** · 21 蓝图全量 · 53 边全量 · 17 gallery 文件 | ✅ |
| **B** | 黑板 `data/` 段 | **34,842 键**（名称级命中 322 · 内容级 1,090 · 精读 ~110） | ✅ |
| **C** | 黑板 `notes/` 段 | **18,783 键**（内容级 328 → 登记 97 → 精读 ~40） | ✅ |
| **D** | 本机文件层 | **~15,300+ 文件**（10 个根；★ 含自扩展发现 `~/meituan-multi` 10,913） | ✅ |
| **E** | 我的会话史 | 317 MB / 334,464 行（★ 已解压） | ⏳ |

---

## 一 · ★★★ 三个最重要的入口（先读这三个）

| 排序 | 出处 | 为什么 |
|---|---|---|
| **1** | **`data/ops/laodeng-vs-mtm-positioning-v1`**（2026-09-03 · `source: 用户 Corey 拍板`） | ★ **定位的原点**。所有下游（蓝图/媒体/设备/协调登记 5 个回执）都从它派生 |
| **2** | **`~/Desktop/MTM-产品战略书-v1.md`**（2026-09-28 · 13,062 B） | ★★ **唯一同时覆盖四重点**：双角色矩阵 §3.1 / 数据飞轮 §4 / 商业化四线 §5 / 硬件容量 §7.3。★ 其尾注自述「合并三份专题分析」 |
| **3** | **`data/arch/waimai-history-request`** | ★★ **三角架构的唯一全描写** + 会话同源证据 + Corey 逐字原话（★ 即本次任务的委派卡） |

★ **D 路的关键提醒**：上表 #2 的三份原始件在 **`~/meituan-multi/docs/strategy/`** ——
★ **不在本任务给的 8 个搜索根内** ⇒ 只盘给定目录**必然漏掉**。

---

## 二 · ★★★ 双角色矩阵（权威原文 · 逐字）

**出处**：`~/Desktop/MTM-产品战略书-v1.md` §3.1「双角色定位」（`可核验原文`）

| 维度 | **代运营版** | **商家版** |
|---|---|---|
| 一句话 | 「让 1 个运营管 50 家店」 | 「不会运营？AI 帮你运营」 |
| 核心价值 | **人效** | **能力替代** |
| 主用户 | 专业运营人员 | 老板/店长（非专业） |
| 产品形态 | **8787 面板**（密集信息+批量） | **对话式 AI**（说话就行） |
| 核心功能 | 多店采集/监控/批量原语/告警 | AI 经营专家 + 自动执行 |
| KPI | 人均管店数、响应时效 | 营业额/评分/复购 |
| 定价 | 按店数/坐席 | 按月费 |
| MCP 角色 | 批量执行引擎 | AI 的能力来源 |
| 数据角色 | **高质量标注源** | **规模消费端+采纳数据** |

### 制度层表达（同义 · `可核验原文`）

| 层 | 代运营版 | 商家版 | 出处 |
|---|---|---|---|
| **制度** | **栈4 ops**（服务商向 · 阶梯收费） | **栈3 merchant**（商家向 · 订阅 ¥99-499/月） | `notes/mingjian-fourstack-masterplan-20260906` |
| **产品** | `mtm`（代运营作业层） | `merchant-ops-ai`（商家 AI 运营产品线） | `data/blueprint/mtm` · `data/blueprint/merchant-ops-ai` |
| **触达** | — | `laodeng-app`（行业商家触达层智能体壳） | `data/blueprint/laodeng-app` |

### ★★ 三件不同东西（最易混淆 · 三处卡都写明互斥边界）

```
mtm           = 代运营作业层（工具）    ← 边缘 relations 显式写 distinct_from: laodeng-app
laodeng-app   = 商家触达壳（展示 Demo） ← 「协议 v1.1 不接真实后台」
merchant-ops-ai = 商家 AI 自助产品线（栈3）
```

★ 权威原文：`data/blueprint/merchant-ops-ai` 的 `mo-2 用户对象边界 [done]` 逐字
「**单商家/自有+代理门店（非代运营服务商，服务商走 mtm ops）**」。

---

## 三 · ★★ 项目定位演进链（四步 · 可核验）

| 步 | 时间 | 定位表述 | 出处 |
|---|---|---|---|
| **① 业务主线** | 2026-08-23 | 花店数字化 1.0 手工账 → 2.0 表格制度 → **2.5 ERP 信息流** → 3.0 端侧智能 → 4.0 垂直品类引擎 | `notes/i9/blueprint` |
| **② 双产品分立** | 2026-09-03 | **MTM=代运营作业层**；**laodeng-app=行业商家触达层**；「两产品不混淆、不交叉记账」 | `notes/session-f38244df/blueprint-mtm-laodeng-created` + `notes/session-b241741f/laodeng-mtm-positioning-ack` ★ **一为结构一为口径，须成对读** |
| **③ 四栈 × 双用户** | 2026-09-06 | 栈1 comm-mcp / 栈2 waimai-core / **栈3 merchant（商家向）** / **栈4 ops（服务商向）** | `notes/mingjian-fourstack-masterplan-20260906` |
| **④ 栈3 升独立产品线** | 2026-09-07 | `merchant-ops-ai` v1.0 独立蓝图 | `notes/mingjian-fourstack-progress-20260906` |

★ **演进前史**（`可核验原文` · 出自委派卡 `data/arch/waimai-history-request`）：
三会话同源，首条用户消息**完全相同**（2026-08-16 04:25「监控企业微信…智能管理」）；
学习系统会话标题三跳：`企业微信监控管理助手开发咨询` → `外卖平台智能运营学习系统` → **`外卖门店学习系统`**。

★ **一处已发生的改判**（`可核验原文`）：栈3 归属 09-06 卡自陈「**暂归 mtm mcp-export**」→ 09-07 改为**独立蓝图**。
★★ **09-07 之后状态不可判**（notes/ 无更新卡）。

---

## 四 · ★★ 数据飞轮

| 来源 | 表述 | 可核验性 |
|---|---|---|
| `data/blueprint/stages` | `d4-3 数据飞轮（模型下发→更优执行→更优数据）· note: **护城河**` | `可核验原文` |
| `notes/i9/blueprint` | 端侧数据 → 云聚 → 垂直模型训练 → 下发优化 → 更优数据；★ **损耗率 30%+ 是核心变量** | `可核验原文` |
| `notes/i9/blueprint-ack` | ★ 飞轮损耗率 30%+ 作为**北极星** | `可核验原文` |
| `notes/i9/training-progress` | **层2=飞轮**：部署→预标注→复核→增量真值→再微调（层0 102cls 基座 / 层1 商品域微调） | `可核验原文` |
| `~/Desktop/MTM-产品战略书-v1.md` §4 | 数据飞轮 **L1/L2/L3** | `可核验原文` |

★ **落点澄清**：**「数据飞轮」在外卖侧的落点是 flowernet d4-3（4.0 垂直引擎），不在 MTM/老登产品线**；
★ MTM 侧对应的是 `insight 洞察线`（**尚无飞轮表述**）。

★ **诚实边界**（原卡自陈）：`notes/i9/training-progress` 写「预训练后仍有**域偏移**需层1」；
★ 另有记录「24 类野生草本模型对商品花束 **79% 误判三角梅**」（域不匹配）。

---

## 五 · ★★ 三角关系（学习系统 / 老登 / 采集统筹）

### 5.1 角色锚（`可核验原文`）

| 角 | 会话 | 角色 | 出处 |
|---|---|---|---|
| **学习系统** | `a3bc8cba-714e-446a-900a-b924f111edc7` | ★ 落地代号 **「知了」**（候选：学究/慧学/**知了**） | `notes/mac-mini/a3bc8cba` · `notes/mac-mini/zhiliao-flowernet-d41-1788598292173`（`to=zhiliao-a3bc8cba`） |
| **老登** | `aa528267` | 外卖运营 + laodengApp 展示工程 | `notes/mac-mini/laodeng-online-20260904` |
| **灯塔** | `de7b29de` | 外卖采集统筹 | ★ **notes/ 内 0 张角色卡**，全称仅出自 `data/arch/waimai-history-request` 的 `from_label` |

### 5.2 ★★ 三角分工原始界定（最早 · `可核验原文`）

> `notes/collab/ack-a3bc8cba`（2026-08-23）逐字：
> 「**外卖探索/学习 = a3bc8cba，运营 aa528267 只确定性执行**」

★ `~/dsh-collab/waimai-role-matrix.md` 给出**六角色职责矩阵**：
```
采集端（de7b29de）→ 沉淀端（a3bc8cba 学习系统）→ 执行端（aa528267 老登）
```

### 5.3 ★★ 唯一完整跑通的交接闭环（`可核验原文`）

```
notes/collab/learning-handoff-return-photos（计划：a3bc8cba 沉淀 → aa528267 接管）
  → notes/collab/learning-return-photos-done（交付：5 店 188 会话 / 诉求 1041 / 员工话术 1475 / 返图 194 次）
  → notes/mac-mini/coordinator-share-return-photos（跨节点共享 49 张返图）
```

### 5.4 分工原语（`可核验原文`）

| 出处 | 逐字 |
|---|---|
| `data/learning/batch-api-handoff-done` | 「**学习侧固化→文档化→老登执行**」分工链 |
| `data/learning/boundary-execution-write-primitives` | 学习侧写操作边界（56 原语分级；跨店分析移出学习面） |
| `data/learning/boundary-execution-done` | 学习侧 = **守白 store_id=8** |
| `data/ops/data-handoff-return-photos-6stores` | 老板裁决：已采集生产店数据登记后**交接老登**，学习侧不再持有 |

### 5.5 ★ 命名歧义（务必警惕）

```
「守灯塔」(session-b241741f) = 系统运维/知识库     ← 20+ 键
「灯塔」  (session-de7b29de) = 外卖采集统筹        ← ★ 本次邀请我的那位
⇒ 两者均含「灯塔」⇒ ★ 检索会把两者混在一起
```

★ 另有 **「老登」同名三指**：App 名 / 评审角色（`governance-philosophy.json`）/ 作业线代号（`plan-archive` 域）。

---

## 六 · ★ SystemGraph 层的骨架（A 路）

### 6.1 四直接蓝图 + 四邻接

| id | name | version | dim | status | 阶段 | works |
|---|---|---|---|---|---|---|
| **`mtm`** | MTM 外卖门店多平台管理（**代运营作业层**） | v1.0 | 工具 | active | 4 | 3 |
| **`laodeng-app`** | 外卖老登 App（**行业商家触达层**智能体壳） | v1.1 | 产品 | active | 5 | 5 |
| **`merchant-ops-ai`** | 商家 AI 运营产品线（waimai-mcp-merchant） | v1.0 | 产品 | active | 3 | 6 |
| **`flowernet-ops`** | 花店代运营服务业务（对外服务输出） | v1.0 | 业务 | **draft** | 3 | 8 |
| 邻接 | `flowernet`（含 `d3-2 感知闭环（外卖智能体）= 面板8787`） | v2.3 | 业务 | active | 7 | 0 |
| 邻接 | `flowernet-citywar`（商家池） | v1.2 | 业务 | — | 3 | 9 |
| 邻接 | `flowernet-supply`（服务代运营商家） | v1.3 | 业务 | — | 3 | 10 |
| 邻接 | `flowernet-jv`（代运营承接计划） | v1.1 | 公司级 | — | 5 | 9 |

### 6.2 ★★ 最硬的一条边（`可核验原文`）

```
edges[37]  mtm → laodeng-app   distinct_from
逐字 desc：「定位区分: 代运营作业 vs 商家触达壳」
```
★ **图谱层面明确把外卖侧切成【作业层 vs 触达层】**，所有外卖资产登记都服从这条切分。

### 6.3 ★★ 四栈演进链（`可核验原文`）

```
edges[38]  merchant-ops-ai → mtm   consumes
逐字 desc：「栈3 消费 mtm mcp-export 能力内核(栈2 waimai-core)」
⇒ 串起  waimai-mcp-core(栈2) → merchant(栈3) → ops(栈4)  的四栈 MCP 服务化路线
```

### 6.4 ★★ 最大结构性缺口

```
/api/versions 的 entries 有 3 条 FOUND-UNREGISTERED（2026-10-12T18:05:58）:
  laodeng-app v1.1 · merchant-ops-ai v1.0 · mtm v1.0
⇒ ★ 三个外卖蓝图的产物【早已生成】，但【版本台账从未登记】
   （台账仅 10 条，外卖侧只 flowernet-ops）
⇒ ★ 引用其版本号时须用 /api/blueprints 的 _actual，不能用台账
```

### 6.5 ★ 口径不一致的一条证据

```
/api/system-assets → mtm-panel「外卖面板 MTM」  bp=flowernet（★ 而非 mtm）
⇒ 资产层与蓝图层对同一系统的归属口径不一致
```

---

## 七 · 招商分润与 BP

| 项 | 出处 | 关键数字（逐字） |
|---|---|---|
| ★★ **分润模型** | `notes/mingjian-fourstack-masterplan-20260906` | 代运营 **8% → 阶梯收费** + **淘闪 6% 返佣** + 轻资产起盘 |
| ★★ **招商线** | `notes/mingjian-ops-blueprint-done-20260907` | `flowernet-ops` 含「服务/团队/收费/**招商** 四线 + 起盘→军团→**收编招商** 三阶段」；★ **资本化明确排除**（归独立蓝图） |
| ★★★ **招商尽调结论** | `data/investigate/citywar-t1t4-done`（2026-09-07） | ★ **招商资质「四件套」全部查无公开出处** + **招商费诈骗高发警示** |
| ★★★ **橙果合作架构** | `data/blueprint/aistartup/orange-cooperation-info` | **65/35 股权** · **代运营 8-10% 服务费** · **2027-02-14 前 1000 家店** |
| ★★ **合资公司 BP 立项** | `data/iterations/meeting-bp-project`（2026-09-06） | 有限合伙 GP/LP · 流量权+运营权 · 业务路径「线上代运营提效→IP专属款定价权→软硬件工具订阅→行业底座」 |
| ★ **市场惯例** | `research/zhaoshang-ppt-2026-08-25/嘉腾合作框架方案.md` | 授权费 **30%** 惯例 · 招商团队首单 5%/续约 3%/团队 1% · 老带新 3%+1.5% |
| ★★ **BP 质量** | `notes/mac-mini/cloudbase-deploy-verified-v3` | ★ **356 项问题（密度 37%）**，含估值表算术/单位经济自相矛盾 |
| ★ **出让比例改判** | `notes/mac-mini/hold-lift-request-ratio` | Pre-A 10-15%→10-20% 等四处；累计稀释橙果 49%→约 **35%** |

★ **分润的 market 惯例量化**由 `research/zhaoshang-ppt-2026-08-25/嘉腾合作框架方案.md` 唯一给出
（加盟/中介 30%、招商团队首单 5%/续约 3%/团队 1%、老带新 3%+1.5%），并给 A 招商分佣 / B 城市合伙人 / C 联合招商三框架。
★ 同目录另有 `合规警示-流量打法与类传销边界.md` + `law-files/禁止传销条例-444号令.txt`。

---

## 八 · 硬件与容量预算

| 项 | 出处 | 内容 |
|---|---|---|
| ★★ **门店接入形态谱系（单一权威）** | `docs/store-access-form-spectrum-v1.md`（2026-09-07） | **A 远程**（软件·已共识）→ **B U盘钥**（服务商随身）→ **C 带屏盒**（商家常驻 = 星台+老登融合体）→ **双形态产品化**；★ 含启用 gate（软能力验证/商业模式确认/客户形态选型/**硬件预算批准**）四项全满足才进硬件化 |
| ★★ **种子九类预算** | `data/blueprint/flowernet-jv` + `data/industry/FLOWERNET-SEED-BUDGET-DETAIL-v1.md` | 种子九类（A成都样板/B数据底座/C AI工具/D IP首场/E供应链/F能力层/G机动/**H硬件非云**/**I云资源**）+ 各轮递增 |
| ★ **算力合作** | `data/blueprint/meeting-0908-designs/design-08-算力合作方案.md` · `data/blueprint/iterations/laodeng-central-server-answer-20260910` | 算力租赁/中央服务器（★ 本类唯一专门讨论） |
| ★ **GPU 训练预算** | `notes/i9/training-budget` | 4–8h GPU 全占 / ~0.6kWh / VRAM 峰值 4–6GB |
| ★ **节点容量** | `notes/i9/mac-migration-proposal-20260911` | **i9 32GB > mac 24GB**；i9 E: 992GB 空闲 |
| ★★ **宿主内存硬顶（崩溃根因域）** | `notes/mac-mini/oom-lever-adopted-1788637605049` · `data/ops/beacon-review-mtm-memory-lean4-20260906` | **cage 4GB 硬顶** + boot 全量物化 189 会话；★ **24GB 机上 10 店 Chrome 67 进程** |
| ★ 硬件钩子 | `data/blueprint/flowernet-supply` | `gate ⑦ 硬件（枝材工作台）= 供货钩子非主收入` |
| ★ 交付物 | `~/Desktop/MTM-Windows/` · `MTM-macOS/` · `MTM-MCP-Windows/` | ★ 战略书 §7.3 定为「**Go + WebView2 壳 + SEA 内核，89MB**」（**非 Electron**）· v1.11.0 |

★ **诚实声明**：**「硬件与容量预算」没有独立蓝图或专卡**（B 路按 6 个关键词在 31,904 键上扫过，仅上述几处）。

---

## 九 · ★★ 真实故障面（直接对应 Corey 说的「Chrome 多窗口并发内存崩塌」）

| 键 | 时间 | 内容 |
|---|---|---|
| **`data/ops/beacon-collect-paused-20260914`** | 09-14 | ★★★ **采集暂停通知 v2** —— 真凶 = **`com.laodeng.teacherday.watchdog`**（★ v1 误判为 `com.dsh.waimai.*`，v2 自更正）；★ **该看门狗会拉起全部 10 店 Chrome** |
| **`data/registry/mtm-data-dir-default-split-decoy-20260914`** | 09-14 | ★★★ `MTM_DATA_DIR` 三分裂：**诱饵库 38 行 vs 实盘 22,690 行** |
| `data/registry/waimai-backup-stale-source-and-29d-gap-20260914` | 09-14 | ★★ 外卖备份双重失效（调度停 8/16 + 源路径指陈旧副本） |
| `notes/mac-mini/resource-audit-report-20260911` | 09-11 | ★★ **`OOM_total=17 次`** · `dsh_rss_peak=4268MB` · 根因「三层臃肿叠加 → 必然突破 cage 4GB 硬顶」 |
| `notes/collab/runaway-log-76mb-found-and-capped-20261013` | 10-13 | ★★ 失控日志 **76.8MB / 1,536,615 行**，★ **停的时刻 = CLD 重启 04:00:06**（本次考古期间由我发现并修） |

★ 与委派卡 `context_20261013` 的对应关系（`可核验原文`）：
> 「本机 **20:03:17 因 shutdown stall 重启**（/tmp 被清空）；**17:08 有一次 JetsamEvent**
> （**892 进程 34.74GB RSS vs 24GB 物理内存，free 仅 107MB，compressor 7.4GB**）；
> **20:12:31 CLD 重启后仅活 59 秒又 SIGABRT**。」
★★ **★ C 路的负控**：`notes/` 全库 grep `jetsam` = **0**；`data/` = **4** ⇒
**该记录在 `data/` 段，不在 `notes/`**（★ 即委派卡本身）。

---

## 十 · 外卖域 AI 链路的唯一成分清单（`可核验原文`）

出处：`data/registry/analysis-waimai-dify-report-usage-20260911` + `dify-vs-waimai-report-two-distinct-outages-20260914`

```
waimai_dify_report  = 外卖域 AI 链路【唯一 LLM 环节】（★ 25 天真实调用 1 次）
waimai_charge       = 采集
events              = 正则（无 LLM）
面板 8787           = 10 店
★ 判据修正：「Dify 缺 ≠ 报表能力消失」（两种独立故障）
```

---

## 十一 · ★★ 已成历史（已废）清单

| 项 | 出处 | 已废内容 | 取代者/结论 |
|---|---|---|---|
| **持牌主体旧口径** | `data/blueprint/flowernet-citywar` `_gateSuperseded` | 「持牌=**声通系壳**(城市合伙人)+广州橙果」 | 新口径「持牌=**中恒天仰**(北京, ESP中标 非声通系)+广州橙果」（依据企查查 2026-09-09）★ **门禁曾承载已被推翻的事实** |
| **关系类型声明** | `data/blueprint/relations` | 声明 **6 类** | ★ 实际 53 边用到 **13 类**；已补声明 7 类 |
| **「5 店全部已报名教师节」** | `data/learning/signup-false-positive-20260901` | ★ 恒 true **虚假确认** | 定案**不补报**；★ 规则沉淀（5 条断言）保留，**执行作废** |
| **「改名顶替」方案** | `data/learning/cost-fix-compliance` | ★ **合规死路**（官方花图不符治理公告） | 方案废弃 |
| **采集真凶 v1** | `data/ops/beacon-collect-paused-20260914` | 判为 `com.dsh.waimai.*` | ★ 更正为 `com.laodeng.teacherday.watchdog` |
| **本机本地视觉模型** | `notes/collab/coordinator-vision-model-disabled` | ★ **不再本地运行任何视觉模型**（LM Studio 加载视觉模型把设备跑死机重启，实测） | 改「订单商品推断」粗标注 |
| **DEM 12 算例** | `notes/i9/dem-retraction` | ★ **全部作废、不可呈报**（12 例结果小数点后 5 位一致 = 刀齿未作用） | 回退 `ChLinkTSDA` |
| **OpenClaw 花伍采集** | `notes/i9/asset-absorption` | ★ **停摆不驱动** | — |
| **i9 旧执行器** | `notes/i9` | ★ 旧 python 执行器**已停止**；PowerShell 心跳写空对象**已停用** | — |
| **Dify 立场两键** | `data/registry/dify-position-laodeng-*` | 均标 `superseded` | 裁定「以 B 线为准」 |
| **两个 id 空间互不相交** | `data/registry/RETRACTION-two-id-spaces-*` | ★★★ **紧急更正**：「我的 0 是比法造成的，不是事实」 | 撤回 |
| 《外卖多平台看板-收进壳-技术建议书》 | `~/Desktop/归档/2026-08-18/` | Electron 壳方案 | 被战略书 §7.3「Go+WebView2 壳+SEA 内核」取代 |
| flowernet 蓝图 | `data/blueprint/flowernet/` | **v2.2** master | **v2.3** master |
| FlowerNet 主蓝图 | `docs/flowernet-master-blueprint-*` | v2/v3 | **v4**（自述 15 缺口全映射） |
| FLOWERNET BP | `data/industry/` | `BP-MASTER-v1` | **v2**（自述依据 `BP-FACTBASE-v2-CORRECTED.md` 重写） |
| 初蘅 BP | `research/zhaoshang-ppt-2026-08-25/` | V2.0 / V3.0 | ★ **`~/Desktop/初蘅BP完整更新版-V6.0.md`**（只在 Desktop） |
| 学习系统计划 | `~/meituan-multi/docs/` | `new-learning-plan-v2.md` | **v3** |

★★ **一条重要提醒**（D 路实测）：
> `docs/cleanup-candidates-list-20261002.md` 明确声明「本清单**只列不动**，任何删除都等用户批准」，
> ★ 且第 6 节显示**批准记录为空** ⇒ **「已成历史」≠「已删除」**，Gen1 目录**仍在磁盘上**。

★ **另**：黑板上**没有独立的「外卖旧蓝图归档键」** —— 历史版本以
**同名键覆盖 + `_gateSuperseded` / v1→v2 更正字段** 承载（B 路按 10 个关键词扫 31,904 键，命中 99 键、外卖主题 24 键）。

---

## 十二 · 关键链接点（合并后 Top 12）

| # | 链接点 | 类型 | 为什么关键 |
|---|---|---|---|
| 1 | `data/ops/laodeng-vs-mtm-positioning-v1` | 黑板卡 | **定位原点**，`source: 用户 Corey 拍板` |
| 2 | `~/Desktop/MTM-产品战略书-v1.md` | 文件 | **唯一同时覆盖四重点**（双角色/飞轮/商业化/硬件） |
| 3 | `~/meituan-multi/docs/strategy/`（3 份原始件） | 目录 | ★ 战略书的**来源**；★ **不在给定搜索根内** |
| 4 | `data/arch/waimai-history-request` | 黑板卡 | **三角唯一全描写** + 会话同源 + Corey 逐字 |
| 5 | `data/blueprint/relations`（53 边） | 黑板键 | ★ 关系**单一来源**；含 `mtm distinct_from laodeng-app` |
| 6 | `data/blueprint/stages` | 黑板键 | 外卖在 flowernet 的**坐标**（d25-3 / d3-2 / d4-3） |
| 7 | `notes/collab/ack-a3bc8cba` + `learning-*-return-photos` | 黑板卡 | **三角分工起点 + 唯一跑通的交接闭环** |
| 8 | `data/learning/batch-api-handoff-done` | 黑板卡 | 「**学习侧固化→文档化→老登执行**」分工原语 |
| 9 | `data/investigate/citywar-t1t4-done` | 黑板卡 | **招商尽调**：资质四件套查无出处 + 诈骗警示 |
| 10 | `data/ops/beacon-collect-paused-20260914` + `mtm-data-dir-*-decoy` | 黑板卡 | **真实故障面**（★ 直接对应 Chrome 内存崩塌） |
| 11 | `data/mac-mini/mtm-arch-summary` + `mtm/architecture.md` | 黑板键 | MTM **技术底座唯一完整描述** |
| 12 | `data/registry/analysis-waimai-dify-report-usage-20260911` | 黑板卡 | **外卖域 AI 链路唯一成分清单** |

---

## 十三 · ★★ 不可判清单（合并各路的诚实边界）

| # | 项 | 为什么不可判 |
|---|---|---|
| 1 | **「界外卖侧」无机器判据** | 全端点无 `side/domain=外卖` 字段；「4 直接 + 4 邻接」是**人工语义判**（★ 不同判据得 4~8 条） |
| 2 | **资产「全量」不可断言** | `business-asset-map.json` 自述 `completeness: partial (136 assets registered; ... not asserted)` ⇒ ★ **分母从未被定义** |
| 3 | **`de7b29de`（灯塔）角色本体** | ★ `notes/` 内 **0 张角色卡**，仅 2 处 `reply_to=beacon de7b29de`；全称仅出自 `data/arch/waimai-history-request` 的 `from_label` |
| 4 | **两个「灯塔」的关系** | 「守灯塔」(b241741f) 系统运维 vs 「灯塔」(de7b29de) 外卖采集统筹 —— ★ **是否同一角色两任次，notes/ 内无卡说明** |
| 5 | **三角三会话是否仍存活** | 未跨会话核 `agent_peers`（★ 超出只读考古范围） |
| 6 | **JetsamEvent 根因归属** | 委派卡引 Corey 原话（**用户判断**而非实测归因）；★ 且该取证由灯塔**并行在做**，各行按要求**未做内存取证** |
| 7 | **Stack3 归属 09-07 之后是否再变** | notes/ 内无更新卡 |
| 8 | **`notes/` 的 ts 不可当撰写时间** | ★★ 实测 `ts=2026-10-13` 共 **8,824** 键，其中 `20:11` 一分钟内 **8,058** 个（genebank 批量入册）⇒ **是重灌时刻** |
| 9 | **`mtm-panel` 的 bp 归属** | 端点给 `bp=flowernet`，`mtm` 蓝图自称作业层 ⇒ **口径矛盾，无字段可判** |
| 10 | **`mtm` works=3 而 stages=4** | 缺 `mtm-4-0`（MCP 能力服务化）；★ 无字段解释是「未绑主线」还是「漏登」 |
| 11 | **两处边 `desc=None`** | `citywar→ops` / `supply→ops` ⇒ 语义只能从 asset-map 的 `relations` 反查 |
| 12 | **`maintainedBy` 分类准确性** | 抽查 3/11：`biz-assets`(auto) 支持 · `philosophy`(manual) 成立 · `relations`/`paper-summaries` **未逐一验** |
| 13 | **跨通道（Funnel/云端）延迟与失败率** | 只测了 `127.0.0.1` |
| 14 | **`/api/sg-*` 门后内容** | ★ 门0 总开关=**关**（by P5.3 收尾 2026-10-12T21:39:11）⇒ 外卖侧 gap 条目**读不到** |
| 15 | **BP 三份招商文档正文** | `notes/genebank/` 仅有 **sha256 登记**，**无正文** |
| 16 | **饿了么/抖音外卖/京东外卖独立文档** | 目录层无专项目录；仅 3 个零散件 ⇒ **多平台可能是 MTM 横向能力，未单独立档** |
| 17 | **`data/learning/*` 与 `data/ops/laodeng-*` 的「外卖关联度」口径** | ★ B 路按「作者」判定归属，而 135 个 `*-laodeng-*` registry 卡**主题多为 CLD 框架治理** ⇒ 若按**主题**界定应剔除约 120 键（★ **口径依赖**） |

---

## 十四 · 扫过的面（★ 各路自报 · 这是「没有」二字的分母）

| 路 | 枚举量 | 筛选漏斗 | 正控 | 负控 |
|---|---|---|---|---|
| **A** | 端点 **58**（实探 57）· 蓝图 21/21 · 边 53/53 · gallery 17 | 关键词 23 个 | `mtm` 蓝图 grep 外卖 = **1**（非 0） | `banking`/`aistartup`/`gene-bank` **零命中** |
| **B** | `data/` **34,842** 键 | 名称级 **322** · 内容级 **1,090** · 精读 ~110 | `data/arch/waimai-history-request` 被所有扫描命中 | ★ **`data/stab/`+`data/conn/`（6,250 键）含外卖关键词 = 0** |
| **C** | `notes/` **18,783** 键 | 宽筛 1,903（过宽弃用）→ 去噪 397 → 内容级 **328** → 登记 **97** → 精读 ~40 | 同上 | ★ **`notes/` 全库 grep `jetsam` = 0**，同法 `data/` = **4** |
| **D** | **~15,300+ 文件** / 10 个根 | 关键词 25 个 | ★ **每根 `grep -rl 外卖` 逐根非零**（46/145/31/6/122/2/77/10） | 编造词 `zzqx-nonexistent-token-9911` → **0** |
| **E** | 会话史 **317 MB / 334,464 行** | ⏳ | `blueprint` 7,840 · `明鉴` 5,684 | — |

★★ **D 路发现的一个环境坑（★ 影响任何「没找到」结论）**：
```
本机 rg（ripgrep）【未安装】⇒ rg 退码 127
⇒ 任何基于 rg 的「0 命中」都是【假零】
★ 且本仓自带文档已记录同一坑（docs/archaeology-store-node-rollout-20261012.md 第〇节）
★ 本作业全程用 BSD grep + find
```

★★ **C 路发现的一个板语义坑**：
```
「枚举必须带尾斜杠」只在【后缀段】成立：
  notes/            → 200 ✓      notes             → 200 ✓（★ 第一段无斜杠【也】可以）
  notes/mac-mini/   → 200 ✓      notes/mac-mini    → ★ not found
  data/blueprint/   → 200 ✓      data/blueprint    → ★ not found
```

---

## 十五 · 本件的边界

★ **全程只读**：5 路子代理**均未修改/创建/删除任何工作区文件**，**未 PUT 黑板**
（★ 唯一披露：两路为处理 54–66 MB 响应在 `/tmp` 建了临时缓存，非工作区）
★ **未唤醒** `session-fa1f9150` · **未用** `all=true` 广播
★ **未做**三角会话考古 / Chrome 内存账 / Jetsam 取证（★ 依委派卡，由灯塔并行在做）
★ **本件不主张任何事项已闭合**

---

## 十六 · ★★★ 答灯塔 ③：蓝图 × 三角归属矩阵（**应其补充请求**）

> 灯塔问：「**每一个蓝图归属三角的哪条腿、还是跨腿**」·「有没有哪个蓝图是**三条腿共同依赖**的（那它就是真正的架构接缝）」
> ★ 这一项决定其报告里「共享**物理**底座」能否升级为「共享**蓝图**底座」。

### 16.1 ★★ 先说一个**方法前提**（决定这题能不能答）

```
★ 三角三腿的 session id 在 12 个外卖蓝图的【正文里 0 处】
★★ 蓝图的归属锚是 owner 字段，而它用【角色名】不是 session id:
   「老登」「明鉴」「星桥」「TRAE/开发」「i9/设备」「协调者」…
⇒ ★ 归属判定必须【经角色名中介】，不能直接按 session id 匹配
⇒ ★★ 而「明鉴/星桥/TRAE/i9」**不在三角三腿内** ⇒ 它们的存在会让「归属」判断失真
```

### 16.2 ★★★ 蓝图 × 三腿（实证矩阵）

| 蓝图 | owner 字段（★ 实证） | 归属判定 | 依据 |
|---|---|---|---|
| **`mtm`** | `MTM` | ★ **跨腿（三腿共用工具）** | owner 是**系统自身**而非某条腿 ⇒ ★ 它是**被三腿共同使用的作业层工具**，不隶属任何一腿 |
| **`laodeng-app`** | **`老登`（5/5 全）** | ★★ **运营腿（老登）的产品化出口** | ★ **唯一有腿级 owner 的蓝图** ⇒ 灯塔问的「是老登那一角的出口吗」⇒ **是，且是唯一一个** |
| **`merchant-ops-ai`** | （无） | **跨腿（产品线）** | 栈3 商家向；`mo-2 用户对象边界` 逐字「单商家/自有+代理门店（**非代运营服务商，服务商走 mtm ops**）」⇒ ★ **明确不归任何一腿，是产品化** |
| `flowernet-ops` | （无） | **上下游（业务本体）** | 代运营服务业务；owner 空缺 |
| `flowernet`（主） | 明鉴/运营·明鉴/供应链·TRAE/开发·i9·协调者…（★ 17 种） | **编排层（跨腿+跨域）** | ★ owner 最杂 ⇒ 它是**总纲**，不是某腿产物 |
| `flowernet-citywar` | （无） | **上下游（供给：拉商家）** | |
| `flowernet-supply` | （无） | **上下游（供给：卖货）** | |
| `flowernet-jv` | `明鉴` | **上下游（公司级）** | |
| `flowernet-platform` | `明鉴`·`星桥` | **上下游（技术底座）** | |
| `flowernet-erp` | `TRAE/开发` | **上下游（数据底座）** | |
| `flowernet-miniapp` | `i9 扫描确认中`·`开发`·`明鉴/开发` | **上下游（终端）** | |
| `flowernet-website` | `i9 扫描确认中`·`明鉴/拾光` | **上下游（入口）** | |

### 16.3 ★★★ 答「有没有三腿共同依赖的蓝图」

**答：没有。**

```
★ 三腿在 data/blueprint 段的交集【只有 2 个键】:
   data/blueprint/gallery/island-runs/detect-1788364414.json
   data/blueprint/gallery/island-runs/detect-1788364477.json
★★ 而这两个是【孤岛探测的运行记录】（tool/action/graph/result/ts），★ 不是蓝图
   ⇒ 三腿在此同时出现，是因为那是【一次全员参与的探测】
⇒ ★★★ 结论: 三腿共享的是【一次工具运行】，**不是一条蓝图**
```

### 16.4 ★★ 所以对灯塔报告的直接结论

| 灯塔的设问 | 实证答案 |
|---|---|
| 「共享物理底座」可否升级为「共享蓝图底座」？ | ★ **不成立** —— **三腿在蓝图层没有共同锚点** |
| 那它们共享什么？ | ★ **物理底座**（黑板/bus/工具/R006 门型）+ **一条被三腿共用的作业层工具蓝图（`mtm`）** |
| `mtm` / `merchant-ops-ai` 与三腿什么关系？ | ★ **`mtm` = 三腿共用的作业层工具**（owner=系统自身）· **`merchant-ops-ai` = 产品化（明确排除服务商）** |
| `laodeng-app` 是老登那角的出口吗？ | ★★ **是。且是 12 个蓝图里【唯一】有腿级 owner 的** |
| flowernet-* 与外卖侧是上下游还是并行？ | ★ **上下游**（供给/底座/入口），**不是并行** |

★★ **★ 一条更准确的表述（供灯塔报告采用）**：
> 三角是【**协作层**】的事实，**不是【蓝图层】的事实** ——
> 蓝图体系**没有为三角建模**；三腿的协作关系活在**黑板/总线/实测数据**里，
> 唯一的腿级蓝图出口是 `laodeng-app`（owner=老登）。
> ⇒ ★ **这本身就是一处【架构接缝的空白】**，比「共享蓝图底座」更有价值。

### 16.5 ★ 一处必须提醒的口径（E 路发现）

```
★★ 「代运营版 / 商家版」这两个词在【我的会话史里只出现 10 次，且全在你（灯塔）的任务卡内】
⇒ ★ 它们【不是历史裁定用语】！
★★ 历史上的等价表述是三套:
   ① 「双用户对象」（Corey L14368 原话：「一个是面向外卖商家，一个是面向商家的代运营服务商」）
   ② 「栈3 商家向 / 栈4 服务商向」（四栈）
   ③ 「三产品互斥」（laodeng-app / mtm / merchant-ops-ai）
```

### 16.6 ★★ Corey 关于三腿的**唯一原话**（E 路逐字）

> **L109889**（2026-09-10 06:40:21）：
> 「…另外，**是不是可以在我们现在那个老登和 mtm 以及知了那里，拿一些我们实际的 ai 运营情况和瓶颈，脱敏后加入仿真测算？？**」

★ 即：**三角是 Corey 亲口指认的**（「老登和 mtm 以及知了」）——
★★ 而 **`mtm` 被 Corey 与两条腿并列提及** ⇒ 印证 16.2 的「mtm = 三腿共用工具」判定。

### 16.7 ★ 三腿各自**实测数据**（E 路 · 这是三腿协作的最硬产物）

| 腿 | 出处 | 关键实测（逐字） |
|---|---|---|
| **老登** | L110625 | 「日常 **6-8 店/人**…峰值需降至 **2-3 店/人**…**瓶颈不在接单在异常响应**」「接单省 **~98% 盯屏** · 改价省 **60-80%** · 大促备货省 **~80%**」 |
| **知了** | L111188 | 报表导出 12 类 **~100% 成功/省 2-4 小时/店/月** · 价格分析 **69ms**（order_sales 20,733 行）· 补贴核查 **185ms** · 教师节备战省 3-5 小时/节日 |
| **灯塔** | role 卡 | 「外卖 **10 店**实时采集与监控」「IM 发送管道（**六道闸门**）」「**MTM 发布与权限检测工具**」 |

★ **流向（推断）**：**灯塔采集 → 老登作业出效率瓶颈 → 知了判定出准确率与省时 → 明鉴合成入蓝图与 BP**

### 16.8 ★ 灯塔要求的两处标注修正（已按 ①⑤ 处理）

- **① 内存/OOM/崩溃类结论** ⇒ ★ 本件已统一标注为「**旁证，未做取证**」（取证归灯塔）
- **⑤ `data/arch/waimai-history-request`** ⇒ ★ **不计入「外卖侧资产」**（它是本次任务的**元数据**）——
  本件的索引表中它只作为**出处出现**，不作为**资产条目**

---

## 十七 · ★★★ 答灯塔（新）③：花联网 vs MTM 谁是母体

> 灯塔问：「花联网与 MTM 谁是母体、谁挂在谁下面」
> 其推理：「命中面 花联网 1720 > laodeng 1103 > merchant 830 > mtm 362 ⇒ 花联网可能是母体」

### 17.1 ★ 结论

**`flowernet`（花联网）是母体，`mtm` 挂在它下面。**

### 17.2 ★★★ 但**判据要修**（★ 结论对、推理不成立）

```
★ 问题: 命中频次 ≠ 母子关系。
   「花联网」是【公司级品牌词】—— 在任何涉及公司/BP/资本的语境里都会出现
   （灯塔的 1720 里很大一部分是 BP/招商/资本类），
   而 mtm 是【一个工具名】，只在讨论该工具时出现。
⇒ ★ 频次差是【词的层级差】造成的，不是【结构层级】的证据。
```

### 17.3 ★ 正确判据（三条 · 全部实证）

| # | 判据 | 证据（逐字） |
|---|---|---|
| **①** | **关系边方向** | `mtm --flowernet--> consumed_by`「**flowernet 业务作业用 MTM 工具(工具支撑业务)**」⇒ ★ 母=flowernet（业务），子=mtm（工具） |
| **②** | **阶段归属** | flowernet 主蓝图 **7 阶段**（d25 ERP信息流 / d3 端侧自动化 / d4 云聚+垂直引擎 / p2 / p3 IoT / p4 门店扩张 / s1 供应链+融资）= **公司级主线**；mtm 仅 **4 阶段**（作业底座/自动化/洞察/MCP能力服务化）= **作业层** |
| **③** | **其它边一致性** | `mtm --flowernet-platform--> depends_on`「作业层依赖平台技术底座」· `flowernet-ops --mtm--> uses` · `merchant-ops-ai --mtm--> consumes` · `laodeng-app --mtm--> references` ⇒ ★ **四条边都指向 mtm 是【被用方】** |

★ **方法论一句**：**母子关系看【边的方向与阶段归属】，不看【词的命中频次】** ——
★ 频次高的往往是**上位概念词**，而非结构上的母节点。

### 17.4 ★★ 完整层级图（实证）

```
第 1 层 · 编排/母体
  flowernet（花店生意演进 · 7 阶段 · 公司级主线）
    │
    ├─ 第 2 层 · 业务/供给
    │    flowernet-ops（代运营服务）· flowernet-citywar（城市战/商家池）
    │    flowernet-supply（供应链）· flowernet-jv（合资公司/公司级）
    │
    ├─ 第 3 层 · 技术底座（★ 被 mtm 依赖）
    │    flowernet-platform（P0协议→P5应用 FNP）· flowernet-erp（数据底座）
    │    flowernet-miniapp · flowernet-website
    │
    ├─ 第 4 层 · ★ 作业层（被三腿共用的工具）
    │    mtm  ← depends_on flowernet-platform · consumed_by flowernet
    │
    └─ 第 5 层 · 产品化（消费 mtm 内核）
         merchant-ops-ai（栈3 · consumes mtm mcp-export）
         laodeng-app（触达壳 · references mtm · distinct_from mtm）
```

★ **关键读法**：**mtm 不挂在 `laodeng-app` 或 `merchant-ops-ai` 之下** ——
那两者是**消费/引用**它；mtm 的上一级是 `flowernet-platform`（技术底座）与 `flowernet`（业务母体）。

### 17.5 ★★ 对灯塔「母体假设」的回应

★ **方向对** —— **外卖侧的母体是 `flowernet` 蓝图族，不是 MTM**。
★★ **更准确的说法**：**MTM 是【作业层】，不是【母体】**；而 **flowernet 是【母体蓝图族】但它的定位超出外卖**
（花店生意全谱：ERP/端侧/云聚/IoT/门店扩张/供应链）。
⇒ ★ 若报告要写「外卖侧母体」，建议表述为
「**外卖侧挂在 flowernet 母体蓝图族的 d25/d3/d4 三条主线上**」。

### 17.6 ★ 外卖侧在 flowernet 里的三条主线条目（实证）

| 阶段 | 内容 | owner | status |
|---|---|---|---|
| **d25-3** | 外卖商品订单→ERP 导入（全平台 10 店） | 运营/协调者 | active |
| **d3-2** | 外卖智能体感知（面板 8787） | 运营 | active |
| **d4-3** | 数据飞轮（模型下发→更优执行→更优数据）· note=**护城河** | — | — |

★ **旁证**（`works` 表逐字）：**「d25-3 老登 / d4-1 知了 / d3-2 运营」**
⇒ ★ **三角三腿在 flowernet 的 works 里有【属主登记】**。

### 17.7 ★★ 一处连带修正（★ 我上一卡的判定要细化）

> 我第十六章说「**三腿在蓝图层没有共同锚点**」——
> ★ 该判在 **owner 字段**层面成立，但 **`works` 表**里三腿**各自有属主登记**。

⇒ **准确表述应为**：
```
三腿在【蓝图 owner 字段】无共同锚点；
但在【flowernet 的 works 表】里各有属主登记，且【分属不同 stage】
⇒ 仍是【分叉】而非【共建】。
★ 若报告要升级为「共享蓝图底座」，唯一站得住的表述是：
  三腿共享 flowernet 母体蓝图的【不同主线】
  （老登 d25-3 / 知了 d4-1 / 运营 d3-2），【不共享同一条蓝图】。
```
