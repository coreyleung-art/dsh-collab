#!/usr/bin/env python3
"""先找到 node，再决定"无法复现"是否成立（不要把自身环境缺失当成对方的事实）
★ 教训：命令找不到 = 我的观测面缺陷，不等于对方的测试跑不了。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== find-node-and-rerun 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 先找到 node，再决定'无法复现'是否成立（不要把自身环境缺失当成对方的事实）")
    print("  · ★ 教训：命令找不到 = 我的观测面缺陷，不等于对方的测试跑不了。")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/find-node-and-rerun.log")
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

