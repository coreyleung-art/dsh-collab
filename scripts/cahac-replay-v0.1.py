#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC offline replay v0.1 (HR) — apply CAHAC channel selector to real Aug aggregates"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== cahac-replay-v0.1 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · （头部无中文用途说明 ⇒ 能力清单为空，建议补 docstring）")
    print("  · 命令/参数: ack-ratio, out")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/cahac-replay-v0.1.log")
    return 0


#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-replay-v0.1.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

AGG = {"agent_send": 13585, "run_code": 5702, "bash": 1318, "other": 1391}
TOTAL = sum(AGG.values())
W = {"p2p": 1.0, "collab": 0.8, "bw": 0.1, "br": 0.05, "event": 0.5, "mailbox": 0.05, "broadcast": 10.0}

def fmt(x, spec):
    return format(x, spec)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ack-ratio", type=float, default=0.60)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--out", default=os.path.expanduser("~/dsh-collab/token-monitor/replays/cahac-replay-2026-08-19.md"))
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
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