# R006 ② TCC + ⑩ 约束门 · canonical 块说明（U6 批次1）

> 适用对象：`scripts/` 下 10 个核心审查工具（gate-canfail / silent-truncation-lint /
> r006-two-tool-audit / gate-auditor / j44-reuse-gate / toolbox-selftest-sweep /
> selftest-inventory / absence-claim-lint / citation-stale-check / verification-level-lint）。
> 交付人：**session-b250bf9d（PSTD · executor）**；委托与裁决：**session-1ffded95（adjudicator）**；
> 规格提出方：**R006 规格文件本身**（三元分离 · R046）。

---

## ① 为什么需要（有实据）

U6 委托附带的缺口表显示这 10 个工具的 R006 ②/⑩ 大面积不达标。**执行方独立复跑后，实测比表上更差**：

| 观测 | 实测事实 | 证据 |
|---|---|---|
| ② | `gate-auditor` 等的 `--selfcheck` **只打印声明、从不查源码**：它印「本器不执行外部命令」，但不扫描自己 | 旧 `selfcheck()` 正文无任何 `open(__file__)` |
| ② | `r006-two-tool-audit --selfcheck` 只输出 **1 行** | `wc -l` = 0（无换行），实际 1 行 |
| ⑩ | 3 个工具**根本没有** `--lean4-check`（rc=2 用法错） | `toolbox-selftest-sweep` / `absence-claim-lint` / `citation-stale-check` |
| ⑩ | **1 个工具静默忽略它并 rc=0** —— 看起来像 PASS，其实什么都没做 | `audit-criteria-triage --lean4-check` → 跑了默认动作 |
| ⑩ | 已有的 A–F 多为**浅 grep**，其中 F 是「本函数自身可跑」＝同义反复 | `selftest-inventory` 旧 F：`callable(lean4_check)` |

> ★ **自指讽刺**：`gate-auditor` 的本职就是抓「**纸面门** = 声明了门、却无结构约束、靠人执行可跳过」——
> 而它**自己的 `--selfcheck` 正是纸面声明**，参数层也不设防（见 ④）。

### ★ 与缺口表的两处口径分歧（executor 独立核实，非对抗）

1. 表判 `gate-canfail` / `silent-truncation-lint` / `r006-two-tool-audit` **②PASS**，判据是
   「有 `--selfcheck` ∧ rc=0 ∧ 源码含 tokenize」。但 R006 §2 ② 的判据是
   「**输出至少三段**：① 能力清单 ② 不该发生路径清单 ③ 依赖完整性」。按规格口径，这三个工具
   的 ② **也不达标**（`r006-two-tool-audit` 只有 1 行）。本批已一并修到规格口径。
2. 表判上述三者 **⑩PASS**，判据是「源码含 `lean4` ∧ rc∈{0,1}」。但 §4.2 要的是
   **A–F 六项自证**。三者原先的 `--lean4-check` 是**免责声明**（"本器无 .lean 规范源…"），
   不是证明。另：`rc∈{0,1}` 会把「**明确拒绝**」（verification-level-lint rc=1）与
   「**静默空转**」（audit-criteria-triage rc=0）**判成同一类**。本批已改为实做 A–F。

---

## ② 是什么（canonical 块做了什么）

每工具注入一段**自包含**块（不依赖任何共享模块 ⇒ 保住「单文件可部署」，
且不触碰尚在待裁的「共享实现·独立验证是否抽模块」议题）：

### ② `--selfcheck`：三段输出 + **7 项结构核验**

判据：**每一句声明都必须被本块核验**；任一项不成立 ⇒ `rc=1`。

```
【① 能力清单】      本器能做什么（并沿用本器【原有 selfcheck() 自述】，不因迁移丢内容）
【② 不该发生路径清单】本器碰不到什么
【③ 依赖完整性】     Python 版本 · 标准库/第三方分类 · 冻结的命令面/写入面 · 日志路径
⇒ 声明核验：N/N 一致   ← 7 项逐条 ✅/❌
```

