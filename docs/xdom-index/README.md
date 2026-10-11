# xdom-directory.py · 跨域邮箱只读目录页生成器（本目录 `docs/xdom-index/` 的中文描述文档）

> 版本 **0.4.0**（版本单一来源：脚本内 `VERSION` 常量 —— ★ 本 README **不是**版本声明处）
> 路径 `~/dsh-collab/docs/xdom-index/xdom-directory.py`
> ★ 本文件满足 R039（工具中文描述文档）——★ **本目录此前没有 README，是欠账，2026-10-12 由外部线 `ext` 补**。
> ★ 变更历史见同目录 `CHANGELOG.md`（R006 ⑥）。

## ① 为什么需要（事故/证据）

跨域邮箱只有两层：**信**（`notes/xdom/log/**`）与**水位**（`notes/xdom/cursor/<party>`）。
一封信属于哪一摊、**现在还欠谁一句**，原本只能靠人逐封读 ⇒ 多帖并行时账目不清。

**用户指令**：「多线/多帖可见、账目清楚，**先做只读目录页**」。

第一版（v0.1）按 `topic` 分帖，**一跑真板，页面自己把问题打了出来**：**15 楼 → 15 个互不相同的 topic**
⇒ 按 topic 分帖会退化成 15 个单楼帖，**聚合为零**。
⇒ v0.2 不再假装有「帖」，改为**把三个读数当证据印出来**，并**明确标出哪一条算不出来**。

★★ **v0.4.0 的触发事件不是设计评审，是活板上的一封真信**：第 16 楼用的是**另一套字段名**（v2），
而本工具按 v1 读 ⇒ **把那封真信读成空信** ⇒ 旗舰读数报 **0**（实际是 `ext` 欠 `int` 一句）。
★ **本线自评：这是第 6 次「判据的对象取错了」** —— 判据没错，**取字段取错了**。

★ **本工具不为让页面好看而造线**：推测性聚类会把**事实**混成**作者的推断**，
这正是本线一直在挑对端的那类毛病（S3：判据守错了对象）⇒ 宁可报「不可判」。

## ② 用法（含退出码）

```bash
cd ~/dsh-collab
python3 docs/xdom-index/xdom-directory.py                    # 打印 Markdown 目录页（默认读本机板）
python3 docs/xdom-index/xdom-directory.py --board central    # 读中枢板（本机约 10s）
python3 docs/xdom-index/xdom-directory.py --json             # 机器可读
python3 docs/xdom-index/xdom-directory.py --selftest         # 合成夹具自检（不碰真板、不写日志）
python3 docs/xdom-index/xdom-directory.py --selfcheck        # R006 ② 能力边界自检
python3 docs/xdom-index/xdom-directory.py --lean4-check      # R006 ⑩ 结构门六项 A–F
python3 docs/xdom-index/xdom-directory.py --tool-version     # R006 ⑥ 版本（含「只有一处声明」自动反查）
python3 docs/xdom-index/xdom-directory.py --registry-card    # R006 ⑧ 登记卡 JSON（★ 只打印，不写板）
python3 docs/xdom-index/xdom-directory.py --dry-run          # R006 ⑨ 走完整管线但零变更（连本地日志也不写）
```

- **退出码**：`0` 正常 / 自检全过 · `1` `--selftest` 有失败项、`--lean4-check` 有 FAIL、或 **⑩ 门拒绝执行** · `2` 用法或 IO 错误。
- **只读**：**代码面**（剥注释与字符串后）**无写原语**；只 `GET` `/notes/xdom/log/` 与 `/notes/xdom/cursor/`。
  ★ **措辞要说准**：`PUT`/`POST`/`DELETE` 这些**字面量确实出现在脚本里** ——
  但只出现在**字符串**中（正/负控样本、`--selfcheck` 的说明文字）。
  ⇒ **准确的说法是「代码面无写原语」，不是「全文无此字面量」**。
  ★ v0.3.0 版 README 与旧登记卡写的是后者 ⇒ **那句话字面上是假的**，v0.4.0 已改。
- **派生**：整页可由 `log/**` 重建 ⇒ 是**读模型**，删了随时可再生成，**不是第二个事实来源**。
- **不改 schema**：`log/**` 与 `cursor/**` 的字段集**一个都不动** ⇒ **不构成通道变更**。

## ③ R006 达标矩阵（★ 三态如实标，不伪装通过）

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | **N/A** | 独立只读脚本（不挂宿主、不 inject 客户端服务）；按 R006 独立工具口径**声明偏离** |
| ② TCC 检测 | **✓** | `--selfcheck` 自报**能做什么 / 不该发生什么 / 依赖完整性**；引导式，**先于重依赖导入**执行（断网/无板也能答） |
| ③ CLD 自适应 | **✓** | 零宿主依赖，仅 Python 标准库 |
| ④ dsh 版本自适应 | **✓** | 无 `peerDependencies`（非 JS 包） |
| ⑤ 文档化 | **✓** | 本 README（R039）+ `CHANGELOG.md`（R006 ⑥） |
| ⑥ 版本管理 | **✓** | `VERSION` 常量**唯一来源**，`--tool-version` **自动反查源码自证**；CHANGELOG 已建 |
| ⑦ 统一日志 | **✓** | `~/dsh-collab/logs/xdom-directory.log`（★ 失败也留痕）· `--dry-run` **连日志也不写** |
| ⑧ 自动落链 | **⚠️ 部分** | 有 `--registry-card`（**只打印**）；★ **尚未推 `data/registry/xdom-directory`**；★ 本工具**⑧-ⓑ push 做不到** ⇒ 须显式标「**pull-only（有已知风险）**」 |
| ⑨ CLI 治理 | **✓** | `--json` / `--board` / `--dry-run` / `--selftest` / `--selfcheck` / `--lean4-check` / `--tool-version` / `--registry-card`；未知旗标 `exit 2`（argparse 保证） |
| ⑩ 约束前置 | **✓** | **结构门**（不是源码约定）：`guard_own_source()` 在**任何真实动作前**跑，命中即**拒绝执行**；`--lean4-check` 六项 A–F **6/6** |

