#!/usr/bin/env python3
"""★ 全量跨板键集比对（不逐键请求，用列表端点做集合差 —— 射程完整）
背景：我先前的「55 个单板残留」只在【可疑名子集】内成立，射程不足。
本脚本回答：notes/mac-mini 全命名空间里，两板的键集到底差多少、差在哪、何时写的。
同时复核 A：字符数 vs UTF-8 字节数。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error, datetime, collections

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-key-set-diff.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"


def fetch(base, url, t=30):
    try:
        r = urllib.request.urlopen(base + url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def all_keys(base, ns="notes/mac-mini"):
    out = {}
    offset = 0
    total = None
    while True:
        s, d = fetch(base, f"{ns}/?limit=1000&offset={offset}")
        if not isinstance(d, dict):
            return out, f"FAIL http={s}"
        lst = d.get("list") or {}
        out.update(lst)
        total = d.get("total", 0)
        if len(lst) < 1000 or len(out) >= total or offset > 20000:
            break
        offset += 1000
    return out, total


print("=" * 74)
print("【A】字符数 vs UTF-8 字节数")
print("=" * 74)
s, d = fetch(LOCAL, "notes/mac-mini/card-1791011480")
body = d["value"]["body"]
print(f"  local 字符数={len(body)}  UTF-8字节={len(body.encode('utf-8'))}")
s, d = fetch(CENTRAL, "notes/mac-mini/card-1791011480")
body = d["value"]["body"]
print(f"  central 字符数={len(body)}  UTF-8字节={len(body.encode('utf-8'))}")
print("  ⇒ 若字符数=1601/1629 而字节数≈2878/2910 ⇒ 我此前写「1601 字节」= **单位标错**（把字符当字节）")

print()
print("=" * 74)
print("【B】★ 全量跨板键集比对（列表端点做集合差，不逐键请求）")
print("=" * 74)
kl, tl = all_keys(LOCAL)
kc, tc = all_keys(CENTRAL)
print(f"  local  键数 = {len(kl)}  (total 报告 {tl})")
print(f"  central 键数 = {len(kc)}  (total 报告 {tc})")
only_l = sorted(set(kl) - set(kc))
only_c = sorted(set(kc) - set(kl))
both = set(kl) & set(kc)
print(f"  两板共有 = {len(both)}")
print(f"  ★ 仅 local 有 = {len(only_l)}")
print(f"  ★ 仅 central 有 = {len(only_c)}")


def tsdist(keys, table):
    c = collections.Counter()
    for k in keys:
        ts = (table.get(k) or {}).get("ts") or "?"
        c[ts[:10]] += 1
    return c


print("\n  仅 local 有的键 · 按日期分布:")
for d_, n in sorted(tsdist(only_l, kl).items()):
    print(f"    {d_}: {n}")
print("\n  仅 central 有的键 · 按日期分布:")
for d_, n in sorted(tsdist(only_c, kc).items()):
    print(f"    {d_}: {n}")

print("\n  仅 local 有的键 · 抽样 15 个（含 ts）:")
for k in only_l[:15]:
    print(f"    {(kl.get(k) or {}).get('ts')}  {k}")
print("\n  仅 central 有的键 · 抽样 15 个（含 ts）:")
for k in only_c[:15]:
    print(f"    {(kc.get(k) or {}).get('ts')}  {k}")

print("\n  ⇒ 判读要点：若「仅 local」集中在早期日期（同步器上线前），属**历史存量**；")
print("     若近期仍有，则同步器**当前也在漏推**，属真缺陷。")

print()
print("=" * 74)
print("【C】区分两种解释：① 同步器不回填历史  ② 中央板曾清理")
print("=" * 74)
print("\n  central 全部键 · 按日期分布（若最早=同步器上线日 ⇒ 支持①）:")
cd = tsdist(list(kc.keys()), kc)
for d_, n in sorted(cd.items()):
    print(f"    {d_}: {n}")
print(f"\n  central 最早键 ts = {min((v.get('ts') or '~') for v in kc.values())}")
print(f"  local   最早键 ts = {min((v.get('ts') or '~') for v in kl.values())}")

print("\n  两板共有键 · 按日期分布（看早期键是否也有被同步的）:")
for d_, n in sorted(tsdist(sorted(both), kl).items()):
    print(f"    {d_}: {n}")

