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
        for r in rows:
            if r["has_selftest"]:
                try:
                    p = subprocess.run([sys.executable, os.path.join(ROOT, r["file"]), "--selftest"],
                                       capture_output=True, text=True, timeout=90)
                    r["run_exit"] = p.status
                except Exception:
                    r["run_exit"] = None
    return rows


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
        print("  ⚠️  **未调本地函数（★ 可能只调了库函数或常量；须人工看）**：")
        for r in n_nocall[:12]:
            print("     %s" % r["file"])
        print()
    if a.run:
        bad = [r for r in n_st if r.get("run_exit") not in (0, None)]
        print("  ★ 实跑：%d 个 selftest · 非 0 退出 %d 个" % (len(n_st), len(bad)))
        for r in bad:
            print("     ❌ %s exit=%s" % (r["file"], r.get("run_exit")))
        print()
    if n_taut:
        print("  ❌ %d 个工具的【自证含恒真条目】 ⇒ 依「一个断言若从未红过就不是判据」，它们不是判据" % len(n_taut))
        return 1
    print("  ✅ 未发现恒真自证条目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
