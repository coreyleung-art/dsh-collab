#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i9-monitor-sub.py v1.0 — i9 回报常驻监控（事件驱动订阅，替代一次性轮询脚本）

订阅黑板事件桥（:8803/events），过滤 tasks/i9/* 变化 → 记录回报到日志 + 黑板 notes。
零轮询（事件驱动），常驻后台。教训：之前用一次性 40min 轮询脚本漏了 CUDA 回报——事件驱动订阅不会漏。

用法:
  python3 i9-monitor-sub.py                      # 常驻（后台）
  python3 i9-monitor-sub.py --log /tmp/i9-monitor.log
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, time, datetime, urllib.request

EVENTS_URL = "http://127.0.0.1:8803/events"
BLACKBOARD = "http://127.0.0.1:8792"
WATCH_PREFIX = "tasks/i9/"   # 监控 i9 相关所有 key（queue/result/results）

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def _bb_put(path, data):
    import http.client, urllib.parse
    u = urllib.parse.urlparse(BLACKBOARD)
    body = json.dumps(data, ensure_ascii=False).encode()
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=8)
    conn.request("PUT", path, body=body, headers={"Content-Type":"application/json","Content-Length":str(len(body))})
    r = conn.getresponse(); raw = r.read().decode(); conn.close()
    return raw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="/tmp/i9-monitor.log")
    args = ap.parse_args()
    logf = open(args.log, "a", encoding="utf-8")
    def log(msg):
        line = "[%s] %s" % (_now(), msg)
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()
    log("i9 回报常驻监控启动（事件驱动订阅 %s，监控 %s）" % (EVENTS_URL, WATCH_PREFIX))
    while True:
        try:
            req = urllib.request.Request(EVENTS_URL, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log("已连接黑板事件桥，等待 i9 事件...")
            for raw_line in resp:
                line = raw_line.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    evt = json.loads(data)
                except json.JSONDecodeError:
                    continue
                key = evt.get("key", "")
                if key.startswith(WATCH_PREFIX):
                    log("🎯 i9 事件: %s" % key)
                    # 若是 result，记录回报摘要
                    if key.endswith("/result") or "/results/" in key:
                        val = evt.get("value", {})
                        log("   回报: task_id=%s ok=%s" % (val.get("task_id"), val.get("ok")))
                    # 黑板 notes 记录（可追溯）
                    try:
                        _bb_put("/notes/i9/monitor", {"ts":_now(), "from":"mac总线","type":"monitor",
                                                       "event_key":key, "value":str(evt.get("value"))[:200]})
                    except Exception:
                        pass
        except Exception as ex:
            log("连接中断: %s（5s 后重连）" % str(ex)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
