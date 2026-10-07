#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理我写错路径的黑板键（含多写的 notes/ 层级）。

规则（已实测）：URL `/notes/<K>` 产生的键就是 `notes/<K>`。
⇒ 要写键 `notes/mbp/X`，URL 必须是 `/notes/mbp/X`。
"""
def _bb_extra():
    """新头 X-Blackboard-Token（读 ~/.dsh/blackboard-token，0600）。
    ★ 2026-10-03 flip 双头过渡：旧头保留 ⇒ flip 前后都能写。"""
    try:
        _t = open(__import__("os").path.expanduser("~/.dsh/blackboard-token"),
                  encoding="utf-8").read().strip()
        return {"X-Blackboard-Token": _t} if _t else {}
    except Exception:
        return {}


import json, urllib.request

TOK = "c6b784621fc871de1077517c24165e93"
BB = "http://106.53.214.108:8792"


def put_full_key(full_key, val):
    """full_key 形如 notes/mbp/X ⇒ 打到 /notes/mbp/X"""
    assert full_key.startswith("notes/")
    url = BB + "/notes/" + full_key[len("notes/"):]
    req = urllib.request.Request(
        url, data=json.dumps(val, ensure_ascii=False).encode("utf-8"),
        method="PUT", headers={"Content-Type": "application/json",
                               "X-Webhook-Token": TOK, **_bb_extra()})
    return json.load(urllib.request.urlopen(req, timeout=20))


def get_full_key(full_key):
    url = BB + "/notes/" + full_key[len("notes/"):]
    try:
        req = urllib.request.Request(url, headers={"X-Webhook-Token": TOK, **_bb_extra()})
        return json.load(urllib.request.urlopen(req, timeout=10))
    except Exception as e:
        return {"ERR": str(e)}


# 需要作废的错误键 → 正确键
BAD = {
    "notes/notes/mbp/approval-blocking-data-request-20260914":
        "notes/mbp/approval-blocking-data-request-20260914",
    "notes/notes/mbp/approval-blocking-probe-script-20260914":
        "notes/mbp/approval-blocking-probe-script-20260914",
    "notes/notes/mbp/probe-connectivity-20260914":
        "notes/mbp/approval-blocking-data-request-20260914",
    "notes/notes/notes/mbp/approval-blocking-data-request-20260914":
        "notes/mbp/approval-blocking-data-request-20260914",
    "notes/notes/notes/mbp/approval-blocking-probe-script-20260914":
        "notes/mbp/approval-blocking-probe-script-20260914",
    "notes/notes/notes/mbp/probe-connectivity-20260914":
        "notes/mbp/approval-blocking-data-request-20260914",
}

print("=== 清理错误键 ===")
for bad, good in BAD.items():
    # 已存在的才处理，避免又造出新键
    cur = get_full_key(bad)
    if "ERR" in cur:
        print("  (不存在，跳过) %s" % bad)
        continue
    if (cur.get("value") or {}).get("type") == "tombstone":
        print("  (已是墓碑)   %s" % bad)
        continue
    r = put_full_key(bad, {"type": "tombstone", "by": "MBP session-20b800d4",
                           "title": "作废：本键路径写错（多一层 notes/）",
                           "correct_key": good})
    print("  已作废 → %s" % r.get("key"))

print()
print("=== 校验：正确键仍在 ===")
for k in ["notes/mbp/approval-blocking-data-request-20260914",
          "notes/mbp/approval-blocking-probe-script-20260914"]:
    d = get_full_key(k)
    v = d.get("value") or {}
    print("  %s\n     title=%s | version=%s" % (k, v.get("title"), d.get("version")))
