#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k6-partial-guard.py — 「partial 不得被静默升格；partial 标注必须带原因」的可机械核验门。

★ 判据来源：任务书 `docs/k6-postrestart-commission-20261010.md` §2 T2 负控逐字：
  「把该 `partial` 标注改回「通过」⇒ **须有判据能发现**（若现无，则**须新增一条**，
    例如收口脚本检查 `partial` 项必须带 reason）。」
★ 为什么值得独立成门：**「原因」是会随版本演进而蒸发的字段**。把 partial 静默升格成"通过"，
  外观上与"真的做完了"完全一样 —— 与本研究线反复出现的「两种成因同痕」同形。

规则（**不改被核对象**；临时写面 = `guard/mutation-work/`）：
  R1 **状态形的 partial 必须带原因**：凡匹配**状态标注形**的行
     （`◐ **partial…` 或表格单元格恰为 `partial`），必须同含原因标记
     （`原因` / `reason` / `宿主不可达` / `＝宿主`）。
     ★ 只认**状态形**，不认散文里提一句 partial —— 否则会误伤"记录历史"的行（本机反复踩的那一族）。
  R2 **已裁的宿主不可达项不得被升格**：`KNOWN_BLOCKED` 列出的行（按**行首模式**精确匹配，
     不用子串 —— 子串会误伤汇总计数行，本脚本第一版就是这么错的），必须仍含 `partial` 且含指定原因标记。

★ 范围如实（本门的**限度**，不得据此声称更多）：
  · 只核**标注层**（文档文字），不核底层事实是否真的如此 —— 判据管不了实。
  · 只扫 `TARGETS` 三份文件；新增文档需显式加入，**不做全库扫**。

退出码：0 = 通过 · 1 = 有违例（逐条列出）· 2 = 环境/用法错误
用法：python3 tools/k6-partial-guard.py [--root <目录>]   # --root 供**沙箱副本**上做变异检验
"""
import os
import re
import sys

ROOT = os.path.expanduser("~/dsh-collab")
TARGETS = [
    "docs/k5-section5-criteria-matrix.md",
    "docs/context-survival-tracker.md",
    "devices/dsh-plugin-context-survival/CHANGELOG.md",
]
KNOWN_BLOCKED = [
    {
        "file": "docs/k5-section5-criteria-matrix.md",
        "row_prefix": "| **负控 3** |",
        # ★ 状态**单元格**下标（0 基，含行首空串）：| 项 | 判据 | 状态 | 命令 | 证据 | ⇒ 状态在第 3 格
        #   为什么必须看单元格而不是整行（本脚本第二版实测）：把状态格改成「✅ 通过」而**证据格里
        #   仍写着 partial 与原因** ⇒ 整行匹配会**假绿**（负控 A 就是这么漏的）。
        "status_cell_index": 3,
        "must_contain": ["partial", "宿主不可达"],
        "why": "已裁 A：投递半＝宿主不可达（非我方未做）⇒ 不得被改回「通过」，且原因不得蒸发",
    },
]
REASON_TOKENS = ["原因", "reason", "宿主不可达", "＝宿主"]
STATUS_SHAPE = re.compile(r"◐\s*\**partial|^\|\s*partial\s*\|", re.IGNORECASE)


def scan(root):
    bad, seen = [], {f: 0 for f in TARGETS}
    for rel in TARGETS:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            bad.append(f"[缺失] {rel} 不存在（门的目标文件不在 ⇒ 不得算通过）")
            continue
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                low = line.lower()
                hit = "partial" in low
                if hit:
                    seen[rel] += 1
                if hit and STATUS_SHAPE.search(line) and not any(t.lower() in low for t in REASON_TOKENS):
                    bad.append(f"[R1] {rel}:{i} 状态形 partial **没有原因** ⇒ 无法判读它为什么是 partial")
                for item in KNOWN_BLOCKED:
                    if item["file"] != rel or not line.lstrip().startswith(item["row_prefix"]):
                        continue
                    cells = line.split("|")
                    idx = item["status_cell_index"]
                    cell = cells[idx] if idx < len(cells) else ""
                    cell_low = cell.lower()
                    # ★ 状态**格**必须同时含 partial 与原因；整行匹配会假绿（见上面 KNOWN_BLOCKED 注释）
                    missing = [t for t in item["must_contain"] if t.lower() not in cell_low]
                    if missing:
                        bad.append(f"[R2] {rel}:{i} 状态格缺 {missing}（状态格实为「{cell.strip()[:40]}」）—— {item['why']}")
    return bad, seen


def main():
    root = ROOT
    if "--root" in sys.argv:
        i = sys.argv.index("--root")
        if i + 1 >= len(sys.argv):
            print("用法错误：--root 后需要目录")
            return 2
        root = os.path.abspath(os.path.expanduser(sys.argv[i + 1]))
    if not os.path.isdir(root):
        print(f"用法错误：目录不存在 {root}")
        return 2

    bad, seen = scan(root)
    print("k6-partial-guard · partial 标注层核验（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
    print(f"  扫描根：{root}")
    for rel in TARGETS:
        print(f"  · {rel}：命中 partial {seen[rel]} 行")
    if bad:
        print("\n❌ 违例：")
        for b in bad:
            print("  " + b)
        return 1
    print("\n✅ 通过：状态形 partial 均带原因；已裁的宿主不可达项仍如实标 partial（未被升格、原因未蒸发）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
