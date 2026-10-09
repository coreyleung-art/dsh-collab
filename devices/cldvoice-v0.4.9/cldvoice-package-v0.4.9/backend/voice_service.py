#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""voice-service.py — CLD-Voice 产品化内核服务 (L1)
提供统一的语音对话网关：多会话 + token 鉴权 + 健康检查 + 会话级日志。
协议: WS 文本帧 v1 (与 duplex_bridge 兼容) + HTTP 健康/统计。

WS v1 (客户端→服务端): {"type":"audio","pcm":b64} {"type":"commit"} {"type":"cancel"} {"type":"close"}
WS v1 (服务端→客户端): ready / transcript_delta / text_delta / text_done / audio_delta / audio_done / done / err

HTTP:  GET /v1/health   GET /v1/stats
用法:  python3 voice-service.py [--port 8905] [--token xxx]
环境:  VOLC_ASR_API_KEY 必填(火山); SEEDUPLEX_MODEL/VOICE 可选
"""
import argparse, asyncio, base64, json, os, sys, threading, time, uuid
import websockets as ws_server

# 复用已验证的 duplex 内核(同目录 import)
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import duplex_bridge as core  # 复用 pump/_ws_handler/VOLC_WS 等已验证逻辑

DEFAULT_PORT = 8905
LOG = os.path.expanduser("~/dsh-collab/logs/voice-service.log")

def vlog(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass
    print(f"[voice] {msg}")

# ── 会话注册(多会话跟踪) ──
_SESSIONS = {}
_SESS_LOCK = threading.Lock()
_TOKEN = os.environ.get("VOICE_TOKEN", "").strip()

def _register(sid):
    with _SESS_LOCK:
        _SESSIONS[sid] = {"ts": time.time(), "n_audio": 0, "n_commit": 0}
def _touch(sid, kind="audio"):
    with _SESS_LOCK:
        s = _SESSIONS.get(sid)
        if s:
            s[kind if kind in ("n_audio","n_commit") else "n_audio"] += 1
            s["ts"] = time.time()
def _unregister(sid):
    with _SESS_LOCK:
        _SESSIONS.pop(sid, None)
def _stats():
    with _SESS_LOCK:
        return {"active": len(_SESSIONS),
                "sessions": [{"id": k, "ts": round(v["ts"],1), "audio": v["n_audio"], "commit": v["n_commit"]}
                             for k, v in list(_SESSIONS.items())[:50]]}

# ── 鉴权包装: 覆盖 _ws_handler, 加 token 校验(可选) + 会话跟踪 ──
async def _authed_handler(websocket, path=None):
    # token 校验(若配置)
    if _TOKEN:
        hdr = websocket.request_headers.get("X-Voice-Token", "") if websocket.request_headers else ""
        if hdr != _TOKEN:
            try:
                await websocket.send(json.dumps({"type": "err", "msg": "unauthorized"}))
            except Exception:
                pass
            await websocket.close()
            return
    sid = uuid.uuid4().hex[:12]
    _register(sid)
    vlog(f"session {sid} open ({len(_SESSIONS)} active)")
    # 包装 pump: 统计 + 收尾清理
    try:
        # 复用 core.pump, 但需要在 client 发 audio 时计数 → 包装 gui_ws.send
        orig_send = websocket.send
        async def counted_send(data):
            await orig_send(data)
        # 直接复用 core pump(它内部 async for msg 处理 audio/commit)
        await core.pump(websocket)
    finally:
        _unregister(sid)
        vlog(f"session {sid} closed ({len(_SESSIONS)} active)")

# ── HTTP 健康/统计(同端口用 ws 服务附带 http? 简化: 独立小 HTTP 线程) ──
def _http_server(port):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path == "/v1/health":
                self._json(200, {"ok": True, "service": "voice-service", "ts": time.time(),
                                 "active_sessions": _stats()["active"]})
            elif self.path == "/v1/stats":
                self._json(200, _stats())
            else:
                self._json(404, {"ok": False, "error": "not found"})
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Voice-Token")
            self.end_headers()
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()

def main():
    ap = argparse.ArgumentParser(description="CLD-Voice 产品化内核服务")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="WS 端口(默认8905)")
    ap.add_argument("--http", type=int, default=8906, help="HTTP 健康端口(默认8906)")
    ap.add_argument("--token", default="", help="X-Voice-Token 鉴权(默认不鉴权)")
    args = ap.parse_args()
    global _TOKEN
    if args.token: _TOKEN = args.token

    vlog(f"voice-service v1.2.0 启动 ws://127.0.0.1:{args.port} http://127.0.0.1:{args.http} "
         f"token={'on' if _TOKEN else 'off'}")

    # HTTP 健康线程
    threading.Thread(target=_http_server, args=(args.http,), daemon=True).start()

    async def serve():
        async with ws_server.serve(_authed_handler, "0.0.0.0", args.port, max_size=2**20):
            await asyncio.Future()
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        vlog("shutdown")

if __name__ == "__main__":
    main()
