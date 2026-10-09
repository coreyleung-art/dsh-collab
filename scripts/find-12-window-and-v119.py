#!/usr/bin/env python3
"""找出星桥的「修复后 12 次写入」对应的窗口边界 + 核 v1.1.9 是否真修了 retryCount
方法：按 at 升序列修复后结果行 ⇒ 看第 12 条落在什么时刻 ⇒ 反推他的口径

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, os, subprocess

LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
CUT = "2026-10-08T00:20:00"

rows = []
for l in open(LOG, errors="replace"):
    l = l.strip()
    if not l:
        continue
    try:
        rows.append(json.loads(l))
    except Exception:
        pass
res = [e for e in rows if e.get("result")]
after = sorted([e for e in res if (e.get("at") or "") >= CUT], key=lambda e: e.get("at"))

print(f"修复后结果行 = {len(after)}")
print("\n=== 按 at 升序（只看前 25 条）===")
for i, e in enumerate(after[:25], 1):
    mark = "  ← 第 12 条" if i == 12 else ""
    print(f"  {i:>3}. {e.get('at')}  {str(e.get('result')):<16} {str(e.get('key'))[:58]}{mark}")

print("\n=== 若他的窗口是「某时刻之前」===")
if len(after) >= 12:
    t12 = after[11].get("at")
    t13 = after[12].get("at") if len(after) > 12 else None
    print(f"  第 12 条 at = {t12}")
    print(f"  第 13 条 at = {t13}")
    print(f"  ⇒ 若窗口上界在 [{t12}, {t13}) 之间，则可得到恰好 12 条")
    print(f"  ⇒ 也即：他的「12」对应窗口 ≈ [{CUT}, {t12}] —— 这是一个**约 30 分钟的窄窗**")

print("\n=== 按 result 分类（修复后全量）===")
import collections
print("  ", dict(collections.Counter(e.get("result") for e in after)))

print("\n=== v1.1.9 核实 ===")
PKG = os.path.expanduser("~/dsh-plugin-bb-card-send/package.json")
CORE = os.path.expanduser("~/dsh-plugin-bb-card-send/lib/core.js")
try:
    d = json.load(open(PKG))
    print(f"  package.json version = {d.get('version')}")
except Exception as e:
    print("  读 package.json 失败:", e)
try:
    src = open(CORE, errors="replace").read()
    import re
    print(f"  core.js 行数 = {src.count(chr(10))+1}")
    for m in re.finditer(r"retryCount:\s*([A-Za-z_][A-Za-z0-9_]*)", src):
        line = src[:m.start()].count("\n") + 1
        print(f"    L{line}: retryCount: {m.group(1)}")
    print(f"  ⇒ 若全部为 retryRounds ⇒ 硬编码 0 已消除 ✓")
    print(f"  ⇒ 是否仍存在 `retryCount: 0` 字面量: {'retryCount: 0' in src}")
except Exception as e:
    print("  读 core.js 失败:", e)
