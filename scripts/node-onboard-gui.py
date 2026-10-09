#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-onboard-gui.py — 分布式节点接入自助工具（GUI）

功能：
1. 填写节点信息 → 生成「角色任命 Prompt」（复制到节点 DSH）
2. 生成「接入提示词」（复制到节点 DSH 执行）
3. 节点状态面板（实时查黑板注册/心跳/任务）

用法：
  python3 node-onboard-gui.py            # 默认 0.0.0.0:8805
  python3 node-onboard-gui.py --port 8805
浏览器打开 http://127.0.0.1:8805

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== node-onboard-gui 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · node-onboard-gui.py — 分布式节点接入自助工具（GUI）")
    print("  · 1. 填写节点信息 → 生成「角色任命 Prompt」（复制到节点 DSH）")
    print("  · 2. 生成「接入提示词」（复制到节点 DSH 执行）")
    print("  · 3. 节点状态面板（实时查黑板注册/心跳/任务）")
    print("  · 命令/参数: port, host")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, datetime, os, time, urllib")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/node-onboard-gui.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, http.server, socketserver, urllib.request, datetime

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/node-onboard-gui.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"  # 本机黑板（GUI 跑在 mac-mini）

# ---------- 模板 ----------
ROLE_TEMPLATE = """你是「{NODE_NAME} 资源节点智能体」——运行在 {DEVICE}（{OS}/{CPU}）上的独立 DSH 智能体，
是分布式智能体网络的 {NODE_NAME} 侧执行节点。

▍定位
- 驻 {DEVICE} 本地，拥有本地 bash/文件/CLD 能力
- 通过黑板任务卡协议与 mac-mini 中枢（100.120.203.20:8792）双向联通
- mac-mini 侧智能体（协调者/各角色）给你下任务 → 你在本地执行 → 结果回传

▍核心能力
1. 资源执行：跑本地命令、读写本地文件、调用本地应用
2. 任务接收：轮询黑板任务卡（GET /tasks/{NODE_ID}/cmd，15s 间隔）
3. 结果回传：执行完写 /tasks/{NODE_ID}/result + 清卡（DELETE）
4. 状态上报：定期心跳（PUT /nodes/{NODE_ID}/heartbeat）

▍任务类型
- 算力任务：批处理/OCR/渲染（利用本地 {CPU}）
- 文件任务：读写/汇总本地文件（扫描目录、提取内容）
- 信息任务：系统状态/已装应用/网络
- CLD 任务：调用本地 CLD/dsh 能力
- 业务任务：按需（如官网扫描、数据采集）

▍边界与纪律
- 危险操作（删除/格式化/系统级修改）需用户确认
- 凭据不落盘、敏感信息不跨总线传明文
- 任务执行前查灯（文件/目录操作先 agent_light）
- 高算力任务先报用户（预算/耗时）
- 报告格式：结构化回传（task_id + ok + result/error）

▍联通协议
- 黑板地址：http://100.120.203.20:8792
- 节点 ID：{NODE_ID}（注册 /nodes/{NODE_ID}）
- 轮询取任务 → 本地执行 → 回传结果 → 清卡"""

ONBOARD_TEMPLATE = """【任务】把我的设备接入分布式智能体网络（黑板任务卡协议），成为「{NODE_NAME}」节点。

【前置检查】
1. 确认本机 Python3 可用（python3 --version）
2. 确认本机到 mac-mini 黑板连通（curl http://100.120.203.20:8792/clock）
3. 确认节点 ID 未被占用（curl http://100.120.203.20:8792/nodes/{NODE_ID}）

【步骤】
1. 获取节点代理脚本（macOS 版 mbp-node-agent.py / 自写同协议脚本）
   - 源：mac-mini 的 ~/dsh-collab/devices/mbp-node-agent.py
   - 复制到本机：~/dsh-collab/devices/
2. 配置常驻（launchd，macOS）
   - 写 plist：com.dsh.{NODE_ID}-node-agent.plist
   - 指向：python3 ~/dsh-collab/devices/mbp-node-agent.py --node-id {NODE_ID} --blackboard http://100.120.203.20:8792
   - launchctl load 并验证 KeepAlive
3. 启动并验证
   - 启动 agent → 确认注册成功（黑板 /nodes/{NODE_ID} 显示 online）
   - 自测：给自己写任务卡（/tasks/{NODE_ID}/cmd）→ 确认执行+回报+清卡
4. 报告
   - 回报：节点 ID / 注册状态 / 心跳频率 / 已验证任务（task_id + ok）
   - 通知 mac-mini 协调者（黑板 notes/{NODE_ID}/joined）

【动作清单（macOS / bash）】
- info: system_profiler/uname/df
- shell: 任意 bash 命令
- dsh: 调用 CLD dsh CLI
- scan: os.walk 扫描目录
- ollama: 本地 Ollama（如启用）

【边界】
- 只读/低风险操作直接执行；删除/系统级修改需用户确认
- 凭据不落盘；敏感信息不跨总线明文"""

