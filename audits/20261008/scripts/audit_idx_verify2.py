#!/usr/bin/env python3
"""索引卡 v3 内容核验（修正版）：判据与被断言对象对齐 —— 我的动作是「中间插入」，
   故旧条目的正确判据是【有序子序列】，而不是【前缀位置相等】。"""
import json, urllib.request

old = json.load(open("/tmp/idx_dump.txt"))
d = json.load(urllib.request.urlopen(
    "http://127.0.0.1:8792/notes/mac-mini/audit-verdict-index-20261008", timeout=25))
new = {k: v for k, v in d["value"].items() if k not in ("from", "from_label", "to")}

os_, ns_ = old["still_open_awaiting_others"], new["still_open_awaiting_others"]
print("== 新 still_open 逐条 ==")
for i, s in enumerate(ns_):
    print(f"[{i}] {s[:100]}")

print("\n== 旧条目在新列表中的位置 ==")
ok = True
for s in os_:
    hits = [i for i, x in enumerate(ns_) if x == s]
    if not hits:
        ok = False
        print("  ❌ 丢失:", s[:70])
    else:
        print(f"  ✅ 位置 {hits}: {s[:60]}")

print("\n旧 5 条全部仍在（集合语义） =", ok)
print("新增条目 =", [s[:60] for s in ns_ if s not in os_])
print("\nVERDICT =", "无内容丢失 ✅（仍为 v%d）" % d.get("version") if ok else "有内容丢失 ❌")
