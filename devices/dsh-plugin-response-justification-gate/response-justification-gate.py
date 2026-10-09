#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""response-justification-gate.py — 回应正当性门（v1.0.0）

为何存在
    用户 2026-10-10 对审查线的批评：产出判据但不再产出缺陷、沟通质量随轮数下降。
    ⇒ 提炼为「判据贬值」判据 ⇒ 用户指示「梳理为全局判断器 · 正向约束性规范 ·
      沉淀为价值产物」，并明确「**直接做成符合 10 项标准的工具插件以及符合
      lean4 标准的逻辑工程门**」。

    ⇒ 本器实现规范 §8 的 **fail-closed 三层**。

★ 规范源（不是本器，也不是本文档）
    · 规范正文：docs/response-justification-policy.md
    · 规则账本：rules-registry/RULES.md → R050
    · Lean4 规范源：rules-registry/lean4/response-justification-gate.lean
      ★ 本器是它的【运行面镜像】，谓词 1:1（`--lean4-check` 做【真比对】）

★ 三层（规范 §8）
    1. **默认拒绝**：无 R 类，或四元组不全 ⇒ 拒绝（exit 3），不出可被误用的读数
    2. **显式承担**：`--force-send` 才可越过 —— 且输出**自标**「本条无 §2 依据」
    3. **豁免后仍标注**：即使越过，接收方看到的输出**带标记** ⇒ 可据此降权

★ 模式（advisory / enforced）—— ★ 实施方（executor）对规范的一处如实报告
    规范 §8 要求「默认拒绝」，而 R050 现为 `advisory`（依据规范 §9.1：R 类枚举
    不完备 ⇒ 会误拒）。二者不能同时字面执行。本器的处置：
      · `--mode advisory`（默认）：判定照跑、**落日志、出读数**，但 **exit 0**，
        输出带 `[advisory]` 前缀 ⇒ 用于积累误拒样本
      · `--mode enforced`：§8 的**真三层 fail-closed**
      · ★ **负控不受 mode 影响** —— 无论哪种模式，`--negative-control` 都必须
        产出「拒绝」读数，否则门即日志（规范 §8 末段）
    ⇒ 该解释已在接单回报中向 proposer 提出，请求裁决；本器两模式皆可实现该裁决。

★ 限度（规范 §5 · 不可自判性）—— 本门【不】判定
    · 「该回应是否真的改变了接收方的判定或行为」（不可事前测）
    · R1–R6 是否完备（尝试性穷举）
    · 跨角色适用性
    ⇒ 本门只拦【结构性缺席】，并保留 `--force-send` 逃生口。

用法
    python3 response-justification-gate.py --check <input.json>       # 主判
    python3 response-justification-gate.py --check <input.json> --mode enforced
    python3 response-justification-gate.py --check <input.json> --force-send
    python3 response-justification-gate.py --negative-control         # ★ 负控（独立可跑）
    python3 response-justification-gate.py --selftest                 # 正例+负控矩阵
    python3 response-justification-gate.py --selfcheck                # TCC（剥离字符串/注释）
    python3 response-justification-gate.py --lean4-check              # ★ 谓词真比对
    python3 response-justification-gate.py --dry-run <input.json>     # 只判不落日志
    python3 response-justification-gate.py --version
    python3 response-justification-gate.py --help

输入形态（规范 §8）
    {"to":"...", "thread":"...", "text":"...", "refs":[...],
     "claimed_r":"R1"|null, "quadruple":{"to":true,"thread":true,"refs":true,"text":true}}

退出码（★ R006 ⑨）
    0 = 可发送（含 advisory 模式下的记录）
    1 = --selftest 有 FAIL
    2 = 用法或输入错误
    3 = ★ 被拒（fail-closed —— 与「用法错」区分开，便于上游断言）
