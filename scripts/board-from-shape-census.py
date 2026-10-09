#!/usr/bin/env python3
"""独立复核独立复核员的「板层 from 形态普查」
他称：修复后窗口板层 PUT 1,895 条 ⇒ 其中修复插件写入 27（1.4%）；其余 1,868 条 from 形态混乱
      （完整 session id 357 / 自由标签 1,511 / 完全缺 80）
我用自己的口径独立取板上的键，统计 from 形态 —— 不采信他的数

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
    print("== board-from-shape-census 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立复核独立复核员的「板层 from 形态普查」")
    print("  · 他称：修复后窗口板层 PUT 1,895 条 ⇒ 其中修复插件写入 27（1.4%）；其余 1,868 条 from 形态混乱")
    print("  · （完整 session id 357 / 自由标签 1,511 / 完全缺 80）")
    print("  · 我用自己的口径独立取板上的键，统计 from 形态 —— 不采信他的数")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/board-from-shape-census.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, re, urllib.request, collections, random

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/board-from-shape-census.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LOCAL = "http://127.0.0.1:8792/"
FULL_ID = re.compile(r"^session-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
SHORT_ID = re.compile(r"^session-[0-9a-f]{8}$", re.I)


def fetch(url, t=25):
    try:
        r = urllib.request.urlopen(url, timeout=t)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return f"ERR:{type(e).__name__}", None


# 取一个较大的域（notes 全域的键列表）
s, d = fetch(LOCAL + "notes/?limit=1000")
if not isinstance(d, dict):
    print("列表失败", s)
    raise SystemExit(1)
keys = list((d.get("list") or {}).keys())
total = d.get("total")
print(f"notes/ total = {total}   本页键数 = {len(keys)}")

random.seed(11)
sample = random.sample(keys, min(150, len(keys)))
print(f"抽样 = {len(sample)} 键\n")

shapes = collections.Counter()
labels = collections.Counter()
missing = []
for k in sample:
    s, v = fetch(LOCAL + k)
    if not isinstance(v, dict):
        shapes["取不到"] += 1
        continue
    val = v.get("value")
    if not isinstance(val, dict):
        shapes["value 非 dict"] += 1
        continue
    fr = val.get("from")
    if fr is None or fr == "":
        shapes["缺 from"] += 1
        missing.append(k)
    elif FULL_ID.match(str(fr)) or SHORT_ID.match(str(fr)):
        shapes["session id 形态"] += 1
    else:
        shapes["自由标签"] += 1
        labels[str(fr)[:40]] += 1

print("=== from 形态分布（我的抽样）===")
for k, n in shapes.most_common():
    print(f"  {k:<20} {n:>4}  ({n/len(sample)*100:.1f}%)")

print("\n=== 自由标签 top 12 ===")
for k, n in labels.most_common(12):
    print(f"  {n:>3}  {k}")

print("\n=== 缺 from 的键（前 8）===")
for k in missing[:8]:
    print("   ", k)

print("\n=== 判读 ===")
print("  若自由标签占多数且缺 from 非零 ⇒ **支持他的结论：板层 from 不是可依赖的归属载体**")
print("  注意：我的抽样口径是 notes/ 随机 150 键，与他的“修复后窗口 PUT 1,895 条”口径不同")
print("        ⇒ 两者只能比**形态比例的量级**，不能比绝对数")
