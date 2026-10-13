#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-doc-numbering-check.py — 文档二级编号顺序校验 v1.1.0

★★ 为什么需要它（明鉴建议 · 2026-10-14）：
  灯塔报告曾两次出现编号事故（§12.7 排在 §12.4 前 / §12.9 插到 §1.5 区段）。
  自陈为「加法容易，把已有结构调顺容易忘」。
  ⇒ 明鉴建议：把「编号顺序」也做成可核验的 ——
     **这样它就从「记得排」变成「能查出没排」。**

★★ 口径（v1.0.1 修）：本脚本输出的「一级段」= `^### N.M` 的【首段号去重】，
  与报告头部的「章」（= `^## ` 总数）【不是同一个集合】—— 两者共用过「章」这个标签，已改名。
用法:
    bb-doc-numbering-check.py <file.md>
    exit 0 = 顺序正确 · exit 1 = 存在乱序/不连续
"""
__version__ = "1.0.1"
import re, sys
from collections import defaultdict

def main():
    if len(sys.argv) < 2:
        print("usage: bb-doc-numbering-check.py <file.md>"); return 2
    p = sys.argv[1]
    lines = open(p, encoding='utf-8').read().split('\n')
    nums = []
    for i, l in enumerate(lines, 1):
        m = re.match(r'^#{3,4} (\d+)\.(\d+) ', l)
        if m:
            nums.append((int(m.group(1)), int(m.group(2)), i))
    # ★ v1.1.0 新增：字母后缀检测（如 12.13b）—— 它此前一直被本工具放过
    letter = [(i+1, l.strip()) for i, l in enumerate(lines)
              if re.match(r'^#{3,4} \d+\.\d+[a-z] ', l)]
    if not nums and not letter:
        print("  无二级编号，跳过"); return 0
    bad = 0
    prev = None
    for a, b, ln in nums:
        if prev and (a, b) <= prev:
            print(f"  ✗ 乱序: {a}.{b} (行 {ln}) 在 {prev[0]}.{prev[1]} 之后"); bad += 1
        prev = (a, b)
    ch = defaultdict(list)
    for a, b, ln in nums:
        ch[a].append(b)
    for a in sorted(ch):
        seq = ch[a]
        if seq != list(range(1, len(seq) + 1)):
            print(f"  ✗ 第 {a} 段编号不连续: {seq}"); bad += 1
    for ln, l in letter:
        print(f"  ✗ 行 {ln} 用了字母后缀，与顺序编号约定不符（应改数字）: {l[:48]}"); bad += 1
    if bad:
        print(f"  ✗ {bad} 处问题（{len(nums)} 个编号）"); return 1
    print(f"  ✓ 编号顺序正确 · {len(nums)} 个二级编号 · 覆盖 {len(ch)} 个一级段（注：非报告头部的「章」）"); return 0

if __name__ == "__main__":
    sys.exit(main())
