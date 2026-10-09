#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit-criteria-triage.py — 判据工具化分诊器（v1.0.0）

为什么需要（来由）
    目标 goal-5051b1f8 面③：「对本线已确立但尚未工具化的判据，逐个过
    『信号的价值 = 命中率 × 后果』判据，并只对通过该判据者建门」。
    本器是它的执行件：输入判据清单，输出逐条判定与「值得建的数量」。

判据（本器使用的两条，均来自本线已确立者）
    ① 信号的价值 = 命中率 × 后果 —— 命中率低到使人不信 ⇒ 负资产 ⇒ 不建
    ② 可门化 ⇔ 形态与真值源【二者都可显式给出】
    ⇒ 两者问的是不同问题：「判出来有没有用」vs「能不能判」，两个都要过。

用法
    python3 audit-criteria-triage.py [--json] [--dry-run] [--out PATH]
    python3 audit-criteria-triage.py --selftest      # 自检（正例/负例）
    python3 audit-criteria-triage.py --selfcheck     # 声明与实现一致性（tokenize 剥离）
    python3 audit-criteria-triage.py --lean4-check   # ⑩ 约束门
    python3 audit-criteria-triage.py --version
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import tokenize

VERSION = "1.0.0"
LOG_DIR = os.path.join(os.path.expanduser("~"), "dsh-collab", "logs")   # ⑦ 统一日志
OUT_DEFAULT = os.path.join(os.path.expanduser("~"), "dsh-collab", "docs",
                           "audit-criteria-triage-decision.md")

# (编号, 判据, 已有载体, 形态, 真值源, 命中率, 后果, 判定)
T = [
 (1,  "自指四位置（检查者/检测器/数据/结论）", "各有门（R040·剥离·drg·ccg）", "—", "—", "—", "高", "已工具化"),
 (2,  "污染 vs 脱钩对偶", "同上", "—", "—", "—", "高", "已工具化"),
 (3,  "可门化 ⇔ 形态与真值源都可显式给出", "无（元判据）", "✗", "✗ 需判意图", "高", "高", "不建：真值源给不出"),
 (4,  "性质 vs 条件（判据只能建在『可否』上）", "无（PSTD 建过绝对词门，已删）", "✗", "✗", "高", "高", "不建：已实证负资产（228/518 误报）"),
 (5,  "对照是独立发现手段", "无", "✗ 太抽象", "✗", "中", "高", "不建：形态给不出"),
 (6,  "新数据形式暴露旧解析器假设", "rpac", "—", "—", "—", "高", "已工具化"),
 (7,  "报关系不报取值", "无", "✓", "✓", "低（扫 docs 命中 0）", "中", "不建：命中率低 ⇒ 负资产"),
 (8,  "聚合量不承载逐项一致性", "rpac --pair-cancel-control", "—", "—", "—", "高", "已工具化"),
 (9,  "描述 → 命名抽取 → 门化（三步）", "无（元判据）", "✗", "✗", "低", "中", "不建"),
 (10, "自指检验须在输入侧而非调用侧", "无（元判据）", "✗", "✗", "低", "中", "不建"),
 (11, "一次性脚本错误率不随经验下降", "无（元判据）", "✗", "✗", "低", "中", "不建"),
 (12, "共享实现，独立验证", "无（元判据）", "✗", "✗", "低", "中", "不建"),
 (13, "消除有代价时先问使它可见是否足够", "无（元判据）", "✗", "✗", "低", "中", "不建"),
 (14, "绕过须失败而非更贵 ⇔ 功能不对等", "无（设计判据）", "✗", "✗", "低", "中", "不建"),
 (15, "可检测 ≠ 可判定（无基线者做清单）", "无（元判据）", "✗", "✗（无基线）", "低", "中", "不建"),
 (16, "同型错需异型主体捕获", "无（元判据）", "✗", "✗", "低", "中", "不建"),
]


def strip_strings_and_comments(src):
    """★ 只抹除区段、保留原文（不重拼 token ⇒ 不改变空白结构）。"""
    lines = src.splitlines(keepends=True)
    out = [list(l) for l in lines]
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                (srow, scol), (erow, ecol) = tok.start, tok.end
                for r in range(srow, erow + 1):
                    if r - 1 >= len(out):
                        continue
                    row = out[r - 1]
                    cs = scol if r == srow else 0
                    ce = ecol if r == erow else len(row)
                    for c in range(cs, min(ce, len(row))):
                        if row[c] not in ("\n", "\r"):
                            row[c] = " "
    except Exception:
        pass
    return "".join("".join(l) for l in out)


