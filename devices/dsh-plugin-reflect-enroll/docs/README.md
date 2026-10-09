# reflect-enroll · 反思入册 · 反馈闭环（R006 十项达标 · 跨设备 v1.1）

> 位置 `~/dsh-collab/devices/dsh-plugin-reflect-enroll/` · 版本见 `package.json`（单一来源，`--tool-version` 读它）
> 角色：**「每日反思」流水线的唯一写库环节** + **「数据飞轮」的闭环点**
> 上游：`dsh-plugin-reflect`（collect → dispatch → harvest → synthesize）· 设计：`docs/daily-reflection-pipeline-design-v1.md`（§5 安全设计 / §10 跨设备层）

---

## ① 为什么需要它（实证，不是推测）

| 问题 | 证据 | 本工具怎么解 |
|---|---|---|
| 治理哲学/规则**改起来没有纪律** | 哲学库 `governance-philosophy.json`（现 v1.6 / 13 条）、规则账本 `RULES.md`（78 个规则块）是**全系统的共同约束基础**，手改容易漏 changelog、编号撞车、写坏 JSON | 唯一写库入口：读 → 追加 → `.tmp` 原子写 → 回读校验 → 失败回滚；编号/幂等双查 |
| **自动改库 = 违反用户主权** | `phi-user-sovereignty`「AI 可提议，执行需人类确认」；本项目最高原则 | 结构上**没有**"没有裁定也能入册"的入口：裁定只能是用户给的 `decision`∈{approve,reject,modify,defer} |
| **规则入册后躺着不动 = 没人知道** | 2026-09-10 用户指出：「引导所有智能体的对象**包括其他设备上的智能体**」；入册若没人读，等于没入册 | 入册后强制生成反馈卡 + 写本机/中央黑板 + 短指引投递到相关设备（含离线设备自取） |
| **只采本机 = 只看到四分之一** | `devices/device-registry.md`：MBP 是**独立 DSH 节点**（有独立智能体网络）、PC-i9 经 MCP 接入 | 相关智能体判定为 `<device>:<agent>`，按资源归属跨设备定位 |
| **凭据会跟着卡片跨设备扩散** | 设计文档 §10.5 风险①（Φ12 形态④） | 落盘/上黑板前**扫描 + 脱敏 + 复检**（fail-closed） |

**一句话**：本工具不做"聪明的判断"，它做的是**把人类的裁定变成可追溯的库变更，并且确保这条新约束真的被所有设备上的相关智能体看到**。

---

## ② 用法

```bash
# ── 入册（必须有人裁） ──
node cli.js --ruling ~/dsh-collab/data/reflect/ruling-2026-09-10.json          # 格式 A：裁定文件
node cli.js --rule P1=approve:philosophy --date 2026-09-10                      # 格式 B：单条裁定
node cli.js --ruling <file> --dry-run                                          # ★ 先看计划：一个字节都不写
node cli.js --ruling <file> --notify                                           # 入册 + 推送短指引给相关智能体
node cli.js --rule P2=approve:rule --json | jq .                               # 机器可读

# ── 自检与验收 ──
node cli.js --selfcheck        # ② TCC 三段：能力清单 / 不该发生路径 / 依赖完整性
node cli.js --lean4-check      # ⑩ 结构门自证 A–F（负例实测 + dry-run 零变更实测）
node cli.js --tool-version     # ⑥ 与 package.json 一致
node cli.js --help

# ── 沙箱/自测（指向副本，绝不碰真库） ──
node cli.js --root /tmp/enroll-test/collab --ruling /tmp/enroll-test/collab/data/reflect/ruling-2026-09-10.json --dry-run
```

**退出码**：`0` 成功/门生效 · `1` 失败（门拒绝 / 校验失败 / 已回滚 / 入册成功但反馈未落地）· `2` 用法或 IO 错误
**两类"非法值"刻意分开**：CLI 参数（`--rule` 的 `decision`/`target` 不在冻结枚举）**在解析期**即拒 → exit 2；裁定文件里的非法值属外部数据 → 走门拒绝 exit 1。这样"参数写错"不会被误报成"门拒绝"。

### 输入格式

**A. 裁定文件**（`<root>/data/reflect/ruling-<date>.json`，或 `--ruling` 指定）

