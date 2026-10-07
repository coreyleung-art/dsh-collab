#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-registry.py — 标准化蓝图库（多蓝图注册/查询/relations 网络/影响分析）

用户指示（2026-09-01）：蓝图库的交互本身工具化插件化（blueprint-platform P2）。
功能：① 注册/盘点多蓝图（BP-9 元信息）② relations 关系网络查询 ③ 影响分析（变更传播）④ 跨蓝图关联跳转（引用解析）。

R006 九标准：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理。

用法：
  python3 bb-blueprint-registry.py --list                        # 盘点全部蓝图（BP-9 元信息表）
  python3 bb-blueprint-registry.py --show flowernet              # 单蓝图详情
  python3 bb-blueprint-registry.py --relations                   # 关系网络（全边）
  python3 bb-blueprint-registry.py --relations --bp agent-network  # 单蓝图关系（出/入）
  python3 bb-blueprint-registry.py --deps-tree flowernet         # 依赖树（递归上游/下游）
  python3 bb-blueprint-registry.py --impact agent-network        # 影响分析（变更→哪些受影响）
  python3 bb-blueprint-registry.py --refs aistartup              # 谁引用了该蓝图（反向查）
  python3 bb-blueprint-registry.py --selfcheck                   # TCC
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, ast

BB = "http://127.0.0.1:8792"
BP9_FIELDS = ["id", "name", "version", "mainlines", "stages", "works", "gate", "status", "ts"]
VERSION = "v1.0.0"
KNOWN_BLUEPRINTS = ["flowernet", "flowernet-platform", "agent-network", "blueprint-platform", "aistartup"]

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
    """读蓝图：优先独立 key（agent-network 等），fallback stages（flowernet 主蓝图在 stages）"""
    d = fetch(f"data/blueprint/{bp_id}")
    if "error" not in d and d.get("value"):
        v = d["value"]
        if isinstance(v, dict) and "id" in v:
            return v
    # flowernet 主蓝图在 stages —— ★ 仅当 bp_id 就是 flowernet 时才回退，
    # 否则未知 id 会静默显示 flowernet 的数据（本次发现的 bug）
    if bp_id != "flowernet":
        return None
    s = fetch("data/blueprint/stages")
    if "error" not in s and s.get("value"):
        sv = s["value"]
        if isinstance(sv, dict) and sv.get("version"):
            sv["id"] = "flowernet"
            sv["name"] = sv.get("name", "花店生意演进")
            # works 从 works key 补
            w = fetch("data/blueprint/works")
            if "error" not in w and w.get("value"):
                sv["works"] = w["value"].get("blueprint_map", [])
            return sv
    return None

def get_relations():
    d = fetch("data/blueprint/relations")
    if "error" in d:
        return {"blueprints": KNOWN_BLUEPRINTS, "edges": []}
    v = d.get("value", {})
    if isinstance(v, dict) and "edges" in v:
        return v
    if isinstance(v, dict) and "value" in v:
        return v["value"]
    return {"blueprints": KNOWN_BLUEPRINTS, "edges": []}

# ─────────── --list：盘点全部蓝图 ───────────
def cmd_list():
    rel = get_relations()
    bps = rel.get("blueprints", KNOWN_BLUEPRINTS)
    print("== 标准化蓝图库（%d 份）==" % len(bps))
    print(f"{'蓝图':<20} {'维度':<12} {'版本':<16} {'状态':<8} 主线")
    print("-" * 80)
    for bp_id in bps:
        bp = get_blueprint(bp_id)
        if not bp:
            print(f"{bp_id:<20} (读失败)")
            continue
        mains = ", ".join(bp.get("mainlines", {}).keys()) if isinstance(bp.get("mainlines"), dict) else ""
        dim = {"flowernet": "业务", "aistartup": "业务", "flowernet-platform": "技术",
               "agent-network": "底座", "blueprint-platform": "元层", "rule-judge": "验证",
               "banking": "业务", "flowernet-erp": "子蓝图", "flowernet-miniapp": "子蓝图",
               "flowernet-website": "子蓝图", "memory-governance": "子蓝图", "gene-bank": "底座", "distributed-network": "底座",
               "mtm": "工具", "laodeng-app": "产品",
               "mingjian-toolchain": "工具", "flowernet-jv": "公司级",
               "flowernet-citywar": "子蓝图", "flowernet-supply": "子蓝图",
               "flowernet-ops": "子蓝图", "merchant-ops-ai": "子蓝图"}.get(bp_id, "?")
        st = bp.get("status", "")
        if not st and bp_id == "flowernet":
            st = "active"  # flowernet 主蓝图从 stages 推断
        print(f"{bp_id:<20} {dim:<12} {str(bp.get('version','')):<16} {str(st):<8} {mains[:30]}")

# ─────────── --show：单蓝图详情 ───────────
def cmd_show(bp_id):
    bp = get_blueprint(bp_id)
    if not bp:
        print(f"❌ 蓝图 {bp_id} 不存在"); return
    print(f"# {bp_id} · {bp.get('name','')} · {bp.get('version','')}")
    print(f"状态: {bp.get('status','')} | 门禁: {str(bp.get('gate',''))[:80]}")
    print("\n主线:")
    for mid, m in (bp.get("mainlines") or {}).items():
        print(f"  {mid}: {m.get('name','')} — {m.get('desc','')[:40]}")
    print("\n阶段:")
    for st in bp.get("stages", []):
        subs = ", ".join(ss.get("id","") for ss in st.get("substages", []))
        print(f"  [{st.get('status')}] {st.get('stage')} {st.get('name')} — {subs[:60]}")
    sw = bp.get("switches", {})
    if sw:
        print("\n自动化开关锁:")
        for sid, sd in sw.items():
            print(f"  {sid}: {sd.get('automation','')[:40]} [默认 {sd.get('default_state','OFF')}]")

