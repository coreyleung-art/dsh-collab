# CLD「本轮运行失败 · reading 'prepare'」+ 修复期启动崩溃 —— 诊断与修复报告

- 日期：2026-10-06
- 范围：CLD（`/Applications/CLD.app`）web profile（`~/.dsh/profiles/web`）
- 状态：**修复已就位，待重启验证**（自动化不自行重启 CLD）
- 影响文件：`~/.dsh/profiles/web/node_modules/@deepseek-ai/**`（移走 14 个遮蔽实体目录）+ `~/dsh-plugin-knowledge-tools/node_modules/@deepseek-ai/dsh-tools`（软链重指）
- 备份（可回滚）：`~/.dsh/_shadow-backup-web-20261006/@deepseek-ai/`

---

## 一、背景与症状

| # | 症状 | 性质 | 状态 |
|---|------|------|------|
| A | CLD 会话开始后弹**「本轮运行失败」**，错误 `Cannot read properties of undefined (reading 'prepare')` | 服务端：工具调度器拿到 `undefined` | ✅ 已修 |
| B | 修复过程中 CLD **启动崩溃**、超 120s 无 URL（`Timed out waiting for dsh web to announce its URL`） | 修复引入了新问题（我漏了一步） | ✅ 已修 |

二者性质不同：A 是**运行期**每次用工具都失败；B 是**启动期**插件树加载失败。B 由 A 的修复动作误伤所致。

关键判读：CLD 的 loader 用 `Promise.allSettled` **一次性收齐全组失败再抛** `AggregateError`（`cordis-plugin-loader/lib/index.js:97`），所以最新一次启动日志里的失败清单就是完整清单。

---

## 二、故障 A：根因 —— `dsh-tools` 双模块实例

### 2.1 直接机制

`dsh-agent-loop`（运行时包）执行工具前会取调度器：

```
// dsh-agent-loop/lib/index.js
:10   import { TOOL_ABORTED_BEFORE_DISPATCH, TOOL_RUNTIME_SCHEDULER } from "@deepseek-ai/dsh-tools";
:254  const prepared = await ctx.tools[TOOL_RUNTIME_SCHEDULER].prepare(call.exec);   // ← 报错点
```

`TOOL_RUNTIME_SCHEDULER` 是**普通 `Symbol()`，不是 `Symbol.for(...)`**：

```
// dsh-tools/lib/index.js
:2416  const TOOL_RUNTIME_SCHEDULER = Symbol("@deepseek-ai/dsh-tools.scheduler");
:2564  [TOOL_RUNTIME_SCHEDULER] = { prepare, dispatch, finalize, finish, ... }
```

**同一份代码只要被加载成两个模块实例，就produce两个不同的 Symbol。** 于是 `ctx.tools` 上挂的是 A 实例的 symbol，而 `dsh-agent-loop` 读的是 B 实例的 symbol → `ctx.tools[B]` 为 `undefined` → `.prepare` 抛错。

> 注意错误文案只点名 `prepare`，说明 `ctx.tools` **存在**，只是那个 symbol 键取不到 —— 正是「实例分裂」的指纹，而非「服务缺失」。

### 2.2 两个实例从哪来

| 实例 | 位置 | 版本 |
|---|---|---|
| ① profile 遮蔽副本 | `~/.dsh/profiles/web/node_modules/@deepseek-ai/dsh-tools` | `0.1.0-rc.7` |
| ② 运行时 | `/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools` | `0.1.1-rc.2` |

**加载路径分叉**：

- loader 解析**插件入口**用 **profile 目录**当锚（`createRequire(ctx.baseUrl)`，baseUrl = profile 目录）→ `@deepseek-ai/dsh-tools` 命中 **① profile 遮蔽**；
- `dsh-agent-loop` 被加载后，其内部 `import "@deepseek-ai/dsh-tools"` **按自身文件位置**解析（文件在运行时树里）→ 命中 **② 运行时**。

两条路径 → 两份模块实例 → symbol 不一致。

```mermaid
flowchart TD
    L[loader: baseUrl = profile 目录] -->|import dsh-tools| S1["① profile 遮蔽副本 dsh-tools 0.1.0-rc.7<br/>Symbol_A"]
    L -->|import dsh-agent-loop| RT["② 运行时 dsh-agent-loop"]
    RT -->|"import dsh-tools（按文件位置）"| S2["② 运行时 dsh-tools 0.1.1-rc.2<br/>Symbol_B"]
    S1 -->|provide| TOOLS["ctx.tools 服务（挂 Symbol_A）"]
    S2 -->|读 ctx.tools[Symbol_B]| UNDEF["undefined"]
    UNDEF -->|".prepare(...)"| ERR["TypeError: reading 'prepare'"]
    ERR -->|"turn/end reason.kind=error"| GUI["GUI: 本轮运行失败"]
```

### 2.3 与 GUI 文案的对应

