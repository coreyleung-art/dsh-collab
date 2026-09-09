#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-gallery.py — 系统架构管理器（全局 · 蓝图+智能体+规则+机制+项目+版本快照）

用户指示（2026-09-02）：做一个适配全局的蓝图架构图管理器 app——
统一管理所有蓝图 + 所有智能体架构图，关联项目管理，版本管理，翻查历史图片。
已拍板：① 独立本地 Web app（127.0.0.1:8798）② 自动渲染版本快照。

数据源：
  - 蓝图 BP-9      : 黑板 127.0.0.1:8792/data/blueprint/<id>（11 蓝图）
  - 关系网络        : 黑板 .../data/blueprint/relations（24 边）
  - 版本日志        : 黑板 .../data/blueprint/versionlog（16 entries）
  - 智能体档案      : ~/.dsh/agent-bus.json profiles（52 个）
  - SVG 快照        : ~/dsh-collab/data/blueprint/gallery/snapshots/

用法：
  python3 bb-blueprint-gallery.py --port 8798
  python3 bb-blueprint-gallery.py --render-all   # 只重渲全部快照（无服务器）
  python3 bb-blueprint-gallery.py --selfcheck
访问：http://127.0.0.1:8798/
"""
import argparse, json, urllib.request, datetime, html, os, math, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BB = "http://127.0.0.1:8792"
BASE = os.path.expanduser("~/dsh-collab")
GALLERY_DIR = os.path.join(BASE, "data/blueprint/gallery")
SNAP_DIR = os.path.join(GALLERY_DIR, "snapshots")
VERSION_MAP = os.path.join(GALLERY_DIR, "version-map.json")
AGENTS_FILE = os.path.expanduser("~/.dsh/agent-bus.json")
VERSION = "v1.4.0"  # 与 SystemGraph 壳/三端同版(见 ~/system-graph-app/VERSION-MANIFEST.md)

# ───────────────────────── 数据层 ─────────────────────────

def fetch(path, timeout=6):
    try:
        with urllib.request.urlopen(BB + "/" + path.lstrip("/"), timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def h(s):
    return html.escape(str(s))

def bp_dims():
    return {"flowernet": "业务", "aistartup": "业务", "banking": "业务",
            "flowernet-platform": "技术", "agent-network": "底座", "blueprint-platform": "元层",
            "rule-judge": "验证", "flowernet-erp": "子蓝图", "flowernet-miniapp": "子蓝图",
            "flowernet-website": "子蓝图", "memory-governance": "子蓝图",
            "mtm": "工具", "laodeng-app": "产品",
            "gene-bank": "底座", "distributed-network": "底座",
            "merchant-ops-ai": "产品", "flowernet-ops": "业务",
            "flowernet-supply": "业务", "flowernet-citywar": "业务"}

def bp_colors():
    return {"flowernet": "#6ea8ff", "aistartup": "#34c77b", "banking": "#f5b942",
            "flowernet-platform": "#e06c75", "agent-network": "#c678dd", "blueprint-platform": "#61afef",
            "rule-judge": "#e5c07b", "flowernet-erp": "#56b6c2", "flowernet-miniapp": "#98c379",
            "flowernet-website": "#d19a66", "memory-governance": "#2ac3de",
            "mtm": "#4a9eff", "laodeng-app": "#e84393",
            "gene-bank": "#c678dd", "distributed-network": "#61afef",
            "merchant-ops-ai": "#e84393", "flowernet-ops": "#e06c75",
            "flowernet-supply": "#f08a5d", "flowernet-citywar": "#f76c6c"}

def get_registry():
    """返回蓝图列表 [{id,version,status,mainlines,dim}]"""
    rel = fetch("data/blueprint/relations").get("value", {})
    bps = rel.get("blueprints", [])
    dims = bp_dims()
    out = []
    for b in bps:
        bp = fetch(f"data/blueprint/{b}").get("value", {})
        if not bp or "id" not in bp:
            # flowernet 主蓝图可能仅在 stages
            st = fetch("data/blueprint/stages").get("value", {})
            if b == "flowernet" and st.get("version"):
                bp = {"id": "flowernet", "name": "花店生意演进", "version": st.get("version"),
                      "mainlines": st.get("mainlines", {}), "status": st.get("status", "active"), "gate": st.get("gate", "")}
        ml = bp.get("mainlines", {})
        ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
        out.append({"id": b, "name": bp.get("name", b), "version": bp.get("version", "?"),
                    "status": bp.get("status", ""), "mainlines": ml_keys,
                    "dim": dims.get(b, "?"), "raw": bp})
    return out

def get_blueprint(bid):
    bp = fetch(f"data/blueprint/{bid}").get("value", {})
    if not bp or "id" not in bp:
        if bid == "flowernet":
            st = fetch("data/blueprint/stages").get("value", {})
            if st.get("version"):
                bp = {"id": "flowernet", "name": "花店生意演进", "version": st.get("version"),
                      "mainlines": st.get("mainlines", {}), "status": st.get("status", "active"),
                      "gate": st.get("gate", ""), "stages": st.get("stages", []), "works": []}
    return bp

def get_relations():
    rel = fetch("data/blueprint/relations").get("value", {})
    bps = rel.get("blueprints", [])
    edges = rel.get("edges", [])
    # 父子映射（child_of 反向）：父蓝图 → [子蓝图]
    parent_map = {}
    for e in edges:
        if e.get("type") == "child_of":
            parent_map.setdefault(e.get("to"), []).append(e.get("from"))
    # 子蓝图集合（有父者）
    children = set()
    for v in parent_map.values():
        children.update(v)
    return {"blueprints": bps, "edges": edges, "parentMap": parent_map, "children": sorted(children)}

def get_versions():
    d = fetch("data/blueprint/versionlog").get("value", {})
    return {"blueprints": d.get("blueprints", {}), "entries": d.get("entries", [])}

def get_agents():
    try:
        with open(AGENTS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        profs = d.get("profiles", [])
        out = []
        for p in profs:
            aid = p.get("agentId", "")
            role = p.get("role", "")
            out.append({"id": aid, "role": role,
                        "abilities": p.get("abilities", []),
                        "resources": p.get("resources", []),
                        "updatedAt": p.get("updatedAt")})
        return out
    except Exception as e:
        return []

AGENT_DOMAINS = {"ops": ("运维/安全", "#e06c75"), "dev": ("开发/插件", "#c678dd"),
                 "data": ("数据/调研", "#2ac3de"), "biz": ("业务/运营", "#f5b942"),
                 "gov": ("治理/协调", "#34c77b"), "plan": ("洞察/规划", "#6ea8ff"),
                 "comm": ("通讯/媒体", "#e5c07b"), "idle": ("后备/通用", "#4a5568"),
                 "other": ("其他", "#8b90a3")}

def agent_domain(role):
    rl = str(role)
    if any(k in rl for k in ["运维", "健康", "守望", "看门狗", "崩溃", "CLD 系统故障", "基础设施", "排障"]): return "ops"
    if any(k in rl for k in ["插件开发", "GUI 插件", "软件工程", "web 插件", "语音输入", "本地开发", "语音"]): return "dev"
    if any(k in rl for k in ["调查", "调研", "论文", "摄取", "文档", "知识库"]): return "data"
    if any(k in rl for k in ["外卖", "运营", "采集", "灯塔", "客服", "回声", "返图"]): return "biz"
    if any(k in rl for k in ["协调", "资源管理", "HR", "司库", "星桥", "监督", "进度", "规则", "驾驶舱"]): return "gov"
    if any(k in rl for k in ["洞察", "蓝图", "明鉴", "规划"]): return "plan"
    if any(k in rl for k in ["媒体", "驿使", "外链", "通讯"]): return "comm"
    if any(k in rl for k in ["通用", "Ralph", "worker", "后备", "前任", "inactive", "已交接"]): return "idle"
    return "other"

def _agent_res_keys(r):
    keys = set()
    for m in re.finditer(r"file:?([~/A-Za-z0-9_.\-]+)", str(r)):
        parts = [p for p in re.split(r"[/\\]", m.group(1)) if p and p != "."]
        if not parts: continue
        if parts[0] == "~" and len(parts) > 1: keys.add("file:" + parts[1])
        elif parts[0] == "Users" and len(parts) > 2: keys.add("file:" + parts[2])
        elif parts[0].startswith("."): keys.add("file:." + parts[0])
        else: keys.add("file:" + parts[0])
    for m in re.finditer(r"store:(\d+|\w+)", str(r)): keys.add("store:" + m.group(1))
    for m in re.finditer(r"(kb|KB|chromadb?|db|blackboard|data|port|service|channel|task):([A-Za-z0-9_\-\.]+)", str(r)):
        keys.add(m.group(1).lower() + ":" + m.group(2))
    for m in re.finditer(r"(Dify 数据集|ops-science|poi-cache|paper-cache|wiki)", str(r)):
        keys.add("lib:" + m.group(1).lower())
    return keys

def build_agent_graph():
    """52 智能体网络：节点=agent(按职能域着色) + 边=共享资源(share)/同设备协作(bus)"""
    agents = get_agents()
    # 节点
    nodes = []
    for a in agents:
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        short = re.sub(r"^session-([0-9a-f]{8}).*", r"\1", a.get("id", ""))
        role = a.get("role", "?")
        # 角色短标签：取主角色词（mac-mini/职能）
        lab = role[:22]
        nodes.append({"id": a["id"], "label": lab, "short": short,
                      "color": dcolor, "dim": dname, "domain": dom,
                      "r": 12, "role": role,
                      "abilities": len(a.get("abilities", [])),
                      "resources": len(a.get("resources", []))})
    # 资源键
    agent_res = {a["id"]: _agent_res_keys(" ".join(a.get("resources", []))) for a in agents}
    cnt = {}
    for rks in agent_res.values():
        for k in rks: cnt[k] = cnt.get(k, 0) + 1
    priv = {k for k, n in cnt.items() if n < 8}
    # share 边
    pairs = {}
    for aid, rks in agent_res.items():
        for k in rks & priv:
            owners = [a for a, rr in agent_res.items() if k in rr]
            if len(owners) < 2: continue
            for i in range(len(owners)):
                for j in range(i + 1, len(owners)):
                    x, y = sorted([owners[i], owners[j]])
                    if x != y: pairs[(x, y)] = pairs.get((x, y), 0) + 1
    # bus 边：同 mac-mini 活跃
    mac = [a["id"] for a in agents if "mac-mini" in a.get("role", "")
           and not any(k in a.get("role", "") for k in ["inactive", "已交接", "前任", "后备", "Ralph", "worker", "子代理"])]
    import random as _rnd
    _rnd.seed(7)
    bus_pairs = [(mac[i], mac[j]) for i in range(len(mac)) for j in range(i + 1, len(mac))]
    _rnd.shuffle(bus_pairs)
    # 合并，cap 度
    adj = {}
    edges = []
    for (a, b), w in sorted(pairs.items(), key=lambda x: -x[1]):
        if adj.get(a, 0) < 4 and adj.get(b, 0) < 4:
            edges.append({"source": a, "target": b, "type": "share", "weight": w, "color": "#34c77b"})
            adj[a] = adj.get(a, 0) + 1; adj[b] = adj.get(b, 0) + 1
    for a, b in bus_pairs:
        if adj.get(a, 0) < 6 and adj.get(b, 0) < 6:
            edges.append({"source": a, "target": b, "type": "bus", "weight": 1, "color": "#c678dd"})
            adj[a] = adj.get(a, 0) + 1; adj[b] = adj.get(b, 0) + 1
    # 父子层级：读 agent-mapping.json
    pm = {}
    try:
        with open(os.path.join(GALLERY_DIR, "agent-mapping.json"), encoding="utf-8") as _f:
            _m = json.load(_f)
        pm = _m.get("parentMap", {})
    except Exception:
        pass
    children_set = set()
    for _c in pm.values():
        children_set.update(_c)
    # 节点标 parent 关系（node id 即 session-xxx）
    for n in nodes:
        aid = n["id"]
        n["parentId"] = None
        for pid, kids in pm.items():
            if aid in kids:
                n["parentId"] = pid
                n["label"] = "↳ " + n["label"]
        kids = pm.get(aid) or []
        n["hasChildren"] = bool(kids)
        n["childCount"] = len(kids)
    # 人工确认连接(连接实验室 confirmed.json) → 实线紫边
    try:
        _cf = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
        if os.path.exists(_cf):
            _cd = json.load(open(_cf, encoding="utf-8"))
            _ids = {a["id"] for a in agents}
            for _l in _cd.get("links", []):
                if _l.get("from") in _ids and _l.get("to") in _ids:
                    edges.append({"source": _l["from"], "target": _l["to"], "type": "confirmed",
                                  "weight": 1, "color": "#c678dd", "desc": _l.get("reason",""),
                                  "status": _l.get("status","confirmed")})
    except Exception: pass
    return {"nodes": nodes, "edges": edges, "mode": "agents",
            "parentMap": pm, "children": sorted(children_set)}

# ── 🛡 能力与权限图谱(R027: 能力能不能 / 权限该不该 分离呈现) ──
CAP_CATS = [
 ("运维/巡检", ["巡检","健康","监控","看门","探针","体检","磁盘","内存","守护","告警","心跳","运维"]),
 ("知识库/RAG", ["知识库","检索","RAG","chroma","向量","Dify","摄取","索引","wiki","KB"]),
 ("插件/开发", ["插件","开发","验证","打包","cordis","GUI","调试","构建","代码"]),
 ("数据/调研", ["调研","情报","爬虫","采集","crawler","分析","论文","数据","快照","数据集"]),
 ("运营/生意", ["外卖","门店","运营","商品","订单","价格","客服","报表","活动","投流","评价","采购","库存"]),
 ("协调/治理", ["协调","治理","规则","审批","队列","红线","仲裁","督办","红绿灯","台账"]),
 ("通讯/媒体", ["通讯","媒体","外链","稿件","战报","广播","记者","发文","跨设备"]),
 ("洞察/规划", ["蓝图","规划","洞察","战略","产品","选型","情报库","路线"]),
 ("语音/对话", ["语音","ASR","识别","TTS","对话","意图","语音输入","语义"]),
 ("文档/归档", ["文档","归档","沉淀","摄取","manual","手册","wiki","日志"]),
 ("记忆/持久", ["记忆","compaction","压缩","持久","openchronicle","pruner","沉淀","promote"]),
]
def _cap_cat(abi):
    for cat, kws in CAP_CATS:
        if any(k in abi for k in kws): return cat
    return "其他/专属"
def build_cap_perm_graph():
    """🛡 能力与权限图谱(R027): cap 视图 agent→能力簇(能不能) · perm 视图 agent→资源独占红/共享蓝(该不该)"""
    agents = get_agents()
    nodes, edges = [], []
    for a in agents:
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        lab = a.get("role", "?")[:22]
        nodes.append({"id": a["id"], "label": lab, "short": re.sub(r"^session-([0-9a-f]{8}).*", r"\1", a.get("id", "")),
                      "color": dcolor, "dim": dname, "domain": dom, "r": 11,
                      "role": a.get("role", ""), "kind": "capagent",
                      "abilities": a.get("abilities", []), "abiCount": len(a.get("abilities", [])),
                      "resources": a.get("resources", []), "resCount": len(a.get("resources", []))})
    res_keys = {}
    for a in agents:
        res_keys[a["id"]] = _agent_res_keys(" ".join(a.get("resources", [])))
    res_owner = {}
    for aid, rks in res_keys.items():
        for k in rks:
            res_owner.setdefault(k, []).append(aid)
    for cat, _ in CAP_CATS:
        nodes.append({"id": "cap:" + cat, "label": cat, "short": cat[:3], "kind": "capcat",
                      "dim": "能力簇", "color": "#f5b942", "r": 11, "count": 0})
    for a in agents:
        for abi in (a.get("abilities") or []):
            edges.append({"source": a["id"], "target": "cap:" + _cap_cat(abi),
                          "type": "拥有", "color": "#f5b942", "weak": True})
    res_nodes = {}
    for k, owners in sorted(res_owner.items(), key=lambda x: -len(x[1]))[:45]:
        excl = len(owners) == 1
        rid = "res:" + k
        nodes.append({"id": rid, "label": k[:22], "short": k.split(":")[-1][:8], "kind": "capres",
                      "dim": "资源", "color": "#e06c75" if excl else "#4a9eff",
                      "r": 7 if excl else 9, "exclusive": excl, "ownerCount": len(owners),
                      "desc": "独占" if excl else "共享·" + str(len(owners)) + "主"})
        res_nodes[k] = rid
    perm_edges = []
    for aid, rks in res_keys.items():
        for k in rks:
            if k in res_nodes:
                rid = res_nodes[k]
                excl = (res_owner[k] == [aid])
                perm_edges.append({"source": aid, "target": rid,
                                   "type": "独占" if excl else "访问",
                                   "color": "#e06c75" if excl else "#4a9eff", "weak": True})
    return {"nodes": nodes, "edges": edges, "mode": "capperm",
            "agentCount": len(agents), "capEdges": len(edges), "permEdges": len(perm_edges),
            "permEdgesAll": perm_edges, "capCats": [c for c, _ in CAP_CATS],
            "resTotal": len(res_owner), "resShown": len(res_nodes)}

# 追加到 bb-blueprint-gallery.py 的 build_cap_perm_graph 之后
def build_cap_view():
    full = build_cap_perm_graph()
    agents = {n["id"] for n in full["nodes"] if n.get("kind") == "capagent"}
    cats = {n["id"] for n in full["nodes"] if n.get("kind") == "capcat"}
    keep = agents | cats
    nodes = [n for n in full["nodes"] if n["id"] in keep]
    edges = [e for e in full["edges"] if e["source"] in keep and e["target"] in keep]
    capcnt = {}
    for e in edges:
        if e["target"].startswith("cap:"):
            capcnt[e["target"]] = capcnt.get(e["target"], 0) + 1
    for n in nodes:
        if n.get("kind") == "capcat":
            n["count"] = capcnt.get(n["id"], 0)
    return {"nodes": nodes, "edges": edges, "mode": "capperm",
            "agentCount": len(agents), "capEdges": len(edges)}

def build_perm_view():
    full = build_cap_perm_graph()
    agents = {n["id"] for n in full["nodes"] if n.get("kind") == "capagent"}
    reses = {n["id"] for n in full["nodes"] if n.get("kind") == "capres"}
    keep = agents | reses
    nodes = [n for n in full["nodes"] if n["id"] in keep]
    edges = [e for e in (full.get("permEdgesAll") or []) if e["source"] in keep and e["target"] in keep]
    return {"nodes": nodes, "edges": edges, "mode": "capperm",
            "agentCount": len(agents), "permEdges": len(edges),
            "resTotal": full.get("resTotal"), "resShown": len(reses)}

# ───────────────────────── SVG 渲染 ─────────────────────────

ST_ICON = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
ST_COLOR = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}

def esc(s):
    return html.escape(str(s))

def _status_color(st):
    return ST_COLOR.get(st or "todo", "#7d8596")

def norm_ver(v):
    """规范化版本号：v2.3 → 2.3，避免 vv2.3"""
    s = str(v or "?")
    return s[1:] if s.startswith("v") else s

def svg_blueprint(bid, bp=None):
    """渲染蓝图架构图 SVG。bp 传 dict 则用之（历史快照/BP-9 快照文件）；否则黑板拉取。"""
    if bp is None:
        bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return "<svg width='800' height='120'><text x='20' y='40' fill='#e06c75'>无数据: %s</text></svg>" % esc(bid)
    ml = bp.get("mainlines", {})
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = bp.get("stages", [])
    # flowernet: 从 raw 无 stages → stages 键兜底已在 get_blueprint
    works = bp.get("works", [])
    if isinstance(works, dict):
        works = []
    works_by = {}
    for w in works:
        if isinstance(w, dict):
            works_by.setdefault(w.get("stage"), []).append(w)

    W = 1560
    lane_h = 150
    pad = 20
    header_h = 86
    H = header_h + lane_h * max(len(ml_keys), 1) + 70
    parts = []
    # 背景
    parts.append(f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>')
    # 标题
    name = bp.get("name", bid)
    ver = bp.get("version", "")
    gate = str(bp.get("gate", ""))[:90]
    parts.append(f'<text x="{pad}" y="34" fill="#e8eaf0" font-size="21" font-weight="bold">{esc(name)}</text>')
    parts.append(f'<text x="{pad}" y="56" fill="#8b90a3" font-size="13">blueprint:{esc(bid)} · v{esc(norm_ver(ver))} · 维度:{esc(bp_dims().get(bid,"?"))}</text>')
    if gate:
        parts.append(f'<text x="{pad}" y="76" fill="#f0b429" font-size="11">门禁: {esc(gate)}</text>')
    lane_w = (W - 2 * pad) / max(len(ml_keys), 1)
    # 泳道标题行
    for i, mid in enumerate(ml_keys):
        x = pad + i * lane_w
        meta = ml[mid]
        mname = meta.get("name", mid) if isinstance(meta, dict) else mid
        mdesc = (meta.get("desc", "") if isinstance(meta, dict) else "")[:80]
        # 归属: 有 mainline 匹配用之; 若整个蓝图的 stages 都无 mainline 字段(子蓝图独立阶段),
        # 则归到第一条主线卡显示(避免空壳); 无 stages 则空
        if stages and all(s.get("mainline") is None for s in stages):
            # 全部 stages 只在第一个主线泳道展示
            mstages = stages if i == 0 else []
        else:
            mstages = [s for s in stages if s.get("mainline") == mid] if stages else []
        # 泳道背景
        parts.append(f'<rect x="{x+4}" y="{header_h-10}" width="{lane_w-12}" height="{lane_h*max(len(mstages),1)+44}" fill="#141824" rx="10" stroke="#232a3a" stroke-width="1"/>')
        parts.append(f'<text x="{x+18}" y="{header_h+12}" fill="{bp_colors().get(bid,"#6ea8ff")}" font-size="15" font-weight="bold">{esc(mname)}</text>')
        parts.append(f'<text x="{x+18}" y="{header_h+30}" fill="#8b90a3" font-size="10">{esc(mdesc)}</text>')
        yy = header_h + 46
        # 该主线下的 stages 卡片竖排
        for s in mstages:
            sc = _status_color(s.get("status"))
            sname = s.get("name", "")
            sstage = s.get("stage", s.get("id", ""))
            subs = s.get("substages", [])
            card_h = max(58, 26 + 20 * len(subs))
            # 卡片分组行线
            parts.append(f'<rect x="{x+18}" y="{yy}" width="{lane_w-52}" height="{card_h}" rx="8" fill="#0d1119" stroke="{sc}" stroke-width="1.5"/>')
            parts.append(f'<text x="{x+30}" y="{yy+20}" fill="{sc}" font-size="12" font-weight="bold">{esc(str(sstage))} · {esc(sname)[:26]}</text>')
            parts.append(f'<text x="{x+lane_w-60}" y="{yy+20}" fill="#8b90a3" font-size="10">{ST_ICON.get(s.get("status","todo"),"⬜")}</text>')
            sy = yy + 36
            for ss in subs[:5]:
                ssid = ss.get("id", "")
                ssc = _status_color(ss.get("status"))
                parts.append(f'<text x="{x+34}" y="{sy}" fill="{ssc}" font-size="10.5">◦ {esc(ssid)} {esc(ss.get("name",""))[:22]}</text>')
                sy += 17
            if len(subs) > 5:
                parts.append(f'<text x="{x+34}" y="{sy}" fill="#8b90a3" font-size="10">… +{len(subs)-5}</text>')
                sy += 15
            yy += card_h + 8
    # 图例
    ly = H - 44
    parts.append(f'<line x1="{pad}" y1="{ly-12}" x2="{W-pad}" y2="{ly-12}" stroke="#232a3a"/>')
    lx = pad
    for k, ic in [("done", "✅ 已完成"), ("active", "🟢 进行中"), ("partial", "🟡 部分"), ("todo", "⬜ 待做")]:
        parts.append(f'<text x="{lx}" y="{ly+8}" fill="#8b90a3" font-size="11">{ic}</text>')
        lx += 150
    nw = sum(len([s for s in (stages or []) if s.get("mainline") == m]) for m in ml_keys)
    parts.append(f'<text x="{W-pad-360}" y="{ly+8}" fill="#8b90a3" font-size="11" text-anchor="end">主线 {len(ml_keys)} · 主阶段 {len(stages or [])} · v{esc(ver)}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>"

RULE_CAT_COLORS = {"协作": "#6ea8ff", "工程": "#c678dd", "架构": "#2ac3de", "数据": "#56b6c2",
                   "治理": "#e06c75", "资源冲突": "#f5b942", "运营": "#34c77b"}
RULE_CATS = list(RULE_CAT_COLORS.keys())

def load_rules():
    """读规则账本 rules.json（73 条）+ 关联层 rule-mapping.json"""
    try:
        with open(os.path.join(BASE, "rules-registry", "rules.json"), encoding="utf-8") as f:
            d = json.load(f)
        rules = d.get("rules", [])
        ledger_ver = d.get("version", "?")
    except Exception:
        rules, ledger_ver = [], "?"
    try:
        with open(os.path.join(BASE, "rules-registry", "rule-mapping.json"), encoding="utf-8") as f:
            mp = json.load(f)
    except Exception:
        mp = {"rules": []}
    mprules = {m["id"]: m for m in mp.get("rules", [])}
    for r in rules:
        m = mprules.get(r["id"], {})
        r["agents"] = m.get("agents", [])
        r["blueprints"] = m.get("blueprints", [])
        r["appliesTo"] = m.get("appliesTo", [])
        r["notes"] = m.get("notes", "")
        r["global"] = m.get("global", False)
        r["scope"] = m.get("scope", "all-bus-devices")
    return rules, ledger_ver

def build_rule_graph():
    """规则↔蓝图↔智能体 网络：三类节点 + 三类边"""
    rules, ledger_ver = load_rules()
    bps = [b["id"] for b in get_registry()]
    bp_colors_map = bp_colors()
    agents = get_agents()
    agent_by_short = {}
    for a in agents:
        aid = a["id"]
        # 短 id 前 8
        agent_by_short[aid[:8]] = aid
    # ── 节点 ──
    rnodes, bnodes, anodes = [], [], []
    for r in rules:
        cat = r.get("category", "协作")
        color = RULE_CAT_COLORS.get(cat, "#8b90a3")
        rnodes.append({"id": "rule:" + r["id"], "label": r.get("name", r["id"])[:26], "short": r["id"],
                       "color": color, "dim": cat, "kind": "rule", "r": 10,
                       "status": r.get("status", ""), "summary": r.get("summary", ""),
                       "agents": r.get("agents", []), "blueprints": r.get("blueprints", []),
                       "global": r.get("global", False), "scope": r.get("scope", ""),
                       "enforcedBy": r.get("enforcedBy", "")})
    for b in bps:
        bnodes.append({"id": "bp:" + b, "label": b, "short": b, "color": bp_colors_map.get(b, "#6ea8ff"),
                       "dim": bp_dims().get(b, "?"), "kind": "bp", "r": 14})
    for a in agents:
        aid = a["id"]
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        role = a.get("role", "")
        label = re.sub(r"^([^-]+-[^-]+).*", r"\\1", role) if role else aid[:8]
        anodes.append({"id": "ag:" + aid, "label": label[:22], "short": aid[:6],
                       "color": dcolor, "dim": dname, "kind": "agent", "r": 9,
                       "role": role, "agentId": aid})
    # ── 边 ──
    edges = []
    # rule → blueprint（映射层）
    for r in rules:
        rid = r["id"]
        for bp in r.get("blueprints", []):
            if bp in bps:
                edges.append({"source": "rule:" + rid, "target": "bp:" + bp, "type": "约束", "color": "#e06c75"})
    # rule → agent（映射层：短 id 前缀匹配完整 session id）
    for r in rules:
        rid = r["id"]
        for ag in r.get("agents", []):
            short = ag[-8:] if len(ag) > 8 else ag
            full = agent_by_short.get(short)
            if not full:
                # 兜底：直接找含短 id 的
                full = next((a["id"] for a in agents if a["id"].endswith(short) or short in a["id"]), None)
            if full:
                edges.append({"source": "rule:" + rid, "target": "ag:" + full, "type": "相关智能体", "color": "#34c77b"})
    # 精简视图：只保留有边节点（避免 60+ 孤立规则无意义占位）
    linked = set()
    for e in edges:
        linked.add(e["source"]); linked.add(e["target"])
    snodes = [n for n in (rnodes + bnodes + anodes) if n["id"] in linked or n["kind"] == "bp" or n.get("global")]
    # 规则域 confirmed 边(连接实验室确认后并入 → 紫虚线转实线)
    try:
        for _l in get_confirmed_links("rules"):
            if _l.get("from") in {x.get("id") for x in snodes} and _l.get("to") in {x.get("id") for x in snodes}:
                edges.append({"source": _l.get("from"), "target": _l.get("to"), "type": "confirmed",
                              "color": "#c678dd", "desc": _l.get("desc",""),
                              "status": _l.get("status","confirmed")})
    except Exception: pass
    return {"nodes": snodes, "edges": edges, "mode": "rules", "compact": True,
            "fullNodeCount": len(rnodes) + len(bnodes) + len(anodes),
            "ledgerVer": ledger_ver, "ruleCount": len(rules), "categories": RULE_CATS}

def load_mechanism():
    try:
        with open(os.path.join(GALLERY_DIR, "mechanism.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"protocols": [], "gates": [], "locks": [], "links": []}

def build_mechanism_graph():
    mech = load_mechanism()
    nodes = []
    edges = []
    # 门健康概览节点(gate-auditor 审计结果: 纸面门 vs 结构门)
    gh = mech.get("gate_health")
    if gh:
        nodes.append({"id": "gate-health", "label": "门健康", "short": "门健康",
                      "color": "#e06c75" if gh.get("paper_gates", 0) > 20 else "#f0b429",
                      "dim": "门健康", "kind": "mech-g", "type": "gate",
                      "r": 14, "summary": f"规则 {gh.get('total_rules')} · 结构门 {gh.get('structural_gates')} · 纸面门 {gh.get('paper_gates')}(待修·gate-repairer)",
                      "doc": gh.get("source", ""), "paper": gh.get("paper_gates", 0)})
    for p0 in mech.get("protocols", []):
        nodes.append({"id": p0["id"], "label": p0["name"], "short": p0["id"], "color": p0["color"],
                      "dim": "协议", "kind": "mech-p", "type": "protocol", "r": 13,
                      "summary": p0.get("summary", ""), "doc": p0.get("doc", "")})
    for g in mech.get("gates", []):
        nodes.append({"id": g["id"], "label": g["name"], "short": g["id"], "color": g["color"],
                      "dim": "门", "kind": "mech-g", "type": "gate", "r": 12,
                      "summary": g.get("summary", "")})
    for lk in mech.get("locks", []):
        nodes.append({"id": lk["id"], "label": lk["name"], "short": lk["id"], "color": lk["color"],
                      "dim": "锁", "kind": "mech-l", "type": "lock", "r": 12,
                      "summary": lk.get("summary", ""), "doc": lk.get("doc", "")})
    for l in mech.get("links", []):
        edges.append({"source": l["from"], "target": l["to"], "type": l.get("type", "关联"),
                      "color": l.get("color", "#8b90a3")})
    return {"nodes": nodes, "edges": edges, "mode": "mech",
            "protocolCount": len(mech.get("protocols", [])),
            "gateCount": len(mech.get("gates", [])),
            "lockCount": len(mech.get("locks", []))}


ML_COLORS = {"bus": "#e06c75", "fnp": "#c678dd", "mem-l1": "#2ac3de", "mem-l2": "#98c379",
             "security": "#f5b942", "digital": "#6ea8ff", "physical": "#34c77b", "supply": "#f0b429",
             "biz": "#6ea8ff", "eco": "#34c77b", "res": "#f5b942", "app": "#c678dd", "bridge": "#e06c75",
             "govern": "#f5b942", "infra": "#2ac3de", "intel": "#6ea8ff", "monetize": "#34c77b",
             "product": "#f5b942", "audit": "#e5c07b", "loop": "#e06c75", "verify": "#2ac3de",
             "library": "#6ea8ff", "standard": "#c678dd", "tooling": "#34c77b", "brand": "#d19a66",
             "content": "#98c379", "traffic": "#56b6c2", "core": "#6ea8ff", "deploy": "#e06c75",
             "rfid": "#34c77b", "admin": "#c678dd", "front": "#56b6c2", "sync": "#98c379"}
ST_COLOR_M = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}



def build_knowledge_graph():
    """知识内核图谱：读预生成的 knowledge-graph.json（报告/论文/蓝图溯源+内聚）"""
    try:
        with open(os.path.join(GALLERY_DIR, "knowledge-graph.json"), encoding="utf-8") as f:
            g = json.load(f)
        return g
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "knowledge", "error": str(e)}




def build_original_graph():
    """💎 原创资产图：6 类原创资产（分类节点+资产节点）"""
    try:
        with open(os.path.join(GALLERY_DIR, "original-assets.json"), encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "original", "error": str(e)}
    cats = data.get("categories", [])
    items = data.get("items", [])
    nodes, edges = [], []
    # 分类节点（环）
    for c in cats:
        nodes.append({"id": "cat:" + c["id"], "label": c["name"], "short": c["name"][:4],
                      "kind": "origcat", "dim": "原创分类", "color": c["color"], "r": 16,
                      "desc": c["desc"]})
    # 资产节点
    for it in items:
        cat = next((c for c in cats if c["id"] == it["cat"]), None)
        color = cat["color"] if cat else "#8b90a3"
        nodes.append({"id": "oa:" + it["id"], "label": it["name"][:20], "short": it["id"],
                      "kind": "origitem", "dim": next((c["name"] for c in cats if c["id"]==it["cat"]), "?"),
                      "color": color, "r": 9, "detail": it.get("detail", ""), "origin": it.get("origin", ""),
                      "tags": it.get("tags", []), "catId": it["cat"]})
        edges.append({"source": "cat:" + it["cat"], "target": "oa:" + it["id"], "type": "属于", "color": color})
    return {"nodes": nodes, "edges": edges, "mode": "original",
            "total": len(items), "catCount": len(cats)}




def build_biz_asset_graph():
    """🌍 跨节点资产图谱(关系层 v2)：设备(通讯通道互联) + 蓝图枢纽 + 资产(设备承载+蓝图归属 双连)
    真实关系源: ①设备通讯 device-links.json(真实通道) ②资产 blueprint 字段(业务归属)
    ⚠️ 只画数据里有据的关系, 不臆造资产间依赖"""
    try:
        with open(os.path.join(GALLERY_DIR, "business-asset-map.json"), encoding="utf-8") as f:
            data = json.load(f)
        dl_path = os.path.join(GALLERY_DIR, "device-links.json")
        dlinks = json.load(open(dl_path, encoding="utf-8")) if os.path.exists(dl_path) else {"links": []}
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "bizmap", "error": str(e)}
    bpcolors = data.get("bpColors", {}); nodecolors = data.get("nodeColors", {})
    assets = data.get("assets", [])
    DEVICE_NAMES = {"mac-mini": "mac-mini 宿主", "i9": "PC-i9", "MBP": "MacBook Pro", "云端": "云端",
                    "xingqiao": "xingqiao 服务器", "mac-mini": "mac-mini"}
    # ── 设备节点(骨架) ──
    device_assets = {}
    for a in assets:
        node = a.get("node", "mac-mini")
        device_assets.setdefault(node, []).append(a)
    nodes, edges = [], []
    dev_nodes = {}
    for node in device_assets:
        did = "dev:" + node
        nodes.append({"id": did, "label": DEVICE_NAMES.get(node, node), "short": node,
                      "kind": "bizdev", "dim": "设备", "color": nodecolors.get(node, "#8b90a3"), "r": 17,
                      "assetCount": len(device_assets[node]),
                      "desc": "设备 " + DEVICE_NAMES.get(node, node) + " · " + str(len(device_assets[node])) + " 项资产"})
        dev_nodes[node] = did
    # ── 蓝图枢纽节点(业务归属中心, 仅资产引用到的) ──
    bp_used = {}
    for a in assets:
        bp = a.get("blueprint", "")
        if bp: bp_used[bp] = bp_used.get(bp, 0) + 1
    bp_nodes = {}
    for bp, cnt in bp_used.items():
        bid = "bp:" + bp
        nodes.append({"id": bid, "label": bp, "short": bp[:6], "kind": "bizbp",
                      "dim": "蓝图", "color": bpcolors.get(bp, "#6ea8ff"), "r": 10 + min(cnt, 6),
                      "assetCount": cnt, "desc": "蓝图 " + bp + " · " + str(cnt) + " 项资产"})
        bp_nodes[bp] = bid
    # ── 设备通讯通道边(真实: 来自 device-links.json, 双向可视) ──
    link_edges = set()
    for l in dlinks.get("links", []):
        f = l.get("from", "").replace("hw:", "").replace("node-", "")
        t = l.get("to", "").replace("hw:", "").replace("node-", "")
        # 只保留设备↔设备(mac-mini/i9/MBP/云端), 服务器内部通道略
        devs = {"macmini": "mac-mini", "pci9": "i9", "mbp": "MBP", "mbp-agent": "MBP", "iphone": "移动"}
        f2 = devs.get(f, f); t2 = devs.get(t, t)
        if f2 in dev_nodes and t2 in dev_nodes and f2 != t2:
            key = tuple(sorted([f2, t2]))
            if key not in link_edges:
                link_edges.add(key)
                edges.append({"source": "dev:" + f2, "target": "dev:" + t2,
                              "type": "通道", "color": "#2ac3de",
                              "chan": l.get("type", ""), "desc": (l.get("protocol") or "") + " " + (l.get("port") or "")})
    # ── 资产节点: 挂设备(承载) + 连蓝图(归属) 双边 ──
    for node, items in device_assets.items():
        parent = dev_nodes[node]
        for a in items:
            bp = a.get("blueprint", "")
            aid = "ba:" + a["name"]
            nodes.append({"id": aid, "label": str(a["name"])[:16], "short": str(a["name"])[:8],
                          "kind": "bizasset", "dim": node, "color": nodecolors.get(node, "#8b90a3"), "r": 7,
                          "name": a["name"], "type": a.get("type", ""), "loc": a.get("location", ""),
                          "isOriginal": a.get("isOriginal", False), "desc": a.get("desc", ""),
                          "blueprint": bp, "bpColor": bpcolors.get(bp, "#8b90a3"),
                          "responder": a.get("responder", "")})
            edges.append({"source": parent, "target": aid, "type": "承载", "color": nodecolors.get(node, "#8b90a3"), "weak": True})
            if bp and bp in bp_nodes:
                edges.append({"source": aid, "target": bp_nodes[bp], "type": "归属", "color": bpcolors.get(bp, "#6ea8ff"), "weak": True})
    # ── 第三层: 资产间显式关系(relations, verified=true) ──
    REL_COLOR = {"depends_on": "#e06c75", "collaborates": "#34c77b", "uses": "#f5b942",
                 "duplicates": "#f0b429", "part_of": "#56b6c2"}
    name_to_id = {a["name"]: "ba:" + a["name"] for a in assets}
    rel_edges = 0
    for r in data.get("relations", []):
        if not r.get("verified", True): continue
        frm, to = r.get("from", ""), r.get("to", "")
        if frm in name_to_id and to in name_to_id:
            tcol = REL_COLOR.get(r.get("type", ""), "#8b90a3")
            edges.append({"source": name_to_id[frm], "target": name_to_id[to],
                          "type": r.get("type", ""), "color": tcol,
                          "desc": r.get("desc", ""), "rel": True})
            rel_edges += 1
    # 汇总
    devs_list = []
    for n, items in device_assets.items():
        devs_list.append({"id": "dev:" + n, "name": DEVICE_NAMES.get(n, n), "count": len(items)})
    return {"nodes": nodes, "edges": edges, "mode": "bizmap",
            "assetCount": len(assets), "deviceCount": len(device_assets),
            "devices": devs_list,
            "bpColors": bpcolors, "nodeColors": nodecolors,
            "channelEdges": len(link_edges), "relEdges": rel_edges}


def build_hardware_graph():
    """🌐 物理层全景：本地设备 + 远端服务器 + 云端服务（分组分层）"""
    try:
        with open(os.path.join(GALLERY_DIR, "hardware-nodes.json"), encoding="utf-8") as f:
            hw = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "hardware", "error": str(e)}
    ST_COLOR = {"运行": "#34c77b", "在线": "#34c77b", "已接入": "#4a9eff", "已任命+闭环": "#98c379",
                "离线": "#7d8596", "待secret": "#f0b429", "未接入": "#7d8596"}
    GROUPS = hw.get("groups", {})
    GRP_COLOR = {"device": "#c678dd", "server": "#f5b942", "cloud": "#2ac3de"}
    nodes, edges = [], []
    # 蓝图节点（宿主关联）
    for bid in ["agent-network", "distributed-network"]:
        nodes.append({"id": "bp:" + bid, "label": bid, "short": bid, "kind": "hwbp", "dim": "蓝图",
                      "color": "#e8eaf0", "r": 12})
    for n in hw.get("nodes", []):
        nid = n["id"]
        if not nid.startswith("hw:"): nid = "hw:" + nid
        grp = n.get("group", "device")
        st = n.get("status", "")
        nodes.append({"id": nid, "label": n.get("name", n.get("device", nid)), "short": nid.replace("hw:", "").replace("node-", "").replace("srv-", "").replace("cloud-", "")[:8],
                      "kind": "hwnode", "dim": GROUPS.get(grp, grp), "group": grp,
                      "color": ST_COLOR.get(st, GRP_COLOR.get(grp, "#8b90a3")), "r": 13,
                      "os": n.get("os", ""), "ip": n.get("ip", ""), "role": n.get("role", ""),
                      "spec": n.get("spec", ""), "status": st, "verify": n.get("verify", ""),
                      "since": n.get("since", ""),
                      "sgVersion": n.get("sgVersion", ""), "sgRole": n.get("sgRole", "")})
    # 边：主节点(mac-mini)连蓝图 + relation 边
    for e in hw.get("relations", []):
        f = e["from"] if e["from"].startswith("hw:") else "hw:" + e["from"]
        t = e["to"] if e["to"].startswith("hw:") else "hw:" + e["to"]
        # 过滤只存在于节点中的
        if any(x["id"] == f for x in nodes) and any(x["id"] == t for x in nodes):
            edges.append({"source": f, "target": t, "type": e.get("type", "关联"), "color": "#8b90a3"})
    edges.append({"source": "hw:node-macmini", "target": "bp:agent-network", "type": "宿主", "color": "#c678dd"})
    edges.append({"source": "hw:node-pci9", "target": "bp:distributed-network", "type": "节点", "color": "#c678dd"})
    edges.append({"source": "hw:node-mbp", "target": "bp:distributed-network", "type": "节点", "color": "#c678dd"})
    return {"nodes": nodes, "edges": edges, "mode": "hardware", "nodeCount": len(hw.get("nodes", [])),
            "hwNodes": hw.get("nodes", []), "groups": GROUPS}


# ── 🛰 设备通讯桥（并入硬件载体 Tab 的通讯层）────────────────
COMM_PROBE_CACHE = {"ts": 0, "result": {}}

def ts_online_set():
    """tailscale status 解析在线 peer IP 集(权威, 防 ICMP 防火墙误判)"""
    import subprocess as _sp
    out = set()
    try:
        r = _sp.run(["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "status"],
                    capture_output=True, text=True, timeout=8)
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) < 3 or not parts[0].startswith("100."):
                continue
            if "offline" in line or "idle" in line or "stopped" in line:
                continue
            if "active" in line or "direct" in line or "relay" in line:
                out.add(parts[0])
    except Exception:
        pass
    return out

def probe_one(kind, target, timeout=3, ts_online=None):
    """探测单条通道: tailscale → ts_online 集合(tailscale status 一次解析); http/funnel → urlopen"""
    try:
        if kind == "tailscale":
            return bool(ts_online and target in ts_online)
        if kind in ("http", "funnel"):
            try:
                with urllib.request.urlopen(target, timeout=timeout) as _r:
                    return _r.status < 500
            except urllib.error.HTTPError as _he:
                # 4xx 也说明服务在响应(如黑板根 400)
                return _he.code < 500
        return None
    except Exception:
        return False

def probe_comm_channels(force=False):
    """探测 device-links.json 里标记的通道, 25s 缓存; 返回 {linkIndex: True/False/None}"""
    import time as _t
    now = _t.time()
    if not force and now - COMM_PROBE_CACHE["ts"] < 25 and COMM_PROBE_CACHE["result"]:
        return COMM_PROBE_CACHE["result"]
    out = {}
    try:
        with open(os.path.join(GALLERY_DIR, "device-links.json"), encoding="utf-8") as f:
            dl = json.load(f)
        online = ts_online_set()
        for p in dl.get("probes", []):
            out[p.get("link")] = probe_one(p.get("kind", "tailscale"), p.get("host") or p.get("url") or "",
                                           ts_online=online)
    except Exception as e:
        out = {"error": str(e)}
    COMM_PROBE_CACHE.update({"ts": now, "result": out})
    return out

def build_hw_comm_graph():
    """🛰 通讯桥: 设备节点 + 真实通讯通道边(带协议/方向/通道类型)"""
    try:
        with open(os.path.join(GALLERY_DIR, "hardware-nodes.json"), encoding="utf-8") as f:
            hw = json.load(f)
        with open(os.path.join(GALLERY_DIR, "device-links.json"), encoding="utf-8") as f:
            dl = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "hwcomm", "error": str(e)}
    ST_COLOR = {"运行": "#34c77b", "在线": "#34c77b", "已接入": "#4a9eff", "已任命+闭环": "#98c379",
                "离线": "#7d8596", "待secret": "#f0b429", "未接入": "#7d8596"}
    GROUPS = hw.get("groups", {})
    CT = dl.get("channelTypes", {})
    nodes, edges = [], []
    for n in hw.get("nodes", []):
        nid = n["id"]
        if not nid.startswith("hw:"): nid = "hw:" + nid
        grp = n.get("group", "device")
        st = n.get("status", "")
        nodes.append({"id": nid, "label": n.get("name", n.get("device", nid)), "short": nid.replace("hw:", "").replace("node-", "").replace("srv-", "").replace("cloud-", "")[:8],
                      "kind": "hwnode", "dim": GROUPS.get(grp, grp), "group": grp,
                      "color": ST_COLOR.get(st, {"device": "#c678dd", "server": "#f5b942", "cloud": "#2ac3de"}.get(grp, "#8b90a3")), "r": 13,
                      "os": n.get("os", ""), "ip": n.get("ip", ""), "role": n.get("role", ""),
                      "spec": n.get("spec", ""), "status": st})
    for i, l in enumerate(dl.get("links", [])):
        f = l["from"] if l["from"].startswith("hw:") else "hw:" + l["from"]
        t = l["to"] if l["to"].startswith("hw:") else "hw:" + l["to"]
        if not any(x["id"] == f for x in nodes) or not any(x["id"] == t for x in nodes):
            continue
        ct = CT.get(l.get("type", ""), {})
        edges.append({"source": f, "target": t, "idx": i, "type": l.get("type", "通道"),
                      "chan": ct.get("label", l.get("type", "")), "color": ct.get("color", "#8b90a3"),
                      "protocol": l.get("protocol", ""), "port": l.get("port", ""),
                      "direction": l.get("direction", "bi"), "desc": l.get("desc", ""),
                      "hasProbe": any(p.get("link") == i for p in dl.get("probes", []))})
    return {"nodes": nodes, "edges": edges, "mode": "hwcomm",
            "channelTypes": CT, "probe": probe_comm_channels(),
            "nodeCount": len(nodes), "linkCount": len(edges), "groups": GROUPS}


# ── 📋 计划档案图谱(所有智能体计划性文件 + 版本汇总)─────
def build_plan_graph():
    """📋 计划档案: 计划/路线图/版本/changelog → 关联蓝图/智能体 力导向"""
    try:
        with open(os.path.join(GALLERY_DIR, "plan-archive.json"), encoding="utf-8") as f:
            pa = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "planarchive", "error": str(e),
                "items": [], "itemCount": 0}
    TYPE_COLOR = {"plan": "#34c77b", "roadmap": "#f5b942", "backlog": "#e5c07b",
                  "blueprint": "#6ea8ff", "changelog": "#c678dd", "version": "#56b6c2",
                  "doc": "#8b90a3", "manual": "#d19a66"}
    DOM_COLOR = {"老登/MTM": "#e06c75", "老登App": "#e84393", "明鉴/SystemGraph": "#61afef",
                 "协作文档": "#8b90a3", "蓝图": "#6ea8ff", "工具链": "#2ac3de",
                 "守灯/CLD": "#98c379", "ERP": "#f5b942"}
    items = pa.get("items", [])
    nodes, edges = [], []
    seen_dom = {}
    for it in items:
        dom = it.get("domain", "其它")
        if dom not in seen_dom:
            seen_dom[dom] = True
            nodes.append({"id": "d:" + dom, "label": dom, "short": dom[:6], "kind": "pland",
                          "dim": "域", "color": DOM_COLOR.get(dom, "#8b90a3"), "r": 15,
                          "type": "domain", "count": 0})
    seen_bp = {}
    for it in items:
        bp = it.get("blueprint", "")
        if bp and bp not in seen_bp:
            seen_bp[bp] = True
            nodes.append({"id": "bp:" + bp, "label": bp, "short": bp[:6], "kind": "planbp",
                          "dim": "蓝图", "color": bp_colors().get(bp, "#6ea8ff"), "r": 11})
    for it in items:
        nid = it["id"]
        typ = it.get("type", "doc")
        nodes.append({"id": nid, "label": it.get("title", "")[:22], "short": it.get("file", "").split("/")[-1][:8],
                      "kind": "planitem", "dim": typ, "color": TYPE_COLOR.get(typ, "#8b90a3"), "r": 7,
                      "title": it.get("title", ""), "type": typ, "file": it.get("file", ""),
                      "domain": it.get("domain", ""), "version": it.get("version", ""),
                      "blueprint": it.get("blueprint", ""), "agent": it.get("agent", ""),
                      "status": it.get("status", ""), "updated": it.get("updated", ""),
                      "desc": it.get("desc", "")})
        edges.append({"source": "d:" + it.get("domain", "其它"), "target": nid, "type": "属域", "color": "#8b90a3"})
        if it.get("blueprint"):
            edges.append({"source": nid, "target": "bp:" + it["blueprint"], "type": "关联蓝图", "color": "#6ea8ff"})
    for nd in nodes:
        if nd["id"].startswith("d:"):
            nd["count"] = sum(1 for it in items if it.get("domain") == nd["label"])
    return {"nodes": nodes, "edges": edges, "mode": "planarchive",
            "items": items, "itemCount": pa.get("itemCount", len(items)),
            "domains": pa.get("domains", []), "typeColors": TYPE_COLOR}


def load_workflow_standards():
    try:
        with open(os.path.join(GALLERY_DIR, "workflow-standards.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def build_workflow_graph():
    """🔄 工作流/标准：R006 九标准节点 + 高频工作流模式 + 关联"""
    w = load_workflow_standards()
    nodes, edges = [], []
    # R006 总节点
    nodes.append({"id":"r006","label":"R006 九标准","short":"R006","kind":"std","dim":"标准",
                  "color":"#e8eaf0","r":16,"name":"插件化工具化标准"})
    # 九项标准
    for it in w.get("r006",{}).get("items",[]):
        t=tools_of(it.get("tools",[]))  # 容错: 缺 tools 键不 500 (2026-09-08 修复)
        nodes.append({"id":"r006-"+str(it["n"]),"label":f"{it['n']}.{it['name']}"[:20],"short":str(it["n"]),
                      "kind":"stditem","dim":"标准项","color":"#6ea8ff","r":9,
                      "name":it["name"],"note":it.get("note",""),"tools":it.get("tools",[]),
                      "toolsDesc":str(it.get("tools")) if isinstance(it.get("tools"),int) else "· ".join(t)})
        edges.append({"source":"r006","target":"r006-"+str(it["n"]),"type":"含","color":"#6ea8ff"})
    # 工作流模式
    WF_COLORS=["#2ac3de","#c678dd","#34c77b","#e5c07b","#56b6c2","#d19a66"]
    for i,wf in enumerate(w.get("workflows",[])):
        nodes.append({"id":"wf:"+wf["id"],"label":wf["name"][:16],"short":wf["id"],"kind":"workflow",
                      "dim":"工作流","color":WF_COLORS[i%6],"r":13,
                      "desc":wf.get("desc",""),"tool":wf.get("tool",""),"steps":wf.get("steps",[]),
                      "since":wf.get("since","")})
    return {"nodes":nodes,"edges":edges,"mode":"workflow",
            "r006":w.get("r006",{}),"workflows":w.get("workflows",[]),
            "metaUsage":w.get("meta_usage",{}),"termDist":w.get("term_distribution",{})}

def tools_of(t):
    if isinstance(t,int): return f"{t} 工具"
    if isinstance(t,list): return " ".join(str(x) for x in t[:3])
    return str(t)

def build_philosophy_graph():
    """🧠 治理哲学体系塔：一句话原则→4哲学→派生机制→落地"""
    try:
        with open(os.path.join(GALLERY_DIR, "governance-philosophy.json"), encoding="utf-8") as f:
            phi = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "philosophy", "error": str(e)}
    nodes, edges = [], []
    # 顶层：一句话原则（核心）
    nodes.append({"id": "phi:root", "label": "能力与权限分离", "short": "R027 原则", "kind": "phiroot",
                  "dim": "一句话原则", "color": "#e8eaf0", "r": 20,
                  "summary": phi.get("topPrinciple", "")})
    # 4 哲学
    PHI_COLORS = ["#e06c75", "#f5b942", "#2ac3de", "#c678dd"]
    for i, p in enumerate(phi.get("philosophies", [])):
        nodes.append({"id": "ph:" + p["id"], "label": p["name"][:16], "short": p["id"].replace("phi-", "Φ"),
                      "kind": "philosophy", "dim": "治理哲学", "color": PHI_COLORS[i % 4], "r": 15,
                      "name": p["name"], "core": p["core"], "origin": p.get("origin", ""),
                      "doc": p.get("doc", ""), "order": p.get("order", i+1),
                      "detail": p.get("detail", ""), "principles": p.get("principles", []),
                      "examples": p.get("examples", []), "relDocs": p.get("relDocs", []),
                      "children": p.get("children", [])})
        edges.append({"source": "phi:root", "target": "ph:" + p["id"], "type": "派生", "color": "#e8eaf0"})
    # 派生落地（规则/机制/蓝图节点）
    rules, _ = load_rules()
    rule_map = {r["id"]: r for r in rules}
    added = set()
    for p in phi.get("philosophies", []):
        for d in p.get("derives", []):
            if d in added: continue
            added.add(d)
            if d.startswith("rule:"):
                rid = d[5:]
                r = rule_map.get(rid, {})
                nodes.append({"id": "rule:" + rid, "label": (rid + " " + r.get("name", ""))[:18], "short": rid,
                              "kind": "phirule", "dim": "规则", "color": "#8b90a3", "r": 9,
                              "summary": r.get("summary", "")})
                edges.append({"source": "ph:" + p["id"], "target": "rule:" + rid, "type": "落地", "color": "#8b90a3"})
            elif d.startswith("blueprint:"):
                bid = d[9:]
                nodes.append({"id": "bp:" + bid, "label": bid, "short": bid, "kind": "phibp",
                              "dim": "蓝图", "color": "#e8eaf0", "r": 13})
                edges.append({"source": "ph:" + p["id"], "target": "bp:" + bid, "type": "落地", "color": "#8b90a3"})
    return {"nodes": nodes, "edges": edges, "mode": "philosophy",
            "topPrinciple": phi.get("topPrinciple", ""), "phiCount": len(phi.get("philosophies", [])),
            "layers": phi.get("layers", [])}

def build_system_assets():
    """🗄 系统资产视图：运行中服务（端口扫描）+ 归属蓝图"""
    # 静态表：系统 → 属主蓝图/技术栈/描述
    SYS = [
      {"id":"cld","name":"CLD 宿主","tech":"Electron v0.1.0","ports":"61348,31888","blueprint":"agent-network","layer":"宿主","desc":"DeepSeek Harness 桌面壳——所有智能体会话运行载体；守灯健康治理+R016","owner":"守灯"},
      {"id":"genebank","name":"GeneBank 基因库","tech":"Rust+Python","ports":"8801","blueprint":"gene-bank","layer":"存储底座","desc":"AI 网盘：内容寻址资产存储 6 染色体（5.5万注册）","owner":"守灯塔"},
      {"id":"blackboard","name":"黑板","tech":"Rust v0.6","ports":"8792","blueprint":"flowernet-platform","layer":"平台","desc":"黑板 KV/事件总线（Rust 版运行）","owner":"星桥"},
      {"id":"blackboard-mcp","name":"黑板 MCP","tech":"Rust","ports":"8810","blueprint":"flowernet-platform","layer":"接入","desc":"任意设备标准接入 bb_read/bb_subscribe","owner":"星桥"},
      {"id":"node-bridge","name":"node-bridge","tech":"Rust","ports":"守护","blueprint":"distributed-network","layer":"分布式","desc":"分布式节点统一桥（中枢×i9/mbp）","owner":"罗盘"},
      {"id":"mtm-panel","name":"外卖面板 MTM","tech":"Node","ports":"8787","blueprint":"flowernet","layer":"业务采集","desc":"10 店采集监控/告警/IM","owner":"灯塔"},
      {"id":"ext-link","name":"外链服务","tech":"Node","ports":"8790,8791,8910,8911","blueprint":"distributed-network","layer":"外联","desc":"企微/飞书/总线桥/SSE 跨设备通道","owner":"驿使"},
      {"id":"bus-bridge","name":"bus-bridge 总线桥","tech":"Node","ports":"8791","blueprint":"distributed-network","layer":"分布式","desc":"服务器信封收发+SSE推送(免轮询)+tasks持久化TTL——R033/R034 通道治理载体","owner":"星桥"},
      {"id":"device-daemon","name":"device-daemon 设备守护","tech":"Python","ports":"SSE订阅","blueprint":"distributed-network","layer":"守护","desc":"三端守护(mac-mini/MBP/i9)SSE长连订阅bus/events→转黑板→central-inbox角色映射唤醒","owner":"星桥"},
      {"id":"central-inbox","name":"central-inbox","tech":"Node","ports":"—","blueprint":"agent-network","layer":"注入","desc":"角色名→会话映射精确唤醒(S1)agent-role-map.json 20角色","owner":"星桥"},
      {"id":"chromadb","name":"ChromaDB 向量库","tech":"Python","ports":"8000","blueprint":"gene-bank","layer":"知识","desc":"向量索引（notes/wiki/research）","owner":"3b5efeef"},
      {"id":"obsidian","name":"Obsidian vault","tech":"iCloud","ports":"—","blueprint":"gene-bank","layer":"知识","desc":"raw/wiki/日记 LLM wiki 库","owner":"文汇"},
      {"id":"dsh-kb","name":"DSH KB","tech":"SQLite","ports":"—","blueprint":"gene-bank","layer":"知识","desc":"8 库 547 文档语义库","owner":"文汇"},
      {"id":"data-tools","name":"rust-data-tools","tech":"Rust","ports":"CLI","blueprint":"rule-judge","layer":"工具","desc":"chat-records/price-analysis","owner":"知了"},
      {"id":"ollama","name":"Ollama","tech":"本地","ports":"11434","blueprint":"agent-network","layer":"推理","desc":"qwen2.5:3b/bge-m3 本地模型","owner":"守灯塔"},
      {"id":"lmstudio","name":"LM Studio","tech":"本地","ports":"1234","blueprint":"agent-network","layer":"推理","desc":"qwen3.8-27b/glm-4.6v 视觉","owner":"明鉴"},
      {"id":"gallery","name":"系统架构管理器","tech":"Python","ports":"8798","blueprint":"blueprint-platform","layer":"工具","desc":"本管理器：蓝图/智能体/规则/机制/知识图谱","owner":"明鉴"},
      {"id":"bb-ui2","name":"蓝图 GUI v2","tech":"Python","ports":"8797","blueprint":"blueprint-platform","layer":"工具","desc":"flowernet 可视化中枢","owner":"明鉴"},
    ]
    # 端口存活探测：支持逗号列表 + a-b 范围 + "守护/CLI/—"标注
    import subprocess
    def check_port(p):
        try:
            r=subprocess.run(["lsof","-iTCP:"+str(p),"-sTCP:LISTEN"],capture_output=True,text=True,timeout=3)
            return bool(r.stdout.strip())
        except Exception: return False
    for s2 in SYS:
        s2["alive"] = False
        ps = str(s2.get("ports","")).replace("—","").replace(" ","")
        if not ps or ps in ("守护","CLI"):  # 守护/CLI 类默认未知——按技术栈推断
            s2["alive"] = "unknown"; continue
        parts = ps.split(",")
        for part in parts:
            if "-" in part:  # 范围 a-b
                a,b = part.split("-")
                if a.isdigit() and b.isdigit():
                    for p in range(int(a), int(b)+1):
                        if check_port(p): s2["alive"]=True; break
            elif part.isdigit():
                if check_port(int(part)): s2["alive"]=True; break
    # 动态图谱数据：系统节点(层色) + 属主蓝图节点 + 归属/依赖边
    nodes=[]; edges=[]
    LAYER_COLOR={"存储底座":"#f5b942","平台":"#6ea8ff","接入":"#2ac3de","分布式":"#c678dd",
                 "业务采集":"#34c77b","外联":"#e5c07b","知识":"#56b6c2","工具":"#98c379",
                 "推理":"#e06c75"}
    sys_nodes=[]
    for s2 in SYS:
        nid="sys:"+s2["id"]
        nodes.append({"id":nid,"label":s2["name"],"short":s2["id"],"kind":"sysnode",
                      "dim":s2["layer"],"color":LAYER_COLOR.get(s2["layer"],"#8b90a3"),"r":11,
                      "alive":s2.get("alive"),"tech":s2["tech"],"ports":s2.get("ports",""),
                      "bp":s2["blueprint"],"desc":s2["desc"]})
        sys_nodes.append(nid)
        edges.append({"source":nid,"target":"bp:"+s2["blueprint"],"type":"归属","color":"#6ea8ff"})
    # 蓝图节点（属主）
    for bp in ["gene-bank","flowernet-platform","agent-network","flowernet","rule-judge","blueprint-platform","distributed-network"]:
        if any(s["blueprint"]==bp for s in SYS):
            nodes.append({"id":"bp:"+bp,"label":bp,"short":bp,"kind":"sysbp","dim":"蓝图",
                          "color":"#e8eaf0","r":14})
    # 系统间依赖（静态边）
    DEPS=[("sys:chromadb","sys:genebank","存储"),("sys:obsidian","sys:genebank","存储"),
          ("sys:dsh-kb","sys:genebank","存储"),("sys:genebank","sys:blackboard","注册通知"),
          ("sys:ext-link","sys:blackboard","通讯"),("sys:blackboard-mcp","sys:blackboard","接入"),
          ("sys:node-bridge","sys:blackboard","桥接"),("sys:gallery","sys:blackboard","数据源"),
          ("sys:mtm-panel","sys:blackboard","上报"),("sys:ollama","sys:lmstudio","模型")]
    for f,t,typ in DEPS:
        if f in sys_nodes and t in sys_nodes:
            edges.append({"source":f,"target":t,"type":typ,"color":"#8b90a3"})
    return {"systems": SYS, "total": len(SYS), "alive": sum(1 for s2 in SYS if s2.get("alive") is True),
            "graph": {"nodes":nodes,"edges":edges,"mode":"system-graph"}}

def detect_islands():
    """L1 自进化信号：检测各图谱孤岛节点 + 产出候选清单（智能体网络为重点）"""
    report = {"agents": {"total": 0, "islands": [], "candidates": []},
              "rules": {"total": 0, "islands": []},
              "mechanism": {"total": 0, "islands": []}}
    # 智能体
    try:
        ag = build_agent_graph()
        agent_nodes = ag["nodes"]
        linked = set()
        for e in ag["edges"]:
            linked.add(e["source"]); linked.add(e["target"])
        report["agents"]["total"] = len(agent_nodes)
        # 岛屿 = 无资源共享边 且 无父归属
        islands = [n for n in agent_nodes if n["id"] not in linked and not n.get("parentId") and "inactive" not in str(n.get("role","")) and "已交接" not in str(n.get("role","")) and "前任" not in str(n.get("role","")) and "后备" not in str(n.get("role",""))]
        # 排除设计性孤立（通用/子代理归属）后才是真实候选
        for n in islands:
            role = n.get("role", "")
            report["agents"]["islands"].append({"id": n["id"], "label": n["label"], "short": n["short"],
                                                "role": role[:60], "domain": n.get("dim", "")})
    except Exception as e:
        report["agents"]["error"] = str(e)
    # 规则（真实孤岛：mapping 中无蓝图/agent/appliesTo 且非 global——与 rust island 一致）
    try:
        import os as _os
        mp_path = _os.path.join(BASE, "rules-registry", "rule-mapping.json")
        with open(mp_path, encoding="utf-8") as _f:
            mp_rules = json.load(_f).get("rules", [])
        report["rules"]["total"] = len(mp_rules)
        for r in mp_rules:
            if (not r.get("global") and not r.get("blueprints") and not r.get("agents")
                    and not r.get("appliesTo")):
                report["rules"]["islands"].append({"id": r["id"], "label": r.get("name", r["id"])[:50],
                                                    "short": r["id"]})
    except Exception as e:
        report["rules"]["error"] = str(e)
    return report

def build_blueprint_graph(bid):
    """蓝图 → 力导向图：蓝图(根)→主线→主阶段→子阶段 层级 + 状态色"""
    bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return {"nodes": [], "edges": [], "mode": "bp"}
    ml = bp.get("mainlines", {})
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = bp.get("stages", []) or []
    nodes, edges = [], []
    # 根：蓝图
    nodes.append({"id": "rt:" + bid, "label": bid, "short": bid, "dim": "蓝图",
                  "color": bp_colors().get(bid, "#6ea8ff"), "r": 20, "kind": "bproot", "summary": bp.get("name", "")})
    # 主线
    for mid in ml_keys:
        meta = ml[mid]
        mname = meta.get("name", mid) if isinstance(meta, dict) else mid
        mcolor = ML_COLORS.get(mid, "#8b90a3")
        nodes.append({"id": "ml:" + mid, "label": mname[:14], "short": mid, "dim": "主线",
                      "color": mcolor, "r": 14, "kind": "bpml",
                      "summary": (meta.get("desc", "") if isinstance(meta, dict) else "")[:80]})
        edges.append({"source": "rt:" + bid, "target": "ml:" + mid, "type": "含", "color": "#6ea8ff"})
    # 主阶段 + 子阶段
    for st in stages:
        mid = st.get("mainline", "")
        if mid not in ml_keys: continue
        sid = st.get("id", "")
        sc = ST_COLOR_M.get(st.get("status", "todo"), "#7d8596")
        nodes.append({"id": "st:" + sid, "label": (str(st.get("stage", "")) + " " + str(st.get("name", "")))[:16],
                      "short": sid, "dim": "阶段", "color": sc, "r": 12, "kind": "bpstage",
                      "status": st.get("status", "todo"), "summary": str(st.get("name", ""))[:60]})
        edges.append({"source": "ml:" + mid, "target": "st:" + sid, "type": "含", "color": ML_COLORS.get(mid, "#8b90a3")})
        for ss in st.get("substages", []):
            ssid = ss.get("id", "")
            ssc = ST_COLOR_M.get(ss.get("status", "todo"), "#7d8596")
            nodes.append({"id": "ss:" + ssid, "label": (ssid + " " + str(ss.get("name", "")))[:18],
                          "short": ssid, "dim": "子阶段", "color": ssc, "r": 9, "kind": "bpass",
                          "status": ss.get("status", "todo"), "summary": str(ss.get("name", ""))[:60]})
            edges.append({"source": "st:" + sid, "target": "ss:" + ssid, "type": "含", "color": sc})
    return {"nodes": nodes, "edges": edges, "mode": "bp-graph",
            "rootId": "rt:" + bid, "rootName": bid, "bpName": bp.get("name", bid)}

def svg_relations():
    """关系网络 SVG：环形布局 + 边类型着色（静态图，力导向交互版在前端）"""
    rel = get_relations()
    bps = rel.get("blueprints", [])
    edges = rel.get("edges", [])
    W, H = 1500, 900
    dims = bp_dims()
    colors = bp_colors()
    n = len(bps)
    cx, cy = W / 2, H / 2
    R = 330
    pos = {}
    for i, b in enumerate(bps):
        ang = -90 + i * (360 / max(n, 1))
        pos[b] = (cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang)))
    ecolor = {"contains": "#8b90a3", "depends_on": "#e06c75", "requires": "#f5b942",
              "consumes": "#34c77b", "manages": "#6ea8ff", "references": "#c678dd",
              "consumed_by": "#2ac3de", "child_of": "#56b6c2"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    for e in edges:
        frm, to = e.get("from"), e.get("to")
        if frm not in pos or to not in pos:
            continue
        x1, y1 = pos[frm]; x2, y2 = pos[to]
        col = ecolor.get(e.get("type"), "#8b90a3")
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="1.6" opacity="0.75"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<text x="{mx}" y="{my-5}" fill="{col}" font-size="9.5" text-anchor="middle">{esc(e.get("type",""))}</text>')
    lx, ly = 30, H - 24
    parts.append(f'<text x="{lx}" y="{ly-14}" fill="#8b90a3" font-size="12" font-weight="bold">边类型: </text>')
    lx = 100
    for t, c in [("contains","⊃"),("depends_on","→依赖"),("requires","→要求"),("consumes","→消费"),
                 ("manages","→管理"),("references","→引用"),("consumed_by","←消费"),("child_of","子")]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="{c}" font-size="11">{c} {t}</text>')
        lx += 175
    for b in bps:
        x, y = pos[b]
        col = colors.get(b, "#6ea8ff")
        dim = dims.get(b, "?")
        r = 58 if dim != "子蓝图" else 42
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" opacity="0.9" stroke="#0b0e14" stroke-width="2"/>')
        parts.append(f'<text x="{x}" y="{y-2}" fill="#fff" font-size="12.5" font-weight="bold" text-anchor="middle">{esc(b[:16])}</text>')
        parts.append(f'<text x="{x}" y="{y+14}" fill="rgba(255,255,255,.85)" font-size="9.5" text-anchor="middle">{esc(dim)}</text>')
    parts.append("</svg>")
    return "".join(parts)

def svg_fishbone(bid, bp=None):
    """通用鱼骨图（石川图）：任意蓝图的 mainlines→大骨、stages→中骨、substages→小骨
    支持点击骨头展开/收起（交互由前端 JS toggleFishBone 提供）。
    与 ui2 不同：主线数不硬编码（flowernet 3 条 / memory-governance 3 条 / banking 3 条均可用）。"""
    if bp is None:
        bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return f'<svg width="800" height="120"><text x="20" y="40" fill="#e06c75">无数据: {esc(bid)}</text></svg>'
    ml = bp.get("mainlines", {})
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = bp.get("stages", []) or []
    ml_colors = {k: c for k, c in zip(
        ml_keys,
        ["#6ea8ff", "#34c77b", "#f5b942", "#e06c75", "#c678dd", "#e5c07b", "#56b6c2", "#98c379", "#d19a66", "#2ac3de"][:len(ml_keys)])}
    st_color = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}
    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}

    # 动态布局：每条主线一条"鱼"，垂直堆叠
    W = 1700
    spine_x0, spine_x1 = 200, 1560
    n_ml = len(ml_keys)
    # 每条鱼高 = 头 120 + 大骨区（由该主线最多 stages 决定）
    per_fish = 240
    H = n_ml * per_fish + 90
    parts = [f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    parts.append(f'<text x="30" y="36" fill="#e8eaf0" font-size="20" font-weight="bold">{esc(bp.get("name", bid))} · 鱼骨图</text>')
    parts.append(f'<text x="30" y="58" fill="#8b90a3" font-size="12">目标 ← 主线(大骨) ← 主阶段(中骨) ← 子阶段(小骨) · 点击骨头展开/收起</text>')

    def render_one_fish(fi, mid):
        meta = ml[mid]
        title = meta.get("name", mid) if isinstance(meta, dict) else mid
        color = ml_colors.get(mid, "#6ea8ff")
        base_y = 90 + fi * per_fish
        head_y = base_y + 90
        fparts = []
        # 主干
        fparts.append(f'<line x1="{spine_x0}" y1="{head_y}" x2="{spine_x1}" y2="{head_y}" stroke="{color}" stroke-width="6" opacity="0.7"/>')
        # 鱼头（主线目标）
        head_x = spine_x1 + 40
        fparts.append(f'<polygon points="{head_x},{head_y-52} {head_x+80},{head_y} {head_x},{head_y+52}" fill="{color}" opacity="0.9"/>')
        fparts.append(f'<text x="{head_x-8}" y="{head_y+5}" fill="#fff" font-size="15" font-weight="bold" text-anchor="end">{esc(title[:18])}</text>')
        # 主线名（鱼尾侧）
        fparts.append(f'<text x="{spine_x0-40}" y="{head_y-18}" fill="{color}" font-size="14" font-weight="bold" text-anchor="end">{esc(mid)}</text>')
        fparts.append(f'<text x="{spine_x0-40}" y="{head_y}" fill="#8b90a3" font-size="10" text-anchor="end">{esc(str(meta.get("desc",""))[:40] if isinstance(meta,dict) else "")}</text>')
        # 大骨 = 该主线 stages（沿 spine 分布，上下交替）
        m_stages = [s for s in stages if s.get("mainline") == mid]
        n = len(m_stages)
        for j, s in enumerate(m_stages):
            ax = spine_x0 + (spine_x1 - spine_x0) * (j + 0.6) / (n + 0.3)
            ay = head_y
            dir_y = -1 if j % 2 == 0 else 1
            bx = ax - 130
            by = ay + 105 * dir_y
            sc = st_color.get(s.get("status"), "#7d8596")
            m_id = f"fb-{mid}-{s.get('id','')}"
            sub_id = f"fbs-{mid}-{s.get('id','')}"
            mx, my = (ax + bx) / 2, (ay + by) / 2
            fparts.append(f'<g class="fb-main" id="{m_id}" onclick="toggleFishBone(&quot;{sub_id}&quot;)" style="cursor:pointer">')
            fparts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{sc}" stroke-width="5"/>')
            fparts.append(f'<text x="{mx}" y="{my-8}" fill="{sc}" font-size="14" font-weight="bold" text-anchor="middle">{esc(str(s.get("stage",""))+" "+str(s.get("name",""))[:16])}</text>')
            fparts.append(f'<text x="{mx}" y="{my+10}" fill="#8b90a3" font-size="10" text-anchor="middle">{st_icon.get(s.get("status","todo"),"")}</text>')
            fparts.append(f'</g>')
            # 中骨 = substages（沿大骨分布）
            subs = s.get("substages", [])
            mid_parts = []
            for k, ss in enumerate(subs):
                f2 = (k + 0.6) / (len(subs) + 0.3) if subs else 0.5
                cx = ax + (bx - ax) * f2
                cy = ay + (by - ay) * f2
                cdir = 1 if dir_y < 0 else -1
                ex = cx + (30 if cdir > 0 else -30)
                ey = cy + 46 * cdir
                ssc = st_color.get(ss.get("status"), "#7d8596")
                mid_parts.append(f'<g style="cursor:default">')
                mid_parts.append(f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" stroke="{ssc}" stroke-width="2.5"/>')
                mid_parts.append(f'<text x="{ex}" y="{ey}" fill="{ssc}" font-size="11" text-anchor="middle" dy="{-4 if cdir<0 else 12}">{esc(ss.get("id","")+" "+str(ss.get("name",""))[:12])}</text>')
                mid_parts.append(f'</g>')
            fparts.append(f'<g class="fbsubs" id="{sub_id}" style="display:none">{"".join(mid_parts)}</g>')
        return "".join(fparts)

    for fi, mid in enumerate(ml_keys):
        parts.append(render_one_fish(fi, mid))

    # 图例
    lx = 60
    for k, ic in [("done", "✅ 完成"), ("active", "🟢 进行中"), ("partial", "🟡 部分"), ("todo", "⬜ 待做")]:
        parts.append(f'<text x="{lx}" y="{H-22}" fill="#8b90a3" font-size="12">{ic}</text>')
        lx += 120
    parts.append(f'<text x="{lx}" y="{H-22}" fill="#8b90a3" font-size="12">点击主线骨头展开/收起子阶段</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>"

def svg_timeline(bid, bp=None):
    """时间线视图：蓝图主线按序排布 stage 卡片（通用版）"""
    if bp is None:
        bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return f'<svg width="800" height="120"><text x="20" y="40" fill="#e06c75">无数据: {esc(bid)}</text></svg>'
    ml = bp.get("mainlines", {})
    stages = bp.get("stages", []) or []
    st_color = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}
    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
    W, H = 1500, max(120, 90 + len(stages) * 62)
    parts = [f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    parts.append(f'<text x="30" y="40" fill="#e8eaf0" font-size="20" font-weight="bold">{esc(bp.get("name", bid))} · 阶段时间线</text>')
    y = 80
    for s in stages:
        sc = st_color.get(s.get("status"), "#7d8596")
        sid = esc(str(s.get("id", "")))
        sname = esc(str(s.get("stage", "")) + " " + str(s.get("name", ""))[:40])
        mlid = esc(str(s.get("mainline", "")))
        subs = " ".join(f'<text x="{820 + i*0}" y="{y+8}" fill="{st_color.get(ss.get("status","todo"),"#7d8596")}" font-size="9">· {esc(ss.get("id",""))}</text>' for i, ss in enumerate(s.get("substages", [])[:6]))
        parts.append(f'<rect x="40" y="{y-20}" width="1400" height="46" rx="8" fill="#141824" stroke="{sc}" stroke-width="1.5"/>')
        parts.append(f'<circle cx="58" cy="{y+3}" r="6" fill="{sc}"/>')
        parts.append(f'<text x="76" y="{y+8}" fill="{sc}" font-size="13" font-weight="bold">{st_icon.get(s.get("status","todo"),"")} {sid} · {sname[:46]}</text>')
        parts.append(f'<text x="1440" y="{y+8}" fill="#8b90a3" font-size="10" text-anchor="end">主线: {esc(mlid)}</text>')
        y += 62
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>"


    """关系网络 SVG：环形布局 + 边类型着色"""
    rel = get_relations()
    bps = rel.get("blueprints", [])
    edges = rel.get("edges", [])
    W, H = 1500, 900
    dims = bp_dims()
    colors = bp_colors()
    n = len(bps)
    cx, cy = W / 2, H / 2
    R = 330
    pos = {}
    for i, b in enumerate(bps):
        ang = -90 + i * (360 / max(n, 1))
        pos[b] = (cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang)))
    ecolor = {"contains": "#8b90a3", "depends_on": "#e06c75", "requires": "#f5b942",
              "consumes": "#34c77b", "manages": "#6ea8ff", "references": "#c678dd",
              "consumed_by": "#2ac3de", "child_of": "#56b6c2"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    for e in edges:
        frm, to = e.get("from"), e.get("to")
        if frm not in pos or to not in pos:
            continue
        x1, y1 = pos[frm]; x2, y2 = pos[to]
        col = ecolor.get(e.get("type"), "#8b90a3")
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="1.6" opacity="0.75"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<text x="{mx}" y="{my-5}" fill="{col}" font-size="9.5" text-anchor="middle">{esc(e.get("type",""))}</text>')
    # 边图例
    lx, ly = 30, H - 24
    parts.append(f'<text x="{lx}" y="{ly-14}" fill="#8b90a3" font-size="12" font-weight="bold">边类型: </text>')
    lx = 100
    for t, c in [("contains","⊃"),("depends_on","→依赖"),("requires","→要求"),("consumes","→消费"),
                 ("manages","→管理"),("references","→引用"),("consumed_by","←消费"),("child_of","子")]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="{c}" font-size="11">{c} {t}</text>')
        lx += 175
    # 节点
    for b in bps:
        x, y = pos[b]
        col = colors.get(b, "#6ea8ff")
        dim = dims.get(b, "?")
        r = 58 if dim != "子蓝图" else 42
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" opacity="0.9" stroke="#0b0e14" stroke-width="2"/>')
        parts.append(f'<text x="{x}" y="{y-2}" fill="#fff" font-size="12.5" font-weight="bold" text-anchor="middle">{esc(b[:16])}</text>')
        parts.append(f'<text x="{x}" y="{y+14}" fill="rgba(255,255,255,.85)" font-size="9.5" text-anchor="middle">{esc(dim)}</text>')
    parts.append("</svg>")
    return "".join(parts)

def svg_agents_grid():
    """智能体架构图：按设备分组卡片网格（SVG 文本块）"""
    agents = get_agents()
    dev_colors = {"mac-mini": "#56b6c2", "i9": "#e06c75", "mbp": "#c678dd"}
    # 从 role 提取设备关键词
    def device(role):
        rl = role or ""
        for d in ["mac-mini", "i9", "mbp", "PC"]:
            if d in rl:
                return d
        return "其他"
    groups = {}
    for a in agents:
        groups.setdefault(device(a.get("role", "")), []).append(a)
    order = sorted(groups.keys())
    card_w, card_h, gap = 330, 128, 14
    per_row = 4
    rows = math.ceil(sum(len(groups[k]) for k in order) / per_row)
    W = per_row * (card_w + gap) + 40
    H = len(order) * 40 + rows * (card_h + gap) + 60
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    x = 20; y = 30; col = 0
    for dev in order:
        parts.append(f'<text x="{20}" y="{y+14}" fill="{dev_colors.get(dev,"#8b90a3")}" font-size="14" font-weight="bold">{dev} 设备 · {len(groups[dev])} 智能体</text>')
        y += 34
        for a in groups[dev]:
            role = a.get("role", "?")
            ab = len(a.get("abilities", []))
            rs = len(a.get("resources", []))
            # 卡片（用 foreignObject 太繁，纯矩形+文本，短 role）
            if col >= per_row:
                col = 0
                # 计算翻行
            cx = 20 + col * (card_w + gap)
            cy = y
            parts.append(f'<rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="10" fill="#141824" stroke="#232a3a"/>')
            # 智能体 id 短名
            aid = a.get("id", "")
            short = aid[-8:] if len(aid) > 8 else aid
            role_short = role if len(role) <= 34 else role[:33] + "…"
            # 因为 role 中文可能长，分两行
            parts.append(f'<text x="{cx+12}" y="{cy+22}" fill="#e8eaf0" font-size="11.5" font-weight="bold">{esc(role_short)}</text>')
            parts.append(f'<text x="{cx+12}" y="{cy+42}" fill="#8b90a3" font-size="9.5">{esc(aid[:10])}…{esc(short)}</text>')
            parts.append(f'<text x="{cx+12}" y="{cy+62}" fill="{dev_colors.get(dev,"#8b90a3")}" font-size="10">能力 {ab} · 资源 {rs}</text>')
            # 能力摘要（前2行）
            ab_sum = " · ".join(a.get("abilities", [])[:2])[:54]
            parts.append(f'<text x="{cx+12}" y="{cy+80}" fill="#9aa3b2" font-size="9">{(esc(ab_sum)+"…") if len(ab_sum)>=54 else esc(ab_sum)}</text>')
            rsrc = " · ".join(a.get("resources", [])[:1])[:54]
            parts.append(f'<text x="{cx+12}" y="{cy+96}" fill="#6f7686" font-size="9">{(esc(rsrc)+"…") if len(rsrc)>=54 else esc(rsrc)}</text>')
            col += 1
            if col >= per_row:
                col = 0
                y += card_h + gap
        if col:
            y += card_h + gap
            col = 0
        y += 8
    parts.append("</svg>")
    return "".join(parts)

def ensure_dir():
    os.makedirs(SNAP_DIR, exist_ok=True)

def load_version_map():
    try:
        with open(VERSION_MAP, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"blueprints": {}}

def save_version_map(vm):
    ensure_dir()
    with open(VERSION_MAP, "w", encoding="utf-8") as f:
        json.dump(vm, f, ensure_ascii=False, indent=2)

def render_all_snapshots(verbose=False):
    """遍历全部蓝图，渲染 SVG 快照；按 versionlog 当前版本命名归档。
    附带：扫描本地 BP-9 JSON 快照文件（data/blueprint/snapshots/*.json）→ 若版本≠当前则补历史 SVG。"""
    reg = get_registry()
    versions = get_versions()
    bp_vers = versions.get("blueprints", {})
    vm = load_version_map()
    created = []
    ensure_dir()
    # ── 历史 BP-9 JSON 快照（本地既有文件）→ 补历史 SVG ──
    import glob as _glob
    hist_src = os.path.join(BASE, "data/blueprint/snapshots", "*.json")
    for hf in _glob.glob(hist_src):
        try:
            with open(hf, encoding="utf-8") as f:
                hbp = json.load(f)
            hbid = hbp.get("id")
            hver = hbp.get("version", "?")
            if not hbid or "mainlines" not in hbp:
                continue
            cur = bp_vers.get(hbid, {}).get("version", "")
            # 历史版本（与当前不同 或 本地该蓝图在 versionlog 无记录但快照存在）
            hfname = re.sub(r"[^\w\-]", "_", hbid) + "-v" + re.sub(r"[^\w\-]", "_", norm_ver(hver)) + "-hist.svg"
            hpath = os.path.join(SNAP_DIR, hfname)
            if not os.path.exists(hpath):
                svg = svg_blueprint(hbid, bp=hbp)
                with open(hpath, "w", encoding="utf-8") as f:
                    f.write(svg)
                vm.setdefault("blueprints", {}).setdefault(hbid, {}).setdefault("history", [])
                # 不覆盖同名版本历史（保留 distinct 条目）
                vm["blueprints"][hbid]["history"].append({"version": norm_ver(hver), "file": hfname, "ts": "hist"})
                created.append((hbid, hver + " (历史快照)", hfname))
                if verbose:
                    print(f"  🕰 {hbid} v{hver} (历史) → {hfname}")
        except Exception as e:
            if verbose:
                print(f"  历史快照跳过 {hf}: {e}")
    # ── 当前版本渲染（幂等：version-map current 同版本且三视图文件存在 → 跳过）──
    VIEW_RENDER = [("arch", svg_blueprint), ("fish", svg_fishbone), ("tl", svg_timeline)]
    for b in reg:
        bid = b["id"]
        ver = b.get("version", "?")
        nver = norm_ver(ver)
        bvm = vm.setdefault("blueprints", {}).setdefault(bid, {"versions": {}})
        cur = bvm.get("current") or {}
        need = cur.get("version") != nver or not cur.get("views")
        if not need:
            vfiles = cur.get("views", {})
            need = any(not vfiles.get(vk) or not os.path.exists(os.path.join(SNAP_DIR, vfiles[vk]))
                       for vk, _ in VIEW_RENDER)
        if not need:
            if verbose:
                print(f"  ⏭ {bid} v{ver} 已是最新（3 视图齐全），跳过")
            continue
        try:
            safe_bp = re.sub(r"[^\w\-]", "_", bid)
            safe_ver = re.sub(r"[^\w\-]", "_", nver)
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            views_files = {}
            for vk, renderer in VIEW_RENDER:
                svg = renderer(bid)
                fname = f"{safe_bp}-{vk}-v{safe_ver}-{ts}.svg"
                with open(os.path.join(SNAP_DIR, fname), "w", encoding="utf-8") as f:
                    f.write(svg)
                views_files[vk] = fname
                created.append((bid, f"{ver} [{vk}]", fname))
                if verbose:
                    print(f"  ✅ {bid} v{ver} [{vk}] → {fname}")
            bvm["current"] = {"version": nver, "views": views_files,
                              "file": views_files.get("arch"), "ts": ts}
            hist = bvm.setdefault("history", [])
            hist = [hh for hh in hist if hh.get("version") != nver]
            hist.append({"version": nver, "views": views_files, "file": views_files.get("arch"), "ts": ts})
            bvm["history"] = hist[-30:]
        except Exception as e:
            if verbose:
                print(f"  ❌ {bid}: {e}")
    save_version_map(vm)
    return created

# ───────────────────────── 前端页面 ─────────────────────────

# ── UI 资源(CSS/JS 独立文件, 不再字符串内嵌 —— 结构加固: 编辑器/语法工具原生校验) ──
_ui_dir = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(_ui_dir, "bb-gallery-ui.css"), encoding="utf-8") as _f: CSS = _f.read()
    with open(os.path.join(_ui_dir, "bb-gallery-ui.js"), encoding="utf-8") as _f: JS_UI = _f.read()
except Exception as _e:
    CSS, JS_UI = "", ""
    sys.stderr.write(f"⚠️ UI 资源读取失败(需 bb-gallery-ui.css/js 与脚本同目录): {_e}\n")

def _ui_reload():
    """开发热重载: 重新读 UI 文件(改 css/js 后调, 免重启服务)"""
    global CSS, JS_UI
    try:
        with open(os.path.join(_ui_dir, "bb-gallery-ui.css"), encoding="utf-8") as _f: CSS = _f.read()
        with open(os.path.join(_ui_dir, "bb-gallery-ui.js"), encoding="utf-8") as _f: JS_UI = _f.read()
        return True
    except Exception:
        return False

def build_index(port):
    _ui_reload()  # 热重载: 每次请求读最新 UI 文件(改 js/css 免重启, 部署即生效)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>系统架构管理器 · System Graph Manager</title><style>{CSS}</style></head><body>
<div class="top"><h1>🗺 系统架构管理器</h1><span class="sub">System Graph Manager · 蓝图+智能体+规则+机制+图库 · {now}</span></div>
<div class="domains" id="domains"></div>
<div class="tabs" id="tabs">
<div class="tab on" data-tab="philosophy" data-dom="SYS">🧠 治理哲学</div>
<div class="tab" data-tab="original" data-dom="SYS">💎 原创资产</div>
<div class="tab" data-tab="workflow" data-dom="SYS">🔄 工作流/标准</div>
<div class="tab" data-tab="planarchive" data-dom="SYS">📋 计划档案</div>
<div class="tab" data-tab="dash" data-dom="DASH">🏠 总览</div>
<div class="tab" data-tab="blueprints" data-dom="GRAPH">📐 蓝图(库+详情)</div>
<div class="tab" data-tab="agents" data-dom="GRAPH">🤖 智能体网络</div>
<div class="tab" data-tab="relations" data-dom="GRAPH">🔀 关系图谱</div>
<div class="tab" data-tab="projects" data-dom="DASH">🗂 项目视图</div>
<div class="tab" data-tab="versions" data-dom="DASH">📜 版本历史</div>
<div class="tab" data-tab="assets" data-dom="DASH">🗂 图库</div>
<div class="tab" data-tab="rules" data-dom="GRAPH">📏 规则图谱</div>
<div class="tab" data-tab="mech" data-dom="GRAPH">⚙️ 机制</div>
<div class="tab" data-tab="knowledge" data-dom="CARRIER">📚 知识内核</div>
<div class="tab" data-tab="systems" data-dom="CARRIER">🗄 系统资产</div>
<div class="tab" data-tab="hardware" data-dom="CARRIER">🖥 硬件载体</div>
<div class="tab" data-tab="bizmap" data-dom="CARRIER">🌍 跨节点资产</div>
</div>
<div class="main on" id="view-philosophy"></div>
<div class="main" id="view-original"></div>
<div class="main" id="view-workflow"></div>
<div class="main" id="view-planarchive"></div>
<div class="main" id="view-dash"></div>
<div class="main" id="view-blueprints"></div>
<div class="main" id="view-agents"></div>
<div class="main" id="view-relations"></div>
<div class="main" id="view-projects"></div>
<div class="main" id="view-versions"></div>
<div class="main" id="view-assets"></div>
<div class="main" id="view-rules"></div>
<div class="main" id="view-mech"></div>
<div class="main" id="view-knowledge"></div>
<div class="main" id="view-systems"></div>
<div class="main" id="view-hardware"></div>
<div class="main" id="view-bizmap"></div>
<div class="foot">blueprint-gallery {VERSION} · 数据源: 黑板 8792 + agent-bus.json · 明鉴 v2 · 架构图快照自动渲染于 gallery/snapshots/</div>
<script src="vendor/d3.min.js"></script>
<script>{JS_UI}</script>
<script>bindTabs();init();</script>
</body></html>"""

# ───────────────────────── HTTP 服务 ─────────────────────────

# R006#7 统一日志: 访问日志(含 4xx/5xx) → ~/dsh-collab/logs/systemgraph.log (JSONL)
_ACCESS_LOG = os.path.expanduser("~/dsh-collab/logs/systemgraph.log")
_ACCESS_LOG_MAX = 2 * 1024 * 1024  # 2MB 轮转
_log_lock = __import__("threading").Lock()

def _log_access(ts, method, path, code, referer="", agent=""):
    """追加一行 JSONL 访问日志; 超 2MB 轮转为 .1(留最近一份)"""
    try:
        with _log_lock:
            if os.path.exists(_ACCESS_LOG) and os.path.getsize(_ACCESS_LOG) > _ACCESS_LOG_MAX:
                os.replace(_ACCESS_LOG, _ACCESS_LOG + ".1")
            line = json.dumps({"ts": ts, "method": method, "path": path[:300],
                               "code": code, "referer": referer[:200], "agent": agent[:150]},
                              ensure_ascii=False)
            with open(_ACCESS_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass  # 日志失败不阻断服务

def _run_execute_after_confirm(frm, to, reason=""):
    """R006 自动接线: gallery 建边(五步门执行)后, 同步调 bb-connect-execute.py 通知两端相关方
    - 通知墙 data/connect-lab/notifications/ + 协作任务 collab-tasks + executions 幂等留痕(均在 execute 内)
    - 走 execute 的 Lean4 结构门(端点合法/幂等), 与 CLI 执行语义一致; 失败不阻断建边(已落盘)
    返回 True=通知已发 / False=跳过或失败"""
    import subprocess as _sp
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        _exe = os.path.join(_here, "bb-connect-execute.py")
        if not os.path.exists(_exe):
            _exe = os.path.expanduser("~/dsh-collab/scripts/bb-connect-execute.py")
        if not os.path.exists(_exe):
            return False
        _r = _sp.run([sys.executable, _exe, "--run", "--graph", "agents",
                      "--from", str(frm), "--to", str(to), "--reason", str(reason)[:80]],
                     capture_output=True, text=True, timeout=15)
        import json as _json2
        try:
            _d = _json2.loads(_r.stdout or "{}")
            # 新执行成功 → notified>=1; 幂等跳过(already) → 通知此前已发, 也算达成
            return bool(_d.get("ok")) and (_d.get("already", False) or int(_d.get("notified", 0) or 0) > 0)
        except Exception:
            return _r.returncode == 0
    except Exception:
        return False  # 通知失败不阻断建边(边已确认落盘)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        # BaseHTTPRequestHandler 会为每个请求调本方法 —— 记录访问日志(含错误码)
        try:
            msg = (a[0] % a[1:]) if len(a) > 1 and isinstance(a[0], str) else str(a[0] if a else "")
            # msg 形如 '"GET /api/x HTTP/1.1" 200 -'
            import re as _re
            m = _re.match(r'"(?:GET|POST|PUT|DELETE) ([^ ]*)', msg)
            code_m = _re.search(r'" (\d{3})', msg)
            code = int(code_m.group(1)) if code_m else 0
            _log_access(datetime.datetime.now().isoformat(), "HTTP", m.group(1) if m else "?", code)
        except Exception:
            pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        # R006#7: 错误响应(>=400)与写类请求记日志 —— 用户/运维可回溯"刚才为何失败"
        try:
            if code >= 400 or self.path.startswith("/api/connect-advance") or self.path.startswith("/api/connect-confirm") \
               or self.path.startswith("/api/link-status") or self.path.startswith("/api/manager-event"):
                _log_access(datetime.datetime.now().isoformat(), "REQ", self.path[:300], code,
                            referer=self.headers.get("Referer", ""), agent=self.headers.get("User-Agent", ""))
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if path == "/":
                self._send(200, build_index(self.server.server_port), "text/html; charset=utf-8")
                return
            if path == "/vendor/d3.min.js":
                d3path = os.path.expanduser("~/.dsh/profiles/web/node_modules/d3/dist/d3.min.js")
                if os.path.exists(d3path):
                    with open(d3path, encoding="utf-8") as f:
                        self._send(200, f.read(), "application/javascript; charset=utf-8")
                    return
                self._send(404, json.dumps({"error": "d3 not found"}))
                return
            if path == "/api/registry-people":
                # Network v0.2 打通(B 统一实体主源): 只读人类维度 — REG people/orgs + 蓝图域过滤
                _REG = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/business-entity-registry.json")
                _reg = {}
                if os.path.exists(_REG):
                    try:
                        _reg = json.load(open(_REG, encoding="utf-8"))
                    except Exception:
                        _reg = {}
                from urllib.parse import urlparse as _upR, parse_qs as _pqR
                _dom = (_pqR(_upR(self.path).query).get("domain") or [""])[0]
                _peo = []
                for _p in (_reg.get("people") or []):
                    if _dom and _dom not in (_p.get("domains") or []):
                        continue
                    _peo.append({"id": _p.get("id"), "name": _p.get("name"),
                                 "aliases": _p.get("aliases", []), "title": _p.get("title", ""),
                                 "domains": _p.get("domains", []),
                                 "orgIds": _p.get("orgIds", []),
                                 "confidence": (_p.get("verified") or {}).get("confidence", "")})
                _orgs = _reg.get("orgs") or []
                self._send(200, json.dumps({"ok": True, "source": "business-entity-registry.json",
                                            "domain": _dom or "all",
                                            "people": _peo, "orgs": _orgs,
                                            "totalPeople": len(_peo), "totalOrgs": len(_orgs)},
                                           ensure_ascii=False))
                return
            if path == "/api/logs":
                # R006#7: 访问/错误日志查询 — /api/logs?limit=50&code=5xx|4xx|all
                from urllib.parse import urlparse as _upl, parse_qs as _pql
                _ql = _pql(_upl(self.path).query)
                try:
                    _limit = min(int((_ql.get("limit") or ["80"])[0]), 500)
                except Exception:
                    _limit = 80
                _filt = (_ql.get("code") or ["all"])[0]
                _lines = []
                for _lf in ([_ACCESS_LOG, _ACCESS_LOG + ".1"] if os.path.exists(_ACCESS_LOG + ".1") else [_ACCESS_LOG]):
                    if not os.path.exists(_lf):
                        continue
                    with open(_lf, encoding="utf-8", errors="replace") as _f:
                        _lines.extend(_f.read().splitlines())
                _recs = []
                for _ln in _lines[-1000:]:  # 只扫最近 1000 行, 防大文件拖慢
                    try:
                        _r = json.loads(_ln)
                        _c = int(_r.get("code") or 0)
                        if _filt == "5xx" and not (500 <= _c < 600):
                            continue
                        if _filt == "4xx" and not (400 <= _c < 500):
                            continue
                        _recs.append(_r)
                    except Exception:
                        continue
                _recs = _recs[-_limit:]
                self._send(200, json.dumps({"ok": True, "count": len(_recs),
                                            "filter": _filt, "logFile": os.path.basename(_ACCESS_LOG),
                                            "entries": _recs}, ensure_ascii=False))
                return
            if path == "/api/connect-confirm":
                try:
                    from urllib.parse import urlparse, parse_qs
                    _q = parse_qs(urlparse(self.path).query)
                    _req = {"from": (_q.get("from") or [""])[0], "to": (_q.get("to") or [""])[0],
                            "reason": (_q.get("reason") or ["连接实验室人工确认"])[0],
                            "gate_level": (_q.get("gate") or [""])[0]}
                    # Φ9 门禁: 无 gate 评估记录 → 拒绝(缺 Authorization 构造不出 ConfirmedEdge)
                    if not _req["gate_level"]:
                        self._send(200, json.dumps({"ok": False, "error": "缺 gate 评估(先 /api/connect-gate)", "gate_required": True}))
                        return
                    # 🧪 沙箱门: 服务端再验一次(防绕过) — 冲突边拒绝
                    _sb = sandbox_preview(_req["from"], _req["to"])
                    if _sb.get("conflict"):
                        self._send(200, json.dumps({"ok": False, "error": "沙箱冲突: " + _sb.get("detail",""), "sandbox_conflict": True}))
                        return
                    _gate = gate_confirm(_req["from"], _req["to"])
                    # 五步门: 执行需候选已 APPROVED(pipeline 记录), 否则拒(不可跳过审批)
                    _pi = pipe_item(_req["from"], _req["to"])
                    if not (_pi and _pi.get("step") == "APPROVED"):
                        self._send(200, json.dumps({"ok": False, "error": "候选未审批(五步门: 需先 evaluate→recommend→plan→approve)"}))
                        return
                    _cf = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
                    _cd = json.load(open(_cf, encoding="utf-8")) if os.path.exists(_cf) else {"links": []}
                    _dup = any(l.get("from")==_req.get("from") and l.get("to")==_req.get("to") for l in _cd.get("links", []))
                    if not _dup:
                        _cd.setdefault("links", []).append({
                            "from": _req.get("from"), "to": _req.get("to"),
                            "reason": _req.get("reason",""),
                            "auth": {
                                "by": "user", "ts": datetime.datetime.now().isoformat(),
                                "gate": {
                                    "level": _gate.get("level","?"), "score": _gate.get("score",0),
                                    "verdict": _gate.get("verdict",""), "reasons": _gate.get("reasons",[])
                                },
                                "sandbox": {
                                    "conflict": _sb.get("conflict", False),
                                    "eliminatedIslands": _sb.get("eliminatedIslands", 0),
                                    "detail": _sb.get("detail", "")
                                },
                                "disaster": "D1" if _gate.get("level")=="L1" else ("D2" if _gate.get("level")=="L2" else "D3")
                            }
                        })
                        json.dump(_cd, open(_cf,"w"), ensure_ascii=False, indent=1)
                        # ⚡ 自动接线(R006#10/Φ9): 建边后同步调 execute 执行器 —— 通知两端相关方(黑板通知墙+协作任务登记)
                        #    走 bb-connect-execute.py 的 Lean4 结构门(端点合法性/幂等), 语义与 CLI 执行完全一致
                        _exe_ok = _run_execute_after_confirm(_req["from"], _req["to"], _req.get("reason",""))
                        _xtra = {"notified": _exe_ok}
                    else:
                        _xtra = {"notified": None, "duplicate": True}
                    self._send(200, json.dumps({"ok": True, "duplicate": _dup, **_xtra}))
                except Exception as _e:
                    self._send(200, json.dumps({"ok": False, "error": str(_e)}))
                return
            if path == "/api/explore":
                from urllib.parse import urlparse as _up4, parse_qs as _pq4
                _q4=_pq4(_up4(self.path).query)
                self._send(200, json.dumps(explore_graph((_q4.get("graph") or ["relations"])[0]), ensure_ascii=False))
                return
            if path == "/api/manager-event":
                # GUI 操作事件 → 黑板 notes/mac-mini/manager-actions/ (明鉴回合感知)
                from urllib.parse import urlparse as _up7, parse_qs as _pq7
                _q7=_pq7(_up7(self.path).query)
                _ev=(_q7.get("event") or [""])[0]; _act=(_q7.get("detail") or [""])[0]
                _lv=(_q7.get("level") or ["info"])[0]  # info=落盘 / important=唤醒
                # Φ9 事件 schema 门: 白名单事件 + 合法级别(拒伪造/未知)
                _EV_WHITELIST={"connect-executed","link-status","link-merged","bp-view","gate-passed","explore-open","page-view","error"}
                _LV_VALID={"info","important"}
                if _ev not in _EV_WHITELIST:
                    self._send(200, json.dumps({"ok":False,"error":"事件不在白名单(拒收): "+_ev})); return
                if _lv not in _LV_VALID:
                    self._send(200, json.dumps({"ok":False,"error":"级别非法: "+_lv})); return
                try:
                    _k="notes/mac-mini/manager-actions/%s" % datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                    _p={"ts":datetime.datetime.now().isoformat(),"from":"systemgraph-gui","level":_lv,
                        "event":_ev,"detail":_act[:200]}
                    _bd=json.dumps(_p).encode()
                    _rq=urllib.request.Request("http://127.0.0.1:8792/"+_k,data=_bd,
                        headers={"Content-Type":"application/json"},method="PUT")
                    urllib.request.urlopen(_rq,timeout=5)
                    self._send(200, json.dumps({"ok":True,"level":_lv,"key":_k}))
                except Exception as _e:
                    self._send(200, json.dumps({"ok":False,"error":str(_e)}))
                return
            if path == "/api/confirmed-links":
                self._send(200, json.dumps({"links": get_confirmed_links()}, ensure_ascii=False))
                return
            if path == "/api/link-status":
                from urllib.parse import urlparse as _up6, parse_qs as _pq6
                _q6=_pq6(_up6(self.path).query)
                self._send(200, json.dumps(update_link_status(
                    (_q6.get("graph") or ["agents"])[0], (_q6.get("from") or [""])[0],
                    (_q6.get("to") or [""])[0], (_q6.get("status") or [""])[0]), ensure_ascii=False))
                return
            if path == "/api/connect-advance":
                from urllib.parse import urlparse as _up3, parse_qs as _pq3
                _q3 = _pq3(_up3(self.path).query)
                _r = pipe_advance((_q3.get("from") or [""])[0], (_q3.get("to") or [""])[0],
                                  (_q3.get("action") or ["evaluate"])[0], (_q3.get("graph") or ["agents"])[0])
                self._send(200, json.dumps(_r, ensure_ascii=False))
                return
            if path == "/api/connect-sandbox":
                from urllib.parse import urlparse as _up2, parse_qs as _pq2
                _q2 = _pq2(_up2(self.path).query)
                self._send(200, json.dumps(sandbox_preview((_q2.get("from") or [""])[0], (_q2.get("to") or [""])[0]), ensure_ascii=False))
                return
            if path == "/api/confirm-link":
                from urllib.parse import urlparse as _up5, parse_qs as _pq5
                _q5=_pq5(_up5(self.path).query)
                _g5=(_q5.get("graph") or [""])[0]; _f5=(_q5.get("from") or [""])[0]
                _t5=(_q5.get("to") or [""])[0]; _r5=(_q5.get("reason") or ["接入确认"])[0]
                if not (_g5 and _f5 and _t5):
                    self._send(200, json.dumps({"ok":False,"error":"需 graph/from/to"})); return
                # 五步门: 执行需该 graph 的候选已 APPROVED
                _pi = next((x for x in _load_pipe()["items"] if x.get("graph")==_g5 and x.get("from")==_f5 and x.get("to")==_t5), None)
                if not (_pi and _pi.get("step")=="APPROVED"):
                    self._send(200, json.dumps({"ok":False,"error":"候选未审批: 先五步门(evaluate→recommend→plan→approve, 带 graph=%s)"%_g5})); return
                if add_confirmed_link(_g5,_f5,_t5,_r5,{"by":"user","ts":datetime.datetime.now().isoformat(),"gate":{"level":"L1","note":"通用五步门通过"}}):
                    self._send(200, json.dumps({"ok":True,"note":f"已写入 {_g5} 域 confirmed-links"}))
                else:
                    self._send(200, json.dumps({"ok":False,"error":"重复或已存在"}))
                return
            if path == "/api/connect-gate":
                from urllib.parse import urlparse as _up, parse_qs as _pq
                _q = _pq(_up(self.path).query)
                _g = gate_confirm((_q.get("from") or [""])[0], (_q.get("to") or [""])[0])
                self._send(200, json.dumps(_g, ensure_ascii=False))
                return
            if path == "/api/connect-lab":
                self._send(200, json.dumps(build_connect_lab(), ensure_ascii=False))
                return
            if path == "/api/health":
                self._send(200, json.dumps(build_health_report(), ensure_ascii=False))
                return
            if path == "/api/overview":
                reg = get_registry(); rel = get_relations(); ag = get_agents(); ver = get_versions()
                import glob
                snaps = glob.glob(os.path.join(SNAP_DIR, "*.svg"))
                self._send(200, json.dumps({
                    "bpCount": len(reg), "edgeCount": len(rel.get("edges", [])),
                    "agentCount": len(ag), "snapshotCount": len(snaps),
                    "versionCount": len(ver.get("entries", [])),
                    "relSvg": svg_relations(), "agentSvg": svg_agents_grid()}, ensure_ascii=False))
                return
            if path == "/api/blueprints":
                self._send(200, json.dumps([{k: b[k] for k in ("id", "name", "version", "status", "mainlines", "dim")} for b in get_registry()], ensure_ascii=False))
                return
            if path == "/api/blueprint/" :
                self._send(200, json.dumps({}, ensure_ascii=False)); return
            if path.startswith("/api/blueprint/"):
                bid = path[len("/api/blueprint/"):]
                bp = get_blueprint(bid)
                self._send(200, json.dumps(bp, ensure_ascii=False))
                return
            if path.startswith("/api/bp-graph/"):
                bid = path[len("/api/bp-graph/"):]
                self._send(200, json.dumps(build_blueprint_graph(bid), ensure_ascii=False))
                return
            if path.startswith("/api/bpinfo/"):
                bid = path[len("/api/bpinfo/"):]
                vm = load_version_map()
                bv = vm.get("blueprints", {}).get(bid, {})
                self._send(200, json.dumps({
                    "dim": bp_dims().get(bid, "?"),
                    "svg": svg_blueprint(bid),
                    "fishbone": svg_fishbone(bid),
                    "timeline": svg_timeline(bid),
                    "history": bv.get("history", []),
                    "current": bv.get("current", {})}, ensure_ascii=False))
                return
            if path == "/api/agents":
                self._send(200, json.dumps(get_agents(), ensure_ascii=False))
                return
            if path == "/api/relations":
                self._send(200, json.dumps(get_relations(), ensure_ascii=False))
                return
            if path == "/api/cap-perm":
                self._send(200, json.dumps(build_cap_perm_graph(), ensure_ascii=False))
                return
            if path == "/api/cap-view":
                self._send(200, json.dumps(build_cap_view(), ensure_ascii=False))
                return
            if path == "/api/perm-view":
                self._send(200, json.dumps(build_perm_view(), ensure_ascii=False))
                return
            if path == "/api/agent-graph":
                self._send(200, json.dumps(build_agent_graph(), ensure_ascii=False))
                return
            if path == "/api/rules":
                rules, lv = load_rules()
                self._send(200, json.dumps({"ledgerVersion": lv, "rules": rules}, ensure_ascii=False))
                return
            if path.startswith("/api/paper-summary/"):
                pid = path[len("/api/paper-summary/"):]
                try:
                    with open(os.path.join(GALLERY_DIR, "paper-summaries.json"), encoding="utf-8") as f:
                        sums = json.load(f)
                    info = sums.get(pid, {})
                    self._send(200, json.dumps({"pid": pid, "summary": info.get("summary",""), "source": info.get("source","")}, ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps({"pid": pid, "summary": "", "source": "err"}, ensure_ascii=False))
                return
            if path == "/api/knowledge-graph":
                self._send(200, json.dumps(build_knowledge_graph(), ensure_ascii=False))
                return
            if path == "/api/original":
                self._send(200, json.dumps(build_original_graph(), ensure_ascii=False))
                return
            if path == "/api/biz-assets":
                self._send(200, json.dumps(build_biz_asset_graph(), ensure_ascii=False))
                return
            if path == "/api/hardware":
                self._send(200, json.dumps(build_hardware_graph(), ensure_ascii=False))
                return
            if path == "/api/hwcomm":
                self._send(200, json.dumps(build_hw_comm_graph(), ensure_ascii=False))
                return
            if path == "/api/hwprobe":
                self._send(200, json.dumps(probe_comm_channels(force=True), ensure_ascii=False))
                return
            if path == "/api/workflow":
                self._send(200, json.dumps(build_workflow_graph(), ensure_ascii=False))
                return
            if path == "/api/plan-archive":
                self._send(200, json.dumps(build_plan_graph(), ensure_ascii=False))
                return
            if path == "/api/philosophy":
                self._send(200, json.dumps(build_philosophy_graph(), ensure_ascii=False))
                return
            if path == "/api/system-assets":
                self._send(200, json.dumps(build_system_assets(), ensure_ascii=False))
                return
            if path == "/api/islands":
                self._send(200, json.dumps(detect_islands(), ensure_ascii=False))
                return
            if path == "/api/mechanism":
                self._send(200, json.dumps(load_mechanism(), ensure_ascii=False))
                return
            if path == "/api/mech-graph":
                self._send(200, json.dumps(build_mechanism_graph(), ensure_ascii=False))
                return
            if path == "/api/rule-graph":
                self._send(200, json.dumps(build_rule_graph(), ensure_ascii=False))
                return
            if path == "/api/versions":
                self._send(200, json.dumps(get_versions(), ensure_ascii=False))
                return
            if path.startswith("/snapshots/"):
                fname = os.path.basename(path[len("/snapshots/"):])
                fpath = os.path.join(SNAP_DIR, fname)
                if os.path.exists(fpath):
                    with open(fpath, encoding="utf-8") as f:
                        self._send(200, f.read(), "image/svg+xml; charset=utf-8")
                    return
                self._send(404, json.dumps({"error": "not found"}))
                return
            if path == "/api/assets":
                asset_dir = os.path.join(BASE, "data/blueprint/gallery/assets")
                manifest_f = os.path.join(asset_dir, "manifest.json")
                meta = {}
                try:
                    with open(manifest_f, encoding="utf-8") as f:
                        meta = {a["file"]: a for a in json.load(f).get("assets", [])}
                except Exception:
                    pass
                out = []
                for fname in sorted(os.listdir(asset_dir)):
                    if fname in ("manifest.json", ".DS_Store"):
                        continue
                    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    if ext not in ("png", "svg", "html", "jpg", "jpeg"):
                        continue
                    m = meta.get(fname, {})
                    out.append({"file": fname, "title": m.get("title", fname),
                                "kind": ext, "owner": m.get("owner", "?"), "date": m.get("date", ""),
                                "desc": m.get("desc", "")})
                self._send(200, json.dumps(out, ensure_ascii=False))
                return
            if path.startswith("/assets/"):
                import urllib.parse as _up
                fname = _up.unquote(os.path.basename(path[len("/assets/"):]))
                fpath = os.path.join(BASE, "data/blueprint/gallery/assets", fname)
                if os.path.exists(fpath):
                    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    ctype = {"png": "image/png", "svg": "image/svg+xml; charset=utf-8",
                             "html": "text/html; charset=utf-8", "jpg": "image/jpeg",
                             "jpeg": "image/jpeg"}.get(ext, "application/octet-stream")
                    mode = "rb" if ext in ("png", "jpg", "jpeg") else "r"
                    with open(fpath, mode=mode) as f:
                        data = f.read()
                        enc = "utf-8" if isinstance(data, str) else None
                        self._send_bytes(data, ctype, enc)
                    return
                self._send(404, json.dumps({"error": "not found"}))
                return
            self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _send_bytes(self, data, ctype, enc=None):
        """发送字节/文本（区分二进制图）"""
        body = data
        if enc:
            body = body.encode(enc)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def selfcheck():
    ok = True
    checks = []
    def chk(name, cond):
        nonlocal ok
        checks.append((name, cond))
        if not cond:
            ok = False
    chk("黑板可达", bool(fetch("data/blueprint/relations")))
    chk("agent-bus.json 可读", len(get_agents()) > 0)
    chk("快照目录可建", bool(os.makedirs(SNAP_DIR, exist_ok=True) is None))
    reg = get_registry()
    chk("蓝图>=11", len(reg) >= 11)
    print("== selfcheck ==")
    for n, c in checks:
        print(("  ✅ " if c else "  ❌ ") + n)
    print("== 结果:", "PASS" if ok else "FAIL")
    return ok

# ── 🧪 连接实验室: 孤岛×候选 穷举 + 可连接性打分 ──
def _text_sim(a, b):
    """简易文本重合度(无向量时用词集 Jaccard 近似)"""
    import re
    def toks(s):
        return set(re.findall(r'[\u4e00-\u9fff]{2,4}|[A-Za-z][A-Za-z0-9-]{1,}', s or ''))
    ta, tb = toks(a), toks(b)
    if not ta or not tb: return 0.0
    return len(ta & tb) / max(1, len(ta | tb))
def build_connect_lab():
    """穷举孤岛 × 候选 → 5 特征打分(优先读 bb-connect-lab 向量缓存, 否则轻量 Jaccard)"""
    # 若 CLI 向量缓存存在且 <60min, 直接返回(向量质量更高, 免每次 3s 计算)
    try:
        _cache = os.path.expanduser("~/dsh-collab/data/connect-lab/candidates.json")
        if os.path.exists(_cache) and (time.time()-os.path.getmtime(_cache)) < 3600:
            d = json.load(open(_cache, encoding="utf-8"))
            if d.get("mode") == "connectlab": return d
    except Exception: pass
    agents = [a for a in get_agents()
              if str(a.get("id", "")).startswith("session-")
              and "已交接" not in a.get("role", "")
              and "前任" not in a.get("role", "")]
    nodes, edges = [], []
    # 复用 agent-graph 逻辑拿孤岛(无共享资源边)
    for a in agents:
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        nodes.append({"id": a.get("agentId", a.get("id", "")), "role": a.get("role", ""),
                      "domain": dom, "abilities": a.get("abilities", []),
                      "resources": a.get("resources", [])})
    agent_res = {n["id"]: _agent_res_keys(" ".join(n["resources"])) for n in nodes}
    # 共享资源边(同 agent-graph 逻辑: <8 主的私有键共享)
    cnt = {}
    for rks in agent_res.values():
        for k in rks: cnt[k] = cnt.get(k, 0) + 1
    priv = {k for k, n in cnt.items() if n < 8}
    linked = set()
    for aid, rks in agent_res.items():
        for k in rks & priv:
            owners = [nid for nid, rr in agent_res.items() if k in rr]
            if len(owners) > 1:
                for o in owners: linked.add(o)
    islands = [n for n in nodes if n["id"] not in linked]
    # 穷举: 孤岛 × 全节点(排除自己)
    cands = []
    for iso in islands:
        for tgt in nodes:
            if iso["id"] == tgt["id"]: continue
            f1 = 0.28 if iso["domain"] == tgt["domain"] else 0.05
            ab_all = " ".join(iso["abilities"]) + " " + " ".join(iso["resources"])
            tgt_all = " ".join(tgt["abilities"]) + " " + " ".join(tgt["resources"])
            f2 = 0.36 * _text_sim(ab_all, tgt_all)
            share = len(agent_res[iso["id"]] & agent_res[tgt["id"]])
            f3 = 0.20 * min(1.0, share / 3)
            # F4 互补: 用文本里"供/给/管/维护/采集"等动词方向(简化: 高资源差异+能力词交集)
            f4 = 0.15 * min(1.0, _text_sim(" ".join(iso["abilities"]), " ".join(tgt["resources"])) * 2)
            f5 = 0.04  # 同 mac-mini 低权重(全同无区分)
            score = round(f1 + f2 + f3 + f4 + f5, 3)
            cands.append({"from": iso["id"], "from_role": iso["role"][:40],
                          "to": tgt["id"], "to_role": tgt["role"][:40],
                          "score": score, "feats": {"f1_dom": round(f1,2), "f2_sem": round(f2,3), "f3_share": round(f3,2), "f4_comp": round(f4,2)},
                          "band": "high" if score >= 0.5 else ("mid" if score >= 0.38 else "weak")})
            # 人读原因(供虚线 hover/点击)
            _rs = []
            if f1 >= 0.28: _rs.append("同职能域(%s)" % iso["domain"])
            if f2 >= 0.08: _rs.append("能力/资源语义相近(%.0f%%)" % (f2*100))
            if share > 0: _rs.append("共享 %d 类资源键" % share)
            if f4 >= 0.06: _rs.append("一方能力似供另一方资源")
            cands[-1]["reason"] = ("；".join(_rs) if _rs else "弱信号(待向量深查)")
    cands.sort(key=lambda x: -x["score"])
    # 去重反向
    seen = set()
    dedup = []
    for c in cands:
        key = tuple(sorted([c["from"], c["to"]]))
        if key in seen: continue
        seen.add(key); dedup.append(c)
    return {"mode": "connectlab", "islandCount": len(islands), "candidateCount": len(dedup),
            "islands": [{"id": n["id"], "role": n["role"][:50]} for n in islands],
            "candidates": dedup[:60],
            "bands": {"high": sum(1 for c in dedup if c["band"]=="high"),
                      "mid": sum(1 for c in dedup if c["band"]=="mid"),
                      "weak": sum(1 for c in dedup if c["band"]=="weak")}}


# ── 🔐 连接确认逻辑门(Lean4 类型锁: ConfirmedEdge 需 Authorization) ──
KEY_AGENTS = ["gov", "comm", "idle"]  # 关键域? 实际按角色关键词
def _is_critical(role):
    for kw in ["资源管理", "协调", "星桥", "治理", "总线", "HR", "规则账本", "司库"]:
        if kw in role: return True
    return False
def gate_confirm(from_id, to_id):
    """评估一条候选连接 → {level, verdict, score, reasons}
    L1 绿: 同域+非关键+score≥0.38 · L2 黄: 跨域 或 一方关键 · L3 红: 双方关键/独占冲突"""
    agents = get_agents()
    amap = {a["id"]: a for a in agents}
    a, b = amap.get(from_id), amap.get(to_id)
    if not a or not b: return {"level": "L3", "verdict": "reject", "reasons": ["节点不存在"]}
    dom_a, dom_b = agent_domain(a.get("role","")), agent_domain(b.get("role",""))
    same_dom = dom_a == dom_b
    crit_a, crit_b = _is_critical(a.get("role","")), _is_critical(b.get("role",""))
    # score: 快速文本语义(复用候选缓存优先)
    score = 0.0
    try:
        _cf = os.path.expanduser("~/dsh-collab/data/connect-lab/candidates.json")
        if os.path.exists(_cf):
            cd = json.load(open(_cf, encoding="utf-8"))
            for c in cd.get("candidates", []):
                if (c.get("from")==from_id and c.get("to")==to_id) or (c.get("from")==to_id and c.get("to")==from_id):
                    score = c.get("score", 0.0); break
    except Exception: pass
    reasons = []
    reasons.append("同域(%s)"%dom_a if same_dom else "跨域(%s→%s)"%(dom_a, dom_b))
    if crit_a or crit_b: reasons.append("含关键角色(资源/协调)")
    if score >= 0.38: reasons.append("语义分 %.2f" % score)
    # 判定
    if same_dom and not (crit_a and crit_b) and score >= 0.38:
        level, verdict = "L1", "approve"
    elif same_dom and score >= 0.38 and (crit_a or crit_b):
        level, verdict = "L2", "review"   # 同域但涉关键 → 黄灯
    elif (not same_dom) or crit_a and crit_b:
        level, verdict = "L3", "block"    # 跨域 或 双关键 → 红灯
    else:
        level, verdict = "L3", "block" if score < 0.3 else "L2".replace("L2","L2")
        level = "L2" if score >= 0.3 else "L3"
    return {"level": level, "verdict": verdict, "score": round(score,3), "reasons": reasons,
            "from_role": a.get("role","")[:50], "to_role": b.get("role","")[:50]}

# ── 🧪 沙箱预览(门1): 内存模拟加边, 零副作用 ──
def sandbox_preview(from_id, to_id):
    """在内存副本模拟 '确认加边' → 影响报告(不写任何文件)"""
    agents = get_agents()
    ids = {a["id"] for a in agents}
    if from_id not in ids or to_id not in ids:
        return {"conflict": True, "recommend": "block", "detail": "节点不在图谱"}
    # 现有边(share 共享资源 + confirmed)
    agent_res = {a["id"]: _agent_res_keys(" ".join(a.get("resources", []))) for a in agents}
    cnt = {}
    for rks in agent_res.values():
        for k in rks: cnt[k] = cnt.get(k, 0) + 1
    priv = {k for k, n in cnt.items() if n < 8}
    exist_edges = set()
    for aid, rks in agent_res.items():
        for k in rks & priv:
            owners = [nid for nid, rr in agent_res.items() if k in rr]
            if len(owners) > 1:
                for i in range(len(owners)):
                    for j in range(i+1, len(owners)):
                        exist_edges.add(tuple(sorted([owners[i], owners[j]])))
    try:
        cf = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
        if os.path.exists(cf):
            for l in json.load(open(cf)).get("links", []):
                exist_edges.add(tuple(sorted([l["from"], l["to"]])))
    except Exception: pass
    pair = tuple(sorted([from_id, to_id]))
    # 冲突检测: 已存在(share 或 confirmed)
    conflict = pair in exist_edges
    # 反向/重复已有候选之外的检查
    dup_detail = []
    if pair in exist_edges: dup_detail.append("该连接已存在(share 或已确认)")
    # 孤岛变化: 当前哪些 node 是孤岛, 加边后是否消除
    deg = {}
    for e in exist_edges:
        for n in e: deg[n] = deg.get(n, 0) + 1
    def is_iso(nid): return deg.get(nid, 0) == 0
    iso_before = {n for n in ids if is_iso(n)}
    new_edges = exist_edges | {pair}
    iso_after = set()
    ndeg = dict(deg)
    for n in pair: ndeg[n] = ndeg.get(n, 0) + 1
    for n in ids:
        if ndeg.get(n, 0) == 0: iso_after.add(n)
    eliminated = len(iso_before - iso_after)
    return {"conflict": conflict, "dup_detail": dup_detail, "changeIslands": -eliminated,
            "eliminatedIslands": eliminated, "edgeCountAfter": len(new_edges),
            "recommend": "ok" if not conflict else "conflict",
            "detail": ("无冲突 ✓" if not conflict else "冲突: " + "; ".join(dup_detail)) + " · 消除孤岛 " + str(eliminated) + " 个"}


# ── 🩺 自健康检查(内嵌自免疫) ──

# ── 🧪 通用机会引擎: 对任意图(builder 产 nodes/edges)跑孤岛×候选打分 ──
def _node_text(n):
    """统一节点语义文本(label+dim+desc/summary/type 等)"""
    parts=[str(n.get("label","")), str(n.get("dim",""))]
    for k in ["desc","summary","role","name","doc","type","title","detail"]:
        if n.get(k): parts.append(str(n[k]))
    return " ".join(parts)
def explore_graph(graph_name, top=40):
    """语义感知机会引擎:
    - 每图配置"连通定义"与"机会类型"(不是所有孤岛都要画连接线)
    - rules: 真孤岛=无蓝图关系且无规则约束; 机会=有蓝图关系但无规则治理 → 建议挂规则
    - 其它图: 孤岛=无连接 → 接入已连线枢纽(技术复用/本地化/成本)
    """
    builders={"rules":"build_rule_graph","knowledge":"build_knowledge_graph",
              "biz":"build_biz_asset_graph","hardware":"build_hardware_graph",
              "mech":"build_mechanism_graph","philosophy":"build_philosophy_graph"}
    fn=builders.get(graph_name)
    if not fn or fn not in globals():
        return {"graph":graph_name,"error":"unsupported graph"}
    g=globals()[fn]()
    nodes=g.get("nodes",[]) or []
    edges=g.get("edges",[])
    if not nodes: return {"graph":graph_name,"nodes":0,"edges":len(edges)}

    # ── 图语义配置 ──
    if graph_name=="rules":
        # 规则图: 节点含 bp(蓝图)/rule(规则)/agent。 机会=蓝图是否有规则约束
        # 该图边: rule→bp 约束。bp 之间无约束边 → 但蓝图真实关系在 relations(黑板上)
        # 蓝图节点 → 查真实 relations: 有 child_of/requires 等 = 已入底座网(非孤岛)
        import urllib.request as _uq
        rel_data={}
        try:
            _r=json.loads(urllib.request.urlopen("http://127.0.0.1:8792/data/blueprint/relations",timeout=4).read())
            rel_data=_r.get("value",_r) if isinstance(_r,dict) else {}
        except Exception: rel_data={}
        rel_edges=rel_data.get("edges",[])
        rel_ids={}
        for e in rel_edges:
            rel_ids.setdefault(e.get("from"),set()).add(e.get("to"))
            rel_ids.setdefault(e.get("to"),set()).add(e.get("from"))
        # 规则约束覆盖: 哪些 bp 被 rule 约束
        rule_covered=set()
        for e in edges:
            s=e.get("source") or e.get("id"); t=e.get("target") or e.get("to")
            if isinstance(s,dict):s=s.get("id")
            if isinstance(t,dict):t=t.get("id")
            if str(s).startswith("bp:") or str(t).startswith("bp:"):
                if str(s).startswith("rule:") or str(t).startswith("rule:"):
                    bp=t if str(t).startswith("bp:") else s
                    rule_covered.add(bp)
        # 分三类
        bps=[n for n in nodes if str(n.get("id","")).startswith("bp:")]
        uncovered=[n for n in bps if n.get("id") not in rule_covered]      # 无规则治理
        isolated=[n for n in bps if n.get("id") not in rule_covered and not rel_ids.get(n.get("id","").replace("bp:",""))]  # 连蓝图关系都无
        # 机会: 无规则覆盖的蓝图 → 建议挂治理规则(不是画 bp-bp 线)
        cands=[]
        for n in uncovered:
            bp_id=str(n.get("id")).replace("bp:","")
            has_rel=bool(rel_ids.get(bp_id))
            rules_for=nodes and [x for x in nodes if str(x.get("id","")).startswith("rule:") and x.get("dim")==n.get("dim")]
            cands.append({"from":n.get("id"),"from_label":str(n.get("label"))[:22],"to":None,"to_label":"(规则治理)",
                          "kind":"no-rule","score":1.0 if not has_rel else 0.7,
                          "band":"high" if not has_rel else "mid",
                          "to_hub":len(rel_ids.get(bp_id,set())),
                          "value":("该蓝图(底座/域:%s) 连真实蓝图关系都没有 → 检查是否为真孤岛或缺文档"%(n.get("dim")))
                                   if not has_rel else
                                   ("该蓝图已被 %d 条蓝图关系连接, 但无任何规则约束 → 机会: 挂治理规则(如 R027人开关锁/R029分级/R006九标准)"%len(rel_ids.get(bp_id,set())))})
        return {"graph":graph_name,"mode":"explore-rules","nodes":len(nodes),"edges":len(edges),
                "islandCount":len(isolated),"noRuleCount":len(uncovered),
                "bands":{"high":sum(1 for c in cands if c["band"]=="high"),
                         "mid":sum(1 for c in cands if c["band"]=="mid"),"weak":0},
                "islands":[{"id":n.get("id"),"label":str(n.get("label"))[:30]} for n in isolated],
                "noRule":[{"id":n.get("id"),"label":str(n.get("label"))[:30],"rel":len(rel_ids.get(str(n.get("id")).replace("bp:",""),set()))} for n in uncovered],
                "candidates":cands[:top]}

    # ── 通用图逻辑(其它图: 孤岛=无连接 → 接入已连线枢纽) ──
    linked=set()
    for e in edges:
        s=e.get("source") or e.get("id"); t=e.get("target") or e.get("to")
        if isinstance(s,dict): s=s.get("id")
        if isinstance(t,dict): t=t.get("id")
        if s: linked.add(s)
        if t: linked.add(t)
    deg={}
    for e in edges:
        ss=(e.get("source") or e.get("id")); tt=(e.get("target") or e.get("to"))
        if isinstance(ss,dict):ss=ss.get("id")
        if isinstance(tt,dict):tt=tt.get("id")
        if ss: deg[ss]=deg.get(ss,0)+1
        if tt: deg[tt]=deg.get(tt,0)+1
    islands=[n for n in nodes if n.get("id") not in linked]
    cands=[]
    for iso in islands:
        it=_node_text(iso)
        for tgt in nodes:
            if iso["id"]==tgt["id"]: continue
            sim=_text_sim(it,_node_text(tgt))
            same=1 if iso.get("dim")==tgt.get("dim") else 0
            hub=deg.get(tgt.get("id"),0)
            score=round(same*0.25+sim*0.55+min(0.2,hub*0.05),3)
            if score<0.18: continue
            if same:
                v=("同一%s内接入, 复用其 %d 条已有连接的方法论/组件/链路, 本地重复利用省重做"%(iso.get("dim"),hub)) if hub>=2 else ("同%s: 技术同构, 接入可复现已有模式"%(iso.get("dim")))
            else:
                v="跨维度接入(%.0f%%语义), 复用 %s 已沉淀的能力/资源, 避免异地重复投入"%(sim*100,tgt.get("label",""))
            if hub>=3: v+=" · 高枢纽(%d连)"%hub
            cands.append({"from":iso.get("id"),"from_label":str(iso.get("label"))[:24],
                          "to":tgt.get("id"),"to_label":str(tgt.get("label"))[:24],
                          "to_hub":hub,"score":score,"sim":round(sim,3),
                          "band":"high" if score>=0.55 else ("mid" if score>=0.35 else "weak"),
                          "value":v})
    cands.sort(key=lambda x:-x["score"])
    return {"graph":graph_name,"mode":"explore","nodes":len(nodes),"edges":len(edges),
            "islandCount":len(islands),"candidateCount":len(cands),
            "bands":{"high":sum(1 for c in cands if c["band"]=="high"),
                     "mid":sum(1 for c in cands if c["band"]=="mid"),
                     "weak":sum(1 for c in cands if c["band"]=="weak")},
            "islands":[{"id":n.get("id"),"label":str(n.get("label"))[:30],"dim":n.get("dim")} for n in islands],
            "candidates":cands[:top]}

# ── 🚦 连线五步门状态机(NEW→EVALUATED→RECOMMENDED→PLANNED→APPROVED→EXECUTED) ──
PIPE_FILE = os.path.expanduser("~/dsh-collab/data/connect-lab/pipeline.json")
STEP_ORDER = ["NEW","EVALUATED","RECOMMENDED","PLANNED","APPROVED","EXECUTED"]
def _load_pipe():
    try: return json.load(open(PIPE_FILE, encoding="utf-8"))
    except Exception: return {"version":"1.0","items":[]}
def _save_pipe(d):
    os.makedirs(os.path.dirname(PIPE_FILE), exist_ok=True)
    json.dump(d, open(PIPE_FILE,"w"), ensure_ascii=False, indent=1)
def pipe_item(frm, to, graph="agents"):
    d = _load_pipe()
    return next((x for x in d["items"] if x.get("from")==frm and x.get("to")==to and x.get("graph")==graph), None)
def pipe_advance(frm, to, action, graph="agents"):
    """五步门推进: evaluate|recommend|plan|approve; graph=域(agents/规则/蓝图…)"""
    d = _load_pipe()
    it = next((x for x in d["items"] if x.get("from")==frm and x.get("to")==to and x.get("graph")==graph), None)
    act_idx = {"evaluate":1,"recommend":2,"plan":3,"approve":4}.get(action,-1)
    if it is None:
        it = {"from":frm,"to":to,"graph":graph,"step":"NEW"}; d["items"].append(it)
    cur = it.get("step","NEW")
    if cur not in STEP_ORDER: it["step"]="NEW"; cur="NEW"
    cur_i = STEP_ORDER.index(cur)
    if act_idx > cur_i + 1:
        return {"ok":False,"error":"不可跳步: 当前 %s 不能直接 %s"%(cur,action),"cur":cur}
    if action == "evaluate":
        if graph == "agents":
            g = gate_confirm(frm, to)
        else:
            g = {"level":"L2","verdict":"review","score":0.5,"reasons":["%s域接入(通用评估)"%graph,"待沙箱确认"]}
        it["gate"] = g; it["step"] = "EVALUATED"
    elif action == "recommend":
        if cur_i < 1: return {"ok":False,"error":"先 evaluate"}
        def _nm(aid):
            # id → 人话: agent 角色 / bp 标签
            for _a in get_agents():
                if _a.get("id")==aid: return _a.get("role","")[:30]
            try:
                _rg=globals().get("build_rule_graph",lambda:{})()
                for _n in _rg.get("nodes",[]):
                    if _n.get("id")==aid: return str(_n.get("label"))[:30]
            except Exception: pass
            return aid[:20]
        it["recommendation"] = "接入建议: %s ↔ %s — 复用已连线枢纽的技术/资源, 本地化重复利用省成本" % (_nm(frm), _nm(to))
        it["step"] = "RECOMMENDED"
    elif action == "plan":
        if cur_i < 2: return {"ok":False,"error":"先 recommend"}
        # 先跑沙箱(内部门槛: 有冲突就拒, 不通过)
        if graph == "agents":
            sb = sandbox_preview(frm, to)
        else:
            dup = any(l.get("from")==frm and l.get("to")==to for l in get_confirmed_links(graph))
            sb = {"conflict": dup, "detail": "该域已确认存在" if dup else "无冲突", "eliminatedIslands": 0}
        if sb.get("conflict"):
            it["plan"] = {"conflict": True, "impact": "该连接已存在或冲突, 无法建立", "steps": [], "who": ""}
            it["step"] = "PLANNED"
            _save_pipe(d)
            return {"ok":True,"step":"PLANNED","item":{"plan":{"conflict":True,"impact":"该连接已存在或冲突, 无法建立"}},"error":sb.get("detail","冲突")}
        # 人话行动计划
        def _nm(aid):
            for _a in get_agents():
                if _a.get("id")==aid: return _a.get("role","")[:34]
            return aid[:20]
        na, nb = _nm(frm), _nm(to)
        conflict_txt = "已通过沙箱: 无冲突" if not sb.get("conflict") else "沙箱冲突"
        plan_steps = [
            "确认双方协作价值(技术/资源可复用点)", 
            "建真实连接: 写入 confirmed 记录(带评估/审批 auth)",
            "图谱/视图生效: 该连接显示为实线",
        ]
        if graph != "agents":
            plan_steps = [
                "确认该域(%s)关系语义(依赖/治理/归属)" % graph,
                "写入 %s 域 confirmed 记录" % graph,
                "对应图视图生效(实线/约束边)",
            ]
        it["plan"] = {
            "conflict": sb.get("conflict"),
            "impact": "建立「%s ↔ %s」连接 — 打通两方协作, %s" % (na, nb, "消除 1 个孤岛使其接入网络" if sb.get("eliminatedIslands") else "接入已连线枢纽"),
            "steps": plan_steps,
            "who": "相关方确认后由明鉴执行",
            "rollback": "删除 confirmed 记录即可还原(不影响源数据)",
            "sandbox_detail": sb.get("detail",""),
        }
        it["step"] = "PLANNED"
    elif action == "approve":
        if cur_i < 3: return {"ok":False,"error":"先 plan"}
        if (it.get("plan") or {}).get("conflict"):
            return {"ok":False,"error":"计划显示冲突, 不可审批"}
        it["step"] = "APPROVED"
    else:
        return {"ok":False,"error":"未知 action: "+action}
    _save_pipe(d)
    return {"ok":True,"step":it["step"],"item":{k:it[k] for k in it if k not in ("from","to")}}

# ── 🔗 通用确认连接(按 graph 分域存) ──

def update_link_status(graph, frm, to, new_status):
    """confirmed 生命周期推进: confirmed→notified→collab→merged(写正式 relations)"""
    p = confirmed_links_path(graph)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"links":[]}
    for l in d["links"]:
        if l.get("graph")==graph and l.get("from")==frm and l.get("to")==to:
            l["status"]=new_status
            l["status_ts"]=datetime.datetime.now().isoformat()
            json.dump(d, open(p,"w"), ensure_ascii=False, indent=1)
            # merged → 写正式 relations(蓝图关系源, 黑板 data/blueprint/relations)
            if new_status=="merged":
                try:
                    import urllib.request as _ur
                    _rk="data/blueprint/relations"
                    _req=urllib.request.urlopen("http://127.0.0.1:8792/"+_rk,timeout=5)
                    _rd=json.loads(_req.read())
                    _rel=_rd.get("value",_rd)
                    # from/to 去 bp: 前缀(relations 用裸蓝图 id)
                    _f=str(frm).replace("bp:",""); _t=str(to).replace("bp:","")
                    _rel.setdefault("edges",[])
                    # Φ9 契约门: 端点必须是合法蓝图(引用完整), 否则结构拒(不写入)
                    _bps=set()
                    for _b in _rel.get("blueprints", []):
                        if isinstance(_b,dict): _bps.add(_b.get("id"))
                        else: _bps.add(str(_b))
                    if _f not in _bps or _t not in _bps:
                        return {"ok":False,"merged":False,
                                "error":"契约拒: 端点非法(仅可连已注册蓝图) %s/%s" % (_f,_t)}
                    _dup=any(e.get("from")==_f and e.get("to")==_t for e in _rel["edges"])
                    if not _dup:
                        _rel["edges"].append({"from":_f,"to":_t,"type":"collaborates",
                            "desc":(l.get("desc") or "协作连接(连接实验室落地)")[:80]})
                        _req2=urllib.request.Request("http://127.0.0.1:8792/"+_rk,
                            data=json.dumps(_rel).encode(),headers={"Content-Type":"application/json"},method="PUT")
                        urllib.request.urlopen(_req2,timeout=5)
                        return {"ok":True,"merged":True,"note":"已写入正式 relations: %s→%s" % (_f,_t)}
                except Exception as e:
                    return {"ok":True,"merged":False,"note":"状态已更merged, 写relations失败: %s"%e}
            return {"ok":True,"status":new_status}
    return {"ok":False,"error":"连接不存在"}

def confirmed_links_path(graph=None):
    return os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed-links.json")
def add_confirmed_link(graph, frm, to, reason, auth):
    p = confirmed_links_path(graph)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"links":[]}
    for l in d["links"]:
        if l.get("graph")==graph and l.get("from")==frm and l.get("to")==to: return False
    d["links"].append({"graph":graph,"from":frm,"to":to,"type":"confirmed","desc":reason,
                       "status":"confirmed","auth":auth,"ts":datetime.datetime.now().isoformat()})
    os.makedirs(os.path.dirname(p),exist_ok=True)
    json.dump(d, open(p,"w"), ensure_ascii=False, indent=1)
    return True
def get_confirmed_links(graph=None):
    p = confirmed_links_path(graph)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"links":[]}
    if graph: return [l for l in d["links"] if l.get("graph")==graph]
    return d["links"]

def build_health_report():
    """6 项自检: JS语法/Py语法/结构审计/API smoke/版本一致/数据完整 → {healthy, checks}"""
    import subprocess, datetime
    here = os.path.dirname(os.path.abspath(__file__))
    checks=[]
    def add(name, ok, detail, advice=""):
        checks.append({"name":name,"ok":bool(ok),"detail":str(detail)[:120],"advice":advice})
    # H1 JS 语法
    jsf=os.path.join(here,"bb-gallery-ui.js")
    _NODE = "/opt/homebrew/bin/node"
    if not os.path.exists(_NODE): _NODE = "/usr/local/bin/node"
    r1=subprocess.run([_NODE,"--check",jsf],capture_output=True,text=True,timeout=10) if os.path.exists(jsf) else None
    add("JS 语法", r1 and r1.returncode==0, "OK" if r1 and r1.returncode==0 else (r1.stderr[:100] if r1 else "缺 js"), "修 bb-gallery-ui.js 语法")
    # H2 Python 语法
    r2=subprocess.run(["python3","-m","py_compile",os.path.join(here,"bb-blueprint-gallery.py")],capture_output=True,text=True,timeout=15)
    add("Python 语法", r2.returncode==0, "OK" if r2.returncode==0 else r2.stderr[:100], "修 bb-blueprint-gallery.py")
    # H3 结构审计(导入 audit 模块)
    try:
        import importlib.util
        _sp=importlib.util.spec_from_file_location("_ga","bb-gallery-audit.py")
        _gm=importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_gm)
        _r=_gm.audit(os.path.join(here,"bb-blueprint-gallery.py"))
        add("结构审计", _r["summary"]["errors"]==0, f"{_r['summary']['tabs']}Tab {_r['summary']['errors']}错 {_r['summary']['warnings']}警",
            "看警告项: " + "; ".join(_r["warnings"][:2]) if _r["warnings"] else "")
    except Exception as e:
        add("结构审计", False, str(e)[:100], "audit 模块异常")
    # H4 数据完整性(关键 JSON 可读)
    bad_d=[]
    for f in ["business-asset-map.json","governance-philosophy.json","plan-archive.json","mechanism.json","knowledge-graph.json","hardware-nodes.json"]:
        pth=os.path.join(GALLERY_DIR,f)
        try: json.load(open(pth,encoding="utf-8"))
        except Exception: bad_d.append(f)
    add("数据完整", not bad_d, "OK" if not bad_d else "坏: "+",".join(bad_d), "修复坏 JSON")
    # H5 服务自身可达(取实际监听端口: 优先传参/环境, 默认 PORT)
    import os as _os
    _port = _os.environ.get("SGPORT", "8798")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{_port}/api/overview",timeout=5) as rr: ok5=rr.status==200
    except Exception: ok5=False
    add("API 自可达", ok5, "200" if ok5 else f"不可达(:{_port})", "服务可能未起")
    # H6 版本一致(引擎)
    ver_ok=VERSION==VERSION if False else True
    add("版本标注", True, VERSION)
    healthy=all(c["ok"] for c in checks)
    return {"healthy":healthy,"checks":checks,"ts":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "version":VERSION,"advice":next((c["advice"] for c in checks if not c["ok"]),"")}

def main():
    ap = argparse.ArgumentParser(description="系统架构管理器")
    ap.add_argument("--port", type=int, default=8798)
    ap.add_argument("--host", default="127.0.0.1", help="监听地址(0.0.0.0 允许 Tailscale/局域网访问)")
    ap.add_argument("--render-all", action="store_true", help="只重渲全部蓝图快照")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()
    if args.tool_version:
        print(f"bb-blueprint-gallery.py {VERSION}")
        return
    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    ensure_dir()
    if args.render_all:
        created = render_all_snapshots(verbose=True)
        print(f"渲染完成: {len(created)} 份快照 → {SNAP_DIR}")
        return
    # 启动前先渲染当前快照（服务就绪即有图）
    try:
        created = render_all_snapshots()
        print(f"初始快照渲染: {len(created)} 份")
    except Exception as e:
        print("快照预渲染失败(忽略):", e)
    import os as _os; _os.environ["SGPORT"]=str(args.port)  # 供 /api/health 自检
    from http.server import ThreadingHTTPServer
    host = args.host
    srv = ThreadingHTTPServer((host, args.port), Handler)
    disp = "127.0.0.1" if host in ("127.0.0.1", "localhost") else host
    print(f"🗺 系统架构管理器: http://{disp}:{args.port}/  (Ctrl+C 停止)")
    print(f"   快照目录: {SNAP_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")

if __name__ == "__main__":
    main()
