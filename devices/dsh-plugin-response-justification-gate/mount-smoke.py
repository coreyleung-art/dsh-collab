#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mount-smoke.py — 回应正当性门 · **真挂载冒烟**（R006 ① · 四态如实分报）

为何单独成器
    R006 ① 要求「**真挂载冒烟**的 pass/fail/skipped/timeout **四态如实分报**」。
    ★ 「真挂载」= **真的把被测对象调起来并观测其行为**，而非静态阅读源码。
    ★ 本门是 P3 独立 CLI（非常驻插件）⇒ 对它的「真挂载」= **真的以子进程方式
      调用其各入口，并核对退出码与输出**（等价于插件的 mount，只是挂载面是 CLI）。

★ 四态定义（★ 不做折算 —— skipped/timeout **不折算为通过**）
    pass     用例真跑且结论与期望一致
    fail     用例真跑但结论与期望不一致
    skipped  环境不满足前置条件（如缺解释器）⇒ 如实标记，**不计入通过**
    timeout  用例超时 ⇒ 如实标记，**不计入通过**

★ 为何必须真跑（本机教训）：静态阅读会漏「代码在但入口没接上」这类缺陷 ——
    本线今日已实测多次同形（工具已登记而 agent 找不到 · 函数已加而旗标未注册）。

用法
    python3 mount-smoke.py              # 全量四态报告
    python3 mount-smoke.py --json       # 机器可读
    python3 mount-smoke.py --help
    python3 mount-smoke.py --version

退出码
    0 = 无 fail 且无 timeout（skipped 允许，但会显式列出）
    1 = 有 fail 或 timeout
    2 = 用法错误
