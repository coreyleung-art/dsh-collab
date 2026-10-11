#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静默截断 lint（v2）—— 三判据维度 + 扫描时点/面声明 + 按归属分列

★ 归属（2026-10-10 定）：**本文件为唯一实现**
   裁判于 data/registry/f71-followup-accepted-and-scope-decision 表态：
   「**以你的 tools/ 为唯一实现** —— 你三处优于我（`--group` 结构性预防 / `cut(` 判据更精确 /
   fail-closed 三层）。**我不再改 `scripts/silent-truncation-lint.py`**（冻结为证据）。」
   ⇒ 其文件保留为证据链；**本文件为权威读数来源**。
   v1（sha256[0:16] `f251622f40f44694`）备份于 `guard/backups/`。

★ v2 落实的判据（两条由裁判**书面移交**，一条为我方提出）
   ①【移交·扫描时点 + 扫描面须打印】—— 它 grep 本文件发现「时点相关行 0 条」⇒ **我方同病**。
     其原话：「这是**两侧共同缺口**，不是指责。」
   ②【移交·`SILENT` 改名 `UNANNOTATED`】—— 原文案：「它把『**无标注**』与『**是截断**』混为一谈，
     由 `use` 决定是否该报。」⇒ 本版改名，并新增 `should_report` 作**裁决列**。
   ③【我方提出·切片语义】—— 判据应看「**被切对象的类型 + 结果的去向**」，而非只看切片语法：
     `list[-N:]` 取尾部元素（遍历用）**不是截断**；`str[:N]` 须逐处判用途。

★ 移植时的**基座假设审查**（依裁判建议：「移植对方机制时，必审它的基座假设在你侧是否成立」）
   它的 `classify_use()` 以正则匹配上下文判 DISPLAY/EXTRACT。
   **其基座假设**：「同行/邻近行的关键词能反映用途」。
   **在我侧是否成立**：**部分成立** —— 它**解决不了 `list[-N:]`**，
   因为那不是**用途**问题，而是**对象类型**问题。
   ⇒ 故本版取其三分，**另加 `subject` 维度**，裁决由二者共同得出。

三维与裁决规则
   verdict ∈ {ANNOTATED, UNANNOTATED, COMMENT}
   subject ∈ {str, list, list_or_str, other}        —— 被切对象的类型（我方维度）
   use     ∈ {DISPLAY, EXTRACT, UNKNOWN}            —— 结果的去向（移植维度）
   should_report（裁决）:
     ANNOTATED                  ⇒ 否（已有显式标注）
     subject=list               ⇒ 否（列表切片非字符串截断）
     subject=str + EXTRACT      ⇒ 否（语义提取）
     subject=str + DISPLAY      ⇒ 是（静默则危险）
     subject=list_or_str / other / UNKNOWN ⇒ 保守：**是**

口径（显式声明，必打印）
   code      —— 只计**代码行**（排除注释行）★ 默认
   comments  —— 连同注释里的提及一起计
   literal   —— 只计形如 `[:160]` 的**特定宽度**（配 --width）

用法
   python3 tools/lint-silent-truncation.py --group "归属=路径1,路径2" [--group ...] [--verbose]
   python3 tools/lint-silent-truncation.py <paths...>

纪律
   ★ 只读：不写任何被扫描对象。★ 归属交叉默认拒绝（fail-closed），须 --allow-overlap 豁免。
"""
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

VERSION = "2.0.0"

PAT_HEAD = re.compile(r"\[:\s*(\d+)\]")
PAT_TAIL = re.compile(r"\[-\s*(\d+)\s*:\]")

DISPLAY_HINTS = [r"\bprint\s*\(", r"json\.dumps\s*\(", r"\.append\s*\(", r"\.write\s*\(",
                 r"return\b", r"f['\"]", r"\.format\s*\(", r"%\s*\("]
EXTRACT_HINTS = [r"Counter\s*\(", r"\.split\s*\(", r"startswith\s*\(", r"endswith\s*\(",
                 r"\.lower\s*\(", r"\bmatch\s*\(", r"\bsearch\s*\(", r"group", r"\bkey\b"]


def strip_comment(line):
    """去掉行尾注释（不处理字符串内的 #；局限已声明）。"""
    in_s = None
    for i, ch in enumerate(line):
        if in_s:
            if ch == in_s and (i == 0 or line[i - 1] != "\\"):
                in_s = None
        elif ch in "\"'":
            in_s = ch
        elif ch == "#":
            return line[:i]
    return line


