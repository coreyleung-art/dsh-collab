#!/usr/bin/env python3
"""决定性验证：那条新出现的「仅-local」键是否在 <=300s 同步窗口内被推上
对象：notes/mac-mini/closing-the-a-b-gap-binary-and-carrier-errors-only-cause-false-negatives-20261008
（ts 12:36:28；我第一次测于 ~12:5x，发现它仍是仅-local）
若现已两板都有 ⇒ 支持「表内前缀 + <=300s 同步窗口」模型；若仍仅 local ⇒ 真遗漏
"""
import json, urllib.request, urllib.error, datetime

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
K = "notes/mac-mini/closing-the-a-b-gap-binary-and-carrier-errors-only-cause-false-negatives-20261008"


def get(base, key):
    try:
        r = urllib.request.urlopen(base + key, timeout=20)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


print("NOW =", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
sl, vl = get(LOCAL, K)
sc, vc = get(CENTRAL, K)
print(f"\n  local   http={sl}  ts={(vl or {}).get('ts')}")
print(f"  central http={sc}  ts={(vc or {}).get('ts')}")
print(f"\n  ⇒ {'✅ 已被推上（两板都有）⇒ 支持表内前缀 + <=300s 同步窗口' if sc == 200 else '⚠ 仍仅 local ⇒ 可能真遗漏，或同步周期未到'}")

# 再统计当前仅-local 的最晚 ts（全前缀快速版：只比键集，不取 value）
def keys_of(base, ns):
    out = {}
    off = 0
    while True:
        try:
            r = urllib.request.urlopen(f"{base}{ns}/?limit=1000&offset={off}", timeout=30)
            d = json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            break
        lst = d.get("list") or {}
        out.update(lst)
        if len(lst) < 1000 or len(out) >= d.get("total", 0):
            break
        off += 1000
    return out


kl = keys_of(LOCAL, "notes/mac-mini")
kc = keys_of(CENTRAL, "notes/mac-mini")
only_l = {k: v for k, v in kl.items() if k not in kc}
ts = sorted((str(v.get("ts") or ""), k) for k, v in only_l.items())
print(f"\n  当前：local={len(kl)} central={len(kc)} 仅local={len(only_l)}")
print("  仅-local 最晚 5 条:")
for t, k in ts[-5:]:
    print(f"    {t}  {k}")
