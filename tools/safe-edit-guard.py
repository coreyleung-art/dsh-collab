#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""safe-edit-guard —— 【改必跑面相关文件前的硬门】

★★★ 立据（用户 2026-10-15 裁可）：★「把 safe-edit 强制接入（★ 别名 + 必跑面相关文件必走门）」

★ 它做一件事：★ 若你要改【必跑面相关文件】而【没有走四步门】⇒ ★★ **拒绝并告诉你正确姿势**。

★ 三态：★ 在门内（有 `.draft`）⇒ 放行；★ 不在门内且是受控文件 ⇒ **exit 1**；★ 不是受控文件 ⇒ exit 0。

用法：
  python3 tools/safe-edit-guard.py <file>          # ★ 检查能不能改
  python3 tools/safe-edit-guard.py --list          # ★ 列受控文件
"""
import os
import sys

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "dsh-collab")
# ★ 受控文件（★ 必跑面相关 —★ 它们出错会直接污染判据）
GUARDED = [
    "tools/beacon-check.py",
    "tools/silent-failure-scan.py",
    "tools/industry-parity.py",
    "tools/delivery-probe.py",
    "tools/health-manager.py",
    "tools/onboarding-conformance.py",
    "tools/leadership-claims.py",
    "tools/negctl-coverage.py",
    "tools/writer-attribution-gate.py",
    "tools/stability-probe.py",
    "scripts/cahac-envelope-conformance.py",
]


def is_guarded(p):
    ap = os.path.abspath(os.path.expanduser(p))
    for g in GUARDED:
        if ap == os.path.join(ROOT, g):
            return g
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    if sys.argv[1] == "--list":
        print("★ 受控文件（%d 个）：" % len(GUARDED))
        for g in GUARDED:
            print("    %s" % g)
        return 0
    f = sys.argv[1]
    g = is_guarded(f)
    if not g:
        print("★ 不是受控文件 ⇒ 放行")
        return 0
    draft = os.path.abspath(os.path.expanduser(f)) + ".draft"
    if os.path.exists(draft):
        print("★ [门内] %s ⇒ 放行（★ 已 begin，请改 %s）" % (g, os.path.basename(draft)))
        return 0
    print("★★★ 【拒绝直接修改】%s" % g)
    print()
    print("  它是【必跑面相关文件】—★ 直接改会污染判据。")
    print("  ★★ 正确姿势（★ 四步）：")
    print("      se begin  %s" % f)
    print("      # ★ 然后改：%s.draft" % f)
    print("      se check  %s" % f)
    print("      se commit %s" % f)
    print()
    print("  ★ 为何：★ 今晚本线改 beacon-check.py 损坏 3 次（★ 42→24 · 删 5 条 · 54→51）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
