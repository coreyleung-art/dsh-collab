#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence-channel-guard.py — 「退出码是不是**被观对象**的」这条证据通道的回归门（只读）。

★ 立据（星桥 2026-10-10 自述的一次险误）：
  「用 `| tail` 取 `$?` 拿到的是 **tail 的**退出码 ⇒ 红显示成绿，差点报假 bug。」
★ 为什么值得单独成门：这与本线反复出现的「两种成因同痕」是**同一族** ——
  **一条红经管道之后与一条绿长得完全一样**：退出码是唯一通道，而管道会**静默地**把它换掉。
  ★ 与之配套的写法：shell 用 `${PIPESTATUS[0]}` 或 `set -o pipefail`；
    Python 用**列表传参**（`subprocess.run([...])`，不用 `shell=True`）——
    后者在结构上就没有"管道换掉退出码"这个面。

本门查两件事（只扫**活代码**，扫描前剥离注释/字符串 —— 本机 R006 反复踩的自伤面）：
  R1 Python：同一行里既有 `shell=True` 又有管道 `|` ⇒ 该调用的 returncode 是**管道最后一个命令**的 ⇒ 红。
  R2 Shell（*.sh）：`$?` 出现在**含管道的行之后**的下一行 ⇒ 同上 ⇒ 红（建议 PIPESTATUS / pipefail）。

★★ 声明通路（**处置假红的正确手段是开声明，不是放宽判据** —— 星桥 2026-10-10 裁决）：
  弱形态（如 `set -o pipefail`：能发现失败，但**给不出被观对象的退出码**）不被判据正面认可，
  但**允许显式声明**：在上一行或同一行写注释
      `# evidence-channel-allow: pipefail — <为什么这里可以接受>`
  ⇒ 该处由「违例(红)」降为「**已声明降级(黄)**」，并**逐条打印**（不静默）。
  ★ 为什么这样不算放宽：**未声明**时仍红 ⇒ 事故形态（INC-04）不会因为这条通路而变绿；
    声明是**可审计的**（谁声明、为什么、在哪一行），而放宽是无声的。
  ★ `--strict` 下**已声明降级也算红**（给"一律不许弱形态"的场合用）。

★ 覆盖面（**显式声明不覆盖什么**，照 qk-structure-guard line 83 的惯例）：
  · 覆盖：**已落盘的** `tools/*.py`、`scripts/*.py`、`*.sh`。
  · **不覆盖**：① **未落盘的即时命令**（即"下次手打一条 `cmd | tail` 再 `echo $?`"这个发生面 —— 两层基本不相交：
    本门防的是"有人把这种写法写进仓库"，不是"下次别手打管道"）；
    ② R2 的**邻接启发式**（`$?` 与管道**不相邻**时会漏 ⇒ 假绿方向；该例未构造、未判）；
    ③ 其它退出码被替换的形态（子壳、`xargs`、`&`、`set -e` 与管道交互等）。

★ 正/反两个对照都要有（否则只是"必红的噪声"或"恒绿的摆设"）：
  · 正控（应当红）：活代码里写一行 `subprocess.run("a | b", shell=True)`
  · 反控（应当绿）：**注释里**提到 `shell=True` 与 `|`（描述历史修复）—— 这正是本仓当前的实情，
    第一版若按整行裸匹配就会把它误判成违例。

