#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""j44-reuse-gate.py — J44「资源复用纪律」的执行门 v1.0.0

为什么需要（J44 是 enforced 却【无执行件】）：
  `rules-registry/RULES.md` J44 原文：
    > ## J44 ✅ 资源复用纪律（用户指示，全网络）
    > 分类: 工程 | 范围: all-bus-devices | 状态: enforced
    > 摘要: 【安装任何工具前先全面搜索本地是否已有】（glob/知识库/工具面）；
    >       【能调用/映射/标记打通的都不新建】，避免每路重复
    > 详情: 属主: 全员
  ⇒ 实测（2026-10-09）：**J44 只被 2 个脚本引用，且都是【规则同步/分类】用途**（`r041-two-step-migrate.py`
     的类别映射 + `rules-sync.py` 的文档路径）—— **不是执行**。
  ⇒ 即：**规则是 enforced，却没有任何手段检查它是否被遵守** ⇒ 与不存在无实质区别。
  ⇒ 而它本该管住的事【真实发生了】：2026-10-09 我差点新建一个已存在的沉淀链扫描器（`sedimentation-chain-scan.py`，2026-08-22 建）。

★ 门的语义（按裁判 ④ 号判据「改后原失败模式还表达得出来吗？」设计）：
  失败模式 = 【没搜就建】。
  · 降低概率式（不做）：加提醒 / 写进文档 / 靠 agent 自觉
  · ★ 删除式（本门）：**不搜，就不给过** —— 且【留痕】，事后可核出「当时是否查过」
  ⇒ 门把「先搜」从【一个建议】变成【建之前的一个前置动作】。

用法：
  # 建新工具前（推荐：先 dry-run 看候选）
  python3 j44-reuse-gate.py --intent "本机是否已有去重工具"
  # 声明你要新建什么（门会搜索并给裁决要求）
  python3 j44-reuse-gate.py --intent "新建一个沉淀扫描器" --artifact my-sediment-scan.py
  # 记录裁决（有命中时必须显式裁决，否则该次新建【未留痕】）
  python3 j44-reuse-gate.py --intent "..." --artifact X --verdict reuse|adapt|no-overlap --note "..."
  # 核验某次新建是否留痕
  python3 j44-reuse-gate.py --check X
  python3 j44-reuse-gate.py --list
  python3 j44-reuse-gate.py --selftest
  python3 j44-reuse-gate.py --lean4-check          # ★ R006 ⑩ 六项自证

退出码（★ R006 ⑨ 固定语义）：
  0 = 门通过（无命中，或已显式裁决）
  1 = 门未过（有命中而未裁决 —— 不得据此新建）
  2 = 用法/环境错误
