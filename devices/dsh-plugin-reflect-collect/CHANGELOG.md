# CHANGELOG · dsh-plugin-reflect-collect

## v1.1.0 · 2026-09-11（跨设备层：上传中央黑板 + 回读校验 + 凭据脱敏 + 时点三件套）

**依据**：`docs/daily-reflection-pipeline-design-v1.md` §10（用户指令：「包括星桥外联出去的其他设备上的智能体，也应该加入这个思考，去把它们的事件和经验吸收回来」）+ 用户追加强制要求（4 条）。

### 新增
1. **`--device <name>`**：默认取 `os.hostname()` 短名过**冻结别名表**（本机 `CoreydeMac-mini.local` → `mac-mini`）。**动机是实测的**：兄弟环节已在用 `data/reflect/{cards,answers}/mac-mini/`，若用裸主机名会让跨设备 key 段对不上。
2. **跨设备上传**：`PUT http://106.53.214.108:8792/data/reflect/events/<device>/<date>`，唯一写点（origin 冻结、路径正则、device/date 各自过门）；`--no-upload` 可跳过。
3. **★ 回读校验**：PUT → GET 同 key → **规范化 JSON sha256** 一致 + 卡片 `key` 一致；任一不成立即 `ok:false`、日志 `result=fail`、**exit 1**。
4. **★ 落盘/上传前凭据扫描**：6 类形态，命中即 `[REDACTED]` 并写 `secrets_redacted`；`--allow-secrets` 才原样（仅调试）。
5. **★ 事件时点三件套**：`ts`（设备本地时间 + 显式时区偏移）/ `collected_at`（采集时刻 UTC）/ `origin_device`（采集者）；顶层加 `device` / `hostname` / `plugin_version`。唯一打点入口 `stampEvents()` + 逐条门检 `assertEventStamped()`。
6. **⑩ 门升级**：`assertBoardUpload`（三条件）/ `assertReadTarget`（读白名单：环回 `/data/ /notes/`，中央仅 `/data/reflect/`）/ 凭据形态矩阵 / 时点门 / 回读判据门；`--lean4-check` A 项扩为"除唯一写入模块外**全包**零写入原语"，F 项扩为"写入点 + 命令 + `http.request` + 读门 + 上传门 + `httpPutJson` 调用点"六类白名单。
7. **默认产出名按用法分流**：五源全开 → `events-<YYYYMMDD>.json`（规格）；部分源 → `events-<YYYYMMDD>-<源名>.json`（防覆盖当天全量）。
8. 新增模块：`lib/transport.js`（唯一 HTTP 模块，GET/PUT 两个方法各自绑定一个门）、`lib/upload.js`（唯一上传模块）、`lib/version.js`（零依赖版本读取）。

