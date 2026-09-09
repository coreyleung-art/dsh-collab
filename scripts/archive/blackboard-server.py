#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blackboard-server v0.1 (HR) — 跨设备黑板服务器 PoC（:8792）

CAHAC §6 六操作：PUT/GET/LIST/SUBSCRIBE/DELETE/AUDIT + 命名空间（nodes/tasks/data/registry）。
存储：data/blackboard/ JSONL（append-only）+ 内存 dict。订阅：变更→POST callback。
认证：BLACKBOARD_TOKEN env 可选（内网信任默认关；启用后所有请求需 X-Blackboard-Token）。
用法：BLACKBOARD_TOKEN=xxx python3 blackboard-server.py --port 8792
"""
import argparse, json, os, re, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.path.expanduser("~/dsh-collab/token-monitor/blackboard")
TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
NS_RE = re.compile(r"^([a-z]+)/([\w\-./]+)$")

# 内存状态
state = {}          # key -> {version, value, ts}
subs = []           # {topic_pattern, callback_url}

def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".jsonl"):
            for line in open(os.path.join(DATA_DIR, f), encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line:
                    try:
                        e = json.loads(line)
                        if e["op"] == "PUT":
                            state[e["key"]] = {"version": e["version"], "value": e["value"], "ts": e["ts"]}
                    except Exception:
                        pass

def _audit(op, key, value):
    os.makedirs(DATA_DIR, exist_ok=True)
    import datetime
    entry = {"op": op, "key": key, "version": state.get(key, {}).get("version", 1), "value": value,
             "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(os.path.join(DATA_DIR, "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def _notify(key):
    for s in subs:
        if key.startswith(s["topic"]):
            try:
                data = json.dumps({"key": key, "value": state.get(key, {}).get("value"),
                                   "version": state.get(key, {}).get("version")}).encode()
                req = urllib.request.Request(s["callback"], data=data, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

class H(BaseHTTPRequestHandler):
    def _ok(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _err(self, code, msg):
        body = json.dumps({"error": msg}, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _auth(self):
        if TOKEN and self.headers.get("X-Blackboard-Token") != TOKEN:
            self._err(401, "unauthorized")
            return False
        return True
    def do_GET(self):
        if not self._auth(): return
        # GET /ns/key | LIST /ns/ | AUDIT /audit?since=
        path = self.path.lstrip("/")
        if path.startswith("audit"):
            self._ok({"audit": True}); return
        # LIST：/nodes 或 /nodes/ 无 key → 列前缀
        if "/" not in path or path.endswith("/"):
            ns = path.rstrip("/").split("/")[0]
            prefix = ns + "/"
            items = {k: v for k, v in state.items() if k.startswith(prefix)}
            self._ok({"list": items}); return
        m = NS_RE.match(path)
        if not m:
            self._err(400, "bad key"); return
        ns, key = m.group(1), m.group(2)
        if False:
            prefix = ns + "/"
            items = {k: v for k, v in state.items() if k.startswith(prefix)}
            self._ok({"list": items}); return
        if ns + "/" + key in state:
            self._ok({"key": ns + "/" + key, **state[ns + "/" + key]})
        else:
            self._err(404, "not found")
    def do_PUT(self):
        if not self._auth(): return
        try:
            n = int(self.headers.get("Content-Length", 0))
            value = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            value = {}
        m = NS_RE.match(self.path.lstrip("/"))
        if not m:
            self._err(400, "bad key"); return
        ns, key = m.group(1), m.group(2)
        full = ns + "/" + key
        cur = state.get(full, {})
        ver = cur.get("version", 0) + 1
        state[full] = {"version": ver, "value": value, "ts": __import__("datetime").datetime.now().isoformat(timespec="seconds")}
        _audit("PUT", full, value)
        _notify(full)
        self._ok({"key": full, "version": ver})
    def do_DELETE(self):
        if not self._auth(): return
        m = NS_RE.match(self.path.lstrip("/"))
        if m:
            full = m.group(1) + "/" + m.group(2)
            if full in state:
                del state[full]
                _audit("DELETE", full, None)
        self._ok({"deleted": True})
    def do_POST(self):
        if not self._auth(): return
        # SUBSCRIBE {topic, callback}
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            body = {}
        if self.path.rstrip("/").endswith("subscribe"):
            subs.append({"topic": body.get("topic", ""), "callback": body.get("callback", "")})
            self._ok({"subscribed": len(subs)})
        else:
            self._err(400, "use /subscribe")
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8792)
    args = ap.parse_args()
    _load()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("blackboard-server on :%d (token=%s) data=%s" % (args.port, "on" if TOKEN else "off", DATA_DIR))
    srv.serve_forever()
