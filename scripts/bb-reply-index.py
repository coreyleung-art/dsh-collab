#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-reply-index.py v1.0.0 —— 回执索引的【派生 + 校验】工具

★ 为什么需要它（2026-10-13 与灯塔协作产生）：
  灯塔实测「发送前先查是否已有回执」这条机制可行，但**成本高** ——
  全量枚举 notes/mac-mini/ = 2,752 键 / 14,941 KB / 0.10s。
  而我复测发现瓶颈【不是时间，是 14.6 MB 体积】，且**前缀筛发生在下载之后**
  ⇒ 「先按前缀筛」修不了成本。板也不支持服务端过滤（4 种语法实测全部返回全量）。

  ⇒ 方案：我维护一张【本地回执索引】，对方只读它 ⇒ 成本 14.6 MB → 6.9 KB（0.046%）。

★★★ 结构约束（R061 · 双表示必须定源）：
  * **单一真相源 = `reply-ledger.json`**（我手写）
  * 本索引 = **派生投影**（只读派生，不手写）
  * ⇒ 本工具只做两件事：`--build`（从台账重建）· `--check`（校验是否漂移）
  * ⇒ **索引不可能成为第二真相源** —— 因为没有任何代码路径写它而不同时写台账。

★ 用法：
  python3 bb-reply-index.py --build     # 从台账重建索引
  python3 bb-reply-index.py --check     # 校验索引与台账一致（漂移则 exit 1）
  python3 bb-reply-index.py --query <re_card_key>   # 查一张卡是否有回执
"""
import json, os, sys, argparse, datetime, hashlib

BASE = os.path.expanduser("~/dsh-collab/data/registry")
LEDGER = os.path.join(BASE, "reply-ledger.json")
INDEX = os.path.join(BASE, "reply-index.jsonl")


def _load_ledger():
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def _project(ledger):
    """★ 台账 → 索引行（纯函数，无副作用）"""
    rows = []
    for k, v in (ledger.get("entries") or {}).items():
        if not v.get("repliedAt"):
            continue
        rows.append({
            "re": k,
            "my": v.get("myCardKey"),
            "ts": v.get("repliedAt"),
            "thread": v.get("thread"),
            "dir": v.get("direction", "they-sent"),
        })
    rows.sort(key=lambda r: r["ts"] or "")
    return rows


def _read_index_rows():
    if not os.path.exists(INDEX):
        return None
    rows = []
    with open(INDEX, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "_" in r and "re" not in r:
                continue          # 首行元信息
            rows.append(r)
    return rows


def fingerprint(rows):
    """★ 内容指纹：只对【数据行】算，与元信息里的时间戳无关"""
    blob = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cmd_build(args):
    ledger = _load_ledger()
    rows = _project(ledger)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "_": "reply-index v1 · 派生自 reply-ledger.json · ★ 单一真相源=ledger，本文件只读",
            "_built": datetime.datetime.now().isoformat(),
            "_rows": len(rows),
            "_fp": fingerprint(rows),
        }, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    size = os.path.getsize(INDEX)
    print("✓ 已重建索引: %d 行 · %d B · fp=%s" % (len(rows), size, fingerprint(rows)))
    return 0


def cmd_check(args):
    ledger = _load_ledger()
    want = _project(ledger)
    got = _read_index_rows()
    if got is None:
        print("★ 索引不存在 ⇒ 请先 --build", file=sys.stderr)
        return 1
    if fingerprint(want) == fingerprint(got):
        print("✓ 索引与台账一致 · %d 行 · fp=%s" % (len(want), fingerprint(want)))
        return 0
    print("★★ 索引已漂移（台账 %d 行 / 索引 %d 行）—— 请跑 --build" % (len(want), len(got)),
          file=sys.stderr)
    wk = {r["re"] for r in want}; gk = {r["re"] for r in got}
    for k in sorted(wk - gk)[:5]:
        print("   台账有而索引无: %s" % k, file=sys.stderr)
    for k in sorted(gk - wk)[:5]:
        print("   索引有而台账无: %s" % k, file=sys.stderr)
    return 1


def cmd_query(args):
    got = _read_index_rows()
    if got is None:
        print("★ 索引不存在 ⇒ 请先 --build", file=sys.stderr)
        return 2
    hit = [r for r in got if r.get("re") == args.key]
    if not hit:
        print("无回执（★ 这张卡我没有回过）")
        return 1
    for r in hit:
        print("★ 有回执 → %s（%s）" % (r.get("my"), r.get("ts")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="从台账重建索引")
    ap.add_argument("--check", action="store_true", help="校验索引与台账一致")
    ap.add_argument("--query", metavar="RE_CARD_KEY", help="查一张卡是否有回执")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.build:
        return cmd_build(a)
    if a.check:
        return cmd_check(a)
    if a.query:
        a.key = a.query
        return cmd_query(a)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
