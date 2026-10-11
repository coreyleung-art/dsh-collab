# 执行度审查 · 锚点 v5（Wave 0–5 / Wave S / Wave C）

> **出件**：2026-10-10T07:22:54+08:00（`date` 实读）
> **审查人**：CU 实验台线（Claude Code 会话）· 应**用户**当次指令「做一次执行度审查」出件
> **审查对象**：锚点 `docs/distributed-agent-network-governance-plan-v5-20261010.md` @ `3c92e2a602978d9c`（mtime `2026-10-10T07:18:24`，size 57487 B，`state_version` 4）
> **审查方法**：**每条分「声明」与「核验」两栏**——「声明」= 台账/登记卡自述；「核验」= 本次实跑 / 实读。**不把前者当后者**（R030）。
> **本报告不是达标判定**，是**执行度**判定：只回答「做了没有 / 有多少独立证据」，不回答「做得好不好」。

---

## 〇、★ 元发现：审计对象是移动靶，且该现象已被自己登记为 P27

### 0.1 实测漂移（本次审查窗口内）

| 时刻 | 锚点 sha256 前缀 | `state_version` | beacon-check 该条 |
|---|---|---|---|
| 07:16:53 | `c096f2ce…`（索引声明值） | 4 | — |
| 07:1x | `34d26bd6…` | 4 | **PASS** |
| 07:17:58 | `bba935a8…` | 4 | **FAIL**（索引 `34d26bd6` ≠ 文件 `bba935a8`） |
| 07:18:24 | `3c92e2a6…` | 4 | 07:18:29 索引跟上，**PASS** |
| 07:18:49 / 51 / 53 | `3c92e2a6…`（三次恒等） | 4 | **PASS** |

**正文改了 4 次，`state_version` 恒为 4。** 本报告结论**钉死**在 `3c92e2a602978d9c…`。

### 0.2 这不是事故，是规则内的做法——但暴露了门的盲区

写入者自己的 `continuity-index._v5_sync_note` 逐字记着：

> 「★ 三次同步：v5 补 §4.1③ 40 行容量约束后**重新盖章**（sha 终值）。
> ★ 四次同步：全库时间戳规范化为 RFC3339（±HH:MM 带冒号）+ **重新盖章**。」

⇒ **指纹门（`beacon-check.py`「锚点指纹未变（改了正文须同时升 state_version 并重盖章）」）的机检部分只覆盖括号后半句「重盖章」**：它比对「索引里盖的章 == 文件现算的 sha」，**没有历史可比** ⇒ **「改了正文却没升 `state_version`」这一半,它结构上永远看不见**。审查窗口内该门**全程绿灯**，而正文改了 4 次。

### 0.3 这一族正是锚点自己新登记的 P27，而它的门还没通电

锚点 §7 第 330 行：

> `P27 | 检查项与变化项不是同一项 | 不崩、不报错、校验全绿，而事实已经变了：权威索引落后于交付物、时间戳落在未来、内部两段互相矛盾 | 判据覆盖缺口 + 自指参照系（比较的两端同源 ⇒ 一起变就永远相等） | 2026-10-10T07:0x 实测，三层同现 | G-CR18 信标自检覆盖门 | 重建判据后重跑；不是回滚数据，是回滚判据`

**但 G-CR18 只写了判据，没进门**：

```
$ grep -oE 'G-CR[0-9]+' tools/gcr-gate.py | sort -u -V
G-CR1 G-CR2 … G-CR17        ← 无 G-CR18
```

⇒ **为「校验全绿而事实已变」造的那道门，尚未实现。** 本报告 §四 实测到的全部漂移，与该门同一族。

---

## 一、计划本体（§10 WBS）：**Wave 0–5 共 39 项，完成 0 项**

### 1.1 逐项→产物穷尽盘点

清单来源：锚点 §10。盘点方式：全库检索产物存在性 + 登记卡自述；**只记存在性与自称，不含达标判断**。

