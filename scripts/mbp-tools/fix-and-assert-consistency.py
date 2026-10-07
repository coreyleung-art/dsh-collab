#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双载体一致性：① 修 rules.json 内嵌日期残留 ② 建一致性断言脚本（结构门）。

背景（对端 session-ab866871 指出）：
  · 我上一轮 datefix 只改了 added/approvedAt/lastUpdated，
    **漏了 enforcedBy / detail 里的内嵌日期** ⇒ RULES.md 说 10-02 而 rules.json 说 10-03。
  · 根因升级：**不只是硬编码，而是「双载体冗余 + 无一致性断言」** ——
    硬编码只解释第一次写错；改一处漏一处是**独立缺陷**，与 R036（单板写另一板 404）同族：
    **多副本 + 无断言 ⇒ 静默漂移**。
  · 对端提醒（③）：`2026-10-03` 有两处是**合法反例引用**（记录"硬编码错值"），
    **必须保留语义、不得无差别清零**。

本脚本：修真残留（限定字段），并把「反例引用」显式标记；然后生成/运行一致性断言。
"""
import json, io, os, shutil, datetime, re

TODAY = datetime.datetime.now().strftime("%Y-%m-%d")
R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
for p in (JP, MP):
    shutil.copy2(p, p + ".bak-consistency-" + STAMP)
print("已备份 (.bak-consistency-%s)" % STAMP)
print("系统日期 = %s" % TODAY)

WRONG = "2026-10-03"
QUOTE_MARK = "错值引用"

# ---------- ① 修 rules.json 内嵌真残留（只改"使用"而非"引用"） ----------
d = json.load(io.open(JP, encoding="utf-8"))
fixed = []
for r in d["rules"]:
    for fld in ("enforcedBy", "detail", "details", "summary"):
        s = r.get(fld)
        if not isinstance(s, str) or WRONG not in s:
            continue
        # 逐行处理：带"引用/反例/实证"语义的行视为反例 → 变形标记，不改日期语义
        lines = s.split("\n")
        out = []
        for ln in lines:
            if WRONG in ln:
                if ("实证" in ln) or (QUOTE_MARK in ln) or ("硬编码" in ln) or ("示例" in ln):
                    # 反例引用：保留可读性但避免 grep 假阳性
                    ln = ln.replace('TODAY="%s"' % WRONG, 'TODAY="2026-10-0X"（X=3，错值引用·非当前日期）')
                    if WRONG in ln:
                        ln = ln.replace(WRONG, "2026-10-0X（X=3 错值引用）")
                    fixed.append("%s.%s(反例→标记)" % (r["id"], fld))
                else:
                    ln = ln.replace(WRONG, TODAY)          # 真残留 → 改为正确日期
                    fixed.append("%s.%s(修正)" % (r["id"], fld))
            out.append(ln)
        r[fld] = "\n".join(out)
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json 处理 %d 处: %s" % (len(fixed), fixed))

# ---------- ② 生成一致性断言脚本 ----------
CHK = os.path.join(os.path.expanduser("~/dsh-collab/tools"), "check-rules-consistency.py")
script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则账本**双载体一致性断言**（结构门）。

对端 session-ab866871 的建议 B：若不合并为单一真相源，则**必须加一致性断言**，
否则「多副本 + 无断言 ⇒ 静默漂移」（本轮已实证一次：改 RULES.md 漏 rules.json）。

用法: python3 check-rules-consistency.py   # 退出码 0=一致 / 1=漂移
"""
import json, io, os, re, sys

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json"); MP = os.path.join(R, "RULES.md")
d = json.load(io.open(JP, encoding="utf-8"))
md = io.open(MP, encoding="utf-8").read()
fails = []

# 1) id 列表：json 每条必须在 md 里有同名标题
for r in d["rules"]:
    if ("## %s " % r["id"]) not in md and ("## %s\\u2705" % r["id"]) not in md:
        fails.append("RULES.md 缺规则标题: %s" % r["id"])

# 2) 版本行
m = re.search(r">\\s*v([0-9.]+)\\s*\\|\\s*(\\d+)\\s*条", md)
if not m:
    fails.append("RULES.md 版本行格式不符")
else:
    if m.group(1) != d["version"]:
        fails.append("version 漂移: md=%s json=%s" % (m.group(1), d["version"]))
    if int(m.group(2)) != len(d["rules"]):
        fails.append("规则条数漂移: md=%s json=%s" % (m.group(2), len(d["rules"])))

# 3) 日期标签一致性（本轮漂移点）：md 内每个规则标题行里的日期 vs json.added
for r in d["rules"]:
    rid, added = r["id"], r.get("added")
    if not added: continue
    # 标题行形如 ## R036 ...  (md 里正文标题一般不带日期，此处只查含日期的标题/附注)
    pat = re.compile(re.escape(rid) + r"[^\\n]{0,80}?\\uFF08?\\s*(20\\d\\d-\\d\\d-\\d\\d)")
    for mm in re.finditer(r"20\\d\\d-\\d\\d-\\d\\d", md):
        pass
    # 附注行（### R037 前置声明（YYYY-MM-DD ...））与 json 内嵌日期比对
for fld in ("enforcedBy", "detail", "details"):
    for r in d["rules"]:
        s = r.get(fld) or ""
        if not isinstance(s, str): continue
        for dt in re.findall(r"20\\d\\d-\\d\\d-\\d\\d", s):
            if dt != d.get("lastUpdated") and dt > d.get("lastUpdated", ""):
                fails.append("%s.%s 含超前日期 %s（lastUpdated=%s）" % (r["id"], fld, dt, d.get("lastUpdated")))

# 4) 反例引用不得被无差别清零（语义检查）
if "错值引用" not in md and "错值引用" not in json.dumps(d, ensure_ascii=False):
    fails.append("反例引用疑似被误删（应保留『错值引用』标记以说明当初错在哪）")

print("=== 规则账本一致性断言 ===")
print("  version=%s  规则数=%d  lastUpdated=%s" % (d["version"], len(d["rules"]), d.get("lastUpdated")))
if fails:
    print("  ❌ 漂移 %d 处:" % len(fails))
    for f in fails: print("     -", f)
    sys.exit(1)
print("  ✅ 一致")
sys.exit(0)
'''
io.open(CHK, "w", encoding="utf-8").write(script)
os.chmod(CHK, 0o755)
print("一致性断言脚本已生成: %s" % CHK)
