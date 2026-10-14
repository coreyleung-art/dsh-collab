#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rule-in-failure-output — 判【门的失败输出里有没有【规则号】】（★ R065 候选的可机检实现）。

★★★ 立据（2026-10-15 · ★ 由明鉴 v3 的实测逼出来，★ 而它抓到的是【本线自己的读数】）：
  ★ 本线先报「6 个门的失败输出都带规则号（6/6）」，★★ 而那是用
    **全文件 grep `R0\\d\\d`** 数出来的 —— ★★ **它量的是「文件里提到过规则号」**。
  ★★ 明鉴 v3 独立扫时逐字指出：`tools/beacon-check.py` **全文件有 R030，
    而 FAIL 行【没有】**（R030 在 docstring 与 skip() 文本里）⇒
    ★★★ **「规则号在源码里」≠「规则号在【失败输出】里」**。
  ★ 按正确的面与判据重测 ⇒ 本线读数 **不是 6/6，而是 1/6**。

★★ 判据（★ 只看【失败分支里构造的字符串】，★ 显式规则 ⇒ 可反驳）：
  · `check(<名>, False, <串>)` / `skip(...)` / `fail(...)` 的**第 3 参**；
  · 含 `verdict` 或 `why` 的 dict 字面量里的 `why` / `msg` / `detail` 值；
  · `print("FAIL …")` / `print("❌ …")` 的首参。
  ★ 命中判据：上述串里出现 `R0\\d\\d` / `R-ERR\\d+` / `J\\d\\d`。
  ★★ 若某判据的失败串是**动态判定**（第二参不是字面 False）⇒ ★ 该串**成功与失败共用** ⇒ **计入**。

★ 三态：★ 面为空 ⇒ 不可判；★ 门有失败串但**一条不带**规则号 ⇒ FAIL；★ 全部带 ⇒ PASS。

★ 边界（★ 不掩盖）：★ 它只判【串里有没有规则号】，★ **不判规则号是否【对】**（★ 对错需人核）；
  ★ 也不判规则号是否与判据真的相关。