```
未找到任何产物（36 项）:
  C4
  W0.2  W0.3  W0.4  W0.5
  W1.1  W1.2  W1.3  W1.4  W1.5  W1.6  W1.7  W1.8      （全部 8 项）
  W2.1  W2.2  W2.3  W2.4  W2.5  W2.6  W2.7  W2.8  W2.9  W2.10  （全部 10 项）
  W3.2  W3.3
  W4.2  W4.3  W4.4  W4.5  W4.6
  W5.1  W5.2  W5.3  W5.4  W5.5  W5.6                  （全部 6 项）

带条件 / 非完整交付（4 项）:
  W0.1  仅「判据修正件」—— docs/compaction-lowerbound-crash-20261009.md 自陈
        「并修正 W0.1 / G-CR9 的验收判据（这是本件最重要的产出）」⇒ 非「挂载」机制本体
  W0.6  仅 tools/gcr-gate.py 内同名的 G-CR8 检查函数
  W3.1  仅 headers["X-Writer"] 头（bb_dualwrite.py:66），**无 HMAC**
        （HMAC 密钥分发 owner = 用户，见 continuity-index `Q-E`）
  W4.1  仅 tools/gcr-gate.py 内同名的 G-CR14 检查函数
```

> ★ **关键更正**：上表 W0.6 / W4.1 所谓的「产物」，**都是 `gcr-gate.py` 里的同名检查函数**——而 `gcr-gate.py` 本身是 **S5（Wave S）的交付物**。⇒ **那不是 Wave 0/4 做了，是同一件工具被两处认领。**

### 1.2 登记层面亦无逐项自称

- `data/registry/continuity-index.json` 的 `items` 段只登记 `C1–C7 / P26 / R049`，**不含任何 W0.x…W5.x 条目**。
- `data/registry/state-registry.json` 只有**波级** `open`，**无逐项条目**。

⇒ Wave 1–5 的 39 项，**在事实上与登记上都不存在「已完成」自称**，声明与核验一致：**确实没做**。

### 1.3 反向发现：机制在、账上没有

`tools/floodgate.py`（11,745 B，mtime 2026-10-09 01:03）docstring 自称：

> 「**Token bucket / RFC 1363** 流规范…**Circuit breaker** / Bulkhead / Retry-with-backoff…失败与过载要**熔断**而不是重试放大」·「**SPILLWAY**（ACM）…**开闸泄洪**」

**机制名正对 W1.2（熔断）/ W1.4（floodgate 改造）/ W2.1（token bucket）/ W2.4（泄洪态）**，但：

```
$ grep -rl 'floodgate' data/registry/
data/registry/starbridge-knowledge-index.json     ← 知识索引，非交付卡
```

⇒ **没有任何登记卡声称它是这些 WBS 项的交付物。** 这类「东西在、账上没有」与「账上有、东西不在」**同样会造成漂移**。
**⇒ 待裁（见 §六 第 4 条）：`floodgate.py` 是 Wave 1/2 的既有实现（则 Wave 1/2 进度须重估），还是与计划无关的旁支？**

### 1.4 计数不符（与 P27 同族）

| 处 | 自称 | 实列 | 判 |
|---|---|---|---|
| 锚点 §10 表头 | 「WBS（**30 项** + v5 状态重标）」 | **39** 个唯一 W 编号（6+8+10+3+6+6） | 不符 |
| 锚点 §10 / 卡 | G-CR「**十五条**」 | §7.9 实列 **17**（`gcr-gate.py` 自陈已登记） | 不符（已登记） |

---

## 二、Wave S（门 / 工具面）：**交付 8 件，验证 0 件**

### 2.1 声明

锚点 §10 + `docs/wave-s-toolchain-delivery-v1.md`（19,171 B，mtime 03:31）：S1–S5 五项 **+ 增① 身份声称门 + 增② 自指破坏门**「工具面已交付，全部走完 R006 §5 三步」。
`continuity-index.waves[S]` = `in_flight`，note 自述：

> 「七件实体在 tools/ 已逐一核对字节数…★ **但七件均为作者自测，缺独立 verifier** ⇒ 整体 in_flight，**不得记 closed**。」

### 2.2 核验

| 件 | 文件 | 字节 | mtime |
|---|---|---|---|
| S1 沙箱模拟框架 | `tools/sandbox-script.py` | 23,760 | 10-10 04:03 |
| S2 信息包模板 | `tools/infopack-check.py` | 24,953 | 10-10 03:49 |
| S3 独立审查流程 | `tools/review-gate.py` | 26,473 | 10-10 03:49 |
| S4 官方规范校对门 | `tools/official-ref-gate.py` | 19,376 | 10-10 03:49 |
| S5 G-CR 校验脚本 | `tools/gcr-gate.py` | 33,157 | 10-10 03:31 |
| 增① 身份声称门 | `tools/node-claim-gate.py` | 10,659 | 10-10 01:51 |
| 增② 自指破坏门 | `tools/self-destruct-gate.py` | 23,495 | 10-10 03:18 |
| （另）声明有效性扫描 | `tools/declaration-validity-scan.py` | 18,862 | 10-10 05:28 |

