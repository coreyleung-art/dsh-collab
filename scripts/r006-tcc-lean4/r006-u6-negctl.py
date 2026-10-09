#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-u6-negctl.py — canonical 块【能不能红】的负控矩阵。

判据（本线口径）：**一个判据若没有能让它失败的输入，它就不是判据，是日志。**
故必须实测：给块注入 4 类「应当被拒」的变异，逐条确认 --lean4-check 红，
且红的正是**对应的那一项**（不是随便哪一项红了就算数 —— 那会掩盖判据错位）。

变异（都在 /tmp 的工作副本上做，不碰生产文件）：
  M1 新增危险原语（os.system）            ⇒ A 须红
  M2 新增越界常量写入（open(...,'w')）     ⇒ E 须红（并触发写入面变更检测）
  M3 新增别名形式的外部命令（sp.Popen）    ⇒ F 须红（★ 别名逃逸检测）
  M4 把扫描器改成恒返回空（= 扫描器瞎了）   ⇒ A/E/F 须因【反空洞】红
      ★ M4 是核心：没有它，前三项可能靠「扫描器本来就看不见」而假绿。
"""
import os
import re
import sys
import shutil
import subprocess

SRC = os.path.expanduser("~/dsh-collab/scripts/gate-canfail.py")
WORK = "/tmp/r006/negctl"

M1 = '\nimport os as _n1\n_n1.system("echo r006-negctl-should-be-detected")\n'
M2 = '\n_ = open("/etc/r006-negctl-outside-roots", "w")\n'
M3 = '\nimport subprocess as _n3\n_n3.Popen(["true"])\n'
M4_OLD = '    r = {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}\n    try:'
M4_NEW = '    return {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}\n    try:'

CASES = [("M1 新增危险原语 os.system", M1, "danger", True),
         ("M2 新增越界常量写入", M2, "write", True),
         ("M3 别名形式外部命令", M3, "exec", True),
         ("M4 扫描器致盲（反空洞）", "BLIND", "anti-vacuous", True)]


def build(name, mut):
    p = os.path.join(WORK, name)
    s = open(SRC, encoding="utf-8").read()
    if mut == "BLIND":
        if M4_OLD not in s:
            return None, "锚点未命中：扫描器首行变了（须同步更新负控）"
        s = s.replace(M4_OLD, M4_NEW, 1)
    else:
        s = s + mut
    open(p, "w", encoding="utf-8").write(s)
    return p, ""


def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    bad = 0
    for i, (name, mut, expect, _) in enumerate(CASES, 1):
        p, err = build("neg%d.py" % i, mut)
        if p is None:
            print("  ⏭  %s — %s" % (name, err))
            bad += 1
            continue
        r = subprocess.run([sys.executable, p, "--lean4-check"], capture_output=True,
                           text=True, timeout=120, cwd=WORK)
        rows = [l for l in r.stdout.splitlines() if re.match(r"^\s+(OK|FAIL)\s+[A-F]\s", l)]
        failed = [l.split()[1] for l in rows if "FAIL" in l]
        ctrl = [l for l in r.stdout.splitlines() if "反空洞" in l]
        ok = (r.returncode == 1)
        note = "rc=%s 红项=%s" % (r.returncode, ",".join(failed) or "无")
        if expect == "anti-vacuous":
            ok = ok and bool(ctrl) and set(failed) >= {"A", "E", "F"}
            note += " · 反空洞控制已触发=%s" % bool(ctrl)
        elif expect == "danger":
            ok = ok and "A" in failed
        elif expect == "write":
            ok = ok and "E" in failed
        elif expect == "exec":
            ok = ok and "F" in failed
        print("  %s %-26s %s" % ("✅" if ok else "❌", name, note))
        if not ok:
            bad += 1
            print("\n".join("        " + l for l in r.stdout.splitlines()[-8:]))
    print("\n⇒ 负控 %d/%d 通过%s" % (len(CASES) - bad, len(CASES), "" if not bad else " ★ 有负控未通过"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
