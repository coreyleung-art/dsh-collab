#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R4 · 复跑脚本：drift 告警卡「双板到达率」多口径并列

用途：一条命令复现 5 个时间窗口下的到达率，并对样本为 0 的窗口报「不可判」。
不写任何文件、不改任何状态；只读两板。

复跑：
    python3 research/v7-caliber/evidence/repro-arrival-window.py

★ 口径纪律（本脚本的全部要点）：
  1) 分母 = 本机板在该窗口内的卡（按【内容 ts】= value.ts 归窗，非板级 ts）
  2) 分子 = 该卡同时存在于中枢板（按键名匹配）
  3) 样本 = 0  ⇒  报 "UNDECIDABLE"，不报 0%、不报 100%
  4) 逐窗并列，不合并、不取平均
  5) 自指卡（check=board-central）单独标出 —— 它结构上不可能双板到达
"""
import json
import sys
import time
import urllib.request

LOCAL = "http://127.0.0.1:8792"
CENTRAL = "http://106.53.214.108:8792"
NS = "data/ops/drift-alert/"

WINDOWS = [
    ("1h", 1),
    ("3h", 3),
    ("6h", 6),
    ("24h", 24),
    ("FULL", None),  # None = 全量（累计口径）
]


def fetch(base, key):
    url = "%s/%s" % (base, key)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_ns(base):
    """列举命名空间，返回 {key: value_obj}"""
    d = fetch(base, NS)
    return d.get("list", {}), d.get("total")


def main():
    now_ms = int(time.time() * 1000)
    local, ltotal = fetch_ns(LOCAL)
    central, ctotal = fetch_ns(CENTRAL)

    print("=" * 78)
    print("R4 复跑 · drift 双板到达率多口径")
    print("=" * 78)
    print("时刻(now_ms)     : %d  (%s)" % (now_ms, time.strftime("%Y-%m-%dT%H:%M:%S")))
    print("本机板 total     : %s" % ltotal)
    print("中枢板 total     : %s" % ctotal)
    print("命名空间         : %s" % NS)
    print("-" * 78)

    # 建立中枢键集合（判到达）
    cset = set(central.keys())

    # 逐卡取内容 ts（value.ts）
    cards = []
    for k, v in local.items():
        val = v.get("value") if isinstance(v, dict) else None
        vts = None
        if isinstance(val, dict):
            vts = val.get("ts")
        checks = []
        if isinstance(val, dict):
            for d in (val.get("drifts") or []):
                if isinstance(d, dict):
                    checks.append(d.get("check"))
        cards.append(
            {
                "key": k,
                "vts": vts,
                "board_ts": v.get("ts") if isinstance(v, dict) else None,
                "arrived": k in cset,
                "checks": checks,
                "selfref": "board-central" in checks,
            }
        )

    usable = [c for c in cards if isinstance(c["vts"], int)]
    print("可归窗卡（有 value.ts）: %d / %d" % (len(usable), len(cards)))
    print("-" * 78)

    results = []
    for name, hours in WINDOWS:
        if hours is None:
            sel = usable
        else:
            cut = now_ms - hours * 3600 * 1000
            sel = [c for c in usable if c["vts"] >= cut]
        n = len(sel)
        if n == 0:
            verdict = "UNDECIDABLE"
            rate = None
        else:
            arrived = sum(1 for c in sel if c["arrived"])
            rate = arrived / n * 100.0
            verdict = "OK" if abs(rate - 100.0) < 1e-9 else "FAIL"
            n = n
        results.append((name, hours, n, rate, verdict, sel))
        if rate is None:
            print("窗口 %-5s 样本=%-4d 到达率= UNDECIDABLE  ← 样本为0，不得报0%%/100%%" % (name, n))
        else:
            arr = sum(1 for c in sel if c["arrived"])
            print("窗口 %-5s 样本=%-4d 到达=%-4d 到达率= %6.2f%%  %s" % (name, n, arr, rate, verdict))

    print("-" * 78)
    print("★ 全量口径下的未达卡按日期分布（解释为何全量恒红）")
    miss = [c for c in usable if not c["arrived"]]
    bydate = {}
    for c in miss:
        day = time.strftime("%m-%d", time.localtime(c["vts"] / 1000.0))
        bydate[day] = bydate.get(day, 0) + 1
    for day in sorted(bydate):
        print("   %s : %3d 条未达" % (day, bydate[day]))
    print("   未达合计: %d 条" % len(miss))

    print("-" * 78)
    print("★ 自指卡（check 含 board-central）逐条 —— 结构上不可能双板到达")
    sref = [c for c in usable if c["selfref"]]
    for c in sorted(sref, key=lambda x: x["vts"]):
        t = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(c["vts"] / 1000.0))
        print("   %s  %s  arrived=%s" % (t, c["key"], c["arrived"]))
    print("   自指卡合计: %d 条（其中已到达 %d 条）" % (len(sref), sum(1 for c in sref if c["arrived"])))

    print("=" * 78)
    # 机器可读汇总
    print("JSON_SUMMARY=" + json.dumps(
        {
            "now_ms": now_ms,
            "local_total": ltotal,
            "central_total": ctotal,
            "usable": len(usable),
            "windows": [
                {"window": n, "sample": s, "rate": (None if r is None else round(r, 2)), "verdict": v}
                for (n, h, s, r, v, _sel) in results
            ],
            "miss_by_date": bydate,
            "selfref_total": len(sref),
            "selfref_arrived": sum(1 for c in sref if c["arrived"]),
        },
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
