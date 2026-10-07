#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审查发现应用器 · apply-findings.py
====================================
把逐单元审查结果（每项含 line / reason / suggest）**按行号逐项应用**到源文档。

设计原则（吸取的教训）：
  ✗ 不用正则批量替换 —— 那正是之前制造 23 处表格损坏的原因
  ✓ 逐行定位 → 原文必须精确匹配 → 才替换；不匹配则报告待人工处理
  ✓ 默认 dry-run，--apply 才真正写入；写入前自动备份

suggest 字段格式假定为「原文 → 建议」；解析出两侧后做精确匹配替换。
若 suggest 不是该格式（纯描述），则归入"需人工处理"。

用法：
    # 预览（不写入）
    python3 apply-findings.py <源文件> <findings.json> [findings2.json ...]

    # 实际应用（自动备份）
    python3 apply-findings.py <源文件> <findings.json> --apply

    # 只看某类（如只应用 flag）
    python3 apply-findings.py <源文件> <findings.json> --only flag
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import sys, os, re, json, argparse, shutil, datetime


def parse_suggest(sug):
    """从 suggest 里解析 (原文, 建议)。支持多种写法：
       ① 原文 → 建议
       ② 将「X」改为「Y」 / 把"X"改成"Y"
       ③ 删除「X」 / 删去"X"
       ④ 把 X 替换为 Y
    """
    if not sug:
        return None, None
    s = sug.strip()
    # ① 箭头式
    for sep in [" → ", " -> ", "→", "->"]:
        if sep in s:
            a, b = s.split(sep, 1)
            return a.strip().strip('"「」“”'), b.strip().strip('"「」“”')
    # ② 将「X」改为「Y」
    m = re.search(r'[将把]\s*[「"\'](.+?)[」"\']\s*(?:改|换|替换|修正)?[为成]\s*[「"\'](.+?)[」"\']', s)
    if m:
        return m.group(1), m.group(2)
    # ③ 删除「X」
    m = re.search(r'(?:建议)?(?:删去|删除|去掉|移除)\s*[「"\'](.+?)[」"\']', s)
    if m:
        return m.group(1), ""
    # ④ 把 X 替换为 Y（无引号）
    m = re.search(r'[将把]\s*(.{4,60}?)\s*(?:改|换|替换)[为成]\s*(.{2,60}?)(?:[。；]|$)', s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def main():
    ap = argparse.ArgumentParser(description="审查发现应用器")
    ap.add_argument("src", help="源文档")
    ap.add_argument("findings", nargs="+", help="findings JSON（可多个）")
    ap.add_argument("--apply", action="store_true", help="真正写入（默认 dry-run）")
    ap.add_argument("--only", choices=["flag", "suspect", "all"], default="flag",
                    help="只应用哪类（默认 flag，最确定的一类）")
    args = ap.parse_args()

    src = os.path.expanduser(args.src)
    lines = open(src, encoding="utf-8").read().split("\n")

    # 收集 findings
    items = []
    for fp in args.findings:
        d = json.load(open(os.path.expanduser(fp), encoding="utf-8"))
        for f in d.get("findings", []):
            if args.only != "all" and f.get("verdict") != args.only:
                continue
            items.append(f)
    items.sort(key=lambda x: x.get("line") or 0)

    applied, manual, notfound = [], [], []
    for f in items:
        ln = f.get("line")
        sug = f.get("suggest", "")
        old, new = parse_suggest(sug)
        if not ln or not old:
            manual.append(f); continue
        # 行号可能因前序修改而漂移 → 在 ±5 行内搜索
        idx = None
        for d in range(0, 6):
            for cand in (ln - 1 - d, ln - 1 + d):
                if 0 <= cand < len(lines) and old and old in lines[cand]:
                    idx = cand; break
            if idx is not None:
                break
        if idx is None:
            # 全文件搜一次
            for i, l in enumerate(lines):
                if old and old in l:
                    idx = i; break
        if idx is None:
            notfound.append((ln, old[:60])); continue
        applied.append((idx + 1, old, new))

    print(f"\n=== {'应用' if args.apply else '预览'}（来源 {len(args.findings)} 个文件 / {len(items)} 项 / only={args.only}）===")
    print(f"  可精确定位: {len(applied)} 项")
    print(f"  需人工处理（suggest 非「原文 → 建议」格式）: {len(manual)} 项")
    print(f"  原文未找到: {len(notfound)} 项\n")
    for ln, old, new in applied[:25]:
        print(f"  L{ln}: {old[:62]}")
        print(f"        → {str(new)[:62]}")
    if len(applied) > 25:
        print(f"  … 另有 {len(applied)-25} 项")
    if manual:
        print(f"\n  【需人工处理】前 8 项：")
        for f in manual[:8]:
            print(f"    L{f.get('line')}: {f.get('reason','')[:88]}")

    if args.apply and applied:
        bak = src + ".bak-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(src, bak)
        for ln, old, new in applied:
            lines[ln - 1] = lines[ln - 1].replace(old, new, 1)
        open(src, "w", encoding="utf-8").write("\n".join(lines))
        print(f"\n  ✅ 已应用 {len(applied)} 项 | 备份: {bak}")
    elif applied:
        print(f"\n  （dry-run，未写入。加 --apply 执行）")


if __name__ == "__main__":
    main()
