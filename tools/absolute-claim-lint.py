#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""absolute-claim-lint.py — 「绝对断言须同句给观测面」的可机械核验门（**不改被核对象**；临时写面 = `guard/mutation-work/`）。

★ 立据（短判决位 2026-10-10 判决 + 命名的**两轮两现**模式）：
  · 我在崩溃牵连自查里写「原生栈 SIGABRT **不可能**出自本件」——**加了限定语（⚠不等于已排除）却没降断言**；
  · 上一轮我在待办表里写「他人维护 · 需其维护者决定」——**同样是加了限定、没降断言**（那是我不知道的东西）。
  · ⇒ 模式命名：**加限定但不降断言**。正确的做法是**把断言降到观测能支撑的强度**（"未发现"），
    那样限定语就不需要了。
  · 判决给的建议判据：**凡「不可能 / 一定 / 全部」须同句给观测面**。本件就是它的机械形式。

规则（只读；扫描前**剥离代码块**——设计承诺句常写在代码/fence 里，例如不变量「绝不静默 no-op」）：
  R1b **归纳/规律类断言**（归纳/规律/总是/每次/从不/分布/统计上）**同句必须标成色**
      （定性/统计/样本/当夜/本次/范围内）—— 判决位 2026-10-10：「**归纳要连它的成色一起标，否则会被后人当统计引用**」。
  R1 含**绝对断言词**（不可能/一定/全部/必然/绝不/永远/从未/无一/毫无）的行，
     **同句**必须含**观测面标记**（观测面/含项/排除项/实测/范围内/经核/R030/据…核）。
     缺标记 ⇒ 红，并给出改写建议：**降到「未发现」**或**补观测面**。
  R2 **豁免通道**（声明式）：同一行或上一行写 `<!-- absolute-claim-allow: <理由> -->` ⇒ 豁免（须非空理由）。

退出码：0 = 无违例 · 1 = 有违例 · 2 = 用法错误
用法：python3 tools/absolute-claim-lint.py [<文件或目录> ...]   # 缺省扫 docs/*.md 与插件 CHANGELOG.md
  --selftest  造四条对照（该红必红 / 带观测面必绿 / fence 内设计承诺必绿 / 显式豁免必绿）
  ★ 默认只扫**本会话自己写的那几份**；他人文档请显式传路径（其命中只作提示）
