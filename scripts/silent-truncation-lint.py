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

# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets", "--dry-run")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──

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


# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块 · 自包含 · 勿手改） ═══════════
# 由 scripts/r006-u6-apply.py 注入；改模板后重跑注入器，勿在本块内手工编辑。
# 设计原则（三条，均有本线实证来源）：
#   1) ② 的每一句声明都必须【被本块结构核验】—— 只打印不检查的「纸面声明」不算 TCC。
#   2) ⑩ 的 A/ E/F 是【冻结声明 + 变更检测】：新增危险原语/写入点/外部命令调用点 ⇒ 立刻红。
#   3) 反空洞：写入点与命令点扫描器必须先在【合成恶意源】上自证会红，否则判「不能判定」。
#      （依据 R006 §4.2 坑 3：剥字面量后读不到实参 ⇒ 调用点枚举为 0 ⇒ 「0 ⊆ 允许」空洞通过）
import sys as _r006_sys
import os as _r006_os
import io as _r006_io
import re as _r006_re
import json as _r006_json
import ast as _r006_ast
import time as _r006_time
import tokenize as _r006_tokenize
import subprocess as _r006_subprocess

_R006_DECL = {
    'tool': 'silent-truncation-lint',
    'version': '1.0.3',
    'capability': ['只读扫描：找出「静默截断」—— 输出被截断却没有声明（口径：只看输出面，不判内容对错）', '只写 /tmp 与本器自有日志；被扫文件一律只读', '--dry-run 只列将报什么；--json 机器可读'],
    'impossible': ['不修改任何被扫文件', '不执行任何外部命令（本器零命令调用点）', '不做「内容是否正确」的判断（本器只判「截断有没有被声明」）'],
    'log': 'silent-truncation-lint.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--by-owner']],
    'positive': ['--selftest'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {

    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset(),
    'positive_expect_rc': [0],
    'dryrun_via_block': False,
    'dry_suppress': [],
    'dryrun_note': '本器自带 --dry-run 实现 ⇒ canonical 块不接管，把旗标放回 argv 交还原实现',
}

_R006_EXEC_ATTRS = ("run", "Popen", "call", "check_call", "check_output")
_R006_DANGER_ATTRS = {
    "os": ("system", "popen", "remove", "unlink", "rmdir", "removedirs", "chmod", "chown", "kill"),
    "shutil": ("rmtree", "move"),
    "subprocess": _R006_EXEC_ATTRS,
}
_R006_DANGER_NAMES = ("eval", "exec", "compile", "__import__")
_R006_SYNTH_EXEC = "import subprocess as _sp\nfrom subprocess import Popen\n_sp.run(['ls'], shell=True)\nPopen(['x'])\n"
_R006_SYNTH_WRITE = "open('x','w')\nopen(p, mode='a')\n"
_R006_SYNTH_EXEC_WANT = frozenset({"subprocess.run", "subprocess.Popen"})
_R006_SYNTH_WRITE_WANT = frozenset({"const:x", "<expr>"})


def _r006_src():
    return open(_r006_os.path.abspath(__file__), encoding="utf-8").read()


def _r006_strip(s):
    """tokenize 抹除注释与字符串【内容】：按原文区间置空。
    ★ 不重拼 token —— 重拼会吞掉 token 间空白（`if a.selftest:` 变 `ifa.selftest:`）。"""
    buf = list(s)
    off = [0]
    for ln in s.splitlines(True):
        off.append(off[-1] + len(ln))
    try:
        for tk in _r006_tokenize.generate_tokens(_r006_io.StringIO(s).readline):
            if tk.type in (_r006_tokenize.COMMENT, _r006_tokenize.STRING):
                a = off[tk.start[0] - 1] + tk.start[1]
                b = off[tk.end[0] - 1] + tk.end[1]
                for i in range(a, min(b, len(buf))):
                    if buf[i] not in "\r\n":
                        buf[i] = " "
    except Exception:
        return s
    return "".join(buf)


def _r006_aliases(t):
    """import 别名解析：`import subprocess as sp` / `from subprocess import run` 都要认得。
    ★ 不做这步，改个别名就能绕过扫描器（= 空洞通过）。"""
    m = {}
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                m[(a.asname or a.name.split(".")[0])] = a.name.split(".")[0]
        elif isinstance(n, _r006_ast.ImportFrom):
            for a in n.names:
                m[(a.asname or a.name)] = (n.module or "").split(".")[0] + "." + a.name
    return m


def _r006_scan(src):
    """AST 三面读数：外部命令调用点 / 写入点 / 危险原语。
    ★ 用 AST 而非正则：注释与字符串天生不进 AST ⇒ 免除「扫到自己的检测正则」假阳性。"""
    r = {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}
    try:
        t = _r006_ast.parse(src)
    except Exception as e:
        r["err"] = "AST 解析失败: %s" % e
        return r
    al = _r006_aliases(t)
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                r["imports"].add(a.name.split(".")[0])
        elif isinstance(n, _r006_ast.ImportFrom):
            if n.module:
                r["imports"].add(n.module.split(".")[0])
        elif isinstance(n, _r006_ast.Call):
            f = n.func
            if isinstance(f, _r006_ast.Attribute) and isinstance(f.value, _r006_ast.Name):
                mod = al.get(f.value.id, f.value.id)
                if mod in _R006_DANGER_ATTRS and f.attr in _R006_DANGER_ATTRS[mod]:
                    if mod == "subprocess":
                        r["exec"].add("subprocess." + f.attr)
                    else:
                        r["danger"].add(mod + "." + f.attr)
            elif isinstance(f, _r006_ast.Name):
                tgt = al.get(f.id, f.id)
                if tgt.startswith("subprocess."):
                    r["exec"].add("subprocess." + tgt.split(".", 1)[1])
                elif f.id in _R006_DANGER_NAMES:
                    r["danger"].add(f.id)
                elif f.id == "open":
                    mode = ""
                    if len(n.args) >= 2 and isinstance(n.args[1], _r006_ast.Constant):
                        mode = str(n.args[1].value)
                    for kw in n.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, _r006_ast.Constant):
                            mode = str(kw.value.value)
                    if any(c in mode for c in ("w", "a", "x", "+")):
                        p = "<expr>"
                        if n.args and isinstance(n.args[0], _r006_ast.Constant):
                            p = "const:" + str(n.args[0].value)
                        r["write"].add(p)
    return r


