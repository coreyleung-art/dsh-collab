#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""writer-attribution-gate —— 写者归属门（★ 机械化「卡该带署名」这条）

★★ 立据（2026-10-13 查清）：
  某 GUI 的自动上报通道把卡写到 `notes/mac-mini/manager-actions/`，
  `value.from` 只填了一个【服务名】`systemgraph-gui`，**没有任何会话身份**。
  ⇒ 收到时显示 `unattributed` ⇒ **板/校验层无法把它归属到任何会话**。

★ 而本仓【已有 X-Writer 约定】（`tools/bb_dualwrite.py:66` · `scripts/bb-put-verify.py:144`）
  ⇒ 缺的是【机械化检查】，不是新约定。

★★ 判据（三态，不猜）：
  · 有归属：`value.from` 含 `session-` 形态，**或**有 `from_label` / `writer` / `X-Writer` / `writerLabel`
  · 无归属：`value.from` 是一个【服务/进程名】（★ 无 session 形态，且无任何署名类字段）
  · 不可判：读卡失败 / 卡无 `from` 字段（★ 可能是别的卡形）

★ 用法：
  python3 tools/writer-attribution-gate.py                     # 扫默认面
  python3 tools/writer-attribution-gate.py --ns notes/mac-mini/manager-actions/
  python3 tools/writer-attribution-gate.py --json
  python3 tools/writer-attribution-gate.py --selftest
