# dsh-plugin-item-validity-review-check

> 对「一条卡 / 一条待办 / 一个条目」快速回答**「它现在还有效吗」**：先分形态，再给**五态**，附**每态所依赖的条件量**与**盲区声明**。

R006 十项交付 · PSTD `PSTD/1.0.4` 模式 `P2_bundled_plugin` · 工具 `item_validity_*`（4 个）
数据源 P0：`~/.dsh/inbox/*.json`（本机实测 **2642** 条）

---

## 一、为什么需要（事故/证据）

| 证据 | 后果 | 本插件的处置 |
|---|---|---|
| 插件缺 `type: module` ⇒ CLD 启动崩溃 | 整包不可用 | `package.json` 有 `type: module`，纯 ESM |
| `defineTool` 的嵌套 object 缺 `additionalProperties` ⇒ `UNSUPPORTED_SCHEMA` ⇒ `apply()` 崩 | **九项全绿却根本挂不上** | 输出 schema 显式写 `additionalProperties`；`--selfcheck` 带**真挂载冒烟**（pass/fail/skipped 三态如实分报） |
| 「单一窗判记录体」：`~/.dsh/inbox` 2624 条里 **1111 条 stale > 动作项 433 条** 的悖论 | 把「历史事实」当成「过期待办」 | **先分形态**：记录体/回执/流水 ⇒ `n/a`，其年龄不构成失效理由 |
| 「形态判不了」被并入 `n/a` | 把「**判不了**」说成「**不适用**」 | 形态判不了 ⇒ `unknown`（负例第 4 条抓出） |
| 盲区声明与末行报数自相矛盾（声明「看不到是否被回」却又把 open 报成「仍有未决待办」） | 过度断言 | 每份输出必带盲区声明；`open` 的含义固定为【无关闭声明且无可见回复】 |
| `reply_to` 载体**不统一**（实测：黑板键 159 · 短 id 2 · **空串 22** · 其它 72） | `if (reply_to)` 漏空串 | 判据**三分**：短 id / 黑板键 / 空串（空串按「未提供」处理） |

★ **本插件唯一的新判据**是「回复可见性」三通道（A 卡内指针 / B 线程记录 / C 指针形态）——
它把「无显式关闭声明」与「已在可见通道被回复」区分开。实测当前 inbox：通道 A 命中 3 条、通道 B 命中 34 条、通道 C 有效指针 270 条（解析到 3 条）。

---

## 二、用法与退出码

### 旗标

```
node cli.js --source inbox                  # 全量扫描（五态 + 形态计数）
node cli.js --json --source inbox           # 机器可读全量（含逐条 conditions）
node cli.js --key <文件名|去.json|key字段>   # 判一条
node cli.js --list closed                   # 只列某一态
node cli.js --max-age-days 14               # 覆盖时效窗（窗值必打印）
node cli.js --write-index                   # 写索引（默认 dry-run，零变更）
node cli.js --write-index --confirm         # 真写（写临时文件→原子改名→回读断言）
node cli.js --dry-run                       # 零变更演练
node cli.js --selftest                      # 正/负例矩阵（27 条）
node cli.js --selfcheck                     # 三段：能力清单 / 不该发生路径 / 依赖完整性
node cli.js --lean4-check                   # 约束门六项 A–F
node cli.js --tool-version                  # 版本（唯一来源 package.json）
node cli.js --help
```

### 退出码

| 码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 门失效 / 判 fail |
| `2` | 用法或 IO 错误（**未知旗标一律 2**） |

### 四个工具（名字已过命名门，不得改）

| 工具 | 访问 | 作用 |
|---|---|---|
| `item_validity_check` | 只读 | 判一条：形态 + 五态 + 条件量 + 盲区 |
| `item_validity_batch` | 只读 | 全量扫描：五态计数 + 形态计数 + 逐条行 |
| `item_validity_explain` | 只读 | 判据链 + 依赖条件量（可传 `sample` 离线推演） |
| `item_validity_index_write` | **唯一可写** | 写 `~/dsh-collab/docs/item-validity-index.json`；`dryRun` 默认 `true`，须 `confirm:true` |

### 判定阶梯（自上而下，命中即返回）

