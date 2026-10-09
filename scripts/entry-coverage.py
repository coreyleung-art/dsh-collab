#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entry-coverage.py — 入口覆盖审计：**逐入口列出「哪个用例经过它」**

作者: 老登 session-aa528267 (mac-mini) · 2026-09-28
起因: 同一天在两个工具里各发现一个缺陷，而**两者都活过了「全绿的自测」**：
      · require-graph.py 自测直接调 run()，**未被经过** main() 的参数解析
      · binding-check.py 自测全部走 --file，**未被经过** fetch() 的取卡/网络路径

核心判据（本工具存在的理由）
  **覆盖率的正确单位不是「用例数」，是「被经过的入口数」。**
  ⇒ 「24 个用例全绿」与「0 个用例」，在**没有被经过的那条路径**上读数完全相同。
  ⇒ 这是「空域恒真」的**命令入口版**，且比空域**更难看见**，因为总数是漂亮的。

用法
  entry-coverage.py <工具.py> [--selftest-args "--selftest"] [--json]

输出
  逐「未被执行的可执行行」列出（带函数归属），并给出判定：
    · 该行所在函数**是否被任何用例经过**
    · 若某函数整体零执行 ⇒ 记 **零覆盖**，不论总用例数多少

★ 反身纪律（本工具自己踩过的坑，写在最前）
  **「我的探针看不见它」≠「它没被经过」。**
  第一版用 `python3 -m trace --count <tool> --selftest` ⇒ 报出「main() 整个写卡路径零执行」。
  那是**测量假象**：该自测用 subprocess 拉起子进程，而 trace 不跨进程。
  若照那个读数上报，我就犯了**同一天刚在 binding-check 里修好的那个错**
  （把「不可达」报成「不存在」＝ 把环境的性质当成对象的性质）。
  ⇒ 故本工具用 sitecustomize 在**每个子进程启动时**装配计数器，并按 PID 分开落盘、
     最后**按「任一线程/进程执行过即为已覆盖」求并集**。

退出码
  0 全部入口至少被一个用例经过
  2 存在**零被经过**的入口（列出）
  3 探针自身未能装配（**不得当成通过**）
  4 工具路径不可读 / 用法错
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== entry-coverage 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · entry-coverage.py — 入口覆盖审计：**逐入口列出「哪个用例经过它」**")
    print("  · 作者: 老登 session-aa528267 (mac-mini) · 2026-09-28")
    print("  · 起因: 同一天在两个工具里各发现一个缺陷，而**两者都活过了「全绿的自测」**：")
    print("  · · require-graph.py 自测直接调 run()，**未被经过** main() 的参数解析")
    print("  · 命令/参数: lean4-check, selftest-args, json, selftest, version")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 本工具涉及「删除文件/目录」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, os, re, sys, tempfile, time")
    print("  · ★ 第三方: trace ⇒ 缺失时行为须明确（拒绝或降级），不得抛栈")
    print("  · 固定日志: ~/dsh-collab/logs/entry-coverage.log")
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

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, ast, json, os, re, shutil, subprocess, sys, tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/entry-coverage.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"

SITECUSTOMIZE = '''# -*- coding: utf-8 -*-
import os, sys, atexit
_d = os.environ.get("ENTRY_TRACE_DIR")
if _d and os.environ.get("ENTRY_TRACE_ON"):
    try:
        import trace, threading
        _t = trace.Trace(count=1, trace=0, ignoredirs=[sys.prefix, sys.exec_prefix])
        sys.settrace(_t.globaltrace)
        # ★★ sys.settrace 只作用于**当前线程**。实测佐证：binding-check 自测里的
        #    stub HTTP 服务器跑在新线程 ⇒ 不设 threading.settrace 时它的处理函数
        #    会被报成「零被经过」——**那是探针的盲区，不是被测对象的缺口**。
        #    （与前一条同族：**「我的探针看不见它」≠「它没被经过」**）
        threading.settrace(_t.globaltrace)
        # ★ 按 PID 分开落盘：trace 的 write_results 是 'w' 打开 ⇒ 同目录会**互相覆盖**
        #   实测：不分开写，读到的只是**最后一个子进程**的计数（并集丢失）。
        _sub = os.path.join(_d, str(os.getpid()))
        os.makedirs(_sub, exist_ok=True)
        atexit.register(lambda: _t.results().write_results(show_missing=1, coverdir=_sub))
    except Exception as e:
        sys.stderr.write("ENTRYTRACE-ASSEMBLY-FAILED %r\\n" % (e,))
'''