# ─────────── --relations：关系网络 ───────────
def cmd_relations(bp_filter=""):
    rel = get_relations()
    edges = rel.get("edges", [])
    if bp_filter:
        edges = [e for e in edges if e["from"] == bp_filter or e["to"] == bp_filter]
    print("== 蓝图关系网络（%d 条边，类型: %s）==" % (len(edges), ", ".join(rel.get("relation_types", []))))
    if not edges:
        print("（无关系）"); return
    for e in edges:
        arrow = {"contains": "⊃", "depends_on": "→依赖", "requires": "→要求",
                 "consumes": "→消费", "manages": "→管理", "references": "→引用"}.get(e["type"], "→" + e["type"])
        print(f"  {e['from']} {arrow} {e['to']}  ({e.get('desc','')[:50]})")

# ─────────── --deps-tree：依赖树（递归）───────────
def cmd_deps_tree(bp_id, reverse=False):
    rel = get_relations()
    edges = rel.get("edges", [])
    visited = set()
    def walk(node, depth, is_last):
        indent = "  " * depth + ("└─ " if is_last else "├─ ")
        print(indent + node)
        if node in visited:
            print("  " * (depth+1) + "(cycle)")
            return
        visited.add(node)
        if reverse:
            kids = [e["from"] for e in edges if e["to"] == node]
        else:
            kids = [e["to"] for e in edges if e["from"] == node]
        for i, k in enumerate(kids):
            walk(k, depth+1, i == len(kids)-1)
        visited.discard(node)
    print(f"== {'上游' if reverse else '下游'}依赖树: {bp_id} ==")
    walk(bp_id, 0, True)

# ─────────── --impact：影响分析 ───────────
def cmd_impact(bp_id):
    """变更某蓝图 → 传播到哪些下游"""
    rel = get_relations()
    edges = rel.get("edges", [])
    # 下游传播（含间接）
    affected = set()
    queue = [bp_id]
    visited = set()
    while queue:
        node = queue.pop(0)
        if node in visited: continue
        visited.add(node)
        for e in edges:
            if e["from"] == node and e["to"] not in visited:
                affected.add(e["to"])
                queue.append(e["to"])
    print(f"== 影响分析: {bp_id} 变更 → {len(affected)} 个下游受影响 ==")
    for a in sorted(affected):
        # 找路径说明
        path_edges = [e for e in edges if e["from"] == bp_id and e["to"] == a] or [e for e in edges if e["to"] == a and e["from"] in visited]
        print(f"  ⚡ {a}")
    # 影响规则提示
    rules = rel.get("impact_rules", [])
    if rules:
        print("\n影响传播规则:")
        for r in rules:
            print(f"  • {r[:70]}")

# ─────────── --refs：反向引用 ───────────
def cmd_refs(bp_id):
    rel = get_relations()
    edges = rel.get("edges", [])
    refs = [e for e in edges if e["to"] == bp_id]
    print(f"== 关系图引用 {bp_id}（{len(refs)} 处）==")
    for e in refs:
        print(f"  {e['from']} -{e['type']}-> {bp_id}")
    # bp1-2: 蓝图 md 正文引用(blueprint:<id> 语法)扫描
    import glob as _g, re as _re
    hits = []
    bp_dir = os.path.expanduser("~/dsh-collab/data/blueprint")
    for md in _g.glob(bp_dir + "/*/*.md") + _g.glob(bp_dir + "/*.md"):
        try:
            txt = open(md, encoding="utf-8").read()
        except Exception: continue
        # 找引用目标(蓝图目录名含 bp_id 或 blueprint:bp_id)
        for m in _re.finditer(r"blueprint:\s*([a-z0-9-]+)(?:#([0-9.]+))?", txt):
            if m.group(1) == bp_id or bp_id.startswith(m.group(1)):
                src = os.path.basename(md).replace(".md", "")
                hits.append((src, m.group(2) or "*"))
    if hits:
        print(f"== md 正文引用(blueprint:{bp_id}#stage) {len(hits)} 处 ==")
        seen = set()
        for src, stg in hits:
            k = (src, stg)
            if k not in seen:
                seen.add(k)
                print(f"  {src} → {bp_id}#{stg}")
    elif bp_id != "all":
        print("(无 md 正文引用标注 — 文档内未用 blueprint:<id> 语法)")

# ─────────── TCC ───────────
def selfcheck():
    ok = True
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    d = fetch("data/blueprint/relations")
    if "error" in d:
        print(f"❌ 黑板不可达: {d['error']}"); ok = False
    else:
        print("✅ 黑板连通")
    try:
        get_relations()
        print("✅ relations 可用")
    except Exception as e:
        print(f"❌ relations: {e}"); ok = False
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="标准化蓝图库（registry）")
    ap.add_argument("--list", action="store_true", help="盘点全部蓝图")
    ap.add_argument("--show", default="", help="单蓝图详情")
    ap.add_argument("--relations", action="store_true", help="关系网络")
    ap.add_argument("--bp", default="", help="蓝图过滤")
    ap.add_argument("--deps-tree", default="", help="依赖树")
    ap.add_argument("--reverse", action="store_true", help="依赖树方向（上游）")
    ap.add_argument("--impact", default="", help="影响分析")
    ap.add_argument("--refs", default="", help="反向引用查询")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"bb-blueprint-registry {VERSION}")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.list:
        cmd_list()
    elif args.show:
        cmd_show(args.show)
    elif args.relations:
        cmd_relations(args.bp)
    elif args.deps_tree:
        cmd_deps_tree(args.deps_tree, args.reverse)
    elif args.impact:
        cmd_impact(args.impact)
    elif args.refs:
        cmd_refs(args.refs)
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
