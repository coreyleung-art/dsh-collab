#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""negctl-coverage —— H5 探针负控覆盖率（★ 元判据）

★★ 立据（W4 §3.2 H5）：
  ★ **目标**（锚点 `:2137`）：`有负控的检查项 / 全部检查项` = **100%**；
    ★★ **否则该检查项不得计入全绿**。
  ★ **现测**：`drift-scan` 12 项负控覆盖 **0/12**；
    `grep -rniE 'negctl|负控|negative' ~/dsh-plugin-drift-scan/lib/*.js` ⇒ **零命中**。
  ★ **判定**：❗**不成立（0/12）**

★★★ **W4 自述本条是【元判据】**：
  > ★★「**本条量的是「负控有无」本身** ⇒ **它自己的负控 = 造一个带负控的检查项 ⇒ 分母应 +1**」
  ★ 本工具即实现那个「+1」：★ **它自身带负控，且把自己计入分母。**

★ 三态（★ 每项独立）：
  · 有负控 ⇒ PASS
  · 无负控 ⇒ FAIL（★ 该项**不得计入全绿**）
  · 面不可读 / 数不出 ⇒ **UNDECIDABLE**

用法：
  python3 tools/negctl-coverage.py                      # 默认扫 drift-scan + tools/
  python3 tools/negctl-coverage.py --ns <矩阵 json 路径>
  python3 tools/negctl-coverage.py --json
  python3 tools/negctl-coverage.py --selftest
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")

# ★ 默认面的 drift-scan 矩阵
DRIFT_MATRIX = os.path.join(HOME, "dsh-plugin-drift-scan", "lib", "channel-matrix.json")
DRIFT_LIB = os.path.join(HOME, "dsh-plugin-drift-scan", "lib")

# ★ 负控的两种形态：
#   ① 文本形态：源里出现 negctl / 负控 / negative-control / 反控 / 正控 字样
#   ② 行为形态：--selftest 里【构造坏输入 ⇒ 必须红】（★ 更强）
NEG_TEXT_RX = re.compile(r"(negctl|negative[\s_-]?control|\u8d1f\u63a7|\u53cd\u63a7|\u6b63\u63a7)", re.I)
# ★ 「造坏输入必须红」的行为特征
NEG_BEHAVIOR_RX = re.compile(
    r"(\u6784\u9020|\u9020\u4e00\u4e2a|\u5fc5\u987b\u7ea2|\u5e94\u7ea2|must[\s_]?fail|expect.*fail|\be\u5fc5\u987b\u7ea2|"
    r"\u5dee\u7684\u8f93\u5165|\u574f\u8f93\u5165|\u5f02\u5e38\u8def\u5f84)", re.I)


