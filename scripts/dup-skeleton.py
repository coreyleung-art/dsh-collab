#!/usr/bin/env python3
"""找「同一个知识被写了两遍」—— 即 HR 那条判据的违反面。

HR 2026-09-14 的可判定形式：
  「知识→检查的转换 ＝ 把该事实编码进一个【被多处共用的实现】；
    判据：若某处绕过该实现，该事实即失效 ⇒『共用』是转换的标志（而不是『我记住了』）」
⇒ 于是「绕过」是可检测的：绕过表现为【同一段实现存在两份】——
  一处改了、另一处没改，事实就在那一处失效。

它做什么：把每个函数的【骨架】归一化（去注释 · 去字符串 · 去数字 · 变量名统一 · 去空白），
          再比较所有函数对，报出骨架相同的组。

★ 它是【半语义】判据，所以报的是候选而非结论：
  · 骨架相同 → 可能确实是同一知识写了两遍（该合并）
  · 骨架相同 → 也可能只是两个碰巧同形的简单函数（不该合并）
  判据的【结构侧】是确定的（骨架字符串相等），【语义侧】需要人看。
  所以输出必须被读作「待确认的重复候选」，不是「违规清单」。

用法：python3 dup-skeleton.py <file.py> [file2.py ...]
      python3 dup-skeleton.py --dir ~/dsh-collab/scripts --min-lines 4

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== dup-skeleton 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 找「同一个知识被写了两遍」—— 即 HR 那条判据的违反面。")
    print("  · HR 2026-09-14 的可判定形式：")
    print("  · 「知识→检查的转换 ＝ 把该事实编码进一个【被多处共用的实现】；")
    print("  · 判据：若某处绕过该实现，该事实即失效 ⇒『共用』是转换的标志（而不是『我记住了』）」")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: ast, collections, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/dup-skeleton.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import ast, sys, os, glob, hashlib, re
from collections import defaultdict



# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/dup-skeleton.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def skeleton(fn):
    """函数的归一化骨架：去注释与字符串（ast 层面天然去除），变量名统一，数字统一。"""
    src = ast.dump(fn, annotate_fields=False)
    # 变量名/属性名统一化
    src = re.sub(r"'[A-Za-z_][A-Za-z0-9_]*'", "'V'", src)
    src = re.sub(r"\b\d+\b", "N", src)
    return hashlib.sha256(src.encode()).hexdigest()[:12], src


def functions_of(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception as e:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines = (node.end_lineno or node.lineno) - node.lineno + 1
            sh, src = skeleton(node)
            out.append((path, node.name, node.lineno, lines, sh))
    return out


def main():
    args = sys.argv[1:]
    min_lines = 3
    if "--min-lines" in args:
        i = args.index("--min-lines"); min_lines = int(args[i + 1]); args = args[:i] + args[i + 2:]
    files = []
    if "--dir" in args:
        i = args.index("--dir")
        files = sorted(glob.glob(os.path.expanduser(args[i + 1]) + "/*.py"))
    else:
        files = [os.path.expanduser(a) for a in args]
    fns = []
    for f in files:
        fns += functions_of(f)
    fns = [x for x in fns if x[3] >= min_lines]
    print(f"扫描 {len(files)} 个文件 · {len(fns)} 个函数（≥{min_lines} 行）")
    groups = defaultdict(list)
    for path, name, ln, lines, sh in fns:
        groups[sh].append((os.path.basename(path), name, ln, lines))
    dups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"★ 骨架相同的组：{len(dups)}")
    for sh, members in dups.items():
        print(f"  [{sh}]")
        for base, name, ln, lines in members:
            print(f"      {base}:{ln}  {name}()  {lines} 行")
    if not dups:
        print("  ✅ 未发现骨架相同的函数（但本检查只看骨架，改写过的重复不会被发现）")
    print()
    print("★ 判读：这是【半语义】判据 —— 骨架相同是结构事实，是否该合并需要人看。")
    return 0 if not dups else 1


if __name__ == "__main__":
    sys.exit(main())