7 项：依赖无第三方 · 外部命令面与冻结集一致 · 写入面与冻结集一致 · 常量写入点在允许根内 ·
危险原语面与冻结集一致 · 声明的日志路径真实存在于源码 · **声明的正例实测可用**。

### ⑩ `--lean4-check`：A–F，**每项带反空洞**

| 项 | 证明 | 关键点 |
|---|---|---|
| **A** | 危险原语面**全部已声明并冻结** | ★ **不是**「一定没有」—— 三者确有 `os.unlink/rmdir`（清理自建 /tmp）；有则逐条声明，**未声明即红** |
| **B** | 负例全部被拒（**≥2 条**，实测 rc≠0） | 条数下限防"只给 1 条摆样子" |
| **C** | 正例可用（防门太宽） | 默认 rc==0；报告器类可声明 `positive_expect_rc` **并须给出理由** |
| **D** | 零变更 | 见 ③「限度」 |
| **E** | 写入面白名单冻结 | `frozenset` + **变更检测**：新增写入点即红 |
| **F** | 外部命令白名单 | **别名逃逸已覆盖**：`import subprocess as sp; sp.Popen(...)` 也认 |

### ★ 反空洞（本批最重要的一处）

`_r006_scan` 是**扫描器**。若它瞎了，A/E/F 会「0 ⊆ 允许」**空洞通过**（正是 §4.2 坑 3）。
故三项**共用一条前置控制**：扫描器必须先在**合成恶意源**上自证会红 ——
`import subprocess as sp` + `sp.run(...)` + `from subprocess import Popen` 必须被完整检出。
做不到 ⇒ A/E/F 一律判**「不能判定」**，而不是判过。

---

## ③ 限度（如实自陈 —— 请据此打折）

1. **D 是变体，不是实测。** 本批多数工具**没有 `--dry-run`**（⑨③ 缺口，属批次 2），
   故 D 以「**写入面冻结 + 全部写入点在允许根内**」作**结构证明**，输出里显式标 `△ 变体（非实测）`。
   ★ 批次 2 补 `--dry-run` 后，D 会自动升级为实测（`decl["dryrun"]` 填上即可）。
2. **A 的"双通道一致"目前只证明「正则通道没多报」。** AST 通道是主判据；剥离正则通道用于
   交叉验证。若两通道**结论不一致**，A 判「不能判定」。当前 10 个工具两通道均一致。
3. **写入面 `<expr>` 类不作路径校验。** 只校验 `const:` 字面量写入路径是否在 `write_roots` 内；
   动态拼接路径（如 `os.path.join(LOG_DIR, ...)`）只作**变更检测**（新增/改动即红），不做前缀断言。
4. **E/F 是「变更检测器」而非「能力证明器」。** 它们保证「**引入新的危险面会被发现**」，
   不保证「现有危险面是安全的」—— 后者靠 ④ 的 `allowed_danger` 逐条人工理由。
5. **块是复制的，不是共享模块。** 10 份 24 KB 块的重复是**为保「单文件可部署」而付的代价**；
   若「共享实现·独立验证」议题裁决为可抽模块，应重构成共享件并保留独立的验证通道。

---

## ④ 注入机制与坑（后来者照做）

```bash
python3 scripts/r006-tcc-lean4/r006-u6-apply.py --dry-run   # 只看将改什么
python3 scripts/r006-tcc-lean4/r006-u6-apply.py --apply     # 真写（自动备份）
python3 scripts/r006-tcc-lean4/r006-u6-apply.py --verify    # 20 项实跑复验
python3 scripts/r006-tcc-lean4/r006-u6-negctl.py            # 负控 4/4（证明它会红）
```

