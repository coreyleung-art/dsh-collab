#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G6 改名：hazards 自有规则 R1–R43 → H1–H43（命名空间隔离，星桥已采纳）。

边界（防止误改）：
  · 只改 `~/dsh-collab/hazards/**.md`
  · 只匹配 **1–2 位** 数字：`R43` ✅ / `R025`（账本三位数）❌ / `R-ERR4` ❌
  · 备份 `.bak-hrename-<stamp>`；改后逐文件读回断言「无残留 1–2 位 R 号」

用法：--dry-run 先看；无参数=真改。
"""
import io, os, re, sys, glob, datetime, shutil

ROOT = os.path.expanduser("~/dsh-collab/hazards")
# 1–2 位数字，且左右不是字母数字（避免 R025 / R-ERR / 单词内匹配）
PAT = re.compile(r"(?<![0-9A-Za-z_])R(\d{1,2})(?![0-9])")

dry = "--dry-run" in sys.argv
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
files = sorted(glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True))
print("模式:", "DRY-RUN（不落盘）" if dry else "真改")
print("目标文件:", len(files))

total = 0
report = []
for f in files:
    src = io.open(f, encoding="utf-8").read()
    out, n = PAT.subn(lambda m: "H" + m.group(1), src)
    if n:
        report.append((os.path.relpath(f, ROOT), n))
        total += n
        if not dry:
            shutil.copy2(f, f + ".bak-hrename-" + stamp)
            io.open(f, "w", encoding="utf-8").write(out)

print("\n逐文件改名数:")
for rel, n in report:
    print("  %-40s %d" % (rel, n))
print("合计替换:", total)

# ── 读回断言（R036：不是保险，是必要条件）────────────────────────────
if not dry:
    print("\n读回断言:")
    bad = 0
    for f in files:
        s = io.open(f, encoding="utf-8").read()
        leftover = PAT.findall(s)
        keep3 = re.findall(r"(?<![0-9A-Za-z_])R(\d{3})", s)
        if leftover:
            print("  ❌ %s 残留 1–2 位 R 号: %s" % (os.path.relpath(f, ROOT), leftover[:8]))
            bad += 1
        else:
            print("  ✅ %-40s 无残留（保留三位账本号 %d 处）" % (os.path.relpath(f, ROOT), len(keep3)))
    sys.exit(1 if bad else 0)
