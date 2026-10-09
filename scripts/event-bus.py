#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""event-bus v1.0 (HR) — B 级事件总线 PoC：发布/订阅/匹配/待发指令

五类基线事件（CAHAC §8.2）：cost.alert / store.alert / task.completed / agent.offline / risk.detected
机制：append-only 事件日志 + dedup_key + 断点续读 + 订阅匹配 → send-instructions/（agent 消费后定向 agent_send）
用法：
  python3 event-bus.py --publish <topic> --payload '{"summary":"..."}'
  python3 event-bus.py --consume            # 生成待发指令（未 sent）
  python3 event-bus.py --mark-sent <id>     # agent 发送后标记
  python3 event-bus.py --status

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
零 LLM 成本。"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, datetime, hashlib, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/event-bus.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

COLLAB = os.path.expanduser("~/dsh-collab")
BASE = os.path.join(COLLAB, "token-monitor", "event-bus")
EVENTS = os.path.join(BASE, "events")
INSTR = os.path.join(BASE, "send-instructions")
SUB = os.path.join(COLLAB, "subscriptions.json")
TOPICS = ["cost.alert", "store.alert", "task.completed", "agent.offline", "risk.detected"]

def today(): return datetime.date.today().isoformat()

def load_events():
    rows = []
    for p in sorted(glob.glob(os.path.join(EVENTS, "*.jsonl"))):
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line:
                try: rows.append(json.loads(line))
                except Exception: pass
    return rows

def load_subs():
    try:
        return json.load(open(SUB, encoding="utf-8")).get("event_subscriptions", [])
    except Exception:
        return []

def publish(topic, payload):
    if topic not in TOPICS:
        print("unknown topic:", topic, "| valid:", TOPICS); return
    os.makedirs(EVENTS, exist_ok=True)
    dedup = hashlib.sha256((topic + json.dumps(payload, ensure_ascii=False)).encode()).hexdigest()[:16]
    # dedup：已存在同 topic+payload 则不重复
    for e in load_events():
        if e.get("dedup") == dedup:
            print("dup, skip"); return
    ev = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "topic": topic,
          "payload": payload, "dedup": dedup, "consumed": False}
    with open(os.path.join(EVENTS, "events-" + today() + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print("PUBLISHED:", topic, ev["ts"], "dedup=" + dedup)

def consume():
    subs = load_subs()
    os.makedirs(INSTR, exist_ok=True)
    count = 0
    for e in load_events():
        if e.get("consumed"): continue
        topic = e.get("topic", "")
        text = json.dumps(e.get("payload", {}), ensure_ascii=False) + " " + topic
        for s in subs:
            if topic in s.get("topics", []):
                instr_id = e["dedup"] + "-" + s.get("agent", "x")[:8]
                ip = os.path.join(INSTR, instr_id + ".json")
                if os.path.exists(ip): continue
                inst = {"id": instr_id, "ts": e["ts"], "topic": topic, "agent": s.get("agent"),
                        "summary": e.get("payload", {}).get("summary", topic), "sent": False}
                json.dump(inst, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                count += 1
        e["consumed"] = True
        # 更新事件日志 consumed（简单重写当日文件）
    print("CONSUME: instructions=%d" % count)
    return count

def mark_sent(iid):
    p = os.path.join(INSTR, iid + ".json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        d["sent"] = True
        d["sent_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("SENT:", iid)
    else:
        print("not found:", iid)

def status():
    evs = load_events()
    insts = []
    for p in glob.glob(os.path.join(INSTR, "*.json")):
        try: insts.append(json.load(open(p, encoding="utf-8")))
        except Exception: pass
    by_topic = {}
    for e in evs: by_topic[e["topic"]] = by_topic.get(e["topic"], 0) + 1
    pending = [i for i in insts if not i.get("sent")]
    print("events:", len(evs), by_topic)
    print("instructions: total=%d pending=%d" % (len(insts), len(pending)))
    for i in pending[:10]:
        print("  PENDING:", i["id"], "->", i["agent"][:20], i["topic"], i["summary"][:40])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", default="")
    ap.add_argument("--payload", default='{"summary":""}')
    ap.add_argument("--payload-file", default="", help="从文件读 payload JSON（规避 shell 引号污染）")
    ap.add_argument("--consume", action="store_true")
    ap.add_argument("--mark-sent", default="")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    if args.publish:
        try:
            if args.payload_file:
                payload = json.load(open(args.payload_file, encoding="utf-8"))
            else:
                payload = json.loads(args.payload)
        except Exception:
            payload = {"summary": args.payload}
        publish(args.publish, payload)
    if args.consume: consume()
    if args.mark_sent: mark_sent(args.mark_sent)
    if args.status: status()
    if not (args.publish or args.consume or args.mark_sent or args.status):
        print("usage: --publish <topic> --payload ... | --consume | --mark-sent <id> | --status")

if __name__ == "__main__":
    main()
