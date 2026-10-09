# CHANGELOG · dsh-plugin-reflect-dispatch

## v1.1.2 · 2026-09-11（键语法收紧：与 bb-write.py 交叉验证抓出的双边漏点）

**触发**：司库广播「新工具 bb-write.py：黑板写入校验（写前查 key 语法 + 回读验证非空，防 400 伪装/空壳键）」。
我做的是**交叉验证**（不是读一遍就点头）：把两套校验器放在**同一批键**上跑，再拿**黑板真实响应**当裁判。

### 方法
12 个键 × 三列对照：`bb-write.py validate_key` / 我的 `BB_KEY_RE` / **真实 `PUT` 的 HTTP 码**。凡"校验说 OK 而 board≠200"即漏点。

### 结果：**两边各有一个漏点，都在"写前说 OK、实际被拒"这一类**（即 bb-write.py 自己要防的那个陷阱）

| 键盘 | bb-write | 我（修前） | board 实测 | 判定 |
|---|---|---|---|---|
| `data` | REJECT | **OK** | **400** | ★**我的漏点** |
| `data/x/a:b` | **OK** | REJECT | **400** | ★bb-write 漏点 |
| `data/x/a#b` | **OK** | REJECT | **400** | ★bb-write 漏点 |
| `data/x/y z` | **OK** | REJECT | 客户端报错 `URL can't contain control characters` | ★bb-write 漏点 |
| `data/x/中文` | **OK** | REJECT | 客户端 `'ascii' codec can't encode` | ★bb-write 漏点 |
| `data/reflect/__syn__/ok` | OK | OK | 200 | 一致 |
| `Data/x`、`data/` | REJECT | REJECT | 400 | 一致 |

- **bb-write 的口子**：`validate_key` 只约束**首段**，后续段任意 → 冒号/井号/空格/非 ASCII 全放行，随后 400 或客户端崩溃。
  已用其自带 CLI 复现：`bb-write.py validate data/x/a:b` → `OK 语法合法`；`bb-write.py put data/x/a:b --json '{"t":1}'` → `[put] X 400 bad key syntax …`，exit=2。
- **我的口子**：`BB_KEY_RE` 末尾是 `(...)*` → **单段键 `data` 被判合法**，而实测 `PUT /data` → **400**。

### 修正（我的侧）
`BB_KEY_RE` 收紧为 `/^[a-z]+\/[A-Za-z0-9._-]+(\/[A-Za-z0-9._-]+)*$/`：
1. **至少两段**（单段是"命名空间"不是键 → 新错误码 `BB_KEY_NOT_A_KEY`，消息里给出 `data/<域>/<键>` 写法）
2. 后续段字符集收口到 `[A-Za-z0-9._-]`（空格 / `:` / `#` / 非 ASCII 一律拒）
3. 首段斜杠归一（`/data/reflect/x` → `data/reflect/x`）
4. 门矩阵：B 增 **7** 条键语法负例；C 增 2 条正例
（单段形式只用于"按命名空间列举"的 GET，那条路径走 `board.listKeys` 的 `rawRequest`，不经过此门 —— 已核对 `assertBoardKey` 仅有 2 个调用点，均为完整键。）

### 交叉验证的另一半：**对方工具认证我的产出**
`bb-write.py get data/reflect/cards/{mac-mini,mbp}/2026-09-10 --server central` → **exit 0 且内容非空**；
`bb-write.py get data/registry/dsh-plugin-reflect-dispatch --server local` → **exit 0**。
→ 我写的卡与登记卡能被独立实现的第三方校验器读通（不是自说自话）。

### 有意思的收敛
bb-write v1.0.2 的修法与我的**独立相同**：黑板服务端对嵌套对象做键排序（serde_json 无 preserve_order），
所以 `str()` 比对会把"键序不同但内容相同"判成不符 → 假阳性；两边都改成了**规范化 JSON 深比对**（他们 `json.dumps(sort_keys=True)`，我 `canonicalJson`）。

## v1.1.1 · 2026-09-11（合规加固：R003 黑板写规范补充通告）

**触发**：司库广播「看黑板 data/registry/r003-key-syntax-notice-20260911（R003 补充：key 首段须纯小写字母；400=键错/404=不存在；写入必回读）」。
逐条对照 → **第 1、2 条本工具已达标；第 3 条（空壳键）的读路径有漏，已修**。

### 逐条对照与实测
| 通告条款 | 本工具现状 | 证据 |
|---|---|---|
| ① key 首段命名空间必须 `[a-z]+` | ✅ 早有硬门 | `BB_KEY_RE = /^[a-z]+(\/[A-Za-z0-9._\-]+)*$/`；实测放行 `data/reflect/cards/mac-mini/2026-09-10`，拒绝 `cld-health/foo`、`mac-mini/x`、`i9/x`、`foo_bar/x`、`abc123/x`、`ABC/x`（均 `BB_KEY_INVALID`） |
| ② 400=写法非法 / 404=不存在，不可合并 | ✅ 三态分明 | `probeKey` 返回 `status`；`putAndVerify` 非 200 抛 `BB_WRITE_REJECTED` 并注明"400=键写法非法 / 404=路径不存在"；`--devices-status` 逐设备打印 200/404/400 |
| ③ **空壳键**：键在但 `value={}`，纯状态码校验会漏 | ❌ **读路径有漏 → 已修** | 实测：某键 PUT `{}` → 200、有 `ts`/`version`，而 `probeKey().exists===true`（**误判为"该设备当天上报过"**）；`--devices-status` 显示 `200` |