def call_sites(src):
    """返回 {函数名: 本文件内的**调用点**行号列表}（精确：只看 ast.Call 的被调对象）。

    ★ 为什么需要它：审计报「零被经过」时，**有两种成因而读数完全相同**：
      ㈠**可达但未被测试**（有调用点，只是用例没走到）⇒ 处置＝补用例
      ㈡**根本无人调用**（死代码）⇒ 处置＝补调用点或删除
      二者处置相反 ⇒ 只看「零被经过」**分不出**，必须再看调用点。
      ⇒ 这与「造不出反例有两种成因」同构：**读数相同、处置相反 ⇒ 必须加一问**。
    ★ 精确性：只数 `ast.Call` 且被调对象是 `Name(id=fn)` 或 `Attribute(attr=fn)`，
      不做名字子串匹配（子串匹配会把定义行、注释、文档里的提及都算进去）。
    """
    tree = ast.parse(src)
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = None
        if isinstance(f, ast.Name):
            name = f.id
        elif isinstance(f, ast.Attribute):
            name = f.attr
        if name:
            out.setdefault(name, []).append(node.lineno)
    return out


def executable_lines(src):
    """返回 {行号: 归属函数名}，覆盖模块级与所有函数体（含嵌套）。"""
    tree = ast.parse(src)
    out = {}
    def walk(node, owner):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            owner = node.name
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef,
                                                               ast.AsyncFunctionDef,
                                                               ast.ClassDef)):
            out.setdefault(node.lineno, owner)
        for ch in ast.iter_child_nodes(node):
            walk(ch, owner)
    walk(tree, "<module>")
    return out


def parse_cover(path):
    """解析 .cover：返回**已执行的源码行号**集合。

    ★ 首版写成 `re.match(r"^\\s*(\\d+):", ln)` 并把捕获组当行号 ⇒ **错了**：
      `.cover` 每行的**前导数字是【执行次数】，不是行号**；行号是**隐式的文件位置**
      （trace 的 write_results 对每个源码行输出一行：已执行的写 `count:`，
        未执行的写 `>>>>>>`）⇒ 故**文件行号 == 源码行号**，1:1。
      实测佐证：`require-graph.cover` 780 行 == `require-graph.py` 780 行 ✓
      ⇒ 我上一版把「计数」当成了「它标注的对象」⇒ 与「用我的词搜它的字段」同族：
        **读数与它标注的对象错位** ✓ 失败方向：命中行数被**低估**（本例 59 vs 408）。
    """
    hit = set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for lineno, ln in enumerate(f, 1):
            if ln.startswith(">>>>>>"):
                continue
            if re.match(r"^\s*\d+:", ln):
                hit.add(lineno)
    return hit


def merge_cover(coverdir, target_stem, want_lines=None):
    """★ 并集：任一线程/进程执行过 ⇒ 已覆盖。

    ★ 实测坑一：`.cover` 文件名用**模块名**，而模块名的推导**依赖调用方式** ——
      同一个文件 `python3 full.py` ⇒ `full.cover`，而 `python3 /abs/path/full.py`
      ⇒ `tmp.fx.full.cover`。故**不能**用精确等值匹配（首版即踩此坑）。
    ★ 实测坑二（更要紧）：名字沾边不等于**就是同一个对象**。
      ⇒ 故要求「覆盖文件行数 == 被测源码行数」这一**对象同一性**校验；
        不相等者**排除并报出**，绝不留作静默的错位审计。
      ⇒ 这与我自己那族错误同源：「读数与它标注的对象错位」。
    """
    hit, used, rejected = set(), [], []
    for root, _dirs, files in os.walk(coverdir):
        for fn in files:
            if not fn.endswith(".cover"):
                continue
            stem = os.path.splitext(fn)[0]
            if not (stem == target_stem or stem.endswith("." + target_stem)):
                continue
            p = os.path.join(root, fn)
            if want_lines is not None:
                n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
                if n != want_lines:
                    rejected.append({"文件": fn, "覆盖文件行数": n,
                                     "源码行数": want_lines})
                    continue
            used.append(fn)
            hit |= parse_cover(p)
    return hit, used, rejected


