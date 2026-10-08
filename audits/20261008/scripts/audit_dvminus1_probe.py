#!/usr/bin/env python3
"""追查唯一的 dv=-1 例：local 比 central 多一次写 —— 两板【值】是否一致？
（若值一致 ⇒ 仅状态不一致；若值不同 ⇒ 内容不一致=真问题）
同时补一个时间梯度检验：dv=0 是否集中在最年轻的卡上（支持「同步器随时间重推」）。
"""
import json, urllib.request, urllib.error, hashlib, datetime

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
TARGET = "notes/mac-mini/audit-two-caller-criterion-and-my-overclaim-20261008"


def fetch(base, key, t=25):
    try:
        r = urllib.request.urlopen(base + key, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def sha(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


print("=== dv=-1 例追查 ===")
sl, vl = fetch(LOCAL, TARGET)
sc, vc = fetch(CENTRAL, TARGET)
print("local  ", sl, "version=", vl.get("version"), "ts=", vl.get("ts"))
print("central", sc, "version=", vc.get("version"), "ts=", vc.get("ts"))
sha_l, sha_c = sha(vl.get("value")), sha(vc.get("value"))
print("value sha (sort_keys) local/central =", sha_l, sha_c, "->", "一致 ✅" if sha_l == sha_c else "**不一致 ❌**")

# 键级差异
a, b = vl.get("value"), vc.get("value")
if isinstance(a, dict) and isinstance(b, dict):
    only_l = set(a) - set(b); only_c = set(b) - set(a)
    diff = [k for k in set(a) & set(b) if a[k] != b[k]]
    print("  仅 local 有:", sorted(only_l))
    print("  仅 central 有:", sorted(only_c))
    print("  值不同的键:", sorted(diff))
    print("  local keys =", len(a), " central keys =", len(b))
    print("  local subject =", str(a.get("subject"))[:100])

print()
print("=== 时间梯度检验（dv=0 是否集中在最年轻的卡）===")
s, d = fetch(LOCAL, "notes/mac-mini/?limit=400")
items = sorted(d["list"].items(), key=lambda kv: kv[1].get("ts") or "", reverse=True)
print("按 ts 降序的前 8 张卡：")
for i, (k, m) in enumerate(items[:8], 1):
    sc2, vc2 = fetch(CENTRAL, k)
    sv2, vl2 = fetch(LOCAL, k)
    dv = (vc2.get("version") - vl2.get("version")) if isinstance(vc2, dict) and isinstance(vl2, dict) else None
    print(f"  #{i} dv={dv} local_ts={m.get('ts')} {k.split('/')[-1][:58]}")
