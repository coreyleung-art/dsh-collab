#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 闭环率 —— 现测口径（★ 分母为 0 时报「不可判」，不报 0%/OK）"""
import json, os, sys

P = os.path.expanduser("~/dsh-collab/data/registry/continuity-index.json")
d = json.load(open(P, encoding="utf-8"))
items = d.get("items") or []
total = len(items)
if total == 0:
    print("分母 = 0 ⇒ ★ 不可判（不得报 0%/OK）")
    sys.exit(3)

CLOSED = "closed_with_evidence"
closed = [i for i in items if i.get("state") == CLOSED]

# verifier 在位 = 字段非空 **且** 不是一个「待复核」占位串
def verifier_ok(v):
    if not v or not isinstance(v, str):
        return False
    if "待第三方复核" in v or "待复核" in v:
        return False
    if "missing" in v.lower():
        return False
    return True

with_v = [i for i in closed if verifier_ok(i.get("verifier"))]

print("索引:", P)
print("索引 updated_at:", d.get("updated_at"), "· state_version:", d.get("state_version"))
print()
print("分母（items 总数）= %d" % total)
print("分子（state == closed_with_evidence）= %d" % len(closed))
print("闭环率 = %d/%d = %.1f%%   （目标 ≥80%%）" % (len(closed), total, 100.0*len(closed)/total))
print()
print("逐项:")
for i in items:
    v = i.get("verifier")
    tag = "OK" if verifier_ok(v) else ("缺失" if not v else "占位/待复核")
    print("  %-6s %-22s verifier=%s" % (i.get("id"), i.get("state"), tag))
print()
print("★ 真正到位的 verifier（非占位）：%d/%d" % (len(with_v), len(closed)))
if closed and len(with_v) == 0:
    print("★ ⇒ 全部 closed 项的 verifier 均是「待第三方复核」占位 ⇒ 按 §5.1「未证不得记 closed」，")
    print("  这些 closed 在【审查意义上】全部不可判 ⇒ 闭环率的分子在审查口径下 = 不可判。")
print()
print("★ 时刻声明：本读数是上面 updated_at 时刻的索引状态，不是「现在的事实」。")
