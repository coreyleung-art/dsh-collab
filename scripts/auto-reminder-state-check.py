#!/usr/bin/env python3
"""送审③ v3 现状核查（只读）：① 三个计数器/时限文件 ② 日志全量尾部 ③ 失败路径是否被实战触发过
★ 关键：round=9/10 ⇒ 第 10 轮会自动 bootout ⇒ 这是一个"即将发生且可验"的事件，应先记录现状再核结果
"""
import os, datetime, subprocess

FILES = {
    "count": "~/.dsh/auto-reminder-count",
    "fails": "~/.dsh/auto-reminder-fails",
    "deadline": "~/.dsh/auto-reminder-deadline",
}
LOG = os.path.expanduser("~/dsh-collab/logs/auto-reminder.log")

print("=" * 74)
print("【①】计数器 / 时限文件现状")
print("=" * 74)
for label, p in FILES.items():
    fp = os.path.expanduser(p)
    if os.path.isfile(fp):
        st = os.stat(fp)
        mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M:%S")
        try:
            val = open(fp).read().strip()
        except Exception as e:
            val = f"<读取失败 {e}>"
        print(f"  {label:<9} 值={val!r:<24} mtime={mt}  size={st.st_size}")
    else:
        print(f"  {label:<9} ❌ 不存在 {p}")

d = os.path.expanduser("~/.dsh/auto-reminder-deadline")
if os.path.isfile(d):
    try:
        dl = int(open(d).read().strip())
        now = int(datetime.datetime.now().timestamp())
        print(f"\n  绝对时限 = {datetime.datetime.fromtimestamp(dl).strftime('%Y-%m-%dT%H:%M:%S')}"
              f"  剩余 = {(dl-now)/3600:.2f} h  （{'已过期' if now >= dl else '未到期'}）")
    except Exception as e:
        print("  时限解析失败", e)

print()
print("=" * 74)
print("【②】launchd 当前是否仍加载")
print("=" * 74)
r = subprocess.run("launchctl list 2>/dev/null | grep -i auto-reminder", shell=True, capture_output=True, text=True)
print("  ", (r.stdout or "").strip() or "（未加载 / 已 bootout）")

print()
print("=" * 74)
print("【③】日志：轮次轨迹 + 失败路径是否被实战触发过")
print("=" * 74)
if os.path.isfile(LOG):
    st = os.stat(LOG)
    print(f"  日志 {LOG}  size={st.st_size}  mtime="
          f"{datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')}")
    lines = open(LOG, errors="replace").read().splitlines()
    print(f"  总行数 = {len(lines)}")
    print("\n  末 12 行:")
    for l in lines[-12:]:
        print("   ", l[:150])
    n_inject = sum(1 for l in lines if "injected_ok" in l)
    n_fail = sum(1 for l in lines if "FAIL" in l)
    n_bump = sum(1 for l in lines if "连续失败" in l)
    n_ok = sum(1 for l in lines if "round=" in l and "injected_ok" in l)
    print(f"\n  ★ 成功注入记录 = {n_inject}")
    print(f"  ★ FAIL 记录 = {n_fail}")
    print(f"  ★ “连续失败 … bootout”记录 = {n_bump}   ← **为 0 则说明“失败上限”保险未被实战触发**")
    print(f"  ★ round=…injected_ok 记录 = {n_ok}")
else:
    print("  ❌ 日志不存在")