**可启动性抽检**（只读 `--help`）：

```
$ python3 tools/node-claim-gate.py --help          → rc=0
$ python3 tools/declaration-validity-scan.py --help → rc=0
```

**验证层**：

```
$ cat data/registry/review-tracker.json
{ "items": [], "_correction": { … } }
```

唯一一条历史登记被**移除**，理由是 `executor 与 verifier 同为 session-1ffded95（R046 禁 verifier=executor）`，当前记 `verifier_unavailable`，保持 `in_flight`。

⇒ **工具面 8/8 在位（事实层）；独立验证 0/8（验证层）。** 索引自述**属实**。

### 2.3 ★ 第 4 类漂移：同一波，两张卡直接对立

| 卡 | Wave S 状态 | 自述理由 | `source` 字段 |
|---|---|---|---|
| `state-registry.json`（10-09 21:58） | **`blocked`** | 「只见设计（§5/§6），**未见建成证据**；各项 DoD 与负控未落盘」 | `blackboard:data/registry:continuity-index` |
| `continuity-index.json`（10-10 07:18） | `in_flight` | 「工具面**已交付**…缺独立 verifier」 | — |

★ **`state-registry.json` 该条的 `source` 自称派生自 `continuity-index`，内容却与索引相反。**
这正是 P27 那句话的反面：**「比较的两端同源 ⇒ 一起变就永远相等」——而此处两端同源却不等，且没有任何门在看。**

---

## 三、Wave C（信标）：**在位 5 件，独立 verifier 0 件**

### 3.1 声明 vs 核验

| 项 | 声明 | 核验 |
|---|---|---|
| C1 单一索引键 | `closed_with_evidence`，证据 `blackboard:data/registry/continuity-index` | **C1 无 `verifier` 字段**；证据是黑板键，而 `beacon-check` 对它 **SKIP**（未开 `--net`）⇒ **C1 自己的证据从未被门抽检过** |
| C2 锚点文档 | `closed_with_evidence` | 证据**仍指向 `…v4-20261009.md`** —— **已被 v5 取代**，证据滞留在上一版 |
| C3 续接提示词 | `closed_with_evidence` | `verifier: "待第三方复核（本件由外部第三方自建，按 S3「不可自审」必须另找复核人）"`；40 行，正踩 §4.1③ 上限 |
| C4 自启动注入 | `open` | `blocked_reason`：需改 CLD preset（外部第三方不代做） |
| C5 反遗忘校验 | `closed_with_evidence` | `verifier: "待第三方复核（同上，禁自证）"` |
| C6 状态机登记 | `in_flight` | `tools/build-state-registry.py` 在位、定义五态；索引自陈「closure 三要素缺 **verifier**」 |
| C7 证伪门与半修清单 | `in_flight` | 索引自陈「§11 六者**缺一**（边界用例）」 |

### 3.2 第三处漂移：C6 镜像过期

`state-registry.json` 里 C6 的镜像字段 `continuity_index_state: "open"`，而 `continuity-index.json` 已 `in_flight`。

### 3.3 §11 验收全文表缺席

```
continuity-index.dod._status = "**缺席**"
continuity-index.dod.full_table = null
```

⇒ §11 要求的**八字段全文表（正向判据/负控/边界用例/测量方法与样本量/阈值与判定规则/证据形态/审查员/沙箱复跑方式）从未落盘**。索引**自己声明了这一点**（诚实），但表仍不存在。

---

## 四、门（§7.9）：**当前是红的**

### 4.1 G-CR 门实跑

