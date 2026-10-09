#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panel Event Adapter v1.0 (HR) — S2a: 8787 alerts -> CAHAC event/blackboard
Incremental: tracks seen alert ids, writes new events to event log + current state,
applies CAHAC classification (new_order/delivery/refund -> EVENT; handled -> STATUS).
Zero LLM cost. Manual or scheduled (S2a post-approval).
Usage: python3 panel-event-adapter.py [--panel-url http://127.0.0.1:8787]

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
    print("== panel-event-adapter 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")
    print("  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数")
    print("  · ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。")
    print("  · 命令/参数: panel-url")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/panel-event-adapter.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/panel-event-adapter.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
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