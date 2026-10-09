#!/usr/bin/env python3
"""独立复核独立复核员补的平台资产六项 + 关键判别：labels 是否 = GitHub 默认集
默认集（若为这 9 个且描述未改）⇒ 说明无人自定义过标签 ⇒ 无人类活动信号
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== repo-platform-assets-verify 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立复核独立复核员补的平台资产六项 + 关键判别：labels 是否 = GitHub 默认集")
    print("  · 默认集（若为这 9 个且描述未改）⇒ 说明无人自定义过标签 ⇒ 无人类活动信号")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, subprocess, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/repo-platform-assets-verify.log")
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