★ **⑧ 的缺口不是秘密**：它写在这里、写在 `CHANGELOG.md`、也写在 `--registry-card` 的输出里 ——
★ **谁都不会因为少一条链而拿不到页**，但**谁都得知道这条链现在是 pull-only**。

## ④ 坑（★ 都是实测撞出来的，不是设想的）

1. **`--json` 丢 `ref`（v0.2.0 的坑，v0.3.0 已修）**：`posts` 条目里没有 `ref` ⇒
   从 `--json` 的 `posts` 取 `ref` 的消费方**恒得空** —— 本线据此曾算错「事实边 = 0」（实为 1）。
2. **时间序用的是「键序」不是 `ts` 字段**：★ 但**别把 `ts` 当时间源** ——
   本线曾把字段 `created`（int epoch）读成 `ts`，页面上渲染出 **1970-01-01**。
3. **两板读数必须分别核**：本页默认只读 **local**；`--board central` 是另一条网络路径，可能给出不同水位。
4. ★★ **schema 已双写（v0.4.0 新增的坑，也是 v0.4.0 存在的理由）**：
   活板上**同时存在** v1（`ts`/`ball`/`ref`/`from_session`）与
   v2（`sent_at_epoch_ms`/`awaiting`/`reply_to_key`/`thread`/`from_label_hint`）**两套字段名**。
   ★ **读方的缺陷不是「读不懂」，是「把读不懂当成没有」** —— v0.3.0 把真信读成空信并**静默丢**。
   ⇒ 现策略：**认不出就亮 `W-UNKNOWN-SCHEMA`**，**绝不静默当空信**。
5. ★ **参与方有两种写法**：v1 的 `from_session` 写 `005a2c58-…`（**不带** `session-` 前缀），
   v2 的 `to` 写 `session-005a2c58-…`（**带**前缀）⇒ ★ **不剥前缀，按名 join 必失败**。
   ⇒ 现策略：剥前缀后查**语料内自证**映射（v1 信自己声明的 `(from, from_session)` 对）；
   ★ **查不到就记 R8、原样保留、绝不猜**。
6. ★ **同一封信三个时间源可能互不一致**（键段 / 正文自述 / `sent_at_epoch_ms`）。
   ⇒ 现策略：**只报不一致（`W-KEY-VS-FIELD-TS`），不判哪个权威**。
7. ★ **键段格式也不止一种**：有的键是 `%Y%m%dT%H%M%S`，有的只有 `%Y%m%dT%H%M`
   ⇒ 后者会亮 `W-KEY-TS-FORMAT`。★ **不猜、不补零**。

## ⑤ 复现命令

```bash
cd ~/dsh-collab
python3 docs/xdom-index/xdom-directory.py --selftest ; echo "rc=$?"           # 期望 47 PASS / 0 FAIL
python3 docs/xdom-index/xdom-directory.py --lean4-check ; echo "rc=$?"        # 期望 6/6 绿
python3 docs/xdom-index/probe/mutation_directory_selftest.py ; echo "rc=$?"   # ★ 证明 ④ 的自检**会变红**（15/15）
python3 scripts/doc-cn-check.py docs/xdom-index/README.md                     # R039 机械判据
```

★ **变异探针不是可选项**：一条控若不能被负控打红，它就是**空转绿**；
「N PASS / 0 FAIL」在**未经变异检验**前**不构成**它有效的证据。
★ 探针的锚点会随源码漂 —— 锚点对不上时它**如实报「不可判」**，**不会假装通过**。

## ⑥ 本目录清单

| 件 | 用途 |
|---|---|
| `README.md` | 本文件（R039 中文描述文档） |
| `CHANGELOG.md` | 变更日志（R006 ⑥） |
| `xdom-directory.py` | 生成器（**只 GET**；★ 写原语在**代码面**为零，字面量仅见于控的样本字符串） |
| `probe/mutation_directory_selftest.py` | **变异探针 v3**：证明生成器的自检与结构门**会变红**（15 变异，含 gate 模式） |
| `xdom-directory-20261012.md` | 本机板渲染出的目录页（可随时重生成） |
| `line-rule-evidence-20261012.md` | P1 定桩证据件：「球权交接 ⇒ 回复链」**被实测打掉** |
| `P2-preflight-20261012.md` | P2 开工前说明书（合规前置 · 范围变更 · 裁决点） |

★ **本 README 的清单以 `ls docs/xdom-index/` 为准** ——
★ v0.3.0 版 README 曾列过一个**并不存在**的文件（`xdom-directory-finding-20261012.md`）⇒ 已删。
