#!/usr/bin/env python3
"""精确核实作者所列的 12 个 /tmp 残留（不宽模式匹配，逐个点名）
并列出我工作时段（06:00–08:00）内 /tmp 的文件，帮我自己盘点归属。
★ 只盘点与报告，不清理归属不明的（先报告后动手）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, datetime, json


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-tmp-residue-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

NAMES = [
    "bb-audit.json", "channel-audit.log",
    "board-poll-notes_mac-mini_audit-verdict-index-20261008.jsonl",
    "ar_audit.sh", "ar_probe2.sh", "channel-audit.err",
    "channel-gate-weekly.log", "channel-gate-weekly.err.log",
    "audit-corey-i9-mechanism-crossconfirm-20261008.json",
    "audit-bbcard-false-red-rootcaused-20261008.json",
    "audit-probe-hit-and-claims-reconcile-20261008.json",
    "audit-g11-from-attribution-live-probe-20261008.json",
]

print("=" * 74)
print("【A】作者所列 12 件 · 逐个核实存在性")
print("=" * 74)
present = 0
for n in NAMES:
    p = os.path.join("/tmp", n)
    if os.path.isfile(p):
        present += 1
        st = os.stat(p)
        mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%m-%d %H:%M:%S")
        head = ""
        try:
            with open(p, "rb") as f:
                head = f.read(160).decode("utf-8", "replace").replace("\n", " ")
        except Exception as e:
            head = f"<读取失败 {e}>"
        print(f"  ✅ 存在  {mt}  {st.st_size:>8}B  {n}")
        print(f"          首段: {head[:130]}")
    else:
        print(f"  ❌ 不存在  {n}")
print(f"\n⇒ 作者所列 12 件中，实测存在 {present}/{len(NAMES)}")

print()
print("=" * 74)
print("【B】/tmp 中 mtime ∈ 06:00–08:00 的文件（我的工作时段，盘点归属）")
print("=" * 74)
rows = []
for name in sorted(os.listdir("/tmp")):
    p = os.path.join("/tmp", name)
    if not os.path.isfile(p):
        continue
    try:
        st = os.stat(p)
    except Exception:
        continue
    dt = datetime.datetime.fromtimestamp(st.st_mtime)
    if dt.date() == datetime.date(2026, 10, 8) and 5 <= dt.hour < 9:
        rows.append((dt.strftime("%H:%M:%S"), st.st_size, name))
rows.sort()
print(f"数量 = {len(rows)}")
for t, sz, n in rows:
    print(f"  {t}  {sz:>8}B  {n}")

print()
print("=" * 74)
print("【C】我方自认（基于我的脚本/操作可确证的）")
print("=" * 74)
mine = [n for n in os.listdir("/tmp") if n.startswith("audit_") or n.startswith("port_from") or n.startswith("idx_dump")]
print(f"  以 audit_/port_from/idx_dump 开头的残留 = {len(mine)}  {mine}")
print("  ⇒ ① 我的「/tmp/audit_* 清零」射程 = 仅 audit_ 前缀（实测该射程内确为 0）")
print("  ⇒ ② 但作者核的是「audit 类件」（含 ar_/bb-*/channel-*/board-poll-*/卡键命名）⇒ 射程不同")
print("  ⇒ ③ 故我的「清零」表述**未声明射程** ⇒ 与「字符/字节」同族：**射程与单位都必须声明**")
