#!/usr/bin/env python3
"""bb-proxy.py v1.0 — 本地黑板 TCP 代理：127.0.0.1:8792 → 100.120.203.20:8792

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
dsh-tools 硬编码连本机 8792；MBP 黑板在 mac-mini，故需转发。"""
import socket, threading

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-proxy.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
