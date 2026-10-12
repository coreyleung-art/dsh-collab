# R-M2 · 篇四 · `§0.3 Wave S 交付清单` 那类「已交付」怎么复核

> **出件**：v7 调研代理 R-M2 · 2026-10-12（+08:00）
> **对象**：`docs/distributed-agent-network-governance-plan-v6.1-20261011.md` **§0.3 Wave S 实际交付清单**（`:302-322`，七件工具）
> **本仓先例**：核字节数 · 核 sha · 核工具是否真跑过
> **纪律**：★ 现测；★ 不照抄 v6.1；★ 只读，不改 `docs/`。

---

## §0 一句话结论

**§0.3 的【字节数】七件全对、【结构门六项】七件全绿 —— 这两条【经得起复核】；**
**但【功能跑】当场判红：`gcr-gate.py` 实跑 `PASS 6 · FAIL 2 · N-A 9`，`exit=1`，输出逐字「❌ 有 FAIL ⇒ 禁止推进/重启」。**
★★ **⇒ 「已交付」与「当前通过」是两件事；`§0.3` 的清单只证前者，而它被 `§10:1708` 记作「✅ 覆盖 17 条」⇒ 该写法会被读成后者。**

---

## §1 可复跑的五步复核规程（★ 本件核心产出）

| 步 | 核什么 | 命令 | **红条件** | 本件实测 |
|---|---|---|---|---|
| **① 实体在否** | 文件/脚本确实存在 | `ls -la tools/<f>` | 不存在 = 红 | ✅ 七件全在 |
| **② 字节数** | 与清单声称**逐字相等** | `stat -f%z tools/<f>` | 不等 = 红 | ✅ **7/7 相等** |
| **③ sha256** | 内容指纹（防「同长不同物」） | `shasum -a 256 tools/<f>` | ★ 无基线 ⇒ **报「无基线可核」**，**不得报绿** | 🟡 **§0.3 无 sha 栏** ⇒ **无基线** |
| **④ 真跑过没** | 三个独立读数**分开报**：`--selftest`（负控资格）/ `--lean4-check`（结构门）/ **无参功能跑** | 见 §2.3 | 任一面非 0 退出 = 该面红 | 🔴 **功能面 `gcr-gate` exit=1** |
| **⑤ 「已交付」≠「当前通过」** | 清单里的**限定语**是否随数字一起被引用 | 人判 + 逐字比对 | 限定语被丢掉 = 红 | 🔴 **`§0.3:315`「`N-A` 不是通过」 vs `§10:1708`「✅ 覆盖 17 条」—— 同一事实两处相反** |

★ **★ 第 ⑤ 步是本仓特有、也是本次唯一「抓出新东西」的一步。** 前四步全是核实体；**只有第 ⑤ 步核【文本是否忠实】**。

---

## §2 复跑命令 + 未编辑原始输出 + 退出码

### 2.1 第①②步：实体 + 字节数

```bash
cd /Users/coreyleung/dsh-collab
for f in sandbox-script.py infopack-check.py review-gate.py official-ref-gate.py gcr-gate.py node-claim-gate.py self-destruct-gate.py; do
  printf "%-24s stat=%s sha256=%s\n" "$f" "$(stat -f%z tools/$f)" "$(shasum -a 256 tools/$f | cut -c1-16)"
done
```

**未编辑原始输出**：

```
sandbox-script.py        stat=23760 sha256=f56ff1f0e610013b
infopack-check.py        stat=24953 sha256=23d2268e84498583
review-gate.py           stat=26473 sha256=ccc45dd5859dcb77
official-ref-gate.py     stat=19376 sha256=6e965739f9dea1c9
gcr-gate.py              stat=33157 sha256=f0ba3a585a8e9aa4
node-claim-gate.py       stat=10659 sha256=f640dc494799d102
self-destruct-gate.py    stat=23495 sha256=870504538fd3a6c5
```

**退出码**：`0`

★ **与 `§0.3` 逐项对照**（`v6.1:306-312`）：