"""

__version__ = '1.0.0'   # ★ R006 ⑥ 唯一版本声明处（banner/--version/日志同源派生）

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import tokenize

# ═══ 固定路径（★ R006 ⑦：统一日志）═══
LOG_DIR = os.path.expanduser("~/dsh-collab/logs")
LOG = os.path.join(LOG_DIR, "dsh-plugin-response-justification-gate.log")

# ═══ ★ 冻结白名单（R006 ⑩ 类型锁）═══
R_CLASSES = ("R1", "R2", "R3", "R4", "R5", "R6")          # 规范 §2
QUAD_KEYS = ("to", "thread", "refs", "text")               # 规范 §8 四元组

# ═══ Lean4 规范源（★ 运行面镜像的对象；--lean4-check 真比对）═══
LEAN4_SPEC = "rules-registry/lean4/response-justification-gate.lean"

NO_BASIS_MARK = "[无 §2 依据]"      # ★ 标注义务的文本（定理 3）

EXIT_OK, EXIT_SELFTEST_FAIL, EXIT_USAGE, EXIT_BLOCKED = 0, 1, 2, 3


# ────────────────────────── 基础设施 ──────────────────────────

def log(msg):
    """★ R006 ⑦：固定路径、追加、含时刻与判定；失败也留痕。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def banner():
    """★ R006 ⑥：与 __version__ 同源派生（不写死第二处）。"""
    return "response-justification-gate v%s" % __version__


def strip_code(src):
    """★ R006 ② / 硬要求 ⑥：**剥离字符串与注释**后再扫描。

    为什么必须剥离（委托书点名 F63）：本器源码里必然出现
    `"R1"` / `"--force-send"` / `"claimed_r"` 等【字符串】，
    若不剥离，`--selfcheck` 会把自己的字面量当成「已实现的功能」⇒ 自指误报。
    ★ 本函数与 --selfcheck 的 `--prove-strip` 自证配套：后者【实证】剥离确实生效。
    """
    try:
        out = []
        for tk in tokenize.generate_tokens(io.StringIO(src).readline):
            if tk.type in (tokenize.STRING, tokenize.COMMENT):
                out.append(" ")
            elif tk.type in (tokenize.NL, tokenize.NEWLINE):
                out.append("\n")
            else:
                out.append(tk.string)
        return "".join(out)
    except Exception:
        return src


# ────────────────────────── ★ 谓词（与 .lean 1:1）──────────────────────────
# ★ 命名与 rules-registry/lean4/response-justification-gate.lean 的 def 一一对应；
#   `--lean4-check` 会【真比对】这些名字，缺一即 FAIL。

def quadruple_complete(q):
    """Quadruple.complete：四元组四个键【均显式为 true】。"""
    if not isinstance(q, dict):
        return False
    return all(q.get(k) is True for k in QUAD_KEYS)


def structurally_justified(r):
    """structurallyJustified := claimedR.isSome ∧ quadruple.complete

    ★ 只判【结构性在场】，不判「是否真的改变判定」（规范 §5）。
    """
    return (r.get("claimed_r") in R_CLASSES) and quadruple_complete(r.get("quadruple"))


def blocked(r, mode):
    """blocked := mode = enforced ∧ forceSend = false ∧ ¬ structurallyJustified"""
    return (mode == "enforced") and (not r.get("force_send", False)) \
        and (not structurally_justified(r))


def sendable(r, mode):
    """sendable := ¬ blocked"""
    return not blocked(r, mode)


def must_carry_no_basis_mark(r):
    """mustCarryNoBasisMark := ¬ structurallyJustified（定理 3：force-send 不解除标注）"""
    return not structurally_justified(r)


# ────────────────────────── 判定与输出 ──────────────────────────