### 修正
1. 新增 `gate.isEmptyShell(v)`：`null/undefined`、`{}`、`[]`、纯空白串 → 空壳（内容口径）。
2. `board.probeKey` 的 `exists` 改为**内容口径**（`200 且非空`），并**同时**返回 `httpStatus200` 与 `emptyShell` —— 谁用哪个口径是显式的，不靠猜。受影响的三处业务判定（设备发现 / 在场判定 `reportedToday` / `--devices-status`）自动继承修正。
3. `assertReadback` 新增独立错误码 `READBACK_EMPTY_SHELL`（此前会落到泛化的 `READBACK_MISMATCH`，能拦住但**说不清是空壳**；现在错误信息直接点名 R003 第③条）。
4. `--devices-status` 增加 `空壳` 档（四态：200 有内容 / 空壳 / 404 / 400）。
5. 门矩阵：B 增 3 条空壳负例（`{}`、`[]`、空白串）；C 增 1 条 9 组口径正例。

### 实测（修后）
- 空壳键：`exists=false`、`httpStatus200=true`、`emptyShell=true`；`assertReadback({...}, {})` → `READBACK_EMPTY_SHELL` ✅
- 回归（门不能做太紧）：`cards/mac-mini/2026-09-10` → `exists=true/emptyShell=false`；`events/emp/...` → `404/exists=false` 均正确
- `--lean4-check` A–F 仍全绿；自测键已 `DELETE` 清理（回读 404）

## v1.1.0 · 2026-09-10（跨设备层：事件源扩到全设备 + 第 5 问 + 离线待投递队列）

**性质**：按用户指令扩到跨设备（设计文档 §10）。核心新增不是"多读几台机器"，
而是承认一个更强的事实：**不同设备独立踩同一个坑 = 系统性缺陷，不是某条工作流的偶然**。

### 新增
1. **事件源**：优先中央黑板 `data/reflect/events/<device>/<date>`，遍历设备；`--local-only` 退回本机；`--devices` 显式指定。
2. **设备枚举**：`--devices` → 前缀列举（**仅当键集完整**）→ `data/reflect/devices` 索引 → 冻结候选探测 → 兜底本机。
   **实际用了哪一条 + 它的局限**写进结果 / 台账 / `--devices-status` / selfcheck。
3. **卡片落盘多一层 device**：`cards/<device>/<短键>.md`（最新）+ `cards/<device>/<YYYYMMDD>/<短键>.md`（同日归档，补派不互相覆盖）+ `_device-card.md`（设备合并卡）+ `_index.json`。
4. **中央派发**：PUT `data/reflect/cards/<device>/<date>`（一设备一键，内含各 agent 段落）+ **立即回读校验**；回填去向改为 `data/reflect/answers/<device>/<date>`。
5. **离线语义**：目标设备不在场 → `status: pending`（离线待取），**不是** `failed`；`--allow-late` 支持 T+1/T+2 补派；台账按状态记录 `deliveredAt` / `pendingSince`。
6. **卡的第 5 问**：这个坑在你的设备/环境下是普遍的，还是特定于你这边？（`普遍 / 仅本设备 / 不确定`），并印出**实测到的跨设备线索**。
7. **回填 schema 扩展**：`device` / `origin_device` / `device_scope` / `plugin_version` / `evidence.collected_at`（与 `ts` 分开标）。
8. **凭据脱敏**（Φ12 `device_gates` 落盘端 scrub）：9 类形态，幂等，只报形态与条数不回显原文。
9. 新命令 `--devices-status`（三件套键三态探测）与 `--list-check`（黑板前缀列举实测结论）；新旗标 `--assume-online`。

### 门（⑩）新增 3 条不该发生路径
跨设备污染（键/路径的设备段必须等于卡片自己的 device）、设备名非法/超长、把"离线待取"记成失败 / 把补派记成当天。
`--lean4-check`：B 从 28 → **41** 条负例（25 类错误码）；C 从 12 → **20** 条正例（新增脱敏 7 类样本 + 假阳性检查、三件套 key、设备段匹配、补派门）。

### ★ 被自己的门 / 自审 / 真挂载冒烟抓到的 7 个错误（复盘，全部真实）

