#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weekly cost/replay summary generator v0.1 (HR) — alert layer
Aggregates daily-trend into weekly summary + lists alerts (if any).
launchd template: com.dsh.hr.cahac-replay.weekly (Sunday 10:00)
"""
import os, datetime

BASE = os.path.expanduser("~/dsh-collab/token-monitor/replays")
TREND = os.path.join(BASE, "daily-trend.md")
ALERTS = os.path.join(BASE, "alerts.md")

def main():
    rows = []
    if os.path.exists(TREND):
        with open(TREND, encoding="utf-8") as f:
            rows = [l for l in f.read().splitlines() if l.startswith("| 20")]
    alerts = []
    if os.path.exists(ALERTS):
        with open(ALERTS, encoding="utf-8") as f:
            alerts = [l for l in f.read().splitlines() if l.startswith("| 20")]
    week = rows[-7:]
    total = sum(float(r.split("|")[2].strip()) for r in week) if week else 0
    cahac = sum(float(r.split("|")[3].strip()) for r in week) if week else 0
    L = ["# 每周成本/回放汇总 · " + datetime.date.today().isoformat(), "",
         "- 近 7 日实际 ¥" + format(total, ".2f") + " · CAHAC 反事实 ¥" + format(cahac, ".2f") + " (saving " + format(1 - cahac/total, ".0%") + ")" if total else "- 无趋势数据",
         "- 告警数: " + str(len(alerts)), ""]
    if alerts:
        L.append("## 告警（需关注）"); L.append(""); L.append("| 日期 | 成本 | 级别 | 说明 |"); L.append("|---|---|---|---|")
        L.extend(alerts[-10:])
    else:
        L.append("✅ 本周无熔断告警")
    L.append(""); L.append("---"); L.append("*weekly-summary v0.1 · HR · 2026-08-19*")
    out = os.path.join(BASE, "weekly-" + datetime.date.today().isoformat() + ".md")
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("weekly:", out)

if __name__ == "__main__":
    main()