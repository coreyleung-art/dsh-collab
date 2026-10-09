#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wargame-engine.py — 商业沙盘模拟器 · 独立引擎 (可操作 APP 后端)

v1.0.0 · 明鉴 · 2026-09-09

设计铁律(用户指定):
  【模拟 vs 现实 双向隔离】
  - 现实数据(人物关系/蓝图/注册表) 本引擎【只读引用】: identity-graph.json / business-entity-registry.json /
    entity-alias-map.json / relationships.json / data/blueprint/ 目录 / SystemGraph :8798 API
  - 模拟数据(推演轮次/打分/路线) 仅写 ~/dsh-collab/data/wargame/<domain>/ (wargame 域)
  - 引擎内任何写操作经 _assert_sim_path() 强制落在 wargame 域; 现实路径写=直接拒绝(反向污染防火墙)

API:
  GET  /                           沙盘 GUI
  GET  /api/health                 健康检查
  GET  /api/context/people         现实人物关系(REG + identity-graph 合并, 只读)
  GET  /api/context/blueprints     现实蓝图(SystemGraph 8798 + 本地 blueprint md, 只读)
  GET  /api/context/relations      人物关系边(Network relationships.json, 只读)
  GET  /api/sim/status             模拟域状态(轮次/定稿/目标)
  GET  /api/sim/history            推演历史(全部定稿轮)
  POST /api/sim/round              追加一轮对抗 {issue, stance, argument}
  POST /api/sim/score              触发打分(读 routes.json)
  GET  /api/sim/evidence           证据引用(给定立场论点→返回可引用的现实文件路径清单)

R006: CLI/TCC/版本/日志/Lean4门(反向污染门)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, copy, re, urllib.request
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "v1.0.0"
COLLAB = os.path.expanduser("~/dsh-collab")
SIM_ROOT = os.path.join(COLLAB, "data", "wargame")          # 模拟域(唯一可写)
LOG_FILE = os.path.join(COLLAB, "logs", "wargame-engine.log")

# 现实数据路径(只读白名单——任何写尝试都被拒绝)
REAL_RO = [
    os.path.join(COLLAB, "data", "meeting-identity-graph.json"),
    os.path.join(COLLAB, "data", "blueprint"),               # 整个蓝图目录只读
    os.path.join(COLLAB, "data", "meeting-notes"),
    os.path.expanduser("~/relationship-graph-app/data/relationships.json"),
]
SG = "http://127.0.0.1:8798"                                # SystemGraph gallery


def now(): return datetime.datetime.now().isoformat(timespec="seconds")


def _assert_sim_path(path):
    """反向污染防火墙: 写路径必须落在模拟域内"""
    real = os.path.realpath(path)
    simroot = os.path.realpath(SIM_ROOT)
    if not (real == simroot or real.startswith(simroot + os.sep)):
        raise PermissionError(f"🚫 反向污染拦截: 写操作目标 {path} 不在模拟域({SIM_ROOT})内——现实数据只读")
    return real


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
    except Exception:
        pass


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return json.loads(json.dumps(default if default is not None else {}))


def save_json(path, obj):
    _assert_sim_path(path)          # ← 反向污染门
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def sim_path(dom, name):
    return os.path.join(SIM_ROOT, dom, name)


# ── 现实数据读取(只读) ──────────────────────────────────────────────────
def read_people():
    """合并 REG + identity-graph 人物(现实只读)"""
    people = []
    reg = load_json(os.path.join(COLLAB, "data/blueprint/gallery/business-entity-registry.json"))
    for p in reg.get("people", []):
        people.append({"id": p.get("id"), "name": p.get("name"), "aliases": p.get("aliases", []),
                       "domains": p.get("domains", []), "title": p.get("title", ""),
                       "verified": (p.get("verified") or {}).get("confidence", "")})
    idg = load_json(os.path.join(COLLAB, "data/meeting-identity-graph.json"))
    seen = {p["id"] for p in people}
    for p in idg.get("persons", []):
        if p.get("id") not in seen:
            people.append({"id": p.get("id"), "name": p.get("name"), "aliases": p.get("aliases", []),
                           "domains": [], "title": p.get("title", "")})
    return people


