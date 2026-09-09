#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""研究沉淀同步工具 v0.1 (HR)

职责：把 dsh-collab/research/ops-science/*.md 的关键结论同步为 Obsidian vault wiki 编译页的骨架，
     并生成知识库入库提示（agent 需用 knowledge_* 工具实际入库/嵌入）。
用法：python3 research-sink.py [--dry-run]

说明：vault 路径=iCloud Obsidian；本脚本只生成/更新骨架与清单，编译由 agent 负责（LLM 提炼）。
"""
import argparse, glob, os

VAULT = os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents")
SRC = os.path.expanduser("~/dsh-collab/research/ops-science")

MAP = {
    "flower-shop-evolution-research.md": "wiki/concepts/flower-shop-evolution.md",
    "ai-ops-science-lab-design.md": "wiki/concepts/ai-ops-science-lab.md",
    "phone-control-platform-comparison.md": "wiki/concepts/market-research-automation.md",
    "token-cost-research-roadmap.md": "wiki/concepts/token-cost-governance.md",
    "research-paper-library-index.md": "wiki/research-paper-library.md",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    print("=== research-sink v0.1 (骨架同步) ===")
    print("源目录:", SRC)
    print("vault :", VAULT)
    missing = [f for f in MAP if not os.path.exists(os.path.join(SRC, f))]
    if missing: print("⚠️ 源缺失:", missing)
    for src, dst in MAP.items():
        s = os.path.join(SRC, src); d = os.path.join(VAULT, dst)
        action = "exists" if os.path.exists(d) else "NEEDS-CREATE"
        print(f"  {src} -> {dst} [{action}]" + (" (dry)" if args.dry_run else ""))
    print("=== 下一步（agent） ===")
    print("1. NEEDS-CREATE 页面由 agent 用 LLM 提炼编译（参考 raw/research-session-thoughts）")
    print("2. 论文全文: 运行 paper-fetch.py + knowledge_add_document(baseId=afa7de13-...)")
    print("3. 每日审查: 运行 token-roi-review.py（成本治理恢复后由 launchd 触发）")

if __name__ == "__main__":
    main()