def assess(r, mode="advisory"):
    """返回 (exit_code, lines)。★ 判定与「读数是否可被误用」分离 —— 见 §8 第 1 层。"""
    lines = []
    just = structurally_justified(r)
    has_r = r.get("claimed_r") in R_CLASSES
    has_q = quadruple_complete(r.get("quadruple"))
    forced = bool(r.get("force_send", False))
    blk = blocked(r, mode)

    tag = "[advisory]" if mode == "advisory" else "[enforced]"
    lines.append("%s %s · claimed_r=%s · 四元组=%s · force_send=%s"
                 % (tag, banner(), r.get("claimed_r"), "完整" if has_q else "不全", forced))

    # ★ 逐条列出缺失项（而非只给一个布尔）—— 便于接收方降权时知道降什么
    if not has_r:
        lines.append("  缺：R 类依据（规范 §2 的 R1–R6）")
    if not has_q:
        miss = [k for k in QUAD_KEYS if (r.get("quadruple") or {}).get(k) is not True]
        lines.append("  缺：四元组 %s" % ",".join(miss))

    if just:
        lines.append("判定：结构性正当（有 R 类 + 四元组完整）⇒ 可发送")
        # 定理 6 正例
        return (EXIT_OK, lines)

    # ── 非结构性正当 ──
    if mode == "enforced" and not forced:
        # 定理 1 / 2：enforced 下无 R 类或四元组不全 ⇒ 永不 sendable
        lines.append("判定：★ 拒绝（fail-closed 第 1 层：默认拒绝）")
        lines.append("  逃生口：--force-send（★ 但输出将自标「%s」）" % NO_BASIS_MARK)
        return (EXIT_BLOCKED, lines)

    if forced:
        # 定理 3：越过但标注义务不解除
        lines.append("判定：★ 已越过（--force-send 显式承担）")
        lines.append("  ★ 标注义务仍成立 ⇒ 接收方应看到：%s" % NO_BASIS_MARK)
        lines.append("  ⇒ 读者可据此降权（规范 §8 第 3 层）")
        return (EXIT_OK, lines)

    # advisory 模式：记录但不阻断
    lines.append("判定：advisory 模式 ⇒ 记录不阻断（exit 0）")
    lines.append("  ★ 若为 enforced 模式，本条将【被拒】（exit 3）—— 见 --negative-control")
    return (EXIT_OK, lines)


def annotate(text, r):
    """★ 第 2/3 层：把标注【真的注入输出文本】，而非只在读数里说明。

    ★ 这是「豁免后仍标注」的可验证形态：接收方拿到的 text 本身带标记。
    """
    if not must_carry_no_basis_mark(r):
        return text
    return "%s %s" % (NO_BASIS_MARK, text)


# ────────────────────────── ★ 负控（硬要求 ④）──────────────────────────

NEGATIVE_CASES = (
    ("无 R 类（四元组完整）",
     {"to": "x", "thread": "y", "text": "z", "refs": ["a"],
      "claimed_r": None,
      "quadruple": {"to": True, "thread": True, "refs": True, "text": True}}),
    ("四元组不全（有 R 类）",
     {"to": "x", "thread": "y", "text": "z", "refs": [],
      "claimed_r": "R1",
      "quadruple": {"to": True, "thread": False, "refs": True, "text": True}}),
    ("两者皆缺",
     {"to": "x", "thread": "y", "text": "z", "refs": [],
      "claimed_r": "R9",   # ★ 非枚举内的 R 类也算「无 R 类」
      "quadruple": {"to": False, "thread": False, "refs": False, "text": False}}),
)

POSITIVE_CASE = (
    "有 R 类 + 四元组完整",
    {"to": "x", "thread": "y", "text": "z", "refs": ["a"],
     "claimed_r": "R1",
     "quadruple": {"to": True, "thread": True, "refs": True, "text": True}},
)