"""
import ast
import io
import json
import os
import re
import sys

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★★★ 面【显式写死】—— ★ 明鉴 v3 问的就是这一件：「你的『6 个门』是哪 6 个」。
#   ★★ 面必须写在代码里，★ 不能靠读者猜（★ 否则两个人的分母不可比）。
FACE = [
    "tools/stability-probe.py",
    "tools/beacon-check.py",
    "tools/false-result-patterns.py",
    "tools/selftest-audit.py",
    "scripts/j44-reuse-gate.py",
    "scripts/rules-integrity.py",
]
RULE = re.compile(r'R0\d\d|R-ERR\d+|J\d\d')


def _strings(node):
    """★ 收集一个表达式里的所有字符串片段（含 f-string 与 % 拼接的字面模板）。"""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
        elif isinstance(n, ast.JoinedStr):
            for v in n.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.append(v.value)
    return out


# ★★★ 2026-10-15（★ 由明鉴 v3 抓到【本器的假阴性】）：★ 它实测 `rules-integrity.py` 在 `--net` 下
#   造真悬空 ⇒ **运行时输出逐字带 `（★ R063：声明有据 ≠ 据存在）`**，★ 而本器报它 **0**。
#   ★ 根因：本器 `print` 那一支**只认首字 `FAIL`/`❌`** ⇒ ★ 而那条明细行是
#     `print(f"   · ★★ 悬空指针(行…): …（★ R063…）")` —— **首字是 `·`** ⇒ 漏掉。
#   ★★ 修法：加一条**结构规则** —— ★ 凡 `print` 位于【以 problems/missing/fails… 为条件的 if 块内】，
#     ★ 即为**失败输出**（★ 不靠首字前缀）。
# ★★★ 2026-10-15（★ 由明鉴 v3 查出【面限度】并【实证当前无害】）：
#   ★ 原实现用 `k in c.lower()` ⇒ **关键词必须是【条件变量名的子串】**（★ 方向单一）⇒
#     `errors` **in** `err` ⇒ **✗**（★ **方向反了**）· `missing` **in** `miss` ⇒ ✗ · `bad` 不在表里。
#   ★ 它实测受影响的块：`beacon-check`（`bad` 21+11 条串 · `_miss` 6 条）· `j44-reuse-gate`（`err` 2 条）·
#     `rules-integrity`（`miss` 7 条）⇒ ★★ **逐个打开扫规则号 ⇒ 全部 0** ⇒ **原 2/6 读数成立**。
#   ★ 修法：★ **双向匹配**（★ 键在名中 ∨ 名在键中）+ ★ 补 `bad`/`miss`/`err` 等短名。
#   ★★ 并把 `FAILCON` **声明为【面】**（★ 见主输出）—— ★ **关键词表是一个面，不被声明就会被当成结论的边界**。
FAILCON = ("problems", "missing", "fails", "errors", "n_fail", "hard", "violations", "dangling",
           "bad", "miss", "err", "bads", "fails_hard")


def failure_strings(src):
    """★ 取【失败分支里构造的字符串】—— ★ 这是本件的判据核心。"""
    tree = ast.parse(src)
    par = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            par[c] = n

    def _in_failure_block(node):
        cur = node
        while cur in par:
            cur = par[cur]
            if isinstance(cur, ast.If):
                _t = ast.dump(cur.test).lower()
                # ★ 双向：键在名中 ∨ 名在键中（★ 后者修 `errors` vs `err` 这个反向）
                if any(k in _t or (len(k) >= 4 and k[:4] in _t) for k in FAILCON):
                    return True
        return False

    found = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            keys = [k.value for k in n.keys if isinstance(k, ast.Constant)]
            if "verdict" in keys or "why" in keys:
                for k, v in zip(n.keys, n.values):
                    if getattr(k, "value", None) in ("why", "msg", "detail"):
                        found += _strings(v)
        elif isinstance(n, ast.Call):
            fn = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            if fn in ("check", "skip", "fail") and len(n.args) >= 3:
                second = n.args[1]
                if isinstance(second, ast.Constant) and second.value is True:
                    continue                       # ★ 纯 PASS 分支 ⇒ 不计
                found += _strings(n.args[2])
            if fn == "print" and n.args:
                _ss = _strings(n.args[0])
                if any(x.strip().startswith(("FAIL", "❌")) for x in _ss) or _in_failure_block(n):
                    found += _ss
    return found


def audit(face=None):
    rows = []
    for rel in (face or FACE):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            rows.append({"file": rel, "state": "undecidable", "why": "★ 文件不存在"})
            continue
        try:
            ss = failure_strings(io.open(p, encoding="utf-8", errors="replace").read())
        except Exception as e:
            rows.append({"file": rel, "state": "undecidable", "why": type(e).__name__})
            continue
        hit = [s for s in ss if RULE.search(s)]
        rows.append({"file": rel, "state": "ok" if hit else "fail",
                     "failure_strings": len(ss), "with_rule": len(hit),
                     "sample_rules": sorted({RULE.search(s).group(0) for s in hit})[:4]})
    return rows


def selftest():
    ok = tot = 0

    def c(name, cond):
        nonlocal ok, tot
        tot += 1
        print("  %s %s" % ("✅" if cond else "❌", name))
        ok += 1 if cond else 0

    c("正控：`check(x, False, '... R030 ...')` 计为带规则号",
      bool([s for s in failure_strings("check('x', False, '见 R030')\n") if RULE.search(s)]))
    c("★ 负控：`check(x, True, '... R030 ...')`（纯 PASS 分支）不计",
      not failure_strings("check('x', True, '见 R030')\n"))
    c("★ 负控（明鉴的实例）：规则号只在 docstring / 非失败串里 ⇒ 不得计入",
      not [s for s in failure_strings(
          'def f():\n    """R030 在 docstring 里"""\n    print("hello R030")\n') if RULE.search(s)])
    c("正控：verdict/why dict 里的 why 计入",
      bool([s for s in failure_strings("d = {'verdict': 'FAIL', 'why': '依 R063'}\n") if RULE.search(s)]))
    c("★ 负控：含 verdict 但 why 无规则号 ⇒ 不计入",
      not [s for s in failure_strings("d = {'verdict': 'FAIL', 'why': '没有编号'}\n") if RULE.search(s)])
    c("★ 正控（明鉴的实例）：`if problems:` 块内的明细 print 计入（★ 首字是 `·` 也要算）",
      bool([s for s in failure_strings(
          "if r['problems']:\n    for p in r['problems']:\n"
          "        print(f'   · x {p}（★ R063）')\n") if RULE.search(s)]))
    c("★ 负控：不在失败块内的普通 print ⇒ 不计入",
      not [s for s in failure_strings("print('一切正常 R030')\n") if RULE.search(s)])
    c("★ 正控（明鉴的面限度实例）：条件变量名 `err`（★ 关键词 `errors` 的【反向】）⇒ 块内 print 计入",
      bool([s for s in failure_strings(
          "if err:\n    print(f'   · bad {err}（★ R030）')\n") if RULE.search(s)]))
    c("★ 正控：`bad` 也在关键词面内",
      bool([s for s in failure_strings("if bad:\n    print('· x（★ R030）')\n") if RULE.search(s)]))
    c("三态：面里有不存在的文件 ⇒ undecidable",
      audit(["_no_such_gate_.py"])[0]["state"] == "undecidable")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    if "--version" in sys.argv:
        print("rule-in-failure-output %s" % VERSION)
        return 0
    if "--selftest" in sys.argv:
        return selftest()
    rows = audit()
    if "--json" in sys.argv:
        print(json.dumps({"face": FACE, "rows": rows}, ensure_ascii=False, indent=1))
        return 0
    n_ok = len([r for r in rows if r["state"] == "ok"])
    n_fail = len([r for r in rows if r["state"] == "fail"])
    print("== rule-in-failure-output %s（★ R065 候选）==" % VERSION)
    print("  面（★ 显式清单，%d 个门）：" % len(FACE))
    # ★★ 声明【关键词面】：★ 不声明它，它的边界就会被当成结论的边界。
    print("  ★ 块判据的面：FAILCON = %d 个关键词（%s）⇒ ★ **块名落在表外者【不计入】**"
          % (len(FAILCON), ", ".join(FAILCON)))
    for r in rows:
        print("    %s %-38s 失败串 %3d · 带规则号 %2d %s"
              % ("✅" if r["state"] == "ok" else ("❌" if r["state"] == "fail" else "？"),
                 r["file"], r.get("failure_strings", 0), r.get("with_rule", 0),
                 ("例 " + ",".join(r.get("sample_rules", []))) if r["state"] == "ok" else "★ 失败输出无规则号"))
    print()
    print("  ⇒ 失败输出带规则号：%d/%d（★ 判据只看【失败分支里的串】，★ 不看全文件）" % (n_ok, len(rows)))
    if n_fail:
        print("  ❌ %d 个门的失败输出【不带规则号】 ⇒ ★ 规则未在【出错时的输出】里落地" % n_fail)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
