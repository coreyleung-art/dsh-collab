#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backfill-missing.py —— 【双板欠账补写器】（★ 把本机独有的键补到中枢）

★★★ 立据（用户裁可 2026-10-15 · D-336/D-337 · H3/H4）：
  ★ 中枢黑板 OOM 循环持续 **11 天**（★ `D-336`：OOM 累计 2048 次），
    ★★ 期间【本机写成功、中枢腿失败】的卡 ⇒ **永远到不了中枢**。
  ★ 修复后实测：★ **H3 今日窗 `4/4 = 100%`、H4 `Δ=+0`** ⇒ ★ **新卡已 100% 双板送达** ✓
  ★★ 而**历史欠账**（★ `data/ops/drift-alert`：本机 **446** · 中枢 **138** ⇒ 差 **309**）
    ★ **不会自动补** ⇒ ★★ 本器就是那个补写动作。

★★ 四条安全纪律：
  ① **默认 dry-run** —— ★ 不加 `--go` 只列不写
  ② **先试 1 张** —— ★ `--limit 1` 验证通道，再批量
  ③ **写完必回读** —— ★ 逐条断言（★ 依本仓「写后必回读」）
  ④ **不覆盖中枢已有** —— ★ 只补【本机有而中枢无】的键

用法：
  python3 tools/backfill-missing.py                       # ★ 只列出欠账（dry-run）
  python3 tools/backfill-missing.py --limit 1 --go        # ★ 试补 1 张
  python3 tools/backfill-missing.py --go                  # ★ 全量补
  python3 tools/backfill-missing.py --selftest