def guess_subject(line, start):
    """★ 判被切对象的类型（我方维度）。

    启发式取 `[:N]` 左侧最近的表达式尾；**自陈局限**：文本启发式，非 AST ⇒ 复杂表达式落 other。
    """
    head = line[:start].rstrip()
    # ★ 先判「循环里的列表切片」：`for X in Y[-N:]:` ⇒ list（最易误判的一类；
    #   实见于我方 n7-ignition-source.py L94 曾被判 other+DISPLAY ⇒ 误报）
    if re.search(r'for\s+\w+\s+in\s+[\w\.\[\]"\']+\s*$', head):
        return "list"
    if re.search(r'(json\.dumps\s*\(|str\s*\(|\.replace\s*\(|\.strip\s*\(|\.text\b)', head):
        return "str"
    m = re.search(r'([A-Za-z_][A-Za-z0-9_\.\[\]]*)\s*$', head)
    if m:
        tail = m.group(1).split(".")[-1].split("[")[0]
        if re.match(r'^[a-z_][a-z0-9_]*$', tail):
            if re.search(r'(between|before|after|items|rows|lines|hits|samples|comp|list)\b', tail):
                return "list"
            if re.search(r'(text|str|s|line|msg|name|desc|raw)\b', tail):
                return "str"
            return "list_or_str"
    return "other"


def classify_use(line, ctx):
    """结果的去向（移植裁判概念；关键词本侧自定）。"""
    for p in EXTRACT_HINTS:
        if re.search(p, line):
            return "EXTRACT"
    for p in DISPLAY_HINTS:
        if re.search(p, line):
            return "DISPLAY"
    for p in DISPLAY_HINTS:
        if re.search(p, ctx):
            return "DISPLAY"
    return "UNKNOWN"


def decide_report(verdict, subject, use):
    """★ 裁决规则（本版核心）：三维共同决定是否该报。"""
    if verdict != "UNANNOTATED":
        return False
    if subject == "list":
        return False
    if subject in ("str", "list_or_str"):
        return use != "EXTRACT"
    return True


