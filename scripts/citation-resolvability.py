#!/usr/bin/env python3
# citation-resolvability.py — 「引用自检三问」第②问的机械实现：路径/名字是全名吗？
#
# 由来（2026-10-08，实测）：移交包里写 `dsh-tool-cordis/lib/index.js:6898`，第三人照此路径读
# **第一跳就 not found**（真实路径需补 npm scope 与 runtime 根）。核实是真的，但它**没留在可解路径上**。
#
# ★ 本脚本立意的关键（第一次实作用 os.path.exists 就错了）：
#   可解析性必须相对 **文档声明的解析根** 判定，而不是相对 **作者自己知道的根**。
#   实测：`dsh-tool-cordis/lib/index.js` 配上作者知道的 @deepseek-ai 根在我盘上存在 ⇒ 判「可解析」，
#   但那个根**文档里没写** ⇒ 第三人仍 not found。把「我知道的」当成「文档说了的」= 假绿。
#
# ★ 另一个实测教训：naive 版双向不可靠 —— 它把两类**非引证**误报为不可解析：
#   · 模板占位符（`~/dsh-collab/logs/dsh-plugin-<slug>.log`，是 N5 命名规则不是引证）
#   · 多行号后缀（`.../index.js:556,563,724`，旧正则只剥单行号 ⇒ 尾巴当路径 ⇒ 假 not found）
#   故本版显式排除占位符、显式解析多行号。
#
# ★ 残余局限（实测暴露）：本脚本**分不出「声明为非路径的片段」与「写坏的引证」**。
#   实测：我把 ps 命令行片段 `dsh/lib/bin.js web` 加了反引号 ⇒ 被判不可解析。
#   正确做法是**片段不加引证格式**（不是把扫描器放行）——否则等于给自己开豁免口子。
#
#   · 第三类良性真阳性（**保留告警、不改文档**）：对**已删除/历史**构件的引用。实测 `lib/core.js` 被判
#     不可解析，但 README 已明写「`lib/core.js` 不再存在」、CHANGELOG 写「删除 `lib/core.js`」——
#     那是**路径**（只是历史路径），加反引号是正确写法，去掉反引号反而降低清晰度 ⇒ 不改。
#     ⇒ 本脚本**分不出这三类**，一律报出来让**人**判；人的判必须留痕（本条即留痕）。
#       这不是开豁免口子：告警仍然可见，只是不再重复调查。
#
# 用法：python3 citation-resolvability.py <文档> [--roots a b ...] [--selftest]
# 退出码：0 全部可解析 / 1 有不可解析引用（需人工改） / 2 用法或 IO 错误 / 3 自证矩阵失败
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#

import os
import re
import sys

# 文档形如 `path` 或 `path:LINE`
CITE_RE = re.compile(r'`([^`\n]+?)`')
PATHISH = re.compile(r'^(~?/|[\w.@-]+/)')  # 含目录分隔 ⇒ 像路径
PLACEHOLDER = re.compile(r'<[^>]+>')      # <slug> <node> 等模板占位
SUFFIX = re.compile(r':\d+(?:[,，]\d+)*(?:-\d+)?$')

# 文档**声明**的解析根：写进文档的、第三人能自己复制的根。
# ★★ 2026-10-08 自证负控抓到本脚本自己的 bug（留痕）：初版把 runtime 的 @deepseek-ai 根写进这里，
#    于是 `dsh-tool-cordis/lib/index.js` 被「作者私有知识」救活、判为可解析 —— **它复现了它要抓的缺陷**。
#    （与 R047 那次同源：把「我的测量条件」当成「对象的属性」）。
#    故：默认根只含**文档正文能读到**者；其余一律须由 --roots 显式给，或由文档自己写明全路径。
#    完整 runtime 路径请在文档里写全（本移交给已如此修），不要指望读者猜根。
DECLARED_ROOTS = ['~', '~/dsh-collab']



# ★ 机械修法（2026-10-08）：剥离 argv 的解释器前缀
#   反例：plist 的 ProgramArguments 写作「/bin/bash ~/x.sh」⇒ 整串被当路径 ⇒ 误报不可解析
#   实证：cld-maintenance-restart.sh 确实存在，而解析器报 not found（误报）
INTERP_PREFIXES = ("/bin/bash ", "/bin/sh ", "/usr/bin/python3 ", "/usr/bin/env ", "/opt/homebrew/bin/node ")
def _strip_interp(s):
    for p_ in INTERP_PREFIXES:
        if s.startswith(p_):
            return s[len(p_):].strip()
    return s

