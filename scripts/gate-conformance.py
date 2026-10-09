#!/usr/bin/env python3
"""gate-conformance —— 门的验收回归运行器（2026-09-14 老登 aa528267）

立据（HR 门三件套）：门的验收须报 **(所需值的类型/条数, 最小满足样本, 真实样本)**。
对偶关系：**数的反例是边界例；门的反例是最小满足例**。

★ 本工具的核心约定：**基线 ≠ 规格**。
  每条用例同时记 expect_baseline（当前实际输出）与 expect_should（应为的输出），
  运行器把两者**分开报**：
    · 与 baseline 一致 ⇒ 该门行为未变（回归保护）
    · 与 should 一致   ⇒ 该门达到期望
  若把 baseline 当规格，回归集会**把缺陷固化成规格** —— 这正是本工具要防的事。

用法: gate-conformance.py [--cases FILE] [--lint PATH] [--json]
退出码: 0 = 全部与 expect_should 一致 · 1 = 存在与 should 不符的用例（已知缺口）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, subprocess, sys, tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/gate-conformance.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CASES_DEFAULT = "~/dsh-collab/scripts/gate-conformance-cases.json"
LINT_DEFAULT = "~/dsh-collab/scripts/absence-claim-lint.py"


def verdict_of(lint, card):
    """跑权威 lint 取 verdict；无法判定时返回 'unsupported'（供语言边界用例使用）"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False)
        p = f.name
    try:
        r = subprocess.run([sys.executable, lint, "--file", p], capture_output=True, text=True, timeout=60)
        out = (r.stdout or "") + (r.stderr or "")
        # 稳健解析：优先读汇总行的 pass/warn/fail 计数（不依赖 [FAIL] 标记文本）
        m = re.search(r"pass=(\d+)\s*·\s*warn=(\d+)\s*·\s*fail=(\d+)", out)
        if m:
            _, w, f = (int(x) for x in m.groups())
            return "fail" if f > 0 else ("warn" if w > 0 else "pass")
        # ★ 显式 [PASS] 也要被识别（否则「通过不可观测」—— 只认失败标记）
        for v in ("PASS", "FAIL", "WARN"):
            if f"[{v}]" in out:
                return v.lower()
        return f"unknown(rc={r.returncode})"
    finally:
        try: os.remove(p)
        except Exception: pass


def matches(expect, actual):
    """expect 可为 'pass' / 'warn' / 'fail' / 'warn-or-fail' / 'unsupported'"""
    if expect == actual:
        return True
    if expect == "warn-or-fail" and actual in ("warn", "fail"):
        return True
    return False



