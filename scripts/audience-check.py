#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audience-check.py — 按受众检查文档里「不该出现」的内容

为什么存在
----------
一个项目反复调整「什么内容给谁看」：给平台的材料要删掉 AI 工具实测数据、
数据回流、账号线、合规技术细节、四跑法推演；股东版则保留股权/对赌/资金。

给平台的 = 只说「做什么、给谁带来什么、要什么」。
不给平台的：① 我们内部怎么干活 ② 我们怎么想这件事 ③ 我们的技术细节。
共同点：平台不需要知道；知道了可能有害。

用法
----
  audience-check.py <file.md> --audience platform
  audience-check.py <file.md> --audience shareholder --json
  audience-check.py --list-rules

退出码：发现该受众下不该出现的内容 → 1；干净 → 0；用法/文件错误 → 2。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import json
import os
import re
import sys

DEFAULT_MATRIX = "audience-matrix.json"
HERE = os.path.dirname(os.path.abspath(__file__))
BAR = "=" * 64
THIN = "-" * 64

CJK_RE = re.compile(r"[\u3400-\u9fff]")

# 否定语境前缀：命中词紧跟在「不是 / 无需 …」后面时不算越界
# （「成功率是可能性评估，不是承诺」不该因为出现「承诺」被判违规）
NEG_PREFIX = ("不是", "并非", "不算", "不属于", "无需", "不用", "不会", "不再", "没有", "未", "不")


def is_negated(line, start):
    ctx = line[max(0, start - 4):start]
    return any(ctx.endswith(n) for n in NEG_PREFIX)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def find_matrix(explicit):
    if explicit:
        return os.path.abspath(explicit)
    for cand in (
        os.path.join(HERE, DEFAULT_MATRIX),
        os.path.abspath(DEFAULT_MATRIX),
    ):
        if os.path.isfile(cand):
            return cand
    return None


def compile_pattern(pattern):
    """ASCII 词做词边界匹配（防 API 命中 rapid），中文做子串匹配；re: 前缀走正则。"""
    if pattern.startswith("re:"):
        return re.compile(pattern[3:], re.IGNORECASE)
    if CJK_RE.search(pattern):
        return re.compile(re.escape(pattern), re.IGNORECASE)
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(pattern) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def scan(text, rules):
    """逐行扫描，返回 (越界命中, 放行命中, 因否定语境跳过的命中数)。"""
    lines = text.split("\n")
    in_code = False
    denied, allowed = [], []
    negated = 0
    for lineno, line in enumerate(lines, start=1):
        if re.match(r"^\s*(`{3,}|~{3,})", line):
            in_code = not in_code
            continue
        if not line.strip():
            continue
        for rule in rules:
            hits = []
            for p, rx in rule["_rx"]:
                for m in rx.finditer(line):
                    if is_negated(line, m.start()):
                        negated += 1
                    else:
                        hits.append(p)
                        break
            if not hits:
                continue
            rec = {
                "line": lineno,
                "rule_id": rule["id"],
                "rule_label": rule["label"],
                "matched": hits,
                "excerpt": line.strip(),
                "note": rule.get("note", ""),
                "in_code": in_code,
            }
            if rule["_audience"] in rule["allow"]:
                allowed.append(rec)
            else:
                denied.append(rec)
    return denied, allowed, negated


def cmd_list_rules(matrix_path, matrix):
    print("受众矩阵 · %s" % matrix_path)
    print(BAR)
    print("受众：%s" % "、".join(
        "%s（%s）" % (a, matrix.get("audience_labels", {}).get(a, a)) for a in matrix["audiences"]))
    print("规则：%d 条" % len(matrix["rules"]))
    print(THIN)
    for r in matrix["rules"]:
        print("[%s] %s" % (r["id"], r["label"]))
        print("    可见：%s" % "、".join(r.get("allow", [])))
        print("    禁止：%s" % "、".join(r.get("deny", [])))
        print("    命中词：%s" % "、".join(r.get("pattern", [])))
        if r.get("note"):
            print("    说明：%s" % r["note"])
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="audience-check.py",
        description="按受众检查文档里不该出现的内容（股权/内部操作/技术细节/AI 实测/数据回流/账号线…）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  audience-check.py 材料.md --audience platform
  audience-check.py 材料.md --audience shareholder --json
  audience-check.py --list-rules