### 纠错复盘（每条都有实测证据；"检查本身会撒谎"是这一版的主题）
| # | 错误 | 证据 | 修正 |
|---|---|---|---|
| 1 | **凭据扫描门太宽，会先毁掉事件流** | 初版通用"40+ base64"与朴素 `[a-z0-9]{4}-{4}-{4}` 在 2026-09-10 真实事件流（1747 条）上命中 12 处，全是文件名/UUID（`flowernet-tech-path-moat-revision-v1.md`、`664ce0d2-2ef1-4a68-b1d4-b86209009911`、`laodeng-app-arch-v1_0-20260903-100236.svg`、`cloudbase-plan-push-task`） | 加段级谓词（三段每段含字母+数字）+ 前后边界排除 UUID/路径片段 + **"必须保留"语料 10/10 回归**；刻意不抓 ≥32 位 hex 与通用高熵串 |
| 2 | **假失败**：回读比对用"原文 sha256"，**永远不可能相等** | 黑板存为卡片信封 `{key,ts,value,version}` 且重新序列化：原文 `82445f1565a3…` vs 回读 `c3087fc6d467…`，规范化后两侧同为 `9ac34f97ec63…` | 判据改为**规范化 JSON** sha256；原文 sha 降为诊断字段 |
| 3 | **假失败**：自查 baseDir 写成 `HERE/..` | `--selfcheck` 报"源文件不可读: cli.js（ENOENT …/devices/cli.js）"，而 cli.js 一直在包里 | baseDir=包根；"文件不存在"类报错先怀疑**查的目录** |
| 4 | **空集通过**：写入调用点枚举成 0，仍判"⊆ 白名单"通过 | 正则 `(?<![\w.$])` 排除了 `.`，而本包写入写作 `fs.writeFileSync(...)` → 枚举 0 | 允许 `fs.` 前缀；F 项每个白名单断言**枚举数 > 0** |
| 5 | **扫描器误伤自己** | A 项 `includes('exec(')` 把本模块 `callRe.exec(code)` 当 shell 调用（9 处假阳性）；HTTP 方法扫描把 `method: m[1]` 当方法名 | 危险原语改带前缀否定正则；方法扫描改"去字面量定位 → 回原文读实参" |
| 6 | **白名单下标引用漂移** | `ALLOWED_GIT_ARG_PREFIXES[3]` 取 pretty 模板，白名单插入一项后实参变 `--pretty=o`，被门当场拒 | 同源构造器 `buildGitLogArgs()` + `GIT_LOG_PRETTY` 冻结常量 |
| 7 | **入口返回值看错**：`assertWriteAllowed(x).path` 是**规则路径**不是目标 | `outPath` 变成 `data/reflect` → `mkdirp(data)` 被白名单拒 → exit 2 | 门只做判定；目标用 `path.resolve(入参)` |
| 8 | **版本读取耦合宿主**：CLI 从 `lib/index.js` 取版本 → 无宿主环境 `ERR_MODULE_NOT_FOUND`（连 `--tool-version` 都跑不了，违反 ③） | 非登录 shell（PATH 无 node）下实测崩溃 | 版本读取下沉 `lib/version.js`（仍只读 package.json） |
| 9 | **插件 output schema 编译失败**：嵌套 `{type:'object'}` 未写 `additionalProperties` | `defineTool` 抛 `JsonSchemaError: UNSUPPORTED_SCHEMA`（apply 阶段即崩） | 嵌套 object/array 显式标注；**此类问题只有真跑 `apply()` 才发现** |
| 10 | **插件入口缺窗口归一**：`execute()` 直传字符串 → `since.ms` undefined、窗口过滤失效 | 冒烟测试报 `Cannot read properties of undefined (reading 'slice')` | 归一动作下沉到 `collectAll` 唯一入口 |
| 11 | **本机黑板 35MB 全量列举** 使每次自检多花约 1s 带宽 | 实测 `GET /data/` = 34.8MB / 20140 键 | 保留（诊断价值 > 成本），并在 `--selfcheck` 打印字节数以便察觉劣化 |
| 13 | **部分源运行覆盖当天全量产出** | `--out` 默认名只含日期：`--no-files --no-board …` 跑一次把当天 1779 条全量文件覆盖成 55 条；验证过程中**同一坑又踩一次**（424 条 → logs-only 61KB） | 默认名按用法分流（五源全开 → `events-<date>.json`；部分源 → `events-<date>-<源名>.json` + stderr 提示），并把该坑从"文档附注"升为正式坑条目 |
| 12 | **④ 版本自适应假达标：peer 声明解析不上**（最容易"看起来达标"的一项） | 初版照抄参考实现写 `"@deepseek-ai/dsh-tools": "^0.1.0-rc.6"`，而运行时是 `0.1.1-rc.2`。用 npm 的 semver 实测：`^0.1.0-rc.6`→**false**、`^0.1.0-rc.1`→false、`>=0.1.0-rc.1 <1.0.0`→false、`>=0.1.0-rc.1 <1.0.0-0`→false、`*`→**false**（预发布版本只被"同 major.minor.patch 且带预发布"的比较器满足）；实测可用：`>=0.1.1-rc.1 <1.0.0-0`→true | ① 声明改为 `>=0.1.1-rc.1 <1.0.0-0`；② 新增 `peerSatisfies()`（包内零依赖最小 semver，仅覆盖本包声明的 5 种形态，其它形态明确 unsupported）+ `--selfcheck` 打印"被解析到的版本 + 声明 + 判定结果"，把"peer 是否真的被解析"从**宣称**变成**机械判定**；③ 补 10 条 peer-range 负例（含参考实现的写法本身作为反例） |

