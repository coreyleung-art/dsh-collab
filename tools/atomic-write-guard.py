#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""atomic-write-guard —「非原子写关键文件」的可机械核验门。

★ 立据（2026-10-12 事故，本线亲身）：
  ★ `io.open(p, "w", encoding="utf-8").write(s)` ——「w」模式【先截断】文件，
  ★★ 而 `write()` 因编码错误失败 ⇒ **634 KB 台账被清空**（已从 git 恢复）。
  ★ 正确写法：**临时文件 + `os.replace()` 原子替换**。

本门扫两件（★ 扫描前剥离注释/字符串 —— R006 反复踩的自伤面）：
  R1 Python：`open(TARGET, "w")` 直写 ⇒ **warn**（★ 若同文件有 `os.replace` 则放行）
  R2 关键文件：目标路径落在【关键清单】内 ⇒ **fail**

三态：未扫到目标且扫描面为空 ⇒ 报「不可判」，不当通过。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["tools", "scripts"]
# ★ 关键文件（★ 改坏代价大的）
CRITICAL = ["deviation-ledger", "continuity-index", "resume-prompt", "governance-plan",
            "RULES.md", "agent-role-map", "review-tracker", "CCEP-continuity"]

# ★ 目标写法两种：变量（p / path）与字面量（"x.md"）⇒ 字符类须允许【引号开头】
#   ★ 立据：本门初版正控「直写样本未命中」，根因 = 捕获组要求以字母/下划线开头
#   ★ ⇒ 匹配不到 `io.open("x.md","w")` 这种【字面量路径】的写法。
RE_OPEN_W = re.compile(r'open\s*\(\s*([A-Za-z_][\w\.\[\]\'"]*|[\'"][^\'"]*[\'"])\s*,\s*[\'"]w[\'"]')


def strip_comments(src):
    """★ 只剥【注释】与【多行 docstring】，【保留字符串字面量】。

    ★★ 为何不剥字符串（★ 2026-10-12 自证抓到的一次假绿）：
      ★ 本函数初版【连字符串一起剥】⇒ `open("x","w")` 里的 `"w"` 被剥掉
      ★ ⇒ 正则再也匹配不到 ⇒ **扫描报「0 处直写」而实际有** ⇒ **假绿**。
      ★★ 而它【被自证的正控抓住】—— ★ 这正是「负控须验被消费的值」的实例。
    ★ 现在：短字符串保留；只有【跨行三引号块】与 `#` 注释被剥离。
    """
    out = []
    i, n = 0, len(src)
    dq = '"' * 3
    sq = "'" * 3
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        # ★ 只剥跨行三引号（docstring / 长块），★ 单行短字符串一律保留
        if src.startswith(dq, i) or src.startswith(sq, i):
            q = src[i:i + 3]
            j = src.find(q, i + 3)
            i = n if j < 0 else j + 3
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ★ 保留旧名做别名（★ 防下游引用断裂）
strip_comments_strings = strip_comments


def scan_src(code):
    """★ 在【已前剥离】的代码上找直写。"""
    return RE_OPEN_W.findall(code)


def scan_file(path):
    hits = []
    try:
        raw = io.open(path, encoding="utf-8").read()
    except Exception:
        return hits
    code = strip_comments_strings(raw)
    for tgt in scan_src(code):
        crit = any(c.lower() in tgt.lower() for c in CRITICAL)
        hits.append({"file": os.path.relpath(path, ROOT), "target": tgt,
                     "kind": "CRITICAL" if crit else "plain",
                     "has_os_replace": "os.replace" in code})
    return hits


def inventory(root=None):
    out = []
    _root = root or ROOT
    for d in SCAN_DIRS:
        base = os.path.join(_root, d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith(".py"):
                continue
            out.extend(scan_file(os.path.join(base, fn)))
    return out


def selftest():
    ok = tot = 0
    # ★ 正控：直写样本 ⇒ 必须命中
    tot += 1
    if scan_src(strip_comments_strings('io.open("x.md","w").write(s)')):
        ok += 1
        print("  ✅ 正控：直写样本 ⇒ 命中")
    else:
        print("  ❌ 正控：直写样本未命中")
    # ★ 负控：注释里的直写 ⇒ 必须不命中（前剥离有效）
    tot += 1
    if not scan_src(strip_comments_strings('# io.open("y.md","w").write(s)')):
        ok += 1
        print("  ✅ 负控：注释里的直写 ⇒ 已前剥离、不命中")
    else:
        print("  ❌ 负控：注释未前剥离 ⇒ 自伤")
    # ★ 负控：字符串里的直写 ⇒ 必须不命中
    tot += 1
    if not scan_src(strip_comments_strings('s = "io.open(\\"z.md\\",\\"w\\")"')):
        ok += 1
        print("  ✅ 负控：字符串里的直写 ⇒ 已前剥离、不命中")
    else:
        print("  ❌ 负控：字符串未前剥离 ⇒ 自伤")
    # ★ 正控：原子写样本 ⇒ 仍应命中 R1（★ 由 has_os_replace 放行，不是不命中）
    tot += 1
    if scan_src(strip_comments_strings('tmp = p + ".tmp"\nio.open(tmp,"w").write(s)\nos.replace(tmp,p)')):
        ok += 1
        print("  ✅ 正控：原子写样本仍命中 R1（★ 由 has_os_replace 放行）")
    else:
        print("  ❌ 正控：原子写样本不命中 ⇒ 正则过窄")
    # ★ 扫描面非空
    tot += 1
    n = 0
    for d in SCAN_DIRS:
        b = os.path.join(ROOT, d)
        if os.path.isdir(b):
            n += len([f for f in os.listdir(b) if f.endswith(".py")])
    if n > 0:
        ok += 1
        print("  ✅ 正控：扫描面 %d 个 .py" % n)
    else:
        print("  ❌ 正控：扫描面为空 ⇒ 不可判")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    # ★★ 2026-10-13（ext E-5）：加 `--path` seam —★ 让【外部】能驱动它（★ 原只扫固定面）。
    ap.add_argument("--path", default=None, help="★ 被扫根（默认仍走原固定面）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("atomic-write-guard 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    items = inventory(getattr(a, 'path', None))
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    print("== atomic-write-guard 1.0.0 · 共 %d 处直写 ==" % len(items))
    for h in items:
        flag = "★★ CRITICAL" if h["kind"] == "CRITICAL" else "   plain"
        print("  %s  %-38s 目标=%-26s os.replace=%s"
              % (flag, h["file"], h["target"][:26], h["has_os_replace"]))
    print()
    if not items:
        print("  ★ 未扫到直写目标 —— ★ 但请先确认扫描面非空（★ 无命中 ≠ 无问题）")
        return 0
    crit = [h for h in items if h["kind"] == "CRITICAL" and not h["has_os_replace"]]
    if crit:
        print("  ❌ %d 处危险：关键文件直写且无 os.replace" % len(crit))
        return 1
    print("  ✅ 关键文件无未保护直写")
    return 0


if __name__ == "__main__":
    sys.exit(main())
