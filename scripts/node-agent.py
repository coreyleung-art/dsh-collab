#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-agent v0.1 (HR) — 节点总线 PoC 执行器

注册→心跳(60s)→命令轮询→本地探针→回报。黑板 :8792 为状态中枢。
用法：python3 node-agent.py --node-id mbp [--blackboard http://127.0.0.1:8792] [--once]
"""
import argparse, json, os, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
PROBES = {
    "dsh": lambda: "ok" if os.path.exists(os.path.expanduser("~/.dsh")) else "missing",
    "blackboard": lambda: _get("/nodes/") != None,
}

def _req(method, path, data=None):
    url = os.environ.get("NODE_AGENT_BB", BB) + path
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as ex:
        return {"error": str(ex)[:80]}

def _get(path):
    return _req("GET", path)

def heartbeat(node_id):
    probes = {k: (v() if callable(v) else v) for k, v in PROBES.items()}
    return _req("PUT", "/nodes/%s/heartbeat" % node_id, {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "load": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0,
        "probes": probes, "health": "ok"})

def register(node_id, caps):
    return _req("PUT", "/nodes/%s" % node_id, {"status": "online", "capabilities": caps, "registered": True})

def poll_commands(node_id):
    """轮询黑板 tasks/<node_id>/cmd 看有没有命令（PoC：命令由调度者 PUT 写入）"""
    r = _req("GET", "/tasks/%s/cmd" % node_id)
    if r and "value" in r and r["value"]:
        cmd = r["value"]
        print("CMD:", cmd)
        _req("DELETE", "/tasks/%s/cmd" % node_id)
        return cmd
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-id", default="mbp")
    ap.add_argument("--blackboard", default=BB)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    args = ap.parse_args()
    os.environ["NODE_AGENT_BB"] = args.blackboard
    caps = ["dsh", "blackboard-client", "scripts"]
    print("register:", register(args.node_id, caps))
    while True:
        hb = heartbeat(args.node_id)
        print("heartbeat:", json.dumps(hb, ensure_ascii=False)[:120])
        cmd = poll_commands(args.node_id)
        if cmd:
            print("  executing:", cmd)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
