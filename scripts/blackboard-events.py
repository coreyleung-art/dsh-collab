#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blackboard-events.py v1.0 — 黑板事件桥：SUBSCRIBE 回调 → SSE 广播

黑板（blackboard-server 8792）的 SUBSCRIBE 是 HTTP 回调（黑板变更 → POST 到 callback）。
本桥把它转成 SSE 事件流，让智能体用 sse-sub 框架订阅黑板事件（事件驱动，零轮询）。

架构:
  黑板 8792（KV + SUBSCRIBE）
    ↓ 变更 → POST /cb（本桥）
  本桥（:8803）
    ↓ SSE 广播
  智能体 sse-sub（订阅 http://127.0.0.1:8803/events）

用法:
  python3 blackboard-events.py --port 8803
  智能体订阅: sse-sub --url http://127.0.0.1:8803/events --event 'tasks/*' 'handle=...'

事件格式（SSE data）:
  {"key":"tasks/i9/queue/123","value":{...},"version":1,"ts":"..."}
"""
import argparse, json, queue, threading, time, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# SSE 广播队列：黑板回调 → 事件 → 所有 SSE 客户端
_broadcast_q = queue.Queue()
_sse_clients = set()  # 客户端队列集合（每个客户端一个 queue.Queue）

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def broadcast(key, value, version):
    """黑板回调到达 → 广播事件给所有 SSE 客户端"""
    evt = json.dumps({"key": key, "value": value, "version": version, "ts": _now()}, ensure_ascii=False)
    for cq in list(_sse_clients):
        try:
            cq.put(evt)
        except Exception:
            pass

class H(BaseHTTPRequestHandler):
    # 黑板 SUBSCRIBE 回调入口：黑板变更时 POST 到这里
    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            data = {}
        key = data.get("key", "?")
        value = data.get("value")
        version = data.get("version")
        broadcast(key, value, version)
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    # SSE 端点：智能体 sse-sub 订阅
    def do_GET(self):
        if self.path.startswith("/events"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            cq = queue.Queue()
            _sse_clients.add(cq)
            try:
                # 初始心跳
                self.wfile.write(b"event: hello\ndata: {\"bridge\":\"blackboard-events\",\"ts\":\"%s\"}\n\n" % _now().encode())
                self.wfile.flush()
                while True:
                    try:
                        evt = cq.get(timeout=15)
                        self.wfile.write(b"event: change\ndata: " + evt.encode("utf-8") + b"\n\n")
                        self.wfile.flush()
                    except queue.Empty:
                        # 心跳保活
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                _sse_clients.discard(cq)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
    def log_message(self, *a):
        pass

def main():
    ap = argparse.ArgumentParser(description="黑板事件桥：SUBSCRIBE 回调 → SSE 广播")
    ap.add_argument("--port", type=int, default=8803)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("黑板事件桥 :%d（黑板 SUBSCRIBE 回调入口 /cb → SSE /events）" % args.port)
    print("智能体订阅: sse-sub --url http://127.0.0.1:%d/events --event 'tasks/*'" % args.port)
    srv.serve_forever()

if __name__ == "__main__":
    main()
