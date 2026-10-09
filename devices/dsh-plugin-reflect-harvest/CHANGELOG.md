# CHANGELOG · dsh-plugin-reflect-harvest

## v1.1.1 · 2026-09-11（依 R003 补充通告修正「空壳键」漏读）

**动因**：读黑板卡 `data/registry/r003-key-syntax-notice-20260911`（R003 补充 · enforced）——
通告点名的两类规则：① key 首段须纯小写字母，**400=键错 / 404=不存在**；② **写入必须回读确认内容非空**，
并特别指出「**空壳键变体**：键存在但 `value={}` —— **纯状态码校验会漏**，必须验内容」。

### 被抓到的自身缺口（正是通告点名的那一类）
本工具 `lib/http.js` 的 `blackboardExists()` 初版写的是
`exists: r.ok && r.value !== null && r.value !== undefined` —— **只看状态码 + 非 null**，
正是通告说的"纯状态码校验"。后果：一个 `value={}` 的空壳卡会被判成"卡已派出"，
于是该设备的回填状态从 `not_dispatched` 被**误标成 `pending`**（静默降级，输出里看不出来）。

### 修正
1. 新增 `isMeaningfulValue(v)`：对象须有 ≥1 个自有键、数组须非空、字符串须非空白；否则不算"有内容"。
2. `blackboardExists()` 改为**内容判据**，并新增 `emptyShell` 字段 —— 空壳键按"不存在"处理但**如实上报**（不静默吞掉）。
3. 回填源 `lib/source.js`：黑板返回 200 但内容为空时，记 `errors`（"空壳键…按未提交处理；依 R003 补充，写入方需回读确认内容非空"）而不是当成一份空回填。
4. 统一日志口径：`items` 字段原来是 `${valid}/${rejected.length} rejected` —— 而 `rejected` **混含**条目级与文件级，
   与 payload 的 `items_rejected`（仅条目级）**对不上**（实测日志写 "13 valid / 4 rejected"，而 payload 是 `items_rejected=3`）。
   现拆成 `N valid / M item-rejected / K file-rejected`，两处口径一致。
5. `reason` 字段区分四种情形：`bad key（首段须纯小写字母）` / `not found（格式合法但不存在）` / `empty shell（键在但 value 为空）` / `ok（内容非空）`。

### 实测（v1.1.1）
- 400 探测：`Bad-Namespace/foo` → `{"exists":false,"status":400,"reason":"bad key（首段须纯小写字母）"}`
- 404 探测：`data/reflect/answers/nope/1999-01-01` → `{"exists":false,"status":404,"reason":"not found（格式合法但不存在）"}`
- 命中探测：`data/reflect/answers/lab-mbp/2026-09-10` → `{"exists":true,"reason":"ok（内容非空）"}`
- **空壳探测**：PUT `{}` 到 probe 键后 → `{"exists":false,"emptyShell":true,"status":200,"reason":"empty shell（键在但 value 为空）"}` ✅ 纯状态码校验会漏的变体已堵
- 回归：`--lean4-check` A–F 全绿 exit 0 · `--dry-run` exit 0

### 本包自身的合规自检（对照通告）
- 登记卡 key `data/registry/dsh-plugin-reflect-harvest`：首段 `data` 为纯小写字母 ✅
- 写入后已回读确认（HTTP 200 且 `value` 非空）✅
- 本工具的**出站只有 GET**（F 项扫描证明无 `http.request/fetch/XMLHttpRequest`），因此它只**读**黑板、从不写 —— 通告约束的是写入方行为

## v1.1.0 · 2026-09-10（★ 跨设备层）

**性质**：把"从哪儿收"从**单一目录**扩展为**全设备**（用户指令 + design v1.1 §10）。
动因：**只采本机 = 只看到四分之一** —— MBP 上跑着独立的 DSH 智能体网络，i9 经 MCP 接入，
它们的经验若不被吸收就是**永久的盲区**。

### 新增
1. **全设备回填源**：本机 `<localRoot>/answers/<device>/<date>/`（兼容老布局 `<localRoot>/answers/<date>/`）
   + **中央黑板** `data/reflect/answers/<device>/<date>`（GET）。`--devices` / `--device` / `--central` / `--local-root` / `--local-only`。
2. **按设备分组统计** `per_device`：每设备独立的 items_valid / items_rejected / 拒收原因分布 / flags / 源计数 / 错误。
3. **版本漂移检查**：回填带 `plugin_version` 时比对，不一致 → 进 notes + 摘要 + 提案统计表（"裁定前先确认口径"）。
4. **pending ≠ missing**：无回填但**卡已派出** → `pending`（可能离线）；未派卡 → `not_dispatched`。卡探测走本机 cards 目录 + 黑板。
5. **`--allow-late`**：额外读 T-1/T-2 的 key，**只收归属当日**的记录，并标注 `late_by_key` / `late_key_offset` / `submitted_at`（Φ13 实践）。
6. **集群 agents 升级为 `<设备>:<智能体>`**；`recurrence` 语义升级为"几个 **设备:智能体** 独立提到"；
   **新增 `cross_device: true/false`**（跨设备复现 = 更强的信号）。
