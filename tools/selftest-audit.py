#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest-audit —「判据的自证是不是【真的】」的机械核验门。

★ 立据（2026-10-12 · v7 更正账 19）：
  ★ `tools/gcr-gate.py --selftest` 的五条「负例」**全是恒真字面量** ——
    源码逐字 `("G-CR14 负例 port=0", 0 == 0, True)` ★ **`0 == 0` 永远为 True**。
  ★★ ⇒ 它们**从未调用被测判据函数** ⇒ 该总门对 11 个判据函数的**可信负控数 = 0**，
     而它报「自证 5/5」。
  ★★★ **⇒ 故本门把「自证是不是真的」机械化**：它不跑工具，它**读源码**。

本门查四件：
  A **有 `--selftest`**：源码里是否出现 `selftest` 入口
  B **自证条目里没有恒真表达式**（★ 本门核心）：
    · `(..., 0 == 0, ...)` · `(..., 1 == 1, ...)` · `(..., True, True)` ·
      `(..., <字面量比较字面量>, ...)` · `(..., <裸 True/False>, ...)`
  C **自证条目里有对本地函数的调用**（★ 证明它真调了判据）
  D **`--selftest` 真能跑出 0**（★ 可选，`--run`）

三态：无可扫文件 ⇒ 「不可判」；有工具但全无 selftest ⇒ 报红并列出。

★★★ **本门的已知局限（★ 如实声明，★ 不假装能检）**：
  ★ **【跳行赋值】型恒真本门【检不出】** —★ 如果源码写：
    ```python
    mb = 245.0                                        # ★ 写死在【另一行】
    cases.append(("G-CR8 负例", mb >= 200, True))   # ★ 本门看不出 mb 是常量
    ```
    ★ 而 **gcr-gate 旧版的第二条正是这个形态**（D-204 逐字：`mb = 245.0` + `mb >= 200`）。
    ★★ 要检它需**跳行数据流分析** —★ **正则做不到**。
  ★★ ⇒ ★ 故本门的 8 个命中是【下界】—★ **真正的恒真数量只会更多。**
