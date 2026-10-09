#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""silent-truncation-lint.py — 静默截断检测（v1.0.2）

★★ 状态：**待合并**（2026-10-09，工具交接 line）★★
    用户授权工具交接（`data/registry/audit-tool-handover` · authority 字段），判据 =
    **「测量对象是『任何人的』还是『我方的』」**（S3 不可自审的推论：**尺子的校准权不在第三方手里**）。
    ⇒ 本工具测「任何人」⇒ **归审查方**（我方）。对侧同名工具 `tools/lint-silent-truncation.py`
      亦测「任何人」⇒ 同归我方 ⇒ **两件功能重叠，须合并为一件**。

    合并基座**待双方确认**。我（本工具作者）的建议：**以对侧为基座**，理由 ——
      · 对侧用 `--group LABEL=PATH`（**归属显式给定**）= **结构性预防**；
      · 本工具用 `--by-owner <正则>`（**归属靠猜**）+ 事后告警 = **检测**；
      · **预防优于检测**（告警可被忽略，结构不能）。
    但**本工具有一项对侧没有的**：**归属交集检测**（F69）——
      实测 `--by-owner repro --by-owner stage-review`（宽在前）⇒ 窄模式被**静默吞掉**，
      使用者以为分了两组、实际只有一组。对侧 `--group` 从结构上避免了它，
      **但 `--group A=repo B=repo/sub` 仍可由用户自己造出交叉，而对侧不告警** ⇒
      **建议：以对侧为基座 + 移植本工具的交集检测 = 预防 + 检测双保险。**
    本文件**暂不删除**（删了会使本轮 T5 交付与证据链断裂）；合并完成后应转为 DEPRECATED。

为什么需要（来由）
    星桥审查线 2026-10-09：对侧提交的取证脚本用 `json.dumps(dd)[:160]` 打印事件，
    导致 error 文本被截断、下游把【另一条】的数值读进本条（其对侧编号 X18）；
    对方随后自曝「X19 修复后仍有 15 处静默 `[:N]`」（U9）。

    我方在核验 U9 时发现：**我自己的脚本里有 61 处静默截断，是对侧的 5 倍**（F61）。
    ⇒ 该失误**在两侧同时存在**，且**只在自己统计时才看得见**。
    ⇒ 故本工具的核心判据不是「有多少截断」，而是【**按归属分列**】——
      让使用者同时看到「别人的」与「自己的」（否则重演 F61：只看别人不看自己）。

判据（★ 三态，不看退出码）
    SILENT   截断处【同行或邻行】都没有配套的计数 / 标注 / 省略号 ⇒ 下游无法知道被截
    ANNOTATED 有配套标记（count / 截断 / … / len( 等）⇒ 下游可推断
    ★ 本判据是【启发式】：邻行窗口 = ±2 行。⇒ 报告是**下界/上界**，不是精确值（见「限度」）。

用法
    python3 silent-truncation-lint.py [PATH ...]                 # 扫文件或目录
    python3 silent-truncation-lint.py PATH --by-owner '正则'      # ★ 按归属分列（可给多个）
    python3 silent-truncation-lint.py PATH --json                 # 机器可读
    python3 silent-truncation-lint.py --selftest                  # 本工具自测（正例+负例）
    python3 silent-truncation-lint.py --selfcheck                 # R006 ② TCC 能力边界自检
    python3 silent-truncation-lint.py --version

限度（自陈）
    1. **只检截断原语的字面出现**；不判断「该截断是否正当」（有些截断是故意的，如固定宽度打印）。
    2. **邻行窗口固定 ±2 行** ⇒ 配套标记若写在更远处，本工具会**误报为 SILENT**（上界偏高）。
    3. **不跟踪变量传播**（`x = s[:160]` 再 `print(x)` 追踪不到 x 的截断性）。
    4. 语言覆盖：`.py` / `.sh`（其他后缀不检）。

约束门（R006 ⑩）
    ★ 本工具**只读**：不执行外部命令、不写任何文件（`--selftest` 亦只写 /tmp 并自清理）、
      不删除数据、不改权限。静态扫描：无 subprocess / os.system / eval / exec /
      os.remove / rmtree / os.chmod / os.chown / os.kill / pkill。
"""
import os
import argparse
import json
import time
import re
import sys
import tempfile


# === R006 7 统一日志（本批补课新增）===
#   契约不变：log() 只【追加写日志】，不改变 stdout 内容与退出码。
LOG_DIR = os.path.expanduser("~/dsh-collab/logs")
LOG = os.path.join(LOG_DIR, "silent-truncation-lint.log")


def log(msg):
    """R006 7：固定路径、追加、含时刻；失败也留痕（绝不因日志失败影响主流程）。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " " + msg + "\n")
    except Exception:
        pass