退出码：0 = 无违例 · 1 = 有违例 · 2 = 环境/用法错误
用法：python3 tools/evidence-channel-guard.py [<目录或文件> ...]    # 默认扫 tools/ 与 scripts/
"""
import os
import re
import sys

HERE = os.path.expanduser("~/dsh-collab")
DEFAULT_ROOTS = [os.path.join(HERE, "tools"), os.path.join(HERE, "scripts")]
PY_LIVE = re.compile(r"shell\s*=\s*True")
PIPE = "|"


def strip_comments_and_strings(src, is_py=True):
    """剥离注释与字符串字面量，只留**活代码**。

    ★ 为什么要剥（本门第一版就是被这个绊住的）：本仓 `scripts/g10-g11-verify.py` 等件里有
      **注释**写着「原 shell=True 仅为使用管道 |，已改为列表传参」—— 裸匹配会把这段**历史记录**
      判成现行违例（假红）。与 R006 ⑩ 的做法一致：扫描前剥离注释/字符串。
    """
    out = []
    in_s3 = in_d3 = in_s1 = in_d1 = False
    i = 0
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_s3:
            if ch == "\\" and i + 1 < len(src):
                i += 2
                continue
            if src.startswith("'''", i):
                in_s3 = False
                i += 3
                continue
            out.append(" " if ch != "\n" else "\n")
            i += 1
            continue
        if in_d3:
            if ch == "\\" and i + 1 < len(src):
                i += 2
                continue
            if src.startswith('"""', i):
                in_d3 = False
                i += 3
                continue
            out.append(" " if ch != "\n" else "\n")
            i += 1
            continue
        if in_s1 or in_d1:
            if ch == "\\" and i + 1 < len(src):
                i += 2
                continue
            if (in_s1 and ch == "'") or (in_d1 and ch == '"'):
                in_s1 = in_d1 = False
                i += 1
                continue
            out.append(" " if ch != "\n" else "\n")
            i += 1
            continue
        if src.startswith("'''", i):
            in_s3 = True
            i += 3
            out.append("   ")
            continue
        if src.startswith('"""', i):
            in_d3 = True
            i += 3
            out.append("   ")
            continue
        if ch == "#":
            while i < len(src) and src[i] != "\n":
                i += 1
            continue
        if is_py and ch == "'":
            in_s1 = True
            i += 1
            out.append(" ")
            continue
        if ch == '"':
            in_d1 = True
            i += 1
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def iter_files(roots):
    for r in roots:
        if os.path.isfile(r):
            yield r
            continue
        if not os.path.isdir(r):
            continue
        for name in sorted(os.listdir(r)):
            if name.endswith((".py", ".sh")):
                yield os.path.join(r, name)


ALLOW_MARK = "evidence-channel-allow:"


def has_declaration(lines, idx):
    """上一行或同一行是否有**显式声明**（照文件头的「声明通路」）。"""
    for j in (idx - 1, idx - 2):
        if 0 <= j < len(lines) and ALLOW_MARK in lines[j]:
            return True
    return False