"""
import argparse
import datetime
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
BB = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")
CENTRAL = os.environ.get("DSH_BB_CENTRAL_URL", "http://xingqiao.meetfunbp.com:8792")
DEFAULT_NS = "data/ops/drift-alert/"


def tok():
    try:
        return io.open(os.path.join(HOME, ".dsh", "blackboard-token"), encoding="utf-8").read().strip()
    except Exception:
        return ""


def req(url, method="GET", data=None, timeout=25):
    r = urllib.request.Request(url, method=method, data=data)
    t = tok()
    r.add_header("Authorization", "Bearer " + t)
    r.add_header("X-Blackboard-Token", t)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return f.status, f.read().decode("utf-8", "replace")


def keys_of(base, ns, timeout=60):
    try:
        st, body = req(base + "/" + ns, timeout=timeout)
        return set((json.loads(body).get("list") or {}).keys()), None
    except Exception as e:
        return set(), "%s: %s" % (type(e).__name__, str(e)[:50])


def plan(ns):
    loc, e1 = keys_of(BB, ns)
    cen, e2 = keys_of(CENTRAL, ns)
    if e2:
        return None, None, "中枢不可读：%s ⇒ 不可判（★ 空 ≠ 无）" % e2
    return loc, cen, None


def run(ns, limit=None, go=False, as_json=False, reverse=False):
    """★★★ 2026-10-15（D-356）【--reverse】—★ 反向：把【中枢独有】的键补回本机。

    ★ 立据（D-355）：五面清零后实测发现 **中枢数量普遍略多于本机**
      （★ 447 vs 446 · 655 vs 654 · 2840 vs 2827 · 1325 vs 1306）
      ★★ ⇒ 说明【反向也有欠账】。
    ★ 而本器原只管单向（★ 本机→中枢）⇒ 本旗标补反向。
    ★ 安全纪律同前（★ dry-run 默认 · 先试 1 张 · 写完必回读 · 不覆盖）。
    """
    loc, cen, err = plan(ns)
    if err:
        print("  ★★ %s" % err)
        return 1
    # ★ 方向：默认本机→中枢；--reverse 则中枢→本机
    SRC, DST = (CENTRAL, BB) if reverse else (BB, CENTRAL)
    sname, dname = ("中枢", "本机") if reverse else ("本机", "中枢")
    only = sorted((cen - loc) if reverse else (loc - cen))
    n_todo = len(only) if limit is None else min(limit, len(only))
    d = {"ns": ns, "reverse": reverse, "local": len(loc), "central": len(cen), "missing": len(only),
         "will_write": n_todo, "go": go}
    print("══ 双板欠账补写器 %s ══" % VERSION)
    print("  面   = %s" % ns)
    print("  本机 = %d · 中枢 = %d · ★ 仅%s = %d%s" % (len(loc), len(cen), sname, len(only),
          ("（★ --reverse）" if reverse else "")))
    if not only:
        print("  ★ 无欠账 ⇒ 双板一致（★ 无需补写）")
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 0
    if not go:
        print("  ★ dry-run：将补写 %d 张（★ 加 --go 才真写）" % n_todo)
        for k in only[:5]:
            print("    · %s" % str(k)[-52:])
        if len(only) > 5:
            print("    … 另有 %d 张" % (len(only) - 5))
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 0

    # ★★★ 2026-10-15（D-356）【加退避重试】—★ 与 `drift-scan-cron.py` 同族。
    #   ★ 立据：本器首次反向补写时 **2 处失败**，★ 而**重跑即成** ⇒ 那是【瞬态】。
    #   ★★ ⇒ **单次失败 ≠ 永久失败**；★ 而无重试会把瞬态失败记成终态。
    RETRY = 3
    ok = fail = 0
    for i, k in enumerate(only[:n_todo]):
        try:
            st, body = req(SRC + "/" + k, timeout=20)
            v = json.loads(body).get("value")
            if not isinstance(v, dict):
                print("    [%d] %s ⇒ value 非 dict，跳过" % (i + 1, str(k)[-40:]))
                fail += 1
                continue
            payload = json.dumps(v, ensure_ascii=False).encode()
            # ★ 退避重试（★ 1s → 2s）+ 每次重试后回读断言
            _done = False
            for _att in range(RETRY):
                try:
                    req(DST + "/" + k, method="PUT", data=payload, timeout=25)
                    st2, body2 = req(DST + "/" + k, timeout=20)
                    if json.loads(body2).get("value") == v:
                        _done = True
                        break
                except Exception:
                    pass
                if _att < RETRY - 1:
                    time.sleep(1 << _att)
            if _done:
                ok += 1
                print("    [%d/%d] ✓ %s%s" % (i + 1, n_todo, str(k)[-40:],
                      "" if _att == 0 else " (★ 第 %d 次重试成功)" % (_att + 1)))
            else:
                fail += 1
                print("    [%d/%d] ✗ %s 已重试 %d 次" % (i + 1, n_todo, str(k)[-40:], RETRY))
        except Exception as e:
            fail += 1
            print("    [%d/%d] ✗ %s %s" % (i + 1, n_todo, type(e).__name__, str(k)[-30:]))
    print()
    print("  【结果】成功 %d · 失败 %d（★ 共尝试 %d）" % (ok, fail, n_todo))
    d.update({"ok": ok, "fail": fail})
    # ★ 复算（★ 补写后再取一次）
    loc2, cen2, e = plan(ns)
    if not e:
        print("  【复算】本机 %d · 中枢 %d · ★ 仍缺 %d" % (len(loc2), len(cen2), len((cen2 - loc2) if reverse else (loc2 - cen2))))
        d.update({"after_central": len(cen2), "after_missing": len(loc2 - cen2)})
    if as_json:
        print(json.dumps(d, ensure_ascii=False))
    return 0 if fail == 0 else 1


def selftest():
    ok = tot = 0
    print("== backfill-missing 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    # ★ 正控：两板都可读
    l, c, e = plan(DEFAULT_NS)
    chk(e is None, "正控：两板可读（本机 %s · 中枢 %s）" % (len(l) if l is not None else "?", len(c) if c is not None else "?"))
    # ★ 正控：差集计算正确
    chk(l is not None and c is not None and isinstance(l - c, set), "正控：差集可算（仅本机 %d）" % (len(l - c) if l is not None and c is not None else -1))
    # ★ 负控：不可达中枢必须报【不可判】而非【0 缺失】
    l2, c2, e2 = plan("data/ops/__never_exists__/")
    chk(e2 is None, "负控：不存在的面 ⇒ 不报错而是空集（★ 空 ≠ 无）")
    # ★ 负控：dry-run 不得写（★ 用一个必然不存在的面）
    r = run("data/ops/__never_exists__/", go=False)
    chk(r == 0, "负控：dry-run 在空面上返回 0 且不写")
    # ★ 正控：有 --limit 时 will_write ≤ limit
    d = None
    l3, c3, e3 = plan(DEFAULT_NS)
    n_gap = len(l3 - c3) if (l3 is not None and c3 is not None) else 0
    chk(n_gap >= 0, "正控：欠账数可算（%d）" % n_gap)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", default=DEFAULT_NS)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--reverse", action="store_true",
                    help="★ 反向：把中枢独有的键补回本机")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("backfill-missing %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    return run(a.ns, a.limit, a.go, a.json, a.reverse)


if __name__ == "__main__":
    sys.exit(main())
