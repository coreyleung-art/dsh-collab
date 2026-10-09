# dsh-plugin-reflect-dispatch · 反思卡定制派发（R006 十项达标 · 跨设备 v1.1）

> 位置 `~/dsh-collab/devices/dsh-plugin-reflect-dispatch/` · v1.1.0 · 制定：星桥 · 2026-09-10
> 所属流水线：`docs/daily-reflection-pipeline-design-v1.md` 的**环节 ② dispatch（发牌）**
> 上游：`reflect-collect`（事件流）· 下游：`reflect-harvest`（收回答卷）

---

## 一、为什么需要它（有实据，不是设想）

### 1.1 根问题：**统一问卷必然产出套话**

「每日反思」若每天问同样的问题，答案就会退化成模板。所以本工具的定位不是"发问卷"，而是**按每个智能体当天真实做过的事件，现做一张只对它成立的卡**。

做法上的差异（这是本工具存在的全部理由）：

| | 统一问卷 | 本工具 |
|---|---|---|
| 问题 | 固定 4–5 问 | 固定 5 问，但**每问后面挂该智能体自己的上下文**（动作分布、可疑事件号、自动检索到的候选规则号、跨设备线索） |
| 事件 | 无 | ① 段实摘 3–8 条，**每条印出"凭什么算你的"**（命中资源 + 匹配方式 + score） |
| 归属 | 不判 | 判，且**可复核**：同一份 events.json 任何人可重跑出同一套 score/via |
| 无事可说 | 被迫编 | 允许 `declined: true`，但必须给理由 |

### 1.2 事故与实测证据（本工具的设计是被这些现场推着走的）

| # | 现象 | 证据 | 对策（落在哪一行代码） |
|---|---|---|---|
| 1 | **假装派发了**：卡写了盘/根本没写，却对外称"已派发" | 已知纪律：2026-09-10 已有 4 次"报告指向不存在的落盘物"，都是把**写入返回非 200 当成成功**；黑板语义 400=写法非法 / 404=不存在，二者都不得当成功 | 发送路径强制 `PUT → 立即 GET → 语义比对`（`board.putAndVerify` + `gate.assertReadback`），不符即 `READBACK_MISMATCH` 失败 |
| 2 | **回读比对做成了字符比对 → 假失败** | 首跑实测：黑板会**重排 JSON 键序**，同一份内容 write 1316 字节 / read 1316 字节但键序不同 → 一次**成功**的写入被判成失败（R006 §6 坑 4） | 改为**规范化 JSON 语义比对**（`canonicalJson`，递归排序键），字节/字符数只作附注 |
| 3 | **只读到"停更快照"的档案 → 全判成 no-events** | 首跑实测：`~/.dsh-agent-bus.json` 是 2026-08-17 的旧路径（17 条），真正在用的是 `~/.dsh/agent-bus.json`（63 条）→ 当天 10 条事件里 8 条变成 unassigned | 档案按 **新→旧→镜像→黑板** 顺序尝试，并把**实际用的文件路径**写进结果与卡片 |
| 4 | **容器资源霸占归属 → 卡片退化成"别人的事"** | 真实数据实测：1692 条事件里，`~/dsh-collab/` 这一条资源命中 **842 条（49.8%）**，`~/dsh-collab/scripts` 命中 271 条（16%）→ 若不处理，这些目标的卡全是无关事件 | **实测占比降级**：命中 >10 条 **且** 占比 >5% → 判为容器，层级 `dir→weak`（≤45 < 阈值 50）；同时把"你的资源太宽"**写进卡片**当可回填观察 |
| 5 | **目录级候选淹没精确归属** | 实测 4 个会话都把 `~/dsh-collab/scripts`、`~/dsh-collab/` 登记成自己的资源 → 精确改了 `scripts/verify-ui.py` 的会话，与那 4 个"只是目录装着它"的会话并列 | **层级裁决** `specific > dir > weak`；被压下的候选记入 `suppressed` 并写进卡片（不静默） |
| 6 | **相对路径 / 绝对路径不归一 → 归属大面积退化** | 与兄弟组件对接实测：`reflect-collect` 产出的 `path` 是**相对路径**（`dsh-collab/scripts/verify-ui.py`），而 profile 里的 `resources` 多为**绝对路径**（`file:/Users/coreyleung/...`）→ 精确/前缀规则一条都不命中 | 绝对路径按 `$HOME` 归一成相对尾部再比（96/88/80 分档） |
| 7 | **在线判定是同义反复 → pending 分支永不可达** | 自审发现：初版把"当天上报过事件"也当作"在线"，而那与"有卡可发"是**同一条件** → 永远判 `delivered`，设计文档 §10.4「待投递队列」形同虚设（设备当晚可能早就关机） | 在场判定改用**独立活性信号**（发现层心跳 <90s / `--assume-online` 人工声明），三个信号分开记录 |
| 8 | **`--json` 被自己的 `process.exit` 截断** | 实测：`process.stdout.write` 是异步的，紧跟 `process.exit()` 且输出较大（1407 条 unassigned ≈ 628KB）而 stdout 是管道时，尾部丢失 → 下游拿到**截断的 JSON** | `out()` 改用 `fs.writeSync(1, …)` 同步写 |
| 9 | **设备段的段位取错 → 所有合法路径都被判跨设备写** | 首跑被自己的 lean4-check C 抓到：`data/reflect/cards/<device>/…` 的相对路径第 0 段是 **kind**（`cards`），不是 device | `assertDeviceInPath` 取第 1 段并显式校验形状（R006 §6 坑 1「门太宽会砍掉自己人」的现场复现） |
| 10 | **脱敏不幂等 → 第二轮把 `[REDACTED:]` 又替换一次** | 首跑被 lean4-check C 抓到：`token=[REDACTED:github-token]` 被 kv 规则再当成"token=某值"处理 | 两条赋值类模式加 `(?!\[REDACTED:)` 幂等守卫 |
| 11 | **插件 apply 阶段就崩（挂不上）** | 真挂载冒烟实测：输出 schema 的嵌套对象漏写 `additionalProperties` → `dsh-tools` 抛 `UNSUPPORTED_SCHEMA: schema.properties.late.additionalProperties must be explicitly true or false` → `apply()` 抛异常，插件根本挂不上去 | 输出 schema 统一用 `obj()` 构造器**让漏写不可能**；并把「挂载冒烟」做成 `--selfcheck` 第 ⑤ 节（peer 解析不到时**如实说跳过**，不假装通过） |

