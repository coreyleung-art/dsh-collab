#!/usr/bin/env python3
"""索引卡 v4 核验（判据与被断言对象对齐版）
旧条目判据 = 「逐字仍在」且「相对顺序保持」；不用前缀位置，不用数量。
"""
import json, urllib.request, sys

old = json.load(open("/tmp/idx_dump.txt"))
d = json.load(urllib.request.urlopen(
    "http://127.0.0.1:8792/notes/mac-mini/audit-verdict-index-20261008", timeout=25))
new = {k: v for k, v in d["value"].items() if k not in ("from", "from_label", "to")}
print("readback version =", d.get("version"), "ts =", d.get("ts"))

fails = []

# A) inventory：旧 17 条逐条 deep-equal（内容+顺序）
oi = old["all_verdicts_inventory"]; ni = new.get("all_verdicts_inventory", [])
print(f"inventory  old={len(oi)} new={len(ni)}")
for i, it in enumerate(oi):
    if i >= len(ni) or ni[i] != it:
        fails.append(f"inventory[{i}] 内容/顺序不符: {it.get('item')}")

# B) r048 三段逐字一致
for k, v in old["r048_three_items_status"].items():
    if new.get("r048_three_items_status", {}).get(k) != v:
        fails.append(f"r048[{k}] 内容不符")

# C) still_open：旧 5 条必须「逐字仍在」且保持相对顺序（有序子序列）
os_ = old["still_open_awaiting_others"]; ns_ = new.get("still_open_awaiting_others", [])
print(f"still_open old={len(os_)} new={len(ns_)}")
pos = -1; ordered = True
for s in os_:
    hits = [i for i, x in enumerate(ns_) if x == s]
    if not hits:
        fails.append(f"still_open 逐字丢失: {s[:70]}")
        ordered = False
    else:
        h = [i for i in hits if i > pos]
        if not h:
            ordered = False
            fails.append(f"still_open 顺序倒置: {s[:50]}")
        else:
            pos = h[0]
            print(f"  ✅ [{pos}] {s[:55]}")

# D) 短字段
for k in ("adjudicator", "purpose", "reading_note", "self_limit", "notify_only"):
    if old.get(k) != new.get(k):
        fails.append(f"字段 {k} 被改动")

# E) 新增条目清单
print("inventory 新增:", [x.get("item") for x in ni[len(oi):]])
print("still_open 新增:", [x[:60] for x in ns_ if x not in os_])
print("subject:", new.get("subject"))
print()
if fails:
    print("VERDICT = 内容有损 ❌")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("VERDICT = 无内容丢失 ✅（旧条目逐字仍在、顺序保持、短字段未动，仅有新增）")