```json
{ "date": "2026-09-10",
  "rulings": [ { "proposal_id": "P1", "decision": "approve", "target": "philosophy",
                 "modifications": "（decision=modify 时必填）", "reason": "用户给的理由" } ] }
```

**B. CLI 单条**：`--rule <proposal_id>=<decision>:<target>`

**提案正本**（入册内容的唯一来源，工具**绝不自行编造**）：`<root>/data/reflect/proposals-<date>.json`
查找顺序 = `--proposal` → `proposals-<date>.json` → `proposals.json` → 最近的 `proposals-YYYY-MM-DD.json`（≤3 份，跨零点回退，**回退时会在输出里明说用了哪份**）。

### 三种 target × 四种 decision

| target | 干什么 | 写哪 |
|---|---|---|
| `philosophy` | 新增哲学条目 | `data/blueprint/gallery/governance-philosophy.json`（含 `id/name/core/origin/doc/order/status` + changelog 数组 + `version` 递增）**与** `governance-philosophy-changelog.md`（新增段落插在「版本历史」下） |
| `rule` | 新增规则 | `rules-registry/RULES.md`（规则块插在「治理哲学」段之前 + 头行版本/条数校正）**与** `rules-registry/rules.json`（同步 + `audit.ruleCount`） |
| `spec` | 转规范（**不改治理库**） | `docs/sops/<slug>.md`（已存在则拒绝，不覆盖） |
| `archive` | 只归档为案例（不入册） | `data/reflect/archive/<date>.md` |

| decision | 行为 |
|---|---|
| `approve` | 照提案正本入册 |
| `modify` | 入册，且裁定**必须**带 `modifications` 文本（工具不猜改法）；该文本原样记入 changelog 与台账 |
| `reject` | **不入册**，只把驳回写进案例归档（可再审） |
| `defer` | **完全不动**（不写台账），下次裁定可再提交 |

---

## ③ R006 十项达标矩阵

| # | R006 项 | 达标 | 实现 / 证据 |
|---|---------|------|------|
| ① | dsh 插件形态 | ✅ | `package.json`（`type:module` / `main` / `version` / `dsh.bundle.patch`）+ `cordis.patch.yml`（`- insert:`）+ `lib/index.js`（`export const inject=['tools']`、`ctx.effect(() => ctx.tools.register(...))`，注册 **`reflect_enroll`**） |
| ② | TCC 检测 | ✅ | `--selfcheck` 输出三段：① 能力清单 ② 不该发生路径（7 条） ③ 依赖完整性；`runSelfCheck` 落盘 `~/.dsh/plugin-selfcheck/reflect-enroll.json` |
| ③ | CLD 自适应 | ✅ | 运行期只用 node 内置模块（`fs/path/os/http/crypto/url/util/module`）；无 CLD/宿主私有 API；`--lean4-check` 在无宿主环境同样可跑 |
| ④ | dsh 版本自适应 | ✅ | `peerDependencies` 正式声明 `@deepseek-ai/cordis`/`dsh-tools`；解析走"本目录 → profile `node_modules`"两级（selfcheck 可见 `via:profile`）；未知版本只影响挂载、不影响 CLI |
| ⑤ | 文档化 | ✅ | 本文件（为什么/用法+退出码/十项矩阵/坑/复现命令）+ `package.json` `r006.documented` |
| ⑥ | 版本管理 | ✅ | 版本**只**写在 `package.json`；`lib/version.js` 运行时读取，`--tool-version` 与日志/卡片都取自它；`CHANGELOG.md` 含纠错复盘 |
| ⑦ | 统一日志 | ✅ | `~/dsh-collab/logs/dsh-plugin-reflect-enroll.log`，每动作一行 JSON（时间/输入/判断/结果/诊断）；**失败也留痕**（`apply.failed` 含回滚详情；`plan.rejected` 含拒绝码） |
| ⑧ | 自动落链 | ✅ | `data/registry/dsh-plugin-reflect-enroll.json` 登记卡 + 本机/中央黑板 `data/registry/reflect-feedback-<date>` 通知卡 + `docs/README.md` |
| ⑨ | CLI 治理 | ✅ | 严格 `parseArgs`（未知旗标 → exit 2）；`--rule` 语法 + 冻结枚举**解析期**校验（非法值 → exit 2）；退出码语义固定 0/1/2；`--dry-run` **零变更**（文件 + 黑板双侧实测）；`--json`（成功/失败两条路径都是合法 JSON）；`--help` 自解释 |
| ⑩ | 约束前置·不可绕过 | ✅ | 见下节（四条"不该发生路径"结构封死 + 跨设备/凭据/R001 持锁门 + `--lean4-check` A–F 六项全绿） |

