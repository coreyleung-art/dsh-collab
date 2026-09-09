#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC offline replay v0.1 (HR) — apply CAHAC channel selector to real Aug aggregates"""
import argparse, os, datetime

AGG = {"agent_send": 13585, "run_code": 5702, "bash": 1318, "other": 1391}
TOTAL = sum(AGG.values())
W = {"p2p": 1.0, "collab": 0.8, "bw": 0.1, "br": 0.05, "event": 0.5, "mailbox": 0.05, "broadcast": 10.0}

def fmt(x, spec):
    return format(x, spec)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ack-ratio", type=float, default=0.60)
    ap.add_argument("--out", default=os.path.expanduser("~/dsh-collab/token-monitor/replays/cahac-replay-2026-08-19.md"))
    args = ap.parse_args()
    n = AGG["agent_send"]
    types = {"ACK": n*args.ack_ratio, "STATUS": n*0.20, "COLLAB": n*0.10, "TASK": n*0.07, "EVENT": n*0.02, "BROADCAST": n*0.01}
    actual = n * 1.0
    cahac = (types["ACK"]*W["br"] + types["STATUS"]*W["bw"] + types["COLLAB"]*W["collab"]
             + types["TASK"]*W["p2p"] + types["EVENT"]*W["event"] + types["BROADCAST"]*W["broadcast"])
    save = 1 - cahac/actual
    peak_day, storm_share = 748.20, 0.40
    storm_cost = peak_day * storm_share
    saved_peak = storm_cost * save
    L = []
    L.append("# CAHAC Offline Replay v0.1"); L.append("")
    L.append("> generated: " + datetime.date.today().isoformat() + " · data: 12.8h aggregate (21,996 events) + billing calibration")
    L.append("> assumption: agent_send=" + str(n) + ", ratios ACK=" + fmt(args.ack_ratio, ".0%") + "/STATUS=20%/COLLAB=10%/TASK=7%/EVENT=2%/BROADCAST=1%")
    L.append(""); L.append("## 1. Event distribution (12.8h)"); L.append(""); L.append("| tool | count | share |"); L.append("|---|---|---|")
    for k in ["agent_send", "run_code", "bash", "other"]:
        L.append("| " + k + " | " + str(AGG[k]) + " | " + fmt(AGG[k]/TOTAL, ".1%") + " |")
    L.append(""); L.append("## 2. CAHAC channel remap (agent_send part)"); L.append(""); L.append("| type | count(est) | old | new channel | new weight |"); L.append("|---|---|---|---|---|")
    chmap = {"ACK": ("blackboard-read", W["br"]), "STATUS": ("blackboard-write", W["bw"]), "COLLAB": ("p2p-thread", W["collab"]),
             "TASK": ("p2p", W["p2p"]), "EVENT": ("eventbus", W["event"]), "BROADCAST": ("broadcast-whitelist", W["broadcast"])}
    for t, cnt in types.items():
        ch, wgt = chmap[t]
        L.append("| " + t + " | " + fmt(cnt, ".0f") + " | 1.0x | " + ch + " | " + fmt(wgt, ".2f") + "x |")
    L.append(""); L.append("## 3. Cost comparison (agent_send channel)"); L.append(""); L.append("| basis | cost index |"); L.append("|---|---|")
    L.append("| current (all p2p) | " + fmt(actual, ".0f") + " |")
    L.append("| CAHAC (graded) | " + fmt(cahac, ".0f") + " |")
    L.append("| saving | " + fmt(save, ".0%") + " |")
    L.append(""); L.append("## 4. Money calibration (peak day 8/18)"); L.append("")
    L.append("- peak day = ¥" + str(peak_day) + ", storm share ~40% -> related ≈ ¥" + fmt(storm_cost, ".0f"))
    L.append("- if CAHAC: saving " + fmt(save, ".0%") + " ≈ **¥" + fmt(saved_peak, ".0f") + "/peak day**")
    L.append("- monthly (3 peak days/mo): ≈ ¥" + fmt(saved_peak*3, ".0f") + "/mo")
    L.append(""); L.append("> note: v0.1 = event-level weight model; ACK ratio tunable (--ack-ratio); token-level replay in v0.2 when thread history available.")
    L.append("---"); L.append("*cahac-replay-v0.1 · HR · 2026-08-19*")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("replay done: save=" + fmt(save, ".1%") + " peak-day ¥" + fmt(saved_peak, ".0f") + " out=" + args.out)

if __name__ == "__main__":
    main()