| # | 错误 | 谁抓到的 | 根因 / 修法 |
|---|---|---|---|
| 1 | **门太宽砍掉自己人**：`assertDeviceInPath` 取了相对路径第 0 段（`cards`）当设备名 → **所有**合法落盘被判跨设备写 | lean4-check C（正例被误拦） | R006 §6 坑 1 的现场复现。修：取第 1 段并显式校验 `<cards\|events\|answers>/<device>/<...>` 形状 |
| 2 | **脱敏不幂等**：第二轮把上一轮写下的 `token=[REDACTED:github-token]` 又当成"token=某值"替换一次（openai-key / github-token / kv-secret 三类失败） | lean4-check C（幂等断言） | 修：赋值类模式加 `(?!\[REDACTED:)` 幂等守卫 |
| 3 | **同义反复的在场判定**：初版把"当天上报过事件"也算"在线"，而那与"有卡可发"是**同一条件** → `pending` 分支**永不可达**，设计文档 §10.4 待投递队列形同虚设 | 自审推演 | 事件是 collect 一次性上传的，设备当晚可能早就关机。修：改用独立活性信号（心跳 <90s / `--assume-online`），三个信号分开记录 |
| 4 | **`--json` 尾部被截断**：`process.stdout.write` 异步 + 紧跟 `process.exit()` + 输出 628KB + stdout 是管道 → 下游拿到截断 JSON | 自测时 JSON 解析报 `Unterminated string` | 修：`out()` 改 `fs.writeSync(1, …)` 同步写 |
| 5 | **回读比对做成了字符比对 → 假失败** | 跨设备 PUT 首次运行（`READBACK_MISMATCH`，但两侧长度都是 1316 字节） | 黑板会**重排 JSON 键序**。修：改规范化 JSON（递归排序键）**语义比对**——R006 §6 坑 4「假失败」 |
| 6 | **自己的结论下得太重**：`--list-check` 一口断定"黑板不支持前缀列举" | 复跑时发现 `limit=500` 已返回全部 70 键，`present === total` | 接口确实**不做前缀过滤**，但键集**完整**时按前缀过滤有效（实测据此发现了没硬编码的 `rc-test`）。修：先判 `complete` 再决定用不用，结论与 selfcheck 文案同步更正 |
| 7 | **插件 apply 阶段就崩（最严重的一条）**：输出 schema 的嵌套对象漏写 `additionalProperties` → `dsh-tools` 抛 `UNSUPPORTED_SCHEMA` | **真挂载冒烟**（临时软链 profile 的 `node_modules/@deepseek-ai` 后 `import lib/index.js` 并调 `apply()`） | 正是 R006 §1「插件 apply 阶段 ReferenceError，启动即崩，靠外部 restart-guard 事后发现」那一类。修：输出 schema 统一用 `obj()` 构造器（漏写变得不可能）；并把「挂载冒烟」固化为 `--selfcheck` 第 ⑤ 节（peer 解析不到时**如实说跳过**，绝不假装通过） |

### 与兄弟组件的对接修正（对接到真实产出后的三处）
- **档案路径**：`~/.dsh-agent-bus.json` 是 2026-08-17 的停更快照（17 条），真正在用的是 `~/.dsh/agent-bus.json`（63 条）。修：新→旧→镜像→黑板，并把**实际用的文件路径**写进结果与卡片。
- **相对 vs 绝对路径**：`collect` 产出的 `path` 是**相对路径**，profile 的 `resources` 多为绝对路径 → 精确/前缀规则全不命中。修：绝对路径按 `$HOME` 归一成相对尾部再比。
- **设备集合**：对齐 `harvest` 的 `device_layer.devices` 实产 `[mac-mini, mbp, lab-mbp, i9]`（初版凭设计文档猜了 `iphone`）。

### 质量修正（真实数据 1692 条上实测驱动）
- **容器资源降级**：`~/dsh-collab/` 命中 **842/1692（49.8%）**、`~/dsh-collab/scripts` 命中 271（16%）→ 卡片会退化成"别人的事"。加实测规则：命中 >10 条 **且** 占比 >5% → 判容器，层级 `dir→weak`（≤45 < 阈值 50），并把"你的资源太宽"**写进卡片**当可回填观察。
- **层级裁决** `specific > dir > weak`：精确归属存在时不再向下兼容；被压下的候选记入 `suppressed` 并写进卡片（不静默跳到 0）。
- 效果：单个目标最多归属事件数 271 → 74（1692 条事件集上）。

---

## v1.0.0 · 2026-09-10（首版）

- 起因：用户指出「每日反思」若发**统一问卷**，智能体必然写套话；卡片必须按**它当天真正做了什么**定制。
- 首版实现：读本机 `events-<date>.json` → 按 `agent_profiles` 的 `resources` 做归属判定（逐条给出 score+via）→ 生成定制卡（① 实摘 ② 4 问带上下文 ③ 证据要求 ④ 回填 JSON schema）→ 落盘 `cards/<日期>/<短键>.md`。
- 同版确立结构门：通知模板类型锁（≤50 字、无自由文本入参）+ 目标存在门（void-or-throw，不静默跳过）+ 黑板回读校验（R003）+ 写盘根前缀门 + 状态机 + `--lean4-check` A–F 六项。
- 首版自测被抓到的 2 个错误：假档案路径（旧 store）、标识符 `-`/`_` 不归一致 `im_sessions` 类事件漏判。
