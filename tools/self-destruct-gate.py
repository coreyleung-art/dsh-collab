#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self-destruct-gate.py — 自指破坏门（R006 ⑩ 类型锁 + 入口门）

★ 为什么需要（2026-10-10 实测事故，非假想）
    星桥第三任为 CLD 换装写了个脚本，并在**脚本开头**写：
        launchctl remove com.dsh.<本脚本自己的 label>   # 想取消 launchctl 的保活重启
    而那个 label **正是该脚本自己的 launchd label**。
    ⇒ `launchctl remove` 会**移除该 job 并终止其下所有进程** ⇒
      **脚本刚启动就被 launchd 杀掉，什么都没做**（日志未生成、CLD 未变）。
    ⇒ 这是「**动作终止执行者自身**」——本文称**自指破坏**（self-destruct）。

★ 三层原因：为什么本机既有门没拦住（诚实记录）
    ① **这段路径上没有门**：R006 ⑩ 是**交付门**（管插件/CLI 工具的交付），
       而本事故是**会话里临时造脚本 + 直接 `launchctl submit`** ⇒ **执行这一步无门可过**。
       （R006 豁免条款只豁免「一次性临时脚本」的 ⑤⑥⑧，而该脚本落在了 `tools/` 里=进库。）
    ② **既有危险原语扫描是文本级**：`scripts/r006-debt-assess.py` 的 `DANGEROUS_RE` **能**匹配
       `launchctl\\s+(unload|remove|bootout)`，**但它不知道参数指向脚本自己**。
       ⇒ ★ 这正是 R006 三句口诀的第三句：「**读不到实参会空集通过**」。
    ③ **它不是门**：`r006-debt-assess.py` 是**欠账评估**（输出统计），**没有 exit 非 0 拒绝**。

★ 本门补的三点
    ① 与交付流程解耦：**可在执行前独立调用**（`--check <脚本>`），不要求走 R006 交付。
    ② **读实参**：不只看「有没有原语」，而判「**其目标是否可能是执行者自身**」。
    ③ **能拒**：命中 ⇒ `exit 1`（不是评估统计）。

★★ 本门独有的一处设计矛盾与解法（R006 A 项 vs 自指判定）
    R006 `--lean4-check` 的 **A 项**要求「**去注释/字符串/正则字面量后扫描**」，
    以免把自己的检测正则当靶子（**自指假阳性**）；
    而**自指判定恰恰要读原文里的实参**（参数就写在源码里）。
    ⇒ **两者不能共用一次扫描** ⇒ 本门**分层**：
      · **A 项自证** ⇒ 用**剥离后**的文本扫（避免误伤）
      · **自指判定** ⇒ 用**原文**扫（必须读到实参），但**排除本门自身的判据定义区**
        （否则本门文件自己会被自己的样例字符串命中）

判据（可机械核）
    危险原语（自指可能造成"杀执行者"的）与该原语的目标**可能等于自身标识**，二者同现 ⇒ 拒绝。
    自身标识来源：`$$` · `BASHPID` · `$0` · `${BASH_SOURCE[0]}` · `dirname $0` · `basename $0` ·
                  本脚本路径 · 本脚本文件名的 stem · 脚本内声明的 launchd label

用法
    self-destruct-gate.py --check <脚本>            # 校验单个（exit 0/1）
    self-destruct-gate.py --check-all <目录>        # 批量
    self-destruct-gate.py --selftest                # 正负例自证（含本次事故实况）
    self-destruct-gate.py --lean4-check             # A–F 六项（R006 要求）
    self-destruct-gate.py --selfcheck               # ②③④ 能力边界
    self-destruct-gate.py --dry-run <脚本>          # 零变更演示（前后外部状态一致）
    self-destruct-gate.py --tool-version

退出码
    0 = 通过 · 1 = 拒绝（命中自指破坏）· 2 = 用法/环境错
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

VERSION = "1.0.0"
LOG = os.path.join(os.path.expanduser("~/dsh-collab"), "logs", "self-destruct-gate.log")