```
0  非 JSON 对象                    → unknown（写明缺的是什么 + 怎么补）
1  形态判不了                      → unknown（**不得**并入 n/a）
2  状态类字段命中关闭词             → closed（① 显式声明，最强）
3  非动作项（record/feed/ack）      → n/a（不对它谈有效性）
4  通道 A 命中（卡内指针）           → closed（写明 A）
5  通道 B 命中（线程记录）           → closed（写明 B）
6  缺时刻                          → unknown（缺 ≠ 没有）
7  超窗 / 已被取代                  → stale（窗值打印在理由里）
8  通道 B 适用却未见回复            → unknown（强制理由：未观测到回复，但本插件看不到线程外的回复）
9  其余（无关闭声明、无可见回复）     → open（含义见盲区声明）
```

**词表只作用于状态类字段**（`status`/`state`/`verdict`/`resolution`/`result`/`still_pending_user`/`awaiting_user`/`needs_user`），
**绝不在正文里找**——否则正文里出现「已完成」三个字就会被误判。

**时效载体**：`sent_at_epoch_ms`/`ts_epoch_ms`/`created_at_epoch_ms`（ms 数字，>1e11）
或 `ts`/`at`/`measured_at`/`created_at`（ISO 串）。一律按 **UTC** 解释；字符串无时区时
**在理由里写明该假设**（`（ts 无时区 ⇒ 按 UTC 解释，此为假设）`）。

**三通道**：A 中强度 · B 强强度 · C 弱强度（**只作参考信息，不得据此判 closed**）。

---

## 三、R006 达标矩阵

| 项 | 判据 | 证据（可核验） |
|---|---|---|
| ① dsh 插件形态 | package.json + cordis.patch.yml + `apply` + 真挂载冒烟 | `--selfcheck` 冒烟 `pass`，注册 4 个工具；`node -e 'import(...)'` → `name/inject/apply` |
| ② TCC 自检 | 三段输出 | `--selfcheck`：① 能力清单（4 工具 + 只读/可写） ② 不该发生路径 **9 条拒绝证明** ③ 依赖完整性 |
| ③ CLD 自适应 | 只依赖 node 内置 + peer | `lib/*.js` 仅 `node:fs`/`node:path`/`node:os`/`node:crypto`/`node:url` |
| ④ dsh 版本自适应 | peerDependencies 全声明 | `@deepseek-ai/cordis` + `@deepseek-ai/dsh-tools`，两级解析（plugin → profile） |
| ⑤ 文档化 | 本文件 + `r006.documented` | 五节齐（为什么/用法与退出码/达标矩阵/坑/复现命令） |
| ⑥ 版本单一来源 | `package.json` 唯一 | `--tool-version` 现读；源码内无第二处版本硬编码 |
| ⑦ 统一日志 | `~/dsh-collab/logs/dsh-plugin-item-validity-review-check.log` | 每次判一条一行 JSON `{ts,tool,source,shape,state,why,channel,elapsed_ms}`；**unknown 也写** |
| ⑧ 自动落链 | `data/registry/dsh-plugin-item-validity-review-check` | 见「未做到」一节（未登记） |
| ⑨ CLI 治理 | 未知旗标 exit 2 / 退出码 0·1·2 / `--dry-run` 零变更 / `--json` / `--help` | `node cli.js --bogus` → exit 2；`--lean4-check` D 项 sha256 实测零变更 |
| ⑩ 约束门 | 冻结枚举 + 负例矩阵 + 命令白名单 + 六项 A–F | `--lean4-check`：A 真扫 `lib/*.js`（剥字面量）· B **14 条**负例 · C **8 条**正例 · D sha256 · E `Object.isFrozen` · F 12 个调用点 ⊆ `{node}` |

---

## 四、坑（都踩过）

