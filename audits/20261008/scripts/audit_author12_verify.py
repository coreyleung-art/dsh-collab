#!/usr/bin/env python3
"""逐条互核 PSTD 作者内联的 12 条超时卡：
判据 = ① 双板 HTTP 200（对象存在） ② 实测 ts == 声称 ts（同一条卡，而非仅仅是「有个卡」）
"""
import json, urllib.request, urllib.error

CARD = "notes/mac-mini/author-timeout-entries-12-inline-20261008"
LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"


def fetch(base, key, timeout=25):
    try:
        r = urllib.request.urlopen(base + key, timeout=timeout)
        body = r.read().decode("utf-8", "replace")
        return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


d = json.load(urllib.request.urlopen(LOCAL + CARD, timeout=25))
entries = d["value"]["content"]["作者侧 12 条（键 + 落盘 ts）"]
print(f"卡内条目数 = {len(entries)}（卡落盘 ts = {d.get('ts')}）\n")

ok_obj = ok_ts = 0
rows = []
for e in entries:
    idx, key, claim_ts = e[0], e[1], e[2]
    sl, vl = fetch(LOCAL, key)
    sc, vc = fetch(CENTRAL, key)
    tl = vl.get("ts") if isinstance(vl, dict) else None
    tc = vc.get("ts") if isinstance(vc, dict) else None
    obj_ok = (sl == 200 and sc == 200)
    ts_ok = (tl == claim_ts and tc == claim_ts)
    ok_obj += obj_ok
    ok_ts += ts_ok
    rows.append((idx, key, claim_ts, sl, sc, tl, tc, obj_ok, ts_ok))
    print(f"[{idx:>2}] {key}")
    print(f"     声称 ts={claim_ts}  local {sl} ts={tl}  central {sc} ts={tc}")
    print(f"     对象 {('✅' if obj_ok else '❌')}    ts一致 {('✅' if ts_ok else '❌')}")

print(f"\n=== 汇总 ===")
print(f"对象存在（双板 200）: {ok_obj}/{len(entries)}")
print(f"声称 ts 双板一致     : {ok_ts}/{len(entries)}")

# ★ 他自报的更正：#10 键名写错
print("\n=== 他自报更正的 #10 键名 ===")
wrong = "notes/mac-mini/twodim-table-landed-and-criterion-mixup-20261008"
right = "notes/mac-mini/two-dim-table-landed-and-criterion-mixup-20261008"
for label, k in (("他先前写的错键", wrong), ("他更正的正确键", right)):
    s, v = fetch(LOCAL, k)
    print(f"  {label}: {k}")
    print(f"     local http={s} ts={(v or {}).get('ts') if isinstance(v, dict) else None}")
print("  期望：错键 404（**不是 400**，因格式合法只是不存在）；正确键 200 且 ts=2026-10-08T07:21:16")
