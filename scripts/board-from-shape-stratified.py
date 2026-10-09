#!/usr/bin/env python3
"""分层抽样重做 from 形态普查
★ 上一版暴露了我自己的一个错：从 notes/ 的列表页 random.sample(150) 得到「缺 from = 100%」——
  但抽出来的键几乎全是 `notes/8c2494e0/xingduo-wake-*`（批量自动化卡）⇒ **样本偏斜**。
  这与「用差异最小的命名空间推板级结论」同族 ⇒ 本版改为【按命名空间分层】抽样。

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
    print("== board-from-shape-stratified 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 分层抽样重做 from 形态普查")
    print("  · ★ 上一版暴露了我自己的一个错：从 notes/ 的列表页 random.sample(150) 得到「缺 from = 100%」——")
    print("  · 但抽出来的键几乎全是 `notes/8c2494e0/xingduo-wake-*`（批量自动化卡）⇒ **样本偏斜**。")
    print("  · 这与「用差异最小的命名空间推板级结论」同族 ⇒ 本版改为【按命名空间分层】抽样。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/board-from-shape-stratified.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, re, urllib.request, collections, random

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/board-from-shape-stratified.log")


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


LAYERS = ["notes/mac-mini", "notes/collab", "notes/i9", "notes/mbp",
          "data/registry", "data/ops", "data/rules", "tasks/central/queue"]
PER = 25

random.seed(7)
rows = []
for ns in LAYERS:
    s, d = fetch(f"{LOCAL}{ns}/?limit=1000")
    if not isinstance(d, dict):
        print(f"  {ns}: 列表失败 {s}")
        continue
    ks = list((d.get("list") or {}).keys())
    if not ks:
        print(f"  {ns}: 空")
        continue
    take = random.sample(ks, min(PER, len(ks)))
    stat = collections.Counter()
    lab = collections.Counter()
    for k in take:
        s2, v = fetch(LOCAL + k)
        if not isinstance(v, dict):
            stat["取不到"] += 1
            continue
        val = v.get("value")
        fr = val.get("from") if isinstance(val, dict) else None
        if fr is None or fr == "":
            stat["缺 from"] += 1
        elif FULL_ID.match(str(fr)) or SHORT_ID.match(str(fr)):
            stat["session id"] += 1
        else:
            stat["自由标签"] += 1
            lab[str(fr)[:30]] += 1
    print(f"  {ns:<24} 抽 {len(take):>3} 键  " +
          " · ".join(f"{k}={v}" for k, v in stat.most_common()) +
          (f"   标签例: {[x for x,_ in lab.most_common(3)]}" if lab else ""))
    rows.append((ns, take, stat))

print("\n=== 合计（分层）===")
tot = collections.Counter()
for ns, take, stat in rows:
    tot.update(stat)
n = sum(tot.values())
for k, v in tot.most_common():
    print(f"  {k:<14} {v:>4}  ({v/n*100:.1f}%)")
print(f"\n  总样本 = {n}")
print("\n  判读：与上一版（单层抽样得 100% 缺 from）对照 ⇒ 可见“分层”对结论的影响")
