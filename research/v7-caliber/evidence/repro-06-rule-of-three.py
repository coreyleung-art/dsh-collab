#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R4 · 复跑脚本 06：样本量与判据分辨力的匹配检验（rule of three）

原理（rule of three，二项比例的近似 95% 置信区间）：
    在 n 次试验中观察到 0 次失败 ⇒ 失败率的 95% 置信上界 ≈ 3/n
    等价地：成功率（到达率）的 95% 置信下界 ≈ 1 − 3/n
    来源：Binomial confidence interval（Rule of three 节，已读原文，见 05 篇 §一）

用途：回答「以本机的告警卡到达率，【== 100%】或【≥99.5%】这类判据
      在统计上能不能被这批样本支持？」

复跑：
    python3 research/v7-caliber/evidence/repro-06-rule-of-three.py
"""
import sys

# 本机现测（repro-arrival-window.py @ 2026-10-12T19:48:25）
OBS = [
    ("1h", 0),
    ("3h", 0),
    ("6h", 1),
    ("24h", 11),
    ("FULL", 352),
]

TARGETS = [0.995, 0.99, 0.95, 0.90, 0.80]


def required_n(target):
    """要以 95% 置信声称「到达率 >= target」（且 0 失败），需要多少样本。"""
    return -(-3 / (1.0 - target))  # ceil(3/(1-target))


def lower_bound(n):
    """n 次 0 失败时，到达率的 95% 置信下界。

    ★ 前置条件：rule of three 要求 n >= 3（否则 3/n > 1，下界为负、无意义）。
      不满足时返回 None，由调用方报「下界不可算（n<3）」—— 不得把负数当结果打印。
    """
    if n < 3:
        return None
    return 1.0 - 3.0 / n


def main():
    print("=" * 84)
    print("R4 复跑 06 · 样本量 vs 判据分辨力（rule of three）")
    print("=" * 84)
    print("公式：n 次试验 0 失败 ⇒ 到达率 95% 置信下界 ≈ 1 − 3/n")
    print("-" * 84)

    print("【A】本机各窗口现测样本量 ⇒ 即便【全部到达】也只能支持到哪个数")
    print("%-8s %-8s %-34s %s" % ("窗口", "样本 n", "0 失败时 95% 置信下界", "能否支持 == 100% ?"))
    for name, n in OBS:
        if n == 0:
            print("%-8s %-8d %-34s %s" % (name, n, "（不可判：样本为 0）", "否（无样本）"))
            continue
        lb = lower_bound(n)
        lb_s = "下界不可算（n<3，rule of three 前置条件不满足）" if lb is None else "%.2f%%" % (lb * 100)
        print("%-8s %-8d %-34s %s" % (name, n, lb_s, "否"))
    print()
    print("★ 「== 100%」在 rule of three 下【永远无法被有限样本支持】")
    print("  （要支持 100% 需要 n 无穷大）⇒ 该判据形式本身不可证，只能证伪。")
    print("★ rule of three 前置条件 n>=3：6h 窗口现测 n=1 ⇒ 连置信下界都算不出。")
    print("-" * 84)

    print("【B】要以 95% 置信声称「到达率 ≥ target」（0 失败），需要多少样本")
    print("%-12s %-14s %s" % ("target", "需要样本 n", "本机 24h 口径(11) 够吗"))
    for t in TARGETS:
        need = required_n(t)
        print("%-12s %-14s %s" % ("%.1f%%" % (t * 100), "%d" % need, "够" if 11 >= need else "★不够（差 %d）" % (need - 11)))
    print()
    print("★★ 关键：本机 24h 窗口样本 n=11。")
    print("   即便 11/11 全到达，符合 95%% 置信的下界也只有 %.2f%%。" % (lower_bound(11) * 100))
    print("   要支持 >=99.5%% 需 n>=%d；>=95%% 需 n>=%d。" % (required_n(0.995), required_n(0.95)))
    print("-" * 84)

    print("【C】按本机告警卡产出速率折算「要攒够样本需多久」")
    per_day = 11.0  # 24h 窗口现测 11 张
    for t in (0.995, 0.99, 0.95, 0.90):
        need = required_n(t)
        print("   target ≥%-7s 需 n=%-5d ⇒ 按 %d 张/天 折算 ≈ %.1f 天"
              % ("%.1f%%" % (t * 100), need, per_day, need / per_day))
    print()
    print("★ 注意：告警卡只在 driftCount>0 时写 ⇒ 产出速率【正比于系统有多坏】。")
    print("  ⇒ 「攒够样本」与「系统健康」在方向上相反：越健康越攒不够。")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    sys.exit(main())