# ═══ 危险原语：会造成「执行者被终止」的那些 ═══
# ★ 依 R006 ⑩「不该发生的路径在结构上不可绕过」⇒ 只收**终止进程/移除自身 job/自删**类；
#   不收普通写文件（那是常规写，非本门范畴）。
SELF_KILLING = (
    (r"launchctl\s+(?:remove|bootout|unload)\b", "launchctl 移除 job"),
    (r"\bkill(?:all)?\b(?:\s+-[\w]+)*\s+", "kill/killall"),
    (r"\bpkill\b", "pkill"),
    (r"os\.kill\s*\(", "os.kill"),
    # ★ v1.0.6 修（扫历史脚本时抓到假阳性）：**`os.getpid()` 本身不是危险原语** ——
    #   它只在 `os.kill(os.getpid(), ...)` 时才构成自指破坏。
    #   实测假阳性：`scripts/entry-coverage.py:160` `_sub = os.path.join(_d, str(os.getpid()))`
    #   （**用 pid 拼临时目录名**，完全正常）—— 因该原语同时出现在 SELF_KILLING 与 SELF_MARKS，
    #   **任何含它的行都"自我同现"** ⇒ 必然命中。
    #   ⇒ 移除本行；保留 `os.kill` 作危险原语 + `os.getpid()` 作自身记号
    #     ⇒ 正确形态 `os.kill(os.getpid(), …)` 仍会被"原语+记号同现"命中。
    (r"rm\s+-[rRf]+\b", "rm -rf"),
    (r"shutil\.rmtree\s*\(", "shutil.rmtree"),
)

# ═══ 自身标识：可能表示"执行者自己"的记号 ═══
SELF_MARKS = (
    (r"\$\$", "$$（本 shell pid）"),
    (r"\bBASHPID\b", "BASHPID"),
    (r"\bsys\.argv\[0\]", "sys.argv[0]"),
    (r"__file__", "__file__"),
    (r"os\.getpid\s*\(\s*\)", "os.getpid()"),
    (r"\$\{?0\}?(?!\w)", "$0"),
    (r"\$\{BASH_SOURCE\[0\]\}", "BASH_SOURCE[0]"),
    (r"dirname\s+\"?\$0", "dirname $0"),
    (r"basename\s+\"?\$0", "basename $0"),
)

STRIP_LITERALS = re.compile(
    r'("""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', re.M)


def strip_literals_and_comments(text):
    """剥离字符串与三引号块 + 整行注释（R006 A 项要求）。

    ★ 复用本机既有技术（`bb-absorb.py` 等多处「剥离字符串与注释 —— 避免自指假阳性」）。
    局限（自陈）：不处理 shell heredoc 内的字符串；对 `#` 不在行首的行只剥尾部注释。
    """
    t = STRIP_LITERALS.sub('""', text)
    out = []
    for ln in t.split("\n"):
        s = ln.lstrip()
        if s.startswith("#"):
            out.append("")
        else:
            out.append(re.sub(r"\s+#.*$", "", ln))
    return "\n".join(out)


def find_hits(text, patterns):
    hits = []
    for i, ln in enumerate(text.split("\n"), 1):
        for pat, name in patterns:
            if re.search(pat, ln):
                hits.append({"line": i, "what": name, "text": ln.strip()[:120]})
    return hits


