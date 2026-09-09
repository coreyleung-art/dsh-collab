#!/usr/bin/env python3
"""comm-server 同步层 v1 · 下行镜像（中枢 → mac-mini 读侧）
订阅中枢 SSE 8803，把 i9/MBP 写入中枢的新键镜像到本机黑板（notes/i9/, notes/mbp/, notes/collab/ 相关）
本机写中枢的键不回灌（防回声：seen 记录 + from 过滤）
"""
import json, os, sys, time, subprocess, urllib.request

CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
CENTRAL_SSE = os.environ.get("CENTRAL_SSE", "http://xingqiao.meetfunbp.com:8803/events")
LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
# 下行镜像域：i9/MBP 写中枢的键
from comm_domains import down_domains_as_prefixes as _down, self_domains_as_prefixes as _self
DOWN_PREFIXES = _down()  # 单源: comm-domains.py
# 本机自己推上去的键不镜像回（防循环）
SELF_PREFIXES = _self()  # 单源: comm-domains.py
SEEN_FILE = os.path.expanduser("~/.dsh/comm-sync-down-seen.json")

def log(m):
    print(f"[sync-down] {time.strftime('%H:%M:%S')} {m}", flush=True)

def load_seen():
    try: return set(json.load(open(SEEN_FILE)))
    except: return set()

def save_seen(s):
    try: json.dump(sorted(s)[-5000:], open(SEEN_FILE, "w"))
    except: pass

def bb_put_local(url, val):
    try:
        body = json.dumps(val).encode()
        req = urllib.request.Request(url, data=body, method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception as e:
        log(f"镜像失败 {url}: {str(e)[:50]}")
        return False

def sync_down_once():
    seen = load_seen()
    mirrored = 0
    # 全库 list 中枢（只取 i9/mbp 域新键）
    try:
        with urllib.request.urlopen(CENTRAL_BB + "/notes", timeout=15) as r:
            d = json.loads(r.read())
    except Exception as e:
        log(f"中枢 list 失败: {e}")
        return 0
    lst = d.get("list", {}) if isinstance(d, dict) else {}
    for key, meta in lst.items():
        if not isinstance(meta, dict): continue
        if not any(key.startswith(p) for p in DOWN_PREFIXES): continue
        if any(key.startswith(p) for p in SELF_PREFIXES): continue
        if key in seen: continue
        seen.add(key)
        try:
            with urllib.request.urlopen(CENTRAL_BB + "/" + key, timeout=6) as r:
                v = json.loads(r.read())
            val = v.get("value", {})
            if val:
                # 标注来源中枢，镜像本机
                val2 = dict(val)
                val2["_via"] = "comm-central"
                if bb_put_local(LOCAL_BB + "/" + key, val2):
                    mirrored += 1
                    if mirrored <= 5: log(f"镜像 {key}")
        except Exception as e:
            log(f"键 {key} 异常: {str(e)[:40]}")
    save_seen(seen)
    log(f"下行同步 {mirrored} 键（累计 {len(seen)}）")
    return mirrored

def watch():
    log(f"watch 启动: {CENTRAL_SSE}")
    while True:
        try:
            req = urllib.request.Request(CENTRAL_SSE)
            with urllib.request.urlopen(req, timeout=60) as r:
                for raw in r:
                    line = raw.decode(errors="ignore").strip()
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[6:])
                            key = ev.get("key", "")
                            if any(key.startswith(p) for p in DOWN_PREFIXES) and not any(key.startswith(p) for p in SELF_PREFIXES):
                                sync_down_once()
                        except: pass
        except Exception as e:
            log(f"SSE 断: {str(e)[:50]}，3s 重连")
            time.sleep(3)

if __name__ == "__main__":
    if "--once" in sys.argv:
        sync_down_once()
    else:
        sync_down_once()
        watch()