"""

__version__ = '1.0.0'

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "response-justification-gate.py")
TIMEOUT_SEC = 20

POS = ("justified", {"to": "x", "thread": "y", "text": "z", "refs": ["a"],
                     "claimed_r": "R1",
                     "quadruple": {"to": True, "thread": True, "refs": True, "text": True}})
NO_R = ("no_r", {"to": "x", "thread": "y", "text": "z", "refs": ["a"],
                 "claimed_r": None,
                 "quadruple": {"to": True, "thread": True, "refs": True, "text": True}})
BAD_Q = ("bad_q", {"to": "x", "thread": "y", "text": "z", "refs": [],
                   "claimed_r": "R2",
                   "quadruple": {"to": True, "thread": False, "refs": True, "text": True}})

# (用例名, argv, 期望退出码, 输出须含, 输出须不含)
CASES = (
    ("CLI.正例.enforced",        ["--check", "@no_r", "--mode", "enforced"], None, None, None),  # 占位，见下
)

# ★ 显式构造（避免上面的占位写法产生歧义）
def build_cases(tmp):
    import json as _j
    paths = {}
    for name, obj in (POS, NO_R, BAD_Q):
        p = os.path.join(tmp, "%s.json" % name)
        with open(p, "w", encoding="utf-8") as f:
            _j.dump(obj, f, ensure_ascii=False)
        paths[name] = p
    return (
        ("① --version 与 banner 同源",
         ["--version"], 0, ["1.0.0"], []),
        ("② --negative-control 全拒",
         ["--negative-control"], 0, ["已拒", "0 FAIL"], ["误放行"]),
        ("③ enforced·有R ⇒ 放行(exit 0)",
         ["--check", paths["justified"], "--mode", "enforced"], 0, ["结构性正当"], []),
        ("④ enforced·无R ⇒ ★拒绝(exit 3)",
         ["--check", paths["no_r"], "--mode", "enforced"], 3, ["拒绝"], ["可发送"]),
        ("⑤ enforced·四元组不全 ⇒ ★拒绝(exit 3)",
         ["--check", paths["bad_q"], "--mode", "enforced"], 3, ["拒绝"], ["可发送"]),
        ("⑥ enforced·无R+force ⇒ 放行但带标注",
         ["--check", paths["no_r"], "--mode", "enforced", "--force-send"], 0,
         ["无 §2 依据"], []),
        ("⑦ advisory·无R ⇒ 记录不阻断(exit 0)",
         ["--check", paths["no_r"], "--mode", "advisory"], 0, ["advisory"], []),
        ("⑧ --selftest 全绿",
         ["--selftest"], 0, ["0 FAIL"], []),
        ("⑨ --selfcheck 三段齐",
         ["--selfcheck"], 0, ["① 能力清单", "② 不该发生路径清单", "③ 依赖完整性"], []),
        ("⑩ --prove-strip 剥离生效",
         ["--prove-strip"], 0, ["剥离后=False"], []),
        ("⑪ --lean4-check 真比对全绿",
         ["--lean4-check"], 0, ["0 FAIL"], []),
        ("⑫ usage：无参数 ⇒ exit 2",
         [], 2, ["usage"], []),
    )


def run_case(name, argv, want_code, want_in, want_out, tmp):
    """真跑一个用例 ⇒ 返回 (state, detail)。★ 四态不做折算。"""
    if not os.path.exists(GATE):
        return ("skipped", "被测对象不存在：%s" % GATE)
    if not os.access(sys.executable, os.X_OK):
        return ("skipped", "解释器不可执行：%s" % sys.executable)
    try:
        t0 = time.time()
        r = subprocess.run([sys.executable, GATE] + argv,
                           capture_output=True, text=True, timeout=TIMEOUT_SEC, cwd=HERE)
        dt = time.time() - t0
    except subprocess.TimeoutExpired:
        return ("timeout", "超时 >%ss（★ 不折算为通过）" % TIMEOUT_SEC)
    except Exception as e:
        return ("skipped", "环境无法执行：%s" % type(e).__name__)

    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != want_code:
        return ("fail", "退出码 %s ≠ 期望 %s" % (r.returncode, want_code))
    for s in (want_in or []):
        if s not in out:
            return ("fail", "输出缺 %r" % s)
    for s in (want_out or []):
        if s in out:
            return ("fail", "输出不应含 %r" % s)
    return ("pass", "%.2fs" % dt)


def main():
    ap = argparse.ArgumentParser(description="回应正当性门 · 真挂载冒烟（四态如实分报）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--help-extra", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(__version__)
        return 0

    import tempfile
    tmp = tempfile.mkdtemp(prefix="rjg-smoke-")
    rows = []
    for name, argv, wc, wi, wo in build_cases(tmp):
        st, detail = run_case(name, argv, wc, wi, wo, tmp)
        rows.append({"case": name, "state": st, "detail": detail})

    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1

    if a.json:
        print(json.dumps({"tool": "response-justification-gate", "version": __version__,
                          "cases": rows, "counts": counts}, ensure_ascii=False, indent=1))
    else:
        print("== response-justification-gate · 真挂载冒烟（v%s）==" % __version__)
        print("   ★ 四态如实分报 —— skipped / timeout **不折算为通过**")
        print()
        icon = {"pass": "✅", "fail": "❌", "skipped": "⏭", "timeout": "⏱"}
        for r in rows:
            print("  %s %-6s %-40s %s" % (icon.get(r["state"], "?"), r["state"], r["case"], r["detail"]))
        print()
        print("  ⇒ pass %d · fail %d · skipped %d · timeout %d"
              % (counts.get("pass", 0), counts.get("fail", 0),
                 counts.get("skipped", 0), counts.get("timeout", 0)))
        bad = counts.get("fail", 0) + counts.get("timeout", 0)
        print("  ⇒ 判定：%s" % ("PASS（无 fail 无 timeout）" if bad == 0 else "FAIL（%d 项）" % bad))
        if counts.get("skipped", 0):
            print("  ★ 注意：skipped %d 项【未计入通过】—— 见上逐条原因" % counts["skipped"])

    bad = counts.get("fail", 0) + counts.get("timeout", 0)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
