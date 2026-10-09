#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rules-integrity.py — 规则账本完整性检查（只读 · 不修改账本）

为什么要它（2026-09-11 星桥实测发现）：
  RULES.md 是全局纪律账本，所有设备查规则都读它。但账本**自身的完整性此前无人校验**，
  实测同日发现三处互相矛盾的计数 + 两个重复编号：
    · 标题声明   v2.15.0 | 76 条
    · rules-cli audit       78 条
    · 实际 `## ` 标题        86 个（R 37 + J 44 + 其他 5）
    · R033 出现 2 次（行 413 / 458）、R034 出现 2 次（行 420 / 463）
  后果：`get R033` 得到哪一条不确定；「76 条」不可核。**账本不可核 → 依账本做的判断都不可核。**
  这正是「结构门优于纪律」：靠人翻账本发现不了重复，靠机器每次都能发现。

用法：
  rules-integrity.py            # 人类可读报告（有问题 exit 1）
  rules-integrity.py --json     # 机器可读

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== rules-integrity 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · rules-integrity.py — 规则账本完整性检查（只读 · 不修改账本）")
    print("  · 为什么要它（2026-09-11 星桥实测发现）：")
    print("  · RULES.md 是全局纪律账本，所有设备查规则都读它。但账本**自身的完整性此前无人校验**，")
    print("  · 实测同日发现三处互相矛盾的计数 + 两个重复编号：")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/rules-integrity.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/rules-integrity.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LEDGER = os.path.expanduser("~/dsh-collab/rules-registry/RULES.md")
HEAD_RE = re.compile(r"^##\s+([A-Za-z]+-?[A-Za-z]*)(\d+)\b")
DECL_RE = re.compile(r"^>\s*v([\d.]+)\s*\|\s*(\d+)\s*条")


