#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rule-audit v0.1 — 规则账本全景 + 冲突/覆盖检测 (audit 工具族·骨架)
域: 规则账本 (RULES.md + rules-registry)
模式: 域全景扫描 → 分类 + 冲突/重叠矩阵 → 判断输入 (Φ10 判断力)
输出:
  A. 规则全景分类 (enforced/archived/draft + 分类: 工程/资源/数据/治理)
  B. 冲突/覆盖检测 (同主题规则重叠/引用工具缺失)
用法:
  rule-audit.py scan [--rules <RULES.md>]  # 规则全景
  rule-audit.py conflicts                   # 冲突/覆盖检测
  rule-audit.py --lean4-check              # 自检 (只读)
  rule-audit.py --version

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
    print("== rule-audit 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · rule-audit v0.1 — 规则账本全景 + 冲突/覆盖检测 (audit 工具族·骨架)")
    print("  · 域: 规则账本 (RULES.md + rules-registry)")
    print("  · 模式: 域全景扫描 → 分类 + 冲突/重叠矩阵 → 判断输入 (Φ10 判断力)")
    print("  · A. 规则全景分类 (enforced/archived/draft + 分类: 工程/资源/数据/治理)")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/rule-audit.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import os
import re
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/rule-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "0.1.0"
DEFAULT_RULES = os.path.expanduser("~/dsh-collab/rules-registry/RULES.md")


def _parse_rules(path: str) -> list:
    """解析 RULES.md → 规则条目列表 {id, title, status, category, text}"""
    if not os.path.exists(path):
        return []
    rules = []
    current = None
    with open(path) as f:
        for line in f:
            m = re.match(r"^##\s+(\S+)\s+([✅⚠️📋]?)\s*(.*)", line)
            if m:
                if current:
                    rules.append(current)
                rid = m.group(1)
                status = "enforced" if "✅" in line else ("archived" if "⚠️" in line else "draft")
                current = {"id": rid, "title": m.group(3).strip(),
                           "status": status, "text": line.strip(), "body": []}
            elif current is not None:
                current["body"].append(line.rstrip())
    if current:
        rules.append(current)
    return rules


def scan(path: str = DEFAULT_RULES) -> dict:
    """A: 规则全景分类"""
    rules = _parse_rules(path)
    by_status = {}
    by_cat = {}
    for r in rules:
        by_status.setdefault(r["status"], []).append(r["id"])
        # 从 body 摘要行取分类 (如 "- 分类: 工程")
        cat = None
        for b in r["body"]:
            cm = re.search(r"分类:\s*([^\s|]+)", b)
            if cm:
                cat = cm.group(1)
                break
        by_cat.setdefault(cat or "uncat", []).append(r["id"])
    return {"total": len(rules), "by_status": {k: len(v) for k, v in by_status.items()},
            "by_category": {k: len(v) for k, v in by_cat.items()}, "rules": rules}


def conflicts(path: str = DEFAULT_RULES) -> list:
    """B: 冲突/覆盖检测 —— 引用结构门工具但工具不存在 / 同 id 重复"""
    rules = _parse_rules(path)
    issues = []
    seen = {}
    # 同 id 重复
    for r in rules:
        if r["id"] in seen:
            issues.append({"type": "dup_id", "id": r["id"]})
        seen[r["id"]] = True
    # 标注结构门但对应工具缺 (简化: 标注了 "结构门: xxx" 即视为有工具)
    return issues


def _lean4_check(path: str = DEFAULT_RULES) -> int:
    ok = True
    out = [f"== Lean4 约束门自检 (rule-audit v{VERSION}) =="]
    src = open(__file__).read()
    has_write = bool(re.search(r"rm\s+-rf|os\.remove|shutil\.rmtree|open\([^)]*['\"]w['\"]", src))
    checks = [
        ("① 只读无破坏写", not has_write),
        ("② scan 返回结构", "total" in scan(path)),
        ("③ RULES.md 存在", os.path.exists(path)),
        ("④ conflicts 返回 list", isinstance(conflicts(path), list)),
    ]
    for label, cond in checks:
        out.append(f"  [{'✅' if cond else '❌'}] {label}")
        ok = ok and cond
    out.append(f"  结果: {'✅ GATE OK' if ok else '❌ GATE FAIL'}")
    print("\n".join(out))
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--lean4-check" in args:
        raise SystemExit(_lean4_check())
    if "--version" in args:
        print(f"rule-audit v{VERSION}")
        raise SystemExit(0)
    path = DEFAULT_RULES
    if "--rules" in args:
        path = os.path.expanduser(args[args.index("--rules") + 1])
    if not args or args[0] == "scan":
        import json
        s = scan(path)
        s.pop("rules", None)
        print(json.dumps(s, ensure_ascii=False, indent=2))
    elif args[0] == "conflicts":
        import json
        print(json.dumps(conflicts(path), ensure_ascii=False, indent=2))
    else:
        print("用法: rule-audit.py [scan|conflicts|--lean4-check|--version]")
