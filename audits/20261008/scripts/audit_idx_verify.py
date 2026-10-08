#!/usr/bin/env python3
"""索引卡 v3 写后核验：不是「写成功了吗」，而是「**旧内容逐条还在吗**」"""
import json, urllib.request, sys

OLD = "/tmp/idx_dump.txt"
KEY = "notes/mac-mini/audit-verdict-index-20261008"

old = json.load(open(OLD))
try:
    d = json.load(urllib.request.urlopen(f"http://127.0.0.1:8792/{KEY}", timeout=25))
except Exception as e:
    print("FETCH_FAIL", e); sys.exit(2)
new = {k: v for k, v in d["value"].items() if k not in ("from", "from_label", "to")}
print("readback_version =", d.get("version"), " ts =", d.get("ts"))

fails = []

# 1) 旧字段一个都不能少
missing = [k for k in old if k not in new]
if missing:
    fails.append(f"字段丢失: {missing}")

# 2) inventory 前 17 条必须逐条 deep-equal（内容和顺序）
oi, ni = old["all_verdicts_inventory"], new.get("all_verdicts_inventory", [])
print(f"inventory: old={len(oi)} new={len(ni)}")
for i, item in enumerate(oi):
    if i >= len(ni) or ni[i] != item:
        fails.append(f"inventory[{i}] 与旧不一致: {item.get('item')}")

# 3) r048 三段必须逐字一致
for k, v in old["r048_three_items_status"].items():
    if new.get("r048_three_items_status", {}).get(k) != v:
        fails.append(f"r048[{k}] 与旧不一致")

# 4) still_open 旧 5 条必须按序保留在开头
os_, ns_ = old["still_open_awaiting_others"], new.get("still_open_awaiting_others", [])
print(f"still_open: old={len(os_)} new={len(ns_)}")
for i, s in enumerate(os_):
    if i >= len(ns_) or ns_[i] != s:
        fails.append(f"still_open[{i}] 与旧不一致")

# 5) 短字段
for k in ("adjudicator", "purpose", "reading_note", "self_limit", "notify_only"):
    if old.get(k) != new.get(k):
        fails.append(f"字段 {k} 被改动")

# 6) 增量确认
print("新增条目:")
for it in ni[len(oi):]:
    print("  +", it.get("date"), "|", it.get("item"), "|", str(it.get("verdict"))[:60])
print("subject =", new.get("subject"))

print()
if fails:
    print("VERDICT = 内容有损 ❌")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("VERDICT = 无内容丢失 ✅（旧字段/旧条目/r048 三段/still_open 逐条保留，仅新增）")
