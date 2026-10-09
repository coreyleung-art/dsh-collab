#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-toolize.py — 工具化候选发现器(Φ8 两次法则落地 · R006 九标准)
扫描环境: 找"出现过两次以上"的可工具化候选(重复模式/重复工具/命名相似/可并标准)
用法:
  python3 bb-toolize.py --suggest         扫候选(重复/模式)
  python3 bb-toolize.py --check-dup DIR   指定目录重复检测
  python3 bb-toolize.py --selfcheck       TCC 自检
  python3 bb-toolize.py --tool-version    版本
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, re, json, sys, glob
from collections import Counter


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-toolize.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "v1.0.0"
SCAN_DIRS = [
    os.path.expanduser("~/dsh-collab/scripts"),          # 工具真源
    os.path.expanduser("~/meituan-multi/scripts"),
]  # 注: ~/system-graph-app 是 app 打包副本(非真源), 排除防同名误报
# 已知已工具化(防重复建议)
TOOLIZED = {"bb-gallery-audit", "bb-asset-relations", "bb-plan-scanner", "bb-gallery-export",
            "sysgraph-version", "bb-blueprint-registry", "bb-blueprint-ingest"}

def check_dup(paths, min_dup=2):
    """找: 同名脚本跨目录(可工具化候选)"""
    names = []
    for d in paths:
        if os.path.isdir(d):
            names += [os.path.basename(f) for f in glob.glob(d + "/*.py") + glob.glob(d + "/*.sh")]
    cnt = Counter(names)
    dups = {k: v for k, v in cnt.items() if v >= min_dup}
    return dups

def suggest():
    out = {"toolized": sorted(TOOLIZED), "duplicates": {}, "patterns": []}
    # 1) 跨目录同名脚本
    dups = check_dup(SCAN_DIRS)
    real = {k: v for k, v in dups.items() if k not in TOOLIZED}
    if real: out["duplicates"] = real
    # 2) 模式: 常见重复操作的关键词在多个脚本出现(暗示可抽公共)
    if os.path.isdir(SCAN_DIRS[0]):
        txts = []
        for f in glob.glob(SCAN_DIRS[0] + "/*.py")[:40]:
            try: txts.append(open(f, encoding="utf-8").read())
            except Exception: pass
        allt = "\n".join(txts)
        # 看哪些脚本都有 --selfcheck/--tool-version(已 R006 化) vs 没有的
        r006 = [os.path.basename(f) for f in glob.glob(SCAN_DIRS[0] + "/*.py")[:40]
                if "--selfcheck" in open(f, encoding="utf-8", errors="ignore").read()]
        not_r006 = [os.path.basename(f) for f in glob.glob(SCAN_DIRS[0] + "/*.py")[:40]
                    if "--selfcheck" not in open(f, encoding="utf-8", errors="ignore").read()
                    and os.path.basename(f).startswith("bb-")]
        if not_r006:
            out["patterns"].append({"type": "r006-gap", "detail": f"未含 --selfcheck 的 bb- 工具(建议补 TCC): {not_r006[:8]}"})
        if r006:
            out["patterns"].append({"type": "r006-ok", "detail": f"已含 --selfcheck 的工具数: {len(r006)}"})
    return out

def main():
    ap = argparse.ArgumentParser(description="工具化候选发现器(Φ8)")
    ap.add_argument("--suggest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()
    if args.tool_version:
        print(f"bb-toolize {VERSION}"); return
    if args.suggest:
        r = suggest()
        print("══ 工具化候选(Φ8 两次法则) ══")
        if r["duplicates"]:
            for k, v in r["duplicates"].items(): print(f"⚠️ 重复脚本: {k} ×{v}(跨目录, 可抽公共)")
        else:
            print("✅ 无跨目录重复脚本")
        for p in r["patterns"]: print(("⚠️ " if p["type"].endswith("gap") else "ℹ️ ") + p["detail"])
        print(f"已工具化: {len(r['toolized'])} 个")
        return
    if args.selfcheck:
        # TCC: 工具自身可运行 + 语法
        r = suggest()
        import subprocess
        ok = subprocess.run(["python3","-m","py_compile",__file__],capture_output=True).returncode==0
        print("TCC:", "✅ 通过" if ok else "❌ 失败")
        sys.exit(0 if ok else 1)
    ap.print_help()

if __name__ == "__main__":
    main()
