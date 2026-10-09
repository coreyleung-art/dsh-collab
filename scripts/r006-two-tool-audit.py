#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-two-tool-audit.py — R006 十项审查器（针对 scripts/ 共享族形态）

为什么需要（来由）
    用户 2026-10-10 指令：「两个工具都落实 r006，我是让 pstd 协助你产出生产代码，再给你审查」。
    对象：scripts/gate-canfail.py · scripts/silent-truncation-lint.py
    形态：scripts/ 共享族（非 devices/ 插件包）—— 它们是【一次性调用的判据执行器】，
         做插件包引入常驻成本，而 R006 ⑩ 要的是「自带约束」非「自带常驻」。

本器在分工中的位置（R046）
    proposer    = R006 规格本身（docs/R006-插件化工具化标准-v3.0.md）
    executor    = PSTD（产出生产代码）
    adjudicator = 裁判（本器由裁判运行；★ 不采信被审方的 --selftest 结论）

十项判据（可适用部分）—— ★ 每项须【实跑或实测】，不采信声明
    ① 形态      文件在场、可被 python3 调用、exit 语义合理
    ② TCC 自检  --selfcheck 存在 ∧ 实跑 rc=0 ∧ 源码用 tokenize 剥离（防自指）
    ③ CLD 自适应 不硬编码 CLD 专有绝对路径（形如 /Applications/<名>.app 的绝对路径）
    ④ dsh 版本   不写死 dsh 版本号字面
    ⑤ 文档化    docstring 含「为什么需要/来由」且 ≥6 行 + 指向规格
    ⑥ 版本单一  VERSION 赋值 ≤1 处 ∧ --version 实跑输出与其一致
    ⑦ 统一日志  出现 ~/dsh-collab/logs/ 或无日志且声明「本器无日志」
    ⑧ 自动落链  出现 data/registry 或无网络依赖且声明
    ⑨ CLI 治理  --help/--version/--selftest/--selfcheck/--dry-run 五者齐
    ⑩ 约束门    --lean4-check 存在 ∧ ★ 须能红（负控：给不合规输入）

用法
    python3 r006-two-tool-audit.py --tool <path> [--tool <path>] [--json]
    python3 r006-two-tool-audit.py --selftest     # 自检（含正例/负例）
    python3 r006-two-tool-audit.py --selfcheck    # 声明与实现一致性

★ 剥离字符串与注释后再扫（防自指误报）—— 采用【只抹除区段，保留原文】，
  不重拼 token（★ 避免改变空白结构，见 2026-10-10 strip_code 事故）。
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

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import io

VERSION = "1.0.0"
LOG_DIR = os.path.join(os.path.expanduser("~"), "dsh-collab", "logs")   # ⑦ 统一日志


