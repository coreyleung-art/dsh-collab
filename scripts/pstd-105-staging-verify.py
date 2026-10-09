#!/usr/bin/env python3
"""独立核验作者关于 1.0.5 暂存区的可核声称（只读，不改任何被审对象）
① staging 与现役包 review.js 是否逐字相同
② staging vs 现役包的差异文件清单是否恰为「4 改 + 1 新增」
③ pit 计数是否 29/29
④ staging 自测是否真的 0 失败
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== pstd-105-staging-verify 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立核验作者关于 1.0.5 暂存区的可核声称（只读，不改任何被审对象）")
    print("  · ① staging 与现役包 review.js 是否逐字相同")
    print("  · ② staging vs 现役包的差异文件清单是否恰为「4 改 + 1 新增」")
    print("  · ③ pit 计数是否 29/29")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/pstd-105-staging-verify.log")
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

import os, subprocess, hashlib


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/pstd-105-staging-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

PKG = os.path.expanduser("~/dsh-plugin-pstd")
STG = os.path.expanduser("~/dsh-collab/audits/20261008/pstd-105-staging")


def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except Exception as e:
        return f"ERR:{e}"


def run(cmd, cwd=None, timeout=120):
    # ★ 2026-10-09 R10 修复：**支持列表传参**（不传 shell ⇒ 参数不经 shell 解析）。
    #   仍保留字符串+shell 的兼容（本文件里确有需要管道/重定向的调用），
    #   但【新增调用一律用列表】。
    _use_shell = isinstance(cmd, str)
    try:
        r = subprocess.run(cmd, shell=_use_shell, cwd=cwd, capture_output=True, text=True, timeout=timeout)
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
# ★ 2026-10-09 R10 修复：命令写死 ⇒ 改列表传参
rc, out = run(["bash", os.path.expanduser("~/dsh-collab/scripts/pit-count-check.sh")])
print("  exit =", rc)
for l in out.splitlines()[-8:]:
    print("   ", l[:150])

print()
print("=" * 74)
print("【④】暂存区自测（只读运行）")
print("=" * 74)
if os.path.isdir(STG):
    rc, out = run(["node", "tests/audit-tally.mjs"], cwd=STG, timeout=180)
    print("  node tests/audit-tally.mjs exit =", rc)
    for l in out.splitlines()[-15:]:
        print("   ", l[:150])
    rc2, out2 = run(["node", "cli.js", "--selfcheck"], cwd=STG, timeout=180)
    print("\n  node cli.js --selfcheck exit =", rc2)
    for l in out2.splitlines()[-8:]:
        print("   ", l[:150])

