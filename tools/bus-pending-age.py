#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bus-pending-age —「队列待投递项是否被标超时」的机械核验门（★ 只读）。

★ 立据（2026-10-12 · v7 M4③ 实测）：
  ★ `token-monitor/event-bus/send-instructions/` 实测 **122 个 `.json`**，
    其中 **`sent != true` = 111 条**（★ 分子 111 / 分母 122）。
  ★★ 而**最老的一条从 `2026-08-20` 起**，**消费侧停滞 40.9 天** ——
    ★★★ **却【无任何超时标记】**：`expired` 计数 = **0 / 111**。
  ★ 且 **122/122 收件人是同一个会话**（`session-fa1f9150-…`）。
  ★★ ⇒ 故本门查：**pending 项里，有多少条【已超时却未被标出】**。

★★ 【本门只读】—— **不改 event-bus 的任何文件**；它只报「该有多少条被标超时」。

三态：目录不存在 ⇒ 「不可判」；目录存在但 0 文件 ⇒ 「不适用」；有文件 ⇒ 给出分母/分子/最老项。
"""
import io
import os
import re
import sys
import json
import glob
import argparse
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(ROOT, "token-monitor", "event-bus", "send-instructions")


def parse_ts(s):
    if not s:
        return None
    try:
        t = datetime.datetime.fromisoformat(str(s))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
        return t
    except Exception:
        return None


def scan(bus_dir=None, ttl_hours=24.0):
    d = bus_dir or BUS
    if not os.path.isdir(d):
        return None
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    now = datetime.datetime.now().astimezone()
    rows = []
    for f in files:
        try:
            o = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            rows.append({"file": os.path.basename(f), "unreadable": True})
            continue
        ts = parse_ts(o.get("ts"))
        age_h = ((now - ts).total_seconds() / 3600.0) if ts else None
        rows.append({
            "file": os.path.basename(f),
            "topic": o.get("topic"),
            "agent": o.get("agent"),
            "sent": o.get("sent"),
            "sent_at": o.get("sent_at"),
            "expired": o.get("expired"),
            "ts": o.get("ts"),
            "age_hours": round(age_h, 1) if age_h is not None else None,
            # ★ 判据：pending 且 龄 > TTL
            # ★★ 2026-10-13 修（ext 第三轮 F-10）：原 `age_h is None ⇒ False` ⇒
            #   ★★ **【不可判】被当成【不超时】**（★ 三态塔缩）。
            #   ★ 现拆两栏：`should_be_expired`（★ 可判时）· `undecidable`（★ 无龄）。
            "should_be_expired": (o.get("sent") is not True) and (age_h is not None and age_h > ttl_hours),
            "undecidable": (o.get("sent") is not True) and (age_h is None),
            "marked_expired": o.get("expired") is True,
        })
    return {"dir": d, "now": now.isoformat(), "rows": rows, "ttl_hours": ttl_hours}


def summarize(res):
    # ★★ 2026-10-13（ext F-10）：三态报告 —★ 【不可判】单列，不归入「不超时」
    _und = [r for r in res["rows"] if r.get("undecidable")]
    if _und:
        res["undecidable_count"] = len(_und)
        res["undecidable_keys"] = sorted({k for r in _und for k in ("sent_at", "ts", "age_hours") if r.get(k) is None})

    rows = res["rows"]
    total = len(rows)
    pending = [r for r in rows if r.get("sent") is not True]
    should = [r for r in pending if r.get("should_be_expired")]
    marked = [r for r in pending if r.get("marked_expired")]
    ages = [r["age_hours"] for r in pending if r.get("age_hours") is not None]
    _out = {
        "total": total,
        "pending": len(pending),
        "should_be_expired": len(should),
        "marked_expired": len(marked),
        "oldest_pending_hours": max(ages) if ages else None,
        "oldest_pending_days": round(max(ages) / 24.0, 1) if ages else None,
        "ttl_hours": res["ttl_hours"],
        "now": res["now"],
    }
    # ★★ 2026-10-13 再修（ext 第四轮 F-10）：上一版**算了却丢**（★ 死码）—★
    #   ★ 原实现在 :71/:79-82 算了 `undecidable`，★★ 而本函数返回「字面量」只列七项 ⇒ **丢掉**。
    #   ★ 现：把它真接进返回值（★ 文本与 JSON 都会出现）。
    _und = [r for r in rows if r.get("undecidable")]
    _out["undecidable_count"] = len(_und)
    _out["undecidable_keys"] = sorted({k for r in _und for k in ("sent_at", "ts", "age_hours") if r.get(k) is None})
    _out["undecidable_ids"] = [r.get("file") or r.get("id") for r in _und][:20]
    return _out



def selftest():
    ok = tot = 0
    import tempfile
    # ★ 正控：造一个【超时且未标】的项 ⇒ should_be_expired 必须 True
    tot += 1
    tmp = tempfile.mkdtemp(prefix="bus-age-")
    old = (datetime.datetime.now().astimezone() - datetime.timedelta(days=30)).isoformat()
    io.open(os.path.join(tmp, "a.json"), "w", encoding="utf-8").write(
        json.dumps({"sent": False, "ts": old, "topic": "t"}))
    r = scan(tmp, ttl_hours=24.0)
    s = summarize(r)
    if s["should_be_expired"] == 1 and s["marked_expired"] == 0:
        ok += 1
        print("  ✅ 正控：30 天前 pending 未标 ⇒ should_be_expired=1 · marked=0（★ 可红）")
    else:
        print("  ❌ 正控：超时未标项未判出（%s）" % s)
    # ★ 负控：【刚入队】的项不得判超时
    tot += 1
    fresh = datetime.datetime.now().astimezone().isoformat()
    io.open(os.path.join(tmp, "b.json"), "w", encoding="utf-8").write(
        json.dumps({"sent": False, "ts": fresh, "topic": "t"}))
    r2 = scan(tmp, ttl_hours=24.0)
    s2 = summarize(r2)
    if s2["should_be_expired"] == 1:      # ★ 仍只有 a 那一条
        ok += 1
        print("  ✅ 负控：刚入队项未计超时（★ 仍只有旧的 1 条）")
    else:
        print("  ❌ 负控：刚入队项被误计超时（%s）" % s2)
    # ★ 负控：已 sent 的项不计 pending
    tot += 1
    io.open(os.path.join(tmp, "c.json"), "w", encoding="utf-8").write(
        json.dumps({"sent": True, "sent_at": fresh, "ts": old, "topic": "t"}))
    r3 = scan(tmp, ttl_hours=24.0)
    s3 = summarize(r3)
    if s3["pending"] == 2:                 # ★ a + b，不含 c
        ok += 1
        print("  ✅ 负控：已 sent 项不计入 pending（★ pending=%d）" % s3["pending"])
    else:
        print("  ❌ 负控：sent 项被计入 pending（%s）" % s3)
    # ★ 三态：目录不存在 ⇒ None
    tot += 1
    if scan("/tmp/__no_such_bus_dir__") is None:
        ok += 1
        print("  ✅ 负控：目录不存在 ⇒ None（★ 调用方报「不可判」）")
    else:
        print("  ❌ 负控：不存在的目录竟返回结果")
    # ★ 三态：空目录 ⇒ 空结果（★ 调用方报「不适用」）
    tot += 1
    empty = tempfile.mkdtemp(prefix="bus-empty-")
    s5 = summarize(scan(empty, 24.0))
    if s5["total"] == 0:
        ok += 1
        print("  ✅ 正控：空目录 ⇒ total=0（★ 调用方报「不适用」，★ 不是通过）")
    else:
        print("  ❌ 正控：空目录竟有项")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(empty, ignore_errors=True)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--ttl-hours", type=float, default=24.0, help="超时阈值（默认 24h）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("bus-pending-age 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    res = scan(a.dir, a.ttl_hours)
    if res is None:
        print("★ 目录不可读 ⇒ 【不可判】（★ 不冒充通过）: %s" % (a.dir or BUS))
        return 2
    s = summarize(res)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0
    print("== bus-pending-age 1.0.0 ==")
    print("  目录：%s" % os.path.relpath(res["dir"], ROOT))
    print("  时刻：%s · TTL：%sh" % (s["now"][:19], s["ttl_hours"]))
    if s["total"] == 0:
        print("  ★ 目录存在但 0 文件 ⇒ 【不适用】（★ 不是通过）")
        return 0
    print()
    print("  ★ 分母 total            = %d" % s["total"])
    print("  ★ 分子 pending          = %d" % s["pending"])
    print("  ★★ 应标未标 should_exp  = %d" % s["should_be_expired"])
    print("  ★★ 已标 expired         = %d" % s["marked_expired"])
    if s["oldest_pending_days"] is not None:
        print("  ★★ 最老 pending         = %.1f 天（%.0f h）" % (s["oldest_pending_days"], s["oldest_pending_hours"]))
    print()
    if s["should_be_expired"] > 0 and s["marked_expired"] == 0:
        print("  ❌ **%d 条 pending 已超 TTL 而【无一条被标 expired】**" % s["should_be_expired"])
        print("     ★ 依 M4③ 判据「expired 告警」⇒ **不成立**")
        return 1
    if s["marked_expired"] > 0:
        print("  ✅ 已标 expired 共 %d 条" % s["marked_expired"])
        return 0
    print("  ✅ 无超时项")
    return 0


if __name__ == "__main__":
    sys.exit(main())