"""
import argparse
import json
import os
import re
import sys
import urllib.request

BB = os.environ.get("BB", "http://127.0.0.1:8792")
TOKEN_FILE = os.path.expanduser("~/.dsh/blackboard-token")

# ★ 默认扫的面（★ 已知的自动上报前缀优先）
DEFAULT_NS = [
    "notes/mac-mini/manager-actions/",
]

# ★ 署名类字段名（★ 任一存在即算有归属）
SIGN_FIELDS = ("from_label", "writer", "writerLabel", "X-Writer", "x-writer", "session", "sessionId")

# ★ 会话身份形态
SESSION_RX = re.compile(r"(?:^|\W)session-[0-9a-f]{6,}", re.I)


def _token():
    try:
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    except Exception:
        return ""


def _get(url, timeout=12):
    """★ 返回 (ok, obj)；ok=False ⇒ 读失败（★ 与「空」区分）"""
    req = urllib.request.Request(url)
    t = _token()
    if t:
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return False, None


def _unwrap(value, depth=3):
    """★★ 2026-10-13 实测：某些卡的 value 是【双层嵌套】
    （`value.value.from`）⇒ 直取 `value.from` 会得 None ⇒ 误判「无 from」。
    ★ 故逐层剥到有 `from` 为止（★ 有限深度，★ 不无限穿）。
    """
    cur, d = value, 0
    while isinstance(cur, dict) and "from" not in cur and isinstance(cur.get("value"), dict) and d < depth:
        cur = cur["value"]; d += 1
    return cur, d


def classify(value):
    """★ 三态判一个卡的 value：'attributed' / 'unattributed' / 'undecidable'"""
    if not isinstance(value, dict):
        return "undecidable", "value 非 dict"
    value, _d = _unwrap(value)
    fr = value.get("from")
    if not fr:
        # ★ 无 from ⇒ 可能是别的卡形 ⇒ 不升格为缺陷
        return "undecidable", "无 from 字段（★ 卡形不同，不升格）"
    for f in SIGN_FIELDS:
        if value.get(f):
            return "attributed", "有署名类字段 %s" % f
    if SESSION_RX.search(str(fr)):
        return "attributed", "from 含 session 形态"
    return "unattributed", "from=%r 是服务/进程名，无任何会话身份" % str(fr)[:40]


def scan_ns(ns, limit=60):
    """★ 扫一个前缀，返回 (ok, rows, note)"""
    ok, d = _get(BB + "/" + ns.rstrip("/") + "/")
    if not ok or not isinstance(d, dict):
        return False, [], "枚举读失败"
    lst = d.get("list") or {}
    if not isinstance(lst, dict):
        return False, [], "list 形态异常"
    keys = sorted(lst.keys())[-limit:]
    rows = []
    for k in keys:
        # ★★ 2026-10-13 修（★ 本纳自查）：**list 的键已是【完整键】**
        #   （★ 实测：`'notes/mac-mini/manager-actions/20260906143337441485'`）
        #   ⇒ 原再拼一次前缀 ⇒ **键翻倍** ⇒ 读卡失败 ⇒ 全判「不可判」（★ 门自己的错）。
        full = str(k) if str(k).startswith(ns.rstrip("/")) else (ns.rstrip("/") + "/" + str(k))
        ok2, card = _get(BB + "/" + full)
        if not ok2 or not isinstance(card, dict):
            rows.append({"key": full, "state": "undecidable", "why": "读卡失败"})
            continue
        v = card.get("value") or {}
        st, why = classify(v)
        rows.append({"key": full, "state": st, "why": why,
                     "from": str(v.get("from"))[:40] if isinstance(v, dict) else None})
    return True, rows, "枚举到 %d 键" % len(lst)


def run(namespaces=None, limit=60):
    namespaces = namespaces or DEFAULT_NS
    out = {"gate": "writer-attribution-gate", "namespaces": [], "summary": {}}
    agg = {"attributed": 0, "unattributed": 0, "undecidable": 0, "readfail": 0}
    honest = []          # ★ 如实标注：空/读失败
    for ns in namespaces:
        ok, rows, note = scan_ns(ns, limit)
        if not ok:
            agg["readfail"] += 1
            honest.append("%s ⇒ %s（★ 不可判，不是「无问题」）" % (ns, note))
            out["namespaces"].append({"ns": ns, "ok": False, "note": note, "rows": []})
            continue
        if not rows:
            honest.append("%s ⇒ 0 条（★ 该前缀下无卡或超出 limit）" % ns)
        for r in rows:
            agg[r["state"]] = agg.get(r["state"], 0) + 1
        out["namespaces"].append({"ns": ns, "ok": True, "note": note, "rows": rows})
    # ★ 无归属的明细（★ 去重按 from）
    un = {}
    for blk in out["namespaces"]:
        for r in blk["rows"]:
            if r["state"] == "unattributed":
                un.setdefault(r.get("from"), []).append(r["key"])
    out["summary"] = agg
    out["unattributed_by_from"] = {k: {"count": len(v), "sample": v[:3]} for k, v in un.items()}
    out["honesty"] = honest
    return out


def selftest():
    """★ 自证：分类器的两向 + 不可判"""
    cases = [
        ({"from": "session-e317d6ab-5302-4b33-b095-947983ba16f4"}, "attributed", "★ 正控：session 形态"),
        ({"from": "systemgraph-gui"}, "unattributed", "★ 负控：纯服务名"),
        ({"from": "systemgraph-gui", "from_label": "明鉴"}, "attributed", "★ 正控：有 from_label"),
        ({"from": "x", "writer": "s"}, "attributed", "★ 正控：有 writer 字段"),
        ({"detail": "no from"}, "undecidable", "★ 不可判：无 from（★ 不升格）"),
        ("not-a-dict", "undecidable", "★ 不可判：非 dict"),
    ]
    ok = 0
    for v, want, name in cases:
        got, why = classify(v)
        if got == want:
            ok += 1
            print("  \u2705 %s \u2192 %s" % (name, got))
        else:
            print("  \u274c %s \u2192 \u671f\u671b %s \u5b9e\u5f97 %s" % (name, want, got))
    # ★ 正控：正则本身能命中
    ok += 1
    if SESSION_RX.search("session-abcdef123456"):
        print("  \u2705 \u6b63\u63a7\uff1aSESSION_RX \u80fd\u547d\u4e2d session \u5f62\u6001")
    else:
        print("  \u274c \u6b63\u63a7\uff1aSESSION_RX \u672a\u547d\u4e2d\uff08\u2605 \u63a2\u9488\u574f\u4e86\uff09")
        ok -= 1
    # ★ 负控：正则不该误命中普通词
    ok += 1
    if not SESSION_RX.search("systemgraph-gui"):
        print("  \u2705 \u8d1f\u63a7\uff1aSESSION_RX \u4e0d\u8bef\u547d\u4e2d\u670d\u52a1\u540d")
    else:
        print("  \u274c \u8d1f\u63a7\uff1aSESSION_RX \u8bef\u547d\u4e2d\u670d\u52a1\u540d")
        ok -= 1
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, len(cases) + 2))
    return 0 if ok == len(cases) + 2 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", action="append", default=None, help="\u626b\u7684\u524d\u7f00\uff08\u53ef\u591a\u6b21\uff09")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("writer-attribution-gate 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    res = run(a.ns, a.limit)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        s = res["summary"]
        print("== writer-attribution-gate 1.0.0 ==")
        print("  \u626b\u9762\uff1a%s" % ", ".join(x["ns"] for x in res["namespaces"]))
        print("  \u5f52\u5c5e %d \u00b7 \u65e0\u5f52\u5c5e %d \u00b7 \u4e0d\u53ef\u5224 %d \u00b7 \u8bfb\u5931\u8d25 %d"
              % (s.get("attributed", 0), s.get("unattributed", 0),
                 s.get("undecidable", 0), s.get("readfail", 0)))
        if res["unattributed_by_from"]:
            print("  \u2605\u2605 \u65e0\u5f52\u5c5e\u5199\u8005\uff08\u2605 \u6309 from \u5206\u7ec4\uff09\uff1a")
            for k, v in res["unattributed_by_from"].items():
                print("     %-24s %d \u5f20 \u00b7 \u4f8b\uff1a%s" % (k, v["count"], v["sample"][0]))
        for h in res["honesty"]:
            print("  \u2605 %s" % h)
        if not res["unattributed_by_from"]:
            print("  \u2705 \u672a\u53d1\u73b0\u65e0\u5f52\u5c5e\u5199\u8005")
    return 1 if res["summary"].get("unattributed", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
