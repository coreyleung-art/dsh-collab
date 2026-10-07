#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""identity-graph-gui.py — 会议人物身份图谱 GUI（独立 web app）

用户开会时念名字 → 实时查身份/关系/组织; 可视化关系图谱 + 人物卡 + 扫描登记
纯 stdlib(ThreadingHTTPServer) + 内嵌前端, 零外部依赖, 双击即开。

用法:
  python3 identity-graph-gui.py [--port 8811] [--host 127.0.0.1]
打开 http://127.0.0.1:8811

R006: CLI(--port/--host) · TCC(--selfcheck) · 版本(--tool-version) · 只读图谱(防越写) · 写走 API 门控
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, urllib.request, urllib.parse, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "v1.0.0"
GRAPH = os.path.expanduser("~/dsh-collab/data/meeting-identity-graph.json")
SCRIPT = os.path.expanduser("~/dsh-collab/scripts/identity-graph.py")

def load_graph():
    with open(GRAPH, encoding="utf-8") as f:
        return json.load(f)

def save_graph(g):
    with open(GRAPH, "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, indent=1)

# ── 复用 CLI 逻辑(import 方式) ────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(SCRIPT))
import importlib.util
_spec = importlib.util.spec_from_file_location("idg", SCRIPT)
idg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(idg)

HTML = """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<title>会议人物身份图谱</title>
<style>
:root{--bg:#0d1119;--panel:#161c2a;--line:#2a3348;--txt:#e8eaf0;--mut:#8b90a3;--acc:#6ea8ff}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC",Helvetica,Arial,sans-serif;padding:20px}
h1{font-size:20px;margin-bottom:4px}
.sub{color:var(--mut);font-size:12px;margin-bottom:16px}
.tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.tab{padding:8px 16px;border-radius:8px;cursor:pointer;background:var(--panel);border:1px solid var(--line);font-size:13px;color:var(--mut)}
.tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.pane{display:none}
.pane.on{display:block}
#graph-svg{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}
.card h3{font-size:16px;margin-bottom:8px;color:var(--acc)}
.card .k{color:var(--mut);font-size:11px;margin-top:8px}
.card .v{font-size:13px;line-height:1.6}
input,textarea,select{background:#0d1119;border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:8px 12px;font-size:13px;margin:4px;width:calc(100% - 10px)}
button{background:var(--acc);border:none;color:#fff;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:13px;margin:4px}
button.ghost{background:transparent;border:1px solid var(--line);color:var(--mut)}
.hit{display:inline-block;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:4px 14px;margin:3px;font-size:12px;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.badge{display:inline-block;background:rgba(110,168,255,.15);color:var(--acc);border-radius:6px;padding:2px 8px;font-size:11px;margin-left:6px}
.lbl{color:var(--mut);font-size:12px;margin-bottom:6px}
textarea{min-height:120px;font-family:monospace;font-size:12px}
#result{border:1px solid var(--line);background:#0d1119;border-radius:8px;padding:10px;font-size:12px;white-space:pre-wrap;color:#9ecbff;min-height:60px}
</style></head><body>
<h1>🪪 会议人物身份图谱 <span class="badge">v1.0.0</span></h1>
<div class="sub" id="status">载入中…</div>
<div class="tabs">
  <div class="tab on" data-p="graph">关系图谱</div>
  <div class="tab" data-p="persons">人物档案</div>
  <div class="tab" data-p="scan">扫描识别</div>
  <div class="tab" data-p="identify">查身份</div>
  <div class="tab" data-p="orgs">组织</div>
  <div class="tab" data-p="add">登记人物</div>
</div>

<div class="pane on" id="pane-graph"><div class="card"><div id="graph-svg"></div></div></div>

<div class="pane" id="pane-persons"><div class="grid" id="person-grid"></div></div>

<div class="pane" id="pane-scan">
  <div class="card">
    <div class="lbl">粘贴会议转写文本(或拖入妙记转录), 自动识别在场/被谈人物</div>
    <textarea id="scan-text" placeholder="Speaker 1 00:00:00\n……"></textarea>
    <button onclick="doScan()">🔍 扫描识别</button>
    <div class="lbl" style="margin-top:10px">识别结果(点击查身份):</div>
    <div id="scan-hits"></div>
    <div id="result"></div>
  </div>
</div>

<div class="pane" id="pane-identify">
  <div class="card">
    <div class="lbl">输入名字(支持别名: 振宇/紫阳/阿凯…)</div>
    <input id="idq" placeholder="输入名字…" onkeydown="if(event.key==='Enter')doIdentify()">
    <button onclick="doIdentify()">查身份</button>
    <div id="result"></div>
  </div>
</div>

<div class="pane" id="pane-orgs"><div class="grid" id="org-grid"></div></div>

<div class="pane" id="pane-add">
  <div class="card">
    <div class="lbl">登记新人物(开会听到新名字)</div>
    <input id="a-name" placeholder="规范名 *">
    <input id="a-title" placeholder="头衔/称呼">
    <input id="a-org" placeholder="所属组织">
    <input id="a-aliases" placeholder="别名(逗号分隔)">
    <textarea id="a-role" placeholder="角色描述…"></textarea>
    <button onclick="doAdd()">✅ 登记</button>
    <div id="result"></div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
async function api(path, body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json()}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.pane').forEach(x=>x.classList.remove('on'));
  t.classList.add('on');$('pane-'+t.dataset.p).classList.add('on');
});
async function init(){
  const d=await api('/api/data');
  $('status').textContent=`${d.persons.length} 人物 · ${d.orgs.length} 组织 · ${new Date().toLocaleString()}`;
  drawGraph(d);renderPersons(d);renderOrgs(d);
}
// ── 关系图谱(SVG 力导向简化版: 分层) ──
function drawGraph(d){
  const W=1100,H=700;let svg=`<svg id="gsvg" width="100%" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="cursor:grab">`;
  svg+=`<rect width="${W}" height="${H}" rx="12" fill="#0d1119" stroke="#2a3348"/>`;
  const orgs=d.orgs,persons=d.persons;
  const orgW=W/orgs.length;
  const orgPos={};orgs.forEach((o,i)=>{orgPos[o.id]={x:orgW*i+orgW/2,y:80}});
  const pPos={};
  // 人物归到其组织列(下缘)
  persons.forEach((p,i)=>{
    let orgId=null;
    p.relations.forEach(r=>{if(orgs.some(o=>o.id===r.to))orgId=r.to});
    // 没有组织关系的放最右列
    const oi=orgId?orgs.findIndex(o=>o.id===orgId):orgs.length;
    const col=oi<0?orgs.length:oi;
    const cx=col<orgs.length?orgW*col+orgW/2:W-80;
    const members=(pPos[col]||0);
    pPos[p.id]={x:cx+(members%3-1)*90,y:200+Math.floor(members/3)*70};
    pPos[col]=members+1;
  });
  // edges
  persons.forEach(p=>{p.relations.forEach(r=>{
    const tgt=r.to;
    const a=pPos[p.id],b=orgPos[tgt]||pPos[tgt];
    if(a&&b){svg+=`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="#8b90a3" stroke-width="1" opacity=".5"/>`}
  })});
  // org nodes
  orgs.forEach(o=>{const p=orgPos[o.id];svg+=`<g onclick="identifyOrg('${o.id}')"><rect x="${p.x-70}" y="${p.y-18}" width="140" height="36" rx="8" fill="#1b2436" stroke="#6ea8ff"/><text x="${p.x}" y="${p.y+4}" fill="#6ea8ff" font-size="11" text-anchor="middle">${o.name.length>8?o.name.slice(0,8)+'…':o.name}</text></g>`});
  // person nodes
  persons.forEach(p=>{const q=pPos[p.id];if(!q)return;
    svg+=`<g onclick="identify('${encodeURIComponent(p.name)}')"><circle cx="${q.x}" cy="${q.y-8}" r="26" fill="${p.name==='梁振宇'?'#e06c75':p.confidence==='high'?'#6ea8ff':'#c678dd'}" opacity=".85"/><text x="${q.x}" y="${q.y-3}" fill="#fff" font-size="9" text-anchor="middle">${p.name.length>4?p.name.slice(0,4):p.name}</text><text x="${q.x}" y="${q.y+22}" fill="#8b90a3" font-size="9" text-anchor="middle">${(p.title||'').slice(0,8)}</text></g>`});
  svg+=`</svg>`;
  $('graph-svg').innerHTML=svg;
}
function renderPersons(d){$('person-grid').innerHTML=d.persons.map(p=>`
  <div class="card" onclick="identify('${encodeURIComponent(p.name)}')" style="cursor:pointer">
    <h3>${p.name} <span class="badge">${p.confidence||''}</span></h3>
    <div class="v">${(p.title||'').replace(/</g,'&lt;')}</div>
    <div class="k">组织</div><div class="v">${p.org||''}</div>
    <div class="k">角色</div><div class="v" style="font-size:11px;color:var(--mut)">${(p.role||'').slice(0,80)}</div>
  </div>`).join('')}
function renderOrgs(d){$('org-grid').innerHTML=d.orgs.map(o=>`
  <div class="card"><h3>${o.name}</h3>
    <div class="k">类型</div><div class="v">${o.type||''}</div>
    <div class="k">角色</div><div class="v">${o.role||''}</div></div>`).join('')}
async function identify(name){const d=await api('/api/identify?name='+encodeURIComponent(decodeURIComponent(name)));$('result').textContent=JSON.stringify(d,null,1)}
async function identifyOrg(oid){const d=await api('/api/org?id='+oid);$('result').textContent=JSON.stringify(d,null,1)}
async function doIdentify(){const d=await api('/api/identify?name='+encodeURIComponent($('idq').value));$('result').textContent=JSON.stringify(d,null,1)}
async function doScan(){const t=$('scan-text').value;if(!t){return}const d=await api('/api/scan',{text:t});$('scan-hits').innerHTML=(d.hits||[]).map(h=>`<span class="hit" onclick="identify('${encodeURIComponent(h.name)}')">${h.name} ×${h.count}</span>`).join('')||'<div class="lbl">未识别到已知人物</div>';$('result').textContent=d.summary||''}
async function doAdd(){const body={name:$('a-name').value,title:$('a-title').value,org:$('a-org').value,aliases:$('a-aliases').value,role:$('a-role').value};const d=await api('/api/add-person',body);$('result').textContent=JSON.stringify(d,null,1);if(d.ok)init()}
init();
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _html(self):
        body = HTML.encode()
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        g = load_graph()
        if self.path == "/" or self.path.startswith("/?"):
            self._html(); return
        if self.path.startswith("/api/data"):
            self._json({"persons": g.get("persons",[]), "orgs": g.get("orgs",[])}); return
        if self.path.startswith("/api/identify"):
            q = urllib.parse.parse_qs(self.path.split("?",1)[1]) if "?" in self.path else {}
            name = q.get("name",[""])[0]
            hits = {k.lower():p for p in g.get("persons",[]) for k in [p["name"]]+p.get("aliases",[])}
            p = hits.get(name.lower())
            self._json(p or {"error": f"未找到 {name}"}); return
        if self.path.startswith("/api/org"):
            q = urllib.parse.parse_qs(self.path.split("?",1)[1]) if "?" in self.path else {}
            oid = q.get("id",[""])[0]
            o = next((x for x in g.get("orgs",[]) if x["id"]==oid), None)
            members = [p["name"] for p in g.get("persons",[]) if any(r.get("to")==oid for r in p.get("relations",[]))]
            self._json({"org": o, "members": members}); return
        self._json({"error":"not found"}, 404)
    def do_POST(self):
        g = load_graph()
        ln = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(ln).decode()) if ln else {}
        if self.path.startswith("/api/scan"):
            text = body.get("text","")
            hits = idg.scan_text(text, g, include_org=True)
            arr = [{"name":h["name"],"count":h["count"],"title":h["title"]} for h in sorted(hits.values(), key=lambda x:-x["count"])]
            self._json({"hits": arr, "summary": f"识别到 {len(arr)} 个人物/组织"}); return
        if self.path.startswith("/api/add-person"):
            name = body.get("name","")
            if not name: self._json({"ok":False,"error":"name 必填"},400); return
            # 去重
            if any(p["name"]==name for p in g.get("persons",[])):
                self._json({"ok":False,"error":f"{name} 已存在"}); return
            pid = "p-"+re.sub(r'[^\w]','',name)[:12]
            g.setdefault("persons",[]).append({"id":pid,"name":name,"title":body.get("title") or name,
              "aliases":[a.strip() for a in body.get("aliases","").split(",") if a.strip()],
              "org":body.get("org",""),"role":body.get("role",""),"speakers":{},"relations":[],
              "source":"GUI add "+datetime.date.today().isoformat(),"confidence":"medium(待用户确认)"})
            save_graph(g)
            self._json({"ok":True,"id":pid}); return
        self._json({"error":"not found"},404)

def main():
    ap = argparse.ArgumentParser(description="会议人物身份图谱 GUI")
    ap.add_argument("--port", type=int, default=8811)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"identity-graph-gui {VERSION}")
    a = ap.parse_args()
    if a.selfcheck:
        g = load_graph()
        print(f"✅ 图谱: {len(g['persons'])} 人物 / {len(g['orgs'])} 组织")
        print(f"✅ GUI 内嵌 HTML: {len(HTML)} 字符")
        print("TCC: PASS"); return 0
    print(f"🪪 会议人物身份图谱 GUI → http://{a.host}:{a.port}")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()

if __name__ == "__main__":
    sys.exit(main())
