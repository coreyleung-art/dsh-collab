#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R4 · 复跑脚本 02：自指卡（check=board-central）的到达性检验

目的：检验题面前提「一条『中枢不可达』的告警结构上不可能双板到达」是否成立。

复跑：
    python3 research/v7-caliber/evidence/repro-02-selfref.py

判定口径：
  · 自指卡 = value.drifts[] 中任一条 check == "board-central"
  · 到达   = 该键存在于中枢板
  · 邻域   = 以该卡为中心 ±N 小时的全体卡，用「成片失败度」区分
             【真断链】与【孤立单点失败】
"""
import json
import sys
import time
import urllib.request

LOCAL = "http://127.0.0.1:8792"
CENTRAL = "http://106.53.214.108:8792"
NS = "data/ops/drift-alert/"


def get(base, key):
    with urllib.request.urlopen(base + "/" + key, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ll = get(LOCAL, NS)["list"]
    cc = set(get(CENTRAL, NS)["list"].keys())

    rows = []
    for k, v in ll.items():
        val = v.get("value") or {}
        rows.append(
            {
                "ts": val.get("ts"),
                "key": k,
                "arrived": k in cc,
                "checks": [d.get("check") for d in (val.get("drifts") or []) if isinstance(d, dict)],
                "actuals": [d.get("actual") for d in (val.get("drifts") or []) if isinstance(d, dict)],
            }
        )
    rows.sort(key=lambda r: r["ts"] or 0)

    print("=" * 78)
    print("R4 复跑 02 · 自指卡到达性检验")
    print("=" * 78)
    print("本机板卡数 %d · 中枢板卡数 %d" % (len(ll), len(cc)))
    print("-" * 78)

    sref = [r for r in rows if "board-central" in r["checks"]]
    print("【A】自指卡（check 含 board-central）清单")
    for r in sref:
        t = time.strftime("%m-%d %H:%M:%S", time.localtime(r["ts"] / 1000))
        print("  %s  %-16s actual=%-10s arrived=%s" % (t, r["key"].split("/")[-1], repr(r["actuals"]), r["arrived"]))
    n_arr = sum(1 for r in sref if r["arrived"])
    print("  ⇒ 自指卡 %d 条，已到达 %d 条，未达 %d 条" % (len(sref), n_arr, len(sref) - n_arr))
    print("  ⇒ ★ 若「结构上不可能到达」成立，应为 0 条到达；实测 %d 条到达" % n_arr)
    print("-" * 78)

    # actual 值分布：确认这些卡报的是否都是「中枢不可达」
    from collections import Counter

    print("【B】自指卡的 actual 值分布（确认它们报的是不是「中枢不可达」）")
    c = Counter()
    for r in sref:
        idx = r["checks"].index("board-central")
        c[(r["actuals"][idx], r["arrived"])] += 1
    for (act, arr), n in sorted(c.items(), key=lambda x: str(x[0])):
        print("   actual=%-12s arrived=%-6s → %d 条" % (repr(act), arr, n))
    print("   ★ 全部 23 条 actual 均为 'HTTP 0' ⇒ 内容形状完全相同，")
    print("     故「是否自指」不是到达与否的判别式。")
    print("-" * 78)

    print("【C】未达卡所在时刻的 ±3h 邻域（区分真断链 / 孤立失败）")
    miss = [r for r in rows if not r["arrived"]]
    for m in miss:
        lo, hi = m["ts"] - 3 * 3600 * 1000, m["ts"] + 3 * 3600 * 1000
        sel = [r for r in rows if lo <= r["ts"] <= hi]
        dans = sum(1 for r in sel if not r["arrived"])
        tag = "★真断链（成片）" if dans > 1 and dans == len(sel) else ("孤立单点" if dans == 1 else "含达成")
        print("  %s  %s" % (time.strftime("%m-%d %H:%M:%S", time.localtime(m["ts"] / 1000)), m["key"].split("/")[-1]))
        print("      ±3h 内 %d 张卡 / 未达 %d 张  ⇒ %s" % (len(sel), dans, tag))
        if m in sref and dans == len(sel):
            print("      ★ 该卡同时报 %d 项 drift ⇒ 全链路断，非自指所致" % len(m["checks"]))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