| 件 | §0.3 声称字节 | 现测字节 | 判 |
|---|---|---|---|
| S1 `sandbox-script.py` | 23,760 B | **23760** | ✅ |
| S2 `infopack-check.py` | 24,953 B | **24953** | ✅ |
| S3 `review-gate.py` | 26,473 B | **26473** | ✅ |
| S4 `official-ref-gate.py` | 19,376 B | **19376** | ✅ |
| S5 `gcr-gate.py` | 33,157 B | **33157** | ✅ |
| 增① `node-claim-gate.py` | 10,659 B | **10659** | ✅ |
| 增② `self-destruct-gate.py` | 23,495 B | **23495** | ✅ |

★★ **⇒ 7/7 全等 —— 这是一个【能红也能绿】的判据，它现在绿。** 本件如实记：**§0.3 的字节数一栏，经得起独立复核。**
★ **且 7 件 sha256 前 16 位已落盘**（本件首次给出）：**后人可据此判断内容是否被改过**（`§0.3` 原本**无 sha 栏** ⇒ **无基线**，见 §1 第③步）。

### 2.2 第④步之一：结构门 `--lean4-check`

```bash
for t in sandbox-script infopack-check review-gate official-ref-gate gcr-gate node-claim-gate self-destruct-gate; do
  printf -- "--- %s ---\n" "$t"; python3 tools/$t.py --lean4-check 2>&1 | tail -3; echo "[exit=${PIPESTATUS[0]}]"
done
```

**未编辑原始输出（七段，各取尾 3 行）**：

```
--- sandbox-script ---
  ✅ E 白名单冻结（tuple） — DANGEROUS_PRIMS / ALLOWED_CMDS 为不可变 tuple
  ✅ F 外部命令白名单（枚举 0 处 → 断言 ⊆ 12 项） — 命令集 []
  六项：6/6 全绿
[exit=0]
--- infopack-check ---
  六项：6/6 全绿
[exit=0]
--- review-gate ---
  六项：6/6 全绿
[exit=0]
--- official-ref-gate ---
  六项：6/6 全绿
[exit=0]
--- gcr-gate ---
  ✅ F 外部命令白名单（枚举 6 处 → 断言 ⊆ 8 项白名单） — 命令集 ['codesign', 'pgrep', 'ps']
  六项：6/6 全绿
[exit=0]
--- node-claim-gate ---
  ✅ 错误归属不可构造（定理 1）                     Lean=True 运行面=True
  ✅ 不依赖提出者（定理 4）                       Lean=True 运行面=True
  对应性：6/6
[exit=0]
--- self-destruct-gate ---
  ✅ E 判据表冻结（tuple） — SELF_KILLING/SELF_MARKS 为不可变 tuple
  ✅ F 外部命令白名单（枚举 1 处 → 断言 ⊆ ['ps']） — 调用点 ['ps']
  六项：6/6 全绿
[exit=0]
```

★ **⇒ `§0.3` 的「结构门 6/6」栏，7/7 经得起复跑。本件如实记。**

### 2.3 第④步之二：负控资格 `--selftest` / `--selfcheck`

```bash
for t in gcr-gate review-gate infopack-check official-ref-gate node-claim-gate self-destruct-gate sandbox-script; do
  printf -- "--- %s ---\n" "$t"; python3 tools/$t.py --selftest 2>&1 | tail -4; echo "[exit=${PIPESTATUS[0]}]"
done
```

**未编辑原始输出（尾段）**：

```
--- gcr-gate ---
  自证：5/5
[exit=0]
--- review-gate ---
  自证：8/8
[exit=0]
--- infopack-check ---
  自证：5/5
[exit=0]
--- official-ref-gate ---
  自证：4/4
[exit=0]
--- node-claim-gate ---
  自证：6/6
[exit=0]
--- self-destruct-gate ---
  自证：5/5
[exit=0]
--- sandbox-script ---
                         [--protect PROTECT] [--cwd CWD] [--timeout TIMEOUT]
                         [--expect-exit EXPECT_EXIT] [--env ENV] [--json]
                         script
sandbox-script.py: error: the following arguments are required: script
[exit=2]
```

★★ **⇒ 六件「负控曾红」有实跑留痕；`sandbox-script.py` 的 `--selftest` 报错退出 2。**
精确化（★ 不得升格，故再跑一次带位置参数）：

```bash
python3 tools/sandbox-script.py --selftest foo 2>&1 | tail -3 ; echo "[exit=${PIPESTATUS[0]}]"
for t in infopack-check review-gate official-ref-gate gcr-gate node-claim-gate self-destruct-gate; do
  printf -- "%s: " "$t"; python3 tools/$t.py --help 2>&1 | grep -c -- "--selftest"
done
```

