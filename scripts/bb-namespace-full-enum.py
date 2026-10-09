#!/usr/bin/env python3
"""完整枚举顶层命名空间（拉全量键名前缀，不靠抽样推断）
并逐命名空间做两板键数对比 —— 这是「射程」问题的正确修法。
作者的反例 notes/genebank 我的上一版脚本**根本没探到**，因为候选集是从前 400 条推断的。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error, collections

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-namespace-full-enum.log")


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


def fetch(base, url, t=40):
    try:
        r = urllib.request.urlopen(base + url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def enumerate_ns(root, cap=80000):
    """拉全量键名，提取二级前缀"""
    prefixes = collections.Counter()
    offset = 0
    seen = 0
    while True:
        s, d = fetch(LOCAL, f"{root}/?limit=1000&offset={offset}")
        if not isinstance(d, dict):
            break
        lst = d.get("list") or {}
        for k in lst:
            parts = k.split("/")
            if len(parts) >= 2:
                prefixes[parts[0] + "/" + parts[1]] += 1
        seen += len(lst)
        if len(lst) < 1000 or seen >= d.get("total", 0) or seen >= cap:
            break
        offset += 1000
    return prefixes, seen


all_ns = collections.Counter()
for root in ("notes", "data", "tasks"):
    p, n = enumerate_ns(root)
    print(f"  {root}/ 共枚举 {n} 条，二级前缀 {len(p)} 个")
    all_ns.update(p)

print(f"\n=== 完整二级命名空间清单（{len(all_ns)} 个，按 local 键数降序）===")
print(f"{'命名空间':<34}{'local':>9}{'central':>9}{'差':>9}")
rows = []
for ns in all_ns:
    sl, dl = fetch(LOCAL, ns + "/?limit=1", t=20)
    tl = dl.get("total") if isinstance(dl, dict) else None
    sc, dc = fetch(CENTRAL, ns + "/?limit=1", t=20)
    tc = dc.get("total") if isinstance(dc, dict) else None
    rows.append((ns, tl, tc, all_ns[ns]))
rows.sort(key=lambda r: -(r[1] or 0))
rows = [r for r in rows if (r[1] or 0) > 0 or (r[2] or 0) > 0]   # 过滤掉 total=0 的假前缀（键名被误当前缀）
print(f"  实际有键的命名空间 = {len(rows)} 个")
for ns, tl, tc, cnt in rows:
    diff = (tl or 0) - (tc or 0)
    flag = "  ← ★ 板级反例" if (tl or 0) > 1000 and (tc or 0) == 0 else ""
    print(f"  {ns:<32}{str(tl):>9}{str(tc):>9}{diff:>9}{flag}")

tot_l = sum(r[1] or 0 for r in rows)
tot_c = sum(r[2] or 0 for r in rows)
print(f"\n  合计 local = {tot_l}   central = {tot_c}   差 = {tot_l - tot_c}")
