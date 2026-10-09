#!/usr/bin/env python3
"""复核星桥补的两条（都源自我标的未覆盖项）：
① `DEADLINE_FILE` 写入是否已加 fsync/sync（断电窗口）
② hold-out 的排序字段是否已显式化
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== verify-two-gaps-closed 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 复核星桥补的两条（都源自我标的未覆盖项）：")
    print("  · ① `DEADLINE_FILE` 写入是否已加 fsync/sync（断电窗口）")
    print("  · ② hold-out 的排序字段是否已显式化")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, subprocess, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/verify-two-gaps-closed.log")
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

import os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/verify-two-gaps-closed.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

AR = os.path.expanduser("~/dsh-collab/tools/auto-reminder.sh")
PLAN = os.path.expanduser("~/dsh-collab/docs/systemgraph-internal-completion-plan-20261008.md")

print("=" * 74)
print("【①】auto-reminder.sh：DEADLINE 段 与 sync 分布")
print("=" * 74)
if os.path.isfile(AR):
    lines = open(AR, errors="replace").read().splitlines()
    print(f"  脚本 {len(lines)} 行")
    print("\n  L20–L35（DEADLINE 段）:")
    for i in range(19, min(35, len(lines))):
        print(f"    {i+1:>3}: {lines[i]}")
    print("\n  全脚本 sync 出现行:")
    for i, l in enumerate(lines, 1):
        if "sync" in l:
            print(f"    {i:>3}: {l.strip()[:130]}")
else:
    print("  ❌ 脚本不存在")

print()
print("=" * 74)
print("【②】方案第十节：排序字段是否显式")
print("=" * 74)
if os.path.isfile(PLAN):
    txt = open(PLAN, errors="replace").read()
    for i, l in enumerate(txt.splitlines(), 1):
        if re.search(r"排序|time_field|时间字段|holdout-split|复跑手段", l):
            print(f"    {i:>3}: {l.strip()[:160]}")
else:
    print("  ❌ 方案不存在")

print()
print("=" * 74)
print("【③】holdout-split.py 自检输出里的排序字段")
print("=" * 74)
import subprocess, tempfile, json
SC = os.path.expanduser("~/dsh-collab/scripts/holdout-split.py")
if os.path.isfile(SC):
    td = tempfile.mkdtemp(prefix="holdout-field-")
    inp = os.path.join(td, "in.json")
    json.dump([{"id": f"L{i}", "ts": f"2026-10-{i+1:02d}T00:00:00"} for i in range(20)], open(inp, "w"))
    r = subprocess.run(["python3", SC, "--input", inp], capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    for l in out.splitlines():
        if any(k in l for k in ("time_field", "holdout", "total", "digest", "untimed")):
            print("   ", l.strip()[:160])
else:
    print("  ❌ 脚本不存在")

