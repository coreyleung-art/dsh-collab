#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""correction-ledger-gen — 从台账【自动生成】上一版 → 本版的更正账。

★ 立据（2026-10-12）：v7 主文里【最有价值的部分】是 `§0.0 v6.1 → v7 更正账`（22 条 + 本线自己的错 5 条），
  ★★ **而它是本线【手工拼】出来的** —— 逐条从台账誊抄、排序、补「谁发现的」。
  ★ 故本工具把它机械化：读台账 → 按【规则号/状态/时间】筛 → 渲染成 v7 体例的更正账表。

体例（★ 与 v7 §0.0 一致）：
  | # | ★ 上一版写 | ★★ 实情（现测） | ★ 谁发现 |

三态：台账不存在或读不出 ⇒ 报「不可判」；台账无条目 ⇒ 「不适用」；有则渲染。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "docs", "deviation-ledger-20261011.md")

# ★ 每条 D 条目的字段（★ 从 markdown 表里抽）
FIELD_KEYS = {
    "自核": ["自核", "自查", "本线自己"],
    "发现者": ["谁发现", "发现者", "由谁", "代理", "审查代理", "调研代理"],
    "状态": ["状态"],
}
RE_ENTRY = re.compile(r'^## (D-\d{3}) · (.*)$', re.M)
RE_ROW = re.compile(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|', re.M)


def load_entries(path=None):
    p = path or LEDGER
    if not os.path.exists(p):
        return None
    s = io.open(p, encoding="utf-8").read()
    heads = list(RE_ENTRY.finditer(s))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(s)
        body = s[h.start():end]
        rows = {}
        for m in RE_ROW.finditer(body):
            rows[m.group(1).strip()] = m.group(2).strip()
        out.append({"id": h.group(1), "title": h.group(2).strip(), "rows": rows, "body": body})
    return out


def pick_finder(rows):
    for k, alts in FIELD_KEYS.items():
        for a in alts:
            for rk, rv in rows.items():
                if a in rk:
                    return rv[:80]
    return "★ 未标"


def render(entries, only_ids=None, tail=0):
    """★ 渲染成 v7 体例的更正账表。"""
    sel = entries
    if only_ids:
        sel = [e for e in entries if e["id"] in only_ids]
    elif tail:
        sel = entries[-tail:]
    L = []
    L.append("| # | ★ 上一版写 / 事件 | ★★ 实情 | ★ 谁发现 |")
    L.append("|---|---|---|---|")
    # ★ 排除字段（★ 2026-10-12 实跑抓到：「实情」列抽到了「真实时刻」的 date 输出）
    EXCLUDE = ("真实时刻", "规则号", "审查员", "状态", "项", "出处", "引子", "交付", "用户授权")
    for n, e in enumerate(sel, 1):
        # ★ 「实情」= 该条里最像结论的一行（★ 按优先级找，且排除元数据字段）
        truth = ""
        for rk, rv in e["rows"].items():
            if any(x in rk for x in EXCLUDE):
                continue
            if any(k in rk for k in ("实情", "根因", "结论", "现测", "实测")):
                truth = rv
                break
        if not truth:
            for rk, rv in e["rows"].items():
                if any(x in rk for x in EXCLUDE):
                    continue
                truth = rv
                break
        title = re.sub(r'\s+', ' ', e["title"]).strip("★ ")[:110]
        truth = re.sub(r'\s+', ' ', truth).strip("★ ")[:150]
        L.append("| %d | ★ `%s` %s | ★★ %s | ★ %s |" % (n, e["id"], title, truth, pick_finder(e["rows"])))
    return "\n".join(L)


def summary(entries):
    """★ 统计：按状态 / 按发现者。"""
    by_state = {}
    by_finder = {}
    for e in entries:
        st = ""
        for rk, rv in e["rows"].items():
            if "状态" in rk:
                st = rv.strip("★ `")[:20]
                break
        by_state[st or "(未标)"] = by_state.get(st or "(未标)", 0) + 1
        f = pick_finder(e["rows"])
        key = "本线自核" if "本线" in f else ("代理" if "代理" in f else "(未标)")
        by_finder[key] = by_finder.get(key, 0) + 1
    return by_state, by_finder


def selftest():
    ok = tot = 0
    # ★ 正控：台账真实存在且条目数 > 100
    tot += 1
    ents = load_entries()
    if ents and len(ents) > 100:
        ok += 1
        print("  ✅ 正控：台账读到 %d 条（★ > 100）" % len(ents))
    else:
        print("  ❌ 正控：台账读不到或过少（%s）" % (len(ents) if ents else None))
    # ★ 正控：渲染非空且含表头
    tot += 1
    if ents and "上一版写" in render(ents, tail=5):
        ok += 1
        print("  ✅ 正控：渲染含表头且非空")
    else:
        print("  ❌ 正控：渲染为空或缺表头")
    # ★ 负控：不存在的 id ⇒ 空表体（★ 只剩表头两行）
    tot += 1
    r = render(ents or [], only_ids={"D-999"})
    if r.count("\n") == 1:
        ok += 1
        print("  ✅ 负控：不存在的 id ⇒ 只剩表头（可红）")
    else:
        print("  ❌ 负控：不存在的 id 竟渲染出内容")
    # ★ 负控：台账路径不存在 ⇒ load 返回 None（★ 调用方报不可判）
    tot += 1
    if load_entries("/tmp/__no_such_ledger__.md") is None:
        ok += 1
        print("  ✅ 负控：台账不存在 ⇒ None（★ 调用方报「不可判」）")
    else:
        print("  ❌ 负控：不存在的台账竟返回内容")
    # ★ 正控：每条都有 id
    tot += 1
    if ents and all(re.match(r'^D-\d{3}$', e["id"]) for e in ents):
        ok += 1
        print("  ✅ 正控：全部 id 形如 D-nnn")
    else:
        print("  ❌ 正控：存在非 D-nnn 的 id")
    # ★★ 负控（★ 2026-10-12 实跑抽错修入）：「实情」列不得抽到元数据字段
    tot += 1
    if ents:
        rows = render(ents, tail=6)
        bad = [ln for ln in rows.split("\n") if "\u2605\u2605 **2026-" in ln]
        if not bad:
            ok += 1
            print("  ✅ 负控：「实情」列未抽到「真实时刻」（★ 已排除元数据字段）")
        else:
            print("  ❌ 负控：「实情」列仍抽到时刻（%d 行）" % len(bad))
    else:
        print("  ❌ 负控：无条目可测")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=0, help="只取最后 N 条")
    ap.add_argument("--ids", default=None, help="只取这些 id（逗号分隔）")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("correction-ledger-gen 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    ents = load_entries()
    if ents is None:
        print("★ 台账不可读 ⇒ 本门【不可判】（★ 不冒充通过）: %s" % LEDGER)
        return 2
    if not ents:
        print("★ 台账无条目 ⇒ 本门【不适用】")
        return 0
    if a.json:
        print(json.dumps([{"id": e["id"], "title": e["title"]} for e in ents], ensure_ascii=False, indent=1))
        return 0
    if a.summary:
        bs, bf = summary(ents)
        print("== correction-ledger-gen 1.0.0 · 共 %d 条 ==" % len(ents))
        print("  ── 按状态 ──")
        for k, v in sorted(bs.items(), key=lambda x: -x[1])[:10]:
            print("    %-16s %d" % (k or "(空)", v))
        print("  ── 按发现者 ──")
        for k, v in sorted(bf.items(), key=lambda x: -x[1]):
            print("    %-16s %d" % (k, v))
        return 0
    ids = set(x.strip() for x in a.ids.split(",")) if a.ids else None
    print("== correction-ledger-gen 1.0.0 · 共 %d 条 · 取 %s =="
          % (len(ents), ("ids=%s" % a.ids) if ids else ("tail=%d" % a.tail if a.tail else "全部")))
    print()
    print(render(ents, only_ids=ids, tail=a.tail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