1. **门太宽**：把合法键也当违规。⇒ **先精确枚举命中**，再对非白名单输入判「路径类」原因（否则「禁止路径」的正则会误伤合法值）。
2. **扫描器误伤自己**：直接扫原文，会把自己的检测清单与帮助文本当成靶子。⇒ 先**剥注释/字符串/正则字面量**再扫（本文件里的词表本身是字面量，被剥掉后不会自命中）。
3. **空洞通过**：剥离字面量后读不到实参 ⇒ 调用点枚举为 0 ⇒「0 ⊆ 允许」假通过。⇒ F 项**显式判空集失败**；A 项附**正向对照**（人造样本必须被扫出来，本次 5 行命中 4 个原语）。
4. **假失败**：依赖解析不到就断言「插件挂不上」。⇒ 两级解析，并区分「环境问题」与「包问题」；本目录 `node_modules` 是指向 CLD runtime 的符号链接（见下）。
5. **两处版本**：`const VERSION` 与 `package.json` 各写一份必然漂移。⇒ 只留 `package.json`，`--tool-version` 现读。
6. **`if (reply_to)` 是错的**：`reply_to` 三种载体混用，**空串**（实测 22 条）会被真值判断漏掉。⇒ 判据**三分**：短 id / 黑板键 / 空串；空串按「未提供」处理，不算命中也不报错。
7. **单一窗判记录体**（移植自 Python v1.0 的错）：一个时效窗同时装「回执」与「待办」⇒ 出现 `stale 1111 > 动作项 433` 的悖论。⇒ 先分形态，只对动作项谈时效。
8. **形态判不了 ≠ 不适用**：「不知道它适不适用判据」与「它不适用判据」是两个结论。⇒ 前者报 `unknown`（负例第 4 条）。
9. **盲区声明与末行报数自相矛盾**：声明「看不到是否被回」，却把 `open` 报成「仍有未决待办」。⇒ 声明与报数同源同措辞。
10. **隐藏文件**：`~/.dsh/inbox` 里有一个 `.lock-ask-auto-hello.json`（点开头）。`ls *.json | wc -l` = 2641，而 `readdirSync` 数到 **2642** —— 少算 1 条会让你在「总数对不上」上白花时间。
11. **★ 规范里两处要求的口径张力（本题必须如实说明）**：§2 的 `open` 定义是「动作项、窗内、无关闭声明、无可见回复」，而 §3 的合成规则写「A/B 都不命中 ⇒ 报 unknown，不得报 open」。两条按字面在同一个条件上给出不同结论。**本实现的处置**：把 §3 适用于「回复通道**可观测**」的条目（本条带 `thread` ⇒ 我们确实查了该线程，查到没查到都只能叫 `unknown`）；不带 `thread` 的条目没有可观测的回复通道，其结论就是 §2/§4 的 `open`，由盲区声明兜底。**两种口径的计数都输出**（`tally` 与 `strictTally`），若采严格读法，把 `ctx.strictNoReply = true` 一处打开即可全量切换。
12. **peer 解析**：本目录的 `node_modules` 是指向 `/Applications/CLD.app/.../runtime/node_modules` 的符号链接（本地 dev 用）。没有它，`node -e 'import(...)'` 会 `ERR_MODULE_NOT_FOUND`；`--selfcheck` 会如实标 `skipped` 而**不是**假装通过。

---

## 五、复现命令

```
cd ~/dsh-collab/devices/dsh-plugin-item-validity-review-check

node cli.js --selfcheck                     # 三段 + 真挂载冒烟（期望 exit 0）
node cli.js --lean4-check                   # A–F 六项（期望 exit 0）
node cli.js --tool-version                  # 1.0.0
node cli.js --dry-run                       # 零变更演练
node cli.js --selftest                      # 27 PASS / 0 FAIL
node cli.js --json --source inbox           # 真实扫描（2642 条）
node cli.js --bogus                         # 未知旗标（期望 exit 2）

# 索引 dry-run 零变更 sha 比对
shasum -a 256 ~/dsh-collab/docs/item-validity-index.json
node cli.js --write-index                   # 不改文件
shasum -a 256 ~/dsh-collab/docs/item-validity-index.json   # 应完全一致

# 入口导出
node -e 'import("./lib/index.js").then(m=>console.log(Object.keys(m)))'
```

**本机实测（2026-10-09，2642 条 inbox）**

| 五态 | closed | stale | open | unknown | n/a |
|---|---|---|---|---|---|
| 计数 | 3 | 2 | 397 | 135 | 2105 |

| 形态 | action | record | feed | ack | unknown |
|---|---|---|---|---|---|
| 计数 | 433 | 1396 | 709 | 3 | 101 |

`⇒ 需判有效性的只有动作项 433 条`（与 Python 参考实现 v1.2.3 的 433 一致 ⇒ 形态判据已对齐）。
严格口径计数：`{closed:3, stale:0, open:0, unknown:534, n/a:2105}`。

---

## 附：盲区声明（每份输出必带）

```
★ 盲区：本插件只看条目本身 + 可见线程。看不到：只发在线程里未落盘的回复 /
  我未参与的线程 / 未持久化的会话。⇒ open = 【无关闭声明且无可见回复】，
  不等于【确定仍有未决待办】。
```
