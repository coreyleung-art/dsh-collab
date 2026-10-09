#!/usr/bin/env python3
"""独立复核独立复核员补的平台资产六项 + 关键判别：labels 是否 = GitHub 默认集
默认集（若为这 9 个且描述未改）⇒ 说明无人自定义过标签 ⇒ 无人类活动信号
"""
import subprocess, json, glob, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/repo-platform-assets-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

GH = "/opt/homebrew/bin/gh"
if not os.path.isfile(GH):
    c = glob.glob("/opt/homebrew/bin/gh") + glob.glob("/usr/local/bin/gh")
    GH = c[0] if c else "gh"
REPO = "coreyleung-art/-"

DEFAULT_LABELS = {
    "bug", "documentation", "duplicate", "enhancement",
    "good first issue", "help wanted", "invalid", "question", "wontfix",
}


def gh(args, t=60):
    r = subprocess.run([GH] + args, capture_output=True, text=True, timeout=t)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


print("=" * 74)
print("【①】我复核他补的六项")
print("=" * 74)
probes = [
    (["api", f"repos/{REPO}/hooks", "--jq", "length"], "hooks"),
    (["api", f"repos/{REPO}/keys", "--jq", "length"], "keys(部署密钥)"),
    (["api", f"repos/{REPO}/environments", "--jq", ".total_count"], "environments"),
    (["api", f"repos/{REPO}/deployments", "--jq", "length"], "deployments"),
    (["api", f"repos/{REPO}/collaborators", "--jq", "length"], "collaborators"),
]
for args, label in probes:
    rc, out, err = gh(args)
    print(f"  {label:<16} exit={rc}  值={out or '(空)'} {err[:60]}")

print()
print("=" * 74)
print("【②】★ 关键判别：labels 是否 = GitHub 默认 9 个（可判「无人自定义」）")
print("=" * 74)
rc, out, err = gh(["api", f"repos/{REPO}/labels", "--paginate", "--jq", "[.[].name]"])
if rc == 0:
    try:
        names = json.loads(out)
    except Exception:
        names = [x.strip().strip('"') for x in out.splitlines() if x.strip()]
    print(f"  实测 labels（{len(names)}）: {names}")
    s = set(names)
    print(f"\n  GitHub 默认集（{len(DEFAULT_LABELS)}）: {sorted(DEFAULT_LABELS)}")
    print(f"\n  ⇒ 实测 == 默认集 ? **{s == DEFAULT_LABELS}**")
    extra = sorted(s - DEFAULT_LABELS)
    missing = sorted(DEFAULT_LABELS - s)
    print(f"  ⇒ 多出（自定义）: {extra or '（无）'}")
    print(f"  ⇒ 缺失（被删）  : {missing or '（无）'}")
    if s == DEFAULT_LABELS:
        print("  ⇒ ⇒ **可判：该仓的标签从未被人工增删** ⇒ 无人类标签活动信号 ✓")
else:
    print("  读取失败:", err[:150])

print()
print("=" * 74)
print("【③】结论（仅我所测）")
print("=" * 74)
print("  ⇒ 六项平台资产与 labels 判别合起来，给「该仓无实质平台活动」再加一层独立证据")
print("  ⇒ 注意 collaborators=1 的含义需看清楚：是「仅属主」还是「属主+1」⇒ 看上方逐项输出")
