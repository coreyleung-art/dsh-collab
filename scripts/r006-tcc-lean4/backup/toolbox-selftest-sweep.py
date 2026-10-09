#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""toolbox-selftest-sweep.py — 审查工具库全量自检实跑器

为什么需要（来由）
    用户 2026-10-10「回到你的工具库完善目标来」。
    audits/_review-toolmap.md 原只覆盖 34 个审查类工具，而 scripts/ 有 306 个 .py
    ⇒ 「先查存量工具面」这一步的存量面【只覆盖了 11%】。
    本器把覆盖面推到全量，并保留三态读数。

判据（取自 selftest-inventory.py）
    ★ 不看 exit 码 —— 因为 exit=0 对「真通过」与「静默跑默认动作」同痕。
    ★ 看输出里是否有【自测标识行】（selftest/自测/PASS/✅/期望/断言/通过/selfcheck/TCC/只读）。

三态 + 两态
    PASS_CLEAN   实跑通过（rc=0）且输出含自测标识行
    PASS_NOMARK  实跑通过但【无自测标识行】⇒ ★ 无法证明跑的是自测（可能是静默默认动作）
    FAIL         实跑返回非零
    TIMEOUT      超时（★ 不计入通过）
    NO_ENTRY     源码里既无 --selfcheck 也无 --selftest

用法
    python3 toolbox-selftest-sweep.py [--limit N] [--timeout S] [--workers W] [--out PATH] [--selftest] [--selfcheck] [--json]
    python3 toolbox-selftest-sweep.py --selftest     # 自检（含正例/负例）
    python3 toolbox-selftest-sweep.py --selfcheck    # 声明与实现一致性
