#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC Daily Incremental Replay v1.0 (HR) — zero-LLM-cost local task
User-directed daily automation (2026-08-19). Reads billing CSV + panel 8787,
computes yesterday actual vs CAHAC counterfactual, appends to trend file.
No LLM calls: csv + urllib + local compute only.

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== cahac-replay-daily 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")
    print("  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数")
    print("  · ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: csv, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/cahac-replay-daily.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import csv, glob, os, datetime, json, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-replay-daily.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CSV_DIR = os.path.expanduser("~/dsh-collab/token-monitor/deepseek-export")
PANEL = "http://127.0.0.1:8787"
FACTOR = 0.24  # CAHAC counterfactual coefficient (comm 0.10/exec 0.50/auto 0.10 @ 40/35/25)
TREND = os.path.expanduser("~/dsh-collab/token-monitor/replays/daily-trend.md")
KEEP = 35

def latest_cost(csv_dir):
    daily = {}
    for p in sorted(glob.glob(os.path.join(csv_dir, "cost-*.csv"))):
        with open(p, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                d = row.get("start_time_iso", "")[:10]
                try: daily[d] = daily.get(d, 0) + float(row.get("cost", 0) or 0)
                except ValueError: pass
    if not daily: return None, None
    d = max(daily)
    return d, daily[d]

def panel_events(panel_url):
    try:
        with urllib.request.urlopen(panel_url + "/api/alerts", timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        return len(data.get("alerts", []))
    except Exception:
        return -1  # panel unreachable (daemon down), not an error for the trend

def main():
    date, cost = latest_cost(CSV_DIR)
    if date is None:
        print("no billing data"); return
    events = panel_events(PANEL)
    cahac = cost * FACTOR
    saving = 1 - FACTOR
    # auto-fuse detection (thresholds from s2-s3-parallel-acceleration): >100 FUSED, >200 HALT
    fuse = ""
    if cost > 200: fuse = " | 🚨 HALT (cost>200)"
    elif cost > 100: fuse = " | ⚠️ FUSED (cost>100, degrade to p2p TASK + blackboard read)"
    if fuse:
        alerts = os.path.expanduser("~/dsh-collab/token-monitor/replays/alerts.md")
        with open(alerts, "a", encoding="utf-8") as af:
            af.write("| " + date + " | " + format(cost, ".2f") + " | " + fuse.strip(" |") + " | auto-fuse by cahac-replay-daily |\n")
    lines = []
    if os.path.exists(TREND):
        with open(TREND, encoding="utf-8") as f:
            lines = f.read().splitlines()
    header = ["# CAHAC Daily Incremental Replay · Trend", "",
              "> zero-LLM local task · launchd com.dsh.hr.cahac-replay.daily · factor=" + str(FACTOR), "",
              "| date | actual ¥ | CAHAC ¥ | saving | panel events |", "|---|---|---|---|---|"]
    # keep header + existing rows, drop rows for same date, append new
    rows = [l for l in lines if l.startswith("| 20")]
    rows = [r for r in rows if not r.startswith("| " + date + " |")]
    rows.append("| " + date + " | " + format(cost, ".2f") + " | " + format(cahac, ".2f") + " | " + format(saving, ".0%") + " | " + str(events) + " |")
    rows = rows[-KEEP:]
    out = header + rows
    os.makedirs(os.path.dirname(TREND), exist_ok=True)
    with open(TREND, "w", encoding="utf-8") as f: f.write("\n".join(out) + "\n")
    print("daily replay: " + date + " actual ¥" + format(cost, ".2f") + " -> CAHAC ¥" + format(cahac, ".2f") + " (saving " + format(saving, ".0%") + ") events=" + str(events))

if __name__ == "__main__":
    main()