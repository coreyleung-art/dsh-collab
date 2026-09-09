#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-dashboard.py v3 — 黑板看板（双视角：人类版 + AI 版）

用户建议（2026-08-23）：看板分成两个——
  GET /    → 人类版：业务语言、一眼看懂（谁在线/各业务多少记录/最近动态/整体健康）
  GET /ai  → AI 版：技术数据、完整细节（时钟seq/时间轴/订阅/注册表/队列/原始JSON）

用法：python3 bb-dashboard.py --port 8798
  人类版 http://127.0.0.1:8798/
  AI 版  http://127.0.0.1:8798/ai
"""
import argparse, json, urllib.request, datetime, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BB = "http://127.0.0.1:8792"

def fetch(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:100]}

def h(s):
    return html.escape(str(s))

# ───────────────────── 人类版 ─────────────────────
def build_human():
    clock = fetch("/clock"); nodes = fetch("/nodes"); tl = fetch("/timeline?limit=10")
    subs = fetch("/subs"); data = fetch("/data"); tasks = fetch("/tasks")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    seq = clock.get("seq", "?"); bb_ts = (clock.get("ts") or "")[11:19]

    # 设备
    node_rows, node_count = "", 0
    if isinstance(nodes, dict) and nodes.get("list"):
        for k, v in nodes["list"].items():
            if "/heartbeat" in k: continue
            node_count += 1
            name = k.replace("nodes/", "")
            hb = nodes["list"].get(k + "/heartbeat"); online = False; when = ""
            if hb:
                try:
                    hb_ts = hb.get("value", {}).get("ts", "")
                    online = (datetime.datetime.now() - datetime.datetime.fromisoformat(hb_ts)).total_seconds() < 180
                    when = hb_ts[11:19]
                except Exception: pass
            dot = '<span style="color:%s">●</span>' % ("#34c77b" if online else "#ff5c5c")
            node_rows += '<div class="row">%s <a href="/node/%s" style="color:var(--acc);text-decoration:none"><b>%s</b></a> <span class="muted">%s</span></div>' % (
                dot, h(name), h(name), ("在线 · 心跳 " + when) if online else "离线")

    # 业务消息量
    ns_rows = ""
    if isinstance(data, dict) and data.get("list"):
        counts = {}
        for k in data["list"]:
            parts = k.split("/"); ns = parts[1] if len(parts) > 1 else "?"
            counts[ns] = counts.get(ns, 0) + 1
        names = {"recovery": "恢复/自查", "iterations": "迭代记录", "erp": "ERP 对接", "i9": "i9 节点",
                 "frameworks": "框架登记", "learning": "学习", "qa": "QA 验收", "media": "媒体",
                 "ops": "运营", "ingest": "文档摄取", "registry": "资源登记", "investigate": "数据调查",
                 "supply-chain": "供应链", "customer-service": "客服", "tasks": "任务", "ack": "确认",
                 "projects": "项目", "external-link": "外链", "timeline": "时间轴"}
        for ns, c in sorted(counts.items(), key=lambda x: -x[1]):
            label = names.get(ns, ns)
            ns_rows += '<div class="row"><span>%s</span><span class="badge">%s 条</span></div>' % (h(label), c)

    # 最近动态（业务化）
    evt_rows = ""
    if isinstance(tl, dict) and tl.get("events"):
        for e in tl["events"][-8:]:
            key = e.get("key", ""); op = e.get("op", ""); biz = key
            for a, b in [("data/recovery/", "恢复自查·"), ("data/iterations/", "迭代·"), ("tasks/i9/", "i9任务·"),
                         ("nodes/", "节点·"), ("data/erp/", "ERP·"), ("notes/", "通知·")]:
                if key.startswith(a): biz = b + key[len(a):]; break
            op_cn = {"PUT": "写入", "DELETE": "删除"}.get(op, op)
            evt_rows += '<div class="evt"><span class="op">%s</span><span>%s</span></div>' % (op_cn, h(biz))

    sub_count = len(subs.get("subs", [])) if isinstance(subs, dict) else 0
    q_count = 0
    if isinstance(tasks, dict) and tasks.get("list"):
        q_count = len([k for k in tasks["list"] if "/queue/" in k])

    return """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>协作黑板 · 总览</title>