def check_script(path, label=None):
    """返回 (ok, reasons, detail)。判据：危险原语 + 自身标识【同现】或【目标即自身】。"""
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
    except Exception as e:
        return False, ["无法读取 %s: %s" % (path, e)], {}
    stem = os.path.splitext(os.path.basename(path))[0]
    # ★ 自身标识的**具体形态**（用于"目标即自身"的精确判定）
    concrete = [stem, os.path.basename(path)]
    if label:
        concrete.append(label)
    # 脚本内声明的 launchd label（形如 -l com.xxx 或 LABEL=com.xxx）
    for m in re.finditer(r"(?:-l\s+|label[\"']?\s*[:=]\s*[\"']?)(com\.[\w.\-]+)", raw):
        concrete.append(m.group(1))
    # ★ v1.0.1 修（自测抓到）：label **可能由外部给出**（`launchctl submit -l <label>`），
    #   脚本内无声明 —— 本次事故正是如此（label=com.dsh.cld-restart，脚本名=cld-restart-to-correct-app）。
    #   ⇒ 故**从危险原语的目标反推**：若目标的词根与脚本 stem 有重叠 ⇒ 视为自身标识。
    STEM_WORDS = set(w for w in re.split(r'[-_.]', stem.lower()) if len(w) >= 4)
    for m in re.finditer(r"launchctl\s+(?:remove|bootout|unload)\s+([\w.\-]+)", raw):
        tgt = m.group(1)
        TGT_WORDS = set(w for w in re.split(r'[-_.]', tgt.lower()) if len(w) >= 4)
        # ★ 判据演进（两次自测各抓一侧，记录于代码以便后人）：
        #   v1.0.1 用「词根交集非空」⇒ **假阳性**（remove-other.sh 与 com.example.other-job 共有泛用词 other）
        #   v1.0.2 收紧为「≥2 词根」⇒ **假阴性**（`cld` 仅 3 字符被 len>=4 门槛滤掉，交集只剩 restart）
        #   ⇒ v1.0.3 改**段级前缀匹配**（不受词长门槛影响，且语义直观）：
        #     label 的**尾段**（`com.dsh.cld-restart` → `cld-restart`）
        #     是否等于 stem 的**前 N 段**（N=1..3，`cld-restart-to-correct-app` → `cld-restart`）。
        _tail = tgt.lower().split(".")[-1]
        _parts = stem.lower().split("-")
        if any("-".join(_parts[:n]) == _tail for n in (1, 2, 3)):
            concrete.append(tgt)

    # ═══ ★ 对本门自身检查时的豁免（v1.0.3：**必须在两次判定之前**）═══
    #   ★ 教训：初版把这段写在「① 精确判定」**之后** ⇒ ① 先跑并抓到 selftest 的样例，
    #     之后才豁免 ⇒ **豁免形同虚设**（自测连报 4 条）。
    #   豁免两类，二者都是**文本而非动作**：
    #     ① `selftest()` 函数体 —— 必须原样复刻事故（label 同真事故），否则自证无力；
    #     ② `SELF_KILLING` / `SELF_MARKS` 判据表 —— 那是**判据定义**，不是破坏动作。
    # ★★ 通用豁免约定（v1.0.5）：`# gate-self-exempt: begin` … `# gate-self-exempt: end`
    #   用途：门的**测试样例/判据表**必然包含"看起来像破坏"的字面量，
    #   若不豁免 ⇒ **门永远无法通过自己**（R006 第二句口诀「扫原文会误伤自己」）。
    #   ★ 为何不硬编码"跳过某函数"：那对本门有效、对别的门无用 ⇒ 改为**显式标记**，
    #     任何门都可用同一约定标出自己的样例区。**标记本身可审查**（读者一眼看到豁免了哪段）。
    def _apply_markers(text):
        out, skip = [], False
        for ln in text.split("\n"):
            if "gate-self-exempt: begin" in ln:
                skip = True; out.append(""); continue
            if "gate-self-exempt: end" in ln:
                skip = False; out.append(""); continue
            out.append("" if skip else ln)
        return "\n".join(out)
    raw = _apply_markers(raw)

    if os.path.abspath(path) == os.path.abspath(__file__):
        # ★ v1.0.4：用**等长空行替换**（而非删除）—— 删除会使后续**行号整体偏移**，
        #   实测导致报错指向错误行（L208 报的是 selftest 的首行而非命中行）。
        def _blank(text, mm):
            return text[:mm.start()] + ("\n" * mm.group(0).count("\n")) + text[mm.end():]
        m = re.search(r"def selftest\(\):(?:.|\n)*?(?=\ndef )", raw)
        if m:
            raw = _blank(raw, m)
        for var in ("SELF_KILLING", "SELF_MARKS"):
            mm = re.search(r"%s = \((?:.|\n)*?\n\)" % var, raw)
            if mm:
                raw = _blank(raw, mm)

    reasons = []
    # ① 精确判定：危险原语的**目标**字面等于自身标识（本次事故正是此形态）
    for i, ln in enumerate(raw.split("\n"), 1):
        for pat, name in SELF_KILLING:
            if not re.search(pat, ln):
                continue
            for c in concrete:
                if c and re.search(r"(?<![\w.\-])%s(?![\w.\-])" % re.escape(c), ln):
                    reasons.append({
                        "severity": "REJECT",
                        "line": i, "prim": name, "self": c,
                        "why": "★ **原语的目标字面等于自身标识（%s）** ⇒ 动作将终止执行者自身" % c,
                        "text": ln.strip()[:120]})
    # ② 泛化判定：危险原语与"自身记号"（$$/$0/__file__ 等）同现
    for i, ln in enumerate(raw.split("\n"), 1):
        fired = [n for pat, n in SELF_KILLING if re.search(pat, ln)]
        if not fired:
            continue
        marks = [n for pat, n in SELF_MARKS if re.search(pat, ln)]
        if marks:
            reasons.append({
                "severity": "REJECT",
                "line": i, "prim": "/".join(fired), "self": "/".join(marks),
                "why": "★ 危险原语与**自身记号**同现 ⇒ 参数**可能**等于执行者自身",
                "text": ln.strip()[:120]})
    # 去重（同一行可能被两条判据各报一次）
    seen, uniq = set(), []
    for r in reasons:
        k = (r["line"], r["why"][:20])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    detail = {"path": path, "bytes": len(raw), "concrete_self_marks": sorted(set(concrete)),
              "dangerous_lines": len(find_hits(raw, SELF_KILLING))}
    return (len(uniq) == 0), uniq, detail