| # | 坑 | 表现 | 修法 |
|---|---|---|---|
| 1 | **本器自己先拒掉自检旗标** | `selftest-inventory`/`verification-level-lint` 在**模块级**校验 argv ⇒ 末尾的块来不及接管，`--selfcheck` 被当非法参数拒（rc=2/1） | **早期旗标垫片**置于 docstring 之后，先摘出三旗标暂存，由末尾块统一分派 |
| 2 | **块放太前会丢自述** | 块若置于文件头，其守卫在 `def selfcheck()` 之前触发 ⇒ 取不到本器原有自述 | 块放**最后一个 `if __name__ == "__main__":` 之前** |
| 3 | **先截断再序列化** | `json.dump(o, open(p,"w"))` 序列化抛异常 ⇒ 留下**被截断的** `decls.json`（本器第一版就踩了） | 先 `json.dumps` 成字符串，再 `open(p,"w").write(...)` |
| 4 | **别名逃逸** | 旧扫描器用正则 `subprocess\.run\(` ⇒ `import subprocess as sp; sp.run(...)` **扫不到** | AST + **import 别名解析表**；并用合成源反证 |
| 5 | **同义反复的检查** | 第一版本块里有一项「Python 版本读数非硬编码」= 读自己刚打印的行 ⇒ 恒真 | 改为「声明的正例**实测**可用」等**跨进程**可证伪项 |
| 6 | **负例选到幽灵旗标** | `gate-auditor --rules` 曾被当合法首参数 ⇒ 负例 rc=0 | 负例失败先查**被检物**是否真错：`--rules` 只在 `scan` 子分支内被消费 ⇒ 作首参数即幽灵旗标 |

---

## ⑤ 实测证据（可复现）

| 项 | 命令 | 结果 |
|---|---|---|
| 20 项实跑 | `python3 scripts/r006-tcc-lean4/r006-u6-apply.py --verify` | **20/20 rc=0** |
| 负控矩阵 | `python3 scripts/r006-tcc-lean4/r006-u6-negctl.py` | **4/4**：M1 新增 `os.system`→**A 红**；M2 越界常量写入→**E 红**；M3 别名 `sp.Popen`→**F 红**；M4 扫描器致盲→**A,B,D,E,F 红 + 反空洞控制触发** |
| 回归 | 各器 `--selftest` 与默认主路径 | 行为未变（selftest 全 rc=0，除既有的 selftest-inventory rc=2 / verification-level-lint rc=1） |
| 第三方复评 | `r006-two-tool-audit.py --tool <10 器>` | **② 10/10 PASS · ⑩ 10/10 PASS**（原 ② 2、⑩ 3） |

★ **M4 是这套设计的关键证据**：它证明**若无反空洞控制，M1–M3 会假绿**。

---

## ⑥ 本批顺带修出的真实缺陷（由 B 项逼出，非"顺手改"）

- **`gate-auditor` 参数层不设防**：`--definitely-not-a-flag` → **rc=0**（静默忽略、照跑默认扫描）；
  `--rules` 作首参数同样是幽灵旗标（只在 `scan` 子分支内被 `args.index("--rules")` 消费）。
  ⇒ 补严格校验：未知首参数 → `rc=2` + 列出可接受参数。
  ★ 该器本职是抓「纸面门」，而**它自己参数层就是纸面门**。

---

## ⑦ 未结项（交 adjudicator）

1. **`audit-criteria-triage.py` 未纳入本批** —— 它是**一次性分析脚本**（无 argparse、无函数、
   顶层直接跑完即落盘 `/tmp/u7/verdicts.json`），**没有可复用输入面**；而 R006 ① 的反例正是
   「只有 `.py` 无 CLI 包装的裸脚本」。**把它工具化是一个"形态决策"，不是缺口补丁**：
   - 选项 A：工具化（加 argparse + `--input` 读判据表，内置表作默认集）
   - 选项 B：**按报告产物归档**（它是一次 U7 分析的产出，其结论已落盘）
   ★ 需 adjudicator/owner 裁形态；不作此裁决前我不擅自重构，以免毁掉一次性产物。
2. **⑧ 自动落链 10/10 UNCHECKED** —— 口径差（本方按默认注入面判 PASS，审查器按静态字面量判 UNCHECKED），
   维持原判为**非缺口**。
3. **D 的实测化**依赖批次 2 的 `--dry-run`（⑨③）。
4. **`selftest-inventory` 无可表示的成功退出码**（任何合法调用都 rc=1）⇒ 「0=成功」在该器不可达，
   属 ⑨② 缺口，留批次 2。（本批 C 项以 `positive_expect_rc=[0,1]` + 显式理由暂过，**不是免检**。）