**未编辑原始输出**：

```
sandbox-script.py: error: unrecognized arguments: --selftest
[exit=2]
infopack-check: 2
review-gate: 2
official-ref-gate: 2
gcr-gate: 2
node-claim-gate: 1
self-destruct-gate: 2
```

★ **⇒ 结论（精确）**：`sandbox-script.py` **没有 `--selftest` 这个开关**（argparse 判 `unrecognized arguments`）；**同批六件兄弟工具都有**。
⇒ **不是「跑失败了」，是「该开关不存在」。**

### 2.4 ★★ 本件关闭 `§0.3` 的「待核项」

`v6.1:322` 逐字：

> 「★ **待核项**（v5 不替其裁决）：交付说明对 `sandbox-script.py` 同时给出 `--selfcheck` **5/5** 与 `--selftest` **4/4**。经比对 §2 与 §3 上下文，二者**应为不同检查**（`--selfcheck` 属 R006 §5 三步之①，`--selftest` 属自证矩阵），**但 v5 未逐一实跑复核** ⇒ 记为「**未测**」，**不并入任一侧**。」

**复跑**：

```bash
python3 tools/sandbox-script.py --selfcheck 2>&1 | tail -8 ; echo "[exit=${PIPESTATUS[0]}]"
python3 tools/sandbox-script.py --selftest 2>&1 | tail -3 ; echo "[exit=${PIPESTATUS[0]}]"
```

**未编辑原始输出**：

```
★ selfcheck（R006 ②③④）
  ✅ ② TCC：本工具**不写**被检对象
  ✅ ③ 无 CLD 硬编码路径（可移植）
  ✅ ④ 版本单一来源 VERSION
  ✅ ⑤ 有输出（非静默成功）
  ✅ ⑩ A 预检：源码无危险原语（剥离后）
  自查：5/5
[exit=0]
```
```
sandbox-script.py: error: the following arguments are required: script
[exit=2]
```

★★ **⇒ 本件的现测裁定**（★ 只报测到的事实，不替 v5 补推）：
1. `--selfcheck` **存在**，实跑 **5/5**，`exit 0` —— **与交付说明的 5/5 相符**。
2. `--selftest` **在 `sandbox-script.py` 上不存在**（`exit 2`）。
3. ⇒ **交付说明里的「`--selftest` 4/4」无法在 `sandbox-script.py` 上复现**。
   ★ **可能的解释有三种，本件【不择一】**：(a) 该数字来自**别的工具**；(b) 来自**别的调用形态**（如 `bash tools/x.sh --selftest`）；(c) 记录本身有误。
   ★★ **⇒ 按本仓纪律，此项现应记为【口径不符·待归因】，而不是「未测」。** —— **这是一个【可判的负结果】，比「未测」强。**

### 2.5 ★★ 第④步之三：**无参功能跑**（清单里**没有**这一步）

```bash
python3 tools/gcr-gate.py ; echo "[exit=$?]"
```

**未编辑原始输出**（完整，47 行中的判定段）：

