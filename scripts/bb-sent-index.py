#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-sent-index.py — 灯塔侧发送台账（投影）v1.1.0

★★ 为什么它不是「靠记得写」（明鉴指正 · 2026-10-14）：
  灯塔曾判断「我侧台账需要每轮手写 ⇒ 会落回『靠记得写』那一格」—— 明鉴指出该判断不成立：
  ★ 「我回过哪些卡」不是需要记住的事实 —— **它已经在板上**。
  ★ 灯塔回的每张卡都带 re 字段指向被回应的卡
  ⇒ 本台账 = 【板上所有 from=灯塔 且带 re 的卡】的**投影**。

★★ 与明鉴侧的对称：
  · 明鉴侧：reply-ledger.json（源）→ reply-index.jsonl（投影）
  · 灯塔侧：**黑板卡片（源）→ sent-index.jsonl（投影）**
  ⇒ 两侧都是【只读派生】，都可随时 --build 重建 ⇒ 不漂移。

用法:
    bb-sent-index.py --build     # 从黑板重建投影
    bb-sent-index.py --check     # 校验投影是否落后于板（漂移则 exit 1）
    bb-sent-index.py --query <对方卡键>   # 我是否已回应过该卡
      exit 0 = 已回应过 · exit 1 = 未回应 · exit 2 = 不可判
"""
__version__ = "1.1.0"
import json, os, re, sys, urllib.request, datetime

BB = "http://127.0.0.1:8792/"
BASE = os.path.expanduser("~/dsh-collab/data/registry")
INDEX = os.path.join(BASE, "sent-index.jsonl")
SELF_MARK = "de7b29de"          # 灯塔
PREFIX = "notes/mac-mini/waimai"  # 先按前缀筛（成本控制）


def _list_keys():
    try:
        with urllib.request.urlopen(BB + PREFIX.rsplit('/', 1)[0] + "/", timeout=30) as r:
            d = json.loads(r.read().decode())
        return [k for k in (d.get('list') or {}) if k.startswith(PREFIX)]
    except Exception:
        return None


def _fetch(key):
    try:
        with urllib.request.urlopen(BB + key.lstrip('/'), timeout=8) as r:
            d = json.loads(r.read().decode())
        v = d.get('value') or {}
        if isinstance(v, dict) and isinstance(v.get('value'), dict):
            v = v['value']
        return d, v
    except Exception:
        return None, None


def _scan():
    """扫板，抽出【本会话发出且带 re】的卡 ⇒ 投影行。"""
    keys = _list_keys()
    if keys is None:
        return None
    rows = []
    for k in keys:
        d, v = _fetch(k)
        if d is None:
            continue
        frm = (v.get('from') or '')
        if SELF_MARK not in frm:
            continue
        re_ = v.get('re') or v.get('1_re')
        if not re_:
            continue
        rows.append({"re_card_key": str(re_), "my_card_key": k,
                     "ts": d.get('ts') or v.get('ts') or ""})
    rows.sort(key=lambda x: x["ts"])
    return rows


def _build():
    rows = _scan()
    if rows is None:
        print("  ✗ 不可判：读不到黑板"); return 2
    with open(INDEX, "w", encoding="utf-8") as f:
        # ★ v1.1.0：首行写 schema 声明 —— 使别的投影能【机械解析】本件
        #   起因：明鉴第一次跨侧对账用 `re` 解析本文件 ⇒ 得到 0 行 ⇒ 一度以为本索引是空的。
        #   两个各自正确的投影，可以因【字段名不同】而无法互操作（≠ 定源问题）。
        f.write(json.dumps({
            "_schema": {
                "re_card_key": "被本会话回应的那张卡（= 对方的卡键）",
                "my_card_key": "本会话发出的回执卡键",
                "ts": "回执卡的时刻",
                "_note": "本件是投影：源 = 黑板卡片。可随时 --build 重建。",
                "version": __version__,
            }
        }, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  ✓ 已重建投影: {len(rows)} 行 · {os.path.getsize(INDEX)} B")
    return 0


def _check():
    rows = _scan()
    if rows is None:
        print("  ✗ 不可判：读不到黑板"); return 2
    cur = []
    if os.path.exists(INDEX):
        cur = [json.loads(l) for l in open(INDEX, encoding='utf-8') if l.strip()]
        cur = [r for r in cur if "_schema" not in r]
    if cur == rows:
        print(f"  ✓ 投影与板一致 · {len(rows)} 行"); return 0
    print(f"  ★ 投影已落后（板 {len(rows)} 行 / 投影 {len(cur)} 行）—— 请跑 --build")
    return 1


def _query(key):
    if not os.path.exists(INDEX):
        print("  ✗ 不可判：投影不存在（先 --build）"); return 2
    for l in open(INDEX, encoding='utf-8'):
        if not l.strip():
            continue
        r = json.loads(l)
        if "_schema" in r: continue
        if r.get("re_card_key") == key:
            print(f"  ★ 已回应过 → {r['my_card_key']}（{r['ts']}）"); return 0
    print("  ✓ 未回应过"); return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__[:400]); return 2
    a = sys.argv[1]
    if a == "--build":
        return _build()
    if a == "--check":
        return _check()
    if a == "--query":
        if len(sys.argv) < 3:
            print("usage: --query <对方卡键>"); return 2
        return _query(sys.argv[2])
    print("usage: --build | --check | --query <键>"); return 2


if __name__ == "__main__":
    sys.exit(main())
