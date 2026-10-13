#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""leadership-claims —— L-1 / L-2 的可红判据（★ 维度四「保持领先」）

★★ 立据（W4 §3.4）：
  ★ **L-1**：只在**同时满足三条**时才记领先 ——
    ① 本机有实现 ② 已给出**业界等价物**并说明差在哪 ③ 有**阴性证据**（写清搜过的词与面）
    ★★ 而 W4 自陈：**「L-1 是元判据，不是可红判据」** ⇒ ★ **本工具即把它变成可红的**：
      ★ **扫全仓的「领先」主张，逐条查三条是否同时满足 ⇒ 不满足即报红。**
  ★ **L-2**：每个「领先」主张须挂**可被第三方复跑的对照实验**
    ★★ 现测：**未建**；★ 锚点自陈 ⇒ ★ **当前不可判，不得记领先**。

★ 判据（★ 三条合取，缺一即「不得记领先」）：
  C1 有实现   —— 主张附近出现【本仓路径/文件名】
  C2 有业界等价物 —— 主张附近出现【业界名/标准号/URL】**且**有「差在哪」的表述
  C3 有阴性证据 —— 主张附近写清【搜过的词与面】+ 有阳性对照

★ 三态：★ 主张本身不在 ⇒ 不可判（★ 不报 0）；★ 有主张但不满足三条 ⇒ **FAIL**（★ 不得记领先）。

用法：
  python3 tools/leadership-claims.py                # 扫 docs/ + 锚点
  python3 tools/leadership-claims.py --json
  python3 tools/leadership-claims.py --selftest