---

## ④ ⑩ 结构门：四条"不该发生路径"怎么被**结构上**封死

| 不该发生 | 门型 | 结构措施（不是"检查后放行"） |
|---|---|---|
| **自动决定入册什么** | 类型锁 + 入口门 | `DECISIONS`/`TARGETS` 冻结枚举；唯一入口是"用户裁定"（裁定文件 / `--rule`）；包内**不存在**任何"生成裁定/默认裁定"的函数，也没有 `autoDecide`/`force` 开关（`cordis.patch.yml` 刻意不提供这些键） |
| **删除任何条目** | 能力缺失 | 源码零删除原语（A 项扫描：`unlink/rm/rmdir/truncate/killall/...` + `process.kill` 命中 0）；唯一写形态是"读取 → 追加 → 原子覆盖"；回读阶段断言 `条目数 === 写入前 + N`，且既有条目 prefix 逐字节比对 |
| **重复入册** | 幂等门 | 台账 `data/reflect/enrolled.json`（同 `proposal_id` 且 `outcome=enrolled` 即拒）+ 同批重复即拒 + 编号唯一性查重（哲学 `id`/`order`；规则号在 `rules.json` 与 `RULES.md` **双查**） |
| **写坏目标文件** | 原子写 + 回滚 | 备份前置（**回读验证备份可解析**）→ `.tmp` 写入 → 校验可解析 → `rename` 覆盖 → **回读校验**（可解析/条目数/编号在位/字段齐全/旧条目未变）→ 任一环失败**自动回滚**并逐个回读验证；另有"计划生成后文件被改动即拒写"的并发保护 |

**跨设备层新增的 2 条门（v1.1）**

| 不该发生 | 门型 | 结构措施 |
|---|---|---|
| **凭据随卡片扩散**（Φ12 形态④） | 值门 + fail-closed | 落盘前 / 上黑板前 `redactCredentials` 脱敏 → `assertNoCredentials` **复检**，残留即拒写；命中种类与次数进日志与输出 |
| **越权写别人目录 / 非法 key** | 命名空间门 | `assertWriteKey`：key 首段必须 `[a-z]+`（否则黑板 400）—— **非法键本机即拦，连请求都不发**；正文只允许 `data/reflect/`·`data/registry/`；`notes/` **仅**允许 ≤50 字短指引（`POINTER_TOO_LONG`）；出站主机冻结白名单 `[127.0.0.1, localhost, ::1, 106.53.214.108]` |
| **把"写了"当成"落地了"**（R003 补充 2026-09-11） | 语义门 + 内容门 | `classifyBbReadback` 区分 **400=键错 / 404=不存在 / 200+value 非空+标记命中=真落地**；**空壳键（`value={}`）判未落地**——纯状态码校验会漏，必须验内容；`assertLanded()` 非落地即抛 `BB_WRITE_NOT_LANDED`。实证：今日已有 4 次"报告指向不存在的落盘物"事故 |

### `--lean4-check` 六项（实测输出见 §⑥）

| 项 | 证明内容 | 方法（含踩过的坑） |
|---|---|---|
| **A** | 源码无删除/终止原语 | **去注释/字符串/正则字面量后**扫描（否则会把自己的检测正则当靶子 → 假阳性） |
| **B** | 负例全部被拒（54 条） | 越界 `decision`/`target`/`slug`/`bbUrl`/重复编号/重复入册/路径逃逸 + 越权写入 key + 残留凭据，逐条实测 `GateError` |
| **C** | 正例全部可用（20 条） | 4 决策 × 4 目标 + 合法 key + 合法短指引 + 黑板主机 + **普通 sha256/uuid 不被当凭据**（防"门太宽砍掉自己人"） |
| **D** | `--dry-run` 零变更 | 目标文件 sha256 前后实测一致 + 计划 2 个待写文件而实际写入 0 / 备份 0（套件里另加黑板侧 PUT/GET 计数前后一致） |
| **E** | 白名单/枚举冻结 | `Object.isFrozen(...)`：决策、目标、写入前缀、出站主机、协议、命令白名单（空集）、危险原语表、必填字段表 |
| **F** | 出站白名单 + 零 shell 出站 | 枚举对外调用点：**恰好 1 个**（`lib/feedback.js` 的 `bbRequest`），且断言该函数体内先调 `assertBbHost`；exec/spawn 执行点 0、`child_process` 模块 import 0 —— 用"恰好 1 个出站点"避免"空集通过"这种假证明 |

