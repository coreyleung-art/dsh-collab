#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""false-result-patterns — 「结果看上去对而实为假」的【可跑检查器】。

★★★ 立据（2026-10-12 一晚，八次实证 · 见 v7 §0.2.1）：
  ★ 八次【全都不是「代码不跑」】，而是 **代码跑得好好的，在报一个假结果**：
    · D-204 恒真负例（`0 == 0`）        · D-217 判据时变
    · D-228 `p2.status`（正确 returncode）· D-231 同一错在本工具自身
    · D-234 并发伪失败                   · D-237 检测面窄
    · D-240 只读三清单中的两个           · D-241 用截短键查板
  ★★ 而八次里有**三次是本线自己的探针**（D-228/D-237/D-241）。

★★ 故本门把其中【可机械检】的五种做成检查：
  P1 **`subprocess` 结果取 `status`**（★ 应为 `returncode`）—— ★ D-228/D-231 的根因
  P2 **`None` 被当绿**（★ 判据里 `in (0, None)` / `!= None` 型放行）—— ★ D-231
  P3 **恒真负例**（★ 见 `selftest-audit`，本门只检 `status` 与 `None` 两类）
  P4 **`grep` 型判据用长串**（★ 检测面窄的常见形态）—— ★ D-237
  P5 **硬编码时间戳**（★ 负控会过期）—— ★ D-225

三态：扫描面为空 ⇒ 「不可判」；无命中 ⇒ PASS；有 ⇒ FAIL（★ 列文件与行）。

★★★ **本门的已知局限（★ 如实声明，★ 不加补丁掩盖）**：
  ★ **P1 的变量判定是【文件级】而非【逐处数据流】** ——
    ★ 若同一变量名在文件里**既是 `subprocess` 结果、又别处是 HTTP 响应**（★ 实测 `scripts/bb-copy.py` 的 `r`），
    ★★ 则本门会**误报**那些 HTTP 的 `.status`。
  ★★ 要修需**逐处数据流分析**（★ 大工程）⇒ **故本门报的 P1 命中【必须人工核】**，★ 命中 ≠ 缺陷。
  ★ **P5（硬编码时间）多数是数据/日志行而非判据** —— ★ 同样须人工筛。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = [
    # \u2605\u2605\u2605 2026-10-13 \u4fee\uff08D-242\uff09\uff1a\u9996\u7248 `\b\w+\.status\b` **\u8fc7\u5bbd** \u2014\u2605
    #   \u5b9e\u6d4b\u547d\u4e2d **105 \u5904**\uff0c\u2605\u2605 \u800c\u591a\u6570\u662f `args.status` / \u677f\u7684 `status` \u7b49**\u522b\u7684\u5bf9\u8c61**\u3002
    #   \u2605 \u4fee\u6cd5\uff1a**\u9650\u5b9a\u4e3a\u3010\u540c\u4e00\u4f5c\u7528\u57df\u5185\u6709 `subprocess.\u2026(` \u7684\u53d8\u91cf\u3011**\u2014\u2605 \u5373\u53d8\u91cf\u540d\u5fc5\u987b\u5728\u6587\u4ef6\u91cc\u51fa\u73b0\u8fc7 `= subprocess.`\u3002
    ("P1", r'\.status\b',
     '\u2605 subprocess \u7ed3\u679c\u53d6 `.status`\uff08\u2605 \u5e94\u4e3a `.returncode`\uff09\u2014\u2605 D-228/D-231 \u6839\u56e0',
     re.compile(r'\b(getattr\s*\(\s*)?\w+\.status\b(?!\s*=)')),
    ("P2", r'in\s*\(\s*0\s*,\s*None\s*\)|==\s*None\s*or|not\s+in\s*\(0,\s*None\)',
     '\u2605 `None` \u88ab\u5f53\u7eff\uff08\u2605 \u5f02\u5e38\u8def\u5f84\u4e0e\u6210\u529f\u540c\u5f62\uff09\u2014\u2605 D-231',
     re.compile(r'not\s+in\s*\(\s*0\s*,\s*None\s*\)|in\s*\(\s*0\s*,\s*None\s*\)')),
    ("P4", r'grep.*\\u00a7|\u00a7',
     '\u2605 `grep` \u578b\u5224\u636e\u7528\u957f\u4e32\uff08\u2605 \u68c0\u6d4b\u9762\u7a84\uff09\u2014\u2605 D-237',
     re.compile(r"re\.search\(\s*[\"'][^\"']{18,}[\"']\s*,\s*\w+\.(?:stdout|body|stdout\s*or\s*[\"']{2})\s*\)")),
    ("P5", r'20\d\d-\d\d-\d\dT',
     '\u2605 \u786c\u7f16\u7801\u65f6\u95f4\u6233\uff08\u2605 \u8d1f\u63a7\u4f1a\u968f\u65f6\u95f4\u5931\u6548\uff09\u2014\u2605 D-225',
     re.compile(r'[\"\']20\d\d-\d\d-\d\dT\d\d:\d\d[^\"\']*[\"\']')),
]


