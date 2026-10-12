#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S11 黑板数据体积 / snapshot / DELETE 次数 —— 现测口径

★ 黑板进程实参（现读，不写死）：
  ps -o command= -p $(pgrep -f rust-blackboard | head -1) | tr ' ' '\n' | grep -A1 data-dir
★ DELETE 判据取自 audit*.jsonl 的 action 字段，而不是 grep 文本里的 'DELETE'
  —— grep 'DELETE' 会命中 payload 内容（实测 1140 行命中，而 action 字段里 DELETE = 0）。
"""
import glob, json, os, subprocess, collections

# 1) 现读 data-dir（★ 不写死路径）
# ★ 不能用 `pgrep -f 'rust-blackboard .*--port'`：ps 里的进程名被截断成 `rust-blac`，
#   但**完整路径**在 argv 里 ⇒ 用更宽的锚 'rust-blackboard-macos'（实测稳定命中）。
pid = subprocess.run("pgrep -f 'rust-blackboard-macos' | head -1", shell=True,
                     capture_output=True, text=True).stdout.strip()
datadir = None
if pid:
    cmd = subprocess.run(["ps", "-o", "command=", "-p", pid],
                         capture_output=True, text=True).stdout
    parts = cmd.split()
    if "--data-dir" in parts:
        datadir = parts[parts.index("--data-dir") + 1]
print("黑板 pid =", pid or "（未找到进程）")
print("data-dir =", datadir or "（不可判）")
if not datadir or not os.path.isdir(datadir):
    print("★ data-dir 不可读 ⇒ 体积/DELETE 均【不可判】")
    raise SystemExit(3)

def du(p):
    out = subprocess.run(["du", "-sk", p], capture_output=True, text=True).stdout
    return int(out.split()[0]) * 1024 if out.strip() else 0

print()
print("整目录体积 = %.1f MiB" % (du(datadir) / 1048576.0))
snap = os.path.join(datadir, "snapshot.json")
print("snapshot.json = %.1f MiB" % (os.path.getsize(snap) / 1048576.0 if os.path.exists(snap) else -1))
audits = sorted(glob.glob(os.path.join(datadir, "audit*.jsonl")))
tot = sum(os.path.getsize(a) for a in audits)
print("audit 文件数 = %d · 合计 %.1f MiB" % (len(audits), tot / 1048576.0))

# 2) DELETE：读 action 字段（非 grep 文本）
acts = collections.Counter()
lines = 0
for a in audits:
    for ln in open(a, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        lines += 1
        try:
            o = json.loads(ln)
        except Exception:
            continue
        acts[o.get("action") or o.get("op") or o.get("method")] += 1
print()
print("audit 总行数 = %d" % lines)
print("action 字段分布 =", acts.most_common())
print("★ DELETE 次数（action 口径）= %d" % acts.get("DELETE", 0))
print()
print("★ 口径声明：audit 只覆盖它自己轮转窗口内的行；更早的行已轮转掉 ⇒")
print("  「DELETE=0」只能读成【本窗口内 0】，不能读成【历史上从未 DELETE】。")
