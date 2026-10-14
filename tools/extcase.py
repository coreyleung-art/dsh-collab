#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extcase —— 【异源用例】共享模块（★ 让每个工具一行接入）

★★★★★ 立据（明鉴 2026-10-15 的一般形式 · 本线采纳）：
  ★★ **「夹具与被测共享【同一个前提】时，测试无法证伪那个前提。」**
  ★ 而它的判据：★ **「我的测试里，有没有一个输入不是我自己写的？」**
  ★★★ 若没有 ⇒ **它只能证伪我假设之外的东西。**

★★★ 而本线的普查（`D-374`/`D-375`）实证了严重性：
  ★ **349 个带自证的工具里，224 个（64%）的输入【全是作者自己写的】** ——
  ★★ **它们的全绿不能证伪它们自己的前提。**

★ 本模块提供【三种异源输入】（★ 按可取性降级，★ 且三态）：
  ① `real_cards(ns, n)`   —— ★ 从【真实黑板】读 n 张真卡（★ 最强异源）
  ② `real_files(pat, n)`  —— ★ 从【真实文件系统】列 n 个真文件（★ 中）
  ③ `real_procs(n)`       —— ★ 从【真实进程表】取 n 行（★ 弱但异源）

★ 用法（★ 一行）：
    from extcase import extcase_selftest
    ...
    ok, tot, msg = extcase_selftest()
    print(msg)

★ 三态纪律：★ 取不到异源输入 ⇒ 返回 **`None`**（★ 不可判），★ **绝不返回 False** ——
  ★ 因为「取不到」不是「被测有问题」。
"""
import io
import json
import os
import re
import subprocess
import urllib.request

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
BB = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")
ROOT = os.path.join(HOME, "dsh-collab")


def _tok():
    try:
        return open(os.path.join(HOME, ".dsh", "blackboard-token"), encoding="utf-8").read().strip()
    except Exception:
        return ""


def real_cards(ns="notes/mac-mini/manager-actions/", n=2):
    """★ 从真实黑板读 n 张真卡 ⇒ list[dict] 或 None（★ 取不到 = 不可判）"""
    try:
        req = urllib.request.Request(BB + "/" + ns.rstrip("/") + "/")
        t = _tok()
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        keys = sorted((d.get("list") or {}).keys())[-n:]
        out = []
        for k in keys:
            req2 = urllib.request.Request(BB + "/" + k)
            req2.add_header("Authorization", "Bearer " + t)
            req2.add_header("X-Blackboard-Token", t)
            try:
                with urllib.request.urlopen(req2, timeout=15) as r2:
                    v = json.loads(r2.read().decode("utf-8", "replace")).get("value")
                out.append({"key": k, "value": v})
            except Exception:
                continue
        return out or None
    except Exception:
        return None


def real_files(pat=r"^[\w\-]+\.py$", n=3, where=None):
    """★ 从真实文件系统列 n 个真文件 ⇒ list[str] 或 None"""
    d = where or os.path.join(ROOT, "tools")
    try:
        rx = re.compile(pat)
        names = [x for x in sorted(os.listdir(d)) if rx.search(x)][:n]
        return [os.path.join(d, x) for x in names] or None
    except Exception:
        return None


def real_procs(n=3):
    """★ 从真实进程表取 n 行 ⇒ list[str] 或 None"""
    try:
        p = subprocess.run(["ps", "-axo", "pid,comm"], capture_output=True, text=True, timeout=15)
        rows = [x for x in p.stdout.split("\n")[1:] if x.strip()][:n]
        return rows or None
    except Exception:
        return None


def extcase_selftest(name="extcase"):
    """★ 统一入口 ⇒ (ok, tot, msg)

    ★ 三态：★ 三种异源输入【全部取不到】⇒ ok=None（★ 不可判）。
    """
    got = []
    c = real_cards()
    if c:
        got.append("★ 真卡 %d 张（%s）" % (len(c), str(c[0].get("key"))[-28:]))
    f = real_files()
    if f:
        got.append("★ 真文件 %d 个" % len(f))
    p = real_procs()
    if p:
        got.append("★ 真进程 %d 行" % len(p))

    if not got:
        return None, 0, ("  \u2753 %s\uff1a\u3010\u5f02\u6e90\u8f93\u5165\u5168\u53d6\u4e0d\u5230\u3011"
                         "\u21d2 **\u4e0d\u53ef\u5224**\uff08\u2605 \u7a7a \u2260 \u65e0\uff1b\u2605 \u4e5f\u2260 \u88ab\u6d4b\u6709\u95ee\u9898\uff09" % name)
    return True, len(got), "  \u2705 %s\uff1a\u53d6\u5230\u3010\u5f02\u6e90\u8f93\u5165\u3011\u2014\u2605 %s" % (name, " \u00b7 ".join(got))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("extcase %s" % VERSION)
        return 0
    ok, tot, msg = extcase_selftest()
    print("== extcase %s ==" % VERSION)
    print(msg)
    print("  \u81ea\u8bc1\uff1a%s" % ("\u4e0d\u53ef\u5224" if ok is None else "%d/%d" % (tot, tot)))
    return 0 if ok is not None else 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
