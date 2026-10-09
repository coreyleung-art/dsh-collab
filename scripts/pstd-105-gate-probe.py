#!/usr/bin/env python3
"""本轮取证：① 读作者卡 ② 查 PSTD 包状态（版本/暂存区/CHANGELOG/进程启动时刻）
目的：给「1.0.5 可否落地」构造可核前置条件清单（不代裁）
"""
import json, os, subprocess, datetime, glob, urllib.request

PKG = os.path.expanduser("~/dsh-plugin-pstd")
CARD = "notes/mac-mini/pstd-105-staged-and-changelog-selfcontradiction-20261008"

print("=" * 74)
print("【A】作者卡")
print("=" * 74)
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8792/" + CARD, timeout=25))
    v = d["value"]
    print("ts =", d.get("ts"), "| version =", d.get("version"))
    print("subject:", v.get("subject"))
    for k, val in v.items():
        if k in ("subject", "from", "from_label", "to"):
            continue
        if isinstance(val, (dict, list)):
            print(f"\n[{k}]")
            print("  " + json.dumps(val, ensure_ascii=False)[:1600])
        else:
            print(f"\n[{k}]\n  {str(val)[:900]}")
except Exception as e:
    print("读卡失败:", e)

print()
print("=" * 74)
print("【B】PSTD 包状态")
print("=" * 74)
try:
    pj = json.load(open(os.path.join(PKG, "package.json")))
    st = os.stat(os.path.join(PKG, "package.json"))
    print(f"  package.json version = {pj.get('version')}  mtime = "
          f"{datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}")
except Exception as e:
    print("  读 package.json 失败:", e)

for f in ("lib/review.js", "CHANGELOG.md"):
    p = os.path.join(PKG, f)
    if os.path.isfile(p):
        st = os.stat(p)
        print(f"  {f:<18} mtime = {datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}  size={st.st_size}")
    else:
        print(f"  {f:<18} 不存在")

print("\n  目录顶层:")
for n in sorted(os.listdir(PKG)):
    if n in ("node_modules", ".git"):
        continue
    p = os.path.join(PKG, n)
    kind = "dir " if os.path.isdir(p) else "file"
    print(f"    {kind} {n}")

print("\n  CHANGELOG 前 40 行:")
try:
    with open(os.path.join(PKG, "CHANGELOG.md"), errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            if i > 40:
                break
            print("   ", line.rstrip()[:120])
except Exception as e:
    print("   读取失败:", e)

print()
print("=" * 74)
print("【C】进程/重启状态（决定 1.0.4 的 ③ 判据是否触发）")
print("=" * 74)
try:
    boot = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True, text=True).stdout
    print("  boot:", boot.strip())
except Exception as e:
    print("  boot 读取失败:", e)
try:
    ps = subprocess.run(["ps", "-eo", "pid,lstart,command"], capture_output=True, text=True).stdout
    for line in ps.splitlines():
        if "dsh/lib/bin.js" in line or "MacOS/CLD" in line:
            print("  ", line.strip()[:150])
except Exception as e:
    print("  ps 失败:", e)
try:
    st = os.stat(os.path.join(PKG, "lib/review.js"))
    print("  review.js mtime =", datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M:%S"))
    print("  ⇒ 判据 F2（重启时刻 > review.js mtime）：须 boot 晚于该 mtime")
except Exception as e:
    print("  review.js stat 失败:", e)