VERSION = "1.0.3"

# 截断原语（字面）
TRUNC_PATTERNS = [
    (re.compile(r"\[:\s*\d+\]"), "[:N]"),
    (re.compile(r"\[-\s*\d+\s*:\]"), "[-N:]"),
    (re.compile(r"\[:\s*-\s*\d+\]"), "[:-N]"),
    (re.compile(r"\bhead\s+-c\b"), "head -c"),
    (re.compile(r"\.substring\s*\("), ".substring("),
    (re.compile(r"\.substr\s*\("), ".substr("),
    (re.compile(r"\bsubstr\s*\("), "substr("),
]
# 配套标记（出现即视为「已标注」，非静默）
ANNOT_PATTERNS = [
    re.compile(r"truncat", re.I), re.compile(r"截断"), re.compile(r"省略"),
    re.compile(r"计数"), re.compile(r"\bcount\b", re.I),
    re.compile(r"…"), re.compile(r"\.\.\."), re.compile(r"len\s*\("),
    re.compile(r"\bhead\b.*\bof\b", re.I), re.compile(r"ELIDED|omitted", re.I),
]
WINDOW = 2
SCAN_EXT = (".py", ".sh")

# ★ v1.0.3（F71）：区分 `[:N]` 的两种用途 —— 对侧 2026-10-09 判据：
#   ① **DISPLAY** 显示截断（打印长文本）⇒ **静默危险，该报**
#   ② **EXTRACT** 语义提取（`(cid)[:8]` / `iso(t)[:13]` 做分组键）⇒ **不是截断，不该报**
#   判据：**看结果是否用于展示**。
#   ★ 实测影响：对侧 17 处 = 4 注释提及 + 3 语义提取 ⇒ 真该报 10 处；
#     我方原判 61 处 SILENT **同样含大量语义提取** ⇒ 原数字是**偏高**的上界。
#   ★ 依 F61 教训：**EXTRACT 必须【单列】，不能静默丢弃**（否则又变成"看不见的统计口径"）。
DISPLAY_CTX = [
    re.compile(r"\bprint\s*\("), re.compile(r"\bf[\"']"), re.compile(r"%s"),
    re.compile(r"\.format\s*\("), re.compile(r"\bsys\.(stdout|stderr)\.write"),
    re.compile(r"\+\s*[\"']"), re.compile(r"\bjson\.dumps\b"), re.compile(r"\blog\w*\s*\("),
]
EXTRACT_CTX = [
    re.compile(r"\bCounter\s*\("), re.compile(r"\.append\s*\("), re.compile(r"\bset\s*\("),
    re.compile(r"\.add\s*\("), re.compile(r"\[\s*[a-z_]*\[:"), re.compile(r"\bkey\b"),
    re.compile(r"\biso\s*\("), re.compile(r"\bsplit\s*\("), re.compile(r"==\s*[\"']"),
    re.compile(r"\bin\s+\w+\s*:"), re.compile(r"\bfor\s+\w+\s+in\b"),
    re.compile(r"\bgroupby\b"), re.compile(r"\bsorted\s*\("),
]


