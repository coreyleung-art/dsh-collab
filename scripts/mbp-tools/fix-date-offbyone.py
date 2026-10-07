#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正账本/约束表中「超前一天」的日期标注（对端 session-ab866871 指出）。

根因：我在写 R036-R038 时**硬编码** TODAY="2026-10-03"，而实际本地时间为
      2026-10-02 23:4x ⇒ 全部超前一天。
修法：**从系统取日期**，不再硬编码；并把「日期必须取系统时间」作为自纠要点。
影响面：RULES.md 两处、rules.json 三处(added/approvedAt) + lastUpdated、约束表 updated。
注：RC-001 的「生效日期=2026-10-02」本就正确（那是用户指令日期），不动。
"""
import json, io, os, shutil, datetime

TODAY = datetime.datetime.now().strftime("%Y-%m-%d")   # ★ 取系统时间，不硬编码
print("系统日期 = %s（改前硬编码值为 2026-10-03）" % TODAY)
assert TODAY == "2026-10-02", "系统日期非预期，人工确认后再跑"

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
for p in (JP, MP):
    shutil.copy2(p, p + ".bak-datefix-" + STAMP)
CP = os.path.expanduser("~/dsh-collab/data/ops/resource-constraints.json")
shutil.copy2(CP, CP + ".bak-datefix-" + STAMP)
print("已备份三份 (.bak-datefix-%s)" % STAMP)

# 1) rules.json
d = json.load(io.open(JP, encoding="utf-8"))
fixed = []
if d.get("lastUpdated") == "2026-10-03":
    d["lastUpdated"] = TODAY; fixed.append("lastUpdated")
for r in d["rules"]:
    for k in ("added", "approvedAt"):
        if r.get(k) == "2026-10-03":
            r[k] = TODAY; fixed.append("%s.%s" % (r["id"], k))
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json 修正 %d 处: %s" % (len(fixed), fixed))

# 2) RULES.md
md = io.open(MP, encoding="utf-8").read()
n = md.count("2026-10-03")
md = md.replace("2026-10-03", TODAY)
io.open(MP, "w", encoding="utf-8").write(md)
print("RULES.md 替换 %d 处 2026-10-03 → %s" % (n, TODAY))

# 3) 约束表
t = json.load(io.open(CP, encoding="utf-8"))
if t.get("updated") == "2026-10-03":
    t["updated"] = TODAY
    io.open(CP, "w", encoding="utf-8").write(json.dumps(t, ensure_ascii=False, indent=2) + "\n")
    print("约束表 updated → %s" % TODAY)

print("\n=== 校验：账本内是否还有 2026-10-03 ===")
chk = json.load(io.open(JP, encoding="utf-8"))
bad = [r["id"] for r in chk["rules"] if r.get("added") == "2026-10-03" or r.get("approvedAt") == "2026-10-03"]
print("  rules.json 残留: %s | lastUpdated=%s" % (bad or "无", chk.get("lastUpdated")))
print("  RULES.md 残留: %d 处" % io.open(MP, encoding="utf-8").read().count("2026-10-03"))
print("  R036-R038 日期: %s" % [(r["id"], r.get("added")) for r in chk["rules"] if r["id"] in ("R036", "R037", "R038")])