---

## ⑤ 跨设备层（v1.1）：反馈卡推送到全部设备

| 落点 | key / 路径 | 谁写 | 谁读 | 写入后校验 |
|---|---|---|---|---|
| 本机落盘 | `data/reflect/feedback-<date>.md` | 本工具 | 本机会话/人 | 回读含标题 |
| 本机黑板·全卡 | `data/reflect/feedback/<date>` | 本工具 | 本机 | PUT → GET 回读比对 |
| 本机黑板·通知卡 | `data/registry/reflect-feedback-<date>` | 本工具 | 本机 | PUT → GET 回读比对 |
| **中央黑板**·全卡 | `data/reflect/feedback/<date>` | 本工具 | **全设备** | PUT → GET 回读比对 |
| **中央黑板**·通知卡 | `data/registry/reflect-feedback-<date>` | 本工具 | **全设备** | PUT → GET 回读比对 |
| 短指引（待投递队列） | `notes/<device>/reflect-feedback-<date>` | 本工具 | 该设备上线后自取 | PUT → GET 回读比对，正文 ≤50 字 |

- **中央黑板**默认 `http://106.53.214.108:8792`（可用 `--central-bb` / `env DSH_BLACKBOARD` 覆盖；**必须过主机白名单**）。
- **相关智能体 = `<device>:<agent>`**，四级判定（按可信度，回报用了哪级）：
  1. 提案 `related_agents`（支持 `mbp:review` / `mbp` 整设备 / `review` 本机 agent）
  2. **资源归属**：提案 `resources` → `data/registry/resource-owners.json`（资源在哪台设备）+ `device:<name>` 自述
  3. 设备发现表 `data/discovery/agents/*.json`（含 `sessions[].role` → `device:role`）
  4. 判不出 → 空列表 + **如实说明**（不猜）
- **本机设备名**：`--device` > `$DSH_NODE_ID` > 主机名匹配 `devices/device-registry.md`（含别名表 `DEVICE_ALIASES`）> 主机名派生（派生时会**警告**，提示显式 `--device`）。
- **时间坐标（Φ13）**：黑板值同时带 `ts`（UTC，采集时刻）与 `ts_local`（设备本地时间）、`origin_device`（采集者）、`plugin_version`。
- **通知卡内容**（要求 3）：`rules[]`（摘要 + **它约束什么** `constrains` + 落点文件 + 裁定与理由）、`devices[]`（**哪些设备的哪些智能体该注意**）、`card_key`/`card_file`、`redactions`。

---

## ⑥ 复现命令（照抄即用）

