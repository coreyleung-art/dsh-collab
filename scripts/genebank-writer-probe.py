#!/usr/bin/env python3
"""独立复核作者给出的 genebank 成因：kb-genebank-watch (launchd) + rust-genebank:8801
核点：① plist 是否存在及其调度；② 进程/端口是否在；③ 04 点批量入库的规模是否与实测吻合
"""
import os, glob, subprocess, json, urllib.request, collections

print("=" * 74)
print("【①】launchd plist")
print("=" * 74)
pats = [os.path.expanduser("~/Library/LaunchAgents/*genebank*"),
        os.path.expanduser("~/Library/LaunchAgents/*kb-*"),
        "/Library/LaunchAgents/*genebank*",
        "/Library/LaunchDaemons/*genebank*"]
found = []
for p in pats:
    for f in glob.glob(p):
        found.append(f)
        st = os.stat(f)
        print(f"  ✅ {f}  size={st.st_size}")
        try:
            with open(f, errors="replace") as fh:
                txt = fh.read()
            for line in txt.splitlines():
                s = line.strip()
                if any(k in s for k in ("StartInterval", "StartCalendarInterval", "Label", "Hour", "Minute",
                                        "Program", "StandardOut", "StandardError", "RunAtLoad", "KeepAlive")):
                    print("      ", s[:140])
        except Exception as e:
            print("      读取失败", e)
if not found:
    print("  ❌ 未找到匹配的 plist")

print()
print("=" * 74)
print("【②】进程与端口")
print("=" * 74)
try:
    # ★ 2026-10-09 R10 修复：命令写死 ⇒ 改列表传参（去 shell）
    ps = subprocess.run(["ps", "-eo", "pid,lstart,command"], capture_output=True, text=True).stdout
    hits = [l.strip() for l in ps.splitlines() if "genebank" in l.lower() and "grep" not in l]
    if hits:
        for l in hits:
            print("  ", l[:160])
    else:
        print("  （无 genebank 进程）")
except Exception as e:
    print("  ps 失败", e)
try:
    # ★ 2026-10-09 R10 修复：命令写死 ⇒ 改列表传参（去 shell）
    lsof = subprocess.run(["lsof", "-nP", "-iTCP:8801", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
    print("  端口 8801:", lsof.strip()[:200] or "（未监听）")
except Exception as e:
    print("  lsof 失败", e)

print()
print("=" * 74)
print("【③】notes/genebank 的 04 时批量规模（核实 8511）")
print("=" * 74)
total = None
c = collections.Counter()
off = 0
while True:
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:8792/notes/genebank/?limit=1000&offset={off}", timeout=30)
        d = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  读取失败", e); break
    lst = d.get("list") or {}
    total = d.get("total")
    for v in lst.values():
        c[str(v.get("ts"))[:13]] += 1
    if len(lst) < 1000 or off + 1000 >= (total or 0) or off > 20000:
        break
    off += 1000
print(f"  total = {total}")
print("  按小时（top 8）:")
for k, n in sorted(c.items(), key=lambda x: -x[1])[:8]:
    print(f"    {k}  {n}")
h04 = sum(n for k, n in c.items() if k.endswith("T04"))
print(f"\n  04 时合计（本次枚举范围）= {h04}")
print("  作者声称：今日 04 点批量入库 8511 键")


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/genebank-writer-probe.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass
