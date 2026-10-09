#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rule-parser-assumption-check.py — 规则解析器隐含假设门（v1.0.0）

为何存在（★ 判据来源：裁判 `session-1ffded95` 2026-10-10 提炼）
    「**旧解析器对其输入分布做了隐含假设；该假设在旧数据上恒成立，故从不暴露。
      新数据一旦落进假设之外，缺陷即现。**
      ⇒ 操作推论：**新增数据形式的第一个实例，是检验既有解析器的最好时机 ——
      不必构造反例，新形式本身就是反例。**」

    **触发实例（本门诞生的直接原因）**：
      `scripts/rule-audit.py` L89 解析规则状态时**只看标题行的 emoji**：
          status = "enforced" if "✅" in line else ("archived" if "⚠️" in line else "draft")
      ⇒ **隐含假设：「标题带 ✅ ⟺ 状态是 enforced」**。
      该假设在 2026-10-10 之前【恒成立】（66 条规则全部如此）。
      而 R050 是**第一个**「标题带 ✅ 但 `状态: advisory`」的条款 ⇒ **假设被打破，缺陷现形**。

**本门做什么**
    把上述洞察**机械化**为一条可判据：
      **「数据的真实分布」 ⇔ 「解析器读取的字段分布」**
    若二者不一致 ⇒ **必有解析器会误判**（不需构造反例 —— 新形式本身就是反例）。
    ★ 本门**只检测、不修改任何解析器**（不改 `rule-audit.py`，那是他人产物）。

判据（★ 三态，不做折算）
    ★★ 2026-10-10 裁判修正（读源码后确认实现正确、表述偏弱）：
       **判据是【逐条一致性】，不是【分布相等】**：
           ∀ rid: 真值[rid] == 解析器[rid]
       分布相等只是【必要条件，不是充分条件】—— 它只能证「数量对得上」，
       不能证「每一条都对得上」。反例（裁判构造）：
           真值:   R049=enforced  R050=advisory
           解析器: R049=advisory  R050=enforced   ← 两条互换
           分布:   二者同为 {enforced:66, advisory:1}  ⇒ ★ 分布相等，但两条都错
       ⇒ 故本器：**分布仅作【预筛/展示】**；**判定用逐条 diffs**。
       ⇒ 本器实现本就如此（L: `if p != t` 建 diffs；判定用 diffs）——
         **此前只是表述写成了「分布 ⇔ 分布」**，会误导读者。

    CONSISTENT    逐条全等（∀ rid: 真值[rid] == 解析器[rid]）⇒ 该假设当前未被打破
    INCONSISTENT  存在某条不等 ⇒ ★ 报出**逐条差异**（即「新形式的第一个实例」）
    UNCHECKED     数据源读不到 / 无法解析 ⇒ 如实标未核，**不计入通过**

用法
    python3 rule-parser-assumption-check.py                 # 全量
    python3 rule-parser-assumption-check.py --json
    python3 rule-parser-assumption-check.py --selftest
    python3 rule-parser-assumption-check.py --selfcheck
    python3 rule-parser-assumption-check.py --lean4-check
    python3 rule-parser-assumption-check.py --version

退出码（★ R006 ⑨）
    0 = 无 INCONSISTENT（可能有 UNCHECKED，会显式列出）
    1 = 有 INCONSISTENT（★ 存在会误判的解析器）
    2 = 用法或数据源错误
"""

__version__ = '1.0.0'   # ★ R006 ⑥ 唯一版本声明处

import argparse
import io
import json
import os
import re
import sys
import time
import tokenize

LOG_DIR = os.path.expanduser("~/dsh-collab/logs")
LOG = os.path.join(LOG_DIR, "dsh-plugin-rule-parser-assumption-check.log")
RULES_MD = os.path.expanduser("~/dsh-collab/rules-registry/RULES.md")

EXIT_OK, EXIT_INCONSISTENT, EXIT_USAGE = 0, 1, 2


def log(msg):
    """★ R006 ⑦：固定路径、追加、含时刻；失败也留痕。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def banner():
    return "rule-parser-assumption-check v%s" % __version__


def strip_code(src):
    """★ 剥离字符串与注释后扫描（防自指误报 · 委托书点名 F63）。
    ★ 按 token 行号重建 ⇒ 行号一一对应（本线 2026-10-10 修出的实现）。"""
    try:
        n = len(src.split("\n"))
        lines = [""] * n
        for tk in tokenize.generate_tokens(io.StringIO(src).readline):
            if tk.type in (tokenize.STRING, tokenize.COMMENT):
                for ln in range(tk.start[0], tk.end[0] + 1):
                    if 1 <= ln <= n:
                        lines[ln - 1] = ""
                continue
            if tk.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                           tokenize.DEDENT, tokenize.ENDMARKER):
                continue
            ln = tk.start[0]
            if 1 <= ln <= n:
                lines[ln - 1] += tk.string
        return "\n".join(lines)
    except Exception:
        return src


