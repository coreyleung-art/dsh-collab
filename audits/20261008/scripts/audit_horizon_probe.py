#!/usr/bin/env python3
"""独立复核独立复核员的「保留地平线 3h31m」与「seq 编码 = epoch秒×10^6 + 序」
判据：① 用现有轮转文件的首末 ts 算真实跨度（不引用对方读数）
     ② 用 seq // 10^6 与 ts 的 epoch 秒比对
"""
import json, os, glob, datetime

DD = "/Users/coreyleung/dsh-collab/token-monitor/blackboard"
files = sorted(glob.glob(os.path.join(DD, "audit*.jsonl")))


def ep(ts):
    try:
        return int(datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").timestamp())
    except Exception:
        return None


rows = []
for f in files:
    first = last = None
    n = 0
    with open(f, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            n += 1
            if first is None:
                first = e
            last = e
    rows.append((os.path.basename(f), os.path.getsize(f), n, first, last))

print(f"data_dir = {DD}")
print(f"轮转文件数 = {len(files)}\n")
print(f"{'文件':<34}{'字节MB':>8}{'条数':>7}  {'首ts':<21}{'末ts':<21}")
for name, size, n, fi, la in rows:
    print(f"{name:<34}{size/1048576:>8.2f}{n:>7}  {str((fi or {}).get('ts')):<21}{str((la or {}).get('ts')):<21}")

allf = [r[3] for r in rows if r[3]]
alll = [r[4] for r in rows if r[4]]
tmin = min(x.get("ts") for x in allf if x.get("ts"))
tmax = max(x.get("ts") for x in alll if x.get("ts"))
span = ep(tmax) - ep(tmin)
print(f"\n=== 地平线（全量首末） ===")
print(f"最早 = {tmin}")
print(f"最新 = {tmax}")
print(f"跨度 = {span}s = {span//3600}h{(span%3600)//60}m{span%60}s")
tot = sum(r[1] for r in rows)
print(f"总字节 = {tot/1048576:.1f} MB，总条数 = {sum(r[2] for r in rows)}")

print("\n=== seq 编码验证（seq // 10^6 vs ts 的 epoch 秒）===")
for name, size, n, fi, la in rows[:3] + rows[-3:]:
    for tag, e in (("首", fi), ("末", la)):
        if not e:
            continue
        s = e.get("seq"); t = e.get("ts"); sec = ep(t)
        if isinstance(s, int) and sec:
            print(f"  {name[:26]:<28}{tag} ts={t} seq={s} seq//1e6={s//10**6} diff={s//10**6 - sec:+d}")
    print()
