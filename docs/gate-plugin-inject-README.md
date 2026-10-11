# gate-plugin-inject.py · 插件 inject 声明门

> 路径 `~/dsh-collab/scripts/gate-plugin-inject.py` · 独立 py 脚本（非 dsh 插件）
> v1.0.0 · 2026-10-10 · 本文档满足 R006 ⑤ 与 R039（中文描述文档）

## ① 为什么需要（事故与证据）

2026-10-09 **15:21:55.598Z → 15:57:15.993Z**（北京 23:21:55–23:57:16）CLD 在 **35 分 20 秒**内
启动 **806** 次（`~/.cld/logs/dsh-web.log` 的 `===== CLD boot … =====` 头分桶：10-09T15 一档 806，
即该窗口内**每一次启动都撞同一因**；`plugin tree failed to load` 全日志 811 次，余 5 次在窗口外）。
原因是一行结构性错误：`dsh-plugin-excalidraw` 在**宿主平面**声明了
`inject = ['slots']`，而 `slots` 只在**客户端平面**存在
（`dsh-client-runtime/lib/client.js:35` 的 `super(ctx, "slots")`）。官方
`assertEntriesActivated`（`dsh-app-boot/lib/index.js:1125` 取 `fiber.ctx.get(s) === void 0`，
:1134 抛）缺一条 ⇒ 整棵插件树加载失败 ⇒ 子进程 exit 1 ⇒ 自动重启。
风暴最后一次启动（`pid 29097`，`15:57:15.993Z`）就是用户当晚报的那次崩溃，现场逐行可复核。

**这个门的判据不是重新设计的，是复刻运行时自己的判据。** 门只需静态地算同一个谓词：
「这个 `inject` 名，在它所在的平面里真的有人 provide 吗」。

## ② 两条规则

| 规则 | 判据 | 抓的是 |
|---|---|---|
| **a 宿主/客户端边界** | 入口标为宿主平面时，`inject` 里的名字若**只在客户端平面被 provide** | 2026-10-09 那 806 次启动的形态 |
| **b 源/产物一致** | 同一入口的 `src/` 声明与 `lib/` 产物声明必须相等 | 「只修产物未修源」——2026-10-09 的 CJS→ESM 重编译从仍损坏的 `src/` 复活了已删除的 `inject` |

平面判定：包名含 `client` 段、或入口文件名为 `client.*` ⇒ 客户端平面；否则宿主平面。

## ③ 用法（含退出码）

```bash
python3 ~/dsh-collab/scripts/gate-plugin-inject.py                 # 跑 a+b，人读
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --rule a        # 只跑一条
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --json          # 纯机读（stdout 只有 JSON）
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --strict        # WARN 也判失败
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --show-skip     # 连跳过行一起打
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --all           # 连 OK 行一起打
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --selftest      # 正控（见 ⑤）
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --mounts-dir <D>  # 额外挂载根（自证/试跑用）
```

退出码：`0` = 无 RED（`--strict` 时也无 WARN）· `1` = 有 RED（或 `--strict` 下有 WARN）· `2` = 未知旗标/用法错。

**实测（2026-10-10）**：42 个挂载点，规则 a **0 红 / 0 黄 / 0 跳过**；规则 b 27 对实评 **0 红**、
34 跳过（跳过理由只有一种：该包没有 `src/`，纯 `lib` 交付，规则 b 不适用）。总判 PASS。

## ④ 为什么每处判据长这样（都是踩出来的）

1. **产物侧必须同时认 `const inject` 与 `X.inject = […]`。**
   打包器把 `export const inject = […]` 改写成 `const inject = […];` + 末尾
   `export { …, inject, … };`；客户端 bundle 更进一步 minify 成**成员赋值**全一行
   （`@omdsh-dev/dsh-genui/lib/client.js` 就是 `…,n.inject=[`slots`,`sessions`],…`）。
   只认 `export const` 会对**每一个打包产物**报假红。
2. **源侧必须沿 barrel 下探。** 入口常是 `src/index.ts` 只写 `export * from './plugin/index'`，
   真声明在子模块。只读入口 ⇒ 假红。下探**只跟 `export … from`**（`inject` 必须被再导出才有意义）；
   若把裸 `import` 也算进来，一个副作用引入的子模块会把它自己的 `inject` 冒充成入口的，
   那会**把红洗成绿**，比假红更坏。
3. **服务清单认三种 provide 形态**：`provide("x")` / `super(ctx, "x")` / **常量间接**
   `const SVC = "x"; ctx.provide(SVC, …)`。第三种是官方运行时的真实写法
   （`@deepseek-ai/dsh-web-app/lib/index.js:28` + `:175` 提供 `webRuntime`），
   漏掉它会把**已存在的宿主服务**当成未知、把合法 `inject` 报假黄。
   该形态另补上 `webStartup` / `headlessStartup` / `configuredAgentIdentities` 三个真服务。
4. **但 `super(ctx, 标识符)` 这一形态被实测否掉了**：它在运行时/档里新增 7 个条目、
   **真服务 0 个**，全是 vendored bundle 里的普通构造器调用
   （mermaid.js / three.js / pdfjs 的 `super(x, y)`，恰好 `y` 是字符串常量）。
   留一删一，依据是实测计数不是口味。