```bash
PLUG=~/dsh-collab/devices/dsh-plugin-reflect-enroll
export PATH="/opt/homebrew/bin:$PATH"          # 本机 node 在 homebrew（PATH 缺 node 是环境问题，不是包问题）

# 0) 建副本（真库只读复制；★ 绝不在真库上跑入册）
R=/tmp/enroll-test/collab
mkdir -p $R/data/blueprint/gallery $R/rules-registry $R/data/reflect $R/docs
cp ~/dsh-collab/data/blueprint/gallery/governance-philosophy.json $R/data/blueprint/gallery/
cp ~/dsh-collab/data/blueprint/gallery/governance-philosophy-changelog.md $R/data/blueprint/gallery/
cp ~/dsh-collab/rules-registry/RULES.md $R/rules-registry/
cp ~/dsh-collab/rules-registry/rules.json $R/rules-registry/
#（外加自备 data/reflect/proposals-<date>.json 与 ruling-<date>.json）

# 1) 自检门 + 结构门（②③④⑩）
node $PLUG/cli.js --selfcheck     # exit 0
node $PLUG/cli.js --lean4-check   # A–F 全绿 exit 0

# 2) dry-run 零变更（⑨⑩D）：sha256 全量比对
find $R -type f | sort | xargs shasum -a 256 > /tmp/before.sha256
node $PLUG/cli.js --root $R --ruling $R/data/reflect/ruling-2026-09-10.json --dry-run
find $R -type f | sort | xargs shasum -a 256 > /tmp/after.sha256
diff /tmp/before.sha256 /tmp/after.sha256 && echo "零变更 ✅"

# 3) 真实入册（副本）
node $PLUG/cli.js --root $R --ruling $R/data/reflect/ruling-2026-09-10.json --device mac-mini --notify

# 4) 幂等 / 编号冲突（都必须被拒，exit 1）
node $PLUG/cli.js --root $R --ruling $R/data/reflect/ruling-2026-09-10.json            # DUPLICATE_ENROLL
node $PLUG/cli.js --root $R --ruling <用已存在编号的裁定>                                # ID_CONFLICT

# 5) 回滚（注入真实 IO 故障：chflags uchg 冻住第二个目标文件 → 第一个已写文件必须被还原）
shasum -a 256 $R/data/blueprint/gallery/governance-philosophy.json
chflags uchg $R/data/blueprint/gallery/governance-philosophy-changelog.md
node $PLUG/cli.js --root $R --rule P5=approve:philosophy --date <date> --device mac-mini   # exit 1，含「↳ 已回滚」
chflags nouchg $R/data/blueprint/gallery/governance-philosophy-changelog.md
shasum -a 256 $R/data/blueprint/gallery/governance-philosophy.json                      # 与之前一致 ✅

# 6) 未知旗标 exit 2 / --json 合法
node $PLUG/cli.js --frobnicate; echo $?                     # 2
node $PLUG/cli.js --root $R --rule P5=approve:philosophy --dry-run --json | node -e "JSON.parse(require('fs').readFileSync(0,'utf8'));console.log('json ok')"

# 7) 中央黑板写入 → 回读校验（真实 106.53.214.108:8792，自测标签键）
node --input-type=module -e "
import { bbPutVerified } from '$PLUG/lib/feedback.js';
const key='data/reflect/feedback/selftest-'+Date.now();
console.log(await bbPutVerified('http://106.53.214.108:8792', key, {key,topic:'自测'}, {kind:'card',marker:key}));"
```

---

## ⑦ 与 `scripts/bb-write.py` 的**跨实现一致性**（R006 §1 事故防范）

同一个黑板写入协议在生态里有两处实现：Python 侧 `scripts/bb-write.py`（各角色通用）与**本工具的原生实现**（`bbRequest`/`bbPutVerified`）。
R006 §1 记录过"两处实现行为不一致 → 认知分裂"的事故，所以本工具**逐条对账**（`/tmp/enroll-test/suite-part7.sh`，23 个键）：

- **一致 18 / 23**；首段大小写、中文键名、前导斜杠、单段拒绝、`cld-health/x` 类 400 键等全部一致。
- **5 处分歧**（均因本工具更严，且分歧方向已用黑板实测裁定）：
  | 键 | bb-write.py | 本工具 | 黑板实测 | 裁定 |
  |---|---|---|---|---|
  | `data/reflect/`（尾斜杠） | 接受 | 拒 | `GET` → **200 + `{list,total}` 全库列举** | **应拒**：列举里必然含你写的键字符串，任何"标记命中即落地"的判据都会被骗过 |
  | `data//key`（空段） | 接受 | 拒 | `GET /data//reflect` → **404** | **应拒**：写得进、读不到 |
  | `data/dom/my key`（空格） | 接受 | 拒 | `GET /data/…/my%20key` → **400 bad key** | **应拒**：验证通过但服务端 400 |
