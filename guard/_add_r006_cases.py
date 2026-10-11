#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_add_r006_cases.py — 为 Wave S 工具注入**真实**的 `_r006_cases()`（替换占位实现）。

★ 为何需要（我方自陈的欠账，登记于 `data/registry/r006-step5-backfill-complete`）：
  通用块 `guard/_r006_block_generic.py` 的 B/C 两项**缺省用占位**（只比 bool("") 之类）
  ⇒ 那**只验证了「布尔运算」，没有验证「本门判据能红」** ——
  而 R006 B/C 的本意是「**用本工具真实的越界输入**证明判据会红 / 合法输入能过」。

★ 注入原则：
  · **不许改判据本身**，只加一个 `_r006_cases()` 覆盖函数；
  · 合成输入**取自该门自己的真实语义**（用它自己的 `check()`/`run_once()` 跑）；
  · **必须有负例（应红）与正例（应过）**，且**正例不能是「随便什么都能过」**。

★ 写法纪律（今晚 heredoc 引号致 SyntaxError 六次的产物）：
  所有含引号的代码用 `chr()` 拼接或写在三引号外，**本文件自身不含字面三引号**。

用法：python3 guard/_add_r006_cases.py <工具.py> <cases_py文件>
"""
import os
import re
import sys


def inject(target, cases_file):
    tgt = os.path.expanduser(target)
    s = open(tgt, encoding="utf-8").read()
    cases = open(os.path.expanduser(cases_file), encoding="utf-8").read()

    if "_r006_cases" in s and "def _r006_cases():" in s and "return None" not in s.split("def _r006_cases():")[1][:400]:
        print("  %-24s 已有真实实现，跳过" % os.path.basename(tgt))
        return 0

    # 替换占位实现（形如 def _r006_cases(): ... return None）
    m = re.search(r"def _r006_cases\(\):(?:.|\n)*?(?=\n\ndef |\n\n# )", s)
    if not m:
        print("  %-24s 未找到 _r006_cases 占位" % os.path.basename(tgt))
        return 1
    s = s[:m.start()] + cases.rstrip() + "\n\n" + s[m.end():]
    open(tgt, "w", encoding="utf-8").write(s)
    print("  %-24s ✓ 已注入真实 _r006_cases()" % os.path.basename(tgt))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(inject(sys.argv[1], sys.argv[2]))