def selftest():
    """★ selftest：覆盖码 1（与期望不符）· 4（无输入）· 0（全部与期望一致）。
    用**临时用例集与临时门脚本**，不触碰真实制品。
    """
    import tempfile, shutil
    me = os.path.abspath(__file__)
    T = tempfile.mkdtemp(prefix="gc-selftest-")
    def run(args):
        r = subprocess.run([sys.executable, me] + args, capture_output=True, text=True)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    # 桩门：读 --file 卡片里的 "verdict" 字段并原样输出标记
    stub = os.path.join(T, "stub-gate.py")
    # 单行桩门（避免多行转义问题）：读卡里的 verdict 字段并打印标记
    open(stub, "w").write(
        "import argparse,json,sys;ap=argparse.ArgumentParser();"
        "ap.add_argument('--file');ap.add_argument('--json-out');a=ap.parse_args();"
        "v=json.load(open(a.file,encoding='utf-8')).get('verdict','pass');"
        "print('['+v.upper()+']')")
    def cases(rows, tag="cases"):
        f = os.path.join(T, f"{tag}.json")   # ★ 每组用例**各自一个文件**（否则后者会覆盖前者）
        json.dump({"schema": "gate-conformance-cases/v1", "cases": rows}, open(f, "w", encoding="utf-8"), ensure_ascii=False)
        return f
    good = cases([{"id": "S1", "name": "桩·应为 pass", "card": {"verdict": "pass"},
                   "expect_baseline": "pass", "expect_should": "pass", "rationale": "selftest"}], "good")
    bad = cases([{"id": "S2", "name": "桩·应为 warn 但实得 pass", "card": {"verdict": "pass"},
                  "expect_baseline": "pass", "expect_should": "warn", "rationale": "selftest"}], "bad")
    empty = os.path.join(T, "empty.json")
    json.dump({"cases": []}, open(empty, "w", encoding="utf-8"))
    specs = [
        ("码0·全部与期望一致", ["--cases", good, "--lint", stub], 0),
        ("must_reject·码1 与期望不符", ["--cases", bad, "--lint", stub], 1),
        ("must_reject·码4 用例文件不存在", ["--cases", os.path.join(T, "nope.json"), "--lint", stub], 4),
        ("must_reject·码4 用例集为空", ["--cases", empty, "--lint", stub], 4),
        ("must_reject·码4 被测门不存在", ["--cases", good, "--lint", os.path.join(T, "nope.py")], 4),
    ]
    r = []
    for name, args, exp in specs:
        got, out = run(args)
        r.append((name, got, exp, out))
    shutil.rmtree(T, ignore_errors=True)
    ok = sum(1 for _, got, exp, _ in r if got == exp)
    for name, got, exp, out in r:
        mark = "✅" if got == exp else "❌"
        print(f"  {mark} {name}  期望 exit={exp} / 实得 {got}")
        if got != exp:
            tail = " | ".join((out or "").strip().splitlines()[-3:])
            print(f"       内层输出尾部：{tail[:240]}")
    print(f"\nselftest {ok}/{len(r)}")
    return ok, len(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=CASES_DEFAULT)
    ap.add_argument("--lint", default=LINT_DEFAULT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        ok, tot = selftest(); sys.exit(0 if ok == tot else 2)
    cp = os.path.expanduser(a.cases)
    if not os.path.exists(cp):
        print(f"⚠️ 无输入：用例文件不存在（{cp}）⇒ **未评估** · 退出码 4"); sys.exit(4)
    cases = json.load(open(cp, encoding="utf-8"))
    if not cases.get("cases"):
        print("⚠️ 无输入：用例集为空 ⇒ **未评估**（没有用例 ≠ 全部通过）· 退出码 4"); sys.exit(4)
    lint = os.path.expanduser(a.lint)
    if not os.path.exists(lint):
        print(f"⚠️ 无输入：被测门不存在（{lint}）⇒ **未评估** · 退出码 4"); sys.exit(4)
    rows, ok_should, ok_base = [], 0, 0
    lack = [c.get("id", "?") for c in cases["cases"]
            if not all(k in c for k in ("id", "card", "expect_baseline", "expect_should"))]
    if lack:
        print(f"❌ 用例不合规（缺必填字段 id/card/expect_baseline/expect_should）：{lack} · 退出码 5")
        sys.exit(5)
    for c in cases["cases"]:
        act = verdict_of(lint, c["card"])
        b, s = matches(c["expect_baseline"], act), matches(c["expect_should"], act)
        ok_base += b; ok_should += s
        rows.append({"id": c["id"], "name": c["name"], "actual": act,
                     "baseline": c["expect_baseline"], "should": c["expect_should"],
                     "与基线一致": b, "与期望一致": s, "rationale": c.get("rationale", "")})
    res = {"lint": lint, "cases": len(rows), "与基线一致": ok_base, "与期望一致": ok_should,
           "required_values_declared": cases.get("required_values_declared"), "rows": rows}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"门的验收回归 · {lint}")
        print(f"所需值（三件套①）：{cases.get('required_values_declared')}")
        print(f"\n{'用例':<6}{'实际':<20}{'基线':<18}{'应为':<18}{'基线':<6}{'期望'}")
        for r in rows:
            print(f"{r['id']:<6}{r['actual']:<20}{r['baseline']:<18}{r['should']:<18}"
                  f"{'✓' if r['与基线一致'] else '✗':<6}{'✓' if r['与期望一致'] else '✗'}")
        print(f"\n与基线一致 {ok_base}/{len(rows)} · **与期望一致 {ok_should}/{len(rows)}**")
        print("★ 注：与基线不一致 = 门的行为已变（需复核）；与期望不一致 = 已知缺口或门过严。")
        print("★ 二者分开报，**不得把基线当规格**。")
    sys.exit(0 if ok_should == len(rows) else 1)


main()
