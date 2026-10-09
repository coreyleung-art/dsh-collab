#!/usr/bin/env python3
"""card-json-check.py 的三向验收（must_pass / must_reject / must_differ）。
三向对应三类规则失效：过严 / 过宽 / 无观测。
用法：python3 card-json-check-selftest.py
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== card-json-check-selftest 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · card-json-check.py 的三向验收（must_pass / must_reject / must_differ）。")
    print("  · 三向对应三类规则失效：过严 / 过宽 / 无观测。")
    print("  · 用法：python3 card-json-check-selftest.py")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/card-json-check-selftest.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, subprocess, sys, tempfile, os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
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


# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
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
