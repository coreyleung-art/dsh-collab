#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC offline replay v0.2 — multi-scenario (P0/P1/P2)

Scenarios:
  p0       governance/main thread (real: 1836 msgs, ACK 75.3%)
  p1-device device-coord thread (real: 9 msgs, STATUS/EVENT)
  p1-events waimai event stream (model: 50 event msgs/day)
  p2-papers paper-library ingestion (model: 29 papers = 58 scheduling ops)
Weights: p2p=1.0 collab=0.8 blackboard-write=0.1 blackboard-read=0.05 event=0.5 broadcast=10
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-replay-v0.2.log")


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

def calc(counts):
    actual = sum(counts.values())
    m = {"ACK": W["br"], "STATUS": W["bw"], "TASK": W["p2p"], "COLLAB": W["collab"], "EVENT": W["event"], "BROADCAST": W["broadcast"], "OTHER": W["p2p"]}
    cahac = sum(cnt * m.get(t, 1.0) for t, cnt in counts.items())
    return actual, cahac, 1 - cahac/actual if actual else 0

SCEN = {
    "p0": {"label": "P0 治理值守线程(主线程 mswanlwh)", "real": True, "counts": {"ACK": 1383, "STATUS": 369, "TASK": 16, "COLLAB": 16, "EVENT": 5, "OTHER": 47}},
    "p1-device": {"label": "P1 设备协调线程(msxp8lx2)", "real": True, "counts": {"STATUS": 5, "EVENT": 3, "COLLAB": 1}},
    "p1-events": {"label": "P1 外卖事件流(真实: 45 告警/24h, 面板8787)", "real": True, "counts": {"EVENT": 38, "STATUS": 7}},
    "p2-papers": {"label": "P2 论文库入库(模型估计)", "real": False, "counts": {"TASK": 29, "STATUS": 29}},
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", help="p0|p1-device|p1-events|p2-papers|all")
    ap.add_argument("--out", default=os.path.expanduser("~/dsh-collab/token-monitor/replays/cahac-replay-scenarios.md"))
    args = ap.parse_args()
    keys = list(SCEN.keys()) if args.scenario == "all" else [args.scenario]
    L = ["# CAHAC Offline Replay v0.2 · 全场景", "", "> generated: " + datetime.date.today().isoformat() + " · P0/P1-device=真实线程分类, P1-events/P2=模型估计", ""]
    L.append("| 场景 | 消息/操作 | 实际指数 | CAHAC 指数 | 节省 | 数据 |"); L.append("|---|---|---|---|---|---|")
    for k in keys:
        sc = SCEN[k]
        a, c, save = calc(sc["counts"])
        L.append("| " + sc["label"] + " | " + str(a) + " | " + format(a, ".0f") + " | " + format(c, ".1f") + " | **" + format(save, ".0%") + "** | " + ("真实" if sc["real"] else "模型") + " |")
    L.append(""); L.append("## P0 主线程类型分布（真实分类）"); L.append(""); L.append("| 类型 | 数量 | 占比 | 新通道 | 权重 |"); L.append("|---|---|---|---|---|")
    for t, cnt in SCEN["p0"]["counts"].items():
        ch = {"ACK": "blackboard-read", "STATUS": "blackboard-write", "TASK": "p2p", "COLLAB": "p2p-thread", "EVENT": "eventbus", "OTHER": "p2p"}[t]
        wgt = {"ACK": 0.05, "STATUS": 0.10, "TASK": 1.0, "COLLAB": 0.8, "EVENT": 0.5, "OTHER": 1.0}[t]
        L.append("| " + t + " | " + str(cnt) + " | " + format(cnt/1836, ".1%") + " | " + ch + " | " + str(wgt) + "x |")
    L.append(""); L.append("> 注: ACK 占比 75.3% 证实治理值守=ACK 重灾区; 模型场景为估计, v0.3 待真实数据(事件日志/入库流程)校准.")
    L.append("---"); L.append("*cahac-replay-v0.2 · HR · 2026-08-19*")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("scenarios written:", args.out)

if __name__ == "__main__":
    main()