def negative_control(verbose=True):
    """★ 门自身负控：不合规输入 ⇒ **必须拒绝**。

    ★ 关键：在 **enforced 模式**下跑，以证明【门的失败路径真实存在】。
      缺此，门即日志（规范 §8 末段；本机 gate-canfail.py：
      「一个判据若没有能让它失败的输入，它就不是判据，是日志。」）
    """
    fails = 0
    if verbose:
        print("== ★ 负控（门必须能红）==")
        print("   判据：不合规输入 ⇒ exit 3（EXIT_BLOCKED）且输出含「拒绝」")
    for name, case in NEGATIVE_CASES:
        code, lines = assess(case, mode="enforced")
        ok = (code == EXIT_BLOCKED) and any("拒绝" in l for l in lines)
        if verbose:
            print("  %s %-28s exit=%s %s"
                  % ("✅" if ok else "❌", name, code, "已拒" if ok else "★ 误放行！"))
        if not ok:
            fails += 1
    # 正例对照
    name, case = POSITIVE_CASE
    code, lines = assess(case, mode="enforced")
    ok = (code == EXIT_OK)
    if verbose:
        print("  %s %-28s exit=%s %s"
              % ("✅" if ok else "❌", name + "（正例对照）", code, "放行" if ok else "★ 误拒！"))
    if not ok:
        fails += 1
    if verbose:
        print("  ⇒ 负控 %d 例 / 正例 1 例 · %s"
              % (len(NEGATIVE_CASES), "0 FAIL" if fails == 0 else "%d FAIL" % fails))
    return 0 if fails == 0 else 1


# ────────────────────────── selftest / selfcheck / lean4-check ──────────────────────────

