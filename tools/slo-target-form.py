#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slo-target-form —「SLO 目标是否为【可判形态】」的机械核验门。

★ 立据（2026-10-12 · v7 撰写代理 W4 实测）：
  ★ 锚点 §12 的 **14 个 SLO 指标** 里，**3 条判定为「不可判」** ——★ 而根因【是同一个】：
    · ① 信标新鲜度 ：「**1 次状态变化**」⇒ ★ **无分母定义**（★ 何为「一次」？）
    · ⑩ bus 单文件 ：「**无整份读写**」⇒ ★ **是一个架构性质，不是一个数**
    · ⑭ 端口稳定性 ：「**固定**」⇒ ★ **是一个形容词，不是一个判据**
  ★★ ⇒ 故本门查的不是「指标达没达标」，而是【**这个目标本身能不能被判定**】。

本门查四件（★ 缺一即「不可判」）：
  F1 **有量**：目标里含可比较的数或率（`≤ N` / `≥ N` / `N%` / `N/M`）
  F2 **有窗口**：目标里含时间窗（`24h` / `7d` / `每次` / `连续` / `单次`）
  F3 **有分母**：目标里含被量的面（`通道` / `会话` / `项` / `条` / `文件` / `端口` …）
  F4 **元语言检测**：目标若只由【形容词 / 架构性质】构成（固定 · 稳定 · 无 · 全 · 一致）⇒ **fail**

三态：目标为空 ⇒ 「不可判」；四件齐 ⇒ PASS；缺项 ⇒ FAIL（★ 并列出缺哪件）。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── F1 有量 ──
RE_QUANT = re.compile(r'(≤|>=|≥|<|>|=)\s*\d|^\s*\d+(?:\.\d+)?\s*[%％]|\d+\s*[%％]|\d+\s*/\s*\d+|\d+(?:\.\d+)?\s*(?:MB|GB|KB|s|ms|min|h|d|天|分钟|秒|次|条|项|个)')
# ── F2 窗口 ──
RE_WINDOW = re.compile(r'\d+\s*(?:h|d|min|s|小时|天|分钟|秒|周|月)|24h|7d|每次|单次|连续|逐次|自\s*\d|窗口')
# ── F3 分母 ──
SURFACE_WORDS = ["通道", "会话", "项", "条", "文件", "端口", "指标", "判据", "卡", "键", "节点",
                 "设备", "进程", "插件", "工具", "行", "字节", "事件", "订单", "店", "面"]
# ── F4 元语言（★ 纯形容词/架构性质 ⇒ 不可判） ──
META_ADJ = ["固定", "稳定", "无整份", "全绿", "一致", "健康", "良好", "充分", "合理", "完善",
            "顺畅", "健全", "优雅", "靠谱"]


def judge(target):
    """★ 返回 (verdict, missing_list, evidence)

    ★★ 2026-10-12 修（★ 首版过严，自证抓到）：
      ★ 首版把 F2（窗口）当【无条件要求】⇒ 对 14 个指标报 FAIL 13 ——
      ★★ 而锚点原文里「≤500MB」「≥80%」「≤10」这类目标**本来就不需要时间窗**
        （★ 它们是【存量快照量】，不是【时间相关量】）。
      ★ 而 W4 的独立判定真不可判的只有 3 条（①「1 次状态变化」· ⑩「无整份读写」· ⑭「固定」）。
      ★★★ ⇒ 故 F2 改为【条件性】：**仅当目标含时间相关词时**才要求窗口。
    """
    if not target or not target.strip():
        return "UNDECIDABLE", ["目标为空"], {}
    t = target.strip()
    f1 = bool(RE_QUANT.search(t))
    # ★ 时间相关词 ⇒ 才要求窗口
    TIME_WORDS = ["落后", "复发", "提前", "延迟", "新鲜", "同步", "超时", "持续", "连续", "每次", "逐次"]
    time_related = any(w in t for w in TIME_WORDS) or bool(re.search(r'\d+\s*(?:h|d|min|小时|天|分钟|秒|周|月)', t))
    f2 = bool(RE_WINDOW.search(t))
    need_f2 = time_related                      # ★ 条件性：只有时间相关量才必须给窗
    f3 = any(w in t for w in SURFACE_WORDS)
    # ★ F4：★ 只有当【F1 缺】而含元语言词时，才判元语言 —— 避免误伤「固定 ≤ 5 个」
    adj = [w for w in META_ADJ if w in t]
    f4_bad = bool(adj) and (not f1)
    ev = {"f1_quant": f1, "f2_window": f2, "time_related": time_related,
          "f3_surface": f3, "f4_meta_adj": adj, "f4_violation": f4_bad}
    miss = []
    if not f1:
        miss.append("F1 无【量】")
    if need_f2 and not f2:
        miss.append("F2 【时间相关量】却无【窗口】")
    if not f3:
        miss.append("F3 无【分母/被量的面】")
    if f4_bad:
        miss.append("F4 【元语言】: %s ⇒ 是形容词/架构性质，不是判据" % "/".join(adj))
    return ("PASS" if not miss else "FAIL"), miss, ev


