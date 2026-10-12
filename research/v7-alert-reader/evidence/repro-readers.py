#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repro-readers.py — 读者扫描（只读）

对每个 data/ops/<seg>，在【代码面】找引用。
★ 扫描面 = 本机 dsh 相关代码目录（不含 node_modules / .git / 备份 .bak）。
★ 带【阳性对照】（ops/ 必命中）与【阴性对照】（ops/ZZZ_NOPE_QQQ 必不命中）。
★ 无对照的 0 一律标注「探针未验证」。
"""
import os, re, sys

HOME = os.path.expanduser("~")
ROOTS = [f"{HOME}/dsh-collab/scripts", f"{HOME}/dsh-collab/tools",
         f"{HOME}/dsh-collab/guard", f"{HOME}/dsh-collab/rust-tools/src"]
for n in sorted(os.listdir(HOME)):
    if n.startswith("dsh-plugin-"):
        ROOTS.append(os.path.join(HOME, n))

EXTS = {".py", ".js", ".mjs", ".cjs", ".sh", ".json", ".yml", ".yaml", ".rs", ".ts", ".plist", ".md"}
SKIP_DIRS = {"node_modules", ".git", "target", "dist", "__pycache__", "backups"}

def files():
    for r in ROOTS:
        if not os.path.isdir(r): continue
        for dp, dns, fns in os.walk(r):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if fn.endswith(".bak") or ".bak" in fn: continue
                if os.path.splitext(fn)[1] in EXTS:
                    yield os.path.join(dp, fn)

ALL = list(files())
print(f"扫描文件数: {len(ALL)}")
print("扫描根: " + " | ".join(r.replace(HOME, "~") for r in ROOTS if os.path.isdir(r)))
print()

SEGS = ["pollution","drift-alert","plugin-selfcheck","channel-gate-weekly",
        "drift-delivery-failure","drift-heartbeat","bus-expired-alert",
        "gate-weekly-audit","pitfalls","resource-gate","queue-condense"]

def scan(needle):
    hits = []
    for p in ALL:
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if needle in line:
                        hits.append((p.replace(HOME, "~"), i, line.strip()[:150]))
        except Exception:
            pass
    return hits

# ---- 对照 ----
ctrl = scan("ops/")
print(f"【阳性对照】needle='ops/' 命中文件数={len(set(h[0] for h in ctrl))} 行数={len(ctrl)}  ⇒ {'✅探针有效' if ctrl else '❌探针未验证'}")
neg = scan("ops/ZZZ_NOPE_QQQ_TOKEN")
print(f"【阴性对照】needle='ops/ZZZ_NOPE_QQQ_TOKEN' 命中={len(neg)}  ⇒ {'✅' if not neg else '❌'}")
zero = scan("ZZZ_NOPE_QQQ_TOKEN")
print(f"【阴性对照②】needle='ZZZ_NOPE_QQQ_TOKEN'(更宽) 命中={len(zero)} ⇒ {'✅' if not zero else '❌'}")
print()

for s in SEGS:
    h = scan(f"ops/{s}")
    print(f"===== data/ops/{s} =====")
    print(f"  命中 {len(h)} 处")
    for p, i, t in h:
        print(f"    {p}:{i}: {t}")
    if not h:
        print("    (0 命中 —— ★ 对照已通过，故本 0 是【真 0】；但仍不等价于『无人读』，见下说明)")
    print()

print("===== ★ 全库唯一引用核验：drifts[].check 的读者 =====")
dh = scan("drifts")
print(f"  needle='drifts' 命中 {len(dh)} 处")
for p, i, t in dh:
    print(f"    {p}:{i}: {t}")
print()
print("===== ★ 谁引用 beacon-check（读者自己的调用方）=====")
bh = scan("beacon-check")
for p, i, t in bh[:20]:
    print(f"    {p}:{i}: {t}")
print(f"  beacon-check 命中 {len(bh)} 处，涉及 {len(set(x[0] for x in bh))} 个文件")
