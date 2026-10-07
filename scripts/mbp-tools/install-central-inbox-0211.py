#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把暂存的 0.2.11 安装到 profile（**不删除任何东西**），逐文件读回断言。

纪律：
  · **绝不 `--delete`**（A 类：源里没有、目标必须有的文件会被误删 —— 事故 #3/#4）
  · 包内 `.bak*` 属 §4.2/H6 违规 ⇒ **搬出**（不是删）到归档
  · 交付后**逐文件 md5 读回复算**（H38），并断言 `dsh.bundle.patch` 指向文件在位（G14）
"""
import hashlib, os, shutil, subprocess, sys, json, datetime

STAGE = os.path.expanduser("~/dsh-collab/data/packages/staging-central-inbox-0.2.11")
TARGET = os.path.expanduser("~/.dsh/profiles/web/node_modules/dsh-plugin-central-inbox")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BAK = os.path.expanduser("~/dsh-collab/data/backups/central-inbox-20261004/pre-0211-" + STAMP)


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def walk_files(base):
    out = []
    for r, _, fs in os.walk(base):
        for n in fs:
            out.append(os.path.relpath(os.path.join(r, n), base))
    return sorted(out)


print("══ ① 备份当前部署（含其 .bak，一并留档）══")
shutil.copytree(TARGET, BAK)
print("  备份 →", BAK, "|", len(walk_files(BAK)), "个文件")

print("\n══ ② 搬出包内 .bak（§4.2/H6：包内禁带旧副本）══")
moved = 0
for f in walk_files(TARGET):
    if ".bak" in os.path.basename(f):
        src = os.path.join(TARGET, f)
        os.makedirs(os.path.join(BAK, "_pkg_baks"), exist_ok=True)
        shutil.move(src, os.path.join(BAK, "_pkg_baks", os.path.basename(f)))
        moved += 1
print("  搬出 %d 个" % moved)

print("\n══ ③ 覆盖安装 0.2.11（cp，不用 rsync --delete）══")
n = 0
for f in walk_files(STAGE):
    src, dst = os.path.join(STAGE, f), os.path.join(TARGET, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    n += 1
print("  覆盖 %d 个文件" % n)

print("\n══ ④ 逐文件读回断言（H38）══")
bad = []
for f in walk_files(STAGE):
    a = md5(os.path.join(STAGE, f)); b = md5(os.path.join(TARGET, f))
    if a != b:
        bad.append(f)
    print("  %-22s %s" % (f, "✅" if a == b else "❌ %s≠%s" % (a[:8], b[:8])))

print("\n══ ⑤ 契约断言（G14 / 版本 / 排除集）══")
d = json.load(open(os.path.join(TARGET, "package.json"), encoding="utf-8"))
patch = (d.get("dsh") or {}).get("bundle", {}).get("patch")
present = bool(patch) and os.path.isfile(os.path.join(TARGET, patch.lstrip("./")))
print("  version =", d.get("version"), "| dsh.bundle.patch =", patch, "| 在位 =", present)
leftover = [f for f in walk_files(TARGET) if ".bak" in os.path.basename(f)]
print("  包内残留 .bak =", leftover or "无 ✅")

ok = (not bad) and present and d.get("version") == "0.2.11" and not leftover
print("\n  ⇒ " + ("✅ 安装完成且断言全过" if ok else "❌ 有断言不通过 —— 请回滚"))
print("  回滚：cp -R %s/* %s/" % (BAK, TARGET))
sys.exit(0 if ok else 1)