def parse(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    declared = None
    entries = []  # {id, line, title, has: {...}}
    cur = None
    for i, ln in enumerate(lines, 1):
        m = DECL_RE.match(ln.strip())
        if m and declared is None:
            declared = {"version": m.group(1), "count": int(m.group(2))}
            continue
        if ln.startswith("## "):
            hm = HEAD_RE.match(ln)
            cur = {
                "id": (hm.group(1) + hm.group(2)) if hm else None,
                "prefix": hm.group(1) if hm else None,
                "num": int(hm.group(2)) if hm else None,
                "line": i,
                "title": ln[3:].strip(),
                "fields": set(),
            }
            entries.append(cur)
            continue
        if cur is not None and ln.startswith("- "):
            body = ln[2:]
            if ":" in body:
                cur["fields"].add(body.split(":", 1)[0].strip())
    return lines, declared, entries


def check(path=LEDGER):
    lines, declared, entries = parse(path)
    problems, warnings = [], []

    # 1) 编号唯一
    seen = {}
    for e in entries:
        if e["id"] is None:
            # 非规则小节（如「治理哲学（Φ 系列…）」这类分区标题）→ 提示，不算硬问题
            # （此前误判为硬问题＝我自己的假阳性；假阳性会让门失去权威）
            warnings.append({"kind": "non-rule-section", "line": e["line"], "title": e["title"]})
            continue
        seen.setdefault(e["id"], []).append(e)
    for rid, group in sorted(seen.items()):
        if len(group) > 1:
            problems.append({
                "kind": "duplicate-id", "id": rid,
                "lines": [g["line"] for g in group],
                "titles": [g["title"] for g in group],
                "note": "同一编号多处定义 → 查该条规则的结果不确定",
            })

    # 2) 声明计数 vs 实际
    # ★ 2026-09-11 自纠假阳性：声明数算的是「**规则条数**」，而先前实现拿它和
    # 「全部 `## ` 标题数」比 —— 把非规则小节（如「治理哲学（Φ 系列…）」分区标题）也算进去，
    # 于是恒差 1，报出「声明 83 / 实际 84」这种**假问题**。
    # 假阳性会让门失去权威（今晚已多次验证），故改为**只数带规则编号的标题**。
    actual_headings = len(entries)
    actual = len([e for e in entries if e["id"] is not None])
    if declared:
        if declared["count"] != actual:
            problems.append({
                "kind": "count-mismatch",
                "declared": declared["count"], "actual": actual,
                "note": f"标题声称 {declared['count']} 条规则，实际带编号的规则标题 {actual} 个"
                        f"（另有非规则 `## ` 小节 {actual_headings - actual} 个，不计入）",
            })
    else:
        warnings.append({"kind": "no-declaration", "note": "未找到「> vX | N 条」声明行"})

    # 3) 每条规则必备字段
    for e in entries:
        if e["id"] is None:
            continue
        miss = [f for f in ("分类", "摘要") if f not in e["fields"]]
        if miss:
            warnings.append({"kind": "missing-fields", "id": e["id"], "line": e["line"], "missing": miss})

    # 4) 编号顺序（同前缀应递增；乱序常是追加错位/合并事故的指纹）
    by_prefix = {}
    for e in entries:
        if e["id"]:
            by_prefix.setdefault(e["prefix"], []).append(e)
    unordered = []
    for pfx, group in by_prefix.items():
        nums = [g["num"] for g in group]
        if nums != sorted(nums):
            for a, b in zip(group, group[1:]):
                if b["num"] < a["num"]:
                    unordered.append({"kind": "out-of-order", "id": b["id"], "line": b["line"],
                                      "after": a["id"], "after_line": a["line"]})
    if unordered:
        warnings.extend(unordered)

    # 5) 前缀统计
    stats = {}
    for e in entries:
        key = e["prefix"] if e["prefix"] else "(无法解析)"
        stats[key] = stats.get(key, 0) + 1

    return {
        "ledger": path,
        "declared": declared,
        "actual_headings": actual,
        "unique_ids": len(seen),
        "prefix_stats": stats,
        "problems": problems,
        "warnings": warnings,
        "ok": not problems,
    }


def main():
    path = LEDGER
    as_json = "--json" in sys.argv
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return 0
    if os.path.exists(path) is False:
        print(f"❌ 账本不存在: {path}")
        return 1
    r = check(path)

    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        d = r["declared"] or {}
        print(f"规则账本完整性检查 · {path}")
        print(f"  声明: v{d.get('version','?')} | {d.get('count','?')} 条")
        print(f"  实际: {r['actual_headings']} 个标题 / {r['unique_ids']} 个唯一编号")
        print(f"  前缀分布: " + " · ".join(f"{k}={v}" for k, v in sorted(r["prefix_stats"].items())))
        print()
        if r["problems"]:
            print(f"❌ 硬问题 {len(r['problems'])} 项（账本不可信，须修）:")
            for p in r["problems"]:
                if p["kind"] == "duplicate-id":
                    print(f"   · 重复编号 {p['id']}  行 {p['lines']}  → {p['note']}")
                    for ln, t in zip(p["lines"], p["titles"]):
                        print(f"       行{ln}: {t[:70]}")
                elif p["kind"] == "count-mismatch":
                    print(f"   · 计数不符: 声明 {p['declared']} / 实际 {p['actual']}")
                else:
                    print(f"   · {p}")
        else:
            print("✅ 无硬问题")
        if r["warnings"]:
            print(f"\n⚠️ 提示 {len(r['warnings'])} 项:")
            for w in r["warnings"][:12]:
                if w["kind"] == "out-of-order":
                    print(f"   · 编号乱序: {w['id']}(行{w['line']}) 出现在 {w['after']}(行{w['after_line']}) 之后")
                elif w["kind"] == "missing-fields":
                    print(f"   · {w['id']}(行{w['line']}) 缺字段: {w['missing']}")
                elif w["kind"] == "non-rule-section":
                    print(f"   · 行{w['line']} 非规则小节（分区标题，跳过）: {w['title'][:50]}")
            if len(r["warnings"]) > 12:
                print(f"   … 另有 {len(r['warnings'])-12} 项")
        print()
        print("结论: " + ("❌ 账本存在硬问题 —— 依账本做的判断不可核，应先修复" if not r["ok"]
                        else "✅ 账本通过完整性检查"))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
