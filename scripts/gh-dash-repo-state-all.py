#!/usr/bin/env python3
"""★ 核实星桥的提醒：判「曾有过 issue」必须 state=all（open_issues_count 只含未解决）
对象：GitHub 仓「-」（coreyleung-art/-），关系到一条不可逆操作（删仓审批）
谓词必须分开数：open / closed / all；且 GitHub 的 issues API 会混入 PR（有 pull_request 字段）
"""
import subprocess, json

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/gh-dash-repo-state-all.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

REPO = "coreyleung-art/-"

# ★ 应用刚学到的规则：「命令找不到」是观测面缺陷，不是对象的事实 ⇒ 先去找全路径
import os, glob
GH = "gh"
for cand in ("/opt/homebrew/bin/gh", "/usr/local/bin/gh", "/usr/bin/gh") + \
            tuple(glob.glob(os.path.expanduser("~/go/bin/gh"))):
    if os.path.isfile(cand) and os.access(cand, os.X_OK):
        GH = cand
        break
print(f"[env] 使用 gh = {GH}   本进程 PATH = {os.environ.get('PATH','')[:120]}")


def gh(args, timeout=60):
    cmd = [GH] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return f"ERR:{type(e).__name__}", str(e)


print("=" * 74)
print("【A】仓元数据：open_issues_count 是什么谓词")
print("=" * 74)
rc, out = gh(["api", f"repos/{REPO}", "--jq",
              "{name,private,created_at,open_issues_count,has_issues,has_wiki,has_discussions,size,archived,fork}"])
print(f"  exit={rc}")
print("  " + out.strip()[:600])

print()
print("=" * 74)
print("【B】★ state=all 逐谓词计数（issue 与 PR 必须分开）")
print("=" * 74)
for state in ("open", "closed", "all"):
    rc, out = gh(["api", f"repos/{REPO}/issues?state={state}&per_page=100", "--paginate",
                  "--jq", "[.[] | select(.pull_request == null)] | length"])
    rc2, out2 = gh(["api", f"repos/{REPO}/issues?state={state}&per_page=100", "--paginate",
                    "--jq", "[.[] | select(.pull_request != null)] | length"])
    print(f"  state={state:<7} issues={out.strip() or '?'}   PRs={out2.strip() or '?'}")

print()
print("=" * 74)
print("【C】releases / wiki / discussions")
print("=" * 74)
for path, label in ((f"repos/{REPO}/releases", "releases"),
                    (f"repos/{REPO}/wiki", "wiki(需鉴权/可能 404)"),
                    (f"repos/{REPO}/discussions", "discussions(可能 404)")):
    rc, out = gh(["api", path, "--jq", "length"])
    print(f"  {label:<28} exit={rc}  值={out.strip()[:80]}")

print()
print("=" * 74)
print("【D】判定")
print("=" * 74)
print("  ⇒ 若 state=all 的 issues/PRs 数 ≠ 0，则「将永久丢失」的措辞**应恢复**（确有物可失）")
print("  ⇒ 若 state=all 也全为 0，则星桥改后的「实测均为 0，无物可失」成立")
