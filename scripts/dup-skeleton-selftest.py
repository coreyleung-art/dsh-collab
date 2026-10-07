#!/usr/bin/env python3
"""dup-skeleton.py 的正控 + 负控。

由来（HR 2026-09-14）：候选型工具也须有正控。
  我此前立的那一层是「结构判据 ⇒ 工具可给判决；语义判据 ⇒ 工具只能给候选」。
  HR 补的是这一层的另一半：候选型工具若没有正控，则「它从不给候选」与
  「它正确地没给候选」不可分 —— 两者外观相同。

两级控制的含义（判决型与候选型通用）：
  正控 = 给一个【应当被报出】的样本 ⇒ 排除「从不报」
  负控 = 给一个【不应当被报出】的样本 ⇒ 排除「全报」
  缺正控 ⇒ 无法区分「没发现问题」与「检查没工作」
  缺负控 ⇒ 无法区分「严格」与「乱报」

用法：python3 dup-skeleton-selftest.py
退出码 0 = 正负控均通过
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import os, subprocess, sys, tempfile

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dup-skeleton.py")

SAMPLE = '''def alpha(x):
    total = 0
    for i in range(x):
        total = total + i
    return total

def beta(y):
    acc = 0
    for j in range(y):
        acc = acc + j
    return acc

def gamma(s):
    return s.upper()

def delta(n):
    if n > 0:
        return "pos"
    return "neg"
'''


def run(path):
    r = subprocess.run([sys.executable, TOOL, path], capture_output=True, text=True)
    return r.stdout + r.stderr


def main():
    d = tempfile.mkdtemp(prefix="dupskel-")
    p = os.path.join(d, "sample.py")
    open(p, "w").write(SAMPLE)
    out = run(p)
    print("样本：alpha/beta 同一算法（只换变量名）· gamma/delta 算法不同\n")
    pos = ("alpha" in out and "beta" in out)
    neg = not ("gamma" in out or "delta" in out)
    print(f"  正控（alpha/beta 应被报出）: {'✅ 通过' if pos else '★ 失败 —— 已知重复没被报出'}")
    print(f"  负控（gamma/delta 不应被报出）: {'✅ 通过' if neg else '★ 失败 —— 被误报'}")
    print()
    if pos and neg:
        print("总判定: ✅ 正负控均通过 —— 该工具既能报出已知重复，也不会乱报")
        return 0
    print("总判定: ★ 未通过 —— 本工具的输出不可用于判读")
    return 1


if __name__ == "__main__":
    sys.exit(main())
