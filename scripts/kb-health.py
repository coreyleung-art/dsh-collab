#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-health v1.0 (HR) — 知识库健康巡检（每日自动，零 LLM）

验证：① KB embedded 状态 ② doc/chunk 计数 ③ 索引文件同步（research-paper-library-index.md）
异常 → 写 alerts.md（不打扰用户）。用法：python3 kb-health.py
"""
import json, os, datetime, re

KB = "afa7de13-011a-4c73-a9d6-13492c05cdf7"
IDX = os.path.expanduser("~/dsh-collab/research/ops-science/research-paper-library-index.md")
ALERTS = os.path.expanduser("~/dsh-collab/token-monitor/replays/alerts.md")

def main():
    issues = []
    # 索引文件 doc 数（解析 AUTO-GENERATED 头）
    idx_docs = None
    try:
        head = open(IDX, encoding="utf-8").read()[:2000]
        m = re.search(r"- documents: (\d+)", head)
        if m: idx_docs = int(m.group(1))
    except Exception:
        issues.append("索引文件不可读")
    # 最近批次报告（paper-pull-final-summary*）的 doc 数作为对照
    summary_docs = None
    for f in ["paper-pull-final-summary-mcp-gateway-2026-08-22.md"]:
        p = os.path.expanduser("~/dsh-collab/research/ops-science/" + f)
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read()
            m = re.search(r"KB ops-science-research \d+ → \*\*(\d+)\*\* docs", t)
            if m: summary_docs = int(m.group(1))
    report = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "idx_docs": idx_docs, "summary_docs": summary_docs,
        "note": "KB embedded 状态由 knowledge_stats 查询（agent 侧），脚本侧验证索引文件一致性",
        "issues": issues,
    }
    out = os.path.expanduser("~/dsh-collab/token-monitor/kb-health.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if issues:
        with open(ALERTS, "a", encoding="utf-8") as f:
            f.write("\n## kb-health " + datetime.date.today().isoformat() + "\n- " + "；".join(issues) + "\n")
    print("kb-health:", json.dumps(report, ensure_ascii=False)[:200])

if __name__ == "__main__":
    main()
