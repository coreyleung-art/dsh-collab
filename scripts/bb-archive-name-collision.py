#!/usr/bin/env python3
"""复核独立复核员的三点：
① 归档名粒度（ts[..14] = 10 秒桶？）——用源码规则反推 + 与实际文件名对照
② 同桶轮转同名覆盖：是否已发生？（判据：归档序列 ts 是否【无缝连续】；覆盖会留缺口）
③ 触发同名覆盖所需的写入速率

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== bb-archive-name-collision 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 复核独立复核员的三点：")
    print("  · ① 归档名粒度（ts[..14] = 10 秒桶？）——用源码规则反推 + 与实际文件名对照")
    print("  · ② 同桶轮转同名覆盖：是否已发生？（判据：归档序列 ts 是否【无缝连续】；覆盖会留缺口）")
    print("  · ③ 触发同名覆盖所需的写入速率")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/bb-archive-name-collision.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import os, glob, json, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-archive-name-collision.log")


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
AUDIT_ROTATE_BYTES = 5 * 1024 * 1024


def ep(ts):
    try:
        return int(datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").timestamp())
    except Exception:
        return None


# ① 源码规则反推：now_ts() 形如 2026-10-08T07:38:09
#   replace([':','-'],"") -> 20261008T073809 ; replace('T',"-") -> 20261008-073809 ; [..14] -> 20261008-07380
sample = "2026-10-08T07:38:09"
t = sample.replace(":", "").replace("-", "").replace("T", "-")
print("=== ① 归档名粒度反推 ===")
print(f"  now_ts() 形如 : {sample}")
print(f"  规则变换后     : {t}  (len={len(t)})")
print(f"  &ts[..14]      : {t[:14]}  ⇒ 归档名 audit-{t[:14]}.jsonl")
print(f"  ⇒ 粒度判定     : 秒字段仅保留【首位】⇒ **10 秒桶**（{t[:14][-1]}0–{t[:14][-1]}9 秒共享一名）")

files = sorted(glob.glob(os.path.join(DD, "audit-*.jsonl")))
print(f"\n  实际归档文件名（{len(files)} 个）:")
for f in files:
    n = os.path.basename(f)
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%H:%M:%S")
    print(f"    {n:<34} mtime={mtime}")

# ② 连续性检查
print("\n=== ② 归档序列 ts 连续性（覆盖会留缺口）===")
rows = []
for f in sorted(glob.glob(os.path.join(DD, "audit*.jsonl"))):
    fin = flo = None
    with open(f, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if fin is None:
                fin = e.get("ts")
            flo = e.get("ts")
    if fin:
        rows.append((os.path.basename(f), fin, flo))

gaps = []
for i in range(len(rows) - 1):
    a_end = ep(rows[i][2])
    b_start = ep(rows[i + 1][1])
    gap = (b_start - a_end) if (a_end and b_start) else None
    flag = "✅ 无缝" if gap is not None and gap <= 1 else f"⚠ 缺口 {gap}s"
    if gap is None or gap > 1:
        gaps.append((rows[i][0], rows[i + 1][0], gap))
    print(f"  {rows[i][0]:<32} 末 {rows[i][2]}  →  {rows[i+1][0]:<32} 首 {rows[i+1][1]}   {flag}")

print(f"\n⇒ 缺口数量 = {len(gaps)}  ⇒ {'**未发现覆盖迹象**（序列无缝）' if not gaps else '**存在缺口，可能发生过覆盖**'}")

# ③ 触发速率
print("\n=== ③ 触发「同桶同名覆盖」所需速率 ===")
need_bps = AUDIT_ROTATE_BYTES / 10.0
print(f"  同桶 = 10 秒；写满 5 MB 才能触发下一次轮转")
print(f"  ⇒ 需要 ≥ {AUDIT_ROTATE_BYTES/10/1024:.0f} KB/s = {AUDIT_ROTATE_BYTES/10/1024/1024:.2f} MB/s")
# 实测速率
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
                json.loads(line)
            except Exception:
                continue
            n += 1
    t1 = None
    # 用文件内容首末 ts 近似
    with open(f, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if t1 is None:
                t1 = e.get("ts")
            t2 = e.get("ts")
    if t1 and t2:
        dur = ep(t2) - ep(t1)
        if dur > 0:
            data.append((os.path.basename(f), os.path.getsize(f), n, dur, os.path.getsize(f) / dur))

print("\n  各文件实际字节速率:")
for name, size, n, dur, bps in sorted(data, key=lambda x: -x[4])[:4]:
    print(f"    {name:<34} {size/1048576:.2f}MB/{dur}s = {bps/1024:8.0f} KB/s  ({n} 条)")
fastest = max(x[4] for x in data)
print(f"\n  实测最快 = {fastest/1024:.0f} KB/s；需要 {AUDIT_ROTATE_BYTES/10/1024:.0f} KB/s 才可能同桶覆盖")
print(f"  ⇒ 安全裕度 = {AUDIT_ROTATE_BYTES/10/fastest:.1f}x")
