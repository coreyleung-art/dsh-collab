#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""version-pin-lint.py — **版本判据的点值/下限检查**（不改被核对象；临时写面 = `guard/mutation-work/`）。

★ 立据（判决位 2026-10-10 重启前审查，会致**误回滚**）：T3 前置判据原文写「必须返回 `version 0.12.0`」，
  而盘面已推进到 0.12.12 ⇒ **字面执行 ⇒ 判不通过 ⇒ 误回滚**。⇒ 规矩：**版本判据钉下限（≥X），不钉点值**；
  若必须点值，须**同句**给出理由（例如"该判据就是在核这一版"）。

★ 判据（执行，不是抄写）：
  · 含项 = 目标文件里**出现在判据语境**的版本点值：行内同时含「必须/须/应为/==/=」与 `版本号 0.x.y`
    （或 `version` 与 `0.x.y` 同行）
  · 排除项 = ① 历史叙述行（含「→」「曾」「原文」「保留」，或出现在表格的"变更"列）② 版本标题行（`## 0.12.x`）
    ③ 同句已含下限词（`≥`/`>=`/「下限」/「或更高」/「至少」）④ 同句已含理由标记（「同源」「首个」「点值理由」）
  · 补偿控制 = ① 命中即红（fail-closed）② **零命中 ⇒ 也打印**（避免"没扫到"被读成"没问题"）
    ③ 打印扫描面（文件数 · 行数）与运行戳 ④ 单位 = 处；**工具** = python3；**时刻** = RFC3339

退出码：0 = 通过 · 1 = 有点值判据未注明 · 2 = 用法错误
用法：python3 tools/version-pin-lint.py <文件...> | --selftest
"""
import datetime
import os
import re
import sys

HERE = os.path.expanduser("~/dsh-collab")
VER = re.compile(r"\b(\d+\.\d+\.\d+)\b")
# ★ 判决 2026-10-10：判据面**只能收「判据句式」** —— 裸 `=`/`==` 会把常量定义、清点行、夹具行全捞进来。
CRIT_WORDS = ("必须", "须", "应为")
CRIT_SENTENCE = re.compile(r"(必须|须|应为)[^\n]{0,20}version|version[^\n]{0,12}(==|＝)", re.I)
LOWER_WORDS = ("≥", ">=", "下限", "或更高", "至少", "以上")
REASON_WORDS = ("同源", "首个", "点值理由", "原文", "保留")


def ts():
    s = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return s[:-2] + ":" + s[-2:]


def non_criterion_kind(ln):
    """★ 公共判定：返回**非判据**的类别名，或 None（＝可能是判据）。两个检查共用，避免两套面。"""
    if re.match(r"\s*[A-Z_]{3,}\s*=", ln) or ("VERSION" in ln and "=" in ln and '"' in ln):
        return "定义行"
    if ("open(" in ln and "write(" in ln) or ("\\n" in ln and "write(" in ln):
        return "夹具行"
    if any(w in ln for w in ('"incident"', '"covers"', '"title"', "原话", "引述", "事故")):
        return "引述行"
    if any(w in ln for w in ("立据", "钉下限", "不钉点值", "规矩：")):
        return "元规则行"
    if any(w in ln for w in ("✅", "❌", "实测", "读数", "记录")):
        return "读数行"
    if "→" in ln or "变更" in ln:
        return "历史行"
    return None


def scan(path):
    hits, scanned = [], 0
    half = []                      # ★ 只钉下限、缺「同源/一致」条款的**半边判据**
    excluded = {"定义行": 0, "夹具行": 0, "引述行": 0}   # ★ 排除项**必须计数**（不许静默丢弃）
    live, hist = 0, 0
    for ln_no, ln in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        scanned += 1
        if "version" not in ln.lower() and "版本" not in ln:
            continue
        m = VER.search(ln)
        if not m:
            continue
        if not any(w in ln for w in CRIT_WORDS):
            excluded["非判据句式"] = excluded.get("非判据句式", 0) + 1
            continue
        if not CRIT_SENTENCE.search(ln):
            excluded["非判据句式"] = excluded.get("非判据句式", 0) + 1
            continue
        # ★★ 三类非判据（判决 2026-10-10：全库跑命中 8 处，「面宽于声明」）——各自计数后排除：
        _is_def = bool(re.match(r"\s*[A-Z_]{3,}\s*=", ln)) or ("VERSION" in ln and "=" in ln and '"' in ln)
        _is_fix = ("open(" in ln and "write(" in ln) or ("\\n" in ln and "write(" in ln)
        _is_quote = any(w in ln for w in ('"incident"', '"covers"', '"title"', "原话", "引述", "事故"))
        # ★ **元规则行**：本工具自己的「立据」段落**引述**被判据、并陈述规矩 ⇒ 不是活判据（判决：面宽于声明）
        _is_meta = any(w in ln for w in ("立据", "钉下限", "不钉点值", "规矩："))
        if _is_def:
            excluded["定义行"] += 1
            continue
        if _is_fix:
            excluded["夹具行"] += 1
            continue
        if _is_quote:
            excluded["引述行"] += 1
            continue
        if _is_meta:
            excluded["元规则行"] = excluded.get("元规则行", 0) + 1
            continue
        if ln.lstrip().startswith("#"):
            continue
        if any(w in ln for w in LOWER_WORDS) or any(w in ln for w in REASON_WORDS):
            continue
        if "→" in ln or "变更" in ln:
            continue
        # ★★ 判决位 2026-10-10 的边界：「改写面比裁定说的小 —— 只有 :97 是**活判据**；:13/:27 是**历史基线/读数**，
        #   改了反而是篡改。」⇒ 判据必须区分 **读数表行（带 ✅/❌/实测/读数）** 与 **判据指令行**：
        #   读数行**不算判据**（它记录"当时读到什么"，不是"必须是什么"）。
        if any(w in ln for w in ("✅", "❌", "实测", "读数", "记录")):
            continue
        hits.append((ln_no, m.group(1), ln.strip()[:110]))

    # ★★ 半边判据检查（裁判：只钉下限会漏掉"落后但达标"）：
    #   在**判据语境**里出现下限词 ⇒ 必须同时出现同源/一致条款（同段 3 行内），否则记「缺同源条款」。
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    for i, ln in enumerate(lines):
        if "version" not in ln.lower() and "版本" not in ln:
            continue
        if not any(w in ln for w in LOWER_WORDS):
            continue
        # ★ 判决②第二轮：半边长句也**必须是判据句式** —— 需有**判据动作词**（调/返回/验证/检查/判据/触发）
        #   否则会把"清点行/修复叙述/docstring"都当成半边判据（实测捞出 10 处噪声）。
        if not any(w in ln for w in ("调", "返回", "验证", "检查", "判据", "触发")):
            continue
        if ln.lstrip().startswith('"""') or "不改被核对象" in ln:      # 工具自述 docstring 不是判据
            continue
        _k2 = non_criterion_kind(ln)
        if _k2:                                          # ★ 半边检查套用**同一套**排除（否则会捞元规则行/夹具行）
            continue
        window = "\n".join(lines[i:i + 3])
        if ("==" in window) or ("同源" in window) or ("一致" in window):
            continue
        if any(w in ln for w in ("✅", "❌", "实测", "读数")):
            continue
        half.append((i + 1, ln.strip()[:110]))
    return hits, scanned, half, excluded