def load_targets(path):
    """★ 从 v7 W4 草稿抽 14 个指标的目标原文（★ 只读）。"""
    if not os.path.exists(path):
        return None
    s = io.open(path, encoding="utf-8").read()
    secs = re.split(r'^### (2\.\d+ 指标[^\n]*)$', s, flags=re.M)
    out = []
    for i in range(1, len(secs), 2):
        title = secs[i].strip()
        body = secs[i + 1]
        # ★ 目标行通常是 | **目标** | ... | 或 **目标**：...
        m = re.search(r'\*\*目标[^*]*\*\*\s*\|\s*([^|\n]+)', body)
        if not m:
            m = re.search(r'\*\*目标\*\*[：:]\s*([^\n]+)', body)
        tgt = m.group(1).strip() if m else ""
        out.append({"title": title, "target": tgt})
    return out


def selftest():
    ok = tot = 0
    # ★ 正控：合格目标（有量+窗口+分母）⇒ PASS
    tot += 1
    v, m, _ = judge("24h 窗口内 drift 双板到达率 ≤ 100%，分母 = 全部通道")
    if v == "PASS":
        ok += 1; print("  ✅ 正控：含量+窗口+分母 ⇒ PASS")
    else:
        print("  ❌ 正控：合格目标判 FAIL（%s）" % m)
    # ★ 正控：形容词目标 ⇒ FAIL 且命中 F4
    tot += 1
    v, m, ev = judge("端口固定")
    if v == "FAIL" and any("F4" in x for x in m):
        ok += 1; print("  ✅ 正控：`端口固定` ⇒ FAIL 且命中 F4（★ 形容词）")
    else:
        print("  ❌ 正控：`端口固定` 未判 F4（%s）" % m)
    # ★ 正控：「无整份读写」⇒ FAIL（★ 架构性质）
    tot += 1
    v, m, _ = judge("bus 单文件无整份读写")
    if v == "FAIL":
        ok += 1; print("  ✅ 正控：`无整份读写` ⇒ FAIL（★ 架构性质）")
    else:
        print("  ❌ 正控：架构性质未判 FAIL")
    # ★ 负控：★ 带量的「固定」不得被误伤（★ 防 F4 过宽）
    tot += 1
    v, m, _ = judge("端口固定 ≤ 5 个，连续 7d 测试")
    if v == "PASS":
        ok += 1; print("  ✅ 负控：`固定 ≤ 5 个，连续 7d` ⇒ PASS（★ F4 未误伤）")
    else:
        print("  ❌ 负控：F4 误伤带量的目标（%s）" % m)
    # ★★ 负控（★ 2026-10-12 严格度修正）：【非时间相关量】不得要求窗口
    tot += 1
    v, m, _ = judge("会话目录 ≤ 500MB")
    if v == "PASS":
        ok += 1; print("  ✅ 负控：`会话目录 ≤ 500MB` ⇒ PASS（★ 非时间量不要求窗）")
    else:
        print("  ❌ 负控：非时间量被误要窗（%s）" % m)
    # ★★ 正控：【时间相关量】必须要求窗口
    tot += 1
    v, m, _ = judge("信标落后 ≤ 1 次状态变化")
    if v == "FAIL" and any("F2" in x for x in m):
        ok += 1; print("  ✅ 正控：`落后 ≤ 1 次` ⇒ FAIL 且命中 F2（★ 时间量缺窗）")
    else:
        print("  ❌ 正控：时间量缺窗未命中（%s）" % m)
    # ★ 正控：含 24h 窗 的好目标 ⇒ PASS
    tot += 1
    v, m, _ = judge("100% 涉 dsh 设计项有 24h 内留证")
    if v == "PASS":
        ok += 1; print("  ✅ 正控：`100% … 24h 内` ⇒ PASS（★ 量+窗+面）")
    else:
        print("  ❌ 正控：含窗好目标判 FAIL（%s）" % m)
    # ★ 三态：空目标 ⇒ UNDECIDABLE
    tot += 1
    v, m, _ = judge("")
    if v == "UNDECIDABLE":
        ok += 1; print("  ✅ 正控：空目标 ⇒ UNDECIDABLE（★ 不冒充 FAIL/PASS）")
    else:
        print("  ❌ 正控：空目标未判 UNDECIDABLE")
    # ★ 三态：文件不存在 ⇒ load 返回 None
    tot += 1
    if load_targets("/tmp/__no_such_slo__.md") is None:
        ok += 1; print("  ✅ 负控：文件不存在 ⇒ None（★ 调用方报不可判）")
    else:
        print("  ❌ 负控：不存在的文件竟返回内容")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", default="docs/v7-draft-W4-20261012.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("slo-target-form 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    p = a.draft if os.path.isabs(a.draft) else os.path.join(ROOT, a.draft)
    tg = load_targets(p)
    if tg is None:
        print("★ 目标件不可读 ⇒ 【不可判】（★ 不冒充通过）: %s" % p)
        return 2
    if not tg:
        print("★ 未抽到任何指标目标 ⇒ 【不可判】（★ 未抽到 ≠ 不存在）")
        return 2
    res = []
    for it in tg:
        v, miss, ev = judge(it["target"])
        res.append({**it, "verdict": v, "missing": miss, "evidence": ev})
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    print("== slo-target-form 1.0.0 · %s ==" % os.path.relpath(p, ROOT))
    print("  ★ 共 %d 个指标" % len(res))
    from collections import Counter
    c = Counter(r["verdict"] for r in res)
    print("  形态分布：%s" % dict(c))
    print()
    for r in res:
        mark = "✅" if r["verdict"] == "PASS" else "❌"
        print("  %s %s" % (mark, r["title"][:52]))
        if r["target"]:
            print("       目标：%s" % r["target"][:100])
        for m in r["missing"]:
            print("       ★ 缺：%s" % m)
    n_fail = c.get("FAIL", 0)
    print()
    # ★★ 诚实声明（★ 2026-10-12）：本门的 FAIL 【有两种成因，不得混谈】
    f4_hits = [r for r in res if r["verdict"] == "FAIL" and any("F4" in x for x in r["missing"])]
    other = [r for r in res if r["verdict"] == "FAIL" and r not in f4_hits]
    if f4_hits:
        print("  ★★ 真信号（F4 元语言）：%d 条 —★ **目标由形容词/架构性质构成，本身不可判**" % len(f4_hits))
        for r in f4_hits:
            print("      ★ %s" % r["title"][:50])
    if other:
        print("  ★★ 待核项（非 F4）：%d 条 —★★ **【不得直接当作不可判】**：" % len(other))
        print("      ★ 本门的输入是【草稿的目标摘要】，不是锚点原文 ⇒ **摘要不全会产生假阳性**；")
        print("      ★ 结论前必【逐条对锚点§12 原文核】。")
        for r in other[:6]:
            print("      ? %s" % r["title"][:50])
    if n_fail:
        print()
        print("  ❌ %d/%d 个目标未通过形态检查 ⇒ ★ **其中只有 F4 那几条是【本身不可判】**" % (n_fail, len(res)))
        return 1
    print("  ✅ 全部目标均为可判形态")
    return 0


if __name__ == "__main__":
    sys.exit(main())
