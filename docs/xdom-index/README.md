# xdom-directory.py · 跨域邮箱只读目录页生成器（本目录 `docs/xdom-index/` 的中文描述文档）

> 版本 0.2.0（版本单一来源：脚本内 `__version__ = "0.2.0"`）
> 路径 `~/dsh-collab/docs/xdom-index/xdom-directory.py`
> ★ 本文件满足 R039（工具中文描述文档）——★ **本目录此前没有 README，是欠账，2026-10-12 由外部线 `ext` 补**。

## ① 为什么需要（事故/证据）

跨域邮箱只有两层：**信**（`notes/xdom/log/**`）与**水位**（`notes/xdom/cursor/<party>`）。
一封信属于哪一摊、**现在还欠谁一句**，原本只能靠人逐封读 ⇒ 多帖并行时账目不清。

**用户指令**：「多线/多帖可见、账目清楚，**先做只读目录页**」。

第一版（v0.1）按 `topic` 分帖，**一跑真板，页面自己把问题打了出来**：**15 楼 → 15 个互不相同的 topic**
⇒ 按 topic 分帖会退化成 15 个单楼帖，**聚合为零**。
⇒ v0.2 不再假装有「帖」，改为**把三个读数当证据印出来**，并**明确标出哪一条算不出来**
（`现在还欠谁一句` = **不可判**，因为缺「回复链」载体）。

★ **本工具不为让页面好看而造线**：推测性聚类会把**事实**混成**作者的推断**，
这正是本线一直在挑对端的那类毛病（S3：判据守错了对象）⇒ 宁可报「不可判」。

## ② 用法（含退出码）

```bash
cd ~/dsh-collab
python3 docs/xdom-index/xdom-directory.py                    # 打印 Markdown 目录页（默认读本机板）
python3 docs/xdom-index/xdom-directory.py --board central    # 读中枢板（本机约 10s）
python3 docs/xdom-index/xdom-directory.py --json             # 机器可读
python3 docs/xdom-index/xdom-directory.py --selftest         # 合成夹具自检（不碰真板）
python3 docs/xdom-index/xdom-directory.py --version
```

- **退出码**：`0` 正常 / 自检全过 · `1` `--selftest` 有失败项 · `2` 用法或 IO 错误（`argparse` 未知旗标 + 网络异常）。
- **只读**：全文**无 `PUT`/`POST`/`DELETE` 字面量**；只 `GET` `/notes/xdom/log/` 与 `/notes/xdom/cursor/`。
- **派生**：整页可由 `log/**` 重建 ⇒ 是**读模型**，删了随时可再生成，**不是第二个事实来源**。
- **不改 schema**：`log/**` 与 `cursor/**` 的字段集**一个都不动**。

## ③ R006 达标矩阵（★ 三态如实标，不伪装通过）

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | **N/A** | 独立只读脚本（不挂宿主）；按 R006 独立工具口径**声明偏离** |
| ② TCC 检测 | **⚠️ 部分** | 有 `--selftest`（14 控）+ **变异探针**证明它会变红；★ 但**未按 R006 ② 口径导出 `--selfcheck`**，且**不自报「不能做什么」** |
| ③ CLD 自适应 | **✓** | 零宿主依赖，仅 Python 标准库 |
| ④ dsh 版本自适应 | **✓** | 无 `peerDependencies`（非 JS 包） |
| ⑤ 文档化 | **⚠️ 补课中** | 本文件即补课件；此前**缺 README** ⇒ R039 欠账 |
| ⑥ 版本管理 | **⚠️ 部分** | `__version__` 单一来源在脚本内；★ **无 CHANGELOG** |
| ⑦ 统一日志 | **✗ 缺** | 无固定日志（R006 ⑦ 要求落 `~/dsh-collab/logs`） |
| ⑧ 自动落链 | **✗ 缺** | 未登记 `data/registry/`，未进 R039 冻结清单 `scripts/tool-doc-manifest.json` |
| ⑨ CLI 治理 | **⚠️ 部分** | 有 `--json` / `--board` / `--version`；未知旗标 `exit 2`（argparse 保证）；★ 只读故无「dry-run」语义可谈 |
| ⑩ 约束前置 | **⚠️ 部分** | 「只读」目前是**源码约定**，**不是结构门**；★ 缺 `--lean4-check` 证明 |

★ **未达标项不是秘密**：它们是 P2（v0.3.0）的**开工前置**，见同目录
`P2-preflight-20261012.md`（合规前置实测矩阵 + 范围变更 + 裁决点）。

## ④ 坑（★ 都是实测撞出来的，不是设想的）

1. **`--json` 丢 `ref`**：v0.2.0 的 `build_index()` 把 `ref` **只聚合进 `threading`**，
   **per-post 的 `posts` 条目里没有 `ref`**。
   ⇒ ★ 任何**从 `--json` 的 `posts` 里取 `ref`** 的消费方**恒得空**
   —— 本线据此曾算错「事实边 = 0」「R4 = 7/7」（实为 **1** 与 **6/7**）。
   ★ **对 P2 的硬要求**：`--json` 必须显式给出 `edges_fact` / `edges_inferred` / `undecidable` 三个键。
2. **时间序用的是「键序」不是 `ts` 字段**：键前缀是 `%Y%m%dT%H%M%S`，故排序不依赖各板 `ts` 解析差异。
   ★ 但**别把 `ts` 当时间源** —— 本线曾把字段 `created`（int epoch）读成 `ts`，页面上渲染出 **1970-01-01**。
3. **两板读数必须分别核**：本页默认只读 **local**；`--board central` 是另一条网络路径，可能给出不同水位。

## ⑤ 复现命令

```bash
cd ~/dsh-collab
python3 docs/xdom-index/xdom-directory.py --selftest ; echo "rc=$?"
python3 docs/xdom-index/probe/mutation_directory_selftest.py ; echo "rc=$?"   # ★ 证明 ① 的自检会变红
python3 scripts/doc-cn-check.py docs/xdom-index/README.md                     # R039 机械判据
```

## ⑥ 本目录清单

| 件 | 用途 |
|---|---|
| `README.md` | 本文件（R039 中文描述文档） |
| `xdom-directory.py` | 生成器（**只 GET，全文无 PUT/POST/DELETE**） |
| `probe/mutation_directory_selftest.py` | **变异探针**：证明生成器的自检**会变红**（7 变异） |
| `xdom-directory-20261012.md` | 本机板渲染出的目录页（可随时重生成） |
| `line-rule-evidence-20261012.md` | P1 定桩证据件：「球权交接 ⇒ 回复链」**被实测打掉** |
| `xdom-directory-finding-20261012.md` | 第一版说明书 + 它带出的一条真发现（邮箱缺「线」载体） |
| `P2-preflight-20261012.md` | P2 开工前说明书（合规前置 · 范围变更 · 裁决点） |
