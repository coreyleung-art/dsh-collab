#!/usr/bin/env python3
"""便宜且射程正确的做法：用【顶层命名空间 total】做两板对比（只 6 次请求）
不枚举全量键名（那个要约 63k 条、数百次请求，且会把键名误当前缀）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"


def total(base, ns, t=25):
    try:
        r = urllib.request.urlopen(f"{base}{ns}/?limit=1", timeout=t)
        d = json.loads(r.read().decode("utf-8", "replace"))
        return d.get("total")
    except urllib.error.HTTPError as e:
        return f"HTTP{e.code}"
    except Exception as e:
        return f"ERR:{type(e).__name__}"


print("=== 顶层命名空间两板 total 对比（射程 = 整块板）===")
print(f"{'顶层':<12}{'local':>10}{'central':>10}{'差':>10}")
tl_sum = tc_sum = 0
for ns in ("notes", "data", "tasks"):
    a = total(LOCAL, ns)
    b = total(CENTRAL, ns)
    diff = (a - b) if isinstance(a, int) and isinstance(b, int) else "?"
    if isinstance(a, int):
        tl_sum += a
    if isinstance(b, int):
        tc_sum += b
    print(f"  {ns:<10}{str(a):>10}{str(b):>10}{str(diff):>10}")
print(f"  {'合计':<10}{tl_sum:>10}{tc_sum:>10}{tl_sum-tc_sum:>10}")

print("\n=== 作者反例专项：notes/genebank ===")
for label, base in (("local", LOCAL), ("central", CENTRAL)):
    t = total(base, "notes/genebank")
    print(f"  {label:<8} total = {t}")
    try:
        r = urllib.request.urlopen(f"{base}notes/genebank/?limit=1000", timeout=30)
        d = json.loads(r.read().decode("utf-8", "replace"))
        lst = d.get("list") or {}
        if lst:
            today = sum(1 for v in lst.values() if str(v.get("ts", "")).startswith("2026-10-08"))
            h04 = sum(1 for v in lst.values() if str(v.get("ts", "")).startswith("2026-10-08T04"))
            print(f"           本页 {len(lst)} 条中：今日 {today} 条、其中 04 时 {h04} 条")
            ts = sorted(str(v.get("ts")) for v in lst.values())
            print(f"           ts 范围 {ts[0]} .. {ts[-1]}")
    except Exception as e:
        print(f"           明细读取失败 {e}")

print("\n=== 对照：notes/mac-mini（我先前结论的作用域）===")
for label, base in (("local", LOCAL), ("central", CENTRAL)):
    print(f"  {label:<8} total = {total(base, 'notes/mac-mini')}")
