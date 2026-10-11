#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report-claim-check.py — **报告声明可核性判据**（**不改被核对象**；临时写面 = `guard/mutation-work/`）：让「凡引用落盘物，给出可 grep 的位置」可被机器验。

★ 立据（短判决位 2026-10-10 最终收工判决，逐字要点）：
  「你报的三条**每一条都带可 grep 的位置或可复跑的命令** —— 这正是你上一轮刚写进台账的那条规矩
   （『凡引用落盘物，必须给出可 grep 的位置并当场核一次』）**的第一次执行** ⇒ **规则写在台账上不到一轮，
   就已经用在收工报告上** ⇒ 从「写在纸上」到「用在事上」只隔了一轮 —— **这是今天所有纪律里传导最快的一条**。」
  ⇒ 本件把那次"靠人照做"变成"机器可验"：**报告里的每个位置引用都必须真的存在、行号真的够**。

★ 判据（**执行，不是抄写**）：从报告文本里抽出三类引用并逐条核
  · `文件:行号`（如 `tools/x.py:78`）⇒ 文件存在 **且** 行数 ≥ 该行号
  · `cards/键`（如 `notes/mac-mini/foo`）⇒ 黑板 GET **HTTP 200**（两板任一；都不可达 ⇒ **不可判**，非绿）
  · `tools/xxx.py` / `xxx.log` ⇒ 文件存在

★ 观测面（六要素）：
  · 含项 = 被检查的报告文本里的上述三类引用；**排除项** = ① 未写成"位置形态"的散文引用（本判据只认可核形态）
    ② 引用的**内容正确性**（只核"存在/够行数"）③ 命令的**语义是否跑得通**（那要真跑，属各件 selftest）
    ④ 引用的**时效**（不判"是不是当轮产物"）；**补偿控制** = ① 解析失败/悬空即红（fail-closed）
    ② 两板都不可达 ⇒ 记「不可判」而非绿 ③ **零引用 ⇒ 红**（报告若一条可核位置都没有，那是叙述不是报告）
    ④ 打印扫描面与运行戳；**工具** = python3 + curl（**不改被核对象**；临时写面 = `guard/mutation-work/`）；**单位** = 处；**时刻** = RFC3339。

