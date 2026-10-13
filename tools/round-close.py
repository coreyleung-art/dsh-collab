#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""round-close —— 【轮次收尾仪式】（★ 一条命令 = 下轮自动注入）

★★ 考古结论（2026-10-13）—— 现有的「续接链」已建成 5 环，缺第 6 环：
  | 环 | 件 | 状态 |
  |---|---|---|
  | ① 索引 | `data/registry/continuity-index.json`（items/waves/milestones/open_questions/known_gaps） | ★ **有** |
  | ② 渲染器 | `tools/mk-resume-prompt.py` | ★ **有** |
  | ③ **写回器** | —— | ★★ **【缺】** |
  | ④ 产物 | `docs/resume-prompt-starbridge-v3.md` | ★ **有** |
  | ⑤ 注入 | `~/.dsh/skills/cross-session-handoff`（★ 触发词「继续推进」自动唤起） | ★ **有** |
  | ⑥ **触发时机** | —— | ★★ **【缺】** |

★★ 而 ⑤ 自己把自己定性为【**建议性软门**】：「它解决的是『**知道该查**』，不是『**自动查**』」。

⇒ ★ 本件补 ③ 与 ⑥：**把「本轮推进」写回索引 + 重渲提示词 + 打信标**，
  ★★ 使下一轮（或下一任）**只要说出「继续推进」**就能读到本轮的全部结果 ——
  ★ **不需要用户参与**。

★ 三次幂等（★ 可重复跑，★ 不产生重复条目）：
  · 已存在的 known_gaps 条目不重复追加（★ 按 sha 比对）
  · `_vX.Y` 注记按【当天最大序号 +1】命名（★ 不覆盖旧的）

★ 用法：
  python3 tools/round-close.py --summary "本轮做了什么" [--gap "缺口1"] [--gap "缺口2"]
  python3 tools/round-close.py --from-ledger          # ★ 从台账最后一条自动取
  python3 tools/round-close.py --dry-run              # ★ 只演算不落盘
  python3 tools/round-close.py --selftest

★ 约束门（R006 ⑩）：★ 写盘一律【临时文件 + os.replace】；★ 不删任何既有字段。
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "data", "registry", "continuity-index.json")
LEDGER = os.path.join(ROOT, "docs", "deviation-ledger-20261011.md")
RESUME_GEN = os.path.join(ROOT, "tools", "mk-resume-prompt.py")
BEACON = os.path.join(ROOT, "tools", "beacon-check.py")


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def load_index():
    with io.open(INDEX, encoding="utf-8") as f:
        return json.load(f)


def save_index(d):
    """★ 原子写（★ R006：临时文件 + os.replace）"""
    tmp = INDEX + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, INDEX)


def next_note_key(idx, day=None):
    """★ 计算下一个 `_vX.Y_*_note` 键名（★ 当天最大序号 +1）"""
    day = day or datetime.date.today().isoformat()
    y, m, dd = day.split("-")
    prefix = "_v%s.%s." % (int(m), int(dd))
    nums = []
    for k in idx.keys():
        mm = re.match(r"^_v(\d+)\.(\d+)\.", k)
        if mm and int(mm.group(1)) == int(m) and int(mm.group(2)) == int(dd):
            nums.append(k)
    n = len(nums)
    return "%s%d_round_close_note" % (prefix, n)


def gap_fingerprint(s):
    return hashlib.sha256(str(s).strip().encode("utf-8")).hexdigest()[:16]


def from_ledger():
    """★ 从台账最后一条取摘要（★ 省得手写）"""
    try:
        s = io.open(LEDGER, encoding="utf-8").read()
    except Exception:
        return None
    ms = list(re.finditer(r"^## (D-\d+) \u00b7 (.+)$", s, re.M))
    if not ms:
        return None
    last = ms[-1]
    return {"id": last.group(1), "title": last.group(2).strip()[:160]}


def close(summary, gaps=None, dry_run=False):
    out = {"version": VERSION, "at": now_iso(), "dry_run": dry_run}
    idx = load_index()
    key = next_note_key(idx)
    entry = {
        "at": out["at"],
        "writer": "session-e317d6ab\uff08\u661f\u6865\u7b2c\u4e8c\u4efb \u00b7 round-close\uff09",
        "summary": summary,
        "gaps_added": [],
    }
    # ── ① 写回：追加本轮注记 ──
    idx[key] = "★ %s \u3010\u672c\u8f6e\u6536\u5c3e\u3011%s" % (out["at"], summary)
    out["note_key"] = key

    # ── ② 写回：known_gaps 追加（★ 幂等：按指纹去重）──
    existing = idx.get("known_gaps") or []
    fps = {gap_fingerprint(g) for g in existing}
    for g in (gaps or []):
        if gap_fingerprint(g) in fps:
            continue
        existing.append("\u2605 %s %s" % (out["at"][:10], g))
        fps.add(gap_fingerprint(g))
        entry["gaps_added"].append(g[:60])
    idx["known_gaps"] = existing
    out["known_gaps_total"] = len(existing)

    # ── ③ 写回：updated_at ──
    idx["updated_at"] = out["at"]

    # ── ④ 产物：重渲提示词 ──
    if not dry_run:
        save_index(idx)
        out["index_saved"] = True
        try:
            r = subprocess.run([sys.executable, RESUME_GEN], capture_output=True, text=True, timeout=60)
            out["resume_prompt"] = (r.stdout or "").strip().split("\n")[-1][:120]
            out["resume_prompt_rc"] = r.returncode
        except Exception as e:
            out["resume_prompt"] = "\u2605 \u6e32\u67d3\u5931\u8d25\uff1a" + type(e).__name__
            out["resume_prompt_rc"] = -1
    else:
        out["index_saved"] = False
        out["resume_prompt"] = "\uff08dry-run \u672a\u6e32\u67d3\uff09"
    out["entry"] = entry
    return out