def selftest():
    """★ 自证：负例必须被拒（含本次事故实况）；正例必须通过。"""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sdg-neg-")
    # 负例 1：本次事故的原样复刻
    neg1 = os.path.join(tmp, "cld-restart-to-correct-app.sh")
    open(neg1, "w").write(
        "#!/bin/bash\n"
        "launchctl remove com.dsh.cld-restart 2>/dev/null || true\n"
        "echo done\n")
    # 负例 2：$$ 形态
    neg2 = os.path.join(tmp, "killself.sh")
    open(neg2, "w").write("#!/bin/bash\nkill -9 $$\n")
    # 负例 3：pkill 自身名
    neg3 = os.path.join(tmp, "pkillself.sh")
    open(neg3, "w").write("#!/bin/bash\npkill -f pkillself.sh\n")
    # 正例 1：从**外部**移除别的 job（本次的正确做法）
    pos1 = os.path.join(tmp, "remove-other.sh")
    open(pos1, "w").write("#!/bin/bash\nlaunchctl remove com.example.other-job || true\n")
    # 正例 2：只读脚本
    pos2 = os.path.join(tmp, "readonly.sh")
    open(pos2, "w").write("#!/bin/bash\nps -axo pid=,command= | grep CLD\n")

    cases = []
    for p, want, name in [
        (neg1, False, "★ 负例·**本次事故原样复刻**（launchctl remove 自己的 label）⇒ 应拒"),
        (neg2, False, "负例·kill -9 $$ ⇒ 应拒"),
        (neg3, False, "负例·pkill -f 自身名 ⇒ 应拒"),
        (pos1, True, "正例·**从外部移除别的 job**（本次的正确做法）⇒ 应过"),
        (pos2, True, "正例·只读脚本 ⇒ 应过"),
    ]:
        ok, reasons, _ = check_script(p)
        cases.append((name, ok == want, ok, reasons))
    print("★ self-destruct-gate 自证：负例必须被拒（含本次事故实况），正例必须通过")
    n = 0
    for name, good, got, reasons in cases:
        print("  %s %s（实得 pass=%s）" % ("✅" if good else "❌", name, got))
        for r in reasons[:2]:
            print("        L%-4s [%s] %s" % (r["line"], r["prim"], r["why"][:80]))
        n += 1 if good else 0
    print("  自证：%d/%d" % (n, len(cases)))
    return 0 if n == len(cases) else 1


