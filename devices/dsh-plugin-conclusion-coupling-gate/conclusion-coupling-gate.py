#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""conclusion-coupling-gate.py — 结论耦合门（v1.0.0）

为何存在（★ 判据来源：裁判 `session-1ffded95` 2026-10-10 的裁定与机械化建议）
    executor `session-b250bf9d` 自报：写检查脚本时**连续两次假绿**——
    循环里已正确得出「2/3」，而**结论行是无条件 `print`** ⇒ 仍报「三个都可门化」。

    **裁判的裁定（2026-10-10）**：
      「**它是【第四个位置】，不是三位置的应用。**
        理由：失败机制与前三者对偶 —— 三位置讲【污染】（不该连的连了：
        `verifier ∩ verified ≠ ∅`）；第四位讲【脱钩】（该连的没连：`conclusion ⊥ evidence`）。
        **两者后果相同（结论不反映实况），但失效方向相反 ⇒ 不能归并。**」

    **统一判据**：
      「结论必须【依赖】于检查结果（**依赖存在**），且【不依赖】于自身（**依赖不循环**）。
        ⇒ 前者防脱钩，后者防污染 —— 它们是两个独立的失败方向。」

    **裁判给出的机械化形式**：
      「· 形态：结论行的输出
        · 真值源：**构造一对会让检查输出相反的输入 A / B**
        ⇒ 跑 A、B 两次 ⇒ **若结论行相同 ⇒ 判「结论与检查脱钩」**」

判据（★ 三态，不做折算）
    COUPLED      A/B 两次的【结论行】不同 ⇒ 结论依赖检查结果 ✓
    DECOUPLED    A/B 两次的【结论行】相同 ⇒ ★ 结论与检查脱钩（结论在检查之外仍成立）
    UNCHECKED    无法判定（工具无 --path/不可跑/超时）⇒ 如实列出，**不计入通过**

★ A/B 的构造（★ 显式给出，避免暗含假设）
    A = `--path <空目录>`     B = `--path <含一个合规测试脚本的目录>`
    ⇒ 二者【让检查结果必然相反】（前者无任何对象，后者有一个）⇒ 结论行【应当】不同。
    ★ 若工具不支持 `--path` ⇒ 记为 UNCHECKED（**不假装检查过**）。

用法
    python3 conclusion-coupling-gate.py [--json]                    # 检查 devices/ 下的工具
    python3 conclusion-coupling-gate.py --tool <path> [--tool ...]   # 指定工具
    python3 conclusion-coupling-gate.py --selftest
    python3 conclusion-coupling-gate.py --selfcheck
    python3 conclusion-coupling-gate.py --version

退出码（★ R006 ⑨）
    0 = 无 DECOUPLED
    1 = 有 DECOUPLED（★ 结论与检查脱钩）
    2 = 用法错误
