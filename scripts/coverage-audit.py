#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coverage-audit v0.1 — 文档摄取覆盖全景 (audit 工具族)
域: 文档知识摄取覆盖 — 适用角色: 文汇(55d4d1bd)
数据源: Obsidian vault raw/ + research/ (摄取目标) + 各业务域目录 (摄取源)
模式: 域全景扫描 → 摄取源×摄取状态 覆盖矩阵 → Φ10 判断输入
输出:
  A. 摄取覆盖 (各域 → raw 是否已摄取)
  B. 缺口矩阵 (落盘但未摄取/未索引的文档)
用法:
  coverage-audit.py scan                  # 摄取覆盖全景
  coverage-audit.py gaps                  # 摄取缺口
  coverage-audit.py --lean4-check         # 自检 (只读)
  coverage-audit.py --version
"""
import os
import re
import sys

VERSION = "0.2.0"
VAULT = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents")
STATE_FILE = os.path.expanduser("~/.dsh/ingest-state.json")
# 各业务域落盘目录 (摄取源) → 应摄取进 raw/
SOURCE_DIRS = {
    "supply-chain": os.path.expanduser("~/dsh-collab/supply-chain"),
    "plugin-scan": os.path.expanduser("~/dsh-collab/plugin-scan"),
    "qa": os.path.expanduser("~/dsh-collab/qa"),
    "cld-health": os.path.expanduser("~/dsh-collab/cld-health"),
    "cost-governance": os.path.expanduser("~/dsh-collab/research/cost-governance"),
    "ops": os.path.expanduser("~/dsh-collab/ops"),
}


def _load_ingest_state() -> dict:
    """权威摄取状态: {源相对路径: hash}——与 ingest-pipeline 一致（v0.2 修复：
    原按 raw/ 文件名启发式猜测覆盖，漏 raw/d-55d4- 域且无法精确匹配）"""
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            import json
            return json.load(f)
    return {}


def _raw_files():
    """v0.2: 已摄取 = ingest-state 中登记的源相对路径集合（权威口径）"""
    state = _load_ingest_state()
    return set(state.keys())


def _domain_files(path: str) -> list:
    if not os.path.isdir(path):
        return []
    files = []
    for f in os.listdir(path):
        if f.endswith((".md", ".json")) and not f.startswith("."):
            files.append(f)
    return files


def scan() -> dict:
    """A: 摄取覆盖 (各域文件 → 是否已摄取) —— 基于 ingest-state 精确判定"""
    ingested = _raw_files()
    result = {}
    for domain, path in SOURCE_DIRS.items():
        files = _domain_files(path)
        # ingest-state 键 = 相对 dsh-collab 的路径（如 supply-chain/xxx.md）
        covered = sum(1 for f in files if f"{domain}/{f}" in ingested)
        result[domain] = {"files": len(files), "covered": covered,
                          "gap": len(files) - covered,
                          "missing": sorted(f for f in files if f"{domain}/{f}" not in ingested)}
    return result


def gaps() -> dict:
    """B: 缺口 (各域未摄取文件)"""
    state = _load_ingest_state()
    gaps_out = {}
    for domain, path in SOURCE_DIRS.items():
        missing = [f for f in _domain_files(path)
                   if f"{domain}/{f}" not in state]
        if missing:
            gaps_out[domain] = missing
    return gaps_out


def _lean4_check() -> int:
    ok = True
    out = [f"== Lean4 约束门自检 (coverage-audit v{VERSION}) =="]
    src = open(__file__).read()
    checks = [
        ("① 只读无破坏写", not re.search(r"rm\s+-rf|os\.remove|shutil\.rmtree|open\([^)]*['\"]w['\"]", src)),
        ("② scan 返回结构", isinstance(scan(), dict)),
        ("③ vault 存在", os.path.isdir(VAULT)),
        ("④ gaps 返回 dict", isinstance(gaps(), dict)),
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
        print(f"coverage-audit v{VERSION}")
        raise SystemExit(0)
    import json
    if not args or args[0] == "scan":
        print(json.dumps(scan(), ensure_ascii=False, indent=2))
    elif args[0] == "gaps":
        print(json.dumps(gaps(), ensure_ascii=False, indent=2))
    else:
        print("用法: coverage-audit.py [scan|gaps|--lean4-check|--version]")