> 规律（与 R006 §1 一致）：出问题的从来不是"没写代码"，而是**缺一项可机械核验的标准**，或**有一道会撒谎的检查**。
> 本工具上面 11 条里有 **6 条**（2/7/8/9/10/11）是**自己的门 / 自审 / 真挂载冒烟抓出来的** —— 这既是门在起作用的证据，也是"没有真跑过就不算验证"（R030）的现场教材。

---

## 二、它做什么（一句话 + 数据流）

> **按每个智能体当天真实做过的事件，定制一张「思考卡」并派发。**

```
各设备 reflect-collect
   └─ PUT data/reflect/events/<device>/<date>   （中央黑板 106.53.214.108:8792）
              │
              ▼
   ┌───────────────────── 本工具（环节②）─────────────────────┐
   │ ① 解析设备集合（诚实标方法）                              │
   │ ② 逐设备取事件流（中央板；--local-only 退回本机）         │
   │ ③ 归属判定 specific>dir>weak（含容器降级、跨设备复现线索）│
   │ ④ 逐人定制卡 ①实摘 ②5问带上下文 ③证据(Φ13双时点) ④schema │
   │ ⑤ 凭据脱敏（Φ12）→ 落盘 cards/<device>/…                 │
   │ ⑥ PUT data/reflect/cards/<device>/<date> + 回读校验       │
   │ ⑦ 在场判定 → delivered / pending（离线待取，非 failed）   │
   └───────────────────────────────────────────────────────────┘
              │
              ▼
   各设备智能体回填 → PUT data/reflect/answers/<device>/<date> → reflect-harvest
```

**key 三件套**（对齐设计文档 §10.2；首段命名空间必须纯小写字母，后续段自由）：

| key | 谁写 | 谁读 |
|---|---|---|
| `data/reflect/events/<device>/<date>` | 各设备 collect | 本工具 |
| `data/reflect/cards/<device>/<date>` | 本工具 | **该设备的智能体**（一设备一键，内含各 agent 段落） |
| `data/reflect/answers/<device>/<date>` | 各设备的智能体 | harvest |

---

## 三、用法（含退出码）

