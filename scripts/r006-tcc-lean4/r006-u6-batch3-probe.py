#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-u6-batch3-probe.py — 批次3（⑥版本单一来源 / ⑦统一日志 / ⑤文档化）缺口实测探针（只读）

★ 方法学（两次教训的沉淀）：
  · 旗标/常量一律用 **AST** 取，不用 `"xxx" in src`（会命中 canonical 块里的说明字符串）
  · 一律**排除 canonical 块行区间**
  · ⑦ 用【规格 §2⑦ 自检原文】判据：**跑一次后日志追加行数 > 0** —— 而不是查「路径声明是否存在」

⑥ 判据（规格 §2⑥）：版本号只有一个声明处；`--version` 机器可读地取自该来源
⑦ 判据（规格 §2⑦）：日志路径固定；跑一次后追加行数 > 0；失败也留痕
⑤ 判据（规格 §2⑤）：docs/ 下有可独立复现的文档
"""
import ast
import os
import subprocess
import sys

SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
DOCS = os.path.expanduser("~/dsh-collab/docs")
MARK_S = "# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块"
MARK_E = "# ══════════════════════════════ R006 块结束 ══════════════════════════════"

# ⑦ 的候选 argv（best-of-candidates）：★ 单候选会误判 —— 有的器只在特定调用上写日志
WORK = {
    "gate-canfail.py": [[], ["--selftest"], ["--lean4-check"]],
    "silent-truncation-lint.py": [[], ["--selftest"], ["--lean4-check"], ["--dry-run"]],
    "r006-two-tool-audit.py": [[], ["--lean4-check"], ["--tool", "gate-canfail.py"]],
    "gate-auditor.py": [[], ["list-tools"], ["scan-all"], ["--lean4-check"]],
    "j44-reuse-gate.py": [[], ["--selftest"], ["--list"]],
    "toolbox-selftest-sweep.py": [[], ["--selftest"], ["--limit", "3"]],
    "selftest-inventory.py": [[], ["--tools", "gate-canfail.py"], ["--lean4-check"]],
    "absence-claim-lint.py": [[], ["--selftest"], ["--lean4-check"]],
    "citation-stale-check.py": [[], ["--selftest"], ["--lean4-check"]],
    "verification-level-lint.py": [[], ["--limit", "1"], ["--lean4-check"], ["--version"]],
}


def block_range(lines):
    lo = hi = None
    for i, l in enumerate(lines, 1):
        if l.startswith(MARK_S):
            lo = i
        if l.startswith(MARK_E):
            hi = i
    return lo, hi


def scan(path):
    src = open(path, encoding="utf-8").read()
    lines = src.splitlines()
    lo, hi = block_range(lines)
    t = ast.parse(src)
    ver_names, log_assign = [], []
    for n in t.body:                                  # ★ 只看模块级
        ln = getattr(n, "lineno", 0)
        if lo and hi and lo <= ln <= hi:
            continue
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name):
                    if tg.id in ("VERSION", "__version__"):
                        val = None
                        if isinstance(n.value, ast.Constant):
                            val = n.value.value
                        ver_names.append((tg.id, ln, val))
                    if tg.id in ("LOG", "LOG_FILE", "LOG_PATH"):
                        log_assign.append((tg.id, ln))
    return ver_names, log_assign, src, lines, (lo, hi)


def run(args, to=60):
    try:
        p = subprocess.run([sys.executable] + args, capture_output=True, text=True, timeout=to, cwd=SCRIPTS)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    except Exception as e:
        return "ERR", str(e)


def lines_of(p):
    try:
        with open(p, "rb") as f:
            return f.read().count(b"\n")
    except OSError:
        return None


TOOLS = list(WORK)
print("%-30s %-22s %-12s %-30s %-8s" % ("工具", "⑥版本声明处", "--version 自洽", "⑦日志(路径→追加行)", "⑤文档"))
print("-" * 116)
gaps = {}
for t in TOOLS:
    p = os.path.join(SCRIPTS, t)
    ver, lg, src, lines, blk = scan(p)

    # ⑥ 单一来源
    vdesc = " · ".join("%s L%d=%r" % (n, l, v) for n, l, v in ver) or "★无声明"
    uniq = sorted({v for _, _, v in ver if v is not None})
    v_ok = (len(ver) == 1) and len(uniq) == 1

    # ⑥' --version 输出是否含本地值
    rc_v, out_v = run([t, "--version"])
    self_consistent = bool(uniq) and (str(uniq[0]) in out_v)
    if not uniq:
        self_consistent = False
    if rc_v != 0:
        self_consistent = "rc=%s" % rc_v

    # ⑦ 实跑后日志追加行数 —— ★ best-of-candidates（单候选会误判）
    logpath = os.path.expanduser("~/dsh-collab/logs/%s.log" % t[:-3])
    best, where = 0, ""
    for c in WORK[t]:
        b0 = lines_of(logpath) or 0
        run([t] + c)
        a0 = lines_of(logpath) or 0
        if a0 - b0 > best:
            best, where = a0 - b0, (" ".join(c) or "(无参)")
    if best == 0 and lines_of(logpath) is None:
        ldesc = "★ 文件不存在"
        l_ok = False
    else:
        ldesc = "+%d 行 @ %s" % (best, where or "★全候选皆 0")
        l_ok = best > 0

    # ⑤ 文档
    stem = t[:-3]
    hit = [f for f in os.listdir(DOCS) if f.endswith(".md") and stem in f]
    d_ok = bool(hit)

    g = []
    if not v_ok:
        g.append("⑥ %d 处声明" % len(ver))
    if self_consistent is not True:
        g.append("⑥ --version 不自洽(%s)" % self_consistent)
    if not l_ok:
        g.append("⑦ 追加 0 行 / 文件不存在")
    if not d_ok:
        g.append("⑤ 无文档")
    gaps[t] = g
    print("%-30s %-22s %-12s %-30s %-8s" % (
        t, vdesc[:22], str(self_consistent), ldesc[:30], (hit[0][:22] if hit else "★无")))
print()
for t, g in gaps.items():
    if g:
        print("  ✗ %-30s %s" % (t, " · ".join(g)))
print("\n⇒ 有缺口工具 %d / %d" % (sum(1 for g in gaps.values() if g), len(TOOLS)))
