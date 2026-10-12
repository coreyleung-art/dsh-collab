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
                return rel, p.returncode           # ★ returncode，不是 status
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
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=None, help="扫的面（可多次；默认 tools/scripts/research）")
    ap.add_argument("--run", action="store_true", help="★ 真跑每个 --selftest 并记退出码")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("selftest-audit 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    rows = audit(a.root, run=a.run)
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
        for r in cl["other"][:20]:
            print("        \u274c %s exit=%s" % (r["file"], r.get("run_exit")))
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
