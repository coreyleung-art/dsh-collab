#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""变异测试：v1.1.2 新增的「游标上不得有信封字段」这条控，到底能不能变红？

问题（外部线提出）：
  `int` 在信里称——「其中『游标上不得有信封字段』若早存在，`:751` 当时就会红」。
  但该控断言的对象是 `cursor_value(party, upto)` **这个纯函数的返回值**；
  而 W8.2 的越界是在 `cmd_ack` 里 `val = cursor_value(...)` **之后**由 `with_envelope(val,…)` 注入的。
  ⇒ 若把那一行重新加回去，`cursor_value()` 的返回值**不变** ⇒ 该控**仍绿**？
  ⇒ 若是，这条控对它声称守护的那个回归是【空转绿】，`int` 那句话【不成立】。

做法（★ 不改仓库任何一行）：
  把源文件读进内存 → 做一处字符串变异（重新注入 W8.2）→ 在内存里 exec → 跑 --selftest。
  ★ 对照组：同一套流程跑**未变异**的源 ⇒ 应当 50/0，证明 harness 本身没把结果搞歪。

用法：
  python3 docs/xdom-diff-20261012/probe/mutation_cursor_control.py
"""
import contextlib
import io
import os
import sys

SRC = "/Users/coreyleung/dsh-collab/tools/xdom-mail.py"
ANCHOR = "    val = cursor_value(party, upto)\n"
INJECT = "    with_envelope(val, val.get(\"body\", \"\"))   # ★ 变异：把 W8.2 回归重新注入\n"


def run_selftest(code: str) -> tuple[int, str]:
    """在内存里 exec 这段源码（__name__='__main__'）并捕获 --selftest 输出。"""
    ns = {"__name__": "__main__", "__file__": SRC}
    argv = sys.argv
    sys.argv = ["xdom-mail.py", "--selftest"]
    buf = io.StringIO()
    rc = None
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, SRC, "exec"), ns)
    except SystemExit as e:
        rc = e.code
    finally:
        sys.argv = argv
    return (rc if rc is not None else -1), buf.getvalue()


def count(out: str) -> tuple[int, int, int]:
    ls = [l.strip() for l in out.splitlines()]
    return (sum(l.startswith("✅") for l in ls),
            sum(l.startswith("❌") for l in ls),
            sum(l.startswith("⚠") for l in ls))


def main() -> int:
    src = open(SRC, encoding="utf-8").read()
    n = src.count(ANCHOR)
    print(f"锚点出现次数 = {n}   （须为 1，否则变异不唯一）")
    if n != 1:
        print("★ 锚点不唯一 ⇒ 不变异，直接报「不可判」")
        return 2

    mut = src.replace(ANCHOR, ANCHOR + INJECT)
    print(f"变异后比原源多 {len(mut) - len(src)} 字节")

    print("\n—— 对照组（未变异）——")
    rc0, out0 = run_selftest(src)
    a0 = count(out0)
    print(f"  rc={rc0}  ✅={a0[0]}  ❌={a0[1]}  ⚠={a0[2]}")

    print("\n—— 变异组（把 W8.2 的游标注入加回去）——")
    rc1, out1 = run_selftest(mut)
    a1 = count(out1)
    print(f"  rc={rc1}  ✅={a1[0]}  ❌={a1[1]}  ⚠={a1[2]}")

    print("\n—— 判定 ——")
    if a1[1] == 0 and rc1 == 0:
        print("  ★★ 变异组【全绿】⇒ 「游标上不得有信封字段」这条控")
        print("     **对它声称守护的那个回归（:751 重新注入）不敏感** ⇒ 【空转绿】。")
        print("     ⇒ `int` 那句「若早存在，:751 当时就会红」**不成立**。")
    else:
        print("  ✔ 变异组【变红】⇒ 该控确实能抓到这个回归（int 的说法成立）。")
        bad = [l for l in out1.splitlines() if l.strip().startswith("❌")]
        for l in bad:
            print("    ", l.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