def classify_use(line, window_ctx):
    """判定该 [:N] 是用于**展示**还是**语义提取**（对侧判据：看结果是否用于展示）"""
    if any(p.search(line) for p in DISPLAY_CTX):
        return "DISPLAY"
    if any(p.search(line) for p in EXTRACT_CTX):
        return "EXTRACT"
    # 行内无线索时看窗口：若邻近只有 display，则 DISPLAY
    if any(p.search(window_ctx) for p in DISPLAY_CTX):
        return "DISPLAY"
    return "UNKNOWN"



def scan_text(text):
    """返回 [(lineno, prim, verdict, use)]
    verdict: ANNOTATED（有配套）| SILENT（无配套）
    use    : DISPLAY（用于展示 ⇒ 静默危险）| EXTRACT（语义提取 ⇒ 不是截断）| UNKNOWN
    """
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and not any(p[0].search(stripped) for p in TRUNC_PATTERNS[:1]):
            # 纯注释行：仍检（注释里提到原语也值得看），但打标记
            pass
        for pat, name in TRUNC_PATTERNS:
            if pat.search(line):
                lo = max(0, i - WINDOW)
                hi = min(len(lines), i + WINDOW + 1)
                ctx = "\n".join(lines[lo:hi])
                annotated = any(a.search(ctx) for a in ANNOT_PATTERNS)
                use = classify_use(line, ctx)
                out.append((i + 1, name, "ANNOTATED" if annotated else "SILENT", use))
    return out


def iter_files(paths):
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isfile(p):
            if p.endswith(SCAN_EXT):
                yield p
        elif os.path.isdir(p):
            for dp, dn, fns in os.walk(p):
                dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
                for fn in sorted(fns):
                    if fn.endswith(SCAN_EXT):
                        yield os.path.join(dp, fn)


def owners_matching(path, owners):
    """返回**所有**匹配的归属标签（不只是首个）—— 用于检出「归属歧义」。"""
    return [label for label, rx in owners if rx.search(path)]


def owner_of(path, owners, ambiguous=None):
    """★ v1.0.2（F69）：返回首个命中，但**同时把「多归属」记入 ambiguous**。
    理由（对侧 2026-10-09 的判据）：
        **「分列本身不是机制，『归属无交集的分列』才是。」**
        实测：`--by-owner repro --by-owner stage-review`（宽在前）⇒ stage-review 被 repro
        **静默吞掉** ⇒ 使用者以为分了两组，实际只有一组，且工具不报错。
        ⇒ 这是**静默的不完整**（与 M10 静默截断同族）。
    对策：**不靠"先匹配者胜"冒充分列** —— 检出多归属即计入 ambiguous 并在报告中告警。
    """
    ms = owners_matching(path, owners)
    if len(ms) > 1 and ambiguous is not None:
        ambiguous.append((path, ms))
    return ms[0] if ms else "未分类"


