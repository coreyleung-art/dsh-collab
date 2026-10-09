#!/usr/bin/env python3
"""复核星桥补的两条（都源自我标的未覆盖项）：
① `DEADLINE_FILE` 写入是否已加 fsync/sync（断电窗口）
② hold-out 的排序字段是否已显式化
"""
import os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/verify-two-gaps-closed.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

AR = os.path.expanduser("~/dsh-collab/tools/auto-reminder.sh")
PLAN = os.path.expanduser("~/dsh-collab/docs/systemgraph-internal-completion-plan-20261008.md")

print("=" * 74)
print("【①】auto-reminder.sh：DEADLINE 段 与 sync 分布")
print("=" * 74)
if os.path.isfile(AR):
    lines = open(AR, errors="replace").read().splitlines()
    print(f"  脚本 {len(lines)} 行")
    print("\n  L20–L35（DEADLINE 段）:")
    for i in range(19, min(35, len(lines))):
        print(f"    {i+1:>3}: {lines[i]}")
    print("\n  全脚本 sync 出现行:")
    for i, l in enumerate(lines, 1):
        if "sync" in l:
            print(f"    {i:>3}: {l.strip()[:130]}")
else:
    print("  ❌ 脚本不存在")

print()
print("=" * 74)
print("【②】方案第十节：排序字段是否显式")
print("=" * 74)
if os.path.isfile(PLAN):
    txt = open(PLAN, errors="replace").read()
    for i, l in enumerate(txt.splitlines(), 1):
        if re.search(r"排序|time_field|时间字段|holdout-split|复跑手段", l):
            print(f"    {i:>3}: {l.strip()[:160]}")
else:
    print("  ❌ 方案不存在")

print()
print("=" * 74)
print("【③】holdout-split.py 自检输出里的排序字段")
print("=" * 74)
import subprocess, tempfile, json
SC = os.path.expanduser("~/dsh-collab/scripts/holdout-split.py")
if os.path.isfile(SC):
    td = tempfile.mkdtemp(prefix="holdout-field-")
    inp = os.path.join(td, "in.json")
    json.dump([{"id": f"L{i}", "ts": f"2026-10-{i+1:02d}T00:00:00"} for i in range(20)], open(inp, "w"))
    r = subprocess.run(["python3", SC, "--input", inp], capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    for l in out.splitlines():
        if any(k in l for k in ("time_field", "holdout", "total", "digest", "untimed")):
            print("   ", l.strip()[:160])
else:
    print("  ❌ 脚本不存在")
