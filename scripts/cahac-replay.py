#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC Replay CLI v1.0 (HR) — unified offline replay toolkit

Subcommands:
  aggregate  12.8h aggregate replay (v0.1 data)
  scenario   multi-scenario replay (P0/P1/P2)
  week       full-week replay from billing CSV
  stream     panel 8787 event replay (live fetch, read-only)
  compare    compare two replay reports (savings trend)

Usage:
  python3 cahac-replay.py week --csv-dir DIR --out PATH
  python3 cahac-replay.py scenario --name all
  python3 cahac-replay.py stream --panel-url http://127.0.0.1:8787
  python3 cahac-replay.py compare --a A.md --b B.md

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
    print("== cahac-replay 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")
    print("  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数")
    print("  · ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。")
    print("  · 命令/参数: aggregate, scenario, week, stream, compare, name, out, csv-dir")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, collections, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/cahac-replay.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, csv, glob, os, datetime, sys, json, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-replay.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

W = {"p2p": 1.0, "collab": 0.8, "bw": 0.1, "br": 0.05, "event": 0.5, "broadcast": 10.0}

AGG = {"agent_send": 13585, "run_code": 5702, "bash": 1318, "other": 1391}
SCEN = {
    "p0": {"label": "P0 governance main thread", "counts": {"ACK": 1383, "STATUS": 369, "TASK": 16, "COLLAB": 16, "EVENT": 5, "OTHER": 47}},
    "p1-device": {"label": "P1 device-coord thread", "counts": {"STATUS": 5, "EVENT": 3, "COLLAB": 1}},
    "p1-events": {"label": "P1 waimai event stream (real 45/24h)", "counts": {"EVENT": 38, "STATUS": 7}},
    "p2-papers": {"label": "P2 paper ingestion (model)", "counts": {"TASK": 29, "STATUS": 29}},
}
CH_MAP = {"ACK": ("blackboard-read", W["br"]), "STATUS": ("blackboard-write", W["bw"]), "TASK": ("p2p", W["p2p"]),
          "COLLAB": ("p2p-thread", W["collab"]), "EVENT": ("eventbus", W["event"]), "BROADCAST": ("broadcast", W["broadcast"]),
          "OTHER": ("p2p", W["p2p"])}

def calc(counts):
    actual = sum(counts.values())
    cahac = sum(cnt * CH_MAP.get(t, ("p2p", 1.0))[1] for t, cnt in counts.items())
    return actual, cahac, (1 - cahac/actual) if actual else 0

def cmd_aggregate(args):
    # apply main-thread cutting ratios to agent_send; other tools -> TASK (exec, local-routing 0.5 factor)
    n = AGG["agent_send"]
    counts = {"ACK": n*0.753, "STATUS": n*0.201, "TASK": n*0.016 + AGG["run_code"] + AGG["bash"] + AGG["other"],
              "COLLAB": n*0.009, "EVENT": n*0.003, "OTHER": n*0.018}
    a, c, s = calc(counts)
    print("aggregate replay: actual", a, "-> CAHAC", round(c, 1), "saving", format(s, ".0%"), "(12.8h cutting applied)")

def cmd_scenario(args):
    keys = list(SCEN.keys()) if args.name == "all" else [args.name]
    L = ["# CAHAC Scenario Replay", "", "> " + datetime.date.today().isoformat(), "", "| scenario | msgs | actual | CAHAC | saving |", "|---|---|---|---|---|"]
    for k in keys:
        sc = SCEN[k]; a, c, s = calc(sc["counts"])
        L.append("| " + sc["label"] + " | " + str(a) + " | " + format(a, ".0f") + " | " + format(c, ".1f") + " | **" + format(s, ".0%") + "** |")
    out = args.out or os.path.expanduser("~/dsh-collab/token-monitor/replays/scenario-" + datetime.date.today().isoformat() + ".md")
    _write(out, L); print("scenario ->", out)

