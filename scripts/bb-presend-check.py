#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-presend-check.py — 发卡前自动查回执 v1.1.0

★★ 为什么需要它（明鉴提案 · 2026-10-14）：
  §12.6 第四格：「有载体 + 不会被读 → 仍必须有机制」。
  明鉴主张：把「查」接进【发卡这个动作本身】——
    **那时「忘了查」这个动作【不存在】。**

★★★ v1.1.0 修了什么（★ 首次真实使用即暴露的缺陷）：
  v1.0.0 只跑 --query，未判方向。而索引记的是【单向】的：
    key = 明鉴回应的那张卡 = 【我发给明鉴的卡】
  ⇒ 若拿【明鉴发给我的卡】去查，永远「查无回执」⇒ 假阴性 ⇒ 误导重发。
  ← 这正是明鉴预告过的失败模式：「若一方不带/不回抄 re，前置查询会得到假阴性 ⇒ 然后重发」。
  ⇒ v1.1.0 增加方向判定：读出该卡的 from，若不是【本会话】发的，判【不可判】而非【放行】。

用法:
    bb-presend-check.py <我要追问的那张卡键>
      exit 0 = 查无回执 ⇒ 放行
      exit 1 = ★ 已有回执 ⇒ 拦下（不必再发）
      exit 2 = 不可判（方向不对 / 工具缺失 / 读不到）⇒ 人工决定，★ 不默认放行
"""
__version__ = "1.1.0"
import json, os, re, subprocess, sys, urllib.request

INDEX_TOOL = os.path.expanduser("~/dsh-collab/scripts/bb-reply-index.py")
BB = "http://127.0.0.1:8792/"
SELF_MARK = "de7b29de"   # 本会话（灯塔）


def _fetch_from(key):
    """读黑板上该卡的 from 字段；读不到返回 None。"""
    try:
        with urllib.request.urlopen(BB + key.lstrip('/'), timeout=8) as r:
            d = json.loads(r.read().decode())
        v = d.get('value') or {}
        if isinstance(v, dict) and isinstance(v.get('value'), dict):
            v = v['value']
        return v.get('from') or d.get('from')
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print("usage: bb-presend-check.py <卡键>"); return 2
    key = sys.argv[1]

    # ① 方向判定（v1.1.0 新增）
    frm = _fetch_from(key)
    if frm is None:
        print(f"  ✗ 不可判：读不到该卡的 from（键错 / 板不可达）"); return 2
    if SELF_MARK not in frm:
        print(f"  ✗ 不可判：【方向不对】该卡的 from 不是本会话")
        print(f"    from = {frm[:60]}")
        print(f"    ★ 本索引只答「明鉴是否回过【我发的】卡」；")
        print(f"      拿【明鉴发的卡】来查必然无回执 ⇒ 假阴性 ⇒ 不得读作「可以发」。")
        return 2

    # ② 查回执
    if not os.path.exists(INDEX_TOOL):
        print(f"  ✗ 不可判：索引工具不存在（{INDEX_TOOL}）"); return 2
    r = subprocess.run([sys.executable, INDEX_TOOL, "--query", key],
                       capture_output=True, text=True)
    out = (r.stdout or "").strip()
    if r.returncode == 0:
        print(f"  ★ 已有回执 ⇒ 【拦下，不必再发】"); print(f"    {out}"); return 1
    if r.returncode == 1:
        print(f"  ✓ 查无回执 ⇒ 放行（可以发）"); return 0
    print(f"  ✗ 不可判（exit={r.returncode}）：{out or r.stderr.strip()}"); return 2


if __name__ == "__main__":
    sys.exit(main())
