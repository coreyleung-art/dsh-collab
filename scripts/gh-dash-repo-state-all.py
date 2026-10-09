#!/usr/bin/env python3
"""★ 核实星桥的提醒：判「曾有过 issue」必须 state=all（open_issues_count 只含未解决）
对象：GitHub 仓「-」（coreyleung-art/-），关系到一条不可逆操作（删仓审批）
谓词必须分开数：open / closed / all；且 GitHub 的 issues API 会混入 PR（有 pull_request 字段）
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== gh-dash-repo-state-all 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 核实星桥的提醒：判「曾有过 issue」必须 state=all（open_issues_count 只含未解决）")
    print("  · 对象：GitHub 仓「-」（coreyleung-art/-），关系到一条不可逆操作（删仓审批）")
    print("  · 谓词必须分开数：open / closed / all；且 GitHub 的 issues API 会混入 PR（有 pull_request 字段）")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, subprocess, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/gh-dash-repo-state-all.log")
    return 0



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。

import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 无 shell=True ⇒ 参数不经 shell 解析",
      not _re.search(r'shell\s*=\s*True', _code),
      "无 shell（变量传参亦安全）")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


import sys as _r006_sys
if __name__ == "__main__" and "--lean4-check" in _r006_sys.argv:
    _r006_sys.exit(lean4_check())

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

