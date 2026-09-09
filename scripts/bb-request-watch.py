#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-request-watch.py — 请求监控（request 水位：版本变化检测）

用户指示（2026-08-24）：杜绝「黑板有信息看不到」（i9 请求遗漏 ×3 教训）。
原理：notes/<node>/* 的 request 类 key 每次更新 version+1——记住已消费 version（水位），
版本变化 = 新请求/更新 → 自动报告/触发处理。

用法：
  python3 bb-request-watch.py --scan          # 扫一次：找版本变化的 request key
  python3 bb-request-watch.py --init          # 初始化水位（记当前版本为已消费）
  python3 bb-request-watch.py --status        # 查水位与未处理请求
常驻：launchd（周期 60s 或事件驱动）
"""
import argparse, json, sys, os, datetime, urllib.request

BB = "http://127.0.0.1:8792"
WM_NS = "/data/frameworks/request-watermark"
WATCH_PREFIXES = ["notes/i9/", "notes/collab/", "notes/mac-mini/"]
# 关键 request key（必须监控的）
KEY_INTEREST = {
    "notes/i9/paper-request": "i9 论文请求",
    "notes/i9/blueprint-request": "i9 蓝图请求",
    "notes/i9/dashboard-config-request": "i9 看板配置请求",
    "notes/i9/role-evaluation-request": "i9 角色评估请求",
    "notes/i9/papers-ack": "i9 论文确认",
}

def get(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def get_watermarks():
    d = get(WM_NS)
    return d.get("value", {}).get("wm", {}) if isinstance(d, dict) else {}

def set_watermark(key, version):
    wm = get_watermarks()
    wm[key] = {"version": version, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    put(WM_NS, {"wm": wm, "ts": datetime.datetime.now().isoformat(timespec="seconds")})

def scan():
    """扫描 request 类 key，找版本变化（未消费的新请求）"""
    wm = get_watermarks()
    notes = get("/notes")
    changes = []
    if not isinstance(notes, dict):
        return changes
    for k, v in notes.get("list", {}).items():
        val = v.get("value")
        if not isinstance(val, dict):
            continue
        # 只监控 request 类 / 兴趣 key
        is_request = val.get("type") == "request" or k in KEY_INTEREST
        if not is_request:
            continue
        ver = v.get("version", 0)
        last = wm.get(k, {}).get("version", 0)
        # 修复：水位不存在（从未处理过的 request key）也视为待处理——不依赖 init 吞存量
        if k not in wm or ver > last:
            changes.append({
                "key": k,
                "version": ver,
                "last_seen": last if k in wm else "未处理",
                "label": KEY_INTEREST.get(k, val.get("subject", val.get("type", ""))),
                "ts": val.get("ts", ""),
            })
    return changes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true", help="扫一次找变化")
    ap.add_argument("--init", action="store_true", help="初始化水位（当前版本为已消费）")
    ap.add_argument("--status", action="store_true", help="查水位")
    args = ap.parse_args()

    if args.status:
        wm = get_watermarks()
        print("== 请求水位 ==")
        for k, v in sorted(wm.items()):
            print("  %s → v%s (%s)" % (k, v.get("version"), v.get("ts","")[:16]))
        sys.exit(0)

    if args.init:
        notes = get("/notes")
        for k, v in notes.get("list", {}).items():
            val = v.get("value")
            if isinstance(val, dict) and (val.get("type") == "request" or k in KEY_INTEREST):
                set_watermark(k, v.get("version", 0))
        print("✅ 水位已初始化（当前所有 request 标记为已消费）")
        sys.exit(0)

    changes = scan()
    if changes:
        print("⚠️ 发现 %d 个未处理请求（版本变化）:" % len(changes))
        for c in changes:
            print("  [v%s→v%s] %s (%s) %s" % (
                c["last_seen"], c["version"], c["key"], c["label"], c["ts"]))
        # 更新水位（标记已报告）
        for c in changes:
            set_watermark(c["key"], c["version"])
        sys.exit(2)  # 有变化
    else:
        print("✅ 无未处理请求（水位一致）")
        sys.exit(0)

if __name__ == "__main__":
    main()