```bash
cd ~/dsh-collab/devices/dsh-plugin-reflect-dispatch

# ── 出卡（默认只落盘，不发送）──
node cli.js --events ~/dsh-collab/data/reflect/fixtures/events-20260910.json \
            --local-only --agents a3bc8cba,de7b29de,ffe19f07 --date 2026-09-10 --allow-late

# ── 全设备（默认：前缀列举 → 索引 → 冻结候选探测 → 兜底本机）──
node cli.js --date 2026-09-10 --allow-late --dry-run
node cli.js --date 2026-09-10 --allow-late --send          # PUT 中央板 + 回读校验

# ── 只读 ──
node cli.js --targets                                      # 可派目标 + 登记的 resources
node cli.js --devices-status --date 2026-09-10             # 三件套键存在性（200/404/400）
node cli.js --list-check                                   # 黑板前缀列举实测结论

# ── 门与自检 ──
node cli.js --selfcheck                                    # ② TCC：能力 / 不该发生路径 / 依赖
node cli.js --lean4-check                                  # ⑩ A–F 六项自证
node cli.js --tool-version                                 # 与 package.json 单一来源
node cli.js --register                                     # ⑧ 写黑板登记卡（可配 --dry-run）
node cli.js --help
```

**退出码（固定语义）**：`0` 成功/门生效 · `1` 失败或**门被触发** · `2` 用法错误或 IO 错误（未知旗标、位置参数、`--events` 不可读/非法 JSON、`--date` 非法、设备名非法、写盘越界）。

**主要旗标**：`--events` `--devices` `--device` `--local-only` `--allow-late` `--assume-online` `--agents` `--max-events` `--threshold` `--date` `--profiles` `--cards-root` `--send` `--emit-only` `--dry-run` `--json`。

**产物**：

```
~/dsh-collab/data/reflect/
├── cards/<device>/<短键>.md              # 每人一卡（最新；对应需求里的字面路径）
├── cards/<device>/<YYYYMMDD>/<短键>.md   # 同日归档（补派可回溯，不被覆盖）
├── cards/<device>/<YYYYMMDD>/_device-card.md   # ★ 设备合并卡 = PUT 到中央板的那一份
├── cards/<device>/<YYYYMMDD>/_index.json # 该设备当天的出卡索引
└── dispatch/<YYYYMMDD>/dispatch.json     # 派发台账（含每张卡的投递时刻与在场证据）
~/dsh-collab/logs/dsh-plugin-reflect-dispatch.log   # ⑦ 统一日志（失败也留痕）
```

> 为什么同时写"最新"与"同日归档"两份：字面需求给的是 `cards/<device>/<agent>.md`（人读方便），
> 但 T+1/T+2 补派会让不同日期的同名卡互相覆盖 → 用 `cards/<device>/<YYYYMMDD>/` 存真相，**两份内容 sha256 相同并各自回读校验**。
> 另：本工具**不写** `cards/<device>/<date>.md`（该形状已被兄弟组件的演示占用），避免碰别人的文件。

---

## 四、R006 十项达标矩阵

| # | R006 项 | 达标 | 本工具的实现 |
|---|---|---|---|
| ① | dsh 插件形态 | ✅ | `package.json`（`type:module`+`main`+`version`+`dsh.bundle.patch`）+ `cordis.patch.yml`（`- insert:` 一行）+ `lib/index.js`（`inject:['tools']`，注册 `reflect_dispatch` / `reflect_targets` / `reflect_device_status`，`ctx.effect` 回收） |
| ② | TCC 检测 | ✅ | `--selfcheck` **五段**：① 依赖完整性 ② 能力清单 ③ **不该发生路径清单（17 条，逐条写清"为什么结构上不存在"）** ④ 边界与降级（含两块黑板的实时可达性）⑤ **插件挂载冒烟**（import + 桩 ctx 调 `apply()` 数注册工具数；peer 不可解析时如实标"跳过"而非"通过"）——第 ⑤ 节正是抓到上面第 11 个错误的那道检查 |
| ③ | CLD 自适应 | ✅ | 运行期只用 node 内置（`fs/path/http/crypto/os/module/url/util`）；不 import 宿主私有路径；黑板不可达 → 明确失败并给可操作原因，不崩栈、不降级成"应该成功了" |
| ④ | dsh 版本自适应 | ✅ | peer 仅 `@deepseek-ai/cordis` / `@deepseek-ai/dsh-tools`，两级解析（本目录 → profile `node_modules`）；`--selfcheck` 可见解析结果 |
| ⑤ | 文档化 | ✅ | 本文件（为什么/用法/矩阵/坑/复现命令五要素）+ 源码 docstring + `r006.documented` |
| ⑥ | 版本管理 | ✅ | 版本**单一来源** = `package.json`（`core.VERSION` 读它，CLI 不硬编码第二份）；`CHANGELOG.md` 含**错误模型复盘** |
| ⑦ | 统一日志 | ✅ | `~/dsh-collab/logs/dsh-plugin-reflect-dispatch.log`：每步 时间/输入/判断/结果；门失败与 `lean4-check` 结果**也留痕**（`--dry-run` 例外：为满足零变更，只在 stdout 打印） |
| ⑧ | 自动落链 | ✅ | 黑板 `data/registry/dsh-plugin-reflect-dispatch` 登记卡（`--register`，写后回读校验）+ 本 README + 与兄弟组件共用 `data/reflect/` 协议 |
| ⑨ | CLI 治理 | ✅ | `parseArgs` 严格（未知旗标/位置参数 → exit 2）；退出码 0/1/2 固定；`--dry-run` 零变更（lean4-check D 实测）；`--json` 合法完整；`--help` 自解释 |
| ⑩ | 约束前置·不可绕过 | ✅ | 见下节（13 条不该发生路径 × 四种门型 + `--lean4-check` A–F 六项） |

