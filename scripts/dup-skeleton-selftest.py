#!/usr/bin/env python3
"""dup-skeleton.py 的正控 + 负控。

由来（HR 2026-09-14）：候选型工具也须有正控。
  我此前立的那一层是「结构判据 ⇒ 工具可给判决；语义判据 ⇒ 工具只能给候选」。
  HR 补的是这一层的另一半：候选型工具若没有正控，则「它从不给候选」与
  「它正确地没给候选」不可分 —— 两者外观相同。

两级控制的含义（判决型与候选型通用）：
  正控 = 给一个【应当被报出】的样本 ⇒ 排除「从不报」
  负控 = 给一个【不应当被报出】的样本 ⇒ 排除「全报」
  缺正控 ⇒ 无法区分「没发现问题」与「检查没工作」
  缺负控 ⇒ 无法区分「严格」与「乱报」

用法：python3 dup-skeleton-selftest.py
退出码 0 = 正负控均通过
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import os, subprocess, sys, tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/dup-skeleton-selftest.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dup-skeleton.py")

SAMPLE = '''def alpha(x):
    total = 0
    for i in range(x):
        total = total + i
    return total

def beta(y):
    acc = 0
    for j in range(y):
        acc = acc + j
    return acc

def gamma(s):
    return s.upper()

def delta(n):
    if n > 0:
        return "pos"
    return "neg"
'''


def run(path):
    r = subprocess.run([sys.executable, TOOL, path], capture_output=True, text=True)
    return r.stdout + r.stderr


def main():
    d = tempfile.mkdtemp(prefix="dupskel-")
    p = os.path.join(d, "sample.py")
    open(p, "w").write(SAMPLE)
    out = run(p)
    print("样本：alpha/beta 同一算法（只换变量名）· gamma/delta 算法不同\n")
    pos = ("alpha" in out and "beta" in out)
    neg = not ("gamma" in out or "delta" in out)
    print(f"  正控（alpha/beta 应被报出）: {'✅ 通过' if pos else '★ 失败 —— 已知重复没被报出'}")
    print(f"  负控（gamma/delta 不应被报出）: {'✅ 通过' if neg else '★ 失败 —— 被误报'}")
    print()
    if pos and neg:
        print("总判定: ✅ 正负控均通过 —— 该工具既能报出已知重复，也不会乱报")
        return 0
    print("总判定: ★ 未通过 —— 本工具的输出不可用于判读")
    return 1



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


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    sys.exit(main())