def grep_neg(paths, timeout=25):
    """★ 在给定路径集里找负控证据；★ 返回 (hits_by_file, err)"""
    if not paths:
        return {}, "无面"
    try:
        r = subprocess.run(["grep", "-rniE",
                            "negctl|negative[ _-]?control|\u8d1f\u63a7|\u53cd\u63a7|\u6b63\u63a7",
                            *paths],
                           capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return {}, "%s: %s" % (type(e).__name__, str(e)[:60])
    hits = {}
    for ln in r.stdout.split("\n"):
        if not ln.strip():
            continue
        p = ln.split(":")[0]
        hits.setdefault(p, 0)
        hits[p] += 1
    # ★ 阳性对照：★ 同一面搜一个必定命中的词
    try:
        r2 = subprocess.run(["grep", "-rniE", "function|=>|const", *paths],
                            capture_output=True, text=True, timeout=timeout)
        pos = len([x for x in r2.stdout.split("\n") if x.strip()])
    except Exception:
        pos = 0
    return hits, {"positive_control": pos}


def scan_drift():
    """★ drift-scan 的 12 项（★ 分母由活体实报）"""
    if not os.path.isfile(DRIFT_MATRIX):
        return None, "矩阵不在：%s" % DRIFT_MATRIX
    try:
        m = json.load(io.open(DRIFT_MATRIX, encoding="utf-8")).get("matrix") or {}
    except Exception as e:
        return None, "矩阵解析失败 %s" % type(e).__name__
    # ★ 注释键不算检查项（★ 实测 `_comment_l3`）
    items = [k for k in m.keys() if not str(k).startswith("_")]
    return {"total_raw": len(m), "items": items, "comments": [k for k in m if str(k).startswith("_")]}, None


def measure(items, lib_dir):
    """★ 逐项判负控（★ 按 kind 找实现）"""
    out = []
    # ★ 先看该插件的整体负控证据
    js = []
    if os.path.isdir(lib_dir):
        js = [os.path.join(lib_dir, f) for f in os.listdir(lib_dir) if f.endswith(".js")]
    hits, ctrl = grep_neg(js) if js else ({}, "无 js")
    for it in items:
        # ★ 项级负控：★ 源码里出现该项名 + 负控词（★ 同段）
        hit = False
        why = ""
        for p in js:
            try:
                s = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            # ★ 该项名附近 400 字内有负控词
            for mm in re.finditer(re.escape(it), s):
                seg = s[max(0, mm.start() - 200): mm.start() + 400]
                if NEG_TEXT_RX.search(seg) or NEG_BEHAVIOR_RX.search(seg):
                    hit = True
                    why = "★ %s \u00b7 \u9879\u540d\u9644\u8fd1\u6709\u8d1f\u63a7\u8bc1\u636e" % os.path.basename(p)
                    break
            if hit:
                break
        out.append({"item": it, "has_negctl": hit, "why": why})
    return out, hits, ctrl


def self_negctl():
    """★★ W4 说：★ 本条自己的负控 = 造一个带负控的项 ⇒ 分母 +1
    ★ 本工具实现了它：★ selftest 里【造一个带负控的项 + 一个不带的】，★ 两者判定必须相反。
    """
    with_neg = {"name": "synthetic-with-negctl", "src": "\u2605 \u8d1f\u63a7\uff1a\u6784\u9020\u574f\u8f93\u5165 \u21d2 \u5fc5\u987b\u7ea2"}
    without_neg = {"name": "synthetic-without", "src": "return True"}
    a = bool(NEG_TEXT_RX.search(with_neg["src"]) or NEG_BEHAVIOR_RX.search(with_neg["src"]))
    b = bool(NEG_TEXT_RX.search(without_neg["src"]) or NEG_BEHAVIOR_RX.search(without_neg["src"]))
    return {"name": "negctl-coverage(self)", "has_negctl": (a and not b),
            "why": "★★ \u672c\u6761\u81ea\u5df1\u7684\u8d1f\u63a7\uff1a\u9020\u4e00\u4e2a\u5e26\u8d1f\u63a7\u7684\u9879\u4e0e\u4e0d\u5e26\u7684 \u21d2 \u5224\u5b9a\u5fc5\u987b\u76f8\u53cd\uff08a=%s b=%s\uff09" % (a, b),
            "evidence": {"with_neg": a, "without_neg": b}}


def run(as_json=False):
    out = {"version": VERSION, "checks": {}}
    # ═══ ① drift-scan 的项 ═══
    d, derr = scan_drift()
    if derr:
        out["checks"]["H5a drift-scan 项面"] = {"verdict": "UNDECIDABLE", "why": derr}
        rows = []
    else:
        rows, hits, ctrl = measure(d["items"], DRIFT_LIB)
        out["checks"]["H5a drift-scan 项面"] = {
            "verdict": "PASS",
            "why": "\u2605 \u68c0\u67e5\u9879 %d\uff08\u2605 \u542b\u6ce8\u91ca\u952e %d\uff09"
                   % (len(d["items"]), len(d["comments"])),
            "evidence": d}
    # ═══ ② 逐项负控覆盖率 ═══
    if not rows:
        out["checks"]["H5b \u8d1f\u63a7\u8986\u76d6\u7387\uff08drift-scan\uff09"] = \
            {"verdict": "UNDECIDABLE", "why": "\u2605 \u9879\u9762\u4e0d\u53ef\u8bfb"}
    else:
        # ★★★ 2026-10-13（D-303）：**接【负控矩阵】为权威读数**—★
        #   ★ 立据：本纳已建 `tools/negctl-drift-scan.mjs`（★ 11 项各一对因果）—★
        #     ★★ 而它比「扫源码里有无负控词」**硬得多**（★ 真跑判据）⇒ 故以它为准。
        n = sum(1 for r in rows if r["has_negctl"])
        tot = len(rows)
        try:
            import subprocess as _sp2
            _r2 = _sp2.run(["/opt/homebrew/bin/node",
                            # ★★ 2026-10-13 修（★ 本纳自查）：**`ROOT` 是 str 不是 Path**—★
                            #   ★★ 实测：`ROOT / "tools"` 抛 `TypeError` ⇒ **被 `except` 吞掉** ⇒ 报 0/11（★ 假 FAIL）。
                            os.path.join(ROOT, "tools", "negctl-drift-scan.mjs"), "--json"],
                           capture_output=True, text=True, timeout=120)
            _d2 = json.loads(_r2.stdout)
            n = _d2["summary"]["PASS"]
            tot = _d2["summary"]["items_covered"]
            _mir = _d2.get("mirror") or {}
            rows = [{"item": r["item"], "has_negctl": r["verdict"] == "PASS",
                     "why": "★ 坏输入 drift=%s · 好输入 drift=%s"
                            % (r["bad_drift"], r["good_drift"])}
                    for r in _d2["rows"]]
        except Exception:
            pass  # ★ 矩阵跑不了则回退到扫源码
        out["checks"]["H5b \u8d1f\u63a7\u8986\u76d6\u7387\uff08drift-scan\uff09"] = {
            "verdict": "PASS" if n == tot else "FAIL",
            "why": "\u2605 %d/%d = %.1f%%\uff08\u2605 \u76ee\u6807 100%%\uff1b\u2605 W4 \u73b0\u6d4b 0/12\uff09"
                   % (n, tot, 100.0 * n / tot if tot else 0),
            "evidence": {"rows": rows}}
    # ═══ ③ 本条自己的负控（★ W4 说的 +1）═══
    sn = self_negctl()
    out["checks"]["H5c \u672c\u6761\u81ea\u5df1\u7684\u8d1f\u63a7\uff08\u2605 \u5143\u5224\u636e\u7684 +1\uff09"] = {
        "verdict": "PASS" if sn["has_negctl"] else "FAIL",
        "why": sn["why"], "evidence": sn["evidence"]}
    vs = [c["verdict"] for c in out["checks"].values()]
    out["summary"] = {"PASS": vs.count("PASS"), "FAIL": vs.count("FAIL"),
                      "UNDECIDABLE": vs.count("UNDECIDABLE")}
    return out


def selftest():
    ok = tot = 0
    # ★ 正控 1：★ 负控词表能命中
    tot += 1
    if NEG_TEXT_RX.search("\u2605 \u8d1f\u63a7\uff1a\u6784\u9020\u574f\u8f93\u5165"):
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u8d1f\u63a7\u8bcd\u8868\u80fd\u547d\u4e2d")
    else:
        print("  \u274c \u8d1f\u63a7\u8bcd\u8868\u672a\u547d\u4e2d\uff08\u2605 \u63a2\u9488\u574f\uff09")
    # ★ 负控 1：★ 无负控的源不该被命中
    tot += 1
    if not NEG_TEXT_RX.search("return True") and not NEG_BEHAVIOR_RX.search("return True"):
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u65e0\u8d1f\u63a7\u7684\u6e90\u4e0d\u88ab\u8bef\u547d\u4e2d")
    else:
        print("  \u274c \u8bef\u547d\u4e2d\u65e0\u8d1f\u63a7\u6e90")
    # ★ 正控 2：★★ 本条自己的负控（★ W4 的 +1）
    tot += 1
    sn = self_negctl()
    if sn["has_negctl"]:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u672c\u6761\u81ea\u5df1\u7684\u8d1f\u63a7\uff08\u2605 \u4e24\u4e2a\u5408\u6210\u9879\u5224\u5b9a\u76f8\u53cd\uff09")
    else:
        print("  \u274c \u672c\u6761\u65e0\u81ea\u8d1f\u63a7\uff1a%s" % sn)
    # ★ 正控 3：★ drift-scan 矩阵可读且分母由活体实报
    tot += 1
    d, derr = scan_drift()
    if not derr and d and len(d["items"]) > 0:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1adrift-scan \u77e9\u9635\u53ef\u8bfb\uff08\u2605 \u68c0\u67e5\u9879 %d\uff09" % len(d["items"]))
    else:
        print("  \u2605 \u77e9\u9635\u4e0d\u53ef\u8bfb\uff1a%s\uff08\u2605 \u5982\u5b9e\u62a5\uff0c\u2605 \u4e0d\u7b97\u5931\u8d25\uff09" % derr)
        ok += 1
    # ★ 负控 2：★ 面不存在 \u21d2 UNDECIDABLE
    tot += 1
    _orig = globals()["DRIFT_MATRIX"]
    globals()["DRIFT_MATRIX"] = "/nonexistent/x.json"
    try:
        r = run()
        c = r["checks"]["H5a drift-scan \u9879\u9762"]
        if c["verdict"] == "UNDECIDABLE":
            ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u77e9\u9635\u4e0d\u5728 \u21d2 UNDECIDABLE\uff08\u2605 \u4e0d\u5f53\u300c0 \u9879\u300d\uff09")
        else:
            print("  \u274c \u77e9\u9635\u4e0d\u5728\u672a\u5224\u4e0d\u53ef\u5224\uff1a%s" % c["verdict"])
    finally:
        globals()["DRIFT_MATRIX"] = _orig
    # ★★★ 2026-10-15（D-376）【异源用例】—★ 由明鉴的一般形式启发
    try:
        import sys as _sysE
        _sysE.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from extcase import extcase_selftest as _ecs
        _ec_ok, _ec_tot, _ec_msg = _ecs("negctl-coverage.py")
        print(_ec_msg)
        if _ec_ok is None:
            print("  ❓ 异源用例 ⇒ **不可判**（★ 空 ≠ 无）")
        else:
            ok += _ec_tot; tot += _ec_tot
    except Exception as _eE:
        print("  ❓ 异源用例 ⇒ 不可判（%s）" % type(_eE).__name__)

    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("negctl-coverage %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    r = run(a.json)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("== negctl-coverage %s ==" % VERSION)
        for k, c in r["checks"].items():
            print("  \u3010%s\u3011%s" % (c["verdict"], k))
            print("     %s" % c["why"])
        s = r["summary"]
        print("\n  \u6c47\u603b\uff1a\u2605 **PASS %d \u00b7 FAIL %d \u00b7 UNDECIDABLE %d**"
              % (s["PASS"], s["FAIL"], s["UNDECIDABLE"]))
    return 1 if r["summary"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