def check(roots, strict=False):
    bad, scanned, noted = [], 0, []
    for path in iter_files(roots):
        scanned += 1
        try:
            raw = open(path, encoding="utf-8", errors="replace").read()
        except Exception as e:
            bad.append(f"[读取失败] {path}: {e}")
            continue
        is_py = path.endswith(".py")
        live = strip_comments_and_strings(raw, is_py)
        # ★★ 两个视图、各答一个问题（本门第二版才想通，第一版因此**恒绿**）：
        #   · `live` 行回答「`shell=True` 是不是**活代码**」——注释里的不算（防假红）；
        #   · `raw`  行回答「这条语句里**有没有管道**」——管道**本来就在命令字符串里**，
        #     若拿 live 视图去判，字符串被抹掉 ⇒ 管道看不见 ⇒ **假绿**（第一版的真身）。
        #   ⇒ 必须 raw 与 live **同下标**合判。剥离器保留行结构，故下标一一对应。
        raw_lines = raw.split("\n")
        for i, line in enumerate(live.split("\n"), 1):
            raw_line = raw_lines[i - 1] if i - 1 < len(raw_lines) else ""
            if is_py and PY_LIVE.search(line) and PIPE in raw_line:
                bad.append(f"[R1] {os.path.relpath(path, HERE)}:{i} 活代码里 `shell=True` 与管道同行"
                           f" ⇒ 该调用 returncode 是**管道最后一条命令**的（不是被观对象的）"
                           f" ⇒ 建议改**列表传参**，或显式使用 PIPESTATUS/pipefail")
            # ★★ R2 的两个视图**方向与 R1 相反**，别照抄（星桥判决 D 实证的假红正是照抄出来的）：
            #   · 当前行：`$?` 常**写在引号里**（`echo "exit=$?"`）⇒ 内容判定必须看 **raw**（看 live 会假绿）；
            #   · 上一行：管道写在**字符串里不算管道**（`echo "a|b"` 不是管道）⇒ 管道判定必须看 **live**
            #     （看 raw 会把字符串里的 | 当管道 ⇒ **假红**；判决 D 的案例 A 就是这一例）。
            if (not is_py) and "$?" in raw_line and line.strip() != "":
                prev_live = live.split("\n")[i - 2] if i >= 2 else ""
                if PIPE in prev_live and prev_live.strip() != "" and not prev_live.lstrip().startswith("#"):
                    msg = (f"[R2] {os.path.relpath(path, HERE)}:{i} `$?` 紧随含管道的上一行"
                           f" ⇒ 拿到的是管道末端的退出码 ⇒ 应用 `${{PIPESTATUS[0]}}` 精确取被观对象；"
                           f"`set -o pipefail` **不能**替代它（它给的是整条管道的末位非零码，仍不是被观对象的）")
                    if has_declaration(raw_lines, i - 1):
                        if strict:
                            bad.append(msg + " —— ★ 本处**已声明**弱形态，但 `--strict` 下声明亦算红")
                        else:
                            noted.append(msg + " —— **已声明降级（黄）**：请确认声明理由仍然成立")
                    else:
                        bad.append(msg + " —— 若确要用弱形态，须**显式声明**（见文件头「声明通路」）")
    return bad, scanned, noted