### 实测（本版交付时）
- `--lean4-check`：A–F **全绿**（B 项 110 条负例 + 凭据矩阵 11/11 脱敏、10/10 保留）。
- `--dry-run`：本进程落盘 0 次、PUT 0 次；**独立快照**（统一日志 stat / `data/reflect` 列表 / 两采集根全量指纹 / 中央 2 个 key 内容 sha256）前后一致；期间唯一变化的文件是第三方写入的 `~/dsh-collab/token-monitor/blackboard/audit.jsonl`（非本进程）。
- 上传 + 回读：`mac-mini/2026-09-10`（1692 条）与 `mac-mini/2026-09-11`（291 条）PUT 200 + 回读 200 + 规范化 sha256 一致；隔离测试 key `rc-test/2026-09-10` 用 curl 独立复核一致（`47eefb70df49…`）。
- 凭据脱敏端到端：造 3 处假凭据的临时日志 → `secrets_redacted=3`，产出中 3 处全为 `[REDACTED]`、sha256 与文件名**未被误伤**；测试用临时日志已删除（**由智能体删除——工具本身无删除能力**）。

## v1.1.3 · 2026-09-11（采纳 R003 v3 统一操作建议：黑板枚举改**有界分页**）

**依据**：R003 补充通告 **v3**（HR，2026-09-11 01:00）新增「探活/枚举必须带 `?limit=N`」统一操作建议（触发者正是本工具自陈的"探一次下拉 36.59MB"）。

### 变更
1. `board` 源的命名空间枚举从**单次全量 GET** 改为**有界分页**：`limit=BOARD_PAGE_SIZE(2000，冻结)` + `offset` 递进，并用响应里的 `total` 判定是否取完；上限 `BOARD_MAX_KEYS(200000，冻结)`。
   - 实测：单页 **386KB–2.41MB**（原为 36.6MB 一次）；本机 `/data/` 20,224 键 → **11 页**、`/notes/` 13,531 键 → **7 页**，共 **18 次 GET**；`board` 当日卡数 189 条（与改造前一致，无丢卡）。
   - **截断不静默**：`offset < total` 或触上限 → 写 `errors[]`（`kind: limit`）并给出 total/已取键数/页数。
   - **诚实说明（不夸大）**：分页降的是**单次响应峰值**与**失败面**（一页失败只丢一页且留痕），**总字节数基本不变**（43.76MB → 43.79MB）；要真正降总流量需服务端支持按 `ts`/前缀过滤（实测当前不支持）。
2. 探活继续使用 `GET /data/?limit=1`（120 字节）；存在性判定一律精确 key GET。
3. `E 白名单冻结` 增加分页常量（`BOARD_PAGE_SIZE` / `BOARD_MAX_KEYS`）；`--selfcheck` ① 增一行"枚举=有界分页"。

## v1.1.2 · 2026-09-11（② 加第 ④ 段「真挂载冒烟」+ 上游字段契约实测确认）

### 新增
1. **`--selfcheck` 第 ④ 段：真挂载冒烟** —— `import lib/index.js` + 桩 ctx 调 `apply()`，数注册了几个工具并校验工具形状（name/description/parameters/execute）与 `inject` 含 `'tools'`。**peer 解析不到时如实标「跳过」而非「通过」**（环境问题 ≠ 包问题，退出码不受影响）。结果并入 `.selfcheck/reflect-collect.json`。
   - 六条分支**全部实测**：真实挂载 `passed`(registered=1) / peer 解析不到 `skipped`+原因原文 / 导入期失败 `failed@import` / 缺 apply `failed@shape` / **apply 抛错 `failed@apply`（能原样透出 `JsonSchemaError: UNSUPPORTED_SCHEMA`）** / 注册 0 个工具 `failed@assert`（不被 try/catch 吞）。
   - 防递归：模块级 `inSmoke` 闸门；宿主内不自动跑（宿主调 apply 那一刻本身就是真挂载），仅 `--selfcheck` 显式启用。
2. **`--selfcheck` 第 ⑤ 段：自证摘要**（结构门负/正例数、凭据矩阵、冻结白名单计数、唯一模块）。
3. `docs/README.md` 新增「跨设备字段契约（上游协议）」章节：把 harvest/dispatch 依赖的字段与路径**逐条实测确认**（1692 条事件缺 `collected_at`=0、缺 `origin_device`=0；顶层 `device/hostname/plugin_version` 齐；上传 key 形态与首段语法合规）。

### 实测（本轮）
- `--selfcheck` exit 0（五段全绿；④ 真挂载=passed，registered=1，期望工具 `reflect_collect` 命中）
- `--lean4-check` exit 0（A–F 全绿；负例 142 全拒 / 正例 41 全过）
- 心跳实测：`data/discovery/agents/mac-mini` **中央** HTTP 200（version=11634，2 秒前）· **本机 404** → 在场判定须查中央

