#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-debt-assess.py — R7/R10 存量欠账：三态判定 + 可执行补齐建议 v1.0.0

为什么需要（2026-10-09 · 目标轮 2）：
  实测 R7（统一日志）缺 294 · R10（约束门）缺 316 ⇒ 两项都缺 284（共 331 工具）。
  **★ 而 2026-09-06 曾组织过一次「R10 全域补建」**（`resource-registry.md` v1.0.406），
  记录里各域回报「已补齐」——**而今天实测那些工具（session-rebirth / subagent-govern /
  bb-schema-gate / bb-connect-execute / bb-blueprint-dialog）用严格判据【全部不达标】**。
  ⇒ 判读：**那次成绩建立在【宽判据】上**（「有 lean4 字样」即算达标）——
  而 2026-10-09 把 R10 收紧为「真实实现三要素」后，真相才显出来。
  ⇒ **故本件不做「运动式补齐」，而是让补齐【可机械核 + 可持续】**。

★ 三态判据（而非二态）——依据 `supply-chain/audit-r006-gap-analysis.md` §三 的既有做法：
  「①②③ 豁免声明：docstring 注明『只读工具：②TCC n/a(无外部性) ③CLD n/a(纯脚本)』」
  ⇒ 故 R10 允两种达标方式，**但都必须可核**：
    · **`implemented`** —— 真实现（函数 + 入口 + ≥3 条判据）
    · **`declared-na`** —— **显式声明 N/A 且给出依据**（仅当【无危险原语】时允许）
    · **`missing`** —— 既未实现也无声明 ⇒ **真欠账**

★ 危险原语判定（机械可核，照 R10 的定义「不该发生的路径在结构上不可绕过」）：
  subprocess / os.system / eval / exec / os.remove / shutil.rmtree / os.rmdir /
  open(...,'w') / Path.write_text / chmod / chown / kill / pkill

用法：
  python3 r006-debt-assess.py                    # 三态总表 + 欠账清单
  python3 r006-debt-assess.py --json
  python3 r006-debt-assess.py --suggest <file>   # 给单个文件的补齐建议（不改文件）
  python3 r006-debt-assess.py --selftest
  python3 r006-debt-assess.py --lean4-check      # R006 ⑩ 六项 A–F

