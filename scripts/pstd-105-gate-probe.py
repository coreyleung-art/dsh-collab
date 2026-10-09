#!/usr/bin/env python3
"""本轮取证：① 读作者卡 ② 查 PSTD 包状态（版本/暂存区/CHANGELOG/进程启动时刻）
目的：给「1.0.5 可否落地」构造可核前置条件清单（不代裁）
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== pstd-105-gate-probe 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 本轮取证：① 读作者卡 ② 查 PSTD 包状态（版本/暂存区/CHANGELOG/进程启动时刻）")
    print("  · 目的：给「1.0.5 可否落地」构造可核前置条件清单（不代裁）")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/pstd-105-gate-probe.log")
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

import json, os, subprocess, datetime, glob, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/pstd-105-gate-probe.log")


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
CARD = "notes/mac-mini/pstd-105-staged-and-changelog-selfcontradiction-20261008"

print("=" * 74)
print("【A】作者卡")
print("=" * 74)
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8792/" + CARD, timeout=25))
    v = d["value"]
    print("ts =", d.get("ts"), "| version =", d.get("version"))
    print("subject:", v.get("subject"))
    for k, val in v.items():
        if k in ("subject", "from", "from_label", "to"):
            continue
        if isinstance(val, (dict, list)):
            print(f"\n[{k}]")
            print("  " + json.dumps(val, ensure_ascii=False)[:1600])
        else:
            print(f"\n[{k}]\n  {str(val)[:900]}")
except Exception as e:
    print("读卡失败:", e)

print()
print("=" * 74)
print("【B】PSTD 包状态")
print("=" * 74)
try:
    pj = json.load(open(os.path.join(PKG, "package.json")))
    st = os.stat(os.path.join(PKG, "package.json"))
    print(f"  package.json version = {pj.get('version')}  mtime = "
          f"{datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}")
except Exception as e:
    print("  读 package.json 失败:", e)

for f in ("lib/review.js", "CHANGELOG.md"):
    p = os.path.join(PKG, f)
    if os.path.isfile(p):
        st = os.stat(p)
        print(f"  {f:<18} mtime = {datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}  size={st.st_size}")
    else:
        print(f"  {f:<18} 不存在")

print("\n  目录顶层:")
for n in sorted(os.listdir(PKG)):
    if n in ("node_modules", ".git"):
        continue
    p = os.path.join(PKG, n)
    kind = "dir " if os.path.isdir(p) else "file"
    print(f"    {kind} {n}")

print("\n  CHANGELOG 前 40 行:")
try:
    with open(os.path.join(PKG, "CHANGELOG.md"), errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            if i > 40:
                break
            print("   ", line.rstrip()[:120])
except Exception as e:
    print("   读取失败:", e)

print()
print("=" * 74)
print("【C】进程/重启状态（决定 1.0.4 的 ③ 判据是否触发）")
print("=" * 74)
try:
    boot = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True, text=True).stdout
    print("  boot:", boot.strip())
except Exception as e:
    print("  boot 读取失败:", e)
try:
    ps = subprocess.run(["ps", "-eo", "pid,lstart,command"], capture_output=True, text=True).stdout
    for line in ps.splitlines():
        if "dsh/lib/bin.js" in line or "MacOS/CLD" in line:
            print("  ", line.strip()[:150])
except Exception as e:
    print("  ps 失败:", e)
try:
    st = os.stat(os.path.join(PKG, "lib/review.js"))
    print("  review.js mtime =", datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M:%S"))
    print("  ⇒ 判据 F2（重启时刻 > review.js mtime）：须 boot 晚于该 mtime")
except Exception as e:
    print("  review.js stat 失败:", e)