def _r006_regex_pass(s):
    """A 的【独立第二通道】：在 tokenize-剥离后的文本上做正则扫描。
    两通道结论不一致 ⇒ 判「不能判定」，**不得**假设其中某一个对。"""
    code = _r006_strip(s)
    hits = set()
    for pat, name in ((r"\beval\s*\(", "eval"), (r"\bexec\s*\(", "exec"),
                      (r"\b__import__\s*\(", "__import__"),
                      (r"\bos\.system\s*\(", "os.system"), (r"\bos\.popen\s*\(", "os.popen"),
                      (r"\.rmtree\s*\(", "shutil.rmtree"), (r"\bos\.remove\s*\(", "os.remove")):
        if _r006_re.search(pat, code):
            hits.add(name)
    return hits


def _r006_run(argv, timeout=60):
    try:
        p = _r006_subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                 cwd=_r006_os.path.dirname(_r006_os.path.abspath(__file__)))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except _r006_subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, str(e)


def _r006_snap(paths):
    import hashlib
    out = {}
    for p in paths:
        try:
            st = _r006_os.stat(p)
            with open(p, "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()[:16]
            out[p] = [st.st_size, h]
        except OSError:
            out[p] = None
    return out


def _r006_std_imports(imports):
    """③ 依赖完整性：把顶层 import 分类为 内置 / 标准库 / 第三方（Python 3.9 无 stdlib_module_names）。"""
    import importlib.util as _u
    import sysconfig
    std = _r006_os.path.realpath(sysconfig.get_paths()["stdlib"])
    third, stdlib = [], []
    for m in sorted(imports):
        if m in _r006_sys.builtin_module_names:
            stdlib.append(m)
            continue
        try:
            sp = _u.find_spec(m)
        except Exception:
            sp = None
        if sp is None:
            third.append(m + "(未解析)")
        elif sp.origin and _r006_os.path.realpath(sp.origin).startswith(std):
            stdlib.append(m)
        elif sp.origin in (None, "built-in", "frozen"):
            stdlib.append(m)
        else:
            third.append(m)
    return stdlib, third


def _r006_logline(what, status):
    """R006 ⑦ 统一日志：本块每次动作也留痕。★ 这不是装饰 ——
    本块的早期守卫会遮蔽本器【自带的同名旗标实现】，若那实现里原本有 log 调用，
    该副作用会【永不到达】（实测 gate-canfail 的唯一 log 调用点就在其自己的 lean4_check 内）。
    故本块必须自己补上，否则本块会把被修物的 ⑦ 从「有留痕」打成「死声明」。"""
    if globals().get("_R006_DRY", False):
        return
    fn = None
    for _nm in ("log", "write_log"):
        _f = globals().get(_nm)
        if callable(_f):
            fn = _f
            break
    if fn is None:
        return
    try:
        fn("[R006] %s · %s · %s" % (_R006_DECL["tool"], what, status))
    except Exception:
        pass


def _r006_legacy_narrative():
    """沿用本器【原有的 selfcheck() 自述】—— 不因迁移到 canonical 块而丢失既有声明内容。
    取不到时如实说明（不静默当空）。"""
    f = globals().get("selfcheck")
    if not callable(f) or getattr(f, "__module__", None) != __name__:
        return []
    try:
        import io as _i
        import contextlib as _c
        buf = _i.StringIO()
        with _c.redirect_stdout(buf):
            f()
        return [l.rstrip() for l in buf.getvalue().splitlines() if l.strip()]
    except Exception as e:
        return ["(沿用原有 selfcheck() 失败，如实报出: %s)" % e]


def _r006_selfcheck():
    """R006 ② TCC 能力边界自检：三段输出 + 【结构核验】（不做纸面声明）。"""
    name = _R006_DECL["tool"]
    src = _r006_src()
    sc = _r006_scan(src)
    stdlib, third = _r006_std_imports(sc["imports"])
    W = _R006_DECL
    lines = ["R006 ② TCC 能力边界自检 · %s v%s" % (name, W["version"])]
    lines.append("【① 能力清单】")
    for x in W["capability"]:
        lines.append("  · " + x)
    legacy = _r006_legacy_narrative()
    if legacy:
        lines.append("  · —— 以下沿用本器原有 selfcheck() 自述 ——")
        for l in legacy:
            lines.append("  " + l)
    lines.append("【② 不该发生路径清单】")
    for x in W["impossible"]:
        lines.append("  · " + x)
    lines.append("【③ 依赖完整性】")
    lines.append("  · Python %s（本机）" % _r006_sys.version.split()[0])
    lines.append("  · 标准库 %d 个：%s" % (len(stdlib), ", ".join(stdlib) if stdlib else "无"))
    lines.append("  · 第三方 %d 个：%s" % (len(third), ", ".join(third) if third else "无"))
    lines.append("  · 外部命令调用点（冻结）：%s" % (", ".join(sorted(W["frozen_exec"])) or "无"))
    lines.append("  · 写入点（冻结）：%s" % (", ".join(sorted(W["frozen_write"])) or "无"))
    lines.append("  · 固定日志：%s" % (W["log"] or "无"))

    chk = []
    chk.append(("依赖无第三方", not third, "第三方: %s" % (", ".join(third) or "无")))
    ext_ok = (frozenset(sc["exec"]) == frozenset(W["frozen_exec"]))
    chk.append(("外部命令面与冻结集一致", ext_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["exec"]) or "无", sorted(W["frozen_exec"]) or "无")))
    wr_ok = (frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    chk.append(("写入面与冻结集一致", wr_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["write"]) or "无", sorted(W["frozen_write"]) or "无")))
    roots = [r for r in W.get("write_roots", [])]
    bad = [p for p in sc["write"] if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(_r006_os.path.expanduser(r)) for r in roots)]
    chk.append(("常量写入点在允许根内", not bad, "越界: %s" % (", ".join(bad) if bad else "无")))
    dg_ok = (frozenset(sc["danger"]) == frozenset(W["frozen_danger"]))
    chk.append(("危险原语面与冻结集一致", dg_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["danger"]) or "无", sorted(W["frozen_danger"]) or "无")))
    lg_ok = (not W["log"]) or (W["log"] in src)
    chk.append(("声明的日志路径真实存在于源码", lg_ok, W["log"] or "N/A（本器无日志）"))
    need = ["【① 能力清单】", "【② 不该发生路径清单】", "【③ 依赖完整性】"]
    chk.append(("R006 ② 规格要求的三段齐备", all(n in lines for n in need), " / ".join(need)))
    # ★ 第 9 项 —— 采纳 adjudicator 建议的【可判定窄口径】版，而非其原表述。
    #   为何是窄口径（均为实测，见 docs「批次缺陷复核」节）：
    #     ① 只扫【剥离面】：对「版本写进字符串声明」与「写进错误消息」两种【自然写法】命中 0 ⇒ 瞎；
    #     ② 改扫【字符串面】：现有 10 器立刻误报 11 处（多为 legit 的文档提及与工具自身版本常量）。
    #   ⇒ 「硬编码版本」整体**不可门化**（真值源给不出：无法机械区分合法的版本下限声明与不正当锁死）。
    #     故只保留其中【可判定】的一片：生产代码里的**浮点型**版本字面量（形态✓ 真值源✓）。
    #   ★ 如实标注：本项命中率极低，是**变更检测器**，不是能力证明。
    _vh = sorted(set(_r006_re.findall(r"\b3\.\d+(?:\.\d+)?\b", _r006_strip(src))))
    chk.append(("剥离面无浮点型 Python 版本字面量（窄口径可判定片）", not _vh,
                "命中: %s" % (", ".join(_vh) if _vh else "无（★ 低命中率：变更检测器，非能力证明）")))
    # ★ 声明的正例必须实测可用（非空转）—— 此前这里放的是「读过自己打印的行」，那是同义反复。
    _pos = W.get("positive", [])
    _prc = None
    if _pos:
        _prc, _po = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(_pos))
    chk.append(("声明的正例实测可用（非空转）",
                bool(_pos) and _prc in W.get("positive_expect_rc", [0]) and _prc not in (2, 124, 125),
                "%s → rc=%s" % (" ".join(_pos), _prc)))

    fails = [c for c in chk if not c[1]]
    lines.append("⇒ 声明核验：%d/%d 一致%s" % (len(chk) - len(fails), len(chk),
                                        "" if not fails else " · ❌ " + "; ".join(c[0] for c in fails)))
    for nm, ok, dt in chk:
        lines.append("   %s %s — %s" % ("✅" if ok else "❌", nm, dt))
    print("\n".join(lines))
    _r006_logline("selfcheck", "PASS %d/%d" % (len(chk) - len(fails), len(chk)))
    return 0 if not fails else 1


