#!/usr/bin/env python3
"""先找到 node，再决定"无法复现"是否成立（不要把自身环境缺失当成对方的事实）
★ 教训：命令找不到 = 我的观测面缺陷，不等于对方的测试跑不了。
"""
import os, subprocess, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/find-node-and-rerun.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CANDIDATES = []
for base in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/opt/local/bin"):
    CANDIDATES.append(os.path.join(base, "node"))
CANDIDATES += glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/node"))
CANDIDATES += glob.glob(os.path.expanduser("~/.volta/bin/node"))
CANDIDATES += glob.glob(os.path.expanduser("~/Library/pnpm/node"))
CANDIDATES += glob.glob("/Applications/CLD.app/Contents/Resources/dsh-runtime/**/node", recursive=True)
CANDIDATES += glob.glob("/Applications/CLD.app/Contents/**/node", recursive=True)

print("=== node 候选位置探测 ===")
found = None
for c in CANDIDATES:
    if os.path.isfile(c) and os.access(c, os.X_OK):
        print(f"  ✅ 可执行: {c}")
        if found is None:
            found = c
    elif os.path.isfile(c):
        print(f"  ⚠ 存在但不可执行: {c}")

print(f"\n  which node (shell) -> ", end="")
# ★ 2026-10-09 R10 修复：原 shell=True 仅为重定向 `2>&1`；命令写死 ⇒ 改列表传参
r = subprocess.run(["which", "node"], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())

print("\n  PATH =", os.environ.get("PATH", "")[:300])

if found:
    print(f"\n=== 用 {found} 跑暂存区自测 ===")
    STG = os.path.expanduser("~/dsh-collab/audits/20261008/pstd-105-staging")
    # ★ 2026-10-09 R10 修复：原为 f-string 拼接 + shell ⇒ 改列表传参
    for cmd in ([found, "tests/audit-tally.mjs"], [found, "cli.js", "--selfcheck"]):
        r = subprocess.run(cmd, cwd=STG, capture_output=True, text=True, timeout=180)
        print(f"\n  $ {cmd}")
        print(f"    exit = {r.returncode}")
        out = (r.stdout or "") + (r.stderr or "")
        for l in out.splitlines()[-14:]:
            print("     ", l[:150])
else:
    print("\n  ⇒ 未在常见位置找到 node ⇒ 我方**无法独立复现**该自测")
    print("     ★ 但这**不能**推断「作者的测试未通过」——他只是可能在自己的环境里跑通了")