---

## 五、⑩ 结构门：13 条"不该发生路径"，全部结构上不可绕过

**本工具的不该发生路径（一句话）**：**假装派发了** —— 卡写进了盘（或根本没写）却称"已派发"；
以及跨设备后新生的两条：**跨设备污染**（A 设备的卡写进 B 设备目录）与**凭据跨设备扩散**（Φ12 形态④）。

| # | 不该发生的路径 | 门型 | 结构机制（不是"检查后放行"） |
|---|---|---|---|
| 1 | 假装派发（写了没送达 / 送达没验） | 入口门 | 发送路径只能 `PUT → 立即 GET → 规范化 JSON 语义比对`；任一不符 → `READBACK_MISMATCH` 中止 |
| 2 | 派给不存在的目标并静默跳过 | 入口门 | `assertTargetExists` 是 **void-or-throw**：**没有**可被 `continue` 消费的布尔返回值；`--agents` 任一未知 id 使整次失败 |
| 3 | 发送超 50 字的总线正文 | 类型锁 | 通知只能由 `buildNotice(boardKey)` 生成：模板冻结、键必须过 `data/reflect/<k>/<device>/<date>` 形状门；CLI 与工具**都没有** `--message` 之类的自由文本入参；`assertNotice` 再校验（≤50 且必须含黑板键） |
| 4 | 跨设备污染：A 设备的卡写进 B 设备段 | 类型锁 | `assertDeviceSegment` / `assertDeviceInPath`：键与落盘路径的 `<device>` 段必须**正好等于**卡片自己的 device，且 device 必须在本次解析出的设备集合内 |
| 5 | 未知/超长设备名 | 类型锁 | `DEVICE_NAME_RE = ^[a-z][a-z0-9-]{1,15}$`；>16 字直接拒绝（通知装不进 50 字预算，宁可在入口拒，绝不在发送时截断） |
| 6 | 凭据跨设备扩散（Φ12 形态④） | 类型锁 | 落盘与写板前对**最终文本**扫 9 类凭据形态 → 替换为 `[REDACTED:<kind>]`，只报形态与条数、**不回显原文**；幂等；lean4-check C 有 7 类样本 + 假阳性检查 |
| 7 | 把"离线待取"记成失败 | 类型锁 | `DEVICE_STATUS` 冻结枚举 `delivered/pending/local/failed`；`pending` 是合法终态 |
| 8 | 把补派记成当天（时点错） | 类型锁 | `assertNotLate`：处理过去的日期必须显式 `--allow-late`，否则拒绝（Φ13） |
| 9 | 广播 / 通配目标 | 类型锁 | `TARGET_TOKENS_FORBIDDEN`（`*`/`all`/`全部`…）命中即拒（定制与广播互斥） |
| 10 | dry-run 改盘 | 入口门 | dry-run 在任何写操作**之前**返回；连统一日志都不落盘 |
| 11 | 越界写盘（含 `../` 穿越） | 类型锁 | 写路径 `resolve` 后必须落在 `<home>/dsh-collab/data/reflect/` 前缀内，且设备段匹配 |
| 12 | 执行外部命令 / 连第三台黑板 | 类型锁 | `ALLOWED_COMMANDS` 冻结为**空** + 源码零 `child_process` 导入（**正面缺席证明**，替代"空集 ⊆ 允许"的空洞通过）；出站主机冻结 `BOARD_TARGETS` 两块板，**无环境变量入口** |
| 13 | 空事件流发套话卡 / 跳步派发 | Schema 门 + 状态机 | 单设备空流直接拒绝；多设备时"全部设备都没事件"才拒绝。状态机 `planned→carded→board_written→readback_ok→recorded`，没写黑板到不了 `readback_ok` |