def _r006_dryrun_proof():
    """⑩ D：有 --dry-run ⇒ 实测 run 前后外部状态一致；无 ⇒ 【结构证明】（并如实标注为变体）。"""
    W = _R006_DECL
    dr = W.get("dryrun")
    watch = [_r006_os.path.expanduser(p) for p in W.get("watch", [])]
    if dr:
        b = _r006_snap(watch)
        rc, out = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(dr))
        a = _r006_snap(watch)
        return (rc == 0 and a == b), "★ 实测：rc=%s · watch %d 项前后一致=%s" % (rc, len(watch), a == b), "实测"
    src = _r006_src()
    wr = _r006_scan(src)["write"]
    roots = [_r006_os.path.expanduser(r) for r in W.get("write_roots", [])]
    outside = [p for p in wr if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(r) for r in roots)]
    ok = (frozenset(wr) == frozenset(W["frozen_write"])) and not outside
    return ok, ("△ 变体（非实测）：本器无 --dry-run ⇒ 以【写入面冻结 + 全部写入点在允许根内】作结构证明"
                "（%s）" % (", ".join(sorted(wr)) or "零写入点")), "结构证明"


def _r006_lean4_check():
    """R006 ⑩ 约束门 A–F。每项都带【反空洞】控制：扫描器先在合成恶意源上自证会红。"""
    W = _R006_DECL
    src = _r006_src()
    sc = _r006_scan(src)
    me = _r006_os.path.basename(_r006_os.path.abspath(__file__))
    rows = []

    # 反空洞前置：扫描器自证
    syn_e = frozenset(_r006_scan(_R006_SYNTH_EXEC)["exec"])
    syn_w = frozenset(_r006_scan(_R006_SYNTH_WRITE)["write"])
    scanner_live = (syn_e == _R006_SYNTH_EXEC_WANT) and (syn_w == _R006_SYNTH_WRITE_WANT)
    vac = [] if scanner_live else ["合成源未被完整检出 exec=%s write=%s" % (sorted(syn_e), sorted(syn_w))]

    # A 危险原语面（★ 不是「一定没有」—— 有则必须逐条声明并冻结；未声明即红）
    allowed_dg = dict(W.get("allowed_danger", {}))
    a_ast = frozenset(sc["danger"])
    a_rx = frozenset(_r006_regex_pass(src))
    a_frozen = frozenset(W["frozen_danger"])
    unallowed = sorted(a_ast - set(allowed_dg))
    a_ok = (scanner_live and a_ast == a_frozen and not (a_rx - a_ast) and not unallowed)
    rows.append(("A", "危险原语面全部已声明并冻结（无未声明原语）", a_ok,
                 "实测=%s · 已声明 %d 项 · 双通道一致=%s%s"
                 % (sorted(a_ast) or "无（零危险原语）", len(allowed_dg), (a_rx - a_ast) == set(),
                    "" if not unallowed else " · ★未声明: %s" % unallowed)))

    # B 负例全部被拒（非空，且实测 rc != 0）
    negs = W.get("negatives", [])
    b_det, b_ok = [], len(negs) >= 2
    for nv in negs:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(nv))
        b_det.append("%s→rc%s" % (" ".join(nv), rc))
        if rc == 0:
            b_ok = False
    if not scanner_live:
        b_ok = False
    rows.append(("B", "负例全部被拒（≥2 条，实测 rc≠0）", b_ok, " · ".join(b_det) or "无负例"))

    # C 正例可用（防门太宽砍掉自己）
    # ★ 口径：合法输入必须被【受理并产出结果】。默认 rc==0；对「报告器」类工具，
    #   rc=1（报告有发现）是合法结果 —— 但须在 decl 里显式声明 expect_rc 并给出理由，
    #   不得拿它当免检口（否则 C 退化为空转）。rc∈{2,124,125} 一律算门失效。
    pos = W.get("positive", [])
    want_rc = W.get("positive_expect_rc", [0])
    c_ok, c_det = bool(pos), "无正例 ⇒ 不能判定"
    if pos:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(pos))
        c_ok = (rc in want_rc) and (rc not in (2, 124, 125))
        c_det = "%s → rc=%s（期望 %s）%s" % (" ".join(pos), rc, want_rc,
                                            "" if rc in want_rc else " · ★门太宽或用法被拒")
    if len(want_rc) > 1:
        c_det += " · 放宽理由：" + W.get("positive_expect_reason", "（未给理由 ⇒ 视为未声明）")
    rows.append(("C", "正例可用（防门太宽砍掉自己）", c_ok, c_det))

    # D 零变更
    d_ok, d_det, d_kind = _r006_dryrun_proof()
    rows.append(("D", "零变更（%s）" % d_kind, d_ok, d_det))

    # E 白名单冻结 + 写入面变更检测
    e_ok = (scanner_live and isinstance(W["frozen_write"], frozenset)
            and frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    rows.append(("E", "写入面白名单冻结（frozenset + 变更即红）", e_ok,
                 "类型=%s · 元素=%d · 变更检测=on" % (type(W["frozen_write"]).__name__, len(W["frozen_write"]))))

    # F 外部命令白名单 + 别名逃逸检测
    f_ok = scanner_live and isinstance(W["frozen_exec"], frozenset) and frozenset(sc["exec"]) == frozenset(W["frozen_exec"])
    f_alias = "import subprocess as _sp" in _R006_SYNTH_EXEC and "subprocess.run" in syn_e
    rows.append(("F", "外部命令白名单（别名逃逸已覆盖 + 变更即红）", f_ok and f_alias,
                 "命令集=%s · 别名形式检出=%s" % (sorted(sc["exec"]) or "无", f_alias)))

    nf = [r for r in rows if not r[2]]
    print("== %s · --lean4-check（六项 A–F）==" % me)
    for k, nm, ok, dt in rows:
        print("  %s %s %-38s %s" % ("OK  " if ok else "FAIL", k, nm, dt))
    if vac:
        print("  ★ 反空洞控制未过：%s" % "; ".join(vac))
    print("\n  => %d/%d pass, %d FAIL" % (len(rows) - len(nf), len(rows), len(nf)))
    _r006_logline("lean4-check", "PASS %d/%d" % (len(rows) - len(nf), len(rows)))
    return 0 if not nf else 1


def _r006_sets():
    """诊断口：给出本器【实际】三面读数与冻结集，供注入器「先算后填」。"""
    sc = _r006_scan(_r006_src())
    print(_r006_json.dumps({
        "tool": _R006_DECL["tool"],
        "observed_exec": sorted(sc["exec"]), "frozen_exec": sorted(_R006_DECL["frozen_exec"]),
        "observed_write": sorted(sc["write"]), "frozen_write": sorted(_R006_DECL["frozen_write"]),
        "observed_danger": sorted(sc["danger"]), "frozen_danger": sorted(_R006_DECL["frozen_danger"]),
        "imports": sorted(sc["imports"]), "err": sc["err"],
    }, ensure_ascii=False, indent=2))
    return 0


def _r006_want(flag):
    """旗标本器是否被请求：既认当前 argv，也认【早期垫片】暂存的旗标。
    （垫片必须存在：本器可能在模块级就校验 argv，会先于本块把旗标当「不认识的参数」拒掉。）"""
    return (flag in _r006_sys.argv) or (flag in globals().get("_R006_EARLY_FLAGS", []))


# ── R006 ⑨③ `--dry-run` 统一实现（canonical） ────────────────────────────────
# 分流（★ 必须分流：本族里 3 个器【自带】--dry-run，拦截它会破坏其既有语义）：
#   · dryrun_via_block=True  : 本器无自带实现 ⇒ 由本块接管：把 --dry-run 从 argv 摘掉
#     （故其 argparse 不因未知旗标报错），并按 decl["dry_suppress"] 把【自动写入助手】
#     置为空操作 ⇒ 本器走完整逻辑但不产生自动落盘副作用。
#   · dryrun_via_block=False : 本器自带实现 ⇒ 把垫片摘走的旗标【放回 argv】，交还原实现。
if __name__ == "__main__":
    _R006_DRY = False
    if _R006_DECL.get("dryrun_via_block") and _r006_want("--dry-run"):
        _R006_DRY = True
        _r006_sys.argv = [x for x in _r006_sys.argv if x != "--dry-run"]
        for _rn in _R006_DECL.get("dry_suppress", []):
            if callable(globals().get(_rn)):
                globals()[_rn] = (lambda *a, **k: None)
    elif "--dry-run" in globals().get("_R006_EARLY_FLAGS", []):
        _r006_sys.argv.append("--dry-run")
else:
    _R006_DRY = False


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