<style>
:root{--bg:#10131a;--card:#171b26;--line:#262c3a;--fg:#e8eaf0;--muted:#98a0b3;--acc:#6ea8ff}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;padding:24px;max-width:1100px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}.sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}
.card h2{font-size:14px;color:var(--muted);margin-bottom:12px;font-weight:600}
.row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px dashed var(--line);font-size:14px}
.row:last-child{border:none}.muted{color:var(--muted);font-size:12px}
.badge{background:rgba(110,168,255,.15);color:var(--acc);padding:2px 10px;border-radius:20px;font-size:12px}
.evt{display:flex;gap:10px;padding:5px 0;border-bottom:1px dashed var(--line);font-size:13px}
.evt .op{color:var(--acc);min-width:34px}.big{font-size:30px;font-weight:700;color:var(--acc)}
.tip{background:rgba(110,168,255,.08);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin-bottom:20px;font-size:14px;line-height:1.8;color:var(--muted)}
.ai-link{position:fixed;top:20px;right:20px;color:var(--muted);font-size:12px;background:var(--card);border:1px solid var(--line);padding:6px 14px;border-radius:20px;text-decoration:none}
</style></head><body>
<a class="ai-link" href="/ai">🤖 AI 技术版 →</a>
<h1>📋 协作黑板 · 总览</h1>
<div class="sub">所有智能体共用的「公告板」· 每 8 秒刷新 · 现在 %(now)s</div>
<div class="tip"><b style="color:var(--fg)">这是什么？</b><br>
黑板上所有智能体（运营/客服/QA/学习/i9节点…）共用的公告板：谁在干活、干到哪、最新动态，都在这里。<br>
<b style="color:var(--fg)">看哪里？</b> ① 谁在线 ② 各业务多少条记录 ③ 最近发生了什么。想看技术细节点右上角「AI 技术版」。</div>
<div class="cards">
<div class="card"><h2>⏱ 黑板时钟</h2><div class="big">%(seq)s</div>
<div class="muted" style="margin-top:6px">最新事件号（全网唯一顺序）</div><div class="muted">服务器时间：%(bb_ts)s</div></div>
<div class="card"><h2>🖥 设备在线（%(node_count)s 台）</h2>%(node_rows)s</div>
<div class="card"><h2>📦 各业务消息量</h2>%(ns_rows)s</div>
<div class="card"><h2>🔔 事件通知桥</h2>
<div class="row"><span>订阅通道</span><span class="badge">%(sub_count)s 条</span></div>
<div class="row"><span>待处理任务卡</span><span class="badge">%(q_count)s 张</span></div>
<div class="muted" style="margin-top:8px;line-height:1.7">设备订阅黑板，有变化自动通知，不用反复询问。</div></div>
<div class="card" style="grid-column:1/-1"><h2>🕘 最近动态</h2>%(evt_rows)s</div>
</div></body></html>""" % {"now": now, "seq": seq, "bb_ts": bb_ts, "node_count": node_count,
        "node_rows": node_rows, "ns_rows": ns_rows, "evt_rows": evt_rows,
        "sub_count": sub_count, "q_count": q_count}

# ───────────────────── AI 版 ─────────────────────
def build_ai():
    clock = fetch("/clock"); nodes = fetch("/nodes"); tl = fetch("/timeline?limit=20")
    subs = fetch("/subs"); nsreg = fetch("/ns-registry"); data = fetch("/data"); tasks = fetch("/tasks")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    seq = clock.get("seq", "?"); bb_ts = clock.get("ts", "?")

    # 时钟+时间轴
    evt_rows = ""
    if isinstance(tl, dict) and tl.get("events"):
        for e in tl["events"][-15:]:
            evt_rows += '<div class="mono">%s <b class="op">%s</b> %s</div>' % (h(e.get("seq","")), h(e.get("op","")), h(e.get("key","")))

    # 节点技术
    node_rows = ""
    if isinstance(nodes, dict) and nodes.get("list"):
        for k, v in nodes["list"].items():
            if "/heartbeat" in k: continue
            caps = ",".join((v.get("value") or {}).get("capabilities", []))
            node_rows += '<div class="mono">%s <span class="muted">[%s]</span></div>' % (h(k.replace("nodes/","")), h(caps))

    # 订阅
    sub_rows = ""
    if isinstance(subs, dict) and subs.get("subs"):
        for s in subs["subs"]:
            sub_rows += '<div class="mono">%s → <span class="muted">%s</span></div>' % (h(s["topic"]), h(s["callback"]))

    # 注册表
    reg_rows = ""
    if isinstance(nsreg, dict) and nsreg.get("registry"):
        for i, (sid, info) in enumerate(nsreg["registry"].items()):
            reg_rows += '<div class="mono">%s <span class="muted">%s</span> → <b>%s</b></div>' % (h(sid), h(info.get("role","")), h(info.get("ns","")))

    # 队列
    q_rows = ""
    if isinstance(tasks, dict) and tasks.get("list"):
        for k in sorted(tasks["list"]):
            if "/queue/" in k:
                q_rows += '<div class="mono">%s</div>' % h(k)

    # 原始数据（精简）
    raw = json.dumps({"clock": clock, "subs_count": len(subs.get("subs",[])) if isinstance(subs,dict) else 0,
                      "ns_registry": len(nsreg.get("registry",{})) if isinstance(nsreg,dict) else 0,
                      "data_keys": len(data.get("list",{})) if isinstance(data,dict) else 0}, ensure_ascii=False)

    return """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>黑板 · AI 技术版</title>