```
$ python3 tools/gcr-gate.py
★ 扫描时点：2026-10-10T07:19:10+0800
★ 条款来源：锚点 §7.9（实列 17 条；§10 称「十五条」⇒ 计数不符，已登记）
★ 覆盖：17 条全建档；本工具机械化的 11 条，其余标 N-A 并指向既有工具

  ✅ G-CR1  插件变更→沙箱挂载+dump-config+真挂载冒烟三态
  ⚠️ G-CR2  schema/DSL 过官方规则
  ✅ G-CR3  命名门 N1–N3 常驻
  ⚠️ G-CR4  依赖操作后扫遮蔽
  ⚠️ G-CR5  去遮蔽顺序固定
  ✅ G-CR6  dylib/binary 改动后逐个验签
  ✅ G-CR7  重签后 TCC 流程
  ❌ G-CR8  装载前事件数门 —— ★ 1 个会话文件 ≥200MB，最大 245.2MB（session-fa1f9150-c949-40）
  ✅ G-CR9  compaction 挂载+约束钉住
  ⚠️ G-CR10 子进程内存监控
  ⚠️ G-CR11 禁用/沙箱验证 31888 reload（「不用即安全」）
  ✅ G-CR12 不动运行中的 app.asar
  ⚠️ G-CR13 动态插件只用沙箱原语
  ⚠️ G-CR14 端口固定
  ⚠️ G-CR15 重启票流程
  ✅ G-CR16 请求前 token 预算门
  ⚠️ G-CR17 压缩有效性门

  ⇒ 汇总：PASS 7 · FAIL 1 · N-A 9（共 17）
  ⇒ ❌ 有 FAIL ⇒ 禁止推进/重启
```

### 4.2 读法（三处不得误读）

1. **唯一的 FAIL 是真的**，且它**就是 P26 那具尸体**（`continuity-index.last_session.status = "bricked"`，`session-fa1f9150-…`）⇒ **门正确地红了**。
2. **9 条 N-A 不是通过。** 其中 G-CR11 写的是「不用即安全」——那是**声明性豁免**，不是验证。
3. **G-CR8 自称「体积是代理指标，非事件数」** —— 判据本身还不是它自称的那个判据（其名是「**事件数**门」）。
4. **G-CR18 未实现**（`gcr-gate.py` 只覆盖 G-CR1–17）⇒ §0.3。

### 4.3 beacon-check 实跑

```
$ python3 tools/beacon-check.py
… 17 条 PASS …
SKIP C1 证据指针可解   << 未开 --net（黑板键 data/registry/continuity-index 本轮未抽检）
反遗忘校验：无 FAIL，但**有 1 条根本没抽检** ⇒ 不得读作『全绿』（0 条 WARN，1 条 SKIP）
EXIT=0
```

### 4.4 台账↔索引漂移实跑

```
$ python3 tools/qk-tracker-drift-check.py
  台账阶段: ['K0','K1','K2','K2.1','K3','K4','K5','K6','K7']
  索引 state: ['k1','k2','k21','k6']
  ❌ K3: 台账 §1 已标进展（✅），而索引没有对应 state 块
  ❌ K4: 同上
  ❌ K5: 同上
  ❌ 检出错位 3 处 —— 按目标要求「两处不许漂」，须先同步再推进
```

**4 类漂移汇总**：K3/K4/K5 台账↔索引 · C2 证据滞留 v4 · C6 镜像过期 · **Wave S 两卡对立**。**检查器只报不拦。**

---

## 五、综合执行度

| 层 | 声明 | 独立核验 | 判定 |
|---|---|---|---|
| Wave 0–5（**39 项**） | 全 `open` | 无完整交付物；4 项系 S5 工具被重复认领 | **0 / 39** |
| Wave S 工具面 | `in_flight` | 8 件实体；2 件抽检可启动（rc=0） | **已交付** |
| Wave S 验证 | `in_flight` | `review-tracker.items = []` | **0 / 8** |
| Wave C 信标 | 4 closed / 2 in_flight / 1 open | 5 件在位，**0 件有独立 verifier** | **在位，未验证** |
| §11 验收全文表 | — | `dod.full_table = null`（自标「缺席」） | **0** |
| §7.9 门 | — | **1 FAIL**（G-CR8/P26）· G-CR18 未实现 | **红** |

---

## 六、结论

1. **计划主体 39 项，执行度 0。** 不是失败，是 **Wave 0「开关合上」还没合**；且合闸前 §11 验收表根本不存在，合了也无从判。
2. **已做出来的（Wave S 工具 + Wave C 信标）全部卡在同一处：缺独立 verifier。** 这不是执行不足，是 **S3「不可自审」在这个体系里从未真正落地过一次**——`review-tracker` 空、C1 连 `verifier` 字段都没有、Wave S 八件全自测。
3. **最该先通电的是 G-CR18。** 本次实测到的漂移、Wave S 两卡对立、C2 滞留 v4、C6 镜像过期——**全是同一族**（校验全绿而事实已变），而这一族的门**只写了判据**。

