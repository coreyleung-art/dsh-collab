#!/usr/bin/env python3
"""G10/G11 复核取证：
① 刚发的卡（走新代码路径）的 `from` 是否仍是硬编码星桥 ⇒ 判 G11 是否已修
② gate.js 与 g11 备份的 diff（gate.js 从 4066 → 5181B，说明有改动）
③ core.js 的 delays 数组实际长度（他称“8 次”，但列了 7 个数字）
"""
import json, urllib.request, urllib.error, subprocess, re, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/g10-g11-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

KEY = "notes/mac-mini/r048-two-items-verified-one-command-gap-20261008"

print("=" * 74)
print("【①】G11 即时验证：我刚发的卡 from 是谁")
print("=" * 74)
for label, base in (("local", "http://127.0.0.1:8792/"), ("central", "http://106.53.214.108:8792/")):
    try:
        d = json.load(urllib.request.urlopen(base + KEY, timeout=25))
        v = d.get("value", {})
        print(f"  {label:<8} from = {v.get('from')}")
        print(f"           from_label = {v.get('from_label')}")
    except Exception as e:
        print(f"  {label} 读取失败 {e}")
print("  ⇒ 期望（若 G11 已修）：from == session-1ffded95-c401-41f3-8bec-f74f2d9790cd（裁判）")
print("     若仍为 session-fa1f9150-…（星桥）⇒ G11 未修或未生效")

print()
print("=" * 74)
print("【②】gate.js 现状 vs g11 备份")
print("=" * 74)
D = os.path.expanduser("~/dsh-plugin-bb-card-send/lib")
for f in ("gate.js", "gate.js.bak-20261008-g11"):
    p = os.path.join(D, f)
    if os.path.isfile(p):
        src = open(p, errors="replace").read()
        print(f"  {f}: {len(src)}B, {src.count(chr(10))+1} 行")
        for m in re.finditer(r"FROM_SELF|from\s*[:=]|session-|writerLabel|authorResolved", src):
            line = src[:m.start()].count("\n") + 1
            seg = src.splitlines()[line - 1].strip() if line - 1 < src.count("\n") else ""
            print(f"     L{line}: {seg[:110]}")
print()
rc = subprocess.run(f"diff '{D}/gate.js.bak-20261008-g11' '{D}/gate.js' | head -40", shell=True,
                    capture_output=True, text=True)
print("  diff（旧→新，前 40 行）:")
for l in (rc.stdout or "").splitlines():
    print("   ", l[:130])
if not (rc.stdout or "").strip():
    print("    （无差异）")

print()
print("=" * 74)
print("【③】core.js 的 delays 数组实际内容")
print("=" * 74)
src = open(os.path.join(D, "core.js"), errors="replace").read()
m = re.search(r"delays\s*=\s*\[([^\]]*)\]", src)
if m:
    nums = [x.strip() for x in m.group(1).split(",") if x.strip()]
    print(f"  delays = [{m.group(1).strip()}]")
    print(f"  ⇒ 元素个数 = {len(nums)}   （他称“8 次”；列出的数字是 5/10/20/40/60/60/45 = 7 个）")
    try:
        tot = sum(int(float(n)) for n in nums)
        print(f"  ⇒ 等待总和 = {tot}s   （他称“总窗 ≤240s”）")
    except Exception as e:
        print("  求和失败", e)
else:
    print("  ❌ 未找到 delays 数组定义（可能在别处/动态生成）")
    for i, line in enumerate(src.splitlines(), 1):
        if "delay" in line.lower():
            print(f"    L{i}: {line.strip()[:130]}")
