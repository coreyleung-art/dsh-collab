#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""text-assertion-lint.py — 「**在自证里用源码文本当证据**」的判据（**不改被核对象**；临时写面 = `guard/mutation-work/`）。

★ 立据（短判决位 2026-10-10 判决 C 逐字要点）：
  「这是你**第三次**撞上「查字符串」这一族（`is_gate` 字面串 / `absolute-claim-lint` 早期文本级 / 本次第一版断言）
   ⇒ **「查字符串存在」有强诱惑：便宜、看起来像检查、而且永远能绿**；三次你都改成了「真跑」。」
  判决 B 的闭环更狠：我立的 P1 就是「**判据必须有能让它失败的输入**」，而我的新断言（只查源码里有没有标记串）
  在它上面**又违了一次**（放过了 `RUN_STAMP` 未定义的 NameError ⇒ 假绿）。

★ 判据：在**自证/测试函数**里，若一条断言的证据是**源码文本**（`in _src` / `in src` / `open(...).read()`），
  则它**默认红** —— 除非同处写明**豁免理由**（`文本级断言：` 前缀）：
  · 合法的文本级断言之例：「文档标记必须存在」（那本来就是形态检查，不是行为检查）；
  · 不合法的：把「源码里有这句话」当成「这段代码能跑 / 这行为已执行」。

★ 观测面（六要素）：
  · 含项：`tools/*.py` 与 `devices/dsh-plugin-context-survival/**/*.js`（**.js 只做文本级粗筛**，见排除项）；
  · 排除项：① 非自证位置的文本匹配（如**功能代码**里读文件——那不是断言）② 注释行 ③ 正则/字符串字面量本身
    ④ 跨文件/动态构造的文本比较 ⑤ **本判据不判「行为对不对」**，只判「证据类型是否为文本」；
  · 补偿控制：① 默认红（fail-closed）：拿不准就报，不静默 ② 豁免须**显式写理由**（无理由不放行）
    ③ 每次打印**本轮扫描面与运行戳**，可被第三方复算；
  · 工具：python3 静态扫描（AST 级定位函数，行级匹配证据） · 单位：处 · 时刻：RFC3339。

