# dsh-plugin-assert-audit · v1.0.0

> **为什么需要**：断言套件自己会说谎。2026-10-01 我手工审查一份 19 条的断言套件，
> 在里面查出 **1 条恒真断言**、**1 条只看文件头的探针型空判据**、**3 处「同谓词多调用点只覆盖一个」**，
> 以及**我自己两处断言写错了性质**。更糟的是：**我的手工变异测试工具把「变异体崩溃」判成了「存活」**
> —— 那会让审查得出**反向结论**。这件事必须工具化，且工具必须**结构上不允许**犯这个错。

---

## 一、用法

```bash
cd ~/dsh-collab/devices/dsh-plugin-assert-audit
NODE=/opt/homebrew/bin/node          # 本机 node 不在 PATH，用绝对路径

# ① 能力边界自检 + 真挂载冒烟（三态）
$NODE cli.js --selfcheck

# ② R006 ⑩ 六项自证（A–F 全绿才交付）
$NODE cli.js --lean4-check

# ③ 版本（单一来源 = package.json）
$NODE cli.js --tool-version

# ④ 零变更演示（只枚举，不跑变异、不写文件）
$NODE cli.js --dry-run

# ⑤ 审计一个套件
$NODE cli.js \
  --source  <被测实现.py> \
  --tests   <断言套件.py|.js> \
  --token   '<谓词片段，可重复>' \
  --run-arg selftest \
  --runner  python3 \
  --mutants-json <变异体.json> \
  [--json]
```

**变异体 JSON 格式**：
```json
[{ "name": "M4 去掉 done 前置证明",
   "old":  "<源码中恰好出现 1 次的片段>",
   "new":  "<替换为>" }]
```
> 锚点出现次数 **≠ 1** ⇒ 该变异体直接判 `INCONCLUSIVE`，**不做替换**。
> （实测教训：同一 SQL 片段在 `claim()` 与 `inbox()` 各出现一次，`replace(...,1)` 只改中前者，
> 而会误判成「变异存活」——即覆盖有洞。工具把它变成不可判，逼人去对齐调用点。）

**退出码**：`0` 成功 · `1` 门失效 / 发现真存活或不可判或空断言 · `2` 用法或 IO 错误
**机器可读**：`--json`

---

## 二、三态判定（本工具存在的理由）

| 判定 | 含义 | 触发条件 |
|---|---|---|
| `CAUGHT` | 变异被断言捕获 | 有汇总行 **且** FAIL>0 |
| `SURVIVED` | **真存活 = 覆盖有洞** | 有汇总行 **且** FAIL=0 |
| `INCONCLUSIVE` | **不可判** | 无汇总行（套件崩了） **或** 出现 `SyntaxError`/`IndentationError`/`Incorrect number of bindings`/`ModuleNotFoundError` **或** 锚点出现次数≠1 |

**`INCONCLUSIVE` 既不算捕获也不算存活，且在汇总里单独计数**（三者互斥、合计必须等于总数；不一致即报严重）。

闭集里**故意没有 `PASS`/`OK`** —— 不是被拒绝，而是**语法上不存在那个值**（⑩ 入口门）。

---

## 三、R006 十项达标矩阵

| # | 项 | 状态 | 证据 |
|---|---|---|---|
| ① | dsh 插件形态 | ✅ | `package.json`（type/module/main/dsh.bundle.patch）+ `cordis.patch.yml` + `lib/index.js` `inject:['tools']` + `ctx.tools.register` |
| ①-5 | **真挂载冒烟（三态）** | ✅ | `--selfcheck` → `pass :: 注册 assert_audit`；缺依赖时输出 `skipped :: 依赖在本目录解析不到：…`（**绝不假装通过**） |
| ② | TCC 能力边界自检 | ✅ | `--selfcheck` 三段：能力清单 / 不该发生路径 / 依赖完整性 |
| ③ | CLD 自适应 | ✅ | 运行期仅 node 内置模块；无 CLD 依赖；peer 缺失不崩溃（降级为 `skipped`） |
| ④ | dsh 版本自适应 | ✅ | `peerDependencies` 声明；不做相对路径硬引用；peer 两级解析（self → profile） |
| ⑤ | 文档化 | ✅ | 本文件（为什么/用法/退出码/矩阵/坑/复现） |
| ⑥ | 版本管理 | ✅ | 版本唯一来源 = `package.json`；`--tool-version` 机器可读地从它读取（不硬编码） |
| ⑦ | 统一日志 | ✅ | `~/dsh-collab/logs/assert-audit.log`，每次动作记 时间/命令/结果/诊断；**门失效也留痕** |
| ⑧ | 自动落链 | ✅ | 黑板 `data/registry/dsh-plugin-assert-audit` + RULES.md 规则 + 索引行 |
| ⑨ | CLI 治理 | ✅ | 未知旗标 exit 2；退出码固定；`--dry-run` 零变更（A–F 的 D 项实测）；`--json`；`--help` |
| ⑩ | 约束前置（Lean4 门） | ✅ | `--lean4-check` A–F 全绿；见下 |