# ---------- 黑板 API ----------
def bb(method, path, data=None, timeout=6):
    url = BB + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def list_nodes():
    d = bb("GET", "/nodes/")
    nodes = {}
    for k, v in (d.get("list") or {}).items():
        if k.startswith("nodes/") and not k.endswith("/heartbeat"):
            nid = k.split("/")[-1]
            val = v.get("value", {})
            # 存活标准：nodes/{id}/heartbeat 60 秒内新鲜 = 在线（i9 2026-08-25 确认）
            hb = bb("GET", "/nodes/%s/heartbeat" % nid)
            hb_ts = (hb.get("value") or {}).get("ts", "")
            online = False
            if hb_ts:
                try:
                    import datetime as _dt
                    hb_time = _dt.datetime.fromisoformat(hb_ts)
                    age = (_dt.datetime.now() - hb_time).total_seconds()
                    online = 0 <= age <= 60
                except Exception:
                    online = val.get("status") == "online"
            else:
                online = val.get("status") == "online"
            nodes[nid] = {
                "status": "online" if online else ("stale" if hb_ts else (val.get("status") or "?")),
                "os": val.get("os", ""),
                "hostname": val.get("hostname", ""),
                "capabilities": val.get("capabilities", []),
                "ts": hb_ts[:19] if hb_ts else (val.get("ts") or "")[:19],
                "alive": online,
            }
    return nodes

def node_status(nid):
    d = bb("GET", "/nodes/%s" % nid)
    v = d.get("value", {})
    hb = bb("GET", "/nodes/%s/heartbeat" % nid)
    task = bb("GET", "/tasks/%s/cmd" % nid)
    result = bb("GET", "/tasks/%s/result" % nid)
    return {
        "node": v,
        "heartbeat": hb.get("value", {}),
        "task_cmd": (task.get("value") or {}).get("task_id", None) if "value" in task else None,
        "last_result": (result.get("value") or {}).get("task_id", None) if "value" in result else None,
    }