def main():
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not files:
        print("用法错误：需要至少一个文件")
        return 2
    RUN = ts()
    print("version-pin-lint · 版本判据的**点值/下限**检查（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
    print(f"  · 本次运行戳 run={RUN} —— ★ 引用本页数字须连同它一起引用")
    print("  观测面（六要素）：**含项** = 判据语境里的版本点值（同行含 必须/须/应为/== 且含 `0.x.y`）；"
          "**排除项** = ① 历史叙述（含 →/变更/原文保留）② 版本标题行 ③ 同句已含下限词 ④ 同句已含理由词；"
          "**补偿控制** = ① 命中即红 ② **零命中也打印扫描面**（「没扫到」≠「没问题」）③ 打印运行戳 ④ 单位=处；"
          "**工具** = python3；**单位** = 处；**时刻** = " + RUN)
    total_hits, total_lines, half_here, ex_counts = [], 0, [], {}
    for f in files:
        p = f if os.path.isabs(f) else os.path.join(HERE, f)
        if not os.path.isfile(p):
            print(f"  ★ 文件不存在（**不可判**，非绿）：{f}")
            return 2
        h, n, _hf, _ex = scan(p)
        for k, v in _ex.items():
            ex_counts[k] = ex_counts.get(k, 0) + v
        half_here.extend([(os.path.relpath(p, HERE), x) for x in _hf])
        total_lines += n
        print(f"  · {os.path.relpath(p, HERE)}：扫描 **{n}** 行 ⇒ 命中 **{len(h)}** 处")
        total_hits += [(os.path.relpath(p, HERE), x) for x in h]
    print(f"  · 扫描面合计：**{len(files)}** 文件 · **{total_lines}** 行")
    print(f"  · **排除项（已计数，非静默丢弃）**：" +
          (" · ".join(f"{k} **{v}** 处" for k, v in sorted(ex_counts.items())) if ex_counts else "无"))
    if half_here:
        print(f"\n★ **半边判据**（只钉下限、缺同源条款）**{len(half_here)}** 处 —— "
              f"裁判裁定：**下限排除「太旧」、同源排除「不一致」，两者缺一不可**：")
        for f, (ln, txt) in half_here:
            print(f"  {f}:{ln} · {txt}")
    if not total_hits and not half_here:
        print(f"\n✅ [run {RUN}] 通过：**未发现未注明的版本点值判据，也无半边判据**（扫描面见上）")
        return 0
    if not total_hits and half_here:
        # ★ 结论行必须与退出码一致（今天已多次因"打绿却红"被抓）
        print(f"\n❌ [run {RUN}] **未通过**：点值判据 0 处，但**半边判据 {len(half_here)} 处** ⇒ "
              f"**下限排除「太旧」、同源排除「不一致」，缺一不可**")
        return 1
    print(f"\n❌ [run {RUN}] 发现 **{len(total_hits)}** 处未注明的版本点值判据（应钉下线或注明理由）：")
    for f, (ln, v, txt) in total_hits:
        print(f"  {f}:{ln} ⇒ `{v}` · {txt}")
    return 1


def selftest():
    import shutil
    import tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="version-pin-lint-selftest-", dir=work)
    bad = []
    try:
        p = os.path.join(sb, "d.md")
        # 正控①：点值判据
        open(p, "w", encoding="utf-8").write("- 调 csx_status ⇒ 必须返回 `version 0.12.0`\n")
        h, _, _, _ = scan(p)
        print(f"  {'✅' if len(h) == 1 else '❌'} 正控：点值判据（必须返回 version X）⇒ 命中（{len(h)}）")
        if len(h) != 1:
            bad.append("点值未命中")
        # 反控①：下限写法 ⇒ 不命中
        open(p, "w", encoding="utf-8").write("- 调 csx_status ⇒ `version` **≥ 0.12.0**（下限）\n")
        h, _, _, _ = scan(p)
        print(f"  {'✅' if not h else '❌'} 反控：下限写法（≥）⇒ 不命中")
        if h:
            bad.append("下限被误报")
        # 反控②：历史叙述 ⇒ 不命中
        open(p, "w", encoding="utf-8").write("- **2026-10-10** 版本 0.11.1 → **0.12.0**（变更记录）\n")
        h, _, _, _ = scan(p)
        print(f"  {'✅' if not h else '❌'} 反控：历史叙述（含 →/变更）⇒ 不命中")
        if h:
            bad.append("历史叙述被误报")
        # 正控②：表格点值判据
        open(p, "w", encoding="utf-8").write("| 前置 | 必须 `version 0.12.0` |\n")
        h, _, _, _ = scan(p)
        print(f"  {'✅' if len(h) == 1 else '❌'} 正控：表格里的点值判据 ⇒ 命中（{len(h)}）")
        if len(h) != 1:
            bad.append("表格点值未命中")
        # ★ 半边判据：正控（只钉下限 ⇒ 判半边）+ 反控（下限+同源 ⇒ 不判）
        open(p, "w", encoding="utf-8").write("- 调 csx_status ⇒ `version` **≥ 0.12.0**（下限）\n")
        h3, _, half3, _ = scan(p)
        print(f"  {'✅' if (not h3 and len(half3) == 1) else '❌'} 正控：**只钉下限** ⇒ 判「半边判据」（{len(half3)}）")
        if h3 or len(half3) != 1:
            bad.append("半边判据未判")
        open(p, "w", encoding="utf-8").write("- 调 csx_status ⇒ `version` **≥ 0.12.0** 且 **== 盘面 version**（同源）\n")
        h4, _, half4, _ = scan(p)
        print(f"  {'✅' if (not h4 and not half4) else '❌'} 反控：**下限 + 同源** ⇒ 不判（半边 {len(half4)}）")
        if h4 or half4:
            bad.append("完整判据被误判")
        if bad:
            print("  ❌ --selftest 失败：" + " ｜ ".join(bad))
            return 1
        print("  ✅ --selftest 通过：**正控 3**（行内点值 · 表格点值 · **只钉下限 ⇒ 半边判据**）"
              "+ **反控 3**（下限 · 历史叙述 · **下限+同源 ⇒ 不判**）")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
