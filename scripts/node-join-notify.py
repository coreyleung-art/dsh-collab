#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-join-notify v1.0 (HR) — 节点接入自动告知（架构阶段 2.4）

监听跨设备黑板 :8792 nodes/ 域：新节点注册 / 首次心跳 / 离线（心跳超时）
→ 发布事件总线 agent.online / agent.offline → 值班消费后定向 agent_send 告知 HR/协调者/设备协调。
零 LLM。用法：python3 node-join-notify.py [--blackboard http://127.0.0.1:8792] [--once]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, urllib.request, hashlib

BB = "http://127.0.0.1:8792"
STATE = os.path.expanduser("~/dsh-collab/token-monitor/node-join-state.json")
HEARTBEAT_TIMEOUT_S = 180  # 3 分钟无心跳=离线

def _req(method, path, data=None):
    url = os.environ.get("NJN_BB", BB) + path
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as ex:
        return {"error": str(ex)[:80]}

def list_nodes():
    r = _req("GET", "/nodes/")
    if "list" not in r:
        return {}
    return r["list"]

def publish_event(topic, summary):
    """写 event-bus 事件（经 event-bus.py --publish 的等价逻辑：直接写事件日志）"""
    base = os.path.expanduser("~/dsh-collab/token-monitor/event-bus/events")
    os.makedirs(base, exist_ok=True)
    dedup = hashlib.sha256((topic + summary).encode()).hexdigest()[:16]
    ev = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "topic": topic,
          "payload": {"summary": summary}, "dedup": dedup, "consumed": False}
    with open(os.path.join(base, "events-" + datetime.date.today().isoformat() + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print("EVENT:", topic, summary[:60])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blackboard", default=BB)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    os.environ["NJN_BB"] = args.blackboard
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        state = {}
    now = time.time()
    nodes = list_nodes()
    # 1) 新注册节点（nodes/<id> 存在但 state 无记录）
    for key in nodes:
        nid = key.split("/")[-1]
        if nid == "heartbeat":
            continue
        if nid not in state:
            state[nid] = {"first_seen": now, "last_heartbeat": now, "notified": False}
            publish_event("agent.online", "节点上线: %s（新注册 %s）" % (nid, key))
            state[nid]["notified"] = True
    # 2) 心跳更新（nodes/<id>/heartbeat）
    for key in nodes:
        if key.endswith("/heartbeat"):
            nid = key.split("/")[-2]
            if nid not in state:
                state[nid] = {"first_seen": now, "last_heartbeat": now, "notified": False}
                publish_event("agent.online", "节点上线: %s（首次心跳）" % nid)
                state[nid]["notified"] = True
            else:
                state[nid]["last_heartbeat"] = now
    # 3) 离线检测（已知节点心跳超时）
    for nid, s in list(state.items()):
        if now - s.get("last_heartbeat", now) > HEARTBEAT_TIMEOUT_S and not s.get("offline_notified"):
            publish_event("agent.offline", "节点离线: %s（%d 秒无心跳）" % (nid, int(now - s.get("last_heartbeat", now))))
            state[nid]["offline_notified"] = True
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("node-join-notify: nodes=%d tracked=%d" % (len(nodes), len(state)))

if __name__ == "__main__":
    main()