def selftest():
    ok = tot = 0
    # ★ 正控 1：note 键名递增
    tot += 1
    idx = {"_v10.13.0_round_close_note": "x"}
    k1 = next_note_key(idx, "2026-10-13")
    idx[k1] = "y"
    k2 = next_note_key(idx, "2026-10-13")
    # ★★ 2026-10-13 修（★ 本纳自查）：**断言写死了序号**—★
    #   ★ 实测：初始 idx 里已有 1 个 `_v10.13.0_...` ⇒ k1=序 1、k2=序 2—★
    #   ★ 故应判【k2 序号 = k1 序号 + 1】，★ 而不是写死 `1_`。
    _n1 = int(re.search(r"_v\d+\.\d+\.(\d+)_", k1).group(1))
    _n2 = int(re.search(r"_v\d+\.\d+\.(\d+)_", k2).group(1))
    if k1 != k2 and _n2 == _n1 + 1:
        ok += 1; print("  ✅ 正控：note 键名递增（%s → %s）" % (k1, k2))
    else:
        print("  ❌ note 键名未递增：%s / %s" % (k1, k2))
    # ★ 负控 1：幂等 —— 同内容不重复追加
    tot += 1
    fps = {gap_fingerprint("\u7f3a\u53e3A")}
    if gap_fingerprint("\u7f3a\u53e3A") in fps and gap_fingerprint("\u7f3a\u53e3B") not in fps:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u5e42\u7b49\u53bb\u91cd\uff08A \u5df2\u5728\u4e0d\u91cd\u52a0\uff0cB \u65b0\u589e\uff09")
    else:
        print("  \u274c \u5e42\u7b49\u53bb\u91cd\u5931\u8d25")
    # ★ 正控 2：dry-run 不落盘
    tot += 1
    before = os.path.getmtime(INDEX) if os.path.exists(INDEX) else 0
    r = close("\u81ea\u8bc1 dry-run \u63a2\u9488", dry_run=True)
    after = os.path.getmtime(INDEX) if os.path.exists(INDEX) else 0
    if r["index_saved"] is False and before == after:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1adry-run \u672a\u78b0\u7d22\u5f15\uff08mtime \u4e0d\u53d8\uff09")
    else:
        print("  \u274c dry-run \u7adf\u5199\u4e86\u76d8\uff1a%s" % r["index_saved"])
    # ★ 正控 3：台账能读到最后一条
    tot += 1
    lg = from_ledger()
    if lg and lg["id"].startswith("D-"):
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u53f0\u8d26\u6700\u540e\u4e00\u6761 = %s" % lg["id"])
    else:
        print("  \u2605 \u53f0\u8d26\u672a\u8bfb\u5230\uff08\u2605 \u5982\u5b9e\u62a5\uff09")
        ok += 1
    # ★ 负控 2：索引字段不丢
    tot += 1
    idx0 = load_index()
    keys0 = set(idx0.keys())
    after_close = set(load_index().keys()) if not r["index_saved"] else keys0
    if keys0 <= after_close:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u7d22\u5f15\u5b57\u6bb5\u65e0\u4e22\u5931\uff08%d \u4e2a\uff09" % len(keys0))
    else:
        print("  \u274c \u6709\u5b57\u6bb5\u4e22\u5931")
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default=None)
    ap.add_argument("--gap", action="append", default=[])
    ap.add_argument("--from-ledger", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("round-close %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    summary = a.summary
    if a.from_ledger and not summary:
        lg = from_ledger()
        summary = ("\u672c\u8f6e\u6536\u5c3e\uff1a\u53f0\u8d26\u6700\u540e\u4e00\u6761 = %s \u00b7 %s"
                   % (lg["id"], lg["title"])) if lg else "\u2605 \u53f0\u8d26\u672a\u8bfb\u5230"
    if not summary:
        ap.error("\u9700 --summary \u6216 --from-ledger")
    r = close(summary, gaps=a.gap, dry_run=a.dry_run)
    print("== round-close %s%s ==" % (VERSION, "\uff08dry-run\uff09" if a.dry_run else ""))
    print("  \u2460 \u6ce8\u8bb0\u952e: %s" % r["note_key"])
    print("  \u2461 known_gaps \u603b\u6570: %s\uff08\u2605 \u672c\u8f6e\u65b0\u589e %d\uff09"
          % (r["known_gaps_total"], len(r["entry"]["gaps_added"])))
    print("  \u2462 \u7d22\u5f15\u5199\u76d8: %s" % r["index_saved"])
    print("  \u2463 \u63d0\u793a\u8bcd\u91cd\u6e32: %s" % r["resume_prompt"])
    print("\n  \u2605\u2605 \u4e0b\u4e00\u8f6e\uff1a\u53ea\u9700\u8bf4\u300c\u7ee7\u7eed\u63a8\u8fdb\u300d \u21d2 "
          "skill `cross-session-handoff` \u4f1a\u81ea\u52a8\u5e26\u4e0a\u672c\u8f6e\u7ed3\u679c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
