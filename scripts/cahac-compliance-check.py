#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC compliance checker v0.1 (HR) — consistency assurance
Scans agent profile exports for Agent Card fields (channels/budget/topics/comm_style),
reports adoption rate. Weekly run with agent_profiles export.
Usage: python3 cahac-compliance-check.py --profiles profiles.json
"""
import argparse, json, os, datetime

CARD_FIELDS = ["channels", "budget", "topics", "comm_style"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True)
    args = ap.parse_args()
    profs = json.load(open(args.profiles, encoding="utf-8"))
    profs = profs.get("profiles", profs) if isinstance(profs, dict) else profs
    total = len(profs)
    adopted = 0
    missing = []
    for p in profs:
        s = json.dumps(p, ensure_ascii=False)
        if "cahac" in s.lower() or any(f in s.lower() for f in CARD_FIELDS):
            adopted += 1
        else:
            missing.append(p.get("agentId", "?"))
    L = ["# CAHAC 一致性检查 · " + datetime.date.today().isoformat(), "",
         "- profiles: " + str(total) + " · 已声明 Agent Card: " + str(adopted) + " (" + format(adopted/total, ".0%") if total else "0",
         "- 缺失: " + str(len(missing)) + " 会话", "", "## 建议", "",
         "1. 未声明会话=默认 p2p（向后兼容，CAHAC §11）",
         "2. 关键角色（协调/HR/运营/设备）优先补 Agent Card 声明（channels/budget/topics）",
         "3. 行为一致性：审计 agent_send 占比周检（目标 <30%）",
         "4. 结果一致性：每日回放/日审自动验证成本"]
    out = os.path.expanduser("~/dsh-collab/token-monitor/replays/compliance-" + datetime.date.today().isoformat() + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("compliance:", out, "| adopted", adopted, "/", total)

if __name__ == "__main__":
    main()