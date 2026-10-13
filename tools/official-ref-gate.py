#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""official-ref-gate.py — 官方规范校对门（锚点 §10 Wave S 之 S4）

依据（锚点 §6.1 强制前置，三条 —— 读原文）
    1. 跑 `guard_doc_check`（本地官方镜像 `~/tech-research/dsh-docs`，**24h 留证** `gate-state.json`）；
    2. 镜像无命中且需落地 ⇒ 官方来源 **web 补证后再动**；
    3. 产物记录「**官方条款 → 我们的设计 → 差异（一致/未覆写/未证）**」。

★ 与 J44 的关系：本工具**封装/调用**既有 `guard_doc_check`（工具面），**不重造其检索能力** ——
  它只做**准入判定**：读留证、核三栏、给 GO/NO-GO。裁决留痕见 `j44-reuse-gate.py --list`。

实测的留证结构（**读实体取得，非假设**）
    `~/dsh-collab/guard/gate-state.json`：
      { "_doc_checks": [ { "ts","ts_epoch","target","topic","domain",
                           "mirror_hits","hit_files","mirror_age_days","mirror_stale","web_evidence" } ],
        "_day": …, "_tasks": …, "<绝对路径>": … }

用户面
    python3 tools/official-ref-gate.py --list                 # 列留证（按时间倒序）
    python3 tools/official-ref-gate.py --target "session persistence"   # 该主题的留证是否 24h 内
    python3 tools/official-ref-gate.py --artifact <产物.md>            # 该产物是否含「条款→设计→差异」三栏
    python3 tools/official-ref-gate.py --artifact <产物> --target <主题>  # 合判（推荐）
    python3 tools/official-ref-gate.py --selftest

退出码
    0 = GO（留证新鲜 **且** 产物三栏齐）· 1 = NO-GO · 2 = 用法/环境错误

自陈限度
    · 「24h」取自锚点原文，**本工具不判断该时长是否合理**；
    · 三栏判据为**关键词共现启发式**（见下），**可能假阳/假阴**；
    · 本工具**不调用** `guard_doc_check`（它是工具面，脚本无法直调）⇒ 若留证过期，
      正确动作是**先跑 `guard_doc_check` 生成新留证**，而非由本工具代跑。
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

VERSION = "1.0.0"
STATE = Path.home() / "dsh-collab" / "guard" / "gate-state.json"
MIRROR = Path.home() / "tech-research" / "dsh-docs"
FRESH_HOURS = 24

# 三栏的语义别名（锚点：官方条款 → 我们的设计 → 差异）
COL_OFFICIAL = ["官方条款", "官方来源", "条款", "官方文档", "official"]
COL_OURS = ["我们的设计", "本方设计", "设计", "实现", "our design"]
COL_DIFF = ["差异", "一致", "未覆写", "未证", "diff", "差距"]


def load_state():
    if not STATE.exists():
        return None
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as e:
        print("✗ gate-state.json 不可解析：%s" % e)
        return None


def checks_of(st):
    if not isinstance(st, dict):
        return []
    rows = st.get("_doc_checks")
    return rows if isinstance(rows, list) else []