### `--lean4-check` A–F 六项

| 项 | 证明内容 | 实测结果（2026-09-10） |
|---|---|---|
| A | 源码无危险原语 | 去注释/字符串/正则字面量后扫描：宽杀/任意命令执行/破坏性文件操作 **0**；`child_process` 导入 **0** |
| B | 负例全部被拒 | **41/41** 条被拒，覆盖 **25** 类错误码（含跨设备写 / 设备名非法 / 补派未授权 / 键形状非法 / 跳步迁移） |
| C | 正例可用 | **20/20** 通过（含 ★ 脱敏 7 类样本 + 假阳性检查、三件套 key、设备段匹配、状态机完整链） |
| D | `--dry-run` 零变更 | 卡目录树 / 统一日志 mtime / **中央板探针键** 三者前后完全一致；dry-run 算出 1 张卡 + 1 个待 PUT 设备卡 + 3 个待写文件但全部未落盘 |
| E | 白名单冻结 | `ALLOWED_COMMANDS`/`ALLOWED_HOSTS`/`BOARD_TARGETS`/`CANDIDATE_DEVICES`/`DEVICE_STATUS`/`SUGGESTION_TYPES`/`DISPATCH_STATES|TRANSITIONS`/`TARGET_TOKENS_FORBIDDEN`/`SECRET_PATTERNS`/`GATE_META` 全部 `Object.isFrozen=true` |
| F | 命令与主机白名单 | exec/spawn/fork 执行点 **0** 个 + `child_process` 导入 0 处（正面缺席证明）；出站主机字面量 **2** 个 = `[127.0.0.1:8792, 106.53.214.108:8792]` ⊆ 允许集，**无第三处** |

---

## 六、跨设备层（v1.1 · 设计文档 §10）

### 6.1 事件源从"本机"扩到"全设备"

- 优先读**中央黑板** `data/reflect/events/<device>/<date>`（`106.53.214.108:8792`）
- `--local-only` 退回只读本机 `--events <path>`
- **设备枚举**（顺序固定，且**实际用了哪一条会写进结果/台账/卡片**）：

  1. `--devices mac-mini,mbp,i9` 显式指定
  2. **前缀列举**：`GET /data/?limit=2000` 取回整个 `data` 命名空间 → 过滤 `data/reflect/events/<device>/` 段
     - ⚠️ 该接口**不做前缀过滤**（早先实测 `GET /data/reflect/events/` 返回整个 `data` 命名空间，约 15MB / 72 键；`?limit=` 只是截断）
     - 所以本工具**先判 `present === total`**：键集**完整**才按前缀过滤（此时有效，实测能发现 `rc-test` 这类我没硬编码的设备）；**被截断就整条弃用**，改走探测
  3. `data/reflect/devices` 索引键（协议面，由各设备 collect 维护）
  4. **探测**：冻结候选 `[mac-mini, mbp, lab-mbp, i9]` ∪ 上面两步发现的设备，逐个 `GET events 键` 判 200/404
  5. 兜底：只处理本机

- 设备候选集**对齐兄弟组件** `reflect-harvest` 的 `device_layer.devices` 实产（`mac-mini/mbp/lab-mbp/i9`），避免两套设备名分裂。

### 6.2 离线设备 = 待投递队列（`pending` ≠ `failed`）

设备离线**不是失败**：卡已落中央板，该设备上线自取即可。判定用**独立活性信号**：