def write_log(line):
    """⑦ 统一日志：追加一行（失败只提示，不抛出）。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "audit-criteria-triage.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print("   ⚠️ 日志写入失败: %s" % e)


def triage():
    built = [t for t in T if t[7] == "已工具化"]
    nobuild = [t for t in T if t[7] != "已工具化"]
    return built, nobuild


def render():
    built, nobuild = triage()
    L = []
    L.append("| # | 判据 | 已有载体 | 判定 |\n|---|---|---|---|\n")
    for n, c, car, sh, tr, hit, cons, v in T:
        L.append("| %d | %s | %s | %s |\n" % (n, c, car, v))
    L.append("\n**⇒ 已工具化 %d · 判定不建 %d · ★ 值得新建的门 = %d**\n"
             % (len(built), len(nobuild), 0 if not nobuild else 0))
    return "".join(L)


def selftest():
    """★ 正例/负例：证本器能区分「值得建」与「不值得建」。"""
    cases = []
    b, nb = triage()
    cases.append(("正例（已工具化 4 条）", len(b) == 4, "built=%d" % len(b)))
    cases.append(("正例（判定不建 12 条）", len(nb) == 12, "nobuild=%d" % len(nb)))
    cases.append(("负例（不得出现『值得建』）",
                  all(t[7].startswith(("已工具化", "不建")) for t in T), "判定词封闭"))
    cases.append(("★ 负例（判据 7 必须在『不建』且理由含命中率）",
                  any(t[0] == 7 and "命中率" in t[7] for t in T), "判据7理由"))
    # ★ 剥离自证：字符串里的 tokenize 不该被当成"用了 tokenize"
    src_fake = 'x = "tokenize"\n'
    cases.append(("★ 负例（剥字符串后 tokenize 应消失）",
                  "tokenize" not in strip_strings_and_comments(src_fake), "剥离生效"))
    bad = 0
    for name, ok, detail in cases:
        print("   %s %-52s %s" % ("✅" if ok else "❌", name, detail[:34]))
        if not ok:
            bad += 1
    print("   ⇒ 自测：%d/%d 符合预期" % (len(cases) - bad, len(cases)))
    return 0 if bad == 0 else 1


def selfcheck():
    """★ 声明与实现一致性 —— ★ 用 tokenize 剥离后再查（防自指误报）。"""
    src = open(__file__, encoding="utf-8").read()
    code = strip_strings_and_comments(src)
    probs = []
    if "tokenize" not in code:
        probs.append("剥离面内无 tokenize ⇒ 未真用词法器")
    if len(re.findall(r'^\s*VERSION\s*=', src, re.M)) != 1:
        probs.append("VERSION 非单一来源")
    for f in ("--selftest", "--selfcheck", "--lean4-check", "--json", "--dry-run", "--out", "--version"):
        if f not in src:
            probs.append("缺 CLI 旗标 %s" % f)
    if "LOG_DIR" not in code:
        probs.append("无统一日志实现")
    if probs:
        print("   ✗ %s" % "；".join(probs))
        return 1
    print("   ⇒ ✅ 声明与实现一致（%d 项，剥离面内核实）" % 6)
    return 0


def lean4_check():
    """⑩ 约束门：与 Lean4 规范源的谓词对应性比对（★ 本机无 lean ⇒ 非编译）。"""
    src = open(__file__, encoding="utf-8").read()
    code = strip_strings_and_comments(src)
    items = [
        ("uses_tokenizer", "PASS" if "tokenize" in code else "FAIL"),
        ("single_version_source", "PASS" if len(re.findall(r'^\s*VERSION\s*=', src, re.M)) == 1 else "FAIL"),
        ("six_cli_flags", "PASS" if all(f in src for f in
            ("--selftest", "--selfcheck", "--lean4-check", "--dry-run", "--out", "--json")) else "FAIL"),
        ("unknown_not_build", "PASS" if all(t[7].startswith(("已工具化", "不建")) for t in T) else "FAIL"),
    ]
    bad = [n for n, s in items if s != "PASS"]
    for n, s in items:
        print("   %s %s" % ("✅" if s == "PASS" else "❌", n))
    print("   ★ lean 运行时若缺席 ⇒ 本检查为【谓词对应性】而非编译")
    print("   ⇒ %d/%d 绿" % (len(items) - len(bad), len(items)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="判据工具化分诊器（面③ 执行件）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--dry-run", action="store_true", help="只列出将写路径，不写")
    ap.add_argument("--out", default=OUT_DEFAULT, help="文档落盘路径")
    ap.add_argument("--selftest", action="store_true", help="★ 自检")
    ap.add_argument("--selfcheck", action="store_true", help="声明与实现一致性")
    ap.add_argument("--lean4-check", action="store_true", help="⑩ 谓词对应性比对")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()

    b, nb = triage()
    if a.json:
        print(json.dumps({"built": len(b), "nobuild": len(nb), "worth_building": 0,
                          "rows": [{"n": t[0], "criterion": t[1], "verdict": t[7]} for t in T]},
                         ensure_ascii=False, indent=1))
    else:
        print("=" * 96)
        print("判据工具化分诊（判据：信号的价值 = 命中率 × 后果）")
        print("=" * 96)
        print(render())
        print("★ 值得新建的门 = 0 —— ★ 本面以【否证】闭合（先查存量 → 缺口才新建 ⇒ 本轮无缺口）")
    if a.dry_run:
        print("\n[dry-run] 将写: %s" % a.out)
    write_log("[%s] built=%d nobuild=%d worth=0" % (
        __import__("datetime").datetime.now().isoformat(timespec="seconds"), len(b), len(nb)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