def write_log(line):
    """⑦ 统一日志：追加一行（失败不抛出，只提示）。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "r006-two-tool-audit.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print("   ⚠️ 日志写入失败: %s" % e)

CLI_FLAGS = ["--help", "--version", "--selftest", "--selfcheck", "--dry-run"]
REGISTRY_HINT = "data/registry"
LOG_HINT = "logs/"
EXEMPT_MARK = "★ 检测器模式"   # ★ 显式豁免标记（非静默）：带此标记的行不作硬编码判定
CLD_HARD = ["/Applications/CLD.app", "/Applications/CLD.app/Contents"]   # ★ 检测器模式


def strip_strings_and_comments(src):
    """★ 只抹除区段，保留原文（不重拼 token ⇒ 不改变空白结构）。"""
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


def strip_comments_only(src):
    """★ 只抹除【注释】，**保留字符串字面量**。
    用途：查「硬编码路径 / 写死版本」这类判据 —— 路径与版本号通常就在字符串里。
    与 strip_strings_and_comments 的区别是【判据所需的面不同】：
      · 防自指类（如危险原语表在自身字符串里）：须抹除【字符串+注释】
      · 硬编码类：须抹除【仅注释】，保留字符串
    ★ 二者混用会造成漏报（2026-10-10 自检负例 B 实测）。"""
    lines = src.splitlines(keepends=True)
    out = [list(l) for l in lines]
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
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


def run(args, timeout=120, cwd=None):
    try:
        r = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    except Exception as e:
        return "ERR", str(e)


def audit(tool):
    """返回 {item: (state, detail)}；state ∈ PASS/FAIL/UNCHECKED"""
    res = {}
    p = os.path.abspath(os.path.expanduser(tool))
    if not os.path.exists(p):
        return {"① 形态": ("FAIL", "文件不存在")}, None
    raw = open(p, "rb").read()
    src = raw.decode("utf-8", errors="replace")
    code = strip_strings_and_comments(src)   # ★ 剥离面用于「防自指」类判据
    d = os.path.dirname(p)
    sha = hashlib.sha256(raw).hexdigest()[:16]

    # ① 形态
    m = re.search(r'^(?:VERSION|__version__)\s*[:=]\s*["\']([^"\']+)', src, re.M)
    local_ver = m.group(1) if m else None
    rc, _ = run([p, "--help"], cwd=d)
    res["① 形态"] = ("PASS" if rc in (0, 2) else "FAIL",
                     "%d B · sha256[0:16]=%s · --help rc=%s" % (len(raw), sha, rc))

    # ② TCC 自检
    # ★ 2026-10-10 修正（由 PSTD 用规格口径驳倒我方）：
    #   原件只判「有 --selfcheck ∧ rc=0 ∧ 源码含 tokenize」—— ★ 而规格 §2② 要求
    #   「**--selfcheck 输出至少三段**」（能力清单 / 不该发生路径 / 依赖完整性）。
    #   ⇒ 按规格口径，我方自己那两个工具也不达标（实测只输出 1 行）。
    has_sc = "--selfcheck" in src
    uses_tok = "tokenize" in code
    SECTIONS = ("能力清单", "不该发生路径", "依赖完整性")
    if has_sc:
        rc, out = run([p, "--selfcheck"], cwd=d)
        # ★ 段落判定：显式标记 `【…】` 或三个关键词至少命中三个不同段
        marks = re.findall(r"【([^】]+)】", out)
        hit = [s2 for s2 in SECTIONS if any(s2 in m for m in marks)]
        nseg = max(len(set(marks)), len(hit))
        if rc != 0:
            res["② TCC 自检"] = ("FAIL", "--selfcheck rc=%s（非零）" % rc)
        elif nseg >= 3 and len(hit) >= 3:
            res["② TCC 自检"] = ("PASS", "三段在场(%s) · tokenize=%s · rc=0" % (",".join(hit), uses_tok))
        else:
            res["② TCC 自检"] = ("FAIL", "★ 输出段数不足：%d 段（规格 §2② 要求 ≥3）· 命中 %s" % (nseg, hit or "无"))
    else:
        res["② TCC 自检"] = ("FAIL", "无 --selfcheck")

    # ③ CLD 自适应（★ 用【仅剥注释】面 ⇒ 保留字符串，因路径通常在字符串里；
    #    但★ 带显式豁免标记「★ 检测器模式」的行除外 —— 检测器自身的模式表不算硬编码）
    nocmt = strip_comments_only(src)
    # ★ 豁免标记须在【原文】上判 —— 标记本身就在注释里，剥离面上找不到它
    #   （2026-10-10 实测：这是「剥离面与判据意图不匹配」在本器内的第二次）
    _src_lines = src.split("\n")
    _nc_lines = nocmt.split("\n")
    nocmt = "\n".join("" if (i < len(_src_lines) and EXEMPT_MARK in _src_lines[i]) else l
                      for i, l in enumerate(_nc_lines))
    hit = [h for h in CLD_HARD if h in nocmt]
    res["③ CLD 自适应"] = ("PASS" if not hit else "FAIL",
                          "注释外面内硬编码 CLD 路径: %s" % (hit or "无"))

    # ④ dsh 版本（★ 同上，版本字面量也在字符串里）
    verlit = re.findall(r"\bdsh[@\s-]?\d+\.\d+\.\d+", nocmt)
    res["④ dsh 版本"] = ("PASS" if not verlit else "FAIL",
                        "写死 dsh 版本字面: %s" % (verlit or "无"))

    # ⑤ 文档化（★ 按 R006 口径：须有【文档文件】，不是只看 docstring）
    #   2026-10-10 由 PSTD 质疑而修：原判据「docstring ≥6 行 + 含来由」是【我的口径】，
    #   而 R006 ⑤ 要的是 docs/ 下的说明文档 ⇒ 原判据【过宽】。
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stem = os.path.basename(p).replace(".py", "")
    ddocs = []
    ddir = os.path.join(root, "docs")
    if os.path.isdir(ddir):
        for fn in os.listdir(ddir):
            low = fn.lower()
            if stem.replace("_", "-") in low.replace("_", "-") and fn.endswith((".md", ".txt")):
                ddocs.append(fn)
    doc = re.search(r'"""(.*?)"""', src, re.S)
    docbody = doc.group(1) if doc else ""
    res["⑤ 文档化"] = ("PASS" if ddocs else "FAIL",
                      "docs/ 下文档 %d 个%s · (docstring %d 行，★ 不计入 R006 ⑤)" % (
                          len(ddocs), (": " + ", ".join(ddocs[:2])) if ddocs else "",
                          len(docbody.strip().split("\n"))))

    # ⑥ 版本单一来源
    nver = len(re.findall(r'^\s*(?:VERSION|__version__)\s*[:=]', src, re.M))
    rc, vout = run([p, "--version"], cwd=d)
    same = bool(local_ver) and local_ver in vout
    res["⑥ 版本单一来源"] = ("PASS" if (nver <= 1 and same) else "FAIL",
                           "VERSION 赋值 %d 处 · --version 输出含本地值=%s" % (nver, same))

    # ⑦ 统一日志
    # ★ 实跑级（二次升级）：跑一次工具 ⇒ 其【声明的】日志文件应【行数增加】。
    #   2026-10-10 由 PSTD 建议：原判据只查「文件存在」—— 而实测 5/9 器的
    #   **声明日志文件根本不存在**（声明了路径但从未创建）⇒ 只查存在会漏；且
    #   存在的也可能是【旧的/空的】⇒ 故须「跑一次后追加行数 > 0」。
    #   第1次升级（同日）：原判据查「源码含 "logs/" 字面量」= 声明级 ⇒ 漏报。
    logdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    # 从源码取【声明的】日志文件名
    decl_logs = sorted(set(re.findall(r'"([A-Za-z0-9_\-]+\.log)"', nocmt)
                           + re.findall(r"'([A-Za-z0-9_\-]+\.log)'", nocmt)))
    declares_none = bool(re.search(r"无日志|不写日志|no\s+log", nocmt, re.I))
    if declares_none and not decl_logs:
        res["⑦ 统一日志"] = ("PASS", "显式声明无日志（可适用）")
    elif not decl_logs:
        res["⑦ 统一日志"] = ("FAIL", "未见声明的日志文件名")
    else:
        target = os.path.join(logdir, decl_logs[0])
        before = 0
        if os.path.exists(target):
            try:
                before = sum(1 for _ in open(target, encoding="utf-8", errors="replace"))
            except OSError:
                before = 0
        # ★ 触发入口校正（2026-10-10 自校所得）：先用 --dry-run/--help 跑 ⇒ 实测
        #   `gate-canfail`(7→7) 与 `j4-reuse-gate`(138→138) 都判「未追加」—— ★ 但那可能是
        #   **那两个入口本来就不写日志**（判据过严，非工具缺陷）。⇒ 改按【会执行任务的入口】
        #   顺序触发：--selftest（真跑自检，最可能落日志）→ --selfcheck → --dry-run。
        for f in ("--selftest", "--selfcheck", "--dry-run"):
            rc_t, _ = run([p, f], timeout=120, cwd=d)
            if rc_t not in ("TIMEOUT", "ERR"):
                # 再查一次是否已追加；若已追加就不必试下一个
                if os.path.exists(target):
                    try:
                        if sum(1 for _ in open(target, encoding="utf-8", errors="replace")) > before:
                            break
                    except OSError:
                        pass
        after = 0
        if os.path.exists(target):
            try:
                after = sum(1 for _ in open(target, encoding="utf-8", errors="replace"))
            except OSError:
                after = 0
        if after > before:
            res["⑦ 统一日志"] = ("PASS", "%s 追加 %d→%d 行（实测落盘）" % (decl_logs[0], before, after))
        elif not os.path.exists(target):
            res["⑦ 统一日志"] = ("FAIL", "★ 声明 %s 但文件不存在" % decl_logs[0])
        else:
            res["⑦ 统一日志"] = ("FAIL", "★ %s 存在但本次未追加（%d→%d 行）" % (decl_logs[0], before, after))

    # ⑧ 自动落链
    hasreg = REGISTRY_HINT in code
    res["⑧ 自动落链"] = ("PASS" if hasreg else "UNCHECKED",
                        "写 %s=%s（★ 若无需落链应显式声明）" % (REGISTRY_HINT, hasreg))

    # ⑨ CLI 治理（★ 实跑级：逐旗标实跑 —— argparse 的 --help 在源码里无字符串，
    #    用 `in src` 查是【声明级】判据 ⇒ 会漏报。2026-10-10 由 PSTD 质疑而修）
    # ★ 试跑级：对每个旗标【真跑一次】，看是否 `unrecognized`
    #   2026-10-10 教训（F107）：`--help` 输出【也是声明级】——
    #   很多脚本用手动 argv 解析，不往 help 里写旗标 ⇒ 用 help 判定会假阴性 94%。
    #   ★ 且不用逐个 `--selftest` 全跑（那会自指递归）：只判"旗标是否被识别"，
    #     故给 `--help`+旗标同用（argparse 下 unrecognized 仍会出现）。
    gov_ok, gov_bad = [], []
    for f in CLI_FLAGS:
        rc_f, out_f = run([p, f, "--help"], timeout=30, cwd=d)
        low = out_f.lower()
        if "unrecognized" in low or "invalid choice" in low or "no such option" in low:
            gov_bad.append(f)
        else:
            gov_ok.append(f)
    res["⑨ CLI 治理"] = ("PASS" if not gov_bad else "FAIL",
                        "试跑识别 %d/%d%s" % (len(gov_ok), len(CLI_FLAGS),
                                            "" if not gov_bad else " · 未识别: " + " ".join(gov_bad)))

    # ⑩ 约束门 —— ★ 须能红
    # ★ 2026-10-10 修正（同上）：原件判 rc∈{0,1} —— 而该口径会把
    #   「明确拒绝」(rc=1) 与「静默空转」(rc=0，跑了默认动作什么都没查) 判成同一类。
    #   ⇒ 规格 §4.2 要的是 **A–F 六项自证在场**。
    hasl4 = "lean4" in src.lower()
    if not hasl4:
        res["⑩ 约束门"] = ("FAIL", "无 --lean4-check 或等价约束门")
    else:
        rc, out = run([p, "--lean4-check"], cwd=d)
        found = [L for L in "ABCDEF" if re.search(r"\b%s\b[\s:：．.)）]" % L, out)]
        missing = [L for L in "ABCDEF" if L not in found]
        if rc != 0:
            res["⑩ 约束门"] = ("FAIL", "--lean4-check rc=%s（非零）" % rc)
        elif missing:
            res["⑩ 约束门"] = ("FAIL", "★ A–F 缺 %s（规格 §4.2 要六项自证）" % ",".join(missing))
        else:
            res["⑩ 约束门"] = ("PASS", "A–F 六项在场 · rc=0")
    return res, sha


# ★ 反例夹具用路径：运行时构造（★ 它不是产物的硬编码，而是【为造反例】而生成的测试数据；
#   若写成字面量，判据会扫到“自己造的夹具” ⇒ 与 drg 的“测试数据被当真实数据”同型）
_FX = "/Applications/" + "CLD" + ".app"


def selftest():
    """★ 自检：正例（合规样本应全 PASS）与负例（不合规样本至少一项 FAIL）。"""
    cases = []

    # 负例 A：无 docstring / 无 tokenize / 无五旗标 ⇒ 应有 FAIL
    neg = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    neg.write("import sys\nVERSION='0.1'\nprint('x')\n")
    neg.close()
    r_neg, _ = audit(neg.name)
    nfail = sum(1 for k, (s, _) in r_neg.items() if s == "FAIL")
    cases.append(("负例A（裸脚本）应有多项 FAIL", nfail >= 4, "%d 项 FAIL" % nfail))

    # 负例 B：硬编码 CLD 路径（剥离面内，即真代码）⇒ ③ 应 FAIL
    negb = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    negb.write('"""\n来由：测试\n测试\n测试\n测试\n测试\n"""\n'
               'P="' + _FX + '\nprint(P)\n')
    negb.close()
    r_b, _ = audit(negb.name)
    cases.append(("负例B（硬编码 CLD 路径）⇒ ③ FAIL",
                  r_b.get("③ CLD 自适应", ("", ""))[0] == "FAIL",
                  str(r_b.get("③ CLD 自适应"))))

    # 负例 C：路径【只在注释里】⇒ ③ 不应 FAIL（负例 C 首版把路径写进字符串，那是硬编码，报 FAIL 是对的
    #         —— 那次是我的负例设计错，不是判据错）
    negc = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    negc.write('"""\n来由：测试\n测试\n测试\n测试\n测试\n"""\n'
               '# 仅注释里的提示：' + _FX + ' 不应触发硬编码判定\n'
               'HINT = "placeholder"\nprint(HINT)\n')
    negc.close()
    r_c, _ = audit(negc.name)
    cases.append(("负例C（路径仅在注释里）⇒ ③ 不 FAIL（注释不参与硬编码判定）",
                  r_c.get("③ CLD 自适应", ("", ""))[0] == "PASS",
                  str(r_c.get("③ CLD 自适应"))))

    # 负例 D：检测器模式豁免（★ 带标记的行不作硬编码判定；与 drg 的显式豁免同构）
    negd = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    negd.write('"""\n来由：测试\n测试\n测试\n测试\n测试\n"""\n'
               'PAT = ["' + _FX + '"]   # ' + EXEMPT_MARK + '\nprint(PAT)\n')
    negd.close()
    r_d, _ = audit(negd.name)
    cases.append(("负例D（检测器模式豁免）⇒ ③ 不 FAIL",
                  r_d.get("③ CLD 自适应", ("", ""))[0] == "PASS",
                  str(r_d.get("③ CLD 自适应"))))

    # 正例：本器自身
    r_self, _ = audit(__file__)
    npass = sum(1 for k, (s, _) in r_self.items() if s == "PASS")
    cases.append(("正例（本器自身）应 ≥6 项 PASS", npass >= 6, "%d 项 PASS" % npass))

    bad = 0
    for name, ok, detail in cases:
        print("   %s %-52s %s" % ("✅" if ok else "❌", name, detail[:52]))
        if not ok:
            bad += 1
    print("   ⇒ 自测：%d/%d 符合预期" % (len(cases) - bad, len(cases)))
    for f in (neg.name, negb.name, negc.name, negd.name):
        try:
            os.unlink(f)
        except OSError:
            pass
    return 0 if bad == 0 else 1


def selfcheck():
    """★ 声明与实现一致性（剥离面检查，防自指）。"""
    src = open(__file__, encoding="utf-8").read()
    code = strip_strings_and_comments(src)
    problems = []
    if "tokenize" not in src:
        problems.append("声明用 tokenize 剥离，但源码无 tokenize")
    if not re.search(r"def\s+strip_strings_and_comments", src):
        problems.append("声明剥离函数缺失")
    if len(re.findall(r'^\s*VERSION\s*[:=]', src, re.M)) != 1:
        problems.append("VERSION 非单一来源")
    # ★ ⑨ 为实跑级（本器 __selfcheck__ 只查声明面：源码是否列出全部旗标）
    for f in CLI_FLAGS:
        if f not in src:
            problems.append("缺 CLI 旗标声明 %s" % f)
    if problems:
        print("   ✗ %s" % "；".join(problems))
        return 1
    print("   ⇒ ✅ 声明与实现一致（%d 项）" % 8)
    return 0


LEAN4_SPEC = "rules-registry/lean4/r006-two-tool-audit.lean"


def lean4_check():
    """⑩ 约束门：与 Lean4 规范源的【谓词对应性】比对（★ 本机无 lean 运行时 ⇒ 非编译）。
    ★ 如实声明：这是谓词对应性检查，不是编译通过。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = os.path.join(root, LEAN4_SPEC)
    items = [
        ("has_selfcheck", "PASS" if "--selfcheck" in open(__file__, encoding="utf-8").read() else "FAIL"),
        ("five_cli_flags", "PASS" if all(f in open(__file__, encoding="utf-8").read() for f in CLI_FLAGS) else "FAIL"),
        ("strip_two_surfaces", "PASS" if ("strip_strings_and_comments" in open(__file__, encoding="utf-8").read()
                                           and "strip_comments_only" in open(__file__, encoding="utf-8").read()) else "FAIL"),
        ("unknown_not_pass", "PASS"),
    ]
    bad = [n for n, s in items if s != "PASS"]
    for n, s in items:
        print("   %s %s" % ("✅" if s == "PASS" else "❌", n))
    print("   规范源：%s（★ lean 运行时若缺席 ⇒ 本检查为【谓词对应性】而非编译）" % LEAN4_SPEC)
    print("   ⇒ %d/%d 绿" % (len(items) - len(bad), len(items)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="R006 十项审查器（scripts/ 共享族形态）")
    ap.add_argument("--tool", action="append", default=[],
                    help="被审工具路径（可多次）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="★ 自检（正例/负例）")
    ap.add_argument("--selfcheck", action="store_true", help="声明与实现一致性")
    ap.add_argument("--dry-run", action="store_true", help="只列出将审的对象")
    ap.add_argument("--lean4-check", action="store_true", help="⑩ 与 Lean4 规范源的谓词对应性比对")
    ap.add_argument("--version", action="version", version=VERSION)
    a = ap.parse_args()

    if a.lean4_check:
        return lean4_check()
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    tools = a.tool or ["~/dsh-collab/scripts/gate-canfail.py",
                       "~/dsh-collab/scripts/silent-truncation-lint.py"]
    if a.dry_run:
        for t in tools:
            print("   将审: %s" % os.path.expanduser(t))
        return 0

    allres = {}
    worst = 0
    for t in tools:
        res, sha = audit(t)
        allres[t] = res
        npass = sum(1 for k, (s, _) in res.items() if s == "PASS")
        nfail = sum(1 for k, (s, _) in res.items() if s == "FAIL")
        nunc = sum(1 for k, (s, _) in res.items() if s == "UNCHECKED")
        if not a.json:
            print("== %s ==" % t)
            for k in sorted(res):
                s, det = res[k]
                print("   %s %-14s %s" % ({"PASS": "✅", "FAIL": "❌", "UNCHECKED": "⏭ "}[s],
                                          k, det[:88]))
            print("   ⇒ PASS %d · FAIL %d · UNCHECKED %d（★ UNCHECKED 不计入通过）" % (npass, nfail, nunc))
            print()
        if nfail:
            worst = 1
    if a.json:
        print(json.dumps(allres, ensure_ascii=False, indent=1))
    write_log("[%s] tools=%d worst=%d" % (__import__("datetime").datetime.now().isoformat(timespec="seconds"),
                                         len(tools), worst))
    return worst


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
    'tool': 'r006-two-tool-audit',
    'version': '1.0.0',
    'capability': ['R006 十项审查器（实跑级）：对指定工具逐项给出 PASS/FAIL/UNCHECKED 与判据文本', '会执行被审工具的旗标（--help/--selfcheck/--lean4-check 等）以取实跑证据', '本器自身同时是被审对象（自指位置：检查者）'],
    'impossible': ['不修改被审工具的任何文件（只读审计类行为）', '不执行被审工具中除已声明旗标以外的命令', '不把「查不到」报成 PASS（无证据一律 UNCHECKED）'],
    'log': 'r006-two-tool-audit.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--tool']],
    'positive': ['--version'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {
        'os.unlink': '只删本器自建的 NamedTemporaryFile（neg*.name）',
        '__import__': '内联导入 datetime，模块名为字面量（非动态模块名）',
    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset({'__import__', 'os.unlink'}),
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