def strip_suffix(s):
    return SUFFIX.sub('', s)


def resolve(cite, roots):
    """返回 (可解析?, 用了哪个根)。只用文档声明的根，不用作者私有知识。"""
    p = strip_suffix(_strip_interp(cite))
    if p.startswith('~'):
        p = os.path.expanduser(p)
    if os.path.isabs(p):
        return os.path.exists(p), '绝对路径'
    for r in roots:
        rp = os.path.join(os.path.expanduser(r), p)
        if os.path.exists(rp):
            return True, r
    return False, None


def scan(text, roots):
    cites = set()
    for m in CITE_RE.finditer(text):
        s = m.group(1).strip()
        if not PATHISH.match(s) and not s.startswith('~'):
            continue
        if PLACEHOLDER.search(s):
            continue          # 模板占位符不是引证
        if re.search(r'\.\.\.|\(|\)|\|', s):
            continue          # 省略号/括号/管道 ⇒ 正则或 shell 片段，非引证
        if not re.search(r'\.[a-z]{2,4}\b\s*$', s.rstrip(':0123456789-, ')):
            continue          # 结尾须是扩展名 ⇒ 排除正则字面量等
        cites.add(s)
    bad, good = [], []
    for s in sorted(cites):
        ok, root = resolve(s, roots)
        (good if ok else bad).append((s, root))
    return good, bad


def selftest():
    """自证矩阵：负控必须红、正控必须绿、两类假阳必须被排除。"""
    cases = [
        ('正控', '见 `/Applications/CLD.app/Contents/MacOS/CLD` 与 `~/dsh-collab/rules-registry/rules.json`', 0),
        ('负控-不可解', '见 `dsh-tool-cordis/lib/index.js:6898`', 1),
        ('正控-全名绝对路径', '见 `~/.dsh/profiles/node_modules/@deepseek-ai/dsh-tool-cordis/lib/index.js`', 0),
        ('负控-多行号', '见 `~/dsh-collab/rules-registry/nope.js:556,563,724`', 1),
        ('假阳排除-占位符', '见 `~/dsh-collab/logs/dsh-plugin-<slug>.log`', 0),
        ('假阳排除-多行号可解', '见 `~/dsh-collab/rules-registry/rules.json:556,563`', 0),
    ]
    fails = 0
    for name, text, expect_bad in cases:
        _, bad = scan(text, DECLARED_ROOTS)
        got = 1 if bad else 0
        ok = got == expect_bad
        fails += 0 if ok else 1
        print('  %s %-22s 期望不可解析=%d 实得=%d' % ('✓' if ok else '✗', name, expect_bad, got))
    print('  自证：%d/%d %s' % (len(cases) - fails, len(cases), 'PASS' if not fails else 'FAIL'))
    return 0 if not fails else 3


def main(argv):
    if '--selftest' in argv:
        return selftest()
    args = [a for a in argv[1:] if not a.startswith('--')]
    if not args:
        sys.stderr.write('用法: citation-resolvability.py <文档> [--selftest]\n')
        return 2
    roots = DECLARED_ROOTS
    if '--roots' in argv:
        i = argv.index('--roots')
        roots = argv[i + 1:] or roots
    total_bad = 0
    for path in args:
        try:
            text = open(path, encoding='utf-8').read()
        except OSError as err:
            sys.stderr.write('读取失败 %s: %s\n' % (path, err))
            return 2
        # 读者可**推断**的根：文档自身目录 + 最近的包根（向上找 package.json）+ 其间的祖先
        d = os.path.dirname(os.path.abspath(path))
        infer = [d]
        cur = d
        for _ in range(6):
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            infer.append(parent)
            if os.path.exists(os.path.join(parent, 'package.json')):
                break
            cur = parent
        good, bad = scan(text, roots + infer)
        print('%s —— 路径类引用 %d 条：可解析 %d / **不可解析 %d**' % (path, len(good) + len(bad), len(good), len(bad)))
        for s, _root in bad:
            print('  ✗ %s   （照此跑会 not found；请补全名，或在文档里声明解析根）' % s)
        total_bad += len(bad)
        print('  解析根（**文档须自行声明，第三人才可复跑**）：%s' % ' · '.join(roots))
    return 1 if total_bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

# ── 自证（形态①：argv 前缀误报已消除）──
# 运行：python3 citation-resolvability.py <doc.md>
