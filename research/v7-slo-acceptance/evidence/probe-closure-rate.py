#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 闭环率 —— 现测口径（★ 分母为 0 时报「不可判」，不报 0%/OK）

★ 2026-10-12 增补（v7 M4-① 第四项 / W4 报「11/14 无负控」）：
  ★ 本件此前**从未被造坏验证过** —— 它的逻辑**一直是对的**，
    但**「对」和「被验证过对」是两件事**。
  ★★ 故新增 `--data <path>`（★ 注入任一份索引，供负控用）与 `--selftest`（★ 3 正控 + 2 负控）。
  ★★★ **判据：造坏数据 ⇒ 本 probe 必须给出「红」；造好数据 ⇒ 必须给出「绿」/「不可判」（按设计）。**
"""
import json, os, sys, argparse, tempfile

DEFAULT = os.path.expanduser("~/dsh-collab/data/registry/continuity-index.json")


def verifier_ok(v):
    """verifier 在位 = 字段非空 **且** 不是一个「待复核」占位串"""
    if not v or not isinstance(v, str):
        return False
    if "待第三方复核" in v or "待复核" in v:
        return False
    if "missing" in v.lower():
        return False
    return True


def evaluate(d, label=None):
    """★ 纯函数：给定索引 dict ⇒ 返回 (verdict, payload)。``verdict`` ∈ {PASS, FAIL, UNDECIDABLE}"""
    items = d.get("items") or []
    total = len(items)
    if total == 0:
        return "UNDECIDABLE", {"reason": "分母 = 0", "total": 0}
    CLOSED = "closed_with_evidence"
    closed = [i for i in items if i.get("state") == CLOSED]
    with_v = [i for i in closed if verifier_ok(i.get("verifier"))]
    rate = 100.0 * len(closed) / total
    # ★ 判据：① 闭环率 ≥80%  ② 每项有 verifier（★ 锚点 §12 原文「≥80%，每项有 verifier」）
    crit1 = rate >= 80.0
    crit2 = (len(with_v) == len(closed))
    verdict = "PASS" if (crit1 and crit2) else "FAIL"
    return verdict, {
        "label": label, "total": total, "closed": len(closed),
        "with_verifier": len(with_v), "rate_pct": round(rate, 1),
        "crit1_rate_ge_80": crit1, "crit2_every_closed_has_verifier": crit2,
        "items": items, "updated_at": d.get("updated_at"),
        "state_version": d.get("state_version"),
    }


def report(p, payload):
    print("索引:", p)
    print("索引 updated_at:", payload.get("updated_at"), "· state_version:", payload.get("state_version"))
    print()
    print("分母（items 总数）= %d" % payload["total"])
    print("分子（state == closed_with_evidence）= %d" % payload["closed"])
    print("闭环率 = %d/%d = %.1f%%   （目标 ≥80%%）" % (payload["closed"], payload["total"], payload["rate_pct"]))
    print()
    print("逐项:")
    for i in payload["items"]:
        v = i.get("verifier")
        tag = "OK" if verifier_ok(v) else ("缺失" if not v else "占位/待复核")
        print("  %-6s %-22s verifier=%s" % (i.get("id"), i.get("state"), tag))
    print()
    print("★ 真正到位的 verifier（非占位）：%d/%d" % (payload["with_verifier"], payload["closed"]))
    if payload["closed"] and payload["with_verifier"] == 0:
        print("★ ⇒ 全部 closed 项的 verifier 均是「待第三方复核」占位 ⇒ 按 §5.1「未证不得记 closed」，")
        print("  这些 closed 在【审查意义上】全部不可判 ⇒ 闭环率的分子在审查口径下 = 不可判。")
    # ★★ 判据逐条显式报（★ 这样红在哪一眼可见）
    print()
    print("★ 判据①  闭环率 ≥80%%        : %s（实得 %.1f%%）" % ("✓" if payload["crit1_rate_ge_80"] else "❌", payload["rate_pct"]))
    print("★ 判据②  每个 closed 有 verifier: %s（实得 %d/%d）"
          % ("✓" if payload["crit2_every_closed_has_verifier"] else "❌",
             payload["with_verifier"], payload["closed"]))
    if payload["crit1_rate_ge_80"] and payload["crit2_every_closed_has_verifier"]:
        print("★ ⇒ 两条判据均过 ⇒ **成立**")
    else:
        print("★ ⇒ 至少一条不过 ⇒ **不成立**")
    print()
    print("★ 时刻声明：本读数是上面 updated_at 时刻的索引状态，不是「现在的事实」。")


def selftest():
    """★ 3 正控 + 2 负控 —— ★ 全部真调 ``evaluate()``。"""
    ok = tot = 0
    # ★ 正控①：造【该红】的数据（闭环率低 + verifier 全占位）⇒ 必须 FAIL
    tot += 1
    bad = {"items": [{"id": "X%d" % i, "state": "closed_with_evidence",
                      "verifier": "★ 待第三方复核"} for i in range(1, 4)] +
                    [{"id": "Y%d" % i, "state": "open"} for i in range(1, 8)],
           "updated_at": "2026-10-12T00:00:00+08:00"}
    v, pl = evaluate(bad)
    if v == "FAIL":
        ok += 1
        print("  ✅ 正控①：闭环率 %s%% + verifier 全占位 ⇒ FAIL" % pl["rate_pct"])
    else:
        print("  ❌ 正控①：该红却判 %s" % v)
    # ★ 正控②：造【该绿】的数据（闭环率高 + verifier 真到位）⇒ 必须 PASS
    tot += 1
    good = {"items": [{"id": "X%d" % i, "state": "closed_with_evidence",
                       "verifier": "独立复核员 session-abc（2026-10-12 复核）"} for i in range(1, 9)] +
                     [{"id": "Y1", "state": "open"}],
            "updated_at": "2026-10-12T00:00:00+08:00"}
    v2, pl2 = evaluate(good)
    if v2 == "PASS":
        ok += 1
        print("  ✅ 正控②：闭环率 %s%% + verifier 到位 ⇒ PASS（★ 防判据恒红）" % pl2["rate_pct"])
    else:
        print("  ❌ 正控②：该绿却判 %s" % v2)
    # ★ 负控①：分母为 0 ⇒ 必须 UNDECIDABLE（★ 不得报 0%/OK）
    tot += 1
    v3, _ = evaluate({"items": []})
    if v3 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 负控①：分母 0 ⇒ UNDECIDABLE（★ 不报 0%%/OK）")
    else:
        print("  ❌ 负控①：分母 0 未判 UNDECIDABLE（%s）" % v3)
    # ★ 负控②：闭环率高但 verifier 全缺 ⇒ 仍必须 FAIL（★ 防「只看率」）
    tot += 1
    half = {"items": [{"id": "X%d" % i, "state": "closed_with_evidence"} for i in range(1, 10)] +
                     [{"id": "Y1", "state": "open"}],
            "updated_at": "2026-10-12T00:00:00+08:00"}
    v4, pl4 = evaluate(half)
    if v4 == "FAIL" and pl4["crit1_rate_ge_80"] and not pl4["crit2_every_closed_has_verifier"]:
        ok += 1
        print("  ✅ 负控②：率 %.1f%% 过但 verifier 全缺 ⇒ 仍 FAIL（★ 判据②独立生效）" % pl4["rate_pct"])
    else:
        print("  ❌ 负控②：只过判据①竟判通过（%s）" % v4)
    # ★ 负控③：占位串「missing」也须被认出（★ 防 verifier_ok 过宽）
    tot += 1
    if not verifier_ok("★ missing：生效未验") and not verifier_ok("") and verifier_ok("真的复核了"):
        ok += 1
        print("  ✅ 负控③：`missing`/空串判不合格 · 真复核判合格（★ verifier_ok 不过宽）")
    else:
        print("  ❌ 负控③：verifier_ok 判别有误")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="★ 注入另一份索引（供负控用）；缺省用真索引")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("probe-closure-rate 1.1.0")
        return 0
    if a.selftest:
        return selftest()
    p = os.path.expanduser(a.data) if a.data else DEFAULT
    if not os.path.exists(p):
        print("★ 索引不可读 ⇒ 不可判（★ 读不到 ≠ 不存在）: %s" % p)
        return 3
    d = json.load(open(p, encoding="utf-8"))
    verdict, payload = evaluate(d, label=p)
    if a.json:
        print(json.dumps({**payload, "verdict": verdict}, ensure_ascii=False, indent=1))
        return 0 if verdict == "PASS" else (3 if verdict == "UNDECIDABLE" else 1)
    report(p, payload)
    return 0 if verdict == "PASS" else (3 if verdict == "UNDECIDABLE" else 1)


if __name__ == "__main__":
    sys.exit(main())
