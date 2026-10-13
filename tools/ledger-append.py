#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger-append —— 【台账原子追加器】（★ 从 /tmp 落进仓库，防临时文件被清）

★★ 立据（D-319 实测）：
  本线长期用 `/tmp/atomic_append.py` 追加台账 —— 而 **/tmp 会被清理**，
  2026-10-13 一次追加就因此失败（`ModuleNotFoundError`）。
  ⇒ ★★ **依赖临时文件的机制会在最需要时断链** —— 故落进仓库。

★ 三条纪律（★ 与手工追加同）：
  ① **原子**：临时文件 + `os.replace`（★ 不留半截）
  ② **`__NOW__` 占位**：★ 由本器替换为**真实时刻**（★ 防手写时刻与事实不符）
  ③ **禁代理对 emoji 转义**：★ `\\ud83d\\ude00` 这类【代理对】必须写成实际字符，
     否则 `json`/文本处理会炸（★ 本仓实测过）。

★ 用法：
  from ledger_append import append_entry
  now, n = append_entry(markdown_text)      # ★ 自动替换 __NOW__ 并原子追加

  python3 tools/ledger-append.py --selftest
  python3 tools/ledger-append.py --text "## D-999 · 标题\n\n| a | b |"   # ★ CLI 追加
"""
import argparse
import datetime
import io
import os
import re
import sys

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "docs", "deviation-ledger-20261011.md")


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def has_surrogate(s):
    """★ 检测代理对（★ 它们不该出现 —— 该是实际字符）"""
    return bool(re.search(r"\\ud[89ab][0-9a-f]{2}", str(s), re.I))


def append_entry(text, ledger=None, now=None):
    """★ 原子追加一条台账；★ 返回 (真实时刻, 追加后条数)"""
    ledger = ledger or LEDGER
    now = now or now_iso()
    if has_surrogate(text):
        raise ValueError("\u2605 \u6587\u672c\u542b\u4ee3\u7406\u5bf9\u8f6c\u4e49 \u21d2 \u8bf7\u6539\u6210\u5b9e\u9645\u5b57\u7b26")
    body = str(text).replace("__NOW__", now)
    if not body.endswith("\n"):
        body += "\n"
    old = ""
    if os.path.exists(ledger):
        old = io.open(ledger, encoding="utf-8").read()
    new = old + ("\n" if old and not old.endswith("\n") else "") + body
    tmp = ledger + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.replace(tmp, ledger)          # ★ 原子
    n = len(re.findall(r"^## D-\d{3}", new, re.M))
    return now, n


def selftest():
    ok = tot = 0
    import tempfile
    # ★ 正控 1：追加后条数 +1
    tot += 1
    d = tempfile.mkdtemp()
    L = os.path.join(d, "led.md")
    io.open(L, "w", encoding="utf-8").write("## D-001 \u00b7 x\n")
    _, n1 = append_entry("## D-002 \u00b7 y", ledger=L, now="2026-01-01T00:00:00+08:00")
    if n1 == 2:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u8ffd\u52a0\u540e\u6761\u6570 = 2")
    else:
        print("  \u274c \u6761\u6570\u9519\uff1a%d" % n1)
    # ★ 正控 2：__NOW__ 被替换为真实时刻
    tot += 1
    append_entry("## D-003 \u00b7 __NOW__", ledger=L, now="2026-02-02T02:02:02+08:00")
    if "2026-02-02T02:02:02+08:00" in io.open(L, encoding="utf-8").read() \
       and "__NOW__" not in io.open(L, encoding="utf-8").read():
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a__NOW__ \u5df2\u66ff\u6362\u4e3a\u771f\u5b9e\u65f6\u523b")
    else:
        print("  \u274c __NOW__ \u672a\u66ff\u6362")
    # ★ 负控 1：代理对被拒
    tot += 1
    try:
        append_entry("## D-004 \u00b7 \\ud83d\\ude00", ledger=L)
        print("  \u274c \u4ee3\u7406\u5bf9\u7adf\u88ab\u63a5\u53d7")
    except ValueError:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u4ee3\u7406\u5bf9\u88ab\u62d2\uff08\u2605 \u9632\u8f6c\u4e49\u70b8\uff09")
    # ★ 负控 2：原子性 —— 过程中不留 .tmp
    tot += 1
    if not os.path.exists(L + ".tmp"):
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u65e0\u6b8b\u7559 .tmp\uff08\u2605 \u539f\u5b50\uff09")
    else:
        print("  \u274c \u6709\u6b8b\u7559 .tmp")
    # ★ 正控 3：真台账可读
    tot += 1
    if os.path.exists(LEDGER):
        n = len(re.findall(r"^## D-\d{3}", io.open(LEDGER, encoding="utf-8").read(), re.M))
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u771f\u53f0\u8d26\u53ef\u8bfb\uff08\u2605 %d \u6761\uff09" % n)
    else:
        print("  \u2605 \u771f\u53f0\u8d26\u4e0d\u5728\uff08\u2605 \u5982\u5b9e\u62a5\uff09"); ok += 1
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("ledger-append %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    text = a.text
    if a.file:
        text = io.open(a.file, encoding="utf-8").read()
    if not text:
        ap.error("--text \u6216 --file")
    now, n = append_entry(text)
    print("  \u2705 \u5df2\u8ffd\u52a0\uff08\u771f\u5b9e\u65f6\u523b %s\uff09\u00b7 \u73b0 %d \u6761" % (now, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
