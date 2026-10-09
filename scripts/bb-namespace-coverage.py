#!/usr/bin/env python3
"""核实作者的反例：notes/genebank 是否 local 8595 / central 0，且多在今日 04 点
★ 同时升维：把结论从「单个命名空间」提升到「全板命名空间覆盖」

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error, collections

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-namespace-coverage.log")


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


print("=" * 76)
print("【A】枚举顶层命名空间")
print("=" * 76)
ns_candidates = set()
for probe in ("notes/", "data/", "tasks/"):
    s, d = fetch(LOCAL, probe)
    if isinstance(d, dict):
        lst = d.get("list") or {}
        print(f"  GET /{probe}  http={s}  total={d.get('total')}  顶层条目数={len(lst)}")
        # list 的 key 形如 notes/genebank/xxx 或 notes/genebank
        for k in list(lst.keys())[:400]:
            parts = k.split("/")
            if len(parts) >= 2:
                ns_candidates.add(parts[0] + "/" + parts[1])
        # 也看 value 是否是子命名空间列表
        sample = list(lst.items())[:2]
        for k, v in sample:
            print(f"     例: {k} -> {json.dumps(v, ensure_ascii=False)[:120]}")
    else:
        print(f"  GET /{probe}  http={s}  非 dict")

print(f"\n  探测到的子命名空间候选（{len(ns_candidates)} 个，前 30）:")
for n in sorted(ns_candidates)[:30]:
    print("   ", n)

print()
print("=" * 76)
print("【B】逐命名空间两板键数对比（★ 这正是「射程」的正确修法）")
print("=" * 76)
print(f"{'命名空间':<28}{'local':>10}{'central':>10}{'差':>10}")
for ns in sorted(ns_candidates):
    sl, dl = fetch(LOCAL, ns + "/?limit=1")
    sc, dc = fetch(CENTRAL, ns + "/?limit=1")
    tl = dl.get("total") if isinstance(dl, dict) else None
    tc = dc.get("total") if isinstance(dc, dict) else None
    if isinstance(tl, int) or isinstance(tc, int):
        diff = (tl or 0) - (tc or 0)
        print(f"  {ns:<26}{str(tl):>10}{str(tc):>10}{diff:>10}")

print()
print("=" * 76)
print("【C】genebank 专项：键数与写入时刻分布（核对方的 8595 / 今日 04 点 8511）")
print("=" * 76)
for label, base in (("local", LOCAL), ("central", CENTRAL)):
    s, d = fetch(base, "notes/genebank/?limit=1000")
    if isinstance(d, dict):
        print(f"  {label}: total={d.get('total')}  本页={len(d.get('list') or {})}  http={s}")
        lst = d.get("list") or {}
        c = collections.Counter((v.get("ts") or "?")[:13] for v in lst.values())
        print(f"    本页 ts 按小时分布（前 8）:")
        for k, n in sorted(c.items(), reverse=True)[:8]:
            print(f"      {k}  {n}")
    else:
        print(f"  {label}: http={s}")
