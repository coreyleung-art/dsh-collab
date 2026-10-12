#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R4 · 复跑脚本 07：把【建议的单一口径】写成可执行形态

目的：让「口径」不是一个说法，而是**一段能跑、能核对、能红的代码**。

建议口径（调研结论，非裁定）：
  ① 窗口        = 滚动 24 小时（= 48 × 巡检周期 1800s）
  ② 样本下限    = n >= 3（低于则不可判；n>=3 只支持【证伪】不支持【确认】）
  ③ 输出三件套  = (n, 到达率, 95% 置信下界)
  ④ 样本不足    = 报 UNDECIDABLE，另由心跳断言承担「流是否在流」
  ⑤ 判据形式    = 到达率 == 100% AND n >= 3   （不得写成 >= 99.5%，见 repro-06）

复跑：
    python3 research/v7-caliber/evidence/repro-07-recommended-caliber.py
"""
import json
import sys
import time
import urllib.request

LOCAL = "http://127.0.0.1:8792"
CENTRAL = "http://106.53.214.108:8792"
NS = "data/ops/drift-alert/"
WINDOW_HOURS = 24
MIN_SAMPLES = 3


def get(base, key):
    with urllib.request.urlopen(base + "/" + key, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def lower_bound(n):
    return None if n < MIN_SAMPLES else 1.0 - 3.0 / n


def main():
    now = int(time.time() * 1000)
    ll = get(LOCAL, NS)["list"]
    cc = set(get(CENTRAL, NS)["list"].keys())
    cut = now - WINDOW_HOURS * 3600 * 1000

    sel = []
    for k, v in ll.items():
        its = (v.get("value") or {}).get("ts")
        if isinstance(its, int) and its >= cut:
            sel.append((its, k, k in cc))

    n = len(sel)
    arrived = sum(1 for _, _, a in sel if a)

    print("=" * 78)
    print("R4 复跑 07 · 建议口径的可执行形态")
    print("=" * 78)
    print("窗口          : 滚动 %d 小时（= 48 × 巡检周期 1800s）" % WINDOW_HOURS)
    print("样本下限      : n >= %d" % MIN_SAMPLES)
    print("读取时刻      : %d (%s)" % (now, time.strftime("%Y-%m-%dT%H:%M:%S")))
    print("窗口下界(ms)  : %d" % cut)
    print("-" * 78)

    if n < MIN_SAMPLES:
        print("样本 n = %d  <  下限 %d" % (n, MIN_SAMPLES))
        print()
        print("⇒ 判定 : UNDECIDABLE （不可判）")
        print("⇒ 不得报 0%%、不得报 100%%")
        print("⇒ 此时「告警流是否在流」由【心跳断言】承担，不塞进本判据")
        verdict = "UNDECIDABLE"
    else:
        rate = arrived / n * 100.0
        lb = lower_bound(n)
        print("样本 n        : %d" % n)
        print("到达          : %d" % arrived)
        print("到达率        : %.2f%%" % rate)
        print("95%% 置信下界  : %.2f%%   ← 判据【不得】声称超过此数" % (lb * 100))
        print()
        ok = (arrived == n)
        print("判据 `到达率 == 100%% AND n >= %d` ⇒ %s" % (MIN_SAMPLES, "PASS" if ok else "FAIL"))
        if ok and lb < 0.95:
            print("★ 注意：虽 PASS，但 n=%d 太小，95%% 置信下界仅 %.2f%%" % (n, lb * 100))
            print("  ⇒ 该 PASS 只支持【尚未发现失败】，不支持【已达 95%% 以上】")
        verdict = "PASS" if ok else "FAIL"

    print("-" * 78)
    print("逐卡（窗口内）")
    for its, k, a in sorted(sel):
        print("   %s  %s  arrived=%s"
              % (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(its / 1000)), k.split("/")[-1], a))
    print("=" * 78)
    print("VERDICT=%s  n=%d  arrived=%d" % (verdict, n, arrived))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