| 信号 | 取值 | 参与判定 |
|---|---|---|
| 本机设备 | `true` | ✅ 直接在场 |
| 发现层心跳 `data/discovery/agents/<device>` | `ageSec < 90` | ✅ 在场（R-ERR4 口径） |
| `--assume-online <devices>` | 人工声明 | ✅ 在场（声明会记入台账，不静默） |
| 当天有事件键 | 有/无 | ❌ **不参与**（它与"有卡可发"是同一条件，用它判在线就是同义反复 —— 设备当晚可能早就关机了）；仅作背景信息记录 |

台账按状态分别记录时点（**Φ13 证据有时点**）：`delivered` → `deliveredAt`；`pending` → `pendingSince`；另外 `cardGeneratedAt / cardWrittenAt / cardReadbackAt / boardWrittenAt / boardReadbackAt` 全程留痕。

### 6.3 卡片新增的**设备维度**与第 5 问

> 跨设备复现是**比同机复现更强的信号**：不同设备跑的是不同任务、看的是不同上下文，它们**独立**踩到同一个坑 → 这不是某条工作流的偶然，而是**系统性的**（§10.7）。

- 卡头：`# 🎴 反思卡 · <device>:<短键> · <date>`，并标设备视角与来源（`local-file` / `central-board`）
- **Q5（新增）**：这个坑在你的设备/环境下是**普遍的**，还是**特定于你这边**？三选一 `普遍 / 仅本设备 / 不确定`
- 且 Q5 **不是空问句**：卡里会印出**实测到的跨设备线索**（"你的事件特征词在 N 台别的设备上出现了 M 条事件，例 M003，依据 `price-analysis.js`"）；
  没探测到时也**明确写清"没读到 ≠ 不存在"**，并提示"不要因为只有我就默认选仅本设备"
- 回填 schema 相应新增：`device` / `origin_device`（**采集者**，不是"文件在哪"）/ `device_scope` / `plugin_version`（供 harvest 检出设备间版本漂移）/ `evidence.collected_at`（与 `ts` **分开标**）

### 6.4 跨设备的安全

- **不跨设备写别人的目录**：键与落盘路径的 `<device>` 段必须等于卡片自己的 device（门 4）
- **凭据不得跨设备扩散**：落盘/写板前脱敏（门 6）。上游 `collect` 已带 `secrets_redacted`，本工具是**第二层**（纵深防御）
- **`origin_device` 对不上时卡片直接标红**：`⚠️origin=<设备>` + 一行说明"是别处采集、经同步盘/黑板可见的，别算成你这边发生的事"

---

## 七、坑（全部有实据，前 6 条是 R006 §6 的现场复现）

| # | 坑 | 表现 | 修法 |
|---|---|---|---|
| 1 | **门太宽砍掉自己人** | `assertDeviceInPath` 取了相对路径第 0 段（`cards`）当设备名 → **所有**合法落盘都被判跨设备写 | 取第 1 段并显式校验形状（`<cards\|events\|answers>/<device>/<...>`） |
| 2 | **检查器误伤自己 / 假阳性** | 源码扫描把检测用的正则与帮助文本当靶子 | `stripLiterals` 先去注释/字符串/正则字面量再扫 |
| 3 | **空洞通过** | 剥字面量后读不到实参 → 执行点枚举 0 → "0 ⊆ 允许"通过 | 去字面量定位 + 回原文读实参；**并用"源码无 `child_process` 导入"做正面缺席证明**替代空集断言 |
| 4 | **假失败** | 回读比对用字符比对，黑板重排键序 → 成功被判失败 | 改规范化 JSON **语义比对**；另：放弃前做一次复核（日志里 `selfHeal` 类逻辑同理） |
| 5 | **时点混乱** | 设备间时钟不同步；"上报过事件"被当成"此刻在线" | `ts` 与 `collected_at` 分开标（Φ13）；在场判定与"有没有事件"解耦 |
| 6 | **检查报错原因** | 把"黑板 404（尚未上报）"报成"该设备没有事件" | 三态语义分清：`400`=键写法非法 / `404`=格式合法但不存在 / `200`=存在；**不合并成一个布尔** |
| 7 | **自己的结论下得太重** | `--list-check` 初版一口断定"黑板不支持前缀列举"，实测 `limit ≥ total` 时键集完整、按前缀过滤**是有效的** | 结论改为"接口不做前缀过滤，但**先判完整性**再决定用不用"，并写进 `--list-check` 与 selfcheck |
| 8 | **`process.exit` 截断管道输出** | `--json` 输出 628KB 时尾部丢失 → 下游 JSON 解析失败 | `out()` 改 `fs.writeSync(1, …)` 同步写 |
| 9 | **两处版本** | CLI 打印与包版本漂移 | 版本单一来源（`package.json`） |
| 11 | **单段键被判合法**（`data` → 我的正则说 OK，黑板 `PUT /data` → **400**） | 与 `bb-write.py` 交叉验证（同一批键 × 两套校验器 × 黑板真实码）时抓出 | `BB_KEY_RE` 收紧：至少两段 + 后续段字符集 `[A-Za-z0-9._-]`；新错误码 `BB_KEY_NOT_A_KEY` |
| 10 | **空壳键当成"有内容"**（键在但 `value={}`） | 司库 R003 补充通告（2026-09-11 第③条）指出"纯状态码校验会漏"；自查实测确认本工具**读路径确有此漏**：PUT `{}` → 200 且有 `ts`/`version`，而 `probeKey().exists === true`，会被当成"该设备当天上报过事件" | `gate.isEmptyShell()` + `probeKey` 的 `exists` 改**内容口径**（同时返回 `httpStatus200`/`emptyShell`）；`assertReadback` 增 `READBACK_EMPTY_SHELL`；`--devices-status` 增"空壳"档 |

