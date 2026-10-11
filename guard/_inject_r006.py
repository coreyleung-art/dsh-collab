#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_inject_r006.py — 把 R006 §5 两步（--selfcheck / --lean4-check）注入指定工具。

★ 为何用独立脚本而非 heredoc 内联：今晚 heredoc 内的复杂引号已连续致 SyntaxError 三次
  （lint 三引号 · 落卡未转义双引号 · `\\'\\'\\'` 转义）
  ⇒ **纪律：含复杂引号/正则的代码一律写成文件**。

用法：python3 guard/_inject_r006.py <目标工具.py> <代码块.py> [--version-bump]
"""
import os
import re
import sys


def inject(target, block_path, bump=False):
    tgt = os.path.expanduser(target)
    blk = os.path.expanduser(block_path)
    s = open(tgt, encoding="utf-8").read()
    block = open(blk, encoding="utf-8").read()

    # 幂等：已注入则跳过
    if "--selfcheck" in s and "def selfcheck(" in s:
        print("  ⏭ 已注入过，跳过：%s" % os.path.basename(tgt))
        return 0

    # ① 在 def main(): 之前插入函数块
    m = re.search(r"^def main\(\)", s, re.M)
    if not m:
        print("  ✗ 未找到 def main()：%s" % tgt)
        return 1
    s = s[:m.start()] + block + "\n\n" + s[m.start():]

    # ② argparse 加两个开关（挂在最后一个 add_argument 之后）
    m2 = list(re.finditer(r"^(\s*)ap\.add_argument\([^\n]*\)\n", s, re.M))
    if not m2:
        print("  ✗ 未找到 ap.add_argument")
        return 1
    last = m2[-1]
    ind = last.group(1)
    add = (ind + 'ap.add_argument("--selfcheck", action="store_true", help="R006 ②③④ 能力边界")\n'
           + ind + 'ap.add_argument("--lean4-check", action="store_true", help="R006 ⑩ 六项 A–F")\n')
    s = s[:last.end()] + add + s[last.end():]

    # ③ main 里加分支（在第一个 sys.exit(...) 之前）
    m3 = re.search(r"^(\s*)if a\.\w+:\n\s*sys\.exit\(", s, re.M)
    if not m3:
        print("  ✗ 未找到 main 的分支锚点（首个 arg 分支）")
        return 1
    ind2 = m3.group(1)
    branch = (ind2 + "if a.selfcheck:\n" + ind2 + "    sys.exit(selfcheck())\n"
              + ind2 + "if a.lean4_check:\n" + ind2 + "    sys.exit(lean4_check())\n")
    s = s[:m3.start()] + branch + s[m3.start():]

    open(tgt, "w", encoding="utf-8").write(s)
    print("  ✓ 已注入：%s" % os.path.basename(tgt))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(inject(sys.argv[1], sys.argv[2], "--version-bump" in sys.argv))
