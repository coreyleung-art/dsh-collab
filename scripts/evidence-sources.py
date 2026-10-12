#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence-sources.py — 【判据的独立来源数】自检（S3 的机制化）

为什么存在：
  ★ 2026-10-12 由 session-c05b831c 给出的一层：**自审在结构上【不带信息】** ——
    · 报对方错：判据的唯一来源是自己的提取 ⇒ 提取错了【没有内部矛盾】；
    · 自我升格：判据的唯一来源是自己的产出 ⇒ 产出错了【同样没有内部矛盾】。
  ★★ ⇒ 二者【同构】；制止自升格的不是【谦虚】，是【独立性要求】在【自指情形】下的同一形态。
  ★★★ 故 S3「不可自审」从【纪律】升为【机制】：
     不问「有没有违反」，而问「**这份自证里，判据有几个独立来源？**」——
     ★ **n=1 ⇒ 不得记作证据**（可数、可验、可写进工具）。

用法:
  python3 scripts/evidence-sources.py --sources A B C        # 判一组来源是否构成证据
  python3 scripts/evidence-sources.py --scan docs/xxx.md     # 扫一份报告里的来源声明
  python3 scripts/evidence-sources.py --selfcheck
  python3 scripts/evidence-sources.py --lean4-check
"""
import sys, os, re, json, argparse

VERSION = "1.0.0"

# ★ 独立性判定：两来源是否【共享假设】—— 共享则不算独立（D-135/D-142）
#   ★ 这里的「假设」以【来源类型】粗分；同型即视为可能共享假设。
ASSUMPTION_CLASS = {
    "own-extraction":  "self",        # ★ 自己提取
    "own-production":  "self",        # ★ 自己产出
    "own-memory":      "self",        # ★ 自己的记忆
    "own-report":      "self",        # ★ 自己写的报告
    "regex":           "regex-string",# ★ 正则扫字符串
    "regex-string":    "regex-string",
    "git":             "git-object",  # ★ git 对象（提交/树/引用）
    "filesystem":      "fs",          # ★ 文件系统
    "external-source": "external",    # ★ 外部源（官方文档/外部机器/第三方）
    "other-party":     "external",    # ★ 另一方
    "board-readback":  "board",       # ★ 黑板回读（★ 服务端所记）
}


def classify(name):
    n = (name or "").strip().lower()
    if n in ASSUMPTION_CLASS:
        return ASSUMPTION_CLASS[n]
    for k, v in ASSUMPTION_CLASS.items():
        if k in n:
            return v
    return "unknown:" + n


def count_independent(sources):
    """★ 返回 (n, 明细)。n = 【假设类】的种数（不是来源个数）"""
    classes = {}
    for s in sources:
        classes.setdefault(classify(s), []).append(s)
    return len(classes), classes


def verdict(sources, method=None):
    """★★ 新增（2026-10-12，★ 由 session-c05b831c 建议）：【同法两次 ⇒ n 不增】
    ★ 理由：★ 同法两次，**来源数仍是 1** —★ 与「判据的独立来源数 n」**同一把尺**。
    ★ 两次结果一致时，若**方法标识相同** ⇒ 该结果不计入证据数。
    """
    if method and method.get("same_method_twice"):
        n, classes = count_independent(sources)
        return {"n": n, "classes": classes, "verdict": "NOT_EVIDENCE",
                "same_method_twice": True,
                "reason": "★★ **同法两次 ⇒ n 不增**（★ 方法标识相同：%s）"
                          "⇒ 不得记作证据" % method.get("id", "?")}

    n, classes = count_independent(sources)
    if not sources:
        # ★★★ 修（2026-10-12，★ 由 session-c05b831c 指出）：
        #   ★ 空来源是【未声明（UNSTATED）】，★★ **不是【不可判（UNDECIDABLE）】**。
        #   ★ 区别：未声明 = 调用者【没给】来源（★ 他没做事）；
        #          不可判 = 给了来源但【无法判定】（★ 判据不够）。
        return {"n": 0, "classes": {}, "verdict": "UNSTATED",
                "reason": "★ 未给出来源清单 ⇒ **未声明**（★ 不得读作 n=1，也不得读作通过）"}
    # ★★ ★ 真正的【不可判】：有来源，但类型均无法归类 ⇒ 判据不够，★ 不是「他没声明」也不是「他提交不足」
    if sources and all(c.startswith("unknown:") for c in classes):
        return {"n": n, "classes": classes, "verdict": "UNDECIDABLE",
                "reason": "★ 有来源但类型均无法归类 ⇒ **不可判**（★ 需先定义这些类型）"}
    if n <= 1:
        return {"n": n, "classes": classes, "verdict": "NOT_EVIDENCE",
                "reason": "★ n=%d ⇒ **不得记作证据**（★ 所有来源共享同一假设类：%s）"
                          % (n, "/".join(classes.keys()))}
    return {"n": n, "classes": classes, "verdict": "EVIDENCE",
            "reason": "★ n=%d（假设类：%s）⇒ 可作证据（★ 但仍须注意各来源自身的正确性）"
                      % (n, "/".join(sorted(classes.keys())))}


def cmd_sources(sources, as_json=False, method=None):
    r = verdict(sources, method)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1)); return 0
    print("== evidence-sources %s ==" % VERSION)
    print("  给定来源: %s" % (", ".join(sources) if sources else "(无)"))
    for c, ss in r["classes"].items():
        print("    假设类 %-14s ← %s" % (c, ", ".join(ss)))
    print("  ★ n（独立假设类数）= %d" % r["n"])
    print("  ⇒ %s" % r["reason"])
    return 0 if r["verdict"] in ("EVIDENCE", "NOT_EVIDENCE", "UNDECIDABLE") else 1


def check_errors(claims):
    """★★ 判据乙（管「自罚/多报」，★ 由 session-c05b831c 提出，2026-10-12）
    ★ 要求：★★ **每条所报的错各配一个【能证伪它的读数】**；
      ★ **且【错数】= 【互不相同的证伪读数】个数**（★ 同一读数不能同时顶两条错）。
    ★ 为什么需要它：★ 判据甲（引文可核到原文）**只量引文存在性**，
      ★★ **对「两错叠」这种多报【不能红】** —★ 故需乙。
    claims: list of {"claim": ★ 错的描述, "falsifier": ★ 能证伪它的读数 (or None)}
    """
    if not claims:
        return {"verdict": "UNSTATED", "n_claims": 0, "n_falsifiers": 0,
                "reason": "★ 未给出任何声称 ⇒ 未声明"}
    with_f = [c for c in claims if (c.get("falsifier") or "").strip()]
    fs = {(c.get("falsifier") or "").strip() for c in with_f}
    n_c, n_f = len(claims), len(fs)
    if len(with_f) < n_c:
        return {"verdict": "OVERREPORTED", "n_claims": n_c, "n_falsifiers": n_f,
                "missing": [c.get("claim") for c in claims if not (c.get("falsifier") or "").strip()],
                "reason": "★★ 有 %d 条声称【找不到证伪读数】⇒ "
                          "★ **错数（%d）> 证伪读数数（%d）** ⇒ ★★ **多报**"
                          % (n_c - len(with_f), n_c, n_f)}
    if n_f < n_c:
        return {"verdict": "OVERREPORTED", "n_claims": n_c, "n_falsifiers": n_f,
                "reason": "★★ 证伪读数有重复（★ 互不相同者 %d < 错数 %d）"
                          "⇒ ★ **同一读数不能顶两条错** ⇒ 多报" % (n_f, n_c)}
    return {"verdict": "CONSISTENT", "n_claims": n_c, "n_falsifiers": n_f,
            "reason": "★ 错数 = 互不相同的证伪读数个数 = %d ⇒ 不构成多报" % n_c}


def cmd_errors(path, as_json=False):
    import json as _j
    try:
        claims = _j.load(open(path, encoding="utf-8"))
    except Exception as e:
        print("  ★ 读不到 %s：%s ⇒ 不可判" % (path, e)); return 0
    r = check_errors(claims)
    if as_json:
        print(_j.dumps(r, ensure_ascii=False, indent=1)); return 0
    print("== 判据乙：错数 vs 证伪读数 ==")
    for i, c in enumerate(claims, 1):
        f = (c.get("falsifier") or "").strip()
        print("  %d. %s…" % (i, (c.get("claim") or "")[:44]))
        print("     证伪读数: %s" % (f if f else "★★ **找不到**"))
    print("  ⇒ %s" % r["reason"])
    return 0


def cmd_scan(path):
    """★ 扫报告里的「来源/证据」声明行，粗估 n"""
    if not os.path.exists(path):
        print("  ★ 文件不存在: %s ⇒ 不可判" % path); return 0
    s = open(path, encoding="utf-8", errors="replace").read()
    found = re.findall(r"(?:来源|证据|source|evidence)[^\n:：]{0,6}[:：]\s*([^\n]{1,200})", s, re.I)
    print("== 扫 %s ==" % path)
    print("  命中「来源/证据」声明行: %d" % len(found))
    if not found:
        print("  ★★ 未命中 ⇒ 【不可判】（★ 不是「n=1」，★ 也不是「无来源」）"); return 0
    for i, f in enumerate(found[:12], 1):
        toks = [t.strip() for t in re.split(r"[，,、/|；;]", f) if t.strip()]
        n, classes = count_independent(toks)
        print("   %2d. n=%d  %s" % (i, n, f[:80]))
    return 0


def selfcheck():
    src = open(__file__, encoding="utf-8").read()
    print("== 负控矩阵 ==")
    ok = 0; tot = 0
    def t(name, cond):
        nonlocal ok, tot
        tot += 1; ok += bool(cond)
        print("  %s %s" % ("OK " if cond else "★ 不成立", name))
    t("① 空来源 ⇒ **UNSTATED（未声明）**（★ 不得读作 n=1 或通过）", verdict([])["verdict"] == "UNSTATED")
    t("①b **UNSTATED ≠ UNDECIDABLE**（★ 两个不同的三态位）", verdict([])["verdict"] != "UNDECIDABLE")
    t("①c 来源类型无法归类 ⇒ 真正的 UNDECIDABLE", verdict(["zzz-unknown-1","yyy-unknown-2"])["verdict"] == "UNDECIDABLE")
    t("② 单一来源 ⇒ NOT_EVIDENCE", verdict(["own-extraction"])["verdict"] == "NOT_EVIDENCE")
    t("③ 两个【同类】来源 ⇒ 仍 NOT_EVIDENCE（★ 共享假设不算独立）",
      verdict(["own-extraction", "own-production"])["verdict"] == "NOT_EVIDENCE")
    t("④ 两个【不同类】来源 ⇒ EVIDENCE",
      verdict(["own-extraction", "git"])["verdict"] == "EVIDENCE")
    t("⑤ n 数的是【假设类】不是【来源个数】",
      verdict(["regex", "regex-string"])["n"] == 1)
    t("⑥ 三条同类 ⇒ n=1 仍 NOT_EVIDENCE",
      verdict(["own-extraction", "own-production", "own-memory"])["verdict"] == "NOT_EVIDENCE")
    # ★★★ ⑥ 「能被否决」的负控（★ 由 session-c05b831c 建议）：
    #   ★ 饲【真有多源】者 ⇒ 须通过；
    #   ★★ 饲【单源而「自报多源」】者 ⇒ **须红** —― ★ **后者才是它的守门能力所在**。
    #   ★ 实现依据：本工具**不收 `n` 字段**，只收【来源清单】并**自己数**。
    t("⑥a 【真多源】须通过（★ 吞入正向）",
      verdict(["own-extraction", "git"])["verdict"] == "EVIDENCE")
    t("⑥b 【单源】不得因「声称多源」而通过（★ 吞入反向・守门）",
      verdict(["own-extraction"])["verdict"] == "NOT_EVIDENCE")
    # ★★★ ★ 到此一步重踏了今晚同一个坑：刚才判据命中的是【docstring 里的 `n=` 文案】，★ **不是代码**。
    #   ★ 修法：先剥 docstring 与注释，再判。★ 同族：「注释不控事」。
    import re as _re
    _q3 = chr(39) * 3
    _code = src.split(_q3)
    _code = "".join(p for i, p in enumerate(_code) if i % 2 == 0)  # ★ 丢掉三引号块内容
    _code = _re.sub(r"(?m)^\s*#.*$", "", _code)                     # ★ 丢掉注释
    # ★★★ 致命一步：判据的面必须【排除判据自身】。
    #   ★ 本函数体内含 "--n" / "add_argument('n'" 等字面串
    #   ★ 不剔除 ⇒ 自指污染 ⇒ 6c 误判（★ 2026-10-12 实测，★ 修了四次）
    _i = _code.find("def selfcheck")
    if _i > 0:
        _code = _code[:_i]
    # ★★★ 新增（★ 由 session-c05b831c 建议）：同法两次 ⇒ n 不增
    t("⑥d 同法两次 ⇒ NOT_EVIDENCE（★ n 不增）",
      verdict(["own-extraction"])["verdict"] == "NOT_EVIDENCE" and
      verdict(["own-extraction"], {"same_method_twice": True, "id": "grep-A"})["verdict"] == "NOT_EVIDENCE")
    # ★ 到此又踩一次：刚才判据查 reason 里有无 `same_method_twice`，
    #   ★ 而实际 reason 写的是中文文案「方法标识相同」。★ 修法：判它含【方法标识】字样且含具体 id。
    _r = verdict(["a"], {"same_method_twice": True, "id": "grep-A"}).get("reason", "")
    t("⑥e 同法两次时仍报【方法标识】（★ 含具体 id）",
      ("方法标识" in _r) and ("grep-A" in _r))
    # ★★★ 新增：判据乙（★ 管自罚/多报）—★ ★ 用对方那次「两错叠」作反例
    t("⑥f 两错叠而第二条无证伪读数 ⇒ OVERREPORTED（★ 多报）",
      check_errors([{"claim": "编号串行", "falsifier": "D-027 实为端口归因"},
                    {"claim": "引文不在", "falsifier": None}])["verdict"] == "OVERREPORTED")
    t("⑥g 每条错各有一个【互不相同】证伪读数 ⇒ CONSISTENT",
      check_errors([{"claim": "编号串行", "falsifier": "R-1"},
                    {"claim": "措辞不当", "falsifier": "R-2"}])["verdict"] == "CONSISTENT")
    t("⑥h 同一读数顶两条错 ⇒ OVERREPORTED（★ 重复不算）",
      check_errors([{"claim": "A", "falsifier": "R-1"},
                    {"claim": "B", "falsifier": "R-1"}])["verdict"] == "OVERREPORTED")
    t("⑥i 无声称 ⇒ UNSTATED（★ 不得读作合格）",
      check_errors([])["verdict"] == "UNSTATED")
    t("⑥c 本工具的【参数面】不接收 n（★ 防「读自报」）",
      ("--n" not in _code) and ("add_argument('n'" not in _code) and ("add_argument(\"n\"" not in _code))
    print("\n== 负控 %d/%d ==" % (ok, tot))
    return 0 if ok == tot else 1


def lean4_check():
    import re as _re
    src = open(__file__, encoding="utf-8").read()
    print("== --lean4-check（A–F）==")
    code = _re.sub(r'"""(?:.|\n)*?"""', "", src)
    code = _re.sub(r"(?m)^\s*#.*$", "", code)
    i = code.find("def lean4_check")
    if i > 0: code = code[:i]
    res = []
    def chk(n, c, w): res.append((n, bool(c), w))
    chk("A 无删除原语", not _re.search(r"\b(rmtree|os\.remove|os\.unlink)\b", code), "只读判据")
    chk("B 无写盘", not _re.search(r"\bopen\([^)]*['\"][wa]", code), "不落盘")
    chk("C 无危险原语", not _re.search(r"\b(eval|exec|__import__)\s*\(", code), "无动态执行")
    chk("D 空来源有护栏", "UNDECIDABLE" in code and "verdict([])" in code, "三态")
    chk("E 假设表单一来源", code.count("ASSUMPTION_CLASS =") == 1, "无重复")
    chk("F 版本单一来源", code.count("VERSION =") == 1, "无重复")
    ok = sum(1 for _, c, _ in res if c)
    for n, c, w in res: print("  %s %-20s（%s）" % ("OK " if c else "★ 不成立", n, w))
    print("\n== lean4 %d/%d ==" % (ok, len(res)))
    return 0 if ok == len(res) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="*")
    ap.add_argument("--scan")
    ap.add_argument("--errors", help="★ 判据乙：JSON 文件（[{\"claim\",\"falsifier\"}]）")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--same-method-twice", dest="smt", action="store_true",
                    help="★ 两次结果一致且【方法标识相同】 ⇒ n 不增")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(VERSION); return 0
    if a.selfcheck: return selfcheck()
    if a.lean4_check: return lean4_check()
    if a.errors: return cmd_errors(a.errors, a.json)
    if a.scan: return cmd_scan(a.scan)
    m = {"same_method_twice": True, "id": "★ --same-method-twice"} if getattr(a, "smt", False) else None
    return cmd_sources(a.sources or [], a.json, m)


if __name__ == "__main__":
    sys.exit(main())
