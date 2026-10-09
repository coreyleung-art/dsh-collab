#!/usr/bin/env python3
"""定位「未归因」来源假设：bb-card-send.log 的 IO 是否显著慢于对照？
★ 本脚本纯读（stat + read），不写任何被审对象。
★ 带【双对照】：
   阳性对照 = bb-card-send.log（被怀疑的载体）
   阴性对照 = 同机另一个普通文件（对照组）
   ⇒ 若两者量级相同 ⇒ 不是该目录的问题；若被怀疑者显著慢 ⇒ 假设得到支持

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, time, statistics, tempfile

SUSPECT = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
CONTROL = os.path.expanduser("~/dsh-collab/rules-registry/RULES.md")
TMPCTRL = os.path.join(tempfile.gettempdir(), "io-ctrl.txt")
open(TMPCTRL, "w").write("x" * 1000)


def bench(path, n_stat=30, n_read=10):
    st = []
    for _ in range(n_stat):
        t = time.perf_counter()
        try:
            os.stat(path)
        except Exception as e:
            return None, None, str(e)
        st.append((time.perf_counter() - t) * 1000)
    rd = []
    for _ in range(n_read):
        t = time.perf_counter()
        try:
            with open(path, "rb") as f:
                f.read()
        except Exception as e:
            return st, None, str(e)
        rd.append((time.perf_counter() - t) * 1000)
    return st, rd, None


print("=" * 74)
print("IO 延迟基准（毫秒）")
print("=" * 74)
for label, p in (("被怀疑：bb-card-send.log", SUSPECT),
                 ("对照1：RULES.md（同 ~/dsh-collab）", CONTROL),
                 ("对照2：/tmp 小文件", TMPCTRL)):
    st, rd, err = bench(p)
    if err:
        print(f"  {label}: 失败 {err}")
        continue
    print(f"  {label}")
    print(f"    stat × {len(st)}: 中位 {statistics.median(st):.3f}ms  最大 {max(st):.3f}ms")
    if rd:
        print(f"    read × {len(rd)}: 中位 {statistics.median(rd):.3f}ms  最大 {max(rd):.3f}ms")
    print(f"    文件大小 = {os.path.getsize(p)} B")

print()
print("=" * 74)
print("判读")
print("=" * 74)
print("  若 bb-card-send.log 与对照组同量级（亚毫秒）⇒ **不支持**「logLine 慢」假设")
print("  若显著慢（几十/几百 ms）⇒ 支持「appendFileSync + mkdirSync 每次执行」是未归因的来源")
print("  ⇒ 注意：本脚本只读；真实的 logLine 是【同步写 + 每次 mkdirSync】⇒ 写通常比读更慢，")
print("     若读已慢，写更可能慢；若读很快，仍需另找解释（例如 fsync 或目录竞争）")
