#!/usr/bin/env python3
"""两项独立复核：
A) 他的 v2 卡是否真的「另发一版 + 键字段纯值」⇒ 用【字段原样】（不 strip/replace）逐条 GET
B) 「dv = -1 ⇒ 绕过写门」这一推论的基率与分档（dv<0 的卡：value 是否一致）
"""
import json, urllib.request, urllib.error, hashlib, collections

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
V2 = "notes/mac-mini/author-timeout-entries-12-pure-values-v2-20261008"
V1 = "notes/mac-mini/author-timeout-entries-12-inline-20261008"


def fetch(base, key, t=20):
    try:
        r = urllib.request.urlopen(base + key, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def sha(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


print("=" * 76)
print("【A】v2 卡：键字段是否纯值（用字段原样拼 URL，不做任何清洗）")
print("=" * 76)
s, d = fetch(LOCAL, V2)
print("v2 卡 http =", s, " ts =", (d or {}).get("ts"))
raw = None
if isinstance(d, dict):
    c = d["value"].get("content", {})
    print("v2 content keys =", list(c.keys()))
    for k, v in c.items():
        if isinstance(v, list) and v and isinstance(v[0], list):
            raw = v
            print("条目字段名 =", k)
    if raw:
        ok = 0
        tsok = 0
        for row in raw:
            idx, key = row[0], row[1]
            claim = row[2] if len(row) > 2 else None
            dirty = (key != key.strip()) or (" " in key) or ("注" in key)
            sl, vl = fetch(LOCAL, key)
            sc, vc = fetch(CENTRAL, key)
            tl = (vl or {}).get("ts")
            good = (sl == 200 and sc == 200)
            ok += good
            tgood = (tl == claim)
            tsok += tgood
            print(f"  [{idx:>2}] 含空白/注释={dirty}  local={sl} central={sc} ts匹配={tgood}  {key}")
        print(f"\n⇒ 原样字段逐条: 双板 200 = {ok}/{len(raw)}   ts 匹配 = {tsok}/{len(raw)}")
        print("⇒ 纯值判定:", "✅ 成立（无空白/注释，全部原样可解析）" if ok == len(raw) else "❌ 仍有不可解析项")

print()
print("=" * 76)
print("【B】上版是否保留且未被偷改")
print("=" * 76)
s1, d1 = fetch(LOCAL, V1)
print(f"v1 卡 http={s1} ts={(d1 or {}).get('ts')} version={(d1 or {}).get('version')}")
print("  期望 ts = 2026-10-08T07:33:27（我此前实测值）")

print()
print("=" * 76)
print("【C】dv<0 基率与分档（最近 120 张）")
print("=" * 76)
s, d = fetch(LOCAL, "notes/mac-mini/?limit=400")
items = sorted(d["list"].items(), key=lambda kv: kv[1].get("ts") or "", reverse=True)[:120]
stat = collections.Counter()
neg = []
for key, meta in items:
    sl, vl = fetch(LOCAL, key)
    sc, vc = fetch(CENTRAL, key)
    if not isinstance(vl, dict) or not isinstance(vc, dict):
        stat["fetch_fail"] += 1
        continue
    dv = vc.get("version") - vl.get("version")
    stat[dv] += 1
    if dv < 0:
        same = sha(vl.get("value")) == sha(vc.get("value"))
        neg.append((key, vl.get("version"), vc.get("version"), dv, same, vl.get("ts")))
print("dv 分布:", dict(sorted(stat.items(), key=lambda x: str(x[0]))))
tot = sum(v for k, v in stat.items() if isinstance(k, int))
print(f"有效样本 = {tot}")
for k in sorted([x for x in stat if isinstance(x, int)]):
    print(f"  dv={k:>2}: {stat[k]:>3}/{tot} = {stat[k]/tot*100:.1f}%")
print("\ndv<0 的卡：")
for key, lv, cv, dv, same, ts in neg:
    print(f"  dv={dv} local v{lv}/central v{cv}  value一致={same}  {ts}  {key.split('/')[-1][:56]}")
print("\n⇒ 判读：dv<0 若罕见且集中在已知绕门样本上，则「dv<0 可作绕门指纹」有支持；")
print("   但需注意 dv<0 且 value 不一致才是【内容风险】，应单独分档。")