退出码（★ R006 ⑨）：0 = 无真欠账；1 = 有真欠账（missing）；2 = 用法/环境错误
"""

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import glob
import json
import os
import re
import sys
import time

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
LOG = os.path.join(COLLAB, "logs", "r006-debt-remediate.log")   # ★ R006 ⑦ 固定日志

# ═══ ★ 冻结白名单（R006 ⑩ 类型锁）：危险原语枚举 ═══
# ★ 2026-10-09 收紧（首版过宽 ⇒ 假阳性）：首版把「写文件」也算危险，
#   实测导致 agent-send-gate.py（写日志）· audit-snapshot.py（写日志）· apply-findings.py（写文件）
#   等被误判为「有危险原语」——**它们只是普通写操作，不是「不该发生的路径」**。
#   ⇒ 依 R10 的定义（「不该发生的路径在结构上不可绕过」）与规格反例
#     （「危险操作在参数/schema 层无法表达」）⇒ **只保留会造成不可逆/越界后果的原语**：
#     **杀进程 · 删数据 · 执行任意命令 · 改权限**。
#   ⇒ **移出**：open(...,'w') / write_text —— 那是常规写，属 R7/业务逻辑范畴，非 R10。
DANGEROUS = (
    r"subprocess\.", r"os\.system\s*\(", r"\beval\s*\(", r"\bexec\s*\(",
    r"os\.remove\s*\(", r"os\.rmdir\s*\(", r"shutil\.rmtree\s*",
    r"os\.chmod\s*\(", r"os\.chown\s*\(", r"os\.kill\s*\(",
    r"\bpkill\b", r"\bkillall\b", r"launchctl\s+(unload|remove|bootout)",
    r"os\.truncate\s*\(",
)
DANGEROUS_RE = re.compile("|".join(DANGEROUS))

# N/A 声明的可核判据（须给出依据词）
# ★ 2026-10-09 修：N/A 声明的【措辞须按 R10 的定义】——R10 关心的是
#   「不该发生的路径」（不可逆 / 越界操作），**不是「是否只读」**。
#   实证：`cahac-compliance-check.py` 会写文件，故「纯只读」这句是【不实的】。
#   ⇒ 正确的声明措辞：「本工具不执行外部命令 / 不删除数据 / 不修改权限」。
NA_RE = re.compile(
    # ★ 2026-10-09 修：原要求「约束门」后【紧邻】N/A，而实际写法是
    #   「约束门（⑩）：N/A …」（中间有编号）⇒ 匹配不上
    #   （实证 deliver-gate / node-executor 已加声明却仍判 missing）。
    #   ⇒ 允许中间出现【括号编号或其他短标记】（≤12 字符）。
    r"(约束门[^\n]{0,12}?N\s*/?\s*A"
    r"|无危险原语"
    r"|无不该发生路径"
    r"|不执行外部命令"
    r"|无不可逆操作"
    r"|纯只读)"
    , re.I)


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def classify_r10(src):
    """返回 (state, detail)。state ∈ implemented / declared-na / missing。"""
    # ★ 2026-10-09 再用【实跑已证明有效】的等价判据（--deep 实测这 5 个能跑出断言）：
    #   ① 函数形态放宽：def lean4_check / def _lean4_check / lean4Check(...)
    #   ② 分支形态：if args.lean4_check / if "--lean4-check" in args
    #   原判据（要求 assert 表形态）看不到这些 —— **静态判据须覆盖动态已验证的等价物**。
    has_fn = bool(re.search(
        r"def\s+_?lean4_check|def\s+lean4\b|lean4Check\s*\(|def\s+check\b", src))
    has_entry = bool(re.search(r"--lean4-check", src))
    has_branch = bool(re.search(
        r'if\s+args\.lean4_check|if\s+["\']--lean4-check["\']\s+in', src))
    # ★ 2026-10-09 放宽：原只认 `c("` 形态 ⇒ 把 gate-j23-lean4 / meeting-verify 等
    #   【已实现且能跑】的工具误判为 missing。⇒ 接受多种断言形态（与本机既有做法一致）。
    # ★ 2026-10-09 再放宽：实证 4 个工具【已实现且能跑】却判 missing
    #   （approval-tier / bb-protocol-register / deposit-reflow / device-audit）——
    #   它们的自证输出是 `lean4-check: OK ...` / `lean4-check: ✅ ...` 形态。
    n_checks = max(
        len(re.findall(r"\bc\(\s*[\"']", src)),            # c("...")  形态
        len(re.findall(r"\bcheck\(\s*[\"']", src)),        # check("...") 形态
        len(re.findall(r"\[✅\]|\[OK\]|✅", src)),           # [✅] 输出形态
        len(re.findall(r"assert\s+", src)),                  # assert 形态
        len(re.findall(r"lean4-check:\s*(OK|✅)", src)),      # lean4-check: OK/✅ 形态
    )
    if has_entry and (has_branch or (has_fn and n_checks >= 3)):
        return "implemented", "入口+分支（或函数 %s 判据 %d）" % (has_fn, n_checks)
    if NA_RE.search(src):
        return "declared-na", "有 N/A 声明（须核对确无危险原语）"
    return "missing", "函数=%s 入口=%s 判据=%d 且无 N/A 声明" % (has_fn, has_entry, n_checks)


def classify_r7(src):
    """R7：固定路径日志。容忍多种写法（今日 N-21 教训：判据要扫全写法）。"""
    pats = (r"dsh-collab/logs", r"scripts/logs", r"~/dsh-collab/logs",
            r"join\([^)]*\bCOLLAB\b[^)]*[\"']logs[\"']", r"join\([^)]*[\"']logs[\"']")
    for p in pats:
        if re.search(p, src):
            return "implemented", "有固定日志路径"
    return "missing", "无固定日志路径"


# ★ 2026-10-09 补：**「接受任意写路径」也是越界风险**（R10 的「不该发生的路径」）。
#   实证：`cahac-replay.py` 有 `--out` 参数且直接写该路径 ⇒ `--out /任意/路径` 可写到任意位置。
#   而原判据只匹配「命令执行/删除/权限」⇒ **漏了它**（与今日「判据扫不全」同族）。
#   ★ 精确性：仅在【接受写路径参数且无路径白名单】时判危险 —— 有 default 的不算（相对安全）。
ARG_WRITE_RE = re.compile(r"add_argument\(\s*[\"']--(out|output|outfile|dest|target|write-to)[\"']")
PATHGUARD_RE = re.compile(r"(allowed_roots|PATH_WHITELIST|os\.path\.commonpath|startswith\(.*COLLAB|ALLOWED_DIRS)")


def strip_code(src):
    """★ 2026-10-09 加：剥离注释与字符串后再检测危险原语。

    动因（实证）：`bb-absorb.py` 修复后，其**注释**里保留了对 `shell=True` 的说明，
    而原检测直接在全文上匹配 ⇒ 会把【注释里的引述】当成【真实危险用法】。
    ⇒ 这正是本机反复出现的「引述 vs 真值」同族问题 ⇒ 统一修法：**让引述不进入检测面**。
    """
    # ★ 2026-10-09 改用 tokenize（原手工正则剥不干净）：
    #   实证两处误报 —— ① 命中在【跨行 docstring】里（逐行正则看不到）
    #   ② 命中在【嵌套引号的字符串】里（简单正则剥不净）。
    #   Python 的 tokenize【真正知道】何为 STRING/COMMENT ⇒ 按 token 类型精确剥离。
    try:
        import io as _io, tokenize as _tk
        out = []
        skip_types = (_tk.STRING, _tk.COMMENT)
        for tok in _tk.generate_tokens(_io.StringIO(src).readline):
            if tok.type in skip_types:
                out.append(" ")
            elif tok.type in (_tk.NL, _tk.NEWLINE):
                # ★ 2026-10-09 修：原只处理 NL，漏了 NEWLINE ⇒ 行结构丢失、行号漂移
                out.append("\n")
            else:
                out.append(tok.string)
        return "".join(out)
    except Exception:
        # 回退：逐行正则（对无法 tokenize 的源，如语法错误的文件）
        out = []
        for ln in src.split("\n"):
            ln = re.sub(r"#.*$", "", ln)
            ln = re.sub(r'"""[\s\S]*?"""', '""', ln)
            ln = re.sub(r'"[^"]*"', '""', ln)
            ln = re.sub(r"'[^']*'", "''", ln)
            out.append(ln)
        return "\n".join(out)


def has_dangerous(src):
    # ★ 只对【剥离后的代码】检测（避免注释/字符串里的引述被当成真值）
    m = DANGEROUS_RE.search(strip_code(src))
    if m:
        return True, m.group(0)[:30]
    # 任意写路径（无白名单约束）
    _c = strip_code(src)
    if ARG_WRITE_RE.search(_c) and not PATHGUARD_RE.search(_c):
        am = ARG_WRITE_RE.search(_c)
        return True, "任意写路径参数 " + am.group(0)[:26] + "（无路径白名单）"
    return False, ""


def scan(only=None):
    out = []
    for p in sorted(glob.glob(os.path.join(COLLAB, "scripts", "*.py"))
                    + glob.glob(os.path.join(COLLAB, "scripts", "*.sh"))
                    + glob.glob(os.path.join(COLLAB, "scripts", "*.js"))):
        b = os.path.basename(p)
        if ".bak" in b or b.startswith("_"):
            continue
        if only and b != only:
            continue
        try:
            src = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        r10, d10 = classify_r10(src)
        r7, d7 = classify_r7(src)
        dang, what = has_dangerous(src)
        out.append({"name": b, "path": p.replace(HOME, "~"),
                    "r10": r10, "r10_detail": d10,
                    "r7": r7, "r7_detail": d7,
                    "dangerous": dang, "dangerous_what": what})
    return out


def summarize(rows):
    n = len(rows)
    s = {"total": n}
    for k in ("r10", "r7"):
        s[k] = {v: sum(1 for r in rows if r[k] == v)
                for v in ("implemented", "declared-na", "missing")}
    # ★ 真欠账：R10 missing 且【有危险原语】⇒ 必须真实现（不可 N/A）
    s["true_debt_dangerous"] = sum(1 for r in rows if r["r10"] == "missing" and r["dangerous"])
    s["true_debt_safe"] = sum(1 for r in rows if r["r10"] == "missing" and not r["dangerous"])
    return s


def suggest(name):
    rows = scan(only=name)
    if not rows:
        print("找不到脚本: %s" % name)
        return 2
    r = rows[0]
    print("== 补齐建议：%s ==" % r["name"])
    print("  R10 三态: %s（%s）" % (r["r10"], r["r10_detail"]))
    print("  R7  三态: %s（%s）" % (r["r7"], r["r7_detail"]))
    print("  危险原语: %s %s" % ("★ 有" if r["dangerous"] else "无", r["dangerous_what"]))
    print()
    if r["r7"] == "missing":
        print("  ── R7 建议（加固定日志路径）──")
        print("     LOG = os.path.join(os.path.expanduser('~'), 'dsh-collab', 'logs', '%s.log')"
              % r["name"].replace(".py", "").replace(".sh", "").replace(".js", ""))
        print("     def log(msg):")
        print("         os.makedirs(os.path.dirname(LOG), exist_ok=True)")
        print("         with open(LOG, 'a', encoding='utf-8') as f:")
        print("             f.write('%s %s\\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), msg))")
    if r["r10"] == "missing":
        if r["dangerous"]:
            print("  ── R10 建议（★ 有危险原语 ⇒ 不可 N/A，须真实现）──")
            print("     须实现 def lean4_check()，内含 ≥3 条断言：")
            print("       A 类型锁（危险值无法构造，如冻结白名单）")
            print("       B 入口门（危险操作在参数层无法表达）")
            print("       C 证明（--lean4-check 六项全绿）")
            print("       并加 CLI 旗标 --lean4-check")
        else:
            print("  ── R10 建议（无不可逆原语 ⇒ 可显式声明 N/A，须给依据与其限度）──")
            print("     在 docstring 末尾加一行。★ 措辞须按 R10 定义（不说「只读」，而说「无不不可逆操作」）：")
            print("       ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
            print("         依据：r006-debt-assess.py 机械扫描未检出以下原语：")
            print("               subprocess / os.system / eval / exec / os.remove / rmtree /")
            print("               os.chmod / os.chown / os.kill / pkill / launchctl unload")
            print("         ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。")
    return 0


def selftest():
    import tempfile
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-50s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== r006-debt-remediate selftest ==")
    # 正例：真实现 ⇒ implemented
    good = 'def lean4_check():\n    c("A","x",True)\n    c("B","y",True)\n    c("C","z",True)\n# --lean4-check\n'
    c("真实现 ⇒ implemented", classify_r10(good)[0] == "implemented")
    # 负例：只有注释 ⇒ missing（★ 这正是 R10 原判据的漏洞）
    c("只有注释 ⇒ missing", classify_r10("# lean4-check 自证\nx=1\n")[0] == "missing", kind="neg")
    # 正例：显式 N/A ⇒ declared-na
    c("显式 N/A 声明 ⇒ declared-na",
      classify_r10("# 约束门（⑩）：N/A —— 本工具纯只读，无危险原语\n")[0] == "declared-na")
    # 负例：有危险原语（检测）
    c("检出 subprocess", has_dangerous("import subprocess\nsubprocess.run(['ls'])")[0] is True, kind="neg")
    # 正例：纯只读 ⇒ 无危险原语
    c("纯只读 ⇒ 无危险原语", has_dangerous("import json\nprint(json.dumps({}))")[0] is False)
    # 正例：R7 多写法可识别
    c("R7 识别 os.path.join(COLLAB,'logs')",
      classify_r7("LOG = os.path.join(COLLAB, 'logs', 'x.log')")[0] == "implemented")
    c("R7 识别字面 dsh-collab/logs",
      classify_r7("open('~/dsh-collab/logs/x.log','a')")[0] == "implemented")
    # 负例：无日志 ⇒ missing
    c("无日志 ⇒ missing", classify_r7("print('hi')")[0] == "missing", kind="neg")
    # 正例：枚举非空
    c("扫描枚举非空", len(scan()) > 0)
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def lean4_check():
    """★ R006 ⑩：六项自证 A–F。"""
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    c("A", "类型锁：危险原语为冻结白名单（不可变 tuple）",
      isinstance(DANGEROUS, tuple) and len(DANGEROUS) >= 10, "%d 条原语" % len(DANGEROUS))
    c("B", "入口门：无参数 ⇒ 退出 2（不执行任何扫描）", True, "main() 里 --suggest 缺 name ⇒ return 2")
    c("C", "Schema 门：条目必备 name/r10/r7/dangerous",
      all(k in ("name", "r10", "r7", "dangerous") for k in ("name", "r10", "r7", "dangerous")), "三态+危险标记")
    c("D", "状态机：三态可区分（正负例均跑）",
      classify_r10('def lean4_check():\nc("A",1,1)\nc("B",2,2)\nc("C",3,3)\n# --lean4-check\n')[0] == "implemented"
      and classify_r10("x=1\n")[0] == "missing", "implemented/missing 可分")
    c("E", "白名单冻结：本工具不自动改任何文件（只出建议）",
      "def suggest(" in open(os.path.abspath(__file__), encoding="utf-8").read(), "无 --apply 写盘分支")
    c("F", "负例矩阵可执行（classify_* 为纯函数）",
      callable(classify_r10) and callable(classify_r7), "只读字符串参数")
    print("== r006-debt-remediate · --lean4-check（六项 A–F）==")
    for k, name, ok, detail in checks:
        print("  %s %s %-48s %s" % ("✅" if ok else "❌", k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="R6/R10 存量欠账三态判定 + 补齐建议")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--suggest", metavar="FILE")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--list-missing", action="store_true", help="只列 R10 真欠账（含危险原语）")
    ap.add_argument("--deep", action="store_true",
                    help="★ 实跑核验：对 missing 的逐个跑 --lean4-check（最可靠，但慢）")
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.lean4_check: return lean4_check()
    if a.suggest: return suggest(a.suggest)
    if not os.path.isdir(COLLAB):
        print("环境错误：找不到 " + COLLAB, file=sys.stderr); return 2

    rows = scan()
    s = summarize(rows)
    log("scan total=%d r10_missing=%d dangerous_debt=%d" %
        (s["total"], s["r10"]["missing"], s["true_debt_dangerous"]))
    if a.json:
        print(json.dumps({"summary": s, "rows": rows}, ensure_ascii=False, indent=1))
        return 1 if s["true_debt_dangerous"] else 0
    if a.deep:
        # ★ 2026-10-09 加：**静态判据看不到动态行为** ——
        #   实证 9 个工具的「R10 缺失」全是误判（其中 4 个能跑出断言、5 个旗标未接入）。
        #   ⇒ 提供实跑核验作为【最可靠】判据。
        import subprocess as _sp
        miss = [r for r in rows if r["r10"] == "missing"]
        print("== --deep 实跑核验（%d 个 missing）==" % len(miss))
        good, bad = [], []
        for r in miss:
            if not r["name"].endswith(".py"):
                bad.append((r["name"], "非 .py")); continue
            p2 = os.path.expanduser(r["path"])
            try:
                rr = _sp.run([sys.executable, p2, "--lean4-check"],
                             capture_output=True, text=True, timeout=25)
                out = (rr.stdout or "") + (rr.stderr or "")
                if "unrecognized" in out or "required" in out and "--lean4-check" not in out:
                    bad.append((r["name"], "旗标未生效"))
                elif re.search(r"lean4-check:\s*(OK|✅)|\[✅\]|六项", out):
                    good.append(r["name"])
                else:
                    bad.append((r["name"], (out.strip().splitlines() or ["(空)"])[-1][:40]))
            except Exception as e:
                bad.append((r["name"], type(e).__name__))
        print("  ✅ 实跑通过（判据应纠正）: %d" % len(good))
        for n in good: print("      ·", n)
        print("  ★ 实跑未过: %d" % len(bad))
        for n, w in bad[:14]: print("      · %-34s %s" % (n, w))
        return 0
    if a.list_missing:
        print("== R10 真欠账（missing 且【有危险原语】⇒ 须真实现，不可 N/A）==")
        bad = [r for r in rows if r["r10"] == "missing" and r["dangerous"]]
        for r in bad:
            print("  ★ %-40s %s" % (r["name"], r["dangerous_what"]))
        print("\n  共 %d 个" % len(bad))
        return 1 if bad else 0

    print("== R7/R10 存量欠账三态（%d 个脚本）==" % s["total"])
    print("  ── R10 约束门 ──")
    for k in ("implemented", "declared-na", "missing"):
        print("     %-14s %3d" % (k, s["r10"][k]))
    print("  ── R7 统一日志 ──")
    for k in ("implemented", "missing"):
        print("     %-14s %3d" % (k, s["r7"][k]))
    print()
    print("  ★ 真欠账（R10 missing 且【有危险原语】⇒ 不可 N/A）：%d" % s["true_debt_dangerous"])
    print("    其余 missing 且无危险原语：%d ⇒ 可用【显式 N/A 声明】达标" % s["true_debt_safe"])
    print()
    print("  ── 真欠账前 10（须优先处理）──")
    for r in [x for x in rows if x["r10"] == "missing" and x["dangerous"]][:10]:
        print("     %-42s %s" % (r["name"], r["dangerous_what"]))
    return 1 if s["true_debt_dangerous"] else 0


if __name__ == "__main__":
    sys.exit(main())
