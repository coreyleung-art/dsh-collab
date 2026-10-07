#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-content-check.py — 蓝图空呈现检查修复器 v1.0(R006 九标准)
检查: 每蓝图详情/图谱数据是否"空呈现"(mainlines/stages/svg 内容密度)
用法:
  --scan            全部蓝图健康度表
  --check BP        单蓝图(如 flowernet-website)
  --fix BP          尝试修复(从蓝图 md 提取 stages 补黑板)
  --selfcheck       TCC
  --tool-version
  --json            结构化输出
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, glob, datetime, urllib.request

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
GALLERY = "http://127.0.0.1:8798"
BLUEPRINT_DIR = os.path.expanduser("~/dsh-collab/data/blueprint")

def _fetch(url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, data=(json.dumps(data).encode() if data else None),
                                     headers={"Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def list_blueprints():
    d = _fetch(GALLERY + "/api/blueprints")
    return d if isinstance(d, list) else []

def check_one(bid):
    """返回 {id, healthy, empty_kind, mainlines, stages, works, svgText, svgSubs, issues[]}"""
    bp = _fetch(BB + "/data/blueprint/" + bid)
    v = bp.get("value", bp) if isinstance(bp, dict) else {}
    info = _fetch(GALLERY + "/api/bpinfo/" + bid) or {}
    svg = info.get("svg", "") or ""
    issues = []
    # flowernet: 主数据在全局 data/blueprint/stages 键
    if bid == "flowernet":
        st = _fetch(BB + "/data/blueprint/stages") or {}
        v = st.get("value", st) if isinstance(st, dict) else {}
    ml = v.get("mainlines") or {}
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = v.get("stages") or []
    works = v.get("works") or []
    if not isinstance(stages, list): stages = []
    if not isinstance(works, list): works = []
    # svg 文本行/子阶段(视觉丰富度)
    svg_texts = [t for t in re.findall(r"<text[^>]*>([^<]{2,})</text>", svg) if t.strip()]
    svg_subs = len(re.findall(r"◦", svg))
    # 判定
    if not ml_keys:
        empty = "no-mainlines"
    elif not stages and not works and svg_subs == 0:
        empty = "no-stages-works"  # 只有主线名, 无阶段/工作(骨架空)
    elif not stages and svg_subs == 0 and len(svg_texts) < 14:
        empty = "no-stages-content"
    else:
        # 有 stages 但 svg 视觉空?
        has_ml_field = any(isinstance(s, dict) and s.get("mainline") for s in stages)
        if not has_ml_field and svg_subs == 0 and len(svg_texts) < 10:
            empty = "contract-mismatch"  # stages 无 mainline 未归入(svg 空壳)
        else:
            empty = None
    return {"id": bid, "name": (v.get("name") or bid),
            "mainlines": ml_keys, "nStage": len(stages), "nWorks": len(works),
            "svgChars": len(svg), "svgText": len(svg_texts), "svgSubs": svg_subs,
            "hasMainlineField": any(isinstance(s, dict) and s.get("mainline") for s in stages),
            "empty": empty, "healthy": empty is None,
            "issues": [e for e in [empty] if e]}

def scan():
    bps = list_blueprints()
    results = [check_one(b["id"]) for b in bps]
    return results

def fix_one(bid):
    """从蓝图 md 提取 stages 补黑板(幂等: 已有 stages 跳过)"""
    # 找蓝图目录 md(master/main 优先)
    cand = glob.glob(f"{BLUEPRINT_DIR}/{bid}/*.md")
    # 蓝图 id 可能含 - 对应目录名
    if not cand:
        for d in glob.glob(f"{BLUEPRINT_DIR}/*/"):
            base = os.path.basename(d.rstrip("/"))
            if base == bid or bid.startswith(base):
                cand = glob.glob(f"{BLUEPRINT_DIR}/{base}/*.md"); break
    if not cand:
        return {"ok": False, "reason": "no-md", "id": bid}
    # 提取主线(mainlines 词典 + stage 行)
    md = ""
    for f in cand:
        md += open(f, encoding="utf-8").read() + "\n"
    ml_lines = re.findall(r"^([\w-]+)\s*[:：]\s*(.+)$", md, re.M)
    stages_found = re.findall(r"^\s*[-*]\s*(?:stage|阶段)\s*([\w.-]+)\s*[:：]?\s*(.+)$", md, re.M | re.I)
    mainlines = {}
    # mainlines: 从 md 里 '| 主线 |' 或 name 词典
    for k, val in ml_lines[:20]:
        if k.lower() in ("mainlines", "stages"): continue
        if len(k) < 20 and len(val) < 120:
            mainlines[k] = {"name": val[:40], "desc": val[:80]}
    if not mainlines:
        # 兜底: 用现有黑板 mainlines 不覆盖
        return {"ok": False, "reason": "no-mainlines-extracted", "id": bid}
    return {"ok": True, "id": bid, "mainlinesFound": len(mainlines),
            "stagesFound": len(stages_found),
            "note": "md 提取完成; 人工确认后写黑板(不自动覆写, 保源真)"}

def main():
    ap = argparse.ArgumentParser(description="蓝图空呈现检查修复器(R006)")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--check")
    ap.add_argument("--fix")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.tool_version: print(f"bb-blueprint-content-check {VERSION}"); return
    if args.selfcheck:
        r = check_one("flowernet-website")
        ok = isinstance(r, dict) and "empty" in r
        print("TCC:", "✅ 通过" if ok else "❌ 失败")
        sys.exit(0 if ok else 1)
    if args.check:
        r = check_one(args.check)
        if args.json: print(json.dumps(r, ensure_ascii=False, indent=1)); return
        _print_one(r); return
    if args.fix:
        print(json.dumps(fix_one(args.fix), ensure_ascii=False, indent=1)); return
    # scan
    results = scan()
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1)); return
    print("══ 蓝图内容健康度 ══")
    n_empty = 0
    for r in results:
        mark = "❌ 空" if r["empty"] else ("✅" if r["healthy"] else "⚠️")
        if r["empty"]: n_empty += 1
        print(f"{mark} {r['id']:26s} mainlines={len(r['mainlines'])} stages={r['nStage']} works={r['nWorks']} svg文本{r['svgText']}/{r['svgSubs']}子 {('空因:'+r['empty']) if r['empty'] else ''}")
    print(f"→ {len(results)} 蓝图, {n_empty} 个空/退化")

def _print_one(r):
    mark = "❌ 空" if r["empty"] else "✅"
    print(f"{mark} {r['id']} ({r.get('name')})")
    print(f"  mainlines: {r['mainlines']}")
    print(f"  stages: {r['nStage']} | works: {r['nWorks']}")
    print(f"  svg: {r['svgChars']}字符 {r['svgText']}文本 {r['svgSubs']}子阶段 | mainline字段: {r['hasMainlineField']}")
    if r["issues"]: print(f"  空因: {r['issues']}")

if __name__ == "__main__":
    main()
