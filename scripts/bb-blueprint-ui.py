#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-ui.py — 蓝图独立 GUI（:8797）

用户指示（2026-08-24）：蓝图可视化要独立 GUI，不塞在看板里。
独立服务，服务端渲染（打开即见），双主线 × 子阶段 × 工作，自动刷新。

用法：python3 bb-blueprint-ui.py --port 8797
访问：http://127.0.0.1:8797/  （独立蓝图 GUI）
数据源：黑板 data/blueprint/stages + works（bb-blueprint.py 工具维护）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, urllib.request, datetime, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint-ui.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"

def h(s):
    return html.escape(str(s))

def fetch(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def build_page():
    stages = fetch("/data/blueprint/stages").get("value", {})
    works = fetch("/data/blueprint/works").get("value", {}).get("blueprint_map", [])
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stage_list = stages.get("stages", [])
    works_by_stage = {}
    for w in works:
        works_by_stage.setdefault(w.get("stage"), []).append(w)

    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
    st_color = {"done": "#34c77b", "active": "#34c77b", "partial": "#f5b942", "todo": "#7d8596"}

    def render_mainline(mid, title, desc):
        m_stages = [s for s in stage_list if s.get("mainline") == mid]
        html_rows = ""
        for s in m_stages:
            icon = st_icon.get(s.get("status"), "⬜")
            color = st_color.get(s.get("status"), "#7d8596")
            ws = works_by_stage.get(s.get("id"), [])
            w_html = ""
            for w in ws:
                w_html += '<div class="w-item"><span class="w-name">%s</span><span class="w-owner">%s</span><span class="w-status %s">%s</span></div>' % (
                    h(w.get("work","")), h(w.get("owner","")), w.get("status","todo"),
                    st_icon.get(w.get("status","todo"), "⬜"))
            subs = s.get("substages", [])
            sub_html = ""
            for ss in subs:
                sic = st_icon.get(ss.get("status"), "⬜")
                scolor = st_color.get(ss.get("status"), "#7d8596")
                ssws = works_by_stage.get(ss.get("id"), [])
                ssw_html = ""
                for w in ssws:
                    ssw_html += '<div class="w-item" style="padding-left:36px"><span class="w-name">%s</span><span class="w-owner">%s</span><span class="w-status %s">%s</span></div>' % (
                        h(w.get("work","")), h(w.get("owner","")), w.get("status","todo"),
                        st_icon.get(w.get("status","todo"), "⬜"))
                sub_html += '<div class="stage" style="margin-left:16px;border-left:3px solid %s"><div class="stage-head"><span class="stage-icon">%s</span><b>%s</b><span class="muted">%s</span></div>%s</div>' % (
                    scolor, sic, h(ss.get("name","")), h(ss.get("note","")), ssw_html)
            active_cls = ' stage-cur' if s.get("status") in ("active","partial") else ''
            html_rows += '<div class="stage%s" style="border-left:3px solid %s"><div class="stage-head"><span class="stage-icon">%s</span><b>%s</b><span class="muted">%s</span></div>%s%s</div>' % (
                active_cls, color, icon, h(s.get("stage","")+" "+s.get("name","")), h(s.get("note","")), w_html, sub_html)
        return '<div class="ml"><div class="ml-title">%s <span class="muted">%s</span></div>%s</div>' % (h(title), h(desc), html_rows)

    dline = render_mainline("digital", stages.get("mainlines",{}).get("digital",{}).get("name","数字化主线"),
                            stages.get("mainlines",{}).get("digital",{}).get("desc",""))
    pline = render_mainline("physical", stages.get("mainlines",{}).get("physical",{}).get("name","物理主线"),
                            stages.get("mainlines",{}).get("physical",{}).get("desc",""))
    cur_pos = stages.get("current_position", "")
    gate = stages.get("gate", "")

    return """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>花店蓝图 · 独立管理中枢</title>
<style>
:root{--bg:#0b0e14;--card:#141824;--line:#232a3a;--fg:#e8eaf0;--muted:#8b90a3;--acc:#6ea8ff;--ok:#34c77b;--warn:#f5b942}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;padding:28px;max-width:1280px;margin:0 auto}
h1{font-size:26px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
.sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.pos{background:linear-gradient(90deg,rgba(110,168,255,.12),transparent);border:1px solid var(--line);border-radius:12px;padding:14px 20px;margin-bottom:20px;font-size:15px;line-height:1.8}
.pos b{color:var(--acc)}
.ml{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:20px}
.ml-title{font-size:17px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.stage{padding:12px 16px;margin-bottom:10px;background:#101420;border-radius:10px}
.stage-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:14px}
.stage-cur{background:rgba(52,199,123,.07)}
.stage-icon{font-size:16px}
.w-item{display:flex;justify-content:space-between;align-items:center;font-size:13px;color:var(--muted);padding:5px 0 5px 24px;border-bottom:1px dashed var(--line)}
.w-item:last-child{border:none}
.w-name{flex:1;color:var(--fg)}
.w-owner{color:var(--acc);font-size:12px;margin-right:10px}
.w-status{font-size:12px}
.muted{color:var(--muted);font-size:12px}
.legend{display:flex;gap:18px;font-size:13px;color:var(--muted);margin-bottom:16px;padding:8px 14px;background:var(--card);border:1px solid var(--line);border-radius:10px}
.refresh{position:fixed;top:22px;right:24px;color:var(--muted);font-size:12px;background:var(--card);border:1px solid var(--line);padding:7px 16px;border-radius:20px}
</style></head><body>
<div class="refresh">🔄 每 15 秒自动刷新 · %(now)s</div>
<h1>🌷 花店生意演进蓝图</h1>
<div class="sub">独立管理中枢 · 双主线 × 子阶段 × 工作 · 数据：黑板 data/blueprint/</div>
<div class="pos">📍 当前位置：<b>%(cur_pos)s</b><br>🚦 决策门禁：%(gate)s</div>
<div class="legend"><span>✅ 完成</span><span>🟢 进行中</span><span>🟡 部分/雏形</span><span>⬜ 待启动</span></div>
%(dline)s
%(pline)s
<script>setTimeout(function(){location.reload()},15000)</script>
</body></html>""" % {"now": now, "cur_pos": h(cur_pos), "gate": h(gate), "dline": dline, "pline": pline}

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
            self._send(200, build_page(), "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8797)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("蓝图独立 GUI :%d" % args.port)
    srv.serve_forever()
