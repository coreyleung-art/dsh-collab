#!/usr/bin/env python3
"""card-json-check.py 的三向验收（must_pass / must_reject / must_differ）。
三向对应三类规则失效：过严 / 过宽 / 无观测。
用法：python3 card-json-check-selftest.py
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, subprocess, sys, tempfile, os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/card-json-check-selftest.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "card-json-check.py")

PASS_CASES = {
    "含中文":        {"key": "t", "value": {"标题": "中文标题", "正文": "标点：，。；！？（）【】「」"}},
    "含嵌套":        {"key": "t", "value": {"a": {"b": {"c": {"d": [1, 2, {"e": "深五层"}]}}}}},
    "含长字符串":     {"key": "t", "value": {"content": "长" * 4000}},
    "键名含数字":     {"key": "t", "value": {"r1_口径": "x", "2026": "z"}},
    "含转义与制表":   {"key": "t", "value": {"path": "~/x\\y", "nl": "l1\nl2"}},
}
REJECT_RAW = {
    "值里含ASCII双引号": '{"key":"k","value":{"bad":"这里有个 " 裸引号"}}',
    "结构错_缺右括号":   '{"key":"k","value":{"a":1}',
    # ★ 形态4：来自 2026-09-14 的真实失效（key 后直接逗号，漏了 : 与 value）
    "结构错_漏冒号":     '{"key":"k",\n  "这一行只有key没有值",\n  "b":2}',
    # ★ 形态6：来自 2026-09-14 的真实失效（用单引号收尾导致字符串未闭合）
    #   判据应用：本失效【可由本工具产生】（它是 JSON 语法错）⇒ 属于本判据 ⇒ 入此集合。
    "结构错_引号未闭合":  '{"key":"k","value":{"a":"值。\'}}',
    # ★ 形态5（正则写错导致 0 命中）【不属于本判据】，故不在此集合 —— 见文件末尾说明。
}

def run(p):
    r = subprocess.run([sys.executable, CHECK, p], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    return ("✅" in out and r.returncode == 0), out.splitlines()[0][:80] if out else "(无输出)"

def main():
    d = tempfile.mkdtemp(prefix="cardjson-")
    print("=== must_pass：合法卡必须全部通过（排除【过严】）===")
    n = ok = 0
    for name, card in PASS_CASES.items():
        p = os.path.join(d, name + ".json")
        json.dump(card, open(p, "w"), ensure_ascii=False)
        good, line = run(p)
        n += 1; ok += good
        print(f"  {'通过' if good else '★误报'}  {name:14} | {line}")
    print(f"  must_pass: {ok}/{n}\n")

    print("=== must_reject：非法卡必须被拦（排除【过宽】）===")
    n2 = ok2 = 0
    for name, raw in REJECT_RAW.items():
        p = os.path.join(d, name + ".json")
        open(p, "w").write(raw)
        good, line = run(p)          # good=True 表示"通过了检查"，这里我们要的是没通过
        caught = not good
        n2 += 1; ok2 += caught
        print(f"  {'拦住' if caught else '★漏过'}  {name:16} | {line}")
    print(f"  must_reject: {ok2}/{n2}\n")

    print("=== must_differ：合法与非法必须给出不同判定（排除【无观测】）===")
    p1 = os.path.join(d, "ok.json"); json.dump({"key": "t", "value": {"a": "b"}}, open(p1, "w"))
    p2 = os.path.join(d, "bad.json"); open(p2, "w").write(REJECT_RAW["值里含ASCII双引号"])
    a, _ = run(p1); b, _ = run(p2)
    differ = (a != b)
    print(f"  {'有区分' if differ else '★无区分'}  合法卡判定={a} · 非法卡判定={b}")
    print(f"  must_differ: {'1/1' if differ else '0/1'}\n")

    allgood = (ok == n) and (ok2 == n2) and differ
    print(f"总判定: {'全绿' if allgood else '★有失败项'}")
    return 0 if allgood else 1

if __name__ == "__main__":
    sys.exit(main())

# ── 关于【哪些失效属于本判据】的说明（2026-09-14 明鉴补，来自一次真实的错误）──
# 我曾把「用前 8 字符 startswith 匹配导致 0 命中」也塞进 REJECT_RAW。
# 那张卡是【合法 JSON】，所以 must_reject 判定为「漏过」⇒ 3/4 ⇒ 总判定失败。
# 错不在那张卡，在于：该失效【不可能由本工具产生】—— card-json-check.py 只做 JSON 检查，
# 它不会去做字符串匹配。所以那是【另一个判据】的失效面。
# 判据（补）：加测试用例前，先问「这个失效可否由本工具产生？」
#   可 ⇒ 属于本判据，入对应集合。
#   不可 ⇒ 它属于别的工具/判据，塞进来就是让测试集【过宽】。
# 这正是三向失效里的「过宽」发生在测试集自己身上。
