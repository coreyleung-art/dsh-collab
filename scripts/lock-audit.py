#!/usr/bin/env python3
"""
lock-audit v1 —— 锁审计自动化（残留锁/异常锁检测）

作用：agent_light 全量锁检查的自动化版本——检测异常残留锁（进程中断未释放），
     并对照登记表快照判断「该解锁未解锁」。前任 b3778a1e 遗留锁教训的固化。

用法：
  python3 lock-audit.py              # 全量审计（默认）
  python3 lock-audit.py --json       # JSON 输出（供外部告警）
  python3 lock-audit.py --warn-only  # 只输出异常

纪律：只读审计，不写文件、不广播（J34）；秒级时间观可随时跑。
"""
import json
import os
import sys
import time
from datetime import datetime

def load_bus():
    path = os.path.expanduser("~/.dsh/agent-bus.json")
    with open(path) as f:
        return json.load(f)

def audit():
    bus = load_bus()
    locks = bus.get("locks", [])
    light_log = bus.get("lightLog", [])

    issues = []

    # 1. 当前持有锁检查
    for lk in locks:
        holder = lk.get("holder", "?")
        resource = lk.get("resource", "?")
        acquired = lk.get("acquiredAt", 0)
        age_h = (time.time() - acquired / 1000) / 3600 if acquired else 0
        note = lk.get("note", "")
        # 持锁超 24h = 疑似残留（正常任务锁秒级~分钟级）
        if age_h > 24:
            issues.append({
                "type": "stale_lock",
                "severity": "high",
                "resource": resource,
                "holder": holder,
                "age_hours": round(age_h, 1),
                "note": note[:80],
            })

    # 2. 锁日志异常模式（acquire 无对应 release）
    acquires = {}
    releases = set()
    for ev in light_log:
        kind = ev.get("kind", "")
        res = ev.get("resource", "")
        holder = ev.get("holder", "")
        if kind == "acquire":
            acquires.setdefault(res, []).append(holder)
        elif kind == "release":
            releases.add(res)
    for res, holders in acquires.items():
        if res not in releases:
            # 有 acquire 无 release（日志窗口内未释放）
            issues.append({
                "type": "unreleased",
                "severity": "medium",
                "resource": res,
                "holders": holders[-3:],
                "note": "最近日志窗口内 acquire 未见 release",
            })

    return locks, issues

def main():
    as_json = "--json" in sys.argv
    warn_only = "--warn-only" in sys.argv

    locks, issues = audit()

    if as_json:
        print(json.dumps({"locks": len(locks), "issues": issues}, ensure_ascii=False, indent=2))
        return

    now = datetime.now().strftime("%m-%d %H:%M")
    print(f"[lock-audit] {now} · 当前持有锁 {len(locks)} 把")
    for lk in locks:
        acquired = lk.get("acquiredAt", 0)
        age = (time.time() - acquired / 1000) / 3600 if acquired else 0
        print(f"  - {lk.get('resource','?')} | {lk.get('holder','?')} | 已持 {round(age,2)}h | {str(lk.get('note',''))[:50]}")

    if issues:
        print(f"\n[lock-audit] ⚠️ 发现 {len(issues)} 项异常:")
        for it in issues:
            print(f"  [{it['severity']}] {it['type']}: {it['resource']} (holder={it.get('holder','?')}, age={it.get('age_hours','-')}h)")
    elif warn_only:
        print("[lock-audit] ✅ 无异常（--warn-only 无输出则正常）")
    else:
        print("\n[lock-audit] ✅ 锁状态健康，无异常残留")

if __name__ == "__main__":
    main()
