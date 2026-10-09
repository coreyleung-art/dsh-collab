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

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, urllib.request, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-mgr-events.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
