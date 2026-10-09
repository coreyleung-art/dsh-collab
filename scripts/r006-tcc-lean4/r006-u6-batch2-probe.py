#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-u6-batch2-probe.py v2 — 批次2（⑨ CLI 治理）缺口实测探针（只读）

★ v1 的教训（如实记录）：v1 用 `"--dry-run" in src` 判旗标存在 ⇒ **假阳性** ——
  命中的是【我注入的 canonical 块里的说明字符串】。这正是 R006 §6 坑2「扫描器误伤自己」，
  也正是我自己的块用【AST + 反空洞】防住、而探针没防住的那一类。
v2 修法：**AST 抽旗标字面量**，并**排除 canonical 块所在行区间**。

⑨ 五条子判据：① 未知旗标 ⇒ rc=2 ② 退出码语义 0/1/2 ③ --dry-run ④ 机器可读开关 ⑤ --help 自解释
"""
import ast
import os
import subprocess
import sys

TOOLS = ["gate-canfail.py", "silent-truncation-lint.py", "r006-two-tool-audit.py", "gate-auditor.py",
         "j44-reuse-gate.py", "toolbox-selftest-sweep.py", "selftest-inventory.py",
         "absence-claim-lint.py", "citation-stale-check.py", "verification-level-lint.py"]
D = os.path.expanduser("~/dsh-collab/scripts")
MARK_S = "# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块"
MARK_E = "# ══════════════════════════════ R006 块结束 ══════════════════════════════"


def run(args, to=40):
    try:
        p = subprocess.run([sys.executable] + args, capture_output=True, text=True, timeout=to, cwd=D)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    except Exception as e:
        return "ERR", str(e)


def flags_outside_block(path):
    """返回 (声明旗标集, 是否有 argparse, 是否有 --help/-h 处理)。★ 排除 canonical 块行区间。"""
    lines = open(path, encoding="utf-8").read().splitlines()
    lo, hi = None, None
    for i, l in enumerate(lines, 1):
        if l.startswith(MARK_S):
            lo = i
        if l.startswith(MARK_E):
            hi = i
    t = ast.parse("\n".join(lines))
    fl, has_argparse = set(), False
    for n in ast.walk(t):
        ln = getattr(n, "lineno", 0)
        if lo and hi and lo <= ln <= hi:
            continue
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument":
            has_argparse = True
            if n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                fl.add(n.args[0].value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("--"):
            fl.add(n.value)
    return fl, has_argparse


print("%-30s %-10s %-11s %-11s %-12s %-14s" % ("工具", "①未知旗标", "③--dry-run", "④机器可读", "⑤--help", "②退出码"))
print("-" * 100)
gaps = {}
for t in TOOLS:
    p = os.path.join(D, t)
    fl, has_ap = flags_outside_block(p)
    rc1, _ = run([t, "--r006-definitely-unknown-flag"])
    has_dr = "--dry-run" in fl
    rc_dr, o_dr = run([t, "--dry-run"]) if has_dr else ("n/a", "")
    jsonf = "--json" if "--json" in fl else ("--json-out" if "--json-out" in fl else None)
    has_help = ("--help" in fl) or has_ap
    rc_h, o_h = run([t, "--help"])
    help_ok = (rc_h == 0) and bool(o_h.strip()) and (("usage" in o_h.lower()) or ("用法" in o_h) or ("选项" in o_h) or ("usage" in o_h.lower()))
    g = []
    if rc1 != 2:
        g.append("①未知旗标 rc=%s≠2" % rc1)
    if not has_dr:
        g.append("③无 --dry-run")
    if not jsonf:
        g.append("④无机器可读开关")
    if not help_ok:
        g.append("⑤--help rc=%s 非帮助" % rc_h)
    gaps[t] = g
    print("%-30s %-10s %-11s %-11s %-12s %-14s" % (
        t, "rc=%s" % rc1, ("有 rc=%s" % rc_dr) if has_dr else "★无",
        jsonf or "★无", ("OK rc=%s" % rc_h) if help_ok else ("★rc=%s" % rc_h),
        "✓rc=2" if rc1 == 2 else "★"))
print()
for t, g in gaps.items():
    if g:
        print("  ✗ %-30s %s" % (t, " · ".join(g)))
print("\n⇒ 有缺口工具数 %d / %d" % (sum(1 for g in gaps.values() if g), len(TOOLS)))
