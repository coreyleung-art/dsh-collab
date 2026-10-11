#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mutation_directory_selftest.py — 证明 xdom-directory.py 的 --selftest 【会变红】（v2，对 v0.2.0）

★ 为什么必须有这一支
  本轮的教训（我对 int 的 S3）：一条控若不能被负控打红，它就是**空转绿**。
  「N PASS / 0 FAIL」在**未经变异检验**前，**不构成**它有效的证据。
  做法：把源读进内存 → 一处变异 → 内存 exec → 跑 selftest → 比对 PASS/FAIL。
  ★ 全程不落盘、不改仓库任何一行。

★ 探针自身的错（自曝，第一版）
  v1 里写了 `hit = "★ 期望控" in txt and ...` —— 那字面量只存在于**本探针源码**，
  工具输出里根本没有 ⇒ 恒 False ⇒ 四行全报「期望控未命中」。
  ★ 同族错误：**判据的对象取错了**（不是读数错）。本版已修，并逐行核命中。

用法: python3 docs/xdom-index/probe/mutation_directory_selftest.py
"""
import contextlib
import io
import re
import sys

SRC = "/Users/coreyleung/dsh-collab/docs/xdom-index/xdom-directory.py"

SORT_LINE = '    keys = sorted(k for k in logs if k.startswith(LOG_PREFIX))\n'
OWED_LINE = '    owed = [p for p in posts if p["requires_reply"]]\n'
REQ_LINE = '        requires = rr and ball not in _NO_BALL\n'
UNREAD_LINE = '                                       if p["to"] == party and (upto is None or p["key"] > upto))}\n'
REF_LINE = '    if r.startswith(LOG_PREFIX):\n        return "letter"\n'
REUSE_LINE = '    reused = {t: n for t, n in topics.items() if n >= 2}\n'

MUTANTS = [
    ("M1 欠账表 = 全部楼（丢掉 requires_reply 过滤）", OWED_LINE,
     "    owed = posts\n", "正控：要求回复的楼 = 2（t1 两楼）"),
    ("M2 去掉键序排序（改用输入顺序）", SORT_LINE,
     "    keys = [k for k in logs if k.startswith(LOG_PREFIX)]\n",
     "★ 负控：打乱输入 ⇒ 末楼仍按键序为 t2-c（不被输入序带偏）"),
    ("M3 未读判据方向反转（k>upto → k<upto）", UNREAD_LINE,
     '                                       if p["to"] == party and (upto is None or p["key"] < upto))}\n',
     "★ 负控：水位退回第一楼 ⇒ 未读=1（证明未读计数是真算的）"),
    ("M4 忽略 reply_required（只看球）", REQ_LINE,
     "        requires = ball not in _NO_BALL\n",
     "★ 拆分控：球在 int 但【明说勿回】⇒ 不要求回复"),
    ("M5 忽略 ball 的 none 判定（只要求回复）", REQ_LINE,
     "        requires = rr\n",
     "★ 拆分控：要求回但【球在 none】⇒ 不要求回复（谁也不欠）"),
    ("M6 ref 分类：把信键也判成文件路径", REF_LINE,
     '    if r.startswith(LOG_PREFIX):\n        return "path"\n',
     "★ ref 控：指向信键的边 = 1"),
    ("M7 topic 复用数 = 全部 topic（丢掉 ≥2 过滤）", REUSE_LINE,
     "    reused = topics\n",
     "★ topic 控：夹具里 t1 有 2 楼 ⇒ 被复用 topic 数 = 1"),
]


def score(src):
    """调 selftest()，捕获 stdout ⇒ (pass, fail, 文本 或 异常文本)。"""
    ns = {"__name__": "notmain", "__file__": SRC}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(src, SRC, "exec"), ns)
            ns["selftest"]()
    except Exception as e:                                    # 变异体直接崩，也算被抓到
        return -1, -1, f"{type(e).__name__}: {e}"
    text = buf.getvalue()
    m = re.search(r"selftest: (\d+) PASS / (\d+) FAIL", text)
    return (int(m.group(1)), int(m.group(2)), text) if m else (None, None, text)


def main():
    base = open(SRC, encoding="utf-8").read()
    p0, f0, _ = score(base)
    print(f"═══ 对照组（未变异）═══ {p0} PASS / {f0} FAIL")
    if p0 is None or p0 < 0:
        print("★ 对照组没跑出读数 ⇒ 无法判定")
        return 2

    bad = 0
    print("\n═══ 变异组 ═══")
    for name, anchor, repl, expect in MUTANTS:
        n = base.count(anchor)
        if n != 1:
            print(f"  ⚠ {name}: 锚点出现 {n} 次（≠1）⇒ 变异未施加，本行【不可判】")
            bad += 1
            continue
        p, f, txt = score(base.replace(anchor, repl))
        turned = (p is not None and (p < 0 or f > f0))
        hit = ("❌ " + expect) in (txt or "")
        print(f"  {'✅ 变红' if turned else '❌ 纹丝不动（空转绿！）'}  {name}\n"
              f"      {'崩溃' if (p is not None and p < 0) else f'{p} PASS / {f} FAIL'}"
              f"（对照 {p0}/{f0}） · 期望控{'确已' if hit else '★未'}命中"
              f"{'' if hit else f'「{expect}」'}")
        if not turned:
            bad += 1

    print(f"\n结论：{'★ 该自检【会变红】—— 是真控' if bad == 0 else f'★ 有 {bad} 项未通过变异检验'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