```
★ gcr-gate v1.0.0
★ 扫描时点：2026-10-12T20:04:30+0800
★ 条款来源：锚点 §7.9（**实列 17 条**；§10 称「十五条」⇒ 计数不符，已登记）
★ 覆盖：17 条全建档；本工具机械化的 11 条，其余标 N-A 并指向既有工具

❌ G-CR1    插件变更→沙箱挂载+dump-config+真挂载冒烟三态
      plugin-preflight 判红（exit=1 ⇒ 禁止重启）
⚠️ G-CR2    schema/DSL 过官方规则
      须官方规则集；部分由 dump-config 覆盖（见 G-CR1 的 A 检）
✅ G-CR3    命名门 N1–N3 常驻
      目录名=dsh-plugin-central-inbox · name=dsh-plugin-central-inbox · patch id=central-inbox
⚠️ G-CR4    依赖操作后扫遮蔽（含 .bak/.pnpmcopy）
      guard_deps_scan 不可用；静态数得惰性残骸 0 个（不判红）
⚠️ G-CR5    去遮蔽顺序固定（先重指→再移走）
      流程类，无机械判据
✅ G-CR6    dylib/binary 改动后逐个验签
      验签：抽检 1 个 .dylib/.so（共 1 个）全部通过 ｜ entitlement：关键键齐备
✅ G-CR7    重签后 TCC 流程
      TCC 相关键在 4 个 Helper 上齐备：CLD Helper (GPU).app, CLD Helper (Plugin).app, CLD Helper (Renderer).app
❌ G-CR8    装载前事件数门（拒绝而非崩）
      ★ 1 个会话文件 ≥200MB，最大 245.2MB（session-fa1f9150-c949-40）—— **体积是代理指标，非事件数**
✅ G-CR9    compaction 挂载+约束钉住（v2：含 P26 负控）
      6/6 preset 已挂 compaction，且见显式阈值配置（P26 负控的存在性证据）
⚠️ G-CR10   子进程内存监控
      需运行时；heartbeat.json 可作旁证
⚠️ G-CR11   禁用/沙箱验证 31888 reload
      「不用即安全」
✅ G-CR12   不动运行中的 app.asar
      app.asar 0.18MB · mtime=2026-10-08 15:03:06 · bundle验签=通过
⚠️ G-CR13   动态插件只用沙箱原语
      静态扫描可部分覆盖，本轮未做
⚠️ G-CR14   端口固定
      未在配置中显式找到 port（可能由别处指定）
⚠️ G-CR15   重启票流程
      既有 restart-governor.sh + RESTART_GO 标记
✅ G-CR16   请求前 token 预算门（含 completion 预留）
      contextWindow=1048576 · completion 预留=256000 ⇒ 消息可达上限=792576
⚠️ G-CR17   压缩有效性门（降幅 ≤0 ⇒ 告警）
      须读会话 JSONL 的 summar/shadowed 降幅 ⇒ 超出本工具范围；判据与实测见 blackboard:data/registry/dead-session-postmortem-activity 与 c7 系列卡

══ 汇总：PASS 6 · FAIL 2 · N-A 9（共 17）══
   ⇒ ❌ **有 FAIL ⇒ 禁止推进/重启**
```

**退出码**：`1`

★★★ **这是本件最重要的读数。三点**：

1. **它自己就判红了**（`exit=1`）⇒ **该门是「能红」的**（★ 依本仓纪律「一个断言若从未红过，它就不是判据」，**这一条它【现在】满足**，而且满足得很实在）。
2. **`§0.3` 把 S5 记作「✅（各附自证矩阵）· 结构门 6/6」** —— ★ 这两栏我复跑**确实通过**（§2.2）。**但功能跑是 FAIL 2。**
   ⇒ **⇒ 「自证 ✅」+「结构门 ✅」+「功能跑 ❌」三个读数【同时】成立，且【互不矛盾】**。清单只报了前两个。
3. **`G-CR8` 与 `G-CR14` 两条 FAIL/⚠️ 直接命中 WBS 项**：
   - **`G-CR8` 装载前事件数门 ❌** ⇒ 对应 **W0.6**（且工具自己注明「**体积是代理指标，非事件数**」—— ★ 自我标注了口径缺口，**这是好实践**）
   - **`G-CR14` 端口固定 ⚠️「未在配置中显式找到 port」** ⇒ 对应 **W4.1 端口固定**

### 2.6 ★★ 第⑤步：三套口径互相不等

```bash
grep -n "机械化 10" docs/distributed-agent-network-governance-plan-v6.1-20261011.md
python3 tools/gcr-gate.py 2>&1 | sed -n '4p'
python3 tools/gcr-gate.py 2>&1 | grep "汇总"
```

**未编辑原始输出**：

```
1708:  - S1 沙箱模拟框架 ✅ `sandbox-script.py` · ... · S5 **G-CR 校验脚本（实列 17 条**，非「十五条」）✅ `gcr-gate.py` · **覆盖 17 条**（机械化 10 · `N-A` 7）
★ 覆盖：17 条全建档；本工具机械化的 11 条，其余标 N-A 并指向既有工具
══ 汇总：PASS 6 · FAIL 2 · N-A 9（共 17）══
```

**退出码**：`0`

★★ **⇒ 同一个 S5，三处给出【三套不同的口径】**：

