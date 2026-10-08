#!/usr/bin/env python3
"""复核独立复核员的两项：① 「轮转前先写快照」是否可验（用 mtime 做独立载体）
② 「风暴期地平线可短至 14 分钟」是构造上界还是观测值
"""
import os, glob, datetime, json

DD = "/Users/coreyleung/dsh-collab/token-monitor/blackboard"
AUDIT_ROTATE_BYTES = 5 * 1024 * 1024
ARCHIVE_KEEP = 10


def mt(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%dT%H:%M:%S")


print("=== ① 快照写入时机（独立载体：mtime）===")
snap = os.path.join(DD, "snapshot.json")
cur = os.path.join(DD, "audit.jsonl")
print(f"snapshot.json  mtime = {mt(snap)}  size = {os.path.getsize(snap)}")
print(f"audit.jsonl    mtime = {mt(cur)}   size = {os.path.getsize(cur)}")
files = sorted(glob.glob(os.path.join(DD, "audit-*.jsonl")))
print("\n轮转文件 mtime（应 ≈ 各自轮转时刻）:")
for f in files:
    print(f"  {os.path.basename(f):<34} mtime = {mt(f)}")

# 轮转文件 mtime 降序 = 轮转时刻序列；最近一次轮转 = audit.jsonl 的创建/最早
print("\n源码对照：")
print("  store.rs:378  if size <= AUDIT_ROTATE_BYTES { return; }")
print("  store.rs:380  self.write_snapshot_inner();   ← 快照在归档之前")
print("  store.rs:384  fs::rename(&ap, &arch);")
print("  ⇒ 若声称成立：snapshot.json 的 mtime 应 ≈ 最近一次轮转时刻（与 audit.jsonl 起算同刻）")

print()
print("=== ② 地平线：上界（风暴）vs 观测值 ===")
# 观测
def ep(ts):
    return int(datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").timestamp())

data = []
for f in sorted(glob.glob(os.path.join(DD, "audit*.jsonl"))):
    fin = flo = None
    n = 0
    with open(f, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            n += 1
            if fin is None:
                fin = e
            flo = e
    if fin:
        data.append((os.path.basename(f), os.path.getsize(f), n, fin.get("ts"), flo.get("ts")))
obs_min = min(d[3] for d in data if d[3])
obs_max = max(d[4] for d in data if d[4])
obs_span = ep(obs_max) - ep(obs_min)
print(f"观测地平线 = {obs_span}s = {obs_span//3600}h{(obs_span%3600)//60}m{obs_span%60}s  ({obs_min} → {obs_max})")
print("\n各文件耗时（秒）与速率:")
for name, size, n, t1, t2 in data:
    if t1 and t2:
        dur = ep(t2) - ep(t1)
        rate = n / dur * 60 if dur else 0
        print(f"  {name:<34} {size/1048576:>5.2f}MB {n:>6}条 {dur:>6}s  {rate:>8.0f} 条/分")

# 上界：若 10 个文件全部以最快文件速率写满
fastest = min(((ep(d[4]) - ep(d[3])), d[0], d[2]) for d in data if d[3] and d[4] and (ep(d[4]) - ep(d[3])) > 0)
print(f"\n最快文件：{fastest[1]}  写满 5MB 用 {fastest[0]}s（{fastest[2]} 条）")
print(f"⇒ 构造上界地平线 = {fastest[0]}s × {ARCHIVE_KEEP} = {fastest[0]*ARCHIVE_KEEP}s "
      f"= {fastest[0]*ARCHIVE_KEEP//60}m{fastest[0]*ARCHIVE_KEEP%60}s")
print(f"⇒ 观测地平线     = {obs_span}s = {obs_span//60}m{obs_span%60}s")
print(f"⇒ 比值 = 观测/上界 = {obs_span/(fastest[0]*ARCHIVE_KEEP):.1f}x")
print("\n判读：14 分钟成立的条件是【风暴持续到 10 个文件全部写满】；")
print("      本次观测中风暴只有 1 个文件（其余 20–30 分钟/文件）⇒ 14 分钟是构造上界，不是观测值。")