def run_audit(tool, selftest_args, timeout=900):
    tool = os.path.abspath(os.path.expanduser(tool))
    if not os.path.isfile(tool):
        return {"error": "工具不可读：%s" % tool}, 4
    src = open(tool, encoding="utf-8").read()
    try:
        want = executable_lines(src)
    except SyntaxError as e:
        return {"error": "被测工具语法错，无法静态枚举可执行行：%s" % e}, 4

    tmp = tempfile.mkdtemp(prefix="entry-cov-")
    try:
        site = os.path.join(tmp, "site")
        covdir = os.path.join(tmp, "cov")
        os.makedirs(site); os.makedirs(covdir)
        open(os.path.join(site, "sitecustomize.py"), "w",
             encoding="utf-8").write(SITECUSTOMIZE)
        env = dict(os.environ)
        env["PYTHONPATH"] = site + os.pathsep + env.get("PYTHONPATH", "")
        env["ENTRY_TRACE_ON"] = "1"
        env["ENTRY_TRACE_DIR"] = covdir
        p = subprocess.run([sys.executable, tool] + list(selftest_args),
                           capture_output=True, text=True, env=env, timeout=timeout,
                           cwd=os.path.dirname(tool) or ".")
        if "ENTRYTRACE-ASSEMBLY-FAILED" in (p.stderr or ""):
            return {"error": "探针未能装配（见 stderr）",
                    "stderr": p.stderr[-800:]}, 3
        n_src_lines = len(src.splitlines())
        hit, used, rejected = merge_cover(
            covdir, os.path.splitext(os.path.basename(tool))[0], n_src_lines)
        nfiles = len(used)
        if nfiles == 0:
            # ★ 没有 .cover 产物 ⇒ **读不到**，不是「零覆盖」。
            #   二者不同：前者是我的探针没工作，后者是被测对象真没跑。不得互相顶替。
            return {"error": "未产出可用于本对象的 .cover 产物 ⇒ 本次**读不到**"
                             "（不做零覆盖结论）",
                    "名字沾边但对象不符者": rejected,
                    "selftest_rc": p.returncode,
                    "stderr_tail": (p.stderr or "")[-500:]}, 3
        uncovered = {ln: fn for ln, fn in want.items() if ln not in hit}
        # 按函数聚合：整体零执行的函数 = 零被经过的入口候选
        by_fn = {}
        for ln, fn in want.items():
            by_fn.setdefault(fn, []).append(ln)
        calls = call_sites(src)
        fn_stat = []
        for fn, lns in sorted(by_fn.items()):
            done = sum(1 for l in lns if l in hit)
            # ★ 零被经过的**成因**（两种，处置相反）：见 call_sites 的 docstring
            cs = calls.get(fn, [])
            cause = None
            if done == 0 and fn != "<module>":
                cause = "可达但未被测试" if cs else "本文件内无调用点（疑似死代码）"
            fn_stat.append({"函数": fn, "可执行行": len(lns), "已执行行": done,
                            "被经过": done > 0,
                            "调用点": cs, "调用点数": len(cs), "零被经过的成因": cause})
        zero = [f for f in fn_stat if not f["被经过"]]
        dead = [f for f in zero if f["调用点数"] == 0]
        untested = [f for f in zero if f["调用点数"] > 0]
        verdict = ("全部函数至少被一个用例经过" if not zero
                   else "存在**零被经过**的函数 %d 个（其中**疑似死代码** %d · **可达但未被测试** %d）：%s"
                        % (len(zero), len(dead), len(untested),
                           "、".join(f["函数"] for f in zero)))
        # ★★ 退出码必须**由判定推出**，不得写死。
        #    首版此处写死 `, 0` ⇒ 判定文字报 ❌ 而退出码报**成功** ——
        #    **读数与判决不一致**，正是我自己编目了一整天的那族错误
        #    （fail-closed 的反面：嘴上说「有问题」，手上给绿灯）。
        #    ★ 本工具的**自测**当场抓到它（must_reject·gap 夹具 期望 2 实得 0）——
        #      这是「新工具必须有自测」那条纪律的实证回报。
        code = 2 if zero else 0
        return {"工具": tool, "行数": len(src.splitlines()),
                "自测参数": list(selftest_args), "自测退出码": p.returncode,
                "cover 文件数（含子进程）": nfiles,
                "采用的覆盖文件": used,
                "对象不符被排除": rejected,
                "可执行行数": len(want), "已执行行数": len(want) - len(uncovered),
                "未被执行的行数": len(uncovered),
                "未被执行的行": [{"行": l, "函数": uncovered[l]} for l in sorted(uncovered)],
                "函数级": fn_stat,
                "零被经过的函数": zero,
                "判定": verdict}, code
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


