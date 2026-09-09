#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blackboard-server v0.2 (coordinator) — 黑板进化版（:8792 兼容升级）

v0.1 → v0.2 变更（2026-08-23 · 协调者，底座进化 P0 三刀）：
  1. 【卡槽效率】result 自动镜像：回报写 tasks/<node>/result（单槽，兼容现有读取者）
     的同时，server 自动复制一份到 tasks/<node>/results/<seq>（seq=毫秒时间戳，
     独立 key 不覆盖）→ 并发回报历史可追溯，不再丢失。
  2. 【通讯桥】订阅去重 + 退订 + 列表：
     - 同 (topic, callback) 只注册一次（不再重复通知）
     - POST /subscribe 带 unsub=true 可退订
     - GET /subs 列出当前订阅者
  3. 【通讯桥】异步通知：notify 走后台线程池，慢回调不阻塞 PUT 返回（防级联超时）
  4. 【健壮性】LIST 分页：GET /ns?limit=N&offset=M 返回 {list,total,limit,offset}
     （默认不截断，保持 v0.1 行为；显式传参才分页）

兼容性：全部 v0.1 API 语义不变（PUT/GET/LIST/SUBSCRIBE/DELETE/AUDIT + 命名空间）。
存储：data/blackboard/ JSONL（append-only）+ 内存 dict；认证：BLACKBOARD_TOKEN env 可选。

用法：BLACKBOARD_TOKEN=xxx python3 blackboard-server-v0.2.py --port 8792
"""
import argparse, json, os, re, threading, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.path.expanduser("~/dsh-collab/token-monitor/blackboard")
TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
NS_RE = re.compile(r"^([a-z]+)/([\w\-./]+)$")
QUEUE_RE = re.compile(r"^tasks/([\w\-]+)/result$")       # tasks/<node>/result → 镜像
MIRROR_NS = "results"                                     # tasks/<node>/results/<seq>

# 内存状态
state = {}          # key -> {version, value, ts}
subs = {}           # (topic, callback) -> {topic, callback, ts}  去重
_notify_pool = ThreadPoolExecutor(max_workers=8)

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
    entry = {"op": op, "key": key, "version": state.get(key, {}).get("version", 1), "value": value,
             "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(os.path.join(DATA_DIR, "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def _notify_one(s, key):
    """单个订阅者回调（在后台线程执行，失败静默）"""
    try:
        data = json.dumps({"key": key, "value": state.get(key, {}).get("value"),
                           "version": state.get(key, {}).get("version")}).encode()
        req = urllib.request.Request(s["callback"], data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def _notify(key):
    """异步通知：全部订阅者回调进线程池，不阻塞 PUT 返回（v0.2 变更 3）"""
    for s in list(subs.values()):
        if key.startswith(s["topic"]):
            _notify_pool.submit(_notify_one, s, key)

def _mirror_result(key):
    """v0.2 变更 1：tasks/<node>/result 自动镜像到 tasks/<node>/results/<seq>"""
    m = QUEUE_RE.match(key)
    if not m:
        return
    node = m.group(1)
    val = state.get(key, {}).get("value")
    if not isinstance(val, dict):
        return
    seq = str(int(datetime.datetime.now().timestamp() * 1000))[-10:]
    mirror_key = "tasks/%s/%s/%s" % (node, MIRROR_NS, seq)
    cur = state.get(mirror_key, {})
    state[mirror_key] = {"version": cur.get("version", 0) + 1,
                         "value": val, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    _audit("PUT", mirror_key, val)
    # 镜像不触发 notify（避免重复通知原订阅者）

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
        path = self.path.lstrip("/")
        # 分页参数（v0.2 变更 4）
        limit, offset = None, 0
        if "?" in path:
            path, qs = path.split("?", 1)
            for kv in qs.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if k == "limit" and v.isdigit(): limit = int(v)
                    elif k == "offset" and v.isdigit(): offset = int(v)
        # GET /subs — 订阅者列表（v0.2 变更 2）
        if path == "subs":
            self._ok({"subscribed": len(subs),
                      "subs": [{"topic": s["topic"], "callback": s["callback"], "ts": s["ts"]}
                               for s in subs.values()]})
            return
        if path.startswith("audit"):
            self._ok({"audit": True}); return
        if "/" not in path or path.endswith("/"):
            ns = path.rstrip("/").split("/")[0]
            prefix = ns + "/"
            items = {k: v for k, v in state.items() if k.startswith(prefix)}
            total = len(items)
            if limit is not None:  # 显式分页
                keys = sorted(items.keys())
                page = keys[offset:offset + limit]
                items = {k: items[k] for k in page}
            self._ok({"list": items, "total": total,
                      "limit": limit, "offset": offset})
            return
        m = NS_RE.match(path)
        if not m:
            self._err(400, "bad key"); return
        ns, key = m.group(1), m.group(2)
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
        state[full] = {"version": ver, "value": value, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
        _audit("PUT", full, value)
        _mirror_result(full)          # v0.2 变更 1
        _notify(full)                 # v0.2 变更 3（异步）
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
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            body = {}
        if self.path.rstrip("/").endswith("subscribe"):
            topic = body.get("topic", "")
            callback = body.get("callback", "")
            unsub = body.get("unsub", False)
            if unsub:  # v0.2 变更 2：退订
                removed = [k for k, s in subs.items() if s["topic"] == topic and s["callback"] == callback]
                for k in removed:
                    del subs[k]
                self._ok({"unsubscribed": len(removed), "subscribed": len(subs)})
                return
            key = (topic, callback)
            if key not in subs:  # v0.2 变更 2：去重
                subs[key] = {"topic": topic, "callback": callback,
                             "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            self._ok({"subscribed": len(subs)})
        else:
            self._err(400, "use /subscribe")
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8792)
    ap.add_argument("--data-dir", default=None, help="数据目录（默认 ~/dsh-collab/token-monitor/blackboard，测试用独立目录隔离）")
    args = ap.parse_args()
    if args.data_dir:
        DATA_DIR = args.data_dir
    _load()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("blackboard-server v0.2 on :%d (token=%s) data=%s subs=%d"
          % (args.port, "on" if TOKEN else "off", DATA_DIR, len(subs)))
    srv.serve_forever()
