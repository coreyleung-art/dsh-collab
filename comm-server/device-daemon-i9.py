#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""device-daemon-i9.py — i9(Windows) 收件守护（node-kit 精简版 v1）
治本: i9 直接订阅服务器 bus SSE，收到 target=i9 消息 → 转写黑板 notes/i9/ 域
      → i9-coordinator 读域处理。不再依赖 mac-mini 代收转发。

配置(env):
  DSH_NODE_ID  必填=i9 (无默认, 部署门 G-D2)
  SERVER_BUS   默认 http://106.53.214.108:8791
  LOCAL_BB     默认 http://100.120.203.20:8792  (i9 经 Tailscale 到 mac-mini 黑板)
  BLACKBOARD_TOKEN 默认 bb-token-20260829-macmini

用法:
  python device-daemon-i9.py              # SSE 常驻
  python device-daemon-i9.py --once       # 单次测试
纯 stdlib 跨平台(Windows 可用)。
"""
import argparse, json, os, sys, time, datetime, urllib.request

def require_env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        sys.stderr.write(f"[i9d] 缺少 env {name} (部署门 G-D2)\n"); sys.exit(2)
    return v

NODE = require_env("DSH_NODE_ID")
SERVER_BUS = os.environ.get("SERVER_BUS", "http://106.53.214.108:8791")
LOCAL_BB = os.environ.get("LOCAL_BB", "http://100.120.203.20:8792")
BB_TOKEN = os.environ.get("BLACKBOARD_TOKEN", "bb-token-20260829-macmini")
LOG = os.path.expanduser("~/.dsh/logs/device-daemon-i9.log")

def log(m):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    try:
        import os as _o
        _o.makedirs(_o.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    except Exception: pass

def http_get_json(url, headers=None, timeout=10):
    h = headers or {}
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "errmsg": str(e)[:60]}

def bb_put(key, value):
    body = json.dumps(value, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{LOCAL_BB}/{key.lstrip('/')}", data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "X-Blackboard-Token": BB_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=8) as r: return json.loads(r.read().decode())
    except Exception as e:
        log(f"黑板写失败 {key}: {str(e)[:60]}"); return None

def reply_task(tid, ok, result=None, error=None, stage="done"):
    """回执。G-C31 两级确认: 守护默认 stage=delivered(送达声明) 防假闭环"""
    body = json.dumps({"task_id": tid, "ok": ok, "result": result, "error": error,
                       "stage": stage}).encode()
    req = urllib.request.Request(f"{SERVER_BUS}/bus/reply", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r: return True
    except Exception: return False

def _source_ok(frm):
    """信源校验(Lean4 防 spoof)：from 须可信设备/角色"""
    if not frm: return False
    if frm.startswith("bus:"): frm = frm[4:]
    if frm in ("mac-mini", "mbp", "i9", "server", "server:coordinator"): return True
    if ":" in frm: return frm.split(":", 1)[0] in ("mac-mini", "mbp", "i9")
    return frm in ("星桥", "明鉴", "司库", "coordinator", "i9")  # 已知角色简表

def dispatch(task):
    """收信 → 转写黑板 notes/i9/ 域（i9-coordinator 读域处理）
    Lean4 防 spoof：不可信信源拒转写"""
    tid = task.get("task_id", "")
    payload = task.get("payload") or {}
    action = task.get("action", "msg")
    frm = task.get("from") or payload.get("from") or ""
    if not _source_ok(frm):
        reply_task(tid, False, error=f"untrusted-source:{str(frm)[:30]}")
        log(f"⛔ 拒路由 不可信信源 from={str(frm)[:30]} (task {tid[:8]})")
        return None
    text = payload.get("text") or payload.get("msg") or json.dumps(payload, ensure_ascii=False)[:400]
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    key = f"notes/i9/bus-{action}-{tid[:8]}"
    val = {"content": f"[bus:{action}] {text}", "from": f"bus:{task.get('from','?')}",
           "key": key, "to": payload.get("to") or "i9", "ts": ts,
           "type": "bus-envelope", "task_id": tid,
           "_bus": {"task_id": tid, "from": task.get("from"), "action": action, "received_by": "i9-daemon"}}
    if bb_put(key, val):
        reply_task(tid, True, result={"note": f"i9 delivered, see {key}"}, stage="delivered")
        log(f"收信→黑板 {key} (task {tid[:8]})")
    else:
        reply_task(tid, False, error="bb-write-failed")
        log(f"⚠️ 黑板写失败 (task {tid[:8]})")

def sse_loop():
    url = f"{SERVER_BUS}/bus/events?node={NODE}"
    while True:
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log(f"SSE 已连接 {url} (推送模式)")
            buf = ""
            while True:
                chunk = resp.read(1)
                if not chunk: raise RuntimeError("SSE 断开")
                buf += chunk.decode("utf-8", "ignore")
                while "\n\n" in buf:
                    event, buf = buf.split("\n\n", 1)
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                ev = json.loads(line[6:])
                                if ev.get("type") == "new-task" and (ev.get("target") in (NODE, "any")):
                                    log(f"收到推送 {ev.get('action')} (task {str(ev.get('task_id'))[:8]})")
                                    dispatch({"task_id": ev.get("task_id"), "from": ev.get("from"),
                                              "action": ev.get("action"), "payload": ev.get("payload")})
                            except Exception as e:
                                log(f"解析失败: {str(e)[:50]}")
        except Exception as e:
            log(f"SSE 异常: {str(e)[:70]} —— 3s 重连")
        time.sleep(3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    log(f"i9 守护启动 node={NODE} server={SERVER_BUS} bb={LOCAL_BB}")
    if args.once:
        # 单测：订阅一次看能否连服务器
        print("connectivity check...")
        r = http_get_json(f"{SERVER_BUS}/bus/status")
        print("bus status:", "ok" if r.get("ok") else r.get("errmsg", "?"))
        return
    sse_loop()

if __name__ == "__main__":
    main()