"""
import argparse
import io
import json
import os
import re
import sys

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★★ 2026-10-13 修（★ 本纳自查）：【收窄到「本机/本线 vs 业界」】—★
#   ★ 原筛字只要行里有「领先」就抓 ⇒ **假红 62 条**—★
#   ★★ 而抽样看，它们是：技术描述（「文档站版本领先于发布」）· 实验数据（「TF-IDF 领先 1.75 倍」）·
#     变量语义（「local 领先」）· 别人的基准（「GLiDE 领先 Jev」）· ★★ **用户目标原话**。
#   ★ 故收窄为：**主语必是【我们/本机/本线/本仓/本方案】且 对象是【业界/竞品/标准/同类】**。
#   ★ 且排除用户原话引用（★ 那是目标，★ 不是主张）。
SELF_RX = re.compile(r"(我们|本机|本线|本仓|本方案|CAHAC|星桥|花网|本项目)")
PEER_RX = re.compile(r"(业界|竞品|标准|同类|对标|行业|industry|FIPA|A2A|MCP)")
QUOTE_RX = re.compile(r"(让整个 cld|也保持领先」|「[^」]{0,20}领先[^」]{0,20}」)")

# ★ 三条的证据词
C1_RX = re.compile(r"(`[^`]*\.(py|js|mjs|sh|md)`|~/[\w./-]+|/Users/[\w./-]+|本机有|已实现|已建)")
C2_RX = re.compile(r"(FIPA|A2A|MCP|CAHAC|CWEP|RFC\s?\d+|ISO|W3C|OASIS|arXiv|doi:|https?://)")
C2B_RX = re.compile(r"(差在|差异|相比|较之|落后|不如|对齐度|差距)")
C3_RX = re.compile(r"(阴性证据|搜过的|检索词|扫过的面|阳性对照|未发现|未搜到)")
C3B_RX = re.compile(r"(阳性对照|必定命中|grep)")

# ★ 明确的【否定断言】—— ★ 它们不是「主张领先」，★ 是「不主张领先」⇒ 应排除
NEG_RX = re.compile(r"(不主张|不得记|未发现|无可靠|不成立|落\s*后|对齐\s*4|保守结论|不可判)")


def scan_claims(paths, window=6, limit=400):
    rows = []
    for p in paths:
        if not os.path.isfile(p):
            continue
        try:
            lines = io.open(p, encoding="utf-8", errors="ignore").read().split("\n")
        except Exception:
            continue
        for i, ln in enumerate(lines):
            if "领先" not in ln and "leading" not in ln.lower():
                continue
            # ★★ 收窄 1：★ 用户目标原话引用 ⇒ 不是主张
            if QUOTE_RX.search(ln):
                continue
            # ★★ 收窄 2：★ 主语必是【本方】且 对象是【业界】
            if not (SELF_RX.search(ln) and PEER_RX.search(ln)):
                continue
            ctx = "\n".join(lines[max(0, i - window): i + window + 1])
            negated = bool(NEG_RX.search(ctx))
            rows.append({"file": os.path.relpath(p, ROOT), "line": i + 1,
                         "text": ln.strip()[:110], "negated": negated})
            if len(rows) >= limit:
                return rows
    return rows


def judge(row, all_lines=None):
    """★ 三条合取判一条主张"""
    t = row["text"]
    # ★ 否定断言 ⇒ 不是「主张领先」⇒ 不判（★ 也不报红）
    if row["negated"]:
        return {"verdict": "NOT_A_CLAIM", "why": "★ 该行是【否定/保守】断言（★ 它不主张领先）"}
    c1 = bool(C1_RX.search(t))
    c2 = bool(C2_RX.search(t)) and bool(C2B_RX.search(t))
    c3 = bool(C3_RX.search(t)) and bool(C3B_RX.search(t))
    miss = [n for n, v in (("C1有实现", c1), ("C2业界等价物+差在哪", c2), ("C3阴性证据+阳性对照", c3)) if not v]
    if not miss:
        return {"verdict": "PASS", "why": "★ 三条齐", "checks": {"C1": c1, "C2": c2, "C3": c3}}
    return {"verdict": "FAIL", "why": "★ 缺 " + " · ".join(miss) + " ⇒ **不得记领先**",
            "checks": {"C1": c1, "C2": c2, "C3": c3}}


def run(paths=None, as_json=False):
    if paths is None:
        paths = []
        dd = os.path.join(ROOT, "docs")
        if os.path.isdir(dd):
            paths += [os.path.join(dd, f) for f in sorted(os.listdir(dd))
                      if f.endswith(".md")]
    rows = scan_claims(paths)
    judged = []
    for r in rows:
        j = judge(r)
        r2 = dict(r); r2.update(j)
        judged.append(r2)
    claims = [r for r in judged if r["verdict"] != "NOT_A_CLAIM"]
    fails = [r for r in claims if r["verdict"] == "FAIL"]
    pass_ = [r for r in claims if r["verdict"] == "PASS"]
    # ★★ L-2：★ 每个「领先」主张须挂【可复跑对照实验】
    l2 = [r for r in claims if "复跑" not in r["text"] and "对照实验" not in r["text"]]
    out = {"version": VERSION, "scanned_files": len([p for p in paths if os.path.isfile(p)]),
           "claims_found": len(claims), "negated_excluded": len(judged) - len(claims),
           "L1": {"PASS": len(pass_), "FAIL": len(fails),
                  "verdict": ("UNDECIDABLE" if not claims else ("PASS" if not fails else "FAIL"))},
           "L2": {"claims_without_experiment": len(l2), "total": len(claims),
                  "verdict": ("UNDECIDABLE" if not claims else ("PASS" if not l2 else "FAIL"))},
           "detail": {"fails": [{"file": r["file"], "line": r["line"], "text": r["text"], "why": r["why"]}
                               for r in fails[:20]],
                      "pass": [{"file": r["file"], "line": r["line"]} for r in pass_[:10]]}}
    return out


def selftest():
    ok = tot = 0
    # ★ 正控 1：三条齐 ⇒ PASS
    tot += 1
    r1 = judge({"text": "本机有实现 scripts/x.py · 业界等价物 FIPA 标准 · 差在 X · 阴性证据：搜过的词 A/B · 阳性对照 grep 命中",
                "negated": False})
    if r1["verdict"] == "PASS":
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u4e09\u6761\u9f50 \u21d2 PASS")
    else:
        print("  \u274c \u6b63\u63a7\u5931\u8d25\uff1a%s" % r1["why"])
    # ★ 负控 1：缺 C3 ⇒ FAIL
    tot += 1
    r2 = judge({"text": "本机有实现 scripts/x.py · 业界等价物 FIPA · 差在 X",
                "negated": False})
    if r2["verdict"] == "FAIL" and "C3" in r2["why"]:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u7f3a C3 \u21d2 FAIL\uff08\u2605 \u4e0d\u5f97\u8bb0\u9886\u5148\uff09")
    else:
        print("  \u274c \u8d1f\u63a7\u5931\u8d25\uff1a%s" % r2["why"])
    # ★ 负控 2：否定断言 ⇒ 不判（★ 不报红）
    tot += 1
    r3 = judge({"text": "\u672c\u8f6e\u672a\u53d1\u73b0\u53ef\u9760\u7684\u9886\u5148\u9879", "negated": True})
    if r3["verdict"] == "NOT_A_CLAIM":
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u5426\u5b9a\u65ad\u8a00 \u21d2 NOT_A_CLAIM\uff08\u2605 \u5b83\u4e0d\u4e3b\u5f20\u9886\u5148\uff09")
    else:
        print("  \u274c \u8d1f\u63a7\u5931\u8d25\uff1a%s" % r3["verdict"])
    # ★ 正控 2：空主张面 ⇒ UNDECIDABLE（★ 不报 0\uff0c\u4e0d\u62a5 PASS）
    tot += 1
    o = run(paths=[], as_json=True)
    if o["L1"]["verdict"] == "UNDECIDABLE":
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u65e0\u4e3b\u5f20 \u21d2 UNDECIDABLE\uff08\u2605 \u4e0d\u8bfb\u4f5c\u300c\u65e0\u95ee\u9898\u300d\uff09")
    else:
        print("  \u274c \u7a7a\u9762\u5224\u9519\uff1a%s" % o["L1"]["verdict"])
    # ★ 正控 3：真扫面能命中（★ 阳性对照）
    tot += 1
    o2 = run(as_json=True)
    if o2["scanned_files"] > 0 and (o2["claims_found"] + o2["negated_excluded"]) > 0:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u771f\u626b\u9762\u547d\u4e2d\uff08\u2605 %d \u6587\u4ef6 \u00b7 \u4e3b\u5f20 %d \u00b7 \u5426\u5b9a %d\uff09"
                       % (o2["scanned_files"], o2["claims_found"], o2["negated_excluded"]))
    else:
        print("  \u274c \u626b\u9762\u672a\u547d\u4e2d\uff08\u2605 \u7591\u63a2\u9488\u574f\uff09")
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("leadership-claims %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    r = run(as_json=a.json)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("== leadership-claims %s\uff08\u2605 \u626b %d \u6587\u4ef6\uff09==" % (VERSION, r["scanned_files"]))
        print("  \u4e3b\u5f20 %d \u6761\uff08\u2605 \u5df2\u6392\u9664\u5426\u5b9a\u65ad\u8a00 %d \u6761\uff09"
              % (r["claims_found"], r["negated_excluded"]))
        print("  \u3010L-1 \u4e09\u6761\u5408\u53d6\u3011%s \u2014 PASS %d \u00b7 FAIL %d"
              % (r["L1"]["verdict"], r["L1"]["PASS"], r["L1"]["FAIL"]))
        print("  \u3010L-2 \u5bf9\u7167\u5b9e\u9a8c\u3011%s \u2014 \u65e0\u5bf9\u7167\u5b9e\u9a8c\u7684\u4e3b\u5f20 %d/%d"
              % (r["L2"]["verdict"], r["L2"]["claims_without_experiment"], r["L2"]["total"]))
        for f in r["detail"]["fails"][:6]:
            print("     \u2605 %s:%d \u2014 %s" % (f["file"], f["line"], f["why"]))
    return 1 if (r["L1"]["verdict"] == "FAIL" or r["L2"]["verdict"] == "FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
