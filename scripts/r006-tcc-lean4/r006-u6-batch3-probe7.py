#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-u6-batch3-probe7.py — ⑦ 专项：找出【哪个调用真会写日志】，找不到即是结论

方法：对每器逐个候选 argv 实跑，量日志追加行数；取最大值。
★ 判据来源：R006 §2⑦ 自检原文「跑一次后日志追加行数 > 0」。
★ 诚实边界：若【所有候选】都不追加 ⇒ 该器的 ⑦ 是【死声明】（声明了路径但从不留痕）。
   我不把「找不到写日志的调用」等同于「工具不好」—— 但它是 ⑦ 的客观不达标。
"""
import os
import subprocess
import sys

S = os.path.expanduser("~/dsh-collab/scripts")
LOGS = os.path.expanduser("~/dsh-collab/logs")

CAND = {
    "gate-canfail.py": [[], ["--selftest"], ["--lean4-check"], ["--dry-run", "--selftest"]],
    "silent-truncation-lint.py": [[], ["--selftest"], ["--lean4-check"], ["--dry-run"]],
    "r006-two-tool-audit.py": [[], ["--lean4-check"], ["--tool", "gate-canfail.py"]],
    "gate-auditor.py": [[], ["list-tools"], ["scan-all"], ["--lean4-check"]],
    "j44-reuse-gate.py": [[], ["--selftest"], ["--list"], ["--check", "gate-canfail"]],
    "toolbox-selftest-sweep.py": [[], ["--selftest"], ["--limit", "3"]],
    "selftest-inventory.py": [[], ["--tools", "gate-canfail.py"], ["--lean4-check"]],
    "absence-claim-lint.py": [[], ["--selftest"], ["--lean4-check"], ["--limit", "3"]],
    "citation-stale-check.py": [[], ["--selftest"], ["--lean4-check"]],
    "verification-level-lint.py": [[], ["--limit", "1"], ["--lean4-check"], ["--version"]],
}


def nl(p):
    try:
        with open(p, "rb") as f:
            return f.read().count(b"\n")
    except OSError:
        return None


def run(args, to=90):
    try:
        p = subprocess.run([sys.executable, args[0]] + args[1:], capture_output=True,
                           text=True, timeout=to, cwd=S)
        return p.returncode
    except subprocess.TimeoutExpired:
        return "TO"
    except Exception:
        return "ER"


print("%-30s %-9s %s" % ("工具", "增量", "逐候选（argv → rc/追加行）"))
print("-" * 118)
dead = []
for t, cands in CAND.items():
    lp = os.path.join(LOGS, t[:-3] + ".log")
    base = nl(lp)
    if base is None:
        base = 0
    rows, best = [], 0
    for c in cands:
        b = nl(lp) or 0
        rc = run([t] + c)
        a = nl(lp) or 0
        d = a - b
        best = max(best, d)
        rows.append("%s→rc%s/+%d" % (" ".join(c) or "(无参)", rc, d))
    flag = "★死声明" if best == 0 else ("+%d" % best)
    if best == 0:
        dead.append(t)
    print("%-30s %-9s %s" % (t, flag, " · ".join(rows)[:78]))

print()
print("★ 全候选均不追加日志的器（= ⑦ 死声明）：%d 个" % len(dead))
for d in dead:
    print("   · %s" % d)
