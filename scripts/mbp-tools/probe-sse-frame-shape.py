#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓一次**真实 SSE change 帧**，看插件到底收到什么（决定时效门该读哪个字段）。

背景（不许靠猜）：G27 时效门测试里出现 12/106「无法判龄」，且中位卡龄与 10-03 的实测对不上
⇒ 说明我读的字段层级可能不是插件实际看到的层级。⇒ 主动制造一次事件再观测（R035 延伸）。
"""
import json, os, threading, time, urllib.request, sys

TOK = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
H = {"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK}
BASE = "http://xingqiao.meetfunbp.com:8792"
frames = []
stop = threading.Event()


def reader():
    req = urllib.request.Request(BASE + "/events?prefix=notes/_selftest/", headers=H)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            cur = {}
            while not stop.is_set():
                line = r.readline()
                if not line:
                    break
                s = line.decode("utf-8", "ignore").rstrip("\n")
                if s.startswith("event:"):
                    cur["event"] = s.split(":", 1)[1].strip()
                elif s.startswith("id:"):
                    cur["id"] = s.split(":", 1)[1].strip()
                elif s.startswith("data:"):
                    cur["data"] = s.split(":", 1)[1].strip()
                elif s == "" and cur:
                    frames.append(dict(cur)); cur = {}
    except Exception as e:
        frames.append({"error": str(e)[:120]})


t = threading.Thread(target=reader, daemon=True)
t.start()
time.sleep(1.5)

key = "notes/_selftest/ageprobe-%d" % int(time.time())
now_ms = int(time.time() * 1000)
card = {"from": "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7", "to": "coordinator",
        "type": "note", "subject": "时效门探针（可忽略）", "body": "probe",
        "sent_at_epoch_ms": now_ms, "ts": now_ms // 1000, "reply_required": False}
req = urllib.request.Request(BASE + "/" + key, data=json.dumps(card, ensure_ascii=False).encode(),
                             method="PUT", headers=dict(H, **{"Content-Type": "application/json"}))
try:
    r = urllib.request.urlopen(req, timeout=15)
    print("PUT →", r.status, r.read().decode()[:120])
except Exception as e:
    print("PUT 失败:", e)

time.sleep(4)
stop.set()
time.sleep(0.3)

print("\n捕获帧数:", len(frames))
for f in frames:
    if f.get("event") == "change" or "data" in f:
        print("\n--- 帧 ---")
        print("  event =", f.get("event"), " id =", f.get("id"))
        d = f.get("data", "")
        try:
            obj = json.loads(d)
            print("  data 顶层键:", list(obj.keys()))
            print("  data =", json.dumps(obj, ensure_ascii=False)[:900])
        except Exception:
            print("  data(原样) =", d[:400])
