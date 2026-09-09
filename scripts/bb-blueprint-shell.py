#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-shell.py — 蓝图交互式 shell（关联跳转/引用解析/导航）

用户指示（2026-09-01）：蓝图之间父子关系相互引用 + 关联跳转能力。
功能：交互式 REPL——在蓝图/阶段/任务卡间导航跳转；引用语法解析（blueprint:<id>#<stage>）。

R006 九标准：CLI 形态 / TCC / 文档化 / 版本管理 / 自动落链 / CLI 治理。

用法：
  python3 bb-blueprint-shell.py --bp flowernet         # 进入蓝图（交互模式）
  python3 bb-blueprint-shell.py --resolve 'blueprint:flowernet#d3-3'   # 解析引用→定位
  python3 bb-blueprint-shell.py --nav flowernet d3-3   # 导航到阶段
  python3 bb-blueprint-shell.py --version              # 版本
  交互命令: list / ls <bp> / go <bp> / stage <id> / refs / back / help / exit
"""
import argparse, json, sys, datetime, urllib.request, ast, re

BB = "http://127.0.0.1:8792"
VERSION = "v1.0.0"

def _url(path):
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def get_blueprint(bp_id):
    d = fetch(f"data/blueprint/{bp_id}")
    if "error" not in d and d.get("value"):
        v = d["value"]
        if isinstance(v, dict) and "id" in v:
            return v
    s = fetch("data/blueprint/stages")
    if "error" not in s and s.get("value"):
        sv = s["value"]
        if isinstance(sv, dict) and sv.get("version"):
            sv["id"] = "flowernet"
            sv["name"] = sv.get("name", "花店生意演进")
            w = fetch("data/blueprint/works")
            if "error" not in w and w.get("value"):
                sv["works"] = w["value"].get("blueprint_map", [])
            return sv
    return None

def get_relations():
    d = fetch("data/blueprint/relations")
    if "error" in d:
        return {"edges": []}
    v = d.get("value", {})
    if isinstance(v, dict) and "edges" in v:
        return v
    if isinstance(v, dict) and "value" in v:
        return v["value"]
    return {"edges": []}

def resolve_ref(ref):
    """解析引用语法 blueprint:<id>#<stage> / @blueprint:<id>#<stage> → 定位"""
    m = re.match(r'@?blueprint:(\w[\w-]*)(?:#([\w-]+))?', ref)
    if not m:
        return None, None, None
    bp_id, stage = m.group(1), m.group(2)
    bp = get_blueprint(bp_id)
    if not bp:
        return bp_id, None, None
    stage_info = None
    if stage:
        for st in bp.get("stages", []):
            if st.get("id") == stage:
                stage_info = st
                break
            for ss in st.get("substages", []):
                if ss.get("id") == stage:
                    stage_info = ss
                    break
    return bp_id, stage, stage_info

# ─────────── 交互 REPL ───────────
def repl(start_bp=""):
    current = start_bp or "flowernet"
    print(f"🌸 蓝图 Shell v{VERSION} — 当前蓝图: {current}（输入 help 查看命令）")
    while True:
        try:
            line = input(f"[{current}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye 👋"); break
        if not line:
            continue
        if line in ("exit", "quit", "q"):
            print("bye 👋"); break
        elif line in ("help", "h"):
            print("命令: list | ls <bp> | go <bp> | stage <id> | refs | resolve <引用> | back | exit")
        elif line in ("list", "ls"):
            rel = get_relations()
            for b in rel.get("blueprints", []):
                print(f"  {b}")
        elif line.startswith("ls ") or line.startswith("go "):
            target = line.split(" ", 1)[1]
            bp = get_blueprint(target)
            if bp:
                current = target
                print(f"📍 进入 {target} · {bp.get('name','')} · {bp.get('version','')}")
                for st in bp.get("stages", []):
                    subs = ", ".join(ss.get("id","") for ss in st.get("substages", []))
                    print(f"  [{st.get('status')}] {st.get('stage')} {st.get('name')} — {subs[:60]}")
            else:
                print(f"❌ 蓝图 {target} 不存在")
        elif line.startswith("stage "):
            sid = line.split(" ", 1)[1]
            bp = get_blueprint(current)
            if not bp: continue
            for st in bp.get("stages", []):
                for ss in st.get("substages", []):
                    if ss.get("id") == sid or st.get("id") == sid:
                        print(f"📍 {current}#{ss.get('id')} {ss.get('name')} [{ss.get('status')}]")
                        print(f"   note: {ss.get('note','')}")
                        # 关联跳转：显示引用了此阶段的其他蓝图
                        rel = get_relations()
                        refs = [e for e in rel.get("edges", []) if e["to"] == current or e["from"] == current]
                        if refs:
                            print("   🔗 关联蓝图:")
                            for e in refs:
                                print(f"     {e['from']} -{e['type']}-> {e['to']}  （go {e['from'] if e['to']==current else e['to']} 跳转）")
        elif line == "refs":
            rel = get_relations()
            for e in rel.get("edges", []):
                if e["from"] == current or e["to"] == current:
                    print(f"  {e['from']} -{e['type']}-> {e['to']}  ({e.get('desc','')[:40]})")
        elif line.startswith("resolve "):
            ref = line.split(" ", 1)[1]
            bp_id, stage, info = resolve_ref(ref)
            if bp_id and stage:
                print(f"📍 {ref} → {bp_id}#{stage} {info.get('name','') if info else ''} [{info.get('status','') if info else '?'}]")
            elif bp_id:
                print(f"📍 {ref} → {bp_id}（蓝图级）")
            else:
                print(f"❌ 无法解析: {ref}")
        elif line == "back":
            current = "flowernet"
            print(f"📍 回到默认蓝图: {current}")
        else:
            print("未知命令（help 查看）")

def main():
    ap = argparse.ArgumentParser(description="蓝图交互 shell（关联跳转/引用解析）")
    ap.add_argument("--bp", default="", help="初始蓝图")
    ap.add_argument("--resolve", default="", help="解析引用（一次性）")
    ap.add_argument("--nav", nargs=2, metavar=("BP", "STAGE"), help="导航到蓝图阶段")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"bb-blueprint-shell {VERSION}")
    args = ap.parse_args()

    if args.selfcheck:
        ok = True
        try:
            ast.parse(open(__file__).read()); print("✅ 语法 OK")
        except SyntaxError:
            print("❌ 语法"); ok = False
        d = fetch("data/blueprint/relations")
        print("✅ 黑板连通" if "error" not in d else f"❌ {d['error']}")
        print("TCC:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)
    elif args.resolve:
        bp_id, stage, info = resolve_ref(args.resolve)
        if bp_id and stage:
            print(f"📍 {args.resolve} → {bp_id}#{stage} {info.get('name','') if info else ''}")
        elif bp_id:
            print(f"📍 {args.resolve} → {bp_id}（蓝图级）")
        else:
            print(f"❌ 无法解析: {args.resolve}")
    elif args.nav:
        bp_id, stage = args.nav
        _, _, info = resolve_ref(f"blueprint:{bp_id}#{stage}")
        print(f"📍 {bp_id}#{stage}: {info.get('name','') if info else '未找到阶段'} [{info.get('status','') if info else '?'}]")
        if info:
            print(f"   note: {info.get('note','')}")
    else:
        repl(args.bp)

if __name__ == "__main__":
    main()
