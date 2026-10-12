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


def verdict(sources):
    n, classes = count_independent(sources)
    if not sources:
        return {"n": 0, "classes": {}, "verdict": "UNDECIDABLE",
                "reason": "★ 未给出来源 ⇒ 不可判（★ 不得读作 n=1，也不得读作通过）"}
    if n <= 1:
        return {"n": n, "classes": classes, "verdict": "NOT_EVIDENCE",
                "reason": "★ n=%d ⇒ **不得记作证据**（★ 所有来源共享同一假设类：%s）"
                          % (n, "/".join(classes.keys()))}
    return {"n": n, "classes": classes, "verdict": "EVIDENCE",
            "reason": "★ n=%d（假设类：%s）⇒ 可作证据（★ 但仍须注意各来源自身的正确性）"
                      % (n, "/".join(sorted(classes.keys())))}


def cmd_sources(sources, as_json=False):
    r = verdict(sources)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=1)); return 0
    print("== evidence-sources %s ==" % VERSION)
    print("  给定来源: %s" % (", ".join(sources) if sources else "(无)"))
    for c, ss in r["classes"].items():
        print("    假设类 %-14s ← %s" % (c, ", ".join(ss)))
    print("  ★ n（独立假设类数）= %d" % r["n"])
    print("  ⇒ %s" % r["reason"])
    return 0 if r["verdict"] in ("EVIDENCE", "NOT_EVIDENCE", "UNDECIDABLE") else 1


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
    print("== 负控矩阵 ==")
    ok = 0; tot = 0
    def t(name, cond):
        nonlocal ok, tot
        tot += 1; ok += bool(cond)
        print("  %s %s" % ("OK " if cond else "★ 不成立", name))
    t("① 空来源 ⇒ UNDECIDABLE（★ 不得读作 n=1 或通过）", verdict([])["verdict"] == "UNDECIDABLE")
    t("② 单一来源 ⇒ NOT_EVIDENCE", verdict(["own-extraction"])["verdict"] == "NOT_EVIDENCE")
    t("③ 两个【同类】来源 ⇒ 仍 NOT_EVIDENCE（★ 共享假设不算独立）",
      verdict(["own-extraction", "own-production"])["verdict"] == "NOT_EVIDENCE")
    t("④ 两个【不同类】来源 ⇒ EVIDENCE",
      verdict(["own-extraction", "git"])["verdict"] == "EVIDENCE")
    t("⑤ n 数的是【假设类】不是【来源个数】",
      verdict(["regex", "regex-string"])["n"] == 1)
    t("⑥ 三条同类 ⇒ n=1 仍 NOT_EVIDENCE",
      verdict(["own-extraction", "own-production", "own-memory"])["verdict"] == "NOT_EVIDENCE")
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
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(VERSION); return 0
    if a.selfcheck: return selfcheck()
    if a.lean4_check: return lean4_check()
    if a.scan: return cmd_scan(a.scan)
    return cmd_sources(a.sources or [], a.json)


if __name__ == "__main__":
    sys.exit(main())
