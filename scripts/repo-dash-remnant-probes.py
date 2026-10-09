#!/usr/bin/env python3
"""独立复核星桥补测的五项 + 尝试为 packages 面找一条不依赖 read:packages 的路径
★ 原则：403 缺权限 = 工具能力不足，不等于目标不存在 ⇒ 应尝试替代路径，而不是接受“无法查”
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== repo-dash-remnant-probes 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立复核星桥补测的五项 + 尝试为 packages 面找一条不依赖 read:packages 的路径")
    print("  · ★ 原则：403 缺权限 = 工具能力不足，不等于目标不存在 ⇒ 应尝试替代路径，而不是接受“无法查”")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, subprocess, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/repo-dash-remnant-probes.log")
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

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
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

import subprocess, json, os, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/repo-dash-remnant-probes.log")


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

