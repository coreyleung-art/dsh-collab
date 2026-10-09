#!/usr/bin/env python3
"""独立复核 holdout-split.py：① 自检是否真 6 例 3 负控 0 失败 ② 同输入两次 digest 是否一致
③ 空输入是否报错（负控） ④ 真实数据源是否真的 0 条
★ 只读 + 只写 /tmp 下自造输入；不碰被审对象的生产文件。
"""
import os, subprocess, json, tempfile, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/holdout-split-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SC = os.path.expanduser("~/dsh-collab/scripts/holdout-split.py")
print("=" * 74)
print("【①】脚本存在性")
print("=" * 74)
print(f"  {SC}  exists={os.path.isfile(SC)}  size={os.path.getsize(SC) if os.path.isfile(SC) else '-'}")


def run(args, timeout=120):
    r = subprocess.run(["python3", SC] + args, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


print()
print("=" * 74)
print("【②】--selftest")
print("=" * 74)
if os.path.isfile(SC):
    rc, out = run(["--selftest"])
    print(f"  exit = {rc}")
    for l in out.splitlines()[-22:]:
        print("   ", l[:150])

print()
print("=" * 74)
print("【③】同输入两次 ⇒ digest 是否一致（可复跑的核心）")
print("=" * 74)
td = tempfile.mkdtemp(prefix="holdout-verify-")
inp = os.path.join(td, "in.json")
data = [{"id": f"L{i}", "ts": f"2026-10-{i+1:02d}T00:00:00"} for i in range(20)]
json.dump(data, open(inp, "w"))
digests = []
for i in (1, 2):
    rc, out = run(["--input", inp])
    line = [l for l in out.splitlines() if "digest" in l]
    print(f"  第{i}次 exit={rc}  {line[0][:130] if line else out.strip()[:130]}")
    for l in line:
        if "holdout_digest=" in l:
            digests.append(l.split("holdout_digest=")[1].split()[0])
print(f"  ⇒ digest 两次 = {digests}  一致={len(set(digests)) == 1 if len(digests) == 2 else 'N/A'}")

print()
print("=" * 74)
print("【④】负控：空输入应报错（不是静默返回空划分）")
print("=" * 74)
empty = os.path.join(td, "empty.json")
json.dump([], open(empty, "w"))
rc, out = run(["--input", empty])
print(f"  exit = {rc}（期望非 0）")
print("  输出:", out.strip()[:200])
print(f"  ⇒ {'✅ 报错（符合其声称）' if rc != 0 else '❌ 未报错，与其文档声称不符'}")

print()
print("=" * 74)
print("【⑤】真实数据源条数（其文档声称 0 条）")
print("=" * 74)
for p in ("~/dsh-collab/data/confirmed-links.json",
          "~/dsh-collab/data/registry/confirmed-links.json",
          "~/dsh-collab/systemgraph/data/confirmed-links.json"):
    fp = os.path.expanduser(p)
    print(f"  {p}: exists={os.path.isfile(fp)}")
print("  （本项只列常见路径；未找到不等于不存在——标注为未覆盖）")