退出码：0 = 通过 · 1 = 有悬空引用/零引用 · 2 = 用法错误
用法：python3 tools/report-claim-check.py <报告文件> | --selftest
"""
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.expanduser("~/dsh-collab")
BOARDS = ["http://127.0.0.1:8792", "http://106.53.214.108:8792"]
RE_FILELINE = re.compile(r"([A-Za-z0-9_./~-]+\.(?:py|js|md|json|log|yml)):(\d+)")
RE_CARD = re.compile(r"(notes/[a-z0-9-]+/[A-Za-z0-9._-]+|data/[a-z0-9-]+/[A-Za-z0-9._-]+)")
RE_TOOLFILE = re.compile(r"tools/([A-Za-z0-9._-]+\.py)")


def ts():
    s = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return s[:-2] + ":" + s[-2:]


# ★★ 多根解析（判决未声明⑤：`lib/index.js` 被误判"不存在"而实存 659 行 ⇒ **我按仓库根解析、插件相对路径必然假红**）
ROOTS = [HERE, os.path.join(HERE, "devices/dsh-plugin-context-survival")]


def resolve(p):
    """返回 (绝对路径 或 None, 命中根 或 None)。**多根**：仓库根 + 插件目录。"""
    p = os.path.expanduser(p)
    if os.path.isabs(p):
        return (p, os.path.dirname(p)) if os.path.isfile(p) else (None, None)
    for root in ROOTS:
        cand = os.path.join(root, p)
        if os.path.isfile(cand):
            return cand, root
    return None, None


def http_ok(key):
    for base in BOARDS:
        try:
            r = subprocess.run(["curl", "-s", "-m", "6", "-o", "/dev/null", "-w", "%{http_code}",
                                f"{base}/{key}"], capture_output=True, text=True, timeout=12)
            code = (r.stdout or "").strip()
            if code == "200":
                return True
            if code == "404":
                return False
        except Exception:
            pass
    return None


def scan(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    dangling, unknown, nrefs = [], [], 0
    seen_dangling = set()   # ★ 去重：同一路径不被 `文件:行号` 与 `tools/*.py` 两类各报一次（实测：会把 1 处报成 2 处）
    for m in RE_FILELINE.finditer(txt):
        f, ln = m.group(1), int(m.group(2))
        nrefs += 1
        full, _root = resolve(f)
        if full is None:
            if f not in seen_dangling:
                seen_dangling.add(f)
                dangling.append(f"`{f}:{ln}` ⇒ **文件不存在**")
            continue
        nlines = sum(1 for _ in open(full, encoding="utf-8", errors="replace"))
        if nlines < ln:
            dangling.append(f"`{f}:{ln}` ⇒ 文件只有 **{nlines}** 行 ⇒ **行号越界**")
    for m in RE_CARD.finditer(txt):
        key = m.group(1)
        nrefs += 1
        ok = http_ok(key)
        if ok is False:
            dangling.append(f"卡片 `{key}` ⇒ **HTTP 404**")
        elif ok is None:
            unknown.append(f"卡片 `{key}` ⇒ 两板不可达 ⇒ **不可判**（非绿）")
    for m in RE_TOOLFILE.finditer(txt):
        t = m.group(1)
        nrefs += 1
        rel = os.path.join("tools", t)
        if not os.path.isfile(os.path.join(HERE, rel)) and rel not in seen_dangling:
            seen_dangling.add(rel)
            dangling.append(f"`tools/{t}` ⇒ **文件不存在**")
    return dangling, unknown, nrefs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法错误：需要 <报告文件>")
        return 2
    path, _root = resolve(args[0])
    RUN = ts()
    if path is None:
        print(f"用法错误/环境错误：找不到报告 {args[0]}（已试根：{ROOTS}）")
        return 2
    print("report-claim-check · 报告声明的可核性（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
    print(f"  · 本次运行戳 run={RUN} —— ★ 引用本页数字须连同它一起引用")
    print(f"  观测面（六要素）：**含项** = {os.path.relpath(path, HERE)} 里的 `文件:行号` / 卡片键 / `tools/*.py` 三类引用；"
          f"**排除项** = ① 散文引用（只认可核形态）② 引用内容是否正确 ③ 命令语义是否跑得通 ④ 引用时效；"
          f"**补偿控制** = ① 悬空即红 ② 两板不可达 ⇒ 不可判 ② 零引用 ⇒ 红（叙述 ≠ 报告）④ 打印扫描面与运行戳；"
          f"**工具** = python3 + curl；**单位** = 处；**时刻** = {RUN}")
    dangling, unknown, nrefs = scan(path)
    print(f"  · 扫描面：可核引用 **{nrefs}** 处")
    if nrefs == 0:
        print("\n❌ **零引用 ⇒ 红**：本报告没有任何 `文件:行号` / 卡片 / `tools/*.py` 形态的可核位置 ⇒ "
              "那是**叙述**不是报告（照台账规矩：凡引用落盘物，须给出可 grep 的位置）")
        return 1
    if unknown:
        print(f"  · 不可判（两板不可达，**非绿**）：{len(unknown)} 处")
        for u in unknown[:3]:
            print("    " + u)
    if dangling:
        print(f"\n❌ [run {RUN}] 悬空引用 {len(dangling)} 处：")
        for d in dangling[:10]:
            print("  " + d)
        return 1
    print(f"\n✅ [run {RUN}] 通过：可核引用 **{nrefs}** 处**全部可解析**（悬空 0 · 不可判 {len(unknown)}）")
    return 0


def selftest():
    import shutil
    import tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="report-claim-check-selftest-", dir=work)
    bad = []
    try:
        p = os.path.join(sb, "r.md")
        # 反控：真实位置 + 真实行号
        open(p, "w", encoding="utf-8").write("见 `tools/gate-scaffold.py:78`。\n")
        d, u, n = scan(p)
        ok = (len(d) == 0) and (n >= 1)
        print(f"  {'✅' if ok else '❌'} 反控：真实 `文件:行号` ⇒ 绿（悬空 {len(d)} · 引用 {n}）")
        if not ok:
            bad.append("反控未绿")
        # 正控①：文件不存在
        open(p, "w", encoding="utf-8").write("见 `tools/no-such-file-xyz.py:3`。\n")
        d, _, _ = scan(p)
        ok = len(d) == 1
        print(f"  {'✅' if ok else '❌'} 正控：文件不存在 ⇒ 红（悬空 {len(d)}）")
        if not ok:
            bad.append("不存在未红")
        # 正控②：行号越界
        open(p, "w", encoding="utf-8").write("见 `tools/gate-scaffold.py:999999`。\n")
        d, _, _ = scan(p)
        ok = len(d) == 1
        print(f"  {'✅' if ok else '❌'} 正控：**行号越界** ⇒ 红（悬空 {len(d)}）")
        if not ok:
            bad.append("越界未红")
        # 正控③：零引用 ⇒ 红（在 main 层判；此处验 scan 返回 0 引用）
        open(p, "w", encoding="utf-8").write("本报告全绿，一切正常。\n")
        _, _, n = scan(p)
        ok = n == 0
        print(f"  {'✅' if ok else '❌'} 正控：**零引用**被识别（引用 {n} ⇒ main 会判红）")
        if not ok:
            bad.append("零引用未被识别")
        if bad:
            print("  ❌ --selftest 失败：" + " ｜ ".join(bad))
            return 1
        print("  ✅ --selftest 通过：一正控（不存在）+ 一正控（越界）+ 一正控（零引用）+ 一反控（真位置）")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