def selftest():
    """★ 自证：四条对照（两条正控必红 + 两条反控必绿）都在**沙箱**里造，真仓只读。"""
    import shutil, tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="evchan-selftest-", dir=work)
    cases = []
    try:
        # 正控 1：活代码 shell=True + 管道 ⇒ 红
        d = os.path.join(sb, "c1"); os.makedirs(d)
        open(os.path.join(d, "s.py"), "w", encoding="utf-8").write(
            'import subprocess\nsubprocess.run("echo a | tail -1", shell=True)\n')
        cases.append(("正控1 活代码 shell=True+管道 ⇒ 应红", d, True))

        # 反控 1：该写法只出现在注释/字符串里 ⇒ 绿（本仓当前的实情）
        d = os.path.join(sb, "c2"); os.makedirs(d)
        open(os.path.join(d, "s.py"), "w", encoding="utf-8").write(
            '# 历史：原 subprocess.run("a | b", shell=True) 已改列表传参\nHELP = "不要用 shell=True 配管道 | 取退出码"\n')
        cases.append(("反控1 只在注释/字符串里提及 ⇒ 应绿", d, False))

        # 正控 2：壳脚本里管道后取 $? ⇒ 红
        d = os.path.join(sb, "c3"); os.makedirs(d)
        open(os.path.join(d, "x.sh"), "w", encoding="utf-8").write('#!/bin/sh\nfoo | tail -1\necho "exit=$?"\n')
        cases.append(("正控2 壳脚本 管道后取 $? ⇒ 应红", d, True))

        # ★ 真阴性反控（星桥判决 C：缺的恰好是最该有的那条）：**正确写法**必须被判据正面认可
        d = os.path.join(sb, "c5"); os.makedirs(d)
        open(os.path.join(d, "z.sh"), "w", encoding="utf-8").write(
            '#!/bin/sh\nfoo | tail -1\necho "rc=${PIPESTATUS[0]}"\n')
        cases.append(("反控3 正确写法 ${PIPESTATUS[0]} ⇒ 应绿", d, False))

        # 弱形态两态：未声明 ⇒ 红（事故形态不得变绿）；已声明 ⇒ 黄（非红，但必须被打印出来）
        d = os.path.join(sb, "c6"); os.makedirs(d)
        open(os.path.join(d, "w1.sh"), "w", encoding="utf-8").write(
            '#!/bin/sh\nset -o pipefail\nfoo | tail -1\necho "rc=$?"\n')
        cases.append(("正控3 弱形态 pipefail **未声明** ⇒ 应红", d, True))

        d = os.path.join(sb, "c7"); os.makedirs(d)
        open(os.path.join(d, "w2.sh"), "w", encoding="utf-8").write(
            '#!/bin/sh\nset -o pipefail\n# evidence-channel-allow: pipefail — 本处只需判"失败与否"，不需归因到哪一段\nfoo | tail -1\necho "rc=$?"\n')
        cases.append(("反控4 弱形态 pipefail **已声明** ⇒ 应黄(非红)", d, False))

        # 反控 2：壳脚本里只在注释里提及 ⇒ 绿
        d = os.path.join(sb, "c4"); os.makedirs(d)
        open(os.path.join(d, "y.sh"), "w", encoding="utf-8").write('#!/bin/sh\n# 原写 foo | tail -1 后取 $? 已改 PIPESTATUS\nfoo\necho ok\n')
        cases.append(("反控2 壳脚本注释里提及 ⇒ 应绿", d, False))

        okall = True
        for name, d, want_red in cases:
            bad, _, noted = check([d])
            state = "红" if bad else ("黄(已声明降级)" if noted else "绿")
            good = (state.startswith("红")) == want_red
            okall = okall and good
            print(f"  {'✅' if good else '❌'} {name}（实得 {state}）")
        if not okall:
            print("  ❌ --selftest 失败：判据与预期不符")
            return 1
        print("  ✅ --selftest 通过：三条正控均红 / 四条反控（含**真阴性** PIPESTATUS 与**已声明弱形态**）均非红"
              " ⇒ 既不恒绿、也不误伤历史注释，且事故形态不因声明通路而变绿")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    strict = "--strict" in sys.argv
    roots = [a for a in sys.argv[1:] if not a.startswith("--")] or DEFAULT_ROOTS
    bad, scanned, noted = check(roots, strict=strict)
    print("evidence-channel-guard · 退出码通道（只读；扫描前剥离注释/字符串）")
    # ★ 观测面五要素（gate-scaffold audit 的 H3 项；判决 B 指出本件缺它 —— 按骨架补齐，不是挪词）
    import datetime as _dt
    _t = _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    print(f"  观测面：**含项** = {scanned} 个文件（**已落盘**的 tools/ scripts/ 下 .py/.sh）；"
          f"**排除项** = ① 未落盘的即时命令（本门防的是「有人把这种写法写进仓库」，不是「下次别手打管道」）"
          f"② R2 的邻接启发式（`$?` 与管道不相邻时会漏 ⇒ 假绿方向）③ 其它退出码被替换的形态（子壳/xargs/&/set -e）"
          f"；**补偿控制** = ① 声明通路只降为**黄**、不放行 ② 判据用**两视图**（live/raw）防字符串剥离造成恒绿"
          f" ③ `--strict` 供收紧用、默认不放宽"
          f"；**工具** = python3 静态扫描（剥离注释与字符串）；**单位** = 文件 · 行；**时刻** = {_t[:-2] + ':' + _t[-2:]}")
    print(f"  扫描：{scanned} 个文件 · 根：{', '.join(os.path.relpath(r, HERE) for r in roots)}"
          f"{' · --strict（声明亦算红）' if strict else ''}")
    if noted:
        print("\n⚠️ 已声明降级（黄 · 逐条列出，不静默）：")
        for n in noted:
            print("  " + n)
    if bad:
        print("\n❌ 违例：")
        for b in bad:
            print("  " + b)
        return 1
    print("\n✅ 通过：活代码里没有「shell=True + 管道」；shell 脚本里没有「管道后取 $?」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
