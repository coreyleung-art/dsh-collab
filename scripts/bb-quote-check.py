#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-quote-check.py — 引用逐字核验 v1.1.0

★★ 为什么需要它（明鉴提案 · 2026-10-14）：
  §12.10 第三维：「触发靠记得还是可判」。
  本报告的「我核了一下，没有」是【用回忆核的】⇒ 软守卫 ⇒ 下次可能漏。
  明鉴建议：**「引用」本身是一个可核验的关系** ——
    扫卡里所有「引用对方原话」处，检查那段引用【在源卡里逐字存在吗】。
    找不到 ⇒ 它是被补全/改写的。

用法:
    bb-quote-check.py <源卡键> "<引用文本>"
      exit 0 = 逐字命中（引用成立）
      exit 1 = ★ 未逐字命中 ⇒ 该引用被补全/改写/记错
      exit 2 = 不可判（源卡读不到 / 参数错）⇒ ★ 不默认放行
"""
__version__ = "1.1.0"
import json, sys, urllib.request

BB = "http://127.0.0.1:8792/"


def _fetch_text(key):
    try:
        with urllib.request.urlopen(BB + key.lstrip('/'), timeout=10) as r:
            raw = r.read().decode()
    except Exception:
        return None
    try:
        d = json.loads(raw)
        v = d.get('value') or {}
        if isinstance(v, dict) and isinstance(v.get('value'), dict):
            v = v['value']
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return raw


def main():
    if len(sys.argv) < 3:
        print("usage: bb-quote-check.py <源卡键> \"<引用文本>\""); return 2
    key, quote = sys.argv[1], sys.argv[2]
    src = _fetch_text(key)
    if src is None:
        print(f"  ✗ 不可判：读不到源卡 {key}"); return 2
    if quote in src:
        # ★ v1.1.0：报出引用长度（不按比例分类 —— 引用天然远短于源，比例无意义）
        print(f"  ✓ 逐字命中 ⇒ 该文本在源中【逐字存在】")
        print(f"    引用长度 {len(quote)} 字符（源 {len(src)} 字符）")
        print(f"    ★ 本工具只判【该文本是否逐字存在】，")
        print(f"      不判【它是否构成源的完整表述】—— 判完整性需另一次检查")
        return 0
    # 给一处有界提示：找最长公共前缀
    lo, hi = 0, min(len(quote), len(src))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if quote[:mid] in src: lo = mid
        else: hi = mid - 1
    print(f"  ★ 未逐字命中 ⇒ 该引用【被补全 / 改写 / 记错】")
    print(f"    源: {key}（{len(src)} 字符）")
    print(f"    引用前 {lo} 字符在源中逐字存在；从第 {lo+1} 字符起【源中找不到】")
    if lo:
        print(f"    逐字一致部分: …{quote[max(0,lo-24):lo]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