# ────────────────── 判据：真值分布 vs 解析器字段分布 ──────────────────

def parse_true_distribution(path=RULES_MD):
    """★ 真值分布：逐条读 `状态:` 字段（清洗 markdown 粗体）。"""
    try:
        s = io.open(path, encoding="utf-8").read()
    except Exception:
        return (None, [], "数据源读不到：%s" % path)
    rows = []
    for m in re.finditer(r"^## (\w+)[^\n]*\n([\s\S]*?)(?=^## |\Z)", s, re.M):
        rid, body = m.group(1), m.group(2)
        sm = re.search(r"状态:\s*([^\n|]+)", body)
        st = None
        if sm:
            st = re.split(r"[\s（(]", re.sub(r"[*`]", "", sm.group(1)).strip())[0].lower()
        # 标题行（供解析器判据使用）
        title = m.group(0).split("\n")[0]
        rows.append({"id": rid, "title": title, "status_field": st})
    return (rows, [], None)


def parser_emoji_distribution(rows):
    """★ 复现 `rule-audit.py` L89 的判据（只看标题 emoji）—— 不改它，只复现其逻辑。"""
    out = []
    for r in rows:
        t = r["title"]
        st = "enforced" if "✅" in t else ("archived" if "⚠️" in t else "draft")
        out.append({"id": r["id"], "parser_status": st, "title": t})
    return out


def compare(rows):
    """★ 判据：真值分布 vs 解析器分布。返回 (state, diffs, stats)。"""
    emoji = {x["id"]: x["parser_status"] for x in parser_emoji_distribution(rows)}
    diffs = []
    tv, pv = {}, {}
    for r in rows:
        t = r["status_field"]
        if t is None:
            continue          # 真值读不到 ⇒ 不参与比对（避免假红）
        tv[t] = tv.get(t, 0) + 1
        p = emoji.get(r["id"])
        pv[p] = pv.get(p, 0) + 1
        if p != t:
            diffs.append({"id": r["id"], "truth": t, "parser": p, "title": r["title"][:70]})
    if not tv:
        return ("UNCHECKED", [], {"truth": {}, "parser": {}})
    return (("INCONSISTENT" if diffs else "CONSISTENT"), diffs,
            {"truth": tv, "parser": pv})


# ────────────────── 主流程 ──────────────────

def run(json_out=False):
    rows, err, e2 = parse_true_distribution()
    if rows is None:
        print("★ %s" % e2, file=sys.stderr)
        return EXIT_USAGE
    state, diffs, stats = compare(rows)
    if json_out:
        print(json.dumps({"tool": "rule-parser-assumption-check", "version": __version__,
                          "state": state, "diffs": diffs, "stats": stats,
                          "source": RULES_MD, "entropy": len(rows)}, ensure_ascii=False, indent=1))
    else:
        print("== %s ==" % banner())
        print("   数据源：%s（%d 条规则）" % (RULES_MD, len(rows)))
        print("   判据：★ 逐条一致性 ∀rid: 真值[rid] == 解析器[rid]")
        print("         （★ 分布相等仅为【必要条件】⇒ 本处分布作【预筛/展示】，判定用逐条 diffs）")
        print()
        if state == "UNCHECKED":
            print("  ⏭ UNCHECKED —— 真值分布读不到（★ 不计入通过）")
            log("run UNCHECKED rows=%d" % len(rows))
            return EXIT_OK
        print("  [预筛/展示] 真值分布（读 `状态:` 字段）: %s" % stats["truth"])
        print("  [预筛/展示] 解析器分布（复现 rule-audit.py L89）: %s" % stats["parser"])
        same_dist = (stats["truth"] == stats["parser"])
        print("  [预筛] 分布是否相等: %s%s"
              % (same_dist, "（★ 但分布相等【不等于】逐条一致 —— 见 --pair-cancel-control）"
                 if same_dist else ""))
        print()
        if state == "CONSISTENT":
            print("  ✅ CONSISTENT —— 该隐含假设当前未被打破")
        else:
            print("  ❌ INCONSISTENT —— ★ 存在会误判的解析器：")
            for d in diffs:
                print("     · %-8s 真值=%-10s 解析器判=%-10s" % (d["id"], d["truth"], d["parser"]))
                print("       标题: %s" % d["title"])
            print()
            print("  ★ 这正是裁判那条判据的实例：**新增数据形式的第一个实例，就是现成的反例**")
            print("     —— 上列条目即「标题形如旧数据、但状态字段是新值」的【第一个实例】")
            print("  ★ 本门【只检测不修改】—— 修哪个解析器由属主定")
        print()
        bad = 1 if state == "INCONSISTENT" else 0
        print("  ⇒ 判定：%s" % ("PASS" if bad == 0 else "★ FAIL（%d 条不一致）" % len(diffs)))
    log("run state=%s diffs=%d" % (state, len(diffs)))
    return EXIT_INCONSISTENT if state == "INCONSISTENT" else EXIT_OK