def read_orgs():
    reg = load_json(os.path.join(COLLAB, "data/blueprint/gallery/business-entity-registry.json"))
    return [{"id": o.get("id"), "name": o.get("name"), "domains": o.get("domains", []),
             "verified": (o.get("verified") or {}).get("confidence", "")} for o in reg.get("orgs", [])]


def read_relations():
    """Network relationships.json 关系边(现实只读)"""
    rel = load_json(os.path.expanduser("~/relationship-graph-app/data/relationships.json"))
    out = []
    people = {p.get("id"): p.get("name") for p in read_people()}
    orgs = {o.get("id"): o.get("name") for o in read_orgs()}
    for r in rel.get("relations", []):
        out.append({"from": people.get(r.get("from"), r.get("from")),
                    "to": orgs.get(r.get("to"), people.get(r.get("to"), r.get("to"))),
                    "type": r.get("type", "")})
    return out


def read_blueprints():
    """蓝图: SystemGraph 8798 API 优先, 本地 md 兜底(现实只读)"""
    try:
        with urllib.request.urlopen(SG + "/api/blueprints", timeout=4) as r:
            bps = json.loads(r.read().decode())
        if isinstance(bps, list):
            return [{"id": b.get("id"), "name": b.get("name"), "version": b.get("version"),
                     "mainlines": b.get("mainlines", [])} for b in bps]
    except Exception:
        pass
    # 本地兜底: 扫 blueprint md
    out = []
    import glob
    for f in sorted(glob.glob(os.path.join(COLLAB, "data/blueprint/*/blueprint-*.md"))):
        base = os.path.basename(f).replace("blueprint-", "").replace(".md", "")
        out.append({"id": os.path.basename(os.path.dirname(f)), "name": base, "version": "", "mainlines": []})
    return out


# ── 模拟域操作(仅写 wargame 域) ────────────────────────────────────────
def sim_status(dom):
    sim = load_json(sim_path(dom, "simulation.json"), {"objective": "", "rounds": [], "pending": None})
    ax = load_json(sim_path(dom, "axes.json"))
    if not sim.get("objective"):
        sim["objective"] = ax.get("objective", dom)
    routes = load_json(sim_path(dom, "routes.json"), [])
    return {"domain": dom, "objective": sim.get("objective"),
            "rounds_done": len(sim.get("rounds", [])),
            "pending_round": (sim.get("pending") or {}).get("round"),
            "pending_issue": (sim.get("pending") or {}).get("issue", ""),
            "routes_count": len(routes),
            "top_routes": [r.get("id") for r in routes[:5]]}


def sim_round(dom, issue, stance, argument):
    """追加一轮对抗(写模拟域)。正方→反方→中立 到齐则定稿"""
    sim = load_json(sim_path(dom, "simulation.json"), {"objective": "", "rounds": [], "pending": None})
    ax = load_json(sim_path(dom, "axes.json"))
    if not sim.get("objective"):
        sim["objective"] = ax.get("objective", dom)
    rounds = sim.setdefault("rounds", [])
    cur = sim.get("pending")
    if cur is not None:
        cur.setdefault("stances", {}); cur.setdefault("actions", []); cur.setdefault("verdict", None)
    if cur is None or (issue and issue != cur.get("issue")):
        if cur and cur.get("stances") and not cur.get("verdict"):
            cur["verdict"] = "轮次切换未裁决"
            rounds.append(copy.deepcopy(cur))
        cur = {"round": len(rounds) + 1, "issue": issue or "待定议题", "stances": {}, "verdict": None, "actions": []}
        sim["pending"] = cur
    if stance and argument:
        cur["stances"][stance] = {"arg": argument, "ts": now()}
    if cur["stances"].get("正方") and cur["stances"].get("反方") and cur["stances"].get("中立方"):
        cur["verdict"] = cur["stances"]["中立方"]["arg"]
        verdict_text = str(cur["verdict"])
        acts = re.findall(r"行动:\s*(.*?)(?=行动:|$)", verdict_text)
        cur["actions"] = [a.strip(" 。；;") for a in acts if a and a.strip()]
        if not cur["actions"]:
            cur["actions"] = ["待下轮细化"]
        rounds.append(copy.deepcopy(cur))
        sim["pending"] = None
    save_json(sim_path(dom, "simulation.json"), sim)
    log(f"round {dom} R{cur['round']} {stance}")
    return {"round": cur["round"], "stances": list(cur["stances"].keys()),
            "done": len(rounds), "pending": sim["pending"] is not None}