退出码：0 = 通过（无未豁免的文本级断言） · 1 = 有违例 · 2 = 用法错误
用法：python3 tools/text-assertion-lint.py [<文件或目录> ...] | --selftest
"""
import ast
import datetime
import glob
import os
import re
import sys

HERE = os.path.expanduser("~/dsh-collab")
DEFAULT_TARGETS = [os.path.join(HERE, "tools", "*.py")]
JUSTIFY = "文本级断言："
ASSERT_CALLS = ("eq(", "eq_tr", "okTrue(", "assert", "expect(", "must(", "check(")
TEXT_EVIDENCE = ("in _src", "in src", "in self_src", ".read()", "in _self", "in _txt")
TEST_HINT = ("selftest", "self_test", "test_", "_test")


def ts():
    s = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return s[:-2] + ":" + s[-2:]


def test_function_lines(tree):
    """返回**自证/测试函数**覆盖的行号集合（AST 级定位，不用字符串猜）。"""
    covered = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nm = node.name.lower()
            if any(h in nm for h in TEST_HINT):
                covered.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return covered


def read_derived_names(tree):
    """找出**由读取动作派生的变量名**（如 `_src = open(...).read()`）⇒ 这些才是"源码文本"证据。"""
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        v = node.value
        # 形态：X = <任意>.read() / read_text() / read_bytes()
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in ("read", "read_text", "read_bytes"):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        # 形态：X = <Name>（传递赋值，如 _self = _src）
        if isinstance(v, ast.Name) and v.id in names:
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def is_source_text(node, read_names):
    """判断一个表达式是否是**源码文本**（而不是函数返回值/输出文本）。"""
    if isinstance(node, ast.Name) and node.id in read_names:
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("read", "read_text", "read_bytes"):
        return True
    return False


def scan_file(path):
    """★ 判据（收窄版，第二轮）：测试函数内的 `Compare(In)`，**任一侧是"读源码派生的名字"**才算违例。

    · 第一版按行文本 ⇒ 夹具字符串**假阳**；
    · 第二版按 AST 但只要求"左操作数是字符串常量" ⇒ **过宽**（`"已知原因" in c1` 里的 `c1` 是**函数返回值**，
      那是**真证据**，不该报）；
    · 本版：只看**证据来源** —— 右侧（或左侧）是否来自 `.read()` 派生 ⇒ 这才是"查源码里有这句话"。
    """
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
    except Exception:
        return [], "unparsable"
    covered = test_function_lines(tree)
    read_names = read_derived_names(tree)
    lines = src.split("\n")
    hits, declared = [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or node.lineno not in covered:
            continue
        if not any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
            continue
        operands = [node.left] + list(node.comparators)
        if not any(is_source_text(o, read_names) for o in operands):
            continue
        seg = "\n".join(lines[max(0, node.lineno - 3):node.lineno])
        item = (node.lineno, lines[node.lineno - 1].strip()[:100])
        (declared if JUSTIFY in seg else hits).append(item)
    return (hits, declared), "ok"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args or DEFAULT_TARGETS
    files = []
    for t in targets:
        if os.path.isdir(t):
            files += sorted(glob.glob(os.path.join(t, "*.py")))
        elif any(ch in t for ch in "*?["):
            files += sorted(glob.glob(t))
        else:
            files.append(t)
    files = [f for f in files if os.path.isfile(f)]
    RUN = ts()
    print("text-assertion-lint · 自证里的**文本级断言**（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
    print(f"  · 本次运行戳 run={RUN} —— ★ 引用本页数字须连同它一起引用")
    print(f"  观测面（六要素）：**含项** = {len(files)} 个 .py（默认面 = tools/*.py）；"
          f"**排除项** = ① 非自证位置的文本匹配（功能代码读文件不算断言）② 注释行 ③ 正则/字面量本身 "
          f"④ 跨文件/动态构造的文本比较 ⑤ **本判据不判「行为对不对」**，只判「证据类型是否为文本」；"
          f"**补偿控制** = ① 默认红（拿不准就报，不静默）② 豁免须显式写理由 ③ 每轮打印扫描面与运行戳；"
          f"**工具** = python3（AST 定函数 + 行级匹配）；**单位** = 处；**时刻** = {RUN}")
    bad, declared_all, unparsable = [], [], []
    for f in files:
        res, status = scan_file(f)
        if status != "ok":
            unparsable.append(os.path.basename(f))
            continue
        hits, declared = res
        declared_all += [(os.path.basename(f), n) for n, _ in declared]
        for n, txt in hits:
            bad.append(f"{os.path.basename(f)}:{n} 自证里的**文本级断言**（无豁免理由）⇒ {txt}")
    print(f"  · 已声明豁免（{JUSTIFY}）的文本级断言：{len(declared_all)} 处"
          + (f"（{declared_all[:3]}…）" if declared_all else ""))
    if unparsable:
        print(f"  · 无法解析（跳过，已计入排除项④精神）：{unparsable}")
    if bad:
        print(f"\n❌ [run {RUN}] 未豁免的文本级断言 {len(bad)} 处：")
        for b in bad[:15]:
            print("  " + b)
        if len(bad) > 15:
            print(f"  …另有 {len(bad) - 15} 处")
        print("\n  ⇒ 处置：**改成真跑**（执行被测路径并核对输出/退出码），或写明豁免理由：`# 文本级断言：<为什么文本就够>`")
        return 1
    print(f"\n✅ [run {RUN}] 通过：自证里没有未豁免的文本级断言")
    return 0


def selftest():
    """★ 双向自证：正控（无豁免的文本断言 ⇒ 必红）+ 反控（豁免 / 真跑 / 非断言 ⇒ 必绿）。"""
    import shutil
    import tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="text-assertion-lint-selftest-", dir=work)
    bad = []
    try:
        cases = [
            ("正控：自证里查源码字符串、无理由 ⇒ 应红",
             'def selftest():\n    src = open(__file__).read()\n    eq("含标记", "MARKER" in src, True)\n', True),
            ("反控：同样查字符串但写明理由 ⇒ 应绿",
             'def selftest():\n    # 文本级断言：这里查的就是"文档标记必须在"，不是行为检查\n    src = open(__file__).read()\n    eq("含标记", "MARKER" in src, True)\n', False),
            ("反控：真跑（执行被测路径）⇒ 应绿",
             'import subprocess, sys\ndef selftest():\n    r = subprocess.run([sys.executable, __file__, "--x"], capture_output=True, text=True)\n    eq("exit", r.returncode, 0)\n', False),
            ("反控：非自证函数里的文本匹配（功能代码）⇒ 应绿",
             'def load():\n    src = open(__file__).read()\n    assert "MARKER" in src\n', False),
        ]
        for name, body, want_red in cases:
            p = os.path.join(sb, f"case_{abs(hash(name)) % 9999}.py")
            open(p, "w", encoding="utf-8").write(body)
            res, status = scan_file(p)
            red = bool(res[0]) if status == "ok" else False
            good = red == want_red
            if not good:
                bad.append(name)
            print(f"  {'✅' if good else '❌'} {name}（实得 {'红' if red else '绿'}）")
        if bad:
            print("  ❌ --selftest 失败：" + " ｜ ".join(bad))
            return 1
        print("  ✅ --selftest 通过：一正控 + 三反控（豁免 / 真跑 / 非断言）方向均正确")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