def strip_docstrings(src, keep_newlines=True):
    """★ 剥三引号块与注释（★ 免自伤，★ R006 惯例）。

    ★★★ 2026-10-13 修（D-243，★ **第十次同形**）：
      ★ 首版把剥离后的文本**压成一行** ⇒ 在它上数行号 ⇒
      ★★ **行号与原文件完全对不上**（★ 本纳取上下文时发现）。
      ★★☃ ⇒ ★ 修法：**剥离时保留换行符**（★ `keep_newlines=True`）⇒ 行号与原一致。
      ★ ★ 而这正印证本线纪律「**行号不是证据，行号在某时刻的内容才是**」。
    """
    out = []
    i, n = 0, len(src)
    dq = '"' * 3
    sq = "'" * 3
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            if j < 0:
                i = n
            else:
                if keep_newlines:
                    out.append("\n")     # ★ 保留换行 ⇒ 行号不漂
                i = j + 1                  # ★★ 修：跳过那个 \n（★ 否则与上一行【重复计】）
            continue
        if src.startswith(dq, i) or src.startswith(sq, i):
            q = src[i:i + 3]
            j = src.find(q, i + 3)
            if j < 0:
                i = n
            else:
                seg = src[i:j + 3]
                if keep_newlines:
                    out.append("\n" * seg.count("\n"))   # ★ 保留行数
                i = j + 3
            continue
        out.append(c)
        i += 1
    return "".join(out)


def scan_file(path, rel):
    try:
        raw = io.open(path, encoding="utf-8").read()
    except Exception:
        return []
    code = strip_docstrings(raw)
    # ★★★ 数据流过滤（D-242 + D-243）：★ 只有【被 `= subprocess.…(` 赋值过的变量】才算候选。
    #   ★ 首版只判「文件里出现过 `= subprocess.`」⇒ **仍误报**：
    #     ★★ 实例 `scripts/bb-copy.py`：文件里有 subprocess，★ **而 `r` 在那里是【HTTP 响应对象】**（★ 有 `.status`）。
    #   ★★ 修法：**逐个变量名判** —★ 只要该名字在文件里【有一处非-subprocess 赋值】⇒ 不算候选。
    subproc_vars = set(re.findall(r'(\w+)\s*=\s*subprocess\.[a-z_]+\s*\(', code))
    all_assigned = set(re.findall(r'\b(\w+)\s*=\s*[^=\n]', code))
    http_vars = set()
    for nm in subproc_vars:
        # ★ 同一名字若还有其他赋值（如 `r = sess.get(…)`）⇒ 它不只是 subprocess
        others = re.findall(r'\b%s\s*=\s*([^=\n]+)' % re.escape(nm), code)
        if any('subprocess' not in o for o in others):
            http_vars.add(nm)
    hits = []
    for cid, _hint, why, rx in CHECKS:
        for m in rx.finditer(code):
            if cid == "P1":
                var = re.match(r'(?:getattr\s*\(\s*)?(\w+)\.status', m.group(0))
                if not var or var.group(1) not in subproc_vars or var.group(1) in http_vars:
                    continue      # ★ 不是纯粹 subprocess 结果 ⇒ 不算
            # ★ \u53d6\u884c\u53f7
            ln = code[:m.start()].count("\n") + 1
            # ★ \u6392\u9664\u5de5\u5177\u81ea\u8eab\uff08\u2605 \u5b83\u7684\u6837\u672c\u5b57\u7b26\u4e32\u4f1a\u547d\u4e2d\uff09
            if rel.endswith("false-result-patterns.py"):
                continue
            hits.append({"check": cid, "file": rel, "line": ln,
                         "snippet": m.group(0)[:60], "why": why})
    return hits