"""

# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

VERSION = "1.0.0"
LOG_DIR = os.path.join(os.path.expanduser("~"), "dsh-collab", "logs")   # ⑦ 统一日志

MARK = ("selftest", "自测", "PASS", "✅", "期望", "断言", "通过", "selfcheck", "TCC", "只读")


def write_log(line):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "toolbox-selftest-sweep.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print("   ⚠️ 日志写入失败: %s" % e)


def probe(p, timeout):
    """返回 dict(状态/rc/标识行数/首行/用时)"""
    name = os.path.basename(p)
    try:
        src = open(p, encoding="utf-8", errors="replace").read()
    except OSError as e:
        return {"tool": name, "state": "NO_ENTRY", "rc": None, "marks": 0,
                "first": "", "secs": 0, "why": str(e)}
    # ★ 入口判定用【试跑级】—— ★ 三个口径的实测教训（2026-10-10）：
    #   ① 源码含字样        ⇒ 假阳性（5 个工具的注释里有字样，CLI 未实现）
    #   ② --help 列出       ⇒ 假阴性 94%（18 抽样中 17 个其实有入口 —— 很多脚本用手动 argv 解析）
    #   ③ ★ 真跑那个旗标，看是否 "unrecognized" ⇒ 唯一可区分
    #   ⇒ 只有【真跑】才是实跑级；--help 本身也是一种声明。
    flag = None
    for cand in ("--selfcheck", "--selftest"):
        try:
            tr = subprocess.run([sys.executable, p, cand], capture_output=True, text=True,
                                timeout=20, cwd=os.path.dirname(os.path.dirname(p)))
            tout = ((tr.stdout or "") + (tr.stderr or "")).lower()
            if "unrecognized" in tout or "invalid choice" in tout or "no such option" in tout:
                continue
            flag = cand
            break
        except subprocess.TimeoutExpired:
            flag = cand      # 超时 ⇒ 入口存在（只是慢），由主扫描的限时再判
            break
        except Exception:
            continue
    if flag is None:
        return {"tool": name, "state": "NO_ENTRY", "rc": None, "marks": 0,
                "first": "", "secs": 0,
                "why": "★ 试跑 --selfcheck/--selftest 均 unrecognized ⇒ 真无 CLI 自检入口"}
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, p, flag], capture_output=True, text=True,
                           timeout=timeout, cwd=os.path.dirname(os.path.dirname(p)))
        el = round(time.time() - t0, 2)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        marks = len([l for l in out.split("\n") if any(k in l for k in MARK)])
        first = (out.split("\n")[0][:70] if out else "(空输出)")
        if r.returncode != 0:
            state = "FAIL"
        else:
            state = "PASS_CLEAN" if marks > 0 else "PASS_NOMARK"
        return {"tool": name, "state": state, "rc": r.returncode, "marks": marks,
                "first": first, "secs": el, "flag": flag, "why": ""}
    except subprocess.TimeoutExpired:
        return {"tool": name, "state": "TIMEOUT", "rc": "TIMEOUT", "marks": -1,
                "first": "★ 超时", "secs": round(time.time() - t0, 2), "flag": flag, "why": ""}
    except Exception as e:
        return {"tool": name, "state": "FAIL", "rc": "ERR", "marks": -1,
                "first": type(e).__name__, "secs": round(time.time() - t0, 2), "flag": flag, "why": str(e)}


def sweep(limit=None, timeout=8, workers=8):
    root = os.path.join(os.path.expanduser("~"), "dsh-collab", "scripts")
    files = sorted(os.path.join(root, f) for f in os.listdir(root) if f.endswith(".py"))
    if limit:
        files = files[:limit]
    out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(probe, p, timeout): p for p in files}
        for i, f in enumerate(concurrent.futures.as_completed(futs), 1):
            out.append(f.result())
            if i % 40 == 0:
                print("   … %d/%d" % (i, len(files)), flush=True)
    out.sort(key=lambda x: x["tool"])
    return out


def selftest():
    """★ 正例 + 负例：证本器能区分四态。"""
    cases = []
    d = tempfile.mkdtemp()
    # 负例 A：无入口
    a = os.path.join(d, "a_noentry.py")
    open(a, "w").write("import argparse\n"
                       "p = argparse.ArgumentParser()\n"
                       "p.add_argument('--foo')\n"
                       "p.parse_args()\n")
    ra = probe(a, 8)
    cases.append(("负例A（用 argparse 但无自检旗标）⇒ NO_ENTRY（unrecognized）",
                  ra["state"] == "NO_ENTRY", ra["state"]))
    # 负例 B：有入口但 rc≠0
    b = os.path.join(d, "b_fail.py")
    open(b, "w").write("import sys\n"
                    "if '--help' in sys.argv: print('--selfcheck')\n"
                    "if '--selfcheck' in sys.argv: print('bad'); sys.exit(3)\n")
    rb = probe(b, 8)
    cases.append(("负例B（入口非零退出）⇒ FAIL", rb["state"] == "FAIL", "%s rc=%s" % (rb["state"], rb["rc"])))
    # 负例 C：rc=0 但无自测标识 ⇒ PASS_NOMARK（★ 关键区分）
    c = os.path.join(d, "c_nomark.py")
    open(c, "w").write("import sys\n"
                    "if '--help' in sys.argv: print('--selfcheck')\n"
                    "if '--selfcheck' in sys.argv: pass\n")
    rc = probe(c, 8)
    cases.append(("负例C（rc=0 无标识）⇒ PASS_NOMARK（★ 与 PASS_CLEAN 分离）",
                  rc["state"] == "PASS_NOMARK", rc["state"]))
    # 正例：有入口 + 有标识 + rc=0
    e = os.path.join(d, "e_clean.py")
    open(e, "w").write("import sys\n"
                    "if '--help' in sys.argv: print('--selfcheck')\n"
                    "if '--selfcheck' in sys.argv: print('✅ 自测 1/1 符合预期')\n")
    re_ = probe(e, 8)
    cases.append(("正例（rc=0 + 自测标识）⇒ PASS_CLEAN", re_["state"] == "PASS_CLEAN", re_["state"]))
    # ★ 负例D：源码含 "--selfcheck" 字样但 --help 未列 ⇒ 应 NO_ENTRY（F105 场景）
    f = os.path.join(d, "f_fake_entry.py")
    open(f, "w").write("import argparse\n"
                       "# 注释里提到 --selfcheck 但 CLI 未实现\n"
                       "p = argparse.ArgumentParser()\n"
                       "p.add_argument('--bar')\n"
                       "p.parse_args()\n")
    rf = probe(f, 8)
    cases.append(("负例D（源码含字样但 argparse 未定义）⇒ NO_ENTRY（★ F105 场景）",
                  rf["state"] == "NO_ENTRY", "%s %s" % (rf["state"], rf.get("why", "")[:30])))

    # ★ 负例E：不解析 argv 的脚本 ⇒ 任何旗标都 rc=0 但无自测标识 ⇒ PASS_NOMARK（正确归类）
    g = os.path.join(d, "g_noargv.py")
    open(g, "w").write("print('hi')\n")
    rg = probe(g, 8)
    cases.append(("负例E（不解析 argv）⇒ PASS_NOMARK（★ 跑它等于跑默认动作）",
                  rg["state"] == "PASS_NOMARK", rg["state"]))
    bad = 0
    for name, ok, detail in cases:
        print("   %s %-52s %s" % ("✅" if ok else "❌", name, detail[:40]))
        if not ok:
            bad += 1
    print("   ⇒ 自测：%d/%d 符合预期" % (len(cases) - bad, len(cases)))
    for f in (a, b, c, e, f, g):
        try:
            os.unlink(f)
        except OSError:
            pass
    try:
        os.rmdir(d)
    except OSError:
        pass
    return 0 if bad == 0 else 1


def selfcheck():
    src = open(__file__, encoding="utf-8").read()
    probs = []
    if "tokenize" in src:
        pass  # 本器不剥离扫描，无自指需求
    if len(re.findall(r'^\s*VERSION\s*=', src, re.M)) != 1:
        probs.append("VERSION 非单一来源")
    for f in ("--selftest", "--selfcheck", "--json", "--timeout", "--workers", "--limit", "--out"):
        if f not in src:
            probs.append("缺 CLI 旗标 %s" % f)
    if probs:
        print("   ✗ %s" % "；".join(probs)); return 1
    print("   ⇒ ✅ 声明与实现一致（%d 项）" % 7)
    return 0


def main():
    ap = argparse.ArgumentParser(description="审查工具库全量自检实跑器")
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 个（调试用）")
    ap.add_argument("--timeout", type=int, default=8, help="每工具限时秒（默认 8）")
    ap.add_argument("--workers", type=int, default=8, help="并发数（默认 8）")
    ap.add_argument("--out", default=None, help="结果 JSON 落盘路径")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    ap.add_argument("--selftest", action="store_true", help="★ 自检（4 例）")
    ap.add_argument("--selfcheck", action="store_true", help="声明与实现一致性")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()

    t0 = time.time()
    rows = sweep(a.limit, a.timeout, a.workers)
    el = round(time.time() - t0, 1)
    from collections import Counter
    c = Counter(r["state"] for r in rows)
    print()
    print("★ 扫描 %d 个 .py · 用时 %ss · 限时 %ss · 并发 %d" % (len(rows), el, a.timeout, a.workers))
    for k in ("PASS_CLEAN", "PASS_NOMARK", "FAIL", "TIMEOUT", "NO_ENTRY"):
        print("   %-12s %d" % (k, c.get(k, 0)))
    print()
    print("★ 非 PASS_CLEAN 的明细（前 40）")
    for r in rows:
        if r["state"] != "PASS_CLEAN":
            print("   %-12s %-40s rc=%-8s %s" % (r["state"], r["tool"][:38], r["rc"],
                                                (r.get("first") or r.get("why") or "")[:44]))
    if a.out:
        json.dump(rows, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n落盘: %s" % a.out)
    write_log("[%s] swept=%d clean=%d nomark=%d fail=%d timeout=%d noentry=%d secs=%s" % (
        time.strftime("%Y-%m-%dT%H:%M:%S"), len(rows), c.get("PASS_CLEAN", 0),
        c.get("PASS_NOMARK", 0), c.get("FAIL", 0), c.get("TIMEOUT", 0), c.get("NO_ENTRY", 0), el))
    return 0


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
    'tool': 'toolbox-selftest-sweep',
    'version': '1.0.0',
    'capability': ['审查工具库全量自检实跑器：对 scripts/ 下的工具逐个探 --selftest 可达性并实跑', '会执行被探工具的 --selftest（这是它的用途），命令由本器按目录枚举生成', '--json 机器可读；--out 结果落盘'],
    'impossible': ['不修改被探工具的任何文件（只读 + 只执行其自检入口）', '不把「超时/无入口」与「失败」混为一类（四态分报）', '不跳过超时项而假装通过'],
    'log': 'toolbox-selftest-sweep.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--timeout']],
    'positive': ['--selftest'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {
        'os.unlink': '只删本器自建的临时文件（a,b,c,e,f,g）',
        'os.rmdir': '只删本器自建的临时目录（d）',
    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset({'os.rmdir', 'os.unlink'}),
    'positive_expect_rc': [0],
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


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
