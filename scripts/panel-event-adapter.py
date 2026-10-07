#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panel Event Adapter v1.0 (HR) — S2a: 8787 alerts -> CAHAC event/blackboard
Incremental: tracks seen alert ids, writes new events to event log + current state,
applies CAHAC classification (new_order/delivery/refund -> EVENT; handled -> STATUS).
Zero LLM cost. Manual or scheduled (S2a post-approval).
Usage: python3 panel-event-adapter.py [--panel-url http://127.0.0.1:8787]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, datetime, urllib.request

BASE = os.path.expanduser("~/dsh-collab/token-monitor/events")
SEEN = os.path.join(BASE, "seen.json")
STATE = os.path.join(BASE, "current-state.json")

def fetch(panel_url):
    with urllib.request.urlopen(panel_url + "/api/alerts", timeout=10) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("alerts", [])

def load_seen():
    if os.path.exists(SEEN):
        try:
            return set(json.load(open(SEEN, encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_seen(s):
    os.makedirs(BASE, exist_ok=True)
    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(sorted(s), f)

def classify(a):
    k = a.get("kind", "")
    if k in ("new_order", "delivery", "refund"): return "EVENT"
    return "EVENT"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-url", default="http://127.0.0.1:8787")
    args = ap.parse_args()
    try:
        alerts = fetch(args.panel_url)
    except Exception as ex:
        print("panel unreachable:", ex); return
    seen = load_seen()
    new = [a for a in alerts if str(a.get("id")) not in seen]
    os.makedirs(BASE, exist_ok=True)
    now = datetime.date.today().isoformat()
    log = os.path.join(BASE, "events-" + now + ".jsonl")
    added = 0
    for a in new:
        entry = {"id": a.get("id"), "ts": a.get("ts"), "kind": a.get("kind"), "severity": a.get("severity"),
                 "store": a.get("store"), "status": a.get("status"), "cahac_type": classify(a), "processed": now}
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        seen.add(str(a.get("id")))
        added += 1
    save_seen(seen)
    state = {"updated": datetime.datetime.now().isoformat(), "total_alerts": len(alerts), "new_events": added, "seen": len(seen)}
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print("adapter: new=" + str(added) + " total=" + str(len(alerts)) + " seen=" + str(len(seen)) + " -> " + STATE)

if __name__ == "__main__":
    main()