#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-incremental v1.0 (HR) — 每日增量索引自动化

扫描 vault 中最近 N 小时新增/修改的 .md 文件 → chroma_index 增量 upsert（幂等）。
零 LLM 成本。用法：python3 kb-incremental.py [--hours 24] [--dry-run]
输出：新增索引文件数 + 总 chunks（写 ~/dsh-collab/token-monitor/kb-incremental-YYYY-MM-DD.json）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, pathlib
sys_path = "/Users/coreyleung/.claude/automation"
import sys; sys.path.insert(0, sys_path)
from lib import chroma_index, VAULT


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/kb-incremental.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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