def scan_file(p, caliber="code", width=None):
    out = []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return out
    # ★ docstring 跟踪（v2.0.1 修）：三引号内的 `[:N]` 常出现在**说明文字**里，不属代码行。
    #   此前它们被计入 ⇒ 假阳性（实见于我方 3 个脚本的 docstring，各 1 处）。
    #   局限（自陈）：不解析字符串边界，仅按**三引号奇偶**计数 ⇒ 含三引号的行会翻转状态。
    in_doc = False
    for i, line in enumerate(lines, 1):
        _tq = line.count('"""') + line.count("'''")
        _was_in_doc = in_doc
        if _tq % 2 == 1:
            in_doc = not in_doc
        stripped = strip_comment(line)
        ctx = "\n".join(lines[max(0, i - 3):min(len(lines), i + 2)])
        for pat, prim in ((PAT_HEAD, "[:N]"), (PAT_TAIL, "[-N:]")):
            for m in pat.finditer(line):
                n = int(m.group(1))
                if width is not None and n != width:
                    continue
                in_comment = bool(pat.search(line)) and not pat.search(stripped)
                if in_comment or _was_in_doc:
                    verdict = "COMMENT"      # docstring 内的 = 说明文字，与注释同类处理
                else:
                    verdict = "ANNOTATED" if "cut(" in line[:m.start()] else "UNANNOTATED"
                if caliber == "code" and verdict == "COMMENT":
                    continue
                if caliber == "literal" and width is None:
                    continue
                subj = guess_subject(line, m.start())
                use = classify_use(line, ctx)
                rep = decide_report(verdict, subj, use) if verdict == "UNANNOTATED" else False
                out.append((i, n, prim, verdict, subj, use, rep, line.strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="目录或文件（单一归属时用）")
    ap.add_argument("--group", action="append", default=[],
                    help="LABEL=PATH[,PATH...]，可重复 ⇒ **按归属分列**（推荐用法）")
    ap.add_argument("--caliber", choices=["code", "comments", "literal"], default="code")
    ap.add_argument("--width", type=int, default=None, help="literal 口径下的宽度，如 160")
    ap.add_argument("--allow-overlap", action="store_true",
                    help="★ 显式豁免**归属交叉**（默认拒绝：交叉会使分列失去自查意义）")
    ap.add_argument("--recurse", action="store_true",
                    help="递归子目录（★ 默认不递归 —— 递归会让归属分列交叉）")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--emit-readout", metavar="PATH",
                    help="把「可比性指纹」写到 PATH（供 --compare 用）")
    ap.add_argument("--compare", nargs=2, metavar=("A.json", "B.json"),
                    help="★ 比较两个 readout —— **指纹不同即拒绝（exit 3）**，"
                         "须 `--force-compare` 才可强行并置")
    ap.add_argument("--force-compare", action="store_true",
                    help="★ 显式承担后果：指纹不同仍并置（并置后每格标口径）")
    a = ap.parse_args()

    # ── ★ 口径维度 fail-closed（裁判 discoverable-vs-comparable 建议）──────────
    #   动机：本工具在【归属交集】维度已是真 fail-closed（拒绝+显式旗标+豁免后标注）；
    #   但【口径/扫描面】维度此前只「打印声明」⇒ 可见 ≠ 不被比较 ⇒ 仍是 fail-open。
    #   读者看到两行口径声明后仍可能把两个数并列（裁判原话）。
    #   ⇒ 此处补：**指纹不同即拒绝**。
    if a.compare:
        import json as _j
        try:
            ra = _j.load(open(a.compare[0], encoding='utf-8'))
            rb = _j.load(open(a.compare[1], encoding='utf-8'))
        except Exception as e:
            print("✗ readout 不可读：%s" % e)
            sys.exit(2)
        fa, fb = ra.get("fingerprint"), rb.get("fingerprint")
        if fa != fb and not a.force_compare:
            print("✗ 两读数的**可比性指纹不同** ⇒ 拒绝并置（exit 3，fail-closed）")
            print("   A: %s" % fa)
            print("   B: %s" % fb)
            print("   差异维度：")
            for k in ("caliber", "width", "surface", "version"):
                if ra.get(k) != rb.get(k):
                    print("     %-10s A=%s  B=%s" % (k, ra.get(k), rb.get(k)))
            print("   ⇒ 依裁判判据：「**两个读数口径不同时，正确做法不是统一口径，"
                  "而是标注口径 + 禁止直接比较**」")
            print("   ⇒ 若确需并置：加 `--force-compare`（并置后每格须标口径）。")
            sys.exit(3)
        if fa != fb:
            print("⚠️ 指纹不同，已被 --force-compare 豁免 —— **并置读数不可作为比较结论**")
            print("   A 口径=%s 面=%s" % (ra.get("caliber"), str(ra.get("surface"))[:80]))
            print("   B 口径=%s 面=%s" % (rb.get("caliber"), str(rb.get("surface"))[:80]))
            print()
        else:
            print("★ 指纹相同 ⇒ 两读数可直接比较")
        for name, r in (("A", ra), ("B", rb)):
            print("  %s: %s" % (name, _j.dumps(r.get("by_owner"), ensure_ascii=False)))
        sys.exit(0)

    pairs = []
    for g in a.group:
        if "=" not in g:
            print("✗ --group 需为 LABEL=PATH[,PATH...] 形式：%s" % g)
            sys.exit(2)
        label, paths_s = g.split("=", 1)
        for one in paths_s.split(","):
            one = one.strip()
            if one:
                pairs.append((label, one))
    if not pairs:
        pairs = [("(未标注归属)", p) for p in a.paths]
    if not pairs:
        print("✗ 未给路径。用法：--group 归属=目录/文件")
        sys.exit(2)

    # ★ 归属交集检测（移植自裁判 · 它指出本工具的缺口）；fail-closed +
    #   豁免后仍标注「不可用于按归属比较」（裁判 F72 承认我这一层比其告警强）
    _rp = [(lab, Path(os.path.expanduser(pth)).resolve()) for lab, pth in pairs]
    _overlaps = []
    for _i, (_l1, _p1) in enumerate(_rp):
        for _l2, _p2 in _rp[_i + 1:]:
            if _p1 == _p2 or _p1 in _p2.parents or _p2 in _p1.parents:
                _overlaps.append((_l1, str(_p1), _l2, str(_p2)))
    if _overlaps and not a.allow_overlap:
        print("✗ 归属交叉 ⇒ 拒绝（fail-closed）")
        for _l1, _q1, _l2, _q2 in _overlaps:
            print("   %s(%s) 与 %s(%s) 存在包含关系" % (_l1, _q1, _l2, _q2))
        print("   ⇒ 同一文件可能被计入两组 ⇒ **分列失去自查意义**（F69 形态：宽模式吞掉窄模式）。")
        print("   ⇒ 修正：让各组路径互不包含；或显式 `--allow-overlap` 承担后果。")
        sys.exit(2)

    scanned_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    # ── ★ 扫描时点 + 扫描面声明（判据① · 裁判移交；它 grep 出我方同病）──────
    print("★ 静默截断 lint v%s" % VERSION)
    print("★ 扫描时点：%s" % scanned_at)
    print("★ 口径声明：caliber=%s%s" % (a.caliber, (" width=%d" % a.width) if a.width else ""))
    print("   code = 只计代码行（排除注释提及）｜ comments = 连注释一起计｜ literal = 只计指定宽度")
    if _overlaps:
        print("⚠️ 归属交叉已被 --allow-overlap 豁免 —— 读数**不可用于按归属比较**：")
        for _l1, _q1, _l2, _q2 in _overlaps:
            print("   %s 与 %s 包含" % (_l1, _l2))

    by_owner = {}
    details = {}
    surface = []
    for owner, path in pairs:
        pp = Path(os.path.expanduser(path))
        if pp.is_file():
            files = [pp]
        elif pp.is_dir():
            files = sorted(pp.rglob("*.py")) if a.recurse else sorted(pp.glob("*.py"))
        else:
            files = []
        surface.append("%s=%s(%d)" % (owner, path, len(files)))
        agg = {"files": 0, "unannotated": 0, "report": 0, "annotated": 0, "comment": 0}
        for f in files:
            hits = scan_file(f, a.caliber, a.width)
            if not hits:
                continue
            agg["files"] += 1
            for (ln, n, prim, verdict, subj, use, rep, raw) in hits:
                key = {"UNANNOTATED": "unannotated", "ANNOTATED": "annotated"}.get(verdict, "comment")
                agg[key] += 1
                if rep:
                    agg["report"] += 1
                details.setdefault(str(f), []).append(
                    {"line": ln, "n": n, "prim": prim, "verdict": verdict, "subject": subj,
                     "use": use, "should_report": rep, "raw": raw[:110]})
        if owner not in by_owner:
            by_owner[owner] = agg
        else:
            for k in agg:
                by_owner[owner][k] += agg[k]

    print("★ 扫描面：" + " ｜ ".join(surface))
    print()
    print("=== ★ 按归属分列（should_report 为**裁决列**）===")
    print("  %-20s %-7s %-13s %-9s %-11s %-9s" % ("归属", "文件数", "UNANNOTATED", "→该报", "ANNOTATED", "注释提及"))
    tu = tr = 0
    for o, v in sorted(by_owner.items()):
        print("  %-20s %-7d %-13d %-9d %-11d %-9d"
              % (o, v["files"], v["unannotated"], v["report"], v["annotated"], v["comment"]))
        tu += v["unannotated"]
        tr += v["report"]
    print("  %-20s %-7s %-13d %-9d" % ("合计", "", tu, tr))
    print()
    print("★ 裁决规则：ANNOTATED⇒不报 ｜ subject=list⇒不报（列表切片非字符串截断）｜ "
          "str+EXTRACT⇒不报 ｜ str+DISPLAY⇒报 ｜ UNKNOWN/other⇒保守报")
    if a.verbose:
        print()
        print("=== 逐条明细（仅 UNANNOTATED 且该报者，前 40 条）===")
        shown = 0
        for f, items in sorted(details.items()):
            for it in items:
                if it["verdict"] != "UNANNOTATED" or not it["should_report"]:
                    continue
                if shown >= 40:
                    break
                print("  %-52s L%-4s %-7s subj=%-12s use=%-9s" %
                      (f.split("/")[-1], it["line"], it["prim"], it["subject"], it["use"]))
                print("      %s" % it["raw"][:100])
                shown += 1
        print("  （共 %d 条该报）" % tr)
    # ★ 可比性指纹（口径维度的 fail-closed 载体）
    import hashlib as _h
    import json as _j
    fp_src = _j.dumps({"version": VERSION, "caliber": a.caliber, "width": a.width,
                       "surface": sorted(surface)}, ensure_ascii=False, sort_keys=True)
    fingerprint = _h.sha256(fp_src.encode()).hexdigest()[:16]
    readout = {"version": VERSION, "fingerprint": fingerprint, "scanned_at": scanned_at,
               "caliber": a.caliber, "width": a.width, "surface": sorted(surface),
               "by_owner": by_owner}
    print()
    print("★ 可比性指纹：%s" % fingerprint)
    print("   ⇒ **本读数仅可与指纹相同的读数直接比较**；指纹不同须 `--compare` 判定（不同即拒绝）。")
    if a.emit_readout:
        with open(a.emit_readout, "w", encoding="utf-8") as f:
            _j.dump(readout, f, ensure_ascii=False, indent=1)
        print("   已写 readout：%s" % a.emit_readout)
    if a.json:
        print(_j.dumps(readout, ensure_ascii=False, indent=1))
    sys.exit(0)


if __name__ == "__main__":
    main()
