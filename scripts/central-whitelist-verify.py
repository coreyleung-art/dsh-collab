#!/usr/bin/env python3
"""★★★ 决定性验证：中央板的键是否恰好落在「上行域白名单」内
机制来源：comm-server/comm_domains.py 的 UP_DOMAINS + OTHER_UP
          → sync-to-central.py:57 `if not any(key.startswith(p) for p in UP_PREFIXES): continue`
判据：若中央板存在【不在白名单】的键 ⇒ 机制不完整（有反例）；若全部在内 ⇒ 机制成立。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import sys, os, json, urllib.request, urllib.error, collections

sys.path.insert(0, os.path.expanduser("~/dsh-collab/comm-server"))
try:
    import comm_domains as CD
    PREFIXES = CD.up_domains_as_prefixes()
    print("=== 上行域白名单（源码单源）===")
    for p in PREFIXES:
        print("   ", p)
except Exception as e:
    print("导入 comm_domains 失败:", e)
    PREFIXES = ()

CENTRAL = "http://106.53.214.108:8792/"


def fetch(url, t=30):
    try:
        r = urllib.request.urlopen(url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


print()
print("=== 拉取中央板全部键（notes/ data/ tasks/）===")
allkeys = []
for root in ("notes", "data", "tasks"):
    off = 0
    got = 0
    while True:
        s, d = fetch(f"{CENTRAL}{root}/?limit=1000&offset={off}")
        if not isinstance(d, dict):
            print(f"  {root}/ 读取失败 http={s}")
            break
        lst = d.get("list") or {}
        allkeys.extend(lst.keys())
        got += len(lst)
        if len(lst) < 1000 or got >= d.get("total", 0):
            break
        off += 1000
    print(f"  {root}/ = {got}")

print(f"\n中央板键总数 = {len(allkeys)}")

inwl = [k for k in allkeys if any(k.startswith(p) for p in PREFIXES)]
outwl = [k for k in allkeys if not any(k.startswith(p) for p in PREFIXES)]
print(f"  ★ 在白名单内 = {len(inwl)} ({len(inwl)/len(allkeys)*100:.1f}%)")
print(f"  ★ 在白名单外 = {len(outwl)} ({len(outwl)/len(allkeys)*100:.1f}%)")

print()
print("=== 中央板键的二级命名空间分布 ===")
c = collections.Counter()
for k in allkeys:
    parts = k.split("/")
    c["/".join(parts[:2]) + "/"] += 1
for ns, n in c.most_common(25):
    flag = "✅在册" if any(ns.startswith(p) or p.startswith(ns) for p in PREFIXES) else "❌不在册"
    print(f"  {ns:<34}{n:>7}  {flag}")

if outwl:
    print()
    print("=== ⚠️ 不在白名单的键（若有，即机制反例）前 20 ===")
    for k in outwl[:20]:
        print("   ", k)

print()
print("=== 结论 ===")
if not outwl:
    print("  ✅ 中央板的键**全部**落在上行域白名单内 ⇒ 「域白名单决定哪些键上中央」机制成立")
else:
    pct = len(outwl) / len(allkeys) * 100
    print(f"  ⚠️ 有 {len(outwl)} 个键（{pct:.1f}%）不在白名单 ⇒ 机制不完整，需查其他推送路径")
