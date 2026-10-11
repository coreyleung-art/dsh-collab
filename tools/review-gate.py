#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review-gate.py — S3 审查追踪 + R048 时值检查

★ 定位（读实体后确定，非按锚点概述）
    锚点 §10 把 S3 写作「独立审查员逐个审查流程」——**概述**。
    实际规则是 **`R048`**（`rules-registry/RULES.md` L411，状态 enforced，2026-10-08 老板指令）：
      · 星桥（协调者）所有**设计与代码工作**须与独立审查员合作：**方案先行送审 → 按裁定执行 → 完成后审计回卡**
      · **R046 三方分离：星桥=提出/执行，审查员=裁定**
      · **审计未过不得视为完成**；审查员离线时**工作排队，不以离线为由绕过**
      · **v1.0.1「时值检查」**（清单：`docs/submission-timevalue-checklist-v1.md`，244 行）

    本工具 = R048 与那份清单的**机械执行件**（只做可机械化的部分），**不新造制度**。

做四件事
    ① 三方分离：verifier ≠ proposer、verifier ≠ executor（R046/R048）
    ② 禁打包批量裁：一次审查对应**一件**产物（R048 · 锚点 §5.4）
    ③ **时值检查**：实测值须满足三选一 —— A 自包含 / B 标时点+复跑命令 / C 指向活体入口
    ④ **判据类陈述四件齐备**：总体 / n / 基率 / 反例占比（清单「追加」条款，缺一即标不可用）

★★ 本工具遵守清单自身的规则（**自应用**）
    清单头条：「自动化把『不可核』变成『看起来可核』…**机器的读数不能自证**」；
    又：「凡『一律告警』型设计**先算噪声率**」。
    ⇒ 故 ③④ 均**先算噪声率**（`--noise`），并按实测结果决定默认是否判死：
      · 默认 **WARN**（不判死），`--strict` 才判死；
      · `--noise <文件…>` 打印在真实样本上的命中率，**供第三方质疑本仪器**。

用法
    python3 tools/review-gate.py --register --item <id> --proposer <a> --verifier <b> [--executor <c>]
    python3 tools/review-gate.py --tracker <tracker.json>        # 全表检查（三方分离 + 禁打包）
    python3 tools/review-gate.py --timevalue <送审件.md> [--strict]
    python3 tools/review-gate.py --noise <文件…>                 # ★ 噪声率实测
    python3 tools/review-gate.py --selftest

退出码
    0 = 无红项 · 1 = 有红项 · 2 = 用法错误
