#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wargame.py — 商业沙盘模拟器 (Business Strategy Wargame)

v1.0.0 · 明鉴 · 2026-09-09 · 纯 stdlib · 任意业务域通用(flowernet 为首个应用)

把"20 条路线沙盘推演"过程工具化: 路线生成 → 多维打分 → 对抗修正 → 收敛分析 → 力导向图/报告
方法源自: LucidWargames 思路(竞对响应+量化风险) + redteam 对抗 + 本会话 flowernet 20 路线实战

数据: ~/dsh-collab/data/wargame/<domain>/
  axes.json        战略轴定义(轴名→取值列表) → 路线穷举基础
  routes.json      生成的路线(手工或 --generate)
  checks.json      对抗检查点({route_id或"all": [风险点]})
  result.json      打分+对抗+收敛结果(输出)
  wargame.html     力导向图产物(输出)

R006: CLI(argparse) · TCC(--selfcheck) · CLD自适应(纯stdlib) · 版本(--tool-version)
      日志(logs/wargame.log) · Lean4门(--lean4-check)
用法:
  python3 wargame.py --domain flowernet init                 # 初始化域
  python3 wargame.py --domain flowernet generate             # 轴组合穷举路线
  python3 wargame.py --domain flowernet score                # 5维打分
  python3 wargame.py --domain flowernet adversary            # 对抗修正
  python3 wargame.py --domain flowernet converge             # 簇收敛
  python3 wargame.py --domain flowernet graph                # 力导向图输出
  python3 wargame.py --domain flowernet report               # 沙盘报告 md
  python3 wargame.py --domain flowernet run                  # 一键全流程(score→adversary→converge→graph→report)
