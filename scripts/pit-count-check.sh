#!/bin/bash
# 自包含：核对「头部声明的坑计数」与「实际条数」是否一致
# 设计要点（来自实测教训）：
#   ① 按【行索引】定位两端（## 5 · 已知坑 → ## 6 ·），**不靠字面锚点**（避开「关键词未命中≠不存在」陷阱）
#   ② 同时给出【最大编号】（必要不充分：编号连续时它=条数，若别节编号更大则失效）
#   ③ 打印【过宽计数】并标为陷阱：`^[0-9]+\. \*\*` 会把各节所有编号列表项都算进来 ⇒ 不可与坑条数对账
H="$HOME/dsh-collab/docs/audit-reviewer-handover-v1.md"
R="$HOME/dsh-plugin-pstd/docs/README.md"
python3 - "$H" "$R" <<'PY'
import re,sys
def scoped(p,a,b):
    L=open(p,encoding='utf-8').read().split('\n'); s=e=None
    for i,l in enumerate(L):
        if s is None and l.startswith(a): s=i
        elif s is not None and l.startswith(b): e=i; break
    seg=L[s:e] if s is not None else []
    return len([x for x in seg if re.match(r'^\d+\. \*\*', x)])
def maxno(p):
    ns=[int(m.group(1)) for m in re.finditer(r'^(\d+)\. \*\*', open(p,encoding='utf-8').read(), re.M)]
    return max(ns) if ns else 0
def wide(p):
    return len(re.findall(r'^\d+\. \*\*', open(p,encoding='utf-8').read(), re.M))
H,R=sys.argv[1],sys.argv[2]
pkg,own=scoped(R,'## 坑（都踩过）','## 实测记录'),scoped(H,'## 5 · 已知坑','## 6 ·')
m=re.search(r'包内 `[^`]+` (\d+) 条 / 本处 (\d+) 条', open(H,encoding='utf-8').read())
print("  声明 = %s   实测（作用域内）= (%d, %d)   ⇒ %s"%(m.groups(),pkg,own,
      "✅ 一致" if (int(m.group(1)),int(m.group(2)))==(pkg,own) else "❌ 不一致"))
print("  最大编号：包内 = %d · 本处 = %d   （必要不充分：仅当编号连续且别节编号更小时才等于条数）"%(maxno(R),maxno(H)))
print("  ⚠ 过宽计数（**陷阱，勿用于对账**）：包内 = %d · 本处 = %d —— 它把各节所有编号列表项都算进来（判据清单/复现命令/变更记录等）"%(wide(R),wide(H)))
PY