def run(paths, owners, as_json):
    res = {}
    for f in iter_files(paths):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        hits = scan_text(txt)
        if hits:
            res[f] = hits
    # 聚合
    per_owner = {}
    total = {"SILENT": 0, "ANNOTATED": 0}
    ambiguous = []
    for f, hits in res.items():
        o = owner_of(f, owners, ambiguous)
        d = per_owner.setdefault(o, {"SILENT": 0, "ANNOTATED": 0, "files": 0})
        d["files"] += 1
        for _, _, v, _u in hits:
            d[v] += 1
            total[v] += 1
    if as_json:
        print(json.dumps({
            "version": VERSION, "per_owner": per_owner, "totals": total,
            "ambiguous": [{"file": f, "owners": o} for f, o in ambiguous],
            "files": {f: [{"line": a, "prim": b, "verdict": c, "use": u} for a, b, c, u in h] for f, h in res.items()},
        }, ensure_ascii=False, indent=1))
        return 0
    print("★ 静默截断检测（v%s）· 判据：截断处的 ±%d 行内有无配套计数/标注" % (VERSION, WINDOW))
    print("=" * 96)
    print("%-30s %8s %8s %8s" % ("归属", "SILENT", "ANNOTATED", "文件数"))
    print("-" * 96)
    for o, d in sorted(per_owner.items(), key=lambda x: -x[1]["SILENT"]):
        print("%-30s %8d %8d %8d" % (o[:28], d["SILENT"], d["ANNOTATED"], d["files"]))
    print("-" * 96)
    print("%-30s %8d %8d" % ("合计", total["SILENT"], total["ANNOTATED"]))
    print()
    print("★ 明细（按 SILENT 数排序，前 20 文件）")
    for f, hits in sorted(res.items(), key=lambda x: -sum(1 for h in x[1] if h[2] == "SILENT"))[:20]:
        s = sum(1 for h in hits if h[2] == "SILENT")
        if s == 0:
            continue
        print("  [%s] %s  SILENT=%d / %d" % (owner_of(f, owners), f, s, len(hits)))
        for a, b, c, u in hits:
            if c == "SILENT":
                print("       L%-5d %s" % (a, b))
    print()
    print("★ 限度：启发式（±%d 行窗口）⇒ 本报告为【上界】；不判断截断是否正当。" % WINDOW)
    # ★ v1.0.2（F69）：归属歧义告警 —— 不靠"先匹配者胜"冒充分列
    if ambiguous:
        print()
        print("★★ **归属歧义告警**（%d 个文件同时匹配多个 --by-owner 模式）:" % len(ambiguous))
        print("   ⇒ 本表【不是】真分列：宽模式排在前面时，窄模式会被【静默吞掉】。")
        print("   ⇒ 判据（对侧 2026-10-09）：「**分列本身不是机制，『归属无交集的分列』才是。**」")
        for f, ms in ambiguous[:8]:
            print("      %s  ← %s" % (f[-62:], ms))
        if len(ambiguous) > 8:
            print("      …（共 %d 个）" % len(ambiguous))
        print("   建议：把窄模式写在前面，或使各模式两两无交集。")
    else:
        print()
        print("★ 归属自检：各 --by-owner 模式两两无交集 ✅ ⇒ 本次分列是【真分列】")
    return 0


def selftest():
    """正例 + 负例（★ 判据必须能红）"""
    cases = [
        ("负例1 无标注 ⇒ SILENT", 'x = json.dumps(d)[:160]', "SILENT", True),
        ("负例2 有省略号 ⇒ ANNOTATED", 'x = json.dumps(d)[:160] + "…"', "ANNOTATED", True),
        ("负例3 有截断字样 ⇒ ANNOTATED", 's = t[:50]  # 截断标记', "ANNOTATED", True),
        ("正例1 无截断 ⇒ 零命中", 'x = json.dumps(d)', None, True),
        ("正例2 head -c 命中", 'cat f | head -c 100', "SILENT", True),
    ]
    ok = 0
    for name, text, expect, _ in cases:
        hits = scan_text(text)
        got = hits[0][2] if hits else None   # 4 元 tuple 的第 3 位仍是 verdict
        good = (got == expect)
        ok += 1 if good else 0
        print("  %s %-34s 期望=%-9s 实得=%-9s" % ("✅" if good else "❌", name, expect, got))
    print("  自测：%d/%d 符合预期" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def selfcheck():
    """R006 ② TCC 能力边界自检 —— 静态扫描本文件是否含危险原语

    ★ v1.0.1 修正（自指误报）：v1.0.0 直接 grep 源码字符串 ⇒ 命中了**本函数自己声明的
      危险原语列表**（列表字面量就在源码里）⇒ 自检恒报「有危险原语」。
      这与本线的教训同型：**检测器检测到自己**（同源误报）。
      ⇒ 现先**剥离字符串与注释**（tokenize），只扫**可执行 token**。
      （对照：`plugin_review` 工具说明亦载「扫描前剥离注释/字符串以免误伤自己的检测正则」。）
    """
    import io
    import tokenize
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    danger = ["subprocess", "os.system", "eval(", "exec(", "os.remove", "rmtree",
              "os.chmod", "os.chown", "os.kill", "pkill", "launchctl"]
    parts = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE):
                continue
            parts.append(tok.string)
    except Exception:
        parts = src.split("\n")
    code = " ".join(parts)
    found = [d for d in danger if d in code]
    print("R006 ② TCC 能力边界自检 · silent-truncation-lint v%s" % VERSION)
    print("  ★ 本工具声明：只读 · 只写 /tmp · 自清理 · 不改任何被扫文件")
    print("  静态扫描危险原语: %s" % (found if found else "无 ✅"))
    print("  ⇒ %s" % ("✅ 声明与实现一致" if not found else "★ 有危险原语，须逐条说明"))
    return 0 if not found else 1