`dsh-client-ui-conversation` 把 `turn/end` 且 `data.reason.kind === "error"` 渲染成「本轮运行失败」，并附 `error.message`：

```
:6245  "message.turnError": "本轮运行失败"
:9025  turnErrorDefinition  → 匹配 turn/end, data.reason.kind === "error"
```

---

## 三、证据

| 证据 | 内容 | 说明 |
|---|---|---|
| 字节相同、版本不同 | ① 与 ② 的 `lib/index.js` **sha1 均为 `12d0614b2050`** | 排除「代码不同」；差异纯粹是**实例身份** |
| 错误只点名 `prepare` | `ctx.tools` 存在，仅 symbol 键缺失 | 分裂指纹 |
| 逐回合统计（会话 fa1f9150） | 用工具（read/bash）的回合**全部** `error`；不用工具的回合正常 `completed` | 与「每次工具调用都取调度器」一致 |
| 环境全量比对 | `@deepseek-ai/*` 中 **14 个**为 profile 遮蔽实体目录，其余客户端插件本就随运行时 | 见 §4 清单 |

---

## 四、修复 A：去遮蔽（de-shadow）

**原理**：profile 的 `node_modules` 本就是 pnpm 管树外插件的；而 app 维护了一份**回退目录** `$DSH_HOME/profiles/node_modules`（= `~/.dsh/profiles/node_modules`），其中**每个包一条软链 → 运行时**。遮蔽实体目录压住了回退链。**把遮蔽实体目录移走**，解析即下落回退链 → 运行时，两锚点归一到同一文件。

> 这不是「改代码」，是**改解析布局**；与既有做法一致（`cordis`/`dsh-api-gateway`/`dsh-base`/`dsh-web-app`/`dsh-client-runtime` 本就是 web 下的软链 → 运行时）。

移走清单（14，全部在运行时存在）：

```
cosmokit dsh-attachment dsh-brand dsh-client-ui-slots dsh-credentials
dsh-host-directory-picker dsh-llm dsh-native-command dsh-settings dsh-skill
dsh-tools dsh-typert-protocol dsh-user-approval schemastery
```

版本对齐（profile → 运行时）：

```
cosmokit              1.8.2        → 1.8.3
dsh-attachment        0.1.0-rc.7   → 0.1.1-rc.2
dsh-brand             0.1.0-rc.7   → 0.1.1-rc.2
dsh-client-ui-slots   0.1.0-rc.7   → 0.1.0-rc.6   ← 降级（见 §7）
dsh-credentials       0.1.0-rc.7   → 0.1.1-rc.2
dsh-host-directory-picker 0.1.0-rc.7 → 0.1.1-rc.2
dsh-llm               0.1.0-rc.7   → 0.1.1-rc.2
dsh-native-command    0.1.0-rc.7   → 0.1.1-rc.2
dsh-settings          0.1.0-rc.7   → 0.1.1-rc.2
dsh-skill             0.1.0-rc.7   → 0.1.1-rc.2
dsh-tools             0.1.0-rc.7   → 0.1.1-rc.2   ← 本次故障主角
dsh-typert-protocol   0.1.0-rc.6   → 0.1.1-rc.2
dsh-user-approval     0.1.0-rc.7   → 0.1.1-rc.2
schemastery           3.18.1       → 3.18.2
```

**验证（决定性）**：分别从 profile 锚点与运行时 `dsh-agent-loop/lib/` 锚点解析这 14 个包，比对 `realpath`：

```
DIFF count: 0  => every shared package is a single module instance
```

即 14/14 归一到运行时同一文件，`dsh-tools` 单一实例，symbol 统一。

---

## 五、故障 B：修复期启动崩溃（我漏的一步）

### 5.1 现象

移走遮蔽后，新一轮启动（本地 17:54，pid 76587）崩溃：

```
Error: dsh: plugin tree failed to load: failed to apply loader entry include (cordis:include):
  failed to import loader entry knowledge-tools (dsh-plugin-knowledge-tools):
  Cannot find package '@deepseek-ai/dsh-tools' imported from
  /Users/coreyleung/dsh-plugin-knowledge-tools/lib/index.js
Error [ERR_MODULE_NOT_FOUND]
  ...
  at async Promise.allSettled (index 173)
[exit-trace] CRASH: dsh-crash (pid 76587, code 1, signal null)
[child-exit] dsh 崩溃(code=1) 自动重启 1/3
```

（同日志里 `dsh-read-url` 的 selfcheck `PASS peer @deepseek-ai/dsh-tools` —— 说明**只有 knowledge-tools 这一个入口**断链。）

### 5.2 根因：树外插件的**自有**软链指向了 web 遮蔽

树外插件各自带一份 `node_modules/@deepseek-ai/*` 软链（≠ 走 profile 锚点）。`knowledge-tools` 的那条**指向了 web 遮蔽**：

