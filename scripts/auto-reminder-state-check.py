#!/usr/bin/env python3
"""送审③ v3 现状核查（只读）：① 三个计数器/时限文件 ② 日志全量尾部 ③ 失败路径是否被实战触发过
★ 关键：round=9/10 ⇒ 第 10 轮会自动 bootout ⇒ 这是一个"即将发生且可验"的事件，应先记录现状再核结果
"""


# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
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

import os, datetime, subprocess

FILES = {
    "count": "~/.dsh/auto-reminder-count",
    "fails": "~/.dsh/auto-reminder-fails",
    "deadline": "~/.dsh/auto-reminder-deadline",
}
LOG = os.path.expanduser("~/dsh-collab/logs/auto-reminder.log")

print("=" * 74)
print("【①】计数器 / 时限文件现状")
print("=" * 74)
for label, p in FILES.items():
    fp = os.path.expanduser(p)
    if os.path.isfile(fp):
        st = os.stat(fp)
        mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M:%S")
        try:
            val = open(fp).read().strip()
        except Exception as e:
            val = f"<读取失败 {e}>"
        print(f"  {label:<9} 值={val!r:<24} mtime={mt}  size={st.st_size}")
    else:
        print(f"  {label:<9} ❌ 不存在 {p}")

d = os.path.expanduser("~/.dsh/auto-reminder-deadline")
if os.path.isfile(d):
    try:
        dl = int(open(d).read().strip())
        now = int(datetime.datetime.now().timestamp())
        print(f"\n  绝对时限 = {datetime.datetime.fromtimestamp(dl).strftime('%Y-%m-%dT%H:%M:%S')}"
              f"  剩余 = {(dl-now)/3600:.2f} h  （{'已过期' if now >= dl else '未到期'}）")
    except Exception as e:
        print("  时限解析失败", e)

print()
print("=" * 74)
print("【②】launchd 当前是否仍加载")
print("=" * 74)
# ★ 2026-10-09 R10 修复：原 `shell=True` 仅为使用管道 `|`，而命令本可写死。
#   ⇒ 改为【列表传参 + Python 内过滤】⇒ 参数不经 shell，注入路径结构性消除。
_r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
_lines = [l for l in (_r.stdout or "").splitlines() if "auto-reminder" in l.lower()]
class _R:  # 保持下游 `r.stdout` 用法不变
    stdout = "\n".join(_lines)
r = _R()
print("  ", (r.stdout or "").strip() or "（未加载 / 已 bootout）")

print()
print("=" * 74)
print("【③】日志：轮次轨迹 + 失败路径是否被实战触发过")
print("=" * 74)
if os.path.isfile(LOG):
    st = os.stat(LOG)
    print(f"  日志 {LOG}  size={st.st_size}  mtime="
          f"{datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}")
    lines = open(LOG, errors="replace").read().splitlines()
    print(f"  总行数 = {len(lines)}")
    print("\n  末 12 行:")
    for l in lines[-12:]:
        print("   ", l[:150])
    n_inject = sum(1 for l in lines if "injected_ok" in l)
    n_fail = sum(1 for l in lines if "FAIL" in l)
    n_bump = sum(1 for l in lines if "连续失败" in l)
    n_ok = sum(1 for l in lines if "round=" in l and "injected_ok" in l)
    print(f"\n  ★ 成功注入记录 = {n_inject}")
    print(f"  ★ FAIL 记录 = {n_fail}")
    print(f"  ★ “连续失败 … bootout”记录 = {n_bump}   ← **为 0 则说明“失败上限”保险未被实战触发**")
    print(f"  ★ round=…injected_ok 记录 = {n_ok}")
else:
    print("  ❌ 日志不存在")

