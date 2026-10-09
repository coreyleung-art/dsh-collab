#!/usr/bin/env python3
"""独立核验作者关于 1.0.5 暂存区的可核声称（只读，不改任何被审对象）
① staging 与现役包 review.js 是否逐字相同
② staging vs 现役包的差异文件清单是否恰为「4 改 + 1 新增」
③ pit 计数是否 29/29
④ staging 自测是否真的 0 失败
"""
import os, subprocess, hashlib

PKG = os.path.expanduser("~/dsh-plugin-pstd")
STG = os.path.expanduser("~/dsh-collab/audits/20261008/pstd-105-staging")


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except Exception as e:
        return f"ERR:{e}"


def run(cmd, cwd=None, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return f"ERR:{type(e).__name__}", str(e)


print("=" * 74)
print("【①】staging 与现役包逐文件比对")
print("=" * 74)
print(f"  现役包 = {PKG}")
print(f"  暂存区 = {STG}  exists={os.path.isdir(STG)}")
if os.path.isdir(STG):
    rc, out = run(f"diff -rq '{PKG}' '{STG}' 2>&1 | grep -v node_modules | grep -v '\\.git'")
    print("  diff -rq 结果（退出码 %s）:" % rc)
    lines = [l for l in out.splitlines() if l.strip()]
    if lines:
        for l in lines:
            print("   ", l[:150])
    else:
        print("    （无差异）")
    n_diff = sum(1 for l in lines if l.startswith("Files "))
    n_only = sum(1 for l in lines if l.startswith("Only in "))
    print(f"\n  ⇒ 内容不同的文件 = {n_diff}；仅一侧存在的条目 = {n_only}")
    print("  作者声称：与现役包 diff 仅 4 文件（lib/fsops.js · lib/index.js · CHANGELOG.md · docs/README.md）+ 新增 tests/audit-tally.mjs")

    a = sha(os.path.join(PKG, "lib/review.js"))
    b = sha(os.path.join(STG, "lib/review.js"))
    print(f"\n  review.js sha16  现役={a}  暂存={b}  ⇒ {'✅ 逐字相同' if a == b else '❌ 不同'}")

    a = sha(os.path.join(PKG, "package.json"))
    b = sha(os.path.join(STG, "package.json"))
    print(f"  package.json sha16  现役={a}  暂存={b}  ⇒ {'逐字相同' if a == b else '不同（看下方版本）'}")
    for tag, root in (("现役", PKG), ("暂存", STG)):
        try:
            import json
            v = json.load(open(os.path.join(root, "package.json"))).get("version")
            print(f"    {tag} version = {v}")
        except Exception as e:
            print(f"    {tag} 读取失败 {e}")
else:
    print("  ❌ 暂存区不存在，后续跳过")

print()
print("=" * 74)
print("【③】pit 计数自检")
print("=" * 74)
rc, out = run("bash ~/dsh-collab/scripts/pit-count-check.sh")
print("  exit =", rc)
for l in out.splitlines()[-8:]:
    print("   ", l[:150])

print()
print("=" * 74)
print("【④】暂存区自测（只读运行）")
print("=" * 74)
if os.path.isdir(STG):
    rc, out = run("node tests/audit-tally.mjs", cwd=STG, timeout=180)
    print("  node tests/audit-tally.mjs exit =", rc)
    for l in out.splitlines()[-15:]:
        print("   ", l[:150])
    rc2, out2 = run("node cli.js --selfcheck", cwd=STG, timeout=180)
    print("\n  node cli.js --selfcheck exit =", rc2)
    for l in out2.splitlines()[-8:]:
        print("   ", l[:150])