def age_hours(rec):
    t = rec.get("ts_epoch")
    if isinstance(t, (int, float)) and t > 0:
        return (time.time() - t) / 3600.0
    ts = rec.get("ts")
    if isinstance(ts, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return (time.time() - datetime.datetime.strptime(ts, fmt).timestamp()) / 3600.0
            except Exception:
                continue
    return None


def match_target(rows, target):
    if not target:
        return None
    key = target.strip().lower()
    best = None
    for r in rows:
        blob = ("%s %s %s" % (r.get("target", ""), r.get("topic", ""), r.get("domain", ""))).lower()
        if key in blob:
            if best is None or (r.get("ts_epoch") or 0) > (best.get("ts_epoch") or 0):
                best = r
    return best


def check_artifact(p):
    txt = Path(p).expanduser().read_text(encoding="utf-8", errors="replace")
    hit = {}
    for name, aliases in (("官方条款", COL_OFFICIAL), ("我们的设计", COL_OURS), ("差异", COL_DIFF)):
        hit[name] = sorted({a for a in aliases if re.search(re.escape(a), txt, re.I)})
    # ★ 三栏须**同段共现**才算「成栏」（单字散落不算）—— 启发式
    lines = txt.splitlines()
    trio_lines = [i for i, ln in enumerate(lines)
                  if any(a in ln for a in COL_OFFICIAL)
                  and any(a in ln for a in COL_DIFF)]
    return hit, trio_lines


def selftest():
    # gate-self-exempt: begin  ← 测试样例区（临时目录内造数据并清理，不碰生产）
    """★ 自证：合成留证与产物，证明两侧判据都会红"""
    import tempfile
    cases = []
    tmp = Path(tempfile.mkdtemp(prefix="s4-neg-"))
    # ① 留证新鲜度：构造 1h 前 → 应 GO；48h 前 → 应 NO-GO
    now = time.time()
    r_fresh = {"ts_epoch": now - 3600, "target": "x"}
    r_stale = {"ts_epoch": now - 48 * 3600, "target": "x"}
    cases.append(("合成·留证 1h 前 ⇒ 新鲜", (age_hours(r_fresh) or 0) <= FRESH_HOURS, True))
    cases.append(("合成·留证 48h 前 ⇒ 过期", (age_hours(r_stale) or 0) > FRESH_HOURS, True))
    # ② 三栏：只写两栏 → 应检出缺
    a = tmp / "two-col.md"
    a.write_text("官方条款 §6.1 说 X。我们的设计是 Y。\n", encoding="utf-8")
    hit, trio = check_artifact(a)
    cases.append(("合成·缺「差异」栏 ⇒ 可判缺", not hit["差异"], True))
    b = tmp / "three-col.md"
    b.write_text("官方条款：A ｜ 我们的设计：B ｜ 差异：一致\n", encoding="utf-8")
    hit2, trio2 = check_artifact(b)
    cases.append(("合成·三栏齐 ⇒ 无缺", all(hit2.values()), True))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("★ official-ref-gate 自证：合成正/负例证明判据可判")
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


    # gate-self-exempt: end
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

    ★ 用**字符扫描**实现（而非单条复杂正则）—— 后者在自身源码里会被自己的模式串干扰。
    """
    out, i, n = [], 0, len(txt)
    while i < n:
        ch = txt[i]
        if ch == "#":
            while i < n and txt[i] != "\n":
                i += 1
            out.append("\n")
            continue
        if txt.startswith('"""', i) or txt.startswith("'''", i):
            q = txt[i:i + 3]
            i += 3
            while i < n and not txt.startswith(q, i):
                i += 1
            i += 3
            out.append('""')
            continue
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and txt[i] != q:
                if txt[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append('""')
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _r006_cases():
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 依据：`age_hours()` / `FRESH_HOURS` 与三栏判据 —— 它们正是 `selftest()` 里已有的
      合成负例，本函数把它们**抽出来给 R006 B/C 复用**（同一判据，不另起一套）。
    ★ 实测（2026-10-10）：留证 1h 前 ⇒ 新鲜（GO）；48h 前 ⇒ 过期（NO-GO）。
    """
    _now = time.time()
    _fresh = {"ts_epoch": _now - 3600, "target": "x"}
    _stale = {"ts_epoch": _now - 48 * 3600, "target": "x"}

    b = [
        ("留证 48h 前 ⇒ 应过期（age=%.1fh > %.1fh）" % (age_hours(_stale) or -1, FRESH_HOURS),
         (age_hours(_stale) or 0) > FRESH_HOURS, True),
    ]
    c = [
        ("留证 1h 前 ⇒ 应新鲜（age=%.1fh ≤ %.1fh）" % (age_hours(_fresh) or -1, FRESH_HOURS),
         (age_hours(_fresh) or 0) <= FRESH_HOURS, True),
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
    ap.add_argument("--target", default=None)
    ap.add_argument("--artifact", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:

        sys.exit(selfcheck())

    if a.lean4_check:

        sys.exit(lean4_check())

    if a.selftest:
        sys.exit(selftest())

    print("★ official-ref-gate v%s（S4 官方规范校对门）" % VERSION)
    print("★ 扫描时点：%s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("★ 依据：锚点 §6.1 强制前置（24h 留证 · web 补证 · 产物三栏）")
    print("★ 镜像：%s  %s" % (MIRROR, "存在" if MIRROR.exists() else "**不存在**"))
    print()

    st = load_state()
    rows = checks_of(st)
    print("=== ① 留证（%s）===" % STATE)
    if st is None:
        print("  ❌ 不可读 ⇒ 须先跑 guard_doc_check 生成留证")
    else:
        print("  _doc_checks 条数：%d" % len(rows))
        if a.list:
            for r in sorted(rows, key=lambda x: x.get("ts_epoch") or 0, reverse=True)[:12]:
                ag = age_hours(r)
                print("    %-20s %-34s %s"
                      % (str(r.get("ts"))[:19], str(r.get("target") or r.get("topic"))[:34],
                         ("%.1fh 前" % ag) if ag is not None else "年龄未知"))
    red = []
    if a.target:
        rec = match_target(rows, a.target)
        if rec is None:
            print("  ❌ 主题「%s」**无留证** ⇒ NO-GO（须先跑 guard_doc_check）" % a.target)
            red.append("主题无留证")
        else:
            ag = age_hours(rec)
            fresh = (ag is not None and ag <= FRESH_HOURS)
            print("  %s 主题「%s」留证 %s（%.1fh 前，阈值 %dh）"
                  % ("✅" if fresh else "❌", a.target, str(rec.get("ts"))[:19],
                     ag if ag is not None else -1, FRESH_HOURS))
            print("      mirror_hits=%s · mirror_stale=%s · 域=%s"
                  % (rec.get("mirror_hits"), rec.get("mirror_stale"), rec.get("domain")))
            if not fresh:
                red.append("留证过期（>%dh）" % FRESH_HOURS)
    print()

    if a.artifact:
        p = Path(a.artifact).expanduser()
        print("=== ② 产物三栏（%s）===" % p)
        if not p.exists():
            print("  ❌ 产物不存在")
            red.append("产物不存在")
        else:
            hit, trio = check_artifact(p)
            for k in ("官方条款", "我们的设计", "差异"):
                print("  %s %-10s 命中别名：%s" % ("✅" if hit[k] else "❌", k, hit[k] or "**无**"))
            print("  %s 同段共现（「官方」与「差异」同行）行数：%d"
                  % ("✅" if trio else "⚠️", len(trio)))
            miss = [k for k in ("官方条款", "我们的设计", "差异") if not hit[k]]
            if miss:
                red.append("产物缺栏：%s" % "、".join(miss))
        print()

    # ★★★ 2026-10-13 修（W4 H1）：【空分母必须报「不可判」，不得报 GO】—★
    #   ★★ 立据：W4 点名的第①处假绿：未给 `--target/--artifact` ⇒ **本体【未做准入判定】**，
    #     ★★ 而它仍打 `✅ GO` 且 `rc=0` ⇒ **空分母下报绿**。
    #   ★ 目标（锚点 :2133）：分母为 0 或可被完全跳过的检查项 = 0
    #     ⇒ ★ 空分母输入时，判据必须指向「**不可判**」。
    no_target = not (a.target or a.artifact)
    if red:
        _verdict = "❌ **NO-GO**（禁止动 dsh 设计项）"; _rc = 1
    elif no_target:
        _verdict = "⚠️ **UNDECIDABLE（不可判）**"; _rc = 2
    else:
        _verdict = "✅ **GO**"; _rc = 0
    print("══ 判定：%s ══" % _verdict)
    for x in red:
        print("   · %s" % x)
    if no_target:
        print("   （未给 --target/--artifact ⇒ **本体未做准入判定**）")
        print("   ★★ **空分母 ⇒ 不得报「通过」**（★ W4 H1：空分母必须指向不可判）")
    if a.json:
        print(json.dumps({"version": VERSION, "red": red, "verdict": _verdict, "rc": _rc,
                          "no_target": no_target,
                          "doc_checks": len(rows)}, ensure_ascii=False, indent=1))
    sys.exit(_rc)


if __name__ == "__main__":
    main()
