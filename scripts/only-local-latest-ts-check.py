#!/usr/bin/env python3
"""独立复核对方的强确证：「notes/mac-mini/ 的仅-local 键最晚 ts = 2026-10-02T22:22」
若属实 ⇒ 支持「表内前缀在启用后完整、启用前不回填」这一统一模型。
"""
import json, urllib.request, urllib.error

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"


def keys_of(base, ns):
    out = {}
    off = 0
    while True:
        try:
            r = urllib.request.urlopen(f"{base}{ns}/?limit=1000&offset={off}", timeout=30)
            d = json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            print(f"  读取失败 {base}{ns}: {e}")
            break
        lst = d.get("list") or {}
        out.update(lst)
        if len(lst) < 1000 or len(out) >= d.get("total", 0):
            break
        off += 1000
    return out


NS = "notes/mac-mini"
kl = keys_of(LOCAL, NS)
kc = keys_of(CENTRAL, NS)
only_l = {k: v for k, v in kl.items() if k not in kc}
both = {k: v for k, v in kl.items() if k in kc}

print(f"local={len(kl)}  central={len(kc)}  仅local={len(only_l)}  共有={len(both)}")


def latest(d):
    ts = sorted(str(v.get("ts") or "") for v in d.values())
    return (ts[0], ts[-1]) if ts else (None, None)


lo_l, hi_l = latest(only_l)
lo_b, hi_b = latest(both)
print(f"\n  仅-local 键 ts 范围: {lo_l} .. {hi_l}")
print(f"  共有键    ts 范围: {lo_b} .. {hi_b}")
print(f"\n  ★ 仅-local 的最晚 ts = {hi_l}")
print("  对方声称 = 2026-10-02T22:22")
print(f"  ⇒ {'✅ 一致' if hi_l and hi_l.startswith('2026-10-02T22:') else '⚠ 不一致/不一致的精度'}")
print(f"\n  ⇒ 若一致：10-02 之后该前缀的键**全部两板都有** ⇒ 支持“表内前缀在启用后完整”")
print(f"  ⇒ 注意：最晚一条 = {hi_l} 对应的键名（便于逐步核对）:")
for k, v in sorted(only_l.items(), key=lambda kv: str(kv[1].get('ts') or ''), reverse=True)[:5]:
    print(f"     {v.get('ts')}  {k}")