## v1.1.1 · 2026-09-11（R003 补充通告 v2 采纳：键语法门 + 四态 key 状态 + 有界探活）

**依据**：黑板卡 `data/registry/r003-key-syntax-notice-20260911`（司库/HR，v2）。**先独立复测再采纳**（R030）。

### 新增
1. `assertBoardKeySyntax()`：首段 `[a-z]+` / 后续段 `[A-Za-z0-9._-]` / **禁空段（尾斜杠、双斜杠）** —— 由 `buildUploadKey()` 与 `assertBoardUpload()` 同时调用，非法 key 结构上构造不出来。负例矩阵 +16（全部取自实测 400 或静默降级形态），正例 +4。
2. `centralKeyState()` 从布尔升为**四态**：`present` / `absent(404)` / `bad-key(400)` / `unreachable`；`--selfcheck` 逐态标注，`bad-key` 出现即视为门漏。
3. `boardReachable()`：探活改**有界** —— `GET /data/?limit=1`（**120 字节**），替代原先探一次就下拉 36.59MB 全量列举的做法。

### 独立复测（我的数字 vs 通告）
- 一致：首段大写 / 段内 `:` `+` `@` `~` `!` 空格 `%2F` → **400**；`a.b-c_d` → 404（格式合法）；400 与 404 语义不同。
- **修正 1**：**尾斜杠不是 400，而是 HTTP 200 + 全量列举**（`data/registry/`、`data/reflect/events/mac-mini/2026-09-10/` 均 200 / 36,589,877 B）⇒ "必须拒空段"是纯客户端义务，且会被"回读有内容=已落地"的判据**静默假通过**。
- **修正 2**：`data//registry` → **404**（不是 400），同样不报错。
- **修正 3**：陷阱不限于 reflect 路径（`/data/registry/` 亦然）；规模按实例差异极大且随时间增长 —— 本机 **36.59MB / 20,220 键**（通告记 34.88MB / 20,214；reflect 前缀键 13 个 vs 通告 11 个），中央 **15.95MB / 99 键**。
- rule_3（回读须到语义相等、必须规范化键序）与本工具 v1.1.0 的判据一致 —— 我在 v1.1.0 已因同一原因踩过"原文 sha256 假失败"（见纠错 #2）。

### 加固（读路径：本工具自己的门抓到自己的一处漏洞）
中央侧的读原来只校验"路径以 `/data/reflect/` 开头"→ **`GET http://106.53.214.108:8792/data/reflect/` 仍被放行**，而它正是"命名空间列举端点"（尾斜杠）。已收紧为：中央读**只能是精确 key 读**（过 `assertBoardKeySyntax`，尾斜杠一律拒）。新增 5 条 `read-target-trailing-slash` 负例锁定该形态（本机 `/data/registry/`、`/data/reflect/`，中央 `/data/registry/`、`/data/reflect/`、`/data/`）。
> 由**我自己的负例矩阵**当场抓出（第 142 条负例放行 1 条 → `--lean4-check` 立即报"门未生效"）。这就是"负例矩阵要能抓住自己"的价值。

### 实测
`--selfcheck` exit 0（③ 段显示中央 key `[present]`、本机探活 `120 字节`）；负例矩阵 **142 条全拒**、正例 **41 条全过**；`--lean4-check` A–F 全绿。

## v1.0.0 · 2026-09-11（首版：只读采集五源）
- 五源采集（files / board / tools / logs / git），各自独立开关；结构化事件流（`window/collected_at/counts/events/errors`）。
- ⑩ 结构门：本地写入目标白名单 3 条 + 采集内核零写入原语 + 采集根白名单 + `..`/软链双条件校验 + 自采样排除（自己的日志/产出/自查不进自己的采集结果）+ `--lean4-check` A–F 六项。
- ⑨ CLI：严格参数解析、退出码 0/1/2、`--dry-run` 零字节落盘（连日志都不写）、`--json`、`--summary`、`--help`。
- ⑦ 统一日志 `~/dsh-collab/logs/dsh-plugin-reflect-collect.log`（失败也留痕）。
- 同版确立：`logs` 源单文件读尾部 1MB / 单文件最多 50 条（超限进 `errors[]`）；`board` 源全量列举后按卡 `ts` 过滤；`git` 源非仓库则 `skipped` 并正常退出。