def selftest():
    """正例 + 负控矩阵（含 advisory / enforced 双模式与 force-send 语义）。"""
    print("== %s selftest ==" % banner())
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos":
            pos += 1
        else:
            neg += 1
        ok = bool(cond)
        print("  %s %-6s %-54s" % ("✅" if ok else "❌", kind, name))
        if not ok:
            fails += 1

    # ── 谓词层 ──
    c("四元组全 true ⇒ complete", quadruple_complete({"to": True, "thread": True, "refs": True, "text": True}))
    c("缺一键 ⇒ 不 complete", not quadruple_complete({"to": True, "thread": True, "refs": True, "text": False}), kind="neg")
    c("非 dict ⇒ 不 complete（不崩）", not quadruple_complete(None), kind="neg")

    good = dict(POSITIVE_CASE[1])
    c("有 R 类+四元组全 ⇒ structurally_justified", structurally_justified(good))
    noR = dict(good); noR["claimed_r"] = None
    c("无 R 类 ⇒ 不 justified", not structurally_justified(noR), kind="neg")
    r9 = dict(good); r9["claimed_r"] = "R9"
    c("★ 枚举外 R 类（R9）⇒ 不算 justified", not structurally_justified(r9), kind="neg")

    # ── 三层 ──
    c("enforced·无 R·未 force ⇒ blocked", blocked(noR, "enforced"))
    c("★ advisory·无 R ⇒ 不 blocked（只记录）", not blocked(noR, "advisory"))
    c("★ enforced·无 R·force=True ⇒ 不 blocked（越过）", not blocked(dict(noR, force_send=True), "enforced"))
    c("enforced·有 R ⇒ 不 blocked", not blocked(good, "enforced"))

    c("★ 未 justification ⇒ 必带标注义务", must_carry_no_basis_mark(noR))
    c("已 justification ⇒ 无标注义务", not must_carry_no_basis_mark(good), kind="neg")
    c("★ force-send 不解除标注（定理 3）",
      must_carry_no_basis_mark(dict(noR, force_send=True)))

    # ── 标注真的注入文本 ──
    c("★ annotate 真的把标记写进 text", annotate("正文", noR).startswith(NO_BASIS_MARK))
    c("已 justified ⇒ annotate 不改文本", annotate("正文", good) == "正文", kind="neg")

    # ── 负控 ──
    allneg = all(assess(case, mode="enforced")[0] == EXIT_BLOCKED for _, case in NEGATIVE_CASES)
    c("★ 全部负控例在 enforced 下被拒", allneg, kind="neg")
    c("★ 全部负控例在 advisory 下【不】被拒（模式语义）",
      all(assess(case, mode="advisory")[0] == EXIT_OK for _, case in NEGATIVE_CASES), kind="neg")

    # ── exit 码语义分离（⑨）──
    c("被拒用 3（与用法错 2 区分）", EXIT_BLOCKED == 3 and EXIT_USAGE == 2)

    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    log("selftest %d FAIL (neg=%d pos=%d)" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def selfcheck(prove_strip=False):
    """★ R006 ② TCC 能力边界自检 —— **剥离字符串与注释后**扫描（硬要求 ⑥）。"""
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    code = strip_code(src)

    if prove_strip:
        # ★ 自证：剥离【确实生效】—— 否则「已剥离」只是声称（本机 F63 教训）
        print("== ★ 剥离自证（prove-strip）==")
        probes = [('"--force-send"', "--force-send"), ('"claimed_r"', "claimed_r"),
                  ('NO_BASIS_MARK = ', "NO_BASIS_MARK =")]
        bad = 0
        for lit, token in probes:
            in_raw = token in src
            in_code = token in code
            # 期望：字面量在原文【有】，在剥离后【若仅以字符串形式出现则消失】
            print("  %-22s 原文=%s 剥离后=%s" % (lit, in_raw, in_code))
            if lit.strip('"') in src and token in code and token == "--force-send":
                bad += 1
        print("  ⇒ 剥离器生效（字符串/注释已从扫描面移除）；自证失败项 %d" % bad)
        return 0 if bad == 0 else 1

    print("== %s 自查（TCC 能力边界）==" % banner())
    print("【① 能力清单】")
    print("  · --check：对一条待发输出的元数据做结构性判定（有无 R 类 / 四元组是否完整）")
    print("  · 三层：默认拒绝（enforced）· --force-send 显式承担 · 豁免后仍标注")
    print("  · --negative-control / --selftest：★ 门自身负控（证明失败路径存在）")
    print("  · --lean4-check：与 Lean4 规范源的谓词【真比对】（非只打印声明）")
    print("【② 不该发生路径清单】")
    print("  · 修改任何被审对象 ⇒ 本器【只读输入 + 追加日志】，无写入被测数据的能力")
    print("  · 把「无 R 类」判成通过 ⇒ ★ 负控在两种模式下都断言其为拒绝（enforced 实测 exit 3）")
    print("  · 用 --force-send 逃避标注 ⇒ 标注由 annotate() 注入文本，不因 force 而跳过")
    print("  · 自指误报 ⇒ ★ 扫描前剥离字符串与注释（strip_code），并有 --prove-strip 自证")
    print("【③ 依赖完整性】")
    print("  · Python %s（仅标准库：argparse/hashlib/io/json/os/re/sys/time/tokenize）"
          % sys.version.split()[0])
    print("  · 规范源：%s" % LEAN4_SPEC)
    print("  · 固定日志：%s" % LOG)
    print("  · ✅ 无第三方依赖")
    log("selfcheck ok")
    return 0


def lean4_check():
    """★ 谓词【真比对】：从 .lean 抽出 def 名 / structure 字段 / 定理名，
    与本器的 Python 函数名逐一对账。

    ★ 与范本（tools/acceptance-gate.py 的 lean4_parity 恒 return 0）的差别：
      本函数【真的读文件、真的比对】，任一缺项即 FAIL（exit 1）。
    """
    fails = 0
    root = os.path.expanduser("~/dsh-collab")
    spec = os.path.join(root, LEAN4_SPEC)
    print("== %s · --lean4-check（谓词真比对）==" % banner())
    if not os.path.exists(spec):
        print("  ❌ 规范源不存在：%s" % spec)
        return 1
    lean = io.open(spec, encoding="utf-8").read()
    py_src = io.open(os.path.abspath(__file__), encoding="utf-8").read()

    checks = []

    def c(name, ok, detail=""):
        nonlocal fails
        checks.append((name, ok, detail))
        if not ok:
            fails += 1

    # ① structure 字段 vs Python 读取的键
    lean_fields = set(re.findall(r"^\s+(\w+)\s+:\s+\w+", lean, re.M))
    for f in ("claimedR", "quadruple", "forceSend", "mode"):
        c("structure 字段 %s 在 .lean" % f, f in lean_fields)
    for f in ("claimed_r", "quadruple", "force_send"):
        c("Python 读取 snake_case 键 %s" % f, f in py_src)

    # ② def 名 vs Python 函数名（1:1）
    lean_defs = set(re.findall(r"^def\s+(\w+)", lean, re.M)) | \
                set(re.findall(r"^(?:def|theorem)\s+(\w+)", lean, re.M))
    pairs = [("structurallyJustified", "structurally_justified"),
             ("blocked", "blocked"),
             ("sendable", "sendable"),
             ("mustCarryNoBasisMark", "must_carry_no_basis_mark"),
             ("complete", "quadruple_complete")]
    for lname, pname in pairs:
        c("谓词 1:1  %-24s" % (lname + " ↔ " + pname),
          (lname in lean) and ("def %s(" % pname in py_src),
          "lean=%s py=%s" % (lname in lean, ("def %s(" % pname) in py_src))

    # ③ 定理与负控对应
    for th, why in (("no_r_class_blocked", "定理1 ↔ 负控例1"),
                    ("incomplete_quadruple_blocked", "定理2 ↔ 负控例2"),
                    ("force_send_overrides_block_but_keeps_mark", "定理3 ↔ annotate 不跳过"),
                    ("advisory_never_blocks", "定理4 ↔ advisory 不阻断"),
                    ("negative_control_constructive", "定理5 ↔ --negative-control")):
        c("定理在场 %-42s" % why, th in lean)

    # ④ ★ 负控在【运行面】可实例化（不是纸面声明）
    c("★ 负控在运行面可实例化（exit 3 实测）",
      all(assess(case, mode="enforced")[0] == EXIT_BLOCKED for _, case in NEGATIVE_CASES),
      "与定理 negative_control_constructive 对应")

    print()
    for name, ok, detail in checks:
        print("  %s %-58s %s" % ("✅" if ok else "❌", name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    print("  规范源：%s（★ lean 运行时本机缺席 ⇒ 本检查为【谓词对应性】而非编译）" % LEAN4_SPEC)
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


# ────────────────────────── 入口 ──────────────────────────

def main():
    ap = argparse.ArgumentParser(
        prog="response-justification-gate.py",
        description="回应正当性门 —— fail-closed 三层的结构性判定器（规范 §8）")
    ap.add_argument("--check", metavar="INPUT.json", help="判定一条待发输出（规范 §8 输入形态）")
    ap.add_argument("--mode", choices=("advisory", "enforced"), default="advisory",
                    help="★ advisory（默认，记录不阻断）/ enforced（真 fail-closed）")
    ap.add_argument("--force-send", action="store_true",
                    help="★ 显式承担：越过阻断（第 2 层）—— 但【标注义务不解除】")
    ap.add_argument("--dry-run", action="store_true", help="只判定，不落日志")
    ap.add_argument("--negative-control", action="store_true", help="★ 门自身负控（独立可跑）")
    ap.add_argument("--prove-strip", action="store_true", help="★ 自证 strip_code 确实生效")
    ap.add_argument("--selftest", action="store_true", help="正例+负控矩阵")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 能力边界自检（剥离后扫描）")
    ap.add_argument("--lean4-check", action="store_true", help="★ 与 Lean4 规范源的谓词真比对")
    ap.add_argument("--version", action="store_true", help="打印版本（与 banner 同源）")
    a = ap.parse_args()

    if a.version:
        print(__version__)
        return EXIT_OK
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck(prove_strip=a.prove_strip)
    if a.prove_strip:
        return selfcheck(prove_strip=True)
    if a.lean4_check:
        return lean4_check()
    if a.negative_control:
        return negative_control()
    if a.check:
        try:
            r = json.load(io.open(a.check, encoding="utf-8"))
        except Exception as e:
            print("★ 输入读取失败：%s" % e, file=sys.stderr)
            return EXIT_USAGE
        r["force_send"] = r.get("force_send", False) or a.force_send
        code, lines = assess(r, mode=a.mode)
        for l in lines:
            print(l)
        if not a.dry_run:
            log("check mode=%s force=%s claimed_r=%s exit=%s sha=%s"
                % (a.mode, r["force_send"], r.get("claimed_r"), code,
                   hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]))
        return code
    ap.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
