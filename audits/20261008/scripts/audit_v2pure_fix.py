#!/usr/bin/env python3
"""修正版：① 先看清 v2 卡条目字段的真实结构（不预设）② 列出【所有】版本差异常（dv<=-1 或 dv>=2）
★ 本版针对我上一版的两个缺陷：结构预设导致静默跳过；判据只覆盖 dv<0 漏掉 dv 过大。
"""
import json, urllib.request, urllib.error, hashlib, collections

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
V2 = "notes/mac-mini/author-timeout-entries-12-pure-values-v2-20261008"


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


print("=" * 78)
print("【A】v2 卡条目字段的真实结构（先看，不预设）")
print("=" * 78)
s, d = fetch(LOCAL, V2)
assert isinstance(d, dict), f"v2 卡读取失败 http={s}"
c = d["value"]["content"]
for k, v in c.items():
    print(f"\n[{k}]  type={type(v).__name__} len={len(v) if isinstance(v,(list,str,dict)) else '-'}")
    if isinstance(v, list):
        if v:
            print("   首元素 type =", type(v[0]).__name__)
            print("   首元素 =", json.dumps(v[0], ensure_ascii=False)[:300])
    else:
        print("   值 =", str(v)[:200])

# 自适应解析：list 元素可能是 list 或 dict
entries = None
for k, v in c.items():
    if isinstance(v, list) and v:
        e0 = v[0]
        if isinstance(e0, list) and len(e0) >= 2:
            entries = [(r[0], r[1], (r[2] if len(r) > 2 else None)) for r in v]
            break
        if isinstance(e0, dict):
            kk = [x for x in e0 if "key" in x.lower() or "键" in x]
            if kk:
                keyf = kk[0]
                tsf = next((x for x in e0 if "ts" in x.lower()), None)
                entries = [(str(i + 1), r[keyf], r.get(tsf) if tsf else None) for i, r in enumerate(v)]
                break
if entries is None:
    print("\n❌ 未能识别条目结构 —— 明确报错，不静默跳过")
else:
    print(f"\n识别到 {len(entries)} 条；用【字段原样】拼 URL 逐条重跑：")
    ok = tsok = 0
    for idx, key, claim in entries:
        dirty = (key != key.strip()) or (" " in key) or ("注" in key) or ("（" in key)
        sl, vl = fetch(LOCAL, key)
        sc, vc = fetch(CENTRAL, key)
        tl = (vl or {}).get("ts")
        good = (sl == 200 and sc == 200)
        tgood = (tl == claim)
        ok += good; tsok += tgood
        print(f"  [{idx:>2}] 脏字段={dirty} local={sl} central={sc} ts匹配={tgood}  {key}")
    print(f"\n⇒ 原样字段逐条：双板 200 = {ok}/{len(entries)}   ts 精确匹配 = {tsok}/{len(entries)}")

print()
print("=" * 78)
print("【B】所有版本差异常（dv<=-1 或 dv>=2），最近 120 张")
print("=" * 78)
s, d = fetch(LOCAL, "notes/mac-mini/?limit=400")
items = sorted(d["list"].items(), key=lambda kv: kv[1].get("ts") or "", reverse=True)[:120]
stat = collections.Counter(); anomalies = []
for key, meta in items:
    sl, vl = fetch(LOCAL, key)
    sc, vc = fetch(CENTRAL, key)
    if not isinstance(vl, dict) or not isinstance(vc, dict):
        stat["fetch_fail"] += 1
        continue
    dv = vc.get("version") - vl.get("version")
    stat[dv] += 1
    if dv <= -1 or dv >= 2:
        anomalies.append((key, vl.get("version"), vc.get("version"), dv,
                          sha(vl.get("value")) == sha(vc.get("value")), vl.get("ts")))
tot = sum(v for k, v in stat.items() if isinstance(k, int))
print("dv 分布:", {k: f"{v}/{tot} ({v/tot*100:.1f}%)" for k, v in sorted(stat.items(), key=lambda x: str(x[0]))})
print("\n异常卡（dv<=-1 或 dv>=2）:")
for key, lv, cv, dv, same, ts in anomalies:
    print(f"  dv={dv}  local v{lv}/central v{cv}  value一致={same}  ts={ts}")
    print(f"        {key}")
if not anomalies:
    print("  （无）")
