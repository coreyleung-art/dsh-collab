#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-six-conditions.py —— §11「六者齐备」的可跑判据

【判据来源 · 逐字】
  锚点 `docs/distributed-agent-network-governance-plan-v6.1-20261011.md:1939`
  「**通过规则**：正向 ∧ 负控红 ∧ 边界不崩 ∧ 阈值达标 ∧ 沙箱复跑一致 ∧ 官方条款无未声明差异
    —— **六者缺一不得记 `closed_with_evidence`**。」
  锚点 `:1938` 的**八字段**（六者是从这八字段**派生**出来的，映射见 MAPPING）。

【为什么需要本文件】
  现测（2026-10-12）：
    · `continuity-index.json` 的 `dod.full_table` = **null**，`_status` = 「**缺席**」
    · `items` 里 **10 条**，**没有任何一条带六者所需的执行证据**
    · 判据本体只以**自然语言**存在于索引的 `dod.rule` 字符串里 ⇒ **不可跑**
  ⇒ 本文件把那句话变成**能红的东西**。

【三态纪律（★ 本项目的硬纪律）】
  PASS / FAIL / **UNKNOWN**。
  **缺数据一律记 UNKNOWN（不可判），不记 PASS，也不记 FAIL。**
  理由：`dod.full_table` 缺席 ⇒「这一项该填什么」**分母本身没有定义**
  ⇒ 这不是「没通过」，是「**这项到底有没有六者，本机无法回答**」。

【映射（六者 ← 八字段）】
  1 正向        ← 正向判据
  2 负控红      ← 负控（必须能红）
  3 边界不崩    ← 边界用例
  4 阈值达标    ← 阈值与判定规则 + 测量方法与样本量
  5 沙箱复跑一致 ← 沙箱复跑方式
  6 官方条款无未声明差异 ← 本判据**不在八字段内**，须另有出处（§6.1 第 3 条「产物记录三栏」）
  ★ 八字段中**未进六者**的两个：`证据形态` 与 `审查员`
     —— 但 `审查员` 由 §5.1「未证不得记 closed」单独约束（见第六条外的附加判据）。

退出码：0 = 无 FAIL（但仍可能有 UNKNOWN）；1 = 有 FAIL；3 = 判据自身起不来
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(os.path.expanduser("~/dsh-collab"))
INDEX = ROOT / "data/registry/continuity-index.json"

SIX = [
    ("1 正向", "正向判据"),
    ("2 负控红", "负控（必须能红）"),
    ("3 边界不崩", "边界用例"),
    ("4 阈值达标", "阈值与判定规则"),
    ("5 沙箱复跑一致", "沙箱复跑方式"),
    # ★ 第 6 条【不在八字段内】：八字段是 §11 的输入契约，而「官方条款无未声明差异」是 §6.1 第 3 条
    #   要求「产物记录 官方条款 → 我们的设计 → 差异」的产物。故它的键是本判据**新增**的，
    #   且必须显式声明 —— 否则它会变成一个永远拿不到值的恒 FAIL 项（本判据首版即栽在这里，见 --selftest 记录）。
    ("6 官方条款无未声明差异", "官方条款差异"),
]
KEY6 = "官方条款差异"