| 出处 | 机械化 | N-A | 自洽？ |
|---|---|---|---|
| `v6.1:1708`（§10 表头） | **10** | **7** | 10+7=17 ✓ |
| `gcr-gate.py` 自述（工具内逐字） | **11** | **6** | 11+6=17 ✓ |
| `gcr-gate.py` 实跑汇总 | **8**（PASS 6 + FAIL 2） | **9** | 8+9=17 ✓ |

★ **三者【各自自洽】，但【互不相等】**。
★ **本件不裁决哪一套对**（那需要读 `gate.js` 的逐条分类逻辑，**本件未做**）。
★★ **⇒ 但可判的事实是：`§0.3`/`§10` 的「覆盖 17 条（机械化 10 · N-A 7）」【不可作为现状引用】，因为同一工具在同一时刻给出的是 8/9。**
★★★ **⇒ 这正是篇三所说「同一事实两处写法相反」的量化形态** —— ★ 且它**印证了 `§0.3:315` 自己的限定语**：「**`N-A` 不是通过**」。

---

## §3 结论：`§0.3` 这类「已交付清单」的复核判词

| 栏 | 复核结论 | 依据 |
|---|---|---|
| **实体在否** | ✅ **7/7 在** | §2.1 |
| **字节数** | ✅ **7/7 逐字相符** | §2.1 |
| **sha256** | 🟡 **本件首次落盘基线**（原清单无此栏 ⇒ 原本**无基线可核**） | §2.1 |
| **结构门 6/6** | ✅ **7/7 复跑全绿** | §2.2 |
| **负控曾红（自证）** | ✅ **6/7 有实跑留痕**；**1/7（`sandbox-script.py`）无 `--selftest` 开关** | §2.3 §2.4 |
| **功能跑** | 🔴 **`gcr-gate` = `PASS 6 · FAIL 2 · N-A 9`，`exit=1`，逐字「禁止推进/重启」** | §2.5 |
| **口径一致** | 🔴 **S5 三套口径不等**（10/7 · 11/6 · 8/9） | §2.6 |
| **「已交付」的限定语是否被随引** | 🔴 **`§0.3:315`「`N-A` 不是通过」与 `§10:1708`「✅ 覆盖 17 条」并存** | §1 第⑤步 |

★★ **⇒ 一句话判词**：
> **`§0.3` 是一份【诚实且可复核】的交付清单，它的字节数与结构门两栏【经得起独立复核且现在为真】；
> 但它【不含】功能跑栏与口径一致栏，而这两栏【现在分别为 FAIL 与不等】。
> ⇒ 凡下游引用 `§0.3`，必须【连同 `:315` 的限定语一起引】，否则会把「交付」读成「通过」。**

---

## §4 阴性证据

| 面 | 检索 | 结果 |
|---|---|---|
| `docs/`+`research/` `*.md` | `sha256` 栏在 `§0.3` 是否存在 | **不存在**（`§0.3:306-312` 只有字节数） ⇒ **原清单无内容指纹基线** |
| 同上 | 七件工具的**功能跑**输出留痕 | ★ **本件【未检索】`logs/` 与黑板** ⇒ **不主张「从未跑过」** |
| ★ 阳性对照 | `负控` ⇒ 127 命中（篇三 §6） | ✅ 探针可用 |

★ **未搜到 ≠ 不存在**：本件**未覆盖** `logs/` · 黑板键空间 · `notes/` · KB。★ **「七件工具是否真被业务用过」本件未测、未主张。**

---

## §5 限制

1. ★ **未读 `gcr-gate.py` 源码** ⇒ **不裁决 §2.6 三套口径哪一套对**。
2. ★ **未复跑 `§12` 的 14 个 SLO 指标**（超出本件范围）。
3. ★ **`§0.3` 的「零变更 ✓」栏（`:304-312` 第 5 列）本件【未核】。**
4. ★ **未核 `增①` 的 Lean 文件**（`rules-registry/lean4/node-claim-gate.lean`）**是否真的未编译**（`§0.3:318` 自认「本机无 lean 工具链」）。
5. ★ 本件**只读**；**未修改 `docs/` 下任何文件**（`v6.1` sha256 现测 `bf5a4e6b…` 未变，见篇一 §1.2）。

---

*R-M2 · 篇四 fin · 2026-10-12 · 五步规程已给；功能跑当场判红；三套口径已量化*
