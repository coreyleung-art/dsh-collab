#!/usr/bin/env python3
"""comm-server 同步层 v1 · 上行推送（mac-mini 本机 → 中枢）
订阅本机黑板 SSE 8803，把关键域新键推送到中枢 xingqiao.meetfunbp.com
触发：launchd 常驻（com.dsh.comm-sync-up）或手动 python3 sync-to-central.py --once
"""
import json, os, sys, time, subprocess, urllib.request

LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
LOCAL_SSE = os.environ.get("LOCAL_SSE", "http://127.0.0.1:8803/events")
CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
# 上行关键域（跨设备相关；纯本地域不同步避免噪音）
from comm_domains import up_domains_as_prefixes as _up
from comm_domains import collab_broadcast_ok  # v1.1 §3.1 结构门: collab 上行须广播语义
UP_PREFIXES = _up()  # 单源: comm-domains.py
SEEN_FILE = os.path.expanduser("~/.dsh/comm-sync-seen.json")

def log(m):
    print(f"[sync-up] {time.strftime('%H:%M:%S')} {m}", flush=True)

def load_seen():
    try: return set(json.load(open(SEEN_FILE)))
    except: return set()

def save_seen(s):
    try: json.dump(sorted(s)[-5000:], open(SEEN_FILE, "w"))
    except: pass

def bb_put(url, val):
    try:
        body = json.dumps(val).encode()
        req = urllib.request.Request(url, data=body, method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception as e:
        log(f"推送失败 {url}: {str(e)[:60]}")
        return False

def sync_once():
    seen = load_seen()
    pushed = 0
    # list API 忽略前缀返回全库 → 全库遍历按 key 实际前缀过滤
    try:
        with urllib.request.urlopen(LOCAL_BB + "/notes", timeout=15) as r:
            d = json.loads(r.read())
    except Exception as e:
        log(f"本地 list 失败: {e}")
        return 0
    lst = d.get("list", {}) if isinstance(d, dict) else {}
    for key, meta in lst.items():
        if not isinstance(meta, dict): continue
        if not any(key.startswith(p) for p in UP_PREFIXES): continue
        if key in seen: continue
        seen.add(key)
        # 读本地值 → 推中枢
        try:
            with urllib.request.urlopen(LOCAL_BB + "/" + key, timeout=8) as r:
                v = json.loads(r.read())
            val = v.get("value", {})
            # v1.1 结构门 (G-C39 · §3.1): collab 卡无广播语义 = 设备内消息, 不上行中枢
            # (防 i9/mbp 读到本机角色治理/回执内容; 连直写绕过 bb-gate 的也在此拦)
            if key.startswith("notes/collab/") and not collab_broadcast_ok(val):
                log(f"🚫 collab 无广播语义(设备内, 不上行): {key}")
                continue
            if val and bb_put(CENTRAL_BB + "/" + key, val):
                pushed += 1
                if pushed <= 5 or pushed % 20 == 0:
                    log(f"推送 {key}")
        except Exception as e:
            log(f"键 {key} 异常: {str(e)[:50]}")
    save_seen(seen)
    log(f"本次同步 {pushed} 键（累计 seen {len(seen)}）")
    return pushed

def watch():
    """SSE 长连：实时推送新键"""
    import urllib.request as ur
    log(f"watch 启动: {LOCAL_SSE}")
    buf = ""
    while True:
        try:
            req = ur.Request(LOCAL_SSE)
            with ur.urlopen(req, timeout=60) as r:
                for raw in r:
                    line = raw.decode(errors="ignore").strip()
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[6:])
                            key = ev.get("key", "")
                            if any(key.startswith(p) for p in UP_PREFIXES):
                                sync_once()
                        except: pass
        except Exception as e:
            log(f"SSE 断: {str(e)[:60]}，3s 重连")
            time.sleep(3)

if __name__ == "__main__":
    if "--once" in sys.argv:
        sync_once()
    else:
        # 启动先全量同步一次，再 watch
        sync_once()
        watch()