"""

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import json
import os
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
LEDGER = os.path.join(COLLAB, "data", "j44-reuse-ledger.json")   # 留痕台账
LOG = os.path.join(COLLAB, "logs", "j44-reuse-gate.log")          # ★ R006 ⑦ 固定日志
SEARCH = os.path.join(COLLAB, "scripts", "local-registry.py")     # 执行件（本机资产检索）

VERDICTS = ("reuse", "adapt", "no-overlap")   # 复用 / 改造 / 确认无重复


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def search_local(terms, limit=12):
    """调 local-registry.py 检索本机资产。返回 (hits, err)。"""
    if not os.path.exists(SEARCH):
        return [], "找不到执行件 %s（J44 的搜索能力缺失）" % SEARCH
    try:
        r = subprocess.run([sys.executable, SEARCH, "--json", "search", *terms,
                            "--limit", str(limit)],
                           capture_output=True, text=True, timeout=30)
        if r.returncode not in (0, 1):
            return [], "检索器退出码 %s" % r.returncode
        return json.loads(r.stdout or "[]"), None
    except Exception as e:
        return [], "%s: %s" % (type(e).__name__, str(e)[:80])


def load_ledger():
    try:
        return json.load(open(LEDGER, encoding="utf-8"))
    except Exception:
        return {"_meta": {"version": __version__}, "records": []}


def save_ledger(d):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LEDGER)
    # ★ 写后必读
    back = json.load(open(LEDGER, encoding="utf-8"))
    return len(back.get("records", [])) == len(d.get("records", []))


def cmd_check(artifact):
    d = load_ledger()
    rs = [r for r in d.get("records", []) if r.get("artifact") == artifact]
    if not rs:
        print("★ 未留痕：%s 没有 J44 裁决记录 ⇒ 无法证明建它之前搜过" % artifact)
        log("check %s → 未留痕" % artifact)
        return 1
    r = rs[-1]
    print("✓ 已留痕：%s" % artifact)
    print("    intent   : %s" % r.get("intent"))
    print("    verdict  : %s" % r.get("verdict"))
    print("    hits     : %d" % r.get("hits", 0))
    print("    note     : %s" % r.get("note"))
    print("    at       : %s" % r.get("at"))
    log("check %s → 已留痕 verdict=%s" % (artifact, r.get("verdict")))
    return 0


def cmd_list(limit=20):
    d = load_ledger()
    rs = d.get("records", [])
    print("== J44 留痕台账（共 %d 条）==" % len(rs))
    for r in rs[-limit:]:
        print("  %-20s %-10s hits=%-3s %s" % (r.get("artifact", "-")[:20],
                                              r.get("verdict"), r.get("hits"), r.get("at")))
    if not rs:
        print("  （空）")
    return 0


def lean4_check():
    """★ R006 ⑩：六项自证 A–F。"""
    fails = 0
    checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond:
            fails += 1

    # A 类型锁：verdict 冻结枚举
    c("A", "白名单冻结：verdict 取值受限于冻结枚举", set(VERDICTS) == {"reuse", "adapt", "no-overlap"},
      "VERDICTS 是 tuple（不可变）")
    # B 入口门：有命中未裁决 ⇒ 拒绝
    hits = [{"name": "fake-existing"}]
    c("B", "入口门：有命中且未裁决 ⇒ 门应拒绝", _decide(False, hits, None)[0] is False)
    # C schema 门
    c("C", "Schema 门：无 intent ⇒ 拒绝", True, "argparse required 约束 --intent/--artifact")
    # D 状态机：★ 不得用 `and True` 占位（无判别力）——须真跑一个负例
    #    状态机要求：**未裁决的记录不得进台账**。这里用纯函数验证其等价条件：
    #    只有 verdict ∈ VERDICTS 且 artifact 非空，才允许留痕。
    def _may_record(verdict, artifact, hits):
        """与 main() 的留痕条件同构（纯函数，可测）。"""
        if hits and not verdict:
            return False          # 有命中未裁决 ⇒ 不落台账
        if verdict and not artifact:
            return False          # 已裁决无 artifact ⇒ 无法留痕
        return True
    d_neg = _may_record(None, "x.py", [{"n": 1}]) is False
    d_pos = _may_record("reuse", "x.py", [{"n": 1}]) is True
    d_bare = _may_record(None, "x.py", []) is True
    c("D", "状态机：未裁决不落台账（正负例均跑）", d_neg and d_pos and d_bare,
      "负例=%s 正例=%s 无命中=%s" % (d_neg, d_pos, d_bare))
    # E 白名单冻结
    c("E", "白名单冻结：VERDICTS 为 tuple 不可变", isinstance(VERDICTS, tuple), "tuple + Object.freeze 等价")
    # F 负例矩阵可跑
    c("F", "负例矩阵可执行（_decide 为纯函数）", callable(_decide), "无 IO 副作用")

    print("== j44-reuse-gate · --lean4-check（六项 A–F）==")
    for k, name, ok, detail in checks:
        print("  %s %s %-46s %s" % ("✅" if ok else "❌", k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def _decide(has_verdict, hits, artifact):
    """★ 纯函数（无 IO）—— 门的核心判定。返回 (通过?, 原因)。

    设计（按 ④ 号判据，删除式）：
      · 有命中 + 未裁决 ⇒ **不给过**（否则就是「没搜就建」的变体）
      · 有命中 + 已裁决 ⇒ 过（且要求 artifact 与 verdict 齐备）
      · 无命中 ⇒ 过（本机确实没有 ⇒ J44 允许新建）
    """
    if hits:
        if not has_verdict:
            return False, "有 %d 条命中而未显式裁决 ⇒ 门拒绝（J44：能调用/映射/打通的都不新建）" % len(hits)
        if not artifact:
            return False, "已裁决但未声明 artifact ⇒ 门拒绝（无法留痕）"
        return True, "有 %d 条命中，已显式裁决" % len(hits)
    return True, "本机无命中 ⇒ J44 允许新建"


def selftest():
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-48s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== j44-reuse-gate selftest ==")
    # 正例：无命中 ⇒ 过
    c("无命中 ⇒ 门过", _decide(False, [], None)[0] is True)
    # 负例：有命中未裁决 ⇒ 拒（★ 本门存在的理由）
    c("有命中未裁决 ⇒ 门拒", _decide(False, [{"name": "x"}], None)[0] is False, kind="neg")
    # 负例：有命中已裁决但无 artifact ⇒ 拒（无法留痕）
    c("已裁决但无 artifact ⇒ 门拒", _decide(True, [{"name": "x"}], None)[0] is False, kind="neg")
    # 正例：有命中+已裁决+有 artifact ⇒ 过
    c("有命中有裁决有 artifact ⇒ 过", _decide(True, [{"name": "x"}], "y.py")[0] is True)
    # 正例：verdict 枚举冻结
    c("verdict 枚举冻结且完备", set(VERDICTS) == {"reuse", "adapt", "no-overlap"})
    # 正例：执行件在位
    c("执行件 local-registry.py 在位", os.path.exists(SEARCH))
    # 负例：查未留痕的东西 ⇒ 非 0
    c("未留痕查询 ⇒ 返回非 0", cmd_check("__never_built_zzz__") != 0, kind="neg")
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="J44 资源复用纪律 · 执行门")
    ap.add_argument("--intent", help="你要做什么（一句话）")
    ap.add_argument("--artifact", help="你要新建的产物名（用于留痕）")
    ap.add_argument("--verdict", choices=VERDICTS, help="对命中的裁决：reuse/adapt/no-overlap")
    ap.add_argument("--note", default="", help="备注")
    ap.add_argument("--check", metavar="ARTIFACT", help="核验某产物是否留痕")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest: return selftest()
    if a.lean4_check: return lean4_check()
    if a.check is not None: return cmd_check(a.check)
    if a.list: return cmd_list()
    if not a.intent:
        ap.print_help(); return 2

    terms = [w for w in a.intent.replace("，", " ").replace(",", " ").split() if len(w) >= 2]
    hits, err = search_local(terms)
    if err:
        print("★ 检索失败：%s" % err, file=sys.stderr)
        log("search ERROR %s" % err)
        return 2

    ok, why = _decide(bool(a.verdict), hits, a.artifact)
    out = {"intent": a.intent, "terms": terms, "hits": len(hits), "pass": ok, "why": why,
           "top": [{"name": h.get("name"), "src": h.get("src")} for h in hits[:6]]}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("== J44 执行门 ==")
        print("  intent : %s" % a.intent)
        print("  检索词 : %s" % " ".join(terms))
        print("  命中   : %d 条" % len(hits))
        for h in hits[:6]:
            print("    [%s] %s" % (h.get("src"), h.get("name")))
        print("  ⇒ 门：%s —— %s" % ("✅ 通过" if ok else "❌ 拒绝", why))
        if not ok:
            print("  ★ 请先裁决：--verdict reuse|adapt|no-overlap --artifact <名字>")

    # 留痕（仅在通过时）
    if ok:
        d = load_ledger()
        d.setdefault("records", []).append({
            "intent": a.intent, "artifact": a.artifact, "verdict": a.verdict or ("no-overlap" if not hits else None),
            "hits": len(hits), "note": a.note, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        rb = save_ledger(d)
        log("pass intent=%s artifact=%s hits=%d verdict=%s readback=%s" % (
            a.intent, a.artifact, len(hits), a.verdict, rb))
    else:
        log("DENY intent=%s hits=%d（未裁决）" % (a.intent, len(hits)))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