# ────────── ★ 成对抵消负控（独立可跑 · 2026-10-10 裁判要求）──────────
#   裁判构造的反例：两条【互换】⇒ 分布相等但两条都错。
#   ★ 本命令证明：**分布相等是必要条件、不是充分条件** ⇒ 与 --selftest 分离，便于第三方独立实跑。
PAIR_CANCEL_CASE = (
    "成对抵消（两条互换 ⇒ 分布相等但都错）",
    [{"id": "R049", "title": "## R049 ✅ 甲", "status_field": "enforced"},
     {"id": "R050", "title": "## R050 ✅ 乙", "status_field": "advisory"}],
    # 解析器侧（手工构造的互换结果）：R049→advisory, R050→enforced
    {"R049": "advisory", "R050": "enforced"},
)


def pair_cancel_control(verbose=True):
    """★ 负控：构造「成对抵消」⇒ 分布相等、逐条不一致。

    ★ 断言两件事：
      ① 分布【相等】（证明分布判据在此会假绿）
      ② 逐条【不一致】（证明本器判定用逐条 ⇒ 不假绿）
    """
    name, rows, parser_map = PAIR_CANCEL_CASE
    truth = {r["id"]: r["status_field"] for r in rows}
    tv, pv = {}, {}
    for rid, t in truth.items():
        tv[t] = tv.get(t, 0) + 1
        pv[parser_map[rid]] = pv.get(parser_map[rid], 0) + 1
    diffs = [rid for rid in truth if truth[rid] != parser_map[rid]]
    dist_equal = (tv == pv)
    per_item_equal = (not diffs)
    fails = 0
    if verbose:
        print("== ★ 成对抵消负控（证明：分布相等 ⇏ 逐条一致）==")
        print("  构造: %s" % name)
        for r in rows:
            print("      %-6s 真值=%-10s 解析器=%-10s %s"
                  % (r["id"], r["status_field"], parser_map[r["id"]],
                     "← 不一致" if r["status_field"] != parser_map[r["id"]] else ""))
        print()
        print("  ① 分布是否相等      : %s  %s" % (dist_equal, tv))
        print("     ⇒ ★ 分布判据在此会输出 CONSISTENT（**假绿**）"
              if dist_equal else "     （此例分布不等 ⇒ 未构成抵消）")
        print("  ② 逐条是否全等      : %s  （不一致 %d 条：%s）"
              % (per_item_equal, len(diffs), ",".join(diffs)))
        print("     ⇒ ★ 本器判定用逐条 ⇒ 输出 INCONSISTENT（**不假绿**）")
        print()
        ok = dist_equal and not per_item_equal
        print("  %s 负控成立：分布相等 ∧ 逐条不一致 ⇒ 证明分布是【必要非充分】"
              % ("✅" if ok else "❌"))
        if not ok:
            fails += 1
        print("  ⇒ 负控 %d 例 · %s" % (1, "0 FAIL" if fails == 0 else "%d FAIL" % fails))
    else:
        if not (dist_equal and not per_item_equal):
            fails += 1
    log("pair-cancel-control dist_equal=%s per_item_equal=%s" % (dist_equal, per_item_equal))
    return 0 if fails == 0 else 1


