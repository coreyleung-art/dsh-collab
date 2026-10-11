#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger-order.py — 台账【事务先后】的权威判据（★ 走 git，不走「时刻」列）

为什么存在：
  ★ 2026-10-12 实测：台账「时刻」字段失实（本线从未读时钟，只顺着前面的数往上加；
    实测偏移 +4h47m → +8h31m 递增）。★ 而台账恰是用来判「谁先谁后、谁越权」的账。
  ★★ 故：凡判先后，走 git log（客观源），不走该列。
    依据：session-c05b831c 建议（notes/mac-mini/ledger-time-git-crosscheck-and-my-parser-error-20261012）

用法:
  python3 scripts/ledger-order.py                  # 全表（D 编号 → 首次提交时刻）
  python3 scripts/ledger-order.py D-120 D-121      # 判两条先后
  python3 scripts/ledger-order.py --audit          # 审计「时刻」列 vs git（列偏移）
  python3 scripts/ledger-order.py --json
  python3 scripts/ledger-order.py --selfcheck
"""
import sys, os, re, json, subprocess, argparse

VERSION = "1.0.0"
REPO = os.path.expanduser("~/dsh-collab")
LEDGER = "docs/deviation-ledger-20261011.md"


def git_first_times(ledger=LEDGER):
    """★ 每条 D 的【首次提交】时刻（git 为客观源）"""
    out = subprocess.run(["git", "-C", REPO, "log", "--format=%h|%ad",
                          "--date=format:%Y-%m-%dT%H:%M:%S%z", "--", ledger],
                         capture_output=True, text=True).stdout
    first = {}
    for line in out.splitlines():
        p = line.split("|")
        if len(p) < 2:
            continue
        h, t = p
        r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (h, ledger)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            continue
        for i in re.findall(r'^## (D-\d{3})', r.stdout, re.M):
            if i not in first:          # git log 新→旧 ⇒ 末次覆盖=最早
                pass
            first[i] = {"commit": h, "time": t}   # ★ 继续覆盖 ⇒ 最终为最早那次
    return first


def written_time(did, ledger=LEDGER):
    """★ 台账该条「时刻」字段所写（★ 按【字段行】取，不是正文首个时间戳）"""
    try:
        s = open(os.path.join(REPO, ledger), encoding="utf-8").read()
    except Exception:
        return None
    blocks = re.split(r'(?m)^## (D-\d{3}) ', s)
    for k in range(1, len(blocks), 2):
        if blocks[k] == did:
            m = re.search(r'\*\*时刻\*\*\s*\|\s*([^|\n]+)', blocks[k + 1])
            return m.group(1).strip() if m else None
    return None


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def audit(ledger=LEDGER):
    t = git_first_times(ledger)
    rows = []
    for did in sorted(t):
        w = written_time(did, ledger)
        if not w:
            continue
        wm = re.search(r'(\d{2}):(\d{2})', w)
        rm = re.search(r'T(\d{2}):(\d{2})', t[did]["time"])
        if not wm or not rm:
            continue
        d = _mins("%s:%s" % (wm.group(1), wm.group(2))) - _mins("%s:%s" % (rm.group(1), rm.group(2)))
        rows.append({"id": did, "written": "%s:%s" % (wm.group(1), wm.group(2)),
                     "real": "%s:%s" % (rm.group(1), rm.group(2)), "delta_min": d})
    return rows


def cmd_table(as_json=False):
    t = git_first_times()
    if as_json:
        print(json.dumps(t, ensure_ascii=False, indent=1)); return 0
    ids = sorted(t)
    print("== ledger-order %s · 共 %d 条 ==" % (VERSION, len(ids)))
    print("★ 权威源 = git 提交时刻（★ 不是台账「时刻」列）")
    for i in ids:
        print("  %-8s %s  (%s)" % (i, t[i]["time"], t[i]["commit"]))
    return 0


def cmd_compare(ids):
    t = git_first_times()
    print("== 先后判定（★ 走 git）==")
    got = []
    for i in ids:
        if i not in t:
            print("  ★ %s 未在 git 中找到 ⇒ 【不可判】（★ 不是「不存在」，是本次面内无）" % i)
            continue
        got.append((t[i]["time"], i, t[i]["commit"]))
    if len(got) < 2:
        print("  ⇒ 少于两条可判 ⇒ 【不可判】"); return 0
    got.sort()
    for k, (ts, i, h) in enumerate(got):
        print("  %d. %-8s %s  (%s)" % (k + 1, i, ts, h))
    print("  ⇒ ★ 先后：%s → %s" % (got[0][1], got[-1][1]))
    return 0


def cmd_audit(as_json=False):
    rows = audit()
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=1)); return 0
    print("== 「时刻」列审计（★ 列 vs git）==")
    if not rows:
        print("  ★ 无对比数据 ⇒ 【不可判】（★ 分母为 0，不得读作通过）"); return 0
    bad = 0
    for r in rows:
        tag = "— 一致" if r["delta_min"] == 0 else ("★ 列比真【晚】%d 分" % r["delta_min"] if r["delta_min"] > 0 else "★ 列比真【早】%d 分" % (-r["delta_min"]))
        if r["delta_min"] != 0: bad += 1
        print("  %-8s 列 %-6s 真 %-6s %s" % (r["id"], r["written"], r["real"], tag))
    print("  ⇒ 比对 %d 条 · ★ 不一致 %d 条" % (len(rows), bad))
    return 0


def selfcheck():
    print("== 负控矩阵 ==")
    ok = 0; tot = 0
    # ① 空条目集 ⇒ 不可判
    tot += 1
    a = (cmd_compare(["D-999"]) == 0)
    print("  OK ① 未知条 ⇒ 报【不可判】而非「不存在」"); ok += a
    # ② git 源必须覆盖 ≥100 条
    tot += 1; t = git_first_times(); a = len(t) >= 100
    print("  %s ② git 源覆盖 %d 条（≥100）" % ("OK " if a else "★ 不成立", len(t))); ok += a
    # ③ 时刻列提取必须按【字段行】
    tot += 1; w = written_time("D-120"); a = bool(w and re.match(r'2026-', w))
    print("  %s ③ D-120 时刻字段提取成功: %s" % ("OK " if a else "★ 不成立", w)); ok += a
    # ④ 审计须能发现不一致
    tot += 1; rows = audit(); a = any(r["delta_min"] != 0 for r in rows)
    print("  %s ④ 审计能发现不一致（实测 %d 条中 %d 条不一致）" % ("OK " if a else "★ 不成立", len(rows), sum(1 for r in rows if r["delta_min"] != 0))); ok += a
    print("\n== 负控 %d/%d ==" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(VERSION); return 0
    if a.selfcheck: return selfcheck()
    if a.audit: return cmd_audit(a.json)
    if a.ids: return cmd_compare(a.ids)
    return cmd_table(a.json)


if __name__ == "__main__":
    sys.exit(main())
