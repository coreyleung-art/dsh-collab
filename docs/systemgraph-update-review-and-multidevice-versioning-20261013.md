# SystemGraph 更新审查 + 多端版本管理审计

> **出件**：明鉴 v3 · 2026-10-13 · mac-mini
> **范围**：① 对 2026-10-12 夜间「可写枢纽」全部更新做一次审查 ② 对既有多端版本管理体系做一次审计
> ★ **本件不宣布任何事项已闭合**；所有读数带【时刻】与【来源】。

---

## 第一部分 · 更新审查（改动清单与风险）

### 1.1 改了什么

| 期 | 内容 | 规模 |
|---|---|---|
| **P1** | 写端点 `POST /api/write` + 动词层（7 动词白名单）+ ACL 默认拒绝 | — |
| **P2** | R3 页面级内容寻址（`page:<view>`）+ R6 版本与回滚（append-only） | — |
| **P3** | R4 连线编辑（`graph:<name>` 墓碑）+ R5 实时推送（`add_watch`） | — |
| **P4** | R8 并发互斥（乐观锁 `expected_seq` + 锁内读-校验-写） | — |
| **P5** | R7 反向指导（P5.0–P5.5：属主存活校验 / 缺口台账+棘轮 / 五道门 / 三态投递 / 对账+验收 / 通道登记） | — |
| **客户端** | `dsh-plugin-sg-write`（插件 + CLI + 3 工具） | — |
| **规则** | R060 机制登记纪律 · R061 账本单一真相源纪律 | — |

**代码规模**：`bb-blueprint-gallery.py` **4422 行 → 4944 行**（+522 行）
**端点**：GET **53 个**（新增 7 个 `sg-*` 只读端点）· **POST 仅 1 个**（`/api/write` —— ★ 单一写入口）
**新增数据键**：`data/registry/sg-{gap-baseline,gap-history,dispatch-log,rate,breaker,receipt,dispatch-switch}`（7 个，实测均 200）
**新增文件**：`data/registry/sg-acl.json`（磁盘文件，非板键 ⇒ 板键查询 404 属正常）

### 1.2 审查结论：**机制层健全，放行层刻意收紧**

| 维度 | 判定 | 证据 |
|---|---|---|
| **单一写入口** | ✅ | 只有 `do_POST` → 动词层；`do_GET` 未改；无第二写路径 |
| **默认拒绝** | ✅ | ACL `default: deny`；★ **真实页/真实图仍不授权**（实测 `page:ledger`/`relation:relations` 均 403） |
| **放行范围** | ⚠️ **最小** | ★ 只授权 **`page:goal` 一个真实页** + 2 个沙盒 + probe；**撤销 = 删一条 grant** |
| **真实数据安全** | ✅ | 实测 `data/blueprint/relations` **edges=53 · blueprints=21 · ts 仍 2026-09-10** ⇒ 一根未动 |
| **可回滚** | ✅ | append-only 历史 + `rollback`（追加非删除）；服务端改动有 11+ 备份 |
| **审计** | ✅ | `logs/sg-write-audit.jsonl` **49+ 行**，**含被拒的**（403/400/409 全留痕） |
| **并发** | ✅ | 锁内读-校验-写 ⇒ 真并发双写**恰一个 200 一个 409** |
| **客户端** | ✅ | R006 §5 三步全过 · 真挂载冒烟 **pass** · `gate_scan` **High 0** |

### 1.3 ★ 审查中发现并已修的两个真缺陷

**① P4 的 TOCTOU 竞态**（乐观锁第一版**失效**）
> 门禁读 seq 与写函数再读 seq 之间**无原子性** ⇒ 实测**双写都成功且都报 seq=6**。
> ⇒ 修：把「读-校验-追加-PUT-回读」**整段放进同一把锁**。

**② 服务端把「写成功」报成「失败」**（★ P0 级语义缺陷）
> 黑板对 PUT 的**响应极慢（实测 >60s 未回）**，而**写入其实成功**。原实现一律报
> 「写页面档失败：timeout」⇒ **把成功报成了失败**。
> ⇒ 修：**PUT 异常后【回读一次】再判**（R006 §6 坑 #4 原文：「判据要选**结果态**而非过程态」）。
> ★★ 走过弯路（如实记）：第一版按「`urlopen` 是否正常返回」判 ⇒ **不够**（超时也抛异常）。

**③ 我的两次重大误判**（★ 坏的都是**观测装置**，不是被观测对象）
> 我先判「**黑板写路径全挂**」并准备建议重启基础设施 —— 复查发现**写其实全都成功了**
> （回读显示我判「超时」的那两次 PUT 的键**都在**）；`GET /data/` 用 25s 超时**也能通（2.19s）**。
> ★ **真相是「写成功但响应极慢」，不是「写不通」。** 未对基础设施做任何改动。

---

## 第二部分 · 多端版本管理审计

### 2.1 现状：**已有完整体系，但停在 2026-09-06**