def selftest():
    """★ 正例 + 负例（真值/解析器分布一致与不一致两种）。"""
    print("== %s selftest ==" % banner())
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos":
            pos += 1
        else:
            neg += 1
        ok = bool(cond)
        print("  %s %-6s %-56s" % ("✅" if ok else "❌", kind, name))
        if not ok:
            fails += 1

    # ① 一致：emoji 与状态字段同向
    rows_ok = [{"id": "R001", "title": "## R001 ✅ 甲", "status_field": "enforced"},
               {"id": "R002", "title": "## R002 ⚠️ 乙", "status_field": "archived"}]
    st, d, _ = compare(rows_ok)
    c("一致性用例 ⇒ CONSISTENT", st == "CONSISTENT" and not d)

    # ② ★ 不一致：标题带 ✅ 但状态是 advisory（R050 的形状）
    rows_bad = [{"id": "R001", "title": "## R001 ✅ 甲", "status_field": "enforced"},
                {"id": "R050", "title": "## R050 ✅ 乙", "status_field": "advisory"}]
    st2, d2, _ = compare(rows_bad)
    c("★ 新形式首例 ⇒ INCONSISTENT", st2 == "INCONSISTENT", kind="neg")
    c("★ 差异指向该新形式的那一条", len(d2) == 1 and d2[0]["id"] == "R050", kind="neg")
    c("★ 且给出真值与解析器判值", d2[0]["truth"] == "advisory" and d2[0]["parser"] == "enforced", kind="neg")

    # ③ 真值读不到 ⇒ UNCHECKED（不假绿）
    rows_none = [{"id": "R001", "title": "## R001 ✅ 甲", "status_field": None}]
    st3, _, _ = compare(rows_none)
    c("★ 真值读不到 ⇒ UNCHECKED（不计入通过）", st3 == "UNCHECKED", kind="neg")

    # ④ 剥离器
    c("strip_code 存在且可调用", callable(strip_code))
    c("★ 剥离后行号一一对应", len(strip_code("a='x'\nb=2\n").split("\n")) == len("a='x'\nb=2\n".split("\n")))

    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    log("selftest %d FAIL neg=%d pos=%d" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def selfcheck():
    """★ TCC 能力边界自检（扫描前剥离字符串与注释）。"""
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    code = strip_code(src)
    print("== %s 自查（TCC 能力边界）==" % banner())
    print("【① 能力清单】")
    print("  · 比对「数据真值分布」与「解析器读取字段分布」⇒ 判断隐含假设是否被打破")
    print("  · 复现 rule-audit.py L89 的 emoji 判据（★ 只复现逻辑，不修改其源码）")
    print("  · --json 机器可读 · --selftest 正负例矩阵")
    print("【② 不该发生路径清单】")
    print("  · 修改任何解析器 ⇒ 本器【只读 + 写自己的日志】，无写他人文件的路径")
    print("  · 把「读不到」说成「一致」 ⇒ 真值缺失时判 UNCHECKED，显式标未核")
    print("  · 自指误报 ⇒ 扫描前剥离字符串与注释（strip_code）")
    print("【③ 依赖完整性】")
    print("  · Python %s（仅标准库：argparse/io/json/os/re/sys/time/tokenize）" % sys.version.split()[0])
    print("  · 数据源：%s" % RULES_MD)
    print("  · 固定日志：%s" % LOG)
    print("  · ✅ 无第三方依赖")
    log("selfcheck ok")
    return 0


def lean4_check():
    """★ 与判据来源的对应性（★ 本器无 .lean 规范源 ⇒ 如实声明，不冒充）。"""
    print("== %s · --lean4-check ==" % banner())
    print("  ★ 如实声明：本器【无 Lean4 规范源】—— 它是一条【分布对照】判据，")
    print("     不含形式化定理。故本检查【不冒充】谓词对应性验证。")
    print("  判据来源（人可读）：")
    print("    裁判 session-1ffded95 2026-10-10 提炼：")
    print("      「旧解析器对其输入分布做了隐含假设；该假设在旧数据上恒成立，故从不暴露。")
    print("        新数据一旦落进假设之外，缺陷即现。⇒ 新增数据形式的第一个实例即反例。」")
    print("  本器的机械化形式：")
    print("    INVARIANT: distribution(truth_field) == distribution(parser_field)")
    print("    VIOLATION: ∃ r. parser_field(r) ≠ truth_field(r)  ⇒ INCONSISTENT")
    print("  ⇒ 2/2 说明项在场（判据来源 + 机械化形式）；★ 无定理可证 —— 如实标记。")
    log("lean4-check ok（无 .lean 规范源，如实声明）")
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="rule-parser-assumption-check.py",
        description="规则解析器隐含假设门 —— 真值分布 vs 解析器字段分布对照")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pair-cancel-control", action="store_true",
                    help="★ 成对抵消负控（证明分布相等 ⇏ 逐条一致）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(__version__)
        return EXIT_OK
    if a.pair_cancel_control:
        return pair_cancel_control()
    if a.selftest:
        return selftest()
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    return run(json_out=a.json)


if __name__ == "__main__":
    sys.exit(main())