<style>
:root{--bg:#0d0f14;--card:#141720;--line:#232837;--fg:#d8dce6;--muted:#7d8596;--acc:#8ab4ff;--ok:#34c77b;--warn:#f5b942}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;padding:24px;max-width:1200px;margin:0 auto;font-size:13px}
h1{font-size:18px;margin-bottom:4px}.sub{color:var(--muted);font-size:12px;margin-bottom:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h2{font-size:12px;color:var(--muted);margin-bottom:10px;letter-spacing:.5px}
.mono{font-size:12px;padding:3px 0;border-bottom:1px dashed var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mono:last-child{border:none}
.op{color:var(--acc)}.muted{color:var(--muted)}
.big{font-size:24px;font-weight:700;color:var(--acc)}
.human-link{position:fixed;top:20px;right:20px;color:var(--muted);font-size:12px;background:var(--card);border:1px solid var(--line);padding:6px 14px;border-radius:20px;text-decoration:none}
</style></head><body>
<a class="human-link" href="/">👀 人类版 →</a>
<h1>🤖 黑板 · AI 技术版</h1>
<div class="sub">全局时钟 / 时间轴 / 订阅 / 注册表 / 队列 · 刷新 %(now)s · seq=%(seq)s · server=%(bb_ts)s</div>
<div class="cards">
<div class="card"><h2>⏱ 全局时钟</h2><div class="big">%(seq)s</div><div class="muted">HLC 全局唯一 seq（物理秒×10⁶+逻辑计数）</div></div>
<div class="card"><h2>🖥 节点（capabilities）</h2>%(node_rows)s</div>
<div class="card"><h2>🔔 订阅者</h2>%(sub_rows)s</div>
<div class="card"><h2>🗂 职责命名空间注册表</h2>%(reg_rows)s</div>
<div class="card" style="grid-column:1/-1"><h2>🕘 时间轴（最近 15）</h2>%(evt_rows)s</div>
<div class="card"><h2>📥 任务队列</h2>%(q_rows)s</div>
<div class="card"><h2>📊 原始摘要</h2><div class="mono">%(raw)s</div></div>
</div></body></html>""" % {"now": now, "seq": seq, "bb_ts": bb_ts, "node_rows": node_rows,
        "sub_rows": sub_rows, "reg_rows": reg_rows, "evt_rows": evt_rows,
        "q_rows": q_rows or '<div class="mono muted">无队列卡</div>', "raw": h(raw)}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, build_human(), "text/html; charset=utf-8")
        elif self.path in ("/ai", "/ai/"):
            self._send(200, build_ai(), "text/html; charset=utf-8")
        elif self.path in ("/blueprint", "/blueprint/"):
            self._send(200, build_blueprint(), "text/html; charset=utf-8")
        elif self.path.startswith("/node/"):
            # 节点视角：/node/i9 人类版 + /node/i9/ai AI版
            nid = self.path[len("/node/"):].rstrip("/").split("/")[0]
            is_ai = "/ai" in self.path
            self._send(200, build_node(nid, ai=is_ai), "text/html; charset=utf-8")
        elif self.path.startswith("/api/"):
            target = self.path[len("/api/"):]
            try:
                with urllib.request.urlopen(BB + "/" + target, timeout=6) as r:
                    self._send(r.status, r.read(), "application/json")
            except Exception as ex:
                self._send(502, json.dumps({"error": str(ex)[:120]}), "application/json")
        else:
            self._send(404, "not found", "text/plain")
    def log_message(self, *a):
        pass


# ───────────────────── 蓝图可视化（管理中枢）─────────────────────
def build_blueprint():
    """蓝图看板：双主线 × 阶段，工作挂载、状态可视化"""
    stages = fetch("/data/blueprint/stages").get("value", {})
    works = fetch("/data/blueprint/works").get("value", {}).get("blueprint_map", [])
    now = datetime.datetime.now().strftime("%H:%M:%S")

    stage_list = stages.get("stages", [])
    works_by_stage = {}
    for w in works:
        works_by_stage.setdefault(w.get("stage"), []).append(w)

    # 状态样式
    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
    st_color = {"done": "#34c77b", "active": "#34c77b", "partial": "#f5b942", "todo": "#7d8596"}

    # 主线分组渲染（主阶段 → 子阶段 → 工作）
    def render_mainline(mid, title, desc):
        m_stages = [s for s in stage_list if s.get("mainline") == mid]
        rows = ""
        for s in m_stages:
            icon = st_icon.get(s.get("status"), "⬜")
            color = st_color.get(s.get("status"), "#7d8596")
            ws = works_by_stage.get(s.get("id"), [])
            w_html = ""
            for w in ws:
                w_html += '<div class="w-item"><span class="w-name">%s</span><span class="w-owner">%s</span></div>' % (h(w.get("work","")), h(w.get("owner","")))
            # 子阶段
            subs = s.get("substages", [])
            sub_html = ""
            for ss in subs:
                sic = st_icon.get(ss.get("status"), "⬜")
                scolor = st_color.get(ss.get("status"), "#7d8596")
                ssws = works_by_stage.get(ss.get("id"), [])
                ssw_html = ""
                for w in ssws:
                    ssw_html += '<div class="w-item" style="padding-left:34px"><span class="w-name">%s</span><span class="w-owner">%s</span></div>' % (h(w.get("work","")), h(w.get("owner","")))
                sub_html += '<div class="stage" style="margin-left:14px;border-left:3px solid %s;background:#10131a"><div class="stage-head"><span class="stage-icon">%s</span><b>%s</b> <span class="muted">%s</span></div>%s</div>' % (
                    scolor, sic, h(ss.get("name","")), h(ss.get("note","")), ssw_html)
            active_cls = ' stage-cur' if s.get("status") in ("active","partial") else ''
            rows += '<div class="stage%s" style="border-left:3px solid %s"><div class="stage-head"><span class="stage-icon">%s</span><b>%s</b> <span class="muted">%s</span></div>%s%s</div>' % (
                active_cls, color, icon, h(s.get("stage","")+" "+s.get("name","")), h(s.get("note","")), w_html, sub_html)
        return '<div class="ml"><div class="ml-title">%s <span class="muted">%s</span></div>%s</div>' % (h(title), h(desc), rows)

    dline = render_mainline("digital", stages.get("mainlines",{}).get("digital",{}).get("name","数字化"), stages.get("mainlines",{}).get("digital",{}).get("desc",""))
    pline = render_mainline("physical", stages.get("mainlines",{}).get("physical",{}).get("name","物理"), stages.get("mainlines",{}).get("physical",{}).get("desc",""))

    cur_pos = stages.get("current_position", "")
    gate = stages.get("gate", "")

    return """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>花店蓝图 · 管理中枢</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--line:#2a2e3d;--fg:#e6e8ee;--muted:#8b90a3;--acc:#5b8cff;--ok:#34c77b;--warn:#f5b942}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;padding:24px;max-width:1200px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}.sub{color:var(--muted);font-size:13px;margin-bottom:16px}
.pos{background:rgba(91,140,255,.1);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:14px}
.pos b{color:var(--acc)}
.ml{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
.ml-title{font-size:15px;font-weight:700;margin-bottom:12px}
.stage{padding:10px 14px;margin-bottom:10px;background:#141722;border-radius:8px}
.stage-head{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.stage-cur{background:rgba(52,199,123,.06)}
.stage-icon{font-size:14px}
.w-item{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);padding:3px 0 3px 22px;border-bottom:1px dashed var(--line)}
.w-item:last-child{border:none}
.w-owner{color:var(--acc)}
.muted{color:var(--muted);font-size:12px}
.back{position:fixed;top:20px;right:20px;color:var(--muted);font-size:12px;background:var(--card);border:1px solid var(--line);padding:6px 14px;border-radius:20px;text-decoration:none}
.legend{display:flex;gap:16px;font-size:12px;color:var(--muted);margin-bottom:16px}
.legend span{display:flex;align-items:center;gap:4px}
</style></head><body>
<a class="back" href="/">← 总览</a>
<h1>🌷 花店蓝图 · 管理中枢</h1>
<div class="sub">双主线 × 阶段 · 工作挂载 · 状态可视化 · 刷新 %(now)s</div>
<div class="pos">📍 当前位置：<b>%(cur_pos)s</b><br>🚦 决策门禁：%(gate)s</div>
<div class="legend"><span>✅ 完成</span><span>🟢 进行中</span><span>🟡 部分/雏形</span><span>⬜ 待启动</span></div>
%(dline)s
%(pline)s
</body></html>""" % {"now": now, "cur_pos": h(cur_pos), "gate": h(gate), "dline": dline, "pline": pline}

# ───────────────────── 节点视角（卡点关注）─────────────────────
def build_node(nid, ai=False):
    """节点视角看板：聚焦单个节点（i9/门店）的卡点"""
    tasks = fetch("/tasks?node=%s" % nid)
    nodes = fetch("/nodes")
    tl = fetch("/timeline?limit=20")
    clock = fetch("/clock")
    now = datetime.datetime.now().strftime("%H:%M:%S")
    seq = clock.get("seq", "?")

    # 节点状态
    node_online = "?"
    hb = nodes.get("list", {}).get("nodes/%s/heartbeat" % nid)
    if hb:
        try:
            hb_ts = hb.get("value", {}).get("ts", "")
            node_online = "在线" if (datetime.datetime.now() - datetime.datetime.fromisoformat(hb_ts)).total_seconds() < 180 else "离线"
        except Exception:
            node_online = "?"
    else:
        node_online = "未注册"

    # 卡点统计
    queue_keys = [k for k in (tasks.get("list", {}) or {}) if "/queue/" in k]
    result_keys = [k for k in (tasks.get("list", {}) or {}) if "/result" in k]
    # 队列卡明细（含 task_id）
    queue_rows = ""
    for k in sorted(queue_keys)[:10]:
        v = tasks["list"][k].get("value", {})
        tid = v.get("task_id", "?")
        action = v.get("action", "?")
        queue_rows += '<div class="row"><span class="mono">%s</span><span class="muted">%s</span></div>' % (
            h(tid), h(action))
    if not queue_rows:
        queue_rows = '<div class="row"><span class="ok-text">✅ 无积压任务卡</span></div>'

    # 最近该节点相关事件（动态）
    evt_rows = ""
    node_events = [e for e in (tl.get("events") or []) if nid in e.get("key", "")]
    for e in node_events[-8:]:
        op_cn = {"PUT": "写入", "DELETE": "删除"}.get(e.get("op", ""), e.get("op", ""))
        evt_rows += '<div class="evt"><span class="op">%s</span><span class="mono">%s</span></div>' % (op_cn, h(e.get("key", "")))
    if not evt_rows:
        evt_rows = '<div class="row"><span class="muted">暂无最近事件</span></div>'

    if ai:
        # AI 技术版节点视角
        return """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>节点 %(nid)s · AI</title>
<style>
:root{--bg:#0d0f14;--card:#141720;--line:#232837;--fg:#d8dce6;--muted:#7d8596;--acc:#8ab4ff;--ok:#34c77b;--warn:#f5b942;--err:#ff5c5c}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:ui-monospace,Menlo,monospace;padding:24px;max-width:1100px;margin:0 auto;font-size:13px}
h1{font-size:18px;margin-bottom:4px}.sub{color:var(--muted);font-size:12px;margin-bottom:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h2{font-size:12px;color:var(--muted);margin-bottom:10px}
.mono{font-size:12px;padding:3px 0;border-bottom:1px dashed var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.op{color:var(--acc)}.muted{color:var(--muted)}
.big{font-size:24px;font-weight:700;color:var(--acc)}
.back{position:fixed;top:20px;right:20px;color:var(--muted);font-size:12px;background:var(--card);border:1px solid var(--line);padding:6px 14px;border-radius:20px;text-decoration:none}
</style></head><body>
<a class="back" href="/">← 总览</a>
<h1>🤖 节点 %(nid)s · AI 技术版</h1>
<div class="sub">seq=%(seq)s · 状态=%(node_online)s · 刷新 %(now)s</div>
<div class="cards">
<div class="card"><h2>📥 任务卡队列（%(qcount)s）</h2>%(queue_rows)s</div>
<div class="card"><h2>🕘 节点事件</h2>%(evt_rows)s</div>
<div class="card"><h2>📊 原始</h2><div class="mono">tasks keys: %(qcount)s queue</div><div class="mono">seq: %(seq)s</div></div>
</div></body></html>""" % {"nid": h(nid), "seq": seq, "node_online": h(node_online), "now": now,
            "queue_rows": queue_rows, "evt_rows": evt_rows, "qcount": len(queue_keys)}
    else:
        # 人类版节点视角（卡点友好）
        return """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>节点 %s · 卡点</title>
<style>
:root{--bg:#10131a;--card:#171b26;--line:#262c3a;--fg:#e8eaf0;--muted:#98a0b3;--acc:#6ea8ff;--ok:#34c77b;--err:#ff5c5c}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,'PingFang SC',sans-serif;padding:24px;max-width:900px;margin:0 auto}
h1{font-size:20px;margin-bottom:4px}.sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:16px}
.card h2{font-size:14px;color:var(--muted);margin-bottom:12px}
.row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px dashed var(--line);font-size:14px}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--fg)}
.muted{color:var(--muted);font-size:12px}.ok-text{color:var(--ok)}
.big{font-size:30px;font-weight:700;color:var(--acc)}
.status{display:inline-block;padding:3px 14px;border-radius:20px;font-size:13px;font-weight:600}
.st-on{background:rgba(52,199,123,.15);color:var(--ok)}.st-off{background:rgba(255,92,92,.15);color:var(--err)}
.back{position:fixed;top:20px;right:20px;color:var(--muted);font-size:12px;background:var(--card);border:1px solid var(--line);padding:6px 14px;border-radius:20px;text-decoration:none}
</style></head><body>
<a class="back" href="/">← 总览</a>
<h1>🖥 节点 %(nid)s <span class="status %(stcls)s">%(node_online)s</span></h1>
<div class="sub">当前时间 %(now)s · 最新事件号 %(seq)s</div>
<div class="card"><h2>📥 待处理任务（%(qcount)s 张）—— 卡在这里就是有事没干完</h2>%(queue_rows)s</div>
<div class="card"><h2>🕘 这个节点最近在干嘛</h2>%(evt_rows)s</div>
</body></html>""" % {"nid": h(nid), "node_online": h(node_online),
            "stcls": "st-on" if node_online == "在线" else "st-off",
            "now": now, "seq": seq, "qcount": len(queue_keys),
            "queue_rows": queue_rows, "evt_rows": evt_rows}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8798)
    ap.add_argument("--blackboard", default=BB)
    args = ap.parse_args()
    BB = args.blackboard.rstrip("/")
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("黑板看板 v3（双视角）:%d → %s\n  人类版 http://127.0.0.1:%d/\n  AI 版  http://127.0.0.1:%d/ai"
          % (args.port, BB, args.port, args.port))
    srv.serve_forever()
