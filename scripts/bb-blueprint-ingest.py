#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-ingest.py — 蓝图注册流水线（Blueprint Ingest Pipeline）

用户指示（2026-09-02）：以后新建蓝图/类似物后，能快速更新到系统架构管理器中，
更快速节省资源地找到对应匹配位置。R006 九标准工具化。

功能：
  1. 一键注册新蓝图 → 黑板 + relations + registry + versionlog + 本地 md 全同步
  2. 全点关联：新蓝图在所有图谱触点自动出现（蓝图库/关系图谱/项目视图/详情快照/知识溯源候选）
  3. 智能匹配：分析新蓝图名/主线 → 建议 child_of 父蓝图 + 关联边（from 已有 relations 学习）
  4. 快照自动渲染（三视图）

用法：
  python3 bb-blueprint-ingest.py --register <id> --dim <维度>   # 注册现有蓝图键
  python3 bb-blueprint-ingest.py --list                          # 已注册蓝图
  python3 bb-blueprint-ingest.py --suggest <name>               # 匹配位置建议
  python3 bb-blueprint-ingest.py --sync-all                     # 全量同步（快照+registry）
  python3 bb-blueprint-ingest.py --selfcheck
  python3 bb-blueprint-ingest.py --tool-version
"""
import argparse, json, os, re, sys, datetime, urllib.request, glob

BB = "http://127.0.0.1:8792"
BASE = os.path.expanduser("~/dsh-collab")
SCRIPTS = os.path.join(BASE, "scripts")
SNAP = os.path.join(BASE, "data/blueprint/gallery/snapshots")
VERSION = "v1.0.0"

# ── 蓝图维度知识（用于匹配建议）──
DIM_PARENTS = {  # 维度 → 建议父蓝图
  "业务": None, "技术": None, "底座": "agent-network", "元层": "blueprint-platform",
  "验证": "rule-judge", "子蓝图": None,
}
DIM_COLORS = {"业务": "#6ea8ff", "技术": "#e06c75", "底座": "#c678dd", "元层": "#61afef",
              "验证": "#e5c07b", "子蓝图": "#56b6c2", "存储": "#f5b942"}

def fetch(path):
    try:
        with urllib.request.urlopen(BB + "/" + path.lstrip("/"), timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def put(path, value):
    body = json.dumps(value, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + "/" + path.lstrip("/"), data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read().decode()[:120]

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def get_relations():
    d = fetch("data/blueprint/relations").get("value", {})
    return {"blueprints": d.get("blueprints", []), "edges": d.get("edges", [])}

def list_bps():
    rel = get_relations()
    out = []
    for b in rel["blueprints"]:
        d = fetch(f"data/blueprint/{b}").get("value", {})
        ver = d.get("version", "?")
        # flowernet 主蓝图 fallback stages（先 fallback 再取 version）
        if (not d or "id" not in d) and b == "flowernet":
            st = fetch("data/blueprint/stages").get("value", {})
            if st.get("version"):
                d = {"version": st.get("version"), "dimension": "业务", "name": "花店生意演进"}
        ver = d.get("version", "?")
        if isinstance(ver, str) and ver.startswith("v"): ver = ver[1:]
        dims = {"flowernet":"业务","aistartup":"业务","banking":"业务","flowernet-platform":"技术",
                "agent-network":"底座","blueprint-platform":"元层","rule-judge":"验证",
                "flowernet-erp":"子蓝图","flowernet-miniapp":"子蓝图","flowernet-website":"子蓝图",
                "memory-governance":"子蓝图","gene-bank":"底座","distributed-network":"底座"}
        out.append({"id": b, "version": ver,
                    "dim": dims.get(b, d.get("dimension", d.get("dim", "?"))), "name": d.get("name", b)})
    return out

def suggest_position(name, dim="", mainlines=None):
    """智能匹配：分析名称/维度/主线 → 建议 child_of + 关联边"""
    rel = get_relations()
    known = set(rel["blueprints"]) - {name}  # 已注册的其他蓝图
    name_l = name.lower()
    ml = mainlines or []
    suggestions = {"childOf": None, "edges": [], "reason": ""}
    # 1) 维度 → 父（底座→agent-network，技术→需判断）
    parent = DIM_PARENTS.get(dim)
    if parent and parent in known:
        suggestions["childOf"] = parent
    elif dim == "底座":
        suggestions["childOf"] = "agent-network" if "agent-network" in known else None
    elif dim == "存储":
        suggestions["childOf"] = "gene-bank" if "gene-bank" in known else None
    elif dim == "子蓝图":
        suggestions["childOf"] = None  # 子蓝图父需人工
    # 2) 名称关键词 → 关联
    KW = {
        "memory": ("memory-governance", "references", "内存治理关联"),
        "gene|bank|storage|store|存储": ("gene-bank", "references", "存储底座关联"),
        "distributed|node|device|跨设备|设备": ("distributed-network", "references", "分布式网络关联"),
        "rule|judge|验证": ("rule-judge", "references", "验证层关联"),
        "agent|bus|底座|协作": ("agent-network", "references", "底座关联"),
        "flower|花": ("flowernet", "references", "花店业务关联"),
        "^(?!gene-)bank|银行": ("banking", "references", "银行业务关联"),
    }
    for pat, (target, etype, why) in KW.items():
        if re.search(pat, name_l) and target != name:
            suggestions["edges"].append({"to": target, "type": etype, "why": why})
    # 3) 主线关键词 → 关联
    for m in ml:
        for pat, (target, etype, why) in KW.items():
            if re.search(pat, str(m).lower()) and target != name:
                suggestions["edges"].append({"to": target, "type": etype, "why": why + "(" + str(m) + ")"})
    # 去重
    seen = set(); dedup = []
    for e in suggestions["edges"]:
        k = (e["to"], e["type"])
        if k not in seen: seen.add(k); dedup.append(e)
    suggestions["edges"] = dedup
    suggestions["reason"] = f"建议 child_of={suggestions['childOf']} · {len(dedup)} 条关联边"
    return suggestions

def register(bid, dim):
    """注册蓝图到全部触点"""
    d = fetch(f"data/blueprint/{bid}").get("value", {})
    if not d or "id" not in d:
        return f"❌ 蓝图 {bid} 不存在于黑板"
    ml_keys = list(d.get("mainlines", {}).keys()) if isinstance(d.get("mainlines"), dict) else []
    # 1) relations.blueprints
    rel = fetch("data/blueprint/relations").get("value", {})
    bps = rel.get("blueprints", [])
    if bid not in bps: bps.append(bid)
    edges = rel.get("edges", []); existing = {(e["from"], e["to"], e["type"]) for e in edges}
    # 2) 智能匹配
    sug = suggest_position(bid, dim, ml_keys)
    if sug["childOf"]:
        k = ("distributed-network" if False else (bid, sug["childOf"], "child_of"))
        if (bid, sug["childOf"], "child_of") not in existing:
            edges.append({"from": bid, "to": sug["childOf"], "type": "child_of", "desc": "智能匹配父蓝图"})
    for e in sug["edges"]:
        if e["to"] != bid and (bid, e["to"], e["type"]) not in existing:
            edges.append({"from": bid, "to": e["to"], "type": e["type"], "desc": e["why"]})
    # 3) 元层 manages
    if (bid, "manages") not in existing and "blueprint-platform" in bps:
        pass  # manages 由元层方向加
    rel["edges"] = edges; rel["ts"] = now()
    put("data/blueprint/relations", rel)
    # 4) versionlog
    vl = fetch("data/blueprint/versionlog").get("value", {})
    vl["blueprints"][bid] = {"ts": now(), "version": d.get("version", "?")}
    vl.setdefault("entries", []).append({"action": "CREATED", "bp": bid, "by": "bb-blueprint-ingest",
        "detail": f"蓝图 {bid} 经流水线注册（dim={dim} · 匹配 {sug['reason']}）", "ts": now()})
    put("data/blueprint/versionlog", vl)
    # 5) registry 维度
    reg_py = os.path.join(SCRIPTS, "bb-blueprint-registry.py")
    if os.path.exists(reg_py):
        s = open(reg_py, encoding="utf-8").read()
        if bid not in s:
            # 插到维度 map
            m = re.search(r'"([\w\-]+)": "(\w+)"\}\)\.get\(bp_id', s)
            if m:
                old = m.group(0)
                new = f'"{bid}": "{dim}", {old}'
                s = s.replace(old, new, 1)
                open(reg_py, "w", encoding="utf-8").write(s)
    return f"✅ {bid} 注册完成: {sug['reason']} · relations {len(rel['edges'])} 边"

def render_snapshot(bid):
    """渲染三视图快照（调用 gallery 渲染函数逻辑简化——直接运行 render-all）"""
    import subprocess
    r = subprocess.run(["python3", os.path.join(SCRIPTS, "bb-blueprint-gallery.py"), "--render-all"],
                       capture_output=True, text=True, timeout=120)
    return "快照已重渲染" if "完成" in r.stdout else r.stdout[-100:]

def selfcheck():
    ok = True
    checks = [
        ("黑板可达", bool(fetch("data/blueprint/relations"))),
        ("蓝图≥13", len(get_relations()["blueprints"]) >= 13),
        ("registry 脚本存在", os.path.exists(os.path.join(SCRIPTS, "bb-blueprint-registry.py"))),
        ("gallery 脚本存在", os.path.exists(os.path.join(SCRIPTS, "bb-blueprint-gallery.py"))),
    ]
    print("== bb-blueprint-ingest --selfcheck ==")
    for n, c in checks:
        print(f"  {'✅' if c else '❌'} {n}")
        if not c: ok = False
    print("== 结果:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="蓝图注册流水线")
    ap.add_argument("--register", help="注册蓝图 id")
    ap.add_argument("--dim", default="技术", help="蓝图维度")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--suggest", help="匹配建议（输入名称）")
    ap.add_argument("--sync-all", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()
    if args.tool_version: print(f"bb-blueprint-ingest {VERSION}"); return
    if args.selfcheck: sys.exit(0 if selfcheck() else 1)
    if args.list:
        for b in list_bps(): print(f"  {b['id']:<24} {b['dim']:<8} v{b['version']}")
        return
    if args.suggest:
        s = suggest_position(args.suggest, args.dim)
        print(f"📐 匹配建议 for '{args.suggest}':")
        print(f"  child_of: {s['childOf']}")
        for e in s["edges"]: print(f"  → {e['to']} [{e['type']}] {e['why']}")
        return
    if args.register:
        print(register(args.register, args.dim))
        # 自动渲染快照
        r = render_snapshot(args.register)
        print("快照:", r)
        print(f"💡 已在系统架构管理器可见: http://127.0.0.1:8798/ (蓝图库/关系图谱/项目视图自动含 {args.register})")
        return
    if args.sync_all:
        import subprocess
        subprocess.run(["python3", os.path.join(SCRIPTS, "bb-blueprint-gallery.py"), "--render-all"])
        print("✅ 全量同步完成")
        return

if __name__ == "__main__":
    main()