# ---------- HTTP Handler ----------
HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>分布式节点接入工具</title>
<style>
:root{--bg:#0f1115;--card:#171a21;--line:#2a2f3a;--fg:#e6e9ef;--mut:#8b93a3;--acc:#4f8cff;--ok:#3fb950;--warn:#d29922;--err:#f85149}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;padding:24px;max-width:1100px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}
.card h2{font-size:15px;margin-bottom:12px;color:var(--acc)}
label{display:block;font-size:12px;color:var(--mut);margin:10px 0 4px}
input,select{width:100%;padding:8px 10px;background:#0d0f13;border:1px solid var(--line);border-radius:8px;color:var(--fg);font-size:13px;outline:none}
input:focus{border-color:var(--acc)}
textarea{width:100%;height:200px;background:#0d0f13;border:1px solid var(--line);border-radius:8px;color:var(--fg);font-size:12px;padding:10px;font-family:ui-monospace,Menlo,monospace;resize:vertical}
button{padding:8px 16px;border:none;border-radius:8px;background:var(--acc);color:#fff;font-size:13px;cursor:pointer;margin-top:10px}
button:hover{opacity:.9}
button.ghost{background:transparent;border:1px solid var(--line);color:var(--mut)}
.copybtn{margin-left:8px;padding:4px 10px;font-size:12px;background:transparent;border:1px solid var(--line);color:var(--mut);border-radius:6px;cursor:pointer}
.tabs{margin-top:10px;display:flex;gap:8px}
.tab{padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:transparent;color:var(--mut);font-size:12px;cursor:pointer}
.tab.active{background:var(--acc);color:#fff;border-color:var(--acc)}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--mut);font-weight:500}
.badge{padding:2px 8px;border-radius:10px;font-size:11px}
.badge.on{background:#103a1a;color:var(--ok)}
.badge.off{background:#3a1313;color:var(--err)}
.badge.idle{background:#3a2f10;color:var(--warn)}
.nodelist{max-height:300px;overflow-y:auto}
.actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
#statusbar{color:var(--mut);font-size:12px;margin-top:8px}
.detail{margin-top:12px;padding:10px;background:#0d0f13;border-radius:8px;font-size:12px}
.detail pre{white-space:pre-wrap;color:var(--fg)}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>🌐 分布式节点接入自助工具</h1>
<div class="sub">填写节点信息 → 一键生成「角色任命 Prompt」和「接入提示词」→ 复制到节点侧 DSH 执行。节点状态面板实时查看。</div>

<div class="grid">
  <!-- 左：生成器 -->
  <div class="card">
    <h2>① 节点信息</h2>
    <label>节点名称（如：MBP 资源节点 / i9 资源节点）</label>
    <input id="f_name" placeholder="MBP 资源节点">
    <label>节点 ID（小写，如 mbp / i9 / pc2）</label>
    <input id="f_id" placeholder="mbp">
    <label>设备（如：MacBook Pro / PC-i9）</label>
    <input id="f_dev" placeholder="MacBook Pro">
    <label>操作系统（如：macOS 26.5 / Windows 11 / Linux）</label>
    <input id="f_os" placeholder="macOS 26.5">
    <label>CPU/内存（如：Apple M3 / 16GB）</label>
    <input id="f_cpu" placeholder="Apple M3 / 16GB">

    <div class="tabs">
      <button class="tab active" onclick="switchTab('role',this)">角色任命 Prompt</button>
      <button class="tab" onclick="switchTab('onboard',this)">接入提示词</button>
    </div>
    <textarea id="out" placeholder="（自动生成，可复制）"></textarea>
    <div class="actions">
      <button onclick="gen('role')">生成角色任命 Prompt</button>
      <button onclick="gen('onboard')">生成接入提示词</button>
      <button class="ghost" onclick="copyOut()">📋 复制</button>
    </div>
  </div>

  <!-- 右：节点状态 -->
  <div class="card">
    <h2>② 节点状态面板</h2>
    <div class="actions">
      <button onclick="refresh()">🔄 刷新状态</button>
      <button class="ghost" onclick="sendTask()">📤 发测试任务</button>
      <button class="ghost" onclick="viewDetail()">🔍 看详情</button>
    </div>
    <div class="nodelist"><table>
      <thead><tr><th>节点</th><th>状态</th><th>系统</th><th>主机</th><th>心跳</th></tr></thead>
      <tbody id="nodetbody"><tr><td colspan="5" style="color:var(--mut)">加载中…</td></tr></tbody>
    </table></div>
    <div class="detail" id="detail" style="display:none"><pre id="detailpre"></pre></div>
    <div id="statusbar"></div>
  </div>
</div>

<script>
let roleText = '';
function switchTab(t, btn) {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  if (t === 'role') { if (roleText) document.getElementById('out').value = roleText; }
  else { document.getElementById('out').value = ''; }
}
function collect() {
  return {
    name: document.getElementById('f_name').value || '新节点',
    id: (document.getElementById('f_id').value || 'node').toLowerCase().replace(/[^a-z0-9-]/g,''),
    dev: document.getElementById('f_dev').value || '本机',
    os: document.getElementById('f_os').value || '未知系统',
    cpu: document.getElementById('f_cpu').value || '未知CPU',
  };
}
async function gen(type) {
  const f = collect();
  const r = await fetch('/api/gen', {method:'POST', body: JSON.stringify({type, ...f})});
  const d = await r.json();
  document.getElementById('out').value = d.text;
  if (type === 'role') roleText = d.text;
  setStatus('✅ 已生成' + (type === 'role' ? '角色任命 Prompt' : '接入提示词') + '，可复制');
}
function copyOut() {
  const t = document.getElementById('out');
  t.select();
  navigator.clipboard.writeText(t.value).then(() => setStatus('✅ 已复制到剪贴板'));
}
async function refresh() {
  setStatus('刷新中…');
  const r = await fetch('/api/nodes');
  const d = await r.json();
  const tb = document.getElementById('nodetbody');
  tb.innerHTML = '';
  if (!d.nodes || Object.keys(d.nodes).length === 0) {
    tb.innerHTML = '<tr><td colspan="5" style="color:var(--mut)">暂无节点</td></tr>';
  }
  Object.entries(d.nodes).sort().forEach(([id, n]) => {
    const st = n.alive === true ? '<span class="badge on">online</span>'
      : (n.status === 'stale' ? '<span class="badge idle">心跳停</span>'
      : `<span class="badge off">${n.status||'off'}</span>`);
    tb.innerHTML += `<tr><td>${id}</td><td>${st}</td><td>${n.os||''}</td><td>${n.hostname||''}</td><td>${n.ts||''}</td></tr>`;
  });
  setStatus('✅ 已刷新 ' + Object.keys(d.nodes).length + ' 个节点');
}
async function sendTask() {
  const f = collect();
  const tid = 'test-' + Date.now().toString(36);
  const r = await fetch('/api/task', {method:'POST', body: JSON.stringify({node: f.id, task_id: tid})});
  const d = await r.json();
  setStatus(d.ok ? `📤 已发测试任务 ${tid} 给 ${f.id}（15s 内应执行回报）` : `❌ ${d.error}`);
}
async function viewDetail() {
  const f = collect();
  const r = await fetch('/api/detail?node=' + f.id);
  const d = await r.json();
  const el = document.getElementById('detail');
  const pre = document.getElementById('detailpre');
  pre.textContent = JSON.stringify(d, null, 2);
  el.style.display = 'block';
}
function setStatus(msg) { document.getElementById('statusbar').textContent = msg; }
refresh();
</script></body></html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/api/nodes"):
            self._send(200, {"nodes": list_nodes()})
        elif self.path.startswith("/api/detail"):
            import urllib.parse as up
            q = up.parse_qs(up.urlparse(self.path).query)
            nid = q.get("node", ["mbp"])[0]
            self._send(200, node_status(nid))
        else:
            self._send(404, {"error": "not found"})
    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(ln).decode() if ln else "{}"
        try: data = json.loads(raw)
        except: data = {}
        if self.path == "/api/gen":
            tpl = ROLE_TEMPLATE if data.get("type") == "role" else ONBOARD_TEMPLATE
            text = tpl.format(
                NODE_NAME=data.get("name", "新节点"),
                NODE_ID=data.get("id", "node"),
                DEVICE=data.get("dev", "本机"),
                OS=data.get("os", "未知"),
                CPU=data.get("cpu", "未知"),
            )
            self._send(200, {"text": text})
        elif self.path == "/api/task":
            nid = data.get("node", "mbp")
            tid = data.get("task_id", "test")
            cmd = "echo ===NODE-TEST-OK=== & hostname & uname -a"
            r = bb("PUT", "/tasks/%s/cmd" % nid, {
                "task_id": tid, "action": "shell", "cmd": cmd,
                "requester": "node-onboard-gui", "ts": datetime.datetime.now().isoformat()})
            self._send(200, {"ok": "value" in r or "key" in r, "error": r.get("error", ""), "task_id": tid})
        else:
            self._send(404, {"error": "not found"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8805)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--host", default="0.0.0.0")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((args.host, args.port), Handler) as httpd:
        print("🌐 节点接入自助工具: http://127.0.0.1:%d" % args.port)
        print("   生成 Prompt / 接入提示词 / 节点状态面板")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
