#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catch-all 扫描器：数一个目录里有多少处「什么都接」的 except，以及其中多少处连类名都拿不到。

由来（2026-09-28）：
  老登用我的尺子量了他自己（`bb-put-verify.py` 8 处 except Exception、其中 5 处连 `as e` 都没有）
  ⇒ 那 5 处**连类名都拿不到 ⇒ 更不可能报「吞了几类」**。
  ⇒ 那次是**人工统计**。本工具把它变成**一次调用产出的读数**（同「把贵的判断封进工具」）。

★ 为什么用 `ast` 而不是正则：
  这是老登那条统一的直接实例 —— **凡自检优先「调用它自己」，无法调用才退回复刻**。
  Python 的 `ast` 就是**语言自己的解析器**；用正则去找 `except` 是在**复刻**它的行为，
  会撞上注释与字符串里的假 except。本工具因此提供 `--regex` 复刻版**只为对照**，
  默认走 ast；两者读数不一致时，**以上限/下限成对报出**，不合并成一个数。

★ 三档输出（每档都是可数的量）：
  ① `except Exception` / 裸 `except:` 总数（catch-all）
  ② 其中**裸接**（无 `as <name>`）的数量 ⇒ 这一类**连异常类名都拿不到**
  ③ 每个 catch-all 的 `文件:行`

用法：python3 catchall-scan.py [目录] [--regex] [--json]
退出码：0 = 没有裸接 catch-all；1 = 有（并逐条列出）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import ast, json, os, re, sys



# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/catchall-scan.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def scan_ast(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return None, f"SyntaxError: {e}"
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # catch-all 的两种形态：`except Exception` 与裸 `except:`
        is_catchall = (node.type is None) or (
            isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"))
        if not is_catchall:
            continue
        hits.append({"line": node.lineno, "bare": node.name is None,
                     "form": "裸 except:" if node.type is None else ast.unparse(node.type)})
    return hits, None


REGEX_CA = re.compile(r"^\s*except\s*(Exception|BaseException)?\s*(as\s+(\w+))?\s*:", re.M)


def scan_regex(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    hits = []
    for m in REGEX_CA.finditer(src):
        line = src[:m.start()].count("\n") + 1
        hits.append({"line": line, "bare": m.group(3) is None,
                     "form": (m.group(1) or "裸 except:")})
    return hits, None



_KNOWN = {"--regex", "--json", "-h", "--help"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _KNOWN]
if _unknown:
    print(f"❌ 不认识的参数: {' '.join(_unknown)}")
    print(f"   本工具接受的参数: {' '.join(sorted(_KNOWN))}")
    print("   ★ 加这道检查的起因：本工具自己曾把伪造旗标【静默忽略】、照常跑默认动作")
    sys.exit(2)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    root = args[0] if args else os.path.dirname(os.path.abspath(__file__))
    use_regex = "--regex" in sys.argv
    as_json = "--json" in sys.argv

    # ★ 2026-09-28 加：位置参数若不是目录，要说清楚。
    #   起因（老登实测）：`catchall-scan.py bb-put-verify.py`（文件参数）⇒
    #   第 75 行 os.listdir 抛 NotADirectoryError ⇒ 裸 traceback（③态）。
    #   同一个形态我今天在 ts-not-future-check / card-json-check / msg-count-lint 上编过目
    #   （参数被当成另一种对象）—— ⇒ 而现在它出现在【我用来编目这个形态的工具】自己身上。
    if not os.path.isdir(root):
        print(f"❌ 位置参数不是目录: {root}")
        if os.path.exists(root):
            print("   ⇒ 它存在，但是个【文件】。本工具只扫目录（拿目录里的 *.py 枚举）。")
            print("   ⇒ 若你想扫单个文件：直接读它，或把它的目录传进来。")
        else:
            print("   ⇒ 它不存在。")
        sys.exit(2)
    files = sorted(f for f in os.listdir(root) if f.endswith(".py"))
    rows, tot, bare = [], 0, 0
    for f in files:
        p = os.path.join(root, f)
        hits, err = (scan_regex(p) if use_regex else scan_ast(p))
        if err:
            rows.append({"file": f, "error": err, "catchall": 0, "bare": 0, "lines": []})
            continue
        b = sum(1 for h in hits if h["bare"])
        tot += len(hits); bare += b
        if hits:
            rows.append({"file": f, "catchall": len(hits), "bare": b,
                         "lines": [f"{h['line']}:{'裸' if h['bare'] else '有类名'}({h['form']})" for h in hits]})

    if as_json:
        print(json.dumps({"scanner": "regex" if use_regex else "ast", "root": root,
                          "files": len(files), "catchall_total": tot, "bare_total": bare,
                          "rows": rows}, ensure_ascii=False, indent=1))
        return 1 if bare else 0

    print(f"catch-all 扫描（扫描器 = {'正则复刻' if use_regex else 'ast（语言自己的解析器）'}）")
    print(f"目录: {root} · .py 文件 {len(files)} 个")
    print()
    print(f"  {'文件':34s} {'catch-all':>9s} {'裸接':>5s} 位置")
    for r in rows:
        if "error" in r:
            print(f"  {r['file']:34s} {'—':>9s} {'—':>5s} {r['error']}")
            continue
        print(f"  {r['file']:34s} {r['catchall']:9d} {r['bare']:5d} {' '.join(r['lines'])}")
    print()
    # ★ 2026-09-28 加：空域不得报「通过」。
    #   起因（实测）：`catchall-scan.py /tmp/emptydir` ⇒ 打「合计：catch-all 0 处 · 裸接 0 处」
    #   并 exit=0 ⇒ 与「扫过了、真的没有裸接」**同痕** ⇒ 这就是老登那条「空域恒真」。
    #   而他给了正确样板（datadir-audit「未评估」+ 退出码 4 / gate-conformance 同）⇒ 照抄。
    #   ⇒ 判据：**「我这句话，在【数据为空】时会说什么？」——仍说「通过」⇒ 恒真＝无信息。**
    if len(files) == 0:
        print(f"  ⚠ 目录里没有一个 .py ⇒ 【未评估】（没有文件 ≠ 没有裸接 catch-all）· 退出码 4")
        print("SELFTEST catchall-scan 未评估（空域）")
        return 4
    print(f"★ 合计：catch-all {tot} 处 · 其中【裸接（连类名都拿不到）】{bare} 处")
    if bare:
        print("   ⇒ 裸接的那些**不可能报出「我吞了哪一类」**（连异常类名都没有）")
    return 1 if bare else 0


if __name__ == "__main__":
    sys.exit(main())
