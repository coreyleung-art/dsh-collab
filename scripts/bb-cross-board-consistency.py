#!/usr/bin/env python3
"""修正版 v2：① 按他「格式说明」里写的 `序号|键|ts` 解析 ② ★ 正确判据 = 逐张比对两板 value（不论 dv）
教训来源：dv 只是代理指标；dv=0 也可能两板值不同（分叉）。上一版我只查了 dv!=0 的卡，射程不足。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error, hashlib, collections

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-cross-board-consistency.log")


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
print("【A】v2 卡：按 `序号|键|ts` 解析，用字段原样逐条重跑")
print("=" * 78)
s, d = fetch(LOCAL, V2)
c = d["value"]["content"]
lines = c["条目（键字段为纯值，可直接拼 URL 重跑）"]
ok = tsok = 0
for line in lines:
    parts = line.split("|")
    if len(parts) != 3:
        print(f"  ❌ 行格式不符 `序号|键|ts`：{line[:80]}")
        continue
    idx, key, claim = parts
    sl, vl = fetch(LOCAL, key)
    sc, vc = fetch(CENTRAL, key)
    tl = (vl or {}).get("ts")
    good = (sl == 200 and sc == 200); ok += good
    tgood = (tl == claim); tsok += tgood
    print(f"  [{idx:>2}] local={sl} central={sc} ts匹配={tgood}  {key}")
print(f"\n⇒ 双板 200 = {ok}/{len(lines)}   ts 精确匹配 = {tsok}/{len(lines)}")

print()
print("=" * 78)
print("【B】★ 正确判据：逐张比对两板 value（不论 dv）—— 最近 120 张")
print("=" * 78)
s, d = fetch(LOCAL, "notes/mac-mini/?limit=400")
items = sorted(d["list"].items(), key=lambda kv: kv[1].get("ts") or "", reverse=True)[:120]
dvstat = collections.Counter()
mismatch = []
n = 0
for key, meta in items:
    sl, vl = fetch(LOCAL, key)
    sc, vc = fetch(CENTRAL, key)
    if not isinstance(vl, dict) or not isinstance(vc, dict):
        continue
    n += 1
    dv = vc.get("version") - vl.get("version")
    dvstat[dv] += 1
    if sha(vl.get("value")) != sha(vc.get("value")):
        mismatch.append((key, vl.get("version"), vc.get("version"), dv, vl.get("ts")))
print(f"有效样本 = {n}")
print("dv 分布:", {k: f"{v}({v/n*100:.1f}%)" for k, v in sorted(dvstat.items(), key=lambda x: str(x[0]))})
print(f"\n★ 两板 value **不一致** 的卡: {len(mismatch)}/{n} = {len(mismatch)/n*100:.1f}%")
for key, lv, cv, dv, ts in mismatch:
    print(f"  dv={dv:>2} local v{lv}/central v{cv}  ts={ts}  {key}")
    sl, vl = fetch(LOCAL, key); sc, vc = fetch(CENTRAL, key)
    a, b = vl.get("value"), vc.get("value")
    if isinstance(a, dict) and isinstance(b, dict):
        only_l = sorted(set(a) - set(b)); only_c = sorted(set(b) - set(a))
        diffk = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        print(f"        仅local有={only_l[:6]}  仅central有={only_c[:6]}  值不同键={diffk[:6]}")
print("\n⇒ 注意：若存在 dv=0 但 value 不同，则「version 相同 ⇒ 内容相同」不成立（两板分叉）。")