"""
import glob
import os
import re
import sys

HERE = os.path.expanduser("~/dsh-collab")
# ★ 默认只扫**我自己的产物**（2026-10-10 实测教训：首版默认 glob 了 docs/*.md ⇒ 539 个文件，
#   绝大多数是**他人**的文档 ⇒ 既越权（我无权要求别人改）又噪声（「全部」是常用词，不是断言）。
#   ⇒ 默认白名单化；要广扫请显式传路径，且他人文档的命中**只作提示**。
# ★★ 适用面（第三版修正，2026-10-10）：**本判据管"证据性断言"，不管"设计承诺"与"历史日志"**。
#   实测：把 append-only 的台账纳入默认面 ⇒ 19 处命中，绝大多数是
#     ① 设计承诺（"绝不写进 inject" / "绝不抛出" / "绝不冒充 MISS" —— 可据源码核，且是**契约**不是观测）
#     ② 数学推导（"必然高于 0.8" —— 可据算术核）
#   而台账本身**只追加、不可改写**（文件地图明写）⇒ **不得为过门而改写历史**。
#   ⇒ 默认面收窄为"我当次可控的陈述性文件"；台账改**显式传入**（其命中作**提示**，并附本说明）。
#   实测第二版：把 CHANGELOG 也纳入 ⇒ 24 处命中，**同样是"设计承诺 + append-only 历史"**
#   （例：「绝不冒充 MISS」「绝不写进 inject」「永远发现不了」）⇒ 同一结论：**本判据不该管历史与契约**。
#   ⇒ 默认面 = **我当次可控的陈述性文件**（可改、且承载"证据性断言"）；历史与契约类文件**显式传入**，
#     其命中作**提示**，且**不得为过门改写历史**（只追加）。
DEFAULT_TARGETS = [
    os.path.join(HERE, "docs/k5-section5-criteria-matrix.md"),
    os.path.join(HERE, "tools/PRINCIPLES-landing.md"),
]
# ★ 只收**真绝对断言词**；剔除「全部」（常用词：分类/清单语境里到处都是 ⇒ 噪声大于信号）
# ★ R1b：归纳/规律类断言的词表（判决位 2026-10-10）
GENERALIZE = ["归纳", "规律", "统计上", "分布上"]
GEN_VERB = ["都", "总是", "每次", "从不", "凡", "无一例外"]
CALIBER_MARK = ["定性", "统计", "样本", "当夜", "本次", "范围内", "次数", "定量的", "非统计"]
ABSOLUTE = ["不可能", "一定", "必然", "绝不", "永远", "从未", "无一", "毫无", "绝不会"]
SURFACE = ["观测面", "含项", "排除项", "实测", "范围内", "经核", "R030", "据实测", "已核"]
ALLOW_MARK = "absolute-claim-allow:"


def strip_fences(text):
    """剥离 ``` 围栏内的行（设计承诺/代码常在那里；它们不是观测断言）。"""
    out, in_fence = [], False
    for ln in text.split("\n"):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else ln)
    return out


def check(paths):
    bad, scanned = [], 0
    files = []
    excluded_files = []          # ★ 面与实际一致：被排除的文件必须列出来（含原因）
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "*.md")))
        elif any(ch in p for ch in "*?["):
            files += sorted(glob.glob(p))
        else:
            files.append(p)
    for f in files:
        if not os.path.isfile(f):
            excluded_files.append((f, "不存在"))
            continue
        if not f.endswith((".md", ".txt")):
            excluded_files.append((f, "非 .md/.txt（本判据只扫陈述性文本）"))
            continue
        scanned += 1
        raw = open(f, encoding="utf-8", errors="replace").read().split("\n")
        live = strip_fences("\n".join(raw))
        for i, ln in enumerate(live):
            # ★ R1b（独立于 R1）：**归纳/规律类断言须同句标成色**
            _gen = [g for g in GENERALIZE if g in ln]
            if _gen and any(v in ln for v in GEN_VERB):
                if not any(c in ln for c in CALIBER_MARK):
                    if ALLOW_MARK not in ln and not (i > 0 and ALLOW_MARK in raw[i - 1]):
                        bad.append(f"{os.path.relpath(f, HERE)}:{i+1} 含归纳类断言「{_gen[0]}…」**同句未标成色** "f"⇒ 请标「定性/统计/样本/当夜/范围内」之一（判决位：**归纳要连成色一起标，否则会被后人当统计引用**）")
                        continue
            if not any(a in ln for a in ABSOLUTE):
                continue
            if any(s in ln for s in SURFACE):
                continue
            if ALLOW_MARK in ln or (i > 0 and ALLOW_MARK in raw[i - 1]):
                continue
            hit = [a for a in ABSOLUTE if a in ln][0]
            bad.append(f"{os.path.relpath(f, HERE)}:{i+1} 含绝对断言「{hit}」但**同句无观测面** "
                       f"⇒ 请降到观测能支撑的强度（如「未发现」），或同句给观测面（含项/排除项/实测/R030）"
                       f"；确属设计承诺请加豁免声明")
    return bad, scanned, len(files), excluded_files


def selftest():
    import shutil, tempfile
    sb = tempfile.mkdtemp(prefix="absclaim-", dir=os.path.join(HERE, "guard/mutation-work"))
    cases = []
    try:
        # ★ R1b 正反控（归纳类断言须同句标成色）
        p_r1b_red = os.path.join(sb, "r1b-red.md")
        open(p_r1b_red, "w", encoding="utf-8").write("本线今晚的规律：每一例都由当事人自己认下。\n")
        cases.append(("该红：归纳类断言未标成色", p_r1b_red, True))
        p_r1b_green = os.path.join(sb, "r1b-green.md")
        open(p_r1b_green, "w", encoding="utf-8").write("本线今晚的规律（**当夜定性归纳，非统计**）：每一例都由当事人自己认下。\n")
        cases.append(("该绿：归纳类断言已标成色", p_r1b_green, False))
        p1 = os.path.join(sb, "a.md")
        open(p1, "w", encoding="utf-8").write("本插件与本次崩溃的关联**不可能**存在。\n")
        cases.append(("该红：绝对断言、同句无观测面", p1, True))
        p2 = os.path.join(sb, "b.md")
        open(p2, "w", encoding="utf-8").write("**未发现**关联（观测面：含项=CLD 日志零命中；排除项=未做符号化归因）。\n")
        cases.append(("该绿：降到『未发现』+ 给观测面", p2, False))
        p3 = os.path.join(sb, "c.md")
        open(p3, "w", encoding="utf-8").write("```\n不变量 I1：绝不静默 no-op（设计承诺，非观测断言）\n```\n")
        cases.append(("该绿：fence 内的设计承诺", p3, False))
        p4 = os.path.join(sb, "d.md")
        open(p4, "w", encoding="utf-8").write("<!-- absolute-claim-allow: 引用规范原文 -->\n原文要求「绝不静默」。\n")
        cases.append(("该绿：显式豁免声明", p4, False))
        okall = True
        for name, f, want_red in cases:
            bad, _, _, _ = check([f])
            red = len(bad) > 0
            good = red == want_red
            okall = okall and good
            print(f"  {'✅' if good else '❌'} {name}（实得 {'红' if red else '绿'}）")
        if not okall:
            print("  ❌ --selftest 失败")
            return 1
        print("  ✅ --selftest 通过：两正控（无观测面 ⇒ 红）与两反控（降断言/fence/豁免 ⇒ 绿）均符合预期")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    targets = [a for a in sys.argv[1:] if not a.startswith("--")] or DEFAULT_TARGETS
    bad, scanned, nfiles, excluded_files = check(targets)
    if excluded_files:
        print(f"  · **排除的文件（{len(excluded_files)} 个，非静默丢弃）**：" +
              " · ".join(f"`{os.path.basename(f)}`（{why}）" for f, why in excluded_files[:4]))
    print("absolute-claim-lint · 绝对断言须同句给观测面（只读；剥离 fence）")
    # ★ 时刻由 Python 取（不在 shell 里拼引号 —— 第一版就是这样把 `+0800` 截成 `+08:` 的）
    import datetime as _dt
    ts = _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    ts = ts[:-2] + ":" + ts[-2:]
    print(f"  · **扫描 {scanned} 个文件**（发现 {nfiles} 个；差额见下方「排除的文件」）· 默认面 = **我自己当次可控的陈述性文件**")
    # ★ 观测面五要素（判决 B：enrollment 做对过的这套没继承到本件 ⇒ 第六次）
    print(f"  · 观测面：**含项** = {len(targets) if isinstance(targets, list) else '?'} 个显式目标"
          + (f"（{', '.join(os.path.relpath(t, HERE) for t in targets[:4] if isinstance(t, str) and t.startswith(HERE))}…）" if targets else "")
          + "；**排除项** = ① append-only 历史（台账/CHANGELOG）与设计承诺（不属证据性断言，需显式传入才扫）"
            "② 非 .md/.txt ③ ```` fence 内 ④ 他人文档（默认不扫，越权且噪声）"
          f"；**补偿控制** = ① 默认面收窄到「我当次可控的陈述性文件」（不越权扫他人文档）"
          f" ② 历史/契约类文件**显式传入**且命中只作提示（不得为过门改历史）"
          f" ③ `--selftest` 两正控两反控证明判据本身有判别力"
          f"；**工具** = python3 静态扫描（剥离 fence）；**单位** = 文件 · 行；**时刻** = {ts}")
    if bad:
        print("\n❌ 违例：")
        for b in bad[:20]:
            print("  " + b)
        if len(bad) > 20:
            print(f"  …另有 {len(bad) - 20} 条")
        return 1
    print("\n✅ 通过：未发现「绝对断言但同句无观测面」的行")
    return 0


if __name__ == "__main__":
    sys.exit(main())
