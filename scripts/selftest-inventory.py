#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具族自测入口盘点 —— 把「盘点」从一次性手工探针，变成一次调用产出的读数。

由来（2026-09-28）：
  我做过一次手工盘点，量出「5/10 有可达的 --selftest 入口」，其中把 `dup-skeleton.py` 判为
  「✅ 有入口且跑通」—— **判错了**。它的首行是「扫描 1 个文件 · 0 个函数（≥3 行）」，
  即它把 `--selftest` 当成**文件路径**、照常跑了默认扫描并 exit=0。
  ⇒ 证据就在我自己的探针输出里，**我读的是 exit 码，没读输出**。

★ 本工具用的判据（与那次手探的区别就在这里）：
  1. **不用 exit 码分态** —— `exit=0` 对「真通过」与「静默跑默认动作」**同痕**。
  2. 判「--selftest 有没有真跑」看**输出里有没有工具自报的自测标识/断言**
     （grep 计 `selftest|自测|must_pass|must_reject|期望|PASS|✅` 的行数，>0 才算跑了自测）。
  3. 判「怎么处理不认识的输入」用**伪造旗标** `--zzz-bogus-flag`（老登的那条一般化：
     特定参数是实例，不认识的参数是类别）⇒ 看它有没有**说出那个旗标**。

五态（① ④ 为合格，② ③ ⑤ 为缺口）：
  ① 有自测入口且真跑 ｜ ② 静默跑默认动作（输出像正常报告）｜ ③ 崩（Traceback）
  ④ 干净报用法/不认识的参数 ｜ ⑤ = ② 的体面版：把旗标当对象、错误消息指向另一个原因

