#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-incremental v1.0 (HR) — 每日增量索引自动化

扫描 vault 中最近 N 小时新增/修改的 .md 文件 → chroma_index 增量 upsert（幂等）。
零 LLM 成本。用法：python3 kb-incremental.py [--hours 24] [--dry-run]
输出：新增索引文件数 + 总 chunks（写 ~/dsh-collab/token-monitor/kb-incremental-YYYY-MM-DD.json）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, pathlib
sys_path = "/Users/coreyleung/.claude/automation"
import sys; sys.path.insert(0, sys_path)
from lib import chroma_index, VAULT

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cutoff = time.time() - args.hours * 3600
    files = []
    root = pathlib.Path(VAULT)
    for p in root.rglob("*.md"):
        if p.stat().st_mtime >= cutoff:
            files.append(p)
    total_chunks = 0
    done = []
    for p in sorted(files):
        rel = str(p.relative_to(root))
        if args.dry_run:
            done.append({"rel": rel, "chunks": None})
            continue
        try:
            n = chroma_index(rel, p.read_text(encoding="utf-8"))
            total_chunks += n
            done.append({"rel": rel, "chunks": n})
        except Exception as e:
            done.append({"rel": rel, "chunks": -1, "error": str(e)[:80]})
    summary = {"date": datetime.date.today().isoformat(), "hours": args.hours, "files": len(files),
               "total_chunks": total_chunks, "dry_run": args.dry_run, "items": done}
    out = os.path.expanduser("~/dsh-collab/token-monitor/kb-incremental-" + summary["date"] + ".json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("kb-incremental: files=%d chunks=%d dry=%s -> %s" % (len(files), total_chunks, args.dry_run, out))

if __name__ == "__main__":
    main()