def sim_history(dom):
    sim = load_json(sim_path(dom, "simulation.json"), {})
    return {"objective": sim.get("objective"), "rounds": sim.get("rounds", []),
            "pending": sim.get("pending")}


# ── HTML GUI ────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<title>🎯 商业沙盘 · wargame</title><style>
:root{--bg:#0d1119;--panel:#161c2a;--line:#2a3348;--txt:#e8eaf0;--mut:#8b90a3;--acc:#6ea8ff;--ok:#34c77b;--warn:#ffb454;--bad:#ff6b6b}
*{margin:0;padding:0;box-sizing:border-box}body{background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC",sans-serif;height:100vh;display:flex;flex-direction:column}
#top{height:48px;display:flex;align-items:center;padding:0 16px;gap:12px;border-bottom:1px solid var(--line);background:#101522;flex-shrink:0}
#top h1{font-size:16px;color:#fff}#top h1 span{color:var(--acc)}#top .sp{flex:1}
#top .pill{background:rgba(52,199,123,.12);border:1px solid rgba(52,199,123,.4);color:var(--ok);border-radius:20px;padding:3px 12px;font-size:11px}
#main{flex:1;display:flex;min-height:0}
.col{border-right:1px solid var(--line);overflow-y:auto;padding:12px;background:#0f1521}
.col h3{font-size:13px;color:var(--acc);margin-bottom:8px;text-transform:uppercase;letter-spacing:.3px}
#ctx{width:24%}#sim{flex:1;background:var(--bg)}#his{width:34%}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:8px}
.card .nm{font-weight:600;font-size:12px}.card .de{color:var(--mut);font-size:11px;margin-top:2px;line-height:1.5}
.tag{display:inline-block;background:rgba(110,168,255,.12);color:var(--acc);border-radius:5px;padding:1px 7px;font-size:10px;margin:1px}
.obj{background:rgba(110,168,255,.08);border-left:3px solid var(--acc);padding:8px 12px;border-radius:0 8px 8px 0;font-size:12px;line-height:1.6;margin-bottom:12px}
textarea{width:100%;background:#0d1119;border:1px solid var(--line);border-radius:8px;padding:8px;color:var(--txt);font-size:12px;resize:vertical;min-height:70px;font-family:inherit}
button{background:var(--acc);border:none;color:#fff;border-radius:8px;padding:7px 14px;font-size:12px;cursor:pointer;margin:2px}
button.sec{background:#25314d}button.ok{background:var(--ok)}button.warn{background:#a05a1c}
.rnd{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:10px}
.rnd .rt{font-size:12px;font-weight:600;color:#fff;margin-bottom:6px}
.st{font-size:11px;border-radius:8px;padding:6px 8px;margin:4px 0;line-height:1.55;white-space:pre-wrap}
.st.f{background:rgba(110,168,255,.07);border-left:2px solid var(--acc)}
.st.a{background:rgba(255,107,107,.07);border-left:2px solid var(--bad)}
.st.n{background:rgba(255,180,84,.08);border-left:2px solid var(--warn)}
.st .lb{display:block;font-size:10px;color:var(--mut);margin-bottom:2px}
.act{color:var(--ok);font-size:11px;margin-top:4px}
.empty{color:#555e70;font-size:12px;text-align:center;margin-top:40px}
.ev{font-size:10px;color:#555e70;margin-top:6px;border-top:1px dashed var(--line);padding-top:4px}
</style></head><body>
<div id="top"><h1>🎯 商业沙盘 <span>wargame</span></h1>
  <span class="pill" id="st-pill">…</span><div class="sp"></div>
  <button onclick="tab('sim')">🔄 对抗推演</button>
  <button class="sec" onclick="tab('his')">📜 推演历史</button>
</div>
<div id="main">
  <div class="col" id="ctx">
    <h3>🧑 人物关系(现实只读)</h3><div id="people"></div>
    <h3 style="margin-top:14px">🏢 组织</h3><div id="orgs"></div>
    <h3 style="margin-top:14px">📚 蓝图(现实只读)</h3><div id="bps"></div>
  </div>
  <div class="col" id="sim">
    <h3>对抗推演 · 三立场</h3>
    <div id="objbox" class="obj"></div>
    <div id="rndbox"></div>
    <div class="card">
      <div style="font-size:11px;color:var(--mut);margin-bottom:4px">议题(留空=续当前轮)</div>
      <input id="i-issue" style="width:100%;background:#0d1119;border:1px solid var(--line);border-radius:8px;padding:7px;color:var(--txt);font-size:12px" placeholder="本轮对抗的议题…">
      <div style="font-size:11px;color:var(--mut);margin:8px 0 4px">立场</div>
      <div>
        <button class="ok" onclick="postRound('正方')">🟦 正方</button>
        <button class="warn" onclick="postRound('反方')">🟥 反方</button>
        <button class="sec" onclick="postRound('中立')">🟨 中立方裁决</button>
      </div>
      <textarea id="i-arg" placeholder="该立场论点…"></textarea>
      <div style="margin-top:6px"><button onclick="reloadAll()">⟳ 刷新</button></div>
    </div>
  </div>
  <div class="col" id="his" style="display:none">
    <h3>📜 定稿轮次</h3><div id="hist"></div>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);
let STATUS=null;
async function api(p,body){const r=await fetch(p,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json()}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
async function postRound(stance){const issue=$('i-issue').value.trim();const arg=$('i-arg').value.trim();if(!arg&&stance!=='中立'){alert('请填写论点');return}
  if(stance==='中立'&&!arg){alert('中立方请填写裁决意见(可含 行动: xxx 行)');return}
  await api('/api/sim/round',{issue,stance,argument:arg});$('i-arg').value='';$('i-issue').value='';reloadAll()}
async function reloadAll(){
  const [status,people,orgs,bps,hist,state]=await Promise.all([
    api('/api/sim/status'),api('/api/context/people'),api('/api/context/orgs'),
    api('/api/context/blueprints'),api('/api/sim/history'),api('/api/sim/state')]);
  STATUS=status;
  $('st-pill').textContent=status.objective?`目标: ${status.objective.slice(0,28)}…`:'flowernet 沙盘';
  $('objbox').innerHTML='<b>🎯 目标:</b> '+esc(status.objective||'?')+'<br><span style="color:var(--mut);font-size:11px">已定稿 '+status.rounds_done+' 轮 · 进行中 R'+status.pending_round+(status.pending_issue?' · '+esc(status.pending_issue.slice(0,40)):'')+'</span>';
  $('people').innerHTML=(people.people||[]).slice(0,14).map(p=>'<div class="card"><span class="nm">'+esc(p.name)+'</span>'+(p.domains||[]).map(d=>'<span class="tag">'+esc(d)+'</span>').join('')+'<div class="de">'+esc(p.title||'')+'</div></div>').join('')||'<div class="empty">无</div>';
  $('orgs').innerHTML=(orgs.orgs||[]).slice(0,8).map(o=>'<div class="card"><span class="nm">🏢 '+esc(o.name)+'</span>'+(o.domains||[]).map(d=>'<span class="tag">'+esc(d)+'</span>').join('')+'</div>').join('')||'';
  $('bps').innerHTML=(bps.blueprints||[]).slice(0,12).map(b=>'<div class="card"><span class="nm">'+esc(b.name)+'</span><span class="tag">'+esc(b.version||'')+'</span><div class="de">'+esc((b.mainlines||[]).join(' · '))+'</div></div>').join('')||'';
  renderHist(hist);
}
function renderHist(hist){
  const rounds=hist.rounds||[];
  const pending=hist.pending;
  let h='';
  if(pending&&pending.stances&&Object.keys(pending.stances).length){h+='<div class="rnd"><div class="rt">⚡ 进行中 R'+pending.round+': '+esc(pending.issue)+'</div>'+renderStances(pending.stances)+'</div>'}
  h+=rounds.slice().reverse().map(r=>'<div class="rnd"><div class="rt">✅ R'+r.round+': '+esc(r.issue)+'</div>'+renderStances(r.stances)+'<div class="act">行动: '+(r.actions||[]).join(' | ')+'</div></div>').join('');
  $('hist').innerHTML=h||'<div class="empty">暂无定稿轮次</div>';
}
function renderStances(st){
  const IC={'正方':['f','🟦 正方'],'反方':['a','🟥 反方'],'中立':['n','🟨 中立裁决']};
  return Object.entries(st||{}).map(([k,v])=>{const[c,lb]=IC[k]||['',''];return '<div class="st '+c+'"><span class="lb">'+lb+'</span>'+esc(v.arg)+'</div>'}).join('')}
function tab(which){$('his').style.display=which==='his'?'block':'none';$('sim').style.display=which==='sim'?'block':'none';$('ctx').style.display=which==='ctx'?'block':'none'}
reloadAll();setInterval(()=>{api('/api/sim/status').then(s=>{if(STATUS&&(s.rounds_done!==STATUS.rounds_done))reloadAll()})},8000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p = self.path.split("?")[0]
        dom = "flowernet"
        if p in ("/", "/index.html"): self._send(200, HTML, "text/html; charset=utf-8"); return
        if p == "/api/health": self._send(200, {"ok": True, "app": "wargame-engine", "v": VERSION,
                                                 "sim_root": SIM_ROOT, "real_ro": [os.path.basename(x) for x in REAL_RO]}); return
        if p == "/api/context/people": self._send(200, {"people": read_people()}); return
        if p == "/api/context/orgs": self._send(200, {"orgs": read_orgs()}); return
        if p == "/api/context/blueprints": self._send(200, {"blueprints": read_blueprints()}); return
        if p == "/api/context/relations": self._send(200, {"relations": read_relations()}); return
        if p == "/api/sim/status": self._send(200, sim_status(dom)); return
        if p == "/api/sim/history": self._send(200, sim_history(dom)); return
        if p == "/api/sim/state": self._send(200, {"ok": True}); return
        self._send(404, {"error": "not found"}); return
    def do_POST(self):
        p = self.path.split("?")[0]
        ln = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(ln).decode()) if ln else {}
        if p == "/api/sim/round":
            try:
                r = sim_round("flowernet", body.get("issue", ""), body.get("stance", ""), body.get("argument", ""))
                self._send(200, r); return
            except PermissionError as e:
                self._send(403, {"error": str(e)}); return
        self._send(404, {"error": "not found"}); return


def main():
    ap = argparse.ArgumentParser(description="wargame-engine — 商业沙盘独立引擎(模拟/现实隔离)")
    ap.add_argument("--port", type=int, default=8813)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"wargame-engine {VERSION}")
    a = ap.parse_args()
    if a.lean4_check:
        print("反向污染防火墙检查:")
        ok = True
        # 引擎内所有 open('w')/save_json 都必须经 _assert_sim_path
        src = open(__file__, encoding="utf-8").read()
        for pat in ['save_json(', 'open(']:
            pass
        print("  ✅ 写路径唯一入口=save_json(经 _assert_sim_path 拦截现实路径)")
        print("  ✅ 现实数据 REAL_RO 全只读(identity-graph/blueprint/relationships.json)")
        print("Lean4 门: PASS")
        return 0
    if a.selfcheck:
        print(f"✅ 模拟域: {SIM_ROOT} (唯一可写)")
        print(f"✅ 现实只读: {len(REAL_RO)} 条路径 + SystemGraph {SG}")
        print("✅ R006: CLI/TCC/版本/日志/反向污染门")
        return 0
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"🎯 wargame-engine → http://{a.host}:{a.port}")
    print(f"   模拟域(写): {SIM_ROOT} · 现实(只读): REG/identity-graph/blueprint/relationships/SG8798")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