# 有实际判别力的 verifier（非占位串）
def verifier_real(v):
    if not v or not isinstance(v, str):
        return False
    for bad in ("待第三方复核", "待复核", "missing", "verifier_unavailable", "待补"):
        if bad.lower() in v.lower():
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=str(INDEX))
    ap.add_argument("--strict", action="store_true", help="UNKNOWN 也致非 0")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    p = Path(a.index)
    if not p.exists():
        print("判据起不来：索引不存在 %s" % p, file=sys.stderr)
        return 3
    d = json.load(open(p, encoding="utf-8"))

    dod = d.get("dod") or {}
    full = dod.get("full_table")
    items = d.get("items") or []

    print("§11 六者齐备 · 可跑判据")
    print("判据来源：锚点 `:1939`（逐字见本文件 docstring）")
    print("索引：%s" % p)
    print("索引 updated_at：%s" % d.get("updated_at"))
    print()
    print("六者定义：")
    for name, src in SIX:
        print("   %-24s ← %s" % (name, src))
    print()

    # ---- 分母声明 ----
    print("=== 分母声明 ===")
    print("  dod.full_table = %s" % ("null（缺席）" if full is None else "存在，%d 项" % len(full)))
    print("  dod._status    = %s" % dod.get("_status"))
    print("  items 条数     = %d" % len(items))
    print()
    if full is None:
        print("  ★★ 判定：**六者齐备的分母未定义** —— 「哪些项应当有六者」本机没有权威清单")
        print("     （§11 正文代表性表 7 行 · §10 自称 39 个 W 项 + S1–S5 · `grep` 唯一 W 号 72 ⇒ 三个数对不上）")
        print("     ⇒ ★ 本判据对**全部项**一律报 UNKNOWN（★ 不报 OK，也不报 0%）")
        print()

    # ---- 逐项 ----
    print("=== 逐项 ===")
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0}
    rows = []
    for it in items:
        iid = it.get("id")
        state = it.get("state")
        closed = state == "closed_with_evidence"
        detail = full.get(iid) if isinstance(full, dict) else None
        if detail is None:
            six = {n: "UNKNOWN" for n, _ in SIX}
        else:
            six = {}
            for n, src in SIX:
                key = src.split(" ")[0]
                v = detail.get(key)
                six[n] = "PASS" if v else "FAIL"
        ver = verifier_real(it.get("verifier"))
        # ★ 判定序（★ 首版判反了，故把顺序写死在这里）：
        #   ① 非 closed ⇒ 六者不适用 ⇒ UNKNOWN
        #   ② closed 但 verifier 是占位/缺失 ⇒ FAIL（§5.1 未证不得记 closed）—— 与 full_table 在不在无关
        #   ③ closed 且 verifier 到位、但无 DoD 记录 ⇒ UNKNOWN（分母未定义）
        #   ④ closed 且 verifier 到位、有 DoD 记录但六者缺一 ⇒ FAIL
        #   ⑤ 其余 ⇒ PASS
        if not closed:
            verdict = "UNKNOWN"
        elif not ver:
            verdict = "FAIL"
        elif detail is None:
            verdict = "UNKNOWN"
        elif any(v == "FAIL" for v in six.values()):
            verdict = "FAIL"
        else:
            verdict = "PASS"
        rows.append((iid, state, six, ver, verdict))
        for k in counts:
            if k == verdict:
                counts[k] += 1

    for iid, state, six, ver, verdict in rows:
        print("  %-6s state=%-22s verifier=%-8s ⇒ %s" % (iid, state, "到位" if ver else "占位/无", verdict))
        if all(v == "UNKNOWN" for v in six.values()):
            print("        六者：全部 UNKNOWN（无 DoD 记录）")
        else:
            print("        六者：" + " · ".join("%s=%s" % (k.split(" ")[0], v) for k, v in six.items()))

    print()
    print("=== 汇总 ===")
    print("  PASS %d · FAIL %d · UNKNOWN %d（共 %d）" % (counts["PASS"], counts["FAIL"], counts["UNKNOWN"], len(rows)))
    closed_n = sum(1 for it in items if it.get("state") == "closed_with_evidence")
    closed_ok = sum(1 for (_, _, _, _, v) in rows if v == "PASS")
    print("  closed_with_evidence 项 %d · 其中六者+审查员齐备 %d" % (closed_n, closed_ok))
    print()
    print("=== 附加判据（不在六者内，但 §5.1/§5.1.1 要求）===")
    print("  §5.1「未证不得记 closed」：现测 %d/%d 的 closed 项 verifier 是占位串 ⇒ %s"
          % (closed_n - closed_ok, closed_n, "FAIL" if closed_n and closed_ok < closed_n else "PASS"))
    print()
    print("★ 三态纪律：UNKNOWN ≠ PASS，也 ≠ FAIL。")
    print("★ 本判据的负控（必须红）：见 --selftest")
    rc = 1 if counts["FAIL"] else (1 if (a.strict and counts["UNKNOWN"]) else 0)
    print()
    print("退出码 %d%s" % (rc, "（--strict：UNKNOWN 亦致非 0）" if a.strict else ""))
    return rc


