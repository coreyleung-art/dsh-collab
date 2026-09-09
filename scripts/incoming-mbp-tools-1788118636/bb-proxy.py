#!/usr/bin/env python3
"""bb-proxy.py v1.0 — 本地黑板 TCP 代理：127.0.0.1:8792 → 100.120.203.20:8792
dsh-tools 硬编码连本机 8792；MBP 黑板在 mac-mini，故需转发。"""
import socket, threading

REMOTE = ("100.120.203.20", 8792)

def pipe(src, dst):
    try:
        while True:
            d = src.recv(65536)
            if not d: break
            dst.sendall(d)
    except Exception: pass
    finally:
        for s in (src, dst):
            try: s.close()
            except: pass

def handle(c):
    try:
        u = socket.create_connection(REMOTE, timeout=10)
    except Exception:
        c.close(); return
    threading.Thread(target=pipe, args=(c, u), daemon=True).start()
    pipe(u, c)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8792)); s.listen(64)
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
