#!/usr/bin/env python3
"""读 PSTD 作者的「12 条超时卡内联条目」卡，取出条目结构（先看清再验证）"""
import json, urllib.request

KEY = "notes/mac-mini/author-timeout-entries-12-inline-20261008"
d = json.load(urllib.request.urlopen(f"http://127.0.0.1:8792/{KEY}", timeout=25))
v = d["value"]
print("ts =", d.get("ts"), "version =", d.get("version"))
print("value keys =", list(v.keys()))
for k, val in v.items():
    if isinstance(val, list):
        print(f"\n[{k}] list len={len(val)}")
        for i, it in enumerate(val):
            print(f"  ({i}) {json.dumps(it, ensure_ascii=False)[:220]}")
    elif isinstance(val, dict):
        print(f"\n[{k}] dict keys={list(val.keys())}")
        for kk, vv in val.items():
            print(f"   {kk} = {json.dumps(vv, ensure_ascii=False)[:180]}")
    else:
        print(f"\n[{k}] = {str(val)[:400]}")