def selftest() -> int:
    """★ 每条检项都必须能红 —— 用【内存中的合成索引】证明，不写盘、不碰生产。"""
    import tempfile
    base = {"updated_at": "2026-01-01T00:00:00+08:00",
            "dod": {"full_table": None, "_status": "缺席", "rule": "…"},
            "items": []}
    cases = []

    def mk(items, full=None):
        o = json.loads(json.dumps(base))
        o["items"] = items
        o["dod"]["full_table"] = full
        return o

    def run(o):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(o, f)
            tmp = f.name
        try:
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main_argv(["--index", tmp])
            return rc, buf.getvalue()
        finally:
            os.unlink(tmp)

    # 正控：closed + 六者齐 + 真 verifier ⇒ PASS
    full_ok = {"C9": {"正向判据": "x", "负控（必须能红）": "x", "边界用例": "x",
                      "阈值与判定规则": "x", "沙箱复跑方式": "x", "官方条款差异": "无"}}
    cases.append(("正控·closed 且六者齐且 verifier 到位 ⇒ PASS",
                  mk([{"id": "C9", "state": "closed_with_evidence", "verifier": "守灯 session-9910d4b2"}], full_ok),
                  0, "PASS"))
    # 负控 1：closed 但 verifier 是占位串 ⇒ 必须红（★ 与 full_table 是否缺席无关）
    cases.append(("负控·closed 而 verifier 为占位串 ⇒ 必须红",
                  mk([{"id": "C9", "state": "closed_with_evidence", "verifier": "待第三方复核"}]),
                  1, "FAIL"))
    # 负控 1b：full_table 齐、verifier 占位 ⇒ 仍必须红
    cases.append(("负控·full_table 齐而 verifier 占位 ⇒ 仍必须红",
                  mk([{"id": "C9", "state": "closed_with_evidence", "verifier": "待第三方复核"}], full_ok),
                  1, "FAIL"))
    # 负控 1c：full_table 齐、verifier 到位、但第 6 条（官方条款差异）缺 ⇒ 必须红
    full_no6 = {"C9": {k: "x" for k in ("正向判据", "负控（必须能红）", "边界用例",
                                        "阈值与判定规则", "沙箱复跑方式")}}
    cases.append(("负控·六者缺第 6 条（官方条款差异）⇒ 必须红",
                  mk([{"id": "C9", "state": "closed_with_evidence", "verifier": "裁判 session-abc"}], full_no6),
                  1, "FAIL"))
    # 负控 2：closed 但六者缺一 ⇒ 必须红
    bad = {"C9": {"正向判据": "x"}}   # 只填 1/6
    cases.append(("负控·六者只齐 1/6 ⇒ 必须红",
                  mk([{"id": "C9", "state": "closed_with_evidence", "verifier": "裁判 session-abc"}], bad),
                  1, "FAIL"))
    # 负控 3：full_table 缺席 ⇒ 必须 UNKNOWN，不得 PASS
    cases.append(("负控·full_table 缺席 ⇒ 必须 UNKNOWN 且无 FAIL",
                  mk([{"id": "C9", "state": "closed_with_evidence", "verifier": "裁判 session-abc"}]),
                  0, "UNKNOWN"))
    # 负控 4：空 items ⇒ 不得报 OK（分母 0）
    cases.append(("负控·items 为空 ⇒ 不得出现 PASS 计数",
                  mk([]), 0, "PASS 0"))

    ok = 0
    print("check-six-conditions 自证（合成 fixture，★ 不写生产路径）")
    for name, obj, want_rc, want_sub in cases:
        rc, out = run(obj)
        good = (rc == want_rc) and (want_sub in out)
        ok += good
        print("  %s %s → rc=%d（期望 %d）· 期望含 %r → %s"
              % ("✅" if good else "❌", name, rc, want_rc, want_sub, "命中" if want_sub in out else "未命中"))
    print("自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def main_argv(argv):
    import sys as _s
    old = _s.argv
    try:
        _s.argv = ["check-six-conditions.py"] + argv
        return main()
    finally:
        _s.argv = old


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