### ⑩ 门型与「不该发生的路径」

| 门型 | 本工具的实现 |
|---|---|
| **入口门** | 判定值只能是 `VERDICT` 冻结闭集成员；**闭集无 PASS/OK** ⇒ 崩溃无法冒充通过 |
| **类型锁** | `ALLOWED_COMMANDS` 冻结 `['python3','node']`；`Object.isFrozen` 由 E 项断言 |
| **Schema 门** | 工具入参 `runner` 为 `enum`；`parameters` 扁平属性表（见坑 1） |
| **唯一写入面** | 全仓库写入只有两处：`lib/audit.js` 的变异体写盘（**必须过 `assertTmpContained`**）+ `cli.js` 的固定日志路径 |

| 封堵的「不该发生的路径」 |
|---|
| 把套件崩溃判成 `CAUGHT` 或 `SURVIVED` |
| 把无效变异体（语法错/绑定错/锚点不唯一）判成 `SURVIVED` |
| 对未执行的断言报 PASS |
| 写入被测源文件或其所在目录 |
| 越出 `os.tmpdir()` 写文件（**含路径穿越**） |
| 执行白名单外命令 / `shell:true` 拼接 |

---

## 四、坑（全部为 2026-10-01 实测，含本工具自己踩的）

| # | 坑 | 表现 | 修法 |
|---|---|---|---|
| 1 | **`parameters` 形态写错** | 包了一层 `{type:'object',properties}` → `defineTool` 抛 `unsupported JSON schema: parameters.type must be a value schema object` → **apply() 崩、插件根本挂不上** | `parameters` **直接就是 properties 表**。★ 由 ①-5 真挂载冒烟抓到——「其它九项全绿而插件不存在」正是该项存在的理由 |
| 2 | **嵌套 object 漏 `additionalProperties`** | `UNSUPPORTED_SCHEMA`（2026-09-13 历史坑，本次在 `mutants.items` 上主动规避） | 嵌套 object 一律显式声明 `additionalProperties` |
| 3 | **路径穿越绕过 `startsWith`** | gate 初版用字符串前缀判定，`/tmp/../etc/hosts` **以 `/tmp/` 开头 ⇒ 假通过** | **先 `path.resolve` 消解 `..` 再比较**。★ 由 B 项负例抓到 |
| 4 | **扫描器「空集通过」** | 出站调用点实参是变量时读不到字面量 → 判定为 0 个坏命令 → 通过 | `scanExecSites` 三态：`literal` / `variable-guarded`（近邻有 `assertCommand`）/ **`UNRESOLVED`（判红）** |
| 5 | **崩溃被当成结论** | 变异体语法错被记为「存活」→ 审查得出反向结论 | 三态判定 + 闭集无 PASS |
| 6 | **`node` 不在 PATH** | 直接用 `node` 报 `command not found` | 本机 node 在 `/opt/homebrew/bin/node`；文档与脚本用绝对路径 |
| 7 | **`timeout` 命令不存在**（macOS） | 脚本里用 `timeout` 直接 127 | 用 `gtimeout` 或交由工具内 `execFileSync` 的 `timeout` 选项 |

---

## 五、复现命令（可复制即用）

```bash
cd ~/dsh-collab/devices/dsh-plugin-assert-audit
NODE=/opt/homebrew/bin/node

$NODE cli.js --tool-version                    # → 1.0.0
$NODE cli.js --lean4-check                     # → A–F 全绿 exit 0
$NODE cli.js --selfcheck                       # → 三段 + 冒烟三态
$NODE cli.js --bogus ; echo $?                 # → 2（用法错误）

# 用它对一份真实套件跑审计（示例：本机 L1 邮箱）
$NODE cli.js --source ~/dsh-collab/comm-server/agent-mailbox.py \
             --tests  ~/dsh-collab/comm-server/agent-mailbox.py \
             --token 'expires_at > ?' --run-arg selftest --runner python3 \
             --mutants-json /tmp/mutants-am.json
```

---

## 六、本工具**不做**什么（边界）

1. **不做覆盖完整性证明**：变异测试只能证明「已写的断言能红」，**证明不了「该写的都写了」**。
   多调用点检测是靠「同谓词计数 + 套件提及次数」的**启发式**，会漏（尤其谓词不以字符串复用时）。
2. **不判断言语义是否正确**：`WEAK_COMPARE` 是**诊断输出**不是判决——`len(x) >= 5` 可能是合理的。
3. **不跨进程并发**：被测套件自身的并发形态由套件负责。
4. **不改被测文件**：只读；只写 `os.tmpdir()`。

---

*v1.0.0 · 2026-10-01 · 星桥 · R006 十项达标*
