#!/usr/bin/env python3
"""i9 秒级轮询 v2 — 监控 tasks/i9/result + tasks/i9/cmd + notes/i9/*（i9 消息键）
v2 修复：之前只查 result/cmd，漏了 notes/i9（i9 发消息的键）——这就是『秒级还收不到』的根因
"""
import json, sys, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
INTERVAL = 2

def get(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def main():
    last_result = None
    seen_notes = set()
    print("[%s] i9 秒级轮询 v2 启动（result+cmd+notes/i9 三路监控）" % datetime.datetime.now().strftime("%H:%M:%S"), flush=True)
    while True:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        # 1. 任务回报
        r = get("/tasks/i9/result")
        v = r.get("value") or {}
        tid, ts = v.get("task_id"), v.get("ts","")
        if tid and (tid, ts) != last_result:
            last_result = (tid, ts)
            print("[%s] 🔄 回报: %s ok=%s | %s" % (now, tid, v.get("ok"), ts[:19]), flush=True)
            out = str(v.get("output",""))[:150]
            if out: print("    ", out, flush=True)
        # 2. 任务卡
        c = get("/tasks/i9/cmd")
        if "value" in c and c["value"]:
            print("[%s] 📥 任务卡: %s" % (now, c["value"].get("task_id","?")), flush=True)
        # 3. notes/i9（i9 消息）——v2 新增
        n = get("/notes/i9/?limit=50")
        for k, item in (n.get("list") or {}).items():
            if k not in seen_notes:
                seen_notes.add(k)
                val = item.get("value", {})
                if val.get("from") == "i9":
                    print("[%s] 💬 i9消息: %s | %s" % (now, k.split("/")[-1], str(val.get("subject") or val.get("type",""))[:60]), flush=True)
                    print("    ", json.dumps(val.get("content",""), ensure_ascii=False)[:200], flush=True)
                elif val.get("from") == "coordinator":
                    pass  # 自己写的忽略
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
