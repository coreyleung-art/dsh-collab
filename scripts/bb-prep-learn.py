#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-prep-learn.py — 提前学习扫描器（R025 学习调查类提前并行）

用户指示（2026-08-31）：把『提前学习』输出为符合 R006 九标准的工具。
功能：扫描蓝图 taskboard 的 todo 卡 → 识别可提前学习类（数据学习/规则学习/模型学习）→ 插卡标记 prep_ahead + 生成委派清单。

R006 九标准：① CLI 形态（dsh 插件化预留）② TCC 检测（--selfcheck）③ CLD 自适应（无耦合）④ dsh 版本自适应 ⑤ 文档化（README）⑥ 版本管理（--tool-version）⑦ 统一日志（黑板落链）⑧ 自动落链（黑板 taskboard）⑨ CLI 治理（argparse）

用法：
  python3 bb-prep-learn.py --scan                # 扫描 todo 卡，识别可提前学习项
  python3 bb-prep-learn.py --insert --who 知了    # 自动插卡（识别结果 → taskboard）
  python3 bb-prep-learn.py --selfcheck           # TCC 自检（语法+依赖）
  python3 bb-prep-learn.py --tool-version        # 版本
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, ast, os

BB = "http://127.0.0.1:8792"
NS = "data/blueprint/flowernet/taskboard"
VERSION = "v1.0.0"
LEARN_KEYWORDS = [
    "学习", "基线", "分析", "规则库", "模型", "模式", "特征",
    "数据学习", "决策模式", "定价", "损耗", "预测", "SOP", "知识",
]
LEARN_STAGES = ["d3-3", "d4-2", "p2-2", "p3-2"]  # 学习类高发阶段

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

# ─────────── 扫描：识别可提前学习类 todo 卡 ───────────
def scan():
    cards = load_cards()
    if not cards:
        print("（空）先 bb-taskboard --init"); return []
    hits = []
    for k, c in cards.items():
        if c.get("status") != "todo":
            continue
        if c.get("prep_ahead"):
            continue  # 已标提前
        name = c.get("name", "") + c.get("desc", "")
        stage = c.get("stage", "")
        # 命中关键词 或 高发阶段 + 学习型描述
        kw_hit = any(kw in name for kw in LEARN_KEYWORDS)
        stage_hit = stage in LEARN_STAGES
        if kw_hit or (stage_hit and any(w in name for w in ["准备", "分析", "调研", "设计", "基线"])):
            hits.append({"id": k, "stage": stage, "name": c.get("name", ""), "owner": c.get("owner", ""), "reason": "关键词命中" if kw_hit else "阶段+描述匹配"})
    return hits

def cmd_scan():
    hits = scan()
    print("== 可提前学习类 todo 卡 ==")
    if not hits:
        print("（无——或已全部标记 prep_ahead）")
    for h in hits:
        print(f"  {h['id']} {h['name'][:30]:32s} [{h['stage']}] owner={h['owner']} 原因={h['reason']}")
    print(f"\n共 {len(hits)} 张可提前学习（--insert 自动插卡标记）")

# ─────────── 插卡标记 prep_ahead ───────────
def cmd_insert(who):
    hits = scan()
    if not hits:
        print("无新可提前学习卡"); return
    cards = load_cards()
    n = 0
    for h in hits:
        c = cards.get(h["id"])
        if c and not c.get("prep_ahead"):
            c["prep_ahead"] = True
            c["prep_type"] = "learn"
            c["prep_who"] = who
            c["prep_ts"] = now()
            n += 1
    save_cards(cards)
    print(f"✅ 标记 {n} 张为提前学习卡（prep_who={who}）")
    print("→ 执行侧可领卡（bb-taskboard --claim <id> --who <角色>）")

# ─────────── TCC 自检 ───────────
def selfcheck():
    ok = True
    # ① 语法
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    # ② 黑板连通
    d = fetch(NS)
    if "error" in d:
        print(f"❌ 黑板不可达: {d['error']}"); ok = False
    else:
        print("✅ 黑板连通")
    # ③ 核心函数
    try:
        scan()
        print("✅ scan 函数可用")
    except Exception as e:
        print(f"❌ scan: {e}"); ok = False
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="提前学习扫描器（R025）")
    ap.add_argument("--scan", action="store_true", help="扫描可提前学习卡")
    ap.add_argument("--insert", action="store_true", help="自动插卡标记")
    ap.add_argument("--who", default="", help="委派角色")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    ap.add_argument("--tool-version", action="version", version=f"bb-prep-learn {VERSION} (R025/R006)")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.scan:
        cmd_scan()
    elif args.insert:
        cmd_insert(args.who or "待指派")
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