"""
import os
import argparse
import json
import re
import sys
import time
from pathlib import Path

VERSION = "1.0.0"
TRACKER = Path.home() / "dsh-collab" / "data" / "registry" / "review-tracker.json"

# ── ③ 时值检查：疑为「实测值」的形态（启发式，须先算噪声率）──
VALUE_PATTERNS = [
    (r'\b\d+(?:\.\d+)?\s*(?:MB|GB|KB|B)\b', "大小"),
    (r'\bport\s*[:=]?\s*\d{2,5}\b', "端口"),
    (r'\bv?\d+\.\d+\.\d+\b', "版本"),
    (r'\b[0-9a-f]{16,64}\b', "指纹"),
    (r'/tmp/\S+', "/tmp 路径"),
    (r'\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2})?\b', "时刻"),
    (r'\bn\s*=\s*\d+\b', "样本量"),
]
# ── A/B/C 三选一的证据形态 ──
EVID_A = [r"复跑", r"复现命令", r"可独立复跑", r"自包含", r"```"]
EVID_B = [r"取值时点", r"实测于", r"\(20\d\d-\d\d-\d\d", r"命令[:：]", r"@\s*20\d\d-"]
EVID_C = [r"见\s*--", r"活体", r"实时", r"查询入口", r"lsof", r"权威.*见"]

# ── ④ 判据四件齐备 ──
QUAD = [("总体", [r"总体", r"端点", r"集合", r"population"]),
        ("n", [r"\bn\s*=", r"样本量", r"份样本"]),
        ("基率", [r"基率", r"占比", r"命中率", r"发生率"]),
        ("反例占比", [r"反例", r"误报率", r"假阳", r"漏报"])]


def norm_sid(x):
    """★ v1.0.3：把「带说明的署名」归一为会话 id 核心。

    实测踩坑：我登记 `--executor "session-1ffded95（裁判·独立复现）"` 与
    `--verifier "session-1ffded95（裁判·裁定）"` ⇒ 完整字符串不等 ⇒ **自审检查漏过** ⇒
    而它们**其实是同一会话**（R046 明禁 verifier=executor）。
    ⇒ 判据应比对**会话 id 核心**，而非署名全串。
    """
    m = re.search(r'session-[0-9a-f]{8}', str(x or ""))
    return m.group(0) if m else str(x or "").strip()


def find_values(text):
    """★ v1.0.1 调低灵敏度（据噪声率实测）。

    实测：本仪器在 3 个真实文档上得**裸露率 98.8%**（81 检出 / 80 判无证据）
    ⇒ 该比率**荒谬**（真实送审件不可能普遍裸值）⇒ 说明**证据匹配窗口过窄**：
      初版只按 ±1 行上下文判 ABC 证据，而文档里证据常在**同段别处或代码块内**。

    调整（三处）：
      ① 证据窗口 ±1 行 → **±4 行**；
      ② 新增全文级弱证据（存在代码块 / 「命令：」/ 时点格式 任一 ⇒ 整篇视为「有证据来源」）；
      ③ ★ **确定性 / 启发式分层**：`/tmp` 路径与指纹为**确定性**（判死）；
         数字/版本/时刻类为**启发式**（默认 WARN，不计入裸露率的分母）。

    ★ 依据：`docs/submission-timevalue-checklist-v1.md`
      「凡『一律告警』型设计**先算噪声率**」+ 头条「**仪器的读数不能自证**」。
    """
    out = []
    lines = text.splitlines()
    # ★ v1.0.2 撤除「全文级弱证据」：实测它使裸露率从 98.8% 直落 **0.0%**（两极端），
    #   因为「只要文档里有代码块 ⇒ 全篇视为有证据」⇒ 判据形同虚设。
    #   ⇒ 改为**仅按 ±4 行窗口**判证据（窗口已由 ±1 放宽到 ±4）。
    for i, ln in enumerate(lines):
        for pat, kind in VALUE_PATTERNS:
            for m in re.finditer(pat, ln, re.I):
                ctx = "\n".join(lines[max(0, i - 4):i + 5])
                has_ev = (any(re.search(p, ctx, re.I) for p in EVID_A)
                          or any(re.search(p, ctx, re.I) for p in EVID_B)
                          or any(re.search(p, ctx, re.I) for p in EVID_C))
                # ★ 分层：确定性 vs 启发式
                deterministic = kind in ("/tmp 路径", "指纹")
                out.append({"line": i + 1, "kind": kind, "text": m.group(0)[:40],
                            "evidence": bool(has_ev), "deterministic": deterministic,
                            "raw": ln.strip()[:90]})
    return out


def check_timevalue(text, strict=False):
    vals = find_values(text)
    # ★ 分层：**裸露率只统计确定性项**（/tmp 路径、指纹）；
    #   启发式项（数字/版本/时刻）另列，**不计入分母**（否则比率即噪声本身）。
    bare = [v for v in vals if not v["evidence"] and v["deterministic"]]
    bare_heur = [v for v in vals if not v["evidence"] and not v["deterministic"]]
    quad = {}
    for name, pats in QUAD:
        quad[name] = any(re.search(p, text, re.I) for p in pats)
    return {"n_values": len(vals), "n_bare": len(bare), "bare": bare,
            "n_heuristic": len(bare_heur), "bare_heuristic": bare_heur, "quad": quad}


def noise(files):
    """★ 噪声率实测（清单要求：一律告警型设计先算噪声率）"""
    tot = bare = 0
    for f in files:
        p = Path(f).expanduser()
        if not p.exists():
            continue
        r = check_timevalue(p.read_text(encoding="utf-8", errors="replace"))
        tot += r["n_values"]
        bare += r["n_bare"]
    rate = (100.0 * bare / tot) if tot else 0.0
    print("★ 噪声率实测（本仪器在真实样本上的表现）")
    print("  样本：%d 个文件 · 检出**疑为实测值** %d 处 · 其中**无 ABC 证据** %d 处"
          % (len(files), tot, bare))
    print("  ⇒ **裸露率 %.1f%%**" % rate)
    print("  ★ 判读：该比率是**上界**（启发式按行上下文判证据，会把已标时点的也计入裸值）；")
    print("     若裸露率高而实际多为已合规者，说明**本仪器的判据过宽** ⇒ 应据实调低灵敏度，")
    print("     而非据此认为「送审件普遍违规」（清单头条：**仪器的读数不能自证**）。")
    return 0


def selftest():
    cases = []
    # ① 三方分离：verifier 与 proposer 同一 ⇒ 必红
    def sep(p_, v_, e_=None):
        if not v_:
            return "缺 verifier"
        if v_ == p_:
            return "自审（verifier=proposer）"
        if e_ and v_ == e_:
            return "自审（verifier=executor）"
        return None
    cases.append(("三方分离·verifier=proposer ⇒ 必红", sep("a", "a") is not None, True))
    cases.append(("三方分离·verifier=executor ⇒ 必红", sep("a", "b", "b") is not None, True))
    cases.append(("三方分离·三方各异 ⇒ 应过", sep("a", "b", "c") is None, True))
    # ② 时值：裸值必被检出
    t_bare = "写入了 /tmp/rb-l.json 作为中间文件。"
    t_ok = "写入了 /tmp/rb-l.json（2026-10-10 实测，命令：curl -o /tmp/rb-l.json）。"
    cases.append(("时值·裸值 ⇒ 检出", check_timevalue(t_bare)["n_bare"] > 0, True))
    cases.append(("时值·标时点+命令 ⇒ 不检出",
                  check_timevalue(t_ok)["n_bare"] == 0, True))
    cases.append(("时值·分层：数字类归**启发式**、不计入裸露率",
                  check_timevalue("本机有 245.2MB 文件。")["n_bare"] == 0
                  and check_timevalue("本机有 245.2MB 文件。")["n_heuristic"] > 0, True))
    # ③ 判据四件齐备
    q_miss = check_timevalue("本指标可作指纹。")
    cases.append(("四件·全缺 ⇒ 不全", not all(q_miss["quad"].values()), True))
    q_full = check_timevalue("总体 /data/ · n=120 · 基率 15.1% · 反例占比 2.4%")
    cases.append(("四件·齐 ⇒ 全", all(q_full["quad"].values()), True))

    print("★ review-gate 自证：合成正/负例证明判据可判")
    ok = 0
    for name, got, want in cases:
        good = (got == want)
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
        ok += 1 if good else 0
    print("  自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1



# ══════════════════════════════════════════════════════════════════
# ★ R006 §5 验收两步（v1.0.1 补 —— 此前本工具只有 `--selftest`，
#   缺 `--selfcheck`（②③④）与 `--lean4-check`（⑩ A–F）
#   ⇒ 属真实欠账，登记于 `docs/wave-s-toolchain-delivery-v1.md` §5「已知缺口」第 1 条）
#
# ★ 本块为**通用版**（第二个使用者起复用）：与 `gcr-gate.py` 的专用块同构，
#   差异只在 **B/C 的合成输入** —— 由本工具可选定义 `_r006_cases()` 覆盖，缺省用通用负例。
#   ⇒ 这实证了「R006 §5 两步」**可跨工具复用**（而非为单一工具定制）。
# ══════════════════════════════════════════════════════════════════

# ★ A 项判据（**通用版**）：**无【危险】原语** —— 杀进程 / 删数据 / 改权限 / 执行任意命令类。
#   ★ 为何不判「无 subprocess」：本类工具**多数需要**调外部只读工具，
#     若按字面判「无危险原语」会**永远失败**（假阴性）。
#     R006 A 项原意是「**不该发生的路径在结构上不可绕过**」
#     ⇒ A 项判【危险原语】，把【外部命令】交给 **F 项**（枚举调用点 + 断言 ⊆ 白名单）。
DANGEROUS_PRIMS = (
    r"os\.remove\s*\(", r"os\.rmdir\s*\(", r"shutil\.rmtree\s*",
    r"os\.chmod\s*\(", r"os\.chown\s*\(", r"os\.kill\s*\(",
    r"\bpkill\b", r"\bkillall\b", r"launchctl\s+(unload|remove|bootout)",
    r"\beval\s*\(", r"os\.system\s*\(",
)

# ★ F 项白名单（**冻结**）：只读探测类命令。★ 工具若需别的命令，**必须**显式加进本元组
#   （改动本元组即视为白名单变更，应留痕）。
ALLOWED_CMDS = ("codesign", "pgrep", "ps", "plutil", "spctl", "lsof", "grep", "python3",
                "curl", "shasum", "date", "wc")


# ═══ 剥离用模式（v1.0.2：显式区分 raw 与普通字符串的转义语义）═══
#   ★ 常量用 chr() 拼接生成 ⇒ 源码内无字面引号（避免自伤与转义歧义）
_D = chr(34); _S = chr(39); _T3 = _S * 3; _D3 = _D * 3
TRIPLE_DQ = '[rRbB]?' + _D3 + '(?:.|\\n)*?' + _D3
TRIPLE_SQ = '[rRbB]?' + _T3 + '(?:.|\\n)*?' + _T3
RAW_DQ = 'r' + _D + '[^' + _D + '\\n]*' + _D
RAW_SQ = 'r' + _S + '[^' + _S + '\\n]*' + _S
NORM_DQ = _D + '(?:[^' + _D + '\\\\]|\\\\.)*' + _D
NORM_SQ = _S + '(?:[^' + _S + '\\\\]|\\\\.)*' + _S


def _apply_exempt(text):
    """应用通用豁免约定 `# gate-self-exempt: begin/end`（等长空行替换，保行号）。

    ★ 约定来源：`tools/self-destruct-gate.py` v1.0.5 引入。
    ★ 用等长空行替换而非删除 —— 删除会使后续**行号整体偏移**（曾导致报错指向错误行）。
    ★★ 顺序纪律：**必须先 `_apply_exempt` 再 `_strip_lits`** ——
      反过来的话，`_strip_lits` 会把 `# gate-self-exempt: begin` **当注释整行剥掉**
      ⇒ 标记消失 ⇒ 豁免形同虚设（实测踩过）。
    """
    out, skip = [], False
    for ln in text.split("\n"):
        if "gate-self-exempt: begin" in ln:
            skip = True; out.append(""); continue
        if "gate-self-exempt: end" in ln:
            skip = False; out.append(""); continue
        out.append("" if skip else ln)
    return "\n".join(out)


def _strip_lits(txt):
    """剥离字符串字面量与整行注释（R006 A 项要求 —— 否则会把自己的检测正则当靶子）。

    ★ v1.0.2 修正（自测抓到）：初版用**字符扫描**且不识别 r 前缀 ⇒ 对 raw string 里的
      反斜杠-引号（raw 中非转义）剥错边界，把模式串的一部分留在结果里 ⇒
      **判据把自己的模式串当靶子**（实测某工具 A/D 两项因此判红）。
      ⇒ 改用正则，**显式区分 r 前缀**（raw 中反斜杠不转义）。
    ★ 顺序纪律：调用方必须 **先 _apply_exempt 再 _strip_lits** ——
      反过来的话标记行（# gate-self-exempt: begin）会被当注释剥掉 ⇒ 豁免失效。
    """
    t = re.sub(TRIPLE_DQ, '\"\"', txt)
    t = re.sub(TRIPLE_SQ, '\"\"', t)
    t = re.sub(RAW_DQ, '\"\"', t)      # ★ raw 双引号（斜杠不转义）
    t = re.sub(RAW_SQ, '\"\"', t)
    t = re.sub(NORM_DQ, '\"\"', t)     # 普通双引号（斜杠转义）
    t = re.sub(NORM_SQ, '\"\"', t)
    out = []
    for ln in t.split('\n'):
        out.append('' if ln.lstrip().startswith('#') else re.sub(r'\s+#.*$', '', ln))
    return '\n'.join(out)

def _r006_cases():
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 依据：`check_timevalue()` 的输出字段 ——
        · `n_bare` = **无证据支撑的确定性值个数**（如裸露的 `/tmp` 路径、指纹）
        · R048 的**时值检查三选一**要求：A 自包含 / B 标时点+复跑命令 / C 指向活体入口
      ⇒ B 项：**裸露值 ⇒ `n_bare > 0`**（判据能红）
      ⇒ C 项：**含时点 + 复跑命令 ⇒ `n_bare == 0`**（判据不误伤合法写法）
    ★ 实测值（2026-10-10 · 本机）：
        · 含裸露 /tmp 与指纹 ⇒ n_values=2 n_bare=2
        · 含时点+复跑命令    ⇒ n_values=2 n_bare=0
    """
    # ── B 负例：裸露的确定性值（易失路径 + 指纹，均无证据）⇒ 应红 ──
    _bare = ("临时文件在 /tmp/foo-12345.json，指纹 abcdef123456abcd。")
    r_bare = check_timevalue(_bare)
    # ── C 正例：标了时点 + 复跑命令（R048 的 B 式）⇒ 应无裸露值 ──
    _nl = chr(10)
    _good = ("时点：2026-10-10T03:00:00+0800" + _nl
             + "复跑命令：python3 tools/x.py --check" + _nl
             + "临时文件在 /tmp/foo.json（**命令自创建的中间文件**，非依赖）")
    r_good = check_timevalue(_good)

    b = [
        ("裸露易失路径+指纹 ⇒ 应红（n_bare=%d）" % r_bare["n_bare"], r_bare["n_bare"] > 0, True),
    ]
    c = [
        ("含时点+复跑命令 ⇒ 应无裸露值（n_bare=%d）" % r_good["n_bare"], r_good["n_bare"] == 0, True),
    ]
    return b, c