### 待决 / 待办（**本报告不自行择一动手**）

| # | 项 | 归属 |
|---|---|---|
| 1 | **实现 G-CR18 四条判据**进 `gcr-gate.py`：① `waves`/`items` 两段 state 一致 ② `updated_at` 不得晚于当前时刻 ③ `closed_with_evidence` 项 `verifier` 字段不得缺失 ④ 本地副本 ↔ 板值一致 | 待指派 |
| 2 | **清漂移补课单**：Wave S 两卡对立 · C2 证据改指 v5 · C6 镜像 · K3/K4/K5 三处 · §10 计数 30→39 | 待指派 |
| 3 | **§11 八字段全文表落盘**（`dod.full_table`）—— Wave 0 合闸的前置 | 待指派 |
| 4 | **给 `floodgate.py` 定性**：是 W1.2/W1.4/W2.1/W2.4 的既有实现（⇒ Wave 1/2 进度须重估），还是与计划无关的旁支？ | **★ 只有用户知道** |
| 5 | **独立 verifier 从哪来**（S3「不可自审」的唯一出路）—— Wave S 八件 + C1/C3/C5 全卡在此 | **待用户裁定** |

---

## 附录：本次审查的原始命令与退出码

```bash
# 时间戳与对象锚定（§0）
NOW=$(date +%Y-%m-%dT%H:%M:%S%:z)                      # 实读，非估算
shasum -a 256 docs/…v5-20261010.md                     # 3c92e2a602978d9c1f083302bef849dcaaa1828cbf9337ee48b3bbad80316b55
stat -f '%Sm %z' docs/…v5-20261010.md                  # mtime 07:18:24  size 57487

# 连续读数（证并发改写，§0.1）
for i in 1 2 3; do shasum -a 256 <anchor>; sleep 2; done
# 07:18:49/51/53 三次恒为 3c92e2a602978d9c（此前 4 次变动）

# 门的机检覆盖范围（§0.3）
grep -oE 'G-CR[0-9]+' tools/gcr-gate.py | sort -u -V   # G-CR1…G-CR17，无 18

# 各门实跑（§四）
python3 tools/beacon-check.py                          # 17 PASS · 1 SKIP · 0 FAIL  EXIT=0
python3 tools/gcr-gate.py                              # PASS 7 · FAIL 1 · N-A 9
python3 tools/qk-tracker-drift-check.py                # ❌ 3 处错位

# Wave S 实体与可启动性（§二）
wc -c tools/{sandbox-script,infopack-check,review-gate,official-ref-gate,gcr-gate,self-destruct-gate,node-claim-gate,declaration-validity-scan}.py
python3 tools/node-claim-gate.py --help                # rc=0
python3 tools/declaration-validity-scan.py --help      # rc=0
cat data/registry/review-tracker.json                  # {"items": [], …}

# Wave C 证据指针（§三）
python3 -c "…逐条 os.path.exists…"                     # C2 → v4（已被 v5 取代）
python3 -c "…state-registry C6 镜像…"                  # C6: open（索引已 in_flight）

# Wave 0–5 产物盘点（§一）
grep -oE '\bW[0-9]\.[0-9]+\b' <anchor> | sort -u | wc -l   # 39
grep -nE '^# §10|WBS（' <anchor>                           # 「WBS（30 项 + v5 状态重标）」
grep -rl 'floodgate' data/registry/                        # 仅 starbridge-knowledge-index.json
```

**工具**：`tools/beacon-check.py` · `tools/gcr-gate.py` · `tools/qk-tracker-drift-check.py` · 逐项产物盘点子代理（32 次工具调用）
**登记卡**：待出（用户本次仅授权 `docs/` 台账）

---

> **本件是执行度审查，不是达标判定，也不是回滚指令。**
> 所有「声明」栏内容均引自台账/卡自述，可能本身有误；「核验」栏为本机实跑实读，
> **其有效期止于 `3c92e2a6` 那一版锚点**——该文件在审查期间被并发改写 4 次（§0.1）。
