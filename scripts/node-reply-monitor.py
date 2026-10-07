#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-reply-monitor.py — 中枢侧节点回复常驻监听
监听黑板 notes/{mbp,i9}/reply-* 和 dialog-reply 等节点回复键，
收到新回复即打印 + 写日志（中枢会话可感知）。

用法:
  python3 node-reply-monitor.py              # 常驻监听（默认 3s 轮询）
  python3 node-reply-monitor.py --once       # 单次检查

配合:
  · 端侧 node-bridge outbox（节点写 outbox 即发信）
  · 黑板 SSE 事件桥 :8803（可选事件驱动，更快）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
NODES = ["mbp", "i9"]
# 监听键模式：节点回复通常以 reply / dialog-reply / report 开头
KEY_PATTERNS = ("reply", "dialog-reply", "report-in", "outbox-test-reply")
SEEN = set()  # 已处理键去重

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get(path):
    try:
        req = urllib.request.Request(BB + path)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def scan():
    # 逐键 GET：绕开命名空间列被 genebank 刷屏的问题
    # 已知回复键：dialog-reply、dialog-reply2、report-in、reply-* 等
    for node in NODES:
        # 先看该节点是否有最新回复（GET 具体键）
        for pattern in KEY_PATTERNS:
            key = "notes/%s/%s" % (node, pattern)
            d = get("/" + key)
            if d and "value" in d:
                if key not in SEEN:
                    SEEN.add(key)
                    val = d.get("value") or {}
                    print("[%s] 📩 节点回复 %s" % (now(), key), flush=True)
                    print("    from=%s subject=%s" % (val.get("from"), val.get("subject")), flush=True)
                    content = str(val.get("content") or "")[:120]
                    if content:
                        print("    content=%s" % content, flush=True)
                    with open("/tmp/node-reply-monitor.log", "a") as f:
                        f.write("%s %s %s\n" % (now(), key, json.dumps(val, ensure_ascii=False)[:300]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=3)
    args = ap.parse_args()
    print("[%s] node-reply-monitor 启动（监听 %s 节点回复，%ss 轮询）" % (now(), ",".join(NODES), args.interval), flush=True)
    while True:
        try:
            scan()
        except Exception as ex:
            print("[%s] scan error: %s" % (now(), str(ex)[:80]), flush=True)
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