""",
    )
    p.add_argument("file", nargs="?", help="要检查的文档（--list-rules 时可省略）")
    p.add_argument("--audience", help="受众：shareholder / partner / platform / public")
    p.add_argument("--matrix", help="矩阵文件路径（默认取脚本同目录的 audience-matrix.json）")
    p.add_argument("--json", action="store_true", help="输出 JSON（便于程序化处理）")
    p.add_argument("--list-rules", action="store_true", help="列出矩阵里的全部规则后退出")
    args = p.parse_args(argv)

    matrix_path = find_matrix(args.matrix)
    if not matrix_path or not os.path.isfile(matrix_path):
        print("❌ 找不到受众矩阵：%s（用 --matrix 指定）" % (args.matrix or DEFAULT_MATRIX))
        return 2
    try:
        matrix = json.loads(read_text(matrix_path))
    except Exception as exc:  # noqa: BLE001
        print("❌ 矩阵 JSON 解析失败（%s）：%s" % (matrix_path, exc))
        return 2

    if args.list_rules:
        return cmd_list_rules(matrix_path, matrix)

    if not args.file:
        print("❌ 缺少要检查的文档路径")
        return 2
    if not args.audience:
        print("❌ 缺少 --audience（可选：%s）" % " / ".join(matrix["audiences"]))
        return 2

    audience = args.audience.strip()
    if audience not in matrix["audiences"]:
        print("❌ 未知受众：%s（可选：%s）" % (audience, " / ".join(matrix["audiences"])))
        return 2

    src = os.path.abspath(args.file)
    if not os.path.isfile(src):
        print("❌ 找不到文件：%s" % src)
        return 2

    rules = []
    for r in matrix.get("rules", []):
        item = dict(r)
        item["_rx"] = [(pat, compile_pattern(pat)) for pat in r.get("pattern", [])]
        item["_audience"] = audience
        rules.append(item)

    text = read_text(src)
    denied, allowed, negated = scan(text, rules)
    label = matrix.get("audience_labels", {}).get(audience, audience)

    if args.json:
        print(json.dumps({
            "file": src,
            "audience": audience,
            "audience_label": label,
            "matrix": matrix_path,
            "rules_total": len(rules),
            "violations": denied,
            "allowed_hits": allowed,
            "violation_count": len(denied),
            "allowed_count": len(allowed),
            "negated_skipped": negated,
            "exit_code": 1 if denied else 0,
        }, ensure_ascii=False, indent=2))
        return 1 if denied else 0

    print("受众审查 · %s" % os.path.basename(src))
    print("受众　　：%s（%s）" % (audience, label))
    print("矩阵　　：%s（%d 条规则）" % (matrix_path, len(rules)))
    print(BAR)

    if not denied:
        print("✅ 未发现不该出现的内容")
        if allowed:
            print("   （%d 处命中均在该受众可见范围内，已放行）" % len(allowed))
        if negated:
            print("   （另有 %d 处命中处于否定语境，已跳过，如「不是承诺」）" % negated)
        print(THIN)
        print("结论：%s（%s）视角下 0 处越界" % (audience, label))
        return 0

    rule_ids = []
    for d in denied:
        if d["rule_id"] not in rule_ids:
            rule_ids.append(d["rule_id"])
    print("❌ 发现 %d 处不该出现的内容（涉及 %d 条规则）：" % (len(denied), len(rule_ids)))
    print("")
    for i, d in enumerate(denied, start=1):
        tag = "（代码块内）" if d["in_code"] else ""
        print("[%d] 第 %d 行 · [%s] %s%s" % (i, d["line"], d["rule_id"], d["rule_label"], tag))
        print("    原文：%s" % (d["excerpt"][:160] + ("…" if len(d["excerpt"]) > 160 else "")))
        print("    命中：%s" % "、".join(d["matched"]))
        if d["note"]:
            print("    说明：%s" % d["note"])
        print("")
    print(THIN)
    print("结论：%s（%s）视角下 %d 处越界，需删除或改写" % (audience, label, len(denied)))
    print("      涉及规则：%s" % "、".join(rule_ids))
    if allowed:
        print("      另有 %d 处命中属于该受众可见范围（已放行）" % len(allowed))
    if negated:
        print("      另有 %d 处命中处于否定语境，已跳过（如「不是承诺」）" % negated)
    print("")
    print("提示：关键词法只做兜底闸门；正式审查请用 unit-review.py 逐单元语义审查，")
    print("      关键词法报「全通过」而逐单元审查发现大量问题的情形很常见。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