5. **宿主入口不能只看 `main`。** 包可以只声明 `exports["."]`
   （`@liustack/modlens` `main` 为空、宿主入口在 `exports["."] = ./dsh/index.js`）。
   只看 `main` 会让**整个包被静默跳过** —— 「没检查」冒充「通过」，比报错更坏。
6. **点目录一律不扫。** `~/.dsh/profiles/web/node_modules/.@linxin666.disabled/` 是**已停用**的包，
   扫它会把两个早已不在档里的服务（`none`、`webUiSettings`）算进清单；`none` 尤其糟，
   它根本不是服务，是 minified 代码里的构造器调用被误读。
7. **`--json` 的 stdout 只能有 JSON。** 原先尾部还打一行「== 结论 ==」，
   下游 `json.load` 报 `Extra data` ⇒ 人读结论改走 stderr。

## ⑤ R006 达标矩阵（独立工具口径）

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ⚠️ 显式偏离 | 独立脚本，非插件形态；按 R006 §2 独立工具口径交付 |
| ② TCC 检测 | N/A | 不触屏、不调 peekaboo、无 TCC 面 |
| ③④ CLD/版本自适应 | ⚠️ 部分 | 挂载点/服务清单**从实盘现算**，不写死版本；但根路径 `RUNTIME`/`PROFILE` 是模块常量，换 CLD 安装位置须改 |
| ⑤ 文档化 | ✓ | 本文件 |
| ⑥ 版本管理 | ⚠️ 部分 | 无 `--version`；版本只在本文件与卡里声明 |
| ⑦ 统一日志 | ⚠️ 部分 | 只打 stdout，不落日志文件 |
| ⑧ 语义检索/KB | N/A | 分析工具，非资料源 |
| ⑨ 可复现 | ✓ | 只读；`--json` 连跑 3 次 sha256 相同（`00c30d4d35c31276fc0902ac…`） |
| ⑩ 约束门 | ✓ | 只读：只 `open()` 读文件与 `os.walk`，无写盘、无 `subprocess`/`eval`/`exec`、无网络。`--mounts-dir` 只**读**调用方给的目录 |
| 正控（`--selftest`） | ✓ | **10/10**，见下 |

### 正控清单（`--selftest`，10 项全过）

`slots` 被判为仅客户端 · `webRuntime` 被判为宿主（常量间接形态）· 规则 a 抓住事故形态
`fx-boundary` · 规则 a 不冤枉 `fx-clean` · 规则 b 抓住「只修产物未修源」 `fx-parity` ·
规则 b 不冤枉 `fx-clean` · 认得打包器形态 `fx-bundled` · 认得成员赋值形态 `fx-member[client]` ·
认得源侧 barrel `fx-barrel[host]` · **反向正控** `fx-barrel-stale`：下探后仍抓得住真差异
（防止「下探」这个新机制把红洗成绿）。

## ⑥ 限度（明确写出，不靠读者猜）

1. **静态不可判定的一律 WARN，不静默通过。** 名字在两边清单里都找不到 ⇒ 报
   「证据不足（无法证明可满足）」，而不是 OK。实测该情形为 0 个。
2. **规则 b 对无 `src/` 的包不适用**（34 对跳过）。这些包是纯 `lib` 交付，
   「只修产物未修源」这个失效模式在它们身上没有载体；反过来「手改 lib 被下次构建覆盖」
   也检测不到。**跳过 ≠ 通过**，报告里单列。
3. **只复刻了 `inject` 这一条谓词。** 官方激活检查还包含入口是否解析、`apply` 是否存在、
   `dsh.client.inject` 与服务的位置是否匹配等；本门不覆盖。
4. **服务清单来自扫描，不是运行时自述。** 动态 provide（运行期算出来的名字）认不出，
   会落到 WARN 而不是 RED（偏向不误报）。
5. **根路径写死**（见 ⑤ ③④）：换 CLD 安装位置或换 profile 名须改模块常量。

## ⑦ 复现

```bash
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --selftest   # 期望：10/10，exit 0
python3 ~/dsh-collab/scripts/gate-plugin-inject.py --rule all   # 期望：PASS，RED 0，WARN 0
for i in 1 2 3; do python3 ~/dsh-collab/scripts/gate-plugin-inject.py --rule all --json \
  | shasum -a 256; done                                          # 期望：三行相同
```

## ⑧ 与既有工具的关系

`scripts/cordis-crash-audit.py`（v1.0，2026-10-03 补课）是**单文件、人工指定路径**的审查
（查 `slots.inject` 是否仅 1 处、是否 `ctx.effect` 内 return disposer 等 4 项启发式）。
本门是它的**全量、自动、复刻运行时谓词**的版本：不需要人指定文件，扫全部挂载点，
判据不是启发式而是官方 `assertEntriesActivated` 的同一条谓词。两者并存，不互相取代
（`cordis-crash-audit` 的 1/3 项本门不覆盖）。
