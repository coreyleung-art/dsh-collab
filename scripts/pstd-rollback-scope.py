#!/usr/bin/env python3
"""回退范围取证：落地 1.0.5 后若要回退到 1.0.4，需要还原哪些文件？
（用 Python 逐文件比对，避开 diff -rq 在 node_modules 上的耗时）
"""
import os, hashlib

PKG = os.path.expanduser("~/dsh-plugin-pstd")
STG = os.path.expanduser("~/dsh-collab/audits/20261008/pstd-105-staging")
SKIP = {"node_modules", ".git", ".cargo", "target", "dist"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def walk(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, root)] = sha(p)
    return out


a = walk(PKG)
b = walk(STG)
only_a = sorted(set(a) - set(b))
only_b = sorted(set(b) - set(a))
diff = sorted(k for k in set(a) & set(b) if a[k] != b[k])

print("=" * 74)
print("【回退范围】现役包（1.0.4） vs 暂存区（1.0.5）")
print("=" * 74)
print(f"  现役包文件数={len(a)}  暂存区文件数={len(b)}")
print(f"\n  ★ 内容不同（{len(diff)}）—— 回退时【必须还原】:")
for k in diff:
    print(f"     {k}   现役={a[k]}  暂存={b[k]}")
print(f"\n  ★ 仅暂存区有（{len(only_b)}）—— 回退时【需删除】:")
for k in only_b:
    print(f"     {k}")
print(f"\n  ★ 仅现役包有（{len(only_a)}）—— 回退时【需保留】:")
for k in only_a:
    print(f"     {k}")

print()
print("=" * 74)
print("【1.0.4 快照是否存在】回退的前提")
print("=" * 74)
cands = [
    os.path.expanduser("~/dsh-collab/audits/20261008/pstd-104-snapshot"),
    os.path.expanduser("~/dsh-collab/guard/backups"),
    os.path.expanduser("~/dsh-plugin-pstd.104.bak"),
]
for c in cands:
    print(f"  {c}  exists={os.path.exists(c)}")
# guard/backups 下找与 pstd 相关的
gb = os.path.expanduser("~/dsh-collab/guard/backups")
if os.path.isdir(gb):
    hits = [n for n in os.listdir(gb) if "pstd" in n.lower()]
    print(f"\n  guard/backups 内含 pstd 的条目 = {len(hits)}")
    for h in hits[:10]:
        print("   ", h)
else:
    print("\n  guard/backups 不存在")

print()
print("=" * 74)
print("【结论】")
print("=" * 74)
print(f"  回退 1.0.5 → 1.0.4 需要：**还原 {len(diff)} 个文件 + 删除 {len(only_b)} 个新增文件**")
print("  ⇒ 不是“只还原 package.json”：单改 version 会造出")
print("     【版本号 1.0.4 + 代码 1.0.5】的混合态 ⇒ 比不回退更糟（版本↔内容绑定被打破）")
print("  ⇒ 而现役包**现在就是 1.0.4** ⇒ 落地前做一个完整快照，回退才真的是“还原 + 重启”")