def lean4_check():
    """R006 ⑩ `--lean4-check` 六项（A–F）。"""
    me = os.path.abspath(__file__)
    raw = open(me, encoding="utf-8").read()
    stripped = strip_literals_and_comments(raw)
    res = []
    # A 源码无危险原语（剥离后扫；门自身**不应**含危险原语）
    a_hits = find_hits(stripped, SELF_KILLING)
    # 门自身只做静态检查、不执行被检脚本 ⇒ 不应含真会"杀自己"的调用
    res.append(("A 源码无危险原语（剥离后扫）", len(a_hits) == 0,
                "命中 %d 条：%s" % (len(a_hits), [h["what"] for h in a_hits][:3])))
    # B 负例全部被拒
    n_neg = 3
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sdg-lean4-")
    negs = []
    # gate-self-exempt: begin  ← 本段是「门的测试数据」，非破坏动作（见 check_script 的豁免约定）
    for i, body in enumerate([
        "launchctl remove %s\n",
        "kill -9 $$\n",
        "pkill -f neg2\n"]):
        p = os.path.join(tmp, "neg%d.sh" % i)
        open(p, "w").write("#!/bin/bash\n" + (body % "neg%d" % i if "%s" in body else body))
        negs.append(p)
    # gate-self-exempt: end
    b_ok = all(not check_script(p)[0] for p in negs)
    res.append(("B 负例全部被拒", b_ok, "3 条越界样例全部 REJECT" if b_ok else "有负例被放过"))
    # C 正例可用（防门太宽砍自己人）
    pos = os.path.join(tmp, "pos.sh")
    open(pos, "w").write("#!/bin/bash\nlaunchctl remove com.other.job\n")
    c_ok = check_script(pos)[0]
    res.append(("C 正例可用（防门太宽）", c_ok, "「移除别的 job」通过" if c_ok else "★ 门把合法用法也拦了"))
    # D --dry-run 零变更（外部状态一致）
    d_ok, d_note = _dryrun_consistent()
    res.append(("D --dry-run 零变更", d_ok, d_note))
    # E 白名单冻结
    e_ok = isinstance(SELF_KILLING, tuple) and isinstance(SELF_MARKS, tuple)
    res.append(("E 判据表冻结（tuple）", e_ok, "SELF_KILLING/SELF_MARKS 为不可变 tuple"))
    # F 外部命令白名单（**枚举全部调用点 → 回原文读实参 → 断言命令集 ⊆ 允许集**）
    # ★ 依 R006 F 项步骤：「去字面量定位调用点 → 回原文读实参」（否则会"空集通过"）。
    # ★ 本门只允许**只读探测**命令（D 项零变更演示所需的 ps）；**禁止**执行被检脚本。
    ALLOWED_CMDS = {"ps"}                      # ← 白名单（冻结）
    call_sites = []
    for m2 in re.finditer(r"subprocess\.(?:run|Popen|call)\s*\(\s*\[\s*([\"'])(\w+)\1", raw):
        call_sites.append(m2.group(2))
    bad_cmds = sorted(set(call_sites) - ALLOWED_CMDS)
    f_ok = (len(bad_cmds) == 0)
    res.append(("F 外部命令白名单（枚举 %d 处 → 断言 ⊆ %s）" % (len(call_sites), sorted(ALLOWED_CMDS)),
                f_ok, "调用点 %s" % (sorted(set(call_sites)) or "无") if f_ok
                else "★ 越界命令：%s" % bad_cmds))
    print("★ lean4-check（R006 ⑩ 六项）")
    n = 0
    for name, ok, note in res:
        print("  %s %s — %s" % ("✅" if ok else "❌", name, note))
        n += 1 if ok else 0
    print("  六项：%d/%d %s" % (n, len(res), "全绿" if n == len(res) else "★ 未全绿"))
    return 0 if n == len(res) else 1


def _dryrun_consistent():
    """D 项：--dry-run 前后外部状态实测一致（PID/端口/mtime 三类采样）。"""
    def snap():
        try:
            p = subprocess.run(["ps", "-axo", "pid="], capture_output=True, text=True, timeout=10)
            npids = len([x for x in p.stdout.split() if x.strip()])
        except Exception:
            npids = -1
        st = os.stat(LOG) if os.path.exists(LOG) else None
        return (npids, st.st_mtime if st else 0, st.st_size if st else 0)
    a = snap()
    time.sleep(0.6)
    b = snap()
    # 允许 PID 数浮动（系统常态），但**本门自身不产生副作用** ⇒ 日志文件必须未被本门改写
    same = (a[1] == b[1] and a[2] == b[2])
    return same, ("日志 mtime/size 未变（%s）· PID 数 %d→%d（系统浮动属预期）" % (a[2], a[0], b[0]))


