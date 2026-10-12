#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repro-census.py — data/ops 全段普查（只读；输入 /tmp/bb-ops.json，由 repro-all.sh 先抓）"""
import json, collections, datetime, os
P = "/tmp/bb-ops.json"
if not os.path.exists(P):
    raise SystemExit("先跑: curl -s -m 30 http://127.0.0.1:8792/data/ops/ -o /tmp/bb-ops.json")
d = json.load(open(P)); L = d.get("list") or {}
print("抓取时刻:", datetime.datetime.now().isoformat())
print("★ data/ops/ 前缀下列举 total:", d.get("total"), " list 条数:", len(L))
print("   （★ 这是 data/ops 前缀下的键数，不是【整个板】的键数；全板另测：curl .../data/ 与 .../notes/）")
g = collections.defaultdict(list)
for k, v in L.items():
    p = k.split("/")
    if len(p) >= 3 and p[0] == "data" and p[1] == "ops":
        g[p[2]].append((k, v))
print("data/ops 下【第三段】去重数:", len(g))
print()
print("=== 条数 >=2 的段（含键形态与 version）===")
print(f"{'段':26s}{'条数':>7s}{'maxVer':>8s}  样例键")
for s, items in sorted(g.items(), key=lambda x: -len(x[1])):
    if len(items) >= 2:
        mv = max((v.get("version") or 0) for _, v in items)
        print(f"{s:26s}{len(items):7d}{mv:8d}  {items[0][0]}")
print()
print("=== 题面点名的 13 个段（★ 逐个实数）===")
for t in ["pollution","drift-alert","plugin-selfcheck","channel-gate-weekly",
          "drift-delivery-failure","drift-heartbeat","auth-probe","bus-expired-alert",
          "gate-weekly-audit-","pitfalls","probe","resource-gate","queue-condense"]:
    n = len(g.get(t, []))
    print(f"  data/ops/{t:24s} 条数={n}" + ("   ★ 板上无此段" if n == 0 else ""))
print()
print("=== gate-weekly-audit-* 实际键 ===")
for k in L:
    if "/gate-weekly-audit-" in k: print("  ", k, "ts=", L[k].get("ts"))
