#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cardfmt.py —— 卡正文模板填充（**禁止 `%` 格式化**，2026-10-04 建立）

【为什么存在】（hazards 类别 E：测量/工具本身错；同一坑**踩了两次**）
  我用 `body % (...)` 拼卡正文，而正文里天然含 `%`（如「拦截率 100%」）⇒
  `ValueError: unsupported format character` 或**参数错位**。
  两次实测：`report-r43-contribution.py`、`report-side-export-delivery.py` 各一次。
  ⇒ 规则：**卡正文一律用占位符 `.replace()`，并且必须断言「没有漏填的占位符」**。

【工具化点】`fill()` 在**漏填时会报错**，而不是把 `@@XXX@@` 原样发出去（那正是"静默脏数据"）。

用法：
    from cardfmt import fill
    body = fill("板键: @@KEY@@  字节: @@N@@", KEY=k, N=len(raw))
"""
import re

TOKEN = re.compile(r"@@([A-Z0-9_]+)@@")


def fill(tpl, **kw):
    """按 `@@NAME@@` 填充；**漏填即抛错**（fail-closed），并在返回前断言无残留占位符。"""
    def sub(m):
        k = m.group(1)
        if k not in kw:
            raise KeyError("模板占位符 @@%s@@ 没有提供值（数值/键名拼错？）" % k)
        return str(kw[k])
    out = TOKEN.sub(sub, tpl)
    left = TOKEN.findall(out)
    if left:
        raise ValueError("填充后仍有未替换占位符: %s" % left[:5])
    return out


def _selftest():
    ok = True

    def ck(name, cond):
        nonlocal ok
        ok = ok and cond
        print("  %s %s" % ("✅" if cond else "❌", name))

    ck("基本填充", fill("a=@@A@@ b=@@B@@", A=1, B="x") == "a=1 b=x")
    ck("正文含 % 不受影响（本次动机）",
       fill("拦截率 100% ⇒ @@R@@%", R=99.5) == "拦截率 100% ⇒ 99.5%")
    try:
        fill("x=@@MISSING@@", A=1); ck("漏填应抛 KeyError", False)
    except KeyError:
        ck("漏填应抛 KeyError", True)
    # 同一占位符多次出现
    ck("同占位符多处替换", fill("@@K@@ / @@K@@", K="k") == "k / k")
    print("\n  ⇒ %s" % ("全部通过" if ok else "有失败项"))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
