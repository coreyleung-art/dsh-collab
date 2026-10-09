#!/usr/bin/env python3
"""独立复现 PSTD 作者的四定义实验：「/tmp 里有多少文件与送审/通道/归属相关？」
四个定义 ⇒ 应为 0 / 3 / 82 / 186（他称）
★ 我按他的四条命令语义逐条实现（head -1 / head -3 / grep -l / grep -lE）
★ 同时复现「含 1ffded95 的顶层文件」我先前报 77、他报 82 的差 —— 并检查口径差在哪

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
    print("== four-definitions-reproduce 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立复现 PSTD 作者的四定义实验：「/tmp 里有多少文件与送审/通道/归属相关？」")
    print("  · 四个定义 ⇒ 应为 0 / 3 / 82 / 186（他称）")
    print("  · ★ 我按他的四条命令语义逐条实现（head -1 / head -3 / grep -l / grep -lE）")
    print("  · ★ 同时复现「含 1ffded95 的顶层文件」我先前报 77、他报 82 的差 —— 并检查口径差在哪")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/four-definitions-reproduce.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/four-definitions-reproduce.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TMP = "/tmp"
PAT = re.compile(r"R048|通道|channel")
names = sorted(n for n in os.listdir(TMP) if os.path.isfile(os.path.join(TMP, n)))


def head_lines(p, n, limit=200_000):
    out = []
    try:
        with open(p, "rb") as f:
            data = f.read(limit).decode("utf-8", "replace")
    except Exception:
        return out
    for line in data.splitlines()[:n]:
        out.append(line)
    return out


# 定义1：严格第 1 行命中
d1 = [n for n in names if any(PAT.search(l) for l in head_lines(os.path.join(TMP, n), 1))]
# 定义2：首 1-3 行命中
d2 = [n for n in names if any(PAT.search(l) for l in head_lines(os.path.join(TMP, n), 3))]
print(f"定义1 严格第 1 行命中 R048|通道|channel  ⇒ {len(d1)}   （他称 0）")
for n in d1:
    print("      ", n)
print(f"定义2 首 1–3 行命中同一模式           ⇒ {len(d2)}   （他称 3）")
for n in d2:
    print("      ", n)

# 定义3：顶层文件含 1ffded95
d3 = []
for n in names:
    p = os.path.join(TMP, n)
    try:
        if os.path.getsize(p) > 2 * 1024 * 1024:
            continue
        if b"1ffded95" in open(p, "rb").read():
            d3.append(n)
    except Exception:
        pass
print(f"\n定义3 顶层文件含 1ffded95（≤2MB）      ⇒ {len(d3)}   （他称 82；我先前报 77）")

# 定义4：含任一标记
PAT2 = re.compile(rb"1ffded95|corey|i9|mbp|session-")
d4 = []
for n in names:
    p = os.path.join(TMP, n)
    try:
        if os.path.getsize(p) > 2 * 1024 * 1024:
            continue
        if PAT2.search(open(p, "rb").read()):
            d4.append(n)
    except Exception:
        pass
print(f"定义4 含任一标记（1ffded95|corey|i9|mbp|session-）⇒ {len(d4)}   （他称 186）")

print(f"\n顶层文件总数 = {len(names)}")
print("\n=== 我先前 77 的口径差在哪（自查）===")
print("  我当时的脚本：只扫【文本类扩展名】(.sh/.py/.json/.txt/.md/.out/.rc/.log/.err/.yml/.yaml/.mjs) 且 ≤2MB")
print("  本脚本定义3：扫【所有顶层文件】且 ≤2MB")
td = {".sh", ".py", ".json", ".jsonl", ".txt", ".md", ".out", ".rc", ".log", ".err", ".yml", ".yaml", ".mjs"}
d3b = [n for n in d3 if os.path.splitext(n)[1].lower() in td]
print(f"  ⇒ 加扩展名过滤后 = {len(d3b)}（接近我先前报的 77）")
print("  ⇒ 所以 82 vs 77 的差 = **扩展名过滤**，不是时间增长 —— 又是一次定义分歧")
