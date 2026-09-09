#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-mgr-events.py — 管理器 GUI 操作事件读取器(明鉴回合自查)
回合开始时跑: 读黑板 notes/mac-mini/manager-actions/ 自上次以来新事件, 高亮 important
用法:
  python3 bb-mgr-events.py --check    # 读新事件(标记 seen, 不重复)
  python3 bb-mgr-events.py --peek     # 只看不标 seen
  python3 bb-mgr-events.py --important # 只看重要事件
  python3 bb-mgr-events.py --clear    # 清 seen(重读全部)
状态: ~/.dsh/inbox/mgr-events.seen
"""
import argparse, json, os, sys, urllib.request, datetime

BB="http://127.0.0.1:8792"
PREFIX="notes/mac-mini/manager-actions/"
SEEN=os.path.expanduser("~/.dsh/inbox/mgr-events.seen")

def load_seen():
    try: return set(json.load(open(SEEN)))
    except Exception: return set()
def save_seen(s):
    os.makedirs(os.path.dirname(SEEN),exist_ok=True)
    json.dump(sorted(s),open(SEEN,"w"))

def list_keys():
    try:
        r=json.loads(urllib.request.urlopen(BB+"/"+PREFIX,timeout=5).read())
        d=r.get("list",r.get("value",{}))
        return sorted([k for k in d if k.startswith(PREFIX)])
    except Exception as e:
        return []

def read_key(k):
    try:
        r=json.loads(urllib.request.urlopen(BB+"/"+k,timeout=5).read())
        v=r.get("value",r)
        return v if isinstance(v,dict) else {"raw":str(v)[:100]}
    except Exception: return {"error":k}

def main():
    ap=argparse.ArgumentParser(description="管理器 GUI 操作事件读取器")
    ap.add_argument("--check",action="store_true")
    ap.add_argument("--peek",action="store_true")
    ap.add_argument("--important",action="store_true")
    ap.add_argument("--clear",action="store_true")
    args=ap.parse_args()
    if args.clear:
        save_seen(set()); print("seen 已清, 下次 --check 重读全部"); return
    seen=load_seen()
    keys=list_keys()
    newk=[k for k in keys if k not in seen]
    if not newk:
        print("(无新管理器事件)"); return
    imp_only=args.important
    n=0
    for k in newk:
        v=read_key(k)
        lv=v.get("level","info")
        if imp_only and lv!="important": continue
        n+=1
        mark="🔔" if lv=="important" else "·"
        print(f"{mark} {v.get('ts','')[:16]} [{v.get('event','')}] {v.get('detail','')[:90]}")
    if args.check and not args.peek:
        # 标 seen(重要+普通都标; peek 不标)
        save_seen(seen | set(newk))
    elif args.check:
        # check 默认标
        save_seen(seen | set(newk))
    if n: print(f"→ {n} 条新事件")

if __name__=="__main__":
    main()