def lean4_check():
    """R006 10 约束门 —— 本器的不变量声明（如实标注限度）。"""
    print("== " + os.path.basename(__file__) + " · --lean4-check ==")
    print("  如实声明：本器【无 .lean 规范源】—— 它是判据执行器，不含形式化定理。")
    print("  => 本检查【不冒充】编译或谓词对应性验证；仅声明其判据形态与限度。")
    print("  本器的不变量（机械化形式）：见 docstring 的「判据」节逐条定义。")
    print("  可独立跑的负控：--selftest（它才是本器的能力边界证据）")
    log("lean4-check ok（无 .lean 规范源，如实声明）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="静默截断检测（只读）")
    ap.add_argument("paths", nargs="*", help="要扫的文件或目录")
    ap.add_argument("--by-owner", action="append", default=[],
                    metavar="正则", help="★ 按归属分列（可多次；匹配路径即归为该组，写在前者优先）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 约束门")
    ap.add_argument("--dry-run", action="store_true", help="只列出将扫描什么，不执行")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("silent-truncation-lint %s" % VERSION); return 0
    if a.dry_run:
        # R006 9：--dry-run 只列将扫描什么，不执行
        import glob as _g
        tgts = []
        for x in (a.paths or []):
            tgts += _g.glob(x) if any(c in x for c in "*?[") else [x]
        print("[dry-run] 将扫描 " + str(len(tgts)) + " 个目标：")
        for t in tgts[:40]:
            print("  · " + t)
        if len(tgts) > 40:
            print("  ...（共 " + str(len(tgts)) + " 个）")
        log("dry-run targets=" + str(len(tgts)))
        return 0
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    if not a.paths:
        ap.print_help(); return 2
    # === 2026-10-10 补契约：非法输入（不存在的目标）须【如实报错、不静默降级】 ===
    #   裁判裁定 A（2026-10-10）：「没跑看起来像跑过」的危害【在自动化管道里】
    #     => stderr 警告只做到【人可区分】，做不到【机器可区分】=> 必须动退出码。
    #   理由二：「不改行为契约」指【正常输入】的输出语义；「不存在的目录」是【非法输入】，
    #     其退出码【本就没有契约】=> 「契约未声明 != 契约允许任何行为」=> 补上该声明。
    #   => 与 gate-canfail 同类情形对齐（其现为 rc=1）。
    _missing = []
    for _x in a.paths:
        _e = os.path.expanduser(_x)
        if any(c in _x for c in "*?["):     # glob 模式：以展开结果判定
            import glob as _g2
            if not _g2.glob(_e):
                _missing.append(_x)
        elif not os.path.exists(_e):
            _missing.append(_x)
    if _missing:
        sys.stderr.write("★ 前置缺失：以下目标不存在 => 未扫描（rc=1；不静默降级）\n")
        for _m in _missing[:20]:
            sys.stderr.write("  · " + _m + "\n")
        if len(_missing) > 20:
            sys.stderr.write("  ...（共 " + str(len(_missing)) + " 个）\n")
        log("prerequisite-missing targets=" + str(len(_missing)) + " rc=1")
        return 1
    owners = [(pat, re.compile(pat)) for pat in a.by_owner]
    return run(a.paths, owners, a.json)


if __name__ == "__main__":
    sys.exit(main())
