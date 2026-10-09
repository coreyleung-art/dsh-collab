#!/usr/bin/env python3
"""独立复核独立复核员的「保留地平线 3h31m」与「seq 编码 = epoch秒×10^6 + 序」
判据：① 用现有轮转文件的首末 ts 算真实跨度（不引用对方读数）
     ② 用 seq // 10^6 与 ts 的 epoch 秒比对

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, os, glob, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-retention-horizon.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