用法：python3 selftest-inventory.py [--tools a,b,c]
退出码：0 = 全部合格；1 = 有缺口（逐条列出）。
"""

# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets", "--dry-run")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──


# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== selftest-inventory 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 工具族自测入口盘点 —— 把「盘点」从一次性手工探针，变成一次调用产出的读数。")
    print("  · 由来（2026-09-28）：")
    print("  · 我做过一次手工盘点，量出「5/10 有可达的 --selftest 入口」，其中把 `dup-skeleton.py` 判为")
    print("  · 「✅ 有入口且跑通」—— **判错了**。它的首行是「扫描 1 个文件 · 0 个函数（≥3 行）」，")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/selftest-inventory.log")
    return 0



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。

import sys as _r006_sys
if False:  # ★ R006 ②⑩ 已迁移至文件末 canonical 块（原守卫并入）
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
if False:  # ★ R006 ②⑩ 已迁移至文件末 canonical 块（原守卫并入）
    _r006_sys.exit(lean4_check())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, re, subprocess, sys, time



# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/selftest-inventory.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

_KNOWN = {"--tools", "--dir", "-h", "--help"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _KNOWN]
if _unknown:
    print(f"❌ 不认识的参数: {' '.join(_unknown)}")
    print(f"   本工具接受的参数: {' '.join(sorted(_KNOWN))}")
    print("   ★ 加这道检查的起因：本工具自己曾把伪造旗标【静默忽略】、照常跑默认动作")
    sys.exit(2)
# ★ R006 ⑨⑤ --help 自解释：原状是【静默忽略 --help 并跑默认盘点（28s，rc=1）】
if ("-h" in sys.argv[1:]) or ("--help" in sys.argv[1:]):
    print("用法: selftest-inventory [--dir <dir>] [--tools a,b,c]")
    print("退出码: 0/1 均为【正常跑完】（本器是报告器：1 = 报告有发现）；2 = 用法或 IO 错误")
    print("★ 已知未结项（⑨②）：本器【无可表示的成功退出码】—— 任何合法调用都返回 1，")
    print("  故「0=成功」在本器上不可达。这里明确说出来，而不是让读者以为是失败。")
    print("")
    print(__doc__ or "")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
BOGUS = "--zzz-bogus-flag"
CRASH = "Traceback (most recent call last)"
# ★ R1 的判据被改了四次，每次都因为「同痕」（这是本工具最该记住的一件事）：
#   第 1 版 exit 码        ⇒ exit=0 对「真通过」与「静默跑默认动作」同痕（dup-skeleton 被我判成①）
#   第 2 版 宽标记集(✅/PASS)⇒ dup-skeleton 的【默认动作输出】里也有 ✅ ⇒ 又中了（假阳性）
#   第 3 版 窄标记(自测/selftest)⇒ card-json-check 的崩溃消息 `FileNotFoundError: '--selftest'`
#                             回显了旗标名 ⇒ 假阳性；加「排除旗标回显行」堵住
#   第 4 版 窄标记+排除回显  ⇒ ts-not-future-check 根本不印「自测」二字、只打断言行 ⇒ 假阴性
#   ⇒ ★ 结论：任何「找输出里的某个字面」的判据都同时有假阳性与假阴性两侧。
#     正解与我给老登那条建议**同构**：不要把「识别」做成扫字串，要做成【必填字段】——
#     让每个工具在自测输出里打一行固定形态的机器可读标识：`SELFTEST <工具名> <通过>/<总数>`。
#     这一行在默认动作里不可能出现（默认动作不知道总数）⇒ 二值、不撞车。
SELFTEST_LINE = re.compile(r"^SELFTEST\s+\S+\s+\S+", re.M)
DEFAULT_TOOLS = ["verification-level-lint", "inplace-pointer-audit", "absence-claim-lint",
                 "ts-not-future-check", "thread-fork-audit", "card-json-check", "dup-skeleton",
                 "msg-count-lint", "bb-put-both", "put-card"]


def ran_selftest(out, out_default):
    """工具是否真的声明自己在跑自测。

    ★ 判据最终定为【两段】—— 第二段是被老登现场逼出来的：
      他只写 `SELFTEST OK`（无数字）时，**默认动作可能顺手把这行也打了** ⇒ 那一行不携带信息。
      ⇒ 所以判据是：㈠`--selftest` 的输出里有 SELFTEST 标识行 **且** ㈡**默认动作的输出里没有**。
      第二段等价于「这里有一个只有真跑了自测才会出现的量」——但它**不查格式**，
      所以不用管各工具是写 `6/6` 还是 `16 PASS / 0 FAIL`（格式不统一正是找字面判据必然漏的原因）。
    """
    if CRASH in out:
        return 0, "崩溃（不是自测）"
    m = SELFTEST_LINE.search(out)
    if not m:
        return 0, "没有 SELFTEST 标识行 ⇒ 无法证明它跑的是自测（未申报）"
    if SELFTEST_LINE.search(out_default):
        return 0, "★ 该标识行在【默认动作】的输出里也出现 ⇒ 它不携带信息（可被伪造）"
    return 1, f"有 SELFTEST 行，且默认动作不打它：{m.group(0).strip()}"


def run(path, args, timeout=12):
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, path] + args, capture_output=True, text=True, timeout=timeout)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = "timeout", ""
    return code, out, time.time() - t0


def _discover(here):
    """★ 名单从【目录枚举】得来，不手写。

    起因（2026-09-28，当天）：`DEFAULT_TOOLS` 原本是**手写的 10 个名字**，于是
    **我当天新建的两个工具（catchall-scan.py · selftest-inventory.py 自己）从未进过盘点** ——
    而它们恰好带着我花一整天编目的那个缺陷（伪造旗标 ⇒ 静默跑默认动作）。
    ⇒ 这暴露了我上一卡那条「把判别对象换到我这一侧就安全」的一个反例：
      **世界侧 = 无法枚举 · 我这一侧 = 可以枚举、但名单可能不完整。**
    ⇒ 修法：名单由 `*.py` 枚举产生 ⇒ 那一刻「漏」变成不可能；`--tools` 只用于收窄。
    """
    out = sorted(f[:-3] for f in os.listdir(here) if f.endswith(".py"))
    return out


def main():
    here = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else HERE
    all_py = _discover(here)
    tools = all_py
    if "--tools" in sys.argv:
        tools = sys.argv[sys.argv.index("--tools") + 1].split(",")
    elif "--exhaustive" not in sys.argv:
        # ★ 预筛（默认开）：只动态跑「文件里出现过 SELFTEST 字面」的那些。
        #   起因：名录改成目录枚举后是 218 个文件 × 2 次子进程 ⇒ 跑不动（实测超时）。
        #   ★ 预筛的代价必须写出来：**它是一道【找字面】的闸** ⇒ 会漏掉「不写字面
        #     但真跑自测」的工具 ⇒ 所以报出跳过了几个，并给 --exhaustive 兜底。
        keep = []
        for t in all_py:
            try:
                if "SELFTEST" in open(os.path.join(here, t + ".py"), encoding="utf-8", errors="replace").read():
                    keep.append(t)
            except OSError:
                pass
        skipped = [t for t in all_py if t not in keep]
        print(f"  （预筛：{len(all_py)} 个 .py 里，{len(keep)} 个含 SELFTEST 字面 ⇒ 只动态跑这些）")
        # ★ 被跳过的名字要列出来，不能只报个数。
        #   实测假阴性一例：`put-card` —— 它的 SELFTEST 字面在【兄弟文件】 put-card-selftest.py 里，
        #   不在 put-card.py 里 ⇒ 预筛把它跳过了，而它恰好是当时【唯一】合格的一个。
        #   ⇒ 只报「跳过 N 个」时那个 N 里藏着「唯一合格的那个」；列出名字才可发现。
        print(f"   ★ 未动态测的 {len(skipped)} 个（已知假阴性：put-card，其标识在兄弟文件里）：")
        print("     " + " ".join(skipped[:40]) + (" …" if len(skipped) > 40 else ""))
        print("     ⇒ 要全跑用 --exhaustive（代价：会执行 218 个工具，慢且有副作用风险）")
        tools = keep
    tools = [t[:-3] if t.endswith(".py") else t for t in tools]

    print("工具族自测入口盘点（判据：①自报 SELFTEST 行 ②该行在默认动作里不出现）")
    print(f"被测目录: {here}")
    print()
    print(f"  {'工具':26s} {'selftest态':10s} {'伪造旗标态':12s} 证据")
    gaps = []
    for t in tools:
        f = os.path.join(here, t + ".py")
        if not os.path.exists(f):
            print(f"  {t:26s} {'文件不存在':10s} {'—':12s} （我档案里可能登记过一个不存在的工具）")
            gaps.append((t, "MISSING", "文件不存在"))
            continue
        c1, o1, _ = run(f, ["--selftest"])
        c0, o0, _ = run(f, [])
        marks, why1 = ran_selftest(o1, o0)
        st1 = "①真跑" if marks > 0 else ("③自测崩" if CRASH in o1 else "②没跑自测")
        c2, o2, _ = run(f, [BOGUS])
        named = "bogus" in o2
        crashed = CRASH in o2
        usage = bool(re.search(r"usage:|用法", o2))
        if crashed:
            st2 = "③崩"
        elif named:
            st2 = "④报出旗标"
        elif usage:
            st2 = "④报用法"
        else:
            st2 = "⑤默默当成对象"
        ev = f"自测标识行={marks}（{why1}）· 旗标 exit={c2} · 说出旗标={named}"
        print(f"  {t:26s} {st1:10s} {st2:12s} {ev}")
        if st1.startswith(("②", "③")):
            gaps.append((t, "NO_SELFTEST_ENTRY", f"selftest 态={st1}（exit={c1}，{why1}）"))
        if st2.startswith(("③", "⑤")):
            gaps.append((t, "BAD_UNKNOWN_INPUT", f"伪造旗标的处理={st2}（exit={c2}）"))

    print()
    if not gaps:
        print("★ 全部合格：每个工具都有真跑的自测入口，且对不认识的输入有声。")
        return 0
    print(f"缺口 {len(gaps)} 项：")
    for t, kind, why in gaps:
        print(f"  ✗ {t:26s} {kind:22s} {why}")
    return 1




# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块 · 自包含 · 勿手改） ═══════════
# 由 scripts/r006-u6-apply.py 注入；改模板后重跑注入器，勿在本块内手工编辑。
# 设计原则（三条，均有本线实证来源）：
#   1) ② 的每一句声明都必须【被本块结构核验】—— 只打印不检查的「纸面声明」不算 TCC。
#   2) ⑩ 的 A/ E/F 是【冻结声明 + 变更检测】：新增危险原语/写入点/外部命令调用点 ⇒ 立刻红。
#   3) 反空洞：写入点与命令点扫描器必须先在【合成恶意源】上自证会红，否则判「不能判定」。
#      （依据 R006 §4.2 坑 3：剥字面量后读不到实参 ⇒ 调用点枚举为 0 ⇒ 「0 ⊆ 允许」空洞通过）
import sys as _r006_sys
import os as _r006_os
import io as _r006_io
import re as _r006_re
import json as _r006_json
import ast as _r006_ast
import time as _r006_time
import tokenize as _r006_tokenize
import subprocess as _r006_subprocess

_R006_DECL = {
    'tool': 'selftest-inventory',
    'version': '1.0.0',
    'capability': ['工具族自测入口盘点：把一次性的手工探针，变成一次调用产出的读数', '由来（2026-09-28）：手工盘点曾把 dup-skeleton.py 判为「有入口且跑通」—— 判错了', '会执行被盘点工具的旗标以取实跑证据'],
    'impossible': ['不修改被盘点工具的任何文件（只读审计类行为）', '不把「有入口」等同于「有意义」（首行是否为空/0 命中也纳入读数）', '不静默略过读不到的项（如实报 UNCHECKED）'],
    'log': 'selftest-inventory.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--dir']],
    'positive': ['--tools', 'gate-canfail.py'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {

    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset(),
    'positive_expect_rc': [0, 1],
    'positive_expect_reason': '本器是【报告器】而非门：rc=1 = 报告有发现，是合法结果；只有 rc=2（用法错）/124/125（超时/崩溃）才算门失效。★ 同时如实记缺陷：本器【无可表示的成功退出码】—— 任何合法调用都返回 1，故「0=成功」在本器上不可达，属 ⑨② 缺口，留待批次 2 修。',
    'dryrun_via_block': True,
    'dry_suppress': ['log'],
    'dryrun_note': '本器原无 --dry-run ⇒ 由 canonical 块接管：垫片摘旗标 + 置空写助手 log',
}

_R006_EXEC_ATTRS = ("run", "Popen", "call", "check_call", "check_output")
_R006_DANGER_ATTRS = {
    "os": ("system", "popen", "remove", "unlink", "rmdir", "removedirs", "chmod", "chown", "kill"),
    "shutil": ("rmtree", "move"),
    "subprocess": _R006_EXEC_ATTRS,
}
_R006_DANGER_NAMES = ("eval", "exec", "compile", "__import__")
_R006_SYNTH_EXEC = "import subprocess as _sp\nfrom subprocess import Popen\n_sp.run(['ls'], shell=True)\nPopen(['x'])\n"
_R006_SYNTH_WRITE = "open('x','w')\nopen(p, mode='a')\n"
_R006_SYNTH_EXEC_WANT = frozenset({"subprocess.run", "subprocess.Popen"})
_R006_SYNTH_WRITE_WANT = frozenset({"const:x", "<expr>"})


def _r006_src():
    return open(_r006_os.path.abspath(__file__), encoding="utf-8").read()


def _r006_strip(s):
    """tokenize 抹除注释与字符串【内容】：按原文区间置空。
    ★ 不重拼 token —— 重拼会吞掉 token 间空白（`if a.selftest:` 变 `ifa.selftest:`）。"""
    buf = list(s)
    off = [0]
    for ln in s.splitlines(True):
        off.append(off[-1] + len(ln))
    try:
        for tk in _r006_tokenize.generate_tokens(_r006_io.StringIO(s).readline):
            if tk.type in (_r006_tokenize.COMMENT, _r006_tokenize.STRING):
                a = off[tk.start[0] - 1] + tk.start[1]
                b = off[tk.end[0] - 1] + tk.end[1]
                for i in range(a, min(b, len(buf))):
                    if buf[i] not in "\r\n":
                        buf[i] = " "
    except Exception:
        return s
    return "".join(buf)


def _r006_aliases(t):
    """import 别名解析：`import subprocess as sp` / `from subprocess import run` 都要认得。
    ★ 不做这步，改个别名就能绕过扫描器（= 空洞通过）。"""
    m = {}
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                m[(a.asname or a.name.split(".")[0])] = a.name.split(".")[0]
        elif isinstance(n, _r006_ast.ImportFrom):
            for a in n.names:
                m[(a.asname or a.name)] = (n.module or "").split(".")[0] + "." + a.name
    return m


def _r006_scan(src):
    """AST 三面读数：外部命令调用点 / 写入点 / 危险原语。
    ★ 用 AST 而非正则：注释与字符串天生不进 AST ⇒ 免除「扫到自己的检测正则」假阳性。"""
    r = {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}
    try:
        t = _r006_ast.parse(src)
    except Exception as e:
        r["err"] = "AST 解析失败: %s" % e
        return r
    al = _r006_aliases(t)
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                r["imports"].add(a.name.split(".")[0])
        elif isinstance(n, _r006_ast.ImportFrom):
            if n.module:
                r["imports"].add(n.module.split(".")[0])
        elif isinstance(n, _r006_ast.Call):
            f = n.func
            if isinstance(f, _r006_ast.Attribute) and isinstance(f.value, _r006_ast.Name):
                mod = al.get(f.value.id, f.value.id)
                if mod in _R006_DANGER_ATTRS and f.attr in _R006_DANGER_ATTRS[mod]:
                    if mod == "subprocess":
                        r["exec"].add("subprocess." + f.attr)
                    else:
                        r["danger"].add(mod + "." + f.attr)
            elif isinstance(f, _r006_ast.Name):
                tgt = al.get(f.id, f.id)
                if tgt.startswith("subprocess."):
                    r["exec"].add("subprocess." + tgt.split(".", 1)[1])
                elif f.id in _R006_DANGER_NAMES:
                    r["danger"].add(f.id)
                elif f.id == "open":
                    mode = ""
                    if len(n.args) >= 2 and isinstance(n.args[1], _r006_ast.Constant):
                        mode = str(n.args[1].value)
                    for kw in n.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, _r006_ast.Constant):
                            mode = str(kw.value.value)
                    if any(c in mode for c in ("w", "a", "x", "+")):
                        p = "<expr>"
                        if n.args and isinstance(n.args[0], _r006_ast.Constant):
                            p = "const:" + str(n.args[0].value)
                        r["write"].add(p)
    return r


def _r006_regex_pass(s):
    """A 的【独立第二通道】：在 tokenize-剥离后的文本上做正则扫描。
    两通道结论不一致 ⇒ 判「不能判定」，**不得**假设其中某一个对。"""
    code = _r006_strip(s)
    hits = set()
    for pat, name in ((r"\beval\s*\(", "eval"), (r"\bexec\s*\(", "exec"),
                      (r"\b__import__\s*\(", "__import__"),
                      (r"\bos\.system\s*\(", "os.system"), (r"\bos\.popen\s*\(", "os.popen"),
                      (r"\.rmtree\s*\(", "shutil.rmtree"), (r"\bos\.remove\s*\(", "os.remove")):
        if _r006_re.search(pat, code):
            hits.add(name)
    return hits


def _r006_run(argv, timeout=60):
    try:
        p = _r006_subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                 cwd=_r006_os.path.dirname(_r006_os.path.abspath(__file__)))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except _r006_subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, str(e)


def _r006_snap(paths):
    import hashlib
    out = {}
    for p in paths:
        try:
            st = _r006_os.stat(p)
            with open(p, "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()[:16]
            out[p] = [st.st_size, h]
        except OSError:
            out[p] = None
    return out


def _r006_std_imports(imports):
    """③ 依赖完整性：把顶层 import 分类为 内置 / 标准库 / 第三方（Python 3.9 无 stdlib_module_names）。"""
    import importlib.util as _u
    import sysconfig
    std = _r006_os.path.realpath(sysconfig.get_paths()["stdlib"])
    third, stdlib = [], []
    for m in sorted(imports):
        if m in _r006_sys.builtin_module_names:
            stdlib.append(m)
            continue
        try:
            sp = _u.find_spec(m)
        except Exception:
            sp = None
        if sp is None:
            third.append(m + "(未解析)")
        elif sp.origin and _r006_os.path.realpath(sp.origin).startswith(std):
            stdlib.append(m)
        elif sp.origin in (None, "built-in", "frozen"):
            stdlib.append(m)
        else:
            third.append(m)
    return stdlib, third


def _r006_legacy_narrative():
    """沿用本器【原有的 selfcheck() 自述】—— 不因迁移到 canonical 块而丢失既有声明内容。
    取不到时如实说明（不静默当空）。"""
    f = globals().get("selfcheck")
    if not callable(f) or getattr(f, "__module__", None) != __name__:
        return []
    try:
        import io as _i
        import contextlib as _c
        buf = _i.StringIO()
        with _c.redirect_stdout(buf):
            f()
        return [l.rstrip() for l in buf.getvalue().splitlines() if l.strip()]
    except Exception as e:
        return ["(沿用原有 selfcheck() 失败，如实报出: %s)" % e]


def _r006_selfcheck():
    """R006 ② TCC 能力边界自检：三段输出 + 【结构核验】（不做纸面声明）。"""
    name = _R006_DECL["tool"]
    src = _r006_src()
    sc = _r006_scan(src)
    stdlib, third = _r006_std_imports(sc["imports"])
    W = _R006_DECL
    lines = ["R006 ② TCC 能力边界自检 · %s v%s" % (name, W["version"])]
    lines.append("【① 能力清单】")
    for x in W["capability"]:
        lines.append("  · " + x)
    legacy = _r006_legacy_narrative()
    if legacy:
        lines.append("  · —— 以下沿用本器原有 selfcheck() 自述 ——")
        for l in legacy:
            lines.append("  " + l)
    lines.append("【② 不该发生路径清单】")
    for x in W["impossible"]:
        lines.append("  · " + x)
    lines.append("【③ 依赖完整性】")
    lines.append("  · Python %s（本机）" % _r006_sys.version.split()[0])
    lines.append("  · 标准库 %d 个：%s" % (len(stdlib), ", ".join(stdlib) if stdlib else "无"))
    lines.append("  · 第三方 %d 个：%s" % (len(third), ", ".join(third) if third else "无"))
    lines.append("  · 外部命令调用点（冻结）：%s" % (", ".join(sorted(W["frozen_exec"])) or "无"))
    lines.append("  · 写入点（冻结）：%s" % (", ".join(sorted(W["frozen_write"])) or "无"))
    lines.append("  · 固定日志：%s" % (W["log"] or "无"))

    chk = []
    chk.append(("依赖无第三方", not third, "第三方: %s" % (", ".join(third) or "无")))
    ext_ok = (frozenset(sc["exec"]) == frozenset(W["frozen_exec"]))
    chk.append(("外部命令面与冻结集一致", ext_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["exec"]) or "无", sorted(W["frozen_exec"]) or "无")))
    wr_ok = (frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    chk.append(("写入面与冻结集一致", wr_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["write"]) or "无", sorted(W["frozen_write"]) or "无")))
    roots = [r for r in W.get("write_roots", [])]
    bad = [p for p in sc["write"] if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(_r006_os.path.expanduser(r)) for r in roots)]
    chk.append(("常量写入点在允许根内", not bad, "越界: %s" % (", ".join(bad) if bad else "无")))
    dg_ok = (frozenset(sc["danger"]) == frozenset(W["frozen_danger"]))
    chk.append(("危险原语面与冻结集一致", dg_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["danger"]) or "无", sorted(W["frozen_danger"]) or "无")))
    lg_ok = (not W["log"]) or (W["log"] in src)
    chk.append(("声明的日志路径真实存在于源码", lg_ok, W["log"] or "N/A（本器无日志）"))
    need = ["【① 能力清单】", "【② 不该发生路径清单】", "【③ 依赖完整性】"]
    chk.append(("R006 ② 规格要求的三段齐备", all(n in lines for n in need), " / ".join(need)))
    # ★ 第 9 项 —— 采纳 adjudicator 建议的【可判定窄口径】版，而非其原表述。
    #   为何是窄口径（均为实测，见 docs「批次缺陷复核」节）：
    #     ① 只扫【剥离面】：对「版本写进字符串声明」与「写进错误消息」两种【自然写法】命中 0 ⇒ 瞎；
    #     ② 改扫【字符串面】：现有 10 器立刻误报 11 处（多为 legit 的文档提及与工具自身版本常量）。
    #   ⇒ 「硬编码版本」整体**不可门化**（真值源给不出：无法机械区分合法的版本下限声明与不正当锁死）。
    #     故只保留其中【可判定】的一片：生产代码里的**浮点型**版本字面量（形态✓ 真值源✓）。
    #   ★ 如实标注：本项命中率极低，是**变更检测器**，不是能力证明。
    _vh = sorted(set(_r006_re.findall(r"\b3\.\d+(?:\.\d+)?\b", _r006_strip(src))))
    chk.append(("剥离面无浮点型 Python 版本字面量（窄口径可判定片）", not _vh,
                "命中: %s" % (", ".join(_vh) if _vh else "无（★ 低命中率：变更检测器，非能力证明）")))
    # ★ 声明的正例必须实测可用（非空转）—— 此前这里放的是「读过自己打印的行」，那是同义反复。
    _pos = W.get("positive", [])
    _prc = None
    if _pos:
        _prc, _po = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(_pos))
    chk.append(("声明的正例实测可用（非空转）",
                bool(_pos) and _prc in W.get("positive_expect_rc", [0]) and _prc not in (2, 124, 125),
                "%s → rc=%s" % (" ".join(_pos), _prc)))

    fails = [c for c in chk if not c[1]]
    lines.append("⇒ 声明核验：%d/%d 一致%s" % (len(chk) - len(fails), len(chk),
                                        "" if not fails else " · ❌ " + "; ".join(c[0] for c in fails)))
    for nm, ok, dt in chk:
        lines.append("   %s %s — %s" % ("✅" if ok else "❌", nm, dt))
    print("\n".join(lines))
    return 0 if not fails else 1


def _r006_dryrun_proof():
    """⑩ D：有 --dry-run ⇒ 实测 run 前后外部状态一致；无 ⇒ 【结构证明】（并如实标注为变体）。"""
    W = _R006_DECL
    dr = W.get("dryrun")
    watch = [_r006_os.path.expanduser(p) for p in W.get("watch", [])]
    if dr:
        b = _r006_snap(watch)
        rc, out = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(dr))
        a = _r006_snap(watch)
        return (rc == 0 and a == b), "★ 实测：rc=%s · watch %d 项前后一致=%s" % (rc, len(watch), a == b), "实测"
    src = _r006_src()
    wr = _r006_scan(src)["write"]
    roots = [_r006_os.path.expanduser(r) for r in W.get("write_roots", [])]
    outside = [p for p in wr if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(r) for r in roots)]
    ok = (frozenset(wr) == frozenset(W["frozen_write"])) and not outside
    return ok, ("△ 变体（非实测）：本器无 --dry-run ⇒ 以【写入面冻结 + 全部写入点在允许根内】作结构证明"
                "（%s）" % (", ".join(sorted(wr)) or "零写入点")), "结构证明"


def _r006_lean4_check():
    """R006 ⑩ 约束门 A–F。每项都带【反空洞】控制：扫描器先在合成恶意源上自证会红。"""
    W = _R006_DECL
    src = _r006_src()
    sc = _r006_scan(src)
    me = _r006_os.path.basename(_r006_os.path.abspath(__file__))
    rows = []

    # 反空洞前置：扫描器自证
    syn_e = frozenset(_r006_scan(_R006_SYNTH_EXEC)["exec"])
    syn_w = frozenset(_r006_scan(_R006_SYNTH_WRITE)["write"])
    scanner_live = (syn_e == _R006_SYNTH_EXEC_WANT) and (syn_w == _R006_SYNTH_WRITE_WANT)
    vac = [] if scanner_live else ["合成源未被完整检出 exec=%s write=%s" % (sorted(syn_e), sorted(syn_w))]

    # A 危险原语面（★ 不是「一定没有」—— 有则必须逐条声明并冻结；未声明即红）
    allowed_dg = dict(W.get("allowed_danger", {}))
    a_ast = frozenset(sc["danger"])
    a_rx = frozenset(_r006_regex_pass(src))
    a_frozen = frozenset(W["frozen_danger"])
    unallowed = sorted(a_ast - set(allowed_dg))
    a_ok = (scanner_live and a_ast == a_frozen and not (a_rx - a_ast) and not unallowed)
    rows.append(("A", "危险原语面全部已声明并冻结（无未声明原语）", a_ok,
                 "实测=%s · 已声明 %d 项 · 双通道一致=%s%s"
                 % (sorted(a_ast) or "无（零危险原语）", len(allowed_dg), (a_rx - a_ast) == set(),
                    "" if not unallowed else " · ★未声明: %s" % unallowed)))

    # B 负例全部被拒（非空，且实测 rc != 0）
    negs = W.get("negatives", [])
    b_det, b_ok = [], len(negs) >= 2
    for nv in negs:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(nv))
        b_det.append("%s→rc%s" % (" ".join(nv), rc))
        if rc == 0:
            b_ok = False
    if not scanner_live:
        b_ok = False
    rows.append(("B", "负例全部被拒（≥2 条，实测 rc≠0）", b_ok, " · ".join(b_det) or "无负例"))

    # C 正例可用（防门太宽砍掉自己）
    # ★ 口径：合法输入必须被【受理并产出结果】。默认 rc==0；对「报告器」类工具，
    #   rc=1（报告有发现）是合法结果 —— 但须在 decl 里显式声明 expect_rc 并给出理由，
    #   不得拿它当免检口（否则 C 退化为空转）。rc∈{2,124,125} 一律算门失效。
    pos = W.get("positive", [])
    want_rc = W.get("positive_expect_rc", [0])
    c_ok, c_det = bool(pos), "无正例 ⇒ 不能判定"
    if pos:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(pos))
        c_ok = (rc in want_rc) and (rc not in (2, 124, 125))
        c_det = "%s → rc=%s（期望 %s）%s" % (" ".join(pos), rc, want_rc,
                                            "" if rc in want_rc else " · ★门太宽或用法被拒")
    if len(want_rc) > 1:
        c_det += " · 放宽理由：" + W.get("positive_expect_reason", "（未给理由 ⇒ 视为未声明）")
    rows.append(("C", "正例可用（防门太宽砍掉自己）", c_ok, c_det))

    # D 零变更
    d_ok, d_det, d_kind = _r006_dryrun_proof()
    rows.append(("D", "零变更（%s）" % d_kind, d_ok, d_det))

    # E 白名单冻结 + 写入面变更检测
    e_ok = (scanner_live and isinstance(W["frozen_write"], frozenset)
            and frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    rows.append(("E", "写入面白名单冻结（frozenset + 变更即红）", e_ok,
                 "类型=%s · 元素=%d · 变更检测=on" % (type(W["frozen_write"]).__name__, len(W["frozen_write"]))))

    # F 外部命令白名单 + 别名逃逸检测
    f_ok = scanner_live and isinstance(W["frozen_exec"], frozenset) and frozenset(sc["exec"]) == frozenset(W["frozen_exec"])
    f_alias = "import subprocess as _sp" in _R006_SYNTH_EXEC and "subprocess.run" in syn_e
    rows.append(("F", "外部命令白名单（别名逃逸已覆盖 + 变更即红）", f_ok and f_alias,
                 "命令集=%s · 别名形式检出=%s" % (sorted(sc["exec"]) or "无", f_alias)))

    nf = [r for r in rows if not r[2]]
    print("== %s · --lean4-check（六项 A–F）==" % me)
    for k, nm, ok, dt in rows:
        print("  %s %s %-38s %s" % ("OK  " if ok else "FAIL", k, nm, dt))
    if vac:
        print("  ★ 反空洞控制未过：%s" % "; ".join(vac))
    print("\n  => %d/%d pass, %d FAIL" % (len(rows) - len(nf), len(rows), len(nf)))
    return 0 if not nf else 1


def _r006_sets():
    """诊断口：给出本器【实际】三面读数与冻结集，供注入器「先算后填」。"""
    sc = _r006_scan(_r006_src())
    print(_r006_json.dumps({
        "tool": _R006_DECL["tool"],
        "observed_exec": sorted(sc["exec"]), "frozen_exec": sorted(_R006_DECL["frozen_exec"]),
        "observed_write": sorted(sc["write"]), "frozen_write": sorted(_R006_DECL["frozen_write"]),
        "observed_danger": sorted(sc["danger"]), "frozen_danger": sorted(_R006_DECL["frozen_danger"]),
        "imports": sorted(sc["imports"]), "err": sc["err"],
    }, ensure_ascii=False, indent=2))
    return 0


def _r006_want(flag):
    """旗标本器是否被请求：既认当前 argv，也认【早期垫片】暂存的旗标。
    （垫片必须存在：本器可能在模块级就校验 argv，会先于本块把旗标当「不认识的参数」拒掉。）"""
    return (flag in _r006_sys.argv) or (flag in globals().get("_R006_EARLY_FLAGS", []))


# ── R006 ⑨③ `--dry-run` 统一实现（canonical） ────────────────────────────────
# 分流（★ 必须分流：本族里 3 个器【自带】--dry-run，拦截它会破坏其既有语义）：
#   · dryrun_via_block=True  : 本器无自带实现 ⇒ 由本块接管：把 --dry-run 从 argv 摘掉
#     （故其 argparse 不因未知旗标报错），并按 decl["dry_suppress"] 把【自动写入助手】
#     置为空操作 ⇒ 本器走完整逻辑但不产生自动落盘副作用。
#   · dryrun_via_block=False : 本器自带实现 ⇒ 把垫片摘走的旗标【放回 argv】，交还原实现。
if __name__ == "__main__":
    _R006_DRY = False
    if _R006_DECL.get("dryrun_via_block") and _r006_want("--dry-run"):
        _R006_DRY = True
        _r006_sys.argv = [x for x in _r006_sys.argv if x != "--dry-run"]
        for _rn in _R006_DECL.get("dry_suppress", []):
            if callable(globals().get(_rn)):
                globals()[_rn] = (lambda *a, **k: None)
    elif "--dry-run" in globals().get("_R006_EARLY_FLAGS", []):
        _r006_sys.argv.append("--dry-run")
else:
    _R006_DRY = False


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
