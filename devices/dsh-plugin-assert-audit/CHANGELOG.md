# CHANGELOG · dsh-plugin-assert-audit

## v1.0.0 — 2026-10-01（星桥）

**动因**：手工审查一份 19 条断言套件（`~/dsh-collab/comm-server/agent-mailbox.py` 的 selftest），
查出 7 类问题，其中两类是**我自己的验证工具在骗我**。过程必须工具化。

### 新增
- `lib/gate.js`：⑩ 结构门。`VERDICT` 冻结闭集（**故意无 PASS/OK**）、`ALLOWED_COMMANDS=['python3','node']`、
  `stripLiterals`（先剥注释/字符串/正则再扫，防坑「扫描器误伤自己」）、`scanExecSites` 三态、`assertTmpContained`、负例/正例矩阵。
- `lib/audit.js`：枚举断言 / 空断言与探针型检测 / **同谓词多调用点覆盖检测** / 变异测试三态判定。
- `lib/selfcheck.js`：② 三段自检 + ① 第5项 **真挂载冒烟（pass/fail/skipped 三态分离）**。
- `lib/index.js`：dsh 插件形态，注册 `assert_audit` 工具。
- `cli.js`：⑨ CLI 治理（`--selfcheck` / `--lean4-check` / `--tool-version` / `--dry-run` / `--json`）。

### 错误模型复盘（本次自查自纠，全部为实测）

| # | 我犯的错 | 怎么发现的 | 修法 |
|---|---|---|---|
| E1 | `parameters` 包了一层 `{type:'object',properties}` → `defineTool` 抛 `parameters.type must be a value schema object` → **apply() 崩、插件挂不上** | **①-5 真挂载冒烟**（其它九项当时全绿） | 改为扁平 properties 表。**这正是该项存在的理由**：九项全绿而交付物在运行时不存在 |
| E2 | `assertTmpContained` 用字符串 `startsWith` → `/tmp/../etc/hosts` **以 `/tmp/` 开头 ⇒ 假通过** | **B 项负例**（18 条里 1 条未拒） | 先 `path.resolve` 消解 `..` 再比较 |
| E3 | `scanExecSites` 读不到字面量时按「0 个坏命令」通过（**空集通过**） | **F 项**报 `UNRESOLVED` | 三态：literal / variable-guarded / **UNRESOLVED 判红** |
| E4 | F 项只允许 `lib/audit.js` 写入，但 ⑦ 统一日志**必须**写 `cli.js` → 门太宽把法定行为也拦了 | F 项自证失败 | 允许**两处**写入面：tmp 门控的变异体写 + **固定路径**日志（并机械断言日志行使用常量 `LOG`） |
| E5 | 手工变异测试把「变异体语法错/绑定数错」判成「存活」→ **审查结论会反向** | 逐条复跑两个「存活」变异体，发现它们根本没跑起来 | 三态判定 + 锚点唯一性检查 + 闭集内无 PASS |

### 已知边界（不掩盖）
- 多调用点覆盖检测是**启发式**（同谓词计数 + 套件提及次数），**不构成覆盖完整性证明**。
- `WEAK_COMPARE` 为**诊断输出**而非判决。
- 未做跨进程并发形态的验证（由被测套件自身负责）。

## v1.1.0 — 2026-10-01（星桥）

**动因**：用户指出「审查对象好像没包含 node-bridge」。**用户正确**——我审了自己新写的代码，
却漏审了那个**已造成三次生产事故**的组件。偏差确认：**倾向审「我新写的」和「我刚碰过的」，
漏掉「有事故史但不热」的**；而「已被 log-guard 兜住」被误当成了「已被审计」。

### 新增：范围审查模式 `--scope`
- `lib/scope.js`：多源发现（进程/launchd/profile 依赖/文件系统）→ 范围归类 → **覆盖三态判定** → 盲区排序
- **三态 + 不可判**：`COVERED` / `HAS_TESTS_NO_AUDIT` / `NO_TESTS` / **`UNKNOWN`（不折算为任一侧）**
- **自述盲区**：工具必须报出「我这一类看不见什么」（外部设备组件、无源码的二进制、模式表外的新组件）
- ⑩ 新增 **G 项**：`DENIED_SUBCOMMANDS` 冻结扫描（本工具只做只读盘点，不得获得 `bootstrap`/`bootout`/`enable` 等可变能力）
- `ALLOWED_COMMANDS` 扩为 `[python3, node, ps, launchctl]`（后两者只读盘点；附冻结禁用子命令清单）

### 错误模型复盘（v1.1.0 自查自纠，全部实测）

| # | 我犯的错 | 怎么发现的 | 修法 |
|---|---|---|---|
| E6 | **门太宽**：`SCOPE_PATTERNS` 含裸 `'session'` ⇒ 把 `nsurlsessiond`/`liveactivitiesd`/`nesessionmanager` 全收进来（R006 坑 #1） | 首跑输出人工复核 | 删裸词 + 新增**负向排除面** `EXCLUDE_PATTERNS` 并**先判** |
| E7 | **非源码载体被当组件**：`node-bridge.log` 入列 | 同上 | 排除面含 `.log/.bak/.json/.db` 等 |
| E8 | **同组件重复计**：launchd label 与进程名各算一个 | 同上 | `canonicalName()` 规范名去重 |
| E9 | ★ **贪婪正则**：`/^com\.[a-z0-9._-]*\./` 吃到**最后一个点** ⇒ `com.dsh.node-bridge.mac-mini` 被削成 `mac-mini` ⇒ **源码映射全挂不上，组件掉成 UNKNOWN** | **反控**（造审计记录看是否会翻 COVERED，结果匹配不到） | 改 `[a-z0-9-]+`；补 `canonicalName` 断言 |
| E10 | **源码映射按精确键** ⇒ 进程名 `node-bridge-macos-arm64-v1` 挂不上 `node-bridge` | 反控 | `SOURCE_MAP` 冻结表 + **最长 key 命中**（防 `blackboard` 吃掉 `bb-sub`） |

### 首跑结论（可能比工具本身更重要）
```
COVERED 0 · HAS_TESTS_NO_AUDIT 12 · NO_TESTS 18 · UNKNOWN 7
```
**整条 agent 会话/跨设备沟通工具链里，没有任何一个组件同时具备「测试 + 审计记录」。**

### 已知边界
- 范围模式表是**冻结白名单** ⇒ 名字不含任何模式的新组件会漏（需人工补模式，已在自述盲区里声明）
- `UNKNOWN` 来自「无源码映射」，**不折算**为已覆盖或未覆盖
- 覆盖判定的「有测试」是**计数启发式**（`#[test]` / `check(` / `assert(`），不等于测试有效——有效性归 `assert-audit` 模式管