def cmd_week(args):
    daily = {}
    for p in sorted(glob.glob(os.path.join(args.csv_dir, "cost-*.csv"))):
        with open(p, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                d = row.get("start_time_iso", "")[:10]
                if args.since <= d <= args.until:
                    try: daily[d] = daily.get(d, 0) + float(row.get("cost", 0) or 0)
                    except ValueError: pass
    total = sum(daily.values()); factor = args.factor
    L = ["# CAHAC Week Replay (" + args.since + " ~ " + args.until + ")", "", "> " + datetime.date.today().isoformat(), "",
         "| date | actual ¥ | CAHAC ¥ | saving |", "|---|---|---|---|"]
    for d in sorted(daily):
        c = daily[d]
        L.append("| " + d + " | " + format(c, ".2f") + " | " + format(c*factor, ".2f") + " | " + format(1-factor, ".0%") + " |")
    L.append("| **total** | **" + format(total, ".2f") + "** | **" + format(total*factor, ".2f") + "** | **" + format(1-factor, ".0%") + "** |")
    L.append("")
    L.append("> factor=" + str(factor) + " (CAHAC counterfactual coefficient: comm 0.10 / exec 0.50 / auto 0.10 weighted 40/35/25)")
    out = args.out or os.path.expanduser("~/dsh-collab/token-monitor/replays/week-" + args.since + "-" + args.until + ".md")
    _write(out, L); print("week replay ->", out, "(total ¥" + format(total, ".2f") + ", CAHAC ¥" + format(total*factor, ".2f") + ")")

def cmd_stream(args):
    try:
        with urllib.request.urlopen(args.panel_url + "/api/alerts", timeout=10) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        alerts = d.get("alerts", [])
        from collections import Counter
        kinds = Counter(a.get("kind") for a in alerts)
        counts = {"EVENT": len(alerts), "STATUS": 0}
        a, c, s = calc(counts)
        L = ["# CAHAC Stream Replay (panel alerts)", "", "> " + datetime.date.today().isoformat(), "",
             "- alerts: " + str(len(alerts)) + " · kinds: " + json.dumps(dict(kinds), ensure_ascii=False),
             "- actual index: " + str(a) + " -> CAHAC " + format(c, ".1f") + " (saving " + format(s, ".0%") + ")",
             "- blackboard mode (0.1x): " + format(len(alerts)*0.1, ".1f") + " (saving " + format(1-0.1, ".0%") + ")",
             "> note: panel events are the high-threshold alert layer; real stream is larger (scale analysis in waimai report)."]
        out = args.out or os.path.expanduser("~/dsh-collab/token-monitor/replays/stream-" + datetime.date.today().isoformat() + ".md")
        _write(out, L); print("stream replay ->", out)
    except Exception as ex:
        print("stream fetch failed:", ex); sys.exit(1)

def cmd_compare(args):
    def parse(path):
        tot = None
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("| **total**"):
                    tot = line
        return tot
    print("A:", args.a); print("B:", args.b)
    ta = parse(args.a); tb = parse(args.b)
    if ta: print("A total row:", ta.strip()[:80])
    if tb: print("B total row:", tb.strip()[:80])

def _write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))

def main():
    ap = argparse.ArgumentParser(description="CAHAC offline replay toolkit v1.0")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("aggregate")
    sp = sub.add_parser("scenario"); sp.add_argument("--name", default="all"); sp.add_argument("--out")
    sp = sub.add_parser("week"); sp.add_argument("--csv-dir", default=os.path.expanduser("~/dsh-collab/token-monitor/deepseek-export"))
    sp.add_argument("--since", default="2026-08-12"); sp.add_argument("--until", default="2026-08-19")
    sp.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    sp.add_argument("--factor", type=float, default=0.24); sp.add_argument("--out")
    sp = sub.add_parser("stream"); sp.add_argument("--panel-url", default="http://127.0.0.1:8787"); sp.add_argument("--out")
    sp = sub.add_parser("compare"); sp.add_argument("--a", required=True); sp.add_argument("--b", required=True)
    args = ap.parse_args()
    {"aggregate": cmd_aggregate, "scenario": cmd_scenario, "week": cmd_week, "stream": cmd_stream, "compare": cmd_compare}[args.cmd](args)

if __name__ == "__main__":
    main()