| 件 | 位置 | 状态 |
|---|---|---|
| **版本台账** | `~/system-graph-app/VERSION-MANIFEST.md` | ★ **mtime Sep 6 18:37**（一个多月未更新） |
| **管理工具** | `~/system-graph-app/scripts/sysgraph-version.sh`（151 行） | ✅ 有三个动作：`check` / `release` / `status` |
| **发布门禁** | `data/blueprint/gallery/gates/release-*.md` | ★ 最后一份 **release-1.4.0-20260906** |
| **CHANGELOG** | `~/system-graph-app/CHANGELOG.md` | — |
| **产物** | `dist/SystemGraph.{app,dmg}` | ★ 均 **Sep 6 18:37** |
| **iOS** | `~/system-graph-ios/build-archive-*` | ★ 有 **3 个 2026-10-12** 的新 archive（★ 台账未记） |

### 2.2 ★★ 核心发现：**`check` 是【恒真判据】**

**四处版本声明实测（全部 `1.4.0`）**：
```
① 引擎    bb-blueprint-gallery.py:33   VERSION = "v1.4.0"
② macOS   ~/system-graph-app/package.json      "version": "1.4.0"
③ iOS     ~/system-graph-ios/project.yml       MARKETING_VERSION: "1.4.0"
④ 台账    VERSION-MANIFEST.md                  当前版本: v1.4.0
⇒ sysgraph-version.sh check ⇒ ✅ 三端+台账版本一致: v1.4.0（exit 0）
```

**★ 而内容实测【差了一倍】**：
```
源引擎   ~/dsh-collab/scripts/bb-blueprint-gallery.py
         282,064 B · sha16 c3f10d7a66f23241 · mtime 2026-10-13 01:32
壳副本   ~/system-graph-app/dist/SystemGraph.app/Contents/Resources/app/gallery/bb-blueprint-gallery.py
         149,575 B · sha16 6bb5aeacaff43877 · mtime 2026-09-06
★ 一致：False      ← 版本号一致，内容差 132 KB（近一半）
```

★★★ **⇒ 结论：`check` 只比【版本号字符串】⇒ 版本号一致 ≠ 内容一致 ⇒ 只要没人记得 bump 版本号，它永远报 ✅。**

★★ **而这一点**体系自己早就记过**：`~/system-graph-app/desktop/main.js:29` 注释逐字 ——
> 「两者同称 v1.4.0 但内容不同 —— 即『**同版号不同内容**』类分叉。」

### 2.3 ★★ R061 视角：声明的方向 ⇄ 执行的检查，不一致

`VERSION-MANIFEST.md:18` 逐字写明了源与方向：
> 「macOS 壳内嵌 gallery 服务副本 = 源 `~/dsh-collab/scripts/bb-blueprint-gallery.py`（**发布时 rsync 同步**）」

★ **但**：
- 方向**只在文档里**，`check` 脚本**不检查它**（只比版本号）
- 「发布时 rsync」⇒ **没人检查「发布过没有」**
- ★★ 实测：**壳副本停在 Sep 6，源已到 Oct 13** ⇒ **方向已长时间未执行，而无任何报警**

⇒ **按 R061(a)「方向须与事实一致」**：**声明的方向与执行的事实已不一致**。

### 2.4 ★ 我今晚亲手加重了这次漂移

> 引擎 **4422 → 4944 行**（+522 行，含写端点 / 五道门 / 缺口台账 / 三态投递），
> ★ **而 `VERSION` 仍是 `v1.4.0`，`VERSION-MANIFEST.md` 未被触碰** ⇒ `check` 报 ✅。

★ **这正是 R061 要治的形态**：**改了产物而没动版本 ⇒ 漂移不可见**。

---

## 第三部分 · 建议（按优先级）

| # | 建议 | 理由 |
|---|---|---|
| **1** | ★★ **给 `check` 加【内容指纹】**：比对源引擎 sha256 ⇄ 壳副本 sha256，不一致即报 ❌（同版号不同内容） | 治「恒真判据」。★ 实测该判据**现在已经会红**（`c3f10d7a…` ≠ `6bb5aeac…`） |
| **2** | ★ **把「源 → 壳副本」的 rsync 纳入 `release` 的可机械核步骤**（或至少让 `check` 校验它） | 治「声明的方向无执行体」 |
| **3** | **明确四处版本的【唯一真相源】**（建议：引擎 `VERSION` 常量 = 源；其余为派生物）并在 MANIFEST 里写明方向 | ★ R061(a) |
| **4** | **本轮改动应 bump 版本**（引擎 +522 行、新增 8 个端点）⇒ 建议 `v1.5.0`；同步四处 + 台账 + CHANGELOG | 让漂移可见 |
| **5** | **iOS 那 3 个 10-12 archive 应记入台账** | 现在台账落后于事实 |
| **6** | ★ **给 `check` 加「不可判」态**：某源读不到时**不得报 ✅**（今日多次栽在这上面） | 「拿不到」≠「一致」 |

---

## 附 · 边界与未做

★ **未改动** `sysgraph-version.sh` / `VERSION-MANIFEST.md` / `package.json`（本节只审计与建议，改动待授权）
★ **未汇报**黑板 PUT 响应慢（按用户指示：只记录）
★ **未对** `rust-blackboard` / iOS 工程 / dist 产物做任何改动