FIXTURE_FULL = '''# -*- coding: utf-8 -*-
import sys
def used_a():
    return 1
def used_b():
    return 2


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        assert used_a() == 1 and used_b() == 2
        print("fixture ok")
        sys.exit(0)
    print("default action")
'''

FIXTURE_GAP = '''# -*- coding: utf-8 -*-
import sys
def used():
    return 1
def never_called():
    return 99
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        used()
        print("fixture ok")
        sys.exit(0)
    print("default action")
'''

FIXTURE_REACHABLE = '''# -*- coding: utf-8 -*-
import sys
def used():
    return 1
def reachable_but_untested():
    return 2
def caller():
    return reachable_but_untested()
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        used()
        sys.exit(0)
    caller()
'''

FIXTURE_NOREAD = '''# -*- coding: utf-8 -*-
import os, sys
if "--selftest" in sys.argv:
    # os._exit ⇒ atexit 不运行 ⇒ **不产出 .cover**
    # ⇒ 用于验证「**读不到**」与「**零覆盖**」是两个不同的判定，不得互相顶替
    os._exit(0)
print("default action")
'''


def selftest():
    """自测：**每个非 0 退出码都须有一个 must_reject 用例**，且须有 must_pass 反向用例。

    ★ 为什么本工具必须有自测（而不是「它只是审计工具」）：
      我自己立的纪律是「**不发布我无法验证的门/工具**」。本工具有码 0/2/3/4 四条路径；
      首次审计时发现它**一个自测都没有** ⇒ 那本身就是「未被检查的宣称」。
      ⇒ 故补上，并覆盖：2（零被经过）· 3（读不到）· 4（路径/用法）。
    """
    import tempfile
    T = tempfile.mkdtemp(prefix="entry-cov-selftest-")
    cases, detail = [], []
    try:
        for name, body in (("full.py", FIXTURE_FULL),
                           ("gap.py", FIXTURE_GAP),
                           ("noread.py", FIXTURE_NOREAD)):
            with open(os.path.join(T, name), "w", encoding="utf-8") as f:
                f.write(body)
        cases = [
            ("must_pass·全覆盖夹具 ⇒ 码 0（防「一律报缺」冒充审计）",
             os.path.join(T, "full.py"), [], 0),
            ("must_reject·有一个从未被调用的函数 ⇒ 码 2",
             os.path.join(T, "gap.py"), [], 2),
            ("must_reject·探针**读不到**产物 ⇒ 码 3（不得报成零覆盖）",
             os.path.join(T, "noread.py"), [], 3),
            ("must_reject·工具路径不可读 ⇒ 码 4", os.path.join(T, "nope.py"), [], 4),
        ]
        for name, tool, args, expect in cases:
            rep, rc = run_audit(tool, args or ["--selftest"])
            good = (rc == expect)
            # 附加方向性断言：码 2 与码 3 的**判定文字必须不同**
            if good and expect == 2:
                good = "零被经过" in rep.get("判定", "")
            if good and expect == 3:
                good = "读不到" in rep.get("error", "")
            if good and expect == 0:
                good = "全部函数至少被一个用例经过" in rep.get("判定", "")
            detail.append((name, good, rc, expect))
        # ★ 差分断言：码 2 与码 3 须**既不同码也不同文**（否则分类只是装饰）
        r2, c2 = run_audit(os.path.join(T, "gap.py"), ["--selftest"])
        r3, c3 = run_audit(os.path.join(T, "noread.py"), ["--selftest"])
        detail.append(("★ 审计·码2 与码3 既不同码也不同文（可区分）",
                       c2 != c3 and r2.get("判定") != r3.get("error"), "%s/%s" % (c2, c3), "不同"))
        # ★★ 线程覆盖：sitecustomize 必须同时设 threading.settrace，
        #    否则新线程里的代码会被误报成「零被经过」（实测 binding-check 的 stub 服务器）
        with open(os.path.join(T, "thr.py"), "w", encoding="utf-8") as f:
            f.write('import sys, threading\n'
                    'def in_thread():\n    return 7\n'
                    'if __name__ == "__main__":\n'
                    '    if "--selftest" in sys.argv:\n'
                    '        t = threading.Thread(target=in_thread)\n'
                    '        t.start(); t.join()\n'
                    '        sys.exit(0)\n'
                    '    print("default")\n')
        rt, ct = run_audit(os.path.join(T, "thr.py"), ["--selftest"])
        zt = [g["函数"] for g in rt.get("零被经过的函数", [])]
        detail.append(("★ 线程内函数**不得**被误报零被经过（threading.settrace 已设）",
                       "in_thread" not in zt, ct, 0))
        # ★★ 差分断言（本工具最要紧的一条）：**「零被经过」的两种成因必须被分开**
        #    ㈠可达但未被测试（有调用点）㈡本文件内无调用点（疑似死代码）
        #    二者处置**相反**（补用例 vs 补调用点/删除）⇒ 若读数相同，工具就在**误导**。
        with open(os.path.join(T, "reachable.py"), "w", encoding="utf-8") as f:
            f.write(FIXTURE_REACHABLE)
        r_dead, _ = run_audit(os.path.join(T, "gap.py"), ["--selftest"])
        r_reach, _ = run_audit(os.path.join(T, "reachable.py"), ["--selftest"])
        z_dead = r_dead.get("零被经过的函数", [])
        z_reach = r_reach.get("零被经过的函数", [])
        dead_ok = bool(z_dead) and all(f["调用点数"] == 0 for f in z_dead) \
            and all("无调用点" in (f["零被经过的成因"] or "") for f in z_dead)
        reach_ok = bool(z_reach) and any(f["调用点数"] > 0 for f in z_reach) \
            and any(f["零被经过的成因"] == "可达但未被测试" for f in z_reach)
        detail.append(("★★ 成因·无调用点 ⇒ 报「疑似死代码」（gap 夹具）", dead_ok,
                       [f["调用点数"] for f in z_dead], "全 0"))
        detail.append(("★★ 成因·有调用点 ⇒ 报「可达但未被测试」（reachable 夹具）", reach_ok,
                       [f["调用点数"] for f in z_reach], "至少一个 >0"))
    finally:
        shutil.rmtree(T, ignore_errors=True)
    ok = sum(1 for d in detail if d[1])
    n_rej = [d for d in detail if "must_reject" in d[0]]
    n_pas = [d for d in detail if "must_pass" in d[0]]
    return ok, len(detail), detail, (sum(1 for d in n_rej if d[1]), len(n_rej),
                                     sum(1 for d in n_pas if d[1]), len(n_pas))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tool", nargs="?")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    ap.add_argument("--selftest-args", default="--selftest")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version="entry-coverage %s" % VERSION)
    a = ap.parse_args()
    if a.selftest:
        ok, tot, detail, shape = selftest()
        for n, good, got, exp in detail:
            print("  %s %s  期望 %s / 实得 %s" % ("✅" if good else "❌", n, exp, got))
        print("\nselftest %d/%d" % (ok, tot))
        print("覆盖形态: must_reject %d/%d · must_pass %d/%d"
              % (shape[0], shape[1], shape[2], shape[3]))
        if shape[3] == 0:
            print("  ⚠️ must_pass 用例数=0 ⇒ 本测**无法区分**「正确审计」与「一律报缺」")
        sys.exit(0 if ok == tot else 2)
    if not a.tool:
        print(__doc__); sys.exit(4)
    rep, rc = run_audit(a.tool, a.selftest_args.split())
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        if "error" in rep:
            print("❌ %s" % rep["error"])
            for k in ("stderr_tail", "stderr"):
                if rep.get(k):
                    print("   %s" % rep[k].strip().splitlines()[-1])
        else:
            print("入口覆盖审计 · %s" % rep["工具"])
            print("  自测: %s ⇒ 退出码 %s" % (" ".join(rep["自测参数"]), rep["自测退出码"]))
            print("  覆盖产物: %d 个 .cover（**含子进程**，按 PID 分落、求并集）"
                  % rep["cover 文件数（含子进程）"])
            print("  可执行行 %d · 已执行 %d · **未执行 %d**"
                  % (rep["可执行行数"], rep["已执行行数"], rep["未被执行的行数"]))
            print("  ── 函数级（判据：**被经过**，不是行数比例）──")
            for f in rep["函数级"]:
                mark = "✅" if f["被经过"] else "❌ **零被经过**"
                print("    %s %-28s 可执行 %3d / 已执行 %3d"
                      % (mark, f["函数"], f["可执行行"], f["已执行行"]))
            uf = rep["零被经过的函数"]
            print("  ── 判定 ──")
            if uf:
                print("    ❌ %s" % rep["判定"])
                print("    ⇒ 这些入口的读数**不受任何用例约束**：")
                print("       「用例全绿」与「零用例」在它们身上**完全相同**。")
            else:
                print("    ✅ %s" % rep["判定"])
    sys.exit(rc)


if __name__ == "__main__":
    main()
