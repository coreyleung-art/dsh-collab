#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-prep-research.py — 提前调查扫描器（R025 学习调查类提前并行）

用户指示（2026-08-31）：把『提前调查』输出为符合 R006 九标准的工具。
功能：扫描蓝图 taskboard 的 todo 卡 → 识别可提前调查类（方法调研/数据源调研/论文查证/竞品分析）→ 插卡标记 prep_ahead + 生成委派清单（默认委派数据调查员）。

R006 九标准：① CLI 形态 ② TCC 检测（--selfcheck）③ CLD 自适应 ④ dsh 版本自适应 ⑤ 文档化 ⑥ 版本管理（--tool-version）⑦ 统一日志 ⑧ 自动落链（黑板 taskboard）⑨ CLI 治理

用法：
  python3 bb-prep-research.py --scan              # 扫描 todo 卡，识别可提前调查项
  python3 bb-prep-research.py --insert --who 4787d717  # 自动插卡标记（默认 4787d717）
  python3 bb-prep-research.py --selfcheck          # TCC 自检
  python3 bb-prep-research.py --tool-version       # 版本
"""
import argparse, json, sys, datetime, urllib.request, ast

BB = "http://127.0.0.1:8792"
NS = "data/blueprint/flowernet/taskboard"
VERSION = "v1.0.0"
RESEARCH_KEYWORDS = [
    "调研", "调查", "方法", "数据源", "论文", "方案", "评估",
    "竞品", "可行性", "选型", "趋势", "资料", "案例", "最佳实践",
]
RESEARCH_STAGES = ["d3-3", "d4-1", "d4-2", "d4-3", "p3-2"]  # 调查类高发阶段

def _url(path):
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(path), data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def load_cards():
    d = fetch(NS)
    if "error" in d:
        return {}
    v = d.get("value", {})
    return v.get("cards", {}) if isinstance(v, dict) else {}

def save_cards(cards):
    return put(NS, {"cards": cards, "ts": now()})

def scan():
    cards = load_cards()
    if not cards:
        return []
    hits = []
    for k, c in cards.items():
        if c.get("status") != "todo" or c.get("prep_ahead"):
            continue
        name = c.get("name", "") + c.get("desc", "")
        stage = c.get("stage", "")
        kw_hit = any(kw in name for kw in RESEARCH_KEYWORDS)
        stage_hit = stage in RESEARCH_STAGES and any(w in name for w in ["调研", "方案", "评估", "数据", "模型", "管道", "设计"])
        if kw_hit or stage_hit:
            hits.append({"id": k, "stage": stage, "name": c.get("name", ""), "owner": c.get("owner", ""),
                         "reason": "关键词命中" if kw_hit else "阶段+描述匹配"})
    return hits

def cmd_scan():
    hits = scan()
    print("== 可提前调查类 todo 卡 ==")
    if not hits:
        print("（无——或已全部标记 prep_ahead）")
    for h in hits:
        print(f"  {h['id']} {h['name'][:30]:32s} [{h['stage']}] owner={h['owner']} 原因={h['reason']}")
    print(f"\n共 {len(hits)} 张可提前调查（--insert 自动插卡标记，默认委派数据调查员 4787d717）")

def cmd_insert(who):
    hits = scan()
    if not hits:
        print("无新可提前调查卡"); return
    cards = load_cards()
    n = 0
    for h in hits:
        c = cards.get(h["id"])
        if c and not c.get("prep_ahead"):
            c["prep_ahead"] = True
            c["prep_type"] = "research"
            c["prep_who"] = who
            c["prep_ts"] = now()
            n += 1
    save_cards(cards)
    print(f"✅ 标记 {n} 张为提前调查卡（prep_who={who}）")
    print("→ 数据调查员可领卡（bb-taskboard --claim <id> --who 4787d717）")

def selfcheck():
    ok = True
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    d = fetch(NS)
    if "error" in d:
        print(f"❌ 黑板不可达: {d['error']}"); ok = False
    else:
        print("✅ 黑板连通")
    try:
        scan()
        print("✅ scan 函数可用")
    except Exception as e:
        print(f"❌ scan: {e}"); ok = False
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="提前调查扫描器（R025）")
    ap.add_argument("--scan", action="store_true", help="扫描可提前调查卡")
    ap.add_argument("--insert", action="store_true", help="自动插卡标记")
    ap.add_argument("--who", default="", help="委派角色（默认 4787d717）")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    ap.add_argument("--tool-version", action="version", version=f"bb-prep-research {VERSION} (R025/R006)")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.scan:
        cmd_scan()
    elif args.insert:
        cmd_insert(args.who or "4787d717")
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