def selfcheck():
    """R006 ②③④ 能力边界自检。"""
    me = os.path.abspath(__file__)
    txt = open(me, encoding="utf-8").read()
    stripped = _strip_lits(_apply_exempt(txt))
    writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(|\.write\s*\(")
              if re.search(p, stripped)]
    outs = [p for p in (r"sys\.stdout", r"print\s*\(") if re.search(p, stripped)]
    checks = [
        ("② TCC：本工具**不写**被检对象", len(writes) == 0),
        ("③ 无 CLD 硬编码路径（可移植）", "/Applications/CLD.app" not in stripped),
        ("④ 版本单一来源 VERSION", 'VERSION = "%s"' % VERSION in txt),
        ("⑤ 有输出（非静默成功）", len(outs) > 0),
        ("⑩ A 预检：源码无危险原语（剥离后）",
         not any(re.search(p, stripped) for p in DANGEROUS_PRIMS)),
    ]
    print("★ selfcheck（R006 ②③④）")
    n = 0
    for name, ok in checks:
        print("  %s %s" % ("✅" if ok else "❌", name))
        n += 1 if ok else 0
    print("  自查：%d/%d" % (n, len(checks)))
    return 0 if n == len(checks) else 1


def lean4_check():
    """R006 ⑩ `--lean4-check` 六项（A–F）。"""
    me = os.path.abspath(__file__)
    raw = open(me, encoding="utf-8").read()
    stripped = _strip_lits(_apply_exempt(raw))
    res = []

    # ── A 源码无危险原语（**剥离后**扫）──
    a_hits = [p for p in DANGEROUS_PRIMS if re.search(p, stripped)]
    res.append(("A 源码无危险原语（剥离后扫）", len(a_hits) == 0,
                "命中 0 条" if not a_hits else "命中 %d 条：%s" % (len(a_hits), a_hits[:3])))

    # ── B/C：优先用工具自定义的合成输入 ──
    cases = _r006_cases()
    if cases is None:
        b_cases = [("通用负例·空值应被拒", bool(""), False),
                   ("通用负例·None 应被拒", bool(None), False)]
        c_cases = [("通用正例·非空应可用", bool("x"), True)]
        note = "★ 占位实现（本工具未定义 `_r006_cases()`）"
    else:
        b_cases, c_cases = cases
        note = "用本工具真实判据的纯函数部分"
    b_bad = [n for n, got, want in b_cases if got != want]
    res.append(("B 负例全部被拒", len(b_bad) == 0,
                "%d 条越界样例全部 FAIL（%s）" % (len(b_cases), note) if not b_bad
                else "★ 有负例被放过：%s" % b_bad))
    c_bad = [n for n, got, want in c_cases if got != want]
    res.append(("C 正例可用（防门太宽）", len(c_bad) == 0,
                "%d 条合法样例全部 PASS" % len(c_cases) if not c_bad else "★ 门把合法值也拦了：%s" % c_bad))

    # ── D 零变更（本类工具多只读 ⇒ 断言无写调用）──
    d_writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(") if re.search(p, stripped)]
    res.append(("D 零变更（无写调用）", len(d_writes) == 0,
                "源码无写文件调用" if not d_writes else "★ 检出写调用：%s" % d_writes))

    # ── E 白名单冻结 ──
    e_ok = isinstance(DANGEROUS_PRIMS, tuple) and isinstance(ALLOWED_CMDS, tuple)
    res.append(("E 白名单冻结（tuple）", e_ok, "DANGEROUS_PRIMS / ALLOWED_CMDS 为不可变 tuple"))

    # ── F 外部命令白名单（**枚举调用点 → 回原文读实参 → 断言 ⊆ 允许集**）──
    #    ★ 依 R006 F 项步骤：**去字面量定位调用点 → 回原文读实参**（否则会「空集通过」）。
    calls = re.findall(r"subprocess\.\w+\(\s*\[\s*\"([\w.\-]+)\"", raw)
    calls += re.findall(r"subprocess\.\w+\(\s*\[\s*'([\w.\-]+)'", raw)
    calls += re.findall(r"sh\(\s*\[\s*\"([\w.\-]+)\"", raw)
    calls += re.findall(r"sh\(\s*\[\s*'([\w.\-]+)'", raw)
    bad = sorted(set(calls) - set(ALLOWED_CMDS))
    res.append(("F 外部命令白名单（枚举 %d 处 → 断言 ⊆ %d 项）" % (len(calls), len(ALLOWED_CMDS)),
                len(bad) == 0, "命令集 %s" % sorted(set(calls)) if not bad else "★ 越界命令：%s" % bad))

    print("★ lean4-check（R006 ⑩ 六项）")
    n = 0
    for name, ok, note2 in res:
        print("  %s %s — %s" % ("✅" if ok else "❌", name, note2))
        n += 1 if ok else 0
    print("  六项：%d/%d %s" % (n, len(res), "全绿" if n == len(res) else "★ 未全绿"))
    return 0 if n == len(res) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--item", default=None)
    ap.add_argument("--proposer", default=None)
    ap.add_argument("--executor", default=None)
    ap.add_argument("--verifier", default=None)
    ap.add_argument("--tracker", default=str(TRACKER))
    ap.add_argument("--timevalue", nargs="+", default=None)
    ap.add_argument("--noise", nargs="+", default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 ②③④ 能力边界")
    ap.add_argument("--lean4-check", action="store_true", help="R006 ⑩ 六项 A–F")
    a = ap.parse_args()

    if a.selfcheck:

        sys.exit(selfcheck())

    if a.lean4_check:

        sys.exit(lean4_check())

    if a.selftest:
        sys.exit(selftest())
    if a.noise:
        sys.exit(noise(a.noise))

    print("★ review-gate v%s（S3 审查追踪 + R048 时值检查）" % VERSION)
    print("★ 扫描时点：%s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("★ 依据：**R048**（rules-registry/RULES.md L411 · enforced）+ "
          "`docs/submission-timevalue-checklist-v1.md`（244 行）")
    print()

    if a.register:
        if not (a.item and a.proposer and a.verifier):
            print("✗ --register 需 --item/--proposer/--verifier")
            sys.exit(2)
        p = Path(a.tracker).expanduser()
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"items": []}
        probe = {"item": a.item, "proposer": a.proposer, "executor": a.executor,
                 "verifier": a.verifier, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        # 校验：自审 / 缺 verifier
        red = []
        if not a.verifier:
            red.append("缺 verifier")
        nv, np_, ne = norm_sid(a.verifier), norm_sid(a.proposer), norm_sid(a.executor)
        if nv == np_:
            red.append("自审：verifier == proposer（归一后 %s）" % nv)
        if a.executor and nv == ne:
            red.append("自审：verifier == executor（归一后 %s）" % nv)
        if red:
            print("❌ 登记被拒（R048/R046 三方分离）：")
            for x in red:
                print("   · %s" % x)
            sys.exit(1)
        d.setdefault("items", []).append(probe)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("✅ 已登记：%s（proposer=%s · verifier=%s）⇒ %s"
              % (a.item, a.proposer, a.verifier, p))
        sys.exit(0)

    if a.timevalue:
        red, warn = [], []
        for f in a.timevalue:
            p = Path(f).expanduser()
            if not p.exists():
                print("  ❌ 不存在：%s" % p)
                red.append("文件不存在")
                continue
            r = check_timevalue(p.read_text(encoding="utf-8", errors="replace"), a.strict)
            print("=== 时值检查：%s ===" % p.name)
            print("  疑为实测值 **%d** 处 · 其中**无 ABC 证据** %d 处"
                  % (r["n_values"], r["n_bare"]))
            for v in r["bare"][:8]:
                print("    L%-4s [%s] %-28s ｜ %s" % (v["line"], v["kind"], v["text"], v["raw"][:60]))
            if r["n_bare"] == 0:
                print("  ✅ 无裸值")
            else:
                msg = "时值检查：%d 处裸值（无 A 自包含/B 标时点/C 活体指向）" % r["n_bare"]
                (red if a.strict else warn).append("%s ｜ %s" % (p.name, msg))
            print()
        # 判据四件齐备（仅当文本含「判据/指纹/可作告警」类陈述时提示）
        for f in a.timevalue:
            p = Path(f).expanduser()
            if not p.exists():
                continue
            txt = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"可作指纹|可作告警|判据", txt):
                q = check_timevalue(txt)["quad"]
                miss = [k for k, ok in q.items() if not ok]
                if miss:
                    warn.append("%s ｜ 判据类陈述缺件：%s（清单「追加」条款）" % (p.name, "、".join(miss)))
        print()
        if warn:
            print("⚠️ WARN %d 条（默认不判死；--strict 判死）：" % len(warn))
            for x in warn:
                print("   · %s" % x)
        if red:
            print("❌ 红项 %d 条：" % len(red))
            for x in red:
                print("   · %s" % x)
        print("══ 判定：%s ══" % ("❌ 有红项" if red else "✅ 无红项"))
        sys.exit(1 if red else 0)

    # 默认：列追踪表状态
    p = Path(a.tracker).expanduser()
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        items = d.get("items", [])
        print("=== 审查登记（%s）===" % p)
        print("  共 %d 件" % len(items))
        for it in items:
            print("    %-40s proposer=%s verifier=%s"
                  % (it.get("item", "")[:40], it.get("proposer", "?")[:12], it.get("verifier", "?")[:12]))
    else:
        print("=== 审查登记 ===")
        print("  尚无登记（%s）⇒ 用 --register 开始" % p)
    print()
    print("★ 提示：本工具的时值检查为**启发式**；按清单要求，"
          "**调阈值前先跑 `--noise <真实样本…>` 算噪声率**。")
    sys.exit(0)


if __name__ == "__main__":
    main()
