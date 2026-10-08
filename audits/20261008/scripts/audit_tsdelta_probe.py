#!/usr/bin/env python3
"""★ 深挖：central ts 比 local ts 晚 3–8 分钟意味着什么？
判据：正常双写（同一次工具调用先 local 后 central）两板 ts 应差【秒级】；
      若差【分钟级】⇒ 当次调用未完成 central 写，值系事后由同步器补入。
     ⇒ ts 差可能构成「该次调用超时中断」的【可核旁证】——正是作者声称「不可核」的那一项。
含正控：我今日本人刚发的卡（双写实时完成）的 ts 差。
"""
import json, urllib.request, urllib.error, datetime

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"


def fetch(base, key, t=25):
    try:
        r = urllib.request.urlopen(base + key, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def secs(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").timestamp()
    except Exception:
        return None


print("=" * 78)
print("【A】作者内联的 12 条（#10 用其更正后的正确键）")
print("=" * 78)
d = json.load(urllib.request.urlopen(LOCAL + "notes/mac-mini/author-timeout-entries-12-inline-20261008", timeout=25))
entries = d["value"]["content"]["作者侧 12 条（键 + 落盘 ts）"]
FIX10 = "notes/mac-mini/two-dim-table-landed-and-criterion-mixup-20261008"

author = {}
for e in entries:
    idx, key = e[0], e[1]
    if idx == "10" or "twodim" in key:
        key = FIX10
    sl, vl = fetch(LOCAL, key)
    sc, vc = fetch(CENTRAL, key)
    tl = (vl or {}).get("ts"); tc = (vc or {}).get("ts")
    vvl = (vl or {}).get("version"); vvc = (vc or {}).get("version")
    dl = secs(tl); dc = secs(tc)
    delta = (dc - dl) if (dl and dc) else None
    author[key] = delta
    print(f"[{idx:>2}] v(local/central)={vvl}/{vvc}  ts差={delta:>7.0f}s  {key.split('/')[-1][:52]}")
    print(f"      local  {sl} {tl}")
    print(f"      central{sc} {tc}")

ds = [x for x in author.values() if x is not None]
print(f"\n作者 12 条：ts 差 min={min(ds):.0f}s  max={max(ds):.0f}s  mean={sum(ds)/len(ds):.0f}s  n={len(ds)}")

print()
print("=" * 78)
print("【B】正控：我本人在本轮（07:3x）发出的卡 —— 双写应当实时完成")
print("=" * 78)
mine = [
    "notes/mac-mini/audit-half-cross-checked-24-and-list-rule-nailed-20261008",
    "notes/mac-mini/audit-pstd-f1-not-triggered-and-my-anomaly-mislabel-20261008",
    "notes/mac-mini/audit-index-v3-verbatim-loss-and-judgement-alignment-20261008",
    "notes/mac-mini/c8-downgraded-independent-reproduction-20261008",
    "notes/mac-mini/audit-verdict-index-20261008",
]
mds = []
for k in mine:
    sl, vl = fetch(LOCAL, k)
    sc, vc = fetch(CENTRAL, k)
    tl = (vl or {}).get("ts"); tc = (vc or {}).get("ts")
    delta = (secs(tc) - secs(tl)) if (secs(tl) and secs(tc)) else None
    if delta is not None:
        mds.append(delta)
    print(f"  v(local/central)={(vl or {}).get('version')}/{(vc or {}).get('version')}  ts差={delta}s  {k.split('/')[-1][:50]}")
    print(f"      local {sl} {tl} | central {sc} {tc}")

if mds:
    print(f"\n我的卡：ts 差 min={min(mds):.0f}s max={max(mds):.0f}s mean={sum(mds)/len(mds):.0f}s  n={len(mds)}")
print()
print("⇒ 判读：若『作者 12 条』的 ts 差显著大于『我的卡』，则 ts 差是【调用未完成 central 写】的可核旁证。")
