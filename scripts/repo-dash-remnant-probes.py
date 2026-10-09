#!/usr/bin/env python3
"""独立复核星桥补测的五项 + 尝试为 packages 面找一条不依赖 read:packages 的路径
★ 原则：403 缺权限 = 工具能力不足，不等于目标不存在 ⇒ 应尝试替代路径，而不是接受“无法查”
"""
import subprocess, json, os, glob

GH = "/opt/homebrew/bin/gh"
if not os.path.isfile(GH):
    cand = glob.glob("/opt/homebrew/bin/gh") + glob.glob("/usr/local/bin/gh")
    GH = cand[0] if cand else "gh"

REPO = "coreyleung-art/-"


def gh(args, t=60):
    r = subprocess.run([GH] + args, capture_output=True, text=True, timeout=t)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


print("=" * 74)
print("【①】仓库元数据六项")
print("=" * 74)
rc, out, err = gh(["api", f"repos/{REPO}", "--jq",
                   "{size,created_at,pushed_at,has_pages,has_wiki,has_discussions,open_issues_count,archived,private,disabled}"])
print(f"  exit={rc}")
print("  ", out or err[:200])

print()
print("=" * 74)
print("【②】deployments / environments")
print("=" * 74)
for path, label, jq in ((f"repos/{REPO}/deployments", "deployments", "length"),
                        (f"repos/{REPO}/environments", "environments", ".total_count")):
    rc, out, err = gh(["api", path, "--jq", jq])
    print(f"  {label:<14} exit={rc}  值={out or '(空)'}  err={err[:120]}")

print()
print("=" * 74)
print("【③】★ packages 面：试多条路径")
print("=" * 74)
probes = [
    (["api", f"repos/{REPO}/packages?package_type=container", "--jq", "length"], "仓库级 container packages"),
    (["api", f"repos/{REPO}/packages?package_type=npm", "--jq", "length"], "仓库级 npm packages"),
    (["api", f"orgs/coreyleung-art/packages?package_type=container", "--jq", "length"], "组织级 container packages"),
    (["api", f"users/coreyleung-art/packages?package_type=container", "--jq", "length"], "用户级 container packages"),
    (["api", "/user/packages?package_type=container", "--jq", "length"], "/user packages（需 read:packages）"),
]
for args, label in probes:
    rc, out, err = gh(args)
    verdict = out if rc == 0 else f"exit={rc} {err[:90]}"
    print(f"  {label:<32} -> {verdict}")

print()
print("=" * 74)
print("【④】换一条不依赖 token 权限的路径：网页")
print("=" * 74)
print("  尝试 URL（需人工/另一位用 read_url 工具）：")
print(f"    https://github.com/{REPO}/packages")
print(f"    https://github.com/orgs/coreyleung-art/packages")
print("  ⇒ 注意：仓库为 private ⇒ 网页可能被登录墙阻挡（login wall 不可访问）")