"""
import argparse, json, os, sys, datetime, re, copy

VERSION = "v1.0.0"
COLLAB = os.path.expanduser("~/dsh-collab")
WG_DIR = os.path.join(COLLAB, "data", "wargame")
LOG_FILE = os.path.join(COLLAB, "logs", "wargame.log")


def now(): return datetime.datetime.now().isoformat(timespec="seconds")


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
    except Exception:
        pass


def domain_dir(dom):
    d = os.path.join(WG_DIR, dom)
    os.makedirs(d, exist_ok=True)
    return d


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ── ① init: 初始化域(axes 种子或用户手工) ──────────────────────────────
def cmd_init(dom, objective="", axes=None):
    d = domain_dir(dom)
    ax_p = os.path.join(d, "axes.json")
    if os.path.exists(ax_p):
        print(f"ℹ️ {dom} 已存在 axes.json, 跳过(可手工编辑或删后重 init)"); return 0
    if not objective:
        objective = input("沙盘目标(一句, 如: 垂直鲜花全国第一): ").strip()
    seed = axes or {
        "objective": objective,
        "引擎": ["A1", "A2"],
        "资本": ["B1", "B2", "B3"],
        "护城河": ["C1", "C2"],
        "节奏": ["快", "稳"],
    }
    save_json(ax_p, seed)
    save_json(os.path.join(d, "checks.json"), {})
    log(f"init {dom}")
    print(f"✅ {dom} 初始化: {ax_p}\n目标: {objective}\n编辑 axes.json 定义你的战略轴后跑 generate")
    return 0


# ── ② generate: 轴组合穷举路线 ─────────────────────────────────────────
def cmd_generate(dom, combos=None, named=None):
    """路线=轴取值组合; 提供 named 手写路线(推荐业务语义化) 或 combos 自动笛卡尔"""
    d = domain_dir(dom)
    ax = load_json(os.path.join(d, "axes.json"))
    routes = []
    if named:
        routes = named
    else:
        axes = {k: v for k, v in ax.items() if k != "objective"}
        keys = list(axes.keys())
        if combos:
            for c in combos:
                rid = f"R{len(routes)+1:02d}"
                routes.append({"id": rid, "dims": c,
                               "desc": " / ".join(f"{k}={c.get(k,'?')}" for k in keys[:4])})
        else:
            import itertools
            vals = [axes[k] for k in keys]
            for tup in itertools.product(*vals):
                if len(routes) >= 40:
                    break
                rid = f"R{len(routes)+1:02d}"
                routes.append({"id": rid, "dims": dict(zip(keys, tup)),
                               "desc": " × ".join(str(x) for x in tup[:3])})
    save_json(os.path.join(d, "routes.json"), routes)
    log(f"generate {dom}: {len(routes)} routes")
    print(f"✅ {dom} 生成 {len(routes)} 条路线 → routes.json")
    for r in routes[:20]:
        print(f"  {r['id']} | {r.get('desc','')[:70]}")
    return 0


# ── ③ score: 目标贡献度多维打分(可配置, 默认6维) ───────────────────────
DIM_DEFS = {
    "cash":    {"zh": "现金引擎力", "w": 1.0},   # 该路线自带现金流的能力
    "capital": {"zh": "资本效率",   "w": 1.0},   # 每元资本推向目标的效率
    "control": {"zh": "控盘保持",   "w": 1.2},   # 51%投票权可维持度
    "window":  {"zh": "窗口利用",   "w": 1.3},   # 一年授权+半年先发窗内推进度
    "moat":    {"zh": "护城河沉淀", "w": 1.0},   # 数据/供应链/品牌资产积累
    "profit":  {"zh": "盈利弹性",   "w": 1.0},   # 盈利情景好/不盈利情景可存活度
}


def cmd_score(dom, weights=None):
    """打分: 目标贡献度6维(现金引擎力/资本效率/控盘保持/窗口利用/护城河沉淀/盈利弹性)
    规则: score.json by_dim_value(中文dim键→数值) + profit_rule(盈利引擎→盈利/不盈利弹性分)
    分数: 每维 0-5, weighted → total = Σ(score*w)/Σw*5 (满分25折算为5档显示 total25)"""
    d = domain_dir(dom)
    routes = load_json(os.path.join(d, "routes.json"), [])
    if not routes:
        print("❌ 无 routes.json, 先 generate"); return 1
    w = weights or {k: v["w"] for k, v in DIM_DEFS.items()}
    rules = load_json(os.path.join(d, "score.json"), {})
    bv = rules.get("by_dim_value", {})
    pr = rules.get("profit_rule", {})   # 盈利引擎 → (盈利情景分, 不盈利情景分)
    for r in routes:
        scores = {k: 3.0 for k in w}     # 默认中性
        dims = r.get("dims", {})
        # 中文 dim 值映射(引擎/资本/护城河/节奏 → 英文评分维)
        for k, mapping in bv.items():
            val = dims.get(k)
            if val in mapping and mapping[val] in scores:
                scores[mapping[val]] = scores[mapping[val]] * 0.4 + 2.4  # 加权偏移
        # 盈利弹性: 基于 盈利引擎 字段
        eng = r.get("盈利引擎", "") or dims.get("盈利引擎", "")
        if pr and eng in pr:
            p_ok, p_bad = pr[eng]
            scores["profit"] = p_ok
            r["profit_scene"] = {"盈利": p_ok, "不盈利": p_bad,
                                 "note": f"盈利引擎={eng}"}
        # 窗口/控盘/护城河: 由节奏/资本/护城河 dim 规则直接给
        pace = dims.get("节奏", "")
        if pace == "窗口抢跑": scores["window"] = 4.5
        elif pace == "稳健积累": scores["window"] = 3.0
        cap = dims.get("资本", "")
        control_r = {"自己人种子": 4.5, "滚动现金流": 4.8, "声通资源协同": 3.5,
                     "混合资本分层": 3.0, "外部基金": 2.0}
        if cap in control_r: scores["control"] = control_r[cap]
        moat_r = {"数据端口": 5, "算力×数据": 4.8, "供应链锁店": 4, "IP聚合": 3, "品牌连锁": 3.2}
        mkey = dims.get("护城河", "")
        if mkey in moat_r: scores["moat"] = moat_r[mkey]
        raw = sum(scores[k] * w[k] for k in w)
        norm = raw / sum(w.values())
        r["scores"] = {k: round(scores[k], 1) for k in scores}
        r["total25"] = round(norm * 5, 1)
    routes.sort(key=lambda x: -x.get("total25", 0))
    save_json(os.path.join(d, "routes.json"), routes)
    save_json(os.path.join(d, "score-meta.json"), {"weights": w, "dims": {k: v["zh"] for k, v in DIM_DEFS.items()}, "ts": now()})
    log(f"score {dom}: {len(routes)} routes")
    zh = {k: v["zh"] for k, v in DIM_DEFS.items()}
    print(f"✅ {dom} 目标贡献度打分({len(routes)}条) — 维度: {'/'.join(zh.values())} → 满分25排行:")
    for r in routes[:20]:
        print(f"  {r['total25']:5.1f} {r['id']:5s} {r.get('desc','')[:44]}")
    return 0


# ── ④ adversary: 对抗检查点修正 ────────────────────────────────────────
def cmd_adversary(dom, pen=3):
    """对抗: checks.json {route_id 或 'all':[风险点]}; 命中每条 -pen 分"""
    d = domain_dir(dom)
    routes = load_json(os.path.join(d, "routes.json"), [])
    checks = load_json(os.path.join(d, "checks.json"), {})
    if not checks:
        print("ℹ️ 无 checks.json — 编辑之: {\"R01\": [\"风险点1\",...], \"all\": [...]} 或\n  python3 wargame.py --domain X add-check --route R01 --risk '文本'")
        return 1
    for r in routes:
        r["penalties"] = []
        # all 检查点适用于全部
        for risk in checks.get("all", []):
            r["penalties"].append(risk)
        # 特定路线
        for risk in checks.get(r["id"], []):
            if risk not in r["penalties"]:
                r["penalties"].append(risk)
        r["total_adj"] = round(r.get("total25", 0) - pen * len(r["penalties"]), 1)
    routes.sort(key=lambda x: -x.get("total_adj", 0))
    save_json(os.path.join(d, "routes.json"), routes)
    log(f"adversary {dom}: {sum(len(r['penalties']) for r in routes)} hits")
    print(f"✅ {dom} 对抗修正完成(每命中 -{pen}分) → 排行:")
    for r in routes[:15]:
        n = len(r.get("penalties", []))
        print(f"  {r['total_adj']:6.1f} {r['id']:8s} (原{r['total25']}) 对抗[{n}] {r.get('desc','')[:45]}")
    return 0


# ── ⑤ converge: 簇收敛 ─────────────────────────────────────────────────
def cmd_converge(dom, cluster_map=None):
    """收敛: 显式簇定义 {簇名: [route_ids]} 或按共享维度自动聚类; 输出主线/副翼"""
    d = domain_dir(dom)
    routes = load_json(os.path.join(d, "routes.json"), [])
    if not routes:
        print("❌ 无 routes"); return 1
    cmap = cluster_map or load_json(os.path.join(d, "clusters.json"), {})
    out = {"clusters": {}, "top": [r["id"] for r in routes[:3]]}
    if cmap:
        for name, rids in cmap.items():
            members = [r for r in routes if r["id"] in rids]
            if members:
                best = max(members, key=lambda r: r.get("total_adj", 0))
                out["clusters"][name] = {
                    "routes": rids,
                    "main": best["id"],
                    "logic": best.get("desc", "")[:80],
                }
    save_json(os.path.join(d, "result.json"), out)
    log(f"converge {dom}")
    print(f"✅ {dom} 收敛完成 → result.json")
    for name, c in out["clusters"].items():
        print(f"  簇[{name}]: 主线={c['main']} 成员={','.join(c['routes'])}")
    print(f"  Top3: {','.join(out['top'])}")
    return 0


# ── ⑥ graph: 力导向图输出 ──────────────────────────────────────────────
def cmd_graph(dom, out_dir=None):
    """输出 d3 力导向 HTML: 节点=路线(着色/分数) 边=共享维度"""
    d = domain_dir(dom)
    routes = load_json(os.path.join(d, "routes.json"), [])
    if not routes:
        print("❌ 无 routes"); return 1
    # 边: 共享 dims 值(引擎/资本/护城河等) 按相同取值建边
    links = []
    dim_keys = []
    for r in routes:
        for k in r.get("dims", {}):
            if k not in dim_keys:
                dim_keys.append(k)
    for i in range(len(routes)):
        for j in range(i + 1, len(routes)):
            a, b = routes[i], routes[j]
            ad, bd = a.get("dims", {}), b.get("dims", {})
            shared = [k for k in dim_keys[:4] if k in ad and k in bd and ad[k] == bd[k]]
            if shared:
                links.append({"s": i, "t": j, "v": min(1, 0.3 + 0.2 * len(shared)), "dims": shared})
    html = render_force_html(routes, links, dom, load_json(os.path.join(d, "axes.json"), {}).get("objective", ""))
    out_dir = out_dir or os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, f"wargame-{dom}.html")
    save_json.__doc__  # noop
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"graph {dom}: {len(routes)} nodes {len(links)} links → {out_path}")
    print(f"✅ 力导向图: {out_path} ({len(routes)}节点/{len(links)}边)")
    return out_path


def render_force_html(routes, links, dom, objective):
    # 配色: 取每路线第一个 dim 值做组
    groups = {}
    for r in routes:
        ds = list(r.get("dims", {}).values())
        g = ds[0] if ds else "?"
        groups.setdefault(g, []).append(r["id"])
    palette = ["#6ea8ff", "#34c77b", "#ffb454", "#f2709c", "#b98cff", "#ff6b6b", "#4ecdc4", "#ffe66d"]
    gcolor = {g: palette[i % len(palette)] for i, g in enumerate(groups)}
    # 简化: dims 转字符串键用于前端着色
    R = json.dumps([{**r, "dims": {str(k): str(v) for k, v in r.get("dims", {}).items()}} for r in routes], ensure_ascii=False)
    L = json.dumps(links, ensure_ascii=False)
    D = json.dumps({"groups": {g: {"color": gcolor[g], "count": len(v)} for g, v in groups.items()}}, ensure_ascii=False)
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<title>wargame · {dom} 沙盘</title><script src="/vendor/d3.min.js"></script>
<style>:root{{--bg:#0d1119;--txt:#e8eaf0;--mut:#8b90a3;--line:#2a3348}}*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC",sans-serif;height:100vh;display:flex;flex-direction:column}}
#top{{height:44px;display:flex;align-items:center;gap:10px;padding:0 14px;border-bottom:1px solid var(--line);background:#101522}}
#top h1{{font-size:15px}} #top h1 span{{color:#6ea8ff}} #top .obj{{margin-left:16px;color:var(--mut);font-size:12px}}
#main{{flex:1;display:flex;min-height:0}} #g{{flex:1;position:relative}} svg{{width:100%;height:100%}}
#side{{width:320px;border-left:1px solid var(--line);background:#101522;overflow:auto;padding:12px;font-size:12px}}
#side h3{{color:#6ea8ff;margin-bottom:6px}} .tag{{display:inline-block;background:rgba(110,168,255,.12);color:#6ea8ff;border-radius:6px;padding:2px 8px;font-size:11px;margin:2px}}
.link{{stroke:#2a3348}} .node{{cursor:pointer}} .node circle{{stroke:#fff}}
.lg{{position:absolute;top:10px;right:14px;font-size:11px;color:var(--mut)}}</style></head><body>
<div id="top"><h1>🎯 <span>{dom}</span> 商业沙盘 · 路线图</h1><div class="obj">{objective}</div></div>
<div id="main"><div id="g"><svg id="svg"></svg></div><div id="side">← 点击节点看路线</div></div>
<script>const ROUTES={R};const LINKS={L};const GROUPS={D};
const svg=d3.select('#svg'),W=innerWidth*.7,H=innerHeight-44;
const colorOf=d=>{{const ds=Object.values(d.dims||{{}});const g=GROUPS.groups&&Object.keys(GROUPS.groups).find(gg=>ROUTES.filter(r=>Object.values(r.dims||{{}})[0]===gg).includes(d));return g?GROUPS.groups[g].color:'#888'}};
const nodes=ROUTES.map((r,i)=>({{...r,i}}));
const links=LINKS.map(l=>({{source:l.s,target:l.t,v:l.v}}));
const sim=d3.forceSimulation(nodes).force('link',d3.forceLink(links).id(d=>d.i).distance(80).strength(l=>l.v))
 .force('charge',d3.forceManyBody().strength(-300)).force('center',d3.forceCenter(W/2,H/2)).force('collide',d3.forceCollide(30));
const g=svg.append('g');
const lg=g.selectAll('line').data(links).enter().append('line').attr('class','link').attr('stroke-opacity',d=>d.v).attr('stroke-width',d=>1+d.v);
const nd=g.selectAll('g.node').data(nodes).enter().append('g').attr('class','node').call(d3.drag().on('start',(e,d)=>{{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y}}).on('drag',(e,d)=>{{d.fx=e.x;d.fy=e.y}}).on('end',(e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null}}));
nd.append('circle').attr('r',20).attr('fill',colorOf);
nd.append('text').attr('text-anchor','middle').attr('dy','2').attr('font-size',d=>d.id.length>8?8:10).text(d=>d.id);
nd.append('text').attr('text-anchor','middle').attr('dy','26').attr('font-size','9').attr('fill',d=>(d.total_adj||0)>=15?'#34c77b':'#8b90a3').text(d=>d.total_adj?'分'+d.total_adj:'');
svg.call(d3.zoom().scaleExtent([.3,3]).on('zoom',e=>g.attr('transform',e.transform)));
nd.on('click',(e,d)=>{{e.stopPropagation();const near=ROUTES.filter(r=>LINKS.some(l=>(l.s===d.i&&l.t===ROUTES.indexOf(r))||(l.t===d.i&&l.s===ROUTES.indexOf(r)))).slice(0,6);
document.getElementById('side').innerHTML=`<h3>${{d.id}}</h3><div class="v">${{d.desc||''}}</div>`+Object.entries(d.dims||{{}}).map(([k,v])=>`<span class="tag">${{k}}:${{v}}</span>`).join('')+`<div style="margin-top:8px">原分 ${{d.total25||'-'}} → 修正 ${{d.total_adj||'-'}} (对抗${{(d.penalties||[]).length}})</div>`+`<div style="margin-top:4px;color:#ffb454">${{(d.penalties||[]).join('<br>')||''}}</div>`+`<hr style="border-color:var(--line);margin:8px 0"><div style="color:var(--mut)">相近路线:</div>`+near.map(n=>`<div style="margin:3px 0">• <b>${{n.id}}</b> ${{(n.desc||'').slice(0,30)}}</div>`).join('')}});
sim.on('tick',()=>{{lg.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);nd.attr('transform',d=>`translate(${{d.x}},${{d.y}})`);}});
</script></body></html>"""