"""
import io
import os
import re
import sys
import json
import argparse
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★★ 又一坑（2026-10-12）：`list.append((…))` 是【两层括号】—★ 首版模式只吃一层 ⇒ **全部 0 命中**
# ── B 恒真模式（★ 逐条有立据）──
# ★★★ 2026-10-12 修（★ 首版误报 8 个，★ 本纳自查发现）：
#   ★ 首版模式只匹配 `("...", None,` —★★ 而那个形态也出现在【普通函数调用】里！
#     实例：`scripts/l3-semantic-check.py:163` 逐字 `cmd_check("", None, args.model)` —★ 它是**函数调用**，不是自证条目。
#   ★★★ ⇒ 故所有模式**必须锁定在【自证语境】**（`cases.append(` / `checks.append(` / `results.append(`…）。
#   ★ 并新增一条**负控**：普通函数调用形态不得被误伤。
_CTX = r'(?:cases|checks|results|cases_|CASES|CASES_)\.append\s*\('
TAUTOLOGY_PATTERNS = [
    (r'(?:cases|checks|results|CASES)\.append\s*\(\s*\(\s*["\'][^"\']*["\']\s*,\s*(\d+)\s*==\s*\1\s*,',
     '★ 字面量自等 `N == N`（如 `0 == 0`）'),
    (r'(?:cases|checks|results|CASES)\.append\s*\(\s*\(\s*["\'][^"\']*["\']\s*,\s*True\s*,\s*True\s*\)',
     '★ 裸 `True` 当 got（★ 未调判据）'),
    (r'(?:cases|checks|results|CASES)\.append\s*\(\s*\(\s*["\'][^"\']*["\']\s*,\s*False\s*,\s*False\s*\)',
     '★ 裸 `False` 当 got'),
    (r'(?:cases|checks|results|CASES)\.append\s*\(\s*\(\s*["\'][^"\']*["\']\s*,\s*None\s*,',
     '★ 裸 `None` 当 got（★ 仅在自证语境内）'),
    (r'(?:cases|checks|results|CASES)\.append\s*\(\s*\(\s*["\'][^"\']*["\']\s*,\s*\d+(?:\.\d+)?\s*(?:>=|<=|>|<)\s*\d+(?:\.\d+)?\s*,',
     '★ 字面量直接相比（如 `245.0 >= 200`）'),
    (r'(?:cases|checks|results|CASES)\.append\s*\(\s*\(\s*["\'][^"\']*["\']\s*,\s*\d+(?:\.\d+)?\s*==\s*\d+(?:\.\d+)?\s*,',
     '★ 字面量相等'),
]
RE_SELFTEST = re.compile(r'\bdef\s+selftest\s*\(|\bdef\s+selfcheck\s*\(|["\']--selftest["\']|["\']--selfcheck["\']')
# ── C：自证里是否调了本地函数（★ 形如 `foo(` 且 foo 在本文件有 def）──
RE_DEF = re.compile(r'^\s*def\s+([A-Za-z_]\w*)\s*\(', re.M)


def strip_docstrings(src):
    """★ 剥三引号块（★ 免得自己的立据注释被误伤 —— ★ R006 惯例）。"""
    out = []
    i, n = 0, len(src)
    dq = '"' * 3
    sq = "'" * 3
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith(dq, i) or src.startswith(sq, i):
            q = src[i:i + 3]
            j = src.find(q, i + 3)
            i = n if j < 0 else j + 3
            continue
        out.append(c)
        i += 1
    return "".join(out)


def scan_file(path):
    """★ 返回 {has_selftest, tautologies, calls_local, selftest_body}"""
    try:
        raw = io.open(path, encoding="utf-8").read()
    except Exception:
        return None
    code = strip_docstrings(raw)
    has = bool(RE_SELFTEST.search(code))
    taut = []
    for pat, why in TAUTOLOGY_PATTERNS:
        for m in re.finditer(pat, code):
            taut.append({"pattern": why, "snippet": m.group(0)[:80]})
    defs = set(RE_DEF.findall(code))
    # ★ 取 selftest 函数体
    m = re.search(r'def\s+(selftest|selfcheck)\s*\([^)]*\):(.*?)(?=\n\S|\Z)', code, re.S)
    body = m.group(2) if m else ""
    called = sorted({fn for fn in defs if fn not in ("selftest", "selfcheck", "main")
                     and re.search(r'\b%s\s*\(' % re.escape(fn), body)})
    return {"has_selftest": has, "tautologies": taut, "calls_local": called,
            "defs": sorted(defs)}


def discover(roots=None):
    out = []
    for d in (roots or ["tools", "scripts", "research"]):
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != "node_modules" and not x.startswith(".")]
            for fn in filenames:
                if fn.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return sorted(out)


def audit(roots=None, run=False):
    files = discover(roots)
    rows = []
    for rel in files:
        r = scan_file(os.path.join(ROOT, rel))
        if r is None:
            continue
        rows.append({"file": rel, **r})
    if run:
        # ★★★ 2026-10-12 修（D-231）—— 两处：
        #   ★ ① **本行原写 `p.status`，而正确属性是 `p.returncode`！**
        #       ★★ 立据：本线用同一写法跑 `scripts/` 面 ⇒ **341 个全被记成 `ERR:AttributeError`**
        #          ⇒ **报告说「341 个全坏」，而手动跑一个 ⇒ `exit=0`**（★ D-228）。
        #       ★★★ **而那个 bug 就【在本函数里】—— 本线先前只修了外部脚本，漏了本工具自身。**
        #   ★ ② 新增【四分类】：`0` / `2`（不支持该旗标）/ `TIMEOUT` / **其它非 0（候缺陷）**。
        #       ★ 立据：`scripts/` 面 341 个里 **165 个是 `rc=2`**（★ 不支持）⇒ 不单列就会报成缺陷。
        #   ★ ③ 新增 `stdin=subprocess.DEVNULL` —— ★ 防脚本等输入而**永久挂住**（★ 实测主进程曾跑 12:18）。
        from concurrent.futures import ThreadPoolExecutor

        def _one(rel):
            try:
                p = subprocess.run([sys.executable, os.path.join(ROOT, rel), "--selftest"],
                                   capture_output=True, text=True, timeout=90,
                                   stdin=subprocess.DEVNULL)
                rc = p.returncode                  # ★ returncode，不是 status
                # ★★★ 2026-10-12（D-232）：【不支持】不一定返 `2` —★
                #   ★ 实测：6 个脚本用 **`rc=1` + 「用法:」/`不认识的参数`** 表示用法错；
                #   ★ 而其中两个还**明确写了「本工具【没有】--selftest 入口」** —★ 那是对的做法。
                #   ★★☃ ⇒ 故按【输出内容】也认一遍，归入「不支持」。
                blob = ((p.stdout or "") + (p.stderr or ""))[:2000]
                marks = ("用法:", "用法：", "usage:", "不认识的参数",
                         "unrecognized", "没有】--selftest", "没有 --selftest",
                         "本工具【没有】")
                if rc != 0 and any(mk in blob for mk in marks):
                    return rel, 2
                return rel, rc
            except subprocess.TimeoutExpired:
                return rel, "TIMEOUT"
            except Exception:
                return rel, None

        targets = [r["file"] for r in rows if r["has_selftest"]]
        try:
            with ThreadPoolExecutor(max_workers=8) as ex:
                got = dict(ex.map(_one, targets))
        except Exception:
            got = {}
        for r in rows:
            if r["file"] in got:
                r["run_exit"] = got[r["file"]]
    return rows


def recheck_serial(rows, cand):
    """★★★ 2026-10-12 新增（D-234）：对「候缺陷」做【串行复核】。

    ★ 立据：本纳用 8 并发跑 `scripts/` 面 341 个自证 ⇒ `bb-model-store` 被报 `exit=1`；
    ★★ 而【串行 3 次 + 并发 8 次单独跑它】均 `exit=0` ⇒
    ★★☃ **故那是【并发下的伪失败】**（★ 多个脚本同时打板 ⇒ 板瞬时过载）。
    ★ 故本函数把「其它非 0」【串行重跑一次】—★ ★ **红而不复现的，不算缺陷。**
    """
    import subprocess as _sp
    out = []
    for r in cand:
        try:
            cp = _sp.run([sys.executable, os.path.join(ROOT, r["file"]), "--selftest"],
                         capture_output=True, text=True, timeout=90, stdin=_sp.DEVNULL)
            rc = cp.returncode
        except _sp.TimeoutExpired:
            rc = "TIMEOUT"
        except Exception:
            rc = None
        out.append({**r, "serial_exit": rc, "reproducible": (rc == r.get("run_exit"))})
    return out


def classify_run(rows):
    """★ 四分类（★ D-231）：把「非 0」拆成【不支持】与【候缺陷】，避免误报。"""
    st = [r for r in rows if r["has_selftest"] and "run_exit" in r]
    ok = [r for r in st if r["run_exit"] == 0]
    usage = [r for r in st if r["run_exit"] == 2]
    tod = [r for r in st if r["run_exit"] == "TIMEOUT"]
    other = [r for r in st if r["run_exit"] not in (0, 2, "TIMEOUT", None)]
    return {"total": len(st), "ok": ok, "usage": usage, "timeout": tod, "other": other}


def selftest():
    ok = tot = 0
    # ★ 正控：检出 `0 == 0` 型恒真（★ 复刻 gcr-gate 旧版原文）
    tot += 1
    bad = 'cases.append(("G-CR14 负例 port=0", 0 == 0, True))\n'
    hit = any(re.search(p, bad) for p, _ in TAUTOLOGY_PATTERNS)
    if hit:
        ok += 1
        print("  ✅ 正控：检出 `0 == 0` 型恒真（★ 复刻 gcr-gate 旧版原文）")
    else:
        print("  ❌ 正控：未检出 `0 == 0` 型恒真")
    # ★ 正控：检出裸 True 当 got
    tot += 1
    if any(re.search(p, 'cases.append(("x 负例", True, True))\n') for p, _ in TAUTOLOGY_PATTERNS):
        ok += 1
        print("  ✅ 正控：检出裸 `True` 当 got")
    else:
        print("  ❌ 正控：未检出裸 True")
    # ★ 正控：检出【字面量直接相比】（★ 如 `245.0 >= 200`）
    tot += 1
    if any(re.search(p, 'cases.append(("x", 245.0 >= 200, True))\n') for p, _ in TAUTOLOGY_PATTERNS):
        ok += 1
        print("  ✅ 正控：检出字面量直接相比（`245.0 >= 200`）")
    else:
        print("  ❌ 正控：未检出字面量直接相比")
    # ★★ 负控（2026-10-12 实测误报修入）：【普通函数调用】不得被误伤
    tot += 1
    callform = 'cmd_check("", None, args.model)\n'
    if not any(re.search(p, callform) for p, _ in TAUTOLOGY_PATTERNS):
        ok += 1
        print("  ✅ 负控：`cmd_check(\"\", None, x)`（★ 普通调用）未被误伤（★ 已锁定自证语境）")
    else:
        print("  ❌ 负控：普通调用被误判为恒真条目")
    # ★★ 诚实：【跳行赋值】型恒真本门检不出 —★ 本门不假装能检
    tot += 1
    varname = 'mb = 245.0\ncases.append(("G-CR8", mb >= 200, True))\n'
    if not any(re.search(p, varname) for p, _ in TAUTOLOGY_PATTERNS):
        ok += 1
        print("  ✅ 诚实：【跳行赋值】型恒真本门检不出（★ 已在文档里声明该局限）")
    else:
        print("  ❌ 意外：跳行赋值型竟被检出（★ 那本门的局限声明需改）")
    # ★★ 负控：真调判据的写法【不得】被误伤（★ 防过宽）
    tot += 1
    good = 'cases.append(("G-CR8 负例", _synth_gcr8(245.0), False))\n'
    if not any(re.search(p, good) for p, _ in TAUTOLOGY_PATTERNS):
        ok += 1
        print("  ✅ 负控：真调判据的写法未被误伤（★ 防过宽）")
    else:
        print("  ❌ 负控：真调判据的写法被误判为恒真")
    # ★ 负控：调本地函数可被识别
    tot += 1
    src = "def helper(x):\n    return x > 1\n\ndef selftest():\n    helper(2)\n"
    m = re.search(r'def\s+(selftest|selfcheck)\s*\([^)]*\):(.*?)(?=\n\S|\Z)', strip_docstrings(src), re.S)
    defs = set(RE_DEF.findall(strip_docstrings(src)))
    called = [fn for fn in defs if fn != "selftest" and re.search(r'\b%s\s*\(' % fn, m.group(2))]
    if called == ["helper"]:
        ok += 1
        print("  ✅ 负控：自证体里调本地函数可被识别（★ 证明它真调了）")
    else:
        print("  ❌ 负控：本地函数调用识别失败（%s）" % called)
    # ★ 三态：空目录 ⇒ 空列表
    tot += 1
    if discover(["/tmp/__no_such_root__"]) == []:
        ok += 1
        print("  ✅ 正控：不存在的根 ⇒ 空列表（★ 调用方报「不可判」）")
    else:
        print("  ❌ 正控：不存在的根竟有结果")
    # ★★★ 2026-10-15（D-378）【异源用例】—★ 四维判据相关工具补齐
    try:
        import sys as _sysE
        _sysE.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/tools")
        from extcase import extcase_selftest as _ecs
        _ec_ok, _ec_tot, _ec_msg = _ecs("selftest-audit.py")
        print(_ec_msg)
        if _ec_ok is None:
            print("  ❓ 异源用例 ⇒ **不可判**")
        else:
            ok += _ec_tot; tot += _ec_tot
    except Exception as _eE:
        print("  ❓ 异源用例 ⇒ 不可判（%s）" % type(_eE).__name__)

    # ★★★ 2026-10-15 补（D-398）：【可失败路径判定】的四向控制 ——
    #   ★ 立据：旧基线用正则 `(?=\ndef )` ⇒ ★ 只抓第一个 def ⇒ **第二任实测被切断**。
    #   ★★ 故控制里【必须含那一个坑的复刻】。
    _c398 = [
        ("正控", "`return 0 if not fails else 1` ⇒ 必须判 failable",
         "def selfcheck():\n    return 0 if not fails else 1\n", "failable"),
        ("负控", "打印即 `return 0` ⇒ 必须判 no_failable_path",
         "def selfcheck():\n    print('capability list')\n    return 0\n", "no_failable_path"),
        ("★正控（第二任的坑）", "两个自证函数，判据在【第二个】⇒ 必须判 failable（★ 旧正则在此误报）",
         "def selfcheck():\n    print('x')\n    return 0\n\n\ndef _r006_selfcheck():\n"
         "    return 0 if not fails else 1\n", "failable"),
        ("正控", "入口调用【被调函数】里的失败出口 ⇒ 必须判 failable",
         "def _core():\n    import sys\n    sys.exit(1)\n\ndef selfcheck():\n    return _core()\n", "failable"),
        ("负控", "无自证入口 ⇒ 必须判 no_entry（★ 不得当「无判据」）",
         "def main():\n    return 0\n", "no_entry"),
    ]
    for _k, _name, _src, _want in _c398:
        tot += 1
        _got, _why = ast_failable(_src, is_src=True)
        if _got == _want:
            ok += 1
            print("  \u2705 %s\uff1a%s\uff08\u2605 D-398\uff09" % (_k, _name))
        else:
            print("  \u274c %s\uff1a%s\uff08\u2605 \u5b9e\u9645 %s\uff0c\u671f\u671b %s\uff09" % (_k, _name, _got, _want))

    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


# ══════════════════════════════════════════════════════════════════
# ★★★ 2026-10-15（D-398 另一条）【可失败路径判定 + 基线可重生】
#   立据（第二任 D-377/D-395）：原 `H5e 无判据退化档` 的基线
#   `data/registry/same-source-selftest-survey-20261015.json` 用的是**正则**
#   `re.search(r"def (selftest|selfcheck)\(.*?(?=\ndef |\Z)", s, re.S)` ——
#   ★★ **非贪婪前瞻【只抓到第一个 def 到下一个 def】**（实测 21–23 行），
#   ★★ 而许多工具有【两个自证函数】（`def selfcheck()` 与 `def _r006_selfcheck()`）
#   ⇒ **切断得太早 ⇒ 把「有判据」读成「无判据」**（★ 第三任采样 5/5 反驳）。
#   ★ 本函数改用 **AST（结构，不靠正则）**：★ 且**分析【全部**入口函数及其被调函数**】。
#   ★★ 且本器给基线【补上生成器】—— 原基线**全仓无生成器**（grep 只命中 beacon-check.py）
#     ⇒ ★ 那意味着**只能手改 JSON 才能变绿**（★ 那就是造假）。
# ══════════════════════════════════════════════════════════════════

def _ret_can_be_nonzero(v):
    """★ `return <expr>` 是否**可能非零**（★ 只有【明确的 0/None 字面量】才算不可能）。"""
    if v is None:
        return False
    if isinstance(v, ast.Constant):
        return not (v.value is None or v.value == 0)
    if isinstance(v, ast.IfExp):
        return _ret_can_be_nonzero(v.body) or _ret_can_be_nonzero(v.orelse)
    return True     # ★ 变量/比较/布尔/调用 ⇒ **都可能非零**（★ 宁宽勿窄：本判据只用来【否掉】极窄的形态）


def ast_failable(path_or_src, is_src=False):
    """★★ 判【工具的自证里有没有可失败路径】—— ★ 静态 AST，不是正则。

    四态：`failable` / `no_failable_path` / `no_entry` / `undecidable`
    ★★ **本判据的边界（★ 不掩盖）**：★ 它是**静态**的 ⇒ ★ **不能证明「真会失败」**，
      ★ 只能证明**源码里存在非零出口**；★ **行为证据仍是 `--run` 的退出码**。
    """
    try:
        src = path_or_src if is_src else io.open(path_or_src, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
    except Exception as e:
        # ★★★ 2026-10-15（D-398 自查）：原写 `return "undecidable", ""` —— ★★ 而它把
        #   **一切异常（含本文件自己漏 import 的 NameError）都读成「不可判」** ⇒
        #   ★★ 5 条控制当场全报 undecidable，★ 而【看不出根因】。
        #   ★ 这**正是本仓盯的那一形态**：★ **异常路径与成功同形**（★ D-231 的 `None` 当绿）。
        #   ★ 修法：★ 把【异常类名与消息】带出去。
        return "undecidable", "%s: %s" % (type(e).__name__, str(e)[:70])
    fns = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns[n.name] = n
    entries = [nm for nm in fns if "selfcheck" in nm or "selftest" in nm]
    if not entries:
        return "no_entry", ""
    def _calls(fnnode):
        out = set()
        for c in ast.walk(fnnode):
            if isinstance(c, ast.Call):
                f = c.func
                nm = getattr(f, "id", None) or getattr(f, "attr", None)
                if nm:
                    out.add(nm)
        return out
    frontier, seen = set(entries), set(entries)
    for _ in range(3):
        nxt = {cn for nm in frontier for cn in _calls(fns[nm]) if cn in fns and cn not in seen}
        if not nxt:
            break
        seen |= nxt
        frontier = nxt
    for nm in sorted(seen):
        for node in ast.walk(fns[nm]):
            if isinstance(node, ast.Raise):
                return "failable", "%s: raise" % nm
            if isinstance(node, ast.Return) and _ret_can_be_nonzero(node.value):
                return "failable", "%s: return 可能非零" % nm
            if isinstance(node, ast.Call):
                f = node.func
                fn = getattr(f, "id", None) or getattr(f, "attr", None)
                if fn in ("exit", "quit"):
                    if not node.args or not (isinstance(node.args[0], ast.Constant)
                                             and node.args[0].value == 0):
                        return "failable", "%s: exit(非零)" % nm
    return "no_failable_path", "入口 %d 个、共查 %d 个函数：无任何非零出口" % (len(entries), len(seen))


# ★ D-398：本器新增的两件依赖（★ 首版漏了它们 ⇒ 5 条控制全报 undecidable —— ★ 见下）
import ast
import time

SURVEY_DEFAULT = os.path.join(ROOT, "data", "registry",
                              "same-source-selftest-survey-%s.json" % time.strftime("%Y%m%d"))
SURVEY_LIVE = os.path.join(ROOT, "data", "registry",
                           "same-source-selftest-survey-20261015.json")


def survey(rows, out_path=None):
    """★★★ 重算基线：★ `vacuous_no_failable_criterion` 用 **AST** 判，★ 并**附行为读数**。

    ★★ 诚实边界：★ 本器的 `same_source_only*` **本轮不重算** ——
      ★ 它**沿用旧基线值并显式标注 `_carried_forward`**（★ 照抄必须标注，★ 不冒充现测）。
    """
    old_ref = {}
    try:
        old_ref = json.loads(io.open(SURVEY_LIVE, encoding="utf-8").read())
    except Exception:
        old_ref = {}
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "version": "4.0.0-ast",
           "generator": os.path.relpath(os.path.abspath(__file__), ROOT),
           "_definition": {
               "vacuous_no_failable_criterion":
                   "★ AST 判【入口函数及其被调函数里无非零出口】；"
                   "★★ 静态 ⇒ 不等于行为证明（行为证据是 run_exit）",
               "same_source_only": "★ 本轮**未重算** ⇒ 沿用旧基线（★ 见 _carried_forward）",
           },
           "_carried_forward": {}}
    vac, failable, noentry, undec = [], [], [], []
    for r in rows:
        p = os.path.join(ROOT, r["file"])
        k, why = ast_failable(p)
        r["ast_failable"] = k
        r["ast_reason"] = why
        if k == "no_failable_path":
            vac.append(r["file"])
        elif k == "failable":
            failable.append(r["file"])
        elif k == "no_entry":
            noentry.append(r["file"])
        else:
            undec.append(r["file"])
    out["scanned"] = len(rows)
    out["vacuous_no_failable_criterion"] = len(vac)
    out["vacuous_tools"] = sorted(vac)
    out["failable_tools_n"] = len(failable)
    out["no_entry_n"] = len(noentry)
    out["undecidable_n"] = len(undec)
    # ★ 载入旧基线 ⇒ ★ **只搬 same_source 两项并标注 carried_forward**
    try:
        old = old_ref or json.loads(io.open(SURVEY_LIVE, encoding="utf-8").read())
        for k in ("same_source_only", "same_source_only_strict"):
            if k in old:
                out[k] = old[k]
                out["_carried_forward"][k] = old.get("at")
        if "same_source_tools" in old:
            out["same_source_tools"] = old["same_source_tools"]
        out["_legacy_vacuous"] = {"value": old.get("vacuous_no_failable_criterion"),
                                  "at": old.get("at"), "version": old.get("version"),
                                  "note": "★ 旧值（正则判法，已知误标）—— ★ 保留以便对照，★ 不得作为现测引用"}
    except Exception as e:
        out["_carried_forward"] = {"error": "%s ⇒ same_source 未搬运（★ 空 ≠ 无）" % type(e).__name__}
    # ★★★ 报数必带【面】（★ v7 纪律）—— ★ 没有面，分母不可比（★ 旧基线的面【不可判】：
    #   ★ 它无生成器 ⇒ 无从复现它当时扫的是哪些根）。
    _roots = {}
    for r in rows:
        top = r["file"].split("/")[0]
        _roots[top] = _roots.get(top, 0) + 1
    out["_face"] = {"roots": _roots, "total": len(rows),
                    "note": "★ 本面 = selftest-audit 的默认根（tools/scripts/research）；"
                            "★★ 与旧基线 349 的【面不同】⇒ 两个分母不可直接比"
                            "（★ 旧面不可判 —— 它没有生成器）"}
    # ★★★ 2026-10-15 修（D-399b，★ 由明鉴 v3 的 schema 卡【对照】发现）：
    #   ★ 首版逐字写 `out["beacon_scope"] = out.get("beacon_scope") or {}` ⇒ ★★ **发出一个空 dict**，
    #   ★ 而旧基线里那个字段是**有内容的**（{"tools":13,"has_external":13,...} = 「必跑面 13 个全已异源」）。
    #   ★★ ⇒ 那是**静默丢字段**（★ 空 ≠ 无）；★ 且它量的是【必跑面】—— ★ 不该由我重算。
    #   ★ 修法：★ 与 `same_source` 同样【搬运】并标注进 `_carried_forward`。
    for _k in ("beacon_scope", "note"):
        if _k in old_ref:
            out[_k] = old_ref[_k]
            # ★★★ 2026-10-15（D-400，★ 明鉴 v3 指出）：★ **「沿用」是【来源类别】，不是数值**
            #   ⇒ 沿用项的【可判性等级】与现算项【不同级】：★ 现算可复跑，★ 沿用**不可复跑**
            #     （★ 旧基线的生成器**已丢失**）。★★ 故不能只标时间戳，必须标【等级】。
            out["_carried_forward"][_k] = {
                "at": old_ref.get("at"),
                "class": "carried_forward",
                "decidability": "★ 不可复跑（★ 旧基线生成器已丢失 · ★ 且面与 scanned 不同）"}
        else:
            out[_k] = {} if _k == "beacon_scope" else None
            out["_carried_forward"][_k] = {
                "at": None, "class": "absent",
                "decidability": "★ 旧基线无此字段 ⇒ 不可判（★ 空 ≠ 无）"}
    # ★★★ 同一条（D-400）：★ 顶层给一张【可判性总表】—— ★ 哪些字段现算、哪些沿用/缺席。
    out["_decidability"] = {
        "recomputable": ["vacuous_no_failable_criterion", "vacuous_tools", "scanned",
                         "failable_tools_n", "no_entry_n", "undecidable_n", "_face"],
        "carried_forward": [k for k, v in out["_carried_forward"].items()
                            if isinstance(v, dict) and v.get("class") == "carried_forward"],
        "absent": [k for k, v in out["_carried_forward"].items()
                   if isinstance(v, dict) and v.get("class") == "absent"],
        "note": "★★ 两类字段【不可混用】：★ 现算项可复跑；★ 沿用项 ★ 不可复跑（★ 生成器已丢失）。"
                "★★★ 且沿用项的【面】与 scanned【不同】⇒ 二者相除【无意义】。"}

    p = out_path or SURVEY_DEFAULT
    tmp = p + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    os.replace(tmp, p)
    out["_written"] = os.path.relpath(p, ROOT)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=None, help="扫的面（可多次；默认 tools/scripts/research）")
    ap.add_argument("--run", action="store_true", help="★ 真跑每个 --selftest 并记退出码")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--survey", action="store_true",
                    help="★★ 重算基线 JSON（★ H5d/H5e 读它）—— ★ vacuous 用 AST 判，★ same_source 沿用旧值并标注")
    ap.add_argument("--out", default=None, help="★ 基线落盘路径（缺省 data/registry/same-source-selftest-survey-<今天>.json）")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("selftest-audit 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    rows = audit(a.root, run=a.run)
    if a.survey:
        sv = survey(rows, a.out)
        print("== selftest-audit 基线重算（★ v%s）==" % sv["version"])
        print("  扫描面：%d" % sv["scanned"])
        print("  ★★ 无判据（AST）：%d（★ 旧基线值 %s —— ★ 已知误标，只作对照）"
              % (sv["vacuous_no_failable_criterion"],
                 (sv.get("_legacy_vacuous") or {}).get("value")))
        print("  ★ 有判据（AST 见到非零出口）：%d" % sv["failable_tools_n"])
        print("  ★ 无入口：%d · ★ 不可判：%d" % (sv["no_entry_n"], sv["undecidable_n"]))
        print("  ★ 已写入：%s" % sv.get("_written"))
        return 0
    # ★★ 2026-10-12：【自我指涉】排除 —★ 本门的自证里【必然含那三条样本字符串】
    #   （★ 它们就是要被检的形态）⇒ 不排除的话它永远自报命中。
    SELF = "tools/selftest-audit.py"
    self_hits = [r for r in rows if r["file"] == SELF and r["tautologies"]]
    rows = [r for r in rows if r["file"] != SELF]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    print("== selftest-audit 1.0.0 ==")
    if not rows:
        print("  ★ 无可扫文件 ⇒ 【不可判】（★ 未抽到 ≠ 不存在）")
        return 2
    n_st = [r for r in rows if r["has_selftest"]]
    n_taut = [r for r in n_st if r["tautologies"]]
    n_nocall = [r for r in n_st if not r["calls_local"] and not r["tautologies"]]
    print("  扫描面：%d 个 .py" % len(rows))
    print("  ★ 有 selftest 的：%d" % len(n_st))
    print("  ★★ 其中【含恒真条目】的：%d" % len(n_taut))
    print("  ★ 其中【未调本地函数】的：%d" % len(n_nocall))
    print()
    if n_taut:
        print("  ❌❌ **恒真条目（★ 这些自证【无论怎么改都不会红】）**：")
        for r in n_taut:
            print("     %s" % r["file"])
            for t in r["tautologies"][:4]:
                print("        %s  `%s`" % (t["pattern"], t["snippet"]))
        print()
    if n_nocall:
        # ★★ 2026-10-12 降级（D-227）：本项是【启发式】，实测会【假报】——
        #   ★ `incident-regression` 与 `principle-landing-check` 被它报「未调本地函数」，
        #   ★★ 而实跑均 `exit=0` 且输出含【反向对照】（★ 真自证）。
        #   ★ 原因：它们用 `_t(...)` / 直接 `print`，★ **不通过 `cases.append`**。
        #   ★★★ ⇒ 故本项从【警告】降为【信息】，并明写【硬证据是 `--run`】。
        print("  ℹ️  【信息·非警告】未调本地函数的（%d 个）：" % len(n_nocall))
        print("     ★ 本项是【启发式】，会假报 —— ★ **硬证据是 `--run`**（真跑看 exit）。")
        print("     ★ 已知假报：incident-regression / principle-landing-check 用 `_t()` 与 `print`，非 `cases.append`。")
        for r in n_nocall[:12]:
            print("       %s" % r["file"])
        print()
    if a.run:
        # \u2605\u2605\u2605 2026-10-12 \u6539\u4e3a\u3010\u56db\u5206\u7c7b\u3011\uff08D-231\uff09\uff1a\u907f\u514d\u628a\u300c\u4e0d\u652f\u6301\u8be5\u65d7\u6807\u300d\u62a5\u6210\u7f3a\u9677
        cl = classify_run(rows)
        print("  \u2605 \u5b9e\u8dd1\uff1a%d \u4e2a selftest" % cl["total"])
        print("     0        \uff08\u2605 \u771f\u901a\u8fc7\uff09      : %d" % len(cl["ok"]))
        print("     2        \uff08\u2605\u2605 \u4e0d\u652f\u6301 --selftest\uff09: %d  \u2190 \u2605 \u4e0d\u5f52\u7f3a\u9677" % len(cl["usage"]))
        print("     TIMEOUT  \uff08\u2605 \u7f51\u7edc/\u4e45\u8dd1\uff09    : %d" % len(cl["timeout"]))
        print("     \u5176\u5b83\u975e 0 \uff08\u2605\u2605 \u5019\u7f3a\u9677\uff09    : %d" % len(cl["other"]))
        # \u2605\u2605 2026-10-12\uff08D-234\uff09\uff1a\u5bf9\u300c\u5019\u7f3a\u9677\u300d\u505a\u4e32\u884c\u590d\u6838\uff08\u2605 \u9632\u5e76\u53d1\u4f2a\u5931\u8d25\uff09
        rechecked = recheck_serial(rows, cl["other"]) if cl["other"] else []
        nonrepro = [r for r in rechecked if not r.get("reproducible")]
        real = [r for r in rechecked if r.get("reproducible")]
        for r in real:
            print("        \u274c %s exit=%s\uff08\u2605 \u4e32\u884c\u590d\u6838\u4ecd\u7ea2\uff09" % (r["file"], r.get("serial_exit")))
        if nonrepro:
            print("     \u2605 \u4e32\u884c\u590d\u6838\u540e\u3010\u4e0d\u590d\u73b0\u3011\uff08\u2605\u2605 \u7591\u4f3c\u5e76\u53d1\u4f2a\u5931\u8d25\uff0c\u4e0d\u7b97\u7f3a\u9677\uff09\uff1a%d \u4e2a" % len(nonrepro))
            for r in nonrepro[:8]:
                print("        ~ %s \u5e76\u53d1=%s \u2192 \u4e32\u884c=%s" % (r["file"], r.get("run_exit"), r.get("serial_exit")))
        cl["other"] = real
        if len(cl["other"]) > 20:
            print("        \u2026 \u53e6\u6709 %d \u4e2a" % (len(cl["other"]) - 20))
        if cl["usage"]:
            print("     \u2605 \u4e0d\u652f\u6301\u7684\u524d 5 \u4e2a\uff1a%s" % ", ".join(r["file"] for r in cl["usage"][:5]))
        bad = cl["other"]
        # ★★★ 2026-10-12 新增（D-228）：【探针自检】—— 防「探针坏而报告说全坏」
        #   ★ 立据：本线第一次跑 `scripts/` 面时，用 `p2.status`（★ 正确是 `returncode`）
        #   ★★ ⇒ **341 个全部被记成 `ERR:AttributeError`** ⇒ 报告说「341 个全非 0」，
        #      而**手动跑其中一个 ⇒ `exit=0`** —— ★ **那不是工具坏，是探针坏。**
        #   ★★★ ⇒ 故加：**非 0 比例 > 90% 且有 ≥3 个 ⇒ 主动报「疑似探针故障，不报为工具缺陷」**。
        _ratio = (len(bad) / len(n_st)) if n_st else 0
        if len(n_st) >= 3 and _ratio > 0.90:
            print()
            print("  ⚠️⚠️ **疑似【探针故障】，不是工具缺陷** ——")
            print("        %d/%d = %.0f%% 非 0" % (len(bad), len(n_st), _ratio * 100))
            print("        ★ 若真如此高的比例，更可能是【调用方式错】而非工具全坏。")
            print("        ★★ 请先【手动跑其中一个】核（★ 本线曾因 `p2.status` 误写致 341 个全报错）。")
        print()
    if n_taut:
        print("  ❌ %d 个工具的【自证含恒真条目】 ⇒ 依「一个断言若从未红过就不是判据」，它们不是判据" % len(n_taut))
        return 1
    print("  ✅ 未发现恒真自证条目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
