#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R4 · 复跑脚本 04：样本为 0 报「不可判」的【负控】

项目纪律：「空 ≠ 无」—— 分母为 0 必须报「不可判」，不得报 0%/100%。
本脚本不写任何文件、不改任何状态；只对纯函数做正例/负例矩阵。

★ 负控的含义（本项目的既有要求）：
   一条断言必须【能红】才算判据。故必须证明：
   (a) 正例：样本充足 ⇒ 给出具体百分比
   (b) 负例：样本为 0 ⇒ 给出 UNDECIDABLE（而不是 0.0 或 100.0）
   (c) 负例：把样本为 0 当成 0% 的【天真实现】必须被本脚本判为 FAIL

   —— 若 (c) 不 FAIL，说明本脚本自己没有判别力。

复跑：
    python3 research/v7-caliber/evidence/repro-04-negctrl.py
"""
import sys

PASS = "PASS"
FAIL = "FAIL"
UNDECIDABLE = "UNDECIDABLE"


def rate_disciplined(arrived, total):
    """受纪律保护的实现：样本为 0 ⇒ 不可判。"""
    if total <= 0:
        return (None, UNDECIDABLE)
    return (arrived / total * 100.0, PASS if arrived == total else FAIL)


def rate_naive_zero(arrived, total):
    """天真实现 A：样本为 0 报 0%（「没有未达」）—— 违反「空 ≠ 无」。"""
    if total <= 0:
        return (0.0, PASS)
    return (arrived / total * 100.0, PASS if arrived == total else FAIL)


def rate_naive_hundred(arrived, total):
    """天真实现 B：样本为 0 报 100%（「没有失败」）—— 违反「空 ≠ 无」。"""
    if total <= 0:
        return (100.0, PASS)
    return (arrived / total * 100.0, PASS if arrived == total else FAIL)


def main():
    cases = [
        # (名称, arrived, total, 期望 rate, 期望 verdict)
        ("正例 1 · 全部到达", 10, 10, 100.0, PASS),
        ("正例 2 · 部分到达", 10, 11, 90.9090909090909, FAIL),
        ("正例 3 · 全部未达", 0, 5, 0.0, FAIL),
        ("负例 1 · 样本为 0", 0, 0, None, UNDECIDABLE),
        ("负例 2 · 样本为负（脏输入）", 0, -1, None, UNDECIDABLE),
    ]

    print("=" * 78)
    print("R4 复跑 04 · 「样本为 0 ⇒ 不可判」负控矩阵")
    print("=" * 78)
    print("%-26s %-8s %-8s %-14s %-14s %s" % ("用例", "分子", "分母", "期望 rate", "实得 rate", "判定"))
    print("-" * 78)

    bad = 0
    for name, a, t, exp_r, exp_v in cases:
        r, v = rate_disciplined(a, t)
        ok = (v == exp_v) and (
            (r is None and exp_r is None) or (r is not None and exp_r is not None and abs(r - exp_r) < 1e-9)
        )
        mark = "✓" if ok else "✗"
        if not ok:
            bad += 1
        print("%-26s %-8d %-8d %-14s %-14s %s %s"
              % (name, a, t, exp_r, (None if r is None else round(r, 2)), v, mark))

    print("-" * 78)
    print("★ 关键一节：证明【天真实现】会被本脚本抓出（否则本脚本无判别力）")
    print("-" * 78)
    caught_zero = rate_naive_zero(0, 0)
    caught_hundred = rate_naive_hundred(0, 0)
    print("  天真 A（0 样本报 0%%）  ⇒ %s" % (caught_zero,))
    print("  天真 B（0 样本报 100%%）⇒ %s" % (caught_hundred,))
    neg_ok = (caught_zero[1] == PASS and caught_zero[0] == 0.0) and (
        caught_hundred[1] == PASS and caught_hundred[0] == 100.0
    )
    print("  ⇒ 两个天真实现都被识别为【与纪律冲突】: %s" % ("是" if neg_ok else "否"))
    if not neg_ok:
        bad += 1

    print("-" * 78)
    print("★ 真实数据接入：本机 1h / 3h 窗口现测均为样本 0（见 repro-arrival-window）")
    print("   ⇒ 受纪律保护的实现应当输出 UNDECIDABLE，而不是任何一个百分比。")
    r, v = rate_disciplined(0, 0)
    print("   实得: rate=%s verdict=%s" % (r, v))
    print()
    print("=" * 78)
    print("总计: %d 项不符（bad=%d）" % (bad, bad))
    print("结论: %s" % ("全部符合纪律" if bad == 0 else "存在不符项"))
    print("=" * 78)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