```
~/dsh-plugin-knowledge-tools/node_modules/@deepseek-ai/dsh-tools
  -> ~/.dsh/profiles/web/node_modules/@deepseek-ai/dsh-tools   ← 被移走 → 断链
```

对照 `dsh-plugin-guard` 等**正确**的写法：

```
~/dsh-plugin-guard/node_modules/@deepseek-ai/dsh-tools
  -> ~/.dsh/profiles/node_modules/@deepseek-ai/dsh-tools        ← 回退链 → 运行时 ✔
```

**正确顺序应是**：① 先把指向 web 遮蔽的树外链重指到回退/运行时，**② 再**移走遮蔽。我做反了 → 断链 → 启动崩。

### 5.3 处置与现状

- 该链现指向 `…/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-tools`，**已 resolving**（mtime **18:03**；我操作前为 03:58。**改链者未确认** —— 若非人工，疑有自愈/守护程序介入）。
- 全量扫：`~/dsh-*` 与 `~/.dsh/profiles/*` 下 **无断链**、**无残留指向 web 遮蔽的链**。
- 最终一致性（四锚点 realpath 全同）：

```
SAME  profile-web              v=0.1.1-rc.2
SAME  runtime-agent-loop       v=0.1.1-rc.2
SAME  plugin knowledge-tools   v=0.1.1-rc.2
SAME  plugin guard             v=0.1.1-rc.2
```

---

## 六、为什么 `pnpm install` 不是本问题的工具（已实证）

本次用户曾倾向「对齐依赖 + `pnpm install`」。证据表明它**修不了这个**：

| 证据 | 结果 |
|---|---|
| profile `package.json` 声明的 `@deepseek-ai/*` 依赖 | **0 个** |
| `pnpm-lock.yaml` 里这些包的位置 | **全部是各插件包的 `peerDependencies`**（cordis 38 处、dsh-llm 13、dsh-tools 5…） |
| `settings.autoInstallPeers` | **false**（不自动装 peer） |
| `node_modules/.pnpm` 里 `@deepseek-ai+*` 条目 | **0** |

结论：`pnpm install` **不会**把它们对齐到运行时；反而可能把旧 `rc.7/rc.6` 重新装回来、再造遮蔽。正确工具是**去遮蔽**（§4）。根治需**上游化**：让第三方插件别把 `@deepseek-ai/*` 放进 `dependencies`/`peer`，或改用 patch/override 指到运行时。

---

## 七、附带发现与风险

- **`dsh-client-ui-slots` 为降级对齐**：profile 副本 `rc.7`、运行时 `rc.6`（运行时反而更旧）。以运行时为准做了统一；若该客户端包后续报错，单包回滚即可（备份中有）。
- **易被覆盖**：移走/重指的改动会被下次 `pnpm install/update` 或 `build-bundle.sh` 覆盖 —— 后者**有意**把 peerDeps 拷成实体副本（「避免符号链接」），这正是遮蔽的来源之一。
- **同类隐患仍在**：`profiles/web/node_modules/@deepseek-ai/` 下残留大量 `.bak-*-shade` / `.pnpmcopy-*` 目录（早前会话去遮蔽的备份），本身不遮蔽（非 bare 名），但会随 `pnpm install` 回流。
- **树外插件链接写法不统一**：有的指回退（`profiles/node_modules/...`，正确）、有的曾指 web 遮蔽（错误）。建议统一为回退链。

---

## 八、验证步骤与后续

1. **由用户重启 CLD**（自动化不自行重启）。
2. 新会话发一条**会用工具**的消息：应不再出现「本轮运行失败 … reading 'prepare'」；应不再出现 `Cannot find package '@deepseek-ai/dsh-tools'`。
3. 若仍报，错误会点名插件与精确符号/路径，按同法继续收敛（先扫树外链，再动 profile）。
4. 根治（后续，需联网/动 lockfile，须确认）：把第三方插件清单里的 `@deepseek-ai/*` 依赖去掉或 override 到运行时版本 + patch 机制，使 `pnpm install` 幂等不再造遮蔽。

---

## 附：状态快照（报告时）

```
遮蔽移走：14（备份 ~/.dsh/_shadow-backup-web-20261006/@deepseek-ai/，可回滚）
web 下剩余 bare 软链（本就正确）：cordis dsh-api-gateway dsh-base dsh-web-app dsh-client-runtime
dsh-tools：① 与 ② 的 lib/index.js sha1 同为 12d0614b2050（字节相同，仅版本不同）
一致性：profile/runtime/两个树外插件 四锚点 realpath 全同（v=0.1.1-rc.2）
断链扫描：@deepseek-ai / dsh-* 无
崩溃样本：pid 76587, code 1（boot 2026-10-06T09:54:44Z, 本地 17:54），自动重启 1/3
不相关历史崩溃：pid 78256 SIGKILL（早前 dylib 签名，已另修）
```