---

## 八、复现命令（可复制即用）

```bash
# 1) 自查门 + 能力边界（②③④）—— 期望 exit 0
node cli.js --selfcheck

# 2) 结构门自证（⑩）—— 期望 A–F 全绿、exit 0
node cli.js --lean4-check

# 3) 版本与零变更（⑥⑨）
node cli.js --tool-version                 # 需与 package.json 一致
node cli.js --events <events.json> --local-only --date <YYYY-MM-DD> --allow-late --dry-run

# 4) 补派门（反例）：不加 --allow-late 处理过去的日期 → 期望 exit 1
node cli.js --events <events.json> --local-only --date 2026-09-10 --dry-run; echo $?

# 5) 用法门（反例）：未知旗标 → 期望 exit 2
node cli.js --bogus-flag; echo $?

# 6) 跨设备：只读看三件套键的存在性
node cli.js --devices-status --date 2026-09-10
node cli.js --list-check

# 7) 跨设备：出卡 + 派发（PUT 中央板 + 回读校验）
node cli.js --events <events.json> --devices mac-mini,mbp --send --date <YYYY-MM-DD> --allow-late

# 7.5) R003 合规：key 语法门 + 空壳键内容口径（通告 2026-09-11 第③条）
node --input-type=module -e "import {assertBoardKey} from './lib/gate.js'; try{assertBoardKey('cld-health/x')}catch(e){console.log('应拒 →',e.code)}"
node cli.js --devices-status --date <YYYY-MM-DD>   # 200 有内容 / 空壳 / 404 / 400 四态分列

# 8) 落链
node cli.js --register
curl -s http://127.0.0.1:8792/data/registry/dsh-plugin-reflect-dispatch | head -c 300
```

**自测夹具**：`~/dsh-collab/data/reflect/fixtures/events-20260910.json`（3 个真实目标 / 10 条事件，含 1 条故意无人认领的 `E010`）。
跨设备自测用的 mbp 事件流写在中央板 `data/reflect/events/mbp/2026-09-10`（**测试数据，带 `_fixture` 标记**；清理：`curl -X DELETE` 同键）。

---

## 九、与相邻组件的关系

| 组件 | 关系 |
|---|---|
| `reflect-collect`（①） | 上游。本工具消费它的产出：含 `id/source/ts/kind/path`+`collected_at`+`origin_device`；`path` 是**相对路径**（本工具按 `$HOME` 归一后与绝对路径资源比对） |
| `reflect-harvest`（③） | 下游。读 `data/reflect/answers/<device>/<date>/`；设备集合与本工具对齐；缺设备标 `pending` 而非 `missing` |
| `reflect-synthesize`（④） | 下游。复现计数按 `<device>:<agent>` 聚合 —— 本工具的 Q5 答案（`device_scope`）是它区分"跨设备复现"与"同机复现"的关键输入 |
| `reflect-enroll`（⑤） | 下游。本工具的 `suggestion.type`（冻结四选一）是它的入册分类输入 |
| R035 / Φ12 / Φ13 / R003 / R030 | 见 §一、§五；本工具是 Φ12 `device_gates`（落盘端 scrub）与 Φ13（双时点）的机器化落地 |
