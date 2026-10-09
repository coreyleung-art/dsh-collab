#!/usr/bin/env python3
"""★ 基率检验（决定「1/2 指纹」是否成立的命门）
问题：若 notes/mac-mini 里【大多数】卡都是 central=local+1，则「+1 ⇒ 该次调用超时」不成立。
方法：取该命名空间最近 N 张卡，逐张查两板 version 与 ts，统计分布。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error, datetime, collections

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-baserate-probe.log")


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
N = 45


def fetch(base, key, t=20):
    try:
        r = urllib.request.urlopen(base + key, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


def secs(ts):
    try:
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").timestamp()
    except Exception:
        return None


s, d = fetch(LOCAL, "notes/mac-mini/?limit=400")
lst = d["list"]
print("命名空间 notes/mac-mini 条目数（list）=", len(lst), " total=", d.get("total"))

items = sorted(lst.items(), key=lambda kv: kv[1].get("ts") or "", reverse=True)
print("最近卡时间范围:", items[0][1].get("ts"), "→", items[min(N, len(items)) - 1][1].get("ts"))

# 已知归属标注
AUTHOR_KEYS = set()
try:
    c = json.load(urllib.request.urlopen(LOCAL + "notes/mac-mini/author-timeout-entries-12-inline-20261008", timeout=20))
    for e in c["value"]["content"]["作者侧 12 条（键 + 落盘 ts）"]:
        k = e[1].split("notes/mac-mini/")[-1]
        AUTHOR_KEYS.add(e[1] if "twodim" not in k else "notes/mac-mini/two-dim-table-landed-and-criterion-mixup-20261008")
except Exception as ex:
    print("(作者清单读取失败)", ex)
MINE = {"audit-half-cross-checked-24-and-list-rule-nailed-20261008",
        "audit-pstd-f1-not-triggered-and-my-anomaly-mislabel-20261008",
        "audit-index-v3-verbatim-loss-and-judgement-alignment-20261008",
        "c8-downgraded-independent-reproduction-20261008",
        "audit-verdict-index-20261008"}

stat = collections.Counter()
rows = []
codes = collections.Counter()
for key, meta in items[:N]:
    full = key  # ★ 修正：list 返回的 key 已含完整路径（notes/mac-mini/xxx），
                #   先前误加前缀 ⇒ 全部 404 ⇒ 静默 None（我的方法错，已记录）
    sl, vl = fetch(LOCAL, full)
    sc, vc = fetch(CENTRAL, full)
    codes[(sl, sc)] += 1
    if not isinstance(vl, dict) or not isinstance(vc, dict):
        print(f"  ⚠ 取样失败 local={sl} central={sc} :: {full[:70]}")
        continue
    vvl = vl.get("version"); vvc = vc.get("version")
    tl = vl.get("ts"); tc = vc.get("ts")
    dv = (vvc - vvl) if isinstance(vvl, int) and isinstance(vvc, int) else None
    dt = (secs(tc) - secs(tl)) if (secs(tl) and secs(tc)) else None
    stat[dv] += 1
    tag = "作者" if full in AUTHOR_KEYS else ("裁判" if key in MINE else "")
    rows.append((key, vvl, vvc, dv, dt, tag, tl))
    print(f"  dv={str(dv):>5} ts差={('%7.0f' % dt) if dt is not None else '   None'}s {tag:>4} {key[:56]}")
print("\nHTTP 码分布 (local, central):", dict(codes))

print("\n=== 基率：central - local 的 version 差分布（最近 %d 张）===" % len(rows))
tot = sum(stat.values())
for dv, cnt in sorted(stat.items(), key=lambda x: (x[0] is None, x[0])):
    print(f"  dv={dv}: {cnt}/{tot} = {cnt/tot*100:.1f}%")

pos = [r for r in rows if r[3] == 1]
print(f"\ndv=+1（=central 多发过一次写）的卡: {len(pos)}/{tot}")
if pos:
    dts = [r[4] for r in pos if r[4] is not None]
    print(f"  其中 ts 差: min={min(dts):.0f}s max={max(dts):.0f}s mean={sum(dts)/len(dts):.0f}s")
zero = [r for r in rows if r[3] == 0]
if zero:
    dts0 = [r[4] for r in zero if r[4] is not None]
    print(f"dv=0 的卡: {len(zero)}/{tot}；其 ts 差 min={min(dts0):.0f}s max={max(dts0):.0f}s mean={sum(dts0)/len(dts0):.0f}s")
print("\n⇒ 判读：若 dv=+1 只是少数且作者 12 条集中落在其中，则「+1 指纹」成立；反之不成立。")