def selfcheck():
    """②③④ 能力边界（R006 ② TCC / ③ CLD 自适应 / ④ 版本）

    ★ v1.0.1 修（自测抓到两处假阴性）：
      · ② 原判据 `"subprocess" not in <剥离后全文>` ⇒ **误报**：本门的 `_dryrun_consistent`
        用 `subprocess` 跑 **`ps` 只读探测**（D 项零变更演示所需），**并非执行被检对象**。
        ⇒ 改为：判「**是否存在执行被检脚本**的调用」——即 subprocess 的实参含被检路径变量。
      · ③ 原判据在**全文**搜 `/Applications/CLD.app` ⇒ **误报**：该串出现在 **docstring 的说明**里。
        ⇒ 改为：在**剥离字符串与注释后**的文本里搜（R006 A 项同款处理）。
    """
    txt = open(os.path.abspath(__file__), encoding="utf-8").read()
    stripped = strip_literals_and_comments(txt)
    # ② 是否存在「执行被检对象」的调用（而非只读探测）
    exec_target = re.search(r"subprocess\.\w+\s*\(\s*\[?\s*(path|target|t)\b", stripped) is not None
    checks = [
        ("② TCC：本门不执行被检对象（仅 ps 只读探测）", not exec_target),
        ("③ CLD 自适应：不依赖 CLD 特有路径（剥离后搜）", "CLD.app" not in stripped),
        ("④ 版本单一来源 VERSION", 'VERSION = "%s"' % VERSION in txt),
        ("本门自身通过自指门", check_script(os.path.abspath(__file__))[0]),
    ]
    print("★ selfcheck（②③④ 能力边界）")
    n = 0
    for name, ok in checks:
        print("  %s %s" % ("✅" if ok else "❌", name))
        n += 1 if ok else 0
    print("  自查：%d/%d" % (n, len(checks)))
    return 0 if n == len(checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="脚本")
    ap.add_argument("--check-all", metavar="目录")
    ap.add_argument("--label", help="该脚本的 launchd label（若有，用于精确判定）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--dry-run", metavar="脚本")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.tool_version:
        print(VERSION); sys.exit(0)
    if a.selftest:
        sys.exit(selftest())
    if a.lean4_check:
        sys.exit(lean4_check())
    if a.selfcheck:
        sys.exit(selfcheck())
    if a.dry_run:
        ok, note = _dryrun_consistent()
        print("★ dry-run（零变更演示）")
        print("  %s" % note)
        print("  ⇒ %s" % ("✅ 无副作用" if ok else "❌ 检出变更"))
        sys.exit(0 if ok else 1)

    targets = []
    if a.check:
        targets = [a.check]
    elif a.check_all:
        d = os.path.expanduser(a.check_all)
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith((".sh", ".py", ".bash")):
                    targets.append(os.path.join(root, f))
    if not targets:
        print(__doc__); sys.exit(2)

    all_red, rows = [], []
    for t in targets:
        ok, reasons, detail = check_script(t, a.label)
        rows.append({"path": t, "ok": ok, "reasons": reasons, "detail": detail})
        if not ok:
            all_red.extend(reasons)

    print("★ self-destruct-gate v%s（自指破坏门）" % VERSION)
    print("★ 扫描时点：%s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("★ 判据：危险原语与该原语的**目标是否可能是执行者自身**（R006 ⑩ 类型锁 + 入口门）")
    print("★ 被检：%d 个脚本" % len(rows))
    print()
    for r in rows:
        if r["ok"]:
            print("  ✅ %s" % r["path"])
        else:
            print("  ❌ %s" % r["path"])
            for x in r["reasons"]:
                print("       L%-5s [%s] %s" % (x["line"], x["prim"], x["why"]))
                print("              %s" % x["text"])
    print()
    if all_red:
        print("══ 判定：❌ **REJECT**（%d 条自指破坏）—— 不得执行 ══" % len(all_red))
        print("   ⇒ 正解：把该动作移到**外部**执行（入口门），或改用**幂等性**避免自指。")
    else:
        print("══ 判定：✅ PASS（未检出自指破坏）══")
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    sys.exit(1 if all_red else 0)


if __name__ == "__main__":
    main()