7. **`evidence_no_collected_at`**：`evidence.ts` 是对象时刻、缺 `collected_at` 采集时刻 → 标注（**不拒收**；
   现有回填格式还没这个字段，拒收会让流水线当天停摆）。**不做跨设备时间戳一致性判定**（各设备时钟可能不同步）。
8. **`possible_sync_duplicate`**：`lesson` **逐字相同** + 跨 ≥2 设备 + `evidence.ts` 时点接近（<24h）
   → 判为同步盘/复制粘贴产物，**不重复计入 recurrence**（否则跨设备信号会被"同一份文件的两份副本"伪造）。
9. **`device_mismatch`**：key 说 A 设备、载荷自称 B 设备 → 拒绝该条并计数（跨设备污染防护）。
10. **(device, agent) 去重，来源优先级：黑板 > 本地** —— 否则同一台设备的"本地落盘 + 黑板推送"会被算两遍。
11. **设备名门**：`[a-z0-9][a-z0-9._-]{0,31}`，同时挡黑板 key 语法与本地路径穿越（`../`、`/`、空白、前导点）。

### ⑩ 结构门相应升级（新增能力 = 新增"不该发生路径"候选）
- 新增出站能力后，立刻补上封堵：**本工具只读黑板，绝不写黑板**（谁回填谁写；汇集方代笔 = 证据链失效）。
  - **没有那个入口**：`lib/http.js` 只导出 `httpGetJson(url)` —— **无 method 参数**，无通用 request 原语。
  - **没有那个能力**：F 项扫描证明全包**不存在** `http.request` / `fetch` / `XMLHttpRequest` / `net.connect` / `dgram` 调用点（允许的 HTTP 方法闭集 = `['GET']`）。
  - **有那个证明**：新增 **HTTP 扫描器正控**（喂 `http.request({method:'PUT'})` + `fetch(...,{method:'POST'})` + `XMLHttpRequest` + `net.connect` 必须被命中 4/4 —— 否则是"空洞通过"）。
  - **失败即停**：设备名非法 → `DeviceError`；黑板不可达 → 逐设备报错并**继续用本地数据**（降级，不抛栈）。

### ★ 被自己的检查抓到的四个错误（错误模型复盘）

| # | 错误模型 | 实际后果 | 怎么发现的 | 修法 |
|---|---|---|---|---|
| 1 | 以为 `items` 是"智能体记录列表" | 单体回填 `{agent, items:[反思条目]}` 被当成捆扎包 → 一条反思被拆成一堆"缺 agent"的碎片；**mac-mini 的 4 份回填全部文件级拒收** | 按设备统计里 mac-mini 显示 `文件级拒收 4` + `第 N 条缺 agent` | 先判单体形态（自带 `agent` 且 `items` 是数组），捆扎键只认 `answers/records/submissions`（**不含 `items`**） |
| 2 | 以为 `recurrenceOf()` 可以直接复用 | 它按 `m.agent`（**只有智能体名**）去重 → 两台设备上同名的 `agent-echo` 被合并 → `recurrence=4`，而同一行的明细 `lab-mbp×1 + mac-mini×3 + mbp×1` 加起来是 **5** | **明细与计数自相矛盾**（人眼） → 遂增加 D 项「产出不变量」自动检查 `recurrence === agents.length` | 按 `<设备>:<智能体>` **复合键**去重 |
| 3 | 以为负例里放什么都会被拒 | 把 `MAC-MINI`（应归一化成 `mac-mini`）与 `42`（合法数字设备名）错列进负例 → 制造了 2 个永远修不掉的"红" | B 项的 `★竟然放行` 明细 | 修正**我自己的测试期望**（这才是 R006 §6 坑#1 的反向形态：不是门太宽，是**测试错了**） |
| 4 | 以为"多层信封"不用管 | 第一次 PUT 黑板时把 body 写成 `{"value": BUNDLE}`，黑板自己还会包一层 → 值变成 `{value:{value:...}}` → 解析不到答案 | 回读校验（R003）发现 `value.device=None` | ① 写入方直接 PUT 值本身；② 解析侧加**有界解包**（最多 2 层）并明确告警"写入方应直接 PUT 值本身" |

> 第 2 条尤其值得记：**它是"人眼看明细发现的"，不是工具发现的**。补上 D 项产出不变量之后，
> 这类"同一份输出里两个字段互相矛盾"的错才会被机器自动抓住 —— 那正是最容易被漏掉的一类错。

### 实测证据（v1.1.0 交付时）
- `--selfcheck`：exit 0（能力清单 / 不该发生路径清单 · 集合运算 20 个键命中 0 / 依赖完整性 `cordis@4.0.2`+`dsh-tools@0.1.1-rc.2` via profile）
- `--lean4-check`：A–F 全绿、exit 0
  - B：证据负例 10/10 · 字段类型 8/8 · 品牌 6/6 · **写门 12/12** · **设备名门 16/16** · 削弱旗标 0/20
  - D：`--dry-run` 前后 **7 项**外部状态一致 · **产出不变量全部自洽**（6 簇）
  - F：exec 扫描器正控 2+1 · **HTTP 扫描器正控 4/4** · 本包通用 HTTP 调用点 **0** · 写调用点全在 `lib/out.js`
