#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""waimai-replay v1.0 (HR) — 外卖运营全量回放引擎（监察体系 L2）

按时间窗口回放外卖操作轨迹：读审计日志 → 时间线重建 → 成本归因 → 异常标注 → 回放报告
成本归因复用 CAHAC 权重（EVENT 0.05×/STATUS 0.05×/p2p 1×/broadcast 10× 相对权重）。
零 LLM 成本。用法：
  python3 waimai-replay.py --since 2026-08-19 --until 2026-08-20 [--store 客村店] [--out report.md]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, glob, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/waimai-replay.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

OUT = os.path.expanduser("~/dsh-collab/token-monitor/waimai-audit")
CAHAC_WEIGHT = {"EVENT": 0.05, "STATUS": 0.05, "TASK": 1.0, "COLLAB": 1.0, "BATCH": 0.05, "BROADCAST": 10.0, "bus_message": 0.05, "new_order": 0.05, "delivery": 0.05, "refund": 0.05}

def load_all(since, until):
    rows = []
    for p in sorted(glob.glob(os.path.join(OUT, "audit-*.jsonl"))):
        d = os.path.basename(p)[6:16]
        if since and d < since: continue
        if until and d > until: continue
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line:
                try: rows.append(json.loads(line))
                except Exception: pass
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=datetime.date.today().isoformat())
    ap.add_argument("--until", default=datetime.date.today().isoformat())
    ap.add_argument("--store", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    rows = load_all(args.since, args.until)
    if args.store:
        rows = [r for r in rows if args.store in str(r.get("store", ""))]
    rows.sort(key=lambda r: str(r.get("ts", "")))
    # 时间线重建
    lines = ["# 外卖运营回放 " + args.since + " ~ " + args.until, "", "| # | 时间 | 店铺 | 动作 | 结果 | 来源 | 成本权重 |"]
    total_cost = 0.0
    for i, r in enumerate(rows, 1):
        act = str(r.get("action", ""))
        w = CAHAC_WEIGHT.get(act, CAHAC_WEIGHT.get(str(r.get("cahac_type", "")), 1.0))
        total_cost += w
        lines.append("| %d | %s | %s | %s | %s | %s | %.2f |" % (i, str(r.get("ts", ""))[:19], r.get("store", ""), act, r.get("result", ""), r.get("source", ""), w))
    # 异常标注
    rejects = [r for r in rows if "reject" in str(r.get("action", "")).lower() or "拒" in str(r.get("action", ""))]
    errs = [r for r in rows if r.get("result") in ("error", "failed", "500", "timeout")]
    lines += ["", "## 归因汇总", "- 操作数：%d" % len(rows), "- 相对成本（CAHAC 权重和）：%.1f" % total_cost,
              "- 拒单：%d（%.1f%%）" % (len(rejects), 100 * len(rejects) / max(len(rows), 1)),
              "- 异常：%d" % len(errs)]
    if errs:
        lines += ["", "## 异常明细"]
        for e in errs[:20]:
            lines.append("- %s %s %s → %s" % (e.get("ts", "")[:19], e.get("store", ""), e.get("action", ""), e.get("result", "")))
    report = "\n".join(lines)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(report + "\n")
        print("replay report:", args.out)
    else:
        print(report)

if __name__ == "__main__":
    main()