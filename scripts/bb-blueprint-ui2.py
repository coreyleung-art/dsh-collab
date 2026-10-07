#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-ui2.py — FlowerNet 蓝图可视化 GUI v2（可缩放/平移/三条主线）

用户指示（2026-08-31）：给 flowernet 蓝图一个可放大缩小的独立 GUI app。
升级：① 三条主线（digital/physical/supply 动态渲染）② 画布缩放（滚轮/按钮/触摸板）③ 平移拖拽 ④ 子阶段状态色 + 子步展开 ⑤ 实时数据（黑板 8792）

用法：python3 bb-blueprint-ui2.py --port 8797
访问：http://127.0.0.1:8797/
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, urllib.request, datetime, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BB = "http://127.0.0.1:8792"

def fetch(path):
    try:
        with urllib.request.urlopen(BB + "/" + path.lstrip("/"), timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def h(s):
    return html.escape(str(s))

def build_page():
    stages = fetch("data/blueprint/stages").get("value", {})
    works = fetch("data/blueprint/works").get("value", {}).get("blueprint_map", [])
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stage_list = stages.get("stages", [])
    works_by_stage = {}
    for w in works:
        works_by_stage.setdefault(w.get("stage"), []).append(w)
    mains = stages.get("mainlines", {})

    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
    st_color = {"done": "#34c77b", "active": "#34c77b", "partial": "#f5b942", "todo": "#7d8596"}

    # 渲染一条主线（三级折叠：主线/主阶段/子阶段）
    def render_mainline(mid):
        meta = mains.get(mid, {})
        title = meta.get("name", mid)
        desc = meta.get("desc", "")
        m_stages = [s for s in stage_list if s.get("mainline") == mid]
        rows = ""
        for s in m_stages:
            color = st_color.get(s.get("status"), "#7d8596")
            icon = st_icon.get(s.get("status"), "⬜")
            sid = h("ms-" + s.get("id",""))
            subs = ""
            for ss in s.get("substages", []):
                sc = st_color.get(ss.get("status"), "#7d8596")
                sic = st_icon.get(ss.get("status"), "⬜")
                ssid = h("st-" + ss.get("id",""))
                ws = works_by_stage.get(ss.get("id"), [])
                w_html = ""
                for w in ws:
                    w_html += '<div class="w-item"><span class="w-name">%s</span><span class="w-owner">%s</span><span class="w-st %s">%s</span></div>' % (
                        h(w.get("work","")), h(w.get("owner","")), w.get("status","todo"),
                        st_icon.get(w.get("status","todo"), "⬜"))
                steps_html = ""
                for sb in ss.get("substeps", []):
                    steps_html += '<div class="substep">↳ %s %s [%s] dep=%s</div>' % (
                        h(sb.get("id","")), h(sb.get("name","")), st_icon.get(sb.get("status","todo"),"⬜"), h(str(sb.get("dep","-"))))
                subs += '<div class="stage" style="border-left:3px solid %s"><div class="stage-head">%s <b>%s</b> <span class="muted">%s</span> <span class="fold-btn" onclick="toggleFold(&quot;%s&quot;)">▼</span></div><div class="fold-body" id="%s">%s%s</div></div>' % (
                    sc, sic, h(ss.get("id","")+" "+ss.get("name","")), h(ss.get("note","")[:60]), ssid, ssid, w_html, steps_html)
            rows += '<div class="main-stage" style="border-left:3px solid %s"><div class="stage-head">%s <b>%s %s</b> <span class="fold-btn" onclick="toggleFold(&quot;%s&quot;)">▼</span></div><div class="fold-body" id="%s">%s</div></div>' % (
                color, icon, h(s.get("stage","")), h(s.get("name","")), sid, sid, subs)
        mid_btn = "mlb-" + h(mid)
        return '<div class="ml" id="ml-%s"><div class="ml-title"><span class="fold-btn" onclick="toggleFold(&quot;%s&quot;)">▼</span> %s <span class="muted">%s</span></div><div class="fold-body" id="%s">%s</div></div>' % (
            h(mid), mid_btn, h(title), h(desc), mid_btn, rows)

    ml_html = ""
    for mid in mains.keys():
        ml_html += render_mainline(mid)

    # ── 鱼骨图（石川图）：目标 ← 主线(大骨) ← 主阶段(中骨) ← 子阶段(小骨) ──
    def render_fishbone():
        """双鱼骨图：物理鱼（实体世界）+ 虚拟鱼（数字世界），各可交互"""
        W, H = 1700, 1040
        st_icon_f = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
        st_color_f = {"done": "#34c77b", "active": "#34c77b", "partial": "#f5b942", "todo": "#7d8596"}
        # 维度颜色
        dim_colors = {"physical": "#34c77b", "supply": "#f5b942", "digital": "#6ea8ff"}

        def render_one_fish(fish_id, title, dim_ids, goal, spine_y, head_y, color_base):
            """渲染一条鱼：主干+鱼头+大骨(主阶段)+中骨(子阶段)+小骨(子步)"""
            parts = []
            spine_x0, spine_x1 = 160, 1520
            # 主干
            parts.append(f'<line x1="{spine_x0}" y1="{spine_y}" x2="{spine_x1}" y2="{spine_y}" stroke="{color_base}" stroke-width="6" opacity="0.7"/>')
            # 鱼头（目标）
            head_x = spine_x1 + 40
            parts.append(f'<polygon points="{head_x},{head_y-70} {head_x+90},{head_y} {head_x},{head_y+70}" fill="{color_base}" opacity="0.9"/>')
            parts.append(f'<text x="{head_x-12}" y="{head_y-14}" fill="#fff" font-size="16" font-weight="bold" text-anchor="end">{html.escape(title)}</text>')
            gx = head_x - 12
            gy = head_y + 12
            for gl in goal:
                parts.append(f'<text x="{gx}" y="{gy}" fill="#eaf2ff" font-size="12" text-anchor="end">{html.escape(gl)}</text>')
                gy += 20
            # 维度名标注（鱼尾侧）
            parts.append(f'<text x="{spine_x0}" y="{spine_y-16}" fill="{color_base}" font-size="15" font-weight="bold">{html.escape(title)}</text>')
            # 大骨 = 该维度下的主阶段
            m_stages = [s for s in stage_list if s.get("mainline") in dim_ids]
            n = len(m_stages)
            anchors = [(spine_x0 + (spine_x1 - spine_x0) * (j + 0.6) / (n + 0.3)) for j in range(n)] if n else []
            for j, s in enumerate(m_stages):
                ax, ay = anchors[j], spine_y
                dir_y = -1 if j % 2 == 0 else 1   # 上下交替
                bx = ax - 120
                by = ay + 120 * dir_y
                sc = st_color_f.get(s.get("status"), "#7d8596")
                m_id = f"fm-{fish_id}-{s.get('id','')}"
                sub_id = f"fs-{fish_id}-{s.get('id','')}"
                mx, my = (ax + bx) / 2, (ay + by) / 2
                rot = 40 if dir_y < 0 else -40
                parts.append(f'<g class="fish-main" id="{m_id}" onclick="toggleFish(&quot;{sub_id}&quot;)" style="cursor:pointer">'
                             f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{sc}" stroke-width="5"/>'
                             f'<text x="{mx}" y="{my}" fill="{sc}" font-size="15" font-weight="bold" text-anchor="middle" transform="rotate({rot} {mx} {my})">{html.escape(s.get("stage","")+" "+s.get("name",""))}</text>'
                             f'<text x="{mx+18}" y="{my-12}" font-size="11" fill="#8b90a3">▾</text>'
                             f'</g>')
                # 中骨 = 子阶段（沿大骨分布）
                subs = s.get("substages", [])
                mid_parts = []
                for k, ss in enumerate(subs):
                    f2 = (k + 0.6) / (len(subs) + 0.3) if subs else 0.5
                    cx = ax + (bx - ax) * f2
                    cy = ay + (by - ay) * f2
                    cdir = 1 if dir_y < 0 else -1
                    ex = cx
                    ey = cy + 52 * cdir
                    ssc = st_color_f.get(ss.get("status"), "#7d8596")
                    ss_id = f"fst-{fish_id}-{ss.get('id','')}"
                    ssub_id = f"fss-{fish_id}-{ss.get('id','')}"
                    mid_parts.append(f'<g class="fish-stage" id="{ss_id}" onclick="toggleFish(&quot;{ssub_id}&quot;)" style="cursor:pointer">'
                                     f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" stroke="{ssc}" stroke-width="3"/>'
                                     f'<text x="{ex}" y="{ey}" fill="{ssc}" font-size="12" text-anchor="middle" dy="{-6 if cdir<0 else 14}">{html.escape(ss.get("id","")+" "+ss.get("name","")[:14])}</text>'
                                     f'<text x="{ex+24}" y="{ey}" font-size="9" fill="#8b90a3">▸</text>'
                                     f'</g>')
                    # 小骨 = 子步（默认折叠）
                    step_parts = []
                    for m2, sb in enumerate(ss.get("substeps", [])):
                        ssc2 = st_color_f.get(sb.get("status","todo"), "#7d8596")
                        kx = ex + 36
                        ky = ey + (m2 - (len(ss.get("substeps",[]))-1)/2) * 17 * cdir
                        step_parts.append(f'<text x="{kx}" y="{ky}" fill="{ssc2}" font-size="10">{html.escape(sb.get("id",""))}</text>')
                    if step_parts:
                        mid_parts.append(f'<g class="fish-sub" id="{ssub_id}" style="display:none">{"".join(step_parts)}</g>')
                parts.append(f'<g class="fish-subs" id="{sub_id}">{"".join(mid_parts)}</g>')
            return "".join(parts)

        # 两条鱼：物理（含供应链）+ 虚拟（数字化）
        parts = []
        # 物理鱼（上）：实体世界
        parts.append(render_one_fish("phy", "物理鱼 · 实体世界", ["physical", "supply"],
                                     ["无人产线", "千店网络", "供应链融资"], 300, 300, "#34c77b"))
        # 虚拟鱼（下）：数字世界
        parts.append(render_one_fish("dig", "虚拟鱼 · 数字世界", ["digital"],
                                     ["垂直引擎", "数据飞轮", "端侧自动化"], 780, 780, "#6ea8ff"))
        # 图例
        lx = 60
        for k, (stt, ic) in enumerate([("done","✅"),("active","🟢"),("partial","🟡"),("todo","⬜")]):
            parts.append(f'<text x="{lx}" y="{H-20}" fill="#8b90a3" font-size="12">{ic} {stt}</text>')
            lx += 90
        parts.append(f'<text x="{lx}" y="{H-20}" fill="#8b90a3" font-size="12">点击骨头展开/收起</text>')
        return f'<div class="view" id="view-fishbone" style="display:none"><svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="background:#0d1119;border-radius:14px;border:1px solid #232a3a">{"".join(parts)}</svg></div>'

    def render_timeline():
        rows = ""
        # 从 schedule 或 stages 生成时间线（按主阶段排列，标状态）
        order = list(mains.keys())
        all_stages = []
        for mid in order:
            for s in stage_list:
                if s.get("mainline") == mid:
                    all_stages.append((mid, s))
        for mid, s in all_stages:
            color = st_color.get(s.get("status"), "#7d8596")
            icon = st_icon.get(s.get("status"), "⬜")
            subs = " ".join(f'<span class="tl-sub" style="color:{st_color.get(ss.get("status"),"#7d8596")}">{html.escape(ss.get("id",""))}</span>' for ss in s.get("substages", []))
            rows += f'<div class="tl-item" style="border-left:3px solid {color}"><div class="tl-head">{icon} <b>{html.escape(s.get("stage",""))} {html.escape(s.get("name",""))}</b> <span class="muted">{html.escape(s.get("desc",""))}</span></div><div class="tl-subs">{subs}</div></div>'
        return f'<div class="view" id="view-timeline" style="display:none"><div class="tl-wrap">{rows}</div></div>'

    def render_relations():
        """关系图谱：5 蓝图依赖图（节点=蓝图，边=关系类型，SVG）"""
        import urllib.request as _ur
        W, H = 1400, 640
        try:
            with _ur.urlopen("http://127.0.0.1:8792/data/blueprint/relations", timeout=6) as r:
                rel = json.loads(r.read().decode()).get("value", {})
        except Exception:
            rel = {}
        bps = rel.get("blueprints", ["flowernet", "flowernet-platform", "agent-network", "blueprint-platform", "aistartup"])
        edges = rel.get("edges", [])
        # 布局：5 节点环形/网格
        dims = {"flowernet": "业务", "aistartup": "业务", "flowernet-platform": "技术", "agent-network": "底座", "blueprint-platform": "元层"}
        colors = {"flowernet": "#6ea8ff", "aistartup": "#34c77b", "flowernet-platform": "#f5b942", "agent-network": "#e06c75", "blueprint-platform": "#c678dd"}
        n = len(bps)
        cx, cy = W/2, H/2
        R = 200
        positions = {}
        for i, b in enumerate(bps):
            ang = -90 + i * (360 / n)
            import math
            x = cx + R * math.cos(math.radians(ang))
            y = cy + R * math.sin(math.radians(ang))
            positions[b] = (x, y)
        parts = []
        # 边（关系）
        for e in edges:
            frm, to = e["from"], e["to"]
            if frm not in positions or to not in positions: continue
            x1, y1 = positions[frm]; x2, y2 = positions[to]
            etype = e["type"]
            ecolor = {"contains": "#8b90a3", "depends_on": "#e06c75", "requires": "#f5b942",
                      "consumes": "#34c77b", "manages": "#6ea8ff", "references": "#c678dd"}.get(etype, "#8b90a3")
            parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{ecolor}" stroke-width="2" stroke-dasharray="6 3" opacity="0.8"/>')
            mx, my = (x1+x2)/2, (y1+y2)/2
            parts.append(f'<text x="{mx}" y="{my-4}" fill="{ecolor}" font-size="10" text-anchor="middle">{etype}</text>')
        # 节点（蓝图，可点击→提示）
        for b in bps:
            x, y = positions[b]
            color = colors.get(b, "#6ea8ff")
            dim = dims.get(b, "?")
            parts.append(f'<circle cx="{x}" cy="{y}" r="42" fill="{color}" opacity="0.85" stroke="#0b0e14" stroke-width="2"/>')
            parts.append(f'<text x="{x}" y="{y-6}" fill="#fff" font-size="13" font-weight="bold" text-anchor="middle">{b[:14]}</text>')
            parts.append(f'<text x="{x}" y="{y+12}" fill="#fff" font-size="10" text-anchor="middle">{dim}</text>')
        # 图例
        lx = 40
        for k, (t, ic) in enumerate([("contains","⊃"),("depends_on","→依赖"),("requires","→要求"),("consumes","→消费"),("manages","→管理"),("references","→引用")]):
            parts.append(f'<text x="{lx}" y="{H-16}" fill="#8b90a3" font-size="11">{ic} {t}</text>')
            lx += 130
        return f'<div class="view" id="view-relations" style="display:none"><svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="background:#0d1119;border-radius:14px;border:1px solid #232a3a">{"".join(parts)}</svg></div>'

    cur = h(stages.get("current_position", ""))
    gate = h(stages.get("gate", ""))
    ver = h(str(stages.get("version", "")))

    TPL = """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FlowerNet 蓝图 v__VER__ · 可视化中枢</title>
<style>
:root{--bg:#0b0e14;--card:#141824;--line:#232a3a;--fg:#e8eaf0;--muted:#8b90a3;--acc:#6ea8ff}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,'PingFang SC',sans-serif;overflow:hidden;height:100vh}
#toolbar{position:fixed;top:0;left:0;right:0;height:52px;background:rgba(20,24,36,.95);border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 16px;gap:10px;z-index:100;backdrop-filter:blur(8px)}
#toolbar h1{font-size:16px;font-weight:700;margin-right:12px}
#toolbar .muted{color:var(--muted);font-size:12px}
.btn{background:var(--card);border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:4px 12px;font-size:13px;cursor:pointer}
.btn:hover{border-color:var(--acc)}
#zoom-info{color:var(--muted);font-size:12px;min-width:60px;text-align:center}
#canvas-wrap{position:fixed;top:52px;left:0;right:0;bottom:0;overflow:hidden;background:radial-gradient(ellipse at 50% 0%,#10152a 0%,#0b0e14 60%)}
#canvas{transform-origin:0 0;transition:transform .05s ease;padding:24px;width:1600px}
.ml{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:18px;max-width:1540px}
.ml-title{font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.main-stage{padding:12px 14px;margin-bottom:10px;background:#101420;border-radius:10px}
.stage{padding:10px 12px;margin:8px 0 8px 14px;background:#0d1119;border-radius:8px}
.stage-head{display:flex;align-items:center;gap:6px;font-size:13px;margin-bottom:4px;flex-wrap:wrap}
.w-item{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);padding:3px 0 3px 16px;border-bottom:1px dashed var(--line)}
.w-name{flex:1;color:var(--fg)}
.w-owner{color:var(--acc);font-size:11px;margin-right:8px}
.substep{font-size:11px;color:var(--muted);padding:2px 0 2px 16px}
.muted{color:var(--muted);font-size:11px}
.fold-btn{display:inline-block;cursor:pointer;color:var(--acc);font-size:12px;padding:0 4px;border-radius:4px;user-select:none;transition:transform .15s}
.fold-btn:hover{background:rgba(110,168,255,.15)}
.fold-btn.collapsed{transform:rotate(-90deg)}
.fold-body{transition:opacity .15s}
.view{min-width:1400px}
.view-btn.active{background:var(--acc);border-color:var(--acc);color:#fff}
.tl-wrap{padding:8px}
.tl-item{background:var(--card);border-radius:10px;padding:12px 14px;margin-bottom:10px}
.tl-head{display:flex;align-items:center;gap:8px;font-size:14px;margin-bottom:6px;flex-wrap:wrap}
.tl-subs{display:flex;gap:8px;flex-wrap:wrap}
.tl-sub{background:#101420;border:1px solid var(--line);border-radius:5px;padding:2px 8px;font-size:11px}
.legend{display:flex;gap:14px;font-size:12px;color:var(--muted)}
#pos-card{position:fixed;bottom:14px;right:14px;background:rgba(20,24,36,.92);border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:12px;max-width:380px;z-index:99;line-height:1.7}
#pos-card b{color:var(--acc)}
</style></head><body>
<div id="toolbar">
  <h1>🌸 FlowerNet 蓝图 v__VER__</h1>
  <span class="muted">__NOW__</span>
  <div style="flex:1"></div>
  <div class="legend"><span>✅done</span><span>🟢active</span><span>🟡partial</span><span>⬜todo</span></div>
  <button class="btn" onclick="zoomBy(1.2)">➕</button>
  <span id="zoom-info">100%</span>
  <button class="btn" onclick="zoomBy(0.8)">➖</button>
  <div style="display:flex;gap:6px;border:1px solid var(--line);border-radius:8px;padding:3px">
  <button class="btn view-btn active" id="vb-flow" onclick="switchView('flow')">🌲 流程图</button>
  <button class="btn view-btn" id="vb-fish" onclick="switchView('fishbone')">🐟 鱼骨图</button>
  <button class="btn view-btn" id="vb-timeline" onclick="switchView('timeline')">📅 时间线</button>
  <button class="btn view-btn" id="vb-relations" onclick="switchView('relations')">🔗 关系图谱</button>
</div>
  <button class="btn" onclick="expandAll()">全部展开</button>
  <button class="btn" onclick="collapseAll()">全部收起</button>
  <button class="btn" onclick="resetView()">复位</button>
  <button class="btn" onclick="fitView()">适配</button>
</div>
<div id="canvas-wrap">
  <div id="canvas">__ML__</div>
</div>
<div id="pos-card">📍 <b>当前位置：</b>__CUR__<br>🚦 <b>门禁：</b>__GATE__</div>
<script>
function toggleFish(id){
  var el = document.getElementById(id);
  if(!el) return;
  el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}
function switchView(name){
  document.querySelectorAll('.view').forEach(v=>v.style.display='none');
  document.querySelectorAll('.view-btn').forEach(b=>b.classList.remove('active'));
  var v = document.getElementById('view-'+name);
  if(v) v.style.display='block';
  var b = document.getElementById('vb-'+name);
  if(b) b.classList.add('active');
  setTimeout(fitView, 50);
}
function toggleFold(id){
  var el = document.getElementById(id);
  if(!el) return;
  var btn = el.previousElementSibling;
  while(btn && !btn.classList.contains('fold-btn')){ btn = btn.previousElementSibling; }
  if(el.style.display === 'none'){ el.style.display = 'block'; if(btn) btn.classList.remove('collapsed'); }
  else { el.style.display = 'none'; if(btn) btn.classList.add('collapsed'); }
}
function expandAll(){ document.querySelectorAll('.fold-body').forEach(e=>{e.style.display='block';}); document.querySelectorAll('.fold-btn').forEach(b=>b.classList.remove('collapsed')); }
function collapseAll(){ document.querySelectorAll('.fold-body').forEach(e=>{e.style.display='none';}); document.querySelectorAll('.fold-btn').forEach(b=>b.classList.add('collapsed')); }
let scale = 1, tx = 0, ty = 0, dragging = false, startX = 0, startY = 0;
const canvas = document.getElementById('canvas');
const wrap = document.getElementById('canvas-wrap');
function apply(){canvas.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;document.getElementById('zoom-info').textContent = Math.round(scale*100)+'%';}
function zoomBy(f, cx, cy){if(cx===undefined){cx=wrap.clientWidth/2;cy=wrap.clientHeight/2;}const ns = Math.min(4, Math.max(0.2, scale*f));tx = cx - (cx-tx)*(ns/scale);ty = cy - (cy-ty)*(ns/scale);scale = ns;apply();}
function resetView(){scale=1;tx=0;ty=0;apply();}
function fitView(){const sw = canvas.scrollWidth, sh = canvas.scrollHeight;const s = Math.min(1, Math.min(wrap.clientWidth/sw, wrap.clientHeight/sh)*0.95);scale=s;tx=20;ty=20;apply();}
wrap.addEventListener('wheel', e=>{e.preventDefault();zoomBy(e.deltaY<0?1.1:0.9, e.clientX, e.clientY);},{passive:false});
wrap.addEventListener('mousedown', e=>{dragging=true;startX=e.clientX-tx;startY=e.clientY-ty;canvas.style.cursor='grabbing';});
window.addEventListener('mousemove', e=>{if(dragging){tx=e.clientX-startX;ty=e.clientY-startY;apply();}});
window.addEventListener('mouseup', ()=>{dragging=false;canvas.style.cursor='default';});
// 触摸板双指缩放
wrap.addEventListener('gesturestart', e=>e.preventDefault());
wrap.addEventListener('gesturechange', e=>{e.preventDefault();zoomBy(e.scale>1?1.02:0.98);});
fitView();
</script></body></html>"""
    fish = render_fishbone()
    tl = render_timeline()
    rel_v = render_relations()
    return (TPL.replace("__VER__", ver).replace("__NOW__", now)
                .replace("__ML__", '<div class="view" id="view-flow">' + ml_html + '</div>' + fish + tl + rel_v)
                .replace("__CUR__", cur).replace("__GATE__", gate))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = build_page().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8797)
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    args = ap.parse_args()
    if args.selfcheck:
        import ast as _ast
        try:
            _ast.parse(open(__file__).read())
            print("✅ 语法 OK")
        except SyntaxError:
            print("❌ 语法"); sys.exit(1)
        print("TCC: PASS")
        sys.exit(0)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"🌸 FlowerNet 蓝图 GUI: http://127.0.0.1:{args.port}/  (Ctrl+C 停止)")
    srv.serve_forever()