- 4 设备实测（mac-mini 本地 / mbp 本地 / **lab-mbp 走中央黑板 GET** / i9 pending）：
  - 设备 3/4 已回填 · 1 pending（i9）· 版本漂移 `0.9.9 vs 1.0.0`
  - `lab-mbp` 源计数 **本地 1 · 黑板 2**，并触发去重 `保留 blackboard，丢弃 local`
  - **C1 跨设备 cluster：recurrence=5（lab-mbp×1 + mac-mini×3 + mbp×1）**
  - **C2 同步盘剔除**：`mbp:agent-echo#R2` 逐字相同 → 不计入，recurrence 保持 2（mac-mini×2），`cross_device=false`

---

## v1.0.0 · 2026-09-10（首版）

**性质**：每日反思流水线「收牌」（④）环节的工具化。核心不是合并，是**校验** ——
把「无证据的条目当有效混进汇总」这条路径做成**结构上不可走**。

### 交付
- 插件形态：`package.json` + `cordis.patch.yml` + `lib/index.js`（`inject:['tools']`）注册工具 `reflect_harvest`
- 五类校验：★证据完整性 / 必填字段 / `suggestion.type` 合法性 / `related_rule` 存在性 / `declined` 合法性
- 跨智能体聚类 + **复现广度**计数
- ⑩ 结构门：品牌机制（`mintAdmitted` 唯一入口 / `buildValidSet` 唯一 push 点）+ 冻结闭集 + 命令白名单空集 + `--lean4-check` A–F

### ★ 首版开发中被自己的门抓到的三个错误（错误模型复盘）

#### 1. 写扫描器漏掉自己的主要目标（空洞通过）
- **错误模型**：以为"用 `(?<![\w.$])` 做负向后顾"更严谨（连 `.` 也排除）。
- **后果**：`fs.writeFileSync(` 的前缀正是 `.` → **全部写调用点被漏掉** → 「0 个越界写」**空洞通过**（R006 §6 坑#3）。门看起来全绿，其实什么都没查。
- **发现**：F 项**扫描器正控**（喂含 `fs.writeFileSync('/tmp/RULES.md')` 的合成源码，断言必须命中 1 条）实测命中 **0**。
- **修法**：负向后顾只排除 `[\w$]`。

#### 2. 扫描器把自己当靶子（假阳性）
- **后果**：F 项立刻变红 —— 它把 `lib/gate.js` 里自己的 `re.exec(code)` 当成外部命令执行点（R006 §6 坑#2）。
- **两种错修都要避免**：收紧正则会**顺手关掉真漏洞**（`cp.exec('ls')` 漏掉）；静默 filter 则变成"看不见的豁免"。
- **修法**：照常枚举 + 识别接收者 + 标 `benign:true` 并**在图示里计数**；正控同时断言"良性被识别 **且** 真调用仍被枚举"。

#### 3. 聚类单判据会漏合（把复现广度错拆）
- **错误模型**：以为 bigram Dice ≥ 0.52 足够判定"同一条 lesson"。
- **后果**：实测两句同一件事的复述共享 **13 个 bigram**，Dice 只有 **0.491** → 只按 Dice 会把「3 个智能体独立提到」错拆成「1+1+1」，而复现广度正是本工具存在的全部理由。
- **修法**：双判据 `dice ≥ 0.52` **或**（`shared ≥ 8` 且 `dice ≥ 0.40`）；并把 `dice ≥ 0.25` 的**灰区对显式列出**。

#### 4. 一个实现 bug（如实登记）
`mintAdmitted()` 初版只透传 `{agent, item, flags}`，**丢掉 `item_id`** → 聚类键变成 `agent-alpha#undefined`。由输出直接暴露，已修。

### 实测证据（首版）
- `--selfcheck` exit 0；`--lean4-check` A–F 全绿 exit 0
- B：证据负例 10/10 + 字段类型 8/8 + 品牌 6/6 + 写门 12/12 全部被拒
- D：`--dry-run` 前后 6 项外部状态完全一致
- fixture（4 智能体 / 11 条目，故意含 2 条无证据 + 1 条非法 type + 1 条 unknown_rule + 1 条 declined 无理由）：
  `items_valid=8` / `items_rejected=3` / `files_rejected=1`；拒收分布 `invalid_evidence ×2 · invalid_type ×1 · invalid_decline ×1`；flag `unknown_rule ×1`
- 簇：`C1 recurrence=3` · `C2 recurrence=2` · 3 个 `recurrence=1`

### 已登记的局限（不隐瞒）
- 聚类是**字面层**近似，非语义近似；真正换述可能并不到一起 → 靠 `similarity` 灰区矩阵显式暴露交人工。
- 扫描器是**源码结构扫描，非完整 AST**（本包零外部依赖）；命名与输出均如实标注。
- `--lean4-check` D 项依赖包内只读 `testdata/`；缺失时**如实报失败**而不是假装通过。