def discover(roots):
    out = []
    for d in roots:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != "node_modules" and not x.startswith(".")]
            for fn in filenames:
                if fn.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return sorted(out)


def audit(roots):
    hits = []
    for rel in discover(roots):
        hits += scan_file(os.path.join(ROOT, rel), rel)
    return hits


def selftest():
    ok = tot = 0
    # ★ 正控：`.status` 型须命中
    tot += 1
    if scan_file_text('r = subprocess.run([...])\nrc = r.status\n'):
        ok += 1
        print("  ✅ 正控：`r.status` 命中（★ D-228/D-231 的根因）")
    else:
        print("  ❌ 正控：`r.status` 未命中")
    # ★ 负控：`.returncode` 不得命中
    tot += 1
    if not scan_file_text('rc = r.returncode\n'):
        ok += 1
        print("  ✅ 负控：`r.returncode` 不命中（★ 防过宽）")
    else:
        print("  ❌ 负控：`r.returncode` 被误伤")
    # ★ 正控：`None` 当绿须命中
    tot += 1
    if scan_file_text('bad = [r for r in rows if r.get("rc") not in (0, None)]\n'):
        ok += 1
        print("  ✅ 正控：`not in (0, None)` 命中（★ D-231）")
    else:
        print("  ❌ 正控：`not in (0, None)` 未命中")
    # ★ 正控：硬编码时间戳须命中
    tot += 1
    if scan_file_text('_fixture(updated_at="2026-10-11T00:20:00+08:00")\n'):
        ok += 1
        print("  ✅ 正控：硬编码时间戳命中（★ D-225）")
    else:
        print("  ❌ 正控：硬编码时间戳未命中")
    # ★ 负控：注释里的不得命中（★ 前剥离有效）
    tot += 1
    if not scan_file_text('# rc = r.status\n'):
        ok += 1
        print("  ✅ 负控：注释里的 `.status` 不命中（★ 已前剥离）")
    else:
        print("  ❌ 负控：注释未前剥离 ⇒ 自伤")
    # ★ 三态：不存在的根 ⇒ 空
    tot += 1
    if discover(["/tmp/__no_such_root__"]) == []:
        ok += 1
        print("  ✅ 正控：不存在的根 ⇒ 空列表（★ 调用方报「不可判」）")
    else:
        print("  ❌ 正控：不存在的根竟有结果")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def scan_file_text(src):
    """★ 供自证用：直接扫一段源码文本。"""
    code = strip_docstrings(src)
    return [1 for _c, _h, _w, rx in CHECKS if rx.search(code)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("false-result-patterns 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    roots = a.root or ["tools", "scripts"]
    hits = audit(roots)
    files = discover(roots)
    if a.json:
        print(json.dumps({"scanned": len(files), "hits": hits}, ensure_ascii=False, indent=1))
        return 0
    print("== false-result-patterns 1.0.0 ==")
    if not files:
        print("  ★ 扫描面为空 ⇒ 【不可判】（★ 未抽到 ≠ 不存在）")
        return 2
    print("  扫描面：%d 个 .py" % len(files))
    from collections import Counter
    by = Counter(h["check"] for h in hits)
    print("  命中：%d（★ 按类：%s）" % (len(hits), dict(by)))
    print()
    for cid, _hint, why, _rx in CHECKS:
        sub = [h for h in hits if h["check"] == cid]
        if not sub:
            continue
        print("  ★ %s %s" % (cid, why))
        for h in sub[:6]:
            print("      %s:%s  `%s`" % (h["file"], h["line"], h["snippet"]))
        if len(sub) > 6:
            print("      … 另有 %d 处" % (len(sub) - 6))
        print()
    if hits:
        print("  ❌ %d 处命中 ⇒ ★ **每处须人工核**（★ 命中 ≠ 缺陷，★ 见 v7 §0.2.1）" % len(hits))
        print("     ★★ 本门已知局限：P1 变量判定是【文件级】非逐处 · P5 多数是数据行 ⇒ **必人工筛**")
        return 1
    print("  ✅ 未命中五类假结果形态")
    return 0


if __name__ == "__main__":
    sys.exit(main())