- **分工**：Python 角色用 `bb-write.py`（独立 CLI，零依赖）；dsh 插件**不 shell 出站**（R006 ③⑩ 要求），故原生实现同一协议，语义与 `--lean4-check` 一起自证。
- **对账即观测点（Φ8 的高级用法）**：两处实现跑同一批输入 → 逐条对账，能抓到**任何单一实现自己看不见的问题**（因为只有一个实现时没有对照物）。首轮对账抓到我 2 处缺口 + 对方 3 类宽松点；对方修复后复验 **23/23 一致**；第二轮加测字符类又发现**双方共有**的盲区（`% & ; + = :` 与非 ASCII 实测 400、`.`/`..` 段触发路径归一化）。建议与 HR 做**定期对账**（新键形态出现时）。
- **实测字符类**（只读 GET 真黑板，对 20195 个真实键零误伤）：允许 `字母数字 . - _ ? #`；拒 `% & ; + = :` 与非 ASCII（400）、拒 `.`/`..` 段（路径归一化 → 命名空间列举）。
- **落地判据（两边同源）**：`回读 200 + value 非空 + 内容深比对一致`（键排序规范化，防截断/并发覆盖；对齐 bb-write.py v1.0.2 的修复）。

## ⑧ 坑（全部是本次真实踩到的，含"会撒谎的检查"）

