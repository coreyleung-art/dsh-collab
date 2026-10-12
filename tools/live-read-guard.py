#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live-read-guard —「照抄旧读数」的疑似检测器。

★ 立据（2026-10-12）：v6.1 的读数在出件后 **28 小时内被推翻 22 处**；
  ★ 而 §3.1 那句在 **v4/v5/v6/v6.1 四代逐字继承、无一版重测**。
  ★★ 故本门查：本件的【读数】是否与【在册旧件】里的**逐字相同**。

★★★ 【本门只报「疑似」，不报「确定」】—— 理由：
  ★ 「逐字相同」有两种成因：① **照抄**（坏）② **真的没变**（好）
  ★★ 两者**在文本层同形**，★ **故本门不得报「照抄」，只能报「疑似照抄，须现测复核」**。
  ★ 这正是本仓「两成因同痕」族的又一例 —— ★ 而解药是【强制现测 + 带时刻】，不是本门。

用法：
  live-read-guard.py --draft <本件.md> --reference <旧件.md> [--threshold 3]
三态：draft 或 reference 读不到 ⇒ 「不可判」；无共同读数 ⇒ 「不适用」；有 ⇒ 列疑似。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★ 读数形态：N/M · 百分比 · N 条/项/个/处/次/批
RE_READS = [
    ("ratio", re.compile(r'\b\d{1,5}\s*/\s*\d{1,5}\b')),
    ("pct", re.compile(r'\b\d{1,3}(?:\.\d+)?\s*[%％]')),
    ("count", re.compile(r'\b\d{1,6}\s*(?:条|项|个|处|次|批)')),
]


def extract(text):
    out = {}
    for kind, rx in RE_READS:
        for m in rx.finditer(text):
            v = re.sub(r'\s+', '', m.group(0))
            out.setdefault(v, {"kind": kind, "count": 0})
            out[v]["count"] += 1
    return out


def load(path):
    if not os.path.exists(path):
        return None
    try:
        return io.open(path, encoding="utf-8").read()
    except Exception:
        return None


def compare(draft_text, ref_text):
    d = extract(draft_text)
    r = extract(ref_text)
    common = sorted(set(d) & set(r))
    only_d = sorted(set(d) - set(r))
    only_r = sorted(set(r) - set(d))
    return d, r, common, only_d, only_r


def selftest():
    ok = tot = 0
    # ★ 正控：两边都有 16.48% ⇒ 必须出现在 common
    tot += 1
    d, r, c, _, _ = compare("到达率 16.48% 与旧件相同", "旧件记 16.48%")
    if "16.48%" in c:
        ok += 1
        print("  ✅ 正控：共同读数 `16.48%%` ⇒ 进 common（★ 可报疑似）")
    else:
        print("  ❌ 正控：共同读数未进 common")
    # ★ 负控：只在一侧 ⇒ 不进 common
    tot += 1
    _, _, c2, od, _ = compare("本件 91.67%", "旧件 16.48%")
    if "91.67%" in od and "91.67%" not in c2:
        ok += 1
        print("  ✅ 负控：单侧读数 ⇒ 进 only_draft、不进 common")
    else:
        print("  ❌ 负控：单侧读数判错")
    # ★ 负控：文本完全不同 ⇒ common 为空（可红）
    tot += 1
    _, _, c3, _, _ = compare("一二三", "四五六")
    if not c3:
        ok += 1
        print("  ✅ 负控：无共同读数 ⇒ common 空（可红）")
    else:
        print("  ❌ 负控：不相关文本竟有共同读数")
    # ★ 三态：不存在的文件 ⇒ load 返回 None
    tot += 1
    if load("/tmp/__no_such_draft__.md") is None:
        ok += 1
        print("  ✅ 负控：文件不存在 ⇒ None（★ 调用方报「不可判」）")
    else:
        print("  ❌ 负控：不存在的文件竟返回内容")
    # ★ 正控：计数形态（N 条）可被抽到
    tot += 1
    if "205条" in extract("台账 205 条"):
        ok += 1
        print("  ✅ 正控：计数形态 `205 条` 可抽")
    else:
        print("  ❌ 正控：计数形态抽不到")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft")
    ap.add_argument("--reference")
    ap.add_argument("--threshold", type=int, default=3, help="疑似门槛：共同读数 ≥ N 条才报")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("live-read-guard 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    if not (a.draft and a.reference):
        print("用法: live-read-guard.py --draft <本件.md> --reference <旧件.md> | --selftest | --version")
        return 2
    dt, rt = load(a.draft), load(a.reference)
    if dt is None:
        print("★ draft 不可读 ⇒ 【不可判】（★ 不冒充通过）: %s" % a.draft)
        return 2
    if rt is None:
        print("★ reference 不可读 ⇒ 【不可判】（★ 不冒充通过）: %s" % a.reference)
        return 2
    d, r, common, only_d, only_r = compare(dt, rt)
    if a.json:
        print(json.dumps({"common": common, "only_draft": only_d, "only_reference": only_r},
                         ensure_ascii=False, indent=1))
        return 0
    print("== live-read-guard 1.0.0 ==")
    print("  draft     : %s（%d 个读数）" % (a.draft, len(d)))
    print("  reference : %s（%d 个读数）" % (a.reference, len(r)))
    print("  ★ 共同读数 %d · 仅本件 %d · 仅旧件 %d" % (len(common), len(only_d), len(only_r)))
    if not d or not r:
        print("  ★ 一侧无读数 ⇒ 本门【不适用】（★ 不是通过）")
        return 0
    if len(common) < a.threshold:
        print("  ★ 共同读数 < 门槛 %d ⇒ ★ 未见系统性疑似（★ 但【低重合 ≠ 已现测】）" % a.threshold)
        return 0
    print()
    print("  ★★ 疑似照抄（★ 【仅疑似】—— 逐字相同有两种成因：照抄 / 真的没变，★ 文本层同形）")
    for v in common[:20]:
        print("    ? %-14s [%s]" % (v, d[v]["kind"]))
    if len(common) > 20:
        print("    … 另有 %d 条" % (len(common) - 20))
    print()
    print("  ❌ %d 条共同读数 ⇒ ★★ **须逐条现测并附时刻**；★ 本门【不判照抄】" % len(common))
    return 1


if __name__ == "__main__":
    sys.exit(main())