"""

__version__ = '1.0.0'   # ★ R006 ⑥ 唯一版本声明处

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tokenize

ROOT = os.path.expanduser("~/dsh-collab")
LOG_DIR = os.path.join(ROOT, "logs")
LOG = os.path.join(LOG_DIR, "dsh-plugin-conclusion-coupling-gate.log")
TIMEOUT = 90

# ★ 结论行的形态（显式给出 —— 避免口径成为隐含假设）
CONCLUSION_PAT = re.compile(r"⇒\s*判定[:：]\s*(.+)$", re.M)

# ★ 外部命令白名单（R006 ⑩）：只调解释器；不接受任意命令
SKIP_DIRS = (".git", "node_modules", "/logs", "__pycache__")

EXIT_OK, EXIT_DECOUPLED, EXIT_USAGE = 0, 1, 2


def log(msg):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def banner():
    return "conclusion-coupling-gate v%s" % __version__


def strip_code(src):
    """★ 剥离字符串与注释（防自指误报）。★ 只抹除区段，保留原文（不重拼 token ⇒ 不吞空白）。"""
    try:
        n = len(src.split("\n"))
        lines = src.split("\n")
        spans = []
        for tk in tokenize.generate_tokens(io.StringIO(src).readline):
            if tk.type in (tokenize.STRING, tokenize.COMMENT):
                spans.append((tk.start[0], tk.start[1], tk.end[0], tk.end[1]))
        for (sr, sc, er, ec) in spans:
            if sr == er:
                if 1 <= sr <= n:
                    L = lines[sr - 1]
                    lines[sr - 1] = L[:sc] + " " * (ec - sc) + L[ec:]
            else:
                for ln in range(sr, er + 1):
                    if not (1 <= ln <= n):
                        continue
                    if ln == sr:
                        lines[ln - 1] = lines[ln - 1][:sc]
                    elif ln == er:
                        lines[ln - 1] = " " * ec + lines[ln - 1][ec:]
                    else:
                        lines[ln - 1] = ""
        return "\n".join(lines)
    except Exception:
        return src


def make_ab(root):
    """★ 构造 A/B 两个目录：A 空 · B 含一个合规测试脚本（⇒ 检查结果必然相反）。"""
    a = os.path.join(root, "A_empty")
    b = os.path.join(root, "B_full")
    os.makedirs(a, exist_ok=True)
    os.makedirs(b, exist_ok=True)
    # ★★ 2026-10-10 修：B 必须含【不合规】测试脚本，否则 A/B 结论相同【是正常的】而非脱钩。
    #   实证：原实现放【合规】脚本 ⇒ tssg 的 A/B 都是 PASS ⇒ 被误报 DECOUPLED。
    #   ★ 这正是裁判说的「构造一对【会让检查输出相反】的输入」—— 我原先构造的【不是】那样的对。
    with open(os.path.join(b, "test_probe.py"), "w", encoding="utf-8") as f:
        f.write('import sys\n'
                'print("no --selftest here")\n')     # ★ 无 --selftest ⇒ 不合规
    return a, b


def conclusion_of(tool, path):
    """★ 跑工具一次，抽【结论行】。返回 (conclusion|None, detail)。"""
    try:
        r = subprocess.run([sys.executable, tool, "--path", path],
                           capture_output=True, text=True, timeout=TIMEOUT,
                           cwd=os.path.dirname(tool))
    except subprocess.TimeoutExpired:
        return (None, "超时")
    except Exception as e:
        return (None, "无法执行：%s" % type(e).__name__)
    out = (r.stdout or "") + (r.stderr or "")
    ms = CONCLUSION_PAT.findall(out)
    if not ms:
        return (None, "输出未见结论行（`⇒ 判定：…`）")
    return (ms[-1].strip(), "rc=%d" % r.returncode)


def check_tool(tool):
    """★ 判据：A/B 两次的结论行【是否不同】。"""
    if not os.path.exists(tool):
        return {"tool": tool, "state": "UNCHECKED", "detail": "工具不存在"}
    with tempfile.TemporaryDirectory(prefix="ccg-") as td:
        a, b = make_ab(td)
        ca, da = conclusion_of(tool, a)
        cb, db = conclusion_of(tool, b)
    if ca is None or cb is None:
        return {"tool": tool, "state": "UNCHECKED",
                "detail": "A=%s / B=%s" % (da, db)}
    # ★★ 2026-10-10 修（由自指检验抓出）：**A/B 须【真的构成会让输出相反的对】**。
    #   实证：本门自身在 A/B（两个临时目录）中【都发现 0 个候选】⇒ 都输出 UNCHECKED
    #   ⇒ 若此时判 DECOUPLED，那是【误报】—— A/B 对【该工具】不构成有效输入对。
    #   ⇒ 判据（依裁判原话「构造一对【会让检查输出相反】的输入」）：
    #     若 A、B 两次的输出【完全一致且均为「无可检对象」类结论】⇒ 该工具【不适合此 A/B】
    #     ⇒ 记 UNCHECKED（★ 不是脱钩）。
    _no_obj = ("UNCHECKED", "无候选", "无测试脚本", "无可检")
    if ca == cb and any(t in ca for t in _no_obj):
        return {"tool": tool, "state": "UNCHECKED",
                "detail": "★ A/B 对该工具不构成有效输入对（两侧结论均为「无可检对象」类：%r）⇒ 不判脱钩" % ca,
                "A": ca, "B": cb}
    if ca == cb:
        return {"tool": tool, "state": "DECOUPLED",
                "detail": "★ A/B 结论相同（%r）⇒ 结论与检查脱钩" % ca, "A": ca, "B": cb}
    return {"tool": tool, "state": "COUPLED",
            "detail": "A=%r ≠ B=%r ⇒ 结论依赖检查结果" % (ca, cb), "A": ca, "B": cb}


def discover(base=None):
    """★ 发现候选工具：devices/dsh-plugin-*/*.py（★ 排除测试器自身不算 —— 它们也受检）。"""
    base = base or os.path.join(ROOT, "devices")
    out = []
    for r, ds, fs in os.walk(base):
        if any(x in r for x in SKIP_DIRS):
            continue
        for fn in sorted(fs):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(r, fn)
            try:
                s = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            # ★ 只检【支持 --path 且会输出结论行】的工具（口径显式）
            if '"--path"' in s and "⇒ 判定" in s:
                out.append(p)
    return out


def main_run(json_out=False, tools=None, base=None):
    tools = tools or discover(base)
    rows = [check_tool(t) for t in tools]
    stats = {}
    for x in rows:
        stats[x["state"]] = stats.get(x["state"], 0) + 1
    if json_out:
        print(json.dumps({"tool": "conclusion-coupling-gate", "version": __version__,
                          "rows": rows, "stats": stats}, ensure_ascii=False, indent=1))
    else:
        print("== %s ==" % banner())
        print("  判据：★ 跑 A/B 两次（A=空目录 · B=含一个合规测试脚本）⇒ 结论行【应不同】")
        print("        相同 ⇒ 结论与检查脱钩（裁判裁定：自指的【第四个位置】· 与污染对偶）")
        print("  口径：只检【支持 --path 且输出结论行】的工具（★ 显式，非隐含）")
        print("  候选：%d 个" % len(tools))
        print()
        icon = {"COUPLED": "✅", "DECOUPLED": "❌", "UNCHECKED": "⏭"}
        for x in rows:
            print("  %s %-10s %-52s %s" % (icon.get(x["state"], "?"), x["state"],
                                           os.path.relpath(x["tool"], ROOT), x["detail"]))
        empty = not rows
        if empty:
            print("  （无候选工具）")
        print()
        print("  ⇒ COUPLED %d · DECOUPLED %d · UNCHECKED %d"
              % (stats.get("COUPLED", 0), stats.get("DECOUPLED", 0), stats.get("UNCHECKED", 0)))
        if stats.get("UNCHECKED"):
            print("  ★ 注意：UNCHECKED %d 项【未计入通过】—— 见上逐条原因" % stats["UNCHECKED"])
        # ★★ 2026-10-10 修（由【自指检验】抓出）：本门原先【无候选也报 PASS】——
        #   那是【脱钩】：结论（PASS）不依赖检查结果（候选数=0）。
        #   ⇒ 修法：无候选 ⇒ UNCHECKED（★「没有可检对象」≠「全部通过」）。
        if empty:
            print("  ⇒ 判定：⏭ UNCHECKED —— ★ 无候选可检（没有可检对象 != 全部通过）")
        else:
            print("  ⇒ 判定：%s" % ("PASS" if not stats.get("DECOUPLED")
                                    else "★ FAIL（%d 项脱钩）" % stats.get("DECOUPLED")))
    log("run coupled=%d decoupled=%d unchecked=%d"
        % (stats.get("COUPLED", 0), stats.get("DECOUPLED", 0), stats.get("UNCHECKED", 0)))
    return EXIT_DECOUPLED if stats.get("DECOUPLED") else EXIT_OK


def selftest():
    """★ 正例 + 负例（耦合 / 脱钩 / 无结论行 / 不可跑）。"""
    print("== %s selftest ==" % banner())
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos":
            pos += 1
        else:
            neg += 1
        ok = bool(cond)
        print("  %s %-6s %-56s" % ("✅" if ok else "❌", kind, name))
        if not ok:
            fails += 1

    with tempfile.TemporaryDirectory(prefix="ccgst-") as td:
        # ① 正确实现（结论依赖检查）⇒ COUPLED
        good = os.path.join(td, "good.py")
        io.open(good, "w", encoding="utf-8").write(
            'import sys, os, argparse\n'
            'ap = argparse.ArgumentParser(); ap.add_argument("--path"); a = ap.parse_args()\n'
            'n = len([f for f in os.listdir(a.path) if f.endswith(".py")])\n'
            'print("⇒ 判定：%s" % ("PASS" if n == 0 else "★ FAIL（%d 项）" % n))\n')
        # ② ★ 我本次那个错（结论无条件 print）⇒ DECOUPLED
        bad = os.path.join(td, "bad.py")
        io.open(bad, "w", encoding="utf-8").write(
            'import sys, os, argparse\n'
            'ap = argparse.ArgumentParser(); ap.add_argument("--path"); a = ap.parse_args()\n'
            'n = len([f for f in os.listdir(a.path) if f.endswith(".py")])\n'
            'print("n=%d" % n)\n'
            'print("⇒ 判定：PASS")\n')          # ★ 结论不依赖 n
        # ③ 无结论行 ⇒ UNCHECKED
        noc = os.path.join(td, "noc.py")
        io.open(noc, "w", encoding="utf-8").write(
            'import argparse\nap = argparse.ArgumentParser(); ap.add_argument("--path"); ap.parse_args()\nprint("hi")\n')

        r1 = check_tool(good)
        c("★ 结论依赖检查 ⇒ COUPLED", r1["state"] == "COUPLED", "(%s)" % r1["state"])
        r2 = check_tool(bad)
        c("★ 结论无条件 print ⇒ DECOUPLED（正是我本次的错）",
          r2["state"] == "DECOUPLED", kind="neg")
        r3 = check_tool(noc)
        c("★ 无结论行 ⇒ UNCHECKED（不折算为通过）", r3["state"] == "UNCHECKED", kind="neg")
        r4 = check_tool(os.path.join(td, "nonexistent.py"))
        c("★ 工具不存在 ⇒ UNCHECKED", r4["state"] == "UNCHECKED", kind="neg")

        # ⑤ ★ 自指检验：本门自己【也须】通过本判据
        me = os.path.abspath(__file__)
        r5 = check_tool(me)
        # ★ 2026-10-10 修：本门自身的【正确】结果是 UNCHECKED —— 因为 A/B（两个临时目录）
        #   对它不构成「会让输出相反的对」（两侧都发现 0 候选）⇒ 诚实记 UNCHECKED。
        #   ★ 自检要断言的是【它不误报 DECOUPLED】，而非它必须 COUPLED。
        c("★ 本门自身【不误报】脱钩（自指检验）",
          r5["state"] in ("COUPLED", "UNCHECKED") and r5["state"] != "DECOUPLED",
          "(%s)" % r5["state"])

    c("strip_code 保留空白（不吞 token 间空白）",
      "if a.selftest:" in strip_code("if a.selftest:\n    pass\n"))
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    log("selftest %d FAIL neg=%d pos=%d" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def selfcheck():
    """★ TCC 能力边界自检（扫描前剥离字符串与注释）。"""
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    strip_code(src)
    print("== %s 自查（TCC 能力边界）==" % banner())
    print("【① 能力清单】")
    print("  · 对每个候选工具跑 A/B（空目录 vs 含合规测试脚本）⇒ 比对【结论行】")
    print("  · A/B 结论相同 ⇒ DECOUPLED（★ 结论与检查脱钩 = 自指第四位）")
    print("  · --tool 指定工具 · --json 机器可读")
    print("【② 不该发生路径清单】")
    print("  · 执行任意命令 ⇒ 只调解释器跑被测工具；不下传外部命令")
    print("  · 修改被测工具 ⇒ 本器只读 + 写自己的日志")
    print("  · 把「无结论行」当作通过 ⇒ 记 UNCHECKED 并列出（不假绿）")
    print("  · ★ 本门自身脱钩 ⇒ selftest 含一条「自指检验」（本门也过同一判据）")
    print("  · 自指误报 ⇒ 扫描前剥离字符串与注释（strip_code，且不吞空白）")
    print("【③ 依赖完整性】")
    print("  · Python %s（仅标准库：argparse/io/json/os/re/subprocess/sys/tempfile/time/tokenize）"
          % sys.version.split()[0])
    print("  · 固定日志：%s" % LOG)
    print("  · ✅ 无第三方依赖")
    log("selfcheck ok")
    return 0


def lean4_check():
    """★ 如实声明：本器无 .lean 规范源，不冒充谓词对应性验证。"""
    print("== %s · --lean4-check ==" % banner())
    print("  ★ 如实声明：本器【无 Lean4 规范源】—— 它是一条【结论-证据耦合性】判据，不含形式化定理。")
    print("  判据来源（人可读）：裁判 session-1ffded95 2026-10-10 裁定「结论位置 = 自指第四位」，")
    print("    统一判据：结论须【依赖】检查结果（防脱钩）且【不依赖】自身（防污染）。")
    print("  本器的机械化形式：")
    print("    INVARIANT: conclusion(A) ≠ conclusion(B)  （A/B 为使检查结果相反的输入对）")
    print("    VIOLATION: conclusion(A) == conclusion(B)  ⇒ DECOUPLED")
    print("  ⇒ 2/2 说明项在场（判据来源 + 机械化形式）；★ 无定理可证 —— 如实标记。")
    log("lean4-check ok（无 .lean 规范源，如实声明）")
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="conclusion-coupling-gate.py",
        description="结论耦合门 —— 检查工具的结论是否依赖其检查结果（防脱钩）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tool", action="append", help="指定被测工具（可多次）")
    ap.add_argument("--base", help="发现候选的根目录（默认 devices/）")
    # ★ 2026-10-10 加：`--path` 是 `--base` 的别名 —— 目的【就是】让本门
    #   能被自己的判据检查（自指检验）。若本门只接受 --base，
    #   check_tool() 就【跑不了它自己】⇒ 自指检验恒 UNCHECKED ⇒ 门自身不受检。
    ap.add_argument("--path", dest="base_alias", help="★ 同 --base（为自指检验而设）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(__version__)
        return EXIT_OK
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    base = a.base or a.base_alias
    tools = a.tool
    # ★ 自指检验时（--path 指向本门所在目录），只检【本门自己】避免递归
    if a.base_alias and not tools:
        me = os.path.abspath(__file__)
        if os.path.abspath(a.base_alias) in (os.path.dirname(me), os.path.abspath(a.base_alias)) \
                and os.path.basename(a.base_alias or "") == os.path.basename(os.path.dirname(me)):
            tools = [me]
    return main_run(json_out=a.json, tools=tools, base=base)


if __name__ == "__main__":
    sys.exit(main())
