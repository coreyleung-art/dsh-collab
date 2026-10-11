#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_strip_lits.py — 把已注入工具的 `_strip_lits` 替换为 **raw-string 感知** 版。

★ 为何需要（2026-10-10 自测抓到）：
  初版 `_strip_lits` 用**字符扫描**且不识别 `r` 前缀 ⇒ 对形如
  `r"open\\s*\\([^)]*['\\"]w"` 的 **raw string（其中 `\\"` 不是转义）** 剥错字符串边界，
  把模式串的一部分留在结果里 ⇒ **判据把自己的模式串当靶子** ⇒ 实测某工具 A/D 两项因此判红。

★★ 写法纪律（本文件自身就是教训的产物）：
  今晚 heredoc / 直接写「含引号的正则」已致 SyntaxError **五次**。
  ⇒ 本文件的所有引号相关常量一律用 **chr() 拼接**，源码里**不出现字面三引号**。
     `Q  = chr(34)`（双引号） · `Q3 = chr(39)*3`（三单引号）

用法：python3 guard/_fix_strip_lits.py <工具.py> [<工具.py> ...]
"""
import os
import re
import sys

# ═══ 引号常量（全部用 chr 拼接 ⇒ 源码内无字面引号）═══
D = chr(34)        # "
S = chr(39)        # '
T3 = S * 3         # '''（三单引号）
D3 = D * 3         # """（三双引号）

# ═══ 剥离用模式（v1.0.2：显式区分 raw 与普通字符串的转义语义）═══
TRIPLE_DQ_PAT = '[rRbB]?' + D3 + '(?:.|\\n)*?' + D3
TRIPLE_SQ_PAT = '[rRbB]?' + T3 + '(?:.|\\n)*?' + T3
RAW_DQ_PAT = 'r' + D + '[^' + D + '\\n]*' + D
RAW_SQ_PAT = 'r' + S + '[^' + S + '\\n]*' + S
NORM_DQ_PAT = D + '(?:[^' + D + '\\\\]|\\\\.)*' + D
NORM_SQ_PAT = S + '(?:[^' + S + '\\\\]|\\\\.)*' + S

# 生成「常量定义段」文本（写进目标文件）
CONSTS = (
    "# ═══ 剥离用模式（v1.0.2：显式区分 raw 与普通字符串的转义语义）═══\n"
    "#   ★ 常量用 chr() 拼接生成 ⇒ 源码内无字面引号（避免自伤与转义歧义）\n"
    "_D = chr(34); _S = chr(39); _T3 = _S * 3; _D3 = _D * 3\n"
    "TRIPLE_DQ = '[rRbB]?' + _D3 + '(?:.|\\\\n)*?' + _D3\n"
    "TRIPLE_SQ = '[rRbB]?' + _T3 + '(?:.|\\\\n)*?' + _T3\n"
    "RAW_DQ = 'r' + _D + '[^' + _D + '\\\\n]*' + _D\n"
    "RAW_SQ = 'r' + _S + '[^' + _S + '\\\\n]*' + _S\n"
    "NORM_DQ = _D + '(?:[^' + _D + '\\\\\\\\]|\\\\\\\\.)*' + _D\n"
    "NORM_SQ = _S + '(?:[^' + _S + '\\\\\\\\]|\\\\\\\\.)*' + _S\n"
)

# 生成「新函数实现」文本
NEW_IMPL = (
    "def _strip_lits(txt):\n"
    '    """剥离字符串字面量与整行注释（R006 A 项要求 —— 否则会把自己的检测正则当靶子）。\n'
    "\n"
    "    ★ v1.0.2 修正（自测抓到）：初版用**字符扫描**且不识别 r 前缀 ⇒ 对 raw string 里的\n"
    '      反斜杠-引号（raw 中非转义）剥错边界，把模式串的一部分留在结果里 ⇒\n'
    "      **判据把自己的模式串当靶子**（实测某工具 A/D 两项因此判红）。\n"
    "      ⇒ 改用正则，**显式区分 r 前缀**（raw 中反斜杠不转义）。\n"
    "    ★ 顺序纪律：调用方必须 **先 _apply_exempt 再 _strip_lits** ——\n"
    "      反过来的话标记行（# gate-self-exempt: begin）会被当注释剥掉 ⇒ 豁免失效。\n"
    '    """\n'
    "    t = re.sub(TRIPLE_DQ, '\\\"\\\"', txt)\n"
    "    t = re.sub(TRIPLE_SQ, '\\\"\\\"', t)\n"
    "    t = re.sub(RAW_DQ, '\\\"\\\"', t)      # ★ raw 双引号（斜杠不转义）\n"
    "    t = re.sub(RAW_SQ, '\\\"\\\"', t)\n"
    "    t = re.sub(NORM_DQ, '\\\"\\\"', t)     # 普通双引号（斜杠转义）\n"
    "    t = re.sub(NORM_SQ, '\\\"\\\"', t)\n"
    "    out = []\n"
    "    for ln in t.split('\\n'):\n"
    "        out.append('' if ln.lstrip().startswith('#') else re.sub(r'\\s+#.*$', '', ln))\n"
    "    return '\\n'.join(out)\n"
)


def fix(path):
    p = os.path.expanduser(path)
    s = open(p, encoding="utf-8").read()
    if "_strip_lits" not in s:
        print("  %-24s 无 _strip_lits（跳过）" % os.path.basename(p))
        return 0
    m = re.search(r"def _strip_lits\(txt\):(?:.|\n)*?(?=\ndef )", s)
    if not m:
        print("  %-24s 未匹配到函数体（跳过）" % os.path.basename(p))
        return 0
    s = s[:m.start()] + NEW_IMPL + s[m.end():]
    if "TRIPLE_DQ =" not in s:
        m2 = re.search(r"^ALLOWED_CMDS = \([^)]*\)\n", s, re.M)
        if m2:
            s = s[:m2.end()] + "\n\n" + CONSTS + s[m2.end():]
        else:
            m3 = re.search(r"^def ", s, re.M)
            s = s[:m3.start()] + CONSTS + "\n\n" + s[m3.start():]
    open(p, "w", encoding="utf-8").write(s)
    print("  %-24s ✓ 已替换为 raw-string 感知版 + 模式常量已注入" % os.path.basename(p))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    rc = 0
    for f in sys.argv[1:]:
        rc |= fix(f)
    sys.exit(rc)