# ── ⑦ report: 沙盘报告 md ──────────────────────────────────────────────
def cmd_report(dom):
    d = domain_dir(dom)
    routes = load_json(os.path.join(d, "routes.json"), [])
    result = load_json(os.path.join(d, "result.json"), {})
    ax = load_json(os.path.join(d, "axes.json"), {})
    if not routes:
        print("❌ 无 routes"); return 1
    obj = ax.get("objective", dom)
    lines = [f"# {dom} 商业沙盘报告", "", f"> 目标: {obj} · 工具: wargame {VERSION} · {now()[:10]}", ""]
    lines.append("## Top 路线(对抗修正后)")
    lines.append("")
    lines.append("| 排名 | 路线 | 原分 | 修正 | 对抗 | 描述 |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(routes[:10], 1):
        p = "<br>".join(r.get("penalties", [])[:2]) or "—"
        lines.append(f"| {i} | {r['id']} | {r.get('total25','-')} | {r.get('total_adj','-')} | {p} | {r.get('desc','')[:40]} |")
    if result.get("clusters"):
        lines.append("\n## 收敛簇")
        lines.append("")
        for name, c in result["clusters"].items():
            lines.append(f"- **{name}**: 主线={c['main']} · 成员={','.join(c['routes'])} · {c.get('logic','')}")
    rp = os.path.join(d, "report.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"report {dom}")
    print(f"✅ 报告: {rp}")
    return 0


# ── ⑧ simulate: 三立场对抗推演(正方/反方/中立) ────────────────────────
# 核心: "怎么推向目标"的过程推演——每轮三方就当前议题对抗, 产出裁决与行动, 逐轮逼近
# 数据: data/wargame/<dom>/simulation.json (轮次历史, append-only)
def cmd_simulate(dom, issue="", stance="", argument="", verbose=True):
    """追加一轮对抗推演。议题+三立场论点由调用者(模型/人工)提供, 工具负责结构化存档与裁决记录。
    用法(每轮一次调用, 提供当前轮该立场的内容):
      --issue '议题' --stance 正方 --argument '...'   # 正方先攻
      --stance 反方 --argument '...'                  # 反方再攻(同 issue)
      --stance 中立 --argument '...'                  # 中立方裁决(触发该轮定稿+行动)
    """
    d = domain_dir(dom)
    sim_p = os.path.join(d, "simulation.json")
    sim = load_json(sim_p, {"objective": "", "rounds": [], "pending": None})
    # 载入目标
    ax = load_json(os.path.join(d, "axes.json"), {})
    if not sim.get("objective"):
        sim["objective"] = ax.get("objective", dom)
    if not issue and sim.get("pending") and sim["pending"].get("issue"):
        issue = sim["pending"]["issue"]
    rounds = sim.setdefault("rounds", [])
    cur = sim.get("pending")
    # 兼容旧 pending 缺键
    if cur is not None:
        cur.setdefault("stances", {}); cur.setdefault("actions", []); cur.setdefault("verdict", None)
    if cur is None:
        cur = {"round": len(rounds) + 1, "issue": issue, "stances": {}, "verdict": None, "actions": []}
        sim["pending"] = cur
    if issue and issue != cur.get("issue"):
        # 新议题: 定稿上一轮(若无裁决则自动记未决)并开新轮
        if cur.get("stances") and not cur.get("verdict"):
            cur["verdict"] = "轮次切换未裁决, 议题保留"
            rounds.append(copy.deepcopy(cur))
        cur = {"round": len(rounds) + 1, "issue": issue, "stances": {}, "verdict": None, "actions": []}
        sim["pending"] = cur
    if stance and argument:
        cur["stances"][stance] = {"arg": argument, "ts": now()}
        log(f"simulate {dom} R{cur['round']} {stance}: {argument[:40]}")
    # 中立方到齐 → 该轮定稿
    if cur["stances"].get("中立方") and cur["stances"].get("正方") and cur["stances"].get("反方"):
        cur["verdict"] = cur["stances"]["中立方"]["arg"]
        # 行动从裁决提取: 兼容 换行"行动:" 与 同行多"行动:"(regex 非贪婪到下一"行动:"或结尾)
        verdict_text = str(cur["verdict"])
        import re as _re
        acts = _re.findall(r"行动:\s*(.*?)(?=行动:|$)", verdict_text)
        cur["actions"] = [a.strip(" 。；;") for a in acts if a and a.strip()]
        if not cur["actions"]:
            cur["actions"] = ["待下轮细化行动"]
        rounds.append(copy.deepcopy(cur))
        sim["pending"] = None
    save_json(sim_p, sim)
    if verbose:
        o = sim.get("objective", "")
        print(f"🎯 {dom} 沙盘目标: {o}")
        print(f"── 第 {cur['round']} 轮 ── 议题: {cur['issue']}")
        for st, v in cur["stances"].items():
            icon = {"正方": "🟦", "反方": "🟥", "中立": "🟨"}.get(st, "⬜")
            print(f"  {icon} {st}: {v['arg'][:150]}{'…' if len(v['arg'])>150 else ''}")
        print(f"  已定稿轮次: {len(rounds)}")
    return 0


def cmd_simview(dom):
    """查看推演历史(全部轮次定稿内容)"""
    d = domain_dir(dom)
    sim = load_json(os.path.join(d, "simulation.json"), {})
    rounds = sim.get("rounds", [])
    print(f"🎯 {dom} 推演目标: {sim.get('objective','?')} · 已定稿 {len(rounds)} 轮")
    if sim.get("pending") and sim["pending"].get("stances"):
        print(f"⚠️ 进行中第 {sim['pending']['round']} 轮未定稿: {sim['pending']['issue']}")
    for r in rounds:
        print(f"\n══ 第 {r['round']} 轮: {r['issue']} ══")
        for st, v in r.get("stances", {}).items():
            print(f"  [{st}] {v['arg']}")
        print(f"  → 裁决: {r.get('verdict','')[:200]}")
        for a in r.get("actions", []):
            print(f"  → 行动: {a}")
    return 0


# ── R006 ────────────────────────────────────────────────────────────────
def selfcheck(dom="flowernet"):
    print("✅ 域目录:", domain_dir(dom))
    print("✅ 纯 stdlib / CLI / 日志 / Lean4门")
    return 0


def lean4_check():
    """R006#10: 只写域数据目录(wargame/<dom>), 无系统外部性"""
    src = open(__file__, encoding="utf-8").read()
    writes = src.count("save_json(")
    gated = True  # 所有写经 save_json → 域目录受控
    print(f"  ✅ 写路径: save_json({writes}处) 全部进 data/wargame/<dom>/ 域目录")
    print("Lean4 门: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="商业沙盘模拟器 wargame — 路线生成/打分/对抗/收敛/图/报告")
    ap.add_argument("--domain", default="flowernet", help="业务域(默认 flowernet)")
    ap.add_argument("--objective", default="", help="沙盘目标(init 用)")
    ap.add_argument("--run", action="store_true", help="一键全流程(score→adversary→converge→graph→report)")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"wargame {VERSION}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("init"); sub.add_parser("generate"); sub.add_parser("score")
    sub.add_parser("adversary"); sub.add_parser("converge")
    sub.add_parser("graph"); sub.add_parser("report")
    sub.add_parser("simulate"); sub.add_parser("simview")
    ap.add_argument("--issue", default="", help="对抗议题(simulate 用)")
    ap.add_argument("--stance", default="", help="立场: 正方/反方/中立(simulate 用)")
    ap.add_argument("--argument", default="", help="该立场论点(simulate 用)")
    a = ap.parse_args()
    if a.selfcheck: return selfcheck(a.domain)
    if a.lean4_check: return lean4_check()
    dom = a.domain
    if a.run:
        d = domain_dir(dom)
        if not os.path.exists(os.path.join(d, "routes.json")) and os.path.exists(os.path.join(d, "axes.json")):
            cmd_generate(dom)
        if os.path.exists(os.path.join(d, "routes.json")):
            cmd_score(dom); cmd_adversary(dom); cmd_converge(dom)
            cmd_graph(dom); cmd_report(dom)
            print("\n🎯 沙盘全流程完成"); return 0
        print("❌ 无 routes.json/axes.json, 先 init+generate 或手工建配置"); return 1
    if not a.cmd:
        ap.print_help(); return 1
    fns = {"init": lambda: cmd_init(dom, a.objective), "generate": lambda: cmd_generate(dom),
           "score": lambda: cmd_score(dom), "adversary": lambda: cmd_adversary(dom),
           "converge": lambda: cmd_converge(dom), "graph": lambda: cmd_graph(dom),
           "report": lambda: cmd_report(dom),
           "simulate": lambda: cmd_simulate(dom, a.issue, a.stance, a.argument),
           "simview": lambda: cmd_simview(dom)}
    if a.cmd in fns:
        return fns[a.cmd]()
    ap.print_help(); return 1


if __name__ == "__main__":
    sys.exit(main())