| # | 坑 | 表现 | 修法 |
|---|---|---|---|
| 1 | **会撒谎的检查（假失败）** | 回读校验写了"原文本必须是前缀"，但哲学 changelog 与 RULES.md 都是**插在中间**的 → **正确**的写入被判失败并触发回滚 | 换成真实不变式：**原文每一行按序仍在（只增不删）**；RULES.md 头行的版本/条数改写做成**唯一允许的改写**并显式核对 from→to |
| 2 | **假失败（反向）** | 黑板回读断言"回读体必须含 key"，可 value 里根本没写 key → 明明 landed 却报 `landed=false` | value 里显式带 `key`；回读断言用"键名 + 日期 + 文本标记"三项 |
| 3 | **notify 的 ok 字段不存在** | 短指引明明写入成功，CLI 却显示 ⚠️（`n.ok` 为 undefined，`ok` 混淆了"发送结果"与"是否需人工转发"） | `ok = landed`，与"跳过原因"分开两个字段 |
| 4 | **跨零点空转** | 深夜 00:35 跑 `--rule`，工具只找 `proposals-<今天>.json` → 找不到 → 整条链在午夜后空转 | 提案库按 `proposals-<date>` → `proposals.json` → 最近 3 份**回退**并**明说**；**裁定文件刻意不自动回退**（那是权威人工输入，替人挑=越权） |
| 5 | **半夜的"编号冲突"是别人写的** | 真库在我工作期间被另一会话改了（哲学 2.4→1.6、11→13 条），若我按旧快照写入就会丢他们的更新 | 计划阶段记录每个目标文件的 sha256，apply 前**复核**：不一致即 `CONCURRENT_MODIFY` 拒写 |
| 6 | **凭据扫描"0 命中"不等于测过** | 探针把凭据放在规则 `detail` 里，而卡面取的是 `summary` → 卡里本来就没有凭据，脱敏链路**没被真正执行** | 探针改成让凭据**流经**卡与黑板值；并把 `redactDeep` 升级为**计数版**，输出现「凭据脱敏 N 处（openai-key,assigned-secret）」+ 通知卡里可见 `«REDACTED:…»` |
| 7 | **自己写的门会误伤自己（第二次）** | 扫"是否 import 了 child_process"时，扫到我自己**文档里写的** "不 import child_process" → 假阳性 | 扫描改成分离注释、**保留字符串**，只匹配 import/require 的**模块说明符** |
| 8 | **函数体定位踩参数默认值** | F 项靠大括号配对找函数范围，`function bbRequest(a, b, { timeoutMs = 3000 } = {})` 的第一个 `{` 是**解构参数** → 范围算错、`fn=null` | 先跨过参数表（括号配对），再找函数体的 `{` |
| 9 | **`--dry-run` 只测了文件** | 起初只比对文件 sha256 | 套件额外断言两个黑板的 **PUT/GET 计数前后一致**（含中央黑板），dry-run 才是真零变更 |
| 10 | **回滚自检用了不存在的字段** | `backupFile()` 返回 `{path,bytes,verified}` 没有 `sha256`，回滚自检却拿它比对 → **回滚成功却报"sha256 不一致"**，日志里长期挂假 `rollbackErrors` | `backupFile` 真正算 `sha256`；自检改为"实际回读 ≠ 备份才报错"，并输出 `matched` |
| 17 | **只信"当前字段"而没有旁证 → 把别人的错固化下去** | 库的 `version` 被写成 1.4（应为 2.4）时，我的 `bumpMinor` 照样算出 1.5 —— **我成了错误的放大器**，而且我这一侧没有任何机制能发现"基准本身错了" | 用**同文件内的旁证**（changelog/versionHistory 里的历史版本）做单调性校验；基准低于历史 → 拒写并交人修复。★ 教训：**只读一个字段就动手的工具，会把上游的错误变成自己的输出** |
| 16 | **URL 语义字符在"键"里的真实语义与直觉相反** | 我原以为 `data/dom/a?b` 会写成"查询串"导致写 A 读 B —— 实测黑板把 `?`/`#` 当**键名字面量**（404=语法合法），**我的假设被证伪**；而真正会 400 的是 `% & ; + = :` 与非 ASCII，两者旧校验器都放行 | 只拒**实测**判定的字符类（400 的、路径归一化的），不按直觉设规则；每条规则都用"真键全集零误伤"验证 |
| 15 | **修复动作改写"事件时点"**（HR 2026-09-11 指出，自查发现我也有） | 本工具每次入册都把 `releasedAt` 覆盖为写入时刻且不留原值 → 用"新的不精确"替换"旧的滞后"；**旧错看得见（明显滞后），新错看不见（长得像正经时点）** | 新增 `releasedAtHistory[]` 留档原值 + 记录 cause/by；回读校验断言"原值已留档"与"事件时点/写入时点分列" |
| 14 | **尾斜杠键把"全库列举"当成回读值** | `GET /data/reflect/` 返回 **200 + `{list,total}` 全库列举** —— 列举里**必然**含有你刚写的键字符串，于是"回读含标记即落地"的判据在尾斜杠键上**必然假通过**；写它其实只是往命名空间端点打（不是写键） | ① key 规则要求**≥2 段且每段非空**（单段/尾斜杠/空段一律拒）② 传输层再拦一次 ③ 落地判据加**内容深比对**，不再只看标记 |
| 13 | **"回读 200"被当成"落地了"** | R003 补充通告点名：`400`（键错，你以为写了其实被拒）与 `404`（不存在）语义不同；更隐蔽的是**空壳键**——键在、`value={}`，**只看状态码必漏**（今日 4 起"报告指向不存在的落盘物"事故） | 落地判定改为三合一：**回读 200 + `value` 非空 + 内容命中标记**；分类器把 400/404/空壳/标记未命中分别定性并写进诊断；非法 key 在本机就拦，不发非法请求 |
| 12 | **把"参数写错"报成"门拒绝"** | `--rule P4=approve:repository` 的枚举只在门阶段校验 → exit 1；用户按"门拒绝"去查权限，实际该查的是自己敲的参数 | CLI 语法与冻结枚举都在**解析期**校验 → exit 2；外部数据（裁定文件）里的非法值仍走门 → exit 1，两类语义分开并在文档写明 |
| 11 | **只测了一条失败路径就以为测过了** | 起初只注入 IO 失败（`rename EPERM`），而"写入成功但内容不对"是**另一条**路径（走回读校验）；第一次注入还因内容被改成非法 JSON 而**落在 rename 前的 validate 上**，完全没碰到回读 | 注入要打在**校验**上：写入合法 JSON 但内容不对 → `VERIFY_FAILED` 并列出未通过项；并把四类坏产物直接喂给判据证明其**可证伪** |

---

## ⑨ 与治理哲学/规则的关系

- **`phi-user-sovereignty`**：本工具**只执行人的裁定**，从不自己拍板（结构上无该入口）。
- **`phi-constraint-frontloaded`（Φ9 约束前置）**：四条"不该发生路径"由冻结枚举 + 能力缺失 + 幂等门 + 原子回滚封死，并自带 A–F 证明。
- **`R006`⑩**：本工具是继 `dsh-plugin-cldvoice-activate` 之后第二台"带 Lean4 逻辑门"的工具；门型是 **类型锁 + 入口门 + 幂等门 + 值门（凭据）+ 命名空间门**。
- **`R030`（无验证不陈述）/ `R033`（通道治理）/ `R034`（探照灯）**：所有黑板写入都"PUT 后回读"，短消息 ≤50 字、正文一律走黑板。

---

*reflect-enroll · 十项达标 + 跨设备层 v1.1 · 证据全部来自 `/tmp` 副本与桩黑板实测（真库零写入，见自测报告）*
